# -------------------------------------------------------------------------
# Name:        Capillar Rise module
# Purpose: Capillary rise calculation module for groundwater-surface water interaction.
# Determines cell fractions influenced by capillary rise based on groundwater depth.
# Connects groundwater processes with soil moisture through capillary action.
#
# Author:      PB
# Created:     20/07/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


class capillarRise(object):
    """
    Capillary rise module for groundwater-surface interaction.

    This class calculates the cell fraction influenced by capillary rise based on
    groundwater depth and relative elevation within each grid cell. It determines
    areas where groundwater can reach the surface through capillary action.

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
    capRiseFrac                          Array         fraction of a grid cell where capillar rise may happen                  --   
    capRiseOn                            Flag          True if CapillarRise = True and modflow_coupling = False                bool 
    capRisePct                           List          percentiles of the relative elevation dzRel                             --   
    capRiseSlope                         List          capillar rise fraction per m elevation between two dzRel percentiles    1/m  
    modflow                             Flag          True if modflow_coupling = True in settings file                        bool  
    storGroundwater                      Array         Groundwater storage (non-fossil). This is primarily used when not usin  m    
    specificYield                        Array         Groundwater reservoir parameters (if ModFlow is not used) used to comp  m    
    maxGWCapRise                         Array         influence of capillary rise above groundwater level                     m    
    dzRel                                Array         relative elevation in a gridcell by fraction of area                    m    
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize the capillary rise module.

        Parameters
        ----------
        model : object
            CWatM model instance containing variables and configuration
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initialize the capillary rise module.

        Loads the relative elevation dzRel (always, also used by the snow modules)
        and precomputes the static slope of the capillary rise fraction per m elevation
        between two neighbouring percentiles of dzRel. Must be called before the snow module initial.
        """

        # maps of relative elevation above flood plains -> used in capillar rise and snow
        #            0             1           2              3           4             5          6           7
        #             8          9             10           11          12
        dzRel = ['dzRel0000','dzRel0001', 'dzRel0005', 'dzRel0010', 'dzRel0020', 'dzRel0030', 'dzRel0040', 'dzRel0050',
                 'dzRel0060', 'dzRel0070', 'dzRel0080', 'dzRel0090', 'dzRel0100']
        self.var.dzRel = []
        for i, item in enumerate(dzRel):
            self.var.dzRel.append(readnetcdfWithoutTime(cbinding('relativeElevation'), item, i))

        self.var.capRiseOn = checkOption('CapillarRise') and not self.var.modflow
        if self.var.capRiseOn:
            # dzRel:       0     1     2     3     4     5     6     7     8     9    10    11    12
            self.var.capRisePct = [0.0, 0.01, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
            # capRiseSlope[i-1]: fraction per m between dzRel[i-1] and dzRel[i]
            self.var.capRiseSlope = []
            for i in range(1, 13):
                self.var.capRiseSlope.append((self.var.capRisePct[i] - self.var.capRisePct[i-1]) /
                                             np.maximum(1e-3, self.var.dzRel[i] - self.var.dzRel[i-1]))

    def dynamic(self):
        """
        Calculate capillary rise dynamics for the current time step.

        Computes the cell fraction influenced by capillary rise based on the
        approximate height of groundwater and relative elevation within each grid cell.
        This determines areas where groundwater contributes to surface processes
        through capillary action.
        """

        if self.var.capRiseOn:

            # approximate height of groundwater table and corresponding reach of cell under influence of capillary rise
            dzGroundwater = self.var.storGroundwater / self.var.specificYield + self.var.maxGWCapRise
            # linear interpolation of the area fraction between the percentiles of dzRel
            CRFRAC = 1.0 - (self.var.dzRel[12] - dzGroundwater) * self.var.capRiseSlope[11]
            for i in range(11, 0, -1):
                h = self.var.capRisePct[i] - (self.var.dzRel[i] - dzGroundwater) * self.var.capRiseSlope[i-1]
                CRFRAC = np.where(dzGroundwater < self.var.dzRel[i], h, CRFRAC)

            self.var.capRiseFrac = np.maximum(0.0, np.minimum(1.0, CRFRAC))
        else:
            self.var.capRiseFrac = 0.
