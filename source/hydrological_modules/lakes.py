# -------------------------------------------------------------------------
# Name:        Lakes module
# Purpose:
#
# Author:      PB
#
# Created:     28/01/2017
# Copyright:   (c) PB 2017
# -------------------------------------------------------------------------

from management_modules.data_handling import *
from hydrological_modules.routing_reservoirs.routing_sub import *
from management_modules.globals import *

#from pcraster.framework import *

class lakes(object):

    """
    # ************************************************************
    # ***** LAKES   **********************************************
    # ************************************************************
    """

    def __init__(self, lakes_variable):
        self.var = lakes_variable


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the lakes module

        """

        ii =1

        #self.var.lakeInflowOldC = np.bincount(self.var.downstruct, weights=self.var.ChanQ)[self.var.LakeIndex]
        self.var.lakeInflowOldC = np.compress(self.var.compress_LR, self.var.chanQKin)
        # for Modified Puls Method the Q(inflow)1 has to be used. It is assumed that this is the same as Q(inflow)2 for the first timestep
        # has to be checked if this works in forecasting mode!


        #LakeArea = lookupscalar(binding['TabLakeArea'], LakeSitePcr)
        #LakeAreaC = compressArray(LakeArea)
        #self.var.LakeAreaCC = np.compress(LakeSitesC>0,LakeAreaC)
        self.var.lakeAreaC = self.var.waterBodyOutC * 0. + 100000000.

        # Surface area of each lake [m2]
        #LakeA = lookupscalar(binding['TabLakeA'], LakeSitePcr)
        #LakeAC = compressArray(LakeA) * loadmap('LakeMultiplier')
        #self.var.LakeACC = np.compress(LakeSitesC>0,LakeAC)
        self.var.lakeAC = self.var.waterBodyOutC * 0. + 100.
        # Lake parameter A (suggested  value equal to outflow width in [m])
        # multiplied with the calibration parameter LakeMultiplier

        """

        LakeInitialLevelValue  = loadmap('LakeInitialLevelValue')
        if np.max(LakeInitialLevelValue) == -9999:
            LakeAvNetInflowEstimate = lookupscalar(binding['TabLakeAvNetInflowEstimate'], LakeSitePcr)
            LakeAvNetC = compressArray(LakeAvNetInflowEstimate)
            self.var.LakeAvNetCC = np.compress(LakeSitesC>0,LakeAvNetC)

            LakeStorageIniM3CC = self.var.LakeAreaCC * np.sqrt(self.var.LakeAvNetCC / self.var.LakeACC)
            # Initial lake storage [m3]  based on: S = LakeArea * H = LakeArea * sqrt(Q/a)
            self.var.LakeLevelCC = LakeStorageIniM3CC / self.var.LakeAreaCC
        else:
            self.var.LakeLevelCC = np.compress(LakeSitesC > 0, LakeInitialLevelValue)
            LakeStorageIniM3CC = self.var.LakeAreaCC * self.var.LakeLevelCC
            # Initial lake storage [m3]  based on: S = LakeArea * H

            self.var.LakeAvNetCC = np.compress(LakeSitesC > 0,loadmap('PrevDischarge'))
        """
        self.var.lakeAvNetC = self.var.lakeInflowOldC.copy()   # inflow in m3/s estimate
        lakeStorageIniM3C = self.var.lakeAreaC * np.sqrt(self.var.lakeAvNetC / self.var.lakeAC)
        # lake storage ini
        self.var.lakeLevelC = lakeStorageIniM3C / self.var.lakeAreaC

        # Repeatedly used expressions in lake routine

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

        lakeStorageIndicator = lakeStorageIniM3C / self.var.dtRouting + self.var.lakeAvNetC / 2
        # SI = S/dt + Q/2
        self.var.lakeOutflow = np.square(-self.var.lakeFactor + np.sqrt(self.var.lakeFactorSqr + 2 * lakeStorageIndicator))
        # solution of quadratic equation
        #  it is as easy as this because:
        # 1. storage volume is increase proportional to elevation
        #  2. Q= a *H **2.0  (if you choose Q= a *H **1.5 you have to solve the formula of Cardano)


        self.var.lakeStorageM3C = lakeStorageIniM3C.copy()

        ii=1

        #self.var.LakeStorageM3BalanceCC = lakeStorageIniM3C.copy()

        #self.var.lakeStorageIniM3 = globals.inZero.copy()
        #self.var.LakeLevel = globals.inZero.copy()
        #np.put(self.var.LakeStorageIniM3,self.var.LakeIndex,LakeStorageIniM3CC)
        #self.var.LakeStorageM3 = self.var.LakeStorageIniM3.copy()
        #np.put(self.var.LakeLevel,self.var.LakeIndex,self.var.LakeLevelCC)


        #self.var.EWLakeCUMM3 = globals.inZero.copy()
        # Initialising cumulative output variables
        # These are all needed to compute the cumulative mass balance error



        #self.var.UpArea1 = upstreamArea(self.var.dirDown_LR, dirshort_LR, globals.inZero + 1.0)
		#self.var.UpArea = upstreamArea(self.var.dirDown, dirshort_LR, self.var.cellArea)
		#d1 = downstream1(self.var.dirUp_LR, self.var.UpArea1)
		#up1 = upstream1(self.var.downstruct_LR, self.var.UpArea1)



		#ldd = pcraster.ldd(loadmap('Ldd',pcr=True))
		#sub1 = subcatchment(ldd, nominal(decompress(self.var.waterBodyOut)))






    def dynamic_inloop(self, NoRoutingExecuted, inflowC):

        # ************************************************************
        # ***** LAKE
        # ************************************************************

		#self.var.LakeInflowCC = np.bincount(self.var.downstruct, weights=self.var.ChanQ)[self.var.LakeIndex]
		# Lake inflow in [m3/s]

        lakeInflowC = inflowC / self.var.dtRouting

        lakeIn = (lakeInflowC + self.var.lakeInflowOldC) * 0.5
        # for Modified Puls Method: (S2/dtime + Qout2/2) = (S1/dtime + Qout1/2) - Qout1 + (Qin1 + Qin2)/2
		#  here: (Qin1 + Qin2)/2
        self.var.lakeInflowOldC = lakeInflowC.copy()
        # Qin2 becomes Qin1 for the next time step


        lakeStorageIndicator = self.var.lakeStorageM3C /self.var.dtRouting - 0.5 * self.var.lakeOutflow + lakeIn
        # here S1/dtime - Qout1/2 + LakeIn , so that is the right part
		# of the equation above



        self.var.lakeOutflow = np.square( -self.var.lakeFactor + np.sqrt(self.var.lakeFactorSqr + 2 * lakeStorageIndicator))
        # Flow out of lake:
		#  solving the equation  (S2/dtime + Qout2/2) = (S1/dtime + Qout1/2) - Qout1 + (Qin1 + Qin2)/2
		#  SI = (S2/dtime + Qout2/2) =  (A*H)/DtRouting + Q/2 = A/(DtRouting*sqrt(a)  * sqrt(Q) + Q/2
		#  -> replacement: A/(DtRouting*sqrt(a)) = Lakefactor, Y = sqrt(Q)
		#  Y**2 + 2*Lakefactor*Y-2*SI=0
		# solution of this quadratic equation:
		# Q=sqr(-LakeFactor+sqrt(sqr(LakeFactor)+2*SI));

        QLakeOutM3DtC = self.var.lakeOutflow * self.var.dtRouting
        # Outflow in [m3] per timestep
		# Needed at every cell, hence cover statement

        self.var.lakeStorageM3C = (lakeStorageIndicator - self.var.lakeOutflow * 0.5) * self.var.dtRouting
        # Lake storage

		# New lake storage [m3] (assuming lake surface area equals bottom area)
		#self.var.LakeStorageM3Balance += LakeIn * self.var.DtRouting - self.var.QLakeOutM3Dt - self.var.EWLakeM3Dt
        # self.var.lakeStorageM3BalanceC += lakeIn * self.var.DtRouting - QLakeOutM3DtC
        # for mass balance, the lake storage is calculated every time step
        self.var.lakeLevelC = self.var.lakeStorageM3C / self.var.lakeAreaC

        # expanding the size
		#self.var.QLakeOutM3Dt = globals.inZero.copy()
		#np.put(self.var.QLakeOutM3Dt,self.var.LakeIndex,QLakeOutM3DtC)

        return QLakeOutM3DtC


        # ---------------------------------------------------------------------------------------------
		# ---------------------------------------------------------------------------------------------


