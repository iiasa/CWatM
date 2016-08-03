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
     # ************************************************************
     # ***** READ METEOROLOGICAL DATA              ****************
     # ************************************************************
    """

    def __init__(self, readmeteo_variable):
        self.var = readmeteo_variable


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the readmeteo module
            read meteo input maps
        """

        # ************************************************************
        # ***** READ METEOROLOGICAL DATA *****************************
        # ************************************************************
        #self.var.currentTimeStep()
        date = self.var.CalendarDate
        self.var.Precipitation = readnetcdf2(binding['PrecipitationMaps'],date) * self.var.DtDay * self.var.con_precipitation

        #TODO PB
        #self.var.Precipitation = self.var.Precipitation * 0 + 0.2

        # precipitation (conversion to [mm] per time step)
        self.var.Tavg = readnetcdf2(binding['TavgMaps'], date)
        # average DAILY temperature (even if you are running the model
        # on say an hourly time step) [degrees C]
        self.var.ETRef = readnetcdf2(binding['ETMaps'], date) * self.var.DtDay * self.var.con_e
        # daily reference evaporation (conversion to [mm] per time step)
        self.var.EWRef = readnetcdf2(binding['E0Maps'], date) * self.var.DtDay * self.var.con_e
        # potential evaporation rate from water surface (conversion to [mm] per time step)


        #self.var.ESRef = (self.var.EWRef + self.var.ETRef)/2
        # potential evaporation rate from a bare soil surface (conversion # to [mm] per time step)

        if option['TemperatureInKelvin']:
            # if temperature is in Kelvin -> conversion to deg C
            self.var.Tavg -= 273.15