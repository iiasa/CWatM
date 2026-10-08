import re
from configparser import ConfigParser
import os
import glob
from multiprocessing import Pool
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from scipy.stats import binned_statistic_2d
import matplotlib.pyplot as plt


# =====================================================================
# 1. THE SPATIAL GRIDDING & INTERPOLATION ENGINES
# =====================================================================
def resolve_ini_interpolation(parser: ConfigParser, max_depth: int = 10):
    """
    Recursively resolves custom $(VAR) and $(SECTION:VAR) placeholders 
    directly within a ConfigParser object.
    """
    pattern = re.compile(r'\$\((?:([^:]+):)?([^)]+)\)')

    for depth in range(max_depth):
        modifications_made = False

        for section in parser.sections():
            for option in parser.options(section):
                raw_value = parser.get(section, option, raw=True)
                
                matches = pattern.findall(raw_value)
                if not matches:
                    continue
                
                new_value = raw_value
                for target_section, target_var in matches:
                    lookup_section = target_section if target_section else section
                    
                    if parser.has_option(lookup_section, target_var):
                        resolved_piece = parser.get(lookup_section, target_var, raw=True)
                        match_str = f"$({target_section}:{target_var})" if target_section else f"$({target_var})"
                        new_value = new_value.replace(match_str, resolved_piece)
                        modifications_made = True

                parser.set(section, option, new_value)
                
        if not modifications_made:
            break
    else:
        print(f"Warning: Interpolation resolution halted. Reached maximum loop depth limit ({max_depth}).")

    return parser


def grid_observation_data(shapefile_path, swl_col_name, ref_transform, nrows, ncols):
    """
    Grids shapefile observation points onto the reference grid frame ONCE, 
    taking the mean if multiple points share a pixel cell.
    """
    if not os.path.exists(shapefile_path):
        raise FileNotFoundError(f"Observation shapefile missing at: {shapefile_path}")
    
    gdf = gpd.read_file(shapefile_path)
    if swl_col_name not in gdf.columns:
        raise KeyError(f"Column '{swl_col_name}' not found in shapefile attributes.")

    x_coords = gdf.geometry.x.values
    y_coords = gdf.geometry.y.values
    swl_values = pd.to_numeric(gdf[swl_col_name], errors='coerce').values

    valid_idx = ~np.isnan(swl_values)
    x_coords, y_coords, swl_values = x_coords[valid_idx], y_coords[valid_idx], swl_values[valid_idx]

    if swl_values.size == 0:
        raise ValueError("No valid numerical observation points found in the designated shapefile column.")

    x_min = ref_transform.c
    y_max = ref_transform.f
    x_max = x_min + (ref_transform.a * ncols)
    y_min = y_max + (ref_transform.e * nrows)

    x_bins = np.linspace(min(x_min, x_max), max(x_min, x_max), ncols + 1)
    y_bins = np.linspace(min(y_min, y_max), max(y_min, y_max), nrows + 1)

    ret = binned_statistic_2d(
        x=x_coords, 
        y=y_coords, 
        values=swl_values, 
        statistic='mean', 
        bins=[x_bins, y_bins]
    )
    
    gridded_swl = np.flipud(ret.statistic.T)
    return gridded_swl


# =====================================================================
# 2. MULTIPROCESSING WORKER FUNCTION (POST-ANALYSIS MODE)
# =====================================================================
def analyze_single_run(args):
    """
    Worker pipeline executing spatial map residual analysis on an 
    existing simulation output folder. Returns scalar metrics and the 
    2D absolute error matrix array.
    """
    (
        directory_run,
        topo_array_master,
        gridded_swl
    ) = args

    # Structural template tracking dictionary for failure states
    run_folder = os.path.basename(os.path.normpath(directory_run))
    run_id = run_folder.split("_")[-1]
    
    error_template = {
        "Run_ID": run_id,
        "Status": "FAILED",
        "Observed_Cells": 0,
        "ME": np.nan,
        "MAE": np.nan,
        "RMSE": np.nan,
        "NSE": np.nan,
        "abs_error_matrix": None
    }

    try:
        sim_depth_path = os.path.join(directory_run, run_id, 'steady_state_equilibrium_heads.npy')
        
        if not os.path.exists(sim_depth_path):
            error_template["Status"] = "MISSING_OUTPUT"
            return error_template

        # Load matrix safely
        sim_data = np.load(sim_depth_path)
        water_depth_array = sim_data[0, :, :] if len(sim_data.shape) == 3 else sim_data
        water_depth_array[water_depth_array > 1e10] = np.nan

        # Calculate Simulated Head Level
        simulated_swl = topo_array_master - water_depth_array

        # Compute point-by-point spatial residuals (Simulated minus Observed)
        residual_matrix = np.where(np.isnan(gridded_swl), np.nan, simulated_swl - gridded_swl)
        valid_residuals = residual_matrix[~np.isnan(residual_matrix)]
        
        if valid_residuals.size == 0:
            error_template["Status"] = "NO_VALID_OVERLAPS"
            return error_template

        # -------------------------------------------------------------
        # COMPUTE RECOMMENDED ADVANCED METRICS DIRECTLY
        # -------------------------------------------------------------
        count_obs = int(valid_residuals.size)
        me = float(np.mean(valid_residuals))
        mae = float(np.mean(np.abs(valid_residuals)))
        rmse = float(np.sqrt(np.mean(valid_residuals**2)))
        
        # Nash-Sutcliffe Efficiency Calculation
        observed_valid = gridded_swl[~np.isnan(gridded_swl)]
        obs_mean = np.mean(observed_valid)
        numerator_nse = np.sum(valid_residuals**2)
        denominator_nse = np.sum((observed_valid - obs_mean)**2)
        nse = float(1.0 - (numerator_nse / denominator_nse)) if denominator_nse != 0 else np.nan

        # Calculate Local Absolute Error matrix per grid cell
        abs_error_matrix = np.abs(residual_matrix)

        return {
            "Run_ID": run_id,
            "Status": "ANALYZED",
            "Observed_Cells": count_obs,
            "ME": me,
            "MAE": mae,
            "RMSE": rmse,
            "NSE": nse,
            "abs_error_matrix": abs_error_matrix
        }

    except Exception as e:
        error_template["Status"] = f"ERROR: {str(e)}"
        return error_template


# =====================================================================
# 3. MAIN SYSTEM INITIALIZATION ENGINE BLOCK
# =====================================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python batch_analyze_existing.py <settings_file.ini>")
        sys.exit(1)

    iniFile = os.path.normpath(sys.argv[1])

    # Read master project layout parameters
    parser = ConfigParser()
    parser.read(iniFile)
    
    root_fldr = parser.get("DEFAULT", "RootPC")
    modeltemplate = parser.get("Path", "Templates")
    SubCatchmentPath = os.path.normpath(os.path.join(root_fldr, parser.get("Path", "SubCatchmentPath")))
    NUM_CORES = int(parser.get("DEFAULT", "cores"))

    ModelSettings_template = os.path.normpath(os.path.join(root_fldr, modeltemplate, parser.get("Templates", "ModelSettings")))

    shapefile_path = os.path.normpath(os.path.join(root_fldr, parser.get("ObservedData", "ObsGW")))
    swl_column = parser.get("ObservedData", "var_col")

    # Extract target export pathways directly from your master config parameters
    output_dir_path = os.path.normpath(os.path.join(root_fldr, parser.get("Path", "OutputFolder")))
    excel_export_path = os.path.normpath(os.path.join(output_dir_path, "global_results.xlsx"))
    map_export_path = os.path.normpath(os.path.join(output_dir_path, "gridded_error.tif"))

    # Parse template structural specifications blocks 
    template_parser = ConfigParser()
    template_parser.read(ModelSettings_template)
    template_parser = resolve_ini_interpolation(template_parser)
    
    topo_relative_path = template_parser.get("GROUNDWATER_MODFLOW", "topo_modflow")
    maskmap_config = template_parser.get("GROUNDWATER_MODFLOW", "modflow_basin")

    topo_master_path = os.path.normpath(os.path.join(root_fldr, topo_relative_path))
    ref_tif_path = os.path.normpath(os.path.join(root_fldr, maskmap_config))

    if not os.path.exists(ref_tif_path) or not os.path.exists(shapefile_path) or not os.path.exists(topo_master_path):
        print("Error: One or more critical file dependencies missing.")
        sys.exit(1)

    with rasterio.open(ref_tif_path) as ref_src:
        ref_crs = ref_src.crs
        ref_transform = ref_src.transform
        nrows, ncols = ref_src.shape

    print(f"Loading master surface elevation matrix array from layout template path: {topo_master_path}")
    with rasterio.open(topo_master_path) as topo_src:
        topo_array_master = topo_src.read(1).astype(np.float32)
        topo_nodata = topo_src.nodata
        
    if topo_nodata is not None:
        topo_array_master[topo_array_master == topo_nodata] = np.nan
    topo_array_master[topo_array_master > 1e10] = np.nan

    print(f"Gridding observation point data from {os.path.basename(shapefile_path)} based on mask map geometry...")
    gridded_swl = grid_observation_data(shapefile_path, swl_column, ref_transform, nrows, ncols)

    # Detect all existing output scenario folders
    search_path = os.path.join(SubCatchmentPath, "Run_*")
    run_folders = [f for f in glob.glob(search_path) if os.path.isdir(f)]

    if not run_folders:
        print(f"Error: No run directories found matching 'Run_*' within target location: {SubCatchmentPath}")
        sys.exit(1)

    print(f"Found {len(run_folders)} existing model data directories to post-analyze.")

    packed_tasks = [
        (folder, topo_array_master, gridded_swl)
        for folder in run_folders
    ]

    available_cores = os.cpu_count()
    if NUM_CORES > available_cores:
        NUM_CORES = available_cores
        
    print(f"Processing evaluation metrics across {NUM_CORES} core threads...")

    with Pool(processes=NUM_CORES) as pool:
        results_list = pool.map(analyze_single_run, packed_tasks)

    # Ensure output directories exist cleanly before saving file arrays
    os.makedirs(output_dir_path, exist_ok=True)

    # -----------------------------------------------------------------
    # PROCESS EXCEL COMPILATION & INDIVIDUAL RUN MAPS
    # -----------------------------------------------------------------
    print("\nCompiling statistical metric datasets and exporting individual run maps...")
    
    clean_metrics_rows = []
    valid_matrices = []

    for item in results_list:
        print(item["Run_ID"])
        clean_metrics_rows.append({
            "Run_ID": item["Run_ID"],
            "Status": item["Status"],
            "Observed_Cells": item["Observed_Cells"],
            "Mean_Error_Bias": item["ME"],
            "MAE": item["MAE"],
            "RMSE": item["RMSE"],
            "NSE": item["NSE"]
        })
        
        # If the individual matrix was parsed successfully, save its single map profile
        if item["abs_error_matrix"] is not None:
            valid_matrices.append(item["abs_error_matrix"])
            
            # Export individual map per run to the central output directory
            run_map_path = os.path.join(output_dir_path, f"error_run_{item['Run_ID']}.tif")
            
            plt.figure(figsize=(10, 8))
            masked_individual_mae = np.ma.masked_invalid(item["abs_error_matrix"])
            plt.imshow(masked_individual_mae, cmap='YlOrRd', origin='upper')
            plt.colorbar(label='Absolute Error Magnitude (m)')
            plt.title(f'Spatial Absolute Error Profile — Run ID: {item["Run_ID"]}')
            plt.xlabel('Grid Column (X)')
            plt.ylabel('Grid Row (Y)')
            
            plt.savefig(run_map_path, dpi=150, bbox_inches='tight')
            plt.close()

    df_results = pd.DataFrame(clean_metrics_rows)
    df_results.sort_values(by="Run_ID", key=lambda x: pd.to_numeric(x, errors='coerce'), inplace=True)

    # Export out to Excel Sheet
    df_results.to_excel(excel_export_path, index=False, sheet_name="Calibration_Metrics")
    print(f"SUCCESS: Statistical calibration table saved to: {excel_export_path}")
    print(f"SUCCESS: Individual run error maps saved inside: {output_dir_path}")

    # -----------------------------------------------------------------
    # AGGREGATE SPATIAL GRID-CELL ENSEMBLE MAE MAP
    # -----------------------------------------------------------------
    if valid_matrices:
        print("\nAggregating grid-cell absolute error arrays to construct regional average MAE map...")
        
        stacked_errors = np.stack(valid_matrices, axis=0)
        grid_cell_mae = np.nanmean(stacked_errors, axis=0)
        
        plt.figure(figsize=(10, 8))
        masked_mae = np.ma.masked_invalid(grid_cell_mae)
        
        plt.imshow(masked_mae, cmap='YlOrRd', origin='upper') 
        plt.colorbar(label='Mean Absolute Error (MAE) Magnitude (m)')
        plt.title('Ensemble Spatial Grid-Cell Calibration Error Profile (Ensemble MAE Map)')
        plt.xlabel('Grid Column (X)')
        plt.ylabel('Grid Row (Y)')
        
        plt.savefig(map_export_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"SUCCESS: Regional ensemble average grid-cell error profile map saved to: {map_export_path}")
    else:
        print("\nWarning: No spatial metrics could be aggregated because all calibration executions failed.")

    print("\nBatch metrics run processing complete.")