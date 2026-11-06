# -------------------------------------------------------------------------
# Name:        Water demand module
# Purpose: Integrated water demand module coordinating all sectoral water requirements.
# Orchestrates domestic, industrial, agricultural, livestock, and environmental demands.
# Manages water allocation and source attribution across multiple demand sectors.
#
# Author:      PB, MS, LG, JdeB, DF
# Created:     15/07/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import numpy as np
from cwatm.management_modules import globals

from cwatm.management_modules.globals import dateVar, option
from cwatm.management_modules.data_handling import returnBool, binding, loadmap, divideValues, checkOption
from cwatm.hydrological_modules.water_demand.domestic import waterdemand_domestic
from cwatm.hydrological_modules.water_demand.industry import waterdemand_industry
from cwatm.hydrological_modules.water_demand.livestock import waterdemand_livestock
from cwatm.hydrological_modules.water_demand.irrigation import waterdemand_irrigation
from cwatm.hydrological_modules.water_demand.environmental_need import waterdemand_environmental_need, ENVFLOW_OFF
from cwatm.hydrological_modules.water_demand.wastewater import waterdemand_wastewater
from cwatm.hydrological_modules.water_demand.irrigation_agents import waterdemand_irrigation_agents
from cwatm.hydrological_modules.water_demand.surface_water_abstraction import waterdemand_surfacewater
from cwatm.hydrological_modules.water_demand.groundwater_abstraction import waterdemand_groundwater
from cwatm.hydrological_modules.water_demand.sector_demand import (set_zero, SECTOR_SOURCE, ORDER_WITHDRAWAL_SECTOR,
                                                                   sum_vars)


# set to 0 in initial with and without water demand
ZERO_BOTH = SECTOR_SOURCE + [
    'leakage', 'leakageCanals_M', 'modfPumpingM', 'Pumping_daily', 'abstractedLakeReservoirM3',
    'act_bigLakeResAbst_wwt', 'act_DesalWaterAbstractM', 'act_nonIrrWithdrawal',
    'ratio_irrWithdrawalGW_month', 'ratio_irrWithdrawalSW_month', 'act_irrNonpaddyWithdrawal', 'act_irrPaddyWithdrawal',
    'act_nonIrrConsumption', 'act_totalIrrConsumption', 'act_totalWaterConsumption',
    'act_indConsumption', 'act_domConsumption', 'act_livConsumption', 'returnflowIrr', 'returnflowNonIrr']

# set to 0 in initial only with water demand
ZERO_DEMAND = ['act_irrWithdrawalSW_month', 'act_irrWithdrawalGW_month', 'pitLatrinToGW']

# set to 0 in initial only without water demand (with water demand these are computed every day)
ZERO_NODEMAND = [
    'nonIrrReturnFlowFraction', 'nonFossilGroundwaterAbs',
    'domesticDemand', 'industryDemand', 'livestockDemand', 'nonIrrDemand', 'totalIrrDemand',
    'totalWaterDemand', 'act_irrPaddyDemand', 'act_irrNonpaddyDemand', 'act_irrWithdrawal', 'act_totalWaterWithdrawal',
    'act_indWithdrawal', 'act_domWithdrawal', 'act_livWithdrawal', 'act_nonpaddyConsumption', 'act_paddyConsumption',
    'unmetDemand', 'unmetDemand_runningSum', 'unmet_lost',
    'addtoevapotrans', 'returnFlow', 'act_bigLakeResAbst', 'pot_GroundwaterAbstract',
    'relaxSWagent', 'relaxGWagent']


class water_demand:
    """
    Water demand: coordinates the demand sectors and the abstraction from the water sources.

    Each day the demands of the sectors are computed (domestic, industry, livestock: maps; irrigation: from the
    soil moisture deficit; environmental flow) and taken from the sources in this order:
    desalination, channel, lift areas, wastewater reuse, lakes, reservoirs (surface_water_abstraction.py),
    then groundwater, unmet demand or fossil groundwater, zonal abstraction, MODFLOW pumping
    (groundwater_abstraction.py). Irrigation agents can limit the irrigation abstraction (irrigation_agents.py).
    Shared helpers for sectors and sources: sector_demand.py.
    With sectorSourceAbstractionFractions each sector has its own fraction per source; otherwise only
    surface water / groundwater (swAbstractionFrac) is distinguished.
    After the abstraction: withdrawals and consumption per sector, return flows, water balance checks.

    Attributes
    ----------
    domestic, industry, livestock, irrigation, environmental_need, wastewater : object
        Demand modules of the sectors
    agents : waterdemand_irrigation_agents
        Irrigation agents (adminSegments)
    surfacewater : waterdemand_surfacewater
        Surface water abstraction
    groundwater : waterdemand_groundwater
        Groundwater abstraction

    **Global variables**

    =========================================  ==========    ================================================================  =====
    Variable [self.var]                        Type          Description                                                       Unit 
    =========================================  ==========    ================================================================  =====
    channelStorage                             Array         Channel water storage                                             m3   
    unmetDemand_runningSum                     Array         Sum of the unmet demand since the start                           m    
    modflow                                    Flag          True if modflow_coupling = True                                   bool 
    pot_domesticConsumption                    Array         Potential domestic water consumption                              m    
    load_initial                               Function      Function: loads a variable from the initial conditions            --   
    pot_industryConsumption                    Array         Potential industry water consumption                              m    
    efficiencyPaddy                            Array         Input irrPaddy_efficiency: paddy irrigation efficiency            frac 
    efficiencyNonpaddyWithdrawal               Array         efficiencyNonpaddy / fraction_IncreaseIrrigation_Nonpaddy         frac 
    returnfractionIrr                          Array         Input irrigation_returnfraction: return part of the losses        frac 
    compress_LR                                Array         Boolean map: outlet cells of lakes/reservoirs (compress)          --   
    M3toM                                      Array         Coefficient m3 -> m (= InvCellArea)                               1 m-2
    wwtColArea                                 Array         Wastewater: collection area (ID of the treatment plant)           --   
    wwtSewerCollection                         Array         Wastewater: sewer collection (domestic + industry)                m    
    wwtOverflowOutM                            Array         Wastewater: overflow of the treatment plants                      m    
    fracVegCover                               Array         Land cover fractions (0 forest, 1 grassland, 2 paddy, ...)        frac 
    adminSegments                              Array         Agent areas (administrative segments) of the irrigation agents    --   
    adminSegmentsIndex                         Object        Index of adminSegments for area total/average (AreaIndex)         --   
    limitAbstraction                           Flag          True if limitAbstraction = True: no fossil groundwater            bool 
    cellArea                                   Array         Cell area                                                         m2   
    nonFossilGroundwaterAbs                    Array         Non-fossil groundwater abstraction                                m    
    includeWastewater                          Flag          True if includeWastewater = True                                  bool 
    act_SurfaceWaterAbstract                   Array         Surface water abstraction                                         m    
    readAvlChannelStorageM                     Array         Channel water available for abstraction (minus env. flow)         m    
    leakageCanals_M                            Array         Canal leakage spread over the canal cells                         m    
    includeWastewaterPits                      Flag          True if includePitLatrine = True                                  bool 
    pitLatrinToGW                              Array         Non-irrigation return flow from pit latrines to groundwater       m    
    addtoevapotrans                            Array         Irrigation losses that evaporate                                  m    
    act_irrConsumption                         Array         Irrigation consumption per land cover                             m    
    act_irrNonpaddyWithdrawal                  Array         Non-paddy irrigation withdrawal                                   m    
    act_irrPaddyWithdrawal                     Array         Paddy irrigation withdrawal                                       m    
    act_bigLakeResAbst                         Array         Abstraction from lakes and reservoirs at demand location          m    
    returnFlow                                 Array         Return flow to the channels (irrigation + non-irrigation)         m    
    act_nonIrrConsumption                      Array         Non-irrigation consumption                                        m    
    act_nonIrrWithdrawal                       Array         Non-irrigation withdrawals                                        m    
    act_irrWithdrawal                          Array         Irrigation withdrawals                                            m    
    waterdemandFixed                           Flag          True if waterdemandFixed = True: demand of a fixed year           bool 
    modfPumpingM                               Array         MODFLOW: pumping since the last MODFLOW run                       m    
    domesticDemand                             Array         Domestic water demand (withdrawal)                                m    
    swAbstractionFraction_domestic             Array         Domestic agents: surface water share of the request               frac 
    demand_unit                                Flag          Non-irrigation demand maps in m/day (True) or Mm3 per period      bool 
    sectorSourceAbstractionFractions           Flag          True if sector- and source-specific abstraction fractions         bool 
    dom_efficiency                             Array         Domestic consumption / withdrawal, at most 1                      frac 
    envFlow                                    Array         Channel storage kept for the environmental flow                   m    
    industryDemand                             Array         Industry water demand (withdrawal)                                m    
    ind_efficiency                             Array         Industry consumption / withdrawal, at most 1                      frac 
    unmetDemand                                Array         Unmet demand, taken from fossil groundwater (limitAbstraction F)  m    
    irrDemand                                  Array         Irrigation demand per land cover                                  m    
    totalIrrDemand                             Array         Irrigation demand                                                 m    
    livestockDemand                            Array         Livestock water demand (withdrawal)                               m    
    pot_livestockConsumption                   Array         Potential livestock consumption (= livestock demand)              m    
    liv_efficiency                             Number        Livestock consumption / withdrawal (= 1)                          frac 
    wwtEffluentsGenerated                      Array         Wastewater: effluents of domestic + industry                      m    
    wwtSewerCollection_domestic                Array         Wastewater: domestic effluents collected by sewers                m    
    wwtSewerCollection_industry                Array         Wastewater: industry effluents collected by sewers                m    
    includeIndusDomesDemand                    Flag          True if includeIndusDomesDemand = True                            bool 
    relaxGWagent                               Array         Agents: relax counter of the groundwater fraction                 --   
    relaxSWagent                               Array         Agents: relax counter of the surface water fraction               --   
    waterdemandFixedYear                       Number        Year of the demand maps with waterdemandFixed                     year 
    frac_industry                              Array         Industry share of the non-irrigation demand (nonIrrDemand)        frac 
    frac_domestic                              Array         Domestic share of the non-irrigation demand (nonIrrDemand)        frac 
    frac_livestock                             Array         Livestock share of the non-irrigation demand (nonIrrDemand)       frac 
    leakage                                    Array         Canal leakage at the reservoir outlets (to groundwater/runoff)    m3   
    Pumping_daily                              Array         MODFLOW: groundwater pumping of the day                           m    
    ratio_irrWithdrawalGW_month                Array         Agents: groundwater withdrawal of the month / request             frac 
    ratio_irrWithdrawalSW_month                Array         Agents: surface water withdrawal of the month / request           frac 
    act_irrWithdrawalSW_month                  Array         Agents: surface water withdrawal of the month (segment)           m3   
    act_irrWithdrawalGW_month                  Array         Agents: groundwater withdrawal of the month (segment)             m3   
    Desal_Domestic                             Array         Desalinated water for domestic                                    m    
    Desal_Industry                             Array         Desalinated water for industry                                    m    
    Desal_Livestock                            Array         Desalinated water for livestock                                   m    
    Desal_Irrigation                           Array         Desalinated water for irrigation                                  m    
    Channel_Domestic                           Array         Channel water for domestic                                        m    
    Channel_Industry                           Array         Channel water for industry                                        m    
    Channel_Livestock                          Array         Channel water for livestock                                       m    
    Channel_Irrigation                         Array         Channel water for irrigation                                      m    
    Lift_Domestic                              Array         Lift area channel water for domestic                              m    
    Lift_Industry                              Array         Lift area channel water for industry                              m    
    Lift_Livestock                             Array         Lift area channel water for livestock                             m    
    Lift_Irrigation                            Array         Lift area channel water for irrigation                            m    
    wwt_Domestic                               Array         Reused wastewater for domestic                                    m    
    wwt_Industry                               Array         Reused wastewater for industry                                    m    
    wwt_Livestock                              Array         Reused wastewater for livestock                                   m    
    wwt_Irrigation                             Array         Reused wastewater for irrigation                                  m    
    Lake_Domestic                              Array         Lake water for domestic                                           m    
    Lake_Industry                              Array         Lake water for industry                                           m    
    Lake_Livestock                             Array         Lake water for livestock                                          m    
    Lake_Irrigation                            Array         Lake water for irrigation                                         m    
    Res_Domestic                               Array         Reservoir water for domestic                                      m    
    Res_Industry                               Array         Reservoir water for industry                                      m    
    Res_Livestock                              Array         Reservoir water for livestock                                     m    
    Res_Irrigation                             Array         Reservoir water for irrigation                                    m    
    GW_Domestic                                Array         Groundwater for domestic (fossil incl. if limitAbstraction F)     m    
    GW_Industry                                Array         Groundwater for industry (fossil incl. if limitAbstraction F)     m    
    GW_Livestock                               Array         Groundwater for livestock (fossil incl. if limitAbstraction F)    m    
    GW_Irrigation                              Array         Groundwater for irrigation (fossil incl. if limitAbstraction F)   m    
    abstractedLakeReservoirM3                  Array         Abstraction from lakes/reservoirs at the outlet cells             m3   
    leakage_wwtC_daily                         Array         Canal leakage of the wastewater reservoirs (compressed)           m3   
    act_bigLakeResAbst_wwt                     Array         Wastewater reuse from lakes/reservoirs at demand location         m    
    act_DesalWaterAbstractM                    Array         Desalinated water                                                 m    
    act_totalIrrConsumption                    Array         Total irrigation consumption                                      m    
    act_totalWaterConsumption                  Array         Total water consumption                                           m    
    act_indConsumption                         Array         Industrial consumption                                            m    
    act_domConsumption                         Array         Domestic consumption                                              m    
    act_livConsumption                         Array         Livestock consumption                                             m    
    returnflowIrr                              Array         Irrigation return flow                                            m    
    returnflowNonIrr                           Array         Non-irrigation return flow                                        m    
    nonIrrReturnFlowFraction                   Array         Return flow fraction of the non-irrigation withdrawal             frac 
    nonIrrDemand                               Array         Non-irrigation demand (domestic + industry + livestock)           m    
    totalWaterDemand                           Array         Irrigation and non-irrigation demand                              m    
    act_totalWaterWithdrawal                   Array         Total water withdrawals                                           m    
    act_indWithdrawal                          Array         Industrial withdrawal                                             m    
    act_domWithdrawal                          Array         Domestic withdrawal                                               m    
    act_livWithdrawal                          Array         Livestock withdrawal                                              m    
    unmet_lost                                 Array         Fossil water lost instead of becoming return flow                 m    
    pot_GroundwaterAbstract                    Array         Potential groundwater abstraction                                 m    
    act_nonpaddyConsumption                    Array         Non-paddy irrigation consumption                                  m    
    act_paddyConsumption                       Array         Paddy consumption                                                 m    
    act_irrPaddyDemand                         Array         Paddy irrigation demand                                           m    
    act_irrNonpaddyDemand                      Array         Non-paddy irrigation demand                                       m    
    pot_nonIrrConsumption                      Array         Potential non-irrigation consumption                              m    
    unmet_lostirr                              Array         Fossil water for irrigation lost instead of return flow           m    
    unmet_lostNonirr                           Array         Fossil water for non-irrigation lost instead of return flow       m    
    wwtEffluentsGenerated_domestic             Array         Wastewater: domestic part of returnflowNonIrr                     m    
    wwtEffluentsGenerated_industry             Array         Wastewater: industry part of returnflowNonIrr                     m    
    wwtSewerCollectedBySoruce                  Array         Wastewater: effluents minus the non-collected return flow         m    
    waterabstraction                           Array         nonFossilGroundwaterAbs + unmetDemand + surface water             m    
    humanConsumption                           Array         Human consumption incl. crop transpiration (output only)          m    
    humanUse                                   Array         Human withdrawal incl. non-irrigated crops (output only)          m    
    natureUse                                  Array         Not computed (always 0)                                           m    
    ETRefAverage_segments                      Array         ETRef averaged over adminSegments                                 m    
    precipEffectiveAverage_segments            Array         Infiltration of grassland averaged over adminSegments             m    
    head_segments                              Array         MODFLOW water level averaged over adminSegments                   masl 
    gwdepth_adjusted_segments                  Array         Adjusted groundwater depth averaged over adminSegments            m    
    gwdepth_segments                           Array         Groundwater depth, averaged over adminSegments                    m    
    adminSegments_area                         Array         Agricultural area (grass, paddy, non-paddy) per adminSegment      m2   
    infiltration                               Array         Water actually infiltrating the soil                              m    
    actTransTotal_paddy                        Array         Transpiration from paddy land cover                               m    
    actTransTotal_nonpaddy                     Array         Transpiration from non-paddy land cover                           m    
    actTransTotal_crops_nonIrr                 Array         Transpiration of the non-irrigated crops                          m    
    head                                       Array         MODFLOW water level                                               masl 
    gwdepth_adjusted                           Array         Adjusted depth to groundwater table                               m    
    gwdepth                                    Array         Depth to groundwater table                                        m    
    ETRef                                      Array         Reference evapotranspiration                                      m    
    Crops                                      Array         List of the crops and their Kc/Ky parameters                      --   
    sum_openWaterEvap                          Array         Open water evaporation of all land covers                         m    
    =========================================  ==========    ================================================================  =====

    """

    def __init__(self, model):
        """
        Create the demand modules of the sectors and the agents, surface water and groundwater modules.

        Parameters
        ----------
        model : object
            CWatM model instance
        """
        self.var = model.var
        self.model = model

        self.domestic = waterdemand_domestic(model)
        self.industry = waterdemand_industry(model)
        self.livestock = waterdemand_livestock(model)
        self.irrigation = waterdemand_irrigation(model)
        self.environmental_need = waterdemand_environmental_need(model)
        self.wastewater = waterdemand_wastewater(model)
        self.agents = waterdemand_irrigation_agents(model)
        self.surfacewater = waterdemand_surfacewater(model, self.agents)
        self.groundwater = waterdemand_groundwater(model, self.agents)

    def initial(self):
        """
        Options and flags of the water demand (includeIndusDomesDemand, includeWastewater, limitAbstraction,
        waterdemandFixed, sectorSourceAbstractionFractions), initial of the sector modules, irrigation agents,
        surface water (fractions per sector, command areas, canals, lift areas, swAbstractionFraction) and
        groundwater (fractions, commandAreasRelaxGwAbstraction, allocation zones); maps set to 0.

        The order matters: agents first (adminSegments), surfacewater.initial needs sectorSourceAbstractionFractions,
        groundwater.initial needs using_reservoir_command_areas (set in surfacewater.initial).
        """

        if checkOption('includeWaterDemand'):
            self.var.includeIndusDomesDemand = True
        else:
            self.var.includeIndusDomesDemand = False

        # True if all demands are taken into account,
        # False if not only irrigation is considered
        # This variable has no impact if includeWaterDemand is False
        if "includeIndusDomesDemand" in option:
            self.var.includeIndusDomesDemand = checkOption('includeIndusDomesDemand')

        self.var.includeWastewater = False
        if "includeWastewater" in option:
            self.var.includeWastewater = checkOption('includeWastewater')

        # irrigation agents (also adminSegments, used by dynamic_output): irrigation_agents.py
        self.agents.initial()

        self.var.includeWastewaterPits = False
        if 'includePitLatrine' in option:
            self.var.includeWastewaterPits = checkOption('includePitLatrine')

        # in case fossil water abstraction is allowed this will be filled
        self.var.unmetDemand = globals.inZero.copy()
        self.var.unmetDemand_runningSum = self.var.load_initial('unmetDemand_runningSum', default=globals.inZero.copy())
        self.var.sectorSourceAbstractionFractions = False


        # =======================================================

        if checkOption('includeWaterDemand'):
            # limitAbstraction = False: fossil groundwater covers the unmet demand (read once instead of every day)
            self.var.limitAbstraction = checkOption('limitAbstraction')

            if self.var.includeIndusDomesDemand:  # all demands are taken into account

                self.domestic.initial()
                self.industry.initial()
                self.livestock.initial()
                self.irrigation.initial()
                self.environmental_need.initial()
                self.wastewater.initial()
            else:  # only irrigation is considered

                self.irrigation.initial()
                self.environmental_need.initial()

            # if waterdemand is fixed it means it does not change between years.
            self.var.waterdemandFixed = False
            if "waterdemandFixed" in binding:
                if returnBool('waterdemandFixed'):
                    self.var.waterdemandFixed = True
                    # int: loadmap gives a float and date.replace(year=...) needs an int
                    self.var.waterdemandFixedYear = int(loadmap('waterdemandFixedYear'))

            # Sector-,source-abstraction fractions facilitate designating the specific source for the specific sector
            # Sources: River, Lake, Reservoir, Groundwater
            # Sectors: Domestic, Industry, Livestock, Irrigation
            # Otherwise, one can distinguish only between surface and groundwater, irrigation and non-irrigation

            if 'sectorSourceAbstractionFractions' in option:
                if checkOption('sectorSourceAbstractionFractions'):
                    #print('Sector- and source-specific abstraction fractions are activated (water_demand.py)')
                    self.var.sectorSourceAbstractionFractions = True

            # surface water fractions per sector, command areas and canals, lift areas, swAbstractionFraction
            self.surfacewater.initial()
            # groundwater abstraction fractions, commandAreasRelaxGwAbstraction, allocation zones
            self.groundwater.initial()

            # non-irrigation input maps have for each month or year the unit m/day (True) or million m3/month (False)
            self.var.demand_unit = True
            if "demand_unit" in binding:
                self.var.demand_unit = returnBool('demand_unit')


            # maps set to 0: same list as without water demand (ZERO_BOTH) + ZERO_DEMAND
            set_zero(self.var, ZERO_BOTH + ZERO_DEMAND)

        else:  # no water demand
            set_zero(self.var, ZERO_BOTH + ZERO_NODEMAND)

        # with and without water demand
        self.var.swAbstractionFraction_domestic = 1 + globals.inZero.copy()
        self.var.ind_efficiency = 1.
        self.var.dom_efficiency = 1.
        self.var.liv_efficiency = 1
        # for wastewater package
        if checkOption('includeWaterBodies'):
            self.var.leakage_wwtC_daily = np.compress(self.var.compress_LR, globals.inZero.copy())


    def dynamic(self):
        """
        Water demand and abstraction of the day.

        1. environmental flow, channel water available (readAvlChannelStorageM, minus envFlow, 0 in lake cells)
        2. demand of the sectors (wd_date: waterdemandFixed), totalDemand [m]
        3. agents (new month), groundwater fraction in command areas (new month / after the 15th)
        4. surface water abstraction (surface_water_abstraction.py), returns pot_Channel for the zonal abstraction
        5. groundwater abstraction (groundwater_abstraction.py), returns the irrigation withdrawal SW / GW (agents)
        6. consumption per sector, return flows, pit latrines, water balance checks, agents end of day
        """

        # environmental flow [m] stays in the channel: once per day, before the MODFLOW leakage uses it
        # (environmental_need.initial is only called with includeWaterDemand)
        if checkOption('includeWaterDemand'):
            self.environmental_need.dynamic()
        else:
            self.var.envFlow = ENVFLOW_OFF

        if self.var.modflow:

            # computing leakage from rivers to groundwater

            # self.var.readAvlChannelStorageM will be used in land covertype to compute leakage to
            # groundwater if ModFlow coupling to avoid small values and to avoid surface water abstractions
            # from dry channels (>= 0.01mm)
            self.var.readAvlChannelStorageM = np.where(
                self.var.channelStorage < (0.0005 * self.var.cellArea), 0.,
                self.var.channelStorage)  # in [m3]
            # coversersion m3 -> m # minus environmental flow
            self.var.readAvlChannelStorageM = self.var.readAvlChannelStorageM * self.var.M3toM  # in [m]
            self.var.readAvlChannelStorageM = np.maximum(
                0., self.var.readAvlChannelStorageM - self.var.envFlow)

        if checkOption('includeWaterDemand'):

            # for debugging of a specific date
            # if (globals.dateVar['curr'] >= 137):
            #    ii =1

            # ----------------------------------------------------
            # WATER DEMAND

            # Fix year of water demand on predefined year
            wd_date = globals.dateVar['currDate']
            if self.var.waterdemandFixed:
                wd_date = wd_date.replace(day=1)
                wd_date = wd_date.replace(year=self.var.waterdemandFixedYear)

            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.domestic.dynamic(wd_date)
                self.industry.dynamic(wd_date)
                self.livestock.dynamic(wd_date)
                self.irrigation.dynamic()
            else:
                self.irrigation.dynamic()

            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                if globals.dateVar['newStart'] or globals.dateVar['newMonth']:
                    # total (potential) non irrigation water demand
                    self.var.nonIrrDemand = (self.var.domesticDemand + self.var.industryDemand +
                                              self.var.livestockDemand)
                    self.var.pot_nonIrrConsumption = np.minimum(
                        self.var.nonIrrDemand,
                        (self.var.pot_domesticConsumption + self.var.pot_industryConsumption +
                         self.var.pot_livestockConsumption))
                    # fraction of return flow from domestic and industrial water demand
                    self.var.nonIrrReturnFlowFraction = divideValues(
                        (self.var.nonIrrDemand - self.var.pot_nonIrrConsumption), self.var.nonIrrDemand)
                    # non-irrigation sector fractions of nonIrrDemand (change only with the demand maps)
                    self.var.frac_industry = divideValues(self.var.industryDemand, self.var.nonIrrDemand)
                    self.var.frac_domestic = divideValues(self.var.domesticDemand, self.var.nonIrrDemand)
                    self.var.frac_livestock = divideValues(self.var.livestockDemand, self.var.nonIrrDemand)

                # Sum up water demand
                # totalDemand [m]: total maximum (potential) water demand: irrigation and non irrigation
                totalDemand = self.var.nonIrrDemand + self.var.totalIrrDemand  # in [m]
            else:  # only irrigation is considered
                totalDemand = np.copy(self.var.totalIrrDemand)  # in [m]
                set_zero(self.var, ['domesticDemand', 'industryDemand', 'livestockDemand', 'nonIrrDemand',
                                    'pot_nonIrrConsumption', 'nonIrrReturnFlowFraction'])
                # print('-----------------------------totalDemand---------: ', np.mean(totalDemand))

            # ----------------------------------------------------
            # WATER AVAILABILITY

            if not self.var.modflow:  # already done if ModFlow coupling
                # conversion m3 -> m # minus environmental flow
                self.var.readAvlChannelStorageM = np.maximum(
                    0., self.var.channelStorage * self.var.M3toM - self.var.envFlow)  # in [m]
            # no channel water in lake cells: lake cells are pits of the lake network, their kinematic wave is not used
            # (discharge = lake outflow) - the water of a lake is in the lake storage (act_bigLakeResAbst)
            if checkOption('includeWaterBodies'):
                self.var.readAvlChannelStorageM = np.where(self.var.waterBodyID > 0, 0., self.var.readAvlChannelStorageM)

            # -------------------------------------
            # WATER DEMAND vs. WATER AVAILABILITY
            # -------------------------------------

            if dateVar['newStart'] or dateVar['newMonth']:
                # agents: reset of the monthly withdrawals, irrigation fractions of the new month
                self.agents.update_fractions()

            # groundwater fraction for irrigation in command areas (new month / after the 15th)
            self.groundwater.update_fractions()
            
            
            # surface water: desalination, channel, lift areas, wastewater reuse, lakes, reservoirs:
            # surface_water_abstraction.py
            pot_Channel = self.surfacewater.dynamic(totalDemand)

            # groundwater: potential and non-fossil abstraction, unmet demand or fossil groundwater (limitAbstraction),
            # zonal abstraction, MODFLOW pumping: groundwater_abstraction.py
            act_irrWithdrawalSW, act_irrWithdrawalGW = self.groundwater.dynamic(totalDemand, pot_Channel)

            self.var.act_irrConsumption[2] = divideValues(self.var.act_irrPaddyWithdrawal,
                                                          self.var.fracVegCover[2]) * self.var.efficiencyPaddy
            # efficiency of the withdrawal: with the extra water of fraction_IncreaseIrrigation_Nonpaddy (irrigation.py)
            self.var.act_irrConsumption[3] = divideValues(self.var.act_irrNonpaddyWithdrawal,
                                                          self.var.fracVegCover[3]) * self.var.efficiencyNonpaddyWithdrawal


            if self.var.sectorSourceAbstractionFractions:

                self.var.act_domWithdrawal, self.var.act_livWithdrawal, self.var.act_indWithdrawal = [
                    sum_vars(self.var, [s + '_' + sector for s in ORDER_WITHDRAWAL_SECTOR])
                    for sector in ('Domestic', 'Livestock', 'Industry')]

                self.var.act_indConsumption = self.var.ind_efficiency * self.var.act_indWithdrawal
                self.var.act_domConsumption = self.var.dom_efficiency * self.var.act_domWithdrawal
                self.var.act_livConsumption = self.var.liv_efficiency * self.var.act_livWithdrawal
                self.var.act_nonIrrConsumption = self.var.act_domConsumption + self.var.act_indConsumption + \
                                                 self.var.act_livConsumption

            elif self.var.includeIndusDomesDemand:  # all demands are taken into account

                self.var.act_indWithdrawal = self.var.frac_industry * self.var.act_nonIrrWithdrawal
                self.var.act_domWithdrawal = self.var.frac_domestic * self.var.act_nonIrrWithdrawal
                self.var.act_livWithdrawal = self.var.frac_livestock * self.var.act_nonIrrWithdrawal
                self.var.act_indConsumption = self.var.ind_efficiency * self.var.act_indWithdrawal
                self.var.act_domConsumption = self.var.dom_efficiency * self.var.act_domWithdrawal
                self.var.act_livConsumption = self.var.liv_efficiency * self.var.act_livWithdrawal
                self.var.act_nonIrrConsumption = self.var.act_domConsumption + self.var.act_indConsumption + \
                                                 self.var.act_livConsumption

            else:  # only irrigation is considered
                self.var.act_nonIrrConsumption = globals.inZero.copy()

            self.var.act_totalIrrConsumption = self.var.fracVegCover[2] * self.var.act_irrConsumption[2] + \
                                               self.var.fracVegCover[3] * self.var.act_irrConsumption[3]
            self.var.act_paddyConsumption = self.var.fracVegCover[2] * self.var.act_irrConsumption[2]
            self.var.act_nonpaddyConsumption = self.var.fracVegCover[3] * self.var.act_irrConsumption[3]

            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.var.totalWaterDemand = self.var.fracVegCover[2] * self.var.irrDemand[2] + self.var.fracVegCover[
                    3] * self.var.irrDemand[3] + self.var.nonIrrDemand
                self.var.act_totalWaterWithdrawal = self.var.act_nonIrrWithdrawal + self.var.act_irrWithdrawal
                self.var.act_totalWaterConsumption = self.var.act_nonIrrConsumption + self.var.act_totalIrrConsumption
            else:  # only irrigation is considered
                self.var.totalWaterDemand = self.var.fracVegCover[2] * self.var.irrDemand[2] + self.var.fracVegCover[
                    3] * self.var.irrDemand[3]
                self.var.act_totalWaterWithdrawal = np.copy(self.var.act_irrWithdrawal)
                self.var.act_totalWaterConsumption = np.copy(self.var.act_totalIrrConsumption)

            # --- calculate return flow
            # Sum up loss - difference between withdrawn and consumed - split into return flow and evaporation
            sumIrrLoss = self.var.act_irrWithdrawal - self.var.act_totalIrrConsumption

            self.var.returnflowIrr = self.var.returnfractionIrr * sumIrrLoss
            self.var.addtoevapotrans = (1 - self.var.returnfractionIrr) * sumIrrLoss

            if self.var.sectorSourceAbstractionFractions:
                self.var.returnflowNonIrr = self.var.act_nonIrrWithdrawal - self.var.act_nonIrrConsumption
            elif self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.var.returnflowNonIrr = self.var.nonIrrReturnFlowFraction * self.var.act_nonIrrWithdrawal

            # limit return flow to not put all fossil groundwater back into the system, because it can lead to higher
            # river discharge than without water demand, as water is taken from fossil groundwater (out of system)
            # share of the withdrawal from fossil groundwater = unmetDemand / withdrawal (only used with
            # limitAbstraction = False, there act_totalWaterWithdrawal = full demand, which already includes unmetDemand)
            unmet_div_ww = 1. - np.minimum(1, divideValues(self.var.unmetDemand, self.var.act_totalWaterWithdrawal))

            # 'fossil_water_treated_normally' means that there is no lost fossil water
            if 'fossil_water_treated_normally' in option:
                if checkOption('fossil_water_treated_normally'):
                    unmet_div_ww = 1

            if self.var.limitAbstraction:
                unmet_div_ww = 1

            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.var.unmet_lost = (self.var.returnflowIrr + self.var.returnflowNonIrr + self.var.addtoevapotrans) \
                                      * (1 - unmet_div_ww)
            else:  # only irrigation is considered
                self.var.unmet_lost = (self.var.returnflowIrr + self.var.addtoevapotrans) * (1 - unmet_div_ww)

            # self.var.waterDemandLost = self.var.act_totalWaterConsumption + self.var.addtoevapotrans
            self.var.unmet_lostirr = (self.var.returnflowIrr + self.var.addtoevapotrans) * (1 - unmet_div_ww)
            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.var.unmet_lostNonirr = self.var.returnflowNonIrr * (1 - unmet_div_ww)

            self.var.returnflowIrr = self.var.returnflowIrr * unmet_div_ww
            self.var.addtoevapotrans = self.var.addtoevapotrans * unmet_div_ww
            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.var.returnflowNonIrr = self.var.returnflowNonIrr * unmet_div_ww
            
            if self.var.includeWastewaterPits:
                shareNonIrrReturnFlowToGW = globals.inZero.copy()
                if 'pitLatrinShare' in binding:
                    shareNonIrrReturnFlowToGW = loadmap('pitLatrinShare')
                self.var.pitLatrinToGW = self.var.returnflowNonIrr * shareNonIrrReturnFlowToGW
                self.var.returnflowNonIrr = self.var.returnflowNonIrr * (1 - shareNonIrrReturnFlowToGW)
                
            if self.var.includeWastewater & self.var.includeIndusDomesDemand:  # all demands are taken into account
                ## create domestic, industry returnFlows
                # Simple implementation - not precise. Don't allow livestock returnFlow
                # better, is to calculate sectoral returnflows rate based on withdrawal, 1) for simple approahc 2) sourcesector fraction 3) unmetdemand - limitAbstraction = FALSE
                self.var.wwtEffluentsGenerated_domestic = self.var.returnflowNonIrr.copy() * divideValues(self.var.frac_domestic, self.var.frac_domestic + self.var.frac_industry) # [m]
                self.var.wwtEffluentsGenerated_industry = self.var.returnflowNonIrr.copy() * divideValues(self.var.frac_industry, self.var.frac_domestic + self.var.frac_industry)
                self.var.wwtEffluentsGenerated = self.var.wwtEffluentsGenerated_domestic + self.var.wwtEffluentsGenerated_industry
            
                self.var.wwtSewerCollection_domestic = np.where(self.var.wwtColArea > 0,
                                                                self.var.wwtEffluentsGenerated_domestic, 0.)
                self.var.wwtSewerCollection_industry = np.where(self.var.wwtColArea > 0,
                                                                self.var.wwtEffluentsGenerated_industry, 0.)
                self.model.wastewater_module.dynamic()

                self.var.returnflowNonIrr = np.maximum(self.var.returnflowNonIrr - self.var.wwtSewerCollection, 0.)
                self.var.wwtSewerCollectedBySoruce = self.var.wwtEffluentsGenerated - self.var.returnflowNonIrr

            # returnflow to river and to evapotranspiration
            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                #if self.var.includeWastewater:
                    # add uncollected wastewater
                #    uncollectedWWT = self.var.wwtSewerCollection * self.var.cellArea - \
                #                     self.var.wwtExportedCollected - self.var.wwtSewerCollected  # M3
                #    self.var.returnflowNonIrr += uncollectedWWT / self.var.cellArea
                self.var.returnFlow = self.var.returnflowIrr + self.var.returnflowNonIrr
            else:  # only irrigation is considered
                self.var.returnFlow = self.var.returnflowIrr

            # add wastewater discharge to river to returnFlow - so they are sent to routing
            if self.var.includeWastewater & self.var.includeIndusDomesDemand:
                self.var.returnFlow += self.var.wwtOverflowOutM

            self.var.waterabstraction = self.var.nonFossilGroundwaterAbs + self.var.unmetDemand + \
                                        self.var.act_SurfaceWaterAbstract

            # agents: monthly withdrawal per adminSegment, switch off / relax the irrigation fractions
            self.agents.end_of_day(act_irrWithdrawalSW, act_irrWithdrawalGW)

            # ---------------------------------------------

    def dynamic_output(self):
        """
        Variables only for the output (moved from routing_kinematic.py 2026-11-04), computed after the routing and
        only if they are in the output settings:
        humanConsumption, humanUse, natureUse (always 0) and the averages per adminSegment
        (ETRefAverage_segments, precipEffectiveAverage_segments, head_segments, gwdepth_adjusted_segments,
        gwdepth_segments) and adminSegments_area
        """

        if not hasattr(self, 'outputNames'):
            from cwatm.management_modules.globals import outMap, outTss
            # entries are variable names, or after output.initial lists [file, variable name, ...]
            self.outputNames = {str(e[1] if isinstance(e, list) else e).split('[')[0].strip()
                                for names in list(outMap.values()) + list(outTss.values()) for e in names}
        out = self.outputNames

        if 'humanConsumption' in out or 'humanUse' in out:
            self.var.humanConsumption = globals.inZero.copy()
            self.var.humanUse = globals.inZero.copy()
            if 'includeCrops' in option:
                if checkOption('includeCrops'):
                    for i in range(len(self.var.Crops)):
                        self.var.humanConsumption += self.var.actTransTotal_crops_nonIrr[i]
                        self.var.humanUse += self.var.actTransTotal_crops_nonIrr[i]
            self.var.humanConsumption += (self.var.act_nonIrrConsumption + self.var.actTransTotal_paddy +
                                          self.var.addtoevapotrans + self.var.actTransTotal_nonpaddy +
                                          self.var.sum_openWaterEvap)
            self.var.humanUse += (self.var.act_nonIrrWithdrawal + self.var.act_irrWithdrawal)
            # + self.var.sum_openWaterEvap # + self.var.leakage # + reservoir evaporation

        if 'natureUse' in out:
            # not computed (idea: actTransTotal_grasslands - humanUse + EvapoChannel + sum_actBareSoilEvap +
            # sum_interceptEvap + EvapWaterBodyM)
            self.var.natureUse = globals.inZero.copy()

        if 'adminSegments' in binding:
            segIndex = self.var.adminSegmentsIndex
            if 'ETRefAverage_segments' in out:
                self.var.ETRefAverage_segments = segIndex.average(self.var.ETRef)
            if 'precipEffectiveAverage_segments' in out:
                self.var.precipEffectiveAverage_segments = segIndex.average(self.var.infiltration[1])
            if self.var.modflow:
                if 'head_segments' in out:
                    self.var.head_segments = segIndex.average(self.var.head)
                if 'gwdepth_adjusted_segments' in out:
                    self.var.gwdepth_adjusted_segments = segIndex.average(self.var.gwdepth_adjusted)
                if 'gwdepth_segments' in out:
                    self.var.gwdepth_segments = segIndex.average(self.var.gwdepth)
            if 'adminSegments_area' in out:
                # agricultural area (grassland + paddy + non-paddy irrigated) of each admin segment [m2]
                # (before 2026-11-04: average per cell of the segment instead of the segment total)
                self.var.adminSegments_area = segIndex.total(
                    (self.var.fracVegCover[1] + self.var.fracVegCover[2] + self.var.fracVegCover[3]) * self.var.cellArea)
