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

    def getParameterFiles(self):

        #           self.var.cellArea    self.var..Ldd self.var.cellLength    ,self.var.cellSize
        # parameters for Water Bodies: fracWat
        #                              waterBodyIds
        #                              waterBodyOut
        #                              waterBodyArea
        #                              waterBodyTyp
        #                              waterBodyCap

        #self.cellArea = cellArea
        self.var.includeLakes = "True"
        self.var.includeReservoirs = "True"

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
            waterBodyOut = boolean(0)
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
                waterBodyOutPcr = ifthenelse(scalar(waterBodyIdsPcr) > 0, waterBodyOutPcr, 0.0)

                # correcting water body ids
                waterBodyIdsPcr = ifthen( scalar(waterBodyIdsPcr) > 0., subcatchment(self.var.Ldd, waterBodyOutPcr))

                # boolean map for water body outlets:
                waterBodyOutPcr = ifthen( pcr.scalar(waterBodyOutPcr) > 0., pcr.boolean(1))

                self.var.waterBodyIds = compressArray(waterBodyIdsPcr)
                self.var.waterBodyOut = compressArray(waterBodyOutPcr)



                # reservoir surface area (m2):
                resSfArea = 1000. * 1000. * readnetcdf2(self.var.waterbody_file, self.var.CalendarDate, "yearly", value='resSfAreaInp')

                resSfArea = npareaaverage(resSfArea, self.var.waterBodyIds)


                # water body surface area (m2): (lakes and reservoirs)
                self.var.waterBodyArea = np.maximum(npareatotal(self.var.fracWat * self.var.cellArea, self.var.waterBodyIds),
                                        npareaaverage( resSfArea, self.var.waterBodyIds))
                self.var.waterBodyArea = np.where(self.var.waterBodyArea > 0., self.var.waterBodyArea)

                # correcting water body ids and outlets (excluding all water bodies with surfaceArea = 0)
                self.var.waterBodyIds = np.where(self.var.waterBodyArea > 0.,self.var.waterBodyIds)
                self.var.waterBodyOut = np.where(self.var.waterBodyIds > 0, self.var.waterBodyOut)

            # water body types:
            # - 2 = reservoirs (regulated discharge)
            # - 1 = lakes (weirFormula)
            # - 0 = non lakes or reservoirs (e.g. wetland)
            self.var.waterBodyTyp = pcr.nominal(0)

            if self.var.includeLakes == "True" or self.var.includeReservoirs == "True":
                self.var.waterBodyTyp = readnetcdf2(self.var.waterbody_file, self.var.CalendarDate, "yearly", value='waterBodyTyp')

                self.var.waterBodyTyp = np.where( pcr.scalar(self.var.waterBodyTyp) > 0, pcr.nominal(self.var.waterBodyTyp))
                self.var.waterBodyTyp = np.where( pcr.scalar(self.var.waterBodyIds) > 0, pcr.nominal(self.var.waterBodyTyp))
                self.var.waterBodyTyp = pcr.areamajority(self.var.waterBodyTyp, self.var.waterBodyIds)
                self.var.waterBodyTyp = np.where( pcr.scalar(self.var.waterBodyTyp) > 0, pcr.nominal(self.var.waterBodyTyp))
                self.var.waterBodyTyp = np.where(pcr.boolean(self.var.waterBodyIds), self.var.waterBodyTyp)

                # correcting water body ids and outlets:
                self.var.waterBodyIds = np.where(pcr.boolean(self.var.waterBodyTyp), self.var.waterBodyIds)
                self.var.waterBodyOut = np.where(pcr.boolean(self.var.waterBodyIds), self.var.waterBodyOut)

            # correcting water bodies attributes if reservoirs are ignored (for natural runs):
            if self.var.includeLakes == "True" and self.var.includeReservoirs == "False":
                # correcting fracWat
                reservoirExcluded = pcr.cover( np.where(pcr.scalar(self.var.waterBodyTyp) == 2., pcr.boolean(1)), pcr.boolean(0))
                maxWaterBodyAreaExcluded = np.where(reservoirExcluded, self.var.waterBodyArea / pcr.areatotal( \
                                                      pcr.scalar(reservoirExcluded), self.var.waterBodyIds))
                maxfractionWaterExcluded = pcr.cover( maxWaterBodyAreaExcluded / self.var.cellArea, 0.0)
                maxfractionWaterExcluded = np.minimum(1.0, maxfractionWaterExcluded)
                maxfractionWaterExcluded = np.minimum(self.var.fracWat, maxfractionWaterExcluded)

                self.var.fracWat = self.var.fracWat - maxfractionWaterExcluded
                self.var.fracWat = np.maximum(0., self.var.fracWat)
                self.var.fracWat = np.minimum(1., self.var.fracWat)

                self.var.waterBodyArea = np.where(pcr.scalar(self.var.waterBodyTyp) < 2.,self.var.waterBodyArea)
                self.var.waterBodyTyp = np.where(pcr.scalar(self.var.waterBodyTyp) < 2., self.var.waterBodyTyp)
                self.var.waterBodyIds = np.where(pcr.scalar(self.var.waterBodyTyp) > 0., self.var.waterBodyIds)
                self.var.waterBodyOut = np.where(pcr.scalar(self.var.waterBodyIds) > 0., self.var.waterBodyOut)

            # reservoir maximum capacity (m3):
            self.var.resMaxCap = pcr.scalar(0.0)
            self.var.waterBodyCap = pcr.scalar(0.0)

            if self.var.includeReservoirs == "True":

                # reservoir maximum capacity (m3):
                self.var.resMaxCap = 1000. * 1000. * readnetcdf2(self.var.waterbody_file, self.var.CalendarDate, "yearly", value='resMaxCapInp')
                self.var.resMaxCap = np.where(self.var.resMaxCap > 0, self.var.resMaxCap)
                self.var.resMaxCap = pcr.areaaverage(self.var.resMaxCap, self.var.waterBodyIds)

                # water body capacity (m3): (lakes and reservoirs)
                # Note: Most of lakes have capacities > 0.
                self.var.waterBodyCap = pcr.cover(self.var.resMaxCap, 0.0)
                self.var.waterBodyCap = np.where(pcr.boolean(self.var.waterBodyIds), self.var.waterBodyCap)

                # correcting water body types:
                self.var.waterBodyTyp = np.where(self.var.waterBodyCap > 0., self.var.waterBodyTyp, \
                        np.where(pcr.scalar(self.var.waterBodyTyp) == 2, pcr.nominal(1), self.var.waterBodyTyp))
                self.var.waterBodyTyp = np.where(pcr.scalar(self.var.waterBodyTyp) > 0., self.var.waterBodyTyp)

                # final corrections:
                self.var.waterBodyTyp = np.where(self.var.waterBodyArea > 0., self.var.waterBodyTyp)
                self.var.waterBodyIds = np.where(pcr.scalar(self.var.waterBodyTyp) > 0., self.var.waterBodyIds)
                self.var.waterBodyOut = np.where(pcr.scalar(self.var.waterBodyIds) > 0., self.var.waterBodyOut)

        # For each new reservoir (introduced at the beginning of the year)
        # initiating storage, average inflow and outflow:
        self.var.waterBodyStorage = pcr.cover(self.var.waterBodyStorage, 0.0)
        self.var.avgInflow = pcr.cover(self.var.avgInflow, 0.0)
        self.var.avgOutflow = pcr.cover(self.var.avgOutflow, 0.0)

    # --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the lakes and reservoirs module
        """
        i = 2

