# -------------------------------------------------------------------------
# Name:        globals
# Purpose:     Global variables, constants, and initialization functions for CWatM
#
# Author:      burekpe
# Created:     16/05/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.

# This program comes with ABSOLUTELY NO WARRANTY

# -------------------------------------------------------------------------

"""
Global variables and initialization functions for the Community Water Model (CWatM).

This module defines and manages all global variables, dictionaries, and data structures
used throughout CWatM execution. It provides centralized state management for:

- Model configuration and settings
- Spatial domain information and masking
- Time stepping and model execution flow
- Input/output data management
- Meteorological data handling
- Initial conditions and state variables
- Output reporting and NetCDF metadata
- Cross-platform shared library loading
- Command-line flag processing

The module also handles platform-specific initialization of shared libraries for
kinematic wave routing and other computational routines.

Key Global Variables
--------------------
settingsfile : list
    Storage for settings file paths
maskinfo : dict  
    Spatial mask and domain information
modelSteps : list
    Model time step configuration
binding : dict
    Variable bindings from settings files
option : dict
    Configuration options and parameters
Flags : dict
    Command-line execution flags
versioning : dict
    Version control and build information
dateVar : dict
    Date and time variable management
outDir, outMap, outTss : dict
    Output directory and file specifications
meteofiles : dict
    Meteorological input file tracking
domain, indexes : dict
    Spatial domain and indexing for MODFLOW coupling

Platform Detection
-------------------
The module automatically detects the operating system and loads appropriate
shared libraries for computational routines, supporting Windows, Linux and macOS.
"""

import getopt
import os.path
import sys

import ctypes
import numpy.ctypeslib as npct
import numpy as np

# for detecting on which system it is running
import platform

from cwatm.management_modules.messages import *

def globalclear():
    """
    Clear all global variables and data structures used in CWatM.
    
    This function resets all global dictionaries, lists, and containers to their 
    initial empty state. It is typically called during model initialization or 
    between model runs to ensure clean state.
    
    Notes
    -----
    This function clears all major global data structures including:
    - Configuration and settings (settingsfile, binding, option)
    - Model spatial information (maskinfo, geotrans, domain, indexes)
    - Time stepping and initialization data (timestepInit, modelSteps)
    - Input/output management (meteofiles, outDir, outMap, outTss)
    - Reporting and metadata structures (reportMaps*, metadataNCDF)
    - Version control and model tracking (versioning)
    """

    settingsfile.clear()
    maskinfo.clear()
    modelSteps.clear()
    xmlstring.clear()
    geotrans.clear()
    projection.clear()
    versioning.clear()
    timestepInit.clear()
    binding.clear()
    option.clear()
    metaNetcdfVar.clear()

    inputcounter.clear()
    flagmeteo.clear()
    meteofiles.clear()
    meteohandles.clear()

    initCondVarValue.clear()
    initCondVar.clear()

    dateVar.clear()

    outDir.clear()
    outMap.clear()
    outTss.clear()
    outsection.clear()
    reportTimeSerieAct.clear()
    reportMapsAll.clear()
    reportMapsSteps.clear()
    reportMapsEnd.clear()


    ReportSteps.clear()
    FilterSteps.clear()
    EnsMembers.clear()
    nrCores.clear()
    outputDir.clear()

    maskmapAttr.clear()
    bigmapAttr.clear()
    metadataNCDF.clear()

    domain.clear()
    indexes.clear()


def calibclear():
    """
    Clear global variables specifically for calibration mode.
    
    This function performs a selective clearing of global variables that need to be 
    reset between calibration runs, while preserving spatial and model structure 
    information that remains constant across calibration iterations.
    
    Notes
    -----
    This partial clearing approach optimizes calibration performance by:
    - Resetting all command-line flags to False
    - Clearing input data counters and meteorological file tracking
    - Resetting initial condition variables and date variables
    - Clearing time series output but preserving map output structure
    - Maintaining spatial domain information (maskinfo, geotrans, domain)
    - Preserving model structure (modelSteps, xmlstring) for efficiency
    """

    for i in Flags.keys():
        Flags[i] = False
    settingsfile.clear()

    inputcounter.clear()
    flagmeteo.clear()
    meteofiles.clear()
    meteohandles.clear()

    initCondVarValue.clear()
    initCondVar.clear()

    dateVar.clear()

    # outDir.clear()
    # outMap.clear()

    outTss.clear()


    # outsection.clear()
    # reportTimeSerieAct.clear()
    # reportMapsAll.clear()
    # reportMapsSteps.clear()
    # reportMapsEnd.clear()


    # ReportSteps.clear()
    # FilterSteps.clear()
    # EnsMembers.clear()
    # nrCores.clear()
    # outputDir.clear()

    # maskmapAttr.clear()
    # bigmapAttr.clear()
    # metadataNCDF.clear()

    # domain.clear()
    # indexes.clear()

    outsection.clear()
    outputDir.clear()
    binding.clear()
    option.clear()



global settingsfile
settingsfile = []

global maskinfo, zeromap, modelSteps, xmlstring, geotrans,projection
# noinspection PyRedeclaration
maskinfo = {}
modelSteps = []
xmlstring = []
geotrans = []
projection = {}

global binding, option, FlagName, Flags, ReportSteps, FilterSteps, EnsMembers, outputDir
global MMaskMap, maskmapAttr, bigmapAttr, cutmap, cutmapGlobal, cutmapFine, cutmapVfine, metadataNCDF
global timestepInit
global metaNetcdfVar
global inputcounter
global versioning
global meteofiles,meteohandles, flagmeteo

versioning = {}
timestepInit = []
binding = {}
option = {}
metaNetcdfVar = {}

inputcounter = {}
flagmeteo = {}
meteofiles = {}
meteohandles = {} # open netCDF Dataset per meteo map: name -> [Dataset, file number]

# Initial conditions
global initCondVar, initCondVarValue
initCondVarValue = []
initCondVar = []


# date variable
global dateVar
# noinspection PyRedeclaration
dateVar = {}

# Output variables
global outDir, outsection, outputTyp
global outMap, outTss
global outputTypMap,outputTypTss, outputTypTss2

outDir = {}
outMap = {}
outTss = {}
outsection = []
outputTypMap = ['daily', 'monthtot', 'monthavg', 'monthend', 'monthmid', 'annualtot', 'annualavg', 'annualend',
                'totaltot', 'totalavg', 'totalend', 'once', '12month']
"""list: Valid output types for map (NetCDF) outputs.
Defines temporal aggregation options for spatial output files including daily, 
monthly, annual, and total simulation period aggregations."""

outputTypTss = ['daily', 'monthtot', 'monthavg', 'monthend', 'annualtot', 'annualavg', 'annualend', 'totaltot',
                'totalavg']
"""list: Valid output types for time series outputs.
Similar to outputTypMap but without spatial-only options like 'once' and '12month'."""

outputTypTss2 = ['tss', 'areasum', 'areaavg']
"""list: Valid aggregation methods for time series outputs.
Defines whether time series should be point values, area sums, or area averages."""

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
cdfFlag = [0, 0, 0, 0, 0, 0, 0]  # flag for netcdf output for all, steps and end, monthly (steps), yearly(steps), monthly , yearly
metadataNCDF = {}

# groundwater modflow
global domain, indexes
domain = {}
indexes = {}

global timeMes, timeMesString, timeMesSum
timeMes = []
timeMesString = []  # name of the time measure - filled in dynamic
timeMesSum = []    # time measure of hydrological modules


global coverresult
coverresult = [False, 0]
# -------------------------
global platform1

platform1 = platform.uname()[0]

# ----------------------------------
FlagName = ['quiet', 'veryquiet', 'loud',
            'checkfiles', 'printtime', 'warranty', 'calib', 'warm', 'gui']
"""list: Valid flag names for command-line argument parsing.
Used by getopt to recognize valid command-line options."""

Flags = {'quiet': False, 'veryquiet': False, 'loud': False,
         'check': False, 'printtime': False, 'warranty': False, 'use': False,
         'test': False, 'calib': False, 'warm': False, 'gui': False, 'maskmap': False}
"""dict: Global execution flags controlling CWatM behavior.
Controls output verbosity, execution modes, and special features throughout the model."""



python_bit = ctypes.sizeof(ctypes.c_voidp) * 8
"""int: Python architecture bit size (32 or 64).
Used to ensure CWatM runs on 64-bit Python installations only."""

# print("Running under platform: ", platform1)
if python_bit < 64:
    msg = "Error 301: The Python version used is not a 64 bit version! Python " + str(python_bit) + "bit"
    raise CWATMError(msg)

path_global = os.path.dirname(__file__)

if platform1 == "Windows":
    dll_routing = os.path.join(os.path.split(path_global)[0], "hydrological_modules", "routing_reservoirs",
                               "t6.dll")
elif platform1 == "Darwin":
    # Apple: t6_mac_arm64.so (Apple silicon) or t6_mac_x86_64.so (Intel)
    if platform.machine() in ("arm64", "aarch64"):
        mac_routing = "t6_mac_arm64.so"
    else:
        mac_routing = "t6_mac_x86_64.so"
    dll_routing = os.path.join(os.path.split(path_global)[0], "hydrological_modules", "routing_reservoirs",
                               mac_routing)

else:
    print("Linux\n")
    dll_routing = os.path.join(os.path.split(path_global)[0], "hydrological_modules", "routing_reservoirs",
                               "t6_linux.so")

# dll_routing = "C:/work2/test1/t4.dll"
lib2 = ctypes.cdll.LoadLibrary(dll_routing)

# setup the return typs and argument types
# input type for the cos_doubles function
# must be a double array, with single dimension that is contiguous
array_1d_double = npct.ndpointer(dtype=np.double, ndim=1, flags='CONTIGUOUS')
array_2d_int = npct.ndpointer(dtype=np.int64, ndim=2)
array_1d_int = npct.ndpointer(dtype=np.int64, ndim=1)
# array_1d_int16 = npct.ndpointer(dtype=np.int16, ndim=1, flags='CONTIGUOUS')
# array_2d_int32 = npct.ndpointer(dtype=np.int32, ndim=2, flags='CONTIGUOUS')
array_2d_double = npct.ndpointer(dtype=np.double, ndim=2, flags='CONTIGUOUS')


lib2.ups.restype = None
lib2.ups.argtypes = [array_1d_int, array_1d_int, array_1d_double, ctypes.c_int]

lib2.dirID.restype = None
lib2.dirID.argtypes = [array_2d_int, array_2d_int, array_2d_int, ctypes.c_int, ctypes.c_int]

# lib2.repairLdd1.argtypes = [ array_2d_int, ctypes.c_int,ctypes.c_int]
lib2.repairLdd1.argtypes = [array_2d_int, ctypes.c_int, ctypes.c_int]

lib2.repairLdd2.restype = None
lib2.repairLdd2.argtypes = [array_1d_int, array_1d_int, array_1d_int, ctypes.c_int]

lib2.kinematic.restype = None
# lib2.kinematic.argtypes = [array_1d_double,array_1d_double, array_1d_int, array_1d_int, array_1d_int,  array_1d_double,  ctypes.c_double, ctypes.c_double,ctypes.c_double, ctypes.c_double, ctypes.c_int]
#                             qold            q               dirdown        diruplen     dirupid         Qnew              alpha             beta            deltaT          deltaX           size
lib2.kinematic.argtypes = [array_1d_double, array_1d_double, array_1d_int, array_1d_int, array_1d_int,
                           array_1d_double, array_1d_double, ctypes.c_double, ctypes.c_double,
                           array_1d_double, ctypes.c_int]

# parallel kinematic wave (t6 library from 2026 on): levels of the river network + parallel routing
if not hasattr(lib2, "kinematicPar"):
    msg = "Error 305: The routing library " + dll_routing + " is an old version without parallel routing\n"
    msg += "Please use the new t6 library (t6.dll, t6_linux.so, t6_mac_arm64.so or t6_mac_x86_64.so)"
    raise CWATMError(msg)
lib2.kinematicLevels.restype = ctypes.c_int
#                               dirDown       dirupLen      dirupID       size          ncells        levelOrder    levelStart
lib2.kinematicLevels.argtypes = [array_1d_int, array_1d_int, array_1d_int, ctypes.c_int, ctypes.c_int, array_1d_int, array_1d_int]
lib2.kinematicPar.restype = None
#                             Qold             q                levelOrder    levelStart    nlevels       dirupLen      dirupID
lib2.kinematicPar.argtypes = [array_1d_double, array_1d_double, array_1d_int, array_1d_int, ctypes.c_int, array_1d_int, array_1d_int,
                              array_1d_double, array_1d_double, ctypes.c_double, ctypes.c_double, array_1d_double, ctypes.c_int]
#                             Qnew             alpha            beta             deltaT           deltaX           nthreads
lib2.kinematicParMaxThreads.restype = ctypes.c_int


lib2.runoffConc.restype = None
lib2.runoffConc.argtypes = [array_2d_double, array_1d_double, array_1d_double, array_1d_double,
                             ctypes.c_int, ctypes.c_int]





def globalFlags(setting, arg, settingsfile, Flags):
    """
    Parse command-line flags and configure CWatM execution behavior.
    
    This function processes command-line arguments to set various execution flags
    that control CWatM's output verbosity, checking modes, timing, and special
    execution modes like calibration or GUI operation.
    
    Parameters
    ----------
    setting : str
        Path to the settings file for the CWatM run
    arg : list
        List of command-line arguments passed to CWatM
    settingsfile : list
        Global list to store the settings file path
    Flags : dict
        Global dictionary of boolean flags controlling execution behavior
        
    Notes
    -----
    Supported command-line flags:
    - `-q, --quiet`: Minimal output with progress dots
    - `-v, --veryquiet`: No progress output 
    - `-l, --loud`: Verbose output with timestep details
    - `-c, --checkfiles`: Input validation mode only
    - `-t, --printtime`: Print computation time for modules
    - `-w, --warranty`: Show copyright and warranty information
    - `-k, --calib`: Enable calibration mode
    - `-0, --warm`: Enable warm start/restart mode
    - `-g, --gui`: Enable GUI mode
    - `-m, --maskmap`: Enable mask map processing
    
    The function also automatically detects pytest execution environment
    and sets the 'test' flag accordingly.
    """
    # put the settingsfile name in a global variable

    settingsfile.append(setting)

    try:
        opts, args = getopt.getopt(arg, 'qvlchtwk0gm', FlagName)
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
        if o in ('-t', '--printtime'):
            Flags['printtime'] = True
        if o in ('-w', '--warranty'):
            Flags['warranty'] = True
        # PB21 calibration flag
        if o in ('-k', '--calib'):
            Flags['calib'] = True
            Flags['warm'] = False
        if o in ('-0', '--warm'):
            Flags['warm'] = True
        if o in ('-g', '--gui'):
            Flags['gui'] = True
        if o in ('-m', '--maskmap'):
            Flags['maskmap'] = True
    # if testing from pytest
    if "pytest" in sys.modules:
        Flags['test'] = True

