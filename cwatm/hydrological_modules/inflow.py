# -------------------------------------------------------------------------
# Name:        INFLOW HYDROGRAPHS module (OPTIONAL)
# Purpose: External inflow hydrographs module for adding prescribed water inputs.
# Manages point source water additions and boundary condition flows.
# Supports observed streamflow integration and water system augmentation.
#
# Author:      PB
#
# Created:     13/07/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------


from cwatm.management_modules.data_handling import *

class inflow(object):
    """
    Inflow hydrographs module for adding external water inputs.
    
    Processes inflow hydrograph time series data from external files and applies
    them at specified spatial locations within the model domain. This module is
    optional and only activates when the 'inflow' option is enabled.
    

    Attributes
    ----------
    var : object
        Reference to model variables object containing state variables
    model : object
        Reference to the main CWatM model instance

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    sampleInflow                         Dictionary    cell of each inflow point (number of the point: cell)                   --   
    inflowTs                             Dictionary    inflow time series data per day of the run, for each point              m3 s-
    inflowM3                             Array         inflow to basin                                                         m3   
    DtSec                                Array         number of seconds per timestep (default = 86400)                        s    
    QInM3Old                             Array         Inflow from previous day                                                m3   
    load_initial                         Flag          Settings initLoad holds initial conditions for variables                bool 
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize inflow module.
        
        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initialize inflow points and load time series data.
        
        Reads inflow point locations from a map or coordinates, loads the time
        series from one or more csv files (or tss files in the old format if there is no csv file) and checks them
        before the first day.
        
        Notes
        -----
        This method performs several key operations:
        - Identifies spatial locations for inflow application
        - Reads and validates time series data from the csv (or tss) files
        - Stores the flow of each point per day of the run
        """

        def getlocOutpoints(out):
            """
            Extract spatial locations of inflow points from input array.
            
            Processes an array of inflow point identifiers and creates a dictionary
            mapping point IDs to their corresponding linear array indices.
            
            Parameters
            ----------
            out : numpy.ndarray
                Array containing inflow point identifiers (positive integers)
                
            Returns
            -------
            dict
                Dictionary mapping inflow point IDs to linear array indices
            """

            # a point number in two cells: the dictionary would keep only the last cell
            numbers, counts = np.unique(out[out > 0], return_counts=True)
            if np.any(counts > 1):
                number = numbers[counts > 1][0]
                msg = "Error 163: Inflow point: " + str(number) + " is in more than one cell of: " + cbinding('InflowPoints') + "\n"
                cellsOfMask = np.flatnonzero(~maskinfo['maskflat'])
                for i in np.flatnonzero(out == number):
                    row, col = np.unravel_index(cellsOfMask[i], maskinfo['shape'])
                    x = maskmapAttr['x'] + (col + 0.5) * maskmapAttr['cell']
                    y = maskmapAttr['y'] - (row + 0.5) * maskmapAttr['cell']
                    msg += "x = " + str(round(float(x), 5)) + "  y = " + str(round(float(y), 5)) + "\n"
                msg += "Each cell needs its own point number"
                raise CWATMError(msg)

            sampleAdresses = {}
            for i in range(maskinfo['mapC'][0]):
                if out[i] > 0:
                    sampleAdresses[out[i]] = i
            return sampleAdresses

        if checkOption('inflow'):

            # the inflow is put into the channels by the routing: without routing it would not be used
            if not checkOption('includeRouting'):
                msg = "Error 164: inflow = True needs includeRouting = True, without routing the inflow is not used"
                raise CWATMError(msg)

            where = "InflowPoints"
            inflowPointsMap = cbinding(where)
            coord = cbinding(where).split()  # could be gauges, sites, lakeSites etc.
            try:
                [float(xy) for xy in coord]
                isNumbers = len(coord) > 0
            except ValueError:
                isNumbers = False

            inflowPointsAll = None
            # a file first: the path of a map can have blanks
            if os.path.exists(inflowPointsMap):
                # not compressed first: to see the points of the map which are outside the mask
                inflowPointsAll = loadmap(where, compress=False, local=returnBool('InLocal'), masked=True)
                inflowPoints = compressArray(inflowPointsAll, name=inflowPointsMap).astype(np.int64)
            elif isNumbers and len(coord) % 2 == 0:
                inflowPoints = valuecell(coord, inflowPointsMap)
            else:
                if isNumbers:
                    msg = "Error 127: Coordinates are not pairs\n"
                else:
                    msg = "Error 216: Inflow points are neither coordinates nor a file\n"
                raise CWATMFileError(inflowPointsMap, msg, sname=where)

            inflowPoints[inflowPoints < 0] = 0
            self.var.sampleInflow = getlocOutpoints(inflowPoints)  # for key in sorted(mydict):

            # every point of the settings has to be inside the mask. Points of a map: the map can hold more points
            # than this mask (e.g. a map for several catchments), so at least one has to be inside
            if inflowPointsAll is None:
                lost = [i for i in range(len(coord) // 2) if i + 1 not in self.var.sampleInflow]
                if lost:
                    msg = "Error 158: Inflow points outside the mask map, or in the same cell as another point:\n"
                    for i in lost:
                        msg += "x = " + coord[i * 2] + "  y = " + coord[i * 2 + 1] + "\n"
                    msg += "Please have a look at \"InflowPoints\" and \"MaskMap\""
                    raise CWATMError(msg)
            else:
                pointsAll = np.unique(np.ma.compressed(inflowPointsAll).astype(np.int64))
                lost = [str(i) for i in pointsAll if i > 0 and i not in self.var.sampleInflow]
                if not self.var.sampleInflow:
                    msg = "Error 158: No inflow point of the map: " + inflowPointsMap + " is inside the mask map\n"
                    msg += "Please have a look at \"InflowPoints\" and \"MaskMap\""
                    raise CWATMError(msg)
                if lost:
                    msg = "Inflow points of the map: " + inflowPointsMap + " outside the mask map are not used: "
                    print(CWATMWarning(msg + " ".join(lost)))

            inDir = cbinding('In_Dir')
            inflowFile = cbinding('QInTS').split()

            # days of this run: the inflow of each point is stored per day of the run
            noDays = dateVar['intEnd'] - dateVar['intStart'] + 1
            runDates = [(d.day, d.month, d.year) for d in dateVar['dates'][:noDays]]

            self.var.inflowTs = {}
            inflowFiles = {}   # file of each column, for the error messages
            inflowNames = []
            firstFile = None
            for name in inflowFile:
                # csv file, or the old tss format if only a tss file exists
                names, dates, values, filename = readInflowFile(os.path.join(inDir, name))

                for column in names:
                    if column in inflowNames:
                        msg = "Error 217: " + column + " in: " + filename + " is used already"
                        raise CWATMError(msg)
                    inflowNames.append(column)
                    inflowFiles[column] = filename

                # all files need the same number of rows
                if firstFile is None:
                    firstFile = (filename, len(values))
                elif len(values) != firstFile[1]:
                    msg = "Error 162: Inflow files have a different number of rows:\n"
                    msg += firstFile[0] + ": " + str(firstFile[1]) + "\n" + filename + ": " + str(len(values))
                    raise CWATMError(msg)

                # a tss file has no dates: the first row is the first day of the run (StepStart)
                if dates is None:
                    dates = runDates[:len(values)]

                # the flow of a day is found by its date
                rowOfDate = {date: i for i, date in enumerate(dates)}
                missing = [date for date in runDates if date not in rowOfDate]
                if missing:
                    msg = "Error 161: Inflow file: " + filename + " has no value for " + str(len(missing))
                    msg += " of the " + str(noDays) + " days of this run, first: %02d/%02d/%d\n" % missing[0]
                    msg += "It needs daily values from StepStart to StepEnd"
                    raise CWATMError(msg)
                rows = [rowOfDate[date] for date in runDates]
                for i, column in enumerate(names):
                    self.var.inflowTs[column] = values[rows, i]

            # all points need a column in the files, with values which can go into the routing
            for key in self.var.sampleInflow:
                column = str(key)
                if column not in self.var.inflowTs:
                    msg = "Error 160: Inflow point: " + column + " has no column in the inflow files: " + " ".join(inflowFile)
                    msg += "\nColumns in the files: " + " ".join(inflowNames)
                    raise CWATMError(msg)
                series = self.var.inflowTs[column]
                wrong = np.flatnonzero(~np.isfinite(series) | (series < 0.) | (series >= 1e30))
                if wrong.size > 0:
                    msg = "Error 159: Inflow file: " + inflowFiles[column] + " point: " + column + " has " + str(wrong.size)
                    msg += " missing or negative value(s) in this run\nFirst: " + str(series[wrong[0]])
                    msg += " on %02d/%02d/%d" % runDates[wrong[0]]
                    raise CWATMError(msg)

            # inflow of the previous day (routing_kinematic.py interpolates between it and today's inflow) - from the
            # init file for a restart, else None: the inflow of the first day (inflow.dynamic)
            self.var.QInM3Old = self.var.load_initial('QInM3Old', default=None, warn=False)

    def dynamic(self):
        """
        Apply inflow hydrographs at specified locations for current time step.
        
        Retrieves inflow values from time series data for the current time step,
        and applies them at the corresponding spatial locations.
        
        Notes
        -----
        Inflow values are:
        - Read from pre-loaded time series data
        - Converted from m3/s to m3 per time step
        - Applied at specified inflow point locations
        """

        if checkOption('inflow'):

            # Get inflow hydrograph at each inflow point [m3 per time step]
            self.var.inflowM3 = globals.inZero.copy()
            for key in self.var.sampleInflow:
                loc = self.var.sampleInflow[key]
                index = dateVar['curr'] - 1
                self.var.inflowM3[loc] = self.var.inflowTs[str(key)][index] * self.var.DtSec
            # first day without an init file: the inflow of the day as the previous inflow (before 2026-10-13: 0, the
            # routing got only (N+1)/2N of the first day's inflow, N = NoRoutingSteps: Tisa 52 %)
            if self.var.QInM3Old is None:
                self.var.QInM3Old = self.var.inflowM3.copy()


