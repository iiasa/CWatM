# Preprocessing for the CWatM-MODFLOW coupling (version 2)

Creates the MODFLOW input maps from the CWatM mask and a fine DEM - one script, no QGIS, no shapefiles.

```
python preprocess_modflow.py preprocessing_tisa1.ini
```

## Input

| Setting | Content |
|---|---|
| `cwatm_mask` | CWatM mask (tif with CRS; a file without CRS, e.g. PCRaster `.map`, needs `cwatm_epsg`). Active: not nodata and not 0 |
| `dem` | fine DEM (tif with CRS), for the elevation and the river network |
| `modflow_epsg` | CRS of the MODFLOW grid in metres (e.g. UTM zone of the basin); empty: UTM zone of the basin centre |
| `res_modflow`, `res_finer` | MODFLOW resolution and resolution of the river network [m]; `res_modflow` a whole multiple of `res_finer` |
| `stream_density` | river where the upstream area > `stream_density`^2 [m^2] (low = dense network) |
| `extent` | `active`: grid around the active CWatM cells (smaller grid); `full`: around the whole mask rectangle (as version 1) |
| `basin_fraction`, `mask_subsampling` | MODFLOW cell active if more than `basin_fraction` of it is inside the CWatM mask, counted on a `mask_subsampling` times finer grid |
| `snap_to_dem` | `True` (default): if DEM and MODFLOW have the same CRS, the grid origin is moved onto the DEM pixel grid (MODFLOW and finer cells contain whole DEM pixels). A CRS without EPSG code in the file (EU-DEM `ETRS89_ETRS_LAEA`) is recognised by its parameters |
| `[EXTRA_MAPS]` | optional maps (e.g. permeability, porosity) projected to the MODFLOW grid (average) |

## Output (`<output_folder>/<res_modflow>m/`)

| File | CWatM setting (`[GROUNDWATER_MODFLOW]`) |
|---|---|
| `modflow_basin.tif` - active MODFLOW cells | `modflow_basin` |
| `elevation_modflow.tif` - average elevation of the DEM [m] | `topo_modflow` |
| `modflow_river_percentage.tif` - share of river cells of the finer network [0-1] | `chanRatio` |
| `finer_<res_finer>m/dem_finer.tif`, `stream_network_finer.tif` - finer DEM and river network (for checking) | - |

DEM: any CRS (lat/lon, UTM, ETRS89-LAEA ...), heights in m, nodata set in the file. It has to cover the MODFLOW
grid, which is rounded up to whole cells - clip it with a margin of at least 2 MODFLOW cells around the CWatM mask.
The script prints how far the DEM covers the grid on each side and stops if an active MODFLOW cell has no
elevation. The DEM is not read into memory as a whole (GDAL reads it in pieces), so large DEMs (EU-DEM 25 m) work.
With EU-DEM, `modflow_epsg = 3035` is recommended (equal area, no reprojection of the DEM).

Example `tisa1/`: EU-DEM 100 m (EPSG:3035) + CWatM mask 1 arcmin, settings `preprocessing_tisa1.ini` (every key
explained). 1000 m / 500 m: 93 x 83 cells, 4904 active (+0.15 % of the CWatM mask area), river percentage 0.313;
500 m / 100 m: 19639 active cells (+0.27 %), river percentage 0.073; a few seconds each.

Note: the river percentage depends strongly on `res_finer` - a river cell of 100 m covers a smaller share of a
MODFLOW cell than one of 500 m (tisa1: 0.073 with 100 m vs 0.313 with 500 m). CWatM uses it (`chanRatio`) to
split the upward flow from MODFLOW into baseflow and capillary rise, so keep `res_finer` the same as in earlier
setups if results should be comparable.

The script prints a check (active cells, area compared with the CWatM mask, elevation range, river share) and the
settings lines for CWatM. `plot = True` shows the maps.

## Differences to version 1 (`preprocessing_modflow2_ms`)

- No translation table (`indices/*.npy`, `intersection.csv`, shapefiles): CWatM will build it at the start.
  Until then, CWatM still needs the indices of version 1 for the same MODFLOW grid.
- Basin mask: share of each MODFLOW cell inside the CWatM mask, counted on a finer grid. Version 1 left out every
  MODFLOW cell touching a CWatM cell outside the mask (0 x inf = NaN in the area correction) - Tisza 1000 m:
  35077 instead of 35824 cells (-1.9 % of the basin area); version 2 is within +0.2 % of the CWatM mask area.
- The finer grid is derived from the MODFLOW grid (same origin, k x k cells), so the river share always fits.
- `extent = active` gives a smaller MODFLOW grid (Tisza 1000 m: 257 x 273 instead of 573 x 631 cells).
- River network with pyflwdir (Deltares) instead of pysheds: DEM depressions filled (priority flood), D8 flow
  direction, upstream area in m2. pysheds 0.5 (newest) does not run with NumPy 2.4 (`np.in1d`) and marked
  rivers on DEM nodata cells (Tisza: 75955 of 103481 nodata cells of the finer grid).
- No Python loops (Tisza 1000 m: ~35 s), settings in an ini file, deprecated pyproj calls replaced.
- Elevation written as float32 with nodata -9999 (version 1: nodata 0); output name `modflow_river_percentage.tif`
  (version 1: `modlfow_river_percentage.tif`).

Test Tisza 1000 m / 500 m, `extent = full` against version 1: same grid size (origin 11 m different - the mask
`area.tif` has a slightly different extent than `cellArea.tif`, which version 1 used); elevation mean abs
difference 0.6 m; basin see above.
River share: with pysheds (as version 1) identical in 96.4 % of the cells, same mean (0.2727). With pyflwdir the
mean river share in the basin is 0.254 instead of 0.270 (-6 %); on cells with DEM data 90 % of the finer river
cells agree. The difference comes from the different depression filling / flow directions - with
`stream_density = 1000` (rivers from 1 km2 = 4 finer cells) many very small streams count, so small changes in
the flow paths change the share. A slightly lower `stream_density` gives the same share again if needed.

Requirements: numpy, rasterio, pyproj, pyflwdir (needs numba, scipy, affine); matplotlib only for `plot = True`.
