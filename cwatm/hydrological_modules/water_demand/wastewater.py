# -------------------------------------------------------------------------
# -------------------------------------------------------------------------
# Name:        Wastewaster Treatment
# Purpose:
#
# Author:      DF
#
# Created:     27/10/2021
# Copyright:   (c) DF 2021
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
from cwatm.management_modules.globals import *


class waterdemand_wastewater(object):
    """
    WASTEWATER TREATMENT
    Update 28/06/21:
    * In progess: allowing many-to-many relations between WWTP and reservoirs. Based on Excel input to replace reservoirs maps.
    
    Update 14/04/21:
     * Now include urban lekage: allow share of direct runoff from sealed areas to be added to wastewater.
     * New ways to treat access volume of influents:calculate HRT as daily_capacity/influents -> define min_HRT allowed. if HRT > min_HRT -> wwt treatment quality is reduced,
       else -> discharge to raw sewage
    
    Update 9/12/21:
     * Now includes evaporation from wastewater treatment facilities. Assume treatment ponds as a 6-meter deep cylinder-like.
     * Now includes two types of wastewater export:
        * export of untreated collected wastewater, in case collection area has a wwtID that is outside the maskmap.
        * export of treated wastewater, based on predefined share of water exported per wastewater treatment facility.
        
    Note:
    Wastewater are the result of domestic/industrial wateruse. They are collected as a share of these water users return flows.
    Effluents are collected and sent to differenct wastewater treatment facilites from prescpecified collection areas. 
    After treatment water can be released back to the environment in a prespecified overflow location, or reused via a distribution reservoir (type == 4).
    
    How to use:
    In the [OPTIONS] section in the settings file add: 'includeWastewater = True'. Later, in the [WASTEWATER] section include the following:
     -- specify a path to the wastewater module input data.
     -- include netCDF files describing the wastewater treatement facilities: ID (wwtID), daily volume (wwtVol), and year of establishment (wwtYear), 
        duration of treatment in days (wwtTime; if missing the default is 2 days; recommended values range from 1 -3 days). 
     -- include additional netCDF files associated to each treatment facility with its ID to describe: overflow/discharge point (wwtOverflow), and effluents colleciton area (wwt_ColArea).  

    Optional input: 
     -- reduce sewege geneartion or collection with wwtColShare (ration between no collection of effluents, 0 - to - collect all wastewater and no return flows 1)
     -- allow water discharge in reservoir - add a netCDF file with reservoir locations. For each reservoir accepting water from a treatment plant - put wastewater treatment facility ID.
     -- using the 'wwtToResManagement' input you can decide if a treatment facility sends all water as overflow/discharge (-1); try to send all to a reservoir (0), or exports 
        a predefined portion of it ( > 0; <=1); defaults to 0.

    **Global variables**

    =====================================  ======================================================================  =====
    Variable [self.var]                    Description                                                             Unit 
    =====================================  ======================================================================  =====
    wwt_def                                                                                                             
    wastewater_to_reservoirs                                                                                            
    waterBodyOut                           biggest outlet (biggest accumulation of ldd network) of a waterbody     --   
    compress_LR                            boolean map as mask map for compressing lake/reservoir                  --   
    decompress_LR                          boolean map as mask map for decompressing lake/reservoir                --   
    waterBodyOutC                          compressed map biggest outlet of each lake/reservoir                    --   
    resVolumeC                             compressed map of reservoir volume                                      Milli
    cellArea                               Area of cell                                                            m2   
    EWRef                                  potential evaporation rate from water surface                           m    
    wwtUrbanLeakage                                                                                                     
    wwtColArea                                                                                                          
    urbanleak                                                                                                           
    wwtID                                                                                                               
    compress_WWT                                                                                                        
    decompress_WWT                                                                                                      
    wwtC                                                                                                                
    minHRT                                                                                                              
    wwtOverflow                                                                                                         
    toResManageC                                                                                                        
    wwtStorage                                                                                                          
    wwtColShare                                                                                                         
    wwtSewerCollectedC                                                                                                  
    wwtSewerTreatedC                                                                                                    
    wwtExportedTreatedC                                                                                                 
    wwtSewerToTreatmentC                                                                                                
    wwtSewerOverflowC                                                                                                   
    wwtSewerResOverflowC                                                                                                
    wwtTreatedOverflowC                                                                                                 
    wwtSentToResC                                                                                                       
    wwtOverflowOut                                                                                                      
    wwtEvapC                                                                                                            
    wwtSewerCollected                                                                                                   
    wwtSewerTreated                                                                                                     
    wwtExportedTreated                                                                                                  
    wwtSewerToTreatment                                                                                                 
    wwtSewerExported                                                                                                    
    wwtSewerOverflow                                                                                                    
    wwtSentToRes                                                                                                        
    wwtSewerResOverflow                                                                                                 
    wwtTreatedOverflow                                                                                                  
    wwtEvap                                                                                                             
    wwtInTreatment                                                                                                      
    wwtIdsOrdered                                                                                                       
    wwtVolC                                                                                                             
    wwtTimeC                                                                                                            
    extensive                                                                                                           
    noPools_extensive                                                                                                   
    poolVolume_extensive                                                                                                
    wwtSurfaceAreaC                                                                                                     
    extensive_counter                                                                                                   
    wwtResIDTemp_compress                                                                                               
    wwtResIDC                                                                                                           
    wwtResTypC                                                                                                          
    wwtResYearC                                                                                                         
    wwtSentToResC_LR                                                                                                    
    wwtOverflowOutM                                                                                                     
    lakeVolumeM3C                          compressed map of lake volume                                           m3   
    lakeStorageC                                                                                                   m3   
    reservoirStorageM3C                                                                                                 
    lakeResStorageC                                                                                                     
    lakeResStorage                                                                                                      
    includeWastewater                                                                                                   
    wwtEffluentsGenerated                                                                                               
    wwtSewerCollection                                                                                                  
    wwtExportedCollected                                                                                                
    =====================================  ======================================================================  =====

    **Functions**
    """

    def __init__(self, model):
        self.var = model.var
        self.model = model
	
    def initial(self):
        if self.var.includeWastewater:
            ## Setup wastewater treatment facilities
            # load inputs
            self.var.wwtID = loadmap('wwtID').astype(np.int64)
            self.var.compress_WWT = self.var.wwtID > 0
            self.var.decompress_WWT = np.nonzero(self.var.compress_WWT)
            self.var.wwtC =  np.compress(self.var.compress_WWT, self.var.wwtID)
 
            ### make adjustement for low-tech basin - e.g., set maximum pools to 5. 
            ## Build extensive differently, e.g. 5 days and more in treatment is extensive - set max surface area or as function of reservoir volume with 6 meter depth.
            
            # Currently assumes each treatment pond to be a cylinder-like shape with 6 meters depth - daily surface area
            
            # share to collect urban leakage
            self.var.urbanleak = loadmap('urbanleak')
            
            # share defines the minimum HRT allowed before sending water to the sewers
            self.var.minHRT = np.maximum(loadmap('minHRT'), 0.01)

            # create outlet for overflow
            self.var.wwtOverflow = loadmap('wwtOverflow').astype(np.int64) 

            # toResManageC control wwt2reservoir operations:
            '''
                -1: only send to overflow point as discharge (do not send to reservoir)
                0 -1: between zero to one gives the fraction of treated wastewater to export; the rest are sent to reservoir (if exists)
                An extreme case of 0 tries sending all treated wastewater to the reservoir (if exists), it send it to overflow point when it is full 
            
            THIS PART IS IN DYNAMIC_INIT
            # CONSIDER INCLUDING
            if "wwtExportCoeffcient" in binding:
                self.var.toResManageC = np.minimum(self.var.toResManageC + loadmap('wwtExportCoeffcient'), 1.) * (self.var.toResManageC > 0)
            '''
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
            # use self.var.decompress_LR to decompress
            self.var.wwtSewerResOverflowC = np.compress(self.var.compress_LR, globals.inZero.copy())
            self.var.wwtTreatedOverflowC = np.compress(self.var.compress_WWT, globals.inZero.copy())
            self.var.wwtSentToResC = np.compress(self.var.compress_LR, globals.inZero.copy())
            # maybe another approach?? -> compress and decompress?
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
        '''
            Update: wwt definitions from Excel Settings
            
            Settings are loaded from Excel allow dynamic update of wastewater treatment plants operation and capacities.
            The file defines for each WWTP ID within a specific range of time (from-to years) the following:
             * daily capacity (Volume)
             * Treatment duration (Days)
             * Treatment level (categories: 1 primary, 2 secondary, 3, tertiary
             * Export share (%) of daily outflows - exported out of basin
             * Wastewater source: Domestic, Industrial (boolean)
             
            
             The variable is a dictionary with keys as WWTP ID and np,array for each instance. The variable order is as follows:
             ['From year', 'To year', 'Volume (cubic m per day)', 'Treatment days', 'Treatment level', 'Export share', 'Domestic', 'Industrial']
            
        '''
        
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
        
        # Volume, treatementTime, ExportAndMangement

        self.var.wwtVolC = []
        self.var.wwtTimeC = []
        self.var.toResManageC = []
        
        for wwtid in self.var.wwtIdsOrdered:
            i = np.in1d(self.var.wwtIdsOrdered, wwtid)
            self.var.wwtVolC.append(self.var.wwt_def[wwtid][int(annual_wwtpIdx[i])][2])
            self.var.wwtTimeC.append(self.var.wwt_def[wwtid][int(annual_wwtpIdx[i])][3]) 
            # if no management data - assume 0 -> try to send to reservoir, and discharge if no free volume
            mng = self.var.wwt_def[wwtid][int(annual_wwtpIdx[i])][5]
            self.var.toResManageC.append(int(np.where(np.isnan(mng), 0., mng)))
        
        self.var.wwtVolC = np.array(self.var.wwtVolC)
        self.var.wwtTimeC = np.array(self.var.wwtTimeC)
        self.var.toResManageC = np.array(self.var.toResManageC)
        self.var.wwtIdsOrdered = np.array(self.var.wwtIdsOrdered)
        ### Extensive WWTP ####
        # Identify extensive systems - if timeLag >= 5
        self.var.extensive = self.var.wwtTimeC >= 5
        # number of days to fill a treatement pool in extensive systems - default no. of pools: 3
        self.var.noPools_extensive = 3
        
        daysToFill_extensive = self.var.wwtTimeC / self.var.noPools_extensive
        # Volume for an extnesive treatement pool in extensive systems
        self.var.poolVolume_extensive = self.var.wwtVolC * daysToFill_extensive
        
        # Calculate surface area of treatment pools for evaporation
        self.var.wwtSurfaceAreaC = np.where(self.var.extensive, self.var.poolVolume_extensive, self.var.wwtVolC) / np.where(self.var.wwtIdsOrdered  > 0, 6.0, 1.0)        
        
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
        if dateVar['newStart'] or dateVar['newYear']:
            self.dynamic_init()
        
        # set daily overflow to zero - prevent double counting 
        ### A PROBLEM OCCURS: in the result it seems that thse two variables are zero at the first day of each year - is it possible that the model initializes every year?
        overflow_temp =  globals.inZero.copy()  
        self.var.wwtSentToRes = globals.inZero.copy()

        
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
            
            # sum sewer collection per facility [m3]
            self.var.wwtSewerCollectedC[idIndex] = np.nansum(collectionAreaMask * (self.var.wwtSewerCollection) * self.var.cellArea) #  - self.var.wwtExportedCollected 

            # calculate max water allowed
            max_collected_idIndex = self.var.wwtVolC[idIndex] / self.var.minHRT 
          
            
            # calculate to overflow
            toOverflow = np.maximum(self.var.wwtSewerCollectedC[idIndex] - max_collected_idIndex, 0.)
            
            # calculate collected
            wwtSewerCollected_idIndex2 = self.var.wwtSewerCollectedC[idIndex] - toOverflow
            
            # calculate HRT - for water quality calculations
            hrt_idIndex = np.minimum(self.var.wwtVolC[idIndex] / wwtSewerCollected_idIndex2, 1.)
            
           
            # calculate overflow - if summed volume excceds daily capacity [m3]
            self.var.wwtSewerOverflowC[idIndex] = toOverflow
            '''
            if wwt_id == 32:
                print(np.nansum(collectionAreaMask))
                print(self.var.wwtSewerCollectedC[idIndex])
                print(self.var.wwtSewerOverflowC[idIndex])
            '''
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
            
            # handle storage 
            if self.var.extensive[idIndex]:
                
                #print(idIndex)
                #print("last Storage Ext" + str(np.round(self.var.wwtStorage[idIndex][-1], 0)))
                # extensive
                # calculate remainStorage in pool 0
                remainStorage0 = self.var.poolVolume_extensive[idIndex] - self.var.wwtStorage[wwt_id][0]
                
                # calculate volume to add to storage0 and add to storage1
                addToStorage0 = np.minimum(remainStorage0, self.var.wwtSewerToTreatmentC[idIndex])
                addToStorage1 =  self.var.wwtSewerToTreatmentC[idIndex] - addToStorage0
                    
                # add to storage
                self.var.wwtStorage[wwt_id][0] += addToStorage0
                
                # if reservoir routing is off
                self.var.wwtSewerTreatedC[idIndex] = 0
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
                    self.var.wwtSewerTreatedC[idIndex] =  np.nansum(self.var.wwtStorage[wwt_id][cond])
                
                    # update storage
                    self.var.wwtStorage[wwt_id] = np.where(cond, 0., self.var.wwtStorage[wwt_id])
                
                # active treatement pools are those which are not receieving water inflows. Ther are being emptied (e.g., water are used after the defined treatment days)
                # count days with positive water volume in active treatement pools
                cond = self.var.wwtStorage[wwt_id][1:] > 0
                if cond.any():
                    
                    self.var.extensive_counter[wwt_id][1:] += (cond * 1)
                    
                    self.var.extensive_counter[wwt_id][1:] = np.where(np.logical_not(cond), 0, self.var.extensive_counter[wwt_id][1:])
                '''
                Example from Sorek - print for water quality code dev.
                if idIndex == 2:
                    print(idIndex)
                    print(self.var.wwtStorage[idIndex])
                    print(self.var.extensive_counter[idIndex])
                    print(self.var.wwtSewerTreatedC[idIndex])
                '''
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
            
            #print("Raw sewer")
            #print(np.nansum(overflow_temp))
            # toResManageC control wwt2reservoir operations:
            '''
                -1: only send to overflow point as discharge (do not send to reservoir)
                0 -1: between zero to one gives the fraction of treated wastewater to export; the rest are sent to reservoir (if exists)
                An extreme case of 0 tries sending all treated wastewater to the reservoir (if exists), it send it to overflow point when it is full 
            
            '''
            toResManage = self.var.toResManageC[idIndex]
                
            dischargeTreatedWaterBool = False
            if toResManage == -1:
                dischargeTreatedWaterBool = True
            
            
            if (toResManage > 1) | (toResManage < 0):
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
                #print(wwt_id)
                #print(np.nansum(overflow_temp))
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
                self.var.wwtResTypC = np.compress(self.var.wwtResIDTemp_compress, loadmap('waterBodyTyp').astype(np.int64))
                self.var.wwtResYearC = np.compress(self.var.wwtResIDTemp_compress, loadmap('waterBodyYear'))
                    
                # do not alow reservoir use if their type ids is zero (e.g., wetland) or id they have not been yet established
                self.var.wwtResIDC =  np.where(self.var.wwtResTypC == 0, 0,  np.where(self.var.wwtResYearC > simulatedYear, 0,  self.var.wwtResIDC))
                    
                # calculate allocation weights
                resVolumeC = np.compress(self.var.wwtResIDTemp_compress, loadmap('waterBodyVolRes')) * 1000000
                    
                resVolumeLeftC = np.minimum(np.maximum(resVolumeC - np.compress(self.var.wwtResIDTemp_compress, self.var.lakeResStorage), 0.), resVolumeC)
                   
                resAllocWeights = divideValues(resVolumeLeftC, npareatotal(resVolumeLeftC, self.var.wwtResIDC > 0)) * (self.var.wwtResIDC > 0)
                
                # Do not allow all reservoir to be zero - split wastewater proportionally to total storage
                if np.nansum(resAllocWeights) == 0:
                    resAllocWeights = divideValues(resVolumeC, npareatotal(resVolumeC, self.var.wwtResIDC > 0)) * (self.var.wwtResIDC > 0)
                        
                    
                    
                #print(np.nansum(self.var.wwtSewerTreatedC[idIndex]))
                # get location of res
                #wwtResindex = self.var.wwtResID_LRC == wwt_id
                wwtResindex = np.in1d(self.var.waterBodyOutC, self.var.wastewater_to_reservoirs[wwt_id])
                sendToRes = self.var.wwtSewerTreatedC[idIndex] * resAllocWeights
                    

                self.var.wwtSentToResC[wwtResindex] = np.where((sendToRes - resVolumeLeftC) >= 0, resVolumeLeftC, sendToRes)
                # split water and calcualte overflow in reservoirs - continute here ! error! - something doesnot work with res overflow - it is not written to the layer
                # see lines 286 -295 for clues

                # below it was originaly assignes (=); I suspect it overwritten
                    
                self.var.wwtSewerResOverflowC[wwtResindex] = sendToRes - self.var.wwtSentToResC[wwtResindex]
                  
                #self.var.wwtSewerResOverflowC[wwtResindex] = np.where(self.var.wwtSewerResOverflowC[wwtResindex] < 0, resVolumeLeftC, self.var.wwtSewerResOverflowC[wwtResindex])
                #self.var.wwtSentToResC[wwtResindex] -= self.var.wwtSewerResOverflowC[wwtResindex]
                  
                # update overflow
                    
                overflow_temp += overflowMask * np.nansum(self.var.wwtSewerResOverflowC[wwtResindex])
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
        np.put(self.var.wwtSewerResOverflow, self.var.decompress_LR, self.var.wwtSewerResOverflowC)
        np.put(self.var.wwtTreatedOverflow, self.var.decompress_WWT, self.var.wwtTreatedOverflowC)   
        np.put(self.var.wwtEvap, self.var.decompress_WWT, self.var.wwtEvapC)
        np.put(self.var.wwtExportedTreated, self.var.decompress_WWT, self.var.wwtExportedTreatedC)
        self.var.wwtSewerExported =  self.var.wwtExportedTreated + self.var.wwtExportedCollected
        self.var.wwtSentToResC_LR = np.compress(self.var.compress_LR, self.var.wwtSentToRes)
        
        
        
        # add inflow from wwt treatment facilities
        ## add water from other source to distribution reservoirs
    
        # Reservoir inflow in [m3] at the end of all sub-timestep - source treated wastewater
        #print(np.nansum(self.var.lakeResStorageC - self.var.resVolumeC > 0))
               
        self.var.lakeVolumeM3C += self.var.wwtSentToResC_LR
        self.var.lakeStorageC += self.var.wwtSentToResC_LR
        self.var.lakeResStorageC += self.var.wwtSentToResC_LR 
        self.var.reservoirStorageM3C += self.var.wwtSentToResC_LR 
        #resStorageC += self.var.wwtSentToResC_LR
                
        sendToResOverflow_LR = np.where((self.var.lakeResStorageC - self.var.resVolumeC) > 0, self.var.lakeResStorageC - self.var.resVolumeC, 0.)
        addTowwtSewerResOverflow = globals.inZero.copy()
        np.put(addTowwtSewerResOverflow, self.var.decompress_WWT, sendToResOverflow_LR)
        self.var.wwtSewerResOverflow += addTowwtSewerResOverflow
        self.var.wwtOverflowOut += addTowwtSewerResOverflow
        
        '''
        # correct urbanlekage and wastewater collection from deleted wwtp and send to overflow.
        deletedWWTPIDs = self.var.wwtC[np.in1d(self.var.wwtC, self.var.wwtIdsOrdered)]
        deletedWWTPIDs_mask = np.where(np.in1d(self.var.wwtColArea, deletedWWTPIDs), 1, 0)
        deletedWWTPIDsOverflow_mask = np.where(np.in1d(self.var.wwtOverflow, deletedWWTPIDs), 0, 1) * (self.var.wwtOverflow > 0)
        collection2returnflow = np.nansum(self.var.wwtSewerCollection * self.var.cellArea * deletedWWTPIDs_mask) * deletedWWTPIDsOverflow_mask
        
        # update nonIrr runoff
        self.var.wwtOverflowOut += collection2returnflow
        
        # update also sewerOverflow outmap
        self.var.wwtSewerOverflow += collection2returnflow
        '''
        
        # convert OverflowOut from m3 to m
        self.var.wwtOverflowOutM = self.var.wwtOverflowOut / self.var.cellArea
        
        
        
        
        
        
        # UPDATE wwtSendToRes
        self.var.wwtSentToRes -= addTowwtSewerResOverflow
                
        # UPDATE LAKERESSTORAGE
        self.var.lakeVolumeM3C -= sendToResOverflow_LR
        self.var.lakeStorageC -= sendToResOverflow_LR
        self.var.lakeResStorageC -= sendToResOverflow_LR
        self.var.reservoirStorageM3C -= sendToResOverflow_LR
        #resStorageC -= sendToResOverflow_LR
        
        printError = False
        if (printError):
            # print balance
            inputs = np.nansum(self.var.wwtSewerCollected)
            outputs = np.nansum(self.var.wwtSewerOverflow + self.var.wwtSewerResOverflow + self.var.wwtTreatedOverflow + self.var.wwtEvap +  self.var.wwtSewerExported + self.var.wwtSentToRes)
            sto = np.nansum(self.var.wwtInTreatment)
        
            wwt_error = (inputs - outputs + (sto - sto_0))/ ((inputs + outputs) / 2)
            print("wastewater error: ", str(wwt_error))
        #print(np.nansum(self.var.wwtSentToResC_LR))
        