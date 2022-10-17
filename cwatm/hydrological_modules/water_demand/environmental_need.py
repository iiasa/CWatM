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
from cwatm.management_modules.data_handling import returnBool, binding, readnetcdf2

class waterdemand_environmental_need:
    """
    WATERDEMAND environment_need

    calculating water demand -
    environmental need based on precalculated maps done before in CWatM

    **Global variables**

    =====================================  ======================================================================  =====
    Variable [self.var]                    Description                                                             Unit 
    =====================================  ======================================================================  =====
    cut_ef_map                             if TRUE calculated maps of environmental flow are clipped to the area   bool 
    use_environflow                                                                                                     
    envFlowm3s                                                                                                          
    M3toM                                  Coefficient to change units                                             --   
    chanLength                             Input, Channel length                                                   m    
    channelAlpha                                                                                                        
    envFlow                                                                                                             
    =====================================  ======================================================================  =====

    **Functions**
    """

    def __init__(self, model):
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initial part of the water demand module - environment

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
        Dynamic part of the water demand module - environment
        read monthly (or yearly) water demand from netcdf and transform (if necessary) to [m/day]

        """
        if self.var.use_environflow:
            if globals.dateVar['newStart'] or globals.dateVar['newMonth']:
                # envflow in [m3/s] -> [m]
                self.var.envFlowm3s = readnetcdf2('EnvironmentalFlowFile', globals.dateVar['currDate'], "month", cut=self.var.cut_ef_map) # in [m3/s]
                self.var.envFlow = self.var.M3toM  * self.var.channelAlpha * self.var.chanLength * self.var.envFlowm3s ** 0.6 # in [m]
        else:
            self.var.envFlow = 0.00001  # 0.01mm