# -*- coding: utf-8 -*-
"""
Created on Mon May 13 10:31:47 2019

@author: Luca
"""

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling


def Project_InputsMap(modflow_res, input_map, ncol_ModFlow, nrow_ModFlow, crs_modflow, modflow_affine, create_tif=False):
    """Function to project input maps generaly from finner resolution and in WGS84 coordinates
    to the ModFlow resolution and on UTM system, the user have to choose the good EPSG code for
    the studied basin, and also the resampling method.
    arg1: res_ModFlow : choosen resolution
    arg2: input_map : input map to project (tif)
    arg3: ncol_ModFlow : number of columns of the output DEM
    arg4: nrow_ModFlow : number of rows of the output DEM
    arg5: crs_modflow : crs of the ModFlow grid (like {'init': 'EPSG:32643'} )
    arg6: modflow_affine : ModFlow grid information
    arg7: create_tif=No : the new map is directly returned as numpy array
    """

    with rasterio.open(input_map) as src:
        src_transform = src.transform
        src_crs = src.crs
        source = src.read(1)

    dst_shape = (nrow_ModFlow, ncol_ModFlow)    # rows and columns of the ModFlow grid
    dst_crs = crs_modflow          # UTM32N for the UPPER BHIMA !!!!!!!!
    destination = np.zeros(dst_shape)

    reproject(source, destination, src_transform=src_transform, src_crs=src_crs, dst_transform=modflow_affine,
                dst_crs=dst_crs, resampling=Resampling.average)  # OTHER RESAMPLING IS POSSIBLE (NEAREST, ...)
    
    if create_tif:  # We create a new tif fil for Matlab processing, in the aim to compute the stream network
        with rasterio.open(create_tif, 'w', driver='GTiff', width=dst_shape[1],
                            height=dst_shape[0], count=1, dtype=np.float64, nodata=0, transform=modflow_affine,
                            crs=dst_crs) as dst:
            dst.write(destination, indexes=1)
        dst.close()
    else:
        return destination
