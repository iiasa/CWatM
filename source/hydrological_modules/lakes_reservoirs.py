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


from management_modules.globals import *
# from pcraster.framework import *

class lakes_reservoirs(object):
    """
    LAKES AND RESERVOIRS
    calculate water retention in lakes and reservoirs
    """

    def __init__(self, lakes_reservoirs_variable):
        self.var = lakes_reservoirs_variable


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------


    def initWaterbodies(self):
        """
        Initialize water bodies
        Read parameters from maps e.g
        area, location, initial average discharge, type 9reservoir or lake) etc.

        Compress numpy array from mask map to the size of lakes+reservoirs
        (marked as capital C at the end of the variable name)

        """

        if checkOption('includeWaterBodies'):

            # load lakes/reservoirs map with a single ID for each lake/reservoir
            #self.var.waterBodyID = readnetcdf2(self.var.waterbody_file, dateVar['currDate'], "yearly",value='waterBodyIds').astype(np.int64)
            self.var.waterBodyID = loadmap('waterBodyID').astype(np.int64)

            # calculate biggest outlet = biggest accumulation of ldd network
            lakeResmax = npareamaximum(self.var.UpArea1, self.var.waterBodyID)
            self.var.waterBodyOut = np.where(self.var.UpArea1 == lakeResmax,self.var.waterBodyID, 0)

            # dismiss water bodies that a not subcatchment of an outlet
            sub = subcatchment1(self.var.dirUp, self.var.waterBodyOut,self.var.UpArea1)
            self.var.waterBodyID = np.where(self.var.waterBodyID == sub, sub, 0)

             #and again calculate outlets, because ID might have changed due to the operation before
            lakeResmax = npareamaximum(self.var.UpArea1, self.var.waterBodyID)
            self.var.waterBodyOut = np.where(self.var.UpArea1 == lakeResmax,self.var.waterBodyID, 0)

            #report(decompress( self.var.waterBodyID), "C:\work\output3/ID.map")


            # change ldd: put pits in where lakes are:
            self.var.ldd_LR = np.where( self.var.waterBodyID > 0, 5, self.var.lddCompress)
            # create new ldd without lakes reservoirs
            self.var.lddCompress_LR, dirshort_LR, self.var.dirUp_LR, self.var.dirupLen_LR, self.var.dirupID_LR, \
                self.var.downstruct_LR, self.var.catchment_LR, self.var.dirDown_LR, self.var.lendirDown_LR = defLdd2(self.var.ldd_LR)

            #report(ldd(decompress(self.var.lddCompress_LR)), "C:\work\output3/ldd_lr.map")

            # boolean map as mask map for compressing and decompressing
            self.var.compress_LR = self.var.waterBodyOut > 0
            self.var.decompress_LR = np.nonzero(self.var.waterBodyOut)[0]
            self.var.waterBodyOutC = np.compress(self.var.compress_LR, self.var.waterBodyOut)

            # year when the reservoirs is operating
            self.var.resYearC = np.compress(self.var.compress_LR, loadmap('waterBodyYear'))


            # water body types:
            # - 3 = reservoirs and lakes (used as reservoirs but before the year of construction as lakes
            # - 2 = reservoirs (regulated discharge)
            # - 1 = lakes (weirFormula)
            # - 0 = non lakes or reservoirs (e.g. wetland)
            waterBodyTyp = loadmap('waterBodyTyp').astype(np.int64)
            #waterBodyTyp = np.where(waterBodyTyp > 0., 1, waterBodyTyp)  # TODO change all to lakes for testing
            self.var.waterBodyTypC = np.compress(self.var.compress_LR, waterBodyTyp)
            self.var.waterBodyTypC = np.where(self.var.waterBodyOutC > 0, self.var.waterBodyTypC.astype(np.int64), 0)

            # ================================
            # Lakes

            # lake area - stored in km2
            # Surface area of each lake [m2]
            self.var.lakeArea = loadmap('waterBodyArea') * 1000 * 1000   # mult with 1000000 to convert from km2 to m2
            self.var.lakeAreaC = np.compress(self.var.compress_LR, self.var.lakeArea)

            #FracWaterC = np.compress(self.var.compress_LR,npareatotal(self.var.fracVegCover[5] * self.var.cellArea, self.var.waterBodyID))
            # if water body surface from fraction map > area from lakeres map then use fracwater map
            # not used, bc lakes res is splitted into big lakes linked to river network and small lakes linked to runoff of a gridcell

            # lake discharge at outlet to calculate alpha: parameter of channel width, gravity and weir coefficient
            # Lake parameter A (suggested  value equal to outflow width in [m])
            # multiplied with the calibration parameter LakeMultiplier
            self.var.lakeDis0 = np.maximum(loadmap('waterBodyDis'),0.1)
            self.var.lakeDis0C = np.compress(self.var.compress_LR, self.var.lakeDis0)
            chanwidth = 7.1 * np.power(self.var.lakeDis0C, 0.539)

            self.var.lakeAC =  loadmap('lakeAFactor') * 0.612 * 2 / 3 * chanwidth * (2 * 9.81) ** 0.5

            # ================================
            # Reservoirs
            self.var.resVolumeC = np.compress(self.var.compress_LR, loadmap('waterBodyVolRes')) * 1000000
            # if vol = 0 volu = 10 * area just to mimic all lakes are reservoirs
            # in [Million m3] -> converted to mio m3


            # correcting water body types if the volume is 0:
            self.var.waterBodyTypC = np.where(self.var.resVolumeC > 0., self.var.waterBodyTypC, np.where(self.var.waterBodyTypC == 2, 1, self.var.waterBodyTypC))
            # correcting reservoir volume for lakes, just to run them all as reservoirs
            self.var.resVolumeC = np.where(self.var.resVolumeC > 0, self.var.resVolumeC, self.var.lakeAreaC * 10)

            # a factor which increases evaporation from lake because of wind
            self.var.lakeEvaFactor =  loadmap('lakeEvaFactor')


            # initial

            self.var.outflow = globals.inZero.copy()
            self.var.lakeStorage = globals.inZero.copy()
            self.var.lakeInflow = globals.inZero.copy()
            self.var.lakeOutflow = globals.inZero.copy()
            self.var.outLake = self.var.init_module.load_initial("outLake")


            self.var.reservoirStorage = globals.inZero.copy()

            ii = 1

            #self.var.UpArea1 = upstreamArea(self.var.dirDown_LR, dirshort_LR, globals.inZero + 1.0)
            #self.var.UpArea = upstreamArea(self.var.dirDown, dirshort_LR, self.var.cellArea)
            #d1 = downstream1(self.var.dirUp_LR, self.var.UpArea1)
            #up1 = upstream1(self.var.downstruct_LR, self.var.UpArea1)
            #ldd = pcraster.ldd(loadmap('Ldd',pcr=True))
            #sub1 = subcatchment(ldd, nominal(decompress(self.var.waterBodyOut)))


    def initial_lakes(self):
        """
        Initial part of the lakes module
        Using the **Modified Puls approach** to calculate retention of a lake

        See also:
            LISFLOOD maunal Annex 3 (Burek et al. 2013)

        """

        # self.var.lakeInflowOldC = np.bincount(self.var.downstruct, weights=self.var.ChanQ)[self.var.LakeIndex]

        # self.var.lakeInflowOldC = np.compress(self.var.compress_LR, self.var.chanQKin)
        # for Modified Puls Method the Q(inflow)1 has to be used. It is assumed that this is the same as Q(inflow)2 for the first timestep
        # has to be checked if this works in forecasting mode!


        # NEW Lake Routine using Modified Puls Method (see Maniak, p.331ff)
        # (Qin1 + Qin2)/2 - (Qout1 + Qout2)/2 = (S2 - S1)/dtime
        # changed into:
        # (S2/dtime + Qout2/2) = (S1/dtime + Qout1/2) - Qout1 + (Qin1 + Qin2)/2
        # outgoing discharge (Qout) are linked to storage (S) by elevation.
        # Now some assumption to make life easier:
        # 1.) storage volume is increase proportional to elevation: S = A * H
        #      H: elevation, A: area of lake
        # 2.) outgoing discharge = c * b * H **2.0 (c: weir constant, b: width)
        #      2.0 because it fits to a parabolic cross section see Aigner 2008
        #      (and it is much easier to calculate (that's the main reason)
        # c for a perfect weir with mu=0.577 and Poleni: 2/3 mu * sqrt(2*g) = 1.7
        # c for a parabolic weir: around 1.8
        # because it is a imperfect weir: C = c* 0.85 = 1.5
        # results in a formular : Q = 1.5 * b * H ** 2 = a*H**2 -> H =
        # sqrt(Q/a)
        self.var.lakeFactor = self.var.lakeAreaC / (self.var.dtRouting * np.sqrt(self.var.lakeAC))

        #  solving the equation  (S2/dtime + Qout2/2) = (S1/dtime + Qout1/2) - Qout1 + (Qin1 + Qin2)/2
        #  SI = (S2/dtime + Qout2/2) =  (A*H)/DtRouting + Q/2 = A/(DtRouting*sqrt(a)  * sqrt(Q) + Q/2
        #  -> replacement: A/(DtRouting*sqrt(a)) = Lakefactor, Y = sqrt(Q)
        #  Y**2 + 2*Lakefactor*Y-2*SI=0
        # solution of this quadratic equation:
        # Q=sqr(-LakeFactor+sqrt(sqr(LakeFactor)+2*SI))

        self.var.lakeFactorSqr = np.square(self.var.lakeFactor)
        # for faster calculation inside dynamic section

        lakeInflowIni = self.var.init_module.load_initial("lakeInflow")  # inflow in m3/s estimate
        if not (isinstance(lakeInflowIni, np.ndarray)):
           self.var.lakeInflowOldC = self.var.lakeDis0C.copy()
        else:
           self.var.lakeInflowOldC = np.compress(self.var.compress_LR, lakeInflowIni)

        lakeStorageIni = self.var.init_module.load_initial("lakeStorage")
        if not (isinstance(lakeStorageIni, np.ndarray)):
            self.var.lakeStorageM3C = self.var.lakeAreaC * np.sqrt(self.var.lakeInflowOldC / self.var.lakeAC)
        else:
            self.var.lakeStorageM3C = np.compress(self.var.compress_LR, lakeStorageIni)


        lakeOutflowIni = self.var.init_module.load_initial("lakeOutflow")
        if not (isinstance(lakeOutflowIni, np.ndarray)):
            lakeStorageIndicator = np.maximum(0.0,self.var.lakeStorageM3C / self.var.dtRouting + self.var.lakeInflowOldC / 2)
            # SI = S/dt + Q/2
            self.var.lakeOutflowC = np.square(-self.var.lakeFactor + np.sqrt(self.var.lakeFactorSqr + 2 * lakeStorageIndicator))
            # solution of quadratic equation
            #  it is as easy as this because:
            # 1. storage volume is increase proportional to elevation
            #  2. Q= a *H **2.0  (if you choose Q= a *H **1.5 you have to solve the formula of Cardano)
        else:
            self.var.lakeOutflowC = np.compress(self.var.compress_LR, lakeOutflowIni)

        # lake storage ini
        self.var.lakeLevelC = self.var.lakeStorageM3C / self.var.lakeAreaC



    def initial_reservoirs(self):
        """
        Initial part of the reservoir module
        Using the appraoch of LISFLOOD

        See Also:
            LISFLOOD manual Annex 1: (Burek et al. 2013)

        """

        #  Conservative, normal and flood storage limit (fraction of total storage, [-])
        self.var.conLimitC = np.compress(self.var.compress_LR, loadmap('conservativeStorageLimit') + globals.inZero)
        self.var.normLimitC = np.compress(self.var.compress_LR, loadmap('normalStorageLimit') + globals.inZero)
        self.var.floodLimitC = np.compress(self.var.compress_LR, loadmap('floodStorageLimit') + globals.inZero)
        self.var.adjust_Normal_FloodC = np.compress(self.var.compress_LR, loadmap('adjust_Normal_Flood') + globals.inZero)
        self.var.norm_floodLimitC = self.var.normLimitC + self.var.adjust_Normal_FloodC * (self.var.floodLimitC - self.var.normLimitC)

        # Minimum, Normal and Non-damaging reservoir outflow  (fraction of average discharge, [-])
        # muyktiplied with the given discharge at the outlet from Hydrolakes database
        self.var.minQC = np.compress(self.var.compress_LR, loadmap('MinOutflowQ') * self.var.lakeDis0)
        self.var.normQC = np.compress(self.var.compress_LR, loadmap('NormalOutflowQ') * self.var.lakeDis0)
        self.var.nondmgQC = np.compress(self.var.compress_LR, loadmap('NonDamagingOutflowQ') * self.var.lakeDis0)

        # Repeatedly used expressions in reservoirs routine
        self.var.deltaO = self.var.normQC - self.var.minQC
        self.var.deltaLN = self.var.normLimitC - 2 * self.var.conLimitC
        self.var.deltaLF = self.var.floodLimitC - self.var.normLimitC
        self.var.deltaNFL = self.var.floodLimitC - self.var.norm_floodLimitC

        reservoirStorageIni = self.var.init_module.load_initial("reservoirStorage")
        if not (isinstance(reservoirStorageIni, np.ndarray)):
            self.var.reservoirFillC = self.var.normLimitC.copy()
            # Initial reservoir fill (fraction of total storage, [-])
            self.var.reservoirStorageM3C = self.var.reservoirFillC * self.var.resVolumeC
        else:
            self.var.reservoirStorageM3C = np.compress(self.var.compress_LR, reservoirStorageIni)
            self.var.reservoirFillC = self.var.reservoirStorageM3C / self.var.resVolumeC
        ii = 1






   # ------------------ End init ------------------------------------------------------------------------------------
   # ----------------------------------------------------------------------------------------------------------------




    def dynamic_inloop(self, NoRoutingExecuted):
        """
        Dynamic part to calculate outflow from lakes and reservoirs

        * lakes with modified Puls approach
        * reservoirs with special filling levels

        :param NoRoutingExecuted: actual number of routing substep
        :return: outLdd: outflow in m3 to the network

        Note:
            outflow to adjected lakes and reservoirs is calculated separately
        """

        def dynamic_inloop_lakes(inflowC, NoRoutingExecuted):
            """
            Lake routine to calculate lake outflow

            :param inflowC: inflow to lakes and reservoirs
            :param NoRoutingExecuted: actual number of routing substep
            :return: QLakeOutM3DtC - lake outflow in [m3] per subtime step
            """

            # ************************************************************
            # ***** LAKE
            # ************************************************************


            #if (dateVar['curr'] == 32):
            #    iii = 1

            # Lake inflow in [m3/s]
            lakeInflowC = inflowC / self.var.dtRouting

            lakeIn = (lakeInflowC + self.var.lakeInflowOldC) * 0.5
            # for Modified Puls Method: (S2/dtime + Qout2/2) = (S1/dtime + Qout1/2) - Qout1 + (Qin1 + Qin2)/2
            #  here: (Qin1 + Qin2)/2

            self.var.evapWaterBodyC = np.where(self.var.lakeStorageM3C - self.var.evapWaterBodyC > 0., self.var.evapWaterBodyC, self.var.lakeStorageM3C)
            self.var.lakeStorageM3C = self.var.lakeStorageM3C - self.var.evapWaterBodyC
            # lakestorage - evaporation from lakes

            self.var.lakeInflowOldC = lakeInflowC.copy()
            # Qin2 becomes Qin1 for the next time step


            lakeStorageIndicator = np.maximum(0.0,self.var.lakeStorageM3C / self.var.dtRouting - 0.5 * self.var.lakeOutflowC + lakeIn)
            # here S1/dtime - Qout1/2 + LakeIn , so that is the right part
            # of the equation above

            self.var.lakeOutflowC = np.square(-self.var.lakeFactor + np.sqrt(self.var.lakeFactorSqr + 2 * lakeStorageIndicator))
            # Flow out of lake:
            #  solving the equation  (S2/dtime + Qout2/2) = (S1/dtime + Qout1/2) - Qout1 + (Qin1 + Qin2)/2
            #  SI = (S2/dtime + Qout2/2) =  (A*H)/DtRouting + Q/2 = A/(DtRouting*sqrt(a)  * sqrt(Q) + Q/2
            #  -> replacement: A/(DtRouting*sqrt(a)) = Lakefactor, Y = sqrt(Q)
            #  Y**2 + 2*Lakefactor*Y-2*SI=0
            # solution of this quadratic equation:
            # Q=sqr(-LakeFactor+sqrt(sqr(LakeFactor)+2*SI));

            QLakeOutM3DtC = self.var.lakeOutflowC * self.var.dtRouting
            # Outflow in [m3] per timestep

            self.var.lakeStorageM3C = (lakeStorageIndicator - self.var.lakeOutflowC * 0.5) * self.var.dtRouting
            # Lake storage

            # New lake storage [m3] (assuming lake surface area equals bottom area)
            # self.var.LakeStorageM3Balance += LakeIn * self.var.DtRouting - self.var.QLakeOutM3Dt - self.var.EWLakeM3Dt
            # self.var.lakeStorageM3BalanceC += lakeIn * self.var.DtRouting - QLakeOutM3DtC
            # for mass balance, the lake storage is calculated every time step

            if self.var.noRoutingSteps == (NoRoutingExecuted + 1):
                self.var.lakeLevelC = self.var.lakeStorageM3C / self.var.lakeAreaC

            # expanding the size
            # self.var.QLakeOutM3Dt = globals.inZero.copy()
            # np.put(self.var.QLakeOutM3Dt,self.var.LakeIndex,QLakeOutM3DtC)
            if self.var.saveInit and (self.var.noRoutingSteps == (NoRoutingExecuted + 1)):
                np.put(self.var.lakeStorage, self.var.decompress_LR, self.var.lakeStorageM3C)
                np.put(self.var.lakeInflow, self.var.decompress_LR, self.var.lakeInflowOldC)
                np.put(self.var.lakeOutflow, self.var.decompress_LR, self.var.lakeOutflowC)



            """
            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [lakeIn * self.var.dtRouting],  # In
                    [lakeout *self.var.dtRouting,self.var.evapWaterBodyC]  ,  # Out  self.var.evapWaterBodyC
                    [oldlake],  # prev storage
                    [self.var.lakeStorageM3C],
                    "lake", True)
            #print lakeIn[5]* self.var.dtRouting1,  lakeout[5]* self.var.dtRouting1, oldlake[5],self.var.lakeStorageM3C[5],oldlake[5] + lakeIn[5]* self.var.dtRouting1 - lakeout[5]* self.var.dtRouting1
            """

            return QLakeOutM3DtC

        # ---------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------


        def dynamic_inloop_reservoirs(inflowC, NoRoutingExecuted):
            """
            Reservoir outflow

            :param inflowC: inflow to reservoirs
            :param NoRoutingExecuted: actual number of routing substep
            :return: qResOutM3DtC - reservoir outflow in [m3] per subtime step
            """

            # ************************************************************
            # ***** Reservoirs
            # ************************************************************

            # QResInM3Dt = inflowC
            # Reservoir inflow in [m3] per timestep
            self.var.reservoirStorageM3C += inflowC
            # New reservoir storage [m3] = plus inflow for this sub step

            # check that reservoir storage - evaporation > 0
            self.var.evapWaterBodyC = np.where(self.var.reservoirStorageM3C - self.var.evapWaterBodyC > 0., self.var.evapWaterBodyC, self.var.reservoirStorageM3C)
            self.var.reservoirStorageM3C = self.var.reservoirStorageM3C - self.var.evapWaterBodyC

            self.var.reservoirFillC = self.var.reservoirStorageM3C / self.var.resVolumeC
            # New reservoir fill [-]

            reservoirOutflow1 = np.minimum(self.var.minQC, self.var.reservoirStorageM3C * self.var.InvDtSec)
            # Reservoir outflow [m3/s] if ReservoirFill

            reservoirOutflow2 = self.var.minQC + self.var.deltaO * (self.var.reservoirFillC - 2 * self.var.conLimitC) / self.var.deltaLN
            # 2*ConservativeStorageLimit
            # Reservoir outflow [m3/s] if NormalStorageLimit <= ReservoirFill > 2*ConservativeStorageLimit

            reservoirOutflow3 = self.var.normQC + ((self.var.reservoirFillC - self.var.norm_floodLimitC) / self.var.deltaNFL) * (self.var.nondmgQC - self.var.normQC)
            # Reservoir outflow [m3/s] if FloodStorageLimit le ReservoirFill gt NormalStorageLimit

            temp = np.minimum(self.var.nondmgQC, np.maximum(inflowC * 1.2, self.var.normQC))
            reservoirOutflow4 = np.maximum((self.var.reservoirFillC - self.var.floodLimitC - 0.01) * self.var.resVolumeC * self.var.InvDtSec, temp)

            # Reservoir outflow [m3/s] if ReservoirFill gt FloodStorageLimit
            # Depending on ReservoirFill the reservoir outflow equals ReservoirOutflow1, ReservoirOutflow2,
            # ReservoirOutflow3 or ReservoirOutflow4

            reservoirOutflow = reservoirOutflow1.copy()
            reservoirOutflow = np.where(self.var.reservoirFillC > 2 * self.var.conLimitC, reservoirOutflow2, reservoirOutflow)
            reservoirOutflow = np.where(self.var.reservoirFillC > self.var.normLimitC, self.var.normQC, reservoirOutflow)
            reservoirOutflow = np.where(self.var.reservoirFillC > self.var.norm_floodLimitC, reservoirOutflow3, reservoirOutflow)
            reservoirOutflow = np.where(self.var.reservoirFillC > self.var.floodLimitC, reservoirOutflow4, reservoirOutflow)

            temp = np.minimum(reservoirOutflow, np.maximum(inflowC, self.var.normQC))

            reservoirOutflow = np.where((reservoirOutflow > 1.2 * inflowC) &
                                        (reservoirOutflow > self.var.normQC) &
                                        (self.var.reservoirFillC < self.var.floodLimitC), temp, reservoirOutflow)

            qResOutM3DtC = reservoirOutflow * self.var.dtRouting

            # Reservoir outflow in [m3] per sub step
            qResOutM3DtC = np.where(self.var.reservoirStorageM3C - qResOutM3DtC > 0., qResOutM3DtC, self.var.reservoirStorageM3C)
            # check if storage would go < 0 if outflow is used
            qResOutM3DtC = np.maximum(qResOutM3DtC, self.var.reservoirStorageM3C - self.var.resVolumeC)
            # Check to prevent reservoir storage from exceeding total capacity

            self.var.reservoirStorageM3C -= qResOutM3DtC

            # self.var.reservoirStorageM3C = np.maximum(0.0,self.var.reservoirStorageM3C)


            # New reservoir storage [m3]
            self.var.reservoirFillC = self.var.reservoirStorageM3C / self.var.resVolumeC
            # New reservoir fill

            if self.var.saveInit and (self.var.noRoutingSteps == (NoRoutingExecuted + 1)):
                np.put(self.var.reservoirStorage, self.var.decompress_LR, self.var.reservoirStorageM3C)

            return qResOutM3DtC



        # ---------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------
        # lake and reservoirs


        if checkOption('calcWaterBalance'):
            preRes = globals.inZero.copy()
            np.put(preRes,self.var.decompress_LR,self.var.reservoirStorageM3C)
            preLake = globals.inZero.copy()
            np.put(preLake, self.var.decompress_LR, self.var.lakeStorageM3C)
            pre1Lake = self.var.lakeStorageM3C

            #preLake = self.var.outLake

        # check years
        if dateVar['newStart'] or dateVar['newYear']:
            year = dateVar['currDate'].year

            # - 3 = reservoirs and lakes (used as reservoirs but before the year of construction as lakes
            # - 2 = reservoirs (regulated discharge)
            # - 1 = lakes (weirFormula)
            # - 0 = non lakes or reservoirs (e.g. wetland)
            if eval(binding['useResAndLakes']):

                if eval(binding['dynamicLakesRes']):
                    year = dateVar['currDate'].year
                else:
                    year = loadmap('fixLandcoverYear')

                self.var.waterBodyTypCTemp = np.where((self.var.resYearC > year) & (self.var.waterBodyTypC == 2), 0, self.var.waterBodyTypC)
                self.var.waterBodyTypCTemp = np.where((self.var.resYearC > year) & (self.var.waterBodyTypC == 3), 1, self.var.waterBodyTypCTemp)
            else:
                self.var.waterBodyTypCTemp = np.where(self.var.waterBodyTypC == 2, 0, self.var.waterBodyTypC)
                self.var.waterBodyTypCTemp = np.where(self.var.waterBodyTypC == 3, 1, self.var.waterBodyTypCTemp)

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
        inflow = np.where(self.var.waterBodyOut > 0, inflow, 0.) / self.var.noRoutingSteps + self.var.outLake

        # calculate total inflow into lakes and compress it to waterbodie outflow point
        # inflow to lake is discharge from upstream network + runoff directly into lake + outflow from upstream lakes
        inflowC = np.compress(self.var.compress_LR, inflow)

        # ------------------------------------------------------------
        outflowLakesC = dynamic_inloop_lakes(inflowC, NoRoutingExecuted)
        outflowResC = dynamic_inloop_reservoirs(inflowC, NoRoutingExecuted)
        outflow0C = inflowC.copy()   # no retention
        outflowC = np.where( self.var.waterBodyTypCTemp == 0, outflow0C , np.where( self.var.waterBodyTypCTemp == 1, outflowLakesC, outflowResC))

        #outflowC = dynamic_inloop_lakes(inflowC,NoRoutingExecuted)        # only lakes
        #outflowC = dynamic_inloop_reservoirs(inflowC,NoRoutingExecuted)  # only reservoirs
        #outflowC = inflowC.copy() - self.var.evapWaterBodyC
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





        """
        #report(decompress(runoff_LR), "C:\work\output3/run.map")

        if checkOption('calcWaterBalance'):
            self.var.waterbalance_module.waterBalanceCheck(
                [inflowC ],            # In
                [outflowC, self.var.evapWaterBodyC],           # Out
                [self.var.preRes],                                  # prev storage
                [self.var.reservoirStorageM3C],
                "reservoir", False)

        if checkOption('calcWaterBalance'):
            Res = globals.inZero.copy()
            np.put(Res, self.var.decompress_LR, self.var.reservoirStorageM3C)
            Lake = globals.inZero.copy()
            np.put(Lake, self.var.decompress_LR, self.var.lakeStorageM3C)

            ee = globals.inZero.copy()
            np.put(ee, self.var.decompress_LR, self.var.evapWaterBodyC)

            self.var.waterbalance_module.waterBalanceCheck(
                [inflow ],            # In
                [self.var.outflow,ee ],           # Out
                [preRes],                                  # prev storage
                [Res],
                "reservoir1", False)

            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheckSum(
                    [inflow ],            # In
                    [outLdd,self.var.outLake,ee ],           # Out
                    [preRes],                                  # prev storage
                    [Res],
                    "reservoir2", False)

            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheckSum(
                    [inflow ],            # In
                    [outLdd,self.var.outLake,ee],           # Out
                    [],                                  # prev storage
                    [],
                    "reservoir3", False)

            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheckSum(
                    [inflow ],            # In
                    [outLdd,self.var.outLake],           # Out
                    [preLake],                                  # prev storage
                    [Lake],
                    "lake2", False)

            """


        return outLdd







# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
