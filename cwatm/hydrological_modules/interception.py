# -------------------------------------------------------------------------
# Name:        Interception module
# Purpose:
#
# Author:      PB
#
# Created:     01/08/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


class interception(object):
    """
    INTERCEPTION


    **Global variables**

    =====================================  ======================================================================  =====
    Variable [self.var]                    Description                                                             Unit 
    =====================================  ======================================================================  =====
    interceptCap                           interception capacity of vegetation                                     m    
    interceptEvap                          simulated evaporation from water intercepted by vegetation              m    
    potTranspiration                       Potential transpiration (after removing of evaporation)                 m    
    snowEvap                               total evaporation from snow for a snow layers                           m    
    minInterceptCap                        Maximum interception read from file for forest and grassland land cove  m    
    interceptStor                          simulated vegetation interception storage                               m    
    availWaterInfiltration                 quantity of water reaching the soil after interception, more snowmelt   m    
    twothird                               2/3                                                                     --   
    EWRef                                  potential evaporation rate from water surface                           m    
    Rain                                   Precipitation less snow                                                 m    
    SnowMelt                               total snow melt from all layers                                         m    
    actualET                               simulated evapotranspiration from soil, flooded area and vegetation     m    
    =====================================  ======================================================================  =====

    **Functions**
    """

    def __init__(self, model):
        self.var = model.var
        self.model = model

    # noinspection PyTypeChecker
    def dynamic(self,coverType, No):
        """
        Dynamic part of the interception module
        calculating interception for each land cover class

        :param coverType: Land cover type: forest, grassland  ...
        :param No: number of land cover type: forest = 0, grassland = 1 ...
        :return: interception evaporation, interception storage, reduced pot. transpiration

        """

        if coverType in ['forest','grassland']:
            ## interceptCap Maximum interception read from file for forest and grassland land cover
            # for specific days of the year - repeated every year
            if dateVar['newStart'] or dateVar['new10day']:  # check if first day  of the year
                self.var.interceptCap[No]  = readnetcdf2(coverType + '_interceptCapNC', dateVar['10day'], "10day")
                self.var.interceptCap[No] = np.maximum(self.var.interceptCap[No], self.var.minInterceptCap[No])
        else:
            self.var.interceptCap[No] = self.var.minInterceptCap[No]

        if checkOption('calcWaterBalance'):
            prevState = self.var.interceptStor[No].copy()



        # Rain instead Pr, because snow is substracted later
        # assuming that all interception storage is used the other time step
        throughfall = np.maximum(0.0, self.var.Rain + self.var.interceptStor[No] - self.var.interceptCap[No])

        # update interception storage after throughfall
        self.var.interceptStor[No] = self.var.interceptStor[No] + self.var.Rain - throughfall

        # availWaterInfiltration Available water for infiltration: throughfall + snow melt
        self.var.availWaterInfiltration[No] = np.maximum(0.0, throughfall + self.var.SnowMelt)

        if coverType in ['forest', 'grassland', 'irrPaddy', 'irrNonPaddy']:
            mult = divideValues(self.var.interceptStor[No],self.var.interceptCap[No]) ** self.var.twothird
            # interceptEvap evaporation from intercepted water (based on potTranspiration)
            self.var.interceptEvap[No] = np.minimum(self.var.interceptStor[No], self.var.potTranspiration[No] * mult)

        if coverType in ['sealed']:
            self.var.interceptEvap[No] = np.maximum(np.minimum(self.var.interceptStor[No], self.var.EWRef),globals.inZero)


        # update interception storage and potTranspiration
        self.var.interceptStor[No] = self.var.interceptStor[No] - self.var.interceptEvap[No]
        self.var.potTranspiration[No] = np.maximum(0, self.var.potTranspiration[No] - self.var.interceptEvap[No])

        # update actual evaporation (after interceptEvap)
        # interceptEvap is the first flux in ET, soil evapo and transpiration are added later
        self.var.actualET[No] = self.var.interceptEvap[No]  + self.var.snowEvap



        #if (dateVar['curr'] == 15):
        #    ii=1

        if checkOption('calcWaterBalance'):
            self.model.waterbalance_module.waterBalanceCheck(
               [self.var.Rain, self.var.SnowMelt],  # In
               [self.var.availWaterInfiltration[No], self.var.interceptEvap[No]],  # Out
               [prevState],  # prev storage
               [self.var.interceptStor[No]],
               "Interception", False)

