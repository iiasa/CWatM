import os
import numpy as np
import rasterio

def convert_head_to_depth(npy_path, elevation_tif_path, output_tif_path):

    # -------------------------
    # 1. Load DEM
    # -------------------------
    print("Loading elevation...")
    with rasterio.open(elevation_tif_path) as src:
        meta = src.meta.copy()
        elevation = src.read(1).astype(np.float32)
        elev_nodata = src.nodata

    if elev_nodata is not None:
        elevation[elevation == elev_nodata] = np.nan

    # -------------------------
    # 2. Load MODFLOW heads
    # -------------------------
    print("Loading MODFLOW heads...")
    sim = np.load(npy_path)

    # take layer 1
    head = sim[0, :, :].astype(np.float32)

    # mask extreme values
    head[head > 1e20] = np.nan

    # -------------------------
    # 3. Compute depth to water table
    # -------------------------
    print("Computing depth to groundwater (DEM - head)...")
    depth = elevation - head

    # -------------------------
    # 4. Prepare output raster
    # -------------------------
    meta.update({
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "nodata": -9999.0
    })

    out = np.where(np.isnan(depth), -9999.0, depth)

    # -------------------------
    # 5. Write output
    # -------------------------
    print("Writing output...")
    os.makedirs(os.path.dirname(output_tif_path), exist_ok=True)

    with rasterio.open(output_tif_path, "w", **meta) as dst:
        dst.write(out.astype(np.float32), 1)

    print("Done.")

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":

    NPY_INPUT = r"P:/watmodel/CWATM\model/cwatm_modflow_layers/Toolkit/Calibration_modflow/runs_calibration/Run_86/86/steady_state_equilibrium_heads.npy"
    ELEVATION = r"P:/watmodel/CWATM/modelruns/uppernile_wmz_G4DR/inputs/modf_out/5000.0m/elevation_modflow.tif"
    OUTPUT = r"P:/watmodel/CWATM\model/cwatm_modflow_layers/Toolkit/Calibration_modflow/runs_calibration/Run_86/water_table_depth.tif"

    convert_head_to_depth(NPY_INPUT, ELEVATION, OUTPUT)