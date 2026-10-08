# -------------------------------------------------------------------------
# Name:        Interception module
# Purpose: Rainfall interception module for canopy and surface interception processes.
# Calculates water capture by vegetation canopies before reaching soil surface.
# Manages interception storage capacity and evaporation from intercepted water.
#
# Author:      PB
# Created:     01/08/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


class interception(object):
    """
    Interception module for calculating canopy interception processes.
    
    Handles the interception of precipitation by vegetation canopies and subsequent
    evaporation of intercepted water for different land cover types. Calculates
    throughfall, interception storage, and evaporation from intercepted water.
    
    Attributes
    ----------
    var : object
        Reference to model variables object containing state variables
    model : object
        Reference to the main CWatM model instance

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    snowEvap                             Array         total evaporation from snow for a snow layers                           m    
    iceEvap                              Array         Evaporation from ice (sublimation)                                      m    
    interceptCap                         Array         interception capacity of vegetation                                     m    
    potTranspiration                     Array         Potential transpiration (after removing of evaporation)                 m    
    interceptEvap                        Array         simulated evaporation from water intercepted by vegetation              m    
    minInterceptCap                      Array         Maximum interception read from file for forest and grassland land cove  m    
    interceptStor                        Array         simulated vegetation interception storage                               m    
    twothird                             Number        2025-03-02 00:00:00                                                     --   
    EWRef                                Array         potential evaporation rate from water surface                           m    
    availWaterInfiltration               Array         quantity of water reaching the soil after interception, more snowmelt   m    
    SnowMelt                             Array         total snow melt from all layers                                         m    
    IceMelt                              Array         Ice melt (not really ice but an additional snow melt in summer)         m    
    Rain                                 Array         Precipitation less snow                                                 m    
    actualET                             Array         simulated evapotranspiration from soil, flooded area and vegetation     m    
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize interception module.
        
        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.var = model.var
        self.model = model

    # noinspection PyTypeChecker
    def dynamic(self, coverType, No):
        """
        Calculate interception processes for a specific land cover type.
        
        Computes throughfall, interception storage, and evaporation from intercepted
        water based on precipitation, interception capacity, and potential transpiration.
        Updates state variables for water available for infiltration and actual evapotranspiration.
        
        Parameters
        ----------
        coverType : str
            Land cover type identifier (e.g., 'forest', 'grassland', 'irrPaddy', 
            'irrNonPaddy', 'sealed')
        No : int
            Index number of the land cover type in model arrays
            
        Notes
        -----
        The method handles different interception processes based on land cover type:
        - Forest/grassland: Uses seasonal interception capacity with 2/3 power law
        - Irrigated areas: Uses minimum interception capacity with 2/3 power law
        - Sealed surfaces: Uses reference evapotranspiration for interception evaporation
        """
        """
        if coverType in ['forest','grassland']:
            ## interceptCap Maximum interception read from file for forest and grassland land cover
            # for specific days of the year - repeated every year
            if dateVar['newStart'] or dateVar['new10day']:  # check if first day  of the year
                self.var.interceptCap[No]  = readnetcdf2(coverType + '_interceptCapNC', dateVar['10day'], "10day")
                self.var.interceptCap[No] = np.maximum(self.var.interceptCap[No], self.var.minInterceptCap[No])
        else:
            self.var.interceptCap[No] = self.var.minInterceptCap[No] 
        """

        # Rain instead Pr, because snow is substracted later
        # assuming that all interception storage is used the other time step
        if coverType in ['forest', 'grassland']:
            throughfall = np.maximum(0.0, self.var.Rain + self.var.interceptStor[No] - 
                                     self.var.interceptCap[No, dateVar['30day'], :])
        else:
            throughfall = np.maximum(0.0, self.var.Rain + self.var.interceptStor[No] - 
                                     self.var.minInterceptCap[No])
        # update interception storage after throughfall
        self.var.interceptStor[No] = self.var.interceptStor[No] + self.var.Rain - throughfall

        # availWaterInfiltration Available water for infiltration: throughfall + snow melt
        self.var.availWaterInfiltration[No] = np.maximum(0.0, throughfall + self.var.SnowMelt + self.var.IceMelt)

        if coverType in ['forest', 'grassland']:
            mult = (divideValues(self.var.interceptStor[No], self.var.interceptCap[No, dateVar['30day'], :]) ** 
                    self.var.twothird)
            # interceptEvap evaporation from intercepted water (based on potTranspiration)
            self.var.interceptEvap[No] = np.minimum(self.var.interceptStor[No], self.var.potTranspiration[No] * mult)
        if coverType in ['irrPaddy', 'irrNonPaddy']:
            mult = (divideValues(self.var.interceptStor[No], self.var.minInterceptCap[No] + globals.inZero) ** 
                    self.var.twothird)
            # interceptEvap evaporation from intercepted water (based on potTranspiration)
            self.var.interceptEvap[No] = np.minimum(self.var.interceptStor[No], self.var.potTranspiration[No] * mult)
        if coverType in ['sealed']:
            self.var.interceptEvap[No] = np.maximum(np.minimum(self.var.interceptStor[No], self.var.EWRef), 
                                                    globals.inZero)


        # update interception storage and potTranspiration
        self.var.interceptStor[No] = self.var.interceptStor[No] - self.var.interceptEvap[No]
        self.var.potTranspiration[No] = np.maximum(0, self.var.potTranspiration[No] - self.var.interceptEvap[No])

        # update actual evaporation (after interceptEvap)
        # interceptEvap is the first flux in ET, soil evapo and transpiration are added later
        self.var.actualET[No] = self.var.interceptEvap[No] + self.var.snowEvap + self.var.iceEvap



