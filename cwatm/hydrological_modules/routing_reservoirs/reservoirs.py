# -------------------------------------------------------------------------
# Name:        Reservoirs
# Purpose:     Reservoir routine (approach of LISFLOOD): storage limits, outflows, Excel values,
#              daily release ratio (netCDF or Excel) and the reservoir outflow of each routing substep
#
# Author:      PB, DF
# Created:     06/11/2026 (from lakes_reservoirs.py)
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
from cwatm.management_modules.caching import readexcel, excelsheetnames


def reservoir_info_rows(var):
    """
    Rows of the Excel sheet Reservoirs (var.reservoir_info) with a water body in the model and its index
    (option reservoir_add_info_in_Excel; empty list if the option is off)

    :param var: model variables (self.var)
    :return: list of (row, index in the compressed lake/reservoir arrays)
    """
    rows = []
    if 'reservoir_add_info_in_Excel' in option:
        if checkOption('reservoir_add_info_in_Excel'):
            for info in var.reservoir_info:
                resindex = np.where(var.waterBodyID_C == int(info[0]))[0]
                # test if reservoir is found -> later on make a new one
                if resindex.size > 0:
                    rows.append((info, resindex.tolist()[0]))
    return rows


class reservoirs(object):
    """
    Reservoirs

    Using the approach of LISFLOOD (LISFLOOD manual Annex 1: Burek et al. 2013):
    the outflow depends on the filling of the reservoir between the conservative, normal and flood storage limit.
    Optional: daily release ratio from netCDF (Reservoir_releases) or Excel (reservoir_releases_in_Excel_settings),
    outflow limit (limit_to_resOutflows), values from the Excel sheet Reservoirs, transfers (reservoir_transfers.py).

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    reservoir_info                       List          Values per reservoir from Excel sheet Reservoirs                        --   
    waterBodyID_C                        Array         ID of the waterbody - compressed                                        --   
    compress_LR                          Array         boolean map as mask map for compressing lake/reservoir                  --   
    decompress_LR                        Array         boolean map as mask map for decompressing lake/reservoir                --   
    resVolumeC                           Array         compressed map of reservoir volume                                      Mm3  
    waterBodyTypC                        Array         water body types 3 reservoirs and lakes (used as reservoirs but before  --   
    lakeDis0C                            Array         average discharge at the outlet of a lake/reservoir                     m3 s-
    reservoirStorage                     Array         Storage of reservoirs                                                   m3   
    lakeNewC                             Array         True if a water body is not in the init file (new) -> default values    bool 
    conLimitC                            Array         Reservoir calculation: conservativeStorageLimit                         --   
    normLimitC                           Array         Reservoir calculation: normalStorageLimit                               --   
    floodLimitC                          Array         Reservoir calculation:                                                  --   
    minQC                                Array         Reservoir calculation:                                                  m3 s-
    normQC                               Array         Reservoir calculation:                                                  m3 s-
    nondmgQC                             Array         Reservoir calculation:                                                  m3 s-
    adjust_Normal_FloodC                 Array         Reservoir calculation:                                                  --   
    norm_floodLimitC                     Array         Reservoir calculation:                                                  --   
    deltaO                               Array         Reservoir calculation:                                                  m3 s-
    deltaLN                              Array         Reservoir calculation:                                                  --   
    deltaLF                              Array         Reservoir calculation:                                                  --   
    deltaNFL                             Array         Reservoir calculation:                                                  --   
    reservoirFillC                       Array         actual filling fraction of a reservoir                                  --   
    reservoirOutflowLimitC               Array         limit fill fraction for reservoir outflow (limit_to_resOutflows)        --   
    reservoir_releases_excel_option      Flag          If Excel file is used for addition reservoirs, watertransfer, release   bool 
    reservoir_releases_netcdf_option     Flag          True if Reservoir_releases (netCDF) is in the settings file             bool 
    reservoir_transfers_option           Flag          True if reservoir_transfers = True (Excel sheet Reservoir_transfers)    bool 
    reservoir_releases                   Array         Release of reservoirs                                                   --   
    lakeResStorage_release_ratio         Array         daily release ration for reservoirs                                     --   
    lakeResStorage_release_ratioC        Array         daily release ration for reservoirs - compressed                        --   
    resEvapWaterBodyC                    Array         evaporation from reservoirs                                             m    
    InvDtSec                             Array         inversere of seconds per timestep (default 1/86400)                     1 s-1
    dtRouting                            Array         number of seconds per routing timestep                                  s    
    evapWaterBodyC                       Array         Compressed version of EvapWaterBodyM                                    m    
    noRoutingSteps                       Number        Number of routing step - how often the subroutine is run during a day   --   
    sumResEvapWaterBodyC                 Array         sum of all routingsteps of evaporation from lakes and reservoirs   - s  --   
    reservoirStorageM3C                  Array         Initial reservoir fill (fraction of total storage, [-]) (AI)            --   
    reservoir_supply                     Array                                                                                 --   
    ===================================  ==========    ======================================================================  =====

    **Functions**
    """

    def __init__(self, model, transfers):
        self.var = model.var
        self.model = model
        # reservoir transfers (reservoir_transfers.py), also used by the coordinator lakes_reservoirs
        self.transfers = transfers

    def read_releases(self, xl_settings_file_path):
        """
        Daily release ratio of the reservoirs from the Excel sheets Reservoirs_downstream and Reservoirs_supply
        (-1 = no value)

        :param xl_settings_file_path: Excel settings file
        :return: reservoir_release, reservoir_supply (366 days x water bodies)
        """
        df = readexcel(xl_settings_file_path, 'Reservoirs_downstream')
        waterBodyID_C_tolist = self.var.waterBodyID_C.tolist()

        reservoir_release = [[-1 for i in self.var.waterBodyID_C] for i in range(366)]
        for res in list(df)[2:]:
            if res in waterBodyID_C_tolist:
                res_index = waterBodyID_C_tolist.index(int(float(res)))

                for day in range(366):
                    reservoir_release[day][res_index] = df[res][day]

        reservoir_supply = [[-1 for i in self.var.waterBodyID_C] for i in range(366)]
        # reservoir_release.copy()
        # only the sheet names are checked - before all sheets were parsed for this test
        if 'Reservoirs_supply' in excelsheetnames(xl_settings_file_path):
            df2 = readexcel(xl_settings_file_path, 'Reservoirs_supply')
            for res in list(df2)[2:]:
                if res in waterBodyID_C_tolist:
                    res_index = waterBodyID_C_tolist.index(int(float(res)))

                    for day in range(366):
                        reservoir_supply[day][res_index] = df2[res][day]
        else:
            reservoir_supply = reservoir_release.copy()

        return reservoir_release, reservoir_supply

    def initial(self):
        """
        Initial part of the reservoirs: storage limits, outflows, Excel values, start storage, releases, transfers
        (needs lakeNewC from lakes_reservoirs.initial_lakes)
        """
        #  Conservative, normal and flood storage limit (fraction of total storage, [-])
        self.var.conLimitC = np.compress(self.var.compress_LR, loadmap('conservativeStorageLimit') + globals.inZero)
        self.var.normLimitC = np.compress(self.var.compress_LR, loadmap('normalStorageLimit') + globals.inZero)
        self.var.floodLimitC = np.compress(self.var.compress_LR, loadmap('floodStorageLimit') + globals.inZero)

        # Minimum, Normal and Non-damaging reservoir outflow  (fraction of average discharge, [-])
        # multiplied with the given discharge at the outlet from Hydrolakes database
        self.var.minQC = np.compress(self.var.compress_LR, loadmap('MinOutflowQ') + globals.inZero) * self.var.lakeDis0C
        self.var.normQC = np.compress(self.var.compress_LR, loadmap('NormalOutflowQ') + globals.inZero) * self.var.lakeDis0C
        self.var.nondmgQC = np.compress(self.var.compress_LR, loadmap('NonDamagingOutflowQ') + globals.inZero) * self.var.lakeDis0C
        self.var.adjust_Normal_FloodC = np.compress(self.var.compress_LR,loadmap('adjust_Normal_Flood') + globals.inZero)
        # MODIFIED DOR FRIDMAN: limit res. outflows to reservoir with water level > limit_to_resOutflows
        # limit_to_resOutflows is defined relative to res. volume - loaded once, compressed to lakes/reservoirs
        self.var.reservoirOutflowLimitC = None
        if "limit_to_resOutflows" in binding:
            self.var.reservoirOutflowLimitC = np.compress(self.var.compress_LR, globals.inZero + loadmap('limit_to_resOutflows'))

        # Excel sheet Reservoirs: values > 0 replace the values of the maps (reservoir_add_info_in_Excel)
        for info, resindex in reservoir_info_rows(self.var):
            if float(info[12]) > 0: self.var.conLimitC[resindex] = float(info[12])
            if float(info[13]) > 0: self.var.normLimitC[resindex] = float(info[13])
            if float(info[14]) > 0: self.var.floodLimitC[resindex] = float(info[14])
            if float(info[15]) > 0: self.var.adjust_Normal_FloodC[resindex] = float(info[15])

            if float(info[16]) > 0: self.var.minQC[resindex] = float(info[16]) * self.var.lakeDis0C[resindex]
            if float(info[17]) > 0: self.var.normQC[resindex] = float(info[17]) * self.var.lakeDis0C[resindex]
            if float(info[18]) > 0: self.var.nondmgQC[resindex] = float(info[18]) * self.var.lakeDis0C[resindex]

        self.var.norm_floodLimitC = self.var.normLimitC + self.var.adjust_Normal_FloodC * (
                    self.var.floodLimitC - self.var.normLimitC)

        # Repeatedly used expressions in reservoirs routine
        self.var.deltaO = self.var.normQC - self.var.minQC
        self.var.deltaLN = self.var.normLimitC - 2 * self.var.conLimitC
        self.var.deltaLF = self.var.floodLimitC - self.var.normLimitC
        self.var.deltaNFL = self.var.floodLimitC - self.var.norm_floodLimitC

        reservoirStorageIni = self.var.load_initial("reservoirStorage")

        # Initial reservoir fill (fraction of total storage, [-])
        self.var.reservoirFillC = self.var.normLimitC.copy()
        self.var.reservoirStorageM3C = self.var.reservoirFillC * self.var.resVolumeC
        # set initial fill of distribution and fake reservoirs to zero (res. type-4 and 5) - only if not loaded
        self.var.reservoirStorageM3C = np.where((self.var.waterBodyTypC > 3) & (self.var.waterBodyTypC < 6), 0., self.var.reservoirStorageM3C)

        if isinstance(reservoirStorageIni, np.ndarray):
            loadres = np.compress(self.var.compress_LR, reservoirStorageIni)
            # new water bodies (lakeNewC from initial_lakes) keep the default, the others the saved storage - also 0
            self.var.reservoirStorageM3C = np.where(self.var.lakeNewC, self.var.reservoirStorageM3C, loadres)

        self.var.reservoirFillC = self.var.reservoirStorageM3C / self.var.resVolumeC

        self.var.reservoir_releases_excel_option = False
        # reservoir releases from netCDF (Reservoir_releases): checked once, used in each routing substep
        self.var.reservoir_releases_netcdf_option = 'Reservoir_releases' in binding
        if checkOption('reservoir_releases_in_Excel_settings', True):
            if 'Excel_settings_file' in binding:
                self.var.reservoir_releases_excel_option = True
                xl_settings_file_path = cbinding('Excel_settings_file')
                self.var.reservoir_releases, self.var.reservoir_supply = self.read_releases(xl_settings_file_path)

                self.var.reservoir_releases = np.array(self.var.reservoir_releases)
                self.var.reservoir_supply = np.array(self.var.reservoir_supply)

        # reservoir transfers: daily sums, option, year and check of givers/receivers/rules
        self.transfers.initial()

    def dynamic(self):
        """
        Daily release ratio of the reservoirs (netCDF Reservoir_releases or Excel sheet Reservoirs_downstream)

        Reservoir_releases holds variables for different reservoir operations, each with 366 timesteps.
        The value of the variable at the reservoir is the maximum fraction of available storage to be
        released for the associated operation.
        Downstream release is the water released downstream into the river.
        This is overridden only in flooding conditions.
        """
        if self.var.reservoir_releases_netcdf_option:
            day_of_year = dateVar['currDate'].timetuple().tm_yday
            self.var.lakeResStorage_release_ratio = readnetcdf2(
                'Reservoir_releases', day_of_year,
                useDaily='DOY', value='Downstream release')

            self.var.lakeResStorage_release_ratioC = np.compress(self.var.compress_LR,
                                                                 self.var.lakeResStorage_release_ratio)

        elif self.var.reservoir_releases_excel_option:
            self.var.lakeResStorage_release_ratioC = self.var.reservoir_releases[dateVar['doy']-1]

    def route(self, inflowC, NoRoutingExecuted):
        """
        Reservoir outflow of one routing substep

        :param inflowC: inflow to reservoirs [m3] per subtime step
        :param NoRoutingExecuted: actual number of routing substep
        :return: qResOutM3DtC - reservoir outflow in [m3] per subtime step
        """

        # ************************************************************
        # ***** Reservoirs
        # ************************************************************

        # QResInM3Dt = inflowC
        # Reservoir inflow in [m3] per timestep
        #self.var.reservoirStorageM3C += inflowC
        # New reservoir storage [m3] = plus inflow for this sub step
        # if reservoirtype = 4 -> no inflow
        self.var.reservoirStorageM3C = np.where(self.var.waterBodyTypC == 4, self.var.reservoirStorageM3C, self.var.reservoirStorageM3C + inflowC)

        # check that reservoir storage - evaporation > 0
        self.var.resEvapWaterBodyC = np.where(self.var.reservoirStorageM3C - self.var.evapWaterBodyC > 0.,
                                              self.var.evapWaterBodyC, self.var.reservoirStorageM3C)

        # Reservoir type 5 is only in for water transfer without a reservoir retention without ET
        self.var.resEvapWaterBodyC = np.where(self.var.waterBodyTypC == 5, 0., self.var.resEvapWaterBodyC)
        self.var.sumResEvapWaterBodyC += self.var.resEvapWaterBodyC

        self.var.reservoirStorageM3C = self.var.reservoirStorageM3C - self.var.resEvapWaterBodyC

        self.var.reservoirFillC = self.var.reservoirStorageM3C / self.var.resVolumeC
        # New reservoir fill [-]

        # MODIFIED DOR FRIDMAN
        # limit res. outflows to reservoir with water level > limit_to_resOutflows
        # limit_to_resOutflows is defined relative to res. Volume
        if self.var.reservoirOutflowLimitC is not None:
            # Create mask for limit out flow: 1 allow out flow (in case fill > limit)
            reservoirOutflowLimitMask = np.where(self.var.reservoirOutflowLimitC < self.var.reservoirFillC, 1, 0)
        else:
            reservoirOutflowLimitMask = 1

        reservoirOutflow1 = np.minimum(self.var.minQC, self.var.reservoirStorageM3C * self.var.InvDtSec)
        # Reservoir outflow [m3/s] if ReservoirFill is nearing absolute minimum.

        reservoirOutflow2 = self.var.minQC + self.var.deltaO * (
                    self.var.reservoirFillC - 2 * self.var.conLimitC) / self.var.deltaLN
        # 2*ConservativeStorageLimit
        # Reservoir outflow [m3/s] if NormalStorageLimit <= ReservoirFill > 2*ConservativeStorageLimit

        reservoirOutflow3 = self.var.normQC + (
                    (self.var.reservoirFillC - self.var.norm_floodLimitC) / self.var.deltaNFL) * (
                                        self.var.nondmgQC - self.var.normQC)
        # Reservoir outflow [m3/s] if FloodStorageLimit le ReservoirFill gt NormalStorageLimit
        inflowCQ = inflowC * self.var.InvDtSec * self.var.noRoutingSteps

        temp = np.minimum(self.var.nondmgQC,np.maximum(inflowCQ, self.var.normQC))
        reservoirOutflow4 = np.maximum(
            (self.var.reservoirFillC - self.var.floodLimitC - 0.01) * self.var.resVolumeC * self.var.InvDtSec, temp)

        # Reservoir outflow [m3/s] if ReservoirFill gt FloodStorageLimit
        # Depending on ReservoirFill the reservoir outflow equals ReservoirOutflow1, ReservoirOutflow2,
        # ReservoirOutflow3 or ReservoirOutflow4

        reservoirOutflow = reservoirOutflow1.copy()

        reservoirOutflow = np.where(self.var.reservoirFillC > 2 * self.var.conLimitC, reservoirOutflow2,
                                    reservoirOutflow)
        reservoirOutflow = np.where(self.var.reservoirFillC > self.var.normLimitC, self.var.normQC,
                                    reservoirOutflow)
        reservoirOutflow = np.where(self.var.reservoirFillC > self.var.norm_floodLimitC, reservoirOutflow3,
                                    reservoirOutflow)
        reservoirOutflow = np.where(self.var.reservoirFillC > self.var.floodLimitC, reservoirOutflow4,
                                    reservoirOutflow)

        temp = np.minimum(reservoirOutflow, np.maximum(inflowCQ, self.var.normQC))

        reservoirOutflow = np.where((reservoirOutflow > 1.2 * inflowCQ) &
                                    (reservoirOutflow > self.var.normQC) &
                                    (self.var.reservoirFillC < self.var.floodLimitC), temp, reservoirOutflow)

        # Reservoir_releases holds variables for different reservoir operations, each with 366 timesteps.
        # The value of the variable at the reservoir is the maximum fraction of available storage to be
        # released for the associated operation.
        # Downstream release is the water released downstream into the river.
        # This is overridden only in flooding conditions.

        if self.var.reservoir_releases_netcdf_option:
            reservoirOutflow = np.where(self.var.reservoirFillC > self.var.floodLimitC, reservoirOutflow,
                                        np.where(self.var.lakeResStorage_release_ratioC > 0,
                                        self.var.lakeResStorage_release_ratioC * self.var.reservoirStorageM3C *
                                        self.var.InvDtSec, 0))

        if self.var.reservoir_releases_excel_option:
            reservoirOutflow = np.where(self.var.reservoirFillC > self.var.floodLimitC, reservoirOutflow,
                                        np.where(self.var.lakeResStorage_release_ratioC > -1,
                                        self.var.lakeResStorage_release_ratioC * self.var.reservoirStorageM3C *
                                        self.var.InvDtSec, reservoirOutflow))

        # Apply reservoirOutflowLimitMask to limit resOutflows based on storagre relative to threshold volume
        # This may override the reservoir_releases behaviour - ATTENTION FROM MIKHAIL/DOR
        reservoirOutflow = reservoirOutflow * reservoirOutflowLimitMask

        qResOutM3DtC = reservoirOutflow * self.var.dtRouting

        # Reservoir outflow in [m3] per sub step
        qResOutM3DtC = np.where(self.var.reservoirStorageM3C - qResOutM3DtC > 0., qResOutM3DtC,
                                self.var.reservoirStorageM3C)
        # check if storage would go < 0 if outflow is used
        qResOutM3DtC = np.maximum(qResOutM3DtC, self.var.reservoirStorageM3C - self.var.resVolumeC)
        # Check to prevent reservoir storage from exceeding total capacity
        # for watertyp 4: In = Out (inflow passes through, storage only from wastewater/transfers)
        qResOutM3DtC = np.where(self.var.waterBodyTypC == 4, inflowC, qResOutM3DtC)
        # for watertyp 5: In = Out. (Outflow = inflow + water that is transferred)
        qResOutM3DtC = np.where(self.var.waterBodyTypC == 5, self.var.reservoirStorageM3C, qResOutM3DtC)
        # bugfix: the pass-through of type 4 was never added to storage
        self.var.reservoirStorageM3C -= np.where(self.var.waterBodyTypC == 4, 0., qResOutM3DtC)

        # Transfer water between reservoirs (rules 1-6, reservoir_transfers.py)
        if self.var.reservoir_transfers_option:
            qResOutM3DtC = self.transfers.route(qResOutM3DtC)

        # New reservoir storage [m3]
        self.var.reservoirStorageM3C = np.maximum(0.0, self.var.reservoirStorageM3C)
        # New reservoir fill
        self.var.reservoirFillC = self.var.reservoirStorageM3C / self.var.resVolumeC
        if self.var.noRoutingSteps == (NoRoutingExecuted + 1):
            np.put(self.var.reservoirStorage, self.var.decompress_LR, self.var.reservoirStorageM3C)

        return qResOutM3DtC
