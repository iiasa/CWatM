# -------------------------------------------------------------------------
# Name:        Waterdemand module
# Purpose:
#
# Author:      PB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class waterdemand(object):

    """
    WATERDEMAND
    calculating water demand
    Industrial, domenstic based on precalculated maps
    Agricultural water demand based on water need by plants
    """

    def __init__(self, waterdemand_variable):
        self.var = waterdemand_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """
        Initial part of the water demand module
        Set the water allocation
        """
        if checkOption('includeWaterDemand'):

            # Add  zones at which water allocation (surface and groundwater allocation) is determined
            if checkOption('usingAllocSegments'):
               self.var.allocSegments = loadmap('allocSegments').astype(np.int)
               self.var.segmentArea = npareatotal(self.var.cellArea, self.var.allocSegments)

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
                    averageBaseflowInput = npareaaverage(averageBaseflowInput, self.var.allocSegments)
                    averageUpstreamInput = npareamaximum(averageDischargeInput, self.var.allocSegments)

                swAbstractionFraction = np.maximum(0.0, np.minimum(1.0, averageDischargeInput / np.maximum(1e-20, averageDischargeInput + averageBaseflowInput)))
                swAbstractionFraction = np.minimum(1.0, np.maximum(0.0, swAbstractionFraction))
                # self.var.swAbstractionFraction[np.isnan(self.var.swAbstractionFraction)] = 0
                # self.var.swAbstractionFraction = np.round(self.var.swAbstractionFraction,2)


            self.var.swAbstractionFraction = globals.inZero.copy()
            for No in xrange(4):
                self.var.swAbstractionFraction += self.var.fracVegCover[No] * swAbstractionFraction
            for No in xrange(4,6):
                self.var.swAbstractionFraction += self.var.fracVegCover[No]
            ii =1


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
            self.var.alphaDepletion = 1.0
            if "alphaDepletion" in binding:
                self.var.alphaDepletion = loadmap('alphaDepletion')



        else:  # no water demand
            self.var.nonIrrDemand = 0
            self.var.nonIrrReturnFlowFraction = 0
            self.var.nonFossilGroundwaterAbs = 0




            self.var.sumIrrDemand = 0
            self.var.waterDemand = 0
            self.var.act_irrDemand = 0
            self.var.act_nonIrrDemand = 0
            self.var.unmetDemand = 0
            self.var.sumirrConsumption = 0
            self.var.addtoevapotrans = 0
            self.var.returnflowIrr = 0
            self.var.returnFlow = 0

            self.var.unmetDemandPaddy = globals.inZero.copy()
            self.var.unmetDemandNonpaddy = globals.inZero.copy()




            # ---------------------------------------------------------------------------------------
    #from pcraster.framework import *

    # report(decompress(self.var.discharge), "C:\work\output/q1.map")



# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Dynamic part of the water demand module

        * calculate the fraction of water from surface water vs. groundwater
        * get non-Irrigation water demand and its return flow fraction
        """

        #


        if checkOption('includeWaterDemand'):

            if (dateVar['curr'] >= 137):
                ii =1

            # ----------------------------------------------------
            # WATER AVAILABILITY

            if checkOption('use_environflow'):
                if dateVar['newStart'] or dateVar['newMonth']:
                    # envflow in [m3/s] -> [m]
                    self.var.envFlowm3s = readnetcdf2('EnvironmentalFlowFile', dateVar['currDate'],"month", cut = self.var.cut_ef_map) # in [m3/s]
                    #self.var.envFlow = self.var.M3toM * self.var.DtSec * self.var.envFlow
                    self.var.envFlow = self.var.M3toM  * self.var.channelAlpha * self.var.chanLength * self.var.envFlowm3s  ** 0.6 # in [m]
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

            #dateVar['daysInMonth']

            # industry water demand
            new = 'newYear'
            if self.var.industryTime == 'monthly': new = 'newMonth'

            if dateVar['newStart'] or dateVar[new]:
                self.var.industryDemand = readnetcdf2('industryWaterDemandFile', dateVar['currDate'], self.var.industryTime, value=self.var.indWithdrawalVar)
                self.var.industryConsumption = readnetcdf2('industryWaterDemandFile', dateVar['currDate'], self.var.industryTime, value=self.var.indConsumptionVar)
                self.var.industryDemand = np.where(self.var.industryDemand > self.var.InvCellArea, self.var.industryDemand, 0.0)
                self.var.industryConsumption = np.where(self.var.industryConsumption > self.var.InvCellArea, self.var.industryConsumption, 0.0)

            # domestic water demand
            new = 'newYear'
            if self.var.domesticTime == 'monthly': new = 'newMonth'
            if dateVar['newStart'] or dateVar[new]:
                self.var.domesticDemand = readnetcdf2('domesticWaterDemandFile', dateVar['currDate'], self.var.domesticTime, value=self.var.domWithdrawalVar)
                self.var.domesticConsumption = readnetcdf2('domesticWaterDemandFile', dateVar['currDate'], self.var.domesticTime, value=self.var.domConsumptionVar)
                # avoid small values (less than 1 m3):
                self.var.domesticDemand = np.where(self.var.domesticDemand > self.var.InvCellArea, self.var.domesticDemand, 0.0)
                self.var.domesticConsumption = np.where(self.var.domesticConsumption > self.var.InvCellArea, self.var.domesticConsumption, 0.0)

                # livestock water demand
            if self.var.uselivestock:
                new = 'newYear'
                if self.var.livestockTime == 'monthly': new = 'newMonth'
                if dateVar['newStart'] or dateVar[new]:
                    self.var.livestockDemand = readnetcdf2('livestockWaterDemandFile', dateVar['currDate'], self.var.domesticTime, value=self.var.livVar)
                # avoid small values (less than 1 m3):
                self.var.livestockDemand = np.where(self.var.livestockDemand > self.var.InvCellArea, self.var.livestockDemand, 0.0)
            else:
                self.var.livestockDemand = 0.


            if dateVar['newStart'] or dateVar['newMonth']:
                # total (potential) non irrigation water demand
                self.var.nonIrrDemand = self.var.domesticDemand + self.var.industryDemand + self.var.livestockDemand
                self.var.nonIrrConsumption = np.minimum(self.var.nonIrrDemand, self.var.domesticConsumption + self.var.industryConsumption + self.var.livestockDemand)
                # fraction of return flow from domestic and industrial water demand
                self.var.nonIrrReturnFlowFraction = divideValues((self.var.nonIrrDemand - self.var.nonIrrConsumption), self.var.nonIrrDemand)



            # from irrigation
            #-----------------
            # Paddy irrigation -> No = 2
            # Non paddy irrigation -> No = 3

            # irrigation water demand for paddy
            No = 2
            self.var.irrConsumption[No] = 0.0
            # a function of cropKC (evaporation and transpiration) and available water see Wada et al. 2014 p. 19
            self.var.irrConsumption[No] = np.where(self.var.cropKC[No] > 0.75, np.maximum(0.,(self.var.alphaDepletion * self.var.maxtopwater - (self.var.topwater +
                                        self.var.availWaterInfiltration[No]))), 0.)
            # ignore demand if less than 1 m3
            self.var.irrConsumption[No] = np.where(self.var.irrConsumption[No] > self.var.InvCellArea, self.var.irrConsumption[No], 0)
            self.var.irrDemand[No] = self.var.irrConsumption[No] / self.var.efficiencyPaddy



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



            availWaterPlant1 = np.maximum(0., self.var.w1[No] - self.var.wwp1[No]) * self.var.rootDepth[0][No]
            availWaterPlant2 = np.maximum(0., self.var.w2[No] - self.var.wwp2[No]) * self.var.rootDepth[1][No]
            #availWaterPlant3 = np.maximum(0., self.var.w3[No] - self.var.wwp3[No]) * self.var.rootDepth[2][No]
            readAvlWater = availWaterPlant1 + availWaterPlant2 # + availWaterPlant3

            # calculate   ****** SOIL WATER STRESS ************************************

            #The crop group number is a indicator of adaptation to dry climate,
            # e.g. olive groves are adapted to dry climate, therefore they can extract more water from drying out soil than e.g. rice.
            # The crop group number of olive groves is 4 and of rice fields is 1
            # for irrigation it is expected that the crop has a low adaptation to dry climate
            #cropGroupNumber = 1.0
            etpotMax = np.minimum(0.1 * (self.var.totalPotET[No] * 1000.),1.0)
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

            critWaterPlant1 = np.maximum(0., wCrit1 - self.var.wwp1[No]) * self.var.rootDepth[0][No]
            critWaterPlant2 = np.maximum(0., wCrit2 - self.var.wwp2[No]) * self.var.rootDepth[1][No]
            #critWaterPlant3 = np.maximum(0., wCrit3 - self.var.wwp3[No]) * self.var.rootDepth[2][No]
            critAvlWater = critWaterPlant1 + critWaterPlant2 # + critWaterPlant3

            # with alpha from Xiaogang He, to adjust irrigation to farmer's need
            self.var.irrConsumption[No] = np.where(self.var.cropKC[No] > 0.20, np.where(readAvlWater < (self.var.alphaDepletion * critAvlWater),
                                                            np.maximum(0.0, self.var.alphaDepletion * self.var.totAvlWater - readAvlWater),  0.), 0.)
            # should not be bigger than infiltration capacity
            self.var.irrConsumption[No] = np.minimum(self.var.irrConsumption[No],potInf)

            # ignore demand if less than 1 m3
            self.var.irrConsumption[No] = np.where(self.var.irrConsumption[No] > self.var.InvCellArea, self.var.irrConsumption[No], 0)
            self.var.irrDemand[No] = self.var.irrConsumption[No] / self.var.efficiencyNonpaddy





            # Sum up irrigation water demand
            irrPaddyDemand = self.var.fracVegCover[2] * self.var.irrDemand[2]
            irrNonpaddyDemand = self.var.fracVegCover[3] * self.var.irrDemand[3]
            self.var.sumIrrDemand = irrPaddyDemand +  irrNonpaddyDemand


            # Sum up water demand
            # totalDemand [m]: total maximum (potential) water demand: irrigation and non irrigation
            totalPotDemand = self.var.nonIrrDemand + self.var.sumIrrDemand  # in [m]


            # surface water abstraction that can be extracted to fulfill totalDemand
            # - based on ChannelStorage and swAbstractionFraction * totalPotDemand
            # sum up potentiel surface water abstraction (no groundwater abstraction under water and sealed area)
            potSurfaceAbstract = totalPotDemand * self.var.swAbstractionFraction





            # WATER DEMAND vs. WATER AVAILABILITY
            #-------------------------------------

            if not(checkOption('usingAllocSegments')):
                # only local surface water abstraction is allowed (network is only within a cell)
                self.var.actSurfaceWaterAbstract = np.minimum(self.var.readAvlChannelStorageM, potSurfaceAbstract)
                # if surface water is not sufficient it is taken from groundwater


                if checkOption('includeWaterBodies'):
                    #self.var.potGroundwaterAbstract = totalPotDemand - self.var.actSurfaceWaterAbstract
                    #realswAbstractionFraction = divideValues(self.var.actSurfaceWaterAbstract, totalPotDemand)

                    # water that is still needed from surface water
                    remainNeed = potSurfaceAbstract - self.var.actSurfaceWaterAbstract


                    # first from big Lakes and reservoirs, big lakes cover several gridcells
                    # collect all water deamand from lake pixels of same id
                    remainNeedBig = npareatotal(remainNeed, self.var.waterBodyID)
                    remainNeedBigC = np.compress(self.var.compress_LR, remainNeedBig)

                    # Storage of a big lake
                    lakeResStorageC = np.where(self.var.waterBodyTypCTemp == 0, 0.,
                                np.where(self.var.waterBodyTypCTemp == 1, self.var.lakeStorageC, self.var.reservoirStorageM3C)) / self.var.MtoM3C
                    minlake =  np.maximum(0., lakeResStorageC - 0.99 *  lakeResStorageC)


                    actbigLakeAbstC = np.minimum(minlake , remainNeedBigC)
                    # substract from both, because it is sorted by self.var.waterBodyTypCTemp
                    self.var.lakeStorageC = self.var.lakeStorageC - actbigLakeAbstC * self.var.MtoM3C
                    self.var.lakeVolumeM3C = self.var.lakeVolumeM3C - - actbigLakeAbstC * self.var.MtoM3C
                    self.var.reservoirStorageM3C = self.var.reservoirStorageM3C - actbigLakeAbstC * self.var.MtoM3C
                    # and from the combided one for waterbalance issues
                    self.var.lakeResStorageC = self.var.lakeResStorageC - actbigLakeAbstC * self.var.MtoM3C
                    self.var.lakeResStorage = globals.inZero.copy()
                    np.put(self.var.lakeResStorage, self.var.decompress_LR, self.var.lakeResStorageC)

                    bigLakesFactorC = divideValues(actbigLakeAbstC , remainNeedBigC)

                    # and back to the big array
                    bigLakesFactor = globals.inZero.copy()
                    np.put(bigLakesFactor, self.var.decompress_LR, bigLakesFactorC)
                    bigLakesFactorAllaroundlake = npareamaximum(bigLakesFactor, self.var.waterBodyID)
                    # abstraction from big lakes is partioned to the users around the lake
                    self.var.actbigLakeResAbst = remainNeed * bigLakesFactorAllaroundlake



                    # remaining need is used from small lakes
                    remainNeed1 = remainNeed  * (1 - bigLakesFactorAllaroundlake)
                    #minlake = np.maximum(0.,self.var.smalllakeStorage - self.var.minsmalllakeStorage) * self.var.M3toM

                    if returnBool('useSmallLakes'):
                        minlake = np.maximum(0.,self.var.smalllakeStorage) * self.var.M3toM
                        self.var.actsmallLakeResAbst = np.minimum(minlake, remainNeed1)
                        #self.var.actLakeResAbst = np.minimum(0.5 * self.var.smalllakeStorageM3 * self.var.M3toM, remainNeed)
                        # actsmallLakesres is substracted from small lakes storage
                        self.var.smalllakeVolumeM3 = self.var.smalllakeVolumeM3 - self.var.actsmallLakeResAbst * self.var.MtoM3
                        self.var.smalllakeStorage = self.var.smalllakeStorage - self.var.actsmallLakeResAbst * self.var.MtoM3
                    else:
                        self.var.actsmallLakeResAbst = 0

                    self.var.actSurfaceWaterAbstract = self.var.actSurfaceWaterAbstract + self.var.actbigLakeResAbst + self.var.actsmallLakeResAbst
                    # remaining is taken from groundwater if possible
                    remainNeed2 = potSurfaceAbstract - self.var.actSurfaceWaterAbstract
                    self.var.potGroundwaterAbstract = totalPotDemand - self.var.actSurfaceWaterAbstract
                    # real surface water abstraction can be lower, because not all demand can be done from surface water
                    realswAbstractionFraction = divideValues(self.var.actSurfaceWaterAbstract, totalPotDemand)
                else:
                    self.var.potGroundwaterAbstract = totalPotDemand - self.var.actSurfaceWaterAbstract
                    realswAbstractionFraction = divideValues(self.var.actSurfaceWaterAbstract, totalPotDemand)




                # calculate renewableAvlWater (non-fossil groundwater and channel) - environmental flow
                self.var.renewableAvlWater = self.var.readAvlStorGroundwater + self.var.readAvlChannelStorageM
            else:
                ii =0

            if (dateVar['curr'] > 261):
                ii = 1

            self.var.nonFossilGroundwaterAbs = np.minimum(self.var.readAvlStorGroundwater,  self.var.potGroundwaterAbstract)




            # if limitAbstraction from groundwater is True
            # fossil gwAbstraction and water demand may be reduced
            # variable to reduce/limit groundwater abstraction (> 0 if limitAbstraction = True)
            if checkOption('limitAbstraction'):

                # Fossil groundwater abstraction is not allowed
                # allocation rule here: domestic& industry > irrigation > paddy

                # nonirrgated demand: adjusted (and maybe increased) by gwabstration factor
                nonIrrDemandGW = self.var.nonIrrDemand  * (1- realswAbstractionFraction)

                # if nonirrgated water demand is higher than actual growndwater abstraction (wwhat is needed and what is stored in gw)
                nonIrrDemandGW  = np.where(nonIrrDemandGW > self.var.nonFossilGroundwaterAbs, self.var.nonFossilGroundwaterAbs, nonIrrDemandGW)
                self.var.act_nonIrrDemand = realswAbstractionFraction * self.var.nonIrrDemand + nonIrrDemandGW


                sum_irrDemandGW = self.var.sumIrrDemand  * (1- realswAbstractionFraction)
                sum_irrDemandGW = np.minimum(self.var.nonFossilGroundwaterAbs - nonIrrDemandGW, sum_irrDemandGW)
                self.var.act_irrDemand = realswAbstractionFraction * self.var.sumIrrDemand + sum_irrDemandGW

                # nonpaddy
                irrnonpaddyGW = self.var.fracVegCover[3] * (1- realswAbstractionFraction) * self.var.irrDemand[3]
                irrnonpaddyGW = np.minimum(self.var.nonFossilGroundwaterAbs - nonIrrDemandGW, irrnonpaddyGW)
                self.var.act_irrNonpaddyWithdrawal = self.var.fracVegCover[3] * realswAbstractionFraction * self.var.irrDemand[3]  +  irrnonpaddyGW
                # paddy
                irrpaddyGW = self.var.fracVegCover[2] * (1 - realswAbstractionFraction) * self.var.irrDemand[2]
                irrpaddyGW = np.minimum(self.var.nonFossilGroundwaterAbs - nonIrrDemandGW - irrnonpaddyGW, irrpaddyGW)
                self.var.act_irrPaddyDemand = self.var.fracVegCover[2] * realswAbstractionFraction * self.var.irrDemand[2]  +  irrpaddyGW

                # back to non fraction values
                self.var.irrDemand[2] = divideValues(self.var.act_irrPaddyDemand, self.var.fracVegCover[2])
                self.var.irrDemand[3] = divideValues(self.var.act_irrNonpaddyWithdrawal, self.var.fracVegCover[3])
                # consumption - irrigation (without loss) = demand  * efficiency
                self.var.irrConsumption[2] = self.var.irrDemand[2] * self.var.efficiencyPaddy
                self.var.irrConsumption[3] = self.var.irrDemand[3] * self.var.efficiencyNonpaddy

                # calculate real water demand, because irr demand has still demand from previous day included
                # if the demand from previous day is not fulfilled it is taken to the next day and so on
                # if we do not correct we double account each day the demand from previous days
                self.var.act_irrPaddyDemand = np.maximum(0, irrPaddyDemand - self.var.unmetDemandPaddy)
                self.var.act_irrNonpaddyDemand = np.maximum(0, irrNonpaddyDemand - self.var.unmetDemandNonpaddy)

                # unmet is either potGroundwaterAbstract - self.var.nonFossilGroundwaterAbs or demand - withdrawal
                #self.var.unmetDemand = np.maximum(0.0, self.var.potGroundwaterAbstract - self.var.nonFossilGroundwaterAbs)
                self.var.unmetDemand = (self.var.sumIrrDemand - self.var.act_irrDemand) + (self.var.nonIrrDemand - self.var.act_nonIrrDemand)
                self.var.unmetDemandPaddy = irrPaddyDemand - self.var.act_irrPaddyDemand
                self.var.unmetDemandNonpaddy = irrNonpaddyDemand - self.var.act_irrNonpaddyDemand


            else:
                # Fossil groundwater abstractions are allowed
                self.var.unmetDemand = self.var.potGroundwaterAbstract - self.var.nonFossilGroundwaterAbs

                self.var.act_nonIrrDemand = self.var.nonIrrDemand
                self.var.act_irrDemand = self.var.sumIrrDemand
                self.var.act_irrNonpaddyDemand = self.var.fracVegCover[3] * self.var.irrDemand[3]
                self.var.act_irrPaddyDemand = self.var.fracVegCover[2] * self.var.irrDemand[2]

            if (dateVar['curr'] == 1):
                ii = 1
            self.var.sumirrConsumption = self.var.fracVegCover[2] * self.var.irrConsumption[2] + self.var.fracVegCover[3] * self.var.irrConsumption[3]
            self.var.waterDemand =  self.var.act_irrPaddyDemand  + self.var.act_irrNonpaddyDemand + self.var.nonIrrDemand
            self.var.waterWithdrawal = self.var.act_nonIrrDemand + self.var.act_irrDemand




            #Sum up loss
            #sumIrrLoss = self.var.fracVegCover[2] * (self.var.irrDemand[2] - self.var.irrConsumption[2]) +  self.var.fracVegCover[3] * (self.var.irrDemand[3] - self.var.irrConsumption[3])
            sumIrrLoss =  self.var.act_irrDemand - self.var.sumirrConsumption
            #sumIrrLoss = self.var.act_irrPaddyDemand - (self.var.fracVegCover[2] * self.var.irrConsumption[2]) +
            self.var.returnflowIrr =  self.var.returnfractionIrr * sumIrrLoss
            self.var.addtoevapotrans = (1- self.var.returnfractionIrr) *  sumIrrLoss



            # returnflow to river and to evapotranspiration
            self.var.returnFlow = self.var.nonIrrReturnFlowFraction * self.var.act_nonIrrDemand + self.var.returnflowIrr

            #if addtoevapotrans  > 0:
            #    jjj =1

            # This is done in landcover.py, therefore it is out commented
            #self.var.totalET += self.var.addtoevapotrans


            """
            area = self.var.area1.astype(np.int64)
            diff = 1000000000.
            irrDemand = self.var.act_irrDemand * self.var.MtoM3 / diff
            self.var.sum_IrrDemand = npareatotal(irrDemand, area)
            withd = self.var.waterWithdrawal * self.var.MtoM3 / diff
            self.var.sum_waterWithdrawal = npareatotal(withd, area)
            """

            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.act_irrDemand],  # In
                    [self.var.sumirrConsumption, self.var.returnflowIrr,self.var.addtoevapotrans],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterlossdemand1", False)



            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.nonIrrDemand, self.var.sumIrrDemand],  # In
                    [self.var.nonFossilGroundwaterAbs, self.var.unmetDemand, self.var.actSurfaceWaterAbstract],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand1", False)


            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.nonFossilGroundwaterAbs, self.var.unmetDemand, self.var.actSurfaceWaterAbstract],  # In
                    [self.var.waterWithdrawal],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand2", False)


            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.waterWithdrawal],  # In
                    [self.var.act_irrPaddyDemand, self.var.act_irrNonpaddyDemand, self.var.act_nonIrrDemand],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand3", False)

            nonIrrReturn = self.var.nonIrrReturnFlowFraction * self.var.act_nonIrrDemand
            nonIrruse = self.var.act_nonIrrDemand - nonIrrReturn

            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.waterWithdrawal],  # In
                    [self.var.sumirrConsumption,self.var.returnflowIrr,self.var.addtoevapotrans, nonIrruse, nonIrrReturn],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand4", False)

            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.waterWithdrawal],  # In
                    [self.var.sumirrConsumption,self.var.returnFlow,self.var.addtoevapotrans, nonIrruse],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand5", False)