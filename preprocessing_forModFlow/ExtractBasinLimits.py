# -*- coding: utf-8 -*-
"""
Created on Wed Jan 16 13:42:29 2019

@author: Guillaumot Luca
"""

# Import modules
import numpy as np
#import xarray as xr
#from xarray import Dataset
#import matplotlib.pyplot as plt
#from scipy.interpolate import griddata
from rasterio import Affine
#import netCDF4
import pyproj
import rasterio
import os
import math


def ExtractBasinLimits(res_ModFlow, cwatm_lon, cwatm_lat, wgs84, UTM):
    """This function uses the mask map of the basin used in CWATM, so the basin is defined at CWATM resolution,
    here we project and interpolate at the choosen resolution the map for ModFlow regular grid.
    arg1: res_ModFlow : choosen ModFlow resolution
    arg2: CWatM longitudes (or X)
    arg3: CWatM latitudes (or Y)
    arg4: wgs84: CWatM coordinates system
    arg5: UTM: ModFlow coordinates system
    """
    
    a, b = np.meshgrid(
        np.append(cwatm_lon, 2*cwatm_lon[-1] - cwatm_lon[-2]),
        np.append(cwatm_lat, 2*cwatm_lat[-1] - cwatm_lat[-2])
    )
    a_utm, b_utm = pyproj.transform(wgs84, UTM, a, b)  # Convert coordinates from wgs84 to UTM32N

    xmin = np.min(a_utm)
    xmax = np.max(a_utm)
    ncols = math.ceil((xmax-xmin) / res_ModFlow)
    xmax = xmin + ncols * res_ModFlow
    ymin = np.min(b_utm)
    ymax = np.max(b_utm)
    nrows = math.ceil((ymax-ymin) / res_ModFlow)
    ymax = ymin + nrows * res_ModFlow

    gt_modlfow = (
        xmin, res_ModFlow, 0, ymax, 0, -res_ModFlow
    )

    affine_modflow = Affine.from_gdal(*gt_modlfow)

    return affine_modflow, ncols, nrows
