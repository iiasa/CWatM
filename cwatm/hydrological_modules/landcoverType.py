# -------------------------------------------------------------------------
# Name:        Land Cover Type module
# Purpose: Land cover type management module for multi-class hydrological modeling.
# Handles spatial fractions and dynamics of different land use categories.
# Supports irrigation scheduling and land cover change over time.
#
# Author:      PB, MS, JdB, DF
# Created:     15/07/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


def decompress(map, nanvalue=None):
    """
    Decompress CWatM maps from 1D compressed to 2D spatial arrays.
    
    Converts compressed 1D arrays back to full 2D spatial maps using
    the model mask, handling missing values appropriately.
    
    Parameters
    ----------
    map : numpy.ndarray
        Compressed 1D array to be expanded to 2D
    nanvalue : float, optional
        Value to assign to NaN locations in the decompressed map
        
    Returns
    -------
    numpy.ndarray
        Decompressed 2D spatial array with mask-based reconstruction
    """

    dmap = maskinfo['maskall'].copy()
    dmap[~maskinfo['maskflat']] = map[:]
    if nanvalue is not None:
        dmap.data[np.isnan(dmap.data)] = nanvalue

    return dmap.data


class landcoverType(object):
    """
    Land cover type management module for multi-class hydrological modeling.
    
    Orchestrates hydrological processes across different land cover types by
    managing land cover fractions, calling appropriate soil routines for each
    type, and integrating results for comprehensive water balance calculations.

      
    Attributes
    ----------
    
    var : object
        Reference to model variables object containing state variables
    model : object
        Reference to the main CWatM model instance
        
    Notes
    -----
    
    Manages six primary land cover types:
    0. Forest
    1. Grassland
    2. Irrigated paddy
    3. Irrigated non-paddy
    4. Sealed surfaces
    5. Water bodies
    
    The module handles land cover fraction dynamics, calls soil processes
    for each type, and aggregates results weighted by land cover fractions
    for pixel-scale water balance calculations.









    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    modflow                              Flag          True if modflow_coupling = True in settings file                        bool 
    load_initial                         Flag          Settings initLoad holds initial conditions for variables                bool 
    compress_LR                          Array         boolean map as mask map for compressing lake/reservoir                  --   
    decompress_LR                        Array         boolean map as mask map for decompressing lake/reservoir                --   
    MtoM3C                               Array         conversion factor from m to m3 (compressed map)                         --   
    waterBodyTypTemp                     Array         waterbody temp e.g. lake, reservoir, wetlands                           --   
    maxGWCapRise                         Array         influence of capillary rise above groundwater level                     m    
    minCropKC                            Array         minimum crop factor (default 0.2)                                       --   
    minInterceptCap                      Array         Maximum interception read from file for forest and grassland land cove  m    
    irrigatedArea_original               Array                                                                                 --   
    fracAllCover                         Array                                                                                 --   
    frac_totalnonIrr                     Array         Fraction sown with specific non-irrigated crops                         %    
    frac_totalIrr_max                    Array         Fraction sown with specific irrigated crops, maximum throughout simula  %    
    frac_totalnonIrr_max                 Array         Fraction sown with specific non-irrigated crops, maximum throughout si  %    
    GeneralCrop_Irr                      Array         Fraction of irrigated land class sown with generally representative cr  %    
    fallowIrr                            Array         Fraction of fallowed irrigated land                                     %    
    fallowIrr_max                        Array         Fraction of fallowed irrigated land, maximum throughout simulation      %    
    GeneralCrop_nonIrr                   Array         Fraction of grasslands sown with generally representative crop          %    
    fallownonIrr                         Array         Fraction of fallowed non-irrigated land                                 %    
    fallownonIrr_max                     Array         Fraction of fallowed non-irrigated land, maximum throughout simulation  %    
    availableArableLand                  Array         Fraction of land not currently planted with specific crops              %    
    sum_gwRecharge                       Array         groundwater recharge                                                    m    
    interceptStor                        Array         simulated vegetation interception storage                               m    
    lakeStorage                          Array         Storage volume of lakes                                                 m3   
    resStorage                           Array         Storage volume of reservoirs                                            m3   
    riverbedExchangeM                    Array         Flow from channel into groundwater                                      m    
    leakageIntoGw                        Array         Canal leakage leading to groundwater recharge                           m    
    leakageIntoRunoff                    Array         Canal leakage leading to runoff                                         m    
    dynamicLandcover                     Flag          If landcover changes per year or is constant                            bool 
    staticLandCoverMaps                  Flag          1=staticLandCoverMaps in settings file is True, 0=otherwise             bool 
    landcoverSum                         Array         Sum of all landcover, should be 1.0                                     %    
    totalET                              Array         Total evapotranspiration for each cell including all landcover types    m    
    sum_interceptStor                    Array         Total of simulated vegetation interception storage including all landc  m    
    minTopWaterLayer                     Array         minimum water level above the top soil zone (for paddy rice)            m    
    maxRootDepth                         Array         maximum root depth                                                      m    
    rootDepth                            Array         rootdepth of different layers                                           m    
    KSat1                                Array         Saturated conductivity layer 1                                          cm da
    KSat2                                Array         Saturated conductivity layer 2                                          cm da
    KSat3                                Array         Saturated conductivity layer 3                                          cm da
    alpha1                               Array         Van Genuchten parameter alpha layer1                                    --   
    alpha2                               Array         Van Genuchten parameter alpha layer2                                    --   
    alpha3                               Array         Van Genuchten parameter alpha layer3                                    --   
    lambda1                              Array         Pore size index (lambda) layer 1                                        --   
    lambda2                              Array         Pore size index (lambda) layer 2                                        --   
    lambda3                              Array         Pore size index (lambda) layer 3                                        --   
    thetas1                              Array         Saturated volumetric soil moisture content layer 1                      --   
    thetas2                              Array         Saturated volumetric soil moisture content layer 2                      --   
    thetas3                              Array         Saturated volumetric soil moisture content layer 3                      --   
    thetar1                              Array         Residual volumetric soil moisture content layer 1                       --   
    thetar2                              Array         Residual volumetric soil moisture content layer 2                       --   
    thetar3                              Array         Residual volumetric soil moisture content layer 3                       --   
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
    kUnSat3FC                            Array         calculation from van Genuchten, Mualem equation                         m day
    kunSatFC12                           Array         calculation from van Genuchten, Mualem equation                         m day
    kunSatFC23                           Array         calculation from van Genuchten, Mualem equation                         m day
    rootFraction1                        Array                                                                                 --   
    cropCoefficientNC_filename           List                                                                                  --   
    interceptCapNC_filename              List                                                                                  --   
    coverFractionNC_filename             Array         landcover type + coverFractionNC                                        --   
    ElevationStD                         Array         Standard elevation from DEM                                             m    
    arnoBetaOro                          Array         chosen ModFlow model timestep (1day, 7days, 30days, etc.)               m    
    arnoBeta                             Array         arnoBeta defines the shape of soil water capacity distribution curve a  --   
    adjRoot                              Array                                                                                 --   
    sum_topwater                         Array         quantity of water on the soil (flooding) (weighted sum for all landcov  m    
    sum_soil                             Array         sum of all soilmpositure in all 3 layers + topwater                     m    
    sum_w1                               Array         sum of actual soil mositure, weighted by the fraction of landcover      m    
    sum_w2                               Array         sum of actual soil mositure, weighted by the fraction of landcover      m    
    sum_w3                               Array         sum of actual soil mositure, weighted by the fraction of landcover      m    
    totalSto                             Array         Total soil,snow and vegetation storage for each cell including all lan  m    
    maxtopwater                          Array         maximum heigth of topwater                                              m    
    totAvlWater                          Array         Field capacity minus wilting point in soil layers 1 and 2               m    
    Rain_times_fracPaddy                 Array                                                                                 --   
    Rain_times_fracNonPaddy              Array                                                                                 --   
    fracGlacierCover                     Array         Fraction of glacier cover in a grid cell                                %    
    areaGlacier                          Area          Area of glacier in a gridcell                                           --   
    pretotalSto                          Array         Previous totalSto                                                       m    
    prefFlow_GW                          Array         Preferential flow to groundwater. sum_prefFlow goes either to groundwa  m    
    sum_prefFlow                         Array         Preferential flow from soil to groundwater (summed up for all land cov  m    
    sum_perc3toGW                        Array         Percolation from 3rd soil layer to groundwater (summed up for all land  m    
    perc3toGW_GW                         Array         Percolation from 3rd soil layer to groundwater. sum_perc3toGW goes eit  m    
    riverbedExchangeM3                   Array         converting leakage in m3 (AI)                                           --   
    lakebedExchangeM                     Array         Flow of water from lakes and reservoirs into groundwater                m    
    sum_actTransTotal                    Array         actual total transpiration  (sum over all land cover types)             m    
    sum_actBareSoilEvap                  Array         actual bare soil evaporation (sum over all land cover types)            m    
    sum_interceptEvap                    Array                                                                                 --   
    sum_runoff                           Array         Runoff above the soil, more interflow, including all landcover types    m    
    GWVolumeVariation                    Number                                                                                --   
    MtoM3                                Array         Coefficient to change units                                             --   
    InvCellArea                          Array         Inverse of cell area of each simulated mesh                             1 m-2
    Precipitation                        Array         Precipitation (input for the model)                                     m    
    includeGlaciers                      Flag          Include glaciers                                                        bool 
    waterBodyID                          Array         lakes/reservoirs map with a single ID for each lake/reservoir           --   
    sum_openWaterEvap                    Array         sum of open water evaporation from all different land cover types       m    
    coverTypes                           Array         land cover types - forest - grassland - irrPaddy - irrNonPaddy - water  --   
    sum_directRunoff                     Array         direct runoff from surface  (sum over all land cover types)             m    
    sum_interflow                        Array         sum of iterflow from all land cover types                               m    
    availWaterInfiltration               Array         quantity of water reaching the soil after interception, more snowmelt   m    
    Rain                                 Array         Precipitation less snow                                                 m    
    snowEvap                             Array         total evaporation from snow for a snow layers                           m    
    SnowCover                            Array         snow cover (sum over all layers)                                        m    
    frac_totalIrr                        Array         Fraction sown with specific irrigated crops                             %    
    soilLayers                           List          Number of soil layers                                                   --   
    soildepth                            Array         Thickness of the first soil layer                                       m    
    wfc1                                 Array         Soil moisture at field capacity in layer 1                              m    
    wfc2                                 Array         Soil moisture at field capacity in layer 2                              m    
    wfc3                                 Array         Soil moisture at field capacity in layer 3                              m    
    w1                                   Array         Simulated water storage in the layer 1                                  m    
    w2                                   Array         Simulated water storage in the layer 2                                  m    
    w3                                   Array         Simulated water storage in the layer 3                                  m    
    topwater                             Array         quantity of water above the soil (flooding)                             m    
    baseflow                             Array         simulated baseflow (= groundwater discharge to river)                   m    
    capriseindex                         Array         computing saturated fraction of each CWatM cells (where water table >=  --   
    soildepth12                          Array         Total thickness of layer 2 and 3                                        m    
    leakageriver_factor                  Array                                                                                 --   
    leakagelake_factor                   Array                                                                                 --   
    modflow_timestep                     Array         Chosen ModFlow model timestep (1day, 7days, 30days, etc.)               day  
    wwtUrbanLeakage                      Array                                                                                 --   
    wwtColArea                           Array         Setup wastewater treatment facilities load collection area (AI)         --   
    urbanleak                            Array         share to collect urban leakage (AI)                                     --   
    fracVegCover                         Array         Fraction of specific land covers (0=forest, 1=grasslands, etc.)         %    
    cellArea                             Array         Area of cell                                                            m2   
    includeWastewater                    Flag                                                                                  --   
    lakeVolumeM3C                        Array         compressed map of lake volume                                           m3   
    lakeStorageC                         Array                                                                                 --   
    reservoirStorageM3C                  Array         Initial reservoir fill (fraction of total storage, [-]) (AI)            --   
    lakeResStorageC                      Array         and from the combined onenpfor waterbalance issues (AI)                 --   
    lakeResStorage                       Array                                                                                 --   
    act_SurfaceWaterAbstract             Array         Surface water abstractions                                              m    
    readAvlChannelStorageM               Array         coversersion m3 -> m # minus environmental flow (AI)                    --   
    leakageCanals_M                      Array         Without this, npareamaximum uses the historical maximum (AI)            --   
    includeWastewaterPits                Flag                                                                                  --   
    pitLatrinToGW                        Array                                                                                 --   
    addtoevapotrans                      Array         Irrigation application loss to evaporation                              m    
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize land cover type module.
        
        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.var = model.var
        self.model = model

    # noinspection PyTypeChecker
    def initial(self):
        """
        Initialize land cover type fractions and parameters.
        
        Sets up spatial distributions of land cover types, irrigation fractions,
        crop parameters, and other land cover-specific characteristics required
        for hydrological process differentiation.
        
        Notes
        -----
        Initialization includes:
        - Land cover fraction maps for all types
        - Irrigation area fractions and dynamics
        - Crop coefficient parameters
        - Land cover-specific hydrological parameters
        - Temporal dynamics of land cover changes
        
        Land cover types:
        0 Forest - Natural forest areas
        1 Grasland/non irrigated land No.1
        2 Paddy irrigation No.2
        3 non-Paddy irrigation No.3
        4 Sealed area No.4
        5 Water covered area No.5

        And initialize the soil variables
        """
        self.var.riverbedExchangeM = globals.inZero.copy()
        self.var.GeneralCrop_nonIrr = globals.inZero.copy()
        self.var.GeneralCrop_Irr = globals.inZero.copy()

        self.var.frac_totalIrr = globals.inZero.copy()
        self.var.frac_totalnonIrr = globals.inZero.copy()
        self.var.frac_totalIrr_max = globals.inZero.copy()
        self.var.frac_totalnonIrr_max = globals.inZero.copy()
        self.var.fallowIrr = globals.inZero.copy()
        self.var.fallownonIrr = globals.inZero.copy()
        self.var.fallowIrr_max = globals.inZero.copy()
        self.var.fallownonIrr_max = globals.inZero.copy()

        # Fraction of cells where capillary rise occurs (used when ModFlow coupling)
        self.var.capriseindex = globals.inZero.copy()
        self.var.leakageIntoGw = globals.inZero.copy()
        self.var.leakageIntoRunoff = globals.inZero.copy()
        self.var.availableArableLand = globals.inZero.copy()

        # make land cover change from year to year or fix it to 1 year
        if returnBool('dynamicLandcover'):
            self.var.dynamicLandcover = True
        else:
            self.var.dynamicLandcover = False

        self.var.staticLandCoverMaps = False
        if "staticLandCoverMaps" in option:
            self.var.staticLandCoverMaps = checkOption('staticLandCoverMaps')


        self.var.coverTypes = list(map(str.strip, cbinding("coverTypes").split(",")))
        landcoverAll = ['fracVegCover', 'interceptStor', 'availWaterInfiltration', 'interceptEvap',
                        'directRunoff', 'openWaterEvap']
        for variable in landcoverAll:
            vars(self.var)[variable] = np.tile(globals.inZero, (6, 1))

        landcoverPara = ['minInterceptCap', 'cropDeplFactor', 'rootFraction1',
                         'maxRootDepth', 'topWaterLayer', 'interflow',
                         'cropCoefficientNC_filename', 'interceptCapNC_filename', 'coverFractionNC_filename']
        # arrays stored as list not as numpy, because it can contain strings, single parameters or arrays
        # list is filled with append afterwards
        for variable in landcoverPara:
            vars(self.var)[variable] = []

        # fraction (m2) of a certain irrigation type over (only) total irrigation area ; will be assigned by 
        # the landSurface module output variable per land cover class
        landcoverVars = ['irrTypeFracOverIrr', 'fractionArea', 'totAvlWater', 'cropKC', 'cropKC_landCover',
                         'effSatAt50', 'effPoreSizeBetaAt50', 'rootZoneWaterStorageMin', 'rootZoneWaterStorageRange',
                         'totalPotET', 'potTranspiration', 'soilWaterStorage',
                         'infiltration', 'actBareSoilEvap', 'landSurfaceRunoff', 'actTransTotal',
                         'gwRecharge','gwRecharge2', 'interflow','actualET', 'pot_irrConsumption', 'act_irrConsumption', 'irrDemand',
                         'topWaterLayer',
                         'perc3toGW', 'capRiseFromGW', 'netPercUpper', 'netPerc', 'prefFlow']
     
        # for 6 landcover types
        for variable in landcoverVars:
            vars(self.var)[variable] = np.tile(globals.inZero, (6, 1))


        # for 4 landcover types with soil underneath
        landcoverVarsSoil = ['arnoBeta', 'rootZoneWaterStorageCap', 'rootZoneWaterStorageCap12', 'perc1to2', 
                             'perc2to3', 'theta1', 'theta2', 'theta3']
        for variable in landcoverVarsSoil:
            vars(self.var)[variable] = np.tile(globals.inZero, (4, 1))

        soilVars = ['adjRoot', 'perc', 'capRise', 'rootDepth', 'storCap']
        # For 3 soil layers and 4 landcover types
        for variable in soilVars:
            vars(self.var)[variable] = np.tile(globals.inZero, (self.var.soilLayers, 4, 1))

        # set aggregated storages to zero
        self.var.landcoverSum = ['interceptStor', 'interflow',
                                 'directRunoff', 'totalPotET', 'potTranspiration', 'availWaterInfiltration',
                                 'interceptEvap', 'infiltration', 'actBareSoilEvap', 'landSurfaceRunoff', 'actTransTotal', 
                                 'gwRecharge','gwRecharge2', 'openWaterEvap', 'capRiseFromGW', 'perc3toGW', 'prefFlow','act_irrConsumption']
        for variable in self.var.landcoverSum:
            vars(self.var)["sum_" + variable] = globals.inZero.copy()

        # for three soil layers
        soilVars = ['w1', 'w2', 'w3']
        for variable in soilVars:
            vars(self.var)[variable] = np.tile(globals.inZero, (4, 1))
        for variable in soilVars:
            vars(self.var)["sum_" + variable] = globals.inZero.copy()


        self.var.totalET = globals.inZero.copy()
        self.var.act_SurfaceWaterAbstract = globals.inZero.copy()
        self.var.irrigatedArea_original = globals.inZero.copy()

        # ----------------------------------------------------------
        # Load initial values and calculate basic soil parameters which are not changed in time

        self.dynamic_fracIrrigation(init=True, dynamic=True)
        i = 0
        for coverType in self.var.coverTypes:
            self.var.minInterceptCap.append(loadmap(coverType + "_minInterceptCap"))
            # init values
            if coverType in ['forest', 'grassland', 'irrPaddy', 'irrNonPaddy', 'sealed']:
                self.var.interceptStor[i] = self.var.load_initial(coverType + "_interceptStor")

            # summarize the following initial storages:
            self.var.sum_interceptStor += self.var.fracVegCover[i] * self.var.interceptStor[i]
            i += 1

        self.var.minCropKC = loadmap('minCropKC')
        self.var.minTopWaterLayer = loadmap("minTopWaterLayer")
        self.var.maxGWCapRise = loadmap("maxGWCapRise")

        i = 0
        for coverType in self.var.coverTypes[:4]:
            # calculate rootdepth for each soillayer and each land cover class

            soildepth_factor = loadmap('soildepth_factor')
            self.var.maxRootDepth.append(loadmap(coverType + "_maxRootDepth") * soildepth_factor)

            self.var.rootDepth[0][i] = self.var.soildepth[0].copy()  # 0.05 m
            # if land cover = forest
            if coverType != 'grassland':
                # soil layer 1 = root max of land cover  - first soil layer
                h1 = np.maximum(self.var.soildepth[1], self.var.maxRootDepth[i] - self.var.soildepth[0])
                #
                self.var.rootDepth[1][i] = np.minimum(self.var.soildepth12 - 0.05, h1)
                # soil layer is minimim 0.05 m
                self.var.rootDepth[2][i] = np.maximum(0.05, self.var.soildepth12 - self.var.rootDepth[1][i])
            else:
                self.var.rootDepth[1][i] = self.var.soildepth[1].copy()
                self.var.rootDepth[2][i] = self.var.soildepth[2].copy()
            i += 1



        soilVars1 = ['KSat1', 'KSat2', 'KSat3', 'alpha1', 'alpha2', 'alpha3', 'lambda1', 'lambda2', 'lambda3',
                      'thetas1', 'thetas2', 'thetas3', 'thetar1', 'thetar2', 'thetar3']
        for variable in soilVars1:
            vars(self.var)[variable] = []

        # ksat multiplier
        if 'ksat_fact' in binding:
            ksat_fact = loadmap('ksat_fact')  # define limit
        else:
            ksat_fact = 1.

        # thetas multiplier
        if 'thetas_fact' in binding:
            thetas_fact = loadmap('thetas_fact')  # define limit
        else:
            thetas_fact = 1.

        # thetar multiplier - limits 0.1 - 2.0
        if 'thetar_fact' in binding:
            thetar_fact = loadmap('thetar_fact')  # define limit
            thetar_fact = np.maximum(0.1, np.minimum(thetar_fact, 2.0))
        else:
            thetar_fact = 1.

        i = 0
        for coverType in self.var.coverTypes[:2]:
            if i == 0:
                pre = coverType + "_"
            else:
                pre = ""
            # ksat in cm/d-1 -> m/dm
            self.var.KSat1.append(ksat_fact * (loadmap(pre + "KSat1")) / 100)
            self.var.KSat2.append(ksat_fact * (loadmap(pre + "KSat2")) / 100)
            self.var.KSat3.append(ksat_fact * (loadmap(pre + "KSat3")) / 100)
            self.var.alpha1.append((loadmap(pre + "alpha1")))
            self.var.alpha2.append((loadmap(pre + "alpha2")))
            self.var.alpha3.append((loadmap(pre + "alpha3")))
            self.var.lambda1.append((loadmap(pre + "lambda1")))
            self.var.lambda2.append((loadmap(pre + "lambda2")))
            self.var.lambda3.append((loadmap(pre + "lambda3")))
            self.var.thetas1.append(thetas_fact * (loadmap(pre + "thetas1")))
            self.var.thetas2.append(thetas_fact * (loadmap(pre + "thetas2")))
            self.var.thetas3.append(thetas_fact * (loadmap(pre + "thetas3")))
            self.var.thetar1.append(thetar_fact * (loadmap(pre + "thetar1")))
            self.var.thetar2.append(thetar_fact * (loadmap(pre + "thetar2")))
            self.var.thetar3.append(thetar_fact * (loadmap(pre + "thetar3")))
            i += 1



        # Van Genuchten n and m coefficients
        # GenuN1=Lambda+1
        with np.errstate(invalid='ignore', divide='ignore'):
            genuN1 = [x + 1 for x in self.var.lambda1]   # unit [-]
            genuN2 = [x + 1 for x in self.var.lambda2]
            genuN3 = [x + 1 for x in self.var.lambda3]
            # self.var.GenuM1=Lambda1/GenuN1
            self.var.genuM1 = [x / y for x, y in zip(self.var.lambda1, genuN1)]
            self.var.genuM2 = [x / y for x, y in zip(self.var.lambda2, genuN2)]
            self.var.genuM3 = [x / y for x, y in zip(self.var.lambda3, genuN3)]
            # self.var.GenuInvM1=1/self.var.GenuM1
            self.var.genuInvM1 = [1 / x for x in self.var.genuM1]
            self.var.genuInvM2 = [1 / x for x in self.var.genuM2]
            self.var.genuInvM3 = [1 / x for x in self.var.genuM3]

        soilVars2 = ['ws1', 'ws2', 'ws3', 'wres1', 'wres2', 'wres3', 'wrange1', 'wrange2', 'wrange3',
                      'wfc1', 'wfc2', 'wfc3', 'wwp1', 'wwp2', 'wwp3', 'kunSatFC12', 'kunSatFC23']
        for variable in soilVars2:
            vars(self.var)[variable] = []

        i = 0
        for coverType in self.var.coverTypes[:4]:
            j = 0
            if coverType != "forest":
                j = 1
            self.var.ws1.append(self.var.thetas1[j] * self.var.rootDepth[0][i])   # unit [m]
            self.var.ws2.append(self.var.thetas2[j] * self.var.rootDepth[1][i])
            self.var.ws3.append(self.var.thetas3[j] * self.var.rootDepth[2][i])

            # unit [m] because of rootDepth [m]
            self.var.wres1.append(self.var.thetar1[j] * self.var.rootDepth[0][i])
            self.var.wres2.append(self.var.thetar2[j] * self.var.rootDepth[1][i])
            self.var.wres3.append(self.var.thetar3[j] * self.var.rootDepth[2][i])

            self.var.wrange1.append(self.var.ws1[i] - self.var.wres1[i])   # unit [m]
            self.var.wrange2.append(self.var.ws2[i] - self.var.wres2[i])
            self.var.wrange3.append(self.var.ws3[i] - self.var.wres3[i])

            # Soil moisture at field capacity (pF2, 100 cm) [cm water slice]    # Mualem equation (van Genuchten, 1980)
            # see https://en.wikipedia.org/wiki/Water_retention_curve
            # alpha in 1/cm * cm water slice e.g. 10**4.2  around 15000 cm water slice for wilting point
            self.var.wfc1.append(self.var.wres1[i] + self.var.wrange1[i] / 
                                 ((1 + (self.var.alpha1[j] * 100) ** genuN1[j]) ** self.var.genuM1[j]))
            self.var.wfc2.append(self.var.wres2[i] + self.var.wrange2[i] / 
                                 ((1 + (self.var.alpha2[j] * 100) ** genuN2[j]) ** self.var.genuM2[j]))
            self.var.wfc3.append(self.var.wres3[i] + self.var.wrange3[i] / 
                                 ((1 + (self.var.alpha3[j] * 100) ** genuN3[j]) ** self.var.genuM3[j]))

            # Soil moisture at wilting point (pF4.2, 10**4.2 cm) [cm water slice]    
            # Mualem equation (van Genuchten, 1980)
            self.var.wwp1.append(self.var.wres1[i] + self.var.wrange1[i] / 
                                 ((1 + (self.var.alpha1[j] * (10**4.2)) ** genuN1[j]) ** self.var.genuM1[j]))   # unit [m]
            self.var.wwp2.append(self.var.wres2[i] + self.var.wrange2[i] / 
                                 ((1 + (self.var.alpha2[j] * (10**4.2)) ** genuN2[j]) ** self.var.genuM2[j]))
            self.var.wwp3.append(self.var.wres3[i] + self.var.wrange3[i] / 
                                 ((1 + (self.var.alpha3[j] * (10**4.2)) ** genuN3[j]) ** self.var.genuM3[j]))



            satTerm1FC = np.maximum(0., self.var.wfc1[i] - self.var.wres1[i]) / self.var.wrange1[i]  # unit [-]
            satTerm2FC = np.maximum(0., self.var.wfc2[i] - self.var.wres2[i]) / self.var.wrange2[i]
            satTerm3FC = np.maximum(0., self.var.wfc3[i] - self.var.wres3[i]) / self.var.wrange3[i]

            # van Genuchten, Mualem equation see 
            # https://acsess.onlinelibrary.wiley.com/doi/epdf/10.2136/sssaj2000.643843x
            # with Mualem (1976)  L = 0.5 -> np.sqrt(satTerm2FC)

            kUnSat1FC = self.var.KSat1[j] * np.sqrt(satTerm1FC) * np.square(
                1 - (1 - satTerm1FC ** self.var.genuInvM1[j]) ** self.var.genuM1[j])
            kUnSat2FC = self.var.KSat2[j] * np.sqrt(satTerm2FC) * np.square(
                1 - (1 - satTerm2FC ** self.var.genuInvM2[j]) ** self.var.genuM2[j])
            self.var.kUnSat3FC = self.var.KSat3[j] * np.sqrt(satTerm3FC) * np.square(
                1 - (1 - satTerm3FC ** self.var.genuInvM3[j]) ** self.var.genuM3[j])
            self.var.kunSatFC12.append(np.sqrt(kUnSat1FC * kUnSat2FC))
            self.var.kunSatFC23.append(np.sqrt(kUnSat2FC * self.var.kUnSat3FC))

            i += 1


        i = 0
        for coverType in self.var.coverTypes[:4]:
            # other paramater values
            # b coefficient of soil water storage capacity distribution
            # self.var.minTopWaterLayer.append(loadmap(coverType + "_minTopWaterLayer"))
            # self.var.minCropKC.append(loadmap(coverType + "_minCropKC"))

            # self.var.minInterceptCap.append(loadmap(coverType + "_minInterceptCap"))
            # self.var.cropDeplFactor.append(loadmap(coverType + "_cropDeplFactor"))
            # parameter values

            self.var.rootFraction1.append(loadmap(coverType + "_rootFraction1"))
            # self.var.rootFraction2 = self.var.rootFraction1
            self.var.maxRootDepth.append(loadmap(coverType + "_maxRootDepth"))

            # store filenames
            self.var.cropCoefficientNC_filename.append(coverType + "_cropCoefficientNC")
            self.var.interceptCapNC_filename.append(coverType + "_interceptCapNC")
            self.var.coverFractionNC_filename.append(coverType + "_coverFractionNC")

            # init values
            # self.var.interflow[i] = self.var.load_initial(coverType + "_interflow")
            self.var.w1[i] = self.var.load_initial(coverType + "_w1", default=self.var.wwp1[i])
            self.var.w2[i] = self.var.load_initial(coverType + "_w2", default=self.var.wwp2[i])
            self.var.w3[i] = self.var.load_initial(coverType + "_w3", default=self.var.wwp3[i])

            # it is better to start with a humid soil to avoid too much pumping at the begining because of 
            # the irrigation demand
            if self.var.modflow:
                start_soil_humid = 0.75
                if 'start_soil_humid' in binding:
                    start_soil_humid = loadmap('start_soil_humid')
                if i == 0:
                    print('=> Soil moisture is filled at ', 100 * start_soil_humid, ' % at the begining')
                self.var.w1[i] = self.var.load_initial(coverType + "_w1", 
                                                       default=self.var.wwp1[i] + start_soil_humid * 
                                                       (self.var.wfc1[i] - self.var.wwp1[i]))
                self.var.w2[i] = self.var.load_initial(coverType + "_w2", 
                                                       default=self.var.wwp2[i] + start_soil_humid * 
                                                       (self.var.wfc2[i] - self.var.wwp2[i]))
                self.var.w3[i] = self.var.load_initial(coverType + "_w3", 
                                                       default=self.var.wwp3[i] + start_soil_humid * 
                                                       (self.var.wfc3[i] - self.var.wwp3[i]))
            
            # Improved Arno's scheme parameters: Hageman and Gates 2003
            # arnoBeta defines the shape of soil water capacity distribution curve as a function of 
            # topographic variability. b = max( (oh - o0)/(oh + omax), 0.01)
            # oh: the standard deviation of orography, o0: minimum std dev, omax: max std dev

            self.var.ElevationStD = loadmap('ElevationStD')
            self.var.arnoBetaOro = (self.var.ElevationStD - 10.0) / (self.var.ElevationStD + 1500.0)

            # for CALIBRATION
            self.var.arnoBetaOro = self.var.arnoBetaOro + loadmap('arnoBeta_add')
            self.var.arnoBetaOro = np.minimum(1.2, np.maximum(0.01, self.var.arnoBetaOro))

            self.var.arnoBeta[i] = self.var.arnoBetaOro + loadmap(coverType + "_arnoBeta")
            self.var.arnoBeta[i] = np.minimum(1.2, np.maximum(0.01, self.var.arnoBeta[i]))

            # Due to large rooting depths, the third (final) soil layer may be pushed to its minimum of 0.05 m.
            # In such a case, it may be better to turn off the root fractioning feature, as there is limited depth
            # in the third soil layer to hold water, while having a significant fraction of the rootss.
            # TODO: Extend soil depths to match maximum root depths
            
            rootFrac = np.tile(globals.inZero, (self.var.soilLayers, 1))
            fractionroot12 = self.var.rootDepth[0][i] / (self.var.rootDepth[0][i] + self.var.rootDepth[1][i])
            rootFrac[0] = fractionroot12 * self.var.rootFraction1[i]
            rootFrac[1] = (1 - fractionroot12) * self.var.rootFraction1[i]
            rootFrac[2] = 1.0 - self.var.rootFraction1[i]

            if 'rootFrac' in binding:
                if not checkOption('rootFrac'):
                    root_depth_sum = self.var.rootDepth[0][i] + self.var.rootDepth[1][i] + self.var.rootDepth[2][i]
                    for layer in range(3):
                        rootFrac[layer] = self.var.rootDepth[layer][i] / root_depth_sum

            rootFracSum = np.sum(rootFrac, axis=0)

            for soilLayer in range(self.var.soilLayers):
                self.var.adjRoot[soilLayer][i] = rootFrac[soilLayer] / rootFracSum
            i += 1

        soilVars = ['w1', 'w2', 'w3']
        for variable in soilVars:
            vars(self.var)["sum_" + variable] = globals.inZero.copy()
            for No in range(4):
                vars(self.var)["sum_" + variable] += self.var.fracVegCover[No] * vars(self.var)[variable][No]

        # for paddy irrigation flooded paddy fields
        self.var.topwater = self.var.load_initial("topwater", default=0.) * globals.inZero.copy()
        self.var.sum_topwater = self.var.fracVegCover[2] * self.var.topwater
        self.var.sum_soil = self.var.sum_w1 + self.var.sum_w2 + self.var.sum_w3 + self.var.sum_topwater
        self.var.totalSto = self.var.SnowCover + self.var.sum_interceptStor + self.var.sum_soil

        # for maximum of topwater flooding (default = 0.05m)
        self.var.maxtopwater = 0.05
        if "irrPaddy_maxtopwater" in binding:
            self.var.maxtopwater = loadmap('irrPaddy_maxtopwater')

        # for irrigation of non paddy -> No =3
        totalWaterPlant1 = np.maximum(0., self.var.wfc1[3] - self.var.wwp1[3])  # * self.var.rootDepth[0][3]
        totalWaterPlant2 = np.maximum(0., self.var.wfc2[3] - self.var.wwp2[3])  # * self.var.rootDepth[1][3]
        # totalWaterPlant3 = np.maximum(0., self.var.wfc3[3] - self.var.wwp3[3]) * self.var.rootDepth[2][3]
        self.var.totAvlWater = totalWaterPlant1 + totalWaterPlant2  # + totalWaterPlant3

        self.var.Rain_times_fracPaddy = globals.inZero.copy()
        self.var.Rain_times_fracNonPaddy = globals.inZero.copy()
    # --------------------------------------------------------------------------

    def dynamic_fracIrrigation(self, init=False, dynamic=True):
        """
        Update irrigation fractions dynamically or during initialization.
        
        Manages temporal changes in irrigation area fractions for paddy
        and non-paddy irrigation, handling both initialization and dynamic
        updates throughout model execution.
        
        Parameters
        ----------
        init : bool, optional
            Flag for initialization mode (default: False)
        dynamic : bool, optional
            Flag for dynamic update mode (default: True)
            
        Notes
        -----
        Updates irrigation fractions based on:
        - Temporal irrigation datasets
        - Seasonal irrigation patterns
        - Long-term irrigation changes
        - Crop calendar considerations
        """
        """
        Dynamic part of the land cover type module

        Calculating fraction of land cover

        * loads the fraction of landcover for each year from netcdf maps
        * calculate the fraction of 6 land cover types based on the maps
        * if used add glacier maps

        :param init: (optional) True: set for the first time of a run
        :param dynamic: used in the dynmic run not in the initial phase
        :return: -

        """

        #if checkOption('includeIrrigation') and checkOption('dynamicIrrigationArea'):

        # updating fracVegCover of landCover (for historical irrigation areas, done at yearly basis)
        # if first day of the year or first day of run

        if init and dynamic:

            if self.var.staticLandCoverMaps:

                self.var.fracVegCover[0] = loadmap('forest_fracVegCover')
                self.var.fracVegCover[2] = loadmap('irrPaddy_fracVegCover')
                self.var.fracVegCover[3] = loadmap('irrNonPaddy_fracVegCover')
                self.var.fracVegCover[4] = loadmap('sealed_fracVegCover')
                self.var.fracVegCover[5] = loadmap('water_fracVegCover')

            else:
                if self.var.dynamicLandcover:
                    landcoverYear = dateVar['currDate']
                else:
                    landcoverYear = datetime.datetime(int(binding['fixLandcoverYear']), 1, 1)

                i = 0
                for coverType in self.var.coverTypes:
                    self.var.fracVegCover[i] = readnetcdf2('fractionLandcover', landcoverYear, useDaily="yearly",
                                                           value='frac' + coverType)
                    i += 1

                if 'static_irrigation_map' in option:
                    if checkOption('static_irrigation_map'):
                        self.var.fracVegCover[3] = loadmap('irrNonPaddy_fracVegCover')

            # for Xiaogang's agent model
            if "paddyfraction" in binding:
                self.var.fracVegCover[2] = loadmap('paddyfraction')
                self.var.fracVegCover[3] = loadmap('nonpaddyfraction')

            # correction of grassland if sum is not 1.0
            sum = np.sum(self.var.fracVegCover, axis=0)
            self.var.fracVegCover[1] = np.maximum(0., self.var.fracVegCover[1] + 1.0 - sum)
            sum = np.sum(self.var.fracVegCover, axis=0)
            self.var.fracVegCover[0] = np.maximum(0., self.var.fracVegCover[0] + 1.0 - sum)
            sum = np.sum(self.var.fracVegCover, axis=0)


            # Adjust because of Glaciers. If glaicers than glacier area should be taken from grassland
            # if there is not enough grassland than glacier are is taken from
            self.var.fracGlacierCover = 0
            if self.var.includeGlaciers:
                self.var.fracGlacierCover = globals.inZero.copy()
                if returnBool('excludeGlacierArea'):
                
                    # reading land cover year in case static land is used for other land classes
                    if self.var.dynamicLandcover:
                        landcoverYear = dateVar['currDate']
                    else:
                        landcoverYear = datetime.datetime(int(binding['fixLandcoverYear']), 1, 1) 
                        
                    # substract glacier area from sealed area first
                    # substract glacier area from grassland fraction later on
                    self.var.fracGlacierCover = readnetcdf2('fractionGlaciercover', landcoverYear, 
                                                            useDaily="yearly", value='on_area', cut=False)
                    invfracGlacierCover  = 1 - self.var.fracGlacierCover

                    self.var.fracGlacierCover = np.minimum(np.maximum(self.var.fracGlacierCover, 0.0), 1.0)
                    self.var.areaGlacier = self.var.cellArea * self.var.fracGlacierCover

                    self.var.fracVegCover[4] = self.var.fracVegCover[4] - self.var.fracGlacierCover
                    # if there are some pixels where sealed area is not large enough to substract glacier area, 
                    # the other lancovertypes have to be used
                    # sealed, grassland, forest, water, irrNonPaddy,
                    # ind_landcovertype_glaciers = [1,0,3,2,4,5]
                    ind_landcovertype_glaciers = [1, 4, 0, 5, 2, 3]
                    for i, ind in enumerate(ind_landcovertype_glaciers[:-1]):
                        if any(self.var.fracVegCover[ind] < 0):
                            # substract glacier area from landcovertype
                            self.var.fracVegCover[ind_landcovertype_glaciers[i + 1]][
                                np.where(self.var.fracVegCover[ind] < 0)] -= np.abs(
                                self.var.fracVegCover[ind][np.where(self.var.fracVegCover[ind] < 0)])
                            self.var.fracVegCover[ind][np.where(self.var.fracVegCover[ind] < 0)] = 0

                    # Fraction landcover sum has to be back to 100%
                    i = 0
                    for coverType in self.var.coverTypes:
                        value= 0
                        if i ==  1: # grassland
                            value = 1
                        self.var.fracVegCover[i] = np.where(invfracGlacierCover<0.0001, value,
                            self.var.fracVegCover[i] / invfracGlacierCover)
                        i += 1

                """
            temp = loadmap('reservoir_command_areas').astype(np.int)
            self.var.fracVegCover[3] += np.where(temp > 0, self.var.fracVegCover[1] * 0.25, 0)
            self.var.fracVegCover[1] -= np.where(temp > 0, self.var.fracVegCover[1] * 0.25, 0)
            self.var.fracVegCover[3] += np.where(temp == 46, self.var.fracVegCover[1] * 0.25, 0)
            self.var.fracVegCover[1] -= np.where(temp == 46, self.var.fracVegCover[1] * 0.25, 0)
            """


            self.var.irrigatedArea_original = self.var.fracVegCover[3].copy()

            # sum of landcover without water and sealed
            # self.var.sum_fracVegCover = np.sum(self.var.fracVegCover[0:4], axis=0)

            # if irrigation is off every fraction of paddy and non paddy irrigation is put to land dcover 'grassland'
            if not (checkOption('includeIrrigation')):
                self.var.fracVegCover[1] = (self.var.fracVegCover[1] + self.var.fracVegCover[2] + 
                                            self.var.fracVegCover[3])
                self.var.fracVegCover[2] = 0.0
                self.var.fracVegCover[3] = 0.0



            #self.var.fracVegCover[0] = self.var.fracVegCover[0] + self.var.fracVegCover[4]
            #self.var.fracVegCover[1] = self.var.fracVegCover[1] + self.var.fracVegCover[5]
            """
            self.var.fracVegCover[0] = 0.2   # forest
            self.var.fracVegCover[1] = 0.2  # others (grassland)
            self.var.fracVegCover[2] = 0.2  # paddy irrigation
            self.var.fracVegCover[3] = 0.2  # non paddy irrigation
            self.var.fracVegCover[4] = 0.1
            self.var.fracVegCover[5] = 0.1
            """
            self.var.fracAllCover = np.sum(self.var.fracVegCover, axis=0)


# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Execute land cover type processes for current time step.
        
        Orchestrates hydrological calculations across all land cover types,
        calling appropriate modules for each type and integrating results
        weighted by land cover fractions.
        
        Notes
        -----
        Processing sequence:
        1. Update dynamic land cover fractions if applicable
        2. Call interception module for relevant land cover types
        3. Execute snow/frost processes for each type
        4. Run soil water dynamics for each land cover type
        5. Process sealed water and open water dynamics
        6. Aggregate results weighted by land cover fractions
        7. Calculate total pixel-scale water balance components
        
        Each land cover type maintains separate state variables that
        are integrated based on their spatial fractions within each pixel.
        """
        """
        Dynamic part of the land cover type module

        Calculating soil for each of the 6  land cover class

        * calls evaporation_module.dynamic
        * calls interception_module.dynamic
        * calls soil_module.dynamic
        * calls sealed_water_module.dynamic

        And sums every thing up depending on the land cover type fraction
        """

        ### To compute water balance for modflow
        # Currently, only daily time scale is implemented for this version')
        #if self.var.modflow:
            #if (dateVar['curr'] - int(dateVar['curr'] / self.var.modflow_timestep) * self.var.modflow_timestep) == 1 and \
            #        dateVar['curr'] > self.var.modflow_timestep:  # if it is the first step of the week
            #    self.var.presumed_sum_gwRecharge = self.var.sumed_sum_gwRecharge.copy()
                # stormodf = np.nansum((self.var.presumed_sum_gwRecharge/self.var.modflow_timestep-self.var.capillar-self.var.baseflow) * self.var.cellArea) # From ModFlow during the previous step
                # stormodf = self.var.GWVolumeVariation / self.var.modflow_timestep # GW volume change from the previous ModFlow run (difference betwwen water levels times porosity)
        self.var.pretotalSto = self.var.totalSto.copy()

        coverNo = 0
        # update soil (loop per each land cover type):
        for coverType in self.var.coverTypes:
            if checkOption('includeIrrigation'):
                usecovertype = 4  # include paddy and non paddy irrigation
            else:
                usecovertype = 2   # exclude irrigation
            # calculate evaporation and transpiration for soil land cover types (not for sealed and water covered areas)
            if coverNo < usecovertype:
                self.model.evaporation_module.dynamic(coverType, coverNo)
            self.model.interception_module.dynamic(coverType, coverNo)
            coverNo += 1

        # -----------------------------------------------------------
        # Calculate  water available for infiltration
        # *********  WATER Demand   *************************
        # Allow Urban runoff to be collected by wastewater collection systems from sealed areas

        if self.var.includeWastewater:
            self.var.wwtUrbanLeakage = np.where(self.var.wwtColArea > 0, self.var.availWaterInfiltration[4] * self.var.urbanleak, 0.)
            self.var.availWaterInfiltration[4] -= self.var.wwtUrbanLeakage
            self.var.wwtUrbanLeakage = self.var.fracVegCover[4] * self.var.wwtUrbanLeakage
            
        self.model.waterdemand_module.dynamic()

        # Calculate soil
        coverNo = 0
        for coverType in self.var.coverTypes:
            if checkOption('includeIrrigation'):
                usecovertype = 4  # include paddy and non paddy irrigation
            else:
                usecovertype = 2   # exclude irrgation

            if coverNo < usecovertype:
                self.model.soil_module.dynamic(coverType, coverNo)
            if coverNo > 3:
                # calculate for openwater and sealed area
                self.model.sealed_water_module.dynamic(coverType, coverNo)
            coverNo += 1


        # aggregated variables by fraction of land cover
        for variable in self.var.landcoverSum:
            vars(self.var)["sum_" + variable] = globals.inZero.copy()
            for No in range(6):
                vars(self.var)["sum_" + variable] += self.var.fracVegCover[No] * vars(self.var)[variable][No]

        # for watercycle output of preflow and perc3toGW
        self.var.prefFlow_GW = divideValues(self.var.sum_prefFlow, self.var.sum_prefFlow + self.var.sum_perc3toGW) * self.var.sum_gwRecharge
        self.var.perc3toGW_GW = divideValues(self.var.sum_perc3toGW, self.var.sum_prefFlow + self.var.sum_perc3toGW) * self.var.sum_gwRecharge

        if self.var.modflow:
            # computing leakage from rivers (if modflow coupling is used)

            # leakage depends on water bodies storage, water bodies fraction and modflow saturated area
            self.var.riverbedExchangeM = np.minimum(self.var.leakageriver_factor * np.maximum(self.var.fracVegCover[5], 0) *
                                                    ((1 - self.var.capriseindex + 0.25) // 1),
                                                    0.80 * self.var.readAvlChannelStorageM)  # leakage in m/d
            self.var.riverbedExchangeM = np.where(self.var.riverbedExchangeM > self.var.InvCellArea,
                                                       self.var.riverbedExchangeM, 0)  # to avoid too small values

            # if there is a lake in this cell, there is no leakage
            if checkOption('includeWaterBodies'):
                self.var.riverbedExchangeM = np.where(self.var.waterBodyID > 0, 0., self.var.riverbedExchangeM)
            self.var.riverbedExchangeM3 = self.var.riverbedExchangeM * self.var.cellArea  # converting leakage in m3
            # self.var.riverbedExchangeM3 is then removed from river storage in routing_kinematic module

            # adding leakage from river to the groundwater recharge
            self.var.sum_gwRecharge += self.var.riverbedExchangeM

            self.var.leakageIntoGw = self.var.leakageCanals_M * (1 - self.var.capriseindex)
            self.var.leakageIntoRunoff = self.var.leakageCanals_M * self.var.capriseindex
            self.var.sum_gwRecharge += self.var.leakageIntoGw




            if checkOption('includeWaterBodies'):

                # first, lakes variable need to be extended to their area and not only to the discharge point
                lakeIDbyID = np.unique(self.var.waterBodyID)
                if len(lakeIDbyID) > 1:

                    lakestor_id = np.copy(self.var.lakeStorage)
                    resstor_id = np.copy(self.var.resStorage)
                    for id in range(len(lakeIDbyID)):  # for each lake or reservoir
                        if lakeIDbyID[id] != 0:
                            temp_map = np.where(self.var.waterBodyID == lakeIDbyID[id], np.where(self.var.lakeStorage > 0, 1, 0), 0)  # Looking for the discharge point of the lake
                            if np.sum(temp_map) == 0:  # try reservoir
                                temp_map = np.where(self.var.waterBodyID == lakeIDbyID[id], np.where(self.var.resStorage > 0, 1, 0), 0)  # Looking for the discharge point of the reservoir
                            discharge_point = np.nanargmax(temp_map)  # Index of the cell where the lake outlet is stored
                            if self.var.waterBodyTypTemp[discharge_point] != 0:

                                if self.var.waterBodyTypTemp[discharge_point] == 1:  # this is a lake
                                    # computing the lake area
                                    area_stor = np.sum(np.where(self.var.waterBodyID == lakeIDbyID[id], self.var.cellArea, 0))  # required to keep mass balance rigth
                                    # computing the lake storage in meter and put this value in each cell including the lake
                                    lakestor_id = np.where(self.var.waterBodyID == lakeIDbyID[id],
                                                           self.var.lakeStorage[discharge_point] / area_stor, lakestor_id)  # in meter

                                else:  # this is a reservoir
                                    # computing the reservoir area
                                    area_stor = np.sum(np.where(self.var.waterBodyID == lakeIDbyID[id], self.var.cellArea, 0))  # required to keep mass balance rigth
                                    # computing the reservoir storage in meter and put this value in each cell including the reservoir
                                    resstor_id = np.where(self.var.waterBodyID == lakeIDbyID[id],
                                                           self.var.resStorage[discharge_point] / area_stor, resstor_id)  # in meter

                    # Gathering lakes and reservoirs in the same array
                    lakeResStorage = np.where(self.var.waterBodyTypTemp == 0, 0., np.where(self.var.waterBodyTypTemp == 1, lakestor_id, resstor_id))  # in meter

                    minlake = np.maximum(0., 0.98 * lakeResStorage)  # reasonable but arbitrary limit

                    # leakage depends on water bodies storage, water bodies fraction and modflow saturated area
                    lakebedExchangeM_temp = np.minimum(self.var.leakagelake_factor * np.maximum(self.var.fracVegCover[5], 0) *
                                                       ((1 - self.var.capriseindex + 0.25) // 1), minlake)  # leakage in m/d

                    # Now, leakage is converted again from the lake/reservoir area to discharge point to be removed from the lake/reservoir store
                    self.var.lakebedExchangeM = np.zeros(np.shape(self.var.cellArea))
                    for id in range(len(lakeIDbyID)):  # for each lake or reservoir
                        if lakeIDbyID[id] != 0:
                            temp_map = np.where(self.var.waterBodyID == lakeIDbyID[id], np.where(self.var.lakeStorage > 0, 1, 0), 0)  # Looking for the discharge point of the lake
                            if np.sum(temp_map) == 0:  # try reservoir
                                temp_map = np.where(self.var.waterBodyID == lakeIDbyID[id], np.where(self.var.resStorage > 0, 1, 0), 0)  # Looking for the discharge point of the reservoir
                            discharge_point = np.nanargmax(temp_map)  # Index of the cell where the lake outlet is stored
                        # Converting the lake/reservoir leakage from meter to cubic meter and put this value in the cell corresponding to the outlet
                        self.var.lakebedExchangeM[discharge_point] = np.sum(np.where(self.var.waterBodyID == lakeIDbyID[id],
                                                                                                            lakebedExchangeM_temp * self.var.cellArea, 0))  # in m3
                    self.var.lakebedExchangeM = self.var.lakebedExchangeM / self.var.MtoM3  # in meter

                    # compressed version for lakes and reservoirs
                    lakeExchangeM = np.compress(self.var.compress_LR, self.var.lakebedExchangeM)

                    # substract from both, because it is sorted by self.var.waterBodyTypCTemp
                    self.var.lakeStorageC = self.var.lakeStorageC - lakeExchangeM * self.var.MtoM3C
                    self.var.lakeVolumeM3C = self.var.lakeVolumeM3C - lakeExchangeM * self.var.MtoM3C
                    self.var.reservoirStorageM3C = self.var.reservoirStorageM3C - lakeExchangeM * self.var.MtoM3C

                    # and from the combined one for waterbalance issues
                    self.var.lakeResStorageC = self.var.lakeResStorageC - lakeExchangeM * self.var.MtoM3C
                    self.var.lakeResStorage = globals.inZero.copy()
                    np.put(self.var.lakeResStorage, self.var.decompress_LR, self.var.lakeResStorageC)

                    # adding leakage from lakes and reservoirs to the groundwater recharge
                    self.var.sum_gwRecharge += lakebedExchangeM_temp
        
        if self.var.includeWastewaterPits:
            self.var.sum_gwRecharge += self.var.pitLatrinToGW
            
        soilVars = ['w1','w2','w3','theta1','theta2','theta3']
        for variable in soilVars:
                vars(self.var)["sum_" + variable] = globals.inZero.copy()
                for No in range(4):
                    vars(self.var)["sum_" + variable] += self.var.fracVegCover[No] * vars(self.var)[variable][No]

        self.var.sum_topwater = self.var.fracVegCover[2] * self.var.topwater
        self.var.totalET = self.var.sum_actTransTotal + self.var.sum_actBareSoilEvap + self.var.sum_openWaterEvap + self.var.sum_interceptEvap + self.var.snowEvap + self.var.addtoevapotrans
        # addtoevapotrans: part of water demand which is lost due to evaporation
        self.var.sum_soil = self.var.sum_w1 + self.var.sum_w2 + self.var.sum_w3 + self.var.sum_topwater
        self.var.totalSto = self.var.SnowCover + self.var.sum_interceptStor + self.var.sum_soil

        # leakageIntoRunoff is also added in runoff_concentration
        self.var.sum_runoff = self.var.sum_directRunoff + self.var.sum_interflow + self.var.leakageIntoRunoff
        self.var.Rain_times_fracPaddy = self.var.fracVegCover[2] * self.var.Rain
        self.var.Rain_times_fracNonPaddy = self.var.fracVegCover[3] * self.var.Rain

        ### Printing the soil+GW water balance (considering no pumping), without the surface part
        #print('Date : ', dateVar['currDatestr'])
        if checkOption('calcWaterBalance'):
            if self.var.modflow:
                if dateVar['curr'] > self.var.modflow_timestep:  # from the second step

                    storcwat = np.sum((self.var.totalSto - self.var.pretotalSto) * self.var.cellArea)  # Daily CWAT storage variations
                    #cwatbudg = np.sum((self.var.Precipitation - self.var.sum_runoff - self.var.totalET + self.var.presumed_sum_gwRecharge / self.var.modflow_timestep - self.var.sum_gwRecharge - self.var.baseflow) * self.var.cellArea)  # Inputs-Outputs (baseflow comes from the previous ModFlow model)
                    cwatbudg = np.sum((self.var.Precipitation - self.var.sum_runoff - self.var.totalET + self.var.sum_gwRecharge - self.var.sum_gwRecharge - self.var.baseflow) * self.var.cellArea)  # Inputs-Outputs (baseflow comes from the previous ModFlow model)

                    print('CWatM-ModFlow water balance error [%]: ',
                          round(100 * (cwatbudg - storcwat - self.var.GWVolumeVariation / self.var.modflow_timestep) /
                                (0.5 * cwatbudg + 0.5 * storcwat + 0.5 * self.var.GWVolumeVariation / self.var.modflow_timestep) * 100) / 100)

        # --------------------------------------------------------------------

