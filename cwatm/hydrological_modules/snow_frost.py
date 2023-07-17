# -------------------------------------------------------------------------
# Name:        Snow module
# Purpose:
#
# Author:      PB
#
# Created:     13/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


class snow_frost(object):

    """
    RAIN AND SNOW

    Domain: snow calculations evaluated for center points of up to 7 sub-pixel
    snow zones 1 -7 which each occupy a part of the pixel surface

    Variables *snow* and *rain* at end of this module are the pixel-average snowfall and rain


    **Global variables**

    =====================================  ======================================================================  =====
    Variable [self.var]                    Description                                                             Unit 
    =====================================  ======================================================================  =====
    load_initial                           Settings initLoad holds initial conditions for variables                input
    fracGlacierCover                                                                                               --   
    DtDay                                  seconds in a timestep (default=86400)                                   s    
    Precipitation                          Precipitation (input for the model)                                     m    
    Tavg                                   Input, average air Temperature                                          K    
    SnowMelt                               total snow melt from all layers                                         m    
    Rain                                   Precipitation less snow                                                 m    
    prevSnowCover                          snow cover of previous day (only for water balance)                     m    
    SnowCover                              snow cover (sum over all layers)                                        m    
    ElevationStD                                                                                                   --   
    numberSnowLayersFloat                                                                                          --   
    numberSnowLayers                       Number of snow layers (up to 10)                                        --   
    glaciertransportZone                   Number of layers which can be mimiced as glacier transport zone         --   
    deltaInvNorm                           Quantile of the normal distribution (for different numbers of snow lay  --   
    frac_snow_redistribution                                                                                       --   
    DeltaTSnow                             Temperature lapse rate x std. deviation of elevation                    °C   
    SnowDayDegrees                         day of the year to degrees: 360/365.25 = 0.9856                         --   
    SeasonalSnowMeltSin                                                                                            --   
    excludeGlacierArea                                                                                             --   
    summerSeasonStart                      day when summer season starts = 165                                     --   
    IceDayDegrees                          days of summer (15th June-15th Sept.) to degree: 180/(259-165)          --   
    SnowSeason                             seasonal melt factor                                                    m (Ce
    TempSnowLow                            Temperature below which all precipitation is snow                       °C   
    TempSnowHigh                           Temperature above which all precipitation is rain                       °C   
    TempSnow                               Average temperature at which snow melts                                 °C   
    SnowFactor                             Multiplier applied to precipitation that falls as snow                  --   
    SnowMeltCoef                           Snow melt coefficient - default: 0.004                                  --   
    IceMeltCoef                            Ice melt coefficnet - default  0.007                                    --   
    TempMelt                               Average temperature at which snow melts                                 °C   
    SnowCoverS                             snow cover for each layer                                               m    
    Kfrost                                 Snow depth reduction coefficient, (HH, p. 7.28)                         m-1  
    Afrost                                 Daily decay coefficient, (Handbook of Hydrology, p. 7.28)               --   
    FrostIndexThreshold                    Degree Days Frost Threshold (stops infiltration, percolation and capil  --   
    SnowWaterEquivalent                    Snow water equivalent, (based on snow density of 450 kg/m3) (e.g. Tarb  --   
    FrostIndex                             FrostIndex - Molnau and Bissel (1983), A Continuous Frozen Ground Inde  --   
    extfrostindex                          Flag for second frostindex                                              --   
    FrostIndexThreshold2                   FrostIndex2 - Molnau and Bissel (1983), A Continuous Frozen Ground Ind  --   
    frostInd1                              forstindex 1                                                            --   
    frostInd2                              frostindex 2                                                            --   
    frostindexS                            array for frostindex                                                    --   
    Snow                                   Snow (equal to a part of Precipitation)                                 m    
    snow_redistributed_previous                                                                                    --   
    SnowM1                                                                                                         --   
    IceM1                                                                                                          --   
    fracVegCover                           Fraction of specific land covers (0=forest, 1=grasslands, etc.)         %    
    =====================================  ======================================================================  =====

    **Functions**
    """


    def __init__(self, model):
        self.var = model.var
        self.model = model


    def initial(self):
        """
        Initial part of the snow and frost module

        * loads all the parameters for the day-degree approach for rain, snow and snowmelt
        * loads the parameter for frost
        """

        self.var.numberSnowLayersFloat = loadmap('NumberSnowLayers')    # default 3
        self.var.numberSnowLayers = int(self.var.numberSnowLayersFloat)
        self.var.glaciertransportZone = int(loadmap('GlacierTransportZone'))  # default 1 -> highest zone is transported to middle zone

        # Difference between (average) air temperature at average elevation of
        # pixel and centers of upper- and lower elevation zones [deg C]
        # ElevationStD:   Standard Deviation of the DEM
        # 0.9674:    Quantile of the normal distribution: u(0,833)=0.9674 to split the pixel in 3 equal parts.
        # for different number of layers
        #  Number: 2 ,3, 4, 5, 6, 7, ,8, 9, 10
        dn = {}
        dn[1] = np.array([0])
        dn[2] = np.array([-0.67448975,  0.67448975])
        dn[3] = np.array([-0.96742157,  0.,  0.96742157])
        dn[5] = np.array([-1.28155157, -0.52440051,  0.,  0.52440051,  1.28155157])
        dn[7] = np.array([-1.46523379, -0.79163861, -0.36610636, 0., 0.36610636,0.79163861, 1.46523379])
        dn[9] = np.array([-1.59321882, -0.96742157, -0.5894558 , -0.28221615,  0., 0.28221615,  0.5894558 ,  0.96742157,  1.59321882])
        dn[10] = np.array([-1.64485363, -1.03643339, -0.67448975, -0.38532047, -0.12566135, 0.12566135,  0.38532047,  0.67448975,  1.03643339,  1.64485363])

        #divNo = 1./float(self.var.numberSnowLayers)
        #deltaNorm = np.linspace(divNo/2, 1-divNo/2, self.var.numberSnowLayers)
        #self.var.deltaInvNorm = norm.ppf(deltaNorm)
        self.var.deltaInvNorm = dn[self.var.numberSnowLayers]


        self.var.ElevationStD = loadmap('ElevationStD')

        #self.var.ElevationMin = loadmap('Elevation')
        #self.var.ElevationMean = loadmap('Elevation_avg')

        # max_frac_snow_redistriution = 0.5
        # max_ELevationStD = 1500
        min_ElevationStD_snow_redistr = 100
        # 0.46 is the maximum fraction that can be redistributed if snow density is assumed to be 350kg/m3 according to eq. 13 in Frey & Holzmann (2015)
        # this fraction has to be multiplied with the slope, highest slope is 90 degrees
        # the mean slope of each grid cell is the mean of all slopes of the 3'' SRTM DEM
        # the maximum fraction that can be redistributed if snow density is assumed to be 200kg/m3 according to eq. 13 in Frey & Holzmann (2015) is 0.35
        slope_degrees = np.degrees(np.arctan(loadmap('tanslope')))
        self.var.frac_snow_redistribution = np.maximum(0.35 * slope_degrees / 90, globals.inZero)
        self.var.DeltaTSnow = self.var.ElevationStD * loadmap('TemperatureLapseRate')

        self.var.SnowDayDegrees = 0.9856
        #to get the seasonal cycle in snow melt coefficient, value is 81 (263) for northern (southern) hemisphere
        if 'SeasonalSnowMeltSin' in binding:
            self.var.SeasonalSnowMeltSin = loadmap('SeasonalSnowMeltSin')

        self.var.excludeGlacierArea = False
        if "excludeGlacierArea" in option:
            self.var.excludeGlacierArea = checkOption('excludeGlacierArea')

        # day of the year to degrees: 360/365.25 = 0.9856
        self.var.summerSeasonStart = 165
        #self.var.IceDayDegrees = 1.915
        self.var.IceDayDegrees = 180./(259- self.var.summerSeasonStart)
        # days of summer (15th June-15th Sept.) to degree: 180/(259-165)
        self.var.SnowSeason = loadmap('SnowSeasonAdj') * 0.5
        # default value of range  of seasonal melt factor is set to 0.001 m C-1 day-1
        # 0.5 x range of sinus function [-1,1]
        if 'TempSnowLow' in binding:
            self.var.TempSnowLow = loadmap('TempSnowLow')
            self.var.TempSnowHigh = loadmap('TempSnowHigh')
        else:
            self.var.TempSnow = loadmap('TempSnow')
        self.var.SnowFactor = loadmap('SnowFactor')
        self.var.SnowMeltCoef = loadmap('SnowMeltCoef')
        self.var.IceMeltCoef = loadmap('IceMeltCoef')

        self.var.TempMelt = loadmap('TempMelt')

        # initialize as many snow covers as snow layers -> read them as SnowCover1 , SnowCover2 ...
        # SnowCover1 is the highest zone
        self.var.SnowCoverS = []
        for i in range(self.var.numberSnowLayers):
            self.var.SnowCoverS.append(self.var.load_initial("SnowCover",number = i+1))

        # initial snow depth in elevation zones A, B, and C, respectively  [mm]
        self.var.SnowCover = np.sum(self.var.SnowCoverS,axis=0) / self.var.numberSnowLayersFloat + globals.inZero


        # Pixel-average initial snow cover: average of values in 3 elevation
        # zones

        # ---------------------------------------------------------------------------------
        # Initial part of frost index

        self.var.Kfrost = loadmap('Kfrost')
        self.var.Afrost = loadmap('Afrost')
        self.var.FrostIndexThreshold = loadmap('FrostIndexThreshold')
        self.var.SnowWaterEquivalent = loadmap('SnowWaterEquivalent')

        self.var.FrostIndex = self.var.load_initial('FrostIndex')

    # --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Dynamic part of the snow module

        Distinguish between rain/snow and calculates snow melt and glacier melt
        The equation is a modification of:

        References:
            Speers, D.D., Versteeg, J.D. (1979) Runoff forecasting for reservoir operations - the pastand the future. In: Proceedings 52nd Western Snow Conference, 149-156

        Frost index in soil [degree days] based on:

        References:
            Molnau and Bissel (1983, A Continuous Frozen Ground Index for Flood Forecasting. In: Maidment, Handbook of Hydrology, p. 7.28, 7.55)
        """
        if checkOption('calcWaterBalance'):
            self.var.prevSnowCover = self.var.SnowCover.copy()
        # sinus shaped function between the
        # annual minimum (December 21st) and annual maximum (June 21st) for the northern hemisphere
        # annual maximum (December 21st) and annual minimum (June 21st) for the northern hemisphere
        if 'SeasonalSnowMeltSin' in binding:
            SnowMeltCycle = np.sin(np.radians((dateVar['doy'] - self.var.SeasonalSnowMeltSin)
                                    * self.var.SnowDayDegrees))
            SeasSnowMeltCoef = self.var.SnowSeason * SnowMeltCycle + self.var.SnowMeltCoef

            # IceMelt is adjusted to account for southern hemisphere
            # for northern hemisphere Icemelt can occur between doy 166 and doy 256
            # for southern hemisphere Icemelt can occur between doy 348 and doy 73
            # amplitude and curve shape are the same

            SummerSeason = np.sin(
                math.radians((dateVar['doy'] - self.var.summerSeasonStart) * self.var.SnowDayDegrees * 2))

            SummerSeason = np.where(SummerSeason < 0 or SnowMeltCycle < 0, globals.inZero, SummerSeason)

        else:
            SeasSnowMeltCoef = self.var.SnowSeason * np.sin(math.radians((dateVar['doy'] - 81)
                                                                         * self.var.SnowDayDegrees)) + self.var.SnowMeltCoef
            if (dateVar['doy'] > self.var.summerSeasonStart) and (dateVar['doy'] < 260):
                SummerSeason = np.sin(math.radians((dateVar['doy'] - self.var.summerSeasonStart) * self.var.IceDayDegrees))
            else:
                SummerSeason = 0.0

        self.var.Snow = globals.inZero.copy()
        self.var.Rain = globals.inZero.copy()
        self.var.SnowMelt = globals.inZero.copy()
        self.var.IceMelt = globals.inZero.copy()
        self.var.SnowCover = globals.inZero.copy()
        self.var.snow_redistributed_previous = globals.inZero.copy()

        # snow melt potential is collected from up the mountain towards valley
        snowIceM_surplus = globals.inZero.copy()
        # snow cover fraction of a gridcell
        self.var.SnowFraction = globals.inZero.copy()

        #get number of elevation zones with forest
        #assume forest is most present at lowest location
        nr_frac_forest = self.var.numberSnowLayers - np.round(self.var.fracVegCover[0] / (1 / self.var.numberSnowLayers)) - 1
        if self.var.excludeGlacierArea:
            current_fracGlacierCover = self.var.fracGlacierCover.copy() #percentage area of each layer
            # elev_red = 5
            # current_fracGlacierCover = self.var.fracGlacierCover / elev_red
        #substract glacier area from highest areas
        #loops through snow layers from highest to lowest
        #the capacity depends on the fraction of forest or grassland
        #self.var.SnowCoverSCapacity[i]

        for i in range(self.var.numberSnowLayers):
            TavgS = self.var.Tavg + self.var.DeltaTSnow * self.var.deltaInvNorm[i]
            # Temperature at center of each zone (temperature at zone B equals Tavg)
            # i=0 -> highest zone
            # i=2 -> lower zone
            if 'TempSnowLow' in binding:
                #fraction of solid precipitation maximum 1, minimum 0
                frac_solid = np.clip(1 - (TavgS - self.var.TempSnowLow) / (self.var.TempSnowHigh - self.var.TempSnowLow), 0, 1)
                SnowS = frac_solid * self.var.SnowFactor * self.var.Precipitation
                RainS = (1 - frac_solid) * self.var.Precipitation
            else:
                SnowS = np.where(TavgS < self.var.TempSnow, self.var.SnowFactor * self.var.Precipitation,
                                 globals.inZero)
                # Precipitation is assumed to be snow if daily average temperature is below TempSnow
                # Snow is multiplied by correction factor to account for undercatch of
                # snow precipitation (which is common)
                RainS = np.where(TavgS >= self.var.TempSnow, self.var.Precipitation, globals.inZero)

            #if SWE higher than 1m it is assumed that this is unrealistic, therefore it will be melted faster to avoid
            #snow accumulation (similar to implementation in WaterGAP)
            """
            if np.any(self.var.SnowCoverS[i] >= 1):
                # the temperature of the lowest elevation zone is used for melting
                # this will result in an increase in temp for every elevation zone in the grid cell
                # this change in temp will only become relevant if T > TempMelt
                TavgHighSWE = self.var.Tavg + self.var.DeltaTSnow * self.var.deltaInvNorm[-1]
                SnowMeltNormal = (TavgS - self.var.TempMelt) * SeasSnowMeltCoef * (1 + 0.01 * RainS) * self.var.DtDay
                SnowMeltHighSWE = (TavgHighSWE - self.var.TempMelt) * SeasSnowMeltCoef * (1 + 0.01 * RainS) * self.var.DtDay
                SnowMeltS = np.where(self.var.SnowCoverS[i] < 1, SnowMeltNormal, SnowMeltHighSWE)
            else:
            """

            SnowMeltS = (TavgS - self.var.TempMelt) * SeasSnowMeltCoef * (1 + 0.01 * RainS) * self.var.DtDay
            SnowMeltS = np.maximum(SnowMeltS, globals.inZero)

            # for which layer the ice melt is calculated with the middle temp.
            # for the others it is calculated with the corrected temp
            # this is to mimic glacier transport to lower zones
            if i <= self.var.glaciertransportZone:
                IceMeltS = self.var.Tavg * self.var.IceMeltCoef * self.var.DtDay * SummerSeason
                # if i = 0 and 1 -> higher and middle zone
                # Ice melt coeff in m/C/deg
            else:
                IceMeltS = TavgS * self.var.IceMeltCoef * self.var.DtDay * SummerSeason

            # Check snowcover and snowmelt
            IceMeltS = np.maximum(IceMeltS, globals.inZero)

            SnowIceMeltS = np.maximum(np.minimum(SnowMeltS + IceMeltS + snowIceM_surplus, self.var.SnowCoverS[i]), globals.inZero)

            # snowIceM_surplus: each elevation band snow melt potential is collected -> one way to melt additianl snow which might
            # be colleted in the valley because of snow retribution
            snowIceM_surplus = np.abs(np.minimum(self.var.SnowCoverS[i] - (SnowMeltS + IceMeltS + snowIceM_surplus),0))

            IceMeltS = np.maximum(SnowIceMeltS - SnowMeltS, globals.inZero)
            SnowMeltS = np.maximum(SnowIceMeltS - IceMeltS, globals.inZero)
            # check if snow+ice not bigger than snowcover
            self.var.SnowCoverS[i] = self.var.SnowCoverS[i] + SnowS - SnowIceMeltS

            # snow redistribution inspired by Frey and Holzmann (2015) doi:10.5194/hess-19-4517-2015
            # if snow cover higher than snow holding capacity redistribution
            # get the thresholds for the snow based on the snow density and snow depth values in Frey and Holzmann (2015)
            # capacity of forest 2.5m snow cover, assumed snow density 250kg/m3: 0.25 * 1000 * 2.5 / 1000
            # capacity of other land cover 0.25m snow cover, assumed snow density 250kg/m3: 0.25 * 1000 * 0.25 / 1000
            # but only for cells with std above 100m
            swe_forest = 0.625
            swe_other = 0.2
            # snow capacity depends on whether there is frost cover in the elevation zone
            snowcapacity = np.where(i <= nr_frac_forest, swe_other, swe_forest)
            # where snow cover is higher than capacity, a fraction of snow will be redistributed

            # reduction factor at lowest level no snow_retri, increasing to factor 0.9 at highest level
            reduction_factor = 1.0 * (1 - (i + 1) / self.var.numberSnowLayers)
            snow_redistributed = np.where(self.var.SnowCoverS[i] > snowcapacity,
                    self.var.frac_snow_redistribution * self.var.SnowCoverS[i] * reduction_factor, 0)
            # the lowest elevation zone cannot redistribute snow -> this is replaced by reduction_factor = 0 in the lowest elevation band
            #if i == self.var.numberSnowLayers - 1:
            #    snow_redistributed = globals.inZero.copy()

            snow_redistributed = np.maximum(snow_redistributed, globals.inZero)
            # the current snow cover will be reduced by the amount of snow that is redistributed
            # the redistributed snow from higher elevation zone will be added
            self.var.SnowCoverS[i] = self.var.SnowCoverS[i] - snow_redistributed + self.var.snow_redistributed_previous
            # redistributed snow will be added to next elevation zone in next loop
            self.var.snow_redistributed_previous = snow_redistributed.copy()

            # calculation of snow fraction in each elevation band
            # =< 0.02 SnowCoverS -> no snow
            sfrac = np.where(self.var.SnowCoverS[i] > 0.02,0.25,0)
            sfrac = np.where(self.var.SnowCoverS[i] > 0.05, 0.5,sfrac)
            sfrac = np.where(self.var.SnowCoverS[i] > 0.10, 1.0, sfrac)

            self.var.SnowFraction += sfrac / self.var.numberSnowLayers

            # here outputs are just summed up because equal distribution across elevation zones
            # when glaciers are included the higher elevations should play less of a role
            if self.var.excludeGlacierArea:
                # the weight is the fraction of current elevation zone that is not covered by glacier
                # the glacier is subtracted from the highest elevation zone first
                weight = 1 / self.var.numberSnowLayers - current_fracGlacierCover
                # the fraction of glacier cover is decreased by fraction that is covered by glacier in current elevation zone
                current_fracGlacierCover = np.where(weight > 0, 0, abs(weight))
                #weight below zero is set to zero
                weight[weight < 0] = 0
                assert (weight >= 0).all()
                self.var.Snow += SnowS * weight
                self.var.Rain += RainS * weight
                self.var.SnowMelt += SnowMeltS * weight
                self.var.IceMelt += IceMeltS * weight
                self.var.SnowCover += self.var.SnowCoverS[i] * weight

            else:
                self.var.Snow += SnowS
                self.var.Rain += RainS
                self.var.SnowMelt += SnowMeltS
                self.var.IceMelt += IceMeltS
                self.var.SnowCover += self.var.SnowCoverS[i]

        if not self.var.excludeGlacierArea:
            self.var.Snow /= self.var.numberSnowLayersFloat
            self.var.Rain /= self.var.numberSnowLayersFloat
            self.var.SnowMelt /= self.var.numberSnowLayersFloat
            self.var.IceMelt /= self.var.numberSnowLayersFloat
            self.var.SnowCover /= self.var.numberSnowLayersFloat

        # all in pixel

        # DEBUG Snow
        if checkOption('calcWaterBalance'):
            self.model.waterbalance_module.waterBalanceCheck(
                [self.var.Snow],  # In
                [self.var.SnowMelt, self.var.IceMelt],  # Out
                [self.var.prevSnowCover],   # prev storage
                [self.var.SnowCover],
                "Snow1", False)

        # ---------------------------------------------------------------------------------
        # Dynamic part of frost index
        self.var.Kfrost = np.where(self.var.Tavg < 0, 0.08, 0.5)
        FrostIndexChangeRate = -(1 - self.var.Afrost) * self.var.FrostIndex - self.var.Tavg * \
            np.exp(-0.4 * 100 * self.var.Kfrost * np.minimum(1.0,self.var.SnowCover / self.var.SnowWaterEquivalent))
        # Rate of change of frost index (expressed as rate, [degree days/day])
        self.var.FrostIndex = np.maximum(self.var.FrostIndex + FrostIndexChangeRate * self.var.DtDay, 0)
        # frost index in soil [degree days] based on Molnau and Bissel (1983, A Continuous Frozen Ground Index for Flood
        # Forecasting. In: Maidment, Handbook of Hydrology, p. 7.28, 7.55)
        # if Tavg is above zero, FrostIndex will stay 0
        # if Tavg is negative, FrostIndex will increase with 1 per degree C per day
        # Exponent of 0.04 (instead of 0.4 in HoH): conversion [cm] to [mm]!  -> from cm to m HERE -> 100 * 0.4
        # maximum snowlayer = 1.0 m
        # Division by SnowDensity because SnowDepth is expressed as equivalent water depth(always less than depth of snow pack)
        # SnowWaterEquivalent taken as 0.45
        # Afrost, (daily decay coefficient) is taken as 0.97 (Handbook of Hydrology, p. 7.28)
        # Kfrost, (snow depth reduction coefficient) is taken as 0.57 [1/cm], (HH, p. 7.28) -> from Molnau taken as 0.5 for t> 0 and 0.08 for T<0




