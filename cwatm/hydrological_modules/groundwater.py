# -------------------------------------------------------------------------
# Name:        Groundwater module
# Purpose: Standard groundwater dynamics module using reservoir-based approach.
# Simulates groundwater storage, discharge, and interaction with surface water.
# Handles groundwater abstraction for water demand and baseflow generation.
#
# Author:      PB
#
# Created:     15/07/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


class groundwater(object):
    """
    Groundwater dynamics module.

    This class manages groundwater processes including groundwater flow,
    storage changes, and interactions with surface water systems.

    Attributes
    ----------
    var : object
        Model variables container
    model : object
        CWatM model instance

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    modflow                              Flag          True if modflow_coupling = True in settings file                        bool 
    load_initial                         Flag          Settings initLoad holds initial conditions for variables                bool 
    storGroundwater                      Array         Groundwater storage (non-fossil). This is primarily used when not usin  m    
    specificYield                        Array         groundwater reservoir parameters (if ModFlow is not used) used to comp  m    
    recessionCoeff                       Array         groundwater storage times this coefficient gives baseflow               frac 
    readAvlStorGroundwater               Array         same as storGroundwater but equal to 0 when inferior to a treshold      m    
    loadInit                             Flag          If true initial conditions are loaded                                   bool 
    sum_gwRecharge                       Array         groundwater recharge                                                    m    
    baseflow                             Array         simulated baseflow (= groundwater discharge to river)                   m    
    capillar                             Array         Flow from groundwater to the third CWATM soil layer. Used with MODFLOW  m    
    nonFossilGroundwaterAbs              Array         Non-fossil groundwater abstraction. Used primarily without MODFLOW.     m    
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize the groundwater module.

        Parameters
        ----------
        model : object
            CWatM model instance containing variables and configuration
        """
        self.var = model.var
        self.model = model
    
    def initial(self):
        """
        Initialize groundwater parameters and variables.

        Sets up groundwater model parameters including storage coefficients,
        initial conditions, and configures groundwater-surface water interactions.
        """

        self.var.recessionCoeff = loadmap('recessionCoeff')

        # for CALIBRATION
        self.var.recessionCoeff = 1 / self.var.recessionCoeff * loadmap('recessionCoeff_factor')
        self.var.recessionCoeff = 1 / self.var.recessionCoeff

        self.var.specificYield = loadmap('specificYield')

        # init calculation recession coefficient, speciefic yield, ksatAquifer
        self.var.recessionCoeff = np.maximum(5.e-4, self.var.recessionCoeff)
        self.var.recessionCoeff = np.minimum(1.000, self.var.recessionCoeff)
        self.var.specificYield = np.maximum(0.010, self.var.specificYield)
        self.var.specificYield = np.minimum(1.000, self.var.specificYield)

        # initial conditions
        self.var.storGroundwater = self.var.load_initial('storGroundwater')
        if 'storGroundwater' in binding and not self.var.loadInit:
            self.var.storGroundwater = loadmap('storGroundwater')
        self.var.storGroundwater = np.maximum(0.0, self.var.storGroundwater) + globals.inZero

        # for water demand to have some initial value
        tresholdStorGroundwater = 0.00001  # 0.01 mm
        self.var.readAvlStorGroundwater = np.where(self.var.storGroundwater > tresholdStorGroundwater,
                                                   self.var.storGroundwater - tresholdStorGroundwater, 0.0)

        self.var.nonFossilGroundwaterAbs = globals.inZero

    # --------------------------------------------------------------------------

    def dynamic(self):
        """
        Calculate groundwater dynamics for the current time step.

        Updates groundwater storage, calculates groundwater flow, and manages
        interactions between groundwater and surface water systems.
        """
        """
        Dynamic part of the groundwater module
        Calculate groundwater storage and baseflow
        """

        # update storGoundwater after self.var.nonFossilGroundwaterAbs
        self.var.storGroundwater = np.maximum(0., self.var.storGroundwater - self.var.nonFossilGroundwaterAbs)
        # PS: We assume only local groundwater abstraction can happen (only to satisfy water demand within a cell).
        # unmetDemand (m), satisfied by fossil gwAbstractions (and/or desalinization or other sources)
        # (equal to zero if limitAbstraction = True)

        # get net recharge (percolation-capRise) and update storage:
        self.var.storGroundwater = np.maximum(0., self.var.storGroundwater + self.var.sum_gwRecharge)

        # calculate baseflow and update storage:
        if not (self.var.modflow):
            # Groundwater baseflow from modflow or if modflow is not included calculate baseflow with 
            # linear storage function
            self.var.baseflow = np.maximum(0., np.minimum(self.var.storGroundwater, 
                                                          self.var.recessionCoeff * self.var.storGroundwater))

        self.var.storGroundwater = np.maximum(0., self.var.storGroundwater - self.var.baseflow)
        if self.var.modflow:
            # In the non-MODFLOW version, capillary rise is already dealt with previously be being removed from 
            # groundwater recharge
            self.var.storGroundwater = np.maximum(0, self.var.storGroundwater - self.var.capillar)

        # to avoid small values and to avoid excessive abstractions from dry groundwater
        tresholdStorGroundwater = 0.00001  # 0.01 mm
        self.var.readAvlStorGroundwater = np.where(self.var.storGroundwater > tresholdStorGroundwater, 
                                                   self.var.storGroundwater - tresholdStorGroundwater, 0.0)




