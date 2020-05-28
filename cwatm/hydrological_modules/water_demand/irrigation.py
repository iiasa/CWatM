from cwatm.management_modules import globals
from cwatm.management_modules.data_handling import returnBool, binding, cbinding, loadmap
import numpy as np
import numba as nb

class waterdemand_irrigation:
    def __init__(self, model):
        self.var = model.var
        self.model = model

    def initial(self):
        # init unmetWaterDemand -> to calculate actual one the the unmet water demand from previous day is needed
        self.var.unmetDemandPaddy = self.var.load_initial('unmetDemandPaddy', default=globals.inZero.copy())
        self.var.unmetDemandNonpaddy = self.var.load_initial('unmetDemandNonpaddy', default=globals.inZero.copy())
        # in case fossil water abstraction is allowed this will be filled
        self.var.unmetDemand = globals.inZero.copy()

        # irrigation efficiency
        # at the moment a single map, but will be replaced by map stack for every year
        self.var.efficiencyPaddy = loadmap("irrPaddy_efficiency")
        self.var.efficiencyNonpaddy = loadmap("irrNonPaddy_efficiency")
        self.var.returnfractionIrr = loadmap("irrigation_returnfraction")

        # for Xiaogang's agent model
        if "alphaDepletion" in binding:
            self.var.alphaDepletion = loadmap('alphaDepletion')
        else:
            self.var.alphaDepletion = 0.6

    def dynamic(self):
        # Paddy irrigation -> No = 2
        # Non paddy irrigation -> No = 3

        # irrigation water demand for paddy  
        No = 2
        # a function of cropKC (evaporation and transpiration) and available water see Wada et al. 2014 p. 19
        self.var.pot_irrConsumption[No] = np.where(
            self.var.cropKC[No] > 0.75,
            np.maximum(0., (self.var.alphaDepletion * self.var.maxtopwater - (self.var.topwater + self.var.availWaterInfiltration[No]))),
            0.
        )
        # ignore demand if less than 1 m3
        self.var.pot_irrConsumption[No] = np.where(self.var.pot_irrConsumption[No] > self.var.InvCellArea, self.var.pot_irrConsumption[No], 0)
        self.var.irrDemand[No] = self.var.pot_irrConsumption[No] / self.var.efficiencyPaddy

        #-----------------
        # irrNonPaddy
        No = 3

        # Infiltration capacity
        #  ========================================
        # first 2 soil layers to estimate distribution between runoff and infiltration
        soilWaterStorage = self.var.w1[No] + self.var.w2[No]
        soilWaterStorageCap = self.var.ws1[No] + self.var.ws2[No]
        relSat = soilWaterStorage / soilWaterStorageCap
        satAreaFrac = 1 - (1 - relSat) ** self.var.arnoBeta[No]
        satAreaFrac = np.maximum(np.minimum(satAreaFrac, 1.0), 0.0)

        store = soilWaterStorageCap / (self.var.arnoBeta[No] + 1)
        potBeta = (self.var.arnoBeta[No] + 1) / self.var.arnoBeta[No]
        potInf = store - store * (1 - (1 - satAreaFrac) ** potBeta)
        # ----------------------------------------------------------
        availWaterPlant1 = np.maximum(0., self.var.w1[No] - self.var.wwp1[No])   #* self.var.rootDepth[0][No]  should not be multiplied again with soildepth
        availWaterPlant2 = np.maximum(0., self.var.w2[No] - self.var.wwp2[No])   # * self.var.rootDepth[1][No]
        #availWaterPlant3 = np.maximum(0., self.var.w3[No] - self.var.wwp3[No])  #* self.var.rootDepth[2][No]
        readAvlWater = availWaterPlant1 + availWaterPlant2 # + availWaterPlant3

        # calculate   ****** SOIL WATER STRESS ************************************

        #The crop group number is a indicator of adaptation to dry climate,
        # e.g. olive groves are adapted to dry climate, therefore they can extract more water from drying out soil than e.g. rice.
        # The crop group number of olive groves is 4 and of rice fields is 1
        # for irrigation it is expected that the crop has a low adaptation to dry climate
        #cropGroupNumber = 1.0
        etpotMax = np.minimum(0.1 * (self.var.totalPotET[No] * 1000.), 1.0)
        # to avoid a strange behaviour of the p-formula's, ETRef is set to a maximum of 10 mm/day.

        # for group number 1 -> those are plants which needs irrigation
        # p = 1 / (0.76 + 1.5 * np.minimum(0.1 * (self.var.totalPotET[No] * 1000.), 1.0)) - 0.10 * ( 5 - cropGroupNumber)
        p = 1 / (0.76 + 1.5 * etpotMax) - 0.4
        # soil water depletion fraction (easily available soil water) # Van Diepen et al., 1988: WOFOST 6.0, p.87.
        p = p + (etpotMax - 0.6) / 4
        # correction for crop group 1  (Van Diepen et al, 1988) -> p between 0.14 - 0.77
        p = np.maximum(np.minimum(p, 1.0), 0.)
        # p is between 0 and 1 => if p =1 wcrit = wwp, if p= 0 wcrit = wfc
        # p is closer to 0 if evapo is bigger and cropgroup is smaller

        wCrit1 = ((1 - p) * (self.var.wfc1[No] - self.var.wwp1[No])) + self.var.wwp1[No]
        wCrit2 = ((1 - p) * (self.var.wfc2[No] - self.var.wwp2[No])) + self.var.wwp2[No]
        # wCrit3 = ((1 - p) * (self.var.wfc3[No] - self.var.wwp3[No])) + self.var.wwp3[No]

        critWaterPlant1 = np.maximum(0., wCrit1 - self.var.wwp1[No])  # * self.var.rootDepth[0][No]
        critWaterPlant2 = np.maximum(0., wCrit2 - self.var.wwp2[No])  # * self.var.rootDepth[1][No]
        #critWaterPlant3 = np.maximum(0., wCrit3 - self.var.wwp3[No]) # * self.var.rootDepth[2][No]
        critAvlWater = critWaterPlant1 + critWaterPlant2 # + critWaterPlant3

        # with alpha from Xiaogang He, to adjust irrigation to farmer's need
        self.var.pot_irrConsumption[No] = np.where(self.var.cropKC[No] > 0.20, np.where(readAvlWater < (self.var.alphaDepletion * critAvlWater),
                                                        np.maximum(0.0, self.var.alphaDepletion * self.var.totAvlWater - readAvlWater),  0.), 0.)
        # should not be bigger than infiltration capacity
        self.var.pot_irrConsumption[No] = np.minimum(self.var.pot_irrConsumption[No],potInf)

        # ignore demand if less than 1 m3
        self.var.pot_irrConsumption[No] = np.where(self.var.pot_irrConsumption[No] > self.var.InvCellArea, self.var.pot_irrConsumption[No], 0)
        self.var.irrDemand[No] = self.var.pot_irrConsumption[No] / self.var.efficiencyNonpaddy

        # Sum up irrigation water demand with area fraction
        self.irrPaddyDemand = self.var.fracVegCover[2] * self.var.irrDemand[2]
        self.irrNonpaddyDemand = self.var.fracVegCover[3] * self.var.irrDemand[3]
        self.var.totalIrrDemand = self.irrPaddyDemand + self.irrNonpaddyDemand