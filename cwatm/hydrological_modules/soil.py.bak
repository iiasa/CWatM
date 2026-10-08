# -------------------------------------------------------------------------
# Name:        Soil module
# Purpose: Soil water dynamics module using the Arno scheme for vertical water transfer.
# Implements multi-layer soil model with infiltration, percolation, and storage processes.
# Handles variable infiltration capacity and generates surface runoff components.
#
# Author:      PB. MS, DF, JdB
# Created:     15/07/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
import warnings
warnings.filterwarnings("ignore")


class soil(object):
    """
    Soil water dynamics module using the Arno scheme for vertical water transfer.
    
    Simulates soil water movement, evapotranspiration, and runoff generation using
    a multi-layer soil model based on the Arno scheme. Handles infiltration,
    percolation, capillary rise, preferential flow, and transpiration processes
    across different land cover types.
    
    Attributes
    ----------
    var : object
        Reference to model variables object containing state variables
    model : object
        Reference to the main CWatM model instance
        
    Notes
    -----
    The module implements:
    - Multi-layer soil water balance (typically 3 layers)
    - Arno scheme for heterogeneous runoff generation
    - Root zone dynamics for transpiration
    - Preferential flow and interflow processes
    - Soil hydraulic property management
    - Capillary rise from groundwater
    
    Based on concepts from PCRGLOBE, LISFLOOD, and HBV models.
    References the Arno scheme for spatially variable soil moisture.

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    capRiseFrac                          Array         fraction of a grid cell where capillar rise may happen                  m    
    modflow                              Flag          True if modflow_coupling = True in settings file                        bool 
    activatedCrops                       Array         Fraction of area a specific crop is planted                             --   
    currentKC                            Array         Current crop coefficient for specific crops                             --   
    weighted_KC_Irr_woFallow             Array                                                                                 --   
    storGroundwater                      Array         Groundwater storage (non-fossil). This is primarily used when not usin  m    
    includeCrops                         Flag          1 when includeCrops=True in Settings, 0 otherwise                       bool 
    Crops                                Array         Internal: List of specific crops and Kc/Ky parameters                   --   
    potTranspiration                     Array         Potential transpiration (after removing of evaporation)                 m    
    cropKC                               Array         crop coefficient for each of the 4 different land cover types (forest,  --   
    minCropKC                            Array         minimum crop factor (default 0.2)                                       --   
    rootDepth                            Array         rootdepth of different layers                                           m    
    KSat1                                Array         Saturated conductivity layer 1                                          cm/da
    KSat2                                Array         Saturated conductivity layer 2                                          cm/da
    KSat3                                Array         Saturated conductivity layer 3                                          cm/da
    genuM1                               Array         soil: lambda / (1+ lambda)  layer1                                      --   
    genuM2                               Array         soil: lambda / (1+ lambda)  layer2                                      --   
    genuM3                               Array         soil: lambda / (1+ lambda)  layer3                                      --   
    genuInvM1                            Array         soil:1 / genuM1                                                         --   
    genuInvM2                            Array         soil:1 / genuM2                                                         --   
    genuInvM3                            Array         soil:1 / genuM3                                                         --   
    ws1                                  Array         Maximum storage capacity in layer 1                                     m    
    ws2                                  Array         Maximum storage capacity in layer 2                                     m    
    ws3                                  Array         Maximum storage capacity in layer 3                                     m    
    wres1                                Array         Residual storage capacity in layer 1                                    m    
    wres2                                Array         Residual storage capacity in layer 2                                    m    
    wres3                                Array         Residual storage capacity in layer 3                                    m    
    wrange1                              Array         maximum soil moisture (ws) - residual soil mositure (wres) layer 1      m    
    wrange2                              Array         maximum soil moisture (ws) - residual soil mositure (wres) layer 2      m    
    wrange3                              Array         maximum soil moisture (ws) - residual soil mositure (wres) layer 3      m    
    wwp1                                 Array         Soil moisture at wilting point in layer 1                               m    
    wwp2                                 Array         Soil moisture at wilting point in layer 2                               m    
    wwp3                                 Array         Soil moisture at wilting point in layer 3                               m    
    kunSatFC12                           Array         calculation from van Genuchten, Mualem equation                         m/day
    kunSatFC23                           Array         calculation from van Genuchten, Mualem equation                         m/day
    arnoBeta                             Array         arnoBeta defines the shape of soil water capacity distribution curve a  --   
    adjRoot                              Array                                                                                 --   
    maxtopwater                          Array         maximum heigth of topwater                                              m    
    EWRef                                Array         potential evaporation rate from water surface                           m    
    availWaterInfiltration               Array         quantity of water reaching the soil after interception, more snowmelt   m    
    FrostIndexThreshold                  Array         Degree Days Frost Threshold (stops infiltration, percolation and capil  --   
    FrostIndex                           Array         FrostIndex - Molnau and Bissel (1983), A Continuous Frozen Ground Inde  --   
    potBareSoilEvap                      Array         potential bare soil evaporation (calculated with minus snow evaporatio  m    
    irr_Paddy_month                      Array                                                                                 --   
    ET_crop_Irr_paddy                    Array                                                                                 --   
    ET_crop_Irr_paddy_fraccrop           Array                                                                                 --   
    fracCrops_Irr                        Array         Fraction of cell currently planted with specific irrigated crops        %    
    fracCrops_nonIrr                     Array         Fraction of cell currently planted with specific non-irr crops          %    
    actTransTotal_month_nonIrr           Array         Internal variable: Running total of  transpiration for specific non-ir  m    
    actTransTotal_month_Irr              Array         Internal variable: Running total of  transpiration for specific irriga  m    
    irr_crop_month                       Number                                                                                --   
    frac_totalIrr                        Array         Fraction sown with specific irrigated crops                             %    
    weighted_KC_Irr_woFallow_fullKc      Array                                                                                 --   
    totalPotET                           Array         Potential evaporation per land use class                                m    
    PotET_crop                           Array                                                                                 --   
    actualET                             Array         simulated evapotranspiration from soil, flooded area and vegetation     m    
    soilLayers                           Array         Number of soil layers                                                   --   
    soildepth                            Array         Thickness of the first soil layer                                       m    
    wfc1                                 Array         Soil moisture at field capacity in layer 1                              m    
    wfc2                                 Array         Soil moisture at field capacity in layer 2                              m    
    wfc3                                 Array         Soil moisture at field capacity in layer 3                              m    
    w1                                   Array         Simulated water storage in the layer 1                                  m    
    w2                                   Array         Simulated water storage in the layer 2                                  m    
    w3                                   Array         Simulated water storage in the layer 3                                  m    
    topwater                             Array         quantity of water above the soil (flooding)                             m    
    directRunoff                         Array         Simulated surface runoff                                                m    
    interflow                            Array         Simulated flow reaching runoff instead of groundwater                   m    
    openWaterEvap                        Array         Simulated evaporation from open areas                                   m    
    percolationImp                       Array         Fraction of area covered by the corresponding landcover type            m    
    cropGroupNumber                      Array         soil water depletion fraction, Van Diepen et al., 1988: WOFOST 6.0, p.  --   
    cPrefFlow                            Array         Factor influencing preferential flow (flow from surface to GW)          --   
    pumping_actual                       Array                                                                                 --   
    gwdepth_observations                 Array         Input, gw_depth_observations, groundwater depth observations            m    
    gwdepth_adjuster                     Array         Groundwater depth adjuster                                              m    
    rws                                  Array         Transpiration reduction factor (in case of water stress)                --   
    actBareSoilEvap                      Array         Simulated evaporation from the first soil layer                         m    
    prefFlow                             Array         Flow going directly from soil surface to groundwater [land class speci  m    
    infiltration                         Array         Water actually infiltrating the soil                                    m    
    capRiseFromGW                        Array         Simulated capillary rise from groundwater                               m    
    NoSubSteps                           Array         Number of sub steps to calculate soil percolation                       --   
    perc1to2                             Array         Simulated water flow from soil layer 1 to soil layer 2                  m    
    perc2to3                             Array         Simulated water flow from soil layer 2 to soil layer 3                  m    
    perc3toGW                            Array         Simulated water flow from soil layer 3 to groundwater                   m    
    theta1                               Array         fraction of water in soil compartment 1 for each land use class         --   
    theta2                               Array         fraction of water in soil compartment 2 for each land use class         --   
    theta3                               Array         fraction of water in soil compartment 3 for each land use class         --   
    actTransTotal                        Array         Total actual transpiration from the three soil layers                   m    
    actTransTotal_forest                 Array         Transpiration from forest land cover                                    m    
    actTransTotal_grasslands             Array         Transpiration from grasslands land cover                                m    
    actTransTotal_paddy                  Array         Transpiration from paddy land cover                                     m    
    actTransTotal_nonpaddy               Array         Transpiration from non-paddy land cover                                 m    
    actTransTotal_crops_Irr              Array         Transpiration associated with specific irrigated crops                  m    
    actTransTotal_crops_nonIrr           Array         Transpiration associated with specific non-irr crops                    m    
    ET_crop_Irr                          Array                                                                                 --   
    ET_crop_nonIrr                       Array                                                                                 --   
    irr_crop                             Array                                                                                 --   
    ratio_a_p_nonIrr_daily               Array                                                                                 --   
    ratio_a_p_Irr_daily                  Array                                                                                 --   
    irrM3_crop_month_segment             Array                                                                                 --   
    irrM3_Paddy_month_segment            Array                                                                                 --   
    gwRecharge                           Array         groundwater recharge                                                    m    
    baseflow                             Array         simulated baseflow (= groundwater discharge to river)                   m    
    capillar                             Array         Flow from groundwater to the third CWATM soil layer. Used with MODFLOW  m    
    capriseindex                         Array                                                                                 --   
    soildepth12                          Array         Total thickness of layer 2 and 3                                        m    
    fracVegCover                         Array         Fraction of specific land covers (0=forest, 1=grasslands, etc.)         %    
    adminSegments                        Array         Domestic agents                                                         Int  
    cellArea                             Array         Area of cell                                                            m2   
    act_irrConsumption                   Array         actual irrigation water consumption                                     m    
    act_irrNonpaddyWithdrawal            Array         non-paddy irrigation withdrawal                                         m    
    act_irrPaddyWithdrawal               Array         paddy irrigation withdrawal                                             m    
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize soil module.
        
        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initialize soil hydraulic properties and layer configuration.
        
        Sets up soil layer structure, hydraulic parameters, and initial conditions
        for soil water dynamics including percolation limitations, preferential flow,
        root zone characteristics, and field capacity relationships.
        
        Notes
        -----
        Initialization includes:
        - Soil layer configuration (typically 3 layers)
        - Hydraulic properties (field capacity, wilting point, saturation)
        - Preferential flow and interflow parameters
        - Root zone depth and distribution
        - Percolation impedance factors
        - Initial soil moisture conditions
        - Crop-specific parameters for water uptake
        
        Soil layers represent different depths and hydraulic characteristics
        for realistic vertical water movement simulation.
        """

        self.var.soilLayers = 3
        # Fraction of area where percolation to groundwater is impeded [dimensionless]
        self.var.percolationImp = np.maximum(0, np.minimum(1, loadmap('percolationImp') * 
                                                            loadmap('factor_interflow')))

        # ------------ Preferential Flow constant ------------------------------------------
        self.var.cropGroupNumber = loadmap('cropgroupnumber')
        # soil water depletion fraction, Van Diepen et al., 1988: WOFOST 6.0, p.86, Doorenbos et. al 1978
        # crop groups for formular in van Diepen et al, 1988

        # ------------ Preferential Flow constant ------------------------------------------
        self.var.cPrefFlow = loadmap('preferentialFlowConstant')

        # ------------ SOIL DEPTH ----------------------------------------------------------
        # soil thickness and storage

        # soilDepthLayer = [('soildepth', 'SoilDepth'),('storCap','soilWaterStorageCap')]
        soilDepthLayer = [('soildepth', 'SoilDepth')]
        for layer, property in soilDepthLayer:
            vars(self.var)[layer] = np.tile(globals.inZero, (self.var.soilLayers, 1))

        # first soil layer = 5 cm to represent a shallow soil layer which can be used to compare with remote sensing data
        self.var.soildepth[0] = 0.05 + globals.inZero
        # second soil layer minimum 5cm (for calculation purpose). 2nd soli layer = soildepth - 1st soil layer of 5 cm
        self.var.soildepth[1] = np.maximum(0.05, loadmap('StorDepth1') - self.var.soildepth[0])

        # third soildepth minimum 5cm (to calculation purpose).
        self.var.soildepth[2] = loadmap('StorDepth2')
        self.var.soildepth[2] = np.maximum(0.05, self.var.soildepth[2])

        # Calibration
        # a calibration soil factor can multiply the 2nd and 3rd soillayer thickness
        soildepth_factor = loadmap('soildepth_factor')
        self.var.soildepth[1] = self.var.soildepth[1] * soildepth_factor
        self.var.soildepth[2] = self.var.soildepth[2] * soildepth_factor
        self.var.soildepth12 = self.var.soildepth[1] + self.var.soildepth[2]

        # This is here, as groundwater.py is not called if MODFLOW is used
        self.var.pumping_actual = globals.inZero.copy()
        self.var.capillar = globals.inZero.copy()
        self.var.baseflow = globals.inZero.copy()

        if 'gw_depth_observations' in binding:
            self.var.gwdepth_observations = readnetcdfWithoutTime(cbinding('gw_depth_observations'),
                                                                  value='Groundwater depth')
        if 'gw_depth_sim_obs' in binding:
            self.var.gwdepth_adjuster = loadmap('gw_depth_sim_obs')

        # --------------------------------------------------------------------------
        # --------------------------------------------------------------------------

    def dynamic(self, coverType, No):
        """
        Calculate soil water dynamics for a specific land cover type.
        
        Simulates vertical water transport, evapotranspiration, and runoff generation
        for a land cover class using multi-layer soil water balance with the Arno scheme.
        Handles infiltration, percolation, capillary rise, transpiration, and preferential flow.
        
        Parameters
        ----------
        coverType : str
            Land cover type identifier (e.g., 'forest', 'grassland', 'irrPaddy', 'irrNonPaddy')
        No : int
            Index number of the land cover type in model arrays
            
        Notes
        -----
        Processing sequence:
        1. Water stress calculation and transpiration limitation
        2. Bare soil evaporation from upper layer
        3. Infiltration capacity using Arno scheme
        4. Preferential flow calculation
        5. Multi-layer percolation with Van Genuchten equations
        6. Capillary rise between layers and from groundwater
        7. Interflow and groundwater recharge calculation
        
        Special handling for irrigated paddy fields:
        - Maintains surface water storage (topwater)
        - Open water evaporation from flooded fields
        - Modified infiltration when fields are flooded
        
        The Arno scheme accounts for spatial variability in soil saturation
        within grid cells, leading to heterogeneous runoff generation.
        """

        # ---------------------------------------------------------

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

        # if (dateVar['curr'] > 6520):

        availWaterInfiltration = self.var.availWaterInfiltration[No].copy()
        availWaterInfiltration = availWaterInfiltration + self.var.act_irrConsumption[No]
        # availWaterInfiltration = water net from precipitation (- soil - interception - snow + snow melt) + 
        # water for irrigation

        if coverType == 'irrPaddy':
            # depending on the crop calender -> here if cropKC > 0.75 paddies are flooded to 50mm (as set in settings file)

            # if self.var.cropKC[No] > 0.75:
            #     ii = 1

            self.var.topwater = np.where(self.var.cropKC[No] > 0.75, 
                                         self.var.topwater + availWaterInfiltration, 
                                         self.var.topwater)

            # open water evaporation from the paddy field - using potential evaporation from open water
            self.var.openWaterEvap[No] = np.minimum(np.maximum(0., self.var.topwater), self.var.EWRef)
            self.var.topwater = self.var.topwater - self.var.openWaterEvap[No]

            # if paddies are flooded, avail water is calculated before: top + avail, otherwise it is calculated here
            availWaterInfiltration = np.where(self.var.cropKC[No] > 0.75, 
                                              self.var.topwater, 
                                              self.var.topwater + availWaterInfiltration)

            # open water can evaporate more than maximum bare soil + transpiration because it is calculated from 
            # open water pot evaporation
            # h = self.var.potBareSoilEvap - self.var.openWaterEvap[No]
            self.var.potBareSoilEvap = np.maximum(0., self.var.potBareSoilEvap - self.var.openWaterEvap[No])
            # if open water revaporation is bigger than bare soil, transpiration rate is reduced
            # self.var.potTranspiration[No] = np.where( h > 0, self.var.potTranspiration[No], 
            #                                           np.maximum(0.,self.var.potTranspiration[No] + h))

        else:
            self.var.openWaterEvap[No] = 0.


        # if (dateVar['curr'] >= 0) and (No == 3):
        #     ii = 1

        # add capillary rise from groundwater if modflow is used
        if self.var.modflow:
            # if GW capillary rise saturates soil layers, water is sent to the above layer, then to runoff
            self.var.w3[No] = self.var.w3[No] + self.var.capillar
            # CAPRISE from GW to soilayer 3 , if this is full it is send to soil layer 2
            self.var.w2[No] = self.var.w2[No] + np.where(self.var.w3[No] > self.var.ws3[No], 
                                                          self.var.w3[No] - self.var.ws3[No], 0)
            self.var.w3[No] = np.minimum(self.var.ws3[No], self.var.w3[No])
            # CAPRISE from GW to soilayer 2 , if this is full it is send to soil layer 1
            self.var.w1[No] = self.var.w1[No] + np.where(self.var.w2[No] > self.var.ws2[No], 
                                                          self.var.w2[No] - self.var.ws2[No], 0)
            self.var.w2[No] = np.minimum(self.var.ws2[No], self.var.w2[No])
            # CAPRISE from GW to soilayer 1 , if this is full it is send to RUNOFF
            saverunofffromGW = +np.where(self.var.w1[No] > self.var.ws1[No], 
                                         self.var.w1[No] - self.var.ws1[No], 0)
            self.var.w1[No] = np.minimum(self.var.ws1[No], self.var.w1[No])

            # Now, we need to add transfer between soil layers  # MODIF LUCA TO IMPROVE MODFLOW COUPLING

            # Percolation -----------------------------------------------
            if No == 0:
                NoSoil = 0
            else:
                NoSoil = 1

            # Available water in both soil layers [m]
            availWater1 = np.maximum(0., self.var.w1[No] - self.var.wres1[No])
            availWater2 = np.maximum(0., self.var.w2[No] - self.var.wres2[No])
            availWater3 = np.maximum(0., self.var.w3[No] - self.var.wres3[No])

            satTerm2 = availWater2 / self.var.wrange2[No]
            satTerm3 = availWater3 / self.var.wrange3[No]

            # Saturation term in Van Genuchten equation (always between 0 and 1)
            satTerm2 = np.maximum(np.minimum(satTerm2, 1.0), 0)
            satTerm3 = np.maximum(np.minimum(satTerm3, 1.0), 0)

            # Unsaturated conductivity
            kUnSat2 = self.var.KSat2[NoSoil] * np.sqrt(satTerm2) * np.square(
                1 - (1 - satTerm2 ** self.var.genuInvM2[NoSoil]) ** self.var.genuM2[NoSoil])
            kUnSat3 = self.var.KSat3[NoSoil] * np.sqrt(satTerm3) * np.square(
                1 - (1 - satTerm3 ** self.var.genuInvM3[NoSoil]) ** self.var.genuM3[NoSoil])

            # ----------------------------------------------------------
            # Capillar Rise

            satTermFC1 = np.maximum(0., self.var.w1[No] - self.var.wres1[No]) / (
                self.var.wfc1[No] - self.var.wres1[No])
            satTermFC2 = np.maximum(0., self.var.w2[No] - self.var.wres2[No]) / (
                self.var.wfc2[No] - self.var.wres2[No])
            satTermFC3 = np.maximum(0., self.var.w3[No] - self.var.wres3[No]) / (
                self.var.wfc3[No] - self.var.wres3[No])
            capRise1 = np.minimum(np.maximum(0., (1 - satTermFC1) * kUnSat2), self.var.kunSatFC12[No])
            capRise2 = np.minimum(np.maximum(0., (1 - satTermFC2) * kUnSat3), self.var.kunSatFC23[No])

            self.var.w1[No] = self.var.w1[No] + capRise1
            self.var.w2[No] = self.var.w2[No] - capRise1 + capRise2
            # GW capillary rise has already been added to the soil
            self.var.w3[No] = self.var.w3[No] - capRise2

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
            # e.g. olive groves are adapted to dry climate, therefore they can extract more water from drying out 
            # soil than e.g. rice. The crop group number of olive groves is 4 and of rice fields is 1
            # for irrigation it is expected that the crop has a low adaptation to dry climate
        else:

            p = 1 / (0.76 + 1.5 * etpotMax) - 0.10 * (5 - self.var.cropGroupNumber)
            # soil water depletion fraction (easily available soil water)
            # Van Diepen et al., 1988: WOFOST 6.0, p.87
            # to avoid a strange behaviour of the p-formula's, ETRef is set to a maximum of
            # 10 mm/day. Thus, p will range from 0.15 to 0.45 at ETRef eq 10 and
            # CropGroupNumber 1-5
            p = np.where(self.var.cropGroupNumber <= 2.5, 
                         p + (etpotMax - 0.6) / (self.var.cropGroupNumber * (self.var.cropGroupNumber + 3)), 
                         p)
            # correction for crop groups 1 and 2 (Van Diepen et al, 1988)

        p = np.maximum(np.minimum(p, 1.0), 0.)
        # p is between 0 and 1 => if p =1 wcrit = wwp, if p= 0 wcrit = wfc
        # p is closer to 0 if evapo is bigger and cropgroup is smaller

        wCrit1 = ((1 - p) * (self.var.wfc1[No] - self.var.wwp1[No])) + self.var.wwp1[No]
        wCrit2 = ((1 - p) * (self.var.wfc2[No] - self.var.wwp2[No])) + self.var.wwp2[No]
        wCrit3 = ((1 - p) * (self.var.wfc3[No] - self.var.wwp3[No])) + self.var.wwp3[No]

        # Transpiration reduction factor (in case of water stress)
        rws1 = divideValues((self.var.w1[No] - self.var.wwp1[No]), (wCrit1 - self.var.wwp1[No]), default=1.)
        rws2 = divideValues((self.var.w2[No] - self.var.wwp2[No]), (wCrit2 - self.var.wwp2[No]), default=1.)
        rws3 = divideValues((self.var.w3[No] - self.var.wwp3[No]), (wCrit3 - self.var.wwp3[No]), default=1.)

        # with np.errstate(invalid='ignore', divide='ignore'):
        # rws1 = np.where((wCrit1 - self.var.wwp1[No]) > 0, 
        #                 (self.var.w1[No] - self.var.wwp1[No]) / (wCrit1 - self.var.wwp1[No]), 1.0)
        # rws2 = np.where((wCrit2 - self.var.wwp2[No]) > 0, 
        #                 (self.var.w2[No] - self.var.wwp2[No]) / (wCrit2 - self.var.wwp2[No]), 1.0)
        # rws3 = np.where((wCrit3 - self.var.wwp3[No]) > 0, 
        #                 (self.var.w3[No] - self.var.wwp3[No]) / (wCrit3 - self.var.wwp3[No]), 1.0)

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

        # if (dateVar['curr'] == 23) and (No == 1):
        #     ii = 1
        #     # print ('t', self.var.w1[No][0:3])

        self.var.w1[No] = self.var.w1[No] - ta1
        self.var.w2[No] = self.var.w2[No] - ta2
        self.var.w3[No] = self.var.w3[No] - ta3


        # -------------------------------------------------------------
        # Actual potential bare soil evaporation - upper layer
        self.var.actBareSoilEvap[No] = np.minimum(self.var.potBareSoilEvap, 
                                                  np.maximum(0., self.var.w1[No] - self.var.wres1[No]))
        self.var.actBareSoilEvap[No] = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, 0., 
                                                self.var.actBareSoilEvap[No])

        # no bare soil evaporation in the inundated paddy field
        if coverType == 'irrPaddy':
            self.var.actBareSoilEvap[No] = np.where(self.var.topwater > 0., 0., self.var.actBareSoilEvap[No])

        self.var.w1[No] = self.var.w1[No] - self.var.actBareSoilEvap[No]


        # -------------------------------------------------------------

        # Infiltration capacity
        # ========================================
        # first 2 soil layers to estimate distribution between runoff and infiltration
        soilWaterStorage = self.var.w1[No] + self.var.w2[No]
        soilWaterStorageCap = self.var.ws1[No] + self.var.ws2[No]
        relSat = soilWaterStorage / soilWaterStorageCap
        relSat = np.minimum(relSat, 1.0)

        # if np.min(self.var.w1[No]) < 0.:
        #     ii = 1

        # if (dateVar['curr'] == 23) and (No == 1):
        #     ii = 1
        #     print(No, self.var.w1[No][0:3])

        satAreaFrac = 1 - (1 - relSat) ** self.var.arnoBeta[No]
        # Fraction of pixel that is at saturation as a function of the ratio Theta1/ThetaS1. 
        # Distribution function taken from Zhao,1977, as cited in Todini, 1996 (JoH 175, 339-382)
        satAreaFrac = np.maximum(np.minimum(satAreaFrac, 1.0), 0.0)

        store = soilWaterStorageCap / (self.var.arnoBeta[No] + 1)
        potBeta = (self.var.arnoBeta[No] + 1) / self.var.arnoBeta[No]
        potInf = store - store * (1 - (1 - satAreaFrac) ** potBeta)




        # ------------------------------------------------------------------
        # calculate preferential flow

        if coverType == 'irrPaddy' or not (checkOption('preferentialFlow')):
            self.var.prefFlow[No] = 0.
        else:
            self.var.prefFlow[No] = availWaterInfiltration * relSat ** self.var.cPrefFlow
            self.var.prefFlow[No] = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, 0.0, self.var.prefFlow[No])

        if self.var.modflow:
            # multiplied by the fraction of ModFlow unsaturated cells
            self.var.prefFlow[No] = self.var.prefFlow[No] * (1 - self.var.capriseindex)

        # ---------------------------------------------------------
        # calculate infiltration
        # infiltration, limited with KSat1 and available water in topWaterLayer
        self.var.infiltration[No] = np.minimum(potInf, availWaterInfiltration - self.var.prefFlow[No])
        self.var.infiltration[No] = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, 0.0, 
                                             self.var.infiltration[No])
        self.var.directRunoff[No] = np.maximum(0., availWaterInfiltration - self.var.infiltration[No] - 
                                               self.var.prefFlow[No])

        if coverType == 'irrPaddy':
            self.var.topwater = np.maximum(0., self.var.topwater - self.var.infiltration[No])
            # if paddy fields flooded only runoff if topwater > 0.05m
            h = np.maximum(0., self.var.topwater - self.var.maxtopwater)
            self.var.directRunoff[No] = np.where(self.var.cropKC[No] > 0.75, h, self.var.directRunoff[No])
            self.var.topwater = np.maximum(0., self.var.topwater - self.var.directRunoff[No])


        # ModFlow
        if self.var.modflow:
            self.var.directRunoff[No] = self.var.directRunoff[No] + saverunofffromGW
            # ADDING EXCESS WATER FROM GW CAPILLARY RISE


        # infiltration to soilayer 1 , if this is full it is send to soil layer 2
        self.var.w1[No] = self.var.w1[No] + self.var.infiltration[No]
        self.var.w2[No] = self.var.w2[No] + np.where(self.var.w1[No] > self.var.ws1[No], 
                                                      self.var.w1[No] - self.var.ws1[No], 0)
        self.var.w1[No] = np.minimum(self.var.ws1[No], self.var.w1[No])

        # ----------------------------------------------------------
        # to the water demand module  # could not be done before from landcoverType_module because 
        # readAvlWater is needed

        # for plants availailabe water
        # availWaterPlant1 = np.maximum(0., self.var.w1[No] - self.var.wwp1[No]) * self.var.rootDepth[0][No]
        # availWaterPlant2 = np.maximum(0., self.var.w2[No] - self.var.wwp2[No]) * self.var.rootDepth[1][No]
        # availWaterPlant3 = np.maximum(0., self.var.w3[No] - self.var.wwp3[No]) * self.var.rootDepth[2][No]
        # readAvlWater = availWaterPlant1 + availWaterPlant2 + availWaterPlant3

        # Percolation -----------------------------------------------
        if No == 0:
            NoSoil = 0
        else:
            NoSoil = 1

        # Available water in both soil layers [m]
        availWater1 = np.maximum(0., self.var.w1[No] - self.var.wres1[No])
        availWater2 = np.maximum(0., self.var.w2[No] - self.var.wres2[No])
        availWater3 = np.maximum(0., self.var.w3[No] - self.var.wres3[No])


        satTerm2 = availWater2 / self.var.wrange2[No]
        satTerm3 = availWater3 / self.var.wrange3[No]

        # Saturation term in Van Genuchten equation (always between 0 and 1)
        satTerm2 = np.maximum(np.minimum(satTerm2, 1.0), 0)
        satTerm3 = np.maximum(np.minimum(satTerm3, 1.0), 0)

        # Unsaturated conductivity
        kUnSat2 = self.var.KSat2[NoSoil] * np.sqrt(satTerm2) * np.square(
            1 - (1 - satTerm2 ** self.var.genuInvM2[NoSoil]) ** self.var.genuM2[NoSoil])
        kUnSat3 = self.var.KSat3[NoSoil] * np.sqrt(satTerm3) * np.square(
            1 - (1 - satTerm3 ** self.var.genuInvM3[NoSoil]) ** self.var.genuM3[NoSoil])



        ## ----------------------------------------------------------
        # Capillar Rise

        satTermFC1 = np.maximum(0., self.var.w1[No] - self.var.wres1[No]) / (
            self.var.wfc1[No] - self.var.wres1[No])
        satTermFC2 = np.maximum(0., self.var.w2[No] - self.var.wres2[No]) / (
            self.var.wfc2[No] - self.var.wres2[No])
        satTermFC3 = np.maximum(0., self.var.w3[No] - self.var.wres3[No]) / (
            self.var.wfc3[No] - self.var.wres3[No])
        capRise1 = np.minimum(np.maximum(0., (1 - satTermFC1) * kUnSat2), self.var.kunSatFC12[No])
        capRise2 = np.minimum(np.maximum(0., (1 - satTermFC2) * kUnSat3), self.var.kunSatFC23[No])


        if self.var.modflow:
            # from Modflow
            self.var.capRiseFromGW[No] = self.var.capillar
        else:
            self.var.capRiseFromGW[No] = np.maximum(0., (1 - satTermFC3) * 
                                                    np.sqrt(self.var.KSat3[NoSoil] * kUnSat3))
            self.var.capRiseFromGW[No] = 0.5 * self.var.capRiseFrac * self.var.capRiseFromGW[No]
            self.var.capRiseFromGW[No] = np.minimum(np.maximum(0., self.var.storGroundwater), 
                                                    self.var.capRiseFromGW[No])

        self.var.w1[No] = self.var.w1[No] + capRise1
        self.var.w2[No] = self.var.w2[No] - capRise1 + capRise2
        if self.var.modflow:
            # GW capillary rise has already been added to the soil
            self.var.w3[No] = self.var.w3[No] - capRise2
        else:
            self.var.w3[No] = self.var.w3[No] - capRise2 + self.var.capRiseFromGW[No]

        # Percolation -----------------------------------------------
        # Available water in both soil layers [m]
        availWater1 = np.maximum(0., self.var.w1[No] - self.var.wres1[No])
        availWater2 = np.maximum(0., self.var.w2[No] - self.var.wres2[No])
        availWater3 = np.maximum(0., self.var.w3[No] - self.var.wres3[No])

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
        kUnSat1 = self.var.KSat1[NoSoil] * np.sqrt(satTerm1) * np.square(
            1 - (1 - satTerm1 ** self.var.genuInvM1[NoSoil]) ** self.var.genuM1[NoSoil])
        kUnSat2 = self.var.KSat2[NoSoil] * np.sqrt(satTerm2) * np.square(
            1 - (1 - satTerm2 ** self.var.genuInvM2[NoSoil]) ** self.var.genuM2[NoSoil])
        kUnSat3 = self.var.KSat3[NoSoil] * np.sqrt(satTerm3) * np.square(
            1 - (1 - satTerm3 ** self.var.genuInvM3[NoSoil]) ** self.var.genuM3[NoSoil])

        """
        # Courant condition for computed soil moisture fluxes:
        # if Courant gt CourantCrit: sub-steps needed for required numerical accuracy
        with np.errstate(invalid='ignore', divide='ignore'):
            courant1to2 = np.where(availWater1 == 0, 0, kUnSat1 / availWater1)
            courant2to3 = np.where(availWater2 == 0, 0, kUnSat2 / availWater2)
            courant3toGW = np.where(availWater3 == 0, 0, kUnSat3 / availWater3)

        # Flow between soil layers and flow to GW
        # need to be numerically stable, so number of sub-steps is
        # based on process with largest Courant number
        courantSoil = np.maximum(courant1to2, courant2to3, courant3toGW)
        # Number of sub-steps needed for required numerical
        # accuracy. Always greater than or equal to 1
        # Do not change, default value of 2.5. Generally combines sufficient numerical accuracy within a limited number of sub - steps
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
                satTerm1 = np.maximum(0., wtemp1 - self.var.wres1[No]) / self.var.wrange1[No]
                satTerm2 = np.maximum(0., wtemp2 - self.var.wres2[No]) / self.var.wrange2[No]
                satTerm3 = np.maximum(0., wtemp3 - self.var.wres3[No]) / self.var.wrange3[No]

                satTerm1 = np.maximum(np.minimum(satTerm1, 1.0), 0)
                satTerm2 = np.maximum(np.minimum(satTerm2, 1.0), 0)
                satTerm3 = np.maximum(np.minimum(satTerm3, 1.0), 0)

                # Unsaturated hydraulic conductivities
                kUnSat1 = self.var.KSat1[NoSoil] * np.sqrt(satTerm1) * np.square(
                    1 - (1 - satTerm1 ** self.var.genuInvM1[NoSoil]) ** self.var.genuM1[NoSoil])
                kUnSat2 = self.var.KSat2[NoSoil] * np.sqrt(satTerm2) * np.square(
                    1 - (1 - satTerm2 ** self.var.genuInvM2[NoSoil]) ** self.var.genuM2[NoSoil])
                kUnSat3 = self.var.KSat3[NoSoil] * np.sqrt(satTerm3) * np.square(
                    1 - (1 - satTerm3 ** self.var.genuInvM3[NoSoil]) ** self.var.genuM3[NoSoil])

            # Flux from top- to subsoil
            subperc1to2 = np.minimum(availWater1, np.minimum(kUnSat1 * DtSub, capLayer2))
            subperc2to3 = np.minimum(availWater2, np.minimum(kUnSat2 * DtSub, capLayer3))

            # Frozen soils do not facilitate percolation
            subperc1to2 = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, 0, subperc1to2)
            subperc2to3 = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, 0, subperc2to3)

            if self.var.modflow:
                # multiplied by the fraction of ModFlow unsaturated cells
                subperc3toGW = np.minimum(availWater3, np.minimum(kUnSat3 * DtSub, availWater3)) * (
                    1 - self.var.capriseindex)
            else:
                subperc3toGW = np.minimum(availWater3, np.minimum(kUnSat3 * DtSub, availWater3))

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

            self.var.perc1to2[No] += subperc1to2   # 0 if frozen
            self.var.perc2to3[No] += subperc2to3   # 0 if frozen
            self.var.perc3toGW[No] += subperc3toGW

        # When the soil is frozen (frostindex larger than threshold), no perc1 and 2
        self.var.perc1to2[No] = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, 0, 
                                         self.var.perc1to2[No])
        self.var.perc2to3[No] = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, 0, 
                                         self.var.perc2to3[No])

        # Update soil moisture
        self.var.w1[No] = self.var.w1[No] - self.var.perc1to2[No]
        testw = np.minimum(self.var.w1[No], 0)
        self.var.w1[No] = self.var.w1[No] - testw
        self.var.perc1to2[No] = self.var.perc1to2[No] + testw

        self.var.w2[No] = self.var.w2[No] + self.var.perc1to2[No] - self.var.perc2to3[No]
        testw = np.minimum(self.var.w2[No], 0)
        self.var.w2[No] = self.var.w2[No] - testw
        self.var.perc2to3[No] = self.var.perc2to3[No] + testw

        self.var.w3[No] = self.var.w3[No] + self.var.perc2to3[No] - self.var.perc3toGW[No]
        testw = np.minimum(self.var.w3[No], 0)
        self.var.w3[No] = self.var.w3[No] - testw
        self.var.perc3toGW[No] = self.var.perc3toGW[No] + testw

        # Compute the amount of water that could not infiltrate and add this water to the surface runoff
        self.var.theta1[No] = self.var.w1[No] / self.var.rootDepth[0][No]
        self.var.theta2[No] = self.var.w2[No] / self.var.rootDepth[1][No]
        self.var.theta3[No] = self.var.w3[No] / self.var.rootDepth[2][No]

        # ---------------------------------------------------------------------------------------------
        # total actual transpiration
        self.var.actTransTotal[No] = ta1 + ta2 + ta3

        self.var.actTransTotal_forest = self.var.actTransTotal[0] * self.var.fracVegCover[0]
        self.var.actTransTotal_grasslands = self.var.actTransTotal[1] * self.var.fracVegCover[1]
        self.var.actTransTotal_paddy = self.var.actTransTotal[2] * self.var.fracVegCover[2]
        self.var.actTransTotal_nonpaddy = self.var.actTransTotal[3] * self.var.fracVegCover[3]

        self.var.ET_crop_Irr_paddy = (self.var.actTransTotal_paddy + 
                                      (self.var.actBareSoilEvap[3] + self.var.openWaterEvap[2]) * 
                                      self.var.fracVegCover[2])
        self.var.ET_crop_Irr_paddy_fraccrop = np.where(self.var.fracVegCover[2] > 0, 
                                                       self.var.ET_crop_Irr_paddy / self.var.fracVegCover[2], 0)

        if self.var.includeCrops:  # checkOption('includeCrops') and checkOption('includeCropSpecificWaterUse'):
            if No == 3:

                # Method 1: Area proportional

                # for c in range(len(self.var.Crops)):
                #     self.var.actTransTotal_crops_Irr[c] = np.where(self.var.fracVegCover[3] > 0, self.var.fracCrops_Irr[c] / (self.var.fracVegCover[3]), 0) * self.var.actTransTotal_nonpaddy
                #     self.var.actTransTotal_crops_nonIrr[c] = np.where(self.var.fracVegCover[1] > 0, self.var.fracCrops_nonIrr[c] / (self.var.fracVegCover[1]), 0) * self.var.actTransTotal_paddy

                # Crop-specific transpiration (m) scales the land-class specific transpiration according to its
                # specific potential evapotranspiration and the land-class specific potential evapotranspiration

                for c in range(len(self.var.Crops)):

                    # Area and transpiration-Kc proportional
                    self.var.actTransTotal_crops_Irr[c] = np.where(
                        self.var.fracVegCover[3] * (self.var.cropKC[3] - self.var.minCropKC) > 0,
                        (self.var.fracCrops_Irr[c] * (self.var.currentKC[c] - self.var.minCropKC)) /
                        (self.var.fracVegCover[3] * (self.var.cropKC[3] - self.var.minCropKC)),
                        0) * self.var.actTransTotal_nonpaddy
                    
                    self.var.actTransTotal_crops_nonIrr[c] = np.where(
                        self.var.fracVegCover[1] * (self.var.cropKC[1] - self.var.minCropKC) > 0,
                        (self.var.fracCrops_nonIrr[c] * (self.var.currentKC[c] - self.var.minCropKC)) /
                        (self.var.fracVegCover[1] * (self.var.cropKC[1] - self.var.minCropKC)),
                        0) * self.var.actTransTotal_grasslands



                    self.var.ET_crop_Irr[c] = (self.var.actTransTotal_crops_Irr[c] +
                                               self.var.actBareSoilEvap[3] * self.var.fracCrops_Irr[c])
                    vars(self.var)['ET_crop_Irr_' + str(c)] = self.var.ET_crop_Irr[c].copy()
                    vars(self.var)['ET_crop_Irr_fraccrop_' + str(c)] = np.where(
                        self.var.fracCrops_Irr[c] > 0,
                        self.var.ET_crop_Irr[c] / self.var.fracCrops_Irr[c], 0)

                    self.var.actTransTotal_month_Irr[c] += self.var.ET_crop_nonIrr[c]

                    
                    self.var.ET_crop_nonIrr[c] = (self.var.actTransTotal_crops_nonIrr[c] +
                                                  self.var.actBareSoilEvap[1] * self.var.fracCrops_nonIrr[c])
                    vars(self.var)['ET_crop_nonIrr_' + str(c)] = self.var.ET_crop_nonIrr[c].copy()
                    vars(self.var)['ET_crop_nonIrr_fraccrop_' + str(c)] = np.where(
                        self.var.fracCrops_nonIrr[c] > 0,
                        self.var.ET_crop_nonIrr[c] / self.var.fracCrops_nonIrr[c], 0)

                    self.var.actTransTotal_month_nonIrr[c] += self.var.ET_crop_nonIrr[c]


                    self.var.irr_crop[c] = np.where(
                        self.var.frac_totalIrr * self.var.weighted_KC_Irr_woFallow > 0, 
                        (self.var.fracCrops_Irr[c] * self.var.currentKC[c]) / 
                        self.var.weighted_KC_Irr_woFallow_fullKc,
                        0) * self.var.act_irrNonpaddyWithdrawal
                    vars(self.var)['irr_crop_' + str(c)] = self.var.irr_crop[c].copy()


                    # daily ratio of actual transpiration to potential ET
                    self.var.ratio_a_p_nonIrr_daily[c] = np.where(
                        self.var.PotET_crop[c] * self.var.activatedCrops[c] > 0,
                        (self.var.actTransTotal_crops_nonIrr[c] + 
                         self.var.actBareSoilEvap[1] * self.var.fracCrops_nonIrr[c]) /
                        ((self.var.PotET_crop[c]) * self.var.fracCrops_nonIrr[c]),
                        0)  # This should always be <= 1.

                    self.var.ratio_a_p_Irr_daily[c] = np.where(
                        self.var.PotET_crop[c] * self.var.activatedCrops[c] > 0,
                        (self.var.actTransTotal_crops_Irr[c] + 
                         self.var.actBareSoilEvap[3] * self.var.fracCrops_Irr[c]) /
                        ((self.var.PotET_crop[c]) * self.var.fracCrops_Irr[c]),
                        0)  # This should always be <= 1.


                    self.var.irr_crop_month[c] += self.var.irr_crop[c]
                    if 'adminSegments' in binding:
                        self.var.irrM3_crop_month_segment[c] = npareatotal(
                            self.var.irr_crop_month[c] * self.var.cellArea,
                            self.var.adminSegments)

                self.var.irr_Paddy_month += self.var.act_irrPaddyWithdrawal
                if 'adminSegments' in binding:
                    self.var.irrM3_Paddy_month_segment = npareatotal(
                        self.var.irr_Paddy_month * self.var.cellArea,
                        self.var.adminSegments)


        # total actual evaporation + transpiration
        self.var.actualET[No] = (self.var.actualET[No] + self.var.actBareSoilEvap[No] + 
                                 self.var.openWaterEvap[No] + self.var.actTransTotal[No])
        # actual evapotranspiration can be bigger than pot, because openWater is taken from pot open water 
        # evaporation, therefore self.var.totalPotET[No] is adjusted
        self.var.totalPotET[No] = np.maximum(self.var.totalPotET[No], self.var.actualET[No])
        # groundwater recharge
        toGWorInterflow = self.var.perc3toGW[No] + self.var.prefFlow[No]
        self.var.interflow[No] = self.var.percolationImp * toGWorInterflow

        if self.var.modflow:
            self.var.gwRecharge[No] = (1 - self.var.percolationImp) * toGWorInterflow
        else:
            self.var.gwRecharge[No] = ((1 - self.var.percolationImp) * toGWorInterflow - 
                                       self.var.capRiseFromGW[No])
            # Check if gwRecharge < 0
            testgw = np.minimum(self.var.gwRecharge[No], 0)
            self.var.gwRecharge[No] = self.var.gwRecharge[No] - testgw
            self.var.capRiseFromGW[No] = self.var.capRiseFromGW[No] + testgw



