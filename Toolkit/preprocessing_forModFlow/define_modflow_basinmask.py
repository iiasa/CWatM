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
import netCDF4
import pyproj
import rasterio
import pandas as pd
import os


def define_modflow_basinmask(res_ModFlow, namefile_map, entrys_file, modflow_crs, modflow_affine, ncol_ModFlow,
                             nrow_ModFlow, ncol_CWatM, nrow_CWatM, cwatmarea):
    """This function uses the mask map of the basin used in CWATM, so the basin is defined at CWATM resolution,
    here we project and interpolate at the choosen resolution the map for ModFlow regular grid.
    arg1: res_ModFlow : choosen ModFlow resolution
    arg2: namefile_map : basin mask defined for CWatM (tif file)
    arg3: entrys_file : path where new information are saved
    arg4: crs_modflow : crs of the ModFlow grid (like {'init': 'EPSG:32643'} )
    arg5: modflow_affine : ModFlow grid information
    arg6: ncol_ModFlow : number of columns of the ModFlow model
    arg7: nrow_ModFlow : number of rows of the ModFlow model
    arg8: ncol_CWatM : number of columns of the CWatM model
    arg9: nrow_CWatM : number of rows of the CwatM model
    """

    # First, the Excel File coming from QGIS is converted numpy matrices

    df = pd.read_csv(os.path.join(entrys_file, 'intersection.csv'))

    if not os.path.exists(os.path.join(entrys_file, 'indices')):
        os.makedirs(os.path.join(entrys_file, 'indices'))

    modflow_x = df['x_modflow'].to_numpy()  # ModFlow column
    modflow_y = df['y_modflow'].to_numpy()  # ModFlow row
    cwatm_x = df['x_cwatm'].to_numpy()  # CWatM row
    cwatm_y = df['y_cwatm'].to_numpy()  # CWatM col
    area = df['area'].to_numpy()  # Area shared by each CWatM and ModFlow cell [m2]

    np.save(os.path.join(entrys_file, 'indices/modflow_x.npy'), modflow_x)
    np.save(os.path.join(entrys_file, 'indices/modflow_y.npy'), modflow_y)
    np.save(os.path.join(entrys_file, 'indices/cwatm_x.npy'), cwatm_x)
    np.save(os.path.join(entrys_file, 'indices/cwatm_y.npy'), cwatm_y)
    np.save(os.path.join(entrys_file, 'indices/area.npy'), area)

    # Now, these data are used to define the basin mask (in ModFlow grid)

    # Creating 1D arrays containing ModFlow and CWatM indices anf Intersected area [m2]
    ModFlow_index = np.array(modflow_y * ncol_ModFlow + modflow_x)
    CWatM_index = np.array(cwatm_y * ncol_CWatM + cwatm_x)  # associated CWatM cell index

    # Defining the ModFlow mask
    ModFlowcellarea = res_ModFlow ** 2
    # Opening the file containing basin cells flag in the rectangular CWATM area (Mask)
    with rasterio.open(namefile_map) as src:
        mask_basin = src.read(1)  # Save basin cells values

    tempmask = np.where(mask_basin == 255, 0.0, 1.0)

    cwatmarea = np.where(tempmask == 1, cwatmarea, 0)  # In case, remove cell areas outside of the mask

    plt.figure()
    plt.imshow(cwatmarea)
    plt.title('CWatM cells area [m²]', fontsize=14)
    plt.colorbar()
    plt.show()

    # Area in common need to be corrected because computed in a different system than cwatm cell area, IT WILL BE DONE AGAIN INSIDE THE MODEL
    indices_cell_area = np.bincount(CWatM_index, weights=area, minlength=np.shape(mask_basin)[0]*np.shape(mask_basin)[1])
    area_correction = (cwatmarea.ravel() / indices_cell_area)[CWatM_index]
    area = area * area_correction
    # now if we sum areas we should have exactly the same

    plt.figure()
    aa = cwatmarea/np.reshape(indices_cell_area, np.shape(mask_basin))
    #aa[aa>10] = np.nan
    plt.imshow(aa)
    plt.title('Correcting factor applied to the shared area', fontsize=14)
    plt.colorbar()
    plt.show()

    # Looking at if the ModFlow cell is mainly out of the basin
    ratio_ModFlowcellarea = np.bincount(ModFlow_index, weights=tempmask.ravel()[CWatM_index] * area, minlength=nrow_ModFlow * ncol_ModFlow) / ModFlowcellarea

    basin_limits = np.zeros(nrow_ModFlow * ncol_ModFlow, dtype=np.int32)  # Creating the ModFlow basin/region mask
    # Keeping ModFlow cells where more than 50 % of the area is inside the CWATM basin/region mask
    basin_limits[ratio_ModFlowcellarea > 0.5] = 1  # Cell = 0 will be INACTIVE in ModFlow simulation
    basin_limits = basin_limits.reshape(nrow_ModFlow, ncol_ModFlow)


    # ------------------------------------------------------------------------------------------------------------------
    print('\nCHECKING PROJECTION BETWEEN CWATM AND MODFLOW')

    plt.figure()
    plt.imshow(100 * np.reshape(ratio_ModFlowcellarea, (nrow_ModFlow, ncol_ModFlow)))
    plt.title('Percentage of the areas of each ModFlow cell inside the CWatM mask', fontsize=14)
    plt.colorbar()
    plt.show()

    plt.figure()
    variable = np.where(mask_basin == 255, 0, 1.0)
    plt.imshow(variable)
    plt.title('Imposed recharge from CWatM (here 1 everywhere)', fontsize=14)
    plt.colorbar()

    plt.figure()
    array = (np.bincount(ModFlow_index, variable.ravel()[CWatM_index] * area, minlength=nrow_ModFlow * ncol_ModFlow) / ModFlowcellarea).reshape((nrow_ModFlow, ncol_ModFlow))
    plt.imshow(np.where(basin_limits == 1, array, 0))
    plt.title('Resulting ModFlow recharge (should be close from 1 everywhere)', fontsize=14)
    plt.colorbar()
    plt.show()
    print('\n => Total percentage error from CWatm to ModFlow : ', (np.nansum(array) - np.nansum(variable*cwatmarea/ModFlowcellarea)) / np.nansum(array) * 100)

    plt.figure()
    variable = np.where(basin_limits == 1, 1.0, 0)
    plt.imshow(variable)
    plt.title('Imposed baseflow or "capillary rise" from ModFlow (here 1 everywhere)', fontsize=14)
    plt.colorbar()

    plt.figure()
    array = (np.bincount(CWatM_index, weights=variable.ravel()[ModFlow_index] * area, minlength=np.shape(mask_basin)[0]*np.shape(mask_basin)[1]) / cwatmarea.ravel()).reshape(np.shape(mask_basin)[0], np.shape(mask_basin)[1])
    plt.imshow(array)
    plt.title('Resulting CWatM baseflow or "capillary rise" (should be close from 1 everywhere)', fontsize=14)
    plt.colorbar()
    plt.show()
    print(' => Total percentage error from ModFlow to CWatm: ', (np.nansum(variable) - np.nansum(array * cwatmarea) / ModFlowcellarea) / np.nansum(variable) * 100)


    # ------------------------------------------------------------------------------------------------------------------
    # SAVING THE BASIN MASK IN TIF FORMAT
    print('\nSAVING THE MODFLOW MASK\n')
    with rasterio.open(os.path.join(entrys_file, 'modflow_basin.tif'), 'w', driver='GTiff', width=ncol_ModFlow,
                            height=nrow_ModFlow, count=1, dtype=np.int32, nodata=-1, transform=modflow_affine,
                            crs=modflow_crs) as dst:
         dst.write(basin_limits, 1)

    # If we want plot the basin mask for ModFlow
    plt.figure()

    plt.subplot(1, 2, 1)
    plt.imshow(tempmask, interpolation='none', cmap=plt.cm.BrBG)
    plt.axis('equal')
    plt.title('CWatM mask', fontsize=14)

    plt.subplot(1, 2, 2)
    plt.imshow(basin_limits, interpolation='none', cmap=plt.cm.BrBG)
    plt.axis('equal')
    plt.title('ModFlow mask', fontsize=14)
    plt.show()
