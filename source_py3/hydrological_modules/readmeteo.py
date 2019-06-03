# -------------------------------------------------------------------------
# Name:        READ METEO input maps
# Purpose:
#
# Author:      PB
#
# Created:     13/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *
import scipy.ndimage

class readmeteo(object):
    """
    READ METEOROLOGICAL DATA

    reads all meteorological data from netcdf4 files
    """

    def __init__(self, readmeteo_variable):
        self.var = readmeteo_variable


    def initial(self):
        """
        Initial part of meteo

        read multiple file of input
        """

        # test if ModFlow is in the settingsfile
        # if not, use default without Modflow
        self.var.modflow = False
        self.var.modflowsteady = True
        if "modflow_coupling" in option:
            self.var.modflow = checkOption('modflow_coupling')

        if self.var.modflow:
            ## Model properties ##
            self.var.modflowsteady = returnBool('modflow_steadystate')

        if (self.var.modflow and self.var.modflowsteady):
            self.var.preMaps  = 'ModflowPrecipitationMaps'
            self.var.tempMaps = 'ModflowTavgMaps'
            self.var.evaTMaps = 'ModflowETMaps'
            self.var.eva0Maps = 'ModflowE0Maps'
        else:
            self.var.preMaps = 'PrecipitationMaps'
            self.var.tempMaps = 'TavgMaps'
            self.var.evaTMaps = 'ETMaps'
            self.var.eva0Maps = 'E0Maps'


        if checkOption('calc_evaporation'):
            meteomaps = [self.var.preMaps, self.var.tempMaps,'TminMaps','TmaxMaps','PSurfMaps','WindMaps','RSDSMaps','RSDLMaps']
            if returnBool('useHuss'):
                meteomaps.append('QAirMaps')
            else:
                meteomaps.append('RhsMaps')

        else:
            meteomaps = [self.var.preMaps, self.var.tempMaps,self.var.evaTMaps,self.var.eva0Maps]

        #meteomaps = ["PrecipitationMaps","TavgMaps"]
        multinetdf(meteomaps)

        # Downscaling
        self.var.meteodown = True
        if "usemeteodownscaling" in binding:
            self.var.meteodown = returnBool('usemeteodownscaling')

        self.var.wc2_tavg = 0
        self.var.wc4_tavg = 0
        self.var.wc2_tmin = 0
        self.var.wc4_tmin = 0
        self.var.wc2_tmax = 0
        self.var.wc4_tmax = 0
        self.var.wc2_prec = 0
        self.var.wc4_prec = 0


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

    def downscaling1(self,input, downscale = 0):
        """
        Downscaling based on elevation correction for temperature and pressure

        :param input:
        :param downscale: 0 for no change, 1: for temperature change 6 deg per 1km , 2 for psurf
        :return: input - downscaled input data

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


    def downscaling2(self,input, downscaleName = "", wc2 = 0 , wc4 = 0, downscale = 0):
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
        :param downscale: 0 for no change, 1: for temperature , 2 for pprecipitation, 3 for psurf
        :return: input - downscaled input data
        :return: wc2
        :return: wc4
        """
        reso = maskmapAttr['reso_mask_meteo']
        resoint = int(reso)

        if self.var.meteomapsscale:
            if downscale == 0:
                return input
            else:
                return input, wc2, wc4


        down3 = np.kron(input, np.ones((resoint, resoint)))
        if downscale == 0:
            down2 = down3[cutmapVfine[2]:cutmapVfine[3], cutmapVfine[0]:cutmapVfine[1]].astype(np.float64)
            input = compressArray(down2)
            return input
        else:
            if dateVar['newStart'] or dateVar['newMonth']:  # loading every month a new map
                wc1 = readnetcdf2(downscaleName, dateVar['currDate'], useDaily='month', compress = False, cut = False)
                wc2 = wc1[cutmapGlobal[2]*resoint:cutmapGlobal[3]*resoint, cutmapGlobal[0]*resoint:cutmapGlobal[1]*resoint]
                #wc2 = wc1[cutmapGlobal[2] * resoint:cutmapGlobal[3] * resoint, cutmapGlobal[0] * resoint:cutmapGlobal[1] * resoint]
                rows = wc2.shape[0]
                cols = wc2.shape[1]
                wc3 =  wc2.reshape(rows//resoint,resoint,cols//resoint,resoint)
                wc4 =  np.nanmean(wc3, axis=(1, 3))

        if downscale == 1: # Temperature
            diff_wc = wc4 - input
            #diff_wc[np.isnan( diff_wc)] = 0.0
            # could also use np.kron !
            diffSmooth = scipy.ndimage.zoom(diff_wc, resoint, order=1)
            down1 = wc2 - diffSmooth
            down1 = np.where(np.isnan(down1),down3,down1)
        if downscale == 2:  # precipitation
            quot_wc = divideValues(input, wc4)
            quotSmooth = scipy.ndimage.zoom(quot_wc, resoint, order=1)
            down1 = wc2 * quotSmooth
            down1 = np.where(np.isnan(down1),down3,down1)
            down1 = np.where(np.isinf(down1), down3, down1)


        down2 = down1[cutmapVfine[2]:cutmapVfine[3], cutmapVfine[0]:cutmapVfine[1]].astype(np.float64)
        input = compressArray(down2)
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
        modflow = False
        if (self.var.modflow and self.var.modflowsteady):
            modflow = True

        ZeroKelvin = 0.0
        if checkOption('TemperatureInKelvin'):
            # if temperature is in Kelvin -> conversion to deg C
            # TODO in initial there could be a check if temperature > 200 -> automatic change to Kelvin
            ZeroKelvin = 273.15


        self.var.Precipitation = readmeteodata(self.var.preMaps, dateVar['currDate'], addZeros=True, mapsscale = self.var.meteomapsscale, modflowSteady = modflow) * self.var.DtDay * self.var.con_precipitation
        self.var.Precipitation = np.maximum(0., self.var.Precipitation)

        if self.var.meteodown:
            self.var.Precipitation, self.var.wc2_prec, self.var.wc4_prec = self.downscaling2(self.var.Precipitation, "downscale_wordclim_prec", self.var.wc2_prec, self.var.wc4_prec, downscale=2)
        else:
            self.var.Precipitation = self.downscaling2(self.var.Precipitation, "downscale_wordclim_prec", self.var.wc2_prec, self.var.wc4_prec, downscale=0)

        #self.var.Precipitation = self.var.Precipitation * 1000

        self.var.prec = self.var.Precipitation / self.var.con_precipitation
        # precipitation (conversion to [mm] per time step)  `
        if Flags['check']:
            checkmap(self.var.preMaps, "", self.var.Precipitation, True, True, self.var.Precipitation)


        #self.var.Tavg = readnetcdf2('TavgMaps', dateVar['currDate'], addZeros = True, zeros = ZeroKelvin, meteo = True)

        tzero = 0
        if checkOption('TemperatureInKelvin'):
            tzero = ZeroKelvin
        self.var.Tavg = readmeteodata(self.var.tempMaps,dateVar['currDate'], addZeros=True, zeros = tzero, mapsscale = self.var.meteomapsscale, modflowSteady = modflow)

        if self.var.meteodown:
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


        #self.var.Tavg = downscaling(self.var.Tavg, downscale = 0)

        # -----------------------------------------------------------------------
        # if evaporation has to be calculated load all the meteo map sets
        # Temparture min, max;  Windspeed,  specific humidity or relative humidity
        # psurf, radiation
        # -----------------------------------------------------------------------



        if checkOption('calc_evaporation'):

            #self.var.TMin = readnetcdf2('TminMaps', dateVar['currDate'], addZeros = True, zeros = ZeroKelvin, meteo = True)
            self.var.TMin = readmeteodata('TminMaps',dateVar['currDate'], addZeros=True, zeros=ZeroKelvin, mapsscale = self.var.meteomapsscale)
            if self.var.meteodown:
                self.var.TMin, self.var.wc2_tmin, self.var.wc4_tmin = self.downscaling2(self.var.TMin, "downscale_wordclim_tmin", self.var.wc2_tmin, self.var.wc4_tmin, downscale=1)
            else:
                self.var.TMin = self.downscaling2(self.var.TMin, "downscale_wordclim_tmin", self.var.wc2_tmin, self.var.wc4_tmin, downscale=0)

            if Flags['check']: checkmap('TminMaps', "", self.var.Tmin, True, True, self.var.Tmin)

            #self.var.TMax = readnetcdf2('TmaxMaps', dateVar['currDate'], addZeros = True, zeros = ZeroKelvin, meteo = True)
            self.var.TMax = readmeteodata('TmaxMaps', dateVar['currDate'], addZeros=True, zeros=ZeroKelvin, mapsscale = self.var.meteomapsscale)
            if self.var.meteodown:
                self.var.TMax, self.var.wc2_tmax, self.var.wc4_tmax = self.downscaling2(self.var.TMax, "downscale_wordclim_tmin", self.var.wc2_tmax, self.var.wc4_tmax, downscale=1)
            else:
                self.var.TMax = self.downscaling2(self.var.TMax, "downscale_wordclim_tmin", self.var.wc2_tmax, self.var.wc4_tmax, downscale=0)

            if Flags['check']: checkmap('TmaxMaps', "", self.var.Tmax, True, True, self.var.Tmax)


            #self.var.Psurf = readnetcdf2('PSurfMaps', dateVar['currDate'], addZeros = True, meteo = True)
            self.var.Psurf = readmeteodata('PSurfMaps', dateVar['currDate'], addZeros=True, mapsscale = self.var.meteomapsscale)
            self.var.Psurf = self.downscaling2(self.var.Psurf)
                # Instantaneous surface pressure[Pa]
            #self.var.Wind = readnetcdf2('WindMaps', dateVar['currDate'], addZeros = True, meteo = True)
            self.var.Wind = readmeteodata('WindMaps', dateVar['currDate'], addZeros=True, mapsscale = self.var.meteomapsscale)
            self.var.Wind = self.downscaling2(self.var.Wind)
                # wind speed maps at 10m [m/s]
            #self.var.Rsds = readnetcdf2('RSDSMaps', dateVar['currDate'], addZeros = True, meteo = True)
            self.var.Rsds = readmeteodata('RSDSMaps', dateVar['currDate'], addZeros=True, mapsscale = self.var.meteomapsscale)
            self.var.Rsds = self.downscaling2(self.var.Rsds)
                # radiation surface downwelling shortwave maps [W/m2]
            #self.var.Rsdl = readnetcdf2('RSDLMaps', dateVar['currDate'], addZeros = True, meteo = True)
            self.var.Rsdl = readmeteodata('RSDLMaps', dateVar['currDate'], addZeros=True, mapsscale = self.var.meteomapsscale)
            self.var.Rsdl = self.downscaling2(self.var.Rsdl)
                # radiation surface downwelling longwave maps [W/m2]
            if returnBool('useHuss'):
                #self.var.Qair = readnetcdf2('QAirMaps', dateVar['currDate'], addZeros = True, meteo = True)
                self.var.Qair = readmeteodata('QAirMaps', dateVar['currDate'], addZeros=True, mapsscale =self.var.meteomapsscale)
                # 2 m istantaneous specific humidity[kg / kg]
            else:
                #self.var.Qair = readnetcdf2('RhsMaps', dateVar['currDate'], addZeros = True, meteo = True)
                self.var.Qair = readmeteodata('RhsMaps', dateVar['currDate'], addZeros=True, mapsscale =self.var.meteomapsscale)
            self.var.Qair = self.downscaling2(self.var.Qair)
                #


            #--------------------------------------------------------
            # conversions

            if checkOption('TemperatureInKelvin'):
                self.var.TMin -= ZeroKelvin
                self.var.TMax -= ZeroKelvin

            # [Pa] to [KPa]
            self.var.Psurf = self.var.Psurf * 0.001

            # Adjust wind speed for measurement height: wind speed measured at
            # 10 m, but needed at 2 m height
            # Shuttleworth, W.J. (1993) in Maidment, D.R. (1993), p. 4.36
            self.var.Wind = self.var.Wind * 0.749

            # Conversion factor from [W] to [MJ]
            self.var.WtoMJ = 86400 * 1E-6

            # conversion from W/m2 to MJ/m2/day
            self.var.Rsds = self.var.Rsds * self.var.WtoMJ
            self.var.Rsdl = self.var.Rsdl * self.var.WtoMJ


        # if pot evaporation is already precalulated
        else:

            """
            # in case ET_ref is cut to local area there is an optional flag in settings which checks this
            # if it is not sert the standart is used
            try:
                if returnBool('cutET'):
                    cutET = True
                else: cutET = False
            except:
                cutET = False
            """

            #self.var.ETRef = readmeteodata('ETMaps', dateVar['currDate'], addZeros=True) * self.var.DtDay * self.var.con_e
            self.var.ETRef = readmeteodata(self.var.evaTMaps, dateVar['currDate'], addZeros=True, mapsscale = True, modflowSteady = modflow) * self.var.DtDay * self.var.con_e
            #self.var.ETRef = downscaling2(self.var.ETRef)
            # daily reference evaporation (conversion to [m] per time step)
            #self.var.EWRef = readmeteodata('E0Maps', dateVar['currDate'], addZeros=True) * self.var.DtDay * self.var.con_e
            self.var.EWRef = readmeteodata(self.var.eva0Maps, dateVar['currDate'], addZeros=True, mapsscale = True, modflowSteady = modflow) * self.var.DtDay * self.var.con_e
            #self.var.EWRef = downscaling2(self.var.EWRef)
            # potential evaporation rate from water surface (conversion to [m] per time step)
            # self.var.ESRef = (self.var.EWRef + self.var.ETRef)/2
            # potential evaporation rate from a bare soil surface (conversion # to [m] per time step)




