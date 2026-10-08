# -*- coding: utf-8 -*-
"""
Created for CWatM-MODFLOW Coupling
Sub-grid Topography Percentile Aggregator (Projected NetCDF Output)
"""

import os
import numpy as np
import rasterio
import xarray as xr


def Compute_DEM_Percentiles(
    res_ModFlow,
    res_ModFlow_finer,
    Inputs_file,
    Inputs_file_finer,
    finer_dem_path,
    ncol_ModFlow,
    nrow_ModFlow,
    modflow_crs,
    affine_modflow,
    percentiles=[1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99, 100],
    output_name="dem_percentiles.nc",
):
    print("Calculating sub-grid topographic percentiles at coarse resolution...")

    # 1. Open fine-resolution DEM raster
    with rasterio.open(finer_dem_path, "r") as src:
        fine_dem = src.read(1)
        nodata_val = src.nodata

    # Ratio of coarse to fine cell dimensions (e.g., 5000 / 250 = 20)
    ratio = int(round(res_ModFlow / res_ModFlow_finer))

    # 2. Pad or trim fine DEM to fit exact target coarse dimensions (nrow_ModFlow x ncol_ModFlow)
    req_rows = nrow_ModFlow * ratio
    req_cols = ncol_ModFlow * ratio

    padded_dem = np.full((req_rows, req_cols), np.nan, dtype=np.float32)
    valid_rows = min(fine_dem.shape[0], req_rows)
    valid_cols = min(fine_dem.shape[1], req_cols)

    padded_dem[:valid_rows, :valid_cols] = fine_dem[:valid_rows, :valid_cols]

    if nodata_val is not None:
        padded_dem[padded_dem == nodata_val] = np.nan

    # 3. Reshape array to aggregate fine pixels inside each 5000 m cell
    # Reshaped shape: (nrow_ModFlow, ratio, ncol_ModFlow, ratio)
    blocks = padded_dem.reshape(nrow_ModFlow, ratio, ncol_ModFlow, ratio)
    # Flatten inner sub-pixels: (nrow_ModFlow, ncol_ModFlow, ratio * ratio)
    blocks_flat = blocks.transpose(0, 2, 1, 3).reshape(
        nrow_ModFlow, ncol_ModFlow, ratio * ratio
    )

    # 4. Calculate percentiles across sub-grid axis (-1) -> shape: (9, nrow_ModFlow, ncol_ModFlow)
    perc_array = np.nanpercentile(blocks_flat, q=percentiles, axis=-1)

    # 5. Extract 2D Spatial Coordinates (x, y) for 5000 m cell centers in projected meters
    x_coords = np.array(
        [
            affine_modflow.c + affine_modflow.a * (i + 0.5)
            for i in range(ncol_ModFlow)
        ]
    )
    y_coords = np.array(
        [
            affine_modflow.f + affine_modflow.e * (j + 0.5)
            for j in range(nrow_ModFlow)
        ]
    )

    # Convert modflow_crs to standard string if passed as int (e.g., 32636 -> "EPSG:32636")
    crs_str = (
        f"EPSG:{modflow_crs}"
        if isinstance(modflow_crs, int)
        else str(modflow_crs)
    )

    # 6. Build NetCDF Dataset with 2D (y, x) dimensions and 9 separate variables
    data_vars = {}
    for idx, p in enumerate(percentiles):
        var_name = f"z_p{p}"
        data_vars[var_name] = (
            ["y", "x"],
            perc_array[idx, :, :],
            {
                "units": "masl",
                "long_name": f"{p}th percentile elevation",
                "grid_mapping": "spatial_ref",
            },
        )

    # Add CF-convention spatial reference variable
    data_vars["spatial_ref"] = (
        [],
        0,
        {
            "spatial_ref": crs_str,
            "crs_wkt": crs_str,
            "GeoTransform": f"{affine_modflow.c} {affine_modflow.a} 0 {affine_modflow.f} 0 {affine_modflow.e}",
        },
    )

    ds = xr.Dataset(
        data_vars=data_vars,
        coords={
            "y": y_coords,
            "x": x_coords,
        },
        attrs={
            "description": "Sub-grid topographic elevation percentiles",
            "res_coarse_m": res_ModFlow,
            "res_finer_m": res_ModFlow_finer,
            "crs": crs_str,
        },
    )

    # Set spatial coordinate attributes for spatial readers (GDAL / QGIS)
    ds["x"].attrs["units"] = "m"
    ds["x"].attrs["long_name"] = "x-coordinate in projected coordinate system"
    ds["x"].attrs["standard_name"] = "projection_x_coordinate"

    ds["y"].attrs["units"] = "m"
    ds["y"].attrs["long_name"] = "y-coordinate in projected coordinate system"
    ds["y"].attrs["standard_name"] = "projection_y_coordinate"

    # 7. Save NetCDF
    output_path = os.path.join(Inputs_file, output_name)
    ds.to_netcdf(output_path)

    print(
        f"Successfully saved NetCDF to {output_path} with MODFLOW projection ({crs_str})"
    )
    return None