# -------------------------------------------------------------------------
# Name:        Snow module with pySnowClim (usepySnowClim = True)
# Purpose: Energy balance snow model for precipitation partitioning and snow dynamics.
# Simulates snowfall, snow accumulation, snowmelt, refreezing, sublimation and condensation
# in snow samples (elevation zones) with pySnowClim:
# Lute, A. C. et al. (2022)
# Frost index: frost.py, degree-day snow model: snow.py
#
# Author:      PB, MS, SH
# Created:     13/07/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
# functions used by both snow modules: only defined in snow.py
from cwatm.hydrological_modules.snow import snowZoneOffsets, loadLapseRate, zoneTemperature, snowCoverFraction
# saturation vapour pressure (FAO 56 Magnus formula): only defined in evaporationPot.py
from cwatm.hydrological_modules.evaporationPot import satVapPress

import importlib


class snow_pysnowclim(object):
    """
    Snow module with the energy balance snow model pySnowClim (usepySnowClim = True).

    Handles the partitioning of precipitation into rain and snow and calculates the snow pack
    (snow water equivalent, pack water, melt, refreezing, sublimation, condensation, deposition)
    with pySnowClim for each snow sample (elevation zone, temperature, dew point, air pressure and
    humidity corrected with the elevation of the zone). The cell values are the means of the samples.
    Based on pySnowClim:
    Lute, A. C., Abatzoglou, J., and Link, T.: SnowClim v1.0: high-resolution snow model and data for the western United States, Geosci. Model Dev.,
    15, 5045–5071, https://doi.org/10.5194/gmd-15-5045-2022
    The frost index is calculated in frost.py.


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
    stopaftersnow                        Flag          stop run after snow calculation -> for snow calibration                 --   
    cropCorrect                          Array         calibration factor of crop KC factor                                    --   
    saveInit                             Flag          If true initial conditions are saved                                    bool 
    minCropKC                            Array         minimum crop factor (default 0.2)                                       --   
    ETRef                                Array         potential evapotranspiration rate from reference crop                   m    
    Precipitation                        Array         Precipitation (input for the model)                                     m    
    Psurf                                Array         surface air pressure                                                    kPa  
    Rsdl                                 Array         long wave downward surface radiation fluxes                             MJ/m2
    huss                                 Array         2 m specific humidity                                                   kg/kg
    rhs                                  Array         relative humidity                                                       %    
    Tdew                                 Array         dew point temperature (map or Magnus formula, FAO 56)                   deg C
    Tavg                                 Array         Input, average air Temperature                                          deg C
    Rsds                                 Array         short wave downward surface radiation fluxes                            MJ/m2
    Wind                                 Array         wind speed at 2 m                                                       m/s  
    WtoMJ                                Number        Conversion factor from [W] to [MJ] for radiation: 86400 * 1E-6          --   
    dzRel                                Array         relative elevation in a gridcell by fraction of area                    m    
    lat                                  Array         Latitude (Tarboton albedo)                                              deg  
    Rain                                 Array         Precipitation less snow (pySnowClim: rain on snow free ground)          m    
    SnowMelt                             Array         snow melt (mean of all layers / samples)                                m    
    IceMelt                              Array         Summer ice melt + snow melted by surplus of higher zones (pySnowClim 0  m    
    snowEvap                             Array         evaporation (sublimation) from snow (mean of all layers / samples)      m    
    SnowCover                            Array         snow cover (mean over all layers / samples)                             m    
    SnowFactor                           Array         Multiplier applied to precipitation that falls as snow                  --   
    _process_forcings_and_energy         Function      pySnowClim: forcings and energy of a time step                          --   
    _run_snowclim_step                   Function      pySnowClim: one time step of the snow pack                              --   
    _prepare_outputs                     Function      pySnowClim: snow model variables -> outputs (mm)                        --   
    Snowpack                             Class         pySnowClim snow pack class                                              --   
    constSnowClim                        Module        pySnowClim constants (e.g. WATERDENS)                                   --   
    stability                            Array         pySnowClim stability setting (Table 2 Lute et al. 2022)                 --   
    windHt                               Array         Wind height (default: 10 meters)                                        m    
    tempHt                               Array         Temperature height (default: 2 meters)                                  m    
    snowoff_month                        Number        Month of snow-off reset (0 = no reset)                                  --   
    snowoff_day                          Number        Day of snow-off reset (default: 1)                                      --   
    albedo_option                        Number        pySnowClim albedo scheme (2 = Tarboton, needs latitude)                 --   
    max_albedo                           Array         Maximum albedo (default: 0.85) (calib: 0.85-0.90) (AI)                  --   
    z_0                                  Array         Roughness length (default: 0.00001 m) (10-5 - 10-3) (AI)                --   
    z_h                                  Array         Roughness length for heat (default: z_0/10) (AI)                        --   
    lw_max                               Array         Maximum liquid water content of the snow pack (default: 0.1)            --   
    Tstart                               Array         Starting temperature (default: 0°C) (AI)                                --   
    Tadd                                 Array         Temperature adjustment (default: -10000°C) (AI)                         --   
    maxtax                               Array         Maximum tax (default: 0.9) (calib: 0.3-0.9) (AI)                        --   
    E0_value                             Array         Windless exchange coefficient (default: 1) (calib  0-2) (AI)            --   
    E0_app                               Array         Windless exchange application option (default: 1) (AI)                  --   
    E0_stable                            Array         Windless exchange stability option (default: 2) (AI)                    --   
    Ts_add                               Array         Temperature add factor (default: 2°C) (calib 0-2) (AI)                  --   
    smooth_time_steps                    Array         Smoothing time steps (default: 12) (calib: 8-24) (AI)                   --   
    ground_albedo                        Array         Ground albedo (default: 0.25) (AI)                                      --   
    snow_emis                            Array         Snow emissivity (default: 0.98) (AI)                                    --   
    snow_dens_default                    Array         Default snow density (default: 250 kg/m³) (AI)                          --   
    G                                    Array         Ground conduction (default: 173/86400 kJ/m²/s) (AI)                     --   
    max_swe_height                       Array         SWE above which downward_radiation_factor is used (snow towers)         m    
    downward_radiation_factor            Array         factor for long wave radiation of snow towers (SWE > max_swe_height)    --   
    downward_radiation_start_month       Number        Month where downward_radiation_factor starts (default: 6)               --   
    downward_radiation_end_month         Number        Month where downward_radiation_factor ends (default: 10)                --   
    snowclimParameters                   Dict          parameter dictionary of pySnowClim                                      --   
    pySnowClimInitVars                   List          snow pack variables saved / loaded as initial conditions                --   
    saveInitpySnowClim                   Flag          If true pySnowClim initial conditions are saved                         bool 
    saveInitFilepySnowClim               String        save file name of the pySnowClim initial conditions                     --   
    SnowFraction                         Array         snow covered fraction of the cell (snowCoverFraction)                   --   
    SnowCoverS                           List          snow cover for each layer / sample                                      m    
    ExistSnow                            Array         fraction of samples with snow (pySnowClim ExistSnow)                    --   
    Rain_on_snow                         Array         rain falling on snow (goes into the snow pack)                          m    
    Snow                                 Array         Snow (equal to a part of Precipitation)                                 m    
    snowSWE                              Array         Snow water equivalent (without pack water), cell mean of the samples    m    
    packwater                            Array         Liquid water in the snow pack, cell mean of the samples                 m    
    snowwaterevaporation                 Array         Evaporation of liquid water from the snow pack, cell mean               m    
    deposition                           Array         Deposition on the snow pack (negative = gain), cell mean                m    
    sublimation                          Array         Sublimation from the snow pack, cell mean                               m    
    condensation                         Array         Condensation on the snow pack (negative = gain), cell mean              m    
    refrozen                             Array         Pack water refrozen to snow (SWE), cell mean                            m    
    snowmelt1                            Array         Snow (SWE) melted to pack water, cell mean                              m    
    precipitation_sn                     Array         CWatM uses a snow undercatch correction if calibrated. This precipitat  m    
    potBareSoilEvap                      Array         potential bare soil evaporation (reduced by the snow covered fraction)  m    
    numberSnowSamples                    Number        Number of pySnowClim snow samples (elevation zones), default 1          --   
    dzZone                               List          elevation offset of each snow zone / sample to the cell median          m    
    dewLapseRate                         Array         dew point lapse rate (default 0.002)                                    K/m  
    snowpackAll                          List          pySnowClim snow pack of each sample                                     --   
    snowModelvarsAll                     List          pySnowClim snow model variables of each sample                          --   
    loadInit                             Flag          If true initial conditions are loaded                                   bool 
    potBareSoilEvapNoSnow                Array         potential bare soil evaporation before the snow reduction               m    
    snowReset                            Array         snow + pack water removed by the snow-off reset (mean of samples)       m    
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize snow module with pySnowClim.

        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initialize the pySnowClim snow module: snow samples (elevation zones), lapse rates,
        pySnowClim parameters and snow packs.

        Notes
        -----
        Key initialization components:
        - Snow sample configuration (NumberSnowSamples, default 1) based on relative elevation data (snowZoneOffsets)
        - Temperature lapse rate setup (constant or variable, loadLapseRate) and dew point lapse rate
        - pySnowClim libraries and parameters (Table 2 in Lute et al. 2022)
        - latitude for the Tarboton albedo (albedo_option = 2)
        - one pySnowClim snow pack per sample, initial conditions from initLoad_pySnowClim
          (one file for all samples: variable name + sample number, e.g. lastswe1, lastswe2 ...)
        """

        # --- Topography -----------------------------------------------------
        # relative elevation dzRel (13 layers 0% ... 100%) is loaded in capillarRise.initial

        # number of snow samples (elevation zones); settings without the key (older files) -> 1 sample
        self.var.numberSnowSamples = 1
        if 'NumberSnowSamples' in binding:
            self.var.numberSnowSamples = int(loadmap('NumberSnowSamples'))
        # elevation offset of each snow sample [m] (zone centres relative to the cell median), computed once
        self.var.dzZone = snowZoneOffsets(self.var.numberSnowSamples, self.var.dzRel)
        # temperature lapse rate (constant or monthly maps)
        loadLapseRate(self.var)

        # dewpoint lapse rate [K/m], positive, ~1/3 of the temperature lapse rate. Used for the snow
        # zones together with the temperature lapse (tdmean, psfc, relhum, huss follow the zone)
        self.var.dewLapseRate = loadmap('DewPointLapseRate') if 'DewPointLapseRate' in binding else 0.002

        # loading snowfactor, a factor to account for snow udercatching when measuring snow
        self.var.SnowFactor = loadmap('SnowFactor')
        # no ice melt in pySnowClim (IceMelt is used in the water balance and in the soil module) -> always 0
        self.var.IceMelt = globals.inZero.copy()

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
        self.var.constSnowClim = importlib.import_module('cwatm.hydrological_modules.pySnowClim.constants')

        # Parameter foor pySnowClim , also calibration parameters
        # see Table2 in https://gmd.copernicus.org/articles/15/5045/2022/gmd-15-5045-2022.html
        self.var.stability = loadmap('stability')  # Stability setting (default: 1)
        self.var.windHt = loadmap('windHt')  # Wind height (default: 10 meters)
        self.var.tempHt = loadmap('tempHt')  # Temperature height (default: 2 meters)
        self.var.snowoff_month = loadmap('snowoff_month')  # Month of snow-off (default: 9)
        self.var.snowoff_day = loadmap('snowoff_day')  # Day of snow-off (default: 1)
        self.var.albedo_option = int(loadmap('albedo_option'))  # Albedo option(default: 2) (calib: 1 or 2))
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

        # parameter dictionary of pySnowClim (the parameters are loaded above one by one, so that each has its own
        # self.var name, as documented in metaNetcdf.xml)
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
            snowfactor = self.var.SnowFactor,)

        # tarboton albedo alg requires latitude
        if self.var.albedo_option == 2:
            try:
                self.var.lat = loadmap('latitude')
            except (CWATMError, CWATMFileError) as e:
                # no latitude map: latitude from the y coordinate of the mask map (cell centres)
                # -> only right for a lat/lon grid, on a projected grid the y coordinate is in m
                rows = maskmapAttr['row']
                cell_size = maskmapAttr['cell']
                yu = maskmapAttr['y']
                yd = yu - rows*cell_size
                latitudes = np.linspace(yu, yd, rows, endpoint=False)
                latitudes = latitudes - cell_size/2
                latitudes_hstack = np.transpose([latitudes]*maskmapAttr['col'])
                self.var.lat = compressArray(latitudes_hstack)
                msg = "Warning: albedo_option = 2 (Tarboton) without a latitude map: latitude is taken from the y " \
                      "coordinate of the mask map"
                if np.max(np.abs(self.var.lat)) > 90.:
                    msg += " - but the y coordinate is not a latitude (projected grid?) -> put latitude in the settings"
                print(CWATMWarning(msg))

        # snow pack variables of pySnowClim which are saved / loaded as initial conditions
        self.var.pySnowClimInitVars = ['lastpacktemp', 'snowage', 'lastalbedo', 'lastswe', 'lastsnowdepth', 'packsnowdensity', 'lastpackcc',
                                       'lastpackwater', 'rain_in_snow']

        # one pySnowClim snow pack and one set of snow model variables per snow sample
        self.var.snowpackAll = [self.var.Snowpack(globals.inZero.shape[0], self.var.snowclimParameters)
                                for _ in range(self.var.numberSnowSamples)]
        self.var.snowModelvarsAll = [SnowModelVariables(globals.inZero.shape[0])
                                for _ in range(self.var.numberSnowSamples)]

        # snow cover of the cell and of each sample [m]: 0 at a cold start (set from the init file below)
        self.var.SnowCover = globals.inZero.copy()
        self.var.SnowCoverS = np.tile(globals.inZero, (self.var.numberSnowSamples, 1))

        # ----------------------------
        # Loading in initial conditions: one file for all samples, variable name + sample number (lastswe1, lastswe2 ...)
        # like SnowCover1, SnowCover2 ... in snow.py; an init file from before the samples has the names without number
        loadInitpySnowClim = False
        if 'load_initial_pySnowClim' in binding:
            loadInitpySnowClim = returnBool('load_initial_pySnowClim')
        if loadInitpySnowClim:
            loadInitFilepySnowClim = cbinding('initLoad_pySnowClim')
            # number of samples in the init file
            nFile = 0
            while readnetcdfInitial(loadInitFilepySnowClim, 'lastswe' + str(nFile + 1), default=None, warn=False) is not None:
                nFile += 1
            numbers = [str(k + 1) for k in range(nFile)] if nFile > 0 else ['']
            if len(numbers) != self.var.numberSnowSamples:
                msg = "Warning: " + loadInitFilepySnowClim + " has " + str(len(numbers)) + " snow samples but NumberSnowSamples = " + \
                      str(self.var.numberSnowSamples) + " -> every sample starts with the mean of the samples in the file"
                print(CWATMWarning(msg))
            for v in self.var.pySnowClimInitVars:
                values = [readnetcdfInitial(loadInitFilepySnowClim, v + k, default=None) for k in numbers]
                # variable missing in init file (warning) -> keep the cold-start value of Snowpack (not a scalar 0)
                if any(value is None for value in values):
                    continue
                for sample in range(self.var.numberSnowSamples):
                    value = values[sample] if len(values) == self.var.numberSnowSamples else np.mean(values, axis=0)
                    snowpack = self.var.snowpackAll[sample]
                    # astype: own copy for each sample, same dtype as pySnowClim (float32)
                    setattr(snowpack, v, value.astype(getattr(snowpack, v).dtype))
            for sample in range(self.var.numberSnowSamples):
                # snow storage [m] of the sample from the loaded snowpack (snowModelvars is only filled in dynamic)
                self.var.SnowCoverS[sample] = self.var.snowpackAll[sample].lastswe + self.var.snowpackAll[sample].lastpackwater
            # cell snow storage before the first time step (e.g. totalSto in landcoverType.initial)
            self.var.SnowCover = np.mean(self.var.SnowCoverS, axis=0)
        elif self.var.loadInit:
            msg = "Warning: load_initial = True but load_initial_pySnowClim = False -> the pySnowClim snow pack starts empty"
            print(CWATMWarning(msg))

        # Saving initial condition
        self.var.saveInitpySnowClim = False
        if 'save_initial_pySnowClim' in binding:
            self.var.saveInitpySnowClim = returnBool('save_initial_pySnowClim')
        if self.var.saveInitpySnowClim:
            self.var.saveInitFilepySnowClim = cbinding('initSave_pySnowClim')


    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------

    def dynamic(self):
        """
        Calculate the snow processes for the current time step with pySnowClim.

        For each snow sample the forcings are corrected for the elevation of the zone, the snow-off
        reset is applied (snowoff_month > 0) and one pySnowClim step is run. The cell values (snow, rain,
        snow melt, snow cover, snow evaporation, snow fraction, snow pack balance terms) are the means of
        the samples. Frost index: frost.py.

        References
        ----------
        Lute, A. C., Abatzoglou, J., and Link, T.: SnowClim v1.0: high-resolution snow model and data for the western United States,
        Geosci. Model Dev., 15, 5045–5071, https://doi.org/10.5194/gmd-15-5045-2022
        """

        # calculate bare soil evap for snowevaporation
        if self.var.stopaftersnow:
            # if it is snow only, we don't care
            self.var.potBareSoilEvap = 0
        else:
            self.var.potBareSoilEvap = self.var.cropCorrect * self.var.minCropKC * self.var.ETRef
        # potential bare soil evaporation before the reduction by snow -> used for potential transpiration (evaporation.py)
        # (otherwise the snow reduction of bare soil evaporation would increase potential transpiration)
        self.var.potBareSoilEvapNoSnow = self.var.potBareSoilEvap    # -> goes to evaporation.py

        # forcings in the units of pySnowClim:
        # lrad - downward longwave radiation (kJ/m2 per time step)
        # tavg - average air temperature (C)
        # ppt - precipitation (m)
        # solar - downward shortwave radiation (kJ/m2 per time step)
        # tdmean  - dewpoint temperature (C)
        # vs - windspeed (m/s)
        # relhum - relative humidity (%)
        # psfc - air pressure (hPa or mb)
        # huss - specific humidity (kg/kg)

        # kPa to hPA
        Psurf = self.var.Psurf * 10

        time_value = [dateVar['currDate'].year, dateVar['currDate'].month, dateVar['currDate'].day]
        # There is only 1 albedo scheme which uses lat. Tavg is passed here
        # only to have the size of the classes correctly.
        if self.var.albedo_option == 2:
            coords = {"lat": self.var.lat}
        else:
            # lat only required with tarboton albedo
            coords = {"lat": self.var.Tavg}

        # forcings which are the same for all samples; the zone values (tavg, tdmean, psfc, relhum, huss) and lrad
        # are set in the loop over the samples
        forcings = {# wind speed: readmeteo converts the 10 m wind to 2 m (* 0.749) -> back to 10 m (windHt)
                    "vs": self.var.Wind/0.749,
                    "ppt": self.var.Precipitation,
                    # Rsds [MJ/m2/day] / WtoMJ -> W/m2, * 3.6 -> kJ/m2/hr, * hours_in_ts -> kJ/m2 per time step
                    "solar": (self.var.Rsds/self.var.WtoMJ)*3.6*self.var.snowclimParameters['hours_in_ts'],
            }

        # Because CWatM handles data differenty and it is daily these
        # values snow_model_instances and index_snowclim are basically
        # unused by pySnowClim.
        snow_model_instances = [None]
        index_snowclim = 0

        # precipitation of each sample: rain/snow partition depends on the zone temperature,
        # so it has to be kept per sample for the aggregation below
        precipAll = [None] * self.var.numberSnowSamples
        # snow-off reset as in pySnowClim (run_snowclim_model): on snowoff_month / snowoff_day every snow pack is set
        # back to an empty snow pack (snowoff_month = 0 -> no reset); the removed snow + pack water [m] (mean of the
        # samples) is booked as snowReset in the water balance (water leaves the model)
        snowOff = self.var.snowoff_month > 0 and time_value[1] == self.var.snowoff_month and \
                  time_value[2] == self.var.snowoff_day
        self.var.snowReset = globals.inZero.copy()

        for sample in range(self.var.numberSnowSamples):

            TavgS = zoneTemperature(self.var, sample, dateVar['currDate'].month - 1)

            # lrad is changed by pySnowClim (snow towers in summer: * downward_radiation_factor) -> new for each sample
            # Rsdl [MJ/m2/day] -> kJ/m2 per time step (as solar)
            forcings['lrad'] = (self.var.Rsdl/self.var.WtoMJ)*3.6*self.var.snowclimParameters['hours_in_ts']

            forcings['tavg'] = TavgS

            # dewpoint, air pressure and humidity belong to the zone too, not to the cell mean:
            # tdmean sets the snow surface temperature (SnowTemp), which drives both the upward
            # longwave and the sensible heat flux. forcings is shared by all samples, so every value
            # is computed from the cell mean again (never from forcings[...] of the previous sample).
            # dzZone > 0 is above the reference zone, so all of them fall with height.
            # The clamp only stops the lapse from creating supersaturation (tavg lapses faster than
            # tdmean); Tdew > Tavg already in the input (~20% of cell-days, because rhs and Tdew are
            # built from the TMin/TMax-averaged ESat) is kept as it is.
            tdmeanS = np.minimum(self.var.Tdew - self.var.dewLapseRate * self.var.dzZone[sample],
                                 TavgS + np.maximum(self.var.Tdew - self.var.Tavg, 0.))
            # scale height R_d * T / g = 29.27 * T[K], using the zone's own temperature
            psfcS = Psurf * np.exp(-self.var.dzZone[sample] / (29.27 * (TavgS + 273.15)))
            # relhum and huss follow tdmean and psfc only by their *relative* change, so CWatM's own
            # rhs/huss are kept at dzZone = 0 (recomputing them from ESat(Tavg) would not match
            # evaporationPot.py). Clip bounds come from the cell value, as rhs itself can exceed 100.
            eRatio = satVapPress(tdmeanS) / satVapPress(self.var.Tdew)
            
            forcings['relhum'] = np.clip(self.var.rhs * (eRatio * (satVapPress(self.var.Tavg) / satVapPress(TavgS))),
                                         np.minimum(1., self.var.rhs), np.maximum(100., self.var.rhs))
            forcings['huss'] = self.var.huss * (eRatio * (Psurf / psfcS))
            forcings['tdmean'] = tdmeanS
            forcings['psfc'] = psfcS
            forcings_data = {"forcings": forcings, "coords": coords}

            # loading necessary data to run the model (precip: partition between snow and rain made by pySnowClim)
            input_forcings, snow_vars, previous_energy, precip = self.var._process_forcings_and_energy(
                index_snowclim, forcings_data, self.var.snowclimParameters, snow_model_instances)

            # snow-off reset: same place as in pySnowClim (after the forcings, before the snow step)
            if snowOff:
                snowpack = self.var.snowpackAll[sample]
                self.var.snowReset += (snowpack.lastswe + snowpack.lastpackwater) / self.var.numberSnowSamples
                self.var.snowpackAll[sample] = self.var.Snowpack(globals.inZero.shape[0], self.var.snowclimParameters)
            self.var.snowpackAll[sample], snow_vars = self.var._run_snowclim_step(
                snow_vars,
                self.var.snowpackAll[sample],
                precip,
                forcings,
                self.var.snowclimParameters,
                coords,
                time_value,
                previous_energy)

            # pySnowClim variables -> CWatM
            self.var.snowModelvarsAll[sample] = self.var._prepare_outputs(snow_vars, precip)
            precipAll[sample] = precip

        # translate pysnowclim -> CWatM
        self.var.ExistSnow = globals.inZero.copy()
        self.var.SnowMelt = globals.inZero.copy()
        self.var.Rain_on_snow = globals.inZero.copy()
        self.var.Rain = globals.inZero.copy()
        self.var.Snow = globals.inZero.copy()
        self.var.SnowCover = globals.inZero.copy()
        self.var.snowEvap = globals.inZero.copy()
        self.var.SnowFraction = globals.inZero.copy()
        # terms of the snow pack water balance, cell means of the samples (WaterBalance output)
        pack = ['snowSWE', 'packwater', 'sublimation', 'condensation', 'deposition', 'snowwaterevaporation',
                'refrozen', 'snowmelt1']
        for name in pack:
            vars(self.var)[name] = globals.inZero.copy()

        no = self.var.numberSnowSamples
        for sample in range(self.var.numberSnowSamples):

            self.var.ExistSnow += self.var.snowModelvarsAll[sample].ExistSnow.copy() / no

            self.var.SnowMelt += (self.var.snowModelvarsAll[sample].Runoff / self.var.constSnowClim.WATERDENS) / no
            # spilt between rain on snow and rain
            # mask and precipitation of THIS sample: ExistSnow is the same mask pySnowClim used to
            # route rain into the pack (SnowpackVariables.update_snowpack_state), so rain booked as
            # rain_on_snow is exactly the rain that came back out as Runoff -> no water is lost
            existSnowS = self.var.snowModelvarsAll[sample].ExistSnow
            self.var.Rain_on_snow += np.where(existSnowS, precipAll[sample].rain, 0) / no
            self.var.Rain += np.where(existSnowS, 0, precipAll[sample].rain) / no
            self.var.Snow += precipAll[sample].sfe / no

            SnowCoverS = ((self.var.snowModelvarsAll[sample].SnowWaterEq +
                                  self.var.snowModelvarsAll[sample].PackWater)
                                  / self.var.constSnowClim.WATERDENS)

            self.var.SnowCover += SnowCoverS / no
            # lost due to sublimation and win through condensation (condesation is negative here)
            snowE = (self.var.snowModelvarsAll[sample].Sublimation +
                                 self.var.snowModelvarsAll[sample].Condensation) / self.var.constSnowClim.WATERDENS
            # Deposition is in m (pySnowClim _prepare_outputs scales all other terms to mm, not Deposition)
            snowE += (self.var.snowModelvarsAll[sample].Deposition * self.var.constSnowClim.WATERDENS
                                  + self.var.snowModelvarsAll[sample].Evaporation) / self.var.constSnowClim.WATERDENS
            self.var.snowEvap += snowE / no
            
            # snow covered fraction of the sample (same thresholds as snow.py, defined in snowCoverFraction)
            self.var.SnowFraction += snowCoverFraction(SnowCoverS) / no

            # snow pack water balance terms [m]: SWE and pack water (storage), sublimation and evaporation of pack
            # water (loss), condensation and deposition (negative = gain), refreezing (pack water -> SWE) and melt
            # (SWE -> pack water); the pack water leaving the pack is SnowMelt
            mv = self.var.snowModelvarsAll[sample]
            # Deposition already in m (see snowE above) -> times WATERDENS, so that all terms are divided the same way
            for name, v in zip(pack, [mv.SnowWaterEq, mv.PackWater, mv.Sublimation, mv.Condensation,
                                      mv.Deposition * self.var.constSnowClim.WATERDENS,
                                      mv.Evaporation, mv.RefrozenWater, mv.SnowMelt]):
                vars(self.var)[name] += (v / self.var.constSnowClim.WATERDENS) / no

        # precipitation including snow undercatch correction (for water balance output): all precipitation, also the
        # rain on snow, which goes into the snow pack (WaterBalance Salzach: without Rain_on_snow error -17 % of P)
        self.var.precipitation_sn = self.var.Snow + self.var.Rain + self.var.Rain_on_snow

        # additional variables to close the waterbalance
        # SnowWaterEq += snow - Sublimation - Condensation   + RefrozenWater - SnowMelt
        # PackWater   += rain_on_snow - Runoff - Evaporation - RefrozenWater + SnowMelt
        # SnowWaterEQ + PackWater = Snow + rain_on_snow - Runoff - Sublimation - Condensation - Evaporation
        # (cell means of these terms for the WaterBalance output: above, in the loop over the samples)

        # bare soil evaporation only from the part of the cell which is not covered by snow
        # (before: 0 for the whole cell if any snow existed at the start of the day)
        self.var.potBareSoilEvap = self.var.potBareSoilEvap * (1 - self.var.SnowFraction)

        #---------------------------------------
        # Saving initial pySnowClim at saving timesteps
        if self.var.saveInitpySnowClim and self.var.saveInit:
            if  dateVar['curr'] in dateVar['intInit']:
                saveFile = (self.var.saveInitFilepySnowClim + "_" + "%02d%02d%02d.nc" %
                            (dateVar['currDate'].year, dateVar['currDate'].month,dateVar['currDate'].day))
                # all samples in one file: variable name + sample number (lastswe1, lastswe2 ...)
                varNames = []
                initVar = []
                for sample in range(self.var.numberSnowSamples):
                    for v in self.var.pySnowClimInitVars:
                        varNames.append(v + str(sample + 1))
                        initVar.append(getattr(self.var.snowpackAll[sample], v))
                writeIniNetcdf(saveFile, varNames, initVar)

