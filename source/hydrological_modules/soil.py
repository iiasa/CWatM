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

    def dynamic(self):
        """ dynamic part of the soil module
        """

        i = 1
