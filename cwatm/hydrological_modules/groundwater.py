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
    load_initial                         Flag          Settings initLoad holds initial conditions for variables                bool 
    storGroundwater                      Array         Groundwater storage (non-fossil). This is primarily used when not usin  m    
    specificYield                        Array         Groundwater reservoir parameters (if ModFlow is not used) used to comp  --   
    recessionCoeff                       Array         groundwater storage times this coefficient gives baseflow               1/day
    readAvlStorGroundwater               Array         storGroundwater minus a threshold of 0.01 mm, at least 0                m    
    loadInit                             Flag          If true initial conditions are loaded                                   bool 
    sum_gwRecharge                       Array         groundwater recharge                                                    m    
    baseflow                             Array         simulated baseflow (= groundwater discharge to river)                   m    
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

        # for CALIBRATION: recessionCoeff_factor > 1 -> slower baseflow
        # (= recessionCoeff / factor, written this way to keep results bit-identical to earlier versions)
        self.var.recessionCoeff = 1 / (1 / loadmap('recessionCoeff') * loadmap('recessionCoeff_factor'))

        self.var.specificYield = loadmap('specificYield')

        # limits of recession coefficient and specific yield
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
        self.readavailable()

        # copy: never share (and change) globals.inZero
        self.var.nonFossilGroundwaterAbs = globals.inZero.copy()

    def readavailable(self):
        """
        Groundwater storage available for abstraction.

        Storage minus a threshold of 0.01 mm, to avoid small values and excessive abstractions
        from dry groundwater.
        """
        tresholdStorGroundwater = 0.00001  # 0.01 mm
        self.var.readAvlStorGroundwater = np.maximum(0., self.var.storGroundwater - tresholdStorGroundwater)

    # --------------------------------------------------------------------------

    def dynamic(self):
        """
        Calculate groundwater storage and baseflow for the current time step.

        Only used without MODFLOW (with MODFLOW groundwater_modflow is called instead).
        Groundwater storage is updated by abstraction, net recharge (percolation - capillary rise,
        can be negative) and baseflow from a linear reservoir.
        """

        # update storGroundwater after self.var.nonFossilGroundwaterAbs
        # (abstraction is limited by readAvlStorGroundwater in water demand)
        self.var.storGroundwater = np.maximum(0., self.var.storGroundwater - self.var.nonFossilGroundwaterAbs)
        # PS: We assume only local groundwater abstraction can happen (only to satisfy water demand within a cell).
        # unmetDemand (m), satisfied by fossil gwAbstractions (and/or desalinization or other sources)
        # (equal to zero if limitAbstraction = True)

        # get net recharge (percolation - capRise) and update storage:
        # capillary rise in soil is limited by the storage left after abstraction -> the maximum is only a safeguard
        self.var.storGroundwater = np.maximum(0., self.var.storGroundwater + self.var.sum_gwRecharge)

        # baseflow with linear storage function (0 < recessionCoeff <= 1 -> baseflow <= storGroundwater)
        self.var.baseflow = self.var.recessionCoeff * self.var.storGroundwater
        self.var.storGroundwater = self.var.storGroundwater - self.var.baseflow

        self.readavailable()


