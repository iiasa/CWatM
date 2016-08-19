# -------------------------------------------------------------------------
# Name:        Snow module
# Purpose:
#
# Author:      PB
#
# Created:     13/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class snow(object):

    """
    # ************************************************************
    # ***** RAIN AND SNOW *****************************************
    # ************************************************************

    # Domain: snow calculations evaluated for center points of 3 sub-pixel
    # snow zones A, B, and C, which each occupy one-third of the pixel surface
    #
    # Variables 'snow' and 'rain' at end of this module are the pixel-average snowfall and rain
    #
    # Zone A: lower third
    # Zone B: center third
    # Zone C: upper third
    """

    def __init__(self, snow_variable):
        self.var = snow_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the snow and frost module
        """
        self.var.TotalPrecipitation = globals.inZero.copy()
        self.var.DeltaTSnow = 0.9674 * loadmap('ElevationStD') * loadmap('TemperatureLapseRate')

        # Difference between (average) air temperature at average elevation of
        # pixel and centers of upper- and lower elevation zones [deg C]
        # ElevationStD:   Standard Deviation of the DEM from Bodis (2009)
        # 0.9674:    Quantile of the normal distribution: u(0,833)=0.9674
        #              to split the pixel in 3 equal parts.
        self.var.SnowDayDegrees = 0.9856
        # day of the year to degrees: 360/365.25 = 0.9856

        self.var.IceDayDegrees = 1.915
        # days of summer (15th June-15th Sept.) to degree: 180/(259-165)
        self.var.SnowSeason = loadmap('SnowSeasonAdj') * 0.5
        # default value of range  of seasonal melt factor is set to 1
        # 0.5 x range of sinus function [-1,1]
        self.var.TempSnow = loadmap('TempSnow')
        self.var.SnowFactor = loadmap('SnowFactor')
        self.var.SnowMeltCoef = loadmap('SnowMeltCoef')
        self.var.TempMelt = loadmap('TempMelt')

        #SnowCover1 = loadmap('SnowCover1Ini')
        SnowCover1 = self.var.init_module.load_initial('SnowCover1')
        SnowCover2 = self.var.init_module.load_initial('SnowCover2')
        SnowCover3 = self.var.init_module.load_initial('SnowCover3')
        #self.var.init_module.load_initial('SnowCover1')
        self.var.SnowCoverS = [SnowCover1, SnowCover2, SnowCover3]

        # initial snow depth in elevation zones A, B, and C, respectively  [mm]
        self.var.SnowCoverInit = (SnowCover1 + SnowCover2 + SnowCover3) / 3
        # Pixel-average initial snow cover: average of values in 3 elevation
        # zones

        # ---------------------------------------------------------------------------------
        # Initial part of frost index

        self.var.Kfrost = loadmap('Kfrost')
        self.var.Afrost = loadmap('Afrost')
        self.var.FrostIndexThreshold = loadmap('FrostIndexThreshold')
        self.var.SnowWaterEquivalent = loadmap('SnowWaterEquivalent')

        # FrostIndexInit=ifthen(defined(self.var.MaskMap),scalar(loadmap('FrostIndexInitValue')))

        #self.var.FrostIndex = loadmap('FrostIndexIni')
        self.var.FrostIndex = self.var.init_module.load_initial('FrostIndex')





    # --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the snow module
        """

        SeasSnowMeltCoef = self.var.SnowSeason * np.sin(math.radians((dateVar['doy'] - 81)
                                * self.var.SnowDayDegrees)) + self.var.SnowMeltCoef

        # SeasSnowMeltCoef = SnowSeason * sin((dateVar['doy']-81)* SnowDayDegrees) + SnowMeltCoef;

        # sinus shaped function between the
        # annual minimum (December 21st) and annual maximum (June 21st)
        # SummerSeason = ifthenelse(dateVar['doy'] > 165,np.sin((dateVar['doy']-165)* self.var.IceDayDegrees ),scalar(0.0))
        # SummerSeason = ifthenelse(dateVar['doy'] > 259,0.0,SummerSeason)
        if (dateVar['doy'] > 165) and (dateVar['doy'] < 260):
            SummerSeason = np.sin(math.radians((dateVar['doy'] - 165) * self.var.IceDayDegrees))
        else:
            SummerSeason = 0.0

        self.var.Snow = globals.inZero.copy()
        self.var.Rain = globals.inZero.copy()
        self.var.SnowMelt = globals.inZero.copy()
        self.var.SnowCover = globals.inZero.copy()

        for i in xrange(3):
            TavgS = self.var.Tavg + self.var.DeltaTSnow * (i - 1)
            # Temperature at center of each zone (temperature at zone B equals Tavg)
            # i=0 -> highest zone
            # i=2 -> lower zone
            SnowS = np.where(TavgS < self.var.TempSnow, self.var.SnowFactor * self.var.Precipitation, globals.inZero)
            # Precipitation is assumed to be snow if daily average temperature is below TempSnow
            # Snow is multiplied by correction factor to account for undercatch of
            # snow precipitation (which is common)
            RainS = np.where(TavgS >= self.var.TempSnow, self.var.Precipitation, globals.inZero)
            # if it's snowing then no rain
            SnowMeltS = (TavgS - self.var.TempMelt) * SeasSnowMeltCoef * (1 + 0.01 * RainS) * self.var.DtDay

            if i < 2:
                IceMeltS = self.var.Tavg * 7.0 * self.var.DtDay * SummerSeason
                # if i = 0 and 1 -> higher and middle zone
            else:
                IceMeltS = TavgS * 7.0 * self.var.DtDay * SummerSeason

            SnowMeltS = np.maximum(np.minimum(SnowMeltS + IceMeltS, self.var.SnowCoverS[i]), globals.inZero)
            self.var.SnowCoverS[i] = self.var.SnowCoverS[i] + SnowS - SnowMeltS
            self.var.Snow += SnowS
            self.var.Rain += RainS
            self.var.SnowMelt += SnowMeltS
            self.var.SnowCover += self.var.SnowCoverS[i]

        self.var.Snow /= 3
        self.var.Rain /= 3
        self.var.SnowMelt /= 3
        self.var.SnowCover /= 3
        # all in pixel [mm]


        #map = decompress( self.var.TotalPrecipitation)
        #report(map, 'C:\work\output\out3.map')

        # ---------------------------------------------------------------------------------
        # Dynamic part of frost index

        FrostIndexChangeRate = -(1 - self.var.Afrost) * self.var.FrostIndex - self.var.Tavg * \
            np.exp(-0.04 * self.var.Kfrost * self.var.SnowCover / self.var.SnowWaterEquivalent)
        # FrostIndexChangeRate=self.var.AfrostIndex - self.var.Tavg*      pcraster.exp(self.var.Kfrost*self.var.SnowCover*self.var.InvSnowWaterEquivalent)
        # Rate of change of frost index (expressed as rate, [degree days/day])
        self.var.FrostIndex = np.maximum(self.var.FrostIndex + FrostIndexChangeRate * self.var.DtDay, 0)
        # frost index in soil [degree days] based on Molnau and Bissel (1983, A Continuous Frozen Ground Index for Flood
        # Forecasting. In: Maidment, Handbook of Hydrology, p. 7.28, 7.55)
        # if Tavg is above zero, FrostIndex will stay 0
        # if Tavg is negative, FrostIndex will increase with 1 per degree C per day
        # Exponent of 0.04 (instead of 0.4 in HoH): conversion [cm] to [mm]!
        # Division by SnowDensity because SnowDepth is expressed as equivalent water depth(always less than depth of snow pack)
        # SnowWaterEquivalent taken as 0.100 (based on density of 100 kg/m3) (Handbook of Hydrology, p. 7.5)
        # Afrost, (daily decay coefficient) is taken as 0.97 (Handbook of Hydrology, p. 7.28)
        # Kfrost, (snow depth reduction coefficient) is taken as 0.57 [1/cm], (HH, p. 7.28)

