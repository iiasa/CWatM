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
from cwatm.management_modules.data_handling import binding, cbinding, loadmap, divideValues
from cwatm.hydrological_modules.water_demand.sector_demand import sector_time, new_sector_time, read_sector_demand


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
    domWithdrawalVar                     List          Settings domesticWithdrawalvarname: withdrawal variable in the netCDF   str  
    domConsumptionVar                    List          Settings domesticConsuptionvarname: consumption variable in the netCDF  str  
    domestic_agent_SW_request_month_m3   Array         Domestic agents: surface water request per month (static map)           m3   
    domestic_agent_GW_request_month_m3   Array         Domestic agents: groundwater request per month (static map)             m3   
    pot_domesticConsumption              Array         Potential domestic water consumption                                    m    
    M3toM                                Array         Coefficient to change units                                             --   
    domesticTime                         List          'monthly' or 'yearly' (domesticTimeMonthly), always monthly for agents  str  
    activate_domestic_agents             Flag          Input, True if activate_domestic_agents = True                          bool 
    domesticDemand                       Array         Domestic water demand (withdrawal)                                      m    
    swAbstractionFraction_domestic       Array         Domestic agents: surface water share of the request                     frac 
    sectorSourceAbstractionFractions     Array         Sector-,source-abstraction fractions facilitate designating the specif  --   
    swAbstractionFraction_Channel_Domes  Array         Input, Fraction of Domestic demands to be satisfied with Channel        %    
    swAbstractionFraction_Lift_Domestic  Array         Input, Fraction of Domestic demands to be satisfied with Lift           %    
    swAbstractionFraction_Res_Domestic   Array         Input, Fraction of Domestic demands to be satisfied with Reservoirs     %    
    swAbstractionFraction_Lake_Domestic  Array         Input, Fraction of Domestic demands to be satisfied with Lake           %    
    gwAbstractionFraction_Domestic       Array         Fraction of domestic water demand to be satisfied by groundwater        %    
    dom_efficiency                       Array         Domestic consumption / withdrawal, at most 1                            --   
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

        self.var.domesticTime = sector_time('domesticTimeMonthly')
        # domestic agents: the request maps are m3 per month -> always monthly
        if self.var.activate_domestic_agents:
            self.var.domesticTime = 'monthly'

        if "domesticWithdrawalvarname" in binding:
            self.var.domWithdrawalVar = cbinding("domesticWithdrawalvarname")
        else:
            self.var.domWithdrawalVar = "domesticGrossDemand"
        if "domesticConsuptionvarname" in binding:
            self.var.domConsumptionVar = cbinding("domesticConsuptionvarname")
        else:
            self.var.domConsumptionVar = "domesticNettoDemand"

        # Domestic agents have monthly surface and groundwater requests, at CWatM cellular resolution.
        # domestic_agent_SW_request_month_m3 and domestic_agent_GW_request_month_m3 are static maps with the
        # monthly water demand in cubic metres; domestic_agents_fracConsumptionWithdrawal is a static map (or number)
        # with the ratio of consumption to withdrawal (default 0.2).
        # Loaded once here (before 2026-11 again every month)
        self.var.domestic_agent_SW_request_month_m3 = globals.inZero.copy()
        self.var.domestic_agent_GW_request_month_m3 = globals.inZero.copy()
        self.agentFracConsumption = 0.2
        if self.var.activate_domestic_agents:
            if 'domestic_agent_SW_request_month_m3' in binding:
                self.var.domestic_agent_SW_request_month_m3 = (
                    loadmap('domestic_agent_SW_request_month_m3') + globals.inZero)
            if 'domestic_agent_GW_request_month_m3' in binding:
                self.var.domestic_agent_GW_request_month_m3 = (
                    loadmap('domestic_agent_GW_request_month_m3') + globals.inZero)
            if 'domestic_agents_fracConsumptionWithdrawal' in binding:
                self.agentFracConsumption = loadmap('domestic_agents_fracConsumptionWithdrawal')

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

        if new_sector_time(self.var.domesticTime):

            if self.var.activate_domestic_agents:
                # agent maps loaded in initial; m3 per month
                self.var.domesticDemand = (self.var.domestic_agent_SW_request_month_m3 +
                                           self.var.domestic_agent_GW_request_month_m3)

                # divideValues gives 0 where there is no request
                self.var.swAbstractionFraction_domestic = divideValues(self.var.domestic_agent_SW_request_month_m3,
                                                                       self.var.domesticDemand)

                self.var.pot_domesticConsumption = self.var.domesticDemand * self.agentFracConsumption
                # consumption cannot be more than withdrawal
                self.var.dom_efficiency = np.minimum(1., divideValues(self.var.pot_domesticConsumption,
                                                                      self.var.domesticDemand))

                # m3 per month -> m/day
                # (before 2026-11 demand_unit was set to False here - for industry and livestock too)
                self.var.domesticDemand = self.var.domesticDemand * self.var.M3toM / globals.dateVar['daysInMonth']
                self.var.pot_domesticConsumption = (self.var.pot_domesticConsumption * self.var.M3toM /
                                                    globals.dateVar['daysInMonth'])

                if self.var.sectorSourceAbstractionFractions:
                    # source maps (water_demand.initial) times the surface water share of the agents of this month -
                    # before 2026-11 "*=": the fractions shrank every month (map * f^n) and a restart began again
                    # with the maps (stop and go test Bhima)
                    names = ['Channel', 'Lift', 'Res', 'Lake']
                    if not hasattr(self, 'swFractionMaps'):
                        self.swFractionMaps = {n: np.copy(getattr(self.var, 'swAbstractionFraction_' + n + '_Domestic'))
                                               for n in names}
                    for n in names:
                        setattr(self.var, 'swAbstractionFraction_' + n + '_Domestic',
                                self.swFractionMaps[n] * self.var.swAbstractionFraction_domestic)
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
                # read, scale (scale_domestic_demand), m/day, values < 1 m3/day -> 0, efficiency (sector_demand.py)
                self.var.domesticDemand, self.var.pot_domesticConsumption, self.var.dom_efficiency = \
                    read_sector_demand(self.var, 'domesticWaterDemandFile', wd_date, self.var.domesticTime,
                                       self.var.domWithdrawalVar, self.var.domConsumptionVar, 'scale_domestic_demand')
