# -------------------------------------------------------------------------
# Name:        Groundwater module
# Purpose:
#
# Author:      PB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class groundwater(object):

    """
    # ************************************************************
    # ***** SOIL *****************************************
    # ************************************************************
    """

    def __init__(self, groundwater_variable):
        self.var = groundwater_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the groundwater module
        """
        self.var.recessionCoeff = loadmap('recessionCoeff')
        self.var.specificYield = loadmap('specificYield')
        self.var.kSatAquifer = loadmap('kSatAquifer')

        # init calculation recession coefficient, speciefic yield, ksatAquifer
        self.var.recessionCoeff = np.maximum(5.e-4,self.var.recessionCoeff)
        self.var.recessionCoeff = np.minimum(1.000,self.var.recessionCoeff)
        self.var.specificYield  = np.maximum(0.010,self.var.specificYield)
        self.var.specificYield  = np.minimum(1.000,self.var.specificYield)
        self.var.kSatAquifer = np.maximum(0.010,self.var.kSatAquifer)
        i = 1

        # initial conditions
          #   def getICs(self,iniItems,iniConditions = None):
        self.var.storGroundwater = loadmap('storGroundwater')
        self.var.storGroundwater = np.maximum(0.010, self.var.storGroundwater)

# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the soil module
        """

        i = 1

        # if self.var.debugWaterBalance == str('True'): prestorGroundwater = self.var.storGroundwater

        # get riverbed infiltration from the previous time step (from routing)
###        self.var.surfaceWaterInf = routing.riverbedExchange / routing.cellArea
        self.var.storGroundwater += self.var.surfaceWaterInf

        # get net recharge (percolation-capRise) and update storage:
        self.var.storGroundwater = np.maximum(0., self.var.storGroundwater + self.var.sum_gwRecharge)

        # Current assumption: Groundwater is only abstracted to satisfy local demand.
###        potGroundwaterAbstract = landSurface.potGroundwaterAbstract

        # non fossil gw abstraction to fulfil water demand
        self.var.nonFossilGroundwaterAbs = np.maximum(0.0, np.minimum(self.var.storGroundwater, potGroundwaterAbstract))

        # unmetDemand (m), satisfied by fossil gwAbstractions (and/or desalinization or other sources)
        self.var.unmetDemand = np.maximum(0.0, potGroundwaterAbstract - self.var.nonFossilGroundwaterAbs)
                # (equal to zero if limitAbstraction = True)

        # fractions of water demand sources (to satisfy water demand):
        self.var.fracNonFossilGroundwater = np.where(self.var.landmask,
                np.where(landSurface.totalPotentialGrossDemand > 0., \
                self.var.nonFossilGroundwaterAbs / landSurface.totalPotentialGrossDemand,0.0))
        self.var.fracUnmetDemand = np.where(self.var.landmask, np.where(landSurface.totalPotentialGrossDemand > 0., \
                self.var.unmetDemand / landSurface.totalPotentialGrossDemand, 0.0))
        self.var.fracSurfaceWater = np.where(self.var.landmask, np.where(landSurface.totalPotentialGrossDemand > 0., \
                np.maximum(0.0, 1.0 - self.var.fracNonFossilGroundwater - self.var.fracUnmetDemand), 0.0))

        # update storGoundwater after self.var.nonFossilGroundwaterAbs
        self.var.storGroundwater = np.maximum(0., self.var.storGroundwater - self.var.nonFossilGroundwaterAbs)
        # PS: We assume only local groundwater abstraction can happen (only to satisfy water demand within a cell).

        # calculate baseflow and update storage:
        self.var.baseflow = np.maximum(0., np.minimum(self.var.storGroundwater, self.var.recessionCoeff * self.var.storGroundwater))
        self.var.storGroundwater = np.maximum(0., self.var.storGroundwater - self.var.baseflow)
        # PS: baseflow must be calculated at the end (to ensure the availability of storGroundwater to support nonFossilGroundwaterAbs)

        # to avoid small values and to avoid excessive abstractions from dry groundwater
        tresholdStorGroundwater = 0.00005  # 0.05 mm
        self.var.readAvlStorGroundwater = np.where(self.var.storGroundwater > tresholdStorGroundwater, self.var.storGroundwater,0.0)
        # self.var.readAvlStorGroundwater = pcr.cover(self.var.readAvlStorGroundwater, 0.0)


