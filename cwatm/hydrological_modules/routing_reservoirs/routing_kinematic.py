# -------------------------------------------------------------------------
# Name:        Routing module - Kinematic wave
# Purpose: Kinematic wave routing module for river flow simulation and channel routing.
# Implements numerical solution of kinematic wave equations for streamflow propagation.
# Uses compiled C libraries for efficient computation of river network flow dynamics.
#
# Author:      PB
# Created:     17/01/2017
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
from cwatm.hydrological_modules.routing_reservoirs.routing_sub import *
from cwatm.hydrological_modules.lakes_reservoirs import *


class routing_kinematic(object):
    """
    Kinematic wave routing module for river flow simulation.

    This class implements kinematic wave routing to simulate river flow using
    the kinematic wave approximation of the Saint-Venant equations. It handles
    channel flow routing, evaporation from channels, and water body interactions.

    Attributes
    ----------
    var : object
        Model variables container
    model : object
        CWatM model instance
    lakes_reservoirs_module : object
        Lakes and reservoirs module instance

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    channelStorage                       Array         Channel water storage                                                   m3   
    modflow                              Flag          True if modflow_coupling = True in settings file                        bool 
    load_initial                         Flag          Settings initLoad holds initial conditions for variables                bool 
    inflowM3                             Array         inflow to basin                                                         m3   
    Crops                                Array         Internal: List of specific crops and Kc/Ky parameters                   --   
    compress_LR                          Array         boolean map as mask map for compressing lake/reservoir                  --   
    dirUp                                Array         river network in upstream direction                                     --   
    lddCompress                          Array         compressed river network (without missing values)                       --   
    dirupLen_LR                          Array         number of bifurcation upstream lake/reservoir                           --   
    dirDown_LR                           Array         river network direktion downstream lake/reservoir                       --   
    lendirDown_LR                        Array         number of river network connections lake/reservoir                      --   
    lakeArea                             Array         area of each lake/reservoir                                             m2   
    lakeEvaFactorC                       Array         compressed map of a factor which increases evaporation from lake becau  --   
    riverbedExchangeM3                   Array                                                                                 --   
    DtSec                                Array         number of seconds per timestep (default = 86400)                        s    
    ETRef                                Array         potential evapotranspiration rate from reference crop                   m    
    EWRef                                Array         potential evaporation rate from water surface                           m    
    QInM3Old                             Array         Inflow from previous day                                                m3   
    waterBodyID                          Array         lakes/reservoirs map with a single ID for each lake/reservoir           --   
    UpArea1                              Array         upstream area of a grid cell                                            m2   
    dirupID_LR                           Array         index river upstream lake/reservoir                                     --   
    lakeEvaFactor                        Array         a factor which increases evaporation from lake because of wind          --   
    dtRouting                            Array         number of seconds per routing timestep                                  s    
    evapWaterBodyC                       Array         Compressed version of EvapWaterBodyM                                    m    
    sumLakeEvapWaterBodyC                Array                                                                                 --   
    noRoutingSteps                       Number        Number of routing step - how often the subroutine is run during a day   --   
    sumResEvapWaterBodyC                 Array                                                                                 --   
    discharge                            Array         Channel discharge                                                       m3/s 
    inflowDt                             Number                                                                                --   
    downstruct                           Array         structure of the river network in downstream direction                  --   
    sum_openWaterEvap                    Array         sum of open water evaporation from all different land cover types       m    
    chanLength                           Array         Input, Channel length                                                   m    
    totalCrossSectionArea                Array                                                                                 --   
    dirupLen                             Array                                                                                 --   
    dirupID                              Array                                                                                 --   
    catchment                            Array                                                                                 --   
    dirDown                              Array                                                                                 --   
    lendirDown                           Number                                                                                --   
    UpArea                               Array         upstream area of a grid cell                                            m2   
    beta                                 Array                                                                                 --   
    chanMan                              Array         Input, Channel Manning's roughness coefficient                          s/m^(
    chanGrad                             Array                                                                                 --   
    chanWidth                            Array         Input, Channel width                                                    m    
    chanDepth                            Array         Input, Channel depth                                                    m    
    invbeta                              Array                                                                                 --   
    invchanLength                        Array                                                                                 --   
    invdtRouting                         Array                                                                                 --   
    totalCrossSectionAreaBankFull        Array                                                                                 --   
    chanWettedPerimeterAlpha             Array                                                                                 --   
    alpPower                             Array                                                                                 --   
    channelAlpha                         Array                                                                                 --   
    invchannelAlpha                      Array                                                                                 --   
    riverbedExchange                     Array                                                                                 --   
    Xcel                                 List                                                                                  --   
    EvapoChannel                         Array         Channel evaporation                                                     m3   
    QDelta                               Array                                                                                 --   
    sumsideflow                          Number                                                                                --   
    prechannelStorage                    Array                                                                                 --   
    dis_outlet                           Array                                                                                 --   
    humanConsumption                     Array                                                                                 --   
    humanUse                             Array                                                                                 --   
    natureUse                            Array                                                                                 --   
    ETRefAverage_segments                Array                                                                                 --   
    precipEffectiveAverage_segments      Array                                                                                 --   
    head_segments                        Array         Simulated water level, averaged over adminSegments [masl]               m    
    gwdepth_adjusted_segments            Array         Adjusted depth to groundwater table, averaged over adminSegments        m    
    gwdepth_segments                     Array         Groundwater depth, averaged over adminSegments                          m    
    adminSegments_area                   Array         Spatial area of domestic agents                                         m2   
    runoff                               Array         Total runoff from surface, interflow and groundwater                    m    
    openWaterEvap                        Array         Simulated evaporation from open areas                                   m    
    infiltration                         Array         Water actually infiltrating the soil                                    m    
    actTransTotal_paddy                  Array         Transpiration from paddy land cover                                     m    
    actTransTotal_nonpaddy               Array         Transpiration from non-paddy land cover                                 m    
    actTransTotal_crops_nonIrr           Array         Transpiration associated with specific non-irr crops                    m    
    head                                 Array         Simulated ModFlow water level [masl]                                    m    
    gwdepth_adjusted                     Array         Adjusted depth to groundwater table                                     m    
    gwdepth                              Array         Depth to groundwater table                                              m    
    fracVegCover                         Array         Fraction of specific land covers (0=forest, 1=grasslands, etc.)         %    
    adminSegments                        Array         Domestic agents                                                         Int  
    cellArea                             Array         Area of cell                                                            m2   
    act_SurfaceWaterAbstract             Array         Surface water abstractions                                              m    
    addtoevapotrans                      Array         Irrigation application loss to evaporation                              m    
    act_bigLakeResAbst                   Array         Abstractions to satisfy demands from lakes and reservoirs               m    
    act_smallLakeResAbst                 Array         Abstractions from small lakes at demand location                        m    
    returnFlow                           Array                                                                                 --   
    act_nonIrrConsumption                Array         Non-irrigation consumption                                              m    
    act_nonIrrWithdrawal                 Array         Non-irrigation withdrawals                                              m    
    act_irrWithdrawal                    Array         Irrigation withdrawals                                                  m    
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize the kinematic wave routing module.

        Parameters
        ----------
        model : object
            CWatM model instance containing variables and configuration
        """
        self.var = model.var
        self.model = model
        self.lakes_reservoirs_module = lakes_reservoirs(model)

    def catchment(self, point, ldd):
        """
        Extract catchment boundaries upstream of a specified point.

        Creates a river network from the local drainage direction (LDD) map
        and calculates the catchment area upstream of a given point.

        Parameters
        ----------
        point : array_like
            Point location for catchment delineation
        ldd : array_like
            Local drainage direction map

        Returns
        -------
        tuple
            Catchment map, x-coordinate offset, y-coordinate offset
        """

        dmap = maskinfo['maskall'].copy()
        dmap[~maskinfo['maskflat']] = ldd[:]
        ldd2D = dmap.reshape(maskinfo['shape']).astype(np.int64)
        ldd2D[ldd2D.mask] = 0

        # every cell gets an order starting from 0 ...
        lddshortOrder = np.arange(maskinfo['mapC'][0])
        # decompress this map to 2D
        lddOrder = decompress(lddshortOrder)
        lddOrder[maskinfo['mask']] = -1
        lddOrder = np.array(lddOrder.data, dtype=np.int64)

        lddCompress, dirshort = lddrepair(ldd2D, lddOrder)
        dirUp, dirupLen, dirupID = dirUpstream(dirshort)

        c1 = catchment1(dirUp, point)

        # decompressing catchment from 1D -> 2D
        dmap = maskinfo['maskall'].copy()
        dmap[~maskinfo['maskflat']] = c1[:]
        c2 = dmap.reshape(maskinfo['shape']).astype(np.int64)

        if np.max(c2) == 0:
            return -1, -1, -1

        c3 = np.where(c2 == 1)

        d1, d2 = min(c3[0]), max(c3[0] + 1)
        d3, d4 = min(c3[1]), max(c3[1] + 1)

        c4 = c2[d1: d2, d3: d4]

        return c4, d3, d1


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """
        Initialize routing parameters and river network properties.

        Sets up the river network by loading and processing drainage direction data,
        calculates river network parameters including channel geometry (length, width,
        depth, gradient), initializes channel storage and discharge, and configures
        Manning's roughness coefficients for kinematic wave calculations.
        """

        ldd = loadmap('Ldd')
        # l1 = decompress(ldd)

        (self.var.lddCompress, dirshort, self.var.dirUp, self.var.dirupLen, self.var.dirupID,
         self.var.downstruct, self.var.catchment, self.var.dirDown, self.var.lendirDown) = defLdd2(ldd)

        # self.var.ups = upstreamArea(dirDown, dirshort, self.var.cellArea)
        self.var.UpArea1 = upstreamArea(self.var.dirDown, dirshort, globals.inZero + 1.0)
        self.var.UpArea = upstreamArea(self.var.dirDown, dirshort, self.var.cellArea)


        basin = False
        if 'savebasinmap' in option:
            basin = checkOption('savebasinmap')
        if basin:
            file = os.path.join(outDir[list(outDir)[-1]], "basin.tif")
            report(self.var.catchment, file)
            print("\nBasin area map in: ", file)
            file = os.path.join(outDir[list(outDir)[-1]], "ups.tif")
            report(self.var.UpArea, file)
            print("Upstream area map in: ", file)

        # ---------------------------------------------------------------
        # Calibration
        # mannings roughness factor 0.1 - 10.0
        manningsFactor = loadmap('manningsN')


        # number of substep per day
        self.var.noRoutingSteps = int(loadmap('NoRoutingSteps'))
        # kinematic wave parameter: 0.6 is for broad sheet flow
        self.var.beta = loadmap('chanBeta')
        # Channel Manning's n
        self.var.chanMan = loadmap('chanMan') * manningsFactor
        # Channel gradient (fraction, dy/dx)
        self.var.chanGrad = np.maximum(loadmap('chanGrad'), loadmap('chanGradMin'))
        # Channel length [meters]
        self.var.chanLength = loadmap('chanLength')
        # Channel bottom width [meters]
        self.var.chanWidth = loadmap('chanWidth')

        # Bankfull channel depth [meters]
        self.var.chanDepth = loadmap('chanDepth')



        # -----------------------------------------------
        # Inverse of beta for kinematic wave
        self.var.invbeta = 1 / self.var.beta
        # Inverse of channel length [1/m]
        self.var.invchanLength = 1 / self.var.chanLength

        # Corresponding sub-timestep (seconds)
        self.var.dtRouting = self.var.DtSec / self.var.noRoutingSteps
        self.var.invdtRouting = 1 / self.var.dtRouting

        # -----------------------------------------------
        # ***** CHANNEL GEOMETRY  ************************************

        # Area (sq m) of bank full discharge cross section [m2]
        self.var.totalCrossSectionAreaBankFull = self.var.chanDepth * self.var.chanWidth
        # Cross-sectional area at half bankfull [m2]
        # This can be used to initialise channel flow (see below)
        #TotalCrossSectionAreaHalfBankFull = 0.5 * self.var.TotalCrossSectionAreaBankFull
        # TotalCrossSectionAreaInitValue = loadmap('TotalCrossSectionAreaInitValue')
        self.var.totalCrossSectionArea = 0.5 * self.var.totalCrossSectionAreaBankFull
        # Total cross-sectional area [m2]: if initial value in binding equals -9999 the value at half bankfull is used,

        # -----------------------------------------------
        # ***** CHANNEL ALPHA (KIN. WAVE)*****************************
        # ************************************************************
        # Following calculations are needed to calculate Alpha parameter in kinematic
        # wave. Alpha currently fixed at half of bankful depth

        # Reference water depth for calculation of Alpha: half of bankfull
        #chanDepthAlpha = 0.5 * self.var.chanDepth
        # Channel wetted perimeter [m]
        self.var.chanWettedPerimeterAlpha = self.var.chanWidth + 2 * 0.5 * self.var.chanDepth

        # ChannelAlpha for kinematic wave
        alpTermChan = (self.var.chanMan / (np.sqrt(self.var.chanGrad))) ** self.var.beta
        self.var.alpPower = self.var.beta / 1.5

        """
        The 2.5 factor seems to be a bug (some leftover from a test).
        It will remain because all calibration are done with this factor.
        The factor chanman is also 4.6050393 (chanman = 1 is in real: 4.605)
        """
        self.var.channelAlpha = alpTermChan * (self.var.chanWettedPerimeterAlpha ** self.var.alpPower) * 2.5
        ca = 2.5 * self.var.chanMan * ((1 / np.sqrt(self.var.chanGrad)) ** self.var.beta) * \
             (self.var.chanWettedPerimeterAlpha ** self.var.alpPower)


        self.var.invchannelAlpha = 1. / self.var.channelAlpha

        # -----------------------------------------------
        # ***** CHANNEL INITIAL DISCHARGE ****************************

        # channel water volume [m3]
        # Initialise water volume in kinematic wave channels [m3]
        channelStorageIni = self.var.totalCrossSectionArea * self.var.chanLength * 0.1
        self.var.channelStorage = self.var.load_initial("channelStorage", default=channelStorageIni)

        # Initialise discharge at kinematic wave pixels (note that InvBeta is
        # simply 1/beta, computational efficiency!)
        # self.var.chanQKin = np.where(self.var.channelAlpha > 0, (self.var.totalCrossSectionArea / 
        #                             self.var.channelAlpha) ** self.var.invbeta, 0.)
        dischargeIni = (self.var.channelStorage * self.var.invchanLength * self.var.invchannelAlpha) ** \
                       self.var.invbeta
        self.var.discharge = self.var.load_initial("discharge", default=dischargeIni)
        #self.var.chanQKin = chanQKinIni

        # self.var.riverbedExchange = globals.inZero.copy()
        self.var.riverbedExchange = self.var.load_initial("riverbedExchange", default=globals.inZero.copy())
        # self.var.discharge = self.var.chanQKin.copy()


        # if checkOption('includeWaterDemand'):
        #     self.var.readAvlChannelStorage = 0.95 * self.var.channelStorage
        #    # to avoid small values and to avoid surface water abstractions from dry channels (>= 0.5mm)
        #    self.var.readAvlChannelStorage = np.where(self.var.readAvlChannelStorage < (0.0005 * self.var.cellArea),0.,self.var.readAvlChannelStorage)

        # factor for evaporation from lakes, reservoirs and open channels
        self.var.lakeEvaFactor = globals.inZero + loadmap('lakeEvaFactor')


        #self.var.channelAlphaPcr = decompress(self.var.channelAlpha)
        #self.var.chanLengthPcr = decompress(self.var.chanLength)


        self.var.Xcel = []


    # --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Execute dynamic routing calculations for the current time step.

        Performs the main routing calculations including channel evaporation,
        riverbed-groundwater exchange, water body retention (if enabled),
        lateral inflow calculations, and kinematic wave routing using optimized
        C++ libraries for computational efficiency.
        """

# ---------------------------------------------------------------------------------

        # if routing is not needed return
        if not checkOption('includeRouting'):
            return


        Qnew = globals.inZero.copy()

        # Evaporation from open channel
        # from big lakes/res and small lakes/res is calculated separately
        channelFraction = np.minimum(1.0, self.var.chanWidth * self.var.chanLength / self.var.cellArea)
        # put all the water area in which is not reflected in the lakes ,res
        # channelFraction = np.maximum(self.var.fracVegCover[5], channelFraction)

        EWRefact = np.maximum(0.0, self.var.lakeEvaFactor * self.var.EWRef - self.var.openWaterEvap[5])
        # evaporation from channel minus the calculated evaporation from rainfall
        self.var.EvapoChannel = EWRefact * channelFraction * self.var.cellArea
        #self.var.EvapoChannel = self.var.EWRef * channelFraction * self.var.cellArea

        # restrict to 95% of channel storage -> something should stay in the river
        self.var.EvapoChannel = np.where(
            (0.95 * self.var.channelStorage - self.var.EvapoChannel) > 0.0,
            self.var.EvapoChannel,
            0.95 * self.var.channelStorage)



        # riverbed infiltration (m3):
        # - current implementation based on Inge's principle (later, will be based on groundater head (MODFLOW) and can be negative)
        # - happening only if 0.0 < baseflow < nonFossilGroundwaterAbs
        # - infiltration rate will be based on aquifer saturated conductivity
        # - limited to fracWat
        # - limited to available channelStorage
        # - this infiltration will be handed to groundwater in the next time step

        # used self.var.fracVegCover[5] instead of self.var.dynamicFracWat
        """
        self.var.riverbedExchange = np.maximum(0.0,  np.minimum(self.var.channelStorage, np.where(self.var.baseflow > 0.0, \
                                np.where(self.var.nonFossilGroundwaterAbs > self.var.baseflow, \
                                self.var.kSatAquifer * self.var.fracVegCover[5] * self.var.cellArea, \
                                0.0), 0.0)))
        # to avoid flip flop
        self.var.riverbedExchange = np.minimum(self.var.riverbedExchange, 0.95 * self.var.channelStorage)
        """

        if checkOption('includeWaterBodies'):
            # add reservoirs depending on year

            # ------------------------------------------------------------
            # evaporation from water bodies (m3), will be limited by available water in lakes and reservoirs
            # calculate outflow from lakes and reservoirs

            # average evaporation overeach lake
            EWRefavg = npareaaverage(EWRefact, self.var.waterBodyID)
            # evaporation for the whole lake for each routing step
            eWaterBody = np.maximum(0.0, EWRefavg * self.var.lakeArea) / self.var.noRoutingSteps
            # compressed to the number lakes
            self.var.evapWaterBodyC = self.var.lakeEvaFactorC * np.compress(self.var.compress_LR, eWaterBody)
            # exclude evaporation where lakes are, because they are filled in again with evapWaterBodyC
            self.var.EvapoChannel = np.where(
                self.var.waterBodyID > 0,
                (1 - self.var.fracVegCover[5]) * self.var.EvapoChannel,
                self.var.EvapoChannel)
            #self.var.riverbedExchange = np.where(self.var.waterBodyID > 0, 0., self.var.riverbedExchange)

            # sum of all routingsteps of evaporation from lakes and reservoirs   - set to 0 each time step
            self.var.sumResEvapWaterBodyC = self.var.evapWaterBodyC * 0.
            self.var.sumLakeEvapWaterBodyC = self.var.evapWaterBodyC * 0.

        EvapoChannelM3Dt = self.var.EvapoChannel / self.var.noRoutingSteps
        if self.var.modflow:
            # removing water infiltrating from river to groundwater
            riverbedExchangeDt = self.var.riverbedExchangeM3 / self.var.noRoutingSteps
        # riverbedExchangeDt = self.var.riverbedExchange / self.var.noRoutingSteps

        if checkOption('inflow'):
            self.var.QDelta = (self.var.inflowM3 - self.var.QInM3Old) / self.var.noRoutingSteps
            # difference between old and new inlet flow  per sub step
            # in order to calculate the amount of inlet flow in the routing loop

        WDAddM3Dt = 0
        if checkOption('includeWaterDemand'):
            # self.var.act_SurfaceWaterAbstract includes channel abstractions as well as abstractions from lakes and reservoirs
            # In waterdemand.py: self.var.act_SurfaceWaterAbstract = self.var.act_SurfaceWaterAbstract + self.var.act_bigLakeResAbst + self.var.act_smallLakeResAbst
            # The abstractions from lakes and reservoirs have already been dealt with by removing these amounts from their storages in the same module
            # The water abstractions from the channel are thus the surface water abstractions subtract the lake and reservoir abstractions

            if checkOption('includeWaterBodies'):
                WDAddM3Dt = self.var.act_SurfaceWaterAbstract - \
                            (self.var.act_bigLakeResAbst + self.var.act_smallLakeResAbst)
            else:
                WDAddM3Dt = self.var.act_SurfaceWaterAbstract

            # return flow from (m) non irrigation water demand
            # WDAddM3Dt = WDAddM3Dt - self.var.nonIrrReturnFlowFraction * self.var.act_nonIrrDemand
            WDAddM3Dt = WDAddM3Dt - self.var.returnFlow
            WDAddM3Dt = WDAddM3Dt * self.var.cellArea / self.var.noRoutingSteps

            # sideflowChanM3 -= self.var.sum_act_SurfaceWaterAbstract * self.var.cellArea
            # return flow from (m) non irrigation water demand
            # self.var.nonIrrReturnFlow = self.var.nonIrrReturnFlowFraction * self.var.nonIrrDemand
            # sideflowChanM3 +=  self.var.nonIrrReturnFlow * self.var.cellArea
            # sideflowChan = sideflowChanM3 * self.var.invchanLength * self.var.invdtRouting


        # ------------------------------------------------------
        # ***** SIDEFLOW **************************************

        runoffM3 = self.var.runoff * self.var.cellArea / self.var.noRoutingSteps

        # ************************************************************
        # ***** KINEMATIC WAVE                        ****************
        # ************************************************************

        self.var.sumsideflow = 0
        self.var.prechannelStorage = self.var.channelAlpha * self.var.chanLength * self.var.discharge ** self.var.beta
        avgDis = 0

        for subrouting in range(self.var.noRoutingSteps):

            sideflowChanM3 = runoffM3.copy()
            # minus evaporation from channels
            sideflowChanM3 -= EvapoChannelM3Dt
            if self.var.modflow:
                # minus riverbed exchange
                sideflowChanM3 -= riverbedExchangeDt

            if checkOption('includeWaterDemand'):
                sideflowChanM3 -= WDAddM3Dt
                # minus waterdemand + returnflow

            if checkOption('inflow'):
                self.var.inflowDt = (self.var.QInM3Old + (subrouting + 1) * self.var.QDelta) / self.var.noRoutingSteps
                # flow from inlets per sub step
                sideflowChanM3 += self.var.inflowDt

            if checkOption('includeWaterBodies'):
                lakesResOut, lakeOutflowDis = self.lakes_reservoirs_module.dynamic_inloop(subrouting)
                sideflowChanM3 += lakesResOut

            else:
                lakesResOut = 0

            # sideflowChan = sideflowChanM3 * self.var.invchanLength * self.var.InvDtSec
            sideflowChan = sideflowChanM3 * self.var.invchanLength * 1 / self.var.dtRouting

            if checkOption('includeWaterBodies'):
                lib2.kinematic(self.var.discharge, sideflowChan, self.var.dirDown_LR, self.var.dirupLen_LR,
                               self.var.dirupID_LR, Qnew, self.var.channelAlpha, self.var.beta,
                               self.var.dtRouting, self.var.chanLength, self.var.lendirDown_LR)

            else:
                lib2.kinematic(self.var.discharge, sideflowChan, self.var.dirDown, self.var.dirupLen,
                               self.var.dirupID, Qnew, self.var.channelAlpha, self.var.beta,
                               self.var.dtRouting, self.var.chanLength, self.var.lendirDown)
            self.var.discharge = Qnew.copy()

            self.var.sumsideflow = self.var.sumsideflow + sideflowChanM3
            avgDis = avgDis + self.var.discharge / self.var.noRoutingSteps

        # -- end substeping ---------------------

        if checkOption('includeWaterBodies'):
            # if there is a lake no discharge is calculated in the routing routine.
            # therefore this is filled up with the discharge which goes outof the lake
            # these outflow is used for the whole lake
            self.var.discharge = np.where(self.var.waterBodyID > 0, lakeOutflowDis, self.var.discharge)
        # discharge at the end of a time step

        preStor = self.var.channelStorage.copy()
        self.var.channelStorage = self.var.channelAlpha * self.var.chanLength * Qnew ** self.var.beta

        # discharge only at the outlets to sea or endorheic lakes, otherwise value is 0.
        # as average discharge over timestep e.g. 1 day
        self.var.dis_outlet = np.where(self.var.lddCompress == 5, avgDis, 0.)

        if checkOption('inflow'):
            self.var.QInM3Old = self.var.inflowM3.copy()

        # maybe later, but for now it is known as m3 -> put this active again PB May 2024
        self.var.EvapoChannel = self.var.EvapoChannel / self.var.cellArea


        self.var.humanConsumption = globals.inZero.copy()
        self.var.humanUse = globals.inZero.copy()
        self.var.natureUse = globals.inZero.copy()
        if 'includeCrops' in option:
            if checkOption('includeCrops'):
                for i in range(len(self.var.Crops)):
                    self.var.humanConsumption += self.var.actTransTotal_crops_nonIrr[i]
                    self.var.humanUse += self.var.actTransTotal_crops_nonIrr[i]

        # self.var.natureUse = actTransTotal_grasslands - self.var.humanUse + self.var.EvapoChannel +
        # self.var.sum_actBareSoilEvap + self.var.sum_interceptEvap + self.var.EvapWaterBodyM
        # EvapWaterBodyM is EvapWaterBodyMOutlet spread over the lake

        self.var.humanConsumption += (self.var.act_nonIrrConsumption + self.var.actTransTotal_paddy +
                                       self.var.addtoevapotrans + self.var.actTransTotal_nonpaddy +
                                       self.var.sum_openWaterEvap)
        self.var.humanUse += (self.var.act_nonIrrWithdrawal + self.var.act_irrWithdrawal)
        # + self.var.sum_openWaterEvap # + self.var.leakage # + reservoir evaporation

        if 'adminSegments' in binding:
            self.var.ETRefAverage_segments = npareaaverage(self.var.ETRef, self.var.adminSegments)
            self.var.precipEffectiveAverage_segments = npareaaverage(self.var.infiltration[1],
                                                                     self.var.adminSegments)
            if self.var.modflow:
                self.var.head_segments = npareaaverage(self.var.head, self.var.adminSegments)
                self.var.gwdepth_adjusted_segments = npareaaverage(self.var.gwdepth_adjusted, self.var.adminSegments)
                self.var.gwdepth_segments = npareaaverage(self.var.gwdepth, self.var.adminSegments)

            # self.var.precipEffectiveAverage_segments = npareaaverage(
            #     self.var.Rain - self.var.interceptEvap[1] - self.var.actBareSoilEvap[1],
            #     self.var.adminSegments)
            # self.var.head_development_segments = npareaaverage(self.var.head_development,
            #                                                   self.var.adminSegments)
            self.var.adminSegments_area = npareaaverage(
                (self.var.fracVegCover[1] + self.var.fracVegCover[2] + self.var.fracVegCover[3]) * self.var.cellArea,
                self.var.adminSegments)

# ---------------------------------------------------------------------------------------


