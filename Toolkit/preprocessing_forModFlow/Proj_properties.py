# -*- coding: utf-8 -*-
"""
Created on Fri Apr 19 21:17:12 2019

@author: lguillau
"""

# Import modules
import numpy as np
import matplotlib.pyplot as plt

def Proj_properties(res_ModFlow, limit_file, namefile_map, output_name, version, prop_name):
    """This function save the permeability or porosity map obtained by QGIS, ARCGIS (or Python using Project_InputsMap)
    for ModFlow regular grid. Saving the file in txt format.
    Also, modify strange values
    arg1: res_ModFlow : choosen ModFlow resolution
    arg2: limit_file : name of the text file where information about the grid are saved
    arg3: namefile_map : initial input map in array format given as input
    arg4: output_name : folder+name of the text file where data for ModFlow are used
    arg5: version : GLHYMPS version used for the initial input map (1 or 2)
    arg6: prop_name : special name, precise if the parameter is porosity or permeability
    """
    
    # Importing ModFlow grid information, Defining new coordinates
    Limits = np.loadtxt(limit_file) # Import the limits of the ModFlow map
    nrow = int(Limits[4])
    ncol = int(Limits[5])
    
    zi = namefile_map.reshape(np.product(namefile_map.shape))
    
    # Modifying data to avoid strange values even outside of the basin, and remove too high or too low values
    if prop_name == 'Porosity map used by ModFlow':
        zi[zi < -100] = np.nan        # We replace unknown values by nan
        zi[zi > 900] = np.nan

    mean_variable = np.nanmean(np.nanmean(zi)) # We replace nan values by the mean value
    if prop_name == 'log10(Permeability*200) [m2/s] map used by ModFlow':
        if version == 2:
            mean_variable = 1e7*10**(mean_variable/100)       # in m/s       # as the GLHYMPS V2 map is the log of permeability multiplied by 100, we divide by 100
        if version == 1:
            mean_variable = 1e7*10**mean_variable       # in m/s
    zi[np.isnan(zi)] = mean_variable
    
    # Save in text file for ModFlow
    fichier = open(output_name, "w")    # Create a file to save the data
    for k in range(len(zi)):            # Browse each line and column and save in one column for ModFlow integration
        if prop_name == 'log10(Permeability*200) [m2/s] map used by ModFlow':
            if version == 2:
                zi[k] = 1e7*10**(zi[k]/100)      # in m/s       # as the GLHYMPS map is the log of permeability multiplied by 100, we divide by 100
            if version == 1:
                zi[k] = 1e7*10**(zi[k])      # in m/s
            if np.log10(zi[k]*200) > -2:                  # if transmissivity (considering a thickness of 200m) is not realistic, here too high
                zi[k] = (10**(-2))/200
            if np.log10(zi[k]*200) < -4.5:                # if transmissivity (considering a thickness of 200m) is not realistic, here too low
                zi[k] = (10**(-4.5))/200
        if prop_name == 'Porosity map used by ModFlow':
            if zi[k]<0.03:                              # if porosity is not realistic, here too low
                zi[k] = 0.03
        
        fichier.write(str(zi[k]))
        fichier.write("\n")         # Go to the line
    fichier.close()

    # If we want plot the map
    zi2 = np.zeros((nrow, ncol))
    for ir in range(nrow):    # Browse each line and column
        for ic in range(ncol):
            if zi[ir*ncol+ic] == mean_variable:  # For the plot is better to have nan values
                zi2[ir][ic] = np.nan
            else:
                if prop_name == 'log10(Permeability*200) [m2/s] map used by ModFlow':
                    zi2[ir][ic] = np.log10(zi[ir*ncol+ic]*200)  # in m2/s
                else:
                    zi2[ir][ic] = zi[ir*ncol+ic]
    
    plt.figure()
    extent = (Limits[0]-res_ModFlow/2, Limits[1]+res_ModFlow/2, Limits[2]+res_ModFlow/2, Limits[3]-res_ModFlow/2)
    cmap = plt.cm.BrBG
    if prop_name == 'log10(Permeability*200) [m2/s] map used by ModFlow':
        plt.imshow(zi2, extent=extent, interpolation='none', cmap=cmap)
    else:
        plt.imshow(zi2, extent=extent, interpolation='none', cmap=cmap)
    plt.colorbar()
    plt.axis('equal')
    plt.title(prop_name)
