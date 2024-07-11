# -*- coding: utf-8 -*-
"""
Created on Wed Jan 16 14:03:39 2019

@author: Guillaumot Luca
"""

"""Code to load basin river index of the Rhine basin initially computed by Matlab topotoolbox"""

## Import packages
import numpy as np
import matplotlib.pyplot as plt
from pysheds.grid import Grid  # to compute river network
import numpy as np
from matplotlib import colors

def Compute_RiverNetwork(reso, Inputs_folder, Input_map, modflow_affine, ncol_ModFlow, nrow_ModFlow, min_area, output_name):
    """ Function to compute the river network from the topographic map and a given minimal
    accumulation area to create a stream.
    arg1: reso : choosen resolution
    arg2: Inputs_folder : path where new information are saved
    arg3: Input_map : Topographic map
    arg4: modflow_affine : ModFlow grid information
    arg5: ncol_ModFlow : number of columns of the output DEM
    arg6: nrow_ModFlow : number of rows of the output DEM
    arg7: name_grid_file : name of the text file where information about the grid will be saved
    arg8: min_area : Minimal drainage area to characterize the river network (depending on the region, climate...)
    arg9: output_name : Stream network saved in numpy array (nrow, ncol)
    """

    # Compute the river network
    #grid = Grid.from_raster('C:\GitHub\CWatM_priv\preprocessing_forModFlow\Required_initial_maps\elevation_modflow.tif')
    #dem = grid.read_raster('C:\GitHub\CWatM_priv\preprocessing_forModFlow\Required_initial_maps\elevation_modflow.tif')
    grid = Grid.from_raster(Input_map)
    dem = grid.read_raster(Input_map)

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_alpha(0)

    plt.imshow(dem, extent=grid.extent, cmap='terrain', zorder=1)
    plt.colorbar(label='Elevation (m)')
    plt.grid(zorder=0)
    plt.title('Digital elevation map', size=14)
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.tight_layout()
    
    # Condition DEM
    # ----------------------
    # Fill pits in DEM
    pit_filled_dem = grid.fill_pits(dem)

    # Fill depressions in DEM
    flooded_dem = grid.fill_depressions(pit_filled_dem)
    # Resolve flats in DEM
    inflated_dem = grid.resolve_flats(flooded_dem)

    """grid = Grid.from_raster(Input_map, data_name='dem')
    # Fill depressions in DEM
    grid.fill_depressions('dem', out_name='flooded_dem')
    # Resolve flats in DEM
    grid.resolve_flats('flooded_dem', out_name='inflated_dem')
    # Specify directional mapping"""
    dirmap = (64, 128, 1, 2, 4, 8, 16, 32)
    # Compute flow directions
    """
    grid.flowdir(data='inflated_dem', out_name='dir', dirmap=dirmap)
    """
    fdir = grid.flowdir(inflated_dem, dirmap=dirmap)

    fig = plt.figure(figsize=(8, 6))
    fig.patch.set_alpha(0)

    plt.imshow(fdir, extent=grid.extent, cmap='viridis', zorder=2)
    boundaries = ([0] + sorted(list(dirmap)))
    plt.colorbar(boundaries=boundaries,
                 values=sorted(dirmap))
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.title('Flow direction grid', size=14)
    plt.grid(zorder=-1)
    plt.tight_layout()
    
    # grid.view('dir')
    # Calculate flow accumulation
    """
    grid.accumulation(data='dir', dirmap=dirmap, out_name='acc')
    """
    acc = grid.accumulation(fdir, dirmap=dirmap)

    #import seaborn as sns
    #import seaborn as sns
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_alpha(0)
    plt.grid('on', zorder=0)
    im = ax.imshow(acc, extent=grid.extent, zorder=2,
                   cmap='cubehelix',
                   norm=colors.LogNorm(1, acc.max()),
                   interpolation='bilinear')
    plt.colorbar(im, ax=ax, label='Upstream Cells')
    plt.title('Flow Accumulation', size=14)
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.tight_layout()
    # Extract river network
    # branches = grid.extract_river_network(fdir='dir', acc='acc', threshold=(stream_density**2)/(res_ModFlow_200m**2),
    #                                     dirmap=dirmap)
    """
    temp_acc = np.array(grid.view('acc'))
    """
    temp_acc = np.array(grid.view(acc))
    stream_network_200 = np.where(temp_acc > (min_area ** 2) / (reso ** 2), 1, 0)

    np.save(Inputs_folder + output_name, stream_network_200)  # Save this river network in numpy format
    print('\nStream network computed and saved in numpy format using\ntopographic map at ', reso,  ' m resolution')
    # River network in array format (nrow_ModFlow_200m, ncol_ModFlow_200m)
    # with a cell value of one if the cell is a river, 0 if not

    plt.figure()
    plt.subplot(1, 1, 1, aspect='equal')
    limitXwest = modflow_affine[2]
    limitYnorth = modflow_affine[5]
    limitXeast = modflow_affine[2] + ncol_ModFlow * modflow_affine[0]
    limitYsouth = modflow_affine[5] + nrow_ModFlow * modflow_affine[4]
    extent = (limitXwest, limitXeast, limitYsouth, limitYnorth)
    plt.imshow(stream_network_200, extent=extent, interpolation='none')
    plt.title('Finner River Network of the basin')
    plt.show()
