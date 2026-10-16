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

Version 4 (settings file cwatm_pytests_settings4.ini): no comparison of the last discharge (test_value, last_value
removed). Error tests: expected error number from "error_number:". Water balance test (test_waterbalance): every
normal run writes the daily WaterBalance csv (adds: OUT_TSS_AreaSum_Daily = WaterBalance in the settings file),
copied after the run to output/waterbalance4/<settings file>.csv; a run of >= 30 days passes if every circle of
watercycle_balance.py (the table of cell 07 of budget/watercycle.ipynb, outlet station) has
|error / In| <= balance_threshold or |error| per year <= balance_abs_threshold [mm/yr] (section [Tests]);
a shorter run passes without the water balance check.
"""

import pytest
import time
import sys
import os
import argparse
import importlib
import shutil

# ------------------------------------------------------

# load settingsfile from command line
parser = argparse.ArgumentParser(description="load settingsfile on --settingsfile, use cwatm on --cwatm")
parser.add_argument('--settingsfile')
parser.add_argument('--cwatm')
# water balance test of each normal model run (WaterBalance output, watercycle_balance.py): on / off
parser.add_argument('--waterbalance', default='on')


# parses the settings file and the cwatm folder in the command line
args, notknownargs = parser.parse_known_args()

# parse where is the settingsfile for pytest
test_settingfile = args.settingsfile
if test_settingfile is None:
    print("option --settingsfile e.g.: pytest test_cwatm4.py --html=report.html "
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
# global flags of the cwatm package (to reset the warm flag after a calibration test)
Flags = importlib.import_module("cwatm.management_modules.globals").Flags
# module cwatm.run_cwatm (the wrapper run_cwatm.py only imports main etc.) - errornumber of the last run is stored there
cwatm_run = importlib.import_module("cwatm.run_cwatm")
# water balance test (watercycle_balance.py in this folder): WaterBalance csv of each normal model run in
# WB_CSV[settings file], the tables of all runs in output/waterbalance_summary4.csv
waterbalance = args.waterbalance.lower() != "off"
pytest_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, pytest_dir)
watercycle_balance = importlib.import_module("watercycle_balance")
WB_CSV = {}
WB_SUMMARY = os.path.join(pytest_dir, "output", "waterbalance_summary4.csv")
# copy of the WaterBalance csv of each run (the runs of a section write into the same output folder)
WB_DIR = os.path.join(pytest_dir, "output", "waterbalance4")
# the water balance is only checked for runs of at least WB_MINDAYS days (shorter runs pass without the check)
WB_MINDAYS = 30

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
    linenew = '\n'
    for line in sin:
        linenew = lreplace(line)
        sout.write(linenew)
    # a settings file without a line end at the end: the first added line would be glued to the last line
    if not linenew.endswith('\n'):
        sout.write('\n')
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
threshold = 1e-3  # water balance test: largest |error / In| of a circle (balance_threshold in [Tests])
abs_threshold = None  # or largest |error| per year of a circle [mm/yr] (balance_abs_threshold in [Tests])

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
                    if first == "balance_threshold":
                        threshold = float(secon)
                    if first == "balance_abs_threshold":
                        abs_threshold = float(secon)

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
                        # expected error number of an error test (error_number), None for the other tests
                        values1.append(None)
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
                    if first == "error_number":
                        # "error_number: 101 - text": the number, the text is a comment
                        values1[-1] = int(secon.split()[0])
                    if first == "base_setting":  # finish the setting when next one is in

                        # join to modelruns if it is not skip
                        if noskip[runs[number]]:
                            for i in range(len(set_text1)):
                                replace_setting(set_load[-1], setout1[i], changes1[i], adds1[i])
                                model = (set_text1[i], set_description1[i], changes1[i], adds1[i],
                                         setout1[i], threshold, values1[i], abs_threshold)
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
        model = (set_text1[i], set_description1[i], changes1[i], adds1[i], setout1[i], threshold, values1[i],
                 abs_threshold)
        models.append((set_description1[i], model))
        # a little bit complicated, but to make sure that the description shows up in the report

# to show the description in the report html it is separated here in the variable info
info = []
for model in models:
    info.append(model[0])


def is_normal_run(model):
    # model runs which are not error, calibration or check tests (see cwatm())
    return all(model[4].find(k) == -1 for k in ("error", "calibration", "checkmap"))


def store_waterbalance_csv(model, start):
    """WaterBalance csv written by this run, copied to WB_DIR (the next run of the section overwrites it in its
    output folder) -> WB_CSV[settings file] (None: no csv written)"""
    csvfiles = [os.path.join(d, "WaterBalance_areasum_daily.csv") for d in cwatm_globals.outDir.values()]
    csvfiles = [f for f in csvfiles if os.path.isfile(f) and os.path.getmtime(f) >= start]
    if not csvfiles:
        WB_CSV[model[4]] = None
        return
    os.makedirs(WB_DIR, exist_ok=True)
    copy = os.path.join(WB_DIR, os.path.splitext(os.path.basename(model[4]))[0] + ".csv")
    shutil.copyfile(csvfiles[0], copy)
    WB_CSV[model[4]] = copy


def write_waterbalance_summary(model, res):
    """both lists of a water balance test (1st: circles with an error check, 2nd: without) -> WB_SUMMARY, written
    new in each pytest session"""
    s = res["summary"].drop(columns="terms")
    o = res["others"].rename(columns={"why not in the 1st list": "terms"})
    o.insert(1, "passed", "not checked")
    table = pd.concat([s, o.drop(columns="info")], ignore_index=True)
    table.insert(0, "test", model[0])
    table.insert(1, "days", res["rundays"])
    table.insert(2, "threshold", res["threshold"])
    table.insert(3, "abs_threshold mm/yr", res["abs_threshold"])
    first = not os.path.isfile(WB_SUMMARY) or os.path.getmtime(WB_SUMMARY) < WB_START
    os.makedirs(os.path.dirname(WB_SUMMARY), exist_ok=True)
    table.to_csv(WB_SUMMARY, mode="w" if first else "a", header=first, index=False)


# summary csv of the water balance tests is written new in each pytest session
WB_START = time.time()
pd = importlib.import_module("pandas")


def check_report(report, csvfile):
    """
    Check report of option -c (checks.checkmap): the csv file is written and the numbers fit together.
    Every input file has a date (also files read later in the run, e.g. monthly water demand).
    """
    assert os.path.isfile(csvfile)
    assert open(csvfile, encoding="utf-8").read() == report
    lines = [line for line in report.split("\n") if line.strip()]
    header = [h.strip() for h in lines[0].split(",")]
    assert header[:3] == ["Name", "File/Value", "Create Date"]
    assert header[-4:] == ["min", "mean", "max", "Path"]
    rows = [dict(zip(header, [v.strip() for v in line.split(",")])) for line in lines[1:]]
    assert len(rows) > 100
    maprows = [r for r in rows if r["x-y"] != ""]
    assert maprows
    for r in maprows:
        assert r["valid"] in ("True", "False", "-"), r["Name"]
        assert int(r["Zero values"]) + int(r["NonZero"]) == int(r["number valid"]), r["Name"]
        if r["min"] != "":
            assert float(r["min"]) <= float(r["mean"]) <= float(r["max"]), r["Name"]
        if os.path.splitext(r["File/Value"])[1].lower() in (".nc", ".tif", ".map"):
            assert r["Create Date"] != "", r["Name"] + " " + r["File/Value"]


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
        - model[5] : float, water balance threshold (balance_threshold, used in test_waterbalance)
        - model[6] : int, expected error number of an error test (error_number), None for the other tests
        - model[7] : float, absolute water balance threshold [mm/yr] (balance_abs_threshold, test_waterbalance)

    Notes
    -----
    The function handles different test types based on keywords in the settings file path:
    - "error": Tests expected failure scenarios with quiet mode
    - "calibration": Runs a normal run, the calibration run (meteo data stored in memory) and a warm run
      from memory; the discharge of the warm run has to be the same as of the normal run
    - "checkmap": option -c, input maps are checked without a model run; the csv report is checked (check_report)
    - Default: Performs standard model run with full execution
    
    All test types use assertions to validate successful execution or expected failures.
    """
    print('\n ===== ', model[0], ' =============')
    print(" Setting file: ", model[4])
    print(" Description: ", info)
    print(" Changes: ", model[2])
    print(" Adds: ", model[3], '\n')

    if model[4].find("error") > -1:
        # test for error testing: the run has to stop with the error number of error_number
        try:
            success, last_dis = run_cwatm.main(model[4], ['-q'])
            errornumber = cwatm_run.errornumber
        except SystemExit as e:
            # Error 400: only environmental flow calculation - the run ends with sys.exit(400)
            success, errornumber = False, e.code
        assert (success == 0)
        assert errornumber == int(model[6])

    elif model[4].find("calibration") > -1:
        # test for calibration: normal run, first calibration run (meteo stored in memory), warm run from memory
        # the warm run has to give the same discharge as the normal run
        # normal run first: Flags['warm'] stays True after mainwarm (not cleared by globalclear)
        success, last_dis_normal = run_cwatm.main(model[4], ['-l'])
        assert success
        meteo, success, last_dis = run_cwatm.main(model[4], ['-lk'])
        assert success
        try:
            success, last_dis_warm = run_cwatm.mainwarm(model[4], ['-l'], meteo)
        finally:
            # following tests are normal runs again
            Flags['warm'] = False
        assert success
        print("\n discharge normal run: ", last_dis_normal, " warm run: ", last_dis_warm)
        assert last_dis_warm == last_dis_normal

    elif model[4].find("checkmap") > -1:
        # test for check: report of each input map into a csv file in PathOut (main returns the report)
        pathout = [c.split("=", 1)[1].strip() for c in model[2] if c.split("=")[0].strip() == "PathOut"][-1]
        csvfile = os.path.join(pathout, model[0] + "_check.csv")
        if os.path.exists(csvfile):
            os.remove(csvfile)
        success, report = run_cwatm.main(model[4], ['-c', csvfile])
        assert success
        assert cwatm_run.errornumber == 0
        check_report(report, csvfile)

    else:
        # test for normal model run:
        # the daily WaterBalance output for the water balance test (test_waterbalance) is in the adds: of the test
        # (cwatm_pytests_settings4.ini: OUT_TSS_AreaSum_Daily = WaterBalance)
        start = time.time()
        success, last_dis = run_cwatm.main(model[4], ['-l'])
        assert success
        if waterbalance:
            store_waterbalance_csv(model, start)




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


# area functions of replace_pcr: a float class map or a negative class id has to give Error 140
replace_pcr = importlib.import_module("cwatm.management_modules.replace_pcr")
CWATMError = importlib.import_module("cwatm.management_modules.messages").CWATMError
np = importlib.import_module("numpy")


@pytest.mark.parametrize("info, areafunction, areaclass", [
    ("Error 140: npareatotal with a float class map", "npareatotal", [1., 2., 2.]),
    ("Error 140: npareatotal with a negative class id", "npareatotal", [1, -1, 2]),
    ("Error 140: npareaaverage with a float class map", "npareaaverage", [1., 2., 2.]),
    ("Error 140: npareaaverage with a negative class id", "npareaaverage", [1, -1, 2]),
    ("Error 140: npareamaximum with a float class map", "npareamaximum", [1., 2., 2.]),
    ("Error 140: npareamaximum with a negative class id", "npareamaximum", [1, -1, 2])])
def test_area_error140(info, areafunction, areaclass):
    """
    Area functions (npareatotal, npareaaverage, npareamaximum) stop with Error 140
    if the class map is not integer or has a negative class id.
    (npareamaximum would otherwise use a negative id as index from the end, without an error)
    """
    print('\n ===== ', info, ' =============')
    with pytest.raises(CWATMError) as e:
        getattr(replace_pcr, areafunction)(np.array([1., 2., 3.]), np.array(areaclass))
    assert e.value.errornumber == 140


@pytest.mark.parametrize("info", ["Area functions with a valid class map: no error, right results"])
def test_area_valid(info):
    """
    The area functions work with an integer class map >= 0 (also a boolean map) and give the same results
    as AreaIndex; the maximum of a class with only negative values is its real maximum (not 0).
    """
    print('\n ===== ', info, ' =============')
    values = np.array([-3., -1., 5., 2., 4.])
    areaclass = np.array([1, 1, 2, 0, 2])
    assert np.array_equal(replace_pcr.npareatotal(values, areaclass), [-4., -4., 9., 2., 9.])
    assert np.array_equal(replace_pcr.npareaaverage(values, areaclass), [-2., -2., 4.5, 2., 4.5])
    assert np.array_equal(replace_pcr.npareamaximum(values, areaclass), [-1., -1., 5., 2., 5.])
    assert np.array_equal(replace_pcr.npareatotal(values, areaclass > 1), [-2., -2., 9., -2., 9.])
    index = replace_pcr.AreaIndex(areaclass, onlypositive=False)
    assert np.array_equal(index.total(values), replace_pcr.npareatotal(values, areaclass))
    assert np.array_equal(index.average(values), replace_pcr.npareaaverage(values, areaclass))
    assert np.array_equal(index.maximum(values), replace_pcr.npareamaximum(values, areaclass))
    # onlypositive: class 0 gets 0
    assert np.array_equal(replace_pcr.AreaIndex(areaclass).maximum(values), [-1., -1., 5., 0., 5.])


# settings file parsing (configuration.py): errors and warnings without a model run
configuration = importlib.import_module("cwatm.management_modules.configuration")
cwatm_globals = importlib.import_module("cwatm.management_modules.globals")
PATHOUT = "[FILE_PATHS]\nPathOut = c:/out\nPathRoot = c:/root\n"


def parse_settings_text(tmp_path, text):
    """Write text (str or bytes) as settings file, clear the globals and parse it"""
    ini = tmp_path / "settings.ini"
    if isinstance(text, bytes):
        ini.write_bytes(text)
    else:
        ini.write_text(text, encoding="utf8")
    cwatm_globals.globalclear()
    configuration.parse_configuration(str(ini))


@pytest.mark.parametrize("info, text, errornumber", [
    ("Error 116: placeholder with a missing section", PATHOUT + "[A]\nb = $(FILE_PATH:PathRoot)/x\n", 116),
    ("Error 116: placeholder with a missing key", PATHOUT + "[A]\nb = $(FILE_PATHS:PathRot)/x\n", 116),
    ("Error 141: circular placeholder", PATHOUT + "[A]\na = $(B:b)\n[B]\nb = $(A:a)\n", 141),
    ("Error 142: option not True/False or integer", PATHOUT + "[OPTIONS]\nx = Ture\n", 142),
    ("Error 143: placeholder with two colons", PATHOUT + "[A]\nb = $(FILE_PATHS:PathRoot:x)/x\n", 143),
    ("Error 143: placeholder without )", PATHOUT + "[A]\nb = $(FILE_PATHS:PathRoot/x\n", 143),
    ("Error 144: [Options] instead of [OPTIONS]", PATHOUT + "[Options]\nx = True\n", 144),
    ("Error 307: key twice in a section", PATHOUT + "[A]\na = 1\na = 2\n", 307),
    ("Error 307: section twice", PATHOUT + "[A]\na = 1\n[A]\nb = 2\n", 307),
    ("Error 307: line before the first section", "a = 1\n" + PATHOUT, 307),
    ("Error 307: line without =", PATHOUT + "[A]\njust a line\n", 307),
    ("Error 307: no UTF-8 encoding", PATHOUT.encode() + "[A]\na = M\xfcnchen\n".encode("cp1252"), 307),
    ("Error 308: no PathOut", "[A]\na = 1\n", 308),
    ("Error 145: map output with a misspelled type", PATHOUT + "[OUTPUT]\nOUT_MAP_Dayly = discharge\n", 145),
    ("Error 145: output key without MAP_ or TSS_", PATHOUT + "[OUTPUT]\nOUT_Daily = discharge\n", 145)])
def test_settings_error(tmp_path, info, text, errornumber):
    """
    A wrong settings file stops with a CWatM error number (no Python traceback)
    """
    print('\n ===== ', info, ' =============')
    with pytest.raises(CWATMError) as e:
        parse_settings_text(tmp_path, text)
    assert e.value.errornumber == errornumber


@pytest.mark.parametrize("info", ["Settings file parsing: placeholders, inline comments, options"])
def test_settings_valid(tmp_path, info):
    """
    Placeholders (also nested, repeated and with - in the name), inline comments and option values
    """
    print('\n ===== ', info, ' =============')
    text = PATHOUT + "Path-Maps = $(PathRoot)/maps\n[A]\nr = x\na = $(r)/$(r)/$(FILE_PATHS:Path-Maps)\n" \
                     "b = 500 #comment\nc = a#b\n[OPTIONS]\nt = True\nf = 0\ni = 2\n" \
                     "[OUTPUT]\nOUT_Dir = c:/out\nOUT_MAP_Daily = , discharge\nOUT_MAP_MonthAvg = a,, b ,\n" \
                     "OUT_MAP_AnnualTot = \nOUT_TSS_Daily = discharge\n"
    parse_settings_text(tmp_path, text)
    binding, option = cwatm_globals.binding, cwatm_globals.option
    assert binding["a"] == "x/x/c:/root/maps"
    assert binding["b"] == "500"
    assert binding["c"] == "a#b"
    assert option["t"] is True and option["f"] is False and option["i"] == 2
    assert cwatm_globals.outputDir == ["c:/out"]
    # output lists: empty entries are left out, no entry -> ["None"]
    outMap = cwatm_globals.outMap
    assert outMap["output_out_map_daily"] == ["discharge"]
    assert outMap["output_out_map_monthavg"] == ["a", "b"]
    assert outMap["output_out_map_annualtot"] == ["None"]
    assert cwatm_globals.outTss["output_out_tss_daily"] == ["discharge"]
    assert cwatm_globals.outsection == ["OUTPUT"]


@pytest.mark.parametrize("info, xmltext", [
    ("Error 309: metadata file without <CWATM>", '<OTHER><metanetcdf varname="a" unit="m"/></OTHER>'),
    ("Error 309: metadata entry without varname", '<CWATM><metanetcdf varname="a" unit="m"/><metanetcdf unit="m3"/></CWATM>')])
def test_metanetcdf_error(tmp_path, info, xmltext):
    """
    A wrong metaNetcdf.xml stops with Error 309 (no KeyError / IndexError)
    """
    print('\n ===== ', info, ' =============')
    xmlfile = tmp_path / "meta.xml"
    xmlfile.write_text(xmltext, encoding="utf8")
    with pytest.raises(CWATMError) as e:
        configuration.read_metanetcdf(str(xmlfile))   # absolute path: used as it is
    assert e.value.errornumber == 309


@pytest.mark.parametrize("info", ["Settings file warnings: key in two sections, misspelled key, key in wrong section"])
def test_settings_warning(tmp_path, capsys, info):
    """
    Warnings: a key in two sections with different values (parse_configuration) and
    keys which the model does not use because they are misspelled or in the wrong section (check_settings_keys)
    """
    print('\n ===== ', info, ' =============')
    text = PATHOUT + "[A]\nk = 1\nsame = 1\n[B]\nk = 2\nsame = 1\nSnowMeltRadd = 1\nkeyinoption = 3\n" \
                     "[OPTIONS]\nstopAfterSnoww = True\nuse_flow = False\nreportTss = True\n"
    parse_settings_text(tmp_path, text)
    out = capsys.readouterr().out
    assert "\"k\" is in section [A] and [B] with different values" in out
    assert "\"same\"" not in out
    assert cwatm_globals.binding["k"] == "2"

    # what the model asks for: optional keys which are not there (with these names)
    binding, option = cwatm_globals.binding, cwatm_globals.option
    assert "stopaftersnow" not in option
    assert "SnowMeltRad" not in binding
    assert "use_flow" not in binding
    assert "keyinoption" not in option
    assert "reportOldTss" not in option  # obsolete reportTss: no "misspelled" warning
    assert "PathOut" in binding
    msgs = configuration.check_settings_keys()
    assert len(msgs) == 4
    assert any("\"stopAfterSnoww\"" in m and "\"stopaftersnow\"" in m for m in msgs)
    assert any("\"SnowMeltRadd\"" in m and "\"SnowMeltRad\"" in m for m in msgs)
    assert any("\"use_flow\" in [OPTIONS] is not used" in m for m in msgs)
    assert any("\"keyinoption\" has to be in [OPTIONS]" in m for m in msgs)


# check option -c (checks.py): report of each input map, without a model run
checks = importlib.import_module("cwatm.management_modules.checks")


@pytest.fixture
def checkglobals():
    """
    Empty versioning and maskinfo for a checkmap test; afterwards the old content is put back
    (versioning: check report, file dates; maskinfo: mask of the last model run)
    """
    versioning, maskinfo = cwatm_globals.versioning, cwatm_globals.maskinfo
    saved = (dict(versioning), dict(maskinfo))
    versioning.clear()
    maskinfo.clear()
    yield cwatm_globals
    versioning.clear()
    versioning.update(saved[0])
    maskinfo.clear()
    maskinfo.update(saved[1])


def check_setup(args, inputdates=None):
    """Start of a check run as in CWATMexe: command line args after the settings file, dates of the input files"""
    cwatm_globals.versioning.update({'checkargs': args, 'loadinput': True, 'refvalue': False, 'check': "",
                                     'inputdates': inputdates if inputdates else {}})


def check_rows(text):
    """Check report (CSV text) -> header (list) and rows (list of dict: column name -> value)"""
    lines = [line for line in text.split("\n") if line.strip()]
    header = [h.strip() for h in lines[0].split(",")]
    rows = [dict(zip(header, [v.strip() for v in line.split(",")])) for line in lines[1:]]
    return header, rows


@pytest.mark.parametrize("info, args, expected", [
    ("Check files: no file", ['-c'], (None, None)),
    ("Check files: only the csv file", ['-c', 'o.csv'], (None, 'o.csv')),
    ("Check files: reference and csv file", ['-c', 'r.nc', 'o.csv'], ('r.nc', 'o.csv')),
    ("Check files: csv before reference file", ['-c', 'o.csv', 'r.nc'], ('r.nc', 'o.csv')),
    ("Check files: other option before -c", ['-l', '-c', 'r.nc', 'o.csv'], ('r.nc', 'o.csv')),
    ("Check files: extension in upper case", ['-c', 'R.NC', 'O.CSV'], ('R.NC', 'O.CSV'))])
def test_check_files(info, args, expected):
    """
    Reference netCDF and output csv file of option -c are found by their extension, in any order
    """
    print('\n ===== ', info, ' =============')
    assert checks.checkfiles(args) == expected


@pytest.mark.parametrize("info, filename, attribute, expected", [
    ("Check reference: same date", "a.nc", "a.nc 01/01/2020 10:00;", "True"),
    ("Check reference: other date", "a.nc", "a.nc 02/02/2021 11:00;", "False"),
    ("Check reference: entry without date is skipped", "a.nc", "broken;a.nc 01/01/2020 10:00;", "True"),
    ("Check reference: file name with spaces", "my map.nc", "my map.nc 01/01/2020 10:00;", "True"),
    ("Check reference: file without the list of input files", "a.nc", None, "no list of input files"),
    ("Check reference: file does not exist", "a.nc", "missing", "does not exist")])
def test_check_reference(tmp_path, capsys, checkglobals, info, filename, attribute, expected):
    """
    Comparison with the list of input files (global attribute version_inputfiles) of a reference netCDF.
    A missing reference file or a file without the list gives a warning and the check goes on without comparison.
    """
    print('\n ===== ', info, ' =============')
    Dataset = importlib.import_module("netCDF4").Dataset
    ref = str(tmp_path / "ref.nc")
    if attribute != "missing":
        with Dataset(ref, "w") as nc:
            if attribute is not None:
                nc.setncattr("version_inputfiles", attribute)
    inputfile = str(tmp_path / filename)
    check_setup(['-c', ref], {inputfile: filename + " 01/01/2020 10:00;"})
    checks.checkmap("a", inputfile, 1.0)
    header, rows = check_rows(cwatm_globals.versioning['check'])
    assert rows[0]["File/Value"] == filename
    assert rows[0]["Create Date"] == "01/01/2020 10:00"
    if expected in ("True", "False"):
        assert "Ref Date" in header
        assert rows[0]["Same Date"] == expected
    else:
        assert "Ref Date" not in header
        out = capsys.readouterr().out
        assert "CWATM Warning" in out and expected in out


@pytest.mark.parametrize("info", ["Check numbers: number valid, zero values, min/mean/max only inside the mask"])
def test_check_map_values(checkglobals, info):
    """
    Numbers of a map in the check report on a 3x4 mask with 10 cells: only cells inside the mask with a value count.
    Missing: NaN, masked, <= -9999, > 1e20. -500 is a valid value. Compressed 1D maps (readmeteo) give the same row,
    a map with another shape (meteo maps before downscaling) is not compared with the mask (valid "-").
    """
    print('\n ===== ', info, ' =============')
    # True: outside the mask
    mask = np.array([[True, False, False, False], [False, False, False, False], [False, False, False, True]])
    cwatm_globals.maskinfo.update({'mask': mask, 'shape': mask.shape, 'maskflat': mask.ravel(),
                                   'shapeflat': mask.ravel().shape})
    check_setup(['-c'])

    nan = np.nan
    # inside the mask: 0, -500, 2, 4, 6 valid - -9999, -3.4e38, 1e30, nan and the masked cell missing
    values = np.ma.masked_array([[7., 0., -500., 2.], [-9999., -3.4e38, 1e30, nan], [4., 8., 6., 1e5]],
                                mask=[[False] * 4, [False] * 4, [False, True, False, False]])
    full = np.arange(12.).reshape(3, 4)
    checks.checkmap("values", "", values)
    checks.checkmap("full", "", full)
    checks.checkmap("compressed", "", full.ravel()[~mask.ravel()])
    checks.checkmap("othershape", "", np.where(np.arange(25.).reshape(5, 5) < 2, nan, 1.))
    checks.checkmap("allmissing", "", np.full((3, 4), -9999.))
    checks.checkmap("number", "0.5", 0.5)
    header, rows = check_rows(cwatm_globals.versioning['check'])
    row = {r["Name"]: r for r in rows}

    r = row["values"]
    assert (r["x-y"], r["number valid"], r["valid"]) == ("3x4", "5", "False")
    assert (r["Zero values"], r["NonZero"]) == ("1", "4")
    assert (r["min"], r["mean"], r["max"]) == ("-500.00", "-97.60", "6.00")

    r = row["full"]
    assert (r["number valid"], r["valid"], r["Zero values"], r["NonZero"]) == ("10", "True", "0", "10")
    assert (r["min"], r["mean"], r["max"]) == ("1.00", "5.50", "10.00")
    # compressed 1D map -> same numbers
    assert {k: v for k, v in row["compressed"].items() if k != "Name"} == {k: v for k, v in r.items() if k != "Name"}

    r = row["othershape"]
    assert (r["x-y"], r["number valid"], r["valid"]) == ("5x5", "23", "-")

    r = row["allmissing"]
    assert (r["number valid"], r["valid"], r["min"], r["mean"], r["max"]) == ("0", "False", "", "", "")

    r = row["number"]
    assert r["File/Value"] == "0.5" and r["x-y"] == "" and r["number valid"] == ""


@pytest.mark.parametrize("info", ["Check: file dates by full path, row numbers and header in each check run, csv file"])
def test_check_dates_counter(tmp_path, capsys, checkglobals, info):
    """
    The date of an input file is looked up by its full path (two files with the same name in different folders).
    Each check run (versioning['check'] = "" as in CWATMexe) starts with the header and row number 1.
    save_check writes the report into the csv file given after -c.
    """
    print('\n ===== ', info, ' =============')
    filea, fileb = os.path.join("dirA", "x.nc"), os.path.join("dirB", "x.nc")
    csvfile = str(tmp_path / "check.csv")
    check_setup(['-c', csvfile], {filea: "x.nc 01/01/2001 01:00;", fileb: "x.nc 02/02/2002 02:00;"})
    capsys.readouterr()
    checks.checkmap("a", filea, 1.0)
    checks.checkmap("b", fileb, 1.0)
    checks.checkmap("c", "dirA/x.nc", 1.0)     # other separator: same file as filea
    checks.checkmap("d", os.path.join("dirC", "y.nc"), 1.0)
    header, rows = check_rows(cwatm_globals.versioning['check'])
    assert [r["Create Date"] for r in rows] == ["01/01/2001 01:00", "02/02/2002 02:00", "01/01/2001 01:00", ""]

    out = capsys.readouterr().out
    assert out.count("Name ") == 1
    assert [line.split()[0] for line in out.split("\n") if line[:1].isdigit()] == ["1", "2", "3", "4"]

    # save_check writes the report of this run
    checks.save_check()
    assert open(csvfile, encoding="utf-8").read() == cwatm_globals.versioning['check']

    # next check run in the same process (pytest, GUI): header again and row 1
    cwatm_globals.versioning['check'] = ""
    checks.checkmap("e", filea, 1.0)
    out = capsys.readouterr().out
    assert out.count("Name ") == 1
    assert [line.split()[0] for line in out.split("\n") if line[:1].isdigit()] == ["1"]

    # without a csv file after -c nothing is written
    os.remove(csvfile)
    cwatm_globals.versioning['checkargs'] = ['-c']
    checks.save_check()
    assert not os.path.exists(csvfile)


# MODFLOW (modflow6.py, modflow6_process.py): checks before MODFLOW starts, and a MODFLOW error (Fortran STOP)
# with modflow_subprocess = True ends only the child process: CWatM stops with Error 313, Python and pytest go on
modflow6 = importlib.import_module("cwatm.hydrological_modules.groundwater_modflow.modflow6")
modflow6_process = importlib.import_module("cwatm.hydrological_modules.groundwater_modflow.modflow6_process")

# a tiny MODFLOW model: TRANSIENT.tdis has a wrong block, MODFLOW stops while reading it
MF6_FILES = {
    "mfsim.nam": "BEGIN timing\n  TDIS6  TRANSIENT.tdis\nEND timing\n\n"
                 "BEGIN models\n  gwf6  TRANSIENT.nam  TRANSIENT\nEND models\n\n"
                 "BEGIN exchanges\nEND exchanges\n\n"
                 "BEGIN solutiongroup  1\n  ims6  TRANSIENT.ims  TRANSIENT\nEND solutiongroup  1\n",
    "TRANSIENT.tdis": "BEGIN wrong_block\n  nper  1\nEND wrong_block\n",
    "TRANSIENT.nam": "BEGIN packages\nEND packages\n",
    "TRANSIENT.ims": "BEGIN options\nEND options\n"}


def mf6dll_path():
    """path_mf6dll of the Burgenland test settings: the MODFLOW library of the MODFLOW tests"""
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings", "1km", "Burgenland",
                        "settings_burgenland.ini")
    for line in open(base):
        if line.split("=")[0].strip() == "path_mf6dll":
            return line.split("=", 1)[1].strip()


# inputs of the tiny model (the files are written by the tests, not by flopy)
TINY_INPUTS = dict(timestep=1, specific_storage=0, specific_yield=0, nlay=1, nrow=1, ncol=1, rowsize=1, colsize=1,
                   top=None, bottom=None, basin=np.ones((1, 1), bool), topography=None, permeability=None)


def write_tiny_model(tmp_path, missing=None):
    """Write the tiny model into tmp_path/wd with an input_hash matching TINY_INPUTS, so the files are used as
    they are (not written new)"""
    (tmp_path / "wd").mkdir()
    for name, text in MF6_FILES.items():
        if name != missing:
            (tmp_path / "wd" / name).write_text(text)
    (tmp_path / "wd" / "input_hash").write_text(modflow6.mf6_input_hash(**TINY_INPUTS))


@pytest.mark.parametrize("info", ["Error 227: binary file named in a package file (OPEN/CLOSE) is missing"])
def test_modflow_missing_binary(tmp_path, info):
    """
    A binary input file referenced inside a package file (here top.bin in TRANSIENT.dis) is missing: Error 227
    before MODFLOW starts (MODFLOW itself would end the process with a Fortran STOP)
    """
    print('\n ===== ', info, ' =============')
    write_tiny_model(tmp_path)
    (tmp_path / "wd" / "TRANSIENT.nam").write_text("BEGIN packages\n  DIS6  TRANSIENT.dis  dis\nEND packages\n")
    (tmp_path / "wd" / "TRANSIENT.dis").write_text(
        "BEGIN dimensions\n  NLAY 1\n  NROW 1\n  NCOL 1\nEND dimensions\n\nBEGIN griddata\n  top\n"
        "    OPEN/CLOSE  'top.bin'  FACTOR  1.0  (BINARY)  IPRN  1\nEND griddata\n")
    with pytest.raises(CWATMError) as e:
        modflow6_process.ModFlowProcess("transient", str(tmp_path), mf6dll_path(), head=None, load_from_disk=True,
                                        **TINY_INPUTS)
    assert e.value.errornumber == 227
    assert "top.bin" in str(e.value)


@pytest.mark.parametrize("info, subprocess, missing, errornumber", [
    ("Error 313: wrong MODFLOW input file - MODFLOW stops, Python not (modflow_subprocess = True)", True, None, 313),
    ("Error 227: missing MODFLOW input file (modflow_subprocess = True)", True, "TRANSIENT.ims", 227),
    ("Error 227: missing MODFLOW input file (modflow_subprocess = False)", False, "TRANSIENT.ims", 227),
    ("Error 226: no mfsim.nam (modflow_subprocess = True)", True, "mfsim.nam", 226),
    ("Error 226: no mfsim.nam (modflow_subprocess = False)", False, "mfsim.nam", 226)])
def test_modflow_error(tmp_path, info, subprocess, missing, errornumber):
    """
    MODFLOW with a wrong or missing input file (load_modflow_from_disk = True) stops with a CWatM error number.
    A Fortran STOP in MODFLOW (Error 313) ends only the child process, not Python.
    """
    print('\n ===== ', info, ' =============')
    write_tiny_model(tmp_path, missing)
    ModFlow = modflow6_process.ModFlowProcess if subprocess else modflow6.ModFlowSimulation
    with pytest.raises(CWATMError) as e:
        ModFlow("transient", str(tmp_path), mf6dll_path(), head=None, load_from_disk=True, **TINY_INPUTS)
    assert e.value.errornumber == errornumber
    if errornumber == 313:
        # the error report of MODFLOW and the file with the cause of the error (mfsim.lst) are in the message
        assert "Error occurred while reading file 'TRANSIENT.tdis'" in str(e.value)
        assert os.path.join(os.path.realpath(tmp_path), "wd", "mfsim.lst") in str(e.value)


@pytest.mark.parametrize("info, subprocess, binary", [
    ("MODFLOW gets recharge and pumping (modflow_subprocess = True, binary input files)", True, True),
    ("MODFLOW gets recharge and pumping (modflow_subprocess = False, binary input files)", False, True),
    ("MODFLOW gets recharge and pumping (modflow_subprocess = True, modflow_text_input = True)", True, False),
    ("MODFLOW gets recharge and pumping (modflow_subprocess = False, modflow_text_input = True)", False, False)])
def test_modflow_recharge_pumping(tmp_path, info, subprocess, binary):
    """
    Two MODFLOW cells (100 m, specific yield 0.1, no flow): recharge of 0.01 / 0.02 m raises the head by
    0.1 / 0.2 m, pumping of 100 / 300 m3 lowers it by 0.1 / 0.3 m - with binary and with text input files.
    (libmf6 6.8.1 ignores values written to BOUND - recharge and pumping have to go to RECHARGE and Q)
    """
    print('\n ===== ', info, ' =============')
    basin = np.ones((1, 2), bool)
    ModFlow = modflow6_process.ModFlowProcess if subprocess else modflow6.ModFlowSimulation
    m = ModFlow("transient", str(tmp_path), mf6dll_path(), timestep=1, specific_storage=0,
                specific_yield=np.full((1, 1, 2), 0.1), nlay=1, nrow=1, ncol=2, rowsize=100., colsize=100.,
                top=np.full((1, 2), 10.), bottom=np.zeros((1, 1, 2)), basin=basin, head=np.full((1, 2), 5.),
                topography=np.full((1, 2), 10.), permeability=np.full((1, 1, 2), 1e-9), load_from_disk=False,
                setpumpings=True, pumpingloc=basin, binary=binary)
    # binary input: the arrays and lists are in *.bin files
    assert os.path.isfile(os.path.join(str(tmp_path), "wd", "wells.bin")) == binary
    try:
        m.set_recharge(np.array([[0.01, 0.02]]))
        m.set_groundwater_abstraction(np.zeros((1, 2)))
        m.step()
        assert np.allclose(m.head, [5.1, 5.2], atol=1e-6)
        m.set_recharge(np.zeros((1, 2)))
        m.set_groundwater_abstraction(np.array([[-100., -300.]]))
        m.step()
        assert np.allclose(m.head, [5.0, 4.9], atol=1e-6)
        assert np.allclose(m.actualwell_rate, [-100., -300.])
    finally:
        m.finalize()


@pytest.mark.parametrize("info, subprocess", [
    ("MODFLOW with 2 layers (modflow_subprocess = True)", True),
    ("MODFLOW with 2 layers (modflow_subprocess = False)", False)])
def test_modflow_layers(tmp_path, info, subprocess):
    """
    Two layers (20 x 20 cells of 100 m, layer 1 80 - 100 m, layer 2 0 - 80 m, specific yield 0.1, head 95 m): heads of
    both layers; 0.002 m/day recharge for 5 days is stored in layer 1 (no drain flow below the top): +0.1 m;
    a low vertical permeability (k33) lets less water reach layer 2
    """
    print('\n ===== ', info, ' =============')
    ModFlow = modflow6_process.ModFlowProcess if subprocess else modflow6.ModFlowSimulation
    nr = nc = 20

    def run(folder, k33):
        m = ModFlow("transient", str(folder), mf6dll_path(), timestep=1, specific_storage=0,
                    specific_yield=np.full((2, nr, nc), 0.1), nlay=2, nrow=nr, ncol=nc, rowsize=100., colsize=100.,
                    top=np.full((nr, nc), 100.), bottom=np.array([np.full((nr, nc), 80.), np.zeros((nr, nc))]),
                    basin=np.ones((nr, nc), bool), head=np.full((2, nr, nc), 95.),
                    topography=np.full((nr, nc), 100.), permeability=np.ones((2, nr, nc)),
                    permeability_vertical=k33, load_from_disk=False)
        try:
            for _ in range(5):
                m.set_recharge(np.full((nr, nc), 0.002))
                m.step()
            return m.decompress(np.asarray(m.head))
        finally:
            m.finalize()

    head = run(tmp_path / "k33_1", None)
    assert head.shape == (2, nr, nc)
    assert np.allclose(head[0], 95.1, atol=1e-4)
    low = run(tmp_path / "k33_low", np.full((2, nr, nc), 1e-4))
    assert np.allclose(low[0], 95.1, atol=1e-4)
    assert (low[1] - 95.).mean() < 0.9 * (head[1] - 95.).mean()


@pytest.mark.parametrize("info, subprocess", [
    ("MODFLOW drain elevation through the pointer (modflow_subprocess = True)", True),
    ("MODFLOW drain elevation through the pointer (modflow_subprocess = False)", False)])
def test_modflow_drainage(tmp_path, info, subprocess):
    """
    Drains 2 m below the top, head 0.5 m above the drains: set_drainage with the same elevation gives the same drain
    flow, drains 0.3 m higher from step 2 stop the drain flow (the elevation reaches the running MODFLOW)
    """
    print('\n ===== ', info, ' =============')
    ModFlow = modflow6_process.ModFlowProcess if subprocess else modflow6.ModFlowSimulation
    nr = nc = 20
    top = np.full((nr, nc), 100.)

    def run(folder, raise_m):
        m = ModFlow("transient", str(folder), mf6dll_path(), timestep=1, specific_storage=0,
                    specific_yield=np.full((1, nr, nc), 0.1), nlay=1, nrow=nr, ncol=nc, rowsize=100., colsize=100.,
                    top=top, bottom=np.zeros((nr, nc)), basin=np.ones((nr, nc), bool), head=np.full((nr, nc), 98.5),
                    topography=top - 2, permeability=np.ones((1, nr, nc)), load_from_disk=False)
        flows = []
        try:
            for step in range(3):
                m.set_recharge(np.full((nr, nc), 0.001))
                if step >= 1 and raise_m is not None:
                    m.set_drainage(top - 2 + raise_m)
                m.step()
                flows.append(float(-np.sum(m.drainage)))
            return flows
        finally:
            m.finalize()

    unchanged = run(tmp_path / "a", None)
    assert run(tmp_path / "b", 0.) == unchanged
    higher = run(tmp_path / "c", 0.3)
    assert higher[0] == unchanged[0] and abs(higher[1]) < 1. and unchanged[1] > 1000.


@pytest.mark.parametrize("info", ["MODFLOW steady state with a constant head (run_only_steady_state)"])
def test_modflow_steady_state(tmp_path, info):
    """
    Steady state (folder wd_steady): 1 x 3 cells, constant head 5 m in the first cell, no recharge, drains above the
    head: the steady head is 5 m in all cells
    """
    print('\n ===== ', info, ' =============')
    m = modflow6_process.ModFlowProcess(
        "steady", str(tmp_path), mf6dll_path(), timestep=1, specific_storage=0, specific_yield=np.full((1, 1, 3), 0.1),
        nlay=1, nrow=1, ncol=3, rowsize=100., colsize=100., top=np.full((1, 3), 10.), bottom=np.zeros((1, 3)),
        basin=np.ones((1, 3), bool), head=np.full((1, 3), 3.), topography=np.full((1, 3), 10.),
        permeability=np.ones((1, 1, 3)), load_from_disk=False, solver='dbd', steady=True, perlen=1.0,
        constant_head=np.array([[5., np.nan, np.nan]]))
    try:
        m.set_recharge(np.zeros((1, 3)))
        m.step()
        assert np.allclose(m.head, 5., atol=1e-4)
    finally:
        m.finalize()
    assert os.path.isfile(os.path.join(str(tmp_path), "wd_steady", "STEADY.chd"))


@pytest.mark.parametrize("info", ["MODFLOW: one stress period solved again each day, initial head through the "
                                  "pointer, input files reused if the inputs are unchanged"])
def test_modflow_reuse(tmp_path, info):
    """
    1. One stress period solved again in each step: 0.01 m recharge per day (specific yield 0.1) raises the head
       0.1 m per day, MODFLOW's time stays 1.
    2. A second run with the same inputs reuses the input files (not written again) - with another initial head,
       which is set through the BMI pointer (not in the files).
    3. A changed input (permeability) writes the files new.
    """
    print('\n ===== ', info, ' =============')
    basin = np.ones((1, 2), bool)
    inputs = dict(timestep=1, specific_storage=0, specific_yield=np.full((1, 1, 2), 0.1), nlay=1, nrow=1, ncol=2,
                  rowsize=100., colsize=100., top=np.full((1, 2), 10.), bottom=np.zeros((1, 1, 2)), basin=basin,
                  topography=np.full((1, 2), 10.), permeability=np.full((1, 1, 2), 1e-9))
    wd = tmp_path / "wd"

    def run(head, days, **changes):
        m = modflow6.ModFlowSimulation("transient", str(tmp_path), mf6dll_path(), head=np.full((1, 2), head),
                                       load_from_disk=True, **dict(inputs, **changes))
        heads = []
        try:
            for _ in range(days):
                m.set_recharge(np.full((1, 2), 0.01))
                m.step()
                heads.append(m.head.copy())
            assert m.mf6.get_current_time() == 1.0
        finally:
            m.finalize()
        return np.array(heads)

    heads = run(5.0, 3)
    assert np.allclose(heads[:, 0], [5.1, 5.2, 5.3], atol=1e-6)
    hash1 = (wd / "input_hash").read_text()
    written = os.stat(wd / "TRANSIENT.dis").st_mtime_ns

    heads = run(6.0, 1)
    assert np.allclose(heads[0], [6.1, 6.1], atol=1e-6)
    assert os.stat(wd / "TRANSIENT.dis").st_mtime_ns == written
    assert (wd / "input_hash").read_text() == hash1

    run(5.0, 1, permeability=np.full((1, 1, 2), 2e-9))
    assert (wd / "input_hash").read_text() != hash1


def restart_settings(tmp_path, name, modflow, changes):
    """
    Bhima settings (settings_Bhima_03.ini: MODFLOW, crops) for the restart test, written to tmp_path/<name>.ini,
    output into tmp_path/<name>. changes: {key: value}, the key has to be in the settings file once, "{out}" in a
    value is the output folder
    """
    re = importlib.import_module("re")
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings", "1km", "Bhima", "settings_Bhima_03.ini")
    text = open(base, encoding="utf-8").read()
    out = str(tmp_path / name).replace(os.sep, "/")
    os.makedirs(out, exist_ok=True)
    changes = dict(changes, PathOut=out, modflow_coupling=str(modflow), OUT_MAP_Daily="discharge")
    for key, value in changes.items():
        text, n = re.subn(r"^" + key + r"\s*=.*$", (key + " = " + value.replace("{out}", out)).replace("\\", "/"),
                          text, flags=re.M)
        assert n == 1, key
    # only the outputs needed for the comparison
    totalend = "modflow_watertable" if modflow else ""
    text = re.sub(r"^OUT_MAP_TotalEnd\s*=.*$", "OUT_MAP_TotalEnd = " + totalend, text, flags=re.M | re.I)
    text = re.sub(r"^OUT_Map_MonthTot\s*=.*$", "OUT_Map_MonthTot = ", text, flags=re.M | re.I)
    settings = str(tmp_path / (name + ".ini"))
    open(settings, "w", encoding="utf-8").write(text)
    return settings, out


@pytest.mark.parametrize("info, modflow", [
    ("Restart: 2 runs (01-10/06 + 11-20/06/2013) give the same result as one run - without MODFLOW", False),
    ("Restart: 2 runs (01-10/06 + 11-20/06/2013) give the same result as one run - with MODFLOW", True)])
def test_restart(tmp_path, info, modflow):
    """
    Bhima (crops, irrigation, lakes/reservoirs): one run 01/06-20/06/2013 is compared with run A 01/06-10/06
    (saves the init file - with MODFLOW also the MODFLOW head) and run B 11/06-20/06 started from it. Discharge
    of all cells on 11-20/06 (and the MODFLOW water table at the end) have to be bit-identical.
    Run B starts in the middle of a month: crop coefficients currentKC/KY and globals.inZero (changed in place
    before 2026-10 by irr_Paddy_month) are checked too.
    """
    print('\n ===== ', info, ' =============')
    Dataset = importlib.import_module("netCDF4").Dataset
    full, out_full = restart_settings(tmp_path, "full", modflow, {"StepStart": "01/06/2013", "StepEnd": "20/06/2013",
                                                                   "save_initial": "False"})
    a, out_a = restart_settings(tmp_path, "runA", modflow, {"StepStart": "01/06/2013", "StepEnd": "10/06/2013",
                                                             "save_initial": "True", "initSave": "{out}/init",
                                                             "StepInit": "10/06/2013"})
    b, out_b = restart_settings(tmp_path, "runB", modflow, {"StepStart": "11/06/2013", "StepEnd": "20/06/2013",
                                                             "save_initial": "False", "load_initial": "True",
                                                             "initLoad": out_a + "/init_20130610.nc"})
    for settings in (full, a, b):
        success, last_dis = run_cwatm.main(settings, ['-q'])
        assert success, settings
    if modflow:
        assert os.path.isfile(out_a + "/init_20130610_modflowhead.nc")

    def read(folder, name):
        with Dataset(folder + "/" + name + ".nc") as nc:
            var = [v for v in nc.variables if nc[v].ndim >= 2][-1]
            return np.ma.filled(nc[var][:], np.nan)

    q_full, q_b = read(out_full, "discharge_daily"), read(out_b, "discharge_daily")
    assert q_full.shape[0] == 20 and q_b.shape[0] == 10
    assert np.array_equal(q_full[10:], q_b, equal_nan=True)
    if modflow:
        assert np.array_equal(read(out_full, "modflow_watertable_totalend"), read(out_b, "modflow_watertable_totalend"),
                              equal_nan=True)


@pytest.mark.parametrize("info", ["Error 315: MODFLOW does not answer within modflow_timeout (here 0.01 s)"])
def test_modflow_timeout(tmp_path, info):
    """
    If MODFLOW does not answer within modflow_timeout seconds (e.g. MODFLOW hangs), the MODFLOW process is
    stopped and CWatM stops with Error 315. Here already the start of the child process takes longer than 0.01 s.
    """
    print('\n ===== ', info, ' =============')
    write_tiny_model(tmp_path)
    with pytest.raises(CWATMError) as e:
        modflow6_process.ModFlowProcess("transient", str(tmp_path), mf6dll_path(), timeout=0.01, head=None,
                                        load_from_disk=True, **TINY_INPUTS)
    assert e.value.errornumber == 315
    # the MODFLOW process is stopped
    assert not modflow6_process._running


grid = importlib.import_module("cwatm.hydrological_modules.groundwater_modflow.grid")

# CWatM MaskMap, ModFlow input folder (modflow_basin.tif and the former index files in indices/)
OVERLAP_CASES = {
    "Burgenland (both EPSG:3035)": ("P:/watmodel/CWATM/cwatm_input_1km_burgenland/areamaps/Mask_Burgenland_1km.tif",
                                    "P:/watmodel/CWATM/cwatm_input_1km_burgenland/ModFlow_inputs/100m", 0.),
    "Bhima (lat/lon - UTM 43N)": ("P:/watmodel/CWATM/upper_bhima/FUSE/Input/areamaps/bhima.map",
                                  "P:/watmodel/CWATM/upper_bhima/FUSE/Modflow/modflow_inputs", 2e-5)}


def test_modflow_overlap_shifted():
    """One ModFlow cell (1 m) shifted by half a cell over 2 x 2 CWatM cells (1 m): 4 pairs of 0.25 m2"""
    from rasterio.transform import Affine
    pairs = grid.overlap_table(Affine(1, 0, 0.5, 0, -1, 1.5), (1, 1), "EPSG:3035", 0., 2., 1., (2, 2), "EPSG:3035")
    my, mx, cy, cx, area = pairs
    assert sorted(zip(cy.tolist(), cx.tolist())) == [(0, 0), (0, 1), (1, 0), (1, 1)]
    assert np.allclose(area, 0.25)


@pytest.mark.parametrize("info", list(OVERLAP_CASES))
def test_modflow_overlap_table(info):
    """
    The overlap table of CWatM / ModFlow cells computed from the two grids (grid.overlap_table) agrees with the
    former index files: same pairs (Bhima: plus slivers < 2 m2), area per ModFlow and per CWatM cell within tol
    """
    print('\n ===== ', info, ' =============')
    import rasterio
    mask, folder, tol = OVERLAP_CASES[info]
    if not os.path.isfile(mask):
        pytest.skip("input data not found: " + mask)
    with rasterio.open(mask) as src:
        cw_t, cw_shape, cw_crs = src.transform, src.shape, src.crs or "EPSG:4326"
    with rasterio.open(os.path.join(folder, "modflow_basin.tif")) as src:
        mf_t, mf_shape, mf_crs = src.transform, src.shape, src.crs
    my, mx, cy, cx, area = grid.overlap_table(mf_t, mf_shape, mf_crs, cw_t.c, cw_t.f, cw_t.a, cw_shape, cw_crs)
    old = [np.load(os.path.join(folder, "indices", name + ".npy"))
           for name in ("modflow_y", "modflow_x", "cwatm_y", "cwatm_x", "area")]

    def key(y, x, cwy, cwx):
        return ((y.astype(np.int64) * mf_shape[1] + x) * cw_shape[0] + cwy) * cw_shape[1] + cwx
    new_keys, old_keys = key(my, mx, cy, cx), key(*old[:4])
    assert np.isin(old_keys, new_keys).all()
    assert area[~np.isin(new_keys, old_keys)].max(initial=0) < 2.
    # area per ModFlow cell and per CWatM cell
    for (new_y, new_x, old_y, old_x, ncol) in ((my, mx, old[0], old[1], mf_shape[1]),
                                              (cy, cx, old[2], old[3], cw_shape[1])):
        new_sum = np.bincount(new_y * ncol + new_x, area)
        old_sum = np.bincount(old_y.astype(np.int64) * ncol + old_x, old[4], minlength=len(new_sum))
        assert np.max(np.abs(new_sum - old_sum)) <= tol * np.max(old_sum)


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


@pytest.mark.parametrize("info, model", [m for m in models if is_normal_run(m[1])])
def test_waterbalance(info, model):
    """
    Water balance of a normal model run of >= 30 days (runs after all test_cwatm): every circle of the daily
    WaterBalance output at the outlet (total, interception, soil, soil layers, groundwater, aquifer layers, runoff
    concentration, snow, lakes, reservoirs, channels, routing, water demand, ...) has to close:
    |error / In| <= balance_threshold or |error| per year <= balance_abs_threshold [mm/yr]. Table as in cell 07 of
    budget/watercycle.ipynb (watercycle_balance.py), all results: output/waterbalance_summary4.csv.
    A run of < 30 days and a run without WaterBalance csv pass without the check; if the model run failed, this
    test fails too (no water balance).
    """
    if not waterbalance:
        pytest.skip("--waterbalance=off")
    csvfile = WB_CSV.get(model[4], "missing")
    assert csvfile != "missing", "model run failed or did not run - no water balance"
    if csvfile is None:
        print("no WaterBalance csv written by this run - no water balance check")
        return
    res = watercycle_balance.balance(csvfile, threshold=model[5], abs_threshold=model[7])
    if res["rundays"] < WB_MINDAYS:
        print(f"run of {res['rundays']} days - water balance is checked only for runs of at least {WB_MINDAYS} days")
        return
    write_waterbalance_summary(model, res)
    print(watercycle_balance.report(res))
    absth = "" if model[7] is None else f" and |error| per year = {model[7]:g} mm/yr"
    assert res["failed"].empty, (f"{len(res['failed'])} circle(s) above |error / In| = {model[5]:g}{absth}: "
                                 + watercycle_balance.failed_text(res))





