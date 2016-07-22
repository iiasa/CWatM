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

           i = 1
           # TODO : add  zones at which water allocation (surface and groundwater allocation) is determined
           #  landSurface.py lines 317ff



# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the soil module
        """

        # get NON-Irrigation GROSS water demand and its return flow fraction
        # obtainNonIrrWaterDemand landsurface 487

        # domestic water demand
        self.var.domesticGrossDemand = readnetcdf2(binding['domesticWaterDemandFile'], self.var.CalendarDate, "monthly", value="domesticGrossDemand")
        self.var.domesticNettoDemand = readnetcdf2(binding['domesticWaterDemandFile'], self.var.CalendarDate, "monthly", value="domesticNettoDemand")
        # industry water demand
        self.var.industryGrossDemand = readnetcdf2(binding['industryWaterDemandFile'], self.var.CalendarDate, "yearly", value="industryGrossDemand")
        self.var.industryNettoDemand = readnetcdf2(binding['industryWaterDemandFile'], self.var.CalendarDate, "yearly", value="industryNettoDemand")

        # avoid small values (less than 1 m3):
        self.var.domesticGrossDemand = np.where(self.var.domesticGrossDemand > self.var.InvCellArea, self.var.domesticGrossDemand, 0.0)
        self.var.domesticNettoDemand = np.where(self.var.domesticNettoDemand > self.var.InvCellArea, self.var.domesticNettoDemand, 0.0)
        self.var.industryGrossDemand = np.where(self.var.industryGrossDemand > self.var.InvCellArea, self.var.industryGrossDemand, 0.0)
        self.var.industryNettoDemand = np.where(self.var.industryNettoDemand > self.var.InvCellArea, self.var.industryNettoDemand, 0.0)

        # total (potential) non irrigation water demand
        self.var.potentialNonIrrGrossWaterDemand = self.var.domesticGrossDemand + self.var.industryGrossDemand
        self.var.potentialNonIrrNettoWaterDemand = np.minimum(self.var.potentialNonIrrGrossWaterDemand, self.var.domesticNettoDemand + self.var.industryNettoDemand)

        # fraction of return flow from domestic and industrial water demand
        self.var.nonIrrReturnFlowFraction = getValDivZero((self.var.potentialNonIrrGrossWaterDemand - self.var.potentialNonIrrNettoWaterDemand),\
                                     (self.var.potentialNonIrrGrossWaterDemand), 1E-39)

        # ---------------------------------------------------------------------------------------
        # partitioningGroundSurfaceAbstraction  - landsurface 615
        # partitioning abstraction sources: groundwater and surface water
        # Inge's principle: partitioning based on local average baseflow (m3/s) and upstream average discharge (m3/s)

        # estimates of fractions of groundwater and surface water abstractions
        """
        averageBaseflowInput = routing.avgBaseflow
        averageUpstreamInput = pcr.upstream(routing.lddMap, routing.avgDischarge)

        if self.var.usingAllocSegments:
            averageBaseflowInput = np.maximum(0.0, pcr.ifthen(self.varlandmask, averageBaseflowInput))
            averageUpstreamInput = np.maximum(0.0, pcr.ifthen(self.var.landmask, averageUpstreamInput))
            averageBaseflowInput = pcr.cover(pcr.areaaverage(pcr.cover(averageBaseflowInput, 0.0), self.var.allocSegments), 0.0)
            averageUpstreamInput = pcr.cover(pcr.areamaximum(pcr.cover(averageUpstreamInput, 0.0), self.var.allocSegments), 0.0)

        else:
             print("WARNING! Water demand can only be satisfied by local source.")

        swAbstractionFraction = np.maximum(0.0, np.minimum(1.0,averageUpstreamInput / np.maximum(1e-20,averageUpstreamInput + averageBaseflowInput)))
        swAbstractionFraction = pcr.cover(swAbstractionFraction, 0.0)
        swAbstractionFraction = pcr.roundup(swAbstractionFraction * 100.) / 100.
        swAbstractionFraction = np.maximum(0.0, swAbstractionFraction)
        swAbstractionFraction = np.minimum(1.0, swAbstractionFraction)

        gwAbstractionFraction = 1.0 - swAbstractionFraction
        """
        self.var.swAbstractionFraction = 0.5
        self.var.gwAbstractionFraction = 0.5


    def dynamic_waterdemand(self,coverType, No):

        # ------------------------------------------
        # non irrigation water demand
        nonIrrGrossDemand = self.var.potentialNonIrrGrossWaterDemand

        # irrigation water demand for paddy and non-paddy (m)
        self.var.irrGrossDemand = 0.0
        if coverType == 'irrPaddy':
            self.var.irrGrossDemand = np.where(self.var.cropKC > 0.75, np.maximum(0.0, self.var.minTopWaterLayer[No] - (self.var.topWaterLayer[No] + self.var.availWaterInfiltration[No])), 0.)
            # a function of cropKC (evaporation and transpiration),
            #  topWaterLayer (water available in the irrigation field), and netLqWaterToSoil (amout of liquid precipitation)
            self.var.irrGrossDemand = np.where(self.var.irrGrossDemand > (1.0 / self.var.cellArea), self.var.irrGrossDemand, 0)  # ignore demand if less than 1 m3
        if coverType == 'irrNonPaddy':
            adjDeplFactor = np.maximum(0.1, np.minimum(0.8, (self.var.cropDeplFactor[No] + 40. * (0.005 - self.var.totalPotET))))
            self.var.irrGrossDemand = np.where(self.var.cropKC > 0.20, np.where(self.var.readAvlWater < adjDeplFactor * self.var.totAvlWater, np.maximum(0.0, self.var.totAvlWater - self.var.readAvlWater), 0.), 0.)
            # a function of cropKC and totalPotET (evaporation and transpiration),
            #    readAvlWater (available water in the root zone), and
            #    netLqWaterToSoil (amout of liquid precipitation)
            self.var.irrGrossDemand = np.where(self.var.irrGrossDemand > (1.0 / self.var.cellArea), self.var.irrGrossDemand, 0)  # ignore demand if less than 1 m3

        # totalGrossDemand (m): total maximum (potential) water demand: irrigation and non irrigation
        totalGrossDemand = nonIrrGrossDemand + self.var.irrGrossDemand
        self.var.totalPotentialGrossDemand = totalGrossDemand

        # surface water abstraction that can be extracted to fulfil totalGrossDemand
        # - based on readAvlChannelStorage
        # - and swAbstractionFraction * totalPotGrossDemand
        #
        """
        if self.var.usingAllocSegments:  # using zone/segment at which supply network is defined

            allocSegments = pcr.ifthen(self.var.landmask, allocSegments)

            # gross demand volume in each cell (unit: m3)
            cellVolGrossDemand = totalGrossDemand * routing.cellArea

            # total gross demand volume in each segment/zone (unit: m3)
            segTtlGrossDemand = pcr.areatotal(pcr.cover(cellVolGrossDemand, 0), allocSegments)

            # total available surface water volume in each segment/zone  (unit: m3)
            segAvlSurfaceWater = pcr.areatotal(pcr.cover(routing.readAvlChannelStorage, 0), allocSegments)

            # total actual surface water abstraction volume in each segment/zone (unit: m3)
            #
            swAbstractionFraction = np.minimum(1.0, swAbstractionFraction)
            #
            # scale (if available water is limited)
            ADJUST = swAbstractionFraction * segTtlGrossDemand
            ADJUST = np.where(ADJUST > 0.0, \
                                    np.minimum(1.0, np.maximum(0.0, segAvlSurfaceWater) / ADJUST), 0.)
            #
            ADJUST = pcr.rounddown(ADJUST * 100.) / 100.
            ADJUST = np.maximum(0.0, ADJUST)
            ADJUST = np.minimum(1.0, ADJUST)
            #
            segActSurWaterAbs = ADJUST * swAbstractionFraction * segTtlGrossDemand  # unit: m3

            # actual surface water abstraction volume in each cell (unit: m3)
            volActSurfaceWaterAbstract = np.where(segAvlSurfaceWater > 0.0, \
                                                        routing.readAvlChannelStorage / \
                                                        segAvlSurfaceWater, 0.0) * \
                                         (segActSurWaterAbs)
            volActSurfaceWaterAbstract = np.minimum(routing.readAvlChannelStorage, volActSurfaceWaterAbstract)  # unit: m3
            # avoid small values (to avoid rounding error)
            volActSurfaceWaterAbstract = np.where(volActSurfaceWaterAbstract > 1.0, volActSurfaceWaterAbstract, 0)
            volActSurfaceWaterAbstract = pcr.cover(volActSurfaceWaterAbstract, 0.0)

            # actual surface water abstraction volume in meter (unit: m)
            self.var.actSurfaceWaterAbstract = pcr.ifthen(self.var.landmask, volActSurfaceWaterAbstract) / \
                                           routing.cellArea  # unit: m

            # total actual surface water abstraction volume in each segment/zone (unit: m3) - recalculated to avoid rounding error
            segActSurWaterAbs = pcr.areatotal(self.var.actSurfaceWaterAbstract * routing.cellArea,
                                              allocSegments)  # unit: m3

            # allocation surface water abstraction volume to each cell (unit: m3)
            self.var.volAllocSurfaceWaterAbstract = np.where(segTtlGrossDemand > 0.0,
                                                               cellVolGrossDemand / segTtlGrossDemand, 0.0) * \
                                                segActSurWaterAbs  # unit: m3
            self.var.volAllocSurfaceWaterAbstract = pcr.cover(self.var.volAllocSurfaceWaterAbstract,
                                                          0.0)  # TODO: Do we really have to cover?

            # allocation surface water abstraction in meter (unit: m)
            self.var.allocSurfaceWaterAbstract = pcr.ifthen(self.var.landmask, self.var.volAllocSurfaceWaterAbstract) / \
                                             routing.cellArea  # unit: m

            if self.var.debugWaterBalance == str('True'):
                abstraction = pcr.cover(pcr.areatotal(pcr.cover(self.var.actSurfaceWaterAbstract * routing.cellArea, 0.0),
                                                      self.var.allocSegments) / self.var.segmentArea, 0.0)
                allocation = pcr.cover(pcr.areatotal(pcr.cover(self.var.allocSurfaceWaterAbstract * routing.cellArea, 0.0),
                                                     self.var.allocSegments) / self.var.segmentArea, 0.0)

                vos.waterBalanceCheck([abstraction], \
                                      [allocation], \
                                      [pcr.scalar(0.0)], \
                                      [pcr.scalar(0.0)], \
                                      'surface water allocation per zone/segment in land cover level (PS: Error here may be caused by rounding error.)', \
                                      True, \
                                      "", threshold=5e-3)

        else:
        """
        # alooocation has to be done!! TODO
        # to be changed  TODO
        self.var.readAvlChannelStorage = globals.inZero.copy()

        # only local surface water abstraction is allowed (network is only within a cell)
        self.var.actSurfaceWaterAbstract = np.minimum(self.var.readAvlChannelStorage / self.var.cellArea, self.var.swAbstractionFraction * totalGrossDemand)  # unit: m
        self.var.allocSurfaceWaterAbstract = self.var.actSurfaceWaterAbstract  # unit: m

        # end of else

        self.var.potGroundwaterAbstract = np.maximum(0.0, totalGrossDemand - self.var.allocSurfaceWaterAbstract)  # unit: m

        # if limitAbstraction == 'True'
        # - no fossil gwAbstraction.
        # - limitting abstraction with avlWater in channelStorage (m3) and storGroundwater (m)
        # - water demand may be reduced
        #
        self.var.reducedGroundWaterAbstraction = 0.0  # variable to reduce/limit groundwater abstraction (> 0 if limitAbstraction = True)
        #
        """
        if self.var.limitAbstraction == 'True':

            print ('Fossil groundwater abstractions are NOT allowed.')

            # calculate renewableAvlWater (non-fossil groundwater and channel)
            #
            renewableAvlWater = groundwater.readAvlStorGroundwater + self.var.allocSurfaceWaterAbstract

            # reducing nonIrrGrossDemand if renewableAvlWater < maxGrossDemand
            #
            self.var.nonIrrGrossDemand = \
                np.where(totalGrossDemand > 0.0, \
                               np.minimum(1.0, np.maximum(0.0, \
                                                    vos.getValDivZero(renewableAvlWater, totalGrossDemand,
                                                                      vos.smallNumber))) * self.var.nonIrrGrossDemand, 0.0)

            # reducing irrGrossWaterDemand if maxGrossDemand < renewableAvlWater
            #
            self.var.irrGrossDemand = \
                np.where(totalGrossDemand > 0.0, \
                               np.minimum(1.0, np.maximum(0.0, \
                                                    vos.getValDivZero(renewableAvlWater, totalGrossDemand,
                                                                      vos.smallNumber))) * self.var.irrGrossDemand, 0.0)

            # potential groundwater abstraction (must be equal to actual no fossil groundwater abstraction)
            self.var.potGroundwaterAbstract = self.var.nonIrrGrossDemand + self.var.irrGrossDemand - self.var.allocSurfaceWaterAbstract

            # variable to reduce/limit gw abstraction (to ensure that there are enough water for supplying nonIrrGrossDemand + irrGrossDemand)
            self.var.reducedGroundWaterAbstraction = self.var.potGroundwaterAbstract

        else:
            print ('Fossil groundwater abstractions are allowed.')
        """







