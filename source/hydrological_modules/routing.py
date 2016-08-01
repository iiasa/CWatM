# -------------------------------------------------------------------------
# Name:        Routing module
# Purpose:
#
# Author:      PB
#
# Created:     01/08/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class routing(object):

    """
    # ************************************************************
    # ***** ROUTING      *****************************************
    # ************************************************************
    """

    def __init__(self, routing_variable):
        self.var = routing_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the routing module
        Tdo: might be necessary to cover all variables = put 0 instead of missing value
        """
        self.var.Ldd = lddmask(loadmap('Ldd',pcr=True,lddflag=True), self.var.MaskMap)
        # Cut ldd to size of MaskMap
        # Prevents 'unsound' ldd if MaskMap covers sub-area of ldd

        self.var.Ldd = lddrepair(self.var.Ldd)

        # self.var.cellArea or self.var.cellAreaPcr as pcraster map
        # self.var.cellLength or self.var.cellLengthPcr as pcraster map
        cellsize = clone().cellSize()

        if option['gridSizeUserDefined']:
            # cellLength (m) is approximated cell diagonal
            # assuming cellsize is in degree, each minute is 1852 min
            cellvertical = cellsize * 60 * 1852
            self.var.cellLength = np.sqrt((self.var.cellArea / cellvertical) ** 2 + cellvertical **2)
        else:
            self.var.cellLength = cellsize
        self.var.cellLengthPcr = decompress(self.var.cellLength)




        self.var.gradient = loadmap('gradient')
        # the channel gradient must be >= minGradient
        self.var.gradient = np.maximum(0.000005,self.var.gradient)

        # mannings roughness (set fixed to 0.04)
        self.var.manningsN = loadmap('manningsN')

        # filename composite crop factors for WaterBodies (1 per month):
        self.var.fileCropKC_File = binding['cropCoefficientWaterNC']

        # For method accuTravelTime
        nrCellsDownstream = ldddist(self.var.Ldd, self.var.Ldd == 5, 1.)
        distanceDownstream = ldddist(self.var.Ldd, self.var.Ldd == 5, self.var.cellLengthPcr)
        channelLengthDownstream = (self.var.cellLengthPcr + distanceDownstream) / (nrCellsDownstream + 1)  # unit: m
        self.var.eta = 0.25
        self.var.nu = 0.40
        self.var.tau = 8.00
        self.var.phi = 0.58


        if option['gridSizeUserDefined']:
            # unit: m/arcDegree
            self.var.dist2celllength = channelLengthDownstream / cellsize
        else:
            # unit: m
            self.var.dist2celllength = channelLengthDownstream

        # Initial conditions

        # channelStorage (m3) includes all storages at channels and water bodies (lakes & reservoirs)
        self.var.channelStorage = loadmap('channelStorageIni')
        self.var.readAvlChannelStorage = loadmap('readAvlChannelStorageIni')
        self.var.timestepsToAvgDischarge = loadmap('timestepsToAvgDischargeIni')
        self.var.avgDischarge = loadmap('avgChannelDischargeIni')    # in m3/s
        self.var.avgBaseflow = loadmap('avgBaseflowIni')
        self.var.riverbedExchange = loadmap('riverbedExchangeIni')

        self.var.readAvlChannelStorage = np.minimum(self.var.readAvlChannelStorage, self.var.channelStorage)

        # make sure that timestepsToAvgDischarge is consistent (or the same) for the entire map:
        self.var.timestepsToAvgDischarge = np.amax(self.var.timestepsToAvgDischarge)   # as pcraster.mapmaximum

        i  = 1
 
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the routing module
        """

        def getRoutingParamAvgDischarge(self, avgDischarge, dist2celllength):
            # obtain routing parameters based on average (longterm) discharge
            # output: channel dimensions and
            #         characteristicDistance (for accuTravelTime input)

            yMean = self.eta * pow(avgDischarge, self.nu)  # avgDischarge in m3/s
            wMean = self.tau * pow(avgDischarge, self.phi)

            yMean = pcr.max(yMean, 0.000000001)  # channel depth (m)
            wMean = pcr.max(wMean, 0.000000001)  # channel width (m)
            yMean = pcr.cover(yMean, 0.000000001)
            wMean = pcr.cover(wMean, 0.000000001)

            # characteristicDistance (dimensionless)
            # - This will be used for accutraveltimeflux & accutraveltimestate
            # - discharge & storage = accutraveltimeflux & accutraveltimestate
            # - discharge = the total amount of material flowing through the cell (m3/s)
            # - storage   = the amount of material which is deposited in the cell (m3)
            #
            characteristicDistance =  ((yMean * wMean) /  (wMean + 2 * yMean)) ** self.var.twothird * \
                ((self.gradient) ** (0.5)) / self.manningsN * vos.secondsPerDay()  # meter/day

            characteristicDistance = pcr.max((self.cellSizeInArcDeg) * 0.000000001, characteristicDistance / dist2celllength)  # arcDeg/day

            # PS: In accutraveltime function:
            #     If characteristicDistance (velocity) = 0 then:
            #     - accutraveltimestate will give zero
            #     - accutraveltimeflux will be very high

            # TODO: Consider to use downstreamdist function.

            return (yMean, wMean, characteristicDistance)

        # ---------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------


        def accuTravelTime(self, currTimeStep):

            usedLDD = self.lddMap

            # at cells where lakes and/or reservoirs defined, move channelStorage to waterBodyStorage
            storageAtLakeAndReservoirs = \
                pcr.ifthen(pcr.scalar(self.WaterBodies.waterBodyIds) > 0.,
                           self.channelStorage)
            storageAtLakeAndReservoirs = pcr.cover(storageAtLakeAndReservoirs, 0.0)
            self.channelStorage -= storageAtLakeAndReservoirs  # unit: m3

            # update waterBodyStorage (inflow, storage and outflow)
            self.WaterBodies.update(storageAtLakeAndReservoirs, \
                                    self.timestepsToAvgDischarge, \
                                    self.maxTimestepsToAvgDischargeShort, \
                                    self.maxTimestepsToAvgDischargeLong, \
                                    currTimeStep)

            # transfer outflow from lakes and/or reservoirs to channelStorages
            waterBodyOutflow = pcr.cover( \
                pcr.ifthen( \
                    self.WaterBodies.waterBodyOut,
                    self.WaterBodies.waterBodyOutflow), 0.0)  # unit: m3/day
            #
            # distribute outflow to water body storage
            waterBodyOutflow = pcr.areaaverage(waterBodyOutflow, self.WaterBodies.waterBodyIds)
            waterBodyOutflow = pcr.ifthen( \
                pcr.scalar(self.WaterBodies.waterBodyIds) > 0.0,
                waterBodyOutflow)  # unit: m3/day
            waterBodyOutflow = pcr.cover(waterBodyOutflow, 0.0)
            #
            self.channelStorage += waterBodyOutflow  # TODO: Move waterBodyOutflow according to water body discharge (velocity)

            # obtain water body storages (for reporting)
            self.waterBodyStorage = pcr.ifthen(self.landmask, \
                                               pcr.ifthen( \
                                                   pcr.scalar(self.WaterBodies.waterBodyIds) > 0., \
                                                   self.WaterBodies.waterBodyStorage))  # m3
            # as well as outflows from water bodies (for reporting)
            self.waterBodyOutDisc = pcr.ifthen(self.landmask, \
                                               pcr.ifthen( \
                                                   pcr.scalar(self.WaterBodies.waterBodyIds) > 0., \
                                                   self.WaterBodies.waterBodyOutflow)) / \
                                    vos.secondsPerDay()  # m3/s

            # channelStorage ROUTING:
            channelStorageForAccuTravelTime = self.channelStorage
            channelStorageForAccuTravelTime = pcr.cover(channelStorageForAccuTravelTime,
                                                        0.0)  # TODO: check why do we have to use the "cover" operation.
            #
            characteristicDistanceForAccuTravelTime = pcr.cover(self.characteristicDistance,
                                                                0.001 * self.cellSizeInArcDeg)
            characteristicDistanceForAccuTravelTime = pcr.max(0.001 * self.cellSizeInArcDeg,
                                                              self.characteristicDistance)

            # self.Q = channel discharge (m3/day)
            self.Q = pcr.accutraveltimeflux(usedLDD, \
                                            channelStorageForAccuTravelTime, \
                                            characteristicDistanceForAccuTravelTime)
            self.Q = pcr.cover(self.Q, 0.0)
            # for very small velocity (i.e. characteristicDistanceForAccuTravelTime), discharge can be missing value.
            # see: http://sourceforge.net/p/pcraster/bugs-and-feature-requests/543/
            #      http://karssenberg.geo.uu.nl/tt/TravelTimeSpecification.htm

            # updating channelStorage (after routing)
            self.channelStorage = pcr.accutraveltimestate(usedLDD, \
                                                          channelStorageForAccuTravelTime, \
                                                          characteristicDistanceForAccuTravelTime)

            # after routing, return waterBodyStorage to channelStorage
            waterBodyStorageTotal = \
                pcr.ifthen(pcr.scalar(self.WaterBodies.waterBodyIds) > 0.,
                           pcr.areaaverage( \
                               pcr.ifthen(self.landmask, self.WaterBodies.waterBodyStorage), \
                               pcr.ifthen(self.landmask, self.WaterBodies.waterBodyIds)) + \
                           pcr.areatotal(pcr.cover( \
                               pcr.ifthen(self.landmask, self.channelStorage), 0.0), \
                               pcr.ifthen(self.landmask, self.WaterBodies.waterBodyIds)))
            waterBodyStoragePerCell = \
                waterBodyStorageTotal * \
                self.cellArea / \
                pcr.areatotal(pcr.cover( \
                    self.cellArea, 0.0), \
                    pcr.ifthen(self.landmask, self.WaterBodies.waterBodyIds))
            waterBodyStoragePerCell = \
                pcr.ifthen(pcr.scalar(self.WaterBodies.waterBodyIds) > 0.,
                           waterBodyStoragePerCell)  # unit: m3
            #
            self.channelStorage = pcr.cover(waterBodyStoragePerCell, self.channelStorage)  # unit: m3
            self.channelStorage = pcr.ifthen(self.landmask, self.channelStorage)

            # channel discharge (m3/s): current:
            self.discharge = self.Q / vos.secondsPerDay()
            self.discharge = pcr.max(0., self.discharge)  # reported channel discharge cannot be negative
            self.discharge = pcr.ifthen(self.landmask, self.discharge)

            # discharge at channel and lake/reservoir outlets (m3/s)
            # ~ self.disChanWaterBody = pcr.ifthen(self.landmask,\
            # ~ pcr.cover( self.waterBodyOutDisc,\
            # ~ self.discharge))                  # TODO: FIX THIS, discharge at water bodies is too high. (self.waterBodyOutDisc)
            #
            self.disChanWaterBody = pcr.ifthen(pcr.scalar(self.WaterBodies.waterBodyIds) > 0., \
                                               pcr.areamaximum(self.discharge, self.WaterBodies.waterBodyIds))
            self.disChanWaterBody = pcr.cover(self.disChanWaterBody, self.discharge)
            self.disChanWaterBody = pcr.ifthen(self.landmask, self.disChanWaterBody)
            #
            self.disChanWaterBody = pcr.max(0., self.disChanWaterBody)  # reported channel discharge cannot be negative






# ---------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------

        # runoff from landSurface cells (unit: m)
        self.var.runoff = self.var.landSurfaceRunoff + self.var.baseflow

        # update channelStorage (unit: m3) after runoff
        self.var.channelStorage += self.var.runoff * self.var.cellArea

        # update channelStorage (unit: m3) after actSurfaceWaterAbstraction
        self.var.channelStorage -= self.var.actSurfaceWaterAbstract * self.var.cellArea

        # return flow from (m) non irrigation water demand
        self.var.nonIrrReturnFlow = self.var.nonIrrReturnFlowFraction* self.var.nonIrrGrossDemand
        nonIrrReturnFlowVol = self.var.nonIrrReturnFlow*self.var.cellArea
        self.var.channelStorage  += nonIrrReturnFlowVol

        # get routing parameters (based on avgDischarge)
        self.var.yMean, self.var.wMean, self.var.characteristicDistance = getRoutingParamAvgDischarge(self.var.avgDischarge,self.var.dist2celllength)

        # waterBodies: get parameters at the beginning of the year or simulation
        if (currTimeStep.doy == 1) or (currTimeStep.timeStepPCR == 1):
            getParameterFiles(currTimeStep,self.var.cellArea,self.var.LddMap,self.var.cellLengthFD,self.var.cellSizeInArcDeg)

        # simulating water bodies fraction
        channelFraction = np.minimum(1.0, self.var.wMean * self.var.cellLength / self.var.cellArea)
        self.var.dynamicFracWat = np.maximum(channelFraction, self.var.fractionWater)

        # (additional) evaporation from water bodies
        # current principle:
        # - if landSurface.actualET < waterKC * meteo.referencePotET * self.var.fracWat
        #   then, we add more evaporation
        #
        if (currTimeStep.day == 1) or (currTimeStep.timeStepPCR == 1):
            waterKC = readnetcdf2(self.var.fileCropKC_File ,self.var.CalendarDate,useDaily='month',value='kc')

        #
        # evaporation from water bodies (m3), limited to available channelStorage
        volLocEvapWaterBody = np.minimum(np.maximum(0.0,self.var.channelStorage),
                              np.maximum(0.0, (self.var.waterKC * self.var.ETRef * self.var.dynamicFracWat -\
                              self.var.actualET)* self.var.cellArea))





        # update channelStorage (m3) after evaporation from water bodies
        self.channelStorage -= volLocEvapWaterBody

        # local runoff/change (m) on surface water bodies in meter:
        self.localQW =  volLocEvapWaterBody*-1. / self.cellArea         # Note that precipitation has been calculated/included in the landSurface module.
        self.localQW =  pcr.ifthen(self.landmask, self.localQW)

        # riverbed infiltration (m3):
        # - current implementation based on Inge's principle (later, will be based on groundater head (MODFLOW) and can be negative)
        # - happening only if 0.0 < baseflow < nonFossilGroundwaterAbs
        # - infiltration rate will be based on aquifer saturated conductivity
        # - limited to fracWat
        # - limited to available channelStorage
        # - this infiltration will be handed to groundwater in the next time step
        riverbedConductivity  = groundwater.kSatAquifer
        self.riverbedExchange = pcr.max(0.0,\
                                pcr.min(self.channelStorage,\
                                pcr.ifthenelse(groundwater.baseflow > 0.0, \
                                pcr.ifthenelse(groundwater.nonFossilGroundwaterAbs > groundwater.baseflow, \
                                riverbedConductivity * self.dynamicFracWat * self.cellArea, \
                                0.0), 0.0)))
        self.riverbedExchange = pcr.cover(self.riverbedExchange, 0.0)
        factor = 0.05 # to avoid flip flop
        self.riverbedExchange = pcr.min(self.riverbedExchange, (1.0-factor)*self.channelStorage)
        self.riverbedExchange = pcr.cover(self.riverbedExchange, 0.0)
        self.riverbedExchange = pcr.ifthen(self.landmask, self.riverbedExchange)

        # update channelStorage (m3) after riverbedExchange (m3)
        self.channelStorage  -= self.riverbedExchange

        # make sure that channelStorage >= 0
        self.channelStorage   = pcr.max(0.0, self.channelStorage)

        if self.debugWaterBalance == 'True':\
           vos.waterBalanceCheck([self.runoff,\
                                  self.nonIrrReturnFlow,\
                                  self.localQW],\
                                 [landSurface.actSurfaceWaterAbstract,self.riverbedExchange/self.cellArea],\
                                 [           preStorage/self.cellArea],\
                                 [  self.channelStorage/self.cellArea],\
                                   'channelStorage before routing',\
                                  True,\
                                  currTimeStep.fulldate,threshold=5e-3)

        # updating timesteps to calculate avgDischarge, avgInflow and avgOutflow
        self.timestepsToAvgDischarge += 1.

        if self.method == "accuTravelTime":
            self.accuTravelTime(currTimeStep)                           # output:

        # water height (m) = channelStorage / cellArea
        self.waterHeight = self.channelStorage / self.cellArea

        # total water storage
        self.waterHeight = self.channelStorage / self.cellArea

        # total water storage thickness (m) for the entire column
        # (including interception, snow, soil and groundwater)
        self.totalWaterStorageThickness = pcr.ifthen(self.landmask,\
                                          self.waterHeight + \
                                          landSurface.totalSto + \
                                          groundwater.storGroundwater)  # unit: m


        # total water storage thickness (m) for the entire column
        # (including interception, snow, soil and groundwater)
        self.totalWaterStorageVolume = self.totalWaterStorageThickness *\
                                       self.cellArea                    # unit: m3

        # Calculating avgDischarge
        #
        # average and standard deviation of long term discharge
        #~ self.avgDischarge = (self.avgDischarge  * \
                            #~ (pcr.min(self.maxTimestepsToAvgDischargeLong,
                                     #~ self.timestepsToAvgDischarge)- 1.) + \
                             #~ self.discharge * 1.) / \
                            #~ (pcr.min(self.maxTimestepsToAvgDischargeLong,
                                     #~ self.timestepsToAvgDischarge))             # Edwin's old formula.
        #
        dishargeUsed      = pcr.max(0.0, self.discharge)
        dishargeUsed      = pcr.max(dishargeUsed, self.disChanWaterBody)
        #
        deltaAnoDischarge = dishargeUsed - self.avgDischarge
        self.avgDischarge = self.avgDischarge +\
                            deltaAnoDischarge/\
                            pcr.min(self.maxTimestepsToAvgDischargeLong, self.timestepsToAvgDischarge)
        self.avgDischarge = pcr.max(0.0, self.avgDischarge)
        self.m2tDischarge = self.m2tDischarge + pcr.abs(deltaAnoDischarge*(self.discharge - self.avgDischarge))
        self.varDischarge = self.m2tDischarge / \
                            pcr.max(1.,\
                            pcr.min(self.maxTimestepsToAvgDischargeLong, self.timestepsToAvgDischarge)-1.)
                          # see: online algorithm on http://en.wikipedia.org/wiki/Algorithms_for_calculating_variance
        self.stdDischarge = pcr.max(self.varDischarge**0.5, 0.0)

        # update available channelStorage that can be extracted:
        # principle:
        # - during dry period, only limited water may be extracted.
        # - during non dry period, entire channel storage may be extracted.
        minDischargeForEnvironmentalFlow = pcr.max(0., self.avgDischarge - 3.*self.stdDischarge)
        factor = 0.05 # to avoid flip flop
        minDischargeForEnvironmentalFlow = pcr.max(factor*self.avgDischarge, minDischargeForEnvironmentalFlow)
        self.readAvlChannelStorage = pcr.max(factor*self.channelStorage,\
                                     pcr.max(0.00,\
                                     pcr.ifthenelse(self.discharge > minDischargeForEnvironmentalFlow,\
                                     self.channelStorage,\
                                     self.channelStorage*\
                                   vos.getValDivZero(self.discharge, minDischargeForEnvironmentalFlow, vos.smallNumber))))
        self.readAvlChannelStorage = pcr.min(self.readAvlChannelStorage, (1.0-factor)*self.channelStorage)
        #
        # to avoid small values and to avoid surface water abstractions from dry channels
        tresholdChannelStorage = 0.0005*self.cellArea  # 0.5 mm
        self.readAvlChannelStorage = pcr.ifthenelse(self.readAvlChannelStorage > tresholdChannelStorage, self.readAvlChannelStorage, pcr.scalar(0.0))
        self.readAvlChannelStorage = pcr.cover(self.readAvlChannelStorage, 0.0)

        # average baseflow (m3/s)
        # - avgDischarge and avgBaseflow used as proxies for partitioning groundwater and surface water abstractions
        #
        baseflowM3PerSec = groundwater.baseflow * self.cellArea / vos.secondsPerDay()
        deltaAnoBaseflow = baseflowM3PerSec - self.avgBaseflow
        self.avgBaseflow = self.avgBaseflow +\
                           deltaAnoBaseflow/\
                           pcr.min(self.maxTimestepsToAvgDischargeLong, self.timestepsToAvgDischarge)
        self.avgBaseflow = pcr.max(0.0, self.avgBaseflow)






