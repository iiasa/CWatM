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
            return directRunoff, WFRACB, satAreaFrac
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

        self.var.openWaterEvap = globals.inZero.copy()
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
        self.var.directRunoff[No], WFRACB, satAreaFrac = improvedArnoScheme( No,kUnsatLow030150,
                    iniWaterStorage=self.var.soilWaterStorage[No], inputNetLqWaterToSoil=self.var.topWaterLayer[No])
        self.var.directRunoff[No] = np.minimum(self.var.topWaterLayer[No], self.var.directRunoff[No])

        # Yet, no directRunoff in the paddy field.
        if coverType == 'irrPaddy': self.var.directRunoff[No] = 0.

        # update topWaterLayer (above soil) after directRunoff
        self.var.topWaterLayer[No] = self.var.topWaterLayer[No] - self.var.directRunoff[No]



        # ---------------------------------------------------------
        # calculateInfiltration
        # infiltration, limited with KSat1 and available water in topWaterLayer
        self.var.infiltration[No] = np.minimum(self.var.topWaterLayer[No],self.var.kSatUpp000005)  # P0_L = min(P0_L,KS1*Duration*timeslice());

        # update top water layer after infiltration
        self.var.topWaterLayer[No] = self.var.topWaterLayer[No] - self.var.infiltration[No]

        # ---------------------------------------------------------
        #estimateTranspirationAndBareSoilEvap
        # TRANSPIRATION
        # - partitioning transpiration (based on actual each layer storage)

        dividerTranspFracs = np.maximum(1e-9, self.var.adjRootFrUpp000005[No] * self.var.storUpp000005[No] + \
                    self.var.adjRootFrUpp005030[No] * self.var.storUpp005030[No] + \
                    self.var.adjRootFrLow030150[No] * self.var.storLow030150[No])

        transpFracUpp000005 = np.where((self.var.storUpp000005[No] + self.var.storUpp005030[No] + self.var.storLow030150[No]) > 0., \
                    self.var.adjRootFrUpp000005[No] * self.var.storUpp000005[No] / dividerTranspFracs[No], self.var.adjRootFrUpp000005[No])

        transpFracUpp005030 =  np.where((self.var.storUpp000005[No] +  self.var.storUpp005030[No] + \
                    self.var.storLow030150[No]) > 0., self.var.adjRootFrUpp005030[No] * self.var.storUpp005030[No] / dividerTranspFracs, \
                    self.var.adjRootFrUpp005030[No])

        transpFracLow030150 = np.where((self.var.storUpp000005[No] + self.var.storUpp005030[No] + \
                    self.var.storLow030150[No]) > 0., self.var.adjRootFrLow030150[No] * self.var.storLow030150[No] / dividerTranspFracs, \
                    self.var.adjRootFrLow030150[No])


        # - relActTranspiration = fraction actual transpiration over potential transpiration
        relActTranspiration = (self.var.rootZoneWaterStorageCap  + self.var.arnoBeta[No]*self.var.rootZoneWaterStorageRange[No]*(1.- \
                    (1.+self.var.arnoBeta[No])/self.var.arnoBeta[No]* WFRACB)) / \
                    (self.var.rootZoneWaterStorageCap  + self.var.arnoBeta[No]*self.var.rootZoneWaterStorageRange[No]*(1.- WFRACB))   # original Rens's line:


        relActTranspiration = (1.- satAreaFrac) / \
                    (1.+(np.maximum(0.01,relActTranspiration)/self.var.effSatAt50[No])**\
                    (self.var.effPoreSizeBetaAt50[No]* -3.0))

        relActTranspiration = np.maximum(0.0, relActTranspiration)
        relActTranspiration = np.minimum(1.0, relActTranspiration)

        # estimates of actual transpiration fluxes:
        self.var.actTranspiUpp000005 = relActTranspiration * transpFracUpp000005* self.var.potTranspiration[No]
        self.var.actTranspiUpp005030 = relActTranspiration * transpFracUpp005030* self.var.potTranspiration[No]
        self.var.actTranspiLow030150 = relActTranspiration * transpFracLow030150* self.var.potTranspiration[No]

        # BARE SOIL EVAPORATION
        #
        # actual bare soil evaporation (potential)
        self.var.actBareSoilEvap[No] = satAreaFrac * np.minimum( \
                    self.var.potBareSoilEvap[No], self.var.kSatUpp000005) + \
                    (1. - satAreaFrac) * np.minimum(self.var.potBareSoilEvap[No], kUnsatUpp000005)

        # no bare soil evaporation in the inundated paddy field
        if coverType == 'irrPaddy':
                    self.var.actBareSoilEvap[No] = np.where(self.var.topWaterLayer[No] > 0.0, 0.0, self.var.actBareSoilEvap[No])




        # ---------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------
        # estimateSoilFluxes(self, parameters, capRiseFrac):
        # Given states, we estimate all fluxes.
            # - percolation from storUpp000005 to storUpp005030 (m)
        self.var.percUpp000005 = kThVertUpp000005Upp005030 * 1.
        self.var.percUpp000005 = np.where(effSatUpp000005 > self.var.effSatAtFieldCapUpp000005, \
                    np.minimum(np.maximum(0.,effSatUpp000005 - self.var.effSatAtFieldCapUpp000005) * self.var.storCapUpp000005,
                    self.var.percUpp000005[No]), self.var.percUpp000005[No]) + np.maximum(0., self.var.infiltration[No] - \
                    (self.var.storCapUpp000005 - self.var.storUpp000005[No]))

        # - percolation from storUpp005030 to storLow030150 (m)
        self.var.percUpp005030 = kThVertUpp005030Low030150 * 1.
        self.var.percUpp005030 = np.where(effSatUpp005030 > self.var.effSatAtFieldCapUpp005030, \
                    np.minimum(np.maximum(0., effSatUpp005030 - self.var.effSatAtFieldCapUpp005030) * self.var.storCapUpp005030,
                    self.var.percUpp005030), self.var.percUpp005030) + np.maximum(0., self.var.percUpp000005 - \
                    (self.var.storCapUpp005030 - self.var.storUpp005030[No]))

        # - percolation from storLow030150 to storGroundwater (m)
        self.var.percLow030150 = np.minimum(kUnsatLow030150, np.sqrt(self.var.kUnsatAtFieldCapLow030150 * kUnsatLow030150))

        # - capillary rise to storUpp000005 from storUpp005030 (m)
        self.var.capRiseUpp000005 = np.minimum(np.maximum(0., self.var.effSatAtFieldCapUpp000005 - \
                    effSatUpp000005) * self.var.storCapUpp000005, \
                    kThVertUpp000005Upp005030 * gradientUpp000005Upp005030)

        # - capillary rise to storUpp005030 from storLow030150 (m)
        self.var.capRiseUpp005030 = np.minimum(np.maximum(0., self.var.effSatAtFieldCapUpp005030 - \
                    effSatUpp005030) * self.var.storCapUpp005030, \
                    kThVertUpp005030Low030150 * gradientUpp005030Low030150)


        # - capillary rise to storLow030150 from storGroundwater (m)
        self.var.capRiseLow030150 = 0.5 * (satAreaFrac + self.var.capRiseFrac) * \
                    np.minimum((1. - effSatLow030150) * np.sqrt(self.var.kSatLow030150 * \
                    kUnsatLow030150), np.maximum(0.0, self.var.effSatAtFieldCapLow030150 - \
                    effSatLow030150) * self.var.storCapLow030150)

        # - interflow (m)
        percToInterflow = self.var.percolationImp * ( self.var.percUpp005030 + self.var.capRiseLow030150 - \
                    (self.var.percLow030150 + self.var.capRiseUpp005030))
        self.var.interflow = np.maximum( self.var.interflowConcTime * percToInterflow + \
                    (1.0 - self.var.interflowConcTime) * self.var.interflow[No], 0.0)

        # ---------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------

        # scaleAllFluxes(self, parameters, groundwater):
        # re-scale all fluxes (based on available water).
        # ####################################################
        # scale fluxes (for Upp000005)
        ADJUST = self.var.actBareSoilEvap[No] + self.var.actTranspiUpp000005[No] + self.var.percUpp000005[No]
        ADJUST = np.where(ADJUST > 0.0, np.minimum(1.0, np.maximum(0.0, self.var.storUpp000005[No] + self.var.infiltration[No]) / ADJUST), 0.)
        self.var.actBareSoilEvap[No] = ADJUST * self.var.actBareSoilEvap[No]
        self.var.actTranspiUpp000005 = ADJUST * self.var.actTranspiUpp000005
        self.var.percUpp000005 = ADJUST * self.var.percUpp000005

        # scale fluxes (for Upp000005)
        ADJUST = self.var.actTranspiUpp005030[No] + self.var.percUpp005030[No]
        ADJUST = np.where(ADJUST > 0.0, np.minimum(1.0, np.maximum(0.0, self.var.storUpp005030[No] + self.var.percUpp000005[No]) / ADJUST), 0.)
        self.var.actTranspiUpp005030 = ADJUST * self.var.actTranspiUpp005030
        self.var.percUpp005030 = ADJUST * self.var.percUpp005030

        # scale fluxes (for Low030150)
        ADJUST = self.var.actTranspiLow030150[No] + self.var.percLow030150[No] + self.var.interflow[No]
        ADJUST = np.where(ADJUST > 0.0, np.minimum(1.0, np.maximum(0.0, self.var.storLow030150[No] + self.var.percUpp005030[No]) / ADJUST), 0.)
        self.var.actTranspiLow030150[No] = ADJUST * self.var.actTranspiLow030150[No]
        self.var.percLow030150 = ADJUST * self.var.percLow030150
        self.var.interflow[No] = ADJUST * self.var.interflow[No]

        # capillary rise to storLow is limited to available storGroundwater
        # and also limited with reducedGroundWaterAbstraction
        #
        self.var.capRiseLow030150 = np.maximum(0., np.minimum( \
                np.maximum(0., self.var.storGroundwater - self.var.reducedGroundWaterAbstraction), self.var.capRiseLow030150))

        # capillary rise to storUpp005030 is limited to available storLow030150
        #
        estimateStorLow030150BeforeCapRise = np.maximum(0, self.var.storLow030150[No] + self.var.percUpp005030 - \
                (self.var.actTranspiLow030150 + self.var.percLow030150 + self.var.interflow))
        self.var.capRiseUpp005030 = np.minimum(estimateStorLow030150BeforeCapRise, self.var.capRiseUpp005030)

        # capillary rise to storUpp000005 is limited to available storUpp005030
        #
        estimateStorUpp005030BeforeCapRise = np.maximum(0, self.var.storUpp005030[No] + self.var.percUpp000005 - \
                (self.var.actTranspiUpp005030 + self.var.percUpp005030))
        self.var.capRiseUpp000005 = np.minimum(estimateStorUpp005030BeforeCapRise, self.var.capRiseUpp000005)


        # ---------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------
        # Give new states and make sure that no storage capacities will be exceeded.
        #################################################################################
        # update storLow030150 after the following fluxes:
        # + percUpp005030
        # + capRiseLow030150
        # - percLow030150
        # - interflow
        # - actTranspiLow030150
        # - capRiseUpp005030
        #
        self.var.storLow030150[No] = np.maximum(0., self.var.storLow030150[No] + self.var.percUpp005030 + self.var.capRiseLow030150 - \
                    (self.var.percLow030150 + self.var.interflow + self.var.actTranspiLow030150 + self.var.capRiseUpp005030))
        #
        # If necessary, reduce percolation input:
        percUpp005030 = self.var.percUpp005030.copy()
        self.var.percUpp005030 = np.maximum(0., percUpp005030 - np.maximum(0., self.var.storLow030150[No] - self.var.storCapLow030150))
        self.var.storLow030150[No] = self.var.storLow030150[No] - percUpp005030 + self.var.percUpp005030
        #
        # If necessary, reduce capRise input:
        capRiseLow030150 = self.var.capRiseLow030150.copy()
        self.var.capRiseLow030150 = np.maximum(0., capRiseLow030150 - np.maximum(0., self.var.storLow030150[No] - self.var.storCapLow030150))
        self.var.storLow030150[No] = self.var.storLow030150[No] - capRiseLow030150 + self.var.capRiseLow030150
        #
        # If necessary, increase interflow outflow:
        addInterflow = np.maximum(0., self.var.storLow030150[No] - self.var.storCapLow030150)
        self.var.interflow += addInterflow
        self.var.storLow030150[No] -= addInterflow

        self.var.storLow030150[No] = np.minimum(self.var.storLow030150[No], self.var.storCapLow030150)

        # update storUpp005030 after the following fluxes:
        # + percUpp000005
        # + capRiseUpp005030
        # - percUpp005030
        # - actTranspiUpp005030
        # - capRiseUpp000005
        #
        self.var.storUpp005030[No] = np.maximum(0., self.var.storUpp005030[No] + self.var.percUpp000005 + self.var.capRiseUpp005030 - \
                    (self.var.percUpp005030 + self.var.actTranspiUpp005030 + self.var.capRiseUpp000005))
        #
        # If necessary, reduce percolation input:
        percUpp000005 = self.var.percUpp000005.copy()
        self.var.percUpp000005 = np.maximum(0., percUpp000005 - np.maximum(0., self.var.storUpp005030[No] - self.var.storCapUpp005030))
        self.var.storUpp005030[No] = self.var.storUpp005030[No] - percUpp000005 + self.var.percUpp000005
        #
        # If necessary, reduce capRise input:
        capRiseUpp005030 = self.var.capRiseUpp005030.copy()
        self.var.capRiseUpp005030 = np.maximum(0., capRiseUpp005030 - np.maximum(0., self.var.storUpp005030[No] - self.var.storCapUpp005030))
        self.var.storUpp005030[No] = self.var.storUpp005030[No] - capRiseUpp005030 + self.var.capRiseUpp005030
        #
        # If necessary, introduce interflow outflow:
        self.var.interflowUpp005030 = np.maximum(0., self.var.storUpp005030[No] - self.var.storCapUpp005030)
        self.var.storUpp005030[No] = self.var.storUpp005030[No] - self.var.interflowUpp005030

        # update storUpp000005 after the following fluxes:
        # + infiltration
        # + capRiseUpp000005
        # - percUpp000005
        # - actTranspiUpp000005
        # - actBareSoilEvap
        #
        self.var.storUpp000005[No] = np.maximum(0., self.var.storUpp000005[No] + self.var.infiltration[No] + self.var.capRiseUpp000005 - \
                    (self.var.percUpp000005 + self.var.actTranspiUpp000005 + self.var.actBareSoilEvap[No]))
        #
        # any excess above storCapUpp is handed to topWaterLayer
        self.var.satExcess = np.maximum(0., self.var.storUpp000005[No] - self.var.storCapUpp000005)
        self.var.topWaterLayer[No] = self.var.topWaterLayer[No] + self.var.satExcess

        # any excess above minTopWaterLayer is released as directRunoff
        self.var.directRunoff[No] = self.var.directRunoff[No] + np.maximum(0., self.var.topWaterLayer[No] - self.var.minTopWaterLayer[No])

        # make sure that storage capacities are not exceeded
        self.var.topWaterLayer[No] = np.minimum(self.var.topWaterLayer[No], self.var.minTopWaterLayer[No])
        self.var.storUpp000005[No] = np.minimum(self.var.storUpp000005[No], self.var.storCapUpp000005)
        self.var.storUpp005030[No] = np.minimum(self.var.storUpp005030[No], self.var.storCapUpp005030)
        self.var.storLow030150[No] = np.minimum(self.var.storLow030150[No], self.var.storCapLow030150)

        # total actual evaporation + transpiration

        self.var.actualET[No] += self.var.actBareSoilEvap[No] + self.var.openWaterEvap[No] + self.var.actTranspiUpp000005 + \
                         self.var.actTranspiUpp005030 + self.var.actTranspiLow030150

        # total actual transpiration
        self.var.actTranspiUppTotal = self.var.actTranspiUpp000005 + self.var.actTranspiUpp005030

        # total actual transpiration
        self.var.actTranspiTotal = self.var.actTranspiUppTotal + self.var.actTranspiLow030150

        # net percolation between upperSoilStores (positive indicating downward direction)
        self.var.netPercUpp000005 = self.var.percUpp000005 - self.var.capRiseUpp000005
        self.var.netPercUpp005030 = self.var.percUpp005030 - self.var.capRiseUpp005030

        # groundwater recharge
        self.var.gwRecharge = self.var.percLow030150 - self.var.capRiseLow030150


        # variables / states that are defined the twoLayer and threeLayer model:
        ########################################################################

        # landSurfaceRunoff (needed for routing)
        self.var.landSurfaceRunoff[No] = self.var.directRunoff[No] + self.var.interflow + self.var.interflowUpp005030

