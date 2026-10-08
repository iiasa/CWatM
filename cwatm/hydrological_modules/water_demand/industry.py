# -------------------------------------------------------------------------
# Name:        Waterdemand modules
# Purpose: Industrial water demand module for manufacturing and commercial water requirements.
# Computes water consumption for industrial activities based on economic indicators.
# Handles sectoral water use patterns and industrial water efficiency trends.
#
# Author:      PB, YS, MS, JdB, DF
# Created:     15/07/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules import globals
import numpy as np
from cwatm.management_modules.data_handling import (returnBool, binding, cbinding, loadmap, readnetcdf2,
                                                     divideValues, option, checkOption)

class waterdemand_industry:
    """
    Industrial water demand module for manufacturing and commercial water requirements.
    
    This class computes water consumption for industrial activities based on economic
    indicators and sectoral water use patterns. It handles industrial water efficiency
    trends and supports both monthly and yearly demand calculations with scaling factors.
    The module processes withdrawal and consumption data separately.
    
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
    industryTime                         List          Monthly' when industryTimeMonthly = True, and 'Yearly' otherwise.       --   
    indWithdrawalVar                     List          Settings industryWithdrawalvarname, variable name in industryWaterDema  --   
    indConsumptionVar                    List          Settings industryConsuptionvarname, variable name in domesticWaterDema  --   
    pot_industryConsumption              Array                                                                                 --   
    M3toM                                Array         Coefficient to change units                                             --   
    InvCellArea                          Array         Inverse of cell area of each simulated mesh                             1/m2 
    demand_unit                          Flag                                                                                  --   
    industryDemand                       Array                                                                                 --   
    ind_efficiency                       Array                                                                                 --   
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize the industrial water demand module.
        
        Parameters
        ----------
        model : object
            The CWatM model instance containing variables and methods
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initialize industrial water demand parameters and variable names.
        
        Sets up time resolution (monthly/yearly) for industrial demand calculations,
        configures variable names for withdrawal and consumption data reading,
        and initializes industrial water demand processing parameters.
        """
        if "industryTimeMonthly" in binding:
            if returnBool('industryTimeMonthly'):
                self.var.industryTime = 'monthly'
            else:
                self.var.industryTime = 'yearly'
        else:
            self.var.industryTime = 'monthly'

        if "industryWithdrawalvarname" in binding:
            self.var.indWithdrawalVar = cbinding("industryWithdrawalvarname")
        else:
            self.var.indWithdrawalVar = "industryGrossDemand"
        if "industryConsuptionvarname" in binding:
            self.var.indConsumptionVar = cbinding("industryConsuptionvarname")
        else:
            self.var.indConsumptionVar = "industryNettoDemand"

    def dynamic(self, wd_date):
        """
        Calculate dynamic industrial water demand for the current time step.
        
        Reads monthly or yearly industrial water demand from NetCDF files and transforms
        units to m/day if necessary. Processes both withdrawal and consumption data,
        applies scaling factors if configured, and calculates industrial water efficiency.
        Filters out small demands below the minimum cell area threshold.
        
        Parameters
        ----------
        wd_date : datetime
            Current simulation date for reading time-dependent data
        """


        if self.var.industryTime == 'monthly':
            new = 'newMonth'
        else:
            new = 'newYear'

        if globals.dateVar['newStart'] or globals.dateVar[new]:

            self.var.industryDemand = readnetcdf2('industryWaterDemandFile', wd_date, self.var.industryTime,
                                                  value=self.var.indWithdrawalVar)
            self.var.pot_industryConsumption = readnetcdf2('industryWaterDemandFile', wd_date,
                                                           self.var.industryTime,
                                                           value=self.var.indConsumptionVar)

            # Allows for user to scale industrial demand and potential consumption through the settings file.
            # Industrial demand and potential consumption will be multiplied by the scaling factor.
            if 'scale_industrial_demand' in binding:
                scale_industrial_demand = loadmap('scale_industrial_demand') + globals.inZero
                self.var.industryDemand = self.var.industryDemand * scale_industrial_demand
                self.var.pot_industryConsumption = self.var.pot_industryConsumption * scale_industrial_demand

            self.var.industryDemand = np.where(self.var.industryDemand > self.var.InvCellArea,
                                               self.var.industryDemand, 0.0)
            self.var.pot_industryConsumption = np.where(self.var.pot_industryConsumption > self.var.InvCellArea,
                                                        self.var.pot_industryConsumption, 0.0)

            # transform from mio m3 per year (or month) to m/day if necessary
            if not self.var.demand_unit:
                if self.var.industryTime == 'monthly':
                    timediv = globals.dateVar['daysInMonth']
                else:
                    timediv = globals.dateVar['daysInYear']
                self.var.industryDemand = self.var.industryDemand * 1000000 * self.var.M3toM / timediv
                self.var.pot_industryConsumption = (self.var.pot_industryConsumption * 1000000 *
                                                    self.var.M3toM / timediv)
            self.var.ind_efficiency = divideValues(self.var.pot_industryConsumption,
                                                   self.var.industryDemand)