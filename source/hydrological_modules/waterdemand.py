# -------------------------------------------------------------------------
# Name:        Waterdemand module
# Purpose:
#
# Author:      PB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class waterdemand(object):

    """
    # ************************************************************
    # ***** SOIL *****************************************
    # ************************************************************
    """

    def __init__(self, waterdemand_variable):
        self.var = waterdemand_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the groundwater module
        """
        if option['includeWaterDemandDomInd']:
           #self.var.recessionCoeff = loadmap('recessionCoeff')

           i = 1
           # TODO : add  zones at which water allocation (surface and groundwater allocation) is determined
           #  landSurface.py lines 317ff



# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the soil module
        """

        i = 1
