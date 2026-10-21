"""
Water balance of a CWatM run from its WaterBalance csv (OUT_TSS_AreaSum_Daily = WaterBalance), for pytest

The calculation of the notebook budget/watercycle.ipynb (cells 02, 03, 04, 05 and 07: stations, options of the
settings file, derived series, overall circle and all circles), without the figures. The result is the table of
cell 07: the circles with a balance error check (1st list) and the circles without one and why (2nd list).

A circle passes if |error / In| <= threshold or (abs_threshold given) its absolute error for one year
|error mm / years of the run| <= abs_threshold [mm/yr]. Error = In - Out - dS (balance) or total - sum of the parts
(composition), in mm over the catchment of the station for the whole period.

Use:  res = balance("WaterBalance_areasum_daily.csv", threshold=1e-3, abs_threshold=0.1)
      res["summary"] (1st list, column "passed"), res["others"] (2nd list), res["failed"] (circles above the
      threshold), report(res) (text as in cell 07)
Command line: python watercycle_balance.py WaterBalance_areasum_daily.csv [threshold [abs_threshold]]
"""

import csv
import os
import sys

import numpy as np
import pandas as pd

# options with an effect on the water balance: (option, columns which have to be in the csv if on)
OPTIONS = [
    ("modflow_coupling", ["Pumping_daily", "modflow_buffer", "capillarUsed"]),
    ("modflow_seepage", ["sum_seepage", "sum_capRiseFromAquifer"]),
    ("CapillarRise", ["sum_capRiseFromGW"]),
    ("preferentialFlow", ["prefFlow_GW"]),
    ("includeGlaciers", ["GlacierMelt", "GlacierRain"]),
    ("usepySnowClim", ["packwater"]),
    ("includeRunoffConcentration", ["gridcell_storage"]),
    ("includeRouting", []),
    ("inflow", ["inflowDay"]),
    ("includeWaterBodies", ["lakeResStorage", "lakeResInflowM"]),
    ("useSmallLakes", ["smalllakeStorage", "smallevapWaterBody"]),
    ("includeWaterDemand", ["act_irrWithdrawal", "returnFlow"]),
    ("includeIrrigation", ["act_totalIrrConsumption"]),
    ("sectorSourceAbstractionFractions", ["Lake_Irrigation", "Channel_Irrigation", "GW_Irrigation", "Res_Irrigation"]),
    ("limitAbstraction", []),
    ("using_reservoir_command_areas", []),
    ("reservoir_transfers", []),
    ("includeWastewater", []),
    ("includeDesalination", []),
    ("includePitLatrine", []),
]
# an option only has an effect if its parent option is on
PARENT = {"modflow_seepage": "modflow_coupling", "useSmallLakes": "includeWaterBodies", "reservoir_transfers": "includeWaterBodies",
          "includeIrrigation": "includeWaterDemand", "limitAbstraction": "includeWaterDemand",
          "sectorSourceAbstractionFractions": "includeWaterDemand",
          "using_reservoir_command_areas": "includeWaterDemand", "includeWastewater": "includeWaterDemand",
          "includeDesalination": "includeWaterDemand", "includePitLatrine": "includeWaterDemand"}
# 2nd list: circles without a balance error
REASON = {"potential": "no balance: potential vs actual, the difference is the deficit (water stress), not an error",
          "storage": "no balance: storage change split into decrease (In) and increase (Out), dS = Out - In by definition",
          "implied storage": "no balance: CWatM has no glacier storage, the difference is the implied glacier change "
                             "(error 0 by definition)"}


def read_csv(csv_file, station=None, start_date=None, end_date=None):
    """
    Stations of the csv (a block of columns with the same xloc / yloc each) and the daily values of one station
    (None: largest catchment = outlet) with short column names (rows: days, or months / years of a monthtot /
    annualtot file); period from start_date (baseline: the row before)
    to end_date, None: whole file
    """
    with open(csv_file, encoding="utf-8", errors="ignore", newline="") as f:
        raw = [row for _, row in zip(range(4), csv.reader(f))]
    names_all = [c.strip() for c in raw[3][1:]]
    xy = list(zip([c.strip() for c in raw[1][1:]], [c.strip() for c in raw[2][1:]]))
    starts = [i for i in range(len(xy)) if i == 0 or xy[i] != xy[i - 1]]
    block = len(names_all) // len(starts)
    short = [n.replace("_areasum_m3", "").replace("_sum_m3", "").replace("_m3s-1", "") for n in names_all[:block]]
    full = pd.read_csv(csv_file, skiprows=4, header=None)
    ia = short.index("cellArea")
    stations = pd.DataFrame([[k, float(xy[k * block][0]), float(xy[k * block][1]), full.iloc[0, 1 + k * block + ia] / 1e6]
                             for k in range(len(starts))], columns=["station", "lon", "lat", "area km2"]).set_index("station")
    if station is None:
        station = int(stations["area km2"].idxmax())
    c0 = station * block
    df = full.iloc[:, [0] + list(range(1 + c0, 1 + c0 + block))].copy()
    df.columns = ["Date"] + short
    df = df.loc[:, ~df.columns.duplicated()]
    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y")
    df = df.set_index("Date")
    i_base = 0 if start_date is None else max(df.index.get_loc(pd.to_datetime(start_date, format="%d/%m/%Y")) - 1, 0)
    i_end = len(df) - 1 if end_date is None else df.index.get_loc(pd.to_datetime(end_date, format="%d/%m/%Y"))
    df = df.iloc[i_base:i_end + 1].copy()
    settings_file = next((c.split(":", 1)[1].strip() for c in raw[0] if c.strip().lower().startswith("settingsfile:")), "")
    return df, stations, station, settings_file


def settings_options(settings_file):
    """all True/False options (any section) and the title of the settings file"""
    opts, title = {}, ""
    if os.path.isfile(settings_file):
        with open(settings_file, encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.split("#")[0].strip()
                if "=" in s:
                    k, v = [x.strip() for x in s.split("=", 1)]
                    if v.lower() in ("true", "false"):
                        opts[k] = v.lower() == "true"
                    if k.lower() == "title":
                        title = v
    return opts, title


def balance(csv_file, station=None, threshold=1e-3, start_date=None, end_date=None, abs_threshold=None):
    """
    Water balance of all circles (cell 07 of budget/watercycle.ipynb) for one station (None: outlet)

    Returns a dict: summary (1st list: circles with an error check, column "passed"), others (2nd list: circles
    without an error check, why), failed (circles of the 1st list with |error / In| > threshold and, if abs_threshold
    is given, |error| per year > abs_threshold [mm/yr]), days, period, station, lon, lat, area_km2, title,
    settings_file, threshold, abs_threshold
    """
    df, stations, station, settings_file = read_csv(csv_file, station, start_date, end_date)
    opts, title = settings_options(settings_file)
    area = df["cellArea"].iloc[0]
    days = df.index[1:]
    # days of the balance from the dates (the first row is the baseline): daily, monthtot or annualtot file
    ndays = (df.index[-1] - df.index[0]).days
    nyears = max(ndays, 1) / 365.25

    # options: from the settings file, else from the csv columns, else the CWatM default (routing on)
    on = {}
    for k, cols in OPTIONS:
        in_csv = all(c in df.columns for c in cols) if cols else None
        val = opts.get(k)
        if val is None:
            val = bool(in_csv) if cols else k == "includeRouting"
        if k in PARENT and not on[PARENT[k]]:
            on[k] = False
            continue
        if cols and not val and in_csv:
            val = True
        on[k] = val
    on["CapillarRise"] = on["CapillarRise"] or on["modflow_coupling"]
    modflow = on["modflow_coupling"]

    # derived series (cell 03)
    def z(name):
        return df[name] if name in df.columns else pd.Series(0., index=df.index)

    if "groundwater_storage_total" in df.columns:
        df["storGroundwater"] = df["groundwater_storage_total"]
    # discharge [m3/s]: value of the day (daily file) or mean of the month / year (monthtot / annualtot file)
    # -> times the days of each row
    df["Q_m3"] = z("avgdischarge") * 86400. * df.index.to_series().diff().dt.days.fillna(1.)
    if on["includeGlaciers"]:
        df["glacier"] = z("GlacierMelt") + z("GlacierRain")
    # routing off (includeRouting = False): no discharge - runoff, glacier water and return flow leave the catchment
    # directly (output "Discharge" of Total and of the overall circle; before 2026-10-16 missing: Total 0.2-0.4 of In)
    # (runoff_m3: after the small lakes, which work without routing too - runoff is before them)
    if not on["includeRouting"]:
        df["Q_m3"] = (z("runoff_m3") if "runoff_m3" in df.columns else z("runoff")) + z("glacier") + z("returnFlow")
    if on["includeWaterDemand"] and not opts.get("limitAbstraction", False):
        df["fossil"] = z("unmetDemand")
    if on["includeWaterDemand"] and not modflow:
        df["leakage_lost"] = z("leakage")
    if on["includeWaterDemand"] and modflow:
        # MODFLOW: canal leakage (at the reservoir) goes into groundwater / runoff of the canal cells - canals outside the
        # catchment: lost for it (< 0: leakage of reservoirs outside into canals of the catchment)
        df["canalLeakOutside"] = z("leakage") - z("leakageIntoGw") - z("leakageIntoRunoff")
    df["landRunoff"] = (z("runoff") + z("gridcell_storage").diff().fillna(0.) - z("baseflow") - z("leakageIntoRunoff")
                        - z("rejected_recharge_interflow"))
    if on["CapillarRise"]:
        if modflow:
            df["capGW"] = z("capillarUsed") if "capillarUsed" in df.columns else \
                z("sum_capRiseFromGW") + z("sum_seepage") - z("sum_capRiseFromAquifer")
        else:
            df["capGW"] = z("sum_capRiseFromGW")
    if on["modflow_seepage"]:
        df["capAq"] = z("sum_capRiseFromAquifer")
        landSto = z("totalSto") if "totalSto" in df.columns else z("SnowCover") + z("sum_interceptStor") + z("sum_soil")
        df["pond"] = landSto - z("SnowCover") - z("sum_interceptStor") - z("sum_soil")
    df["percolation"] = (z("sum_gwRecharge") + z("capAq") - z("riverbedExchangeM") - z("lakebedExchangeM") - z("leakageIntoGw")
                         + (0. if modflow else z("sum_capRiseFromGW")))
    if on["includeWaterDemand"]:
        df["gwAbs"] = z("Pumping_daily") if modflow else z("nonFossilGroundwaterAbs")
        # (wastewater reuse act_bigLakeResAbst_wwt is in act_SurfaceWaterAbstract, but from the reservoirs)
        df["channelAbs"] = z("act_SurfaceWaterAbstract") - z("act_bigLakeResAbst") - z("act_bigLakeResAbst_wwt")
    if "act_channelAbstract_Lift" in df.columns:
        # lift areas: channel water taken in the cells of the catchment - lift water the cells get (Lift_<sector>)
        df["liftOutside"] = z("act_channelAbstract_Lift") - sum(z("Lift_" + s) for s in
                                                                  ["Irrigation", "Domestic", "Industry", "Livestock"])
    if "lakeResAbstOutlet" in df.columns:
        # lake water for users outside the catchment: taken from the lakes (at the outlet) - used by the cells of the
        # catchment (buffer / command areas) - canal leakage; < 0: users of the catchment get water of lakes outside
        # (wastewater: the users' reuse of the wastewater reservoirs act_bigLakeResAbst_wwt is part of lakeResAbstOutlet)
        df["lakeAbstOutside"] = z("lakeResAbstOutlet") - z("act_bigLakeResAbst") - z("act_bigLakeResAbst_wwt") - z("leakage")
    df["ET_all"] =z("totalET") + z("EvapWaterBodyM") + z("EvapoChannel") + z("smallevapWaterBody")
    to_mm = 1000. / area

    def flux(col):
        return z(col).iloc[1:].sum() * to_mm

    def change(col):
        s = z(col)
        return (s.iloc[-1] - s.iloc[0]) * to_mm

    # overall circle as in the GUI (cells 04, 05)
    # (MODFLOW: lateral groundwater flow and recharge moved by the grid across the border of the catchment)
    # (reservoir transfers across the border of the catchment; water on its way into the lakes: lakeInflowTransit)
    gui_in = ["Rain", "Rain_on_snow", "Snow", "glacier", "inflowDay", "fossil", "gw_lateral", "gw_rechargeMoved",
              "res_transferIn"]
    # (wastewater: evaporation and export out of the model, storage in treatment)
    gui_out = ["Q_m3", "act_nonIrrConsumption", "unmet_lost", "leakage_lost", "ET_all", "res_transferOut", "wwtEvap",
               "wwtSewerExported", "lakeAbstOutside", "liftOutside", "canalLeakOutside"]
    gui_sto = ["sum_interceptStor", "channelStorage", "lakeResStorage", "smalllakeStorage", "gridcell_storage",
               "storGroundwater", "modflow_buffer", "sum_soil", "pond", "SnowCover", "lakeInflowTransit", "wwtInTreatment"]
    total_input = sum(flux(c) for c in gui_in if c in df.columns)
    total_output = sum(flux(c) for c in gui_out if c in df.columns)
    dstorage = sum(change(c) for c in gui_sto if c in df.columns)

    # circles (cell 07)
    gwname = "Groundwater" + (" (MODFLOW + coupling)" if modflow else "")
    capgw = "Capillary rise from groundwater" + (" (MODFLOW)" if modflow else "")
    PARTS = {
        "Total": dict(
            In=[("Rain", "Rain"), ("Rain on snow", "Rain_on_snow"), ("Snow", "Snow"), ("Glacier", "glacier"), ("Inflow", "inflowDay"),
                ("Fossil groundwater", "fossil"), ("Lateral groundwater flow", "gw_lateral"),
                ("Recharge moved by the grid", "gw_rechargeMoved"), ("Reservoir transfer in", "res_transferIn")],
            Out=[("Evapotranspiration", "ET_all"), ("Discharge", "Q_m3"), ("Non-irrigation consumption", "act_nonIrrConsumption"),
                 ("Unmet lost", "unmet_lost"), ("Canal leakage lost", "leakage_lost"), ("Reservoir transfer out", "res_transferOut"),
                 ("Canal leakage outside the catchment", "canalLeakOutside")],
            S=[("Snow cover", "SnowCover"), ("Interception", "sum_interceptStor"), ("Soil moisture", "sum_soil"),
               ("Seepage pond", "pond"), ("Groundwater", "storGroundwater"), ("MODFLOW buffer", "modflow_buffer"),
               ("Runoff concentration", "gridcell_storage"), ("Channels", "channelStorage"), ("Lakes/reservoirs", "lakeResStorage"),
               ("Small lakes", "smalllakeStorage"), ("Lake inflow in transit", "lakeInflowTransit")]),
        "Soil (+interception, pond)": dict(
            In=[("Rain", "Rain"), ("Snow melt", "SnowMelt"), ("Ice melt", "IceMelt"), ("Irrigation", "act_totalIrrConsumption"),
                (capgw, "capGW"), ("Capillary rise from aquifer", "capAq")],
            Out=[("Transpiration", "sum_actTransTotal"), ("Bare soil evaporation", "sum_actBareSoilEvap"),
                 ("Interception evaporation", "sum_interceptEvap"), ("Open water + pond evaporation", "sum_openWaterEvap"),
                 ("Runoff", "landRunoff"), ("Percolation", "percolation")],
            S=[("Interception", "sum_interceptStor"), ("Soil moisture", "sum_soil"), ("Seepage pond", "pond")]),
        gwname: dict(
            In=[("Percolation", "percolation"), ("River leakage", "riverbedExchangeM"), ("Lake leakage", "lakebedExchangeM"),
                ("Canal leakage", "leakageIntoGw"), ("Lateral groundwater flow", "gw_lateral"),
                # MODFLOW: a ModFlow cell mixes the recharge of the CWatM cells it overlaps (0 over the whole mask)
                ("Recharge moved by the grid", "gw_rechargeMoved")],
            Out=[("Baseflow", "baseflow"), ("Capillary rise", "capGW"), ("Capillary rise from aquifer", "capAq"),
                 ("Rejected recharge", "rejected_recharge_interflow"), ("Pumping", "gwAbs"),
                 ("Exported recharge", "gwRechargeExported_day")],
            S=[("Aquifer", "storGroundwater"), ("MODFLOW buffer", "modflow_buffer")]),
        "Snow": dict(
            In=[("Snowfall", "Snow"), ("Rain on snow", "Rain_on_snow")],
            Out=[("Snow melt", "SnowMelt"), ("Ice melt", "IceMelt"), ("Snow evaporation", "snowEvap")],
            S=[("Snow cover", "SnowCover")]),
        "Lakes/reservoirs": dict(
            In=[("Lake inflow", "lakeResInflowM"), ("Transfer in", "res_transferIn")],
            Out=[("Lake outflow", "lakeResOutflowM"), ("Evaporation", "EvapWaterBodyM"), ("Abstraction", "act_bigLakeResAbst"),
                 ("Canal leakage", "leakage"), ("Lake leakage", "lakebedExchangeM"), ("Transfer out", "res_transferOut")],
            S=[("Lakes/reservoirs", "lakeResStorage")]),
        "Channels (+small lakes)": dict(
            In=[("Runoff", "runoff"), ("Glacier", "glacier"), ("Return flow", "returnFlow"), ("Lake outflow", "lakeResOutflowM"),
                ("Inflow", "inflowDay")],
            Out=[("Discharge", "Q_m3"), ("Channel evaporation", "EvapoChannel"), ("Small lake evaporation", "smallevapWaterBody"),
                 ("Channel abstraction", "channelAbs"), ("River leakage", "riverbedExchangeM"), ("Lake inflow", "lakeResInflowM")],
            # lake inflow in transit: has left the channels (or an upstream lake), not yet in the lake (lake inflow lag)
            S=[("Channels", "channelStorage"), ("Small lakes", "smalllakeStorage"), ("Lake inflow in transit", "lakeInflowTransit")]),
        "Routing (channels + lakes)": dict(
            In=[("Runoff", "runoff"), ("Glacier", "glacier"), ("Return flow", "returnFlow"), ("Inflow", "inflowDay"),
                ("Reservoir transfer in", "res_transferIn")],
            Out=[("Discharge", "Q_m3"), ("Channel evaporation", "EvapoChannel"), ("Lake evaporation", "EvapWaterBodyM"),
                 ("Small lake evaporation", "smallevapWaterBody"), ("Surface water abstraction", "act_SurfaceWaterAbstract"),
                 ("Canal leakage", "leakage"), ("River leakage", "riverbedExchangeM"), ("Lake leakage", "lakebedExchangeM"),
                 ("Reservoir transfer out", "res_transferOut")],
            S=[("Channels", "channelStorage"), ("Lakes/reservoirs", "lakeResStorage"), ("Small lakes", "smalllakeStorage"),
               ("Lake inflow in transit", "lakeInflowTransit")]),
        "Water demand": dict(
            In=[("Surface water", "act_SurfaceWaterAbstract"), ("Groundwater", "gwAbs"), ("Fossil groundwater", "fossil")],
            Out=[("Irrigation consumption", "act_totalIrrConsumption"), ("Non-irrigation consumption", "act_nonIrrConsumption"),
                 ("Irrigation losses (ET)", "addtoevapotrans"), ("Return flow", "returnFlow"), ("Unmet lost", "unmet_lost")],
            S=[]),
    }
    NEEDS = {"Lakes/reservoirs": "includeWaterBodies", "Channels (+small lakes)": "includeRouting",
             "Routing (channels + lakes)": "includeRouting", "Water demand": "includeWaterDemand"}
    parts = {k: v for k, v in PARTS.items() if on.get(NEEDS.get(k), True)}

    # interception, soil layers, soil per land cover (WaterBalance csv)
    NEWPARTS = {
        "Interception": dict(
            In=[("Rain", "Rain")], Out=[("Interception evaporation", "sum_interceptEvap"), ("Throughfall", "sum_throughfall")],
            S=[("Interception", "sum_interceptStor")]),
        "Soil layer 1": dict(
            In=[("Infiltration", "sum_infiltration"), ("Capillary rise from layer 2", "sum_capRise2to1")],
            Out=[("Transpiration", "sum_ta1"), ("Bare soil evaporation", "sum_actBareSoilEvap"), ("Percolation to layer 2", "sum_perc1to2"),
                 ("Infiltration excess to layer 2", "sum_excess1to2"), ("Capillary rise overflow to runoff", "sum_capOverflowRunoff")],
            S=[("Layer 1", "sum_w1")]),
        "Soil layer 2": dict(
            In=[("Percolation from layer 1", "sum_perc1to2"), ("Infiltration excess from layer 1", "sum_excess1to2"),
                ("Capillary rise from layer 3", "sum_capRise3to2"), ("Seepage pond overflow", "pond2soil2")],
            Out=[("Capillary rise to layer 1", "sum_capRise2to1"), ("Transpiration", "sum_ta2"), ("Percolation to layer 3", "sum_perc2to3")],
            S=[("Layer 2", "sum_w2")]),
        "Soil layer 3": dict(
            In=[("Percolation from layer 2", "sum_perc2to3"), (capgw, "sum_capRiseFromGW"), ("Seepage pond overflow", "pond2soil3")],
            Out=[("Capillary rise to layer 2", "sum_capRise3to2"), ("Transpiration", "sum_ta3"), ("Percolation to groundwater", "sum_perc3toGW")],
            S=[("Layer 3", "sum_w3")]),
    }
    SOILLC = []
    for cov, lab in [("forest", "forest"), ("grassland", "grassland"), ("irrPaddy", "paddy"), ("irrNonPaddy", "non-paddy")]:
        if cov + "_inWater" in df.columns and flux(cov + "_inWater") > 0.01:
            SOILLC.append("Soil " + lab)
            NEWPARTS["Soil " + lab] = dict(
                In=[("Throughfall + snow melt", cov + "_inWater"), ("Irrigation", cov + "_irrigation"),
                    ("Capillary rise from groundwater", cov + "_capRise"), ("Seepage into the pond", cov + "_seepage")],
                Out=[("Transpiration", cov + "_transp"), ("Bare soil evaporation", cov + "_bareSoilEvap"),
                     ("Open water + pond evaporation", cov + "_openWaterEvap"), ("Direct runoff", cov + "_directRunoff"),
                     ("Percolation", cov + "_perc3toGW"), ("Preferential flow", cov + "_prefFlow")],
                S=[("Soil", cov + "_soilStor")])
    parts.update({k: v for k, v in NEWPARTS.items() if v["S"][0][1] in df.columns})
    if "sum_directRunoff" in df.columns:
        parts["Runoff concentration"] = dict(
            In=[("Direct runoff", "sum_directRunoff"), ("Interflow", "sum_interflow"), ("Baseflow", "baseflow"),
                ("Canal leakage", "leakageIntoRunoff")],
            Out=[("Runoff to the river", "runoff")], S=[("Runoff concentration", "gridcell_storage")])
    if on["usepySnowClim"] and "snowSWE" in df.columns:
        df["condensationGain"] = -z("condensation")
        df["depositionGain"] = -z("deposition")
        parts["Snow pack (pySnowClim)"] = dict(
            In=[("Snowfall", "Snow"), ("Rain on snow", "Rain_on_snow"), ("Condensation", "condensationGain"),
                ("Deposition", "depositionGain")],
            Out=[("Melt water out of the pack", "SnowMelt"), ("Sublimation", "sublimation"),
                 ("Evaporation of pack water", "snowwaterevaporation"), ("Snow reset", "snowReset")],
            S=[("Snow (SWE)", "snowSWE"), ("Pack water", "packwater")])
    snowname = "Snow pack (pySnowClim)" if "Snow pack (pySnowClim)" in parts else "Snow"
    if on["includeGlaciers"] and "glacierAreaSnow" in df.columns:
        gl_in = z("glacierAreaSnow") + z("glacierAreaRain")
        gl_out = z("GlacierMelt") + z("GlacierRain")
        df["glacierImplied"] = (gl_in - gl_out).where(df.index > df.index[0], 0.).cumsum()
        parts["Glacier"] = dict(
            In=[("Snowfall on glacier", "glacierAreaSnow"), ("Rain on glacier", "glacierAreaRain")],
            Out=[("Glacier melt", "GlacierMelt"), ("Rain on glacier to the routing", "GlacierRain")],
            S=[("Glacier change (implied)", "glacierImplied")])
    for wb, nm in [("lake", "Lakes"), ("res", "Reservoirs")]:
        if wb + "_storage" in df.columns:
            parts[nm] = dict(
                In=[("Inflow", wb + "_inflow"), ("Transfer in", wb + "_transferIn")],
                Out=[("Outflow", wb + "_outflow"), ("Evaporation", wb + "_evap"), ("Abstraction", wb + "_abstraction"),
                     ("Canal leakage", wb + "_leakage"), ("Lakebed leakage", wb + "_bedExchange"), ("Transfer out", wb + "_transferOut")],
                S=[(nm, wb + "_storage")])
    GWLAYERS = []
    n = 1
    while f"gwlayer{n}_storage" in df.columns:
        L = f"gwlayer{n}_"
        GWLAYERS.append(f"Aquifer layer {n}")
        parts[f"Aquifer layer {n}"] = dict(
            In=([("Recharge", "gwlayer1_recharge")] if n == 1 else []) + [
                ("Lateral inflow", L + "lateral"), ("From the layer above", L + "fromAbove"), ("From the layer below", L + "fromBelow")],
            Out=([("Drains (baseflow + capillary rise)", "gwlayer1_drain")] if n == 1 else []) + [("Pumping", L + "pumping")],
            S=[(f"Layer {n}", L + "storage")])
        n += 1
    if "totalWaterDemand" in df.columns:
        df["unmetNotSupplied"] = z("unmetDemand") if opts.get("limitAbstraction", False) else 0.
        parts["Demand vs supply"] = dict(
            In=[("Irrigation paddy demand", "irrPaddyDemand"), ("Irrigation non-paddy demand", "irrNonpaddyDemand"),
                ("Domestic demand", "domesticDemand"), ("Industry demand", "industryDemand"), ("Livestock demand", "livestockDemand")],
            Out=[("Irrigation withdrawal", "act_irrWithdrawal"), ("Domestic withdrawal", "act_domWithdrawal"),
                 ("Industry withdrawal", "act_indWithdrawal"), ("Livestock withdrawal", "act_livWithdrawal"),
                 ("Not supplied (unmet)", "unmetNotSupplied")], S=[])
        parts["Irrigation use"] = dict(
            In=[("Paddy withdrawal", "act_irrPaddyWithdrawal"), ("Non-paddy withdrawal", "act_irrNonpaddyWithdrawal")],
            Out=[("Paddy consumption", "act_paddyConsumption"), ("Non-paddy consumption", "act_nonpaddyConsumption"),
                 ("Return flow", "returnflowIrr"), ("Losses to ET", "addtoevapotrans"), ("Lost (fossil water)", "unmet_lostirr")], S=[])
        parts["Non-irrigation use"] = dict(
            In=[("Domestic withdrawal", "act_domWithdrawal"), ("Industry withdrawal", "act_indWithdrawal"),
                ("Livestock withdrawal", "act_livWithdrawal")],
            Out=[("Domestic consumption", "act_domConsumption"), ("Industry consumption", "act_indConsumption"),
                 ("Livestock consumption", "act_livConsumption"), ("Return flow", "returnflowNonIrr"),
                 ("Lost (fossil water)", "unmet_lostNonirr"), ("Pit latrines (to groundwater)", "pitLatrinToGW")], S=[])
    DEMANDPARTS = ["Demand vs supply", "Irrigation use", "Non-irrigation use"]

    # abstraction from lakes / reservoirs at the outlet (WaterBalance csv): the lake circles lose what is taken from the
    # lake (incl. canal leakage), wherever the users are; Routing and Total: lake water for users outside the catchment
    if "lakeResAbstOutlet" in df.columns:
        for name, pre in [("Lakes/reservoirs", None), ("Lakes", "lake"), ("Reservoirs", "res")]:
            if name in parts:
                old = {"act_bigLakeResAbst", "leakage"} if pre is None else {pre + "_abstraction", pre + "_leakage"}
                parts[name]["Out"] = [t for t in parts[name]["Out"] if t[1] not in old] + [
                    ("Abstraction (taken from the lakes)", "lakeResAbstOutlet" if pre is None else pre + "_abstOutlet")]
        for name in ["Routing (channels + lakes)", "Total"]:
            if name in parts:
                parts[name]["Out"] = parts[name]["Out"] + [("Lake water for users outside the catchment", "lakeAbstOutside")]
    # lift areas (WaterBalance csv): channel water taken in the catchment for users outside (< 0: taken outside for users
    # of the catchment) - an output of the water demand (abstraction in, lift water of the users out) and of Total
    if "liftOutside" in df.columns:
        for name in ["Water demand", "Total"]:
            if name in parts:
                parts[name]["Out"] = parts[name]["Out"] + [("Lift water for users outside the catchment", "liftOutside")]

    # wastewater (includeWastewater, WaterBalance csv): sewer collection from the non-irrigation return flow and from
    # urban runoff (sealed areas) -> treatment (storage) -> overflow / treated water to the river (in the return flow),
    # to reservoirs, evaporation, export out of the model; reuse taken from the wastewater reservoirs
    if "wwtSewerCollection" in df.columns:
        parts["Wastewater"] = dict(
            In=[("Sewer collection", "wwtSewerCollection")],
            Out=[("Overflow + treated to the river", "wwtOverflowOut"), ("Treated to reservoirs", "wwtSentToRes"),
                 ("Evaporation", "wwtEvap"), ("Exported", "wwtSewerExported")],
            S=[("In treatment", "wwtInTreatment")])
        add = {"Total": dict(Out=[("Wastewater evaporation", "wwtEvap"), ("Wastewater exported", "wwtSewerExported")],
                             S=[("Wastewater in treatment", "wwtInTreatment")]),
               "Soil (+interception, pond)": dict(Out=[("Urban runoff to the sewer", "wwtUrbanLeakage")]),
               "Water demand": dict(Out=[("Collected to the sewer", "wwtSewerCollectedBySoruce")]),
               "Non-irrigation use": dict(Out=[("Collected to the sewer", "wwtSewerCollectedBySoruce")]),
               # reuse: part of the abstraction at the outlet (lakeResAbstOutlet, since 2026-10-16), else the users'
               "Lakes/reservoirs": dict(In=[("Treated wastewater", "wwtSentToRes")],
                                        Out=[] if "lakeResAbstOutlet" in df.columns else
                                        [("Wastewater reuse", "act_bigLakeResAbst_wwt")]),
               "Reservoirs": dict(In=[("Treated wastewater", "wwtSentToRes")],
                                  Out=[] if "lakeResAbstOutlet" in df.columns else
                                  [("Wastewater reuse", "act_bigLakeResAbst_wwt")]),
               "Routing (channels + lakes)": dict(In=[("Treated wastewater to reservoirs", "wwtSentToRes")])}
        for name, terms in add.items():
            if name in parts:
                for side, lst in terms.items():
                    parts[name][side] = parts[name][side] + lst

    def part_terms(p):
        terms = []
        for side, other, lst in (("In", "Out", p["In"]), ("Out", "In", p["Out"])):
            for label, col in lst:
                if col in df.columns:
                    v = flux(col)
                    terms.append((side, label, v) if v >= 0 else (other, label + " (neg.)", -v))
        for label, col in p["S"]:
            if col in df.columns:
                v = change(col)
                terms.append(("S+", label, v) if v >= 0 else ("S-", label, -v))
        return terms

    # not drawn: option off, or all terms 0 over the period
    excluded = [[k, "option off: " + NEEDS[k]] for k in PARTS if k not in parts]
    for k in [k for k in parts if k != "Total" and all(abs(v) < 1e-9 for _, _, v in part_terms(parts[k]))]:
        del parts[k]
        excluded.append([k, "all terms 0 over the period (not in this catchment)"])

    def part_row(name, p):
        t = part_terms(p)
        s = {k: sum(v for side, _, v in t if side == k) for k in ("In", "Out", "S+", "S-")}
        return [name, "balance", s["In"], s["Out"], s["S+"] - s["S-"], s["In"] + s["S-"] - s["Out"] - s["S+"],
                ", ".join(l for l, c in p["In"] + p["Out"] + p["S"] if c in df.columns)]

    ET = {"Land": [("Transpiration forest", "actTransTotal_forest"), ("Transpiration grassland", "actTransTotal_grasslands"),
                   ("Transpiration paddy", "actTransTotal_paddy"), ("Transpiration non-paddy", "actTransTotal_nonpaddy"),
                   ("Bare soil", "sum_actBareSoilEvap"), ("Interception", "sum_interceptEvap"),
                   ("Open water + pond", "sum_openWaterEvap"), ("Snow", "snowEvap"), ("Irrigation losses", "addtoevapotrans")],
          "Water bodies": [("Lakes/reservoirs", "EvapWaterBodyM"), ("Small lakes", "smallevapWaterBody"), ("Channels", "EvapoChannel")]}
    GLACIER = [("Glacier melt", "GlacierMelt"), ("Rain on glacier", "GlacierRain")]
    SOURCES = ["Lake", "Res", "Channel", "GW", "Desal", "Lift", "wwt"]
    SECTORS = ["Irrigation", "Domestic", "Industry", "Livestock"]
    use = {(src, sec): flux(f"{src}_{sec}") for src in SOURCES for sec in SECTORS
           if on["sectorSourceAbstractionFractions"] and f"{src}_{sec}" in df.columns}
    withdrawal = flux("act_irrWithdrawal") + flux("act_nonIrrWithdrawal")

    rows = [["Water cycle (overall, GUI)", "balance", total_input, total_output, dstorage,
             total_input - total_output - dstorage, "inputs, outputs and storages of the GUI circle"]]
    for name in ["Total", "Interception", "Soil (+interception, pond)", "Soil layer 1", "Soil layer 2", "Soil layer 3"] + SOILLC + [
            gwname] + GWLAYERS + ["Runoff concentration"]:
        if name in parts:
            rows.append(part_row(name, parts[name]))
    et_terms = [(l, c) for lst in ET.values() for l, c in lst if c in df.columns and flux(c) > 0]
    et_tot, et_sum = flux("ET_all"), sum(flux(c) for _, c in et_terms)
    rows.append(["Evapotranspiration", "composition", et_tot, et_sum, 0., et_tot - et_sum, ", ".join(l for l, _ in et_terms)])
    if "sum_totalPotET" in df.columns:
        for nm, pot, act in [("ET: potential vs actual (land)", "sum_totalPotET", "totalET"),
                             ("Transpiration: potential vs actual", "sum_potTranspiration", "sum_actTransTotal")]:
            rows.append([nm, "potential", flux(pot), flux(act), np.nan, np.nan,
                         f"deficit {flux(pot) - flux(act):.2f} mm" + (f" = {100 * (1 - flux(act) / flux(pot)):.1f} % of the potential"
                                                                      if flux(pot) else "")])
    st_terms = [(l, change(c)) for l, c in parts["Total"]["S"] if c in df.columns]
    st_inc, st_dec = sum(v for _, v in st_terms if v > 0), -sum(v for _, v in st_terms if v < 0)
    rows.append(["Storage change (increase vs decrease)", "storage", st_dec, st_inc, st_inc - st_dec, np.nan,
                 ", ".join(f"{l} {v:+.2f}" for l, v in st_terms)])
    if snowname in parts:
        rows.append(part_row(snowname, parts[snowname]))
    if "Glacier" in parts:
        r = part_row("Glacier", parts["Glacier"])
        r[1] = "implied storage"
        rows.append(r)
    elif on["includeGlaciers"]:
        gl = [(l, flux(c)) for l, c in GLACIER]
        rows.append(["Glacier", "composition", flux("glacier"), sum(v for _, v in gl), 0., flux("glacier") - sum(v for _, v in gl),
                     ", ".join(f"{l} {v:.2f}" for l, v in gl)])
    for name in ["Lakes/reservoirs", "Lakes", "Reservoirs", "Channels (+small lakes)", "Routing (channels + lakes)",
                 "Water demand"] + DEMANDPARTS + ["Wastewater"]:
        if name in parts:
            rows.append(part_row(name, parts[name]))
    if use:
        rows.append(["Water use: source x sector", "composition", withdrawal, sum(use.values()), 0., withdrawal - sum(use.values()),
                     ", ".join(sorted({src for src, _ in use})) + " x " + ", ".join(SECTORS)])

    summary = pd.DataFrame(rows, columns=["circle", "kind", "In mm", "Out mm", "dS mm", "balance error mm", "terms"])
    summary.insert(6, "In mm/yr", summary["In mm"] / nyears)
    with np.errstate(divide="ignore", invalid="ignore"):
        summary.insert(7, "error / In", summary["balance error mm"] / summary["In mm"])
    nobal = summary["kind"].isin(list(REASON))
    others = pd.DataFrame([[c, k, REASON[k], t] for c, k, t in zip(summary.circle[nobal], summary.kind[nobal], summary.terms[nobal])]
                          + [[c, "not drawn", r, ""] for c, r in excluded],
                          columns=["circle", "kind", "why not in the 1st list", "info"])
    summary = summary[~nobal].reset_index(drop=True)
    summary.insert(8, "error mm/yr", summary["balance error mm"] / nyears)
    # passed: |error / In| <= threshold (error / In is nan only for In = 0 and error = 0)
    # or the absolute error for one year |error mm/yr| <= abs_threshold
    rel = summary["error / In"]
    passed = ~(rel.abs() > threshold)
    if abs_threshold is not None:
        passed = passed | (summary["error mm/yr"].abs() <= abs_threshold)
    summary.insert(9, "passed", passed)
    failed = summary[~summary["passed"]]
    lon, lat = stations.loc[station, "lon"], stations.loc[station, "lat"]
    # days: days of the balance (the first row of the csv is the baseline), rundays: simulated days (from the dates)
    return dict(summary=summary, others=others, failed=failed, days=ndays, rundays=ndays + 1, station=station, lon=lon, lat=lat,
                area_km2=area / 1e6,
                period=f"{df.index[0] + pd.Timedelta(days=1):%d/%m/%Y} to {days[-1]:%d/%m/%Y}" if len(days) else "",
                title=title, settings_file=settings_file, threshold=threshold, abs_threshold=abs_threshold)


def failed_text(res):
    """the circles above the threshold in one line, e.g. 'Groundwater (MODFLOW + coupling) error/In = -7.0e-04 (-0.8252 mm)'"""
    f = res["failed"]
    return "; ".join(f"{c} error/In = {r:+.1e} ({e:+.4f} mm, {y:+.4f} mm/yr)" for c, r, e, y in
                     zip(f["circle"], f["error / In"], f["balance error mm"], f["error mm/yr"]))


def report(res):
    """text as in cell 07: header, the 1st list (failed circles marked with <--), the 2nd list"""
    s = res["summary"].copy()
    s["mark"] = np.where(s["passed"], "", "<-- above threshold")
    absth = "" if res.get("abs_threshold") is None else f" and |error| > {res['abs_threshold']:g} mm/yr"
    head = (f"{res['title']} | station {res['station']} lon {res['lon']:.4f} lat {res['lat']:.4f} | {res['area_km2']:.1f} km2 | "
            f"{res['period']} ({res['days']} days)\nthreshold |error / In| = {res['threshold']:g}{absth}: "
            f"{len(res['failed'])} of {len(s)} circle(s) above it")
    fmt = {"In mm": "{:.2f}".format, "Out mm": "{:.2f}".format, "dS mm": "{:.2f}".format, "balance error mm": "{:.4f}".format,
           "In mm/yr": "{:.1f}".format, "error / In": "{:.1e}".format, "error mm/yr": "{:.4f}".format}
    cols = ["circle", "kind", "In mm", "Out mm", "dS mm", "balance error mm", "In mm/yr", "error / In", "error mm/yr", "mark"]
    with pd.option_context("display.width", 250, "display.max_colwidth", 120):
        t1 = s[cols].to_string(index=False, formatters=fmt)
        t2 = res["others"][["circle", "kind", "why not in the 1st list"]].to_string(index=False)
    return f"{head}\n{t1}\ncircles not in the list above:\n{t2}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    res = balance(sys.argv[1], threshold=float(sys.argv[2]) if len(sys.argv) > 2 else 1e-3,
                  abs_threshold=float(sys.argv[3]) if len(sys.argv) > 3 else None)
    print(report(res))
    sys.exit(1 if len(res["failed"]) else 0)
