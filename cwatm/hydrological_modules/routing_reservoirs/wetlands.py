# -------------------------------------------------------------------------
# Name:        Wetlands
# Purpose:     Wetlands (water body type 6): lakes with a triangular shape; optional a daily wet area
#              from the Excel sheet Wetlands and an outflow above the maximum water level
#
# Author:      PB
# Created:     06/11/2026 (from lakes_reservoirs.py)
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
from cwatm.management_modules.caching import readexcel
from cwatm.hydrological_modules.routing_reservoirs.puls import puls_factor, puls_outflow_triangular


class wetlands(object):
    """
    Wetlands (water body type 6)

    Wetlands are lakes (same compressed arrays, same Modified Puls routine) with a triangular shape:
    the outflow of type 6 is calculated with the triangular formula - always, also with a fixed area.
    With wetlands_variable_area = True the wet area changes every day (Excel sheet Wetlands, reference year)
    and the water above the maximum water level goes to the outflow.

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    wetlands_variable_area               Flag          True if wetlands_variable_area = True: daily wetland area from Excel    bool 
    wetland_area                         Array         variable area of wetlands per day                                       m2   
    wetland_maxlevel                     Array         maximum waterlevel of wetlands                                          m    
    includeType6                         Flag          True if there is a wetland of waterbody type 6 (after the Excel values) bool 
    compress_LR                          Array         boolean map as mask map for compressing lake/reservoir                  --   
    decompress_LR                        Array         boolean map as mask map for decompressing lake/reservoir                --   
    dtRouting                            Array         number of seconds per routing timestep                                  s    
    lakeAC                               Array         compressed map of parameter of channel width, gravity and weir coeffic  --   
    lakeArea                             Array         area of each lake/reservoir                                             m2   
    lakeAreaC                            Array         compressed map of the area of each lake/reservoir                       m2   
    lakeFactor                           Array         factor for the Modified Puls approach to calculate retention of the la  --   
    lakeFactorSqr                        Array         square root factor for the Modified Puls approach to calculate retenti  --   
    waterBodyID_C                        Array         ID of the waterbody - compressed                                        --   
    waterBodyTypC                        Array         water body types 3 reservoirs and lakes (used as reservoirs but before  --   
    ===================================  ==========    ======================================================================  =====

    **Functions**
    """

    def __init__(self, model):
        self.var = model.var
        self.model = model

    def read_area(self, xl_settings_file_path):
        """
        Daily wet area and maximum water level of the wetlands from the Excel sheet Wetlands

        :param xl_settings_file_path: Excel settings file
        :return: wetland_area (366 days x water bodies, -1 = no wetland data) [km2], wetland_maxlevel [m]
        """
        df = readexcel(xl_settings_file_path, 'Wetlands')
        waterBodyID_C_tolist = self.var.waterBodyID_C.tolist()

        # factor for the maximum level of wetlands: one value or a map (loaded once)
        wetland_factor = loadmap('wetland_maxlevel')
        if isinstance(wetland_factor, np.ndarray):
            wetland_factor = np.compress(self.var.compress_LR, wetland_factor)
        else:
            wetland_factor = np.full(len(self.var.waterBodyID_C), wetland_factor)

        # initialize wetlands for all lakes & reservoirs (-1 = no wetland data)
        wetland_area = np.full((366, len(self.var.waterBodyID_C)), -1.0)
        wetland_maxlevel = np.zeros(len(self.var.waterBodyID_C))
        # Excel sheet from column 5 ->
        for res in list(df)[5:]:
            if res in waterBodyID_C_tolist:
                wet_index = waterBodyID_C_tolist.index(int(float(res)))
                wetland_maxlevel[wet_index] = float(df[res][1]) * wetland_factor[wet_index]
                for day in range(366):
                    wetland_area[day, wet_index] = df[res][day+3]

        # each wetland (waterBodyTyp = 6) needs a max level and 366 daily areas > 0 in the Excel sheet Wetlands
        missing = (self.var.waterBodyTypC == 6) & ~(np.all(wetland_area > 0, axis=0) & (wetland_maxlevel > 0))
        if missing.any():
            msg = "Wetlands with variable area: missing or incomplete data in Excel sheet 'Wetlands' for water body No: "
            msg += ", ".join(str(i) for i in self.var.waterBodyID_C[missing]) + "\n"
            msg += "each wetland (waterBodyTyp = 6) needs a maximum level and 366 daily areas [km2] > 0\n"
            raise CWATMError(msg)

        return wetland_area, wetland_maxlevel

    def initial(self):
        """
        Initial part of the wetlands: flags, Excel sheet Wetlands and the wet area of the first day
        (called in lakes_reservoirs.initWaterbodies after the Excel values, before the reservoir volume uses lakeAreaC)
        """
        # Flag if wetlands (type 6) are used - without wetlands the outflow needs no replacement
        self.var.includeType6 = bool((self.var.waterBodyTypC == 6).any())

        self.var.wetlands_variable_area = checkOption('wetlands_variable_area', True)
        if self.var.wetlands_variable_area:
            if not 'Excel_settings_file' in binding:
                msg = "wetlands_variable_area = True needs Excel_settings_file with the sheet 'Wetlands'\n"
                raise CWATMError(msg)
            self.var.wetland_area, self.var.wetland_maxlevel = self.read_area(cbinding('Excel_settings_file'))

            # calculate the day of year for first lake area
            firstdoy = datetime.datetime(dateVar['currDate'].year, 1, 1)
            doy = (dateVar['currDate'] - firstdoy).days
            self.var.lakeAreaC = np.where(self.var.waterBodyTypC == 6, self.var.wetland_area[doy,:] * 1000000, self.var.lakeAreaC)
            # back to lakeArea , because it is used in routing_kinematic
            np.put(self.var.lakeArea, self.var.decompress_LR, self.var.lakeAreaC)

    def dynamic(self):
        """
        Wet area of the day (wetlands_variable_area) and the new Modified Puls factor
        """
        if self.var.wetlands_variable_area:
            # for wetland get new wetland area
            self.var.lakeAreaC = np.where(self.var.waterBodyTypC == 6, self.var.wetland_area[dateVar['doy']-1,:] * 1000000, self.var.lakeAreaC)
            # back to lakeArea , because it is used in routing_kinematic
            np.put(self.var.lakeArea, self.var.decompress_LR, self.var.lakeAreaC)
            # the Modified Puls factor depends on the lake area -> new factor with the new wetland area
            self.var.lakeFactor, self.var.lakeFactorSqr = puls_factor(self.var.lakeAreaC, self.var.dtRouting, self.var.lakeAC)

    def outflow(self, lakeStorageIndicator, lakeOutflowC):
        """
        Lake outflow with the wetland part: for type 6 the triangular formula and (wetlands_variable_area)
        the outflow above the maximum level (used at the start and in each routing substep)

        :param lakeStorageIndicator: storage indicator S/dt + Q/2 [m3/s]
        :param lakeOutflowC: outflow of a rectangular lake [m3/s]
        :return: lake outflow [m3/s]
        """
        if not self.var.includeType6:
            return lakeOutflowC

        # calculation if var.waterBodyTyp = 6 and lake is assumed to be triangular
        # and therefore the equation is a bit different
        lakeOutflowC2 = puls_outflow_triangular(lakeStorageIndicator, self.var.lakeFactor, self.var.lakeFactorSqr)
        # replace lakeOutflow if lake type = 6
        lakeOutflowC = np.where(self.var.waterBodyTypC == 6, lakeOutflowC2, lakeOutflowC)

        if self.var.wetlands_variable_area:
            # lakelevel should be at wetland_maxlevel (e.g. =1.0 m) -> rest goes to outflow
            # if lakelevel >= maxlevel sea level is kept constant and equation is changing:
            # outflow so that the level is at wetland_maxlevel after one routing step
            testlevel = ((lakeStorageIndicator - lakeOutflowC * 0.5) * self.var.dtRouting) / self.var.lakeAreaC
            lakeOutflowC3 = np.maximum(0, 2 * (lakeStorageIndicator - self.var.wetland_maxlevel * self.var.lakeAreaC / self.var.dtRouting))
            lakeOutflowC = np.where((self.var.waterBodyTypC == 6) & (testlevel >= self.var.wetland_maxlevel), lakeOutflowC3, lakeOutflowC)

        return lakeOutflowC
