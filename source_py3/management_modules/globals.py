# -------------------------------------------------------------------------
# Name:        globals
# Purpose:
#
# Author:      burekpe
#
# Created:     16/05/2016
# Copyright:   (c) burekpe 2016

# This program comes with ABSOLUTELY NO WARRANTY
# This is free software, and you are welcome to redistribute it under certain conditions
# run cwatm 1 -w for details
# -------------------------------------------------------------------------

import getopt
import os.path

import ctypes
import numpy.ctypeslib as npct
import numpy as np

# for detecting on which system it is running
import platform

from management_modules.messages import *


global maskinfo,zeromap,modelSteps,xmlstring,geotransfrom
# noinspection PyRedeclaration
maskinfo = {}
modelSteps=[]
xmlstring=[]
geotrans=[]

global binding, option, FlagName, Flags, ReportSteps, FilterSteps, EnsMembers, outputDir
global MMaskMap, maskmapAttr, bigmapAttr, cutmap, cutmapGlobal, cutmapFine, cutmapVfine, metadataNCDF
global timestepInit
global metaNetcdfVar
global inputcounter
global versioning

versioning = {}
timestepInit =[]
binding = {}
option = {}
metaNetcdfVar = {}

inputcounter = {}
flagmeteo ={}
meteofiles = {}

# Initial conditions
global initCondVar,initCondVarValue
initCondVarValue = []
initCondVar = []


#date variable
global dateVar
# noinspection PyRedeclaration
dateVar = {}

# Output variables
global outDir, outsection, outputTyp
global outMap, outTss
outDir = {}
outMap = {}
outTss = {}
outsection = []
outputTypMap = ['daily', 'monthtot','monthavg', 'monthend','annualtot','annualavg','annualend','totaltot','totalavg','totalend','once','12month']
outputTypTss = ['daily', 'monthtot','monthavg', 'monthend','annualtot','annualavg','annualend','totaltot','totalavg']

reportTimeSerieAct = {}
reportMapsAll = {}
reportMapsSteps = {}
reportMapsEnd = {}

MMaskMap = 0
ReportSteps = {}
FilterSteps = []
EnsMembers = []
nrCores = []
outputDir = []

maskmapAttr = {}
bigmapAttr = {}
cutmap = [0, 1, 0, 1]
cutmapGlobal = [0, 1, 0, 1]
cutmapFine = [0, 1, 0, 1]
cutmapVfine = [0, 1, 0, 1]
cdfFlag = [0, 0, 0,0,0,0,0]  # flag for netcdf output for all, steps and end, monthly (steps), yearly(steps), monthly , yearly
metadataNCDF = {}

# groundwater modflow
global domain, indexes
domain = {}
indexes = {}



global timeMes,TimeMesString, timeMesSum
timeMes=[]
timeMesString = []  # name of the time measure - filled in dynamic
timeMesSum = []    # time measure of hydrological modules


global coverresult
coverresult = [False,0]
# -------------------------
global platform1

platform1 = platform.uname()[0]
python_bit = ctypes.sizeof(ctypes.c_voidp) * 8

#print "Running under platform: ", platform1
if python_bit  < 64:
   msg = "The Python version used is not a 64 bit version! Python " + str(python_bit) + "bit"
   raise CWATMError(msg)

path_global = os.path.dirname(__file__)
if platform1 == "Windows":
    dll_routing = os.path.join(os.path.split(path_global)[0],"hydrological_modules","routing_reservoirs","t5.dll")
elif platform1 == "CYGWIN_NT-6.1":
    # CYGWIN_NT-6.1 - compiled with cygwin
    dll_routing = os.path.join(os.path.split(path_global)[0],"hydrological_modules","routing_reservoirs","t5cyg.so")
else:
    print("Linux\n")
    dll_routing = os.path.join(os.path.split(path_global)[0],"hydrological_modules","routing_reservoirs","t5_linux.so")

#dll_routing = "C:/work2/test1/t4.dll"
lib2 = ctypes.cdll.LoadLibrary(dll_routing)

# setup the return typs and argument types
# input type for the cos_doubles function
# must be a double array, with single dimension that is contiguous
array_1d_double = npct.ndpointer(dtype=np.double, ndim=1, flags='CONTIGUOUS')
array_2d_int = npct.ndpointer(dtype=np.int64, ndim=2)
array_1d_int = npct.ndpointer(dtype=np.int64, ndim=1)
#array_1d_int16 = npct.ndpointer(dtype=np.int16, ndim=1, flags='CONTIGUOUS')
#array_2d_int32 = npct.ndpointer(dtype=np.int32, ndim=2, flags='CONTIGUOUS')
array_2d_double = npct.ndpointer(dtype=np.double, ndim=2, flags='CONTIGUOUS')


lib2.ups.restype = None
lib2.ups.argtypes = [array_1d_int, array_1d_int, array_1d_double, ctypes.c_int]

lib2.dirID.restype = None
lib2.dirID.argtypes = [array_2d_int, array_2d_int, array_2d_int, ctypes.c_int,ctypes.c_int]

#lib2.repairLdd1.argtypes = [ array_2d_int, ctypes.c_int,ctypes.c_int]
lib2.repairLdd1.argtypes = [ array_2d_int, ctypes.c_int,ctypes.c_int]

lib2.repairLdd2.restype = None
lib2.repairLdd2.argtypes = [ array_1d_int, array_1d_int, array_1d_int, ctypes.c_int]

lib2.kinematic.restype = None
#lib2.kinematic.argtypes = [array_1d_double,array_1d_double, array_1d_int, array_1d_int, array_1d_int,  array_1d_double,  ctypes.c_double, ctypes.c_double,ctypes.c_double, ctypes.c_double, ctypes.c_int]
#                             qold            q               dirdown        diruplen     dirupid         Qnew              alpha             beta            deltaT          deltaX           size
lib2.kinematic.argtypes = [array_1d_double,array_1d_double, array_1d_int, array_1d_int, array_1d_int,  array_1d_double,  array_1d_double, ctypes.c_double,ctypes.c_double, array_1d_double, ctypes.c_int]


lib2.runoffConc.restype = None
lib2.runoffConc.argtypes = [array_2d_double,array_1d_double,array_1d_double,array_1d_double,ctypes.c_int, ctypes.c_int]

# ----------------------------------
FlagName = ['quiet', 'veryquiet', 'loud',
            'checkfiles', 'noheader', 'printtime','warranty']
Flags = {'quiet': False, 'veryquiet': False, 'loud': False,
         'check': False, 'noheader': False, 'printtime': False, 'warranty': False, 'use': False}


def globalFlags(arg):
    """
    Read flags - according to the flags the output is adjusted
    quiet,veryquiet, loud, checkfiles, noheader,printtime, warranty

    :param arg: argument from calling cwatm
    """

    try:
        opts, args = getopt.getopt(arg, 'qvlchtw', FlagName)
    except getopt.GetoptError:
        Flags['use'] = True
        return

    for o, a in opts:
        if o in ('-q', '--quiet'):
            Flags['quiet'] = True
        if o in ('-v', '--veryquiet'):
            Flags['veryquiet'] = True
        if o in ('-l', '--loud'):
            Flags['loud'] = True
        if o in ('-c', '--checkfiles'):
            Flags['check'] = True
        if o in ('-h', '--noheader'):
            Flags['noheader'] = True
        if o in ('-t', '--printtime'):
            Flags['printtime'] = True
        if o in ('-w', '--warranty'):
            Flags['warranty'] = True

