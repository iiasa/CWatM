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

    =====================================  ======================================================================  =====
    Variable [self.var]                    Description                                                             Unit 
    =====================================  ======================================================================  =====
    domesticTime                           Monthly' when domesticTimeMonthly = True, and 'Yearly' otherwise.       str  
    domWithdrawalVar                       Input, domesticWithdrawalvarname, variable name for netCDF              str  
    domConsumptionVar                      Input, domesticConsuptionvarname, variable name for netCDF              str  
    domestic_agent_SW_request_month_m3     map of domestic agent surface water request, in million m3 per month    Mm3  
    domestic_agent_GW_request_month_m3     map of domestic agent groundwater request, in million m3 per month      Mm3  
    InvCellArea                            Inverse of cell area of each simulated mesh                             1/m2 
    M3toM                                  Coefficient to change units                                             --   
    activate_domestic_agents               Input, True if activate_domestic_agents = True                          bool 
    domesticDemand                         Domestic demand                                                         m    
    swAbstractionFraction_domestic         With domestic agents, derived from surface water over total water requ  %    
    demand_unit                                                                                                         
    pot_domesticConsumption                                                                                             
    sectorSourceAbstractionFractions                                                                                    
    swAbstractionFraction_Channel_Domesti  Input, Fraction of Domestic demands to be satisfied with Channel        %    
    swAbstractionFraction_Lift_Domestic    Input, Fraction of Domestic demands to be satisfied with Lift           %    
    swAbstractionFraction_Res_Domestic     Input, Fraction of Domestic demands to be satisfied with Reservoirs     %    
    swAbstractionFraction_Lake_Domestic    Input, Fraction of Domestic demands to be satisfied with Lake           %    
    gwAbstractionFraction_Domestic         Fraction of domestic water demand to be satisfied by groundwater        %    
    dom_efficiency                                                                                                      
    =====================================  ======================================================================  =====

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

        self.var.domestic_agent_SW_request_month_m3 = globals.inZero.copy()
        self.var.domestic_agent_GW_request_month_m3 = globals.inZero.copy()

    def dynamic(self, wd_date):
        """
        Dynamic part of the water demand module - domestic
        read monthly (or yearly) water demand from netcdf and transform (if necessary) to [m/day]

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
                    self.var.domestic_agent_SW_request_month_m3 = loadmap(
                        'domestic_agent_SW_request_month_m3') + globals.inZero.copy()

                if 'domestic_agent_GW_request_month_m3' in binding:
                    self.var.domestic_agent_GW_request_month_m3 = loadmap(
                        'domestic_agent_GW_request_month_m3') + globals.inZero.copy()

                self.var.domesticDemand = self.var.domestic_agent_SW_request_month_m3 + \
                                          self.var.domestic_agent_GW_request_month_m3

                self.var.swAbstractionFraction_domestic = \
                    np.where(self.var.domesticDemand > 0,
                             divideValues(
                                 self.var.domestic_agent_SW_request_month_m3,
                                 self.var.domesticDemand), 0)

                # domesticDemand and domesticConsumption are transformed below from million m3 per month to m/day
                self.var.demand_unit = False
                self.var.domesticDemand /= 1000000

                if 'domestic_agents_fracConsumptionWithdrawal' in binding:
                    self.var.pot_domesticConsumption = self.var.domesticDemand.copy() * loadmap(
                        'domestic_agents_fracConsumptionWithdrawal')
                else:
                    self.var.pot_domesticConsumption = self.var.domesticDemand.copy() * 0.2

                if self.var.sectorSourceAbstractionFractions:
                    self.var.swAbstractionFraction_Channel_Domestic *= self.var.swAbstractionFraction_domestic
                    self.var.swAbstractionFraction_Lift_Domestic *= self.var.swAbstractionFraction_domestic
                    self.var.swAbstractionFraction_Res_Domestic *= self.var.swAbstractionFraction_domestic
                    self.var.swAbstractionFraction_Lake_Domestic *= self.var.swAbstractionFraction_domestic
                    self.var.gwAbstractionFraction_Domestic = 1 - self.var.swAbstractionFraction_domestic
                else:

                    self.var.swAbstractionFraction_Channel_Domestic = self.var.swAbstractionFraction_domestic.copy()
                    self.var.swAbstractionFraction_Lift_Domestic = self.var.swAbstractionFraction_domestic.copy()
                    self.var.swAbstractionFraction_Res_Domestic = self.var.swAbstractionFraction_domestic.copy()
                    self.var.swAbstractionFraction_Lake_Domestic = self.var.swAbstractionFraction_domestic.copy()
                    self.var.gwAbstractionFraction_Domestic = 1 - self.var.swAbstractionFraction_domestic


            else:

                self.var.domesticDemand = readnetcdf2('domesticWaterDemandFile', wd_date, self.var.domesticTime,
                                                      value=self.var.domWithdrawalVar)
                self.var.pot_domesticConsumption = readnetcdf2('domesticWaterDemandFile', wd_date,
                                                               self.var.domesticTime, value=self.var.domConsumptionVar)
                # avoid small values (less than 1 m3):
                self.var.domesticDemand = np.where(self.var.domesticDemand > self.var.InvCellArea,
                                                   self.var.domesticDemand, 0.0)
                self.var.pot_domesticConsumption = np.where(self.var.pot_domesticConsumption > self.var.InvCellArea,
                                                            self.var.pot_domesticConsumption, 0.0)

            self.var.dom_efficiency = divideValues(self.var.pot_domesticConsumption, self.var.domesticDemand)

            # transform from mio m3 per year (or month) to m/day if necessary
            if not self.var.demand_unit:
                if self.var.domesticTime == 'monthly':
                    timediv = globals.dateVar['daysInMonth']
                else:
                    timediv = globals.dateVar['daysInYear']
                self.var.domesticDemand = self.var.domesticDemand * 1000000 * self.var.M3toM / timediv
                self.var.pot_domesticConsumption = self.var.pot_domesticConsumption * 1000000 * self.var.M3toM / timediv
