# -------------------------------------------------------------------------
# Name:        Groundwater module
# Purpose:
#
# Author:      PB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


class groundwater(object):
    """
    GROUNDWATER


    **Global variables**

    ====================  ================================================================================  =========
    Variable [self.var]   Description                                                                       Unit     
    ====================  ================================================================================  =========
    storGroundwater       simulated groundwater storage                                                     m        
    specificYield         groundwater reservoir parameters (if ModFlow is not used) used to compute ground  m        
    recessionCoeff        groundwater storage times this coefficient gives baseflow                         --       
    kSatAquifer           groundwater reservoir parameters (if ModFlow is not used), could be used to comp  m day-1  
    load_initial                                                                                                     
    readAvlStorGroundwat  same as storGroundwater but equal to 0 when inferior to a treshold                m        
    pumping_actual                                                                                                   
    prestorGroundwater    storGroundwater at the beginning of each step                                     m        
    sum_gwRecharge        groundwater recharge                                                              m        
    modflow               Flag: True if modflow_coupling = True in settings file                            --       
    gwstore                                                                                                          
    capillar              Simulated flow from groundwater to the third CWATM soil layer                     m        
    baseflow              simulated baseflow (= groundwater discharge to river)                             m        
    nonFossilGroundwater  groundwater abstraction which is sustainable and not using fossil resources       m        
    ====================  ================================================================================  =========

    **Functions**
    """

    def __init__(self, model):
        self.var = model.var
        self.model = model
        
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

        # init calculation recession coefficient, speciefic yield, ksatAquifer
        self.var.recessionCoeff = np.maximum(5.e-4,self.var.recessionCoeff)
        self.var.recessionCoeff = np.minimum(1.000,self.var.recessionCoeff)
        self.var.specificYield  = np.maximum(0.010,self.var.specificYield)
        self.var.specificYield  = np.minimum(1.000,self.var.specificYield)
        self.var.kSatAquifer = np.maximum(0.010,self.var.kSatAquifer)


        # initial conditions
        self.var.storGroundwater = self.var.load_initial('storGroundwater')
        self.var.storGroundwater = np.maximum(0.0, self.var.storGroundwater) + globals.inZero

        # for water demand to have some initial value
        tresholdStorGroundwater = 0.00001  # 0.01 mm
        self.var.readAvlStorGroundwater = np.where(self.var.storGroundwater > tresholdStorGroundwater, self.var.storGroundwater - tresholdStorGroundwater,0.0)

        self.var.pumping_actual = globals.inZero.copy()
        self.var.capillar = globals.inZero.copy()
        self.var.baseflow = globals.inZero.copy()
        self.var.gwstore = globals.inZero.copy()
        if 'gw_depth_observations' in binding:
            self.var.gwdepth_observations = readnetcdfWithoutTime(cbinding('gw_depth_observations'), value= 'Groundwater depth')
        if 'gw_depth_sim_obs' in binding:
            self.var.gwdepth_adjuster = loadmap('gw_depth_sim_obs') #np.minimum(loadmap('gw_depth_sim_obs'), 10)

        #PB for Bejing
        #self.var.area1 = loadmap('MaskMap')
        #ii = 1


# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Dynamic part of the groundwater module
        Calculate groundweater storage and baseflow
        """

        if checkOption('calcWaterBalance'):
            self.var.prestorGroundwater = self.var.storGroundwater.copy()

        # WATER DEMAND
        # update storGoundwater after self.var.nonFossilGroundwaterAbs
        self.var.storGroundwater = np.maximum(0., self.var.storGroundwater - self.var.nonFossilGroundwaterAbs)
        # PS: We assume only local groundwater abstraction can happen (only to satisfy water demand within a cell).
        # unmetDemand (m), satisfied by fossil gwAbstractions (and/or desalinization or other sources)
        # (equal to zero if limitAbstraction = True)



        # get riverbed infiltration from the previous time step (from routing)
        #self_.var_.surfaceWaterInf = self.var._riverbedExchange * self.var.InvCellArea
        #self.var.storGroundwater = self.var.storGroundwater + self_.var_.surfaceWaterInf

        # get net recharge (percolation-capRise) and update storage:
        self.var.storGroundwater = np.maximum(0., self.var.storGroundwater + self.var.sum_gwRecharge)

        # calculate baseflow and update storage:
        if not(self.var.modflow):
           # Groundwater baseflow from modflow or if modflow is not included calculate baseflow with linear storage function
           self.var.baseflow = np.maximum(0., np.minimum(self.var.storGroundwater, self.var.recessionCoeff * self.var.storGroundwater))

        #MS
        #self.var.storGroundwater = np.maximum(0., self.var.storGroundwater - self.var.baseflow - self.var.capillar)
        self.var.storGroundwater = np.maximum(0., self.var.storGroundwater - self.var.baseflow)
        if self.var.modflow:
            # In the non-MODFLOW version, capillary rise is already dealt with previously be being removed from groundwater recharge
            self.var.storGroundwater = np.maximum(0, self.var.storGroundwater - self.var.capillar)

        # to avoid small values and to avoid excessive abstractions from dry groundwater
        tresholdStorGroundwater = 0.00001  # 0.01 mm
        self.var.readAvlStorGroundwater = np.where(self.var.storGroundwater > tresholdStorGroundwater, self.var.storGroundwater - tresholdStorGroundwater,0.0)


        """

        ## PB for Bejing
        area = self.var.area1.astype(np.int64)
        #diff  = 1000*1000*1000.
        diff = 1.
        #aream =  npareatotal(self.var.cellArea,area)

        gwstor = self.var.storGroundwater * self.var.MtoM3 / diff
        self_.var.sumgwstor = npareatotal(gwstor,area)

        pf = self_.var.sum_prefFlow * self.var.MtoM3 / diff
        self_.var.sumpf = npareatotal(pf,area)

        perc = self.var.sum_perc3toGW * self.var.MtoM3 / diff
        self_.var.sumperc = npareatotal(perc,area)

        cap = self_.var.sum_capRiseFromGW * self.var.MtoM3 / diff
        self_.var.sumcap = npareatotal(cap,area)



        gw = self.var.sum_gwRecharge * self.var.MtoM3 / diff
        self_.var.sumgw = npareatotal(gw,area)


        gw = self.var.sum_gwRecharge * self.var.MtoM3 / diff
        self._var.sumgw = npareatotal(gw,area)


        #pr = self.var.Precipitation * self.var.MtoM3 / diff
        #self.var._sumpr = npareatotal(pr,area)
        self.var._avgpr = npareaaverage(self.var.Precipitation, area)
        run = (self.var.sum_landSurfaceRunoff + self.var.baseflow) * self.var.MtoM3 / diff
        self.var._sumrunoff = npareatotal(run,area)
        et = self.var.totalET * self.var.MtoM3 / diff
        self_.var.sumtotalET = npareatotal(et, area)

        etpot = self.var.ETRef * self.var.MtoM3 / diff
        self_.var.sumETRef = npareatotal(etpot, area)

        base = self.var.baseflow * self.var.MtoM3 / diff
        self_.var.sumbaseflow = npareatotal(base, area)
        """




        if checkOption('calcWaterBalance'):
            self.model.waterbalance_module.waterBalanceCheck(
                [self.var.sum_gwRecharge ],            # In
                [self.var.baseflow,self.var.nonFossilGroundwaterAbs],           # Out
                [self.var.prestorGroundwater],                                  # prev storage
                [self.var.storGroundwater],
                "Ground", False)




