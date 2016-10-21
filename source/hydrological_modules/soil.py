# -------------------------------------------------------------------------
# Name:        Soil module
# Purpose:
#
# Author:      PB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class soil(object):

    """
    # ************************************************************
    # ***** SOIL *****************************************
    # ************************************************************
    """

    def __init__(self, soil_variable):
        self.var = soil_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the soil module
        Tdo: might be necessary to cover all variables = put 0 instead of missing value
        """
        # --- Topography -----------------------------------------------------
        # maps of elevation attributes:
        # topoParams = 'tanslope', 'slopeLength', 'orographyBeta'
        self.var.soilLayers = 3

        self.var.tanslope = loadmap('tanslope')
        self.var.slopeLength = loadmap('slopeLength')
        self.var.orographyBeta = loadmap('orographyBeta')

        self.var.tanslope = np.maximum(self.var.tanslope, 0.00001)
        # setting slope >= 0.00001 to prevent 0 value

        # maps of relative elevation above flood plains
        dzRel = ['dzRel0001','dzRel0005',
                 'dzRel0010','dzRel0020','dzRel0030','dzRel0040','dzRel0050',
                 'dzRel0060','dzRel0070','dzRel0080','dzRel0090','dzRel0100']
        for i in dzRel:
            vars(self.var)[i] = readnetcdfWithoutTime(binding['relativeElevation'],i)

        # --- Soil -----------------------------------------------------
        # soil properties of FAO
        soilProperties = ['airEntryValue1', 'airEntryValue2', 'poreSizeBeta1', 'poreSizeBeta2', 'resVolWC1','resVolWC2','satVolWC1','satVolWC2',
                          'KSat1','KSat2','KSat1','percolationImp',
                          'clappAddCoeff', 'matricSuctionFC', 'matricSuction50', 'matricSuctionWP', 'maxGWCapRise']
        # with the last 5 being soil parameters which are single parameters & uniform for the entire domain
        for property in soilProperties:
            vars(self.var)[property] = loadmap(property)

        # set for 3 soil layers the soil propertiy variables
        soilpropertyToLayer = [('airEntry','airEntryValue'), ('satVol','satVolWC'), ('resVol','resVolWC'), ('poreSizeBeta','poreSizeBeta'),('kSat','KSat')]

        for layer,property  in soilpropertyToLayer:
            vars(self.var)[layer] = np.tile(globals.inZero, (self.var.soilLayers, 1))
            for soilLayer in xrange(self.var.soilLayers):
                # first 2 soils gets the attribute of soil property 1
                if soilLayer < 2: propertysuffix ='1'
                else: propertysuffix ='2'
                vars(self.var)[layer][soilLayer] = vars(self.var)[property+propertysuffix]

        soilProperties2 = ['campbellBeta', 'effSatAtFieldCap','kUnsatAtFieldCap','effSatAt50','effSatAtWiltPoint']
        for property in soilProperties2:
            vars(self.var)[property] = np.tile(globals.inZero, (self.var.soilLayers, 1))
        for i in xrange(self.var.soilLayers):
            # assign Campbell's (1974) beta coefficient, as well as degree
            # of saturation at field capacity and corresponding unsaturated hydraulic conductivity
            # calculate degree of saturation at which transpiration is halved (50)
            # and at wilting point

            self.var.campbellBeta[i] = 2. * self.var.poreSizeBeta[i] + self.var.clappAddCoeff
            self.var.effSatAtFieldCap[i] =  (self.var.matricSuctionFC / self.var.airEntry[i]) ** (-1 / self.var.poreSizeBeta[i])
            self.var.kUnsatAtFieldCap[i] = np.maximum(0.,self.var.effSatAtFieldCap[i] ** self.var.poreSizeBeta[i] * self.var.kSat[i])
            self.var.effSatAt50[i] = (self.var.matricSuction50 / self.var.airEntry[i]) ** (-1 / self.var.poreSizeBeta[i])
            self.var.effSatAtWiltPoint[i] = (self.var.matricSuctionWP / self.var.airEntry[i]) ** (-1 / self.var.poreSizeBeta[i])

        # calculate interflow parameter (TCL):
        self.var.interflowConcTime = (2. * self.var.kSat[2] * self.var.tanslope) /\
                                     (self.var.slopeLength * (1. - self.var.effSatAtFieldCap[2]) * \
                                     (self.var.satVol[2] - self.var.resVol[2]))


    # ------------ SOIL DEPTH ----------------------------------------------------------
        # soil thickness and storage

        soilDepthLayer = [('soildepth', 'SoilDepth'),('storCap','soilWaterStorageCap')]
        for layer,property  in soilDepthLayer:
            vars(self.var)[layer] = np.tile(globals.inZero, (self.var.soilLayers, 1))
        self.var.soildepth[0] = 0.05 / 0.30 * loadmap('firstStorDepth')
        self.var.soildepth[1] = 0.25 / 0.30 * loadmap('firstStorDepth')
        self.var.soildepth[2] = loadmap('secondStorDepth')
        for i in xrange(self.var.soilLayers):
            self.var.storCap[i] = self.var.soildepth[i] * (self.var.satVol[i] - self.var.resVol[i])
        self.var.rootZoneWaterStorageCap = np.sum(self.var.storCap,axis=0)
        i=1





# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self, coverType, No):

        def improvedArnoScheme(No,kUnsat2, iniWaterStorage, inputNetLqWaterToSoil, directRunoffReduction="Default"):
            # improvedArnoScheme(No, iniWaterStorage=self.var.soilWaterStorage[No], inputNetLqWaterToSoil=self.var.topWaterLayer[No])
            # arnoBeta = BCF = b coefficient of soil water storage capacity distribution
            #
            # WMIN = root zone water storage capacity, minimum values
            # WMAX = root zone water storage capacity, area-averaged values
            # W	   = actual water storage in root zone
            # WRANGE  = WMAX - WMIN
            # DW      = WMAX-W
            # WFRAC   = DW/WRANGE ; WFRAC capped at 1
            # WFRACB  = DW/WRANGE raised to the power (1/(b+1))
            # SATFRAC =	fractional saturated area
            # WACT    = actual water storage within rootzone

            Pn = iniWaterStorage +inputNetLqWaterToSoil                            # Pn = W[TYPE]+Pn;
            Pn = Pn - np.maximum(self.var.rootZoneWaterStorageMin[No], iniWaterStorage)    # Pn = Pn-max(WMIN[TYPE],W[TYPE]);

            soilWaterStorage = np.where(Pn < 0., self.var.rootZoneWaterStorageMin[No] + Pn, np.maximum(iniWaterStorage, self.var.rootZoneWaterStorageMin[No]))
            # W[TYPE]= if(Pn<0,WMIN[TYPE]+Pn,max(W[TYPE],WMIN[TYPE]));

            Pn = np.maximum(0., Pn)  # Pn = max(0,Pn);

            DW = np.maximum(0., self.var.rootZoneWaterStorageCap - soilWaterStorage)  # DW = max(0,WMAX[TYPE]-W[TYPE]);

            WFRAC = np.minimum(1.0, DW / self.var.rootZoneWaterStorageRange[No])  # WFRAC = min(1,DW/WRANGE[TYPE]);
            WFRACB = WFRAC ** (1. / (1. + self.var.arnoBeta[No]))  # WFRACB = WFRAC**(1/(1+BCF[TYPE]));

            satAreaFrac = np.where(WFRACB > 0., 1. - WFRACB ** self.var.arnoBeta[No], 0.)  # SATFRAC_L = if(WFRACB>0,1-WFRACB**BCF[TYPE],0);
            satAreaFrac = np.maximum(np.minimum(satAreaFrac, 1.0),0.0)

            actualW = (self.var.arnoBeta[No] + 1) * self.var.rootZoneWaterStorageCap - \
                       self.var.arnoBeta[No] * self.var.rootZoneWaterStorageMin[No] - \
                      (self.var.arnoBeta[No] + 1) * self.var.rootZoneWaterStorageRange[No] * WFRACB
            # WACT_L = (BCF[TYPE]+1)*WMAX[TYPE]- BCF[TYPE]*WMIN[TYPE]- (BCF[TYPE]+1)*WRANGE[TYPE]*WFRACB;


            if directRunoffReduction == "Default":
                directRunoffReduction = np.minimum(kUnsat2, np.sqrt(self.var.kUnsatAtFieldCap[2] * kUnsat2))
                # In order to maintain full saturation and
                # continuous groundwater recharge/percolation,
                # the amount of directRunoff may be reduced.
                # In this case, this reduction is estimated
                # based on (for two layer case) percLow = np.minimum(KUnSatLow, pcr.sqrt(parameters.KUnSatFC2*KUnSatLow))

            # directRunoff
            condition = (self.var.arnoBeta[No] + 1.) * self.var.rootZoneWaterStorageRange[No] * WFRACB

            """
            h1= Pn - (self.var.rootZoneWaterStorageCap + directRunoffReduction - soilWaterStorage)
            h2 = self.var.rootZoneWaterStorageRange[No] * (WFRACB - Pn /        ((self.var.arnoBeta[No] + 1.) * self.var.rootZoneWaterStorageRange[No]))

            #self.rootZoneWaterStorageRange * (self.WFRACB - Pn / ((self.arnoBeta + 1.) * self.rootZoneWaterStorageRange))

            h3 = (self.var.arnoBeta[No] + 1.)
            #report(decompress(self.var.arnoBeta[No]), "C:\work\output\h2.map")
            h4 = h2 ** h3
            h5 = np.where(Pn >= condition, 0.0, h4)
            """
            with np.errstate(invalid='ignore', divide='ignore'):
                directRunoff = np.maximum(0.0, Pn - (self.var.rootZoneWaterStorageCap + directRunoffReduction - soilWaterStorage) + \
                           np.where(Pn >= condition, 0.0, \
                           self.var.rootZoneWaterStorageRange[No] * (WFRACB - \
                           Pn / ((self.var.arnoBeta[No] + 1.) * self.var.rootZoneWaterStorageRange[No])) ** (self.var.arnoBeta[No] + 1.)))
            #    Q1_L[TYPE]= max(0,Pn-(WMAX[TYPE]+P2_L[TYPE]-W[TYPE])+
            #      if(Pn>=(BCF[TYPE]+1)*WRANGE[TYPE]*WFRACB, 0,
            #      WRANGE[TYPE]*(WFRACB-Pn/((BCF[TYPE]+1)*WRANGE[TYPE]))**(BCF[TYPE]+1))); #*
            return directRunoff, WFRACB, satAreaFrac


#---------------------------------------------------------
# ---------------------------------------------------------
        if option['calcWaterBalance']:
            preTopWaterLayer = self.var.topWaterLayer[No].copy()
            preStor1 = self.var.soilStor[0][No].copy()
            preStor2 = self.var.soilStor[1][No].copy()
            preStor3 = self.var.soilStor[2][No].copy()

        effSat = np.tile(globals.inZero, (self.var.soilLayers, 1))
        matricSuction = np.tile(globals.inZero, (self.var.soilLayers, 1))
        kUnsat = np.tile(globals.inZero, (self.var.soilLayers, 1))
        h = np.tile(globals.inZero, (self.var.soilLayers, 1))

        kThVert = np.tile(globals.inZero, (self.var.soilLayers-1, 1))
        gradient = np.tile(globals.inZero, (self.var.soilLayers - 1, 1))


        #if No ==1:
        #    print self.var.soilStor[0][1],self.var.soilStor[1][1], self.var.soilStor[2][1],
        #    if dateVar['currStart']==228:
        #        iii=1


        for j in xrange(self.var.soilLayers):
            effSat[j] = np.minimum(1.0, np.maximum(0., self.var.soilStor[j][No] / self.var.storCap[j]))
            matricSuction[j] = self.var.airEntry[j] * (np.maximum(0.01, effSat[j]) ** -self.var.poreSizeBeta[j])
            kUnsat[j] = np.maximum(0., (effSat[j] ** self.var.campbellBeta[j]) * self.var.kSat[j])
            kUnsat[j] = np.minimum(kUnsat[j], self.var.kSat[j])
            h[j] = np.maximum(0., effSat[j] - self.var.effSatAtWiltPoint[j]) *  (self.var.satVol[j] - self.var.resVol[j]) * self.var.rootDepth[j][No]

        self.var.soilWaterStorage[No] = np.maximum(0., self.var.soilStor[0][No] + self.var.soilStor[1][No] + self.var.soilStor[2][No])
        self.var.readAvlWater = np.sum(h, axis=0)
        self.var.readAvlWater = np.minimum(self.var.readAvlWater, self.var.soilWaterStorage[No])

        for j in xrange(self.var.soilLayers-1):
            kThVert[j]= np.minimum(np.sqrt(kUnsat[j] * kUnsat[j+1]), (kUnsat[j] * kUnsat[j+1] * self.var.kUnsatAtFieldCap[j] * self.var.kUnsatAtFieldCap[j+1]) ** 0.25)
            gradient[j] = np.maximum(0., 2. * (matricSuction[j] - matricSuction[j+1]) / (self.var.soildepth[j] + self.var.soildepth[j+1]) - 1.)


        ## ----------------------------------------------------------
        # to the water demand module
        # could not be done before from landcoverType_module because readAvlWater is needed
        self.var.waterdemand_module.dynamic_waterdemand(coverType, No)


        # -----------------------------------------------------------
        # calculate openWaterEvap: open water evaporation from the paddy field,
        # and update topWaterLayer after openWaterEvap.

        self.var.openWaterEvap[No] = 0
        if coverType == 'irrPaddy':
             # open water evaporation from the paddy field  - using potential evaporation from open water
            self.var.openWaterEvap[No] = np.minimum( np.maximum(0., self.var.topWaterLayer[No]), self.var.EWRef)

             # update potBareSoilEvap & potTranspiration (after openWaterEvap)
            with np.errstate(invalid='ignore', divide='ignore'):
                self.var.potBareSoilEvap[No]  = np.where(self.var.EWRef < 0.00001, 0.0, self.var.potBareSoilEvap[No] - (self.var.potBareSoilEvap[No]/self.var.EWRef) * self.var.openWaterEvap[No])
                self.var.potTranspiration[No] = np.where(self.var.EWRef < 0.00001, 0.0, self.var.potTranspiration[No]- (self.var.potTranspiration[No]/self.var.EWRef)* self.var.openWaterEvap[No])

            # update top water layer after openWaterEvap
            self.var.topWaterLayer[No] = np.maximum(0.,self.var.topWaterLayer[No] - self.var.openWaterEvap[No])

        # -----------------------------------------------------------
        # calculate directRunoff and infiltration, based on the improved Arno scheme (Hageman and Gates, 2003):
        # and update topWaterLayer (after directRunoff and infiltration).
             # update topWaterLayer (above soil)
             # with netLqWaterToSoil and irrGrossDemand

        self.var.topWaterLayer[No] = self.var.topWaterLayer[No] + np.maximum(0., self.var.availWaterInfiltration[No] + self.var.irrGrossDemand[No])
        # topwater = water net from precipitaion (- soil - interception - snow + snow melt) + water for irrigation
        # topWaterLater is partitioned into directRunoff (and infiltration)


        #=========================================
        # run Arno Scheme
        # ========================================
        self.var.directRunoff[No], WFRACB, satAreaFrac = improvedArnoScheme( No,kUnsat[2],
                    iniWaterStorage=self.var.soilWaterStorage[No], inputNetLqWaterToSoil=self.var.topWaterLayer[No])
        self.var.directRunoff[No] = np.minimum(self.var.topWaterLayer[No], self.var.directRunoff[No])

        # Yet, no directRunoff in the paddy field.
        if coverType == 'irrPaddy': self.var.directRunoff[No] = 0.

        # update topWaterLayer (above soil) after directRunoff
        self.var.topWaterLayer[No] = self.var.topWaterLayer[No] - self.var.directRunoff[No]



        # ---------------------------------------------------------
        # calculateInfiltration
        # infiltration, limited with KSat1 and available water in topWaterLayer
        self.var.infiltration[No] = np.minimum(self.var.topWaterLayer[No],self.var.kSat[0])
        # update top water layer after infiltration
        self.var.topWaterLayer[No] = self.var.topWaterLayer[No] - self.var.infiltration[No]

        # ---------------------------------------------------------
        #estimateTranspirationAndBareSoilEvap
        # TRANSPIRATION
        # - partitioning transpiration (based on actual each layer storage)

        transpFrac = np.tile(globals.inZero, (self.var.soilLayers, 1))
        actTrans = np.tile(globals.inZero, (self.var.soilLayers, 1))
        perc = np.tile(globals.inZero, (self.var.soilLayers, 1))
        capRise = np.tile(globals.inZero, (self.var.soilLayers, 1))

        dividerTranspFracs = np.maximum(1e-9, self.var.adjRoot[0][No] * self.var.soilStor[0][No] + \
                    self.var.adjRoot[1][No] * self.var.soilStor[1][No] + \
                    self.var.adjRoot[2][No] * self.var.soilStor[2][No])
        TotalSoilStor = self.var.soilStor[0][No] + self.var.soilStor[1][No] + self.var.soilStor[2][No]

        for j in xrange(self.var.soilLayers):
            transpFrac[j] = np.where(TotalSoilStor > 0., self.var.adjRoot[j][No] * self.var.soilStor[j][No] / dividerTranspFracs, self.var.adjRoot[j][No])


        # - relActTranspiration = fraction actual transpiration over potential transpiration
        relActTranspiration = (self.var.rootZoneWaterStorageCap  + self.var.arnoBeta[No]*self.var.rootZoneWaterStorageRange[No]*(1.- \
                    (1.+self.var.arnoBeta[No])/self.var.arnoBeta[No]* WFRACB)) / \
                    (self.var.rootZoneWaterStorageCap  + self.var.arnoBeta[No]*self.var.rootZoneWaterStorageRange[No]*(1.- WFRACB))
        relActTranspiration = (1.- satAreaFrac) / \
                    (1.+(np.maximum(0.01,relActTranspiration)/self.var.effSatAt50[No])**\
                    (self.var.effPoreSizeBetaAt50[No]* -3.0))

        relActTranspiration = np.minimum(1.0, np.maximum(0.0, relActTranspiration))

        # Actual potyential bare soil evaporation - upper layer
        self.var.actBareSoilEvap[No] = satAreaFrac * np.minimum( \
                    self.var.potBareSoilEvap[No], self.var.kSat[0]) + \
                    (1. - satAreaFrac) * np.minimum(self.var.potBareSoilEvap[No], kUnsat[0])

        # no bare soil evaporation in the inundated paddy field
        if coverType == 'irrPaddy':
                    self.var.actBareSoilEvap[No] = np.where(self.var.topWaterLayer[No] > 0.0, 0.0, self.var.actBareSoilEvap[No])

        # estimates of actual transpiration fluxes:
        for j in xrange(self.var.soilLayers):
            actTrans[j] = relActTranspiration * transpFrac[j]* self.var.potTranspiration[No]

        perc[0] = np.where(effSat[0] > self.var.effSatAtFieldCap[0],
                np.minimum(np.maximum(0., effSat[0] - self.var.effSatAtFieldCap[0]) * self.var.storCap[0], kThVert[0]), kThVert[0]) + \
                np.maximum(0., self.var.infiltration[No] - (self.var.storCap[0] - self.var.soilStor[0][No]))
        perc[1] = np.where(effSat[1] > self.var.effSatAtFieldCap[1],
                np.minimum(np.maximum(0., effSat[1] - self.var.effSatAtFieldCap[1]) * self.var.storCap[1], kThVert[1]), kThVert[1]) + \
                np.maximum(0.,  perc[0] - (self.var.storCap[1] - self.var.soilStor[1][No]))
        # - percolation from storLow030150 to storGroundwater (m)
        self.var.percToGW[No] = np.minimum(kUnsat[2], np.sqrt(self.var.kUnsatAtFieldCap[2] * kUnsat[2]))


        for j in xrange(self.var.soilLayers-1):
            capRise[j] = np.minimum(np.maximum(0., self.var.effSatAtFieldCap[j] - effSat[j]) * self.var.storCap[j], kThVert[j] * gradient[j])
        # - capillary rise to storLow030150 from storGroundwater (m)
        self.var.capRiseFromGW[No] = 0.5 * (satAreaFrac + self.var.capRiseFrac) * \
                    np.minimum((1. - effSat[2]) * np.sqrt(self.var.kSat[2] * \
                    kUnsat[2]), np.maximum(0.0, self.var.effSatAtFieldCap[2] - \

                    effSat[2]) * self.var.storCap[2])

        # - interflow (m)
        percToInterflow = self.var.percolationImp * (perc[1] + self.var.capRiseFromGW[No] - \
                    (self.var.percToGW[No] + capRise[1]))
        self.var.interflow[No] = np.maximum( self.var.interflowConcTime * percToInterflow + \
                    (1.0 - self.var.interflowConcTime) * self.var.interflow[No], 0.0)

        # ---------------------------------------------------------------------------------------------
        # estimateSoilFluxes(self, parameters, capRiseFrac):
        # Given states, we estimate all fluxes.
            # - percolation from first soil layer to second [0] -> [1] in [m]

        # ---------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------

        # scaleAllFluxes(self, parameters, groundwater):
        # re-scale all fluxes (based on available water).
        # ####################################################


        ADJUST = self.var.actBareSoilEvap[No] + actTrans[0] + perc[0]
        with np.errstate(invalid='ignore', divide='ignore'):
            ADJUST = np.where(ADJUST > 0.0, np.minimum(1.0, np.maximum(0.0, self.var.soilStor[0][No] + self.var.infiltration[No]) / ADJUST), 0.)
        self.var.actBareSoilEvap[No] = ADJUST * self.var.actBareSoilEvap[No]
        actTrans[0] = ADJUST * actTrans[0]
        perc[0] = ADJUST * perc[0]

        # scale fluxes for first layer [0]
        ADJUST = actTrans[1] + perc[1]
        with np.errstate(invalid='ignore', divide='ignore'):
            ADJUST = np.where(ADJUST > 0.0, np.minimum(1.0, np.maximum(0.0, self.var.soilStor[1][No] + perc[0]) / ADJUST), 0.)
        actTrans[1] = ADJUST * actTrans[1]
        perc[1] = ADJUST * perc[1]

        # scale fluxes for third layer [2]
        ADJUST = actTrans[2] + self.var.percToGW[No] + self.var.interflow[No]
        with np.errstate(invalid='ignore', divide='ignore'):
            ADJUST = np.where(ADJUST > 0.0, np.minimum(1.0, np.maximum(0.0, self.var.soilStor[2][No] + perc[1]) / ADJUST), 0.)
        actTrans[2] = ADJUST * actTrans[2]
        self.var.percToGW[No] = ADJUST * self.var.percToGW[No]
        self.var.interflow[No] = ADJUST * self.var.interflow[No]

        # capillary rise to storLow is limited to available storGroundwater
        # and also limited with reducedGroundWaterAbstraction
        self.var.capRiseFromGW[No] = np.maximum(0., np.minimum( \
                np.maximum(0., self.var.storGroundwater - self.var.reducedGroundWaterAbstraction), self.var.capRiseFromGW[No]))
        # capillary rise to storUpp005030 is limited to available storLow030150
        capRise[1] = np.minimum(np.maximum(0, self.var.soilStor[2][No] + perc[1] - \
                (actTrans[2] + self.var.percToGW[No] + self.var.interflow[No])),capRise[1])
        # capillary rise to first layer is limited to available water in second layer
        capRise[0] = np.minimum(np.maximum(0, self.var.soilStor[1][No] + perc[0] - \
                (actTrans[1] + perc[1])), capRise[0])

        # ---------------------------------------------------------------------------------------------
        # Give new states and make sure that no storage capacities will be exceeded.
        #################################################################################
        #
        self.var.soilStor[2][No] = np.maximum(0., self.var.soilStor[2][No] + perc[1] + self.var.capRiseFromGW[No] - \
                    (self.var.percToGW[No] + self.var.interflow[No] + actTrans[2] + capRise[1]))
        # If necessary, reduce percolation input:
        percH = perc[1].copy()
        perc[1] = np.maximum(0., perc[1] - np.maximum(0., self.var.soilStor[2][No] - self.var.storCap[2]))
        self.var.soilStor[2][No] = self.var.soilStor[2][No] - percH + perc[1]

        # If necessary, reduce capRise input:
        capRiseLowH = self.var.capRiseFromGW[No].copy()
        self.var.capRiseFromGW[No] = np.maximum(0., self.var.capRiseFromGW[No] - np.maximum(0., self.var.soilStor[2][No] - self.var.storCap[2]))
        self.var.soilStor[2][No] = self.var.soilStor[2][No] - capRiseLowH + self.var.capRiseFromGW[No]
        #
        # If necessary, increase interflow outflow:
        addInterflow = np.maximum(0., self.var.soilStor[2][No] - self.var.storCap[2])
        self.var.interflow[No] = self.var.interflow[No] + addInterflow
        self.var.soilStor[2][No] = self.var.soilStor[2][No] - addInterflow
        self.var.soilStor[2][No] = np.minimum(self.var.soilStor[2][No], self.var.storCap[2])

        # update storage in layer 2 [1] after the following fluxes:

        self.var.soilStor[1][No] = np.maximum(0., self.var.soilStor[1][No] + perc[0] + capRise[1] - \
                    (perc[1] + actTrans[1] + capRise[0]))
        # If necessary, reduce percolation input:
        percUppH = perc[0].copy()
        perc[0] = np.maximum(0., perc[0] - np.maximum(0., self.var.soilStor[1][No] - self.var.storCap[1]))
        self.var.soilStor[1][No] = self.var.soilStor[1][No] - percUppH + perc[0]

        # If necessary, reduce capRise input:
        capRiseUppH = capRise[1].copy()
        capRise[1] = np.maximum(0., capRise[1] - np.maximum(0., self.var.soilStor[1][No] - self.var.storCap[1]))
        self.var.soilStor[1][No] = self.var.soilStor[1][No] - capRiseUppH + capRise[1]

        # If necessary, introduce interflow outflow:
        interflow1 = np.maximum(0., self.var.soilStor[1][No] - self.var.storCap[1])
        self.var.soilStor[1][No] = self.var.soilStor[1][No] - interflow1

        # update storUpp000005 after the following fluxes:
        # + infiltration
        # + capRiseUpp000005
        # - percUpp000005
        # - actTranspiUpp000005
        # - actBareSoilEvap
        #
        self.var.soilStor[0][No] = np.maximum(0., self.var.soilStor[0][No] + self.var.infiltration[No] + capRise[0] - \
                    (perc[0] + actTrans[0] + self.var.actBareSoilEvap[No]))
        #
        # any excess above storCapUpp is handed to topWaterLayer
        satExcess = np.maximum(0., self.var.soilStor[0][No] - self.var.storCap[0])
        self.var.topWaterLayer[No] = self.var.topWaterLayer[No] + satExcess

        # any excess above minTopWaterLayer is released as directRunoff
        self.var.directRunoff[No] = self.var.directRunoff[No] + np.maximum(0., self.var.topWaterLayer[No] - self.var.minTopWaterLayer[No])

        # make sure that storage capacities are not exceeded
        self.var.topWaterLayer[No] = np.minimum(self.var.topWaterLayer[No], self.var.minTopWaterLayer[No])
        self.var.soilStor[0][No] = np.minimum(self.var.soilStor[0][No], self.var.storCap[0])
        self.var.soilStor[1][No] = np.minimum(self.var.soilStor[1][No], self.var.storCap[1])
        self.var.soilStor[2][No] = np.minimum(self.var.soilStor[2][No], self.var.storCap[2])

        # total actual transpiration
        actTranspiUpper = actTrans[0] + actTrans[1]
        self.var.actTransTotal[No] = actTranspiUpper + actTrans[2]

        # total actual evaporation + transpiration
        self.var.actualET[No] += self.var.actBareSoilEvap[No] + self.var.openWaterEvap[No] + self.var.actTransTotal[No]

        # net percolation between upperSoilStores (positive indicating downward direction)
        self.var.netPerc[No] = perc[0] - capRise[0]
        self.var.netPercUpper[No] = perc[1] - capRise[1]

        # groundwater recharge
        self.var.gwRecharge[No] = self.var.percToGW[No] - self.var.capRiseFromGW[No]

        # landSurfaceRunoff (needed for routing)
        self.var.interflowTotal[No] = self.var.interflow[No] + interflow1
        self.var.landSurfaceRunoff[No] = self.var.directRunoff[No] + self.var.interflowTotal[No]


        if option['calcWaterBalance']:
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.availWaterInfiltration[No],self.var.capRiseFromGW[No], self.var.irrGrossDemand[No]],                             # In
                [self.var.directRunoff[No],self.var.interflowTotal[No], self.var.percToGW[No], \
                 self.var.actTransTotal[No], \
                 self.var.actBareSoilEvap[No],self.var.openWaterEvap[No]],                                                                # Out
                [preTopWaterLayer,preStor1,preStor2,preStor3],                                       # prev storage
                [self.var.topWaterLayer[No],self.var.soilStor[0][No],self.var.soilStor[1][No],self.var.soilStor[2][No]],
                "Soil_AllSoil", False)
        i = 1
