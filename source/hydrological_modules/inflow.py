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



        if checkOption('inflow'):
            self.var.InflowPoints = loadmap('InflowPoints')
            self.var.QInM3Old = np.where(self.var.InflowPoints>0,self.var.ChanQ * self.var.DtSec,0)
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
