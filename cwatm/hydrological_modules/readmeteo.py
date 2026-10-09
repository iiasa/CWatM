# -------------------------------------------------------------------------
# Name:        READ METEO input maps
# Purpose: Meteorological data reader and processor for climate forcing inputs.
# Manages temporal reading and processing of weather data from NetCDF files.
# Handles multiple meteorological variables with temporal interpolation and validation.
#
# Author:      PB, MS, SH, JdB
# Created:     13/07/2016 
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
from functools import lru_cache


# --------------------------------------------------------------------------
# helping subroutines for downscaling (module level: the lru_cache of _weights is kept between time steps)

def kron_ones(a, n):
    """
    Same as np.kron(a, np.ones((n, n))), but faster: each value is repeated n times in both directions.

    The 2D input is broadcast to (rows, n, cols, n) and reshaped, which copies every value once.
    The result is float64 (as with np.kron and a float64 array of ones). Masked arrays use np.kron as before.
    """
    if np.ma.isMaskedArray(a):
        return np.kron(a, np.ones((n, n)))
    a = np.asarray(a, dtype=np.result_type(a, np.float64))
    rows, cols = a.shape
    return np.broadcast_to(a[:, None, :, None], (rows, n, cols, n)).reshape(rows * n, cols * n)


@lru_cache(maxsize=32)
def _weights(n_in, n_out):
    """
    Index of the lower coarse cell and linear weight for each fine cell (as scipy.ndimage.zoom, order=1).
    Cached: the same (n_in, n_out) is used every time step.
    """
    x = np.arange(n_out) * (n_in - 1) / (n_out - 1)
    i0 = np.minimum(x.astype(np.intp), n_in - 2)
    return i0, (x - i0).astype(np.float32)


def _zoom_cols(a, nx):
    """Linear interpolation of a 2D float32 array along the columns to nx columns."""
    if a.shape[1] == 1:
        # only one coarse column: nothing to interpolate (as scipy.ndimage.zoom)
        return np.repeat(a, nx, axis=1)
    i0, w = _weights(a.shape[1], nx)
    lo = np.take(a, i0, axis=1)
    hi = np.take(a, i0 + 1, axis=1)
    hi -= lo
    hi *= w
    lo += hi
    return lo


def _zoom_rows(a, ny):
    """Linear interpolation of a 2D float32 array along the rows to ny rows."""
    if a.shape[0] == 1:
        # only one coarse row: nothing to interpolate (as scipy.ndimage.zoom)
        return np.repeat(a, ny, axis=0)
    i0, w = _weights(a.shape[0], ny)
    d = a[1:] - a[:-1]
    # row by row: faster than all rows at once (d[i0], a[i0] would be two full size copies)
    out = np.empty((ny, a.shape[1]), np.float32)
    for j, i in enumerate(i0):
        np.multiply(d[i], w[j], out=out[j])
        out[j] += a[i]
    return out


def zoom(a, factor):
    """Same as scipy.ndimage.zoom(a, factor, order=1) for 2D arrays, in float32."""
    a = np.asarray(a, dtype=np.float32)
    fy, fx = np.broadcast_to(factor, (a.ndim,))[:2]
    ny, nx = int(round(a.shape[0] * fy)), int(round(a.shape[1] * fx))
    b = a.reshape(a.shape[:2])
    if nx != b.shape[1]:
        b = _zoom_cols(b, nx)
    if ny != b.shape[0]:
        b = _zoom_rows(b, ny)
    return b.reshape((ny, nx) + a.shape[2:])

# --------------------------------------------------------------------------


class readmeteo(object):
    """
    Meteorological data reader and processor for CWatM.
    
    Handles reading meteorological forcing data from NetCDF files, performs
    spatial downscaling using WorldClim data, manages temporal interpolation,
    and provides data preprocessing for hydrological calculations.
    
    Attributes
    ----------
    
    model : object
        Reference to the main CWatM model instance
    var : object
        Reference to model variables object containing state variables

   

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    stopaftersnow                        Flag          stop run after snow calcualtion -> for snow calibration (AI)            --   
    DtDay                                Array         length of a timestep as fraction of a day (default=1)                   --
    con_precipitation                    Array         conversion factor for precipitation                                     --   
    con_e                                Array         conversion factor for evaporation                                       --   
    meteo                                Array         store all meteo data in memeory for warm start (eg calibration)         compl
    ETRef                                Array         potential evapotranspiration rate from reference crop                   m    
    Precipitation                        Array         Precipitation (input for the model)                                     m    
    only_radiation                       Flag          Boolean if only radiation is use for calculation e.g JRC EMO dataset    bool 
    Psurf                                Array         Instantaneous surface pressure                                          Pa   
    Rsdl                                 Array         long wave downward surface radiation fluxes                             W m-2
    huss                                 Array         2 m istantaneous specific humidity[kg / kg] (AI)                        --   
    EAct                                 Array         Daily vapor pressure                                                    kPa
    rhs                                  Array                                                                                 --   
    useTdew                              Flag                                                                                  --   
    Tdew                                 Array         calculate Tdew (Magnus Formula) based on FAO56 https://www.fao.org/4/X  --   
    calc_evapo                           Flag          and missing meteo variables have to be calculated in evapoPot.py (AI)   --   
    pet_modus                            Number        Index which ETP approach is used e.g. 1 for Penman-Monteith             bool 
    without_rlds                         Flag                                                                                  --   
    TMin                                 Array         minimum air temperature                                                 K    
    TMax                                 Array         maximum air temperature                                                 K    
    Tavg                                 Array         Input, average air Temperature                                          K    
    Rsds                                 Array         short wave downward surface radiation fluxes                            W m-2
    Wind                                 Array         wind speed                                                              m s-1
    EWRef                                Array         potential evaporation rate from water surface                           m    
    thermalI                             Array         ThermalIndex. Use to calculate pot. Evaporation with Thornthwaite       deg C
    includeGlaciers                      Flag          Include glaciers                                                        bool 
    meteomapsscale                       Array         if meteo maps have the same extend as the other spatial static maps ->  --   
    meteodown                            Array         if meteo maps should be downscaled                                      --   
    InterpolationMethod                  Number        can be spline or kron                                                   Strin
    buffer                               List                                                                                  --   
    includeOnlyGlaciersMelt              Flag          Include only glacier melt but not rain on glacier                       bool 
    preMaps                              Array         choose between steady state precipitation maps for steady state modflo  --   
    tempMaps                             Array         choose between steady state temperature maps for steady state modflow   --   
    evaTMaps                             Array         choose between steady state ETP water maps for steady state modflow or  --   
    eva0Maps                             Array         choose between steady state ETP reference maps for steady state modflo  --   
    RSDSMaps                             Array         Surface Downwelling Shortwave Radiation                                 w m-2
    RSDLMaps                             Array         Surface Downwelling Longwave Radiation                                  W m-2
    glaciermeltMaps                      Array         Melt from glacier                                                       m    
    glacierrainMaps                      Array         Rain on glacier                                                         m    
    snowmelt_radiation                   Array         use radiation term in snow melt (AI)                                    --   
    only_radiation_Wm2                   Flag                                                                                  --   
    WtoMJ                                Array         Conversion factor from [W] to [MJ] for radiation: 86400 * 1E-6          --   
    wc2_tavg                             Array         High resolution WorldClim map for average temperature                   K    
    wc4_tavg                             Array         upscaled to low resolution WorldClim map for average temperature        K    
    wc2_tmin                             Array         High resolution WorldClim map for min temperature                       K    
    wc4_tmin                             Array         upscaled to low resolution WorldClim map for min temperature            K    
    wc2_tmax                             Array         High resolution WorldClim map for max temperature                       K    
    wc4_tmax                             Array         upscaled to low resolution WorldClim map for max temperature            K    
    wc2_prec                             Array         High resolution WorldClim map for precipitation                         m    
    wc4_prec                             Array         upscaled to low resolution WorldClim map for precipitation              m    
    xcoarse_prec                         List          these variables are generated to avoid calculating them at each timest  --   
    ycoarse_prec                         List                                                                                  --   
    xfine_prec                           List                                                                                  --   
    yfine_prec                           List                                                                                  --   
    meshlist_prec                        List                                                                                  --   
    xcoarse_tavg                         List                                                                                  --   
    ycoarse_tavg                         List                                                                                  --   
    xfine_tavg                           List                                                                                  --   
    yfine_tavg                           List                                                                                  --   
    meshlist_tavg                        List                                                                                  --   
    GlacierMelt                          Array         melt from glacier                                                       m    
    GlacierRain                          Array         rain on glacier                                                         m    
    prec                                 Array         precipitation in the unit of the input maps (output variable)           input
    temp                                 Array         average temperature in the unit of the input maps: K or degC (output)   input
    usepySnowClim                        Flag          Flag to use pySnowClim                                                  --   
    SnowFactor                           Array         Multiplier applied to precipitation that falls as snow                  --   
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize meteorological data reader.
        
        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.model = model
        self.var = model.var
        # index meteo cell -> model cell for each shape of the meteo input (see fine_index)
        self.fineindex = {}

    def fine_index(self, shape, resoint):
        """
        Index of the meteo cell for each model cell (compressed order), for meteo maps coarser than the base maps.

        The meteo map (shape: rows, cols of the cut meteo window) is spread to the fine grid (resoint x resoint model
        cells per meteo cell), cut to cutmapVfine and compressed with the mask -> meteo.ravel()[index] gives the same
        as kron_ones + cut + compressArray. Calculated once for each shape and stored.

        Returns False if the fine window does not fit into the spread meteo map (then the old way is used,
        which also gives the error message).
        """
        key = (tuple(shape), resoint)
        if key not in self.fineindex:
            idx = False
            if len(shape) == 2 and min(cutmapVfine[0], cutmapVfine[2]) >= 0:
                rows = np.arange(cutmapVfine[2], cutmapVfine[3]) // resoint
                cols = np.arange(cutmapVfine[0], cutmapVfine[1]) // resoint
                if (len(rows), len(cols)) == maskinfo['mask'].shape and rows[-1] < shape[0] and cols[-1] < shape[1]:
                    index2d = rows[:, None] * shape[1] + cols[None, :]
                    # same selection and order as compressArray
                    idx = np.ma.compressed(np.ma.masked_array(index2d, maskinfo['mask']))
            self.fineindex[key] = idx
        return self.fineindex[key]

    def check_celsius(self, values, mapname):
        """
        Check on the first day if a temperature map is in deg C after the conversion (TemperatureInKelvin).

        Values below -100 or above 100 deg C point to a wrong temperature flag (Kelvin instead of Celsius or vice versa).
        """
        if dateVar['curr'] == 1:
            testtemp = np.nanmin(values)
            if (testtemp < -100) or (testtemp > 100):
                msg = "Error 601: Check temperature flag in [Option]: " + mapname + \
                      " might be Kelvin instead Celsius or vice versa\n"
                msg += mapname + ": " + cbinding(mapname) + "\n"
                raise CWATMError(msg)

    def initial(self):
        """
        Initialize meteorological data processing configuration.
        
        Sets up spatial resolution relationships between meteorological forcing
        data and model domain, configures downscaling parameters, determines
        required meteorological variables based on evapotranspiration method,
        and prepares data structures for efficient data access.
        
        Notes
        -----
        Key initialization tasks:
        - Resolution matching between meteo data and model grid
        - WorldClim downscaling configuration setup
        - Variable selection based on PET calculation method
        - Coordinate system and spatial extent validation
        - Multi-file NetCDF data preparation
        """

        # fit meteorological forcing data to size and resolution of mask map
        # -------------------------------------------------------------------

        name = cbinding('PrecipitationMaps')
        nameall = glob.glob(os.path.normpath(name))
        if not nameall:
            msg = "Error 225: In readmeteo, cannot find precipitation maps "
            raise CWATMFileError(name, msg, sname='PrecipitationMaps')
        namemeteo = nameall[0]
        latmeteo, lonmeteo, _, invcellmeteo, _, _ = readCoordNetCDF(namemeteo)

        nameldd = cbinding('Ldd')
        latldd, lonldd, _, invcellldd, _, _ = readCoord(nameldd)
        maskmapAttr['reso_mask_meteo'] = round(invcellldd / invcellmeteo)
        if maskmapAttr['reso_mask_meteo'] < 1:
            msg = "Error: the meteo forcing (" + namemeteo + ") has a finer resolution than the base maps (" + \
                  nameldd + ")\nMeteo maps have to be at the same or a coarser resolution than the base maps\n"
            raise CWATMError(msg)

        # if meteo maps have the same extend as the other spatial static maps -> meteomapsscale = True
        self.var.meteomapsscale = True
        if invcellmeteo != invcellldd:
            if (not (Flags['quiet'])) and (not (Flags['veryquiet'])) and (not (Flags['check'])):
                msg = ("Resolution of meteo forcing is " + str(maskmapAttr['reso_mask_meteo']) + 
                       " times higher than base maps.")
                print(msg)
            self.var.meteomapsscale = False

        cutmap[0], cutmap[1], cutmap[2], cutmap[3] = mapattrNetCDF(nameldd)
        for i in range(4):
            cutmapFine[i] = cutmap[i]

        # for downscaling meteomaps , Wordclim data at a finer resolution is used
        # here it is necessary to clip the wordclim data so that they fit to meteo dataset
        self.var.meteodown = False
        # if interpolationmethod not defined in settingsfil, use spline interpolation
        self.var.InterpolationMethod = 'spline'
        self.var.buffer = False
        if "usemeteodownscaling" in binding:
            self.var.meteodown = returnBool('usemeteodownscaling')
            if 'InterpolationMethod' in binding:
                # interpolation option can be spline or kron
                self.var.InterpolationMethod = cbinding('InterpolationMethod')
                if self.var.InterpolationMethod != 'spline' and self.var.InterpolationMethod != 'kron':
                    msg = 'Error: InterpolationMethod in settings file must be one of the following: "spline", "kron", but it is {}'.format(self.var.InterpolationMethod)
                    raise CWATMError(msg)

        check_clim = False
        if self.var.meteodown:
            check_clim = checkMeteo_Wordclim(namemeteo, cbinding('downscale_wordclim_prec'))

        # in case other mapsets are used e.g. Cordex RCM meteo data
        if (latldd != latmeteo) or (lonldd != lonmeteo):
            cutmapFine[0], cutmapFine[1], cutmapFine[2], cutmapFine[3], cutmapVfine[0], cutmapVfine[1], cutmapVfine[2], cutmapVfine[3] = mapattrNetCDFMeteo(namemeteo)

        if not self.var.meteomapsscale:
            # if the cellsize of the spatial dataset e.g. ldd, soil etc is not the same as the meteo maps than:
            cutmapFine[0], cutmapFine[1],cutmapFine[2],cutmapFine[3],cutmapVfine[0], cutmapVfine[1],cutmapVfine[2],cutmapVfine[3]  = mapattrNetCDFMeteo(namemeteo)
            # downscaling wordlclim maps
            for i in range(4): cutmapGlobal[i] = cutmapFine[i]

            if not(check_clim):
               # for downscaling it is always cut from the global map
                if (latldd != latmeteo) or (lonldd != lonmeteo):
                    cutmapGlobal[0] = int(cutmap[0] / maskmapAttr['reso_mask_meteo'])
                    cutmapGlobal[2] = int(cutmap[2] / maskmapAttr['reso_mask_meteo'])
                    cutmapGlobal[1] = int(cutmap[1] / maskmapAttr['reso_mask_meteo']+0.999)
                    cutmapGlobal[3] = int(cutmap[3] / maskmapAttr['reso_mask_meteo']+0.999)

        # -------------------------------------------------------------------
        self.var.includeGlaciers = False
        if 'includeGlaciers' in option:
            self.var.includeGlaciers = checkOption('includeGlaciers')
            self.var.includeOnlyGlaciersMelt = False
            if 'includeOnlyGlaciersMelt' in binding:
                self.var.includeOnlyGlaciersMelt = returnBool('includeOnlyGlaciersMelt')

        self.var.preMaps = 'PrecipitationMaps'
        self.var.tempMaps = 'TavgMaps'
        self.var.evaTMaps = 'ETMaps'
        self.var.eva0Maps = 'E0Maps'
        self.var.RSDSMaps = 'RSDSMaps'
        self.var.RSDLMaps = 'RSDLMaps'
        
        if self.var.includeGlaciers:
            self.var.glaciermeltMaps = 'MeltGlacierMaps'
            if not self.var.includeOnlyGlaciersMelt:
                self.var.glacierrainMaps = 'PrecGlacierMaps'


        # use radiation term in snow melt
        self.var.snowmelt_radiation = False
        if 'snowmelt_radiation' in binding:
            self.var.snowmelt_radiation = returnBool('snowmelt_radiation')

        self.var.only_radiation = False
        if 'only_radiation' in binding:
            self.var.only_radiation = returnBool('only_radiation')

        self.var.only_radiation_Wm2 = False
        if 'only_radiation_Wm2' in binding:
            self.var.only_radiation_Wm2 = returnBool('only_radiation_Wm2')

        self.var.era5 = False
        if 'era5' in binding:
            self.var.era5 = returnBool('era5')


        # for high resolution runs eg 1 arcmin the rlds maps are too coarse
        self.var.without_rlds = False
        if 'without_rlds' in binding:
            self.var.without_rlds = returnBool('without_rlds')
        if self.var.only_radiation:
            self.var.without_rlds = True

        # PET modus 0: potential evaporation is not calculated but read from ET maps (calc_evaporation = False)
        # the PET_modus from the settings file is only used if calc_evaporation = True (see below)
        self.var.pet_modus = 0

        self.var.calc_evapo = checkOption('calc_evaporation')

        # dew point temperature maps are read (pySnowClim with useTdew or era5)
        self.var.useTdew = False
        # Check if option pySnowClim exists
        self.var.usepySnowClim = checkOption('usepySnowClim', True)
        if self.var.usepySnowClim:
            self.var.useTdew = returnBool('useTdew')
            # if pySnowClim is used then all meteo var has to be read anyway
            # and missing meteo variables have to be calculated in evapoPot.py
            self.var.calc_evapo = True

        # flags used every time step: read once here
        # if temperature is in Kelvin -> conversion to deg C
        self.var.TemperatureInKelvin = checkOption('TemperatureInKelvin')
        self.var.ZeroKelvin = 273.15 if self.var.TemperatureInKelvin else 0.0
        # specific humidity (QAirMaps) instead of relative humidity (RhsMaps), only used if evaporation is calculated
        # (era5: humidity is calculated from the dew point temperature)
        self.var.useHuss = False
        if self.var.calc_evapo and not self.var.only_radiation and not self.var.era5:
            self.var.useHuss = returnBool('useHuss')
        if self.var.era5 and self.var.only_radiation:
            msg = "Error: era5 = True and only_radiation = True cannot be used together\n" \
                  "era5 uses surface pressure, short and long wave radiation and dew point temperature, " \
                  "only_radiation (e.g. EMO) uses daily radiation and vapour pressure\n"
            raise CWATMError(msg)
        # potential evaporation maps have the same resolution as the other meteo maps
        self.var.ETsamePr = False
        if "ETsamePr" in binding:
            self.var.ETsamePr = returnBool('ETsamePr')

        if self.var.calc_evapo:
            # if PET_modus is missing use Penman Monteith
            self.var.pet_modus = 1
            if "PET_modus" in option:
                self.var.pet_modus = checkOption('PET_modus')

            # pySnowClim needs wind, air pressure, humidity and radiation: these are only read here and
            # completed in evaporationPot.dynamic_1, which runs for PET_modus 1 (Penman-Monteith) and 3 (Yang)
            if self.var.usepySnowClim and self.var.pet_modus not in (1, 3):
                msg = "Error: usepySnowClim = True needs PET_modus 1 or 3 - with PET_modus " + \
                      str(self.var.pet_modus) + " wind, air pressure, humidity or radiation are missing " \
                      "for the snow model\n"
                raise CWATMError(msg)

            if self.var.only_radiation:
                # if addiation snowmlet from radiation
                #if self.var.snowmelt_radiation:
                #    meteomaps = [self.var.preMaps, self.var.tempMaps, 'RGDMaps','EActMaps']
                #else:
                # for maps from EMO-5 with total radiation and vapor pressure instead of huss, air pressure, rsds and rlds
                meteomaps = [self.var.preMaps, self.var.tempMaps,'TminMaps','TmaxMaps','WindMaps','RGDMaps','EActMaps']
            else:
                meteomaps = [self.var.preMaps, self.var.tempMaps,'TminMaps','TmaxMaps','PSurfMaps','WindMaps','RSDSMaps','RSDLMaps']
                if self.var.useHuss:
                    meteomaps.append('QAirMaps')
                else:
                    meteomaps.append('RhsMaps')
            if self.var.pet_modus == 4:
                # Priestley-Taylor: tmin, tmax, tavg, rsds, rlds (or rsd)
                if not(self.var.only_radiation):
                    meteomaps = [self.var.preMaps, self.var.tempMaps, 'TminMaps', 'TmaxMaps','RSDSMaps', 'RSDLMaps']
            if self.var.pet_modus == 5:
                # for modified Thornthwaite: uses only tmin, tmax, tavg
                meteomaps = [self.var.preMaps, self.var.tempMaps, 'TminMaps', 'TmaxMaps']
            if self.var.usepySnowClim and self.var.useTdew:
                meteomaps.append('TdewMaps')

            if self.var.era5:
                meteomaps = [self.var.preMaps, self.var.tempMaps,'TminMaps','TmaxMaps','PSurfMaps',
                             'WindMaps','RSDSMaps','RSDLMaps','TdewMaps']
                self.var.useTdew = True


            if self.var.includeGlaciers:
                meteomaps.append(self.var.glaciermeltMaps)
                if not self.var.includeOnlyGlaciersMelt:
                    meteomaps.append(self.var.glacierrainMaps)

        # no evaporation -> less maps
        else:
            meteomaps = [self.var.preMaps, self.var.tempMaps]
            # snow calibration (stopaftersnow): no potential evaporation maps needed
            if not self.var.stopaftersnow:
                meteomaps += [self.var.evaTMaps, self.var.eva0Maps]
            if self.var.snowmelt_radiation:
                if self.var.only_radiation:
                    meteomaps.append('RGDMaps')
                    meteomaps.append('EActMaps')
                else:
                    meteomaps.append(self.var.RSDSMaps)
                    meteomaps.append(self.var.RSDLMaps)
            if self.var.includeGlaciers:
                meteomaps.append(self.var.glaciermeltMaps)
                if not self.var.includeOnlyGlaciersMelt:
                    meteomaps.append(self.var.glacierrainMaps)

        multinetdf(meteomaps,self.var.buffer)

        # calibration: names of the variables stored in memory in the first run and restored in the warm runs
        # the list depends only on the settings -> same order in the calibration run and in the warm runs
        # stored after evaporationPot -> derived variables (ETRef, EAct, huss ...) are available, warm runs skip evaporationPot
        self.var.meteo_names = ['Precipitation', 'Tavg']
        if not self.var.stopaftersnow:
            self.var.meteo_names += ['ETRef', 'EWRef']
        if self.var.usepySnowClim:
            # forcing of pySnowClim (snow_pysnowclim.py)
            self.var.meteo_names += ['Wind', 'Rsds', 'Rsdl', 'Psurf', 'huss', 'rhs', 'Tdew']
        elif self.var.snowmelt_radiation:
            # radiation snow melt (snow.py): incoming long wave estimated with FAO-56 (needs EAct) or measured (Rsdl)
            # same condition as snowFAOlongwave in snow.py
            if self.var.without_rlds and (self.var.only_radiation or self.var.calc_evapo):
                self.var.meteo_names += ['Rsds', 'EAct']
            else:
                self.var.meteo_names += ['Rsds', 'Rsdl']
        if self.var.includeGlaciers:
            self.var.meteo_names.append('GlacierMelt')
            if not self.var.includeOnlyGlaciersMelt:
                self.var.meteo_names.append('GlacierRain')

        # Conversion factor from [W] to [MJ]
        self.var.WtoMJ = 86400 * 1E-6

        # downscaling to wordclim, set parameter to 0 in case they are only used as dummy
        self.var.wc2_tavg = 0
        self.var.wc4_tavg = 0
        self.var.wc2_tmin = 0
        self.var.wc4_tmin = 0
        self.var.wc2_tmax = 0
        self.var.wc4_tmax = 0
        self.var.wc2_prec = 0
        self.var.wc4_prec = 0

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def downscaling2(self,input, downscaleName = "", wc2 = 0 , wc4 = 0, x=None, y=None, xfine=None, yfine=None, meshlist=None, MaskMapBoundaries= None, downscale = 0):
        """
        Spatially downscale meteorological data using delta method with WorldClim.
        
        Performs statistical downscaling of coarse-resolution meteorological data
        to higher spatial resolution using high-resolution climatological data
        from WorldClim. Supports multiple interpolation methods including spline,
        and Kronecker product approaches.
        
        Parameters
        ----------
        input : numpy.ndarray
            Coarse-resolution input meteorological data
        downscaleName : str, optional
            Name of high-resolution WorldClim dataset for downscaling
        wc2 : numpy.ndarray, optional
            High-resolution WorldClim climatological data
        wc4 : numpy.ndarray, optional
            WorldClim data upscaled to input resolution
        MaskMapBoundaries : tuple, optional
            Boundary flags indicating if mask touches input data boundaries
        downscale : int, optional
            Downscaling mode: 0=no scaling, 1=temperature, 2=precipitation
            
        Returns
        -------
        numpy.ndarray or tuple
            Downscaled meteorological data and auxiliary arrays
            
        Notes
        -----
        Implements delta method downscaling based on:
        - Temperature: additive corrections using climatological differences
        - Precipitation: multiplicative corrections using climatological ratios
        
        References
        ----------
        Moreno and Hasenauer (2015): Spatial downscaling of European 
        climate data. International Journal of Climatology.
        
        Mosier et al. (2018): 30-arcsecond monthly climate surfaces 
        with global land coverage. International Journal of Climatology.
        """

        reso = maskmapAttr['reso_mask_meteo']
        resoint = int(reso)

        if self.var.meteomapsscale:
            if downscale == 0:
                return input
            else:
                return input, wc2, wc4

        # index meteo cell -> model cell: input.ravel()[idx] is the same as kron_ones + cut to cutmapVfine + compressArray
        # but without the big fine arrays (False if it cannot be used -> old way with kron_ones)
        idx = False
        if not np.ma.isMaskedArray(input):
            idx = self.fine_index(np.shape(input), resoint)

        if downscale == 0:
            # no downscaling: each model cell gets the value of its meteo cell -> one gather with the index
            if idx is not False:
                out = np.asarray(input, dtype=np.float64).ravel()[idx]
                # as in compressArray
                out[out > 1.E20] = 0.
                out[out < -1.E20] = 0.
                return out

        # this is creating an array resoint times bigger than input, by copying each item resoint times in x and y direction
        # only needed for kron interpolation (part of the formula) or if the index cannot be used
        # (with spline interpolation the fine input is only used to fill missing values -> done after compressing)
        down3 = None
        if self.var.InterpolationMethod == 'kron' or idx is False:
            down3 = kron_ones(input, resoint)

        if downscale == 0:
            down2 = down3[cutmapVfine[2]:cutmapVfine[3], cutmapVfine[0]:cutmapVfine[1]].astype(np.float64)
            input = compressArray(down2)
            return input
        else:
            if dateVar['newStart'] or dateVar['newMonth']:  # loading every month a new map
                wc1 = readnetcdf2(downscaleName, dateVar['currDate'], useDaily='month', compress = False, cut = False)
                wc2 = wc1[(cutmapGlobal[2]) * resoint: (cutmapGlobal[3]) * resoint,
                      (cutmapGlobal[0]) * resoint: (cutmapGlobal[1]) * resoint]
                # missing values: readnetcdf2 returns the fill value (e.g. 1e20 or -3.4e38) of masked cells, but the
                # downscaling below expects NaN (nanmean, isnan -> input value is used) -> set fill values to NaN
                wc2[np.abs(wc2) > 1.E19] = np.nan
                rows = wc2.shape[0]
                cols = wc2.shape[1]
                wc3 =  wc2.reshape(rows//resoint,resoint,cols//resoint,resoint)
                wc4 =  np.nanmean(wc3, axis=(1, 3))
                # wc4 is as big as the input array -> average of the fine scale downscale map

                if self.var.InterpolationMethod == 'kron':
                    if downscale == 2:  # precipitation
                        # wc4: average of wordclim on the bigger input raster scale (see above)
                        wc3kron = kron_ones(wc4, resoint)
                        # the average values are spread out to the fine scale
                        # looks like quot_wc, but wc2 = input, wc3kron = wc4
                        wc4 = divideValues(wc2, wc3kron)

        if downscale == 1: # Temperature
            diff_wc = wc4 - input

            if self.var.InterpolationMethod == 'spline':
                #diffSmooth = scipy.ndimage.zoom(diff_wc, resoint, order=1)
                diffSmooth = zoom(diff_wc, resoint)
                down1 = wc2 - diffSmooth

            elif self.var.InterpolationMethod == 'kron':
                diff_wc = wc2 - down3
                # on fine scale: wordclim fine scale - spreaded input data (same value for each big cell)
                wc3 = diff_wc.reshape(wc2.shape[0] // resoint, resoint, wc2.shape[1] // resoint, resoint)
                wc4 = np.nanmean(wc3, axis=(1, 3))
                wc4kron = kron_ones(wc4, resoint)
                # wordclim is averaged on big cell scale and the average is spread out to fine raster
                down1 = diff_wc - wc4kron + down3
                # result is the fine scale input data + the difference of wordclim - input data - the average difference of wordclim - input

        if downscale == 2:  # precipitation
            if self.var.InterpolationMethod == 'spline':
                quot_wc = divideValues(input, wc4)
                #quotSmooth = scipy.ndimage.zoom(quot_wc, resoint, order=1)
                quotSmooth = zoom(quot_wc, resoint)
                down1 = wc2 * quotSmooth
            elif self.var.InterpolationMethod == 'kron':
                down1 = down3 * wc4

        # missing values (NaN, for precipitation also inf e.g. division by 0) -> value of the meteo cell (down3)
        down2 = down1[cutmapVfine[2]:cutmapVfine[3], cutmapVfine[0]:cutmapVfine[1]].astype(np.float64)
        if down3 is None:
            # without the fine input: compress first (as compressArray), then fill the missing values with the index
            if down2.shape != maskinfo['mask'].shape:
                compressArray(down2)  # gives Error 105
            out = np.ma.compressed(np.ma.masked_array(down2, maskinfo['mask']))
            missing = np.isnan(out) if downscale == 1 else ~np.isfinite(out)
            if missing.any():
                out[missing] = np.asarray(input, dtype=np.float64).ravel()[idx][missing]
            # as in compressArray
            out[out > 1.E20] = 0.
            out[out < -1.E20] = 0.
            return out, wc2, wc4

        missing = np.isnan(down1) if downscale == 1 else ~np.isfinite(down1)
        down1 = np.where(missing, down3, down1)
        down2 = down1[cutmapVfine[2]:cutmapVfine[3], cutmapVfine[0]:cutmapVfine[1]].astype(np.float64)
        input = compressArray(down2)
        return input, wc2, wc4

     # --- end downscaling ----------------------------





    def dynamic(self):
        """
        Read and process meteorological data for current time step.
        
        Loads meteorological forcing data from NetCDF files for the current time step,
        applies spatial downscaling when configured, performs unit conversions,
        and validates data ranges. Handles different variable sets depending on
        evapotranspiration calculation method.
        
        Notes
        -----
        Processing workflow:
        - Load precipitation data and convert units
        - Read temperature data with Kelvin/Celsius handling
        - Apply spatial downscaling when configured
        - Load additional variables based on PET method
        - Perform data validation and range checks
        - Store data for calibration mode if enabled
        
        Variable loading depends on configuration:
        - Basic mode: precipitation, temperature, reference ET
        - Full PET mode: additional temperature extremes, humidity, wind, pressure
        - Radiation mode: solar and longwave radiation data
        - Glacier mode: glacier-specific precipitation and melt data
        """


        # For calibration - loading meteo data only once
        if Flags['warm']:
            # if warmstart use stored meteo variables
            no = dateVar['curr']-1
            for i, name in enumerate(self.var.meteo_names):
                setattr(self.var, name, self.var.meteo[i, no])
            # output variables prec and temp in the unit of the input maps (as in a normal run)
            self.var.prec = self.var.Precipitation / self.var.con_precipitation
            self.var.temp = self.var.Tavg + self.var.ZeroKelvin if self.var.TemperatureInKelvin else self.var.Tavg.copy()
            return
        # End calibration warm run

        # -------------------------------------------------------------
        # read netcdf data

        self.var.Precipitation = readmeteodata(self.var.preMaps, dateVar['currDate'], addZeros=True, mapsscale = self.var.meteomapsscale, buffering= self.var.buffer)
        self.var.Precipitation = self.var.Precipitation * self.var.DtDay * self.var.con_precipitation

        self.var.Precipitation = np.maximum(0., self.var.Precipitation)
        if self.var.meteodown:
            self.var.Precipitation, self.var.wc2_prec, self.var.wc4_prec = self.downscaling2(self.var.Precipitation, "downscale_wordclim_prec", self.var.wc2_prec, self.var.wc4_prec, downscale=2)
        else:
            self.var.Precipitation = self.downscaling2(self.var.Precipitation, "downscale_wordclim_prec", self.var.wc2_prec, self.var.wc4_prec, downscale=0)

        # precipitation in the unit of the input maps (output variable), Precipitation is in [m] per time step
        self.var.prec = self.var.Precipitation / self.var.con_precipitation
        if Flags['check']:
            checkmap(self.var.preMaps, meteofiles[self.var.preMaps][flagmeteo[self.var.preMaps]][0], self.var.Precipitation)


        # 273.15 if temperature is in Kelvin -> conversion to deg C, otherwise 0 (see initial)
        ZeroKelvin = self.var.ZeroKelvin

        self.var.Tavg = readmeteodata(self.var.tempMaps,dateVar['currDate'], addZeros=True, zeros = ZeroKelvin, mapsscale = self.var.meteomapsscale, buffering= self.var.buffer)

        if self.var.meteodown:
            self.var.Tavg, self.var.wc2_tavg, self.var.wc4_tavg  = self.downscaling2(self.var.Tavg, "downscale_wordclim_tavg", self.var.wc2_tavg, self.var.wc4_tavg, downscale=1)
        else:
            self.var.Tavg  = self.downscaling2(self.var.Tavg, "downscale_wordclim_tavg", self.var.wc2_tavg, self.var.wc4_tavg, downscale=0)
        # average temperature in the unit of the input maps: K or deg C (output variable)
        self.var.temp = self.var.Tavg.copy()

        # average DAILY temperature (even if you are running the model
        # on say an hourly time step) [degrees C]
        if self.var.TemperatureInKelvin:
            self.var.Tavg -= ZeroKelvin

        # check on the first date if Temperature is really kelvin
        self.check_celsius(self.var.Tavg, self.var.tempMaps)


        if self.var.includeGlaciers:
            self.var.GlacierMelt = readmeteodata(self.var.glaciermeltMaps, dateVar['currDate'], addZeros=True, mapsscale = True, extendback = 1,glacier=True)
            # Glaciermelt and Glacierrain is preprocessed after OGGM to have a factor of 1.0
            # -> here glacier melt is again multiplied by the CwatM snow factor to have the same values
            self.var.GlacierMelt = self.var.GlacierMelt * self.var.SnowFactor
            # extendback -> if simulation starts earlier than first glacier map -> day of the year of first year is used
            if not self.var.includeOnlyGlaciersMelt:
                self.var.GlacierRain = readmeteodata(self.var.glacierrainMaps, dateVar['currDate'], addZeros=True, mapsscale = True, extendback = 1, glacier=True)

        if Flags['check']:


            checkmap(self.var.tempMaps, meteofiles[self.var.tempMaps][flagmeteo[self.var.tempMaps]][0], self.var.Tavg)

        if self.var.calc_evapo or self.var.snowmelt_radiation:
            # for new snow calculation radiation is needed
            if self.var.pet_modus < 5:
                # radiation is read for PET_modus 1-4 and for radiation snow melt without calculated evaporation (pet_modus 0)
                # modified Thornthwaite (PET_modus 5) uses only temperature -> no radiation maps
                if self.var.only_radiation:
                    # read daily radiation [in W/m2 or J/m2/day] and convert to MJ/m2/day
                    # named here Rsds instead of rds, because use in evaproationPot in the same way as rsds
                    self.var.Rsds = readmeteodata('RGDMaps', dateVar['currDate'], addZeros=True, mapsscale=self.var.meteomapsscale)
                    if self.var.only_radiation_Wm2:
                        self.var.Rsds = self.downscaling2(self.var.Rsds) * self.var.WtoMJ  # convert from W/m2 to MJ/m2/day
                    else:
                        self.var.Rsds = self.downscaling2(self.var.Rsds) * 0.000001  # convert from J/m2/day to MJ/m2/day

                    # read daily vapor pressure [in hPa]
                    self.var.EAct = readmeteodata('EActMaps', dateVar['currDate'], addZeros=True, mapsscale=self.var.meteomapsscale)
                    self.var.EAct = self.downscaling2(self.var.EAct) * 0.1  # convert from hPa to kPa
                else:
                    self.var.Rsds = readmeteodata('RSDSMaps', dateVar['currDate'], addZeros=True, mapsscale = self.var.meteomapsscale)
                    self.var.Rsds = self.downscaling2(self.var.Rsds)
                        # radiation surface downwelling shortwave maps [W/m2]

                    self.var.Rsdl = readmeteodata('RSDLMaps', dateVar['currDate'], addZeros=True, mapsscale = self.var.meteomapsscale)
                    self.var.Rsdl = self.downscaling2(self.var.Rsdl)
                        # radiation surface downwelling longwave maps [W/m2]

                    # conversion from W/m2 to MJ/m2/day
                    self.var.Rsds = self.var.Rsds * self.var.WtoMJ
                    self.var.Rsdl = self.var.Rsdl * self.var.WtoMJ

        # -----------------------------------------------------------------------
        # if evaporation has to be calculated load all the meteo map sets
        # Temparture min, max;  Windspeed,  specific humidity or relative humidity, psurf
        # -----------------------------------------------------------------------

        if self.var.calc_evapo:

            #self.var.TMin = readnetcdf2('TminMaps', dateVar['currDate'], addZeros = True, zeros = ZeroKelvin, meteo = True)
            self.var.TMin = readmeteodata('TminMaps',dateVar['currDate'], addZeros=True, zeros=ZeroKelvin, mapsscale = self.var.meteomapsscale, buffering= self.var.buffer)
            if self.var.meteodown:
                self.var.TMin, self.var.wc2_tmin, self.var.wc4_tmin = self.downscaling2(self.var.TMin, "downscale_wordclim_tmin", self.var.wc2_tmin, self.var.wc4_tmin, downscale=1)
            else:
                self.var.TMin = self.downscaling2(self.var.TMin, "downscale_wordclim_tmin", self.var.wc2_tmin, self.var.wc4_tmin, downscale=0)

            #self.var.TMax = readnetcdf2('TmaxMaps', dateVar['currDate'], addZeros = True, zeros = ZeroKelvin, meteo = True)
            self.var.TMax = readmeteodata('TmaxMaps', dateVar['currDate'], addZeros=True, zeros=ZeroKelvin, mapsscale = self.var.meteomapsscale, buffering= self.var.buffer)
            if self.var.meteodown:
                self.var.TMax, self.var.wc2_tmax, self.var.wc4_tmax = self.downscaling2(self.var.TMax, "downscale_wordclim_tmax", self.var.wc2_tmax, self.var.wc4_tmax, downscale=1)
            else:
                self.var.TMax = self.downscaling2(self.var.TMax, "downscale_wordclim_tmax", self.var.wc2_tmax, self.var.wc4_tmax, downscale=0)

            if self.var.TemperatureInKelvin:
                self.var.TMin -= ZeroKelvin
                self.var.TMax -= ZeroKelvin
            if Flags['check']:
                # after the conversion: in deg C as Tavg (the rows of readmeteodata are in the unit of the input maps)
                checkmap('TminMaps', meteofiles['TminMaps'][flagmeteo['TminMaps']][0], self.var.TMin)
                checkmap('TmaxMaps', meteofiles['TmaxMaps'][flagmeteo['TmaxMaps']][0], self.var.TMax)
            # check on the first date if TMin and TMax are really in the same unit as Tavg
            self.check_celsius(self.var.TMin, 'TminMaps')
            self.check_celsius(self.var.TMax, 'TmaxMaps')

            if self.var.pet_modus == 5:
                if dateVar['newStart'] or dateVar['newYear']:
                    if self.var.meteomapsscale:
                        # thermal index at the resolution of the base maps
                        self.var.thermalI = readnetcdf2('thermalIndexFile', dateVar['currDate'], "yearly", value="thermalindex", compress=True)
                    else:
                        # thermal index on the grid of the meteo maps: cut the same window as the meteo maps
                        # (see readmeteodata) and spread it to the base maps
                        thermalI = readnetcdf2('thermalIndexFile', dateVar['currDate'], "yearly", cut=False, value="thermalindex", compress=False)
                        thermalI = thermalI[cutmapFine[2]:cutmapFine[3], cutmapFine[0]:cutmapFine[1]]
                        self.var.thermalI = self.downscaling2(thermalI)

            elif self.var.pet_modus == 4:
                self.var.Wind = 0
                # no additional data needed
            else:
                # with priestley ET or Thornewaite ET no wind, psurf,qair available
                self.var.Wind = readmeteodata('WindMaps', dateVar['currDate'], addZeros=True, mapsscale = self.var.meteomapsscale)
                self.var.Wind = self.downscaling2(self.var.Wind)
                # wind speed maps at 10m [m/s]

                # Adjust wind speed for measurement height: wind speed measured at
                # 10 m, but needed at 2 m height
                # Shuttleworth, W.J. (1993) in Maidment, D.R. (1993), p. 4.36
                self.var.Wind = self.var.Wind * 0.749

                if not self.var.only_radiation:

                    #self.var.Psurf = readnetcdf2('PSurfMaps', dateVar['currDate'], addZeros = True, meteo = True)
                    self.var.Psurf = readmeteodata('PSurfMaps', dateVar['currDate'], addZeros=True, mapsscale = self.var.meteomapsscale)
                    self.var.Psurf = self.downscaling2(self.var.Psurf)
                    # Instantaneous surface pressure[Pa]
                    # conversion [Pa] to [KPa]
                    self.var.Psurf = self.var.Psurf * 0.001

                    # era5: dew point temperature instead of humidity -> Tdew is read below (useTdew = True)
                    if not self.var.era5:
                        if self.var.useHuss:
                            self.var.huss = readmeteodata('QAirMaps', dateVar['currDate'], addZeros=True, mapsscale =self.var.meteomapsscale)
                            self.var.huss = self.downscaling2(self.var.huss)
                            # 2 m istantaneous specific humidity[kg / kg]
                        else:
                            self.var.rhs = readmeteodata('RhsMaps', dateVar['currDate'], addZeros=True, mapsscale =self.var.meteomapsscale)
                            self.var.rhs = self.downscaling2(self.var.rhs)

        # if pot evaporation is already precalulated
        else:

            if not(self.var.stopaftersnow):
            # in case ET_ref is the same resolution as the other meteo input map, there is an optional flag in settings which checks this
                if self.var.ETsamePr:
                    self.var.EWRef = readmeteodata(self.var.eva0Maps, dateVar['currDate'], addZeros=True,  mapsscale=self.var.meteomapsscale)
                    self.var.EWRef = self.var.EWRef * self.var.DtDay * self.var.con_e
                    self.var.EWRef = self.downscaling2(self.var.EWRef, "downscale_wordclim_prec", self.var.wc2_prec, self.var.wc4_prec, downscale=0)

                    self.var.ETRef = readmeteodata(self.var.evaTMaps, dateVar['currDate'], addZeros=True,  mapsscale=self.var.meteomapsscale)
                    self.var.ETRef = self.var.ETRef *self.var.DtDay * self.var.con_e
                    self.var.ETRef = self.downscaling2(self.var.ETRef, "downscale_wordclim_prec", self.var.wc2_prec, self.var.wc4_prec, downscale=0)

                else:
                    self.var.EWRef = readmeteodata(self.var.eva0Maps, dateVar['currDate'], addZeros=True, mapsscale = True)
                    self.var.EWRef = self.var.EWRef * self.var.DtDay * self.var.con_e
                    self.var.ETRef = readmeteodata(self.var.evaTMaps, dateVar['currDate'], addZeros=True, mapsscale = True)
                    self.var.ETRef = self.var.ETRef *self.var.DtDay * self.var.con_e

                    # potential evaporation rate from water surface (conversion to [m] per time step)
                    # potential evaporation rate from a bare soil surface (conversion # to [m] per time step)

        # dew point temperature: pySnowClim with useTdew (otherwise Tdew is calculated from EAct in evaporationPot)
        # or era5 (instead of humidity)
        if self.var.useTdew:
            self.var.Tdew = readmeteodata('TdewMaps',
                                          dateVar['currDate'],
                                          addZeros=True, zeros=ZeroKelvin,
                                          mapsscale = self.var.meteomapsscale,
                                          buffering= self.var.buffer)
            self.var.Tdew = self.downscaling2(self.var.Tdew)
            if self.var.TemperatureInKelvin:
                self.var.Tdew -= ZeroKelvin
            # check on the first date if the dewpoint is really in the same unit as the temperature
            self.check_celsius(self.var.Tdew, 'TdewMaps')

    def store_calib(self):
        """
        Store the meteo variables of the current time step in memory (first calibration run).

        Called from cwatm_dynamic after evaporationPot, so derived variables (ETRef, EWRef, EAct, huss ...)
        are available. The variables are listed in self.var.meteo_names (see initial) and restored in the
        warm runs at the beginning of dynamic.
        """
        no = dateVar['curr'] - 1
        if no == 0:
            # first time step: allocate memory for all time steps
            self.var.meteo = np.zeros([len(self.var.meteo_names), 1 + dateVar["intEnd"] - dateVar["intStart"],
                                       len(self.var.Precipitation)])
        for i, name in enumerate(self.var.meteo_names):
            self.var.meteo[i, no] = getattr(self.var, name)
