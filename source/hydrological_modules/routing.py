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


        #self.var.Ldd = loadmap('Ldd',pcr=True,lddflag=True)


        # TODO change this back!!!!!!!!!!!!!!!!!!
        self.var.Ldd = lddmask(loadmap('Ldd',pcr=True,lddflag=True), self.var.MaskMap)
        # Cut ldd to size of MaskMap
        # Prevents 'unsound' ldd if MaskMap covers sub-area of ldd
        self.var.Ldd = lddrepair(self.var.Ldd)


        # upstream function in numpy
        inAr = decompress(np.arange(maskinfo['mapC'][0],dtype="int32"))
        lddC = compressArray(self.var.Ldd)
        # giving a number to each non missing pixel as id
        self.var.downstruct = (compressArray(downstream(self.var.Ldd,inAr))).astype("int32")
        # each upstream pixel gets the id of the downstream pixel
        self.var.downstruct[lddC==5] = maskinfo['mapC'][0]
        # all pits gets a high number
        #d3=np.bincount(self.var.downstruct, weights=loadmap('AvgDis'))[:-1]
          # upstream function in numpy


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

        # maximum memory time-length of AvgDischarge (long term)
        self.var.maxTimestepsToAvgDischargeShort = loadmap('maxTimestepsToAvgDischargeShorTerm')
        # maximum memory time-length of AvgDischarge (long term)
        self.var.maxTimestepsToAvgDischargeLong = loadmap('maxTimestepsToAvgDischargeLongTerm')

        ## if self.method == "accuTravelTime":
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

        self.var.channelStorage = self.var.init_module.load_initial('channelStorage') + globals.inZero.copy()
        self.var.readAvlChannelStorage = self.var.init_module.load_initial('readAvlChannelStorage')
        # make sure that timestepsToAvgDischarge is consistent (or the same) for the entire map: # as pcraster.mapmaximum
        self.var.timestepsToAvgDischarge = np.amax(self.var.init_module.load_initial('timestepsToAvgDischarge'))
        self.var.avgDischarge = self.var.init_module.load_initial('avgChannelDischarge') + globals.inZero.copy()    # in m3/s
        self.var.m2tDischarge = self.var.init_module.load_initial('m2tChannelDischarge') + globals.inZero.copy()
        self.var.avgBaseflow = self.var.init_module.load_initial('avgBaseflow') + globals.inZero.copy()
        self.var.riverbedExchange = self.var.init_module.load_initial('riverbedExchange') + globals.inZero.copy()



        self.var.readAvlChannelStorage = np.minimum(self.var.readAvlChannelStorage, self.var.channelStorage)

        if option['sumWaterBalance']:
            self.var.catchment = loadmap('Catchment').astype(np.int)
            self.var.catchmentNo = int(loadmap('CatchmentNo'))

            lddnp = compressArray(self.var.Ldd)

            # all last outflow points are marked
            self.var.outlets = np.where(lddnp ==5, self.var.catchment, 0)
            #self.var.outlets = np.where(self.var.catchment > 5, self.var.outlets, False)

            #report(decompress(self.var.outlets), "D:/work/output/outlets.map")
            # report(decompress(self.var.catchment), "D:\work\output/catch.map")

            self.var.catchmentsize = npareatotal(globals.inZero + 1., self.var.catchment)

            self.var.discharge = globals.inZero.copy()





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


        def accuTravelTime():


            if option['includeWaterBodies']:

                # at cells where lakes and/or reservoirs defined, move channelStorage to waterBodyStorage  # unit: m3
                storageAtLakeAndReservoirs = np.where(self.var.waterBodyIds > 0., self.var.channelStorage,0.0)
                # storage out
                self.var.channelStorage -= storageAtLakeAndReservoirs

                # update waterBodyStorage (inflow, storage and outflow)
                self.var.lakes_reservoirs_module.dynamic(storageAtLakeAndReservoirs)

                # transfer outflow from lakes and/or reservoirs to channelStorages    # unit: m3/day
                waterBodyOutflowC = np.where(    self.var.waterBodyOutC == True,self.var.waterBodyOutflowC, 0.0)

                # distribute outflow to water body storage
                waterBodyOutflowC = npareaaverage(waterBodyOutflowC,self.var.waterBodyIdsC)
                waterBodyOutflowC = np.where( self.var.waterBodyIdsC > 0., waterBodyOutflowC, 0.0)  # unit: m3/day


                # obtain water body storages (for reporting) #m3
                self.var.waterBodyStorageC = np.where(self.var.waterBodyIdsC > 0., self.var.waterBodyStorageC, 0.0)
                # as well as outflows from water bodies (for reporting) # m3/s
                #self.var.waterBodyOutDiscC = np.where( self.var.waterBodyIdsC > 0., self.var.waterBodyOutflowC, 0.0) / self.var.DtSec

                # Move waterBodyOutflow according to water body discharge (velocity)
                waterBodyOutflow = globals.inZero.copy()
                np.put(waterBodyOutflow, self.var.waterBodyIndexC, waterBodyOutflowC)

                # move reslakes out in in
                self.var.channelStorage += waterBodyOutflow

            else:
                self.var.waterBodyStorage = globals.inZero.copy()

                # end waterbody if includeWaterBodies = True



            # channelStorage ROUTING:
            # convert with decompress to pcraster format
            channelStorageForAccuTravelTime = decompress(self.var.channelStorage.copy())
            #
            characteristicDistanceForAccuTravelTime = self.var.characteristicDistance.copy()   # or  0.001 * self.var.cellsize if nan
            characteristicDistanceForAccuTravelTime = decompress( np.maximum(0.001 * self.var.cellsize, self.var.characteristicDistance))

           # hh1 = compressArray(characteristicDistanceForAccuTravelTime)[25989]
           # hh2 = compressArray(channelStorageForAccuTravelTime)[25989]
           # hh3 = compressArray(self.var.Ldd)[25989]

            # self.var.Q = channel discharge (m3/day)
            QPcr = accutraveltimeflux(self.var.Ldd, channelStorageForAccuTravelTime, characteristicDistanceForAccuTravelTime)
            # updating channelStorage (after routing)
            channelStoragePcr = accutraveltimestate(self.var.Ldd, channelStorageForAccuTravelTime, characteristicDistanceForAccuTravelTime)


            # from pcraster -> numpy
            self.var.Q = compressArray(QPcr)
            self.var.Q[np.isnan(self.var.Q)] = 0
            self.var.channelStorage = compressArray(channelStoragePcr)
            self.var.channelStorage[np.isnan(self.var.channelStorage)] = 0
            # for very small velocity (i.e. characteristicDistanceForAccuTravelTime), discharge can be missing value.
            # see: http://sourceforge.net/p/pcraster/bugs-and-feature-requests/543/
            #      http://karssenberg.geo.uu.nl/tt/TravelTimeSpecification.htm

            # channel discharge (m3/s): current:
            self.var.discharge = self.var.Q / self.var.DtSec
            self.var.discharge = np.maximum(0., self.var.discharge)  # reported channel discharge cannot be negative


            if option['includeWaterBodies']:
                channelStorageC = np.compress(self.var.compressID, self.var.channelStorage)
                dischargeC = np.compress(self.var.compressID, self.var.discharge)

                # after routing, return waterBodyStorage to channelStorage
                h1 = npareaaverage(self.var.waterBodyStorageC,self.var.waterBodyIdsC)
                h2 = npareatotal(  channelStorageC,  self.var.waterBodyIdsC)
                waterBodyStorageTotal = np.where(self.var.waterBodyIdsC > 0., h1 + h2, 0.)

                waterBodyStoragePerCell = waterBodyStorageTotal * self.var.cellAreaC / \
                                      npareatotal(self.var.cellAreaC, self.var.waterBodyIdsC)

                # unit: m3
                waterBodyStoragePerCell = np.where(self.var.waterBodyIdsC > 0.,waterBodyStoragePerCell, channelStorageC)

                waterBodyStoragePerCellAll = globals.inZero.copy()
                np.put(waterBodyStoragePerCellAll, self.var.waterBodyIndexC, waterBodyStoragePerCell)

                # update storage
                self.var.channelStorage = np.where(waterBodyStoragePerCellAll > 0, waterBodyStoragePerCellAll, self.var.channelStorage)  #


                # discharge at channel and lake/reservoir outlets (m3/s)
                # ~ self.var.disChanWaterBody = np.where(self.var.landmask,\
                # ~ pcr.cover( self.var.waterBodyOutDisc,\
                # ~ self.var.discharge))                  # TODO: FIX THIS, discharge at water bodies is too high. (self.var.waterBodyOutDisc)


                disChanWaterBody = np.where(self.var.waterBodyIdsC > 0., npareamaximum(dischargeC, self.var.waterBodyIdsC), dischargeC )
                self.var.disChanWaterBody =  globals.inZero.copy()
                np.put(self.var.disChanWaterBody, self.var.waterBodyIndexC, disChanWaterBody)

                # reported channel discharge cannot be negative
                self.var.disChanWaterBody = np.where(self.var.disChanWaterBody > 0, self.var.disChanWaterBody, self.var.discharge )

                self.var.disChanWaterBody = np.maximum(0., self.var.disChanWaterBody)
            else:
                self.var.disChanWaterBody = self.var.discharge.copy()





# ---------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------
        """
        MAIN PART
        """

        if option['calcWaterBalance']:
            self.var.prechannelStorage = self.var.channelStorage.copy()


        # runoff from landSurface cells (unit: m)
        self.var.runoff = self.var.sum_landSurfaceRunoff + self.var.baseflow

        # update channelStorage (unit: m3) after runoff
        self.var.channelStorage += self.var.runoff * self.var.cellArea

        # update channelStorage (unit: m3) after actSurfaceWaterAbstraction
        self.var.channelStorage -= self.var.sum_actSurfaceWaterAbstract * self.var.cellArea

        # return flow from (m) non irrigation water demand
        self.var.nonIrrReturnFlow = self.var.nonIrrReturnFlowFraction * self.var.nonIrrGrossDemand
        self.var.channelStorage  =  self.var.channelStorage + self.var.nonIrrReturnFlow * self.var.cellArea

        # get routing parameters (based on avgDischarge)
        self.var.yMean, self.var.wMean, self.var.characteristicDistance = getRoutingParamAvgDischarge(self.var.avgDischarge,self.var.dist2celllength)

        # waterBodies: get parameters at the beginning of the year or simulation
        #if (currTimeStep.doy == 1) or (currTimeStep.timeStepPCR == 1):
        if dateVar['newStart'] or dateVar['newYear']:   # check if first day  of the year
            #self.var.lakes_reservoir_module.getParameterFiles(currTimeStep,self.var.cellArea,self.var.LddMap,self.var.cellLengthFD,self.var.cellSize)
            self.var.lakes_reservoirs_module.getParameterFiles()

        # simulating water bodies fraction
        channelFraction = np.minimum(1.0, self.var.wMean * self.var.cellLength / self.var.cellArea)
        self.var.dynamicFracWat = np.maximum(channelFraction, self.var.fractionWater)

        # (additional) evaporation from water bodies
        # current principle:
        # - if landSurface.actualET < waterKC * meteo.referencePotET * self.var.fracWat
        #   then, we add more evaporation

        if dateVar['newStart'] or dateVar['newMonth']:  #Monthly!
        #if (currTimeStep.day == 1) or (currTimeStep.timeStepPCR == 1):
            self.var.waterKC = readnetcdf2(self.var.fileCropKC_File ,dateVar['currDate'],useDaily='month',value='kc')

        # evaporation from water bodies (m3), limited to available channelStorage
        volLocEvapWaterBody = np.minimum(np.maximum(0.0,self.var.channelStorage),
                              np.maximum(0.0, (self.var.waterKC * self.var.ETRef * self.var.dynamicFracWat -\
                              self.var.sum_actualET)* self.var.cellArea))





        # update channelStorage (m3) after evaporation from water bodies
        self.var.channelStorage -= volLocEvapWaterBody

        # local runoff/change (m) on surface water bodies in meter:
        # Note that precipitation has been calculated/included in the landSurface module.
        self.var.localQW =  volLocEvapWaterBody* self.var.InvCellArea

        # riverbed infiltration (m3):
        # - current implementation based on Inge's principle (later, will be based on groundater head (MODFLOW) and can be negative)
        # - happening only if 0.0 < baseflow < nonFossilGroundwaterAbs
        # - infiltration rate will be based on aquifer saturated conductivity
        # - limited to fracWat
        # - limited to available channelStorage
        # - this infiltration will be handed to groundwater in the next time step
        riverbedConductivity  = self.var.kSatAquifer
        self.var.riverbedExchange = np.maximum(0.0,  np.minimum(self.var.channelStorage,\
                                np.where(self.var.baseflow > 0.0, \
                                np.where(self.var.nonFossilGroundwaterAbs > self.var.baseflow, \
                                riverbedConductivity * self.var.dynamicFracWat * self.var.cellArea, \
                                0.0), 0.0)))

        # to avoid flip flop
        factor = 0.05
        self.var.riverbedExchange = np.minimum(self.var.riverbedExchange, (1.0-factor)*self.var.channelStorage)

        # update channelStorage (m3) after riverbedExchange (m3)
        self.var.channelStorage  -= self.var.riverbedExchange

        # make sure that channelStorage >= 0
        self.var.channelStorage   = np.maximum(0.0, self.var.channelStorage)


        if option['calcWaterBalance']:
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.runoff * self.var.cellArea,self.var.nonIrrReturnFlow * self.var.cellArea],            # In
                [self.var.sum_actSurfaceWaterAbstract * self.var.cellArea,self.var.localQW * self.var.cellArea, self.var.riverbedExchange],           # Out
                [self.var.prechannelStorage],                                  # prev storage
                [self.var.channelStorage],
                "Routing", False)
        self.var.channelStorageBefore = self.var.channelStorage.copy()



        # updating timesteps to calculate avgDischarge, avgInflow and avgOutflow
        self.var.timestepsToAvgDischarge += 1.

        """
        Routing with accuflux
        """
        accuTravelTime()




        # water height (m) = channelStorage / cellArea
        self.var.waterHeight = self.var.channelStorage / self.var.cellArea

        # total water storage thickness (m) for the entire column
        # (including interception, snow, soil and groundwater) # unit: m
        self.var.totalWaterStorageThickness = self.var.waterHeight + self.var.totalSto +  self.var.storGroundwater


        # total water storage thickness (m) for the entire column
        # (including interception, snow, soil and groundwater) # unit: m3
        self.var.totalWaterStorageVolume = self.var.totalWaterStorageThickness * self.var.cellArea

        # Calculating avgDischarge
        #
        # average and standard deviation of long term discharge  # Edwin's old formula.
        #~ self.var.avgDischarge = (self.var.avgDischarge  * (np.minimum(self.var.maxTimestepsToAvgDischargeLong,
        #~             self.var.timestepsToAvgDischarge)- 1.) + self.var.discharge * 1.) / (np.minimum(self.var.maxTimestepsToAvgDischargeLong,
        #~             self.var.timestepsToAvgDischarge))
        #

        dischargeUsed      = np.maximum(self.var.discharge, self.var.disChanWaterBody)
        #
        deltaAnoDischarge = dischargeUsed - self.var.avgDischarge
        self.var.avgDischarge = self.var.avgDischarge + deltaAnoDischarge / \
                            np.minimum(self.var.maxTimestepsToAvgDischargeLong, self.var.timestepsToAvgDischarge)
        self.var.avgDischarge = np.maximum(0.0, self.var.avgDischarge)
        self.var.m2tDischarge = self.var.m2tDischarge + np.abs(deltaAnoDischarge*(self.var.discharge - self.var.avgDischarge))

        # see: algorithm:http://en.wikipedia.org/wiki/Algorithms_for_calculating_variance
        self.var.varDischarge = self.var.m2tDischarge / np.maximum(1.,\
                            np.minimum(self.var.maxTimestepsToAvgDischargeLong, self.var.timestepsToAvgDischarge)-1.)

        self.var.stdDischarge = np.maximum(self.var.varDischarge**0.5, 0.0)

        # update available channelStorage that can be extracted:
        # principle:
        # - during dry period, only limited water may be extracted.
        # - during non dry period, entire channel storage may be extracted.

        minDischargeForEnvironmentalFlow = np.maximum(0., self.var.avgDischarge - 3.*self.var.stdDischarge)

        # to avoid flip flop
        factor = 0.05
        minDischargeForEnvironmentalFlow = np.maximum(factor*self.var.avgDischarge, minDischargeForEnvironmentalFlow)
        h1 = getValDivZero(self.var.discharge, minDischargeForEnvironmentalFlow, 1e-39)
        h2 = np.maximum(0.00,np.where(self.var.discharge > minDischargeForEnvironmentalFlow,\
                                     self.var.channelStorage, self.var.channelStorage* h1))
        self.var.readAvlChannelStorage = np.maximum(factor*self.var.channelStorage, h2)

        self.var.readAvlChannelStorage = np.minimum(self.var.readAvlChannelStorage, (1.0-factor) * self.var.channelStorage)

        # to avoid small values and to avoid surface water abstractions from dry channels # 0.5 mm
        tresholdChannelStorage = 0.0005 * self.var.cellArea
        self.var.readAvlChannelStorage = np.where(self.var.readAvlChannelStorage > tresholdChannelStorage, self.var.readAvlChannelStorage, 0.)


        # average baseflow (m3/s)
        # avgDischarge and avgBaseflow used as proxies for partitioning groundwater and surface water abstractions
        baseflowM3PerSec = self.var.baseflow * self.var.cellArea / self.var.DtSec
        deltaAnoBaseflow = baseflowM3PerSec - self.var.avgBaseflow
        self.var.avgBaseflow = self.var.avgBaseflow + deltaAnoBaseflow / \
                           np.minimum(self.var.maxTimestepsToAvgDischargeLong, self.var.timestepsToAvgDischarge)
        self.var.avgBaseflow = np.maximum(0.0, self.var.avgBaseflow)


        #report(decompress(self.var.discharge), "C:\work\output/q1.map")

     #   print "discharge", self.var.discharge[25989],self.var.discharge[23765]




        """
        a = readmap("C:\work\output/q_pcr")
        b = nominal(a*100)
        c = ifthenelse(b == 105779, scalar(9999), scalar(0))
        report(c,"C:\work\output/t3.map")
        d = compressArray(c)
        np.where(d == 9999)   #23765
        e = pcr2numpy(c, 0).astype(np.float64)
        np.where(e > 9000)   # 75, 371  -> 76, 372
        """



