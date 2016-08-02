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
        self.var.cellsize = clone().cellSize()

        if option['gridSizeUserDefined']:
            # cellLength (m) is approximated cell diagonal
            # assuming cellsize is in degree, each minute is 1852 min
            cellvertical = self.var.cellsize * 60 * 1852
            self.var.cellLength = np.sqrt((self.var.cellArea / cellvertical) ** 2 + cellvertical **2)
        else:
            self.var.cellLength = self.var.cellsize
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
            self.var.dist2celllength = compressArray(channelLengthDownstream) / self.var.cellsize
        else:
            # unit: m
            self.var.dist2celllength = compressArray(channelLengthDownstream)

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

        def getRoutingParamAvgDischarge(avgDischarge, dist2celllength):
            # obtain routing parameters based on average (longterm) discharge
            # output: channel dimensions and characteristicDistance (for accuTravelTime input)

            yMean = self.var.eta * np.power(avgDischarge, self.var.nu)  # avgDischarge in m3/s
            wMean = self.var.tau * np.power(avgDischarge, self.var.phi)
            yMean = np.maximum(yMean, 0.000000001)  # channel depth (m)
            wMean = np.maximum(wMean, 0.000000001)  # channel width (m)

            # characteristicDistance (dimensionless)
            # - This will be used for accutraveltimeflux & accutraveltimestate
            # - discharge & storage = accutraveltimeflux & accutraveltimestate
            # - discharge = the total amount of material flowing through the cell (m3/s)
            # - storage   = the amount of material which is deposited in the cell (m3)

            #  meter/day
            characteristicDistance =  ((yMean * wMean) /  (wMean + 2 * yMean)) ** self.var.twothird * \
                ((self.var.gradient) ** (0.5)) / self.var.manningsN * self.var.DtSec

            characteristicDistance = np.maximum((self.var.cellsize) * 0.000000001, characteristicDistance / dist2celllength)  # arcDeg/day

            # PS: In accutraveltime function:
            #     If characteristicDistance (velocity) = 0 then:
            #     - accutraveltimestate will give zero
            #     - accutraveltimeflux will be very high

            return (yMean, wMean, characteristicDistance)

        # ---------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------


        def accuTravelTime(self, currTimeStep):

            usedLDD = self.var.Ldd

            if option['includeWaterBodies']:

                # at cells where lakes and/or reservoirs defined, move channelStorage to waterBodyStorage  # unit: m3
                storageAtLakeAndReservoirs = np.where(self.var.waterBodyIds > 0., self.var.channelStorage,0.0)
                self.var.channelStorage -= storageAtLakeAndReservoirs

                # update waterBodyStorage (inflow, storage and outflow)
                self.var.WaterBodies.update(storageAtLakeAndReservoirs, \
                                    self.var.timestepsToAvgDischarge, \
                                    self.var.maxTimestepsToAvgDischargeShort, \
                                    self.var.maxTimestepsToAvgDischargeLong, \
                                    currTimeStep)

                # transfer outflow from lakes and/or reservoirs to channelStorages    # unit: m3/day
                waterBodyOutflow = np.where( self.var.waterBodyOut == True,self.var.waterBodyOutflow, 0.0)

                # distribute outflow to water body storage
                #waterBodyOutflow = pcr.areaaverage(waterBodyOutflow, self.var.WaterBodies.waterBodyIds)
                #waterBodyOutflow = np.take(np.bincount(self.var.waterBodyIds,waterBodyOutflow) / np.bincount(self.var.waterBodyIds)  , self.var.waterBodyIds)
                waterBodyOutflow = npareaaverage(waterBodyOutflow,self.var.waterBodyIds)
                waterBodyOutflow = np.where( self.var.waterBodyIds > 0., waterBodyOutflow, 0.0)  # unit: m3/day


                # obtain water body storages (for reporting) #m3
                self.var.waterBodyStorage = np.where(self.var.waterBodyIds > 0., self.var.waterBodyStorage, 0.0)
                # as well as outflows from water bodies (for reporting) # m3/s
                self.var.waterBodyOutDisc = np.where( self.var.waterBodyIds > 0., self.var.waterBodyOutflow, 0.0) / self.var.DtSec

                # TODO: Move waterBodyOutflow according to water body discharge (velocity)
                self.var.channelStorage += waterBodyOutflow

                # end waterbody if includeWaterBodies = True


            # channelStorage ROUTING:
            # convert with decompress to pcraster format
            channelStorageForAccuTravelTime = decompress(self.var.channelStorage.copy())
            #
            characteristicDistanceForAccuTravelTime = self.var.characteristicDistance, 0.001 * self.var.cellsize
            characteristicDistanceForAccuTravelTime = decompress( np.maximum(0.001 * self.var.cellsize, self.var.characteristicDistance))

            # self.var.Q = channel discharge (m3/day)
            QPcr = accutraveltimeflux(usedLDD, channelStorageForAccuTravelTime, characteristicDistanceForAccuTravelTime)
            # updating channelStorage (after routing)
            channelStoragePcr = accutraveltimestate(usedLDD, channelStorageForAccuTravelTime, characteristicDistanceForAccuTravelTime)

            self.var.Q = cover(self.var.Q, 0.0)
            # from pcraster -> numpy
            self.var.Q = compressArray(QPcr)
            self.var.channelStorage = compressArray(channelStoragePcr)
            # for very small velocity (i.e. characteristicDistanceForAccuTravelTime), discharge can be missing value.
            # see: http://sourceforge.net/p/pcraster/bugs-and-feature-requests/543/
            #      http://karssenberg.geo.uu.nl/tt/TravelTimeSpecification.htm



            # after routing, return waterBodyStorage to channelStorage

            waterBodyStorageTotal = np.where(self.var.waterBodyIds > 0., npareaaverage( self.var.waterBodyStorage,self.var.waterBodyIds) + \
                           npareatotal(self.var.channelStorage,self.var.waterBodyIds))

            waterBodyStoragePerCell = waterBodyStorageTotal * self.var.cellArea / \
                                      npareatotal(self.var.cellArea, self.var.waterBodyIds)

            # unit: m3
            waterBodyStoragePerCell = np.where(self.var.waterBodyIds > 0.,waterBodyStoragePerCell, self.var.channelStorage)
            #self.var.channelStorage = pcr.cover(waterBodyStoragePerCell, self.var.channelStorage)

            # channel discharge (m3/s): current:
            self.var.discharge = self.var.Q / self.var.DtSec
            self.var.discharge = np.maximum(0., self.var.discharge)  # reported channel discharge cannot be negative
            self.var.discharge = np.where(self.var.landmask, self.var.discharge)

            # discharge at channel and lake/reservoir outlets (m3/s)
            # ~ self.var.disChanWaterBody = np.where(self.var.landmask,\
            # ~ pcr.cover( self.var.waterBodyOutDisc,\
            # ~ self.var.discharge))                  # TODO: FIX THIS, discharge at water bodies is too high. (self.var.waterBodyOutDisc)
            #
            self.var.disChanWaterBody = np.where(self.var.waterBodyIds > 0., npareamaximum(self.var.discharge, self.var.waterBodyIds), self.var.discharge )
            # reported channel discharge cannot be negative
            self.var.disChanWaterBody = np.maximum(0., self.var.disChanWaterBody)






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
        self.var.nonIrrReturnFlow = self.var.nonIrrReturnFlowFraction * self.var.nonIrrGrossDemand
        self.var.channelStorage  =  self.var.channelStorage + self.var.nonIrrReturnFlow * self.var.cellArea

        # get routing parameters (based on avgDischarge)
        self.var.yMean, self.var.wMean, self.var.characteristicDistance = getRoutingParamAvgDischarge(self.var.avgDischarge,self.var.dist2celllength)

        # waterBodies: get parameters at the beginning of the year or simulation
        #if (currTimeStep.doy == 1) or (currTimeStep.timeStepPCR == 1):
        if (self.var.currentTimeStep() == 1) or (int(self.var.CalendarDate.strftime('%j')) == 1):   # check if first day 0of the year
            #self.var.lakes_reservoir_module.getParameterFiles(currTimeStep,self.var.cellArea,self.var.LddMap,self.var.cellLengthFD,self.var.cellSize)
            self.var.lakes_reservoirs_module.getParameterFiles()

        # simulating water bodies fraction
        channelFraction = np.minimum(1.0, self.var.wMean * self.var.cellLength / self.var.cellArea)
        self.var.dynamicFracWat = np.maximum(channelFraction, self.var.fractionWater)

        # (additional) evaporation from water bodies
        # current principle:
        # - if landSurface.actualET < waterKC * meteo.referencePotET * self.var.fracWat
        #   then, we add more evaporation

        #  self.var.CalendarDay
        if (self.var.currentTimeStep() == 1) or (int(self.var.CalendarDate.strftime('%d')) ==1):
        #if (currTimeStep.day == 1) or (currTimeStep.timeStepPCR == 1):
            waterKC = readnetcdf2(self.var.fileCropKC_File ,self.var.CalendarDate,useDaily='month',value='kc')

        # evaporation from water bodies (m3), limited to available channelStorage
        volLocEvapWaterBody = np.minimum(np.maximum(0.0,self.var.channelStorage),
                              np.maximum(0.0, (self.var.waterKC * self.var.ETRef * self.var.dynamicFracWat -\
                              self.var.actualET)* self.var.cellArea))





        # update channelStorage (m3) after evaporation from water bodies
        self.channelStorage -= volLocEvapWaterBody

        # local runoff/change (m) on surface water bodies in meter:
        self.localQW =  volLocEvapWaterBody*-1. / self.cellArea         # Note that precipitation has been calculated/included in the landSurface module.
        self.localQW =  np.where(self.landmask, self.localQW)

        # riverbed infiltration (m3):
        # - current implementation based on Inge's principle (later, will be based on groundater head (MODFLOW) and can be negative)
        # - happening only if 0.0 < baseflow < nonFossilGroundwaterAbs
        # - infiltration rate will be based on aquifer saturated conductivity
        # - limited to fracWat
        # - limited to available channelStorage
        # - this infiltration will be handed to groundwater in the next time step
        riverbedConductivity  = groundwater.kSatAquifer
        self.riverbedExchange = np.maximum(0.0,\
                                np.minimum(self.channelStorage,\
                                np.whereelse(groundwater.baseflow > 0.0, \
                                np.whereelse(groundwater.nonFossilGroundwaterAbs > groundwater.baseflow, \
                                riverbedConductivity * self.dynamicFracWat * self.cellArea, \
                                0.0), 0.0)))
        self.riverbedExchange = pcr.cover(self.riverbedExchange, 0.0)
        factor = 0.05 # to avoid flip flop
        self.riverbedExchange = np.minimum(self.riverbedExchange, (1.0-factor)*self.channelStorage)
        self.riverbedExchange = pcr.cover(self.riverbedExchange, 0.0)
        self.riverbedExchange = np.where(self.landmask, self.riverbedExchange)

        # update channelStorage (m3) after riverbedExchange (m3)
        self.channelStorage  -= self.riverbedExchange

        # make sure that channelStorage >= 0
        self.channelStorage   = np.maximum(0.0, self.channelStorage)

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
        self.totalWaterStorageThickness = np.where(self.landmask,\
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
                            #~ (np.minimum(self.maxTimestepsToAvgDischargeLong,
                                     #~ self.timestepsToAvgDischarge)- 1.) + \
                             #~ self.discharge * 1.) / \
                            #~ (np.minimum(self.maxTimestepsToAvgDischargeLong,
                                     #~ self.timestepsToAvgDischarge))             # Edwin's old formula.
        #
        dishargeUsed      = np.maximum(0.0, self.discharge)
        dishargeUsed      = np.maximum(dishargeUsed, self.disChanWaterBody)
        #
        deltaAnoDischarge = dishargeUsed - self.avgDischarge
        self.avgDischarge = self.avgDischarge +\
                            deltaAnoDischarge/\
                            np.minimum(self.maxTimestepsToAvgDischargeLong, self.timestepsToAvgDischarge)
        self.avgDischarge = np.maximum(0.0, self.avgDischarge)
        self.m2tDischarge = self.m2tDischarge + pcr.abs(deltaAnoDischarge*(self.discharge - self.avgDischarge))
        self.varDischarge = self.m2tDischarge / \
                            np.maximum(1.,\
                            np.minimum(self.maxTimestepsToAvgDischargeLong, self.timestepsToAvgDischarge)-1.)
                          # see: online algorithm on http://en.wikipedia.org/wiki/Algorithms_for_calculating_variance
        self.stdDischarge = np.maximum(self.varDischarge**0.5, 0.0)

        # update available channelStorage that can be extracted:
        # principle:
        # - during dry period, only limited water may be extracted.
        # - during non dry period, entire channel storage may be extracted.
        minDischargeForEnvironmentalFlow = np.maximum(0., self.avgDischarge - 3.*self.stdDischarge)
        factor = 0.05 # to avoid flip flop
        minDischargeForEnvironmentalFlow = np.maximum(factor*self.avgDischarge, minDischargeForEnvironmentalFlow)
        self.readAvlChannelStorage = np.maximum(factor*self.channelStorage,\
                                     np.maximum(0.00,\
                                     np.whereelse(self.discharge > minDischargeForEnvironmentalFlow,\
                                     self.channelStorage,\
                                     self.channelStorage*\
                                   vos.getValDivZero(self.discharge, minDischargeForEnvironmentalFlow, vos.smallNumber))))
        self.readAvlChannelStorage = np.minimum(self.readAvlChannelStorage, (1.0-factor)*self.channelStorage)
        #
        # to avoid small values and to avoid surface water abstractions from dry channels
        tresholdChannelStorage = 0.0005*self.cellArea  # 0.5 mm
        self.readAvlChannelStorage = np.whereelse(self.readAvlChannelStorage > tresholdChannelStorage, self.readAvlChannelStorage, pcr.scalar(0.0))
        self.readAvlChannelStorage = pcr.cover(self.readAvlChannelStorage, 0.0)

        # average baseflow (m3/s)
        # - avgDischarge and avgBaseflow used as proxies for partitioning groundwater and surface water abstractions
        #
        baseflowM3PerSec = groundwater.baseflow * self.cellArea / vos.secondsPerDay()
        deltaAnoBaseflow = baseflowM3PerSec - self.avgBaseflow
        self.avgBaseflow = self.avgBaseflow +\
                           deltaAnoBaseflow/\
                           np.minimum(self.maxTimestepsToAvgDischargeLong, self.timestepsToAvgDischarge)
        self.avgBaseflow = np.maximum(0.0, self.avgBaseflow)






