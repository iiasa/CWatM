# -------------------------------------------------------------------------
# Name:        Lakes and reservoirs module
# Purpose:
#
# Author:      PB
#
# Created:     01/08/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class lakes_reservoirs(object):

    """
    # ************************************************************
    # ***** LAKES AND RESERVOIRS      ****************************
    # ************************************************************
    """

    def __init__(self, lakes_reservoirs_variable):
        self.var = lakes_reservoirs_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the lakes + reservoirs module

        """
        self.var.fractionWater = 0.0

        self.var.waterbody_file = binding['waterBodyInputNC']

        self.var.includeLakes = "True"
        self.var.includeReservoirs = "True"

        if option['includeWaterBodies']:

            self.var.minResvrFrac = loadmap('minResvrFrac') + globals.inZero
            self.var.maxResvrFrac = loadmap('maxResvrFrac') + globals.inZero
            self.var.minWeirWidth = loadmap('minWeirWidth') + globals.inZero


        # initial conditions

        # lake and reservoir storages = waterBodyStorage (m3)
        # - values are given for the entire lake / reservoir cells
        self.var.waterBodyStorage = loadmap('waterBodyStorageIni') + globals.inZero
        self.var.avgInflow = loadmap('avgInflowLakeReservIni') + globals.inZero
        self.var.avgOutflow = loadmap('avgOutflowDischargeIni') + globals.inZero



        i  = 1

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def getParameterFiles(self):

        #           self.var.cellArea    self.var..Ldd self.var.cellLength    ,self.var.cellSize
        # parameters for Water Bodies: fracWat
        #                              waterBodyIds
        #                              waterBodyOut
        #                              waterBodyArea
        #                              waterBodyTyp
        #                              waterBodyCap


        #    fracWat = fraction of surface water bodies
        self.var.fracWat = globals.inZero.copy()
        self.var.waterBodyIds = globals.inZero.copy()
        self.var.waterBodyOut = globals.inZero.copy()
        self.var.waterBodyTyp = globals.inZero.copy()
        self.var.waterBodyArea = globals.inZero.copy()  # waterBody surface areas


        #self.var.waterBodyOut = pcr.boolean(0)  # waterBody outlets
        #self.var.waterBodyArea = pcr.scalar(0.)  # waterBody surface areas
        # d.astype(np.int32) , d.astype(np.bool8)


        #if option['includeWaterBodies']:
            #waterBodyIdsPcr = nominal(0)
            #waterBodyOutPcr = boolean(0)
        self.var.fracWat = readnetcdf2(self.var.waterbody_file, dateVar['currDate'], "yearly", value= 'fracWaterInp')
        self.var.fracWat = np.maximum(0.0, self.var.fracWat)
        self.var.fracWat = np.minimum(1.0, self.var.fracWat)



        if self.var.includeLakes == "True" or self.var.includeReservoirs == "True":
            # water body ids
            self.var.waterBodyIds = readnetcdf2(self.var.waterbody_file, dateVar['currDate'], "yearly",value='waterBodyIds')
            #Adding 1 to make sure that no waterbody has ID = 0
            # missing value for pcraster
            self.var.waterBodyIds[self.var.waterBodyIds==0] = -9999
            waterBodyIdsPcr = decompress(self.var.waterBodyIds)
            ##self.var.waterBodyIds = np.where( self.var.waterBodyIds > 0., pcr.nominal(self.var.waterBodyIds))


            # Pcraster
            # water body outlets:
            # PB calculate for each lake/reservoir the outlet cell
            # e.g. lake Victory has many aterBodyIds (with same id) but only 1 cell where the lakecatchment = max -> outlet
            wbCatchment = catchmenttotal(scalar(1), self.var.Ldd)
            # = outlet ids
            waterBodyOutPcr = ifthen(wbCatchment == areamaximum(wbCatchment, nominal(waterBodyIdsPcr)), waterBodyIdsPcr)

            # this fill ups
            waterBodyOutPcr = ifthen(waterBodyIdsPcr > 0, waterBodyOutPcr)

            # correcting water body ids
            waterBodyIdsPcr = ifthen(waterBodyIdsPcr > 0., subcatchment(self.var.Ldd, nominal(waterBodyOutPcr)))

            # boolean map for water body outlets:
            waterBodyOutPcr = ifthenelse( waterBodyOutPcr > 0 ,scalar(1.0), scalar(0))

            # boolean map for water body outlets:

            self.var.waterBodyIds = compressArray(scalar(waterBodyIdsPcr))
            self.var.waterBodyOut = compressArray(scalar(waterBodyOutPcr))
            self.var.waterBodyIds[np.isnan(self.var.waterBodyIds)] = 0
            self.var.waterBodyOut[np.isnan(self.var.waterBodyOut)] = 0

            self.var.compressID = self.var.waterBodyIds > 0

            self.var.waterBodyIdsC = np.compress(self.var.compressID, self.var.waterBodyIds.astype(np.int32))
            self.var.waterBodyOutC = np.compress(self.var.compressID, self.var.waterBodyOut.astype(np.bool))
            self.var.waterBodyIndexC = np.nonzero(self.var.waterBodyIds)[0]
            fracWatC = np.compress(self.var.compressID > 0, self.var.fracWat)
            self.var.cellAreaC = np.compress(self.var.compressID, self.var.cellArea)


            #np.put(self.var.waterBodyIds, waterBodyIndexC,waterBodyIdsC)


            #self.var.waterBodyIds = self.var.waterBodyIds.astype(np.int32)
            #self.var.waterBodyOut = self.var.waterBodyOut.astype(np.bool)




            # reservoir surface area (m2):
            resSfArea = 1000. * 1000. * readnetcdf2(self.var.waterbody_file, dateVar['currDate'], "yearly", value='resSfAreaInp')
            resSfAreaC = np.compress(self.var.compressID, resSfArea)
            resSfAreaC = npareaaverage(resSfAreaC, self.var.waterBodyIdsC)


            # water body surface area (m2): (lakes and reservoirs)
            self.var.waterBodyAreaC = np.maximum(npareatotal(fracWatC * self.var.cellAreaC,self.var.waterBodyIdsC),
                                        npareaaverage( resSfAreaC, self.var.waterBodyIdsC))



            # Todo at the very end here corect ids, out, area
            #  correcting water body ids and outlets (excluding all water bodies with surfaceArea = 0)            #
            # correcting water body ids and outlets (excluding all water bodies with surfaceArea = 0)



        # water body types:
        # - 2 = reservoirs (regulated discharge)
        # - 1 = lakes (weirFormula)
        # - 0 = non lakes or reservoirs (e.g. wetland)

        if self.var.includeLakes == "True" or self.var.includeReservoirs == "True":
            waterBodyTyp = readnetcdf2(self.var.waterbody_file, dateVar['currDate'], "yearly", value='waterBodyTyp')
            self.var.waterBodyTypC = np.compress(self.var.compressID, waterBodyTyp)

            self.var.waterBodyTypC = np.where( self.var.waterBodyIdsC > 0, self.var.waterBodyTypC.astype(np.int32), 0)

            #self.var.waterBodyTyp = compressArray(areamajority(decompress(self.var.waterBodyTyp), decompress(self.var.waterBodyIds)))
            self.var.waterBodyTypC = npareamajority(self.var.waterBodyTypC, self.var.waterBodyIdsC)

            # TODO at then end
            # correcting water body ids and outlets:
            #self.var.waterBodyIds = np.where(self.var.waterBodyTyp > 0, self.var.waterBodyIds,0)
            #self.var.waterBodyOut = np.where(self.var.waterBodyIds > 0, self.var.waterBodyOut, False)


        # correcting water bodies attributes if reservoirs are ignored (for natural runs):
        if self.var.includeLakes == "True" and self.var.includeReservoirs == "False":
            # correcting fracWat
            #reservoirExcluded = globals.inZero.copy()
            reservoirExcluded = np.where(self.var.waterBodyTypC == 2, True, False)
            maxWaterBodyAreaExcluded = np.where(reservoirExcluded, self.var.waterBodyAreaC / \
                                 npareatotal(reservoirExcluded, self.var.waterBodyIdsC))
            maxfractionWaterExcluded = maxWaterBodyAreaExcluded / self.var.cellAreaC
            maxfractionWaterExcluded = np.minimum(1.0, maxfractionWaterExcluded)
            maxfractionWaterExcluded = np.minimum(fracWatC, maxfractionWaterExcluded)

            fracWatC = fracWatC - maxfractionWaterExcluded
            fracWatC = np.maximum(0., self.var.fracWat)
            fracWatC = np.minimum(1., self.var.fracWat)


            # to check afterwards
            #self.var.waterBodyArea = np.where(self.var.waterBodyTyp < 2,self.var.waterBodyArea, 0.)
            #self.var.waterBodyTyp = np.where(self.var.waterBodyTyp < 2, self.var.waterBodyTyp, 0)
            #self.var.waterBodyIds = np.where(self.var.waterBodyTyp > 0, self.var.waterBodyIds, 0)
            #self.var.waterBodyOut = np.where(self.var.waterBodyIds > 0, self.var.waterBodyOut, False)

        # reservoir maximum capacity (m3):

        self.var.resMaxCapC = np.compress(self.var.compressID, globals.inZero)
        self.var.waterBodyCapC = np.compress(self.var.compressID, globals.inZero)

        if self.var.includeReservoirs == "True":

            # reservoir maximum capacity (m3):
            resMaxCap = 1000. * 1000. * readnetcdf2(self.var.waterbody_file, dateVar['currDate'], "yearly", value='resMaxCapInp')
            self.var.resMaxCapC = np.compress(self.var.compressID, resMaxCap)

            self.var.resMaxCapC = np.where(self.var.resMaxCapC > 0, self.var.resMaxCapC, 0.)
            self.var.resMaxCapC = npareaaverage(self.var.resMaxCapC, self.var.waterBodyIdsC)

            # water body capacity (m3): (lakes and reservoirs)
            # Note: Most of lakes have capacities > 0.
            self.var.waterBodyCapC = np.where(self.var.waterBodyIdsC > 0, self.var.resMaxCapC, 0.0)

            # correcting water body types:
            self.var.waterBodyTypC = np.where(self.var.waterBodyCapC > 0., self.var.waterBodyTypC, \
                     np.where(self.var.waterBodyTypC == 2, 1, self.var.waterBodyTypC))

        # todo final correxction
        # final corrections:
        #self.var.waterBodyTyp = np.where(self.var.waterBodyArea > 0., self.var.waterBodyTyp, 0)
        #self.var.waterBodyIds = np.where(self.var.waterBodyTyp > 0, self.var.waterBodyIds, 0)
        #self.var.waterBodyOut = np.where(self.var.waterBodyIds > 0, self.var.waterBodyOut, False)



        # For each new reservoir (introduced at the beginning of the year)
        # initiating storage, average inflow and outflow:
        self.var.waterBodyStorage = np.where(self.var.waterBodyStorage > 0,self.var.waterBodyStorage, 0.0)
        self.var.avgInflow = np.where(self.var.avgInflow > 0,self.var.avgInflow, 0.0)
        self.var.avgOutflow = np.where(self.var.avgOutflow > 0, self.var.avgOutflow , 0.0)
        self.var.waterBodyStorageC = np.compress(self.var.compressID, self.var.waterBodyStorage)
        self.var.avgInflowC = np.compress(self.var.compressID, self.var.avgInflow)
        self.var.avgOutflowC = np.compress(self.var.compressID, self.var.avgOutflow)

        self.var.minResvrFracC = np.compress(self.var.compressID, self.var.minResvrFrac)
        self.var.maxResvrFracC = np.compress(self.var.compressID, self.var.maxResvrFrac)
        self.var.minWeirWidthC = np.compress(self.var.compressID, self.var.minWeirWidth)






        np.put(self.var.waterBodyIds,self.var.waterBodyIndexC,self.var.waterBodyIdsC)
        np.put(self.var.waterBodyOut, self.var.waterBodyIndexC, self.var.waterBodyOutC)
        self.var.waterBodyOut = self.var.waterBodyOut.astype(np.bool)

        np.put(self.var.waterBodyTyp, self.var.waterBodyIndexC, self.var.waterBodyTypC)
        np.put(self.var.waterBodyTyp, self.var.waterBodyIndexC, self.var.waterBodyTypC)
        i = 1


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
    def moveFromChannelToWaterBody(self, newStorageAtLakeAndReservoirs, timestepsToAvgDischarge, maxTimestepsToAvgDischargeShort):


        # new lake and/or reservoir storages (m3)
        newStorageAtLakeAndReservoirs = npareatotal(newStorageAtLakeAndReservoirs, self.var.waterBodyIdsC)

        # inflow (m3/day)
        self.var.inflowC = newStorageAtLakeAndReservoirs - self.var.waterBodyStorageC

        # inflowInM3PerSec (m3/s)
        inflowInM3PerSec = self.var.inflowC / self.var.DtSec

        # updating average (short term) inflow (m3/s)
        # - needed to constrain lake outflow:

        # ~ self.var.avgInflow = np.maximum(0.,
        # ~ (self.var.avgInflow * \
        # ~ (np.minimum(maxTimestepsToAvgDischargeShort,
        # ~ timestepsToAvgDischarge)- 1.) + \
        # ~ (inflowInM3PerSec /\
        # ~ vos.secondsPerDay()) * 1.) / \
        # ~ (np.minimum(maxTimestepsToAvgDischargeShort,
        # ~ timestepsToAvgDischarge)))         # Edwin's old formula
#
        deltaInflow = inflowInM3PerSec - self.var.avgInflowC
        self.var.avgInflowC = self.var.avgInflowC + deltaInflow / \
                 np.minimum(maxTimestepsToAvgDischargeShort, self.var.timestepsToAvgDischarge)
        self.var.avgInflowC = np.maximum(0.0, self.var.avgInflowC)

        # updating waterBodyStorage (m3)
        self.var.waterBodyStorageC = newStorageAtLakeAndReservoirs.copy()

        # --------------------------------------------------------------------------
        # --------------------------------------------------------------------------

    def weirFormula(self, waterHeight, weirWidth):
        # output: m3/s
        sillElev = 0.0
        weirCoef = 1.0
        # m3/s
        weirFormula = (1.7 * weirCoef * np.maximum(0, waterHeight - sillElev) ** 1.5) * weirWidth
        return (weirFormula)

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------


    def getLakeOutflow(self, avgChannelDischarge=None):

        # waterHeight (m): temporary variable, a function of storage:
        minWaterHeight = 0.000  # (m) Rens used 0.001 m
        waterHeight = np.maximum(minWaterHeight,
                                 (self.var.waterBodyStorageC - self.var.waterBodyCapC) / self.var.waterBodyAreaC)

        # weirWidth (m) : estimated from avgOutflow (m3/s)
        avgOutflowC = self.var.avgOutflowC

        if avgChannelDischarge != None:
            avgOutflowC = np.where(avgOutflowC > 0., avgOutflowC, avgChannelDischarge)
            avgOutflowC = npareamaximum(avgOutflowC, self.var.waterBodyIds)
        bankfullWidth = 4.8 * (avgOutflowC ** 0.5)
        weirWidthUsed = bankfullWidth.copy()
        weirWidthUsed = np.maximum(weirWidthUsed, self.var.minWeirWidthC)

        # TODO: minWeirWidth based on the GRanD database
        weirWidthUsed = np.where(self.var.waterBodyIdsC > 0., weirWidthUsed, 0.)

        # lakeOutflow = weirFormula >= avgInflow <= waterBodyStorage  # m3/day
        lakeOutflow = np.maximum(self.var.lakes_reservoirs_module.weirFormula(waterHeight, weirWidthUsed), self.var.avgInflowC) * self.var.DtSec
        lakeOutflow = np.minimum(self.var.waterBodyStorageC, lakeOutflow)

        # m3/day
        return (lakeOutflow)

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------

    def getReservoirOutflow(self, avgChannelDischarge=None, downstreamDemand=None):

        minWaterHeight = 0.000  # (m) Rens used 0.001 m
        reservoirWaterHeight = np.maximum(minWaterHeight, (self.var.waterBodyStorageC) / self.var.waterBodyAreaC)

        # avgOutflow (m3/s)
        avgOutflowC = self.var.avgOutflowC
        if avgChannelDischarge != None:
            avgOutflowC = np.where(avgOutflowC > 0., avgOutflowC, avgChannelDischarge)
            avgOutflowC = npareamaximum(avgOutflowC, self.var.waterBodyIdsC)


        # calculate resvOutflow (based on reservoir storage and avgDischarge):
        # - unit: m3/day (Note that avgDischarge is given in m3/s)
        # - using reductionFactor in such a way that:
        #   - if relativeCapacity < minResvrFrac : release is terminated
        #   - if relativeCapacity > maxResvrFrac : longterm Average
        reductionFactor = np.minimum(1., np.maximum(0., \
                self.var.waterBodyStorageC - self.var.minResvrFracC * self.var.waterBodyCapC) / \
                (self.var.maxResvrFracC - self.var.minResvrFracC) * self.var.waterBodyCapC)
        # m3/day
        resvOutflow = reductionFactor * avgOutflowC * self.var.DtSec

        # maximum release <= average inflow (especially during dry condition) # m3/day
        resvOutflow = np.maximum(0, np.minimum(resvOutflow, self.var.avgInflowC * self.var.DtSec))

        # downstream demand (m3/day)
        if downstreamDemand == None:
            downstreamDemand = 0.0
        else:
            print("We still have to define downstreamDemand.")
        # reduce demand if storage < lower limit
        reductionFactor = getValDivZero(downstreamDemand, self.var.minResvrFracC * self.var.waterBodyCapC, 1e-39)
        downstreamDemand = np.minimum(downstreamDemand, downstreamDemand * reductionFactor)
        # resvOutflow > downstreamDemand # m3/day
        resvOutflow = np.maximum(resvOutflow, downstreamDemand)

        # additional release if storage > upper limit
        ratioQBankfull = 2.3
        estmStorage = np.maximum(0., self.var.waterBodyStorageC - resvOutflow)

        a1 = np.maximum(0.0, estmStorage - self.var.maxResvrFracC * self.var.waterBodyCapC)
        a2 = (1. - self.var.maxResvrFracC) * self.var.waterBodyCapC
        with np.errstate(invalid='ignore', divide='ignore'):
            a3 = np.where(a2 > 0,a1/a2, 0.0)
        a4 =  np.maximum(0.0, ratioQBankfull * avgOutflowC * self.var.DtSec - resvOutflow)

        floodOutflow = np.maximum(0.0, estmStorage - self.var.waterBodyCapC) + a3 * a4

        floodOutflow = np.maximum(0.0,
                                  np.minimum(floodOutflow, estmStorage - self.var.maxResvrFracC * self.var.waterBodyCapC))
        resvOutflow = resvOutflow + floodOutflow

        # maximum release if storage > upper limit
        resvOutflow = np.where(self.var.waterBodyStorageC > self.var.maxResvrFracC * self.var.waterBodyCapC, \
                               np.minimum(resvOutflow, np.maximum(0, self.var.waterBodyStorageC - \
                               self.var.maxResvrFracC * self.var.waterBodyCapC)),resvOutflow)

        return (resvOutflow)  # unit: m3/day

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------

    def getWaterBodyOutflow(self, maxTimestepsToAvgDischargeLong, downstreamDemand=None, avgChannelDischarge=None):

        # outflow from water bodies with lake type (m3/day):
        if self.var.includeLakes == "True":
            lakeOutflow = self.var.lakes_reservoirs_module.getLakeOutflow(avgChannelDischarge)
            self.var.waterBodyOutflowC = np.where(self.var.waterBodyTypC == 1, lakeOutflow, self.var.waterBodyOutflowC)

            # outflow from water bodies with reservoir type (m3/day):
        if self.var.includeReservoirs == "True":
            reservoirOutflow = self.var.lakes_reservoirs_module.getReservoirOutflow(avgChannelDischarge)
            self.var.waterBodyOutflowC = np.where(self.var.waterBodyTypC == 2, reservoirOutflow, self.var.waterBodyOutflowC)

        # limit outflow to available storage # unit: m3/day
        # to avoid flip flop
        factor = 0.33
        self.var.waterBodyOutflowC = np.minimum(self.var.waterBodyStorageC * factor, self.var.waterBodyOutflowC)
        waterBodyOutflowInM3PerSec = self.var.waterBodyOutflowC / self.var.DtSec  # unit: m3/s

        # update average discharge (outflow) m3/s
        # ~ self.var.avgOutflow = (self.var.avgOutflow * \
        # ~ (np.minimum(maxTimestepsToAvgDischargeLong,
        # ~ self.var.timestepsToAvgDischarge)- 1.) + \
        # ~ (waterBodyOutflowInM3PerSec /\
        # ~ vos.secondsPerDay()) * 1.) / \
        # ~ (np.minimum(maxTimestepsToAvgDischargeLong,
        # ~ self.var.timestepsToAvgDischarge))         # Edwin's old formula

        deltaOutflow = waterBodyOutflowInM3PerSec - self.var.avgOutflowC
        self.var.avgOutflowC = self.var.avgOutflowC + deltaOutflow / \
                      np.minimum(maxTimestepsToAvgDischargeLong, self.var.timestepsToAvgDischarge)
        self.var.avgOutflowC = np.maximum(0.0, self.var.avgOutflowC)

        # update waterBodyStorage (after outflow):
        self.var.waterBodyStorageC = self.var.waterBodyStorageC - self.var.waterBodyOutflowC

        # --------------------------------------------------------------------------
        # --------------------------------------------------------------------------






# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------


    def dynamic(self,storageAtLakeAndReservoirs, downstreamDemand = None, avgChannelDischarge = None):
        """ dynamic part of the lakes and reservoirs module
        """
        i = 2
        # self.var.currentTimeStep()
        #self.var.WaterBodies.dynamic(storageAtLakeAndReservoirs)
        #    self.var.timestepsToAvgDischarge, self.var.maxTimestepsToAvgDischargeShort, self.var.maxTimestepsToAvgDischargeLong)

        # unit: m3/s
        storageAtLakeAndReservoirsC = np.compress(self.var.compressID, storageAtLakeAndReservoirs)

        self.var.waterBodyOutflowC = np.compress(self.var.compressID, globals.inZero)

        if self.var.includeLakes == "True" or self.var.includeReservoirs == "True":
            # obtain inflow (and update storage)
            self.var.lakes_reservoirs_module.moveFromChannelToWaterBody(storageAtLakeAndReservoirsC, self.var.timestepsToAvgDischarge, self.var.maxTimestepsToAvgDischargeShort)

            # calculate outflow (and update storage)
            self.var.lakes_reservoirs_module.getWaterBodyOutflow(self.var.maxTimestepsToAvgDischargeLong, downstreamDemand, avgChannelDischarge)



