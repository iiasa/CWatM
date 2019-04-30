# -------------------------------------------------------------------------
# Name:        Capillar Rise module
# Purpose:
#
# Author:      PB
#
# Created:     20/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class capillarRise(object):

    """
    CAPPILAR RISE
    calculate cell fraction influenced by capillary rise
    """

    def __init__(self, capillarRise_variable):
        self.var = capillarRise_variable


# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Dynamic part of the capillar Rise module
        calculate cell fraction influenced by capillary rise
        depending on appr. height of groundwater and relative elevation of grid cell

        :return: capRiseFrac = cell fraction influenced by capillary rise
        """

        if checkOption('CapillarRise') and not(self.var.modflow):

        # approximate height of groundwater table and corresponding reach of cell under influence of capillary rise
            dzGroundwater = self.var.storGroundwater / self.var.specificYield + self.var.maxGWCapRise

            CRFRAC = np.minimum(1.0,  1.0 -(self.var.dzRel0100 - dzGroundwater)*0.1 /np.maximum(1e-3,self.var.dzRel0100-self.var.dzRel0090))
            CRFRAC = np.where(dzGroundwater < self.var.dzRel0090, 0.9 - (self.var.dzRel0090 - dzGroundwater) * 0.1 / np.maximum(1e-3, self.var.dzRel0090 - self.var.dzRel0080), CRFRAC)
            CRFRAC = np.where(dzGroundwater < self.var.dzRel0080, 0.8 - (self.var.dzRel0080 - dzGroundwater) * 0.1 / np.maximum(1e-3, self.var.dzRel0080 - self.var.dzRel0070), CRFRAC)
            CRFRAC = np.where(dzGroundwater < self.var.dzRel0070, 0.7 - (self.var.dzRel0070 - dzGroundwater) * 0.1 / np.maximum(1e-3, self.var.dzRel0070 - self.var.dzRel0060), CRFRAC)
            CRFRAC = np.where(dzGroundwater < self.var.dzRel0060, 0.6 - (self.var.dzRel0060 - dzGroundwater) * 0.1 / np.maximum(1e-3, self.var.dzRel0060 - self.var.dzRel0050), CRFRAC)
            CRFRAC = np.where(dzGroundwater < self.var.dzRel0050, 0.5 - (self.var.dzRel0050 - dzGroundwater) * 0.1 / np.maximum(1e-3, self.var.dzRel0050 - self.var.dzRel0040), CRFRAC)
            CRFRAC = np.where(dzGroundwater < self.var.dzRel0040, 0.4 - (self.var.dzRel0040 - dzGroundwater) * 0.1 / np.maximum(1e-3, self.var.dzRel0040 - self.var.dzRel0030), CRFRAC)
            CRFRAC = np.where(dzGroundwater < self.var.dzRel0030, 0.3 - (self.var.dzRel0030 - dzGroundwater) * 0.1 / np.maximum(1e-3, self.var.dzRel0030 - self.var.dzRel0020), CRFRAC)
            CRFRAC = np.where(dzGroundwater < self.var.dzRel0020, 0.2 - (self.var.dzRel0020 - dzGroundwater) * 0.1 / np.maximum(1e-3, self.var.dzRel0020 - self.var.dzRel0010), CRFRAC)
            CRFRAC = np.where(dzGroundwater < self.var.dzRel0010, 0.1 - (self.var.dzRel0010 - dzGroundwater) * 0.1 / np.maximum(1e-3, self.var.dzRel0010 - self.var.dzRel0005), CRFRAC)
            CRFRAC = np.where(dzGroundwater < self.var.dzRel0005, 0.05 - (self.var.dzRel0005 - dzGroundwater) * 0.1 / np.maximum(1e-3, self.var.dzRel0005 - self.var.dzRel0001), CRFRAC)
            CRFRAC = np.where(dzGroundwater < self.var.dzRel0001, 0.01 - (self.var.dzRel0001 - dzGroundwater) * 0.1 / np.maximum(1e-3, self.var.dzRel0001), CRFRAC)
            self.var.capRiseFrac = np.maximum(0.0,np.minimum(1.0,CRFRAC))
        else:
            self.var.capRiseFrac =  0.




