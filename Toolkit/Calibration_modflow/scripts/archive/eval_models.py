from configparser import ConfigParser
import os
import glob
from multiprocessing import Pool
import sys
import numpy as np
import rasterio

# 1. Worker function to process a single run folder
def process_single_run(args):
    run_folder_path, topo_relative_path, ref_tif_path = args

    try:
        run_folder = os.path.basename(run_folder_path)
        run_id = run_folder.split("_")[-1]
        
        # Build path to the topography file inside this specific Run_X folder
        file_path = os.path.join(run_folder_path, os.path.basename(topo_relative_path))
        
        if not os.path.exists(file_path):
            return "WARNING: Topography file not found for " + str(run_folder) + " at: " + str(file_path) + "\n"

        # Load the data matrix
        data = np.load(file_path)

        # Select layer 0 if the array is 3D
        if len(data.shape) == 3:
            data_to_process = data[0, :, :]
        else:
            data_to_process = data

        # Strip dry cells
        data_to_process[data_to_process > 1e10] = np.nan
        active_data = data_to_process[data_to_process > 0]

        # Build output log statistics report using standard text characters
        log_lines = [
            "------------------------------------------------------------",
            "DATA SUMMARY: " + str(run_folder) + " -> " + str(os.path.basename(file_path)),
            "------------------------------------------------------------",
            "  Grid Shape:         " + str(data_to_process.shape),
            "  Total Cell Count:   " + str(data_to_process.size) + " cells",
        ]

        if active_data.size == 0:
            log_lines.append(
                "WARNING: This array contains nothing but ZEROS or NEGATIVE values."
            )
        else:
            log_lines.extend(
                [
                    "  Active Mask Cells:  " + str(active_data.size) + " cells",
                    "------------------------------------------------------------",
                    "SPREAD OF ACTIVE ELEVATIONS / WATER LEVELS:",
                    "    Hard Minimum:     " + f"{np.nanmin(active_data):.3f}" + " m",
                    "    Median (50th):    " + f"{np.nanmedian(active_data):.3f}" + " m",
                    "    Hard Maximum:     " + f"{np.nanmax(active_data):.3f}" + " m",
                ]
            )

        # --- MANDATORY GEOTIFF EXPORT (Default Behavior) ---
        # Saves to your specific naming requirement inside the localized run directory (e.g. Run_1/1.tif)
        output_tif_name = str(run_id) + ".tif"
        output_tif_path = os.path.join(run_folder_path, output_tif_name)
        nrows, ncols = data_to_process.shape

        with rasterio.open(ref_tif_path) as ref_src:
            ref_crs = ref_src.crs
            ref_transform = ref_src.transform

            # Swap NaNs back to GIS standard missing value codes (-9999.0)
            export_array = np.where(
                np.isnan(data_to_process), -9999.0, data_to_process
            )

            with rasterio.open(
                output_tif_path,
                "w",
                driver="GTiff",
                height=nrows,
                width=ncols,
                count=1,
                dtype=str(export_array.dtype),
                crs=ref_crs,
                transform=ref_transform,
                nodata=-9999.0,
            ) as dst:
                dst.write(export_array, 1)
                
        log_lines.append(
            "SUCCESS: Spatial GeoTIFF Exported: " + str(os.path.join(run_folder, output_tif_name))
        )

        return "\n".join(log_lines) + "\n"

    except Exception as e:
        return "ERROR: Failed to process folder " + str(run_folder_path) + ": " + str(e) + "\n"


# 2. Main Processing Pipeline
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python batch_postprocess.py <settings_file.ini>")
        sys.exit(1)

    iniFile = os.path.normpath(sys.argv[1])

    # Read master configuration blocks
    parser = ConfigParser()
    parser.read(iniFile)

    root_fldr = parser.get("DEFAULT", "RootPC")
    modeltemplate = parser.get("Path", "Templates")
    SubCatchmentPath = os.path.join(
        root_fldr, parser.get("Path", "SubCatchmentPath")
    )
    NUM_CORES = int(parser.get("DEFAULT", "cores"))

    # Resolve the template model settings file path
    ModelSettings_template = os.path.join(
        root_fldr, modeltemplate, parser.get("Templates", "ModelSettings")
    )

    # Read the internal template settings layout
    template_parser = ConfigParser()
    template_parser.read(ModelSettings_template)
    
    try:
        # Extract the source topography target relative name configuration
        topo_relative_path = template_parser.get("GROUNDWATER_MODFLOW", "topo_modflow")
        
        # Extract the base mask map path configuration out of the master template configuration files
        maskmap_config = template_parser.get("GROUNDWATER_MODFLOW", "modflow_basin")
        
        # Build the functional absolute path to your master reference grid TIF map
        ref_tif_path = os.path.normpath(os.path.join(root_fldr, maskmap_config))
        
    except Exception as err:
        print("Error reading settings values out of template: " + str(ModelSettings_template))
        print("Details: " + str(err))
        sys.exit(1)

    # Sanity checks on physical file accessibility
    if not os.path.exists(ref_tif_path):
        print("Error: Reference grid maskmap file does not exist at: " + str(ref_tif_path))
        sys.exit(1)

    if not os.path.exists(SubCatchmentPath):
        print("Error: Output catchment path directory does not exist: " + str(SubCatchmentPath))
        sys.exit(1)

    # Find execution folders matching standard output strings
    search_path = os.path.join(SubCatchmentPath, "Run_*")
    run_folders = [f for f in glob.glob(search_path) if os.path.isdir(f)]

    if not run_folders:
        print("No run directories found matching 'Run_*' within: " + str(SubCatchmentPath))
        sys.exit(1)

    print("Found " + str(len(run_folders)) + " model folders to analyze.")
    print("Reference mask array found at: " + str(ref_tif_path))

    # Pack processing tuples
    packed_tasks = [
        (folder, topo_relative_path, ref_tif_path) for folder in run_folders
    ]

    # Dynamically select processing limits matching server constraints
    available_cores = os.cpu_count()
    if NUM_CORES > available_cores:
        NUM_CORES = available_cores

    print("Processing structural conversions using " + str(NUM_CORES) + " concurrent workers...")

    # Spool work arrays out across cores in parallel
    with Pool(processes=NUM_CORES) as pool:
        batch_logs = pool.map(process_single_run, packed_tasks)

    # Print summary metrics to console window
    print("\n------------------------------------------------------------")
    print("       BATCH PROCESS POST-ANALYSIS METRICS")
    print("------------------------------------------------------------")
    for report in batch_logs:
        print(report)