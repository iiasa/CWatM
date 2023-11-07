# -------------------------------------------------------------------------
# Name:        READ METEO input maps
# Purpose:
#
# Author:      PB
#
# Created:     13/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
import scipy.ndimage
from scipy.interpolate import RegularGridInterpolator

class readmeteo(object):
    """
    READ METEOROLOGICAL DATA

    reads all meteorological data from netcdf4 files

    **Global variables**

    =====================================  ======================================================================  =====
    Variable [self.var]                    Description                                                             Unit 
    =====================================  ======================================================================  =====
    DtDay                                  seconds in a timestep (default=86400)                                   s    
    con_precipitation                      conversion factor for precipitation                                     --   
    con_e                                  conversion factor for evaporation                                       --   
    ETRef                                  potential evapotranspiration rate from reference crop                   m    
    Precipitation                          Precipitation (input for the model)                                     m    
    only_radiation                                                                                                  --
    TMin                                   minimum air temperature                                                 K    
    TMax                                   maximum air temperature                                                 K    
    Tavg                                   Input, average air Temperature                                          K    
    Rsds                                   short wave downward surface radiation fluxes                            W/m2 
    EAct                                                                                                           --   
    Psurf                                  Instantaneous surface pressure                                          Pa   
    Qair                                   specific humidity                                                       kg/kg
    Rsdl                                   long wave downward surface radiation fluxes                             W/m2 
    Wind                                   wind speed                                                              m/s  
    EWRef                                  potential evaporation rate from water surface                           m    
    meteomapsscale                         if meteo maps have the same extend as the other spatial static maps ->  --   
    meteodown                              if meteo maps should be downscaled                                      --   
    InterpolationMethod                                                                                            --   
    buffer                                                                                                         --   
    preMaps                                choose between steady state precipitation maps for steady state modflo  --   
    tempMaps                               choose between steady state temperature maps for steady state modflow   --   
    evaTMaps                               choose between steady state ETP water maps for steady state modflow or  --   
    eva0Maps                               choose between steady state ETP reference maps for steady state modflo  --   
    glaciermeltMaps                                                                                                --   
    glacierrainMaps                                                                                                --   
    wc2_tavg                               High resolution WorldClim map for average temperature                   K    
    wc4_tavg                               upscaled to low resolution WorldClim map for average temperature        K    
    wc2_tmin                               High resolution WorldClim map for min temperature                       K    
    wc4_tmin                               upscaled to low resolution WorldClim map for min temperature            K    
    wc2_tmax                               High resolution WorldClim map for max temperature                       K    
    wc4_tmax                               upscaled to low resolution WorldClim map for max temperature            K    
    wc2_prec                               High resolution WorldClim map for precipitation                         m    
    wc4_prec                               upscaled to low resolution WorldClim map for precipitation              m    
    xcoarse_prec                                                                                                   --   
    ycoarse_prec                                                                                                   --   
    xfine_prec                                                                                                     --   
    yfine_prec                                                                                                     --   
    meshlist_prec                                                                                                  --   
    xcoarse_tavg                                                                                                   --   
    ycoarse_tavg                                                                                                   --   
    xfine_tavg                                                                                                     --   
    yfine_tavg                                                                                                     --   
    meshlist_tavg                                                                                                  --   
    meteo                                                                                                          --   
    prec                                   precipitation in m                                                      m    
    temp                                   average temperature in Celsius deg                                      °C   
    WtoMJ                                  Conversion factor from [W] to [MJ] for radiation: 86400 * 1E-6          --   
    includeGlaciers                                                                                                --   
    includeOnlyGlaciersMelt                                                                                        --   
    GlacierMelt                                                                                                    --   
    GlacierRain                                                                                                    --   
    =====================================  ======================================================================  =====

    **Functions**
    """

    def __init__(self, model):
        self.model = model
        self.var = model.var

    def initial(self):
        """
        Initial part of meteo

        read multiple file of input
        """

        # fit meteorological forcing data to size and resolution of mask map
        #-------------------------------------------------------------------

        name = cbinding('PrecipitationMaps')
        nameall = glob.glob(os.path.normpath(name))
        if not nameall:
            msg = "Error 215: In readmeteo, cannot find precipitation maps "
            raise CWATMFileError(name, msg, sname='PrecipitationMaps')
        namemeteo = nameall[0]
        latmeteo, lonmeteo, cell, invcellmeteo, rows, cols = readCoordNetCDF(namemeteo)

        nameldd = cbinding('Ldd')
        #nameldd = os.path.splitext(nameldd)[0] + '.nc'
        #latldd, lonldd, cell, invcellldd, row, cols = readCoordNetCDF(nameldd)
        latldd, lonldd, cell, invcellldd, rows, cols = readCoord(nameldd)
        maskmapAttr['reso_mask_meteo'] = round(invcellldd / invcellmeteo)

        # if meteo maps have the same extend as the other spatial static maps -> meteomapsscale = True
        self.var.meteomapsscale = True
        if invcellmeteo != invcellldd:
            if (not(Flags['quiet'])) and (not(Flags['veryquiet'])) and (not(Flags['check'])):
                msg = "Resolution of meteo forcing is " + str(maskmapAttr['reso_mask_meteo']) + " times higher than base maps."
                print(msg)
            self.var.meteomapsscale = False

        cutmap[0], cutmap[1], cutmap[2], cutmap[3] = mapattrNetCDF(nameldd)
        for i in range(4): cutmapFine[i] = cutmap[i]

        # for downscaling meteomaps , Wordclim data at a finer resolution is used
        # here it is necessary to clip the wordclim data so that they fit to meteo dataset
        self.var.meteodown = False
        # if interpolationmethod not defined in settingsfil, use spline interpolation
        self.var.InterpolationMethod = 'spline'
        self.var.buffer = False
        if "usemeteodownscaling" in binding:
            self.var.meteodown = returnBool('usemeteodownscaling')
            if 'InterpolationMethod' in binding:
                # interpolation option can be spline or bilinear
                self.var.InterpolationMethod = cbinding('InterpolationMethod')
                if self.var.InterpolationMethod != 'bilinear' and self.var.InterpolationMethod != 'spline' and self.var.InterpolationMethod != 'kron':
                    msg = 'Error: InterpolationMethod in settings file must be one of the following: "spline" or  "bilinear", but it is {}'.format(self.var.InterpolationMethod)
                    raise CWATMError(msg)
                if self.var.InterpolationMethod == 'bilinear':
                    self.var.buffer = True

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
            # if radiation then now snow_melt radiation because it needs rsds and rsdl maps
            self.var.snowmelt_radiation = False

        if checkOption('calc_evaporation'):
            if self.var.only_radiation:
                # for maps from EMO-5 with total radiation and vapor pressure instead of huss, air pressure, rsds and rlds
                meteomaps = [self.var.preMaps, self.var.tempMaps,'TminMaps','TmaxMaps','WindMaps','RGDMaps','EActMaps']
            else:
                meteomaps = [self.var.preMaps, self.var.tempMaps,'TminMaps','TmaxMaps','PSurfMaps','WindMaps','RSDSMaps','RSDLMaps']
                if returnBool('useHuss'):
                    meteomaps.append('QAirMaps')
                else:
                    meteomaps.append('RhsMaps')


            if self.var.includeGlaciers:
                meteomaps.append(self.var.glaciermeltMaps)
                if not self.var.includeOnlyGlaciersMelt:
                    meteomaps.append(self.var.glacierrainMaps)

        # no evaporation -> less maps
        else:
            meteomaps = [self.var.preMaps, self.var.tempMaps, self.var.evaTMaps, self.var.eva0Maps]
            if self.var.snowmelt_radiation:
                meteomaps.append(self.var.RSDSMaps)
                meteomaps.append(self.var.RSDLMaps)
            if self.var.includeGlaciers:
                meteomaps.append(self.var.glaciermeltMaps)
                if not self.var.includeOnlyGlaciersMelt:
                    meteomaps.append(self.var.glacierrainMaps)

        multinetdf(meteomaps)

        # downscaling to wordclim, set parameter to 0 in case they are only used as dummy
        self.var.wc2_tavg = 0
        self.var.wc4_tavg = 0
        self.var.wc2_tmin = 0
        self.var.wc4_tmin = 0
        self.var.wc2_tmax = 0
        self.var.wc4_tmax = 0
        self.var.wc2_prec = 0
        self.var.wc4_prec = 0

        if self.var.InterpolationMethod == 'bilinear':
            #these variables are generated to avoid calculating them at each timestep
            self.var.xcoarse_prec = 0
            self.var.ycoarse_prec = 0
            self.var.xfine_prec = 0
            self.var.yfine_prec = 0
            self.var.meshlist_prec = 0
            self.var.xcoarse_tavg = 0
            self.var.ycoarse_tavg = 0
            self.var.xfine_tavg = 0
            self.var.yfine_tavg = 0
            self.var.meshlist_tavg = 0


        # read dem for making a anomolydem between high resolution dem and low resoultion dem

        """
        # for downscaling1
        dem = loadmap('Elevation', compress = False, cut = False)
        demHigh = dem[cutmapFine[2]*6:cutmapFine[3]*6, cutmapFine[0]*6:cutmapFine[1]*6]
        rows = demHigh.shape[0]
        cols = demHigh.shape[1]
        dem2 = demHigh.reshape(rows/6,6,cols/6,6)
        dem3 = np.average(dem2, axis=(1, 3))
        demLow = np.kron(dem3, np.ones((6, 6)))

        demAnomaly = demHigh - demLow
        self.var.demHigh = compressArray(demHigh[cutmapVfine[2]:cutmapVfine[3], cutmapVfine[0]:cutmapVfine[1]],pcr = False)
        self.var.demAnomaly = compressArray(demAnomaly[cutmapVfine[2]:cutmapVfine[3], cutmapVfine[0]:cutmapVfine[1]],pcr = False)
        """

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    #def downscaling1(self,input, downscale = 0):
        """
        Downscaling based on elevation correction for temperature and pressure

        :param input:
        :param downscale: 0 for no change, 1: for temperature change 6 deg per 1km , 2 for psurf
        :return: input - downscaled input data

        """
        """
        # if meteo maps have the same extend as the other spatial static maps -> meteomapsscale = True
        if not self.var.meteomapsscale:
            down1 = np.kron(input, np.ones((6, 6)))
            down2 = down1[cutmapVfine[2]:cutmapVfine[3], cutmapVfine[0]:cutmapVfine[1]].astype(np.float64)
            down3 = compressArray(down2)
            if downscale == 0:
                input = down3

            if downscale == 1:
                # temperature scaling 6 deg per 1000m difference in altitude
                # see overview in Minder et al 2010 - http://onlinelibrary.wiley.com/doi/10.1029/2009JD013493/full
                tempdiff = -0.006 * self.var.demAnomaly
                input = down3 + tempdiff
            if downscale == 2:
                # psurf correction
                # https://www.sandhurstweather.org.uk/barometric.pdf
                # factor = exp(-elevation / (Temp x 29.263)  Temp in deg K
                demLow = self.var.demHigh - self.var.demAnomaly
                tavgK = self.var.Tavg + 273.15
                factor1 = np.exp(-1 * demLow / (tavgK * 29.263))
                factor2 = np.exp(-1 * self.var.demHigh / (tavgK * 29.263))
                sealevelpressure = down3 / factor1
                input = sealevelpressure * factor2
        return input
        """

    # def downscaling2_peter(self,input, downscaleName = "", wc2 = 0 , wc4 = 0, x=None, y=None, xfine=None, yfine=None, meshlist=None, downscale = 0):
    #     """
    #     Downscaling with only internal (inside the coarse gridcell) interpolation
    #
    #     :param input: low input map
    #     :param downscaleName: High resolution monthly map from WorldClim
    #     :param wc2: High resolution WorldClim map
    #     :param wc4: upscaled to low resolution
    #     :param downscale: 0 for no change, 1: for temperature , 2 for pprecipitation, 3 for psurf
    #     :return: input - downscaled input data
    #     :return: wc2
    #     :return: wc4
    #     """
    #     reso = maskmapAttr['reso_mask_meteo']
    #     resoint = int(reso)
    #     if self.var.meteomapsscale:
    #         if downscale == 0:
    #             return input
    #         else:
    #             return input, wc2, wc4
    #
    #     down3 = np.kron(input, np.ones((resoint, resoint)))
    #     # this is creating an array resoint times bigger than input, by copying each item resoint times in x and y direction
    #
    #     if downscale == 0:
    #         down2 = down3[cutmapVfine[2]:cutmapVfine[3], cutmapVfine[0]:cutmapVfine[1]].astype(np.float64)
    #         input = compressArray(down2)
    #         return input
    #     else:
    #         if dateVar['newStart'] or dateVar['newMonth']:  # loading every month a new map
    #             # wc1 = readnetcdf2(downscaleName, dateVar['currDate'], useDaily='month', compress = False, cut = False)
    #             # wc2 = wc1[cutmapGlobal[2]*resoint:cutmapGlobal[3]*resoint, cutmapGlobal[0]*resoint:cutmapGlobal[1]*resoint]
    #             #print('\n'.join([' '.join(['{:4}'.format(item) for item in row]) for row in wc2]))
    #
    #             if downscale == 2:  # precipitation
    #                 #wc3 looks a like wc3
    #                 wc3 = wc2.reshape(wc2.shape[0] // resoint, resoint, wc2.shape[1] // resoint, resoint)
    #                 #wc3mean looks like w4
    #                 wc3mean = np.nanmean(wc3, axis=(1, 3))
    #                 # Average of wordclim on the bigger input raster scale
    #                 wc3kron = np.kron(wc3mean, np.ones((resoint, resoint)))
    #                 # the average values are spread out to the fine scale
    #                 #looks like quot_wc, but wc2 = input, wc3kron = wc4
    #                 wc4 = divideValues(wc2, wc3kron)
    #                 # wc4 holds the correction multiplicator on fine scale
    #
    #     if downscale == 1: # Temperature
    #         #diff wc is different because originally it is wc4 - input
    #         #diff_wc is difference on small scale
    #         diff_wc = wc2 - down3
    #         # on fine scale: wordclim fine scale - spreaded input data (same value for each big cell)
    #         wc3 = diff_wc.reshape(wc2.shape[0] // resoint, resoint, wc2.shape[1] // resoint, resoint)
    #         wc4 = np.nanmean(wc3, axis=(1, 3))
    #         wc4kron = np.kron(wc4, np.ones((resoint, resoint)))
    #         # wordclim is averaged on big cell scale and the average is spread out to fine raster
    #         down1 = diff_wc - wc4kron + down3
    #         # result is the fine scale input data + the difference of wordclim - input data - the average difference of wordclim - input
    #         down1 = np.where(np.isnan(down1),down3,down1)
    #     if downscale == 2:  # precipitation
    #         # in the other interpolations this is wc2 * quotSmooth, wc2 being the fine worldclimmap cut to map extent, quotSmooth being the interpolated difference between the input and summed worldclim
    #         down1 = down3 * wc4
    #         down1 = np.where(np.isnan(down1),down3,down1)
    #         down1 = np.where(np.isinf(down1), down3, down1)
    #
    #     down2 = down1[cutmapVfine[2]:cutmapVfine[3], cutmapVfine[0]:cutmapVfine[1]].astype(np.float64)
    #     input = compressArray(down2)
    #     return input, wc2, wc4

     # --- end downscaling ----------------------------

    def downscaling2(self,input, downscaleName = "", wc2 = 0 , wc4 = 0, x=None, y=None, xfine=None, yfine=None, meshlist=None, MaskMapBoundaries= None, downscale = 0):
        """
        Downscaling based on Delta method:

        Note:

            | **References**
            | Moreno and Hasenauer  2015:
            | ftp://palantir.boku.ac.at/Public/ClimateData/Moreno_et_al-2015-International_Journal_of_Climatology.pdf
            | Mosier et al. 2018:
            | http://onlinelibrary.wiley.com/doi/10.1002/joc.5213/epdf\

        :param input: low input map
        :param downscaleName: High resolution monthly map from WorldClim
        :param wc2: High resolution WorldClim map
        :param wc4: upscaled to low resolution
        :param MaskMapBoundaries: if 1 maskmap does not touch meteo input dataset boundary, if 0 maskmap touches it
        :param downscale: 0 for no change, 1: for temperature , 2 for pprecipitation, 3 for psurf
        :return: input - downscaled input data
        :return: wc2
        :return: wc4
        """
        reso = maskmapAttr['reso_mask_meteo']
        resoint = int(reso)

        if self.var.InterpolationMethod == 'bilinear' and (downscale == 1 or downscale == 2):
            buffer = 1
            buffer1, buffer2, buffer3, buffer4 = MaskMapBoundaries
            #if 1: does not touch boundaries of meteo input map, if 0 touches boundary of input map
            # to perform bilinear interpolation a buffer around the maskmap is needed, if maskmap touches bounary of input map an artifical buffer has to be created by duplicating the last row/column
            if buffer1 == 0:
                input_first_row = input[0, :]
                input = np.vstack((input_first_row[np.newaxis, :], input))
            if buffer2 == 0:
                input_last_row = input[-1, :]
                input = np.vstack((input, input_last_row[np.newaxis, :]))
            if buffer3 == 0:
                input_first_column = input[:, 0]
                input = np.hstack((input_first_column[:, np.newaxis], input))
            if buffer4 == 0:
                input_last_column = input[:, -1]
                input = np.hstack((input, input_last_column[:, np.newaxis]))

            if dateVar['newStart']:
                x = np.arange(0.5, np.shape(input)[0] + 0.5)
                y = np.arange(0.5, np.shape(input)[1] + 0.5)
                xfine = np.arange(0.5 + 1 / (resoint * 2), np.shape(input)[0] - 0.5, 1 / resoint)
                yfine = np.arange(0.5 + 1 / (resoint * 2), np.shape(input)[1] - 0.5, 1 / resoint)
                xmesh, ymesh = np.meshgrid(xfine, yfine)
                meshlist = list(zip(xmesh.flatten(), ymesh.flatten()))
        else:
            buffer = 0

        if self.var.meteomapsscale:
            if downscale == 0:
                return input
            else:
                return input, wc2, wc4

        if buffer == 0:
          # this is creating an array resoint times bigger than input, by copying each item resoint times in x and y direction
            down3 = np.kron(input, np.ones((resoint, resoint)))
        else:
            down3 = np.kron(input[buffer:-buffer, buffer:-buffer], np.ones((resoint, resoint)))


        if downscale == 0:
            down2 = down3[cutmapVfine[2]:cutmapVfine[3], cutmapVfine[0]:cutmapVfine[1]].astype(np.float64)
            input = compressArray(down2)
            return input
        else:
            if dateVar['newStart'] or dateVar['newMonth']:  # loading every month a new map
                wc1 = readnetcdf2(downscaleName, dateVar['currDate'], useDaily='month', compress = False, cut = False)
                if self.var.InterpolationMethod == 'bilinear':
                    # to perform bilinear interpolation a buffer around the maskmap is needed, if maskmap touches bounary of input map an artifical buffer has to be created by duplicating the last row/column
                    if buffer1 == 0:
                        wc1_first_row = wc1[:resoint, :]
                        wc1 = np.vstack((wc1_first_row, wc1))
                    if buffer2 == 0:
                        wc1_last_row = wc1[-resoint:, :]
                        wc1 = np.vstack((wc1, wc1_last_row))
                    if buffer3 == 0:
                        wc1_first_column = wc1[:, :resoint]
                        wc1 = np.hstack((wc1_first_column, wc1))
                    if buffer4 == 0:
                        wc1_last_column = wc1[:, -resoint:]
                        wc1 = np.hstack((wc1, wc1_last_column))
                    #include buffer
                    if buffer1 == 0:
                        #if maskmap reaches upper boundary you cannot do -buffer because than index would be negative
                        wc2 = wc1[int(np.floor((cutmapGlobal[2]) * reso)):int(np.ceil((cutmapGlobal[3] + buffer* 2) * reso)), :]
                        if buffer3 == 0:
                            wc2 = wc2[:, int(np.floor((cutmapGlobal[0]) * reso)): int(
                                np.ceil((cutmapGlobal[1] + buffer * 2) * reso))]
                    elif buffer3 == 0:
                        # if maskmap reaches left boundary you cannot do -buffer because than index would be negative
                        wc2 = wc1[int(np.floor((cutmapGlobal[2] - buffer) * reso)):int(
                                    np.ceil((cutmapGlobal[3] + buffer) * reso)),int(np.floor((cutmapGlobal[0]) * reso)) : int(np.ceil((cutmapGlobal[1] + buffer * 2) * reso))]
                    else:
                        wc2 = wc1[int(np.floor((cutmapGlobal[2] - buffer) * reso)):int(
                                    np.ceil((cutmapGlobal[3] + buffer) * reso)),
                                      int(np.floor((cutmapGlobal[0] - buffer) * reso)):int(
                                          np.ceil((cutmapGlobal[1] + buffer) * reso))]
                else:
                    wc2 = wc1[(cutmapGlobal[2] - buffer) * resoint: (cutmapGlobal[3] + buffer) * resoint,
                          (cutmapGlobal[0] - buffer) * resoint: (cutmapGlobal[1] + buffer) * resoint]
                rows = wc2.shape[0]
                cols = wc2.shape[1]
                wc3 =  wc2.reshape(rows//resoint,resoint,cols//resoint,resoint)
                wc4 =  np.nanmean(wc3, axis=(1, 3))
                # wc4 is as big as the input array -> average of the fine scale downscale map

                if self.var.InterpolationMethod == 'kron':
                    if downscale == 2:  # precipitation
                        # wc3 looks a like wc3
                        wc3 = wc2.reshape(wc2.shape[0] // resoint, resoint, wc2.shape[1] // resoint, resoint)
                        # wc3mean looks like w4
                        wc3mean = np.nanmean(wc3, axis=(1, 3))
                        # Average of wordclim on the bigger input raster scale
                        wc3kron = np.kron(wc3mean, np.ones((resoint, resoint)))
                        # the average values are spread out to the fine scale
                        # looks like quot_wc, but wc2 = input, wc3kron = wc4
                        wc4 = divideValues(wc2, wc3kron)

        if downscale == 1: # Temperature
            diff_wc = wc4 - input

            if self.var.InterpolationMethod == 'spline':
                diffSmooth = scipy.ndimage.zoom(diff_wc, resoint, order=1)
                down1 = wc2 - diffSmooth

            elif self.var.InterpolationMethod == 'bilinear':
                bilinear_interpolation = RegularGridInterpolator((x, y), diff_wc)
                diffSmooth = bilinear_interpolation(meshlist)
                diffSmooth = diffSmooth.reshape(len(xfine), len(yfine), order='F')
                #no buffer for real downscaled values
                crop = int(resoint / 2)
                diffSmooth = diffSmooth[crop:-crop, crop:-crop]
                down1 = wc2[buffer * resoint:-buffer * resoint, buffer * resoint:-buffer * resoint] - diffSmooth

            elif self.var.InterpolationMethod == 'kron':
                diff_wc = wc2 - down3
                # on fine scale: wordclim fine scale - spreaded input data (same value for each big cell)
                wc3 = diff_wc.reshape(wc2.shape[0] // resoint, resoint, wc2.shape[1] // resoint, resoint)
                wc4 = np.nanmean(wc3, axis=(1, 3))
                wc4kron = np.kron(wc4, np.ones((resoint, resoint)))
                # wordclim is averaged on big cell scale and the average is spread out to fine raster
                down1 = diff_wc - wc4kron + down3
                # result is the fine scale input data + the difference of wordclim - input data - the average difference of wordclim - input
                #down1 = np.where(np.isnan(down1), down3, down1)
            
            down1 = np.where(np.isnan(down1),down3,down1)

        if downscale == 2:  # precipitation
            if self.var.InterpolationMethod == 'spline':
                quot_wc = divideValues(input, wc4)
                quotSmooth = scipy.ndimage.zoom(quot_wc, resoint, order=1)
                down1 = wc2 * quotSmooth
            elif self.var.InterpolationMethod == 'bilinear':
                quot_wc = divideValues(input, wc4)
                bilinear_interpolation = RegularGridInterpolator((x, y), quot_wc)
                quotSmooth = bilinear_interpolation(meshlist)
                quotSmooth = quotSmooth.reshape(len(xfine), len(yfine), order='F')
                crop = int(resoint/2)
                quotSmooth = quotSmooth[crop:-crop, crop:-crop]
                down1 = wc2[buffer * resoint:-buffer * resoint, buffer * resoint:-buffer * resoint] * quotSmooth
            elif self.var.InterpolationMethod == 'kron':
                down1 = down3 * wc4

            down1 = np.where(np.isnan(down1),down3,down1)
            down1 = np.where(np.isinf(down1), down3, down1)

        down2 = down1[cutmapVfine[2]:cutmapVfine[3], cutmapVfine[0]:cutmapVfine[1]].astype(np.float64)
        input = compressArray(down2)
        if self.var.InterpolationMethod == 'bilinear' and (downscale == 1 or downscale == 2):
            return input, wc2, wc4, x, y, xfine, yfine, meshlist
        return input, wc2, wc4

     # --- end downscaling ----------------------------





    def dynamic(self):
        """
        Dynamic part of the readmeteo module

        Read meteo input maps from netcdf files

        Note:
            If option *calc_evaporation* is False only precipitation, avg. temp., and 2 evaporation vlaues are read
            Otherwise all the variable needed for Penman-Monteith

        Note:
            If option *TemperatureInKelvin* = True temperature is assumed to be Kelvin instead of Celsius!

        """
        if Flags['warm']:
            # if warmstart use stored meteo variables
            no = dateVar['curr']-1
            self.var.Precipitation = self.var.meteo[0,no]
            self.var.Tavg = self.var.meteo[1,no]
            self.var.ETRef = self.var.meteo[2,no]
            self.var.EWRef = self.var.meteo[3,no]
            j = 3
            if self.var.snowmelt_radiation:
                self.var.Rsds = self.var.meteo[4,no]
                self.var.Rsdl = self.var.meteo[5,no]
                j = 5
            if self.var.includeGlaciers:
                self.var.GlacierMelt = self.var.meteo[j+1, no]
                if not self.var.includeOnlyGlaciersMelt:
                    self.var.GlacierRain = self.var.meteo[j+2, no]
            return

        ZeroKelvin = 0.0
        if checkOption('TemperatureInKelvin'):
            # if temperature is in Kelvin -> conversion to deg C
            # TODO in initial there could be a check if temperature > 200 -> automatic change to Kelvin
            ZeroKelvin = 273.15

        self.var.Precipitation, MaskMapBoundary = readmeteodata(self.var.preMaps, dateVar['currDate'], addZeros=True, mapsscale = self.var.meteomapsscale, buffering= self.var.buffer)
        self.var.Precipitation = self.var.Precipitation * self.var.DtDay * self.var.con_precipitation

        self.var.Precipitation = np.maximum(0., self.var.Precipitation)
        
        if self.var.includeGlaciers:
            self.var.GlacierMelt, MaskMapBoundary = readmeteodata(self.var.glaciermeltMaps, dateVar['currDate'], addZeros=True, mapsscale = True, extendback = True)
            # Glaciermelt and Glacierrain is preprocessed after OGGM to have a factor of 1.0 
            # -> here glacier melt is again multiplied by the CwatM snow factor to have the same values            self.var.GlacierMelt = self.var.GlacierMelt * self.var.SnowFactor
            # extendback -> if simulation starts earlier than first glacier map -> day of the year of first year is used
            if not self.var.includeOnlyGlaciersMelt:
                self.var.GlacierRain, MaskMapBoundary = readmeteodata(self.var.glacierrainMaps, dateVar['currDate'], addZeros=True, mapsscale = True, extendback = True)

        if self.var.meteodown:
            if self.var.InterpolationMethod == 'bilinear':
                self.var.Precipitation, self.var.wc2_prec, self.var.wc4_prec, self.var.xcoarse_prec, self.var.ycoarse_prec, self.var.xfine_prec, self.var.yfine_prec, self.var.meshlist_prec = self.downscaling2(
                    self.var.Precipitation, "downscale_wordclim_prec", self.var.wc2_prec, self.var.wc4_prec,
                    self.var.xcoarse_prec, self.var.ycoarse_prec, self.var.xfine_prec, self.var.yfine_prec,
                    self.var.meshlist_prec, MaskMapBoundary, downscale=2)
            else:
                self.var.Precipitation, self.var.wc2_prec, self.var.wc4_prec = self.downscaling2(self.var.Precipitation, "downscale_wordclim_prec", self.var.wc2_prec, self.var.wc4_prec, downscale=2)
        else:
            self.var.Precipitation = self.downscaling2(self.var.Precipitation, "downscale_wordclim_prec", self.var.wc2_prec, self.var.wc4_prec, downscale=0)

        #self.var.Precipitation = self.var.Precipitation * 1000
        

        self.var.prec = self.var.Precipitation / self.var.con_precipitation
        # precipitation (conversion to [m] per time step)  `
        if Flags['check']:
            checkmap(self.var.preMaps, "", self.var.Precipitation, True, True, self.var.Precipitation)

        #self.var.Tavg = readnetcdf2('TavgMaps', dateVar['currDate'], addZeros = True, zeros = ZeroKelvin, meteo = True)

        tzero = 0
        if checkOption('TemperatureInKelvin'):
            tzero = ZeroKelvin
        self.var.Tavg, MaskMapBoundary = readmeteodata(self.var.tempMaps,dateVar['currDate'], addZeros=True, zeros = tzero, mapsscale = self.var.meteomapsscale, buffering= self.var.buffer)

        if self.var.meteodown:
            if self.var.InterpolationMethod == 'bilinear':
                self.var.Tavg, self.var.wc2_tavg, self.var.wc4_tavg, self.var.xcoarse_tavg, self.var.ycoarse_tavg, self.var.xfine_tavg, self.var.yfine_tavg, self.var.meshlist_tavg = self.downscaling2(
                    self.var.Tavg, "downscale_wordclim_tavg", self.var.wc2_tavg, self.var.wc4_tavg, self.var.xcoarse_tavg,
                    self.var.ycoarse_tavg, self.var.xfine_tavg, self.var.yfine_tavg, self.var.meshlist_tavg, MaskMapBoundary, downscale=1)
            else:
                self.var.Tavg, self.var.wc2_tavg, self.var.wc4_tavg  = self.downscaling2(self.var.Tavg, "downscale_wordclim_tavg", self.var.wc2_tavg, self.var.wc4_tavg, downscale=1)
        else:
            self.var.Tavg  = self.downscaling2(self.var.Tavg, "downscale_wordclim_tavg", self.var.wc2_tavg, self.var.wc4_tavg, downscale=0)
        self.var.temp = self.var.Tavg.copy()

        # average DAILY temperature (even if you are running the model
        # on say an hourly time step) [degrees C]
        if checkOption('TemperatureInKelvin'):
            self.var.Tavg -= ZeroKelvin

        if Flags['check']:
            checkmap(self.var.tempMaps, "", self.var.Tavg, True, True, self.var.Tavg)

        if checkOption('calc_evaporation') or self.var.snowmelt_radiation:
            # for new snow calculation radiation is needed
            if self.var.only_radiation:
                # read daily calculated radiation [in KJ/m2/day]
                # named here Rsds instead of rds, because use in evaproationPot in the same way as rsds
                self.var.Rsds, MaskMapBoundary = readmeteodata('RGDMaps', dateVar['currDate'], addZeros=True, mapsscale=self.var.meteomapsscale)
                #self.var.Rsds = self.downscaling2(self.var.Rsds) * 0.001  # convert from KJ to MJ/m2/day
                self.var.Rsds = self.downscaling2(self.var.Rsds) * 0.000001  # convert from KJ to MJ/m2/day
                # but for EMO it is 1e6 instead 1000 it seems it is J instead of KJ

                # read daily vapor pressure [in hPa]
                self.var.EAct, MaskMapBoundary = readmeteodata('EActMaps', dateVar['currDate'], addZeros=True, mapsscale=self.var.meteomapsscale)
                self.var.EAct = self.downscaling2(self.var.EAct) * 0.1  # convert from hP to kP
            else:
                self.var.Rsds, MaskMapBoundary = readmeteodata('RSDSMaps', dateVar['currDate'], addZeros=True, mapsscale = self.var.meteomapsscale)
                self.var.Rsds = self.downscaling2(self.var.Rsds)
                    # radiation surface downwelling shortwave maps [W/m2]
                #self.var.Rsdl = readnetcdf2('RSDLMaps', dateVar['currDate'], addZeros = True, meteo = True)
                self.var.Rsdl, MaskMapBoundary = readmeteodata('RSDLMaps', dateVar['currDate'], addZeros=True, mapsscale = self.var.meteomapsscale)
                self.var.Rsdl = self.downscaling2(self.var.Rsdl)
                    # radiation surface downwelling longwave maps [W/m2]

                # Conversion factor from [W] to [MJ]
                self.var.WtoMJ = 86400 * 1E-6

                # conversion from W/m2 to MJ/m2/day
                self.var.Rsds = self.var.Rsds * self.var.WtoMJ
                self.var.Rsdl = self.var.Rsdl * self.var.WtoMJ

        # -----------------------------------------------------------------------
        # if evaporation has to be calculated load all the meteo map sets
        # Temparture min, max;  Windspeed,  specific humidity or relative humidity, psurf
        # -----------------------------------------------------------------------

        if checkOption('calc_evaporation'):

            #self.var.TMin = readnetcdf2('TminMaps', dateVar['currDate'], addZeros = True, zeros = ZeroKelvin, meteo = True)
            self.var.TMin, MaskMapBoundary = readmeteodata('TminMaps',dateVar['currDate'], addZeros=True, zeros=ZeroKelvin, mapsscale = self.var.meteomapsscale, buffering= self.var.buffer)
            if self.var.meteodown:
                if self.var.InterpolationMethod == 'bilinear':
                    self.var.TMin, self.var.wc2_tmin, self.var.wc4_tmin, _, _, _, _, _ = self.downscaling2(self.var.TMin,
                                                                                                           "downscale_wordclim_tmin",
                                                                                                           self.var.wc2_tmin,
                                                                                                           self.var.wc4_tmin,
                                                                                                           self.var.xcoarse_tavg,
                                                                                                           self.var.ycoarse_tavg,
                                                                                                           self.var.xfine_tavg,
                                                                                                           self.var.yfine_tavg,
                                                                                                           self.var.meshlist_tavg, MaskMapBoundary,
                                                                                                           downscale=1)
                else:
                    self.var.TMin, self.var.wc2_tmin, self.var.wc4_tmin = self.downscaling2(self.var.TMin, "downscale_wordclim_tmin", self.var.wc2_tmin, self.var.wc4_tmin, downscale=1)
            else:
                self.var.TMin = self.downscaling2(self.var.TMin, "downscale_wordclim_tmin", self.var.wc2_tmin, self.var.wc4_tmin, downscale=0)

            if Flags['check']:
                checkmap('TminMaps', "", self.var.TMin, True, True, self.var.TMin)

            #self.var.TMax = readnetcdf2('TmaxMaps', dateVar['currDate'], addZeros = True, zeros = ZeroKelvin, meteo = True)
            self.var.TMax, MaskMapBoundary = readmeteodata('TmaxMaps', dateVar['currDate'], addZeros=True, zeros=ZeroKelvin, mapsscale = self.var.meteomapsscale, buffering= self.var.buffer)
            if self.var.meteodown:
                if self.var.InterpolationMethod == 'bilinear':
                    self.var.TMax, self.var.wc2_tmax, self.var.wc4_tmax, _, _, _, _, _ = self.downscaling2(self.var.TMax,
                                                                                                           "downscale_wordclim_tmin",
                                                                                                           self.var.wc2_tmax,
                                                                                                           self.var.wc4_tmax,
                                                                                                           self.var.xcoarse_tavg,
                                                                                                           self.var.ycoarse_tavg,
                                                                                                           self.var.xfine_tavg,
                                                                                                           self.var.yfine_tavg,
                                                                                                           self.var.meshlist_tavg, MaskMapBoundary,
                                                                                                           downscale=1)
                else:
                    self.var.TMax, self.var.wc2_tmax, self.var.wc4_tmax = self.downscaling2(self.var.TMax, "downscale_wordclim_tmin", self.var.wc2_tmax, self.var.wc4_tmax, downscale=1)
            else:
                self.var.TMax = self.downscaling2(self.var.TMax, "downscale_wordclim_tmin", self.var.wc2_tmax, self.var.wc4_tmax, downscale=0)

            if Flags['check']: checkmap('TmaxMaps', "", self.var.TMax, True, True, self.var.TMax)

            if checkOption('TemperatureInKelvin'):
                self.var.TMin -= ZeroKelvin
                self.var.TMax -= ZeroKelvin

            #self.var.Wind = readnetcdf2('WindMaps', dateVar['currDate'], addZeros = True, meteo = True)
            self.var.Wind, MaskMapBoundary = readmeteodata('WindMaps', dateVar['currDate'], addZeros=True, mapsscale = self.var.meteomapsscale)
            self.var.Wind = self.downscaling2(self.var.Wind)
                # wind speed maps at 10m [m/s]

            # Adjust wind speed for measurement height: wind speed measured at
            # 10 m, but needed at 2 m height
            # Shuttleworth, W.J. (1993) in Maidment, D.R. (1993), p. 4.36
            self.var.Wind = self.var.Wind * 0.749

            if not self.var.only_radiation:

                #self.var.Psurf = readnetcdf2('PSurfMaps', dateVar['currDate'], addZeros = True, meteo = True)
                self.var.Psurf, MaskMapBoundary = readmeteodata('PSurfMaps', dateVar['currDate'], addZeros=True, mapsscale = self.var.meteomapsscale)
                self.var.Psurf = self.downscaling2(self.var.Psurf)
                    # Instantaneous surface pressure[Pa]

                if returnBool('useHuss'):
                    #self.var.Qair = readnetcdf2('QAirMaps', dateVar['currDate'], addZeros = True, meteo = True)
                    self.var.Qair, MaskMapBoundary = readmeteodata('QAirMaps', dateVar['currDate'], addZeros=True, mapsscale =self.var.meteomapsscale)
                    # 2 m istantaneous specific humidity[kg / kg]
                else:
                    #self.var.Qair = readnetcdf2('RhsMaps', dateVar['currDate'], addZeros = True, meteo = True)
                    self.var.Qair, MaskMapBoundary = readmeteodata('RhsMaps', dateVar['currDate'], addZeros=True, mapsscale =self.var.meteomapsscale)
                self.var.Qair = self.downscaling2(self.var.Qair)

                #--------------------------------------------------------
                # conversions

                # [Pa] to [KPa]
                self.var.Psurf = self.var.Psurf * 0.001


        # if pot evaporation is already precalulated
        else:

            # in case ET_ref is the same resolution as the other meteo input map, there is an optional flag in settings which checks this
            ETsamePr = False
            if "ETsamePr" in binding:
                if returnBool('ETsamePr'):
                    ETsamePr = True

            if ETsamePr:
                self.var.ETRef, MaskMapBoundary = readmeteodata(self.var.evaTMaps, dateVar['currDate'], addZeros=True,  mapsscale=self.var.meteomapsscale)
                self.var.ETRef = self.var.ETRef *self.var.DtDay * self.var.con_e
                self.var.ETRef = self.downscaling2(self.var.ETRef, "downscale_wordclim_prec", self.var.wc2_prec, self.var.wc4_prec, downscale=0)

                self.var.EWRef, MaskMapBoundary = readmeteodata(self.var.eva0Maps, dateVar['currDate'], addZeros=True,  mapsscale=self.var.meteomapsscale)
                self.var.EWRef = self.var.EWRef * self.var.DtDay * self.var.con_e
                self.var.EWRef = self.downscaling2(self.var.EWRef, "downscale_wordclim_prec", self.var.wc2_prec, self.var.wc4_prec, downscale=0)
            else:
                self.var.ETRef, MaskMapBoundary = readmeteodata(self.var.evaTMaps, dateVar['currDate'], addZeros=True, mapsscale = True)
                self.var.ETRef = self.var.ETRef *self.var.DtDay * self.var.con_e
                self.var.EWRef, MaskMapBoundary = readmeteodata(self.var.eva0Maps, dateVar['currDate'], addZeros=True, mapsscale = True)
                self.var.EWRef = self.var.EWRef * self.var.DtDay * self.var.con_e
                # potential evaporation rate from water surface (conversion to [m] per time step)
                # potential evaporation rate from a bare soil surface (conversion # to [m] per time step)

        if Flags['calib']:
            # if first clibration run, store all meteo data in a variable
            if dateVar['curr'] == 1:
                number = 4
                if self.var.snowmelt_radiation:
                    number = number + 2
                if self.var.includeGlaciers:
                    number = number + 1
                    if not self.var.includeOnlyGlaciersMelt:
                        number = number + 1

                self.var.meteo = np.zeros([number, 1 + dateVar["intEnd"] - dateVar["intStart"], len(self.var.Precipitation)])

            no = dateVar['curr'] -1
            self.var.meteo[0,no] = self.var.Precipitation
            self.var.meteo[1,no] = self.var.Tavg
            self.var.meteo[2,no] = self.var.ETRef
            self.var.meteo[3,no] = self.var.EWRef
            j =3
            if self.var.snowmelt_radiation:
                self.var.meteo[4,no] = self.var.Rsds
                self.var.meteo[5,no] = self.var.Rsdl
                j = 5
            if self.var.includeGlaciers:
                self.var.meteo[j+1, no] = self.var.GlacierMelt
                if not self.var.includeOnlyGlaciersMelt:
                    self.var.meteo[j+2, no] = self.var.GlacierRain
            ii =1

