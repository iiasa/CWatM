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
from cwatm.hydrological_modules.routing_reservoirs.lakes_reservoirs import lakes_reservoirs


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
    compress_LR                          Array         boolean map as mask map for compressing lake/reservoir                  --   
    dirshort                             Array         index of the downstream cell (-1 at pits)                               --   
    lddCompress                          Array         compressed river network (without missing values)                       --   
    dirupLen_LR                          Array         number of bifurcation upstream lake/reservoir                           --   
    dirDown_LR                           Array         river network direktion downstream lake/reservoir                       --   
    lendirDown_LR                        Array         number of river network connections lake/reservoir                      --   
    lakeArea                             Array         area of each lake/reservoir                                             m2   
    lakeEvaFactorC                       Array         compressed map of a factor which increases evaporation from lake becau  --   
    fracAllCover                         Array                                                                                 --   
    riverbedExchangeM3                   Array         converting leakage in m3 (AI)                                           --   
    DtSec                                Array         number of seconds per timestep (default = 86400)                        s    
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
    sumResEvapWaterBodyC                 Array         sum of all routingsteps of evaporation from lakes and reservoirs   - s  --   
    discharge                            Array         Channel discharge                                                       m3 s-
    inflowDt                             Number        flow from inlets per sub step (AI)                                      --   
    inflowDay                            Array         inflow put into the routing during the day (sum of the sub steps)       m3   
    returnFlowLakeM3                     Array         return flow of lake cells, goes into the lake (not into the channel)    m3   
    downstruct                           Array         structure of the river network in downstream direction                  --   
    chanLength                           Array         Input, Channel length                                                   m    
    totalCrossSectionArea                Array         Total cross-sectional area at half bankfull (initial storage, MODFLOW)  m2   
    dirupLen                             Array                                                                                 --   
    dirupID                              Array                                                                                 --   
    catchment                            Array                                                                                 --   
    dirDown                              Array                                                                                 --   
    lendirDown                           Number                                                                                --   
    UpArea                               Array         upstream area of a grid cell                                            m2   
    beta                                 Array         kinematic wave parameter: 0.6 is for broad sheet flow (AI)              --   
    chanMan                              Array         Input, Channel Manning's roughness coefficient                          s m(-
    chanGrad                             Array         Channel gradient (fraction, dy/dx) (AI)                                 --   
    chanWidth                            Array         Input, Channel width                                                    m    
    chanDepth                            Array         Input, Channel depth                                                    m    
    invbeta                              Array         Inverse of beta for kinematic wave (AI)                                 --   
    invchanLength                        Array         Inverse of channel length [1/m] (AI)                                    --   
    invdtRouting                         Array                                                                                 --   
    totalCrossSectionAreaBankFull        Array         Area (sq m) of bank full discharge cross section [m2] (AI)              --   
    chanWettedPerimeterAlpha             Array         Channel wetted perimeter [m] (AI)                                       --   
    alpPower                             Array                                                                                 --   
    channelAlpha                         Array                                                                                 --   
    invchannelAlpha                      Array                                                                                 --   
    EvapoChannel                         Array         Channel evaporation                                                     m    
    QDelta                               Array         difference between old and new inlet flow  per sub step in order to ca  --   
    avgdischarge                         Array         calculating average discharge during day and max discharge (AI)         --   
    maxdischarge                         Array         discharge at the end of a time step (AI)                                --   
    dis_outlet                           Array         discharge only at the outlets to sea or endorheic lakes, otherwise val  --   
    runoff_m3                            Array         back to [m]  # with and without in m3 (AI)                              --   
    openWaterEvap                        Array         Simulated evaporation from open areas                                   m    
    cellArea                             Array         Area of cell                                                            m2   
    act_SurfaceWaterAbstract             Array         Surface water abstractions                                              m    
    act_bigLakeResAbst                   Array         Abstractions to satisfy demands from lakes and reservoirs               m    
    act_smallLakeResAbst                 Array         Abstractions from small lakes at demand location                        m    
    returnFlow                           Array                                                                                 --   
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

        # repaired river network and upstream directions (same as for the routing, routing_sub.lddNetwork)
        lddCompress, dirshort, dirupLen, dirupID = lddNetwork(ldd)

        c1 = catchment1(dirshort, point)

        # decompressing catchment from 1D -> 2D
        # plain array with 0 outside the mask (maskall holds random memory under its mask; a masked c2 passed on
        # to maskfrompoint lets such values become active cells)
        dmap = maskinfo['maskall'].copy()
        dmap[~maskinfo['maskflat']] = c1[:]
        c2 = np.ma.filled(dmap, 0).reshape(maskinfo['shape']).astype(np.int64)

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

        # dirshort: index of the downstream cell (-1 at pits), used for catchments of gauges and lakes
        (self.var.lddCompress, self.var.dirshort, self.var.dirupLen, self.var.dirupID,
         self.var.downstruct, self.var.catchment, self.var.dirDown, self.var.lendirDown) = defLdd2(ldd)
        dirshort = self.var.dirshort

        # ---------------------------------------------------------------
        # parallel kinematic wave: number of threads (nodes)
        # by basin size: 1 node per 15000 cells, at least 2 (small basins gain nothing from more threads:
        # Morava 11850 cells -> 2, Bhima 56347 cells -> 4)
        # upper limit: maxnodes in [ROUTING] if given (maxnodes = 1: serial),
        # otherwise 2/3 of the CPUs (at least 2, at most 16)
        # never more than the CPUs this run may use; calibration runs use 1 node
        if hasattr(os, "sched_getaffinity"):
            cores = len(os.sched_getaffinity(0))   # Linux: only the CPUs this run may use (e.g. SLURM job)
        else:
            cores = os.cpu_count() or 1            # Windows / Mac: all logical CPUs
        if 'SLURM_CPUS_PER_TASK' in os.environ:    # SLURM: not more than the CPUs reserved for the job
            cores = min(cores, int(os.environ['SLURM_CPUS_PER_TASK']))
        if 'maxnodes' in binding:
            upper = int(loadmap('maxnodes'))
        else:
            upper = min(16, max(2, (2 * cores) // 3))
        nodes = max(2, -(-globals.inZero.size // 15000))
        nodes = min(nodes, upper, cores)
        self.var.nodesrouting = max(1, min(nodes, lib2.kinematicParMaxThreads()))


        if Flags['calib'] or Flags['warm']:
            self.var.nodesrouting = 1
        if Flags['loud']:
            print("Routing: kinematic wave on", self.var.nodesrouting, "node(s)")
        # levels of the river network, computed once
        self.var.levelOrder, self.var.levelStart, self.var.nlevels = kinematicLevels(
            self.var.dirDown, self.var.dirupLen, self.var.dirupID)

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
        # the kinematic wave (t6 library) takes beta as one number (fast path for 0.6)
        if np.ndim(self.var.beta) > 0:
            msg = "Error 175: chanBeta has to be a single number (e.g. 0.6), not a map\n"
            raise CWATMError(msg)
        # Channel Manning's n
        self.var.chanMan = loadmap('chanMan') * manningsFactor
        # Channel gradient (fraction, dy/dx)
        self.var.chanGrad = np.maximum(loadmap('chanGrad'), loadmap('chanGradMin'))
        # Channel length [meters]
        self.var.chanLength = loadmap('chanLength').astype(np.float64)
        # Channel bottom width [meters]
        self.var.chanWidth = loadmap('chanWidth').astype(np.float64)

        # Bankfull channel depth [meters]
        self.var.chanDepth = loadmap('chanDepth').astype(np.float64)



        # -----------------------------------------------
        # Inverse of beta for kinematic wave
        self.var.invbeta = 1 / self.var.beta
        # Inverse of channel length [1/m]
        self.var.invchanLength = 1 / self.var.chanLength

        # Corresponding sub-timestep (seconds)
        self.var.dtRouting = self.var.DtSec / self.var.noRoutingSteps
        self.var.invdtRouting = 1 / self.var.dtRouting
        # sideflow [m3 per substep] -> [m2 s-1] for the kinematic wave: sideflowM3 / chanLength / dtRouting
        self.var.sideflowFactor = self.var.invchanLength / self.var.dtRouting

        # channel fraction of a cell, for the evaporation from channels (static)
        self.var.channelFraction = np.minimum(1.0, self.var.chanWidth * self.var.chanLength / self.var.cellArea)

        # -----------------------------------------------
        # ***** CHANNEL GEOMETRY  ************************************

        # Area (sq m) of bank full discharge cross section [m2]
        self.var.totalCrossSectionAreaBankFull = self.var.chanDepth * self.var.chanWidth
        # Cross-sectional area at half bankfull [m2]
        # This can be used to initialise channel flow (see below)
        #TotalCrossSectionAreaHalfBankFull = 0.5 * self.var.TotalCrossSectionAreaBankFull
        # TotalCrossSectionAreaInitValue = loadmap('TotalCrossSectionAreaInitValue')
        # Total cross-sectional area [m2]: half bankfull (also used by MODFLOW, groundwater_modflow/transient.py)
        self.var.totalCrossSectionArea = 0.5 * self.var.totalCrossSectionAreaBankFull

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
        self.var.channelAlpha = self.var.channelAlpha.astype(np.float64)
        ca = 2.5 * self.var.chanMan * ((1 / np.sqrt(self.var.chanGrad)) ** self.var.beta) * \
             (self.var.chanWettedPerimeterAlpha ** self.var.alpPower)


        self.var.invchannelAlpha = 1. / self.var.channelAlpha

        # -----------------------------------------------
        # ***** CHANNEL INITIAL DISCHARGE ****************************

        # channel water volume [m3]
        # Initialise water volume in kinematic wave channels [m3]: 0.1 * half bankfull = 5 % of bankfull
        # (if channelStorage is not loaded from an init file)
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


        # if checkOption('includeWaterDemand'):
        #     self.var.readAvlChannelStorage = 0.95 * self.var.channelStorage
        #    # to avoid small values and to avoid surface water abstractions from dry channels (>= 0.5mm)
        #    self.var.readAvlChannelStorage = np.where(self.var.readAvlChannelStorage < (0.0005 * self.var.cellArea),0.,self.var.readAvlChannelStorage)

        # factor for evaporation from lakes, reservoirs and open channels
        self.var.lakeEvaFactor = globals.inZero + loadmap('lakeEvaFactor')


        #self.var.channelAlphaPcr = decompress(self.var.channelAlpha)
        #self.var.chanLengthPcr = decompress(self.var.chanLength)


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

        # Evaporation from open channel (channel fraction of the cell: self.var.channelFraction, from initial)
        # from big lakes/res and small lakes/res is calculated separately
        EWRefact = np.maximum(0.0, self.var.lakeEvaFactor * self.var.EWRef - self.var.openWaterEvap[5])
        # evaporation from channel minus the calculated evaporation from rainfall
        self.var.EvapoChannel = EWRefact * self.var.channelFraction * self.var.cellArea
        #self.var.EvapoChannel = self.var.EWRef * channelFraction * self.var.cellArea
        # (restricted to 95 % of the channel storage below, after the lake cells are set to 0)



        # riverbed infiltration: with MODFLOW riverbedExchangeM3 from landcoverType.py (taken from the channel below)

        if checkOption('includeWaterBodies'):
            # add reservoirs depending on year

            # ------------------------------------------------------------
            # evaporation from water bodies (m3), will be limited by available water in lakes and reservoirs
            # calculate outflow from lakes and reservoirs

            # evaporation rate of each lake: lakeEvaFactorC * EWRef - openWaterEvap[5], both averaged over the lake,
            # the factor applied once (map value at the outlet, or the value from the reservoir Excel sheet)
            # same rate as for channels and small lakes (before 2026-11-04 the factor was applied twice: in EWRefact
            # and again here)
            EWRefavgC = np.compress(self.var.compress_LR, self.var.waterBodyIndex.average(self.var.EWRef))
            openWaterEvapavgC = np.compress(self.var.compress_LR, self.var.waterBodyIndex.average(self.var.openWaterEvap[5]))
            lakeAreaC = np.compress(self.var.compress_LR, self.var.lakeArea)
            # evaporation for the whole lake for each routing step, compressed to the number of lakes
            self.var.evapWaterBodyC = np.maximum(0.0, self.var.lakeEvaFactorC * EWRefavgC - openWaterEvapavgC) * \
                                      lakeAreaC / self.var.noRoutingSteps
            # no channel evaporation in lake cells: lake cells have no channel (pits of the lake network),
            # the evaporation of a lake is evapWaterBodyC
            self.var.EvapoChannel = np.where(self.var.waterBodyID > 0, 0., self.var.EvapoChannel)

            # sum of all routingsteps of evaporation from lakes and reservoirs   - set to 0 each time step
            self.var.sumResEvapWaterBodyC = self.var.evapWaterBodyC * 0.
            self.var.sumLakeEvapWaterBodyC = self.var.evapWaterBodyC * 0.

        # channel withdrawals of the day [m3]: MODFLOW leakage + channel abstraction; return flow into the channel [m3]
        withdrawM3 = globals.inZero.copy()
        returnM3 = 0.
        if self.var.modflow:
            # water infiltrating from river to groundwater
            withdrawM3 += self.var.riverbedExchangeM3

        if checkOption('inflow'):
            self.var.QDelta = (self.var.inflowM3 - self.var.QInM3Old) / self.var.noRoutingSteps
            # difference between old and new inlet flow  per sub step
            # in order to calculate the amount of inlet flow in the routing loop
            # inflow put into the routing during the day (sum of the sub steps) for the WaterCycle output
            self.var.inflowDay = globals.inZero.copy()

        # return flow of lake cells (water demand): lake cells have no channel -> handed to the lake module
        self.var.returnFlowLakeM3 = 0.

        if checkOption('includeWaterDemand'):
            # self.var.act_SurfaceWaterAbstract includes channel abstractions as well as abstractions from lakes and reservoirs
            # In waterdemand.py: self.var.act_SurfaceWaterAbstract = self.var.act_SurfaceWaterAbstract + self.var.act_bigLakeResAbst + self.var.act_smallLakeResAbst
            # The abstractions from lakes and reservoirs have already been dealt with by removing these amounts from their storages in the same module
            # The water abstractions from the channel are thus the surface water abstractions subtract the lake and reservoir abstractions

            if checkOption('includeWaterBodies'):
                # (wastewater reuse act_bigLakeResAbst_wwt: taken from the wastewater reservoirs in water_demand.py,
                # not from the channels - before 2026-10-16 it was taken from the channels too)
                channelAbstM = self.var.act_SurfaceWaterAbstract - \
                            (self.var.act_bigLakeResAbst + self.var.act_smallLakeResAbst + self.var.act_bigLakeResAbst_wwt)
            else:
                channelAbstM = self.var.act_SurfaceWaterAbstract
            withdrawM3 += channelAbstM * self.var.cellArea

            # return flow from (m) non irrigation water demand
            if checkOption('includeWaterBodies'):
                # return flow of lake cells is not put into the channel of lake cells (pits of the lake network)
                self.var.returnFlowLakeM3 = np.where(self.var.waterBodyID > 0, self.var.returnFlow * self.var.cellArea, 0.)
                returnM3 = np.where(self.var.waterBodyID > 0, 0., self.var.returnFlow) * self.var.cellArea
            else:
                returnM3 = self.var.returnFlow * self.var.cellArea


        # ------------------------------------------------------
        # ***** SIDEFLOW **************************************

        runoffM3 = self.var.runoff_m3 / self.var.noRoutingSteps

        # ************************************************************
        # ***** KINEMATIC WAVE                        ****************
        # ************************************************************

        self.var.avgdischarge = globals.inZero.copy()
        self.var.maxdischarge = globals.inZero.copy()
        avglakeoutflow = 0
        maxlakeoutflow = 0

        # evaporation from channel restricted to 95% of channel storage -> something should stay in the river
        self.var.EvapoChannel = np.where((0.95 * self.var.channelStorage - self.var.EvapoChannel) > 0.0,
                                         self.var.EvapoChannel, 0.95 * self.var.channelStorage)

        # sideflow part which is the same in each substep, calculated once
        # runoff + return flow - withdrawals (abstraction, leakage) - channel evaporation, spread evenly over the
        # substeps
        # (2026-11-05: taking the withdrawals from the storage at the start of the day (review B4 option a) was taken
        # back - the reduced start discharge broke the water balance of the channels (Bhima +4 mm/yr): the lake inflow
        # of a substep is the discharge of the cells upstream of the lake before the substep, so the water of the last
        # substep, in transit into the lake, was cut at the start of the next day)
        sideflowBaseM3 = runoffM3 + (returnM3 - withdrawM3 - self.var.EvapoChannel) / self.var.noRoutingSteps

        # options and river network once for all substeps
        inflowOn = checkOption('inflow')
        lakesOn = checkOption('includeWaterBodies')
        if lakesOn:
            net = (self.var.levelOrder_LR, self.var.levelStart_LR, self.var.nlevels_LR, self.var.dirupLen_LR,
                   self.var.dirupID_LR)
        else:
            net = (self.var.levelOrder, self.var.levelStart, self.var.nlevels, self.var.dirupLen, self.var.dirupID)

        for subrouting in range(self.var.noRoutingSteps):

            sideflowChanM3 = sideflowBaseM3.copy()

            if inflowOn:
                self.var.inflowDt = (self.var.QInM3Old + (subrouting + 1) * self.var.QDelta) / self.var.noRoutingSteps
                # flow from inlets per sub step
                sideflowChanM3 += self.var.inflowDt
                self.var.inflowDay += self.var.inflowDt

            if lakesOn:
                lakesResOut, lakeOutflowDis = self.lakes_reservoirs_module.dynamic_inloop(subrouting)
                sideflowChanM3 += lakesResOut

            # [m3 per substep] -> [m2 s-1]
            sideflowChan = sideflowChanM3 * self.var.sideflowFactor

            lib2.kinematicPar(self.var.discharge, sideflowChan, net[0], net[1], net[2], net[3], net[4], Qnew,
                              self.var.channelAlpha, self.var.beta, self.var.dtRouting, self.var.chanLength,
                              self.var.nodesrouting)
            if lakesOn:
                avglakeoutflow = avglakeoutflow + lakeOutflowDis / self.var.noRoutingSteps
                maxlakeoutflow = np.maximum(maxlakeoutflow, lakeOutflowDis)

            # new discharge; the old array is the buffer for the next substep (kinematicPar writes every cell)
            self.var.discharge, Qnew = Qnew, self.var.discharge

            # calculating average discharge during day and max discharge
            np.add(self.var.avgdischarge, self.var.discharge / self.var.noRoutingSteps, out=self.var.avgdischarge)
            np.maximum(self.var.maxdischarge, self.var.discharge, out=self.var.maxdischarge)

        # discharge of the kinematic wave at the end of the day (before the lake cells get the lake outflow)
        Qnew = self.var.discharge

        # -- end substeping ---------------------

        if checkOption('includeWaterBodies'):
            # if there is a lake no discharge is calculated in the routing routine.
            # therefore this is filled up with the discharge which goes outof the lake
            # these outflow is used for the whole lake
            self.var.discharge = np.where(self.var.waterBodyID > 0, lakeOutflowDis, self.var.discharge)
            self.var.avgdischarge = np.where(self.var.waterBodyID > 0, avglakeoutflow, self.var.avgdischarge)
            self.var.maxdischarge = np.where(self.var.waterBodyID > 0, maxlakeoutflow, self.var.maxdischarge)
        # discharge at the end of a time step

        preStor = self.var.channelStorage.copy()
        self.var.channelStorage = self.var.channelAlpha * self.var.chanLength * Qnew ** self.var.beta
        if checkOption('includeWaterBodies'):
            # lake cells have no channel: the water of a lake is in lakeResStorage (the kinematic wave of lake cells,
            # pits of the lake network, is not used - their discharge is the lake outflow)
            self.var.channelStorage = np.where(self.var.waterBodyID > 0, 0., self.var.channelStorage)

        # discharge only at the outlets to sea or endorheic lakes, otherwise value is 0.
        # as average discharge over timestep e.g. 1 day
        self.var.dis_outlet = np.where(self.var.lddCompress == 5, self.var.avgdischarge, 0.)        
        
        if checkOption('inflow'):
            self.var.QInM3Old = self.var.inflowM3.copy()

        # maybe later, but for now it is known as m3 -> put this active again PB May 2024
        self.var.EvapoChannel = self.var.EvapoChannel / self.var.cellArea

        # humanConsumption, humanUse, natureUse and the averages per adminSegment (output only): since 2026-11-04 in
        # water_demand.dynamic_output, computed only if they are in the output

# ---------------------------------------------------------------------------------------


