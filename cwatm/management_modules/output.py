# -------------------------------------------------------------------------
# Name: Output
# Purpose: Output as timeseries, netcdf,
#
# Author:      PB
# Created:     5/08/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import difflib  # to check the closest word in settingsfile, if an error occurs
import math
import os
import string
import sys
from decimal import Decimal

import numpy as np
from netCDF4 import Dataset, num2date, date2num, date2index

from . import globals
from .messages import *
from cwatm.hydrological_modules.routing_reservoirs.routing_sub import *
from cwatm.management_modules.checks import *
from cwatm.management_modules.data_handling import *
from cwatm.management_modules.replace_pcr import *

class outputTssMap(object):

    """
    Main CWatM output system class handling time series and map output generation.

    This class manages all output operations for the CWatM hydrological model, including
    NetCDF map writing, time series extraction at gauge points, CSV/TSS file generation,
    and progress reporting. It handles various temporal aggregations (daily, monthly,
    annual) and spatial aggregations (point values, catchment averages/sums).

    Attributes
    ----------
    var : object
        Reference to model variable container with hydrological state variables
    model : object
        Reference to main CWatM model instance

    Notes
    -----
    The output system supports multiple output formats:
    - NetCDF maps for spatial data with temporal aggregation
    - Time series files (TSS/CSV) for gauge point data
    - Text dumps for debugging and analysis
    - Progress monitoring for GUI integration
    
    Output timing is controlled by dateVar configuration and supports:
    - Daily outputs
    - Month-end, monthly totals, monthly averages  
    - Annual outputs with various aggregations
    - Simulation-total aggregations

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    dirUp                                Array         river network in upstream direction                                     --   
    meteo                                Array         store all meteo data in memeory for warm start (eg calibration)         compl
    sampleAdresses                       List          outflowpoints as 1D index                                               --   
    outpoints                            List          output points (Gauges)                                                  --   
    noOutpoints                          Number        number of output points                                                 --   
    evalCatch                            Array         indeces of a subbasin in the mask                                       --   
    catcharea                            Array         catchment area of the subbaSIN                                          m2   
    netcdfasindex                        Flag          save netcdf file in a compressed way - for splitting runs in several b  bool 
    firstout                             Number        discharge of the first gauge                                            m3/s 
    discharge                            Array         Channel discharge                                                       m3/s 
    cellArea                             Array         Area of cell                                                            m2   
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize CWatM output system with model reference.

        Parameters
        ----------
        model : object
            Main CWatM model instance containing variable container and configuration

        Notes
        -----
        Sets up references to model variables and configuration needed for output
        operations. The actual output configuration is handled in the initial() method.
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initialize output system configuration, gauge locations, and file structures.

        This method sets up the complete output system including:
        - Processing gauge coordinates and creating sample addresses
        - Configuring catchment boundaries for area-based aggregations
        - Setting up NetCDF and time series file structures
        - Validating output variable names and timing specifications
        - Initializing progress reporting system

        Notes
        -----
        Must be called before any dynamic output operations. Processes settings
        file configuration to determine output locations, variables, and timing.
        Creates catchment delineation for gauges requiring area-based statistics.
        Validates all output variable names against available model variables.
        """

        def getlocOutpoints(out):
            """
            Extract gauge locations from output point map and convert to geographic coordinates.

            Parameters
            ----------
            out : numpy.ndarray
                1D compressed array with gauge IDs at corresponding cell locations,
                zero for non-gauge cells

            Returns
            -------
            dict
                Dictionary mapping gauge IDs to compressed array indices for fast lookup
            list
                List of x,y coordinates in model projection [x1, y1, x2, y2, ...] for all gauges

            Notes
            -----
            Converts from compressed array indices to geographic coordinates using
            mask information and cell size. Coordinates represent cell centers in
            the model's spatial reference system.
            """

            sampleAdresses = {}
            outp = []
            # allpoints = np.where(maskinfo["mask"].data == False)
            allpoints = np.where(maskinfo["mask"] == False)

            for i in range(maskinfo['mapC'][0]):
                if out[i] > 0:
                    sampleAdresses[out[i]] = i

                    outx = allpoints[1][i] * maskmapAttr['cell'] + maskmapAttr['x'] + maskmapAttr['cell'] / 2
                    outy = maskmapAttr['y'] - allpoints[0][i] * maskmapAttr['cell'] - maskmapAttr['cell'] / 2
                    outp.append(outx)
                    outp.append(outy)

            return sampleAdresses, outp


        def appendinfo(out, sec, name, type, ismap):
            """
            Configure output specifications for maps or time series based on settings.

            Parameters
            ----------
            out : dict
                Output configuration dictionary to populate with file information
            sec : str
                Settings file section name (e.g., 'OUTPUT', 'INITIAL', 'ENVIRONMENTAL')
            name : str
                Base output identifier ('_out_tss_' or '_out_map_')
            type : str
                Temporal aggregation type ('daily', 'monthly', 'annual', etc.)
            ismap : bool
                True for NetCDF map output, False for time series output

            Notes
            -----
            Creates file paths and metadata structures for each configured output.
            For maps: sets up NetCDF file paths and variable creation flags.
            For time series: configures CSV or TSS file formats based on settings.
            Validates output directory existence and creates error messages for
            missing paths.
            """

            key = sec.lower() + name + type
            if key in out:
                if out[key][0] != "None":
                    i = 0
                    for var in out[key]:
                        info = []
                        if os.path.exists(outDir[sec]):
                            if ismap:
                                info.append(os.path.join(outDir[sec], str(var) + "_" + type + ".nc"))
                                #vars(self.var)[var+"_"+type] = 0
                                # creates a var to sum/ average the results e.g. self.var.Precipitation_monthtot
                                info.append(var)
                                info.append(False)

                            else:
                                # TimeoutputTimeseries(binding[tss], self.var, outpoints, noHeader=Flags['noheader'])
                                # info.append(os.path.join(outDimpontr[sec], str(var) + "_daily.tss"))
                                newcsvformat = True
                                suffix = ".csv"
                                if 'reportOldTss' in option:
                                    newcsvformat = not(checkOption('reportOldTss'))
                                if not(newcsvformat):
                                    suffix = ".tss"

                                name = os.path.join(outDir[sec], str(var) + "_" + type + suffix)
                                # info.append(TimeoutputTimeseries2(name, self.var, outpoints, noHeader=False))
                                info.append(name)
                                info.append(var)
                                # flag set True for writing times series in csv format
                                info.append(newcsvformat)
                        else:
                            msg = "Error 220: Checking output file path \n"
                            raise CWATMFileError(outDir[sec], msg)

                        placeholder = []
                        info.append(placeholder)
                        if ismap:
                            info.append(type)  # set type to create variable later on first timestep
                        out[key][i] = info
                        i += 1


        # ------------------------------------------------------------------------------
        # if a geotif is used it can be a local map or a global
        localGauges = returnBool('GaugesLocal')
        where = "Gauges"
        outpoints = cbinding(where)

        # globals.inZero = np.zeros(maskinfo['mapC'])

        coord = cbinding(where).split()  # could be gauges, sites, lakeSites etc.
        if len(coord) % 2 == 0:
            compress_arange = np.arange(maskinfo['mapC'][0])
            arange = decompress(compress_arange).astype(int)

            # outpoints = valuecell( coord, outpoints)
            col, row = valuecell(coord, outpoints, returnmap=False)
            self.var.sampleAdresses = {}
            for i in range(len(col)):
                self.var.sampleAdresses[i + 1] = arange[row[i], col[i]]

            self.var.outpoints = list(map(float, outpoints.split(" ")))

        else:
            if os.path.exists(outpoints):
                outpoints = loadmap(where, local=localGauges).astype(np.int64)
            else:
                if len(coord) == 1:
                    msg = "Error 221: Checking output-points file\n"
                else:
                    msg = "Error 129: Coordinates are not pairs\n"
                raise CWATMFileError(outpoints, msg, sname="Gauges")

            # self.var.Tss[tss] = TimeoutputTimeseries(cbinding(tss), self.var, outpoints, noHeader=Flags['noheader'])
            outpoints[outpoints < 0] = 0
            self.var.sampleAdresses, self.var.outpoints = getlocOutpoints(outpoints)  # for key in sorted(mydict):

        self.var.noOutpoints = len(self.var.sampleAdresses)
        # catch = subcatchment1(self.var.dirUp,outpoints,self.var.UpArea1)

        # check if catchment area calculation is necessary
        calcCatch = False
        for s in filter(lambda x: "areaavg" in x, outTss.keys()):
            calcCatch = True
        for s in filter(lambda x: "areasum" in x, outTss.keys()):
            calcCatch = True

        if calcCatch:
            self.var.evalCatch = {}
            self.var.catcharea = {}


            for key in sorted(self.var.sampleAdresses):
                outp = globals.inZero.copy()
                outp[self.var.sampleAdresses[key]] = key



                self.var.evalCatch[key] = catchment1(self.var.dirUp, outp)
                self.var.catcharea[key] = np.bincount(self.var.evalCatch[key], weights=self.var.cellArea)[key]

        # ------------------------------------------------------------------------------
        # report TSS
        # loop through all the section with output variables
        for sec in outsection:
            for type2 in outputTypTss2:
                for type in outputTypTss:
                    if type2 == "tss":
                        type = type
                    else:
                        type = type2 + "_" + type
                    appendinfo(outTss, sec, "_out_tss_",type, False)

        # report MAPs
        metaNetCDF()
        # loop through all the section with output variables
        for sec in outsection:
            # daily output, monthly total monthly average,
            for type in outputTypMap:
                # map or tss, section, type = daily, monthly ....
                appendinfo(outMap,sec, "_out_map_",type, True)

        # check if timing of output is in outputTypTss  (globals.py)
        for out in list(outTss.keys()):
            if not(out.split('_')[-1] in outputTypTss):
                msg = "Error 130: Output is not possible!\n"
                msg += "\""+out +"\" is not one of these: daily, monthend, monthtot, monthavg, annualend, annualtot, annualavg"
                raise CWATMError(msg)
            if not(out.split('_')[-2] in outputTypTss2):
                msg = "Error 131: Output is not possible!\n"
                msg += "\""+out +"\" is not one of these: TSS for point value, AreaSum for sum of area, AreaAvg for average of area"
                raise CWATMError(msg)

        # save netcdf as index maps (not lar/lon) but only the valid cells
        self.var.netcdfasindex = False
        if "netcdfasindex" in option:
            self.var.netcdfasindex = checkOption('netcdfasindex')


    def dynamic(self, ef = False):
        """
        Execute dynamic output operations for current time step.

        This is the main output execution method called at each time step to:
        - Write NetCDF maps with appropriate temporal aggregation
        - Extract and accumulate time series data at gauge points
        - Handle monthly/annual aggregation and reset cycles
        - Update progress reporting for GUI and console output
        - Manage file writing for completed aggregation periods

        Parameters
        ----------
        ef : bool, optional
            Environmental flow flag indicating if processing environmental flow
            calculations, by default False

        Notes
        -----
        Processes all configured outputs based on current date and timing rules.
        Handles temporal aggregation by accumulating values and writing outputs
        at appropriate intervals (month-end, year-end, etc.). Updates progress
        displays and manages memory by resetting aggregation variables after
        writing outputs.
        """

        def firstout(map):
            """
            Extract value from the first configured output point for progress reporting.

            Parameters
            ----------
            map : numpy.ndarray
                1D compressed array containing values to sample

            Returns
            -------
            float
                Value at the first gauge location, used for console progress display

            Notes
            -----
            Used primarily for displaying discharge values during model execution
            to provide feedback on simulation progress. Always samples from the
            lowest-numbered gauge ID for consistency.
            """

            first = sorted(list(self.var.sampleAdresses))[0]
            value = map[self.var.sampleAdresses[first]]
            return value

        def checkifvariableexists(name, vari, space):
            """
            Validate that requested output variable exists in model variable space.

            Parameters
            ----------
            name : str
                Context name for error reporting (output section name)
            vari : str
                Variable name to validate, may include array indexing
            space : list
                List of available variable names in model variable container

            Raises
            ------
            CWATMError
                If variable does not exist in variable space, with suggestion
                for closest matching variable name

            Notes
            -----
            Provides helpful error messages with closest variable name matches
            using difflib fuzzy string matching when requested variable is not found.
            Handles array-indexed variables by checking base variable name.
            """
            if not (vari in space):
                closest = difflib.get_close_matches(vari, space)
                if not closest: closest = ["- no match -"]
                msg = "Error 132: Variable \"" + vari + "\" is not defined in \""+ name+"\"\n"
                msg += "Closest variable to this name is: \"" + closest[0] + "\""
                raise CWATMError(msg)



        def sample3(expression, map, daymonthyear):
            """
            Sample values at gauge points and accumulate for time series output.

            Parameters
            ----------
            expression : list
                Output configuration containing [filename, variable, format_flag, data_list, type]
            map : numpy.ndarray
                1D compressed array with values to sample at gauge locations
            daymonthyear : int
                Temporal aggregation level: 0=daily, 1=monthly, 2=annual

            Returns
            -------
            list
                Updated expression with accumulated time series data

            Notes
            -----
            Handles three types of spatial aggregation:
            - Point values: Direct sampling at gauge coordinates
            - Area averages: Catchment-weighted mean values
            - Area sums: Catchment-weighted total values
            
            Accumulates values during simulation and writes complete time series
            to file at the end of the simulation period. Supports both CSV and
            traditional TSS formats.
            """

            #if dateVar['checked'][dateVar['currwrite'] - 1] >= daymonthyear:
            # using a list with is 1 for monthend and 2 for year end to check for execution
            value = []
            #tss.split('_')[-2]

            # if inputmap is not an array give out error message
            if not (hasattr(map, '__len__')):
                msg = "No values in: " + expression[1] + "\nCould not write: " + expression[0]
                print(CWATMWarning(msg))
                return expression

            for key in sorted(self.var.sampleAdresses):
                if expression[0].split('_')[-2] in ['areaavg','areasum']:
                    # value from catchment
                    v = np.bincount(self.var.evalCatch[key], weights = map * self.var.cellArea)[key]

                    if expression[0].split('_')[-2] == 'areaavg':
                        if self.var.catcharea[key] == 0:
                            v = 0.
                        else:
                            v = v / self.var.catcharea[key]
                else: # from single cell
                   v = map[self.var.sampleAdresses[key]]
                value.append(v)
            expression[3].append(value)

            if dateVar['laststep']:
                if expression[2]:
                    writeTssFileNew(expression, daymonthyear)
                else:
                    writeTssFile(expression, daymonthyear)

            return expression


        def sample4(expression, what, daymonthyear):
            """
            Collects outputpoint value to write it into a time series file
            calls function :meth:`management_modules.writeTssFile`

            :param expression: array of outputpoint information
            :param map: 1D array of data
            :param daymonthyear: day =0 , month =1 , year =2
            :return: expression
            """

            #if dateVar['checked'][dateVar['currwrite'] - 1] >= daymonthyear:
            # using a list with is 1 for monthend and 2 for year end to check for execution
            value = []
            #tss.split('_')[-2]
            map10 = []
            for i in range(self.var.numberSnowLayers):
                w = what +"["+str(i)+"]"
                map10.append(eval(w))

            # if inputmap is not an array give out error message
            if not (hasattr(map10, '__len__')):
                msg = "No values in: " + expression[1] + "\nCould not write: " + expression[0]
                print(CWATMWarning(msg))
                return expression

            ii = 0
            for key in sorted(self.var.sampleAdresses):
                if self.var.sampleAdresses[key] < 0:
                    v = -999
                else:
                    v = map10[self.var.elepoint[ii]][self.var.sampleAdresses[key]]
                value.append(v)
                ii += 1

            expression[3].append(value)

            if dateVar['laststep']:
                if expression[2]:
                    writeTssFileNew(expression, daymonthyear)
                else:
                    writeTssFile(expression, daymonthyear)
            return expression


        def writeTssFile(expression, daymonthyear):
            """
            Write traditional TSS format time series file with PCRaster-style header.

            Parameters
            ----------
            expression : list
                Output configuration with filename, variable info, and accumulated data
            daymonthyear : int
                Temporal filter level: 0=daily, 1=monthly, 2=annual

            Notes
            -----
            Creates traditional PCRaster TSS format files with:
            - Metadata header with model version and run information
            - Column count and timestep numbering
            - Fixed-width numeric formatting
            - Missing value handling with 1e31 sentinel
            
            Only outputs timesteps matching the specified temporal aggregation level
            based on the dateVar checking system.
            """

            outputFilename = expression[0]

            #if expression[2]: now new csv if true
            writeFileHeader(outputFilename,expression)
            outputFile = open(outputFilename, "a")

            assert outputFile
            if len(expression[3]):
                numbervalues = len(expression[3][0])

                for timestep in range(dateVar['intSpin'], dateVar['intEnd'] + 1):
                    if dateVar['checked'][timestep - dateVar['intSpin']] >= daymonthyear:
                    #if dateVar['checked'][timestep - 1] >= daymonthyear:
                        row = ""
                        row += " %8g" % timestep
                        for i in range(numbervalues):
                            value = expression[3][timestep-1][i]
                            if isinstance(value, Decimal):
                                row += "           1e31"
                            else:
                                row += " %14g" % value
                        row += "\n"
                        outputFile.write(row)

            outputFile.close()

        def writeTssFileNew(expression, daymonthyear):
            """
            Write modern CSV format time series file with date headers.

            Parameters
            ----------
            expression : list
                Output configuration with filename, variable info, and accumulated data
            daymonthyear : int
                Temporal filter level: 0=daily, 1=monthly, 2=annual

            Notes
            -----
            Creates modern CSV format files with:
            - Comma-separated values
            - Date column in DD/MM/YYYY format
            - Human-readable headers with gauge coordinates
            - Model version and run metadata
            
            Date formatting adjusts to aggregation level (daily dates, month start
            for monthly data, year start for annual data). Preferred format for
            modern applications and data analysis.
            """

            outputFilename = expression[0]

            if expression[2]:
                writeFileHeaderNew(outputFilename,expression)
                outputFile = open(outputFilename, "a")
            else:
                outputFile = open(outputFilename, "w")

            assert outputFile
            if len(expression[3]):
                numbervalues = len(expression[3][0])

                for timestep in range(dateVar['intSpin'], dateVar['intEnd'] + 1):
                    if dateVar['checked'][timestep - dateVar['intSpin']] >= daymonthyear:
                        date1 = dateVar['dateBegin'] + datetime.timedelta(days=timestep - 1)
                        if "month" in os.path.split(outputFilename)[1]:
                            date1 = date1.replace(day=1)
                        if "annual" in os.path.split(outputFilename)[1]:
                            date1 = date1.replace(day=1,month=1)

                        row = date1.strftime('%d/%m/%Y')
                        for i in range(numbervalues):
                            value = expression[3][timestep-1][i]
                            if isinstance(value, Decimal):
                                row += ",1e31"
                            else:
                                row += ",%10g" % value
                        row += "\n"
                        outputFile.write(row)

            outputFile.close()

        def writeFileHeaderNew(outputFilename, expression):
            """
            Write CSV-style header with metadata and gauge coordinates.

            Parameters
            ----------
            outputFilename : str
                Full path to output CSV file
            expression : list
                Output configuration containing gauge information and metadata

            Notes
            -----
            Creates comprehensive CSV header with:
            - Model run metadata (settings file, execution time, version info)
            - Git branch and hash information for reproducibility
            - Longitude coordinates row for all gauges
            - Latitude coordinates row for all gauges
            - Column headers with gauge identifiers (G1, G2, etc.)
            
            Header provides all information needed to interpret time series data
            and reproduce the model run that generated the output.
            """

            outputFile = open(outputFilename, "w")
            # header
            # outputFile.write("timeseries " + self._spatialDatatype.lower() + "\n")
            header = "Timeseries," + "settingsfile: " + os.path.realpath(settingsfile[0]) + ",Runnning date: " + xtime.ctime(
                xtime.time())
            header += ",CWATM: " + versioning['exe'] + " Git-Branch:" + versioning['git']["git_branch"] + " Hash:" + versioning['git']["git_hash"]
            header += "\n"

            outputFile.write(header)

            loc = self.var.outpoints
            xrow = "xloc"
            yrow = "yloc"
            head = "Date"
            for x in loc[::2]:
                xrow = xrow +"," + "%#.4f" % round(x, 4)
            xrow = xrow + "\n"
            for y in loc[1::2]:
                yrow = yrow +"," + "%#.4f" % round(y, 4)
            yrow = yrow + "\n"
            for i in range(len(loc[::2])):
                head = head +",G" + str(i+1)
            head = head + "\n"

            outputFile.write(xrow)
            outputFile.write(yrow)
            outputFile.write(head)

            outputFile.close()



        def writeFileHeader(outputFilename, expression):
            """
            Write PCRaster TSS-style header with run metadata and gauge count.

            Parameters
            ----------
            outputFilename : str
                Full path to output TSS file
            expression : list
                Output configuration containing gauge information and metadata

            Notes
            -----
            Creates traditional PCRaster TSS header format with:
            - Single line metadata (settings, date, version, git info)
            - Number of data columns (timestep + gauge columns)
            - Column identifiers starting with 'timestep'
            - Gauge IDs as column headers
            
            Maintains compatibility with PCRaster and traditional CWatM
            time series processing tools.
            """

            outputFile = open(outputFilename, "w")
            # header
            # outputFile.write("timeseries " + self._spatialDatatype.lower() + "\n")
            header = "timeseries " + " settingsfile: " + os.path.realpath(settingsfile[0]) + " date: " + xtime.ctime(xtime.time())
            header += " CWATM: " + versioning['exe']  + ", " +versioning['lastdate']
            try:
                import git
                header += "git commit " + git.Repo(search_parent_directories=True).head.object.hexsha
            except:
                ii = 1
            header += "\n"

            outputFile.write(header)
            if len(expression[3]):
                numbervalues = len(expression[3][0]) + 1
            else: numbervalues = 0

            outputFile.write(str(numbervalues) + "\n")
            outputFile.write("timestep\n")
            for key in sorted(self.var.sampleAdresses):
                outputFile.write(str(key) + "\n")
            outputFile.close()

        # ************************************************************
        # ***** WRITING RESULTS: TIME SERIES *************************
        # ************************************************************

        # xxx=catchmenttotal(self.var.SurfaceRunForest * self.var.PixelArea, self.var.Ldd) * self.var.InvUpArea
        # self.var.Tss['DisTS'].sample(xxx)
        # self.report(self.Precipitation,cbinding('TaMaps'))


        def sample_maptotxt(expression, map):
            """
            Export spatial map data to text file for debugging and analysis.

            Parameters
            ----------
            expression : list
                Output configuration containing filename and variable information
            map : numpy.ndarray
                1D compressed array with spatial data to export

            Notes
            -----
            Creates simple text dump files with:
            - Model run metadata header
            - Variable name and cell count information
            - One value per line for all valid cells
            - Values scaled by 1000 and rounded to 3 decimal places
            
            Used primarily for total aggregation outputs and debugging
            spatial patterns. Files have .txt extension regardless of
            original output filename.
            """
            size = map.shape[0]

            outputFilename = os.path.splitext(expression[0])[0] + ".txt"
            outputFile = open(outputFilename, "w")
            outputFile.write("Map_dump " + " settingsfile: " + os.path.realpath(settingsfile[0]) + " date: " + xtime.ctime(xtime.time()) + "\n")
            outputFile.write("Parameter: " + expression[1] + "\n")
            outputFile.write("Number of cells: " + str(size) + "\n")

            for i in range(size):
                v = "%.3f\n" % round(1000. * map[i],3)
                outputFile.write(v)
            outputFile.close()









        # ************************************************************

        # ***** WRITING RESULTS: MAPS   ******************************
        # ************************************************************

        # print '----------------#'
        varname = None
        varnameCollect = []
        # set this tru if only the valid cell are stored in netcdf
        nindex = self.var.netcdfasindex
        if dateVar['curr'] >= dateVar['intSpin'] or ef:
            for map in list(outMap.keys()):
                for i in range(outMap[map].__len__()):
                    if outMap[map][i] != "None":

                        netfile = outMap[map][i][0]
                        flag = outMap[map][i][2]
                        # flag to create netcdf or to write
                        varname = outMap[map][i][1]
                        type = outMap[map][i][4]

                        # to use also variables with index from soil e.g. actualET[2]
                        if '[' in varname:
                            checkname = varname[0:varname.index("[")]
                        else:
                            checkname = varname
                        checkifvariableexists(map,checkname, list(vars(self.var).keys()))

                        varnameCollect.append(varname)
                        inputmap = 'self.var.' + varname

                        # create variable after it is checked on the first timestep
                        # creates a var to sum/ average the results e.g. self.var.Precipitation_monthtot
                        if dateVar['curr'] == dateVar['intSpin']:
                            vars(self.var)[varname+"_"+type] = 0

                        if map[-5:] == "daily":
                            outMap[map][i][2] = writenetcdf(netfile, varname,"", "undefined", eval(inputmap),  dateVar['currDate'],dateVar['currwrite'],
                                                            flag, True, dateVar['diffdays'],netcdfindex=nindex)
                        if map[-8:] == "monthend":
                            if dateVar['checked'][dateVar['currwrite'] - 1]>0:
                                outMap[map][i][2] = writenetcdf(netfile, varname, "_monthend", "undefined", eval(inputmap),  dateVar['currDate'], dateVar['currMonth'],
                                                                flag,True,dateVar['diffMonth'],netcdfindex=nindex)
                        if map[-8:] == "monthtot":
                            # sum up daily value to monthly values
                            vars(self.var)[varname + "_monthtot"] = vars(self.var)[varname + "_monthtot"] +  eval(inputmap)
                        if map[-8:] == "monthavg":
                            #vars(self.var)[varname + "_monthavg"] = vars(self.var)[varname + "_monthavg"] + vars(self.var)[varname]
                            vars(self.var)[varname + "_monthavg"] = vars(self.var)[varname + "_monthavg"] +  eval(inputmap)

                        if map[-4:] == "once":
                            if (returnBool('calc_ef_afterRun') == False) or (dateVar['currDate'] == dateVar['dateEnd']):
                                # either load already calculated discharge or at the end of the simulation
                                outMap[map][i][2] = writenetcdf(netfile, varname,"", "undefined", eval(inputmap),
                                                            dateVar['currDate'], dateVar['currwrite'], flag, False,netcdfindex=nindex)
                        if map[-7:] == "12month":
                            if (returnBool('calc_ef_afterRun') == False) or (dateVar['currDate'] == dateVar['dateEnd']):
                                # either load already calculated discharge or at the end of the simulation
                                flag1 = False # create new netcdf file
                                for j in range(12):
                                    in1 = inputmap  + '[' +str(j) + ']'
                                    date1 = datetime.datetime(dateVar['dateEnd'].year, j+1, 1, 0, 0)
                                    outMap[map][i][2] = writenetcdf(netfile, varname,"", "undefined", eval(in1), date1, j+1,
                                                                    flag1, True,12,netcdfindex=nindex)
                                    flag1 = True # now append to netcdf file


                        # if end of month is reached
                        if dateVar['checked'][dateVar['currwrite'] - 1]>0:
                            #if (map[-8:] == "monthend"):
                            #    outMap[map][i][2] = writenetcdf(netfile, varname,"_monthend", "undefined", eval(inputmap+ "_monthend"), #dateVar['currDate'], dateVar['currMonth'], flag, True,
                            #                                    dateVar['diffMonth'],dateunit="months")
                            if map[-8:] == "monthtot":
                                outMap[map][i][2] = writenetcdf(netfile, varname,"_monthtot", "undefined", eval(inputmap+ "_monthtot"), dateVar['currDate'],
                                                                dateVar['currMonth'], flag, True, dateVar['diffMonth'],dateunit="months",netcdfindex=nindex)
                                #vars(self.var)[varname + "monthtot"] = 0
                            if map[-8:] == "monthavg":
                                #days = calendar.monthrange(dateVar['currDate'].year, dateVar['currDate'].month)[1]
                                avgmap = vars(self.var)[varname + "_monthavg"] / dateVar['daysInMonth']
                                outMap[map][i][2] = writenetcdf(netfile, varname,"_monthavg", "undefined", avgmap,dateVar['currDate'], dateVar['currMonth'],
                                                                flag, True,dateVar['diffMonth'],dateunit="months",netcdfindex=nindex)
                                #vars(self.var)[varname+"monthavg"] = 0



                        if map[-9:] == "annualend":
                            if dateVar['checked'][dateVar['currwrite'] - 1]==2:
                                outMap[map][i][2] = writenetcdf(netfile, varname,"_annualend", "undefined", eval(inputmap),  dateVar['currDate'], dateVar['currYear'],
                                                                flag,True,dateVar['diffYear'], dateunit="years", netcdfindex=nindex)
                        if map[-9:] == "annualtot":
                            vars(self.var)[varname + "_annualtot"] = vars(self.var)[varname + "_annualtot"] + vars(self.var)[varname]
                        if map[-9:] == "annualavg":
                            #vars(self.var)[varname2 + "_annualavg"] = vars(self.var)[varname2 + "_annualavg"] + vars(self.var)[varname]
                            vars(self.var)[varname + "_annualavg"] = vars(self.var)[varname + "_annualavg"] + eval(inputmap)

                        if dateVar['checked'][dateVar['currwrite'] - 1]==2:
                            if map[-9:] == "annualtot":
                                    outMap[map][i][2] = writenetcdf(netfile, varname,"_annualtot", "undefined", eval(inputmap+ "_annualtot"), dateVar['currDate'], dateVar['currYear'], flag, True,
                                                                    dateVar['diffYear'], dateunit="years", netcdfindex=nindex)
                            if map[-9:] == "annualavg":
                                        days = 366 if calendar.isleap(dateVar['currDate'].year) else 365
                                        avgmap = vars(self.var)[varname + "_annualavg"] / days
                                        outMap[map][i][2] = writenetcdf(netfile, varname,"_annualavg", "undefined", avgmap, dateVar['currDate'], dateVar['currYear'], flag, True,
                                                                        dateVar['diffYear'],dateunit="years", netcdfindex=nindex)
                                    #vars(self.var)[varname+"annualtot"] = 0


                        if map[-8:] == "totaltot":
                            if dateVar['curr'] >= dateVar['intSpin']:
                                vars(self.var)[varname + "_totaltot"] = vars(self.var)[varname + "_totaltot"] + vars(self.var)[varname]
                                if dateVar['currDate'] == dateVar['dateEnd']:
                                    # at the end of simulation write this map
                                    outMap[map][i][2] = writenetcdf(netfile, varname,"_totaltot", "undefined", eval(inputmap +  "_totaltot"),
                                                                dateVar['currDate'], dateVar['currwrite'], flag, False, netcdfindex=nindex)

                        if map[-8:] == "totalavg":
                            if dateVar['curr'] >= dateVar['intSpin']:
                                vars(self.var)[varname + "_totalavg"] = vars(self.var)[varname + "_totalavg"] + vars(self.var)[varname]/ float(dateVar['diffdays'])
                                if dateVar['currDate'] == dateVar['dateEnd']:
                                    # at the end of simulation write this map
                                    outMap[map][i][2] = writenetcdf(netfile, varname,"_totalavg", "undefined", eval(inputmap + "_totalavg"),
                                                                    dateVar['currDate'], dateVar['currwrite'], flag, False, netcdfindex=nindex)

                        if map[-8:] == "totalend":
                            if dateVar['currDate'] == dateVar['dateEnd']:
                                # at the end of simulation write this map
                                vars(self.var)[varname + "_totalend"] = vars(self.var)[varname]
                                outMap[map][i][2] = writenetcdf(netfile, varname,"_totalend","undefined", vars(self.var)[varname],
                                                                dateVar['currDate'], dateVar['currwrite'], flag, False, netcdfindex=nindex)


                                # ************************************************************
        # ***** WRITING RESULTS: TIME SERIES *************************
        # ************************************************************

        self.var.firstout = firstout(self.var.discharge)

        if Flags['gui']:
            # if CWatM is started from a GUI - update the progress clock
            if hasattr(self.var, 'meteo') and hasattr(self.var.meteo, 'progress_clock'):
                # Calculate progress percentage based on dates
                total_days = dateVar['intEnd'] - dateVar['intStart'] + 1
                current_day = dateVar['curr'] - dateVar['intStart'] + 1
                progress_percent = min(100, max(0, int((current_day / total_days) * 100)))
                self.var.meteo.progress_clock.setValue(progress_percent)



        if Flags['loud']:
            print("\r%-6i %10s %10.2f     " %(dateVar['currStart'],dateVar['currDatestr'],self.var.firstout), end='')
            sys.stdout.flush()

        else:
            if not(Flags['check']):
                if (Flags['quiet']) and (not(Flags['veryquiet'])):
                    sys.stdout.write(".")
                if (not(Flags['quiet'])) and (not(Flags['veryquiet'])):
                    print("\r%d   " % dateVar['currStart'],end ='')
                    sys.stdout.flush()

        # report TSS
        for tss in list(outTss.keys()):
            for i in range(outTss[tss].__len__()):
                # loop for each variable in a section
                if outTss[tss][i] != "None":
                    varname = outTss[tss][i][1]
                    varnameCollect.append(varname)
                    what = 'self.var.' + outTss[tss][i][1]

                    # to use also variables with index from soil e.g. actualET[2]
                    if '[' in varname:
                        checkname = varname[0:varname.index("[")]
                    else:
                        checkname = varname
                    checkifvariableexists(tss, checkname, list(vars(self.var).keys()))

                    if tss[-5:] == "daily":
                        # what = 'self.var.' + reportTimeSerieAct[tss]['outputVar'][0]
                        # how = reportTimeSerieAct[outTss[tss][0][0]]['operation'][0]
                        # if how == 'mapmaximum':
                        # changed = compressArray(mapmaximum(decompress(eval(what))))
                        # what = 'changed'
                        # if how == 'total':
                        # changed = compressArray(catchmenttotal(decompress(eval(what)) * self.var.PixelAreaPcr,self.var.Ldd) * self.var.InvUpArea)
                        # what = 'changed'
                        # print i, outTss[tss][i][1], what
                        if checkOption('reportsnowstations',True):
                            if not (Flags['calib']):
                                outTss[tss][i] = sample4(outTss[tss][i],what,0)
                        else:
                            outTss[tss][i] = sample3(outTss[tss][i], eval(what), 0)

                    if tss[-8:] == "monthend":
                        # reporting at the end of the month:
                        outTss[tss][i] = sample3(outTss[tss][i], eval(what), 1)

                    if tss[-8:] == "monthtot":
                        # if  monthtot is not calculated it is done here
                        if (varname + "_monthtotTss") in vars(self.var):
                            vars(self.var)[varname + "_monthtotTss"] = vars(self.var)[varname + "_monthtotTss"] + vars(self.var)[varname]
                        else:
                            vars(self.var)[varname + "_monthtotTss"] = vars(self.var)[varname]
                        outTss[tss][i] = sample3(outTss[tss][i], eval(what + "_monthtotTss"), 1)

                    if tss[-8:] == "monthavg":
                        if (varname + "_monthavgTss") in vars(self.var):
                            vars(self.var)[varname + "_monthavgTss"] =  vars(self.var)[varname + "_monthavgTss"] + vars(self.var)[varname]
                        else:
                            vars(self.var)[varname + "_monthavgTss"] = 0
                            vars(self.var)[varname + "_monthavgTss"] = vars(self.var)[varname + "_monthavgTss"] + vars(self.var)[varname]
                        avgmap = vars(self.var)[varname + "_monthavgTss"] /  dateVar['daysInMonth']
                        outTss[tss][i] = sample3(outTss[tss][i], avgmap, 1)




                    if tss[-9:] == "annualend":
                        # reporting at the end of the month:
                        #outTss[tss][i][0].sample2(decompress(eval(what)), 2)
                        outTss[tss][i] = sample3(outTss[tss][i], eval(what), 2)

                    if tss[-9:] == "annualtot":

                        if (varname + "_annualtotTss") in vars(self.var):
                            vars(self.var)[varname + "_annualtotTss"] = vars(self.var)[varname + "_annualtotTss"] + vars(self.var)[varname]
                        else:
                            vars(self.var)[varname + "_annualtotTss"] = vars(self.var)[varname]
                        outTss[tss][i] = sample3(outTss[tss][i], eval(what + "_annualtotTss"), 2)

                    if tss[-9:] == "annualavg":
                        if (varname + "_annualavgTss") in vars(self.var):
                            vars(self.var)[varname + "_annualavgTss"] = vars(self.var)[varname + "_annualavgTss"] + vars(self.var)[varname]
                        else:
                            vars(self.var)[varname + "_annualavgTss"] = vars(self.var)[varname]
                        avgmap = vars(self.var)[varname + "_annualavgTss"] /dateVar['daysInYear']
                        #outTss[tss][i][0].sample2(decompress(avgmap), 2)
                        outTss[tss][i] = sample3(outTss[tss][i], avgmap, 2)

                    if tss[-8:] == "totaltot":
                        if dateVar['curr'] >= dateVar['intSpin']:
                            if (varname + "_totaltotTss") in vars(self.var):
                                vars(self.var)[varname + "_totaltotTss"] =  vars(self.var)[varname + "_totaltotTss"] + vars(self.var)[varname]
                            else:
                                vars(self.var)[varname + "_totaltotTss"] = vars(self.var)[varname]
                            if dateVar['currDate'] == dateVar['dateEnd']:
                                #outTss[tss][i] = sample_maptotxt(outTss[tss][i],  eval(what + "_totaltotTss"))
                                sample_maptotxt(outTss[tss][i], eval(what + "_totaltotTss"))

                    if tss[-8:] == "totalavg":
                        if dateVar['curr'] >= dateVar['intSpin']:
                            if (varname + "_totalavgTss") in vars(self.var):
                                vars(self.var)[varname + "_totalavgTss"] = vars(self.var)[varname + "_totalavgTss"] + vars(self.var)[varname] / float(dateVar['diffdays'])
                            else:
                                vars(self.var)[varname + "_totalavgTss"] = vars(self.var)[varname] / float(dateVar['diffdays'])
                            if dateVar['currDate'] == dateVar['dateEnd']:
                                #outTss[tss][i] = sample_maptotxt(outTss[tss][i], eval(what + "_totalavgTss"))
                                sample_maptotxt(outTss[tss][i], eval(what + "_totalavgTss"))

        # if end of month is reached all monthly storage is set to 0
        #if not(varname is None):
        for varname in varnameCollect:
            if dateVar['checked'][dateVar['currwrite'] - 1] > 0:
                if (varname + "_monthtot") in vars(self.var):
                    vars(self.var)[varname + "_monthtot"] = 0
                if (varname + "_monthavg") in vars(self.var):
                    vars(self.var)[varname + "_monthavg"] = 0
                if (varname + "_monthtotTss") in vars(self.var):
                    vars(self.var)[varname + "_monthtotTss"] = 0
                if (varname + "_monthavgTss") in vars(self.var):
                    vars(self.var)[varname + "_monthavgTss"] = 0

            if dateVar['checked'][dateVar['currwrite'] - 1] == 2:
                if (varname + "_annualtot") in vars(self.var):
                    vars(self.var)[varname + "_annualtot"] = 0
                if (varname + "_annualavg") in vars(self.var):
                    vars(self.var)[varname + "_annualavg"] = 0
                if (varname + "_annualtotTss") in vars(self.var):
                    vars(self.var)[varname + "_annualtotTss"] = 0
                for ii in range(self.var.noOutpoints):
                    if (varname + "_annualtotTss"+str(ii)) in vars(self.var):
                        vars(self.var)[varname + "_annualtotTss"+str(ii)] = 0
                if (varname + "_annualavgTss") in vars(self.var):
                    vars(self.var)[varname + "_annualavgTss"] = 0

