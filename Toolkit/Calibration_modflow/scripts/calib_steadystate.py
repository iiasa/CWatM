from configparser import ConfigParser
import os
from multiprocessing import Pool
import sys
import numpy as np
import pandas as pd
from scipy.stats import qmc


# 1. The Worker Function (must accept a single tuple argument for multiprocessing)
def run_single_model(args):
    # Unpack the packed arguments
    (
        row_data,
        template_xml_base,
        ModelSettings_template,
        RunModel_template,
        SubCatchmentPath,
    ) = args

    # Extract Run ID
    run_id = str(int(row_data["Run_ID"]))

    # Setup directories explicitly inside SubCatchmentPath
    directory_run = os.path.join(SubCatchmentPath, f"Run_{run_id}")
    os.makedirs(directory_run, exist_ok=True)

    # Clean template modifications
    template_xml_new = template_xml_base.replace("%run_rand_id", run_id)

    # Loop through all parameter columns except 'Run_ID'
    for prm_name, prm_val in row_data.items():
        if prm_name != "Run_ID":
            template_xml_new = template_xml_new.replace(
                f"%{prm_name}", str(prm_val)
            )

    # ---> CORRECTED LINE: Fixed the filename layout so it doesn't carry over template prefix IDs
    ini_filename = f"ModelSettings-Run{run_id}.ini"
    ini_filepath = os.path.join(directory_run, ini_filename)

    with open(ini_filepath, "w") as f:
        f.write(template_xml_new)

    # ---> CORRECTED LINE: Standardized the batch filename directly inside the Run folder
    bat_filename = f"LaunchModel_Run{run_id}.bat"
    bat_filepath = os.path.join(directory_run, bat_filename)

    # Initialize our localized log file layout
    log_filename = "run_status.log"
    log_filepath = os.path.join(directory_run, log_filename)
    
    with open(log_filepath, "w") as log_file:
        log_file.write(f"==================================\n")
        log_file.write(f"      MODEL RUN METADATA DETAILS  \n")
        log_file.write(f"==================================\n")
        log_file.write(f"Run ID      : {run_id}\n")
        log_file.write(f"Folder Path : {directory_run}\n")
        log_file.write(f"Settings File Used: {ini_filename}\n")
        log_file.write(f"----------------------------------\n")
        log_file.write("Parameters Evaluated:\n")
        for prm_name, prm_val in row_data.items():
            if prm_name != "Run_ID":
                log_file.write(f"  - {prm_name}: {prm_val}\n")
        log_file.write(f"----------------------------------\n")
        log_file.write("--- ENGINES CAPTURED PRINTED LOGS BELOW ---\n\n")

    # Construct batch string utilizing the python call framework with explicit logging redirection
    with open(bat_filepath, "w") as f:
        f.write(
            f"@echo off\n"
            f"p:\\watmodel\\python3810\\python p:\\watmodel\\CWATM\\model\\cwatm_modflow_layers\\run_cwatm.py {ini_filename} -l >> {log_filename} 2>&1\n"
            f"if %%ERRORLEVEL%% EQU 0 (\n"
            f"    echo STATUS: SUCCEEDED >> {log_filename}\n"
            f") else (\n"
            f"    echo STATUS: FAILED with exit code %%ERRORLEVEL%% >> {log_filename}\n"
            f")\n"
        )

    # Construct and run the Windows chain command
    command = f'cd /d "{directory_run}" && "{bat_filename}"'
    print(f"--> Spawning Run {run_id}...")

    exit_code = os.system(command)

    # Determine execution status results for main process overview reporting
    if exit_code == 0:
        status_msg = "SUCCEEDED"
    else:
        status_msg = f"FAILED (Exit Code: {exit_code})"

    return f"Run ID: {run_id.ljust(6)} | STATUS: {status_msg}"


# 2. Main Execution Block
if __name__ == "__main__":
    # Check if configurations file path is provided via command line
    if len(sys.argv) < 2:
        print("Error: Please provide the .ini settings file as an argument.")
        sys.exit(1)

    # READ SETTINGS TEXT
    iniFile = os.path.normpath(sys.argv[1])

    parser = ConfigParser()
    parser.read(iniFile)

    # paths
    root_fldr = parser.get("DEFAULT", "RootPC")
    modeltemplate = parser.get("Path", "Templates")
    SubCatchmentPath = os.path.join(
        root_fldr, parser.get("Path", "SubCatchmentPath")
    )

    NUM_CORES = int(parser.get("DEFAULT", "cores"))

    # read settings for LHS
    prms_pth = os.path.join(root_fldr, parser.get("Path", "ParamRanges"))

    # number of models (max)
    num_samples = int(parser.get("LHS", "max_models"))

    # construct settings/model paths
    ModelSettings_template = os.path.join(
        root_fldr, modeltemplate, parser.get("Templates", "ModelSettings")
    )
    RunModel_template = os.path.join(
        root_fldr, modeltemplate, parser.get("Templates", "RunModel")
    )

    # read input data for LHS
    df_input = pd.read_csv(prms_pth)

    # Extract bounds
    num_params = len(df_input)
    lower_bounds = df_input["min"].values
    upper_bounds = df_input["max"].values

    # Determine optimal number of samples
    opt_num_samples = 50 * num_params
   # opt_num_samples = 1000 * num_params


    if opt_num_samples > num_samples:
        print(
            f"Warning: the maximum number of models {num_samples} is smaller than the optimal number of models: {opt_num_samples}"
        )
    else:
        print(f"Set the number of models to {opt_num_samples}")
        num_samples = opt_num_samples

    # Initialize the LHS sampler
    sampler = qmc.LatinHypercube(d=num_params, optimization="random-cd")
    sample = sampler.random(n=num_samples)

    # Scale the sample from the [0, 1] uniform range to actual parameter bounds
    scaled_sample = qmc.scale(sample, lower_bounds, upper_bounds)

    # Create the final calibration table
    df_calibration = pd.DataFrame(
        scaled_sample, columns=df_input.iloc[:, 0].values
    )
    df_calibration.insert(0, "Run_ID", range(1, num_samples + 1))

    # Read the base template xml/ini file structure
    with open(ModelSettings_template, "r") as f:
        template_xml = f.read()

    # Convert the DataFrame rows into standard list of dictionaries
    rows_list = df_calibration.to_dict(orient="records")

    # Pack parameters up into tuples
    packed_tasks = [
        (
            row,
            template_xml,
            ModelSettings_template,
            RunModel_template,
            SubCatchmentPath,
        )
        for row in rows_list
    ]

    # Dynamically clamp processing cores against available hardware ceiling
    available_cores = os.cpu_count()
    if NUM_CORES > available_cores:
        NUM_CORES = available_cores
    print(f"Launching Multiprocessing Pool using {NUM_CORES} cores...")

    # Fire up the worker pool execution matrix
    with Pool(processes=NUM_CORES) as pool:
        results_array = pool.map(run_single_model, packed_tasks)

    # Print clean summary table to screen
    print("\n======================================")
    print("    CALIBRATION BATCH RESULTS OVERVIEW ")
    print("======================================")
    for log_message in results_array:
        print(log_message)