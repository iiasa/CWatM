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

from cwatm.management_modules import globals
from cwatm.management_modules.data_handling import returnBool, binding, cbinding
from cwatm.hydrological_modules.water_demand.sector_demand import sector_time, new_sector_time, read_sector_demand

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
    livestockTime                        List          'monthly' or 'yearly' (settings livestockTimeMonthly)                   str  
    livVar                               List          Settings livestockvarname: variable in livestockWaterDemandFile         str  
    uselivestock                         Flag          True if uselivestock=True in Settings, False otherwise                  bool 
    livestockDemand                      Array         Livestock water demand (withdrawal)                                     m    
    pot_livestockConsumption             Array         Potential livestock water consumption (= livestock demand)              m    
    liv_efficiency                       Number        Livestock consumption / withdrawal (= 1)                                --   
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

        self.var.livestockTime = sector_time('livestockTimeMonthly')

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
            if new_sector_time(self.var.livestockTime):
                # read, m/day, values < 1 m3/day -> 0 (sector_demand.py); consumption = withdrawal, efficiency 1
                self.var.livestockDemand, self.var.pot_livestockConsumption, self.var.liv_efficiency = \
                    read_sector_demand(self.var, 'livestockWaterDemandFile', wd_date, self.var.livestockTime,
                                       self.var.livVar)
        else:
            # maps (before 2026-11 the scalar 0)
            self.var.livestockDemand = globals.inZero.copy()
            self.var.pot_livestockConsumption = globals.inZero.copy()
            self.var.liv_efficiency = 1.