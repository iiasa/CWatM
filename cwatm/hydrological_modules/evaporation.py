# -------------------------------------------------------------------------
# Name:        Evaporation module
# Purpose:
#
# Author:      PB
#
# Created:     01/08/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


class evaporation(object):
    """
    Evaporation module
    Calculate potential evaporation and pot. transpiration


    **Global variables**

    ====================  ================================================================================  =========
    Variable [self.var]   Description                                                                       Unit     
    ====================  ================================================================================  =========
    cropKC                crop coefficient for each of the 4 different land cover types (forest, irrigated  --       
    ====================  ================================================================================  =========

    **Functions**
    """

    def __init__(self, model):
        """The constructor evaporation"""
        self.var = model.var
        self.model = model
        
    def dynamic(self, coverType, No):
        """
        Dynamic part of the soil module

        calculating potential Evaporation for each land cover class with kc factor
        get crop coefficient, use potential ET, calculate potential bare soil evaporation and transpiration

        :param coverType: Land cover type: forest, grassland  ...
        :param No: number of land cover type: forest = 0, grassland = 1 ...
        :return: potential evaporation from bare soil, potential transpiration
        """

        # get crop coefficient
        # to get ETc from ET0 x kc factor  ((see http://www.fao.org/docrep/X0490E/x0490e04.htm#TopOfPage figure 4:)
        # crop coefficient read for forest and grassland from file



        # calculate potential bare soil evaporation - only once
        if No == 0:
            self.var.potBareSoilEvap = self.var.cropCorrect * self.var.minCropKC * self.var.ETRef
            # calculate snow evaporation
            self.var.snowEvap =  np.minimum(self.var.SnowMelt, self.var.potBareSoilEvap)
            self.var.SnowMelt = self.var.SnowMelt - self.var.snowEvap
            self.var.potBareSoilEvap = self.var.potBareSoilEvap - self.var.snowEvap

        if dateVar['newStart'] or (dateVar['currDate'].day in [1,11,21]):
            self.var.cropKC[No] = readnetcdf2(coverType + '_cropCoefficientNC', dateVar['10day'], "10day")
            self.var.cropKC[No] = np.maximum(self.var.cropKC[No], self.var.minCropKC)

        """
        if checkOption('includeWaterDemand'):
            m = dateVar['currDate'].month
            if m==1: self.var.cropKC[2] = 0.5
            if m == 2: self.var.cropKC[2] = 0.6
            if m ==3: self.var.cropKC[2] = 0.7
            if m >3:  self.var.cropKC[2] = 0.8

            if m > 9: self.var.cropKC[2] = 0.7
            if m > 10: self.var.cropKC[2] = 0.6
        """



        # calculate potential ET
        ##  self.var.totalPotET total potential evapotranspiration for a reference crop for a land cover class [m]
        self.var.totalPotET[No] = self.var.cropCorrect * self.var.cropKC[No] * self.var.ETRef

        # calculate transpiration

        ## potTranspiration: Transpiration for each land cover class
        self.var.potTranspiration[No] = np.maximum(0.,self.var.totalPotET[No] - self.var.potBareSoilEvap - self.var.snowEvap)



        if checkOption('calcWaterBalance'):
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.Precipitation],  # In
                [self.var.Rain,self.var.SnowMelt,self.var.snowEvap],  # Out
                [self.var.prevSnowCover],   # prev storage
                [self.var.SnowCover],
                "Snow2", False)