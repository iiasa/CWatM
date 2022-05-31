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
Main_path = 'Created_files'

# USER INPUTS
Folder_initial_maps = 'Required_initial_maps_Saudi/' #'Required_initial_maps_Saudi/'  # This folder should contain the CWATM mask, area and the DEM that will be used for the ModFlow topography
basin_limits_tif_file = "SaudiMask.tif"  # Mask of the CWATM model ##
initial_dem_tif = 'SaudiDEM.tif'  # This DEM will be used to create both the finer grid to compute the river percentage and the ModFlow grid
init_dem_epsg = 4326
init_dem_epsg_str = 'EPSG:' + str(init_dem_epsg)
initial_dem_system = {'init': init_dem_epsg_str}
res_ModFlow = 1000        # ModFlow model's resolution [m]
res_ModFlow_finer = 500     # Resolution used to define the river percentage for each ModFlow cell [m]

Outputs_file = os.path.join(Main_path, 'output')  # Contains at least one output map (like GW recharge) of CWatM and cellArea, in netcdf format
Inputs_file = os.path.join(Main_path, f'{res_ModFlow}m/')   # Folder where input maps will be saved
Inputs_file_finer = os.path.join(Main_path, f'{res_ModFlow_finer}m_finer/')   # Folder where finner input maps will be saved (not necessary 200m, we choose 250m for the Bhima basin)
if not os.path.exists(Inputs_file):
    os.makedirs(Inputs_file)
if not os.path.exists(Inputs_file_finer):
    os.makedirs(Inputs_file_finer)

name_finer_dem_tif = Inputs_file_finer + 'DEM_ModFlow_finer.tif'

# Spatial resolution of the model
stream_density = 2000      # low = dense.  Must be greater than res_Modflow_finer. in [m], stream_density^2 defines the minimal drainage area of rivers (function of the basin, climate...)
res_CWATM = 0.0833333333    # CWAT model's resolution [m] or [degree] depending of the coordinates system
res_ModFlow = res_ModFlow * 1.0

# Projection: choose the good UTM grid IN FUNCTION OF THE BASIN !!!
cwatm_epsg = 4326
modflow_epsg = 32638 #32650 or 32648yellow # Saudi 32638 #1206 #20437 #8840 #Bhima 32643 https://epsg.io/32638
cwatm_epsg_str = 'EPSG:' + str(init_dem_epsg)
modflow_epsg_str = 'EPSG:' + str(modflow_epsg)
wgs84_cwatm = pyproj.Proj("+init=EPSG:" + str(cwatm_epsg))  # Projection system for the CWatM model
UTM_modflow = pyproj.Proj("+init=EPSG:" + str(modflow_epsg))  # Projection system for the ModFlow model
modflow_crs = {'init': modflow_epsg_str}  # EPSG should be th same than UTM_modflow

# Area [m2] of each CWatM cell: two options
print('\nLoading the map of the CWatM cells area')
# 1) Loading model grid information: if cwatm in lat/lon
with rasterio.open(Folder_initial_maps + 'cellarea_totalend.nc', 'r') as src:  #cellarea_totalend.nc
    gridcellarea = src.read(1)  # Matrix containing the studied CWATM variable
    cwatm_profile = src.profile
nrow_CWatM, ncol_CWatM = cwatm_profile['height'], cwatm_profile['width']

# 2) Loading model grid information: if cwatm in regular grid (in this case, res_CWATM should be used)
#with rasterio.open(Folder_initial_maps + basin_limits_tif_file, 'r') as src:
#    cwatm_profile = src.profile
#nrow_CWatM, ncol_CWatM = cwatm_profile['height'], cwatm_profile['width']
#gridcellarea = res_CWATM*res_CWATM  # m2
#gridcellarea = np.ones((nrow_CWatM, ncol_CWatM)) * gridcellarea

with rasterio.open(Folder_initial_maps + initial_dem_tif, 'r') as src:
    modf_transform = src.transform
    modf_shape = src.shape

cwatm_transform = cwatm_profile['transform']
cwatm_lon = [cwatm_transform.c + cwatm_transform.a * i for i in range(cwatm_profile['width'])]
cwatm_lat = [cwatm_transform.f + cwatm_transform.e * i for i in range(cwatm_profile['height'])]
print('\nModFlow resolution [m]: ', res_ModFlow)
print('CWatM resolution [m or degree]: (', cwatm_transform.a, ', ', cwatm_transform.e, ')')

need_fitting = True
if cwatm_epsg == init_dem_epsg:
    need_fitting = False

# =============================================================================
# CREATING MAPS NECESSARY TO MODFLOW MODEL
# =============================================================================
"""
# ======================================================================================================================
# First, it is necessary to define a river network using a finner topographic map resolution

# has to be run only once

# Run ExtractBasinLimits at finer resolution first
affine_modflow_finer, ncol_ModFlow_finer, nrow_ModFlow_finer = ExtractBasinLimits(res_ModFlow_finer, cwatm_lon,
                                                                                  cwatm_lat, wgs84_cwatm, UTM_modflow,
                                                                                  modf_transform, modf_shape, need_fitting)
np.save(Inputs_file_finer + 'affine_modflow_finer.npy', affine_modflow_finer)
np.save(Inputs_file_finer + 'ncol_ModFlow_finer.npy', ncol_ModFlow_finer)
np.save(Inputs_file_finer + 'nrow_ModFlow_finer.npy', nrow_ModFlow_finer)

Project_InputsMap(res_ModFlow_finer, Folder_initial_maps + initial_dem_tif, ncol_ModFlow_finer, nrow_ModFlow_finer,
                  modflow_crs, affine_modflow_finer, create_tif=name_finer_dem_tif)
Compute_RiverNetwork(res_ModFlow_finer, Inputs_file_finer, name_finer_dem_tif, affine_modflow_finer,
                     ncol_ModFlow_finer, nrow_ModFlow_finer, stream_density, 'StreamNetwork_finer.npy')

# Ones this step is done, the model can be created at different coarser resolutions
a=bbb
"""
# ======================================================================================================================
# Creating ModFlow maps at the chosen resolution

# Defining ModFlow grid limits and cells coordinates in a UTM georeferencing system (regular)
affine_modflow, ncol_ModFlow, nrow_ModFlow = ExtractBasinLimits(res_ModFlow, cwatm_lon, cwatm_lat, wgs84_cwatm,
                                                                UTM_modflow, modf_transform, modf_shape, need_fitting)

# ======================================================================================================================
# Creating raster files from ModFlow and CWatM grid information, then using QGIS to save the area in common of each cell

# this part can't overwrite files inside the ModFlow inputs folder (previous files need to be removed to restart!)
cwatm_shapefile = 'CWatM_model_grid.shp'
create_raster(cwatm_profile['transform'].to_gdal(), int(ncol_CWatM), int(nrow_CWatM), cwatm_epsg,
              Inputs_file, cwatm_shapefile)
modflow_shapefile = 'ModFlow_model_grid.shp'
create_raster(affine_modflow.to_gdal(), int(ncol_ModFlow), int(nrow_ModFlow), modflow_epsg,
              Inputs_file, modflow_shapefile)

cwatm_shp = gpd.read_file(os.path.join(Inputs_file, cwatm_shapefile))
if cwatm_epsg != modflow_epsg:
    cwatm_shp = cwatm_shp.to_crs(crs=modflow_epsg_str, epsg=modflow_epsg)  # need reprojection
modflow_shp = gpd.read_file(os.path.join(Inputs_file, modflow_shapefile))

cwatm_shp['geom'] = cwatm_shp.geometry

intersect = gpd.sjoin(modflow_shp, cwatm_shp, how='inner', op='intersects', lsuffix='modflow', rsuffix='cwatm')

intersect['area'] = intersect.apply(lambda x: x.geom.intersection(x.geometry).area, axis=1)

header = ["x_modflow", "y_modflow", "x_cwatm", "y_cwatm", "area"]

intersect = intersect[intersect["area"] > 1]  # if the area shared is < 1m^2, we do not take into account (because it means the cells overlap perfectly)
intersect = intersect.sort_index()
intersect.to_csv (Inputs_file + 'intersection.csv', index = True, header=True, columns = header)


# ======================================================================================================================
# Defining the basin mask for ModFlow
define_modflow_basinmask(res_ModFlow, Folder_initial_maps + basin_limits_tif_file, Inputs_file, modflow_crs,
                         affine_modflow, ncol_ModFlow, nrow_ModFlow, ncol_CWatM, nrow_CWatM, gridcellarea)

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

# Note that it is better if the finner resolution is a factor of the ModFlow resolution (eg. 250m, 500m, 1000m)
stream_file = Inputs_file_finer + 'StreamNetwork_finer.npy'       # This file was created by "Compute_RiverNetwork.py"
RiverPercentage = ComputeRiverPercent(res_ModFlow, affine_modflow, ncol_ModFlow, nrow_ModFlow, res_ModFlow_finer,
                                      stream_file, affine_modflow_finer, ncol_ModFlow_finer, nrow_ModFlow_finer,
                                      modflow_crs, create_tif=os.path.join(Inputs_file, 'modlfow_river_percentage.tif'))
