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
from hydrological_modules.routing_reservoirs.routing_sub import *
from hydrological_modules.lakes import *

from management_modules.globals import *

#from pcraster.framework import *

class lakes_reservoirs(object):

    """
    # ************************************************************
    # ***** LAKES AND RESERVOIRS      ****************************
    # ************************************************************
    """

    def __init__(self, lakes_reservoirs_variable):
        self.var = lakes_reservoirs_variable
        self.lakes_module = lakes(self.var)

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the lakes + reservoirs module

        """


        # load reservoir parameters
        if option['includeWaterBodies']:

            self.var.waterbody_file = binding['waterBodyInputNC']

            self.var.minResvrFrac = loadmap('minResvrFrac') + globals.inZero
            self.var.maxResvrFrac = loadmap('maxResvrFrac') + globals.inZero
            self.var.minWeirWidth = loadmap('minWeirWidth') + globals.inZero


            # --------------- initial conditions ----------------------------
            # lake and reservoir storages = waterBodyStorage (m3)
            # values are given for the entire lake / reservoir cells
            self.var.waterBodyStorage = self.var.init_module.load_initial('waterBodyStorage') + globals.inZero
            self.var.avgInflow = self.var.init_module.load_initial('avgInflowLakeReserv') + globals.inZero
            self.var.avgOutflow = self.var.init_module.load_initial('avgOutflowDischarge') + globals.inZero





# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initWaterbodies(self):
        """
        :return:
        """


        if option['includeWaterBodies']:
            fracWat = self.var.fracVegCover[5]

            #self.var.waterBodyID = globals.inZero.copy()
            #self.var.waterBodyOut = globals.inZero.copy()
            #self.var.waterBodyTyp = globals.inZero.copy()
            #self.var.waterBodyArea = globals.inZero.copy()

            # load lakes/reservoirs map with a single ID for each lake/reservoir
            self.var.waterBodyID = readnetcdf2(self.var.waterbody_file, dateVar['currDate'], "yearly",value='waterBodyIds').astype(np.int64)
            #self.var.waterBodyID = np.where(self.var.waterBodyID == 10352,self.var.waterBodyID,0)
            """
            self.var.waterBodyID = self.var.waterBodyID * 0

            #self.var.waterBodyID[29] = 4
            #self.var.waterBodyID[30] = 4
            #self.var.waterBodyID[42] = 4

            self.var.waterBodyID[50] = 1

            self.var.waterBodyID[51] = 1
            self.var.waterBodyID[57] = 1
            self.var.waterBodyID[58] = 1
            self.var.waterBodyID[59] = 1
            self.var.waterBodyID[62] = 1
            self.var.waterBodyID[63] = 1

            self.var.waterBodyID[69] = 2
            self.var.waterBodyID[70] = 2
            self.var.waterBodyID[71] = 3
            """

            # calculate biggest outlet = biggest accumulation of ldd network
            lakeResmax = npareamaximum(self.var.UpArea1, self.var.waterBodyID)
            self.var.waterBodyOut = np.where(self.var.UpArea1 == lakeResmax,self.var.waterBodyID, 0)

            report(decompress(self.var.waterBodyID), "C:\work\output3/ID0.map")
            #report(decompress(self.var.waterBodyOut), "C:\work\output3/IDout0.map")


            # dismiss water bodies that a not subcatchment of an outlet
            sub = subcatchment1(self.var.dirUp, self.var.waterBodyOut,self.var.UpArea1)
            self.var.waterBodyID = np.where(self.var.waterBodyID > 0, sub, 0)

             #and again calculate outlets, because ID might have changed due to the operation before
            lakeResmax = npareamaximum(self.var.UpArea1, self.var.waterBodyID)
            self.var.waterBodyOut = np.where(self.var.UpArea1 == lakeResmax,self.var.waterBodyID, 0)


            report(decompress( self.var.waterBodyID), "C:\work\output3/ID.map")
            #self.var.waterBodyIndexC = np.nonzero(self.var.waterBodyIds)[0]


            # change ldd: put pits in where lakes are:
            self.var.ldd_LR = np.where( self.var.waterBodyID > 0, 5, self.var.lddCompress)
            # create new ldd without lakes reservoirs
            self.var.lddCompress_LR, dirshort_LR, self.var.dirUp_LR, self.var.dirupLen_LR, self.var.dirupID_LR, \
                self.var.downstruct_LR, self.var.catchment_LR, self.var.dirDown_LR, self.var.lendirDown_LR = defLdd2(self.var.ldd_LR)

            report(decompress(self.var.lddCompress_LR), "C:\work\output3/ldd_lr.map")

            # boolean map as mask map for compressing and decompressing
            self.var.compress_LR = self.var.waterBodyOut > 0
            self.var.decompress_LR = np.nonzero(self.var.waterBodyOut)[0]
            self.var.waterBodyOutC = np.compress(self.var.compress_LR, self.var.waterBodyOut)



            self.var.outflow = globals.inZero.copy()
            self.var.outLake = globals.inZero.copy()





            #self.var.UpArea1 = upstreamArea(self.var.dirDown_LR, dirshort_LR, globals.inZero + 1.0)
            #self.var.UpArea = upstreamArea(self.var.dirDown, dirshort_LR, self.var.cellArea)
            #d1 = downstream1(self.var.dirUp_LR, self.var.UpArea1)
            #up1 = upstream1(self.var.downstruct_LR, self.var.UpArea1)



            #ldd = pcraster.ldd(loadmap('Ldd',pcr=True))
            #sub1 = subcatchment(ldd, nominal(decompress(self.var.waterBodyOut)))


   # ------------------ End init ------------------------------------------------------------------------------------
   # ----------------------------------------------------------------------------------------------------------------





    def dynamic_inloop(self, NoRoutingExecuted):


        # ----------
        # inflow lakes
        # 1.  dis = upstream1(self.var.downstruct_LR, self.var.discharge)   # from river upstream
        # 2.  runoff = npareatotal(self.var.waterBodyID, self.var.waterBodyID)  # from cell itself
        # 3.                  # outflow from upstream lakes

        # ----------
        # outflow lakes res -> inflow ldd_LR
        # 1. out = upstream1(self.var.downstruct, self.var.outflow)


        # collect discharge from above waterbodies
        dis_LR = upstream1(self.var.downstruct_LR, self.var.discharge)
        # only where lakes are and unit convered to [m]
        dis_LR = np.where(self.var.waterBodyID > 0, dis_LR, 0.) * self.var.DtSec

        # sum up runoff and discharge on the lake
        inflow = npareatotal(dis_LR + self.var.runoff * self.var.cellArea , self.var.waterBodyID)
        # only once at the outlet
        inflow = np.where(self.var.waterBodyOut > 0, inflow, 0.) / self.var.noRoutingSteps

        # calculate total inflow into lakes and compress it to waterbodie outflow point
        # inflow to lake is discharge from upstream network + runoff directly into lake + outflow from upstream lakes
        inflowC = np.compress(self.var.compress_LR, inflow + self.var.outLake)

        # ------------------------------------------------------------
        # calculate outflow from lakes and reservoirs
        outflowC = self.lakes_module.dynamic_inloop(1, inflowC)

        #outflowC = self.var.storage_LR.copy()

        # ------------------------------------------------------------


        # decompress to normal maskarea size
        np.put(self.var.outflow,self.var.decompress_LR,outflowC)
        # shift outflow 1 cell downstream
        out1 = upstream1(self.var.downstruct, self.var.outflow)

        # everything with is not going to another lake is output to river network
        outLdd = np.where(self.var.waterBodyID > 0, 0, out1)

        # verything what i not goingt to the network is going to another lake
        outLake1 = np.where(self.var.waterBodyID > 0, out1,0)
        # sum up all inflow from other lakes
        outLake1 = npareatotal(outLake1, self.var.waterBodyID)
        # use only the value of the outflow point
        self.var.outLake = np.where(self.var.waterBodyOut > 0, outLake1, 0.)

        #report(decompress(runoff_LR), "C:\work\output3/run.map")


        return outLdd







        """



            fracWatC = np.compress(self.var.compressID > 0, self.var.fracVegCover[5])
            self.var.cellAreaC = np.compress(self.var.compressID, self.var.cellArea)


            # reservoir surface area (m2):
            resSfArea = 1000. * 1000. * readnetcdf2(self.var.waterbody_file, dateVar['currDate'], "yearly", value='resSfAreaInp')
            resSfAreaC = np.compress(self.var.compressID, resSfArea)
            resSfAreaC = npareaaverage(resSfAreaC, self.var.waterBodyIdsC)
            # water body surface area (m2): (lakes and reservoirs)
            self.var.waterBodyAreaC = np.maximum(npareatotal(fracWatC * self.var.cellAreaC,self.var.waterBodyIdsC),
                                        npareaaverage( resSfAreaC, self.var.waterBodyIdsC))



            # water body types:
            # - 2 = reservoirs (regulated discharge)
            # - 1 = lakes (weirFormula)
            # - 0 = non lakes or reservoirs (e.g. wetland)
            waterBodyTyp = readnetcdf2(self.var.waterbody_file, dateVar['currDate'], "yearly", value='waterBodyTyp')
            #waterBodyTyp = np.where(waterBodyTyp > 0., 1, waterBodyTyp)  # TODO change all to lakes for testing

            self.var.waterBodyTypC = np.compress(self.var.compressID, waterBodyTyp)
            self.var.waterBodyTypC = np.where( self.var.waterBodyIdsC > 0, self.var.waterBodyTypC.astype(np.int32), 0)
            # use the majority of an type for a whole lake or reservoir
            self.var.waterBodyTypC = npareamajority(self.var.waterBodyTypC, self.var.waterBodyIdsC)





        # correcting water bodies attributes if reservoirs are ignored (for natural runs):
        if self.var.includeLakes == "True" and self.var.includeReservoirs == "False":
            reservoirExcluded = np.where(self.var.waterBodyTypC == 2, True, False)
            maxWaterBodyAreaExcluded = np.where(reservoirExcluded, self.var.waterBodyAreaC / npareatotal(reservoirExcluded, self.var.waterBodyIdsC), 0)
            maxfractionWaterExcluded = maxWaterBodyAreaExcluded / self.var.cellAreaC
            maxfractionWaterExcluded = np.minimum(1.0, maxfractionWaterExcluded)
            maxfractionWaterExcluded = np.minimum(fracWatC, maxfractionWaterExcluded)
            fracWatC = np.minimum(1., np.maximum(0., fracWatC - maxfractionWaterExcluded))
            waterBodyTypC = np.where(waterBodyTypC > 1., 0, waterBodyTyp)

            # correction of grassland if sum of land cover is not 1.0
            np.put(self.var.fracVegCover[5], self.var.waterBodyIndexC, fracWatC)
            sum = np.sum(self.var.fracVegCover, axis=0)
            self.var.fracVegCover[1] = self.var.fracVegCover[1] + 1.0 - sum




        # reservoir maximum capacity (m3):
        self.var.resMaxCapC = np.compress(self.var.compressID, globals.inZero)
        self.var.waterBodyCapC = np.compress(self.var.compressID, globals.inZero)

        if self.var.includeReservoirs == "True":
            # reservoir maximum capacity (m3):
            resMaxCap = 1000. * 1000. * readnetcdf2(self.var.waterbody_file, dateVar['currDate'], "yearly", value='resMaxCapInp')
            self.var.resMaxCapC = np.compress(self.var.compressID, resMaxCap)
            self.var.resMaxCapC = np.where(self.var.resMaxCapC > 0, self.var.resMaxCapC, 0.)
            self.var.resMaxCapC = npareaaverage(self.var.resMaxCapC, self.var.waterBodyIdsC)

            # water body capacity [m3]: (lakes and reservoirs)
            self.var.waterBodyCapC = np.where(self.var.waterBodyIdsC > 0, self.var.resMaxCapC, 0.0)
            # correcting water body types:
            self.var.waterBodyTypC = np.where(self.var.waterBodyCapC > 0., self.var.waterBodyTypC, np.where(self.var.waterBodyTypC == 2, 1, self.var.waterBodyTypC))



        # --------------- initial values ------------------------------------------
        # For each new reservoir (introduced at the beginning of the year)
        # initiating storage, average inflow and outflow
        # new areas are set to initial values


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

        """


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
