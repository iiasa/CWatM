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
    GROUNDWATER
    """

    def __init__(self, groundwater_variable):
        self.var = groundwater_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """
        Initial part of the groundwater module

        * load parameters from settings file
        * initial groundwater storage
        """

        self.var.recessionCoeff = loadmap('recessionCoeff')

        # for CALIBRATION
        self.var.recessionCoeff = 1 / self.var.recessionCoeff * loadmap('recessionCoeff_factor')
        self.var.recessionCoeff = 1 / self.var.recessionCoeff


        self.var.specificYield = loadmap('specificYield')
        self.var.kSatAquifer = loadmap('kSatAquifer')

        #report("C:/work/output2/ksat.map", self.var.kSatAquifer)

        # init calculation recession coefficient, speciefic yield, ksatAquifer
        self.var.recessionCoeff = np.maximum(5.e-4,self.var.recessionCoeff)
        self.var.recessionCoeff = np.minimum(1.000,self.var.recessionCoeff)
        self.var.specificYield  = np.maximum(0.010,self.var.specificYield)
        self.var.specificYield  = np.minimum(1.000,self.var.specificYield)
        self.var.kSatAquifer = np.maximum(0.010,self.var.kSatAquifer)


        # initial conditions
        self.var.storGroundwater = self.var.init_module.load_initial('storGroundwater')
        self.var.storGroundwater = np.maximum(0.0, self.var.storGroundwater) + globals.inZero

        # for water demand to have some initial value
        tresholdStorGroundwater = 0.00005  # 0.05 mm
        self.var.readAvlStorGroundwater = np.where(self.var.storGroundwater > tresholdStorGroundwater, self.var.storGroundwater,0.0)

        #PB for Bejing
        #self.var.area1 = loadmap('MaskMap')
        #ii = 1


# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Dynamic part of the groundwater module
        Calculate groundweater storage and baseflow
        """

        #self.var.sum_gwRecharge = readnetcdf2("C:/work/output2/sum_gwRecharge_daily.nc", dateVar['currDate'], addZeros=True, cut = False, usefilename = True )

        if checkOption('calcWaterBalance'):
            self.var.prestorGroundwater = self.var.storGroundwater.copy()

        # WATER DEMAND
        # update storGoundwater after self.var.nonFossilGroundwaterAbs
        self.var.storGroundwater = np.maximum(0., self.var.storGroundwater - self.var.nonFossilGroundwaterAbs)
        # PS: We assume only local groundwater abstraction can happen (only to satisfy water demand within a cell).
        # unmetDemand (m), satisfied by fossil gwAbstractions (and/or desalinization or other sources)
        # (equal to zero if limitAbstraction = True)



        # get riverbed infiltration from the previous time step (from routing)
        #self.var.surfaceWaterInf = self.var.riverbedExchange * self.var.InvCellArea
        #self.var.storGroundwater = self.var.storGroundwater + self.var.surfaceWaterInf

        # get net recharge (percolation-capRise) and update storage:
        self.var.storGroundwater = np.maximum(0., self.var.storGroundwater + self.var.sum_gwRecharge)

        # calculate baseflow and update storage:
        if not(self.var.modflow):
           # Groundwater baseflow from modflow or if modflow is not included calculate baseflow with linear storage function
           self.var.baseflow = np.maximum(0., np.minimum(self.var.storGroundwater, self.var.recessionCoeff * self.var.storGroundwater))

        self.var.storGroundwater = np.maximum(0., self.var.storGroundwater - self.var.baseflow)
        # PS: baseflow must be calculated at the end (to ensure the availability of storGroundwater to support nonFossilGroundwaterAbs)

        # to avoid small values and to avoid excessive abstractions from dry groundwater
        tresholdStorGroundwater = 0.00005  # 0.05 mm
        self.var.readAvlStorGroundwater = np.where(self.var.storGroundwater > tresholdStorGroundwater, self.var.storGroundwater,0.0)


        """

        ## PB for Bejing
        area = self.var.area1.astype(np.int64)
        #diff  = 1000*1000*1000.
        diff = 1.
        #aream =  npareatotal(self.var.cellArea,area)

        gwstor = self.var.storGroundwater * self.var.MtoM3 / diff
        self.var.sumgwstor = npareatotal(gwstor,area)

        pf = self.var.sum_prefFlow * self.var.MtoM3 / diff
        self.var.sumpf = npareatotal(pf,area)

        perc = self.var.sum_perc3toGW * self.var.MtoM3 / diff
        self.var.sumperc = npareatotal(perc,area)

        cap = self.var.sum_capRiseFromGW * self.var.MtoM3 / diff
        self.var.sumcap = npareatotal(cap,area)



        gw = self.var.sum_gwRecharge * self.var.MtoM3 / diff
        self.var.sumgw = npareatotal(gw,area)


        gw = self.var.sum_gwRecharge * self.var.MtoM3 / diff
        self.var.sumgw = npareatotal(gw,area)


        #pr = self.var.Precipitation * self.var.MtoM3 / diff
        #self.var.sumpr = npareatotal(pr,area)
        self.var.avgpr = npareaaverage(self.var.Precipitation, area)
        run = (self.var.sum_landSurfaceRunoff + self.var.baseflow) * self.var.MtoM3 / diff
        self.var.sumrunoff = npareatotal(run,area)
        et = self.var.totalET * self.var.MtoM3 / diff
        self.var.sumtotalET = npareatotal(et, area)

        etpot = self.var.ETRef * self.var.MtoM3 / diff
        self.var.sumETRef = npareatotal(etpot, area)

        base = self.var.baseflow * self.var.MtoM3 / diff
        self.var.sumbaseflow = npareatotal(base, area)
        """




        if checkOption('calcWaterBalance'):
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.sum_gwRecharge ],            # In
                [self.var.baseflow,self.var.nonFossilGroundwaterAbs],           # Out
                [self.var.prestorGroundwater],                                  # prev storage
                [self.var.storGroundwater],
                "Ground", False)




