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
flows from one model to the other during simulations. Indeed, CWatM grid could be in lat/lon system (or simply not
aligned with the ModFlow grid) while ModFlow requires a
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
#import xarray as xr
import pyproj
import os
import rasterio
import geopandas as gpd

# Import Python functions used for creating the maps
from ExtractBasinLimits import ExtractBasinLimits
from Compute_RiverNetwork import Compute_RiverNetwork
from Project_InputsMap import Project_InputsMap
from create_raster import create_raster
from define_modflow_basinmask import define_modflow_basinmask
from ComputeRiverPercent import ComputeRiverPercent
from Proj_topo import Proj_topo
from Proj_properties import Proj_properties

# To avoid Warning message when dividing by nan values
np.seterr(divide='ignore', invalid='ignore')

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

# Files location
basin_limits_tif_file = "Mask_Burgenland_1km.tif"  # Mask of the CWATM model ##
Main_path = 'ModFlow_inputs'

res_ModFlow = 100           # ModFlow model's resolution [m]
res_ModFlow_200m = 10   # We use a finner resolution to define the river network, and then the river percentage used by ModFlow
Outputs_file = os.path.join(Main_path, 'output')  # Contains at least one output map (like GW recharge) of CWatM and cellArea, in netcdf format
Inputs_file = os.path.join(Main_path, f'{res_ModFlow}m/')   # Folder where input maps will be saved
Inputs_file_200m = os.path.join(Main_path, f'{res_ModFlow_200m}m/')   # Folder where finner input maps will be saved (not necessary 200m, we choose 250m for the Bhima basin)
if not os.path.exists(Inputs_file):
    os.makedirs(Inputs_file)
if not os.path.exists(Inputs_file_200m):
    os.makedirs(Inputs_file_200m)

# Spatial resolution of the model
stream_density = 1000      # in [m] stream_density^2 defines the minimal drainage area of rivers (function of the basin, climate...)
res_CWATM = 1000    # CWAT model's resolution [m]

# Projection: choose the good UTM grid IN FUNCTION OF THE BASIN !!!
wgs84_cwatm = pyproj.Proj("+init=EPSG:3035")  # Associated coord system (regular grid in degree)
UTM_modflow = pyproj.Proj("+init=EPSG:3035")  # Projection system for the BHIMA basin UTM43N (irregular grid in meter)
modflow_crs = {'init': 'EPSG:3035'}


# Area [m2] of each CWatM cell if in lat/lon
#with rasterio.open('DataDrive/CWatM/krishna/input/areamaps/cell_area.tif', 'r') as src:
#    gridcellarea = src.read(1)  # Matrix containing the studied CWATM variable
#    cwatm_profile = src.profile

# Area [m2] of each CWatM cell if in regular square grid
with rasterio.open(basin_limits_tif_file, 'r') as src:
    cwatm_profile = src.profile
gridcellarea = 1000 * 1000  # m2

# =============================================================================
# CREATING MAPS NECESSARY TO MODFLOW MODEL
# =============================================================================

# ======================================================================================================================
# First, it is necessary to define a river network using a finner topographic map resolution

cwatm_transform = cwatm_profile['transform']
cwatm_lon = [cwatm_transform.c + cwatm_transform.a * i for i in range(cwatm_profile['width'])]
cwatm_lat = [cwatm_transform.f + cwatm_transform.e * i for i in range(cwatm_profile['height'])]

# has to be run only once, it could be long because defining grid at finner scale

# Run ExtractBasinLimits at 200m resolution first
#affine_modflow_200m, ncol_ModFlow_200m, nrow_ModFlow_200m = ExtractBasinLimits(res_ModFlow_200m, cwatm_lon, cwatm_lat,
#                                                                               wgs84_cwatm, UTM_modflow)
#np.save(Inputs_file_200m + 'affine_modflow_200m.npy', affine_modflow_200m)
#np.save(Inputs_file_200m + 'ncol_ModFlow_200m.npy', ncol_ModFlow_200m)
#np.save(Inputs_file_200m + 'nrow_ModFlow_200m.npy', nrow_ModFlow_200m)
##Project_InputsMap(res_ModFlow_200m, 'FinalDEM_ExtendedBurgenland_10m.tif', Inputs_file_200m+'modflow_gridlimits.txt',
##                  {'init': 'EPSG:32643'}, create_tif='upperbhima_DEM_utm_250mNEW.tif')
#Compute_RiverNetwork(res_ModFlow_200m, Inputs_file_200m, 'FinalDEM_ExtendedBurgenland_10m.tif',
#                     affine_modflow_200m, ncol_ModFlow_200m, nrow_ModFlow_200m, stream_density,
#                     'StreamNetwork10mV1.npy')
#a=ccc

# Ones this step is done, the model can be created at different coarser resolutions,
# and this part do not need to be used again
 

# ======================================================================================================================
# Creating ModFlow maps at the chosen resolution

# Defining ModFlow grid limits and cells coordinates in a UTM georeferencing system (regular)
affine_modflow, ncol_ModFlow, nrow_ModFlow = ExtractBasinLimits(res_ModFlow, cwatm_lon, cwatm_lat, wgs84_cwatm,
                                                                UTM_modflow)

# ======================================================================================================================
# Creating raster files from ModFlow and CWatM grid information, then using QGIS to save the area in common of each cell

# Load model grid information
nlay = 1
nrow_CWatM, ncol_CWatM = cwatm_profile['height'], cwatm_profile['width']
# Extract CWatM coordinates

cwatm_shape = 'CWatM_Bhima_grid.shp'
#create_raster(cwatm_profile['transform'].to_gdal(),
#              int(ncol_CWatM), int(nrow_CWatM), 3035, Inputs_file, cwatm_shape)
modflow_shape = 'ModFlow_Bhima_grid.shp'
#create_raster(affine_modflow.to_gdal(), int(ncol_ModFlow), int(nrow_ModFlow),
#              3035, Inputs_file, modflow_shape)  # EPSG:32643 for the ModFlow grid of the Bhima basin

# cwatm_shp = gpd.read_file(os.path.join(Inputs_file, 'CWatM_Bhima_grid.shp'))
# modflow_shp = gpd.read_file(os.path.join(Inputs_file, 'ModFlow_Bhima_grid.shp'))

# intersect = gpd.sjoin(cwatm_shp.head(10), modflow_shp.head(10), how='inner', op='intersects', lsuffix='cwatm', rsuffix='modflow')

# import pdb; pdb.set_trace()

print(f"""
    0) Open the {cwatm_shape} and {modflow_shape} in QGIS,
    1) Add spatial index to each raster files (Vector -> Data Management Tools -> Create Spatial index)
    2) Next, go to "Vector overlay" tool -> "intersection" : Use {modflow_shape} as the input layer, {cwatm_shape} as the overlay
    3) Open the attribute table of the new created “intersection map”
    4) Add a new column using geometry $area
    5) Export the new map as CSV in the {Inputs_file} folder as "intersection.csv"
""")

input('When done, press any key to continue')

# ======================================================================================================================
# Defining the basin mask for ModFlow
define_modflow_basinmask(res_ModFlow, basin_limits_tif_file, Inputs_file, modflow_crs, affine_modflow, ncol_ModFlow,
                         nrow_ModFlow, nrow_CWatM, ncol_CWatM)


# ======================================================================================================================
# Creating topographic map for ModFlow from tif file at finner resolution and saving it in text file
Projected_topo_map = Project_InputsMap(res_ModFlow, 'FinalDEM_ExtendedBurgenland_10m.tif',
                                       ncol_ModFlow, nrow_ModFlow, modflow_crs, affine_modflow,
                                       create_tif=os.path.join(Inputs_file, 'elevation_modflow.tif'))

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

affine_modflow_200m = np.load(Inputs_file_200m + 'affine_modflow_200m.npy')
ncol_ModFlow_200m = np.load(Inputs_file_200m + 'ncol_ModFlow_200m.npy')
nrow_ModFlow_200m = np.load(Inputs_file_200m + 'nrow_ModFlow_200m.npy')
# # Note that it is better if the finner resolution is a factor of the ModFlow resolution (eg. 250m, 500m, 1000m)
stream_file = Inputs_file_200m + 'StreamNetwork10mV1.npy'       # This file was created by "Compute_RiverNetwork.py"
RiverPercentage = ComputeRiverPercent(res_ModFlow, affine_modflow, ncol_ModFlow, nrow_ModFlow, res_ModFlow_200m,
                                      stream_file, affine_modflow_200m, ncol_ModFlow_200m, nrow_ModFlow_200m,
                                      modflow_crs, create_tif=os.path.join(Inputs_file, 'modlfow_river_percentage.tif'))
