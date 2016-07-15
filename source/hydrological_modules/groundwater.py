# -------------------------------------------------------------------------
# Name:        Groundwater module
# Purpose:
#
# Author:      PB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class groundwater(object):

    """
    # ************************************************************
    # ***** SOIL *****************************************
    # ************************************************************
    """

    def __init__(self, groundwater_variable):
        self.var = groundwater_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the groundwater module
        """
        self.var.recessionCoeff = loadmap('recessionCoeff')
        self.var.specificYield = loadmap('specificYield')
        self.var.kSatAquifer = loadmap('kSatAquifer')

        # init calculation recession coefficient, speciefic yield, ksatAquifer
        self.var.recessionCoeff = np.maximum(5.e-4,self.var.recessionCoeff)
        self.var.recessionCoeff = np.minimum(1.000,self.var.recessionCoeff)
        self.var.specificYield  = np.maximum(0.010,self.var.specificYield)
        self.var.specificYield  = np.minimum(1.000,self.var.specificYield)
        self.var.kSatAquifer = np.maximum(0.010,self.var.kSatAquifer)
        i = 1

        # initial conditions
          #   def getICs(self,iniItems,iniConditions = None):
        self.var.storGroundwater = loadmap('storGroundwater')

# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the soil module
        """

        i = 1
