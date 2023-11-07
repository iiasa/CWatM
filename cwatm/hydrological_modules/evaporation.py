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
import re

class evaporation(object):
    """
    Evaporation module
    Calculate potential evaporation and pot. transpiration


    **Global variables**

    =====================================  ======================================================================  =====
    Variable [self.var]                    Description                                                             Unit 
    =====================================  ======================================================================  =====
    snowEvap                               total evaporation from snow for a snow layers                           m    
    cropKC_landCover                                                                                               --   
    Crops_names                            Internal: List of specific crops                                        --   
    activatedCrops                                                                                                 --   
    load_initial                           Settings initLoad holds initial conditions for variables                input
    fracCrops_nonIrr                       Fraction of cell currently planted with specific non-irr crops          --   
    monthCounter                                                                                                   --   
    fracCrops_IrrLandDemand                                                                                        --   
    fracCrops_nonIrrLandDemand                                                                                     --   
    ratio_a_p_nonIrr                       Ratio actual to potential evapotranspiration, monthly, non-irrigated [  %    
    totalPotET_month                                                                                               --   
    ratio_a_p_Irr                          Ratio actual to potential evapotranspiration, monthly [crop specific]   %    
    Yield_nonIrr                           Relative monthly non-irrigated yield [crop specific]                    %    
    currentKY                              Yield sensitivity coefficient [crop specific]                           Posit
    Yield_Irr                              Relative monthly irrigated yield [crop specific]                        %    
    currentKC                              Current crop coefficient for specific crops                             --   
    generalIrrCrop_max                                                                                             --   
    generalnonIrrCrop_max                                                                                          --   
    weighted_KC_nonIrr                                                                                             --   
    weighted_KC_Irr                                                                                                --   
    weighted_KC_Irr_woFallow_fullKc                                                                                --   
    _weighted_KC_Irr                                                                                               --   
    weighted_KC_Irr_woFallow                                                                                       --   
    PotET_crop                                                                                                     --   
    totalPotET_month_segment                                                                                       --   
    PotETaverage_crop_segments                                                                                     --   
    areaCrops_Irr_segment                                                                                          --   
    areaCrops_nonIrr_segment                                                                                       --   
    areaPaddy_Irr_segment                                                                                          --   
    Precipitation_segment                                                                                          --   
    availableArableLand_segment                                                                                    --   
    cropCorrect                            calibration factor of crop KC factor                                    --   
    includeCrops                           1 when includeCrops=True in Settings, 0 otherwise                       bool 
    Crops                                  Internal: List of specific crops and Kc/Ky parameters                   --   
    potTranspiration                       Potential transpiration (after removing of evaporation)                 m    
    cropKC                                 crop coefficient for each of the 4 different land cover types (forest,  --   
    minCropKC                              minimum crop factor (default 0.2)                                       --   
    irrigatedArea_original                                                                                         --   
    frac_totalnonIrr                       Fraction sown with specific non-irrigated crops                         %    
    frac_totalIrr_max                      Fraction sown with specific irrigated crops, maximum throughout simula  %    
    frac_totalnonIrr_max                   Fraction sown with specific non-irrigated crops, maximum throughout si  %    
    GeneralCrop_Irr                        Fraction of irrigated land class sown with generally representative cr  %    
    fallowIrr                              Fraction of fallowed irrigated land                                     %    
    fallowIrr_max                          Fraction of fallowed irrigated land, maximum throughout simulation      %    
    GeneralCrop_nonIrr                     Fraction of grasslands sown with generally representative crop          %    
    fallownonIrr                           Fraction of fallowed non-irrigated land                                 %    
    fallownonIrr_max                       Fraction of fallowed non-irrigated land, maximum throughout simulation  %    
    availableArableLand                    Fraction of land not currently planted with specific crops              %    
    cellArea                               Area of cell                                                            m2   
    ETRef                                  potential evapotranspiration rate from reference crop                   m    
    Precipitation                          Precipitation (input for the model)                                     m    
    SnowMelt                               total snow melt from all layers                                         m    
    Rain                                   Precipitation less snow                                                 m    
    prevSnowCover                          snow cover of previous day (only for water balance)                     m    
    SnowCover                              snow cover (sum over all layers)                                        m    
    potBareSoilEvap                        potential bare soil evaporation (calculated with minus snow evaporatio  m    
    irr_Paddy_month                                                                                                --   
    fracCrops_Irr                          Fraction of cell currently planted with specific irrigated crops        %    
    actTransTotal_month_nonIrr             Internal variable: Running total of  transpiration for specific non-ir  m    
    actTransTotal_month_Irr                Internal variable: Running total of  transpiration for specific irriga  m    
    irr_crop_month                                                                                                 --   
    frac_totalIrr                          Fraction sown with specific irrigated crops                             %    
    weighted_KC_nonIrr_woFallow                                                                                    --   
    totalPotET                             Potential evaporation per land use class                                m    
    fracVegCover                           Fraction of specific land covers (0=forest, 1=grasslands, etc.)         %    
    adminSegments                          Domestic agents                                                         Int  
    =====================================  ======================================================================  =====

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
            # calculate snow and ice evaporation
            self.var.snowEvap = np.minimum(self.var.SnowMelt, self.var.potBareSoilEvap)
            self.var.potBareSoilEvap -= self.var.snowEvap

            self.var.iceEvap = np.minimum(self.var.IceMelt, self.var.potBareSoilEvap)
            self.var.potBareSoilEvap -= self.var.iceEvap

            self.var.SnowMelt -= self.var.snowEvap
            self.var.IceMelt -= self.var.iceEvap

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

                    for z in ['irrM3_Paddy_month_segment', 'irr_Paddy_month', 'irr_crop', 'irr_crop_month', 'irrM3_crop_month_segment', 'ratio_a_p_nonIrr', 'ratio_a_p_Irr',
                              'fracCrops_IrrLandDemand', 'fracCrops_Irr', 'areaCrops_Irr_segment', 'areaCrops_nonIrr_segment', 'fracCrops_nonIrrLandDemand', 'fracCrops_nonIrr',
                              'activatedCrops', 'monthCounter', 'currentKC', 'totalPotET_month', 'PET_cropIrr_m3',
                              'actTransTotal_month_Irr', 'actTransTotal_month_nonIrr', 'currentKY', 'Yield_Irr',
                              'Yield_nonIrr', 'actTransTotal_crops_Irr', 'actTransTotal_crops_nonIrr', 'PotET_crop', 'PotETaverage_crop_segments', 'totalPotET_month_segment']:
                        vars(self.var)[z] = np.tile(globals.inZero, (len(self.var.Crops), 1))

                    self.var.irr_Paddy_month = globals.inZero
                    for z in [crop for crop in self.var.Crops_names]:
                        vars(self.var)[z + '_Irr'] = globals.inZero
                        vars(self.var)[z + '_nonIrr'] = globals.inZero

                    # The general crops are representative vegetation.

                    for c in range(len(self.var.Crops)):

                        self.var.activatedCrops[c] = self.var.load_initial("activatedCrops_" + str(c))
                        self.var.fracCrops_Irr[c] = self.var.load_initial('fracCrops_Irr_' + str(c))
                        self.var.fracCrops_nonIrr[c] = self.var.load_initial('fracCrops_nonIrr_' + str(c))
                        self.var.monthCounter[c] = self.var.load_initial("monthCounter_" + str(c))

                if dateVar['newStart'] or dateVar['newYear']:

                    crop_inflate_factor = 1
                    for i in range(len(self.var.Crops)):

                        try:
                            self.var.fracCrops_IrrLandDemand[i] = np.where(
                                loadmap(self.var.Crops_names[i] + '_Irr') * crop_inflate_factor <= 1,
                                loadmap(self.var.Crops_names[i] + '_Irr') * crop_inflate_factor, 1)
                            self.var.fracCrops_nonIrrLandDemand[i] = np.where(
                                loadmap(self.var.Crops_names[i] + '_nonIrr') * crop_inflate_factor <= 1,
                                loadmap(self.var.Crops_names[i] + '_nonIrr') * crop_inflate_factor,
                                1)

                        except:

                            self.var.fracCrops_IrrLandDemand[i] = readnetcdf2(self.var.Crops_names[i] + '_Irr', dateVar['currDate'],
                                                                  'yearly',
                                                                  value=re.split(r'[^a-zA-Z0-9_[\]]', cbinding(self.var.Crops_names[i] + '_Irr'))[-2])


                            self.var.fracCrops_nonIrrLandDemand[i] = readnetcdf2(self.var.Crops_names[i] + '_nonIrr', dateVar['currDate'],
                                                                  'yearly',
                                                                  value=re.split(r'[^a-zA-Z0-9_[\]]', cbinding(self.var.Crops_names[i] + '_nonIrr'))[-2])

                        # in two places
                        if 'crops_leftoverNotIrrigated' in binding:
                            if i <= int(cbinding('crops_leftoverNotIrrigated')):
                                #print('in evaporation: some crops not rainfed')
                                self.var.fracCrops_nonIrrLandDemand[i] = globals.inZero.copy()

                        # activatedCrops[c] = 1 where crop c is planned in at least 0.001% of the cell, and 0 otherwise.
                        self.var.activatedCrops[i] = np.minimum(np.maximum((self.var.fracCrops_IrrLandDemand[i] +
                                                                            self.var.fracCrops_nonIrrLandDemand[i] + 0.99999) // 1,
                                                                           self.var.activatedCrops[i]), 1)



                if dateVar['currDate'].day == 1:

                    if 'moveIrrFallowToNonIrr' in option:
                        if checkOption('moveIrrFallowToNonIrr'):

                            # The irrigated land class may have given up fallow land to the grasslands land class.
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
                        self.var.irr_crop_month[c] = globals.inZero.copy()
                        self.var.irr_Paddy_month = globals.inZero.copy()

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
                        frac_totalIrr, frac_totalnonIrr = globals.inZero.copy(), globals.inZero.copy()
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

                        if 'leftoverIrrigatedCropIsRainfed' in option:
                            if checkOption('leftoverIrrigatedCropIsRainfed'):
                                self.var.fracCrops_nonIrrLandDemand[c] = self.var.fracCrops_IrrLandDemand[c] - \
                                                                         self.var.fracCrops_Irr[c]

                                if 'crops_leftoverNotIrrigated' in binding:
                                    if c <= int(cbinding('crops_leftoverNotIrrigated')):
                                        self.var.fracCrops_nonIrrLandDemand[c] = globals.inZero.copy()

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

                #if No == 3 and (dateVar['newStart'] or dateVar['currDate'].day == 1):
                if dateVar['newStart'] or dateVar['currDate'].day == 1:

                    frac_totalIrr, frac_totalnonIrr = globals.inZero.copy(), globals.inZero.copy()
                    for i in range(len(self.var.Crops)):
                        frac_totalIrr += self.var.fracCrops_Irr[i]
                        frac_totalnonIrr += self.var.fracCrops_nonIrr[i]

                    self.var.frac_totalIrr = frac_totalIrr.copy()
                    self.var.frac_totalnonIrr = frac_totalnonIrr.copy()

                    self.var.frac_totalIrr_max = np.maximum(frac_totalIrr, self.var.frac_totalIrr_max)
                    self.var.frac_totalnonIrr_max = np.maximum(frac_totalnonIrr, self.var.frac_totalnonIrr_max)
                    # UNDER CONSTRUCTION: Automatic fallowing for irrigated land
                    self.var.generalIrrCrop_max = np.maximum(self.var.fracVegCover[3] - self.var.frac_totalIrr_max, globals.inZero.copy())
                    self.var.generalnonIrrCrop_max = np.maximum(self.var.fracVegCover[1] - self.var.frac_totalnonIrr_max, globals.inZero.copy())

                    # The representative vegetation is determined from a specific user-input map, as compared to being
                    # determined automatically otherwise.
                    if 'GeneralCrop_Irr' in binding and checkOption('use_GeneralCropIrr') == True:
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



                    self.var.fallowIrr = self.var.fracVegCover[3] - (self.var.frac_totalIrr + self.var.GeneralCrop_Irr)
                    self.var.fallowIrr_max = np.maximum(self.var.fallowIrr, self.var.fallowIrr_max)

                    # Updating irrigated land to not include fallow
                    # Irrigated fallow land is moved to non-irrigated fallow land. Irrigated fallow land is

                    #UNDER CONSTRUCTION
                    if 'moveIrrFallowToNonIrr' in option:
                        if checkOption('moveIrrFallowToNonIrr'):

                            self.var.fracVegCover[3] = self.var.frac_totalIrr + self.var.GeneralCrop_Irr
                            remainderLand = np.maximum(
                                globals.inZero.copy() + 1 - self.var.fracVegCover[4] - self.var.fracVegCover[3] -
                                self.var.fracVegCover[5] - self.var.fracVegCover[2] - self.var.fracVegCover[0],
                                globals.inZero.copy())

                            self.var.fracVegCover[1] = remainderLand.copy()


                    if 'GeneralCrop_nonIrr' in binding and checkOption('use_GeneralCropnonIrr') == True:

                        self.var.GeneralCrop_nonIrr = loadmap('GeneralCrop_nonIrr')
                        self.var.GeneralCrop_nonIrr = np.minimum(self.var.fracVegCover[1] - frac_totalnonIrr,
                                                                 self.var.GeneralCrop_nonIrr)

                    elif checkOption('use_GeneralCropnonIrr') == False:
                        if checkOption('activate_fallow') == True:
                            self.var.GeneralCrop_nonIrr = self.var.generalnonIrrCrop_max.copy()
                        else:
                            self.var.GeneralCrop_nonIrr = self.var.fracVegCover[1] - self.var.frac_totalnonIrr

                    self.var.fallownonIrr = self.var.fracVegCover[1] - (
                            self.var.frac_totalnonIrr + self.var.GeneralCrop_nonIrr)
                    self.var.fallownonIrr_max = np.maximum(self.var.fallownonIrr, self.var.fallownonIrr_max)

                    self.var.availableArableLand = self.var.fallowIrr + self.var.fracVegCover[1] - frac_totalnonIrr

            if No == 1:

                self.var.weighted_KC_nonIrr = self.var.GeneralCrop_nonIrr * self.var.cropKC_landCover[1]
                for c in range(len(self.var.Crops)):
                    self.var.weighted_KC_nonIrr += self.var.fracCrops_nonIrr[c] * self.var.currentKC[c]
                self.var.weighted_KC_nonIrr_woFallow = self.var.weighted_KC_nonIrr.copy()

                self.var.weighted_KC_nonIrr += self.var.fallownonIrr * self.var.minCropKC
                self.var.weighted_KC_nonIrr = np.where(self.var.fracVegCover[1] > 0,
                                                    self.var.weighted_KC_nonIrr / self.var.fracVegCover[1], 0)
                self.var.cropKC[1] = self.var.weighted_KC_nonIrr.copy()

            if No == 3:

                self.var.weighted_KC_Irr = self.var.GeneralCrop_Irr * self.var.cropKC_landCover[3]
                for c in range(len(self.var.Crops)):
                    self.var.weighted_KC_Irr += self.var.fracCrops_Irr[c] * self.var.currentKC[c]
                self.var.weighted_KC_Irr_woFallow_fullKc = self.var.weighted_KC_Irr.copy()

                self.var.weighted_KC_Irr += self.var.fallowIrr * self.var.minCropKC
                self.var.weighted_KC_Irr = np.where(self.var.fracVegCover[3] > 0,
                                                    self.var.weighted_KC_Irr / self.var.fracVegCover[3], 0)
                self.var.cropKC[3] = self.var.weighted_KC_Irr.copy()

                self.var._weighted_KC_Irr = self.var.GeneralCrop_Irr * (self.var.cropKC_landCover[3]-self.var.minCropKC)
                for c in range(len(self.var.Crops)):
                    self.var._weighted_KC_Irr += self.var.fracCrops_Irr[c] * (self.var.currentKC[c]-self.var.minCropKC)
                self.var.weighted_KC_Irr_woFallow = self.var._weighted_KC_Irr.copy()
                

        # calculate potential ET
        ##  self.var.totalPotET total potential evapotranspiration for a reference crop for a land cover class [m]
        self.var.totalPotET[No] = self.var.cropCorrect * self.var.cropKC[No] * self.var.ETRef

        # calculate transpiration


        ## potTranspiration: Transpiration for each land cover class
        self.var.potTranspiration[No] = np.maximum(0., self.var.totalPotET[No] - self.var.potBareSoilEvap) #Dealt with above - self.var.snowEvap)

        if self.var.includeCrops: #checkOption('includeCrops') and checkOption('includeCropSpecificWaterUse'):

            if No == 3: #only goes through ones

                for c in range(len(self.var.Crops)):

                    self.var.PotET_crop[c] = self.var.cropCorrect * self.var.currentKC[c] * self.var.ETRef
                    self.var.totalPotET_month[c] += self.var.PotET_crop[c] #self.var.cropCorrect * self.var.currentKC[c] * self.var.ETRef #np.maximum(0., self.var.cropCorrect * self.var.currentKC[c] * self.var.ETRef - self.var.potBareSoilEvap - self.var.snowEvap)

                    #For creating named crop maps
                    #vars(self.var)[self.var.Crops_names[c]+'_Irr'] = self.var.fracCrops_Irr[c].copy()
                    #vars(self.var)[self.var.Crops_names[c] + '_nonIrr'] = self.var.fracCrops_nonIrr[c].copy()

                    if 'adminSegments' in binding:
                        self.var.totalPotET_month_segment[c] = npareaaverage(self.var.totalPotET_month[c], self.var.adminSegments)
                        self.var.PotETaverage_crop_segments[c] = npareaaverage(self.var.PotET_crop[c], self.var.adminSegments)

                        self.var.areaCrops_Irr_segment[c] = npareatotal(self.var.fracCrops_Irr[c] * self.var.cellArea,
                                                                        self.var.adminSegments)

                        self.var.areaCrops_nonIrr_segment[c] = npareatotal(
                            self.var.fracCrops_nonIrr[c] * self.var.cellArea,
                            self.var.adminSegments)


                if 'adminSegments' in binding:
                    self.var.areaPaddy_Irr_segment = npareatotal(self.var.fracVegCover[2] * self.var.cellArea,
                                                             self.var.adminSegments)

                    self.var.Precipitation_segment = npareatotal(self.var.Precipitation * self.var.cellArea,
                                                                 self.var.adminSegments)

                    self.var.availableArableLand_segment = npareatotal(self.var.availableArableLand * self.var.cellArea,
                                                                        self.var.adminSegments)





        if checkOption('calcWaterBalance'):
            self.model.waterbalance_module.waterBalanceCheck(
                [self.var.Rain,self.var.Snow],  # In
                [self.var.Rain,self.var.SnowMelt,self.var.IceMelt,self.var.snowEvap,self.var.iceEvap],  # Out
                [self.var.prevSnowCover],   # prev storage
                [self.var.SnowCover],
                "Snow2", False)