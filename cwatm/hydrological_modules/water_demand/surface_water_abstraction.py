# -------------------------------------------------------------------------
# Name:        Waterdemand modules
# Purpose:     Surface water abstraction: desalination, channel, lift areas, wastewater reuse (restricted
#              reservoirs), lakes (big + small) and reservoirs (command areas, canal leakage).
#              Part of water_demand.py until 2026-11 (split).
#
# Author:      PB, MS, LG, JdeB, DF
# Created:     06/11/2026
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import numpy as np
from cwatm.management_modules import globals
from cwatm.management_modules.globals import dateVar, option
from cwatm.management_modules.replace_pcr import npareatotal, npareaaverage, npareamaximum, AreaIndex
from cwatm.management_modules.messages import CWATMError, CWATMWarning
from cwatm.management_modules.data_handling import (returnBool, binding, loadmap, divideValues, checkOption,
                                                     readnetcdf2)
from cwatm.hydrological_modules.water_demand.sector_demand import set_zero, split_sectors, pot_source


class waterdemand_surfacewater(object):
    """
    Surface water abstraction of the water demand.

    The sources are used in this order: desalination (only with sector fractions), channel of the cell, lift areas
    (channel water of the lift area), wastewater reuse from restricted reservoirs (buffer or command areas), big lakes
    and reservoirs in the buffer around them, small lakes, reservoirs in their command areas (domestic, livestock,
    industry first, then irrigation; canal leakage with Water_conveyance_efficiency < 1). Without sector fractions
    the surface water share of the demand (swAbstractionFraction) is taken from these sources. The rest is taken
    from groundwater (groundwater_abstraction.py).

    **Global variables**

    =========================================  ==========    ================================================================  =====
    Variable [self.var]                        Type          Description                                                       Unit 
    =========================================  ==========    ================================================================  =====
    abstractedLakeReservoirM3                  Array         Abstraction from lakes/reservoirs at the outlet cells             m3   
    abstractedLakeReservoirM3C                 Array         abstractedLakeReservoirM3 (compressed)                            m3   
    act_bigLakeResAbst                         Array         Abstraction from lakes and reservoirs at demand location          m    
    act_bigLakeResAbst_wwt                     Array         Wastewater reuse from lakes/reservoirs at demand location         m    
    act_channelAbst                            Array         Channel abstraction                                               m    
    act_channelAbstract_Lift                   Array         Channel abstraction in lift areas at the channel location         m    
    act_DesalWaterAbstractM                    Array         Desalinated water                                                 m    
    act_DesalWaterAbstractM3                   Array         Not used (always 0)                                               m3   
    act_lakeAbst                               Array         Abstraction from lakes at demand location                         m    
    act_ResAbst                                Array         Abstraction from reservoirs at demand location                    m    
    act_ResAbst_wwt                            Array         Wastewater reuse from restricted reservoirs at demand location    m    
    act_smallLakeResAbst                       Array         Abstractions from small lakes at demand location                  m    
    act_SurfaceWaterAbstract                   Array         Surface water abstraction                                         m    
    activate_irrigation_agents                 Flag          True if activate_irrigation_agents = True                         bool 
    allocSegments                              Array         Segments (e.g. catchments) for the average baseflow, cells > 0    --   
    AvlDesalM3                                 Array         Desalination capacity of the day                                  m3   
    canals                                     Array         Canal map (command area number); whole area if none               --   
    canals_wwt                                 Array         Canal map (command area number) for wastewater reuse              --   
    canalsArea                                 Array         Area of the canals of a command area                              m2   
    canalsArea_wwt                             Array         Area of the wastewater canals of a command area                   m2   
    canalsArea_wwtC                            Array         canalsArea_wwt at the reservoir outlets (compressed)              m2   
    canalsAreaC                                Array         canalsArea at the reservoir outlets (compressed)                  m2   
    canalsIndex                                Object        Index of canals for the area maximum of the leakage (AreaIndex)   --   
    cellArea                                   Array         Cell area                                                         m2   
    Channel_Domestic                           Array         Channel water for domestic                                        m    
    Channel_Industry                           Array         Channel water for industry                                        m    
    Channel_Irrigation                         Array         Channel water for irrigation                                      m    
    Channel_Livestock                          Array         Channel water for livestock                                       m    
    compress_LR                                Array         Boolean map: outlet cells of lakes/reservoirs (compress)          --   
    decompress_LR                              Array         Cell numbers of the lake/reservoir outlets (decompress)           --   
    Desal_Domestic                             Array         Desalinated water for domestic                                    m    
    Desal_Industry                             Array         Desalinated water for industry                                    m    
    Desal_Irrigation                           Array         Desalinated water for irrigation                                  m    
    Desal_Livestock                            Array         Desalinated water for livestock                                   m    
    desalAnnualCap                             Dict          Desalination capacity per year (Excel settings file)              m3   
    domesticDemand                             Array         Domestic water demand (withdrawal)                                m    
    fracVegCover                               Array         Land cover fractions (0 forest, 1 grassland, 2 paddy, ...)        frac 
    includeDesal                               Flag          True if includeDesalination = True                                bool 
    includeWastewater                          Flag          True if includeWastewater = True                                  bool 
    industryDemand                             Array         Industry water demand (withdrawal)                                m    
    InvDtSec                                   Array         Inverse of the seconds per time step (1/86400)                    1 s-1
    Lake_Domestic                              Array         Lake water for domestic                                           m    
    Lake_Industry                              Array         Lake water for industry                                           m    
    Lake_Irrigation                            Array         Lake water for irrigation                                         m    
    Lake_Livestock                             Array         Lake water for livestock                                          m    
    lakeResStorage                             Array         Lake + reservoir storage at the outlet cells                      m3   
    lakeResStorage_release_ratioC              Array         Excel settings: release ratio of the reservoirs (compressed)      --   
    lakeResStorageC                            Array         Lake + reservoir storage at the outlets (compressed)              m3   
    lakeStorageC                               Array         Lake and reservoir storage at the outlets (compressed)            m3   
    lakeVolumeM3C                              Array         Lake volume at the outlets (compressed)                           m3   
    leakage                                    Array         Canal leakage at the reservoir outlets (to groundwater/runoff)    m3   
    leakage_wwtC_daily                         Array         Canal leakage of the wastewater reservoirs (compressed)           m3   
    leakageC_daily                             Array         Canal leakage of the reservoirs (compressed)                      m3   
    leakageCanals_M                            Array         Canal leakage spread over the canal cells                         m    
    leakageCanalsC_M                           Array         Canal leakage per canal area at the outlets (compressed)          m    
    lift_command_areas                         Array         Lift areas (lift area number)                                     --   
    lift_command_areasIndex                    Object        Index of lift_command_areas for the area total (AreaIndex)        --   
    Lift_Domestic                              Array         Lift area channel water for domestic                              m    
    Lift_Industry                              Array         Lift area channel water for industry                              m    
    Lift_Irrigation                            Array         Lift area channel water for irrigation                            m    
    Lift_Livestock                             Array         Lift area channel water for livestock                             m    
    Lift_Other                                 Array         Lift water not attributed to a sector                             m    
    livestockDemand                            Array         Livestock water demand (withdrawal)                               m    
    load_command_areas                         Flag          True if reservoir_command_areas is used                           bool 
    load_command_areas_wwt                     Flag          True if reservoir_command_areas_restricted is used                bool 
    M3toM                                      Array         Coefficient m3 -> m (= InvCellArea)                               1 m-2
    modflow                                    Flag          True if modflow_coupling = True                                   bool 
    MtoM3                                      Array         Coefficient m -> m3 (= cellArea)                                  m2   
    nonIrrDemand                               Array         Non-irrigation demand (domestic + industry + livestock)           m    
    othAbstractionFraction_Desal_Domestic      Array         Input: share of the domestic demand from desalination             frac 
    othAbstractionFraction_Desal_Industry      Array         Input: share of the industry demand from desalination             frac 
    othAbstractionFraction_Desal_Irrigation    Array         Input: share of the irrigation demand from desalination           frac 
    othAbstractionFraction_Desal_Livestock     Array         Input: share of the livestock demand from desalination            frac 
    readAvlChannelStorageM                     Array         Channel water available for abstraction (minus env. flow)         m    
    remainNeed                                 Array         Wastewater: demand for reuse (pot_wwt_*, output only)             m    
    Res_Domestic                               Array         Reservoir water for domestic                                      m    
    Res_Industry                               Array         Reservoir water for industry                                      m    
    Res_Irrigation                             Array         Reservoir water for irrigation                                    m    
    Res_Livestock                              Array         Reservoir water for livestock                                     m    
    reservoir_command_areas                    Array         Command areas of the reservoirs (no lakes / restricted res.)      --   
    reservoir_command_areas_wwt                Array         Command areas of the reservoirs restricted to wastewater          --   
    reservoir_command_areas_wwtIndex           Object        Index of reservoir_command_areas_wwt for area total/maximum       --   
    reservoir_command_areasIndex               Object        Index of reservoir_command_areas for area total/maximum           --   
    reservoir_releases_excel_option            Flag          True if reservoir releases come from the Excel settings file      bool 
    reservoir_supply                           Array         Excel settings: daily release fraction for the command areas      frac 
    reservoirStorageM3C                        Array         Reservoir storage at the outlets (compressed)                     m3   
    resId_restricted                           Array         Reservoir ID of the reservoirs restricted to wastewater           --   
    resId_restrictedC                          Array         resId_restricted at the lake/reservoir outlets (compressed)       --   
    sectorSourceAbstractionFractions           Flag          True if sector- and source-specific abstraction fractions         bool 
    segmentArea                                Array         Area of the command area (cellArea outside)                       m2   
    segmentArea_wwt                            Array         Area of the wastewater command area (cellArea outside)            m2   
    smalllakeStorage                           Array         Small lake storage                                                m3   
    smalllakeVolumeM3                          Array         Small lake volume (Puls)                                          m3   
    swAbstractionFraction                      Array         Input swAbstractionFrac: surface water share of the demand        frac 
    swAbstractionFraction_Channel_Domestic     Array         Input: share of the domestic demand from channels                 frac 
    swAbstractionFraction_Channel_Industry     Array         Input: share of the industry demand from channels                 frac 
    swAbstractionFraction_Channel_Irrigation   Array         Input: share of the irrigation demand from channels               frac 
    swAbstractionFraction_Channel_Livestock    Array         Input: share of the livestock demand from channels                frac 
    swAbstractionFraction_Lake_Domestic        Array         Input: share of the domestic demand from lakes                    frac 
    swAbstractionFraction_Lake_Industry        Array         Input: share of the industry demand from lakes                    frac 
    swAbstractionFraction_Lake_Irrigation      Array         Input: share of the irrigation demand from lakes                  frac 
    swAbstractionFraction_Lake_Livestock       Array         Input: share of the livestock demand from lakes                   frac 
    swAbstractionFraction_Lift_Domestic        Array         Input: share of the domestic demand from lift areas               frac 
    swAbstractionFraction_Lift_Industry        Array         Input: share of the industry demand from lift areas               frac 
    swAbstractionFraction_Lift_Irrigation      Array         Input: share of the irrigation demand from lift areas             frac 
    swAbstractionFraction_Lift_Livestock       Array         Input: share of the livestock demand from lift areas              frac 
    swAbstractionFraction_Res_Domestic         Array         Input: share of the domestic demand from reservoirs               frac 
    swAbstractionFraction_Res_Industry         Array         Input: share of the industry demand from reservoirs               frac 
    swAbstractionFraction_Res_Irrigation       Array         Input: share of the irrigation demand from reservoirs             frac 
    swAbstractionFraction_Res_Livestock        Array         Input: share of the livestock demand from reservoirs              frac 
    totalIrrDemand                             Array         Irrigation demand                                                 m    
    unlimitedDesal                             Flag          True if unlimitedDesalinationCapacity = True                      bool 
    using_lift_areas                           Flag          True if using_lift_areas = True                                   bool 
    using_reservoir_command_areas              Flag          True if using_reservoir_command_areas = True                      bool 
    Water_conveyance_efficiency                Array         Canal conveyance efficiency (MODFLOW only, 1 otherwise)           frac 
    Water_conveyance_efficiencyC               Array         Water_conveyance_efficiency at the outlets (compressed)           frac 
    waterBodyBuffer                            Array         Water body number of the buffer around lakes and reservoirs       --   
    waterBodyBuffer_wwt                        Array         waterBodyBuffer for the reservoirs with wastewater reuse          --   
    waterBodyBuffer_wwtIndex                   Object        Index of waterBodyBuffer_wwt for area total/maximum               --   
    waterBodyBufferIndex                       Object        Index of waterBodyBuffer for area total/maximum (AreaIndex)       --   
    waterBodyID                                Array         Lake/reservoir ID of the cells (0 outside lakes/reservoirs)       --   
    waterBodyTyp_unchanged                     Array         Water body type of the settings (1 lake, 2 reservoir)             --   
    waterBodyTypC                              Array         Type of the lakes/reservoirs at the outlets (1 lake, 2/4 res.)    --   
    waterBodyTypCTemp                          Array         Water body type of the current year (compressed)                  --   
    wwt_Domestic                               Array         Reused wastewater for domestic                                    m    
    wwt_Industry                               Array         Reused wastewater for industry                                    m    
    wwt_Irrigation                             Array         Reused wastewater for irrigation                                  m    
    wwt_Livestock                              Array         Reused wastewater for livestock                                   m    
    wwtAbstractionFraction_Res_Domestic        Array         Input: share of the domestic demand from wastewater reuse         frac 
    wwtAbstractionFraction_Res_Industry        Array         Input: share of the industry demand from wastewater reuse         frac 
    wwtAbstractionFraction_Res_Irrigation      Array         Input: share of the irrigation demand from wastewater reuse       frac 
    wwtAbstractionFraction_Res_Livestock       Array         Input: share of the livestock demand from wastewater reuse        frac 
    =========================================  ==========    ================================================================  =====

    """

    def __init__(self, model, agents):
        self.var = model.var
        self.model = model
        self.agents = agents   # irrigation agents: cap of the surface water abstraction for irrigation

    def initial(self):
        """
        Surface water abstraction fractions per sector, reservoir command areas and canals (Error 179),
        lift areas and the surface water share swAbstractionFraction.
        Called after sectorSourceAbstractionFractions is set, before groundwater.initial.
        """

        # surface water abstraction fractions per sector and source
        if self.var.sectorSourceAbstractionFractions:
            self.var.swAbstractionFraction_Channel_Domestic = loadmap('swAbstractionFraction_Channel_Domestic')
            self.var.swAbstractionFraction_Channel_Livestock = loadmap('swAbstractionFraction_Channel_Livestock')
            self.var.swAbstractionFraction_Channel_Industry = loadmap('swAbstractionFraction_Channel_Industry')
            self.var.swAbstractionFraction_Channel_Irrigation = loadmap('swAbstractionFraction_Channel_Irrigation')

            self.var.swAbstractionFraction_Lake_Domestic = loadmap('swAbstractionFraction_Lake_Domestic')
            self.var.swAbstractionFraction_Lake_Livestock = loadmap('swAbstractionFraction_Lake_Livestock')
            self.var.swAbstractionFraction_Lake_Industry = loadmap('swAbstractionFraction_Lake_Industry')
            self.var.swAbstractionFraction_Lake_Irrigation = loadmap('swAbstractionFraction_Lake_Irrigation')

            self.var.swAbstractionFraction_Res_Domestic = loadmap('swAbstractionFraction_Res_Domestic')
            self.var.swAbstractionFraction_Res_Livestock = loadmap('swAbstractionFraction_Res_Livestock')
            self.var.swAbstractionFraction_Res_Industry = loadmap('swAbstractionFraction_Res_Industry')
            self.var.swAbstractionFraction_Res_Irrigation = loadmap('swAbstractionFraction_Res_Irrigation')

            if self.var.includeDesal:
                self.var.othAbstractionFraction_Desal_Domestic = loadmap('othAbstractionFraction_Desal_Domestic')
                self.var.othAbstractionFraction_Desal_Livestock = loadmap('othAbstractionFraction_Desal_Livestock')
                self.var.othAbstractionFraction_Desal_Industry = loadmap('othAbstractionFraction_Desal_Industry')
                self.var.othAbstractionFraction_Desal_Irrigation = loadmap('othAbstractionFraction_Desal_Irrigation')

            if self.var.includeWastewater:
                self.var.wwtAbstractionFraction_Res_Domestic = loadmap('wwtAbstractionFraction_Res_Domestic')
                self.var.wwtAbstractionFraction_Res_Livestock = loadmap('wwtAbstractionFraction_Res_Livestock')
                self.var.wwtAbstractionFraction_Res_Industry = loadmap('wwtAbstractionFraction_Res_Industry')
                self.var.wwtAbstractionFraction_Res_Irrigation = loadmap('wwtAbstractionFraction_Res_Irrigation')

        self.var.using_reservoir_command_areas = False
        self.var.using_reservoir_command_areas = checkOption('using_reservoir_command_areas', True)

        self.var.load_command_areas = False
        self.var.load_command_areas_wwt = False

        if checkOption('includeWaterBodies'):

            # initiate reservoir_command_areas & reservoir_command_areas_wwt
            self.var.reservoir_command_areas = globals.inZero.astype(int)
            self.var.reservoir_command_areas_wwt = globals.inZero.astype(int)

            if self.var.using_reservoir_command_areas and 'reservoir_command_areas' in binding:
                self.var.load_command_areas = True

            if self.var.using_reservoir_command_areas and 'reservoir_command_areas_restricted' in binding:
                self.var.load_command_areas_wwt = True

            if self.var.modflow and 'Water_conveyance_efficiency' in binding:
                self.var.Water_conveyance_efficiency = loadmap('Water_conveyance_efficiency') + globals.inZero
            else:
                self.var.Water_conveyance_efficiency = 1.0 + globals.inZero
            # one value per lake/reservoir outlet (constant), used every day in the reservoir abstraction
            self.var.Water_conveyance_efficiencyC = np.compress(self.var.compress_LR, self.var.Water_conveyance_efficiency)
            self.var.resId_restrictedC = np.compress(self.var.compress_LR, self.var.resId_restricted)

            # load command areas & command areas_wwt
            if self.var.load_command_areas:
                self.var.reservoir_command_areas = loadmap('reservoir_command_areas').astype(int)
                self.var.reservoir_command_areas = np.where(
                    self.var.reservoir_command_areas < 0, 0, self.var.reservoir_command_areas)


            # Lakes/restricted reservoirs within command areas are removed from the command area
            self.var.reservoir_command_areas = np.where(
                self.var.waterBodyTyp_unchanged == 1, 0,
                np.where(self.var.resId_restricted > 0, 0, self.var.reservoir_command_areas))
            self.var.segmentArea = np.where(
                self.var.reservoir_command_areas > 0,
                npareatotal(self.var.cellArea, self.var.reservoir_command_areas),
                self.var.cellArea)

            if self.var.load_command_areas_wwt:
                self.var.reservoir_command_areas_wwt = loadmap('reservoir_command_areas_restricted').astype(int)
                # Lakes & all non-restricted res. within command areas are removed from the command area
                self.var.reservoir_command_areas_wwt = np.where(
                    self.var.waterBodyTyp_unchanged == 1, 0,
                    np.where((self.var.resId_restricted == 0) * (self.var.waterBodyTyp_unchanged == 2), 0,
                             self.var.reservoir_command_areas_wwt))
                self.var.segmentArea_wwt = np.where(
                    self.var.reservoir_command_areas_wwt > 0,
                    npareatotal(self.var.cellArea, self.var.reservoir_command_areas_wwt),
                    self.var.cellArea)

            # indexes for the area functions in commandAreaOperation (command area maps not changed after this)
            # only cells with a command area > 0: the results are only used there
            self.var.reservoir_command_areasIndex = AreaIndex(self.var.reservoir_command_areas)
            self.var.reservoir_command_areas_wwtIndex = AreaIndex(self.var.reservoir_command_areas_wwt)
            # Water abstracted from reservoirs leaks along canals related to conveyance efficiency.
            # Canals are a map where canal cells have the number of the command area they are associated with
            # Command areas without canals experience leakage equally throughout the command area

            if 'canals' in binding:
                self.var.canals = loadmap('canals').astype(int)
                self.var.canals_wwt = self.var.canals.copy()
            else:
                self.var.canals = globals.inZero.copy().astype(int)
                self.var.canals_wwt = self.var.canals.copy()

            # canals for reservoir conveyance and loss
            self.var.canals = np.where(
                self.var.canals != self.var.reservoir_command_areas, 0, self.var.canals)

            # When there are no set canals, the entire command area experiences leakage
            self.var.canals = np.where(
                npareamaximum(self.var.canals, self.var.reservoir_command_areas) == 0,
                self.var.reservoir_command_areas, self.var.canals)
            self.var.canalsArea = np.where(
                self.var.canals > 0, npareatotal(self.var.cellArea, self.var.canals), 0)
            self.var.canalsAreaC = np.compress(self.var.compress_LR, self.var.canalsArea)
            # index for the area maximum of the canal leakage (canals not changed after this; all cells)
            self.var.canalsIndex = AreaIndex(self.var.canals, onlypositive=False)

            # Error 179: the canal leakage of a reservoir is computed at its outlet cell and spread over the
            # canals with canalsArea of the outlet cell. If the outlet is in a command area but not on one of
            # its canal cells, canalsArea there is 0 and the leakage is taken from the reservoir but never
            # added to groundwater/runoff (water balance loss). Only with conveyance efficiency < 1 (MODFLOW).
            outletC = self.var.decompress_LR
            lostLeak = (np.isin(self.var.waterBodyTypC, (2, 4)) & (self.var.resId_restricted[outletC] == 0)
                        & (self.var.reservoir_command_areas[outletC] > 0) & (self.var.canalsAreaC <= 0)
                        & (self.var.Water_conveyance_efficiency[outletC] < 1))
            if np.any(lostLeak):
                resIds = self.var.waterBodyID[outletC][lostLeak]
                cmdIds = self.var.reservoir_command_areas[outletC][lostLeak]
                msg = "Error 179: reservoir outlet cell is in a command area but not on a canal of this " \
                      "command area -> the canal leakage would be lost\n" \
                      "reservoir (command area): " + \
                      ", ".join("%d (%d)" % (r, c) for r, c in zip(resIds, cmdIds)) + "\n" \
                      "Put the outlet cell of the reservoir on a canal cell of its command area (map canals), " \
                      "or the command area number on the outlet cell\n"
                raise CWATMError(msg)

            if self.var.load_command_areas_wwt:
                # canals for wwt reclaimed water
                self.var.canals_wwt = np.where(
                    self.var.canals_wwt != self.var.reservoir_command_areas_wwt, 0, self.var.canals_wwt)

                self.var.canals_wwt = np.where(
                    npareamaximum(self.var.canals_wwt, self.var.reservoir_command_areas_wwt) == 0,
                    self.var.reservoir_command_areas_wwt, self.var.canals_wwt)

                self.var.canalsArea_wwt = np.where(
                    self.var.canals_wwt > 0, npareatotal(self.var.cellArea, self.var.canals_wwt), 0)
                self.var.canalsArea_wwtC = np.compress(self.var.compress_LR, self.var.canalsArea_wwt)

        set_zero(self.var, ['swAbstractionFraction_Lift_Domestic', 'swAbstractionFraction_Lift_Livestock',
                            'swAbstractionFraction_Lift_Industry', 'swAbstractionFraction_Lift_Irrigation'])

        self.var.using_lift_areas = False
        if 'using_lift_areas' in option:
            if checkOption('using_lift_areas'):

                self.var.using_lift_areas = True
                self.var.lift_command_areas = loadmap('lift_areas').astype(int)
                # index for the area functions per lift area (results only used where lift area > 0)
                self.var.lift_command_areasIndex = AreaIndex(self.var.lift_command_areas)

                if self.var.sectorSourceAbstractionFractions:
                    self.var.swAbstractionFraction_Lift_Domestic = loadmap('swAbstractionFraction_Lift_Domestic')
                    self.var.swAbstractionFraction_Lift_Livestock = loadmap('swAbstractionFraction_Lift_Livestock')
                    self.var.swAbstractionFraction_Lift_Industry = loadmap('swAbstractionFraction_Lift_Industry')
                    self.var.swAbstractionFraction_Lift_Irrigation = loadmap('swAbstractionFraction_Lift_Irrigation')
                elif not self.var.activate_irrigation_agents:
                    print(CWATMWarning("using_lift_areas = True but sectorSourceAbstractionFractions = False: "
                                       "the lift fractions are 0, the lift areas take no water"))

        # -------------------------------------------
        # partitioningGroundSurfaceAbstraction
        # partitioning abstraction sources: groundwater and surface water
        # partitioning based on local average baseflow (m3/s) and upstream average discharge (m3/s)
        # estimates of fractions of groundwater and surface water abstractions
        # swAbstractionFrac can be a number or a map: a negative value (number or map cell) means the
        # fraction is computed from average baseflow and discharge (np.any: a map has no single truth value)
        swAbstractionFraction = loadmap('swAbstractionFrac')

        if np.any(swAbstractionFraction < 0):

            averageBaseflowInput = loadmap('averageBaseflow')
            averageDischargeInput = loadmap('averageDischarge')
            # convert baseflow from m to m3/s
            if returnBool('baseflowInM'):
                averageBaseflowInput = averageBaseflowInput * self.var.cellArea * self.var.InvDtSec

            # baseflow averaged over the allocation segments (e.g. catchments): map allocSegments, cells > 0.
            # Before 2026-11 allocSegments was not loaded any more (the load was commented out before 2022)
            # -> AttributeError; checkfirst: settings without usingAllocSegments do not use it
            if checkOption('usingAllocSegments', checkfirst=True):
                self.var.allocSegments = loadmap('allocSegments').astype(int)
                averageBaseflowInput = np.where(self.var.allocSegments > 0,
                                                npareaaverage(averageBaseflowInput, self.var.allocSegments),
                                                averageBaseflowInput)

                # averageUpstreamInput = np.where(self.var.allocSegments > 0,
                #                                npareamaximum(averageDischargeInput, self.var.allocSegments),
                #                                averageDischargeInput)

            swFractionFlow = np.maximum(
                0.0, np.minimum(1.0, averageDischargeInput / np.maximum(
                    1e-20, averageDischargeInput + averageBaseflowInput)))
            # computed fraction where the input is negative, the given fraction elsewhere
            swAbstractionFraction = np.where(swAbstractionFraction < 0, swFractionFlow, swAbstractionFraction)

        self.var.swAbstractionFraction = globals.inZero.copy()
        for No in range(4):
            self.var.swAbstractionFraction += self.var.fracVegCover[No] * swAbstractionFraction
        for No in range(4, 6):
            if self.var.modflow:
                self.var.swAbstractionFraction += self.var.fracVegCover[No] * swAbstractionFraction
            else:
                # The motivation is to avoid groundwater on sealed and water land classes
                # TODO: Groundwater pumping should be allowed over sealed land
                self.var.swAbstractionFraction += self.var.fracVegCover[No]

    def dynamic(self, totalDemand):
        """
        Surface water abstraction of the day.

        Parameters
        ----------
        totalDemand : ndarray
            Total demand [m]

        Returns
        -------
        list of ndarray or None
            pot_Channel: potential channel abstraction per sector (SECTORS order, None without sector fractions)
            for the zonal abstraction [m]
        """

        self.desalination()
        pot_SurfaceAbstract, pot_Channel = self.channel(totalDemand)

        # UNDER CONSTRUCTION
        if self.var.using_lift_areas:
            self.lift()

        if checkOption('includeWaterBodies'):
            self.var.abstractedLakeReservoirM3C = np.compress(self.var.compress_LR, globals.inZero.copy())
            # first wastewater reclamation (restricted use reservoirs), then lakes and reservoirs (not restricted)
            if self.var.includeWastewater:
                self.wastewater_reservoirs(pot_SurfaceAbstract)
            self.lakes(pot_SurfaceAbstract)
            self.reservoirs(pot_SurfaceAbstract)

        return pot_Channel

    def desalination(self):
        """
        Desalination (only with sector fractions and includeDesal): limited by the yearly capacity
        (unless unlimitedDesal), split over the sectors.
        """

        self.var.act_DesalWaterAbstractM3 = globals.inZero.copy()
        # Desalination is not allowed without sectorSourceAbstractionFractions
        if self.var.sectorSourceAbstractionFractions:
            if self.var.includeDesal:
                pot_Desal_Domestic = self.var.othAbstractionFraction_Desal_Domestic * self.var.domesticDemand
                pot_Desal_Livestock = self.var.othAbstractionFraction_Desal_Livestock * self.var.livestockDemand
                pot_Desal_Industry = self.var.othAbstractionFraction_Desal_Industry * self.var.industryDemand
                pot_Desal_Irrigation = self.var.othAbstractionFraction_Desal_Irrigation * self.var.totalIrrDemand

                pot_DesalAbst = (pot_Desal_Domestic + pot_Desal_Livestock + pot_Desal_Industry +
                                  pot_Desal_Irrigation)
                if not self.var.unlimitedDesal:
                    # yearly capacity [m3] spread over the days of the year (366 in leap years)
                    self.var.AvlDesalM3 = self.var.desalAnnualCap[dateVar['currDate'].year] / dateVar['daysInYear']
                    potDesalM3 = np.nansum(pot_DesalAbst * self.var.cellArea)
                    # no desalination demand on this day -> coefficient 0 (not 0/0 = NaN)
                    abstractLimitCoeff = min(potDesalM3, self.var.AvlDesalM3) / potDesalM3 if potDesalM3 > 0 else 0.
                    self.var.act_DesalWaterAbstractM = pot_DesalAbst * abstractLimitCoeff
                else:
                    self.var.act_DesalWaterAbstractM = pot_DesalAbst

                #self.var.act_DesalWaterAbstractM = self.var.act_DesalWaterAbstractM3 / self.var.cellArea
        if self.var.sectorSourceAbstractionFractions:
            if self.var.includeDesal:
                (self.var.Desal_Domestic, self.var.Desal_Livestock, self.var.Desal_Industry,
                 self.var.Desal_Irrigation), _ = split_sectors(self.var.act_DesalWaterAbstractM, (
                    self.var.othAbstractionFraction_Desal_Domestic * self.var.domesticDemand,
                    self.var.othAbstractionFraction_Desal_Livestock * self.var.livestockDemand,
                    self.var.othAbstractionFraction_Desal_Industry * self.var.industryDemand,
                    self.var.othAbstractionFraction_Desal_Irrigation * self.var.totalIrrDemand))

    def channel(self, totalDemand):
        """
        Abstraction from the channel of the cell (readAvlChannelStorageM).

        Returns
        -------
        tuple
            pot_SurfaceAbstract: potential surface water abstraction without sector fractions (None with) [m],
            pot_Channel: potential channel abstraction per sector (SECTORS order, None without sector fractions) [m]
        """

        pot_SurfaceAbstract = pot_Channel = None
        # surface water abstraction that can be extracted to fulfill totalDemand
        # - based on ChannelStorage and swAbstractionFraction * totalDemand
        # sum up potential surface water abstraction (no groundwater abstraction under water and sealed area)

        if self.var.sectorSourceAbstractionFractions:
            pot_Channel_Domestic, pot_Channel_Livestock, pot_Channel_Industry, pot_Channel_Irrigation = pot_source(
                self.var, 'Channel', 'swAbstractionFraction_Channel_%s')

            pot_Channel_Irrigation = self.agents.cap_sw(pot_Channel_Irrigation)

            pot_channelAbst = pot_Channel_Domestic + pot_Channel_Livestock + pot_Channel_Industry + pot_Channel_Irrigation

            self.var.act_SurfaceWaterAbstract = np.minimum(self.var.readAvlChannelStorageM, pot_channelAbst)
        else:
            pot_SurfaceAbstract = totalDemand * self.var.swAbstractionFraction
            # only local surface water abstraction is allowed (network is only within a cell)
            self.var.act_SurfaceWaterAbstract = np.minimum(self.var.readAvlChannelStorageM, pot_SurfaceAbstract)

        self.var.readAvlChannelStorageM -= self.var.act_SurfaceWaterAbstract
        self.var.act_channelAbst = self.var.act_SurfaceWaterAbstract.copy()
        # if surface water is not sufficient it is taken from groundwater

        if self.var.sectorSourceAbstractionFractions:
            (self.var.Channel_Domestic, self.var.Channel_Livestock, self.var.Channel_Industry,
             self.var.Channel_Irrigation), _ = split_sectors(self.var.act_channelAbst, (
                self.var.swAbstractionFraction_Channel_Domestic * self.var.domesticDemand,
                self.var.swAbstractionFraction_Channel_Livestock * self.var.livestockDemand,
                self.var.swAbstractionFraction_Channel_Industry * self.var.industryDemand,
                self.var.swAbstractionFraction_Channel_Irrigation * self.var.totalIrrDemand))

        if self.var.sectorSourceAbstractionFractions:
            pot_Channel = [pot_Channel_Domestic, pot_Channel_Livestock, pot_Channel_Industry, pot_Channel_Irrigation]
        return pot_SurfaceAbstract, pot_Channel

    def lift(self):
        """
        Lift areas: the lift demand of a lift area is taken from the channel water of all its cells.
        """

        # Lift development When there is sufficient water in the Segment to fulfill demand, the water is
        # taken away proportionally from each cell's readAvlChannelStorageM in the Segment. For example,
        # if total demand can be filled with 50% of total availability, then 50% of the
        # readAvlChannelStorageM from each cell is used. Note that if a cell has too little Channel Storage,
        # then no water will be taken from the cell as this was dealt with earlier:  readAvlChannelStorage =
        # 0 if < (0.0005 * self.var.cellArea) Note: Due to the shared use of abstracted channel storage,
        # a cell may abstract more than its pot_SurfaceAbstract, as well as not necessarily satisfy its
        # pot_SurfaceAbstract

        pot_Lift_Domestic, pot_Lift_Livestock, pot_Lift_Industry, pot_Lift_Irrigation = pot_source(
            self.var, 'Lift', 'swAbstractionFraction_Lift_%s')

        pot_Lift_Irrigation = self.agents.cap_sw(pot_Lift_Irrigation)

        pot_liftAbst = pot_Lift_Domestic + pot_Lift_Livestock + pot_Lift_Industry + pot_Lift_Irrigation


        remainNeed_afterLocal = pot_liftAbst.copy()

        # The remaining demand within each command area [M3] is put into a map where each cell in the command
        # area holds this total demand
        demand_Segment_lift = np.where(self.var.lift_command_areas > 0,
                                       self.var.lift_command_areasIndex.total(remainNeed_afterLocal * self.var.cellArea),
                                       0) / self.var.cellArea # [M]

        available_Segment_lift = np.where(self.var.lift_command_areas > 0,
                                          self.var.lift_command_areasIndex.total(self.var.readAvlChannelStorageM * self.var.cellArea),
                                          0) / self.var.cellArea  # [M]

        zone_lift_abstraction = np.minimum(demand_Segment_lift, available_Segment_lift)

        #cell_sf_abstraction = np.maximum(0., np.where(zoneDemand_sw < zone_sf_avail, divideValues(left_sf_avail,
        #                                                                                          zone_sf_avail) * zoneDemand_sw,
        #                                              left_sf_avail))

        cell_lift_abstraction = \
            np.maximum(0., divideValues(self.var.readAvlChannelStorageM, available_Segment_lift) * zone_lift_abstraction)
        cell_lift_allocation = \
            np.maximum(0., divideValues(remainNeed_afterLocal, demand_Segment_lift) * zone_lift_abstraction)

        self.var.act_channelAbst += cell_lift_abstraction
        self.var.act_SurfaceWaterAbstract += cell_lift_abstraction

        self.var.readAvlChannelStorageM -= cell_lift_abstraction
        # same 0.5 mm threshold as for readAvlChannelStorageM above (before 2026-11: 0.01 m = 10 mm)
        self.var.readAvlChannelStorageM = np.where(self.var.readAvlChannelStorageM < 0.0005, 0,
                                                   self.var.readAvlChannelStorageM)
        # Used in landCover for riverbedExchange
        self.var.act_channelAbstract_Lift = cell_lift_abstraction

        if self.var.sectorSourceAbstractionFractions:

            # A
            (self.var.Lift_Domestic, self.var.Lift_Livestock, self.var.Lift_Industry,
             self.var.Lift_Irrigation), self.var.Lift_Other = split_sectors(cell_lift_allocation, (
                pot_Lift_Domestic, pot_Lift_Livestock, pot_Lift_Industry, pot_Lift_Irrigation))

    def wastewater_reservoirs(self, pot_SurfaceAbstract):
        """
        Wastewater reuse from the restricted reservoirs: in the buffer around them (waterBodyBuffer_wwt) or,
        with reservoir_command_areas_restricted, in their command areas (with canal leakage).

        Parameters
        ----------
        pot_SurfaceAbstract : ndarray or None
            Potential surface water abstraction without sector fractions [m]
        """

        if not self.var.load_command_areas_wwt:
            wwtDemandAreaMask =  self.var.waterBodyBuffer_wwt > 0
        else:
            wwtDemandAreaMask =  self.var.reservoir_command_areas_wwt > 0

        # First apply to wastewater reclamation, e.g., restricted use reservoirs. Follow by lakes and reservoirs (not restricted)
        if self.var.sectorSourceAbstractionFractions:
            pot_wwt_Domestic, pot_wwt_Livestock, pot_wwt_Industry, pot_wwt_Irrigation = [
                pot * wwtDemandAreaMask for pot in pot_source(self.var, 'wwt', 'wwtAbstractionFraction_Res_%s')]

            remainNeed = pot_wwt_Domestic + pot_wwt_Livestock + pot_wwt_Industry + pot_wwt_Irrigation
            self.var.remainNeed = remainNeed.copy()

            # UPDATE ALL SECTORSOURCEABSTRACTIONFRACTIONS BELOW
        else:
            irrFracDemand = divideValues(self.var.totalIrrDemand, self.var.nonIrrDemand + self.var.totalIrrDemand)

            # water that is still needed from surface water  - in this case only consider irrigation
            remainNeed = np.maximum(pot_SurfaceAbstract - self.var.act_SurfaceWaterAbstract, 0) * wwtDemandAreaMask * irrFracDemand
        # start wastewater allocation

        if not self.var.load_command_areas_wwt:
            ## opt 1: buffer with no command areas is used
            # remainNeedBig = npareatotal(remainNeed, self.var.waterBodyID)
            # demand and storage in m3: the cells around a lake have different areas (lat/lon grid),
            # before 2026-11 summed in m and compared with storage / outlet cell area (S1)
            remainNeedBig_wwt = self.var.waterBodyBuffer_wwtIndex.total(remainNeed * self.var.cellArea)
            remainNeedBig_wwtC = np.compress(self.var.compress_LR, remainNeedBig_wwt)
            # Storage of a big lake [m3]
            ReservoirsThatAreCurrentlyReservoirs = np.where(np.isin(self.var.waterBodyTypCTemp, (2, 4)), self.var.reservoirStorageM3C, 0)
            ReservoirsThatAreCurrentlyReservoirs = np.where(self.var.resId_restrictedC > 0, ReservoirsThatAreCurrentlyReservoirs, 0)
            lakeResStorageC = np.where(self.var.waterBodyTypCTemp == 0, 0.,
                                np.where(self.var.waterBodyTypCTemp == 1, self.var.lakeStorageC,
                                            ReservoirsThatAreCurrentlyReservoirs))

            minlake = np.maximum(0., 0.98 * lakeResStorageC)  # reasonable but arbitrary limit
            act_bigLakeAbst_wwtM3C = np.minimum(minlake, remainNeedBig_wwtC)

            # substract from both, because it is sorted by self.var.waterBodyTypCTemp
            self.var.lakeStorageC = self.var.lakeStorageC - act_bigLakeAbst_wwtM3C
            self.var.lakeVolumeM3C = self.var.lakeVolumeM3C - act_bigLakeAbst_wwtM3C
            self.var.reservoirStorageM3C = self.var.reservoirStorageM3C - act_bigLakeAbst_wwtM3C
            # and from the combined one for waterbalance issues
            self.var.lakeResStorageC = self.var.lakeResStorageC - act_bigLakeAbst_wwtM3C

            self.var.abstractedLakeReservoirM3C += act_bigLakeAbst_wwtM3C
            bigLakesFactor_wwtC = divideValues(act_bigLakeAbst_wwtM3C, remainNeedBig_wwtC)
            # and back to the big array
            bigLakesFactor_wwt = globals.inZero.copy()
            np.put(bigLakesFactor_wwt, self.var.decompress_LR, bigLakesFactor_wwtC)

            # bigLakesFactorAllaroundlake = npareamaximum(bigLakesFactor, self.var.waterBodyID)
            bigLakesFactorAllaroundlake_wwt = self.var.waterBodyBuffer_wwtIndex.maximum(bigLakesFactor_wwt)
            #print(np.compress(self.var.compress_LR, bigLakesFactorAllaroundlake_wwt))
            # abstraction from big lakes is partioned to the users around the lake
            self.var.act_bigLakeResAbst_wwt = remainNeed * bigLakesFactorAllaroundlake_wwt
            # remaining need is used from lakes and reservoirs without water use restrictions
            #remainNeed0 = remainNeed * (1 - bigLakesFactorAllaroundlake_wwt)


            # allocate water demand in case sectorSourceAbstractionFractions = True
            if self.var.sectorSourceAbstractionFractions:
                (self.var.wwt_Domestic, self.var.wwt_Livestock, self.var.wwt_Industry,
                 self.var.wwt_Irrigation), _ = split_sectors(self.var.act_bigLakeResAbst_wwt, (
                    pot_wwt_Domestic, pot_wwt_Livestock, pot_wwt_Industry, pot_wwt_Irrigation))
        else:
            ## opt 2:  command areas are used
            #self.var.abstractedLakeReservoirM3C = np.compress(self.var.compress_LR, globals.inZero.copy())
            self.var.act_ResAbst_wwt = globals.inZero.copy()
            self.var.act_bigLakeResAbst_wwt = globals.inZero.copy()

            # load maximum reservoir volume fraction available for irrigation
            resStorage_maxFracForIrrigation = self._reservoirReleaseFraction(wwt=True)

            if self.var.sectorSourceAbstractionFractions:
                remainNeedPre = pot_wwt_Domestic + pot_wwt_Livestock + pot_wwt_Industry
                remainNeed = pot_wwt_Irrigation

                # remainNeed, command_areas, maxFracForIrrigation
                ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment, resStorageTotal_allocC, efficiency_CA = self.commandAreaOperation(remainNeed = remainNeedPre, command_areas = self.var.reservoir_command_areas_wwt, command_index = self.var.reservoir_command_areas_wwtIndex,\
                    maxFracForIrrigation = resStorage_maxFracForIrrigation, wwt_only = True)
                metRemainSegment = self._takeFromReservoirs(ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment, efficiency_CA)

                self.var.act_bigLakeResAbst_wwt = remainNeedPre * metRemainSegment
                # (added to act_SurfaceWaterAbstract below with act_bigLakeResAbst_wwt - before 2026-10-16
                # also here: the non-irrigation reuse was counted twice)

                self.var.act_ResAbst_wwt = remainNeedPre * metRemainSegment

            if self.var.sectorSourceAbstractionFractions:
                (self.var.wwt_Domestic, self.var.wwt_Livestock, self.var.wwt_Industry), _ = split_sectors(
                    self.var.act_ResAbst_wwt, (pot_wwt_Domestic, pot_wwt_Livestock, pot_wwt_Industry))

            # Irrigation


                                                    # remainNeed, command_areas, maxFracForIrrigation
            ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment, resStorageTotal_allocC, efficiency_CA = self.commandAreaOperation(remainNeed = remainNeed, command_areas = self.var.reservoir_command_areas_wwt, command_index = self.var.reservoir_command_areas_wwtIndex,\
                                 maxFracForIrrigation = resStorage_maxFracForIrrigation, wwt_only = True)
            metRemainSegment = self._takeFromReservoirs(ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment, efficiency_CA)

            self.var.act_bigLakeResAbst_wwt += remainNeed * metRemainSegment
            self.var.act_ResAbst_wwt += remainNeed * metRemainSegment

            self.var.leakage_wwtC_daily = resStorageTotal_allocC * ResAbstractFactorC * (
                    1 - self.var.Water_conveyance_efficiencyC)


            if self.var.sectorSourceAbstractionFractions:
                self.var.wwt_Irrigation = np.minimum(
                    remainNeed * metRemainSegment,
                    pot_wwt_Irrigation)

            ## End of using_reservoir_command_areas_wwt

        self.var.act_SurfaceWaterAbstract += self.var.act_bigLakeResAbst_wwt

    def lakes(self, pot_SurfaceAbstract):
        """
        Abstraction from big lakes and reservoirs (in the buffer around them) and from small lakes.

        Parameters
        ----------
        pot_SurfaceAbstract : ndarray or None
            Potential surface water abstraction without sector fractions [m]
        """

        # Lakes and reservoirs are both considered lakes for purposes of lake abstraction,
        # both satisfying demands within waterbody cells or within self.var.waterBodyBuffer
        # depending on abstraction fractions

        if self.var.sectorSourceAbstractionFractions:

            pot_Lake_Domestic, pot_Lake_Livestock, pot_Lake_Industry, pot_Lake_Irrigation = pot_source(
                self.var, 'Lake', 'swAbstractionFraction_Lake_%s')

            remainNeed0 = pot_Lake_Domestic + pot_Lake_Livestock + pot_Lake_Industry + pot_Lake_Irrigation

        else:

            # water that is still needed from surface water
            remainNeed0 = np.maximum(pot_SurfaceAbstract - self.var.act_SurfaceWaterAbstract, 0)

        mskWtrBody_unrestricted = self.var.waterBodyBuffer > 0

        # first from big Lakes and reservoirs, big lakes cover several gridcells
        # collect all water demand from lake pixels of the same id

        # remainNeedBig = npareatotal(remainNeed, self.var.waterBodyID)
        # not only the lakes and reservoirs but the command areas around water bodies e.g. here a buffer
        # demand and storage in m3: the cells around a lake have different areas (lat/lon grid),
        # before 2026-11 summed in m and compared with storage / outlet cell area (S1)
        remainNeedBig = self.var.waterBodyBufferIndex.total(remainNeed0 * self.var.cellArea)
        remainNeedBigC = np.compress(self.var.compress_LR, remainNeedBig)

        # Storage of a big lake [m3]
        lakeResStorageC = np.where(self.var.waterBodyTypCTemp == 0, 0.,
                                   np.where(self.var.waterBodyTypCTemp == 1, self.var.lakeStorageC,
                                            self.var.reservoirStorageM3C))

        minlake = np.maximum(0., 0.98 * lakeResStorageC)  # reasonable but arbitrary limit
        act_bigLakeAbstM3C = np.minimum(minlake, remainNeedBigC)
        # substract from both, because it is sorted by self.var.waterBodyTypCTemp
        self.var.lakeStorageC = self.var.lakeStorageC - act_bigLakeAbstM3C
        self.var.lakeVolumeM3C = self.var.lakeVolumeM3C - act_bigLakeAbstM3C
        self.var.reservoirStorageM3C = self.var.reservoirStorageM3C - act_bigLakeAbstM3C
        # and from the combined one for waterbalance issues
        self.var.lakeResStorageC = self.var.lakeResStorageC - act_bigLakeAbstM3C

        # += : with wastewater the abstraction of the wastewater reservoirs (above) is kept (reset at the start
        # of the lakes part and above without wastewater) - before 2026-10-16 "=" dropped it (output only)
        self.var.abstractedLakeReservoirM3C += act_bigLakeAbstM3C

        bigLakesFactorC = divideValues(act_bigLakeAbstM3C, remainNeedBigC)

        # and back to the big array
        bigLakesFactor = globals.inZero.copy()
        np.put(bigLakesFactor, self.var.decompress_LR, bigLakesFactorC)

        # bigLakesFactorAllaroundlake = npareamaximum(bigLakesFactor, self.var.waterBodyID)
        bigLakesFactorAllaroundlake = self.var.waterBodyBufferIndex.maximum(bigLakesFactor)

        # abstraction from big lakes is partioned to the users around the lake
        self.var.act_bigLakeResAbst = remainNeed0  * mskWtrBody_unrestricted * bigLakesFactorAllaroundlake

        # remaining need is used from small lakes
        remainNeed1 = remainNeed0 * (1 - bigLakesFactorAllaroundlake)
        # minlake = np.maximum(0.,self.var.smalllakeStorage - self.var.minsmalllakeStorage) * self.var.M3toM

        if returnBool('useSmallLakes'):
            # limit by the Puls volume too: abstraction is taken from both, a negative volume is set to 0
            # in lakes_res_small.py (max(0, SI)) and the abstracted water would be created again
            minlake = np.maximum(0., 0.98 * np.minimum(self.var.smalllakeStorage, self.var.smalllakeVolumeM3)) * self.var.M3toM
            self.var.act_smallLakeResAbst = np.minimum(minlake, remainNeed1)
            # act_smallLakesres is substracted from small lakes storage
            self.var.smalllakeVolumeM3 = self.var.smalllakeVolumeM3 - self.var.act_smallLakeResAbst * self.var.MtoM3
            self.var.smalllakeStorage = self.var.smalllakeStorage - self.var.act_smallLakeResAbst * self.var.MtoM3
        else:
            self.var.act_smallLakeResAbst = 0

        # available surface water is from river network + large/small lake & reservoirs
        self.var.act_SurfaceWaterAbstract = self.var.act_SurfaceWaterAbstract + self.var.act_bigLakeResAbst \
                                            + self.var.act_smallLakeResAbst
        self.var.act_lakeAbst = self.var.act_bigLakeResAbst + self.var.act_smallLakeResAbst
        # -------------------------------------

        if self.var.sectorSourceAbstractionFractions:

            # A
            (self.var.Lake_Domestic, self.var.Lake_Livestock, self.var.Lake_Industry,
             self.var.Lake_Irrigation), _ = split_sectors(self.var.act_lakeAbst, (
                pot_Lake_Domestic, pot_Lake_Livestock, pot_Lake_Industry, pot_Lake_Irrigation))

    def reservoirs(self, pot_SurfaceAbstract):
        """
        Abstraction from the reservoirs in their command areas: domestic, livestock and industry first (with sector
        fractions), then irrigation (or the rest of the surface water demand); canal leakage.

        Parameters
        ----------
        pot_SurfaceAbstract : ndarray or None
            Potential surface water abstraction without sector fractions [m]
        """

        if self.var.sectorSourceAbstractionFractions:

            # B
            pot_Res_Domestic, pot_Res_Livestock, pot_Res_Industry, pot_Res_Irrigation = pot_source(
                self.var, 'Res', 'swAbstractionFraction_Res_%s')

            pot_Res_Irrigation = self.agents.cap_sw(pot_Res_Irrigation)

            # remainNeed2 = pot_Res_Domestic + pot_Res_Livestock + pot_Res_Industry + pot_Res_Irrigation
            remainNeed2 = pot_Res_Irrigation

        else:

            remainNeed2 = pot_SurfaceAbstract - self.var.act_SurfaceWaterAbstract

        #if self.var.load_command_areas:

        # The command area of a reservoir is the area that can receive water from this reservoir. Before
        # this step, each cell has attempted to satisfy its demands with local water using in-cell
        # channel, lift area, and lake. The remaining demand within each command area is totaled and
        # requested from the associated reservoir. The reservoir offers this water up to a daily maximum
        # relating to the available storage in the reservoir, defined in the Reservoir_releases_input_file.
        #
        # SETTINGS FILE AND INPUTS

        # -Activating
        # In the OPTIONS section towards the beginning of the settings file, add/set
        # using_reservoir_command_areas = True

        # - Command areas raster map Anywhere after the OPTIONS section (in WATERDEMAND, for example),
        # add/set reservoir_command_areas to a path holding... information about the command areas. This
        # Command areas raster map should assign the same positive integer coding to each cell within the
        # same segment. All other cells must Nan values, or values <= 0.

        # -Optional inputs
        #
        # Anywhere after the OPTIONS section, add/set Reservoir_releases_input_file to a path holding
        # information about irrigation releases. This should be a raster map (netCDF) of 366 values
        # determining the maximum fraction of available storage to be used for meeting water demand... in
        # the associated command area on the day of the year. If this is not included, a value of 0.01
        # will be assumed, i.e. 1% of the reservoir storage can be at most released into the command area
        # on each day.
        self.var.act_ResAbst = globals.inZero.copy()
        # Domestic, livestock, and industrial demands are satisfied before irrigation
        resStorage_maxFracForIrrigation = self._reservoirReleaseFraction(wwt=False)

        # canal leakage of the reservoir abstraction for domestic, livestock and industry (1st call)
        leakage_sectorsC = 0
        if self.var.sectorSourceAbstractionFractions:

            remainNeedPre = pot_Res_Domestic + pot_Res_Livestock + pot_Res_Industry
            #print('water_demand.py: np.sum(remainNeedPre) with reservoirs', np.sum(remainNeedPre))

            # remainNeed, command_areas, maxFracForIrrigation
            ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment, resStorageTotal_allocC, efficiency_CA = self.commandAreaOperation(remainNeed = remainNeedPre, command_areas = self.var.reservoir_command_areas, command_index = self.var.reservoir_command_areasIndex,\
              maxFracForIrrigation = resStorage_maxFracForIrrigation, wwt_only = False)

            metRemainSegment = self._takeFromReservoirs(ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment, efficiency_CA)
            # the part (1 - Water_conveyance_efficiency) of the water taken from the reservoirs leaks from the
            # canals as for the 2nd call below (before 2026-10-12 it was lost: Bhima 589 Mm3 in 2 years)
            leakage_sectorsC = resStorageTotal_allocC * ResAbstractFactorC * (
                1 - self.var.Water_conveyance_efficiencyC)

            self.var.act_bigLakeResAbst += remainNeedPre * metRemainSegment
            self.var.act_SurfaceWaterAbstract += remainNeedPre * metRemainSegment

            self.var.act_ResAbst = remainNeedPre * metRemainSegment

            (self.var.Res_Domestic, self.var.Res_Livestock, self.var.Res_Industry), _ = split_sectors(
                self.var.act_ResAbst, (pot_Res_Domestic, pot_Res_Livestock, pot_Res_Industry))

        # If sector- and source-specific abstractions are activated, then domestic, industrial, and
        #  livestock demands were attempted to be satisfied in the previous step. Otherwise, total demands
        #  not satisfied by previous sources is attempted.
        #
        # The remaining demand within each command area [M3] is put into a map where each cell in the
        # command area holds this total demand



        ## Reservoir associated with the Command Area
        #
        # If there is more than one reservoir in a command area,
        #   the storage of the reservoir with maximum storage in this time-step is chosen.
        # The map resStorageTotal_alloc holds this maximum reservoir storage
        #   within a command area in all cells within that command area

        ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment, resStorageTotal_allocC, efficiency_CA = self.commandAreaOperation(remainNeed = remainNeed2, command_areas = self.var.reservoir_command_areas, command_index = self.var.reservoir_command_areasIndex,\
            maxFracForIrrigation = resStorage_maxFracForIrrigation, wwt_only = False)

        metRemainSegment = self._takeFromReservoirs(ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment, efficiency_CA)

        self.var.leakageC_daily = leakage_sectorsC + resStorageTotal_allocC * ResAbstractFactorC * (
                1 - self.var.Water_conveyance_efficiencyC)

        self.var.leakage = globals.inZero.copy()
        np.put(self.var.leakage, self.var.decompress_LR, self.var.leakageC_daily + self.var.leakage_wwtC_daily)

        # self.var.leakageC += self.var.leakageC_daily
        divleak_canal = divideValues((self.var.leakageC_daily +  self.var.leakage_wwtC_daily) ,self.var.canalsAreaC)
        self.var.leakageCanalsC_M = np.where(self.var.canalsAreaC > 0,divleak_canal, 0)

        # Without this, npareamaximum uses the historical maximum
        self.var.leakageCanals_M = globals.inZero.copy()
        np.put(self.var.leakageCanals_M, self.var.decompress_LR, self.var.leakageCanalsC_M)  # good
        self.var.leakageCanals_M = self.var.canalsIndex.maximum(self.var.leakageCanals_M)

        self.var.act_bigLakeResAbst += remainNeed2 * metRemainSegment
        self.var.act_SurfaceWaterAbstract += remainNeed2 * metRemainSegment

        self.var.act_ResAbst += remainNeed2 * metRemainSegment

        ## End of using_reservoir_command_areas

        if self.var.sectorSourceAbstractionFractions:
            self.var.Res_Irrigation = np.minimum(
                remainNeed2 * metRemainSegment,
                pot_Res_Irrigation)

        # map of the lake + reservoir storage at the outlet cells: built once, after all abstractions from
        # lakes and reservoirs above (before 2026-11 rebuilt after each of them, only the last one was used)
        self.var.lakeResStorage = globals.inZero.copy()
        np.put(self.var.lakeResStorage, self.var.decompress_LR, self.var.lakeResStorageC)

    def commandAreaOperation(self, remainNeed, command_areas, command_index, maxFracForIrrigation, wwt_only=False):
        """
        Execute coordinated water allocation operations within reservoir command areas.

        This method performs sophisticated water allocation calculations for command areas
        served by reservoirs, handling complex spatial aggregation of water demands,
        identification of dominant reservoirs within command areas, application of
        abstraction limits based on reservoir rules, and calculation of conveyance
        efficiency losses. It supports both regular water supply and wastewater treatment
        operations with differentiated reservoir access controls.

        The method implements a multi-step allocation algorithm:
        1. Aggregates water demands across all cells within each command area
        2. Identifies the reservoir with maximum storage within each command area
        3. Applies reservoir-specific abstraction limits and operational rules
        4. Calculates actual water abstraction considering conveyance efficiency
        5. Computes abstraction factors for proportional allocation across reservoirs

        Parameters
        ----------
        remainNeed : ndarray
            Remaining water demand per grid cell after other sources [m/day].
            Represents unmet water demand that could be satisfied by reservoir abstraction.
        command_areas : ndarray of int
            Command area identifier map where cells with same positive integer values
            belong to the same command area. Cells with non-positive values are not
            included in command area operations.
        command_index : AreaIndex
            Index of command_areas (cells > 0) for the area total and maximum,
            built once in initial (reservoir_command_areasIndex or reservoir_command_areas_wwtIndex).
        maxFracForIrrigation : ndarray
            Maximum fraction of reservoir storage available for irrigation abstraction
            per reservoir [dimensionless, 0-1]. Represents operational constraints and
            environmental flow requirements.
        wwt_only : bool, optional
            Flag indicating wastewater treatment only operations (default False).
            When True, limits operations to reservoirs designated for wastewater
            treatment. When False, excludes wastewater treatment reservoirs.

        Returns
        -------
        tuple of (ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment, resStorageTotal_allocC, efficiency_CA)
            ResAbstractFactorC : ndarray
                Compressed abstraction factors for reservoir cells [dimensionless].
                Fraction of available reservoir storage to be abstracted.
            act_bigLakeResAbst_alloc : ndarray
                Actual water abstraction allocated per command area [m3].
                Total volume to be abstracted considering all constraints.
            demand_Segment : ndarray
                Total water demand per command area [m3].
                Aggregated demand across all cells within each command area.
            resStorageTotal_allocC : ndarray
                Compressed total reservoir storage per command area [m3].
                Storage of the dominant reservoir serving each command area.
            efficiency_CA : ndarray
                Water_conveyance_efficiency of the dominant reservoir (outlet cell) in all cells of its command
                area, 1 outside [dimensionless]. Abstraction, delivery and canal leakage use the same efficiency.

        Notes
        -----
        Command Area Logic:
        The method identifies the reservoir with maximum storage within each command area
        as the primary water source. This approach handles cases where multiple reservoirs
        exist within a single command area by selecting the most significant one based on
        current storage levels.

        Wastewater Operations:
        When wwt_only=True, the method restricts operations to reservoirs specifically
        designated for wastewater treatment (resId_restricted > 0). This enables
        separate management of treated wastewater supplies versus conventional water sources.

        Conveyance Efficiency:
        Water demands are adjusted by conveyance efficiency to account for distribution
        losses. The method ensures that reservoir abstractions account for these losses
        to meet actual demand requirements at delivery points.

        Abstraction Limits:
        Reservoir abstraction is limited by both storage availability and operational
        rules (maxFracForIrrigation). The method ensures sustainable reservoir operations
        while meeting water demands within physical and regulatory constraints.
        """

        demand_Segment = np.where(
            command_areas > 0, command_index.total(remainNeed * self.var.cellArea),
            0)  # [M3]

        # Reservoir associated with the Command Area
        #
        # If there is more than one reservoir in a command area, the storage of the reservoir with
        # maximum storage in this time-step is chosen. The map resStorageTotal_alloc holds this
        # maximum reservoir storage within a command area in all cells within that command area

        ReservoirsThatAreCurrentlyReservoirs = np.where(np.isin(self.var.waterBodyTypCTemp, (2, 4)), self.var.reservoirStorageM3C, 0)
        if wwt_only:
            ReservoirsThatAreCurrentlyReservoirs = np.where(
                self.var.resId_restrictedC > 0,
                ReservoirsThatAreCurrentlyReservoirs, 0)
        else:
            ReservoirsThatAreCurrentlyReservoirs = np.where(
                self.var.resId_restrictedC == 0,
                ReservoirsThatAreCurrentlyReservoirs, 0)
        reservoirStorageM3 = globals.inZero.copy()
        # np.put(reservoirStorageM3, self.var.decompress_LR, self.var.reservoirStorageM3C)
        np.put(reservoirStorageM3, self.var.decompress_LR, ReservoirsThatAreCurrentlyReservoirs)
        resStorageTotal_alloc = np.where(command_areas > 0,
                                        command_index.maximum(reservoirStorageM3), 0)  # [M3]

        # In the map resStorageTotal_allocC, the maximum storage from each allocation segment is held
        # in all reservoir cells within that allocation segment. We now correct to remove the
        # reservoirs that are not this maximum-storage-reservoir for the command area.
        resStorageTotal_allocC = np.compress(self.var.compress_LR, resStorageTotal_alloc)
        resStorageTotal_allocC = np.where(
            resStorageTotal_allocC == self.var.reservoirStorageM3C,
            resStorageTotal_allocC, 0.)


        # resStorage_maxFracForIrrigationC holds the fractional rules found for each reservoir,
        # so we must null those that are not the maximum-storage reservoirs
        resStorage_maxFracForIrrigation = globals.inZero.copy()
        resStorage_maxFracForIrrigationC = np.compress(self.var.compress_LR, maxFracForIrrigation)
        resStorage_maxFracForIrrigationC = np.where(
            resStorageTotal_allocC == self.var.reservoirStorageM3C,
            resStorage_maxFracForIrrigationC, 0.)
        np.put(resStorage_maxFracForIrrigation, self.var.decompress_LR,
               resStorage_maxFracForIrrigationC)

        resStorage_maxFracForIrrigation_CA = np.where(
            command_areas > 0,
            command_index.maximum(resStorage_maxFracForIrrigation), 0)

        # conveyance efficiency of the dominant reservoir in its command area: the leakage is computed with the
        # efficiency at the reservoir outlet, so the abstraction and the delivery use the same one (before 2026-11 the
        # efficiency of each demand cell: abstraction - leakage != delivered with a non-uniform efficiency map)
        efficiencyC = np.where(resStorageTotal_allocC == self.var.reservoirStorageM3C,
                               self.var.Water_conveyance_efficiencyC, 0.)
        efficiency = globals.inZero.copy()
        np.put(efficiency, self.var.decompress_LR, efficiencyC)
        efficiency_CA = np.where(command_areas > 0, command_index.maximum(efficiency), 0.)
        efficiency_CA = np.where(efficiency_CA > 0, efficiency_CA, 1.)

        act_bigLakeResAbst_alloc = np.minimum(
            resStorage_maxFracForIrrigation_CA * resStorageTotal_alloc,
            demand_Segment / efficiency_CA)  # [M3]

        # fraction of water abstracted versus water available for total segment reservoir volumes
        ResAbstractFactor = np.where(resStorageTotal_alloc > 0,
                                    divideValues(act_bigLakeResAbst_alloc, resStorageTotal_alloc),
                                    0)

        # Compressed version needs to be corrected as above
        ResAbstractFactorC = np.compress(self.var.compress_LR, ResAbstractFactor)
        ResAbstractFactorC = np.where(
            resStorageTotal_allocC == self.var.reservoirStorageM3C, ResAbstractFactorC, 0.)
        return (ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment,
                resStorageTotal_allocC, efficiency_CA)

    def _takeFromReservoirs(self, ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment, efficiency_CA):
        """
        Take the abstraction of commandAreaOperation from the reservoir storages and return the met fraction.

        Subtracts reservoirStorageM3C * ResAbstractFactorC [m3] from the lake and reservoir storages, adds it to
        abstractedLakeReservoirM3(C) and returns metRemainSegment, the fraction of the command area demand which
        is delivered (after the conveyance losses, by definition <= 1).
        """
        taken = self.var.reservoirStorageM3C * ResAbstractFactorC
        self.var.lakeStorageC -= taken
        self.var.lakeVolumeM3C -= taken
        self.var.lakeResStorageC -= taken
        self.var.abstractedLakeReservoirM3C += taken
        self.var.reservoirStorageM3C -= taken
        np.put(self.var.abstractedLakeReservoirM3, self.var.decompress_LR, self.var.abstractedLakeReservoirM3C)

        return np.where(demand_Segment > 0,
                        divideValues(act_bigLakeResAbst_alloc * efficiency_CA, demand_Segment), 0)  # by definition <= 1

    def _reservoirReleaseFraction(self, wwt=False):
        """
        Maximum fraction of the reservoir storage which can be released into the command areas today [-].

        From the netCDF Reservoir_releases (day of year), for the wastewater reservoirs (wwt=True) from the map
        wwt_reservoir_releases (limited to 0..1), from the reservoir Excel sheet (reservoir_supply, 0.03 for the
        reservoirs without a release ratio) or 0.03.
        """
        if 'Reservoir_releases' in binding:
            day_of_year = dateVar['currDate'].timetuple().tm_yday
            return readnetcdf2('Reservoir_releases', day_of_year, useDaily='DOY', value='Fraction of Volume')
        if wwt and 'wwt_reservoir_releases' in binding:
            return np.maximum(np.minimum(loadmap('wwt_reservoir_releases'), 1.), 0.) + globals.inZero.copy()
        if self.var.reservoir_releases_excel_option:
            fraction = globals.inZero.copy()
            fractionC = np.where(self.var.lakeResStorage_release_ratioC > -1,
                                 self.var.reservoir_supply[dateVar['doy'] - 1], 0.03)
            np.put(fraction, self.var.decompress_LR, fractionC)
            return fraction
        return 0.03 + globals.inZero.copy()
