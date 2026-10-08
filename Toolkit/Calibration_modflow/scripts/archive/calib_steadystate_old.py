import os
import sys
import numpy as np
import pandas as pd
from scipy.stats import qmc
from multiprocessing import Pool
from configparser import ConfigParser
import glob



def run_single_model(row_data, template_xml_new, SubCatchmentPath):
    run_id = int(row_data["Run_ID"])
    series_rows_list = row_data.index.astype(str).tolist()[1:]
    # open settings file
    print(row_data)

    template_xml_new = template_xml_new.replace("%run_rand_id", str(run_id))
    for ii in series_rows_list:
        template_xml_new = template_xml_new.replace("%" + ii, str(row_data[ii]))

## run model
    os.mkdir(directory_run)
        f = open(os.path.join(directory_run, ModelSettings_template[:-4] + '-Run' + run_rand_id + '.ini'), "w")
        f.write(template_xml_new)
        f.close()

        template_bat_new = template_bat
        template_bat_new = template_bat_new.replace('%run',ModelSettings_template[:-4]+'-Run'+run_rand_id+'.ini')
        runfile = os.path.join(directory_run,RunModel_template[:-4]+run_rand_id)
        if platform == "win32":
            runfile = runfile + ".bat"
           
# READ SETTINGS TEXT
iniFile = os.path.normpath(sys.argv[1])

parser = ConfigParser()
parser.read(iniFile)

# paths
root_fldr = parser.get('DEFAULT','RootPC')
modeltemplate = parser.get('Path','Templates')
SubCatchmentPath = os.path.join(root_fldr, parser.get('Path','SubCatchmentPath'))

# read settings for LHS
prms_pth = os.path.join(root_fldr, parser.get('Path','ParamRanges'))

# number of models (max)
num_samples = int(parser.get('LHS','max_models'))

# construct settings/model paths
ModelSettings_template = os.path.join(root_fldr, modeltemplate, parser.get('Templates','ModelSettings'))
RunModel_template = parser.get('Templates','RunModel')




# read input data for LHS
df_input =  pd.read_csv(prms_pth)

# 3. Extract bounds
num_params = len(df_input)
lower_bounds = df_input["min"].values
upper_bounds = df_input["max"].values

# optimal number of samples
opt_num_samples = 50 * num_params

if opt_num_samples > num_samples:
    print("Warning: the maximum number of models " + str(num_samples) + " is smaller than the oprimal number of models: " + str(opt_num_samples))
else:
    print("Set the number of models to " + str( opt_num_samples))
    num_samples = opt_num_samples

# 4. Initialize the LHS sampler
# 'space_filling' optimization ensures points are as spread out as possible
sampler = qmc.LatinHypercube(d=num_params, optimization="random-cd")
sample = sampler.random(n=num_samples)

# 5. Scale the sample from the [0, 1] uniform range to your actual parameter bounds
scaled_sample = qmc.scale(sample, lower_bounds, upper_bounds)

# 6. Create the final calibration table
df_calibration = pd.DataFrame(scaled_sample, columns = df_input.iloc[:, 0].values)

# Optional: Add a Run_ID column for easy tracking
df_calibration.insert(0, "Run_ID", range(1, num_samples + 1))

# Run calibrations
f = open(ModelSettings_template,"r")
template_xml = f.read()
f.close()
run_single_model(row_data = df_calibration.iloc[0, :], template_xml_new = template_xml, SubCatchmentPath = SubCatchmentPath)
# 7. View and save the results
#print("--- Generated LHS Calibration Table ---")
#print(df_calibration.to_string(index=False))

# Save to CSV for your simulation environment
# df_calibration.to_csv("lhs_calibration_matrix.csv", index=False)