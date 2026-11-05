# -------------------------------------------------------------------------
# Name:        POTENTIAL REFERENCE EVAPO(TRANSPI)RATION
# Purpose: Potential evapotranspiration calculation using multiple meteorological methods.
# Implements reference evapotranspiration formulas including Penman-Monteith approach.
# Provides baseline atmospheric water demand for actual evapotranspiration calculations.
#
# Author:      PB, MS
# Created:     10/01/2017
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


def satVapPress(t):
    """
    Saturation vapour pressure [kPa] at temperature t [deg C], FAO 56 equation 11 (Magnus formula)
    http://www.fao.org/docrep/X0490E/x0490e07.htm
    The only definition in CWatM (used by evaporationPot.py and snow_pysnowclim.py).
    """
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def dewPointTemp(e):
    """
    Dew point temperature [deg C] from the actual vapour pressure e [kPa]: inverse of satVapPress
    """
    logE = np.log(e / 0.6108)
    return logE * 237.3 / (17.27 - logE)


class evaporationPot(object):
    """
    Calculate potential reference evapotranspiration.

    This class computes potential evapotranspiration from climate data using methods
    primarily based on FAO 56 guidelines and LISVAP. The calculations are based on
    the Penman-Monteith equation for reference evapotranspiration.

    Attributes
    ----------
    
    var : object
        Model variables container
    model : object
        CWatM model instance

    References
    ----------
    
    FAO 56 Guidelines: http://www.fao.org/docrep/X0490E/x0490e08.htm#penman%20monteith%20equation
    LISVAP Documentation: https://ec.europa.eu/jrc/en/publication/eur-scientific-and-technical-research-reports/lisvap-evaporation-pre-processor-lisflood-water-balance-and-flood-simulation-model

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    cropCorrect                          Array         calibration factor of crop KC factor                                    --   
    crop_correct_landCover               Array         correction of crop KC per land cover (forest, grass, paddy, non-paddy)  --   
    AlbedoCanopy                         Array         Albedo of vegetation canopy (FAO,1998) default =0.23                    --   
    AlbedoSoil                           Array         Albedo of bare soil surface (Supit et. al. 1994) default = 0.15         --   
    AlbedoWater                          Array         Albedo of water surface (Supit et. al. 1994) default = 0.05             --   
    co2                                  Array         CO2 concentration (yearly) for the Yang et al. correction, PET_modus 3  ppm  
    albedoLand                           Array         albedo from land surface (from GlobAlbedo database)                     --   
    albedoOpenWater                      Array         albedo from open water surface (from GlobAlbedo database)               --   
    useAlbedoMaps                        Flag          monthly albedo maps instead of fixed values (albedo, default False)     bool 
    ETRef                                Array         potential evapotranspiration rate from reference crop                   m    
    only_radiation                       Flag          only daily radiation and vapour pressure are given (e.g. JRC EMO)       bool 
    Psurf                                Array         surface air pressure                                                    kPa  
    Rsdl                                 Array         long wave downward surface radiation per day                            MJ/m2
    huss                                 Array         2 m specific humidity                                                   kg/kg
    EAct                                 Array         actual vapour pressure                                                  kPa  
    rhs                                  Array         2 m relative humidity                                                   %    
    useTdew                              Flag          dew point temperature maps are read (pySnowClim with useTdew, era5)     bool 
    Tdew                                 Array         dew point temperature (maps, or from EAct: Magnus formula FAO 56)       deg C
    calc_evapo                           Flag          potential evaporation is calculated (not read from ET maps)             bool 
    pet_modus                            Number        PET method 1 PM, 2 Milly-Dunne, 3 PM-Yang, 4 Priestley-T., 5 Thornthw.  --   
    without_rlds                         Flag          net long wave radiation estimated with FAO 56 (no or coarse rlds maps)  bool 
    era5                                 Flag          ERA5 input: vapour pressure from the dew point temperature              bool 
    useHuss                              Flag          specific humidity maps instead of relative humidity maps                bool 
    TMin                                 Array         minimum air temperature                                                 deg C
    TMax                                 Array         maximum air temperature                                                 deg C
    Tavg                                 Array         Input, average air Temperature                                          deg C
    Rsds                                 Array         short wave downward surface radiation per day                           MJ/m2
    Wind                                 Array         wind speed at 2 m                                                       m s-1
    EWRef                                Array         potential evaporation rate from water surface                           m    
    thermalI                             Array         thermal index (yearly) for the modified Thornthwaite method             --   
    thermalWarm                          Array         thermal index > 0 (Thornthwaite PET only there), set once a year        bool 
    thermalIPos                          Array         thermal index, 1.0 where it is 0 (avoids division by 0)                 --   
    thornAlpha                           Array         Thornthwaite exponent alpha from the thermal index, set once a year     --   
    usepySnowClim                        Flag          Flag to use pySnowClim                                                  --   
    dem                                  Array         Digital elevation model                                                 m    
    lat                                  Array         Latitude                                                                deg  
    pressFactor                          Array         air pressure factor from the elevation (FAO 56 equation 7)              --   
    clearSkyFactor                       Array         clear sky radiation factor 0.75 + 2e-5 * dem (FAO 56 equation 37)       --   
    sinLat                               Array         sine of the latitude                                                    --   
    cosLat                               Array         cosine of the latitude                                                  --   
    tanLat                               Array         tangent of the latitude                                                 --   
    snowmelt_radiation                   Flag          use radiation term in snow melt                                         bool 
    snowFAOlongwave                      Flag          radiation snow melt: incoming long wave estimated with FAO 56           bool 
    longwaveFactor                       Array         FAO 56 net long wave factor EmNet * RsRso (from evaporationPot)         --   
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize the potential evapotranspiration module.

        Parameters
        ----------
        model : object
            CWatM model instance containing variables and configuration
        """
        self.var = model.var
        self.model = model
    
    def vari_pySnowClim(self, RNup, RLN, ESat):
        """
        Completes the forcing of pySnowClim (only if usepySnowClim): air pressure and incoming long wave radiation
        (only_radiation), specific and relative humidity, dew point temperature (if not read from maps).
        Called from dynamic_1 (PET_modus 1 or 3).
        """
        # if pysnowclim variables are missing they are calculated
        if self.var.usepySnowClim:
            # for pySnowclim
            eps = 0.621979008
            if self.var.only_radiation:

                # no air pressure maps: air pressure [kPa] from the elevation (FAO 56 equation 7)
                # (not Psycon / 0.665E-3: Psycon contains the latent heat of Tavg -> Psurf would depend on temperature)
                self.var.Psurf = 101.3 * self.var.pressFactor
                # eps: molecular weight of water vapor / The molecular weight of dry air: 18.015 g/mol / 28.964 g/mol
                self.var.Rsdl = RNup - RLN
                self.var.huss = eps * self.var.EAct / (self.var.Psurf - self.var.EAct * (1 - eps))
                # relative humidity [%] = EAct / ESat (Psurf * huss / ((1-eps) * huss + eps) is EAct again)
                self.var.rhs = 100 * self.var.EAct / ESat
            elif self.var.era5:
                # era5: no humidity maps, EAct is calculated from the dew point temperature -> specific and relative humidity
                self.var.huss = eps * self.var.EAct / (self.var.Psurf - self.var.EAct * (1 - eps))
                self.var.rhs = 100 * self.var.EAct / ESat
            else:
                if self.var.useHuss:
                    # EAct is calculated from huss in eact()
                    self.var.rhs = 100 * self.var.EAct / ESat
                else:
                    self.var.huss = eps * self.var.EAct / (self.var.Psurf - self.var.EAct * (1 - eps))
            if not self.var.useTdew:
                # calculate Tdew (Magnus Formula)
                # based on FAO56 https://www.fao.org/4/X0490E/x0490e07.htm
                # equation Compute Dew Point Temperature  No 14: EAct in kPa
                # EAct = 0 (rhs = 0 or missing humidity filled with 0) would give log(0) -> Tdew = NaN
                # lower limit 1e-6 kPa -> Tdew about -100 deg C (extremely dry)
                self.var.Tdew = dewPointTemp(np.maximum(self.var.EAct, 1e-6))
                # or Bolton, D. (1980). The computation of equivalent potential temperature. Monthly Weather Review, 108(7), 1046-1053.
                #self.var.Tdew = np.log(self.var.EAct / 0.6112  ) * 243.5 / (17.67 - np.log(self.var.EAct / 0.6112))
                # or use Arden Buck equation for Temp > 0 deg
                # self.var.Tdew  =  (243.04 * np.log(self.var.EAct / 6.1121)) / (17.625 - np.log(self.var.EAct / 6.1121))
        return

    def initial(self):
        """
        Initial part of the potential evaporation module.

        Loads the crop correction factors (used in evaporation.py and snow.py). If potential evaporation is
        calculated (calc_evaporation = True or pySnowClim), loads the parameters of the PET method.
        PET_modus is set in readmeteo.initial (runs before).
        """

        self.var.cropCorrect = loadmap('crop_correct')
        self.var.crop_correct_landCover = np.tile(1 + globals.inZero, (4, 1))
        if 'crop_correct_forest' in binding:
            self.var.crop_correct_landCover[0] = loadmap('crop_correct_forest')
        if 'crop_correct_grassland' in binding:
            self.var.crop_correct_landCover[1] = loadmap('crop_correct_grassland')
        if 'crop_correct_irrpaddy' in binding:
            self.var.crop_correct_landCover[2] = loadmap('crop_correct_irrpaddy')
        if 'crop_correct_irrnonpaddy' in binding:
            self.var.crop_correct_landCover[3] = loadmap('crop_correct_irrnonpaddy')

        # radiation snow melt (snow.py): incoming long wave estimated with FAO-56 if only radiation is given
        # (only_radiation, e.g. EMO) or long wave maps are too coarse (without_rlds; EAct needs calc_evaporation),
        # otherwise measured long wave Rsdl. The FAO-56 factor longwaveFactor is calculated here (fao_longwave)
        self.var.snowFAOlongwave = self.var.snowmelt_radiation and not self.var.usepySnowClim and \
            self.var.without_rlds and (self.var.only_radiation or self.var.calc_evapo)

        if self.var.calc_evapo:
            self.initial_1()
        elif self.var.snowFAOlongwave:
            # FAO-56 long wave for snow melt without calculated evaporation: elevation and latitude
            self.var.dem = loadmap('dem')
            self.var.lat = loadmap('latitude')
            self.site_constants()

    def site_constants(self):
        """
        Constants per cell from the elevation and the latitude (computed once, used every day):
        air pressure factor (FAO 56 equation 7), clear sky factor (equation 37), sin/cos/tan of the latitude
        """
        if hasattr(self.var, 'dem'):
            self.var.pressFactor = ((293 - 0.0065 * self.var.dem) / 293) ** 5.26
            self.var.clearSkyFactor = 0.75 + (2 * 10 ** -5 * self.var.dem)
        if hasattr(self.var, 'lat'):
            radian = np.pi / 180 * self.var.lat
            self.var.sinLat = np.sin(radian)
            self.var.cosLat = np.cos(radian)
            self.var.tanLat = np.tan(radian)

    # --------------------------------------------------------------------------

    def initial_1(self):
        """
        Loads the parameters of the PET method (only if potential evaporation is calculated).

        PET_modus (set in readmeteo.initial):

        1: Penman-Monteith, FAO 56

        2: Milly and Dunne, energy only PET: ET = 0.8 Rn (equation 8)
           P. C. D. Milly and K. A. Dunne, 2016: Potential evapotranspiration and continental drying,
           Nature Climate Change, DOI: 10.1038/NCLIMATE3046

        3: Penman-Monteith with the CO2 correction of the surface resistance of Yang et al. (2019), equation 14
           Yang, Y., Roderick, M. L., Zhang, S., McVicar, T. R., and Donohue, R. J.: Hydrologic implications of
           vegetation response to elevated CO2 in climate projections, Nat. Clim. Change, 9, 44-48,
           10.1038/s41558-018-0361-0, 2019.

        4: Priestley-Taylor, alpha 1.1 for land (reference crop) and 1.26 for open water
           https://wetlandscapes.github.io/blog/blog/penman-monteith-and-priestley-taylor/
           uses only tmin, tmax, tavg, rsds, rlds (or the FAO-56 long wave estimate)

        5: Modified Thornthwaite, uses only tmin, tmax, tavg
           Pereira, A. R., & Pruitt, W. O. (2004). Adaptation of the Thornthwaite Scheme for Estimating Daily
           Reference Evapotranspiration. Agricultural Water Management, 66, 251-257.
           https://doi.org/10.1016/j.agwat.2003.11.003

        Albedo of canopy, soil and water; elevation (dem) for the psychrometric constant and clear sky radiation;
        latitude for the extraterrestrial radiation and the day length
        """

        self.var.AlbedoCanopy = loadmap('AlbedoCanopy')
        self.var.AlbedoSoil = loadmap('AlbedoSoil')
        self.var.AlbedoWater = loadmap('AlbedoWater')
        # monthly albedo maps (albedoMaps) instead of the fixed albedo values - optional key, default False
        self.var.useAlbedoMaps = False
        if 'albedo' in binding:
            self.var.useAlbedoMaps = returnBool('albedo')

        if self.var.pet_modus == 4 or self.var.without_rlds:
            self.var.dem = loadmap('dem')

        if self.var.pet_modus == 5 or self.var.without_rlds:
            self.var.lat = loadmap('latitude')

        self.site_constants()

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------


    def dynamic(self):
        """
        Dynamic part of the potential evaporation module: calls the method of PET_modus
        (only if potential evaporation is calculated, otherwise ETRef and EWRef are read in readmeteo).

        :return:
            - ETRef - potential reference evapotranspiration rate [m/day]
            - EWRef - potential evaporation rate from water surface [m/day]
        """

        if self.var.calc_evapo:
            if self.var.pet_modus in (1, 3):
                # Penman-Monteith, 3: with the CO2 correction of Yang et al.
                self.dynamic_1()
            elif self.var.pet_modus == 2:
                self.dynamic_2()
            elif self.var.pet_modus == 4:
                self.dynamic_4()
            elif self.var.pet_modus == 5:
                self.dynamic_5()
        elif self.var.snowFAOlongwave:
            # radiation snow melt without calculated evaporation (only_radiation): FAO-56 long wave factor for snow.py
            self.fao_longwave()

    # --------------------------------------------------------------------------
    # parts used by several PET methods (and by snow.py via longwaveFactor)

    def esat(self):
        """
        Saturation vapour pressure [kPa]: mean of ESat(TMin) and ESat(TMax)
        http://www.fao.org/docrep/X0490E/x0490e07.htm   equation 11/12
        """
        ESatmin = satVapPress(self.var.TMin)
        ESatmax = satVapPress(self.var.TMax)
        return (ESatmin + ESatmax) / 2.0

    def eact(self, ESat):
        """
        Actual vapour pressure EAct [kPa] from the dew point temperature (era5), specific humidity (useHuss)
        or relative humidity. Not used with only_radiation: EAct is read in readmeteo (EMO maps).
        FAO 56 page 36
        """
        if self.var.era5:
            # calculate Eact (Magnus Formula)
            # based on FAO56 https://www.fao.org/4/X0490E/x0490e07.htm
            # equation Compute Dew Point Temperature  No 14: Eact in kPa
            self.var.EAct = satVapPress(self.var.Tdew)
        elif self.var.useHuss:
            # if specific humidity calculate actual vapour pressure this way
            self.var.EAct = (self.var.Psurf * self.var.huss) / (((1-0.621979008) * self.var.huss) + 0.621979008)
            # http://www.eol.ucar.edu/projects/ceop/dm/documents/refdata_report/eqns.html
        else:
            # if relative humidity
            self.var.EAct = ESat * self.var.rhs / 100.0

    def solar(self):
        """
        Solar declination [rad] and sunset hour angle ws [rad] (tan of the latitude from site_constants)
        FAO 56 - https://www.fao.org/3/x0490E/x0490e07.htm#solar%20radiation  Chapter 3 equation 22, 24, 25
        """
        declin = 0.409 * np.sin(2 * np.pi * dateVar['doy'] / 365 - 1.39)
        ws = np.arccos(np.clip(-self.var.tanLat * np.tan(declin), -1.0, 1.0))
        return declin, ws

    def fao_longwave(self):
        """
        Net long wave radiation estimated with FAO-56 (if long wave maps are not given or too coarse):
        RLN = sigma T^4 * EmNet * RsRso    Chapter 3 equation 39
        EmNet: net emissivity from the vapour pressure, RsRso: cloudiness from the relative short wave radiation

        For radiation snow melt (snowFAOlongwave) the factor EmNet * RsRso is stored as longwaveFactor (snow.py
        estimates the incoming long wave with it; stored for the warm runs of the calibration as well)

        :return: EmNet, RsRso
        """
        declin, ws = self.solar()
        distanceSun = 1 + 0.033 * np.cos(2 * np.pi * dateVar['doy'] / 365)
        # extraterrestrial radiation: equation 21
        Ra = 24 * 60 / np.pi * 0.082 * distanceSun * (ws * self.var.sinLat * np.sin(declin) + self.var.cosLat * np.cos(declin) * np.sin(ws))
        # clear sky radiation: equation 37 (0.75 + 2e-5 * dem from site_constants)
        Rso = Ra * self.var.clearSkyFactor  # in MJ/m2/day
        Rso = np.maximum(Rso, 1e-6)  # avoid division by zero in polar night (Ra = 0)
        # equation 39
        RsRso = 1.35 * self.var.Rsds / Rso - 0.35
        RsRso = np.minimum(np.maximum(RsRso, 0.05), 1)
        EmNet = (0.34 - 0.14 * np.sqrt(self.var.EAct))  # EAct in kPa (EMO maps in hPa are converted in readmeteo)
        if self.var.snowFAOlongwave:
            self.var.longwaveFactor = EmNet * RsRso
        return EmNet, RsRso

    def net_radiation(self, RLN, LatHeatVap):
        """
        Net absorbed radiation [mm/day] of the reference vegetation canopy (RNA) and of open water (RNAWater):
        albedo from the settings (AlbedoCanopy, AlbedoWater) or monthly albedo maps (albedo = True)

        :return: RNA, RNAWater
        """
        if self.var.useAlbedoMaps:
            if dateVar['newStart'] or dateVar['newMonth']:  # loading every month a new map
                self.var.albedoLand = readnetcdf2('albedoMaps', dateVar['currDate'], useDaily='month',value='albedoLand')
                self.var.albedoOpenWater = readnetcdf2('albedoMaps', dateVar['currDate'], useDaily='month',value='albedoWater')
            RNA = np.maximum(((1 - self.var.albedoLand) * self.var.Rsds - RLN) / LatHeatVap, 0.0)
            RNAWater = np.maximum(((1 - self.var.albedoOpenWater) * self.var.Rsds - RLN) / LatHeatVap, 0.0)
        else:
            RNA = np.maximum(((1 - self.var.AlbedoCanopy) * self.var.Rsds - RLN) / LatHeatVap, 0.0)
            # net absorbed radiation of reference vegetation canopy [mm/d]
            RNAWater = np.maximum(((1 - self.var.AlbedoWater) * self.var.Rsds - RLN) / LatHeatVap, 0.0)
            # net absorbed radiation of water surface
        return RNA, RNAWater

    # --------------------------------------------------------------------------


    def dynamic_1(self):
        """
        PET_modus 1: Penman-Monteith (FAO 56) and PET_modus 3: Penman-Monteith with the CO2 correction of
        Yang et al. (2019).

        Uses tmin, tmax, tavg, wind, radiation and humidity (relative or specific humidity, dew point temperature
        with era5 or vapour pressure with only_radiation). Air pressure from the maps, or with only_radiation
        from the elevation. Long wave radiation from the maps, or with without_rlds estimated with FAO-56.
        """


        if self.var.pet_modus == 3:
            # Yang et al.Penman Montheith correction method
            # loading CO2 concentration RCP2.6-RCP8.5
            if dateVar['newStart'] or dateVar['newYear']:
                self.var.co2 = readnetcdf2('co2conc', dateVar['currDate'], "yearly", value="CO2",
                                           cut=False, compress=False)
                # the CO2 file is a time series with one value per year (variable CO2, dimension time only)
                if np.ndim(self.var.co2) != 0:
                    msg = "Error 174: co2conc: the CO2 file must have one CO2 value per year (variable CO2 with " \
                          "only the dimension time)\nbut the record has the shape " + str(np.shape(self.var.co2)) + \
                          " (a map?)\n"
                    raise CWATMFileError(cbinding('co2conc'), msg, sname='co2conc')

        ESat = self.esat()   # [KPa]
        RNup = 4.903E-9 * (((self.var.TMin + 273.16) ** 4) + ((self.var.TMax + 273.16) ** 4)) / 2
        # Up longwave radiation [MJ/m2/day] https://www.fao.org/4/x0490E/x0490e0j.htm#TopOfPage table 2.8
        LatHeatVap = 2.501 - 0.002361 * self.var.Tavg
        # latent heat of vaporization [MJ/kg]

        # --------------------------------
        if self.var.only_radiation:
            # only daily radiation and vapour pressure are given (e.g. EMO): no air pressure maps
            # EAct is read in readmeteo
            Psycon = 0.00163 * (101.3 / LatHeatVap)
            # psychrometric constant at sea level [kPa deg C-1]
            # http://www.fao.org/docrep/X0490E/x0490e07.htm  Equation 8
            # see http://www.fao.org/docrep/X0490E/x0490e08.htm#penman%20monteith%20equation
            Psycon = Psycon * self.var.pressFactor  # in [KPa deg C-1]
            # air pressure from the elevation: http://www.fao.org/docrep/X0490E/x0490e07.htm  Equation 7
        else:
            Psycon = 0.665E-3 * self.var.Psurf
            # psychrometric constant [kPa C-1]
            # http://www.fao.org/docrep/X0490E/x0490e07.htm  Equation 8
            # see http://www.fao.org/docrep/X0490E/x0490e08.htm#penman%20monteith%20equation
            self.eact(ESat)

        # if long wave radiation maps are not given or too coarse: net long wave radiation estimated with FAO-56
        if self.var.without_rlds:
            EmNet, RsRso = self.fao_longwave()
            RLN = RNup * EmNet * RsRso
        else:
            # longwave radiation balance
            RLN = RNup - self.var.Rsdl
            # radiation is stored on disk as W/m2 but converted to MJ/m2/day in readmeteo.py

        # net absorbed radiation [mm/day]
        RNA, RNAWater = self.net_radiation(RLN, LatHeatVap)

        VapPressDef = np.maximum(ESat - self.var.EAct, 0.0)
        Delta = ((4098.0 * ESat) / ((self.var.Tavg + 237.3) ** 2))
        # slope of saturated vapour pressure curve [kPa/deg C]
        # Equation 13 Chapter 3

        # Chapter 2 Equation 6
        windpart = 900 * self.var.Wind / (self.var.Tavg + 273.16)

        if self.var.pet_modus == 1:
            denominator = Delta + Psycon * (1 + 0.34 * self.var.Wind)
        else:
            # Yang et al.Penman Montheith correction method:  term 2 accounts for changing [CO2] on rs.
            denominator = Delta + Psycon * (1 + self.var.Wind * (0.34 + 0.00024 * (self.var.co2 - 300.)))

        numerator1 = Delta / denominator
        numerator2 = Psycon / denominator
        # the 0.408 constant is replace by 1/LatHeatVap see above

        RNAN = RNA * numerator1
        RNANWater = RNAWater * numerator1

        EA = windpart * VapPressDef * numerator2

        # Potential evapo(transpi)ration is calculated for two reference surfaces:
        # 1. Reference vegetation canopy
        # 2. Open water surface
        self.var.ETRef = (RNAN + EA) * 0.001
        # potential reference evapotranspiration rate [m/day]  # from mm to m with 0.001
        # potential evaporation rate from a bare soil surface [m/day]
        self.var.EWRef = (RNANWater + EA) * 0.001
        # potential evaporation rate from water surface [m/day]
        # -> here we are at ET0 (see http://www.fao.org/docrep/X0490E/x0490e04.htm#TopOfPage figure 4:)

        # if pysnowclim variables missing are calculated
        self.vari_pySnowClim(RNup, RLN, ESat)

    def dynamic_2(self):
        """
        PET_modus 2: Milly and Dunne, energy only PET = 0.8 Rn (equation 8)
        P. C. D. Milly and K. A. Dunne, 2016: Potential evapotranspiration and continental drying,
        Nature Climate Change, DOI: 10.1038/NCLIMATE3046

        Uses tmin, tmax, tavg and radiation. Humidity (and air pressure for specific humidity) only with
        without_rlds for the FAO-56 long wave estimate.
        """
        LatHeatVap = 2.501 - 0.002361 * self.var.Tavg
        # latent heat of vaporization [MJ/kg]
        RNup = 4.903E-9 * (((self.var.TMin + 273.16) ** 4) + ((self.var.TMax + 273.16) ** 4)) / 2
        # Up longwave radiation [MJ/m2/day]

        if self.var.without_rlds:
            if not self.var.only_radiation:
                self.eact(self.esat())
            EmNet, RsRso = self.fao_longwave()
            RLN = RNup * EmNet * RsRso
        else:
            RLN = RNup - self.var.Rsdl
            # radiation is stored on disk as W/m2 but converted to MJ/m2/day in readmeteo.py

        # net absorbed radiation [mm/day]
        RNA, RNAWater = self.net_radiation(RLN, LatHeatVap)

        # 1. Reference vegetation canopy
        # 2. Open water surface
        self.var.ETRef = 0.8 * RNA * 0.001
        # potential reference evapotranspiration rate [m/day]  # from mm to m with 0.001
        # potential evaporation rate from a bare soil surface [m/day]
        self.var.EWRef = 0.8 * RNAWater * 0.001

    def dynamic_4(self):
        """
        PET_modus 4: Priestley-Taylor  PET = alpha * Delta / (Delta + Psycon) * Rn
        https://wetlandscapes.github.io/blog/blog/penman-monteith-and-priestley-taylor/

        alpha = 1.26 (classic value for wet surfaces) for open water (EWRef) and
        alpha = 1.1 for land (reference crop, ETRef): vegetated land is not always saturated, lower values
        (about 1.0 - 1.1) are used for land

        Uses tmin, tmax, tavg, rsds and rlds. With without_rlds the long wave radiation is estimated with FAO-56
        (needs humidity, and air pressure for specific humidity). Air pressure for the psychrometric constant
        from the elevation.
        """
        ESat = self.esat()   # [KPa]
        RNup = 4.903E-9 * (((self.var.TMin + 273.16) ** 4) + ((self.var.TMax + 273.16) ** 4)) / 2
        # Up longwave radiation [MJ/m2/day]
        LatHeatVap = 2.501 - 0.002361 * self.var.Tavg
        # latent heat of vaporization [MJ/kg]

        # if long wave radiation maps are not given or too coarse: net long wave radiation estimated with FAO-56
        if self.var.without_rlds:
            if not self.var.only_radiation:
                self.eact(ESat)
            EmNet, RsRso = self.fao_longwave()
            RLN = RNup * EmNet * RsRso
        else:
            RLN = RNup - self.var.Rsdl

        Psycon = 0.00163 * (101.3 / LatHeatVap)
        # psychrometric constant at sea level [kPa deg C-1]
        # http://www.fao.org/docrep/X0490E/x0490e07.htm  Equation 8
        # see http://www.fao.org/docrep/X0490E/x0490e08.htm#penman%20monteith%20equation
        Psycon = Psycon * self.var.pressFactor  # in [KPa deg C-1]
        # air pressure from the elevation (no air pressure maps are read for PET_modus 4)
        # http://www.fao.org/docrep/X0490E/x0490e07.htm  Equation 7

        # net absorbed radiation [mm/day] (radiation converted to MJ/m2/day in readmeteo.py)
        RNA, RNAWater = self.net_radiation(RLN, LatHeatVap)

        Delta = ((4098.0 * ESat) / ((self.var.Tavg + 237.3) ** 2))
        # slope of saturated vapour pressure curve [kPa/deg C]

        # Priestley-Taylor alpha: 1.1 for land (reference crop), 1.26 for open water
        RNAN = 1.1 * Delta / (Delta + Psycon) * RNA
        RNANWater = 1.26 * Delta / (Delta + Psycon) * RNAWater

        # 1. Reference vegetation canopy
        # 2. Open water surface
        self.var.ETRef = RNAN * 0.001
        # potential reference evapotranspiration rate [m/day]  # from mm to m with 0.001
        # potential evaporation rate from a bare soil surface [m/day]
        self.var.EWRef = RNANWater * 0.001


    def dynamic_5(self):
        """
        PET_modus 5: modified Thornthwaite, uses only tmin, tmax, tavg and the yearly thermal index
        (thermalIndexFile, read in readmeteo)
        Pereira, A. R., & Pruitt, W. O. (2004). Adaptation of the Thornthwaite Scheme for Estimating Daily
        Reference Evapotranspiration. Agricultural Water Management, 66, 251-257.
        https://doi.org/10.1016/j.agwat.2003.11.003
        Put together by Tamas Acs
        """
        
        # ws: sunset hour angle [rad]
        declin, ws = self.solar()
        # Photoperiod (daylength)
        N = ws * 24 / np.pi
        
        # 	k: parameter, found the be 0.69-0.72 (0.72 proposed by Camargo et al.
        #   and 0.69 proposed by Pereira et al.)
        k = 0.69
        # Thermal index of the year: read in readmeteo (thermalIndexFile, every new year)
        # I will be calculated in a prerun, year starts on 1st Jan.
        # I = sum(0.2*T_(eff,mean))^1.514  from n=1 to 12
        # n: index of month
        # T_(eff,mean): the monthly mean of daily T_eff values in the given month [C]
        
        # thermal index 0 (all monthly means <= 0 deg C): no PET with the temperature formula (division by 0 -> inf)
        # 1.0 is only a placeholder to avoid the division by 0, pet1 is set to 0 there below
        # the thermal index changes only once a year (read in readmeteo with the same condition):
        # placeholder and exponent alpha only then
        if dateVar['newStart'] or dateVar['newYear']:
            self.var.thermalWarm = self.var.thermalI > 0
            self.var.thermalIPos = np.where(self.var.thermalWarm, self.var.thermalI, 1.0)
            I = self.var.thermalIPos
            # exponent alpha
            self.var.thornAlpha = 6.75e-7 * I**3 - 7.71e-5 * I**2 + 1.7912e-2 * I + 0.49239
        warm = self.var.thermalWarm
        thermalI = self.var.thermalIPos
        alpha = self.var.thornAlpha

        # Effective temperature (Camargo et al. 1999 and Pereira et al. 2004)
        # polar day (N = 24): limit 24-N to avoid the division by 0 (inf, or NaN if 3*TMax-TMin = 0);
        # Teff is cut to TMax in the next lines anyway
        Teff = N / np.maximum(24-N, 1e-6) * 0.5 * k * (3 * self.var.TMax - self.var.TMin)
        Teff = np.where(Teff < self.var.Tavg, self.var.Tavg, Teff)
        Teff = np.where(Teff > self.var.TMax, self.var.TMax, Teff)
        
        # PET (Thornthwaite 1948 and Willmott et al. 1985):
        # Teff < 0: negative ** alpha would be NaN; PET is set to 0 for Teff < 0 below anyway
        pet1 = N/360 * 16 * (10 * np.maximum(Teff, 0) / thermalI) ** alpha
        pet1 = np.where(warm, pet1, 0.0)
        # above 26.5 deg C: independent of the thermal index
        pet2 = -415.85 + 32.24 * Teff - 0.43 * Teff**2
        # to daily and photoperiod: N/12 * 1/30 = N/360 as pet1, but N/364.386 (PB):
        # the Thornthwaite curves of all thermal indices (I = 20 - 140) meet at 26.5 deg C at 134.90 mm/month,
        # pet2 gives 136.54 mm/month there -> 360 * 136.54 / 134.90 = 364.386 removes the jump between pet1 and pet2
        pet2 = pet2 * N / 364.386
        # smooth transition from pet1 to pet2 between 26 and 27 deg C (remaining jump for very low or high
        # thermal index, e.g. I = 160: +4 %)
        w = np.clip(Teff - 26.0, 0.0, 1.0)
        PET = np.where(Teff < 26.0, pet1, np.where(Teff > 27.0, pet2, (1 - w) * pet1 + w * pet2))
        PET = np.where(Teff < 0, 0, PET)

        # potential reference evapotranspiration rate [m/day]  # from mm to m 
        self.var.ETRef = PET * 0.001   
        # only one potential evapotranspiration: water = reference crop * 1.2
        # 1.2 as empirical factor
        self.var.EWRef = self.var.ETRef * 1.2
