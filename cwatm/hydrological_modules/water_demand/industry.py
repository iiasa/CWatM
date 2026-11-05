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

from cwatm.management_modules.data_handling import binding, cbinding
from cwatm.hydrological_modules.water_demand.sector_demand import sector_time, new_sector_time, read_sector_demand

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
    industryTime                         List          'monthly' or 'yearly' (settings industryTimeMonthly)                    str  
    indWithdrawalVar                     List          Settings industryWithdrawalvarname: withdrawal variable in the netCDF   str  
    indConsumptionVar                    List          Settings industryConsuptionvarname: consumption variable in the netCDF  str  
    pot_industryConsumption              Array         Potential industry water consumption                                    m    
    industryDemand                       Array         Industry water demand (withdrawal)                                      m    
    ind_efficiency                       Array         Industry consumption / withdrawal, at most 1                            --   
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
        self.var.industryTime = sector_time('industryTimeMonthly')

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


        if new_sector_time(self.var.industryTime):
            # read, scale (scale_industrial_demand), m/day, values < 1 m3/day -> 0, efficiency (sector_demand.py)
            self.var.industryDemand, self.var.pot_industryConsumption, self.var.ind_efficiency = read_sector_demand(
                self.var, 'industryWaterDemandFile', wd_date, self.var.industryTime,
                self.var.indWithdrawalVar, self.var.indConsumptionVar, 'scale_industrial_demand')