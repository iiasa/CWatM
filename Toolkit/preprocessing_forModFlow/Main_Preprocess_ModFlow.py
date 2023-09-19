# -*- coding: utf-8 -*-
"""
Created on Mon May  6 12:24:15 2019

@author: Luca G.
"""

#######################################################################################################################
# ------------------------------------ PREPROCESSING MAPS FOR THE MODFLOW MODEL ------------------------------------ #
#######################################################################################################################

""" All these maps will not change during CWatM-ModFlow simulation,
they define the ModFlow grid and associated coordinates, basin mask, topography,
river network (defined as a percentage of river cells in each ModFlow cell using a finner topographic map)
and eventually geological information like permeability, porosity and aquifer thickness maps.
A list is generated containing the area in common between each CWatM and ModFlow cells in the aim to project
flows form one model to the other during simulations. Indeed, CWatMgrid is lat/lon system while ModFlow requires a
rectangular grid.
Some important points:
    - Choose the good UTM system in function of the basin
    - Change filenames and paths
    - Work and import packages in a virtual environment could be easier to use all Python packages required
      without impact your current Python installation
    - Some wheels for pip install can be installed using https://www.lfd.uci.edu/~gohlke/pythonlibs/
    - One part of the code need to use QGis before
"""

# =============================================================================
# IMPORT ALL PACKAGES
# =============================================================================

# Import standard packages
import numpy as np
import xarray as xr
import pyproj
import os
import sys
import rasterio
import geopandas as gpd
from configparser import ConfigParser

print('Loaded dependencies')
# Import Python functions used for creating the maps
from ExtractBasinLimits import ExtractBasinLimits
from Compute_RiverNetwork import Compute_RiverNetwork
from Project_InputsMap import Project_InputsMap
from create_raster import create_raster
from define_modflow_basinmask import define_modflow_basinmask
from ComputeRiverPercent import ComputeRiverPercent
from Proj_topo import Proj_topo
from Proj_properties import Proj_properties

print('Loaded scripts')
# To avoid Warning message when dividing by nan values
np.seterr(divide='ignore', invalid='ignore')

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================


iniFile = os.path.normpath(sys.argv[1])


#parser = SafeConfigParser()
parser = ConfigParser()
parser.read(iniFile)

# FILE_PATHS
Main_path =  parser.get('FILE_PATHS', 'outputsPath') + '\\'
Folder_initial_maps =  parser.get('FILE_PATHS', 'inputsPath') + '\\'

# load maps' names
basin_limits_tif_file = parser.get('MODFLOW_INPUTS', 'basinMap')
initial_dem_tif = parser.get('MODFLOW_INPUTS', 'dem')
input_cellarea = parser.get('MODFLOW_INPUTS', 'cellArea')

# load parameters and resolutions
cwatm_epsg = int(parser.get('MODFLOW_INPUTS', 'cwatm_epsg'))
modflow_epsg = int(parser.get('MODFLOW_INPUTS', 'modflow_epsg'))
init_dem_epsg = int(parser.get('MODFLOW_INPUTS', 'init_dem_epsg'))
res_ModFlow = float(parser.get('MODFLOW_INPUTS', 'modflow_resolution'))
res_ModFlow_finer = float(parser.get('MODFLOW_INPUTS', 'modflow_subResolution'))
res_CWATM = float(parser.get('MODFLOW_INPUTS', 'cwatm_resolution'))
stream_density = float(parser.get('MODFLOW_INPUTS', 'streamDensity'))
relativeArea = float(parser.get('MODFLOW_INPUTS', 'relativeAreaThreshold'))
 
# FILE_PATHS - python scripts path
pyscriptpth = parser.get('FILE_PATHS', 'pythonScriptsPath')
'''

CORRECTIONS -
define_modflow_basinmask.py line 67 - set NA data as input
create_raster.py line 13 - GDAL_POLYGONIZE --> set path as input in settings file.

Document input variables
Create tutorial
Create batch file

test with global dem
test from different folder
create -o overwrite flag to delete existing outputs files

debug watnings

### GLOBAL VARIABLES ###
basin_limits_tif_file = "mask_ayalonSorek.tif"  # Mask of the CWATM model ##
Main_path = 'ModFlow_inputs_AyalonSorek'
Folder_initial_maps = 'Required_initial_maps_AyalonSorek/'  # This folder should contain the CWATM mask, area and the DEM that will be used for the ModFlow topography
initial_dem_tif = 'dem100m.tif'  # This DEM will be used to create both the finer grid to compute the river percentage and the ModFlow grid
input_cellarea = 'cellarea.tif'

cwatm_epsg = 4326     # cwatm epsg code
modflow_epsg = 32636  # modflow epsg code UTM or other metric system; China Sea (m): 3415; UTM 38N (m): 32648; Israel 32636 ; 2039
res_ModFlow = 500          # ModFlow model's resolution [m]
res_ModFlow_finer = 250      # Resolution used to define the river percentage for each ModFlow cell [m]

# Spatial resolution of the model
stream_density= 1000     # in [m], stream_density^2 defines the minimal drainage area of rivers (function of the basin, climate...)
res_CWATM = 0.00833333333    # CWAT model's resolution [m] or [degree] depending of the coordinates system
relativeArea = 0.6   # Minimum share of MODFLOW cell's area in the CWatM basin/region mask, reuqired to keep the cell inside the mask
#mask_na_value = 255
'''
def create_modflowGrids(cwatm_epsg, modflow_epsg, res_ModFlow, res_ModFlow_finer, stream_density, res_CWATM, basin_limits_tif_file, Main_path, Folder_initial_maps, initial_dem_tif, input_cellarea):
    initial_dem_system = {'init': 'EPSG:' + str(cwatm_epsg)}
    Outputs_file = os.path.join(Main_path, 'output')  # Contains at least one output map (like GW recharge) of CWatM and cellArea, in netcdf format
    Inputs_file = os.path.join(Main_path, f'{res_ModFlow}m/')   # Folder where input maps will be saved
    Inputs_file_finer = os.path.join(Main_path, f'{res_ModFlow_finer}m/')   # Folder where finner input maps will be saved (not necessary 200m, we choose 250m for the Bhima basin)
    if not os.path.exists(Inputs_file):
        os.makedirs(Inputs_file)
    if not os.path.exists(Inputs_file_finer):
        os.makedirs(Inputs_file_finer)

    name_finer_dem_tif = Inputs_file_finer + 'DEM_ModFlow_finer.tif'

    res_ModFlow = res_ModFlow * 1.0
    print('ModFlow resolution [m]: ', res_ModFlow)
    # Projection: choose the good UTM grid IN FUNCTION OF THE BASIN !!!



    wgs84_cwatm = pyproj.Proj("+init=EPSG:" + str(cwatm_epsg))  # Projection system for the CWatM model
    UTM_modflow = pyproj.Proj("+init=EPSG:" + str(modflow_epsg))  # Projection system for the ModFlow model
    modflow_crs = {'init': 'EPSG:' + str(modflow_epsg)}  # EPSG should be the same as UTM_modflow

    # Area [m2] of each CWatM cell: two options
    with rasterio.open(Folder_initial_maps + input_cellarea, 'r') as src:
        gridcellarea = src.read(1)  # Matrix containing the studied CWATM variable
        cwatm_profile = src.profile

    # Loading model grid information
    nrow_CWatM, ncol_CWatM = cwatm_profile['height'], cwatm_profile['width']

    # If the CWatM grid is aleady defined in a cartesian system (x,y)
    #with rasterio.open(Folder_initial_maps + basin_limits_tif_file, 'r') as src:
    #    cwatm_profile = src.profile
    #gridcellarea = res_CWATM*res_CWATM  # m2

    # =============================================================================
    # CREATING MAPS NECESSARY TO MODFLOW MODEL
    # =============================================================================

    # ======================================================================================================================
    # First, it is necessary to define a river network using a finner topographic map resolution
    
    with rasterio.open(Folder_initial_maps + initial_dem_tif, 'r') as src:
        modf_transform = src.transform
        modf_shape = src.shape

    cwatm_transform = cwatm_profile['transform']
    cwatm_lon = [cwatm_transform.c + cwatm_transform.a * i for i in range(cwatm_profile['width'])]
    cwatm_lat = [cwatm_transform.f + cwatm_transform.e * i for i in range(cwatm_profile['height'])]
    
    need_fitting = True
    if cwatm_epsg == init_dem_epsg:
        need_fitting = False

    
    # has to be run only once

    # Run ExtractBasinLimits at finer resolution first
    affine_modflow_finer, ncol_ModFlow_finer, nrow_ModFlow_finer = ExtractBasinLimits(res_ModFlow_finer, cwatm_lon,\
        cwatm_lat, wgs84_cwatm, UTM_modflow, modf_transform, modf_shape, need_fitting)
    np.save(Inputs_file_finer + 'affine_modflow_finer.npy', affine_modflow_finer)
    np.save(Inputs_file_finer + 'ncol_ModFlow_finer.npy', ncol_ModFlow_finer)
    np.save(Inputs_file_finer + 'nrow_ModFlow_finer.npy', nrow_ModFlow_finer)
        
    Project_InputsMap(res_ModFlow_finer, Folder_initial_maps + initial_dem_tif, ncol_ModFlow_finer, nrow_ModFlow_finer,
                        modflow_crs, affine_modflow_finer, create_tif=name_finer_dem_tif)
    Compute_RiverNetwork(res_ModFlow_finer, Inputs_file_finer, name_finer_dem_tif, affine_modflow_finer,
                            ncol_ModFlow_finer, nrow_ModFlow_finer, stream_density, 'StreamNetwork_finer.npy')

def create_modflowInputs(cwatm_epsg, modflow_epsg, res_ModFlow, res_ModFlow_finer, stream_density, res_CWATM, basin_limits_tif_file, Main_path, Folder_initial_maps, initial_dem_tif, input_cellarea, relativeArea):
    initial_dem_system = {'init': 'EPSG:' + str(cwatm_epsg)}
    Outputs_file = os.path.join(Main_path, 'output')  # Contains at least one output map (like GW recharge) of CWatM and cellArea, in netcdf format
    Inputs_file = os.path.join(Main_path, f'{res_ModFlow}m/')   # Folder where input maps will be saved
    Inputs_file_finer = os.path.join(Main_path, f'{res_ModFlow_finer}m/')   # Folder where finner input maps will be saved (not necessary 200m, we choose 250m for the Bhima basin)
    if not os.path.exists(Inputs_file):
        os.makedirs(Inputs_file)
    if not os.path.exists(Inputs_file_finer):
        os.makedirs(Inputs_file_finer)

    name_finer_dem_tif = Inputs_file_finer + 'DEM_ModFlow_finer.tif'

    res_ModFlow = res_ModFlow * 1.0
    print('ModFlow resolution [m]: ', res_ModFlow)
    # Projection: choose the good UTM grid IN FUNCTION OF THE BASIN !!!



    wgs84_cwatm = pyproj.Proj("+init=EPSG:" + str(cwatm_epsg))  # Projection system for the CWatM model

    UTM_modflow = pyproj.Proj("+init=EPSG:" + str(modflow_epsg))  # Projection system for the ModFlow model
    modflow_crs = {'init': 'EPSG:' + str(modflow_epsg)}  # EPSG should be th same than UTM_modflow

    # Area [m2] of each CWatM cell: two options
    with rasterio.open(Folder_initial_maps + input_cellarea, 'r') as src:
        gridcellarea = src.read(1)  # Matrix containing the studied CWATM variable
        cwatm_profile = src.profile

    # Loading model grid information
    nrow_CWatM, ncol_CWatM = cwatm_profile['height'], cwatm_profile['width']

    # If the CWatM grid is aleady defined in a cartesian system (x,y)
    #with rasterio.open(Folder_initial_maps + basin_limits_tif_file, 'r') as src:
    #    cwatm_profile = src.profile
    #gridcellarea = res_CWATM*res_CWATM  # m2

    # =============================================================================
    # CREATING MAPS NECESSARY TO MODFLOW MODEL
    # =============================================================================

    # ======================================================================================================================
    # First, it is necessary to define a river network using a finner topographic map resolution

    cwatm_transform = cwatm_profile['transform']
    cwatm_lon = [cwatm_transform.c + cwatm_transform.a * i for i in range(cwatm_profile['width'])]
    cwatm_lat = [cwatm_transform.f + cwatm_transform.e * i for i in range(cwatm_profile['height'])]



    # Ones this step is done, the model can be created at different coarser resolutions

    # ======================================================================================================================
    # Creating ModFlow maps at the chosen resolution

    # Defining ModFlow grid limits and cells coordinates in a UTM georeferencing system (regular)
    with rasterio.open(Folder_initial_maps + initial_dem_tif, 'r') as src:
        modf_transform = src.transform
        modf_shape = src.shape
    need_fitting = True
    if cwatm_epsg == init_dem_epsg:
        need_fitting = False
        
    affine_modflow, ncol_ModFlow, nrow_ModFlow = ExtractBasinLimits(res_ModFlow, cwatm_lon, cwatm_lat, wgs84_cwatm,
                                                                    UTM_modflow, modf_transform, modf_shape, need_fitting)

    # ======================================================================================================================
    # Creating raster files from ModFlow and CWatM grid information, then using QGIS to save the area in common of each cell
    cwatm_shapefile = 'CWatM_model_grid.shp'
    create_raster(cwatm_profile['transform'].to_gdal(), int(ncol_CWatM), int(nrow_CWatM), cwatm_epsg,
                  Inputs_file, cwatm_shapefile, pyscriptpth)
    modflow_shapefile = 'ModFlow_model_grid.shp'
    create_raster(affine_modflow.to_gdal(), int(ncol_ModFlow), int(nrow_ModFlow), modflow_epsg,
                  Inputs_file, modflow_shapefile, pyscriptpth)

    cwatm_shp = gpd.read_file(os.path.join(Inputs_file, cwatm_shapefile))
    crs_to_project = 'EPSG:' + str(int(modflow_epsg))
    cwatm_shp = cwatm_shp.to_crs(crs=crs_to_project, epsg=modflow_epsg)
    modflow_shp = gpd.read_file(os.path.join(Inputs_file, modflow_shapefile))
    cwatm_shp['geom'] = cwatm_shp.geometry

    intersect = gpd.sjoin(modflow_shp, cwatm_shp, how='inner', op='intersects', lsuffix='modflow', rsuffix='cwatm')

    intersect['area'] = intersect.apply(lambda x: x.geom.intersection(x.geometry).area, axis=1)

    header = ["x_modflow", "y_modflow", "x_cwatm", "y_cwatm", "area"]

    intersect = intersect[intersect["area"] > 1]  # if the area shared is < 1m^2, we do not take into account (because it means the cells overlap perfectly)
    intersect = intersect.sort_index()
    intersect.to_csv (Inputs_file + 'intersection.csv', index = True, header=True, columns = header)


    # not necessary now
    #print(f"""
    #    0) Open the {cwatm_shape} and {modflow_shape} in QGIS,
    #    1) Add spatial index to each raster files (Vector -> Data Management Tools -> Create Spatial index)
    #    2) Next, go to "Vector overlay" tool -> "intersection" : Use {modflow_shape} as the input layer, {cwatm_shape} as the overlay
    #    3) Open the attribute table of the new created “intersection map”
    #    4) Add a new column using geometry $area
    #    5) Export the new map as CSV in the {Inputs_file} folder as "intersection.csv"
    #""")
    #input('When done, press any key to continue')

    # ======================================================================================================================
    # Defining the basin mask for ModFlow
    define_modflow_basinmask(res_ModFlow, Folder_initial_maps + basin_limits_tif_file, Inputs_file, modflow_crs,
                             affine_modflow, ncol_ModFlow, nrow_ModFlow, ncol_CWatM, nrow_CWatM, gridcellarea, relativeArea)

    # ======================================================================================================================
    # Creating topographic map for ModFlow from tif file at finner resolution and saving it in text file
    Project_InputsMap(res_ModFlow, Folder_initial_maps + initial_dem_tif, ncol_ModFlow, nrow_ModFlow, modflow_crs,
                      affine_modflow, create_tif=os.path.join(Inputs_file, 'elevation_modflow.tif'))

    # ======================================================================================================================
    # Creating "geological" maps (Permeability and Porosity) if necessary:

    #Projected_permea_map = Project_InputsMap(res_ModFlow , 'ModFlow_maps/PermeaRhine_GLHYMPSv2.tif',
     #                                        Inputs_file+'Lobith_limits.txt')
    #Proj_properties(res_ModFlow, Inputs_file+'Lobith_limits.txt', Projected_permea_map, Inputs_file+'PermeaV2.txt',
     #               2, 'log10(Permeability*200) [m2/s] map used by ModFlow')        # Permeability map from GHLYMPSE
    #Projected_permea_map = Project_InputsMap(res_ModFlow , 'ModFlow_maps/PermeaRhine_GLHYMPSv1.tif', Inputs_file+'Lobith_limits.txt')
    #Proj_properties(res_ModFlow, Inputs_file+'Lobith_limits.txt', Projected_permea_map, Inputs_file+'PermeaV1.txt',
     #               1, 'log10(Permeability*200) [m2/s] map used by ModFlow')        # Permeability map from GHLYMPSE
    #Projected_poro_map = Project_InputsMap(res_ModFlow , 'ModFlow_maps/PoroRhine_GLHYMPSv1.tif',
     #                                      Inputs_file+'Lobith_limits.txt')
    #Proj_properties(res_ModFlow, Inputs_file+'Lobith_limits.txt', Projected_poro_map ,
     #               Inputs_file+'PoroV1.txt', 1, 'Porosity map used by ModFlow')    # Porosity map from GHLYMPSE


    # ======================================================================================================================
    # Computing the percentage of river in each ModFlow cell using the river network obtained at a finner scale

    affine_modflow_finer = np.load(Inputs_file_finer + 'affine_modflow_finer.npy')
    ncol_ModFlow_finer = np.load(Inputs_file_finer + 'ncol_ModFlow_finer.npy')
    nrow_ModFlow_finer = np.load(Inputs_file_finer + 'nrow_ModFlow_finer.npy')
    # # Note that it is better if the finner resolution is a factor of the ModFlow resolution (eg. 250m, 500m, 1000m)
    stream_file = Inputs_file_finer + 'StreamNetwork_finer.npy'       # This file was created by "Compute_RiverNetwork.py"
    RiverPercentage = ComputeRiverPercent(res_ModFlow, affine_modflow, ncol_ModFlow, nrow_ModFlow, res_ModFlow_finer,
                                          stream_file, affine_modflow_finer, ncol_ModFlow_finer, nrow_ModFlow_finer,
                                          modflow_crs, create_tif=os.path.join(Inputs_file, 'modlfow_river_percentage.tif'))


# First run

create_modflowGrids(cwatm_epsg = cwatm_epsg, modflow_epsg = modflow_epsg, res_ModFlow = res_ModFlow, res_ModFlow_finer = res_ModFlow_finer, stream_density = stream_density, res_CWATM = res_CWATM, basin_limits_tif_file = basin_limits_tif_file, Main_path = Main_path, Folder_initial_maps = Folder_initial_maps, initial_dem_tif = initial_dem_tif,input_cellarea = input_cellarea)
 
 # Second run
create_modflowInputs(cwatm_epsg = cwatm_epsg, modflow_epsg = modflow_epsg, res_ModFlow = res_ModFlow, res_ModFlow_finer = res_ModFlow_finer, stream_density = stream_density, res_CWATM = res_CWATM, basin_limits_tif_file = basin_limits_tif_file, Main_path = Main_path, Folder_initial_maps = Folder_initial_maps, initial_dem_tif = initial_dem_tif,input_cellarea = input_cellarea, relativeArea = relativeArea)