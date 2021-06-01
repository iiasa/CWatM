# -*- coding: utf-8 -*-
"""
Created on Fri Apr 19 21:17:12 2019

@author: lguillau
"""

# Import modules
import numpy as np
import matplotlib.pyplot as plt


def Proj_topo(res_ModFlow, ncol_ModFlow, nrow_ModFlow, namefile_map, output_name):
    """This function save the topographic map obtained by QGIS, ARCGIS (or Python using Project_InputsMap)
    for ModFlow regular grid. The ModFlow topographic map is saved in txt file.
    Also, modifies strange values.
    arg1: res_ModFlow : choosen ModFlow resolution
    arg2: limit_file : name of the text file where information about the grid are saved
    arg3: namefile_map : initial input map in array format given as input
    arg4: output_name : folder+name of the text file where topographic data for ModFlow are used)
    """
    
    ## Importing ModFlow grid information
    
    zi = namefile_map.reshape(np.product(namefile_map.shape))
    
    ## Modifying data to avoid strange values even outside of the basin
    zi[zi < -100] = np.nan            # We replace unknown values by nan
    mean_variable = np.nanmean(np.nanmean(zi))  # We replace nan values by the mean value
    zi[np.isnan(zi)] = mean_variable
    
    ## Save in text file for ModFlow
    fichier = open(output_name, "w")    # Create a file to save the data
    for k in range(len(zi)):            # Browse each line and colum and save in one column for ModFlow integration
        fichier.write(str(zi[k]))
        fichier.write("\n")             # Go to the line
    fichier.close()

    print('\nTopography data for ModFlow have been saved in:\n', output_name)