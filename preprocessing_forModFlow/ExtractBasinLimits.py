# -*- coding: utf-8 -*-
"""
Created on Wed Jan 16 13:42:29 2019

@author: Guillaumot Luca
"""

# Import modules
import numpy as np
import xarray as xr
from xarray import Dataset
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from rasterio import Affine
import netCDF4
import pyproj
import rasterio
import os
import math


def ExtractBasinLimits(res_ModFlow, cwatm_lon, cwatm_lat, wgs84, UTM, modf_transform, modf_shape, need_fitting):
    """This function uses the mask map of the basin used in CWATM, so the basin is defined at CWATM resolution,
    here we project and interpolate at the choosen resolution the map for ModFlow regular grid.
    arg1: res_ModFlow : choosen ModFlow resolution
    arg2: CWatM longitudes
    arg3: CWatM latitudes
    arg4: wgs84: CWatM coordinates system
    arg5: UTM: ModFlow coordinates system
    arg6: modf_transform
    arg7 : modf_shape
    arg8 : need_fitting, if True the new toporgaphy should be start on a point of the initial grid
    """
    
    a, b = np.meshgrid(
        np.append(cwatm_lon, 2*cwatm_lon[-1] - cwatm_lon[-2]),
        np.append(cwatm_lat, 2*cwatm_lat[-1] - cwatm_lat[-2])
    )
    a_utm, b_utm = pyproj.transform(wgs84, UTM, a, b)  # Convert coordinates from CWatM (like wgs84) to Modflow system (regular grid)

    if need_fitting:
        # In fact it could be better to avoid to translate the original topography
        # so, affine_modflow should be an existing "corner" of the initial topographic map both for the finer and final resolution
        x0_topomap = modf_transform[2]
        resx_topomap = modf_transform[0]
        y0_topomap = modf_transform[5]
        resy_topomap = modf_transform[4]
        print(x0_topomap, resx_topomap, y0_topomap, resy_topomap)
        x_topomap = [x0_topomap + resx_topomap * i for i in range(modf_shape[0])]
        y_topomap = [y0_topomap + resy_topomap * i for i in range(modf_shape[1])]

    xmin = np.min(a_utm)
    xmax = np.max(a_utm)
    if need_fitting:
        xmin = x_topomap[np.argmin(np.abs(xmin - x_topomap))]

    ncols = math.ceil((xmax-xmin) / res_ModFlow)
    xmax = xmin + ncols * res_ModFlow
    ymin = np.min(b_utm)
    ymax = np.max(b_utm)

    if need_fitting:
        ymin = y_topomap[np.argmin(np.abs(ymin - y_topomap))]

    nrows = math.ceil((ymax-ymin) / res_ModFlow)
    ymax = ymin + nrows * res_ModFlow
    gt_modlfow = (
        xmin, res_ModFlow, 0, ymax, 0, -res_ModFlow
    )

    affine_modflow = Affine.from_gdal(*gt_modlfow)

    return affine_modflow, ncols, nrows
