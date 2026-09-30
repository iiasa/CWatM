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
    - Unit conversion factors (m to m3 and m3 to m)
    - Precipitation and evaporation conversion parameters
    - Mathematical constants and frequently used expressions

    Only used during model initialization phase.










    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    M3toM                                Array         Coefficient to change units from m3 to m (= InvCellArea)                1 m-2
    DtSec                                Number        number of seconds per timestep (default = 86400)                        s    
    twothird                             Number        2/3 (exponent)                                                          --   
    MtoM3                                Array         Coefficient to change units from m to m3 (= cellArea)                   m2   
    InvDtSec                             Number        inverse of seconds per timestep (default 1/86400)                       1 s-1
    InvCellArea                          Array         Inverse of cell area of each simulated mesh                             1 m-2
    DtDay                                Number        timestep as fraction of a day (daily timestep = 1)                      --   
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
        - Unit conversion factors (m to m3, m3 to m)
        - Precipitation and evaporation conversion coefficients
        - Mathematical constants (e.g., 2/3 power for interception calculations)

        Grid size handling:
        - User-defined: Reads cell area from external map files
        - Default: Derives from equal-area projection assuming square cells

        All conversion factors are established to maintain unit consistency
        throughout hydrological calculations.
        """

        if checkOption('gridSizeUserDefined'):
            # cell area [m2] from a map: needed if it cannot be derived from the map attributes
            # (e.g. lat/lon maps or non-equal-area projections). The size may vary across the map.
            self.var.cellArea = loadmap('CellArea')
            projection['crs'] = loadcrs('CellArea')

        else:
            # Default: cell area [m2] derived from the map attributes. Requirements:
            # - Maps are in some equal-area projection
            # - Length units meters
            # - All grid cells have the same size (square)
            # lat/lon maps (cell size and corner coordinates in degree) -> cell ** 2 would be wrong by ~1e10
            if maskmapAttr['cell'] <= 5.0 and abs(maskmapAttr['x']) <= 360.0 and abs(maskmapAttr['y']) <= 90.0:
                msg = "Error 133: the maps seem to be in lat/lon (cell size: " + str(maskmapAttr['cell']) + \
                      ", corner: " + str(maskmapAttr['x']) + ", " + str(maskmapAttr['y']) + ")\n" \
                      "The cell area cannot be derived from a cell size in degree.\n" \
                      "Set gridSizeUserDefined = True in [OPTIONS] and give a map of the cell area in m2 with CellArea\n"
                raise CWATMError(msg)
            self.var.cellArea = np.full(maskinfo['mapC'], maskmapAttr['cell'] ** 2)

        # -----------------------------------------------------------------
        # Miscellaneous repeatedly used expressions for computational efficiency

        # Inverse of cell area [1/m2]
        self.var.InvCellArea = 1.0 / self.var.cellArea

        # Time step [s] and as fraction of a day (daily time step: DtDay = 1)
        # (used to convert rates per day into an amount per time step)
        self.var.DtSec = 86400.0
        self.var.DtDay = self.var.DtSec / 86400
        # Inverse of time step [1/s]
        self.var.InvDtSec = 1 / self.var.DtSec

        # Multiplier to convert water depths in m to cubic metres (= cellArea)
        self.var.MtoM3 = self.var.cellArea
        # Multiplier to convert from cubic metres to m water slice (= InvCellArea)
        self.var.M3toM = self.var.InvCellArea

        # conversion factors of the meteo input (setting names are spelled 'coversion')
        self.var.con_precipitation = loadmap('precipitation_coversion')
        self.var.con_e = loadmap('evaporation_coversion')

        self.var.twothird = 2.0 / 3.0
