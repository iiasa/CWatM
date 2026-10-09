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
binding : KeyTrackDict
    Variable bindings from settings files (records used / missing keys)
option : KeyTrackDict
    Configuration options and parameters (records used / missing keys)
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
    - Model spatial information (maskinfo, domain, indexes)
    - Input/output management (meteofiles, outDir, outMap, outTss)
    - Reporting and metadata structures (reportMaps*, metadataNCDF)
    - Version control and model tracking (versioning)
    """

    settingsfile.clear()
    maskinfo.clear()
    projection.clear()
    versioning.clear()
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
    outputDir.clear()

    maskmapAttr.clear()
    bigmapAttr.clear()
    metadataNCDF.clear()

    domain.clear()
    indexes.clear()

    # time measures (option -t): otherwise a second run in the same process adds to the first one
    timeMes.clear()
    timeMesString.clear()
    timeMesSum.clear()


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
    - Maintaining spatial domain information (maskinfo, domain)
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

    # kept from the previous run: outDir, outMap, reportTimeSerieAct, reportMaps*, maskmapAttr, bigmapAttr,
    # metadataNCDF, domain, indexes
    outTss.clear()
    outsection.clear()
    outputDir.clear()
    binding.clear()
    option.clear()

    # time measures (option -t) of the previous run
    timeMes.clear()
    timeMesString.clear()
    timeMesSum.clear()


class KeyTrackDict(dict):
    """
    Dict for the settings (binding, option) which records the keys the model asks for.

    Reading a key (d[key], key in d, d.get(key)) adds it to used if it is there and to missing if not.
    configuration.check_settings_keys uses this after the first time step to find misspelled keys:
    a key in the settings file which is never used, close to a key the model asked for but did not find.
    Writing, iteration and .keys() are not recorded.

    Attributes
    ----------
    used : set
        Keys which are in the dict and were read
    missing : set
        Keys which were asked for but are not in the dict
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.used = set()
        self.missing = set()

    def __getitem__(self, key):
        self.used.add(key)
        return dict.__getitem__(self, key)

    def __contains__(self, key):
        if dict.__contains__(self, key):
            self.used.add(key)
            return True
        self.missing.add(key)
        return False

    def get(self, key, default=None):
        if dict.__contains__(self, key):
            self.used.add(key)
        else:
            self.missing.add(key)
        return dict.get(self, key, default)

    def clear(self):
        self.used.clear()
        self.missing.clear()
        dict.clear(self)


# module variables, shared with the other modules by "from ... import *"
# (lists and dicts must be changed in place, e.g. .clear(), not reassigned - otherwise the other modules keep the old one)
settingsfile = []

maskinfo = {}
projection = {}

versioning = {}
binding = KeyTrackDict()
option = KeyTrackDict()
metaNetcdfVar = {}

inputcounter = {}
flagmeteo = {}
meteofiles = {}
meteohandles = {} # open netCDF Dataset per meteo map: name -> [Dataset, file number]

# Initial conditions
initCondVarValue = []
initCondVar = []


# date variable
dateVar = {}

# Output variables
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

outputDir = []

maskmapAttr = {}
bigmapAttr = {}
cutmap = [0, 1, 0, 1]
cutmapGlobal = [0, 1, 0, 1]
cutmapFine = [0, 1, 0, 1]
cutmapVfine = [0, 1, 0, 1]
metadataNCDF = {}

# groundwater modflow
domain = {}
indexes = {}

# time measures (option -t)
timeMes = []
timeMesString = []  # name of the time measure - filled in dynamic
timeMesSum = []    # time measure of hydrological modules


coverresult = [False, 0]
# -------------------------

# sys.platform is instant; platform.uname() takes 0.3 s (Python 3.12) to 3 s (Python 3.8) on Windows
# (it also asks for the computer name). Same values as platform.uname()[0]: Windows, Darwin, Linux
platform1 = {"win32": "Windows", "darwin": "Darwin"}.get(sys.platform)
if platform1 is None:
    platform1 = platform.system()

# ----------------------------------
FlagName = ['quiet', 'veryquiet', 'loud',
            'check', 'printtime', 'warranty', 'calib', 'warm', 'gui', 'maskmap', 'error']
"""list: Valid flag names for command-line argument parsing.
Used by getopt to recognize valid command-line options."""

Flags = {'quiet': False, 'veryquiet': False, 'loud': False,
         'check': False, 'printtime': False, 'warranty': False, 'use': False,
         'test': False, 'calib': False, 'warm': False, 'gui': False, 'maskmap': False, 'error': False}
"""dict: Global execution flags controlling CWatM behavior.
Controls output verbosity, execution modes, and special features throughout the model.
Set by globalFlags from the command line (see FlagName), except two internal flags:
'use' (unknown command-line option -> show the usage) and 'test' (run from pytest)."""



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
    # Linux (and all other systems): t6_linux.so is built for x86_64 - on other processors (e.g. aarch64) Error 306
    dll_routing = os.path.join(os.path.split(path_global)[0], "hydrological_modules", "routing_reservoirs",
                               "t6_linux.so")

# dll_routing = "C:/work2/test1/t4.dll"
try:
    lib2 = ctypes.cdll.LoadLibrary(dll_routing)
except OSError as e:
    msg = "Error 306: The routing library (t6) cannot be loaded:\n" + dll_routing + "\n"
    if not os.path.isfile(dll_routing):
        msg += "The file does not exist. Please copy the t6 library for " + platform1 + " into this folder\n"
    else:
        msg += "The file exists but cannot be used: it may be built for another system or processor (" + \
               platform1 + " " + platform.machine() + ", Python " + str(python_bit) + " bit),\n" + \
               "or a library it needs is missing (on Windows e.g. mingw64 not in the PATH)"
    # the Python reason (e) is printed by print_cwatm_error
    raise CWATMError(msg) from e

# setup the return types and argument types
# arrays given to the C functions must have the right type and be contiguous: the C code reads them as one block
# (a non-contiguous view, e.g. a slice with a step, gives a ctypes ArgumentError instead of wrong values)
array_1d_double = npct.ndpointer(dtype=np.double, ndim=1, flags='CONTIGUOUS')
array_2d_int = npct.ndpointer(dtype=np.int64, ndim=2, flags='CONTIGUOUS')
array_1d_int = npct.ndpointer(dtype=np.int64, ndim=1, flags='CONTIGUOUS')
array_2d_double = npct.ndpointer(dtype=np.double, ndim=2, flags='CONTIGUOUS')


lib2.ups.restype = None
lib2.ups.argtypes = [array_1d_int, array_1d_int, array_1d_double, ctypes.c_int]

lib2.dirID.restype = None
lib2.dirID.argtypes = [array_2d_int, array_2d_int, array_2d_int, ctypes.c_int, ctypes.c_int]

lib2.repairLdd1.restype = None
lib2.repairLdd1.argtypes = [array_2d_int, ctypes.c_int, ctypes.c_int]

lib2.repairLdd2.restype = None
lib2.repairLdd2.argtypes = [array_1d_int, array_1d_int, array_1d_int, ctypes.c_int]

# (the serial routing lib2.kinematic is still in the t6 library but not used any more: kinematicPar below)

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
    - `-c, --check`: Input validation mode only
    - `-t, --printtime`: Print computation time for modules
    - `-w, --warranty`: Show copyright and warranty information
    - `-e, --error`: Error messages with the code lines where the error occurred
    - `-k, --calib`: Enable calibration mode
    - `-0, --warm`: Enable warm start/restart mode
    - `-g, --gui`: Enable GUI mode
    - `-m, --maskmap`: Enable mask map processing
    
    Internal flags (no command-line option):
    - 'use': set if getopt finds an unknown option -> run_cwatm shows the usage
    - 'test': set if CWatM runs from pytest (pytest in sys.modules)
    """
    # put the settingsfile name in a global variable

    settingsfile.append(setting)

    try:
        opts, args = getopt.getopt(arg, 'qvlctwk0gme', FlagName)
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
        if o in ('-c', '--check'):
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
        if o in ('-e', '--error'):
            Flags['error'] = True
    # if testing from pytest
    if "pytest" in sys.modules:
        Flags['test'] = True

