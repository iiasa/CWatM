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
    modflow_seepage                      Flag          Seepage scheme with MODFLOW: modflow_seepage in settings, default True  bool 
    seepageOn                            Flag          True if modflow_coupling = True and modflow_seepage = True              bool 
    saturatedFrac                        Array         Share of the cell with the water table at the surface (seepage scheme)  --   
    dzRelMean                            Array         Area mean of the relative elevation dzRel (seepage scheme)              m    
    modflow_cover                        Array         Share of the CWatM cell covered by active ModFlow cells                 --   
    depth_to_water                       Array         Topography (topo_modflow) minus the head of layer 1                     m    
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
        # MODFLOW seepage scheme (modflow_seepage): saturated share and capillary rise share from the MODFLOW head
        self.var.seepageOn = self.var.modflow and self.var.modflow_seepage
        if self.var.capRiseOn or self.var.seepageOn:
            # dzRel:       0     1     2     3     4     5     6     7     8     9    10    11    12
            self.var.capRisePct = [0.0, 0.01, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
            # capRiseSlope[i-1]: fraction per m between dzRel[i-1] and dzRel[i]
            self.var.capRiseSlope = []
            for i in range(1, 13):
                self.var.capRiseSlope.append((self.var.capRisePct[i] - self.var.capRisePct[i-1]) /
                                             np.maximum(1e-3, self.var.dzRel[i] - self.var.dzRel[i-1]))
        if self.var.seepageOn:
            # area mean of dzRel: the MODFLOW water table (depth_to_water) is a mean over the cell
            self.var.dzRelMean = globals.inZero.copy()
            for i in range(1, 13):
                self.var.dzRelMean += (self.var.capRisePct[i] - self.var.capRisePct[i-1]) * 0.5 * (
                    self.var.dzRel[i] + self.var.dzRel[i-1])

    def area_below(self, z):
        """area fraction of the cell with a relative elevation dzRel below z (m), linear between the percentiles"""
        frac = 1.0 - (self.var.dzRel[12] - z) * self.var.capRiseSlope[11]
        for i in range(11, 0, -1):
            h = self.var.capRisePct[i] - (self.var.dzRel[i] - z) * self.var.capRiseSlope[i-1]
            frac = np.where(z < self.var.dzRel[i], h, frac)
        return np.maximum(0.0, np.minimum(1.0, frac))

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
            self.var.capRiseFrac = self.area_below(dzGroundwater)
        elif self.var.seepageOn:
            # MODFLOW water table relative to dzRel (head of the last MODFLOW run): saturated share of the part covered
            # by ModFlow cells (soil percolation and preferential flow), capillary rise up to maxGWCapRise above it
            watertable = self.var.dzRelMean - self.var.depth_to_water
            self.var.saturatedFrac = self.var.modflow_cover * self.area_below(watertable)
            self.var.capRiseFrac = np.maximum(0., self.var.modflow_cover * self.area_below(
                watertable + self.var.maxGWCapRise) - self.var.saturatedFrac)
        else:
            self.var.capRiseFrac = 0.
