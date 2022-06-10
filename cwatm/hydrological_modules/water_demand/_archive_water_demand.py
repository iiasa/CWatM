# -------------------------------------------------------------------------
# Name:        Waterdemand module
# Purpose:
#
# Author:      PB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

import numpy as np
from cwatm.management_modules import globals

from cwatm.management_modules.replace_pcr import npareatotal, npareamaximum
from cwatm.management_modules.data_handling import returnBool, binding, cbinding, loadmap, divideValues, checkOption, npareaaverage, readnetcdf2
from cwatm.hydrological_modules.water_demand.domestic import waterdemand_domestic
from cwatm.hydrological_modules.water_demand.industry import waterdemand_industry
from cwatm.hydrological_modules.water_demand.livestock import waterdemand_livestock
from cwatm.hydrological_modules.water_demand.irrigation import waterdemand_irrigation
from cwatm.hydrological_modules.water_demand.environmental_need import waterdemand_environmental_need


#PB1507
from cwatm.management_modules.data_handling import *


class water_demand:
    """
    WATERDEMAND

    calculating water demand -
    Industrial, domenstic based on precalculated maps
    Agricultural water demand based on water need by plants
    
    **Global variables**

    ====================  ================================================================================  =========
    Variable [self.var]   Description                                                                       Unit     
    ====================  ================================================================================  =========
    domesticDemand                                                                                                   
    pot_domesticConsumpt                                                                                             
    envFlow                                                                                                          
    readAvlStorGroundwat  same as storGroundwater but equal to 0 when inferior to a treshold                m        
    industryDemand                                                                                                   
    efficiencyPaddy                                                                                                  
    efficiencyNonpaddy                                                                                               
    returnfractionIrr                                                                                                
    irrDemand                                                                                                        
    irrPaddyDemand                                                                                                   
    irrNonpaddyDemand                                                                                                
    waterBodyID           lakes/reservoirs map with a single ID for each lake/reservoir                     --       
    waterBodyBuffer                                                                                                  
    compress_LR           boolean map as mask map for compressing lake/reservoir                            --       
    decompress_LR         boolean map as mask map for decompressing lake/reservoir                          --       
    MtoM3C                conversion factor from m to m3 (compressed map)                                   --       
    waterBodyTypCTemp                                                                                                
    livestockDemand                                                                                                  
    pot_livestockConsump                                                                                             
    MtoM3                 Coefficient to change units                                                       --       
    InvDtSec                                                                                                         
    cellArea              Area of cell                                                                      m2       
    M3toM                 Coefficient to change units                                                       --       
    channelStorage                                                                                                   
    fracVegCover          Fraction of specific land covers (0=forest, 1=grasslands, etc.)                   %        
    nonFossilGroundwater  groundwater abstraction which is sustainable and not using fossil resources       m        
    lakeVolumeM3C         compressed map of lake volume                                                     m3       
    lakeStorageC                                                                                            m3       
    reservoirStorageM3C                                                                                              
    lakeResStorageC                                                                                                  
    lakeResStorage                                                                                                   
    smalllakeVolumeM3                                                                                                
    smalllakeStorage                                                                                                 
    act_SurfaceWaterAbst                                                                                             
    addtoevapotrans                                                                                                  
    act_irrWithdrawal                                                                                                
    act_nonIrrConsumptio                                                                                             
    returnFlow                                                                                                       
    act_irrConsumption    actual irrigation water consumption                                               m        
    unmetDemand                                                                                                      
    act_nonIrrWithdrawal                                                                                             
    returnflowIrr                                                                                                    
    nonIrrReturnFlowFrac                                                                                             
    unmet_lost                                                                                                       
    act_totalWaterWithdr                                                                                             
    act_bigLakeResAbst                                                                                               
    act_smallLakeResAbst                                                                                             
    modflowPumpingM                                                                                                  
    modflowTopography                                                                                                
    modflowDepth2                                                                                                    
    leakageC                                                                                                         
    dom_efficiency                                                                                                   
    demand_unit                                                                                                      
    pot_industryConsumpt                                                                                             
    ind_efficiency                                                                                                   
    unmetDemandPaddy                                                                                                 
    unmetDemandNonpaddy                                                                                              
    totalIrrDemand                                                                                                   
    liv_efficiency                                                                                                   
    waterdemandFixed                                                                                                 
    waterdemandFixedYear                                                                                             
    allocSegments                                                                                                    
    swAbstractionFractio                                                                                             
    allocation_zone                                                                                                  
    modflowPumping                                                                                                   
    leakage                                                                                                          
    pumping                                                                                                          
    nonIrruse                                                                                                        
    act_indDemand                                                                                                    
    act_domDemand                                                                                                    
    act_livDemand                                                                                                    
    nonIrrDemand                                                                                                     
    totalWaterDemand                                                                                                 
    act_indConsumption                                                                                               
    act_domConsumption                                                                                               
    act_livConsumption                                                                                               
    act_totalIrrConsumpt                                                                                             
    act_totalWaterConsum                                                                                             
    pot_GroundwaterAbstr                                                                                             
    pot_nonIrrConsumptio                                                                                             
    readAvlChannelStorag                                                                                             
    act_channelAbst                                                                                                  
    reservoir_command_ar                                                                                             
    leakageC_daily                                                                                                   
    leakageC_daily_segme                                                                                             
    act_irrNonpaddyWithd                                                                                             
    act_irrPaddyWithdraw                                                                                             
    act_irrPaddyDemand                                                                                               
    act_irrNonpaddyDeman                                                                                             
    act_indWithdrawal                                                                                                
    act_domWithdrawal                                                                                                
    act_livWithdrawal                                                                                                
    act_paddyConsumption                                                                                             
    act_nonpaddyConsumpt                                                                                             
    returnflowNonIrr                                                                                                 
    unmet_lostirr                                                                                                    
    unmet_lostNonirr                                                                                                 
    waterabstraction                                                                                                 
    ====================  ================================================================================  =========

    **Functions**
    """

    def __init__(self, model):
        self.var = model.var
        self.model = model

        self.domestic = waterdemand_domestic(model)
        self.industry = waterdemand_industry(model)
        self.livestock = waterdemand_livestock(model)
        self.irrigation = waterdemand_irrigation(model)
        self.environmental_need = waterdemand_environmental_need(model)

    def initial(self):
        """
        Initial part of the water demand module

        Set the water allocation
        """

        # This variable has no impact if includeWaterDemand is False
        self.var.includeIndusDomesDemand = True
        if "includeIndusDomesDemand" in option:
            self.var.includeIndusDomesDemand = checkOption('includeIndusDomesDemand')
        # True if all demands are taken into account, if not only irrigation is considered

        if checkOption('includeWaterDemand'):

            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                #print('=> All water demands are taken into account')

                self.domestic.initial()
                self.industry.initial()
                self.livestock.initial()
                self.irrigation.initial()
                self.environmental_need.initial()
            else:  # only irrigation is considered
                #print('=> Only irrigation is considered as water demand')

                self.irrigation.initial()
                self.environmental_need.initial()

            # if waterdemand is fixed:
            self.var.waterdemandFixed = False
            if "waterdemandFixed" in binding:
                if returnBool('waterdemandFixed'):
                    self.var.waterdemandFixed = True
                    self.var.waterdemandFixedYear = loadmap('waterdemandFixedYear')

            #if 'usingAllocSegments' in binding:
            # if checkOption('usingAllocSegments'):
            #    self.var.allocSegments = loadmap('allocSegments').astype(np.int)
            #    self.var.segmentArea = np.where(self.var.allocSegments > 0, npareatotal(self.var.cellArea, self.var.allocSegments), self.var.cellArea)

            # -------------------------------------------
            # partitioningGroundSurfaceAbstraction
            # partitioning abstraction sources: groundwater and surface water
            # partitioning based on local average baseflow (m3/s) and upstream average discharge (m3/s)
            # estimates of fractions of groundwater and surface water abstractions
            swAbstractionFraction = loadmap('swAbstractionFrac')

            if swAbstractionFraction < 0:

                averageBaseflowInput = loadmap('averageBaseflow')
                averageDischargeInput = loadmap('averageDischarge')
                # convert baseflow from m to m3/s
                if returnBool('baseflowInM'):
                    averageBaseflowInput = averageBaseflowInput * self.var.cellArea * self.var.InvDtSec

                if checkOption('usingAllocSegments'):
                    averageBaseflowInput = np.where(self.var.allocSegments > 0, npareaaverage(averageBaseflowInput, self.var.allocSegments), averageBaseflowInput)
                    # averageUpstreamInput = np.where(self.var.allocSegments > 0, npareamaximum(averageDischargeInput, self.var.allocSegments), averageDischargeInput)

                swAbstractionFraction = np.maximum(0.0, np.minimum(1.0, averageDischargeInput / np.maximum(1e-20, averageDischargeInput + averageBaseflowInput)))
                swAbstractionFraction = np.minimum(1.0, np.maximum(0.0, swAbstractionFraction))

            self.var.swAbstractionFraction = globals.inZero.copy()
            for No in range(4):
                self.var.swAbstractionFraction += self.var.fracVegCover[No] * swAbstractionFraction
            for No in range(4, 6):
                if self.var.modflow:
                    self.var.swAbstractionFraction += self.var.fracVegCover[No] * swAbstractionFraction
                else:
                    self.var.swAbstractionFraction += self.var.fracVegCover[No]  # because we cant put a pumping borehole in a lake in reality!

            self.var.demand_unit = True
            if "demand_unit" in binding:
                self.var.demand_unit = returnBool('demand_unit')

            # allocation zone
            # regular grid inside the 2d array
            # inner grid size
            inner = 1
            if "allocation_area" in binding:
                inner = int(loadmap('allocation_area'))

            latldd, lonldd, cell, invcellldd, rows, cols = readCoord(cbinding('Ldd'))
            try:
                filename = os.path.splitext(cbinding('Ldd'))[0] + '.nc'
                cut0, cut1, cut2, cut3 = mapattrNetCDF(filename, check=False)
            except:
                filename = os.path.splitext(cbinding('Ldd'))[0] + '.tif'
                cut0, cut1, cut2, cut3 = mapattrTiff(gdal.Open(filename, GA_ReadOnly))

            arr = np.kron(np.arange(rows // inner * cols // inner).reshape((rows // inner, cols // inner)), np.ones((inner, inner)))
            arr = arr[cut2:cut3, cut0:cut1].astype(int)
            self.var.allocation_zone = compressArray(arr)


            self.var.modflowPumping = globals.inZero.copy()

            self.var.leakage = globals.inZero.copy()
            self.var.pumping = globals.inZero.copy()

            self.var.modfPumpingM = globals.inZero.copy()
            self.var.Pumping_daily = globals.inZero.copy()
            self.var.modflowDepth2 = 0
            self.var.modflowTopography = 0
            #self.var.leakage = globals.inZero.copy()
            #self.var.pumping = globals.inZero.copy()

            # from Mikhail
            #self.var.gwstorage_full = loadmap('poro')*loadmap('thickness') + globals.inZero
            self.var.allowedPumping = globals.inZero.copy()
            self.var.leakageCanals_M = globals.inZero.copy()


        else:  # no water demand
            self.var.nonIrrReturnFlowFraction = globals.inZero.copy()
            self.var.nonFossilGroundwaterAbs = globals.inZero.copy()
            self.var.nonIrruse = globals.inZero.copy()
            self.var.act_indDemand = globals.inZero.copy()
            self.var.act_domDemand = globals.inZero.copy()
            self.var.act_livDemand = globals.inZero.copy()
            self.var.nonIrrDemand = globals.inZero.copy()
            self.var.totalIrrDemand = globals.inZero.copy()
            self.var.totalWaterDemand = globals.inZero.copy()
            self.var.act_irrWithdrawal = globals.inZero.copy()
            self.var.act_nonIrrWithdrawal = globals.inZero.copy()
            self.var.act_totalWaterWithdrawal = globals.inZero.copy()
            self.var.act_indConsumption = globals.inZero.copy()
            self.var.act_domConsumption = globals.inZero.copy()
            self.var.act_livConsumption = globals.inZero.copy()
            self.var.act_nonIrrConsumption = globals.inZero.copy()
            self.var.act_totalIrrConsumption = globals.inZero.copy()
            self.var.act_totalWaterConsumption = globals.inZero.copy()
            self.var.unmetDemand = globals.inZero.copy()
            self.var.addtoevapotrans = globals.inZero.copy()
            self.var.returnflowIrr = globals.inZero.copy()
            self.var.returnFlow = globals.inZero.copy()
            self.var.unmetDemandPaddy = globals.inZero.copy()
            self.var.unmetDemandNonpaddy = globals.inZero.copy()
            self.var.ind_efficiency = 1.
            self.var.dom_efficiency = 1.
            self.var.liv_efficiency = 1
            self.var.modflowPumping = 0
            self.var.modflowDepth2 = 0
            self.var.modflowTopography = 0
            self.var.act_bigLakeResAbst = globals.inZero.copy()

            self.var.leakage = globals.inZero.copy()
            self.var.pumping = globals.inZero.copy()
            self.var.unmet_lost = globals.inZero.copy()
            self.var.pot_GroundwaterAbstract = globals.inZero.copy()


    def dynamic(self):
        """
        Dynamic part of the water demand module

        * calculate the fraction of water from surface water vs. groundwater
        * get non-Irrigation water demand and its return flow fraction
        """

        if self.var.modflow:

            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.environmental_need.dynamic()
            else:
                self.var.envFlow = 0.00001  # 0.01mm

            # computing leakage from rivers to groundwater

            # self.var.readAvlChannelStorageM will be used in land covertype to compute leakage to groundwater if ModFlow coupling
            # to avoid small values and to avoid surface water abstractions from dry channels (>= 0.01mm)
            self.var.readAvlChannelStorageM = np.where(self.var.channelStorage < (0.0005 * self.var.cellArea), 0.,
                                                       self.var.channelStorage)  # in [m3]
            # coversersion m3 -> m # minus environmental flow
            self.var.readAvlChannelStorageM = self.var.readAvlChannelStorageM * self.var.M3toM  # in [m]
            self.var.readAvlChannelStorageM = np.maximum(0., self.var.readAvlChannelStorageM - self.var.envFlow)


        if checkOption('includeWaterDemand'):

            # for debugging of a specific date
            #if (globals.dateVar['curr'] >= 137):
            #    ii =1

            # ----------------------------------------------------
            # WATER DEMAND

            # Fix year of water demand on predefined year
            wd_date = globals.dateVar['currDate']
            if self.var.waterdemandFixed:
                wd_date = wd_date.replace(day = 1)
                wd_date = wd_date.replace(year = self.var.waterdemandFixedYear)

            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.domestic.dynamic(wd_date)
                self.industry.dynamic(wd_date)
                self.livestock.dynamic(wd_date)
                self.irrigation.dynamic()
                self.environmental_need.dynamic()
            else:
                self.irrigation.dynamic()
            #if not self.var.modflow:
                self.environmental_need.dynamic()

            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                if globals.dateVar['newStart'] or globals.dateVar['newMonth']:
                    # total (potential) non irrigation water demand
                    self.var.nonIrrDemand = self.var.domesticDemand + self.var.industryDemand + self.var.livestockDemand
                    self.var.pot_nonIrrConsumption = np.minimum(self.var.nonIrrDemand, self.var.pot_domesticConsumption +
                                                                self.var.pot_industryConsumption + self.var.pot_livestockConsumption)
                    # fraction of return flow from domestic and industrial water demand
                    self.var.nonIrrReturnFlowFraction = divideValues((self.var.nonIrrDemand - self.var.pot_nonIrrConsumption), self.var.nonIrrDemand)

                # non-irrg fracs in nonIrrDemand
                frac_industry = divideValues(self.var.industryDemand, self.var.nonIrrDemand)
                frac_domestic = divideValues(self.var.domesticDemand, self.var.nonIrrDemand)
                frac_livestock = divideValues(self.var.livestockDemand, self.var.nonIrrDemand)

                # Sum up water demand
                # totalDemand [m]: total maximum (potential) water demand: irrigation and non irrigation
                totalDemand = self.var.nonIrrDemand + self.var.totalIrrDemand  # in [m]
            else:  # only irrigation is considered
                totalDemand = np.copy(self.var.totalIrrDemand)  # in [m]
                #print('-----------------------------totalDemand---------: ', np.mean(totalDemand))

            # ----------------------------------------------------
            # WATER AVAILABILITY

            if not self.var.modflow:  # already done if ModFlow coupling
                # conversion m3 -> m # minus environmental flow
                self.var.readAvlChannelStorageM = np.maximum(0.,self.var.channelStorage * self.var.M3toM - self.var.envFlow) # in [m]


            #-------------------------------------
            # WATER DEMAND vs. WATER AVAILABILITY
            #-------------------------------------

            # surface water abstraction that can be extracted to fulfill totalDemand
            # - based on ChannelStorage and swAbstractionFraction * totalDemand
            # sum up potential surface water abstraction (no groundwater abstraction under water and sealed area)
            pot_SurfaceAbstract = totalDemand * self.var.swAbstractionFraction

            # only local surface water abstraction is allowed (network is only within a cell)
            self.var.act_SurfaceWaterAbstract = np.minimum(self.var.readAvlChannelStorageM, pot_SurfaceAbstract)
            self.var.act_channelAbst = self.var.act_SurfaceWaterAbstract.copy()
            # if surface water is not sufficient it is taken from groundwater

            if checkOption('includeWaterBodies'):

                # water that is still needed from surface water
                remainNeed = np.maximum(pot_SurfaceAbstract - self.var.act_SurfaceWaterAbstract, 0)

                # first from big Lakes and reservoirs, big lakes cover several gridcells
                # collect all water demand from lake pixels of the same id

                #remainNeedBig = npareatotal(remainNeed, self.var.waterBodyID)
                # not only the lakes and reservoirs but the command areas around water bodies e.g. here a buffer
                remainNeedBig = npareatotal(remainNeed, self.var.waterBodyBuffer)
                remainNeedBigC = np.compress(self.var.compress_LR, remainNeedBig)

                # Storage of a big lake
                lakeResStorageC = np.where(self.var.waterBodyTypCTemp == 0, 0.,
                            np.where(self.var.waterBodyTypCTemp == 1, self.var.lakeStorageC, self.var.reservoirStorageM3C)) / self.var.MtoM3C

                minlake = np.maximum(0., 0.98*lakeResStorageC) #reasonable but arbitrary limit
                act_bigLakeAbstC = np.minimum(minlake , remainNeedBigC)
                # substract from both, because it is sorted by self.var.waterBodyTypCTemp
                self.var.lakeStorageC = self.var.lakeStorageC - act_bigLakeAbstC * self.var.MtoM3C
                self.var.lakeVolumeM3C = self.var.lakeVolumeM3C - act_bigLakeAbstC * self.var.MtoM3C
                self.var.reservoirStorageM3C = self.var.reservoirStorageM3C - act_bigLakeAbstC * self.var.MtoM3C
                # and from the combined one for waterbalance issues
                self.var.lakeResStorageC = self.var.lakeResStorageC - act_bigLakeAbstC * self.var.MtoM3C
                self.var.lakeResStorage = globals.inZero.copy()
                np.put(self.var.lakeResStorage, self.var.decompress_LR, self.var.lakeResStorageC)
                bigLakesFactorC = divideValues(act_bigLakeAbstC , remainNeedBigC)

                # and back to the big array
                bigLakesFactor = globals.inZero.copy()
                np.put(bigLakesFactor, self.var.decompress_LR, bigLakesFactorC)

                #bigLakesFactorAllaroundlake = npareamaximum(bigLakesFactor, self.var.waterBodyID)
                bigLakesFactorAllaroundlake = npareamaximum(bigLakesFactor, self.var.waterBodyBuffer)

                # abstraction from big lakes is partioned to the users around the lake
                self.var.act_bigLakeResAbst = remainNeed * bigLakesFactorAllaroundlake

                # remaining need is used from small lakes
                remainNeed1 = remainNeed * (1 - bigLakesFactorAllaroundlake)
                #minlake = np.maximum(0.,self.var.smalllakeStorage - self.var.minsmalllakeStorage) * self.var.M3toM

                if returnBool('useSmallLakes'):
                    minlake = np.maximum(0.,0.98 * self.var.smalllakeStorage) * self.var.M3toM
                    self.var.act_smallLakeResAbst = np.minimum(minlake, remainNeed1)
                    #self.var.actLakeResAbst = np.minimum(0.5 * self.var.smalllakeStorageM3 * self.var.M3toM, remainNeed)
                    # act_smallLakesres is substracted from small lakes storage
                    self.var.smalllakeVolumeM3 = self.var.smalllakeVolumeM3 - self.var.act_smallLakeResAbst * self.var.MtoM3
                    self.var.smalllakeStorage = self.var.smalllakeStorage - self.var.act_smallLakeResAbst * self.var.MtoM3
                else:
                    self.var.act_smallLakeResAbst = 0

                # available surface water is from river network + large/small lake & reservoirs
                self.var.act_SurfaceWaterAbstract = self.var.act_SurfaceWaterAbstract + self.var.act_bigLakeResAbst + self.var.act_smallLakeResAbst

                # check for rounding issues
                self.var.act_SurfaceWaterAbstract = np.minimum(totalDemand,self.var.act_SurfaceWaterAbstract)

                # remaining is taken from groundwater if possible
                remainNeed2 = pot_SurfaceAbstract - self.var.act_SurfaceWaterAbstract

                if 'using_reservoir_command_areas' in binding:
                    if checkOption('using_reservoir_command_areas'):  # checkOption('usingAllocSegments2'):

                        # ABOUT
                        #
                        # The command area of a reservoir is the area that can receive water from this reservoir, through canals or other means.
                        # Performed above, each cell has attempted to satisfy its demands with local water using in-cell channel, lake, and reservoir storage.
                        # The remaining demand within each command area is totaled and requested from the associated reservoir.
                        # The reservoir offers this water up to a daily maximum relating to the available storage in the reservoir, defined in the Reservoir_releases_input_file.
                        #
                        # SETTINGS FILE AND INPUTS

                        # -Activating
                        # In the OPTIONS section towards the beginning of the settings file, add/set
                        # using_reservoir_command_areas = True

                        # - Command areas raster map
                        # Anywhere after the OPTIONS section (in WATERDEMAND, for example), add/set reservoir_command_areas to a path holding...
                        # information about the command areas. This Command areas raster map should assign the same positive integer coding to each cell within the same segment.
                        # All other cells must Nan values, or values <= 0.

                        # -Optional inputs
                        #
                        # Anywhere after the OPTIONS section, add/set Reservoir_releases_input_file to a path holding information about irrigation releases.
                        # This should be a raster map (netCDF) of 366 values determining the maximum fraction of available storage to be used for meeting water demand...
                        # in the associated command area on the day of the year. If this is not included, a value of 0.01 will be assumed,
                        # i.e. 1% of the reservoir storage can be at most released into the command area on each day.

                        ## Command area total demand
                        #
                        # The remaining demand within each command area [M3] is put into a map where each cell in the command area holds this total demand
                        demand_Segment = np.where(self.var.reservoir_command_areas > 0,
                                                  npareatotal(remainNeed2 * self.var.cellArea,
                                                              self.var.reservoir_command_areas),
                                                  0)  # [M3]

                        ## Reservoir associated with the Command Area
                        #
                        # If there is more than one reservoir in a command area, the storage of the reservoir with maximum storage in this time-step is chosen.
                        # The map resStorageTotal_alloc holds this maximum reservoir storage within a command area in all cells within that command area

                        reservoirStorageM3 = globals.inZero.copy()
                        np.put(reservoirStorageM3, self.var.decompress_LR, self.var.reservoirStorageM3C)
                        resStorageTotal_alloc = np.where(self.var.reservoir_command_areas > 0,
                                                         npareamaximum(reservoirStorageM3,
                                                                       self.var.reservoir_command_areas), 0)  # [M3]

                        # In the map resStorageTotal_allocC, the maximum storage from each allocation segment is held in all reservoir cells within that allocation segment.
                        # We now correct to remove the reservoirs that are not this maximum-storage-reservoir for the command area.
                        resStorageTotal_allocC = np.compress(self.var.compress_LR, resStorageTotal_alloc)
                        resStorageTotal_allocC = np.multiply(resStorageTotal_allocC == self.var.reservoirStorageM3C,
                                                             resStorageTotal_allocC)

                        # The rules for the maximum amount of water to be released for irrigation are found for the chosen maximum-storage reservoir in each command area
                        day_of_year = globals.dateVar['currDate'].timetuple().tm_yday

                        if 'Reservoir_releases_input_file' in binding:
                            resStorage_maxFracForIrrigation = readnetcdf2('Reservoir_releases_input_file', day_of_year,
                                                                          useDaily='DOY', value='Fraction of Volume')
                        else:
                            resStorage_maxFracForIrrigation = 0.01 + globals.inZero.copy()

                        # resStorage_maxFracForIrrigationC holds the fractional rules found for each reservoir, so we must null those that are not the maximum-storage reservoirs
                        resStorage_maxFracForIrrigationC = np.compress(self.var.compress_LR,
                                                                       resStorage_maxFracForIrrigation)
                        resStorage_maxFracForIrrigationC = np.multiply(
                            resStorageTotal_allocC == self.var.reservoirStorageM3C, resStorage_maxFracForIrrigationC)
                        np.put(resStorage_maxFracForIrrigation, self.var.decompress_LR, resStorage_maxFracForIrrigationC)

                        resStorage_maxFracForIrrigation_CA = np.where(self.var.reservoir_command_areas > 0,
                                                                      npareamaximum(resStorage_maxFracForIrrigation,
                                                                                    self.var.reservoir_command_areas), 0)

                        if 'Water_conveyance_efficiency' in binding:
                            Water_conveyance_efficiency = loadmap('Water_conveyance_efficiency')
                        else:
                            Water_conveyance_efficiency = 1.0

                        act_bigLakeResAbst_alloc = np.minimum(resStorage_maxFracForIrrigation_CA * resStorageTotal_alloc,
                                                              demand_Segment / Water_conveyance_efficiency)  # [M3]

                        ResAbstractFactor = np.where(resStorageTotal_alloc > 0,
                                                     divideValues(act_bigLakeResAbst_alloc, resStorageTotal_alloc),
                                                     0)  # fraction of water abstracted versus water available for total segment reservoir volumes
                        # Compressed version needs to be corrected as above
                        ResAbstractFactorC = np.compress(self.var.compress_LR, ResAbstractFactor)
                        ResAbstractFactorC = np.multiply(resStorageTotal_allocC == self.var.reservoirStorageM3C,
                                                         ResAbstractFactorC)

                        self.var.lakeStorageC -= self.var.reservoirStorageM3C * ResAbstractFactorC
                        self.var.lakeVolumeM3C -= self.var.reservoirStorageM3C * ResAbstractFactorC
                        self.var.lakeResStorageC -= self.var.reservoirStorageM3C * ResAbstractFactorC
                        self.var.reservoirStorageM3C -= self.var.reservoirStorageM3C * ResAbstractFactorC

                        self.var.lakeResStorage = globals.inZero.copy()
                        np.put(self.var.lakeResStorage, self.var.decompress_LR, self.var.lakeResStorageC)

                        metRemainSegment = np.where(demand_Segment > 0,
                                                    divideValues(act_bigLakeResAbst_alloc * Water_conveyance_efficiency,
                                                                 demand_Segment), 0)  # by definition <= 1

                        self.var.leakageC_daily = resStorageTotal_allocC * ResAbstractFactorC * (
                                    1 - Water_conveyance_efficiency)
                        self.var.leakageC += self.var.leakageC_daily
                        self.var.leakageC_daily_segments = np.sum(self.var.leakageC_daily) + globals.inZero

                        self.var.act_bigLakeResAbst += remainNeed2 * metRemainSegment
                        self.var.act_SurfaceWaterAbstract += remainNeed2 * metRemainSegment

                        ## End of using_reservoir_command_areas


            # remaining is taken from groundwater if possible
            #print('                   totalDemand : ', np.mean(totalDemand))
            self.var.pot_GroundwaterAbstract = totalDemand - self.var.act_SurfaceWaterAbstract
            #print('self.var.pot_GroundwaterAbstract : ', np.mean(self.var.pot_GroundwaterAbstract))
            self.var.nonFossilGroundwaterAbs = np.maximum(0.,np.minimum(self.var.readAvlStorGroundwater, self.var.pot_GroundwaterAbstract))
            # calculate renewableAvlWater_local (non-fossil groundwater and channel) - environmental flow
            #self.var.renewableAvlWater_local = self.var.readAvlStorGroundwater + self.var.readAvlChannelStorageM

            if self.var.modflow:
                # if available storage is too low, no pumping in this cell (defined in transient module)

                # self.var.allowedPumping = np.maximum(self.var.groundwater_storage_available - (1-self.var.availableGWStorageFraction)*self.var.gwstorage_full, 0)
                # self.var.nonFossilGroundwaterAbs = np.minimum(self.var.allowedPumping, self.var.pot_GroundwaterAbstract)  # gwstorage_cell
                self.var.nonFossilGroundwaterAbs = np.where(self.var.groundwater_storage_available > (
                        1 - self.var.availableGWStorageFraction) * self.var.gwstorage_full, self.var.pot_GroundwaterAbstract, 0)
                # self.var.nonSatisfiedGWrequest = self.var.pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs

            # if limitAbstraction from groundwater is True
            # fossil gwAbstraction and water demand may be reduced
            # variable to reduce/limit groundwater abstraction (> 0 if limitAbstraction = True)
            if checkOption('limitAbstraction'):
                # real surface water abstraction can be lower, because not all demand can be done from surface water
                act_swAbstractionFraction = divideValues(self.var.act_SurfaceWaterAbstract, totalDemand)
                # Fossil groundwater abstraction is not allowed
                # allocation rule here: domestic& industry > irrigation > paddy

                if self.var.includeIndusDomesDemand:  # all demands are taken into account
                    # non-irrgated water demand: adjusted (and maybe increased) by gwabstration factor
                    # if nonirrgated water demand is higher than actual growndwater abstraction (wwhat is needed and what is stored in gw)
                    act_nonIrrWithdrawalGW = self.var.nonIrrDemand * (1 - act_swAbstractionFraction)
                    act_nonIrrWithdrawalGW = np.where(act_nonIrrWithdrawalGW > self.var.nonFossilGroundwaterAbs, self.var.nonFossilGroundwaterAbs, act_nonIrrWithdrawalGW)
                    act_nonIrrWithdrawalSW = act_swAbstractionFraction * self.var.nonIrrDemand
                    self.var.act_nonIrrWithdrawal = act_nonIrrWithdrawalSW + act_nonIrrWithdrawalGW

                    # irrigated water demand:
                    act_irrWithdrawalGW = self.var.totalIrrDemand * (1 - act_swAbstractionFraction)
                    act_irrWithdrawalGW = np.minimum(self.var.nonFossilGroundwaterAbs - act_nonIrrWithdrawalGW, act_irrWithdrawalGW)
                    act_irrWithdrawalSW = act_swAbstractionFraction * self.var.totalIrrDemand
                    self.var.act_irrWithdrawal = act_irrWithdrawalSW + act_irrWithdrawalGW
                    # (nonpaddy)
                    act_irrnonpaddyGW = self.var.fracVegCover[3] * (1 - act_swAbstractionFraction) * self.var.irrDemand[3]
                    act_irrnonpaddyGW = np.minimum(self.var.nonFossilGroundwaterAbs - act_nonIrrWithdrawalGW, act_irrnonpaddyGW)
                    act_irrnonpaddySW = self.var.fracVegCover[3] * act_swAbstractionFraction * self.var.irrDemand[3]
                    self.var.act_irrNonpaddyWithdrawal = act_irrnonpaddySW + act_irrnonpaddyGW
                    # (paddy)
                    act_irrpaddyGW = self.var.fracVegCover[2] * (1 - act_swAbstractionFraction) * self.var.irrDemand[2]
                    act_irrpaddyGW = np.minimum(self.var.nonFossilGroundwaterAbs - act_nonIrrWithdrawalGW - act_irrnonpaddyGW, act_irrpaddyGW)
                    act_irrpaddySW = self.var.fracVegCover[2] * act_swAbstractionFraction * self.var.irrDemand[2]
                    self.var.act_irrPaddyWithdrawal = act_irrpaddySW + act_irrpaddyGW

                    act_gw = act_nonIrrWithdrawalGW + act_irrWithdrawalGW
                else:  # only irrigation is considered

                    self.var.act_nonIrrWithdrawal = globals.inZero.copy()

                    # irrigated water demand:
                    act_irrWithdrawalGW = self.var.totalIrrDemand * (1 - act_swAbstractionFraction)
                    act_irrWithdrawalGW = np.minimum(self.var.nonFossilGroundwaterAbs, act_irrWithdrawalGW)
                    act_irrWithdrawalSW = act_swAbstractionFraction * self.var.totalIrrDemand
                    self.var.act_irrWithdrawal = act_irrWithdrawalSW + act_irrWithdrawalGW
                    # (nonpaddy)
                    act_irrnonpaddyGW = self.var.fracVegCover[3] * (1 - act_swAbstractionFraction) * self.var.irrDemand[3]
                    act_irrnonpaddyGW = np.minimum(self.var.nonFossilGroundwaterAbs, act_irrnonpaddyGW)
                    act_irrnonpaddySW = self.var.fracVegCover[3] * act_swAbstractionFraction * self.var.irrDemand[3]
                    self.var.act_irrNonpaddyWithdrawal = act_irrnonpaddySW + act_irrnonpaddyGW
                    # (paddy)
                    act_irrpaddyGW = self.var.fracVegCover[2] * (1 - act_swAbstractionFraction) * self.var.irrDemand[2]
                    act_irrpaddyGW = np.minimum(
                        self.var.nonFossilGroundwaterAbs - act_irrnonpaddyGW, act_irrpaddyGW)
                    act_irrpaddySW = self.var.fracVegCover[2] * act_swAbstractionFraction * self.var.irrDemand[2]
                    self.var.act_irrPaddyWithdrawal = act_irrpaddySW + act_irrpaddyGW

                    act_gw = np.copy(act_irrWithdrawalGW)


                # todo: is act_irrWithdrawal needed to be replaced? Check later!!
                # consumption - irrigation (without loss) = demand  * efficiency   (back to non fraction value)

                ## back to non fraction values
                # self.var.act_irrWithdrawal[2] = divideValues(self.var.act_irrPaddyWithdrawal, self.var.fracVegCover[2])
                #self.var.act_irrWithdrawal[3] = divideValues(self.var.act_irrNonpaddyWithdrawal, self.var.fracVegCover[3])
                ## consumption - irrigation (without loss) = demand  * efficiency

                # calculate act_ water demand, because irr demand has still demand from previous day included
                # if the demand from previous day is not fulfilled it is taken to the next day and so on
                # if we do not correct we double account each day the demand from previous days
                self.var.act_irrPaddyDemand = np.maximum(0, self.var.irrPaddyDemand - self.var.unmetDemandPaddy)
                self.var.act_irrNonpaddyDemand = np.maximum(0, self.var.irrNonpaddyDemand - self.var.unmetDemandNonpaddy)

                # unmet is either pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs or demand - withdrawal
                if self.var.includeIndusDomesDemand:  # all demands are taken into account
                    self.var.unmetDemand = (self.var.totalIrrDemand - self.var.act_irrWithdrawal) + (self.var.nonIrrDemand - self.var.act_nonIrrWithdrawal)
                else:  # only irrigation is considered
                    self.var.unmetDemand = (self.var.totalIrrDemand - self.var.act_irrWithdrawal) - self.var.act_nonIrrWithdrawal
                self.var.unmetDemandPaddy = self.var.irrPaddyDemand - self.var.act_irrPaddyDemand
                self.var.unmetDemandNonpaddy = self.var.irrNonpaddyDemand - self.var.act_irrNonpaddyDemand


            else:
                # This is the case when using ModFlow coupling (limitation imposed previously)
                if self.var.modflow:
                    # This is the case when using ModFlow coupling (limitation imposed previously)
                    # part of the groundwater demand unsatisfied
                    self.var.unmetDemand = self.var.pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs

                    if self.var.includeIndusDomesDemand:  # all demands are taken into account
                        self.var.act_nonIrrWithdrawal = np.copy(self.var.nonIrrDemand)
                    self.var.act_irrWithdrawal = np.copy(self.var.totalIrrDemand)

                    act_gw = np.copy(self.var.nonFossilGroundwaterAbs)
                    # LUCA: TAKE CARE OF THE ORDER OF FRACLANDCOVER
                    self.var.act_irrNonpaddyWithdrawal = self.var.fracVegCover[3] * self.var.irrDemand[3]
                    self.var.act_irrPaddyWithdrawal = self.var.fracVegCover[2] * self.var.irrDemand[2]


                else:
                    # Fossil groundwater abstractions are allowed (act = pot)
                    self.var.unmetDemand = self.var.pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs

                    # using allocation from abstraction zone
                    # this might be a regualr grid e.g. 2x2 for 0.5 deg
                    left_sf = self.var.readAvlChannelStorageM - self.var.act_channelAbst
                    # sum demand, surface water - local used, groundwater - local use, not satisfied for allocation zone
                    zoneDemand = npareatotal(self.var.unmetDemand,self.var.allocation_zone)
                    zone_sf_avail = npareatotal(left_sf, self.var.allocation_zone)

                    # zone abstraction is minimum of availability and demand
                    zone_sf_abstraction = np.minimum(zoneDemand,zone_sf_avail)
                    # water taken from surface zone and allocated to cell demand
                    cell_sf_abstraction = np.maximum(0.,divideValues(left_sf,zone_sf_avail) * zone_sf_abstraction)
                    cell_sf_allocation = np.maximum(0.,divideValues(self.var.unmetDemand, zoneDemand) * zone_sf_abstraction)

                    # sum up with other abstraction
                    self.var.act_SurfaceWaterAbstract = self.var.act_SurfaceWaterAbstract + cell_sf_abstraction
                    self.var.act_channelAbst = self.var.act_channelAbst +  cell_sf_abstraction


                    # new potential groundwater abstraction
                    self.var.pot_GroundwaterAbstract = np.maximum(0.,self.var.pot_GroundwaterAbstract - cell_sf_allocation)
                    left_gw_demand = np.maximum(0.,self.var.pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs)
                    left_gw_avail = self.var.readAvlStorGroundwater - self.var.nonFossilGroundwaterAbs
                    zone_gw_avail = npareatotal(left_gw_avail, self.var.allocation_zone)

                    # for groundwater substract demand which is fulfilled by surface zone, calc abstraction and what is left.
                    #zone_gw_demand = npareatotal(left_gw_demand, self.var.allocation_zone)
                    zone_gw_demand = zoneDemand -  zone_sf_abstraction
                    zone_gw_abstraction = np.minimum(zone_gw_demand,zone_gw_avail)
                    #zone_unmetdemand = np.maximum(0., zone_gw_demand - zone_gw_abstraction)

                    # water taken from groundwater zone and allocated to cell demand
                    cell_gw_abstraction = np.maximum(0.,divideValues(left_gw_avail,zone_gw_avail) * zone_gw_abstraction)
                    cell_gw_allocation = np.maximum(0.,divideValues(left_gw_demand,zone_gw_demand) * zone_gw_abstraction)

                    self.var.unmetDemand = np.maximum(0.,left_gw_demand - cell_gw_allocation)
                    self.var.nonFossilGroundwaterAbs = self.var.nonFossilGroundwaterAbs + cell_gw_abstraction

                    #self.var.unmetDemand = self.var.pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs
                    ## end of zonal abstraction

                    # unmet demand is again checked for water from channels and abstraction from surface is increased
                    #channelAbs2 = np.minimum(self.var.readAvlChannelStorageM - self.var.act_channelAbst, self.var.unmetDemand)
                    #self.var.act_SurfaceWaterAbstract = self.var.act_SurfaceWaterAbstract + channelAbs2
                    #self.var.act_channelAbst = self.var.act_channelAbst +  channelAbs2
                    #self.var.unmetDemand = self.var.unmetDemand - channelAbs2
                    #self.var.pot_GroundwaterAbstract = self.var.pot_GroundwaterAbstract - channelAbs2

                    if self.var.includeIndusDomesDemand:  # all demands are taken into account
                        self.var.act_nonIrrWithdrawal = np.copy(self.var.nonIrrDemand)
                    self.var.act_irrWithdrawal = np.copy(self.var.totalIrrDemand)

                    act_gw = np.copy(self.var.pot_GroundwaterAbstract)
                    # LUCA: TAKE CARE OF THE ORDER OF FRACLANDCOVER
                    self.var.act_irrNonpaddyWithdrawal = self.var.fracVegCover[3] * self.var.irrDemand[3]
                    self.var.act_irrPaddyWithdrawal = self.var.fracVegCover[2] * self.var.irrDemand[2]


            ## End of limit extraction if, then

            self.var.act_irrConsumption[2] = divideValues(self.var.act_irrPaddyWithdrawal, self.var.fracVegCover[2]) * self.var.efficiencyPaddy
            self.var.act_irrConsumption[3] = divideValues(self.var.act_irrNonpaddyWithdrawal, self.var.fracVegCover[3]) * self.var.efficiencyNonpaddy

            if self.var.modflow:
                if self.var.GW_pumping:  # pumping demand is sent to ModFlow (used in transient module)
                    self.var.modfPumpingM += act_gw  # modfPumpingM is initialized every "modflow_timestep" in "groundwater_modflow/transient.py"
                    self.var.Pumping_daily = np.copy(act_gw)

            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.var.act_indWithdrawal = frac_industry * self.var.act_nonIrrWithdrawal
                self.var.act_domWithdrawal = frac_domestic * self.var.act_nonIrrWithdrawal
                self.var.act_livWithdrawal = frac_livestock * self.var.act_nonIrrWithdrawal
                self.var.act_indConsumption = self.var.ind_efficiency * self.var.act_indWithdrawal
                self.var.act_domConsumption = self.var.dom_efficiency * self.var.act_domWithdrawal
                self.var.act_livConsumption = self.var.liv_efficiency * self.var.act_livWithdrawal

                self.var.act_nonIrrConsumption = self.var.act_domConsumption + self.var.act_indConsumption + self.var.act_livConsumption
            else:  # only irrigation is considered
                self.var.act_nonIrrConsumption = globals.inZero.copy()
            self.var.act_totalIrrConsumption = self.var.fracVegCover[2] * self.var.act_irrConsumption[2] + self.var.fracVegCover[3] * self.var.act_irrConsumption[3]
            self.var.act_paddyConsumption = self.var.fracVegCover[2] * self.var.act_irrConsumption[2]
            self.var.act_nonpaddyConsumption = self.var.fracVegCover[3] * self.var.act_irrConsumption[3]

            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.var.totalWaterDemand = self.var.fracVegCover[2] * self.var.irrDemand[2] + self.var.fracVegCover[3] * self.var.irrDemand[3] + self.var.nonIrrDemand
                self.var.act_totalWaterWithdrawal = self.var.act_nonIrrWithdrawal + self.var.act_irrWithdrawal
                self.var.act_totalWaterConsumption = self.var.act_nonIrrConsumption + self.var.act_totalIrrConsumption
            else:  # only irrigation is considered
                self.var.totalWaterDemand = self.var.fracVegCover[2] * self.var.irrDemand[2] + self.var.fracVegCover[3] * self.var.irrDemand[3]
                self.var.act_totalWaterWithdrawal = np.copy(self.var.act_irrWithdrawal)
                self.var.act_totalWaterConsumption = np.copy(self.var.act_totalIrrConsumption)

            # --- calculate return flow
            #Sum up loss - difference between withdrawn and consumed - split into return flow and evaporation
            sumIrrLoss = self.var.act_irrWithdrawal - self.var.act_totalIrrConsumption

            self.var.returnflowIrr =  self.var.returnfractionIrr * sumIrrLoss
            self.var.addtoevapotrans = (1- self.var.returnfractionIrr) * sumIrrLoss
            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.var.returnflowNonIrr  = self.var.nonIrrReturnFlowFraction * self.var.act_nonIrrWithdrawal

            # limit return flow to not put all fossil groundwater back into the system, because
            # it can lead to higher river discharge than without water demand, as water is taken from fossil groundwater (out of system)
            unmet_div_ww = 1. - np.minimum(1, divideValues(self.var.unmetDemand, self.var.act_totalWaterWithdrawal))

            if checkOption('limitAbstraction'):
                unmet_div_ww = 1

            #self.var.unmet_lost = ( self.var.returnflowIrr + self.var.returnflowNonIrr +  self.var.addtoevapotrans) * (1-unmet_div_ww)

            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.var.unmet_lost = ( self.var.returnflowIrr + self.var.returnflowNonIrr +  self.var.addtoevapotrans) * (1-unmet_div_ww)
            else:  # only irrigation is considered
                self.var.unmet_lost = (self.var.returnflowIrr + self.var.addtoevapotrans) * (1 - unmet_div_ww)


            #self.var.waterDemandLost = self.var.act_totalWaterConsumption + self.var.addtoevapotrans
            self.var.unmet_lostirr = ( self.var.returnflowIrr  +  self.var.addtoevapotrans) * (1-unmet_div_ww)
            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.var.unmet_lostNonirr = self.var.returnflowNonIrr * (1-unmet_div_ww)

            self.var.returnflowIrr = self.var.returnflowIrr * unmet_div_ww
            self.var.addtoevapotrans = self.var.addtoevapotrans * unmet_div_ww
            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.var.returnflowNonIrr =  self.var.returnflowNonIrr * unmet_div_ww

            # returnflow to river and to evapotranspiration
            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.var.returnFlow = self.var.returnflowIrr + self.var.returnflowNonIrr
            else:  # only irrigation is considered
                self.var.returnFlow = self.var.returnflowIrr
            self.var.waterabstraction = self.var.nonFossilGroundwaterAbs + self.var.unmetDemand + self.var.act_SurfaceWaterAbstract

            #---------------------------------------------
            # testing
            
            
            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.model.waterbalance_module.waterBalanceCheck(
                    [self.var.act_irrWithdrawal],  # In
                    [self.var.act_totalIrrConsumption,self.var.unmet_lostirr,self.var.addtoevapotrans,self.var.returnflowIrr],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand5a", False)


                self.model.waterbalance_module.waterBalanceCheck(
                    [self.var.act_nonIrrWithdrawal],  # In
                    [self.var.act_nonIrrConsumption , self.var.returnflowNonIrr, self.var.unmet_lostNonirr],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand5b", False)

                self.model.waterbalance_module.waterBalanceCheck(
                    [self.var.ind_efficiency * frac_industry * self.var.act_nonIrrWithdrawal],  # In
                    [self.var.act_indConsumption],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand5c", False)

                self.model.waterbalance_module.waterBalanceCheck(
                    [ self.var.act_indWithdrawal],  # In
                    [self.var.act_indConsumption/ self.var.ind_efficiency],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand5d", False)


            # ----------------------------------------------------------------
            if checkOption('calcWaterBalance'):
                self.model.waterbalance_module.waterBalanceCheck(
                    [self.var.act_irrWithdrawal],  # In
                    [self.var.act_totalIrrConsumption, self.var.returnflowIrr,self.var.unmet_lostirr,self.var.addtoevapotrans],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterlossdemand1", False)

                self.model.waterbalance_module.waterBalanceCheck(
                    [self.var.nonIrrDemand, self.var.totalIrrDemand],  # In
                    [self.var.nonFossilGroundwaterAbs, self.var.unmetDemand, self.var.act_SurfaceWaterAbstract],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand1", False)
                if checkOption('includeWaterBodies'):
                    self.model.waterbalance_module.waterBalanceCheck(
                        [self.var.act_SurfaceWaterAbstract],  # In
                        [ self.var.act_bigLakeResAbst,self.var.act_smallLakeResAbst, self.var.act_channelAbst],  # Out
                        [globals.inZero],
                        [globals.inZero],
                        "Waterdemand1b", False)


                self.model.waterbalance_module.waterBalanceCheck(
                    [self.var.nonFossilGroundwaterAbs, self.var.unmetDemand, self.var.act_SurfaceWaterAbstract],  # In
                    [self.var.act_totalWaterWithdrawal],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand2", False)

                self.model.waterbalance_module.waterBalanceCheck(
                    [self.var.act_totalWaterWithdrawal],  # In
                    [self.var.act_irrPaddyWithdrawal, self.var.act_irrNonpaddyWithdrawal, self.var.act_nonIrrWithdrawal],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand3", False)

                self.model.waterbalance_module.waterBalanceCheck(
                    [self.var.act_totalWaterWithdrawal],  # In
                    [self.var.act_totalIrrConsumption, self.var.act_nonIrrConsumption, self.var.addtoevapotrans, self.var.returnflowIrr, self.var.returnflowNonIrr, self.var.unmet_lost],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand4", False)

                self.model.waterbalance_module.waterBalanceCheck(
                    [self.var.act_totalWaterWithdrawal],  # In
                    [self.var.act_totalIrrConsumption, self.var.act_nonIrrConsumption, self.var.addtoevapotrans, self.var.returnFlow, self.var.unmet_lost ],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand5", False)

                self.model.waterbalance_module.waterBalanceCheck(
                    [self.var.act_totalWaterWithdrawal],  # In
                    [self.var.waterabstraction],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand level1", False)
