# -------------------------------------------------------------------------
# Name:        Waterdemand modules
# Purpose: Livestock water demand module for animal husbandry water requirements.
# Computes water consumption for different livestock categories and densities.
# Handles seasonal variations and regional differences in livestock water needs.
#
# Author:      PB, YS, MS, JdB, DF
# Created:     15/07/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import numpy as np
from cwatm.management_modules import globals
from cwatm.management_modules.data_handling import returnBool, binding, cbinding, loadmap, readnetcdf2

class waterdemand_livestock:
    """
    Livestock water demand module for animal husbandry water requirements.
    
    This class computes water consumption for different livestock categories and densities.
    It handles seasonal variations and regional differences in livestock water needs based
    on precalculated maps. The module supports both monthly and yearly demand calculations
    and can be enabled or disabled through configuration settings.
    
    Attributes
    ----------
    var : object
        Model variables container from parent model
    model : object
        Parent CWatM model instance

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    M3toM                                Array         Coefficient to change units                                             --   
    domesticTime                         List          Monthly' when domesticTimeMonthly = True, and 'Yearly' otherwise.       str  
    livestockTime                        List                                                                                  --   
    livVar                               List                                                                                  --   
    uselivestock                         Flag          True if uselivestock=True in Settings, False otherwise                  bool 
    InvCellArea                          Array         Inverse of cell area of each simulated mesh                             1/m2 
    demand_unit                          Flag                                                                                  --   
    livestockDemand                      Array                                                                                 --   
    pot_livestockConsumption             Array         Potential livestock consumption                                         m    
    liv_efficiency                       Number        Livestock water use efficiency                                          --   
    ===================================  ==========    ======================================================================  =====

    """
    def __init__(self, model):
        """
        Initialize the livestock water demand module.
        
        Parameters
        ----------
        model : object
            The CWatM model instance containing variables and methods
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initialize livestock water demand parameters and settings.
        
        Sets up time resolution (monthly/yearly), variable names for livestock demand data,
        and configures whether livestock water demand calculations are enabled.
        Initializes livestock demand processing parameters for animal water requirements.
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

    def dynamic(self, wd_date):
        """
        Calculate dynamic livestock water demand for the current time step.
        
        Reads monthly or yearly livestock water demand from NetCDF files when enabled,
        transforms units to m/day if necessary, and processes livestock water consumption.
        Sets livestock demand to zero when livestock calculations are disabled.
        Assumes 100% efficiency for livestock water use (consumption equals demand).
        
        Parameters
        ----------
        wd_date : datetime
            Current simulation date for reading time-dependent data
        """
        if self.var.uselivestock:
            new = 'newYear'
            if self.var.livestockTime == 'monthly':
                new = 'newMonth'
            if globals.dateVar['newStart'] or globals.dateVar[new]:
                self.var.livestockDemand = readnetcdf2('livestockWaterDemandFile', wd_date,
                                                        self.var.domesticTime, value=self.var.livVar)
                # avoid small values (less than 1 m3):
                self.var.livestockDemand = np.where(self.var.livestockDemand > self.var.InvCellArea,
                                                     self.var.livestockDemand, 0.0)
                self.var.pot_livestockConsumption = self.var.livestockDemand
                self.var.liv_efficiency = 1.

                # transform from mio m3 per year (or month) to m/day if necessary
                # if demand_unit = False -> transform from mio m3 per month or year
                if not self.var.demand_unit:
                    if self.var.livestockTime == 'monthly':
                        timediv = globals.dateVar['daysInMonth']
                    else:
                        timediv = globals.dateVar['daysInYear']
                    self.var.livestockDemand = (self.var.livestockDemand * 1000000 *
                                                 self.var.M3toM / timediv)
                    self.var.pot_livestockConsumption = self.var.livestockDemand

        else:
            self.var.livestockDemand = 0.
            self.var.pot_livestockConsumption = 0.
            self.var.liv_efficiency = 1.