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
    # ***** GROUNDWATER   *****************************************
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
        #self.var.storGroundwater = loadmap('storGroundwaterIni')
        self.var.storGroundwater = self.var.init_module.load_initial('storGroundwater')
        self.var.storGroundwater = np.maximum(0.0, self.var.storGroundwater) + globals.inZero

        # for water demand to have some initial value
        self.var.readAvlStorGroundwater = globals.inZero.copy()

# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the groundwater module
        """


        if option['calcWaterBalance']:
            self.var.prestorGroundwater = self.var.storGroundwater.copy()

        # get riverbed infiltration from the previous time step (from routing)
        self.var.surfaceWaterInf = self.var.riverbedExchange * self.var.InvCellArea

        self.var.storGroundwater = self.var.storGroundwater + self.var.surfaceWaterInf

        # get net recharge (percolation-capRise) and update storage:
        self.var.storGroundwater = np.maximum(0., self.var.storGroundwater + self.var.sum_gwRecharge)

        # Current assumption: Groundwater is only abstracted to satisfy local demand.
        # non fossil gw abstraction to fulfil water demand
        self.var.nonFossilGroundwaterAbs = np.maximum(0.0, np.minimum(self.var.storGroundwater, self.var.sum_potGroundwaterAbstract))

        # unmetDemand (m), satisfied by fossil gwAbstractions (and/or desalinization or other sources)
        self.var.unmetDemand = np.maximum(0.0, self.var.sum_potGroundwaterAbstract - self.var.nonFossilGroundwaterAbs)
                # (equal to zero if limitAbstraction = True)

        # fractions of water demand sources (to satisfy water demand):
        with np.errstate(invalid='ignore', divide='ignore'):
            self.var.fracNonFossilGroundwater = np.where(self.var.sum_totalPotentialGrossDemand > 0., self.var.nonFossilGroundwaterAbs / self.var.sum_totalPotentialGrossDemand,0.0)
            self.var.fracUnmetDemand = np.where(self.var.sum_totalPotentialGrossDemand > 0., self.var.unmetDemand / self.var.sum_totalPotentialGrossDemand, 0.0)
            self.var.fracSurfaceWater = np.where(self.var.sum_totalPotentialGrossDemand > 0., np.maximum(0.0, 1.0 - self.var.fracNonFossilGroundwater - self.var.fracUnmetDemand), 0.0)

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


        if option['calcWaterBalance']:
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.sum_gwRecharge, self.var.surfaceWaterInf],            # In
                [self.var.baseflow,self.var.nonFossilGroundwaterAbs],           # Out
                [self.var.prestorGroundwater],                                  # prev storage
                [self.var.storGroundwater],
                "Ground", False)



        if option['calcWaterBalance']:
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.nonIrrGrossDemand,self.var.sum_irrGrossDemand],                                           # In
                [self.var.nonFossilGroundwaterAbs,self.var.unmetDemand,self.var.sum_actSurfaceWaterAbstract, ],     # Out
                [globals.inZero],
                [globals.inZero],
                "Waterdemand", False)


