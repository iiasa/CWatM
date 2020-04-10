import pytest
import time
import sys
import argparse

sys.path.append("../")
#import cwatm3
import run_cwatm


# ------------------------------------------------------

# load settingsfile from command line
parser = argparse.ArgumentParser(description="load settingsfile on --settingsfile")
parser.add_argument('--settingsfile')
args, notknownargs = parser.parse_known_args()
test_settingfile = args.settingsfile




if test_settingfile == None:
    print ("option --settingsfile e.g.: pytest test_cwatm3.py --html=report.html --settingsfile=test_py_catwm1.txt")
    sys.exit()

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

sets = {}
setout = {}
set_text = {}
set_description = {}
changes = {}
adds = {}
values = {}

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
            first ,secon = line1.split(': ')
            first = first.lstrip().strip()
            secon = secon.lstrip().strip()
            if test_run == False:
                # initial setting of a test case
                if first == "base": set_load.append(secon)
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
                    s = [x.lstrip().strip() for x in secon.split(';')]
                    for i in range(len(s)//2):
                        runs.append(s[i*2])
                        noskip[runs[i]] = False
                        if s[i*2+1].upper() == "TRUE":
                            noskip[runs[i]] = True
                if first == "test_value":
                    if secon.upper() == "TRUE":
                        tvalue = True


            else:
                # settings for the individual tests
                if first == "header": set_text1.append(secon)
                if first == "description": set_description1.append(secon)
                if first == "set_save": setout1.append(secon)
                if first == "changes":
                    s = [x.lstrip().strip() for x in secon.split(';')]
                    changes1.append(s)
                if first == "adds":
                    s = [x.lstrip().strip() for x in secon.split(';')]
                    adds1.append(s)
                if first == "last_value": values1.append(float(secon))
                if first == "base":

                    sets1 = []
                    number = len(set_text1)
                    for i in range(number):
                        replace_setting(set_load[-1], setout1[i], changes1[i], adds1[i])
                        sets1.append(
                            (set_text1[i], set_description1[i], changes1[i], adds1[i], setout1[i], tvalue, values1[i]))
                    sets[dict_name[-1]] = sets1
                    set_text[dict_name[-1]] = set_text1
                    set_description[dict_name[-1]] = set_description1
                    changes[dict_name[-1]] = changes1
                    adds[dict_name[-1]] = adds1
                    values[dict_name[-1]] = values1

                    test_run = False
                    set_load.append(secon)

tin.close()

sets1 = []
number = len(set_text1)
for i in range(number):
    replace_setting(set_load[-1], setout1[i], changes1[i], adds1[i])
    sets1.append((set_text1[i],set_description1[i],changes1[i],adds1[i],setout1[i],tvalue,values1[i]))
sets[dict_name[-1]] = sets1
set_text[dict_name[-1]] = set_text1
set_description[dict_name[-1]] = set_description1
changes[dict_name[-1]] = changes1
adds[dict_name[-1]] = adds1
values[dict_name[-1]] = values1




ii =1
# ===========================================================================
# ===========================================================================

@pytest.fixture(scope='session')
def config():
  config = open('test_py_catwm1.txt')
  return config


@pytest.mark.skipif(noskip[runs[0]] == False, reason= runs[0] + " skripped")
@pytest.mark.parametrize("info, descript, changes, adds, setting, testvalue, outvalue", sets[runs[0]])
def test_1_30min_Rhine(info, descript, changes, adds, setting, testvalue, outvalue):

    print('\n ===== ',info,' =====')
    print (" Setting file: ",setting)
    print(" Description: ", descript)
    print (" Changes: ", changes)
    print (" Adds: ", adds,'\n')

    success, last_dis = run_cwatm.main(setting,['-l'])
    assert success
    if testvalue:
        minvalue = outvalue - outvalue / 100
        maxvalue = outvalue + outvalue / 100
        assert (minvalue <= last_dis <= maxvalue)

@pytest.mark.skipif(noskip[runs[1]] == False, reason= runs[1] + " skipped")
@pytest.mark.parametrize("info, descript, changes, adds, setting, testvalue, outvalue", sets[runs[1]])
def test_2_30min_Global(info, descript, changes, adds, setting, testvalue, outvalue):

    print('\n ===== ',info,' =====')
    print (" Setting file: ",setting)
    print(" Description: ", descript)
    print (" Changes: ", changes)
    print (" Adds: ", adds,'\n')

    success, last_dis = run_cwatm.main(setting,['-l'])
    assert success
    if testvalue:
        minvalue = outvalue - outvalue / 100
        maxvalue = outvalue + outvalue / 100
        assert (minvalue <= last_dis <= maxvalue)

@pytest.mark.skipif(noskip[runs[2]] == False, reason= runs[2] + " skipped")
@pytest.mark.parametrize("info, descript, changes, adds, setting, testvalue, outvalue", sets[runs[2]])
def test_3_5min_Rhine(info, descript, changes, adds, setting, testvalue, outvalue):

    print('\n ===== ',info,' =====')
    print (" Setting file: ",setting)
    print(" Description: ", descript)
    print (" Changes: ", changes)
    print (" Adds: ", adds,'\n')

    success, last_dis = run_cwatm.main(setting,['-l'])
    assert success
    if testvalue:
        minvalue = outvalue - outvalue / 100
        maxvalue = outvalue + outvalue / 100
        assert (minvalue <= last_dis <= maxvalue)


@pytest.mark.skipif(noskip[runs[3]] == False, reason= runs[3] + " skipped")
@pytest.mark.parametrize("info, descript, changes, adds, setting, testvalue, outvalue", sets[runs[3]])
def test_4_5min_Global(info, descript, changes, adds, setting, testvalue, outvalue):

    print('\n ===== ',info,' =====')
    print (" Setting file: ",setting)
    print(" Description: ", descript)
    print (" Changes: ", changes)
    print (" Adds: ", adds,'\n')

    success, last_dis = run_cwatm.main(setting,['-l'])
    assert success
    if testvalue:
        minvalue = outvalue - outvalue / 100
        maxvalue = outvalue + outvalue / 100
        assert (minvalue <= last_dis <= maxvalue)



