#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 19 22:41:24 2024

@author: ral003
"""

#########################################################################################
#           This part of the code will be removed, it is only here for the tests        #
#           with the matlab code                                                        #
#########################################################################################
import os
from scipy.io import loadmat
from SnowModelVariables import SnowModelVariables

def load_mat_files_to_class(folder_path, spatial_dim):
    """
    Load all .mat files in a folder and populate a list of SnowModelVariables objects.

    Args:
        folder_path (str): Path to the folder containing .mat files.
        spatial_dim (int or tuple): Spatial dimension(s) of the variables (e.g., 100 or (100,)).

    Returns:
        list: A list of SnowModelVariables objects, where each object represents one time step.
    """
    # Get all .mat files in the folder
    mat_files = [f for f in os.listdir(folder_path) if f.endswith('.mat')]

    # Mapping for exceptions where the variable name in the .mat file doesn't match the attribute name
    variable_mapping = {
        'SnowfallWaterEq': 'SFE',  # Attribute : .mat file variable name
    }

    # Initialize a dictionary to store loaded data for each variable
    data_dict = {}

    # Load each .mat file into the dictionary
    for mat_file in mat_files:
        variable_name = os.path.splitext(mat_file)[0]  # Variable name from file name
        file_path = os.path.join(folder_path, mat_file)
        mat_data = loadmat(file_path)

        # Check if the variable name matches or is in the exception mapping
        if variable_name in mat_data:
            data_dict[variable_name] = mat_data[variable_name]
            time_dim = mat_data[variable_name].shape[0]
        else:
            for attr, mat_var in variable_mapping.items():
                if variable_name == attr and mat_var in mat_data:
                    data_dict[variable_name] = mat_data[mat_var]

    # Create a list of SnowModelVariables objects, one for each time step
    snow_model_list = []
    for t in range(time_dim):
        snow_model = SnowModelVariables(spatial_dim)
        for key, value in data_dict.items():
            if hasattr(snow_model, key):
                setattr(snow_model, key, value[t,:])  # Set attribute for the time step
        snow_model_list.append(snow_model)

    return snow_model_list

# def print_t(matlab_, snow_model_instances):
#     dm = matlab_.__dict__
#     ds = snow_model_instances.__dict__
#     a = False
#     for k in ds.keys():
#         if k != 'PackWater'  and k != 'Albedo':
#             if np.nansum(dm[k]) > 0:
#                 if abs((np.nansum(dm[k]) - np.nansum(ds[k]))/np.nansum(dm[k])) > 0.005:
#                     a = True
#                     print(k, np.nansum(dm[k]), np.nansum(ds[k]), np.nansum(dm[k]) - np.nansum(ds[k]), sep=",")

#     if a:
#         time.sleep(1)

# dm = matlab_[i].__dict__
# ds = snow_model_instances[i].__dict__

# for k in ds.keys():
#     print(k, np.nansum(dm[k]), np.nansum(ds[k]), np.nansum(dm[k]) - np.nansum(ds[k]), sep=",")
    # print(k, np.nansum(ds[k]), np.nansum(dm[k]) - np.nansum(ds[k]))

# print(np.nansum(matlab_[i].SnowMelt), np.nansum(snow_model_instances[i].SnowMelt))

# def compare_classes(obj1, obj2):
#     if not isinstance(obj1, SnowModelVariables) or not isinstance(obj2, SnowModelVariables):
#         raise TypeError("Both objects must be instances of SnowModelVariables.")

#     mismatches = {}
#     for attr in vars(obj1):
#         if not np.array_equal(getattr(obj1, attr), getattr(obj2, attr), equal_nan=True):
#             mismatches[attr] = {
#                 'obj1': getattr(obj1, attr),
#                 'obj2': getattr(obj2, attr)
#             }

#     return mismatches
#########################################################################################
#           end of the part of the code that will be removed                            #
#########################################################################################

#    matlab_ = load_mat_files_to_class('./pySnowClim/tests/datasets/matlab_fixed/',
#                                      size_lat)

#        if snow_model_instances[i] != matlab_[i]:
#            print(i)
#            mismatches = compare_classes(snow_model_instances[i], matlab_[i])
#            for attr, values in mismatches.items():
#                print(f"Attribute: {attr}")
#                print(f"  obj1: {values['obj1']}")
#                print(f"  obj2: {values['obj2']}")
#            exit
