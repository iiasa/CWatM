#!/usr/bin/env python3.8

"""
::

 -------------------------------------------------
 ######## ##          ##  ####  ######  ##    ##
 ##       ##          ## ##  ##   ##   ####  ####
 ##        ##        ##  ##  ##   ##   ## #### ##
 ##        ##   ##   ## ########  ##  ##   ##   ##
 ##         ## #### ##  ##    ##  ##  ##        ##
 ##         ####  #### ##      ## ## ##          ##
 ##########  ##    ##  ##      ## ## ##          ##

 Community WATer Model


CWATM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

CWATM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details
<http://www.gnu.org/licenses/>.

# --------------------------------------------------
"""

from cwatm import __author__, __version__, __date__, __copyright__, __maintainer__, __status__

# to work with some versions of Linux  - a workaround with pyexpat is needed
from pyexpat import *
import traceback

import os
import numpy as np
# to work with some versions of Linux  - a workaround with pyexpat is needed
import glob
import sys
import time
import datetime
import subprocess
from pathlib import Path


import numpy
import pandas
import scipy
import netCDF4
from osgeo import gdal
from osgeo import osr

from cwatm.management_modules.configuration import globalFlags, settingsfile, versioning, platform1, parse_configuration, read_metanetcdf, dateVar, CWATMRunInfo, outputDir, timeMesSum, timeMesString, globalclear, calibclear
from cwatm.management_modules.data_handling import Flags, cbinding
from cwatm.management_modules.timestep import checkifDate
from cwatm.management_modules.dynamicModel import ModelFrame
from cwatm.management_modules.checks import save_check
from cwatm.cwatm_model import CWATModel
from cwatm.management_modules.globals import *
from cwatm.version import *

if "modflow_coupling" in option:
    if checkOption('modflow_coupling'):
        import flopy
        import xmipy

#import xlrd
#import openpyxl
gdal.UseExceptions()

# ---------------------------


def usage():
    """
    Prints some lines describing how to use this program which arguments and parameters it accepts, etc

    * -q --quiet       output progression given as .
    * -v --veryquiet   no output progression is given
    * -l --loud        output progression given as time step, date and discharge
    * -c --check       input maps and stack maps are checked, output for each input map BUT no model run
    * -t --printtime   the computation time for hydrological modules are printed

    """
    #print('CWatM - Community Water Model')
    #print('Authors: ', __author__)
    #print('Version: ', __version__)
    #print('Date: ', __date__)
    #print('Status: ', __status__)
    print("""
    Arguments list:
    settings.ini     settings file

    -q --quiet       output progression given as .
    -v --veryquiet   no output progression is given
    -l --loud        output progression given as time step, date and discharge
    -c --check       input maps and stack maps are checked, output for each input map BUT no model run
    -t --printtime   the computation time for hydrological modules are printed
    -w --warranty    copyright and warranty information
    """)
    return True


# ==================================================

def CWATMexe(settings):
    """
    Base subroutine of the CWATM model

    * parses the settings file
    * read the information for the netcdf files
    * check if dates are alright
    * check flags for screen output
    * runs the model


    """
    parse_configuration(settings)
    # print option
    # print binding
    # read all the possible option for modelling and for generating output
    # read the settings file with all information about the catchments(s)
    # read the meta data information for netcdf outputfiles
    read_metanetcdf('metaNetcdf.xml')

    # os.chdir(outputDir[0])
    # this prevent from using relative path in settings!

    checkifDate('StepStart', 'StepEnd', 'SpinUp', cbinding('PrecipitationMaps'))
    # checks if end date is later than start date and puts both in modelSteps
    if Flags['check']:
        dateVar["intEnd"] = dateVar["intStart"]
        versioning['check'] = ""
        versioning['loadinput'] = True
        versioning['refvalue'] = False

    CWATM = CWATModel()
    stCWATM = ModelFrame(CWATM, firstTimestep=dateVar["intStart"], lastTimeStep=dateVar["intEnd"])

    """
    ----------------------------------------------
    Deterministic run
    ----------------------------------------------
    """
    if not(Flags['veryquiet']):
        print(CWATMRunInfo([outputDir[0], settingsfile[0]]))
    start_time = datetime.datetime.now().time()
    if Flags['loud']:
        print("%-6s %10s %11s\n" % ("Step", "Date", "Discharge"), end=' ')

    stCWATM.run()

    # cProfile.run('stLisflood.run()')
    # python -m cProfile -o  l1.pstats cwatm.py settings1.ini
    # gprof2dot -f pstats l1.pstats | dot -T png -o callgraph.png
    # pyreverse -AS -f ALL -o png cwatm.py -p Main

    if Flags['printtime']:
        print("\n\nTime profiling")
        print("%2s %-17s %10s %8s" % ("No", "Name", "time[s]", "%"))

        timeSum = np.array(timeMesSum)
        timePrint = timeSum
        for i in range(len(timePrint)):
            print("%2i %-17s %10.2f %8.1f" % (i, timeMesString[i], timePrint[i], 100 * timePrint[i] / timePrint[-1]))

    if Flags['loud']:
        current_time = datetime.datetime.now().time()
        print("\nStart: " + start_time.isoformat())
        print("End:   " + current_time.isoformat())

    # return with last value and true for successfull run for pytest
    if Flags['calib']:
        return (CWATM.var.meteo,True, CWATM.var.firstout)
    else:
        return(True, CWATM.var.firstout)

def CWATMexe2(settings,meteo):
    """
    Base subroutine of the CWATM model for calibration

    * parses the settings file
    * read the information for the netcdf files
    * check if dates are alright
    * check flags for screen output
    * loads meteo data from MEMORY
    * runs the model


    """
    parse_configuration(settings)
    read_metanetcdf('metaNetcdf.xml')

    checkifDate('StepStart', 'StepEnd', 'SpinUp', cbinding('PrecipitationMaps'))
    # checks if end date is later than start date and puts both in modelSteps

    days = 1 + dateVar["intEnd"] - dateVar["intStart"]
    for i in inputcounter.keys():
        inputcounter[i] = inputcounter[i] - days


    CWATM = CWATModel()
    # if GUI calls to check the maskmap
    if Flags['maskmap']:  return
    CWATM.var.meteo = meteo

    stCWATM = ModelFrame(CWATM, firstTimestep=dateVar["intStart"], lastTimeStep=dateVar["intEnd"])

    start_time = datetime.datetime.now().time()
    if Flags['loud']:
        print("%-6s %10s %11s\n" % ("Step", "Date", "Discharge"), end=' ')

    stCWATM.run()

    if Flags['printtime']:
        print("\n\nTime profiling")
        print("%2s %-17s %10s %8s" % ("No", "Name", "time[s]", "%"))

        timeSum = np.array(timeMesSum)
        timePrint = timeSum
        for i in range(len(timePrint)):
            print("%2i %-17s %10.2f %8.1f" % (i, timeMesString[i], timePrint[i], 100 * timePrint[i] / timePrint[-1]))


    # return with last value and true for successfull run for pytest
    return(True, CWATM.var.firstout)





# ==================================================
# ============== USAGE ==============================
# ==================================================


def GNU():
    """
    prints GNU General Public License information

    """

    print('CWatM - Community Water Model')
    print('Authors: ', __author__)
    print('Version: ', __version__)
    print('Date: ', __date__)
    print()
    print("""
    CWATM is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details
    <http://www.gnu.org/licenses/>.
    """)
    sys.exit(1)


def headerinfo(usage=0):
    """
    Print the information on top of each run
    
    this is collecting the last change of one of the source files
    in order to give more information of the settingsfile and the version of cwatm
    this information is put in the result files .tss and .nc
    """
    versioning['git'] = get_version_info()
    versioning['exe'] = __file__
    versioning['lastdate'] = versioning['git'] ['build_timestamp'][0:10]
    __date__ = versioning['lastdate']
    versioning['lastfile'] = "___"
    # versioning all input files
    versioning['input'] = ""


    realPath = os.path.dirname(os.path.realpath(versioning['exe']))


    versioning['version'] = __version__
    versioning['platform'] = platform1
    hash = versioning['git']['git_branch'] + " " + versioning['git']['git_short_hash']

    # test git hash agains current version
    try:
        repo_path = Path(__file__).parents[1]

        result = subprocess.run(["git", "diff", "--name-only",
                   versioning['git']['git_hash']],cwd=repo_path, capture_output=True, text=True, check=True)
        all_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]

        # Filter for .py files and exclude version.py
        python_files = []
        for file_path in all_files:
            path = Path(file_path)
            if (path.suffix == '.py' and
                    path.name != 'version.py' and
                    'version.py' not in str(path)):
                python_files.append(file_path)



        if python_files !=[]:
            veri = " dirty "
        else:
            veri = " verified "
    except:
        veri = " not checked "


    s = "CWATM - Community Water Model Version: " + hash + veri +", Date: " + versioning['lastdate'] + "\n"
    s += "International Institute of Applied Systems Analysis (IIASA)\n"
    s += "Running under platform: " + platform1 + "\n"
    s += "-----------------------------------------------------------"


    if usage == 1:
        if veri == " verified ":
            s += "\nNo change to last git commit\n"
        elif veri == " not checked ":
            s += "\nGit cannot be checked\n"
        else:
            s += "\nChanged files to last git commit:\n"
            for pyf in python_files:
                s += pyf +"\n"


    if not (Flags['veryquiet']) and not (Flags['quiet']):
        print (s)

    return s

def mainwarm(settings, args, meteo):
    success = False
    #print ("Warm start CWatM")

    calibclear()
    if ("pytest" in sys.modules) or ("PySide6" in sys.modules):
        globalclear()

    globalFlags(settings, args, settingsfile, Flags)
    Flags['warm'] = True

    s = headerinfo()

    if Flags['gui']:
        Flags['warm'] = False
        if Flags['maskmap']:
            CWATMexe2(settingsfile[0], meteo)
            return dateVar['maskmap']
        else:
            try:
                success, last_dis = CWATMexe2(settingsfile[0], meteo)
                return success, last_dis
            except Exception as e:
                # return in a controlled way with success = False
                traceback.print_exc()
                return False, 0

    
    if isinstance(meteo, np.ndarray):
        success, last_dis = CWATMexe2(settingsfile[0],meteo)
    else:
        Flags['warm'] = False
        success, last_dis = CWATMexe(settingsfile[0])
    return success, last_dis



def main(settings, args):
    success = False
    # Check if excution comes from pytest or from GUi -> delete all info from previous runs
    if ("pytest" in sys.modules) or ("PySide6" in sys.modules):
        globalclear()

    globalFlags(settings, args, settingsfile, Flags)
    if Flags['use']:
        usage()
    if Flags['warranty']:
        GNU()
    # setting of global flag e.g checking input maps, producing more output information
    headerinfo()

    if Flags['calib']:
        meteo,success, last_dis = CWATMexe(settingsfile[0])
        Flags['calib'] = False
        return meteo,success, last_dis
    else:
        try:
            if Flags['check']:
                Flags['warm'] = False
                versioning['checkargs'] = args
                success, last_dis = CWATMexe(settingsfile[0])
                save_check()
                last_dis = versioning['check']
                versioning.clear()
                Flags['check'] = False
                return success, last_dis

            else:
                success, last_dis = CWATMexe(settingsfile[0])
                return success, last_dis
        except Exception as e:
            # return in a controlled way with success = False
            traceback.print_exc()
            return False, 0


def parse_args():
    if len(sys.argv) < 2:
        headerinfo(1)
        usage()
        sys.exit(0)
    else:
        return sys.argv[1],sys.argv[2:]


def run_from_command_line():
    settings, args = parse_args()
    main(settings, args)

if __name__ == "__main__":
    settings, args = parse_args()
    main(settings, args)
