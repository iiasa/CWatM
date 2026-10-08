# -------------------------------------------------------------------------
# Name:        Waterdemand modules
# Purpose: Domestic water demand module for household and municipal water requirements.
# Calculates residential water consumption based on population and per-capita use rates.
# Supports urban water demand modeling with temporal and spatial variations.
#
# Authors:      PB, YS, MS, JdB, DF
# Created:     15/07/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules import globals
import numpy as np
from cwatm.management_modules.data_handling import (returnBool, binding, cbinding, loadmap, readnetcdf2,
                                                     divideValues)


class waterdemand_domestic:
    """
    Domestic water demand module for household and municipal water requirements.
    
    This class calculates residential water consumption based on population and per-capita
    use rates. It supports urban water demand modeling with temporal and spatial variations.
    The module handles both agent-based and traditional demand calculations, supporting
    surface water and groundwater abstraction fractions.
    
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
    domWithdrawalVar                     List          Input, domesticWithdrawalvarname, variable name for netCDF              str  
    domConsumptionVar                    List          Input, domesticConsuptionvarname, variable name for netCDF              str  
    domestic_agent_SW_request_month_m3   Array         map of domestic agent surface water request, in million m3 per month    Mm3  
    domestic_agent_GW_request_month_m3   Array         map of domestic agent groundwater request, in million m3 per month      Mm3  
    pot_domesticConsumption              Array                                                                                 --   
    M3toM                                Array         Coefficient to change units                                             --   
    domesticTime                         List          Monthly' when domesticTimeMonthly = True, and 'Yearly' otherwise.       str  
    InvCellArea                          Array         Inverse of cell area of each simulated mesh                             1/m2 
    activate_domestic_agents             Flag          Input, True if activate_domestic_agents = True                          bool 
    domesticDemand                       Array         Domestic demand                                                         m    
    swAbstractionFraction_domestic       Array         With domestic agents, derived from surface water over total water requ  %    
    demand_unit                          Flag                                                                                  --   
    sectorSourceAbstractionFractions     Array                                                                                 --   
    swAbstractionFraction_Channel_Domes  Array         Input, Fraction of Domestic demands to be satisfied with Channel        %    
    swAbstractionFraction_Lift_Domestic  Array         Input, Fraction of Domestic demands to be satisfied with Lift           %    
    swAbstractionFraction_Res_Domestic   Array         Input, Fraction of Domestic demands to be satisfied with Reservoirs     %    
    swAbstractionFraction_Lake_Domestic  Array         Input, Fraction of Domestic demands to be satisfied with Lake           %    
    gwAbstractionFraction_Domestic       Array         Fraction of domestic water demand to be satisfied by groundwater        %    
    dom_efficiency                       Array                                                                                 --   
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize the domestic water demand module.
        
        Parameters
        ----------
        model : object
            The CWatM model instance containing variables and methods
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initialize domestic water demand parameters and variables.
        
        Sets up time resolution (monthly/yearly), variable names for withdrawal and consumption,
        agent-based domestic demand parameters, and abstraction fractions for different water
        sources (surface water, groundwater, channels, reservoirs, lakes).
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

        self.var.domestic_agent_SW_request_month_m3 = globals.inZero.copy()
        self.var.domestic_agent_GW_request_month_m3 = globals.inZero.copy()

    def dynamic(self, wd_date):
        """
        Calculate dynamic domestic water demand for the current time step.
        
        Reads monthly or yearly water demand from NetCDF files and transforms units to m/day
        if necessary. Handles both agent-based domestic demand (with predefined monthly requests)
        and traditional demand calculation from input files. Applies scaling factors and
        calculates abstraction fractions for different water sources.
        
        Parameters
        ----------
        wd_date : datetime
            Current simulation date for reading time-dependent data
        """

        if self.var.domesticTime == 'monthly':
            new = 'newMonth'
        else:
            new = 'newYear'

        if globals.dateVar['newStart'] or globals.dateVar[new]:

            if self.var.activate_domestic_agents:

                # Domestic agents have monthly surface and groundwater requests, at CWatM cellular resolution.
                #
                # The settings sw_agentsDomestic_month_m3, and gw_agentsDomestic_month_m3 are static maps
                #  with the monthly water demand in cubic metres at CWatM resolution.
                #
                # The setting domestic_agents_fracConsumptionWithdrawal is a static map
                #  with the ratio of consumption to withdrawal for domestic agents.

                if 'domestic_agent_SW_request_month_m3' in binding:
                    self.var.domestic_agent_SW_request_month_m3 = (
                        loadmap('domestic_agent_SW_request_month_m3') + globals.inZero.copy())

                if 'domestic_agent_GW_request_month_m3' in binding:
                    self.var.domestic_agent_GW_request_month_m3 = (
                        loadmap('domestic_agent_GW_request_month_m3') + globals.inZero.copy())

                self.var.domesticDemand = (self.var.domestic_agent_SW_request_month_m3 +
                                           self.var.domestic_agent_GW_request_month_m3)

                self.var.swAbstractionFraction_domestic = np.where(
                    self.var.domesticDemand > 0,
                    divideValues(self.var.domestic_agent_SW_request_month_m3,
                                 self.var.domesticDemand), 0)

                # domesticDemand and domesticConsumption are transformed below from million m3 per month to m/day
                self.var.demand_unit = False
                self.var.domesticDemand /= 1000000

                if 'domestic_agents_fracConsumptionWithdrawal' in binding:
                    self.var.pot_domesticConsumption = (
                        self.var.domesticDemand.copy() *
                        loadmap('domestic_agents_fracConsumptionWithdrawal'))
                else:
                    self.var.pot_domesticConsumption = self.var.domesticDemand.copy() * 0.2

                if self.var.sectorSourceAbstractionFractions:
                    self.var.swAbstractionFraction_Channel_Domestic *= self.var.swAbstractionFraction_domestic
                    self.var.swAbstractionFraction_Lift_Domestic *= self.var.swAbstractionFraction_domestic
                    self.var.swAbstractionFraction_Res_Domestic *= self.var.swAbstractionFraction_domestic
                    self.var.swAbstractionFraction_Lake_Domestic *= self.var.swAbstractionFraction_domestic
                    self.var.gwAbstractionFraction_Domestic = 1 - self.var.swAbstractionFraction_domestic
                else:
                    self.var.swAbstractionFraction_Channel_Domestic = (
                        self.var.swAbstractionFraction_domestic.copy())
                    self.var.swAbstractionFraction_Lift_Domestic = (
                        self.var.swAbstractionFraction_domestic.copy())
                    self.var.swAbstractionFraction_Res_Domestic = (
                        self.var.swAbstractionFraction_domestic.copy())
                    self.var.swAbstractionFraction_Lake_Domestic = (
                        self.var.swAbstractionFraction_domestic.copy())
                    self.var.gwAbstractionFraction_Domestic = 1 - self.var.swAbstractionFraction_domestic


            else:
                self.var.domesticDemand = readnetcdf2('domesticWaterDemandFile', wd_date,
                                                      self.var.domesticTime,
                                                      value=self.var.domWithdrawalVar)
                self.var.pot_domesticConsumption = readnetcdf2('domesticWaterDemandFile', wd_date,
                                                               self.var.domesticTime,
                                                               value=self.var.domConsumptionVar)

                # Allows for user to scale domestic demand and potential consumption through the settings file.
                # Domestic demand and potential consumption will be multiplied by the scaling factor.
                if 'scale_domestic_demand' in binding:
                    scale_domestic_demand = loadmap('scale_domestic_demand') + globals.inZero
                    self.var.domesticDemand = self.var.domesticDemand * scale_domestic_demand
                    self.var.pot_domesticConsumption = (
                        self.var.pot_domesticConsumption * scale_domestic_demand)

                # avoid small values (less than 1 m3):
                self.var.domesticDemand = np.where(self.var.domesticDemand > self.var.InvCellArea,
                                                   self.var.domesticDemand, 0.0)
                self.var.pot_domesticConsumption = np.where(
                    self.var.pot_domesticConsumption > self.var.InvCellArea,
                    self.var.pot_domesticConsumption, 0.0)

            self.var.dom_efficiency = divideValues(self.var.pot_domesticConsumption,
                                                   self.var.domesticDemand)

            # transform from mio m3 per year (or month) to m/day if necessary
            if not self.var.demand_unit:
                if self.var.domesticTime == 'monthly':
                    timediv = globals.dateVar['daysInMonth']
                else:
                    timediv = globals.dateVar['daysInYear']
                self.var.domesticDemand = self.var.domesticDemand * 1000000 * self.var.M3toM / timediv
                self.var.pot_domesticConsumption = (self.var.pot_domesticConsumption * 1000000 *
                                                    self.var.M3toM / timediv)
