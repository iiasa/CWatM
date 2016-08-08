# -------------------------------------------------------------------------
# Name:        Output
# Purpose:     Output as timeseries, netcdf, pcraster
#
# Author:      PB
#
# Created:     5/08/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

import numpy as np
import globals

import sys
import os
import string
import math




from management_modules.improvepcraster import *
from management_modules.checks import *
from management_modules.replace_pcr import *
from management_modules.data_handling import *

from messages import *

from pcraster import *
from pcraster.framework import *
from netCDF4 import Dataset,num2date,date2num,date2index



class outputTssMap(object):

    """
    # ************************************************************
    # ***** Output of time series (.tss) and maps*****************
    # ************************************************************
    """

    def __init__(self, out_variable):
        self.var = out_variable



    def initial(self):
        """ initial part of the output module
        """
        def appendinfo(out,sec, name, type, ismap):
            key = sec.lower() + name + type
            if key in out:
                if out[key][0] != "None":
                    i = 0
                    for var in out[key]:
                        info = []
                        if os.path.exists(outDir[sec]):
                            if ismap:
                                info.append(os.path.join(outDir[sec], str(var) + "_" + type + ".nc"))
                            else:
                                # TimeoutputTimeseries(binding[tss], self.var, outpoints, noHeader=Flags['noheader'])
                                #info.append(os.path.join(outDir[sec], str(var) + "_daily.tss"))
                                name = os.path.join(outDir[sec], str(var) + "_"+ type + ".tss")
                                info.append(TimeoutputTimeseries2(name, self.var, outpoints, noHeader=False))
                        else:
                            msg = "Checking output file path \n"
                            raise CWATMFileError(outDir[sec], msg)
                        info.append(var)
                        info.append(False)
                        out[key][i] = info
                        i += 1

        # ------------------------------------------------------------------------------
        where = "Gauges"
        outpoints = binding[where]

        coord = binding[where].split()  # could be gauges, sites, lakeSites etc.
        if len(coord) % 2 == 0:
            outpoints = valuecell(self.var.MaskMap, coord, outpoints)
        else:
            if os.path.exists(outpoints):
                outpoints = loadmap(where, pcr=True)
            else:
                msg = "Checking output points file path \n"
                raise CWATMFileError(outpoints, msg)

        # self.var.Tss[tss] = TimeoutputTimeseries(binding[tss], self.var, outpoints, noHeader=Flags['noheader'])

        self.var.everyday = []
        self.var.everymonth=[]
        self.var.everyyear=[]



        # ------------------------------------------------------------------------------

        if option['reportMap']:
            # loop through all the section with output variables
            for sec in outsection:
                # daily output, monthly total monthly average,
                for type in outputTypMap:
                    # map or tss, section, type = daily, monthly ....
                    appendinfo(outMap,sec, "_out_map_",type, True)

        if option['reportTss']:
            # loop through all the section with output variables
            for sec in outsection:
                for type in outputTypTss:
                    appendinfo(outTss, sec, "_out_tss_",type, False)
        i = 1






    def dynamic(self):
        """ dynamic part of the output module
        """

        # ************************************************************
        # ***** WRITING RESULTS: TIME SERIES *************************
        # ************************************************************

        # xxx=catchmenttotal(self.var.SurfaceRunForest * self.var.PixelArea, self.var.Ldd) * self.var.InvUpArea
        # self.var.Tss['DisTS'].sample(xxx)
        # self.report(self.Precipitation,binding['TaMaps'])

        # ************************************************************
        # ***** WRITING RESULTS: TIME SERIES *************************
        # ************************************************************
        monthend, yearend, laststepmonthend, laststepyearend, doy = datecheck(self.var.CalendarDate,self.var.TimeSinceStart)
        self.var.everymonth.append(monthend)
        self.var.everyyear.append(yearend)
        self.var.everyday.append(True)


        if option['loud']:
            # print the discharge of the first output map loc
            # print " %10.2f"  %cellvalue(maptotal(decompress(eval('self.var.' + reportTimeSerieAct["DisTS"]['outputVar'][0]))),1,1)[0]
            #print " %10.2f" % self.var.Tss["DisTS"].firstout(decompress(self.var.ChanQAvg))
            print " %10.2f" % outTss['routing_out_tss_daily'][0][0].firstout(decompress(self.var.discharge))

        for tss in outTss.keys():
            for i in xrange(outTss[tss].__len__()):
            # loop for each variable in a section
                if outTss[tss][i] != "None":
                    what = 'self.var.' + outTss[tss][i][1]
                    if tss[-5:] == "daily":
                        #what = 'self.var.' + reportTimeSerieAct[tss]['outputVar'][0]
                        #how = reportTimeSerieAct[outTss[tss][0][0]]['operation'][0]
                        #if how == 'mapmaximum':
                        #changed = compressArray(mapmaximum(decompress(eval(what))))
                        #what = 'changed'
                        #if how == 'total':
                        #changed = compressArray(catchmenttotal(decompress(eval(what)) * self.var.PixelAreaPcr,self.var.Ldd) * self.var.InvUpArea)
                        #what = 'changed'
                        #print i, outTss[tss][i][1], what
                        outTss[tss][i][0].sample2(decompress(eval(what)), self.var.everyday )

                    if tss[-8:] == "monthend":
                        # reporting at the end of the month:
                        outTss[tss][i][0].sample2( decompress(eval(what)), self.var.everymonth, laststepmonthend)
                    if tss[-9:] == "annualend":
                        # reporting at the end of the month:
                        outTss[tss][i][0].sample2( decompress(eval(what)), self.var.everyyear, laststepyearend)









            i = 1





