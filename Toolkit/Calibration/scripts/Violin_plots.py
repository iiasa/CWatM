

""" The aim of this code is to extract simulated data and display tested parameter values"""

# --------------------------------------------------------------------------
# Import Python packages

import numpy as np
import matplotlib.backends.backend_pdf
import matplotlib.pyplot as plt
import os
import csv
import sys
from sys import platform
# to extract parameters form settings file
import configparser  # to read the settings file

import pandas as pd
import seaborn as sns

iniFile = os.path.normpath(sys.argv[1])
parser = configparser.ConfigParser()
parser.read(iniFile)

if platform == "win32":
    root = parser.get('DEFAULT','RootPC')
else:
	root = parser.get('DEFAULT', 'Root')
rootbasin = os.path.join(root,parser.get('DEFAULT', 'Rootbasin'))

# --------------------------------------------------------------------------
# Import paths

MAIN_PATH = rootbasin #'P:/watmodel/CWATM\model\GitHub_Mikhail\CWatM\Tutorials/09_Calibration_renovation'

#[Path]
#Templates = templates_CWatM
#SubCatchmentPath = runs_calibration

path_model_outputs = MAIN_PATH + '/' + str(parser.get('Path', 'SubCatchmentPath'))
filename_discharge_criter = path_model_outputs + '/' + 'runs_log.csv'

your_path = path_model_outputs  # The directory where there are all the simulations
folders_out = os.listdir(your_path)  # list of all folders containing simulated GW maps and settings file

folders = []
for ll in range(len(folders_out)):  # for each folder (=each simulation)

    if 'best' not in folders_out[ll] and 'pkl' not in folders_out[ll] and 'front_history' not in folders_out[ll]\
            and 'pareto' not in folders_out[ll] and 'runs_log' not in folders_out[ll] and 'readme' not in folders_out[ll]:
        folders.append(folders_out[ll])


# --------------------------------------------------------------------------
# Extract KGE criteria on discharge

dict_discharge_criter = {}  # Dictionary: {'simulation number': 'KGE value'}
with open(filename_discharge_criter, newline='') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',')
    cnt = 0
    for row in spamreader:
        dict_discharge_criter[row[0]] = row[1]

KGE_values = np.zeros(len(folders))  # KGE criteria for discharge
for ll in range(len(folders)):  # for each folder (=each simulation)
    KGE_values[ll] = dict_discharge_criter[folders[ll]]

# Sort the results in function of KGE to have the best models above
Ind = np.argsort(KGE_values)
folders_arranged = [folders[ind] for ind in Ind]

# --------------------------------------------------------------------------
# Extracting tested parameters

# Initializing arrays
CropCorrect_values = np.zeros(len(folders))
SoilDepth_values = np.zeros(len(folders))
PreferentialFlowConstant_values = np.zeros(len(folders))
ArnobetaAdd_values = np.zeros(len(folders))
FactorInterflow_values = np.zeros(len(folders))
RecessionCoeff_values = np.zeros(len(folders))
ManningsN_values = np.zeros(len(folders))
NormalStorageLimit_values = np.zeros(len(folders))

for ll in range(len(folders)):  # for each folder (=each simulation)

        config = configparser.RawConfigParser()
        config.optionxform = str
        config.sections()
        print(path_model_outputs + '/' + folders[ll] + '/' + str(parser.get('Templates', 'ModelSettings'))[:-4]+'-Run' + folders[ll] + '.ini')
        config.read(path_model_outputs + '/' + folders[ll] + '/' + str(parser.get('Templates', 'ModelSettings'))[:-4]+'-Run' + folders[ll] + '.ini')

        CropCorrect_values[ll] = float(config.get('CALIBRATION', 'crop_correct'))
        SoilDepth_values[ll] = float(config.get('CALIBRATION', 'soildepth_factor'))
        PreferentialFlowConstant_values[ll] = float(config.get('CALIBRATION', 'preferentialFlowConstant'))
        ArnobetaAdd_values[ll] = float(config.get('CALIBRATION', 'arnoBeta_add'))
        FactorInterflow_values[ll] = float(config.get('CALIBRATION', 'factor_interflow'))
        RecessionCoeff_values[ll] = float(config.get('CALIBRATION', 'recessionCoeff_factor'))
        ManningsN_values[ll] = float(config.get('CALIBRATION', 'manningsN'))
        NormalStorageLimit_values[ll] = float(config.get('CALIBRATION', 'normalStorageLimit'))

Values = [KGE_values, CropCorrect_values, SoilDepth_values,
          PreferentialFlowConstant_values, ArnobetaAdd_values, FactorInterflow_values, RecessionCoeff_values,
          ManningsN_values, NormalStorageLimit_values]
allowed_ranges = np.zeros((len(Values), 2))
allowed_ranges[0] = [-1, 1]  # min and max allowed value for KGE
Param_ranges_filename = MAIN_PATH + '/' + 'ParamRanges.csv'
ParamRanges = pd.read_csv(Param_ranges_filename, sep=",", index_col=0)
for pp in range(len(Values)-1):
    allowed_ranges[pp+1] = [ParamRanges["MinValue"][pp], ParamRanges["MaxValue"][pp]]

Values_label = ['KGE', 'Crop', 'SoilDepth', 'PrefFlow', 'ArnoBeta', 'Interflow', 'gwRecess',
                'ManningN','NormStorLim']
param_std = np.zeros(len(Values_label))
for vlab in range(len(Values_label)):
    maxValue = allowed_ranges[vlab][1]  #np.max(Values[vlab])
    minValue = allowed_ranges[vlab][0]  #np.min(Values[vlab])
    normValue = [(i - minValue) / (maxValue - minValue) for i in Values[vlab]]
    param_std[vlab] = np.std(normValue)
    Values_label[vlab] = Values_label[vlab] + "\nstd = " + str(np.round((param_std[vlab])*100)/100)

# Sort the parameters by their std, the best (min std) first, we keep KGE first
Indices_param = np.argsort(param_std[1:])
Values_label = np.array(Values_label)
Values_label_temp = Values_label[1:]
Values_label_temp = Values_label_temp[Indices_param]
Values_label[1:] = Values_label_temp
Values = np.array(Values)
Values_temp = Values[1:]
Values_temp = Values_temp[Indices_param]
Values[1:] = Values_temp
allowed_ranges_temp = allowed_ranges[1:]
allowed_ranges_temp = allowed_ranges_temp[Indices_param]
allowed_ranges[1:] = allowed_ranges_temp

df_violin = {'cal_value': [], 'calibration_label': []}

v = 1
for value in Values[v:]:
    maxValue = allowed_ranges[v][1]  #np.max(Values[vlab])
    minValue = allowed_ranges[v][0]  #np.min(Values[vlab])
    normValue = [(i - minValue) / (maxValue - minValue) for i in value]
    df_violin['cal_value'].extend(normValue)
    df_violin['calibration_label'].extend([Values_label[v]] * len(value))
    v += 1

dfviolin = pd.DataFrame(df_violin)

plt.figure(figsize=(10, 8))
sns.violinplot(x="cal_value", y="calibration_label", data=dfviolin, inner=None)
plt.xlabel("Sampled parameter coefficients (normalized)", size=18)
plt.ylabel("Parameters", size=18)
plt.xticks(fontsize=16)
plt.yticks(fontsize=15)
plt.xlim([0, 1])

v = 1
for value in Values[v:]:
    maxValue = allowed_ranges[v][1]  #np.max(Values[vlab])
    minValue = allowed_ranges[v][0]  #np.min(Values[vlab])
    normValue = [(i - minValue) / (maxValue - minValue) for i in value]
    plt.scatter(normValue[np.argmax(KGE_values)], [v-1], c='r')
    v += 1

plt.figure(figsize=(12, 8))
plt.hist(KGE_values, bins=25)
temp_hist = np.histogram(KGE_values, bins=25)
txt_bestKGE = 'Best value : ' + str(np.round(np.max(KGE_values)*100)/100)
plt.plot([np.max(KGE_values), np.max(KGE_values)], [0, np.max(temp_hist[0])+20], color='r', label=txt_bestKGE, linewidth=2)
txt_medianKGE = 'Median value : ' + str(np.round(np.median(KGE_values)*100)/100)
plt.plot([np.median(KGE_values), np.median(KGE_values)], [0, np.max(temp_hist[0])+20], color='g', label=txt_medianKGE, linewidth=2)
plt.ylim([0, np.max(temp_hist[0])+20])
plt.xlim([-1, 1])
plt.legend(fontsize=16)
plt.xlabel("KGE values on log(discharge)", fontsize=18)
txt_nbrmodels = 'Number of models (total is ' + str(len(KGE_values)) + ')'
plt.ylabel(txt_nbrmodels, fontsize=18)
plt.xticks(fontsize=16)
plt.yticks(fontsize=16)
plt.grid(which='both')

savefig = "figures/violin_plot.pdf"
pdf = matplotlib.backends.backend_pdf.PdfPages(savefig)
for fig in range(1, plt.figure().number):
    pdf.savefig(fig)
pdf.close()

#plt.show()
#plt.close('all')
