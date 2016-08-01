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

        if option['includeWaterBodies']:
            self.var.includeLakes = "True"
            self.var.includeReservoirs =  "True"

            self.var.waterbody_file = binding['waterBodyInputNC']
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

    def getParameterFiles(self, currTimeStep, cellArea, ldd, cellLengthFD, cellSizeInArcDeg):
        # parameters for Water Bodies: fracWat
        #                              waterBodyIds
        #                              waterBodyOut
        #                              waterBodyArea
        #                              waterBodyTyp
        #                              waterBodyCap

        self.cellArea = cellArea

        #    fracWat = fraction of surface water bodies
        self.fracWat = pcr.scalar(0.0)

        if self.includeWaterBodies == "True":
            if self.useNetCDF:
                self.fracWat = vos.netcdf2PCRobjClone(self.ncFileInp, 'fracWaterInp', \
                                                      currTimeStep.fulldate, useDoy='yearly', \
                                                      cloneMapFileName=self.cloneMap)
            else:
                self.fracWat = vos.readPCRmapClone( \
                    self.fracWaterInp + str(currTimeStep.year) + ".map",
                    self.cloneMap, self.tmpDir, self.inputDir)

        self.fracWat = pcr.cover(self.fracWat, 0.0)
        self.fracWat = pcr.max(0.0, self.fracWat)
        self.fracWat = pcr.min(1.0, self.fracWat)

        self.waterBodyIds = pcr.nominal(0)  # waterBody ids
        self.waterBodyOut = pcr.boolean(0)  # waterBody outlets
        self.waterBodyArea = pcr.scalar(0.)  # waterBody surface areas

        if self.includeLakes == "True" or \
                        self.includeReservoirs == "True":

            # water body ids
            if self.useNetCDF:
                self.waterBodyIds = vos.netcdf2PCRobjClone(self.ncFileInp, 'waterBodyIds', \
                                                           currTimeStep.fulldate, useDoy='yearly', \
                                                           cloneMapFileName=self.cloneMap)
            else:
                self.waterBodyIds = vos.readPCRmapClone( \
                    self.waterBodyIdsInp + str(currTimeStep.year) + ".map", \
                    self.cloneMap, self.tmpDir, self.inputDir, False, None, True)
            self.waterBodyIds = pcr.ifthen( \
                pcr.scalar(self.waterBodyIds) > 0., \
                pcr.nominal(self.waterBodyIds))

            # water body outlets:
            wbCatchment = pcr.catchmenttotal(pcr.scalar(1), ldd)
            self.waterBodyOut = pcr.ifthen(wbCatchment == \
                                           pcr.areamaximum(wbCatchment, \
                                                           self.waterBodyIds), \
                                           self.waterBodyIds)  # = outlet ids
            self.waterBodyOut = pcr.ifthen( \
                pcr.scalar(self.waterBodyIds) > 0., \
                self.waterBodyOut)

            # correcting water body ids
            self.waterBodyIds = pcr.ifthen( \
                pcr.scalar(self.waterBodyIds) > 0., \
                pcr.subcatchment(ldd, self.waterBodyOut))

            # boolean map for water body outlets:
            self.waterBodyOut = pcr.ifthen( \
                pcr.scalar(self.waterBodyOut) > 0., \
                pcr.boolean(1))

            # reservoir surface area (m2):
            if self.useNetCDF:
                resSfArea = 1000. * 1000. * \
                            vos.netcdf2PCRobjClone(self.ncFileInp, 'resSfAreaInp', \
                                                   currTimeStep.fulldate, useDoy='yearly', \
                                                   cloneMapFileName=self.cloneMap)
            else:
                resSfArea = 1000. * 1000. * vos.readPCRmapClone(
                    self.resSfAreaInp + str(currTimeStep.year) + ".map", \
                    self.cloneMap, self.tmpDir, self.inputDir)
            resSfArea = pcr.areaaverage(resSfArea, self.waterBodyIds)
            resSfArea = pcr.cover(resSfArea, 0.)

            # water body surface area (m2): (lakes and reservoirs)
            self.waterBodyArea = pcr.max(pcr.areatotal( \
                pcr.cover( \
                    self.fracWat * self.cellArea, 0.0), self.waterBodyIds),
                pcr.areaaverage( \
                    pcr.cover(resSfArea, 0.0), self.waterBodyIds))
            self.waterBodyArea = pcr.ifthen(self.waterBodyArea > 0., \
                                            self.waterBodyArea)

            # correcting water body ids and outlets (excluding all water bodies with surfaceArea = 0)
            self.waterBodyIds = pcr.ifthen(self.waterBodyArea > 0.,
                                           self.waterBodyIds)
            self.waterBodyOut = pcr.ifthen(pcr.boolean(self.waterBodyIds),
                                           self.waterBodyOut)

        # water body types:
        # - 2 = reservoirs (regulated discharge)
        # - 1 = lakes (weirFormula)
        # - 0 = non lakes or reservoirs (e.g. wetland)
        self.waterBodyTyp = pcr.nominal(0)

        if self.includeLakes == "True" or \
                        self.includeReservoirs == "True":

            if self.useNetCDF:
                self.waterBodyTyp = vos.netcdf2PCRobjClone(self.ncFileInp, 'waterBodyTyp', \
                                                           currTimeStep.fulldate, useDoy='yearly', \
                                                           cloneMapFileName=self.cloneMap)
            else:
                self.waterBodyTyp = vos.readPCRmapClone(
                    self.waterBodyTypInp + str(currTimeStep.year) + ".map", \
                    self.cloneMap, self.tmpDir, self.inputDir, False, None, True)

            self.waterBodyTyp = pcr.ifthen( \
                pcr.scalar(self.waterBodyTyp) > 0, \
                pcr.nominal(self.waterBodyTyp))
            self.waterBodyTyp = pcr.ifthen( \
                pcr.scalar(self.waterBodyIds) > 0, \
                pcr.nominal(self.waterBodyTyp))
            self.waterBodyTyp = pcr.areamajority(self.waterBodyTyp, \
                                                 self.waterBodyIds)
            self.waterBodyTyp = pcr.ifthen( \
                pcr.scalar(self.waterBodyTyp) > 0, \
                pcr.nominal(self.waterBodyTyp))
            self.waterBodyTyp = pcr.ifthen(pcr.boolean(self.waterBodyIds),
                                           self.waterBodyTyp)

            # correcting water body ids and outlets:
            self.waterBodyIds = pcr.ifthen(pcr.boolean(self.waterBodyTyp),
                                           self.waterBodyIds)
            self.waterBodyOut = pcr.ifthen(pcr.boolean(self.waterBodyIds),
                                           self.waterBodyOut)

        # correcting water bodies attributes if reservoirs are ignored (for natural runs):
        if self.includeLakes == "True" and \
                        self.includeReservoirs == "False":
            # correcting fracWat
            reservoirExcluded = pcr.cover( \
                pcr.ifthen(pcr.scalar(self.waterBodyTyp) == 2., \
                           pcr.boolean(1)), pcr.boolean(0))
            maxWaterBodyAreaExcluded = pcr.ifthen(reservoirExcluded, \
                                                  self.waterBodyArea / \
                                                  pcr.areatotal( \
                                                      pcr.scalar(reservoirExcluded), \
                                                      self.waterBodyIds))
            maxfractionWaterExcluded = pcr.cover( \
                maxWaterBodyAreaExcluded / self.cellArea, 0.0)
            maxfractionWaterExcluded = pcr.min(1.0, maxfractionWaterExcluded)
            maxfractionWaterExcluded = pcr.min(self.fracWat, maxfractionWaterExcluded)

            self.fracWat = self.fracWat - maxfractionWaterExcluded
            self.fracWat = pcr.max(0., self.fracWat)
            self.fracWat = pcr.min(1., self.fracWat)

            self.waterBodyArea = pcr.ifthen(pcr.scalar(self.waterBodyTyp) < 2., \
                                            self.waterBodyArea)
            self.waterBodyTyp = pcr.ifthen(pcr.scalar(self.waterBodyTyp) < 2., \
                                           self.waterBodyTyp)
            self.waterBodyIds = pcr.ifthen(pcr.scalar(self.waterBodyTyp) > 0., \
                                           self.waterBodyIds)
            self.waterBodyOut = pcr.ifthen(pcr.scalar(self.waterBodyIds) > 0., \
                                           self.waterBodyOut)

        # reservoir maximum capacity (m3):
        self.resMaxCap = pcr.scalar(0.0)
        self.waterBodyCap = pcr.scalar(0.0)

        if self.includeReservoirs == "True":

            # reservoir maximum capacity (m3):
            if self.useNetCDF:
                self.resMaxCap = 1000. * 1000. * \
                                 vos.netcdf2PCRobjClone(self.ncFileInp, 'resMaxCapInp', \
                                                        currTimeStep.fulldate, useDoy='yearly', \
                                                        cloneMapFileName=self.cloneMap)
            else:
                self.resMaxCap = 1000. * 1000. * vos.readPCRmapClone( \
                    self.resMaxCapInp + str(currTimeStep.year) + ".map", \
                    self.cloneMap, self.tmpDir, self.inputDir)

            self.resMaxCap = pcr.ifthen(self.resMaxCap > 0, \
                                        self.resMaxCap)
            self.resMaxCap = pcr.areaaverage(self.resMaxCap, \
                                             self.waterBodyIds)

            # water body capacity (m3): (lakes and reservoirs)
            self.waterBodyCap = pcr.cover(self.resMaxCap, 0.0)  # Note: Most of lakes have capacities > 0.
            self.waterBodyCap = pcr.ifthen(pcr.boolean(self.waterBodyIds),
                                           self.waterBodyCap)

            # correcting water body types:
            self.waterBodyTyp = pcr.ifthenelse(self.waterBodyCap > 0., \
                                               self.waterBodyTyp, \
                                               pcr.ifthenelse(pcr.scalar(self.waterBodyTyp) == 2, \
                                                              pcr.nominal(1), \
                                                              self.waterBodyTyp))
            self.waterBodyTyp = \
                pcr.ifthen(pcr.scalar(self.waterBodyTyp) > 0., \
                           self.waterBodyTyp)

            # final corrections:
            self.waterBodyTyp = pcr.ifthen(self.waterBodyArea > 0., \
                                           self.waterBodyTyp)
            self.waterBodyIds = pcr.ifthen(pcr.scalar(self.waterBodyTyp) > 0., \
                                           self.waterBodyIds)
            self.waterBodyOut = pcr.ifthen(pcr.scalar(self.waterBodyIds) > 0., \
                                           self.waterBodyOut)

        # For each new reservoir (introduced at the beginning of the year)
        # initiating storage, average inflow and outflow:
        self.waterBodyStorage = pcr.cover(self.waterBodyStorage, 0.0)
        self.avgInflow = pcr.cover(self.avgInflow, 0.0)
        self.avgOutflow = pcr.cover(self.avgOutflow, 0.0)

    # --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the lakes and reservoirs module
        """
        i = 2

