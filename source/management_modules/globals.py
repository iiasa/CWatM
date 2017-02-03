# -------------------------------------------------------------------------
# Name:        globals
# Purpose:
#
# Author:      burekpe
#
# Created:     16/05/2016
# Copyright:   (c) burekpe 2016
# -------------------------------------------------------------------------

import getopt
import os.path

import ctypes
import numpy.ctypeslib as npct
import numpy as np

# for detecting on which system it is running
import platform

from management_modules.messages import *


global maskinfo,zeromap,modelSteps,xmlstring
maskinfo = {}
modelSteps=[]
xmlstring=[]

global binding, option, FlagName, Flags, ReportSteps, FilterSteps, EnsMembers, outputDir
global MMaskMap, maskmapAttr, bigmapAttr, cutmap, metadataNCDF
global timestepInit
global metaNetcdfVar

timestepInit =[]
binding = {}
option = {}
metaNetcdfVar = {}

# Initial conditions
global initCondVar,initCondVarValue
initCondVarValue = []
initCondVar = []


#date variable
global dateVar
dateVar = {}

# Output variables
global outDir, outsection, outputTyp
global outMap, outTss
outDir = {}
outMap = {}
outTss = {}
outsection = []
outputTypMap = ['daily', 'monthtot','monthavg', 'monthend','annualtot','annualavg','annualend']
outputTypTss = ['daily', 'monthtot','monthavg', 'monthend','annualtot','annualavg','annualend']

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
cdfFlag = [0, 0, 0,0,0,0,0]  # flag for netcdf output for all, steps and end, monthly (steps), yearly(steps), monthly , yearly
metadataNCDF = {}

global timeMes,TimeMesString, timeMesSum
timeMes=[]
timeMesString = []  # name of the time measure - filled in dynamic
timeMesSum = []    # time measure of hydrological modules

# -------------------------

global dirDown
dirDown = []

platform = platform.uname()[0]
python_bit = ctypes.sizeof(ctypes.c_voidp) * 8

print "Running under platform: ", platform
if python_bit  < 64:
   msg = "The Python version used is not a 64 bit version! Python " + str(python_bit) + "bit"
   raise CWATMError(msg)

path_global = os.path.dirname(__file__)
if platform == "Windows":
    dll_routing = os.path.join(os.path.split(path_global)[0],"hydrological_modules","routing_reservoirs","t4.dll")
elif platform == "CYGWIN_NT-6.1":
    # CYGWIN_NT-6.1 - compiled with cygwin
    dll_routing = os.path.join(os.path.split(path_global)[0],"hydrological_modules","routing_reservoirs","t4cyg.so")
else:
    print "Linux or something else\n"
    # Linux?
    dll_routing = os.path.join(os.path.split(path_global)[0],"hydrological_modules","routing_reservoirs","t4_linux.so")

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



# ----------------------------------
FlagName = ['quiet', 'veryquiet', 'loud',
            'checkfiles', 'noheader', 'printtime']
Flags = {'quiet': False, 'veryquiet': False, 'loud': False,
         'check': False, 'noheader': False, 'printtime': False}


def globalFlags(arg):
    """ read flags - according to the flags the output is adjusted
        quiet,veryquiet, loud, checkfiles, noheader,printtime
    """
    try:
        opts, args = getopt.getopt(arg, 'qvlcht', FlagName)
    except getopt.GetoptError:
        usage()

    for o, a in opts:
        if o in ('-q', '--quiet'):
            Flags['quiet'] = True          # Flag[0]=1
        if o in ('-v', '--veryquiet'):
            Flags['veryquiet'] = True      # Flag[1]=1
        if o in ('-l', '--loud'):
            Flags['loud'] = True  # Loud=True
        if o in ('-c', '--checkfiles'):
            Flags['check'] = True  # Check=True
        if o in ('-h', '--noheader'):
            Flags['noheader'] = True  # NoHeader=True
        if o in ('-t', '--printtime'):
            Flags['printtime'] = True      # Flag[2]=1
