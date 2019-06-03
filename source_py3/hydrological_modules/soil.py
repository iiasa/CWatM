# -------------------------------------------------------------------------
# Name:        Soil module
# Purpose:
#
# Author:      PB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016 based on PCRGLOBE, LISFLOOD, HBV
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class soil(object):

    """
    SOIL

    Caclulation vertical transfer of water based on Arno scheme
    """

    def __init__(self, soil_variable):
        self.var = soil_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """
        Initial part of the soil module

        * Initialize all the hydraulic properties of soil
        * Set soil depth
        """

        self.var.soilLayers = 3
        # --- Topography -----------------------------------------------------
        #self.var.tanslope = loadmap('tanslope')
        #self.var.slopeLength = loadmap('slopeLength')


        #self.var.tanslope = np.maximum(self.var.tanslope, 0.00001)
        # setting slope >= 0.00001 to prevent 0 value

        # maps of relative elevation above flood plains
        dzRel = ['dzRel0001','dzRel0005',
                 'dzRel0010','dzRel0020','dzRel0030','dzRel0040','dzRel0050',
                 'dzRel0060','dzRel0070','dzRel0080','dzRel0090','dzRel0100']
        for i in dzRel:
            vars(self.var)[i] = readnetcdfWithoutTime(cbinding('relativeElevation'),i)

        # Fraction of area where percolation to groundwater is impeded [dimensionless]
        self.var.percolationImp = np.maximum(0,np.minimum(1,loadmap('percolationImp') * loadmap('factor_interflow')))


    # ------------ Preferential Flow constant ------------------------------------------
        self.var.cropGroupNumber = loadmap('cropgroupnumber')
        # soil water depletion fraction, Van Diepen et al., 1988: WOFOST 6.0, p.86, Doorenbos et. al 1978
        # crop groups for formular in van Diepen et al, 1988

    # ------------ Preferential Flow constant ------------------------------------------
        self.var.cPrefFlow = loadmap('preferentialFlowConstant')


    # ------------ SOIL DEPTH ----------------------------------------------------------
        # soil thickness and storage

        #soilDepthLayer = [('soildepth', 'SoilDepth'),('storCap','soilWaterStorageCap')]
        soilDepthLayer = [('soildepth', 'SoilDepth')]
        for layer,property  in soilDepthLayer:
            vars(self.var)[layer] = np.tile(globals.inZero, (self.var.soilLayers, 1))

        # first soil layer = 5 cm
        self.var.soildepth[0] = 0.05 + globals.inZero
        # second soul layer minimum 5cm
        self.var.soildepth[1] = np.maximum(0.05, loadmap('StorDepth1') - self.var.soildepth[0])

        # soil depth[1] is inc/decr by a calibration factor
        #self.var.soildepth[1] =  self.var.soildepth[1] * loadmap('soildepth_factor')
        #self.var.soildepth[1] = np.maximum(0.05, self.var.soildepth[1])

        # corrected by the calibration factor, total soil depth stays the same
        #self.var.soildepth[2] = loadmap('StorDepth2') + (1. - loadmap('soildepth_factor') * self.var.soildepth[1])
        #self.var.soildepth[2] = loadmap('StorDepth2') * loadmap('soildepth_factor')
        self.var.soildepth[2] = loadmap('StorDepth2')
        self.var.soildepth[2] = np.maximum(0.05, self.var.soildepth[2])

        # Calibration
        soildepth_factor =  loadmap('soildepth_factor')
        self.var.soildepth[1] = self.var.soildepth[1] * soildepth_factor
        self.var.soildepth[2] = self.var.soildepth[2] * soildepth_factor
        self.var.soildepth12 = self.var.soildepth[1] + self.var.soildepth[2]

        ii= 0

        # report("C:/work/output2/soil.map", self.var.soildepth12)









# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self, coverType, No):
        """
        Dynamic part of the soil module

        For each of the land cover classes the vertical water transport is simulated
        Distribution of water holding capiacity in 3 soil layers based on saturation excess overland flow, preferential flow
        Dependend on soil depth, soil hydraulic parameters
        """

    # ---------------------------------------------------------

        if checkOption('calcWaterBalance'):

            preStor1 = self.var.w1[No].copy()
            preStor2 = self.var.w2[No].copy()
            preStor3 = self.var.w3[No].copy()
            pretopwater = self.var.topwater


        # -----------------------------------------------------------
        # from evaporation
        # calculate potential bare soil evaporation and transpiration
        # self.var.potBareSoilEvap = self.var.cropCorrect * self.var.minCropKC[No] * self.var.ETRef
        # potTranspiration: Transpiration for each land cover class
        # self.var.potTranspiration[No] = self.var.cropCorrect * self.var.cropKC * self.var.ETRef - self.var.potBareSoilEvap

        # from interception module
        # self.var.potTranspiration[No] = np.maximum(0, self.var.potTranspiration[No] - self.var.interceptEvap[No])
        # # interceptEvap is the first flux in ET, soil evapo and transpiration are added later
        # self.var.actualET[No] = self.var.interceptEvap[No].copy()

        #if (dateVar['curr'] == 130) and (No==2):
        #    ii=1

        availWaterInfiltration = self.var.availWaterInfiltration[No].copy()
        availWaterInfiltration = availWaterInfiltration + self.var.act_irrConsumption[No]
        # availWaterInfiltration = water net from precipitation (- soil - interception - snow + snow melt) + water for irrigation




        if coverType == 'irrPaddy':
            # depending on the crop calender -> here if cropKC > 0.75 paddies are flooded to 50mm (as set in settings file)

            #if self.var.cropKC[No]>0.75:
            #    ii = 1

            self.var.topwater = np.where(self.var.cropKC[No] > 0.75, self.var.topwater + availWaterInfiltration, self.var.topwater)

            # open water evaporation from the paddy field  - using potential evaporation from open water
            self.var.openWaterEvap[No] = np.minimum(np.maximum(0., self.var.topwater), self.var.EWRef)
            self.var.topwater = self.var.topwater  - self.var.openWaterEvap[No]

            # if paddies are flooded, avail water is calculated before: top + avail, otherwise it is calculated here
            availWaterInfiltration = np.where(self.var.cropKC[No] > 0.75, self.var.topwater, self.var.topwater + availWaterInfiltration)

            # open water can evaporate more than maximum bare soil + transpiration because it is calculated from open water pot evaporation
            #h = self.var.potBareSoilEvap - self.var.openWaterEvap[No]
            self.var.potBareSoilEvap = np.maximum(0.,self.var.potBareSoilEvap - self.var.openWaterEvap[No])
            # if open water revaporation is bigger than bare soil, transpiration rate is reduced
            # self.var.potTranspiration[No] = np.where( h > 0, self.var.potTranspiration[No], np.maximum(0.,self.var.potTranspiration[No] + h))

        else:
            self.var.openWaterEvap[No] = 0.



        #if (dateVar['curr'] >= 0) and (No==3):
        #    ii=1

        # add capillary rise from groundwater if modflow is used
        if self.var.modflow:
            ### if GW capillary rise saturates soil layers, water is sent to the above layer, then to runoff
            self.var.w3[No] = self.var.w3[No] + self.var.capillar
            # CAPRISE from GW to soilayer 3 , if this is full it is send to soil layer 2
            self.var.w2[No] = self.var.w2[No] + np.where(self.var.w3[No] > self.var.ws3[No], self.var.w3[No] - self.var.ws3[No], 0)
            self.var.w3[No] = np.minimum(self.var.ws3[No], self.var.w3[No])
            # CAPRISE from GW to soilayer 2 , if this is full it is send to soil layer 1
            self.var.w1[No] = self.var.w1[No] + np.where(self.var.w2[No] > self.var.ws2[No], self.var.w2[No] - self.var.ws2[No], 0)
            self.var.w2[No] = np.minimum(self.var.ws2[No], self.var.w2[No])
            # CAPRISE from GW to soilayer 1 , if this is full it is send to RUNOFF
            saverunofffromGW = + np.where(self.var.w1[No] > self.var.ws1[No], self.var.w1[No] - self.var.ws1[No], 0)
            self.var.w1[No]= np.minimum(self.var.ws1[No], self.var.w1[No])

        # ---------------------------------------------------------
        # calculate transpiration
        # ***** SOIL WATER STRESS ************************************

        etpotMax = np.minimum(0.1 * (self.var.totalPotET[No] * 1000.), 1.0)
        # to avoid a strange behaviour of the p-formula's, ETRef is set to a maximum of 10 mm/day.

        if coverType == 'irrPaddy' or coverType == 'irrNonPaddy':

            p = 1 / (0.76 + 1.5 * etpotMax) - 0.4
            # soil water depletion fraction (easily available soil water) # Van Diepen et al., 1988: WOFOST 6.0, p.87.
            p = p + (etpotMax - 0.6) / 4
            # correction for crop group 1  (Van Diepen et al, 1988) -> p between 0.14 - 0.77
            # The crop group number is a indicator of adaptation to dry climate,
            # e.g. olive groves are adapted to dry climate, therefore they can extract more water from drying out soil than e.g. rice.
            # The crop group number of olive groves is 4 and of rice fields is 1
            # for irrigation it is expected that the crop has a low adaptation to dry climate
        else:

            p = 1 / (0.76 + 1.5 * etpotMax) - 0.10 * (5 - self.var.cropGroupNumber)
            # soil water depletion fraction (easily available soil water)
            # Van Diepen et al., 1988: WOFOST 6.0, p.87
            # to avoid a strange behaviour of the p-formula's, ETRef is set to a maximum of
            # 10 mm/day. Thus, p will range from 0.15 to 0.45 at ETRef eq 10 and
            # CropGroupNumber 1-5
            p = np.where(self.var.cropGroupNumber <= 2.5, p + (etpotMax - 0.6) / (self.var.cropGroupNumber * (self.var.cropGroupNumber + 3)), p)
            # correction for crop groups 1 and 2 (Van Diepen et al, 1988)

        p = np.maximum(np.minimum(p, 1.0), 0.)
        # p is between 0 and 1 => if p =1 wcrit = wwp, if p= 0 wcrit = wfc
        # p is closer to 0 if evapo is bigger and cropgroup is smaller

        wCrit1 = ((1 - p) * (self.var.wfc1[No] - self.var.wwp1[No])) + self.var.wwp1[No]
        wCrit2 = ((1 - p) * (self.var.wfc2[No] - self.var.wwp2[No])) + self.var.wwp2[No]
        wCrit3 = ((1 - p) * (self.var.wfc3[No] - self.var.wwp3[No])) + self.var.wwp3[No]

        # Transpiration reduction factor (in case of water stress)
        rws1 = divideValues((self.var.w1[No] - self.var.wwp1[No]),(wCrit1 - self.var.wwp1[No]), default = 1.)
        rws2 = divideValues((self.var.w2[No] - self.var.wwp2[No]), (wCrit2 - self.var.wwp2[No]), default=1.)
        rws3 = divideValues((self.var.w3[No] - self.var.wwp3[No]), (wCrit3 - self.var.wwp3[No]), default=1.)

        #with np.errstate(invalid='ignore', divide='ignore'):
        #rws1 = np.where((wCrit1 - self.var.wwp1[No]) > 0, (self.var.w1[No] - self.var.wwp1[No]) / (wCrit1 - self.var.wwp1[No]), 1.0)
        #rws2 = np.where((wCrit2 - self.var.wwp2[No]) > 0, (self.var.w2[No] - self.var.wwp2[No]) / (wCrit2 - self.var.wwp2[No]), 1.0)
        #rws3 = np.where((wCrit3 - self.var.wwp3[No]) > 0, (self.var.w3[No] - self.var.wwp3[No]) / (wCrit3 - self.var.wwp3[No]), 1.0)

        rws1 = np.maximum(np.minimum(1., rws1), 0.) * self.var.adjRoot[0][No]
        rws2 = np.maximum(np.minimum(1., rws2), 0.) * self.var.adjRoot[1][No]
        rws3 = np.maximum(np.minimum(1., rws3), 0.) * self.var.adjRoot[2][No]
        self.var.rws = rws1 + rws2 + rws3


        TaMax = self.var.potTranspiration[No] * self.var.rws
        # transpiration is 0 when soil is frozen
        TaMax = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, 0., TaMax)

        ta1 = np.maximum(np.minimum(TaMax * self.var.adjRoot[0][No], self.var.w1[No] - self.var.wwp1[No]), 0.0)
        ta2 = np.maximum(np.minimum(TaMax * self.var.adjRoot[1][No], self.var.w2[No] - self.var.wwp2[No]), 0.0)
        ta3 = np.maximum(np.minimum(TaMax * self.var.adjRoot[2][No], self.var.w3[No] - self.var.wwp3[No]), 0.0)

        #if (dateVar['curr'] == 23) and (No==1):
        #    ii=1
        #   #print ('t', self.var.w1[No][0:3])

        self.var.w1[No] = self.var.w1[No] - ta1
        self.var.w2[No] = self.var.w2[No] - ta2
        self.var.w3[No] = self.var.w3[No] - ta3


        # -------------------------------------------------------------
        # Actual potential bare soil evaporation - upper layer
        self.var.actBareSoilEvap[No] = np.minimum(self.var.potBareSoilEvap,np.maximum(0.,self.var.w1[No] - self.var.wres1[No]))
        self.var.actBareSoilEvap[No] = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, 0., self.var.actBareSoilEvap[No])

        # no bare soil evaporation in the inundated paddy field
        if coverType == 'irrPaddy':
            self.var.actBareSoilEvap[No] = np.where(self.var.topwater > 0., 0., self.var.actBareSoilEvap[No])

        self.var.w1[No] = self.var.w1[No] - self.var.actBareSoilEvap[No]


        # -------------------------------------------------------------

        # Infiltration capacity
        #  ========================================
        # first 2 soil layers to estimate distribution between runoff and infiltration
        soilWaterStorage =  self.var.w1[No] + self.var.w2[No]
        soilWaterStorageCap = self.var.ws1[No] + self.var.ws2[No]
        relSat = soilWaterStorage / soilWaterStorageCap
        relSat = np.minimum(relSat, 1.0)

        #if np.min(self.var.w1[No])< 0.:
        #   ii =1

        #if (dateVar['curr'] == 23) and (No==1):
        #    ii=1
        #    print (No, self.var.w1[No][0:3])

        satAreaFrac = 1 - (1 - relSat) ** self.var.arnoBeta[No]
        # Fraction of pixel that is at saturation as a function of
        # the ratio Theta1/ThetaS1. Distribution function taken from
        # Zhao,1977, as cited in Todini, 1996 (JoH 175, 339-382)
        satAreaFrac = np.maximum(np.minimum(satAreaFrac, 1.0), 0.0)

        store = soilWaterStorageCap / (self.var.arnoBeta[No] + 1)
        potBeta = (self.var.arnoBeta[No] + 1) / self.var.arnoBeta[No]
        potInf = store - store * (1 - (1 - satAreaFrac) ** potBeta)




        # ------------------------------------------------------------------
        # calculate preferential flow

        if coverType == 'irrPaddy' or not(checkOption('preferentialFlow')):
            self.var.prefFlow[No] = 0.
        else:
            self.var.prefFlow[No] = availWaterInfiltration * relSat ** self.var.cPrefFlow
            self.var.prefFlow[No] = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, 0.0, self.var.prefFlow[No])

        # ---------------------------------------------------------
        # calculate infiltration
        # infiltration, limited with KSat1 and available water in topWaterLayer
        self.var.infiltration[No] = np.minimum(potInf, availWaterInfiltration - self.var.prefFlow[No])
        self.var.infiltration[No] = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, 0.0, self.var.infiltration[No])
        self.var.directRunoff[No] = np.maximum(0.,availWaterInfiltration - self.var.infiltration[No] - self.var.prefFlow[No])

        if coverType == 'irrPaddy':
            self.var.topwater = np.maximum(0.,  self.var.topwater - self.var.infiltration[No])
            # if paddy fields flooded only runoff if topwater > 0.05m
            h = np.maximum(0., self.var.topwater- self.var.maxtopwater)
            self.var.directRunoff[No] = np.where(self.var.cropKC[No] > 0.75, h, self.var.directRunoff[No])
            self.var.topwater = np.maximum(0., self.var.topwater - self.var.directRunoff[No])


        ### ModFlow
        if self.var.modflow:
            self.var.directRunoff[No]=self.var.directRunoff[No] + saverunofffromGW
            # ADDING EXCESS WATER FROM GW CAPILLARY RISE


        # infiltration to soilayer 1 , if this is full it is send to soil layer 2
        self.var.w1[No] = self.var.w1[No] + self.var.infiltration[No]
        self.var.w2[No] = self.var.w2[No] + np.where(self.var.w1[No] > self.var.ws1[No], self.var.w1[No] - self.var.ws1[No], 0)
        self.var.w1[No] = np.minimum(self.var.ws1[No], self.var.w1[No])


        ## ----------------------------------------------------------
        # to the water demand module  # could not be done before from landcoverType_module because readAvlWater is needed

        # for plants availailabe water
        #availWaterPlant1 = np.maximum(0., self.var.w1[No] - self.var.wwp1[No]) * self.var.rootDepth[0][No]
        #availWaterPlant2 = np.maximum(0., self.var.w2[No] - self.var.wwp2[No]) * self.var.rootDepth[1][No]
        #availWaterPlant3 = np.maximum(0., self.var.w3[No] - self.var.wwp3[No]) * self.var.rootDepth[2][No]
        #self.var.readAvlWater = availWaterPlant1 + availWaterPlant2 + availWaterPlant3





        # Percolation -----------------------------------------------
        if No == 0:
            NoSoil = 0
        else:
            NoSoil = 1

        # Available water in both soil layers [m]
        availWater1 = np.maximum(0.,self.var.w1[No] - self.var.wres1[No])
        availWater2 = np.maximum(0.,self.var.w2[No] - self.var.wres2[No])
        availWater3 = np.maximum(0.,self.var.w3[No] - self.var.wres3[No])


        satTerm2 = availWater2 / self.var.wrange2[No]
        satTerm3 = availWater3 / self.var.wrange3[No]

        # Saturation term in Van Genuchten equation (always between 0 and 1)
        satTerm2 = np.maximum(np.minimum(satTerm2, 1.0), 0)
        satTerm3 = np.maximum(np.minimum(satTerm3, 1.0), 0)

        # Unsaturated conductivity
        kUnSat2 = self.var.KSat2[NoSoil] * np.sqrt(satTerm2) * np.square(1 - (1 - satTerm2 ** self.var.genuInvM2[NoSoil]) ** self.var.genuM2[NoSoil])
        kUnSat3 = self.var.KSat3[NoSoil] * np.sqrt(satTerm3) * np.square(1 - (1 - satTerm3 ** self.var.genuInvM3[NoSoil]) ** self.var.genuM3[NoSoil])



        ## ----------------------------------------------------------
        # Capillar Rise

        #head1 = np.where(satTerm1 > 0.,self.var.invAlpha1[NoSoil] * ((1 / satTerm1) ** self.var.genuInvM1[NoSoil] - 1) ** self.var.genuInvN1[NoSoil],1E+7)
        #head2 = np.where(satTerm2 > 0.,self.var.invAlpha2[NoSoil] * ((1 / satTerm2) ** self.var.genuInvM2[NoSoil] - 1) ** self.var.genuInvN2[NoSoil],1E+7)
        #head3 = np.where(satTerm3 > 0.,self.var.invAlpha3[NoSoil] * ((1 / satTerm3) ** self.var.genuInvM3[NoSoil] - 1) ** self.var.genuInvN3[NoSoil],1E+7)

        #gradient1 = np.maximum(0., 2. * (head1 - head2) / (self.var.rootDepth[0][No] + self.var.rootDepth[1][No]) - 1.)
        #gradient2 = np.maximum(0., 2. * (head2 - head3) / (self.var.rootDepth[1][No] + self.var.rootDepth[2][No]) - 1.)
        #gradient3 = np.maximum(0., head3 / (self.var.rootDepth[2][No]))

        satTermFC1 = np.maximum(0., self.var.w1[No] - self.var.wres1[No]) / (self.var.wfc1[No] - self.var.wres1[No])
        satTermFC2 = np.maximum(0., self.var.w2[No] - self.var.wres2[No]) / (self.var.wfc2[No] - self.var.wres2[No])
        satTermFC3 = np.maximum(0., self.var.w3[No] - self.var.wres3[No]) / (self.var.wfc3[No] - self.var.wres3[No])
        capRise1 = np.minimum(np.maximum(0., (1 - satTermFC1) * kUnSat2), self.var.kunSatFC12[No])
        capRise2 = np.minimum(np.maximum(0., (1 - satTermFC2) * kUnSat3), self.var.kunSatFC23[No])


        if self.var.modflow:
            # from Modflow
            self.var.capRiseFromGW[No] = self.var.capillar
        else:
            self.var.capRiseFromGW[No] = np.maximum(0., (1 - satTermFC3) * np.sqrt(self.var.KSat3[NoSoil] * kUnSat3))
            self.var.capRiseFromGW[No] = 0.5 * self.var.capRiseFrac * self.var.capRiseFromGW[No]
            self.var.capRiseFromGW[No] = np.minimum(np.maximum(0., self.var.storGroundwater), self.var.capRiseFromGW[No])

        self.var.w1[No] = self.var.w1[No] + capRise1
        self.var.w2[No] = self.var.w2[No] - capRise1 + capRise2
        if self.var.modflow:
            self.var.w3[No] = self.var.w3[No] - capRise2
            # GW capillary rise has already been added to the soil
        else:
            self.var.w3[No] = self.var.w3[No] - capRise2 + self.var.capRiseFromGW[No]

        # Percolation -----------------------------------------------
        # Available water in both soil layers [m]
        availWater1 = np.maximum(0.,self.var.w1[No] - self.var.wres1[No])
        availWater2 = np.maximum(0.,self.var.w2[No] - self.var.wres2[No])
        availWater3 = np.maximum(0.,self.var.w3[No] - self.var.wres3[No])

        # Available storage capacity in subsoil
        capLayer2 = self.var.ws2[No] - self.var.w2[No]
        capLayer3 = self.var.ws3[No] - self.var.w3[No]

        satTerm1 = availWater1 / self.var.wrange1[No]
        satTerm2 = availWater2 / self.var.wrange2[No]
        satTerm3 = availWater3 / self.var.wrange3[No]

        # Saturation term in Van Genuchten equation (always between 0 and 1)
        satTerm1 = np.maximum(np.minimum(satTerm1, 1.0), 0)
        satTerm2 = np.maximum(np.minimum(satTerm2, 1.0), 0)
        satTerm3 = np.maximum(np.minimum(satTerm3, 1.0), 0)

        # Unsaturated conductivity
        kUnSat1 = self.var.KSat1[NoSoil] * np.sqrt(satTerm1) * np.square(1 - (1 - satTerm1 ** self.var.genuInvM1[NoSoil]) ** self.var.genuM1[NoSoil])
        kUnSat2 = self.var.KSat2[NoSoil] * np.sqrt(satTerm2) * np.square(1 - (1 - satTerm2 ** self.var.genuInvM2[NoSoil]) ** self.var.genuM2[NoSoil])
        kUnSat3 = self.var.KSat3[NoSoil] * np.sqrt(satTerm3) * np.square(1 - (1 - satTerm3 ** self.var.genuInvM3[NoSoil]) ** self.var.genuM3[NoSoil])

        """
        # Courant condition for computed soil moisture fluxes:
        # if Courant gt CourantCrit: sub-steps needed for required numerical accuracy
        with np.errstate(invalid='ignore', divide='ignore'):
            courant1to2 =  np.where(availWater1 == 0, 0, kUnSat1 / availWater1)
            courant2to3 =  np.where(availWater2 == 0, 0, kUnSat2 / availWater2)
            courant3toGW = np.where(availWater3 == 0, 0, kUnSat3 / availWater3)

        # Flow between soil layers and flow to GW
        # need to be numerically stable, so number of sub-steps is
        # based on process with largest Courant number
        courantSoil = np.maximum(courant1to2, courant2to3, courant3toGW)
        # Number of sub-steps needed for required numerical
        # accuracy. Always greater than or equal to 1
        # Do not change, default value of 2.5. Generally combines sufficient numerical accuracy within a  limited number of sub - steps
        NoSubS = np.maximum(1, np.ceil(courantSoil * 2.5))
        self.var.NoSubSteps = int(np.nanmax(NoSubS))
        """

        self.var.NoSubSteps = 3
        DtSub = 1. / self.var.NoSubSteps


        # Copy current value of W1 and W2 to temporary variables,
        # because computed fluxes may need correction for storage
        # capacity of subsoil and in case soil is frozen (after loop)
        wtemp1 = self.var.w1[No].copy()
        wtemp2 = self.var.w2[No].copy()
        wtemp3 = self.var.w3[No].copy()

        # Initialize top- to subsoil flux (accumulated value for all sub-steps)
        # Initialize fluxes out of subsoil (accumulated value for all sub-steps)
        self.var.perc1to2[No] = 0
        self.var.perc2to3[No] = 0
        self.var.perc3toGW[No] = 0

        # Start iterating

        for i in range(self.var.NoSubSteps):
            if i > 0:
                # Saturation term in Van Genuchten equation
                satTerm1 = np.maximum(0., wtemp1 - self.var.wres1[No])/ self.var.wrange1[No]
                satTerm2 = np.maximum(0., wtemp2 - self.var.wres2[No]) / self.var.wrange2[No]
                satTerm3 = np.maximum(0., wtemp3 - self.var.wres3[No]) / self.var.wrange3[No]

                satTerm1 = np.maximum(np.minimum(satTerm1, 1.0), 0)
                satTerm2 = np.maximum(np.minimum(satTerm2, 1.0), 0)
                satTerm3 = np.maximum(np.minimum(satTerm3, 1.0), 0)

                # Unsaturated hydraulic conductivities
                kUnSat1 = self.var.KSat1[NoSoil] * np.sqrt(satTerm1) * np.square(1 - (1 - satTerm1 ** self.var.genuInvM1[NoSoil]) ** self.var.genuM1[NoSoil])
                kUnSat2 = self.var.KSat2[NoSoil] * np.sqrt(satTerm2) * np.square(1 - (1 - satTerm2 ** self.var.genuInvM2[NoSoil]) ** self.var.genuM2[NoSoil])
                kUnSat3 = self.var.KSat3[NoSoil] * np.sqrt(satTerm3) * np.square(1 - (1 - satTerm3 ** self.var.genuInvM3[NoSoil]) ** self.var.genuM3[NoSoil])

            # Flux from top- to subsoil
            subperc1to2 =  np.minimum(availWater1,np.minimum(kUnSat1 * DtSub, capLayer2))
            subperc2to3 =  np.minimum(availWater2,np.minimum(kUnSat2 * DtSub, capLayer3))
            subperc3toGW = np.minimum(availWater3,np.minimum(kUnSat3 * DtSub, availWater3))

            # Update water balance for all layers
            availWater1 = availWater1 - subperc1to2
            availWater2 = availWater2 + subperc1to2 - subperc2to3
            availWater3 = availWater3 + subperc2to3 - subperc3toGW
            # Update WTemp1 and WTemp2

            wtemp1 = availWater1 + self.var.wres1[No]
            wtemp2 = availWater2 + self.var.wres2[No]
            wtemp3 = availWater3 + self.var.wres3[No]

            # Update available storage capacity in layer 2,3
            capLayer2 = self.var.ws2[No] - wtemp2
            capLayer3 = self.var.ws3[No] - wtemp3

            self.var.perc1to2[No]  += subperc1to2
            self.var.perc2to3[No]  += subperc2to3
            self.var.perc3toGW[No] += subperc3toGW

        # When the soil is frozen (frostindex larger than threshold), no perc1 and 2
        self.var.perc1to2[No] = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, 0,self.var.perc1to2[No])
        self.var.perc2to3[No] = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, 0,self.var.perc2to3[No])

        # Update soil moisture
        self.var.w1[No] = self.var.w1[No] - self.var.perc1to2[No]
        self.var.w2[No] = self.var.w2[No] + self.var.perc1to2[No] - self.var.perc2to3[No]
        self.var.w3[No] = self.var.w3[No] + self.var.perc2to3[No] - self.var.perc3toGW[No]

        # Compute the amount of water that could not infiltrate and add this water to the surface runoff
       # self.var.infiltration[No] = self.var.infiltration[No] - np.maximum(self.var.w1[No] - self.var.ws1[No], 0.0)
       # self.var.directRunoff[No] = self.var.directRunoff[No] + np.maximum(self.var.w1[No] - self.var.ws1[No], 0.0)
       # self.var.w1[No] = np.minimum(self.var.w1[No], self.var.ws1[No])

        self.var.theta1[No] = self.var.w1[No] / self.var.rootDepth[0][No]
        self.var.theta2[No] = self.var.w2[No] / self.var.rootDepth[1][No]
        self.var.theta3[No] = self.var.w3[No] / self.var.rootDepth[2][No]







        # ---------------------------------------------------------------------------------------------
        # Calculate interflow
        #self.var.interflow[No] = self.var.percolationImp * (perc[1] + self.var.capRiseFromGW[No] - (self.var.perc3toGW[No] + capRise[1]))
        #self.var.interflow[No] = np.maximum(0.0, self.var.interflow[No])






        # total actual transpiration
        #self.var.actTransTotal[No] = actTrans[0] + actTrans[1] + actTrans[2]
        #self.var.actTransTotal[No] =  np.sum(actTrans, axis=0)
        self.var.actTransTotal[No] = ta1 + ta2 + ta3

        self.var.before = self.var.actualET[No].copy()

        # total actual evaporation + transpiration
        self.var.actualET[No] = self.var.actualET[No] + self.var.actBareSoilEvap[No] + self.var.openWaterEvap[No] + self.var.actTransTotal[No]
        #self.var.actualET[No] = self.var.actualET[No] + self.var.actBareSoilEvap[No] + self.var.actTransTotal[No]


        #  actual evapotranspiration can be bigger than pot, because openWater is taken from pot open water evaporation, therefore self.var.totalPotET[No] is adjusted
        self.var.totalPotET[No] = np.maximum(self.var.totalPotET[No], self.var.actualET[No])


        # net percolation between upperSoilStores (positive indicating downward direction)
        #elf.var.netPerc[No] = perc[0] - capRise[0]
        #self.var.netPercUpper[No] = perc[1] - capRise[1]

        # groundwater recharge
        #self.var.gwRecharge[No] = self.var.perc3toGW[No] - self.var.capRiseFromGW[No] + self.var.prefFlow[No]
        toGWorInterflow = self.var.perc3toGW[No] + self.var.prefFlow[No]
        self.var.interflow[No] = self.var.percolationImp * toGWorInterflow

        if self.var.modflow:
            self.var.gwRecharge[No] = (1 - self.var.percolationImp) * toGWorInterflow
        else:
            self.var.gwRecharge[No] = (1 - self.var.percolationImp) * toGWorInterflow - self.var.capRiseFromGW[No]




        # landSurfaceRunoff (needed for routing)
        #self.var.landSurfaceRunoff[No] = self.var.directRunoff[No] + self.var.interflowTotal[No]

        #if (dateVar['curr'] == 121) and (No==2):
        #    ii=1
        """
        if checkOption('calcWaterBalance'):
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.availWaterInfiltration[No], self.var.capRiseFromGW[No], self.var.irrConsumption[No]],  # In  water demand included in availwater
                [self.var.directRunoff[No],self.var.perc3toGW[No], self.var.prefFlow[No] ,
                 self.var.actTransTotal[No], self.var.actBareSoilEvap[No], self.var.openWaterEvap[No]],  # Out
                [ preStor1, preStor2, preStor3,pretopwater],  # prev storage
                [self.var.w1[No], self.var.w2[No], self.var.w3[No],self.var.topwater],
                "Soil_1_"+str(No), False)


        if checkOption('calcWaterBalance'):
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.availWaterInfiltration[No], self.var.irrConsumption[No]],  # In
                [self.var.directRunoff[No], self.var.interflow[No],self.var.gwRecharge[No],
                 self.var.actTransTotal[No], self.var.actBareSoilEvap[No], self.var.openWaterEvap[No]],  # Out
                [ preStor1, preStor2, preStor3,pretopwater],  # prev storage
                [self.var.w1[No], self.var.w2[No], self.var.w3[No],self.var.topwater],
                "Soil_2", False)
            # openWaterEvap in because it is taken from availWater directly, out because it taken out immediatly. It is not a soil process indeed

        if option['calcWaterBalance']:
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.availWaterInfiltration[No], self.var.irrConsumption[No],self.var.snowEvap,self.var.interceptEvap[No]],  # In
                [self.var.directRunoff[No], self.var.interflow[No],self.var.gwRecharge[No],
                 self.var.actualET[No]],  # Out
                [preStor1, preStor2, preStor3,pretopwater],  # prev storage
                [self.var.w1[No], self.var.w2[No], self.var.w3[No],self.var.topwater],
                "Soil_AllSoil", False)
        """




