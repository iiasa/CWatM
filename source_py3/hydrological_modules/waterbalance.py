#-------------------------------------------------------------------------
#Name:        Water Balance module
#Purpose:
#1.) check if water balance per time step is ok ( = 0)
#2.) produce an annual overview - income, outcome storage
#Author:      PB
#
#Created:     22/08/2016
#Copyright:   (c) PB 2016
#-------------------------------------------------------------------------

from management_modules.data_handling import *

class waterbalance(object):
    """
    WATER BALANCE
    
    * check if water balnace per time step is ok ( = 0)
    * produce an annual overview - income, outcome storage
    """

    def __init__(self, waterbalance_variable):
        self.var = waterbalance_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """
        Initial part of the water balance module
        """

        if checkOption('calcWaterBalance'):

            self.var.nonIrrReturnFlow = 0
            self.var.localQW = 0
            self.var.channelStorageBefore = 0

        """ store the initial storage volume of snow, soil etc.
        """
        if checkOption('sumWaterBalance'):
            # variables of storage
            self.var.sum_balanceStore = ['SnowCover','sum_interceptStor','sum_topWaterLayer']

            # variable of fluxes
            self.var.sum_balanceFlux = ['Precipitation','SnowMelt','Rain','sum_interceptEvap','actualET']

            #for variable in self.var.sum_balanceStore:
                # vars(self.var)["sumup_" + variable] =  vars(self.var)[variable]
            for variable in self.var.sum_balanceFlux:
                vars(self.var)["sumup_" + variable] =  globals.inZero.copy()



# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def waterBalanceCheck(self, fluxesIn, fluxesOut, preStorages, endStorages, processName, printTrue=False):
        """
        Dynamic part of the water balance module

        Returns the water balance for a list of input, output, and storage map files

        :param fluxesIn: income
        :param fluxesOut: this goes out
        :param preStorages:  this was in before
        :param endStorages:  this was in afterwards
        :param processName:  name of the process
        :param printTrue: calculate it?
        :return: -
        """

        if printTrue:
            minB =0
            maxB = 0
            maxBB = 0
            income =  0
            out = 0
            store = 0

            for fluxIn in fluxesIn:   income += fluxIn
            for fluxOut in fluxesOut:
                out += fluxOut
            for preStorage in preStorages: store += preStorage
            for endStorage in endStorages: store -= endStorage
            balance =  income + store - out
            #balance = endStorages
            #if balance is not empty
            if balance.size:
                balance[np.isnan(balance)]= 0
                minB = np.amin(balance)
                maxB = np.amax(balance)
                maxBB = np.maximum(np.abs(minB),np.abs(maxB))
            #meanB = np.average(balance, axis=0)
            #meanB = 0.0

            # print ("     %s %10.8f " % (processName, maxBB),)
            #if maxBB > 0.00000001:
            #    sys.exit()
            if maxBB > 0.0000000001:
                print("     %s %10.8f %10.8f" % (processName, minB,maxB), end=' ')
                #quit()
                if (minB < -0.00001) or (maxB > 0.00001):
                   i=11111

            return maxBB



    def waterBalanceCheckSum(self, fluxesIn, fluxesOut, preStorages, endStorages, processName, printTrue=False):
        """
        Returns the water balance for a list of input, output, and storage map files
        and sums it up for a catchment

        :param fluxesIn: income
        :param fluxesOut: this goes out
        :param preStorages:  this was in before
        :param endStorages:  this was in afterwards
        :param processName:  name of the process
        :param printTrue: calculate it?
        :return: Water balance as output on the screen
        """

        if printTrue:
            minB =0
            maxB = 0
            maxBB = 0

            income =  0
            out = 0
            store =  0

            for fluxIn in fluxesIn:
                if not(isinstance(fluxIn,np.ndarray)) : fluxIn = globals.inZero
                income = income + np.bincount(self.var.catchmentAll,weights=fluxIn)
            for fluxOut in fluxesOut:
                if not (isinstance(fluxOut, np.ndarray)): fluxOut = globals.inZero
                out = out + np.bincount(self.var.catchmentAll,weights=fluxOut)
            for preStorage in preStorages:
                if not (isinstance(preStorage, np.ndarray)): preStorage = globals.inZero
                store = store + np.bincount(self.var.catchmentAll,weights=preStorage)
            for endStorage in endStorages:
                if not (isinstance(endStorage, np.ndarray)): endStorage = globals.inZero
                store = store - np.bincount(self.var.catchmentAll,weights=endStorage)
            balance =  income + store - out
            #balance = endStorages
            #if balance.size:
                #minB = np.amin(balance)
                #maxB = np.amax(balance)
                #maxBB = np.maximum(np.abs(minB),np.abs(maxB))
                #meanB = np.average(balance, axis=0)
                #meanB = 0.0
            #no = self.var.catchmentNo
            no = 0


            #print "     %s %10.8f " % (processName, maxBB),
            #print "     %s %10.8f %10.8f" % (processName, minB,maxB),
            #print "     %s %10.8f" % (processName, balance[no]),
            print("     %s %10.8f" % (processName, balance[no]), end=' ')

            #avgArea = npareaaverage(self.var.cellArea, self.var.catchmentAll)
            #dis = balance[no] * avgArea[0] / self.var.DtSec
            #print "     %s %10.8f" % (processName, dis),
            return balance[no]





# ----------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------

    def checkWaterSoilGround(self):
        """
        Check water balance of snow, vegetation, soil, groundwater
        """

        if checkOption('calcWaterBalance'):

            """
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.Precipitation, self.var.sumirrConsumption],
                [self.var.sum_directRunoff, self.var.sum_interflow, self.var.sum_gwRecharge,self.var.totalET],  # Out
                [self.var.pretotalSto],  # prev storage
                [self.var.totalSto],
                "Soil_all", False)


            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.Precipitation, self.var.sumirrConsumption,self.var.sum_capRiseFromGW],
                [self.var.sum_directRunoff, self.var.sum_perc3toGW, self.var.sum_prefFlow,
                 self.var.totalET],  # Out
                [self.var.pretotalSto],  # prev storage
                [self.var.totalSto],
                "Soil_all1", False)



            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.Precipitation, self.var.sumirrConsumption,self.var.sum_capRiseFromGW],
                [self.var.sum_directRunoff, self.var.sum_perc3toGW, self.var.sum_prefFlow,
                 self.var.sum_actTransTotal, self.var.sum_actBareSoilEvap, self.var.sum_openWaterEvap, self.var.sum_interceptEvap, self.var.snowEvap],  # Out
                [self.var.pretotalSto],  # prev storage
                [self.var.totalSto],
                "Soil_all2", False)

            #if self.var.sumirrConsumption > 0:
            #    iii =1


            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.Precipitation, self.var.sumirrConsumption],
                [self.var.sum_directRunoff, self.var.sum_interflow, self.var.nonFossilGroundwaterAbs,self.var.baseflow,
                 self.var.sum_actTransTotal, self.var.sum_actBareSoilEvap, self.var.sum_openWaterEvap, self.var.sum_interceptEvap, self.var.snowEvap],  # Out
                [self.var.pretotalSto,self.var.prestorGroundwater],  # prev storage
                [self.var.totalSto,self.var.storGroundwater],
                "Soil+G", False)

            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.unmetDemand,self.var.nonFossilGroundwaterAbs, self.var.act_SurfaceWaterAbstract], # In
                [self.var.act_irrDemand,self.var.act_nonIrrDemand],     # Out
                [globals.inZero],
                [globals.inZero],
                "Waterdemand1", False)

            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.act_irrDemand],  # In
                [self.var.sumirrConsumption, self.var.returnflowIrr,self.var.addtoevapotrans],  # Out
                [globals.inZero],
                [globals.inZero],
                "Waterdemand2", False)



            self.var.waterbalance_module.waterBalanceCheckSum(
                [self.var.Precipitation, self.var.act_irrDemand],
                [self.var.sum_directRunoff, self.var.sum_interflow, self.var.nonFossilGroundwaterAbs,self.var.baseflow,
                 self.var.sum_actTransTotal, self.var.sum_actBareSoilEvap, self.var.sum_openWaterEvap, self.var.sum_interceptEvap, self.var.snowEvap,
                 self.var.returnflowIrr, self.var.addtoevapotrans],  # Out
                [self.var.pretotalSto,self.var.prestorGroundwater],  # prev storage
                [self.var.totalSto,self.var.storGroundwater],
                "Soil+G+WD", False)

            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.Precipitation, self.var.act_irrDemand],
                [self.var.totalET, self.var.runoff, self.var.nonFossilGroundwaterAbs, self.var.returnflowIrr],  # Out
                [self.var.pretotalSto,self.var.prestorGroundwater],  # prev storage
                [self.var.totalSto,self.var.storGroundwater],
                "Soil+G+WD2", False)

            nonIrrReturn = self.var.nonIrrReturnFlowFraction * self.var.act_nonIrrDemand
            nonIrruse = self.var.act_nonIrrDemand - nonIrrReturn

            if checkOption('includeWaterBodies'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.Precipitation, self.var.unmetDemand, self.var.act_SurfaceWaterAbstract],
                    [self.var.totalET, self.var.runoff, self.var.returnflowIrr, self.var.act_nonIrrDemand,  self.var.smallrunoffDiff ],  # Out
                    [self.var.pretotalSto,self.var.prestorGroundwater],  # prev storage
                    [self.var.totalSto,self.var.storGroundwater],
                    "Soil+G+WD31", False)

                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.Precipitation, self.var.unmetDemand, self.var.act_SurfaceWaterAbstract],
                    [self.var.totalET, self.var.runoff, self.var.returnFlow, nonIrruse, self.var.smallrunoffDiff],  # Out
                    [self.var.pretotalSto,self.var.prestorGroundwater],  # prev storage
                    [self.var.totalSto,self.var.storGroundwater ],
                    "Soil+G+WD32", False)


                if checkOption('calcWaterBalance'):
                    self.var.waterbalance_module.waterBalanceCheck(
                        [self.var.lakeResInflowM],  # In
                        [self.var.lakeResOutflowM, self.var.EvapWaterBodyM],  # Out  self.var.evapWaterBodyC
                        [self.var.prelakeResStorage / self.var.cellArea],  # prev storage
                        [self.var.lakeResStorage / self.var.cellArea],
                        "LR1", False)

                if checkOption('calcWaterBalance') and returnBool('useSmallLakes'):
                    self.var.waterbalance_module.waterBalanceCheck(
                        [self.var.smallLakeIn],  # In
                        [self.var.smallLakeout,  self.var.smallevapWaterBody],  # Out
                        [self.var.preSmalllakeStorage / self.var.cellArea],  # prev storage
                        [self.var.smalllakeStorage / self.var.cellArea],
                        "LR2", False)


                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.Precipitation, self.var.unmetDemand, self.var.act_SurfaceWaterAbstract],
                    [self.var.totalET, self.var.runoff, self.var.returnFlow, nonIrruse, self.var.lakeResOutflowM - self.var.lakeResInflowM, self.var.EvapWaterBodyM,
                     self.var.smallrunoffDiff],  # Out
                    [self.var.pretotalSto,self.var.prestorGroundwater, self.var.prelakeResStorage/ self.var.cellArea, ],  # prev storage
                    [self.var.totalSto,self.var.storGroundwater, self.var.lakeResStorage/ self.var.cellArea],
                    "Soil+G+WD+LR", False)

                if checkOption('calcWaterBalance') and returnBool('useSmallLakes'):
                    self.var.waterbalance_module.waterBalanceCheck(
                        [self.var.Precipitation, self.var.unmetDemand, self.var.act_SurfaceWaterAbstract],
                        [self.var.totalET, self.var.runoff, self.var.returnFlow, nonIrruse, self.var.lakeResOutflowM - self.var.lakeResInflowM ,
                         self.var.smallLakeout - self.var.smallLakeIn, self.var.EvapWaterBodyM,  self.var.smallevapWaterBody, self.var.smallrunoffDiff],  # Out
                        [self.var.pretotalSto,self.var.prestorGroundwater, self.var.prelakeResStorage/ self.var.cellArea, self.var.preSmalllakeStorage / self.var.cellArea],  # prev storage
                        [self.var.totalSto,self.var.storGroundwater, self.var.lakeResStorage/ self.var.cellArea, self.var.smalllakeStorage / self.var.cellArea ],
                        "Soil+G+WD+LR2", False)


                if checkOption('calcWaterBalance') and returnBool('useSmallLakes'):
                    self.var.waterbalance_module.waterBalanceCheck(
                        [self.var.Precipitation, self.var.unmetDemand, self.var.act_SurfaceWaterAbstract],
                        [self.var.totalET, self.var.runoff, self.var.returnFlow, nonIrruse,self.var.lakeResOutflowM - self.var.lakeResInflowM ,
                         self.var.EvapWaterBodyM,  self.var.smallevapWaterBody,  self.var.smallLakeDiff],  # Out
                        [self.var.pretotalSto,self.var.prestorGroundwater, self.var.prelakeResStorage/ self.var.cellArea, self.var.preSmalllakeStorage / self.var.cellArea],  # prev storage
                        [self.var.totalSto,self.var.storGroundwater, self.var.lakeResStorage/ self.var.cellArea, self.var.smalllakeStorage / self.var.cellArea ],
                        "Soil+G+WD+LR22", False)

#### IMPORTANT set Routingstep to 1 to test!

            DisOut = self.var.discharge * self.var.DtSec / self.var.cellArea
            DisOut = np.where(self.var.lddCompress == 5, DisOut, 0.)



            self.var.waterbalance_module.waterBalanceCheckSum(
                [self.var.runoff, self.var.returnFlow],  # In
                [self.var.sumsideflow / self.var.cellArea, self.var.EvapoChannel / self.var.cellArea, self.var.act_SurfaceWaterAbstract, ],  # Out
                [],  # prev storage
                [],
                "rout1", False)

            self.var.waterbalance_module.waterBalanceCheckSum(
                [self.var.runoff, self.var.returnFlow],  # In
                [DisOut, self.var.EvapoChannel / self.var.cellArea, self.var.act_SurfaceWaterAbstract],  # Out
                [self.var.prechannelStorage / self.var.cellArea],  # prev storage
                [self.var.channelStorage / self.var.cellArea],
                "rout4", False)

            self.var.waterbalance_module.waterBalanceCheckSum(
                [self.var.Precipitation, self.var.unmetDemand],
                [self.var.totalET, self.var.EvapoChannel / self.var.cellArea, nonIrruse, DisOut ],  # Out
                [self.var.pretotalSto,self.var.prestorGroundwater, self.var.prechannelStorage / self.var.cellArea],  # prev storage
                [self.var.totalSto,self.var.storGroundwater, self.var.channelStorage / self.var.cellArea ],
                "Soil+G+WD+R", False)



            #print self.var.channelStorageBefore[10],
            # print "%10.8f %10.8f %10.8f " % (income[10], out[10], store[10]),
            """


        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


        if checkOption('sumWaterBalance'):
            """
            self.var.waterbalance_module.waterBalanceCheckSum(
                [self.var.nonFossilGroundwaterAbs, self.var.unmetDemand, self.var.act_SurfaceWaterAbstract],  # In
                [self.var.waterWithdrawal],  # Out
                [globals.inZero],
                [globals.inZero],
                "WaterdemandSum", False)

            self.var.waterbalance_module.waterBalanceCheckSum(
                [self.var.Precipitation, self.var.surfaceWaterInf,self.var.sumIrrDemand,self.var.nonIrrReturnFlow],    # In
                [self.var.totalET,   self.var.localQW, self.var.riverbedExchange * self.var.InvCellArea, self.var.nonFossilGroundwaterAbs, self.var.act_SurfaceWaterAbstract],
                [self.var.pretotalSto,self.var.prestorGroundwater,self.var.prechannelStorage * self.var.InvCellArea],       # prev storage
                [self.var.totalSto,self.var.storGroundwater,self.var.channelStorageBefore * self.var.InvCellArea],
                "S+G+Rout1Sum", False)
            """

            # discharge at outlets of catchments
            """
            DisOut = self.var.discharge * self.var.DtSec
            DisOut = np.where(self.var.outlets > 0, DisOut, 0.)

            self.var.waterbalance_module.waterBalanceCheckSum(
                [self.var.Precipitation * self.var.cellArea, self.var.surfaceWaterInf * self.var.cellArea, self.var.sum_irrDemand * self.var.cellArea,self.var.nonIrrReturnFlow * self.var.cellArea],    # In
                [self.var.totalET  * self.var.cellArea,   self.var.localQW  * self.var.cellArea, self.var.riverbedExchange, self.var.nonFossilGroundwaterAbs * self.var.cellArea, self.var.sum_act_SurfaceWaterAbstract * self.var.cellArea, DisOut],
                [self.var.prevSnowCover * self.var.cellArea, self.var.pretotalSoil * self.var.cellArea,self.var.prestorGroundwater * self.var.cellArea,self.var.prechannelStorage],       # prev storage
                [self.var.SnowCover * self.var.cellArea, self.var.totalSoil * self.var.cellArea,self.var.storGroundwater * self.var.cellArea,self.var.channelStorage],
                "S+G+Rout2Sum", False)
            """

        """
        if checkOption('budyko'):


            # in mm
            self.var.sumETRef =[]
            self.var.sumP = []
            self.var.sumETA = []
            for i in xrange(self.var.noOutpoints):
                # TODO change this to store in arrays not in maps for each gauge station!
                area = npareatotal(self.var.cellArea, self.var.evalCatch[i])
                self.var.sumETRef.append(1000 * npareatotal(self.var.ETRef * self.var.cellArea, self.var.evalCatch[i]) / area)
                self.var.sumP.append(1000 * npareatotal(self.var.Precipitation * self.var.cellArea, self.var.evalCatch[i]) / area)
                self.var.sumETA.append(1000 * npareatotal((self.var.totalET) * self.var.cellArea, self.var.evalCatch[i]) / area)

            ##self.var.area = npareatotal(self.var.cellArea, self.var.catchment)
            ##self.var.sumETRef = 1000 * npareatotal(self.var.ETRef * self.var.cellArea, self.var.catchment)/self.var.area
            ##self.var.sumP = 1000 * npareatotal(self.var.Precipitation * self.var.cellArea, self.var.catchment) / self.var.area
            #self.var.sumETA = 1000 * npareatotal((self.var.totalET + self.var.localQW) * self.var.cellArea , self.var.catchment)/self.var.area
            ##self.var.sumETA = 1000 * npareatotal((self.var.totalET) * self.var.cellArea, self.var.catchment) / self.var.area
            #self.var.sumRunoff = 1000 *  npareatotal((self.var.channelStorageBefore - self.var.prechannelStorage), self.var.catchment)/self.var.area
            #self.var.sumDelta1 = 1000 * npareatotal((self.var.SnowCover + self.var.totalSoil + self.var.storGroundwater) * self.var.cellArea , self.var.catchment)/self.var.area
            #self.var.sumDelta2 = 1000 * npareatotal((self.var.prevSnowCover + self.var.pretotalSoil + self.var.prestorGroundwater) * self.var.cellArea , self.var.catchment)/self.var.area
            #self.var.sumAll = self.var.sumDelta1- self.var.sumDelta2


            #report(decompress(self.var.sumRunoff), "C:\work\output3/sumRun.map")

        """



    def dynamic(self):
        """
        Dynamic part of the water balance module
        If option **sumWaterBalance** sum water balance for certain variables
        """

        #if checkOption('sumWaterBalance'):
        #    i = 1

        # sum up storage variables
        #for variable in self.var.sum_balanceStore:
         #   vars(self.var)["sumup_" + variable] =  vars(self.var)[variable].copy()


        # sum up fluxes variables
        for variable in self.var.sum_balanceFlux:
            vars(self.var)["sumup_" + variable] = vars(self.var)["sumup_" + variable] + vars(self.var)[variable]