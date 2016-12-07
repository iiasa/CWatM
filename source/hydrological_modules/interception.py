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

    """@package
    # ************************************************************
    # ***** Interception *****************************************
    # ************************************************************
    """

    def __init__(self, interception_variable):
        self.var = interception_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

 

    def dynamic(self,coverType, No):
        """ Dynamic part of the interception module
        calculating interception for each land cover class

        @param coverType land cover type: forest, grassland ..
        @param No Number of land cover type: forest = 0, grassland = 1 ...
        Args:
            coverType: coverType land cover type: forest, grassland ..
            No: Number of land cover type: forest = 0, grassland = 1 ...
        """

        if not coverType.startswith("irr"):
            ## interceptCap Maximum interception read from file for forest and grassland land cover
            # for specific days of the year - repeated every year
            if dateVar['newStart'] or dateVar['new10day']:  # check if first day  of the year
                self.var.interceptCap[No]  = readnetcdf2(binding[coverType + '_interceptCapNC'], dateVar['10day'], "10day")
                #coverFraction = readnetcdf2(binding[coverType + '_coverFractionNC'], dateVar['doy'], "DOY")
                #interceptCap = coverFraction * interceptCap
                self.var.interceptCap[No] = np.maximum(self.var.interceptCap[No], self.var.minInterceptCap[No])
                #interceptCap = self.var.minInterceptCap[No]
        else:
            self.var.interceptCap[No] = self.var.minInterceptCap[No]

        if option['calcWaterBalance']:
            prevState = self.var.interceptStor[No].copy()


        ## throughfall = surplus above the interception storage threshold
        # PB changed to Rain instead Pr, bceause snow is substracted later
        # PB it is assuming that all interception storage is used the other time step
        throughfall = np.maximum(0.0, self.var.Rain + self.var.interceptStor[No] - self.var.interceptCap[No])
        ## update interception storage after throughfall
        self.var.interceptStor[No] = self.var.interceptStor[No] + self.var.Rain - throughfall
        ## availWaterInfiltration Available water for infiltration: throughfall + snow melt
        self.var.availWaterInfiltration[No] = np.maximum(0.0, throughfall + self.var.SnowMelt)



        #mult = getValDivZero(self.var.interceptStor[No], interceptCap, 1e39, 0.) ** 0.66666
        with np.errstate(invalid='ignore', divide='ignore'):
            mult = np.where(self.var.interceptCap[No] > 0, self.var.interceptStor[No]/self.var.interceptCap[No], 0.0)  ** self.var.twothird
        ## interceptEvap evaporation from intercepted water (based on potTranspiration)
        self.var.interceptEvap[No] = np.minimum(self.var.interceptStor[No], self.var.potTranspiration[No] * mult)
        self.var.interceptEvap[No] = np.minimum(self.var.interceptEvap[No], self.var.potTranspiration[No])

        # update interception storage and potTranspiration
        self.var.interceptStor[No] = self.var.interceptStor[No] - self.var.interceptEvap[No]
        self.var.potTranspiration[No] = np.maximum(0, self.var.potTranspiration[No] - self.var.interceptEvap[No])

        # update actual evaporation (after interceptEvap)
        # interceptEvap is the first flux in ET
        self.var.actualET[No] = self.var.interceptEvap[No].copy()

        if option['calcWaterBalance']:
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.Rain,self.var.SnowMelt],  # In
                [self.var.availWaterInfiltration[No],self.var.interceptEvap[No]],  # Out
                [prevState],   # prev storage
                [self.var.interceptStor[No]],
                "Interception", False)


