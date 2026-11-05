# -------------------------------------------------------------------------
# Name:        Data handling
# Purpose:     Transforming netcdf to numpy arrays, checking mask file
#
# Author:      PB
# Created:     13/07/2016 
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import difflib  # to check the closest word in settingsfile, if an error occurs
import glob
import math
import os
import re
import warnings

import numpy as np
from netCDF4 import Dataset, num2date, date2num, date2index
import rasterio

from . import globals
from cwatm.management_modules.checks import *
from cwatm.management_modules.dynamicModel import *
from cwatm.management_modules.messages import *
from cwatm.management_modules.replace_pcr import (npareatotal, npareaaverage, npareamaximum, npareamajority,
                                                  AreaIndex)
from cwatm.management_modules.timestep import *
from cwatm.management_modules.caching import ncopen, ncclose, ncclose_all, ncstackcache, ncappend, ncwriteclose, mapcoords, coordkey
from cwatm.management_modules.data_modflow import modflow_netcdf_grid, modflow_netcdf_variable
from cwatm.version import version_attributes


# output variable names from the settings file: a name, optionally with integer indices e.g. discharge or actualET[1]
_OUTVARNAME = re.compile(r"([A-Za-z_]\w*)((?:\[-?\d+\])*)")


def parseoutvar(name):
    """
    Split an output variable name from the settings file into the attribute name and the indices.

    Parameters
    ----------
    name : str
        Output variable name from the settings file e.g. 'discharge' or 'actualET[1]'

    Returns
    -------
    tuple
        (attribute name, tuple of integer indices) e.g. ('actualET', (1,)) or ('discharge', ())

    Notes
    -----
    Replaces the former eval of 'self.var.' + name: anything else than a name with integer indices (spaces, calls,
    attributes, expressions) gives an error, so no code from the settings file is run.
    """
    m = _OUTVARNAME.fullmatch(name)
    if m is None:
        msg = "Error 135: Output variable \"" + name + "\" is not a valid name\n"
        msg += "Allowed is a variable name, optionally with integer indices e.g. discharge or actualET[1]"
        raise CWATMError(msg)
    return m.group(1), tuple(int(i) for i in re.findall(r"-?\d+", m.group(2)))


def getoutvar(var, base, index):
    """
    Return var.<base>[i0][i1]... - the same object as the former eval of 'self.var.' + name returned.

    Parameters
    ----------
    var : object
        Model variable container (self.var)
    base : str
        Attribute name (from parseoutvar)
    index : tuple
        Integer indices (from parseoutvar)

    Returns
    -------
    object
        The model variable or the indexed part of it
    """
    value = getattr(var, base)
    for i in index:
        value = value[i]
    return value


# -------------------------------------
def valuecell(coordx, coordstr, returnmap=True):
    """
    Convert geographic coordinates to raster cell values for gauge placement.
    
    This function creates a raster map with numbered cells corresponding to
    gauge locations specified by coordinates. It performs coordinate validation,
    converts geographic coordinates to raster row/column indices, and creates
    a compressed array suitable for CWatM processing. Essential for linking
    point observations to the model grid.
    
    Parameters
    ----------
    coordx : list
        List of coordinate values in alternating x,y or lon/lat format.
        Even indices are x-coordinates, odd indices are y-coordinates.
    coordstr : str
        String representation of coordinates for error reporting.
    returnmap : bool, optional
        If True, return compressed 1D array. If False, return column/row indices.
        Default is True.
    
    Returns
    -------
    numpy.ndarray or tuple
        If returnmap=True: 1D compressed array with gauge numbers (1-based indexing).
        If returnmap=False: tuple of (column_indices, row_indices) lists.
    
    Raises
    ------
    CWATMError
        If coordinate strings cannot be converted to float values.
        If any coordinate falls outside the model domain (mask map bounds).
    
    Notes
    -----
    - Uses maskmapAttr global dictionary for spatial reference information
    - Coordinates outside domain trigger detailed error message with boundary box
    - Background cells are set to -9999 (NoData value)
    - Gauge cells are numbered sequentially starting from 1
    - Coordinate transformation uses inverse cell size for efficiency
    """

    coord = []
    col = []
    row = []
    for xy in coordx:
        try:
            coord.append(float(xy))
        except:
            msg = "Error 101: Gauges in settings file: " + xy + " in " + coordstr + " is not a coordinate"
            raise CWATMError(msg)



    null = np.zeros((maskmapAttr['row'], maskmapAttr['col']))
    null[null == 0] = -9999

    for i in range(int(len(coord) / 2)):
        # floor, not int(): int() truncates towards 0, so a gauge up to one cell outside the map would land in cell 0
        col.append(int(np.floor((coord[i * 2] - maskmapAttr['x']) * maskmapAttr['invcell'])))
        row.append(int(np.floor((maskmapAttr['y'] - coord[i * 2 + 1]) * maskmapAttr['invcell'])))

        if col[i] >= 0 and row[i] >= 0 and col[i] < maskmapAttr['col'] and row[i] < maskmapAttr['row']:
            null[row[i], col[i]] = i + 1
        else:
            x1 = maskmapAttr['x']
            x2 = x1 + maskmapAttr['cell'] * maskmapAttr['col']
            y1 = maskmapAttr['y']
            y2 = y1 - maskmapAttr['cell'] * maskmapAttr['row']
            box = "%5s %5.1f\n" % ("", y1)
            box += "%5s ---------\n" % ""
            box += "%5s |       |\n" % ""
            box += "%5.1f |       |%5.1f     <-- Box of mask map\n" % (x1, x2)
            box += "%5s |       |\n" % ""
            box += "%5s ---------\n" % ""
            box += "%5s %5.1f\n" % ("", y2)

            msg = "Error 102: Coordinates: x = " + str(coord[i * 2]) + '  y = ' + str(
                coord[i * 2 + 1]) + " of gauge is outside mask map\n\n"
            msg += box
            msg += "\nPlease have a look at \"MaskMap\" or \"Gauges\""
            raise CWATMError(msg)
    if returnmap:
        mapnp = compressArray(null).astype(np.int64)
        return mapnp
    else:
        return col, row


def readInflowCsv(filename):
    """
    Read an inflow file in the csv format of the CWatM time series output.

    Parameters
    ----------
    filename : str
        Path of the csv file: header lines, then "Date,G1,G2", then rows of "day/month/year,value,value".

    Returns
    -------
    tuple
        Column names (point number without the G), dates as (day, month, year), values [rows, columns]

    Raises
    ------
    CWATMFileError
        If the file is missing or does not have this format (Error 218).
    """

    try:
        with open(filename, "r") as file:
            lines = file.read().splitlines()
        start = [i for i, line in enumerate(lines) if line.startswith("Date,")][0]
        names = [name.strip().lstrip("G") for name in lines[start].split(",")[1:]]
        dates = []
        values = []
        for line in lines[start + 1:]:
            if line.strip():
                row = line.split(",")
                day, month, year = row[0].split("/")
                dates.append((int(day), int(month), int(year)))
                values.append([float(value) for value in row[1:]])
        values = np.array(values)
        if values.ndim != 2 or values.shape[1] != len(names):
            raise ValueError("number of values does not fit the header")
    except Exception:
        msg = "Error 218: Mistake reading inflow file\nIt has to be a csv file like the time series output of CWatM "
        msg += "(a line \"Date,G1,G2\", then rows \"day/month/year,value,value\")\n"
        raise CWATMFileError(filename, msg, sname="QInTS")
    return names, dates, values


def readInflowTss(filename):
    """
    Read an inflow file in the old tss format (PCRaster time series, written by CWatM before 2026-11-01).

    Parameters
    ----------
    filename : str
        Path of the tss file: a header line, the number of columns, "timestep", one line per column name,
        then rows of "timestep value value" separated by blanks.

    Returns
    -------
    tuple
        Column names, values [rows, columns]. The file has no dates: row 1 is the first day of the run.

    Raises
    ------
    CWATMFileError
        If the file does not have this format (Error 218).
    """

    try:
        with open(filename, "r") as file:
            lines = file.read().splitlines()
        no = int(lines[1]) - 1
        names = [name.strip() for name in lines[3:3 + no]]
        values = []
        for line in lines[3 + no:]:
            if line.strip():
                values.append([float(value) for value in line.split()[1:]])
        values = np.array(values)
        if no < 1 or values.ndim != 2 or values.shape[1] != len(names):
            raise ValueError("number of values does not fit the header")
    except Exception:
        msg = "Error 218: Mistake reading inflow file\nIt has to be a tss file (a header line, the number of columns, "
        msg += "\"timestep\", one line per column name, then rows \"timestep value value\")\n"
        raise CWATMFileError(filename, msg, sname="QInTS")
    return names, values


def readInflowFile(filename):
    """
    Read an inflow file: the csv file, or the old tss file if only this one exists.

    Parameters
    ----------
    filename : str
        Path of the inflow file. With the ending .csv or .tss, first name.csv is used and name.tss only if there is
        no csv file. Another ending is read as csv.

    Returns
    -------
    tuple
        Column names, dates as (day, month, year) or None for a tss file (no dates), values [rows, columns],
        name of the file which was read

    Raises
    ------
    CWATMFileError
        If no file is found or the file does not have the format (Error 218).
    """

    root, ext = os.path.splitext(filename)
    if ext.lower() in (".csv", ".tss"):
        found = [name for name in (root + ".csv", root + ".tss") if os.path.isfile(name)]
        if not found:
            msg = "Error 218: Inflow file not found, looked for: " + root + ".csv and " + root + ".tss\n"
            raise CWATMFileError(filename, msg, sname="QInTS")
        filename = found[0]
    if filename.lower().endswith(".tss"):
        names, values = readInflowTss(filename)
        return names, None, values, filename
    names, dates, values = readInflowCsv(filename)
    return names, dates, values, filename


def invcellsize(cell):
    """
    Inverse of the cell size.

    A cell size like 0.00833333 (coordinates in single precision or with few digits) belongs to a whole number
    of cells per unit (120), so the inverse is rounded. Other cell sizes (0.75, 0.3, 1.5, 0.4) are kept: rounding
    them would change the cell size.

    Parameters
    ----------
    cell : float
        Cell size

    Returns
    -------
    float
        Number of cells per unit of the coordinates
    """
    invcell = round(1 / cell, 0)
    if invcell > 0 and abs(1 / cell - invcell) <= 0.002 * invcell:
        return invcell
    return 1 / cell


def samecellsize(invcell1, invcell2):
    """
    Check if two maps have the same cell size. Cell sizes without a whole number of cells per unit (0.3, 0.4) are
    not rounded, and in a file with coordinates in single precision they are up to about 0.05 % off.

    Parameters
    ----------
    invcell1, invcell2 : float
        Inverse of the two cell sizes (see invcellsize)

    Returns
    -------
    bool
        True if the cell sizes are the same
    """
    return abs(invcell1 - invcell2) <= 0.0005 * abs(invcell2)


def setmaskmapAttr(x, y, col, row, cell):
    """
    Set global spatial reference attributes for the model domain.
    
    Defines the spatial reference system parameters that are used throughout
    CWatM for coordinate transformations, data alignment, and spatial operations.
    These attributes are stored in the global maskmapAttr dictionary and used
    by all spatial data processing functions.
    
    Parameters
    ----------
    x : float
        X-coordinate of the upper-left corner of the model domain.
        Typically longitude in decimal degrees or projected coordinate.
    y : float
        Y-coordinate of the upper-left corner of the model domain.
        Typically latitude in decimal degrees or projected coordinate.
    col : int
        Number of columns in the raster grid.
    row : int
        Number of rows in the raster grid.
    cell : float
        Cell size (spatial resolution) in the same units as x,y coordinates.
    
    Returns
    -------
    None
        Results stored in global maskmapAttr dictionary.
    
    Notes
    -----
    The function performs precision adjustments to handle floating-point
    arithmetic issues in coordinate calculations:
    - Calculates inverse cell size for efficient coordinate transformations
    - Rounds coordinates to appropriate precision based on magnitude
    - Handles edge cases where getgeotransform provides limited precision
    
    Global variables modified:
    - maskmapAttr: Dictionary with keys 'x', 'y', 'col', 'row', 'cell', 'invcell'
    
    This spatial reference is used by functions like valuecell(), loadmap(),
    and coordinate transformation routines throughout the model.
    """
    # getgeotransform only delivers single precision!
    invcell = invcellsize(cell)
    cell = 1 / invcell
    x = round(x, 6)
    y = round(y, 6)
    # This is still not ok! Some rounding issues still appear sometimes

    maskmapAttr['x'] = x
    maskmapAttr['y'] = y
    maskmapAttr['col'] = col
    maskmapAttr['row'] = row
    maskmapAttr['cell'] = cell
    maskmapAttr['invcell'] = invcell

def getvariablename(nf1):
    """
    get variable name of a netcdf file.
    If stored correctedly the variable name is the last one. But in case it is mixed up
    this function will pick the right name

    Parameters
    ----------
    netcdf file handler
    Return
    ------
    name: variable name
    """

    names = list(nf1.variables)
    others = [v for v in names if v not in ["X", "Y", "x", "y", "lon", "lat", "time", "crs"]]
    # the data has at least 2 dimensions; this leaves out grid mappings (spatial_ref, 0 dimensions)
    # and the bounds of the coordinates (lat_bnds, time_bnds), which are named in the bounds attribute of the coordinate
    bounds = [nf1.variables[v].getncattr('bounds') for v in names if 'bounds' in nf1.variables[v].ncattrs()]
    data = [v for v in others if nf1.variables[v].ndim >= 2 and v not in bounds and not v.endswith(("_bnds", "_bounds"))]
    if data:
        return data[-1]
    return others[-1] if others else names[0]

def loadsetclone(self, name):
    """
    Load the mask map that defines the model domain and set the spatial reference.

    The mask can be a NetCDF or GeoTIFF map, a rectangle (5 numbers) or a point (2 numbers; the
    catchment of this point is taken from the Ldd). Sets maskmapAttr, maskinfo and globals.inZero.

    Parameters
    ----------
    name : str
        Binding key of the mask map in the settings file.

    Returns
    -------
    numpy.ndarray or tuple
        Compressed mask. With a point and Flags['maskmap']: (mask2D, xleft, yup).

    Notes
    -----
    Must be called before any other spatial data operation.
    """
  
    filename = cbinding(name)
    coord = filename.split()

    if len(coord) == 2:
        name = "Ldd"

    if len(coord) == 5:
        # changed order of x, y i- in setclone y is first in CWATM
        # settings x is first
        # setclone row col cellsize xupleft yupleft
        # retancle: Number of Cols, Number of rows, cellsize, upper left corner X, upper left corner Y

        mapnp = np.ones((int(coord[1]), int(coord[0])))
        setmaskmapAttr(float(coord[3]),float(coord[4]), int(coord[0]),int(coord[1]),float(coord[2]))
        #mapnp[mapnp == 0] = 1
        #map = numpy2pcr(Boolean, mapnp, -9999)

    elif len(coord) < 3:

        filename = os.path.splitext(cbinding(name))[0] + '.nc'
        try:
            nf1 = ncopen(filename)

            value = getvariablename(nf1)
            
            # sometimes lat and lon gets mixed and lon is variable[0]
            lon_idx = next(i for i, v in enumerate(nf1.variables) if v in ("lon","x", "X"))
            lat_idx = next(i for i, v in enumerate(nf1.variables) if v in ("lat", "y", "Y"))

            x1 = list(nf1.variables.values())[lon_idx][0]
            x2 = list(nf1.variables.values())[lon_idx][1]
            xlast = list(nf1.variables.values())[lon_idx][-1]

            y1 = list(nf1.variables.values())[lat_idx][0]
            ylast = list(nf1.variables.values())[lat_idx][-1]

            # swap to make y1 the biggest number
            turn_latitude = y1 < ylast
            if turn_latitude:  y1, ylast = ylast, y1

            cellSize = np.abs(x2 - x1)
            invcell = invcellsize(cellSize)
            nrRows = int(0.5 + np.abs(ylast - y1) * invcell + 1)
            nrCols = int(0.5 + np.abs(xlast - x1) * invcell + 1)
            x = x1 - cellSize / 2
            y = y1 + cellSize / 2

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                # missing values in the file are not part of the mask
                mapnp = np.ma.filled(nf1.variables[value][0:nrRows, 0:nrCols], 0)
                mapnp[np.isnan(mapnp) | (np.abs(mapnp) > 1e15) | (mapnp == -9999)] = 0
            if turn_latitude:
                mapnp = np.flipud(mapnp)
            setmaskmapAttr( x, y, nrCols, nrRows, cellSize)

        except:
            # load geotiff
            try:

                filename = cbinding(name)
                with rasterio.open(filename) as nf2:
                    t = nf2.transform
                    geotransform = (t.a, t.b, t.c, t.d, t.e, t.f)

                    setmaskmapAttr(geotransform[2], geotransform[5], nf2.shape[1], nf2.shape[0], geotransform[0])
                    mapnp = nf2.read(1)
                # 10 because that includes all valid LDD values [1-9]
                mapnp[mapnp > 10] = 0
                mapnp[mapnp < -10] = 0
                addtoversiondate(filename)

            except:
                raise CWATMFileError(filename,msg = "Error 201: File reading Error\n", sname=name)

    else:
        msg = "Error 103: Maskmap: " + filename + " is not a valid mask map nor valid coordinates nor valid point\n"
        msg +="Or there is a whitespace or undefined character in Maskmap"
        raise CWATMError(msg)



    # put in the ldd map
    # if there is no ldd at a cell, this cell should be excluded from modelling

    # missing values in Ldd (netcdf mask, tif nodata, NaN) are no ldd
    maskldd = np.nan_to_num(np.ma.filled(loadmap('Ldd', compress = False, masked = True), 0))
    maskarea = np.bool_(mapnp)
    mask = np.logical_not(np.logical_and(maskldd,maskarea))

#    mask=np.isnan(mapnp)
#    mask[mapnp==0] = True # all 0 become mask out
    mapC = np.ma.compressed(np.ma.masked_array(mask,mask))

    # Definition of compressed array and info how to blow it up again
    maskinfo['mask']=mask
    maskinfo['shape']=mask.shape
    maskinfo['maskflat']=mask.ravel()    # map to 1D not compresses
    maskinfo['shapeflat']=maskinfo['maskflat'].shape   #length of the 1D array
    maskinfo['mapC']=mapC.shape                        # length of the compressed 1D array
    maskinfo['maskall'] =np.ma.masked_all(maskinfo['shapeflat'])  # empty map 1D but with mask
    maskinfo['maskall'].mask = maskinfo['maskflat']

    globals.inZero=np.zeros(maskinfo['mapC'])

    outpoints = 0
    if len(coord) == 2:
       outpoints = valuecell(coord, filename)
       outpoints[outpoints < 0] = 0
       print("Create catchment from point and river network")
       ldd = compressArray(mapnp)
       mask2D, xleft, yup = self.routing_kinematic_module.catchment(outpoints,ldd)
       mapC = maskfrompoint(mask2D, xleft, yup) + 1

       if Flags['check']:
           checkmap("MaskMap", "", ~mask2D)
           ldd = loadmap('Ldd')
       # load area to print out basin area
       area = np.sum(loadmap('CellArea')) * 1e-6
       print("Number of cells in catchment: %6i = %7.0f km2" % (np.sum(mask2D), area))
       if Flags['maskmap']:
           return mask2D, xleft, yup

    else:
        if Flags['check']:
            checkmap("Mask+Ldd", "", ~mask)
            checkmap(name, filename, mapnp)
            checkmap("Ldd", cbinding("Ldd"), maskldd)




    # if the final results map should be cover up with some mask:
    if "coverresult" in binding:
        coverresult[0] = returnBool('coverresult')
        if coverresult[0]:
            cover = loadmap('covermap', compress=False, cut = False)
            cover[cover > 1] = False
            cover[cover == 1] = True
            coverresult[1] = cover
    else:
        coverresult[0] = False
        coverresult[1] = []


    return mapC


def maskfrompoint(mask2D, xleft, yup):
    """
    Set a 2D mask of a catchment (found from a point) as the new model domain.

    Moves maskmapAttr to the rectangle of the catchment and sets maskinfo and globals.inZero.

    Parameters
    ----------
    mask2D : numpy.ndarray
        2D array of the new mask, != 0 for active cells.
    xleft : int
        Column of the left edge of mask2D; -1: the point has no valid value in the Ldd (Error 104).
    yup : int
        Row of the upper edge of mask2D.

    Returns
    -------
    numpy.ndarray
        1D compressed mask.
    """

    if xleft == -1:
        msg = "Error 104: MaskMap point does not have a valid value in the river network (LDD)"
        raise CWATMError(msg)

    x = xleft * maskmapAttr['cell'] + maskmapAttr['x']
    y = maskmapAttr['y'] - yup * maskmapAttr['cell']

    maskmapAttr['x'] = x
    maskmapAttr['y'] = y
    maskmapAttr['col'] = mask2D.shape[1]
    maskmapAttr['row'] = mask2D.shape[0]

    mask = np.invert(np.bool_(mask2D))
    mapC = np.ma.compressed(np.ma.masked_array(mask, mask))

    # Definition of compressed array and info how to blow it up again
    maskinfo['mask'] = mask
    maskinfo['shape'] = mask.shape
    maskinfo['maskflat'] = mask.ravel()  # map to 1D not compresses
    maskinfo['shapeflat'] = maskinfo['maskflat'].shape  # length of the 1D array
    maskinfo['mapC'] = mapC.shape  # length of the compressed 1D array
    maskinfo['maskall'] = np.ma.masked_all(maskinfo['shapeflat'])  # empty map 1D but with mask
    maskinfo['maskall'].mask = maskinfo['maskflat']

    globals.inZero = np.zeros(maskinfo['mapC'])
    return mapC

def addtoversiondate(filename,history=""):
    """
    Add name and date of an input file to versioning['input'] (each file only once).

    This list goes into the attribute version_inputfiles of discharge and evaporation output maps.

    Parameters
    ----------
    filename : str
        Input file.
    history : str, optional
        Attribute history of a netCDF file: its date is used. If there is none, the creation
        date of the file is used. Default is empty string.
    """

    # each file only once: no second date lookup on disk (slow on network drives) and no double entry
    inputdates = versioning.setdefault('inputdates', {})
    if filename in inputdates:
        return

    if history !="":
        try:
            timestamp = re.search(r'\w{3} \w{3} \d{1,2} \d{2}:\d{2}:\d{2} \d{4}', history)
            date1 = datetime.datetime.strptime(timestamp.group(), '%a %b %d %H:%M:%S %Y')
        except:
            date1 = datetime.datetime.fromtimestamp(os.path.getctime(filename))
    else:
        date1 = datetime.datetime.fromtimestamp(os.path.getctime(filename))
    add = os.path.basename(filename) +" "+ date1.strftime('%d/%m/%Y %H:%M')+';'
    versioning['input'] += add
    inputdates[filename] = add


def loadcrs (name):
    """
    load crs projection to be compliant with netcdf cdf1.13
    name : str
        Configuration binding key or file path for the data to load.
    :return: projection as crs
    """

    value =  cbinding(name)
    filename = os.path.splitext(value)[0] + '.nc'
    crs = None
    try:
        nf1 = ncopen(filename)
        crs = nf1.variables["crs"]
        #nf1.close()
    except:
        # no warning - is a bit annoying
        #msg = "\nWarning: Projection not defined as crs variable in: " + filename + "\n"
        #print(msg)
        pass
    return crs


def loadmap(name, lddflag=False,compress = True, local = False, cut = True, masked = False):
    """
    Load spatial data from various file formats into CWatM arrays.
    
    Universal data loading function that handles NetCDF, GeoTIFF, and other
    raster formats. Performs coordinate checking, data validation, format
    conversion, and optional compression. This is the primary interface for
    loading static spatial data (parameters, initial conditions) in CWatM.
    
    Parameters
    ----------
    name : str
        Configuration binding key or file path for the data to load.
    lddflag : bool, optional
        If True, treat as Local Drain Direction data with special handling.
        Default is False.
    compress : bool, optional
        If True, return data in compressed 1D format. If False, return 2D array.
        Default is True.
    local : bool, optional
        If True, load data relative to local directory. Default is False.
    cut : bool, optional
        If True, clip data to model domain. Default is True.
    masked : bool, optional
        If True, a tif read with compress=False has its nodata cells masked. Default is False.

    Returns
    -------
    numpy.ndarray
        Loaded spatial data, either as 2D array or compressed 1D format.
    
    Raises
    ------
    CWATMFileError
        If file cannot be found or read.
    CWATMError
        If spatial dimensions don't match the model domain.
        If coordinate systems are incompatible.
    
    Notes
    -----
    - Automatically detects file format (NetCDF vs GeoTIFF)
    - Performs spatial consistency checks against clone map
    - Handles coordinate system transformations
    - Supports both static parameters and time-varying data
    - LDD flag enables special processing for flow direction data
    """

    value = cbinding(name)
    filename = value
    mapC = 0  # initializing to prevent warning in code inspection

    try:  # loading an integer or float but not a map
        mapC = float(value)
        load = True
        if Flags['check']:
            checkmap(name, filename, mapC)
    except ValueError:
        load = False


    if not load:   # read a netcdf  (single one not a stack)
        filename = os.path.splitext(value)[0] + '.nc'
         # get mapextend of netcdf map and calculate the cutting
        #cut0, cut1, cut2, cut3 = mapattrNetCDF(filename)

        try:
            nf1 = ncopen(filename)   # cached: same handle as used by mapattrNetCDF/readCoord
            cut0, cut1, cut2, cut3 = mapattrNetCDF(filename, cover = cut)

            # load netcdf map but only the rectangle needed
            value = getvariablename(nf1)

            #if (nf1.variables[maskmapAttr['coordy']][0] - nf1.variables[maskmapAttr['coordy']][-1]) < 0:
            if (nf1.variables[maskmapAttr['coordy']][0] - nf1.variables[maskmapAttr['coordy']][-1]) < 0:
                msg = "Error 202: Latitude is in wrong order\n"
                raise CWATMFileError(filename, msg)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                # in order to ignore some invalid value comments
                if cut:
                    mapnp = nf1.variables[value][cut2:cut3, cut0:cut1].astype(np.float64)
                else:
                    mapnp = nf1.variables[value][:]

            try:
                history = nf1.getncattr('history')
            except:
                history = ""
            addtoversiondate(filename,history)

        except Exception as ncerror:

            filename = cbinding(name)
            try:
                with rasterio.open(filename) as nf2:
                    # masked: nodata cells are missing values as in a netcdf map (compressArray); compress=False: values as in the file
                    # float64 for all data types of a tif, as for a netcdf map
                    mapnp = nf2.read(1, masked=compress or masked).astype(np.float64)

                    # if local no cut
                    if not local:
                        if cut:
                            cut0, cut1, cut2, cut3 = mapattrTiff(nf2)
                            mapnp = mapnp[cut2:cut3, cut0:cut1]
                addtoversiondate(filename)
            except CWATMError:
                # e.g. Error 108: cell size of the map is different
                raise
            except Exception:
                if isinstance(ncerror, CWATMError):
                    # netcdf found but wrong (e.g. Error 202, 107) and not readable by rasterio either
                    raise ncerror
                msg = "Error 203: File does not exists"
                raise CWATMFileError(filename,msg,sname=name)

        if compress:
            mapC = compressArray(mapnp,name=filename)
            if Flags['check']:
                checkmap(name, filename, np.ma.masked_array(mapnp, maskinfo['mask']))
        else:
            mapC = mapnp
            if Flags['check'] and not(name == "Ldd"):
                checkmap(name, filename, mapnp)


    return mapC


def loadmapYearly(name, date, value='None'):
    """
    Load a map which is either a single map or a netCDF stack with one map per year.

    A single map is a number, a GeoTIFF or a netCDF without time; a stack is a netCDF whose variable has a time
    dimension. The stack is found from the file (not from an error of loadmap: loadmap does not fail on a stack).

    Parameters
    ----------
    name : str
        settings key of the map
    date : datetime.datetime
        date of the year to read from a stack
    value : str, optional
        variable name in a stack, default 'None': found by getvariablename

    Returns
    -------
    map : numpy.ndarray or float
        the map (of this year, if a stack)
    stack : bool
        True if a stack: the caller reads it again every new year
    """
    filename = cbinding(name)
    stack = False
    if os.path.splitext(filename)[1].lower() == '.nc' and os.path.isfile(filename):
        nf1 = ncopen(filename)
        var = getvariablename(nf1) if value == 'None' else value
        if var not in nf1.variables:
            msg = "Error 177: variable " + var + " is not in the netCDF file\n"
            raise CWATMFileError(filename, msg, sname=name)
        stack = 'time' in nf1.variables[var].dimensions
    if stack:
        return readnetcdf2(name, date, 'yearly', value=value), True
    return loadmap(name), False


# -----------------------------------------------------------------------
# Compressing to 1-dimensional numpy array
# -----------------------------------------------------------------------

def compressArray(map, name="None", zeros = 0.):
    """
    Compress 2D array to 1D format by removing inactive cells.

    Core data compression function that converts full 2D spatial arrays
    to the efficient 1D compressed format used throughout CWatM.

    Parameters
    ----------
    map : numpy.ndarray
        2D spatial array to be compressed.
    name : str, optional
        File name for error messages. Not "None": NaN inside the mask gives a warning.
    zeros : float, optional
        Value for missing values of the file (masked cells). Default is 0.0.

    Returns
    -------
    numpy.ndarray
        1D compressed array containing only active model cells.

    Notes
    -----
    - Uses global maskinfo for determining active cells
    - All hydrological calculations use this compressed format
    """

    if map.shape != maskinfo['mask'].shape:
        msg = "Error 105: " + name + " has a different shape than area or ldd \n"
        raise CWATMError(msg)
    
    # missing values of the file (its own mask) get the value of zeros
    mapnp1 = np.ma.masked_array(np.ma.filled(map, zeros), maskinfo['mask'])
    mapC = np.ma.compressed(mapnp1)
    # if fill: mapC[np.isnan(mapC)]=0
    if name != "None":
        if np.max(np.isnan(mapC)):
            msg = "Error 106: " + name + " has NaN at " + str(np.count_nonzero(np.isnan(mapC))) + " cells inside the mask map \n"
            raise CWATMError(msg)
    # if a value is 1e20 or -1e20 or beyond than the standard value is taken
    mapC[mapC >= 1.E20] = zeros
    mapC[mapC <= -1.E20] = zeros

    return mapC

def decompress(map):
    """
    Expand compressed 1D array back to full 2D spatial format.
    
    Inverse operation of compressArray, converting CWatM's internal 1D
    compressed format back to full 2D spatial arrays for output, visualization,
    or interface with external tools. Inactive cells are filled with NoData values.
    
    Parameters
    ----------
    map : numpy.ndarray
        1D compressed array from CWatM internal processing.
    
    Returns
    -------
    numpy.ndarray
        2D spatial array with full model domain dimensions.
    
    Notes
    -----
    - Uses global maskinfo and maskmapAttr for spatial reconstruction
    - Inactive cells filled with -9999 (NoData value)
    - Preserves spatial relationships and coordinate system
    - Required for creating output files and maps
    - Inverse operation of compressArray function
    """

    # dmap=np.ma.masked_all(maskinfo['shapeflat'], dtype=map.dtype)
    dmap = maskinfo['maskall'].copy()
    dmap[~maskinfo['maskflat']] = map[:]
    dmap = dmap.reshape(maskinfo['shape'])

    # check if integer map (like outlets, lakes etc
    try:
        checkint = str(map.dtype)
    except:
        checkint = "x"
    if checkint == "int8":
        dmap[dmap < 0] = 0
    else:
        dmap[dmap.mask] = -9999

    return dmap




# -----------------------------------------------------------------------
# NETCDF
# -----------------------------------------------------------------------

def getmeta(key, varname, alternative):
    """
    Retrieve metadata attributes for NetCDF variable creation.
    
    Looks up variable metadata from the global metaNetcdfVar dictionary
    to ensure proper CF-compliant attributes in output NetCDF files.
    Provides fallback values when specific metadata is not available.
    
    Parameters
    ----------
    key : str
        Metadata attribute key (e.g., 'unit', 'long_name', 'standard_name').
    varname : str
        Variable name to look up in metadata dictionary.
    alternative : str
        Default value to use if metadata not found for the variable.
    
    Returns
    -------
    str
        Metadata value for the specified key and variable.
    
    Notes
    -----
    - Searches global metaNetcdfVar dictionary populated from XML metadata
    - Ensures consistent metadata across all model outputs
    - Supports CF convention compliance for scientific data exchange
    - Falls back to sensible defaults when specific metadata unavailable
    """

    ret = alternative
    if varname in metaNetcdfVar:
        if key in metaNetcdfVar[varname]:
            ret = metaNetcdfVar[varname][key]
    return ret


def metaNetCDF():
    """
    Get the attributes of all variables of the first precipitation map (metadataNCDF).

    They give the names and attributes of the coordinates in output files.
    """

    try:
        name = cbinding('PrecipitationMaps')
        name1 = glob.glob(os.path.normpath(name))[0]
        nf1 = ncopen(name1)
        for var in nf1.variables:
           metadataNCDF[var] =  {k: v for k, v in nf1.variables[var].__dict__.items() if k != '_FillValue'}
    except:
        msg = "Error 204: Trying to get metadata from netcdf\n"
        raise CWATMFileError(cbinding('PrecipitationMaps'),msg)


def readCoord(name):
    """
    Read the coordinates of a map: netCDF if a .nc file of this name exists, otherwise GeoTIFF.

    Parameters
    ----------
    name : str
        Path to the map.

    Returns
    -------
    tuple
        lat, lon, cell, invcell, rows, cols.
    """

    # a GeoTIFF was already read: no need to try the netCDF file again
    key = coordkey(name)
    if key in mapcoords:
        return mapcoords[key]

    namenc = os.path.splitext(name)[0] + '.nc'

    try:
        nf1 = ncopen(namenc)   # cached: later calls for the same file cost nothing
        nc = True
    except:
        nc = False
    if nc:
        lat, lon, cell, invcell, rows, cols = readCoordNetCDF(namenc)
    else:
        with rasterio.open(name) as raster:
            gt = raster.transform
            rows = raster.shape[0]
            cols = raster.shape[1]

        cell = gt[0]
        invcell = invcellsize(cell)

        # getgeotransform only delivers single precision!
        cell = 1 / invcell
        lon = gt[2]
        lat = gt[5]
        #lon = 1 / round(1 / (x1 - int(x1)), 4) + int(x1)
        #lat = 1 / round(1 / (y1 - int(y1)), 4) + int(y1)
        mapcoords[key] = lat, lon, cell, invcell, rows, cols

    return lat, lon, cell, invcell, rows, cols

def readCoordNetCDF(name,check = True):
    """
    Read coordinate system information from NetCDF files.
    
    Specialized function for extracting spatial reference information
    from NetCDF files, including dimension sizes, coordinate variables,
    and geospatial metadata. Handles both CF-compliant and legacy NetCDF
    spatial conventions.
    
    Parameters
    ----------
    name : str
        Path to NetCDF file or configuration binding key.
    check : bool, optional
        If True, perform spatial consistency checks. Default is True.
    
    Returns
    -------
    tuple
        Spatial reference information including dimensions, coordinates,
        and transformation parameters.
    
    Notes
    -----
    - Handles various NetCDF coordinate conventions
    - Supports both regular and irregular grids
    - Performs coordinate system validation when check=True
    - Essential for proper NetCDF data integration
    """

    if check:
        try:
            nf1 = ncopen(name)
        except:
            msg = "Error 205: Checking netcdf map \n"
            raise CWATMFileError(name,msg)
    else:
        # if subroutine is called already from inside a try command
        nf1 = ncopen(name)

    if not('coordx' in maskmapAttr.keys()):
        if 'lon' in nf1.variables.keys():
            maskmapAttr['coordx'] = 'lon'
            maskmapAttr['coordy'] = 'lat'
        else:
            maskmapAttr['coordx'] = 'x'
            maskmapAttr['coordy'] = 'y'

    if 'X' in nf1.variables.keys():
        maskmapAttr['coordx'] = 'X'
        maskmapAttr['coordy'] = 'Y'
    if 'x' in nf1.variables.keys():
        maskmapAttr['coordx'] = 'x'
        maskmapAttr['coordy'] = 'y'

    # the lines above run on every call because they set maskmapAttr; the file is read only once per coordinate name
    key = coordkey(name, maskmapAttr['coordx'], maskmapAttr['coordy'])
    if key in mapcoords:
        return mapcoords[key]

    rows = nf1.variables[maskmapAttr['coordy']].shape[0]
    cols = nf1.variables[maskmapAttr['coordx']].shape[0]

    lon0 = nf1.variables[maskmapAttr['coordx']][0]
    try:
        lon1 = nf1.variables[maskmapAttr['coordx']][1]
    except:
        # precipitation map has only 1 cell, because there is no information available -> assuming 6 times
        lon0 = lon0.data
        lon1 = lon0 + 6 * maskmapAttr['cell']
    lat0 = nf1.variables[maskmapAttr['coordy']][0]
    latlast = nf1.variables[maskmapAttr['coordy']][-1]
    # swap to make lat0 the biggest number
    if lat0 < latlast:
        lat0, latlast = latlast, lat0

    cell = round(np.abs(lon1 - lon0),8)
    invcell = invcellsize(cell)

    lon = round(lon0 - cell / 2,8)
    lat = round(lat0 + cell / 2,8)

    mapcoords[key] = lat, lon, cell, invcell, rows, cols
    return lat,lon, cell,invcell,rows,cols

def readCalendar(name):
    """
    Set dateVar['calendar'] to the calendar of the time variable of a NetCDF file.

    Parameters
    ----------
    name : str
        Path to the NetCDF file.
    """
    nf1 = ncopen(name)
    dateVar['calendar'] = nf1.variables['time'].calendar

def checkMeteo_Wordclim(meteodata, wordclimdata):
    """
    Check if a meteo map and a WorldClim map cover the same extent (each edge within 0.00001).

    Only the coordinates are compared, not the values.

    Parameters
    ----------
    meteodata : str
        Path to the meteo map.
    wordclimdata : str
        Path to the WorldClim map.

    Returns
    -------
    bool
        True if the extents are the same.
    """

    try:
        nf1 = ncopen(meteodata)
    except:
        msg = "Error 206: Checking netcdf map \n"
        raise CWATMFileError(meteodata, msg)

    if 'lon' in list(nf1.variables.keys()):
        xy = ["lon", "lat"]
    else:
        xy = ["x", "y"]

    lonM0 = nf1.variables[xy[0]][0]
    if nf1.variables[xy[0]].shape[0] == 1:
        # if shape is only1 then there is no information about the cell -> we assume 6 times bigger
        lon1 = lonM0 + maskmapAttr['cell'] * 6.
    else:
        lon1 = nf1.variables[xy[0]][1]

    cellM = round(np.abs(lon1 - lonM0) / 2.,8)
    lonM0 = round(lonM0 - cellM,8)

    lonM1 = round(nf1.variables[xy[0]][-1] + cellM,8)
    latM0 = nf1.variables[xy[1]][0]
    latM1 = nf1.variables[xy[1]][-1]

    # swap to make lat0 the biggest number
    if latM0 < latM1:
        latM0, latM1 = latM1, latM0
    latM0 = round(latM0 + cellM,8)
    latM1 = round(latM1 - cellM,8)

    # load Wordclima data
    try:
        nf1 = ncopen(wordclimdata)
    except:
        msg = "Error 207: Checking netcdf map \n"
        raise CWATMFileError(wordclimdata, msg)

    lonW0 = nf1.variables[xy[0]][0]
    lon1 = nf1.variables[xy[0]][1]
    cellW = round(np.abs(lon1 - lonW0) / 2.,8)
    lonW0 = round(lonW0 - cellW,8)
    lonW1 = round(nf1.variables[xy[0]][-1] + cellW,8)


    latW0 = nf1.variables[xy[1]][0]
    latW1 = nf1.variables[xy[1]][-1]
    # swap to make lat0 the biggest number
    if latW0 < latW1:
        latW0, latW1 = latW1, latW0
    latW0 = round(latW0 + cellW,8)
    latW1 = round(latW1 - cellW,8)
    # calculate the controll variable: each edge on its own, in a sum a shift east and a shift south cancel out
    contr = max(abs(round(lonM0 - lonW0,5)), abs(round(lonM1 - lonW1,5)), abs(round(latM0 - latW0,5)), abs(round(latM1 - latW1,5)))

    check = True
    if contr > 0.00001:
        #msg = "Data from meteo dataset and Wordclim dataset does not match"
        #raise CWATMError(msg)
        check  = False

    return check

def checkmapcover(name, dx, dy, aligned=True):
    """
    Check if a map can be cut for the mask map: it has to reach the west and north edge of the mask
    and (if it has the resolution of the mask) it has to be on the same grid.
    A map which ends before the east or south edge gets Error 105 in compressArray.

    Parameters
    ----------
    name : str
        Name of the map (for the error message)
    dx, dy : float
        Number of cells from the west / north edge of the map to the west / north edge of the mask.
        Negative: the map starts inside the mask.
    aligned : bool, optional
        False: only the coverage is checked (meteo maps can have a coarser resolution). Default is True.
    """
    tolerance = 0.1   # part of a cell: coordinates are stored with a limited precision
    if dx < -tolerance or dy < -tolerance:
        msg = "Error 154: Map does not cover the mask map: " + name + "\n"
        msg += "Number of cells from the map edge to the mask edge (has to be 0 or more): west: %.1f north: %.1f\n" % (dx, dy)
        raise CWATMError(msg)
    if aligned and (abs(dx - round(dx)) > tolerance or abs(dy - round(dy)) > tolerance):
        msg = "Error 155: Map is not on the same grid as the mask map: " + name + "\n"
        msg += "Number of cells from the map edge to the mask edge (has to be a whole number): west: %.2f north: %.2f\n" % (dx, dy)
        raise CWATMError(msg)


def mapattrNetCDF(name, cover=True):
    """
    Calculate which part of a NetCDF map fits to the mask map.

    Parameters
    ----------
    name : str
        Path to the NetCDF file.
    cover : bool, optional
        True: Error 154/155 if the map does not cover the mask (checkmapcover). Default is True.

    Returns
    -------
    tuple
        cut0, cut1, cut2, cut3: first and last + 1 column, first and last + 1 row.
    """

    lat, lon, cell, invcell, rows, cols = readCoord(name)

    if not samecellsize(maskmapAttr['invcell'], invcell):
        msg = "Error 107: Cell size different in maskmap: " + \
            binding['MaskMap'] + " and: " + name
        raise CWATMError(msg)

    xx = maskmapAttr['x']
    yy = maskmapAttr['y']
    if cover:
        checkmapcover(name, (xx - lon) * invcell, (lat - yy) * invcell)
    #cut0 = int(0.0001 + np.abs(xx - lon) * invcell) # argmin() ??
    #cut2 = int(0.0001 + np.abs(yy - lat) * invcell) #
    cut0 = int(np.abs(xx + maskmapAttr['cell']/2 - lon) * invcell) # argmin() ??
    cut2 = int(np.abs(yy - maskmapAttr['cell']/2 - lat) * invcell) #


    cut1 = cut0 + maskmapAttr['col']
    cut3 = cut2 + maskmapAttr['row']

    # for glacier use the standard cut, if the meteo maps have a different scaling
    if not('cut' in maskmapAttr.keys()):
        maskmapAttr['cut'] = [cut2,cut3,cut0,cut1]

    return cut0, cut1, cut2, cut3

def mapattrNetCDFMeteo(name, check = True):
    """
    Extract spatial attributes specifically for meteorological NetCDF files.
    
    Specialized version of mapattrNetCDF optimized for meteorological data
    files, which often have specific conventions and temporal dimensions.
    Handles time-series data with proper temporal coordinate processing.
    
    Parameters
    ----------
    name : str
        Path to meteorological NetCDF file or configuration binding key.
    check : bool, optional
        If True, validate spatial and temporal consistency. Default is True.
    
    Returns
    -------
    dict
        Spatial and temporal attribute dictionary for meteorological data.
    
    Notes
    -----
    - Optimized for time-series meteorological data
    - Handles temporal dimension metadata
    - Supports various meteorological data conventions
    - Essential for proper forcing data integration
    """

    lat, lon, cell, invcell, rows, cols = readCoordNetCDF(name, check)

    # x0,xend, y0,yend - borders of fine resolution map
    lon0 = maskmapAttr['x']
    lat0 = maskmapAttr['y']
    lonend = lon0 + maskmapAttr['col'] / maskmapAttr['invcell']
    latend = lat0 - maskmapAttr['row'] / maskmapAttr['invcell']

    checkmapcover(name, (lon0 - lon) * invcell, (lat - lat0) * invcell, aligned=False)

    # cut for 0.5 deg map based on finer resolution

    # lats = nc_simulated.variables['lat'][:]
    # in_lat = discharge_location[1]
    # lat_idx = geo_idx(in_lat, lats)
    # geo_idx = (np.abs(dd_array - dd)).argmin()
    # geo_idx(dd, dd_array):

    cut0 = int(0.01 + np.abs(lon0 - lon) * invcell)
    cut2 = int(0.01 + np.abs(lat0 - lat) * invcell)

    # lon and lat of coarse meteo dataset
    lonCoarse = (cut0 * cell) + lon
    latCoarse = lat - (cut2 * cell)
    cut4 = int(0.01 + np.abs(lon0 - lonCoarse) * maskmapAttr['invcell'])
    cut5 = cut4 + maskmapAttr['col']
    cut6 = int(0.01 + np.abs(lat0 - latCoarse) * maskmapAttr['invcell'])
    cut7 = cut6 + maskmapAttr['row']

    # now coarser cut of the coarse meteo dataset
    cut1 = int(0.01 + np.abs(lonend - lon) * invcell)
    cut3 = int(0.01 + np.abs(latend - lat) * invcell)

    # test if fine cut is inside coarse cut
    cellx = (cut1 - cut0) * maskmapAttr['reso_mask_meteo']
    celly = (cut3 - cut2) * maskmapAttr['reso_mask_meteo']

    if cellx < cut5:
        cut1 += 1
    if celly < cut7:
        cut3 += 1

    if maskmapAttr['coordy'] == 'lat':
        if cut1 > (360 * invcell): cut1 = int(360 * invcell)
        if cut3 > (180 * invcell): cut3 = int(180 * invcell)



    return cut0, cut1, cut2, cut3, cut4, cut5, cut6, cut7



def mapattrTiff(nf2):
    """
    Calculate which part of a GeoTIFF map fits to the mask map.

    Parameters
    ----------
    nf2 : rasterio.DatasetReader
        Opened GeoTIFF file.

    Returns
    -------
    tuple
        cut0, cut1, cut2, cut3: first and last + 1 column, first and last + 1 row.
    """

    t = nf2.transform
    geotransform = (t.a, t.b, t.c, t.d, t.e, t.f)

    x1 = geotransform[2]
    y1 = geotransform[5]
    cellSize = geotransform[0]

    invcell = invcellsize(cellSize)

    # getgeotransform only delivers single precision!
    cellSize = 1 / invcell
    if (x1-int(x1)) != 0:
        x1 = 1/round(1/(x1-int(x1)),4) + int(x1)
    if (y1-int(y1)) != 0:
        y1 = 1 / round(1 / (y1 - int(y1)), 4) + int(y1)

    if not samecellsize(maskmapAttr['invcell'], invcell):
        msg = "Error 108: Cell size different in maskmap: " + \
            binding['MaskMap']
        raise CWATMError(msg)


    checkmapcover(nf2.name, (maskmapAttr['x'] - x1) * invcell, (y1 - maskmapAttr['y']) * invcell)

    x = x1 - cellSize / 2
    y = y1 + cellSize / 2
    cut0 = int(0.01 + np.abs(maskmapAttr['x'] - x) * invcell)
    cut2 = int(0.01 + np.abs(maskmapAttr['y'] - y) * invcell)

    cut1 = cut0 + maskmapAttr['col']
    cut3 = cut2 + maskmapAttr['row']

    return cut0, cut1, cut2, cut3


def regularZones(inner):
    """
    Zones of a regular grid of inner x inner cells, numbered over the whole Ldd map and cut to the mask map.

    Used for the zonal abstraction of water_demand (allocation_area). The grid starts at the upper left corner
    of the Ldd map (netCDF, GeoTIFF or PCRaster .map with the same name), so the zones do not depend on the mask.

    Parameters
    ----------
    inner : int
        Size of a zone in cells (inner x inner).

    Returns
    -------
    numpy.ndarray
        Compressed zone number of each cell (int, zone 0 is a zone).
    """
    _, _, _, _, rows, cols = readCoord(cbinding('Ldd'))
    base = os.path.splitext(cbinding('Ldd'))[0]
    if os.path.isfile(base + '.nc'):
        cut0, cut1, cut2, cut3 = mapattrNetCDF(base + '.nc')
    else:
        filename = base + '.tif'
        if not os.path.isfile(filename):
            filename = base + '.map'
        with rasterio.open(filename) as nf2:   # before 2026-11 opened in water_demand.py and never closed
            cut0, cut1, cut2, cut3 = mapattrTiff(nf2)

    # make the grid as big that it can be divided through inner (one zone row/column more than needed if it can
    # be divided already - harmless), then cut to the mask map
    cols1 = (cols // inner + 1) * inner
    rows1 = (rows // inner + 1) * inner
    arr = np.kron(np.arange(rows1 // inner * cols1 // inner).reshape((rows1 // inner, cols1 // inner)),
                  np.ones((inner, inner)))
    arr = arr[cut2:cut3, cut0:cut1].astype(int)
    return compressArray(arr, name="array")


def multinetdf(meteomaps, startcheck = 'dateBegin'):
    """
    Set up multiple NetCDF meteorological files for efficient reading.
    
    Initializes data structures and index mappings for reading from
    multiple meteorological NetCDF files. Optimizes data access patterns
    during long model runs.
    
    Parameters
    ----------
    meteomaps : list
        List of meteorological variable names to process.
    startcheck : str, optional
        Date key to use for temporal validation. Default is 'dateBegin'.
    
    Returns
    -------
    None
        Sets up global data structures for efficient meteorological
        data access.
    
    Notes
    -----
    - Optimizes I/O patterns for multiple meteorological files
    - Handles temporal indexing across file boundaries
    - Critical for efficient forcing data processing
    """

    end = dateVar['dateEnd']

    no = 0
    for maps in meteomaps:
        name = cbinding(maps)
        nameall = glob.glob(os.path.normpath(name))
        if not nameall:
            msg ="Error 208: File missing \n"
            raise CWATMFileError(name,msg, sname=maps)
        nameall.sort()
        meteolist = {}
        startfile = 0
        nextdate = None   # day after the end of the last file used

        for filename in nameall:

            # --- Netcdf -------------
            try:
                nf1 = ncopen(filename)   # cached: reused by readmeteodata, checkifDate, metaNetCDF
            except:
                msg = "Error 209: Netcdf map stacks: " + filename +"\n"
                raise CWATMFileError(filename, msg, sname=maps)
            nctime = nf1.variables['time']

            unitconv1 = ["DAYS", "HOUR", "MINU", "SECO"]
            unitconv2 = [1, 24, 1440, 86400]
            try:
                unitconv3 = nctime.units[:4].upper()
                datediv = unitconv2[unitconv1.index(unitconv3)]
            except:
                datediv = 1

            try:
                history = nf1.getncattr('history')
            except:
                history = ""
            addtoversiondate(filename,history)
            # round down: a daily record stamped e.g. at 12:00 (x.5) belongs to day x (1e-6: float noise of x.9999999)
            datestartint = int(math.floor(nctime[0].data.tolist() + 1e-6)) // datediv
            datelen= len(nctime)
            dateendint = datestartint + datelen - 1
            #if dateVar['leapYear'] > 0:
            startint = int(date2num(dateVar[startcheck],nctime.units,calendar=nctime.calendar))
            start = num2date(startint, units=nctime.units, calendar=nctime.calendar)
            startint = startint // datediv

            endint = int(date2num(end, nctime.units, calendar=nctime.calendar))
            endint = endint // datediv

            #else:
            #    start = dateVar[startcheck]
            value = getvariablename(nf1)

            # check if mask = map size -> if yes do not cut the map
            shapey = nf1.variables[value].shape[1]
            shapex = nf1.variables[value].shape[2]
            cutcheck = (shapey, shapex) != tuple(maskinfo['shape'])

            # check if it is x or X
            yy = maskmapAttr['coordy']
            if yy == "y":
                if "Y" in nf1.variables.keys(): yy = "Y"
            else:
                if "y" in nf1.variables.keys(): yy = "y"

            # checkif latitude is reversed
            turn_latitude = False
            if (nf1.variables[yy][0] - nf1.variables[yy][-1]) < 0:
                turn_latitude = True

            if startfile == 0:  # search first file where dynamic run starts
                if (dateendint >= startint): # if enddate of a file is bigger than the start of run
                    # and (datestartint <= startint):  # remove thiis, because glacier maps could start latter, than the day of the year of first year is  use
                    startfile = 1
                    indstart = startint - datestartint

                    indend = dateendint - datestartint

                    # value varname of netcdf as index: 4
                    # cutmap as index 5
                    # name of y or latitude: 6
                    # if map is turned )North is down): 7
                    # shapey, shapex : shape y and y of total map  8, 9
                    # Number - no of meteofile  10
                    meteolist[startfile-1] = [filename,indstart,indend, start,value,cutcheck,yy,turn_latitude, shapey, shapex,no]
                    inputcounter[maps] = indstart  # startindex of timestep 1
                    startint = dateendint + 1
                    start = num2date(startint * datediv, units=nctime.units, calendar=nctime.calendar)
                    nextdate = start
                    no += 1

                    # counter is set to a minus value - for some maps (e.g. glacier) if the counter is negativ
                    # the doy of a year of first year is loaded -> to use runs  before glacier maps are calculated
            else:
                if (datestartint >= startint) and (datestartint <= endint):
                    # this file has to start on the day after the previous file ended
                    missing = datestartint - int(date2num(nextdate, nctime.units, calendar=nctime.calendar)) // datediv
                    if missing > 0:
                        msg = "Error 228: " + str(missing) + " days are missing in the map stack before: " + filename + "\n"
                        raise CWATMFileError(filename, msg, sname=maps)
                    startfile += 1
                    indstart = startint - datestartint
                    indend = dateendint - datestartint
                    meteolist[startfile - 1] = [filename, indstart,indend, start,value,cutcheck,yy,turn_latitude, shapey, shapex,no]

                    startint = dateendint + 1
                    start = num2date(startint * datediv, units=nctime.units, calendar=nctime.calendar)
                    nextdate = start
                    no += 1

            # --- End Netcdf -------------
        meteofiles[maps] =  meteolist
        flagmeteo[maps] = 0

    return

def readDischargeFiles(name, disall, nodays):
    """
    Read all days of a stack of netCDF discharge files (environmental flow) into an array.

    Parameters
    ----------
    name : str
        Key of meteofiles: files in time order, as from multinetdf (0: file, 1: index of the first day,
        5: the map has to be cut, 7: the latitude has to be turned).
    disall : numpy.ndarray
        Array [days, cells]; the first nodays rows are filled, missing values are NaN.
    nodays : int
        Number of days to read.

    Returns
    -------
    str
        Name of the last file read.
    """

    row = 0
    filename = ""
    for key in sorted(meteofiles[name]):
        info = meteofiles[name][key]
        filename = os.path.normpath(info[0])
        # only the first file can start before the period, the next ones are used from their first day
        indstart = info[1] if key == 0 else 0
        cut = info[5]
        turn_latitude = info[7]

        if indstart < 0:
            msg = "Error 166: Discharge file starts " + str(-indstart) + " days after the start of the period"
            msg += " (SpinUp or StepStart)\n"
            raise CWATMFileError(filename, msg, sname=name)

        try:
            nf1 = ncopen(filename)   # closes the file first if it is an output file of this run
        except Exception:
            msg = "Error 219: Netcdf map stacks: \n"
            raise CWATMFileError(filename, msg, sname=name)

        var = nf1.variables[getvariablename(nf1)]
        loc = [cutmap[2], cutmap[3], cutmap[0], cutmap[1]] if cut else [0, var.shape[1], 0, var.shape[2]]
        setmeteochunkcache(var, loc)

        for i in range(indstart, indstart + min(var.shape[0] - indstart, nodays - row)):
            if turn_latitude:
                # south is up in the file: first turn it, then cut
                mapnp = np.flipud(var[i])
                if cut:
                    mapnp = mapnp[loc[0]:loc[1], loc[2]:loc[3]]
            else:
                mapnp = var[i, loc[0]:loc[1], loc[2]:loc[3]]

            if mapnp.shape != tuple(maskinfo['shape']):
                msg = "Error 169: Discharge map has the size " + str(var.shape[1:])
                if cut:
                    msg += ", cut to " + str(mapnp.shape)
                msg += ", the mask map has " + str(tuple(maskinfo['shape'])) + "\n"
                raise CWATMFileError(filename, msg, sname=name)

            disall[row, :] = compressArray(mapnp, zeros=np.nan)
            row += 1

        ncclose(filename)

    if row < nodays:
        msg = "Error 166: Discharge files have only " + str(row) + " of the " + str(nodays) + " days needed\n"
        raise CWATMFileError(filename, msg, sname=name)
    return filename


def setmeteochunkcache(ncvar, loc, maxcache=1024 * 1024 * 1024):
    """
    Size the HDF5 chunk cache of a meteo variable so that every chunk touched by the
    cut window stays decompressed in memory across timesteps.
    Only matters for files with a time chunk > 1 (e.g. (30, y, x)); for (1, y, x) it is a no-op.

    ncvar    : netCDF4 variable
    loc      : [y0, y1, x0, x1] cut window (as used in readmeteodata)
    maxcache : upper limit in bytes (default 1 GB)
    """
    chunks = ncvar.chunking()
    if (chunks is None) or (chunks == 'contiguous') or (len(chunks) != 3):
        return
    ct, cy, cx = chunks
    if ct <= 1:
        return

    # number of chunks the window touches in y and x
    ny = (loc[1] - 1) // cy - loc[0] // cy + 1
    nx = (loc[3] - 1) // cx - loc[2] // cx + 1
    nchunks = ny * nx

    chunkbytes = ct * cy * cx * ncvar.dtype.itemsize
    size = min(2 * nchunks * chunkbytes, maxcache)   # factor 2 = headroom
    nelems = max(1009, 4 * nchunks + 1)                # hash-table slots, ideally >> number of chunks
    try:
        ncvar.set_var_chunk_cache(size=int(size), nelems=int(nelems), preemption=0.75)
    except:
        pass   # older netCDF-C / non-HDF5 file: keep library default

def closemeteofile(name):
    """
    Close the open netCDF handle of one meteo map stack (if any).
    Called when the run moves on to the next file of the stack.
    (At the end of a run caching.ncclose_all closes all files; a handle left in meteohandles is then
    closed and is opened again by readmeteodata, see isopen())
    """
    handle = meteohandles.pop(name, None)
    if handle is not None:
        ncclose(handle[2])   # handle = [Dataset, file number, filename] - shared with caching.ncopen

def readmeteodata(name, date, value='None', addZeros=False, zeros=0.0, mapsscale=True,
                  extendback=False, glacier=False):
    """
    Read meteorological forcing data for specific time steps.
    
    Primary function for loading time-varying meteorological data during
    model execution. Handles temporal indexing, data extraction, scaling,
    and format conversion for various meteorological variables. Supports
    efficient caching for improved performance.
    
    Parameters
    ----------
    name : str
        Variable name or configuration binding key for meteorological data.
    date : datetime-like
        Target date for data extraction.
    value : str, optional
        NetCDF variable name if different from binding key. Default is 'None'.
    addZeros : bool, optional
        If True, replace missing values with zeros value. Default is False.
    zeros : float, optional
        Value to use when addZeros=True. Default is 0.0.
    mapsscale : bool, optional
        If True, apply scaling factors and offsets. Default is True.
    extendback : bool, optional
        If True, extend data backward in time if needed. Default is False.
    
    Returns
    -------
    numpy.ndarray
        Meteorological data array for the specified date, in compressed
        1D format or 2D depending on configuration.
    
    Notes
    -----
    - Handles various temporal conventions and calendars
    - Supports data scaling and unit conversions
    - Implements efficient caching
    - Critical for model forcing data integration
    - Manages memory usage during long simulations
    """

    try:
        meteoInfo = meteofiles[name][flagmeteo[name]]
        idx = inputcounter[name]
        filename =  os.path.normpath(meteoInfo[0])
      
    except:
        date1 = "%02d/%02d/%02d" % (date.day, date.month, date.year)
        msg = "Error 210: Netcdf map error for: " + name + " -> " + cbinding(name) + " on: " + date1 + ": \n"
        raise CWATMError(msg)


    # for glaciermaps extend back into past if glaciermaps start later -> use day of the year of first year
    if idx < 0:
        if extendback:
            idx = dateVar['doy'] - 1
        else:
            date1 = "%02d/%02d/%02d" % (date.day, date.month, date.year)
            msg = "Error 211: Netcdf map: " + name + " -> " + cbinding(name) + " starts later than first date of simulation on: " + date1 + ": \n"
            raise CWATMError(msg)

    warnings.filterwarnings("ignore")
    if value == "None":
        value = meteofiles[name][flagmeteo[name]][4]
    cutcheck = meteofiles[name][flagmeteo[name]][5]
    yy = meteofiles[name][flagmeteo[name]][6]
    turn_latitude = meteofiles[name][flagmeteo[name]][7]

    if cutcheck:
        loc = [cutmapFine[2],cutmapFine[3],cutmapFine[0], cutmapFine[1]]
    else:
        loc = [0,meteofiles[name][flagmeteo[name]][8], 0, meteofiles[name][flagmeteo[name]][9]]

        if glacier:
            loc = maskmapAttr['cut']

    # +++++++++++++++ Netcdf ++++++++++++++++++++++
    # the file handle is kept open across timesteps (opened on first use, closed when the
    # run moves to the next file of the stack or by caching.ncclose_all() at the end of the run)
    fileno = flagmeteo[name]
    handle = meteohandles.get(name)
    if (handle is None) or (handle[1] != fileno) or (not handle[0].isopen()):
        if handle is not None:
            closemeteofile(name)
        try:
            nf1 = ncopen(filename)   # shared handle: file was already opened by multinetdf
        except:
            msg = "Error 223: Netcdf map stacks: \n"
            raise CWATMFileError(filename, msg, sname=name)
        setmeteochunkcache(nf1.variables[value], loc)
        meteohandles[name] = [nf1, fileno, filename]
    else:
        nf1 = handle[0]

    mapnp = nf1.variables[value][idx, loc[0]:loc[1],loc[2]:loc[3]]
    # +++++++++++++++ Netcdf End++++++++++++++++++++++

    mapnp = mapnp.astype(np.float64)

    if turn_latitude:
        mapnp = np.flipud(mapnp)
    # missing values of the file become NaN
    mapnp = np.ma.filled(mapnp, np.nan)
    mapnp[mapnp>1e15] = np.nan


    # add zero values to maps in order to supress missing values
    if addZeros: mapnp[np.isnan(mapnp)] = zeros

    if mapsscale:  # if meteo maps have the same extend as the other spatial static maps -> meteomapsscale = True
        if maskinfo['shapeflat'][0]!= mapnp.size:
            msg = "Error 109: " + name + " has less or more valid pixels than the mask map \n"
            msg += "if it is the ET maps, it might be from another run with different mask. Please look at the option: calc_evaporation"
            raise CWATMError(msg)

        mapC = compressArray(mapnp, name=filename,zeros = zeros)
        if Flags['check']:
            checkmap(name, filename, mapnp)
    else: # if static map extend not equal meteo maps -> downscaling in readmeteo
        mapC = mapnp
        if Flags['check']:
            checkmap(name, filename, mapnp)

    # increase index and check if next file
    #if (dateVar['leapYear'] == 1) and calendar.isleap(date.year):
    #    if (date.month ==2) and (date.day == 28):
    #        ii = 1  # dummmy for not doing anything
    #    else:

    inputcounter[name] += 1
    if inputcounter[name] > meteoInfo[2]:
        inputcounter[name] = 0
        flagmeteo[name] += 1
        closemeteofile(name)   # next timestep opens the next file of the stack

    return mapC




def readnetcdf2(namebinding, date, useDaily='daily', value='None', addZeros=False, cut=True, 
                zeros=0.0, meteo=False, usefilename=False, compress=True):
    """
    Generic NetCDF data reader with flexible temporal and spatial options.
    
    Versatile function for reading NetCDF data with various temporal
    aggregation options, spatial clipping, and format conversions.
    Supports both meteorological and static data with comprehensive
    error handling and data validation.
    
    Parameters
    ----------
    namebinding : str
        Configuration binding key or file path.
    date : datetime-like
        Target date for temporal data extraction.
    useDaily : str, optional
        Temporal aggregation method ('daily', 'monthly', etc.).
        Default is 'daily'.
    value : str, optional
        NetCDF variable name. Default is 'None'.
    addZeros : bool, optional
        Replace missing values with zeros value. Default is False.
    cut : bool, optional
        Clip data to model domain. Default is True.
    zeros : float, optional
        Replacement value for missing data. Default is 0.0.
    meteo : bool, optional
        True if reading meteorological data. Default is False.
    usefilename : bool, optional
        Use filename as variable name. Default is False.
    compress : bool, optional
        Return compressed 1D format. Default is True.
    
    Returns
    -------
    numpy.ndarray
        Extracted data in requested format (1D compressed or 2D).
    
    Notes
    -----
    - Supports multiple temporal aggregation methods
    - Handles various NetCDF conventions and structures
    - Provides comprehensive error handling and validation
    - Used throughout CWatM for diverse data loading needs
    """

    # in case a filename is used e.g. because of direct loading of pre results
    if usefilename:
        name = namebinding
    else:
        name = cbinding(namebinding)
    filename =  os.path.normpath(name)


    try:
       nf1 = ncopen(filename)   # cached: 10-day, monthly, yearly stacks are opened only once
    except:
        msg = "Error 212: Netcdf map stacks: \n"
        raise CWATMFileError(filename,msg, sname = namebinding)

    if value == "None":
        value = getvariablename(nf1)
    # stacks read every time step (day-of-year, daily): keep decompressed time chunks in memory
    # if several time steps share one chunk (monthly/yearly reads are too rare to be worth the memory)
    if nf1.variables[value].ndim == 3 and useDaily in ("DOY", "daily"):
        ncstackcache(filename, nf1.variables[value])

    # date if used daily, monthly or yearly or day of year
    idx = None  # will produce an error and indicates something is wrong with date
    if useDaily == "DOY":  # day of year 1-366
        idx = date - 1
    if useDaily == "10day":  # every 10 days
        idx = date
    if useDaily == "month":
        idx = int(date.month) - 1

    if useDaily in ["monthly","yearly","daily"]:

        # DATE2INDEX TAKES A LONG TIME TO GET THE INDEX, THIS SHOULD BE A FASTER VERSION, ONCE THE FIRST INDEX IS COLLECTED
        if (value in inputcounter) and meteo:
            inputcounter[value] += 1
            idx = inputcounter[value]
        else:
            # look for the record of this year/month: with 1 January / the 1st of the month
            # 'nearest' finds records dated on the 1st or in the middle of the month/year
            if useDaily == "yearly":
                date = datetime.datetime(date.year, 1, 1)
            if useDaily == "monthly":
                date = datetime.datetime(date.year, date.month, 1)

            # A netCDF time variable object  - time index (in the netCDF file)
            nctime = nf1.variables['time']

            if nctime.calendar in ['noleap', '365_day']:
                dateVar['leapYear'] = 1
                idx = date2indexNew(date, nctime, calendar=nctime.calendar, select='nearest', name = name)
            elif nctime.calendar in ['360_day']:
                dateVar['leapYear'] = 2
                idx = date2indexNew(date, nctime, calendar=nctime.calendar, select='nearest', name = name)
            else:
                #idx = date2index(date, nctime, calendar=nctime.calendar, select='exact')
                idx = date2indexNew(date, nctime, calendar=nctime.calendar, select='nearest', name = name)

            if meteo: inputcounter[value] = idx

    # store the name and the date when the file is read the first time (files read only later in the run too,
    # e.g. monthly water demand)
    if filename not in versioning.get('inputdates', {}):
        try:
            history = nf1.getncattr('history')
        except:
            history = ""
        addtoversiondate(filename, history)


    #checkif latitude is reversed
    turn_latitude = False
    for yy in ('lat', 'y', 'Y'):
        if yy in nf1.variables and nf1.variables[yy].ndim == 1:
            if (nf1.variables[yy][0] - nf1.variables[yy][-1]) < 0:
                turn_latitude = True
                mapnp = nf1.variables[value][idx].astype(np.float64)
                mapnp = np.flipud(mapnp)
            break
    if 'Glacier' in namebinding:
        cut = tuple(nf1.variables[value].shape[1:3]) != tuple(maskinfo['shape'])

    if cut:
        # the cut of this file only: the global cutmap is used by the other maps
        cuts = cutmap
        if 'maps_cut_individually' in option:
            if checkOption('maps_cut_individually'):
                cuts = mapattrNetCDF(name)
        if turn_latitude:
            mapnp = mapnp[cuts[2]:cuts[3], cuts[0]:cuts[1]]
        else:
            mapnp = nf1.variables[value][idx, cuts[2]:cuts[3], cuts[0]:cuts[1]].astype(np.float64)
    else:
        if not(turn_latitude):
            mapnp = nf1.variables[value][idx].astype(np.float64)
    # missing values of the file get the value of zeros; compress=False: the caller (downscaling) gets the file's values
    mapnp = np.ma.filled(mapnp, zeros) if compress else np.ma.getdata(mapnp)

    # add zero values to maps in order to supress missing values
    if addZeros: mapnp[np.isnan(mapnp)] = zeros
    if not compress:
        return mapnp

    if maskinfo['shapeflat'][0]!= mapnp.size:
        msg = "Error 110: " + name + " has less or more valid pixels than the mask map \n"
        raise CWATMError(msg)

    mapC = compressArray(mapnp, name=filename)
    if Flags['check']:
        checkmap(value, filename, mapnp)
    return mapC


def readnetcdfWithoutTime(name, value="None", counter=0):
    """
    Read static (time-independent) data from NetCDF files.
    
    Specialized function for loading static spatial data that does not
    have a temporal dimension. Used for parameters, initial conditions,
    and other time-invariant model inputs.
    
    Parameters
    ----------
    name : str
        Configuration binding key or file path.
    value : str, optional
        NetCDF variable name. Default is "None".
    counter : int, optional
        Array index for multi-layer data. Default is 0.
    
    Returns
    -------
    numpy.ndarray
        Static spatial data in compressed format.
    
    Notes
    -----
    - Optimized for static data without temporal dimensions
    - Handles multi-layer datasets with counter parameter
    - Performs spatial consistency checking
    - Used for loading parameters and initial conditions
    """

    filename =  os.path.normpath(name)

    try:
       nf1 = ncopen(filename)   # cached: e.g. dzRel - 12 layers from one file
    except:
        msg = "Error 213: Netcdf map stacks: \n"
        raise CWATMFileError(filename,msg)
    if value == "None":
        value = getvariablename(nf1)

    # south to north would load the map upside down (the name of y can differ from the mask map)
    for yy in (maskmapAttr['coordy'], 'lat', 'latitude', 'y', 'Y'):
        if yy in nf1.variables:
            if (nf1.variables[yy][0] - nf1.variables[yy][-1]) < 0:
                msg = "Error 111: Latitude is in wrong order\n"
                raise CWATMFileError(filename, msg)
            break

    mapnp = nf1.variables[value][cutmap[2]:cutmap[3], cutmap[0]:cutmap[1]].astype(np.float64)
    # store date
    if counter == 0:
        try:
            history = nf1.getncattr('history')
        except:
            history = ""
        addtoversiondate(filename, history)


    mapC = compressArray(mapnp, name=filename)
    if Flags['check']:
        checkmap(value, filename, mapnp)

    return mapC

def readnetcdf12month(name, month,value="None"):
    """
    Read monthly climatological data from 12-month NetCDF files.
    
    Specialized reader for climatological data organized as 12-month
    time series. Commonly used for seasonal parameters, climatologies,
    and cyclic forcing data that varies by month but not by year.
    
    Parameters
    ----------
    name : str
        Configuration binding key or file path.
    month : int
        Month number (1-12) for data extraction.
    value : str, optional
        NetCDF variable name. Default is "None".
    
    Returns
    -------
    numpy.ndarray
        Monthly climatological data in compressed format.
    
    Notes
    -----
    - Handles seasonal and climatological data
    - Assumes 12-month temporal dimension
    - Used for cyclic parameters and seasonal forcing
    - Supports monthly varying model parameters
    """

    filename =  os.path.normpath(name)

    try:
       nf1 = ncopen(filename)   # cached: 12 monthly maps from one file (lapse rate)
    except:
        msg = "Error 224: Netcdf map stacks: \n"
        raise CWATMFileError(filename,msg)
    if value == "None":
        value = getvariablename(nf1) # get the last variable name

    mapnp = nf1.variables[value][month,cutmap[2]:cutmap[3], cutmap[0]:cutmap[1]].astype(np.float64)

    # store date (addtoversiondate: each file only once)
    try:
        history = nf1.getncattr('history')
    except:
        history = ""
    addtoversiondate(filename, history)

    mapC = compressArray(mapnp, name=filename)
    if Flags['check']:
        checkmap(value, filename, mapnp)
    return mapC


def readnetcdfInitial(name, value, default=0.0, warn=True):
    """
    Read initial condition data with fallback defaults.
    
    Specialized function for loading initial conditions and state variables
    at model startup. Provides fallback to default values when initial
    condition files are not available, enabling model cold starts.
    
    Parameters
    ----------
    name : str
        Configuration binding key for initial condition file.
    value : str
        Variable name within the NetCDF file.
    default : float, optional
        Default value to use if file not found. Default is 0.0.
    warn : bool, optional
        False: no warning if the variable is not in the file. Default is True.

    Returns
    -------
    numpy.ndarray
        Initial condition data or default values in compressed format.
    
    Notes
    -----
    - Essential for model initialization and warm starts
    - Provides graceful handling of missing initial condition files
    - Supports both warm starts (from files) and cold starts (defaults)
    - Used for hydrological state variables and storage initialization
    """

    filename =  os.path.normpath(name)
    try:
       nf1 = ncopen(filename)   # init file is opened only once for all initial variables
    except:
        msg = "Error 214: Netcdf Initial file: \n"
        raise CWATMFileError(filename,msg)
    if value in list(nf1.variables.keys()):
        try:
            if 'X' in nf1.variables.keys():
                maskmapAttr['coordx'] = 'X'
                maskmapAttr['coordy'] = 'Y'
            if 'x' in nf1.variables.keys():
                maskmapAttr['coordx'] = 'x'
                maskmapAttr['coordy'] = 'y'
            
            cut0, cut1, cut2, cut3 = mapattrNetCDF(filename)

            if (nf1.variables[maskmapAttr['coordy']][0] - nf1.variables[maskmapAttr['coordy']][-1]) < 0:
                msg = "Error 112: Latitude is in wrong order\n"
                raise CWATMFileError(filename, msg)

            #mapnp = nf1.variables[value][cut2:cut3, cut0:cut1].astype(np.float64)
            var = nf1.variables[value]
            var.set_auto_maskandscale(False)  # preserve stored dtype
            mapnp = nf1.variables[value][cut2:cut3, cut0:cut1]

            # read creating date
            try:
                history = nf1.getncattr('history')
            except:
                history = ""
            addtoversiondate(filename,history)
            
            mapC = compressArray(mapnp, name=filename)
            if Flags['check']:
                checkmap(value, filename, mapnp)
            if mapC.shape != globals.inZero.shape:
                msg = "Error 113: map shape is different than mask shape\n"
                raise CWATMError(msg)
            return mapC
        except CWATMError:
            # Error 107, 112, 113 are more exact than Error 114
            raise
        except Exception:
            #nf1.close()
            msg ="Error 114: ===== Problem reading initial data ====== \n"
            msg += "Initial value: " + value + " is has not the same shape as the mask map\n"
            msg += "Maybe put\"load_initial = False\""
            raise CWATMError(msg)

    else:
        if warn:
            default_text = str(default) if np.ndim(default) == 0 else "map with mean " + str(np.mean(default))
            msg = "Warning: Initial value: " + value + " is not included in: " + name + " - using default: " + default_text
            print(CWATMWarning(msg))
        return default


def initialIncluded(name, value):
    """True if the variable value is in the initial condition file name (file opened once, see ncopen)"""
    filename = os.path.normpath(name)
    try:
        nf1 = ncopen(filename)
    except:
        msg = "Error 214: Netcdf Initial file: \n"
        raise CWATMFileError(filename,msg)
    return value in nf1.variables

# --------------------------------------------------------------------------------------------

def ncgrid(nf1, row, col, axis=True, lonlat_fill=None):
    """
    Create and fill the x and y coordinates of a new netCDF file and copy the crs variable.

    Name and attributes of the coordinates come from the precipitation maps (metaNetCDF).

    Parameters
    ----------
    nf1 : netCDF4.Dataset
        New file, open for writing.
    row, col : int
        Number of rows and columns.
    axis : bool, optional
        True: coordinates get the attribute axis. Default is True.
    lonlat_fill : float, optional
        Fill value of lon and lat. Default is None.

    Returns
    -------
    tuple
        Names of the dimensions for a map: ('y', 'x') or ('lat', 'lon').
    """
    # SHMI meteorogist have a capital X and Y
    fields = [('x', 'x', col, 'X', None), ('y', 'y', row, 'Y', None), ('X', 'x', col, 'X', None), ('Y', 'y', row, 'Y', None)]
    latlon = not ('x' in metadataNCDF or 'X' in metadataNCDF)
    if latlon:
        fields += [('lon', 'lon', col, 'X', lonlat_fill), ('lat', 'lat', row, 'Y', lonlat_fill)]

    coord = {}
    for key, dim, size, axisname, fill in fields:
        if key in metadataNCDF:
            nf1.createDimension(dim, size)
            coord[axisname] = nf1.createVariable(dim, 'f8', (dim,), fill_value=fill)
            for i in metadataNCDF[key]:
                setattr(coord[axisname], i, str(metadataNCDF[key][i]))
            if axis:
                coord[axisname].axis = axisname

    # projection -> replace by crs  as in cf1.13
    if projection['crs'] != None:
        crs = nf1.createVariable('crs', 'i4',())
        for key in projection['crs'].ncattrs():
            setattr(crs, key, projection['crs'].getncattr(key))

    cell = maskmapAttr['cell']
    xl = maskmapAttr['x']
    xr = xl + col * cell
    yu = maskmapAttr['y']
    yd = yu - row * cell
    lats = np.linspace(yu, yd, row, endpoint=False)
    lons = np.linspace(xl, xr, col, endpoint=False)

    coord['Y'][:] = lats - cell / 2.0
    coord['X'][:] = lons + cell /2.0

    return ('lat', 'lon') if latlon else ('y', 'x')


def writenetcdf(netfile, prename, addname, varunits, inputmap, timeStamp, posCnt, flag, flagTime, 
                nrdays=None, dateunit="days"):
    """
    Write CWatM results to NetCDF output files with proper metadata.
    
    Primary output function for writing model results to CF-compliant
    NetCDF files. Handles spatial decompression, temporal indexing,
    metadata attribution, and file management for various output types
    including maps, time series, and aggregated results.
    
    Parameters
    ----------
    netfile : str
        Output NetCDF file path.
    prename : str
        Variable name prefix for organization.
    addname : str
        Additional name component for the variable.
    varunits : str
        Physical units for the variable.
    inputmap : numpy.ndarray
        Data array to write (1D compressed format).
    timeStamp : datetime-like
        Timestamp for the data.
    posCnt : int
        Position counter for time indexing.
    flag : str
        Output type flag ('end', 'sum', 'avg', etc.).
    flagTime : str
        Temporal aggregation flag ('daily', 'monthly', etc.).
    nrdays : int, optional
        Number of days for averaging calculations. Default is None.
    dateunit : str, optional
        Time unit specification. Default is "days".
    
    Returns
    -------
    None
        Writes data to NetCDF file with proper formatting and metadata.
    
    Notes
    -----
    - Creates CF-compliant NetCDF files with full metadata
    - Handles spatial decompression from 1D to 2D format
    - Supports various temporal aggregation methods
    - Includes version tracking and provenance information
    - Essential for model output and result distribution
    """

    row = np.abs(cutmap[3] - cutmap[2])
    col = np.abs(cutmap[1] - cutmap[0])


    # check if it is a modflow grid which has another resolution (grid and variable: data_modflow.py)
    modflow = "modflow" in prename.lower()
    if modflow:
        row = domain['nrow']
        col = domain['ncol']


    # create real varname with variable name + time depending name e.g. discharge + monthavg
    varname = prename + addname

    #remove ' in the name. Can happen under Linux
    #netfile = netfile.replace("'","")

    if not flag:
        ncclose(netfile)   # in case the file was read before as input (cached handle)
        ncwriteclose(netfile)   # a new file with the same name in the same run
        nf1 = Dataset(netfile, 'w', format='NETCDF4')

        # general Attributes
        settings = os.path.realpath(settingsfile[0])
        nf1.settingsfile = settings + ": " + xtime.ctime(os.path.getmtime(settings))
        nf1.history = "Created "+ xtime.ctime(xtime.time())
        nf1.Source_Software = 'CWatM Python: ' + versioning['exe'] + " Git Branch:" + versioning['git']["git_branch"] + " Hash:" + versioning['git']["git_hash"] + " " + versioning['git']["state"]
        nf1.Platform = versioning['platform']
        nf1.Version = versioning['version']  + ": " + versioning['lastfile']  + " " + versioning['lastdate']
        nf1.institution = cbinding ("institution")
        nf1.title = cbinding ("title")
        nf1.source = 'CWATM output maps'
        nf1.Conventions = 'CF-1.13'

        try:
            nf1.setncatts(version_attributes())
            gname = os.path.basename(netfile)
            # save the versioning of input files in discharge or ET EW maps
            # save the settingsfile
            if gname[0:9] == "discharge" or gname[0:1] == "E":
                nf1.version_inputfiles = versioning['input']
                with open(settings, 'r', encoding='utf-8') as file:
                    #nf1.version_settingsfile = file.read().splitlines()

                    nf1.version_settingsfile = '\n'.join(file.read().splitlines())

                # save the python version
                python_modules = sys.version
                for name, module in sorted(sys.modules.items()):
                    if module and hasattr(module, '__version__') and not name.startswith('_'):
                        python_modules += "; "+f"{name}: {module.__version__}"
                nf1.version_modules = python_modules


        except:
            pass


        # put the additional genaral meta data information from the xml file into the netcdf file
        # infomation from the settingsfile comes first
        if prename in metaNetcdfVar:
           for key in metaNetcdfVar[prename]:
                if not (key in list(nf1.__dict__.keys())):
                    if not (key in ["unit", "long_name", "standard_name"]):
                        nf1.__setattr__(key, metaNetcdfVar[prename][key])



        # Dimension, coordinates and crs (ModFlow grid: in data_modflow.py)
        if modflow:
            modflow_netcdf_grid(nf1, domain)
        else:
            griddims = ncgrid(nf1, row, col)

        if flagTime:

            year = dateVar['dateStart'].year
            if year > 1900:   yearstr = "1901"
            elif year < 1861: yearstr = "1650"
            else:             yearstr = "1861"

            #nf1.createDimension('time', None)
            nf1.createDimension('time', nrdays)
            time = nf1.createVariable('time', 'f8', 'time')
            time.standard_name = 'time'
            time.long_name = 'time'
            time.units = 'days since ' + yearstr + '-01-01'
            #if dateunit == "days": time.units = 'Days since ' + yearstr + '-01-01'
            #if dateunit == "months": time.units = 'Months since ' + yearstr + '-01-01'
            #if dateunit == "years": time.units = 'Years since ' + yearstr + '-01-01'
            #time.calendar = 'standard'
            time.calendar = dateVar['calendar']
            time.axis = "T"

            if modflow:
                value = modflow_netcdf_variable(nf1, varname, flagTime, domain)
            else:
                value = nf1.createVariable(varname, 'f4', ('time',) + griddims, zlib=True, fill_value=1e20, chunksizes=(1, row, col))
        else:
          if modflow:
              value = modflow_netcdf_variable(nf1, varname, flagTime, domain)
          else:
              value = nf1.createVariable(varname, 'f4', griddims, zlib=True,fill_value=1e20)

        ## remove as in cf1.13 standard name is defined in a list
        ###value.standard_name = getmeta("standard_name",prename,varname)
        p1 = getmeta("long_name",prename,prename)
        p2 = getmeta("time", addname, addname)
        value.long_name = p1 + p2
        value.units= getmeta("unit",prename,varunits)

        # ModFlow grid: grid_mapping set in modflow_netcdf_variable
        if not modflow and projection['crs'] != None:
            value.grid_mapping = "crs"

        #for var in list(metadataNCDF.keys()):
        #    if "esri_pe_string" in list(metadataNCDF[var].keys()):
        #        value.esri_pe_string = metadataNCDF[var]['esri_pe_string']

    else:
        # stays open until the end of the run (ncwriteclose_all) - opening on a network drive costs time
        nf1 = ncappend(netfile)

    if flagTime:
        date_time = nf1.variables['time']
        # if dateunit is month or year then set date to the first days of the period
        if dateunit == "months": timeStamp = timeStamp.replace(day=1)
        if dateunit == "years": timeStamp = timeStamp.replace(day=1,month =1)
        nf1.variables['time'][posCnt - 1] = date2num(timeStamp, date_time.units, date_time.calendar)

    mapnp = maskinfo['maskall'].copy()

    # if inputmap is not an array give out errormessage
    if not(hasattr(inputmap, '__len__')):
        date1 = "%02d/%02d/%02d" % (timeStamp.day, timeStamp.month, timeStamp.year)
        msg = "No values in: " + varname + " on date: " + date1 +"\nCould not write: " + netfile
        if not flag:
            nf1.close()   # a new file is closed, an appended file stays open (ncappend)
        print(CWATMWarning(msg))
        return False

    if modflow:
        mapnp = inputmap
    else:
        mapnp[~maskinfo['maskflat']] = inputmap[:]
        mapnp = mapnp.reshape(maskinfo['shape'])

        if coverresult[0]:
            # cells outside the mask have no value: NaN, also where cover = 1
            mapnp = np.where(coverresult[1], np.ma.filled(mapnp, np.nan), np.nan)

    if flagTime:
        nf1.variables[varname][posCnt -1, :, :] = mapnp
    else:
        # without timeflag
        nf1.variables[varname][:, :] = mapnp

    if not flag:
        nf1.close()   # a new file is closed, an appended file stays open (ncappend)
    flag = True

    return flag


# --------------------------------------------------------------------------------------------


def writeIniNetcdf(netfile,varlist, inputlist):
    """
    Write initial condition NetCDF files for model restart.
    
    Creates NetCDF files containing model state variables for warm start
    and restart capabilities. Saves hydrological state information that
    can be used to initialize subsequent model runs, enabling operational
    workflows and long-term simulations.
    
    Parameters
    ----------
    netfile : str
        Output NetCDF file path for initial conditions.
    varlist : list
        List of variable names to include in the file.
    inputlist : list
        List of corresponding data arrays (1D compressed format).
    
    Returns
    -------
    None
        Creates NetCDF initial condition file with state variables.
    
    Notes
    -----
    - Essential for model restart and warm start capabilities
    - Saves complete hydrological state information
    - Enables operational modeling and long simulations
    - Includes spatial decompression and proper metadata
    """

    row = np.abs(cutmap[3] - cutmap[2])
    col = np.abs(cutmap[1] - cutmap[0])

    ncclose(netfile)   # e.g. initSave == initLoad: close cached read handle first
    nf1 = Dataset(netfile, 'w', format='NETCDF4')

    # general Attributes
    nf1.settingsfile = os.path.realpath(settingsfile[0])
    nf1.date_created = xtime.ctime(xtime.time())
    nf1.Source_Software = 'CWATM Python'
    nf1.setncatts(version_attributes())
    nf1.institution = cbinding ("institution")
    nf1.title = cbinding ("title")
    nf1.source = 'CWATM initial conditions maps'
    nf1.Conventions = 'CF-1.13'

    # put the additional genaral meta data information from the xml file into the netcdf file
    # infomation from the settingsfile comes first

    if "initcondition" in metaNetcdfVar:
        for key in metaNetcdfVar["initcondition"]:
            if not (key in list(nf1.__dict__.keys())):
               if not (key in ["unit", "long_name", "standard_name"]):
                   nf1.__setattr__(key, metaNetcdfVar["initcondition"][key])


    # Dimension, coordinates and crs
    griddims = ncgrid(nf1, row, col, axis=False, lonlat_fill=1e20)

    i = 0
    for varname in varlist:
        dtype_str = np.asarray(inputlist[i][0]).dtype.name
        type_args = {'float64':'f8', 'float32':'f4'}
        value = nf1.createVariable(varname, type_args[dtype_str], griddims, zlib=True, fill_value=1e20)

        ## as in writenetcdf: in cf1.13 standard name is defined in a list
        value.long_name= getmeta("long_name",varname,varname)
        value.units= getmeta("unit",varname,"undefined")
        if projection['crs'] != None:
            value.grid_mapping = "crs"

        # write values
        mapnp = maskinfo['maskall'].copy()
        # no lower limit: balance storages (e.g. lakeStorageBalance in m3) can be below -9999 - a limit changes the restart
        help = np.minimum(10e15, inputlist[i][:])
        mapnp[~maskinfo['maskflat']] = help
        mapnp = mapnp.reshape(maskinfo['shape'])

        nf1.variables[varname][:, :] = mapnp
        i += 1



    nf1.close()

# --------------------------------------------------------------------------------------------
# report .tif

def report(valueIn,name,compr=True):
    """
    Write a map as GeoTIFF.

    Parameters
    ----------
    valueIn : numpy.ndarray
        Map: 1D compressed (compr=True) or 2D (compr=False). An integer map is written as int32, others keep their type.
    name : str
        Name of the file. It always gets the ending .tif.
    compr : bool, optional
        If True, input data is in compressed format. Default is True.

    Returns
    -------
    None
    """

    name = os.path.splitext(name)[0] + ".tif"
    nodata = -9999

    value = decompress(valueIn) if compr else valueIn
    # decompress gives float64 also for integer maps
    checkint = np.asarray(valueIn).dtype.char in np.typecodes['AllInteger']
    value = np.ma.filled(value, nodata)
    if checkint:
        value = value.astype(np.int32)

    ny, nx = value.shape
    geo = (maskmapAttr['cell'], 0.0, maskmapAttr['x'], 0.0, -maskmapAttr['cell'], maskmapAttr['y'])

    # projection from the settings, otherwise lat/lon if the coordinates can be lat/lon
    crsvar = projection.get('crs')
    crs = getattr(crsvar, 'crs_wkt', getattr(crsvar, 'spatial_ref', None))
    if crs is None and abs(maskmapAttr['x']) <= 360 and abs(maskmapAttr['y']) <= 90:
        crs = "+proj=latlong"

    with rasterio.open(name,
        mode="w", driver="GTiff", height=ny, width=nx, count=1,
        dtype=value.dtype, crs=crs, transform=geo, nodata=nodata,
    ) as new_dataset:
        new_dataset.write(value, 1)

# --------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------

def returnBool(inBinding):
    """
    Convert configuration strings to boolean values.
    
    Utility function for parsing boolean configuration options from
    the settings file. Handles various string representations of
    boolean values and provides consistent boolean interpretation
    throughout CWatM.
    
    Parameters
    ----------
    inBinding : str
        Configuration value string to convert to boolean.
    
    Returns
    -------
    bool
        Boolean interpretation of the input string.
    
    Notes
    -----
    - Handles common boolean string representations
    - Provides consistent boolean parsing across CWatM
    - Used for processing configuration file options
    - Supports case-insensitive boolean interpretation
    """

    b = cbinding(inBinding)
    btrue = b.lower() in ("yes", "true", "t", "1")
    bfalse = b.lower() in ("no", "false", "f", "0")
    if btrue or bfalse:
        return btrue
    else:
        msg = "Error 115: Value in: \"" + inBinding + "\" is not True or False! \nbut: " + b
        raise CWATMError(msg)

def checkOption(inBinding,checkfirst = False):
    """
    Validate and process configuration option values.
    
    Performs validation and type checking for configuration options,
    ensuring that values are appropriate for their intended use.
    Provides error handling and default value assignment for
    configuration processing.
    
    Parameters
    ----------
    inBinding : str
        Configuration binding key to check and process.
    checkfirst : bool, optional
        If True, perform preliminary validation checks. Default is False.
    
    Returns
    -------
    varies
        Processed and validated configuration value.
    
    Notes
    -----
    - Validates configuration option values and types
    - Provides error handling for invalid configurations
    - Supports default value assignment
    - Used throughout configuration processing pipeline
    """

    if checkfirst:
        if not(inBinding in option):
            return False

    lineclosest = ""
    test = inBinding in option
    if test:
        return option[inBinding]
    else:
        close = difflib.get_close_matches(inBinding, list(option.keys()))
        if close:
            closest = close[0]
            with open(settingsfile[0], encoding='utf-8', errors='replace') as f:
                i = 0
                for line in f:
                    i +=1
                    if closest in line:
                        lineclosest = "Line No. " + str(i) + ": "+ line
        else:
            closest = "- no match -"

        msg = "Error 136: No key with the name: \"" + inBinding + "\" in the settings file: \"" + settingsfile[0] + "\"\n"
        msg += "Closest key to the required one is: \""+ closest + "\"\n"
        msg += lineclosest
        raise CWATMError(msg)

def cbinding(inBinding):
    """
    Process configuration binding with validation and type conversion.
    
    Core function for processing configuration bindings, performing
    type conversion, validation, and error handling. Ensures that
    configuration values are properly formatted and valid for use
    throughout the model.
    
    Parameters
    ----------
    inBinding : str
        Configuration binding key to process.
    
    Returns
    -------
    varies
        Processed configuration value with appropriate type conversion.
    
    Notes
    -----
    - Central function for configuration value processing
    - Handles type conversion and validation
    - Provides consistent error handling and reporting
    - Used extensively throughout CWatM configuration pipeline
    """

    lineclosest = ""
    test = inBinding in binding
    if test:
        return binding[inBinding]
    else:
        close = difflib.get_close_matches(inBinding, list(binding.keys()))
        if close:
            closest = close[0]

            with open(settingsfile[0], encoding='utf-8', errors='replace') as f:
                i = 0
                for line in f:
                    i +=1
                    if closest in line:
                        lineclosest = "Line No. " + str(i) + ": "+ line
        else:
            closest = "- no match -"

        msg = "Error 117: No key with the name: \"" + inBinding + "\" in the settings file: \"" + settingsfile[0] + "\"\n"
        msg += "Closest key to the required one is: \""+ closest + "\"\n"
        msg += lineclosest
        raise CWATMError(msg)


# --------------------------------------------------------------------------------------------

def divideValues(x,y, default = 0.):
    """
    Perform safe division with handling of zero denominators.
    
    Utility function for array division operations that handles
    division by zero cases gracefully. Provides default values
    when division is undefined, preventing numerical errors in
    hydrological calculations.
    
    Parameters
    ----------
    x : numpy.ndarray
        Numerator array.
    y : numpy.ndarray
        Denominator array.
    default : float, optional
        Default value to use when denominator is zero. Default is 0.0.
    
    Returns
    -------
    numpy.ndarray
        Result of safe division operation.
    
    Notes
    -----
    - Prevents division by zero errors in hydrological calculations
    - Provides consistent handling of undefined mathematical operations
    - Used throughout CWatM for ratio and rate calculations
    - Maintains numerical stability in model computations
    """
    # y can also be a scalar (e.g. a parameter given as a number in the settings)
    zero = y == 0.
    # 1 and not 1.0: keeps the type of y
    z = x / np.where(zero, 1, y)
    # x and y both scalars: the result is a scalar
    if np.ndim(z) == 0:
        return default if zero else z
    z[zero] = default

    #with np.errstate(invalid='ignore', divide='ignore'):
    #    z = np.where(y > 0., x/y, default)
    # have to solve this without err handler to get the error message back

    return z
