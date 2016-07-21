# -------------------------------------------------------------------------
# Name:        Soil module
# Purpose:
#
# Author:      PB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class soil(object):

    """
    # ************************************************************
    # ***** SOIL *****************************************
    # ************************************************************
    """

    def __init__(self, soil_variable):
        self.var = soil_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the soil module
        Tdo: might be necessary to cover all variables = put 0 instead of missing value
        """
        # --- Topography -----------------------------------------------------
        # maps of elevation attributes:
        # topoParams = 'tanslope', 'slopeLength', 'orographyBeta'
        self.var.tanslope = loadmap('tanslope')
        self.var.slopeLength = loadmap('slopeLength')
        self.var.orographyBeta = loadmap('orographyBeta')

        self.var.tanslope = np.maximum(self.var.tanslope, 0.00001)
        # setting slope >= 0.00001 to prevent 0 value

        # maps of relative elevation above flood plains
        dzRel = ['dzRel0001','dzRel0005',
                 'dzRel0010','dzRel0020','dzRel0030','dzRel0040','dzRel0050',
                 'dzRel0060','dzRel0070','dzRel0080','dzRel0090','dzRel0100']
        for i in dzRel:
            vars(self.var)[i] = readnetcdfWithoutTime(binding['relativeElevation'],i)

        # --- Soil -----------------------------------------------------
        # soil properties of FAO
        self.var.airEntryValue1 = loadmap('airEntryValue1')
        self.var.airEntryValue2 = loadmap('airEntryValue2')
        self.var.poreSizeBeta1  = loadmap('poreSizeBeta1')
        self.var.poreSizeBeta2  = loadmap('poreSizeBeta2')
        self.var.resVolWC1      = loadmap('resVolWC1')
        self.var.resVolWC2      = loadmap('resVolWC2')
        self.var.satVolWC1      = loadmap('satVolWC1')
        self.var.satVolWC2      = loadmap('satVolWC2')
        self.var.KSat1 = loadmap('KSat1')
        self.var.KSat2 = loadmap('KSat2')
        self.var.percolationImp = loadmap('percolationImp')

        # soil parameters which are constant / uniform for the entire domain
        self.var.clappAddCoeff = loadmap('clappAddCoeff')
        self.var.matricSuctionFC = loadmap('matricSuctionFC')
        self.var.matricSuction50 = loadmap('matricSuction50')
        self.var.matricSuctionWP = loadmap('matricSuctionWP')
        self.var.maxGWCapRise = loadmap('maxGWCapRise')

        #  ----- some calculation ----------------------------------------
        # set for 3 soil layers the soil propertiy variables
        # they are linked not hard copied!
        self.var.satVolMoistContUpp000005 = self.var.satVolWC1
        self.var.satVolMoistContUpp005030 = self.var.satVolWC1
        self.var.satVolMoistContLow030150 = self.var.satVolWC2
        self.var.resVolMoistContUpp000005 = self.var.resVolWC1
        self.var.resVolMoistContUpp005030 = self.var.resVolWC1
        self.var.resVolMoistContLow030150 = self.var.resVolWC2
        self.var.airEntryValueUpp000005 = self.var.airEntryValue1
        self.var.airEntryValueUpp005030 = self.var.airEntryValue1
        self.var.airEntryValueLow030150 = self.var.airEntryValue2
        self.var.poreSizeBetaUpp000005 = self.var.poreSizeBeta1
        self.var.poreSizeBetaUpp005030 = self.var.poreSizeBeta1
        self.var.poreSizeBetaLow030150 = self.var.poreSizeBeta2
        self.var.kSatUpp000005 = self.var.KSat1
        self.var.kSatUpp005030 = self.var.KSat1
        self.var.kSatLow030150 = self.var.KSat2

        # assign Campbell's (1974) beta coefficient, as well as degree
        # of saturation at field capacity and corresponding unsaturated hydraulic conductivity

        self.var.campbellBetaUpp000005 = 2. * self.var.poreSizeBetaUpp000005 + self.var.clappAddCoeff
        self.var.campbellBetaUpp005030 = 2. * self.var.poreSizeBetaUpp005030 + self.var.clappAddCoeff
        self.var.campbellBetaLow030150 = 2. * self.var.poreSizeBetaLow030150 + self.var.clappAddCoeff
        self.var.effSatAtFieldCapUpp000005 =  (self.var.matricSuctionFC / self.var.airEntryValueUpp000005) ** \
                 (-1 / self.var.poreSizeBetaUpp000005)
        self.var.effSatAtFieldCapUpp005030 = (self.var.matricSuctionFC / self.var.airEntryValueUpp005030) ** \
                 (-1 / self.var.poreSizeBetaUpp005030)
        self.var.effSatAtFieldCapLow030150 = (self.var.matricSuctionFC / self.var.airEntryValueLow030150) ** \
                 (-1 / self.var.poreSizeBetaLow030150)

        self.var.kUnsatAtFieldCapUpp000005 = np.maximum(0., self.var.effSatAtFieldCapUpp000005 ** self.var.poreSizeBetaUpp000005 * self.var.kSatUpp000005)
        self.var.kUnsatAtFieldCapUpp005030 = np.maximum(0., self.var.effSatAtFieldCapUpp005030 ** self.var.poreSizeBetaUpp005030 * self.var.kSatUpp005030)
        self.var.kUnsatAtFieldCapLow030150 = np.maximum(0., self.var.effSatAtFieldCapLow030150 ** self.var.poreSizeBetaLow030150 * self.var.kSatLow030150)

        # calculate degree of saturation at which transpiration is halved (50)
        # and at wilting point
        self.var.effSatAt50Upp000005 = (self.var.matricSuction50 / self.var.airEntryValueUpp000005) ** (-1 / self.var.poreSizeBetaUpp000005)

        self.var.effSatAt50Upp005030 = (self.var.matricSuction50 / self.var.airEntryValueUpp005030) ** (-1 / self.var.poreSizeBetaUpp005030)
        self.var.effSatAt50Low030150 = (self.var.matricSuction50 / self.var.airEntryValueLow030150) ** (-1 / self.var.poreSizeBetaLow030150)
        self.var.effSatAtWiltPointUpp000005 = (self.var.matricSuctionWP / self.var.airEntryValueUpp000005) ** (-1 / self.var.poreSizeBetaUpp000005)
        self.var.effSatAtWiltPointUpp005030 = (self.var.matricSuctionWP / self.var.airEntryValueUpp005030) ** (-1 / self.var.poreSizeBetaUpp005030)
        self.var.effSatAtWiltPointLow030150 =  (self.var.matricSuctionWP / self.var.airEntryValueLow030150) ** (-1 / self.var.poreSizeBetaLow030150)

        # calculate interflow parameter (TCL):
        self.var.interflowConcTime = (2. * self.var.kSatLow030150 * self.var.tanslope) /\
                                     (self.var.slopeLength * (1. - self.var.effSatAtFieldCapLow030150) * \
                                     (self.var.satVolMoistContLow030150 - self.var.resVolMoistContLow030150))

        #self.var.interflowConcTime = pcr.cover(self.var.interflowConcTime, 0.0)




    # ------------ SOIL DEPTH ----------------------------------------------------------
        # soil thickness and storage
        #soilStorages: firstStorDepth, secondStorDepth, soilWaterStorageCap1, soilWaterStorageCap2
        self.var.firstStorDepthInp = loadmap('firstStorDepth')
        self.var.secondStorDepthInp = loadmap('secondStorDepth')
        self.var.soilWaterStorageCap1Inp = loadmap('soilWaterStorageCap1')
        self.var.soilWaterStorageCap2Inp = loadmap('soilWaterStorageCap2')

        # layer thickness
        self.var.thickUpp000005 = (0.05 / 0.30) * self.var.firstStorDepthInp
        self.var.thickUpp005030 = (0.25 / 0.30) * self.var.firstStorDepthInp
        self.var.thickLow030150 = (1.20 / 1.20) * self.var.secondStorDepthInp

        self.var.storCapUpp000005 = self.var.thickUpp000005 * (self.var.satVolMoistContUpp000005 - self.var.resVolMoistContUpp000005)

        self.var.storCapUpp005030 = self.var.thickUpp005030 * (self.var.satVolMoistContUpp005030 - self.var.resVolMoistContUpp005030)
        self.var.storCapLow030150 = self.var.thickLow030150 * (self.var.satVolMoistContLow030150 - self.var.resVolMoistContLow030150)
        self.var.rootZoneWaterStorageCap = self.var.storCapUpp000005 + self.var.storCapUpp005030 + self.var.storCapLow030150

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic_PotET(self,coverType, No):
        """ dynamic part of the soil module - potET
             calculating potential Evaporation for each land cover class
             get crop coefficient, use potential ET, calculate potential bare soil evaporation and transpiration
        """

        # get crop coefficient:
        self.var.cropKC = readnetcdf2(binding[coverType + '_cropCoefficientNC'], self.var.CalendarDay, "DOY")
        self.var.cropKC = np.maximum(self.var.cropKC, self.var.minCropKC[No])

        # calculate potential ET:
        self.var.totalPotET = self.var.cropKC * self.var.ETRef

        # calculate potential bare soil evaporation and transpiration
        self.var.potBareSoilEvap[No] = self.var.minCropKC[No] * self.var.ETRef
        self.var.potTranspiration[No] = self.var.cropKC[No] * self.var.ETRef - self.var.potBareSoilEvap[No]

    def dynamic_interception(self,coverType, No):

        if not coverType.startswith("irr"):
            interceptCap  = readnetcdf2(binding[coverType + '_interceptCapNC'], self.var.CalendarDay, "DOY")
            coverFraction = readnetcdf2(binding[coverType + '_coverFractionNC'], self.var.CalendarDay, "DOY")
            interceptCap = coverFraction * interceptCap
            self.interceptCap = np.maximum(interceptCap, self.var.minInterceptCap[No])
        else:
            interceptCap = self.var.minInterceptCap[No]

        # throughfall = surplus above the interception storage threshold
        throughfall = np.maximum(0.0, self.var.interceptStor[No] + self.var.Precipitation - interceptCap)

        # update interception storage after throughfall
        self.var.interceptStor[No] = np.maximum(0.0, self.var.interceptStor[No] + self.var.Precipitation - throughfall)

        # partitioning throughfall into snowfall and liquid Precipitation:
        # Snow from the snow module: precipitation is split into rain and snow
        self.var.liquidPrecip[No] = np.maximum(0.0, throughfall - self.var.Snow)

        # evaporation from intercepted water (based on potTranspiration)
        mult = getValDivZero(self.var.interceptStor[No], interceptCap, 1e39, 0.) ** 0.66666
        self.var.interceptEvap[No] = np.minimum(self.var.interceptStor[No], self.var.potTranspiration[No] * mult)
        self.var.interceptEvap[No] = np.minimum(self.var.interceptEvap[No], self.var.potTranspiration[No])

        # update interception storage and potTranspiration
        self.var.interceptStor[No] = self.var.interceptStor[No] - self.var.interceptEvap[No]
        self.var.potTranspiration[No] = np.maximum(0, self.var.potTranspiration[No] - self.var.interceptEvap[No])


        # update actual evaporation (after interceptEvap)
        # interceptEvap is the first flux in ET
        self.var.actualET[No] = self.var.interceptEvap[No].copy()


    def dynamic_getSoilStates(self, coverType, No):

        # initial total soilWaterStorage
        self.var.soilWaterStorage[No] = np.maximum(0., self.var.storUpp000005[No] + self.var.storUpp005030[No] + self.var.storLow030150[No])

        # effective degree of saturation (-)
        effSatUpp000005 = np.minimum(1.0,np.maximum(0., self.var.storUpp000005[No] / self.var.storCapUpp000005))
        effSatUpp005030 = np.minimum(1.0,np.maximum(0., self.var.storUpp005030[No] / self.var.storCapUpp005030))
        effSatLow030150 = np.minimum(1.0,np.maximum(0., self.var.storLow030150[No] / self.var.storCapLow030150))


        # matricSuction (m)
        matricSuctionUpp000005 = self.var.airEntryValueUpp000005 * (np.maximum(0.01, effSatUpp000005) ** -self.var.poreSizeBetaUpp000005)
        matricSuctionUpp005030 = self.var.airEntryValueUpp005030 * (np.maximum(0.01, effSatUpp005030) ** -self.var.poreSizeBetaUpp005030)
        matricSuctionLow030150 = self.var.airEntryValueLow030150 * (np.maximum(0.01, effSatLow030150) ** -self.var.poreSizeBetaLow030150)

        # kUnsat (m.day-1): unsaturated hydraulic conductivity
        kUnsatUpp000005 = np.maximum(0., (effSatUpp000005 ** self.var.campbellBetaUpp000005) * self.var.kSatUpp000005)
        kUnsatUpp005030 = np.maximum(0., (effSatUpp005030 ** self.var.campbellBetaUpp005030) * self.var.kSatUpp005030)
        kUnsatLow030150 = np.maximum(0., (effSatLow030150 ** self.var.campbellBetaLow030150) * self.var.kSatLow030150)

        kUnsatUpp000005 = np.minimum(kUnsatUpp000005, self.var.kSatUpp000005)
        kUnsatUpp005030 = np.minimum(kUnsatUpp005030, self.var.kSatUpp005030)
        kUnsatLow030150 = np.minimum(kUnsatLow030150, self.var.kSatLow030150)

        # kThVert (m.day-1) = unsaturated conductivity capped at field capacity
        # - exchange between layers capped at field capacity
        #   between Upp000005Upp005030
        kThVertUpp000005Upp005030 = np.minimum( np.sqrt(kUnsatUpp000005 * kUnsatUpp005030), \
            (kUnsatUpp000005 * kUnsatUpp005030 * self.var.kUnsatAtFieldCapUpp000005 * \
             self.var.kUnsatAtFieldCapUpp005030) ** 0.25)
        #   between Upp005030Low030150
        kThVertUpp005030Low030150 = np.minimum( np.sqrt(kUnsatUpp005030 * kUnsatLow030150), \
            (kUnsatUpp005030 * kUnsatLow030150 * self.var.kUnsatAtFieldCapUpp005030 * \
             self.var.kUnsatAtFieldCapLow030150) ** 0.25)

        # gradient for capillary rise (index indicating target store to its underlying store)
        #    between Upp000005Upp005030
        gradientUpp000005Upp005030 = np.maximum(0., 2. * \
             (matricSuctionUpp000005 - matricSuctionUpp005030) / \
             (self.var.thickUpp000005 + self.var.thickUpp005030) - 1.)
        #    between Upp005030Low030150
        gradientUpp005030Low030150 = np.maximum(0., 2. * \
             (matricSuctionUpp005030 - matricSuctionLow030150) / \
             (self.var.thickUpp005030 + self.var.thickLow030150) - 1.)

        # readily available water in the root zone (upper soil layers)
        h1 = np.maximum(0., effSatUpp000005 - self.var.effSatAtWiltPointUpp000005) *\
             (self.var.satVolMoistContUpp000005 - self.var.resVolMoistContUpp000005) *\
              np.minimum(self.var.thickUpp000005, self.var.maxRootDepth)
        h2 = (np.maximum(0., effSatUpp005030 - self.var.effSatAtWiltPointUpp005030)) *\
            (self.var.satVolMoistContUpp005030 - self.var.resVolMoistContUpp005030) *\
             np.minimum(self.var.thickUpp005030, np.maximum(self.var.maxRootDepth - self.var.thickUpp000005,0.))

        h3 = np.maximum(0.,effSatLow030150 - self.var.effSatAtWiltPointLow030150) *\
             (self.var.satVolMoistContLow030150 - self.var.resVolMoistContLow030150) *\
             np.minimum(self.var.thickLow030150, np.maximum(self.var.maxRootDepth - self.var.thickUpp005030, 0.))

        self.var.readAvlWater = h1 + h2 + h3
        self.var.readAvlWater = np.minimum(self.var.readAvlWater, self.var.storUpp000005[No] + self.var.storUpp005030[No] + self.var.storLow030150[No])


        self.var.waterdemand_module.dynamic_waterdemand(coverType, No)



