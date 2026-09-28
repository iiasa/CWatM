# -------------------------------------------------------------------------
# Name:        Frost module
# Purpose: Frost processes module 
# Calculates if the soil is frozen 
#
# Author:      PB, MS, SH
# Created:     13/07/2016
# Snow albedo: 15/09/2026
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


import importlib


class frost(object):
    """
    Frost processes module 
    Frost index calculations based on: Molnau and Bissel (1983)
    If the soil is frozen -> no soil processes -> surface runoff

    
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
    adv_frost                            Flag          if this use, Kfrost and maxFrost is used                                --   
    maxFrostIndex                        Array         maximum frostindex, frostindex over max causes unusuaL floods in sprin  --   
    Kfrost                               Array         Snow depth reduction coefficient, (HH, p. 7.28)                         m-1  
    Afrost                               Array         Daily decay coefficient, (Handbook of Hydrology, p. 7.28)               --   
    FrostIndexThreshold                  Array         Degree Days Frost Threshold (stops infiltration, percolation and capil  --   
    FrostIndex                           Array         FrostIndex - Molnau and Bissel (1983), A Continuous Frozen Ground Inde  --   
    FrostDay                             Array         frost index in soil [degree days] based on Molnau and Bissel (1983, A   --   

    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize frost module.
        
        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initialize Frost module parameters and elevation zones.
        
       
        Notes
        -----
        Key initialization components:
        - Frost index parameters for soil freezing calculations
        """

        # ---------------------------------------------------------------------------------
        # Initial part of frost index

        self.var.adv_frost = False
        if 'Advanced_FrostIndex' in binding:
            self.var.adv_frost = returnBool('Advanced_FrostIndex')
        # Kfrost and maxFrostIndex only used with Advanced_FrostIndex (otherwise Kfrost = 0.08/0.5 and maxFrostIndex = 1000 in dynamic)
        if self.var.adv_frost:
            self.var.maxFrostIndex = loadmap('maxFrostIndex')
            self.var.Kfrost = loadmap('Kfrost')

        self.var.Afrost = loadmap('Afrost')
        self.var.FrostIndexThreshold = loadmap('FrostIndexThreshold')
        self.var.SnowWaterEquivalent = loadmap('SnowWaterEquivalent')

        self.var.FrostIndex = self.var.load_initial('FrostIndex')


    # --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Calculate snow and frost processes for current time step.
        
        
        Notes
        -----
        - Frost index update based on air temperature and snow cover
        
        References
        ----------
        Frost index calculations based on:
        Molnau and Bissel (1983) A Continuous Frozen Ground Index for Flood 
        Forecasting. In: Maidment, Handbook of Hydrology, p. 7.28, 7.55

        """

        # ---------------------------------------------------------------------------------
        # Dynamic part of frost index
        if self.var.adv_frost:
            Kfrost = self.var.Kfrost
        else:
            Kfrost = np.where(self.var.Tavg < 0, 0.08, 0.5)
            self.var.maxFrostIndex = 1000.

        # self.var.Kfrost = np.where(self.var.Tavg < 0, 0.08, 0.5)
        FrostIndexChangeRate = -(1 - self.var.Afrost) * self.var.FrostIndex - self.var.Tavg * \
            np.exp(-0.4 * 100 * Kfrost * self.var.SnowCover / self.var.SnowWaterEquivalent)
        # Rate of change of frost index (expressed as rate, [degree days/day])
        self.var.FrostIndex = np.maximum(self.var.FrostIndex + FrostIndexChangeRate * self.var.DtDay, 0)
        self.var.FrostIndex = np.where(self.var.FrostIndex > self.var.maxFrostIndex, self.var.maxFrostIndex, self.var.FrostIndex)
        self.var.FrostDay = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, True, False)
        # frost index in soil [degree days] based on Molnau and Bissel (1983, A Continuous Frozen Ground Index for Flood
        # Forecasting. In: Maidment, Handbook of Hydrology, p. 7.28, 7.55)
        # if Tavg is above zero, FrostIndex will stay 0
        # if Tavg is negative, FrostIndex will increase with 1 per degree C per day
        # Exponent of 0.04 (instead of 0.4 in HoH): conversion [cm] to [mm]!  -> from cm to m HERE -> 100 * 0.4
        # maximum snowlayer = 1.0 m
        # Division by SnowDensity because SnowDepth is expressed as equivalent water depth(always less than depth of snow pack)
        # SnowWaterEquivalent taken as 0.45
        # Afrost, (daily decay coefficient) is taken as 0.97 (Handbook of Hydrology, p. 7.28)
        # Kfrost, (snow depth reduction coefficient) is taken as 0.57 [1/cm], (HH, p. 7.28) -> from Molnau taken as 0.5 for t> 0 and 0.08 for T<0


