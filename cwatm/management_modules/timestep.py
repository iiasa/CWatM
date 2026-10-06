# -------------------------------------------------------------------------
# Name:        Handling of timesteps and dates
# Purpose: Temporal management system handling dates, calendars, and time stepping.
# Supports multiple calendar systems and NetCDF temporal coordinate processing.
# Manages simulation period validation and time-based data indexing.
#
# Author:      P. Burek
# Created:     09/08/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import datetime
import difflib  # to check the closest word in settingsfile, if an error occurs
import os
import time as xtime

import numpy as np
from netCDF4 import Dataset, num2date, date2num, date2index

from cwatm.management_modules.data_handling import *
from cwatm.management_modules.globals import *
from cwatm.management_modules.messages import *
from cwatm.management_modules.caching import ncopen

def datenum(date):
    """
    Convert date to integer number based on NetCDF calendar and units.
    
    Converts a datetime object to an integer representation based on the
    calendar system and time units defined in the NetCDF meteorological
    data files. This enables consistent temporal indexing across different
    calendar systems (standard, 360-day, noleap) used in climate data.
    
    Parameters
    ----------
    date : datetime.datetime
        Date to convert to numeric representation.
    
    Returns
    -------
    int
        Integer representation of the date in NetCDF time units.
        Adjusted for the unit conversion factor (daily, hourly, etc.).
    
    Notes
    -----
    Uses global dateVar dictionary containing:
    - unit: NetCDF time units (e.g., "days since 1901-01-01")
    - calendar: Calendar system ('standard', '360_day', 'noleap', etc.)
    - unitConv: Conversion factor for different time resolutions
    
    The function applies rounding to handle NetCDF files that use 12:00
    as the starting time, which results in half-day offsets.
    """
    
    try:
        num = round(date2num(date, units=dateVar['unit'], calendar=dateVar['calendar']))
    except ValueError:
        # e.g. 29/02 with calendar noleap or 31/01 with calendar 360_day
        msg = "Error 138: Date: " + date2str(date) + " does not exist in the calendar: \"" + dateVar['calendar'] + "\" of the precipitation maps\n"
        msg += "Check StepStart, StepEnd, SpinUp and StepInit in the settings file"
        raise CWATMError(msg)
    # changed to round because some date in netcdf have 12:00 as starting time -> results in -0.5
    return num // dateVar['unitConv']

def numdate(num, add=0):
    """
    Convert integer to date based on NetCDF calendar and units.
    
    Converts an integer representation back to a datetime object using
    the calendar system and time units from NetCDF meteorological files.
    This is the inverse operation of datenum() and maintains temporal
    consistency across different calendar systems.
    
    Parameters
    ----------
    num : int or float
        Numeric representation of the date in NetCDF time units.
    add : int, optional
        Additional days to add to the resulting date. Default is 0.
    
    Returns
    -------
    datetime.datetime
        Datetime object corresponding to the numeric representation.
    
    Notes
    -----
    Uses global dateVar dictionary for calendar and unit information.
    The function handles various NetCDF time representations and
    calendar systems commonly used in meteorological and climate data.
    
    Used primarily for:
    - Converting NetCDF time indices back to calendar dates
    - Temporal calculations requiring date arithmetic
    - Output timestamp generation
    """
    # num and add in days -> * unitConv to the time unit of the netcdf file (e.g. hours)
    return (num2date((int(num) + add) * dateVar['unitConv'], units=dateVar['unit'], calendar=dateVar['calendar']))

def date2str(date):
    """
    Convert datetime object to standardized date string format.
    
    Converts a datetime object to a consistent string representation
    used throughout CWatM for output formatting, logging, and user
    display. The format is day/month/year with zero padding.
    
    Parameters
    ----------
    date : datetime.datetime
        Date to convert to string representation.
    
    Returns
    -------
    str
        Date string in format "dd/mm/yyyy" (e.g., "27/12/2018").
    
    Notes
    -----
    - Uses zero-padding for single-digit days and months
    - Provides consistent date formatting across all CWatM outputs
    - Handles dates before 1900 that cause issues with strftime()
    - Used in progress reporting, output headers, and user interfaces
    """

    return "%02d/%02d/%04d" % (date.day, date.month, date.year)


def ctbinding(inBinding):
    """
    Check and retrieve configuration binding with error handling.
    
    Validates that a configuration parameter exists in the settings file
    and retrieves its value. Provides helpful error messages with closest
    matches when parameters are not found, assisting with debugging
    configuration issues.
    
    Parameters
    ----------
    inBinding : str
        Configuration parameter name to look up in the binding dictionary.
    
    Returns
    -------
    str
        Value of the configuration parameter from the binding dictionary.
    
    Raises
    ------
    CWATMError
        If the parameter is not found in the binding dictionary.
        Error message includes closest matching parameter names for debugging.
    
    Notes
    -----
    - Used specifically for time-related configuration parameters
    - Provides fuzzy matching suggestions using difflib for typo detection
    - Part of the configuration validation system
    - Essential for robust parameter handling in temporal calculations
    
    The function helps ensure that all required time-related parameters
    are properly configured before model execution begins.
    """

    test = inBinding in binding
    if test:
        return binding[inBinding]
    else:
        # not tested because you have to remove eg stepstart to test this
        closest = difflib.get_close_matches(inBinding, list(binding.keys()))
        if not closest: closest = ["- no match -"]
        msg = "Error 118: ===== Timing in the section: [TIME-RELATED_CONSTANTS] is wrong! =====\n"
        msg += "No key with the name: \"" + inBinding + "\" in the settings file: \"" + settingsfile[0] + "\"\n"
        msg += "Closest key to the required one is: \""+ closest[0] + "\""
        raise CWATMError(msg)

def timemeasure(name, loops=0, update=False, sample=1):
    """
    Measure execution time for model subroutines and components.
    
    Records high-precision timestamps for performance profiling of CWatM
    components. Enables detailed analysis of computational bottlenecks
    and optimization of model performance. Part of the timing infrastructure
    used when the printtime flag is enabled.
    
    Parameters
    ----------
    name : str
        Name of the subroutine or component being measured.
    loops : int, optional
        Loop counter appended to name for repeated calls. Default is 0.
    update : bool, optional
        Flag for updating measurements (currently unused). Default is False.
    sample : int, optional
        Sampling parameter (currently unused). Default is 1.
    
    Returns
    -------
    None
        Appends timestamp and identifier to global timing arrays.
    
    Notes
    -----
    Uses global arrays:
    - timeMes: List of high-precision timestamps (perf_counter)
    - timeMesString: List of corresponding subroutine identifiers
    
    When loops > 0, the identifier becomes "name_N" where N is the loop number.
    This allows tracking of iterative processes and repeated function calls.
    
    Timing information is processed and reported when the model completes
    if the printtime command-line option is specified.
    """

    timeMes.append(xtime.perf_counter())
    if loops == 0:
        s = name
    else:
        s = name + "_%i" % loops
    timeMesString.append(s)
    return

# -----------------------------------------------------------------------
# Calendar routines
# -----------------------------------------------------------------------

def Calendar(input, errorNo=0):
    """
    Parse and validate date strings from configuration settings.
    
    Robust date parser that handles multiple date formats commonly used
    in configuration files. Converts various date representations to
    datetime objects while providing specific error messages for different
    contexts (start dates, initialization dates, etc.).
    
    Parameters
    ----------
    input : str or float
        Date string or numeric value from settings file.
        Supports formats: dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy, or numeric.
    errorNo : int, optional
        Error context identifier:
        - 0: Start/end date validation (default)
        - 1: Initialization date validation  
        - >1: Returns -99999 for invalid dates instead of raising error
    
    Returns
    -------
    datetime.datetime or float or int
        - datetime.datetime: Successfully parsed date
        - float: Numeric input passed through unchanged
        - int: Special return value (-99999) for invalid dates when errorNo > 1
    
    Raises
    ------
    CWATMError
        If date parsing fails and errorNo <= 1, with context-specific messages.
    
    Notes
    -----
    Date format handling:
    - Automatically detects 2-digit vs 4-digit years
    - Handles various separators (/, -, .)
    - Supports both European (dd/mm/yyyy) and numeric formats
    - Provides flexibility for international date conventions
    
    Used throughout the temporal configuration system for parsing
    start dates, end dates, and initialization timestamps.
    """

    date = None

    try:
        date = float(input)
    except ValueError:
        d = input.replace('.', '/')
        d = d.replace('-', '/')
        year = d.split('/')[-1:]
        if len(year[0]) == 4:
            formatstr = "%d/%m/%Y"
        else:
            formatstr = "%d/%m/%y"
        if len(year[0]) == 1:
            d = d.replace('/', '.', 1)
            d = d.replace('/', '/0')
            d = d.replace('.', '/')

        try:
            date = datetime.datetime.strptime(d, formatstr)
        except ValueError:
            if errorNo == 0:
                msg = ("Error 119: Either date in StepStart is not a date or in SpinUp or StepEnd "
                       "it is neither a number or a date!")
                raise CWATMError(msg)
            elif errorNo == 1:
                msg = "Error 120: First date in StepInit is neither a number or a date!"
                raise CWATMError(msg)
            elif errorNo > 1:
                return -99999

    return date


def datetoInt(dateIn, begin, both=False):
    """
    Convert date to integer offset from reference date.
    
    Calculates the integer number of days between a given date and a
    reference date, handling various calendar systems. This is fundamental
    for CWatM's internal time indexing system, enabling consistent temporal
    calculations across different calendar types.
    
    Parameters
    ----------
    dateIn : str or float
        Input date string or numeric value to convert.
    begin : datetime.datetime
        Reference date for calculating the offset.
    both : bool, optional
        If True, returns both integer offset and string representation.
        Default is False (returns only integer).
    
    Returns
    -------
    int or tuple
        If both=False: Integer day offset from reference date (1-based).
        If both=True: Tuple of (integer_offset, date_string).
    
    Notes
    -----
    The function handles two input types:
    1. Date strings: Parsed using Calendar() and converted to day offsets
    2. Numeric values: Used directly as integer offsets
    
    The offset is 1-based, meaning the reference date itself returns 1.
    This aligns with CWatM's internal timestep numbering system.
    
    Critical for:
    - Converting configuration dates to internal timesteps
    - Temporal indexing in meteorological data
    - Simulation period calculations
    """

    date1 = Calendar(dateIn)

    if type(date1) is datetime.datetime:
        # str1 = date1.strftime("%d/%m/%Y")
        # to cope with dates before 1990
        str1 = date2str(date1)
        d1 = datenum(date1)
        d2 = datenum(begin)
        int1 = int(d1 - d2) + 1
         # to be used with different days in a year e.g. 360_years

    else:
        int1 = int(date1)
        str1 = str(date1)
    if both:
        return int1, str1
    else:
        return int1


def addmonths(d, x):
    """
    Add months to a date with proper handling of month boundaries.
    
    Performs date arithmetic that correctly handles month addition
    across year boundaries and varying month lengths. Ensures that
    invalid dates (e.g., February 30) are adjusted to valid dates
    by using the last valid day of the target month.
    
    Parameters
    ----------
    d : datetime.datetime
        Starting date for the addition operation.
    x : int
        Number of months to add (can be negative for subtraction).
    
    Returns
    -------
    datetime.datetime
        New date with the specified number of months added.
    
    Notes
    -----
    Month addition algorithm:
    - Calculates target month and year accounting for wraparound
    - Month length from the calendar of the netcdf file (leap years, noleap, 360_day)
    - Adjusts day to last valid day if original day exceeds month length
    - Returns a date in the calendar of the netcdf file (comparable with dateEnd)

    For example:
    - January 31 + 1 month = February 28 (or 29 in leap years, 30 in 360_day)
    - December 15 + 2 months = February 15
    - May 31 + 1 month = June 30
    
    Used in initialization date calculations and temporal sequence generation
    for save state operations and periodic output scheduling.
    """

    newmonth = (((d.month - 1) + x) % 12) + 1
    newyear = d.year + (((d.month - 1) + x) // 12)
    # first day of the new month and of the month after in the calendar of the netcdf file
    first = datenum(datetime.datetime(newyear, newmonth, 1))
    if newmonth == 12:
        firstnext = datenum(datetime.datetime(newyear + 1, 1, 1))
    else:
        firstnext = datenum(datetime.datetime(newyear, newmonth + 1, 1))
    # same day of month, but at most the last day of the new month
    newday = min(d.day, firstnext - first)
    # date in the calendar of the netcdf file (comparable with dateEnd)
    return numdate(first, newday - 1)



def datetosaveInit(initdates, begin, end):
    """
    Calculate and validate initialization save dates for model state output.
    
    Processes a list of dates or date patterns to determine when the model
    should save its internal state for initialization purposes. Supports
    both explicit dates and periodic patterns (yearly, monthly, daily).
    This is critical for model restarts and warm start capabilities.
    
    Parameters
    ----------
    initdates : list
        List of date specifications that can include:
        - Explicit date strings
        - Numeric offsets
        - Periodic patterns (e.g., "2y", "6m", "30d")
    begin : datetime.datetime
        Reference start date for the simulation period.
    end : datetime.datetime
        End date limiting the save date generation.
    
    Returns
    -------
    None
        Populates global dateVar['intInit'] list with integer timesteps.
    
    Raises
    ------
    CWATMError
        If date patterns are malformed or numeric values are invalid.
    
    Notes
    -----
    Periodic pattern formats:
    - "Ny": Every N years (e.g., "2y" = every 2 years)
    - "Nm": Every N months (e.g., "6m" = every 6 months)  
    - "Nd": Every N days (e.g., "30d" = every 30 days)
    
    A pattern repeats the last explicit date before it until the simulation
    end date; entries after a pattern are also used
    (e.g. "31/12/1990 1y 15/06/1995"). N has to be a positive integer.
    
    Global variables modified:
    - dateVar['intInit']: List of integer timesteps for state saving
    """

    dateVar['intInit'] = []
    d2 = datenum(begin)
    lastdate = None   # last explicit date (as integer timestep) - start of a repetition

    for i, d in enumerate(initdates, start=1):
        date1 = Calendar(d, i)

        # repetition of the last date before: e.g. 2y = every 2 years, 6m = every 6 month, 30d = every 30 days
        if date1 == -99999:
            rep = d[-1].lower()
            if rep not in ["d", "m", "y"]:
                msg = "Error 121: Value " + str(i) + " in StepInit: \"" + d + "\" is not a number or date nor indicating a repetition of year(y), month(m) or day(d)\n"
                msg += "e.g. 2y for every 2 years or 6m for every 6 month"
                raise CWATMError(msg)
            try:
                add = int(d[0:-1])
            except ValueError:
                add = 0
            if add < 1:
                msg = "Error 122: Value " + str(i) + " in StepInit: \"" + d + "\" needs a positive integer before 'y' or 'm' or 'd'"
                raise CWATMError(msg)
            start = numdate(d2, lastdate - 1)

            j = 1
            while True:
                if rep == 'y':
                    try:
                        date2 = start.replace(year=start.year + add * j)
                    except ValueError:
                        # 29 February -> 28 February in a year without leap day
                        date2 = numdate(datenum(start), -1)
                        date2 = date2.replace(year=date2.year + add * j)
                elif rep == 'm':
                    date2 = addmonths(start, add * j)
                else:
                    date2 = numdate(datenum(start), add * j)

                if date2 > end:
                    break
                dateVar['intInit'].append(int(datenum(date2) - d2) + 1)
                j += 1
            continue

        if type(date1) is datetime.datetime:
            int1 = int(datenum(date1) - d2) + 1
        else:
            int1 = int(date1)
        dateVar['intInit'].append(int1)
        lastdate = int1


# noinspection PyTypeChecker
def checkifDate(start, end, spinup, name):
    """
    Validate temporal configuration and initialize date variables.
    
    Comprehensive validation of simulation temporal bounds, including
    start/end dates, spinup period, and calendar system setup. Extracts
    calendar information from meteorological data files and performs
    extensive date consistency checks. Critical for proper temporal
    framework initialization.
    
    Parameters
    ----------
    start : str
        Configuration key for simulation start date.
    end : str
        Configuration key for simulation end date.
    spinup : str
        Configuration key for spinup end date (when outputs begin).
    name : str
        Path to meteorological file for calendar system extraction.
    
    Returns
    -------
    None
        Populates global dateVar dictionary with temporal parameters.
    
    Raises
    ------
    CWATMFileError
        If meteorological file cannot be found or accessed.
    CWATMError
        If date validation fails or temporal bounds are inconsistent.
    
    Notes
    -----
    The function performs:
    1. NetCDF calendar and units extraction from meteorological data
    2. Unit conversion factor calculation (daily, hourly, etc.)
    3. Date parsing and validation for start, end, and spinup dates
    4. Temporal consistency checks (start < spinup <= end)
    5. Calendar-specific day counting and period calculations
    
    Global dateVar dictionary populated with:
    - Date objects: dateBegin, dateStart, dateEnd
    - Integer offsets: intStart, intEnd, intSpin
    - Calendar info: calendar, unit, unitConv
    - Temporal markers: checked list for month/year boundaries
    - Period counts: diffdays, diffMonth, diffYear
    
    Essential for all subsequent temporal operations in CWatM.
    """

    # begin = Calendar(ctbinding('CalendarDayStart'))
    try:
        name = glob.glob(os.path.normpath(name))[0]
    except IndexError:
        msg = "Error 215: Cannot find precipitation maps\n"
        raise CWATMFileError(name,msg, sname='PrecipitationMaps')

    nf1 = ncopen(name)   # cached: the same precipitation file is used later by multinetdf/readmeteodata
    # time unit and calendar of the precipitation file (defaults if missing)
    timevar = nf1.variables.get('time')
    dateVar['calendar'] = getattr(timevar, 'calendar', 'standard')
    dateVar['unit'] = getattr(timevar, 'units', "days since 1901-01-01T00:00:00Z")

    unitconv1 = ["DAYS","HOUR","MINU","SECO"]
    unitconv2 = [1,24,1440,86400]
    unitconv3 = dateVar['unit'] [:4].upper()
    try:
        dateVar['unitConv'] = unitconv2[unitconv1.index(unitconv3)]
    except ValueError:
        dateVar['unitConv'] = 1

    startdate = Calendar(ctbinding('StepStart'))
    if type(startdate) is datetime.datetime:
        begin = startdate
    else:
        msg = "Error 123: \"StepStart = " + ctbinding('StepStart') + "\"\n"
        msg += "StepStart has to be a valid date!"
        raise CWATMError(msg)

    # spinup date = date from which maps are written
    if ctbinding(spinup).lower() == "none" or ctbinding(spinup) == "0":
        spinup = start

    dateVar['intStart'], strStart = datetoInt(ctbinding(start), begin, True)
    dateVar['intEnd'], strEnd = datetoInt(ctbinding(end), begin, True)
    dateVar['intSpin'], strSpin = datetoInt(ctbinding(spinup), begin, True)


    # test if start and end > begin
    if (dateVar['intStart'] < 0) or (dateVar['intEnd'] < 0) or ((dateVar['intEnd'] - dateVar['intStart']) < 0):
        # strBegin = begin.strftime("%d/%m/%Y")
        strBegin = date2str(begin)
        msg = "Error 124: Start Date: " + strStart + " and/or end date: " + strEnd + " are wrong!\n or smaller than the first time step date: " + strBegin
        raise CWATMError(msg)

    if (dateVar['intSpin'] < dateVar['intStart']) or (dateVar['intSpin'] > dateVar['intEnd']):
        # strBegin = begin.strftime("%d/%m/%Y")
        strBegin = date2str(begin)
        msg = "Error 125: Spin Date: " + strSpin + " is wrong!\n or smaller/bigger than the first/last time step date: " + strBegin + " - " + strEnd
        raise CWATMError(msg)

    dateVar['currDate'] = begin
    dateVar['dateBegin'] = begin
    # dateVar['dateStart'] = begin + datetime.timedelta(days=dateVar['intSpin']-1)

    d1 = datenum(begin)
    dateVar['datenumBegin'] = d1
    startint = int(d1 + dateVar['intSpin'] - 1)
    dateVar['dateStart'] = numdate(startint)
    dateVar['diffdays'] = dateVar['intEnd'] - dateVar['intSpin'] + 1

    d1 = datenum(dateVar['dateStart'])
    endint = int(d1 + dateVar['diffdays'])
    dateVar['dateEnd'] = numdate(endint, -1)


    dateVar['curr'] = 0
    dateVar['currwrite'] = 0
    dateVar['currMonth'] = 0
    dateVar['currYear'] = 0



    # all dates from the first time step to the day after the last one with one num2date call (time in units of the file -> * unitConv)
    # used for currDate in timestep_dynamic and for checked
    dateVar['dates'] = num2date(np.arange(dateVar['datenumBegin'], endint + 1) * dateVar['unitConv'], units=dateVar['unit'], calendar=dateVar['calendar'])
    # checked: 0 = normal day, 1 = last day of a month, 2 = last day of a year - from the spin up date on
    months = [d.month for d in dateVar['dates'][dateVar['intSpin'] - 1:]]
    dateVar['checked'] = []
    for i in range(len(months) - 1):
        if months[i] != months[i + 1]:
            if months[i] == 12:
                dateVar['checked'].append(2)
            else:
                dateVar['checked'].append(1)
        else:
            dateVar['checked'].append(0)

    dateVar['diffMonth'] = dateVar['checked'].count(1) + dateVar['checked'].count(2)
    dateVar['diffYear'] = dateVar['checked'].count(2)


def date2indexNew(date, nctime, calendar, select='nearest', name=""):
    """
    Enhanced date-to-index conversion for NetCDF files with extended time unit support.
    
    Extends the standard NetCDF4 date2index functionality to handle monthly
    and yearly time units that are not supported by the original implementation.
    Critical for accessing climatological data with non-daily temporal resolution
    commonly used in hydrological modeling.
    
    Parameters
    ----------
    date : datetime.datetime
        Target date to find in the NetCDF time dimension.
    nctime : netCDF4.Variable
        NetCDF time variable containing units and values.
    calendar : str
        Calendar system used in the NetCDF file.
    select : str, optional
        Selection method for nearest date matching. Default is 'nearest'.
    name : str, optional
        Dataset name for enhanced error reporting. Default is empty string.
    
    Returns
    -------
    int
        Array index corresponding to the specified date in the NetCDF time dimension.
    
    Notes
    -----
    Supported time units:
    - DAYS: Standard daily resolution (uses original netCDF4.date2index)
    - MONTHS: Monthly resolution with year-month indexing
    - YEARS: Annual resolution with year indexing
    
    For monthly/yearly data, the function:
    - Calculates temporal offset from reference date in units
    - Handles cases where requested date exceeds available data range
    - Issues warnings when using boundary data for out-of-range requests
    - Performs array lookup to find matching time indices
    
    Essential for accessing diverse climatological datasets with varying
    temporal resolutions in hydrological modeling applications.
    """

    unit = nctime.units.split()
    if unit[0].upper() == "DAYS":
        index = date2index(date, nctime, calendar=calendar, select=select)
    elif unit[0][0:5].upper() == "MONTH":
        times = nctime[:]   # read the time axis once
        year0 = int(unit[2][0:4])
        month0 = int(unit[2][5:7])
        value = (date.year - year0) * 12 + (date.month - month0)
        if value > times.max():
            # later than the last record: same month in the last year of the dataset (no warning)
            value = value - 12 * int(np.ceil((value - times.max()) / 12))
        if value < times.min():
            # earlier than the first record: same month in the first year of the dataset (no warning)
            value = value + 12 * int(np.ceil((times.min() - value) / 12))
        index = np.where(times == value)[0][0]
    elif unit[0][0:4].upper() == "YEAR":
        times = nctime[:]   # read the time axis once
        year0 = int(unit[2][0:4])
        value = date.year - year0
        if value > times.max():
            # later than the last record: last year of the dataset (no warning)
            value = times.max()
        if value < times.min():
            # earlier than the first record: first year of the dataset (no warning)
            value = times.min()
        index = np.where(times == value)[0][0]
    else:
        index = date2index(date, nctime, calendar=calendar, select=select)
    return index




# first day of year, days in month and days in year per (calendar, unit, year, month) - used by timestep_dynamic
daysCache = {}

def timestep_dynamic(self):
    """
    Update temporal state variables during dynamic model execution.
    
    Core temporal processing function called at each timestep to advance
    the model's temporal state. Updates current date, calculates temporal
    markers (month/year boundaries), and maintains counters for output
    scheduling and temporal aggregation. Essential for coordinating all
    time-dependent model processes.
    
    Parameters
    ----------
    self : object
        Model instance (parameter not used but maintains method signature).
    
    Returns
    -------
    None
        Updates global dateVar dictionary with current temporal state.
    
    Notes
    -----
    The function updates dateVar with:
    - currDate: Current simulation date (datetime object)
    - currDatestr: Current date as formatted string
    - doy: Day of year (1-366)
    - 10day, 30day: Dekadal and monthly period indices
    - laststep: Boolean flag for final timestep
    - newStart, newMonth, newYear: Boolean flags for temporal boundaries
    - currMonth, currYear: Cumulative month/year counters for output
    - daysInMonth, daysInYear: Current period lengths for averaging
    
    Temporal boundary detection:
    - Identifies first timestep, month start, year start
    - Enables conditional execution of periodic processes
    - Supports flexible output scheduling and aggregation
    
    Called once per timestep during the main simulation loop,
    providing the temporal framework for all model components.
    """

    # dates are calculated once in checkifDate
    dateVar['currDate'] = dateVar['dates'][dateVar['curr']]
    datevarInt = dateVar['datenumBegin'] + dateVar['curr']

    # dateVar['currDatestr'] = dateVar['currDate'].strftime("%d/%m/%Y")
    dateVar['currDatestr'] = date2str(dateVar['currDate'])

    # first day of the year, days in month and days in year change only with the month -> cached
    year = dateVar['currDate'].year
    month = dateVar['currDate'].month
    key = (dateVar['calendar'], dateVar['unit'], year, month)
    if key not in daysCache:
        d1month = datenum(datetime.datetime(year=year, month=month, day=1))
        if month == 12:
            d2month = datenum(datetime.datetime(year=year + 1, month=1, day=1))
        else:
            d2month = datenum(datetime.datetime(year=year, month=month + 1, day=1))
        d1year = datenum(datetime.datetime(year=year, month=1, day=1))
        d2year = datenum(datetime.datetime(year=year + 1, month=1, day=1))
        daysCache[key] = (d1year, d2month - d1month, d2year - d1year)
    firstdoyInt, dateVar['daysInMonth'], dateVar['daysInYear'] = daysCache[key]
    # doy without strftime because of dates before 1900
    dateVar['doy'] = int(datevarInt - firstdoyInt + 1)
    dateVar['10day'] = (dateVar['doy'] - 1) // 10
    dateVar['30day'] = (dateVar['doy'] - 1) // 30

    dateVar['laststep'] = False
    if (dateVar['intStart'] + dateVar['curr']) == dateVar['intEnd']:
        dateVar['laststep'] = True

    dateVar['currStart'] = dateVar['curr'] + 1
    dateVar['curr'] += 1
    # count currwrite only after spin time
    if dateVar['curr'] >= dateVar['intSpin']:
        dateVar['currwrite'] += 1
        # count written month ends (checked 1 or 2) and year ends (checked 2)
        checkedToday = dateVar['checked'][dateVar['currwrite'] - 1]
        if checkedToday > 0:
            dateVar['currMonth'] += 1
            if checkedToday == 2:
                dateVar['currYear'] += 1

    # first timestep
    dateVar['newStart'] = dateVar['curr'] == 1
    dateVar['newMonth'] = dateVar['currDate'].day == 1
    dateVar['newYear'] = (dateVar['currDate'].day == 1) and (dateVar['currDate'].month == 1)
    dateVar['new10day'] = (dateVar['doy'] - 1) % 10 == 0
    dateVar['new30day'] = (dateVar['doy'] - 1) % 30 == 0

    return
