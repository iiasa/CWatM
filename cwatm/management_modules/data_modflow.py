# -------------------------------------------------------------------------
# Name:        Data handling of the MODFLOW coupling
# Purpose:     all reading and writing of files of the CWatM - MODFLOW coupling (hydrological_modules/
#              groundwater_modflow): rasters and netCDF maps at ModFlow resolution
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import os

import numpy as np
import rasterio
from netCDF4 import Dataset

from cwatm.management_modules.messages import CWATMError, CWATMFileError, CWATMDirError
from cwatm.version import version_attributes


def raster_crs(filename):
    """CRS of a raster file; None if the file has no CRS or cannot be read as raster (e.g. MaskMap as coordinates)"""
    try:
        with rasterio.open(filename) as src:
            return src.crs
    except Exception:
        return None


def read_modflow_basin(filename):
    """
    Raster of the active ModFlow cells (modflow_basin), which defines the ModFlow grid:
    returns basin (2D bool, nrow x ncol), transform (affine: cell size, west / north edge) and CRS (None if missing)
    """
    with rasterio.open(filename, 'r') as src:
        return src.read(1).astype(bool), src.profile['transform'], src.crs


def read_modflow_tif(filename):
    """Map at ModFlow resolution (tif, same grid as modflow_basin) as float32"""
    with rasterio.open(filename, 'r') as src:
        return src.read(1).astype(np.float32)


def on_modflow_grid(filename, shape, transform):
    """True if filename is a raster with the ModFlow grid (same shape and transform as modflow_basin)"""
    try:
        with rasterio.open(filename) as src:
            return src.shape == shape and src.transform.almost_equals(transform)
    except Exception:
        return False


def write_modflow_netcdf(filename, name, data, units, long_name, transform, crs):
    """
    Map at ModFlow resolution (2D, nrow x ncol, or 3D with layers, nlay x nrow x ncol) as netCDF: float64 (exact
    values, e.g. the head for a restart), x / y of the cell centres (transform of modflow_basin), CRS of modflow_basin,
    nan outside the basin
    """
    nrow, ncol = np.shape(data)[-2:]
    with Dataset(filename, 'w', format='NETCDF4') as nc:
        nc.title = 'CWatM - MODFLOW: ' + long_name
        nc.setncatts(version_attributes())
        nc.createDimension('y', nrow)
        nc.createDimension('x', ncol)
        for axis, size, start, step in (('y', nrow, transform.f, transform.e),
                                        ('x', ncol, transform.c, transform.a)):
            coordinate = nc.createVariable(axis, 'f8', (axis,))
            coordinate.standard_name = 'projection_' + axis + '_coordinate'
            coordinate.units = 'm'
            coordinate[:] = start + (np.arange(size) + 0.5) * step
        dimensions = ('y', 'x')
        if np.ndim(data) == 3:
            nc.createDimension('layer', np.shape(data)[0])
            layer = nc.createVariable('layer', 'i4', ('layer',))
            layer.long_name = 'ModFlow layer (1: top)'
            layer[:] = np.arange(1, np.shape(data)[0] + 1)
            dimensions = ('layer', 'y', 'x')
        variable = nc.createVariable(name, 'f8', dimensions, zlib=True, fill_value=np.nan)
        variable.long_name = long_name
        variable.units = units
        if crs is not None:
            crs_variable = nc.createVariable('crs', 'i4')
            crs_variable.crs_wkt = crs_variable.spatial_ref = crs.to_wkt()
            variable.grid_mapping = 'crs'
        variable[:] = np.asarray(data, dtype=np.float64)


def read_modflow_netcdf(filename, nlay, nrow, ncol, variable=None):
    """
    Maps of nlay layers at ModFlow resolution (nlay, nrow, ncol) from a netCDF file (the variable with 3 dimensions
    layer, row, col - or 2 dimensions row, col for one layer), values as they are stored (no mask).
    variable: name of the netCDF variable (default: the last variable with 2 or 3 dimensions)
    """
    with Dataset(filename) as nc:
        nc.set_auto_mask(False)
        name = variable if variable is not None else [v for v in nc.variables if nc[v].ndim in (2, 3)][-1]
        if name not in nc.variables:
            msg = "Error 153: the variable " + name + " is not in the file - variables with maps: "
            msg += ", ".join(v for v in nc.variables if nc[v].ndim in (2, 3)) + "\n"
            raise CWATMFileError(filename, msg=msg)
        data = nc[name][:]
    if data.ndim == 2:
        data = data[np.newaxis]
    if data.shape != (nlay, nrow, ncol):
        msg = "Error 149: the map has " + " x ".join(str(i) for i in data.shape) + " cells (layers x rows x cols)"
        msg += " - the ModFlow grid (modflow_basin, nlay) has " + str(nlay) + " x " + str(nrow) + " x "
        msg += str(ncol) + "\n"
        raise CWATMFileError(filename, msg=msg)
    return data


def find_restart_head(init_file):
    """
    MODFLOW head saved together with the init file (save_initial): <init file without extension>_modflowhead.nc;
    None if it does not exist (before 2026-10-13 also <...>_modflowhead.npy, written before 2026-10)
    """
    filename = os.path.splitext(init_file)[0] + '_modflowhead.nc'
    return filename if os.path.isfile(filename) else None


def write_discrepancy_file(filename, discrepancy, threshold):
    """
    Text file of the MODFLOW water balance errors: each MODFLOW run (number, date, error in %) with an error above
    threshold (%), or one line that the error was always below it
    """
    with open(filename, "w") as discrep_file:
        sum_modflow_errors = 0
        for nrun, date, error in discrepancy:
            if abs(error) > threshold:  # if error is higer than threeshold in %, we print it.
                discrep_file.write("ModFlow stress period " + str(nrun) + " (" + date +
                                   ") : percentage error in ModFlow is " + str(error) + "\n")
                sum_modflow_errors += 1
        if sum_modflow_errors == 0:
            discrep_file.write("ModFlow error was always below " + str(threshold) + ' % during the simulation')

def make_directory(path):
    """Create a folder (and its parents) if it does not exist"""
    os.makedirs(path, exist_ok=True)


def remove_file(filename):
    """Delete a file if it exists"""
    try:
        os.remove(filename)
    except OSError:
        pass


def read_binary(filename):
    """Content of a file as bytes"""
    with open(filename, 'rb') as f:
        return f.read()


def read_text(filename):
    """Content of a text file without leading / trailing blanks; None if the file does not exist"""
    if not os.path.isfile(filename):
        return None
    with open(filename) as f:
        return f.read().strip()


def write_text(filename, text):
    """Write text into a new file"""
    with open(filename, 'w') as f:
        f.write(text)


def check_mf6_directory(path):
    """Error 222 if the folder with the MODFLOW library (path_mf6dll) does not exist"""
    if not os.path.isdir(path):
        msg = "Error 222: Path to Modflow6 files does not exists "
        raise CWATMDirError(path, msg, sname='path_mf6dll')


def mf6_library_path(folder, library_name):
    """
    Real path of the MODFLOW library in folder (path_mf6dll; MODFLOW needs the real path, no symlinks);
    Error 310 if it does not exist
    """
    library_path = os.path.realpath(os.path.join(folder, library_name))
    if not os.path.isfile(library_path):
        msg = "Error 310: MODFLOW library " + library_name + " not found\n"
        raise CWATMFileError(library_path, msg=msg, sname="path_mf6dll")
    return library_path


def mf6_simulation_file(working_directory):
    """
    Real path of the MODFLOW simulation file mfsim.nam in working_directory. Error 226 if it does not exist, Error 227
    if input files listed in the name files (or referenced with OPEN/CLOSE) are missing - a missing input file stops
    MODFLOW with a Fortran STOP, which also ends Python (exit code 2)
    """
    config_file = os.path.realpath(os.path.join(working_directory, 'mfsim.nam'))
    if not os.path.exists(config_file):
        msg = "Error 226: MODFLOW simulation file not found - delete input_hash in this folder or set\n"
        msg += "load_modflow_from_disk = False, then the MODFLOW input files are written new\n"
        raise CWATMFileError(config_file, msg=msg, sname="load_modflow_from_disk")
    input_files = mf6_input_files(working_directory)
    missing = [f for f in input_files + mf6_external_files(working_directory, input_files)
               if not os.path.isfile(os.path.join(working_directory, f))]
    if missing:
        msg = "Error 227: MODFLOW input files listed in the name files are missing in:\n"
        msg += os.path.realpath(working_directory) + "\n" + "\n".join(missing) + "\n"
        msg += "Delete input_hash in this folder or set load_modflow_from_disk = False to write them new\n"
        raise CWATMError(msg)
    return config_file


def mf6_input_files(working_directory, namefile='mfsim.nam'):
    """
    Return the input files listed in a MODFLOW 6 name file and in the model name files listed there

    In each block except OPTIONS a line "FTYPE6  file  ..." has the file name as 2nd entry.
    Files referenced inside package files (OPEN/CLOSE) are found with mf6_external_files.
    """
    files = []
    block = None
    with open(os.path.join(working_directory, namefile)) as f:
        for line in f:
            words = line.split()
            if not words or words[0][0] in '#!':
                continue
            if words[0].upper() == 'BEGIN':
                block = words[1].upper()
            elif words[0].upper() == 'END':
                block = None
            elif block not in (None, 'OPTIONS') and len(words) > 1 and words[0].upper().endswith('6'):
                fname = words[1].strip('\'"')
                files.append(fname)
                if block == 'MODELS' and os.path.isfile(os.path.join(working_directory, fname)):
                    files += mf6_input_files(working_directory, fname)
    return files


def mf6_external_files(working_directory, files):
    """
    Return the files referenced with OPEN/CLOSE in the package files (e.g. the binary files top.bin, wells.bin)

    Only package files smaller than 1 MB are read: flopy writes the reference to an external file into a small
    package file; a large package file has the data inside (text input)
    """
    external = []
    for fname in files:
        path = os.path.join(working_directory, fname)
        if not os.path.isfile(path) or os.path.getsize(path) > 1000000:
            continue
        with open(path, errors='replace') as f:
            for line in f:
                words = line.split()
                for i, word in enumerate(words[:-1]):
                    if word.upper() == 'OPEN/CLOSE':
                        external.append(words[i + 1].strip('\'"'))
    return external


def mf6_error_text(working_directory, nlines=30):
    """
    Return the ERROR REPORT in mfsim.lst (MODFLOW listing file) and the lines after it,
    and the names of the files where the cause of the MODFLOW error can be found
    """
    wd = os.path.realpath(working_directory)
    fname = os.path.join(wd, 'mfsim.lst')
    text = ""
    if os.path.isfile(fname):
        with open(fname, errors='replace') as f:
            lines = f.readlines()
        start = [i for i, line in enumerate(lines) if 'ERROR REPORT' in line]
        if start:
            # the first one: an ERROR REPORT can be followed by a UNIT ERROR REPORT
            text = "MODFLOW error message:\n" + "".join(lines[start[0]:start[0] + nlines]).rstrip() + "\n\n"
        text += "The cause of the MODFLOW error is in the MODFLOW listing file:\n" + fname + "\n"
        text += "(more information: the model listing file *.lst and mfsim.stdout in the same folder)\n"
    else:
        text += "No MODFLOW listing file mfsim.lst (MODFLOW stopped before writing it) - look at mfsim.stdout\n"
        text += "(if it exists) in: " + wd + "\n"
    return text


def modflow_netcdf_grid(nf1, domain):
    """
    ModFlow grid in a new output netCDF file of writenetcdf (data_handling.py: variables with 'modflow' in the
    name): dimensions and coordinates x, y (cell centres, m) and the CRS of modflow_basin (variable crs, with CF
    attributes if pyproj is installed). domain: ModFlow grid (globals.domain, set in groundwater_modflow/grid.py)
    """
    row, col = domain['nrow'], domain['ncol']
    nf1.createDimension('x', col)
    longitude = nf1.createVariable('x', 'f8', ('x',))
    for key, val in (('standard_name', 'projection_x_coordinate'), ('units', 'm'), ('axis', 'X')):
        setattr(longitude, key, val)
    nf1.createDimension('y', row)
    latitude = nf1.createVariable('y', 'f8', 'y')
    for key, val in (('standard_name', 'projection_y_coordinate'), ('units', 'm'), ('axis', 'Y')):
        setattr(latitude, key, val)
    # CRS of modflow_basin (e.g. EPSG:3035), not the CWatM one
    if domain.get('crs') is not None:
        crs = nf1.createVariable('crs', 'i4', ())
        crs.crs_wkt = crs.spatial_ref = domain['crs'].to_wkt()
        try:
            # CF attributes (grid_mapping_name ...) for Panoply / netCDF-Java, pyproj is optional
            import pyproj
            for key, val in pyproj.CRS.from_wkt(crs.crs_wkt).to_cf().items():
                setattr(crs, key, val)
        except ImportError:
            pass
    # cell centres (north / west are the edges of modflow_basin)
    latitude[:] = domain['north'] - (np.arange(row) + 0.5) * domain['rowsize']
    longitude[:] = domain['west'] + (np.arange(col) + 0.5) * domain['colsize']


def modflow_netcdf_variable(nf1, varname, flagTime, domain):
    """
    Output variable at ModFlow resolution in a new netCDF file of writenetcdf: (time, y, x) or (y, x), float32,
    grid mapping crs if the file has the CRS
    """
    if flagTime:
        value = nf1.createVariable(varname, 'f4', ('time', 'y', 'x'), zlib=True, fill_value=1e20,
                                   chunksizes=(1, domain['nrow'], domain['ncol']))
    else:
        value = nf1.createVariable(varname, 'f4', ('y', 'x'), zlib=True, fill_value=1e20)
    if 'crs' in nf1.variables:
        value.grid_mapping = "crs"
    return value
