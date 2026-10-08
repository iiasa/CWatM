import os
import numpy as np
import rasterio

def convert_depth_to_swl(npy_path, elevation_tif_path, output_tif_path):
    """
    Loads a water table depth numpy array, subtracts it from a surface elevation 
    GeoTIFF, and exports the resulting Shallow Water Level (SWL) as a georeferenced GeoTIFF.
    """
    # 1. Read the georeferenced Elevation GeoTIFF to get metadata and data
    print(f"Reading elevation profile from: {elevation_tif_path}")
    with rasterio.open(elevation_tif_path) as src:
        # Copy the spatial metadata (projection, coordinates, extent)
        meta = src.meta.copy()
        # Read the first band as a float32 array
        elevation_array = src.read(1).astype(np.float32)
        elev_nodata = src.nodata

    # Clean NoData values in the elevation data if they exist
    if elev_nodata is not None:
        elevation_array[elevation_array == elev_nodata] = np.nan

    # 2. Load the simulated raw depth matrix (.npy)
    print(f"Loading simulated depth array from: {npy_path}")
    sim_data = np.load(npy_path)
    
    # Handle both 2D arrays and 3D arrays (slicing the first layer if 3D)
    water_depth_array = sim_data[0, :, :] if len(sim_data.shape) == 3 else sim_data
    
    # Strip out background model noise / dry cell constants (e.g., values > 1e10)
    water_depth_array[water_depth_array > 1e10] = np.nan

    # 3. Calculate Simulated Head / SWL (Elevation - Depth)
    print("Calculating Shallow Water Level (SWL)...")
    swl_array = elevation_array - water_depth_array

    # 4. Prepare metadata for outputting a float32 GeoTIFF
    # Reset any incoming integer types to float32 to hold the NaNs safely
    meta.update({
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "nodata": -9999.0
    })

    # Swap internal NaNs back to the designated standard GIS NoData code (-9999.0)
    export_array = np.where(np.isnan(swl_array), -9999.0, swl_array)

    # 5. Write out the finished GIS-ready file
    print(f"Exporting georeferenced SWL map to: {output_tif_path}")
    os.makedirs(os.path.dirname(os.path.abspath(output_tif_path)), exist_ok=True)
    with rasterio.open(output_tif_path, "w", **meta) as dst:
        dst.write(export_array.astype(np.float32), 1)

    print("SWL transformation complete.")

# =====================================================================
# EXAMPLE USAGE
# =====================================================================
if __name__ == "__main__":
    # Define your hardcoded paths directly here
    NPY_INPUT = "P:/watmodel/CWATM/model/cwatm_modflow_layers/Toolkit/Calibration_modflow/runs_calibration/Run_165/165/steady_state_equilibrium_heads.npy"
    ELEVATION_TIF = "P:/watmodel/CWATM/modelruns/uppernile_wmz_G4DR/inputs/modf_out/5000.0m/elevation_modflow.tif"
    OUTPUT_TIF = "P:/watmodel/CWATM/model/cwatm_modflow_layers/Toolkit/Calibration_modflow/runs_calibration/Run_165/165/swl_out.tif"

    convert_depth_to_swl(NPY_INPUT, ELEVATION_TIF, OUTPUT_TIF)