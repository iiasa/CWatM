# MODFLOW preprocessing for CWatM - version 2

`Toolkit/preprocessing_modflow_v2/preprocess_modflow.py` creates the MODFLOW input maps for the CWatM-MODFLOW
coupling from two input maps: the CWatM mask and a fine DEM. It replaces `Toolkit/preprocessing_modflow2_ms`
(version 1).

Created 2026-10-05.

## 1. Overview

```
python preprocess_modflow.py preprocessing_tisa1.ini
```

| | |
|---|---|
| Input | CWatM mask map, fine DEM (any CRS) |
| Output | `modflow_basin.tif`, `elevation_modflow.tif`, `modflow_river_percentage.tif` (+ finer DEM and river network for checking) |
| Settings | one ini file (every key explained in `preprocessing_tisa1.ini`) |
| Requirements | numpy, rasterio, pyproj, pyflwdir (needs numba, scipy, affine); matplotlib only for `plot = True` |
| Run time | tisa1 (4900 km2): a few seconds; Tisza (157000 km2, 1000 m / 500 m): ~35 s |

The translation table between the CWatM grid and the MODFLOW grid (version 1: `indices/*.npy`) is **not** created
here. CWatM will build it at the start of a run (plan: `cwatm/hydrological_modules/groundwater_modflow/wmodflow.md`,
section 9). Until then the version 2 maps cannot be used in a CWatM run.

## 2. Input

### CWatM mask (`cwatm_mask`)

- The mask map of the CWatM setup (`MaskMap`), e.g. `area_tisa1.tif`.
- tif with CRS, or a file without CRS (e.g. PCRaster `.map`) - then `cwatm_epsg` gives the CRS.
- Active cells: not nodata and not 0 (e.g. 1 = basin, 255 = nodata).
- lat/lon (EPSG:4326) or projected (e.g. EPSG:3035 for a 1 km CWatM setup).

### DEM (`dem`)

- Any CRS: lat/lon (e.g. MERIT 3"), UTM, ETRS89-LAEA (EU-DEM 25 m / 100 m) ...
- Heights in m; the nodata value has to be set in the file (sea, gaps).
- It has to cover the MODFLOW grid, not only the mask: the grid is rounded up to whole cells. Clip the DEM with a
  margin of at least 2 MODFLOW cells around the CWatM mask (e.g. 2-5 km for 1000 m cells).
- A CRS written without EPSG code (EU-DEM: `ETRS89_ETRS_LAEA`) is recognised by its projection parameters as
  EPSG:3035.
- The DEM is not read into memory as a whole - GDAL reads it in pieces, so large DEMs work.

## 3. Settings

| Section | Key | Meaning | Example |
|---|---|---|---|
| PATHS | `cwatm_mask` | CWatM mask map | `tisa1/area_tisa1.tif` |
| | `dem` | fine DEM | `tisa1/eudem100m_clip.tif` |
| | `output_folder` | output: maps in `<output_folder>/<res_modflow>m/`, finer maps in `.../finer_<res_finer>m/` | `tisa1/output` |
| GRID | `cwatm_epsg` | EPSG of the mask - only used if the mask file has no CRS | `4326` |
| | `modflow_epsg` | EPSG of the MODFLOW grid (metres); empty: UTM zone of the basin centre | `3035` |
| | `res_modflow` | MODFLOW cell size [m] | `500` |
| | `res_finer` | cell size of the river network grid [m]; `res_modflow` a whole multiple of it, best a multiple of the DEM resolution | `100` |
| | `extent` | `active`: grid around the active CWatM cells (smaller); `full`: around the whole mask rectangle (as version 1) | `active` |
| | `basin_fraction` | MODFLOW cell active if more than this share of its area is inside the CWatM mask | `0.5` |
| | `mask_subsampling` | the share is counted on a grid this many times finer than MODFLOW (10 = 100 points per cell, 1 %) | `10` |
| | `snap_to_dem` | move the grid origin onto the DEM pixel grid (only if DEM and MODFLOW have the same CRS) | `True` |
| RIVER | `stream_density` | river where the upstream area > `stream_density`^2 [m2]; >= `res_finer` | `1000` (1 km2) |
| OPTIONS | `plot` | show maps of basin, elevation and river percentage at the end | `False` |
| EXTRA_MAPS | `<name> = <file>` | optional maps projected to the MODFLOW grid (average), written as `<name>.tif` | `permeability_modflow = perm.tif` |

Relative paths are relative to the settings file. The script stops with an error for: missing settings file,
mask without CRS and without `cwatm_epsg`, mask without active cells, `res_modflow` not a whole multiple of
`res_finer`, `stream_density` < `res_finer`, wrong `extent`, DEM without CRS, active MODFLOW cells without
elevation.

**Recommended:** with EU-DEM `modflow_epsg = 3035` - equal area (a 1000 m cell is 1 km2; UTM cells are up to
~0.4 % off in large basins) and the DEM needs no reprojection.

## 4. Steps

### Step 1: MODFLOW grid

1. Read the CWatM mask; active cells as above.
2. MODFLOW CRS from `modflow_epsg`, or the UTM zone (WGS84, north/south) of the centre of the active cells.
3. All corners of the CWatM cells (`extent = active`: only corners of active cells; `full`: all corners of the mask
   rectangle) are transformed to the MODFLOW CRS (`pyproj.Transformer`).
4. Grid: from the smallest x and y, rounded up to whole cells of `res_modflow`.
5. `snap_to_dem`: if the DEM has the same CRS, the west and north edge are moved outwards to the next DEM pixel
   edge, the grid is extended to still cover everything. Then every MODFLOW and finer cell contains whole DEM
   pixels (no interpolation).
6. The script prints by how many metres the DEM covers the grid on each side.

### Step 2: basin mask (`modflow_basin.tif`)

- The CWatM mask (0/1) is projected (nearest neighbour) onto a grid `mask_subsampling` times finer than MODFLOW,
  in blocks of 100 MODFLOW rows (memory).
- Share of each MODFLOW cell inside the mask = mean of its `mask_subsampling`^2 sub-cells.
- Active (1) if share > `basin_fraction`, else 0. int32, nodata -1.

### Step 3: elevation (`elevation_modflow.tif`)

- DEM projected onto the MODFLOW grid with `Resampling.average` (mean of the DEM pixels in each cell; nodata pixels
  are not counted).
- Error if an active MODFLOW cell has no elevation (DEM does not cover it).
- float32, nodata -9999.

### Step 4: river network on the finer grid

1. Finer grid: same origin as the MODFLOW grid, `k = res_modflow / res_finer`, `k*nrow x k*ncol` cells - the
   finer cells always fit exactly into the MODFLOW cells.
2. DEM projected onto the finer grid (average) -> `finer_<res_finer>m/dem_finer.tif`.
3. Hydrologically conditioned DEM and flow directions with **pyflwdir** (`pyflwdir.from_dem`):
   - all depressions filled with the priority-flood method (Wang & Liu 2006), water leaves the DEM at its edge
     (`outlets = 'edge'`), no depth limit;
   - D8 flow direction from the filled DEM.
   The filled DEM is only kept in memory (not written).
4. Upstream area of each finer cell [m2] (`upstream_area`); river (1) where it is > `stream_density`^2, else 0
   -> `finer_<res_finer>m/stream_network_finer.tif` (uint8).

### Step 5: river percentage (`modflow_river_percentage.tif`)

- Share of river cells among the `k x k` finer cells of each MODFLOW cell (block mean), 0-1.
- float32, nodata -9999.

### Step 6: extra maps (optional)

- Each map of `[EXTRA_MAPS]` projected onto the MODFLOW grid (average), written as `<name>.tif`.

### Check report

Printed at the end:
- active MODFLOW cells / all cells;
- active MODFLOW area compared with the CWatM mask area (lat/lon: area on the sphere, R = 6371007 m) and the mask
  area seen by the MODFLOW grid (sum of the shares);
- elevation range in active cells;
- mean river percentage and number of active cells with river;
- the lines for the CWatM settings file.

## 5. Output and CWatM settings

`<output_folder>/<res_modflow>m/`:

| File | Content | CWatM setting (`[GROUNDWATER_MODFLOW]`) |
|---|---|---|
| `modflow_basin.tif` | active MODFLOW cells (1/0), defines the MODFLOW grid (CRS, origin, cell size, rows, columns) | `modflow_basin` |
| `elevation_modflow.tif` | ground elevation [m] | `topo_modflow` |
| `modflow_river_percentage.tif` | share of river in each cell [0-1] - splits upward flow from MODFLOW into baseflow and capillary rise | `chanRatio` |
| `<name>.tif` | extra maps (optional) | e.g. `permeability`, `poro` |
| `finer_<res_finer>m/dem_finer.tif` | DEM on the finer grid (for checking) | - |
| `finer_<res_finer>m/stream_network_finer.tif` | river network (for checking) | - |

Also set `Modflow_resolution = <res_modflow>`. All maps have the same grid and CRS.

## 6. Choosing res_finer and stream_density

The river percentage depends strongly on both:

| tisa1 | res_modflow | res_finer | stream_density | river percentage (mean of active cells) |
|---|---|---|---|---|
| | 1000 | 500 | 1000 | 0.313 |
| | 500 | 100 | 1000 | 0.073 |
| | 500 | 500 | 500 | 0.533 - only 0 or 1 per cell |

- A river cell of 100 m covers a smaller share of a MODFLOW cell than one of 500 m.
- `res_finer = res_modflow` (k = 1) gives no percentage, only 0 or 1.
- `stream_density` close to `res_finer` makes almost every cell with one upstream cell a river.
- For results comparable with earlier setups keep `res_finer` and `stream_density` as there (version 1 setups:
  e.g. Tisza 1000 m / 500 m / 1000).

## 7. Differences to version 1 (`preprocessing_modflow2_ms`)

| | Version 1 | Version 2 |
|---|---|---|
| Translation table | shapefiles of both grids (`gdal_polygonize` with hard-coded paths), geopandas intersection, `intersection.csv`, `indices/*.npy` | none - CWatM builds it |
| Basin mask | from the intersection table; **bug**: every MODFLOW cell touching a CWatM cell outside the mask was left out (0 x inf = NaN in the area correction) - Tisza 1000 m: 35077 instead of 35824 cells, -1.9 % of the basin area | share counted on a finer grid; within +0.2 % of the CWatM mask area |
| Finer grid | computed separately - can be shifted by rows against the MODFLOW grid | derived from the MODFLOW grid, always fits |
| River network | pysheds (does not run with NumPy 2.4; marked rivers on DEM nodata cells) | pyflwdir |
| Grid extent | whole mask rectangle | active cells (`extent = active`), Tisza 1000 m: 257 x 273 instead of 573 x 631 cells |
| DEM | lat/lon, read into memory | any CRS, read in pieces, optional snap to the DEM pixels |
| Settings | edit the Python code | ini file |
| Speed | Python loops, QGIS step | no loops, ~35 s for Tisza |
| Elevation nodata | 0 | -9999 (float32) |
| River map name | `modlfow_river_percentage.tif` | `modflow_river_percentage.tif` |
| Dependencies | geopandas, shapely, xarray, scipy, netCDF4, pysheds, QGIS | numpy, rasterio, pyproj, pyflwdir |

## 8. Tests

**Tisza 1000 m / 500 m, `extent = full`, against version 1** (`preprocessing_modflow2_ms/Created_files/1000m2`):
- same grid size 573 x 631; origin 11 m different (version 1 took the extent from `cellArea.tif`, which differs
  slightly from the mask `area.tif`);
- elevation: mean abs difference 0.6 m;
- basin: 35824 vs 35077 cells - all 747 extra cells come from the version 1 NaN bug; version 1 with the bug fixed
  gives 35849 cells (75 cells different, border cells near 0.5);
- river percentage with pysheds: identical in 96.4 % of the cells, same mean 0.2727; with pyflwdir: mean 0.254
  (-6 %), 90 % of the finer river cells agree (different depression filling / flow paths; many very small streams
  with `stream_density = 1000`).

**Tisza with the DEM in UTM34 and UTM33** (DEM resampled to 100 m for the test): same basin and grid; elevation
mean difference < 0.03 m (mean abs 0.6 / 1.7 m from the extra resampling of the test DEM); same mean river
percentage 0.254.

**tisa1** (EU-DEM 100 m, EPSG:3035, CWatM mask 1 arcmin, `modflow_epsg = 3035`, snap): 500 m / 100 m:
185 x 164 cells, 19639 active (4910 km2, +0.27 % of the mask area), elevation 92.6 - 169.7 m, river percentage
0.073; DEM margin 1.5 - 3 km.

## 9. Open points

- CWatM has to build the translation table itself (wmodflow.md section 9) - before that, no CWatM run with the
  version 2 maps; then a test run against a version 1 setup (discharge, water table, MODFLOW discrepancy).
- Not tested: PCRaster `.map` mask with `cwatm_epsg`, automatic UTM zone, `[EXTRA_MAPS]`, CWatM grid in a projected
  CRS, very large basins (pyflwdir memory on the finer grid).
- Optional: write the filled (hydro) DEM and the D8 flow directions of pyflwdir for checking.
- River percentage outside the basin is computed but not used by CWatM.
- Settings files in pytest / Tutorials still use `modlfow_river_percentage.tif` and `indices` (change after the
  CWatM change).
- Version 1 folder: remove or mark as old after checking; existing setups made with it have the basin mask bug.
