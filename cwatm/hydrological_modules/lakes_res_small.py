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
    (catchment area < 5000 kmÂ² or lake area < 100 kmÂ²) using the modified Puls
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
    
    References
    ----------
    LISFLOOD manual Annex 3 (Burek et al. 2013)

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    load_initial                         Flag          Settings initLoad holds initial conditions for variables                bool 
    smallpart                            Array         fraction of the cellarea which is a small lake                          --   
    smalllakeArea                        Array         Lake area of small lakes (not part of the main river network)           m2   
    smalllakeDis0                        Array         Starting discharge of small lakes                                       m3/s 
    smalllakeA                           Array         Lake A facor of small lakes                                             --   
    smalllakeFactor                      Array         Internal calculation value for modified Puls approach for small lakes   --   
    smalllakeFactorSqr                   Array         Internal calculation value for modified Puls approach for small lakes   --   
    smalllakeInflowOld                   Array         Inflow of the previous day                                              m3/s 
    smalllakeOutflow                     Array         Outflow from small alkes                                                m3/s 
    smalllakeLevel                       Array         Lake level for small lakes                                              m    
    minsmalllakeVolumeM3                 Array         Storage volume of small lakes                                           m3   
    smallLakedaycorrect                  Array         a water balance correction term for a day because Modified Puld approa  m    
    smallLakeIn                          Array         Inflow into small lakes = lakeIn * time / area                          m    
    smallevapWaterBody                   Array         Evaporation from small lakes                                            m    
    smallLakeout                         Array         small lake outflow but in [m]                                           m    
    smallrunoffDiff                      Number        Not used                                                                --   
    DtSec                                Array         number of seconds per timestep (default = 86400)                        s    
    InvDtSec                             Array         inversere of seconds per timestep (default 1/86400)                     1/s  
    EWRef                                Array         potential evaporation rate from water surface                           m    
    lakeEvaFactor                        Array         a factor which increases evaporation from lake because of wind          --   
    runoff                               Array         Total runoff from surface, interflow and groundwater                    m    
    cellArea                             Array         Area of cell                                                            m2   
    smalllakeVolumeM3                    Array                                                                                 --   
    smalllakeStorage                     Array                                                                                 --   
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
        - Configuring minimum storage constraints if specified
        
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

			

            # lake discharge at outlet to calculate alpha: parameter of channel width, gravity and weir coefficient
            # Lake parameter A (suggested  value equal to outflow width in [m])
            # multiplied with the calibration parameter LakeMultiplier
            testRunoff = "averageRunoff" in binding
            if testRunoff:
                self.var.smalllakeDis0 = (loadmap('averageRunoff') * self.var.smallpart * 
                                          self.var.cellArea * self.var.InvDtSec)
            else:
                self.var.smalllakeDis0 = loadmap('smallwaterBodyDis')
            self.var.smalllakeDis0 = np.maximum(self.var.smalllakeDis0, 0.01)
            chanwidth = 7.1 * np.power(self.var.smalllakeDis0, 0.539)
            self.var.smalllakeA = loadmap('lakeAFactor') * 0.612 * 2 / 3 * chanwidth * (2 * 9.81) ** 0.5
            self.var.smalllakeFactor = self.var.smalllakeArea / (self.var.DtSec * np.sqrt(self.var.smalllakeA))

            self.var.smalllakeFactorSqr = np.square(self.var.smalllakeFactor)
            # for faster calculation inside dynamic section

            # inflow in m3/s estimate
            self.var.smalllakeInflowOld = self.var.load_initial("smalllakeInflow", self.var.smalllakeDis0)
            
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
            self.var.smalllakeStorage = self.var.smalllakeVolumeM3.copy()

            testStorage = "minStorage" in binding
            if testStorage:
                self.var.minsmalllakeVolumeM3 = loadmap('minStorage')
            else:
                self.var.minsmalllakeVolumeM3 = 9.e99


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
                Inflow to small lakes [mÂ³] per time step
                
            Returns
            -------
            numpy.ndarray
                Lake outflow [mÂ³] per time step
                
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

            # just for day to day waterbalance -> get X as difference
            # lakeIn = in + X ->  (in + old) * 0.5 = in + X  ->   in + old = 2in + 2X -> in - 2in +old = 2x
            # -> (old - in) * 0.5 = X
            self.var.smallLakedaycorrect = (0.5 * (self.var.smalllakeInflowOld * self.var.DtSec - inflow) / 
                                           self.var.cellArea)

            # Lake inflow in [m3/s]
            lakeIn = (inflowM3S + self.var.smalllakeInflowOld) * 0.5
            # for Modified Puls Method: (S2/dtime + Qout2/2) = (S1/dtime + Qout1/2) - Qout1 + (Qin1 + Qin2)/2
            # here: (Qin1 + Qin2)/2
            self.var.smallLakeIn = lakeIn * self.var.DtSec / self.var.cellArea  # in [m]

            self.var.smallevapWaterBody = self.var.lakeEvaFactor * self.var.EWRef * self.var.smalllakeArea

            self.var.smallevapWaterBody = np.where((self.var.smalllakeVolumeM3 - self.var.smallevapWaterBody) > 0., 
                                                   self.var.smallevapWaterBody, self.var.smalllakeVolumeM3)
            self.var.smallevapWaterBody = np.maximum(0., self.var.smallevapWaterBody)
            self.var.smalllakeVolumeM3 = self.var.smalllakeVolumeM3 - self.var.smallevapWaterBody
            # lakestorage - evaporation from lakes

            self.var.smalllakeInflowOld = inflowM3S.copy()
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

            # if dateVar['curr'] >= dateVar['intSpin']:
            #   self.var.minsmalllakeStorageM3 = np.where(self.var.smalllakeStorageM3 < 
            #                                             self.var.minsmalllakeStorageM3,
            #                                             self.var.smalllakeStorageM3,
            #                                             self.var.minsmalllakeStorageM3)

            self.var.smallevapWaterBody = self.var.smallevapWaterBody / self.var.cellArea  # back to [m]
            self.var.smalllakeLevel = divideValues(self.var.smalllakeVolumeM3, self.var.smalllakeArea)

            return QsmallLakeOut

        # ---------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------



        # ---------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------
        # Small lake and reservoirs

        if checkOption('includeWaterBodies') and returnBool('useSmallLakes'):
            if checkOption('calcWaterBalance'):
                runoffold = self.var.runoff.copy()

            # check years
            if dateVar['newStart'] or dateVar['newYear']:
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



            # ----------
            # inflow lakes
            # 1.  dis = upstream1(self.var.downstruct_LR, self.var.discharge)   # from river upstream
            # 2.  runoff = npareatotal(self.var.waterBodyID, self.var.waterBodyID)  # from cell itself
            # 3.                  # outflow from upstream lakes

            # ----------

            # runoff to the lake as a part of the cell basin
            inflow = self.var.smallpart * self.var.runoff * self.var.cellArea  # inflow in m3
            self.var.smallLakeout = dynamic_smalllakes(inflow) / self.var.cellArea  # back to [m]
            # back to [m]  # with and without in m3
            self.var.runoff = self.var.smallLakeout + (1 - self.var.smallpart) * self.var.runoff



            return

        else:
            self.var.smallrunoffDiff = 0


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
