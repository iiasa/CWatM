# -------------------------------------------------------------------------
# Name: CWATM Initial
# Purpose: Comprehensive model initialization handling all hydrological module setup.
# Manages spatial domain configuration, parameter loading, and initial conditions.
# Coordinates sequential initialization of all hydrological processes in proper order.
#
# Author:      PB
#
# Created:     16/05/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import glob
import os

# Local imports
from cwatm.hydrological_modules.miscInitial import miscInitial
from cwatm.hydrological_modules.initcondition import initcondition
from cwatm.hydrological_modules.readmeteo import readmeteo
from cwatm.hydrological_modules.evaporationPot import evaporationPot
from cwatm.hydrological_modules.inflow import inflow
from cwatm.hydrological_modules.snow_frost import snow_frost
from cwatm.hydrological_modules.soil import soil
from cwatm.hydrological_modules.landcoverType import landcoverType
from cwatm.hydrological_modules.sealed_water import sealed_water
from cwatm.hydrological_modules.evaporation import evaporation
from cwatm.hydrological_modules.groundwater import groundwater
from cwatm.hydrological_modules.groundwater_modflow.transient import groundwater_modflow
from cwatm.hydrological_modules.water_demand.water_demand import water_demand
from cwatm.hydrological_modules.water_demand.wastewater import waterdemand_wastewater as wastewater
from cwatm.hydrological_modules.capillarRise import capillarRise
from cwatm.hydrological_modules.interception import interception
from cwatm.hydrological_modules.runoff_concentration import runoff_concentration
from cwatm.hydrological_modules.lakes_res_small import lakes_res_small
from cwatm.hydrological_modules.environflow import environflow
from cwatm.hydrological_modules.routing_reservoirs.routing_kinematic import routing_kinematic
from cwatm.hydrological_modules.lakes_reservoirs import lakes_reservoirs
from cwatm.hydrological_modules.waterquality1 import waterquality1
from cwatm.management_modules.output import *
from cwatm.management_modules.data_handling import *


class Variables:
    """
    Container class for CWatM variable storage and initial condition loading.
    
    This class provides methods for loading initial hydrological conditions
    either from settings files or netCDF initialization files.
    
    Attributes
    ----------
    initmap : dict
        Dictionary storing initial condition maps during calibration mode
    loadInit : bool
        Flag indicating whether to load initial conditions from netCDF files
    initLoadFile : str
        Path to the initial condition netCDF file
    """
    
    def load_initial(self, name, default=0.0, number=None):
        """
        Load initial hydrological conditions for model state variables.
        
        First checks if the initial value is provided in the settings file.
        If not available, loads from the initialization netCDF file. This method
        supports both single values and multi-layer variables (e.g., soil layers,
        snow layers, runoff concentration layers).
        
        Parameters
        ----------
        name : str
            Name of the initial condition variable to load
        default : float, optional
            Default value to use if no initial condition is found (default: 0.0)
        number : int, optional
            Layer number for multi-layer variables (e.g., soil layers, snow layers)
            When provided, appended to variable name for identification
            
        Returns
        -------
        numpy.ndarray or float
            Spatial map array or scalar value of the initial condition
            
        Notes
        -----
        During calibration mode (Flags['calib']), loaded initial maps are stored
        in the initmap dictionary for potential reuse across calibration runs.
        Multi-layer variables are identified by appending the layer number to
        the base variable name.
        """

        if number is not None:
            name = name + str(number)

        if self.loadInit:
            map = readnetcdfInitial(self.initLoadFile, name)
            if Flags['calib']:
                self.initmap[name] = map
            return map
        else:
            return default

class Config:
    """
    Configuration container class for CWatM model settings.
    
    This class serves as a container for model configuration parameters
    and settings that are passed between different model components.
    Currently implemented as a simple namespace for dynamic attribute assignment.
    
    Notes
    -----
    This class is used to store configuration parameters that need to be
    accessible across different hydrological modules during model initialization
    and execution.
    """
    pass


class CWATModel_ini(DynamicModel):
    """
    CWatM model initialization class for hydrological system setup.
    
    This class handles the complete initialization of the CWatM hydrological model,
    including loading of input data, setting up hydrological modules, configuring
    the spatial domain, and preparing all model state variables for simulation.
    
    The initialization process includes:
    - Spatial domain definition (mask map, coordinate system)
    - Hydrological module instantiation and initialization
    - Initial condition loading for all state variables
    - Water demand and supply system setup
    - Routing and water body initialization
    - Output system configuration
    
    Attributes
    ----------
    var : Variables
        Container for model state variables and parameters
    conf : Config  
        Container for model configuration settings
    MaskMap : numpy.ndarray
        Spatial mask defining the model domain
    output_module : outputTssMap
        Module handling time series and map outputs
    misc_module : miscInitial
        Module for miscellaneous initialization tasks
    init_module : initcondition
        Module for loading initial conditions
    readmeteo_module : readmeteo
        Module for meteorological data reading
    environflow_module : environflow
        Module for environmental flow calculations
    evaporationPot_module : evaporationPot
        Module for potential evapotranspiration
    inflow_module : inflow
        Module for external inflow handling
    snowfrost_module : snow_frost
        Module for snow and frost processes
    soil_module : soil
        Module for soil water processes
    landcoverType_module : landcoverType
        Module for land cover and land use
    evaporation_module : evaporation
        Module for actual evapotranspiration
    groundwater_module : groundwater
        Module for groundwater processes
    groundwater_modflow_module : groundwater_modflow
        Module for MODFLOW coupling (advanced groundwater)
    waterdemand_module : water_demand
        Module for water demand calculations
    wastewater_module : wastewater
        Module for wastewater treatment
    capillarRise_module : capillarRise
        Module for capillary rise processes
    interception_module : interception
        Module for rainfall interception
    sealed_water_module : sealed_water
        Module for sealed/impervious surface processes
    runoff_concentration_module : runoff_concentration
        Module for runoff concentration and routing
    lakes_res_small_module : lakes_res_small
        Module for small lakes and reservoirs
    routing_kinematic_module : routing_kinematic
        Module for kinematic wave routing
    lakes_reservoirs_module : lakes_reservoirs
        Module for large lakes and reservoirs
    waterquality1 : waterquality1
        Module for water quality calculations
        
    Notes
    -----
    The initialization order is critical as some modules depend on variables
    or parameters set by previous modules. Groundwater initialization occurs
    before meteorological reading to check for steady-state conditions.
    MODFLOW coupling is activated when 'modflow_coupling' is True in settings.

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    modflow                              Flag          True if modflow_coupling = True in settings file                        bool 
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self):
        """
        Initialize the CWatM model with complete hydrological system setup.
        
        Performs comprehensive model initialization including spatial domain
        definition, hydrological module instantiation, and initial condition
        loading. Sets up the complete modeling framework for hydrological
        simulation with all necessary components.
        
        The initialization sequence includes:
        1. Base model initialization and variable containers
        2. Output system setup
        3. Hydrological module instantiation
        4. Metadata reading for netCDF outputs
        5. MODFLOW coupling detection
        6. Spatial domain setup (mask map)
        7. Sequential module initialization in dependency order
        
        Notes
        -----
        If the 'maskmap' flag is set, only the mask map is loaded and stored
        in dateVar['maskmap'] for GUI applications, then returns early.
        
        The module initialization order is critical:
        - Miscellaneous and initial conditions first
        - Meteorological and inflow setup
        - Potential evapotranspiration
        - Snow and soil processes
        - Groundwater (before meteorology for steady-state checks)
        - Land cover and actual evapotranspiration
        - Runoff concentration and small water bodies
        - Routing and large water bodies
        - Water demand and environmental flows
        - Output system and water quality
        
        MODFLOW coupling is automatically detected from settings and used
        instead of standard groundwater module when available and not in
        calibration mode.
        """

        DynamicModel.__init__(self)

        self.var = Variables()
        self.conf = Config()

        # ----------------------------------------
        # include output of tss and maps
        self.output_module = outputTssMap(self)

        # include all the hydrological modules
        self.misc_module = miscInitial(self)
        self.init_module = initcondition(self)
        self.readmeteo_module = readmeteo(self)
        self.environflow_module = environflow(self)
        self.evaporationPot_module = evaporationPot(self)
        self.inflow_module = inflow(self)
        self.snowfrost_module = snow_frost(self)
        self.soil_module = soil(self)
        self.landcoverType_module = landcoverType(self)
        self.evaporation_module = evaporation(self)
        self.groundwater_module = groundwater(self)
        self.groundwater_modflow_module = groundwater_modflow(self)
        self.waterdemand_module = water_demand(self)
        self.wastewater_module = wastewater(self)
        self.capillarRise_module = capillarRise(self)
        self.interception_module = interception(self)
        self.sealed_water_module = sealed_water(self)
        self.runoff_concentration_module = runoff_concentration(self)
        self.lakes_res_small_module = lakes_res_small(self)
        self.routing_kinematic_module = routing_kinematic(self)
        self.lakes_reservoirs_module = lakes_reservoirs(self)
        self.waterquality1 = waterquality1(self)


        # ----------------------------------------

        # reading of the metainformation of variables to put into output netcdfs
        metaNetCDF()

        # test if ModFlow coupling is used as defined in settings file
        self.var.modflow = checkOption('modflow_coupling',True)

        # stop run after snow calcualtion -> for snow calibration
        self.var.stopaftersnow = checkOption('stopaftersnow',True)

        # if GUI calls to check the maskmap - using datevar for transporting
        if Flags['maskmap']:
            dateVar['maskmap'] = loadsetclone(self, 'MaskMap')
            return

        # MaskMap: the maskmap is flexible e.g. col,row,x1,y1  or x1,x2,y1,y2
        # set the maskmap
        self.MaskMap = loadsetclone(self, 'MaskMap')

        # run intial misc to get all global variables
        self.misc_module.initial()
        self.init_module.initial()

        self.readmeteo_module.initial()
        self.inflow_module.initial()

        self.evaporationPot_module.initial()
        self.soil_module.initial()

        # groundwater before meteo, bc it checks steady state
        if self.var.modflow and not Flags['calib']:
            self.groundwater_modflow_module.initial()
        else:
            self.groundwater_module.initial()

        # routing must be before output and snow behind
        self.routing_kinematic_module.initial()
        self.output_module.initial()
        self.snowfrost_module.initial()

        self.landcoverType_module.initial()
        self.evaporation_module.initial()

        self.runoff_concentration_module.initial()
        self.lakes_res_small_module.initial()

        if checkOption('includeWaterBodies'):
            self.lakes_reservoirs_module.initWaterbodies()
            self.lakes_reservoirs_module.initial_lakes()
            self.lakes_reservoirs_module.initial_reservoirs()

        self.waterdemand_module.initial()


        self.environflow_module.initial()
        self.waterquality1.initial()


