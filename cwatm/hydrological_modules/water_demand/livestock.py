import numpy as np
from cwatm.management_modules import globals
from cwatm.management_modules.data_handling import returnBool, binding, cbinding, loadmap, readnetcdf2

class waterdemand_livestock:
    def __init__(self, model):
        self.var = model.var
        self.model = model

    def initial(self):
        self.var.livestockTime = 'monthly'
        if "livestockTimeMonthly" in binding:
            if returnBool('livestockTimeMonthly'):
                self.var.livestockTime = 'monthly'
            else:
                self.var.livestockTime = 'yearly'
        else:
            self.var.livestockTime = 'monthly'

        if "livestockvarname" in binding:
            self.var.livVar = cbinding("livestockvarname")
        else:
            self.var.livVar = "livestockDemand"

        if "uselivestock" in binding:
            self.var.uselivestock = returnBool('uselivestock')
        else:
            self.var.uselivestock = False

    def dynamic(self):
        if self.var.uselivestock:
            new = 'newYear'
            if self.var.livestockTime == 'monthly': new = 'newMonth'
            if globals.dateVar['newStart'] or globals.dateVar[new]:
                self.var.livestockDemand = readnetcdf2('livestockWaterDemandFile', globals.dateVar['currDate'], self.var.domesticTime, value=self.var.livVar)
                # avoid small values (less than 1 m3):
                self.var.livestockDemand = np.where(self.var.livestockDemand > self.var.InvCellArea, self.var.livestockDemand, 0.0)
                self.var.pot_livestockConsumption =  self.var.livestockDemand # the same, it is not a copy!
                self.var.liv_efficiency = 1.

                # transform from mio m3 per year (or month) to m/day if necessary - if demand_unit = False -> transdform from mio m3 per month or year
                if not self.var.demand_unit:
                    if self.var.livestockTime == 'monthly':
                        timediv = globals.dateVar['daysInMonth']
                    else:
                        timediv = globals.dateVar['daysInYear']
                    self.var.livestockDemand = self.var.livestockDemand * 1000000 * self.var.M3toM / timediv

        else:
            self.var.livestockDemand = 0.
            self.var.pot_livestockConsumption = 0.
            self.var.liv_efficiency = 1.