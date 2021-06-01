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
    grid = Grid.from_raster(Input_map, data_name='dem')
    # Fill depressions in DEM
    grid.fill_depressions('dem', out_name='flooded_dem')
    # Resolve flats in DEM
    grid.resolve_flats('flooded_dem', out_name='inflated_dem')
    # Specify directional mapping
    dirmap = (64, 128, 1, 2, 4, 8, 16, 32)
    # Compute flow directions
    grid.flowdir(data='inflated_dem', out_name='dir', dirmap=dirmap)
    # grid.view('dir')
    # Calculate flow accumulation
    grid.accumulation(data='dir', dirmap=dirmap, out_name='acc')
    # Extract river network
    # branches = grid.extract_river_network(fdir='dir', acc='acc', threshold=(stream_density**2)/(res_ModFlow_200m**2),
    #                                     dirmap=dirmap)
    temp_acc = np.array(grid.view('acc'))
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
