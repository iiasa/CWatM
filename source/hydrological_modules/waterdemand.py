# -------------------------------------------------------------------------
# Name:        Waterdemand module
# Purpose:
#
# Author:      PB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class waterdemand(object):

    """
    # ************************************************************
    # ***** SOIL *****************************************
    # ************************************************************
    """

    def __init__(self, waterdemand_variable):
        self.var = waterdemand_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the groundwater module
        """
        if option['includeWaterDemandDomInd']:
           #self.var.recessionCoeff = loadmap('recessionCoeff')

           # Add  zones at which water allocation (surface and groundwater allocation) is determined
           if option['usingAllocSegments']:
               self.var.allocSegments = loadmap('allocSegments').astype(np.int)
               self.var.segmentArea = npareatotal(self.var.cellArea, self.var.allocSegments)
        else:
            self.var.reducedGroundWaterAbstraction = 0
            self.var.nonIrrGrossDemand = 0
            self.var.nonIrrReturnFlowFraction = 0



# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the soil module
        """

        # get NON-Irrigation GROSS water demand and its return flow fraction
        # obtainNonIrrWaterDemand landsurface 487

        if option['includeWaterDemandDomInd']:
            # industry water demand
            if dateVar['newStart'] or dateVar['newYear']:
                self.var.industryGrossDemand = readnetcdf2(binding['industryWaterDemandFile'], dateVar['currDate'], "yearly", value="industryGrossDemand")
                self.var.industryNettoDemand = readnetcdf2(binding['industryWaterDemandFile'], dateVar['currDate'], "yearly", value="industryNettoDemand")
                self.var.industryGrossDemand = np.where(self.var.industryGrossDemand > self.var.InvCellArea, self.var.industryGrossDemand, 0.0)
                self.var.industryNettoDemand = np.where(self.var.industryNettoDemand > self.var.InvCellArea, self.var.industryNettoDemand, 0.0)

            # domestic water demand
            if dateVar['newStart'] or dateVar['newMonth']:
                self.var.domesticGrossDemand = readnetcdf2(binding['domesticWaterDemandFile'], dateVar['currDate'], "monthly", value="domesticGrossDemand")
                self.var.domesticNettoDemand = readnetcdf2(binding['domesticWaterDemandFile'], dateVar['currDate'], "monthly", value="domesticNettoDemand")
                # avoid small values (less than 1 m3):
                self.var.domesticGrossDemand = np.where(self.var.domesticGrossDemand > self.var.InvCellArea, self.var.domesticGrossDemand, 0.0)
                self.var.domesticNettoDemand = np.where(self.var.domesticNettoDemand > self.var.InvCellArea, self.var.domesticNettoDemand, 0.0)

                # total (potential) non irrigation water demand
                self.var.potentialNonIrrGrossWaterDemand = self.var.domesticGrossDemand + self.var.industryGrossDemand
                self.var.potentialNonIrrNettoWaterDemand = np.minimum(self.var.potentialNonIrrGrossWaterDemand, self.var.domesticNettoDemand + self.var.industryNettoDemand)

                # fraction of return flow from domestic and industrial water demand
                self.var.nonIrrReturnFlowFraction = getValDivZero((self.var.potentialNonIrrGrossWaterDemand - self.var.potentialNonIrrNettoWaterDemand),\
                                         (self.var.potentialNonIrrGrossWaterDemand), 1E-39)
            """
            self.var.domesticGrossDemand = globals.inZero
            self.var.domesticNettoDemand = globals.inZero
            self.var.industryGrossDemand = globals.inZero
            self.var.industryNettoDemand = globals.inZero
            self.var.potentialNonIrrGrossWaterDemand = globals.inZero
            self.var.potentialNonIrrNettoWaterDemand = globals.inZero
            self.var.nonIrrReturnFlowFraction = 1e-39
            """

            # ---------------------------------------------------------------------------------------
            # partitioningGroundSurfaceAbstraction  - landsurface 615
            # partitioning abstraction sources: groundwater and surface water
            # Inge's principle: partitioning based on local average baseflow (m3/s) and upstream average discharge (m3/s)

            # estimates of fractions of groundwater and surface water abstractions

            averageBaseflowInput =  np.maximum(0.0,self.var.avgBaseflow)
            averageUpstreamInput = np.bincount(self.var.downstruct, weights = self.var.avgDischarge)[:-1]
            # this function replace the pc raster function upstream
            # averageUpstreamInput = upstream(self.var.Ldd, decompress(self.var.avgDischarge))

            averageUpstreamInput = np.maximum(0.0, averageUpstreamInput)

            if option['usingAllocSegments']:
            #if self.var.usingAllocSegments:
                averageBaseflowInput = npareaaverage(averageBaseflowInput, self.var.allocSegments)
                averageUpstreamInput = npareamaximum(averageUpstreamInput, self.var.allocSegments)

            #else:
            #     print("WARNING! Water demand can only be satisfied by local source.")

            self.var.swAbstractionFraction = np.maximum(0.0, np.minimum(1.0,averageUpstreamInput / np.maximum(1e-20,averageUpstreamInput + averageBaseflowInput)))
            self.var.swAbstractionFraction = np.minimum(1.0,np.maximum(0.0, self.var.swAbstractionFraction))
            self.var.swAbstractionFraction[np.isnan(self.var.swAbstractionFraction)] = 0
            self.var.swAbstractionFraction = np.round(self.var.swAbstractionFraction,2)

            self.var.gwAbstractionFraction = 1.0 - self.var.swAbstractionFraction

            #self.var.swAbstractionFraction = 0.5
            #self.var.gwAbstractionFraction = 0.5

            # report(decompress(self.var.discharge), "C:\work\output/q1.map")

    def dynamic_waterdemand(self,coverType, No):

        # ------------------------------------------
        if option['includeWaterDemandDomInd']:
            # non irrigation water demand
            self.var.nonIrrGrossDemand = self.var.potentialNonIrrGrossWaterDemand.copy()

            # irrigation water demand for paddy and non-paddy (m)
            self.var.irrGrossDemand[No] = 0.0
            if coverType == 'irrPaddy':
                self.var.irrGrossDemand[No] = np.where(self.var.cropKC > 0.75, np.maximum(0.0, self.var.minTopWaterLayer[No] - (self.var.topWaterLayer[No] + self.var.availWaterInfiltration[No])), 0.)
                # a function of cropKC (evaporation and transpiration),
                #  topWaterLayer (water available in the irrigation field), and netLqWaterToSoil (amout of liquid precipitation)
                self.var.irrGrossDemand[No] = np.where(self.var.irrGrossDemand[No] > self.var.InvCellArea, self.var.irrGrossDemand[No], 0)  # ignore demand if less than 1 m3
            if coverType == 'irrNonPaddy':
                adjDeplFactor = np.maximum(0.1, np.minimum(0.8, (self.var.cropDeplFactor[No] + 40. * (0.005 - self.var.totalPotET[No]))))
                self.var.irrGrossDemand[No] = np.where(self.var.cropKC > 0.20, np.where(self.var.readAvlWater < adjDeplFactor * self.var.totAvlWater[No],
                            np.maximum(0.0, self.var.totAvlWater[No] - self.var.readAvlWater), 0.), 0.)
                # a function of cropKC and totalPotET (evaporation and transpiration),
                #    readAvlWater (available water in the root zone), and
                #    netLqWaterToSoil (amout of liquid precipitation)

                # ignore demand if less than 1 m3
                self.var.irrGrossDemand[No] = np.where(self.var.irrGrossDemand[No] > self.var.InvCellArea, self.var.irrGrossDemand[No], 0)

            # totalGrossDemand (m): total maximum (potential) water demand: irrigation and non irrigation
            totalGrossDemand = self.var.nonIrrGrossDemand + self.var.irrGrossDemand[No]
            self.var.totalPotentialGrossDemand[No] = totalGrossDemand .copy()
            # self.var.totalPotentialGrossDemand[No] = globals.inZero.copy()


            # surface water abstraction that can be extracted to fulfil totalGrossDemand
            # - based on readAvlChannelStorage
            # - and swAbstractionFraction * totalPotGrossDemand
            #
            if option['usingAllocSegments']:
                # using zone/segment at which supply network is defined

                # gross demand volume in each cell (unit: m3)
                cellVolGrossDemand = totalGrossDemand * self.var.cellArea
                # total gross demand volume in each segment/zone (unit: m3)
                segTtlGrossDemand = npareatotal(cellVolGrossDemand, self.var.allocSegments)

                # total available surface water volume in each segment/zone  (unit: m3)
                segAvlSurfaceWater = npareatotal(self.var.readAvlChannelStorage, self.var.allocSegments)

                # total actual surface water abstraction volume in each segment/zone (unit: m3)
                # scale (if available water is limited)
                ADJUST = self.var.swAbstractionFraction * segTtlGrossDemand
                ADJUST = np.where(ADJUST > 0.0, np.minimum(1.0, np.maximum(0.0, segAvlSurfaceWater) / ADJUST), 0.)
                segActSurWaterAbs = ADJUST * self.var.swAbstractionFraction * segTtlGrossDemand

                # actual surface water abstraction volume in each cell (unit: m3)
                volActSurfaceWaterAbstract = np.where(segAvlSurfaceWater > 0.0, self.var.readAvlChannelStorage / segAvlSurfaceWater, 0.0) * segActSurWaterAbs
                volActSurfaceWaterAbstract = np.minimum(self.var.readAvlChannelStorage, volActSurfaceWaterAbstract)
                # avoid small values (to avoid rounding error)
                volActSurfaceWaterAbstract = np.where(volActSurfaceWaterAbstract > 1.0, volActSurfaceWaterAbstract, 0)

                # actual surface water abstraction volume in meter (unit: m)
                self.var.actSurfaceWaterAbstract[No] = volActSurfaceWaterAbstract / self.var.cellArea
                # total actual surface water abstraction volume in each segment/zone (unit: m3) - recalculated to avoid rounding error
                segActSurWaterAbs = npareatotal(self.var.actSurfaceWaterAbstract[No] * self.var.cellArea, self.var.allocSegments)

                # allocation surface water abstraction volume to each cell (unit: m3)
                volAllocSurfaceWaterAbstract = np.where(segTtlGrossDemand > 0.0, cellVolGrossDemand / segTtlGrossDemand, 0.0) * segActSurWaterAbs
                # allocation surface water abstraction in meter (unit: m)
                self.var.allocSurfaceWaterAbstract[No] = volAllocSurfaceWaterAbstract / self.var.cellArea

                if option['calcWaterBalance']:
                    abstraction = npareatotal(self.var.actSurfaceWaterAbstract *  self.var.cellArea,self.var.allocSegments) / self.var.segmentArea
                    allocation = npareatotal(self.var.allocSurfaceWaterAbstract * self.var.cellArea,self.var.allocSegments) / self.var.segmentArea

                    self.var.waterbalance_module.waterBalanceCheck(
                        [abstraction],  # In
                        [allocation],  # Out
                        [globals.inZero],
                        [globals.inZero],
                        "surface water allocation per zone/segments", True)


            else:
                # only local surface water abstraction is allowed (network is only within a cell) # unit: m
                if No < 4:
                    self.var.actSurfaceWaterAbstract[No] = np.minimum(self.var.readAvlChannelStorage * self.var.InvCellArea, self.var.swAbstractionFraction * self.var.totalPotentialGrossDemand[No])
                else:
                    # if land cover type is sealed or water
                    self.var.actSurfaceWaterAbstract[No] = np.minimum(self.var.readAvlChannelStorage * self.var.InvCellArea,  self.var.totalPotentialGrossDemand[No])
                self.var.allocSurfaceWaterAbstract[No] = self.var.actSurfaceWaterAbstract[No].copy()


            self.var.potGroundwaterAbstract[No] = np.maximum(0.0, self.var.totalPotentialGrossDemand[No] - self.var.allocSurfaceWaterAbstract[No])  # unit: m


            # if limitAbstraction == 'True'
            # - no fossil gwAbstraction.
            # - limitting abstraction with avlWater in channelStorage (m3) and storGroundwater (m)
            # - water demand may be reduced

            # variable to reduce/limit groundwater abstraction (> 0 if limitAbstraction = True)
            self.var.reducedGroundWaterAbstraction = 0.0

            if option['limitAbstraction'] and (No < 4):

                #print ('Fossil groundwater abstractions are NOT allowed.')
                # calculate renewableAvlWater (non-fossil groundwater and channel)
                renewableAvlWater = self.var.readAvlStorGroundwater + self.var.allocSurfaceWaterAbstract[No]

                # reducing nonIrrGrossDemand if renewableAvlWater < maxGrossDemand
                with np.errstate(invalid='ignore', divide='ignore'):
                    h = np.where(totalGrossDemand > 0, renewableAvlWater/totalGrossDemand, 1e-20)
                self.var.nonIrrGrossDemand = np.where(totalGrossDemand > 0.0, np.minimum(1.0, np.maximum(0.0, h)) * self.var.nonIrrGrossDemand, 0.0)
                # reducing irrGrossWaterDemand if maxGrossDemand < renewableAvlWater
                self.var.irrGrossDemand[No] = np.where(totalGrossDemand > 0.0, np.minimum(1.0, np.maximum(0.0, h)) * self.var.irrGrossDemand[No], 0.0)


                # potential groundwater abstraction (must be equal to actual no fossil groundwater abstraction)
                self.var.potGroundwaterAbstract[No] = self.var.nonIrrGrossDemand + self.var.irrGrossDemand[No] - self.var.allocSurfaceWaterAbstract[No]
                # variable to reduce/limit gw abstraction (to ensure that there are enough water for supplying nonIrrGrossDemand + irrGrossDemand)
    #            self.var.reducedGroundWaterAbstraction[No] = self.var.potGroundwaterAbstract[No].copy()

                ii =1

            #else:
            #    print ('Fossil groundwater abstractions are allowed.')








