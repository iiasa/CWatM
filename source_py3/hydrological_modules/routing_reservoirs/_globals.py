#-------------------------------------------------------------------------------
# Name:        globals
# Purpose:
#
# Author:      burekpe
#
# Created:     05/01/2015
# Copyright:   (c) burekpe 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------


import ctypes
import numpy.ctypeslib as npct
import numpy as np

global maskattr,dirDown,catchment
maskattr = {}
dirDown = []

lib2 = ctypes.cdll.LoadLibrary('C:/work2/test1/t3.dll')
#lib2 = ctypes.cdll.LoadLibrary('C:/work2/test1/t5.so')
#lib2 = ctypes.cdll.LoadLibrary('/nahaUsers/burekpe/newrout/t2.so')

# setup the return typs and argument types
# input type for the cos_doubles function
# must be a double array, with single dimension that is contiguous

array_1d_double = npct.ndpointer(dtype=np.double, ndim=1, flags='CONTIGUOUS')
array_2d_int = npct.ndpointer(dtype=np.int64, ndim=2)
array_1d_int = npct.ndpointer(dtype=np.int64, ndim=1)
#array_1d_int16 = npct.ndpointer(dtype=np.int16, ndim=1, flags='CONTIGUOUS')
#array_2d_int32 = npct.ndpointer(dtype=np.int32, ndim=2, flags='CONTIGUOUS')

lib2.ups.restype = None
lib2.ups.argtypes = [array_1d_int, array_1d_int, array_1d_double, ctypes.c_int]

lib2.dirID.restype = None
#lib2.dirID.argtypes = [array_2d_int, array_2d_int, array_2d_int, ctypes.c_int,ctypes.c_int]
lib2.dirID.argtypes = [array_2d_int, array_2d_int, array_2d_int, ctypes.c_int,ctypes.c_int]

#lib2.repairLdd1.restype = None
#lib2.repairLdd1.argtypes = [ array_2d_int, ctypes.c_int,ctypes.c_int]
lib2.repairLdd1.argtypes = [ array_2d_int, ctypes.c_int,ctypes.c_int]

lib2.repairLdd2.restype = None
lib2.repairLdd2.argtypes = [ array_1d_int, array_1d_int, array_1d_int, ctypes.c_int]

lib2.kinematic.restype = None
lib2.kinematic.argtypes = [array_1d_double,array_1d_double, array_1d_int, array_1d_int, array_1d_int,  array_1d_double,  ctypes.c_double, ctypes.c_double,ctypes.c_double, ctypes.c_double, ctypes.c_int]
#                             qold            q               dirdown        diruplen     dirupid         Qnew                                                                             int size
