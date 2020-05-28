from cwatm.management_modules import globals
import numpy as np
from cwatm.management_modules.data_handling import returnBool, binding, cbinding, loadmap, readnetcdf2, divideValues

class waterdemand_domestic:
    def __init__(self, model):
        self.var = model.var
        self.model = model

    def initial(self):
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

    def dynamic(self):
        if self.var.domesticTime == 'monthly':
            new = 'newMonth'
        else:
            new = 'newYear'
        
        if globals.dateVar['newStart'] or globals.dateVar[new]:
            self.var.domesticDemand = readnetcdf2('domesticWaterDemandFile', globals.dateVar['currDate'], self.var.domesticTime, value=self.var.domWithdrawalVar)
            self.var.pot_domesticConsumption = readnetcdf2('domesticWaterDemandFile', globals.dateVar['currDate'], self.var.domesticTime, value=self.var.domConsumptionVar)
            # avoid small values (less than 1 m3):
            self.var.domesticDemand = np.where(self.var.domesticDemand > self.var.InvCellArea, self.var.domesticDemand, 0.0)
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