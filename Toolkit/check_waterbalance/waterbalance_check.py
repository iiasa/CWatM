"""
Water balance check of a CWatM WaterCycle output (OUT_TSS_AreaSum_Daily = WaterCycle)

For every station in the csv and every box (compartment):  residual = In - Out - dS  (> 0 water lost, < 0 water created)
day by day and for the whole period, in mm over the catchment of the station. A box is closed if
|residual| <= tol * In over the period. Storages are states at the end of the day -> day 1 is the baseline.

Boxes: Total, Snow, Soil (+interception), Groundwater, Lakes/reservoirs, Channels (+small lakes),
Routing (channels + lakes), Water demand (same definitions as waterbalance_sub.ipynb).

With MODFLOW the Groundwater box is aquifer + coupling buffer (modflow_buffer, transient.py, since 2026-10-14).
Some boxes cannot be checked from the csv and are marked "info" instead of closed / NOT CLOSED:
- reservoir command areas: Total, Lakes, Routing (a reservoir can supply cells outside the catchment of the station)

Usage:  python waterbalance_check.py WaterCycle_areasum_daily.csv [tol]
        -> table of all boxes, exit code 1 if a box is NOT CLOSED
In python:  summary = check(csvfile, tol=1e-3)   (pandas DataFrame, one row per station and box)
"""

import csv
import os
import sys

import numpy as np
import pandas as pd

# In, Out (fluxes, m3 per day) and S (storages, m3 at the end of the day) of each box
# names: WaterCycle columns without the unit (Rain_areasum_m3 -> Rain) or derived series (see add_derived)
BOXES = {
    "Total": dict(
        # pySnowClim: Rain is only the rain on snow-free ground, the rain on snow goes into the snow pack (Rain_on_snow)
        # gw_lateral: groundwater flow across the border of the catchment, gw_rechargeMoved: recharge moved between
        # CWatM cells by the ModFlow grid (MODFLOW, WaterBalance csv)
        # res_transferIn/Out: reservoir transfers (across the border of the catchment), lakeInflowTransit: water on its
        # way into the lakes (lake inflow lag, WaterBalance csv)
        In=["Rain", "Rain_on_snow", "Snow", "glacier", "fossil", "inflowDay", "gw_lateral", "gw_rechargeMoved",
            "res_transferIn"],
        Out=["totalET", "EvapWaterBodyM", "EvapoChannel", "smallevapWaterBody", "Q_m3", "act_nonIrrConsumption",
             "unmet_lost", "leakage_lost", "res_transferOut", "lakeAbstOutside", "liftOutside", "canalLeakOutside"],
        S=["landSto", "storGroundwater", "modflow_buffer", "gridcell_storage", "channelStorage", "lakeResStorage",
           "smalllakeStorage", "lakeInflowTransit"]),
    "Snow": dict(
        In=["Snow", "Rain_on_snow"], Out=["SnowMelt", "IceMelt", "snowEvap"], S=["SnowCover"]),
    "Soil (+interception)": dict(
        In=["Rain", "SnowMelt", "IceMelt", "act_totalIrrConsumption", "gwToLand"],
        Out=["ET_soil", "landRunoff", "rch_land"], S=["soilSto"]),
    # with MODFLOW: aquifer + coupling buffer (recharge / pumping not yet given to MODFLOW, capillary rise, rejected
    # recharge and baseflow of the last MODFLOW run not yet used by CWatM)
    "Groundwater": dict(
        In=["sum_gwRecharge", "gw_lateral", "gw_rechargeMoved"], Out=["baseflow", "gwAbs", "gwCapOut", "rejected_recharge_interflow", "gwRechargeExported_day"],
        S=["storGroundwater", "modflow_buffer"]),
    "Lakes/reservoirs": dict(
        In=["lakeResInflowM", "res_transferIn"],
        Out=["lakeResOutflowM", "EvapWaterBodyM", "lakeAbstTaken", "lakebedExchangeM", "res_transferOut"],
        S=["lakeResStorage"]),
    "Channels (+small lakes)": dict(
        In=["runoff", "glacier", "returnFlow", "lakeResOutflowM", "inflowDay"],
        Out=["Q_m3", "EvapoChannel", "smallevapWaterBody", "channelAbs", "riverbedExchangeM", "lakeResInflowM"],
        S=["channelStorage", "smalllakeStorage", "lakeInflowTransit"]),
    "Routing (channels+lakes)": dict(
        In=["runoff", "glacier", "returnFlow", "inflowDay", "res_transferIn"],
        Out=["Q_m3", "EvapoChannel", "EvapWaterBodyM", "smallevapWaterBody", "act_SurfaceWaterAbstract", "leakage",
             "riverbedExchangeM", "lakebedExchangeM", "res_transferOut", "lakeAbstOutside"],
        S=["channelStorage", "lakeResStorage", "smalllakeStorage", "lakeInflowTransit"]),
    "Water demand": dict(
        In=["act_SurfaceWaterAbstract", "gwAbs", "fossil"],
        Out=["act_totalIrrConsumption", "act_nonIrrConsumption", "addtoevapotrans", "returnFlow", "unmet_lost",
             "liftOutside"], S=[]),
}
# a box is checked only if this variable is in the csv
NEEDS = {"Lakes/reservoirs": "lakeResStorage", "Water demand": "act_irrWithdrawal", "Groundwater": "storGroundwater"}


def settings_options(csvfile):
    """options of the settings file named in the first row of the csv (True/False, missing -> not in the dict)"""
    opts = {}
    with open(csvfile, encoding="utf-8", errors="ignore") as f:
        first = f.readline()
    setfile = next((c.split(":", 1)[1].strip() for c in first.split(",") if c.strip().lower().startswith("settingsfile:")), "")
    if not os.path.isfile(setfile):
        return opts
    with open(setfile, encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.split("#")[0].strip()
            if "=" in s:
                key, value = [x.strip() for x in s.split("=", 1)]
                if value.lower() in ("true", "false"):
                    opts[key] = value.lower() == "true"
    return opts


def read_watercycle(csvfile):
    """list of (station label, DataFrame with short column names) - a csv can hold several stations side by side"""
    with open(csvfile, encoding="utf-8", errors="ignore", newline="") as f:
        raw = [row for _, row in zip(range(4), csv.reader(f))]
    names = [c.strip() for c in raw[3][1:]]
    block = len(names)
    for j in range(1, len(names)):
        if names[j] == names[0]:
            block = j
            break
    full = pd.read_csv(csvfile, skiprows=4, header=None)
    stations = []
    for s in range(len(names) // block):
        c0 = s * block
        df = full.iloc[:, [0] + list(range(1 + c0, 1 + c0 + block))].copy()
        df.columns = ["Date"] + [n.replace("_areasum_m3", "").replace("_sum_m3", "").replace("_m3s-1", "")
                                 for n in names[:block]]
        df = df.loc[:, ~df.columns.duplicated()]
        df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y")
        stations.append((f"{raw[1][1 + c0].strip()} {raw[2][1 + c0].strip()}", df.set_index("Date")))
    return stations


def add_derived(df, opts):
    """derived series [m3 per day or m3]; returns the function z(name) (column or 0)"""
    def z(name):
        return df[name] if name in df.columns else pd.Series(0., index=df.index)

    modflow = "Pumping_daily" in df.columns
    if "groundwater_storage_total" in df.columns:          # with MODFLOW: storage of all layers
        df["storGroundwater"] = df["groundwater_storage_total"]
    df["Q_m3"] = z("avgdischarge") * 86400.
    df["glacier"] = z("GlacierMelt") + z("GlacierRain")
    # routing off (includeRouting = False): no discharge - runoff, glacier water and return flow leave the catchment
    # directly (output of Total)
    # (runoff_m3: after the small lakes, which work without routing too - runoff is before them)
    if not opts.get("includeRouting", True):
        df["Q_m3"] = (z("runoff_m3") if "runoff_m3" in df.columns else z("runoff")) + df["glacier"] + z("returnFlow")
    # abstraction taken from the lakes (WaterBalance csv: at the outlet, incl. canal leakage), else the users' abstraction
    # (cells around the lakes / command areas) + canal leakage; lake water for users outside the catchment (< 0: users
    # of the catchment get water of lakes outside)
    if "lakeResAbstOutlet" in df.columns:
        df["lakeAbstTaken"] = z("lakeResAbstOutlet")
        # (wastewater: the users' reuse of the wastewater reservoirs act_bigLakeResAbst_wwt is part of lakeResAbstOutlet)
        df["lakeAbstOutside"] = (z("lakeResAbstOutlet") - z("act_bigLakeResAbst") - z("act_bigLakeResAbst_wwt")
                                 - z("leakage"))
    else:
        df["lakeAbstTaken"] = z("act_bigLakeResAbst") + z("leakage")
    # runoff before runoff concentration = released runoff + change of the runoff concentration storage
    # (minus what is not from the land: baseflow, canal leakage, recharge rejected by MODFLOW)
    df["landRunoff"] = (z("runoff") + z("gridcell_storage").diff().fillna(0.) - z("baseflow") - z("leakageIntoRunoff")
                        - z("rejected_recharge_interflow"))
    # percolation of the land: recharge without river / lake / canal leakage; seepage scheme: sum_gwRecharge is net of
    # the capillary rise from the aquifer (soil.py)
    df["rch_land"] = (z("sum_gwRecharge") + z("sum_capRiseFromAquifer") - z("riverbedExchangeM") - z("lakebedExchangeM")
                      - z("leakageIntoGw"))
    # MODFLOW: capillary rise used by the land (soil, seepage pond, sealed / water -> runoff) comes from MODFLOW
    # (without MODFLOW the capillary rise is already subtracted in sum_gwRecharge = percolation - capillary rise)
    # capillarUsed (since 2026-10-14) includes sealed and water; older csv: soil + pond only (sealed / water missing)
    if not modflow:
        df["gwCapOut"] = 0.
    elif "capillarUsed" in df.columns:
        df["gwCapOut"] = z("capillarUsed")
    else:
        df["gwCapOut"] = z("sum_capRiseFromGW") + z("sum_seepage") - z("sum_capRiseFromAquifer")
    # ... into the land: plus the capillary rise from the aquifer (taken by MODFLOW as less recharge)
    df["gwToLand"] = df["gwCapOut"] + z("sum_capRiseFromAquifer") if modflow else 0.
    df["ET_soil"] = z("totalET") - z("addtoevapotrans") - z("snowEvap")
    df["landSto"] = z("totalSto") if "totalSto" in df.columns else z("SnowCover") + z("sum_interceptStor") + z("sum_soil")
    df["soilSto"] = df["landSto"] - z("SnowCover")
    df["gwAbs"] = z("Pumping_daily") if modflow else z("nonFossilGroundwaterAbs")
    # (wastewater reuse act_bigLakeResAbst_wwt is in act_SurfaceWaterAbstract, but from the reservoirs)
    df["channelAbs"] = z("act_SurfaceWaterAbstract") - z("act_bigLakeResAbst") - z("act_bigLakeResAbst_wwt")
    # lift areas: channel water taken in the cells of the catchment - lift water the cells get (Lift_<sector>);
    # output of Water demand and Total (0 without lift areas)
    df["liftOutside"] = (z("act_channelAbstract_Lift") - sum(z("Lift_" + s) for s in
                                                            ["Irrigation", "Domestic", "Industry", "Livestock"])
                         if "act_channelAbstract_Lift" in df.columns else 0.)
    # unmetDemand is fossil water only with limitAbstraction = False, else the demand which was not met
    df["fossil"] = 0. if opts.get("limitAbstraction", False) else z("unmetDemand")
    # canal leakage: lost without MODFLOW, with MODFLOW it goes to groundwater / runoff (leakageIntoGw, leakageIntoRunoff)
    df["leakage_lost"] = 0. if modflow else z("leakage")
    # MODFLOW: canal leakage of canals outside the catchment (leakage at the reservoir - into groundwater / runoff of
    # the canal cells of the catchment), output of Total
    df["canalLeakOutside"] = z("leakage") - z("leakageIntoGw") - z("leakageIntoRunoff") if modflow else 0.
    return z, modflow


def info_reason(box, modflow, opts):
    if opts.get("using_reservoir_command_areas", False) and box in ("Total", "Lakes/reservoirs", "Routing (channels+lakes)"):
        return "reservoir command areas can be outside the catchment"
    return ""


def check(csvfile, tol=1e-3, opts=None):
    """summary DataFrame: one row per station and box"""
    if opts is None:
        opts = settings_options(csvfile)
    rows = []
    for label, df in read_watercycle(csvfile):
        z, modflow = add_derived(df, opts)
        area = df["cellArea"].iloc[0]
        to_mm = 1000. / area
        if "inflow" in opts and opts["inflow"] and "inflowDay" not in df.columns:
            print("waterbalance_check: inflow = True but no inflowDay in the WaterCycle csv (old CWatM version?)")
        for name, b in BOXES.items():
            if name in NEEDS and NEEDS[name] not in df.columns:
                continue
            fin = sum((z(n) for n in b["In"]), pd.Series(0., index=df.index)).iloc[1:]
            fout = sum((z(n) for n in b["Out"]), pd.Series(0., index=df.index)).iloc[1:]
            ds = sum((z(n) for n in b["S"]), pd.Series(0., index=df.index)).diff().iloc[1:]
            res = fin - fout - ds
            In = fin.sum()
            reason = info_reason(name, modflow, opts)
            closed = abs(res.sum()) <= tol * abs(In)
            status = "closed" if closed else ("info" if reason else "NOT CLOSED")
            rows.append(dict(station=label, box=name, In_mm=In * to_mm, Out_mm=fout.sum() * to_mm, dS_mm=ds.sum() * to_mm,
                             residual_mm=res.sum() * to_mm, rel=res.sum() / In if In else np.nan,
                             maxdaily_mm=res.abs().max() * to_mm, status=status, note=reason if not closed else "",
                             days=len(res), area_km2=area / 1e6))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    tol = float(sys.argv[2]) if len(sys.argv) > 2 else 1e-3
    s = check(sys.argv[1], tol)
    with pd.option_context("display.width", 250, "display.max_columns", 20):
        print(s.to_string(index=False, float_format=lambda v: f"{v:.4g}"))
    sys.exit(1 if (s.status == "NOT CLOSED").any() else 0)
