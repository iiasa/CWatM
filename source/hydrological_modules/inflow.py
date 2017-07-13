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
from management_modules.data_handling import *

class inflow(object):

    """
    READ INFLOW HYDROGRAPHS (OPTIONAL)
    If option "inflow" is set to 1 the inflow hydrograph code is used otherwise dummy code is used

    Warning:
        Not included at moment

    Todo:
        has to be revamped
        The  pcraster routine timeinputscalar has to be replaced by reading txt -> numpy
    """

    def __init__(self, inflow_variable):
        self.var = inflow_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
    def initial(self):
        """
        Initial part of the inflow module
        """

        def getlocOutpoints(out):
            """
            :param out: get out
            :return: sampleAdresses - number and locs of the output
            """

            sampleAdresses = {}
            for i in xrange(maskinfo['mapC'][0]):
                if out[i]>0:
                    sampleAdresses[out[i]] = i
            return sampleAdresses

        def join_struct_arrays2(arrays):
            newdtype = sum((a.dtype.descr for a in arrays), [])
            newrecarray = np.empty(len(arrays[0]), dtype=newdtype)
            for a in arrays:
                for name in a.dtype.names:
                    newrecarray[name] = a[name]
            return newrecarray



        if checkOption('inflow'):

            localGauges = returnBool('GaugesLocal')
            inflowPoints = loadmap('InflowPoints', local=localGauges).astype(np.int64)
            inflowPoints[inflowPoints < 0] = 0
            self.var.sampleInflow = getlocOutpoints(inflowPoints)  # for key in sorted(mydict):

            self.var.noinflowpoints = len(self.var.sampleInflow)

            inDir = cbinding('In_Dir')
            inflowFile = cbinding('QInTS').split()

            inflowNames =[]
            for name in inflowFile:
                names =['timestep']
                try:

                    filename = os.path.join(inDir,name)
                    file = open(filename, "r")

                    # read data header
                    line = file.readline()
                    no = int(file.readline()) - 1
                    line = file.readline()
                    for i in xrange(no):
                        line = file.readline().strip('\n')
                        if line in inflowNames:
                            msg = line  + " in: " + filename + " is used already"
                            raise CWATMError(msg)

                        inflowNames.append(line)
                        names.append(line)
                    file.close()
                    skiplines = 3 + no
                except:
                    raise CWATMFileError(filename, sname=name)

                self.var.inflowTs = np.genfromtxt(filename, skip_header=skiplines, names=names, usecols = names[1:], filling_values=0.0)
                b = np.genfromtxt(filename, skip_header=skiplines, names=['x', '3', '4'], usecols='3', filling_values=0.0)
                a = self.var.inflowTs
                ii =1
                #import numpy.lib.recfunctions as rfn
                #d = rfn.merge_arrays((a,b), flatten=True, usemask=False)

                e = join_struct_arrays2((a,b))



                ii = 1




            self.var.totalQInM3 = globals.inZero.copy()

            # calculation of inflow map per timestep - current timestep in dateVar['curr']
            self.var.inflowM3 = globals.inZero.copy()

            for key in self.var.sampleInflow:
                loc = self.var.sampleInflow[key]
                self.var.inflowM3[loc] = self.var.inflowTs[str(key)][dateVar['curr']] * self.var.DtSec
            self.var.totalQInM3 += self.var.inflowM3
            ii = 1





            #self.var.QInM3Old = np.where(self.var.InflowPoints>0,self.var.ChanQ * self.var.DtSec,0)
            # Initialising cumulative output variables
            # These are all needed to compute the cumulative mass balance error

#        self.var.QInDt = globals.inZero.copy()
        # inflow substep amount

    def dynamic_init(self):
        """
        Dynamic part of the inflow module
        Init inflow before sub step routing
        """

        # ************************************************************
        # ***** INLETS INIT
        # ************************************************************
        if checkOption('inflow'):
            self.var.QDelta = (self.var.QInM3 - self.var.QInM3Old) * self.var.InvNoRoutSteps
            # difference between old and new inlet flow  per sub step
            # in order to calculate the amount of inlet flow in the routing loop

    def dynamic(self):
        """
        Dynamic part of the inflow module
        """

        if checkOption('inflow'):
            QIn = timeinputscalar(cbinding('QInTS'), loadmap('InflowPoints',pcr=True))
            # Get inflow hydrograph at each inflow point [m3/s]
            QIn = compressArray(QIn)
            QIn[np.isnan(QIn)]=0
            self.var.QInM3 = QIn * self.var.DtSec
            # Convert to [m3] per time step
            self.var.TotalQInM3 += self.var.QInM3
            # Map of total inflow from inflow hydrographs [m3]


    def dynamic_inloop(self,NoRoutingExecuted):
        """

        :param NoRoutingExecuted: actual number of routing substep
        :return: self.var.QInDt - inflow in m3 per sub timestep
        """

        # ************************************************************
        # ***** INLFLOW **********************************************
        # ************************************************************
        if checkOption('inflow'):
            self.var.QInDt = (self.var.QInM3Old + (NoRoutingExecuted + 1) * self.var.QDelta) * self.var.InvNoRoutSteps
            # flow from inlets per sub step
