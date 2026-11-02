# -------------------------------------------------------------------------
# Name:        Small Lakes and reservoirs module
# Purpose: Small lakes and reservoirs module for local water body processes.
# Simulates water storage and dynamics in small water bodies with limited influence.
# Handles local retention and evaporation from small-scale water features.
#
# Author:      PB
# Created:     30/08/2017
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
from cwatm.hydrological_modules.routing_reservoirs.routing_sub import *


from cwatm.management_modules.globals import *


class lakes_res_small(object):
    """
    Small lakes and reservoirs module for water bodies with limited catchment area.
    
    Handles water retention and outflow calculations for small water bodies
    (catchment area < 5000 km2 or lake area < 100 km2) using the modified Puls
    approach. Processes distributed small water bodies within grid cells rather
    than individual large water bodies.
    
    Attributes
    ----------
    var : object
        Reference to model variables object containing state variables
    model : object
        Reference to the main CWatM model instance
        
    Notes
    -----
    Small water bodies are treated as distributed features within grid cells,
    with each cell containing a fraction of water body coverage. The module
    uses the same modified Puls method as large water bodies but applies it
    to aggregated small water body characteristics.
    









    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    load_initial                         Flag          Settings initLoad holds initial conditions for variables                bool 
    smallpart                            Array         fraction of the cell area which is the catchment of small lakes         --   
    smalllakeArea                        Array         Lake area of small lakes (not part of the main river network)           m2   
    smalllakeDis0                        Array         average discharge of small lakes (for lake parameter A, min 0.01)       m3 s-
    smalllakeA                           Array         Lake parameter A of small lakes (channel width, gravity, weir coeff.)   --   
    smalllakeFactor                      Array         Modified Puls factor of small lakes: area / (dt * sqrt(A))              --   
    smalllakeFactorSqr                   Array         square of smalllakeFactor                                               --   
    smalllakeInflowOld                   Array         Inflow of the previous day                                              m3 s-
    smalllakeOutflow                     Array         Outflow from small lakes                                                m3 s-
    smalllakeLevel                       Array         Lake level for small lakes                                              m    
    smallLakeIn                          Array         Inflow into small lakes = lakeIn * time / area                          m    
    smallevapWaterBody                   Array         Evaporation from small lakes                                            m    
    smallLakeout                         Array         Outflow from small lakes per day                                        m3   
    DtSec                                Array         number of seconds per timestep (default = 86400)                        s    
    InvDtSec                             Array         inversere of seconds per timestep (default 1/86400)                     1 s-1
    EWRef                                Array         potential evaporation rate from water surface                           m    
    lakeEvaFactor                        Array         a factor which increases evaporation from lake because of wind          --   
    runoff_m3                            Array         runoff of the cell (after small lakes: outflow + rest of the cell)      m3   
    cellArea                             Array         Area of cell                                                            m2   
    smalllakeVolumeM3                    Array         Puls volume of small lakes (abstraction subtracted in water_demand)     m3   
    smalllakeStorage                     Array         water balance storage of small lakes (in - out - evap - abstraction)    m3   
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize small lakes and reservoirs module.
        
        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.var = model.var
        self.model = model

    def puls_parameters(self):
        """
        Lake parameter A and Modified Puls factor of the small lakes
        (depend on smalllakeArea and - with averageRunoff - on smallpart: new each year with dynamicLakesRes)
        """
        # lake discharge at outlet to calculate alpha: parameter of channel width, gravity and weir coefficient
        # Lake parameter A (suggested  value equal to outflow width in [m])
        # multiplied with the calibration parameter LakeMultiplier
        if "averageRunoff" in binding:
            self.var.smalllakeDis0 = (loadmap('averageRunoff') * self.var.smallpart *
                                      self.var.cellArea * self.var.InvDtSec)
        else:
            self.var.smalllakeDis0 = loadmap('smallwaterBodyDis')
        self.var.smalllakeDis0 = np.maximum(self.var.smalllakeDis0, 0.01)
        chanwidth = 7.1 * np.power(self.var.smalllakeDis0, 0.539)
        self.var.smalllakeA = loadmap('lakeAFactor') * 0.612 * 2 / 3 * chanwidth * (2 * 9.81) ** 0.5
        self.var.smalllakeFactor = self.var.smalllakeArea / (self.var.DtSec * np.sqrt(self.var.smalllakeA))
        # for faster calculation inside dynamic section
        self.var.smalllakeFactorSqr = np.square(self.var.smalllakeFactor)

    def initial(self):
        """
        Initialize small water body parameters and initial conditions.
        
        Loads spatial data for small water bodies including catchment fractions,
        water body areas, discharge characteristics, and initial storage conditions.
        Calculates hydraulic parameters for modified Puls method application.
        
        Notes
        -----
        Initialization includes:
        - Reading catchment area fractions for each grid cell
        - Loading small water body surface areas
        - Calculating discharge coefficients and lake factors
        - Setting initial storage, inflow, and outflow conditions
        
        Small water bodies are characterized by:
        - Distributed coverage within grid cells (smallpart fraction)
        - Aggregated hydraulic characteristics per cell
        - Modified Puls parameters adapted for small-scale features
        """

        if checkOption('includeWaterBodies') and returnBool('useSmallLakes'):

            if returnBool('useResAndLakes') and returnBool('dynamicLakesRes'):
                year = datetime.datetime(dateVar['currDate'].year, 1, 1)
            else:
                year = datetime.datetime(int(binding['fixLakesResYear']), 1, 1)


            # read which part of the cellarea is a lake/res catchment (sumed up for all lakes/res in a cell)
            self.var.smallpart = (readnetcdf2('smallLakesRes', year, useDaily="yearly", value='watershedarea') * 
                                  1000 * 1000)
            self.var.smallpart = self.var.smallpart / self.var.cellArea
            self.var.smallpart = np.minimum(1., self.var.smallpart)

            self.var.smalllakeArea = (readnetcdf2('smallLakesRes', year, useDaily="yearly", value='area') * 
                                      1000 * 1000)


            # lake parameter A and Modified Puls factor
            self.puls_parameters()

            # inflow in m3/s estimate
            # cells without a small lake get no starting inflow (smalllakeDis0 >= 0.01 is only for parameter A)
            inflowIni = np.where(self.var.smalllakeArea > 0, self.var.smalllakeDis0, 0.)
            self.var.smalllakeInflowOld = self.var.load_initial("smalllakeInflow", inflowIni)
            
            old = self.var.smalllakeArea * np.sqrt(self.var.smalllakeInflowOld / self.var.smalllakeA)
            self.var.smalllakeVolumeM3 = self.var.load_initial("smalllakeStorage", old)


            smalllakeStorageIndicator = np.maximum(0.0, self.var.smalllakeVolumeM3 / self.var.DtSec + 
                                                   self.var.smalllakeInflowOld / 2)
            out = np.square(-self.var.smalllakeFactor + np.sqrt(self.var.smalllakeFactorSqr + 
                                                               2 * smalllakeStorageIndicator))
            # SI = S/dt + Q/2
            # solution of quadratic equation
            # 1. storage volume is increase proportional to elevation
            # 2. Q= a *H **2.0  (if you choose Q= a *H **1.5 you have to solve the formula of Cardano)
            self.var.smalllakeOutflow = self.var.load_initial("smalllakeOutflow", out)

            # lake storage ini
            self.var.smalllakeLevel = divideValues(self.var.smalllakeVolumeM3, self.var.smalllakeArea)
            # water balance storage (in - out - evap; differs from the Puls volume by (Q - Qstart) * dt / 2)
            # from the init file - cold start or old init file: = volume
            self.var.smalllakeStorage = self.var.load_initial("smalllakeStorageBalance", self.var.smalllakeVolumeM3.copy())



   # ------------------ End init ------------------------------------------------------------------------------------
   # ----------------------------------------------------------------------------------------------------------------


    def dynamic(self):
        """
        Calculate outflow from small water bodies for current time step.
        
        Processes water balance for distributed small lakes and reservoirs within
        each grid cell, applying the modified Puls method to determine outflow
        based on inflow from cell runoff and current storage conditions.
        
        Notes
        -----
        Processing steps:
        - Update water body areas and catchment fractions if dynamic
        - Calculate inflow from cell runoff based on catchment fraction
        - Apply modified Puls method for outflow calculation
        - Account for evaporation losses from water surfaces
        - Update storage and water levels
        - Modify cell runoff to account for water body effects
        
        The method partitions cell runoff between:
        - Flow to small water bodies (smallpart fraction)
        - Direct runoff to channel network (1-smallpart fraction)
        """

        def dynamic_smalllakes(inflow):
            """
            Calculate small lake outflow using modified Puls method.
            
            Applies water balance equation to determine outflow from small lakes
            based on current inflow, storage, and hydraulic characteristics.
            
            Parameters
            ----------
            inflow : numpy.ndarray
                Inflow to small lakes [m3] per time step
                
            Returns
            -------
            numpy.ndarray
                Lake outflow [m3] per time step
                
            Notes
            -----
            The modified Puls method solves:
            (S2/dt + Qout2/2) = (S1/dt + Qout1/2) - Qout1 + (Qin1+Qin2)/2
            
            Includes evaporation losses from lake surface and updates
            storage and water level conditions.
            """

            # ************************************************************
            # ***** LAKE
            # ************************************************************

            inflowM3S = inflow / self.var.DtSec

            # Lake inflow in [m3/s]
            lakeIn = (inflowM3S + self.var.smalllakeInflowOld) * 0.5
            # for Modified Puls Method: (S2/dtime + Qout2/2) = (S1/dtime + Qout1/2) - Qout1 + (Qin1 + Qin2)/2
            # here: (Qin1 + Qin2)/2
            self.var.smallLakeIn = lakeIn * self.var.DtSec / self.var.cellArea  # in [m]

            # evaporation [m3] limited by the lake volume (not below 0) - same as in lakes_reservoirs.py
            # rate as for channels and big lakes (routing_kinematic.py EWRefact): minus the evaporation of the
            # water land cover fraction (openWaterEvap[5]), the small lakes are part of this fraction
            evapRate = np.maximum(0., self.var.lakeEvaFactor * self.var.EWRef - self.var.openWaterEvap[5])
            self.var.smallevapWaterBody = np.minimum(evapRate * self.var.smalllakeArea,
                                                     np.maximum(self.var.smalllakeVolumeM3, 0.))
            self.var.smalllakeVolumeM3 = self.var.smalllakeVolumeM3 - self.var.smallevapWaterBody
            # lakestorage - evaporation from lakes

            self.var.smalllakeInflowOld = inflowM3S
            # Qin2 becomes Qin1 for the next time step

            lakeStorageIndicator = np.maximum(0.0, self.var.smalllakeVolumeM3 / self.var.DtSec - 
                                              0.5 * self.var.smalllakeOutflow + lakeIn)

            # here S1/dtime - Qout1/2 + lakeIn , so that is the right part
            # of the equation above

            self.var.smalllakeOutflow = np.square(-self.var.smalllakeFactor + 
                                                 np.sqrt(self.var.smalllakeFactorSqr + 2 * lakeStorageIndicator))

            QsmallLakeOut = self.var.smalllakeOutflow * self.var.DtSec

            self.var.smalllakeVolumeM3 = (lakeStorageIndicator - self.var.smalllakeOutflow * 0.5) * self.var.DtSec
            # Lake storage

            self.var.smalllakeStorage = (self.var.smalllakeStorage + lakeIn * self.var.DtSec - 
                                         QsmallLakeOut - self.var.smallevapWaterBody)
            # for mass balance, the lake storage is calculated every time step

            self.var.smallevapWaterBody = self.var.smallevapWaterBody / self.var.cellArea  # back to [m]
            self.var.smalllakeLevel = divideValues(self.var.smalllakeVolumeM3, self.var.smalllakeArea)

            return QsmallLakeOut

        # ---------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------



        # ---------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------
        # Small lake and reservoirs

        if checkOption('includeWaterBodies') and returnBool('useSmallLakes'):

            # check years
            # new year: area of the new year (at the start this is done in initial)
            if dateVar['newYear'] and not dateVar['newStart']:
                if returnBool('useResAndLakes') and returnBool('dynamicLakesRes'):
                    year = datetime.datetime(dateVar['currDate'].year, 1, 1)
                else:
                    year = datetime.datetime(int(binding['fixLakesResYear']), 1, 1)
                self.var.smallpart = (readnetcdf2('smallLakesRes', year, useDaily="yearly", 
                                                    value='watershedarea') * 1000 * 1000)
                self.var.smallpart = self.var.smallpart / self.var.cellArea
                self.var.smallpart = np.minimum(1., self.var.smallpart)

                self.var.smalllakeArea = (readnetcdf2('smallLakesRes', year, useDaily="yearly", 
                                                         value='area') * 1000 * 1000)
                # mult with 1,000,000 to convert from km2 to m2
                # new area (and smallpart) -> new lake parameter A and Modified Puls factor
                self.puls_parameters()



            # runoff of the catchment part of the small lakes goes into the lakes [m3]
            inflow = self.var.smallpart * self.var.runoff_m3
            self.var.smallLakeout = dynamic_smalllakes(inflow)  # [m3]
            # runoff of the cell [m3] = small lake outflow + runoff of the rest of the cell
            self.var.runoff_m3 = self.var.smallLakeout + (1 - self.var.smallpart) * self.var.runoff_m3


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
