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


import math
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
    sampleInflow                         Number        location of inflow point                                                lat/l
    noinflowpoints                       Array         number of inflow points                                                 --   
    inflowTs                             Array         inflow time series data                                                 m3/s 
    totalQInM3                           Array         total inflow over time (for mass balance calculation)                   m3   
    inflowM3                             Array         inflow to basin                                                         m3   
    DtSec                                Array         number of seconds per timestep (default = 86400)                        s    
    QInM3Old                             Array         Inflow from previous day                                                m3   
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
        
        Reads inflow point locations from configuration files or coordinates,
        loads time series data from multiple files, and prepares data structures
        for dynamic inflow application during model execution.
        
        Notes
        -----
        This method performs several key operations:
        - Identifies spatial locations for inflow application
        - Reads and validates time series data from multiple files
        - Merges time series data from different sources
        - Initializes cumulative inflow tracking variables
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

            sampleAdresses = {}
            for i in range(maskinfo['mapC'][0]):
                if out[i] > 0:
                    sampleAdresses[out[i]] = i
            return sampleAdresses

        def join_struct_arrays2(arrays):
            """
            Merge multiple structured numpy arrays into a single array.
            
            Combines structured arrays with potentially different field names
            into a unified structured array containing all fields from input arrays.
            
            Parameters
            ----------
            arrays : list of numpy.ndarray
                List of structured numpy arrays to be merged
                
            Returns
            -------
            numpy.ndarray
                Combined structured array containing all fields from input arrays
            """

            newdtype = sum((a.dtype.descr for a in arrays), [])
            newrecarray = np.empty(len(arrays[0]), dtype=newdtype)
            for a in arrays:
                for name in a.dtype.names:
                    newrecarray[name] = a[name]
            return newrecarray



        if checkOption('inflow'):

            localGauges = returnBool('InLocal')

            where = "InflowPoints"
            inflowPointsMap = cbinding(where)
            coord = cbinding(where).split()  # could be gauges, sites, lakeSites etc.
            if len(coord) % 2 == 0:
                inflowPoints = valuecell(coord, inflowPointsMap)
            else:
                if os.path.exists(inflowPointsMap):
                    inflowPoints = loadmap(where, local=localGauges).astype(np.int64)
                else:
                    if len(coord) == 1:
                        msg = "Error 216: Checking output-points file\n"
                    else:
                        msg = "Error 127: Coordinates are not pairs\n"
                    raise CWATMFileError(inflowPointsMap, msg, sname="Gauges")


            inflowPoints[inflowPoints < 0] = 0
            self.var.sampleInflow = getlocOutpoints(inflowPoints)  # for key in sorted(mydict):
            self.var.noinflowpoints = len(self.var.sampleInflow)

            inDir = cbinding('In_Dir')
            inflowFile = cbinding('QInTS').split()

            inflowNames =[]
            flagFirstTss = True
            for name in inflowFile:
                names =['timestep']
                try:

                    filename = os.path.join(inDir,name)
                    file = open(filename, "r")

                    # read data header
                    line = file.readline()
                    no = int(file.readline()) - 1
                    line = file.readline()
                    for i in range(no):
                        line = file.readline().strip('\n')
                        if line in inflowNames:
                            msg = "Error 217:" + line + " in: " + filename + " is used already"
                            raise CWATMError(msg)

                        inflowNames.append(line)
                        names.append(line)
                    file.close()
                    skiplines = 3 + no
                except:
                    msg = "Error 218: Mistake reading inflow file\n"
                    raise CWATMFileError(os.path.join(inDir, name), sname=name)

                tempTssData = np.genfromtxt(filename, skip_header=skiplines, names=names, 
                                            usecols=names[1:], filling_values=0.0)

                if flagFirstTss:
                    self.var.inflowTs = tempTssData.copy()
                    flagFirstTss = False
                    # copy temp data into the inflow data
                else:
                    self.var.inflowTs = join_struct_arrays2((self.var.inflowTs, tempTssData))
                    # join this dataset with the ones before

                # import numpy.lib.recfunctions as rfn
                # d = rfn.merge_arrays((a,b), flatten=True, usemask=False)


            self.var.QInM3Old = globals.inZero.copy()
            # Initialising cumulative output variables
            # These are all needed to compute the cumulative mass balance error
            self.var.totalQInM3 = globals.inZero.copy()



    def dynamic(self):
        """
        Apply inflow hydrographs at specified locations for current time step.
        
        Retrieves inflow values from time series data for the current time step,
        applies them at the corresponding spatial locations, and updates cumulative
        inflow tracking variables.
        
        Notes
        -----
        Inflow values are:
        - Read from pre-loaded time series data
        - Converted from mÂ³/s to mÂ³ per time step
        - Applied at specified inflow point locations
        - Accumulated for mass balance tracking
        """

        if checkOption('inflow'):

            # Get inflow hydrograph at each inflow point [m3/s]
            self.var.inflowM3 = globals.inZero.copy()
            for key in self.var.sampleInflow:
                loc = self.var.sampleInflow[key]
                index = dateVar['curr'] - 1
                self.var.inflowM3[loc] = self.var.inflowTs[str(key)][index] * self.var.DtSec
                # Convert to [m3] per time step
            self.var.totalQInM3 += self.var.inflowM3
            # Map of total inflow from inflow hydrographs [m3]


