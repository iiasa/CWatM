# -------------------------------------------------------------------------
# Name:        Environmental water need
# Purpose: Environmental water requirements module for ecosystem water allocation.
# Calculates minimum flow requirements for maintaining aquatic ecosystem health.
# Supports environmental flow standards and habitat preservation water needs.
#
# Author:      PB, YS, MS, JdB
# Created:     15/07/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import numpy as np
from cwatm.management_modules import globals
from cwatm.management_modules.data_handling import returnBool, checkOption, binding, option, readnetcdf2

# environmental flow [m] without environmental flow maps: 0.01 mm stays in the channel
ENVFLOW_OFF = 0.00001


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
    envFlowm3s                           Array         Environmental flow discharge of this month                              m3/s 
    M3toM                                Array         Coefficient to change units                                             --   
    chanLength                           Array         Input, Channel length                                                   m    
    channelAlpha                         Array         Alpha of the kinematic wave of the routing, with calibration            --   
    beta                                 Array         Beta of the kinematic wave                                              --   
    envFlow                              Array         Channel storage at the environmental flow, kept in the channel          m    
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
        # use_environflow can be in the section of the module (binding) or in [OPTIONS] (option)
        if "use_environflow" in binding:
            self.var.use_environflow = returnBool('use_environflow')
        elif "use_environflow" in option:
            self.var.use_environflow = checkOption('use_environflow')
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
        from m3/s to water depths in meters: the channel storage of the kinematic wave at this
        discharge (alpha * length * Q ** beta, as in the routing), divided by the cell area.
        Sets minimum environmental flow when environmental flows are disabled.
        """
        if self.var.use_environflow:
            if globals.dateVar['newStart'] or globals.dateVar['newMonth']:
                # envflow in [m3/s] -> [m]: channel storage at this discharge, same formula as the routing
                # negative values would give NaN in Q ** beta -> no abstraction from this cell: they become 0
                # (no environmental flow). NaN inside the mask already stops readnetcdf2 with Error 106
                self.var.envFlowm3s = np.maximum(
                    readnetcdf2('EnvironmentalFlowFile', globals.dateVar['currDate'], "month",
                                cut=self.var.cut_ef_map), 0.)  # in [m3/s]
                self.var.envFlow = (self.var.M3toM * self.var.channelAlpha * self.var.chanLength *
                                   self.var.envFlowm3s ** self.var.beta)  # in [m]
        else:
            self.var.envFlow = ENVFLOW_OFF