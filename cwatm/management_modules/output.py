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
from packaging import version # DF 29092026

import numpy as np
import pandas as pd
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
    fracGlacierCover                     Array         Fraction of glacier cover in a grid cell                                %    
    meteo                                Array         store all meteo data in memeory for warm start (eg calibration)         compl
    sampleAdresses                       List          outflowpoints as 1D index                                               --   
    outpoints                            List          output points (Gauges)                                                  --   
    noOutpoints                          Number        number of output points                                                 --   
    evalCatch                            Array         indeces of a subbasin in the mask                                       --   
    catcharea                            Array         catchment area of the subbaSIN                                          m2   
    watercycle                           List                                                                                  --   
    netcdfasindex                        Flag          save netcdf file in a compressed way - for splitting runs in several b  bool 
    firstout                             Number        discharge of the first gauge                                            m3 s-
    discharge                            Array         Channel discharge                                                       m3 s-
    usepySnowClim                        Flag          Flag to use pySnowClim                                                  --   
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

            for i in np.flatnonzero(out > 0):
                if out[i] in sampleAdresses:
                    msg = "Gauge number " + str(out[i]) + " is used for more than one cell in the gauge map - only the last cell is used"
                    print(CWATMWarning(msg))
                sampleAdresses[out[i]] = i

            # coordinates in the same order as the output columns (sorted gauge numbers)
            for key in sorted(sampleAdresses):
                i = sampleAdresses[key]
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
                cell = arange[row[i], col[i]]
                if cell < 0:
                    msg = "Error 134: Coordinates: x = " + coord[i * 2] + "  y = " + coord[i * 2 + 1] + " of gauge " + str(i + 1) + " are inside the box of the mask map but on a cell outside the mask\n"
                    msg += "Please have a look at \"MaskMap\" or \"Gauges\""
                    raise CWATMError(msg)
                self.var.sampleAdresses[i + 1] = cell

            self.var.outpoints = list(map(float, outpoints.split(" ")))

        else:
            if os.path.exists(outpoints):
                outpoints = loadmap(where, local=localGauges).astype(np.int64)
                # gauges on cells outside the mask are lost when the map is compressed -> warning
                gaugemap = np.nan_to_num(np.ma.filled(loadmap(where, compress=False, local=localGauges), 0).astype(np.float64))
                lost = np.setdiff1d(gaugemap[gaugemap > 0].astype(np.int64), outpoints[outpoints > 0])
                if lost.size > 0:
                    msg = "Gauges " + ", ".join(str(g) for g in lost) + " in \"Gauges\" are on cells outside the mask map - no output for them"
                    print(CWATMWarning(msg))
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

        # check if catchment area calculation is necessary (areaavg, areasum or WaterCycle output)
        calcCatch = False
        for s in filter(lambda x: "areaavg" in x, outTss.keys()):
            calcCatch = True
        for s in filter(lambda x: "areasum" in x, outTss.keys()):
            calcCatch = True
        for out in outTss.values():
            # here outTss still has the variable names (appendinfo is called later)
            if "WaterCycle" in out:
                calcCatch = True

        if calcCatch:
            self.var.evalCatch = {}
            self.var.catcharea = {}
            # cells of each catchment (in increasing order) and a label 0 for each of them -> sums only over the catchment
            self.var.catchIndex = {}
            self.var.catchZero = {}

            for key in sorted(self.var.sampleAdresses):
                outp = globals.inZero.copy()
                outp[self.var.sampleAdresses[key]] = key

                self.var.evalCatch[key] = catchment1(self.var.dirUp, outp)
                self.var.catcharea[key] = np.bincount(self.var.evalCatch[key], weights=self.var.cellArea)[key]
                self.var.catchIndex[key] = np.flatnonzero(self.var.evalCatch[key] == key)
                self.var.catchZero[key] = np.zeros(len(self.var.catchIndex[key]), dtype=np.int64)


        # for storing water cycle variable the list of variables if pulled together
        self.var.watercycle = [['precipitation_sn', 'areasum_m3', 'flux'], ['Rain', 'areasum_m3', 'flux'], ['Snow', 'areasum_m3', 'flux'],
                      ['SnowMelt','areasum_m3','flux'],['IceMelt', 'areasum_m3', 'flux'],
                      ['runoff', 'areasum_m3','flux'], ['runoff_m3','sum_m3', 'flux'], ['baseflow', 'areasum_m3', 'flux'],
                      ['totalET', 'areasum_m3', 'evap'], ['sum_actTransTotal', 'areasum_m3', 'evap'],
                      ['sum_actBareSoilEvap','areasum_m3', 'evap'], ['sum_interceptEvap', 'areasum_m3', 'evap'], ['sum_openWaterEvap', 'areasum_m3', 'evap'],
                      ['snowEvap', 'areasum_m3', 'evap'], ['EvapoChannel', 'areasum_m3', 'evap'],
                      ['actTransTotal_forest', 'areasum_m3', 'evap'], ['actTransTotal_grasslands', 'areasum_m3', 'evap'],['actTransTotal_paddy', 'areasum_m3', 'evap'], ['actTransTotal_nonpaddy', 'areasum_m3', 'evap'],

                      ['tws', 'areasum_m3', 'storage'],['totalSto','areasum_m3','storage'],
                      ['SnowCover', 'areasum_m3', 'storage'],['sum_interceptStor', 'areasum_m3', 'storage'],['sum_soil', 'areasum_m3', 'storage'],
                      ['storGroundwater','areasum_m3', 'storage'], ['channelStorage', 'sum_m3', 'storage'],

                      ['discharge', 'm3s-1', 'discharge'], ['avgdischarge', 'm3s-1', 'discharge'], ['cellArea', 'sum_m3', 'area']]


        if self.var.usepySnowClim:
            temp =  [['Rain_on_snow', 'areasum_m3', 'flux'],['packwater', 'areasum_m3', 'storage'],['snowReset', 'areasum_m3', 'flux'],
                    ['snowwaterevaporation', 'areasum_m3', 'flux'],['sublimation', 'areasum_m3', 'flux'],
                    ['condensation', 'areasum_m3', 'flux'],['depostition', 'areasum_m3', 'flux'],
                    ['refrozen', 'areasum_m3', 'flux'],['snowmelt1', 'areasum_m3', 'flux']
                    ]
            self.var.watercycle.extend(temp)
        if checkOption('CapillarRise'):
            temp = [['sum_capRiseFromGW','areasum_m3','flux']]
            self.var.watercycle.extend(temp)

        # Always percolation
        temp = [['sum_gwRecharge', 'areasum_m3', 'flux'], ['sum_gwRecharge2', 'areasum_m3', 'flux'],['perc3toGW_GW','areasum_m3','flux']]
        self.var.watercycle.extend(temp)
        if checkOption('preferentialFlow'):
            temp = [['prefFlow_GW','areasum_m3','flux']]
            self.var.watercycle.extend(temp)
        if self.var.includeGlaciers:
            temp = [['GlacierMelt','sum_m3','glacier'],['GlacierRain','sum_m3','glacier'],['areaGlacier','sum_m3','glacier']]
            self.var.watercycle.extend(temp)
        if checkOption('includeRunoffConcentration'):
            temp = [['gridcell_storage','areasum_m3','storage']]
            self.var .watercycle.extend(temp)


        # waterbodies
        if checkOption('includeWaterBodies'):
            temp = [['lakeResStorage','sum_m3','storage'],['EvapWaterBodyM','areasum_m3','lake'],
                    ['lakeResInflowM','areasum_m3','lake'],['lakeResOutflowM','areasum_m3','lake'],
                    ['act_bigLakeResAbst','areasum_m3','lake']]
            self.var.watercycle.extend(temp)
        if checkOption('includeWaterBodies') and returnBool('useSmallLakes'):
            temp = [['smalllakeStorage','sum_m3','storage'],['smallevapWaterBody','areasum_m3','smallake']]
            self.var.watercycle.extend(temp)

        # Waterdemand
        if checkOption('includeWaterDemand'):
            temp = [['addtoevapotrans','areasum_m3','demand'],['unmet_lost','areasum_m3','demand'],['unmetDemand','areasum_m3','demand'],
                    ['act_nonIrrConsumption','areasum_m3','demand'],['act_totalIrrConsumption','areasum_m3','demand'],
                    ['act_nonpaddyConsumption','areasum_m3','demand'],['act_paddyConsumption','areasum_m3','demand'],['act_livConsumption','areasum_m3','demand'],
                    ['act_indConsumption','areasum_m3','demand'],['act_domConsumption','areasum_m3','demand'],
                    ['act_irrWithdrawal','areasum_m3','demand'],['act_nonIrrWithdrawal','areasum_m3','demand'],['act_domWithdrawal','areasum_m3','demand'],
                    ['act_indWithdrawal','areasum_m3','demand'],['act_livWithdrawal','areasum_m3','demand'],['act_SurfaceWaterAbstract','areasum_m3','demand'],
                    ['act_irrNonpaddyWithdrawal','areasum_m3','demand'],['pot_GroundwaterAbstract','areasum_m3','demand'],['nonFossilGroundwaterAbs','areasum_m3','demand'],
                    ['returnFlow','areasum_m3','demand'],
                    ['returnflowIrr','areasum_m3','demand'],['returnflowNonIrr','areasum_m3','demand']]
            self.var.watercycle.extend(temp)

        if 'sectorSourceAbstractionFractions' in option:
            if checkOption('sectorSourceAbstractionFractions'):
                temp = [['Lake_Irrigation','areasum_m3','sector'],['Lake_Industry','areasum_m3','sector'],['Lake_Livestock','areasum_m3','sector'],
                        ['Lake_Domestic','areasum_m3','sector'],['Channel_Irrigation','areasum_m3','sector'],['Channel_Domestic','areasum_m3','sector'],
                        ['Channel_Livestock','areasum_m3','sector'],['Channel_Industry','areasum_m3','sector'],['GW_Irrigation','areasum_m3','sector'],
                        ['GW_Industry','areasum_m3','sector'],['GW_Livestock','areasum_m3','sector'],['GW_Domestic','areasum_m3','sector'],
                        ['Res_Irrigation','areasum_m3','sector'],['Res_Industry','areasum_m3','sector'],['Res_Livestock','areasum_m3','sector'],
                        ['Res_Domestic','areasum_m3','sector']]
                self.var.watercycle.extend(temp)

        # Modflow
        if self.var.modflow:
            temp = [['leakageIntoGw','areasum_m3','Modflow'],['leakageIntoRunoff','areasum_m3','Modflow'],['riverbedExchangeM','areasum_m3','Modflow'],
                    ['lakebedExchangeM','areasum_m3','Modflow'],['leakage','areasum_m3','Modflow'],['Pumping_daily','areasum_m3','Modflow'],
                    ['modfPumpingM_actual','areasum_m3','Modflow'],['groundwater_storage_available','areasum_m3','Modflow']]
            self.var.watercycle.extend(temp)

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

        # check the names of all output variables once at the start (instead of eval of the names in dynamic)
        self.outvarparsed = {}
        for out in list(outTss.values()) + list(outMap.values()):
            for entry in out:
                if entry != "None":
                    self.outvarparsed[entry[1]] = parseoutvar(entry[1])

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
            # adding expression WaterCycle to space to avoid error if watercycle should be stored
            space.append("WaterCycle")

            if not (vari in space):
                closest = difflib.get_close_matches(vari, space)
                if not closest: closest = ["- no match -"]
                msg = "Error 132: Variable \"" + vari + "\" is not defined in \""+ name+"\"\n"
                msg += "Closest variable to this name is: \"" + closest[0] + "\""
                raise CWATMError(msg)

        def catchsum(weights, key):
            """
            Sum of weights over the catchment of gauge key.

            Same result as np.bincount(self.var.evalCatch[key], weights=weights)[key] (same cells in the same
            order, starting with 0.0 -> bit-identical) but only the cells of the catchment are used.
            """
            return np.bincount(self.var.catchZero[key], weights=weights[self.var.catchIndex[key]], minlength=1)[0]


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

            # if inputmap is a scalar (e.g. a variable which is 0 if an option is off) use this value for all cells
            # (skipping the time step would shift all following dates)
            if not (hasattr(map, '__len__')):
                map = map + globals.inZero

            areatype = expression[0].split('_')[-2]
            if areatype in ['areaavg','areasum']:
                # weights calculated once and used for all gauges
                weights = map * self.var.cellArea
            for key in sorted(self.var.sampleAdresses):
                if areatype in ['areaavg','areasum']:
                    # value from catchment
                    v = catchsum(weights, key)

                    if areatype == 'areaavg':
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

        def sample_watercycle(expression, daymonthyear):
            """
            Sample values at gauge points and accumulate for time series output.

            Parameters
            ----------
            expression : list
                Output configuration containing [filename, variable, format_flag, data_list, type]
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

            # the values of this time step are the same for all WaterCycle outputs (daily, monthtot, annualtot)
            # -> calculated only for the first one, the others use them from watercycleToday
            if not watercycleToday:
                keys = sorted(self.var.sampleAdresses)
                nofrac = 1 - self.var.fracGlacierCover
                # value[gauge][variable]; the weights of a variable are calculated once and used for all gauges
                value = [[] for key in keys]
                for var in self.var.watercycle:
                    map = getattr(self.var, var[0])
                    # if inputmap is a scalar (e.g. a variable which is 0 if an option is off) use this value for all cells
                    # (skipping the time step would shift all following dates)
                    if not (hasattr(map, '__len__')):
                        map = map + globals.inZero

                    if var[1] in ['areasum_m3']:  # value from catchment
                        if var[2] in ['demand','sector']:
                            weights = map * self.var.cellArea
                        else:
                            weights = map * self.var.cellArea * nofrac
                    elif var[1] in ['sum_m3']:  # value summed up but without  cellarea
                        weights = map
                    else:  # from single cell for discharge only
                        weights = None

                    for k, key in enumerate(keys):
                        if weights is None:
                            value[k].append(map[self.var.sampleAdresses[key]])
                        else:
                            value[k].append(catchsum(weights, key))
                # end loop variables
                watercycleToday.append(value)

            expression[3].append(watercycleToday[0])

            if dateVar['laststep']:
               writeTssFileNew(expression, daymonthyear,True)

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

        def writeTssFileNew(expression, daymonthyear, flagCycle = False):
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
                if flagCycle:
                    writeFileHeaderWaterCycle(outputFilename, expression)
                    dates = pd.date_range(start=dateVar['dateStart1'], end=dateVar['dateEnd1'], freq="D")
                    # reformat expression: not the best solution
                    # expression: 1: timesteps 2: stations 3: 79 vars eg expression[3][211][0][78]
                    #expression[3] = np.array(expression[3]).transpose(1, 0, 2)
                    # DF 29092026
                    expression[3] = np.array(expression[3][(dateVar['intSpin'] - 1):(dateVar['intEnd'])]).transpose(1, 0, 2)
                    totals = []
                    storage = []
                    
                    # DF 29092026
                    if version.parse(pd.__version__) >= version.parse("2.2.0"):
                        FREQ_MONTH = "ME"
                        FREQ_YEAR = "YE"
                    else:
                        FREQ_MONTH = "M"
                        FREQ_YEAR = "Y"
                    
                    for k in range(len(self.var.sampleAdresses)):
                        df = pd.DataFrame(expression[3][k], index=dates)
                        if daymonthyear == 1:
                            #totals.append(df.resample("ME").sum())
                            totals.append(df.resample(FREQ_MONTH).sum())
                            #storage.append(df.resample("ME").last())
                            storage.append(df.resample(FREQ_MONTH).last())
                        elif daymonthyear == 2:
                            #totals.append(df.resample("YE").sum())
                            totals.append(df.resample(FREQ_YEAR).sum())
                            #storage.append(df.resample("YE").last())
                            storage.append(df.resample(FREQ_YEAR).last())
                        else:
                            totals.append(df.resample("D").sum())
                            storage.append(df.resample("D").last())
                    
                else:
                    writeFileHeaderNew(outputFilename,expression)
                outputFile = open(outputFilename, "a")
            else:
                outputFile = open(outputFilename, "w")

            assert outputFile
            if len(expression[3]):
                numbervalues = len(expression[3][0])

                if flagCycle:
                    numbervalues = len(expression[3][0][0])
                    # run for watercycle and monthly or yearly
                    # per gauge one numpy array (storage variables: last value, others: total) instead of iloc per value
                    isstorage = np.array([var[2] == "storage" for var in self.var.watercycle])
                    values = [np.where(isstorage, storage[k].to_numpy(), totals[k].to_numpy()) for k in range(len(self.var.sampleAdresses))]
                    for i, timestamp in enumerate(totals[0].index):
                        row = timestamp.strftime('%d/%m/%Y')
                        for k in range(len(self.var.sampleAdresses)):
                            for j in range(numbervalues):
                                row += ",%13.10g" % values[k][i, j]
                        row += "\n"
                        outputFile.write(row)

                else:
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
                                    row += ",%13.10g" % value
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
            for key in sorted(self.var.sampleAdresses):
                head = head + ",G" + str(key)
            head = head + "\n"

            outputFile.write(xrow)
            outputFile.write(yrow)
            outputFile.write(head)

            outputFile.close()

        def writeFileHeaderWaterCycle(outputFilename, expression):
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
                for i in self.var.watercycle:
                    xrow = xrow + "," + "%#.4f" % round(x, 4)
            xrow = xrow + "\n"
            for y in loc[1::2]:
                for i in self.var.watercycle:
                    yrow = yrow + "," + "%#.4f" % round(y, 4)
            yrow = yrow + "\n"

            for i in range(len(loc[::2])):
                for var in self.var.watercycle:
                    head = head + "," + var[0] + "_" + var[1]
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
        # water cycle values of this time step: calculated once and used for all WaterCycle outputs (daily, monthtot ...)
        watercycleToday = []
        # set this tru if only the valid cell are stored in netcdf
        nindex = self.var.netcdfasindex
        # number of days which are summed up in the current month/year for monthavg/annualavg
        # (less than the days of the month/year if output starts in the middle of a month/year, e.g. after spin-up)
        daysWritten = max(1, (dateVar['currDate'] - dateVar['dateStart1']).days + 1)
        daysMonthAvg = min(dateVar['currDate'].day, daysWritten)
        daysYearAvg = min(dateVar['doy'], daysWritten)
        if dateVar['curr'] >= dateVar['intSpin'] or ef:
            for map in list(outMap.keys()):
                for i in range(outMap[map].__len__()):
                    if outMap[map][i] != "None":

                        netfile = outMap[map][i][0]
                        flag = outMap[map][i][2]
                        # flag to create netcdf or to write
                        varname = outMap[map][i][1]
                        type = outMap[map][i][4]

                        # to use also variables with index from soil e.g.prefFlow[2]
                        # name and indices are checked once in initial (parseoutvar) - no eval of names from the settings file
                        checkname, index = self.outvarparsed[varname]
                        varname2 = varname.replace("[", "_").replace("]", "_")
                        checkifvariableexists(map,checkname, list(vars(self.var).keys()))

                        varnameCollect.append(varname2)

                        # create variable after it is checked on the first timestep
                        # creates a var to sum/ average the results e.g. self.var.Precipitation_monthtot
                        if dateVar['curr'] == dateVar['intSpin']:
                            vars(self.var)[varname2 + "_" + type] = 0

                        if map[-5:] == "daily":
                            outMap[map][i][2] = writenetcdf(netfile, varname,"", "undefined", getoutvar(self.var, checkname, index),  dateVar['currDate'],dateVar['currwrite'],
                                                            flag, True, dateVar['diffdays'],netcdfindex=nindex)
                        if map[-8:] == "monthend":
                            if dateVar['checked'][dateVar['currwrite'] - 1]>0:
                                outMap[map][i][2] = writenetcdf(netfile, varname, "_monthend", "undefined", getoutvar(self.var, checkname, index),  dateVar['currDate'], dateVar['currMonth'],
                                                                flag,True,dateVar['diffMonth'],netcdfindex=nindex)
                        if map[-8:] == "monthtot":
                            # sum up daily value to monthly values
                            vars(self.var)[varname2 + "_monthtot"] = vars(self.var)[varname2 + "_monthtot"] +  getoutvar(self.var, checkname, index)
                        if map[-8:] == "monthavg":
                            vars(self.var)[varname2 + "_monthavg"] = vars(self.var)[varname2 + "_monthavg"] +  getoutvar(self.var, checkname, index)

                        if map[-4:] == "once":
                            if (returnBool('calc_ef_afterRun') == False) or (dateVar['currDate'] == dateVar['dateEnd']):
                                # either load already calculated discharge or at the end of the simulation
                                outMap[map][i][2] = writenetcdf(netfile, varname,"", "undefined", getoutvar(self.var, checkname, index),
                                                            dateVar['currDate'], dateVar['currwrite'], flag, False,netcdfindex=nindex)
                        if map[-7:] == "12month":
                            if (returnBool('calc_ef_afterRun') == False) or (dateVar['currDate'] == dateVar['dateEnd']):
                                # either load already calculated discharge or at the end of the simulation
                                flag1 = False # create new netcdf file
                                for j in range(12):
                                    date1 = datetime.datetime(dateVar['dateEnd'].year, j+1, 1, 0, 0)
                                    outMap[map][i][2] = writenetcdf(netfile, varname,"", "undefined", getoutvar(self.var, checkname, index)[j], date1, j+1,
                                                                    flag1, True,12,netcdfindex=nindex)
                                    flag1 = True # now append to netcdf file

                        # if end of month is reached
                        if dateVar['checked'][dateVar['currwrite'] - 1]>0:
                            if map[-8:] == "monthtot":
                                outMap[map][i][2] = writenetcdf(netfile, varname,"_monthtot", "undefined", vars(self.var)[varname2 + "_monthtot"], dateVar['currDate'],
                                                                dateVar['currMonth'], flag, True, dateVar['diffMonth'],dateunit="months",netcdfindex=nindex)
                            if map[-8:] == "monthavg":
                                #days = calendar.monthrange(dateVar['currDate'].year, dateVar['currDate'].month)[1]
                                avgmap = vars(self.var)[varname2 + "_monthavg"] / daysMonthAvg
                                outMap[map][i][2] = writenetcdf(netfile, varname,"_monthavg", "undefined", avgmap,dateVar['currDate'], dateVar['currMonth'],
                                                                flag, True,dateVar['diffMonth'],dateunit="months",netcdfindex=nindex)

                        if map[-9:] == "annualend":
                            if dateVar['checked'][dateVar['currwrite'] - 1]==2:
                                outMap[map][i][2] = writenetcdf(netfile, varname,"_annualend", "undefined", getoutvar(self.var, checkname, index),  dateVar['currDate'], dateVar['currYear'],
                                                                flag,True,dateVar['diffYear'], dateunit="years", netcdfindex=nindex)
                        if map[-9:] == "annualtot":
                            vars(self.var)[varname2 + "_annualtot"] = vars(self.var)[varname2 + "_annualtot"] + getoutvar(self.var, checkname, index)
                        if map[-9:] == "annualavg":
                            vars(self.var)[varname2 + "_annualavg"] = vars(self.var)[varname2 + "_annualavg"] + getoutvar(self.var, checkname, index)

                        if dateVar['checked'][dateVar['currwrite'] - 1]==2:
                            if map[-9:] == "annualtot":
                                    outMap[map][i][2] = writenetcdf(netfile, varname,"_annualtot", "undefined", vars(self.var)[varname2 + "_annualtot"], dateVar['currDate'], dateVar['currYear'], flag, True,
                                                                    dateVar['diffYear'], dateunit="years", netcdfindex=nindex)
                            if map[-9:] == "annualavg":
                                        avgmap = vars(self.var)[varname2 + "_annualavg"] / daysYearAvg
                                        outMap[map][i][2] = writenetcdf(netfile, varname,"_annualavg", "undefined", avgmap, dateVar['currDate'], dateVar['currYear'], flag, True,
                                                                        dateVar['diffYear'],dateunit="years", netcdfindex=nindex)

                        if map[-8:] == "totaltot":
                            if dateVar['curr'] >= dateVar['intSpin']:
                                vars(self.var)[varname2 + "_totaltot"] = vars(self.var)[varname2 + "_totaltot"] + getoutvar(self.var, checkname, index)
                                if dateVar['currDate'] == dateVar['dateEnd']:
                                    # at the end of simulation write this map
                                    outMap[map][i][2] = writenetcdf(netfile, varname,"_totaltot", "undefined", vars(self.var)[varname2 + "_totaltot"],
                                                                dateVar['currDate'], dateVar['currwrite'], flag, False, netcdfindex=nindex)

                        if map[-8:] == "totalavg":
                            if dateVar['curr'] >= dateVar['intSpin']:
                                vars(self.var)[varname2 + "_totalavg"] = vars(self.var)[varname2 + "_totalavg"] + getoutvar(self.var, checkname, index) / float(dateVar['diffdays'])
                                if dateVar['currDate'] == dateVar['dateEnd']:
                                    # at the end of simulation write this map
                                    outMap[map][i][2] = writenetcdf(netfile, varname,"_totalavg", "undefined", vars(self.var)[varname2 + "_totalavg"],
                                                                    dateVar['currDate'], dateVar['currwrite'], flag, False, netcdfindex=nindex)

                        if map[-8:] == "totalend":
                            if dateVar['currDate'] == dateVar['dateEnd']:
                                # at the end of simulation write this map
                                vars(self.var)[varname2 + "_totalend"] = getoutvar(self.var, checkname, index)
                                outMap[map][i][2] = writenetcdf(netfile, varname,"_totalend","undefined", getoutvar(self.var, checkname, index),
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

                    # to use also variables with index from soil e.g. prefFlow[2]
                    # name and indices are checked once in initial (parseoutvar) - no eval of names from the settings file
                    checkname, index = self.outvarparsed[varname]
                    varname2 = varname.replace("[", "_").replace("]", "_")
                    checkifvariableexists(tss, checkname, list(vars(self.var).keys()))
                    varnameCollect.append(varname2)

                    if tss[-5:] == "daily":
                        if varname == "WaterCycle":
                            outTss[tss][i] = sample_watercycle(outTss[tss][i], 0)
                        else:
                            outTss[tss][i] = sample3(outTss[tss][i], getoutvar(self.var, checkname, index), 0)

                    if tss[-8:] == "monthend":
                        # reporting at the end of the month:
                        outTss[tss][i] = sample3(outTss[tss][i], getoutvar(self.var, checkname, index), 1)

                    if tss[-8:] == "monthtot":
                        # Calculate monthly watercycle variables
                        if varname == "WaterCycle":
                            outTss[tss][i] = sample_watercycle(outTss[tss][i], 1)
                        else:
                            # if  monthtot is not calculated it is done here
                            if (varname2 + "_monthtotTss") in vars(self.var):
                                #vars(self.var)[varname2 + "_monthtotTss"] = vars(self.var)[varname2 + "_monthtotTss"] + vars(self.var)[varname]
                                vars(self.var)[varname2 + "_monthtotTss"] = vars(self.var)[varname2 + "_monthtotTss"] + getoutvar(self.var, checkname, index)
                            else:
                                #vars(self.var)[varname2 + "_monthtotTss"] = vars(self.var)[varname]
                                vars(self.var)[varname2 + "_monthtotTss"] = 0 + getoutvar(self.var, checkname, index)
                            outTss[tss][i] = sample3(outTss[tss][i], vars(self.var)[varname2 + "_monthtotTss"], 1)

                    if tss[-8:] == "monthavg":
                        if (varname2 + "_monthavgTss") in vars(self.var):
                            vars(self.var)[varname2 + "_monthavgTss"] =  vars(self.var)[varname2 + "_monthavgTss"] + getoutvar(self.var, checkname, index)
                        else:
                            vars(self.var)[varname2 + "_monthavgTss"] = 0
                            vars(self.var)[varname2 + "_monthavgTss"] = vars(self.var)[varname2 + "_monthavgTss"] + getoutvar(self.var, checkname, index)
                        avgmap = vars(self.var)[varname2 + "_monthavgTss"] / daysMonthAvg
                        outTss[tss][i] = sample3(outTss[tss][i], avgmap, 1)

                    if tss[-9:] == "annualend":
                        # reporting at the end of the month:
                        outTss[tss][i] = sample3(outTss[tss][i], getoutvar(self.var, checkname, index), 2)

                    if tss[-9:] == "annualtot":

                        if (varname2 + "_annualtotTss") in vars(self.var):
                            vars(self.var)[varname2 + "_annualtotTss"] = vars(self.var)[varname2 + "_annualtotTss"] + getoutvar(self.var, checkname, index)
                        else:
                            vars(self.var)[varname2 + "_annualtotTss"] = 0 + getoutvar(self.var, checkname, index)
                        outTss[tss][i] = sample3(outTss[tss][i], vars(self.var)[varname2 + "_annualtotTss"], 2)

                    if tss[-9:] == "annualavg":
                        if (varname2 + "_annualavgTss") in vars(self.var):
                            vars(self.var)[varname2 + "_annualavgTss"] = vars(self.var)[varname2 + "_annualavgTss"] + getoutvar(self.var, checkname, index)
                        else:
                            vars(self.var)[varname2 + "_annualavgTss"] = 0 + getoutvar(self.var, checkname, index)
                        avgmap = vars(self.var)[varname2 + "_annualavgTss"] / daysYearAvg
                        #outTss[tss][i][0].sample2(decompress(avgmap), 2)
                        outTss[tss][i] = sample3(outTss[tss][i], avgmap, 2)

                    if tss[-8:] == "totaltot":
                        if dateVar['curr'] >= dateVar['intSpin']:
                            if (varname2 + "_totaltotTss") in vars(self.var):
                                vars(self.var)[varname2 + "_totaltotTss"] =  vars(self.var)[varname2 + "_totaltotTss"] + getoutvar(self.var, checkname, index)
                            else:
                                vars(self.var)[varname2 + "_totaltotTss"] = 0 + getoutvar(self.var, checkname, index)
                            if dateVar['currDate'] == dateVar['dateEnd']:
                                sample_maptotxt(outTss[tss][i], vars(self.var)[varname2 + "_totaltotTss"])

                    if tss[-8:] == "totalavg":
                        if dateVar['curr'] >= dateVar['intSpin']:
                            if (varname2 + "_totalavgTss") in vars(self.var):
                                vars(self.var)[varname2 + "_totalavgTss"] = vars(self.var)[varname2 + "_totalavgTss"] + getoutvar(self.var, checkname, index) / float(dateVar['diffdays'])
                            else:
                                vars(self.var)[varname2 + "_totalavgTss"] = getoutvar(self.var, checkname, index) / float(dateVar['diffdays'])
                            if dateVar['currDate'] == dateVar['dateEnd']:
                                sample_maptotxt(outTss[tss][i], vars(self.var)[varname2 + "_totalavgTss"])

        # if end of month is reached all monthly storage is set to 0
        # during spin-up currwrite is 0 -> checked[currwrite - 1] would be the last simulation day, so use 0 there
        # on the last spin-up day all storages are set to 0 -> the first written month/year has no spin-up days in it
        if dateVar['currwrite'] > 0:
            checkedToday = dateVar['checked'][dateVar['currwrite'] - 1]
        elif dateVar['curr'] == dateVar['intSpin'] - 1:
            checkedToday = 2
        else:
            checkedToday = 0
        for varname in varnameCollect:
            if checkedToday > 0:
                if (varname + "_monthtot") in vars(self.var):
                    vars(self.var)[varname + "_monthtot"] = 0
                if (varname + "_monthavg") in vars(self.var):
                    vars(self.var)[varname + "_monthavg"] = 0
                if (varname + "_monthtotTss") in vars(self.var):
                    vars(self.var)[varname + "_monthtotTss"] = 0
                if (varname + "_monthavgTss") in vars(self.var):
                    vars(self.var)[varname + "_monthavgTss"] = 0

            if checkedToday == 2:
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

