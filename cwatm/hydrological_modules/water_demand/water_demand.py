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

from cwatm.management_modules.replace_pcr import npareatotal, npareaaverage, npareamaximum, AreaIndex
from cwatm.management_modules.messages import CWATMError, CWATMWarning
from cwatm.management_modules.globals import dateVar, option
from cwatm.management_modules.data_handling import (returnBool, binding, loadmap, divideValues, checkOption,
                                                     readnetcdf2, regularZones)
from cwatm.hydrological_modules.water_demand.domestic import waterdemand_domestic
from cwatm.hydrological_modules.water_demand.industry import waterdemand_industry
from cwatm.hydrological_modules.water_demand.livestock import waterdemand_livestock
from cwatm.hydrological_modules.water_demand.irrigation import waterdemand_irrigation
from cwatm.hydrological_modules.water_demand.environmental_need import waterdemand_environmental_need, ENVFLOW_OFF
from cwatm.hydrological_modules.water_demand.wastewater import waterdemand_wastewater


def set_zero(var, names):
    """
    Set each variable in names to its own map of zeros (globals.inZero.copy()).

    Parameters
    ----------
    var : object
        Model variable container (self.var)
    names : list of str
        Names of the variables
    """
    for name in names:
        setattr(var, name, globals.inZero.copy())


# withdrawal of each sector from each source [m]: Desal_Domestic ... GW_Irrigation
SECTOR_SOURCE = [source + '_' + sector
                 for source in ('Desal', 'Channel', 'Lift', 'wwt', 'Lake', 'Res', 'GW')
                 for sector in ('Domestic', 'Industry', 'Livestock', 'Irrigation')]

def split_sectors(total, pots):
    """
    Split the water of one source over the sectors, one after the other.

    Each sector gets at most its potential: part_k = min(rest, pots[k]), rest = total - part_1 - ... - part_k
    (subtracted one by one in this order, as in the code before 2026-11, so the results are bit-identical).

    Parameters
    ----------
    total : ndarray
        Water of the source [m].
    pots : sequence of ndarray
        Potential abstraction of each sector in the order of the allocation (Domestic, Livestock, Industry,
        Irrigation) [m].

    Returns
    -------
    tuple of (parts, rest)
        parts : list of ndarray, the water of each sector [m]; rest : ndarray, total minus all parts [m]
    """
    parts = []
    rest = total
    for pot in pots:
        part = np.minimum(rest, pot)
        parts.append(part)
        rest = rest - part
    return parts, rest


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
    Main coordinating class for integrated water demand calculations across all sectors.
    
    This class orchestrates water demand calculations for domestic, industrial, livestock,
    irrigation, environmental, and wastewater sectors. It manages complex water allocation
    algorithms, coordinates agent-based modeling for irrigation and domestic sectors,
    handles water abstraction fractions from different sources (surface water, groundwater,
    lakes, reservoirs), and processes command area operations for efficient water distribution.
    
    The class implements sophisticated water demand-supply balance algorithms, manages
    sector-specific and source-specific abstraction strategies, and handles desalination
    operations when configured. It supports both traditional grid-based modeling and
    agent-based approaches for enhanced spatial representation of water management decisions.
    
    Parameters
    ----------
    model : object
        The main CWatM model instance containing all model variables and configuration.
        
    Attributes
    ----------
    var : object
        Reference to model variables container for accessing and storing model state variables.
    model : object
        Reference to the main CWatM model instance.
    domestic : waterdemand_domestic
        Domestic water demand calculation module.
    industry : waterdemand_industry
        Industrial water demand calculation module.
    livestock : waterdemand_livestock
        Livestock water demand calculation module.
    irrigation : waterdemand_irrigation
        Irrigation water demand calculation module.
    environmental_need : waterdemand_environmental_need
        Environmental flow requirements calculation module.
    wastewater : waterdemand_wastewater
        Wastewater treatment and reuse calculation module.
        
    Notes
    -----
    This is the main orchestrating module that coordinates all water demand sectors.
    Industrial, domestic, and livestock demands are based on precalculated spatial maps,
    while agricultural water demand is computed dynamically based on crop water requirements.
    
    The module supports advanced features including:
    - Agent-based modeling for spatially explicit water management decisions
    - Sector-specific and source-specific water abstraction strategies
    - Command area operations for coordinated irrigation water allocation
    - Integration with MODFLOW for groundwater-surface water interactions
    - Desalination operations for augmenting water supply
    - Complex water allocation algorithms with priority-based distribution










    **Global variables**
    =========================================  ==========    ================================================================  =====
    Variable [self.var]                        Type          Description                                                       Unit 
    =========================================  ==========    ================================================================  =====
    channelStorage                             Array         Channel water storage                                             m3   
    unmetDemand_runningSum                     Array         Sum of the unmet demand since the start                           m    
    modflow                                    Flag          True if modflow_coupling = True                                   bool 
    pot_domesticConsumption                    Array         Potential domestic water consumption                              m    
    load_initial                               Function      Function: loads a variable from the initial conditions            --   
    readAvlStorGroundwater                     Array         storGroundwater available for abstraction (0 below a threshold)   m    
    pot_industryConsumption                    Array         Potential industry water consumption                              m    
    loadInit                                   Flag          True if initial conditions are loaded (initLoad)                  bool 
    includeDesal                               Flag          True if includeDesalination = True                                bool 
    unlimitedDesal                             Flag          True if unlimitedDesalinationCapacity = True                      bool 
    desalAnnualCap                             Dict          Desalination capacity per year (Excel settings file)              m3   
    efficiencyPaddy                            Array         Input irrPaddy_efficiency: paddy irrigation efficiency            frac 
    efficiencyNonpaddy                         Array         Input irrNonPaddy_efficiency: non-paddy irrigation efficiency     frac 
    efficiencyNonpaddyWithdrawal               Array         efficiencyNonpaddy / fraction_IncreaseIrrigation_Nonpaddy         frac 
    returnfractionIrr                          Array         Input irrigation_returnfraction: return part of the losses        frac 
    irrPaddyDemand                             Array         Paddy irrigation demand                                           m    
    compress_LR                                Array         Boolean map: outlet cells of lakes/reservoirs (compress)          --   
    decompress_LR                              Array         Cell numbers of the lake/reservoir outlets (decompress)           --   
    MtoM3C                                     Array         Cell area at the lake/reservoir outlets (m -> m3, compressed)     m2   
    resId_restricted                           Array         Reservoir ID of the reservoirs restricted to wastewater           --   
    waterBodyBuffer                            Array         Water body number of the buffer around lakes and reservoirs       --   
    waterBodyBufferIndex                       Object        Index of waterBodyBuffer for area total/maximum (AreaIndex)       --   
    waterBodyBuffer_wwt                        Array         waterBodyBuffer for the reservoirs with wastewater reuse          --   
    waterBodyBuffer_wwtIndex                   Object        Index of waterBodyBuffer_wwt for area total/maximum               --   
    reservoir_releases_excel_option            Flag          True if reservoir releases come from the Excel settings file      bool 
    lakeResStorage_release_ratioC              Array         Excel settings: release ratio of the reservoirs (compressed)      --   
    M3toM                                      Array         Coefficient m3 -> m (= InvCellArea)                               1 m-2
    MtoM3                                      Array         Coefficient m -> m3 (= cellArea)                                  m2   
    InvDtSec                                   Array         Inverse of the seconds per time step (1/86400)                    1 s-1
    InvCellArea                                Array         Inverse of the cell area                                          1 m-2
    GW_pumping                                 Flag          True if Groundwater_pumping = True (pumping sent to MODFLOW)      bool 
    availableGWStorageFraction                 Array         MODFLOW: fraction of the groundwater storage that can be pumped   frac 
    groundwater_storage_available              Array         MODFLOW: groundwater storage available for pumping                m    
    gwstorage_full                             Number        MODFLOW: groundwater storage at full capacity                     m    
    wwtColArea                                 Array         Wastewater: collection area (ID of the treatment plant)           --   
    wwtSewerCollection                         Array         Wastewater: sewer collection (domestic + industry)                m    
    wwtOverflowOutM                            Array         Wastewater: overflow of the treatment plants                      m    
    fracVegCover                               Array         Land cover fractions (0 forest, 1 grassland, 2 paddy, ...)        frac 
    adminSegments                              Array         Agent areas (administrative segments) of the irrigation agents    --   
    cellArea                                   Array         Cell area                                                         m2   
    nonFossilGroundwaterAbs                    Array         Non-fossil groundwater abstraction                                m    
    includeWastewater                          Flag          True if includeWastewater = True                                  bool 
    waterBodyTyp_unchanged                     Array         Water body type of the settings (1 lake, 2 reservoir)             --   
    lakeVolumeM3C                              Array         Lake volume at the outlets (compressed)                           m3   
    lakeStorageC                               Array         Lake and reservoir storage at the outlets (compressed)            m3   
    reservoirStorageM3C                        Array         Reservoir storage at the outlets (compressed)                     m3   
    lakeResStorageC                            Array         Lake + reservoir storage at the outlets (compressed)              m3   
    lakeResStorage                             Array         Lake + reservoir storage at the outlet cells                      m3   
    reservoir_supply                           Array         Excel settings: daily release fraction for the command areas      frac 
    waterBodyTypCTemp                          Array         Water body type of the current year (compressed)                  --   
    smalllakeVolumeM3                          Array         Small lake volume (Puls)                                          m3   
    smalllakeStorage                           Array         Small lake storage                                                m3   
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
    act_smallLakeResAbst                       Array         Abstractions from small lakes at demand location                  m    
    returnFlow                                 Array         Return flow to the channels (irrigation + non-irrigation)         m    
    act_nonIrrConsumption                      Array         Non-irrigation consumption                                        m    
    act_nonIrrWithdrawal                       Array         Non-irrigation withdrawals                                        m    
    act_irrWithdrawal                          Array         Irrigation withdrawals                                            m    
    waterdemandFixed                           Flag          True if waterdemandFixed = True: demand of a fixed year           bool 
    modfPumpingM                               Array         MODFLOW: pumping since the last MODFLOW run                       m    
    activate_domestic_agents                   Flag          True if activate_domestic_agents = True                           bool 
    domesticDemand                             Array         Domestic water demand (withdrawal)                                m    
    swAbstractionFraction_domestic             Array         Domestic agents: surface water share of the request               frac 
    demand_unit                                Flag          Non-irrigation demand maps in m/day (True) or Mm3 per period      bool 
    sectorSourceAbstractionFractions           Flag          True if sector- and source-specific abstraction fractions         bool 
    swAbstractionFraction_Channel_Domestic     Array         Input: share of the domestic demand from channels                 frac 
    swAbstractionFraction_Lift_Domestic        Array         Input: share of the domestic demand from lift areas               frac 
    swAbstractionFraction_Res_Domestic         Array         Input: share of the domestic demand from reservoirs               frac 
    swAbstractionFraction_Lake_Domestic        Array         Input: share of the domestic demand from lakes                    frac 
    gwAbstractionFraction_Domestic             Array         Input: share of the domestic demand from groundwater              frac 
    dom_efficiency                             Array         Domestic consumption / withdrawal, at most 1                      frac 
    envFlow                                    Array         Channel storage kept for the environmental flow                   m    
    industryDemand                             Array         Industry water demand (withdrawal)                                m    
    ind_efficiency                             Array         Industry consumption / withdrawal, at most 1                      frac 
    unmetDemand                                Array         Unmet demand, taken from fossil groundwater (limitAbstraction F)  m    
    irrDemand                                  Array         Irrigation demand per land cover                                  m    
    irrNonpaddyDemand                          Array         Non-paddy irrigation demand                                       m    
    totalIrrDemand                             Array         Irrigation demand                                                 m    
    livestockDemand                            Array         Livestock water demand (withdrawal)                               m    
    pot_livestockConsumption                   Array         Potential livestock consumption (= livestock demand)              m    
    liv_efficiency                             Number        Livestock consumption / withdrawal (= 1)                          frac 
    wwtEffluentsGenerated                      Array         Wastewater: effluents of domestic + industry                      m    
    wwtSewerCollection_domestic                Array         Wastewater: domestic effluents collected by sewers                m    
    wwtSewerCollection_industry                Array         Wastewater: industry effluents collected by sewers                m    
    includeIndusDomesDemand                    Flag          True if includeIndusDomesDemand = True                            bool 
    activate_irrigation_agents                 Flag          True if activate_irrigation_agents = True                         bool 
    relaxGWagent                               Array         Agents: relax counter of the groundwater fraction                 --   
    relaxSWagent                               Array         Agents: relax counter of the surface water fraction               --   
    irrWithdrawalSW_max                        Array         Agents: surface water request per month (segment average)         m3   
    irrWithdrawalGW_max                        Array         Agents: groundwater request per month (segment average)           m3   
    relax_irrigation_agents                    Flag          True if relax_irrigation_agents = True                            bool 
    relax_abstraction_fraction_initial         Array         Agents: initial fraction after relaxation (default 0.5)           frac 
    waterdemandFixedYear                       Number        Year of the demand maps with waterdemandFixed                     year 
    swAbstractionFraction_Channel_Livestock    Array         Input: share of the livestock demand from channels                frac 
    swAbstractionFraction_Channel_Industry     Array         Input: share of the industry demand from channels                 frac 
    swAbstractionFraction_Channel_Irrigation   Array         Input: share of the irrigation demand from channels               frac 
    swAbstractionFraction_Lake_Livestock       Array         Input: share of the livestock demand from lakes                   frac 
    swAbstractionFraction_Lake_Industry        Array         Input: share of the industry demand from lakes                    frac 
    swAbstractionFraction_Lake_Irrigation      Array         Input: share of the irrigation demand from lakes                  frac 
    swAbstractionFraction_Res_Livestock        Array         Input: share of the livestock demand from reservoirs              frac 
    swAbstractionFraction_Res_Industry         Array         Input: share of the industry demand from reservoirs               frac 
    swAbstractionFraction_Res_Irrigation       Array         Input: share of the irrigation demand from reservoirs             frac 
    othAbstractionFraction_Desal_Domestic      Array         Input: share of the domestic demand from desalination             frac 
    othAbstractionFraction_Desal_Livestock     Array         Input: share of the livestock demand from desalination            frac 
    othAbstractionFraction_Desal_Industry      Array         Input: share of the industry demand from desalination             frac 
    othAbstractionFraction_Desal_Irrigation    Array         Input: share of the irrigation demand from desalination           frac 
    wwtAbstractionFraction_Res_Domestic        Array         Input: share of the domestic demand from wastewater reuse         frac 
    wwtAbstractionFraction_Res_Livestock       Array         Input: share of the livestock demand from wastewater reuse        frac 
    wwtAbstractionFraction_Res_Industry        Array         Input: share of the industry demand from wastewater reuse         frac 
    wwtAbstractionFraction_Res_Irrigation      Array         Input: share of the irrigation demand from wastewater reuse       frac 
    gwAbstractionFraction_Livestock            Array         Input: share of the livestock demand from groundwater             frac 
    gwAbstractionFraction_Industry             Array         Input: share of the industry demand from groundwater              frac 
    gwAbstractionFraction_Irrigation           Array         Input: share of the irrigation demand from groundwater            frac 
    using_reservoir_command_areas              Flag          True if using_reservoir_command_areas = True                      bool 
    load_command_areas                         Flag          True if reservoir_command_areas is used                           bool 
    load_command_areas_wwt                     Flag          True if reservoir_command_areas_restricted is used                bool 
    reservoir_command_areas                    Array         Command areas of the reservoirs (no lakes / restricted res.)      --   
    reservoir_command_areas_wwt                Array         Command areas of the reservoirs restricted to wastewater          --   
    reservoir_command_areasIndex               Object        Index of reservoir_command_areas for area total/maximum           --   
    reservoir_command_areas_wwtIndex           Object        Index of reservoir_command_areas_wwt for area total/maximum       --   
    Water_conveyance_efficiency                Array         Canal conveyance efficiency (MODFLOW only, 1 otherwise)           frac 
    segmentArea                                Array         Area of the command area (cellArea outside)                       m2   
    segmentArea_wwt                            Array         Area of the wastewater command area (cellArea outside)            m2   
    canals                                     Array         Canal map (command area number); whole area if none               --   
    canalsIndex                                Object        Index of canals for the area maximum of the leakage (AreaIndex)   --   
    commandAreasRelaxGwAbstraction             Array         GW fraction for irrigation in command areas (agents)              frac 
    Water_conveyance_efficiencyC               Array         Water_conveyance_efficiency at the outlets (compressed)           frac 
    resId_restrictedC                          Array         resId_restricted at the lake/reservoir outlets (compressed)       --   
    frac_industry                              Array         Industry share of the non-irrigation demand (nonIrrDemand)        frac 
    frac_domestic                              Array         Domestic share of the non-irrigation demand (nonIrrDemand)        frac 
    frac_livestock                             Array         Livestock share of the non-irrigation demand (nonIrrDemand)       frac 
    canals_wwt                                 Array         Canal map (command area number) for wastewater reuse              --   
    canalsArea                                 Array         Area of the canals of a command area                              m2   
    canalsAreaC                                Array         canalsArea at the reservoir outlets (compressed)                  m2   
    canalsArea_wwt                             Array         Area of the wastewater canals of a command area                   m2   
    canalsArea_wwtC                            Array         canalsArea_wwt at the reservoir outlets (compressed)              m2   
    swAbstractionFraction_Lift_Livestock       Array         Input: share of the livestock demand from lift areas              frac 
    swAbstractionFraction_Lift_Industry        Array         Input: share of the industry demand from lift areas               frac 
    swAbstractionFraction_Lift_Irrigation      Array         Input: share of the irrigation demand from lift areas             frac 
    using_lift_areas                           Flag          True if using_lift_areas = True                                   bool 
    lift_command_areas                         Array         Lift areas (lift area number)                                     --   
    lift_command_areasIndex                    Object        Index of lift_command_areas for the area total (AreaIndex)        --   
    allocSegments                              Array         Segments (e.g. catchments) for the average baseflow, cells > 0    --   
    swAbstractionFraction                      Array         Input swAbstractionFrac: surface water share of the demand        frac 
    allocation_zone                            Array         Zonal abstraction: zone of allocation_area x allocation_area      --   
    allocation_zoneIndex                       Object        Index of allocation_zone for area total, all cells (AreaIndex)    --   
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
    act_DesalWaterAbstractM3                   Array         Not used (always 0)                                               m3   
    AvlDesalM3                                 Array         Desalination capacity of the day                                  m3   
    act_channelAbst                            Array         Channel abstraction                                               m    
    act_channelAbstract_Lift                   Array         Channel abstraction in lift areas at the channel location         m    
    Lift_Other                                 Array         Lift water not attributed to a sector                             m    
    abstractedLakeReservoirM3C                 Array         abstractedLakeReservoirM3 (compressed)                            m3   
    remainNeed                                 Array         Wastewater: demand for reuse (pot_wwt_*, output only)             m    
    act_ResAbst_wwt                            Array         Wastewater reuse from restricted reservoirs at demand location    m    
    act_lakeAbst                               Array         Abstraction from lakes at demand location                         m    
    act_ResAbst                                Array         Abstraction from reservoirs at demand location                    m    
    leakageC_daily                             Array         Canal leakage of the reservoirs (compressed)                      m3   
    leakageCanalsC_M                           Array         Canal leakage per canal area at the outlets (compressed)          m    
    Channel_Domestic_fromZone                  Array         Zonal abstraction: channel water for domestic                     m    
    Channel_Livestock_fromZone                 Array         Zonal abstraction: channel water for livestock                    m    
    Channel_Industry_fromZone                  Array         Zonal abstraction: channel water for industry                     m    
    Channel_Irrigation_fromZone                Array         Zonal abstraction: channel water for irrigation                   m    
    Channel_Other                              Array         Zonal channel water not attributed to a sector                    m    
    GW_Domestic_fromZone                       Array         Zonal abstraction: groundwater for domestic                       m    
    GW_Livestock_fromZone                      Array         Zonal abstraction: groundwater for livestock                      m    
    GW_Industry_fromZone                       Array         Zonal abstraction: groundwater for industry                       m    
    GW_Irrigation_fromZone                     Array         Zonal abstraction: groundwater for irrigation                     m    
    GW_Other                                   Array         Zonal groundwater not attributed to a sector                      m    
    PumpingM3_daily                            Array         MODFLOW: groundwater pumping of the day                           m3   
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
        Initialize the water demand coordination module and all sectoral demand modules.
        
        Establishes the main water demand orchestration system by creating instances of all
        sectoral water demand modules (domestic, industrial, livestock, irrigation, environmental,
        and wastewater) and setting up references to the model variables and configuration.
        This initialization prepares the integrated water demand calculation framework.
        
        Parameters
        ----------
        model : object
            The main CWatM model instance containing model variables, configuration settings,
            and all necessary data structures for water demand calculations.
            
        Notes
        -----
        This method instantiates all sectoral water demand modules that will be coordinated
        by this main class. Each sectoral module is passed the same model instance to ensure
        consistent access to model variables and configuration across all water demand sectors.
        """
        self.var = model.var
        self.model = model

        self.domestic = waterdemand_domestic(model)
        self.industry = waterdemand_industry(model)
        self.livestock = waterdemand_livestock(model)
        self.irrigation = waterdemand_irrigation(model)
        self.environmental_need = waterdemand_environmental_need(model)
        self.wastewater = waterdemand_wastewater(model)

    def initial(self):
        """
        Initialize the comprehensive water demand system configuration and all model variables.
        
        This method performs extensive initialization of the integrated water demand system,
        setting up configuration flags, loading spatial data layers, configuring agent-based
        modeling components, establishing water abstraction fractions for different sectors
        and sources, and initializing command area operations. It handles both simple and
        advanced water demand configurations including sector-specific abstraction strategies,
        desalination operations, wastewater treatment, and complex spatial allocation systems.
        
        The initialization process includes:
        - Configuration of water demand activation flags and sectoral inclusion options
        - Setup of agent-based modeling for irrigation and domestic sectors with spatial allocation
        - Loading and processing of abstraction fraction maps for different water sources and sectors
        - Configuration of command area operations for coordinated water distribution
        - Initialization of desalination and wastewater treatment components
        - Setup of lift irrigation systems and canal conveyance efficiency parameters
        - Configuration of groundwater-surface water partitioning algorithms
        - Initialization of all tracking variables for water demand, withdrawal, and consumption
        
        Notes
        -----
        This method handles complex conditional initialization based on configuration options:
        
        Water Demand Activation:
        - Configures whether water demand calculations are enabled
        - Sets flags for including industrial, domestic, and livestock demands vs irrigation-only
        - Activates wastewater treatment and reuse components when configured
        
        Agent-Based Modeling:
        - Sets up administrative segments for spatially explicit water management decisions
        - Configures irrigation and domestic agent systems with withdrawal limits and relaxation factors
        - Handles agent-based allocation of water resources across spatial administrative units
        
        Abstraction Fractions:
        - Configures sector-specific and source-specific abstraction strategies when enabled
        - Sets up abstraction fractions for channels, lakes, reservoirs, and groundwater by sector
        - Handles desalination and wastewater reuse abstraction fractions
        - Configures groundwater abstraction limitations and surface water partitioning
        
        Command Area Operations:
        - Sets up reservoir command areas for coordinated irrigation water distribution
        - Configures canal systems and conveyance efficiency for water transport
        - Handles both regular and wastewater treatment reservoir command areas
        - Sets up lift irrigation areas for pumping operations
        
        Spatial Allocation:
        - Configures allocation zones for water demand-supply balancing
        - Sets up spatial aggregation systems for efficient water resource management
        - Handles coordinate system transformations and spatial indexing
        
        Variable Initialization:
        - Initializes extensive arrays for tracking water demands, withdrawals, and consumption
        - Sets up sectoral water use efficiency parameters
        - Configures unmet demand tracking and fossil groundwater abstraction variables
        - Initializes MODFLOW coupling variables for groundwater-surface water interactions
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

        # Variables related to agents =========================
        self.var.activate_domestic_agents = False
        if 'activate_domestic_agents' in option:
            if checkOption('activate_domestic_agents'):
                self.var.activate_domestic_agents = True

        self.var.activate_irrigation_agents = False
        if 'activate_irrigation_agents' in option:
            if checkOption('activate_irrigation_agents'):
                self.var.activate_irrigation_agents = True

        set_zero(self.var, ['relaxGWagent', 'relaxSWagent', 'irrWithdrawalSW_max', 'irrWithdrawalGW_max'])

        # irrigation agents need adminSegments: without them the request maps (irrWithdrawal*_max) stay 0, the
        # irrigation abstraction is capped to 0 and relax_abstraction_fraction_initial does not exist
        if self.var.activate_irrigation_agents and 'adminSegments' not in binding and \
                ('irrigation_agent_SW_request_month_m3' in binding or 'irrigation_agent_GW_request_month_m3' in binding):
            raise CWATMError("Error 180: activate_irrigation_agents = True with irrigation_agent_*_request_month_m3 "
                             "but no adminSegments map in the settings file\n"
                             "Add adminSegments (the agent areas) or set activate_irrigation_agents = False\n")

        self.var.relax_irrigation_agents = False
        if 'relax_irrigation_agents' in option:
            if checkOption('relax_irrigation_agents'):
                self.var.relax_irrigation_agents = True

        if 'adminSegments' in binding:
            # adminSegments (administrative segment) are collections of cells that are associated together, ie Agents
            # Cells within the same administrative segment have the same positive integer value.
            # Cells with non-positive integer values are all associated together.
            # Irrigation agents use adminSegments

            self.var.adminSegments = loadmap('adminSegments').astype(int)
            self.var.adminSegments = np.where(self.var.adminSegments > 0, self.var.adminSegments, 0)
            # index for the area totals and averages per segment (adminSegments is not changed after this)
            self.var.adminSegmentsIndex = AreaIndex(self.var.adminSegments, onlypositive=False)

            if 'irrigation_agent_SW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                self.var.irrWithdrawalSW_max = npareaaverage(
                    loadmap('irrigation_agent_SW_request_month_m3') + globals.inZero.copy(),
                    self.var.adminSegments)

                # saved with relax_irrigation_agents (initcondition.py), also without relax_sw_agent
                if self.var.loadInit and ('relax_sw_agent' in binding or self.var.relax_irrigation_agents):
                    self.var.relaxSWagent = self.var.load_initial('relaxSWagent', default=globals.inZero.copy())
                elif 'relax_sw_agent' in binding:
                    self.var.relaxSWagent = loadmap('relax_sw_agent')

            if 'irrigation_agent_GW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                self.var.irrWithdrawalGW_max = npareaaverage(
                    loadmap('irrigation_agent_GW_request_month_m3') + globals.inZero.copy(),
                    self.var.adminSegments)

                # saved with relax_irrigation_agents (initcondition.py), also without relax_gw_agent
                if self.var.loadInit and ('relax_gw_agent' in binding or self.var.relax_irrigation_agents):
                    self.var.relaxGWagent = self.var.load_initial('relaxGWagent', default=globals.inZero.copy())
                elif 'relax_gw_agent' in binding:
                    self.var.relaxGWagent = loadmap('relax_gw_agent')

            if 'relax_abstraction_fraction_initial' in binding:
                self.var.relax_abstraction_fraction_initial = loadmap('relax_abstraction_fraction_initial') + globals.inZero.copy()
            else:
                self.var.relax_abstraction_fraction_initial = 0.5 + globals.inZero.copy()

        self.var.includeWastewaterPits = False
        if 'includePitLatrine' in option:
            self.var.includeWastewaterPits = checkOption('includePitLatrine')

        # in case fossil water abstraction is allowed this will be filled
        self.var.unmetDemand = globals.inZero.copy()
        self.var.unmetDemand_runningSum = self.var.load_initial('unmetDemand_runningSum', default=globals.inZero.copy())
        self.var.sectorSourceAbstractionFractions = False


        # =======================================================

        if checkOption('includeWaterDemand'):

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

                    if not checkOption('limitAbstraction'):
                        self.var.gwAbstractionFraction_Domestic = 1 + globals.inZero.copy()
                        self.var.gwAbstractionFraction_Livestock = 1 + globals.inZero.copy()
                        self.var.gwAbstractionFraction_Industry = 1 + globals.inZero.copy()
                        self.var.gwAbstractionFraction_Irrigation = 1 + globals.inZero.copy()
                    else:
                        self.var.gwAbstractionFraction_Domestic = loadmap('gwAbstractionFraction_Domestic')
                        self.var.gwAbstractionFraction_Livestock = loadmap('gwAbstractionFraction_Livestock')
                        self.var.gwAbstractionFraction_Industry = loadmap('gwAbstractionFraction_Industry')
                        self.var.gwAbstractionFraction_Irrigation = loadmap('gwAbstractionFraction_Irrigation')


            self.var.using_reservoir_command_areas = False
            self.var.using_reservoir_command_areas = checkOption('using_reservoir_command_areas', True)

            # groundwater abstraction fraction for irrigation in reservoir command areas after the 15th of each month
            # (read once here, used every day in dynamic)
            if self.var.sectorSourceAbstractionFractions and 'commandAreasRelaxGwAbstraction' in binding and self.var.using_reservoir_command_areas:
                self.var.commandAreasRelaxGwAbstraction = loadmap('commandAreasRelaxGwAbstraction')
            
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

            # non-irrigation input maps have for each month or year the unit m/day (True) or million m3/month (False)
            self.var.demand_unit = True
            if "demand_unit" in binding:
                self.var.demand_unit = returnBool('demand_unit')

            # allocation zone: regular grid of allocation_area x allocation_area cells, only for the zonal
            # abstraction (before 2026-11 built in every run with water demand, file read here)
            if 'zonal_abstraction' in option and checkOption('zonal_abstraction'):
                inner = 1
                if "allocation_area" in binding:
                    inner = int(loadmap('allocation_area'))
                self.var.allocation_zone = regularZones(inner)
                # index for the area functions per allocation zone (all cells, zone 0 is a zone)
                self.var.allocation_zoneIndex = AreaIndex(self.var.allocation_zone, onlypositive=False)

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
                                                            
    def dynamic(self):
        """
        Execute the complete dynamic water demand-supply allocation cycle for the current time step.
        
        This is the main orchestrating method that coordinates all aspects of water demand calculation,
        water source allocation, abstraction operations, and consumption tracking across all sectors.
        It implements sophisticated water allocation algorithms that balance demands against available
        supplies from multiple sources (surface water, groundwater, reservoirs, lakes, desalination,
        wastewater treatment) while respecting physical constraints, environmental requirements, and
        operational rules.
        
        The method executes a comprehensive water management cycle including:
        
        1. **Sectoral Demand Calculation**: Computes water demands for all active sectors (domestic,
           industrial, livestock, irrigation, environmental) using current meteorological conditions
           and socio-economic factors.
           
        2. **Water Source Assessment**: Evaluates available water supplies from all sources including
           channel storage, groundwater availability, reservoir storage, lake storage, desalination
           capacity, and treated wastewater supplies.
           
        3. **Demand-Supply Balancing**: Implements complex allocation algorithms to match demands
           with available supplies, considering spatial distribution, infrastructure constraints,
           and operational priorities.
           
        4. **Agent-Based Allocation**: When activated, processes agent-based water management decisions
           for irrigation and domestic sectors, handling spatial administrative units and their
           specific allocation rules and constraints.
           
        5. **Multi-Source Abstraction**: Orchestrates water abstraction from multiple sources using
           sector-specific and source-specific abstraction fractions, managing complex allocation
           hierarchies and constraint satisfaction.
           
        6. **Command Area Operations**: Executes coordinated water allocation within reservoir and
           canal command areas, handling conveyance losses and operational efficiency considerations.
           
        7. **Consumption and Return Flow**: Calculates actual water consumption by sector, computes
           return flows to water bodies, and tracks water use efficiency across all sectors.
           
        8. **Groundwater-Surface Water Integration**: When MODFLOW coupling is active, coordinates
           groundwater pumping with surface water abstractions, managing aquifer-river interactions
           and sustainable yield constraints.
        
        Notes
        -----
        This method implements the core water allocation logic of CWatM and handles numerous
        complex scenarios and configurations:
        
        **Temporal Dynamics**: 
        Handles both daily time step calculations and monthly/annual demand updates, managing
        temporal variability in water demands and supply availability. Supports fixed-year
        demand scenarios for scenario analysis and historical reconstructions.
        
        **Spatial Complexity**:
        Manages spatial heterogeneity in water demands, supply sources, infrastructure capacity,
        and allocation rules. Handles multi-scale allocation from individual grid cells to
        large administrative regions and command areas.
        
        **Sectoral Integration**:
        Coordinates water allocation across competing sectors with different priorities, use
        efficiencies, return flow characteristics, and operational constraints. Manages
        inter-sectoral water transfers and reuse opportunities.
        
        **Source Portfolio Management**:
        Optimizes water allocation across diverse supply portfolios including conventional
        sources (rivers, lakes, groundwater) and alternative sources (desalination, wastewater
        reuse), considering economic and environmental constraints.
        
        **Infrastructure Constraints**:
        Accounts for physical infrastructure limitations including canal capacity, pumping
        capacity, conveyance losses, treatment plant capacity, and distribution system
        constraints that affect water delivery efficiency.
        
        **Environmental Protection**:
        Enforces environmental flow requirements, groundwater sustainability constraints,
        and ecosystem water needs while optimizing human water use efficiency and reliability.
        
        **Unmet Demand Management**:
        Tracks and manages unmet water demands through demand management strategies, alternative
        source development, and adaptive allocation algorithms that respond to water scarcity
        conditions.
        
        The method supports both simple water allocation scenarios for basic hydrological
        modeling and highly sophisticated water management configurations for detailed
        water resources planning and management applications.
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
                self.var.act_irrWithdrawalSW_month = globals.inZero.copy()
                self.var.act_irrWithdrawalGW_month = globals.inZero.copy()

                if 'irrigation_agent_SW_request_month_m3' in binding and self.var.activate_irrigation_agents:

                    # These are read at the beginning of each month as they are updated by several relax functions
                    # and turned off once satisfying request
                    if self.var.sectorSourceAbstractionFractions:
                        self.var.swAbstractionFraction_Channel_Irrigation = loadmap('swAbstractionFraction_Channel_Irrigation')
                        if self.var.using_lift_areas:
                            self.var.swAbstractionFraction_Lift_Irrigation = loadmap('swAbstractionFraction_Lift_Irrigation')
                        self.var.swAbstractionFraction_Lake_Irrigation = loadmap('swAbstractionFraction_Lake_Irrigation')
                        self.var.swAbstractionFraction_Res_Irrigation = loadmap('swAbstractionFraction_Res_Irrigation')
                    else:
                        self.var.swAbstractionFraction_Channel_Irrigation = 1 + globals.inZero.copy()
                        if self.var.using_lift_areas:
                            self.var.swAbstractionFraction_Lift_Irrigation = 1 + globals.inZero.copy()
                        self.var.swAbstractionFraction_Lake_Irrigation = 1 + globals.inZero.copy()
                        self.var.swAbstractionFraction_Res_Irrigation = 1 + globals.inZero.copy()

                    if self.var.relax_irrigation_agents:
                        self.var.swAbstractionFraction_Channel_Irrigation = np.where(
                            self.var.relaxSWagent > 0,
                            self.var.relax_abstraction_fraction_initial / self.var.relaxSWagent,
                            self.var.swAbstractionFraction_Channel_Irrigation)
                        if self.var.using_lift_areas:
                            self.var.swAbstractionFraction_Lift_Irrigation = np.where(
                                self.var.relaxSWagent > 0,
                                self.var.relax_abstraction_fraction_initial / self.var.relaxSWagent,
                                self.var.swAbstractionFraction_Lift_Irrigation)
                        self.var.swAbstractionFraction_Lake_Irrigation = np.where(
                            self.var.relaxSWagent > 0,
                            self.var.relax_abstraction_fraction_initial / self.var.relaxSWagent,
                            self.var.swAbstractionFraction_Lake_Irrigation)
                        self.var.swAbstractionFraction_Res_Irrigation = np.where(
                            self.var.relaxSWagent > 0,
                            self.var.relax_abstraction_fraction_initial / self.var.relaxSWagent,
                            self.var.swAbstractionFraction_Res_Irrigation)

                if 'irrigation_agent_GW_request_month_m3' in binding and self.var.activate_irrigation_agents:

                    if self.var.sectorSourceAbstractionFractions and checkOption('limitAbstraction'):
                        self.var.gwAbstractionFraction_Irrigation = loadmap('gwAbstractionFraction_Irrigation')
                    else:
                        self.var.gwAbstractionFraction_Irrigation = 1 + globals.inZero.copy()

                    if self.var.relax_irrigation_agents:
                        self.var.gwAbstractionFraction_Irrigation = np.where(
                            self.var.relaxGWagent > 0,
                            self.var.relax_abstraction_fraction_initial / self.var.relaxGWagent,
                            self.var.gwAbstractionFraction_Irrigation)

                if 'commandAreasRelaxGwAbstraction' in binding and self.var.sectorSourceAbstractionFractions:
                    self.var.gwAbstractionFraction_Irrigation = np.where(self.var.reservoir_command_areas > 0,
                                                                         0.01,
                                                                         self.var.gwAbstractionFraction_Irrigation)

            if self.var.sectorSourceAbstractionFractions and 'commandAreasRelaxGwAbstraction' in binding and \
                    self.var.using_reservoir_command_areas:

                if dateVar['currDate'].day > 15:
                    self.var.gwAbstractionFraction_Irrigation = np.where(self.var.reservoir_command_areas > 0,
                                                                         self.var.commandAreasRelaxGwAbstraction,
                                                                         self.var.gwAbstractionFraction_Irrigation)
            
            
            # Desalination
            
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
               
                
            
            # surface water abstraction that can be extracted to fulfill totalDemand
            # - based on ChannelStorage and swAbstractionFraction * totalDemand
            # sum up potential surface water abstraction (no groundwater abstraction under water and sealed area)

            if self.var.sectorSourceAbstractionFractions:                            
                pot_Channel_Domestic = np.minimum(
                    self.var.swAbstractionFraction_Channel_Domestic * self.var.domesticDemand,
                    self.var.domesticDemand - self.var.Desal_Domestic)                
                pot_Channel_Livestock = np.minimum(
                    self.var.swAbstractionFraction_Channel_Livestock * self.var.livestockDemand,
                    self.var.livestockDemand - self.var.Desal_Livestock)
                pot_Channel_Industry = np.minimum(
                    self.var.swAbstractionFraction_Channel_Industry * self.var.industryDemand,
                    self.var.industryDemand - self.var.Desal_Industry)
                pot_Channel_Irrigation = np.minimum(
                    self.var.swAbstractionFraction_Channel_Irrigation * self.var.totalIrrDemand,
                    self.var.totalIrrDemand - self.var.Desal_Irrigation)

                if 'irrigation_agent_SW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                    pot_Channel_Irrigation = np.minimum(pot_Channel_Irrigation,
                                                        self.var.irrWithdrawalSW_max*self.var.InvCellArea)

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

            # UNDER CONSTRUCTION
            if self.var.using_lift_areas:
                # Lift development When there is sufficient water in the Segment to fulfill demand, the water is
                # taken away proportionally from each cell's readAvlChannelStorageM in the Segment. For example,
                # if total demand can be filled with 50% of total availability, then 50% of the
                # readAvlChannelStorageM from each cell is used. Note that if a cell has too little Channel Storage,
                # then no water will be taken from the cell as this was dealt with earlier:  readAvlChannelStorage =
                # 0 if < (0.0005 * self.var.cellArea) Note: Due to the shared use of abstracted channel storage,
                # a cell may abstract more than its pot_SurfaceAbstract, as well as not necessarily satisfy its
                # pot_SurfaceAbstract
                
                pot_Lift_Domestic = np.minimum(self.var.swAbstractionFraction_Lift_Domestic * self.var.domesticDemand, \
                    self.var.domesticDemand - self.var.Desal_Domestic - self.var.Channel_Domestic )                
                pot_Lift_Livestock = np.minimum(self.var.swAbstractionFraction_Lift_Livestock * self.var.livestockDemand, \
                    self.var.livestockDemand - self.var.Desal_Livestock - self.var.Channel_Livestock)
                pot_Lift_Industry = np.minimum(self.var.swAbstractionFraction_Lift_Industry * self.var.industryDemand, \
                    self.var.industryDemand - self.var.Desal_Industry - self.var.Channel_Industry )
                pot_Lift_Irrigation = np.minimum(self.var.swAbstractionFraction_Lift_Irrigation * self.var.totalIrrDemand, \
                    self.var.totalIrrDemand - self.var.Desal_Irrigation - self.var.Channel_Irrigation)

                if 'irrigation_agent_SW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                    pot_Lift_Irrigation = np.minimum(pot_Lift_Irrigation,
                                                    self.var.irrWithdrawalSW_max * self.var.InvCellArea)

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

            if checkOption('includeWaterBodies'):
                self.var.abstractedLakeReservoirM3C = np.compress(self.var.compress_LR, globals.inZero.copy())

                if self.var.includeWastewater:
                    if not self.var.load_command_areas_wwt:
                        wwtDemandAreaMask =  self.var.waterBodyBuffer_wwt > 0
                    else:
                        wwtDemandAreaMask =  self.var.reservoir_command_areas_wwt > 0
                        
                        
                        
                # First apply to wastewater reclamation, e.g., restricted use reservoirs. Follow by lakes and reservoirs (not restricted)                
                if self.var.includeWastewater:
                    if self.var.sectorSourceAbstractionFractions:
                        pot_wwt_Domestic = np.minimum(
                            self.var.wwtAbstractionFraction_Res_Domestic * self.var.domesticDemand,
                            self.var.domesticDemand - self.var.Desal_Domestic - self.var.Channel_Domestic - self.var.Lift_Domestic) * wwtDemandAreaMask
                
                        pot_wwt_Livestock = np.minimum(
                            self.var.wwtAbstractionFraction_Res_Livestock * self.var.livestockDemand,
                            self.var.livestockDemand - self.var.Desal_Livestock - self.var.Channel_Livestock - self.var.Lift_Livestock) * wwtDemandAreaMask

                        pot_wwt_Industry = np.minimum(
                            self.var.wwtAbstractionFraction_Res_Industry * self.var.industryDemand,
                            self.var.industryDemand - self.var.Desal_Industry - self.var.Channel_Industry - self.var.Lift_Industry) * wwtDemandAreaMask
                        
                        pot_wwt_Irrigation = np.minimum(
                            self.var.wwtAbstractionFraction_Res_Irrigation * self.var.totalIrrDemand,
                            self.var.totalIrrDemand - self.var.Desal_Irrigation - self.var.Channel_Irrigation - self.var.Lift_Irrigation) * wwtDemandAreaMask
                        
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
                # Lakes and reservoirs are both considered lakes for purposes of lake abstraction,
                # both satisfying demands within waterbody cells or within self.var.waterBodyBuffer
                # depending on abstraction fractions

                if self.var.sectorSourceAbstractionFractions:

                    pot_Lake_Domestic = np.minimum(
                        self.var.swAbstractionFraction_Lake_Domestic * self.var.domesticDemand,
                        self.var.domesticDemand - self.var.Desal_Domestic - \
                            self.var.Channel_Domestic - self.var.Lift_Domestic - self.var.wwt_Domestic)

                    pot_Lake_Livestock = np.minimum(
                        self.var.swAbstractionFraction_Lake_Livestock * self.var.livestockDemand,
                        self.var.livestockDemand - self.var.Desal_Livestock - self.var.Channel_Livestock - \
                            self.var.Lift_Livestock - self.var.wwt_Livestock)

                    pot_Lake_Industry = np.minimum(
                        self.var.swAbstractionFraction_Lake_Industry * self.var.industryDemand,
                        self.var.industryDemand - self.var.Desal_Industry - \
                        self.var.Channel_Industry - self.var.Lift_Industry - self.var.wwt_Industry)

                    pot_Lake_Irrigation = np.minimum(
                        self.var.swAbstractionFraction_Lake_Irrigation * self.var.totalIrrDemand,
                        self.var.totalIrrDemand - self.var.Desal_Irrigation - \
                            self.var.Channel_Irrigation - self.var.Lift_Irrigation - self.var.wwt_Irrigation)

                    remainNeed0 = pot_Lake_Domestic + pot_Lake_Livestock + pot_Lake_Industry + pot_Lake_Irrigation

                else:

                    # water that is still needed from surface water
                    remainNeed0 = np.maximum(pot_SurfaceAbstract - self.var.act_SurfaceWaterAbstract, 0)
                
                if not self.var.includeWastewater:
                    self.var.abstractedLakeReservoirM3C = np.compress(self.var.compress_LR, globals.inZero.copy())  
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

                    # B
                    pot_Res_Domestic = np.minimum(
                        self.var.swAbstractionFraction_Res_Domestic * self.var.domesticDemand,
                        self.var.domesticDemand - self.var.Desal_Domestic - self.var.Channel_Domestic - \
                            self.var.Lift_Domestic - self.var.wwt_Domestic - self.var.Lake_Domestic)

                    pot_Res_Livestock = np.minimum(
                        self.var.swAbstractionFraction_Res_Livestock * self.var.livestockDemand,
                        self.var.livestockDemand - self.var.Desal_Livestock - self.var.Channel_Livestock - \
                            self.var.Lift_Livestock - self.var.wwt_Livestock - self.var.Lake_Livestock)

                    pot_Res_Industry = np.minimum(
                        self.var.swAbstractionFraction_Res_Industry * self.var.industryDemand,
                        self.var.industryDemand - self.var.Desal_Industry - self.var.Channel_Industry - \
                            self.var.Lift_Industry - self.var.wwt_Industry - self.var.Lake_Industry)

                    pot_Res_Irrigation = np.minimum(
                        self.var.swAbstractionFraction_Res_Irrigation * self.var.totalIrrDemand,
                        self.var.totalIrrDemand - self.var.Desal_Irrigation - self.var.Channel_Irrigation - \
                            self.var.Lift_Irrigation - self.var.wwt_Irrigation - self.var.Lake_Irrigation)

                    if 'irrigation_agent_SW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                        pot_Res_Irrigation = np.minimum(pot_Res_Irrigation,
                                                        self.var.irrWithdrawalSW_max*self.var.InvCellArea)

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

                # B

            # remaining is taken from groundwater if possible
            if self.var.sectorSourceAbstractionFractions:
                pot_GW_Domestic = np.minimum(
                    self.var.gwAbstractionFraction_Domestic * self.var.domesticDemand,
                    self.var.domesticDemand - self.var.Desal_Domestic - self.var.Channel_Domestic - \
                    self.var.Lift_Domestic - self.var.wwt_Domestic - self.var.Lake_Domestic - self.var.Res_Domestic)
                    
                pot_GW_Livestock = np.minimum(
                    self.var.gwAbstractionFraction_Livestock * self.var.livestockDemand,
                    self.var.livestockDemand - self.var.Desal_Livestock - self.var.Channel_Livestock - \
                    self.var.Lift_Livestock - self.var.wwt_Livestock - self.var.Lake_Livestock - self.var.Res_Livestock)

                pot_GW_Industry = np.minimum(
                    self.var.gwAbstractionFraction_Industry * self.var.industryDemand,
                    self.var.industryDemand - self.var.Desal_Industry - self.var.Channel_Industry - \
                    self.var.Lift_Industry - self.var.wwt_Industry - self.var.Lake_Industry - self.var.Res_Industry)

                pot_GW_Irrigation = np.minimum(
                    self.var.gwAbstractionFraction_Irrigation * self.var.totalIrrDemand,                    
                    self.var.totalIrrDemand - self.var.Desal_Irrigation - self.var.Channel_Irrigation - \
                    self.var.Lift_Irrigation - self.var.wwt_Irrigation - self.var.Lake_Irrigation - self.var.Res_Irrigation)


                if 'irrigation_agent_GW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                    pot_GW_Irrigation = np.minimum(pot_GW_Irrigation,
                                                        self.var.irrWithdrawalGW_max*self.var.InvCellArea)


                self.var.pot_GroundwaterAbstract = pot_GW_Domestic + pot_GW_Livestock + pot_GW_Industry + pot_GW_Irrigation
            else:
                self.var.pot_GroundwaterAbstract = totalDemand - self.var.act_SurfaceWaterAbstract

            if self.var.modflow:
                # groundwater storage that can be pumped: above the minimum saturated fraction of each layer
                # (water_table_limit_for_pumping, groundwater_modflow/transient.py, Dor's version) - before 2026-10 no
                # pumping if the storage was below (1 - water_table_limit_for_pumping) * full storage. Minus the pumping
                # of the days since the last MODFLOW run (modfPumpingM, modflow_timestep > 1: the available storage is
                # updated only by MODFLOW runs) - before 2026-10-11 each day could take the full available storage
                self.var.nonFossilGroundwaterAbs = np.minimum(
                    np.maximum(self.var.groundwater_storage_available - self.var.modfPumpingM, 0),
                    self.var.pot_GroundwaterAbstract)
            else:
                self.var.nonFossilGroundwaterAbs = np.maximum(0., np.minimum(self.var.readAvlStorGroundwater,
                                                                             self.var.pot_GroundwaterAbstract))

            # if limitAbstraction from groundwater is True
            # fossil gwAbstraction and water demand may be reduced
            # variable to reduce/limit groundwater abstraction (> 0 if limitAbstraction = True)

            if self.var.sectorSourceAbstractionFractions:
                # A
                (self.var.GW_Domestic, self.var.GW_Livestock, self.var.GW_Industry,
                 self.var.GW_Irrigation), _ = split_sectors(self.var.nonFossilGroundwaterAbs, (
                    pot_GW_Domestic, pot_GW_Livestock, pot_GW_Industry, pot_GW_Irrigation))

                unmet_Domestic = self.var.domesticDemand - self.var.Desal_Domestic - self.var.Channel_Domestic - \
                    self.var.wwt_Domestic - self.var.Lift_Domestic - self.var.Lake_Domestic - self.var.Res_Domestic - self.var.GW_Domestic
                unmet_Livestock = self.var.livestockDemand - self.var.Desal_Livestock - self.var.Channel_Livestock - \
                    self.var.wwt_Livestock - self.var.Lift_Livestock - self.var.Lake_Livestock - self.var.Res_Livestock - self.var.GW_Livestock
                unmet_Industry = self.var.industryDemand - self.var.Desal_Industry - self.var.Channel_Industry - \
                    self.var.wwt_Industry - self.var.Lift_Industry  - self.var.Lake_Industry - self.var.Res_Industry - self.var.GW_Industry
                unmet_Irrigation = self.var.totalIrrDemand - self.var.Desal_Irrigation - self.var.Channel_Irrigation - \
                    self.var.wwt_Irrigation - self.var.Lift_Irrigation - self.var.Lake_Irrigation - self.var.Res_Irrigation - self.var.GW_Irrigation

            if checkOption('limitAbstraction'):
                # real surface water abstraction can be lower, because not all demand can be done from surface water
                act_swAbstractionFraction = divideValues(self.var.act_SurfaceWaterAbstract, totalDemand)
                # Fossil groundwater abstraction is not allowed
                # allocation rule here: domestic& industry > irrigation > paddy

                if self.var.sectorSourceAbstractionFractions:

                    self.var.act_nonIrrWithdrawal = self.var.Desal_Domestic + self.var.Desal_Livestock + self.var.Desal_Industry + \
                                                    self.var.Channel_Domestic + self.var.Channel_Livestock + self.var.Channel_Industry + \
                                                    self.var.wwt_Domestic + self.var.wwt_Livestock + self.var.wwt_Industry + \
                                                    self.var.Lift_Domestic + self.var.Lift_Livestock + self.var.Lift_Industry + \
                                                    self.var.Lake_Domestic + self.var.Lake_Livestock + self.var.Lake_Industry + \
                                                    self.var.Res_Domestic + self.var.Res_Livestock + self.var.Res_Industry + \
                                                    self.var.GW_Domestic + self.var.GW_Livestock + self.var.GW_Industry
                    self.var.act_irrWithdrawal = self.var.Desal_Irrigation + self.var.Channel_Irrigation + \
                        self.var.wwt_Irrigation + self.var.Lift_Irrigation + self.var.Lake_Irrigation + self.var.Res_Irrigation + self.var.GW_Irrigation
                    # Currently wastewater and desalination are accounted as surface water
                    act_irrWithdrawalSW = self.var.Desal_Irrigation + self.var.Channel_Irrigation + self.var.Lift_Irrigation + \
                        self.var.wwt_Irrigation + self.var.Lake_Irrigation + self.var.Res_Irrigation
                    act_irrWithdrawalGW = self.var.GW_Irrigation
                    self.var.act_irrNonpaddyWithdrawal = np.minimum(self.var.act_irrWithdrawal,
                                                                    self.var.fracVegCover[3] * self.var.irrDemand[3])
                    self.var.act_irrPaddyWithdrawal = self.var.act_irrWithdrawal - self.var.act_irrNonpaddyWithdrawal

                    act_gw = np.copy(self.var.nonFossilGroundwaterAbs)

                elif self.var.includeIndusDomesDemand:  # all demands are taken into account
                    # non-irrgated water demand: adjusted (and maybe increased) by gwabstration factor if
                    # non-irrgated water demand is higher than actual growndwater abstraction (what is needed and
                    # what is stored in gw)
                    act_nonIrrWithdrawalGW = self.var.nonIrrDemand * (1 - act_swAbstractionFraction)
                    act_nonIrrWithdrawalGW = np.where(act_nonIrrWithdrawalGW > self.var.nonFossilGroundwaterAbs,
                                                      self.var.nonFossilGroundwaterAbs, act_nonIrrWithdrawalGW)
                    act_nonIrrWithdrawalSW = act_swAbstractionFraction * self.var.nonIrrDemand
                    self.var.act_nonIrrWithdrawal = act_nonIrrWithdrawalSW + act_nonIrrWithdrawalGW

                    # irrigated water demand:
                    act_irrWithdrawalGW = self.var.totalIrrDemand * (1 - act_swAbstractionFraction)
                    act_irrWithdrawalGW = np.minimum(self.var.nonFossilGroundwaterAbs - act_nonIrrWithdrawalGW,
                                                     act_irrWithdrawalGW)
                    act_irrWithdrawalSW = act_swAbstractionFraction * self.var.totalIrrDemand
                    self.var.act_irrWithdrawal = act_irrWithdrawalSW + act_irrWithdrawalGW
                    # (nonpaddy)
                    act_irrnonpaddyGW = self.var.fracVegCover[3] * (1 - act_swAbstractionFraction) * \
                                        self.var.irrDemand[3]
                    act_irrnonpaddyGW = np.minimum(self.var.nonFossilGroundwaterAbs - act_nonIrrWithdrawalGW,
                                                   act_irrnonpaddyGW)
                    act_irrnonpaddySW = self.var.fracVegCover[3] * act_swAbstractionFraction * self.var.irrDemand[3]
                    self.var.act_irrNonpaddyWithdrawal = act_irrnonpaddySW + act_irrnonpaddyGW
                    # (paddy)
                    act_irrpaddyGW = self.var.fracVegCover[2] * (1 - act_swAbstractionFraction) * self.var.irrDemand[2]
                    act_irrpaddyGW = np.minimum(
                        self.var.nonFossilGroundwaterAbs - act_nonIrrWithdrawalGW - act_irrnonpaddyGW, act_irrpaddyGW)
                    act_irrpaddySW = self.var.fracVegCover[2] * act_swAbstractionFraction * self.var.irrDemand[2]
                    self.var.act_irrPaddyWithdrawal = act_irrpaddySW + act_irrpaddyGW

                    act_gw = act_nonIrrWithdrawalGW + act_irrWithdrawalGW
                    # This should be equal to self.var.nonFossilGroundwaterAbs?


                else:  # only irrigation is considered

                    self.var.act_nonIrrWithdrawal = globals.inZero.copy()

                    # irrigated water demand:
                    act_irrWithdrawalGW = self.var.totalIrrDemand * (1 - act_swAbstractionFraction)
                    act_irrWithdrawalGW = np.minimum(self.var.nonFossilGroundwaterAbs, act_irrWithdrawalGW)
                    act_irrWithdrawalSW = act_swAbstractionFraction * self.var.totalIrrDemand
                    self.var.act_irrWithdrawal = act_irrWithdrawalSW + act_irrWithdrawalGW
                    # (nonpaddy)
                    act_irrnonpaddyGW = self.var.fracVegCover[3] * (1 - act_swAbstractionFraction) * \
                                        self.var.irrDemand[3]
                    act_irrnonpaddyGW = np.minimum(self.var.nonFossilGroundwaterAbs, act_irrnonpaddyGW)
                    act_irrnonpaddySW = self.var.fracVegCover[3] * act_swAbstractionFraction * self.var.irrDemand[3]
                    self.var.act_irrNonpaddyWithdrawal = act_irrnonpaddySW + act_irrnonpaddyGW
                    # (paddy)
                    act_irrpaddyGW = self.var.fracVegCover[2] * (1 - act_swAbstractionFraction) * self.var.irrDemand[2]
                    act_irrpaddyGW = np.minimum(
                        self.var.nonFossilGroundwaterAbs - act_irrnonpaddyGW, act_irrpaddyGW)
                    act_irrpaddySW = self.var.fracVegCover[2] * act_swAbstractionFraction * self.var.irrDemand[2]
                    self.var.act_irrPaddyWithdrawal = act_irrpaddySW + act_irrpaddyGW

                    act_gw = np.copy(act_irrWithdrawalGW)

                # before 2026-11 minus unmetDemandPaddy / unmetDemandNonpaddy (carry-over of unmet demand), but these
                # were always 0: unmet = D - max(0, D - unmet_old) = min(D, unmet_old) stays 0 from a start of 0
                self.var.act_irrPaddyDemand = np.maximum(0, self.var.irrPaddyDemand)
                self.var.act_irrNonpaddyDemand = np.maximum(0, self.var.irrNonpaddyDemand)

                # unmet is either pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs or demand - withdrawal
                if self.var.includeIndusDomesDemand:  # all demands are taken into account
                    self.var.unmetDemand = (self.var.totalIrrDemand - self.var.act_irrWithdrawal) + \
                                           (self.var.nonIrrDemand - self.var.act_nonIrrWithdrawal)
                else:  # only irrigation is considered
                    self.var.unmetDemand = self.var.totalIrrDemand - self.var.act_irrWithdrawal


            else:
                # limitAbstraction = False implies that all demands are satisfied.
                # zonal abstractions from channels will attempt to satisfy remaining surface water demands
                # Then, zonal groundwater will attempt to satisfy all groundwater demands
                # Then, unmetDemand = fossil water satisfies all remaining demands
                # limitAbstraction = False is not compatible with Modflow, however zonal channel abstraction should
                # be allowed. TODO: decouple limitAbstraction and channel zonal abstractions


                # This is the case when using ModFlow coupling (limitation imposed previously)
                # Modflow and limitAbstraction = False are not compatible.
                if self.var.modflow:
                    # This is the case when using ModFlow coupling (limitation imposed previously)
                    # part of the groundwater demand unsatisfied
                    self.var.unmetDemand = self.var.pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs

                    if self.var.includeIndusDomesDemand:  # all demands are taken into account
                        self.var.act_nonIrrWithdrawal = np.copy(self.var.nonIrrDemand)
                    self.var.act_irrWithdrawal = np.copy(self.var.totalIrrDemand)

                    act_gw = np.copy(self.var.nonFossilGroundwaterAbs)

                else:
                    # Fossil groundwater abstractions are allowed (act = pot)
                    if 'zonal_abstraction' in option:
                        if checkOption('zonal_abstraction'):

                            # using allocation from abstraction zone
                            # this might be a regular grid e.g. 2x2 for 0.5 deg
                            left_sf_avail = self.var.readAvlChannelStorageM  # already removed - self.var.act_channelAbst
                            # sum demand, surface water - local used, groundwater - local use, not satisfied for allocation zone

                            self.var.unmetDemand = totalDemand - self.var.act_SurfaceWaterAbstract - self.var.nonFossilGroundwaterAbs
                            if self.var.sectorSourceAbstractionFractions:
                                unmetChannel_Domestic = pot_Channel_Domestic - self.var.Channel_Domestic
                                unmetChannel_Livestock = pot_Channel_Livestock - self.var.Channel_Livestock
                                unmetChannel_Industry = pot_Channel_Industry - self.var.Channel_Industry
                                unmetChannel_Irrigation = pot_Channel_Irrigation - self.var.Channel_Irrigation

                                pot_Channel_Domestic = np.minimum(unmetChannel_Domestic, unmet_Domestic)
                                pot_Channel_Livestock = np.minimum(unmetChannel_Livestock, unmet_Livestock)
                                pot_Channel_Industry = np.minimum(unmetChannel_Industry, unmet_Industry)
                                pot_Channel_Irrigation = np.minimum(unmetChannel_Irrigation, unmet_Irrigation)

                                unmet_Channel = pot_Channel_Domestic + pot_Channel_Livestock \
                                                + pot_Channel_Industry + pot_Channel_Irrigation
                                unmetDemand_sw = unmet_Channel.copy()

                                zoneDemand_sw = self.var.allocation_zoneIndex.total(unmet_Channel * self.var.cellArea) / self.var.cellArea


                            else:
                                # get the demand that still needs to be met

                                #multiply with cellarea [m] -> [m3], otherwise bincount is not correct, divide again by cellarea to get [m] again
                                unmetDemand_sw = np.minimum(self.var.unmetDemand,
                                                            totalDemand * self.var.swAbstractionFraction- self.var.act_SurfaceWaterAbstract)
                                zoneDemand_sw = self.var.allocation_zoneIndex.total(unmetDemand_sw * self.var.cellArea) / self.var.cellArea

                            zone_sf_avail = self.var.allocation_zoneIndex.total(left_sf_avail * self.var.cellArea) / self.var.cellArea

                            # zone abstraction is minimum of availability and demand [m3]
                            zone_sf_abstraction = np.minimum(zoneDemand_sw, zone_sf_avail)
                            # water taken from surface zone and allocated to cell demand

                            # alternate formulation of following formula
                            #cell_sf_abstraction = np.maximum(0., divideValues(left_sf_avail,
                            #                                                  zone_sf_avail) * zone_sf_abstraction
                            cell_sf_abstraction = np.maximum(0., np.where(zoneDemand_sw < zone_sf_avail,
                                                                          divideValues(left_sf_avail, zone_sf_avail) * zoneDemand_sw, left_sf_avail))


                            # the allocation doesn't need to be adapted because zone_sf_abstraction always <= zoneDemand
                            # cell_sf_allocation shows for which cells demand is satisfied how much, whereas cell_sf_abstraction shows where water is abstracted
                            cell_sf_allocation = np.maximum(0., divideValues(unmetDemand_sw,
                                                                             zoneDemand_sw) * zone_sf_abstraction)

                            # sum up with other abstraction
                            self.var.act_SurfaceWaterAbstract = self.var.act_SurfaceWaterAbstract + cell_sf_abstraction
                            self.var.act_channelAbst = self.var.act_channelAbst + cell_sf_abstraction

                            if self.var.sectorSourceAbstractionFractions:
                                # With zonal abstractions, cells can abstract more than their specific demands
                                # In the case that abstractions are greater than demands, this is attributed
                                # to Channel_Other
                                (self.var.Channel_Domestic_fromZone, self.var.Channel_Livestock_fromZone,
                                 self.var.Channel_Industry_fromZone, self.var.Channel_Irrigation_fromZone), \
                                    self.var.Channel_Other = split_sectors(cell_sf_allocation, (
                                        pot_Channel_Domestic, pot_Channel_Livestock, pot_Channel_Industry,
                                        pot_Channel_Irrigation))
                                self.var.Channel_Domestic += self.var.Channel_Domestic_fromZone
                                self.var.Channel_Livestock += self.var.Channel_Livestock_fromZone
                                self.var.Channel_Industry += self.var.Channel_Industry_fromZone
                                self.var.Channel_Irrigation += self.var.Channel_Irrigation_fromZone

                            # new potential groundwater abstraction
                            self.var.pot_GroundwaterAbstract = \
                                np.maximum(0., self.var.pot_GroundwaterAbstract - cell_sf_allocation)

                            left_gw_demand = np.maximum(0., self.var.pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs)
                            left_gw_avail = np.maximum(0., self.var.readAvlStorGroundwater - self.var.nonFossilGroundwaterAbs)

                            zone_gw_avail = self.var.allocation_zoneIndex.total(left_gw_avail * self.var.cellArea) / self.var.cellArea

                            # for groundwater substract demand which is fulfilled by surface zone, calc abstraction and what
                            # is left.
                            zone_gw_demand = self.var.allocation_zoneIndex.total(left_gw_demand * self.var.cellArea) / self.var.cellArea
                            #zone_gw_demand = zoneDemand - zone_sf_abstraction
                            zone_gw_abstraction = np.minimum(zone_gw_demand, zone_gw_avail)
                            # zone_unmetdemand = np.maximum(0., zone_gw_demand - zone_gw_abstraction)

                            # water taken from groundwater zone and allocated to cell demand
                            cell_gw_abstraction = np.maximum(0., np.where(zone_gw_demand < zone_gw_avail,
                                                           divideValues(left_gw_avail, zone_gw_avail) * zone_gw_demand,
                                                           left_gw_avail))
                            #zone_gw_abstraction always <= zone_gw_demand
                            cell_gw_allocation = \
                                np.maximum(0., divideValues(left_gw_demand, zone_gw_demand) * zone_gw_abstraction)

                            self.var.nonFossilGroundwaterAbs = self.var.nonFossilGroundwaterAbs + cell_gw_abstraction
                            self.var.unmetDemand = np.maximum(0., left_gw_demand - cell_gw_allocation)

                            # UNDER CONSTRUCTION
                            if self.var.sectorSourceAbstractionFractions:

                                # With zonal abstractions, cells can abstract more than their specific demands
                                # In the case that abstractions are greater than demands, this is attributed
                                # to GW_Other
                                (self.var.GW_Domestic_fromZone, self.var.GW_Livestock_fromZone,
                                 self.var.GW_Industry_fromZone, self.var.GW_Irrigation_fromZone), \
                                    self.var.GW_Other = split_sectors(cell_gw_allocation, (
                                        pot_GW_Domestic - self.var.GW_Domestic, pot_GW_Livestock - self.var.GW_Livestock,
                                        pot_GW_Industry - self.var.GW_Industry, pot_GW_Irrigation - self.var.GW_Irrigation))
                                self.var.GW_Domestic += self.var.GW_Domestic_fromZone
                                self.var.GW_Livestock += self.var.GW_Livestock_fromZone
                                self.var.GW_Industry += self.var.GW_Industry_fromZone
                                self.var.GW_Irrigation += self.var.GW_Irrigation_fromZone

                                # With zonal abstractions, cells can abstract more than their specific demands
                                demand_satisfied = self.var.Desal_Domestic + self.var.Desal_Livestock + self.var.Desal_Industry + \
                                    self.var.Channel_Domestic + self.var.Channel_Livestock + self.var.Channel_Industry + \
                                    self.var.wwt_Domestic + self.var.wwt_Livestock + self.var.wwt_Industry + \
                                    self.var.Lift_Domestic + self.var.Lift_Livestock + self.var.Lift_Industry + \
                                    self.var.Lake_Domestic + self.var.Lake_Livestock + self.var.Lake_Industry + \
                                    self.var.Res_Domestic + self.var.Res_Livestock + self.var.Res_Industry + \
                                    self.var.GW_Domestic + self.var.GW_Livestock + self.var.GW_Industry + \
                                    self.var.Desal_Irrigation + self.var.Channel_Irrigation + self.var.Lift_Irrigation + \
                                    self.var.wwt_Irrigation + self.var.Lake_Irrigation + self.var.Res_Irrigation + self.var.GW_Irrigation

                                self.var.unmetDemand = totalDemand - demand_satisfied

                                # fossil groundwater: the rest up to pot_GW_* (at most the rest of the sector demand,
                                # the channel water from the zone covers a part) is taken from fossil groundwater, as
                                # without zonal abstraction (GW_* = pot_GW_* below). Before 2026-11 GW_* was only the
                                # non-fossil part here, the consumption of the fossil water went to returnflowNonIrr
                                # (= act_nonIrrWithdrawal (= nonIrrDemand) - act_nonIrrConsumption (from the GW_*))
                                for sector, demand, pot_GW in (('Domestic', self.var.domesticDemand, pot_GW_Domestic),
                                                               ('Livestock', self.var.livestockDemand, pot_GW_Livestock),
                                                               ('Industry', self.var.industryDemand, pot_GW_Industry),
                                                               ('Irrigation', self.var.totalIrrDemand, pot_GW_Irrigation)):
                                    GW = getattr(self.var, 'GW_' + sector)
                                    rest = demand - sum(getattr(self.var, source + '_' + sector) for source in
                                                        ('Desal', 'Channel', 'wwt', 'Lift', 'Lake', 'Res')) - GW
                                    setattr(self.var, 'GW_' + sector, GW + np.maximum(0., np.minimum(pot_GW - GW, rest)))
                            # end of zonal abstraction

                        else: #no zonal abstractions
                            self.var.unmetDemand = totalDemand - self.var.act_SurfaceWaterAbstract - self.var.nonFossilGroundwaterAbs
                            if self.var.sectorSourceAbstractionFractions:
                                self.var.GW_Domestic = pot_GW_Domestic
                                self.var.GW_Industry = pot_GW_Industry
                                self.var.GW_Livestock = pot_GW_Livestock
                                self.var.GW_Irrigation = pot_GW_Irrigation
                    else: #no zonal abstractions
                        self.var.unmetDemand = totalDemand - self.var.act_SurfaceWaterAbstract - self.var.nonFossilGroundwaterAbs
                        if self.var.sectorSourceAbstractionFractions:
                            self.var.GW_Domestic = pot_GW_Domestic
                            self.var.GW_Industry = pot_GW_Industry
                            self.var.GW_Livestock = pot_GW_Livestock
                            self.var.GW_Irrigation = pot_GW_Irrigation


                    if self.var.includeIndusDomesDemand:  # all demands are taken into account
                        self.var.act_nonIrrWithdrawal = np.copy(self.var.nonIrrDemand)
                    self.var.act_irrWithdrawal = np.copy(self.var.totalIrrDemand)

                    act_gw = np.copy(self.var.pot_GroundwaterAbstract)

                self.var.act_irrNonpaddyWithdrawal = self.var.fracVegCover[3] * self.var.irrDemand[3]
                self.var.act_irrPaddyWithdrawal = self.var.fracVegCover[2] * self.var.irrDemand[2]

                self.var.act_irrNonpaddyDemand = self.var.act_irrNonpaddyWithdrawal.copy()
                self.var.act_irrPaddyDemand = self.var.act_irrPaddyWithdrawal.copy()

                # end of limit_abstraction = False
            ## End of limit extraction if, then

            self.var.act_irrConsumption[2] = divideValues(self.var.act_irrPaddyWithdrawal,
                                                          self.var.fracVegCover[2]) * self.var.efficiencyPaddy
            # efficiency of the withdrawal: with the extra water of fraction_IncreaseIrrigation_Nonpaddy (irrigation.py)
            self.var.act_irrConsumption[3] = divideValues(self.var.act_irrNonpaddyWithdrawal,
                                                          self.var.fracVegCover[3]) * self.var.efficiencyNonpaddyWithdrawal

            if self.var.modflow:
                if self.var.GW_pumping:  # pumping demand is sent to ModFlow (used in transient module)
                    # modfPumpingM is initialized every "modflow_timestep" in "groundwater_modflow/transient.py"
                    self.var.modfPumpingM += act_gw
                    self.var.Pumping_daily = np.copy(act_gw)
                    self.var.PumpingM3_daily = act_gw * self.var.cellArea

            if self.var.sectorSourceAbstractionFractions:

                self.var.act_domWithdrawal = self.var.Channel_Domestic + self.var.Lift_Domestic + \
                                             self.var.Desal_Domestic + self.var.wwt_Domestic + self.var.Lake_Domestic + \
                                             self.var.Res_Domestic + self.var.GW_Domestic
                self.var.act_livWithdrawal = self.var.Channel_Livestock + self.var.Lift_Livestock + \
                                             self.var.Desal_Livestock + self.var.wwt_Livestock + self.var.Lake_Livestock + \
                                             self.var.Res_Livestock + self.var.GW_Livestock
                self.var.act_indWithdrawal = self.var.Channel_Industry + self.var.Lift_Industry + \
                                             self.var.Desal_Industry + self.var.wwt_Industry + self.var.Lake_Industry + \
                                             self.var.Res_Industry + self.var.GW_Industry

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

            if checkOption('limitAbstraction'):
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

            if 'adminSegments' in binding and checkOption('limitAbstraction'):

                self.var.act_irrWithdrawalSW_month += self.var.adminSegmentsIndex.total(
                    act_irrWithdrawalSW * self.var.cellArea)

                if 'irrigation_agent_SW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                    self.var.swAbstractionFraction_Channel_Irrigation = np.where(
                        self.var.act_irrWithdrawalSW_month > self.var.irrWithdrawalSW_max, 0,
                        self.var.swAbstractionFraction_Channel_Irrigation)

                    self.var.swAbstractionFraction_Lift_Irrigation = np.where(
                        self.var.act_irrWithdrawalSW_month > self.var.irrWithdrawalSW_max, 0,
                        self.var.swAbstractionFraction_Lift_Irrigation)

                    self.var.swAbstractionFraction_Lake_Irrigation = np.where(
                        self.var.act_irrWithdrawalSW_month > self.var.irrWithdrawalSW_max, 0,
                        self.var.swAbstractionFraction_Lake_Irrigation)

                    self.var.swAbstractionFraction_Res_Irrigation = np.where(
                        self.var.act_irrWithdrawalSW_month > self.var.irrWithdrawalSW_max, 0,
                        self.var.swAbstractionFraction_Res_Irrigation)

                    # no division by 0 where the request is 0; such a segment that withdraws water is over its
                    # request (inf as before 2026-11), 0/0 (was NaN) -> 0: same result in the > 0.95 / 0.98 tests
                    self.var.ratio_irrWithdrawalSW_month = np.where(
                        (self.var.irrWithdrawalSW_max <= 0) & (self.var.act_irrWithdrawalSW_month > 0), np.inf,
                        divideValues(self.var.act_irrWithdrawalSW_month, self.var.irrWithdrawalSW_max))

            if 'adminSegments' in binding and checkOption('limitAbstraction'):
                self.var.act_irrWithdrawalGW_month += self.var.adminSegmentsIndex.total(
                    act_irrWithdrawalGW * self.var.cellArea)
                if 'irrigation_agent_GW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                    self.var.gwAbstractionFraction_Irrigation = np.where(
                        self.var.act_irrWithdrawalGW_month > self.var.irrWithdrawalGW_max, 0,
                        self.var.gwAbstractionFraction_Irrigation)

                    self.var.ratio_irrWithdrawalGW_month = np.where(
                        (self.var.irrWithdrawalGW_max <= 0) & (self.var.act_irrWithdrawalGW_month > 0), np.inf,
                        divideValues(self.var.act_irrWithdrawalGW_month, self.var.irrWithdrawalGW_max))

            if self.var.relax_irrigation_agents:
                if dateVar['currDate'].day == 10:
                    if 'irrigation_agent_SW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                        self.var.relaxSWagent += np.where(self.var.ratio_irrWithdrawalSW_month > 0.95, 1, 0)
                    if 'irrigation_agent_GW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                        self.var.relaxGWagent += np.where(self.var.ratio_irrWithdrawalGW_month > 0.95, 1, 0)

                # This will decrease values that have increased, but not on agents that were never too large
                if dateVar['currDate'].day == 28:
                    if 'irrigation_agent_SW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                        self.var.relaxSWagent -= np.where(self.var.relaxSWagent > 0,
                                                          np.where(self.var.ratio_irrWithdrawalSW_month > 0.98, 0, 1),
                                                          0)
                    if 'irrigation_agent_GW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                        self.var.relaxGWagent -= np.where(self.var.relaxGWagent > 0,
                                                          np.where(self.var.ratio_irrWithdrawalGW_month > 0.98, 0, 1),
                                                          0)

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
