# -------------------------------------------------------------------------
# Name:        Waterdemand modules
# Purpose: Environmental water requirements module for ecosystem water allocation.
# Calculates minimum flow requirements for maintaining aquatic ecosystem health.
# Supports environmental flow standards and habitat preservation water needs.
#
# Author:      PB, YS, MS, JdB
# Created:     15/07/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules import globals
from cwatm.management_modules.data_handling import returnBool, binding, readnetcdf2

class waterdemand_environmental_need:
    """
    Environmental water requirements module for ecosystem water allocation.
    
    This class calculates minimum flow requirements for maintaining aquatic ecosystem health.
    It supports environmental flow standards and habitat preservation water needs based on
    precalculated maps. The module handles monthly environmental flow data and converts
    flow rates to water depths for hydrological calculations.
    
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
    cut_ef_map                           Flag          if TRUE calculated maps of environmental flow are clipped to the area   bool 
    use_environflow                      Flag          Use calculation of environmental flow                                   bool 
    envFlowm3s                           Array         Amount of environmental flow                                            m3   
    M3toM                                Array         Coefficient to change units                                             --   
    chanLength                           Array         Input, Channel length                                                   m    
    channelAlpha                         Array                                                                                 --   
    envFlow                              Array                                                                                 --   
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize the environmental water need module.
        
        Parameters
        ----------
        model : object
            The CWatM model instance containing variables and methods
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initialize environmental flow parameters and settings.
        
        Sets up environmental flow usage flags, configures whether environmental flow
        maps should be cut to the model domain, and initializes environmental flow
        variables for ecosystem water requirements.
        """
        if "use_environflow" in binding:
            self.var.use_environflow = returnBool('use_environflow')
        else:
            self.var.use_environflow = False
        if self.var.use_environflow:
            self.var.cut_ef_map = returnBool('cut_ef_map')
        else:
            self.var.cut_ef_map = False

    def dynamic(self):
        """
        Calculate dynamic environmental flow requirements for the current time step.
        
        Reads monthly environmental flow data from NetCDF files and transforms flow rates
        from mÂ³/s to water depths in meters. Uses channel geometry parameters to convert
        volumetric flow to equivalent water depth for hydrological calculations.
        Sets minimum environmental flow when environmental flows are disabled.
        """
        if self.var.use_environflow:
            if globals.dateVar['newStart'] or globals.dateVar['newMonth']:
                # envflow in [m3/s] -> [m]
                self.var.envFlowm3s = readnetcdf2('EnvironmentalFlowFile', globals.dateVar['currDate'], "month",
                                                   cut=self.var.cut_ef_map)  # in [m3/s]
                self.var.envFlow = (self.var.M3toM * self.var.channelAlpha * self.var.chanLength *
                                   self.var.envFlowm3s ** 0.6)  # in [m]
        else:
            self.var.envFlow = 0.00001  # 0.01mm