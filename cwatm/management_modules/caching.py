# -------------------------------------------------------------------------
# Name:        caching
# Purpose:     Keep input files open during a run instead of opening them again and again.
#
#              1. netCDF: read-only input files are opened only once.
#                 Opening a file on a network drive can cost up to 0.6 s per open,
#                 and without a cache the same files are opened many times during init.
#              2. Excel: the settings workbook (reservoirs, crops, wastewater, ...) is opened
#                 only once and read with the fastest available reader.
#                 If python-calamine is installed (pip install python-calamine, pandas >= 2.2)
#                 it is used: 10-25x faster than openpyxl, identical results.
#                 Without python-calamine openpyxl is used (as before).
#
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import os
import importlib
import netCDF4

nchandles = {}    # normalized filename -> open netCDF4.Dataset (read-only)
excelbooks = {}   # normalized filename -> open pandas.ExcelFile
ncstackvars = set()   # (normalized filename, variable name) whose chunk cache is already set


def _key(filename):
    """
    Normalized dictionary key for a filename, so that different spellings of the
    same path (slashes, '..', upper/lower case on Windows) share one handle.
    """
    return os.path.normcase(os.path.abspath(os.path.normpath(filename)))


# -------------------------------------------------------------------------
# netCDF
# -------------------------------------------------------------------------

def ncopen(filename):
    """
    Return an open read-only netCDF Dataset; the file is opened only on first request.

    Raises the same exception as netCDF4.Dataset if the file cannot be opened,
    so existing try/except blocks keep working. Failed opens are not cached.

    Parameters
    ----------
    filename : str
        Path to the netCDF file.

    Returns
    -------
    netCDF4.Dataset
        Open dataset (read-only). Do not close it - use ncclose / ncclose_all.
    """
    key = _key(filename)
    nf = nchandles.get(key)
    if (nf is not None) and nf.isopen():
        return nf

    # static maps are read once -> no chunk cache needed (a chunk bigger than the
    # cache is read directly). Prevents memory build-up with many open files.
    old = netCDF4.get_chunk_cache()
    netCDF4.set_chunk_cache(size=0, nelems=1, preemption=0.75)
    try:
        nf = netCDF4.Dataset(filename, 'r')
    finally:
        netCDF4.set_chunk_cache(*old)
    nchandles[key] = nf
    return nf


def ncstackcache(filename, ncvar, maxcache=256 * 1024 * 1024):
    """
    Chunk cache for a map stack that is read step by step in the time loop
    (e.g. 10-day, monthly or day-of-year stacks).

    If several time steps are stored in one chunk (e.g. chunks of 92 days), the decompressed
    chunks stay in memory, so the next time step does not decompress the whole block again
    (measured for Reservoir_releases: 54 ms -> 4 ms per read).
    Stacks with one time step per chunk are skipped (nothing to gain).

    Set only once per variable: setting it again reopens the variable and empties the cache.

    Parameters
    ----------
    filename : str
        Path of the netCDF file (used as key together with the variable name).
    ncvar : netCDF4.Variable
        3D variable (time, y, x) of the open file.
    maxcache : int, optional
        Upper limit in bytes. If more is needed the cache is not set (behaviour as before).
    """
    key = (_key(filename), ncvar.name)
    if key in ncstackvars:
        return
    ncstackvars.add(key)

    try:
        chunks = ncvar.chunking()
    except:
        return
    if (chunks is None) or (chunks == 'contiguous') or (len(chunks) != 3) or (chunks[0] <= 1):
        return   # one time step per chunk: every read needs its own chunk anyway

    ct, cy, cx = chunks
    ny, nx = ncvar.shape[1], ncvar.shape[2]
    nchunks = -(-ny // cy) * -(-nx // cx)          # chunks covering one map (ceiling division)
    size = (nchunks + 1) * ct * cy * cx * ncvar.dtype.itemsize
    if size > maxcache:
        return   # too big for memory: keep behaviour as before
    try:
        ncvar.set_var_chunk_cache(size=int(size), nelems=max(1009, 4 * nchunks + 1), preemption=0.75)
    except:
        pass   # older netCDF-C / non-HDF5 file: keep library default


def ncclose(filename):
    """
    Close the cached handle of one file (if open).
    Must be called before a file is opened for writing ('w' or 'a').
    """
    key = _key(filename)
    nf = nchandles.pop(key, None)
    if nf is not None:
        try:
            nf.close()
        except:
            pass
    # chunk cache settings belong to the open file -> forget them
    for k in [k for k in ncstackvars if k[0] == key]:
        ncstackvars.discard(k)


def ncclose_all():
    """
    Close all cached input handles. Called at the end of a run and at the start
    of a new run (pytest, GUI, calibration run several models in one process).
    """
    for key in list(nchandles.keys()):
        nf = nchandles.pop(key)
        try:
            nf.close()
        except:
            pass
    ncstackvars.clear()


# -------------------------------------------------------------------------
# Excel
# -------------------------------------------------------------------------

def excelfile(filename):
    """
    Return an open pandas.ExcelFile; the workbook is opened only on first request.

    Uses the calamine reader if python-calamine is installed, otherwise openpyxl (as before).
    Errors for a missing file or a missing sheet are the same as with pd.read_excel.
    """
    key = _key(filename)
    xl = excelbooks.get(key)
    if xl is None:
        pd = importlib.import_module("pandas")   # pandas only loaded if Excel is used
        try:
            xl = pd.ExcelFile(filename, engine="calamine")
        except (ImportError, ValueError):
            # python-calamine not installed (ImportError) or pandas < 2.2 (ValueError)
            xl = pd.ExcelFile(filename, engine="openpyxl")
        excelbooks[key] = xl
    return xl


def readexcel(filename, sheet_name, header=0):
    """
    Read one sheet of an Excel workbook as DataFrame (replaces pd.read_excel).
    """
    return excelfile(filename).parse(sheet_name, header=header)


def excelsheetnames(filename):
    """
    List of sheet names of a workbook - without parsing any sheet.
    """
    return excelfile(filename).sheet_names


def excelclose_all():
    """
    Close all open workbooks (end of initialisation, start of a new run).
    """
    for key in list(excelbooks.keys()):
        xl = excelbooks.pop(key)
        try:
            xl.close()
        except:
            pass
