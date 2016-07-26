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



        landcoverPara = ['minTopWaterLayer','minCropKC','minInterceptCap','cropDeplFactor','fracVegCover','rootFraction1','rootFraction2',
                         'maxRootDepth', 'minSoilDepthFrac','maxSoilDepthFrac','interceptStor', 'topWaterLayer',
                         'storUpp000005', 'storUpp005030', 'storLow030150', 'interflow','arnoBeta',
                         'cropCoefficientNC_filename', 'interceptCapNC_filename','coverFractionNC_filename']
        for variable in landcoverPara:
            vars(self.var)[variable] = []

        # fraction of what type of irrigation area
        # fraction (m2) of a certain irrigation type over (only) total irrigation area ; will be assigned by the landSurface module
        # output variable per land cover class
        landcoverVars = ['irrTypeFracOverIrr','fractionArea','totAvlWater', 'adjRootFrUpp000005','adjRootFrUpp005030', 'adjRootFrLow030150',
                         'effSatAt50',  'effPoreSizeBetaAt50', 'rootZoneWaterStorageMin','rootZoneWaterStorageRange',
                         'directRunoff','totalPotET','potBareSoilEvap','potTranspiration','availWaterInfiltration','interceptEvap','soilWaterStorage',
                         'infiltration','actBareSoilEvap','landSurfaceRunoff','actTranspiTotal','netPercUpp000005', 'netPercUpp005030',
                         'gwRecharge','interflow','actualET']
        for variable in landcoverVars:
             vars(self.var)[variable] = [globals.inZero.copy(), globals.inZero.copy(), globals.inZero.copy(), globals.inZero.copy()]

        # set aggregated storages to zero
        self.var.landcoverSum = [ 'interceptStor', 'topWaterLayer','interflow', 'storUpp000005', 'storUpp005030', 'storLow030150',
                         'directRunoff', 'totalPotET', 'potBareSoilEvap', 'potTranspiration', 'availWaterInfiltration',
                         'interceptEvap', 'soilWaterStorage', 'infiltration', 'actBareSoilEvap', 'landSurfaceRunoff', 'actTranspiTotal', 'netPercUpp000005',
                         'netPercUpp005030','gwRecharge','actualET']
        for variable in self.var.landcoverSum:
            vars(self.var)["sum_"+variable] = globals.inZero.copy()


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
            self.var.sum_interceptStor += self.var.fracVegCover[i] * self.var.interceptStor[i]
            self.var.sum_topWaterLayer += self.var.fracVegCover[i] * self.var.topWaterLayer[i]
            self.var.sum_storUpp000005 += self.var.fracVegCover[i] * self.var.storUpp000005[i]
            self.var.sum_storUpp005030 += self.var.fracVegCover[i] * self.var.storUpp005030[i]
            self.var.sum_storLow030150 += self.var.fracVegCover[i] * self.var.storLow030150[i]

            # Improved Arno's scheme parameters:
            if self.var.arnoBeta[i] == 0:
                self.var.arnoBeta[i] = np.minimum(10.0,
                    np.maximum(0.001, (self.var.maxSoilDepthFrac[i] - 1.) / (1. - self.var.minSoilDepthFrac[i]) + self.var.orographyBeta - 0.01))
            else:
                self.var.arnoBeta[i] = np.minimum(1.0,np.maximum(0.001, self.arnoBeta))

            # PB changed to max 1.0 #TODO
            #report(decompress(self.var.arnoBeta[i]), "C:\work\output\harno.map")



            self.var.rootZoneWaterStorageMin[i] = self.var.minSoilDepthFrac[i] * self.var.rootZoneWaterStorageCap
            self.var.rootZoneWaterStorageRange[i] = self.var.rootZoneWaterStorageCap - self.var.rootZoneWaterStorageMin[i]

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
                 self.var.adjRootFrUpp005030[i] + self.var.storCapLow030150 * self.var.adjRootFrLow030150[i]
            self.var.effPoreSizeBetaAt50[i] = h1 / h2



            i += 1

        self.var.landcoverSumSum = ['directRunoff', 'totalPotET', 'potTranspiration', "Precipitation", 'ETRef','gwRecharge']
        for variable in self.var.landcoverSumSum:
            vars(self.var)["sumsum_" + variable] = globals.inZero.copy()



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
               nonirrigatedAreaFrac = self.var.fracVegCover[0] + self.var.fracVegCover[1]
               totalAreafrac = irrigatedAreaFrac + nonirrigatedAreaFrac
               # Correction of forest and grassland by irrigation part: #have to think if irrigation should go at the same pecentage from forest
               # BETTER adjust these maps before !!!
               for i in xrange(0,3):
                   self.var.fracVegCover[i] = self.var.fracVegCover[i]/totalAreafrac
               #self.var.fracVegCover[0] = self.var.fracVegCover[0] * (1.0 - irrigatedAreaFrac)
               #self.var.fracVegCover[1] = self.var.fracVegCover[1] * (1.0 - irrigatedAreaFrac)
               i = 1


# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the land cover type module
            calculating soil for each land cover class
        """


        coverNo = 0
        print "soil"
        # update soil (loop per each land cover type):
        for coverType in self.var.coverTypes:
            #print coverNo,coverType

            self.var.soil_module.dynamic_PotET(coverType, coverNo)

            self.var.soil_module.dynamic_Interception(coverType, coverNo)
            self.var.soil_module.dynamic_Soil(coverType, coverNo)
            coverNo += 1

        # aggregated variables by fraction of land cover
        # Land surface module 725


        # set aggregated storages to zero
        self.var.landcoverSum = [ 'interceptStor', 'topWaterLayer','interflow', 'storUpp000005', 'storUpp005030', 'storLow030150',
                         'directRunoff', 'totalPotET', 'potBareSoilEvap', 'potTranspiration', 'availWaterInfiltration',
                         'interceptEvap', 'soilWaterStorage', 'infiltration', 'actBareSoilEvap', 'landSurfaceRunoff', 'actTranspiTotal', 'netPercUpp000005',
                         'netPercUpp005030','gwRecharge','actualET']
        for variable in self.var.landcoverSum:
            vars(self.var)["sum_"+variable] = globals.inZero.copy()

        for variable in self.var.landcoverSum:
            for No in xrange(4):
                vars(self.var)["sum_" + variable] += self.var.fracVegCover[No] * vars(self.var)[variable][No]

        self.var.sumsum_directRunoff +=  self.var.sum_directRunoff
        self.var.sumsum_Precipitation += self.var.Precipitation
        self.var.sumsum_gwRecharge += self.var.sum_gwRecharge

        #report(decompress(self.var.sum_potTranspiration), "c:\work\output/trans.map")
        #report(decompress(self.var.directRunoff[3 ]), "c:\work\output\dir.map")
        report(decompress(self.var.sumsum_directRunoff), "c:\work\output\dirsum.map")
        report(decompress(self.var.sumsum_Precipitation), "c:\work\output\prsum.map")
        #a = decompress(self.var.sumsum_Precipitation)
        #b = cellvalue(a,81,379)
        #print self.var.sum_directRunoff


        #report(decompress(self.var.sumsum_Precipitation), "c:\work\output\Prsum.map")
        #report(decompress(self.var.sumsum_gwRecharge), "c:\work\output\gwrsum.map")








        # landcover UpdateLC 370
        """

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



