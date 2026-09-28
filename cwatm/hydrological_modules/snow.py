# -------------------------------------------------------------------------
# Name:        Snow module
# Purpose: Snow and frost processes module for precipitation partitioning and snow dynamics.
# Simulates snowfall, snow accumulation, snowmelt, and refreezing processes.
# Handles temperature-based precipitation phase determination and snow water equivalent.
# Snow albedo: one snow albedo per cell from fresh snow, snow age and snow cover,
# used in the radiation part of snow melt (snowmelt_radiation = True)
#
# Author:      PB, MS, SH
# Created:     13/07/2016
# Snow albedo: 15/09/2026
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


import importlib


class snow(object):
    """
    Snow and frost processes module for precipitation partitioning and snow dynamics.
    
    Handles the partitioning of precipitation into rain and snow, calculates snowmelt
    and ice melt using temperature-based and radiation-based approaches, manages snow
    redistribution across elevation zones, and computes frost index for soil freezing.
    Supports multi-layer snow zones for topographic variability representation.

    Snow albedo: one snow age and one snow albedo per cell for all snow layers.
    Fresh snow resets the albedo to the fresh snow albedo, afterwards it decays with
    age towards the old snow albedo; shallow snow is mixed with the ground albedo.
    The resulting surface albedo reduces the short wave radiation in the radiation
    part of snow melt of all layers (only used if snowmelt_radiation = True).
    
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
    snow_redistributed_previous          Array         redistributed snow will be added to next elevation zone in next loop (  --   
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
    useSnowAlbedo                        Flag          True: snow albedo from fresh snow, snow age and snow depth              bool
    snowAlbedoMax                        Array         Albedo of fresh snow Amax (default: 0.85, range 0.80-0.90)              --
    snowAlbedoMin                        Array         Albedo of old snow Amin (default: 0.55, range 0.50-0.60)                --
    snowAlbedoAgingCold                  Array         Daily albedo aging coefficient alpha for T < TempMelt (default: 0.98)   --
    snowAlbedoAgingWarm                  Array         Daily albedo aging coefficient alpha for T >= TempMelt (default: 0.90)  --
    freshSnowThreshold                   Array         Snowfall (SWE) per day that resets albedo and snow age (default 0.001)  m
    snowDensity                          Array         Snow density relative to water to get snow depth (default: 0.3)         --
    snowDepthAlbedo                      Array         Snow depth below which ground shows through (default: 0.15)             m
    groundAlbedo                         Array         Albedo of ground/vegetation under shallow snow (default: 0.20)          --
    noSnowThreshold                      Number        Snow cover (SWE) below which a cell is taken as snow free (1e-6)        m
    SnowAge                              Array         snow age of the cell (days since last fresh snow, 0 without snow)       day
    SnowAlbedo                           Array         snow albedo of the cell (without snow depth correction)                 --
    snowSurfaceAlbedo                    Array         surface albedo used in snow melt of all layers (with depth correction)  --
    SnowWaterEquivalent                  Array         Snow water equivalent, (based on snow density of 450 kg/m3) (e.g. Tarb  --   
    Rain_on_snow                         Array         spilt between rain on snow and rain (AI)                                --   
    Snow                                 Array         Snow (equal to a part of Precipitation)                                 m    
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
        """

        # --- Topography -----------------------------------------------------
        # maps of relative elevation above flood plains -> also used in capilar rise
        #            0             1           2              3           4             5          6           7
        #             8          9             10           11          12
        dzRel = ['dzRel0000','dzRel0001', 'dzRel0005', 'dzRel0010', 'dzRel0020', 'dzRel0030', 'dzRel0040', 'dzRel0050',
                 'dzRel0060', 'dzRel0070', 'dzRel0080', 'dzRel0090', 'dzRel0100']
        self.var.dzRel = []
        for i, item in enumerate(dzRel):
            self.var.dzRel.append(readnetcdfWithoutTime(cbinding('relativeElevation'), item, i))

        self.var.numberSnowLayersFloat = loadmap('NumberSnowLayers')
        self.var.numberSnowLayers = int(self.var.numberSnowLayersFloat)
        # default 0 -> highest zone is transported to middle zone
        self.var.glaciertransportZone = int(loadmap('GlacierTransportZone'))

        # elevation offset of each snow zone [m], computed once
        # of all zone centres -> mean temperature of all zones = Tavg; dzSnow table relative to dzRel[6] (50%)
        pct = [0.0, 0.01, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
        self.var.dzZone = []
        for i in range(self.var.numberSnowLayers):
            # zone 0 is the highest: center at percentile 1 - (i + 0.5) / n
            p = 1.0 - (i + 0.5) / self.var.numberSnowLayers
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

        # loading snowfactor, a factor to account for snow udercatching when measuring snow
        self.var.SnowFactor = loadmap('SnowFactor')

        #min_ElevationStD_snow_redistr = 100
        # 0.46 is the maximum fraction that can be redistributed if snow density is assumed to be 350kg/m3 according to eq. 13 in Frey & Holzmann (2015)
        # this fraction has to be multiplied with the slope, highest slope is 90 degrees
        # the mean slope of each grid cell is the mean of all slopes of the 3'' SRTM DEM
        # the maximum fraction that can be redistributed if snow density is assumed to be 200kg/m3 according to eq. 13 in Frey & Holzmann (2015) is 0.35
        slope_degrees = np.degrees(np.arctan(loadmap('tanslope')))
        self.var.frac_snow_redistribution = np.maximum(0.35 * slope_degrees / 90, globals.inZero)

        # a factor to evaporation assuming higher albedo for snow
        self.var.snowEvapFactor = 0.4
        if 'snowEvapFactor' in binding:
            self.var.snowEvapFactor = loadmap('snowEvapFactor')

        # for snow deposition
        self.var.swe_forest = 0.625
        self.var.swe_other = 0.2
        if 'swe_forest' in binding:
            self.var.swe_forest = loadmap('swe_forest') 
        if 'swe_other' in binding:
            self.var.swe_other = loadmap('swe_other') 

        self.var.SnowDayDegrees = 0.9856
        #to get the seasonal cycle in snow melt coefficient, value is 81 (263) for northern (southern) hemisphere
        if 'SeasonalSnowMeltSin' in binding:
            self.var.SeasonalSnowMeltSin = loadmap('SeasonalSnowMeltSin')

        self.var.redistr_factor = 1.0
        if 'redistribution_factor' in binding:
            self.var.redistr_factor = loadmap('redistribution_factor')
        
        # day of the year to degrees: 360/365.25 = 0.9856
        self.var.summerSeasonStart = 165
        #self.var.IceDayDegrees = 1.915
        self.var.IceDayDegrees = 180./(259- self.var.summerSeasonStart)
        # days of summer (15th June-15th Sept.) to degree: 180/(259-165)
        self.var.SnowSeason = loadmap('SnowSeasonAdj') * 0.5
        # default value of range  of seasonal melt factor is set to 0.001 m C-1 day-1
        # 0.5 x range of sinus function [-1,1]
        self.var.TempSnow = loadmap('TempSnow')

        self.var.SnowMeltCoef = loadmap('SnowMeltCoef')
        self.var.IceMeltCoef = loadmap('IceMeltCoef')

        self.var.TempMelt = loadmap('TempMelt')

        # New snowmelt includes radiation and a calibration factor for radiation
        if 'SnowMeltRad' in binding:
            self.var.SnowMeltRad = loadmap('SnowMeltRad')
        else:
            self.var.SnowMeltRad = 1 + globals.inZero

        # initialize as many snow covers as snow layers -> read them as SnowCover1, SnowCover2 ...
        # SnowCover1 is the highest zone
        self.var.SnowCoverS = []
        for i in range(self.var.numberSnowLayers):
            self.var.SnowCoverS.append(self.var.load_initial("SnowCover",number = i+1))

        # initial snow depth in elevation zones A, B, and C, respectively  [mm]
        self.var.SnowCover = np.sum(self.var.SnowCoverS,axis=0) / self.var.numberSnowLayersFloat + globals.inZero

        # incoming long wave for radiation snow melt: estimated with FAO-56 (as in evaporationPot) if only radiation is
        # given (only_radiation, e.g. EMO) or long wave maps are too coarse (without_rlds; EAct from evaporationPot ->
        # needs calc_evaporation), otherwise measured long wave Rsdl
        self.var.snowFAOlongwave = self.var.without_rlds and (self.var.only_radiation or self.var.calc_evapo)
        # radiation snow melt needs Rsds (and Rsdl) which are not read with PET_modus = 5 (Thornthwaite)
        if self.var.snowmelt_radiation and self.var.pet_modus == 5:
            msg = "Error: snowmelt_radiation = True needs radiation data, but with PET_modus = 5 (Thornthwaite) " \
                  "no radiation is read -> use PET_modus 1-4 or snowmelt_radiation = False"
            raise CWATMError(msg)
        # FAO-56 long wave needs elevation and latitude (loaded in evapopot, but not always evapopot is calculated)
        if self.var.snowFAOlongwave:
            self.var.dem = loadmap('dem')
            self.var.lat = loadmap('latitude')

        # snow albedo: parameters and initial snow age / snow albedo -> see initial_snowalbedo
        self.initial_snowalbedo()


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
        - Snow albedo of the cell from fresh snow, snow age and snow cover (dynamic_snowalbedo)
        - Snow and ice melt calculation with seasonal variations
        - Snow redistribution based on holding capacity and slope
        - Snow fraction calculation for each elevation zone
        
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

        # calculate bare soil evap for snowevaporation
        if self.var.stopaftersnow:
            # if it is snow only that we dont care
            self.var.potBareSoilEvap = 0
        else:
            self.var.potBareSoilEvap = self.var.cropCorrect * self.var.minCropKC * self.var.ETRef
        # potential bare soil evaporation before the reduction by snow -> used for potential transpiration (evaporation.py)
        # (otherwise the snow reduction of bare soil evaporation would increase potential transpiration)
        self.var.potBareSoilEvapNoSnow = self.var.potBareSoilEvap



        # sinus shaped function between the
        # annual minimum (December 21st) and annual maximum (June 21st) for the northern hemisphere
        # annual maximum (December 21st) and annual minimum (June 21st) for the southern hemisphere
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
            # half-year period (2 x SnowDayDegrees) so that the southern window mirrors the northern one; slightly shorter than IceDayDegrees (default branch)

            SummerSeason = np.where((SummerSeason < 0) | (SnowMeltCycle < 0), globals.inZero, SummerSeason)

        else:
            SeasSnowMeltCoef = self.var.SnowSeason * np.sin(math.radians((dateVar['doy'] - 81) * self.var.SnowDayDegrees)) + self.var.SnowMeltCoef
            if (dateVar['doy'] > self.var.summerSeasonStart) and (dateVar['doy'] < 260):
                SummerSeason = np.sin(math.radians((dateVar['doy'] - self.var.summerSeasonStart) * self.var.IceDayDegrees))
            else:
                SummerSeason = 0.0

        self.var.Snow = globals.inZero.copy()
        self.var.Rain = globals.inZero.copy()
        self.var.SnowMelt = globals.inZero.copy()
        self.var.IceMelt = globals.inZero.copy()
        self.var.SnowCover = globals.inZero.copy()
        self.var.snowEvap = globals.inZero.copy()
        self.var.snow_redistributed_previous = globals.inZero.copy()

        # snow melt potential is collected from up the mountain towards valley
        snowIceM_surplus = globals.inZero.copy()
        # snow cover fraction of a gridcell
        self.var.SnowFraction = globals.inZero.copy()

        #get number of elevation zones with forest
        #assume forest is most present at lowest location
        nr_frac_forest = self.var.numberSnowLayers - np.round(self.var.fracVegCover[0] / (1 / self.var.numberSnowLayers)) - 1

        # if only radiation is given like in the EMO meteo dataset (only_radiation) or long wave maps are too coarse
        # (without_rlds): incoming long wave is estimated with FAO-56 (as in evaporationPot)
        if self.var.snowmelt_radiation:
            if self.var.snowFAOlongwave:
                radian = np.pi / 180 * self.var.lat
                distanceSun = 1 + 0.033 * np.cos(2 * np.pi * dateVar['doy'] / 365)
                # Chapter 3: equation 24
                declin = 0.409 * np.sin(2 * np.pi * dateVar['doy'] / 365 - 1.39)
                ws = np.arccos(np.clip(-np.tan(radian) * np.tan(declin), -1.0, 1.0))
                Ra = 24 * 60 / np.pi * 0.082 * distanceSun * (
                        ws * np.sin(radian) * np.sin(declin) + np.cos(radian) * np.cos(declin) * np.sin(ws))
                # Equation 21 Chapter 3
                Rso = Ra * (0.75 + (2 * 10 ** -5 * self.var.dem))  # in MJ/m2/day
                Rso = np.maximum(Rso, 1e-6)  # avoid division by zero in polar night (Ra = 0)
                # Equation 37 Chapter 3
                RsRso = 1.35 * self.var.Rsds / Rso - 0.35
                RsRso = np.minimum(np.maximum(RsRso, 0.05), 1)
                RSNet = (0.34 - 0.14 * np.sqrt(self.var.EAct)) * RsRso
                # Eact in hPa but needed in kPa : kpa = 0.1 * hPa - conversion done in readmeteo

        month = dateVar['currDate'].month - 1

        # temperature and snowfall of each zone, calculated once (used for the snow albedo and in the loop below)
        # i=0 -> highest zone
        TavgZone = []
        SnowZone = []
        for i in range(self.var.numberSnowLayers):
            if self.var.lapseratevar:
                # lapse rate from Dutra et al. 2022 is negative
                TavgS = self.var.Tavg + self.var.lapseR[month] * self.var.dzZone[i]
            else:
                TavgS = self.var.Tavg - self.var.lapseRate * self.var.dzZone[i]
            TavgZone.append(TavgS)
            # Precipitation is assumed to be snow if daily average temperature is below TempSnow
            # Snow is multiplied by correction factor to account for undercatch of snow precipitation (which is common)
            SnowZone.append(np.where(TavgS < self.var.TempSnow, self.var.SnowFactor * self.var.Precipitation, globals.inZero))

        # snow albedo: one albedo for the cell before today's melt -> see dynamic_snowalbedo
        if self.var.useSnowAlbedo:
            self.dynamic_snowalbedo(SnowZone)

        # run through all snow layers
        for i in range(self.var.numberSnowLayers):

            # temperature and snowfall of the zone (calculated once before the loop)
            TavgS = TavgZone[i]
            SnowS = SnowZone[i]
            RainS = np.where(TavgS >= self.var.TempSnow, self.var.Precipitation, globals.inZero)

            # Snow melt with radiation
            # Radiation part from evaporationPot -> snowmelt has now a temperature part and a radiation part
            # from Erlandsen et al. 2021Hydrology Research 1 April 2021; 52 (2): 356–372 https://doi.org/10.2166/nh.2021.132
            if self.var.snowmelt_radiation:
                # outgoing long wave radiation sigma * T^4 (T in K; T^4 as T2 * T2 - faster than ** 4)
                TK = TavgS + 273.15
                TK2 = TK * TK
                RNup = 4.903E-9 * (TK2 * TK2)
                # outgoing long wave of the snow surface: melting snow is at most 0 °C
                TS = np.minimum(TavgS, 0.) + 273.15
                TS2 = TS * TS
                RNsnow = 4.903E-9 * (TS2 * TS2)
                # only_radiation / without_rlds: incoming long wave estimated with FAO-56
                if self.var.snowFAOlongwave:
                    # incoming long wave estimated from FAO-56 net long wave at air temperature: Rsdl = RNup * (1 - RSNet)
                    RLN = RNsnow - RNup * (1 - RSNet)
                else:
                    RLN = RNsnow - self.var.Rsdl
                if self.var.useSnowAlbedo:
                    # snow albedo: only the absorbed part (1 - albedo) of short wave radiation melts snow
                    RN = ((1 - self.var.snowSurfaceAlbedo) * self.var.Rsds - RLN) / 334.0
                else:
                    RN = (self.var.Rsds - RLN) / 334.0
                # latent heat of fusion = 0.334 mJKg-1 * desity of water = 1000 khm-3

                # rain factor: 1% more melt per 1mm rain (Conboy Carter, RainS [m] -> [mm]) - only for the temperature part
                SnowMeltS = ((TavgS - self.var.TempMelt) * SeasSnowMeltCoef * (1 + 0.01 * 1000 * RainS)
                             + self.var.SnowMeltRad * RN) * self.var.DtDay
            else:
                # without radiation
                SnowMeltS = (TavgS - self.var.TempMelt) * SeasSnowMeltCoef * (1 + 0.01 * 1000 * RainS) * self.var.DtDay
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
            # Check if snow+ice not bigger than snowcover
            SnowIceMeltS = np.maximum(np.minimum(SnowMeltS + IceMeltS + snowIceM_surplus, self.var.SnowCoverS[i]), globals.inZero)

            # snowIceM_surplus: melt potential (snow + ice) that finds no snow in this zone is passed down to the next lower zone
            # and added to its own potential -> melts snow collected in lower zones (e.g. by snow redistribution) and mimics
            # snow/glacier transport downhill. The melt caused by it is booked as IceMelt (in mountains most of IceMelt).
            # e.g. Otta 1km 2008: 43% of all melt, 97% of IceMelt; without it the snow does not melt out in summer
            snowIceM_surplus = np.abs(np.minimum(self.var.SnowCoverS[i] - (SnowMeltS + IceMeltS + snowIceM_surplus),0))
            IceMeltS = np.maximum(SnowIceMeltS - SnowMeltS, globals.inZero)
            SnowMeltS = np.maximum(SnowIceMeltS - IceMeltS, globals.inZero)

            self.var.SnowCoverS[i] = self.var.SnowCoverS[i] + SnowS - SnowIceMeltS

            # Snow evaporation
            snowEvap = np.minimum(self.var.SnowCoverS[i], self.var.snowEvapFactor * self.var.potBareSoilEvap)
            self.var.SnowCoverS[i] = self.var.SnowCoverS[i] - snowEvap

            # snow redistribution inspired by Frey and Holzmann (2015) doi:10.5194/hess-19-4517-2015
            # if snow cover higher than snow holding capacity redistribution
            # get the thresholds for the snow based on the snow density and snow depth values in Frey and Holzmann (2015)
            # capacity of forest: 2.5m snow depth, assumed snow density 250kg/m3: 0.25 * 1000 * 2.5 / 1000 = 0.625 m SWE (swe_forest)
            # capacity of other land cover: default swe_other = 0.2 m SWE (= 0.8m snow depth at 250kg/m3;
            #   0.25m snow depth would be only 0.0625 m SWE) - both can be set in the settings file
            # not implemented: "only for cells with std of elevation above 100m"
            # snow capacity depends on whether there is forest cover in the elevation zone (forest assumed in the lowest zones)
            snowcapacity = np.where(i <= nr_frac_forest, self.var.swe_other, self.var.swe_forest)
            # where snow cover is higher than capacity, a fraction (0.35 * slope/90 * reduction_factor) of the WHOLE snow pack
            # is moved to the next lower zone (added there after its melt -> max. one zone per day)
            # works together with snowIceM_surplus above: the snow moved down is mostly melted by the surplus melt potential
            # of the (then snow free) higher zones. e.g. Otta 1km 2008: 171% of snowfall moved, but without redistribution
            # discharge differs < 1% per month (surplus share of melt drops from 43% to 4%)

            # reduction factor: 0 at the lowest zone (no redistribution), increasing to 1 - 1/n at the highest zone (0.9 for 10 zones)
            reduction_factor = self.var.redistr_factor * (1 - (i + 1) / self.var.numberSnowLayers)
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
            self.var.Snow += SnowS
            self.var.Rain += RainS
            self.var.SnowMelt += SnowMeltS
            self.var.IceMelt += IceMeltS
            self.var.SnowCover += self.var.SnowCoverS[i]
            self.var.snowEvap += snowEvap


        # join all layers
        self.var.Snow /= self.var.numberSnowLayersFloat
        self.var.Rain /= self.var.numberSnowLayersFloat
        self.var.SnowMelt /= self.var.numberSnowLayersFloat
        self.var.IceMelt /= self.var.numberSnowLayersFloat
        self.var.SnowCover /= self.var.numberSnowLayersFloat
        self.var.snowEvap /= self.var.numberSnowLayersFloat
        # snow albedo: reset snow age and albedo if the cell is snow free -> see reset_snowalbedo
        if self.var.useSnowAlbedo:
            self.reset_snowalbedo()
        # bare soil evaporation only from the part of the cell which is not covered by snow (same as with pySnowClim)
        self.var.potBareSoilEvap = self.var.potBareSoilEvap * (1 - self.var.SnowFraction)
        self.var.precipitation_sn = self.var.Snow + self.var.Rain



    # --------------------------------------------------------------------------
    # Snow albedo
    # one snow albedo for the cell (all snow layers together) from fresh snow, snow age and snow cover,
    # used in the radiation part of snow melt: (1 - snowSurfaceAlbedo) * Rsds
    # --------------------------------------------------------------------------

    def initial_snowalbedo(self):
        """
        Initialize snow albedo parameters and the initial snow age / snow albedo of the cell.

        Called in initial (part without pySnowClim). useSnowAlbedo = False -> no albedo in
        snow melt (same results as snow_frost.py without albedo). Snow age and snow albedo
        are added to the initial conditions (SnowAge, SnowAlbedo); an init file without them
        starts with age 0 and fresh snow albedo.
        """

        # useSnowAlbedo = False -> no albedo in snow melt (same as snow_frost.py without albedo)
        self.var.useSnowAlbedo = True
        if 'useSnowAlbedo' in binding:
            self.var.useSnowAlbedo = returnBool('useSnowAlbedo')
        # radiation snow melt without snow albedo: the full short wave radiation is used for snow melt
        if self.var.snowmelt_radiation and not self.var.useSnowAlbedo:
            msg = "Warning: snowmelt_radiation = True but useSnowAlbedo = False: snow melt uses the full short wave " \
                  "radiation without snow albedo -> SnowMeltRad has to account for the albedo"
            print(CWATMWarning(msg))
        # snow albedo is only used in radiation snow melt -> not calculated (and not saved) without snowmelt_radiation
        self.var.useSnowAlbedo = self.var.useSnowAlbedo and self.var.snowmelt_radiation
        if not self.var.useSnowAlbedo:
            return

        # fresh snow albedo Amax: 0.80 - 0.90 for clean, dry new snow
        self.var.snowAlbedoMax = 0.85
        if 'snowAlbedoMax' in binding:
            self.var.snowAlbedoMax = loadmap('snowAlbedoMax')
        # old snow albedo Amin: 0.50 - 0.60
        self.var.snowAlbedoMin = 0.55
        if 'snowAlbedoMin' in binding:
            self.var.snowAlbedoMin = loadmap('snowAlbedoMin')
        # daily aging coefficient alpha (0.5 - 0.99) in As(t) = (Amax - Amin) * alpha^t + Amin
        # cold, dry snow ages slowly; melting (wet) snow ages faster (grain growth, impurities)
        self.var.snowAlbedoAgingCold = 0.98
        if 'snowAlbedoAgingCold' in binding:
            self.var.snowAlbedoAgingCold = loadmap('snowAlbedoAgingCold')
        self.var.snowAlbedoAgingWarm = 0.90
        if 'snowAlbedoAgingWarm' in binding:
            self.var.snowAlbedoAgingWarm = loadmap('snowAlbedoAgingWarm')
        # fresh snow threshold as snow water equivalent [m] of snowfall in 24 hours
        # Snew > 0.01 m fresh snow depth at a fresh snow density of 100 kg/m3 -> 0.001 m SWE
        self.var.freshSnowThreshold = 0.001
        if 'freshSnowThreshold' in binding:
            self.var.freshSnowThreshold = loadmap('freshSnowThreshold')
        # snow density relative to water [-] to convert SWE into snow depth: depth = SWE / snowDensity
        self.var.snowDensity = 0.3
        if 'snowDensity' in binding:
            self.var.snowDensity = loadmap('snowDensity')
        # snow depth correction: below snowDepthAlbedo [m] (0.10 - 0.20 m) bare ground or vegetation shows through
        self.var.snowDepthAlbedo = 0.15
        if 'snowDepthAlbedo' in binding:
            self.var.snowDepthAlbedo = loadmap('snowDepthAlbedo')
        # albedo of the ground or vegetation seen through shallow snow
        self.var.groundAlbedo = 0.20
        if 'groundAlbedo' in binding:
            self.var.groundAlbedo = loadmap('groundAlbedo')
        # snow cover [m] below which a cell is taken as snow free (-> next snowfall is fresh snow)
        self.var.noSnowThreshold = 1e-6

        # one snow age [days] and one snow albedo for the cell (all snow layers together)
        # missing in init file -> age 0, fresh snow albedo
        self.var.SnowAge = self.var.load_initial("SnowAge") + globals.inZero
        albedo = self.var.load_initial("SnowAlbedo", default=self.var.snowAlbedoMax) + globals.inZero
        # an init file without SnowAlbedo returns 0 (default of load_initial is only used without load_initial)
        # -> snow albedo is never <= 0: take fresh snow albedo
        self.var.SnowAlbedo = np.where(albedo > 0, albedo, self.var.snowAlbedoMax)
        self.var.snowSurfaceAlbedo = self.var.SnowAlbedo.copy()

        # snow age and snow albedo are saved as initial conditions too
        # (initcondition.initial has filled the list before -> append here)
        globals.initCondVar.append("SnowAge")
        globals.initCondVarValue.append("SnowAge")
        globals.initCondVar.append("SnowAlbedo")
        globals.initCondVarValue.append("SnowAlbedo")

    def dynamic_snowalbedo(self, SnowZone):
        """
        Calculate snow age, snow albedo and surface albedo of the cell before today's melt.

        One value for all snow layers (useSnowAlbedo = True):
        - snowfall = mean snowfall of all layers (each layer with its own temperature),
          snow cover = mean of all layers, aging with the temperature of the cell (Tavg)
        - fresh snow (snowfall > freshSnowThreshold, or any snowfall on a snow free cell):
          snow age t = 0, snow albedo = snowAlbedoMax
        - otherwise aging As(t) = (Amax - Amin) * alpha^t + Amin, calculated as recursion
          As(t) = Amin + (As(t-1) - Amin) * alpha with alpha = snowAlbedoAgingCold (T < TempMelt)
          or snowAlbedoAgingWarm (T >= TempMelt); same as the formula for constant alpha
        - snow depth correction: surface albedo = f * As + (1 - f) * groundAlbedo,
          f = min(1, snow depth / snowDepthAlbedo)
        - the surface albedo reduces the short wave part of radiation snow melt: (1 - albedo) * Rsds

        Parameters
        ----------
        SnowZone : list of arrays
            snowfall [m] of each snow layer (zone temperature below TempSnow), calculated once in dynamic

        References
        ----------
        Warren, S.G. (1982) Optical properties of snow. Rev. Geophys. 20(1), 67-89
        https://opg.optica.org/abstract.cfm?uri=ao-38-18-3869
        https://scholars.unh.edu/cgi/viewcontent.cgi?article=1056&context=ersc
        """

        # snow cover of the cell before today's snowfall and melt
        snowCoverCell = np.sum(self.var.SnowCoverS, axis=0) / self.var.numberSnowLayersFloat
        # snowfall of the cell = mean of the snowfall of each layer (calculated once in dynamic)
        snowCell = globals.inZero.copy()
        for SnowS in SnowZone:
            snowCell += SnowS
        snowCell /= self.var.numberSnowLayersFloat

        # fresh snow: snowfall above threshold, or snow falling on a snow free cell -> age 0, albedo Amax
        freshSnow = (snowCell > self.var.freshSnowThreshold) | ((snowCoverCell <= self.var.noSnowThreshold) & (snowCell > 0))
        # aging coefficient alpha: slow aging for cold dry snow, faster aging for melting (wet) snow
        albedoAging = np.where(self.var.Tavg < self.var.TempMelt, self.var.snowAlbedoAgingCold, self.var.snowAlbedoAgingWarm)
        self.var.SnowAge = np.where(freshSnow, 0., self.var.SnowAge + 1.)
        # As(t) = (Amax - Amin) * alpha^t + Amin as recursion As(t) = Amin + (As(t-1) - Amin) * alpha
        # (identical for constant alpha, allows alpha to change with temperature from day to day)
        self.var.SnowAlbedo = np.where(freshSnow, self.var.snowAlbedoMax,
                self.var.snowAlbedoMin + (self.var.SnowAlbedo - self.var.snowAlbedoMin) * albedoAging)

        # snow depth correction: for shallow snow bare ground or vegetation shows through
        snowDepth = (snowCoverCell + snowCell) / self.var.snowDensity
        fracSnowAlbedo = np.minimum(snowDepth / self.var.snowDepthAlbedo, 1.0)
        # surface albedo of the cell used for all snow layers (ground albedo for a snow free cell)
        self.var.snowSurfaceAlbedo = fracSnowAlbedo * self.var.SnowAlbedo + (1 - fracSnowAlbedo) * self.var.groundAlbedo

    def reset_snowalbedo(self):
        """
        Reset snow age and snow albedo where no snow is left in the cell (next snowfall is fresh snow).

        Called in dynamic after the loop over all snow layers (SnowCover = mean of all layers).
        """
        noSnow = self.var.SnowCover <= self.var.noSnowThreshold
        self.var.SnowAge = np.where(noSnow, 0., self.var.SnowAge)
        self.var.SnowAlbedo = np.where(noSnow, self.var.snowAlbedoMax, self.var.SnowAlbedo)




