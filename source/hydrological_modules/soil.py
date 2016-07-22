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
        self.var.airEntryValue1 = loadmap('airEntryValue1')
        self.var.airEntryValue2 = loadmap('airEntryValue2')
        self.var.poreSizeBeta1  = loadmap('poreSizeBeta1')
        self.var.poreSizeBeta2  = loadmap('poreSizeBeta2')
        self.var.resVolWC1      = loadmap('resVolWC1')
        self.var.resVolWC2      = loadmap('resVolWC2')
        self.var.satVolWC1      = loadmap('satVolWC1')
        self.var.satVolWC2      = loadmap('satVolWC2')
        self.var.KSat1 = loadmap('KSat1')
        self.var.KSat2 = loadmap('KSat2')
        self.var.percolationImp = loadmap('percolationImp')

        # soil parameters which are constant / uniform for the entire domain
        self.var.clappAddCoeff = loadmap('clappAddCoeff')
        self.var.matricSuctionFC = loadmap('matricSuctionFC')
        self.var.matricSuction50 = loadmap('matricSuction50')
        self.var.matricSuctionWP = loadmap('matricSuctionWP')
        self.var.maxGWCapRise = loadmap('maxGWCapRise')

        #  ----- some calculation ----------------------------------------
        # set for 3 soil layers the soil propertiy variables
        # they are linked not hard copied!
        self.var.satVolMoistContUpp000005 = self.var.satVolWC1
        self.var.satVolMoistContUpp005030 = self.var.satVolWC1
        self.var.satVolMoistContLow030150 = self.var.satVolWC2
        self.var.resVolMoistContUpp000005 = self.var.resVolWC1
        self.var.resVolMoistContUpp005030 = self.var.resVolWC1
        self.var.resVolMoistContLow030150 = self.var.resVolWC2
        self.var.airEntryValueUpp000005 = self.var.airEntryValue1
        self.var.airEntryValueUpp005030 = self.var.airEntryValue1
        self.var.airEntryValueLow030150 = self.var.airEntryValue2
        self.var.poreSizeBetaUpp000005 = self.var.poreSizeBeta1
        self.var.poreSizeBetaUpp005030 = self.var.poreSizeBeta1
        self.var.poreSizeBetaLow030150 = self.var.poreSizeBeta2
        self.var.kSatUpp000005 = self.var.KSat1
        self.var.kSatUpp005030 = self.var.KSat1
        self.var.kSatLow030150 = self.var.KSat2

        # assign Campbell's (1974) beta coefficient, as well as degree
        # of saturation at field capacity and corresponding unsaturated hydraulic conductivity

        self.var.campbellBetaUpp000005 = 2. * self.var.poreSizeBetaUpp000005 + self.var.clappAddCoeff
        self.var.campbellBetaUpp005030 = 2. * self.var.poreSizeBetaUpp005030 + self.var.clappAddCoeff
        self.var.campbellBetaLow030150 = 2. * self.var.poreSizeBetaLow030150 + self.var.clappAddCoeff
        self.var.effSatAtFieldCapUpp000005 =  (self.var.matricSuctionFC / self.var.airEntryValueUpp000005) ** \
                 (-1 / self.var.poreSizeBetaUpp000005)
        self.var.effSatAtFieldCapUpp005030 = (self.var.matricSuctionFC / self.var.airEntryValueUpp005030) ** \
                 (-1 / self.var.poreSizeBetaUpp005030)
        self.var.effSatAtFieldCapLow030150 = (self.var.matricSuctionFC / self.var.airEntryValueLow030150) ** \
                 (-1 / self.var.poreSizeBetaLow030150)

        self.var.kUnsatAtFieldCapUpp000005 = np.maximum(0., self.var.effSatAtFieldCapUpp000005 ** self.var.poreSizeBetaUpp000005 * self.var.kSatUpp000005)
        self.var.kUnsatAtFieldCapUpp005030 = np.maximum(0., self.var.effSatAtFieldCapUpp005030 ** self.var.poreSizeBetaUpp005030 * self.var.kSatUpp005030)
        self.var.kUnsatAtFieldCapLow030150 = np.maximum(0., self.var.effSatAtFieldCapLow030150 ** self.var.poreSizeBetaLow030150 * self.var.kSatLow030150)

        # calculate degree of saturation at which transpiration is halved (50)
        # and at wilting point
        self.var.effSatAt50Upp000005 = (self.var.matricSuction50 / self.var.airEntryValueUpp000005) ** (-1 / self.var.poreSizeBetaUpp000005)

        self.var.effSatAt50Upp005030 = (self.var.matricSuction50 / self.var.airEntryValueUpp005030) ** (-1 / self.var.poreSizeBetaUpp005030)
        self.var.effSatAt50Low030150 = (self.var.matricSuction50 / self.var.airEntryValueLow030150) ** (-1 / self.var.poreSizeBetaLow030150)
        self.var.effSatAtWiltPointUpp000005 = (self.var.matricSuctionWP / self.var.airEntryValueUpp000005) ** (-1 / self.var.poreSizeBetaUpp000005)
        self.var.effSatAtWiltPointUpp005030 = (self.var.matricSuctionWP / self.var.airEntryValueUpp005030) ** (-1 / self.var.poreSizeBetaUpp005030)
        self.var.effSatAtWiltPointLow030150 =  (self.var.matricSuctionWP / self.var.airEntryValueLow030150) ** (-1 / self.var.poreSizeBetaLow030150)

        # calculate interflow parameter (TCL):
        self.var.interflowConcTime = (2. * self.var.kSatLow030150 * self.var.tanslope) /\
                                     (self.var.slopeLength * (1. - self.var.effSatAtFieldCapLow030150) * \
                                     (self.var.satVolMoistContLow030150 - self.var.resVolMoistContLow030150))

        #self.var.interflowConcTime = pcr.cover(self.var.interflowConcTime, 0.0)




    # ------------ SOIL DEPTH ----------------------------------------------------------
        # soil thickness and storage
        #soilStorages: firstStorDepth, secondStorDepth, soilWaterStorageCap1, soilWaterStorageCap2
        self.var.firstStorDepthInp = loadmap('firstStorDepth')
        self.var.secondStorDepthInp = loadmap('secondStorDepth')
        self.var.soilWaterStorageCap1Inp = loadmap('soilWaterStorageCap1')
        self.var.soilWaterStorageCap2Inp = loadmap('soilWaterStorageCap2')

        # layer thickness
        self.var.thickUpp000005 = (0.05 / 0.30) * self.var.firstStorDepthInp
        self.var.thickUpp005030 = (0.25 / 0.30) * self.var.firstStorDepthInp
        self.var.thickLow030150 = (1.20 / 1.20) * self.var.secondStorDepthInp

        self.var.storCapUpp000005 = self.var.thickUpp000005 * (self.var.satVolMoistContUpp000005 - self.var.resVolMoistContUpp000005)

        self.var.storCapUpp005030 = self.var.thickUpp005030 * (self.var.satVolMoistContUpp005030 - self.var.resVolMoistContUpp005030)
        self.var.storCapLow030150 = self.var.thickLow030150 * (self.var.satVolMoistContLow030150 - self.var.resVolMoistContLow030150)
        self.var.rootZoneWaterStorageCap = self.var.storCapUpp000005 + self.var.storCapUpp005030 + self.var.storCapLow030150

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic_PotET(self,coverType, No):
        """ dynamic part of the soil module - potET
             calculating potential Evaporation for each land cover class
             get crop coefficient, use potential ET, calculate potential bare soil evaporation and transpiration
        """

        # get crop coefficient:
        self.var.cropKC = readnetcdf2(binding[coverType + '_cropCoefficientNC'], self.var.CalendarDay, "DOY")
        self.var.cropKC = np.maximum(self.var.cropKC, self.var.minCropKC[No])

        # calculate potential ET:
        self.var.totalPotET = self.var.cropKC * self.var.ETRef

        # calculate potential bare soil evaporation and transpiration
        self.var.potBareSoilEvap[No] = self.var.minCropKC[No] * self.var.ETRef
        self.var.potTranspiration[No] = self.var.cropKC[No] * self.var.ETRef - self.var.potBareSoilEvap[No]

    def dynamic_interception(self,coverType, No):

        if not coverType.startswith("irr"):
            interceptCap  = readnetcdf2(binding[coverType + '_interceptCapNC'], self.var.CalendarDay, "DOY")
            coverFraction = readnetcdf2(binding[coverType + '_coverFractionNC'], self.var.CalendarDay, "DOY")
            interceptCap = coverFraction * interceptCap
            self.interceptCap = np.maximum(interceptCap, self.var.minInterceptCap[No])
        else:
            interceptCap = self.var.minInterceptCap[No]

        # throughfall = surplus above the interception storage threshold
        # throughfall = np.maximum(0.0, self.var.interceptStor[No] + self.var.Precipitation - interceptCap)
        # PB changed to Rain instead Pr, bceause snow is substracted later
        # PB it is assuming that all interception storage is used the other time step
        self.var.availWaterInfiltration[No] = np.maximum(0.0, self.var.Rain + self.var.interceptStor[No] - interceptCap + self.var.SnowMelt)


        # update interception storage after throughfall
        #self.var.interceptStor[No] = np.maximum(0.0, self.var.interceptStor[No] + self.var.Precipitation - throughfall)
        # PB or to make it short
        self.var.interceptStor[No] = interceptCap


        # evaporation from intercepted water (based on potTranspiration)
        mult = getValDivZero(self.var.interceptStor[No], interceptCap, 1e39, 0.) ** 0.66666
        self.var.interceptEvap[No] = np.minimum(self.var.interceptStor[No], self.var.potTranspiration[No] * mult)
        self.var.interceptEvap[No] = np.minimum(self.var.interceptEvap[No], self.var.potTranspiration[No])

        # update interception storage and potTranspiration
        self.var.interceptStor[No] = self.var.interceptStor[No] - self.var.interceptEvap[No]
        self.var.potTranspiration[No] = np.maximum(0, self.var.potTranspiration[No] - self.var.interceptEvap[No])

        # update actual evaporation (after interceptEvap)
        # interceptEvap is the first flux in ET
        self.var.actualET[No] = self.var.interceptEvap[No].copy()


    def dynamic_getSoilStates(self, coverType, No):

        def improvedArnoScheme(No,kUnsatLow030150,
                iniWaterStorage, inputNetLqWaterToSoil, directRunoffReduction="Default"):
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
                directRunoffReduction = np.minimum(kUnsatLow030150, np.sqrt(self.var.kUnsatAtFieldCapLow030150[No] * kUnsatLow030150))
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

            directRunoff = np.maximum(0.0, Pn - (self.var.rootZoneWaterStorageCap + directRunoffReduction - soilWaterStorage) + \
                           np.where(Pn >= condition, 0.0, \
                           self.var.rootZoneWaterStorageRange[No] * (WFRACB - \
                           Pn / ((self.var.arnoBeta[No] + 1.) * self.var.rootZoneWaterStorageRange[No])) ** (self.var.arnoBeta[No] + 1.)))
            #    Q1_L[TYPE]= max(0,Pn-(WMAX[TYPE]+P2_L[TYPE]-W[TYPE])+
            #      if(Pn>=(BCF[TYPE]+1)*WRANGE[TYPE]*WFRACB, 0,
            #      WRANGE[TYPE]*(WFRACB-Pn/((BCF[TYPE]+1)*WRANGE[TYPE]))**(BCF[TYPE]+1))); #*
            return directRunoff
            #---------------------------------------------------------
            # ---------------------------------------------------------


            # initial total soilWaterStorage
        self.var.soilWaterStorage[No] = np.maximum(0., self.var.storUpp000005[No] + self.var.storUpp005030[No] + self.var.storLow030150[No])

        # effective degree of saturation (-)
        effSatUpp000005 = np.minimum(1.0,np.maximum(0., self.var.storUpp000005[No] / self.var.storCapUpp000005))
        effSatUpp005030 = np.minimum(1.0,np.maximum(0., self.var.storUpp005030[No] / self.var.storCapUpp005030))
        effSatLow030150 = np.minimum(1.0,np.maximum(0., self.var.storLow030150[No] / self.var.storCapLow030150))


        # matricSuction (m)
        matricSuctionUpp000005 = self.var.airEntryValueUpp000005 * (np.maximum(0.01, effSatUpp000005) ** -self.var.poreSizeBetaUpp000005)
        matricSuctionUpp005030 = self.var.airEntryValueUpp005030 * (np.maximum(0.01, effSatUpp005030) ** -self.var.poreSizeBetaUpp005030)
        matricSuctionLow030150 = self.var.airEntryValueLow030150 * (np.maximum(0.01, effSatLow030150) ** -self.var.poreSizeBetaLow030150)

        # kUnsat (m.day-1): unsaturated hydraulic conductivity
        kUnsatUpp000005 = np.maximum(0., (effSatUpp000005 ** self.var.campbellBetaUpp000005) * self.var.kSatUpp000005)
        kUnsatUpp005030 = np.maximum(0., (effSatUpp005030 ** self.var.campbellBetaUpp005030) * self.var.kSatUpp005030)
        kUnsatLow030150 = np.maximum(0., (effSatLow030150 ** self.var.campbellBetaLow030150) * self.var.kSatLow030150)

        kUnsatUpp000005 = np.minimum(kUnsatUpp000005, self.var.kSatUpp000005)
        kUnsatUpp005030 = np.minimum(kUnsatUpp005030, self.var.kSatUpp005030)
        kUnsatLow030150 = np.minimum(kUnsatLow030150, self.var.kSatLow030150)

        # kThVert (m.day-1) = unsaturated conductivity capped at field capacity
        # - exchange between layers capped at field capacity
        #   between Upp000005Upp005030
        kThVertUpp000005Upp005030 = np.minimum( np.sqrt(kUnsatUpp000005 * kUnsatUpp005030), \
            (kUnsatUpp000005 * kUnsatUpp005030 * self.var.kUnsatAtFieldCapUpp000005 * \
             self.var.kUnsatAtFieldCapUpp005030) ** 0.25)
        #   between Upp005030Low030150
        kThVertUpp005030Low030150 = np.minimum( np.sqrt(kUnsatUpp005030 * kUnsatLow030150), \
            (kUnsatUpp005030 * kUnsatLow030150 * self.var.kUnsatAtFieldCapUpp005030 * \
             self.var.kUnsatAtFieldCapLow030150) ** 0.25)

        # gradient for capillary rise (index indicating target store to its underlying store)
        #    between Upp000005Upp005030
        gradientUpp000005Upp005030 = np.maximum(0., 2. * \
             (matricSuctionUpp000005 - matricSuctionUpp005030) / \
             (self.var.thickUpp000005 + self.var.thickUpp005030) - 1.)
        #    between Upp005030Low030150
        gradientUpp005030Low030150 = np.maximum(0., 2. * \
             (matricSuctionUpp005030 - matricSuctionLow030150) / \
             (self.var.thickUpp005030 + self.var.thickLow030150) - 1.)

        # readily available water in the root zone (upper soil layers)
        h1 = np.maximum(0., effSatUpp000005 - self.var.effSatAtWiltPointUpp000005) *\
             (self.var.satVolMoistContUpp000005 - self.var.resVolMoistContUpp000005) *\
              np.minimum(self.var.thickUpp000005, self.var.maxRootDepth)
        h2 = (np.maximum(0., effSatUpp005030 - self.var.effSatAtWiltPointUpp005030)) *\
            (self.var.satVolMoistContUpp005030 - self.var.resVolMoistContUpp005030) *\
             np.minimum(self.var.thickUpp005030, np.maximum(self.var.maxRootDepth - self.var.thickUpp000005,0.))

        h3 = np.maximum(0.,effSatLow030150 - self.var.effSatAtWiltPointLow030150) *\
             (self.var.satVolMoistContLow030150 - self.var.resVolMoistContLow030150) *\
             np.minimum(self.var.thickLow030150, np.maximum(self.var.maxRootDepth - self.var.thickUpp005030, 0.))

        self.var.readAvlWater = h1 + h2 + h3
        self.var.readAvlWater = np.minimum(self.var.readAvlWater, self.var.storUpp000005[No] + self.var.storUpp005030[No] + self.var.storLow030150[No])

        ## ----------------------------------------------------------
        # to the water demand module
        # could not be done before from landcoverType_module because readAvlWater is needed
        self.var.waterdemand_module.dynamic_waterdemand(coverType, No)


        # -----------------------------------------------------------
        # calculate openWaterEvap: open water evaporation from the paddy field,
        # and update topWaterLayer after openWaterEvap.

        self.var.openWaterEvap = 0.0
        if coverType == 'irrPaddy':
             # open water evaporation from the paddy field  - using potential evaporation from open water
            self.var.openWaterEvap = np.minimum( np.maximum(0., self.var.topWaterLayer[No]), self.var.EWRef)

             # update potBareSoilEvap & potTranspiration (after openWaterEvap)
            self.var.potBareSoilEvap[No]  = self.var.potBareSoilEvap[No] - (self.var.potBareSoilEvap[No]/self.var.EWRef) * self.var.openWaterEvap
            self.var.potTranspiration[No] = self.var.potTranspiration[No]- (self.var.potTranspiration[No]/self.var.EWRef)* self.var.openWaterEvap

            # update top water layer after openWaterEvap
            self.var.topWaterLayer[No] = np.maximum(0.,self.var.topWaterLayer[No] - self.var.openWaterEvap)

        # -----------------------------------------------------------
        # calculate directRunoff and infiltration, based on the improved Arno scheme (Hageman and Gates, 2003):
        # and update topWaterLayer (after directRunoff and infiltration).
             # update topWaterLayer (above soil)
             # with netLqWaterToSoil and irrGrossDemand

        self.var.topWaterLayer[No] = self.var.topWaterLayer[No] + np.maximum(0., self.var.availWaterInfiltration[No] + self.var.irrGrossDemand)
        # topwater = water net from precipitaion (- soil - interception - snow + snow melt) + water for irrigation

        # topWaterLater is partitioned into directRunoff (and infiltration)
        self.var.directRunoff[No] = improvedArnoScheme( No,kUnsatLow030150,
                    iniWaterStorage=self.var.soilWaterStorage[No], inputNetLqWaterToSoil=self.var.topWaterLayer[No])
        self.var.directRunoff[No] = np.minimum(self.var.topWaterLayer[No], self.var.directRunoff[No])

        # Yet, no directRunoff in the paddy field.
        if coverType == 'irrPaddy': self.var.directRunoff[No] = 0.

        # update topWaterLayer (above soil) after directRunoff
        self.var.topWaterLayer[No] = self.var.topWaterLayer[No] - self.var.directRunoff[No]



        # ---------------------------------------------------------
        # calculateInfiltration
        # infiltration, limited with KSat1 and available water in topWaterLayer
        self.infiltration = pcr.min(self.topWaterLayer,parameters.kSatUpp000005)  # P0_L = min(P0_L,KS1*Duration*timeslice());

        # update top water layer after infiltration
        self.topWaterLayer = self.topWaterLayer - self.infiltration

        # ---------------------------------------------------------
        #estimateTranspirationAndBareSoilEvap
        # TRANSPIRATION
        # - partitioning transpiration (based on actual each layer storage)

        dividerTranspFracs = pcr.max(1e-9, self.adjRootFrUpp000005 * self.storUpp000005 + \
                                     self.adjRootFrUpp005030 * self.storUpp005030 + \
                                     self.adjRootFrLow030150 * self.storLow030150)

        transpFracUpp000005 = pcr.ifthenelse((self.storUpp000005 + self.storUpp005030 + self.storLow030150) > 0., \
                   self.adjRootFrUpp000005 * self.storUpp000005 / dividerTranspFracs, self.adjRootFrUpp000005)

        transpFracUpp005030 =  pcr.ifthenelse((self.storUpp000005 +  self.storUpp005030 + \
                    self.storLow030150) > 0., self.adjRootFrUpp005030 * self.storUpp005030 / dividerTranspFracs, \
                   self.adjRootFrUpp005030)

        transpFracLow030150 = pcr.ifthenelse((self.storUpp000005 + self.storUpp005030 + \
                    self.storLow030150) > 0., self.adjRootFrLow030150 * self.storLow030150 / dividerTranspFracs, \
                   self.adjRootFrLow030150)


        # - relActTranspiration = fraction actual transpiration over potential transpiration
        relActTranspiration = (parameters.rootZoneWaterStorageCap  + \
                       self.arnoBeta*self.rootZoneWaterStorageRange*(1.- \
                   (1.+self.arnoBeta)/self.arnoBeta*self.WFRACB)) / \
                                  (parameters.rootZoneWaterStorageCap  + \
                       self.arnoBeta*self.rootZoneWaterStorageRange*(1.- self.WFRACB))   # original Rens's line:
                                                                                         # FRACTA[TYPE] = (WMAX[TYPE]+BCF[TYPE]*WRANGE[TYPE]*(1-(1+BCF[TYPE])/BCF[TYPE]*WFRACB))/
                                                                                         #                (WMAX[TYPE]+BCF[TYPE]*WRANGE[TYPE]*(1-WFRACB));
        relActTranspiration = (1.-self.satAreaFrac) / \
              (1.+(pcr.max(0.01,relActTranspiration)/self.effSatAt50)**\
                                           (self.effPoreSizeBetaAt50*pcr.scalar(-3.0)))  # original Rens's line:
                                                                                         # FRACTA[TYPE] = (1-SATFRAC_L)/(1+(max(0.01,FRACTA[TYPE])/THEFF_50[TYPE])**(-3*BCH_50));
        relActTranspiration = pcr.max(0.0, relActTranspiration)
        relActTranspiration = pcr.min(1.0, relActTranspiration)

        # estimates of actual transpiration fluxes:
        self.actTranspiUpp000005 = \
              relActTranspiration*transpFracUpp000005*self.potTranspiration
        self.actTranspiUpp005030 = \
              relActTranspiration*transpFracUpp005030*self.potTranspiration
        self.actTranspiLow030150 = \
              relActTranspiration*transpFracLow030150*self.potTranspiration

        # BARE SOIL EVAPORATION
        #
        # actual bare soil evaporation (potential)
        self.actBareSoilEvap = pcr.scalar(0.0)
        self.actBareSoilEvap = self.satAreaFrac * pcr.min( \
            self.potBareSoilEvap, parameters.kSatUpp000005) + \
                               (1. - self.satAreaFrac) * pcr.min( \
                                   self.potBareSoilEvap, self.kUnsatUpp000005)

        # no bare soil evaporation in the inundated paddy field
        if self.name == 'irrPaddy':
            self.actBareSoilEvap = pcr.ifthenelse(self.topWaterLayer > 0.0, 0.0, self.actBareSoilEvap)





        # ---------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------
        # estimateSoilFluxes(self, parameters, capRiseFrac):
        # Given states, we estimate all fluxes.
            # - percolation from storUpp000005 to storUpp005030 (m)
        self.percUpp000005 = self.kThVertUpp000005Upp005030 * 1.
        self.percUpp000005 = \
            pcr.ifthenelse(self.effSatUpp000005 > parameters.effSatAtFieldCapUpp000005, \
                           pcr.min(pcr.max(0.,
                                           self.effSatUpp000005 - parameters.effSatAtFieldCapUpp000005) * parameters.storCapUpp000005,
                                   self.percUpp000005), self.percUpp000005) + \
            pcr.max(0., self.infiltration - \
                    (parameters.storCapUpp000005 - self.storUpp000005))

        # - percolation from storUpp005030 to storLow030150 (m)
        self.percUpp005030 = self.kThVertUpp005030Low030150 * 1.
        self.percUpp005030 = \
            pcr.ifthenelse(self.effSatUpp005030 > parameters.effSatAtFieldCapUpp005030, \
                           pcr.min(pcr.max(0.,
                                           self.effSatUpp005030 - parameters.effSatAtFieldCapUpp005030) * parameters.storCapUpp005030,
                                   self.percUpp005030), self.percUpp005030) + \
            pcr.max(0., self.percUpp000005 - \
                    (parameters.storCapUpp005030 - self.storUpp005030))

        # - percolation from storLow030150 to storGroundwater (m)
        self.percLow030150 = pcr.min(self.kUnsatLow030150, pcr.sqrt( \
            parameters.kUnsatAtFieldCapLow030150 * \
            self.kUnsatLow030150))

        # - capillary rise to storUpp000005 from storUpp005030 (m)
        self.capRiseUpp000005 = pcr.min(pcr.max(0., \
                                                parameters.effSatAtFieldCapUpp000005 - \
                                                self.effSatUpp000005) * \
                                        parameters.storCapUpp000005, \
                                        self.kThVertUpp000005Upp005030 * \
                                        self.gradientUpp000005Upp005030)

        # - capillary rise to storUpp005030 from storLow030150 (m)
        self.capRiseUpp005030 = pcr.min(pcr.max(0., \
                                                parameters.effSatAtFieldCapUpp005030 - \
                                                self.effSatUpp005030) * \
                                        parameters.storCapUpp005030, \
                                        self.kThVertUpp005030Low030150 * \
                                        self.gradientUpp005030Low030150)

        # - capillary rise to storLow030150 from storGroundwater (m)
        self.capRiseLow030150 = 0.5 * (self.satAreaFrac + capRiseFrac) * \
                                pcr.min((1. - self.effSatLow030150) * \
                                        pcr.sqrt(parameters.kSatLow030150 * \
                                                 self.kUnsatLow030150), \
                                        pcr.max(0.0, parameters.effSatAtFieldCapLow030150 - \
                                                self.effSatLow030150) * \
                                        parameters.storCapLow030150)

        # - interflow (m)
        percToInterflow = parameters.percolationImp * ( \
            self.percUpp005030 + self.capRiseLow030150 - \
            (self.percLow030150 + self.capRiseUpp005030))
        self.interflow = pcr.max( \
            parameters.interflowConcTime * percToInterflow + \
            (pcr.scalar(1.) - parameters.interflowConcTime) * self.interflow, 0.0)




