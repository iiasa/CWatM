# -------------------------------------------------------------------------
# Name:        Evaporation module
# Purpose:
#
# Author:      PB
#
# Created:     01/08/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class evaporation(object):

    """
    # ************************************************************
    # ***** Potential and actual Evaporation *********************
    # ************************************************************
    """

    def __init__(self, evaporation_variable):
        self.var = evaporation_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self, coverType, No):
        """ dynamic part of the soil module - potET
         calculating potential Evaporation for each land cover class
         get crop coefficient, use potential ET, calculate potential bare soil evaporation and transpiration
        """

        # get crop coefficient:
        self.var.cropKC = readnetcdf2(binding[coverType + '_cropCoefficientNC'], dateVar['doy'], "DOY")
        self.var.cropKC = np.maximum(self.var.cropKC, self.var.minCropKC[No])

        # calculate potential ET:
        self.var.totalPotET[No] = self.var.cropKC * self.var.ETRef

        # calculate potential bare soil evaporation and transpiration
        self.var.potBareSoilEvap[No] = self.var.minCropKC[No] * self.var.ETRef
        self.var.potTranspiration[No] = self.var.cropKC * self.var.ETRef - self.var.potBareSoilEvap[No]


