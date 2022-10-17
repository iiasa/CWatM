# -------------------------------------------------------------------------
# Name:        Waterdemand modules
# Purpose:
#
# Author:      PB, YS, MS, JdB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

import numpy as np
from cwatm.management_modules import globals
from cwatm.management_modules.data_handling import returnBool, binding, cbinding, loadmap, readnetcdf2

class waterdemand_livestock:
    """
    WATERDEMAND livestock

    calculating water demand -
    livestock based on precalculated maps

    **Global variables**

    =====================================  ======================================================================  =====
    Variable [self.var]                    Description                                                             Unit 
    =====================================  ======================================================================  =====
    domesticTime                           Monthly' when domesticTimeMonthly = True, and 'Yearly' otherwise.       str  
    livestockTime                                                                                                       
    livVar                                                                                                              
    uselivestock                           True if uselivestock=True in Settings, False otherwise                  bool 
    pot_livestockConsumption                                                                                            
    InvCellArea                            Inverse of cell area of each simulated mesh                             1/m2 
    M3toM                                  Coefficient to change units                                             --   
    demand_unit                                                                                                         
    livestockDemand                                                                                                     
    liv_efficiency                                                                                                      
    =====================================  ======================================================================  =====

    **Functions**
    """
    def __init__(self, model):
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initial part of the water demand module - livestock

        """

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

    def dynamic(self,wd_date):
        """
        Dynamic part of the water demand module - livestock
        read monthly (or yearly) water demand from netcdf and transform (if necessary) to [m/day]

        """
        if self.var.uselivestock:
            new = 'newYear'
            if self.var.livestockTime == 'monthly': new = 'newMonth'
            if globals.dateVar['newStart'] or globals.dateVar[new]:
                self.var.livestockDemand = readnetcdf2('livestockWaterDemandFile', wd_date, self.var.domesticTime, value=self.var.livVar)
                # avoid small values (less than 1 m3):
                self.var.livestockDemand = np.where(self.var.livestockDemand > self.var.InvCellArea, self.var.livestockDemand, 0.0)
                self.var.pot_livestockConsumption =  self.var.livestockDemand
                self.var.liv_efficiency = 1.

                # transform from mio m3 per year (or month) to m/day if necessary - if demand_unit = False -> transdform from mio m3 per month or year
                if not self.var.demand_unit:
                    if self.var.livestockTime == 'monthly':
                        timediv = globals.dateVar['daysInMonth']
                    else:
                        timediv = globals.dateVar['daysInYear']
                    self.var.livestockDemand = self.var.livestockDemand * 1000000 * self.var.M3toM / timediv
                    self.var.pot_livestockConsumption = self.var.livestockDemand

        else:
            self.var.livestockDemand = 0.
            self.var.pot_livestockConsumption = 0.
            self.var.liv_efficiency = 1.