# -------------------------------------------------------------------------
# Name: Checks
# Purpose: Validate CWatM input data and provide diagnostic information
#
# Author:      burekpe
# Created:     16/05/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

"""
Input validation and data quality control for CWatM.

This module provides comprehensive validation and diagnostic functions for
CWatM input data, including spatial data checking, file verification, and
detailed reporting of data characteristics. The validation system helps
ensure data quality and compatibility before model execution.

Key Functions
-------------
checkmap : Comprehensive validation and reporting for spatial data
save_check : Save validation results to CSV files
checkfiles : Reference .nc and output .csv file from the arguments of option -c

The module supports comparison against reference datasets and provides
detailed statistics about spatial data including:
- Spatial dimensions and valid cell counts
- Value ranges, means, and distributions  
- Missing value patterns and data completeness
- File modification dates and version tracking
"""

from .globals import *
from netCDF4 import Dataset

def checkmap(name, value, map):
    """
    Comprehensive validation and diagnostic reporting for CWatM input data.
    
    This function performs detailed validation of spatial and scalar input data,
    comparing against mask requirements and providing comprehensive statistics.
    It supports reference dataset comparison and generates detailed reports.
    
    Parameters
    ----------
    name : str
        Name of the variable as specified in settings file
    value : str  
        Filename or path of the input data
    map : numpy.ndarray or scalar
        Input data - either spatial array or scalar value
        
    Notes
    -----
    The function provides comprehensive diagnostics including:
    - Spatial dimensions and cell counts
    - Data validity against mask requirements
    - Statistical summaries (min, mean, max)
    - Zero and non-zero value counts
    - File creation dates and version comparison
    - Reference dataset validation when available
    
    For spatial data, the function:
    - Decompresses 1D arrays to 2D for analysis
    - Validates coverage against the model mask
    - Handles extreme values and missing data
    - Compares valid cell counts with mask requirements
    
    Output is formatted as CSV-compatible text with headers generated
    on first call. Results are stored globally for batch reporting.
    
    The function integrates with CWatM's version control system to
    compare input data against reference datasets when available.
    """

    def load_global_attribute(filename, attribute_name):
        if not os.path.exists(filename):
            return None

        try:
            with Dataset(filename, 'r') as nc_file:
                if attribute_name in nc_file.ncattrs():
                    return str(nc_file.getncattr(attribute_name))
                else:
                    return None
        except Exception:
            return None

    def input2str(inp):
        if isinstance(inp, str):
            return(inp)
        elif isinstance(inp, (int, np.integer)):
            return f'{inp}'
        else:
            if abs(inp) < 100000:
                return f'{inp:.2f}'
            else:
                return f'{inp:.2E}'

    # ------------------------
    # if a netcdf is given after -c then load its list of input files and compare with it
    refile, _ = checkfiles(versioning['checkargs'])
    if versioning['loadinput'] and refile is not None:
        # load discharge netcdf but only attribute version_inputfiles
        ver_input = load_global_attribute(refile,"version_inputfiles")
        versioning['loadinput'] = False

        if ver_input is None:
            # no comparison: the check goes on without the columns Ref Date and Same Date
            if not os.path.exists(refile):
                msg = "Reference file for the check does not exist: " + refile + "\n"
            else:
                msg = "Reference file for the check has no list of input files (global attribute version_inputfiles)\n"
                msg += "or cannot be read: " + refile + "\n"
            msg += "The input maps are checked without comparison to a reference"
            print(CWATMWarning(msg))
        else:
            versioning['refvalue'] = True

            # put information on input data into dictorary: entry = "filename date time;"
            # (the filename may contain spaces) - an entry without date and time is skipped
            versioning['checkinput'] = {}
            for pair in ver_input.split(';'):
                parts = pair.strip().rsplit(' ', 2)
                if len(parts) == 3:
                    versioning['checkinput'][parts[0].strip()] = parts[1] + " " + parts[2]

    # ----------------------------------
    # stored inputdate with date (addtoversiondate in data_handling.py): full filename -> "basename date time;"
    # look for the full filename first (two files with the same name in different folders), then for the name
    datebyfile = {}
    datebyname = {}
    for file1, entry in versioning.get('inputdates', {}).items():
        parts = entry.rstrip(';').rsplit(' ', 2)
        date1 = parts[1] + " " + parts[2]
        datebyfile[os.path.normcase(os.path.normpath(file1))] = date1
        datebyname[parts[0]] = date1

    s = [name]
    iv = os.path.basename(value)
    s.append(iv)
    # check for filename and get date
    createdate = " "
    if value:
        createdate = datebyfile.get(os.path.normcase(os.path.normpath(value)), datebyname.get(iv, " "))
    s.append(createdate)

    # if a reference inputfile is used
    if versioning['refvalue']:
        refdate = versioning['checkinput'].get(iv, "")
        s.append(refdate)
        if refdate != "":
            if refdate == createdate:
                s.append("True")
            else:
                s.append("False")
        else:
            s.append(" ")

    # evaluate maps
    # if it is notr a number but a map (.tif, .nc, .map)
    flagmap = False
    if isinstance(map, np.ndarray):
        flagmap = True
        mapshape = map.shape
        # if compressed (1D, only cells inside the mask) -> 2D map with nan outside the mask
        if len(mapshape) < 2:
            dmap = np.full(maskinfo['shapeflat'], np.nan)
            dmap[~maskinfo['maskflat']] = map
            map = dmap.reshape(maskinfo['shape'])

    if flagmap:
        # missing values => nan: masked cells (netCDF fill value, outside the catchment),
        # -9999 or less (GeoTIFF no data e.g. -9999, -3.4E38) or bigger than 1e20
        map = np.ma.filled(np.ma.asarray(map).astype(np.float64), np.nan)
        map[(map <= -9999) | (map > 1e20)] = np.nan
        mapshape = input2str(map.shape[0]) + "x" + input2str(map.shape[1])

        vmap = ~np.isnan(map)
        if map.shape == maskinfo['shape']:
            # check if there are less valid cells than there should be compared to maskmap
            # reverse maskmap -> every valid cell has a True
            mask = ~maskinfo['mask']
            # count number of must cells
            numbermask = np.count_nonzero(mask)
            # cells with a value inside the mask
            andmap = mask & vmap
            numbermap = np.count_nonzero(andmap)

            # if this is less the the must cell -> problem
            valid = "True"
            if numbermap < numbermask:
                valid = "False"
        else:
            # other extent or resolution than the mask (e.g. meteo maps which are downscaled in readmeteo):
            # cannot be compared with the mask -> number of valid cells of the whole map, valid = "-"
            andmap = vmap
            numbermap = np.count_nonzero(vmap)
            valid = "-"

        # zero/non zero values and min, mean, max of the cells counted in "number valid"
        # (no missing values, no cells outside the mask)
        values = map[andmap]
        numberzero = np.count_nonzero(values == 0)
        numbernonzero = numbermap - numberzero

        if values.size > 0:
            minmap = values.min()
            meanmap = values.mean()
            maxmap = values.max()
        else:
            minmap = meanmap = maxmap = ""

        s.append(mapshape)
        s.append(input2str(numbermap))
        s.append(valid)
        s.append(input2str(numberzero))
        s.append(input2str(numbernonzero))
        s.append("    ")
        s.append(input2str(minmap))
        s.append(input2str(meanmap))
        s.append(input2str(maxmap))
        s.append(os.path.dirname(value))

    # if it is a number
    else:
        #s.append(input2str(float(map)))
        for i in range(10):
            s.append("")




    # if it is checked against a discharge...nc
    if versioning['refvalue']:
        t = ["<30", "<80", "<20","<20","<10",">11", ">11", ">11", ">11", ">11", ">11", ">11", ">11", ">11", ">11", ">11", "<80"]
        h = ["Name", "File/Value", "Create Date","Ref Date","Same Date", "x-y", "number valid", "valid", "Zero values", "NonZero","-----",
             "min", "mean", "max", "Path"]
    # or without comparsion
    else:
        t = ["<30","<80","<20"   ,">11",">11",">11",">11",">11",">11",">11",">11",">11", ">11",">11","<80"]
        h = ["Name","File/Value","Create Date", "x-y", "number valid", "valid", "Zero values", "NonZero","-----",
             "min", "mean", "max", "Path"]

    # first map of this check run (CWATMexe sets versioning['check'] = "" at the start of each check run):
    # header line and row number from 1
    if versioning['check'] == "":
        versioning['checkcount'] = 0
        s1 =""
        # put all the header (keys) in a text line
        for i in range(len(s)):
            s1 += f'{h[i]:{t[i]}}'
            if i<(len(s)-1):
                s1 += ","
            else:
                s1 += "\n"
        print(s1)
        versioning['check'] += s1

    # put all the values in a text file
    s2 = ""
    for i in range(len(s)):
        s2 += f'{s[i]:{t[i]}}'
        if i < (len(s) - 1):
            s2 += ","
        else:
            s2 += "\n"
    versioning['check'] += s2
    versioning['checkcount'] += 1
    s2 = str(versioning['checkcount']) + " " + s2
    print (s2)

    return

def save_check():
    """
    Save validation results to CSV file.
    
    This function writes accumulated validation results from checkmap calls
    to a CSV file for external analysis. The output location is determined
    from command-line arguments stored in the versioning system.
    
    Notes
    -----
    The output file is the first argument after the settings file ending with .csv
    (see checkfiles), e.g. settings.ini -c reference.nc output.csv or settings.ini -c output.csv

    File saving occurs only when:
    - Valid arguments are provided with .csv extension
    - Validation results have been accumulated in versioning['check']

    The CSV output includes headers and formatted data for each validated input.

    The saved file can be analyzed externally to:
    - Compare multiple model setups
    - Track data quality over time
    - Validate input data consistency
    - Document model configuration for reproducibility
    """

    _, savefile = checkfiles(versioning['checkargs'])
    if savefile is not None:
        with open(savefile, 'w', encoding='utf-8') as f:
            f.write(versioning['check'])
    return


def checkfiles(args):
    """
    Reference netCDF and output CSV file of the check (option -c) from the arguments after the settings file.

    The files are found by their extension (.nc, .csv) in any order; options (-c, -l ...) are skipped.

    Parameters
    ----------
    args : list
        Command-line arguments after the settings file

    Returns
    -------
    tuple
        (reference .nc file or None, output .csv file or None)
    """
    files = [a for a in args if not a.startswith('-')]
    refile = next((a for a in files if a.lower().endswith('.nc')), None)
    csvfile = next((a for a in files if a.lower().endswith('.csv')), None)
    return refile, csvfile








