# -------------------------------------------------------------------------
# Name:        Snow module
# Purpose: Snow module (degree-day approach) for precipitation partitioning and snow dynamics.
# Simulates snowfall, snow accumulation, snow and ice melt, snow evaporation and snow redistribution
# in elevation zones (snow layers). Frost index: frost.py, energy balance snow model: snow_pysnowclim.py
# Snow albedo: one snow albedo per cell from fresh snow, snow age and snow cover,
# used in the radiation part of snow melt (snowmelt_radiation = True)
# Shared functions (also used by snow_pysnowclim.py): snowZoneOffsets, loadLapseRate, zoneTemperature,
# snowCoverFraction
#
# Author:      PB, MS, SH
# Created:     13/07/2016
# Snow albedo: 15/09/2026
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


# --------------------------------------------------------------------------
# Functions used by both snow modules (snow.py and snow_pysnowclim.py) - only defined here
# --------------------------------------------------------------------------

def snowZoneOffsets(number, dzRel):
    """
    Elevation offset [m] of the centre of each snow zone (snow layer / snow sample) relative to the cell median.

    The zones divide the elevation distribution of the cell into equal areas; zone 0 is the highest.
    The centre of zone i is the percentile 1 - (i + 0.5) / number, linearly interpolated in the
    13 percentiles of dzRel (0%, 1%, 5%, 10%, ... 90%, 100%), relative to dzRel[7] (50%).

    Parameters
    ----------
    number : int
        number of snow zones
    dzRel : list of arrays
        relative elevation of the 13 percentiles [m] (loaded in capillarRise.initial)

    Returns
    -------
    list of arrays
        elevation offset of each zone [m] (positive = above the median)
    """
    pct = [0.0, 0.01, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
    dzZone = []
    for i in range(number):
        # zone 0 is the highest: center at percentile 1 - (i + 0.5) / n
        p = 1.0 - (i + 0.5) / number
        # interval j: pct[j] <= p < pct[j+1], j = 0..11
        j = int(min(max(np.searchsorted(pct, p+0.000001)-1, 0), 11))
        # w: weight for w * (x[j+1] - x[j])
        w = (p - pct[j]) / (pct[j + 1] - pct[j])
        dzZone.append(dzRel[j] + w * (dzRel[j + 1] - dzRel[j]))
    return [dz - dzRel[7] for dz in dzZone]


def loadLapseRate(var):
    """
    Load the temperature lapse rate: constant (TemperatureLapseRate, positive) or, with LapseRateVariable = True,
    12 monthly maps (LapseRate, from Dutra et al. 2022 global 0.25 deg, negative values)
    https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2019ea000984

    Parameters
    ----------
    var : object
        model variables (sets var.lapseratevar and var.lapseR or var.lapseRate)
    """
    var.lapseratevar = False
    if 'LapseRateVariable' in binding:
        var.lapseratevar = returnBool('LapseRateVariable')
    if var.lapseratevar:
        var.lapseR = []
        for i in range(12):
            var.lapseR.append(readnetcdf12month(cbinding('LapseRate'), i))
    else:
        var.lapseRate = loadmap('TemperatureLapseRate')


def zoneTemperature(var, i, month):
    """
    Average air temperature [deg C] of snow zone i: cell temperature corrected with the lapse rate and the
    elevation offset of the zone (var.dzZone).

    Parameters
    ----------
    var : object
        model variables (Tavg, dzZone, lapseratevar, lapseR / lapseRate)
    i : int
        snow zone (0 = highest)
    month : int
        month of the year 0..11 (for the monthly lapse rate)

    Returns
    -------
    array
        temperature of the zone [deg C]
    """
    if var.lapseratevar:
        # monthly lapse rate (Dutra et al.) is negative
        return var.Tavg + var.lapseR[month] * var.dzZone[i]
    return var.Tavg - var.lapseRate * var.dzZone[i]


def snowCoverFraction(snowCover):
    """
    Snow covered fraction of one snow layer (snow.py) or one snow sample (snow_pysnowclim.py) from its snow cover.
    The only place where the thresholds are defined (used by both snow modules).

    Parameters
    ----------
    snowCover : array
        snow cover (SWE) of the layer / sample [m]

    Returns
    -------
    array
        snow covered fraction [-]: <= 0.02 m -> 0 (no snow), > 0.02 m -> 0.25, > 0.05 m -> 0.5, > 0.10 m -> 1
    """
    sfrac = np.where(snowCover > 0.02, 0.25, 0.)
    sfrac = np.where(snowCover > 0.05, 0.5, sfrac)
    return np.where(snowCover > 0.10, 1.0, sfrac)


class snow(object):
    """
    Snow module (degree-day approach) for precipitation partitioning and snow dynamics.

    Handles the partitioning of precipitation into rain and snow, calculates snowmelt
    and ice melt using temperature-based and radiation-based approaches, snow evaporation
    and snow redistribution across elevation zones. Supports multi-layer snow zones
    (1-10 snow layers) for topographic variability representation.
    The frost index is calculated in frost.py, the energy balance snow model in snow_pysnowclim.py.

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
    stopaftersnow                        Flag          stop run after snow calculation -> for snow calibration                 --   
    load_initial                         Function      load an initial condition from the init file (initLoad)                 --   
    cropCorrect                          Array         calibration factor of crop KC factor                                    --   
    minCropKC                            Array         minimum crop factor (default 0.2)                                       --   
    DtDay                                Array         seconds in a timestep (default=86400)                                   s    
    ETRef                                Array         potential evapotranspiration rate from reference crop                   m    
    Precipitation                        Array         Precipitation (input for the model)                                     m    
    Rsdl                                 Array         long wave downward surface radiation fluxes                             MJ/m2
    longwaveFactor                       Array         FAO 56 net long wave factor EmNet * RsRso (from evaporationPot)         --   
    Tavg                                 Array         Input, average air Temperature                                          deg C
    Rsds                                 Array         short wave downward surface radiation fluxes                            MJ/m2
    snowmelt_radiation                   Flag          use radiation term in snow melt                                         bool 
    dzRel                                Array         relative elevation in a gridcell by fraction of area                    m    
    snowFAOlongwave                      Flag          radiation snow melt: incoming long wave estimated with FAO 56           bool 
    Rain                                 Array         Precipitation less snow (pySnowClim: rain on snow free ground)          m    
    SnowMelt                             Array         snow melt (mean of all layers / samples)                                m    
    IceMelt                              Array         Summer ice melt + snow melted by surplus of higher zones (pySnowClim 0  m    
    snowEvap                             Array         evaporation (sublimation) from snow (mean of all layers / samples)      m    
    SnowCover                            Array         snow cover (mean over all layers / samples)                             m    
    SnowFactor                           Array         Multiplier applied to precipitation that falls as snow                  --   
    numberSnowLayers                     Number        Number of snow layers (up to 10)                                        --   
    SnowFraction                         Array         snow covered fraction of the cell (snowCoverFraction)                   --   
    snow_redistributed_previous          Array         snow redistributed from the next higher zone                            m    
    numberSnowLayersFloat                Number        Number of snow layers as float                                          --   
    glaciertransportZone                 Number        zones 0..n with ice melt of the cell temperature (glacier transport)    --   
    lapseratevar                         Flag          True or False if a variable (monthly) lapse rate is used                bool 
    lapseR                               List          monthly lapse rate maps (Dutra et al., negative)                        C/m  
    lapseRate                            Array         constant temperature lapse rate (positive)                              C/m  
    frac_snow_redistribution             Array          Maximum fraction of snow that can be redistributed in elevation zones  --   
    snowEvapFactor                       Array         a factor to evaporation assuming higher albedo for snow (AI)            --   
    swe_forest                           Array         snow holding capacity of forest zones (SWE, default 0.625)              m    
    swe_other                            Array         snow holding capacity of other zones (SWE, default 0.2)                 m    
    SnowDayDegrees                       Array         day of the year to degrees: 360/365.25 = 0.9856                         --   
    SeasonalSnowMeltSin                  Array         day of the year of the sinus of the melt coefficient (81 N, 263 S)      day  
    redistr_factor                       Array         factor for the snow redistribution (default 1)                          --   
    summerSeasonStart                    Array         day when summer season starts = 165                                     --   
    IceDayDegrees                        Array         days of summer (15th June-15th Sept.) to degree: 180/(259-165)          --   
    SnowSeason                           Array         seasonal melt factor                                                    m deg
    TempSnow                             Array         Average temperature below which precipitation is snow                   deg C
    SnowMeltCoef                         Array         Snow melt coefficient - default: 0.004                                  --   
    IceMeltCoef                          Array         Ice melt coefficient - default 0.007                                    --   
    TempMelt                             Array         Average temperature at which snow melts                                 deg C
    SnowMeltRad                          Array         calibration value a factor to radiation coefficient                     --   
    SnowCoverS                           List          snow cover for each layer / sample                                      m    
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
    Snow                                 Array         Snow (equal to a part of Precipitation)                                 m    
    precipitation_sn                     Array         CWatM uses a snow undercatch correction if calibrated. This precipitat  m    
    potBareSoilEvap                      Array         potential bare soil evaporation (reduced by the snow covered fraction)  m    
    fracVegCover                         Array         Fraction of specific land covers (0=forest, 1=grasslands, etc.)         %    
    dzZone                               List          elevation offset of each snow zone / sample to the cell median          m    
    loadInit                             Flag          If true initial conditions are loaded                                   bool 
    pet_modus                            Number        method of potential evapotranspiration (1-5)                            --   
    potBareSoilEvapNoSnow                Array         potential bare soil evaporation before the snow reduction               m    
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize snow module.

        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initialize snow module parameters and elevation zones.

        Loads parameters for the day-degree approach for precipitation partitioning,
        snowmelt, and ice melt calculations. Sets up multiple elevation zones for
        representing topographic variability and initializes snow cover distributions.

        Notes
        -----
        Key initialization components:
        - Elevation zone configuration (1-10 zones) based on relative elevation data (snowZoneOffsets)
        - Temperature lapse rate setup (constant or variable, loadLapseRate)
        - Snow redistribution parameters based on slope and land cover
        - Seasonal snow melt coefficient parameters
        - Initial snow cover distribution across elevation zones
        - Snow albedo parameters and initial snow age / snow albedo of the cell (initial_snowalbedo)
        """

        # --- Topography -----------------------------------------------------
        # relative elevation dzRel (13 layers 0% ... 100%) is loaded in capillarRise.initial

        self.var.numberSnowLayersFloat = loadmap('NumberSnowLayers')
        self.var.numberSnowLayers = int(self.var.numberSnowLayersFloat)
        # ice melt of the zones 0 .. glaciertransportZone is calculated with the cell temperature (mimics glacier
        # transport to lower zones); default 0 -> only the highest zone
        self.var.glaciertransportZone = int(loadmap('GlacierTransportZone'))

        # elevation offset of each snow zone [m] (zone centres relative to the cell median), computed once
        self.var.dzZone = snowZoneOffsets(self.var.numberSnowLayers, self.var.dzRel)
        # temperature lapse rate (constant or monthly maps)
        loadLapseRate(self.var)

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

        # New snowmelt includes radiation and a calibration factor for radiation (only used with snowmelt_radiation)
        if self.var.snowmelt_radiation:
            if 'SnowMeltRad' not in binding:
                msg = "Error 176: snowmelt_radiation = True needs SnowMeltRad (calibration factor of the radiation " \
                      "snow melt, with snow albedo about 1.0) in the settings file\n"
                raise CWATMError(msg)
            self.var.SnowMeltRad = loadmap('SnowMeltRad')

        # initialize as many snow covers as snow layers -> read them as SnowCover1, SnowCover2 ...
        # SnowCover1 is the highest zone
        self.var.SnowCoverS = []
        nFile = self.var.numberSnowLayers
        if self.var.loadInit:
            # number of snow layers in the init file
            nFile = 0
            while self.var.load_initial("SnowCover", default=None, number=nFile + 1, warn=False) is not None:
                nFile += 1
        if nFile == self.var.numberSnowLayers:
            for i in range(self.var.numberSnowLayers):
                self.var.SnowCoverS.append(self.var.load_initial("SnowCover",number = i+1))
        else:
            # different number of snow layers in the init file: every layer gets the cell mean of the file layers (keeps the water)
            msg = "Warning: init file has " + str(nFile) + " snow layers (SnowCover1 ...) but NumberSnowLayers = " + \
                  str(self.var.numberSnowLayers) + " -> every snow layer starts with the cell mean of the file"
            print(CWATMWarning(msg))
            meanSnow = np.mean([self.var.load_initial("SnowCover", number=k + 1) for k in range(nFile)], axis=0) if nFile > 0 else 0.0
            for i in range(self.var.numberSnowLayers):
                self.var.SnowCoverS.append(meanSnow + globals.inZero)

        # initial snow cover of the cell = mean of all snow layers [m]
        self.var.SnowCover = np.sum(self.var.SnowCoverS,axis=0) / self.var.numberSnowLayersFloat + globals.inZero

        # incoming long wave for radiation snow melt: estimated with FAO-56 if only radiation is given
        # (only_radiation, e.g. EMO) or long wave maps are too coarse (without_rlds), otherwise measured long wave Rsdl
        # -> flag snowFAOlongwave and the FAO-56 factor longwaveFactor are set in evaporationPot (runs before)
        # radiation snow melt needs Rsds (and Rsdl) which are not read with PET_modus = 5 (Thornthwaite)
        if self.var.snowmelt_radiation and self.var.pet_modus == 5:
            msg = "Error: snowmelt_radiation = True needs radiation data, but with PET_modus = 5 (Thornthwaite) " \
                  "no radiation is read -> use PET_modus 1-4 or snowmelt_radiation = False"
            raise CWATMError(msg)

        # snow albedo: parameters and initial snow age / snow albedo -> see initial_snowalbedo
        self.initial_snowalbedo()


    # --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Calculate snow processes for current time step.

        Performs precipitation partitioning into rain and snow based on temperature
        thresholds, computes snowmelt and ice melt using temperature-index and
        radiation-based approaches, snow evaporation and snow redistribution between
        elevation zones (frost index: frost.py).

        Notes
        -----
        The method processes each elevation zone sequentially and handles:
        - Temperature correction based on elevation and lapse rate (zoneTemperature)
        - Precipitation partitioning using temperature thresholds
        - Snow albedo of the cell from fresh snow, snow age and snow cover (dynamic_snowalbedo)
        - Snow and ice melt calculation with seasonal variations
        - Snow redistribution based on holding capacity and slope
        - Snow fraction calculation for each elevation zone (snowCoverFraction)

        References
        ----------
        Snow melt equations modified from:
        Speers, D.D., Versteeg, J.D. (1979) Runoff forecasting for reservoir
        operations - the past and the future. In: Proceedings 52nd Western
        Snow Conference, 149-156

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

        month = dateVar['currDate'].month - 1

        # temperature and snowfall of each zone, calculated once (used for the snow albedo and in the loop below)
        # i=0 -> highest zone
        TavgZone = []
        SnowZone = []
        for i in range(self.var.numberSnowLayers):
            TavgS = zoneTemperature(self.var, i, month)
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
                    # incoming long wave estimated from FAO-56 net long wave at air temperature:
                    # Rsdl = RNup * (1 - longwaveFactor), longwaveFactor = EmNet * RsRso from evaporationPot.fao_longwave
                    RLN = RNsnow - RNup * (1 - self.var.longwaveFactor)
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

            # for the zones 0 .. glaciertransportZone the ice melt is calculated with the cell temperature Tavg,
            # for the others with the zone temperature
            # this is to mimic glacier transport to lower zones
            if i <= self.var.glaciertransportZone:
                IceMeltS = self.var.Tavg * self.var.IceMeltCoef * self.var.DtDay * SummerSeason
                # default GlacierTransportZone = 0 -> only the highest zone
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

            # calculation of snow fraction in each elevation band (thresholds in snowCoverFraction)
            sfrac = snowCoverFraction(self.var.SnowCoverS[i])

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
        # an init file without SnowAlbedo returns the default (fresh snow albedo); a saved value <= 0 is not possible
        # for snow -> take fresh snow albedo
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




