# -------------------------------------------------------------------------
# Name:        POTENTIAL REFERENCE EVAPO(TRANSPI)RATION
# Purpose:
#
# Author:      PB
#
# Created:     10/01/2017
# Copyright:   (c) PB 2017
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


class evaporationPot(object):
    """
    POTENTIAL REFERENCE EVAPO(TRANSPI)RATION
    Calculate potential evapotranspiration from climate data mainly based on FAO 56 and LISVAP
    Based on Penman Monteith

    References:
        http://www.fao.org/docrep/X0490E/x0490e08.htm#penman%20monteith%20equation
        http://www.fao.org/docrep/X0490E/x0490e06.htm  http://www.fao.org/docrep/X0490E/x0490e06.htm
        https://ec.europa.eu/jrc/en/publication/eur-scientific-and-technical-research-reports/lisvap-evaporation-pre-processor-lisflood-water-balance-and-flood-simulation-model

    **Global variables**

    =====================================  ======================================================================  =====
    Variable [self.var]                    Description                                                             Unit 
    =====================================  ======================================================================  =====
    cropCorrect                            calibration factor of crop KC factor                                         
    pet_modus                              Flag: index which ETP approach is used e.g. 1 for Penman-Monteith       bool 
    AlbedoCanopy                           Albedo of vegetation canopy (FAO,1998) default =0.23                         
    AlbedoSoil                             Albedo of bare soil surface (Supit et. al. 1994) default = 0.15              
    AlbedoWater                            Albedo of water surface (Supit et. al. 1994) default = 0.05                  
    co2                                                                                                                 
    albedoLand                             albedo from land surface (from GlobAlbedo database)                     --   
    albedoOpenWater                        albedo from open water surface (from GlobAlbedo database)               --   
    TMin                                   minimum air temperature                                                 K    
    TMax                                   maximum air temperature                                                 K    
    Psurf                                  Instantaneous surface pressure                                          Pa   
    Qair                                   specific humidity                                                       kg/kg
    Tavg                                   Input, average air Temperature                                          K    
    Rsdl                                   long wave downward surface radiation fluxes                             W/m2 
    Rsds                                   short wave downward surface radiation fluxes                            W/m2 
    Wind                                   wind speed                                                              m/s  
    ETRef                                  potential evapotranspiration rate from reference crop                   m    
    EWRef                                  potential evaporation rate from water surface                           m    
    =====================================  ======================================================================  =====

    **Functions**
    """

    def __init__(self, model):
        """
        The constructor evaporationPot
        """
        self.var = model.var
        self.model = model
        
    def initial(self):
        """
        Initial part of evaporation type module
        Load inictial parameters

        Note:
            Only run if *calc_evaporation* is True
        """

        #self.var.sumETRef = globals.inZero.copy()
        self.var.cropCorrect = loadmap('crop_correct')

        if checkOption('calc_evaporation'):


            # Default calculation method is Penman Monteith
            # if PET_modus is missing use Penman Monteith
            self.var.pet_modus = 1
            if "PET_modus" in option:
                self.var.pet_modus = checkOption('PET_modus')

            self.initial_1()
            #if self.var.pet_modus == 1: self.initial_1()

    # --------------------------------------------------------------------------

    def initial_1(self):
        """
        Initial part of evaporation type module
        Load initial parameters
        1: Penman Monteith
        2: Milly and Dunne method
        P. C. D. Milly* and K. A. Dunne, 2016: Potential evapotranspiration and continental drying, Nature Climate Change, DOI: 10.1038/NCLIMATE3046
        Energy only PET: ET=0.8(Rn ?)   equation 8
        3: Yang et al. Penman Montheith correction method
        Yang, Y., Roderick, M. L., Zhang, S., McVicar, T. R., and Donohue, R. J.: Hydrologic implications of vegetation response to elevated CO2 in climate projections, Nat. Clim. Change, 9, 44-48, 10.1038/s41558-018-0361-0, 2019.
        Equation 14: where the term 2.14 accounts for changing [CO2] on rs



        """

        self.var.AlbedoCanopy = loadmap('AlbedoCanopy')
        self.var.AlbedoSoil = loadmap('AlbedoSoil')
        self.var.AlbedoWater = loadmap('AlbedoWater')


    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------


    def dynamic(self):
        """
        Dynamic part of the potential evaporation module

        :return: 
            - ETRef - potential reference evapotranspiration rate [m/day]
            - EWRef - potential evaporation rate from water surface [m/day]
        """

        if checkOption('calc_evaporation'):
            if self.var.pet_modus == 1: self.dynamic_1()
            if self.var.pet_modus == 2: self.dynamic_2()
            if self.var.pet_modus == 3: self.dynamic_1()
            if self.var.pet_modus == 4: self.dynamic_4()
    # --------------------------------------------------------------------------


    def dynamic_1(self):
        """
        Dynamic part of the potential evaporation module
        Based on Penman Monteith - FAO 56

        """

        if self.var.pet_modus == 3:
            #Yang et al.Penman Montheith correction method
            # loading CO2 concentration RCP2.6-RCP8.5
            if dateVar['newStart'] or dateVar['newYear']:
                self.var.co2 = readnetcdf2('co2conc', dateVar['currDate'], "yearly", value="CO2", cut = False, compress= False)

        ESatmin = 0.6108* np.exp((17.27 * self.var.TMin) / (self.var.TMin + 237.3))
        ESatmax = 0.6108* np.exp((17.27 * self.var.TMax) / (self.var.TMax + 237.3))
        ESat = (ESatmin + ESatmax) / 2.0   # [KPa]
        # http://www.fao.org/docrep/X0490E/x0490e07.htm   equation 11/12

        # Fao 56 Page 36
        # calculate actual vapour pressure
        if returnBool('useHuss'):
            # if specific humidity calculate actual vapour pressure this way
            EAct = (self.var.Psurf * self.var.Qair) / ((0.378 * self.var.Qair) + 0.622)
            # http://www.eol.ucar.edu/projects/ceop/dm/documents/refdata_report/eqns.html
            # (self.var.Psurf * self.var.Qair)/0.622
            # old calculation not completely ok
        else:
            # if relative humidity
            EAct = ESat * self.var.Qair / 100.0

        # ************************************************************
        # ***** NET ABSORBED RADIATION *******************************
        # ************************************************************
        LatHeatVap = 2.501 - 0.002361 * self.var.Tavg
        # latent heat of vaporization [MJ/kg]

        EmNet = (0.34 - 0.14 * np.sqrt(EAct))
        # Net emissivity

        # longwave radiation balance
        RNUp = 4.903E-9 * (((self.var.TMin + 273.16) ** 4) + ((self.var.TMax + 273.16) ** 4)) / 2
        # Up longwave radiation [MJ/m2/day]
        RLN = RNUp - self.var.Rsdl
        # RDL is stored on disk as W/m2 but converted in MJ/m2/s in readmeteo.py

        if returnBool('albedo'):
            if dateVar['newStart'] or dateVar['newMonth']:  # loading every month a new map
                self.var.albedoLand = readnetcdf2('albedoMaps', dateVar['currDate'], useDaily='month',value='albedoLand')
                self.var.albedoOpenWater = readnetcdf2('albedoMaps', dateVar['currDate'], useDaily='month',value='albedoWater')
            RNA = np.maximum(((1 - self.var.albedoLand) * self.var.Rsds - RLN) / LatHeatVap, 0.0)
            RNAWater = np.maximum(((1 - self.var.albedoOpenWater) * self.var.Rsds - RLN) / LatHeatVap, 0.0)

        else:
            RNA = np.maximum(((1 - self.var.AlbedoCanopy) * self.var.Rsds - RLN) / LatHeatVap, 0.0)
            # net absorbed radiation of reference vegetation canopy [mm/d]
            # RNASoil = np.maximum(((1 - self.var.AlbedoSoil) * self.var.Rsds - RLN) / LatHeatVap, 0.0)
            # net absorbed radiation of bare soil surface
            RNAWater = np.maximum(((1 - self.var.AlbedoWater) * self.var.Rsds - RLN) / LatHeatVap, 0.0)
            # net absorbed radiation of water surface

        VapPressDef = np.maximum(ESat - EAct, 0.0)
        Delta = ((4098.0 * ESat) / ((self.var.Tavg + 237.3)**2))
        # slope of saturated vapour pressure curve [mbar/deg C]
        Psycon = 0.665E-3 * self.var.Psurf
        # psychrometric constant [kPa C-1]
        # http://www.fao.org/docrep/X0490E/x0490e07.htm  Equation 8
        # see http://www.fao.org/docrep/X0490E/x0490e08.htm#penman%20monteith%20equation

        windpart = 900 * self.var.Wind / (self.var.Tavg + 273.16)

        if self.var.pet_modus == 1:
            denominator = Delta + Psycon *(1 + 0.34 * self.var.Wind)
        else:
            # Yang et al.Penman Montheith correction method:  term 2 accounts for changing [CO2] on rs.
            denominator = Delta + Psycon * (1 + self.var.Wind*(0.34+0.00024*(self.var.co2-300.)))

        numerator1 = Delta / denominator
        numerator2 = Psycon / denominator
        # the 0.408 constant is replace by 1/LatHeatVap see above

        RNAN = RNA * numerator1
        #RNANSoil = RNASoil * numerator1
        RNANWater = RNAWater * numerator1

        EA = windpart * VapPressDef * numerator2

        # Potential evapo(transpi)ration is calculated for two reference surfaces:
        # 1. Reference vegetation canopy
        # 2. Open water surface
        self.var.ETRef = (RNAN + EA) * 0.001
        # potential reference evapotranspiration rate [m/day]  # from mm to m with 0.001
        #self.var.ESRef = RNANSoil + EA
        # potential evaporation rate from a bare soil surface [m/day]
        self.var.EWRef = (RNANWater + EA) * 0.001
        ii =1
        # potential evaporation rate from water surface [m/day]

        # -> here we are at ET0 (see http://www.fao.org/docrep/X0490E/x0490e04.htm#TopOfPage figure 4:)

        #self.var.sumETRef = self.var.sumETRef + self.var.ETRef*1000


        #if dateVar['curr'] ==32:
        #ii=1

        #report(decompress(self.var.sumETRef), "C:\work\output2/sumetref.map")

    def dynamic_2(self):
        """
        Dynamic part of the potential evaporation module
        2: Milly and Dunne method
        P. C. D. Milly* and K. A. Dunne, 2016: Potential evapotranspiration and continental drying, Nature Climate Change, DOI: 10.1038/NCLIMATE3046
        Energy only PET = 0.8(Rn ? )   equation 8

        """
        LatHeatVap = 2.501 - 0.002361 * self.var.Tavg
        # latent heat of vaporization [MJ/kg]

        RNUp = 4.903E-9 * (((self.var.TMin + 273.16) ** 4) + ((self.var.TMax + 273.16) ** 4)) / 2
        # Up longwave radiation [MJ/m2/day]
        RLN = RNUp - self.var.Rsdl
        # RDL is stored on disk as W/m2 but converted in MJ/m2/s in readmeteo.py

        if returnBool('albedo'):
            if dateVar['newStart'] or dateVar['newMonth']:  # loading every month a new map
                self.var.albedoLand = readnetcdf2('albedoMaps', dateVar['currDate'], useDaily='month',value='albedoLand')
                self.var.albedoOpenWater = readnetcdf2('albedoMaps', dateVar['currDate'], useDaily='month',value='albedoWater')
            RNA = np.maximum(((1 - self.var.albedoLand) * self.var.Rsds - RLN) / LatHeatVap, 0.0)
            RNAWater = np.maximum(((1 - self.var.albedoOpenWater) * self.var.Rsds - RLN) / LatHeatVap, 0.0)

        else:
            RNA = np.maximum(((1 - self.var.AlbedoCanopy) * self.var.Rsds - RLN) / LatHeatVap, 0.0)
            # net absorbed radiation of reference vegetation canopy [mm/d]
            # RNASoil = np.maximum(((1 - self.var.AlbedoSoil) * self.var.Rsds - RLN) / LatHeatVap, 0.0)
            # net absorbed radiation of bare soil surface
            RNAWater = np.maximum(((1 - self.var.AlbedoWater) * self.var.Rsds - RLN) / LatHeatVap, 0.0)
            # net absorbed radiation of water surface

        # 1. Reference vegetation canopy
        # 2. Open water surface
        self.var.ETRef = 0.8 * RNA * 0.001
        # potential reference evapotranspiration rate [m/day]  # from mm to m with 0.001
        # potential evaporation rate from a bare soil surface [m/day]
        self.var.EWRef = 0.8 * RNAWater * 0.001

    def dynamic_4(self):
        """
        Dynamic part of the potential evaporation module
        4. Priestley-Taylor  1.26 * delat
        https://wetlandscapes.github.io/blog/blog/penman-monteith-and-priestley-taylor/
        """
        ESatmin = 0.6108* np.exp((17.27 * self.var.TMin) / (self.var.TMin + 237.3))
        ESatmax = 0.6108* np.exp((17.27 * self.var.TMax) / (self.var.TMax + 237.3))
        ESat = (ESatmin + ESatmax) / 2.0   # [KPa]
        # http://www.fao.org/docrep/X0490E/x0490e07.htm   equation 11/12

        # Fao 56 Page 36
        # calculate actual vapour pressure
        if returnBool('useHuss'):
            # if specific humidity calculate actual vapour pressure this way
            EAct = (self.var.Psurf * self.var.Qair) / ((0.378 * self.var.Qair) + 0.622)
            # http://www.eol.ucar.edu/projects/ceop/dm/documents/refdata_report/eqns.html
            # (self.var.Psurf * self.var.Qair)/0.622
            # old calculation not completely ok
        else:
            # if relative humidity
            EAct = ESat * self.var.Qair / 100.0



        LatHeatVap = 2.501 - 0.002361 * self.var.Tavg
        # latent heat of vaporization [MJ/kg]
        RNUp = 4.903E-9 * (((self.var.TMin + 273.16) ** 4) + ((self.var.TMax + 273.16) ** 4)) / 2
        # Up longwave radiation [MJ/m2/day]
        RLN = RNUp - self.var.Rsdl
        # RDL is stored on disk as W/m2 but converted in MJ/m2/s in readmeteo.py
        RNA = np.maximum(((1 - self.var.AlbedoCanopy) * self.var.Rsds - RLN) / LatHeatVap, 0.0)
        RNAWater = np.maximum(((1 - self.var.AlbedoWater) * self.var.Rsds - RLN) / LatHeatVap, 0.0)

        Delta = ((4098.0 * ESat) / ((self.var.Tavg + 237.3)**2))
        # slope of saturated vapour pressure curve [mbar/deg C]
        Psycon = 0.665E-3 * self.var.Psurf
        # psychrometric constant [kPa C-1]
        # http://www.fao.org/docrep/ X0490E/ x0490e07.htm  Equation 8
        # see http://www.fao.org/docrep/X0490E/x0490e08.htm#penman%20monteith%20equation
        RNAN = 1.1 * Delta / (Delta + Psycon)  * RNA
        #RNANSoil = RNASoil * numerator1
        RNANWater = 1.26 * Delta / (Delta + Psycon) * RNAWater

        # 1. Reference vegetation canopy
        # 2. Open water surface
        self.var.ETRef = RNAN * 0.001
        # potential reference evapotranspiration rate [m/day]  # from mm to m with 0.001
        # potential evaporation rate from a bare soil surface [m/day]
        self.var.EWRef = RNANWater * 0.001

