# -------------------------------------------------------------------------
# Name:        Runoff concentration module
# Purpose:     this is the part between runoff generation and routing
#              for each gridcell and for each land cover class the generated runoff is concentrated 
#              at a corner of a gridcell
#              this concentration needs some lag-time (and peak time) and leads to diffusion
#              lag-time/ peak time is calculated using slope, length and land cover class
#              diffusion is calculated using a triangular-weighting-function
# Author:      PB
# Created:     16/12/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


class runoff_concentration(object):
    """
    Runoff concentration module for temporal flow concentration within grid cells.
    
    Handles the intermediate process between runoff generation and channel routing,
    concentrating runoff from different land cover classes within each grid cell
    using lag-time and diffusion processes based on topographic and land cover
    characteristics.
    
    Attributes
    ----------
    var : object
        Reference to model variables object containing state variables
    model : object
        Reference to the main CWatM model instance
        
    Notes
    -----
    The concentration process accounts for:
    - Variable lag times based on slope, length, and land cover
    - Temporal diffusion using triangular weighting functions
    - Different peak times for surface runoff, interflow, and baseflow
    - Land cover-specific concentration parameters
    
    Mathematical formulation:
    Q(t) = sum_{i=0}^{max} c(i) * Q_source(t - i + 1)
    
    where c(i) represents the triangular weighting coefficients:
    c(i) = integral from (i-1) to i of [2/max - (u - max/2) * 4/max^2] du
    
    References
    ----------
    Based on triangular weighting function concepts for temporal concentration












    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    load_initial                         Flag          Settings initLoad holds initial conditions for variables                bool 
    leakageIntoRunoff                    Array         Canal leakage leading to runoff                                         m    
    fracGlacierCover                     Array         Fraction of glacier cover in a grid cell                                %    
    includeGlaciers                      Flag          Include glaciers                                                        bool 
    GlacierMelt                          Array         melt from glacier                                                       m    
    GlacierRain                          Array         rain on glacier                                                         m    
    coverTypes                           List          land cover types - forest - grassland - irrPaddy - irrNonPaddy - water  --   
    runoff_m3                            Array         runoff of the grid cell in m3 (plus glacier melt and rain)              m3   
    sum_directRunoff                     Array         direct runoff from surface  (sum over all land cover types)             m    
    sum_interflow                        Array         sum of iterflow from all land cover types                               m    
    runoff_peak                          List          peak time of runoff for each land use class                             day  
    tpeak_interflow                      Array         peak time of interflow                                                  day  
    tpeak_baseflow                       Array         peak time of baseflow                                                   day  
    tpeak_glaciers                       Array         peak time of glacier (not used yet)                                     day  
    maxtime_runoff_conc                  Int           maximum number of time steps till all flow is at the outlet (<= 10)     --   
    runoff_conc                          Array         runoff after concentration - triangular-weighting method                m    
    runoffConc_weights                   List          triangular weights [time step, cell] of 6 land covers, interflow, base  --   
    runoffConc_buffer                    Array         buffer for weight * flow (runoff concentration)                         m    
    runoffConc_ones                      Array         fraction 1 for lib2.runoffConc (only if weights are not precomputed)    --   
    gridcell_storage                     Array         storage of water due to runoff concentration                            m    
    sum_landSurfaceRunoff                Array         Runoff concentration above the soil more interflow including all landc  m    
    landSurfaceRunoff                    Array         Runoff concentration above the soil more interflow                      m    
    runoff                               Array         Total runoff from surface, interflow and groundwater                    m    
    directRunoff                         Array         Simulated surface runoff                                                m    
    interflow                            Array         Simulated flow reaching runoff instead of groundwater                   m    
    baseflow                             Array         simulated baseflow (= groundwater discharge to river)                   m    
    fracVegCover                         Array         Fraction of specific land covers (0=forest, 1=grasslands, etc.)         %    
    cellArea                             Array         Area of cell                                                            m2   
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize runoff concentration module.
        
        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initialize runoff concentration parameters and lag time calculations.
        
        Sets up concentration time parameters for different runoff components
        and calculates land cover-specific lag times based on topographic
        characteristics and flow path properties.
        
        Notes
        -----
        Peak times [days = time steps] are limited to 0.5 ... upper limit:
        - Surface runoff: 3 (water: always 0.5)
        - Interflow: 4
        - Baseflow: 5
        maxtime_runoff_conc = ceil(2 * largest peak time) <= 10 time steps

        Concentration time calculation (NRCS TR55 upland method) considers:
        - Grid cell slope (fixed flow length of 50 km)
        - Land cover-specific peak time factors (settings: <coverType>_runoff_peaktime)
        - Calibration factor runoffConc_factor
        - Triangular weighting function parameters
        
        The lag times determine the temporal distribution of runoff
        concentration for each land cover type within grid cells.
        """

        if checkOption('includeRunoffConcentration'):

            # --- Topography -----------------------------------------------------
            tanslope = loadmap('tanslope')
            # setting slope >= 0.00001 to prevent 0 value
            tanslope = np.maximum(tanslope, 0.00001)

            # Natural   Resources   Conservation Service TR55 - upland method
            # T lag = 0.6 T conc = 0.6 * Flowlength / (60* Velocity); V = K * Slope^0.5
            # K paved = 6, k forest = 0.3, grass  = 0.6

            # time to peak in days
            # (fixed flow length of 50 km for every cell, independent of the cell size)
            tpeak = 0.5 + 0.6 * 50000.0 / (1440.0 * 60 * np.power(tanslope, 0.5))

            #     /\   peak time for concentrated runoff
            #   /   \
            #  ---*--

            # for calibration a general runoff concentration factor is loaded
            runoffConc_factor = loadmap('runoffConc_factor')

            # peak time [days] for each land cover type (coverTypes from landcoverType.initial)
            self.var.runoff_peak = []
            for coverType in self.var.coverTypes:
                tpeak_cover = runoffConc_factor * tpeak * loadmap(coverType + "_runoff_peaktime")
                tpeak_cover = np.minimum(np.maximum(tpeak_cover, 0.5), 3.0)
                if coverType == "water":
                    # array: lib2.runoffConc needs an array for the peak time
                    tpeak_cover = globals.inZero + 0.5
                self.var.runoff_peak.append(tpeak_cover)

            self.var.tpeak_interflow = runoffConc_factor * tpeak * loadmap("interflow_runoff_peaktime")
            self.var.tpeak_interflow = np.minimum(np.maximum(self.var.tpeak_interflow, 0.5), 4.0)
            self.var.tpeak_baseflow = runoffConc_factor * tpeak * loadmap("baseflow_runoff_peaktime")
            self.var.tpeak_baseflow = np.minimum(np.maximum(self.var.tpeak_baseflow, 0.5), 5.0)

            if self.var.includeGlaciers:
                # not used yet: glacier melt and rain are not concentrated (added as m3 in dynamic)
                self.var.tpeak_glaciers = runoffConc_factor * tpeak * loadmap("glaciers_runoff_peaktime")
                self.var.tpeak_glaciers = np.minimum(np.maximum(self.var.tpeak_glaciers, 0.5), 3.0)

            #     /\   maximal timestep for concentrated runoff
            #   /   \
            #  ------*
            # all flow is released within 2 * peak time -> maximum over all concentrated components
            # (land covers, interflow, baseflow), otherwise the tail of the triangle would be lost
            maxpeak = max(np.amax(np.maximum.reduce(self.var.runoff_peak)),
                          np.amax(self.var.tpeak_interflow), np.amax(self.var.tpeak_baseflow))
            self.var.maxtime_runoff_conc = int(np.ceil(2 * maxpeak))

            # array with concentrated runoff: always 10 time steps (as in the initial condition file)
            # peak times <= 5 -> maxtime_runoff_conc <= 10
            self.var.runoff_conc = np.tile(globals.inZero, (10, 1))
            for i in range(self.var.maxtime_runoff_conc):
                self.var.runoff_conc[i] = self.var.load_initial("runoff_conc", number=i + 1)

            # triangular weights of each component (6 land covers, interflow, baseflow) are static
            # -> calculated once here (numpy) instead of every time step in lib2.runoffConc
            # memory: 8 * maxtime * cells * 8 bytes (e.g. 10 time steps, 1 Mio cells: 640 MB)
            # -> only up to 500 MB, otherwise the C++ library is used in dynamic
            peaks = self.var.runoff_peak + [self.var.tpeak_interflow, self.var.tpeak_baseflow]
            nbytes = len(peaks) * self.var.maxtime_runoff_conc * globals.inZero.size * 8
            self.var.runoffConc_weights = None
            if nbytes <= 5.e8:
                self.var.runoffConc_weights = [self.triangle_weights(p + globals.inZero, self.var.maxtime_runoff_conc)
                                               for p in peaks]
                # buffer for weight * flow (no new array every time step)
                self.var.runoffConc_buffer = np.empty((self.var.maxtime_runoff_conc, globals.inZero.size))
            else:
                # arrays for lib2.runoffConc: fraction 1 for interflow and baseflow
                self.var.runoffConc_ones = globals.inZero + 1

            # storage = water still waiting: row 0 of a warm start is the runoff of the last time step
            # of the previous run (already released) -> not part of the storage
            self.var.gridcell_storage = np.sum(self.var.runoff_conc[1:], 0)

        else:
            self.var.gridcell_storage = 0


    @staticmethod
    def triangle_weights(peak, maxlag):
        """
        Triangular weights of the runoff concentration for each time step.

        Same calculation (and order of operations) as lib2.runoffConc in routing_reservoirs/t6.cpp:
        the area of the triangle (base 2 * peak, area 1) up to the end of each time step,
        minus the area up to the time step before. Everything left after 2 * peak - 1 is
        put into that time step, so the weights of a cell sum up to 1.

        Parameters
        ----------
        peak : numpy.ndarray
            peak time [time steps] of each cell
        maxlag : int
            number of time steps (maxtime_runoff_conc)

        Returns
        -------
        numpy.ndarray
            weights [maxlag, cells]
        """
        div = 2 * (peak * peak)
        weights = np.empty((maxlag, peak.size))
        areaFractionOld = np.zeros(peak.size)
        for lag in range(maxlag):
            lag1 = float(lag + 1)
            lag1alt = 2 * peak - lag1
            areaFractionSum = np.where(lag1 > peak, 1 - (lag1alt * lag1alt) / div, (lag1 * lag1) / div)
            areaFractionSum = np.where(lag1alt < 1, 1.0, areaFractionSum)
            weights[lag] = areaFractionSum - areaFractionOld
            areaFractionOld = areaFractionSum
        return weights

    # --------------------------------------------------------------------------

    def dynamic(self):
        """
        Calculate runoff concentration for current time step.
        
        Applies temporal concentration to runoff components from different
        land cover types, distributing flow over time using pre-calculated
        lag times and triangular weighting functions.
        
        Notes
        -----
        Processing includes:
        - Temporal distribution of surface runoff, interflow, and baseflow
        - Application of triangular weighting functions
        - Integration of concentrated flows from all land cover types
        - Update of flow concentration arrays for routing
        
        The concentration process smooths the temporal distribution of
        runoff, representing the natural lag between runoff generation
        and arrival at grid cell outlets.

        The triangular weighting of each component is calculated in the C++ library
        (lib2.runoffConc in routing_reservoirs/t6.cpp) for computational speed.
        """

        self.var.sum_landSurfaceRunoff = globals.inZero.copy()
        self.var.sum_directRunoff = globals.inZero.copy()

        for No in range(6):
            self.var.sum_directRunoff += self.var.fracVegCover[No] * self.var.directRunoff[No]
            self.var.landSurfaceRunoff[No] = self.var.directRunoff[No] + self.var.interflow[No]
            self.var.sum_landSurfaceRunoff += self.var.fracVegCover[No] * self.var.landSurfaceRunoff[No]

        #PB 06/26: correction if glaciers - runoff should be not reduced in unit m , but later for m3
        # runoff [m] is calculated for the total area
        #self.var.sum_directRunoff = self.var.sum_directRunoff + (self.var.directRunoff[0] * self.var.fracGlacierCover)
        #self.var.sum_landSurfaceRunoff = (self.var.sum_landSurfaceRunoff +
        #                ((self.var.directRunoff[0] + self.var.interflow[0]) * self.var.fracGlacierCover))

        self.var.runoff = self.var.sum_landSurfaceRunoff + self.var.baseflow + self.var.leakageIntoRunoff

        if checkOption('includeRunoffConcentration'):
            # -------------------------------------------------------
            # runoff concentration: triangular-weighting method

            # shifting array by one time step (only the used rows, in place): row 0 of the last time step
            # was released as runoff, the last used row gets 0
            m = self.var.maxtime_runoff_conc
            self.var.runoff_conc[:m - 1] = self.var.runoff_conc[1:m]
            self.var.runoff_conc[m - 1] = 0.

            W = self.var.runoffConc_weights
            if W is not None:
                # precomputed weights (initial): same order of additions as with lib2.runoffConc
                conc = self.var.runoff_conc[:m]
                buf = self.var.runoffConc_buffer
                # surface runoff of each land cover type (land cover types with fraction 0 add nothing)
                for No in range(6):
                    if np.any(self.var.fracVegCover[No]):
                        conc += np.multiply(W[No], self.var.fracVegCover[No] * self.var.directRunoff[No], out=buf)
                # interflow and baseflow time of concentration
                conc += np.multiply(W[6], self.var.sum_interflow, out=buf)
                conc += np.multiply(W[7], self.var.baseflow, out=buf)
            else:
                # surface runoff of each land cover type
                for No in range(6):
                    if np.any(self.var.fracVegCover[No]):
                        lib2.runoffConc(self.var.runoff_conc, self.var.runoff_peak[No], self.var.fracVegCover[No],
                                        self.var.directRunoff[No], m, maskinfo['mapC'][0])

                # interflow time of concentration
                lib2.runoffConc(self.var.runoff_conc, self.var.tpeak_interflow, self.var.runoffConc_ones,
                                self.var.sum_interflow, m, maskinfo['mapC'][0])

                # baseflow time of concentration (lib2 needs float64)
                lib2.runoffConc(self.var.runoff_conc, self.var.tpeak_baseflow, self.var.runoffConc_ones,
                                np.asarray(self.var.baseflow, dtype=np.float64), m, maskinfo['mapC'][0])

            # canal leakage into runoff (with MODFLOW): no concentration time, released in this time step
            # (it is part of self.var.runoff and of gridcell_storage, so it has to be in runoff_conc too)
            self.var.runoff_conc[0] += self.var.leakageIntoRunoff

            # storage in each grid cell (unit: m): total runoff - runoff for the timestep
            self.var.gridcell_storage = self.var.gridcell_storage - self.var.runoff_conc[0] + self.var.runoff
            self.var.runoff = self.var.runoff_conc[0].copy()

        # multiply by cellarea -> from m to m3
        self.var.runoff_m3 = self.var.runoff * self.var.cellArea

        # glacier melt and rain as m3
        if self.var.includeGlaciers:
            self.var.runoff_m3 = self.var.runoff_m3 * (1-self.var.fracGlacierCover) + self.var.GlacierMelt + self.var.GlacierRain
