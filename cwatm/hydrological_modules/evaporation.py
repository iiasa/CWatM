# -------------------------------------------------------------------------
# Name:        Evaporation module
# Purpose: Potential evapotranspiration and potential transpiration per land cover type.
# Crop coefficients every 30 days, crop calendar (planting, harvest, fallow, yields)
# of grassland and non-paddy, sums per admin segment.
#
# Author:      PB, MS, DF, JdB
# Created:     01/08/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *

class evaporation(object):
    """
    Evaporation module: potential evapotranspiration per land cover and the crop calendar.

    For forest, grassland, paddy and non-paddy: crop coefficient of the day (interpolated between the values every 30 days),
    potential evapotranspiration (KC x ETRef x correction factors) and potential transpiration (minus bare soil
    and snow evaporation). With includeCrops: crop calendar of grassland (rainfed) and non-paddy (irrigated):
    planting and harvest of the crops in months or days, general crop and fallow land, moveIrrFallowToNonIrr,
    the area weighted KC of grassland and non-paddy, potential ET, relative yields of the month per crop and
    the sums per admin segment.

    Attributes
    ----------
    var : object
        Model variables container
    model : object
        CWatM model instance

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    cropKCmonth                          Array         Crop coefficient of land cover 0-3, 13 values every 30 days             --   
    Crops_names                          Array         Internal: List of specific crops                                        --   
    activatedCrops                       Array         1 where the crop is planned in at least 0.001 % of the cell, else 0     --   
    load_initial                         Flag          Settings initLoad holds initial conditions for variables                bool 
    monthCounter                         Array         Months (crops in days: days) since planting, 0: not planted             --   
    fracCrops_IrrLandDemand              Array         Planned fraction of the cell for irrigated crops [crop specific]        --   
    fracCrops_nonIrrLandDemand           Array         Planned fraction of the cell for rainfed crops [crop specific]          --   
    ratio_a_p_nonIrr                     Array         Ratio actual to potential transpiration of the month, rainfed [crop]    --   
    totalPotET_month                     Array         Potential ET of irrigated crops, total of the month [crop specific]     m    
    totalPotET_month_nonIrr              Array         Potential ET of rainfed crops, total of the month [crop specific]       m    
    ratio_a_p_Irr                        Array         Ratio actual to potential transpiration of the month, irrigated [crop]  --   
    Yield_nonIrr                         Array         Relative yield of the month, rainfed [crop specific]                    --   
    currentKY                            Array         Yield sensitivity coefficient [crop specific]                           --   
    Yield_Irr                            Array         Relative yield of the month, irrigated [crop specific]                  --   
    currentKC                            Array         Current crop coefficient [crop specific]                                --   
    generalIrrCrop_max                   Array         Fraction of non-paddy not used by specific crops (at their maximum)     --   
    generalnonIrrCrop_max                Array         Fraction of grassland not used by specific crops (at their maximum)     --   
    weighted_KC_nonIrr                   Array         Crop coefficient of grassland: crops, general crop and fallow           --   
    weighted_KC_nonIrr_woFallow          Array         KC x fraction of crops and general crop on grassland (without fallow)   --   
    weighted_KC_Irr                      Array         Crop coefficient of non-paddy: crops, general crop and fallow           --   
    _weighted_KC_Irr                     Array         Internal: (KC - minCropKC) x fraction of crops and general crop         --   
    weighted_KC_Irr_woFallow             Array         (KC - minCropKC) x fraction of crops, general crop on non-paddy         --   
    totalPotET_month_segment             Array         Potential ET of irrigated crops of the month, mean of admin segment     m    
    PotETaverage_crop_segments           Array         Potential ET of irrigated crops, mean of admin segment [crop]           m    
    areaCrops_Irr_segment                Array         Area of irrigated crops per admin segment [crop specific]               m2   
    areaCrops_nonIrr_segment             Array         Area of rainfed crops per admin segment [crop specific]                 m2   
    areaPaddy_Irr_segment                Array         Area of paddy per admin segment                                         m2   
    Precipitation_segment                Array         Precipitation volume per admin segment                                  m3   
    availableArableLand_segment          Array         Area of available arable land per admin segment                         m2   
    cropCorrect                          Array         calibration factor of crop KC factor                                    --   
    crop_correct_landCover               Array         Correction factor of the crop KC per land cover (from settings)         --   
    includeCrops                         Flag          1 when includeCrops=True in Settings, 0 otherwise                       bool 
    Crops                                Array         Internal: List of specific crops and Kc/Ky parameters                   --   
    daily_crop_KC                        Flag          True if the growth stages in Excel are in days (longest season > 36)    bool 
    interceptCap                         Array         Interception capacity of forest and grassland, 13 values every 30 days  m    
    potTranspiration                     Array         Potential transpiration (after removing of evaporation)                 m    
    cropKC                               Array         Crop coefficient of the day of land cover 0-3 (forest .. non-paddy)     --   
    minCropKC                            Array         minimum crop factor (default 0.2)                                       --   
    minInterceptCap                      Array         minimum interception capacity per land cover type (from settings)       m    
    irrigatedArea_original               Array         Fraction of non-paddy before moveIrrFallowToNonIrr                      --   
    fracAllCover                         Array         Sum of the fractions of all land covers                                 --   
    frac_totalnonIrr                     Array         Fraction planted with specific rainfed crops                            --   
    frac_totalIrr_max                    Array         Fraction planted with specific irrigated crops, maximum so far          --   
    frac_totalnonIrr_max                 Array         Fraction planted with specific rainfed crops, maximum so far            --   
    GeneralCrop_Irr                      Array         Fraction of non-paddy with the general (representative) crop            --   
    fallowIrr                            Array         Fraction of fallow irrigated land (non-paddy)                           --   
    fallowIrr_max                        Array         Fraction of fallow irrigated land, maximum so far                       --   
    GeneralCrop_nonIrr                   Array         Fraction of grassland with the general (representative) crop            --   
    fallownonIrr                         Array         Fraction of fallow grassland                                            --   
    fallownonIrr_max                     Array         Fraction of fallow grassland, maximum so far                            --   
    availableArableLand                  Array         Fraction of fallow non-paddy + grassland without specific crops         --   
    ETRef                                Array         potential evapotranspiration rate from reference crop                   m    
    Precipitation                        Array         Precipitation (input for the model)                                     m    
    coverTypes                           Array         land cover types - forest - grassland - irrPaddy - irrNonPaddy - water  --   
    irr_Paddy_month                      Array         Irrigation of paddy, total of the month                                 m    
    ET_crop_Irr_paddy                    Array         Actual ET of paddy x fraction of paddy (from soil)                      m    
    ET_crop_Irr_paddy_fraccrop           Array         Actual ET of paddy (from soil)                                          m    
    fracCrops_Irr                        Array         Fraction of the cell planted with irrigated crops [crop specific]       --   
    fracCrops_nonIrr                     Array         Fraction of the cell planted with rainfed crops [crop specific]         --   
    actTransTotal_month_nonIrr           Array         Transpiration of rainfed crops, total of the month [crop specific]      m    
    actTransTotal_month_Irr              Array         Transpiration of irrigated crops, total of the month [crop specific]    m    
    irr_crop_month                       Array         Irrigation of crops, total of the month [crop specific]                 m    
    frac_totalIrr                        Array         Fraction planted with specific irrigated crops                          --   
    weighted_KC_Irr_woFallow_fullKc      Array         KC x fraction of crops and general crop on non-paddy (no fallow)        --   
    totalPotET                           Array         Potential evaporation per land use class                                m    
    potBareSoilEvap                      Array         potential bare soil evaporation (calculated with minus snow evaporatio  m    
    PotET_crop                           Array         Potential ET of irrigated crops (non-paddy) [crop specific]             m    
    PotET_crop_nonIrr                    Array         Potential ET of rainfed crops (grassland) [crop specific]               m    
    fracVegCover                         Array         Fraction of specific land covers (0=forest, 1=grasslands, etc.)         --   
    adminSegments                        Array         Domestic agents                                                         Int  
    cellArea                             Array         Area of cell                                                            m2   
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize the evaporation module.

        Parameters
        ----------
        model : object
            CWatM model instance containing variables and configuration
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initialize evaporation module arrays and parameters.

        Reads every 3rd of the 10-day values (13 values: day 1, 31, ..., 361 of the year) of the crop coefficient
        of forest, grassland, paddy and non-paddy (at least minCropKC) and of the interception capacity of forest
        and grassland (at least minInterceptCap).
        """
        # land cover number = position in coverTypes: 0 forest, 1 grassland, 2 irrPaddy, 3 irrNonPaddy
        # without irrigation dynamic runs only for 0 and 1: the KC of paddy and non-paddy is not needed
        noKC = 4 if checkOption('includeIrrigation') else 2
        self.var.cropKCmonth = np.zeros((4, 13, len(globals.inZero)))
        self.var.cropKC = np.zeros((4, len(globals.inZero)))
        self.var.interceptCap = np.zeros((2, 13, len(globals.inZero)))
        for No, coverType in enumerate(self.var.coverTypes[:noKC]):
            for i in range(13):
                self.var.cropKCmonth[No, i, :] = np.maximum(
                    readnetcdf2(coverType + '_cropCoefficientNC', i * 3, "10day"), self.var.minCropKC)
                if No < 2:
                    self.var.interceptCap[No, i, :] = np.maximum(
                        readnetcdf2(coverType + '_interceptCapNC', i * 3, "10day"), self.var.minInterceptCap[No])

    def readCropDemand(self, name):
        """
        Planned fraction of the cell for a crop, from the settings key name (e.g. Wheat_Irr).

        A single map (number, GeoTIFF, netCDF without time) or a netCDF stack with one map per year; the variable
        of the stack has the name of the file (without path and extension).

        Parameters
        ----------
        name : str
            settings key of the crop map

        Returns
        -------
        numpy.ndarray
            planned fraction of the cell (cells)
        """
        try:
            return loadmap(name)
        except CWATMError as mapError:
            # not a single map: a stack with one map per year
            try:
                return readnetcdf2(name, dateVar['currDate'], 'yearly',
                                   value=os.path.splitext(os.path.basename(cbinding(name)))[0])
            except Exception:
                # neither: show the error of the single map, not the one of the stack
                raise mapError

    def dynamic(self, coverType, No):
        """
        Calculate potential evapotranspiration for a specific land cover type.

        This method computes potential evaporation and transpiration using crop coefficients,
        handles crop dynamics when crops are enabled, and calculates bare soil evaporation.
        It processes monthly crop coefficient data with daily interpolation.

        Parameters
        ----------
        coverType : str
            Land cover type identifier (e.g., 'forest', 'grassland', 'irrPaddy')
        No : int
            Numerical identifier for land cover type (forest=0, grassland=1, etc.)

        Returns
        -------
        tuple
            Potential evaporation from bare soil and potential transpiration values
        """

        # crop coefficient: ETc = ET0 x kc factor (see http://www.fao.org/docrep/X0490E/x0490e04.htm figure 4)
        # interpolation for each day from the values every 30 days
        dplus = dateVar['30day'] + 1
        # day within the 30-day period: 0 ... 29 (same base as dateVar['30day'] = (doy - 1) // 30)
        dpart = (dateVar['doy'] - 1) % 30
        # length of the period: 30 days, the last one (from day 361) only to the end of the year (5 or 6 days)
        # -> on 1 January the KC arrives at the January value without a jump (before: jump by 26/30 of the difference)
        plen = 30.
        if dplus > 12:
            dplus = 0
            plen = dateVar['daysInYear'] - 360.
        self.var.cropKC[No] = ((self.var.cropKCmonth[No, dplus, :] - self.var.cropKCmonth[No, dateVar['30day'], :]) / plen *
                               dpart + self.var.cropKCmonth[No, dateVar['30day'], :])
        cropKC_landCover = self.var.cropKC[No]

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

                    for z in ['irrM3_Paddy_month_segment', 'irr_Paddy_month', 'irr_crop', 'irr_crop_month',
                              'irrM3_crop_month_segment', 'ratio_a_p_nonIrr', 'ratio_a_p_Irr',
                              'fracCrops_IrrLandDemand', 'fracCrops_Irr', 'areaCrops_Irr_segment', 'areaCrops_nonIrr_segment',
                              'fracCrops_nonIrrLandDemand', 'fracCrops_nonIrr', 'activatedCrops', 'monthCounter',
                              'currentKC', 'totalPotET_month', 'PET_cropIrr_m3', 'actTransTotal_month_Irr',
                              'actTransTotal_month_nonIrr', 'currentKY', 'Yield_Irr', 'Yield_nonIrr',
                              'actTransTotal_crops_Irr', 'actTransTotal_crops_nonIrr', 'PotET_crop', 'PotET_crop_nonIrr',
                              'totalPotET_month_nonIrr',
                              'PotETaverage_crop_segments', 'totalPotET_month_segment', 'ET_crop_nonIrr', 'ET_crop_Irr',
                              'ratio_a_p_nonIrr_daily', 'ratio_a_p_Irr_daily']:
                        vars(self.var)[z] = np.tile(globals.inZero, (len(self.var.Crops), 1))

                    # copy: never share (and change) globals.inZero - irr_Paddy_month is changed in place
                    # (soil.py: +=), a run starting not on the 1st of a month changed globals.inZero itself
                    self.var.irr_Paddy_month = globals.inZero.copy()
                    for z in [crop for crop in self.var.Crops_names]:
                        vars(self.var)[z + '_Irr'] = globals.inZero.copy()
                        vars(self.var)[z + '_nonIrr'] = globals.inZero.copy()

                    self.var.ET_crop_Irr_paddy = globals.inZero.copy()
                    self.var.ET_crop_Irr_paddy_fraccrop = globals.inZero.copy()

                    for c in range(len(self.var.Crops)):

                        # For creating annual and month total outputs, since such totals don't work with square bracket variables
                        vars(self.var)['ET_crop_Irr_'+str(c)] = globals.inZero.copy()
                        vars(self.var)['ET_crop_Irr_fraccrop_'+str(c)] = globals.inZero.copy()
                        vars(self.var)['ET_crop_nonIrr_'+str(c)] = globals.inZero.copy()
                        vars(self.var)['ET_crop_nonIrr_fraccrop_'+str(c)] = globals.inZero.copy()
                        vars(self.var)['irr_crop_'+str(c)] = globals.inZero.copy()

                        self.var.activatedCrops[c] = self.var.load_initial("activatedCrops_" + str(c))
                        self.var.fracCrops_Irr[c] = self.var.load_initial('fracCrops_Irr_' + str(c))
                        self.var.fracCrops_nonIrr[c] = self.var.load_initial('fracCrops_nonIrr_' + str(c))
                        self.var.monthCounter[c] = self.var.load_initial("monthCounter_" + str(c))
                        # crop coefficients: missing in older init files - one warning for all crops below
                        self.var.currentKC[c] = self.var.load_initial("currentKC_" + str(c), warn=False)
                        self.var.currentKY[c] = self.var.load_initial("currentKY_" + str(c), warn=False)

                    if self.var.loadInit:
                        nocrop = len(self.var.Crops)
                        missing = [c for c in range(nocrop)
                                   if not initialIncluded(self.var.initLoadFile, "currentKC_" + str(c))]
                        if missing:
                            msg = "Warning: Initial values: crop coefficients currentKC_0..%d and currentKY_0..%d" % (
                                nocrop - 1, nocrop - 1)
                            msg += " are not included in: " + self.var.initLoadFile + "\n"
                            msg += "using 0 (as before 2026-10) - they are set on the 1st of the next month"
                            print(CWATMWarning(msg))

                if dateVar['newStart'] or dateVar['newYear']:

                    for i in range(len(self.var.Crops)):

                        # planned fraction of the cell, at most 1
                        self.var.fracCrops_IrrLandDemand[i] = np.minimum(
                            self.readCropDemand(self.var.Crops_names[i] + '_Irr'), 1)
                        self.var.fracCrops_nonIrrLandDemand[i] = np.minimum(
                            self.readCropDemand(self.var.Crops_names[i] + '_nonIrr'), 1)

                        # in two places
                        if 'crops_leftoverNotIrrigated' in binding:
                            if i <= int(cbinding('crops_leftoverNotIrrigated')):
                                #print('in evaporation: some crops not rainfed')
                                self.var.fracCrops_nonIrrLandDemand[i] = globals.inZero.copy()

                        # activatedCrops[c] = 1 where crop c is planned in at least 0.001% of the cell, and 0 otherwise.
                        self.var.activatedCrops[i] = np.minimum(
                            np.maximum((self.var.fracCrops_IrrLandDemand[i] + self.var.fracCrops_nonIrrLandDemand[i] +
                                        0.99999) // 1, self.var.activatedCrops[i]), 1)

                # land cover fractions before moveIrrFallowToNonIrr changes them: the water of the land cover
                # stores is moved with the land after both changes (landcoverType.moveLandcoverStorage)
                moveFallow = 'moveIrrFallowToNonIrr' in option and checkOption('moveIrrFallowToNonIrr')
                if moveFallow:
                    fracOld = np.array(self.var.fracVegCover, copy=True)
                    # warm start: the loaded stores belong to the fractions of the saved day (landcoverType)
                    if getattr(self.var, 'fracVegCoverStart', None) is not None:
                        fracOld = self.var.fracVegCoverStart
                        self.var.fracVegCoverStart = None

                if dateVar['currDate'].day == 1 or self.var.daily_crop_KC:

                    if 'moveIrrFallowToNonIrr' in option:
                        if checkOption('moveIrrFallowToNonIrr'):

                            # The irrigated land class may have given up fallow land to the grasslands land class.
                            # If this is the case, these fallow lands are returned to the irrigated land class briefly to
                            # allow them to be planted on in the irrigated land class, and then returned to the
                            # grasslands land class.

                            self.var.fracVegCover[3] = self.var.irrigatedArea_original.copy()

                            remainderLand = np.maximum(
                                self.var.fracAllCover - self.var.fracVegCover[4] - self.var.fracVegCover[3] -
                                self.var.fracVegCover[5] - self.var.fracVegCover[2] - self.var.fracVegCover[0],
                                globals.inZero.copy())

                            self.var.fracVegCover[1] = remainderLand.copy()


                    # relative yields and the totals of the month: on the 1st of the month, crops in days also
                    # on the day a crop is harvested (the block runs every day, the totals run over the month)
                    newMonth = dateVar['currDate'].day == 1
                    if newMonth:
                        self.var.irr_Paddy_month = globals.inZero.copy()

                    for c in range(len(self.var.Crops)):

                        # Dawn of the next month (crops in days: of the next day)
                        # We first harvest, and then we plant

                        # Add a month (day), if the crop has already been planted
                        self.var.monthCounter[c] += np.where(self.var.monthCounter[c] > 0, 1, 0)

                        # end of the season: harvest today
                        if self.var.daily_crop_KC:
                            harvest = self.var.monthCounter[c] > len(self.var.Crops[c][-1])
                        else:
                            harvest = self.var.monthCounter[c] > self.var.Crops[c][-1][0]
                        endMonth = True if newMonth else harvest

                        # Calculate relative yield for the last month (always <= 1)
                        ratioNonIrr = np.where(
                            self.var.totalPotET_month_nonIrr[c] * self.var.activatedCrops[c] * self.var.fracCrops_nonIrr[c] > 0,
                            self.var.actTransTotal_month_nonIrr[c] / (
                                self.var.totalPotET_month_nonIrr[c] * self.var.fracCrops_nonIrr[c]),
                            0)
                        ratioIrr = np.where(
                            self.var.totalPotET_month[c] * self.var.activatedCrops[c] * self.var.fracCrops_Irr[c] > 0,
                            self.var.actTransTotal_month_Irr[c] / (
                                self.var.totalPotET_month[c] * self.var.fracCrops_Irr[c]),
                            0)
                        yieldNonIrr = np.where(
                            self.var.monthCounter[c] > 0,
                            np.where(self.var.actTransTotal_month_nonIrr[c] > 0,
                                     np.maximum(1 - self.var.currentKY[c] * (1 - ratioNonIrr), 0),
                                     0), 0)
                        yieldIrr = np.where(
                            self.var.monthCounter[c] > 0,
                            np.where(self.var.actTransTotal_month_Irr[c] > 0,
                                     np.maximum(1 - self.var.currentKY[c] * (1 - ratioIrr), 0),
                                     0), 0)
                        self.var.ratio_a_p_nonIrr[c] = np.where(endMonth, ratioNonIrr, self.var.ratio_a_p_nonIrr[c])
                        self.var.ratio_a_p_Irr[c] = np.where(endMonth, ratioIrr, self.var.ratio_a_p_Irr[c])
                        self.var.Yield_nonIrr[c] = np.where(endMonth, yieldNonIrr, self.var.Yield_nonIrr[c])
                        self.var.Yield_Irr[c] = np.where(endMonth, yieldIrr, self.var.Yield_Irr[c])

                        # With the previous month's calculations of yields completed, we reset the running totals of
                        # potential transpiration, transpiration and irrigation (m)
                        for total in (self.var.totalPotET_month, self.var.totalPotET_month_nonIrr,
                                      self.var.actTransTotal_month_nonIrr, self.var.actTransTotal_month_Irr,
                                      self.var.irr_crop_month):
                            total[c] = np.where(endMonth, 0., total[c])

                        # Harvest crops that are finished growing: reset month counter and KC. New seeds are sown after harvesting towards the end.
                        # todo experiment keeping flexible crop_counter, now monthCounter
                        self.var.monthCounter[c] = np.where(harvest, 0, self.var.monthCounter[c])

                        # Removing crops that been harvested
                        self.var.fracCrops_Irr[c] = np.where(self.var.monthCounter[c] > 0, self.var.fracCrops_Irr[c], 0)
                        self.var.fracCrops_nonIrr[c] = np.where(self.var.monthCounter[c] > 0,
                                                                self.var.fracCrops_nonIrr[c], 0)
                        if self.var.daily_crop_KC:
                            # day of the season per cell -> Kc of that day (the counter is a float map)
                            self.var.currentKC[c] = np.where(self.var.monthCounter[c] > 0,
                                                             np.take(self.var.Crops[c][-1], self.var.monthCounter[c].astype(int) - 1), 0)
                            for a in range(1, 4):
                                self.var.currentKY[c] = np.where(self.var.monthCounter[c] > self.var.Crops[c][a][0],
                                                                 self.var.Crops[c][a + 1][2], self.var.currentKY[c])
                        else:
                            self.var.currentKC[c] = np.where(self.var.monthCounter[c] == 0, 0, self.var.currentKC[c])
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

                        # planting day (crops in days) or planting month of the crop
                        if self.var.daily_crop_KC:
                            plantDay = self.var.Crops[c][0] == dateVar['doy']
                        else:
                            plantDay = self.var.Crops[c][0] == dateVar['currDate'].month

                        # Sowing seeds, if crop is not already growing, if there is sufficient space
                        # If it is the planting month of the crop,
                        # the crop is planted both irrigated and non-irrigated,
                        # in the remaining available land.
                        # only where the crop is activated (demand >= 1e-5): elsewhere the counter stays 0 (KC 0)
                        self.var.fracCrops_Irr[c] = np.where(
                            plantDay & (self.var.monthCounter[c] == 0),
                            np.where((remainder_land_Irr > 0) & (self.var.activatedCrops[c] > 0),
                                     np.minimum(remainder_land_Irr, self.var.fracCrops_IrrLandDemand[c]),
                                     0),
                            self.var.fracCrops_Irr[c])

                        if 'leftoverIrrigatedCropIsRainfed' in option:
                            if checkOption('leftoverIrrigatedCropIsRainfed'):
                                self.var.fracCrops_nonIrrLandDemand[c] = self.var.fracCrops_IrrLandDemand[c] - \
                                                                         self.var.fracCrops_Irr[c]

                                if 'crops_leftoverNotIrrigated' in binding:
                                    if c <= int(cbinding('crops_leftoverNotIrrigated')):
                                        self.var.fracCrops_nonIrrLandDemand[c] = globals.inZero.copy()

                        self.var.fracCrops_nonIrr[c] = np.where(
                            plantDay & (self.var.monthCounter[c] == 0),
                            np.where((remainder_land_nonIrr > 0) & (self.var.activatedCrops[c] > 0),
                                     np.minimum(remainder_land_nonIrr, self.var.fracCrops_nonIrrLandDemand[c]),
                                     0),
                            self.var.fracCrops_nonIrr[c])

                        # When it is the crop's planting month and it is not yet already planted (the month counter is zero).
                        # The counter only starts if there is some of the crop growing in the cell (it is activated).
                        # Otherwise, the month counter is kept constant
                        self.var.monthCounter[c] = np.where(
                            plantDay & (self.var.monthCounter[c] == 0),
                            self.var.activatedCrops[c], self.var.monthCounter[c])

                        if self.var.daily_crop_KC:
                            self.var.currentKC[c] = np.where(self.var.monthCounter[c] > 0,
                                                             np.take(self.var.Crops[c][-1], self.var.monthCounter[c].astype(int) - 1), 0)
                        else:
                            self.var.currentKC[c] = np.where(
                                plantDay & (self.var.monthCounter[c] == 1),
                                self.var.Crops[c][1][1],
                                self.var.currentKC[c])
                        self.var.currentKY[c] = np.where(
                            plantDay & (self.var.monthCounter[c] == 1),
                            self.var.Crops[c][1][2],
                            self.var.currentKY[c])

                # daily crops are planted and harvested on any day -> the land fractions change every day
                if dateVar['newStart'] or dateVar['currDate'].day == 1 or self.var.daily_crop_KC:

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
                    if checkOption('use_GeneralCropIrr') is True:
                        if 'GeneralCrop_Irr' not in binding:
                            msg = "Error 171: use_GeneralCropIrr = True needs the map GeneralCrop_Irr in the settings file\n"
                            raise CWATMError(msg)
                        self.var.GeneralCrop_Irr = loadmap('GeneralCrop_Irr')
                        self.var.GeneralCrop_Irr = np.minimum(self.var.fracVegCover[3] - frac_totalIrr,
                                                              self.var.GeneralCrop_Irr)

                    # Fallowing and general crop are determined automatically, and are not specific input maps.
                    else:

                        # Fallow land exists alongside general land as non-specific crop options.
                        if checkOption('activate_fallow') is True:

                            # Crop land that has been previously planted by a specific-crop is fallowed between plantings.
                            if checkOption('automaticFallowingIrr') is True:
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
                                self.var.fracAllCover - self.var.fracVegCover[4] - self.var.fracVegCover[3] -
                                self.var.fracVegCover[5] - self.var.fracVegCover[2] - self.var.fracVegCover[0],
                                globals.inZero.copy())

                            self.var.fracVegCover[1] = remainderLand.copy()

                            # keep the water of the land cover stores (net change of both moves of the day)
                            self.model.landcoverType_module.moveLandcoverStorage(fracOld)


                    if checkOption('use_GeneralCropnonIrr') is True:
                        if 'GeneralCrop_nonIrr' not in binding:
                            msg = "Error 172: use_GeneralCropnonIrr = True needs the map GeneralCrop_nonIrr in the settings file\n"
                            raise CWATMError(msg)
                        self.var.GeneralCrop_nonIrr = loadmap('GeneralCrop_nonIrr')
                        self.var.GeneralCrop_nonIrr = np.minimum(self.var.fracVegCover[1] - frac_totalnonIrr,
                                                                 self.var.GeneralCrop_nonIrr)

                    else:
                        if checkOption('activate_fallow') is True:
                            # as for irrigated land: land planted before is fallowed between plantings
                            # (automaticFallowingNonIrr, default True if not in the settings), otherwise no general
                            # crop: only specific crops and fallow land
                            if 'automaticFallowingNonIrr' not in option or checkOption('automaticFallowingNonIrr'):
                                self.var.GeneralCrop_nonIrr = self.var.generalnonIrrCrop_max.copy()
                            else:
                                self.var.GeneralCrop_nonIrr = globals.inZero.copy()
                        else:
                            self.var.GeneralCrop_nonIrr = self.var.fracVegCover[1] - self.var.frac_totalnonIrr

                    self.var.fallownonIrr = self.var.fracVegCover[1] - (
                            self.var.frac_totalnonIrr + self.var.GeneralCrop_nonIrr)
                    self.var.fallownonIrr_max = np.maximum(self.var.fallownonIrr, self.var.fallownonIrr_max)

                    self.var.availableArableLand = self.var.fallowIrr + self.var.fracVegCover[1] - frac_totalnonIrr

            if No == 1:

                self.var.weighted_KC_nonIrr = self.var.GeneralCrop_nonIrr * cropKC_landCover
                # crops without area in any cell add only 0 and are skipped
                for c in np.flatnonzero(np.any(self.var.fracCrops_nonIrr != 0, axis=1)):
                    self.var.weighted_KC_nonIrr += self.var.fracCrops_nonIrr[c] * self.var.currentKC[c]
                self.var.weighted_KC_nonIrr_woFallow = self.var.weighted_KC_nonIrr.copy()

                self.var.weighted_KC_nonIrr += self.var.fallownonIrr * self.var.minCropKC
                self.var.weighted_KC_nonIrr = np.where(self.var.fracVegCover[1] > 0,
                                                       self.var.weighted_KC_nonIrr / self.var.fracVegCover[1], 0)
                self.var.cropKC[1] = self.var.weighted_KC_nonIrr.copy()

            if No == 3:

                # crops without irrigated area in any cell add only 0 and are skipped
                presentIrr = np.flatnonzero(np.any(self.var.fracCrops_Irr != 0, axis=1))

                self.var.weighted_KC_Irr = self.var.GeneralCrop_Irr * cropKC_landCover
                for c in presentIrr:
                    self.var.weighted_KC_Irr += self.var.fracCrops_Irr[c] * self.var.currentKC[c]
                self.var.weighted_KC_Irr_woFallow_fullKc = self.var.weighted_KC_Irr.copy()

                self.var.weighted_KC_Irr += self.var.fallowIrr * self.var.minCropKC
                self.var.weighted_KC_Irr = np.where(self.var.fracVegCover[3] > 0,
                                                    self.var.weighted_KC_Irr / self.var.fracVegCover[3], 0)
                self.var.cropKC[3] = self.var.weighted_KC_Irr.copy()

                self.var._weighted_KC_Irr = self.var.GeneralCrop_Irr * (cropKC_landCover - self.var.minCropKC)
                for c in presentIrr:
                    self.var._weighted_KC_Irr += self.var.fracCrops_Irr[c] * (self.var.currentKC[c]-self.var.minCropKC)
                self.var.weighted_KC_Irr_woFallow = self.var._weighted_KC_Irr.copy()
                
        # without crops
        # calculate potential ET
        ##  self.var.totalPotET total potential evapotranspiration for a reference crop for a land cover class [m]
        # correction factor of the land cover (once, used for the crops below too)
        correctKC = self.var.cropCorrect * self.var.crop_correct_landCover[No]
        self.var.totalPotET[No] = correctKC * self.var.cropKC[No] * self.var.ETRef

        # potTranspiration: Transpiration for each land cover class
        # uses bare soil evaporation before the reduction by snow: snow must not increase potential transpiration
        # snow evaporation + (snow reduced) bare soil evaporation can be bigger than the bare soil part
        # -> the overflow is taken from transpiration, so actual ET cannot be bigger than potential ET
        # the same for all land covers: computed once per day (land cover 0 is always the first)
        if No == 0:
            self.budgetBareSoilSnow = np.maximum(self.var.potBareSoilEvapNoSnow,
                                                 self.var.potBareSoilEvap + self.var.snowEvap)
        self.var.potTranspiration[No] = np.maximum(0., self.var.totalPotET[No] - self.budgetBareSoilSnow)

        # checkOption('includeCrops') and checkOption('includeCropSpecificWaterUse')
        if self.var.includeCrops:

            # potential ET of the rainfed crops (on grassland: correction factor of grassland), all crops at once
            if No == 1:
                self.var.PotET_crop_nonIrr[:] = correctKC * self.var.currentKC * self.var.ETRef
                self.var.totalPotET_month_nonIrr += self.var.PotET_crop_nonIrr

            # once per day at the last land cover with crops: 3 (non-paddy) with irrigation, else 1 (grassland)
            # without irrigation dynamic is not called for 2 and 3
            if No == (3 if checkOption('includeIrrigation') else 1):

                # potential ET of the irrigated crops (on non-paddy: correction factor of non-paddy)
                if No == 3:
                    self.var.PotET_crop[:] = correctKC * self.var.currentKC * self.var.ETRef
                    self.var.totalPotET_month += self.var.PotET_crop

                # variables only for the output: computed only if they are in the output settings
                if not hasattr(self, 'outputNames'):
                    from cwatm.management_modules.globals import outMap, outTss
                    # entries are variable names, or after output.initial lists [file, variable name, ...]
                    self.outputNames = {str(e[1] if isinstance(e, list) else e).split('[')[0].strip()
                                        for names in list(outMap.values()) + list(outTss.values()) for e in names}
                out = self.outputNames

                # named crop maps
                for c in range(len(self.var.Crops)):
                    cropName = self.var.Crops_names[c]
                    if cropName + '_Irr' in out:
                        vars(self.var)[cropName + '_Irr'] = self.var.fracCrops_Irr[c].copy()
                    if cropName + '_nonIrr' in out:
                        vars(self.var)[cropName + '_nonIrr'] = self.var.fracCrops_nonIrr[c].copy()

                # sums per admin segment; areas only when the fractions can change (start, 1st of the month,
                # crops in days: every day; the land cover maps change on 1 January)
                if 'adminSegments' in binding:
                    segIndex = self.var.adminSegmentsIndex
                    fracChange = dateVar['newStart'] or dateVar['currDate'].day == 1 or self.var.daily_crop_KC
                    for c in range(len(self.var.Crops)):
                        if 'totalPotET_month_segment' in out:
                            self.var.totalPotET_month_segment[c] = segIndex.average(self.var.totalPotET_month[c])
                        if 'PotETaverage_crop_segments' in out:
                            self.var.PotETaverage_crop_segments[c] = segIndex.average(self.var.PotET_crop[c])
                        if fracChange and 'areaCrops_Irr_segment' in out:
                            self.var.areaCrops_Irr_segment[c] = segIndex.total(
                                self.var.fracCrops_Irr[c] * self.var.cellArea)
                        if fracChange and 'areaCrops_nonIrr_segment' in out:
                            self.var.areaCrops_nonIrr_segment[c] = segIndex.total(
                                self.var.fracCrops_nonIrr[c] * self.var.cellArea)

                    if fracChange and 'areaPaddy_Irr_segment' in out:
                        self.var.areaPaddy_Irr_segment = segIndex.total(self.var.fracVegCover[2] * self.var.cellArea)
                    if 'Precipitation_segment' in out:
                        self.var.Precipitation_segment = segIndex.total(self.var.Precipitation * self.var.cellArea)
                    if fracChange and 'availableArableLand_segment' in out:
                        self.var.availableArableLand_segment = segIndex.total(
                            self.var.availableArableLand * self.var.cellArea)
