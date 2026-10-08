# -------------------------------------------------------------------------
# -------------------------------------------------------------------------
# Name:        Wastewaster Treatment
# Purpose: Wastewater treatment and return flow module for water recycling processes.
# Simulates wastewater generation, treatment efficiency, and return flow dynamics.
# Handles treated wastewater discharge and water quality improvement processes.
#
# Author:      DF
# Created:     27/10/2021
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
from cwatm.management_modules.globals import *


class waterdemand_wastewater(object):
    """
    Wastewater treatment and return flow module for water recycling processes.
    
    This class simulates wastewater generation, treatment efficiency, and return flow
    dynamics. It handles treated wastewater discharge, water quality improvement processes,
    and supports many-to-many relations between wastewater treatment plants (WWTP) and
    reservoirs. The module includes urban leakage, evaporation from treatment facilities,
    and two types of wastewater export (untreated and treated).
    
    The module processes domestic and industrial wastewater through collection areas,
    applies treatment with configurable parameters (volume, treatment time, efficiency),
    and manages discharge to overflow points or reuse via distribution reservoirs.
    
    Parameters
    ----------
    Required inputs:
        - wwtID : Wastewater treatment plant identifiers
        - wwtVol : Daily treatment volume capacity
        - wwtYear : Year of establishment
        - wwtTime : Treatment duration in days (default: 2 days, range: 1-3 days)
        - wwtOverflow : Overflow/discharge point locations
        - wwt_ColArea : Effluent collection area definitions
    
    Optional inputs:
        - wwtColShare : Collection efficiency ratio (0-1)
        - wwtToResManagement : Reservoir management strategy (-1, 0-1)
        - urbanleak : Urban leakage coefficient
    
    Attributes
    ----------
    var : object
        Model variables container from parent model
    model : object
        Parent CWatM model instance
    
    Notes
    -----
    Treatment levels: 1=primary, 2=secondary, 3=tertiary
    Management options: -1=discharge only, 0=send to reservoir, 0-1=export fraction

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    wwt_def                              Flag                                                                                  --   
    wastewater_to_reservoirs             Array                                                                                 --   
    compress_LR                          Array         boolean map as mask map for compressing lake/reservoir                  --   
    waterBodyOut                         Array         biggest outlet (biggest accumulation of ldd network) of a waterbody     --   
    decompress_LR                        Array         boolean map as mask map for decompressing lake/reservoir                --   
    waterBodyOutC                        Array         compressed map biggest outlet of each lake/reservoir                    --   
    resYear                              Array         Settings waterBodyYear, with first operating year of reservoirs         map  
    resVolume                            Array         Reservoir volume                                                        m3   
    EWRef                                Array         potential evaporation rate from water surface                           m    
    wwtUrbanLeakage                      Array                                                                                 --   
    wwtColArea                           Array                                                                                 --   
    urbanleak                            Array                                                                                 --   
    wwtID                                Array                                                                                 --   
    compress_WWT                         Array                                                                                 --   
    decompress_WWT                       Array                                                                                 --   
    wwtC                                 Array                                                                                 --   
    act_bigLakeResAbst_UNRestricted      Array                                                                                 --   
    act_bigLakeResAbst_Restricted        Array                                                                                 --   
    wwtOverflow                          Array                                                                                 --   
    wwtStorage                           Array                                                                                 --   
    wwtColShare                          Array                                                                                 --   
    wwtSewerCollectedC                   Array                                                                                 --   
    wwtSewerTreatedC                     Array                                                                                 --   
    wwtExportedTreatedC                  Array                                                                                 --   
    wwtSewerToTreatmentC                 Array                                                                                 --   
    wwtSewerOverflowC                    Array                                                                                 --   
    wwtSewerResOverflowC                 Array                                                                                 --   
    wwtTreatedOverflowC                  Array                                                                                 --   
    wwtSentToResC                        Array                                                                                 --   
    wwtSewerCollection                   Array                                                                                 --   
    wwtOverflowOut                       Array                                                                                 --   
    wwtEvapC                             Array                                                                                 --   
    wwtSewerCollected                    Array                                                                                 --   
    wwtExportedCollected                 Array                                                                                 --   
    wwtSewerTreated                      Array                                                                                 --   
    wwtExportedTreated                   Array                                                                                 --   
    wwtSewerToTreatment                  Array                                                                                 --   
    wwtSewerExported                     Array                                                                                 --   
    wwtSewerOverflow                     Array                                                                                 --   
    wwtSentToRes                         Array                                                                                 --   
    wwtSewerResOverflow                  Array                                                                                 --   
    wwtTreatedOverflow                   Array                                                                                 --   
    wwtEvap                              Array                                                                                 --   
    wwtInTreatment                       Array                                                                                 --   
    wwtIdsOrdered                        List                                                                                  --   
    wwtVolC                              Array                                                                                 --   
    wwtTimeC                             Array                                                                                 --   
    toResManageC                         Array                                                                                 --   
    minHRTC                              Array                                                                                 --   
    maskDomesticCollection               Array                                                                                 --   
    maskIndustryCollection               Array                                                                                 --   
    extensive                            Flag                                                                                  --   
    noPools_extensive                    Array                                                                                 --   
    poolVolume_extensive                 Array                                                                                 --   
    wwtSurfaceAreaC                      Array                                                                                 --   
    extensive_counter                    Array                                                                                 --   
    wwtResIDTemp_compress                Array                                                                                 --   
    wwtResIDC                            Array                                                                                 --   
    wwtResTypC                           Array                                                                                 --   
    wwtResYearC                          Array                                                                                 --   
    wwtSentToResC_LR                     Array                                                                                 --   
    wwtOverflowOutM                      Array                                                                                 --   
    cellArea                             Array         Area of cell                                                            m2   
    includeWastewater                    Flag                                                                                  --   
    waterBodyTyp_unchanged               Array                                                                                 --   
    lakeVolumeM3C                        Array         compressed map of lake volume                                           m3   
    lakeStorageC                         Array                                                                                 --   
    reservoirStorageM3C                  Array                                                                                 --   
    lakeResStorageC                      Array                                                                                 --   
    lakeResStorage                       Array                                                                                 --   
    wwtEffluentsGenerated                Array                                                                                 --   
    wwtSewerCollection_domestic          Array                                                                                 --   
    wwtSewerCollection_industry          Array                                                                                 --   
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize the wastewater treatment module.
        
        Parameters
        ----------
        model : object
            The CWatM model instance containing variables and methods
        """
        self.var = model.var
        self.model = model
	
    def initial(self):
        """
        Initialize wastewater treatment facilities and variables.
        
        Sets up wastewater treatment plant locations, collection areas, storage systems,
        and output variables. Configures treatment facility parameters including daily
        volumes, collection shares, and urban leakage coefficients. Initializes big maps
        for tracking wastewater flows, treatment processes, and discharge outputs.
        """
        if self.var.includeWastewater:
            ## Setup wastewater treatment facilities
            # load inputs
            self.var.wwtID = loadmap('wwtID').astype(np.int64)
            self.var.compress_WWT = self.var.wwtID > 0
            self.var.decompress_WWT = np.nonzero(self.var.compress_WWT)
            self.var.wwtC =  np.compress(self.var.compress_WWT, self.var.wwtID)
                
            # Create maps for resLake irrigation/waster use
            if checkOption('includeWaterBodies'):
                self.var.act_bigLakeResAbst_UNRestricted = globals.inZero.copy()        
                self.var.act_bigLakeResAbst_Restricted = globals.inZero.copy()            
            
            # share to collect urban leakage
            self.var.urbanleak = loadmap('urbanleak')

            # create outlet for overflow
            self.var.wwtOverflow = loadmap('wwtOverflow').astype(np.int64) 

            
            # Initiate WWTP Storage
            self.var.wwtStorage = {}
            
            ## Setup wastewater treatment facilities
            # load collection area
            self.var.wwtColArea = loadmap('wwtColArea').astype(np.int64)
            
            # load collection share - default to 100% collected water
            self.var.wwtColShare = globals.inZero.copy()
            self.var.wwtColShare += 1.
            if 'wwtColShare' in binding:
               self.var.wwtColShare = loadmap('wwtColShare')
            # create variables for output -> collected, treatedWater, output, overflow
            
            ## Create variables: wwtSewerCollection = wwtSewerCollectedC + wwtSewerOverflowC =  wwtSewerTreatedC + wwtSewerInTreatmentC + wwtSewerOverflowC 
            # wwtSewerCollection = act_SewerGeneration * wwtColShare 
            self.var.wwtSewerCollectedC = np.compress(self.var.compress_WWT, globals.inZero.copy())
            self.var.wwtSewerTreatedC = np.compress(self.var.compress_WWT, globals.inZero.copy())
            self.var.wwtExportedTreatedC = np.compress(self.var.compress_WWT, globals.inZero.copy())
            self.var.wwtSewerToTreatmentC = np.compress(self.var.compress_WWT, globals.inZero.copy())
            self.var.wwtSewerOverflowC = np.compress(self.var.compress_WWT, globals.inZero.copy())

            self.var.wwtSewerResOverflowC = np.compress(self.var.compress_WWT, globals.inZero.copy())
            self.var.wwtTreatedOverflowC = np.compress(self.var.compress_WWT, globals.inZero.copy())
            if checkOption('includeWaterBodies'):
                self.var.wwtSentToResC = np.compress(self.var.compress_LR, globals.inZero.copy())
            self.var.wwtUrbanLeakage = globals.inZero.copy()
            self.var.wwtEffluentsGenerated = globals.inZero.copy()
            self.var.wwtSewerCollection =  globals.inZero.copy()
            self.var.wwtOverflowOut =  globals.inZero.copy()
            self.var.wwtEvapC = np.compress(self.var.compress_WWT, globals.inZero.copy())
            
            # Initiates bigmaps 
            self.var.wwtSewerCollected = globals.inZero.copy()
            self.var.wwtExportedCollected = globals.inZero.copy()
            self.var.wwtSewerTreated = globals.inZero.copy()   
            self.var.wwtExportedTreated = globals.inZero.copy()            
            self.var.wwtSewerToTreatment = globals.inZero.copy()
            self.var.wwtSewerExported = globals.inZero.copy()
            self.var.wwtSewerOverflow = globals.inZero.copy()
            self.var.wwtSentToRes = globals.inZero.copy()
            self.var.wwtSewerResOverflow = globals.inZero.copy()  
            self.var.wwtTreatedOverflow = globals.inZero.copy()
            self.var.wwtEvap = globals.inZero.copy()
            self.var.wwtInTreatment =  globals.inZero.copy()
            # get relevant reservoirs ids and their fill status. create an output status to save wwtSentToRes
            
            # to dynamic
            # every year - if year < established - set all collection area to zero - e.g., no collection. 
            # collect all water from each collection area; check daily limit & calculate overflow;
            # move storage, add to treatment, release water to output
            
    
    def dynamic_init(self):
        """
        Initialize annual wastewater treatment plant configurations and storage systems.
        
        Updates wastewater treatment plant definitions from Excel settings for the current
        simulation year. Filters facilities by operational years, creates ordered processing
        lists, and sets up annual treatment parameters including volumes, treatment times,
        and export shares. Configures extensive treatment systems with multiple pools and
        calculates surface areas for evaporation processes.
        
        Notes
        -----
        Treatment plant definitions loaded from Excel include:
        - Daily treatment capacity (Volume in mÂ³/day)
        - Treatment duration (Days, typically 1-3)
        - Treatment level (1=primary, 2=secondary, 3=tertiary)
        - Export share (fraction of outflows exported from basin)
        - Wastewater sources (Domestic and/or Industrial boolean flags)
        - Minimum hydraulic retention time (min_HRT in days)
        
        The method handles technology changes by preserving existing storage when
        treatment parameters change (e.g., from 30 to 20 days treatment time).
        All stored water is allocated to the final treatment pool for release.
        
        Extensive systems (treatment time >= 2 days) use multiple treatment pools
        (default: 3 pools) to simulate realistic treatment processes and timing.
        
        Sets up the following annual arrays:
        - wwtVolC : Daily treatment volumes [mÂ³/day]
        - wwtTimeC : Treatment duration [days]
        - toResManageC : Reservoir management strategy [-1 to 1]
        - minHRTC : Minimum hydraulic retention times [days]
        - wwtSurfaceAreaC : Treatment facility surface areas [mÂ²]
        
        Collection masks are updated for domestic and industrial wastewater
        sources based on facility-specific configuration flags.
        """
        
        # filter wwtC by year and create ordered list for iteration
        year = dateVar['currDate'].year
        
        # get ordered wwt IDS for iteration
        wwtIds = self.var.wwtC.copy()
        resKeys = [k  for  k in self.var.wastewater_to_reservoirs.keys()]
        self.var.wwtIdsOrdered = resKeys + (wwtIds[np.in1d(wwtIds, resKeys, invert = True)].tolist())
        annual_mask = []
        annual_wwtpIdx = []
        for wwtid in self.var.wwtIdsOrdered:
            tmp = self.var.wwt_def[wwtid]
            for r in range(tmp.shape[0]):
                if tmp[r][0] <= year:
                    if np.isnan(tmp[r][1]) or tmp[r][1] >= year:
                        annual_mask.append(True)
                        annual_wwtpIdx.append(r)
                        # if found the valid instance of WWTP ID - break and don't continute looking for another one
                        break
                elif tmp.shape[0] == r + 1:
                    annual_mask.append(False)
                    annual_wwtpIdx.append(np.nan)
        
        self.var.wwtIdsOrdered = np.array(self.var.wwtIdsOrdered)[annual_mask].tolist()
        annual_wwtpIdx = np.array(annual_wwtpIdx)[annual_mask]
        
        ## Create annual inputs
        
        # Volume, treatementTime, ExportAndMangement, minimum Hydrological Retention Time

        self.var.wwtVolC = []
        self.var.wwtTimeC = []
        self.var.toResManageC = []
        self.var.minHRTC = []
        
        # initiate sector collection masks
        self.var.maskDomesticCollection = 1 + globals.inZero.copy()
        self.var.maskIndustryCollection = 1 + globals.inZero.copy()
        
        for wwtid in self.var.wwtIdsOrdered:

            i = np.in1d(self.var.wwtIdsOrdered, wwtid)
            self.var.wwtVolC.append(self.var.wwt_def[wwtid][int(annual_wwtpIdx[i])][2])
            self.var.wwtTimeC.append(self.var.wwt_def[wwtid][int(annual_wwtpIdx[i])][3]) 
            self.var.minHRTC.append(np.maximum(self.var.wwt_def[wwtid][int(annual_wwtpIdx[i])][8], 0.001))
            # toResManageC control wwt2reservoir operations:
            #   0: attempt to send all to reservior
            #   1: export all treated wastewater
            # 0-1: export the fraction and attempt sending the rest to reservoir
            #  -1: only send to overflow point as discharge (do not send to reservoir)
            
            mng = self.var.wwt_def[wwtid][int(annual_wwtpIdx[i])][5]
            self.var.toResManageC.append(float(np.where(np.isnan(mng), 0., mng)))
            # sector collection masks
            self.var.maskDomesticCollection = np.where(self.var.wwtColArea == wwtid, self.var.wwt_def[wwtid][int(annual_wwtpIdx[i])][6], self.var.maskDomesticCollection)
            self.var.maskIndustryCollection = np.where(self.var.wwtColArea == wwtid, self.var.wwt_def[wwtid][int(annual_wwtpIdx[i])][7], self.var.maskIndustryCollection)
           
        self.var.wwtVolC = np.array(self.var.wwtVolC)
        self.var.wwtTimeC = np.array(self.var.wwtTimeC)
        self.var.minHRTC = np.array(self.var.minHRTC)
        self.var.toResManageC = np.array(self.var.toResManageC)
        self.var.wwtIdsOrdered = np.array(self.var.wwtIdsOrdered)
       
        
        ### Extensive WWTP ####
        # Identify extensive systems - if timeLag >= 2
        self.var.extensive = self.var.wwtTimeC >= 2
        # number of days to fill a treatement pool in extensive systems - default no. of pools: 3
        self.var.noPools_extensive = 3
        
        daysToFill_extensive = self.var.wwtTimeC / self.var.noPools_extensive
        # Volume for an extnesive treatement pool in extensive systems
        self.var.poolVolume_extensive = self.var.wwtVolC * daysToFill_extensive
        
        # Calculate surface area of treatment pools for evaporation
        self.var.wwtSurfaceAreaC = np.where(self.var.extensive, self.var.poolVolume_extensive, self.var.wwtVolC)/ np.where(self.var.wwtIdsOrdered  > 0, 6.0, 1.0)
        
        #### Build WWTP Storage ####
        
        # If there is prior storage (e.g., start of model) - save a copy and re-allocate; storage start as empty array
        # It aims to handle cases where technology chnages - e.g., from 30 days to 20 days treatment, or from 2 days to 1 day.
        # In that case all water are being allocated to the last treatment pool, so they will be released next (this may result in a "big" sudden release of treated wastewater).
        
        priorStorage = False
        if not len(self.var.wwtStorage) == 0:
            priorStorage = True
            wwtStroage_last = self.var.wwtStorage.copy()
            
        # create storage variable
        self.var.wwtStorage = {}
        
        
        # extensive wastewater treatement facilites have less pools than days
        timeForStorage = np.where(self.var.extensive,  self.var.noPools_extensive, self.var.wwtTimeC)
        for i in range(self.var.wwtIdsOrdered.shape[0]):
            wwtid = self.var.wwtIdsOrdered[i]
            self.var.wwtStorage[wwtid] = [0] * int(timeForStorage[i])
            if priorStorage:
                if np.in1d(wwtid, wwtStroage_last.keys()):
                    l_new = len(self.var.wwtStorage[wwtid])
                    l_old = len(wwtStroage_last[wwtid])
                    if l_new == l_old:
                        self.var.wwtStorage[wwtid] = wwtStroage_last[wwtid]
                    else:
                        self.var.wwtStorage[wwtid] = (self.var.wwtStorage[wwtid] + 1) * (1 / l_new) * sum(wwtStroage_last[wwtid])
            
            
        self.var.extensive_counter = self.var.wwtStorage.copy()
        #print(self.var.wwtStorage)
        #print(np.array(self.var.wwtStorage))
        #print(np.nansum(np.array(self.var.wwtStorage), axis = 1))
        
    def dynamic(self):
        """
        Execute daily wastewater treatment operations for all active facilities.
        
        Performs the main processing cycle for each time step, handling sewer collection,
        treatment processes, storage dynamics, evaporation losses, and discharge operations.
        Processes wastewater through collection areas, applies treatment with facility-specific
        parameters, and manages discharge to overflow points or distribution reservoirs.
        
        Notes
        -----
        Daily processing sequence:
        1. Initialize annual configurations if new year/start
        2. Calculate total sewer collection from domestic and industrial sources
        3. Handle export of untreated wastewater from areas without facilities
        4. Process each treatment facility in ordered sequence:
           - Check daily capacity limits and calculate overflow
           - Apply hydraulic retention time constraints
           - Calculate evaporation losses from treatment pools
           - Update storage arrays (extensive vs standard systems)
           - Release treated water based on management strategy
           - Allocate water to reservoirs or overflow discharge points
        
        Storage management:
        - Standard systems: Simple queue with daily advancement
        - Extensive systems: Multiple pools with residence time tracking
        - Evaporation calculated from surface area and reference ET
        
        Discharge management strategies (toResManageC):
        - -1: Discharge all treated water to overflow points
        - 0: Send all treated water to reservoirs (if available)
        - 0-1: Export fraction, send remainder to reservoirs
        - 1: Export all treated wastewater
        
        Water allocation to reservoirs uses iterative proportional allocation
        based on available capacity, with overflow handling for excess volumes.
        
        Updates all output variables including collected volumes, treated volumes,
        overflow discharges, reservoir transfers, and evaporation losses.
        """
        if dateVar['newStart'] or dateVar['newYear']:
            self.dynamic_init()
        
        # set daily overflow to zero - prevent double counting 
        ### A PROBLEM OCCURS: in the result it seems that thse two variables are zero at the first day of each year - is it possible that the model initializes every year?
        overflow_temp =  globals.inZero.copy()  
        self.var.wwtSentToRes = globals.inZero.copy()

        # Calculate total sewer collection
        self.var.wwtSewerCollection = (self.var.wwtSewerCollection_domestic  * self.var.maskDomesticCollection + self.var.wwtSewerCollection_industry  * self.var.maskIndustryCollection) * self.var.wwtColShare + self.var.wwtUrbanLeakage
        
        # identify a list of collection areas with wastewater treatment facilities outside of the mask
        # use wwtC instead of wwtIdsOrdered - so WWTP that are not present due to time constraints would not cause export.
        collectWtr2Export = np.unique(self.var.wwtColArea)[np.invert(np.in1d(np.unique(self.var.wwtColArea), self.var.wwtC))]
       
        collectWtr2Export = np.delete(collectWtr2Export, np.where(collectWtr2Export == 0))
        
        # mask for water2export collection
        collection2ExportAreaMask = np.in1d(self.var.wwtColArea, collectWtr2Export) * 1
        
        # document collection for export
        self.var.wwtExportedCollected = collection2ExportAreaMask * self.var.wwtSewerCollection * self.var.cellArea
        
        self.var.wwtInTreatment =  globals.inZero.copy()
        
        for wwt_id in self.var.wwtIdsOrdered:
            idIndex = np.where(self.var.wwtIdsOrdered == wwt_id)[0].item()
            # check year established
            
            
            simulatedYear =  globals.dateVar['currDate'].year
            
            #if self.var.wwtYearC[idIndex] > simulatedYear:
            #    continue
            
            # if year established <= simulated year:
            collectionAreaMask = np.where(self.var.wwtColArea == wwt_id, 1, 0)
            # Check WWTP sectoral sewer collection preferences
            
            # sum sewer collection per facility [m3]
            self.var.wwtSewerCollectedC[idIndex] = np.nansum(collectionAreaMask * (self.var.wwtSewerCollection) * self.var.cellArea)

            # calculate max water allowed
            max_collected_idIndex = self.var.wwtVolC[idIndex] / self.var.minHRTC[idIndex] 
          
            
            # calculate to overflow
            toOverflow = np.maximum(self.var.wwtSewerCollectedC[idIndex] - max_collected_idIndex, 0.)
            
            # calculate collected
            wwtSewerCollected_idIndex2 = self.var.wwtSewerCollectedC[idIndex] - toOverflow
            
            # calculate HRT - for water quality calculations
            hrt_idIndex = np.minimum(self.var.wwtVolC[idIndex] / wwtSewerCollected_idIndex2, 1.)
            
           
            # calculate overflow - if summed volume excceds daily capacity [m3]
            self.var.wwtSewerOverflowC[idIndex] = toOverflow

            # calculate toTreatment [m3]
            self.var.wwtSewerToTreatmentC[idIndex] = np.maximum(self.var.wwtSewerCollectedC[idIndex] - self.var.wwtSewerOverflowC[idIndex], 0.)
            # calculate evaporation from treatment facilities - for daily
            wwtEvapPool = self.var.wwtSurfaceAreaC[idIndex] * np.compress(self.var.compress_WWT, self.var.EWRef)[idIndex]
            wwtEvapArray = wwtEvapPool * self.var.wwtTimeC[idIndex]
            
            # restrict pool evaporation by sewer volume
            wwtEvapArray = np.minimum(self.var.wwtStorage[wwt_id], wwtEvapArray)
            
            # sum evaporation
            self.var.wwtEvapC[idIndex] = np.nansum(wwtEvapArray)
            
            # update storage with evaporation
            self.var.wwtStorage[wwt_id] -= wwtEvapArray
            
            self.var.wwtSewerTreatedC[idIndex] = 0
            
            # handle storage 
            if self.var.extensive[idIndex]:
      
                #print(idIndex)
                #print("last Storage Ext" + str(np.round(self.var.wwtStorage[idIndex][-1], 0)))
                # extensive
                # calculate remainStorage in pool 0
                remainStorage0 = np.maximum(self.var.poolVolume_extensive[idIndex] - self.var.wwtStorage[wwt_id][0], 0.)
                
                # calculate volume to add to storage0 and add to storage1
                addToStorage0 = np.minimum(remainStorage0, self.var.wwtSewerToTreatmentC[idIndex])
                addToStorage1 =  self.var.wwtSewerToTreatmentC[idIndex] - addToStorage0

                # add to storage
                self.var.wwtStorage[wwt_id][0] += addToStorage0
                
                # if reservoir routing is off
                if addToStorage1 > 0:
                    #last storage to TreatedC [m3] - if all treatment pools are with water and more capacity is required
                    self.var.wwtSewerTreatedC[idIndex] = self.var.wwtStorage[wwt_id][-1]
                    
                    # update storage - each element i to i+1; eliminate last [m3] 
                    self.var.wwtStorage[wwt_id][1:] = self.var.wwtStorage[wwt_id][0:-1]
                    # move counter values respecitvely
                    self.var.extensive_counter[wwt_id][1:] = self.var.extensive_counter[wwt_id][0:-1]
                    
                    # update storage - element 0 is new collected [m3]
                    self.var.wwtStorage[wwt_id][0] = addToStorage1

                cond = self.var.extensive_counter[wwt_id] >= (self.var.wwtTimeC[idIndex] - 1)
  
                # empty pool if time in active pool exceeds treatment time
                if cond.any():
                    
                    self.var.wwtSewerTreatedC[idIndex] +=  np.nansum(self.var.wwtStorage[wwt_id][cond])

                    # update storage
                    self.var.wwtStorage[wwt_id] = np.where(cond, 0., self.var.wwtStorage[wwt_id])

                    #self.var.extensive_counter[wwt_id] += (cond * 1)
                # active treatement pools are those which are not receieving water inflows. Ther are being emptied (e.g., water are used after the defined treatment days)
                # count days with positive water volume in active treatement pools
                cond = self.var.wwtStorage[wwt_id][1:] > 0
      
                if cond.any():
                    
                    self.var.extensive_counter[wwt_id][1:] += (cond * 1)
                    self.var.extensive_counter[wwt_id][1:] = np.where(np.logical_not(cond), 0, self.var.extensive_counter[wwt_id][1:])

                self.var.wwtInTreatment[self.var.wwtID == wwt_id] = np.nansum(self.var.wwtStorage[wwt_id])  
            else:
                #last storage to TreatedC [m3]         
                self.var.wwtSewerTreatedC[idIndex] = self.var.wwtStorage[wwt_id][-1]
            
                # update storage - each element i to i+1; eliminate last [m3] 
                self.var.wwtStorage[wwt_id][1:] = self.var.wwtStorage[wwt_id][0:-1]

                # update storage - element 0 is new collected [m3]
                self.var.wwtStorage[wwt_id][0] = self.var.wwtSewerToTreatmentC[idIndex]
            sto_0 = np.nansum(self.var.wwtInTreatment).copy()
            
            self.var.wwtInTreatment[self.var.wwtID == wwt_id] = np.nansum(self.var.wwtStorage[wwt_id])  
            # update overflow output map [m3]
            overflowMask = np.where(self.var.wwtOverflow == wwt_id, 1, 0)
            overflow_temp += overflowMask * self.var.wwtSewerOverflowC[idIndex]

            # toResManageC control wwt2reservoir operations:
            '''
                -1: only send to overflow point as discharge (do not send to reservoir)
                0 -1: between zero to one gives the fraction of treated wastewater to export; the rest are sent to reservoir (if exists)
                An extreme case of 0 tries sending all treated wastewater to the reservoir (if exists), it send it to overflow point when it is full 
            
            '''
            toResManage = self.var.toResManageC[idIndex]
                
            dischargeTreatedWaterBool = False
            if toResManage == -1 or  not checkOption('includeWaterBodies'):
                dischargeTreatedWaterBool = True
            
            
            if (toResManage > 1) | (toResManage < 0 and toResManage != -1):
                msg = "Error: unexpected value in 'wwtToResManagement'"
                raise CWATMFileError(msg)
            
            
            if dischargeTreatedWaterBool:
                
                # treated water are being discharged to overflow point
                overflow_temp += overflowMask * self.var.wwtSewerTreatedC[idIndex]
                self.var.wwtTreatedOverflowC[idIndex] = self.var.wwtSewerTreatedC[idIndex]
            
            
            elif np.invert(wwt_id in self.var.wastewater_to_reservoirs.keys()):
                # account for exported treated water 
                self.var.wwtExportedTreatedC[idIndex] = self.var.wwtSewerTreatedC[idIndex] * toResManage
                self.var.wwtSewerTreatedC[idIndex] -= self.var.wwtExportedTreatedC[idIndex]

                # treated water are being discharged to overflow point
                overflow_temp += overflowMask * self.var.wwtSewerTreatedC[idIndex]
                self.var.wwtTreatedOverflowC[idIndex] = self.var.wwtSewerTreatedC[idIndex]
                self.var.wwtSewerTreatedC[idIndex] -= self.var.wwtTreatedOverflowC[idIndex]
               

                
            else:
                # treated water are being sent to one or more reservoirs. If one reservoir, all water sent until it is full, access water are added to OverflowOut
                # Id multiple reservoirs - water are split proportionally to the reservoirs' current capacity to collect water (e.g., 1 - storage/volume). Access water are sent to OverflowOut.
                
                    
                # account for exported treated water 
                self.var.wwtExportedTreatedC[idIndex] = self.var.wwtSewerTreatedC[idIndex] * toResManage
                self.var.wwtSewerTreatedC[idIndex] -= self.var.wwtExportedTreatedC[idIndex]
                    
                    
                srch =  np.in1d(self.var.wastewater_to_reservoirs[wwt_id], self.var.waterBodyOut)
                self.var.wwtResIDTemp_compress = np.in1d(self.var.waterBodyOut, np.compress(srch, self.var.wastewater_to_reservoirs[wwt_id]))
                    
                self.var.wwtResIDC = np.compress(self.var.wwtResIDTemp_compress, self.var.waterBodyOut)
                self.var.wwtResTypC = np.compress(self.var.wwtResIDTemp_compress, self.var.waterBodyTyp_unchanged)
                self.var.wwtResYearC = np.compress(self.var.wwtResIDTemp_compress, self.var.resYear)
                    
                # do not alow reservoir use if their type ids is zero (e.g., wetland) or id they have not been yet established
                self.var.wwtResIDC =  np.where(self.var.wwtResTypC == 0, 0,  np.where(self.var.wwtResYearC > simulatedYear, 0,  self.var.wwtResIDC))
                    
                # calculate allocation weights
                resVolumeC = np.compress(self.var.wwtResIDTemp_compress, self.var.resVolume)
                    
                resVolumeLeftC = np.minimum(np.maximum(resVolumeC - np.compress(self.var.wwtResIDTemp_compress, self.var.lakeResStorage), 0.), resVolumeC)
                
                treatedSewer = self.var.wwtSewerTreatedC[idIndex]
                #### Iterate to allocate as much water as possible to res ####
                wwtResindex = np.in1d(self.var.waterBodyOutC, self.var.wastewater_to_reservoirs[wwt_id])
                maxIter = 50
                iterCounter = 0
                sendToRes = 0
                while treatedSewer > 1e-10 and np.nansum(resVolumeLeftC) > 1e-10 and iterCounter <= maxIter:
                    resAllocWeights = divideValues(resVolumeLeftC, npareatotal(resVolumeLeftC, self.var.wwtResIDC > 0)) * (self.var.wwtResIDC > 0)
                
                    # Do not allow all reservoir to be zero - split wastewater proportionally to total storage
                    if np.nansum(resAllocWeights) == 0:
                        resAllocWeights = divideValues(resVolumeC, npareatotal(resVolumeC, self.var.wwtResIDC > 0)) * (self.var.wwtResIDC > 0)
                        
                    tmpSendToRes = np.minimum(treatedSewer * resAllocWeights, resVolumeLeftC)
                    sendToRes += tmpSendToRes
                    resVolumeLeftC -= tmpSendToRes
                    treatedSewer -= np.nansum(tmpSendToRes)
                    iterCounter +=1
                ###
                
                
                self.var.wwtSentToResC[wwtResindex] = sendToRes
                # split water and calcualte overflow in reservoirs - continute here ! error! - something doesnot work with res overflow - it is not written to the layer
                # see lines 286 -295 for clues

                # below it was originaly assignes (=); I suspect it overwritten
                self.var.wwtSewerResOverflowC[idIndex] = self.var.wwtSewerTreatedC[idIndex] - np.nansum(sendToRes)

                # update overflow
                    
                overflow_temp += overflowMask * np.nansum(self.var.wwtSewerResOverflowC[idIndex])
      
                wwtSentToRes = np.where(np.in1d(np.compress(self.var.compress_LR, self.var.waterBodyOut), self.var.wwtResIDC), self.var.wwtSentToResC, 0.)
                addToSend = globals.inZero.copy()
                np.put(addToSend, self.var.decompress_LR, wwtSentToRes)

                
                self.var.wwtSentToRes += addToSend 

                # get relevant reservoirs ids and their fill status. create an output status to save wwtSentToRes
                # split treated between reservoirs
                # check for access water - if no allocate, if yes - update: OverflowOut, SewerResOverflowC
                # the wwtSentToRes should be used in the lakes_reservoir.py

        self.var.wwtOverflowOut = overflow_temp        
        # Total overflow output map [m3 to M]
        #self.var.wwtOverflowOutM = self.var.wwtOverflowOut / self.var.cellArea
        
        # decompress results [m3]
        np.put(self.var.wwtSewerCollected, self.var.decompress_WWT, self.var.wwtSewerCollectedC)
        np.put(self.var.wwtSewerTreated, self.var.decompress_WWT, self.var.wwtSewerTreatedC)     
        np.put(self.var.wwtSewerToTreatment, self.var.decompress_WWT, self.var.wwtSewerToTreatmentC)
        np.put(self.var.wwtSewerOverflow, self.var.decompress_WWT, self.var.wwtSewerOverflowC) 
        #np.put(self.var.wwtSewerResOverflow, self.var.decompress_LR, self.var.wwtSewerResOverflowC)
        np.put(self.var.wwtSewerResOverflow, self.var.decompress_WWT, self.var.wwtSewerResOverflowC)
        np.put(self.var.wwtTreatedOverflow, self.var.decompress_WWT, self.var.wwtTreatedOverflowC)   
        np.put(self.var.wwtEvap, self.var.decompress_WWT, self.var.wwtEvapC)
        np.put(self.var.wwtExportedTreated, self.var.decompress_WWT, self.var.wwtExportedTreatedC)
        self.var.wwtSewerExported =  self.var.wwtExportedTreated + self.var.wwtExportedCollected
        if  checkOption('includeWaterBodies'):
            self.var.wwtSentToResC_LR = np.compress(self.var.compress_LR, self.var.wwtSentToRes)
        
        
        
        # add inflow from wwt treatment facilities
        ## add water from other source to distribution reservoirs
    
        # Reservoir inflow in [m3] at the end of all sub-timestep - source treated wastewater
        if checkOption('includeWaterBodies'):               
            self.var.lakeVolumeM3C += self.var.wwtSentToResC_LR
            self.var.lakeStorageC += self.var.wwtSentToResC_LR
            self.var.lakeResStorageC += self.var.wwtSentToResC_LR 
            self.var.reservoirStorageM3C += self.var.wwtSentToResC_LR 
        
        
        # convert OverflowOut from m3 to m
        self.var.wwtOverflowOutM = self.var.wwtOverflowOut / self.var.cellArea
        