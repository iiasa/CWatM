# -------------------------------------------------------------------------
# Name:        MiscInitial
# Purpose: Miscellaneous initialization module for basic model parameters and conversions.
# Sets up unit conversions, spatial parameters, and fundamental model constants.
# Handles coordinate transformations and basic geometric calculations.
#
# Author:      PB
# Created:     13.07.2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *

class miscInitial(object):
    """
    Miscellaneous initialization module for basic model parameters and conversions.
    
    Establishes fundamental model parameters including grid cell characteristics,
    temporal parameters, unit conversion factors, and commonly used mathematical
    expressions that are repeatedly accessed throughout model execution.
    
    Attributes
    ----------
    var : object
        Reference to model variables object containing state variables
    model : object
        Reference to the main CWatM model instance
        
    Notes
    -----
    This module handles essential initialization tasks:
    - Grid cell area determination (user-defined or derived from projection)
    - Time step definitions and conversion factors
    - Unit conversion factors (mm to m, mÂ³ to m, etc.)
    - Precipitation and evaporation conversion parameters
    - Mathematical constants and frequently used expressions
    
    Only used during model initialization phase.

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    M3toM                                Array         Coefficient to change units                                             --   
    DtSec                                Array         number of seconds per timestep (default = 86400)                        s    
    twothird                             Number        2025-03-02 00:00:00                                                     --   
    MtoM3                                Array         Coefficient to change units                                             --   
    InvDtSec                             Array         inversere of seconds per timestep (default 1/86400)                     1/s  
    InvCellArea                          Array         Inverse of cell area of each simulated mesh                             1/m2 
    DtDay                                Array         seconds in a timestep (default=86400)                                   s    
    InvDtDay                             Array         inverse seconds in a timestep (default=86400)                           1/s  
    MMtoM                                Number        Coefficient to change units                                             --   
    MtoMM                                Number        Coefficient to change units                                             --   
    con_precipitation                    Array         conversion factor for precipitation                                     --   
    con_e                                Array         conversion factor for evaporation                                       --   
    cellArea                             Array         Area of cell                                                            m2   
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize miscellaneous parameters module.
        
        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.var = model.var
        self.model = model


    def initial(self):
        """
        Initialize basic model parameters and conversion factors.
        
        Sets up fundamental model parameters including grid cell characteristics,
        temporal parameters, unit conversions, and mathematical constants required
        throughout model execution.
        
        Notes
        -----
        Initialization includes:
        - Grid cell area calculation (user-defined maps or equal-area projection)
        - Time step parameters (daily time step in seconds and fractions)
        - Unit conversion factors (mm/m, m/mÂ³, inverse relationships)
        - Precipitation and evaporation conversion coefficients
        - Mathematical constants (e.g., 2/3 power for interception calculations)
        
        Grid size handling:
        - User-defined: Reads cell area from external map files
        - Default: Derives from equal-area projection assuming square cells
        
        All conversion factors are established to maintain unit consistency
        throughout hydrological calculations.
        """

        if checkOption('gridSizeUserDefined'):

            # <lfoption name="gridSizeUserDefined" choice="1" default="0">
            # If option gridsizeUserDefined is activated, users can specify grid size properties
            # in separate maps. This is useful whenever this information cannot be derived from
            # the location attributes of the base maps (e.g. lat/lon systems or non-equal-area
            # projections)
            # Limitation: always assumes square grid cells (not rectangles!). Size of grid cells
            # may vary across map though

            # Length of pixel [m]
            # NOT needed only in routing

            # Area of pixel [m2]
            self.var.cellArea = loadmap('CellArea')


        else:
            # Default behaviour: grid size is derived from location attributes of
            # base maps. Requirements:
            # - Maps are in some equal-area projection
            # - Length units meters
            # - All grid cells have the same size

            # Area of pixel [m2]
            self.var.cellArea = np.empty(maskinfo['mapC'])
            self.var.cellArea.fill(maskmapAttr['cell'] ** 2)

            # self.var.PixelArea = spatial(self.var.PixelArea)
            # Convert to spatial expresion (otherwise this variable cannnot be
            # used in areatotal function)

        # -----------------------------------------------------------------
        # Miscellaneous repeatedly used expressions for computational efficiency

        # self.var.InvCellLength = 1.0 / self.var.cellLength
        self.var.InvCellArea = 1.0 / self.var.cellArea
        # Inverse of pixel size [1/m]
        self.var.DtSec = 86400.0
        self.var.DtDay = self.var.DtSec / 86400
        # Time step, expressed as fraction of day (used to convert
        # rate variables that are expressed as a quantity per day to
        # into an amount per time step)
        self.var.InvDtSec = 1 / self.var.DtSec
        # Inverse of time step [1/s]
        self.var.InvDtDay = 1 / self.var.DtDay
        # Inverse of time step [1/d]

        # self.var.DtSecChannel = loadmap('DtSecChannel')
        # Sub time step used for kinematic wave channel routing [seconds]
        # within the model,the smallest out of DtSecChannel and DtSec is used

        self.var.MMtoM = 0.001
        # Multiplier to convert water depths in mm to meters
        self.var.MtoMM = 1000
        # Multiplier to convert water depths in meters to mm
        self.var.MtoM3 = 1.0 * self.var.cellArea
        # Multiplier to convert water depths in m to cubic metres
        self.var.M3toM = 1 / self.var.MtoM3
        # Multiplier to convert from cubic metres to m water slice

        self.var.con_precipitation = loadmap('precipitation_coversion')

        self.var.con_e = loadmap('evaporation_coversion')

        self.var.twothird = 2.0 / 3.0








