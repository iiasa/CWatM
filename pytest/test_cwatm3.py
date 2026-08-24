"""
CWatM Testing Framework

A comprehensive pytest-based testing framework for the CWatM (Community Water Model)
hydrological modeling system. This module provides automated testing capabilities
for multiple model configurations, scenarios, and validation workflows.

The framework supports:
- Configuration-driven test scenarios from external settings files
- Multiple test types: normal runs, calibration, checkmap validation, error testing
- Dynamic settings file generation with parameter modifications
- Parametrized testing for systematic model validation
- HTML reporting integration for test results

The testing system reads test configurations from a structured settings file
that defines base configurations, parameter changes, and expected outcomes,
then generates individual test cases for comprehensive model validation.
"""

import pytest
import time
import sys
import os
import argparse
import importlib

# ------------------------------------------------------

# load settingsfile from command line
parser = argparse.ArgumentParser(description="load settingsfile on --settingsfile, use cwatm on --cwatm")
parser.add_argument('--settingsfile')
parser.add_argument('--cwatm')



# parses the settings file and the cwatm folder in the command line
args, notknownargs = parser.parse_known_args()

# parse where is the settingsfile for pytest
test_settingfile = args.settingsfile
if test_settingfile is None:
    print("option --settingsfile e.g.: pytest test_cwatm3.py --html=report.html "
          "--settingsfile=test_py_catwm1.txt --cwatm=C:/work/CWATM/run_cwatm.py")
    sys.exit()

# where is the cwatm folder, if no cwatm folder mentioned use 1 folder backwards
runcwatm = args.cwatm
if runcwatm is None:
    sys.path.append("../")
    cwatm = "run_cwatm"
else:
    path = os.path.dirname(runcwatm)
    cwatm = os.path.basename(runcwatm).split(".")[0]
    sys.path.append(path)

# print(path)
# print(cwatm)  # run_cwatm
# include the cwatm folder as library

run_cwatm = importlib.import_module(cwatm, package=None)

"""
set =  "P:/watmodel/cwatmpublic/develop/pytest/settings/1min/UpperDanube/settings_upper_1min_01.ini"
success, last_dis = run_cwatm.main(set, ['-c'])
set = "P:/watmodel/cwatmpublic/develop/pytest/settings/1min/Morava/settings_calibration_1min.ini"
meteo,success, last_dis = run_cwatm.main(set, ['-lk'])
success, last_dis = run_cwatm.mainwarm(set, ['-l'], meteo)
#set = "P:/watmodel/cwatmpublic/develop/pytest/settings/30min/global_30min/settings_global_30min_08.ini"
set = "P:/watmodel/cwatmpublic/develop/pytest/settings/1km/Burgenland/settings_burgenland_03.ini"
success, last_dis = run_cwatm.main(set, ['-l'])
set = "P:/watmodel/cwatmpublic/develop/pytest/settings/1km/Bhima/settings_Bhima_01.ini"
success, last_dis = run_cwatm.main(set, ['-l'])
#print(run_cwatm)

"""
print("Settingsfile: ", test_settingfile)

# ------------------------------------------------------



def replace_setting(iset, outset, changes, adds):
    """
    Create a modified configuration file with parameter changes and additions.
    
    Reads an original settings file, replaces specified parameter lines, and adds
    new configuration lines to create a new settings file for testing.
    
    Parameters
    ----------
    iset : str
        Path to the input/original settings file
    outset : str  
        Path to the output settings file to be created
    changes : list of str
        List of parameter changes in format "parameter = value"
        Lines matching the parameter name (before "=") will be replaced
    adds : list of str
        List of additional configuration lines to append to the file
    
    Notes
    -----
    The function processes the original settings file line by line:
    - Splits each line at "=" to identify parameter names
    - Replaces lines where parameter names match those in changes list
    - Appends all lines from adds list to the end of the file
    """

    def lreplace(line):
        newline = line
        lookin = line.split('=')[0].strip()
        for ch in changes:
            lookfor = ch.split('=')[0].strip()
            if lookin == lookfor:
                newline = ch + '\n'
        return newline

    sin = open(iset)
    sout = open(outset, "wt")
    for line in sin:
        linenew = lreplace(line)
        sout.write(linenew)
    sin.close()
    sout.close()
    sout = open(outset, "a")
    for a in adds:
        sout.write(a + '\n')
    sout.close()


# =================================================================
noskip = {}
runs = []
models = []
number = 0  # number of models with variations
tvalue = False  # checks if last discharge value fits

# ---------------------
set_load = []
dict_name = []

tin = open(test_settingfile)
test_run = False
for line in tin:
    line1 = line.lstrip()
    if len(line1) > 0:
        if line1[0] != "#":
            if line1[0] != "[":
                print(line1)
                first, secon = line1.split(': ')
                first = first.lstrip().strip()
                secon = secon.lstrip().strip()
                if test_run is False:
                    # initial setting of a test case
                    if first == "base_setting":
                        set_load.append(secon)
                    if first == "name":
                        set1 = dict_name.append(secon)
                        test_run = True
                        setout1 = []
                        set_text1 = []
                        set_description1 = []
                        changes1 = []
                        adds1 = []
                        values1 = []

                    if first == "runtest":
                        s = secon.split()
                        runs.append(s[0])
                        noskip[runs[-1]] = False
                        if s[1].upper() == "TRUE":
                            noskip[runs[-1]] = True
                    if first == "test_value":
                        if secon.upper() == "TRUE":
                            tvalue = True

                else:
                    if first == "path_system":
                        PathSystem = "PathSystem = " + secon
                    if first == "path_root":
                        PathRoot = "PathRoot = " + secon
                    if first == "path_init":
                        PathInit = "PathInit = " + secon
                    if first == "path_out":
                        PathOut = "PathOut = " + secon
                    if first == "path_maps":
                        PathMaps = "PathMaps = " + secon
                    if first == "path_meteo":
                        PathMeteo = "PathMeteo = " + secon

                    # settings for the individual tests
                    if first == "header":
                        set_text1.append(secon)
                    if first == "description":
                        set_description1.append(secon)
                    if first == "set_save":
                        path = os.path.dirname(set_load[-1])
                        setout1.append(os.path.join(path, secon))
                    if first == "changes":
                        s = [x.lstrip().strip() for x in secon.split(';')]
                        s.append(PathSystem)
                        s.append(PathRoot)
                        s.append(PathInit)
                        s.append(PathOut)
                        s.append(PathMaps)
                        s.append(PathMeteo)
                        changes1.append(s)

                    if first == "adds":
                        s = [x.lstrip().strip() for x in secon.split(';')]
                        adds1.append(s)
                    if first == "last_value":
                        try:
                            values1.append(float(secon))
                        except:
                            values1.append(secon[6:9])
                    if first == "base_setting":  # finish the setting when next one is in

                        # join to modelruns if it is not skip
                        if noskip[runs[number]]:
                            for i in range(len(set_text1)):
                                replace_setting(set_load[-1], setout1[i], changes1[i], adds1[i])
                                model = (set_text1[i], set_description1[i], changes1[i], adds1[i],
                                         setout1[i], tvalue, values1[i])
                                models.append((set_description1[i], model))
                                # a little bit complicated, but to make sure that the description shows up in the report
                        test_run = False
                        number += 1
                        set_load.append(secon)

tin.close()

# join to modelruns if it is not skip
if noskip[runs[number]]:
    for i in range(len(set_text1)):
        replace_setting(set_load[-1], setout1[i], changes1[i], adds1[i])
        model = (set_text1[i], set_description1[i], changes1[i], adds1[i], setout1[i], tvalue, values1[i])
        models.append((set_description1[i], model))
        # a little bit complicated, but to make sure that the description shows up in the report

# to show the description in the report html it is separated here in the variable info
info = []
for model in models:
    info.append(model[0])


# ===========================================================================
# ===========================================================================
def cwatm(info, model):
    """
    Execute CWatM model tests with different configurations and settings.
    
    Runs the CWatM hydrological model with specified settings and validates
    execution based on the test type (normal run, calibration, checkmap, or error testing).
    
    Parameters
    ----------
    info : str
        Test description for reporting purposes
    model : tuple
        Model configuration tuple containing:
        - model[0] : str, test header/title
        - model[1] : str, test description  
        - model[2] : list, parameter changes
        - model[3] : list, additional configuration lines
        - model[4] : str, path to settings file
        - model[5] : bool, whether to validate discharge values
        - model[6] : float, expected discharge value for validation
        
    Notes
    -----
    The function handles different test types based on keywords in the settings file path:
    - "error": Tests expected failure scenarios with quiet mode
    - "calibration": Runs calibration workflow with meteorological data loading
    - "checkmap": Validates model configuration without full execution  
    - Default: Performs standard model run with full execution
    
    All test types use assertions to validate successful execution or expected failures.
    """
    print('\n ===== ', model[0], ' =============')
    print(" Setting file: ", model[4])
    print(" Description: ", info)
    print(" Changes: ", model[2])
    print(" Adds: ", model[3], '\n')

    if model[4].find("error") > -1:
        # test for error testing
        # with pytest.raises(SystemExit,  match=model[4]) as pyt:
        #     run_cwatm.main(model[4], ['-q'])
        success, last_dis = run_cwatm.main(model[4], ['-q'])
        assert (success == 0)

    elif model[4].find("calibration") > -1:
        # test for check
        meteo, success, last_dis = run_cwatm.main(model[4], ['-lk'])
        success, last_dis = run_cwatm.mainwarm(model[4], ['-l'], meteo)
        assert success

    elif model[4].find("checkmap") > -1:
        # test for check
        success, last_dis = run_cwatm.main(model[4], ['-c'])
        assert success

    else:
        # test for normal model run:
        success, last_dis = run_cwatm.main(model[4], ['-l'])
        assert success
        """
        if model[5]:
            minvalue = model[6] * 0.99
            maxvalue = model[6] * 1.01
            assert (minvalue <= last_dis <= maxvalue)
        """




@pytest.mark.parametrize("info", ["CWatM first test without any arguments"])
def test_cwatm_without_settings(info):
    """
    Test CWatM library import and basic functionality without settings file.
    
    Validates that the CWatM module can be imported and its usage function
    executes successfully without requiring a settings file. This serves as
    a basic smoke test for the testing infrastructure.
    
    Parameters
    ----------
    info : str
        Test description passed by pytest parametrize decorator
        
    Notes
    -----
    This test verifies the fundamental CWatM setup by calling the usage() function
    which should execute without errors when no settings file is provided.
    """
    print('\n ===== CWATM without settingsfile =====')
    print(" Setting file: NONE")
    success = run_cwatm.usage()
    assert success


ii = 1
@pytest.mark.parametrize("info, model", models)
def test_cwatm(info, model):
    """
    Parameterized test function for CWatM model execution with various configurations.
    
    This is the main test function that executes all configured CWatM test scenarios.
    Each test case is defined by the model configuration and runs through the cwatm() 
    function which handles different test types (normal, calibration, checkmap, error).
    
    Parameters
    ----------
    info : str
        Test description for the specific model configuration
    model : tuple
        Complete model configuration tuple containing settings file path,
        parameter changes, additional configurations, and validation criteria
        
    Notes
    -----
    This function is parameterized using pytest.mark.parametrize with the models
    list that contains all test configurations parsed from the settings file.
    Each model configuration generates a separate test case in the pytest execution.
    """
    cwatm(info, model)





