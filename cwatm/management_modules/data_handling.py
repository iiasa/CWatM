# -------------------------------------------------------------------------
# Name:        Data handling
# Purpose:     Transforming netcdf to numpy arrays, checking mask file
#
# Author:      PB
# Created:     13/07/2016 
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import calendar
import difflib  # to check the closest word in settingsfile, if an error occurs
import glob
import math
import os
import re
import warnings

from netCDF4 import Dataset, num2date, date2num, date2index
#from osgeo import gdal
#from osgeo import gdalconst
#from osgeo import osr
import rasterio

from . import globals
from cwatm.management_modules.checks import *
from cwatm.management_modules.dynamicModel import *
from cwatm.management_modules.messages import *
from cwatm.management_modules.replace_pcr import *
from cwatm.management_modules.timestep import *

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
        col.append(int((coord[i * 2] - maskmapAttr['x']) * maskmapAttr['invcell']))
        row.append(int((maskmapAttr['y'] - coord[i * 2 + 1]) * maskmapAttr['invcell']))

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

            #print box

            print("%2s %-17s %10s %8s" % ("No", "Name", "time[s]", "%"))

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
    invcell = round(1/cell, 0)
    # getgeotransform only delivers single precision!
    if invcell == 0:
        invcell = 1/cell
    cell = 1 / invcell
    if (x - int(x)) != 0.:
        if abs(x - int(x)) > 1e9:
            x = 1/round(1/(x - int(x)), 4) + int(x)
        else:
            x = round(x, 6)
    if (y - int(y)) != 0.:
        if abs(y - int(y)) > 1e9:
            y = 1 / round(1 / (y - int(y)), 4) + int(y)
        else:
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

    value = list(nf1.variables.items())[-1][0]  # get the last variable name
    if value in ["X", "Y", "x", "y", "lon", "lat", "time","crs"]:
        numbervars = len(list(nf1.variables.items()))
        for i in range(2, numbervars+1):
            value = list(nf1.variables.items())[-i][0]
            if not (value in ["X", "Y", "x", "y", "lon", "lat", "time","crs"]): break
    return value

def loadsetclone(self, name):
    """
    Load and set the clone map that defines the model domain.
    
    The clone map is the fundamental spatial reference for CWatM, defining
    the model grid, coordinate system, and computational domain. This function
    loads the clone map from various formats (NetCDF, GeoTIFF), extracts spatial
    attributes, and sets up the global spatial reference system used throughout
    the model.
    
    Parameters
    ----------
    name : str
        Path to the clone map file. Can be NetCDF or GeoTIFF format.
        The binding key for the clone map in the configuration.
    
    Returns
    -------
    None
        Sets up global spatial reference and mask attributes.
    
    Notes
    -----
    The clone map determines:
    - Model grid dimensions and spatial resolution
    - Coordinate reference system and geotransformation
    - Active model domain (non-NoData cells)
    - Spatial attributes for all subsequent data loading
    
    This function must be called before any other spatial data operations.
    It populates the global maskmapAttr dictionary and sets the model's
    spatial framework.
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
            nf1 = Dataset(filename, 'r')

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
            if y1 < ylast:  y1, ylast = ylast, y1

            cellSize = np.abs(x2 - x1)
            invcell = round(1/cellSize)
            if invcell == 0: invcell = 1/cellSize
            nrRows = int(0.5 + np.abs(ylast - y1) * invcell + 1)
            nrCols = int(0.5 + np.abs(xlast - x1) * invcell + 1)
            x = x1 - cellSize / 2
            y = y1 + cellSize / 2

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                mapnp = np.array(nf1.variables[value][0:nrRows, 0:nrCols])
            nf1.close()
            setmaskmapAttr( x, y, nrCols, nrRows, cellSize)
            flagmap = True

        except:
            # load geotiff
            try:

                filename = cbinding(name)
                #nf3 = gdal.Open(filename, gdalconst.GA_ReadOnly)
                #geotransform1 = nf3.GetGeoTransform()
                nf2 =  rasterio.open(filename)
                geotransform = nf2.transform

                geotrans.append(geotransform)
                setmaskmapAttr(geotransform[2], geotransform[5], nf2.shape[1], nf2.shape[0], geotransform[0])
                #setmaskmapAttr( geotransform[0], geotransform[3], nf2.RasterXSize, nf2.RasterYSize, geotransform[1])
                #band = nf2.GetRasterBand(1)
                #bandtype = gdal.GetDataTypeName(band.DataType)
                #mapnp = band.ReadAsArray(0, 0, nf3.shape[1], nf3.shape[0])
                mapnp = nf2.read(1)
                # 10 because that includes all valid LDD values [1-9]
                mapnp[mapnp > 10] = 0
                mapnp[mapnp < -10] = 0
                addtoversiondate(filename)
                flagmap = True

            except:
                raise CWATMFileError(filename,msg = "Error 201: File reading Error\n", sname=name)

    else:
        msg = "Error 103: Maskmap: " + filename + " is not a valid mask map nor valid coordinates nor valid point\n"
        msg +="Or there is a whitespace or undefined character in Maskmap"
        raise CWATMError(msg)



    # put in the ldd map
    # if there is no ldd at a cell, this cell should be excluded from modelling

    maskldd = loadmap('Ldd', compress = False)
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
    Convert 2D mask array to compressed 1D format for CWatM processing.
    
    Transforms a full 2D boolean mask to the compressed 1D format used
    internally by CWatM. This compression removes NoData cells and creates
    efficient storage for hydrological computations, significantly reducing
    memory usage and computation time for sparse domains.
    
    Parameters
    ----------
    mask2D : numpy.ndarray
        2D boolean array where True indicates active model cells.
    xleft : float
        X-coordinate of the left edge of the domain.
    yup : float
        Y-coordinate of the upper edge of the domain.
    
    Returns
    -------
    numpy.ndarray
        1D compressed mask array containing only active cells.
    
    Notes
    -----
    - Uses global spatial reference attributes from maskmapAttr
    - Creates mapping between 2D grid positions and 1D compressed indices
    - Essential for CWatM's efficient spatial data handling
    - All subsequent spatial operations use this compressed format
    """
    """
    load a static map either value or pc raster map or netcdf

    :param mask2D: 2D array of new mask
    :param xleft: left lon coordinate
    :param yup: upper lat coordinate
    :return:  new mask map
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
    Generate version and timestamp information for output files.
    
    Creates standardized version metadata that includes git information,
    build timestamp, and model version. This information is embedded in
    output NetCDF files to ensure full traceability and reproducibility
    of model results.
    
    Parameters
    ----------
    filename : str
        Name of the file being created (used in history string).
    history : str, optional
        Additional history information to include. Default is empty string.
    
    Returns
    -------
    str
        Formatted history string containing version, timestamp, and git info.
    
    Notes
    -----
    The version string includes:
    - CWatM version number
    - Git commit hash and branch information
    - Whether the build has uncommitted changes ("dirty" vs "verified")
    - Build timestamp
    - User-provided history information
    
    This ensures complete provenance tracking for all model outputs.
    """

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
    ii =1


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
        nf1 = Dataset(filename, 'r')
        crs = nf1.variables["crs"]
        #nf1.close()
    except:
        msg = "\nWarning: Projection not defined as crs variable in: " + filename + "\n"
        print(msg)
    return crs


def loadmap(name, lddflag=False,compress = True, local = False, cut = True):
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
        flagmap = False
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
            nf1 = Dataset(filename, 'r')
            cut0, cut1, cut2, cut3 = mapattrNetCDF(filename, check = False)

            # load netcdf map but only the rectangle needed
            value = getvariablename(nf1)

            #if (nf1.variables[maskmapAttr['coordy']][0] - nf1.variables[maskmapAttr['coordy']][-1]) < 0:
            if (nf1.variables[maskmapAttr['coordy']][0] - nf1.variables[maskmapAttr['coordy']][-1]) < 0:
                msg = "Error 202: Latitude is in wrong order\n"
                raise CWATMFileError(filename, msg)

            if not timestepInit:
                #with np.errstate(invalid='ignore'):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    # in order to ignore some invalid value comments
                    if cut:
                        mapnp = nf1.variables[value][cut2:cut3, cut0:cut1].astype(np.float64)
                    else:
                        mapnp = nf1.variables[value][:]
            else:
                if 'time' in nf1.variables:
                    timestepI = Calendar(timestepInit[0])
                    if type(timestepI) is datetime.datetime:
                        timestepI = date2num(timestepI,nf1.variables['time'].units)
                    else: timestepI = int(timestepI) -1

                    if not(timestepI in nf1.variables['time'][:]):
                        msg = "Error 105 time step " + str(int(timestepI)+1)+" not stored in "+ filename
                        raise CWATMError(msg)
                    itime = np.where(nf1.variables['time'][:] == timestepI)[0][0]
                    if cut:
                        mapnp = nf1.variables[value][itime,cut2:cut3, cut0:cut1]
                    else:
                        mapnp = nf1.variables[value][itime][:]
                else:
                    if cut:
                        mapnp = nf1.variables[value][cut2:cut3, cut0:cut1]
                    else:
                        mapnp = nf1.variables[value][:]

            try:
                history = nf1.getncattr('history')
            except:
                history = ""
            addtoversiondate(filename,history)
            nf1.close()

        except:

            filename = cbinding(name)
            try:
                #nf2 = gdal.Open(filename, gdalconst.GA_ReadOnly)
                #band = nf2.GetRasterBand(1)
                #mapnp = band.ReadAsArray(0, 0, nf2.RasterXSize, nf2.RasterYSize).astype(np.float64)
                nf2 = rasterio.open(filename)
                mapnp = nf2.read(1)

                # if local no cut
                if not local:
                    if cut:
                        cut0, cut1, cut2, cut3 = mapattrTiff(nf2)
                        mapnp = mapnp[cut2:cut3, cut0:cut1]
                addtoversiondate(filename)
            except:
                msg = "Error 203: File does not exists"
                raise CWATMFileError(filename,msg,sname=name)

        try:
            if any(maskinfo) and compress: mapnp.mask = maskinfo['mask']
        except:
            ii=0


        if compress:
            mapC = compressArray(mapnp,name=filename)
            if Flags['check']:
                checkmap(name, filename, mapnp)
        else:
            mapC = mapnp
            if Flags['check'] and not(name == "Ldd"):
                checkmap(name, filename, mapnp)


    return mapC


# -----------------------------------------------------------------------
# Compressing to 1-dimensional numpy array
# -----------------------------------------------------------------------

def compressArray(map, name="None", zeros = 0.):
    """
    Compress 2D array to 1D format by removing inactive cells.
    
    Core data compression function that converts full 2D spatial arrays
    to the efficient 1D compressed format used throughout CWatM. This
    compression removes NoData cells and cells outside the model domain,
    significantly reducing memory usage and computational overhead.
    
    Parameters
    ----------
    map : numpy.ndarray
        2D spatial array to be compressed.
    name : str, optional
        Variable name for error reporting. Default is "None".
    zeros : float, optional
        Value to use for replacing zero values. Default is 0.0.
    
    Returns
    -------
    numpy.ndarray
        1D compressed array containing only active model cells.
    
    Notes
    -----
    - Uses global maskinfo for determining active cells
    - Preserves spatial relationships through index mapping
    - Essential for CWatM's memory-efficient spatial operations
    - All hydrological calculations use this compressed format
    - Zero replacement helps avoid numerical issues in computations
    """

    if map.shape != maskinfo['mask'].shape:
        msg = "Error 105: " + name + " has a different shape than area or ldd \n"
        raise CWATMError(msg)
    
    mapnp1 = np.ma.masked_array(map, maskinfo['mask'])
    mapC = np.ma.compressed(mapnp1)
    # if fill: mapC[np.isnan(mapC)]=0
    if name != "None":
        if np.max(np.isnan(mapC)):
            msg = "Error 106:" + name + " has less valid pixels than area or ldd \n"
            #raise CWATMError(msg)
            mapC[np.isnan(mapC)] = 0.000001
            # test if map has less valid pixel than area.map (or ldd)
    # if a value is bigger or smaller than 1e20, -1e20 than the standard value is taken
    mapC[mapC > 1.E20] = zeros
    mapC[mapC < -1.E20] = zeros

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
    if checkint == "int16" or checkint == "int32":
        dmap[dmap.mask] = -9999
    elif checkint == "int8":
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
    Generate standard NetCDF metadata attributes for CWatM outputs.
    
    Creates a dictionary of global attributes that provide essential
    information about the model run, including version, contact information,
    and data description. These attributes ensure proper documentation
    and traceability of CWatM output files.
    
    Returns
    -------
    dict
        Dictionary of NetCDF global attributes including title, institution,
        source, history, and contact information.
    
    Notes
    -----
    Standard attributes include:
    - title: Descriptive name for the dataset
    - institution: Organization responsible for the data
    - source: Model version and configuration information  
    - history: Processing history and timestamps
    - contact: Maintainer contact information
    
    These attributes follow CF conventions and support data discovery
    and provenance tracking in scientific workflows.
    """
    """
    get the map metadata from precipitation netcdf maps
    """

    try:
        name = cbinding('PrecipitationMaps')
        name1 = glob.glob(os.path.normpath(name))[0]
        nf1 = Dataset(name1, 'r')
        for var in nf1.variables:
           metadataNCDF[var] =  {k: v for k, v in nf1.variables[var].__dict__.items() if k != '_FillValue'}
        nf1.close()
    except:
        msg = "Error 204: Trying to get metadata from netcdf\n"
        raise CWATMFileError(cbinding('PrecipitationMaps'),msg)


def readCoord(name):
    """
    Read coordinate information from various raster file formats.
    
    Extracts spatial reference information including extent, resolution,
    and coordinate system from raster files. Supports multiple formats
    and provides unified coordinate information for spatial data alignment.
    
    Parameters
    ----------
    name : str
        Path to the raster file or configuration binding key.
    
    Returns
    -------
    tuple
        Coordinate information (extent, resolution, projection details).
    
    Notes
    -----
    - Supports GeoTIFF, NetCDF, and other GDAL-supported formats
    - Extracts geotransform and projection information
    - Used for spatial consistency checking and data alignment
    - Provides foundation for coordinate transformations
    """

    namenc = os.path.splitext(name)[0] + '.nc'

    try:
        nf1 = Dataset(namenc, 'r')
        nc = True
    except:
        nc = False
    if nc:
        lat, lon, cell, invcell, rows, cols = readCoordNetCDF(namenc)
    else:
        #raster = gdal.Open(name)
        #rows = raster.RasterYSize
        #cols = raster.RasterXSize
        #gt = raster.GetGeoTransform()

        raster = rasterio.open(name)
        gt = raster.transform
        rows = raster.shape[0]
        cols = raster.shape[1]

        #gdal -> rasterio  0->2 3->5, 1->0
        #setmaskmapAttr(geotransform[2], geotransform[5], nf2.shape[1], nf2.shape[0], geotransform[0])
        #gdal
        # setmaskmapAttr( geotransform[0], geotransform[3], nf2.RasterXSize, nf2.RasterYSize, geotransform[1])

        cell = gt[0]
        invcell = round(1.0 / cell, 0)
        if invcell == 0: invcell = 1. / cell

        # getgeotransform only delivers single precision!
        cell = 1 / invcell
        lon = gt[2]
        lat = gt[5]
        #lon = 1 / round(1 / (x1 - int(x1)), 4) + int(x1)
        #lat = 1 / round(1 / (y1 - int(y1)), 4) + int(y1)

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
            nf1 = Dataset(name, 'r')
        except:
            msg = "Error 205: Checking netcdf map \n"
            raise CWATMFileError(name,msg)
    else:
        # if subroutine is called already from inside a try command
        nf1 = Dataset(name, 'r')

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

    rows = nf1.variables[maskmapAttr['coordy']].shape[0]
    cols = nf1.variables[maskmapAttr['coordx']].shape[0]

    lon0 = nf1.variables[maskmapAttr['coordx']][0]
    lon1 = nf1.variables[maskmapAttr['coordx']][1]
    lat0 = nf1.variables[maskmapAttr['coordy']][0]
    latlast = nf1.variables[maskmapAttr['coordy']][-1]
    nf1.close()
    # swap to make lat0 the biggest number
    if lat0 < latlast:
        lat0, latlast = latlast, lat0

    cell = round(np.abs(lon1 - lon0),8)
    invcell = round(1.0 / cell, 0)
    if invcell == 0: invcell = 1./cell

    lon = round(lon0 - cell / 2,8)
    lat = round(lat0 + cell / 2,8)

    return lat,lon, cell,invcell,rows,cols

def readCalendar(name):
    """
    Extract calendar information from NetCDF time dimensions.
    
    Reads time coordinate metadata to determine the calendar system
    used in NetCDF files. This is essential for proper temporal
    alignment and date calculations in CWatM.
    
    Parameters
    ----------
    name : str
        Path to NetCDF file or configuration binding key.
    
    Returns
    -------
    str
        Calendar type ('standard', 'gregorian', '365_day', etc.).
    
    Notes
    -----
    - Supports CF-compliant calendar conventions
    - Defaults to 'standard' calendar if not specified
    - Critical for accurate temporal data processing
    - Used by date conversion and time indexing functions
    """
    nf1 = Dataset(name, 'r')
    dateVar['calendar'] = nf1.variables['time'].calendar
    nf1.close()

def checkMeteo_Wordclim(meteodata, wordclimdata):
    """
    Validate consistency between meteorological and WorldClim climatology data.
    
    Performs quality control checks to ensure that meteorological forcing
    data is reasonable compared to long-term climatological averages from
    WorldClim. This helps detect data quality issues and potential errors
    in meteorological inputs.
    
    Parameters
    ----------
    meteodata : numpy.ndarray
        Current meteorological data values.
    wordclimdata : numpy.ndarray
        WorldClim climatological reference values.
    
    Returns
    -------
    bool or numpy.ndarray
        Validation results indicating data quality status.
    
    Notes
    -----
    - Compares current values against climatological norms
    - Helps identify unrealistic meteorological data
    - Supports quality assurance in operational modeling
    - Can flag potential data processing errors
    """

    try:
        nf1 = Dataset(meteodata, 'r')
    except:
        msg = "Error 206: Checking netcdf map \n"
        raise CWATMFileError(meteodata, msg)

    if 'lon' in list(nf1.variables.keys()):
        xy = ["lon", "lat"]
    else:
        xy = ["x", "y"]

    lonM0 = nf1.variables[xy[0]][0]
    lon1 = nf1.variables[xy[0]][1]

    cellM = round(np.abs(lon1 - lonM0) / 2.,8)
    lonM0 = round(lonM0 - cellM,8)

    lonM1 = round(nf1.variables[xy[0]][-1] + cellM,8)
    latM0 = nf1.variables[xy[1]][0]
    latM1 = nf1.variables[xy[1]][-1]
    nf1.close()

    # swap to make lat0 the biggest number
    if latM0 < latM1:
        latM0, latM1 = latM1, latM0
    latM0 = round(latM0 + cellM,8)
    latM1 = round(latM1 - cellM,8)

    # load Wordclima data
    try:
        nf1 = Dataset(wordclimdata, 'r')
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
    nf1.close()
    # swap to make lat0 the biggest number
    if latW0 < latW1:
        latW0, latW1 = latW1, latW0
    latW0 = round(latW0 + cellW,8)
    latW1 = round(latW1 - cellW,8)
    # calculate the controll variable
    contr1 = (lonM0 + lonM1 + latM0 + latM1)
    contr2 = (lonW0 + lonW1 + latW0 + latW1)
    contr = abs(round(contr1 - contr2,5))

    check = True
    if contr > 0.00001:
        #msg = "Data from meteo dataset and Wordclim dataset does not match"
        #raise CWATMError(msg)
        check  = False

    return check

def mapattrNetCDF(name, check=True):
    """
    Extract complete spatial attributes from NetCDF files.
    
    Comprehensive function for reading all spatial metadata from NetCDF
    files including dimensions, coordinates, projection, and extent.
    Provides complete spatial reference information needed for data
    alignment and processing.
    
    Parameters
    ----------
    name : str
        Path to NetCDF file or configuration binding key.
    check : bool, optional
        If True, validate spatial consistency with model domain.
        Default is True.
    
    Returns
    -------
    dict
        Complete spatial attribute dictionary with coordinate information,
        dimensions, and transformation parameters.
    
    Notes
    -----
    - Handles both meteorological and static NetCDF files
    - Extracts coordinate reference system information
    - Validates spatial consistency when check=True
    - Used for proper data alignment and processing
    """

    lat, lon, cell, invcell, rows, cols = readCoord(name)

    if maskmapAttr['invcell'] != invcell:
        msg = "Error 107: Cell size different in maskmap: " + \
            binding['MaskMap'] + " and: " + name
        raise CWATMError(msg)

    xx = maskmapAttr['x']
    yy = maskmapAttr['y']
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
    Extract spatial attributes from GeoTIFF files using GDAL.
    
    Reads complete spatial reference information from GeoTIFF files
    including geotransform, projection, dimensions, and extent.
    Provides unified spatial metadata extraction for raster data.
    
    Parameters
    ----------
    nf2 : gdal.Dataset
        Opened GDAL dataset object for the GeoTIFF file.
    
    Returns
    -------
    dict
        Spatial attribute dictionary containing coordinate reference
        information, dimensions, and transformation parameters.
    
    Notes
    -----
    - Extracts geotransform coefficients
    - Reads projection and coordinate system information
    - Handles various GeoTIFF conventions and formats
    - Provides foundation for raster data integration
    """

    geotransform = nf2.transform
    x1 = geotransform[2]
    y1 = geotransform[5]
    cellSize = geotransform[0]

    #invcell = round(1/cellSize,0)
    if cellSize > 1:
        invcell = 1 / cellSize
    else:
        invcell = round(1/cellSize,0)

    # getgeotransform only delivers single precision!
    cellSize = 1 / invcell
    if (x1-int(x1)) != 0:
        x1 = 1/round(1/(x1-int(x1)),4) + int(x1)
    if (y1-int(y1)) != 0:
        y1 = 1 / round(1 / (y1 - int(y1)), 4) + int(y1)

    if maskmapAttr['invcell'] != invcell:
        msg = "Error 108: Cell size different in maskmap: " + \
            binding['MaskMap']
        raise CWATMError(msg)


    x = x1 - cellSize / 2
    y = y1 + cellSize / 2
    cut0 = int(0.01 + np.abs(maskmapAttr['x'] - x) * invcell)
    cut2 = int(0.01 + np.abs(maskmapAttr['y'] - y) * invcell)

    cut1 = cut0 + maskmapAttr['col']
    cut3 = cut2 + maskmapAttr['row']

    return cut0, cut1, cut2, cut3


def multinetdf(meteomaps, usebuffer,startcheck = 'dateBegin'):
    """
    Set up multiple NetCDF meteorological files for efficient reading.
    
    Initializes data structures and index mappings for reading from
    multiple meteorological NetCDF files. Optimizes data access patterns
    and supports buffering strategies for improved I/O performance during
    long model runs.
    
    Parameters
    ----------
    meteomaps : list
        List of meteorological variable names to process.
    usebuffer : bool
        If True, enable data buffering for improved performance.
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
    - Sets up buffering strategies based on available memory
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

        for filename in nameall:

            # --- Netcdf -------------
            try:
                nf1 = Dataset(filename, 'r')
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
            datestart = num2date(int(round(nctime[:][0],0)), units=nctime.units,calendar=nctime.calendar)

            # sometime daily records have a strange hour to start with -> it is changed to 0:00 to have the same record
            datestart = datestart.replace(hour=0, minute=0)
            datestartint = int(round(nctime[0].data.tolist(),0)) // datediv
            datelen= len(nctime[:])
            dateendint = datestartint + datelen - 1
            dateend = num2date(dateendint, units=nctime.units, calendar=nctime.calendar)
            #dateend = num2date(int(round(nctime[:][-1],0)), units=nctime.units, calendar=nctime.calendar)
            #dateendint = int(round(nctime[:][-1].data.tolist(),0)) // datediv

            dateend = dateend.replace(hour=0, minute=0)
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
            cutcheckmask = maskinfo['shape'][0] * maskinfo['shape'][1]
            shapey = nf1.variables[value].shape[1]
            shapex = nf1.variables[value].shape[2]
            cutcheckmap = shapey * shapex
            cutcheck = True
            if cutcheckmask == cutcheckmap: cutcheck = False

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

            # calculate buffer
            if not(usebuffer):
                buffer = [0,0,0,0]
            else:
                buffer = 1
                #          buffer1
                #         ---------
                # buffer3¦        ¦ buffer4
                #        ¦        ¦
                #         ---------
                #          buffer2
                buffer4, buffer2 = [1,1]
                #if the input map should be used until the last column there is no buffer
                if shapex == cutmapFine[1]:
                    buffer4 = 0
                # if the input map should be used at the last row there is no buffer
                if shapey == cutmapFine[3]:
                    buffer2 = 0
                # if the input map should be used at the first row or column there is no buffer
                if (cutmapFine[2] == 0) and (cutmapFine[0] == 0):
                     buffer1 = 0
                     buffer3 = 0
                # if the input map should be used at the first row there is no buffer
                elif cutmapFine[2] == 0:
                    buffer1 = 0
                    buffer3 = -1
                # if the input map should be used at the first column there is no buffer
                elif cutmapFine[0] == 0:
                    buffer1 = -1
                    buffer3 = 0
                else:
                    buffer1 = -1
                    buffer3 = -1
                buffer = [buffer1,buffer2,buffer3,buffer4]


            if startfile == 0:  # search first file where dynamic run starts
                if (dateendint >= startint): # if enddate of a file is bigger than the start of run
                    # and (datestartint <= startint):  # remove thiis, because glacier maps could start latter, than the day of the year of first year is  use
                    startfile = 1
                    #indstart = (start - datestart).days
                    indstart = startint - datestartint

                    #indend = (dateend -datestart).days
                    indend = dateendint - datestartint

                    # value varname of netcdf as index: 5
                    # cutmap as index 6
                    # name of y or latitude: 7
                    # if map is turned )North is down): 8
                    # buffer atound the map for interpolation: 9
                    # shapey, shapex : shape y and y of total map  10, 11
                    # Number - no of meteofile  12
                    meteolist[startfile-1] = [filename,indstart,indend, start,dateend,value,cutcheck,yy,turn_latitude, buffer, shapey, shapex,no]
                    inputcounter[maps] = indstart  # startindex of timestep 1
                    startint = dateendint + 1
                    start = num2date(startint * datediv, units=nctime.units, calendar=nctime.calendar)
                    no += 1

                    # counter is set to a minus value - for some maps (e.g. glacier) if the counter is negativ
                    # the doy of a year of first year is loaded -> to use runs  before glacier maps are calculated
            else:
                if (datestartint >= startint) and (datestartint < endint ):
                    startfile += 1
                    indstart = startint - datestartint
                    indend = dateendint - datestartint
                    #meteolist[startfile - 1] = [filename, indstart,indend, start, dateend,value,cutcheck,yy,turn_latitude, buffer, shapey, shapex,no,
                    #                            AsyncReader(filename,value)]
                    meteolist[startfile - 1] = [filename, indstart,indend, start, dateend,value,cutcheck,yy,turn_latitude, buffer, shapey, shapex,no]

                    #start = dateend + datetime.timedelta(days=1)
                    #start = start.replace(hour=0, minute=0)
                    startint = dateendint + 1
                    start = num2date(startint * datediv, units=nctime.units, calendar=nctime.calendar)
                    no += 1

            nf1.close()
            # --- End Netcdf -------------
        meteofiles[maps] =  meteolist
        flagmeteo[maps] = 0

    return



def readmeteodata(name, date, value='None', addZeros=False, zeros=0.0, mapsscale=True, 
                  buffering=False, extendback=False, glacier=False):
    """
    Read meteorological forcing data for specific time steps.
    
    Primary function for loading time-varying meteorological data during
    model execution. Handles temporal indexing, data extraction, scaling,
    and format conversion for various meteorological variables. Supports
    efficient buffering and caching strategies for improved performance.
    
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
    buffering : bool, optional
        If True, use buffered reading for performance. Default is False.
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
    - Implements efficient caching and buffering
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
        value = meteofiles[name][flagmeteo[name]][5]
    cutcheck = meteofiles[name][flagmeteo[name]][6]
    yy = meteofiles[name][flagmeteo[name]][7]
    turn_latitude = meteofiles[name][flagmeteo[name]][8]

    if cutcheck:
        loc = [cutmapFine[2],cutmapFine[3],cutmapFine[0], cutmapFine[1]]
        if buffering:
            buffer = meteofiles[name][flagmeteo[name]][9]
            loc = loc + buffer
    else:
        loc = [0,meteofiles[name][flagmeteo[name]][10], 0, meteofiles[name][flagmeteo[name]][11]]

        if glacier:
            loc = maskmapAttr['cut']


    # +++++++++++++++ Netcdf ++++++++++++++++++++++

    try:
       nf1 = Dataset(filename, 'r')
    except:
        msg = "Error 211: Netcdf map stacks: \n"
        raise CWATMFileError(filename,msg, sname = name)

    mapnp = nf1.variables[value][idx, loc[0]:loc[1],loc[2]:loc[3]]

    nf1.close()
    """
    reader = meteofiles[name][flagmeteo[name]][13]
    mapnp = reader.read_timestep(idx,loc)
    
    """
    # +++++++++++++++ Netcdf End++++++++++++++++++++++

    mapnp = mapnp.astype(np.float64)

    if turn_latitude:
        mapnp = np.flipud(mapnp)
    try:
        mapnp.mask.all()
        mapnp = mapnp.data
        mapnp[mapnp>1e15] = np.nan
    except:
        ii =1


    # add zero values to maps in order to supress missing values
    if addZeros: mapnp[np.isnan(mapnp)] = zeros

    if mapsscale:  # if meteo maps have the same extend as the other spatial static maps -> meteomapsscale = True
        if maskinfo['shapeflat'][0]!= mapnp.size:
            msg = "Error 109: " + name + " has less or more valid pixels than the mask map \n"
            msg += "if it is the ET maps, it might be from another run with different mask. Please look at the option: calc_evaporation"
            raise CWATMWarning(msg)

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
       nf1 = Dataset(filename, 'r')
    except:
        msg = "Error 212: Netcdf map stacks: \n"
        raise CWATMFileError(filename,msg, sname = namebinding)

    if value == "None":
        value = getvariablename(nf1)

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
            if useDaily == "yearly":
                date = datetime.datetime(date.year, int(1), int(1))
#             if useDaily == "monthly":
                date = datetime.datetime(date.year, date.month, int(1))

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

    # if first day store the name and the date
    if dateVar["curr"] == 0:
        try:
            history = nf1.getncattr('history')
        except:
            history = ""
        addtoversiondate(filename, history)


    #checkif latitude is reversed
    turn_latitude = False
    try:
        if (nf1.variables['lat'][0] - nf1.variables['lat'][-1]) < 0:
           turn_latitude = True
           mapnp = nf1.variables[value][idx].astype(np.float64)
           mapnp = np.flipud(mapnp)
    except:
       ii = 1
    if 'Glacier' in namebinding:
        cutcheckmask = maskinfo['shape'][0] * maskinfo['shape'][1]
        cutcheckmap = nf1.variables[value].shape[1] * nf1.variables[value].shape[2]
        cut = True
        if cutcheckmask == cutcheckmap: cut = False

    if cut:
        if 'maps_cut_individually' in option:
            if checkOption('maps_cut_individually'):
                cutmap[0], cutmap[1], cutmap[2], cutmap[3] = mapattrNetCDF(name)
        if turn_latitude:
            mapnp = mapnp[cutmap[2]:cutmap[3], cutmap[0]:cutmap[1]]
        else:
            mapnp = nf1.variables[value][idx, cutmap[2]:cutmap[3], cutmap[0]:cutmap[1]].astype(np.float64)
    else:
        if not(turn_latitude):
            mapnp = nf1.variables[value][idx].astype(np.float64)
    try:
        mapnp.mask.all()
        mapnp = mapnp.data
    except:
        ii =1
    nf1.close()

    # add zero values to maps in order to supress missing values
    if addZeros: mapnp[np.isnan(mapnp)] = zeros
    if not compress:
        return mapnp

    if maskinfo['shapeflat'][0]!= mapnp.size:
        msg = "Error 110: " + name + " has less or more valid pixels than the mask map \n"
        raise CWATMWarning(msg)

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
       nf1 = Dataset(filename, 'r')
    except:
        msg = "Error 213: Netcdf map stacks: \n"
        raise CWATMFileError(filename,msg)
    if value == "None":
        value = getvariablename(nf1)

    '''
    if (nf1.variables[maskmapAttr['coordy']][0] - nf1.variables[maskmapAttr['coordy']][-1]) < 0:
        msg = "Error 111: Latitude is in wrong order\n"
        raise CWATMFileError(filename, msg)
    '''

    mapnp = nf1.variables[value][cutmap[2]:cutmap[3], cutmap[0]:cutmap[1]].astype(np.float64)
    # store date
    if counter == 0:
        try:
            history = nf1.getncattr('history')
        except:
            history = ""
        addtoversiondate(filename, history)

    nf1.close()

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
       nf1 = Dataset(filename, 'r')
    except:
        msg = "Error 213: Netcdf map stacks: \n"
        raise CWATMFileError(filename,msg)
    if value == "None":
        value = getvariablename(nf1) # get the last variable name

    mapnp = nf1.variables[value][month,cutmap[2]:cutmap[3], cutmap[0]:cutmap[1]].astype(np.float64)
    nf1.close()

    mapC = compressArray(mapnp, name=filename)
    if Flags['check']:
        checkmap(value, filename, mapnp)
    return mapC


def readnetcdfInitial(name, value,default = 0.0):
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

    if value == "storGroundwater":
        ii = 1
    filename =  os.path.normpath(name)
    try:
       nf1 = Dataset(filename, 'r')
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
            
            cut0, cut1, cut2, cut3 = mapattrNetCDF(filename, check=False)

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
            
            nf1.close()
            mapC = compressArray(mapnp, name=filename)
            if Flags['check']:
                checkmap(value, filename, mapnp)
            a = globals.inZero
            if mapC.shape != globals.inZero.shape:
                msg = "Error 113: map shape is different than mask shape\n"
                raise CWATMError(msg)
            return mapC
        except:
            #nf1.close()
            msg ="Error 114: ===== Problem reading initial data ====== \n"
            msg += "Initial value: " + value + " is has not the same shape as the mask map\n"
            msg += "Maybe put\"load_initial = False\""
            raise CWATMError(msg)

    else:
        nf1.close()
        msg = "Warning: Initial value: " + value + " is not included in: " + name + " - using default: " + str(default)
        print(CWATMWarning(msg))
        return default

# --------------------------------------------------------------------------------------------

def writenetcdf(netfile, prename, addname, varunits, inputmap, timeStamp, posCnt, flag, flagTime, 
                nrdays=None, dateunit="days", netcdfindex=False):
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
    netcdfindex : bool, optional
        Use NetCDF indexing format. Default is False.
    
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


    # check if it is a modflow grid which has another resolution
    modflow = False
    if "modflow" in prename.lower():
            modflow = True
            row = domain['nrow']
            col = domain['ncol']
            metadataNCDF['modflow_x'] = {}
            metadataNCDF['modflow_x']['standard_name'] = 'X'
            metadataNCDF['modflow_x']['units'] = 'm'
            metadataNCDF['modflow_y'] = {}
            metadataNCDF['modflow_y']['standard_name'] = 'Y'
            metadataNCDF['modflow_y']['units'] = 'm'


    # create real varname with variable name + time depending name e.g. discharge + monthavg
    varname = prename + addname

    # save only index values:
    if netcdfindex:
        netfile = netfile.split(".")[0] + "_index.nc"
    #remove ' in the name. Can happen under Linux
    #netfile = netfile.replace("'","")

    if not flag:
        nf1 = Dataset(netfile, 'w', format='NETCDF4')

        # general Attributes
        settings = os.path.realpath(settingsfile[0])
        nf1.settingsfile = settings + ": " + xtime.ctime(os.path.getmtime(settings))
        nf1.history = "Created "+ xtime.ctime(xtime.time())
        nf1.Source_Software = 'CWatM Python: ' + versioning['exe'] + " Git Branch:" + versioning['git']["git_branch"] + " Hash:" + versioning['git']["git_hash"]
        nf1.Platform = versioning['platform']
        nf1.Version = versioning['version']  + ": " + versioning['lastfile']  + " " + versioning['lastdate']
        nf1.institution = cbinding ("institution")
        nf1.title = cbinding ("title")
        nf1.source = 'CWATM output maps'
        nf1.Conventions = 'CF-1.13'

        try:
            nf1.git_commit = versioning['git']["git_hash"]
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
            ii =1


        # put the additional genaral meta data information from the xml file into the netcdf file
        # infomation from the settingsfile comes first
        if prename in metaNetcdfVar:
           for key in metaNetcdfVar[prename]:
                if not (key in list(nf1.__dict__.keys())):
                    if not (key in ["unit", "long_name", "standard_name"]):
                        nf1.__setattr__(key, metaNetcdfVar[prename][key])



        # Dimension
        if modflow:
            lon = nf1.createDimension('x', col)  # x 1000
            longitude = nf1.createVariable('x', 'f8', ('x',))
            for i in metadataNCDF['modflow_x']:
                exec('%s="%s"' % ("longitude." + i, metadataNCDF['modflow_x'][i]))
            lat = nf1.createDimension('y', row)  # x 950
            latitude = nf1.createVariable('y', 'f8', 'y')
            for i in metadataNCDF['modflow_y']:
                exec('%s="%s"' % ("latitude." + i, metadataNCDF['modflow_y'][i]))
            latitude.axis ="Y"

        else:

            latlon = True
            if 'x' in list(metadataNCDF.keys()):
                lon = nf1.createDimension('x', col)  # x 1000
                longitude = nf1.createVariable('x', 'f8', ('x',))
                latlon = False
                for i in metadataNCDF['x']:
                    exec('%s="%s"' % ("longitude." + i, metadataNCDF['x'][i]))
                longitude.axis = "X"
            if 'y' in list(metadataNCDF.keys()):
                lat = nf1.createDimension('y', row)  # x 950
                latitude = nf1.createVariable('y', 'f8', 'y')
                for i in metadataNCDF['y']:
                    exec('%s="%s"' % ("latitude." + i, metadataNCDF['y'][i]))
                latitude.axis = "Y"
            # SHMI meteorogist have a capital X and Y
            if 'X' in list(metadataNCDF.keys()):
                lon = nf1.createDimension('x', col)  # x 1000
                longitude = nf1.createVariable('x', 'f8', ('x',))
                latlon = False
                for i in metadataNCDF['X']:
                    exec('%s="%s"' % ("longitude." + i, metadataNCDF['X'][i]))
                longitude.axis = "X"
            if 'Y' in list(metadataNCDF.keys()):
                lat = nf1.createDimension('y', row)  # x 950
                latitude = nf1.createVariable('y', 'f8', 'y')
                for i in metadataNCDF['Y']:
                    exec('%s="%s"' % ("latitude." + i, metadataNCDF['Y'][i]))
                latitude.axis = "Y"
            if latlon:
                if 'lon' in list(metadataNCDF.keys()):
                    lon = nf1.createDimension('lon', col)
                    longitude = nf1.createVariable('lon', 'f8', ('lon',))
                    for i in metadataNCDF['lon']:
                        exec('%s="%s"' % ("longitude." + i, metadataNCDF['lon'][i]))
                    longitude.axis = "X"
                if 'lat' in list(metadataNCDF.keys()):
                    lat = nf1.createDimension('lat', row)  # x 950
                    latitude = nf1.createVariable('lat', 'f8', 'lat')
                    for i in metadataNCDF['lat']:
                        exec('%s="%s"' % ("latitude." + i, metadataNCDF['lat'][i]))
                    latitude.axis = "Y"

        # projection -> replace by crs  as in cf1.13

        if projection['crs'] != None:
            crs = nf1.createVariable('crs', 'i4',())
            for key in projection['crs'].ncattrs():
                setattr(crs, key, projection['crs'].getncattr(key))

        # Fill variables
        if modflow:
            lats = np.arange(domain['north'], domain['south'] - 1, domain['rowsize'] * -1)
            lons =  np.arange(domain['west'], domain['east']+1, domain['colsize'])
            #lons =  np.linspace(domain['north'] , domain['south'], col, endpoint=False)
            latitude[:] = lats
            longitude[:] = lons

        else:
            cell = maskmapAttr['cell']
            xl = maskmapAttr['x']
            xr = xl + col * cell
            yu = maskmapAttr['y']
            yd = yu - row * cell
            lats = np.linspace(yu, yd, row, endpoint=False)
            lons = np.linspace(xl, xr, col, endpoint=False)

            latitude[:] = lats - cell / 2.0
            longitude[:] = lons + cell /2.0

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
                value = nf1.createVariable(varname, 'f4', ('time', 'y', 'x'), zlib=True, fill_value=1e20,
                                           chunksizes=(1, row, col))
            else:
                latlon = True
                if 'x' in list(metadataNCDF.keys()):
                    latlon = False
                    value = nf1.createVariable(varname, 'f4', ('time', 'y', 'x'), zlib=True, fill_value=1e20,
                                               chunksizes=(1, row, col))
                if 'X' in list(metadataNCDF.keys()):
                    latlon = False
                    value = nf1.createVariable(varname, 'f4', ('time', 'y', 'x'), zlib=True, fill_value=1e20,
                                               chunksizes=(1, row, col))
                if latlon:
                    if netcdfindex:
                        size = maskinfo['mapC'][0]
                        sizeall = len(maskinfo['maskflat'].data)
                        index = nf1.createDimension('index', size)
                        index1 = nf1.createVariable('index', 'i4', 'index')
                        indexlatlon = nf1.createDimension('indexlatlon', sizeall)
                        indexlatlon1 = nf1.createVariable('indexlatlon', 'i4', 'indexlatlon')
                        index1[:] = np.arange(size)
                        indexlatlon1[:] = np.arange(sizeall)
                        latlon = nf1.createVariable("latlon", 'i1', ('indexlatlon'))
                        latlon[:] = maskinfo['maskflat'].data
                        value = nf1.createVariable(varname, 'f4', ('time', 'index'), zlib=True, fill_value=1e20, chunksizes=(1, size))

                    else:
                        if 'lon' in list(metadataNCDF.keys()):
                            #value = nf1.createVariable(varname, 'f4', ('time', 'lat', 'lon'), zlib=True, fill_value=1e20)
                            value = nf1.createVariable(varname, 'f4', ('time', 'lat', 'lon'), zlib=True, fill_value=1e20,chunksizes=(1,row,col))
        else:
          if modflow:
              value = nf1.createVariable(varname, 'f4', ('y', 'x'), zlib=True, fill_value=1e20)
          else:
              latlon = True
              if 'x' in list(metadataNCDF.keys()):
                  latlon = False
                  value = nf1.createVariable(varname, 'f4', ('y', 'x'), zlib=True,fill_value=1e20)
              if 'X' in list(metadataNCDF.keys()):
                  latlon = False
                  value = nf1.createVariable(varname, 'f4', ('y', 'x'), zlib=True,fill_value=1e20)
              if latlon:
                  if netcdfindex:
                      size = maskinfo['mapC'][0]
                      sizeall = len(maskinfo['maskflat'].data)
                      index = nf1.createDimension('index', size)
                      index1 = nf1.createVariable('index', 'i4', 'index')
                      indexlatlon = nf1.createDimension('indexlatlon', sizeall)
                      indexlatlon1 = nf1.createVariable('indexlatlon', 'i4', 'indexlatlon')
                      index1[:] = np.arange(size)
                      indexlatlon1[:] = np.arange(sizeall)
                      latlon = nf1.createVariable("latlon", 'i1', ('indexlatlon'))
                      latlon[:] = maskinfo['maskflat'].data
                      value = nf1.createVariable(varname, 'f4', ('index'), zlib=True, fill_value=1e20)
                  else:
                      if 'lon' in list(metadataNCDF.keys()):
                         # for world lat/lon coordinates
                         value = nf1.createVariable(varname, 'f4', ('lat', 'lon'), zlib=True, fill_value=1e20)

        ## remove as in cf1.13 standard name is defined in a list
        ###value.standard_name = getmeta("standard_name",prename,varname)
        p1 = getmeta("long_name",prename,prename)
        p2 = getmeta("time", addname, addname)
        value.long_name = p1 + p2
        value.units= getmeta("unit",prename,varunits)

        if projection['crs'] != None:
            value.grid_mapping = "crs"

        #for var in list(metadataNCDF.keys()):
        #    if "esri_pe_string" in list(metadataNCDF[var].keys()):
        #        value.esri_pe_string = metadataNCDF[var]['esri_pe_string']

    else:
        nf1 = Dataset(netfile, 'a')

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
        nf1.close()
        print(CWATMWarning(msg))
        return False

    if modflow:
        mapnp = inputmap
    elif netcdfindex:
        if flagTime:
            nf1.variables[varname][posCnt - 1, :] = inputmap
        else:
            # without timeflag
            nf1.variables[varname][:] = inputmap
        nf1.close()
        flag = True
        return flag


    else:
        mapnp[~maskinfo['maskflat']] = inputmap[:]
        #mapnp = mapnp.reshape(maskinfo['shape']).data
        mapnp = mapnp.reshape(maskinfo['shape'])

        if coverresult[0]:
            mapnp = mapnp.reshape(maskinfo['shape']).data
            mapnp = np.where(coverresult[1], mapnp, np.nan)
        else:
            mapnp = mapnp.reshape(maskinfo['shape'])

    if flagTime:
        nf1.variables[varname][posCnt -1, :, :] = mapnp
    else:
        # without timeflag
        nf1.variables[varname][:, :] = mapnp

    nf1.close()
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

    nf1 = Dataset(netfile, 'w', format='NETCDF4')

    # general Attributes
    nf1.settingsfile = os.path.realpath(settingsfile[0])
    nf1.date_created = xtime.ctime(xtime.time())
    nf1.Source_Software = 'CWATM Python'
    nf1.institution = cbinding ("institution")
    nf1.title = cbinding ("title")
    nf1.source = 'CWATM initial conditions maps'
    nf1.Conventions = 'CF-1.6'

    # put the additional genaral meta data information from the xml file into the netcdf file
    # infomation from the settingsfile comes first

    if "initcondition" in metaNetcdfVar:
        for key in metaNetcdfVar["initcondition"]:
            if not (key in list(nf1.__dict__.keys())):
               if not (key in ["unit", "long_name", "standard_name"]):
                   nf1.__setattr__(key, metaNetcdfVar["initcondition"][key])


    # Dimension
    latlon = True
    if 'x' in list(metadataNCDF.keys()):
        latlon = False
        lon = nf1.createDimension('x', col)  # x 1000
        longitude = nf1.createVariable('x', 'f8', ('x',))
        for i in metadataNCDF['x']:
            exec('%s="%s"' % ("longitude." + i, metadataNCDF['x'][i]))
    if 'y' in list(metadataNCDF.keys()):
        lat = nf1.createDimension('y', row)  # x 950
        latitude = nf1.createVariable('y', 'f8', 'y')
        for i in metadataNCDF['y']:
            exec('%s="%s"' % ("latitude." + i, metadataNCDF['y'][i]))
    if 'X' in list(metadataNCDF.keys()):
        latlon = False
        lon = nf1.createDimension('x', col)  # x 1000
        longitude = nf1.createVariable('x', 'f8', ('x',))
        for i in metadataNCDF['X']:
            exec('%s="%s"' % ("longitude." + i, metadataNCDF['X'][i]))
    if 'Y' in list(metadataNCDF.keys()):
        lat = nf1.createDimension('y', row)  # x 950
        latitude = nf1.createVariable('y', 'f8', 'y')
        for i in metadataNCDF['Y']:
            exec('%s="%s"' % ("latitude." + i, metadataNCDF['Y'][i]))
    if latlon:
        if 'lon' in list(metadataNCDF.keys()):
            lon = nf1.createDimension('lon', col)
            longitude = nf1.createVariable('lon', 'f8', ('lon',), fill_value=1e20)
            for i in metadataNCDF['lon']:
                exec('%s="%s"' % ("longitude." + i, metadataNCDF['lon'][i]))
        if 'lat' in list(metadataNCDF.keys()):
            lat = nf1.createDimension('lat', row)  # x 950
            latitude = nf1.createVariable('lat', 'f8', 'lat', fill_value=1e20)
            for i in metadataNCDF['lat']:
                exec('%s="%s"' % ("latitude." + i, metadataNCDF['lat'][i]))

    # projection
    if 'laea' in list(metadataNCDF.keys()):
        proj = nf1.createVariable('laea', 'i4')
        for i in metadataNCDF['laea']:
            exec('%s="%s"' % ("proj." + i, metadataNCDF['laea'][i]))
    if 'lambert_azimuthal_equal_area' in list(metadataNCDF.keys()):
        proj = nf1.createVariable('lambert_azimuthal_equal_area', 'i4')
        for i in metadataNCDF['lambert_azimuthal_equal_area']:
            exec('%s="%s"' % ("proj." + i, metadataNCDF['lambert_azimuthal_equal_area'][i]))

    # Fill variables
    cell = maskmapAttr['cell']
    xl = maskmapAttr['x']
    xr = xl + col * cell
    yu = maskmapAttr['y']
    yd = yu - row * cell
    lats = np.linspace(yu, yd, row, endpoint=False)
    lons = np.linspace(xl, xr, col, endpoint=False)

    latitude[:] = lats - cell / 2.0
    longitude[:] = lons + cell /2.0


    i = 0
    for varname in varlist:
        dtype_str = np.asarray(inputlist[i][0]).dtype.name
        type_args = {'float64':'f8', 'float32':'f4'}
        latlon = True
        if 'x' in list(metadataNCDF.keys()):
            latlon = False
            #value = nf1.createVariable(varname, 'f8', ('y', 'x'), zlib=True,fill_value=1e20)
            value = nf1.createVariable(varname, type_args[dtype_str], ('y', 'x'), zlib=True,fill_value=1e20)
        if 'X' in list(metadataNCDF.keys()):
            latlon = False
            value = nf1.createVariable(varname, type_args[dtype_str], ('y', 'x'), zlib=True, fill_value=1e20)
        if latlon:
            if 'lon' in list(metadataNCDF.keys()):
                # for world lat/lon coordinates
                value = nf1.createVariable(varname, type_args[dtype_str], ('lat', 'lon'), zlib=True, fill_value=1e20)

        value.standard_name= getmeta("standard_name",varname,varname)
        value.long_name= getmeta("long_name",varname,varname)
        value.units= getmeta("unit",varname,"undefined")

        # write values
        mapnp = maskinfo['maskall'].copy()
        help = np.minimum(10e15,np.maximum(-9999., inputlist[i][:]))
        mapnp[~maskinfo['maskflat']] = help
        #mapnp = mapnp.reshape(maskinfo['shape']).data
        mapnp = mapnp.reshape(maskinfo['shape'])

        nf1.variables[varname][:, :] = mapnp
        i += 1



    nf1.close()

# --------------------------------------------------------------------------------------------
# report .tif and .maps

def report(valueIn,name,compr=True):
    """
    Generate standardized output reports for model variables.
    
    Universal reporting function that handles output formatting,
    spatial decompression, and file writing for various CWatM outputs.
    Supports multiple output formats and handles the conversion between
    internal compressed format and standard output formats.
    
    Parameters
    ----------
    valueIn : numpy.ndarray
        Input data to report (typically 1D compressed format).
    name : str
        Variable name for output identification.
    compr : bool, optional
        If True, input data is in compressed format. Default is True.
    
    Returns
    -------
    None
        Generates output files according to configuration settings.
    
    Notes
    -----
    - Handles various output formats (NetCDF, GeoTIFF, text)
    - Manages spatial decompression and coordinate information
    - Supports temporal aggregation and statistical reporting
    - Central function for all model output generation
    """

    filename = os.path.splitext(name)
    pcmap = False
    if filename[1] == ".map":   pcmap = True

    if compr:
        value = decompress(valueIn)
    else:
        value = valueIn
    value = value.data

    checkint = value.dtype.char in np.typecodes['AllInteger']
    ny, nx = value.shape
    #geo = (maskmapAttr['x'], maskmapAttr['cell'], 0.0, maskmapAttr['y'], 0.0, -maskmapAttr['cell'])
    #           0                 1          2          3     4                      5
    geo = (maskmapAttr['cell'], 0.0, maskmapAttr['x'], 0.0, -maskmapAttr['cell'], maskmapAttr['y'] )

    # gdal -> rasterio  0->2 3->5, 1->0
    # setmaskmapAttr(geotransform[2], geotransform[5], nf2.shape[1], nf2.shape[0], geotransform[0])
    #             0          1      2    3        4             5
    #Affine(0.0166666666667, 0.0, 15.0, 0.0, -0.0166666666667, 50.5)

    # gdal
    # setmaskmapAttr( geotransform[0], geotransform[3], nf2.RasterXSize, nf2.RasterYSize, geotransform[1])
    #  0           1            2   3       4        5
    # (15.0, 0.0166666666667, 0.0, 50.5, 0.0, -0.0166666666667)

    if pcmap:
        # if it is a map
        #raster = gdal.GetDriverByName('PCRaster')
        if checkint:
            value = value.astype(np.int32)
            #ds = raster.Create(name, nx, ny, 1, gdal.GDT_Int32, ["PCRASTER_VALUESCALE=VS_NOMINAL"])

        else:
            value = value.astype(np.float32)
            #ds = raster.Create(name, nx, ny, 1, gdal.GDT_Float32, ["PCRASTER_VALUESCALE=VS_SCALAR"])

        with rasterio.open(name,
            mode="w", driver="PCRaster", height=ny, width=nx, count=1,
            dtype=value.dtype, crs="+proj=latlong",  transform=geo,
        ) as new_dataset:
            new_dataset.write(value, 1)

    else: # if is not a .map
        with rasterio.open(name,
            mode="w", driver="GTiff", height=ny, width=nx, count=1,
            dtype=value.dtype, crs="+proj=latlong",  transform=geo,
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
            with open(settingsfile[0]) as f:
                i = 0
                for line in f:
                    i +=1
                    if closest in line:
                        lineclosest = "Line No. " + str(i) + ": "+ line

            if not closest: closest = ["- no match -"]
        else:
            closest = "- no match -"

        msg = "Error 116: No key with the name: \"" + inBinding + "\" in the settings file: \"" + settingsfile[0] + "\"\n"
        msg += "Closest key to the required one is: \""+ closest + "\""
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

            with open(settingsfile[0]) as f:
                i = 0
                for line in f:
                    i +=1
                    if closest in line:
                        lineclosest = "Line No. " + str(i) + ": "+ line

            if not closest: closest = "- no match -"
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
    y1 = y.copy()
    y1[y1 == 0.] = 1.0
    z = x / y1
    z[y == 0.] = default

    #with np.errstate(invalid='ignore', divide='ignore'):
    #    z = np.where(y > 0., x/y, default)
    # have to solve this without err handler to get the error message back

    return z
