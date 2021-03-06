import numpy as np
import os
# MODIF LUCA
#from cwatm.management_modules.data_handling import globals, cbinding, loadmap, returnBool
from  cwatm.management_modules.data_handling import *
from cwatm.hydrological_modules.groundwater_modflow.modflow6 import ModFlowSimulation
# impotlib to install libraries on the fly if needed e.g. rasterio
import importlib



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


class groundwater_modflow:
    def __init__(self, model):
        self.var = model.var
        self.model = model

    def get_corrected_modflow_cell_area(self):
        return np.bincount(
            self.indices['ModFlow_index'],
            weights=np.invert(self.var.mask.astype(np.bool)).ravel()[self.indices['CWatM_index']] * self.indices['area'],
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
            variable.ravel()[self.indices['CWatM_index']] * self.indices['area'],
            minlength=self.domain['nrow'] * self.domain['ncol']
        ) / modflow_cell_area).reshape((self.domain['nrow'], self.domain['ncol'])).astype(variable.dtype)
        return array

    def modflow2CWATM(self, variable, correct_boundary=False):
        """Converting flow [L/T] from 2D ModFLow map to 2D CWatM map"""
        variable_copy = variable.copy()
        variable_copy[self.modflow.basin == False] = 0
        assert not (np.isnan(variable_copy).any())
        assert self.modflow.basin.dtype == np.bool
        if correct_boundary:
            cwatm_cell_area = self.corrected_cwatm_cell_area.ravel()
        else:
            # MODIF LUCA
            cwatm_cell_area = self.var.cellArea.ravel()  # in m2

        array = (np.bincount(
            self.indices['CWatM_index'],
            weights=variable_copy.ravel()[self.indices['ModFlow_index']] * self.indices['area'],
            minlength=maskinfo['shape'][0]*maskinfo['shape'][1]
        ) / decompress(cwatm_cell_area, nanvalue=0)).reshape(maskinfo['shape']).astype(variable_copy.dtype)
        # MODIF LUCA
        array[maskinfo['mask'] == 1] = np.nan

        return array

    def modflow2CWATMbis(self, variable, correct_boundary=False):
        """Converting the 2D ModFLow capillary rise map into the fraction of area where capillary rise occurs
        in the 2D CWatM maps. return a fraction for each CWatM cell, input is the ModFlow capillary rise map
        the returned array is used to apply leakage from water bodies to the ModFlow layer"""
        variable_copy = variable.copy()
        variable_copy[self.modflow.basin == False] = 0
        variable_copy[variable_copy > 0] = 1  # Each ModFlow cell is distinguished between producing or not producing capillary rise
        assert not (np.isnan(variable_copy).any())
        assert self.modflow.basin.dtype == np.bool
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
        self.var.Ndays_steady = 0  #int(loadmap('Ndays_steady'))

        # test if ModFlow coupling is used as defined in settings file
        self.var.modflow = False
        if 'modflow_coupling' in option:
            #self.var.modflow = returnBool('modflow_coupling')
            self.var.modflow = checkOption('modflow_coupling')

        if self.var.modflow:

            print('\n=> ModFlow is used\n')

            verboseGW = False
            if 'verbose_GW' in binding:
                verboseGW = returnBool('verbose_GW')


            modflow_directory = cbinding('PathGroundwaterModflow')
            modflow_directory_output = cbinding('PathGroundwaterModflowOutput')
            # assert os.path.isabs(modflow_directory_output)

            directory_mf6dll = cbinding('path_mf6dll')
            if not(os.path.isdir(directory_mf6dll)):
                msg = "Error 222: Path to Modflow6 files does not exists "
                raise CWATMDirError(directory_mf6dll,msg,sname='path_mf6dll')

            nlay = int(loadmap('nlay'))

            rasterio = importlib.import_module("rasterio", package=None)
            with rasterio.open(cbinding('modflow_basin'), 'r') as src:
                modflow_basin = src.read(1).astype(np.bool)  # read in as 2-dimensional array (nrows, ncols).
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
                # domain variables will be used here, and in data handlind to save netcdf maps


            thickness = cbinding('thickness')
            if is_float(thickness):  # aquifer thickness is constant
                thickness = float(thickness)
                thickness = np.full((nlay, self.domain['nrow'], self.domain['ncol']), thickness)
            else:  # aquifer thickness is given as a tif file at ModFLow resolution
                raise NotImplementedError

            # Coef to multiply transmissivity and storage coefficient (because ModFlow convergence is better if aquifer's thicknes is big and permeability is small)
            self.coefficient = 1

            with rasterio.open(cbinding('topo_modflow'), 'r') as src:
                topography = src.read(1).astype(np.float32)
                topography[modflow_basin == False] = np.nan

            with rasterio.open(cbinding('chanRatio'), 'r') as src:
                # MODIF LUCA
                # the percentage of river is given at ModFlow resolution, it will be used to partitionning upward flow
                # from ModFlow into capillary rise and baseflow
                self.var.channel_ratio = src.read(1).astype(np.float32)
                #self.var.channel_ratio = self.var.compress(src.read(1))

            permeability_m_s = cbinding('permeability')
            if is_float(permeability_m_s):  # aquifer permeability is constant
                permeability_m_s = float(permeability_m_s)
                self.permeability = np.full((nlay, self.domain['nrow'], self.domain['ncol']), (24 * 3600 * permeability_m_s) / self.coefficient, dtype=np.float32)
            else:  # aquifer permeability is given as a tif file at ModFLow resolution
                raise NotImplementedError

            self.porosity = cbinding('poro')   # default = 0.1
            if is_float(self.porosity):  # aquifer porosity is constant
                self.porosity = float(self.porosity)
                self.porosity = np.full((nlay, self.domain['nrow'], self.domain['ncol']), self.porosity, dtype=np.float32)
            else:  # aquifer porosity is given as a tif file at ModFLow resolution
                raise NotImplementedError

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
            self.indices['area'] = self.indices['area'] * area_correction

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
                    print('=> Topography minus soil depth is used as upper limit of groundwater. Correcting depth under lakes.')
                    waterBodyID_temp = loadmap('waterBodyID').astype(np.int64)
                    soil_depth_temp = np.where(waterBodyID_temp != 0, np.nanmedian(self.var.soildepth12) - loadmap('depth_underlakes'), self.var.soildepth12)
                    soil_depth_temp = np.where(self.var.soildepth12 < 0.4, np.nanmedian(self.var.soildepth12), self.var.soildepth12)  # some cells around lake have small soil depths
                    soildepth_modflow = self.CWATM2modflow(decompress(soil_depth_temp))
                    soildepth_modflow[np.isnan(soildepth_modflow)] = 0
                else:
                    print('=> Topography minus soil depth is used as upper limit of groundwater. No correction of depth under lakes')
                    soildepth_modflow = self.CWATM2modflow(decompress(self.var.soildepth12))
                    soildepth_modflow[np.isnan(soildepth_modflow)] = 0
            else:  # topographic map is used as groundwater upper boundary
                if correct_depth_underlakes:  # we make a manual correction
                    print('=> Topography is used as upper limit of groundwater. Correcting depth under lakes. It can make ModFlow difficulties to converge')
                    waterBodyID_temp = loadmap('waterBodyID').astype(np.int64)
                    soil_depth_temp = np.where(waterBodyID_temp != 0, loadmap('depth_underlakes'), 0)
                    soildepth_modflow = self.CWATM2modflow(decompress(soil_depth_temp))
                    soildepth_modflow[np.isnan(soildepth_modflow)] = 0
                else:
                    print('=> Topography is used as upper limit of groundwater. No correction of depth under lakes')
                    soildepth_modflow = np.zeros((self.domain['nrow'], self.domain['ncol']), dtype=np.float32)


            # defining the top of the ModFlow layer
            self.layer_boundaries = np.empty((nlay + 1, self.domain['nrow'], self.domain['ncol']), dtype=np.float32)
            self.layer_boundaries[0] = topography - soildepth_modflow - 0.05
            # defining the bottom of the ModFlow layer
            self.layer_boundaries[1] = self.layer_boundaries[0] - thickness

            # saving soil thickness at modflow resolution to compute water table depth in postprocessing
            self.var.modflowtotalSoilThickness = soildepth_modflow + 0.05

            # defining the initial water table map (it can be a hydraulic head map previously simulated)
            self.var.load_init_water_table = False
            if 'load_init_water_table' in binding:
                self.var.load_init_water_table = returnBool('load_init_water_table')
            if self.var.load_init_water_table:
                print('=> Initial water table depth is uploaded from ', cbinding('init_water_table'))
                watertable = cbinding('init_water_table')
                if watertable.split(".")[-1] == "npy":
                    head = np.load(cbinding('init_water_table'))
                else:
                    ds = Dataset(watertable)
                    var = list(ds.variables.keys())[-1]
                    head = ds[var][:].data

            else:
                start_watertabledepth = loadmap('initial_water_table_depth')
                print('=> Water table depth is - ', start_watertabledepth, ' m at the begining')
                head = self.layer_boundaries[0] - start_watertabledepth  # initiate head 2 m below the top of the aquifer layer

            # Defining potential leakage under rivers and lakes or reservoirs
            leakageriver_factor = 0
            if 'leakageriver_permea' in binding:
                self.var.leakageriver_factor = loadmap('leakageriver_permea')  # in m/day
            print('=> Leakage under rivers is ', self.var.leakageriver_factor, ' m/day')
            leakagelake_factor = 0
            if 'leakagelake_permea' in binding:
                self.var.leakagelake_factor = loadmap('leakagelake_permea')  # in m/day
            print('=> Leakage under lakes/reservoirs is ', self.var.leakageriver_factor, ' m/day')

            # test if ModFlow pumping is used as defined in settings file
            Groundwater_pumping = False
            if 'Groundwater_pumping' in binding:
                self.var.GW_pumping = returnBool('Groundwater_pumping')
            print('=> Groundwater pumping should be deactivated if includeWaterDemand is False')

            self.var.availableGWStorageFraction = 0.85
            if self.var.GW_pumping:
                print('=> THE PUMPING MAP SHOULD BE DEFINED (In transient.py ALSO LINE 420) BEFORE TO RUN THE MODEL AND BE THE SAME FOR ALL THE SIMULATION')
                # creating a mask to set up pumping wells, TO DO MANUALLY HERE OR TO IMPORT AS A MAP, because running the model with zero pumping rates every cells is consuming
                self.wells_mask = np.copy(modflow_basin)
                # for Burgenland we set up only one well for each CWATM cell (1*1km), thus only one well every ten ModFlow cells
                # TODO NumOfModflowWellsInCWatMCell = 1 #Must be even or 1
                for ir in range(self.domain['nrow']):
                    for ic in range(self.domain['ncol']):
                        if modflow_basin[ir][ic] == 1: #and int((ir+5.0)/10.0) - (ir+5.0)/10.0 == 0 and int((ic+5.0)/10.0) - (ic+5.0)/10.0 == 0:
                            #if ir != 0 and ic != 0 and ir != self.domain['nrow']-1 and ic != self.domain['ncol']-1:
                            self.wells_mask[ir][ic] = True
                        else:
                            self.wells_mask[ir][ic] = False

                if 'water_table_limit_for_pumping' in binding:
                    # if available storage is too low, no pumping in this cell
                    self.var.availableGWStorageFraction = loadmap('water_table_limit_for_pumping')  # if 85% of the ModFlow cell is empty, we prevent pumping in this cell
                print('=> Pumping in the ModFlow layer is prevented if water table is under ', 1 - self.var.availableGWStorageFraction, ' of the layer capacity')

                # initializing the ModFlow6 model
                self.modflow = ModFlowSimulation(
                    'transient',
                    modflow_directory_output,
                    directory_mf6dll,
                    ndays=globals.dateVar['intEnd'],
                    specific_storage=0,
                    specific_yield=float(cbinding('poro')),
                    nlay=nlay,
                    nrow=self.domain['nrow'],
                    ncol=self.domain['ncol'],
                    rowsize=self.domain['rowsize'],
                    colsize=self.domain['colsize'],
                    top=self.layer_boundaries[0],
                    bottom=self.layer_boundaries[1],
                    basin=modflow_basin,
                    head=head,
                    topography=self.layer_boundaries[0],
                    permeability=self.permeability,
                    load_from_disk=returnBool('load_modflow_from_disk'),
                    setpumpings=True,
                    pumpingloc=self.wells_mask,
                    verbose=verboseGW)



            else: # no pumping
                # initializing the ModFlow6 model
                self.modflow = ModFlowSimulation(
                    'transient',
                    modflow_directory_output,
                    directory_mf6dll,
                    ndays=globals.dateVar['intEnd'],
                    specific_storage=0,
                    specific_yield=float(cbinding('poro')),
                    nlay=nlay,
                    nrow=self.domain['nrow'],
                    ncol=self.domain['ncol'],
                    rowsize=self.domain['rowsize'],
                    colsize=self.domain['colsize'],
                    top=self.layer_boundaries[0],
                    bottom=self.layer_boundaries[1],
                    basin=modflow_basin,
                    head=head,
                    topography=self.layer_boundaries[0],
                    permeability=self.permeability,
                    load_from_disk=returnBool('load_modflow_from_disk'),
                    setpumpings=False,
                    pumpingloc=None,
                    verbose=verboseGW)


            # MODIF LUCA
            #self.corrected_cwatm_cell_area = self.get_corrected_cwatm_cell_area()
            #self.corrected_modflow_cell_area = self.get_corrected_modflow_cell_area()

            # MODIF LUCA
            # initializing arrays
            self.var.capillar = globals.inZero.copy()
            self.var.baseflow = globals.inZero.copy()

            self.var.modflow_watertable = np.copy(head)  # water table will be also saved at modflow resolution

            # initial water table map is converting into CWatM map
            self.var.head = compressArray(self.modflow2CWATM(head))

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
            self.var.groundwater_storage_top_layer = (np.where(head>self.layer_boundaries[0],self.layer_boundaries[0],head) - self.layer_boundaries[1]) * self.porosity[0]

            # converting the groundwater storage from ModFlow to CWatM map (in meter)
            self.var.groundwater_storage_available = compressArray(self.modflow2CWATM(self.var.groundwater_storage_top_layer))  # used in water demand module then
            self.var.gwstorage_full = compressArray(self.modflow2CWATM((self.layer_boundaries[0] - self.layer_boundaries[1]) * self.porosity[0])) # use in water damnd to limit pumping

            # permeability need to be translated into CWatM map to compute leakage from surface water bodies
            self.var.permeability = compressArray(self.modflow2CWATM(self.permeability[0])) * self.coefficient

        else:

            ii = 1
            #print('=> ModFlow coupling is not used')

    def dynamic(self):

        # converting the CWatM recharge into ModFlow recharge (in meter)
        # we avoid recharge on saturated ModFlow cells, thus CWatM recharge is concentrated  on unsaturated cells
        corrected_recharge = np.where(self.var.capriseindex == 1, 0, self.var.sum_gwRecharge / (1 - self.var.capriseindex))
        groundwater_recharge_modflow = self.CWATM2modflow(decompress(corrected_recharge, nanvalue=0), correct_boundary=False)
        groundwater_recharge_modflow = np.where(self.var.modflow_watertable - self.layer_boundaries[0] >= 0,
                                                0, groundwater_recharge_modflow)
        # give the information to ModFlow
        self.modflow.set_recharge(groundwater_recharge_modflow)

        ## INSTALLING WELLS
        if self.var.GW_pumping:
            ## Groundwater demand from CWatM installs wells in each Modflow cell

            # Groundwater pumping demand from the CWatM waterdemand module, will be decompressed to 2D array
            # CWatM 2D groundwater pumping array is converted into Modflow 2D array
            # Pumping is given to ModFlow in m3 and < 0
            if self.modflow.verbose:
                print('mean modflow pumping [m]: ', np.nanmean(self.var.modfPumpingM))
            groundwater_abstraction = - self.CWATM2modflow(decompress(self.var.modfPumpingM)) * domain['rowsize'] * domain['colsize'] # BURGENLAND * 100 AND L428
            # * 100 because applied only in one ModFlow cell in Burgenland

            # give the information to ModFlow
            self.modflow.set_groundwater_abstraction(groundwater_abstraction)

            # LUCA: SPECIFIC FOR THE BURGENLAND TEST
            # groundwater_abstraction = groundwater_abstraction / 100


        # running ModFlow
        self.modflow.step()
        #self.modflow.finalize()


        # MODIF LUCA
        # extracting the new simulated hydraulic head map
        head = self.modflow.decompress(self.modflow.head.astype(np.float32))
        #self.var.head = compressArray(self.modflow2CWATM(head))

        # MODIF LUCA
        if self.var.writeerror:
            # copying the previous groundwater storage at ModFlow resolution (in meter)
            groundwater_storage_top_layer0 = np.copy(self.var.groundwater_storage_top_layer)  # for water balance computation

        # computing the new groundwater storage map at ModFlow resolution (in meter)
        self.var.groundwater_storage_top_layer = (np.where(head>self.layer_boundaries[0],self.layer_boundaries[0],head) - self.layer_boundaries[1]) * self.porosity[0]
        # converting the groundwater storage from ModFlow to CWatM map (in meter)
        self.var.groundwater_storage_available = compressArray(self.modflow2CWATM(self.var.groundwater_storage_top_layer))

        assert self.permeability.ndim == 3
        # computing the groundwater outflow by re-computing water outflowing the aquifer through the DRAIN ModFlow package
        groundwater_outflow = np.where(head - self.layer_boundaries[0] >= 0,
                                       (head - self.layer_boundaries[0]) * self.coefficient * self.permeability[0],0)
        groundwater_outflow2 = np.where(head - self.layer_boundaries[0] >= 0, 1.0, 0.0)  # For the next step, it will prevent recharge where ModFlow cells are saturated, even if there is no capillary rise (where h==topo)

        # MODIF LUCA
        # capillary rise and baseflow are allocated in fcuntion of the river percentage of each ModFlow cell
        capillar = groundwater_outflow * (1 - self.var.channel_ratio)  # We are still in ModFlow coordinate
        baseflow = groundwater_outflow * self.var.channel_ratio


        if self.var.writeerror:
            # Check the water balance: recharge = capillary + baseflow + storage change
            modflow_cell_area = self.domain['rowsize'] * self.domain['colsize']  # in m², for water balance computation

            if self.var.GW_pumping:
                mid_gwflow = np.nansum(((groundwater_recharge_modflow + capillar + baseflow) * modflow_cell_area - groundwater_abstraction) / 2)  # in m3, for water balance computation
                Budget_ModFlow_error = np.round(100 * (np.nansum((groundwater_recharge_modflow - capillar - baseflow -
                                                                                              (self.var.groundwater_storage_top_layer-groundwater_storage_top_layer0)) * modflow_cell_area + groundwater_abstraction) /
                                                                                   mid_gwflow), 2)
            else:
                mid_gwflow = np.nansum((groundwater_recharge_modflow + capillar + baseflow) * modflow_cell_area / 2)  # in m3, for water balance computation
                Budget_ModFlow_error = np.round(100 * (np.nansum((groundwater_recharge_modflow - capillar - baseflow -
                                                                                              (self.var.groundwater_storage_top_layer-groundwater_storage_top_layer0)) * modflow_cell_area) /
                                                                                   mid_gwflow), 2)
            print('ModFlow discrepancy : ', Budget_ModFlow_error, ' % (if pumping, it considers pumping demand is satisfied)')

            # converting flows from ModFlow to CWatM domain
            sumModFlowout = np.nansum((capillar + baseflow) * modflow_cell_area) # m3, for water balance computation
            sumModFlowin = np.nansum(groundwater_recharge_modflow * modflow_cell_area)  # m3, for water balance computation



        self.var.capillar = compressArray(self.modflow2CWATM(capillar))
        self.var.baseflow = compressArray(self.modflow2CWATM(baseflow))

        # computing saturated fraction of each CWatM cells (where water table >= soil bottom)
        self.var.capriseindex = compressArray(self.modflow2CWATMbis(groundwater_outflow2))  # initialized in landcoverType module, self.var.capriseindex is the fraction of saturated ModFlow cells in each CWatM cell

        # updating water table maps both at CWatM and ModFlow resolution
        self.var.head = compressArray(self.modflow2CWATM(head))
        self.var.modflow_watertable = np.copy(head)

        if self.var.writeerror:
            # computing the total recharge rate provided by CWatM for this time step (in m3)
            total_recharge_m3_cwatm = (self.var.sum_gwRecharge * self.var.cellArea).sum()  # m3, for water balance computation

            print('ModFlow-CWatM input conversion error : ', np.round(100 * (total_recharge_m3_cwatm - sumModFlowin)/sumModFlowin, 2), ' %')
            print('ModFlow-CWatM output conversion error : ', np.round(100 * (np.nansum((self.var.capillar+self.var.baseflow)*self.var.cellArea)-sumModFlowout)/sumModFlowout, 2), ' %')

            # Check crossed models:
            print('ModFlow discrepancy crossed: ', np.round(100 * (total_recharge_m3_cwatm - np.nansum((capillar + baseflow +
                                                                                                         (self.var.groundwater_storage_top_layer - groundwater_storage_top_layer0)) * modflow_cell_area)) /
                                                            mid_gwflow, 2), ' %')


