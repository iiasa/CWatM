## @package evaporation
# Module documentation

from management_modules.data_handling import *


class evaporation(object):
    """ @brief Evaporation module
    @details Calculate potential and  actual evapotranspiration
    @author  PB
    @date  01/08/2016
    @copyright  PB 2016
    """

    def __init__(self, evaporation_variable):
        """The constructor evaporation"""
        self.var = evaporation_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self, coverType, No):
        """ Dynamic part of the soil module - potET
        calculating potential Evaporation for each land cover class
        get crop coefficient, use potential ET, calculate potential bare soil evaporation and transpiration
        @param coverType (string) land cover type: forest, grassland ..
        @param No [int] Number of land cover type: forest = 0, grassland = 1 ...

        """

        # get crop coefficient
        # crop coefficient read for forest and grassland from file

        ## self.var.cropKC: crop coefficient read for forest and grassland from file
        self.var.cropKC = readnetcdf2(binding[coverType + '_cropCoefficientNC'], dateVar['doy'], "DOY")
        self.var.cropKC = np.maximum(self.var.cropKC, self.var.minCropKC[No])

        # calculate potential ET
        ##  self.var.totalPotET total potential evapotranspiration for a reference crop for a land cover class
        self.var.totalPotET[No] = self.var.cropKC * self.var.ETRef

        # calculate potential bare soil evaporation and transpiration
        self.var.potBareSoilEvap[No] = self.var.minCropKC[No] * self.var.ETRef
        ## potTranspiration: Transpiration for each land cover class
        self.var.potTranspiration[No] = self.var.cropKC * self.var.ETRef - self.var.potBareSoilEvap[No]

        # evaporation from bare soil for each land cover class


