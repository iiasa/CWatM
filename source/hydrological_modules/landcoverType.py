# -------------------------------------------------------------------------
# Name:        Land Cover Type module
# Purpose:
#
# Author:      PB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class landcoverType(object):

    """
    # ************************************************************
    # *****  LAND COVER TYPE *************************************
    # ************************************************************
    """

    def __init__(self, landcoverType_variable):
        self.var = landcoverType_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the land cover type module
        """
        coverTypes= map(str.strip, binding["coverTypes"].split(","))
        i = 1
		#self.var.recessionCoeff = loadmap('recessionCoeff')
 

# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the land cover type module
        """

        i = 1
