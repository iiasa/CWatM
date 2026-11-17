# -------------------------------------------------------------------------
# Name:        Lakes
# Purpose:     Lakes with the Modified Puls approach: start values (also warm start) and the lake routine
#              of each routing substep (wetlands = type 6 via wetlands.py)
#
# Author:      PB
# Created:     06/11/2026 (from lakes_reservoirs.py)
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
from cwatm.hydrological_modules.routing_reservoirs.puls import puls_factor, puls_outflow, start_volume


class lakes(object):
    """
    Lakes (water body type 1, and the lake routine of all water bodies)

    Using the **Modified Puls approach** to calculate retention of a lake
    (LISFLOOD manual Annex 3: Burek et al. 2013; Maniak, p.331ff):
    1. storage volume increases proportionally to elevation: S = A * H
    2. outflow follows a parabolic weir relationship: Q = a * H**2
    (Qin1 + Qin2)/2 - (Qout1 + Qout2)/2 = (S2 - S1)/dt  ->  Q = (-LakeFactor + sqrt(LakeFactor**2 + 2*SI))**2

    The lake routine runs for all water bodies (in parallel to the reservoir routine);
    lakes_reservoirs.py selects the result by the water body type.

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    compress_LR                          Array         boolean map as mask map for compressing lake/reservoir                  --   
    decompress_LR                        Array         boolean map as mask map for decompressing lake/reservoir                --   
    dtRouting                            Array         number of seconds per routing timestep                                  s    
    evapWaterBodyC                       Array         Compressed version of EvapWaterBodyM                                    m    
    lakeAC                               Array         compressed map of parameter of channel width, gravity and weir coeffic  --   
    lakeAreaC                            Array         compressed map of the area of each lake/reservoir                       m2   
    lakeDis0C                            Array         average discharge at the outlet of a lake/reservoir                     m3 s-
    lakeEvapWaterBodyC                   Array         Evaporation from lakes and reservoirs                                   m3   
    lakeFactor                           Array         factor for the Modified Puls approach to calculate retention of the la  --   
    lakeFactorSqr                        Array         square root factor for the Modified Puls approach to calculate retenti  --   
    lakeIn                               Array         Inflow into lakes                                                       m3   
    lakeInflow                           Array         Inflow into lakes                                                       m3   
    lakeInflowOldC                       Array         inflow to the lake from previous days                                   m3   
    lakeLevel                            Array         Waterlevel of lakes                                                     m    
    lakeLevelC                           Array         compressed map of lake level                                            m    
    lakeNewC                             Array         True if a water body is not in the init file (new) -> default values    bool 
    lakeOutflow                          Array         lake outflow - uncompressed  for all basin cells                        m3   
    lakeOutflowC                         Array         compressed map of lake outflow                                          m3 s-
    lakeStorage                          Array         Storage volume of lakes                                                 m3   
    lakeStorageBalance                   Array         water balance storage of lakes (in-out-evap), saved for warm start      m3   
    lakeStorageC                         Array                                                                                 --   
    lakeVolume                           Array         volume of lakes                                                         m3   
    lakeVolumeM3C                        Array         compressed map of lake volume                                           m3   
    noRoutingSteps                       Number        Number of routing step - how often the subroutine is run during a day   --   
    saveInit                             Flag          If true initial conditions are saved                                    bool 
    sumLakeEvapWaterBodyC                Array                                                                                 --   
    ===================================  ==========    ======================================================================  =====

    **Functions**
    """

    def __init__(self, model, wetlands):
        self.var = model.var
        self.model = model
        # wetlands (wetlands.py): outflow of water body type 6
        self.wetlands = wetlands

    def initial(self):
        """
        Initial part of the lakes: Puls factor, start values or values of the init file (warm start), start outflow
        """

        # self_.var.lakeInflowOldC = np.bincount(self_.var.downstruct, weights=self.var.ChanQ)[self.var.LakeIndex]

        # self.var.lakeInflowOldC = np.compress(self_.var.compress_LR, self_.var.chanQKin)
        # for Modified Puls Method the Q(inflow)1 has to be used.
        # It is assumed that this is the same as Q(inflow)2 for the first timestep
        # Does this work in forecasting mode?

        self.var.lakeFactor, self.var.lakeFactorSqr = puls_factor(self.var.lakeAreaC, self.var.dtRouting, self.var.lakeAC)
        # for faster calculation inside dynamic section

        # initial values from the init file (warm start)
        lakeInflowIni = self.var.load_initial("lakeInflow")  # inflow in m3/s estimate
        lakeVolumeIni = self.var.load_initial("lakeStorage")
        lakeOutflowIni = self.var.load_initial("lakeOutflow")

        # a water body is new (not in the init file, e.g. from Excel) if all its saved values are 0
        # (the lake volume alone is not enough: the lake routine of a reservoir runs in parallel and
        #  can be emptied to exactly 0 by reservoir abstraction -> max(0, SI) in lakes.route)
        # new water bodies get the default values, the others keep the saved values - also if they are 0
        if isinstance(lakeVolumeIni, np.ndarray):
            lakeVolumeIniC = np.compress(self.var.compress_LR, lakeVolumeIni)
            self.var.lakeNewC = lakeVolumeIniC == 0.
            for ini in (lakeInflowIni, lakeOutflowIni, self.var.load_initial("reservoirStorage")):
                if isinstance(ini, np.ndarray):
                    self.var.lakeNewC &= np.compress(self.var.compress_LR, ini) == 0.
        else:
            self.var.lakeNewC = np.full(self.var.lakeAreaC.shape, True)

        # for Modified Puls Method the Q(inflow)1 has to be used - default: average discharge
        self.var.lakeInflowOldC = self.var.lakeDis0C.copy()
        if isinstance(lakeInflowIni, np.ndarray):
            self.var.lakeInflowOldC = np.where(self.var.lakeNewC, self.var.lakeDis0C, np.compress(self.var.compress_LR, lakeInflowIni))

        # lake volume - default: level from average discharge (Q = a * H**2)
        self.var.lakeVolumeM3C = start_volume(self.var.lakeAreaC, self.var.lakeInflowOldC, self.var.lakeAC)
        if isinstance(lakeVolumeIni, np.ndarray):
            self.var.lakeVolumeM3C = np.where(self.var.lakeNewC, self.var.lakeVolumeM3C, lakeVolumeIniC)
        self.var.lakeStorageC = self.var.lakeVolumeM3C.copy()
        # water balance storage from the init file (= Puls volume - (Q - Qstart)*dt/2), new water bodies: = volume
        lakeStorageBalanceIni = self.var.load_initial("lakeStorageBalance")
        if isinstance(lakeStorageBalanceIni, np.ndarray):
            self.var.lakeStorageC = np.where(self.var.lakeNewC, self.var.lakeStorageC,
                                             np.compress(self.var.compress_LR, lakeStorageBalanceIni))



        lakeStorageIndicator = np.maximum(0.0, self.var.lakeVolumeM3C / self.var.dtRouting + 0.5 * self.var.lakeInflowOldC)
        # SI = S/dt + Q/2
        lakeOutflowC1 = puls_outflow(lakeStorageIndicator, self.var.lakeFactor, self.var.lakeFactorSqr)
        # solution of quadratic equation
        #  it is as easy as this because:
        # 1. storage volume is increase proportional to elevation
        #  2. Q= a *H **2.0  (if you choose Q= a *H **1.5 you have to solve the formula of Cardano)

        # wetlands (type 6): triangular shape, with variable area the outflow above the max level (wetlands.py)
        lakeOutflowC1 = self.wetlands.outflow(lakeStorageIndicator, lakeOutflowC1)

        # lake level is average lake level = 1/2 of  max level for a triangular lake
        self.var.lakeLevelC = self.var.lakeVolumeM3C / self.var.lakeAreaC
        np.put(self.var.lakeLevel, self.var.decompress_LR, self.var.lakeLevelC)

        # lake outflow - default: from the Puls formula
        self.var.lakeOutflowC = lakeOutflowC1.copy()
        if isinstance(lakeOutflowIni, np.ndarray):
            self.var.lakeOutflowC = np.where(self.var.lakeNewC, lakeOutflowC1, np.compress(self.var.compress_LR, lakeOutflowIni))

    def route(self, inflowC, NoRoutingExecuted):
        """
        Lake routine to calculate lake outflow of one routing substep

        :param inflowC: inflow to lakes and reservoirs [m3]
        :param NoRoutingExecuted: actual number of routing substep
        :return: QLakeOutM3DtC - lake outflow in [m3] per subtime step
        """

        # ************************************************************
        # ***** LAKE
        # ************************************************************

        # Lake inflow in [m3/s]
        lakeInflowC = inflowC / self.var.dtRouting

        self.var.lakeIn = (lakeInflowC + self.var.lakeInflowOldC) * 0.5
        # for Modified Puls Method: (S2/dtime + Qout2/2) = (S1/dtime + Qout1/2) - Qout1 + (Qin1 + Qin2)/2
        #  here: (Qin1 + Qin2)/2

        self.var.lakeEvapWaterBodyC = np.minimum(self.var.evapWaterBodyC, np.maximum(self.var.lakeVolumeM3C, 0.))

        self.var.sumLakeEvapWaterBodyC += self.var.lakeEvapWaterBodyC
        self.var.lakeVolumeM3C = self.var.lakeVolumeM3C - self.var.lakeEvapWaterBodyC
        # lakestorage - evaporation from lakes

        self.var.lakeInflowOldC = lakeInflowC.copy()
        # Qin2 becomes Qin1 for the next time step [m3/s]

        lakeStorageIndicator = np.maximum(0.0, self.var.lakeVolumeM3C / self.var.dtRouting - 0.5 * self.var.lakeOutflowC + self.var.lakeIn)
        # here S1/dtime - Qout1/2 + LakeIn , so that is the right part of the equation above

        # calculation if var.waterBodyTyp = 1 and lake is assumed to be rectangular
        self.var.lakeOutflowC = puls_outflow(lakeStorageIndicator, self.var.lakeFactor, self.var.lakeFactorSqr)
        # wetlands (type 6): triangular shape, with variable area the outflow above the max level (wetlands.py)
        self.var.lakeOutflowC = self.wetlands.outflow(lakeStorageIndicator, self.var.lakeOutflowC)

        QLakeOutM3DtC = self.var.lakeOutflowC * self.var.dtRouting
        # Outflow in [m3] per timestep

        # New lake storage [m3] (assuming lake surface area equals bottom area)
        self.var.lakeVolumeM3C = (lakeStorageIndicator - self.var.lakeOutflowC * 0.5) * self.var.dtRouting
        # Lake storage

        self.var.lakeStorageC += self.var.lakeIn * self.var.dtRouting - QLakeOutM3DtC - self.var.lakeEvapWaterBodyC

        # lakelevel is average of the trigangular part + the rectangular part above
        self.var.lakeLevelC = self.var.lakeVolumeM3C / self.var.lakeAreaC

        if self.var.noRoutingSteps == (NoRoutingExecuted + 1):
            np.put(self.var.lakeLevel, self.var.decompress_LR, self.var.lakeLevelC)

        # values for the init file (warm start), last routing substep of the day
        if self.var.saveInit and (self.var.noRoutingSteps == (NoRoutingExecuted + 1)):
            np.put(self.var.lakeVolume, self.var.decompress_LR, self.var.lakeVolumeM3C)
            np.put(self.var.lakeInflow, self.var.decompress_LR, self.var.lakeInflowOldC)
            np.put(self.var.lakeOutflow, self.var.decompress_LR, self.var.lakeOutflowC)
            np.put(self.var.lakeStorageBalance, self.var.decompress_LR, self.var.lakeStorageC)

        # Water balance
        if self.var.noRoutingSteps == (NoRoutingExecuted + 1):
            np.put(self.var.lakeStorage, self.var.decompress_LR, self.var.lakeStorageC)

        return QLakeOutM3DtC
