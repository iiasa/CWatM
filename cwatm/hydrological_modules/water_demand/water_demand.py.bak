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

from cwatm.management_modules.replace_pcr import npareatotal, npareamaximum
from cwatm.management_modules.data_handling import (returnBool, binding, cbinding, loadmap, divideValues,
                                                     checkOption, npareaaverage, readnetcdf2)
from cwatm.hydrological_modules.water_demand.domestic import waterdemand_domestic
from cwatm.hydrological_modules.water_demand.industry import waterdemand_industry
from cwatm.hydrological_modules.water_demand.livestock import waterdemand_livestock
from cwatm.hydrological_modules.water_demand.irrigation import waterdemand_irrigation
from cwatm.hydrological_modules.water_demand.environmental_need import waterdemand_environmental_need
from cwatm.hydrological_modules.water_demand.wastewater import waterdemand_wastewater

# PB1507
from cwatm.management_modules.data_handling import *


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
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    channelStorage                       Array         Channel water storage                                                   m3   
    unmetDemand_runningSum               Array         Unmet water demand (too less water availability)                        m    
    modflow                              Flag          True if modflow_coupling = True in settings file                        bool 
    pot_domesticConsumption              Array                                                                                 --   
    load_initial                         Flag          Settings initLoad holds initial conditions for variables                bool 
    readAvlStorGroundwater               Array         same as storGroundwater but equal to 0 when inferior to a treshold      m    
    pot_industryConsumption              Array                                                                                 --   
    loadInit                             Flag          If true initial conditions are loaded                                   bool 
    includeDesal                         Flag                                                                                  --   
    unlimitedDesal                       Flag                                                                                  --   
    desalAnnualCap                       Number                                                                                --   
    efficiencyPaddy                      Array         Input, irrPaddy_efficiency, paddy irrigation efficiency, the amount of  frac 
    efficiencyNonpaddy                   Array         Input, irrNonPaddy_efficiency, non-paddy irrigation efficiency, the am  frac 
    returnfractionIrr                    Array         Input, irrigation_returnfraction, the fraction of non-efficient water   frac 
    irrPaddyDemand                       Array         Paddy irrigation demand                                                 m    
    compress_LR                          Array         boolean map as mask map for compressing lake/reservoir                  --   
    decompress_LR                        Array         boolean map as mask map for decompressing lake/reservoir                --   
    MtoM3C                               Array         conversion factor from m to m3 (compressed map)                         --   
    resId_restricted                     Array         waterbody ID for waste water                                            --   
    waterBodyBuffer                      Array         Create a buffer around water bodies as command areas for lakes and res  m2   
    waterBodyBuffer_wwt                  Array         Create a buffer around water bodies as command areas for lakes and res  m2   
    reservoir_releases_excel_option      Flag          If Excel file is used for addition reservoirs, watertransfer, release   bool 
    lakeResStorage_release_ratioC        Array         daily release ration for reservoirs - compressed                        --   
    M3toM                                Array         Coefficient to change units                                             --   
    MtoM3                                Array         Coefficient to change units                                             --   
    InvDtSec                             Array         inversere of seconds per timestep (default 1/86400)                     1/s  
    InvCellArea                          Array         Inverse of cell area of each simulated mesh                             1/m2 
    GW_pumping                           Flag          Input, True if Groundwater_pumping=True                                 bool 
    availableGWStorageFraction           Array                                                                                 --   
    groundwater_storage_available        Array         Groundwater storage. Used with MODFLOW.                                 m    
    gwstorage_full                       Number        Groundwater storage at full capacity                                    m    
    wwtColArea                           Array                                                                                 --   
    wwtSewerCollection                   Array                                                                                 --   
    wwtOverflowOutM                      Array                                                                                 --   
    fracVegCover                         Array         Fraction of specific land covers (0=forest, 1=grasslands, etc.)         %    
    adminSegments                        Array         Domestic agents                                                         Int  
    cellArea                             Array         Area of cell                                                            m2   
    nonFossilGroundwaterAbs              Array         Non-fossil groundwater abstraction. Used primarily without MODFLOW.     m    
    includeWastewater                    Flag                                                                                  --   
    waterBodyTyp_unchanged               Array                                                                                 --   
    lakeVolumeM3C                        Array         compressed map of lake volume                                           m3   
    lakeStorageC                         Array                                                                                 --   
    reservoirStorageM3C                  Array                                                                                 --   
    lakeResStorageC                      Array                                                                                 --   
    lakeResStorage                       Array                                                                                 --   
    reservoir_supply                     Array                                                                                 --   
    waterBodyTypCTemp                    Array         waterbody temp e.g. lake, reservoir, wetlands -> compressed             --   
    smalllakeVolumeM3                    Array                                                                                 --   
    smalllakeStorage                     Array                                                                                 --   
    act_SurfaceWaterAbstract             Array         Surface water abstractions                                              m    
    readAvlChannelStorageM               Array                                                                                 --   
    leakageCanals_M                      Array                                                                                 --   
    includeWastewaterPits                Flag                                                                                  --   
    pitLatrinToGW                        Array                                                                                 --   
    addtoevapotrans                      Array         Irrigation application loss to evaporation                              m    
    act_irrConsumption                   Array         actual irrigation water consumption                                     m    
    act_irrNonpaddyWithdrawal            Array         non-paddy irrigation withdrawal                                         m    
    act_irrPaddyWithdrawal               Array         paddy irrigation withdrawal                                             m    
    act_bigLakeResAbst                   Array         Abstractions to satisfy demands from lakes and reservoirs               m    
    act_smallLakeResAbst                 Array         Abstractions from small lakes at demand location                        m    
    returnFlow                           Array                                                                                 --   
    act_nonIrrConsumption                Array         Non-irrigation consumption                                              m    
    act_nonIrrWithdrawal                 Array         Non-irrigation withdrawals                                              m    
    act_irrWithdrawal                    Array         Irrigation withdrawals                                                  m    
    waterdemandFixed                     Array                                                                                 --   
    modfPumpingM                         Array                                                                                 --   
    activate_domestic_agents             Flag          Input, True if activate_domestic_agents = True                          bool 
    domesticDemand                       Array         Domestic demand                                                         m    
    swAbstractionFraction_domestic       Array         With domestic agents, derived from surface water over total water requ  %    
    demand_unit                          Flag                                                                                  --   
    sectorSourceAbstractionFractions     Array                                                                                 --   
    swAbstractionFraction_Channel_Domes  Array         Input, Fraction of Domestic demands to be satisfied with Channel        %    
    swAbstractionFraction_Lift_Domestic  Array         Input, Fraction of Domestic demands to be satisfied with Lift           %    
    swAbstractionFraction_Res_Domestic   Array         Input, Fraction of Domestic demands to be satisfied with Reservoirs     %    
    swAbstractionFraction_Lake_Domestic  Array         Input, Fraction of Domestic demands to be satisfied with Lake           %    
    gwAbstractionFraction_Domestic       Array         Fraction of domestic water demand to be satisfied by groundwater        %    
    dom_efficiency                       Array                                                                                 --   
    envFlow                              Array                                                                                 --   
    industryDemand                       Array                                                                                 --   
    ind_efficiency                       Array                                                                                 --   
    unmetDemandPaddy                     Array         Unmet paddy demand                                                      m    
    unmetDemandNonpaddy                  Array         Unmet nonpaddy demand                                                   m    
    unmetDemand                          Array         Unmet groundwater demand to determine potential fossil groundwaterwate  m    
    irrDemand                            Array         Cover-specific Irrigation demand                                        m    
    irrNonpaddyDemand                    Array                                                                                 --   
    totalIrrDemand                       Array         Irrigation demand                                                       m    
    livestockDemand                      Array                                                                                 --   
    pot_livestockConsumption             Array         Potential livestock consumption                                         m    
    liv_efficiency                       Number        Livestock water use efficiency                                          --   
    wwtEffluentsGenerated                Array                                                                                 --   
    wwtSewerCollection_domestic          Array                                                                                 --   
    wwtSewerCollection_industry          Array                                                                                 --   
    includeIndusDomesDemand              Flag          Input, True if includeIndusDomesDemand = True                           bool 
    activate_irrigation_agents           Flag          Input, True if activate_irrigation_agents = True                        bool 
    relaxGWagent                         Flag                                                                                  --   
    relaxSWagent                         Flag                                                                                  --   
    irrWithdrawalSW_max                  Array                                                                                 --   
    irrWithdrawalGW_max                  Array                                                                                 --   
    relax_irrigation_agents              Flag                                                                                  --   
    relax_abstraction_fraction_initial   Array                                                                                 --   
    waterdemandFixedYear                 Array                                                                                 --   
    swAbstractionFraction_Channel_Lives  Array         Input, Fraction of Livestock demands to be satisfied from Channels      %    
    swAbstractionFraction_Channel_Indus  Array         Input, Fraction of Industrial water demand to be satisfied by Channels  %    
    swAbstractionFraction_Channel_Irrig  Array         Input, Fraction of Irrigation demand to be satisfied from Channels      %    
    swAbstractionFraction_Lake_Livestoc  Array         Input, Fraction of Livestock water demands to be satisfied by Lakes     %    
    swAbstractionFraction_Lake_Industry  Array         Input, Fraction of Industrial water demand to be satisfied by Lakes     %    
    swAbstractionFraction_Lake_Irrigati  Array         Input, Fraction of Irrigation demand to be satisfied by Lakes           %    
    swAbstractionFraction_Res_Livestock  Array         Input, Fraction of Livestock water demands to be satisfied by Reservoi  %    
    swAbstractionFraction_Res_Industry   Array         Input, Fraction of Industrial water demand to be satisfied by Reservoi  %    
    swAbstractionFraction_Res_Irrigatio  Array         Input, Fraction of Irrigation demand to be satisfied by Reservoirs      %    
    othAbstractionFraction_Desal_Domest  Array                                                                                 --   
    othAbstractionFraction_Desal_Livest  Array                                                                                 --   
    othAbstractionFraction_Desal_Indust  Array                                                                                 --   
    othAbstractionFraction_Desal_Irriga  Array                                                                                 --   
    wwtAbstractionFraction_Res_Domestic  Array                                                                                 --   
    wwtAbstractionFraction_Res_Livestoc  Array                                                                                 --   
    wwtAbstractionFraction_Res_Industry  Array                                                                                 --   
    wwtAbstractionFraction_Res_Irrigati  Array                                                                                 --   
    gwAbstractionFraction_Livestock      Array         Fraction of livestock water demand to be satisfied by groundwater       %    
    gwAbstractionFraction_Industry       Array         Fraction of industrial water demand to be satisfied by groundwater      %    
    gwAbstractionFraction_Irrigation     Array         Fraction of irrigation water demand to be satisfied by groundwater      %    
    using_reservoir_command_areas        Flag          True if using_reservoir_command_areas = True, False otherwise           bool 
    load_command_areas                   Flag                                                                                  --   
    load_command_areas_wwt               Flag                                                                                  --   
    reservoir_command_areas              Array                                                                                 --   
    reservoir_command_areas_wwt          Array                                                                                 --   
    Water_conveyance_efficiency          Array                                                                                 --   
    segmentArea                          Array                                                                                 --   
    segmentArea_wwt                      Array                                                                                 --   
    canals                               Array                                                                                 --   
    canals_wwt                           Array                                                                                 --   
    canalsArea                           Array                                                                                 --   
    canalsAreaC                          Array                                                                                 --   
    canalsArea_wwt                       Array                                                                                 --   
    canalsArea_wwtC                      Array                                                                                 --   
    swAbstractionFraction_Lift_Livestoc  Array         Input, Fraction of Livestock water demands to be satisfied from Lift a  %    
    swAbstractionFraction_Lift_Industry  Array         Input, Fraction of Industrial water demand to be satisfied from Lift a  %    
    swAbstractionFraction_Lift_Irrigati  Array         Input, Fraction of Irrigation demand to be satisfied from Lift areas    %    
    using_lift_areas                     Flag          True if using_lift_areas = True in Settings, False otherwise            bool 
    lift_command_areas                   Array                                                                                 --   
    allocSegments                        Array                                                                                 --   
    swAbstractionFraction                Array         Input, Fraction of demands to be satisfied with surface water           %    
    allocation_zone                      Array                                                                                 --   
    modflowPumping                       Array                                                                                 --   
    leakage                              Array         Canal leakage leading to either groundwater recharge or runoff          m3   
    pumping                              Array                                                                                 --   
    Pumping_daily                        Array         Groundwater abstraction asked of MODFLOW. modfPumpingM_actual is the r  m    
    modflowDepth2                        Array                                                                                 --   
    modflowTopography                    Array                                                                                 --   
    allowedPumping                       Array                                                                                 --   
    ratio_irrWithdrawalGW_month          Array                                                                                 --   
    ratio_irrWithdrawalSW_month          Array                                                                                 --   
    act_irrWithdrawalSW_month            Array         Running total agent surface water withdrawals for the month             m    
    act_irrWithdrawalGW_month            Array         Running total agent groundwater withdrawals for the month               m    
    Desal_Domestic                       Array                                                                                 --   
    Desal_Industry                       Array                                                                                 --   
    Desal_Livestock                      Array                                                                                 --   
    Desal_Irrigation                     Array                                                                                 --   
    Channel_Domestic                     Array         Channel water abstracted for domestic                                   m    
    Channel_Industry                     Array         Channel water abstracted for industry                                   m    
    Channel_Livestock                    Array         Channel water abstracted for livestock                                  m    
    Channel_Irrigation                   Array         Channel water abstracted for irrigation                                 m    
    Lift_Domestic                        Array                                                                                 --   
    Lift_Industry                        Array                                                                                 --   
    Lift_Livestock                       Array                                                                                 --   
    Lift_Irrigation                      Array                                                                                 --   
    wwt_Domestic                         Array                                                                                 --   
    wwt_Industry                         Array                                                                                 --   
    wwt_Livestock                        Array                                                                                 --   
    wwt_Irrigation                       Array                                                                                 --   
    Lake_Domestic                        Array                                                                                 --   
    Lake_Industry                        Array                                                                                 --   
    Lake_Livestock                       Array                                                                                 --   
    Lake_Irrigation                      Array                                                                                 --   
    Res_Domestic                         Array                                                                                 --   
    Res_Industry                         Array                                                                                 --   
    Res_Livestock                        Array                                                                                 --   
    Res_Irrigation                       Array                                                                                 --   
    GW_Domestic                          Array         Groundwater withdrawals to satisfy domestic water requests              m    
    GW_Industry                          Array         Groundwater withdrawals to satisfy Industrial water requests            m    
    GW_Livestock                         Array         Groundwater withdrawals to satisfy Livestock water requests             m    
    GW_Irrigation                        Array         Groundwater withdrawals for Irrigation                                  m    
    abstractedLakeReservoirM3            Array         Abstractions from lakes and reservoirs at the location of the waterbod  m3   
    leakage_wwtC_daily                   Array                                                                                 --   
    act_bigLakeResAbst_wwt               Array                                                                                 --   
    act_DesalWaterAbstractM              Array                                                                                 --   
    act_totalIrrConsumption              Array         Total irrigation consumption                                            m    
    act_totalWaterConsumption            Array         Total water consumption                                                 m    
    act_indConsumption                   Array         Industrial consumption                                                  m    
    act_domConsumption                   Array         Domestic consumption                                                    m    
    act_livConsumption                   Array         Livestock consumptions                                                  m    
    returnflowIrr                        Array                                                                                 --   
    returnflowNonIrr                     Array                                                                                 --   
    nonIrrReturnFlowFraction             Array                                                                                 --   
    nonIrruse                            Array                                                                                 --   
    act_indDemand                        Array         Industrial demand                                                       m    
    act_domDemand                        Array         Domestic demand                                                         m    
    act_livDemand                        Array         Livestock demands                                                       m    
    nonIrrDemand                         Array                                                                                 --   
    totalWaterDemand                     Array         Irrigation and non-irrigation demand                                    m    
    act_totalWaterWithdrawal             Array         Total water withdrawals                                                 m    
    act_indWithdrawal                    Array         Industrial withdrawal                                                   m    
    act_domWithdrawal                    Array         Domestic withdrawal                                                     m    
    act_livWithdrawal                    Array         Livestock withdrawals                                                   m    
    unmet_lost                           Array         Fossil water that disappears instead of becoming return flow            m    
    pot_GroundwaterAbstract              Array         Potential groundwater abstraction. Primarily used without MODFLOW.      m    
    WB_elec                              Array         Fractions of live storage to be exported from basin                     366-d
    act_nonpaddyConsumption              Array         Non-paddy irrigation consumption                                        m    
    act_paddyConsumption                 Array         Paddy consumption                                                       m    
    act_irrPaddyDemand                   Array         paddy irrigation demand                                                 m    
    act_irrNonpaddyDemand                Array         non-paddy irrigation demand                                             m    
    pot_nonIrrConsumption                Array                                                                                 --   
    act_DesalWaterAbstractM3             Array                                                                                 --   
    AvlDesalM3                           Array                                                                                 --   
    act_channelAbst                      Array         Abstractions to satisfy demands from channels                           m    
    act_channelAbstract_Lift             Array         Abstractions from the channel in lift areas at the location of the cha  m    
    Lift_Other                           Array                                                                                 --   
    abstractedLakeReservoirM3C           Array         Compressed abstractedLakeReservoirM3                                    m3   
    remainNeed                           Array                                                                                 --   
    act_ResAbst_wwt                      Array                                                                                 --   
    act_lakeAbst                         Array         Abstractions from lakes at demand location                              m    
    act_ResAbst                          Array         Abstractions from reservoirs at demand location                         m    
    leakageC_daily                       Array                                                                                 --   
    leakageCanalsC_M                     Array                                                                                 --   
    Channel_Domestic_fromZone            Array                                                                                 --   
    Channel_Livestock_fromZone           Array                                                                                 --   
    Channel_Industry_fromZone            Array                                                                                 --   
    Channel_Irrigation_fromZone          Array                                                                                 --   
    Channel_Other                        Array                                                                                 --   
    GW_Domestic_fromZone                 Array                                                                                 --   
    GW_Livestock_fromZone                Array                                                                                 --   
    GW_Industry_fromZone                 Array                                                                                 --   
    GW_Irrigation_fromZone               Array                                                                                 --   
    GW_Other                             Array                                                                                 --   
    waterAbstract                        Array                                                                                 --   
    PumpingM3_daily                      Array                                                                                 --   
    unmet_lostirr                        Array         Fossil water for irrigation that disappears instead of becoming return  m    
    unmet_lostNonirr                     Array         Fossil water for non-irrigation that disappears instead of becoming re  m    
    wwtEffluentsGenerated_domestic       Array                                                                                 --   
    wwtEffluentsGenerated_industry       Array                                                                                 --   
    wwtSewerCollectedBySoruce            Array                                                                                 --   
    waterabstraction                     Array                                                                                 --   
    ===================================  ==========    ======================================================================  =====

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

        self.var.relaxGWagent = globals.inZero.copy()
        self.var.relaxSWagent = globals.inZero.copy()
        self.var.irrWithdrawalSW_max = globals.inZero.copy()
        self.var.irrWithdrawalGW_max = globals.inZero.copy()

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

            if 'irrigation_agent_SW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                self.var.irrWithdrawalSW_max = npareaaverage(
                    loadmap('irrigation_agent_SW_request_month_m3') + globals.inZero.copy(),
                    self.var.adminSegments)

                if 'relax_sw_agent' in binding:
                    if self.var.loadInit:
                        self.var.relaxSWagent = self.var.load_initial('relaxSWagent')
                    else:
                        self.var.relaxSWagent = loadmap('relax_sw_agent')

            if 'irrigation_agent_GW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                self.var.irrWithdrawalGW_max = npareaaverage(
                    loadmap('irrigation_agent_GW_request_month_m3') + globals.inZero.copy(),
                    self.var.adminSegments)

                if 'relax_gw_agent' in binding:
                    if self.var.loadInit:
                        self.var.relaxGWagent = self.var.load_initial('relaxGWagent')
                    else:
                        self.var.relaxGWagent = loadmap('relax_gw_agent')

            if 'relax_abstraction_fraction_initial' in binding:
                self.var.relax_abstraction_fraction_initial = loadmap(
                    'relax_abstraction_fraction_initial') + globals.inZero.copy()
            else:
                self.var.relax_abstraction_fraction_initial = 0.5 + globals.inZero.copy()

        self.var.includeWastewaterPits = False
        if 'includePitLatrine' in option:
            self.var.includeWastewaterPits = checkOption('includePitLatrine')

        # init unmetWaterDemand -> to calculate actual one the the unmet water demand from previous day is needed
        self.var.unmetDemandPaddy = self.var.load_initial('unmetDemandPaddy', default=globals.inZero.copy())
        self.var.unmetDemandNonpaddy = self.var.load_initial('unmetDemandNonpaddy', default=globals.inZero.copy())
        # in case fossil water abstraction is allowed this will be filled
        self.var.unmetDemand = globals.inZero.copy()
        self.var.unmetDemand_runningSum = self.var.load_initial('unmetDemand_runningSum',
                                                                  default=globals.inZero.copy())

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
                    self.var.waterdemandFixedYear = loadmap('waterdemandFixedYear')

            self.var.sectorSourceAbstractionFractions = False
            # Sector-,source-abstraction fractions facilitate designating the specific source for the specific sector
            # Sources: River, Lake, Reservoir, Groundwater
            # Sectors: Domestic, Industry, Livestock, Irrigation
            # Otherwise, one can distinguish only between surface and groundwater, irrigation and non-irrigation

            if 'sectorSourceAbstractionFractions' in option:
                if checkOption('sectorSourceAbstractionFractions'):
                    #print('Sector- and source-specific abstraction fractions are activated (water_demand.py)')
                    self.var.sectorSourceAbstractionFractions = True

                    self.var.swAbstractionFraction_Channel_Domestic = loadmap(
                        'swAbstractionFraction_Channel_Domestic')
                    self.var.swAbstractionFraction_Channel_Livestock = loadmap(
                        'swAbstractionFraction_Channel_Livestock')
                    self.var.swAbstractionFraction_Channel_Industry = loadmap(
                        'swAbstractionFraction_Channel_Industry')
                    self.var.swAbstractionFraction_Channel_Irrigation = loadmap(
                        'swAbstractionFraction_Channel_Irrigation')

                    self.var.swAbstractionFraction_Lake_Domestic = loadmap(
                        'swAbstractionFraction_Lake_Domestic')
                    self.var.swAbstractionFraction_Lake_Livestock = loadmap(
                        'swAbstractionFraction_Lake_Livestock')
                    self.var.swAbstractionFraction_Lake_Industry = loadmap(
                        'swAbstractionFraction_Lake_Industry')
                    self.var.swAbstractionFraction_Lake_Irrigation = loadmap(
                        'swAbstractionFraction_Lake_Irrigation')

                    self.var.swAbstractionFraction_Res_Domestic = loadmap(
                        'swAbstractionFraction_Res_Domestic')
                    self.var.swAbstractionFraction_Res_Livestock = loadmap(
                        'swAbstractionFraction_Res_Livestock')
                    self.var.swAbstractionFraction_Res_Industry = loadmap(
                        'swAbstractionFraction_Res_Industry')
                    self.var.swAbstractionFraction_Res_Irrigation = loadmap(
                        'swAbstractionFraction_Res_Irrigation')
                        
                    if self.var.includeDesal:
                        self.var.othAbstractionFraction_Desal_Domestic = loadmap(
                            'othAbstractionFraction_Desal_Domestic')
                        self.var.othAbstractionFraction_Desal_Livestock = loadmap(
                            'othAbstractionFraction_Desal_Livestock')
                        self.var.othAbstractionFraction_Desal_Industry = loadmap(
                            'othAbstractionFraction_Desal_Industry')
                        self.var.othAbstractionFraction_Desal_Irrigation = loadmap(
                            'othAbstractionFraction_Desal_Irrigation')
                            
                    if self.var.includeWastewater:
                        self.var.wwtAbstractionFraction_Res_Domestic = loadmap(
                            'wwtAbstractionFraction_Res_Domestic')
                        self.var.wwtAbstractionFraction_Res_Livestock = loadmap(
                            'wwtAbstractionFraction_Res_Livestock')
                        self.var.wwtAbstractionFraction_Res_Industry = loadmap(
                            'wwtAbstractionFraction_Res_Industry')
                        self.var.wwtAbstractionFraction_Res_Irrigation = loadmap(
                            'wwtAbstractionFraction_Res_Irrigation')

                    if not checkOption('limitAbstraction'):
                        self.var.gwAbstractionFraction_Domestic = 1 + globals.inZero.copy()
                        self.var.gwAbstractionFraction_Livestock = 1 + globals.inZero.copy()
                        self.var.gwAbstractionFraction_Industry = 1 + globals.inZero.copy()
                        self.var.gwAbstractionFraction_Irrigation = 1 + globals.inZero.copy()
                    else:
                        self.var.gwAbstractionFraction_Domestic = loadmap(
                            'gwAbstractionFraction_Domestic')
                        self.var.gwAbstractionFraction_Livestock = loadmap(
                            'gwAbstractionFraction_Livestock')
                        self.var.gwAbstractionFraction_Industry = loadmap(
                            'gwAbstractionFraction_Industry')
                        self.var.gwAbstractionFraction_Irrigation = loadmap(
                            'gwAbstractionFraction_Irrigation')


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

            self.var.swAbstractionFraction_Lift_Domestic = globals.inZero.copy()
            self.var.swAbstractionFraction_Lift_Livestock = globals.inZero.copy()
            self.var.swAbstractionFraction_Lift_Industry = globals.inZero.copy()
            self.var.swAbstractionFraction_Lift_Irrigation = globals.inZero.copy()

            self.var.using_lift_areas = False
            if 'using_lift_areas' in option:
                if checkOption('using_lift_areas'):

                    self.var.using_lift_areas = True
                    self.var.lift_command_areas = loadmap('lift_areas').astype(int)

                    if self.var.sectorSourceAbstractionFractions:
                        self.var.swAbstractionFraction_Lift_Domestic = loadmap(
                            'swAbstractionFraction_Lift_Domestic')
                        self.var.swAbstractionFraction_Lift_Livestock = loadmap(
                            'swAbstractionFraction_Lift_Livestock')
                        self.var.swAbstractionFraction_Lift_Industry = loadmap(
                            'swAbstractionFraction_Lift_Industry')
                        self.var.swAbstractionFraction_Lift_Irrigation = loadmap(
                            'swAbstractionFraction_Lift_Irrigation')

            # -------------------------------------------
            # partitioningGroundSurfaceAbstraction
            # partitioning abstraction sources: groundwater and surface water
            # partitioning based on local average baseflow (m3/s) and upstream average discharge (m3/s)
            # estimates of fractions of groundwater and surface water abstractions
            swAbstractionFraction = loadmap('swAbstractionFrac')

            if swAbstractionFraction < 0:

                averageBaseflowInput = loadmap('averageBaseflow')
                averageDischargeInput = loadmap('averageDischarge')
                # convert baseflow from m to m3/s
                if returnBool('baseflowInM'):
                    averageBaseflowInput = averageBaseflowInput * self.var.cellArea * self.var.InvDtSec

                if checkOption('usingAllocSegments'):
                    averageBaseflowInput = np.where(self.var.allocSegments > 0,
                                                    npareaaverage(averageBaseflowInput, self.var.allocSegments),
                                                    averageBaseflowInput)

                    # averageUpstreamInput = np.where(self.var.allocSegments > 0,
                    #                                npareamaximum(averageDischargeInput, self.var.allocSegments),
                    #                                averageDischargeInput)

                swAbstractionFraction = np.maximum(
                    0.0, np.minimum(1.0, averageDischargeInput / np.maximum(
                        1e-20, averageDischargeInput + averageBaseflowInput)))
                swAbstractionFraction = np.minimum(1.0, np.maximum(0.0, swAbstractionFraction))

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

            # allocation zone
            # regular grid inside the 2d array
            # inner grid size
            inner = 1
            if "allocation_area" in binding:
                inner = int(loadmap('allocation_area'))

            latldd, lonldd, cell, invcellldd, rows, cols = readCoord(cbinding('Ldd'))
            filename = os.path.splitext(cbinding('Ldd'))[0] + '.nc'
            if os.path.isfile(filename):
                cut0, cut1, cut2, cut3 = mapattrNetCDF(filename, check=False)
            else:
                filename = os.path.splitext(cbinding('Ldd'))[0] + '.tif'

                if not(os.path.isfile(filename)):
                    filename = os.path.splitext(cbinding('Ldd'))[0] + '.map'
                    
                nf2 = gdal.Open(filename, gdalconst.GA_ReadOnly)
                cut0, cut1, cut2, cut3 = mapattrTiff(nf2)

            arr = np.kron(np.arange(rows // inner * cols // inner).reshape((rows // inner, cols // inner)),
                          np.ones((inner, inner)))
            arr = arr[cut2:cut3, cut0:cut1].astype(int)
            self.var.allocation_zone = compressArray(arr)

            self.var.modflowPumping = globals.inZero.copy()
            self.var.leakage = globals.inZero.copy()
            self.var.pumping = globals.inZero.copy()
            self.var.modfPumpingM = globals.inZero.copy()
            self.var.Pumping_daily = globals.inZero.copy()
            self.var.modflowDepth2 = 0
            self.var.modflowTopography = 0
            self.var.allowedPumping = globals.inZero.copy()
            self.var.leakageCanals_M = globals.inZero.copy()

            self.var.act_nonIrrWithdrawal = globals.inZero.copy()
            self.var.ratio_irrWithdrawalGW_month = globals.inZero.copy()
            self.var.ratio_irrWithdrawalSW_month = globals.inZero.copy()
            self.var.act_irrWithdrawalSW_month = globals.inZero.copy()
            self.var.act_irrWithdrawalGW_month = globals.inZero.copy()

            self.var.Desal_Domestic = globals.inZero.copy()
            self.var.Desal_Industry = globals.inZero.copy()
            self.var.Desal_Livestock = globals.inZero.copy()
            self.var.Desal_Irrigation = globals.inZero.copy()
            
            self.var.Channel_Domestic = globals.inZero.copy()
            self.var.Channel_Industry = globals.inZero.copy()
            self.var.Channel_Livestock = globals.inZero.copy()
            self.var.Channel_Irrigation = globals.inZero.copy()

            self.var.Lift_Domestic = globals.inZero.copy()
            self.var.Lift_Industry = globals.inZero.copy()
            self.var.Lift_Livestock = globals.inZero.copy()
            self.var.Lift_Irrigation = globals.inZero.copy()
            
            self.var.wwt_Domestic = globals.inZero.copy()
            self.var.wwt_Industry = globals.inZero.copy()
            self.var.wwt_Livestock = globals.inZero.copy()
            self.var.wwt_Irrigation = globals.inZero.copy()

            self.var.Lake_Domestic = globals.inZero.copy()
            self.var.Lake_Industry = globals.inZero.copy()
            self.var.Lake_Livestock = globals.inZero.copy()
            self.var.Lake_Irrigation = globals.inZero.copy()

            self.var.Res_Domestic = globals.inZero.copy()
            self.var.Res_Industry = globals.inZero.copy()
            self.var.Res_Livestock = globals.inZero.copy()
            self.var.Res_Irrigation = globals.inZero.copy()

            self.var.GW_Domestic = globals.inZero.copy()
            self.var.GW_Industry = globals.inZero.copy()
            self.var.GW_Livestock = globals.inZero.copy()
            self.var.GW_Irrigation = globals.inZero.copy()
            self.var.abstractedLakeReservoirM3 = globals.inZero.copy()

            self.var.swAbstractionFraction_domestic = 1 + globals.inZero.copy()
            self.var.ind_efficiency = 1.
            self.var.dom_efficiency = 1.
            self.var.liv_efficiency = 1
 
            # for wastewater package
            if checkOption('includeWaterBodies'):
                self.var.leakage_wwtC_daily = np.compress(self.var.compress_LR, globals.inZero.copy())
            self.var.act_bigLakeResAbst_wwt = globals.inZero.copy()
            
            self.var.act_DesalWaterAbstractM = globals.inZero.copy()
            
            self.var.act_nonIrrConsumption = globals.inZero.copy()
            self.var.act_totalIrrConsumption = globals.inZero.copy()
            self.var.act_totalWaterConsumption = globals.inZero.copy()
            self.var.act_indConsumption = globals.inZero.copy()
            self.var.act_domConsumption = globals.inZero.copy()
            self.var.act_livConsumption = globals.inZero.copy()
            self.var.returnflowIrr = globals.inZero.copy()
            self.var.returnflowNonIrr = globals.inZero.copy()
            self.var.pitLatrinToGW = globals.inZero.copy()
            self.var.act_irrNonpaddyWithdrawal = globals.inZero.copy()
            self.var.act_irrPaddyWithdrawal = globals.inZero.copy()

        else:  # no water demand
            self.var.ratio_irrWithdrawalGW_month = globals.inZero.copy()
            self.var.ratio_irrWithdrawalSW_month = globals.inZero.copy()

            self.var.nonIrrReturnFlowFraction = globals.inZero.copy()
            self.var.nonFossilGroundwaterAbs = globals.inZero.copy()
            self.var.nonIrruse = globals.inZero.copy()
            self.var.act_indDemand = globals.inZero.copy()
            self.var.act_domDemand = globals.inZero.copy()
            self.var.act_livDemand = globals.inZero.copy()
            self.var.nonIrrDemand = globals.inZero.copy()
            self.var.totalIrrDemand = globals.inZero.copy()
            self.var.totalWaterDemand = globals.inZero.copy()
            self.var.act_irrWithdrawal = globals.inZero.copy()
            self.var.act_nonIrrWithdrawal = globals.inZero.copy()
            self.var.act_totalWaterWithdrawal = globals.inZero.copy()
            self.var.act_indConsumption = globals.inZero.copy()
            self.var.act_domConsumption = globals.inZero.copy()
            self.var.act_livConsumption = globals.inZero.copy()

            self.var.act_indWithdrawal = globals.inZero.copy()
            self.var.act_domWithdrawal = globals.inZero.copy()
            self.var.act_livWithdrawal = globals.inZero.copy()

            self.var.act_totalIrrConsumption = globals.inZero.copy()
            self.var.act_totalWaterConsumption = globals.inZero.copy()
            self.var.unmetDemand = globals.inZero.copy()
            self.var.unmetDemand_runningSum = globals.inZero.copy()
            self.var.addtoevapotrans = globals.inZero.copy()
            self.var.returnflowIrr = globals.inZero.copy()
            self.var.returnflowNonIrr = globals.inZero.copy()
            self.var.returnFlow = globals.inZero.copy()
            self.var.unmetDemandPaddy = globals.inZero.copy()
            self.var.unmetDemandNonpaddy = globals.inZero.copy()
            self.var.ind_efficiency = 1.
            self.var.dom_efficiency = 1.
            self.var.liv_efficiency = 1
            self.var.modflowPumping = 0
            self.var.modflowDepth2 = 0
            self.var.modflowTopography = 0
            self.var.act_bigLakeResAbst = globals.inZero.copy()
            self.var.act_bigLakeResAbst_wwt = globals.inZero.copy()
    
            self.var.leakage = globals.inZero.copy()
            self.var.pumping = globals.inZero.copy()
            self.var.unmet_lost = globals.inZero.copy()
            self.var.pot_GroundwaterAbstract = globals.inZero.copy()
            self.var.leakageCanals_M = globals.inZero.copy()

            self.var.WB_elec = globals.inZero.copy()
            self.var.relaxSWagent = globals.inZero.copy()
            self.var.relaxGWagent = globals.inZero.copy()
            
            self.var.Desal_Domestic = globals.inZero.copy()
            self.var.Desal_Industry = globals.inZero.copy()
            self.var.Desal_Livestock = globals.inZero.copy()
            self.var.Desal_Irrigation = globals.inZero.copy()
            
            self.var.Channel_Domestic = globals.inZero.copy()
            self.var.Channel_Industry = globals.inZero.copy()
            self.var.Channel_Livestock = globals.inZero.copy()
            self.var.Channel_Irrigation = globals.inZero.copy()

            self.var.Lift_Domestic = globals.inZero.copy()
            self.var.Lift_Industry = globals.inZero.copy()
            self.var.Lift_Livestock = globals.inZero.copy()
            self.var.Lift_Irrigation = globals.inZero.copy()

            self.var.Lake_Domestic = globals.inZero.copy()
            self.var.Lake_Industry = globals.inZero.copy()
            self.var.Lake_Livestock = globals.inZero.copy()
            self.var.Lake_Irrigation = globals.inZero.copy()

            self.var.Res_Domestic = globals.inZero.copy()
            self.var.Res_Industry = globals.inZero.copy()
            self.var.Res_Livestock = globals.inZero.copy()
            self.var.Res_Irrigation = globals.inZero.copy()

            self.var.GW_Domestic = globals.inZero.copy()
            self.var.GW_Industry = globals.inZero.copy()
            self.var.GW_Livestock = globals.inZero.copy()
            self.var.GW_Irrigation = globals.inZero.copy()

            self.var.abstractedLakeReservoirM3 = globals.inZero.copy()
            self.var.swAbstractionFraction_domestic = 1 + globals.inZero.copy()

            self.var.act_nonpaddyConsumption = globals.inZero.copy()
            self.var.act_paddyConsumption = globals.inZero.copy()
            self.var.act_irrNonpaddyWithdrawal = globals.inZero.copy()
            self.var.act_irrPaddyWithdrawal = globals.inZero.copy()

            self.var.modfPumpingM = globals.inZero.copy()
            self.var.Pumping_daily = globals.inZero.copy()

            self.var.act_irrPaddyDemand = globals.inZero.copy()
            self.var.act_irrNonpaddyDemand = globals.inZero.copy()
            self.var.domesticDemand = globals.inZero.copy()
            self.var.industryDemand = globals.inZero.copy()
            self.var.livestockDemand = globals.inZero.copy()

            # for wastewater package
            if checkOption('includeWaterBodies'):
                self.var.leakage_wwtC_daily = np.compress(self.var.compress_LR, globals.inZero.copy())
            self.var.act_bigLakeResAbst_wwt = globals.inZero.copy()
            
            self.var.act_DesalWaterAbstractM = globals.inZero.copy()

            self.var.act_nonIrrConsumption = globals.inZero.copy()

    def commandAreaOperation(self, remainNeed, command_areas, maxFracForIrrigation,
                             water_conveyance_efficiency, wwt_only=False):
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
        maxFracForIrrigation : ndarray
            Maximum fraction of reservoir storage available for irrigation abstraction
            per reservoir [dimensionless, 0-1]. Represents operational constraints and
            environmental flow requirements.
        water_conveyance_efficiency : ndarray
            Water conveyance efficiency factor [dimensionless, 0-1]. Accounts for
            losses during water transport from reservoirs to demand locations through
            canals and distribution infrastructure.
        wwt_only : bool, optional
            Flag indicating wastewater treatment only operations (default False).
            When True, limits operations to reservoirs designated for wastewater
            treatment. When False, excludes wastewater treatment reservoirs.
            
        Returns
        -------
        tuple of (ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment, resStorageTotal_allocC)
            ResAbstractFactorC : ndarray
                Compressed abstraction factors for reservoir cells [dimensionless].
                Fraction of available reservoir storage to be abstracted.
            act_bigLakeResAbst_alloc : ndarray
                Actual water abstraction allocated per command area [mÂ³].
                Total volume to be abstracted considering all constraints.
            demand_Segment : ndarray
                Total water demand per command area [mÂ³].
                Aggregated demand across all cells within each command area.
            resStorageTotal_allocC : ndarray
                Compressed total reservoir storage per command area [mÂ³].
                Storage of the dominant reservoir serving each command area.
                
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
            command_areas > 0, npareatotal(remainNeed * self.var.cellArea, command_areas),
            0)  # [M3]

        # Reservoir associated with the Command Area
        #
        # If there is more than one reservoir in a command area, the storage of the reservoir with
        # maximum storage in this time-step is chosen. The map resStorageTotal_alloc holds this
        # maximum reservoir storage within a command area in all cells within that command area

        ReservoirsThatAreCurrentlyReservoirs = np.where(
            self.var.waterBodyTypCTemp == 2, self.var.reservoirStorageM3C,
            np.where(self.var.waterBodyTypCTemp == 4, self.var.reservoirStorageM3C, 0))
        if wwt_only:
            ReservoirsThatAreCurrentlyReservoirs = np.where(
                np.compress(self.var.compress_LR, self.var.resId_restricted) > 0,
                ReservoirsThatAreCurrentlyReservoirs, 0)
        else:
            ReservoirsThatAreCurrentlyReservoirs = np.where(
                np.compress(self.var.compress_LR, self.var.resId_restricted) == 0,
                ReservoirsThatAreCurrentlyReservoirs, 0)
        reservoirStorageM3 = globals.inZero.copy()
        # np.put(reservoirStorageM3, self.var.decompress_LR, self.var.reservoirStorageM3C)
        np.put(reservoirStorageM3, self.var.decompress_LR, ReservoirsThatAreCurrentlyReservoirs)
        resStorageTotal_alloc = np.where(command_areas > 0,
                                        npareamaximum(reservoirStorageM3,
                                                    command_areas), 0)  # [M3]

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
            npareamaximum(resStorage_maxFracForIrrigation, command_areas), 0)

        act_bigLakeResAbst_alloc = np.minimum(
            resStorage_maxFracForIrrigation_CA * resStorageTotal_alloc,
            demand_Segment / water_conveyance_efficiency)  # [M3]

        # fraction of water abstracted versus water available for total segment reservoir volumes
        ResAbstractFactor = np.where(resStorageTotal_alloc > 0,
                                    divideValues(act_bigLakeResAbst_alloc, resStorageTotal_alloc),
                                    0)

        # Compressed version needs to be corrected as above
        ResAbstractFactorC = np.compress(self.var.compress_LR, ResAbstractFactor)
        ResAbstractFactorC = np.where(
            resStorageTotal_allocC == self.var.reservoirStorageM3C, ResAbstractFactorC, 0.)
        return (ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment,
                resStorageTotal_allocC)
                                                            
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

        if self.var.modflow:

            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.environmental_need.dynamic()
            else:
                self.var.envFlow = 0.00001  # 0.01mm

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
                self.environmental_need.dynamic()
            else:
                self.irrigation.dynamic()
                # if not self.var.modflow:
                self.environmental_need.dynamic()

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

                # non-irrg fracs in nonIrrDemand
                frac_industry = divideValues(self.var.industryDemand, self.var.nonIrrDemand)
                frac_domestic = divideValues(self.var.domesticDemand, self.var.nonIrrDemand)
                frac_livestock = divideValues(self.var.livestockDemand, self.var.nonIrrDemand)

                # Sum up water demand
                # totalDemand [m]: total maximum (potential) water demand: irrigation and non irrigation
                totalDemand = self.var.nonIrrDemand + self.var.totalIrrDemand  # in [m]
            else:  # only irrigation is considered
                totalDemand = np.copy(self.var.totalIrrDemand)  # in [m]
                self.var.domesticDemand = globals.inZero.copy()
                self.var.industryDemand = globals.inZero.copy()
                self.var.livestockDemand = globals.inZero.copy()
                self.var.nonIrrDemand = globals.inZero.copy()
                self.var.pot_nonIrrConsumption = globals.inZero.copy()
                self.var.nonIrrReturnFlowFraction = globals.inZero.copy()
                frac_industry = globals.inZero.copy()
                frac_domestic = globals.inZero.copy()
                frac_livestock = globals.inZero.copy()
                # print('-----------------------------totalDemand---------: ', np.mean(totalDemand))

            # ----------------------------------------------------
            # WATER AVAILABILITY

            if not self.var.modflow:  # already done if ModFlow coupling
                # conversion m3 -> m # minus environmental flow
                self.var.readAvlChannelStorageM = np.maximum(
                    0., self.var.channelStorage * self.var.M3toM - self.var.envFlow)  # in [m]

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
                        self.var.swAbstractionFraction_Channel_Irrigation = loadmap(
                            'swAbstractionFraction_Channel_Irrigation')
                        if self.var.using_lift_areas:
                            self.var.swAbstractionFraction_Lift_Irrigation = loadmap(
                                'swAbstractionFraction_Lift_Irrigation')
                        self.var.swAbstractionFraction_Lake_Irrigation = loadmap(
                            'swAbstractionFraction_Lake_Irrigation')
                        self.var.swAbstractionFraction_Res_Irrigation = loadmap(
                            'swAbstractionFraction_Res_Irrigation')
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
                        self.var.gwAbstractionFraction_Irrigation = loadmap(
                            'gwAbstractionFraction_Irrigation')
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
                                                                         loadmap('commandAreasRelaxGwAbstraction'),
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
                        self.var.AvlDesalM3 = self.var.desalAnnualCap[dateVar['currDate'].year] / 365
                        abstractLimitCoeff = (np.minimum(np.nansum(pot_DesalAbst * self.var.cellArea),
                                                       self.var.AvlDesalM3) /
                                               np.nansum(pot_DesalAbst * self.var.cellArea))
                        self.var.act_DesalWaterAbstractM = pot_DesalAbst * abstractLimitCoeff
                    else:
                        self.var.act_DesalWaterAbstractM = pot_DesalAbst
     
                    #self.var.act_DesalWaterAbstractM = self.var.act_DesalWaterAbstractM3 / self.var.cellArea
            if self.var.sectorSourceAbstractionFractions:
                if self.var.includeDesal:
                    self.var.Desal_Domestic = np.minimum(
                        self.var.act_DesalWaterAbstractM,
                        self.var.othAbstractionFraction_Desal_Domestic * self.var.domesticDemand)
                    self.var.Desal_Livestock = np.minimum(
                        self.var.act_DesalWaterAbstractM - self.var.Desal_Domestic,
                        self.var.othAbstractionFraction_Desal_Livestock * self.var.livestockDemand)
                    self.var.Desal_Industry = np.minimum(
                        self.var.act_DesalWaterAbstractM - self.var.Desal_Domestic - self.var.Desal_Livestock,
                        self.var.othAbstractionFraction_Desal_Industry * self.var.industryDemand)
                    self.var.Desal_Irrigation = np.minimum(
                        (self.var.act_DesalWaterAbstractM - self.var.Desal_Domestic -
                         self.var.Desal_Livestock - self.var.Desal_Industry),
                        self.var.othAbstractionFraction_Desal_Irrigation * self.var.totalIrrDemand)
               
                
            
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
                self.var.Channel_Domestic = np.minimum(self.var.act_channelAbst,
                                                       self.var.swAbstractionFraction_Channel_Domestic * self.var.domesticDemand)
                self.var.Channel_Livestock = np.minimum(self.var.act_channelAbst - self.var.Channel_Domestic,
                                                        self.var.swAbstractionFraction_Channel_Livestock * self.var.livestockDemand)
                self.var.Channel_Industry = np.minimum(
                    self.var.act_channelAbst - self.var.Channel_Domestic - self.var.Channel_Livestock,
                    self.var.swAbstractionFraction_Channel_Industry * self.var.industryDemand)
                self.var.Channel_Irrigation = np.minimum(
                    self.var.act_channelAbst - self.var.Channel_Domestic - self.var.Channel_Livestock - self.var.Channel_Industry,
                    self.var.swAbstractionFraction_Channel_Irrigation * self.var.totalIrrDemand)

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
                    pot_Lift_Irrigation = np.maximum(pot_Lift_Irrigation,
                                                    self.var.irrWithdrawalSW_max * self.var.InvCellArea)

                pot_liftAbst = pot_Lift_Domestic + pot_Lift_Livestock + pot_Lift_Industry + pot_Lift_Irrigation


                remainNeed_afterLocal = pot_liftAbst.copy()

                # The remaining demand within each command area [M3] is put into a map where each cell in the command
                # area holds this total demand
                demand_Segment_lift = np.where(self.var.lift_command_areas > 0,
                                               npareatotal(remainNeed_afterLocal * self.var.cellArea,
                                                           self.var.lift_command_areas),
                                               0) / self.var.cellArea # [M]

                available_Segment_lift = np.where(self.var.lift_command_areas > 0,
                                                  npareatotal(self.var.readAvlChannelStorageM * self.var.cellArea,
                                                              self.var.lift_command_areas),
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
                self.var.readAvlChannelStorageM = np.where(self.var.readAvlChannelStorageM < 0.01, 0,
                                                           self.var.readAvlChannelStorageM)
                # Used in landCover for riverbedExchange
                self.var.act_channelAbstract_Lift = cell_lift_abstraction

                if self.var.sectorSourceAbstractionFractions:

                    # A
                    self.var.Lift_Domestic = np.minimum(cell_lift_allocation, pot_Lift_Domestic)
                    self.var.Lift_Livestock = np.minimum(cell_lift_allocation - self.var.Lift_Domestic,
                                                         pot_Lift_Livestock)
                    self.var.Lift_Industry = np.minimum(
                        cell_lift_allocation - self.var.Lift_Domestic - self.var.Lift_Livestock,
                        pot_Lift_Industry)
                    self.var.Lift_Irrigation = np.minimum(
                        cell_lift_allocation - self.var.Lift_Domestic - self.var.Lift_Livestock - self.var.Lift_Industry,
                        pot_Lift_Irrigation)
                    self.var.Lift_Other = cell_lift_allocation - self.var.Lift_Domestic - self.var.Lift_Livestock - self.var.Lift_Industry - self.var.Lift_Irrigation

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
                        remainNeedBig_wwt = npareatotal(remainNeed,  self.var.waterBodyBuffer_wwt)
                        remainNeedBig_wwtC = np.compress(self.var.compress_LR, remainNeedBig_wwt)
                        #print(np.compress(self.var.compress_LR, npareatotal(remainNeed * self.var.cellArea,  self.var.waterBodyBuffer_wwt)))
                        # Storage of a big lake
                        ReservoirsThatAreCurrentlyReservoirs = np.where(self.var.waterBodyTypCTemp == 2, \
                                    self.var.reservoirStorageM3C, np.where(self.var.waterBodyTypCTemp == 4, self.var.reservoirStorageM3C, 0))
                        
                        ReservoirsThatAreCurrentlyReservoirs = np.where(np.compress(self.var.compress_LR, self.var.resId_restricted) > 0, ReservoirsThatAreCurrentlyReservoirs, 0)
                        
                        
                        lakeResStorageC = np.where(self.var.waterBodyTypCTemp == 0, 0.,
                                            np.where(self.var.waterBodyTypCTemp == 1, self.var.lakeStorageC,
                                                        ReservoirsThatAreCurrentlyReservoirs)) / self.var.MtoM3C

                        minlake = np.maximum(0., 0.98 * lakeResStorageC)  # reasonable but arbitrary limit
                        act_bigLakeAbst_wwtC = np.minimum(minlake, remainNeedBig_wwtC)
                     
                        # substract from both, because it is sorted by self.var.waterBodyTypCTemp
                        self.var.lakeStorageC = self.var.lakeStorageC - act_bigLakeAbst_wwtC * self.var.MtoM3C
                        self.var.lakeVolumeM3C = self.var.lakeVolumeM3C - act_bigLakeAbst_wwtC * self.var.MtoM3C
                        self.var.reservoirStorageM3C = self.var.reservoirStorageM3C - act_bigLakeAbst_wwtC * self.var.MtoM3C
                        # and from the combined onenpfor waterbalance issues
                        self.var.lakeResStorageC = self.var.lakeResStorageC - act_bigLakeAbst_wwtC * self.var.MtoM3C
                        

                        self.var.abstractedLakeReservoirM3C += act_bigLakeAbst_wwtC.copy() * self.var.MtoM3C
                        self.var.lakeResStorage = globals.inZero.copy()
                        np.put(self.var.lakeResStorage, self.var.decompress_LR, self.var.lakeResStorageC)
                        bigLakesFactor_wwtC = divideValues(act_bigLakeAbst_wwtC, remainNeedBig_wwtC)
                        # and back to the big array
                        bigLakesFactor_wwt = globals.inZero.copy()
                        np.put(bigLakesFactor_wwt, self.var.decompress_LR, bigLakesFactor_wwtC)

                        # bigLakesFactorAllaroundlake = npareamaximum(bigLakesFactor, self.var.waterBodyID)
                        bigLakesFactorAllaroundlake_wwt = npareamaximum(bigLakesFactor_wwt, self.var.waterBodyBuffer_wwt)
                        #print(np.compress(self.var.compress_LR, bigLakesFactorAllaroundlake_wwt))
                        # abstraction from big lakes is partioned to the users around the lake
                        self.var.act_bigLakeResAbst_wwt = remainNeed * bigLakesFactorAllaroundlake_wwt
                        # remaining need is used from lakes and reservoirs without water use restrictions
                        #remainNeed0 = remainNeed * (1 - bigLakesFactorAllaroundlake_wwt)
                       
                        
                        # allocate water demand in case sectorSourceAbstractionFractions = True
                        if self.var.sectorSourceAbstractionFractions:
                            self.var.wwt_Domestic = np.minimum(self.var.act_bigLakeResAbst_wwt,
                                                           pot_wwt_Domestic)
                            self.var.wwt_Livestock = np.minimum(self.var.act_bigLakeResAbst_wwt - self.var.wwt_Domestic,
                                                                pot_wwt_Livestock)
                            self.var.wwt_Industry = np.minimum(
                                self.var.act_bigLakeResAbst_wwt - self.var.wwt_Domestic - self.var.wwt_Livestock,
                                pot_wwt_Industry)
                            
                            self.var.wwt_Irrigation = np.minimum(
                                self.var.act_bigLakeResAbst_wwt - self.var.wwt_Domestic - self.var.wwt_Livestock - self.var.wwt_Industry,
                                pot_wwt_Irrigation)
                    else:
                        ## opt 2:  command areas are used
                        #self.var.abstractedLakeReservoirM3C = np.compress(self.var.compress_LR, globals.inZero.copy())
                        self.var.act_ResAbst_wwt = globals.inZero.copy()
                        self.var.act_bigLakeResAbst_wwt = globals.inZero.copy()

                        # load maximum reservoir volume fraction available for irrigation
                        day_of_year = globals.dateVar['currDate'].timetuple().tm_yday
                        if 'Reservoir_releases' in binding:
                            resStorage_maxFracForIrrigation = readnetcdf2('Reservoir_releases', day_of_year,
                                                                          useDaily='DOY', value='Fraction of Volume')
                        elif 'wwt_reservoir_releases' in binding:
                                    resStorage_maxFracForIrrigation = np.maximum(np.minimum(loadmap('wwt_reservoir_releases'), 1.), 0.) + globals.inZero.copy()
                                    
                        elif self.var.reservoir_releases_excel_option:
                            resStorage_maxFracForIrrigation = globals.inZero.copy()
                            resStorage_maxFracForIrrigationC = np.where(self.var.lakeResStorage_release_ratioC > -1,
                                                                        self.var.reservoir_supply[dateVar['doy']-1],
                                                                        0.03)
                            np.put(resStorage_maxFracForIrrigation, self.var.decompress_LR, resStorage_maxFracForIrrigationC)
                        else:
                            resStorage_maxFracForIrrigation = 0.03 + globals.inZero.copy()                       

                        if self.var.sectorSourceAbstractionFractions:
                            remainNeedPre = pot_wwt_Domestic + pot_wwt_Livestock + pot_wwt_Industry
                            remainNeed = pot_wwt_Irrigation
                            
                            # remainNeed, command_areas, maxFracForIrrigation, water_conveyance_efficiency        
                            ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment, resStorageTotal_allocC = self.commandAreaOperation(remainNeed = remainNeedPre, command_areas = self.var.reservoir_command_areas_wwt ,\
                                maxFracForIrrigation = resStorage_maxFracForIrrigation, water_conveyance_efficiency = self.var.Water_conveyance_efficiency, wwt_only = True)
                            self.var.lakeStorageC -= self.var.reservoirStorageM3C * ResAbstractFactorC
                            self.var.lakeVolumeM3C -= self.var.reservoirStorageM3C * ResAbstractFactorC
                            self.var.lakeResStorageC -= self.var.reservoirStorageM3C * ResAbstractFactorC
                            self.var.abstractedLakeReservoirM3C += self.var.reservoirStorageM3C * ResAbstractFactorC
                            self.var.reservoirStorageM3C -= self.var.reservoirStorageM3C * ResAbstractFactorC

                            np.put(self.var.abstractedLakeReservoirM3, self.var.decompress_LR,
                                self.var.abstractedLakeReservoirM3C)

                            self.var.lakeResStorage = globals.inZero.copy()
                            np.put(self.var.lakeResStorage, self.var.decompress_LR, self.var.lakeResStorageC)

                            metRemainSegment = np.where(demand_Segment > 0,
                                                        divideValues(act_bigLakeResAbst_alloc * self.var.Water_conveyance_efficiency,
                                                                    demand_Segment), 0)  # by definition <= 1

                            self.var.act_bigLakeResAbst_wwt = remainNeedPre * metRemainSegment
                            self.var.act_SurfaceWaterAbstract += remainNeedPre * metRemainSegment

                            self.var.act_ResAbst_wwt = remainNeedPre * metRemainSegment
                        
                        if self.var.sectorSourceAbstractionFractions:
                            self.var.wwt_Domestic = np.minimum(self.var.act_ResAbst_wwt,
                                                           pot_wwt_Domestic)
                            self.var.wwt_Livestock = np.minimum(self.var.act_ResAbst_wwt - self.var.wwt_Domestic,
                                                                pot_wwt_Livestock)
                            self.var.wwt_Industry = np.minimum(
                                self.var.act_ResAbst_wwt - self.var.wwt_Domestic - self.var.wwt_Livestock,
                                pot_wwt_Industry)
                         
                        # Irrigation
                        
                        
                                                                # remainNeed, command_areas, maxFracForIrrigation, water_conveyance_efficiency        
                        ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment, resStorageTotal_allocC = self.commandAreaOperation(remainNeed = remainNeed, command_areas = self.var.reservoir_command_areas_wwt ,\
                                             maxFracForIrrigation = resStorage_maxFracForIrrigation, water_conveyance_efficiency = self.var.Water_conveyance_efficiency, wwt_only = True)
                        self.var.lakeStorageC -= self.var.reservoirStorageM3C * ResAbstractFactorC
                        self.var.lakeVolumeM3C -= self.var.reservoirStorageM3C * ResAbstractFactorC
                        self.var.lakeResStorageC -= self.var.reservoirStorageM3C * ResAbstractFactorC
                        self.var.abstractedLakeReservoirM3C += self.var.reservoirStorageM3C * ResAbstractFactorC
                        self.var.reservoirStorageM3C -= self.var.reservoirStorageM3C * ResAbstractFactorC

                        np.put(self.var.abstractedLakeReservoirM3, self.var.decompress_LR,
                            self.var.abstractedLakeReservoirM3C)

                        self.var.lakeResStorage = globals.inZero.copy()
                        np.put(self.var.lakeResStorage, self.var.decompress_LR, self.var.lakeResStorageC)

                        metRemainSegment = np.where(demand_Segment > 0,
                                                    divideValues(act_bigLakeResAbst_alloc * self.var.Water_conveyance_efficiency,
                                                                demand_Segment), 0)  # by definition <= 1
                            
                        self.var.act_bigLakeResAbst_wwt += remainNeed * metRemainSegment
                        self.var.act_ResAbst_wwt += remainNeed * metRemainSegment
                            
                        self.var.leakage_wwtC_daily = resStorageTotal_allocC * ResAbstractFactorC * (
                                1 - np.compress(self.var.compress_LR, self.var.Water_conveyance_efficiency))

                        
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
                remainNeedBig = npareatotal(remainNeed0, self.var.waterBodyBuffer)
                remainNeedBigC = np.compress(self.var.compress_LR, remainNeedBig)

                # Storage of a big lake
                lakeResStorageC = np.where(self.var.waterBodyTypCTemp == 0, 0.,
                                           np.where(self.var.waterBodyTypCTemp == 1, self.var.lakeStorageC,
                                                    self.var.reservoirStorageM3C)) / self.var.MtoM3C

                minlake = np.maximum(0., 0.98 * lakeResStorageC)  # reasonable but arbitrary limit
                act_bigLakeAbstC = np.minimum(minlake, remainNeedBigC)
                # substract from both, because it is sorted by self.var.waterBodyTypCTemp
                self.var.lakeStorageC = self.var.lakeStorageC - act_bigLakeAbstC * self.var.MtoM3C
                self.var.lakeVolumeM3C = self.var.lakeVolumeM3C - act_bigLakeAbstC * self.var.MtoM3C
                self.var.reservoirStorageM3C = self.var.reservoirStorageM3C - act_bigLakeAbstC * self.var.MtoM3C
                # and from the combined one for waterbalance issues
                self.var.lakeResStorageC = self.var.lakeResStorageC - act_bigLakeAbstC * self.var.MtoM3C

                self.var.abstractedLakeReservoirM3C = act_bigLakeAbstC.copy() * self.var.MtoM3C

                self.var.lakeResStorage = globals.inZero.copy()
                np.put(self.var.lakeResStorage, self.var.decompress_LR, self.var.lakeResStorageC)
                bigLakesFactorC = divideValues(act_bigLakeAbstC, remainNeedBigC)

                # and back to the big array
                bigLakesFactor = globals.inZero.copy()
                np.put(bigLakesFactor, self.var.decompress_LR, bigLakesFactorC)

                # bigLakesFactorAllaroundlake = npareamaximum(bigLakesFactor, self.var.waterBodyID)
                bigLakesFactorAllaroundlake = npareamaximum(bigLakesFactor, self.var.waterBodyBuffer)

                # abstraction from big lakes is partioned to the users around the lake
                self.var.act_bigLakeResAbst = remainNeed0  * mskWtrBody_unrestricted * bigLakesFactorAllaroundlake   

                # remaining need is used from small lakes
                remainNeed1 = remainNeed0 * (1 - bigLakesFactorAllaroundlake)
                # minlake = np.maximum(0.,self.var.smalllakeStorage - self.var.minsmalllakeStorage) * self.var.M3toM

                if returnBool('useSmallLakes'):
                    minlake = np.maximum(0., 0.98 * self.var.smalllakeStorage) * self.var.M3toM
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
                    self.var.Lake_Domestic = np.minimum(self.var.act_lakeAbst, pot_Lake_Domestic)
                    self.var.Lake_Livestock = np.minimum(self.var.act_lakeAbst - self.var.Lake_Domestic,
                                                         pot_Lake_Livestock)
                    self.var.Lake_Industry = np.minimum(
                        self.var.act_lakeAbst - self.var.Lake_Domestic - self.var.Lake_Livestock,
                        pot_Lake_Industry)
                    self.var.Lake_Irrigation = np.minimum(
                        self.var.act_lakeAbst - self.var.Lake_Domestic - self.var.Lake_Livestock - self.var.Lake_Industry,
                        pot_Lake_Irrigation)

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
                day_of_year = globals.dateVar['currDate'].timetuple().tm_yday
                if 'Reservoir_releases' in binding:
                    resStorage_maxFracForIrrigation = readnetcdf2('Reservoir_releases', day_of_year,
                                                                useDaily='DOY', value='Fraction of Volume')

                elif self.var.reservoir_releases_excel_option:
                    resStorage_maxFracForIrrigation = globals.inZero.copy()
                    resStorage_maxFracForIrrigationC = np.where(self.var.lakeResStorage_release_ratioC > -1,
                                                                self.var.reservoir_supply[dateVar['doy']-1],
                                                                0.03)
                    np.put(resStorage_maxFracForIrrigation, self.var.decompress_LR, resStorage_maxFracForIrrigationC)
                else:
                    resStorage_maxFracForIrrigation = 0.03 + globals.inZero.copy()

                if self.var.sectorSourceAbstractionFractions:

                    remainNeedPre = pot_Res_Domestic + pot_Res_Livestock + pot_Res_Industry
                    #print('water_demand.py: np.sum(remainNeedPre) with reservoirs', np.sum(remainNeedPre))

                    # remainNeed, command_areas, maxFracForIrrigation, water_conveyance_efficiency        
                    ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment, resStorageTotal_allocC = self.commandAreaOperation(remainNeed = remainNeedPre, command_areas = self.var.reservoir_command_areas ,\
                      maxFracForIrrigation = resStorage_maxFracForIrrigation, water_conveyance_efficiency = self.var.Water_conveyance_efficiency, wwt_only = False)

                    self.var.lakeStorageC -= self.var.reservoirStorageM3C * ResAbstractFactorC
                    self.var.lakeVolumeM3C -= self.var.reservoirStorageM3C * ResAbstractFactorC
                    self.var.lakeResStorageC -= self.var.reservoirStorageM3C * ResAbstractFactorC
                    self.var.reservoirStorageM3C -= self.var.reservoirStorageM3C * ResAbstractFactorC

                    self.var.abstractedLakeReservoirM3C += self.var.reservoirStorageM3C * ResAbstractFactorC
                    np.put(self.var.abstractedLakeReservoirM3, self.var.decompress_LR,
                           self.var.abstractedLakeReservoirM3C)

                    self.var.lakeResStorage = globals.inZero.copy()
                    np.put(self.var.lakeResStorage, self.var.decompress_LR, self.var.lakeResStorageC)

                    metRemainSegment = np.where(demand_Segment > 0,
                                                divideValues(act_bigLakeResAbst_alloc * self.var.Water_conveyance_efficiency,
                                                             demand_Segment), 0)  # by definition <= 1

                    self.var.act_bigLakeResAbst += remainNeedPre * metRemainSegment
                    self.var.act_SurfaceWaterAbstract += remainNeedPre * metRemainSegment

                    self.var.act_ResAbst = remainNeedPre * metRemainSegment

                    self.var.Res_Domestic = np.minimum(self.var.act_ResAbst,
                                                       pot_Res_Domestic)
                    self.var.Res_Livestock = np.minimum(self.var.act_ResAbst - self.var.Res_Domestic,
                                                        pot_Res_Livestock)
                    self.var.Res_Industry = np.minimum(
                        self.var.act_ResAbst - self.var.Res_Domestic - self.var.Res_Livestock,
                        pot_Res_Industry)

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

                ResAbstractFactorC, act_bigLakeResAbst_alloc, demand_Segment, resStorageTotal_allocC = self.commandAreaOperation(remainNeed = remainNeed2, command_areas = self.var.reservoir_command_areas ,\
                    maxFracForIrrigation = resStorage_maxFracForIrrigation, water_conveyance_efficiency = self.var.Water_conveyance_efficiency, wwt_only = False)

                self.var.lakeStorageC -= self.var.reservoirStorageM3C * ResAbstractFactorC
                self.var.lakeVolumeM3C -= self.var.reservoirStorageM3C * ResAbstractFactorC
                self.var.lakeResStorageC -= self.var.reservoirStorageM3C * ResAbstractFactorC
                self.var.reservoirStorageM3C -= self.var.reservoirStorageM3C * ResAbstractFactorC

                self.var.abstractedLakeReservoirM3C += self.var.reservoirStorageM3C * ResAbstractFactorC
                np.put(self.var.abstractedLakeReservoirM3, self.var.decompress_LR,
                       self.var.abstractedLakeReservoirM3C)

                self.var.lakeResStorage = globals.inZero.copy()
                np.put(self.var.lakeResStorage, self.var.decompress_LR, self.var.lakeResStorageC)

                metRemainSegment = np.where(demand_Segment > 0,
                                            divideValues(act_bigLakeResAbst_alloc * self.var.Water_conveyance_efficiency,
                                                         demand_Segment), 0)  # by definition <= 1

                self.var.leakageC_daily = resStorageTotal_allocC * ResAbstractFactorC * (
                        1 - np.compress(self.var.compress_LR, self.var.Water_conveyance_efficiency))

                self.var.leakage = globals.inZero.copy()
                np.put(self.var.leakage, self.var.decompress_LR, self.var.leakageC_daily + self.var.leakage_wwtC_daily)

                # self.var.leakageC += self.var.leakageC_daily
                divleak_canal = divideValues((self.var.leakageC_daily +  self.var.leakage_wwtC_daily) ,self.var.canalsAreaC)
                self.var.leakageCanalsC_M = np.where(self.var.canalsAreaC > 0,divleak_canal, 0)

                # Without this, npareamaximum uses the historical maximum
                self.var.leakageCanals_M = globals.inZero.copy()
                np.put(self.var.leakageCanals_M, self.var.decompress_LR, self.var.leakageCanalsC_M)  # good
                self.var.leakageCanals_M = npareamaximum(self.var.leakageCanals_M,
                                                         self.var.canals)

                self.var.act_bigLakeResAbst += remainNeed2 * metRemainSegment
                self.var.act_SurfaceWaterAbstract += remainNeed2 * metRemainSegment

                self.var.act_ResAbst += remainNeed2 * metRemainSegment

                ## End of using_reservoir_command_areas

                if self.var.sectorSourceAbstractionFractions:
                    self.var.Res_Irrigation = np.minimum(
                        remainNeed2 * metRemainSegment,
                        pot_Res_Irrigation)

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
                # if available storage is too low, no pumping in this cell (defined in transient module)

                self.var.nonFossilGroundwaterAbs = np.where(self.var.groundwater_storage_available > (
                        1 - self.var.availableGWStorageFraction) * self.var.gwstorage_full,
                                                            np.minimum(self.var.groundwater_storage_available,
                                                                       self.var.pot_GroundwaterAbstract), 0)
            else:
                self.var.nonFossilGroundwaterAbs = np.maximum(0., np.minimum(self.var.readAvlStorGroundwater,
                                                                             self.var.pot_GroundwaterAbstract))

            # if limitAbstraction from groundwater is True
            # fossil gwAbstraction and water demand may be reduced
            # variable to reduce/limit groundwater abstraction (> 0 if limitAbstraction = True)

            if self.var.sectorSourceAbstractionFractions:
                # A
                self.var.GW_Domestic = np.minimum(self.var.nonFossilGroundwaterAbs, pot_GW_Domestic)
                self.var.GW_Livestock = np.minimum(self.var.nonFossilGroundwaterAbs - self.var.GW_Domestic,
                                                   pot_GW_Livestock)
                self.var.GW_Industry = np.minimum(
                    self.var.nonFossilGroundwaterAbs - self.var.GW_Domestic - self.var.GW_Livestock,
                    pot_GW_Industry)
                self.var.GW_Irrigation = np.minimum(
                    self.var.nonFossilGroundwaterAbs - self.var.GW_Domestic - self.var.GW_Livestock - self.var.GW_Industry,
                    pot_GW_Irrigation)

                unmet_Domestic = self.var.domesticDemand - self.var.Desal_Domestic - self.var.Channel_Domestic - \
                    self.var.wwt_Domestic - self.var.Lift_Domestic - self.var.Lake_Domestic - self.var.Res_Domestic - self.var.GW_Domestic
                unmet_Livestock = self.var.livestockDemand - self.var.Desal_Livestock - self.var.Channel_Livestock - \
                    self.var.wwt_Livestock - self.var.Lift_Livestock - self.var.Lake_Livestock - self.var.Res_Livestock - self.var.GW_Livestock
                unmet_Industry = self.var.industryDemand - self.var.Desal_Industry - self.var.Channel_Industry - \
                    self.var.wwt_Industry - self.var.Lift_Industry  - self.var.Lake_Industry - self.var.Res_Industry - self.var.GW_Industry
                unmet_Irrigation = self.var.totalIrrDemand - self.var.Desal_Irrigation - self.var.Channel_Irrigation - \
                    self.var.wwt_Irrigation - self.var.Lift_Industry - self.var.Lake_Irrigation - self.var.Res_Irrigation - self.var.GW_Irrigation

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

                # calculate act_ water demand, because irr demand has still demand from previous day included
                # if the demand from previous day is not fulfilled it is taken to the next day and so on
                # if we do not correct we double account each day the demand from previous days
                self.var.act_irrPaddyDemand = np.maximum(0, self.var.irrPaddyDemand - self.var.unmetDemandPaddy)
                self.var.act_irrNonpaddyDemand = np.maximum(0,
                                                            self.var.irrNonpaddyDemand - self.var.unmetDemandNonpaddy)

                # unmet is either pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs or demand - withdrawal
                if self.var.includeIndusDomesDemand:  # all demands are taken into account
                    self.var.unmetDemand = (self.var.totalIrrDemand - self.var.act_irrWithdrawal) + \
                                           (self.var.nonIrrDemand - self.var.act_nonIrrWithdrawal)
                else:  # only irrigation is considered
                    self.var.unmetDemand = (self.var.totalIrrDemand - self.var.act_irrWithdrawal) - \
                                           self.var.act_nonIrrWithdrawal
                self.var.unmetDemandPaddy = self.var.irrPaddyDemand - self.var.act_irrPaddyDemand
                self.var.unmetDemandNonpaddy = self.var.irrNonpaddyDemand - self.var.act_irrNonpaddyDemand


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

                                zoneDemand_sw = npareatotal(unmet_Channel * self.var.cellArea, self.var.allocation_zone) / self.var.cellArea


                            else:
                                # get the demand that still needs to be met

                                #multiply with cellarea [m] -> [m3], otherwise bincount is not correct, divide again by cellarea to get [m] again
                                unmetDemand_sw = np.minimum(self.var.unmetDemand,
                                                            totalDemand * self.var.swAbstractionFraction- self.var.act_SurfaceWaterAbstract)
                                zoneDemand_sw = npareatotal(unmetDemand_sw * self.var.cellArea, self.var.allocation_zone) / self.var.cellArea

                            zone_sf_avail = npareatotal(left_sf_avail * self.var.cellArea, self.var.allocation_zone) / self.var.cellArea

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
                                self.var.Channel_Domestic_fromZone = np.minimum(cell_sf_allocation, pot_Channel_Domestic)
                                self.var.Channel_Domestic += self.var.Channel_Domestic_fromZone

                                self.var.Channel_Livestock_fromZone = np.minimum(
                                    cell_sf_allocation - self.var.Channel_Domestic_fromZone,
                                    pot_Channel_Livestock)
                                self.var.Channel_Livestock += self.var.Channel_Livestock_fromZone

                                self.var.Channel_Industry_fromZone = np.minimum(
                                    cell_sf_allocation - self.var.Channel_Domestic_fromZone -
                                    self.var.Channel_Livestock_fromZone,
                                    pot_Channel_Industry)
                                self.var.Channel_Industry += self.var.Channel_Industry_fromZone

                                self.var.Channel_Irrigation_fromZone = np.minimum(pot_Channel_Irrigation, \
                                    cell_sf_allocation \
                                   - self.var.Channel_Domestic_fromZone \
                                   - self.var.Channel_Livestock_fromZone \
                                   - self.var.Channel_Industry_fromZone)

                                self.var.Channel_Irrigation += self.var.Channel_Irrigation_fromZone

                                # With zonal abstractions, cells can abstract more than their specific demands
                                # In the case that abstractions are greater than demands, this is attributed
                                # to Channel_Other

                                self.var.Channel_Other = cell_sf_allocation \
                                   - self.var.Channel_Domestic_fromZone \
                                   - self.var.Channel_Livestock_fromZone \
                                   - self.var.Channel_Industry_fromZone \
                                    - self.var.Channel_Irrigation_fromZone

                            # new potential groundwater abstraction
                            self.var.pot_GroundwaterAbstract = \
                                np.maximum(0., self.var.pot_GroundwaterAbstract - cell_sf_allocation)

                            left_gw_demand = np.maximum(0., self.var.pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs)
                            left_gw_avail = np.maximum(0., self.var.readAvlStorGroundwater - self.var.nonFossilGroundwaterAbs)

                            zone_gw_avail = npareatotal(left_gw_avail * self.var.cellArea, self.var.allocation_zone) / self.var.cellArea

                            # for groundwater substract demand which is fulfilled by surface zone, calc abstraction and what
                            # is left.
                            zone_gw_demand = npareatotal(left_gw_demand, self.var.allocation_zone)
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

                                self.var.GW_Domestic_fromZone = np.minimum(cell_gw_allocation, pot_GW_Domestic-self.var.GW_Domestic)
                                self.var.GW_Domestic += self.var.GW_Domestic_fromZone.copy()

                                self.var.GW_Livestock_fromZone = np.minimum(
                                    cell_gw_allocation - self.var.GW_Domestic_fromZone,
                                    pot_GW_Livestock - self.var.GW_Livestock)
                                self.var.GW_Livestock += self.var.GW_Livestock_fromZone.copy()

                                self.var.GW_Industry_fromZone = np.minimum(
                                    cell_gw_allocation - self.var.GW_Domestic_fromZone - self.var.GW_Livestock_fromZone,
                                    pot_GW_Industry - self.var.GW_Industry)
                                self.var.GW_Industry += self.var.GW_Industry_fromZone.copy()

                                self.var.GW_Irrigation_fromZone = np.minimum(
                                    cell_gw_allocation - self.var.GW_Domestic_fromZone -
                                    self.var.GW_Livestock_fromZone - self.var.GW_Industry_fromZone,
                                    pot_GW_Irrigation - self.var.GW_Irrigation)
                                self.var.GW_Irrigation += self.var.GW_Irrigation_fromZone.copy()

                                # With zonal abstractions, cells can abstract more than their specific demands
                                # In the case that abstractions are greater than demands, this is attributed
                                # to GW_Other

                                self.var.GW_Other = cell_gw_allocation \
                                                    - self.var.GW_Domestic_fromZone \
                                                    - self.var.GW_Livestock_fromZone \
                                                    - self.var.GW_Industry_fromZone \
                                                    - self.var.GW_Irrigation_fromZone

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

                self.var.waterAbstract = self.var.unmetDemand + self.var.nonFossilGroundwaterAbs + self.var.act_SurfaceWaterAbstract

                self.var.act_irrNonpaddyWithdrawal = self.var.fracVegCover[3] * self.var.irrDemand[3]
                self.var.act_irrPaddyWithdrawal = self.var.fracVegCover[2] * self.var.irrDemand[2]

                self.var.act_irrNonpaddyDemand = self.var.act_irrNonpaddyWithdrawal.copy()
                self.var.act_irrPaddyDemand = self.var.act_irrPaddyWithdrawal.copy()

                # end of limit_abstraction = False
            ## End of limit extraction if, then

            self.var.act_irrConsumption[2] = divideValues(self.var.act_irrPaddyWithdrawal,
                                                          self.var.fracVegCover[2]) * self.var.efficiencyPaddy
            self.var.act_irrConsumption[3] = divideValues(self.var.act_irrNonpaddyWithdrawal,
                                                          self.var.fracVegCover[3]) * self.var.efficiencyNonpaddy

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

                self.var.act_indWithdrawal = frac_industry * self.var.act_nonIrrWithdrawal
                self.var.act_domWithdrawal = frac_domestic * self.var.act_nonIrrWithdrawal
                self.var.act_livWithdrawal = frac_livestock * self.var.act_nonIrrWithdrawal
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
            unmet_div_ww = 1. - np.minimum(1, divideValues(self.var.unmetDemand,
                                                           self.var.act_totalWaterWithdrawal + self.var.unmetDemand))

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
                self.var.wwtEffluentsGenerated_domestic = self.var.returnflowNonIrr.copy() * divideValues(frac_domestic, frac_domestic + frac_industry) # [M3]
                self.var.wwtEffluentsGenerated_industry = self.var.returnflowNonIrr.copy() * divideValues(frac_industry, frac_domestic + frac_industry)
                self.var.wwtEffluentsGenerated = self.var.wwtEffluentsGenerated_domestic + self.var.wwtEffluentsGenerated_industry
            
                self.var.wwtSewerCollection_domestic = np.where(self.var.wwtColArea > 0,
                                                       np.minimum(self.var.wwtEffluentsGenerated_domestic,
                                                                  self.var.wwtEffluentsGenerated_domestic), 0.)
                self.var.wwtSewerCollection_industry = np.where(self.var.wwtColArea > 0,
                                                       np.minimum(self.var.wwtEffluentsGenerated_industry,
                                                                  self.var.wwtEffluentsGenerated_industry), 0.) 
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

                self.var.act_irrWithdrawalSW_month += npareatotal(act_irrWithdrawalSW * self.var.cellArea,
                                                                  self.var.adminSegments)

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

                    self.var.ratio_irrWithdrawalSW_month \
                        = self.var.act_irrWithdrawalSW_month / self.var.irrWithdrawalSW_max

            if 'adminSegments' in binding and checkOption('limitAbstraction'):
                self.var.act_irrWithdrawalGW_month += npareatotal(act_irrWithdrawalGW * self.var.cellArea,
                                                                  self.var.adminSegments)
                if 'irrigation_agent_GW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                    self.var.gwAbstractionFraction_Irrigation = np.where(
                        self.var.act_irrWithdrawalGW_month > self.var.irrWithdrawalGW_max, 0,
                        self.var.gwAbstractionFraction_Irrigation)

                    self.var.ratio_irrWithdrawalGW_month \
                        = self.var.act_irrWithdrawalGW_month / self.var.irrWithdrawalGW_max

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


