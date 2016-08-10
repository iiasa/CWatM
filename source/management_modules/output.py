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
            """
            Append info to PCraster TimeoutTimeseries (tss) class
            :param out:  map or tss, info of variable, output location
            :param sec:  Section of settingsfile
            :param name: variable name
            :param type: daily or monthly or avergae monthly etc.
            :param ismap: if map = True , if timeserie = False
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
                                vars(self.var)[var+"_"+type] = 0
                                # creates a var to sum/ average the results e.g. self.var.Precipitation_monthtot
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
                        i +=1


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





        # ------------------------------------------------------------------------------
        if option['reportTss']:
            # loop through all the section with output variables
            for sec in outsection:
                for type in outputTypTss:
                    appendinfo(outTss, sec, "_out_tss_",type, False)


        if option['reportMap']:
            # load netcdf metadata from precipitation
            metaNetCDF()

            # loop through all the section with output variables
            for sec in outsection:
                # daily output, monthly total monthly average,
                for type in outputTypMap:
                    # map or tss, section, type = daily, monthly ....
                    appendinfo(outMap,sec, "_out_map_",type, True)


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
        # ***** WRITING RESULTS: MAPS   ******************************
        # ************************************************************

        # print '----------------#'
        if option['reportMap']:
            for map in outMap.keys():
                for i in xrange(outMap[map].__len__()):
                    if outMap[map][i] != "None":

                        netfile = outMap[map][i][0]
                        flag = outMap[map][i][2]
                        # flag to create netcdf or to write
                        varname = outMap[map][i][1]
                        inputmap = 'self.var.' + varname

                        if map[-5:] == "daily":
                            # writenetcdf(netfile, varname, varunits, inputmap, timeStamp, posCnt, flag, flagTime=True):
                            outMap[map][i][2] = writenetcdf(netfile, varname, "undefined", eval(inputmap),  dateVar['currDate'],dateVar['curr'], flag, True, dateVar['diffdays'])


                        if map[-8:] == "monthend":
                                if dateVar['checked'][dateVar['curr'] - 1]>0:
                                    outMap[map][i][2] = writenetcdf(netfile, varname+ "_monthend", "undefined", eval(inputmap),  dateVar['currDate'], dateVar['currMonth'], flag,True,dateVar['diffMonth'])
                        if (map[-8:] == "monthtot") or (map[-8:] == "monthavg"):
                                vars(self.var)[varname + "_monthtot"] += vars(self.var)[varname]
                                if dateVar['checked'][dateVar['curr'] - 1]>0:
                                    if (map[-8:] == "monthtot"):
                                        outMap[map][i][2] = writenetcdf(netfile, varname+"monthtot", "undefined", eval(inputmap+ "_monthtot"), dateVar['currDate'], dateVar['currMonth'], flag, True,dateVar['diffMonth'])
                                    if (map[-8:] == "monthavg"):
                                        avgmap = vars(self.var)[varname + "_monthtot"] / 30
                                        outMap[map][i][2] = writenetcdf(netfile, varname+"monthavg", "undefined", avgmap,dateVar['currDate'], dateVar['currMonth'], flag, True,dateVar['diffMonth'])
                                    vars(self.var)[varname+"monthtot"] = 0


                        if map[-9:] == "annualend":
                                if dateVar['checked'][dateVar['curr'] - 1]==2:
                                    outMap[map][i][2] = writenetcdf(netfile, varname+"_annualend", "undefined", eval(inputmap),  dateVar['currDate'], dateVar['currYear'], flag,True,dateVar['diffYear'])
                        if (map[-9:] == "annualtot") or (map[-9:] == "annualavg"):
                                vars(self.var)[varname + "_annualtot"] += vars(self.var)[varname]
                                if dateVar['checked'][dateVar['curr'] - 1]==2:
                                    if (map[-9:] == "annualtot"):
                                        outMap[map][i][2] = writenetcdf(netfile, varname+"annualtot", "undefined", eval(inputmap+ "_annualtot"), dateVar['currDate'], dateVar['currYear'], flag, True, dateVar['diffYear'])
                                    if (map[-9:] == "annualavg"):
                                        avgmap = vars(self.var)[varname + "_monthtot"] / 365
                                        outMap[map][i][2] = writenetcdf(netfile, varname+"annualavg", "undefined", avgmap, dateVar['currDate'], dateVar['currYear'], flag, True, dateVar['diffYear'])
                                    vars(self.var)[varname+"annualtot"] = 0



        # ************************************************************
        # ***** WRITING RESULTS: TIME SERIES *************************
        # ************************************************************

        if Flags['loud'] and option['reportTss']:
            # print the discharge of the first output map loc
            # print " %10.2f"  %cellvalue(maptotal(decompress(eval('self.var.' + reportTimeSerieAct["DisTS"]['outputVar'][0]))),1,1)[0]
            # print " %10.2f" % self.var.Tss["DisTS"].firstout(decompress(self.var.ChanQAvg))
            print " %10.2f" % outTss['routing_out_tss_daily'][0][0].firstout(decompress(self.var.discharge))

        if option['reportTss']:
            for tss in outTss.keys():
                for i in xrange(outTss[tss].__len__()):
                    # loop for each variable in a section
                    if outTss[tss][i] != "None":
                        what = 'self.var.' + outTss[tss][i][1]
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
                            outTss[tss][i][0].sample2(decompress(eval(what)), 0 )

                        if tss[-8:] == "monthend":
                            # reporting at the end of the month:
                            outTss[tss][i][0].sample2(decompress(eval(what)),1)
                        if tss[-8:] == "monthtot":
                            # reporting at the end of the month:
                            outTss[tss][i][0].sample2(decompress(eval(what+ "_monthtot")), 1)



                        if tss[-9:] == "annualend":
                            # reporting at the end of the month:
                            outTss[tss][i][0].sample2(decompress(eval(what)), 2)







