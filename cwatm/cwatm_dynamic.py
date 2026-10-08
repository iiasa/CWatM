# -------------------------------------------------------------------------
# Name: CWATM Dynamic
# Purpose: Temporal execution engine managing hydrological process time-stepping.
# Coordinates sequential execution of water cycle components for each simulation step.
# Handles water balance calculations, timing profiler, and MODFLOW integration.
#
# Author:      PB
# Created:     16/05/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

# Standard library imports
import time

# Local imports
from cwatm.management_modules.data_handling import *
from cwatm.management_modules.messages import *


class CWATModel_dyn(DynamicModel):
    """
    CWatM dynamic model execution class for temporal hydrological simulation.
    
    This class implements the temporal loop of the CWatM hydrological model,
    executing all hydrological processes for each time step in the simulation
    period. It coordinates the sequential execution of hydrological modules
    to simulate the complete water cycle including precipitation, evapotranspiration,
    soil processes, groundwater, surface runoff, routing, and water management.
    
    The dynamic execution follows a specific sequence to maintain physical
    consistency and proper water balance accounting throughout the hydrological
    system.
    
    Attributes
    ----------
    All attributes are inherited from the parent DynamicModel class and
    initialized in the CWATModel_ini class, including:
    - Hydrological module instances
    - Model state variables (self.var)
    - Configuration parameters (self.conf)
    - Timing and output systems
    
    Notes
    -----
    The execution order is critical for maintaining water balance and
    physical consistency. The sequence follows the natural hydrological
    cycle from atmospheric inputs through terrestrial processes to
    surface water routing and water management.
    
    Performance timing is tracked for each major process group to
    identify computational bottlenecks and optimize model efficiency.

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    channelStorage                       Array         Channel water storage                                                   m3   
    unmetDemand_runningSum               Array         Unmet water demand (too less water availability)                        m    
    totalET_WB                           Array         Total evapotranspiration including waterbodies                          m    
    lakeReservoirStorage                 Array         Storage of lakes and reservoirs                                         m3   
    tws                                  Array         Total water storage                                                     m    
    modflow                              Flag          True if modflow_coupling = True in settings file                        bool 
    storGroundwater                      Array         Groundwater storage (non-fossil). This is primarily used when not usin  m    
    smallevapWaterBody                   Array         Evaporation from small lakes                                            m    
    EvapWaterBodyM                       Array         Evaporation from lakes and reservoirs                                   m    
    dynamicLandcover                     Flag          If landcover changes per year or is constant                            bool 
    totalET                              Array         Total evapotranspiration for each cell including all landcover types    m    
    totalSto                             Array         Total soil,snow and vegetation storage for each cell including all lan  m    
    InvCellArea                          Array         Inverse of cell area of each simulated mesh                             1/m2 
    EvapoChannel                         Array         Channel evaporation                                                     m3   
    gridcell_storage                     Array         storage of water due to runoff concentration                            m    
    groundwater_storage_available        Array         Groundwater storage. Used with MODFLOW.                                 m    
    lakeResStorage                       Array                                                                                 --   
    smalllakeStorage                     Array                                                                                 --   
    unmetDemand                          Array         Unmet groundwater demand to determine potential fossil groundwaterwate  m    
    ===================================  ==========    ======================================================================  =====

    """

    # =========== DYNAMIC ====================================================

    def dynamic(self):
        """
        Execute one time step of the complete hydrological simulation.
        
        Performs the temporal execution of all hydrological processes for the
        current time step, following the natural sequence of the water cycle.
        This method coordinates all hydrological modules to simulate water
        movement and storage changes throughout the terrestrial hydrological
        system.
        
        The execution sequence includes:
        1. Time step management and meteorological data reading
        2. Potential evapotranspiration calculation
        3. Precipitation partitioning (rain/snow) and snow processes
        4. Land cover dynamics and irrigation scheduling
        5. Soil water processes across different land cover types
        6. Groundwater processes (standard or MODFLOW coupling)
        7. Surface runoff concentration and small water body processes
        8. Channel routing and large water body management
        9. Water quality calculations
        10. Total water storage accounting
        11. Environmental flow assessment
        12. Output generation and state variable updates
        
        Parameters
        ----------
        None
            All required data accessed through self.var and module instances
            
        Returns
        -------
        None
            Results stored in model state variables and written to output files
            
        Notes
        -----
        Special execution modes:
        - Environmental flow only: If calc_environflow is True and
          calc_ef_afterRun is False, only environmental flow is calculated
        - Calibration mode: If Flags['calib'] is True, only meteorological
          data reading and output generation are performed
          
        Output verbosity controlled by flags:
        - 'v' or 'veryquiet': No progress output
        - 'l' or 'loud': Time step and discharge information
        - 't' or 'printtime': Detailed timing of each process
        
        Total Water Storage (TWS) calculation includes:
        - Groundwater storage (available or with unmet demand accounting)
        - Soil moisture storage across all layers and land cover types
        - Surface water storage (lakes, reservoirs, channels)
        - Runoff concentration storage (if enabled)
        
        MODFLOW integration:
        - When self.var.modflow is True, uses groundwater_modflow_module
        - Requires proper finalization at simulation end to close files
        - Temporary MODFLOW files must be properly managed for multi-run scenarios
        """

        # self.CalendarDate = dateVar['dateStart'] + datetime.timedelta(days=dateVar['curr'])
        # self.CalendarDay = int(self.CalendarDate.strftime("%j"))
        timestep_dynamic(self)

        del timeMes[:]
        timemeasure("Start dynamic")

        # ************************************************************
        """ up to here it was fun, now the real stuff starts
        """

        if checkOption('calc_environflow') and not returnBool('calc_ef_afterRun'):
            # if only the dis is used for calculation of EF
            self.environflow_module.dynamic()
            self.output_module.dynamic(ef=True)
            header = "\n\n ======================== CWATM ONLY EF calculation===========\n"
            print(header + "done with Environmental Flow\n")
            sys.exit(400)

        self.readmeteo_module.dynamic()
        timemeasure("Read meteo")  # 1. timing after read input maps

        if Flags['calib']:
            self.output_module.dynamic()
            return

        self.evaporationPot_module.dynamic()
        timemeasure("ET pot")  # 2. timing after read input maps

        # if Flags['check']: return  # if check than finish here

        """ Here it starts with hydrological modules:
        """

        # ***** INFLOW HYDROGRAPHS (OPTIONAL)****************
        self.inflow_module.dynamic()
        self.lakes_reservoirs_module.dynamic()

        # ***** RAIN AND SNOW *****************************************
        self.snowfrost_module.dynamic()
        timemeasure("Snow")  # 3. timing

        # if only snow the skip the rest:
        if not self.var.stopaftersnow:

        # ***** READ land use fraction maps***************************
            self.landcoverType_module.dynamic_fracIrrigation(init=dateVar['newYear'],
                                                              dynamic=self.var.dynamicLandcover)
            self.capillarRise_module.dynamic()
            timemeasure("Soil 1.Part")  # 4. timing

            # *********  Soil splitted in different land cover fractions *************
            self.landcoverType_module.dynamic()
            timemeasure("Soil main")  # 5. timing

            if self.var.modflow:
                self.groundwater_modflow_module.dynamic()
            else:
                self.groundwater_module.dynamic()
            timemeasure("Groundwater")  # 7. timing

            self.runoff_concentration_module.dynamic()
            timemeasure("Runoff conc.")  # 8. timing

            self.lakes_res_small_module.dynamic()
            timemeasure("Small lakes")  # 9. timing

            self.routing_kinematic_module.dynamic()
            timemeasure("Routing_Kin")  # 10. timing

            self.waterquality1.dynamic()

            # calculate Total water storage (tws) [m] as a sum of
            # Groundwater [m] + soil [m] + lake and reservoir storage [m3] + channel storage [m3]
            # [m3] >> [m] --> * InvCellArea

            if self.var.modflow:
                groundwater_storage = self.var.groundwater_storage_available
            elif checkOption('limitAbstraction'):
                groundwater_storage = self.var.storGroundwater
                self.var.unmetDemand_runningSum = self.var.storGroundwater * 0
            else:
                self.var.unmetDemand_runningSum += self.var.unmetDemand
                groundwater_storage = self.var.storGroundwater - self.var.unmetDemand_runningSum

            if checkOption('includeRouting'):
                self.var.totalET_WB = self.var.EvapoChannel.copy()
                if checkOption('includeWaterBodies'):
                    if returnBool('useSmallLakes'):
                        # Sum of lake and reservoirs and small lakes
                        self.var.lakeReservoirStorage = self.var.lakeResStorage + self.var.smalllakeStorage
                    else:
                        # Sum of lake and reservoirs - here without small lakes
                        self.var.lakeReservoirStorage = self.var.lakeResStorage.copy()

                    self.var.tws = (groundwater_storage + self.var.totalSto +
                                    self.var.lakeReservoirStorage * self.var.InvCellArea +
                                    self.var.channelStorage * self.var.InvCellArea)

                    self.var.totalET_WB = (self.var.totalET_WB + self.var.totalET + self.var.EvapWaterBodyM)
                    if returnBool('useSmallLakes'):
                        self.var.totalET_WB = (self.var.totalET_WB + self.var.smallevapWaterBody)
                else:
                    self.var.tws = (groundwater_storage + self.var.totalSto +
                                    self.var.channelStorage * self.var.InvCellArea)
            else:
                self.var.tws = groundwater_storage + self.var.totalSto

            if checkOption('includeRunoffConcentration'):
                self.var.tws = self.var.tws + self.var.gridcell_storage


            # ------------------------------------------------------
            # End of calculation -----------------------------------
            # ------------------------------------------------------

            self.environflow_module.dynamic()
            # in case environmental flow is calculated last

        self.output_module.dynamic()
        timemeasure("Output")  # 12. timing

        self.init_module.dynamic()

        for i in range(len(timeMes)):
            # if self.currentTimeStep() == self.firstTimeStep():
            if self.currentStep == self.firstStep:
                timeMesSum.append(timeMes[i] - timeMes[0])
            else:
                timeMesSum[i] += timeMes[i] - timeMes[0]

        # MODFLOW cleanup: temporary files produced by MODFLOW/Flopy must be properly closed
        # with finalize() to prevent file access conflicts in subsequent runs (pytest, calibration)
        if self.var.modflow:
            if self.currentStep == self.lastStep:
                self.groundwater_modflow_module.modflow.finalize()



