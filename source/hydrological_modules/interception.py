# -------------------------------------------------------------------------
# Name:        Interception module
# Purpose:
#
# Author:      PB
#
# Created:     01/08/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class interception(object):

    """
    # ************************************************************
    # ***** SOIL *****************************************
    # ************************************************************
    """

    def __init__(self, interception_variable):
        self.var = interception_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

 

    def dynamic(self,coverType, No):

        if not coverType.startswith("irr"):
            interceptCap  = readnetcdf2(binding[coverType + '_interceptCapNC'], self.var.CalendarDay, "DOY")
            coverFraction = readnetcdf2(binding[coverType + '_coverFractionNC'], self.var.CalendarDay, "DOY")
            interceptCap = coverFraction * interceptCap
            interceptCap = np.maximum(interceptCap, self.var.minInterceptCap[No])
        else:
            interceptCap = self.var.minInterceptCap[No]

        # throughfall = surplus above the interception storage threshold
        # throughfall = np.maximum(0.0, self.var.interceptStor[No] + self.var.Precipitation - interceptCap)
        # PB changed to Rain instead Pr, bceause snow is substracted later
        # PB it is assuming that all interception storage is used the other time step
        throughfall = np.maximum(0.0, self.var.Rain + self.var.interceptStor[No] - interceptCap)

        # update interception storage after throughfall
        #self.var.interceptStor[No] = np.maximum(0.0, self.var.interceptStor[No] + self.var.Precipitation - throughfall)
        # PB or to make it short
        self.var.interceptStor[No] = self.var.interceptStor[No] + self.var.Rain - throughfall

        self.var.availWaterInfiltration[No] = np.maximum(0.0, throughfall + self.var.SnowMelt)





        # evaporation from intercepted water (based on potTranspiration)
        #mult = getValDivZero(self.var.interceptStor[No], interceptCap, 1e39, 0.) ** 0.66666
        with np.errstate(invalid='ignore', divide='ignore'):
            mult = np.where(interceptCap > 0, self.var.interceptStor[No]/interceptCap, 0.0)  ** self.var.twothird
        self.var.interceptEvap[No] = np.minimum(self.var.interceptStor[No], self.var.potTranspiration[No] * mult)
        self.var.interceptEvap[No] = np.minimum(self.var.interceptEvap[No], self.var.potTranspiration[No])

        # update interception storage and potTranspiration
        self.var.interceptStor[No] = self.var.interceptStor[No] - self.var.interceptEvap[No]
        self.var.potTranspiration[No] = np.maximum(0, self.var.potTranspiration[No] - self.var.interceptEvap[No])

        # update actual evaporation (after interceptEvap)
        # interceptEvap is the first flux in ET
        self.var.actualET[No] = self.var.interceptEvap[No].copy()
