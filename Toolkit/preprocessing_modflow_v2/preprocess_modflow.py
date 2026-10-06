# -*- coding: utf-8 -*-
"""
Preprocessing of the maps for the CWatM-MODFLOW coupling (version 2)

Creates at the MODFLOW resolution (regular grid in metres, e.g. UTM):
    modflow_basin.tif               active MODFLOW cells (1) - more than basin_fraction of the cell inside the CWatM mask
    elevation_modflow.tif           ground elevation, average of the fine DEM [m]
    modflow_river_percentage.tif    fraction of river cells of a finer river network in each MODFLOW cell [0-1]
and in the subfolder finer_<res_finer>m:
    dem_finer.tif                   fine DEM on the finer grid (aligned with the MODFLOW grid)
    stream_network_finer.tif        river network on the finer grid (1 river, 0 no river)

The translation table between the CWatM and MODFLOW grid (indices) is not created here - CWatM builds it itself.
Based on Toolkit/preprocessing_modflow2_ms (L. Guillaumot, J. de Bruijn, M. Smilovic), without shapefiles, QGIS,
intersection table and Python loops.

Usage:
    python preprocess_modflow.py preprocessing_tisa1.ini
"""

import configparser
import math
import os
import sys
import warnings

import numpy as np
import rasterio
import rasterio.warp
from pyproj import CRS, Transformer
from rasterio import Affine
from rasterio.warp import reproject, Resampling

NODATA = -9999.0


def read_settings(inifile):
    """Read the settings file and return a dict with the values (types converted)"""
    config = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    config.optionxform = str  # keep upper/lower case of the keys (extra maps)
    if not config.read(inifile):
        sys.exit("Error: settings file not found: " + inifile)
    base = os.path.dirname(os.path.abspath(inifile))

    def path(name):
        p = config.get('PATHS', name)
        return os.path.normpath(p if os.path.isabs(p) else os.path.join(base, p))

    s = {
        'mask': path('cwatm_mask'),
        'dem': path('dem'),
        'output': path('output_folder'),
        'cwatm_epsg': config.get('GRID', 'cwatm_epsg', fallback='').strip(),
        'modflow_epsg': config.get('GRID', 'modflow_epsg', fallback='').strip(),
        'res': config.getfloat('GRID', 'res_modflow'),
        'res_finer': config.getfloat('GRID', 'res_finer'),
        'extent': config.get('GRID', 'extent', fallback='active').strip().lower(),
        'basin_fraction': config.getfloat('GRID', 'basin_fraction', fallback=0.5),
        'mask_sub': config.getint('GRID', 'mask_subsampling', fallback=10),
        'snap': config.getboolean('GRID', 'snap_to_dem', fallback=True),
        'stream_density': config.getfloat('RIVER', 'stream_density'),
        'plot': config.getboolean('OPTIONS', 'plot', fallback=False),
        'extra': {}
    }
    if config.has_section('EXTRA_MAPS'):
        for name, p in config.items('EXTRA_MAPS'):
            s['extra'][name] = os.path.normpath(p if os.path.isabs(p) else os.path.join(base, p))

    if s['extent'] not in ('active', 'full'):
        sys.exit("Error: extent has to be 'active' or 'full', not " + s['extent'])
    k = s['res'] / s['res_finer']
    if abs(k - round(k)) > 1e-9 or round(k) < 1:
        sys.exit("Error: res_modflow (%g) has to be a whole multiple of res_finer (%g)" % (s['res'], s['res_finer']))
    s['k'] = int(round(k))
    if s['stream_density'] < s['res_finer']:
        sys.exit("Error: stream_density (%g) has to be >= res_finer (%g)" % (s['stream_density'], s['res_finer']))
    return s


def read_cwatm_mask(filename, cwatm_epsg):
    """Read the CWatM mask; returns active cells (bool), transform and CRS.
    Active: not nodata and not 0. A file without CRS (e.g. PCRaster .map) needs cwatm_epsg."""
    with rasterio.open(filename) as src:
        data = src.read(1, masked=True)
        transform = src.transform
        crs = src.crs
    if crs is None:
        if not cwatm_epsg:
            sys.exit("Error: the CWatM mask has no CRS - set cwatm_epsg in [GRID] (e.g. 4326)")
        crs = CRS.from_epsg(int(cwatm_epsg))
    elif cwatm_epsg and not same_crs(crs, CRS.from_epsg(int(cwatm_epsg))):
        print("Warning: cwatm_epsg %s differs from the CRS of the mask file - the CRS of the file is used" % cwatm_epsg)
    active = ~np.ma.getmaskarray(data) & (data.filled(0) != 0)
    if not active.any():
        sys.exit("Error: the CWatM mask has no active cell: " + filename)
    return active, transform, CRS.from_user_input(crs)


def utm_epsg(lon, lat):
    """EPSG code of the UTM zone (WGS84) at lon/lat"""
    zone = int((lon + 180) // 6) + 1
    return (32600 if lat >= 0 else 32700) + zone


def modflow_grid(active, cwatm_transform, cwatm_crs, modflow_crs, res, extent):
    """MODFLOW grid (affine, nrow, ncol) covering the CWatM mask.
    All corners of the CWatM cells (extent = 'full': whole mask rectangle, 'active': only active cells) are
    transformed to the MODFLOW CRS; the grid starts at the smallest x and y (as the old preprocessing)."""
    nrow_c, ncol_c = active.shape
    if extent == 'full':
        node = np.ones((nrow_c + 1, ncol_c + 1), dtype=bool)
    else:
        node = np.zeros((nrow_c + 1, ncol_c + 1), dtype=bool)  # corners of the active cells
        node[:-1, :-1] |= active
        node[1:, :-1] |= active
        node[:-1, 1:] |= active
        node[1:, 1:] |= active
    rows, cols = np.nonzero(node)
    x, y = cwatm_transform * (cols, rows)
    xm, ym = Transformer.from_crs(cwatm_crs, modflow_crs, always_xy=True).transform(x, y)
    xmin, xmax, ymin, ymax = np.min(xm), np.max(xm), np.min(ym), np.max(ym)
    ncol = math.ceil((xmax - xmin) / res)
    nrow = math.ceil((ymax - ymin) / res)
    affine = Affine(res, 0.0, xmin, 0.0, -res, ymin + nrow * res)
    return affine, nrow, ncol


def basin_mask(active, cwatm_transform, cwatm_crs, affine, nrow, ncol, crs, sub, fraction, block=100):
    """Active MODFLOW cells: share of the cell inside the CWatM mask > fraction.
    The share is counted on a grid sub x sub finer than MODFLOW (nearest neighbour), in blocks of MODFLOW rows."""
    res = affine.a
    share = np.zeros((nrow, ncol), dtype=np.float32)
    src = active.astype(np.uint8)
    for r0 in range(0, nrow, block):
        nr = min(block, nrow - r0)
        dst = np.zeros((nr * sub, ncol * sub), dtype=np.uint8)
        dst_transform = Affine(res / sub, 0.0, affine.c, 0.0, -res / sub, affine.f - r0 * res)
        reproject(src, dst, src_transform=cwatm_transform, src_crs=cwatm_crs, dst_transform=dst_transform,
                  dst_crs=crs, resampling=Resampling.nearest, src_nodata=None, dst_nodata=None)
        share[r0:r0 + nr] = dst.reshape(nr, sub, ncol, sub).mean(axis=(1, 3))
    return (share > fraction).astype(np.int32), share


def project_map(filename, affine, nrow, ncol, crs, resampling=Resampling.average):
    """Project a map (e.g. fine DEM) to a grid; cells without data are NaN.
    The map is not read into memory as a whole - GDAL reads it in pieces (large DEMs, e.g. EU-DEM 25 m)"""
    destination = np.full((nrow, ncol), np.nan, dtype=np.float32)
    with rasterio.open(filename) as src:
        if src.crs is None:
            sys.exit("Error: map has no CRS: " + filename)
        reproject(rasterio.band(src, 1), destination, src_nodata=src.nodata, dst_transform=affine, dst_crs=crs,
                  dst_nodata=np.nan, resampling=resampling)
    return destination


def same_crs(a, b):
    """True if two CRS are the same - also if one is written without EPSG code (e.g. EU-DEM 'ETRS89_ETRS_LAEA'
    = EPSG:3035): then the projection parameters are compared"""
    a, b = CRS.from_user_input(a), CRS.from_user_input(b)
    if a == b:
        return True
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')  # to_proj4 warns that it loses information
        return a.to_proj4() == b.to_proj4()


def snap_to_map(affine, nrow, ncol, filename, crs):
    """Move the grid origin onto the pixel grid of a map in the same CRS (west/north edge to the next pixel edge
    outside), so finer cells and map pixels line up. Returns the grid unchanged if the CRS differs."""
    with rasterio.open(filename) as src:
        if src.crs is None or not same_crs(src.crs, crs):
            return affine, nrow, ncol, False
        t = src.transform
    res = affine.a
    west = t.c + math.floor((affine.c - t.c) / t.a) * t.a
    north = t.f - math.floor((t.f - affine.f) / -t.e) * -t.e
    east, south = affine.c + ncol * res, affine.f - nrow * res
    ncol = math.ceil((east - west) / res - 1e-9)
    nrow = math.ceil((north - south) / res - 1e-9)
    return Affine(res, 0.0, west, 0.0, -res, north), nrow, ncol, True


def check_coverage(filename, affine, nrow, ncol, crs):
    """Distance [m] by which the map (e.g. DEM) covers the grid on each side (negative: grid outside the map)"""
    with rasterio.open(filename) as src:
        left, bottom, right, top = rasterio.warp.transform_bounds(src.crs, crs, *src.bounds)
    return {'west': affine.c - left, 'east': right - (affine.c + ncol * affine.a),
            'south': (affine.f - nrow * affine.a) - bottom, 'north': top - affine.f}


def write_tif(filename, array, affine, crs, nodata=None):
    """Write a 2D array as GeoTIFF (NaN -> nodata for float maps)"""
    if np.issubdtype(array.dtype, np.floating) and nodata is not None:
        array = np.where(np.isnan(array), nodata, array).astype(array.dtype)
    with rasterio.open(filename, 'w', driver='GTiff', width=array.shape[1], height=array.shape[0], count=1,
                       dtype=array.dtype, nodata=nodata, transform=affine, crs=crs, compress='deflate') as dst:
        dst.write(array, 1)
    print('  written: ' + filename)


def stream_network(dem, affine, stream_density):
    """River network from the fine DEM with pyflwdir: D8 flow direction after filling depressions (priority flood,
    water leaves at the edge of the DEM), upstream area; river where the upstream area > stream_density^2"""
    import pyflwdir  # only needed here
    nodata = NODATA
    flw = pyflwdir.from_dem(np.where(np.isnan(dem), nodata, dem).astype(np.float32), nodata=nodata,
                            transform=affine, latlon=False, outlets='edge')
    upa = flw.upstream_area(unit='m2')  # -9999 for nodata cells
    return (upa > stream_density ** 2).astype(np.uint8)


def main(inifile):
    s = read_settings(inifile)
    out = os.path.join(s['output'], '%dm' % s['res'])
    out_finer = os.path.join(out, 'finer_%dm' % s['res_finer'])
    os.makedirs(out_finer, exist_ok=True)

    # 1. CWatM mask and MODFLOW grid
    print('\n1. CWatM mask and MODFLOW grid')
    active, cwatm_transform, cwatm_crs = read_cwatm_mask(s['mask'], s['cwatm_epsg'])
    if s['modflow_epsg']:
        crs = CRS.from_epsg(int(s['modflow_epsg']))
    else:
        rows, cols = np.nonzero(active)
        x, y = cwatm_transform * (cols.mean() + 0.5, rows.mean() + 0.5)
        lon, lat = Transformer.from_crs(cwatm_crs, CRS.from_epsg(4326), always_xy=True).transform(x, y)
        crs = CRS.from_epsg(utm_epsg(lon, lat))
        print('  modflow_epsg not set - UTM zone of the basin centre: EPSG:%d' % crs.to_epsg())
    affine, nrow, ncol = modflow_grid(active, cwatm_transform, cwatm_crs, crs, s['res'], s['extent'])
    if s['snap']:
        affine, nrow, ncol, snapped = snap_to_map(affine, nrow, ncol, s['dem'], crs)
        if snapped:
            print('  grid origin moved onto the DEM pixel grid (snap_to_dem)')
    print('  CWatM: %d x %d cells, %d active, %s' % (active.shape[0], active.shape[1], active.sum(), cwatm_crs.to_string()))
    print('  MODFLOW: %d x %d cells of %g m, %s, west %.2f north %.2f' % (nrow, ncol, s['res'], crs.to_string(),
                                                                       affine.c, affine.f))
    cover = check_coverage(s['dem'], affine, nrow, ncol, crs)
    print('  DEM covers the MODFLOW grid by: ' + ', '.join('%s %.0f m' % kv for kv in cover.items()))

    # 2. basin mask
    print('\n2. MODFLOW basin mask')
    basin, share = basin_mask(active, cwatm_transform, cwatm_crs, affine, nrow, ncol, crs, s['mask_sub'],
                              s['basin_fraction'])
    write_tif(os.path.join(out, 'modflow_basin.tif'), basin, affine, crs, nodata=-1)

    # 3. elevation at MODFLOW resolution
    print('\n3. Elevation')
    elevation = project_map(s['dem'], affine, nrow, ncol, crs)
    missing = np.isnan(elevation) & (basin == 1)
    if missing.any():
        sys.exit("Error: %d active MODFLOW cells have no elevation - the DEM does not cover them (nodata or outside)."
                 "\nClip the DEM with a larger margin around the CWatM mask (DEM cover: %s)"
                 % (missing.sum(), ', '.join('%s %.0f m' % kv for kv in cover.items())))
    write_tif(os.path.join(out, 'elevation_modflow.tif'), elevation, affine, crs, nodata=NODATA)

    # 4. river network on the finer grid (same origin as the MODFLOW grid, k x k finer cells per MODFLOW cell)
    print('\n4. River network at %g m' % s['res_finer'])
    k = s['k']
    affine_finer = Affine(s['res_finer'], 0.0, affine.c, 0.0, -s['res_finer'], affine.f)
    dem_finer = project_map(s['dem'], affine_finer, nrow * k, ncol * k, crs)
    dem_finer_file = os.path.join(out_finer, 'dem_finer.tif')
    write_tif(dem_finer_file, dem_finer, affine_finer, crs, nodata=NODATA)
    streams = stream_network(dem_finer, affine_finer, s['stream_density'])
    write_tif(os.path.join(out_finer, 'stream_network_finer.tif'), streams, affine_finer, crs)

    # 5. river percentage: mean of the k x k finer cells
    print('\n5. River percentage')
    river = streams.reshape(nrow, k, ncol, k).mean(axis=(1, 3), dtype=np.float64).astype(np.float32)
    write_tif(os.path.join(out, 'modflow_river_percentage.tif'), river, affine, crs, nodata=NODATA)

    # 6. optional maps (e.g. permeability, porosity) projected with average
    if s['extra']:
        print('\n6. Extra maps')
        for name, filename in s['extra'].items():
            write_tif(os.path.join(out, name + '.tif'), project_map(filename, affine, nrow, ncol, crs),
                      affine, crs, nodata=NODATA)

    # check report
    inb = basin == 1
    cwatm_area = None
    if cwatm_crs.is_geographic:
        # area of the active CWatM cells on the sphere (R = 6371007 m)
        r = 6371007.0
        rows = np.arange(active.shape[0])
        lat_top = np.radians(cwatm_transform.f + cwatm_transform.e * rows)
        lat_bot = np.radians(cwatm_transform.f + cwatm_transform.e * (rows + 1))
        row_area = r * r * np.radians(abs(cwatm_transform.a)) * np.abs(np.sin(lat_top) - np.sin(lat_bot))
        cwatm_area = (active.sum(axis=1) * row_area).sum()
    elif cwatm_crs.is_projected:
        cwatm_area = active.sum() * abs(cwatm_transform.a * cwatm_transform.e)
    print('\n=== Check ===')
    print('  active MODFLOW cells: %d of %d' % (inb.sum(), basin.size))
    if cwatm_area:
        print('  area: MODFLOW active %.0f km2, CWatM mask %.0f km2 (%+.2f %%), mask area seen by MODFLOW grid %.0f km2'
              % (inb.sum() * s['res'] ** 2 / 1e6, cwatm_area / 1e6,
                 100 * (inb.sum() * s['res'] ** 2 / cwatm_area - 1), share.sum() * s['res'] ** 2 / 1e6))
    print('  elevation in active cells: %.1f - %.1f m' % (elevation[inb].min(), elevation[inb].max()))
    print('  river percentage in active cells: mean %.3f, cells with river %d' % (river[inb].mean(), (river[inb] > 0).sum()))
    print('\nCWatM settings ([GROUNDWATER_MODFLOW]):')
    print('  Modflow_resolution = %d' % s['res'])
    print('  modflow_basin = %s' % os.path.join(out, 'modflow_basin.tif'))
    print('  topo_modflow = %s' % os.path.join(out, 'elevation_modflow.tif'))
    print('  chanRatio = %s' % os.path.join(out, 'modflow_river_percentage.tif'))

    if s['plot']:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 3, figsize=(15, 5))
        for a, data, title in zip(ax, (basin, np.where(inb, elevation, np.nan), np.where(inb, river, np.nan)),
                                  ('MODFLOW basin', 'Elevation [m]', 'River percentage')):
            im = a.imshow(data, interpolation='none')
            a.set_title(title)
            fig.colorbar(im, ax=a, shrink=0.7)
        plt.tight_layout()
        plt.show()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
