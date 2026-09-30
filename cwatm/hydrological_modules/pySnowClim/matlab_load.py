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
#from scipy.io import loadmat
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
    
    import zlib
    from concurrent.futures import ThreadPoolExecutor

    import numpy as np

    _MI = {1: "i1", 2: "u1", 3: "i2", 4: "u2", 5: "i4", 6: "u4", 7: "f4", 9: "f8", 12: "i8", 13: "u8", 16: "u1", 17: "u2", 18: "u4"}
    _MX = {6: "f8", 7: "f4", 8: "i1", 9: "u1", 10: "i2", 11: "u2", 12: "i4", 13: "u4", 14: "i8", 15: "u8"}


    def _elements(buf, bo):
        pos = 0
        while pos + 8 <= len(buf):
            typ, n = map(int, np.frombuffer(buf, bo + "u4", 2, pos))
            if typ >> 16:
                yield typ & 0xFFFF, buf[pos + 4:pos + 4 + (typ >> 16)]
                pos += 8
            else:
                yield typ, buf[pos + 8:pos + 8 + n]
                pos += 8 + n + (typ != 15) * (-n % 8)


    def _matrix(buf, bo):
        (_, flags), (_, dims), (_, name), *parts = _elements(buf, bo)
        cls = int(np.frombuffer(flags, bo + "u4")[0]) & 0xFF
        dims = tuple(np.frombuffer(dims, bo + "i4"))
        re, *im = (np.frombuffer(d, bo + _MI[t]) for t, d in parts)
        if cls == 4:
            return bytes(name).decode(), np.array(["".join(map(chr, r)) for r in re.reshape(dims, order="F")])
        if cls not in _MX:
            raise NotImplementedError(f"{bytes(name).decode()}: MATLAB class {cls} not supported")
        arr = re.astype(_MX[cls], copy=False)
        if im:
            arr = arr + 1j * im[0].astype(_MX[cls])
        return bytes(name).decode(), arr.reshape(dims, order="F")


    def _inflate(data, chunk=1 << 16):
        d = zlib.decompressobj()
        out = bytearray()
        for i in range(0, len(data), chunk):
            out += d.decompress(data[i:i + chunk])
        return np.frombuffer(out, np.uint8)


    def _variable(typ, data, bo):
        if typ == 15:
            typ, data = next(_elements(_inflate(data), bo))
        return _matrix(data, bo) if typ == 14 else None


    def loadmat(path, mmap=False):
        raw = np.memmap(path, mode="c") if mmap else np.fromfile(path, np.uint8)
        if bytes(raw[:10]) == b"MATLAB 7.3":
            raise ValueError("v7.3 MAT-file is HDF5; use h5py")
        bo = "<" if bytes(raw[126:128]) == b"IM" else ">"
        with ThreadPoolExecutor() as ex:
            return dict(filter(None, ex.map(lambda e: _variable(*e, bo), _elements(raw[128:], bo))))    
    
    
    
    
    
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
