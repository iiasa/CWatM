# -------------------------------------------------------------------------
# Name:        Snow module
# Purpose: Snow and frost processes module for precipitation partitioning and snow dynamics.
# Simulates snowfall, snow accumulation, snowmelt, and refreezing processes.
# based on pySnowClim:
# Lute, A. C. et al. (2022)

#
# Author:      PB, MS, SH
# Created:     13/07/2016
# Snow albedo: 15/09/2026
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *



import importlib



def _satVapPress(t):
    """Saturation vapour pressure [kPa] over temperature t [C], FAO56 Magnus as in evaporationPot."""
    return 0.61078 * np.exp(17.27 * t / (237.3 + t))

class snow_pysnowclim(object):
    """
    Snow and frost processes module for precipitation partitioning and snow dynamics.
    
    Handles the partitioning of precipitation into rain and snow, calculates snowmelt
    base on pysnowclim: 
    Lute, A. C., Abatzoglou, J., and Link, T.: SnowClim v1.0: high-resolution snow model and data for the western United States, Geosci. Model Dev.,
    15, 5045–5071, https://doi.org/10.5194/gmd-15-5045-2022

    
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
    stopaftersnow                        Flag          stop run after snow calcualtion -> for snow calibration (AI)            --   
    load_initial                         Flag          Settings initLoad holds initial conditions for variables                bool 
    cropCorrect                          Array         calibration factor of crop KC factor                                    --   
    saveInit                             Flag          If true initial conditions are saved                                    bool 
    minCropKC                            Array         minimum crop factor (default 0.2)                                       --   
    DtDay                                Array         seconds in a timestep (default=86400)                                   s    
    ETRef                                Array         potential evapotranspiration rate from reference crop                   m    
    Precipitation                        Array         Precipitation (input for the model)                                     m    
    only_radiation                       Flag          Boolean if only radiation is use for calculation e.g JRC EMO dataset    bool 
    Psurf                                Array         Instantaneous surface pressure                                          kPa
    Rsdl                                 Array         long wave downward surface radiation fluxes                             MJ/m2/day
    huss                                 Array         2 m istantaneous specific humidity[kg / kg] (AI)                        --   
    EAct                                 Array         Daily vapor pressure                                                    kPa
    rhs                                  Array                                                                                 --   
    Tdew                                 Array         calculate Tdew (Magnus Formula) based on FAO56 https://www.fao.org/4/X  --   
    Tavg                                 Array         Input, average air Temperature                                          °C
    Rsds                                 Array         short wave downward surface radiation fluxes                            MJ/m2/day
    Wind                                 Array         wind speed                                                              m s-1
    snowmelt_radiation                   Array         use radiation term in snow melt (AI)                                    --   
    WtoMJ                                Array         Conversion factor from [W] to [MJ] for radiation: 86400 * 1E-6          --   
    dzRel                                Array         relative elevation in a gridcell by fraction of area                    m    
    usepySnowClim                        Flag          Flag to use pySnowClim                                                  --   
    dem                                  Array         Digital elevation model                                                 m    
    lat                                  Array         Latitude                                                                deg  
    Rain                                 Array         Precipitation less snow                                                 m    
    SnowMelt                             Array         total snow melt from all layers                                         m    
    IceMelt                              Array         Summer ice melt + snow melted by surplus potential of higher zones      m    
    snowEvap                             Array         total evaporation from snow for a snow layers                           m    
    SnowCover                            Array         snow cover (sum over all layers)                                        m    
    SnowFactor                           Array         Multiplier applied to precipitation that falls as snow                  --   
    numberSnowLayers                     Array         Number of snow layers (up to 10)                                        --   
    _process_forcings_and_energy         Flag          load libraries, but only if pySnowClim is used (AI)                     --   
    _run_snowclim_step                   Flag                                                                                  --   
    _prepare_outputs                     Flag                                                                                  --   
    Snowpack                             List                                                                                  --   
    constSnowClim                        Array                                                                                 --   
    stability                            Array         Parameter foor pySnowClim , also calibration parameters see Table2 in   --   
    windHt                               Array         Wind height (default: 10 meters) (AI)                                   --   
    tempHt                               Array         Temperature height (default: 2 meters) (AI)                             --   
    snowoff_month                        Array         Month of snow-off (default: 9) (AI)                                     --   
    snowoff_day                          Array         Day of snow-off (default: 1) (AI)                                       --   
    albedo_option                        Flag                                                                                  --   
    max_albedo                           Array         Maximum albedo (default: 0.85) (calib: 0.85-0.90) (AI)                  --   
    z_0                                  Array         Roughness length (default: 0.00001 m) (10-5 - 10-3) (AI)                --   
    z_h                                  Array         Roughness length for heat (default: z_0/10) (AI)                        --   
    lw_max                               Array                                                                                 --   
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
    max_swe_height                       Array         Max height of SWE before solar radiation factor starts to work (defaul  --   
    downward_radiation_factor            Array                                                                                 --   
    downward_radiation_start_month       Array                                                                                 --   
    downward_radiation_end_month         Array         Month where solar_radiation_factor ends (default: 10) (AI)              --   
    snowclimParameters                   List          then passed is to give clarify using the xml file variables. (AI)       --   
    snowpack                             Array                                                                                 --   
    snowModelvars                        Array         pzSnowclim variables -> CWatM (AI)                                      --   
    pySnowClimInitVars                   List                                                                                  --   
    saveInitpySnowClim                   Flag                                                                                  --   
    saveInitFilepySnowClim               Flag                                                                                  --   
    SnowFraction                         Array         Fraction of snow in a gridcell                                          --   
    numberSnowLayersFloat                Array         Number of snow layers (up to 10)                                        --
    glaciertransportZone                 Number        Number of layers which can be mimiced as glacier transport zone         --   
    dzSnow                               Array         which dzRel is taken for snow calculation                               --   
    lapseratevar                         Flag          True or False if a variable lapse rate is used                          --   
    lapseR                               Array         Lapserate per month                                                     deg C
    lapseRate                            Array         Lapserate per month                                                     deg C
    frac_snow_redistribution             Array          Maximum fraction of snow that can be redistributed in elevation zones  --   
    snowEvapFactor                       Array         a factor to evaporation assuming higher albedo for snow (AI)            --   
    swe_forest                           Array                                                                                 --   
    swe_other                            Array                                                                                 --   
    SnowDayDegrees                       Array         day of the year to degrees: 360/365.25 = 0.9856                         --   
    SeasonalSnowMeltSin                  Array                                                                                 --   
    redistr_factor                       Array                                                                                 --   
    summerSeasonStart                    Array         day when summer season starts = 165                                     --   
    IceDayDegrees                        Array         days of summer (15th June-15th Sept.) to degree: 180/(259-165)          --   
    SnowSeason                           Array         seasonal melt factor                                                    m deg
    TempSnow                             Array         Average temperature at which snow melts                                 °C   
    SnowMeltCoef                         Array         Snow melt coefficient - default: 0.004                                  --   
    IceMeltCoef                          Array         Ice melt coefficnet - default  0.007                                    --   
    TempMelt                             Array         Average temperature at which snow melts                                 °C   
    SnowMeltRad                          Array         calibration value a factor to radiation coefficient                     --   
    SnowCoverS                           Array         snow cover for each layer                                               m    
    freshSnowThreshold                   Array         Snowfall (SWE) per day that resets albedo and snow age (default 0.001)  m
    snowDensity                          Array         Snow density relative to water to get snow depth (default: 0.3)         --
    snowDepthAlbedo                      Array         Snow depth below which ground shows through (default: 0.15)             m
    groundAlbedo                         Array         Albedo of ground/vegetation under shallow snow (default: 0.20)          --
    noSnowThreshold                      Number        Snow cover (SWE) below which a cell is taken as snow free (1e-6)        m
    SnowAge                              Array         snow age of the cell (days since last fresh snow, 0 without snow)       day
    SnowAlbedo                           Array         snow albedo of the cell (without snow depth correction)                 --
    snowSurfaceAlbedo                    Array         surface albedo used in snow melt of all layers (with depth correction)  --
    SnowWaterEquivalent                  Array         Snow water equivalent, (based on snow density of 450 kg/m3) (e.g. Tarb  --   
    ExistSnow                            Array                                                                                 --   
    Rain_on_snow                         Array         spilt between rain on snow and rain (AI)                                --   
    Snow                                 Array         Snow (equal to a part of Precipitation)                                 m    
    packwater                            List                                                                                  --   
    snowwaterevaporation                 Array                                                                                 --   
    depostition                          Array                                                                                 --   
    sublimation                          Array                                                                                 --   
    condensation                         Array                                                                                 --   
    refrozen                             Array                                                                                 --   
    snowmelt1                            Array                                                                                 --   
    precipitation_sn                     Array         CWatM uses a snow undercatch correction if calibrated. This precipitat  m    
    potBareSoilEvap                      Array         potential bare soil evaporation (reduced by the snow covered fraction)  m    
    fracVegCover                         Array         Fraction of specific land covers (0=forest, 1=grasslands, etc.)         %    
    cellArea                             Array         Area of cell                                                            m2   
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
        - Snow albedo parameters and initial snow age / snow albedo of the cell (initial_snowalbedo)
        - Frost index parameters for soil freezing calculations
        """

        # --- Topography -----------------------------------------------------
        # Same as in snow.py! Just the numberSnowLayers is replaced by numberSnowSamples
        # maps of relative elevation above flood plains -> also used in capilar rise
        #             0             1           2              3           4             5          6          
        #             8          9             10           11          12
        dzRel = ['dzRel0001', 'dzRel0005', 'dzRel0010', 'dzRel0020', 'dzRel0030', 'dzRel0040', 'dzRel0050',
                 'dzRel0060', 'dzRel0070', 'dzRel0080', 'dzRel0090', 'dzRel0100']
        self.var.dzRel = []
        for i, item in enumerate(dzRel):
            self.var.dzRel.append(readnetcdfWithoutTime(cbinding('relativeElevation'), item, i))

        self.var.numberSnowSamples = int(loadmap('NumberSnowSamples'))
        # default 0 -> highest zone
        # elevation offset of each snow zone [m], computed once
        # of all zone centres -> mean temperature of all zones = Tavg; dzSnow table relative to dzRel[6] (50%)
        pct = [0.0, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
        self.var.dzZone = []
        for i in range(self.var.numberSnowSamples):
            # zone 0 is the highest: center at percentile 1 - (i + 0.5) / n
            p = 1.0 - (i + 0.5) / self.var.numberSnowSamples
            j = int(min(max(np.searchsorted(pct, p+0.000001)-1, 0), 10))
            # w: weight for w * (x[j+1] - x[j])
            w = (p - pct[j]) / (pct[j + 1] - pct[j])
            self.var.dzZone.append(self.var.dzRel[j] + w * (self.var.dzRel[j + 1] - self.var.dzRel[j]))

        self.var.dzZone = [dz - self.var.dzRel[6] for dz in self.var.dzZone]

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

        # dewpoint lapse rate [K/m], positive, ~1/3 of the temperature lapse rate. Used for the snow
        # zones together with the temperature lapse (tdmean, psfc, relhum, huss follow the zone)
        self.var.dewLapseRate = loadmap('DewPointLapseRate') if 'DewPointLapseRate' in binding else 0.002

        # loading snowfactor, a factor to account for snow udercatching when measuring snow
        self.var.SnowFactor = loadmap('SnowFactor')
        # not use in pysnowclim (but used in watercycles)
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
        #import cwatm.hydrological_modules.pySnowClim.constants as const
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
            snowfactor = self.var.SnowFactor,)

        # tarboton albedo alg requires latitude
        if self.var.albedo_option == 2:
            try:
                self.var.lat = loadmap('latitude')
            except (CWATMError, CWATMFileError) as e:
                rows = maskmapAttr['row']
                cell_size = maskmapAttr['cell']
                yu = maskmapAttr['y']
                yd = yu - rows*cell_size
                latitudes = np.linspace(yu, yd, rows, endpoint=False)
                latitudes = latitudes - cell_size/2
                latitudes_hstack = np.transpose([latitudes]*maskmapAttr['col'])
                self.var.lat = compressArray(latitudes_hstack)

        self.var.pySnowClimInitVars = ['lastpacktemp', 'snowage', 'lastalbedo', 'lastswe', 'lastsnowdepth', 'packsnowdensity', 'lastpackcc',
                                       'lastpackwater', 'rain_in_snow']

        #self.var.snowpack = self.var.Snowpack(globals.inZero.shape[0], self.var.snowclimParameters)
        #self.var.snowModelvars = SnowModelVariables(globals.inZero.shape[0])
        self.var.snowpackAll = [self.var.Snowpack(globals.inZero.shape[0], self.var.snowclimParameters)
                                for _ in range(self.var.numberSnowSamples)]
        self.var.snowModelvarsAll = [SnowModelVariables(globals.inZero.shape[0])
                                for _ in range(self.var.numberSnowSamples)]

        # snow fraction: 0 at start, calculated in dynamic from SnowCover
        self.var.SnowCover = globals.inZero.copy()
        self.var.SnowCoverS = np.tile(globals.inZero, (self.var.numberSnowSamples, 1))

        # ----------------------------
        # Loading in initial conditions
        if returnBool('load_initial_pySnowClim'):
            loadInitFilepySnowClim = cbinding('initLoad_pySnowClim')
            for samples in range(self.var.numberSnowSamples):
                for v in self.var.pySnowClimInitVars:
                    # variable missing in init file -> keep the cold-start value of Snowpack (not a scalar 0)
                    var = readnetcdfInitial(loadInitFilepySnowClim+str(samples), v, default=None)
                    if var is not None:
                        setattr(self.var.snowpackAll[samples], v, var)

                #self.var.SnowCover = self.var.snowModelvars.SnowWaterEq / self.var.constSnowClim.WATERDENS  # replace 9/2026
                # snowModelvars is only filled in dynamic -> take snow storage [m] directly from the loaded snowpack
                self.var.SnowCoverS[samples] = (self.var.snowpack[samples].lastswe +
                                                self.var.snowpack[samples].lastpackwater)

        # Saving initial condition
        self.var.saveInitpySnowClim = returnBool('save_initial_pySnowClim')
        if self.var.saveInitpySnowClim:
            self.var.saveInitFilepySnowClim = cbinding('initSave_pySnowClim')


    # --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Calculate snow and frost processes for current time step.

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


        #if self.var.usepySnowClim:
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

        # kPa to hPA
        Psurf = self.var.Psurf.copy() * 10
        #pressure_with_units = (Psurf) * units('hPa')
        #dewpoint_with_units = (self.var.Tdew) * units('degC')

        time_value = [dateVar['currDate'].year, dateVar['currDate'].month, dateVar['currDate'].day]
        # There is only 1 albedo scheme which uses lat. Tavg is passed here
        # only to have the size of the classes correctly.
        if self.var.albedo_option == 2:
            coords = {"lat": self.var.lat}
        else:
            # lat only required with tarboton albedo
            coords = {"lat": self.var.Tavg}

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

        # Because CWatM handles data differenty and it is daily these
        # values snow_model_instances and index_snowclim are basically
        # unused by pySnowClim.
        snow_model_instances = [None]
        index_snowclim = 0

        # precipitation of each sample: rain/snow partition depends on the zone temperature,
        # so it has to be kept per sample for the aggregation below
        precipAll = [None] * self.var.numberSnowSamples

        for sample in range(self.var.numberSnowSamples):

            if self.var.lapseratevar:
                # lapse rate from Dutra et al. 2022 is negative
                TavgS = self.var.Tavg + self.var.lapseR[dateVar['currDate'].month - 1] * self.var.dzZone[sample]
            else:
                TavgS = self.var.Tavg - self.var.lapseRate * self.var.dzZone[sample]
                
            # solar or lrad or both are changed during the process
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
            eRatio = _satVapPress(tdmeanS) / _satVapPress(self.var.Tdew)
            
            forcings['relhum'] = np.clip(self.var.rhs * (eRatio * (_satVapPress(self.var.Tavg) / _satVapPress(TavgS))),
                                         np.minimum(1., self.var.rhs), np.maximum(100., self.var.rhs))
            forcings['huss'] = self.var.huss * (eRatio * (Psurf / psfcS))
            forcings['tdmean'] = tdmeanS
            forcings['psfc'] = psfcS
            #forcings['tavg'] = self.var.Tavg
            forcings_data = {"forcings": forcings, "coords": coords}

            # loading necessary data to run the model
            input_forcings, snow_vars, previous_energy, precip = self.var._process_forcings_and_energy(
                index_snowclim, forcings_data, self.var.snowclimParameters, snow_model_instances)
            # partition between snow and rain made by snowclim
            #Snow = precip.sfe.copy()
            #Rain = precip.rain.copy()

            # snow and pack water removed by the reset [m] -> reported as snowReset (water leaves the model)
            """
            self.var.snowReset = globals.inZero.copy()
            if self.var.snowoff_month > 0:
                if time_value[1] == self.var.snowoff_month and time_value[2] == self.var.snowoff_day:
                    self.var.snowReset = self.var.snowpack.lastswe + self.var.snowpack.lastpackwater
                    #self.var.snowpack = self.var.Snowpack(globals.inZero.shape[0], self.var.snowclimParameters)
            """
            self.var.snowpackAll[sample], snow_vars = self.var._run_snowclim_step(
                snow_vars,
                self.var.snowpackAll[sample],
                precip,
                forcings,
                self.var.snowclimParameters,
                coords,
                time_value,
                previous_energy)

            ## pzSnowclim variables -> CWatM
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
            snowE += (self.var.snowModelvarsAll[sample].Deposition
                                  + self.var.snowModelvarsAll[sample].Evaporation) / self.var.constSnowClim.WATERDENS
            self.var.snowEvap += snowE / no
            
            SnowFractionS = np.where(SnowCoverS > 0.01, 0.25 / no, 0.)
            SnowFractionS = np.where(SnowCoverS > 0.05, 0.5 / no, SnowFractionS)
            SnowFractionS = np.where(SnowCoverS > 0.10, 1.0 / no, SnowFractionS)
            self.var.SnowFraction += SnowFractionS
            
            
            
            
            
        # precipitation including snow undercatch correction (for water balance output)
        self.var.precipitation_sn = self.var.Snow + self.var.Rain  # + self.var.Rain_on_snow # -> I am not sure if this is added for total precipitation

        # additional variables to close the waterbalance
        # SnowWaterEq += snow - Sublimation - Condensation   + RefrozenWater - SnowMelt
        # PackWater   += rain_on_snow - Runoff - Evaporation - RefrozenWater + SnowMelt
        # SnowWaterEQ + PackWater = Snow + rain_on_snow - Runoff - Sublimation - Condensation - Evaporation

        """
        # This one is for watercycle output only
        self.var.packwater = self.var.snowModelvars.PackWater / self.var.constSnowClim.WATERDENS
        self.var.snowwaterevaporation = self.var.snowModelvars.Evaporation / self.var.constSnowClim.WATERDENS
        self.var.depostition = self.var.snowModelvars.Deposition / self.var.constSnowClim.WATERDENS
        self.var.sublimation = self.var.snowModelvars.Sublimation / self.var.constSnowClim.WATERDENS
        self.var.condensation = self.var.snowModelvars.Condensation / self.var.constSnowClim.WATERDENS

        self.var.refrozen = self.var.snowModelvars.RefrozenWater / self.var.constSnowClim.WATERDENS
        self.var.snowmelt1 = self.var.snowModelvars.SnowMelt / self.var.constSnowClim.WATERDENS
        # ----------
        """

        # bare soil evaporation only from the part of the cell which is not covered by snow
        # (before: 0 for the whole cell if any snow existed at the start of the day)
        self.var.potBareSoilEvap = self.var.potBareSoilEvap * (1 - self.var.SnowFraction)

        #---------------------------------------
        # Saving initial pySnowClim at saving timesteps
        if self.var.saveInitpySnowClim and self.var.saveInit:
            if  dateVar['curr'] in dateVar['intInit']:
                saveFile = (self.var.saveInitFilepySnowClim + "_" + "%02d%02d%02d.nc" %
                            (dateVar['currDate'].year, dateVar['currDate'].month,dateVar['currDate'].day))
                initVar = []
                #var_dict = {k : v for k, v in vars(self.var.snowpack).items() if k in self.var.pySnowClimInitVars}
                #np.savez_compressed(saveFile, **var_dict)

                for v in self.var.pySnowClimInitVars:
                    initVar.append(getattr(self.var.snowpack, v))
                writeIniNetcdf(saveFile, self.var.pySnowClimInitVars, initVar)

