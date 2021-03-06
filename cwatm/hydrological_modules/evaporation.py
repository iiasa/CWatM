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
            self.var.cropKC_landCover[No] = self.var.cropKC[No].copy()

        if self.var.includeCrops:
            # includeCrops allows for crops and fallow land to makeup the landcovers grasslands and non-paddy, and
            # maintains including a representative vegetation. It is developed to allow users to decide on the crops
            # and parameters that are relevant for the study. The Excel cwatm_settings.xlsx is used to detail the crops
            # and associated parameters. Crops have a unique planting month and four growth stages. Each stage is associated with a
            # crop coefficient (Kc), yield response factor (Ky), and length.

            if No == 1:
                # Only go through this once:
                # I. new start and II. beginning of the month

                # I. new start
                if dateVar['newStart']:

                    for z in ['ratio_a_p_nonIrr', 'ratio_a_p_Irr',
                              'fracCrops_IrrLandDemand', 'fracCrops_Irr', 'fracCrops_nonIrrLandDemand', 'fracCrops_nonIrr',
                              'activatedCrops', 'monthCounter', 'currentKC', 'totalPotET_month', 'PET_cropIrr_m3',
                              'actTransTotal_month_Irr', 'actTransTotal_month_nonIrr', 'currentKY', 'Yield_Irr',
                              'Yield_nonIrr', 'actTransTotal_crops_Irr', 'actTransTotal_crops_nonIrr']:
                        vars(self.var)[z] = np.tile(globals.inZero, (len(self.var.Crops), 1))

                    # The general crops are representative vegetation.
                    self.var.GeneralCrop_nonIrr = globals.inZero.copy()
                    self.var.GeneralCrop_Irr = globals.inZero.copy()

                    self.var.frac_totalIrr = globals.inZero.copy()
                    self.var.frac_totalnonIrr = globals.inZero.copy()
                    self.var.frac_totalIrr_max = globals.inZero.copy()
                    self.var.frac_totalnonIrr_max = globals.inZero.copy()



                    # to keep a previous planting
                    crop_inflate_factor = 1
                    for i in range(len(self.var.Crops)):

                        self.var.fracCrops_IrrLandDemand[i] = np.where(
                            loadmap(self.var.Crops_names[i] + '_Irr') * crop_inflate_factor <= 1,
                            loadmap(self.var.Crops_names[i] + '_Irr') * crop_inflate_factor, 1)
                        self.var.fracCrops_nonIrrLandDemand[i] = np.where(
                            loadmap(self.var.Crops_names[i] + '_nonIrr') * crop_inflate_factor <= 1,
                            loadmap(self.var.Crops_names[i] + '_nonIrr') * crop_inflate_factor,
                            1)


                    self.var.fallowIrr_max = globals.inZero.copy()
                    self.var.fallownonIrr_max = globals.inZero.copy()
                    self.var.fallowIrr_max = self.var.load_initial('frac_totalIrr_max')
                    self.var.fallownonIrr_max = self.var.load_initial('frac_totalnonIrr_max')

                    # activatedCrops[c] = 1 where crop c is planned in at least 0.001% of the cell, and 0 otherwise.
                    for c in range(len(self.var.Crops)):

                        self.var.activatedCrops[c] = (self.var.fracCrops_IrrLandDemand[c] +
                                                      self.var.fracCrops_nonIrrLandDemand[c] + 0.99999) // 1
                        self.var.activatedCrops[c] = np.maximum(
                            self.var.load_initial("activatedCrops_" + str(c)), self.var.activatedCrops[c])

                        self.var.fracCrops_Irr[c] = self.var.load_initial('fracCrops_Irr_' + str(c))
                        self.var.fracCrops_nonIrr[c] = self.var.load_initial('fracCrops_nonIrr_' + str(c))
                        self.var.monthCounter[c] = self.var.load_initial("monthCounter_" + str(c))


                if dateVar['currDate'].day == 1:

                    if checkOption('moveIrrFallowToNonIrr'):

                        # The irrigated land classes may have given up its fallow land to the grasslands land class.
                        # If this is the case, these fallow lands are returned to the irrigated land class briefly to
                        # allow them to be planted on in the irrigated land class, and then returned to the
                        # grasslands land class.

                        self.var.fracVegCover[3] = self.var.irrigatedArea_original.copy()

                        remainderLand = np.maximum(
                            globals.inZero.copy() + 1 - self.var.fracVegCover[4] - self.var.fracVegCover[3] -
                            self.var.fracVegCover[5] - self.var.fracVegCover[2] - self.var.fracVegCover[0],
                            globals.inZero.copy())

                        self.var.fracVegCover[1] = remainderLand.copy()


                    for c in range(len(self.var.Crops)):

                        # Dawn of the next month
                        # We first harvest, and then we plant

                        # Add a month, if the crop has already been planted

                        self.var.monthCounter[c] += np.where(self.var.monthCounter[c] > 0, 1, 0)

                        # Calculate relative yield for the last month

                        self.var.ratio_a_p_nonIrr[c] = np.where(
                            self.var.totalPotET_month[c] * self.var.activatedCrops[c] > 0,
                            self.var.actTransTotal_month_nonIrr[c] / (self.var.totalPotET_month[c] * self.var.fracCrops_nonIrr[c]),
                            0)  # This should always be <= 1.

                        self.var.ratio_a_p_Irr[c] = np.where(
                            self.var.totalPotET_month[c] * self.var.activatedCrops[c] > 0,
                            self.var.actTransTotal_month_Irr[c] / (self.var.totalPotET_month[c] * self.var.fracCrops_Irr[c]),
                            0)  # This should always be <= 1.

                        self.var.Yield_nonIrr[c] = np.where(self.var.monthCounter[c] > 0,
                                                            np.where(self.var.actTransTotal_month_nonIrr[c] > 0, np.maximum(
                                                                1 - self.var.currentKY[c] * (
                                                                        1 - self.var.ratio_a_p_nonIrr[c]), 0), 0), 0)

                        self.var.Yield_Irr[c] = np.where(self.var.monthCounter[c] > 0,
                                                         np.where(self.var.actTransTotal_month_Irr[c] > 0, np.maximum(
                                                             1 - self.var.currentKY[c] * (
                                                                     1 - self.var.ratio_a_p_Irr[c]), 0), 0), 0)

                        # With the previous month's calculations of yields completed, on this first day of the month, we
                        # reset the running totals of potential transpiration and transpiration (m)
                        self.var.totalPotET_month[c] = globals.inZero.copy()
                        self.var.actTransTotal_month_nonIrr[c] = globals.inZero.copy()
                        self.var.actTransTotal_month_Irr[c] = globals.inZero.copy()

                        # Harvest crops that are finished growing: reset month counter and KC. New seeds are sown after harvesting towards the end.
                        self.var.monthCounter[c] = np.where(self.var.monthCounter[c] > self.var.Crops[c][-1][0], 0,
                                                            self.var.monthCounter[c])
                        self.var.currentKC[c] = np.where(self.var.monthCounter[c] == 0, 0, self.var.currentKC[c])


                        # Removing crops that been harvested
                        self.var.fracCrops_Irr[c] = np.where(self.var.monthCounter[c] > 0, self.var.fracCrops_Irr[c], 0)
                        self.var.fracCrops_nonIrr[c] = np.where(self.var.monthCounter[c] > 0, self.var.fracCrops_nonIrr[c],
                                                                0)

                        for a in range(1, 4):

                            self.var.currentKC[c] = np.where(self.var.monthCounter[c] > self.var.Crops[c][a][0],
                                                             self.var.Crops[c][a + 1][1], self.var.currentKC[c])
                            self.var.currentKY[c] = np.where(self.var.monthCounter[c] > self.var.Crops[c][a][0],
                                                             self.var.Crops[c][a + 1][2], self.var.currentKY[c])

                        # This calculates the current land being used for irrigated and non-irrigated crops
                        frac_totalIrr, frac_totalnonIrr = 0, 0
                        for i in range(len(self.var.Crops)):
                            frac_totalIrr += self.var.fracCrops_Irr[i]
                            frac_totalnonIrr += self.var.fracCrops_nonIrr[i]

                        remainder_land_nonIrr = self.var.fracVegCover[1] - frac_totalnonIrr
                        remainder_land_Irr = self.var.fracVegCover[3] - frac_totalIrr

                        # Sowing seeds, if crop is not already growing, if there is sufficient space

                        # If it is the planting month of the crop, the crop is planted both irrigated and non-irrigated, assuming the demanded land can be satisfied.

                        self.var.fracCrops_Irr[c] = np.where(
                            self.var.Crops[c][0] == dateVar['currDate'].month and self.var.monthCounter[c] == 0,
                            np.where(remainder_land_Irr - self.var.fracCrops_IrrLandDemand[c] > 0,
                                     self.var.fracCrops_IrrLandDemand[c], 0), self.var.fracCrops_Irr[c])

                        if checkOption('leftoverIrrigatedCropIsRainfed'):
                            self.var.fracCrops_nonIrrLandDemand[c] = self.var.fracCrops_IrrLandDemand[c] - \
                                                                     self.var.fracCrops_Irr[c]

                        self.var.fracCrops_nonIrr[c] = np.where(
                            self.var.Crops[c][0] == dateVar['currDate'].month and self.var.monthCounter[c] == 0,
                            np.where(remainder_land_nonIrr - self.var.fracCrops_nonIrrLandDemand[c] > 0,
                                     self.var.fracCrops_nonIrrLandDemand[c], 0), self.var.fracCrops_nonIrr[c])

                        frac_totalIrr, frac_totalnonIrr = globals.inZero.copy(), globals.inZero.copy()
                        for i in range(len(self.var.Crops)):
                            frac_totalIrr += self.var.fracCrops_Irr[i]
                            frac_totalnonIrr += self.var.fracCrops_nonIrr[i]

                        # self.var.frac_totalIrr = frac_totalIrr.copy()
                        # self.var.frac_totalnonIrr = frac_totalnonIrr.copy()

                        remainder_land_nonIrr = self.var.fracVegCover[1] - frac_totalnonIrr
                        remainder_land_Irr = self.var.fracVegCover[3] - frac_totalIrr

                        # When it is the crop's planting month and it is not yet already planted (the month counter is zero).
                        # The counter only starts if there is some of the crop growing in the cell (it is activated).
                        # Otherwise, the month counter is kept constant

                        self.var.monthCounter[c] = np.where(
                            self.var.Crops[c][0] == dateVar['currDate'].month and self.var.monthCounter[c] == 0,
                            self.var.activatedCrops[c], self.var.monthCounter[c])

                        self.var.currentKC[c] = np.where(
                            self.var.Crops[c][0] == dateVar['currDate'].month and self.var.monthCounter[c] == 1,
                            self.var.Crops[c][1][1],
                            self.var.currentKC[c])
                        self.var.currentKY[c] = np.where(
                            self.var.Crops[c][0] == dateVar['currDate'].month and self.var.monthCounter[c] == 1,
                            self.var.Crops[c][1][2],
                            self.var.currentKY[c])

            if No == 3 and (dateVar['newStart'] or dateVar['currDate'].day == 1):

                frac_totalIrr, frac_totalnonIrr = globals.inZero.copy(), globals.inZero.copy()
                for i in range(len(self.var.Crops)):
                    frac_totalIrr += self.var.fracCrops_Irr[i]
                    frac_totalnonIrr += self.var.fracCrops_nonIrr[i]

                self.var.frac_totalIrr = frac_totalIrr.copy()
                self.var.frac_totalnonIrr = frac_totalnonIrr.copy()

                self.var.frac_totalIrr_max = np.maximum(frac_totalIrr, self.var.frac_totalIrr_max)
                self.var.frac_totalnonIrr_max = np.maximum(frac_totalnonIrr, self.var.frac_totalnonIrr_max)
                self.var.generalIrrCrop_max = self.var.fracVegCover[3] - self.var.frac_totalIrr_max
                self.var.generalnonIrrCrop_max = self.var.fracVegCover[1] - self.var.frac_totalnonIrr_max

                # The representative vegetation is determined from a specific user-input map, as compared to being
                # determined automatically otherwise.
                if 'GeneralCrop_Irr' in binding and True and checkOption('use_GeneralCropIrr') == True:
                    self.var.GeneralCrop_Irr = loadmap('GeneralCrop_Irr')
                    self.var.GeneralCrop_Irr = np.minimum(self.var.fracVegCover[3] - frac_totalIrr,
                                                          self.var.GeneralCrop_Irr)

                # Fallowing and general crop are determined automatically, and are not specific input maps.
                elif checkOption('use_GeneralCropIrr') == False:

                    # Fallow land exists alongside general land as non-specific crop options.
                    if checkOption('activate_fallow') == True:

                        # Crop land that has been previously planted by a specific-crop is fallowed between plantings.
                        if checkOption('automaticFallowingIrr') == True:
                            self.var.GeneralCrop_Irr = self.var.generalIrrCrop_max.copy()

                        # With the interest in fallowing without automatic fallowing nor a specific input map implies
                        # the scenario without general lands -- only specific planted crops and fallow land.
                        else:
                            self.var.GeneralCrop_Irr = globals.inZero.copy()

                    else:
                        # activate_fallow = False implies that all non-planted grassland and non-paddy land is made
                        # to be representative vegetation.
                        self.var.GeneralCrop_Irr = self.var.fracVegCover[3] - self.var.frac_totalIrr

                self.var.weighted_KC_Irr = self.var.GeneralCrop_Irr * self.var.cropKC_landCover[3]

                self.var.fallowIrr = self.var.fracVegCover[3] - (self.var.frac_totalIrr + self.var.GeneralCrop_Irr)
                self.var.fallowIrr_max = np.maximum(self.var.fallowIrr, self.var.fallowIrr_max)

                # Updating irrigated land to not include fallow
                # Irrigated fallow land is moved to non-irrigated fallow land. Irrigated fallow land is

                if checkOption('moveIrrFallowToNonIrr'):

                    self.var.fracVegCover[3] = self.var.frac_totalIrr + self.var.GeneralCrop_Irr
                    remainderLand = np.maximum(
                        globals.inZero.copy() + 1 - self.var.fracVegCover[4] - self.var.fracVegCover[3] -
                        self.var.fracVegCover[5] - self.var.fracVegCover[2] - self.var.fracVegCover[0],
                        globals.inZero.copy())

                    self.var.fracVegCover[1] = remainderLand.copy()


                for c in range(len(self.var.Crops)):
                    self.var.weighted_KC_Irr += self.var.fracCrops_Irr[c] * self.var.currentKC[c]
                self.var.weighted_KC_Irr /= self.var.fracVegCover[3]

                self.var.cropKC[3] = np.where(self.var.fracVegCover[3] > 0, self.var.weighted_KC_Irr, 0)

                if 'GeneralCrop_nonIrr' in binding and checkOption('use_GeneralCropnonIrr') == True:

                    self.var.GeneralCrop_nonIrr = loadmap('GeneralCrop_nonIrr')
                    self.var.GeneralCrop_nonIrr = np.minimum(self.var.fracVegCover[1] - frac_totalnonIrr,
                                                             self.var.GeneralCrop_nonIrr)

                elif checkOption('use_GeneralCropnonIrr') == False:
                    if checkOption('activate_fallow') == True:
                        # if fallow is activated, it must be automatically generated for non-irrigated lands, or not at all, but necessary if activated, which is suggested
                        self.var.GeneralCrop_nonIrr = self.var.generalnonIrrCrop_max.copy()
                    else:
                        self.var.GeneralCrop_nonIrr = self.var.fracVegCover[1] - self.var.frac_totalnonIrr

                self.var.weighted_KC_nonIrr = self.var.GeneralCrop_nonIrr * self.var.cropKC_landCover[1]

                self.var.fallownonIrr = self.var.fracVegCover[1] - (
                        self.var.frac_totalnonIrr + self.var.GeneralCrop_nonIrr)
                self.var.fallownonIrr_max = np.maximum(self.var.fallownonIrr, self.var.fallownonIrr_max)

                self.var.availableArableLand = self.var.fallowIrr + self.var.fracVegCover[1] - frac_totalnonIrr

                for c in range(len(self.var.Crops)):
                    self.var.weighted_KC_nonIrr += self.var.fracCrops_nonIrr[c] * self.var.currentKC[c]
                self.var.weighted_KC_nonIrr /= self.var.fracVegCover[1]

                self.var.cropKC[1] = np.where(self.var.fracVegCover[1] > 0, self.var.weighted_KC_nonIrr, 0)

        # calculate potential ET
        ##  self.var.totalPotET total potential evapotranspiration for a reference crop for a land cover class [m]
        self.var.totalPotET[No] = self.var.cropCorrect * self.var.cropKC[No] * self.var.ETRef

        # calculate transpiration


        ## potTranspiration: Transpiration for each land cover class
        self.var.potTranspiration[No] = np.maximum(0.,self.var.totalPotET[No] - self.var.potBareSoilEvap - self.var.snowEvap)

        if self.var.includeCrops: #checkOption('includeCrops') and checkOption('includeCropSpecificWaterUse'):
            if No == 3:
                for c in range(len(self.var.Crops)):

                    self.var.totalPotET_month[c] += np.maximum(0., self.var.cropCorrect * self.var.currentKC[c] * self.var.ETRef - self.var.potBareSoilEvap - self.var.snowEvap)
                    self.var.PET_cropIrr_m3[c] = self.var.cropCorrect * self.var.currentKC[c] * self.var.ETRef * \
                                                 self.var.fracCrops_Irr[
                                                     c] * self.var.cellArea

        if checkOption('calcWaterBalance'):
            self.model.waterbalance_module.waterBalanceCheck(
                [self.var.Precipitation],  # In
                [self.var.Rain,self.var.SnowMelt,self.var.snowEvap],  # Out
                [self.var.prevSnowCover],   # prev storage
                [self.var.SnowCover],
                "Snow2", False)