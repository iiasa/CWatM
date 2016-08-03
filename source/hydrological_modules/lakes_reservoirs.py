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

            self.var.minResvrFrac = loadmap('minResvrFrac')
            self.var.maxResvrFrac = loadmap('maxResvrFrac')
            self.var.minWeirWidth = loadmap('minWeirWidth')


        # initial conditions

        # lake and reservoir storages = waterBodyStorage (m3)
        # - values are given for the entire lake / reservoir cells
        self.var.waterBodyStorage = loadmap('waterBodyStorageIni')
        self.var.avgInflow = loadmap('avgInflowLakeReservIni')
        self.var.avgOutflow = loadmap('avgOutflowDischargeIni')



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
        self.var.waterBodyIds = globals.inZero.astype(np.int32)
        self.var.waterBodyOut = globals.inZero.astype(np.bool8)
        self.var.waterBodyArea = globals.inZero.copy()  # waterBody surface areas


        #self.var.waterBodyOut = pcr.boolean(0)  # waterBody outlets
        #self.var.waterBodyArea = pcr.scalar(0.)  # waterBody surface areas
        # d.astype(np.int32) , d.astype(np.bool8)


        if option['includeWaterBodies']:
            waterBodyIdsPcr = nominal(0)
            waterBodyOutPcr = boolean(0)
        self.var.fracWat = readnetcdf2(self.var.waterbody_file, self.var.CalendarDate, "yearly", value= 'fracWaterInp')
        self.var.fracWat = np.maximum(0.0, self.var.fracWat)
        self.var.fracWat = np.minimum(1.0, self.var.fracWat)



        if self.var.includeLakes == "True" or self.var.includeReservoirs == "True":
            # water body ids
            self.var.waterBodyIds = readnetcdf2(self.var.waterbody_file, self.var.CalendarDate, "yearly",value='waterBodyIds')
            waterBodyIdsPcr = nominal(decompress(self.var.waterBodyIds))
            ##self.var.waterBodyIds = np.where( self.var.waterBodyIds > 0., pcr.nominal(self.var.waterBodyIds))


            # Pcraster
            # water body outlets:
            wbCatchment = catchmenttotal(scalar(1), self.var.Ldd)
            # = outlet ids
            waterBodyOutPcr = ifthen(wbCatchment == areamaximum(wbCatchment, waterBodyIdsPcr), waterBodyIdsPcr)
            waterBodyOutPcr = ifthenelse(scalar(waterBodyIdsPcr) > 0, waterBodyOutPcr, 0)

            # correcting water body ids
            waterBodyIdsPcr = ifthenelse( scalar(waterBodyIdsPcr) > 0., subcatchment(self.var.Ldd, waterBodyOutPcr),0)

            # boolean map for water body outlets:
            self.var.waterBodyIds = compressArray(waterBodyIdsPcr).astype(np.int32)
            self.var.waterBodyOut = compressArray(waterBodyOutPcr).astype(np.bool8)



            # reservoir surface area (m2):
            resSfArea = 1000. * 1000. * readnetcdf2(self.var.waterbody_file, self.var.CalendarDate, "yearly", value='resSfAreaInp')
            resSfArea = npareaaverage(resSfArea, self.var.waterBodyIds)


            # water body surface area (m2): (lakes and reservoirs)
            self.var.waterBodyArea = np.maximum(npareatotal(self.var.fracWat * self.var.cellArea, self.var.waterBodyIds),
                                        npareaaverage( resSfArea, self.var.waterBodyIds))

            # correcting water body ids and outlets (excluding all water bodies with surfaceArea = 0)
            self.var.waterBodyIds = np.where(self.var.waterBodyArea > 0.,self.var.waterBodyIds, 0)
            self.var.waterBodyOut = np.where(self.var.waterBodyIds > 0, self.var.waterBodyOut, False)

        # water body types:
        # - 2 = reservoirs (regulated discharge)
        # - 1 = lakes (weirFormula)
        # - 0 = non lakes or reservoirs (e.g. wetland)
        self.var.waterBodyTyp =globals.inZero.astype(np.int32)

        if self.var.includeLakes == "True" or self.var.includeReservoirs == "True":
            self.var.waterBodyTyp = readnetcdf2(self.var.waterbody_file, self.var.CalendarDate, "yearly", value='waterBodyTyp')
            self.var.waterBodyTyp = np.where( self.var.waterBodyIds > 0, self.var.waterBodyTyp.astype(np.int32), 0)

            self.var.waterBodyTyp = compressArray(areamajority(decompress(self.var.waterBodyTyp), decompress(self.var.waterBodyIds)))

            self.var.waterBodyTyp = np.where(self.var.waterBodyIds > 0, self.var.waterBodyTyp.astype(np.int32), 0)

            # correcting water body ids and outlets:
            self.var.waterBodyIds = np.where(self.var.waterBodyTyp > 0, self.var.waterBodyIds,0)
            self.var.waterBodyOut = np.where(self.var.waterBodyIds > 0, self.var.waterBodyOut, False)


        # correcting water bodies attributes if reservoirs are ignored (for natural runs):
        if self.var.includeLakes == "True" and self.var.includeReservoirs == "False":
            # correcting fracWat
            reservoirExcluded = globals.inZero.copy()
            reservoirExcluded = np.where(self.var.waterBodyTyp == 2, 1.0, 0.1)
            maxWaterBodyAreaExcluded = np.where(reservoirExcluded, self.var.waterBodyArea / \
                                 npareatotal(reservoirExcluded, self.var.waterBodyIds))
            maxfractionWaterExcluded = maxWaterBodyAreaExcluded / self.var.cellArea
            maxfractionWaterExcluded = np.minimum(1.0, maxfractionWaterExcluded)
            maxfractionWaterExcluded = np.minimum(self.var.fracWat, maxfractionWaterExcluded)

            self.var.fracWat = self.var.fracWat - maxfractionWaterExcluded
            self.var.fracWat = np.maximum(0., self.var.fracWat)
            self.var.fracWat = np.minimum(1., self.var.fracWat)

            self.var.waterBodyArea = np.where(self.var.waterBodyTyp < 2,self.var.waterBodyArea, 0.)
            self.var.waterBodyTyp = np.where(self.var.waterBodyTyp < 2, self.var.waterBodyTyp, 0)
            self.var.waterBodyIds = np.where(self.var.waterBodyTyp > 0, self.var.waterBodyIds, 0)
            self.var.waterBodyOut = np.where(self.var.waterBodyIds > 0, self.var.waterBodyOut, False)

        # reservoir maximum capacity (m3):
        self.var.resMaxCap = globals.inZero.copy()
        self.var.waterBodyCap = globals.inZero.copy()

        if self.var.includeReservoirs == "True":

            # reservoir maximum capacity (m3):
            self.var.resMaxCap = 1000. * 1000. * readnetcdf2(self.var.waterbody_file, self.var.CalendarDate, "yearly", value='resMaxCapInp')
            self.var.resMaxCap = np.where(self.var.resMaxCap > 0, self.var.resMaxCap, 0.)
            self.var.resMaxCap = npareaaverage(self.var.resMaxCap, self.var.waterBodyIds)

            # water body capacity (m3): (lakes and reservoirs)
            # Note: Most of lakes have capacities > 0.
            #self.var.waterBodyCap = pcr.cover(self.var.resMaxCap, 0.0)
            self.var.waterBodyCap = np.where(self.var.waterBodyIds > 0, self.var.waterBodyCap, 0.0)

            # correcting water body types:
            self.var.waterBodyTyp = np.where(self.var.waterBodyCap > 0., self.var.waterBodyTyp, \
                     np.where(self.var.waterBodyTyp == 2, 1, self.var.waterBodyTyp))

        # final corrections:
        self.var.waterBodyTyp = np.where(self.var.waterBodyArea > 0., self.var.waterBodyTyp, 0)
        self.var.waterBodyIds = np.where(self.var.waterBodyTyp > 0, self.var.waterBodyIds, 0)
        self.var.waterBodyOut = np.where(self.var.waterBodyIds > 0, self.var.waterBodyOut, False)

        # For each new reservoir (introduced at the beginning of the year)
        # initiating storage, average inflow and outflow:
        self.var.waterBodyStorage = np.where(self.var.waterBodyStorage > 0,self.var.waterBodyStorage, 0.0)
        self.var.avgInflow = np.where(self.var.avgInflow > 0,self.var.avgInflow, 0.0)
        self.var.avgOutflow = np.where(self.var.avgOutflow > 0, self.var.avgOutflow , 0.0)

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
    def moveFromChannelToWaterBody(self, newStorageAtLakeAndReservoirs, timestepsToAvgDischarge, maxTimestepsToAvgDischargeShort):


        # new lake and/or reservoir storages (m3)
        newStorageAtLakeAndReservoirs = npareatotal(newStorageAtLakeAndReservoirs, self.var.waterBodyIds)

        # inflow (m3/day)
        self.var.inflow = newStorageAtLakeAndReservoirs - self.var.waterBodyStorage

        # inflowInM3PerSec (m3/s)
        inflowInM3PerSec = self.var.inflow / self.var.DtSec

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
        deltaInflow = inflowInM3PerSec - self.var.avgInflow
        self.var.avgInflow = self.var.avgInflow + deltaInflow / \
                 np.minimum(maxTimestepsToAvgDischargeShort, self.var.timestepsToAvgDischarge)
        self.var.avgInflow = np.maximum(0.0, self.var.avgInflow)

        # updating waterBodyStorage (m3)
        self.var.waterBodyStorage = newStorageAtLakeAndReservoirs.copy()

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
                                 (self.var.waterBodyStorage - self.var.waterBodyCap) / self.var.waterBodyArea)

        # weirWidth (m) : estimated from avgOutflow (m3/s)
        avgOutflow = self.var.avgOutflow

        if avgChannelDischarge != None:
            avgOutflow = np.where(avgOutflow > 0., avgOutflow, avgChannelDischarge)
            avgOutflow = npareamaximum(avgOutflow, self.var.waterBodyIds)
        bankfullWidth = 4.8 * (avgOutflow ** 0.5)
        weirWidthUsed = bankfullWidth.copy()
        weirWidthUsed = np.maximum(weirWidthUsed, self.var.minWeirWidth)
        weirWidthUsed = np.where(self.var.waterBodyIds > 0., weirWidthUsed, 0.)

        # TODO: minWeirWidth based on the GRanD database
        weirWidthUsed = np.where(self.var.waterBodyIds > 0., weirWidthUsed, 0.)

        # lakeOutflow = weirFormula >= avgInflow <= waterBodyStorage  # m3/day
        lakeOutflow = np.maximum(self.var.lakes_reservoirs_module.weirFormula(waterHeight, weirWidthUsed), self.var.avgInflow) * self.var.DtSec
        lakeOutflow = np.minimum(self.var.waterBodyStorage, lakeOutflow)

        # m3/day
        return (lakeOutflow)

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------

    def getReservoirOutflow(self, avgChannelDischarge=None, downstreamDemand=None):

        minWaterHeight = 0.000  # (m) Rens used 0.001 m
        reservoirWaterHeight = np.maximum(minWaterHeight, (self.var.waterBodyStorage) / self.var.waterBodyArea)

        # avgOutflow (m3/s)
        avgOutflow = self.var.avgOutflow
        if avgChannelDischarge != None:
            avgOutflow = np.where(avgOutflow > 0., avgOutflow, avgChannelDischarge)
            avgOutflow = npareamaximum(avgOutflow, self.var.waterBodyIds)
            # avgOutflow = pcr.cover(avgOutflow, 0.0)

        # calculate resvOutflow (based on reservoir storage and avgDischarge):
        # - unit: m3/day (Note that avgDischarge is given in m3/s)
        # - using reductionFactor in such a way that:
        #   - if relativeCapacity < minResvrFrac : release is terminated
        #   - if relativeCapacity > maxResvrFrac : longterm Average
        reductionFactor = np.minimum(1., np.maximum(0., \
                                                    self.var.waterBodyStorage - self.var.minResvrFrac * self.var.waterBodyCap) / \
                                     (self.var.maxResvrFrac - self.var.minResvrFrac) * self.var.waterBodyCap)
        # m3/day
        resvOutflow = reductionFactor * avgOutflow * self.var.DtSec

        # maximum release <= average inflow (especially during dry condition) # m3/day
        resvOutflow = np.maximum(0, np.minimum(resvOutflow, self.var.avgInflow * self.var.DtSec))

        # downstream demand (m3/day)
        if downstreamDemand == None:
            downstreamDemand = 0.0
        else:
            print("We still have to define downstreamDemand.")
        # reduce demand if storage < lower limit
        reductionFactor = getValDivZero(downstreamDemand, self.var.minResvrFrac * self.var.waterBodyCap, 1e-39)
        downstreamDemand = np.minimum(downstreamDemand, downstreamDemand * reductionFactor)
        # resvOutflow > downstreamDemand # m3/day
        resvOutflow = np.maximum(resvOutflow, downstreamDemand)

        # additional release if storage > upper limit
        ratioQBankfull = 2.3
        estmStorage = np.maximum(0., self.var.waterBodyStorage - resvOutflow)

        h1 = np.maximum(0.0, estmStorage - self.var.maxResvrFrac * self.var.waterBodyCap) / \
             ((1. - self.var.maxResvrFrac) * self.var.waterBodyCap) * \
             np.maximum(0.0, ratioQBankfull * avgOutflow * self.var.DtSec - resvOutflow)
        floodOutflow = np.maximum(0.0, estmStorage - self.var.waterBodyCap) + h1

        floodOutflow = np.maximum(0.0,
                                  np.minimum(floodOutflow, estmStorage - self.var.maxResvrFrac * self.var.waterBodyCap))
        resvOutflow = resvOutflow + floodOutflow

        # maximum release if storage > upper limit
        resvOutflow = np.where(self.var.waterBodyStorage > self.var.maxResvrFrac * self.var.waterBodyCap, \
                               np.minimum(resvOutflow, np.maximum(0, self.var.waterBodyStorage - \
                                                                  self.var.maxResvrFrac * self.var.waterBodyCap)),
                               resvOutflow)

        return (resvOutflow)  # unit: m3/day

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------

    def getWaterBodyOutflow(self, maxTimestepsToAvgDischargeLong, downstreamDemand=None, avgChannelDischarge=None):

        # outflow from water bodies with lake type (m3/day):
        if self.var.includeLakes == "True":
            lakeOutflow = self.var.lakes_reservoirs_module.getLakeOutflow(avgChannelDischarge)
            self.var.waterBodyOutflow = np.where(self.var.waterBodyTyp == 1, lakeOutflow, self.var.waterBodyOutflow)

            # outflow from water bodies with reservoir type (m3/day):
        if self.var.includeReservoirs == "True":
            reservoirOutflow = self.var.lakes_reservoirs_module.getReservoirOutflow(avgChannelDischarge)
            self.var.waterBodyOutflow = np.where(self.var.waterBodyTyp == 2, reservoirOutflow, self.var.waterBodyOutflow)

        # limit outflow to available storage # unit: m3/day
        # to avoid flip flop
        factor = 0.33
        self.var.waterBodyOutflow = np.minimum(self.var.waterBodyStorage * factor, self.var.waterBodyOutflow)
        waterBodyOutflowInM3PerSec = self.var.waterBodyOutflow / self.var.DtSec  # unit: m3/s

        # update average discharge (outflow) m3/s
        # ~ self.var.avgOutflow = (self.var.avgOutflow * \
        # ~ (np.minimum(maxTimestepsToAvgDischargeLong,
        # ~ self.var.timestepsToAvgDischarge)- 1.) + \
        # ~ (waterBodyOutflowInM3PerSec /\
        # ~ vos.secondsPerDay()) * 1.) / \
        # ~ (np.minimum(maxTimestepsToAvgDischargeLong,
        # ~ self.var.timestepsToAvgDischarge))         # Edwin's old formula

        deltaOutflow = waterBodyOutflowInM3PerSec - self.var.avgOutflow
        self.var.avgOutflow = self.var.avgOutflow + deltaOutflow / \
                      np.minimum(maxTimestepsToAvgDischargeLong, self.var.timestepsToAvgDischarge)
        self.var.avgOutflow = np.maximum(0.0, self.var.avgOutflow)

        # update waterBodyStorage (after outflow):
        self.var.waterBodyStorage = self.var.waterBodyStorage - self.var.waterBodyOutflow

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
        self.var.inflow =globals.inZero.copy()
        self.var.waterBodyOutflow = globals.inZero.copy()

        if self.var.includeLakes == "True" or self.var.includeReservoirs == "True":
            # obtain inflow (and update storage)
            self.var.lakes_reservoirs_module.moveFromChannelToWaterBody(storageAtLakeAndReservoirs, self.var.timestepsToAvgDischarge, self.var.maxTimestepsToAvgDischargeShort)

            # calculate outflow (and update storage)
            self.var.lakes_reservoirs_module.getWaterBodyOutflow(self.var.maxTimestepsToAvgDischargeLong, downstreamDemand, avgChannelDischarge)



