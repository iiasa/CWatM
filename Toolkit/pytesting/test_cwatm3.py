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
if test_settingfile == None:
    print ("option --settingsfile e.g.: pytest test_cwatm3.py --html=report.html --settingsfile=test_py_catwm1.txt --cwatm=C:/work/CWATM/run_cwatm.py")
    sys.exit()

# where is the cwatm folder, if no cwatm folder mentioned use 1 folder backwards
runcwatm = args.cwatm
if runcwatm == None:
    sys.path.append("../")
    cwatm = "run_cwatm"
else:
    path = os.path.dirname(runcwatm)
    cwatm = os.path.basename(runcwatm).split(".")[0]
    sys.path.append(path)

#print(path)
#print(cwatm) #run_cwatm
# include the cwatm folder as library
run_cwatm = importlib.import_module(cwatm, package=None)

#print(run_cwatm)

print("Settingsfile: ", test_settingfile)

# ------------------------------------------------------



def replace_setting(iset,outset,changes,adds):
    # settings und changes
    # - original settings -  "settings_rhine_5min.ini"
    # - put new setting in output directory system
    # - replace line(s)
    #     - split before and after "="
    #     - look for before code => replace full line
    # add lines at end (outputs)

    ##-------------------
    # setting_origin, setting_path_new, list with changes, list with add lines

    def lreplace(line):
        newline = line
        lookin = line.split('=')[0].strip()
        for ch in changes:
            lookfor = ch.split('=')[0].strip()
            if lookin == lookfor:
                newline = ch+'\n'
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
        sout.write(a+'\n')
    sout.close()


# =================================================================
noskip = {}
runs = []
models = []
number = 0          # number of models with variations
tvalue = False      # checks if last discharge value fits

# ---------------------
set_load = []
dict_name =[]

tin = open(test_settingfile)
test_run = False
for line in tin:
    line1 = line.lstrip()
    if len(line1)> 0:
        if line1[0] != "#":
            print (line1)
            first ,secon = line1.split(': ')
            first = first.lstrip().strip()
            secon = secon.lstrip().strip()
            if test_run == False:
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
                if first == "path_system":  PathSystem = "PathSystem = " + secon
                if first == "path_root":  PathRoot = "PathRoot = " + secon
                if first == "path_init":  PathInit = "PathInit = " + secon
                if first == "path_out":   PathOut = "PathOut = " + secon
                if first == "path_maps":  PathMaps = "PathMaps = " + secon
                if first == "path_meteo": PathMeteo = "PathMeteo = " + secon

                # settings for the individual tests
                if first == "header": set_text1.append(secon)
                if first == "description": set_description1.append(secon)
                if first == "set_save":
                    path =  os.path.dirname(set_load[-1])
                    setout1.append(os.path.join(path,secon))
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
                if first == "base_setting":    # finish the setting when next one is in

                    # join to modelruns if it is not skip
                    if  noskip[runs[number]]:
                        for i in range(len(set_text1)):
                            replace_setting(set_load[-1], setout1[i], changes1[i], adds1[i])
                            model = (set_text1[i], set_description1[i], changes1[i], adds1[i], setout1[i], tvalue, values1[i])
                            models.append((set_description1[i],model))
                            # a little bit complicated, but to make sure that the description shows up in the report
                    test_run = False
                    number += 1
                    set_load.append(secon)

tin.close()

# join to modelruns if it is not skip
if  noskip[runs[number]]:
    for i in range(len(set_text1)):
        replace_setting(set_load[-1], setout1[i], changes1[i], adds1[i])
        model = (set_text1[i], set_description1[i], changes1[i], adds1[i], setout1[i], tvalue, values1[i])
        models.append((set_description1[i],model))
        # a little bit complicated, but to make sure that the description shows up in the report

# to show the description in the report html it is separated here in the variable info
info=[]
for model in models:
    info.append(model[0])


# ===========================================================================
# ===========================================================================
def cwatm(info, model):
    """
    CWatM module
    Test of CWatM with different settingsfiles and variations
    :param info: description,
    :param model:  info, descript, changes, adds, setting, testvalue, outvalue
                    0        1        2       3       4         5         6
    :return: sucess of model run
    """
    print('\n ===== ', model[0], ' =====')
    print(" Setting file: ", model[4])
    print(" Description: ", info)
    print(" Changes: ", model[2])
    print(" Adds: ", model[3], '\n')

    if model[4].find("error")> -1:
        # test for error testing
        with pytest.raises(SystemExit,  match=model[6]) as pyt:
            run_cwatm.main(model[4], ['-q'])


    elif  model[4].find("checkmap")> -1:
        # test for check
        success, last_dis = run_cwatm.main(model[4], ['-c'])
        assert success

    else:
        # test for normal model run:
        success, last_dis = run_cwatm.main(model[4], ['-l'])
        assert success
        if model[5]:
            minvalue = model[6] * 0.99
            maxvalue = model[6] * 1.01
            assert (minvalue <= last_dis <= maxvalue)




@pytest.mark.parametrize("info", ["CWatM first test without any arguments"])
def test_cwatm_without_settings(info):
    """
    Test with CWatM runs with necessary libraries
    :return: success of model run without settingsfile
    """
    print('\n ===== CWATM without settingsfile =====')
    print (" Setting file: NONE")
    success = run_cwatm.usage()
    assert success


ii = 1
@pytest.mark.parametrize("info, model", models)
def test_cwatm(info, model): cwatm(info, model)





