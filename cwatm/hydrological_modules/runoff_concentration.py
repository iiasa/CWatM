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
    c(i) = integral from (i-1) to i of [2/max - |u - max/2| * 4/maxÂ²] du
    
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
    includeOnlyGlaciersMelt              Flag          Include only glacier melt but not rain on glacier                       bool 
    coverTypes                           Array         land cover types - forest - grassland - irrPaddy - irrNonPaddy - water  --   
    runoff                               Array         Total runoff from surface, interflow and groundwater                    m    
    sum_interflow                        Array         sum of iterflow from all land cover types                               m    
    GlacierMelt                          Array         melt from glacier                                                       m    
    GlacierRain                          Array         rain on glacier                                                         m    
    runoff_peak                          Array         peak time of runoff in seconds for each land use class                  s    
    tpeak_interflow                      Array         peak time of interflow                                                  s    
    tpeak_baseflow                       Array         peak time of baseflow                                                   s    
    tpeak_glaciers                       Array         peak time of glacier                                                    s    
    maxtime_runoff_conc                  Array         maximum time till all flow is at the outlet                             s    
    runoff_conc                          Array         runoff after concentration - triangular-weighting method                m    
    gridcell_storage                     Array         storage of water due to runoff concentration                            m    
    sum_landSurfaceRunoff                Array         Runoff concentration above the soil more interflow including all landc  m    
    landSurfaceRunoff                    Array         Runoff concentration above the soil more interflow                      m    
    directRunoffGlacier                  Array         direct runoff from glacier                                              m    
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
        Peak time settings:
        - Surface runoff: 3 time steps
        - Interflow: 4 time steps  
        - Baseflow: 5 time steps
        
        Concentration time calculation considers:
        - Grid cell slope and length
        - Land cover-specific Manning roughness
        - Flow velocity relationships
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
            tpeak = 0.5 + 0.6 * 50000.0 / (1440.0 * 60 * np.power(tanslope, 0.5))

            self.var.coverTypes = list(map(str.strip, cbinding("coverTypes").split(",")))

            #     /\   peak time for concentrated runoff
            #   /   \
            #  ---*--
            # landcoverAll = ['runoff_peak']
            # for variable in landcoverAll:  vars(self.var)[variable] = np.tile(globals.inZero, (6, 1))

            # Load run off concentration coefficient

            # for calibration a general runoff concentration factor is loaded
            runoffConc_factor = loadmap('runoffConc_factor')

            i = 0
            self.var.runoff_peak = []
            max = globals.inZero
            for coverType in self.var.coverTypes:
                tpeak_cover = runoffConc_factor * tpeak * loadmap(coverType + "_runoff_peaktime")
                tpeak_cover = np.minimum(np.maximum(tpeak_cover, 0.5), 3.0)
                if "coverType" == "water":
                    tpeak_cover = 0.5
                # tpeak_cover = 0.5
                self.var.runoff_peak.append(tpeak_cover)

                max = np.where(self.var.runoff_peak[i] > max, self.var.runoff_peak[i], max)
                i += 1
            #     /\   maximal timestep for concentrated runoff
            #   /   \
            #  ------*

            self.var.tpeak_interflow = runoffConc_factor * tpeak * loadmap("interflow_runoff_peaktime")
            # self.var.tpeak_interflow = 0.5
            self.var.tpeak_interflow = np.minimum(np.maximum(self.var.tpeak_interflow, 0.5), 4.0)
            self.var.tpeak_baseflow = runoffConc_factor * tpeak * loadmap("baseflow_runoff_peaktime")
            # self.var.tpeak_baseflow = 0.5
            self.var.tpeak_baseflow = np.minimum(np.maximum(self.var.tpeak_baseflow, 0.5), 5.0)
            
            if self.var.includeGlaciers:
                self.var.tpeak_glaciers = runoffConc_factor * tpeak * loadmap("glaciers_runoff_peaktime")
                self.var.tpeak_glaciers = np.minimum(np.maximum(self.var.tpeak_glaciers, 0.5), 3.0)

            max = np.where(self.var.tpeak_baseflow > max, self.var.tpeak_baseflow, max)
            self.var.maxtime_runoff_conc = int(np.ceil(2 * np.amax(max)))
            max = 10
            if self.var.maxtime_runoff_conc > 10:
                max = self.var.maxtime_runoff_conc

            # array with concentrated runoff
            # self.var.runoff_conc = np.tile(globals.inZero, (self.var.maxtime_runoff_conc, 1))
            self.var.runoff_conc = []
            # self.var.runoff_conc = np.tile(globals.inZero, (self.var.maxtime_runoff_conc, 1))
            self.var.runoff_conc = np.tile(globals.inZero, (max, 1))
            for i in range(self.var.maxtime_runoff_conc):
                self.var.runoff_conc[i] = self.var.load_initial("runoff_conc", number=i + 1)

            self.var.gridcell_storage = np.sum(self.var.runoff_conc[:], 0)

        else:
            self.var.gridcell_storage = 0





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
        """
        """
        Dynamic part of the runoff concentration module

        For surface runoff for each land cover class  and for interflow and for baseflow the
        runoff concentration time is calculated

        Note:
            the time demanding part is calculated in a c++ library

        """
        def runoff_concentration(lagtime, peak, fraction, flow, flow_conc):
            """
            Apply triangular weighting function for temporal concentration.
            
            Distributes current runoff over multiple time steps using a
            triangular weighting function based on lag time and peak parameters.
            
            Parameters
            ----------
            lagtime : numpy.ndarray
                Lag time for concentration [time steps]
            peak : float
                Peak time multiplier for concentration
            fraction : numpy.ndarray
                Land cover fraction for weighting
            flow : numpy.ndarray
                Current runoff flux to be concentrated [m/time step]
            flow_conc : numpy.ndarray
                Array for storing concentrated flow over time
                
            Returns
            -------
            numpy.ndarray
                Updated concentrated flow array
                
            Notes
            -----
            Uses triangular distribution to spread instantaneous runoff
            over time based on calculated lag and peak times for realistic
            temporal flow concentration within grid cells.

        
            Part which is transferred to C++ for computational speed

            :param lagtime:
            :param peak:
            :param fraction:
            :param flow:
            :param flow_conc:
            :return:

            areaFractionOld = 0.0
            div = 2 * np.power(peak, 2)

            for lag in range(lagtime):
                lag1 = np.float(lag + 1)
                lag1alt = 2 * peak - lag1
                area = np.power(lag1, 2) / div
                areaAlt = 1 - np.power(lag1alt, 2) / div

                areaFractionSum = np.where(lag1 <= peak, area + globals.inZero, areaAlt + globals.inZero)
                areaFractionSum = np.where(lag1alt > 0, areaFractionSum, 1.0 + globals.inZero)
                areaFraction = areaFractionSum - areaFractionOld
                areaFractionOld = areaFractionSum.copy()

                flow_conc[lag] += fraction * flow * areaFraction
            return flow_conc
        """

        self.var.sum_landSurfaceRunoff = globals.inZero.copy()

        for No in range(6):
            # self.var.sum_directRunoff += self.var.fracVegCover[No] * self.var.directRunoff[No]
            self.var.landSurfaceRunoff[No] = self.var.directRunoff[No] + self.var.interflow[No]
            self.var.sum_landSurfaceRunoff += self.var.fracVegCover[No] * self.var.landSurfaceRunoff[No]
        self.var.runoff = self.var.sum_landSurfaceRunoff + self.var.baseflow + self.var.leakageIntoRunoff


        if self.var.includeGlaciers:
            # from m3/d to m/d by dividing by the cell area
            if self.var.includeOnlyGlaciersMelt:
                self.var.directRunoffGlacier = np.divide(self.var.GlacierMelt,
                                                         (self.var.cellArea * self.var.fracGlacierCover),
                                                         out=np.zeros_like(self.var.GlacierMelt),
                                                         where=(self.var.cellArea * self.var.fracGlacierCover) != 0)
                self.var.GlacierMelt = self.var.GlacierMelt / self.var.cellArea
                self.var.runoff += self.var.GlacierMelt
            else:
                self.var.directRunoffGlacier = np.divide(self.var.GlacierMelt + self.var.GlacierRain, 
                                                         (self.var.cellArea * self.var.fracGlacierCover), 
                                                         out=np.zeros_like(self.var.GlacierMelt), 
                                                         where=(self.var.cellArea * self.var.fracGlacierCover) != 0)
                self.var.GlacierMelt = self.var.GlacierMelt / self.var.cellArea
                self.var.GlacierRain = self.var.GlacierRain / self.var.cellArea
                self.var.runoff += self.var.GlacierMelt + self.var.GlacierRain

        # print(self.var.runoff)
        if checkOption('includeRunoffConcentration'):
            # -------------------------------------------------------
            # runoff concentration: triangular-weighting method

            # shifting array
            self.var.runoff_conc = np.roll(self.var.runoff_conc, -1, axis=0)
            self.var.runoff_conc[self.var.maxtime_runoff_conc - 1] = globals.inZero

            for No in range(6):
                # self.var.runoff_conc = runoff_concentration(self.var.maxtime_runoff_conc,self.var.runoff_peak[No],
                #                                           self.var.fracVegCover[No] ,self.var.directRunoff[No], 
                #                                           self.var.runoff_conc)
                lib2.runoffConc(self.var.runoff_conc, self.var.runoff_peak[No], self.var.fracVegCover[No],
                                self.var.directRunoff[No], self.var.maxtime_runoff_conc, maskinfo['mapC'][0])

            # glacier melt time of concentration
            if self.var.includeGlaciers:
                lib2.runoffConc(self.var.runoff_conc, self.var.tpeak_glaciers, self.var.fracGlacierCover, 
                                self.var.directRunoffGlacier.astype('float64'), self.var.maxtime_runoff_conc, 
                                maskinfo['mapC'][0])
            # interflow time of concentration
            # self.var.runoff_conc = runoff_concentration(self.var.maxtime_runoff_conc, self.var.tpeak_interflow, 
            #                                           1.0, self.var.sum_interflow, self.var.runoff_conc)
            lib2.runoffConc(self.var.runoff_conc, self.var.tpeak_interflow, globals.inZero + 1,
                            self.var.sum_interflow, self.var.maxtime_runoff_conc, maskinfo['mapC'][0])
            # self.var.sum_landSurfaceRunoff = self.var.runoff_conc[0].copy()

            # baseflow time of concentration
            # self.var.baseflow = self.var.baseflow.astype(np.float64)
            lib2.runoffConc(self.var.runoff_conc, self.var.tpeak_baseflow, globals.inZero + 1,
                            self.var.baseflow.astype(np.float64), self.var.maxtime_runoff_conc, maskinfo['mapC'][0])
            # self.var.baseflow = self.var.runoff_conc[0] - self.var.sum_landSurfaceRunoff
            # -------------------------------------------------------------------------------
            #  --- from routing module -------
            # runoff from landSurface cells (unit: m)

            # storage in each grid cell. Total runoff - runoff for the timestep
            self.var.gridcell_storage = self.var.gridcell_storage - self.var.runoff_conc[0] + self.var.runoff
            sumnewrunoff = self.var.runoff.copy()
            self.var.runoff = self.var.runoff_conc[0].copy()
