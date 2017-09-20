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
        :return:
        """


        if checkOption('calc_evaporation'):
            meteomaps = ["PrecipitationMaps", "TavgMaps",'TminMaps','TmaxMaps','PSurfMaps','WindMaps','RSDSMaps','RSDLMaps']
            if returnBool('useHuss'):
                meteomaps.append('QAirMaps')
            else:
                meteomaps.append('RhsMaps')

        else:
            meteomaps = ["PrecipitationMaps", "TavgMaps",'ETMaps','E0Maps']

        #meteomaps = ["PrecipitationMaps","TavgMaps"]
        multinetdf(meteomaps)
        ii = 1

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

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

        ZeroKelvin = 0.0
        if checkOption('TemperatureInKelvin'):
            # if temperature is in Kelvin -> conversion to deg C
            # TODO in initial there could be a check if temperature > 200 -> automatic change to Kelvin
            ZeroKelvin = 273.15



        #self.var.Precipitation = readnetcdf2('PrecipitationMaps',dateVar['currDate'],addZeros = True, meteo = True) * self.var.DtDay * self.var.con_precipitation
        self.var.Precipitation = readmeteodata('PrecipitationMaps', dateVar['currDate'], addZeros=True, zeros=ZeroKelvin) * self.var.DtDay * self.var.con_precipitation
        self.var.Precipitation = np.maximum(0., self.var.Precipitation)

        #TODO PB
        ##self.var.Precipitation = self.var.Precipitation * 0 + 0.2


        # precipitation (conversion to [mm] per time step)
        #self.var.Tavg = readnetcdf2('TavgMaps', dateVar['currDate'], addZeros = True, zeros = ZeroKelvin, meteo = True)
        self.var.Tavg = readmeteodata('TavgMaps',dateVar['currDate'], addZeros=True, zeros=ZeroKelvin)
        # average DAILY temperature (even if you are running the model
        # on say an hourly time step) [degrees C]


        if checkOption('TemperatureInKelvin'):
            self.var.Tavg -= ZeroKelvin

        # -----------------------------------------------------------------------
        # if evaporation has to be calculated load all the meteo map sets
        # Temparture min, max;  Windspeed,  specific humidity or relative humidity
        # psurf, radiation
        # -----------------------------------------------------------------------
        if checkOption('calc_evaporation'):

            #self.var.TMin = readnetcdf2('TminMaps', dateVar['currDate'], addZeros = True, zeros = ZeroKelvin, meteo = True)
            self.var.TMin = readmeteodata('TminMaps',dateVar['currDate'], addZeros=True, zeros=ZeroKelvin)

            #self.var.TMax = readnetcdf2('TmaxMaps', dateVar['currDate'], addZeros = True, zeros = ZeroKelvin, meteo = True)
            self.var.TMax = readmeteodata('TmaxMaps', dateVar['currDate'], addZeros=True, zeros=ZeroKelvin)

            #self.var.Psurf = readnetcdf2('PSurfMaps', dateVar['currDate'], addZeros = True, meteo = True)
            self.var.Psurf = readmeteodata('PSurfMaps', dateVar['currDate'], addZeros=True)
                # Instantaneous surface pressure[Pa]
            #self.var.Wind = readnetcdf2('WindMaps', dateVar['currDate'], addZeros = True, meteo = True)
            self.var.Wind = readmeteodata('WindMaps', dateVar['currDate'], addZeros=True)
                # wind speed maps at 10m [m/s]
            #self.var.Rsds = readnetcdf2('RSDSMaps', dateVar['currDate'], addZeros = True, meteo = True)
            self.var.Rsds = readmeteodata('RSDSMaps', dateVar['currDate'], addZeros=True)
                # radiation surface downwelling shortwave maps [W/m2]
            #self.var.Rsdl = readnetcdf2('RSDLMaps', dateVar['currDate'], addZeros = True, meteo = True)
            self.var.Rsdl = readmeteodata('RSDLMaps', dateVar['currDate'], addZeros=True)
                # radiation surface downwelling longwave maps [W/m2]
            if returnBool('useHuss'):
                #self.var.Qair = readnetcdf2('QAirMaps', dateVar['currDate'], addZeros = True, meteo = True)
                self.var.Qair = readmeteodata('QAirMaps', dateVar['currDate'], addZeros=True)
                # 2 m istantaneous specific humidity[kg / kg]
            else:
                #self.var.Qair = readnetcdf2('RhsMaps', dateVar['currDate'], addZeros = True, meteo = True)
                self.var.Qair = readmeteodata('RhsMaps', dateVar['currDate'], addZeros=True)

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

            #self.var.ETRef = readnetcdf2('ETMaps', dateVar['currDate'], addZeros = True, cut = False, meteo = True) * self.var.DtDay * self.var.con_e
            self.var.ETRef = readmeteodata('ETMaps', dateVar['currDate'], addZeros=True) * self.var.DtDay * self.var.con_e
            # daily reference evaporation (conversion to [m] per time step)
            #self.var.EWRef = readnetcdf2('E0Maps', dateVar['currDate'], addZeros = True, cut = False, meteo = True) * self.var.DtDay * self.var.con_e
            self.var.EWRef = readmeteodata('E0Maps', dateVar['currDate'], addZeros=True) * self.var.DtDay * self.var.con_e
            # potential evaporation rate from water surface (conversion to [m] per time step)
            # self.var.ESRef = (self.var.EWRef + self.var.ETRef)/2
            # potential evaporation rate from a bare soil surface (conversion # to [m] per time step)




