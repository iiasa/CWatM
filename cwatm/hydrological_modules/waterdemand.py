# -------------------------------------------------------------------------
# Name:        Waterdemand module
# Purpose:
#
# Author:      PB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------
"""
Naming convention:
  -
  -
  -
  -

"""
from cwatm.management_modules.data_handling import *

class waterdemand(object):

    """
    WATERDEMAND

    calculating water demand -
    Industrial, domenstic based on precalculated maps
    Agricultural water demand based on water need by plants
    """

    def __init__(self, waterdemand_variable):
        self.var = waterdemand_variable

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    def initial(self):
        """
        Initial part of the water demand module

        Set the water allocation
        """

        if checkOption('includeWaterDemand'):

            #if 'usingAllocSegments' in binding:
            #    if checkOption('usingAllocSegments'):
            #       self.var.allocSegments = loadmap('allocSegments').astype(np.int)
            #       self.var.segmentArea = np.where(self.var.allocSegments > 0, npareatotal(self.var.cellArea, self.var.allocSegments), self.var.cellArea)

            # -------------------------------------------
            # partitioningGroundSurfaceAbstraction
            # partitioning abstraction sources: groundwater and surface water
            # partitioning based on local average baseflow (m3/s) and upstream average discharge (m3/s)
            # estimates of fractions of groundwater and surface water abstractions
            swAbstractionFraction = loadmap('swAbstractionFrac')

            if swAbstractionFraction < 0:

                averageBaseflowInput = loadmap('averageBaseflow')
                averageDischargeInput = loadmap('averageDischarge')
                # convert baseflow from m to m3/s
                if returnBool('baseflowInM'):
                    averageBaseflowInput = averageBaseflowInput * self.var.cellArea * self.var.InvDtSec

                if checkOption('usingAllocSegments'):
                    averageBaseflowInput = np.where(self.var.allocSegments > 0, npareaaverage(averageBaseflowInput, self.var.allocSegments), averageBaseflowInput)
                    averageUpstreamInput = np.where(self.var.allocSegments > 0, npareamaximum(averageDischargeInput, self.var.allocSegments), averageDischargeInput)

                swAbstractionFraction = np.maximum(0.0, np.minimum(1.0, averageDischargeInput / np.maximum(1e-20, averageDischargeInput + averageBaseflowInput)))
                swAbstractionFraction = np.minimum(1.0, np.maximum(0.0, swAbstractionFraction))

            self.var.swAbstractionFraction = globals.inZero.copy()
            for No in range(4):
                self.var.swAbstractionFraction += self.var.fracVegCover[No] * swAbstractionFraction
            for No in range(4,6):
                self.var.swAbstractionFraction += self.var.fracVegCover[No]

            # demand time monthly or yearly
            self.var.domesticTime = 'monthly'
            self.var.industryTime = 'yearly'
            self.var.livestockTime = 'monthly'
            if "domesticTimeMonthly" in binding:
                if not(returnBool('domesticTimeMonthly')): self.var.domesticTime = 'yearly'
                if returnBool('industryTimeMonthly'): self.var.industryTime = 'monthly'
                if not(returnBool('livestockTimeMonthly')): self.var.livestockTime = 'yearly'

            # variablenames
            # name of the variable Demand = Withrawal = Gross, consumption = Netto
            if "domesticWithdrawalvarname" in binding:
                self.var.domWithdrawalVar = cbinding("domesticWithdrawalvarname")
                self.var.domConsumptionVar = cbinding("domesticConsuptionvarname")
                self.var.indWithdrawalVar = cbinding("industryWithdrawalvarname")
                self.var.indConsumptionVar = cbinding("industryConsuptionvarname")
                self.var.livVar = cbinding("livestockvarname")
            else:
                self.var.domWithdrawalVar = "domesticGrossDemand"
                self.var.domConsumptionVar = "domesticNettoDemand"
                self.var.indWithdrawalVar = "industryGrossDemand"
                self.var.indConsumptionVar = "industryNettoDemand"
                self.var.livVar = "livestockDemand"

            self.var.uselivestock = False
            if "uselivestock" in binding:
                self.var.uselivestock = returnBool('uselivestock')

            self.var.demand_unit = True
            if "demand_unit" in binding:
                self.var.demand_unit = returnBool('demand_unit')


            self.var.use_environflow = False
            self.var.cut_ef_map = False
            if "use_environflow" in binding:
                self.var.use_environflow = returnBool('use_environflow')
            if self.var.use_environflow:
                self.var.cut_ef_map = returnBool('cut_ef_map')

            # init unmetWaterDemand -> to calculate actual one the the unmet water demand from previous day is needed
            self.var.unmetDemandPaddy = self.var.init_module.load_initial('unmetDemandPaddy', default = globals.inZero.copy())
            self.var.unmetDemandNonpaddy = self.var.init_module.load_initial('unmetDemandNonpaddy', default = globals.inZero.copy())
            # in case fossil water abstraction is allowed this will be filled
            self.var.unmetDemand = globals.inZero.copy()

            # irrigation efficiency
            # at the moment a single map, but will be replaced by map stack for every year
            self.var.efficiencyPaddy = loadmap("irrPaddy_efficiency")
            self.var.efficiencyNonpaddy = loadmap("irrNonPaddy_efficiency")
            self.var.returnfractionIrr = loadmap("irrigation_returnfraction")

            # for Xiaogang's agent model
            self.var.alphaDepletion = 0.6
            if "alphaDepletion" in binding:
                self.var.alphaDepletion = loadmap('alphaDepletion')

            self.var.modflowPumping = globals.inZero.copy()
            self.var.modflowPumpingM = globals.inZero.copy()
            self.var.modflowDepth2 = 0
            self.var.modflowTopography = 0

        else:  # no water demand

            self.var.nonIrrReturnFlowFraction = globals.inZero.copy()
            self.var.nonFossilGroundwaterAbs = globals.inZero.copy()
            self.var.nonIrruse = globals.inZero.copy()
            self.var.act_indDemand = globals.inZero.copy()
            self.var.act_domDemand = globals.inZero.copy()
            self.var.act_livDemand = globals.inZero.copy()
            self.var.nonIrrDemand = globals.inZero.copy()
            self.var.totalIrrDemand = globals.inZero.copy()
            self.var.totalWaterDemand = globals.inZero.copy()
            self.var.act_irrWithdrawal = globals.inZero.copy()
            self.var.act_nonIrrWithdrawal = globals.inZero.copy()
            self.var.act_totalWaterWithdrawal = globals.inZero.copy()
            self.var.act_indConsumption = globals.inZero.copy()
            self.var.act_domConsumption = globals.inZero.copy()
            self.var.act_livConsumption = globals.inZero.copy()
            self.var.act_nonIrrConsumption = globals.inZero.copy()
            self.var.act_totalIrrConsumption = globals.inZero.copy()
            self.var.act_totalWaterConsumption = globals.inZero.copy()
            self.var.unmetDemand = globals.inZero.copy()
            self.var.addtoevapotrans = globals.inZero.copy()
            self.var.returnflowIrr = globals.inZero.copy()
            self.var.returnFlow = globals.inZero.copy()
            self.var.unmetDemandPaddy = globals.inZero.copy()
            self.var.unmetDemandNonpaddy = globals.inZero.copy()
            self.var.ind_efficiency = 1.
            self.var.dom_efficiency = 1.
            self.var.liv_efficiency = 1
            self.var.modflowPumping = 0
            self.var.modflowDepth2 = 0
            self.var.modflowTopography = 0
            self.var.act_bigLakeResAbst = globals.inZero.copy()
            self.var.leakage = globals.inZero.copy()
            self.var.pumping = globals.inZero.copy()



    # --------------------------------------------------------------------------
    def dynamic(self):
        """
        Dynamic part of the water demand module

        * calculate the fraction of water from surface water vs. groundwater
        * get non-Irrigation water demand and its return flow fraction
        """

        if checkOption('includeWaterDemand'):

            # for debugging of a specific date
            #if (dateVar['curr'] >= 137):
            #    ii =1

            # ----------------------------------------------------
            # WATER AVAILABILITY

            if self.var.use_environflow:
                if dateVar['newStart'] or dateVar['newMonth']:
                    # envflow in [m3/s] -> [m]
                    self.var.envFlowm3s = readnetcdf2('EnvironmentalFlowFile', dateVar['currDate'],"month", cut = self.var.cut_ef_map) # in [m3/s]
                    #self.var.envFlow = self.var.M3toM * self.var.DtSec * self.var.envFlow
                    self.var.envFlow = self.var.M3toM  * self.var.channelAlpha * self.var.chanLength * self.var.envFlowm3s ** 0.6 # in [m]
            else:
                self.var.envFlow = 0.0

            # to avoid small values and to avoid surface water abstractions from dry channels (>= 0.5mm)
            self.var.readAvlChannelStorageM = np.where(self.var.channelStorage < (0.0005 * self.var.cellArea), 0., self.var.channelStorage)  # in [m3]
            # coversersion m3 -> m # minus environmental flow
            self.var.readAvlChannelStorageM = self.var.readAvlChannelStorageM * self.var.M3toM  # in [m]
            self.var.readAvlChannelStorageM = np.maximum(0.,self.var.readAvlChannelStorageM - self.var.envFlow)

            # ----------------------------------------------------
            # WATER DEMAND
            # conversion from million m3 per month or year to m per day

            # industry water demand
            new = 'newYear'
            if self.var.industryTime == 'monthly': new = 'newMonth'

            if dateVar['newStart'] or dateVar[new]:
                self.var.industryDemand = readnetcdf2('industryWaterDemandFile', dateVar['currDate'], self.var.industryTime, value=self.var.indWithdrawalVar)
                self.var.pot_industryConsumption = readnetcdf2('industryWaterDemandFile', dateVar['currDate'], self.var.industryTime, value=self.var.indConsumptionVar)
                self.var.industryDemand = np.where(self.var.industryDemand > self.var.InvCellArea, self.var.industryDemand, 0.0)
                self.var.pot_industryConsumption = np.where(self.var.pot_industryConsumption > self.var.InvCellArea, self.var.pot_industryConsumption, 0.0)
                self.var.ind_efficiency = divideValues(self.var.pot_industryConsumption, self.var.industryDemand)


                # transform from mio m3 per year (or month) to m/day if necessary
                if not self.var.demand_unit:
                    if self.var.industryTime == 'monthly':
                        timediv= dateVar['daysInMonth']
                    else:
                        timediv = dateVar['daysInYear']
                    self.var.industryDemand = self.var.industryDemand * 1000000 * self.var.M3toM / timediv
                    self.var.pot_industryConsumption = self.var.pot_industryConsumption * 1000000 * self.var.M3toM / timediv

            # domestic water demand
            new = 'newYear'
            if self.var.domesticTime == 'monthly': new = 'newMonth'
            if dateVar['newStart'] or dateVar[new]:
                self.var.domesticDemand = readnetcdf2('domesticWaterDemandFile', dateVar['currDate'], self.var.domesticTime, value=self.var.domWithdrawalVar)
                self.var.pot_domesticConsumption = readnetcdf2('domesticWaterDemandFile', dateVar['currDate'], self.var.domesticTime, value=self.var.domConsumptionVar)
                # avoid small values (less than 1 m3):
                self.var.domesticDemand = np.where(self.var.domesticDemand > self.var.InvCellArea, self.var.domesticDemand, 0.0)
                self.var.pot_domesticConsumption = np.where(self.var.pot_domesticConsumption > self.var.InvCellArea, self.var.pot_domesticConsumption, 0.0)
                self.var.dom_efficiency = divideValues(self.var.pot_domesticConsumption, self.var.domesticDemand)


                # transform from mio m3 per year (or month) to m/day if necessary
                if not self.var.demand_unit:
                    if self.var.domesticTime == 'monthly':
                        timediv= dateVar['daysInMonth']
                    else:
                        timediv = dateVar['daysInYear']
                    self.var.domesticDemand = self.var.domesticDemand * 1000000 * self.var.M3toM / timediv
                    self.var.pot_domesticConsumption = self.var.pot_domesticConsumption * 1000000 * self.var.M3toM / timediv



                # livestock water demand
            if self.var.uselivestock:
                new = 'newYear'
                if self.var.livestockTime == 'monthly': new = 'newMonth'
                if dateVar['newStart'] or dateVar[new]:
                    self.var.livestockDemand = readnetcdf2('livestockWaterDemandFile', dateVar['currDate'], self.var.domesticTime, value=self.var.livVar)
                    # avoid small values (less than 1 m3):
                    self.var.livestockDemand = np.where(self.var.livestockDemand > self.var.InvCellArea, self.var.livestockDemand, 0.0)
                    self.var.pot_livestockConsumption =  self.var.livestockDemand # the same, it is not a copy!
                    self.var.liv_efficiency = 1.

                    # transform from mio m3 per year (or month) to m/day if necessary - if demand_unit = False -> transdform from mio m3 per month or year
                    if not self.var.demand_unit:
                        if self.var.livestockTime == 'monthly':
                            timediv = dateVar['daysInMonth']
                        else:
                            timediv = dateVar['daysInYear']
                        self.var.livestockDemand = self.var.livestockDemand * 1000000 * self.var.M3toM / timediv

            else:
                self.var.livestockDemand = 0.
                self.var.pot_livestockConsumption = 0.
                self.var.liv_efficiency = 1.


            if dateVar['newStart'] or dateVar['newMonth']:
                # total (potential) non irrigation water demand
                self.var.nonIrrDemand = self.var.domesticDemand + self.var.industryDemand + self.var.livestockDemand
                self.var.pot_nonIrrConsumption = np.minimum(self.var.nonIrrDemand, self.var.pot_domesticConsumption +
                                                            self.var.pot_industryConsumption + self.var.pot_livestockConsumption)
                # fraction of return flow from domestic and industrial water demand
                self.var.nonIrrReturnFlowFraction = divideValues((self.var.nonIrrDemand - self.var.pot_nonIrrConsumption), self.var.nonIrrDemand)

            # non-irrg fracs in nonIrrDemand
            frac_industry = divideValues(self.var.industryDemand, self.var.nonIrrDemand)
            frac_domestic = divideValues(self.var.domesticDemand, self.var.nonIrrDemand)
            frac_livestock = divideValues(self.var.livestockDemand, self.var.nonIrrDemand)
            #-----------------
            # from irrigation
            #-----------------
            # Paddy irrigation -> No = 2
            # Non paddy irrigation -> No = 3

            # irrigation water demand for paddy
            No = 2
            self.var.pot_irrConsumption[No] = 0.0
            # a function of cropKC (evaporation and transpiration) and available water see Wada et al. 2014 p. 19
            self.var.pot_irrConsumption[No] = np.where(self.var.cropKC[No] > 0.75, np.maximum(0.,(self.var.alphaDepletion * self.var.maxtopwater - (self.var.topwater + self.var.availWaterInfiltration[No]))), 0.)
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
            wCrit3 = ((1 - p) * (self.var.wfc3[No] - self.var.wwp3[No])) + self.var.wwp3[No]

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
            irrPaddyDemand = self.var.fracVegCover[2] * self.var.irrDemand[2]
            irrNonpaddyDemand = self.var.fracVegCover[3] * self.var.irrDemand[3]
            self.var.totalIrrDemand = irrPaddyDemand + irrNonpaddyDemand

            # Sum up water demand
            # totalDemand [m]: total maximum (potential) water demand: irrigation and non irrigation
            totalDemand = self.var.nonIrrDemand + self.var.totalIrrDemand  # in [m]

            #-------------------------------------
            # WATER DEMAND vs. WATER AVAILABILITY
            #-------------------------------------

            # surface water abstraction that can be extracted to fulfill totalDemand
            # - based on ChannelStorage and swAbstractionFraction * totalDemand
            # sum up potential surface water abstraction (no groundwater abstraction under water and sealed area)
            pot_SurfaceAbstract = totalDemand * self.var.swAbstractionFraction

            # only local surface water abstraction is allowed (network is only within a cell)
            self.var.act_SurfaceWaterAbstract = np.minimum(self.var.readAvlChannelStorageM, pot_SurfaceAbstract)
            # if surface water is not sufficient it is taken from groundwater

            if checkOption('includeWaterBodies'):

                # water that is still needed from surface water
                remainNeed = np.maximum(pot_SurfaceAbstract - self.var.act_SurfaceWaterAbstract, 0)

                # first from big Lakes and reservoirs, big lakes cover several gridcells
                # collect all water demand from lake pixels of the same id
                remainNeedBig = npareatotal(remainNeed, self.var.waterBodyID)
                remainNeedBigC = np.compress(self.var.compress_LR, remainNeedBig)

                # Storage of a big lake
                lakeResStorageC = np.where(self.var.waterBodyTypCTemp == 0, 0.,
                            np.where(self.var.waterBodyTypCTemp == 1, self.var.lakeStorageC, self.var.reservoirStorageM3C)) / self.var.MtoM3C
                minlake = np.maximum(0., 0.05*lakeResStorageC) #reasonable but arbitrary limit


                act_bigLakeAbstC = np.minimum(minlake , remainNeedBigC)
                # substract from both, because it is sorted by self.var.waterBodyTypCTemp
                self.var.lakeStorageC = self.var.lakeStorageC - act_bigLakeAbstC * self.var.MtoM3C
                self.var.lakeVolumeM3C = self.var.lakeVolumeM3C - act_bigLakeAbstC * self.var.MtoM3C
                self.var.reservoirStorageM3C = self.var.reservoirStorageM3C - act_bigLakeAbstC * self.var.MtoM3C
                # and from the combined one for waterbalance issues
                self.var.lakeResStorageC = self.var.lakeResStorageC - act_bigLakeAbstC * self.var.MtoM3C
                self.var.lakeResStorage = globals.inZero.copy()
                np.put(self.var.lakeResStorage, self.var.decompress_LR, self.var.lakeResStorageC)
                bigLakesFactorC = divideValues(act_bigLakeAbstC , remainNeedBigC)

                # and back to the big array
                bigLakesFactor = globals.inZero.copy()
                np.put(bigLakesFactor, self.var.decompress_LR, bigLakesFactorC)
                bigLakesFactorAllaroundlake = npareamaximum(bigLakesFactor, self.var.waterBodyID)
                # abstraction from big lakes is partioned to the users around the lake
                self.var.act_bigLakeResAbst = remainNeed * bigLakesFactorAllaroundlake

                # remaining need is used from small lakes
                remainNeed1 = remainNeed * (1 - bigLakesFactorAllaroundlake)
                #minlake = np.maximum(0.,self.var.smalllakeStorage - self.var.minsmalllakeStorage) * self.var.M3toM

                if returnBool('useSmallLakes'):
                    minlake = np.maximum(0.,self.var.smalllakeStorage) * self.var.M3toM
                    self.var.act_smallLakeResAbst = np.minimum(minlake, remainNeed1)
                    #self.var.actLakeResAbst = np.minimum(0.5 * self.var.smalllakeStorageM3 * self.var.M3toM, remainNeed)
                    # act_smallLakesres is substracted from small lakes storage
                    self.var.smalllakeVolumeM3 = self.var.smalllakeVolumeM3 - self.var.act_smallLakeResAbst * self.var.MtoM3
                    self.var.smalllakeStorage = self.var.smalllakeStorage - self.var.act_smallLakeResAbst * self.var.MtoM3
                else:
                    self.var.act_smallLakeResAbst = 0

                # available surface water is from river network + large/small lake & reservoirs
                self.var.act_SurfaceWaterAbstract = self.var.act_SurfaceWaterAbstract + self.var.act_bigLakeResAbst + self.var.act_smallLakeResAbst
                # remaining is taken from groundwater if possible
                remainNeed2 = pot_SurfaceAbstract - self.var.act_SurfaceWaterAbstract

                if 'using_reservoir_command_areas' in binding:
                    if checkOption('using_reservoir_command_areas'):  # checkOption('usingAllocSegments2'):

                        # ABOUT
                        #
                        # The command area of a reservoir is the area that can receive water from this reservoir, through canals or other means.
                        # Performed above, each cell has attempted to satisfy its demands with local water using in-cell channel, lake, and reservoir storage.
                        # The remaining demand within each command area is totaled and requested from the associated reservoir.
                        # The reservoir offers this water up to a daily maximum relating to the available storage in the reservoir, defined in the Reservoir_releases_input_file.
                        #
                        # SETTINGS FILE AND INPUTS

                        # -Activating
                        # In the OPTIONS section towards the beginning of the settings file, add/set
                        # using_reservoir_command_areas = True

                        # - Command areas raster map
                        # Anywhere after the OPTIONS section (in WATERDEMAND, for example), add/set reservoir_command_areas to a path holding...
                        # information about the command areas. This Command areas raster map should assign the same positive integer coding to each cell within the same segment.
                        # All other cells must Nan values, or values <= 0.

                        # -Optional inputs
                        #
                        # Anywhere after the OPTIONS section, add/set Reservoir_releases_input_file to a path holding information about irrigation releases.
                        # This should be a raster map (netCDF) of 366 values determining the maximum fraction of available storage to be used for meeting water demand...
                        # in the associated command area on the day of the year. If this is not included, a value of 0.01 will be assumed,
                        # i.e. 1% of the reservoir storage can be at most released into the command area on each day.

                        ## Command area total demand
                        #
                        # The remaining demand within each command area [M3] is put into a map where each cell in the command area holds this total demand
                        demand_Segment = np.where(self.var.reservoir_command_areas > 0,
                                                  npareatotal(remainNeed2 * self.var.cellArea,
                                                              self.var.reservoir_command_areas),
                                                  0)  # [M3]

                        ## Reservoir associated with the Command Area
                        #
                        # If there is more than one reservoir in a command area, the storage of the reservoir with maximum storage in this time-step is chosen.
                        # The map resStorageTotal_alloc holds this maximum reservoir storage within a command area in all cells within that command area

                        reservoirStorageM3 = globals.inZero.copy()
                        np.put(reservoirStorageM3, self.var.decompress_LR, self.var.reservoirStorageM3C)
                        resStorageTotal_alloc = np.where(self.var.reservoir_command_areas > 0,
                                                         npareamaximum(reservoirStorageM3,
                                                                       self.var.reservoir_command_areas), 0)  # [M3]

                        # In the map resStorageTotal_allocC, the maximum storage from each allocation segment is held in all reservoir cells within that allocation segment.
                        # We now correct to remove the reservoirs that are not this maximum-storage-reservoir for the command area.
                        resStorageTotal_allocC = np.compress(self.var.compress_LR, resStorageTotal_alloc)
                        resStorageTotal_allocC = np.multiply(resStorageTotal_allocC == self.var.reservoirStorageM3C,
                                                             resStorageTotal_allocC)

                        # The rules for the maximum amount of water to be released for irrigation are found for the chosen maximum-storage reservoir in each command area
                        day_of_year = dateVar['currDate'].timetuple().tm_yday

                        if 'Reservoir_releases_input_file' in binding:
                            resStorage_maxFracForIrrigation = readnetcdf2('Reservoir_releases_input_file', day_of_year,
                                                                          useDaily='DOY', value='Fraction of Volume')
                        else:
                            resStorage_maxFracForIrrigation = 0.01 + globals.inZero.copy()

                        # resStorage_maxFracForIrrigationC holds the fractional rules found for each reservoir, so we must null those that are not the maximum-storage reservoirs
                        resStorage_maxFracForIrrigationC = np.compress(self.var.compress_LR,
                                                                       resStorage_maxFracForIrrigation)
                        resStorage_maxFracForIrrigationC = np.multiply(
                            resStorageTotal_allocC == self.var.reservoirStorageM3C, resStorage_maxFracForIrrigationC)
                        np.put(resStorage_maxFracForIrrigation, self.var.decompress_LR, resStorage_maxFracForIrrigationC)

                        resStorage_maxFracForIrrigation_CA = np.where(self.var.reservoir_command_areas > 0,
                                                                      npareamaximum(resStorage_maxFracForIrrigation,
                                                                                    self.var.reservoir_command_areas), 0)

                        if 'Water_conveyance_efficiency' in binding:
                            Water_conveyance_efficiency = loadmap('Water_conveyance_efficiency')
                        else:
                            Water_conveyance_efficiency = 1.0

                        act_bigLakeResAbst_alloc = np.minimum(resStorage_maxFracForIrrigation_CA * resStorageTotal_alloc,
                                                              demand_Segment / Water_conveyance_efficiency)  # [M3]

                        ResAbstractFactor = np.where(resStorageTotal_alloc > 0,
                                                     divideValues(act_bigLakeResAbst_alloc, resStorageTotal_alloc),
                                                     0)  # fraction of water abstracted versus water available for total segment reservoir volumes
                        # Compressed version needs to be corrected as above
                        ResAbstractFactorC = np.compress(self.var.compress_LR, ResAbstractFactor)
                        ResAbstractFactorC = np.multiply(resStorageTotal_allocC == self.var.reservoirStorageM3C,
                                                         ResAbstractFactorC)

                        self.var.lakeStorageC -= self.var.reservoirStorageM3C * ResAbstractFactorC
                        self.var.lakeVolumeM3C -= self.var.reservoirStorageM3C * ResAbstractFactorC
                        self.var.lakeResStorageC -= self.var.reservoirStorageM3C * ResAbstractFactorC
                        self.var.reservoirStorageM3C -= self.var.reservoirStorageM3C * ResAbstractFactorC

                        self.var.lakeResStorage = globals.inZero.copy()
                        np.put(self.var.lakeResStorage, self.var.decompress_LR, self.var.lakeResStorageC)

                        metRemainSegment = np.where(demand_Segment > 0,
                                                    divideValues(act_bigLakeResAbst_alloc * Water_conveyance_efficiency,
                                                                 demand_Segment), 0)  # by definition <= 1

                        self.var.leakageC_daily = resStorageTotal_allocC * ResAbstractFactorC * (
                                    1 - Water_conveyance_efficiency)
                        self.var.leakageC += self.var.leakageC_daily
                        self.var.leakageC_daily_segments = np.sum(self.var.leakageC_daily) + globals.inZero

                        self.var.act_bigLakeResAbst += remainNeed2 * metRemainSegment
                        self.var.act_SurfaceWaterAbstract += remainNeed2 * metRemainSegment

                        ## End of using_reservoir_command_areas


            # real surface water abstraction can be lower, because not all demand can be done from surface water
            act_swAbstractionFraction = divideValues(self.var.act_SurfaceWaterAbstract, totalDemand)
            # remaining is taken from groundwater if possible
            self.var.pot_GroundwaterAbstract = totalDemand - self.var.act_SurfaceWaterAbstract


            # calculate renewableAvlWater (non-fossil groundwater and channel) - environmental flow
            self.var.renewableAvlWater = self.var.readAvlStorGroundwater + self.var.readAvlChannelStorageM

            self.var.nonFossilGroundwaterAbs = np.minimum(self.var.readAvlStorGroundwater, self.var.pot_GroundwaterAbstract)


            # if limitAbstraction from groundwater is True
            # fossil gwAbstraction and water demand may be reduced
            # variable to reduce/limit groundwater abstraction (> 0 if limitAbstraction = True)
            if checkOption('limitAbstraction'):
                # Fossil groundwater abstraction is not allowed
                # allocation rule here: domestic& industry > irrigation > paddy

                # non-irrgated water demand: adjusted (and maybe increased) by gwabstration factor
                # if nonirrgated water demand is higher than actual growndwater abstraction (wwhat is needed and what is stored in gw)
                act_nonIrrWithdrawalGW = self.var.nonIrrDemand * (1 - act_swAbstractionFraction)
                act_nonIrrWithdrawalGW = np.where(act_nonIrrWithdrawalGW > self.var.nonFossilGroundwaterAbs, self.var.nonFossilGroundwaterAbs, act_nonIrrWithdrawalGW)
                act_nonIrrWithdrawalSW = act_swAbstractionFraction * self.var.nonIrrDemand
                self.var.act_nonIrrWithdrawal = act_nonIrrWithdrawalSW + act_nonIrrWithdrawalGW

                # irrigated water demand:
                act_irrWithdrawalGW = self.var.totalIrrDemand * (1 - act_swAbstractionFraction)
                act_irrWithdrawalGW = np.minimum(self.var.nonFossilGroundwaterAbs - act_nonIrrWithdrawalGW, act_irrWithdrawalGW)
                act_irrWithdrawalSW = act_swAbstractionFraction * self.var.totalIrrDemand
                self.var.act_irrWithdrawal = act_irrWithdrawalSW + act_irrWithdrawalGW
                # (nonpaddy)
                act_irrnonpaddyGW = self.var.fracVegCover[3] * (1 - act_swAbstractionFraction) * self.var.irrDemand[3]
                act_irrnonpaddyGW = np.minimum(self.var.nonFossilGroundwaterAbs - act_nonIrrWithdrawalGW, act_irrnonpaddyGW)
                act_irrnonpaddySW = self.var.fracVegCover[3] * act_swAbstractionFraction * self.var.irrDemand[3]
                self.var.act_irrNonpaddyWithdrawal = act_irrnonpaddySW + act_irrnonpaddyGW
                # (paddy)
                act_irrpaddyGW = self.var.fracVegCover[2] * (1 - act_swAbstractionFraction) * self.var.irrDemand[2]
                act_irrpaddyGW = np.minimum(self.var.nonFossilGroundwaterAbs - act_nonIrrWithdrawalGW - act_irrnonpaddyGW, act_irrpaddyGW)
                act_irrpaddySW = self.var.fracVegCover[2] * act_swAbstractionFraction * self.var.irrDemand[2]
                self.var.act_irrPaddyWithdrawal = act_irrpaddySW + act_irrpaddyGW

                act_gw = act_nonIrrWithdrawalGW + act_irrWithdrawalGW

                # todo: is act_irrWithdrawal needed to be replaced? Check later!!
                # consumption - irrigation (without loss) = demand  * efficiency   (back to non fraction value)

                ## back to non fraction values
                # self.var.act_irrWithdrawal[2] = divideValues(self.var.act_irrPaddyWithdrawal, self.var.fracVegCover[2])
                #self.var.act_irrWithdrawal[3] = divideValues(self.var.act_irrNonpaddyWithdrawal, self.var.fracVegCover[3])
                ## consumption - irrigation (without loss) = demand  * efficiency

                # calculate act_ water demand, because irr demand has still demand from previous day included
                # if the demand from previous day is not fulfilled it is taken to the next day and so on
                # if we do not correct we double account each day the demand from previous days
                self.var.act_irrPaddyDemand = np.maximum(0, irrPaddyDemand - self.var.unmetDemandPaddy)
                self.var.act_irrNonpaddyDemand = np.maximum(0, irrNonpaddyDemand - self.var.unmetDemandNonpaddy)

                # unmet is either pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs or demand - withdrawal
                self.var.unmetDemand = (self.var.totalIrrDemand - self.var.act_irrWithdrawal) + (self.var.nonIrrDemand - self.var.act_nonIrrWithdrawal)
                self.var.unmetDemandPaddy = irrPaddyDemand - self.var.act_irrPaddyDemand
                self.var.unmetDemandNonpaddy = irrNonpaddyDemand - self.var.act_irrNonpaddyDemand


            else:
                # Fossil groundwater abstractions are allowed (act = pot)
                self.var.unmetDemand = self.var.pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs
                self.var.act_nonIrrWithdrawal = self.var.nonIrrDemand
                self.var.act_irrWithdrawal = self.var.totalIrrDemand

                act_gw = self.var.pot_GroundwaterAbstract

                self.var.act_irrNonpaddyWithdrawal = self.var.fracVegCover[3] * self.var.irrDemand[3]
                self.var.act_irrPaddyWithdrawal = self.var.fracVegCover[2] * self.var.irrDemand[2]


            self.var.act_irrConsumption[2] = divideValues(self.var.act_irrPaddyWithdrawal, self.var.fracVegCover[2]) * self.var.efficiencyPaddy
            self.var.act_irrConsumption[3] = divideValues(self.var.act_irrNonpaddyWithdrawal, self.var.fracVegCover[3]) * self.var.efficiencyNonpaddy

            self.var.pumping = act_gw
            if 'demand2pumping' in binding:
                if checkOption('demand2pumping'): self.var.modflowPumpingM += act_gw


            self.var.act_indWithdrawal = frac_industry * self.var.act_nonIrrWithdrawal
            self.var.act_domWithdrawal = frac_domestic * self.var.act_nonIrrWithdrawal
            self.var.act_livWithdrawal = frac_livestock * self.var.act_nonIrrWithdrawal
            self.var.act_indConsumption = self.var.ind_efficiency * self.var.act_indWithdrawal
            self.var.act_domConsumption = self.var.dom_efficiency * self.var.act_domWithdrawal
            self.var.act_livConsumption = self.var.liv_efficiency * self.var.act_livWithdrawal

            self.var.act_nonIrrConsumption = self.var.act_domConsumption + self.var.act_indConsumption + self.var.act_livConsumption
            self.var.act_totalIrrConsumption = self.var.fracVegCover[2] * self.var.act_irrConsumption[2] + self.var.fracVegCover[3] * self.var.act_irrConsumption[3]

            self.var.totalWaterDemand = self.var.fracVegCover[2] * self.var.irrDemand[2] + self.var.fracVegCover[3] * self.var.irrDemand[3] + self.var.nonIrrDemand
            self.var.act_totalWaterWithdrawal = self.var.act_nonIrrWithdrawal + self.var.act_irrWithdrawal
            self.var.act_totalWaterConsumption = self.var.act_nonIrrConsumption + self.var.act_totalIrrConsumption


            #if (dateVar['curr'] == 1):
            #    ii = 1
            #self.var.sumirrConsumption = self.var.fracVegCover[2] * self.var.irrConsumption[2] + self.var.fracVegCover[3] * self.var.irrConsumption[3]
            #self.var.waterDemand =  self.var.act_irrPaddyDemand  + self.var.act_irrNonpaddyDemand + self.var.nonIrrDemand
            #self.var.waterWithdrawal = self.var.act_nonIrrDemand + self.var.act_irrDemand

            unmet_div_ww = 1. - np.maximum(1, divideValues(self.var.unmetDemand, self.var.act_totalWaterWithdrawal))

            #Sum up loss
            #sumIrrLoss = self.var.fracVegCover[2] * (self.var.irrDemand[2] - self.var.irrConsumption[2]) +  self.var.fracVegCover[3] * (self.var.irrDemand[3] - self.var.irrConsumption[3])
            sumIrrLoss = self.var.act_irrWithdrawal - self.var.act_totalIrrConsumption
            #sumIrrLoss = self.var.act_irrPaddyDemand - (self.var.fracVegCover[2] * self.var.irrConsumption[2]) +
            self.var.returnflowIrr =  self.var.returnfractionIrr * sumIrrLoss
            self.var.addtoevapotrans = (1- self.var.returnfractionIrr) * sumIrrLoss * unmet_div_ww

            # returnflow to river and to evapotranspiration
            self.var.returnFlow = self.var.nonIrrReturnFlowFraction * self.var.act_nonIrrWithdrawal + self.var.returnflowIrr
            self.var.returnFlow = self.var.returnFlow * unmet_div_ww

            self.var.waterDemandLost = self.var.act_totalWaterConsumption + self.var.addtoevapotrans 


            #self.var.waterDemandLostarea = npareatotal(self.var.waterDemandLost, self.var.allocSegments)
            # This is done in landcover.py, therefore it is out commented
            #self.var.totalET += self.var.addtoevapotrans


            """
            area = self.var.area1.astype(np.int64)
            diff = 1000000000.
            irrDemand = self.var.act_irrDemand * self.var.MtoM3 / diff
            self.var.sum_IrrDemand = npareatotal(irrDemand, area)
            withd = self.var.act_totalWaterWithdrawal * self.var.MtoM3 / diff
            self.var.sum_waterWithdrawal = npareatotal(withd, area)
            """

            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.act_irrWithdrawal],  # In
                    [self.var.act_totalIrrConsumption, self.var.returnflowIrr,self.var.addtoevapotrans],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterlossdemand1", False)

            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.nonIrrDemand, self.var.totalIrrDemand],  # In
                    [self.var.nonFossilGroundwaterAbs, self.var.unmetDemand, self.var.act_SurfaceWaterAbstract],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand1", False)

            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.nonFossilGroundwaterAbs, self.var.unmetDemand, self.var.act_SurfaceWaterAbstract],  # In
                    [self.var.act_totalWaterWithdrawal],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand2", False)

            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.act_totalWaterWithdrawal],  # In
                    [self.var.act_irrPaddyDemand, self.var.act_irrNonpaddyDemand, self.var.act_nonIrrWithdrawal],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand3", False)

            nonIrrReturn = self.var.nonIrrReturnFlowFraction * self.var.act_nonIrrWithdrawal
            self.var.nonIrruse = self.var.act_nonIrrWithdrawal - nonIrrReturn

            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.act_totalWaterWithdrawal],  # In
                    [self.var.act_totalIrrConsumption,self.var.returnflowIrr,self.var.addtoevapotrans, self.var.nonIrruse, nonIrrReturn],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand4", False)

            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.act_totalWaterWithdrawal],  # In
                    [self.var.act_totalIrrConsumption,self.var.returnFlow,self.var.addtoevapotrans, self.var.nonIrruse],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand5",False)
