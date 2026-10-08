# -------------------------------------------------------------------------
# Name:        Snow module
# Purpose: Snow and frost processes module for precipitation partitioning and snow dynamics.
# Simulates snowfall, snow accumulation, snowmelt, and refreezing processes.
# Handles temperature-based precipitation phase determination and snow water equivalent.
#
# Author:      PB, MS, SH
# Created:     13/07/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
import pandas as pd

# TODO remove this portion of the code using sys and make simular to what CWatM uses
# Get the absolute path of /station_gap_fill and to sys.path
# common_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../station_gap_fill"))
# sys.path.append(common_path)

#from cwatm.hydrological_modules.pySnowClim.snowclim_model import _process_forcings_and_energy, _run_snowclim_step, _prepare_outputs
#from cwatm.hydrological_modules.pySnowClim.createParameterFile import create_dict_parameters
#from cwatm.hydrological_modules.pySnowClim.SnowpackVariables import Snowpack
#from cwatm.hydrological_modules.pySnowClim.SnowModelVariables import SnowModelVariables
#import cwatm.hydrological_modules.pySnowClim.constants as const
#import metpy.calc as mpcalc
#from metpy.units import units

import importlib


class snow_frost(object):
    """
    Snow and frost processes module for precipitation partitioning and snow dynamics.
    
    Handles the partitioning of precipitation into rain and snow, calculates snowmelt
    and ice melt using temperature-based and radiation-based approaches, manages snow
    redistribution across elevation zones, and computes frost index for soil freezing.
    Supports multi-layer snow zones for topographic variability representation.
    
    Attributes
    ----------
    var : object
        Reference to model variables object containing state variables
    model : object
        Reference to the main CWatM model instance

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    load_initial                         Flag          Settings initLoad holds initial conditions for variables                bool 
    fracGlacierCover                     Array         Fraction of glacier cover in a grid cell                                %    
    DtDay                                Array         seconds in a timestep (default=86400)                                   s    
    Precipitation                        Array         Precipitation (input for the model)                                     m    
    only_radiation                       Flag          Boolean if only radiation is use for calculation e.g JRC EMO dataset    bool 
    Tavg                                 Array         Input, average air Temperature                                          K    
    Rsds                                 Array         short wave downward surface radiation fluxes                            W/m2 
    EAct                                 Array         Daily vapor pressure                                                    hPa  
    Rsdl                                 Array         long wave downward surface radiation fluxes                             W/m2 
    includeGlaciers                      Flag          Include glaciers                                                        bool 
    snowmelt_radiation                   Array                                                                                 --   
    dzRel                                Array         relative elevation in a gridcell by fraction of area                    m    
    SnowMelt                             Array         total snow melt from all layers                                         m    
    IceMelt                              Array         Ice melt (not really ice but an additional snow melt in summer)         m    
    dem                                  Array         Digital elevation model                                                 m    
    lat                                  Array         Latitude                                                                deg  
    Rain                                 Array         Precipitation less snow                                                 m    
    SnowCover                            Array         snow cover (sum over all layers)                                        m    
    SnowFactor                           Array         Multiplier applied to precipitation that falls as snow                  --   
    numberSnowLayersFloat                Array         Number of snow layers (up to 10)                                        --   
    numberSnowLayers                     Array         Number of snow layers (up to 10)                                        --   
    glaciertransportZone                 Number        Number of layers which can be mimiced as glacier transport zone         --   
    dzSnow                               Array         which dzRel is taken for snow calculation                               --   
    lapseratevar                         Flag          True or False if a variable lapse rate is used                          --   
    lapseR                               Array         Lapserate per month                                                     deg C
    lapseRate                            Array         Lapserate per month                                                     deg C
    frac_snow_redistribution             Array          Maximum fraction of snow that can be redistributed in elevation zones  --   
    SnowDayDegrees                       Array         day of the year to degrees: 360/365.25 = 0.9856                         --   
    SeasonalSnowMeltSin                  Array                                                                                 --   
    excludeGlacierArea                   Flag          True or False to exclude glacier areas from calculation because they a  --   
    summerSeasonStart                    Array         day when summer season starts = 165                                     --   
    IceDayDegrees                        Array         days of summer (15th June-15th Sept.) to degree: 180/(259-165)          --   
    SnowSeason                           Array         seasonal melt factor                                                    m (Ce
    TempSnowLow                          Array         Temperature below which all precipitation is snow                       °C   
    TempSnowHigh                         Array         Temperature above which all precipitation is rain                       °C   
    TempSnow                             Array         Average temperature at which snow melts                                 °C   
    SnowMeltCoef                         Array         Snow melt coefficient - default: 0.004                                  --   
    IceMeltCoef                          Array         Ice melt coefficnet - default  0.007                                    --   
    TempMelt                             Array         Average temperature at which snow melts                                 °C   
    SnowMeltRad                          Array         calibration value a factor to radiation coefficient                     --   
    SnowCoverS                           Array         snow cover for each layer                                               m    
    adv_frost                                                                                                                  --   
    maxFrostIndex                                                                                                              --   
    Kfrost                               Array         Snow depth reduction coefficient, (HH, p. 7.28)                         m-1  
    Afrost                               Array         Daily decay coefficient, (Handbook of Hydrology, p. 7.28)               --   
    FrostIndexThreshold                  Array         Degree Days Frost Threshold (stops infiltration, percolation and capil  --   
    SnowWaterEquivalent                  Array         Snow water equivalent, (based on snow density of 450 kg/m3) (e.g. Tarb  --   
    FrostIndex                           Array         FrostIndex - Molnau and Bissel (1983), A Continuous Frozen Ground Inde  --   
    Snow                                 Array         Snow (equal to a part of Precipitation)                                 m    
    Snow1                                Array                                                                                 --   
    Rain1                                Array                                                                                 --   
    snow_redistributed_previous          Array                                                                                 --   
    SnowFraction                         Array         Fraction of snow in a gridcell                                          --   
    precipitation_sn                     Array                                                                                 --   
    fracVegCover                         Array         Fraction of specific land covers (0=forest, 1=grasslands, etc.)         %    
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize snow and frost module.
        
        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initialize snow and frost module parameters and elevation zones.
        
        Loads parameters for the day-degree approach for precipitation partitioning,
        snowmelt, and ice melt calculations. Sets up multiple elevation zones for
        representing topographic variability, initializes snow cover distributions,
        and configures frost index parameters.
        
        Notes
        -----
        Key initialization components:
        - Elevation zone configuration (1-10 zones) based on relative elevation data
        - Temperature lapse rate setup (constant or variable)
        - Snow redistribution parameters based on slope and land cover
        - Seasonal snow melt coefficient parameters
        - Initial snow cover distribution across elevation zones
        - Frost index parameters for soil freezing calculations
        """

        self.var.numberSnowLayersFloat = loadmap('NumberSnowLayers')
        # now using dz_relative -> fix to 1 or several
        #if self.var.numberSnowLayersFloat > 1.0:
        #    self.var.numberSnowLayersFloat = 5.0
        self.var.numberSnowLayers = int(self.var.numberSnowLayersFloat)
        # default 1 -> highest zone is transported to middle zone
        self.var.glaciertransportZone = int(loadmap('GlacierTransportZone'))

        if self.var.usepySnowClim:
            self.var.numberSnowLayers = 1
            self.var.includeGlaciers= False        # Difference between (average) air temperature at average elevation of
        # pixel and centers of upper- and lower elevation zones [deg C]
        # ElevationStD:   Standard Deviation of the DEM
        # 0.9674:    Quantile of the normal distribution: u(0,833)=0.9674 to split the pixel in 3 equal parts.

        # --- Topography -----------------------------------------------------
        # maps of relative elevation above flood plains

        dzRel = ['dzRel0001', 'dzRel0005', 'dzRel0010', 'dzRel0020', 'dzRel0030', 'dzRel0040', 'dzRel0050',
                 'dzRel0060', 'dzRel0070', 'dzRel0080', 'dzRel0090', 'dzRel0100']

        self.var.dzRel = []
        for i, item in enumerate(dzRel):
            self.var.dzRel.append(readnetcdfWithoutTime(cbinding('relativeElevation'), item, i))

        # from relative elevation take 5 levels: 80-100% -> 90% -> id11, 60-80% -> 70% -> id9  ...
        dzSnow = \
            [[7],
            [9, 5],
            [9, 7, 5],
            [11, 8, 5, 3],
            [11, 9, 7, 5, 3],
            [11, 9, 7, 5, 3, 1],
            [11, 9, 8, 7, 5, 3, 1],
            [11, 9, 8, 7, 6, 5, 3, 1],
            [11, 10, 9, 8, 7, 6, 5, 3, 1],
            [11, 10, 9, 8, 7, 6, 5, 4, 3, 1]]

        self.var.dzSnow = dzSnow[self.var.numberSnowLayers - 1]

        self.var.lapseratevar = False
        if 'LapseRateVariable' in binding:
            self.var.lapseratevar = returnBool('LapseRateVariable')

        if self.var.lapseratevar:
            self.var.lapseR = []
            for i in range(12):
                self.var.lapseR.append(readnetcdf12month(cbinding('LapseRate'), i))
                # read lapse rate from Dutra et al. 2022 global 0.25 deg
                # values are negative
                # https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2019ea000984

        else:
            self.var.lapseRate = loadmap('TemperatureLapseRate')

        #divNo = 1./float(self.var.numberSnowLayers)
        #deltaNorm = np.linspace(divNo/2, 1-divNo/2, self.var.numberSnowLayers)
        #self.var.deltaInvNorm = norm.ppf(deltaNorm)
        #self.var.deltaInvNorm = dn[self.var.numberSnowLayers]
        #self.var.ElevationMin = loadmap('Elevation')
        #self.var.ElevationMean = loadmap('Elevation_avg')

        # max_frac_snow_redistriution = 0.5
        # max_ELevationStD = 1500
        #min_ElevationStD_snow_redistr = 100
        # 0.46 is the maximum fraction that can be redistributed if snow density is assumed to be 350kg/m3 according to eq. 13 in Frey & Holzmann (2015)
        # this fraction has to be multiplied with the slope, highest slope is 90 degrees
        # the mean slope of each grid cell is the mean of all slopes of the 3'' SRTM DEM
        # the maximum fraction that can be redistributed if snow density is assumed to be 200kg/m3 according to eq. 13 in Frey & Holzmann (2015) is 0.35
        slope_degrees = np.degrees(np.arctan(loadmap('tanslope')))
        self.var.frac_snow_redistribution = np.maximum(0.35 * slope_degrees / 90, globals.inZero)


        self.var.SnowDayDegrees = 0.9856
        #to get the seasonal cycle in snow melt coefficient, value is 81 (263) for northern (southern) hemisphere
        if 'SeasonalSnowMeltSin' in binding:
            self.var.SeasonalSnowMeltSin = loadmap('SeasonalSnowMeltSin')

        self.var.excludeGlacierArea = False
        if self.var.includeGlaciers:
            self.var.excludeGlacierArea = returnBool('excludeGlacierArea')

        # day of the year to degrees: 360/365.25 = 0.9856
        self.var.summerSeasonStart = 165
        #self.var.IceDayDegrees = 1.915
        self.var.IceDayDegrees = 180./(259- self.var.summerSeasonStart)
        # days of summer (15th June-15th Sept.) to degree: 180/(259-165)
        self.var.SnowSeason = loadmap('SnowSeasonAdj') * 0.5
        # default value of range  of seasonal melt factor is set to 0.001 m C-1 day-1
        # 0.5 x range of sinus function [-1,1]
        if 'TempSnowLow' in binding:
            self.var.TempSnowLow = loadmap('TempSnowLow')
            self.var.TempSnowHigh = loadmap('TempSnowHigh')
        else:
            self.var.TempSnow = loadmap('TempSnow')
        self.var.SnowFactor = loadmap('SnowFactor')
        self.var.SnowMeltCoef = loadmap('SnowMeltCoef')
        self.var.IceMeltCoef = loadmap('IceMeltCoef')

        self.var.TempMelt = loadmap('TempMelt')

        # New snowmelt includes radiation and a calibration factor for radiation
        if 'SnowMeltRad' in binding:
            self.var.SnowMeltRad = loadmap('SnowMeltRad')        # initialize as many snow covers as snow layers -> read them as SnowCover1 , SnowCover2 ...
        else:
            self.var.SnowMeltRad = 1 + globals.inZero
            
        # SnowCover1 is the highest zone
        self.var.SnowCoverS = []
        for i in range(self.var.numberSnowLayers):
            self.var.SnowCoverS.append(self.var.load_initial("SnowCover",number = i+1))

        # initial snow depth in elevation zones A, B, and C, respectively  [mm]
        self.var.SnowCover = np.sum(self.var.SnowCoverS,axis=0) / self.var.numberSnowLayersFloat + globals.inZero

        # if the EMO dataset for meteo data is used, only rd is given, so we need additional data like elevation and latitude
        # it is loaded in evapopot, but not always evapopot is calculated
        if self.var.only_radiation:
            self.var.dem = loadmap('dem')
            self.var.lat = loadmap('latitude')


        # Pixel-average initial snow cover: average of values in 3 elevation
        # zones

        # ---------------------------------------------------------------------------------
        # Initial part of frost index

        self.var.adv_frost = False
        if 'Advanced_FrostIndex' in binding:
            self.var.adv_frost  = returnBool('Advanced_FrostIndex')
            self.var.maxFrostIndex = loadmap('maxFrostIndex')


        self.var.Kfrost = loadmap('Kfrost')
        self.var.Afrost = loadmap('Afrost')
        self.var.FrostIndexThreshold = loadmap('FrostIndexThreshold')
        self.var.SnowWaterEquivalent = loadmap('SnowWaterEquivalent')

        self.var.FrostIndex = self.var.load_initial('FrostIndex')

        if checkOption('reportsnowstations',True):

            # PB 31/8 Snow calibration
            where = "GaugesElev"
            outelev = cbinding(where).split()
            self.var.outelevation = list(map(int, outelev))
            elevation = loadmap('Elevation_min')

            self.var.elepoint = []
            i = 0
            for key in sorted(self.var.sampleAdresses):
                hoehe = self.var.outelevation[i]

                if self.var.sampleAdresses[key] < 0:
                    self.var.elepoint.append(0)
                else:
                    # zero level of a cell can be higher than min elevation
                    e1 = elevation[self.var.sampleAdresses[key]] - self.var.dzRel[0][self.var.sampleAdresses[key]]
                    erange = []
                    for dz in self.var.dzSnow:
                        rel_elev = self.var.dzRel[dz][self.var.sampleAdresses[key]]
                        erange.append(e1 + rel_elev)
                    erange.append(-9999.)

                    for e2 in range(len(self.var.dzSnow)):
                        testE = erange[e2] - (erange[e2] - erange[e2 + 1]) / 2
                        if hoehe > testE:
                            break
                    self.var.elepoint.append(e2)
                i += 1


        if self.var.usepySnowClim:
            # load libraries, but only if pySnowClim is used
            self.var._process_forcings_and_energy = getattr(importlib.import_module('cwatm.hydrological_modules.pySnowClim.snowclim_model'),
                                             '_process_forcings_and_energy')
            self.var._run_snowclim_step = getattr(importlib.import_module('cwatm.hydrological_modules.pySnowClim.snowclim_model'),
                                             '_run_snowclim_step')
            self.var._prepare_outputs = getattr(importlib.import_module('cwatm.hydrological_modules.pySnowClim.snowclim_model'),
                                             '_prepare_outputs')
            create_dict_parameters = getattr(importlib.import_module('cwatm.hydrological_modules.pySnowClim.createParameterFile'),
                                             'create_dict_parameters')
            self.var.Snowpack = getattr(importlib.import_module('cwatm.hydrological_modules.pySnowClim.SnowpackVariables'),
                                             'Snowpack')
            SnowModelVariables = getattr(importlib.import_module('cwatm.hydrological_modules.pySnowClim.SnowModelVariables'),
                                             'SnowModelVariables')
            #import cwatm.hydrological_modules.pySnowClim.constants as const
            self.var.constSnowClim = importlib.import_module('cwatm.hydrological_modules.pySnowClim.constants')

            # Parameter foor pySnowClim , also calibration parameters
            # see Table2 in https://gmd.copernicus.org/articles/15/5045/2022/gmd-15-5045-2022.html
            self.var.stability = loadmap('stability')  # Stability setting (default: 1)
            self.var.windHt = loadmap('windHt')  # Wind height (default: 10 meters)
            self.var.tempHt = loadmap('tempHt')  # Temperature height (default: 2 meters)
            self.var.snowoff_month = loadmap('snowoff_month')  # Month of snow-off (default: 9)
            self.var.snowoff_day = loadmap('snowoff_day')  # Day of snow-off (default: 1)
            self.var.albedo_option = loadmap('albedo_option')  # Albedo option(default: 2) (calib: 1 or 2)
            self.var.max_albedo = loadmap('max_albedo')  # Maximum albedo (default: 0.85) (calib: 0.85-0.90)
            self.var.z_0 = loadmap('z_0')  # Roughness length (default: 0.00001 m) (10-5 - 10-3)
            self.var.z_h = loadmap('z_h')  # Roughness length for heat (default: z_0/10)
            self.var.lw_max = loadmap('lw_max')  # Maximum longwave radiation(default: 0.1)
            self.var.Tstart = loadmap('Tstart')  # Starting temperature (default: 0°C)
            self.var.Tadd = loadmap('Tadd')  # Temperature adjustment (default: -10000°C)
            self.var.maxtax = loadmap('maxtax')  # Maximum tax (default: 0.9) (calib: 0.3-0.9)
            self.var.E0_value = loadmap('E0_value')  # Windless exchange coefficient (default: 1) (calib  0-2)
            self.var.E0_app = loadmap('E0_app')  # Windless exchange application option (default: 1)
            self.var.E0_stable = loadmap('E0_stable')  # Windless exchange stability option (default: 2)
            self.var.Ts_add = loadmap('Ts_add')  # Temperature add factor (default: 2°C) (calib 0-2)
            self.var.smooth_time_steps = loadmap('smooth_time_steps')  # Smoothing time steps (default: 12) (calib: 8-24)
            self.var.ground_albedo = loadmap('ground_albedo')  # Ground albedo (default: 0.25)
            self.var.snow_emis = loadmap('snow_emis')  # Snow emissivity (default: 0.98)
            self.var.snow_dens_default = loadmap('snow_dens_default')  # Default snow density (default: 250 kg/m³)
            self.var.G = loadmap('G')  # Ground conduction (default: 173/86400 kJ/m²/s)
            self.var.max_swe_height = loadmap('max_swe_height')  # Max height of SWE before solar radiation factor starts to work (default: 100 m)
            self.var.downward_radiation_factor = loadmap(
                'downward_radiation_factor')  # Factor to be multiplied by solar radiation when SWE > max_swe_height (default: 1.3)
            self.var.downward_radiation_start_month = loadmap(
                'downward_radiation_start_month')  # Month where solar_radiation_factor start to be applied (default: 6)
            self.var.downward_radiation_end_month = loadmap('downward_radiation_end_month')  # Month where solar_radiation_factor ends (default: 10)

            # The lines below can be replace by for example
            # stability = loadmap('stability'). The reason is neing loaded before
            # then passed is to give clarify using the xml file variables.
            self.var.snowclimParameters = create_dict_parameters(
                stability = self.var.stability,
                windHt = self.var.windHt,
                tempHt = self.var.tempHt,
                snowoff_month = self.var.snowoff_month,
                snowoff_day = self.var.snowoff_day,
                albedo_option = self.var.albedo_option,
                max_albedo = self.var.max_albedo,
                z_0 = self.var.z_0,
                z_h = self.var.z_h,
                lw_max = self.var.lw_max,
                Tstart = self.var.Tstart,
                Tadd = self.var.Tadd,
                maxtax = self.var.maxtax,
                E0_value = self.var.E0_value,
                E0_app = self.var.E0_app,
                E0_stable = self.var.E0_stable,
                Ts_add = self.var.Ts_add,
                smooth_time_steps = self.var.smooth_time_steps,
                ground_albedo = self.var.ground_albedo,
                snow_emis = self.var.snow_emis,
                snow_dens_default = self.var.snow_dens_default,
                G = self.var.G,
                max_swe_height = self.var.max_swe_height,
                downward_radiation_factor = self.var.downward_radiation_factor,
                downward_radiation_start_month = self.var.downward_radiation_start_month,
                downward_radiation_end_month = self.var.downward_radiation_end_month,
                )

            self.var.snowpack = self.var.Snowpack(globals.inZero.shape[0],
                                         self.var.snowclimParameters)
            self.var.snowModelvars = SnowModelVariables(globals.inZero.shape[0])
    # --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Calculate snow and frost processes for current time step.
        
        Performs precipitation partitioning into rain and snow based on temperature
        thresholds, computes snowmelt and ice melt using temperature-index and
        radiation-based approaches, handles snow redistribution between elevation
        zones, and updates frost index for soil freezing conditions.
        
        Notes
        -----
        The method processes each elevation zone sequentially and handles:
        - Temperature correction based on elevation and lapse rate
        - Precipitation partitioning using temperature thresholds
        - Snow and ice melt calculation with seasonal variations
        - Snow redistribution based on holding capacity and slope
        - Snow fraction calculation for each elevation zone
        - Frost index update based on air temperature and snow cover
        
        References
        ----------
        Snow melt equations modified from:
        Speers, D.D., Versteeg, J.D. (1979) Runoff forecasting for reservoir 
        operations - the past and the future. In: Proceedings 52nd Western 
        Snow Conference, 149-156
        
        Frost index calculations based on:
        Molnau and Bissel (1983) A Continuous Frozen Ground Index for Flood 
        Forecasting. In: Maidment, Handbook of Hydrology, p. 7.28, 7.55
        
        Snow redistribution inspired by:
        Frey and Holzmann (2015) doi:10.5194/hess-19-4517-2015
        """

        if self.var.usepySnowClim:
            # TODO remove the hard coded unit transformations
            # ###############################################
            #               ATTENTION !!!!!                 #
            # ###############################################
            # All the transformations in the forcings data were added to adjust
            # the forcings to the correct units used by pySnowClim, which are:
            # lrad - downward longwave radiation (kJ/m2/hr) (time x space)
            # tavg - average air temperature (C) (time x space)
            # ppt - precipitation (m) (time x space)
            # solar - downward shortwave radiation (kJ/m2/hr) (time x space)
            # tdmean  - dewpoint temperature (C) (time x space)
            # vs - windspeed (m/s) (time x space)
            # relhum - relative humidity (%) (time x space)
            # psfc - air pressure (hPa or mb) (time x space)
            # huss - specific humidity (kg/kg) (time x space)

            # TODO the specific humidity calculation should probably be inside
            # readmeto.py

            # kPa to hPA
            Psurf = self.var.Psurf.copy() * 10
            #pressure_with_units = (Psurf) * units('hPa')
            #dewpoint_with_units = (self.var.Tdew) * units('degC')

            # Calculate specific humidity
            #specific_humidity = mpcalc.specific_humidity_from_dewpoint(
            #    pressure_with_units, dewpoint_with_units)
            #specific_humidity.magnitude = self.var.huss


            forcings = {"tavg": self.var.Tavg,
                        "psfc": Psurf,
                        # For wind speed there is an adjustment for measurement height made on readmeteo.
                        # Correction from wind speed measured at 10 m to 2 m height
                        "vs": self.var.Wind/0.749, # correction back from the internal correction made by CwatM, from wind at 2m to wind at 10m height
                        "ppt": self.var.Precipitation,
                        # from W/m2 to kJ/m2/hr *time step
                        "solar": (self.var.Rsds/self.var.WtoMJ)*3.6*self.var.snowclimParameters['hours_in_ts'],
                        "lrad": (self.var.Rsdl/self.var.WtoMJ)*3.6*self.var.snowclimParameters['hours_in_ts'],
                        #"huss": specific_humidity.magnitude,
                        "huss": self.var.huss,
                        # TODO create a variable for RH.
                        # Qa ir is in fact RH when using the option useHuss
                        "relhum": self.var.rhs,
                        "tdmean": self.var.Tdew
                }
            # TODO Lat is only used in snowcilm to calculate albedo and define the
            # sizes of the classes. The variable to get lat should be added here after.
            # There is only 1 albedo scheme which uses lat. Tavg is passed here
            # only to have the size of the classes correctly.
            coords = {"lat": self.var.Tavg}
            forcings_data = {"forcings": forcings, "coords": coords}

            # Because CWatM handles data differenty and it is daily these
            # values snow_model_instances and index_snowclim are basically
            # unused by pySnowClim.
            snow_model_instances = [None]
            index_snowclim = 0

            # loading necessary data to run the model
            input_forcings, snow_vars, previous_energy, precip = self.var._process_forcings_and_energy(
                index_snowclim, forcings_data, self.var.snowclimParameters, snow_model_instances)
            # partition between snow and rain made by snowclim
            SnowS = precip.sfe.copy()
            RainS = precip.rain.copy()

            time_value = [dateVar['currDate'].year, dateVar['currDate'].month, dateVar['currDate'].day]
            # Reset to 0 snow at the specified time of year,
            if self.var.snowoff_month > 0:
                if time_value[1] == self.var.snowoff_month and time_value[2] == self.var.snowoff_day:
                    self.var.snowpack = self.var.Snowpack(globals.inZero.shape[0], self.var.snowclimParameters)

            self.var.snowpack, snow_vars = self.var._run_snowclim_step(
                snow_vars,
                self.var.snowpack,
                precip,
                forcings,
                self.var.snowclimParameters,
                coords,
                time_value,
                previous_energy)
            snow_vars.CCsnowfall = precip.snowfallcc.copy()
            self.var.snowModelvars =  self.var._prepare_outputs(snow_vars, precip)

            self.var.ExistSnow = self.var.snowModelvars.ExistSnow.copy()
            self.var.SnowMelt = self.var.snowModelvars.Runoff / self.var.constSnowClim.WATERDENS
            self.var.Rain_on_snow = np.where(self.var.ExistSnow, precip.rain, 0)
            self.var.Rain = np.where(self.var.ExistSnow, 0, precip.rain)
            self.var.Snow = precip.sfe.copy()


            self.var.SnowCover = self.var.snowModelvars.SnowWaterEq / self.var.constSnowClim.WATERDENS
            self.var.snow_redistributed_previous = globals.inZero.copy()

            # lost due to sublimation and condensation
            # noy calculated in evaporation again!
            self.var.snowEvap = (self.var.snowModelvars.Sublimation +  self.var.snowModelvars.Condensation) / self.var.constSnowClim.WATERDENS


            # snowfraction set to 0 -> ExistSnow for true or false
            self.var.SnowFraction = globals.inZero.copy()
            # icemelt =0 -> snowtowers are handled in pySnowClim
            self.var.IceMelt = globals.inZero.copy()
            self.var.iceEvap = globals.inZero.copy()


        else:

            # sinus shaped function between the
            # annual minimum (December 21st) and annual maximum (June 21st) for the northern hemisphere
            # annual maximum (December 21st) and annual minimum (June 21st) for the northern hemisphere
            if 'SeasonalSnowMeltSin' in binding:
                SnowMeltCycle = np.sin(np.radians((dateVar['doy'] - self.var.SeasonalSnowMeltSin)
                                        * self.var.SnowDayDegrees))
                SeasSnowMeltCoef = self.var.SnowSeason * SnowMeltCycle + self.var.SnowMeltCoef

                # IceMelt is adjusted to account for southern hemisphere
                # for northern hemisphere Icemelt can occur between doy 166 and doy 256
                # for southern hemisphere Icemelt can occur between doy 348 and doy 73
                # amplitude and curve shape are the same

                SummerSeason = np.sin(
                    math.radians((dateVar['doy'] - self.var.summerSeasonStart) * self.var.SnowDayDegrees * 2))

                SummerSeason = np.where(SummerSeason < 0 or SnowMeltCycle < 0, globals.inZero, SummerSeason)

            else:
                SeasSnowMeltCoef = self.var.SnowSeason * np.sin(math.radians((dateVar['doy'] - 81)
                                                                             * self.var.SnowDayDegrees)) + self.var.SnowMeltCoef
                if (dateVar['doy'] > self.var.summerSeasonStart) and (dateVar['doy'] < 260):
                    SummerSeason = np.sin(math.radians((dateVar['doy'] - self.var.summerSeasonStart) * self.var.IceDayDegrees))
                else:
                    SummerSeason = 0.0

            self.var.Snow = globals.inZero.copy()
            self.var.Rain = globals.inZero.copy()
            # for glacier: snow and rain is reduced by glacier size, but to calc the total amount all snow and rain is needed
            self.var.Snow1 = globals.inZero.copy()
            self.var.Rain1 = globals.inZero.copy()
            self.var.SnowMelt = globals.inZero.copy()
            self.var.IceMelt = globals.inZero.copy()
            self.var.SnowCover = globals.inZero.copy()
            self.var.snow_redistributed_previous = globals.inZero.copy()

            # snow melt potential is collected from up the mountain towards valley
            snowIceM_surplus = globals.inZero.copy()
            # snow cover fraction of a gridcell
            self.var.SnowFraction = globals.inZero.copy()

            #get number of elevation zones with forest
            #assume forest is most present at lowest location
            nr_frac_forest = self.var.numberSnowLayers - np.round(self.var.fracVegCover[0] / (1 / self.var.numberSnowLayers)) - 1

            if self.var.includeGlaciers:
                if self.var.excludeGlacierArea:
                    current_fracGlacierCover = self.var.fracGlacierCover.copy() #percentage area of each layer
                # elev_red = 5
                # current_fracGlacierCover = self.var.fracGlacierCover / elev_red
            #substract glacier area from highest areas
            #loops through snow layers from highest to lowest
            #the capacity depends on the fraction of forest or grassland
            #self.var.SnowCoverSCapacity[i]


            # if only radiation is given like in the EMO meteo dataset:
            # then rsdl has to be calculted in this way
            if self.var.snowmelt_radiation:
                if self.var.only_radiation:
                    radian = np.pi / 180 * self.var.lat
                    distanceSun = 1 + 0.033 * np.cos(2 * np.pi * dateVar['doy'] / 365)
                    # Chapter 3: equation 24
                    declin = 0.409 * np.sin(2 * np.pi * dateVar['doy'] / 365 - 1.39)
                    ws = np.arccos(-np.tan(radian * np.tan(declin)))
                    Ra = 24 * 60 / np.pi * 0.082 * distanceSun * (
                            ws * np.sin(radian) * np.sin(declin) + np.cos(radian) * np.cos(declin) * np.sin(ws))
                    # Equation 21 Chapter 3
                    Rso = Ra * (0.75 + (2 * 10 ** -5 * self.var.dem))  # in MJ/m2/day
                    # Equation 37 Chapter 3
                    RsRso = 1.35 * self.var.Rsds / Rso - 0.35
                    RsRso = np.minimum(np.maximum(RsRso, 0.05), 1)
                    RSNet = (0.34 - 0.14 * np.sqrt(self.var.EAct)) * RsRso
                    # Eact in hPa but needed in kPa : kpa = 0.1 * hPa - conversion done in readmeteo

            month = dateVar['currDate'].month - 1
            # run through all snow layers

            for i in range(self.var.numberSnowLayers):

                if self.var.lapseratevar:
                    # lapse rate from Dutra et al. 2022 is negative
                    TavgS = self.var.Tavg + self.var.lapseR[month] * (self.var.dzRel[self.var.dzSnow[i]] - self.var.dzRel[7])
                else:
                    TavgS = self.var.Tavg - self.var.lapseRate * (self.var.dzRel[self.var.dzSnow[i]] - self.var.dzRel[7])

                # Temperature at center of each zone (temperature at zone B equals Tavg)
                # i=0 -> highest zone
                # i=2 -> lower zone
                if 'TempSnowLow' in binding:
                    #fraction of solid precipitation maximum 1, minimum 0
                    frac_solid = np.clip(1 - (TavgS - self.var.TempSnowLow) / (self.var.TempSnowHigh - self.var.TempSnowLow), 0, 1)
                    SnowS = frac_solid * self.var.SnowFactor * self.var.Precipitation
                    RainS = (1 - frac_solid) * self.var.Precipitation
                else:
                    SnowS = np.where(TavgS < self.var.TempSnow, self.var.SnowFactor * self.var.Precipitation,
                                     globals.inZero)
                    # Precipitation is assumed to be snow if daily average temperature is below TempSnow
                    # Snow is multiplied by correction factor to account for undercatch of
                    # snow precipitation (which is common)
                    RainS = np.where(TavgS >= self.var.TempSnow, self.var.Precipitation, globals.inZero)

                # Snow melt with with radiation
                # radiation part from evaporationPot -> snowmelt has now a temperature part and a radiation part
                # from Erlandsen et al. Hydrology Research 52.2 2021
                if self.var.snowmelt_radiation:
                    RNup = 4.903E-9 * (TavgS + 273.16) ** 4
                    # if only radiation is given like in the EMO meteo dataset:
                    if self.var.only_radiation:
                        RLN = RNup * RSNet
                    else:
                        RLN = RNup - self.var.Rsdl
                    RN = (self.var.Rsds - RLN) / 334.0
                    # latent heat of fusion = 0.334 mJKg-1 * desity of water = 1000 khm-3

                    SnowMeltS = (TavgS - self.var.TempMelt) * SeasSnowMeltCoef + self.var.SnowMeltRad * RN
                    SnowMeltS = SnowMeltS * (1 + 0.01 * RainS) * self.var.DtDay
                else:
                    # without radiation
                    SnowMeltS = (TavgS - self.var.TempMelt) * SeasSnowMeltCoef * (1 + 0.01 * RainS) * self.var.DtDay
                SnowMeltS = np.maximum(SnowMeltS, globals.inZero)

                # for which layer the ice melt is calculated with the middle temp.
                # for the others it is calculated with the corrected temp
                # this is to mimic glacier transport to lower zones
                if i <= self.var.glaciertransportZone:
                    IceMeltS = self.var.Tavg * self.var.IceMeltCoef * self.var.DtDay * SummerSeason
                    # if i = 0 and 1 -> higher and middle zone
                    # Ice melt coeff in m/C/deg
                else:
                    IceMeltS = TavgS * self.var.IceMeltCoef * self.var.DtDay * SummerSeason

                # Check snowcover and snowmelt
                IceMeltS = np.maximum(IceMeltS, globals.inZero)

                SnowIceMeltS = np.maximum(np.minimum(SnowMeltS + IceMeltS + snowIceM_surplus, self.var.SnowCoverS[i]), globals.inZero)

                # snowIceM_surplus: each elevation band snow melt potential is collected -> one way to melt additianl snow which might
                # be colleted in the valley because of snow retribution
                snowIceM_surplus = np.abs(np.minimum(self.var.SnowCoverS[i] - (SnowMeltS + IceMeltS + snowIceM_surplus),0))

                IceMeltS = np.maximum(SnowIceMeltS - SnowMeltS, globals.inZero)
                SnowMeltS = np.maximum(SnowIceMeltS - IceMeltS, globals.inZero)
                # check if snow+ice not bigger than snowcover
                self.var.SnowCoverS[i] = self.var.SnowCoverS[i] + SnowS - SnowIceMeltS

                # snow redistribution inspired by Frey and Holzmann (2015) doi:10.5194/hess-19-4517-2015
                # if snow cover higher than snow holding capacity redistribution
                # get the thresholds for the snow based on the snow density and snow depth values in Frey and Holzmann (2015)
                # capacity of forest 2.5m snow cover, assumed snow density 250kg/m3: 0.25 * 1000 * 2.5 / 1000
                # capacity of other land cover 0.25m snow cover, assumed snow density 250kg/m3: 0.25 * 1000 * 0.25 / 1000
                # but only for cells with std above 100m
                swe_forest = 0.625
                swe_other = 0.2
                # snow capacity depends on whether there is frost cover in the elevation zone
                snowcapacity = np.where(i <= nr_frac_forest, swe_other, swe_forest)
                # where snow cover is higher than capacity, a fraction of snow will be redistributed

                # reduction factor at lowest level no snow_retri, increasing to factor 0.9 at highest level
                reduction_factor = 1.0 * (1 - (i + 1) / self.var.numberSnowLayers)
                snow_redistributed = np.where(self.var.SnowCoverS[i] > snowcapacity,
                        self.var.frac_snow_redistribution * self.var.SnowCoverS[i] * reduction_factor, 0)
                # the lowest elevation zone cannot redistribute snow -> this is replaced by reduction_factor = 0 in the lowest elevation band
                #if i == self.var.numberSnowLayers - 1:
                #    snow_redistributed = globals.inZero.copy()

                snow_redistributed = np.maximum(snow_redistributed, globals.inZero)
                # the current snow cover will be reduced by the amount of snow that is redistributed
                # the redistributed snow from higher elevation zone will be added
                self.var.SnowCoverS[i] = self.var.SnowCoverS[i] - snow_redistributed + self.var.snow_redistributed_previous
                # redistributed snow will be added to next elevation zone in next loop
                self.var.snow_redistributed_previous = snow_redistributed.copy()

                # calculation of snow fraction in each elevation band
                # =< 0.02 SnowCoverS -> no snow
                sfrac = np.where(self.var.SnowCoverS[i] > 0.02,0.25,0)
                sfrac = np.where(self.var.SnowCoverS[i] > 0.05, 0.5,sfrac)
                sfrac = np.where(self.var.SnowCoverS[i] > 0.10, 1.0, sfrac)

                self.var.SnowFraction += sfrac / self.var.numberSnowLayers

                # here outputs are just summed up because equal distribution across elevation zones
                # when glaciers are included the higher elevations should play less of a role
                if self.var.excludeGlacierArea:
                    # the weight is the fraction of current elevation zone that is not covered by glacier
                    # the glacier is subtracted from the highest elevation zone first
                    weight = 1 / self.var.numberSnowLayers - current_fracGlacierCover
                    # the fraction of glacier cover is decreased by fraction that is covered by glacier in current elevation zone
                    current_fracGlacierCover = np.where(weight > 0, 0, abs(weight))
                    #weight below zero is set to zero
                    weight[weight < 0] = 0
                    self.var.Snow1 += SnowS / self.var.numberSnowLayersFloat
                    self.var.Rain1 += RainS / self.var.numberSnowLayersFloat
                    # depends on the area of non glacier area in a gridcell
                    self.var.Snow += SnowS * weight
                    self.var.Rain += RainS * weight
                    self.var.SnowMelt += SnowMeltS * weight
                    self.var.IceMelt += IceMeltS * weight
                    self.var.SnowCover += self.var.SnowCoverS[i] * weight

                else:
                    self.var.Snow += SnowS
                    self.var.Rain += RainS
                    self.var.SnowMelt += SnowMeltS
                    self.var.IceMelt += IceMeltS
                    self.var.SnowCover += self.var.SnowCoverS[i]


            
            if not self.var.excludeGlacierArea:
                self.var.Snow /= self.var.numberSnowLayersFloat
                self.var.Rain /= self.var.numberSnowLayersFloat
                self.var.SnowMelt /= self.var.numberSnowLayersFloat
                self.var.IceMelt /= self.var.numberSnowLayersFloat
                self.var.SnowCover /= self.var.numberSnowLayersFloat
                self.var.precipitation_sn = self.var.Snow + self.var.Rain
            else:
                # if glaicer than calculate also rain+snow on glacier
                self.var.precipitation_sn = self.var.Snow1 + self.var.Rain1



        # ---------------------------------------------------------------------------------
        # Dynamic part of frost index
        if self.var.adv_frost:
            Kfrost = self.var.Kfrost
        else:
            Kfrost = np.where(self.var.Tavg < 0, 0.08, 0.5)
            self.var.maxFrostIndex = 1000.

        # self.var.Kfrost = np.where(self.var.Tavg < 0, 0.08, 0.5)
        FrostIndexChangeRate = -(1 - self.var.Afrost) * self.var.FrostIndex - self.var.Tavg * \
            np.exp(-0.4 * 100 * Kfrost * self.var.SnowCover / self.var.SnowWaterEquivalent)
        # Rate of change of frost index (expressed as rate, [degree days/day])
        self.var.FrostIndex = np.maximum(self.var.FrostIndex + FrostIndexChangeRate * self.var.DtDay, 0)
        self.var.FrostIndex = np.where(self.var.FrostIndex > self.var.maxFrostIndex, self.var.maxFrostIndex, self.var.FrostIndex)
        # frost index in soil [degree days] based on Molnau and Bissel (1983, A Continuous Frozen Ground Index for Flood
        # Forecasting. In: Maidment, Handbook of Hydrology, p. 7.28, 7.55)
        # if Tavg is above zero, FrostIndex will stay 0
        # if Tavg is negative, FrostIndex will increase with 1 per degree C per day
        # Exponent of 0.04 (instead of 0.4 in HoH): conversion [cm] to [mm]!  -> from cm to m HERE -> 100 * 0.4
        # maximum snowlayer = 1.0 m
        # Division by SnowDensity because SnowDepth is expressed as equivalent water depth(always less than depth of snow pack)
        # SnowWaterEquivalent taken as 0.45
        # Afrost, (daily decay coefficient) is taken as 0.97 (Handbook of Hydrology, p. 7.28)
        # Kfrost, (snow depth reduction coefficient) is taken as 0.57 [1/cm], (HH, p. 7.28) -> from Molnau taken as 0.5 for t> 0 and 0.08 for T<0




