# -------------------------------------------------------------------------
# Name:        improve/correct some pcraster routines
# Purpose:
#
# Author:      burekpe
#
# Created:     16/05/2016
# Copyright:   (c) burekpe 2016
# -------------------------------------------------------------------------


import xml.dom.minidom
import datetime
import time as xtime
import os

from pcraster import*
from pcraster.framework import *

from globals import *
from management_modules.timestep import *


class DynamicFramework(DynamicFramework):
    """
    Framework class for dynamic models.
    `userModel`
    Instance that models the :ref:`Dynamic Model Concept <dynamicModelConcept>`.
    `lastTimeStep`   Last timestep to run.
    `firstTimestep`  Sets the starting timestep of the model (optional, default is 1).
    Updated by improvepcraster.py
    """

    def run(self):
        """
        Run the dynamic user model.

        .. todo::
        This method depends on the filter frameworks concept. Shouldn't its run
        method call _runSuspend()?
        """
        self._atStartOfScript()
        if(hasattr(self._userModel(), "resume")):
            #if self._userModel().firstTimeStep() == 1:
            # replaced this because starting date is not always the 1
            if self._userModel().firstTimeStep() == datetoInt(binding['StepStart']):
               self._runInitial()
            else:
               self._runResume()
        else:
            self._runInitial()

        self._runDynamic()

        # Only execute this section while running filter frameworks.
        if hasattr(self._userModel(), "suspend") and \
        hasattr(self._userModel(), "filterPeriod"):
          self._runSuspend()

        return 0




    """Adjusting the def _atStartOfTimeStep defined in DynamicFramework
       for a real quiet output
    """
    rquiet = False
    rtrace = False

    def _atStartOfTimeStep(self, step):
        self._userModel()._setInTimeStep(True)
        if not self.rquiet:
            if not self.rtrace:
                msg = u"#"

            else:
                msg = u"%s<time step=\"%s\">\n" % (self._indentLevel(), step)
            sys.stdout.write(msg)
            sys.stdout.flush()


class TimeoutputTimeseries2(TimeoutputTimeseries):
    """
    Class to create pcrcalc timeoutput style timeseries
    Updated py improvepcraster.py
    """



    def _writeFileHeader(self, outputFilename):
        """
        writes header part of tss file
        """
        outputFile = open(outputFilename, "w")
        # header
        #outputFile.write("timeseries " + self._spatialDatatype.lower() + "\n")
        outputFile.write("timeseries " + " settingsfile: "+os.path.realpath(sys.argv[1])+" date: " + xtime.ctime(xtime.time())+ "\n")
        sys.argv[1]
        outputFile.write(str(self._maxId + 1) + "\n")
        outputFile.write("timestep\n")
        for colId in range(1, self._maxId + 1):
            outputFile.write(str(colId) + "\n")
        outputFile.close()

    def _configureOutputFilename(self, filename):
        """
        generates filename
        appends timeseries file extension if necessary
        prepends sample directory if used in stochastic
        """

        # test if suffix or path is given
        head, tail = os.path.split(filename)

        if not re.search("\.tss", tail):
            # content,sep,comment = filename.partition("-")
            # filename = content + "Tss" + sep + comment + ".tss"
            filename = tail + ".tss"

        # for stochastic add sample directory
        if hasattr(self._userModel, "nrSamples"):
            try:
                filename = os.path.join(str(self._userModel.currentSampleNumber()), filename)
            except:
                pass

        return filename

    def sample2(self, expression, daymonthyear):
        """
        Sampling the current values of 'expression' at the given locations for the current timestep
        """
        if dateVar['checked'][dateVar['curr']-1] >= daymonthyear:
          # using a list with is 1 for monthend and 2 for year end to check for execution
          arrayRowPos = self._userModel.currentTimeStep() - self._userModel.firstTimeStep()

        # if isinstance(expression, float):
        #  expression = pcraster.scalar(expression)

          try:
            # store the data type for tss file header
            if self._spatialDatatype == None:
                self._spatialDatatype = str(expression.dataType())
          except AttributeError, e:
            datatype, sep, tail = str(e).partition(" ")
            msg = "Argument must be a PCRaster map, type %s given. If necessary use data conversion functions like scalar()" % (
            datatype)
            raise AttributeError(msg)

          if self._spatialIdGiven:
            #if expression.dataType() == pcraster.Scalar or expression.dataType() == pcraster.Directional:
            #    tmp = pcraster.areaaverage(pcraster.spatial(expression), pcraster.spatial(self._spatialId))
            #else:
            #    tmp = pcraster.areamajority(pcraster.spatial(expression), pcraster.spatial(self._spatialId))

            col = 0
            for cellIndex in self._sampleAddresses:
                #value, valid = pcraster.cellvalue(tmp, cellIndex)
                value, valid = pcraster.cellvalue(pcraster.spatial(expression), cellIndex)
                if not valid:
                    value = Decimal("NaN")

                self._sampleValues[arrayRowPos][col] = value
                col += 1
          else:
            #if expression.dataType() == pcraster.Scalar or expression.dataType() == pcraster.Directional:
            #    tmp = pcraster.maptotal(pcraster.spatial(expression)) \
            #          / pcraster.maptotal(pcraster.scalar(pcraster.defined(pcraster.spatial(expression))))
            #else:
            #    tmp = pcraster.mapmaximum(pcraster.maptotal(pcraster.areamajority(pcraster.spatial(expression), \
            #                    pcraster.spatial( pcraster.nominal(1)))))

            value, valid = pcraster.cellvalue(pcraster.spatial(expression), 1)
            if not valid:
                value = Decimal("NaN")

            self._sampleValues[arrayRowPos] = value

        if dateVar['laststep']:
            self._writeTssFile(daymonthyear)

    def _writeTssFile(self,daymonthyear):
        """
        writing timeseries to disk
        """
        #
        outputFilename =  self._configureOutputFilename(self._outputFilename)

        if self._writeHeader == True:
             self._writeFileHeader(outputFilename)
             outputFile = open(outputFilename, "a")
        else:
             outputFile = open(outputFilename, "w")

        assert outputFile


        for timestep in range(dateVar['intStart'], dateVar['intEnd']+1):
          if dateVar['checked'][timestep-dateVar['intStart']] >= daymonthyear:
            row = ""
            row += " %8g" % timestep
            if self._spatialIdGiven:
                for cellId in range(0, self._maxId):
                    value = self._sampleValues[timestep - dateVar['intStart']][cellId]
                    if isinstance(value, Decimal):
                        row += "           1e31"
                    else:
                        row += " %14g" % (value)
                row += "\n"
            else:
                value = self._sampleValues[timestep - dateVar['intStart']]
                if isinstance(value, Decimal):
                    row += "           1e31"
                else:
                    row += " %14g" % (value)
                row += "\n"

            outputFile.write(row)

        outputFile.close()

    def __init__(self, tssFilename, model, idMap=None, noHeader=False):
        """

        """

        if not isinstance(tssFilename, str):
            raise Exception(
                "timeseries output filename must be of type string")

        self._outputFilename = tssFilename
        self._maxId = 1
        self._spatialId = None
        self._spatialDatatype = None
        self._spatialIdGiven = False
        self._userModel = model
        self._writeHeader = not noHeader
        # array to store the timestep values
        self._sampleValues = None

        _idMap = False
        if isinstance(idMap, str) or isinstance(idMap, pcraster._pcraster.Field):
            _idMap = True

        #nrRows = 10000 - self._userModel.firstTimeStep() + 1
        #nrRows = self._userModel.nrTimeSteps() - self._userModel.firstTimeStep() + 1

        # if header reserve rows from 1 to endstep
        # if noheader only from startstep - endstep
        #if noHeader:
        #    nrRows = int(binding['StepEnd']) - int(binding['StepStart']) - self._userModel.firstTimeStep() + 2
        #else: nrRows = int(binding['StepEnd']) - int(binding['StepStart']) - self._userModel.firstTimeStep() + 2
        if noHeader:
            nrRows = datetoInt(binding['StepEnd'],dateVar['dateStart']) - datetoInt(binding['StepStart'],dateVar['dateStart']) - self._userModel.firstTimeStep() + 2
        else: nrRows = datetoInt(binding['StepEnd'],dateVar['dateStart']) - datetoInt(binding['StepStart'],dateVar['dateStart']) - self._userModel.firstTimeStep() + 2



        if _idMap:
            self._spatialId = idMap
            if isinstance(idMap, str):
                self._spatialId = pcraster.readmap(idMap)

            _allowdDataTypes = [
                pcraster.Nominal, pcraster.Ordinal, pcraster.Boolean]
            if self._spatialId.dataType() not in _allowdDataTypes:
                #raise Exception(

                #    "idMap must be of type Nominal, Ordinal or Boolean")
                # changed into creating a nominal map instead of bailing out
                self._spatialId = pcraster.nominal(self._spatialId)

            if self._spatialId.isSpatial():
                self._maxId, valid = pcraster.cellvalue(
                    pcraster.mapmaximum(pcraster.ordinal(self._spatialId)), 1)
            else:
                self._maxId = 1

            # cell indices of the sample locations

            # #self._sampleAddresses = []
            # for cellId in range(1, self._maxId + 1):
            # self._sampleAddresses.append(self._getIndex(cellId))

            self._sampleAddresses = [1 for i in xrange(self._maxId)]
            # init with the left/top cell - could also be 0 but then you have to catch it in
            # the sample routine and put an exeption in
            nrCells = pcraster.clone().nrRows() * pcraster.clone().nrCols()
            for cell in xrange(1, nrCells + 1):
                if (pcraster.cellvalue(self._spatialId, cell)[1]):
                    self._sampleAddresses[
                        pcraster.cellvalue(self._spatialId, cell)[0] - 1] = cell

            self._spatialIdGiven = True

            nrCols = self._maxId
            self._sampleValues = [
                [Decimal("NaN")] * nrCols for _ in [0] * nrRows]
        else:
            self._sampleValues = [[Decimal("NaN")] * 1 for _ in [0] * nrRows]

    def firstout(self,expression):
        """
        returns the first cell as output value
        """
        try:
            cellIndex = self._sampleAddresses[0]
            tmp = pcraster.areaaverage(pcraster.spatial(expression), pcraster.spatial(self._spatialId))
            value, valid = pcraster.cellvalue(tmp, cellIndex)
            if not valid:
               value = Decimal("NaN")
        except:
            value = Decimal("NaN")
        return value