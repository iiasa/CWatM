# import libraries
import numpy as np
import os
from  cwatm.management_modules.data_handling import *
from cwatm.hydrological_modules.groundwater_modflow.modflow6 import ModFlowSimulation
import importlib
import xarray as xr
'''
    =====================================  ======================================================================  =====
    Variable [self.var]                    Description                                                             Unit 
    =====================================  ======================================================================  =====
    sum_gwRecharge                         groundwater recharge                                                    m    
    cellArea                               Area of cell                                                            m2   
    gwdepth_observations                   Input, gw_depth_observations, groundwater depth observations            m    
    gwdepth_adjuster                       Groundwater depth adjuster                                              m    
    modflow                                Flag: True if modflow_coupling = True in settings file                  --   
    baseflow                               simulated baseflow (= groundwater discharge to river)                   m    
    capillar                               Simulated flow from groundwater to the third CWATM soil layer           m    
    capriseindex                                                                                                        
    soildepth12                            Total thickness of layer 2 and 3                                        m    
    leakageriver_factor                                                                                                 
    leakagelake_factor                                                                                                  
    modflow_timestep   l                    Chosen ModFlow model timestep (1day, 7days, 30days, etc.)                    
    head                                   Simulated ModFlow water level [masl]                                    m    
    gwdepth_adjusted                       Adjusted depth to groundwater table                                     m    
    gwdepth                                Depth to groundwater table                                              m    
    modflow_cell_area                                                                                                   
    modflowsteady                          True if modflow_steadystate = True in settings file                     --   
    Ndays_steady                           Number of steady state run before the transient simulation              --   
    channel_ratio                                                                                                       
    modflowtotalSoilThickness              Array (nrows, ncol) used to compute water table depth in post-processi  m    
    load_init_water_table                                                                                               
    GW_pumping                             Input, True if Groundwater_pumping=True                                 bool 
    use_complex_solver_for_modflow                                                                                      
    availableGWStorageFraction                                                                                          
    wells_index                                                                                                         
    depth                                                                                                               
    sumed_sum_gwRecharge                                                                                                
    modflow_compteur                       Counts each day relatively to the chosen ModFlow timestep, allow to ru       
    modflow_watertable                                                                                                  
    writeerror                                                                                                          
    modflowdiscrepancy                                                                                                  
    groundwater_storage_top_layer                                                                                       
    groundwater_storage_available                                                                                       
    gwstorage_full                         Groundwater storage at full capacity                                    m    
    permeability                                                                                                        
    modfPumpingM_actual                                                                                                 
    gwdepth_difference_sim_obs             Difference between simulated and observed groundwater table             m    
    modflow_head_adjusted                                                                                               
    waterdemandFixed                                                                                                    
    modfPumpingM                                                                                                        
    =====================================  ======================================================================  =====
'''

'''
    **Functions 1**
'''
def parseArray(arr, splt = ";"):
    return arr.split(splt)

def is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def decompress(map, nanvalue=None):
    """
    Decompressing CWatM maps from 1D to 2D with missing values

    :param map: compressed map
    :return: decompressed 2D map
    """

    dmap = maskinfo['maskall'].copy()
    dmap[~maskinfo['maskflat']] = map[:]
    if nanvalue is not None:
        dmap.data[np.isnan(dmap.data)] = nanvalue

    return dmap.data
    
def load_percentile_nc(self, var, percentile, mask=None):
    """Loads a single NetCDF sub-grid elevation percentile as a 2D array matching

    load_lyr_map spatial dimensions (nrow, ncol).

    :param var: Configuration binding string (e.g., 'percentile_elevation')
    :param percentile: Variable name string (e.g., 'z_p50')
    :param mask: Boolean spatial mask array (e.g., self.modflow_basin)
    :return: 2D np.ndarray of shape (nrow, ncol)
    """
    # 1. Resolve NetCDF file path
    filePath = cbinding(var)

    # 2. Open dataset and extract requested percentile variable
    ds = xr.open_dataset(filePath)

    if percentile not in ds.data_vars:
        ds.close()
        raise KeyError(
            f"Percentile variable '{percentile}' not found in NetCDF file."
        )

    grid_2d = ds[percentile].values.astype(np.float32)
    ds.close()

    # Use default MODFLOW basin mask if none passed
    if mask is None and hasattr(self, "modflow_basin"):
        mask = self.modflow_basin[0]

    # 3. Apply 2D spatial mask
    if mask is not None:
        grid_2d[mask == False] = np.nan

    return grid_2d
def load_modflow_basin(self, var):
    rasterio = importlib.import_module("rasterio", package=None)
    with rasterio.open(cbinding(var), 'r') as src:
        mbas = src.read(1).astype(bool)  # read in as 2-dimensional array (nrows, ncols).
        self.domain = {
            'rowsize': abs(src.profile['transform'].e),
            'colsize': abs(src.profile['transform'].a),
            'nrow': int(src.profile['height']),
            'ncol': int(src.profile['width']),
            'west': src.profile['transform'].c,
            'east': src.profile['transform'].c + (src.profile['width']-1) * abs(src.profile['transform'].a),
            'north': src.profile['transform'].f,
            'south': src.profile['transform'].f - (src.profile['height']-1) * abs(src.profile['transform'].e)
        }
        domain['rowsize'] = abs(src.profile['transform'].e)
        domain['colsize'] = abs(src.profile['transform'].a)
        domain['nrow'] = int(src.profile['height'])
        domain['ncol'] = int(src.profile['width'])
        domain['west'] = src.profile['transform'].c
        
        domain['east'] = src.profile['transform'].c + (src.profile['width']-1) * abs(src.profile['transform'].a)
        domain['north'] = src.profile['transform'].f
        domain['south'] = src.profile['transform'].f - (src.profile['height']-1) * abs(src.profile['transform'].e)
    return mbas
  

def load_aquifer_coeff(self, var, nlay, mult = 1, mask = None, splt = ";"):
    # can be used only after loading a mask
    if isinstance(var, int):
        varList = 0
    else:
        varList = parseArray(cbinding(var), splt = splt)  # ['0.08', 'path...']
        
    emptyList = [None] * len(varList)
    lyrs = nlay
    if nlay < len(varList):
        raise ValueError(f'{var} has {len(varList)} parameters, but the model {nlay} layers')
    if nlay == len(varList):
        lyrs = 0
    for i in range(len(varList)):
        #print(i)
        val = varList[i].strip()
        
        #print(val)
        if is_float(val):
           # create map from float
           emptyList[i] = map_from_param(self = self, var = float(val), nlay_ = lyrs, mult = mult)
        else:
           emptyList[i] = load_lyr_map(var = val, mask = mask, mult = mult, parsePath = False)
    if nlay == 1:
        return np.array([np.array(emptyList)[0]])
    return np.array(emptyList)
    

def load_lyr_map(var, mask = None, parsePath = True, mult = 1):
    rasterio = importlib.import_module("rasterio", package=None)
    pth = var
    if parsePath:
        pth = cbinding(pth)
    with rasterio.open(pth, 'r') as src:
        lyrmap = src.read(1).astype(np.float32)
        if not mask is None:
            lyrmap[mask == False] = np.nan
        lyrmap = lyrmap * mult
    return lyrmap

# 
def map_from_param(self, var, nlay_, mult = 1):
    if not is_float(var):
        var = float(cbinding(var))
    prm = var * mult
    if nlay_ == 0:
        return np.full((self.domain['nrow'], self.domain['ncol']), prm)
    return np.full((nlay_, self.domain['nrow'], self.domain['ncol']), prm)
            
            
class groundwater_modflow:
    '''
    **Functions 2**
    '''
    
    def __init__(self, model):
        self.var = model.var
        self.model = model

    def get_corrected_modflow_cell_area(self):
        return np.bincount(
            self.indices['ModFlow_index'],
            weights=np.invert(self.var.mask.astype(bool)).ravel()[self.indices['CWatM_index']] * self.indices['area'],
            minlength=self.modflow.basin.size
        ).reshape(self.modflow.basin.shape)

    def get_corrected_cwatm_cell_area(self):
        return (self.var.cellArea_uncompressed.ravel() - np.bincount(
            self.indices['CWatM_index'],
            weights=np.invert(self.modflow.basin).ravel()[self.indices['ModFlow_index']] * self.indices['area'],
            minlength=self.var.mask.size
        )).reshape(self.var.mask.shape)

    def CWATM2modflow(self, variable, correct_boundary=False):
        """Converting flow [L/T] from 2D CWatM map to 2D ModFlow map"""
        if correct_boundary:
            modflow_cell_area = self.corrected_modflow_cell_area.ravel()
        else:   
            modflow_cell_area = self.domain['rowsize'] * self.domain['colsize']  # in m2
       
        array = (np.bincount(
            self.indices['ModFlow_index'],
            variable.ravel()[self.indices['CWatM_index']]* self.indices['area'],
            minlength=self.domain['nrow'] * self.domain['ncol']
        ) / modflow_cell_area).reshape((self.domain['nrow'], self.domain['ncol'])).astype(variable.dtype)
        return array
    
    def modflow2CWATM(self, variable, correct_boundary=False):
        """Converting flow [L/T] from 2D ModFLow map to 2D CWatM map"""
        basin_map = self.modflow.basin.copy()
        basin_map = basin_map[0]
        variable_copy = variable.copy()
        variable_copy[basin_map == False] = 0 # MODIFIED DOR FRIDMAN; ASSUMES BASIN MASK IS THE SAME FOR ALL LAYERS
        assert not (np.isnan(variable_copy).any())
        assert basin_map.dtype == bool
        if correct_boundary:
            cwatm_cell_area = self.corrected_cwatm_cell_area.ravel()
        else:
            # MODIF LUCA
            cwatm_cell_area = self.var.cellArea.ravel()  # in m2
        array = (np.bincount(
            self.indices['CWatM_index'],
            weights=variable_copy.ravel()[self.indices['ModFlow_index']] * self.indices['area'],
            minlength=maskinfo['shape'][0] * maskinfo['shape'][1]) / \
                 decompress(cwatm_cell_area, nanvalue=0)).reshape(
            maskinfo['shape']).astype(variable_copy.dtype)
        

        array[maskinfo['mask'] == 1] = np.nan

        return array
    '''
    def modflow2CWATM_debug(self, variable, correct_boundary=False):
        """Converting flow [L/T] from 2D ModFLow map to 2D CWatM map"""
        basin_map = self.modflow.basin.copy()
        basin_map = basin_map[0]
        variable_copy = variable.copy()
        variable_copy[basin_map == False] = 0 # MODIFIED DOR FRIDMAN; ASSUMES BASIN MASK IS THE SAME FOR ALL LAYERS
        assert not (np.isnan(variable_copy).any())
        assert basin_map.dtype == bool
        if correct_boundary:
            cwatm_cell_area = self.corrected_cwatm_cell_area.ravel()
        else:
            # MODIF LUCA
            cwatm_cell_area = self.var.cellArea.ravel()  # in m2
        array = (np.bincount(
            self.indices['CWatM_index'],
            weights=variable_copy.ravel()[self.indices['ModFlow_index']] * self.indices['area'],
            minlength=maskinfo['shape'][0] * maskinfo['shape'][1]) / \
                 decompress(cwatm_cell_area, nanvalue=0)).reshape(
            maskinfo['shape']).astype(variable_copy.dtype)
        print("min")
        print(np.nanmin(variable_copy))
        print(np.nanmin(array))
        
        print("mean")
        print(np.nanmean(variable_copy))
        print(np.nanmean(array))

        print("max")
        print(np.nanmax(variable_copy))
        print(np.nanmax(array))

        array[maskinfo['mask'] == 1] = np.nan

        return array
    '''
    def calcSaturatedCellFraction(self, lyr, head, omega = 10**-6):
    
        ''' 
        Applied from 'Documentaton for the MODFLOW 6 Groundwater Flow Model | Ch. 55 of Section A, Groundwater, Book6, Modeling Techniques'
        https://pubs.usgs.gov/tm/06/a55/tm6a55.pdf
           
        '''
        
        Aomega = 1 / (1-omega)
        # calculate cell saturated thickness - pp.62-63; eq.  4-4
        dv_n = np.maximum(np.minimum(head[lyr], self.layer_boundaries[lyr]) - self.layer_boundaries[lyr + 1], 0.)
        
        # calculate cell saturated fraction - pp.62-63; eq.  4-6
        sfn = divideArrays(dv_n, self.layer_boundaries[lyr] - self.layer_boundaries[lyr + 1])
        
        # use quadratic smooth function - pp.62-63; eq.  4-5

        sfn_quad = np.where(sfn < 0,  0., 
        np.where(sfn < omega, (Aomega / (2 * omega)) * sfn ** 2 , 
        np.where(sfn < 1 - omega, Aomega * sfn + 0.5 * (1 -Aomega) , 
        np.where(sfn < 1, 1 - ((Aomega/(2*omega)) * (1 -sfn) ** 2), 1.))))


        # recalculate cell saturated thickness - pp. 64 eq. 4-8

        #v_n_new = sfn_quad * (self.layer_boundaries[lyr] - self.layer_boundaries[lyr + 1])

        #return(sfn)
        return(sfn_quad)
        
    def modflow2CWATMbis(self, variable, correct_boundary=False):
        """Converting the 2D ModFLow capillary rise map into the fraction of area where capillary rise occurs
        in the 2D CWatM maps. return a fraction for each CWatM cell, input is the ModFlow capillary rise map
        the returned array is used to apply leakage from water bodies to the ModFlow layer"""
        basin_map = self.modflow.basin.copy()
        
        basin_map = basin_map[0,: ,:]
        variable_copy = variable.copy()
        variable_copy[basin_map == False] = 0 # MODIFIED DOR FRIDMAN; ASSUMES BASIN MASK IS THE SAME FOR ALL LAYERS
        variable_copy[variable_copy > 0] = 1  # Each ModFlow cell is distinguished between producing or not producing capillary rise
        assert not (np.isnan(variable_copy).any())
        assert self.modflow.basin.dtype == bool
        if correct_boundary:
            cwatm_cell_area = self.corrected_cwatm_cell_area.ravel()
        else:
            cwatm_cell_area = self.var.cellArea.ravel()  # in m2
        array = (np.bincount(
            self.indices['CWatM_index'],
            weights=variable_copy.ravel()[self.indices['ModFlow_index']] * self.indices['area'],
            minlength=maskinfo['shape'][0]*maskinfo['shape'][1]
        ) / decompress(cwatm_cell_area,  nanvalue=0)).reshape(maskinfo['shape']).astype(variable_copy.dtype)
        array[maskinfo['mask'] == 1] = np.nan
        return array

    def initial(self):
        # check if we we are using steady state option. Not yet implemented in this version, the user should provide an
        # estimate of the initial water table ("head" variable in the initial part)

        # ModFlow6 version is only daily currently
        self.var.modflow_timestep = 1  #int(loadmap('modflow_timestep'))
        #self.var.Ndays_steady = 0  #int(loadmap('Ndays_steady'))

       
            
        # test if ModFlow coupling is used as defined in settings file
        self.var.modflow = False
        if 'modflow_coupling' in option:
            self.var.modflow = checkOption('modflow_coupling')
        
        '''
        # --- NEW STEADY STATE SETTINGS DISCOVERY ---
        self.var.modflowsteady = False
        if 'modflow_steadystate' in binding:
            self.var.modflowsteady = returnBool('modflow_steadystate')
            
        self.var.Ndays_steady = 0
        if 'Ndays_steady' in binding:
            self.var.Ndays_steady = int(loadmap('Ndays_steady'))
        ''' 
        if self.var.modflow:

            print('\n=> ModFlow is used\n')

            verboseGW = False
            if 'verbose_GW' in binding:
                verboseGW = returnBool('verbose_GW')

            # Define the size of the ModFlow time step - means that ModFlow is called each "modflow_timestep"
            self.var.modflow_timestep = int(loadmap('modflow_timestep'))
            if verboseGW:
                print('ModFlow is activated')
                print('ModFlow timestep is : ', self.var.modflow_timestep, ' days\n')

            modflow_directory = cbinding('PathGroundwaterModflow')
            modflow_directory_output = cbinding('PathGroundwaterModflowOutput')

            directory_mf6dll = cbinding('path_mf6dll')
            if not(os.path.isdir(directory_mf6dll)):
                msg = "Error 222: Path to Modflow6 files does not exists "
                raise CWATMDirError(directory_mf6dll,msg,sname='path_mf6dll')

            nlay = int(loadmap('nlay'))
            
            # MODIFIED DOR FRIDMAN
            # creata a 3d numpy.ndarray with shape (nlay, nrow, ncol); at this point all layers MUST have the same mask (multiple basins are not allowed)
            modflow_basin = load_modflow_basin(self, var = 'modflow_basin')
           
            nr = modflow_basin.shape[0]
            nc = modflow_basin.shape[1]
            self.modflow_basin = np.full((nlay, nr, nc), modflow_basin)
            
               # uploading arrays allowing to transform 2D arrays from ModFlow to CWatM and conversely
            modflow_x = np.load(os.path.join(cbinding('cwatm_modflow_indices'), 'modflow_x.npy'))
            modflow_y = np.load(os.path.join(cbinding('cwatm_modflow_indices'), 'modflow_y.npy'))
            cwatm_x = np.load(os.path.join(cbinding('cwatm_modflow_indices'), 'cwatm_x.npy'))
            cwatm_y = np.load(os.path.join(cbinding('cwatm_modflow_indices'), 'cwatm_y.npy'))
            
            # MODIF LUCA
      
            self.indices = {
                'area': np.load(os.path.join(cbinding('cwatm_modflow_indices'), 'area.npy')),
                'ModFlow_index': np.array(modflow_y * self.domain['ncol'] + modflow_x),
                'CWatM_index': np.array(cwatm_y * maskinfo['shape'][1] + cwatm_x)
            }

            indices_cell_area = np.bincount(self.indices['CWatM_index'], weights=self.indices['area'],
                                            minlength=maskinfo['mapC'][0])
            area_correction = (decompress(self.var.cellArea, nanvalue=0) / indices_cell_area)[self.indices['CWatM_index']]
            
            # SUGGESTED BY LUCA
            self.indices['area'] = self.indices['area'] * (area_correction + (1-area_correction) * 0.5)
            
            print("NUMBER OF ACTIVE CELLS IN MODEL: " + str(np.nansum(self.modflow_basin)))

            # load topography use mask; modflow resolution
            topography = load_lyr_map(var = 'topo_modflow', mask = self.modflow_basin[0]) 
            
            # load thickness currently with float only. Use thickness = 0.08; 0.1 in settings file for different layer values
            thickness = load_aquifer_coeff(self, var = 'thickness', nlay = nlay)
            
            #
            self.var.channel_ratio = load_lyr_map(var = 'chanRatio')
            
            if checkOption('includeWaterBodies'):
                waterBodyID_temp = loadmap('waterBodyID').astype(np.int64)
                self.waterBodyID_modflow = self.CWATM2modflow(decompress(waterBodyID_temp))
            
            # correct - below water bodies - mask channel_ration with water area from cwatm - currently set to 1
            self.var.channel_ratio = np.where(self.waterBodyID_modflow > 0, 1. , self.var.channel_ratio)
            # ADD WETLAND PERCENTAGE BASED ON ESA 2021 V200 TO INCREASE DRAINANGE THROUGH BASEFLOW
            # FORCE RIVER CHANNEL FRACTION TO BE HIGHER IF FRACTION WETLAND > RIVEER CHANNEL FRACTION
            # SET WETLAND FRACTION IN GRIDCELLS WITH LAKE/RESERVOIR TO 0
            if 'wetland_fraction' in binding:
                wetland_cal_coeff = 1
                if 'wetland_bf_coeff' in binding:
                    wetland_cal_coeff = int(loadmap('wetland_bf_coeff')) 
                
                wetland_frac = load_lyr_map(var = 'wetland_fraction') * wetland_cal_coeff
                # remove wetland in water bodies
                if checkOption('includeWaterBodies'):

                # load lakes/reservoirs map with a single ID for each lake/reservoir
                    
                    wetland_frac = np.where(self.waterBodyID_modflow > 0, 0, wetland_frac)
                
                # update channel_ratio
                self.var.channel_ratio = np.where(wetland_frac > self.var.channel_ratio, wetland_frac, self.var.channel_ratio)
            
            # Coef to multiply transmissivity and storage coefficient (because ModFlow convergence is better if aquifer's thicknes is big and permeability is small)
            self.coefficient = 1

            # load permeability map/paramter - lateral and vertical
            self.permeability = load_aquifer_coeff(self, var = 'permeability', nlay = nlay,  mult =  24 * 3600 / self.coefficient)
            if 'permeability_vertical' in binding:
                self.permeability_v = load_aquifer_coeff(self, var = 'permeability_vertical', nlay = nlay,  mult =  24 * 3600 / self.coefficient)
            else:
                self.permeability_v = self.permeability.copy()
            
            # load porosity map/parameter  
            self.porosity = load_aquifer_coeff(self, var = 'poro', nlay = nlay)
            
            if 'set_confinedAquifer' in binding:
                # set 0 for only confined aquifers, if > 0 so a combination of confined and unconfined layers can be used
                self.confinedAquifer_flags = load_aquifer_coeff(self, var = 'set_confinedAquifer', nlay = nlay)
            else:
                self.confinedAquifer_flags = np.where(self.modflow_basin, 1., 0.)
            
            self.var.adjust_drainage_by_river = False
            if 'adjust_drainage_by_river' in binding:
                self.var.adjust_drainage_by_river = returnBool('adjust_drainage_by_river')
            
            # MODIF LUCA
            # Converting the CWatM soil thickness into ModFlow map, then soil thickness will be removed from topography
            # if there is a lake or a reservoir soil depth should be replace (instead of 0) by the averaged soil depth (if not the topography under the lake is above neighboring cells)
            soildepth_as_GWtop = False
            if 'use_soildepth_as_GWtop' in binding:
                soildepth_as_GWtop = returnBool('use_soildepth_as_GWtop')
            correct_depth_underlakes = False
            if 'correct_soildepth_underlakes' in binding:
                correct_depth_underlakes = returnBool('correct_soildepth_underlakes')

            if soildepth_as_GWtop:  # topographic minus soil depth map is used as groundwater upper boundary
                if correct_depth_underlakes:  # in some regions or models soil depth is around zeros under lakes, so it should be similar than neighboring cells
                    if verboseGW:
                        print('=> Topography minus soil depth is used as upper limit of groundwater. Correcting depth under lakes.')
                    waterBodyID_temp = loadmap('waterBodyID').astype(np.int64)
                    soil_depth_temp = np.where(waterBodyID_temp != 0, np.nanmedian(self.var.soildepth12) - loadmap('depth_underlakes'), self.var.soildepth12)
                    soil_depth_temp = np.where(self.var.soildepth12 < 0.4, np.nanmedian(self.var.soildepth12), self.var.soildepth12)  # some cells around lake have small soil depths
                    soildepth_modflow = self.CWATM2modflow(decompress(soil_depth_temp)) + 0.05
                    soildepth_modflow[np.isnan(soildepth_modflow)] = 0
                else:
                    if verboseGW:
                        print('=> Topography minus soil depth is used as upper limit of groundwater. No correction of depth under lakes')
                    soildepth_modflow = self.CWATM2modflow(decompress(self.var.soildepth12))  + 0.05
                    soildepth_modflow[np.isnan(soildepth_modflow)] = 0
            else:  # topographic map is used as groundwater upper boundary
                if correct_depth_underlakes:  # we make a manual correction
                    if verboseGW:
                        print('=> Topography is used as upper limit of groundwater. Correcting depth under lakes. It can make ModFlow difficulties to converge')
                    waterBodyID_temp = loadmap('waterBodyID').astype(np.int64)
                    soil_depth_temp = np.where(waterBodyID_temp != 0, loadmap('depth_underlakes'), 0)
                    soildepth_modflow = self.CWATM2modflow(decompress(soil_depth_temp))
                    soildepth_modflow[np.isnan(soildepth_modflow)] = 0
                else:
                    if verboseGW:
                        print('=> Topography is used as upper limit of groundwater. No correction of depth under lakes')
                    soildepth_modflow = np.zeros((self.domain['nrow'], self.domain['ncol']), dtype=np.float32)


            # defining the top of the ModFlow layer
            self.layer_boundaries = np.empty((nlay + 1, self.domain['nrow'], self.domain['ncol']), dtype=np.float32)
            self.layer_boundaries[0] = topography - soildepth_modflow
            self.topography = topography.copy()
            # MODIFIED DOR FRIDMAN
            self.layer_boundaries[0] = np.where(np.isnan(self.layer_boundaries[0]), 0, self.layer_boundaries[0])

            # defining the bottom of the ModFlow layer iterate over nlayers
            
            for lyr in range(nlay):
                self.layer_boundaries[lyr + 1] = self.layer_boundaries[lyr] - thickness[lyr]
               
            
            # Allow below topography drainage; set as the minimum altitude across average elevation and sub-gridcell perecntile elevation
            if 'topo_percetile_modflow' in binding:
                prcntile_elev = "z_p10"
                if 'topo_percetile_prm' in binding:
                    prcntile_elev = cbinding('topo_percetile_prm')
                prcntile_elev_map = load_percentile_nc(self, 'topo_percetile_modflow', percentile=prcntile_elev, mask=None)
                self.drain_elevation = np.minimum(prcntile_elev_map, self.layer_boundaries[0])
                self.drain_elevation = np.where(self.drain_elevation <= self.layer_boundaries[1] + 1.0, self.layer_boundaries[1] + 1.0, self.drain_elevation) 

            else:
                self.drain_elevation = self.layer_boundaries[0].copy()
            
            if self.var.adjust_drainage_by_river:
                # if triggered - a dynamic waterlevel + bottom of channel is used to set the drainange in cells of main rivers
                # main rivers has at least width of I meters (default: I = 25)
                self.var.min_chan_width = globals.inZero.copy() + 25.
                if 'chanWidthThreshold' in binding:
                    self.var.min_chan_width = globals.inZero.copy() + loadmap('chanWidthThreshold')
                    chanDepth = np.where(self.var.chanWidth >= self.var.min_chan_width, self.var.chanDepth, 0.)
                    
                    # In the future - maybe to have inputs with higher resolution
                    chanDepth = self.CWATM2modflow(decompress(chanDepth))
                    if checkOption('includeWaterBodies'):
                        chanDepth = np.where(self.waterBodyID_modflow > 0., 0., chanDepth)
                    self.drain_elevation = self.drain_elevation - chanDepth
                    # Dynamic drainange values should be calculated based on water level and (constrained by topography - and
                    # add to drainage.
                    
            # saving soil thickness at modflow resolution to compute water table depth in postprocessing
            self.var.modflowtotalSoilThickness = soildepth_modflow

            # defining the initial water table map (it can be a hydraulic head map previously simulated)
            self.var.load_init_water_table = False
            if 'load_init_water_table' in binding:
                self.var.load_init_water_table = returnBool('load_init_water_table')
                
                
            if self.var.load_init_water_table:
                if verboseGW:
                    print('=> Initial water table depth is uploaded from ', cbinding('init_water_table'))
                watertable = cbinding('init_water_table')
                if watertable.split(".")[-1] == "npy": # case of initial conditions from ModFlow as npy
                    head = np.load(cbinding('init_water_table'))
                    head =  np.where(np.isnan(head), 0., head)             
                else: # case of initial conditions input parameter (scalar) or map (modflow resolution)
                    # MODIFIED DOR FRIDMAN
                    varList = parseArray(watertable, splt = ';')  # ['0.08', 'path...']
                    
                    emptyList = [None] * len(varList)
                    
                    # error raise if len(varList) < nlay or  >
                    for i in range(nlay):
                        emptyList[i] = self.CWATM2modflow(self, loadmap(varList[i]), fname = True)
                    head = np.array(emptyList)
            else:
                start_watertabledepth = load_aquifer_coeff(self, var = 'initial_water_table_depth',  nlay = nlay)

                start_watertabledepthIntFlag = False
                if is_float(parseArray(cbinding('initial_water_table_depth'), splt = ';')[0]):
                    start_watertabledepthIntFlag = True
                
                if start_watertabledepthIntFlag:
                    if verboseGW:
                        print('=> Water table depth is - ', start_watertabledepth, ' m at the begining')
                else:
                    if verboseGW:
                        print('=> The average water table depth is - ', np.nanmean(start_watertabledepth), ' m at the begining')
                # MODIFIED DOR FRIDMAN
                head = self.layer_boundaries[0:nlay] - start_watertabledepth          
            
            # Defining potential leakage under rivers and lakes or reservoirs - maps are cwatm resolution
            leakageriver_factor = 0
            if 'leakageriver_permea' in binding:
                self.var.leakageriver_factor = loadmap('leakageriver_permea')  # in m/day
            if verboseGW:                
                print('=> Leakage under rivers is ', self.var.leakageriver_factor, ' m/day')
            leakagelake_factor = 0
            if 'leakagelake_permea' in binding:
                self.var.leakagelake_factor = loadmap('leakagelake_permea')  # in m/day
            
            if verboseGW:
                print('=> Average leakage under lakes/reservoirs is ', np.nanmean(self.var.leakageriver_factor), ' m/day')
            
            # load specific storage
            if 'specific_storage' in binding:
                self.s_stor = load_aquifer_coeff(self = self, var = 'specific_storage', nlay = nlay, mask = self.modflow_basin[0])
            else:
                self.s_stor = np.where(self.modflow_basin, 0., 0.)

            # test if ModFlow pumping is used as defined in settings file
            Groundwater_pumping = False
            if 'Groundwater_pumping' in binding:
                self.var.GW_pumping = returnBool('Groundwater_pumping')
            
            if verboseGW:
                print('=> Groundwater pumping should be deactivated if includeWaterDemand is False')
           
           
            self.var.use_complex_solver_for_modflow = False
            if 'use_complex_solver_for_modflow' in option:
                if checkOption('use_complex_solver_for_modflow'):
                    self.var.use_complex_solver_for_modflow = True
           
            # MODIFIED BY DOR FRIDMAN
            
            '''
                ADD OPTIONS TO COLELCT RECHARGE IN A SPECFIC MODEL AREA
                E.G.,INFILITRATION TO OTHER GW-BASINS - E.G., THESE AREAS SHOULD NOT ALLOWED PUMPING
                
                
                THE MAP IS IN PERCENTS OF (1) RECHARGE
            '''
            
            # load map of recharge collection
            if 'collect_recharge' in binding:
                self.GWFlows_collectRchrg = load_aquifer_coeff(self = self, var = 'collect_recharge', nlay = nlay, mask = self.modflow_basin[0])
            
            # MODIFIED DOR FRIDMAN
            self.s_yieldCoeff = 1.
            if 'specific_yield_coeff' in binding:
                self.s_yieldCoeff = load_aquifer_coeff(self = self, var = 'specific_yield_coeff', nlay = nlay)[0]
            self.s_yield = self.porosity * self.s_yieldCoeff
            
            
            ## BUILD RECHARGE MASK - TOP LAYER
            self.var.rch_index = []
            rch_mask_from_file = np.copy(self.modflow_basin[0])
            #self.rch_mask = np.copy(self.modflow_basin[0]) #edit
            #self.rch_mask = np.copy(self.modflow_basin)

            for layer in range(nlay):
                index_modflowcell = 0
                for ir in range(self.domain['nrow']):
                    for ic in range(self.domain['ncol']):
                        if self.modflow_basin[0][ir][ic] == 1:  # & rch_mask_from_file[ir][ic] == 1:
                            #self.rch_mask[layer][ir][ic] = True
                            self.var.rch_index.append(index_modflowcell)
                        index_modflowcell += 1
            ## END BUILDING RECHARGE MASK
            
            
            if 'run_only_steady_state' in binding and returnBool('run_only_steady_state'):
                print("\n>>> NOTICE: MODFLOW-6 is running in STEADY STATE mode to calculate and save initial heads. Dynamic loops will be paused. <<<")
                from cwatm.hydrological_modules.groundwater_modflow.modflow_steady import run_standalone_steady_state
                run_standalone_steady_state(
                transient_instance=self,
                folder_out=modflow_directory_output,
                path_mf6dll=directory_mf6dll,
                nlay=nlay,
                nrow=nr,
                ncol=nc,
                rowsize=self.domain['rowsize'],
                colsize=self.domain['colsize'],
                layer_top=self.layer_boundaries[0],
                layer_bottom=self.layer_boundaries[1:],
                drain_elevation = self.drain_elevation,
                basin_mask=self.modflow_basin,
                confined_flags=self.confinedAquifer_flags,
                initial_head=head,
                ss_storage=self.s_stor,
                sy_yield=self.s_yield,
                verbose_gw=verboseGW
                )
            
            else:
                if self.var.GW_pumping:
                    self.var.correctPumpingDiscrepancy = False
                    if 'correctPumpingDiscrepancy' in binding:
                        self.var.correctPumpingDiscrepancy = returnBool('correctPumpingDiscrepancy')
                        
                    self.var.wells_index = []
                    if verboseGW:
                        print('=> THE PUMPING MAP SHOULD BE DEFINED (In transient.py ALSO LINE 420) BEFORE TO RUN THE MODEL AND BE THE SAME FOR ALL THE SIMULATION')
                    if 'pump_location' in binding:
                        # CHECK PUMP LOCATION
                        wells_mask_from_file = load_aquifer_coeff(self, var = 'pump_location', nlay = nlay).astype(np.int32) * self.modflow_basin
                    else:
                        wells_mask_from_file = np.copy(self.modflow_basin)


                    # creating a mask to set up pumping wells, TO DO MANUALLY HERE OR TO IMPORT AS A MAP, because running the model with zero pumping rates every cells is consuming

                    self.wells_mask = np.copy(self.modflow_basin)
                    #self.var.wells_index = []

                    for layer in range(nlay):
                        index_modflowcell = 0
                        for ir in range(self.domain['nrow']):
                            for ic in range(self.domain['ncol']):

                                """
                                if layer<nlay-1:
                                    wells_mask_from_file[layer][ir][ic] = 0
                                # TEST only allowing pumping in last layer
                                """

                                if self.modflow_basin[layer][ir][ic] == 1 & wells_mask_from_file[layer][ir][ic] == 1: #and int((ir+5.0)/10.0) - (ir+5.0)/10.0 == 0 and int((ic+5.0)/10.0) - (ic+5.0)/10.0 == 0:
                                    #if ir != 0 and ic != 0 and ir != self.domain['nrow']-1 and ic != self.domain['ncol']-1:
                                    self.wells_mask[layer][ir][ic] = True
                                    self.var.wells_index.append(index_modflowcell)
                                else:
                                    self.wells_mask[layer][ir][ic] = False
                                index_modflowcell += 1
                                
                ## END BUILDING WELLS_MASK
                
                
                    
                    self.var.availableGWStorageFraction = 0.7
                    
                    if 'water_table_limit_for_pumping' in binding:
                        # if available storage is too low, no pumping in this cell
                        self.var.availableGWStorageFraction = loadmap('water_table_limit_for_pumping')  # if 85% of the ModFlow cell is empty, we prevent pumping in this cell
                    if verboseGW:
                        print('=> Pumping in the ModFlow layer is prevented if water table is under ', 1 - self.var.availableGWStorageFraction, ' of the layer capacity')
                    
                    
                        # PLACE THIS AT THE VERY BOTTOM OF YOUR groundwater_modflow.initial() METHOD:
                
                    # MODIFIED DOR FRIDMAN (bottom=self.layer_boundaries[1:],) (specific_yield = s_yield)
                    
                    # initializing the ModFlow6 model
                    self.modflow = ModFlowSimulation(
                        'transient',
                        modflow_directory_output,
                        directory_mf6dll,
                        ndays=globals.dateVar['intEnd'],
                        timestep=self.var.modflow_timestep,
                        specific_storage= self.s_stor,
                        specific_yield=self.s_yield,
                        nlay=nlay,
                        nrow=self.domain['nrow'],
                        ncol=self.domain['ncol'],
                        rowsize=self.domain['rowsize'],
                        colsize=self.domain['colsize'],
                        top=self.layer_boundaries[0],
                        bottom=self.layer_boundaries[1:],
                        drain_elevation = self.drain_elevation,
                        basin=self.modflow_basin,
                        confined_only = self.confinedAquifer_flags,
                        head=head,
                        topography=self.layer_boundaries[0],
                        permeability=self.permeability,
                        permeability_vertical=self.permeability_v,
                        load_from_disk=returnBool('load_modflow_from_disk'),
                        setpumpings=True,
                        pumpingloc=self.wells_mask,
                        verbose=verboseGW,
                        complex_solver=self.var.use_complex_solver_for_modflow)



                else: # no pumping
                
                    self.wells_mask = self.modflow_basin.copy()
                    # initializing the ModFlow6 model
                    self.modflow = ModFlowSimulation(
                        'transient',
                        modflow_directory_output,
                        directory_mf6dll,
                        ndays=globals.dateVar['intEnd'],
                        timestep=self.var.modflow_timestep,
                        specific_storage=self.s_stor,
                        specific_yield=self.s_yield,
                        nlay=nlay,
                        nrow=self.domain['nrow'],
                        ncol=self.domain['ncol'],
                        rowsize=self.domain['rowsize'],
                        colsize=self.domain['colsize'],
                        top=self.layer_boundaries[0],
                        bottom=self.layer_boundaries[1:],
                        drain_elevation = self.drain_elevation,
                        basin=self.modflow_basin,
                        confined_only = self.confinedAquifer_flags,
                        head=head,
                        topography=self.layer_boundaries[0],
                        permeability=self.permeability,
                        permeability_vertical=self.permeability_v,
                        load_from_disk=returnBool('load_modflow_from_disk'),
                        setpumpings=False,
                        pumpingloc=None,
                        verbose=verboseGW,
                        complex_solver=self.var.use_complex_solver_for_modflow)

               
                # MODIF LUCA
                #self.corrected_cwatm_cell_area = self.get_corrected_cwatm_cell_area()
                #self.corrected_modflow_cell_area = self.get_corrected_modflow_cell_area()

                # MODIF LUCA
                # initializing arrays
                self.var.capillar = globals.inZero.copy()
                self.var.baseflow = globals.inZero.copy()
                self.var.depth = globals.inZero.copy()
                self.var.balance_gw = globals.inZero.copy()
                
                self.var.modflow_watertable = np.copy(head)  # water table will be also saved at modflow resolution
                
                 # sumed up groundwater recharge for the number of days
                self.var.sumed_sum_gwRecharge = globals.inZero
                self.var.modflow_compteur = 0  # Usefull ?
                
                # initial water table map is converting into CWatM map
                
                self.var.head = compressArray(self.modflow2CWATM(head[0]))
                self.var.head = np.array([self.var.head] * nlay)
                for lyr in range(nlay)[1:]:
                    self.var.head[lyr,:] = compressArray(self.modflow2CWATM(head[lyr]))
           
                self.var.writeerror = False
                if 'writeModflowError' in binding:
                    self.var.writeerror = returnBool('writeModflowError')
                if self.var.writeerror:
                    # This one is to check model's water balance between ModFlow and CwatM exchanges
                    # ModFlow discrepancy for each time step can be extracted from the listing file (.lst file) at the end of the simulation
                    # as well as the actual pumping rate applied in ModFlow (ModFlow automatically reduces the pumping rate once the ModFlow cell is almost saturated)
                    print('=> ModFlow-CwatM water balance is checked\nModFlow discrepancy for each time step can be extracted from the listing file (.lst file) at the end of the simulation,\nas well as the actual pumping rate applied in ModFlow (ModFlow automatically reduces the pumping rate once the ModFlow cell is almost saturated)')
                else:
                    print('=> ModFlow-CwatM water balance is not checked\nModFlow discrepancy for each time step can be extracted from the listing file (.lst file) at the end of the simulation,\nas well as the actual pumping rate applied in ModFlow (ModFlow automatically reduces the pumping rate once the ModFlow cell is almost saturated)')

                # then, we got the initial groundwater storage map at ModFlow resolution (in meter)

                # MODIFIED DOR FRIDMAN
                self.groundwater_storage_n_layer = head.copy()
                
                
                for lyr in range(nlay):
                
                    '''
                     Calculate storage as the flow from storage if head was to drop to zero. 
                     Following 'Documentaton for the MODFLOW 6 Groundwater Flow Model | Ch. 5 of Section A, Groundwater, Book6, Modeling Techniques'
                     https://pubs.usgs.gov/tm/06/a55/tm6a55.pdf
                     
                     Q_sto =  Q_ss + Q_sy
                     
                     Q_ss = SS * A * (TOP - BOT) * (SF * ht) : SFt+1 * ht+1 = 0
                     Q_sy = SY * A * (TOP - BOT) * (SF)  : SFt+1 = 0    
                     
                     Q_sto = [A * (TOP -BOT) * SF] * [SS * ht + Sy]
                     
                     Whereas:
                     Q - flow of water from storage in m^3
                     A - grid cell area
                     SS\SY - specific storage/specific yield
                     TOP/BOT - top/bottom of the aquifer in meters
                     SF - Saturation fraction as calculated by: self.calcSaturatedCellFraction(lyr = lyr, head = head)
                     ht - head
                     
                     Here we calculate storage in meters so we do not account for the A (grid cell area). So:
                     Q_sto = [(TOP -BOT) * SF] * [SS * ht + Sy]                 
                     

                    '''
                    
                    satFrac = self.calcSaturatedCellFraction(lyr = lyr, head = head)

                    self.groundwater_storage_n_layer[lyr] = (self.layer_boundaries[lyr] - self.layer_boundaries[lyr + 1]) * satFrac * (self.s_stor[lyr] * head[lyr] + self.s_yield[lyr] * (self.confinedAquifer_flags[lyr] > 0))
                    #self.groundwater_storage_n_layer[lyr] = (self.layer_boundaries[lyr] - self.layer_boundaries[lyr + 1]) * satFrac * (self.s_stor[lyr] * (head[lyr]-self.layer_boundaries[lyr + 1]) + self.s_yield[lyr] * (self.confinedAquifer_flags[lyr] > 0))
                # converting the groundwater storage from ModFlow to CWatM map (in meter)
                self.var.groundwater_storage_total = compressArray(self.modflow2CWATM(np.nansum(self.groundwater_storage_n_layer, axis = 0)))  
                
                 
                # actual pumping output - Zero if no pumping
                self.var.modfPumpingM_actual = globals.inZero.copy()
               
                # calculate groundwater storage available for CWATM
                self.gwavailable_n_lyrs = head.copy()
                for lyr in range(nlay):
                    satFrac = self.calcSaturatedCellFraction(lyr = lyr, head = head)
                    satFrac_min = self.var.availableGWStorageFraction * self.modflow.basin[lyr]
                    head_min = self.layer_boundaries[lyr + 1] + satFrac_min * (self.layer_boundaries[lyr] - self.layer_boundaries[lyr + 1])
                    
                    self.gwavailable_n_lyrs[lyr] =  (self.layer_boundaries[lyr] - self.layer_boundaries[lyr + 1]) * ((self.s_stor[lyr] * np.maximum(head[lyr] * satFrac - head_min * satFrac_min ,0)) + (self.s_yield[lyr] * np.maximum(satFrac - satFrac_min, 0)) * (self.confinedAquifer_flags[lyr] > 0))
                    self.gwavailable_n_lyrs[lyr] = np.where(self.gwavailable_n_lyrs[lyr]  < 0, 0., self.gwavailable_n_lyrs[lyr])
                    
                self.var.groundwater_storage_available = compressArray(self.modflow2CWATM(np.nansum(self.gwavailable_n_lyrs  * self.wells_mask, axis = 0)))  # used in water demand module then
                self.groundwater_storage_available = np.nansum(self.gwavailable_n_lyrs * self.wells_mask, axis = 0)
                
                
                # self.modflowGroupByCWATM(self.groundwater_storage_available) --> SEE IF CAN BE FIXED
                self.gwAvail_weights = np.minimum(divideArrays(self.groundwater_storage_available, self.CWATM2modflow(decompress(self.var.groundwater_storage_available))), 1.0)

                # permeability need to be translated into CWatM map to caompute leakage from surface water bodies & to condition infiltration into aquifer (e.g., replace under soil impervious surface share
                self.var.permeability = compressArray(self.modflow2CWATM(self.permeability[0])) * self.coefficient
                self.var.permeability_v = compressArray(self.modflow2CWATM(self.permeability_v[0])) * self.coefficient
                 # export permeability of top layer to CWatM to replace impervious surface share.
                #self.var.permeability_top = compressArray(self.modflow2CWATM(self.permeability_v[0]))
        else:

            ii = 1
            #print('=> ModFlow coupling is not used')
            
    
            
    def dynamic(self):
  
        # Sumed recharge is re-initialized here for water budget computing purpose
        self.var.modfPumpingM_actual = globals.inZero.copy()  # compressArray(self.modflow2CWATM(self.permeability[0]*0))
        
        

        if self.var.modflow_timestep == 1 or ((dateVar['curr'] - int(dateVar['curr'] / self.var.modflow_timestep) * self.var.modflow_timestep) == 1):  # if it is the first step of the week,months...
            # ? Can the above line be replaced with: (dateVar['curr']  % self.var.modflow_timestep) == 0:
            # setting sumed up recharge again to 7 (or 14 or 30...), will be sumed up for the following 7 days (or 14 or 30...)
            self.var.sumed_sum_gwRecharge = 0

        # Adding recharge of the day to the weekly (or bi-weekly, or monthly...) sum
        self.var.sumed_sum_gwRecharge = self.var.sumed_sum_gwRecharge + self.var.sum_gwRecharge

        # Every modflow timestep (e.g. 7,14,30... days)
        # print('dateVarcurr', dateVar['curr'])
        if dateVar['curr'] == 1 or (dateVar['curr'] % self.var.modflow_timestep) == 0:
            
        
            self.var.modflow_compteur += 1

            # converting the CWatM recharge into ModFlow recharge (in meter)
            # we avoid recharge on saturated ModFlow cells, thus CWatM recharge is concentrated  on unsaturated cells
            corrected_recharge = np.where(self.var.capriseindex == 1, 0,
                                          self.var.sumed_sum_gwRecharge / (1 - self.var.capriseindex))
            groundwater_recharge_modflow = self.CWATM2modflow(decompress(corrected_recharge, nanvalue=0),
                                                              correct_boundary=False)
            groundwater_recharge_modflow = np.where(self.var.modflow_watertable - self.layer_boundaries[0] >= 0,
                                                    0, groundwater_recharge_modflow)
        
        # MODIFIED DOR FRIDMAN
        nlay_dyn = self.modflow.basin.shape[0]
     
        # converting the CWatM recharge into ModFlow recharge (in meter)
        # we avoid recharge on saturated ModFlow cells, thus CWatM recharge is concentrated  on unsaturated cells
        corrected_recharge = np.where(self.var.capriseindex == 1, 0, self.var.sum_gwRecharge / (1 - self.var.capriseindex))
        
        groundwater_recharge_modflow = self.CWATM2modflow(decompress(corrected_recharge, nanvalue=0), correct_boundary=False)
        
        if 'collect_recharge' in binding:
            rechargeOtherGWBasins = groundwater_recharge_modflow * self.GWFlows_collectRchrg
            # collect recharge based on maximum percent for each layer
            groundwater_recharge_modflow -= np.nanmax(rechargeOtherGWBasins, axis = 0)
            
            self.var.sum_gwRechargeExported = compressArray(self.modflow2CWATM(np.nansum(rechargeOtherGWBasins, axis = 0)))
        
        groundwater_recharge_modflow = np.where(self.var.modflow_watertable - self.layer_boundaries[0] >= 0,
                                                0, groundwater_recharge_modflow)
        

        # recharge only for the top layer
        zero_recharge = np.where(self.modflow.basin == 1, 0, 0)
        groundwater_recharge_modflow[1:, :, :] = zero_recharge[1:, :, :]
        # MODIFIED DOR FRIDMAN                                                
        #self.var.sum_gwRecharge_adjusted = compressArray(self.modflow2CWATM(np.nansum(groundwater_recharge_modflow, axis = 0)))
        # give the information to ModFlow
        # cancel recharge in dryModflowCells  with negative storage - e.g., head < bottom_of_cell - recharged that is deleted will be accounted as
        # rejected recharge in the next time-step in soil.py
        dryModflowCells = (self.modflow.decompress(self.modflow.head.astype(np.float32)) - self.layer_boundaries[1:, :,
                                                                                           :]) < 0

        # Correct treatment of multiple layers
        groundwater_recharge_modflow = np.where(np.nansum(dryModflowCells, axis=0) == nlay_dyn, 0,
                                                groundwater_recharge_modflow)

        self.modflow.set_recharge(groundwater_recharge_modflow)
        #print(np.nanmean(- groundwater_recharge_modflow))
        
        #print(dir(self.modflow))

        #print('transient.py', 'np.sum(self.modflow.recharge)', np.sum(self.modflow.recharge))
        actual_recharge = self.modflow.recharge / ( self.domain['rowsize'] * self.domain['colsize'] )

        actual_recharge_modflow_array = np.zeros((nlay_dyn, self.domain['nrow'], self.domain['ncol']), dtype=np.float32)

        # modified for layers
        active_cells = np.nansum(self.modflow.basin) / nlay_dyn
        #print('transient.py', 'active_cells', active_cells)
        lyr = 0
        # apply separately for each layer
        #wghts = actual_recharge[int(lyr * active_cells):int((lyr + 1) * active_cells - 1)] #[0, active_cells-1] #Should the minus 1 be removed?
        wghts = actual_recharge[int(lyr * active_cells):int((lyr + 1) * active_cells)]
        #print('transient.py', 'len(wghts)', len(wghts))

        #rch_index = self.var.rch_index[int(lyr * active_cells):int((lyr + 1) * active_cells - 1)]
        rch_index = self.var.rch_index[int(lyr * active_cells):int((lyr + 1) * active_cells)]
        actual_recharge_modflow_array[lyr, :, :] = np.bincount(rch_index, weights=wghts,
                                        minlength=int(self.modflow.nrow * self.modflow.ncol)).reshape((self.modflow.nrow, self.modflow.ncol))

        self.var.sum_gwRecharge_actualM = compressArray(self.modflow2CWATM(actual_recharge_modflow_array[0]))
        #print('transient.py', 'np.sum(self.var.sum_gwRecharge_actualM*self.var.cellArea)', np.sum(self.var.sum_gwRecharge_actualM* self.var.cellArea))
        self.var.prefFlow_GW = divideValues(self.var.sum_prefFlow, self.var.sum_prefFlow + self.var.sum_perc3toGW) * self.var.sum_gwRecharge_actualM
        self.var.perc3toGW_GW = divideValues(self.var.sum_perc3toGW,
                                            self.var.sum_prefFlow + self.var.sum_perc3toGW) * self.var.sum_gwRecharge_actualM

        self.var.rejected_recharge_previous_day = np.maximum(0, self.var.sum_gwRecharge - self.var.sum_gwRecharge_actualM)
        #print('transient.py, rejected recharge', np.nansum(self.var.rejected_recharge_previous_day * self.var.cellArea))
        
        ## Dynamic Drainage
        if self.var.adjust_drainage_by_river:
            
            # Calculate water level in channel (no floodplain) - see waterquality1.py
            dis = np.where(self.var.discharge < 0.0001, 0.0001, self.var.discharge)
            width = 1.22 * (dis ** 0.557)
            crossArea = 0.4148 * dis ** 0.898
            chanCrossSectionArea = np.where(crossArea < self.var.totalCrossSectionArea, crossArea, self.var.totalCrossSectionArea)
            chanWaterDepth = np.where(self.var.chanWidth >= self.var.min_chan_width, chanCrossSectionArea / width, 0.)
            
            chanWaterDepth = self.CWATM2modflow(decompress(chanWaterDepth))
            if checkOption('includeWaterBodies'):
                chanWaterDepth = np.where(self.waterBodyID_modflow > 0., 0., chanWaterDepth)
                
            # add water level to elevation , make sure does not exceed top of the aquifer
            drain_elevation_dyn = self.drain_elevation + chanWaterDepth
            drain_elevation_dyn = np.where(drain_elevation_dyn > self.layer_boundaries[0], self.layer_boundaries[0], drain_elevation_dyn)
            self.modflow.set_drainage(dynamicDrainElevation = drain_elevation_dyn)
        
        ## INSTALLING WELLS
        if self.var.GW_pumping:
            ## Groundwater demand from CWatM installs wells in each Modflow cell
            # Groundwater pumping demand from the CWatM waterdemand module, will be decompressed to 2D array
            # CWatM 2D groundwater pumping array is converted into Modflow 2D array
            # Pumping is given to ModFlow in m3 and < 0
            #self.modflow.verbose = True
            if self.modflow.verbose:
                print('mean modflow pumping [m]: ', np.nanmean(self.var.modfPumpingM))
            groundwater_abstraction = - self.CWATM2modflow(decompress(self.var.modfPumpingM)) * domain['rowsize'] * domain['colsize'] # BURGENLAND * 100 AND L428

            # MODIFIED DOR FRIDMAN - ASSUMES ALL LAYER MASKS ARE THE SAME AND THAT EVERY CELL HAS A PUMP
            # create initial groundwater abstraction
            # groundwater_abstraction2 allowed only from valid cells
            wellsMask = (np.nansum(self.wells_mask, axis=0) > 0)
            groundwater_abstraction2 = np.array([groundwater_abstraction * wellsMask] * nlay_dyn)

            self.gwAvail_weights = np.minimum(divideArrays(self.groundwater_storage_available, self.CWATM2modflow(decompress(self.var.groundwater_storage_available))), 1.0)
            groundwater_abstraction2 = groundwater_abstraction2 * self.gwAvail_weights

            # correct groundwater discrepancy
            if self.var.correctPumpingDiscrepancy:
                '''
                Correct pumping discrepancy between MODFLOW and CWatM. Due to conversion errors, and inaccurate storage estiamtes - it often occurs that CWatM allocated 
                more groundwater for consumption relative to the volume that is actually being pumped. So np.nansum(self.var.modfPumpingM) > np.nansum(self.var.modfPumpingM_actual)
                
                The correction suggested below, inflate requested pumping in all grid cells by a constant, calculated as CWatM pumping request divided by Modflow adjusted pumping request. 
                The resulting pumping reduces the discrepancy between the two, but causes a spatial mismtach between demand and pumping locations. Therefore, this practice is discourage in 
                coarse resolution appliactions.
                
                User can set it on by setting correctPumpingDiscrepancy = True in the Settings file.
                '''
                groundwater_abstraction2 =  groundwater_abstraction2 * np.nansum(groundwater_abstraction)/ np.nansum(groundwater_abstraction2)

            
            # calculate available water per layer and split abstraction between layers. 
            StorageInAbstractionCells = self.gwavailable_n_lyrs * wellsMask  
            
            proportional_groundwater_storage = StorageInAbstractionCells / np.nansum(StorageInAbstractionCells, axis = 0)
            proportional_groundwater_storage = np.where(np.isnan(proportional_groundwater_storage), 0,
                                                        proportional_groundwater_storage)

            groundwater_abstraction2 = groundwater_abstraction2 * proportional_groundwater_storage
            # update  groundwater abstraction layers
            # give the information to ModFlow

            self.modflow.set_groundwater_abstraction(groundwater_abstraction2)

            # groundwater_abstraction = groundwater_abstraction / 100
            self.groundwater_abstraction2 =  groundwater_abstraction2.copy()
            #self.var.modfPumpingM = globals.inZero.copy() 
            
            
        # running ModFlow
        self.modflow.step()
        #self.modflow.finalize()

        # MODIF LUCA
        # extracting the new simulated hydraulic head map
        head = self.modflow.decompress(self.modflow.head.astype(np.float32))
    
        # MODIF LUCA
        if self.var.writeerror:
            # copying the previous groundwater storage at ModFlow resolution (in meter)
            groundwater_storage_n_layer0 = np.nansum(self.groundwater_storage_n_layer, axis = 0)  # for water balance computation; groundwater_storage_n_layer[0] -> groundwater_storage_top_layer
        
        # MODIFIED DOR FRIDMAN
        # computing the new groundwater storage map at ModFlow resolution (in meter)
        self.groundwater_storage_n_layer = head.copy()
        for lyr in range(nlay_dyn): 
            satFrac = self.calcSaturatedCellFraction(lyr = lyr, head = head)
            self.groundwater_storage_n_layer[lyr] = (self.layer_boundaries[lyr] - self.layer_boundaries[lyr + 1]) * satFrac * (self.s_stor[lyr] * head[lyr] + self.s_yield[lyr] * (self.confinedAquifer_flags[lyr] > 0))
        old_groundwater_storage_total = self.var.groundwater_storage_total.copy()
        self.var.groundwater_storage_total = compressArray(self.modflow2CWATM(np.nansum(self.groundwater_storage_n_layer, axis = 0)))

        self.gwavailable_n_lyrs = head.copy()
        for lyr in range(nlay_dyn):
            satFrac = self.calcSaturatedCellFraction(lyr = lyr, head = head)
            satFrac_min = self.var.availableGWStorageFraction
            head_min = self.layer_boundaries[lyr + 1] + satFrac_min * (self.layer_boundaries[lyr] - self.layer_boundaries[lyr + 1])

            self.gwavailable_n_lyrs[lyr] =  (self.layer_boundaries[lyr] - self.layer_boundaries[lyr + 1]) * ((self.s_stor[lyr] * np.maximum(head[lyr] * satFrac - head_min * satFrac_min ,0)) + (self.s_yield[lyr] * np.maximum(satFrac - satFrac_min, 0)) * (self.confinedAquifer_flags[lyr] > 0))
            self.gwavailable_n_lyrs[lyr] = np.where(self.gwavailable_n_lyrs[lyr] < 0, 0. , self.gwavailable_n_lyrs[lyr])
        
        wellsMask = (np.nansum(self.wells_mask, axis = 0) > 0)
        # calculate groundwater storage available for MODFLOW & gwAvailable allocation weights
        self.groundwater_storage_available = np.nansum(self.gwavailable_n_lyrs  * wellsMask, axis = 0)
        self.var.groundwater_storage_available = compressArray(self.modflow2CWATM(np.nansum(self.gwavailable_n_lyrs  * wellsMask, axis = 0)))  # used in water demand module then

        
        #assert self.permeability.ndim == 3
        
        # computing the groundwater outflow by re-computing water outflowing the aquifer through the DRAIN ModFlow package
        
        if checkOption('CapillarRise'):
            # If percentileElevation is enabled - allow calculation of drainage based on sub-grid dem percentiles
            groundwater_outflow  = np.where(head[0] - self.layer_boundaries[0] > 0, head[0] - self.layer_boundaries[0], 0.) * self.coefficient * self.permeability[0]
        else:
            groundwater_outflow = head[0] - head[0]
        # For the next step, it will prevent recharge where ModFlow cells are saturated, even if there is no capillary rise (where h==topo)
        # here using topography makes sense - as we look for complete 100% saturation
        groundwater_outflow2 = np.where(head[0] - self.layer_boundaries[0] >= 0, 1.0, 0.0) 
        #print('groundwater_outflow', np.nansum(groundwater_outflow), (groundwater_outflow<0).any())
        # MODIF LUCA
        # capillary rise and baseflow are allocated in fucntion of the river percentage of each ModFlow cell
        capillar = groundwater_outflow * (1 - self.var.channel_ratio)  # We are still in ModFlow coordinate
        baseflow = groundwater_outflow * self.var.channel_ratio

        # MODIF DOR & MIKHAIL - GET MODFLOW PUPMING 
        if self.var.GW_pumping:
            # extracting actual ModFlow pumping
            actual_pumping = self.modflow.actualwell_rate.astype(np.float32)
            ### Doesnot work for multiple layers
            # the size of actual pumping corresponds to the number of wells is masked array 'wellsloc'

            actual_pumping_modflow_array = np.zeros((nlay_dyn, self.domain['nrow'], self.domain['ncol']), dtype=np.float32)

            # modified for layers
            active_cells = np.nansum(self.modflow.basin) / nlay_dyn
            for lyr in range(nlay_dyn):
                # apply separately for each layer 
                #wghts = actual_pumping[int(lyr * active_cells):int((lyr + 1) * active_cells - 1)]
                wghts = actual_pumping[int(lyr * active_cells):int((lyr + 1) * active_cells)]
                #wells_index = self.var.wells_index[int(lyr * active_cells):int((lyr + 1) * active_cells - 1)]
                wells_index = self.var.wells_index[int(lyr * active_cells):int((lyr + 1) * active_cells)]
                actual_pumping_modflow_array[lyr, :, :] = np.bincount(wells_index, weights=wghts,
                                           minlength=int(self.modflow.nrow * self.modflow.ncol)).reshape((self.modflow.nrow, self.modflow.ncol))
            self.var.modfPumpingM_actual = -compressArray(self.modflow2CWATM(np.nansum(actual_pumping_modflow_array, axis = 0)) / (domain['rowsize'] * domain['colsize']))
            #print(np.nansum(actual_pumping_modflow_array))
            #print(np.nansum(self.var.modfPumpingM_actual * self.var.cellArea))

        if self.var.writeerror:
            # Check the water balance: recharge = capillary + baseflow + storage change
            modflow_cell_area = self.domain['rowsize'] * self.domain['colsize']  # in m², for water balance computation
           
            if self.var.GW_pumping:
                mid_gwflow = np.nansum(((np.nansum(groundwater_recharge_modflow, axis = 0) + capillar + baseflow + np.nansum(self.groundwater_storage_n_layer, axis = 0) + groundwater_storage_n_layer0) * modflow_cell_area - np.nansum(groundwater_abstraction2, axis = 0)) / 2)  # in m3, for water 
                Budget_ModFlow_error = np.round(100 * (np.nansum((np.nansum(groundwater_recharge_modflow, axis = 0) - capillar - baseflow -
                                                                                              (np.nansum(self.groundwater_storage_n_layer, axis = 0) - groundwater_storage_n_layer0)) * modflow_cell_area + np.nansum(groundwater_abstraction2, axis = 0)) /
                                                                                   mid_gwflow), 2)
            else:
                mid_gwflow = np.nansum((np.nansum(groundwater_recharge_modflow, axis = 0) + capillar + baseflow + np.nansum(self.groundwater_storage_n_layer, axis = 0) + groundwater_storage_n_layer0) * modflow_cell_area / 2)  # in m3, for water balance computation
                Budget_ModFlow_error = np.round(100 * (np.nansum((np.nansum(groundwater_recharge_modflow, axis = 0) - capillar - baseflow -
                                                                                              (np.nansum(self.groundwater_storage_n_layer, axis = 0) - groundwater_storage_n_layer0)) * modflow_cell_area) /
                                                                                   mid_gwflow), 2)
            #print('ModFlow discrepancy : ', Budget_ModFlow_error, ' % (if pumping, it considers pumping demand is satisfied)')

            # converting flows from ModFlow to CWatM domain
            sumModFlowout = np.nansum((capillar + baseflow) * modflow_cell_area) # m3, for water balance computation
            sumModFlowin = np.nansum(groundwater_recharge_modflow * modflow_cell_area)  # m3, for water balance computation
            
        self.var.capillar = compressArray(self.modflow2CWATM(capillar))
        self.var.baseflow = compressArray(self.modflow2CWATM(baseflow))
        change_in_gw_storage = self.var.groundwater_storage_total - old_groundwater_storage_total

        self.var.balance_gw = \
            self.var.prefFlow_GW + self.var.perc3toGW_GW \
            - self.var.capillar - self.var.baseflow - self.var.modfPumpingM_actual \
            - change_in_gw_storage

        self.var.balance_gw *= self.var.cellArea

        #print('balance_gw', np.nansum(self.var.balance_gw))
        #print('prefFlow_GW', np.nansum(self.var.prefFlow_GW*self.var.cellArea))
        #print('perc3toGW_GW', np.nansum(self.var.perc3toGW_GW*self.var.cellArea))
        #print('capillar', np.nansum(self.var.capillar*self.var.cellArea))
        #print('baseflow', np.nansum(self.var.baseflow*self.var.cellArea))
        #print('modfPumpingM_actual', np.nansum(self.var.modfPumpingM_actual*self.var.cellArea))
        #print('change_in_gw_storage', np.nansum(change_in_gw_storage*self.var.cellArea))

        #print('drainage', np.nansum(self.modflow.get_drainage()))


        # computing saturated fraction of each CWatM cells (where water table >= soil bottom)
        self.var.capriseindex = compressArray(self.modflow2CWATMbis(groundwater_outflow2))  # initialized in landcoverType module, self.var.capriseindex is the fraction of saturated ModFlow cells in each CWatM cell

        # updating water table maps both at CWatM and ModFlow resolution
        # MODIFIED DOR FRIDMAN
        
        # Save SWL
        self.var.depth_to_water = compressArray(self.modflow2CWATM(self.topography - head[0]))

        for lyr in range(nlay_dyn):
            setattr(self.var, 'head' + str(lyr), compressArray(self.modflow2CWATM(head[lyr])))
            setattr(self.var, 'gwdepth' + str(lyr), compressArray(self.modflow2CWATM(self.layer_boundaries[lyr] - head[lyr])))
        

        
      
        '''
        if 'gw_depth_observations' in binding:
            self.var.gwdepth_difference_sim_obs = self.var.gwdepth - self.var.gwdepth_observations
        if 'gw_depth_sim_obs' in binding:
            self.var.gwdepth_adjusted = np.maximum(self.var.gwdepth - self.var.gwdepth_adjuster, 0)
            head_adjusted = self.layer_boundaries[0] - self.CWATM2modflow(decompress(self.var.gwdepth_adjusted))
            self.var.modflow_head_adjusted = np.copy(head_adjusted)
        '''
        self.var.modflow_watertable = np.copy(head)
        self.var.modflow_watertable0 = np.copy(head[0])
        
        # if outputs ARE WISHED - DON'T USE FIXED INDICES - USE loop over lyr
        #self.var.modflow_depth0 = self.layer_boundaries[0]-head[0]
        #self.var.modflow_depth1 = self.layer_boundaries[0]-head[1]
        
        ''' SAVE INIT MODFLOW '''
        self.var.save_init_water_table = False
        if 'save_init_water_table' in binding:
            self.var.save_init_water_table = returnBool('save_init_water_table')

        if self.var.save_init_water_table:
            initdates = cbinding('StepInit').split()
            datetosaveInit(initdates,dateVar['dateBegin'],dateVar['dateEnd'])
            # save initial
            if  dateVar['curr'] in dateVar['intInit']:
                saveFile = cbinding('initSave') + "_modflow_" + "%02d%02d%02d.npy" % (dateVar['currDate'].year, dateVar['currDate'].month, dateVar['currDate'].day)
                np.save(saveFile, head)
                print("The init file:" + saveFile + " was saved")
        
        if self.var.writeerror:
            #  saving modflow discrepancy, it will be written a text file at the end of the simulation
            self.var.modflowdiscrepancy = Budget_ModFlow_error
            ## CONTINUE  FROM HERE
            ## ALSO ADD TO SOIL/LANDCOVER/WATER DEMAND -- THINGS THAT ARE NEEDED
            
            # computing the total recharge rate provided by CWatM for this time step (in m3)
            #total_recharge_m3_cwatm = (self.var.sum_gwRecharge * self.var.cellArea).sum()  # m3, for water balance computation
            #total_recharge_m3_cwatm = (self.var.sum_gwRecharge_adjusted * self.var.cellArea).sum()  # m3, for water balance computation
            
            
            #print('ModFlow-CWatM input conversion error : ', np.round(100 * (total_recharge_m3_cwatm - sumModFlowin)/sumModFlowin, 2), ' %')
            #print('ModFlow-CWatM output conversion error : ', np.round(100 * (np.nansum((self.var.capillar+self.var.baseflow)*self.var.cellArea)-sumModFlowout)/sumModFlowout, 2), ' %')

            # Check crossed models:
            #print('ModFlow discrepancy crossed: ', np.round(100 * (total_recharge_m3_cwatm - np.nansum((capillar + baseflow +
            #                                                                                             (np.nansum(self.groundwater_storage_n_layer, axis = 0) - groundwater_storage_n_layer0)) * modflow_cell_area)) /
            #                                                mid_gwflow, 2), ' %')
            # Writing ModFlow discrepancies at the end of simulation:
            if dateVar['currDate'] == dateVar['dateEnd']:
                if self.var.writeerror:
                    discrep_filename = cbinding('PathOut') + '/' + 'ModFlow_DiscrepancyError.txt'
                    discrep_file = open(discrep_filename, "w")
                    sum_modflow_errors = 0
                    threeshold_modflow_error = 0.01  # in percentage

                    for tt in range(dateVar['intEnd']):
                        if self.var.modflowdiscrepancy > threeshold_modflow_error:  # if error is higer than threeshold in %, we print it.
                            discrep_file.write(
                                "ModFlow stress period " + str(tt + 1) + " : percentage error in ModFlow is ")
                            discrep_file.write(str(self.var.modflowdiscrepancy))
                            discrep_file.write("\n")
                            sum_modflow_errors += 1
                    if sum_modflow_errors == 0:
                        discrep_file.write(
                            "ModFlow error was always below " + str(
                                threeshold_modflow_error) + ' % during the simulation')
                    discrep_file.close()


