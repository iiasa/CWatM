# -------------------------------------------------------------------------
# Name:        Waterdemand modules
# Purpose:
#
# Author:      PB, YS, MS, JdB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from cwatm.management_modules import globals
import numpy as np
from cwatm.management_modules.data_handling import returnBool, binding, cbinding, loadmap, readnetcdf2, divideValues

class waterdemand_domestic:
    """
    WATERDEMAND domestic

    calculating water demand -
    domenstic based on precalculated maps

    **Global variables**

    ====================  ================================================================================  =========
    Variable [self.var]   Description                                                                       Unit     
    ====================  ================================================================================  =========
    domesticTime                                                                                                     
    domWithdrawalVar                                                                                                 
    domConsumptionVar                                                                                                
    domesticDemand                                                                                                   
    pot_domesticConsumpt                                                                                             
    InvCellArea           Inverse of cell area of each simulated mesh                                       m-1      
    M3toM                 Coefficient to change units                                                       --       
    dom_efficiency                                                                                                   
    demand_unit                                                                                                      
    ====================  ================================================================================  =========

    **Functions**
    """


    def __init__(self, model):
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initial part of the water demand module

        """

        if "domesticTimeMonthly" in binding:
            if returnBool('domesticTimeMonthly'):
                self.var.domesticTime = 'monthly'
            else:
                self.var.domesticTime = 'yearly'
        else:
            self.var.domesticTime = 'monthly'

        if "domesticWithdrawalvarname" in binding:
            self.var.domWithdrawalVar = cbinding("domesticWithdrawalvarname")
        else:
            self.var.domWithdrawalVar = "domesticGrossDemand"
        if "domesticConsuptionvarname" in binding:
            self.var.domConsumptionVar = cbinding("domesticConsuptionvarname")
        else:
            self.var.domConsumptionVar = "domesticNettoDemand"

    def dynamic(self,wd_date):
        """
        Dynamic part of the water demand module - domestic
        read monthly (or yearly) water demand from netcdf and transform (if necessary) to [m/day]

        """

        if self.var.domesticTime == 'monthly':
            new = 'newMonth'
        else:
            new = 'newYear'
        
        if globals.dateVar['newStart'] or globals.dateVar[new]:

            if 'sw_agentsUrban_month_m3' in binding:
                self.var.demand_unit = False
                self.var.urbanWithdrawalSW_max = loadmap('sw_agentsUrban_month_m3') + globals.inZero.copy()
                self.var.urbanWithdrawalGW_max = loadmap('gw_agentsUrban_month_m3') + globals.inZero.copy()

                #self.var.urbanWithdrawalSW_max *=1.5 #experiment
                #self.var.urbanWithdrawalGW_max *=1.5 #experiment

                self.var.domesticDemand = self.var.urbanWithdrawalSW_max + self.var.urbanWithdrawalGW_max
                self.var.swAbstractionFraction_nonIrr = divideValues(self.var.urbanWithdrawalSW_max,
                                                                     self.var.domesticDemand)
                self.var.domesticDemand /= 1000000
                self.var.pot_domesticConsumption = self.var.domesticDemand.copy() * 0.3  # This will be an input from the Urban module, 0.3 is an assumption for testing

            else:

                self.var.domesticDemand = readnetcdf2('domesticWaterDemandFile', wd_date, self.var.domesticTime, value=self.var.domWithdrawalVar)
                self.var.pot_domesticConsumption = readnetcdf2('domesticWaterDemandFile', wd_date, self.var.domesticTime, value=self.var.domConsumptionVar)
                # avoid small values (less than 1 m3):
                self.var.domesticDemand = np.where(self.var.domesticDemand > self.var.InvCellArea, self.var.domesticDemand, 0.0)

                # test
                #self.var.pot_domesticConsumption = self.var.domesticDemand.copy()
                self.var.pot_domesticConsumption = np.where(self.var.pot_domesticConsumption > self.var.InvCellArea, self.var.pot_domesticConsumption, 0.0)


            self.var.dom_efficiency = divideValues(self.var.pot_domesticConsumption, self.var.domesticDemand)


            # transform from mio m3 per year (or month) to m/day if necessary
            if not self.var.demand_unit:
                if self.var.domesticTime == 'monthly':
                    timediv= globals.dateVar['daysInMonth']
                else:
                    timediv = globals.dateVar['daysInYear']
                self.var.domesticDemand = self.var.domesticDemand * 1000000 * self.var.M3toM / timediv
                self.var.pot_domesticConsumption = self.var.pot_domesticConsumption * 1000000 * self.var.M3toM / timediv