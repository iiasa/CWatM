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


def rootZoneStress(var, No, irrigated):
    """
    Water stress factor of the whole root zone of a land cover (as LISFLOOD soilloop.py).

    Water above wilting point / critical water above wilting point, both weighted with the root fraction of the
    soil layers: a layer without roots drops out, a wet layer makes up for a dry one (before 2026-11 one factor per
    layer, each clipped to 0..1). Used by soil.dynamic (transpiration) and water_demand/irrigation.py (irrigation
    demand of non-paddy), so that irrigation starts at the stress the plants feel.

    Parameters
    ----------
    var : object
        model variables (or the SubVar view of the cells with this land cover)
    No : int
        land cover number (0 forest, 1 grassland, 2 paddy, 3 non-paddy)
    irrigated : bool
        True for paddy and non-paddy: crop group 1 (low adaptation to dry climate), else the crop group number map

    Returns
    -------
    rws : numpy.ndarray
        water stress factor 0..1 (1 = no stress, 0 = wilting point)
    wCrit : tuple of numpy.ndarray
        critical soil moisture of layer 1, 2, 3 [m]
    avail : tuple of numpy.ndarray
        water above wilting point of layer 1, 2, 3 [m], 0 in layers without roots
    """

    etpotMax = np.minimum(100 * var.totalPotET[No], 1.0)
    # to avoid a strange behaviour of the p-formula's, ETRef is set to a maximum of 10 mm/day.
    # etpotMax in cm/d for the formular from Van Diepen

    if irrigated:
        p = 1 / (0.76 + 1.5 * etpotMax) - 0.4
        # soil water depletion fraction (easily available soil water) # Van Diepen et al., 1988: WOFOST 6.0, p.87.
        p = p + (etpotMax - 0.6) / 4
        # correction for crop group 1  (Van Diepen et al, 1988) -> p between 0.14 - 0.77
        # The crop group number is a indicator of adaptation to dry climate,
        # e.g. olive groves are adapted to dry climate, therefore they can extract more water from drying out
        # soil than e.g. rice. The crop group number of olive groves is 4 and of rice fields is 1
        # for irrigation it is expected that the crop has a low adaptation to dry climate
    else:
        p = 1 / (0.76 + 1.5 * etpotMax) - 0.10 * (5 - var.cropGroupNumber)
        # soil water depletion fraction (easily available soil water)
        # Van Diepen et al., 1988: WOFOST 6.0, p.87
        # to avoid a strange behaviour of the p-formula's, ETRef is set to a maximum of
        # 10 mm/day. Thus, p will range from 0.15 to 0.45 at ETRef eq 10 and
        # CropGroupNumber 1-5
        p = np.where(var.cropGroupNumber <= 2.5,
                     p + (etpotMax - 0.6) / (var.cropGroupNumber * (var.cropGroupNumber + 3)),
                     p)
        # correction for crop groups 1 and 2 (Van Diepen et al, 1988)

    p = np.maximum(np.minimum(p, 1.0), 0.)
    # p is between 0 and 1 => if p =1 wcrit = wwp, if p= 0 wcrit = wfc
    # p is closer to 0 if evapo is bigger and cropgroup is smaller

    wCrit1 = ((1 - p) * (var.wfc1[No] - var.wwp1[No])) + var.wwp1[No]
    wCrit2 = ((1 - p) * (var.wfc2[No] - var.wwp2[No])) + var.wwp2[No]
    wCrit3 = ((1 - p) * (var.wfc3[No] - var.wwp3[No])) + var.wwp3[No]

    a1 = var.adjRoot[0][No]
    a2 = var.adjRoot[1][No]
    a3 = var.adjRoot[2][No]
    # water above wilting point, only in layers with roots
    avail1 = np.where(a1 > 0, np.maximum(var.w1[No] - var.wwp1[No], 0.), 0.)
    avail2 = np.where(a2 > 0, np.maximum(var.w2[No] - var.wwp2[No], 0.), 0.)
    avail3 = np.where(a3 > 0, np.maximum(var.w3[No] - var.wwp3[No], 0.), 0.)
    availRoot = a1 * avail1 + a2 * avail2 + a3 * avail3
    critRoot = (a1 * (wCrit1 - var.wwp1[No]) + a2 * (wCrit2 - var.wwp2[No]) +
                a3 * (wCrit3 - var.wwp3[No]))
    # critRoot = 0 (p = 1: wCrit = wilting point) -> no water stress
    rws = np.maximum(np.minimum(divideValues(availRoot, critRoot, default=1.), 1.), 0.)
    return rws, (wCrit1, wCrit2, wCrit3), (avail1, avail2, avail3)


def arnoInfiltrationCapacity(w1, w2, ws1, ws2, arnoBeta):
    """
    Infiltration capacity of soil layers 1 + 2 (Arno scheme).

    Fraction of the cell at saturation as a function of the relative saturation: distribution function from
    Zhao 1977, as cited in Todini 1996 (JoH 175, 339-382). Used by soil.dynamic and water_demand/irrigation.py
    (limit of the non-paddy irrigation).

    Parameters
    ----------
    w1, w2 : numpy.ndarray
        water storage in soil layer 1 and 2 [m]
    ws1, ws2 : numpy.ndarray
        storage at saturation of soil layer 1 and 2 [m]
    arnoBeta : numpy.ndarray
        shape of the soil water capacity distribution curve [-]

    Returns
    -------
    potInf : numpy.ndarray
        infiltration capacity [m]
    relSat : numpy.ndarray
        relative saturation of layers 1 + 2, at most 1 [-]
    """
    soilWaterStorageCap = ws1 + ws2
    relSat = np.minimum((w1 + w2) / soilWaterStorageCap, 1.0)
    # (1 - satAreaFrac) ** ((arnoBeta + 1) / arnoBeta) = (1 - relSat) ** (arnoBeta + 1) = relSatBeta * (1 - relSat)
    # with satAreaFrac = 1 - relSatBeta (arnoBeta >= 0.01); limited to 1 like a clamp of satAreaFrac if relSat < 0
    relSatBeta = (1 - relSat) ** arnoBeta
    store = soilWaterStorageCap / (arnoBeta + 1)
    potInf = store - store * (1 - np.minimum(relSatBeta * (1 - relSat), 1.0))
    return potInf, relSat


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
    
    Based on concepts from PCR-GLOBWB, LISFLOOD, and HBV models.
    References the Arno scheme for spatially variable soil moisture.

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    capRiseFrac                          Array         fraction of a grid cell where capillar rise may happen                  --   
    modflow                              Flag          True if modflow_coupling = True in settings file                        bool 
    activatedCrops                       Array         Fraction of area a specific crop is planted                             --   
    currentKC                            Array         Current crop coefficient for specific crops                             --   
    weighted_KC_Irr_woFallow             Array         (KC - minCropKC) x fraction of crops, general crop on non-paddy         --   
    storGroundwater                      Array         Groundwater storage (non-fossil), used without MODFLOW                  m    
    includeCrops                         Flag          1 when includeCrops=True in Settings, 0 otherwise                       bool 
    Crops                                Array         Internal: List of specific crops and Kc/Ky parameters                   --   
    potTranspiration                     Array         Potential transpiration (after removing of evaporation)                 m    
    cropKC                               Array         crop coefficient for each of the 4 different land cover types (forest,  --   
    minCropKC                            Array         minimum crop factor (default 0.2)                                       --   
    rootDepth                            Array         rootdepth of different layers                                           m    
    KSat1                                Array         Saturated conductivity layer 1                                          m/day
    KSat2                                Array         Saturated conductivity layer 2                                          m/day
    KSat3                                Array         Saturated conductivity layer 3                                          m/day
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
    kunSatFC12                           Array         Unsat. conductivity at field capacity layer 2 (van Genuchten, Mualem)   m/day
    kunSatFC23                           Array         Unsat. conductivity at field capacity layer 3 (van Genuchten, Mualem)   m/day
    arnoBeta                             Array         arnoBeta defines the shape of soil water capacity distribution curve a  --   
    adjRoot                              Array         Root fraction of soil layer 1, 2, 3 per land cover                      --   
    maxtopwater                          Array         maximum heigth of topwater                                              m    
    paddyFloodKC                         Array         Input, irrPaddy_floodKC (0.75), paddy flooded + irrigated if cropKC >   --   
    EWRef                                Array         potential evaporation rate from water surface                           m    
    availWaterInfiltration               Array         quantity of water reaching the soil after interception, more snowmelt   m    
    FrostDay                             Array         frost index in soil [degree days] based on Molnau and Bissel (1983, A   --   
    irr_Paddy_month                      Array         Paddy irrigation withdrawal, running sum of the month                   m    
    ET_crop_Irr_paddy                    Array         Actual ET of paddy x paddy fraction (transp. + soil + open water)       m    
    ET_crop_Irr_paddy_fraccrop           Array         Actual ET of paddy per paddy area                                       m    
    fracCrops_Irr                        Array         Fraction of cell currently planted with specific irrigated crops        --   
    fracCrops_nonIrr                     Array         Fraction of cell currently planted with specific non-irr crops          --   
    actTransTotal_month_nonIrr           Array         Internal variable: Running total of  transpiration for specific non-ir  m    
    actTransTotal_month_Irr              Array         Internal variable: Running total of  transpiration for specific irriga  m    
    irr_crop_month                       Array         Irrigation withdrawal per irrigated crop, running sum of the month      m    
    frac_totalIrr                        Array         Fraction sown with specific irrigated crops                             --   
    weighted_KC_Irr_woFallow_fullKc      Array         KC x fraction of crops and general crop on non-paddy (no fallow)        --   
    totalPotET                           Array         Potential evaporation per land use class                                m    
    potBareSoilEvap                      Array         potential bare soil evaporation (calculated with minus snow evaporatio  m    
    PotET_crop                           Array         Potential ET of irrigated crops (non-paddy) [crop specific]             m    
    PotET_crop_nonIrr                    Array         Potential ET of rainfed crops (grassland) [crop specific]               m    
    actualET                             Array         simulated evapotranspiration from soil, flooded area and vegetation     m    
    soilLayers                           List          Number of soil layers                                                   --   
    soildepth                            Array         Thickness of the 3 soil layers                                          m    
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
    percolationImp                       Array         Fraction of area where percolation to groundwater is impeded            --   
    cropGroupNumber                      Array         Crop group number 1-5 (adaptation to dry climate), WOFOST 6.0           --   
    cPrefFlow                            Array         Factor influencing preferential flow (flow from surface to GW)          --   
    pumping_actual                       Array         This is here, as groundwater.py is not called if MODFLOW is used        --   
    rws                                  Array         Root zone water stress factor per land cover: 1 no stress, 0 wilting pt --   
    actBareSoilEvap                      Array         Simulated evaporation from the first soil layer                         m    
    prefFlow                             Array         Flow going directly from soil surface to groundwater [land class speci  m    
    infiltration                         Array         Water actually infiltrating the soil                                    m    
    capRiseFromGW                        Array         Simulated capillary rise from groundwater                               m    
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
    ET_crop_Irr                          Array         Actual ET per irrigated crop (transp. + bare soil) x crop fraction      m    
    ET_crop_nonIrr                       Array         Actual ET per rainfed crop (transp. + bare soil) x crop fraction        m    
    irr_crop                             Array         Non-paddy irrigation withdrawal per irrigated crop (by KC x fraction)   m    
    ratio_a_p_nonIrr_daily               Array         Daily ratio actual / potential ET per rainfed crop                      --   
    ratio_a_p_Irr_daily                  Array         Daily ratio actual / potential ET per irrigated crop                    --   
    irrM3_crop_month_segment             Array         Irrigation per irrigated crop and admin segment, sum of the month       m3   
    irrM3_Paddy_month_segment            Array         Paddy irrigation per admin segment, sum of the month                    m3   
    gwRecharge                           Array         groundwater recharge                                                    m    
    gwRecharge2                          Array         Recharge from layer 3 (without preferential flow), >= 0, no MODFLOW     m    
    baseflow                             Array         simulated baseflow (= groundwater discharge to river)                   m    
    capillar                             Array         Flow from groundwater to the third CWATM soil layer. Used with MODFLOW  m    
    capriseindex                         Array         computing saturated fraction of each CWatM cells (where water table >=  --   
    soildepth12                          Array         Total thickness of layer 2 and 3                                        m    
    fracVegCover                         Array         Fraction of specific land covers (0=forest, 1=grasslands, etc.)         --   
    adminSegments                        Array         Administrative segments for the crop irrigation totals                  Int  
    cellArea                             Array         Area of cell                                                            m2   
    act_irrConsumption                   Array         actual irrigation water consumption                                     m    
    act_irrNonpaddyWithdrawal            Array         non-paddy irrigation withdrawal                                         m    
    act_irrPaddyWithdrawal               Array         paddy irrigation withdrawal                                             m    
    recharge_limit                       Array         Recharge limit with MODFLOW (vertical permeability, low perm. cover)    m/day
    modflow_seepage                      Flag          Seepage scheme with MODFLOW: modflow_seepage in settings, default True  bool 
    seepageOn                            Flag          True if modflow_coupling = True and modflow_seepage = True              bool 
    saturatedFrac                        Array         Share of the cell with the water table at the surface (seepage scheme)  --   
    seepage                              Array         MODFLOW outflow not taken up by the soil, goes to the seepage pond      m    
    capRiseFromAquifer                   Array         Capillary rise from the aquifer (seepage scheme), negative recharge     m    
    capRiseAquiferLimit                  Array         Max. capillary rise from the aquifer: 10 % of layer-1 storage per day   m    
    seepagePond                          Array         Seepage pond per land cover (max. 0.1 m x saturated share)              m    
    seepageEvap                          Array         Seepage pond evap.: pond area x (max(EWRef, pot. ET) - actual soil ET)  m    
    pondOverflow                         Array         Seepage pond overflow to direct runoff (rest after the soil) per cover  m    
    pondarea                             Array         Pond area: max(capriseindex, saturatedFrac), share of soil covers       --   
    pondToSoil                           Array         Seepage pond overflow into the soil (layer 3, 2 up to field cap.)       m    
    pondDepth                            Number        Depth of the seepage pond over the pond area (seepage_pond_depth)       m    
    ta1                                  Array         Transpiration from soil layer 1 per land cover                          m    
    ta2                                  Array         Transpiration from soil layer 2 per land cover                          m    
    ta3                                  Array         Transpiration from soil layer 3 per land cover                          m    
    capRise2to1                          Array         Flow layer 2 -> 1: capillary rise + overflow of GW capillary rise       m    
    capRise3to2                          Array         Flow layer 3 -> 2: capillary rise + overflow of GW capillary rise       m    
    excess1to2                           Array         Infiltration above the storage capacity of layer 1 -> layer 2           m    
    capOverflowRunoff                    Array         MODFLOW capillary rise overflowing soil layer 1 -> direct runoff        m    
    pondToSoil3                          Array         Part of pondToSoil into soil layer 3 (the rest into layer 2)            m    
    snowEvap                             Array         Evaporation from snow (sublimation)                                     m    
    interceptEvap                        Array         Simulated evaporation from interception storage                         m    
    nonFossilGroundwaterAbs              Array         Non-fossil groundwater abstraction (today, before soil)                 m    
    ===================================  ==========    ======================================================================  =====

    """

    # variables written by dynamic(): per land cover (row No) and per cell
    # used by landcoverType.SubVar.scatter if soil is calculated only on cells with this land cover
    # -> a new self.var.xxx[No] = ... in dynamic() has to be added here too
    WRITE_LC = ['w1', 'w2', 'w3', 'openWaterEvap', 'actBareSoilEvap', 'prefFlow', 'infiltration',
                'directRunoff', 'capRiseFromGW', 'perc1to2', 'perc2to3', 'perc3toGW', 'theta1', 'theta2',
                'theta3', 'actTransTotal', 'actualET', 'totalPotET', 'interflow', 'gwRecharge', 'gwRecharge2',
                # fluxes of the single soil layers (WaterBalance output)
                'ta1', 'ta2', 'ta3', 'capRise2to1', 'capRise3to2', 'excess1to2', 'capOverflowRunoff', 'rws',
                # seepage scheme (MODFLOW, lists of arrays per land cover with soil)
                'seepage', 'capRiseFromAquifer', 'seepagePond', 'seepageEvap', 'pondToSoil', 'pondOverflow', 'pondToSoil3']
    WRITE_CELL = ['topwater', 'pondarea']

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

        # ------------ Crop group number ---------------------------------------------------
        self.var.cropGroupNumber = loadmap('cropgroupnumber')
        # soil water depletion fraction, Van Diepen et al., 1988: WOFOST 6.0, p.86, Doorenbos et. al 1978
        # crop groups for formular in van Diepen et al, 1988

        # ------------ Preferential Flow constant ------------------------------------------
        self.var.cPrefFlow = loadmap('preferentialFlowConstant')

        # ------------ SOIL DEPTH ----------------------------------------------------------
        # soil thickness and storage

        self.var.soildepth = np.tile(globals.inZero, (self.var.soilLayers, 1))

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
        # seepage scheme with MODFLOW (modflow_seepage, set in groundwater_modflow/transient.py): off without MODFLOW
        self.var.modflow_seepage = False

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

        availWaterInfiltration = self.var.availWaterInfiltration[No] + self.var.act_irrConsumption[No]
        # frozen soil somewhere today: otherwise the np.where(FrostDay, 0, ..) are skipped (speed, same result)
        frost = np.any(self.var.FrostDay)
        # upward fluxes between the soil layers (capillary rise and overflow of the capillary rise from groundwater)
        # and capillary rise overflowing layer 1 to runoff - for the water balance of each layer (WaterBalance output)
        self.var.capRise2to1[No] = 0.
        self.var.capRise3to2[No] = 0.
        self.var.capOverflowRunoff[No] = 0.
        # availWaterInfiltration = water net from precipitation (- soil - interception - snow + snow melt) + 
        # water for irrigation

        potBareSoilEvap = self.var.potBareSoilEvap
        # a local soil evap to be changed only by irrpaddy or irrigation
        if coverType == 'irrPaddy':
            # depending on the crop calender -> here if cropKC > paddyFloodKC (default 0.75) paddies are flooded
            # up to maxtopwater (default 50 mm)
            self.var.topwater = np.where(self.var.cropKC[No] > self.var.paddyFloodKC,
                                         self.var.topwater + availWaterInfiltration, 
                                         self.var.topwater)

            # open water evaporation from the paddy field - using potential evaporation from open water, but not more
            # than the crop based potential ET of the paddy minus snow and interception evaporation (the crop
            # coefficient of rice includes the evaporation of the water surface, FAO 56)
            maxOpenWaterEvap = np.maximum(0., self.var.totalPotET[No] - self.var.snowEvap - self.var.interceptEvap[No])
            self.var.openWaterEvap[No] = np.minimum(np.maximum(0., self.var.topwater),
                                                    np.minimum(self.var.EWRef, maxOpenWaterEvap))
            self.var.topwater = self.var.topwater - self.var.openWaterEvap[No]

            # if paddies are flooded, avail water is calculated before: top + avail, otherwise it is calculated here
            availWaterInfiltration = np.where(self.var.cropKC[No] > self.var.paddyFloodKC,
                                              self.var.topwater,
                                              self.var.topwater + availWaterInfiltration)

            # the open water evaporation replaces the bare soil evaporation; the part above the bare soil evaporation
            # is taken from the potential transpiration -> open water + bare soil + transpiration <= potential ET
            # (before 2026-11 open water evaporation up to EWRef plus the full transpiration)
            potBareSoilEvap = np.maximum(0., self.var.potBareSoilEvap - self.var.openWaterEvap[No])
            potTransp = np.maximum(0., self.var.potTranspiration[No] -
                                   np.maximum(0., self.var.openWaterEvap[No] - self.var.potBareSoilEvap))

        else:
            self.var.openWaterEvap[No] = 0.
            potTransp = self.var.potTranspiration[No]

        # bare soil evaporation not bigger than potential ET minus snow and interception evaporation
        # (only matters if potential ET < bare soil part, then potTranspiration is already 0)
        potBareSoilEvap = np.minimum(potBareSoilEvap, np.maximum(0., self.var.totalPotET[No] - self.var.snowEvap -
                                                                 self.var.interceptEvap[No]))

        # soil parameters: 0 forest, 1 all other land covers
        NoSoil = 0 if No == 0 else 1

        # add capillary rise from groundwater if modflow is used
        if self.var.modflow:
            capillar = self.var.capillar
            if self.var.seepageOn:
                # seepage scheme: capillary rise into layer 3 by the depth to water (as without MODFLOW, capRiseFrac of
                # capillarRise.py), supplied from the MODFLOW outflow first, then from the aquifer (capRiseAquiferLimit,
                # groundwater_modflow/transient.py); the rest of the outflow is seepage on the surface
                availWater3 = np.maximum(0., self.var.w3[No] - self.var.wres3[No])
                satTerm3 = np.minimum(availWater3 / self.var.wrange3[No], 1.0)   # >= 0: availWater3 >= 0
                kUnSat3 = self.var.KSat3[NoSoil] * np.sqrt(satTerm3) * np.square(
                    1 - (1 - satTerm3 ** self.var.genuInvM3[NoSoil]) ** self.var.genuM3[NoSoil])
                satTermFC3 = availWater3 / (self.var.wfc3[No] - self.var.wres3[No])
                potCapRise = 0.5 * self.var.capRiseFrac * np.maximum(0., 1 - satTermFC3) * np.sqrt(
                    self.var.KSat3[NoSoil] * kUnSat3)
                fromOutflow = np.minimum(potCapRise, self.var.capillar)
                self.var.capRiseFromAquifer[No] = np.minimum(potCapRise - fromOutflow, self.var.capRiseAquiferLimit)
                self.var.seepage[No] = self.var.capillar - fromOutflow
                capillar = fromOutflow + self.var.capRiseFromAquifer[No]
            # if GW capillary rise saturates soil layers, water is sent to the above layer, then to runoff
            self.var.w3[No] = self.var.w3[No] + capillar
            # CAPRISE from GW to soilayer 3 , if this is full it is send to soil layer 2
            over3to2 = np.maximum(self.var.w3[No] - self.var.ws3[No], 0.)
            self.var.w2[No] = self.var.w2[No] + over3to2
            self.var.w3[No] = np.minimum(self.var.ws3[No], self.var.w3[No])
            # CAPRISE from GW to soilayer 2 , if this is full it is send to soil layer 1
            over2to1 = np.maximum(self.var.w2[No] - self.var.ws2[No], 0.)
            self.var.w1[No] = self.var.w1[No] + over2to1
            self.var.w2[No] = np.minimum(self.var.ws2[No], self.var.w2[No])
            # CAPRISE from GW to soilayer 1 , if this is full it is send to RUNOFF
            saverunofffromGW = np.maximum(self.var.w1[No] - self.var.ws1[No], 0.)
            self.var.w1[No] = np.minimum(self.var.ws1[No], self.var.w1[No])
            self.var.capRise3to2[No] = self.var.capRise3to2[No] + over3to2
            self.var.capRise2to1[No] = self.var.capRise2to1[No] + over2to1
            self.var.capOverflowRunoff[No] = saverunofffromGW

        # ---------------------------------------------------------
        # calculate transpiration
        # ***** SOIL WATER STRESS ************************************
        # root zone water stress factor (also used by the irrigation demand, water_demand/irrigation.py)
        a1 = self.var.adjRoot[0][No]
        a2 = self.var.adjRoot[1][No]
        a3 = self.var.adjRoot[2][No]
        self.var.rws[No], (wCrit1, wCrit2, wCrit3), (avail1, avail2, avail3) = rootZoneStress(
            self.var, No, coverType in ('irrPaddy', 'irrNonPaddy'))

        # actual transpiration of the root zone, 0 when soil is frozen, limited by the water above wilting point
        potTa = np.where(self.var.FrostDay, 0., potTransp) if frost else potTransp
        ta = np.minimum(potTa * self.var.rws[No], avail1 + avail2 + avail3)

        # from which layer (no order, as LISFLOOD in 2 steps): 1st the water above the critical soil moisture,
        # proportional to this water in the layers; 2nd the rest proportional to the water above wilting point left
        # -> sum of the layers = ta, no layer below wilting point
        unstr1 = np.where(a1 > 0, np.maximum(self.var.w1[No] - wCrit1, 0.), 0.)
        unstr2 = np.where(a2 > 0, np.maximum(self.var.w2[No] - wCrit2, 0.), 0.)
        unstr3 = np.where(a3 > 0, np.maximum(self.var.w3[No] - wCrit3, 0.), 0.)
        unstrSum = unstr1 + unstr2 + unstr3
        taUnstr = np.minimum(ta, unstrSum)
        fracUnstr = divideValues(taUnstr, unstrSum)
        ta1 = fracUnstr * unstr1
        ta2 = fracUnstr * unstr2
        ta3 = fracUnstr * unstr3
        left1 = np.maximum(avail1 - ta1, 0.)
        left2 = np.maximum(avail2 - ta2, 0.)
        left3 = np.maximum(avail3 - ta3, 0.)
        # <= 1 (rest <= water left), min only against rounding
        fracLeft = np.minimum(divideValues(ta - taUnstr, left1 + left2 + left3), 1.)
        ta1 = ta1 + fracLeft * left1
        ta2 = ta2 + fracLeft * left2
        ta3 = ta3 + fracLeft * left3

        self.var.w1[No] = self.var.w1[No] - ta1
        self.var.w2[No] = self.var.w2[No] - ta2
        self.var.w3[No] = self.var.w3[No] - ta3


        # -------------------------------------------------------------
        # Actual potential bare soil evaporation - upper layer
        self.var.actBareSoilEvap[No] = np.minimum(potBareSoilEvap, np.maximum(0., self.var.w1[No] - self.var.wres1[No]))
        if frost:
            self.var.actBareSoilEvap[No] = np.where(self.var.FrostDay, 0., self.var.actBareSoilEvap[No])

        # no bare soil evaporation in the inundated paddy field
        if coverType == 'irrPaddy':
            self.var.actBareSoilEvap[No] = np.where(self.var.topwater > 0., 0., self.var.actBareSoilEvap[No])

        self.var.w1[No] = self.var.w1[No] - self.var.actBareSoilEvap[No]


        # -------------------------------------------------------------

        # Infiltration capacity (Arno scheme) of layers 1 + 2, relSat also for the preferential flow
        potInf, relSat = arnoInfiltrationCapacity(self.var.w1[No], self.var.w2[No], self.var.ws1[No],
                                                  self.var.ws2[No], self.var.arnoBeta[No])




        # ------------------------------------------------------------------
        # calculate preferential flow

        if coverType == 'irrPaddy' or not (checkOption('preferentialFlow')):
            self.var.prefFlow[No] = 0.
        else:
            self.var.prefFlow[No] = availWaterInfiltration * relSat ** self.var.cPrefFlow
            if frost:
                self.var.prefFlow[No] = np.where(self.var.FrostDay, 0.0, self.var.prefFlow[No])

        if self.var.modflow:
            # multiplied by the fraction of ModFlow unsaturated cells - seepage scheme: the unsaturated share from the
            # sub-grid elevation (capillarRise.py), no 0/1 switch of whole ModFlow cells (2-day flip-flop)
            saturated = self.var.saturatedFrac if self.var.seepageOn else self.var.capriseindex
            self.var.prefFlow[No] = self.var.prefFlow[No] * (1 - saturated)

        # ---------------------------------------------------------
        # calculate infiltration
        # infiltration, limited by the infiltration capacity potInf (Arno scheme) and the water reaching the soil
        self.var.infiltration[No] = np.minimum(potInf, availWaterInfiltration - self.var.prefFlow[No])
        if frost:
            self.var.infiltration[No] = np.where(self.var.FrostDay, 0.0, self.var.infiltration[No])
        self.var.directRunoff[No] = np.maximum(0., availWaterInfiltration - self.var.infiltration[No] - 
                                               self.var.prefFlow[No])

        if coverType == 'irrPaddy':
            self.var.topwater = np.maximum(0., self.var.topwater - self.var.infiltration[No])
            # if paddy fields flooded only runoff if topwater > maxtopwater
            h = np.maximum(0., self.var.topwater - self.var.maxtopwater)
            self.var.directRunoff[No] = np.where(self.var.cropKC[No] > self.var.paddyFloodKC, h,
                                                 self.var.directRunoff[No])
            self.var.topwater = np.maximum(0., self.var.topwater - self.var.directRunoff[No])


        # ModFlow
        if self.var.modflow:
            self.var.directRunoff[No] = self.var.directRunoff[No] + saverunofffromGW
            # ADDING EXCESS WATER FROM GW CAPILLARY RISE


        # infiltration to soilayer 1 , if this is full it is send to soil layer 2
        self.var.w1[No] = self.var.w1[No] + self.var.infiltration[No]
        self.var.excess1to2[No] = np.maximum(self.var.w1[No] - self.var.ws1[No], 0.)
        self.var.w2[No] = self.var.w2[No] + self.var.excess1to2[No]
        self.var.w1[No] = np.minimum(self.var.ws1[No], self.var.w1[No])

        # Percolation -----------------------------------------------
        # Available water in soil layers 2 and 3 [m] (for the capillary rise)
        availWater2 = np.maximum(0., self.var.w2[No] - self.var.wres2[No])
        availWater3 = np.maximum(0., self.var.w3[No] - self.var.wres3[No])


        satTerm2 = availWater2 / self.var.wrange2[No]
        satTerm3 = availWater3 / self.var.wrange3[No]

        # Saturation term in Van Genuchten equation (between 0 and 1: availWater >= 0)
        satTerm2 = np.minimum(satTerm2, 1.0)
        satTerm3 = np.minimum(satTerm3, 1.0)

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
        capRise1 = np.minimum(np.maximum(0., (1 - satTermFC1) * kUnSat2), self.var.kunSatFC12[No])
        capRise2 = np.minimum(np.maximum(0., (1 - satTermFC2) * kUnSat3), self.var.kunSatFC23[No])


        if self.var.modflow:
            # from Modflow, already added to the soil above (seepage scheme: the outflow without the seepage, plus the
            # capillary rise from the aquifer)
            self.var.capRiseFromGW[No] = capillar
        else:
            satTermFC3 = np.maximum(0., self.var.w3[No] - self.var.wres3[No]) / (
                self.var.wfc3[No] - self.var.wres3[No])
            self.var.capRiseFromGW[No] = np.maximum(0., (1 - satTermFC3) *
                                                    np.sqrt(self.var.KSat3[NoSoil] * kUnSat3))
            self.var.capRiseFromGW[No] = 0.5 * self.var.capRiseFrac * self.var.capRiseFromGW[No]
            # limited by groundwater storage left after today's abstraction (water demand runs before soil)
            # -> groundwater storage cannot become negative by a negative gwRecharge
            self.var.capRiseFromGW[No] = np.minimum(np.maximum(0., self.var.storGroundwater -
                                                    self.var.nonFossilGroundwaterAbs), self.var.capRiseFromGW[No])
            # not above saturation of layer 3 (after capRise2 to layer 2), otherwise negative percolation in the loop
            # (guard, not seen in Morava/Bhima: only a thin layer 3 with a high KSat3)
            self.var.capRiseFromGW[No] = np.minimum(self.var.capRiseFromGW[No],
                                                    np.maximum(0., self.var.ws3[No] - self.var.w3[No] + capRise2))

        self.var.w1[No] = self.var.w1[No] + capRise1
        self.var.w2[No] = self.var.w2[No] - capRise1 + capRise2
        self.var.capRise2to1[No] = self.var.capRise2to1[No] + capRise1
        self.var.capRise3to2[No] = self.var.capRise3to2[No] + capRise2
        if self.var.modflow:
            # GW capillary rise has already been added to the soil
            self.var.w3[No] = self.var.w3[No] - capRise2
        else:
            self.var.w3[No] = self.var.w3[No] - capRise2 + self.var.capRiseFromGW[No]

        # Percolation -----------------------------------------------
        # Available water in the three soil layers [m]
        availWater1 = np.maximum(0., self.var.w1[No] - self.var.wres1[No])
        availWater2 = np.maximum(0., self.var.w2[No] - self.var.wres2[No])
        availWater3 = np.maximum(0., self.var.w3[No] - self.var.wres3[No])

        # Available storage capacity in subsoil
        capLayer2 = self.var.ws2[No] - self.var.w2[No]
        capLayer3 = self.var.ws3[No] - self.var.w3[No]

        satTerm1 = availWater1 / self.var.wrange1[No]
        satTerm2 = availWater2 / self.var.wrange2[No]
        satTerm3 = availWater3 / self.var.wrange3[No]

        # Saturation term in Van Genuchten equation (between 0 and 1: availWater >= 0)
        satTerm1 = np.minimum(satTerm1, 1.0)
        satTerm2 = np.minimum(satTerm2, 1.0)
        satTerm3 = np.minimum(satTerm3, 1.0)

        # Unsaturated conductivity
        kUnSat1 = self.var.KSat1[NoSoil] * np.sqrt(satTerm1) * np.square(
            1 - (1 - satTerm1 ** self.var.genuInvM1[NoSoil]) ** self.var.genuM1[NoSoil])
        kUnSat2 = self.var.KSat2[NoSoil] * np.sqrt(satTerm2) * np.square(
            1 - (1 - satTerm2 ** self.var.genuInvM2[NoSoil]) ** self.var.genuM2[NoSoil])
        kUnSat3 = self.var.KSat3[NoSoil] * np.sqrt(satTerm3) * np.square(
            1 - (1 - satTerm3 ** self.var.genuInvM3[NoSoil]) ** self.var.genuM3[NoSoil])

        # fixed 3 sub-steps (the Courant criterion of LISFLOOD for a variable number of sub-steps is not used)
        NoSubSteps = 3
        DtSub = 1. / NoSubSteps


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

        for i in range(NoSubSteps):
            if i > 0:
                # Saturation term in Van Genuchten equation
                satTerm1 = np.maximum(0., wtemp1 - self.var.wres1[No]) / self.var.wrange1[No]
                satTerm2 = np.maximum(0., wtemp2 - self.var.wres2[No]) / self.var.wrange2[No]
                satTerm3 = np.maximum(0., wtemp3 - self.var.wres3[No]) / self.var.wrange3[No]
                # <= 1 (>= 0 already)
                satTerm1 = np.minimum(satTerm1, 1.0)
                satTerm2 = np.minimum(satTerm2, 1.0)
                satTerm3 = np.minimum(satTerm3, 1.0)

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
            if frost:
                subperc1to2 = np.where(self.var.FrostDay, 0, subperc1to2)
                subperc2to3 = np.where(self.var.FrostDay, 0, subperc2to3)

            if self.var.modflow:
                # multiplied by the fraction of ModFlow unsaturated cells (seepage scheme: sub-grid, see prefFlow)
                subperc3toGW = np.minimum(kUnSat3 * DtSub, availWater3) * (1 - saturated)
            else:
                subperc3toGW = np.minimum(kUnSat3 * DtSub, availWater3)

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

        # Update soil moisture (frozen soil: perc1to2 and perc2to3 are already 0 from the sub-steps)
        # testw: guard against negative storage (not seen in Morava/Bhima)
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

        # volumetric soil moisture of the layers (water storage / layer thickness)
        self.var.theta1[No] = self.var.w1[No] / self.var.rootDepth[0][No]
        self.var.theta2[No] = self.var.w2[No] / self.var.rootDepth[1][No]
        self.var.theta3[No] = self.var.w3[No] / self.var.rootDepth[2][No]

        # ---------------------------------------------------------------------------------------------
        # total actual transpiration
        self.var.actTransTotal[No] = ta1 + ta2 + ta3
        # transpiration of each soil layer (WaterBalance output)
        self.var.ta1[No] = ta1
        self.var.ta2[No] = ta2
        self.var.ta3[No] = ta3

        self.var.actualET[No] = (self.var.actualET[No] + self.var.actBareSoilEvap[No] + 
                                 self.var.openWaterEvap[No] + self.var.actTransTotal[No])
        # actual evapotranspiration can be bigger than pot, because snow evaporation alone is bigger than pot (snowEvapFactor > 1,
        # crop_correct_<landcover> < snowEvapFactor, pySnowClim sublimation), therefore self.var.totalPotET[No] is adjusted
        self.var.totalPotET[No] = np.maximum(self.var.totalPotET[No], self.var.actualET[No])

        # groundwater recharge
        toGWorInterflow = self.var.perc3toGW[No] + self.var.prefFlow[No]
        self.var.interflow[No] = self.var.percolationImp * toGWorInterflow

        if self.var.modflow:
            self.var.gwRecharge[No] = (1 - self.var.percolationImp) * toGWorInterflow
            if self.var.recharge_limit is not None:
                # recharge limited by the vertical permeability of the aquifer and a low permeability cover (MODFLOW
                # coupling, groundwater_modflow/transient.py, Dor's version); the rest goes to interflow
                limited = np.minimum(self.var.gwRecharge[No], self.var.recharge_limit)
                self.var.interflow[No] = self.var.interflow[No] + self.var.gwRecharge[No] - limited
                self.var.gwRecharge[No] = limited
        else:
            # net recharge: can be negative (capillar rise > percolation) -> taken from groundwater storage
            # (capRiseFromGW is already added to w3 and limited by the available groundwater storage)
            self.var.gwRecharge[No] = ((1 - self.var.percolationImp) * toGWorInterflow - self.var.capRiseFromGW[No])
            self.var.gwRecharge2[No] =  ((1 - self.var.percolationImp) *self.var.perc3toGW[No] - self.var.capRiseFromGW[No])

            testgw = np.minimum(self.var.gwRecharge2[No], 0)
            self.var.gwRecharge2[No] = self.var.gwRecharge2[No] - testgw

        if self.var.seepageOn:
            # seepage scheme: net recharge - the capillary rise from the aquifer is taken from MODFLOW as negative
            # recharge (groundwater_modflow/transient.py)
            self.var.gwRecharge[No] = self.var.gwRecharge[No] - self.var.capRiseFromAquifer[No]
            # seepage pond on the saturated part of the cell: share of saturated ModFlow cells or sub-grid saturated
            # share, the larger one (before 2026-10-13 only capriseindex: the drains below the aquifer top give
            # seepage where capriseindex = 0 - UNWMZ 9 of 10 mm/yr pond overflow, Q +3 %): shallow open water with
            # plants; on the pond area soil ET + pond evaporation together up to the larger of EWRef and the potential
            # ET of the land cover (2026-10-13 to 2026-11: pondArea x EWRef on top of the full soil ET, Bhima ET above
            # the potential ET +44 %; before 2026-10-13 EWRef minus the actual ET of today, not area weighted); the
            # pond above pondDepth (seepage_pond_depth, default 0.1 m, over the saturated part) overflows
            pondArea = np.maximum(self.var.capriseindex, self.var.saturatedFrac)
            self.var.pondarea = pondArea
            pond = self.var.seepagePond[No] + self.var.seepage[No]
            # totalPotET >= actualET here (raised above)
            self.var.seepageEvap[No] = np.minimum(pond, pondArea * np.maximum(
                np.maximum(self.var.EWRef, self.var.totalPotET[No]) - self.var.actualET[No], 0.))
            pond = pond - self.var.seepageEvap[No]
            overflow = np.maximum(pond - self.var.pondDepth * pondArea, 0.)
            self.var.seepagePond[No] = pond - overflow
            # overflow first into the soil as capillary rise: layer 3, then layer 2, each up to field capacity (below
            # field capacity hardly any percolation: no loop soil -> aquifer -> seepage), the rest to direct runoff.
            # Before 2026-10-13 all to direct runoff (UNWMZ, drains at the 10 % sub-grid elevation: 24 of 24 mm/yr to
            # the rivers, Q +10 %, ET -22 mm/yr; into the soil: 23 mm/yr, ET as with the drains at the aquifer top)
            toSoil3 = np.minimum(overflow, np.maximum(self.var.wfc3[No] - self.var.w3[No], 0.))
            self.var.w3[No] = self.var.w3[No] + toSoil3
            toSoil2 = np.minimum(overflow - toSoil3, np.maximum(self.var.wfc2[No] - self.var.w2[No], 0.))
            self.var.w2[No] = self.var.w2[No] + toSoil2
            self.var.pondToSoil[No] = toSoil3 + toSoil2
            self.var.pondToSoil3[No] = toSoil3
            overflow = overflow - self.var.pondToSoil[No]
            self.var.pondOverflow[No] = overflow
            self.var.directRunoff[No] = self.var.directRunoff[No] + overflow
            self.var.openWaterEvap[No] = self.var.openWaterEvap[No] + self.var.seepageEvap[No]
            self.var.actualET[No] = self.var.actualET[No] + self.var.seepageEvap[No]
            self.var.totalPotET[No] = np.maximum(self.var.totalPotET[No], self.var.actualET[No])


    def dynamic_crops(self):
        """
        Totals over land cover types and crop-specific evapotranspiration.

        Called once per time step from landcoverType.dynamic after the soil of all land cover
        types is calculated (before it was part of dynamic and calculated for each land cover type).
        """

        self.var.actTransTotal_forest = self.var.actTransTotal[0] * self.var.fracVegCover[0]
        self.var.actTransTotal_grasslands = self.var.actTransTotal[1] * self.var.fracVegCover[1]
        self.var.actTransTotal_paddy = self.var.actTransTotal[2] * self.var.fracVegCover[2]
        self.var.actTransTotal_nonpaddy = self.var.actTransTotal[3] * self.var.fracVegCover[3]

        self.var.ET_crop_Irr_paddy = (self.var.actTransTotal_paddy + 
                                      (self.var.actBareSoilEvap[2] + self.var.openWaterEvap[2]) *
                                      self.var.fracVegCover[2])
        self.var.ET_crop_Irr_paddy_fraccrop = np.where(self.var.fracVegCover[2] > 0, 
                                                       self.var.ET_crop_Irr_paddy / self.var.fracVegCover[2], 0)

        if self.var.includeCrops:
            # checkOption('includeCrops') and checkOption('includeCropSpecificWaterUse')
            # rainfed crops (grassland) also without irrigation, irrigated crops (non-paddy) only with irrigation
            # (without irrigation evaporation.dynamic is not called for 2 and 3: no weighted_KC_Irr)
            irrigation = checkOption('includeIrrigation')

            # Crop-specific transpiration (m) scales the land-class specific transpiration according to its
            # specific potential evapotranspiration and the land-class specific potential evapotranspiration

            # the same for all crops
            if irrigation:
                denIrr = self.var.fracVegCover[3] * (self.var.cropKC[3] - self.var.minCropKC)
                condIrr = denIrr > 0
                # condition on the divisor (before 2026-11: frac_totalIrr x weighted_KC_Irr_woFallow > 0)
                condIrrCrop = self.var.weighted_KC_Irr_woFallow_fullKc > 0
            denNonIrr = self.var.fracVegCover[1] * (self.var.cropKC[1] - self.var.minCropKC)
            condNonIrr = denNonIrr > 0
            # crops not activated and not planted anywhere give 0 everywhere -> skipped
            present = (np.any(self.var.activatedCrops > 0, axis=1) | np.any(self.var.fracCrops_Irr > 0, axis=1) |
                       np.any(self.var.fracCrops_nonIrr > 0, axis=1))
            # variables only for the output (named copies per crop, sums per admin segment): computed only if they
            # are in the output settings (as in evaporation.py)
            if not hasattr(self, 'outputNames'):
                from cwatm.management_modules.globals import outMap, outTss
                # entries are variable names, or after output.initial lists [file, variable name, ...]
                self.outputNames = {str(e[1] if isinstance(e, list) else e).split('[')[0].strip()
                                    for names in list(outMap.values()) + list(outTss.values()) for e in names}
            out = self.outputNames
            segments = 'adminSegments' in binding

            for c in range(len(self.var.Crops)):
                if not present[c]:
                    continue

                # Area and transpiration-Kc proportional
                if irrigation:
                    self.var.actTransTotal_crops_Irr[c] = np.where(
                        condIrr,
                        (self.var.fracCrops_Irr[c] * (self.var.currentKC[c] - self.var.minCropKC)) / denIrr,
                        0) * self.var.actTransTotal_nonpaddy

                self.var.actTransTotal_crops_nonIrr[c] = np.where(
                    condNonIrr,
                    (self.var.fracCrops_nonIrr[c] * (self.var.currentKC[c] - self.var.minCropKC)) / denNonIrr,
                    0) * self.var.actTransTotal_grasslands

                if irrigation:
                    self.var.ET_crop_Irr[c] = (self.var.actTransTotal_crops_Irr[c] +
                                               self.var.actBareSoilEvap[3] * self.var.fracCrops_Irr[c])
                    if 'ET_crop_Irr_' + str(c) in out:
                        vars(self.var)['ET_crop_Irr_' + str(c)] = self.var.ET_crop_Irr[c].copy()
                    if 'ET_crop_Irr_fraccrop_' + str(c) in out:
                        vars(self.var)['ET_crop_Irr_fraccrop_' + str(c)] = np.where(
                            self.var.fracCrops_Irr[c] > 0,
                            self.var.ET_crop_Irr[c] / self.var.fracCrops_Irr[c], 0)

                    self.var.actTransTotal_month_Irr[c] += self.var.ET_crop_Irr[c]

                self.var.ET_crop_nonIrr[c] = (self.var.actTransTotal_crops_nonIrr[c] +
                                              self.var.actBareSoilEvap[1] * self.var.fracCrops_nonIrr[c])
                if 'ET_crop_nonIrr_' + str(c) in out:
                    vars(self.var)['ET_crop_nonIrr_' + str(c)] = self.var.ET_crop_nonIrr[c].copy()
                if 'ET_crop_nonIrr_fraccrop_' + str(c) in out:
                    vars(self.var)['ET_crop_nonIrr_fraccrop_' + str(c)] = np.where(
                        self.var.fracCrops_nonIrr[c] > 0,
                        self.var.ET_crop_nonIrr[c] / self.var.fracCrops_nonIrr[c], 0)

                self.var.actTransTotal_month_nonIrr[c] += self.var.ET_crop_nonIrr[c]

                if irrigation:
                    self.var.irr_crop[c] = np.where(
                        condIrrCrop,
                        (self.var.fracCrops_Irr[c] * self.var.currentKC[c]) /
                        self.var.weighted_KC_Irr_woFallow_fullKc,
                        0) * self.var.act_irrNonpaddyWithdrawal
                    if 'irr_crop_' + str(c) in out:
                        vars(self.var)['irr_crop_' + str(c)] = self.var.irr_crop[c].copy()

                # daily ratio of actual transpiration to potential ET
                # rainfed: potential ET with the correction factor of grassland (PotET_crop_nonIrr)
                condPotNonIrr = self.var.PotET_crop_nonIrr[c] * self.var.activatedCrops[c] * self.var.fracCrops_nonIrr[c] > 0
                self.var.ratio_a_p_nonIrr_daily[c] = np.where(
                    condPotNonIrr,
                    self.var.ET_crop_nonIrr[c] / (self.var.PotET_crop_nonIrr[c] * self.var.fracCrops_nonIrr[c]),
                    0)  # This should always be <= 1.

                if irrigation:
                    condPot = self.var.PotET_crop[c] * self.var.activatedCrops[c] * self.var.fracCrops_Irr[c] > 0
                    self.var.ratio_a_p_Irr_daily[c] = np.where(
                        condPot,
                        self.var.ET_crop_Irr[c] / (self.var.PotET_crop[c] * self.var.fracCrops_Irr[c]),
                        0)  # This should always be <= 1.

                    self.var.irr_crop_month[c] += self.var.irr_crop[c]
                    if segments and 'irrM3_crop_month_segment' in out:
                        self.var.irrM3_crop_month_segment[c] = self.var.adminSegmentsIndex.total(
                            self.var.irr_crop_month[c] * self.var.cellArea)

            if irrigation:
                self.var.irr_Paddy_month += self.var.act_irrPaddyWithdrawal
                if segments and 'irrM3_Paddy_month_segment' in out:
                    self.var.irrM3_Paddy_month_segment = self.var.adminSegmentsIndex.total(
                        self.var.irr_Paddy_month * self.var.cellArea)
