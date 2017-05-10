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
    LAND COVER TYPE

    runs the 6 land cover types through soil procedures
    This routine calls the soil routine for each land cover type

    """

    def __init__(self, landcoverType_variable):
        self.var = landcoverType_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """
        Initial part of the land cover type module
        Initialise the six land cover types

        * Forest
        * Grasland/non irrigated land
        * Irrigation
        * Paddy iirigation
        * Sealed area
        * Water covered area

        And initialize the soil variables
        """

        self.var.coverTypes= map(str.strip, binding["coverTypes"].split(","))
        landcoverAll = ['fracVegCover','interceptStor','interceptCap','availWaterInfiltration','interceptEvap',
                        'directRunoff', 'openWaterEvap']
        for variable in landcoverAll:  vars(self.var)[variable] = np.tile(globals.inZero, (6, 1))

        landcoverPara = ['minInterceptCap','cropDeplFactor','rootFraction1','rootFraction2',
                         'maxRootDepth', 'topWaterLayer','minSoilDepthFrac',
                         'interflow',
                         'cropCoefficientNC_filename', 'interceptCapNC_filename','coverFractionNC_filename',]
        # arrays stored as list not as numpy, because it can contain strings, single parameters or arrays
        # list is filled with append afterwards
        for variable in landcoverPara: vars(self.var)[variable] = []

        # fraction (m2) of a certain irrigation type over (only) total irrigation area ; will be assigned by the landSurface module
        # output variable per land cover class
        landcoverVars = ['irrTypeFracOverIrr','fractionArea','totAvlWater','cropKC',
                         'effSatAt50',  'effPoreSizeBetaAt50', 'rootZoneWaterStorageMin','rootZoneWaterStorageRange',
                         'totalPotET','potBareSoilEvap','potTranspiration','soilWaterStorage',
                         'infiltration','actBareSoilEvap','landSurfaceRunoff','actTransTotal',
                         'gwRecharge','interflow','actualET','irrGrossDemand',
                         'topWaterLayer',
                         'totalPotentialGrossDemand','actSurfaceWaterAbstract','allocSurfaceWaterAbstract','potGroundwaterAbstract',
                         'percToGW','capRiseFromGW','netPercUpper','netPerc','PrefFlow']
        # for 6 landcover types
        for variable in landcoverVars:  vars(self.var)[variable] = np.tile(globals.inZero,(6,1))

        #for 4 landcover types with soil underneath
        landcoverVarsSoil = ['arnoBeta','rootZoneWaterStorageCap','rootZoneWaterStorageCap12']
        for variable in landcoverVarsSoil:  vars(self.var)[variable] = np.tile(globals.inZero,(4,1))

        soilVars = ['adjRoot','perc','capRise', 'soilStor','rootDepth','storCap']
        # For 3 soil layers and 4 landcover types
        for variable in soilVars:  vars(self.var)[variable]= np.tile(globals.inZero,(self.var.soilLayers,4,1))

        # set aggregated storages to zero
        self.var.landcoverSum = [ 'interceptStor', 'topWaterLayer','interflow',
                         'directRunoff', 'totalPotET', 'potBareSoilEvap', 'potTranspiration', 'availWaterInfiltration',
                         'interceptEvap', 'infiltration', 'actBareSoilEvap', 'landSurfaceRunoff', 'actTransTotal', 'gwRecharge',
                         'actualET', 'topWaterLayer', 'openWaterEvap','capRiseFromGW','percToGW',"PrefFlow",
                         'irrGrossDemand','totalPotentialGrossDemand','actSurfaceWaterAbstract','allocSurfaceWaterAbstract','potGroundwaterAbstract']
        for variable in self.var.landcoverSum: vars(self.var)["sum_"+variable] = globals.inZero.copy()

        # for three soil layers
        soilVars = ['soilStor']
        for variable in soilVars: vars(self.var)["sum_" + variable] = np.tile(globals.inZero,(3,1))

        self.var.totalSoil = globals.inZero.copy()
        self.var.totalET = globals.inZero.copy()


        # ----------------------------------------------------------
        # Load initial values and calculate basic soil parameters which are not changed in time
        self.dynamic_fracIrrigation(init=True)
        i = 0
        for coverType in self.var.coverTypes:
            self.var.minInterceptCap.append(loadmap(coverType + "_minInterceptCap"))
            # init values
            if coverType in ['forest', 'grassland', 'irrPaddy', 'irrNonPaddy','sealed']:
                self.var.interceptStor[i] = self.var.init_module.load_initial(coverType + "_interceptStor")

            # summarize the following initial storages:
            self.var.sum_interceptStor += self.var.fracVegCover[i] * self.var.interceptStor[i]
            i += 1



        self.var.minCropKC= loadmap('minCropKC')
        self.var.minTopWaterLayer = loadmap("minTopWaterLayer")

        i = 0
        for coverType in self.var.coverTypes[:4]:
            # other paramater values
            # b coefficient of soil water storage capacity distribution
            #self.var.minTopWaterLayer.append(loadmap(coverType + "_minTopWaterLayer"))
            #self.var.minCropKC.append(loadmap(coverType + "_minCropKC"))

            #self.var.minInterceptCap.append(loadmap(coverType + "_minInterceptCap"))
            self.var.cropDeplFactor.append(loadmap(coverType + "_cropDeplFactor"))
            # parameter values

            self.var.rootFraction1.append(loadmap(coverType + "_rootFraction1"))
            self.var.rootFraction2.append(loadmap(coverType + "_rootFraction2"))
            self.var.maxRootDepth.append(loadmap(coverType + "_maxRootDepth"))
            self.var.minSoilDepthFrac.append(loadmap(coverType + "_minSoilDepthFrac"))

            # store filenames
            self.var.cropCoefficientNC_filename.append(coverType + "_cropCoefficientNC")
            self.var.interceptCapNC_filename.append(coverType + "_interceptCapNC")
            self.var.coverFractionNC_filename.append(coverType + "_coverFractionNC")

            # init values
            self.var.topWaterLayer[i] = self.var.init_module.load_initial(coverType + "_topWaterLayer")
            self.var.interflow[i] = self.var.init_module.load_initial(coverType + "_interflow")

            for soilLayer in xrange(self.var.soilLayers):
                self.var.soilStor[soilLayer][i] = self.var.init_module.load_initial(coverType + "_soilStor[" +str(soilLayer)+"]")
                # summarize the following initial storages:
                self.var.sum_soilStor[soilLayer] += self.var.fracVegCover[i] * self.var.soilStor[soilLayer][i]

            # summarize the following initial storages:
            self.var.sum_topWaterLayer += self.var.fracVegCover[i] * self.var.topWaterLayer[i]

            for soilLayer in xrange(self.var.soilLayers):
                self.var.sum_soilStor[soilLayer] = self.var.sum_soilStor[soilLayer] + self.var.soilStor[soilLayer][i] * self.var.fracVegCover[i]


            # Improved Arno's scheme parameters: Hageman and Gates 2003
            # arnoBeta defines the shape of soil water capacity distribution curve as a function of  topographic variability
            # b = max( (oh - o0)/(oh + omax), 0.01)
            # oh: the standard deviation of orography, o0: minimum std dev, omax: max std dev

            self.var.arnoBetaOro = (self.var.ElevationStD - 10.0) / (self.var.ElevationStD + 1500.0)

            # for CALIBRATION
            self.var.arnoBetaOro = self.var.arnoBetaOro + loadmap('arnoBeta_add')
            self.var.arnoBetaOro = np.minimum(1.2, np.maximum(0.01, self.var.arnoBetaOro))

            self.var.arnoBeta[i] = self.var.arnoBetaOro + loadmap(coverType + "_arnoBeta")
            self.var.arnoBeta[i] = np.minimum(1.2, np.maximum(0.01, self.var.arnoBeta[i]))




            # calculate rootdepth for each soillayer and each land cover class
            #self.var.rootDepth[0][i] = np.minimum(self.var.soildepth[0], self.var.maxRootDepth[i])
            self.var.rootDepth[0][i] = self.var.soildepth[0].copy()  # 0.05 m
            # if land cover = forest
            if coverType <>'grassland':
                # soil layer 1 = root max of land cover  - first soil layer
                h1 = np.maximum(self.var.soildepth[1], self.var.maxRootDepth[i] - self.var.soildepth[0])
                self.var.rootDepth[1][i] = np.minimum(self.var.soildepth12 - 0.05, h1)
                # soil layer is minimim 0.05 m
                self.var.rootDepth[2][i] = np.maximum(0.05, self.var.soildepth12 - self.var.rootDepth[1][i])
            else:
                self.var.rootDepth[1][i] = self.var.soildepth[1].copy()
                self.var.rootDepth[2][i] = self.var.soildepth[2].copy()


            # scaleRootFractions
            rootFrac = np.tile(globals.inZero,(self.var.soilLayers,1))
            fractionroot12 = self.var.rootDepth[0][i] / (self.var.rootDepth[0][i] + self.var.rootDepth[1][i] )
            rootFrac[0] = fractionroot12 * self.var.rootFraction1[i]
            rootFrac[1] = (1 - fractionroot12) * self.var.rootFraction1[i]
            rootFrac[2] = self.var.rootFraction2[i]
            rootFracSum = np.sum(rootFrac,axis=0)
            for soilLayer in xrange(self.var.soilLayers):
                self.var.adjRoot[soilLayer][i] = rootFrac[soilLayer] / rootFracSum




            for j in xrange(self.var.soilLayers):
                self.var.storCap[j][i] = self.var.rootDepth[j][i] * (self.var.satVol[j] - self.var.resVol[j])
            self.var.rootZoneWaterStorageCap[i] = self.var.storCap[0][i] + self.var.storCap[1][i] + self.var.storCap[2][i]
            self.var.rootZoneWaterStorageCap12[i] = self.var.storCap[0][i] + self.var.storCap[1][i]

            self.var.rootZoneWaterStorageMin[i] = self.var.minSoilDepthFrac[i] * self.var.rootZoneWaterStorageCap[i]
            self.var.rootZoneWaterStorageRange[i] = self.var.rootZoneWaterStorageCap[i] - self.var.rootZoneWaterStorageMin[i]



            # ------------------------------------------
            # calculateTotAvlWaterCapacityInRootZone
            # total water capacity in the root zone (upper soil layers)
            # Note: This is dependent on the land cover type.

            h = np.tile(globals.inZero, (self.var.soilLayers, 1))
            for j in xrange(self.var.soilLayers):
                h[j] = np.maximum(0., self.var.effSatAtFieldCap[j] - self.var.effSatAtWiltPoint[j]) * \
                     (self.var.satVol[j] - self.var.resVol[j]) * self.var.rootDepth[j][i]

            self.var.totAvlWater[i] = np.sum(h,axis=0)
            self.var.totAvlWater[i] = np.minimum(self.var.totAvlWater[i], self.var.rootZoneWaterStorageCap[i])

            h0 = np.tile(globals.inZero, (self.var.soilLayers, 1))
            h1 = np.tile(globals.inZero, (self.var.soilLayers, 1))
            h2 = np.tile(globals.inZero, (self.var.soilLayers, 1))
            h3 = np.tile(globals.inZero, (self.var.soilLayers, 1))
            # calculateParametersAtHalfTranspiration(self, parameters):
            # average soil parameters at which actual transpiration is halved
            # calculateParametersAtHalfTranspiration(self, parameters):
            # average soil parameters at which actual transpiration is halved
            for j in xrange(self.var.soilLayers):
                h0[j] = self.var.storCap[j][i] * self.var.adjRoot[j][i]
                h1[j] = np.maximum(0., self.var.effSatAtFieldCap[j] - self.var.effSatAtWiltPoint[j]) * \
                     (self.var.satVol[j] - self.var.resVol[j]) * self.var.rootDepth[j][i]
                h2[j] = h0[j] * (self.var.matricSuction50 / self.var.airEntry[j]) ** (-1. / self.var.poreSizeBeta[j])
                h3[j] = h0[j] * self.var.poreSizeBeta[j]

            adjrootZoneWaterStorageCap = np.sum(h0 , axis=0)
            self.var.totAvlWater[i] = np.sum(h1,axis=0)
            self.var.totAvlWater[i] = np.minimum(self.var.totAvlWater[i], self.var.rootZoneWaterStorageCap[i])
            self.var.effSatAt50[i] = np.sum(h2 / adjrootZoneWaterStorageCap , axis=0)
            self.var.effPoreSizeBetaAt50[i] = np.sum(h3 / adjrootZoneWaterStorageCap, axis=0)

            i += 1



        self.var.landcoverSumSum = ['directRunoff', 'totalPotET', 'potTranspiration', "Precipitation", 'ETRef','gwRecharge','Runoff']
        for variable in self.var.landcoverSumSum:
            vars(self.var)["sumsum_" + variable] = globals.inZero.copy()


    # --------------------------------------------------------------------------

    def dynamic_fracIrrigation(self, init = False):
        """
        Dynamic part of the land cover type module
        Calculating fraction of land cover

        * loads the fraction of landcover for each year from netcdf maps
        * calculate the fraction of 6 land cover types based on the maps
        """

        #if option['includeIrrigation'] and option['dynamicIrrigationArea']:

        # updating fracVegCover of landCover (for historical irrigation areas, done at yearly basis)
        # if first day of the year or first day of run

        if init:
            i = 0
            for coverType in self.var.coverTypes:
                self.var.fracVegCover[i] = readnetcdf2(binding['fractionLandcover'], dateVar['currDate'], useDaily="yearly",  value= 'frac'+coverType)
                #report(decompress(self.var.fracVegCover[i]), "C:\work\output2/lc"+str(i)+".map")
                i += 1

            # correction of grassland if sum is not 1.0
            sum = np.sum(self.var.fracVegCover,axis=0)
            self.var.fracVegCover[1] = self.var.fracVegCover[1] + 1.0 - sum
            # sum of landcover without water and sealed
            self.var.sum_fracVegCover = np.sum(self.var.fracVegCover[0:4], axis=0)



            #self.var.fracVegCover[0] = self.var.fracVegCover[0] + self.var.fracVegCover[4]
            #self.var.fracVegCover[1] = self.var.fracVegCover[1] + self.var.fracVegCover[5]
            #self.var.fracVegCover[0] = 1.0
            #self.var.fracVegCover[1] = 0.0
            #self.var.fracVegCover[2] = 0.0
            #self.var.fracVegCover[3] = 0.0
            #self.var.fracVegCover[4] = 0.0
            #self.var.fracVegCover[5] = 0.0
            #i = 111


# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Dynamic part of the land cover type module
        Calculating soil for each of the 6  land cover class

        * calls evaporation_module.dynamic
        * calls interception_module.dynamic
        * calls soil_module.dynamic
        * calls sealed_water_module.dynamic

        And sums every thing up depending on the land cover type fraction
        """


        if option['calcWaterBalance']:
            preTopWaterLayer = self.var.sum_topWaterLayer.copy()
            preIntStor = self.var.sum_interceptStor.copy()
            preStor1 = self.var.sum_soilStor[0].copy()
            preStor2 = self.var.sum_soilStor[1].copy()
            preStor3 = self.var.sum_soilStor[2].copy()
            self.var.pretotalSoil = self.var.totalSoil.copy()


        coverNo = 0
        # update soil (loop per each land cover type):
        for coverType in self.var.coverTypes:
            #print coverNo,coverType


            # calculate evaporation and transpiration for soil land cover types (not for sealed and water covered areas)
            if coverNo < 4:
                self.var.evaporation_module.dynamic(coverType, coverNo)

            self.var.interception_module.dynamic(coverType, coverNo)

            if coverNo < 4:
                self.var.soil_module.dynamic(coverType, coverNo)
            else:
                self.var.sealed_water_module.dynamic(coverType, coverNo)
                # calculate for openwater and sealed area
            coverNo += 1






        # aggregated variables by fraction of land cover
        for variable in self.var.landcoverSum:
            vars(self.var)["sum_" + variable] = globals.inZero.copy()
            for No in xrange(6):
                vars(self.var)["sum_" + variable] += self.var.fracVegCover[No] * vars(self.var)[variable][No]

        #print "--", self.var.sum_directRunoff



        soilVars = ['soilStor']
        for variable in soilVars:
            for i in xrange(self.var.soilLayers):
                vars(self.var)["sum_" + variable][i] = globals.inZero.copy()
                for No in xrange(4):
                    vars(self.var)["sum_" + variable][i] += self.var.fracVegCover[No] * vars(self.var)[variable][i][No]


        self.var.totalSoil = self.var.sum_interceptStor + self.var.sum_topWaterLayer + \
                             self.var.sum_soilStor[0] + self.var.sum_soilStor[1] + self.var.sum_soilStor[2]
        self.var.totalSto = self.var.SnowCover + self.var.sum_interceptStor + self.var.sum_topWaterLayer + \
                            self.var.sum_soilStor[0] + self.var.sum_soilStor[1] + self.var.sum_soilStor[2]
        self.var.totalET = self.var.sum_actTransTotal + self.var.sum_actBareSoilEvap + self.var.sum_openWaterEvap + self.var.sum_interceptEvap

        #print self.var.totalSoil,self.var.soilStor[0][1],self.var.soilStor[1][1], self.var.soilStor[2][1],
        i= 1

# --------------------------------------------------------------------


        if option['calcWaterBalance']:
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.Rain,self.var.SnowMelt],  # In
                [self.var.sum_availWaterInfiltration,self.var.sum_interceptEvap],  # Out
                [preIntStor],   # prev storage
                [self.var.sum_interceptStor],
                "InterAll", False)

        if option['calcWaterBalance']:
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.sum_availWaterInfiltration,self.var.sum_capRiseFromGW,self.var.sum_irrGrossDemand],                             # In  self.var.irrGrossDemand
                [self.var.sum_directRunoff,self.var.sum_interflow, self.var.sum_percToGW, \
                 self.var.sum_PrefFlow, self.var.sum_actTransTotal, \
                 self.var.sum_actBareSoilEvap,self.var.sum_openWaterEvap],                                                                # Out
                [preTopWaterLayer,preStor1,preStor2,preStor3],                                       # prev storage
                [self.var.sum_topWaterLayer,self.var.sum_soilStor[0], self.var.sum_soilStor[1], self.var.sum_soilStor[2]],
                "Soil_sum1", False)  #True


        if option['calcWaterBalance']:
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.Rain,self.var.SnowMelt,self.var.sum_capRiseFromGW,self.var.sum_irrGrossDemand],                             # In  self.var.irrGrossDemand
                [self.var.sum_directRunoff,self.var.sum_interflow, self.var.sum_percToGW, \
                 self.var.sum_PrefFlow, self.var.sum_actTransTotal, \
                 self.var.sum_actBareSoilEvap,self.var.sum_openWaterEvap, self.var.sum_interceptEvap],                                                                # Out
                [preTopWaterLayer,preStor1,preStor2,preStor3,preIntStor],                                       # prev storage
                [self.var.sum_topWaterLayer,self.var.sum_soilStor[0], self.var.sum_soilStor[1], self.var.sum_soilStor[2], self.var.sum_interceptStor],
                "Soil_sum2", False)

        if option['calcWaterBalance']:
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.Precipitation,self.var.sum_capRiseFromGW,self.var.sum_irrGrossDemand],                             # In
                [self.var.sum_directRunoff,self.var.sum_interflow, self.var.sum_percToGW, \
                 self.var.sum_PrefFlow, self.var.sum_actTransTotal, \
                 self.var.sum_actBareSoilEvap,self.var.sum_openWaterEvap, self.var.sum_interceptEvap],                                                                # Out
                [self.var.prevSnowCover, preTopWaterLayer,preStor1,preStor2,preStor3,preIntStor],                                       # prev storage
                [self.var.SnowCover, self.var.sum_topWaterLayer,self.var.sum_soilStor[0], self.var.sum_soilStor[1], self.var.sum_soilStor[2], self.var.sum_interceptStor],
                "Soil_All", False)  #True
        i = 1




        #a = decompress(self.var.sumsum_Precipitation)
        #b = cellvalue(a,81,379)
        #print self.var.sum_directRunoff
        #report(decompress(self.var.sumsum_Precipitation), "c:\work\output\Prsum.map")
        #report(decompress(self.var.sumsum_gwRecharge), "c:\work\output\gwrsum.map")



