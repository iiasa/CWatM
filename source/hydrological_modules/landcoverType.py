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
        self.var.coverTypes= map(str.strip, binding["coverTypes"].split(","))

        # first, we set the following aggregated storages to zero
        self.var.suminterceptStor = globals.inZero.copy()
        self.var.sumtopWaterLayer = globals.inZero.copy()
        self.var.sumstorUpp000005 = globals.inZero.copy()
        self.var.sumstorUpp005030 = globals.inZero.copy()
        self.var.sumstorLow030150 = globals.inZero.copy()

        self.var.minTopWaterLayer =[];  self.var.minCropKC =[];  self.var.minInterceptCap =[]
        self.var.cropDeplFactor = []
        # area (m2) of a certain land cover type ;
        # grassland + forest adds up to 100% will be corrected by irrigation
        self.var.fracVegCover = []

        self.var.rootFraction1 = []; self.var.rootFraction2 = []
        self.var.maxRootDepth = []; self.var.minSoilDepthFrac = []; self.var.maxSoilDepthFrac = []
        self.var.cropCoefficientNC_filename = []; self.var.interceptCapNC_filename = []; self.var.coverFractionNC_filename = []
        self.var.interceptStor = []; self.var.topWaterLayer = []
        self.var.storUpp000005 = []; self.var.storUpp005030 = []; self.var.storLow030150 = []
        self.var.interflow = [];self.var.arnoBeta=[]

        # fraction of what type of irrigation area
        self.var.irrTypeFracOverIrr = [0, 0, 0, 0]
        # fraction (m2) of a certain irrigation type over (only) total irrigation area ; will be assigned by the landSurface module
        self.var.fractionArea = [0,0,0,0]
        self.var.totAvlWater = [0,0,0,0]
        self.var.adjRootFrUpp000005 = [0,0,0,0]
        self.var.adjRootFrUpp005030 = [0,0,0,0]
        self.var.adjRootFrLow030150 = [0,0,0,0]
        self.var.effSatAt50 = [0,0,0,0]
        self.var.effPoreSizeBetaAt50 = [0,0,0,0]
        self.var.directRunoff = [0,0,0,0]

        i = 0
        for coverType in self.var.coverTypes:
            self.var.fracVegCover.append(loadmap(coverType + "_fracVegCover"))

        #  rescales natural land cover fractions (make sure the total = 1)  #TODO
        # forest  = 0, grassland = 1, irrPaddy = 2 , irrnonpaddy = 3
        # fraction of land for irrigation
        irrigatedAreaFrac = self.var.fracVegCover[2] + self.var.fracVegCover[3]
        # Correction of forest and grassland by irrigation part: #have to think if irrigation should go at the same pecentage from forest
        # BETTER adjust these maps before !!!
        self.var.fracVegCover[0] = self.var.fracVegCover[0] * (1.0- irrigatedAreaFrac)
        self.var.fracVegCover[1] = self.var.fracVegCover[1] * (1.0- irrigatedAreaFrac)

        # fraction of what type of irrigation area
        self.var.irrTypeFracOverIrr[2] = self.var.fracVegCover[2] / np.maximum(1E-9,irrigatedAreaFrac)
        self.var.irrTypeFracOverIrr[3] = self.var.fracVegCover[3] / np.maximum(1E-9,irrigatedAreaFrac)


        i = 0
        for coverType in self.var.coverTypes:
            # other paramater values
            self.var.arnoBeta.append(loadmap(coverType + "_arnoBeta"))
            # b coefficient of soil water storage capacity distribution
            self.var.minTopWaterLayer.append(loadmap(coverType + "_minTopWaterLayer"))
            self.var.minCropKC.append(loadmap(coverType + "_minCropKC"))
            self.var.minInterceptCap.append(loadmap(coverType + "_minInterceptCap"))
            self.var.cropDeplFactor.append(loadmap(coverType + "_cropDeplFactor"))
            # parameter values

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

            # Improved Arno's scheme parameters:
            if self.var.arnoBeta[i] == 0:
                self.var.arnoBeta[i] = np.minimum(10.0,
                    np.maximum(0.001, (self.var.maxSoilDepthFrac[i] - 1.) / (1. - self.var.minSoilDepthFrac[i]) + self.var.orographyBeta - 0.01))
            else:
                self.var.arnoBeta[i] = np.minimum(10.0,np.maximum(0.001, self.arnoBeta))

            #report(decompress(self.var.arnoBeta[i]), "C:\work\output\harno.map")



            self.var.rootZoneWaterStorageMin = self.var.minSoilDepthFrac * self.var.rootZoneWaterStorageCap
            self.var.rootZoneWaterStorageRange = self.var.rootZoneWaterStorageCap - self.var.rootZoneWaterStorageMin

            # scaleRootFractions
            rootFracUpp000005 = 0.05/0.30 * self.var.rootFraction1[i]
            rootFracUpp005030 = 0.25/0.30 * self.var.rootFraction1[i]
            rootFracLow030150 = 1.20/1.20 * self.var.rootFraction2[i]
            self.var.adjRootFrUpp000005[i] = rootFracUpp000005 / (rootFracUpp000005 + rootFracUpp005030 + rootFracLow030150)
            self.var.adjRootFrUpp005030[i] = rootFracUpp005030 / (rootFracUpp000005 + rootFracUpp005030 + rootFracLow030150)
            self.var.adjRootFrLow030150[i] = rootFracLow030150 / (rootFracUpp000005 + rootFracUpp005030 + rootFracLow030150)
            #
            # if not defined, put everything in the first layer:
            #self.var.adjRootFrUpp000005 = pcr.cover(self.adjRootFrUpp000005,1.0)
            self.var.adjRootFrUpp005030[i] = np.where(self.var.adjRootFrUpp000005[i] < 1.0, self.var.adjRootFrUpp005030[i], 0.0)
            self.var.adjRootFrLow030150[i] = 1.0 - (self.var.adjRootFrUpp000005[i] + self.var.adjRootFrUpp005030[i])


            # ------------------------------------------
            # calculateTotAvlWaterCapacityInRootZone
            # total water capacity in the root zone (upper soil layers)
            # Note: This is dependent on the land cover type.

            h1 = np.maximum(0., self.var.effSatAtFieldCapUpp000005 - self.var.effSatAtWiltPointUpp000005) * \
                (self.var.satVolMoistContUpp000005 - self.var.resVolMoistContUpp000005) * \
                np.minimum(self.var.thickUpp000005, self.var.maxRootDepth[i])

            h2 = np.maximum(0., self.var.effSatAtFieldCapUpp005030 - self.var.effSatAtWiltPointUpp005030) * \
                (self.var.satVolMoistContUpp005030 - self.var.resVolMoistContUpp005030) * \
                np.minimum(self.var.thickUpp005030, np.maximum(0.,self.var.maxRootDepth[i] - self.var.thickUpp000005))


            h3 = np.maximum(0., self.var.effSatAtFieldCapLow030150 - self.var.effSatAtWiltPointLow030150) * \
                (self.var.satVolMoistContLow030150 - self.var.resVolMoistContLow030150) * \
                np.minimum(self.var.thickLow030150, np.maximum(self.var.maxRootDepth[i] - self.var.thickUpp005030, 0.))

            self.var.totAvlWater[i] = h1 + h2 + h3
            self.var.totAvlWater[i] = np.minimum(self.var.totAvlWater[i], self.var.storCapUpp000005 + self.var.storCapUpp005030 + self.var.storCapLow030150)

            # --------------------------------------------------------------------------------------------------------
            # calculateParametersAtHalfTranspiration(self, parameters):
            # average soil parameters at which actual transpiration is halved
            h1 = self.var.storCapUpp000005 * self.var.adjRootFrUpp000005[i] * \
                 (self.var.matricSuction50 / self.var.airEntryValueUpp000005) ** (-1. / self.var.poreSizeBetaUpp000005)

            h2 = self.var.storCapUpp005030 * self.var.adjRootFrUpp005030[i] * \
                 (self.var.matricSuction50 / self.var.airEntryValueUpp000005) ** (-1. / self.var.poreSizeBetaUpp000005)

            h3 = self.var.storCapLow030150 * self.var.adjRootFrLow030150[i] * \
                (self.var.matricSuction50 / self.var.airEntryValueLow030150) ** \
                (-1. / self.var.poreSizeBetaLow030150) / \
                (self.var.storCapUpp000005 * self.var.adjRootFrUpp000005[i] + \
                 self.var.storCapUpp005030 * self.var.adjRootFrUpp005030[i] + \
                 self.var.storCapLow030150 * self.var.adjRootFrLow030150[i])
            self.var.effSatAt50[i] = h1 + h2 + h3

            h1 = self.var.storCapUpp000005 * self.var.adjRootFrUpp000005[i] * self.var.poreSizeBetaUpp000005 +\
                 self.var.storCapUpp005030 * self.var.adjRootFrUpp005030[i] * self.var.poreSizeBetaUpp005030 +\
                 self.var.storCapLow030150 * self.var.adjRootFrLow030150[i] * self.var.poreSizeBetaLow030150
            h2 = self.var.storCapUpp000005 * self.var.adjRootFrUpp000005[i] + self.var.storCapUpp005030 *\
                 self.var.adjRootFrUpp005030[i] + self.var.storCapLow030150[i] * self.var.adjRootFrLow030150[i]
            self.var.effPoreSizeBetaAt50[i] = h1 / h2



            i += 1





        # output variable per land cover class
        self.var.potBareSoilEvap = [0, 0, 0, 0]
        self.var.potTranspiration = [0, 0, 0, 0]
        self.var.availWaterInfiltration = [0, 0, 0, 0]
        self.var.interceptEvap = [0, 0, 0, 0]
        self.var.actualET = [0, 0, 0, 0]

        self.var.soilWaterStorage = [0, 0, 0, 0]
        self.var.a2ctualET = [0, 0, 0, 0]
        self.var.a3ctualET = [0, 0, 0, 0]



    # --------------------------------------------------------------------------

    def dynamic_fracIrrigation(self):
        """ dynamic part of the land cover type module
            calculating fraction of land cover
        """

        if option['includeIrrigation'] and option['dynamicIrrigationArea']:
        # if first day of the year or first day of run
            if (self.var.currentTimeStep() == 1) or (int(self.var.CalendarDate.strftime('%j')) ==1):
               date = self.var.CalendarDate
               i = self.var.currentTimeStep()
               # updating fracVegCover of landCover (for historical irrigation areas, done at yearly basis)
               # read historical irrigation areas
               self.var.irrigationArea = 10000.0 *readnetcdf2(binding['historicalIrrigationArea'], self.var.CalendarDate, "yearly")

               # area of irrigation is limited by cellArea
               self.var.irrigationArea = np.maximum(self.var.irrigationArea, 0.0)
               self.var.irrigationArea = np.minimum(self.var.irrigationArea, self.var.cellArea)

               # calculate fracVegCover (for irrigation only)
               # forest  = 0, grassland = 1, irrPaddy = 2 , irrnonpaddy = 3
               for i in[2,3]:
                   self.var.fractionArea[i] = self.var.irrTypeFracOverIrr[i] * self.var.irrigationArea   # unit: square m
                   self.var.fracVegCover[i] = np.minimum(1.0, self.var.fractionArea[i] / self.var.cellArea)  # unit: fraction
                   # avoiding small numbers
                   self.var.fracVegCover[i] = np.where(self.var.fracVegCover[i] > 0.001, self.var.fracVegCover[i], 0.0)

               irrigatedAreaFrac = self.var.fracVegCover[2] + self.var.fracVegCover[3]
               # Correction of forest and grassland by irrigation part: #have to think if irrigation should go at the same pecentage from forest
               # BETTER adjust these maps before !!!
               self.var.fracVegCover[0] = self.var.fracVegCover[0] * (1.0 - irrigatedAreaFrac)
               self.var.fracVegCover[1] = self.var.fracVegCover[1] * (1.0 - irrigatedAreaFrac)


# --------------------------------------------------------------------------

    def dynamic(self, coverType, coverNo):
        """ dynamic part of the land cover type module
            calculating soil for each land cover class
        """

        self.var.soil_module.dynamic_PotET(coverType, coverNo)
        self.var.soil_module.dynamic_interception(coverType, coverNo)
        self.var.soil_module.dynamic_getSoilStates(coverType, coverNo)
        i = 1





        # landcover UpdateLC 370
        """
        self.landCoverObj[coverType].updateLC(meteo,groundwater,routing,\
                                      self.parameters,self.capRiseFrac,\
                                      self.potentialNonIrrGrossWaterDemand,\
                                      self.swAbstractionFraction,\
                                      currTimeStep,\
                                      allocSegments = self.allocSegments)


        getPotET(coverType,coverNo)
        self.interceptionUpdate(meteo, currTimeStep)  # calculate interception and update storage
            # snow already calculated

        # calculate qDR & qSF & q23 (and update storages)
        self.upperSoilUpdate(meteo,groundwater,routing, parameters,capRiseFrac, nonIrrGrossDemand,swAbstractionFraction 378 -> 1642
            self.getSoilStates(parameters) 1656 -> 626
            self.calculateWaterDemand  777
            self.calculateOpenWaterEvap() 1027
            self.calculateDirectRunoff(parameters)   940
            self.calculateInfiltration(parameters)  1052
            self.estimateTranspirationAndBareSoilEvap(parameters)
            self.estimateSoilFluxes(parameters,capRiseFrac)
            self.scaleAllFluxes(parameters, groundwater)
            self.updateSoilStates(parameters)

        """



