# -------------------------------------------------------------------------
# Name:        Land Cover Type module
# Purpose:
#
# Author:      PB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class landcoverType(object):

    """
    # ************************************************************
    # *****  LAND COVER TYPE *************************************
    # ************************************************************
    """

    def __init__(self, landcoverType_variable):
        self.var = landcoverType_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the land cover type module
        """
        coverTypes= map(str.strip, binding["coverTypes"].split(","))

        # first, we set the following aggregated storages to zero
        self.var.suminterceptStor = globals.inZero.copy()
        self.var.sumtopWaterLayer = globals.inZero.copy()
        self.var.sumstorUpp000005 = globals.inZero.copy()
        self.var.sumstorUpp005030 = globals.inZero.copy()
        self.var.sumstorLow030150 = globals.inZero.copy()

        self.var.minTopWaterLayer =[];  self.var.minCropKC =[];  self.var.minInterceptCap =[]
        self.var.cropDeplFactor = []
        self.var.fracVegCover = []; self.var.rootFraction1 = []; self.var.rootFraction2 = []
        self.var.maxRootDepth = []; self.var.minSoilDepthFrac = []; self.var.maxSoilDepthFrac = []
        self.var.cropCoefficientNC_filename = []; self.var.interceptCapNC_filename = []; self.var.coverFractionNC_filename = []
        self.var.interceptStor = []; self.var.topWaterLayer = []
        self.var.storUpp000005 = []; self.var.storUpp005030 = []; self.var.storLow030150 = []
        self.var.interflow = []

        i = 0
        for coverType in coverTypes:
            # other paramater values
            self.var.minTopWaterLayer.append(loadmap(coverType + "_minTopWaterLayer"))
            self.var.minCropKC.append(loadmap(coverType + "_minCropKC"))
            self.var.minInterceptCap.append(loadmap(coverType + "_minInterceptCap"))
            self.var.cropDeplFactor.append(loadmap(coverType + "_cropDeplFactor"))
            # parameter values
            self.var.fracVegCover.append(loadmap(coverType + "_fracVegCover"))
            self.var.rootFraction1.append(loadmap(coverType + "_rootFraction1"))
            self.var.rootFraction2.append(loadmap(coverType + "_rootFraction2"))
            self.var.maxRootDepth.append(loadmap(coverType + "_maxRootDepth"))
            self.var.minSoilDepthFrac.append(loadmap(coverType + "_minSoilDepthFrac"))
            self.var.maxSoilDepthFrac.append(loadmap(coverType + "_maxSoilDepthFrac"))

            # filenames
            self.var.cropCoefficientNC_filename.append(coverType + "_cropCoefficientNC")
            self.var.interceptCapNC_filename.append(coverType + "_interceptCapNC")
            self.var.coverFractionNC_filename.append(coverType + "_coverFractionNC")

            # init values
            self.var.interceptStor.append(loadmap(coverType + "_interceptStorIni"))
            self.var.topWaterLayer.append(loadmap(coverType + "_topWaterLayerIni"))
            self.var.storUpp000005.append(loadmap(coverType + "_storUpp000005Ini"))
            self.var.storUpp005030.append(loadmap(coverType + "_storUpp005030Ini"))
            self.var.storLow030150.append(loadmap(coverType + "_storLow030150Ini"))
            self.var.interflow.append(loadmap(coverType + "_interflowIni"))

            # summarize the following initial storages:
            self.var.suminterceptStor += self.var.fracVegCover[i] * self.var.interceptStor[i]
            self.var.sumtopWaterLayer += self.var.fracVegCover[i] * self.var.topWaterLayer[i]
            self.var.sumstorUpp000005 += self.var.fracVegCover[i] * self.var.storUpp000005[i]
            self.var.sumstorUpp005030 += self.var.fracVegCover[i] * self.var.storUpp005030[i]
            self.var.sumstorLow030150 += self.var.fracVegCover[i] * self.var.storLow030150[i]
            i += 1


        k= 1



# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the land cover type module
        """
        if option['includeIrrigation'] and option['dynamicIrrigationArea']:
            date = self.var.CalendarDate
            i = self.var.currentTimeStep()
            k = 1
        self.var.irri = readnetcdf2(binding['historicalIrrigationArea'], self.var.CalendarDate, "yearly")
