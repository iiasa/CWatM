# -------------------------------------------------------------------------
# Name:        INFLOW HYDROGRAPHS module (OPTIONAL)
# Purpose:
#
# Author:      PB
#
# Created:     13/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------


import math
from cwatm.management_modules.data_handling import *

class inflow(object):

    """
    READ INFLOW HYDROGRAPHS (OPTIONAL)
    If option "inflow" is set to 1 the inflow hydrograph code is used otherwise dummy code is used


    **Global variables**

    =====================================  ======================================================================  =====
    Variable [self.var]                    Description                                                             Unit 
    =====================================  ======================================================================  =====
    sampleInflow                           location of inflow point                                                lat/l
    noinflowpoints                         number of inflow points                                                 --   
    inflowTs                               inflow time series data                                                 m3/s 
    totalQInM3                             total inflow over time (for mass balance calculation)                   m3   
    inflowM3                               inflow to basin                                                         m3   
    DtSec                                  number of seconds per timestep (default = 86400)                        s    
    QInM3Old                               Inflow from previous day                                                m3   
    =====================================  ======================================================================  =====

    **Functions**
    """

    def __init__(self, model):
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initial part of the inflow module
        Get the inflow points

        calls function :meth:`hydrological_modules.getlocOutpoints`
        calls function :meth:`hydrological_modules.join_struct_arrays2`

        """

        def getlocOutpoints(out):
            """
            Get location from Inflow (same as outflow) points

            :param out: get out
            :return: sampleAdresses - number and locs of the output
            """

            sampleAdresses = {}
            for i in range(maskinfo['mapC'][0]):
                if out[i]>0:
                    sampleAdresses[out[i]] = i
            return sampleAdresses

        def join_struct_arrays2(arrays):
            """
            Join arrays to a combined one

            :param arrays:
            :return: combined arry
            """
            """
            :param arrays: 
            :return: 
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
                            msg = "Error 217:" + line  + " in: " + filename + " is used already"
                            raise CWATMError(msg)

                        inflowNames.append(line)
                        names.append(line)
                    file.close()
                    skiplines = 3 + no
                except:
                    msg = "Error 218: Mistake reading inflow file\n"
                    raise CWATMFileError(os.path.join(inDir,name), sname=name)

                tempTssData = np.genfromtxt(filename, skip_header=skiplines, names=names, usecols=names[1:], filling_values=0.0)

                if flagFirstTss:
                    self.var.inflowTs = tempTssData.copy()
                    flagFirstTss = False
                    # copy temp data into the inflow data
                else:
                    self.var.inflowTs = join_struct_arrays2((self.var.inflowTs, tempTssData))
                    # join this dataset with the ones before

                ###import numpy.lib.recfunctions as rfn
                ###d = rfn.merge_arrays((a,b), flatten=True, usemask=False)


            self.var.QInM3Old = globals.inZero.copy()
            # Initialising cumulative output variables
            # These are all needed to compute the cumulative mass balance error
            self.var.totalQInM3 = globals.inZero.copy()



    def dynamic(self):
        """
        Dynamic part of the inflow module
        Use the inflow points to add inflow from time series file(s)
        """

        if checkOption('inflow'):

            # Get inflow hydrograph at each inflow point [m3/s]
            self.var.inflowM3 = globals.inZero.copy()
            for key in self.var.sampleInflow:
                loc = self.var.sampleInflow[key]
                index = dateVar['curr']-1
                self.var.inflowM3[loc] = self.var.inflowTs[str(key)][index] * self.var.DtSec
                # Convert to [m3] per time step
            self.var.totalQInM3 += self.var.inflowM3
            # Map of total inflow from inflow hydrographs [m3]


