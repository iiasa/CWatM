# -------------------------------------------------------------------------
# Name:        Output
# Purpose:     Output as timeseries, netcdf,
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

from hydrological_modules.routing_reservoirs.routing_sub import *


from management_modules.checks import *
from management_modules.replace_pcr import *
from management_modules.data_handling import *
from messages import *
from netCDF4 import Dataset,num2date,date2num,date2index

from decimal import Decimal

class outputTssMap(object):

    """
    Output of time series and map
    """

    def __init__(self, out_variable):
        self.var = out_variable



    def initial(self):
        """
        Initial part of the output module
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


        def appendinfo(out,sec, name, type, ismap):
            """

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
                                #info.append(TimeoutputTimeseries2(name, self.var, outpoints, noHeader=False))
                                info.append(name)
                        else:
                            msg = "Checking output file path \n"
                            raise CWATMFileError(outDir[sec], msg)
                        info.append(var)
                        info.append(True)   # tss header
                        placeholder =[]
                        info.append(placeholder)
                        out[key][i] = info
                        i +=1


        # ------------------------------------------------------------------------------
        # if a geotif is used it can be a local map or a global
        try: localGauges = eval(binding['GaugesLocal'])
        except: localGauges = False

        where = "Gauges"
        outpoints = binding[where]

        coord = binding[where].split()  # could be gauges, sites, lakeSites etc.
        if len(coord) % 2 == 0:
            outpoints = valuecell(self.var.MaskMap, coord, outpoints)
        else:
            if os.path.exists(outpoints):
                #outpoints = loadmap(where, pcr=True)
                outpoints = loadmap(where, local = localGauges).astype(np.int64)
            else:
                msg = "Checking output points file path \n"
                raise CWATMFileError(outpoints, msg)

        # self.var.Tss[tss] = TimeoutputTimeseries(binding[tss], self.var, outpoints, noHeader=Flags['noheader'])
        outpoints[outpoints < 0] = 0
        self.var.sampleAdresses = getlocOutpoints(outpoints)  # for key in sorted(mydict):

        self.var.noOutpoints = len(self.var.sampleAdresses)
        #catch = subcatchment1(self.var.dirUp,outpoints,self.var.UpArea1)
        self.var.evalCatch =[]
        for key in sorted(self.var.sampleAdresses):
            outp = outpoints.copy()
            outp[outp <> key] = 0
            self.var.evalCatch.append(catchment1(self.var.dirUp, outp))

        ii =1



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
        """
        Dynamic part of the output module
        """

        def firstout(map):
            """
            returns the first cell as output value
            """
            first = sorted(list(self.var.sampleAdresses))[0]
            value = map[self.var.sampleAdresses[first]]
            return value



        def sample3(expression, map, daymonthyear):
            """
            :param expression:
            :param map:
            :param daymonthyear:
            :return:
            """

            #if dateVar['checked'][dateVar['currwrite'] - 1] >= daymonthyear:
            # using a list with is 1 for monthend and 2 for year end to check for execution
            value = []
            for key in sorted(self.var.sampleAdresses):
                v = map[self.var.sampleAdresses[key]]
                value.append(v)
            expression[3].append(value)

            if dateVar['laststep']:
                writeTssFile(expression, daymonthyear)

            return expression

        def sample4(expression, input, daymonthyear):
            """
            for mareatotal, for each gauge a separate value
            :param expression:
            :param map:
            :param daymonthyear:
            :return:
            TODO: change this to store in arrays not in maps
            """

            #if dateVar['checked'][dateVar['currwrite'] - 1] >= daymonthyear:
            # using a list with is 1 for monthend and 2 for year end to check for execution
            value = []
            ii = 0
            for key in sorted(self.var.sampleAdresses):
                map = eval(input + str(ii))
                v = map[self.var.sampleAdresses[key]]
                value.append(v)
                ii += 1
            expression[3].append(value)

            if dateVar['laststep']:
                writeTssFile(expression, daymonthyear)

            return expression



        def writeTssFile(expression, daymonthyear):
            """
            writing timeseries to disk
            """
            #
            outputFilename = expression[0]

            if expression[2]:
                writeFileHeader(outputFilename,expression)
                outputFile = open(outputFilename, "a")
            else:
                outputFile = open(outputFilename, "w")

            assert outputFile
            if len(expression[3]):
                numbervalues = len(expression[3][0])

                for timestep in xrange(dateVar['intSpin'], dateVar['intEnd'] + 1):
                    if dateVar['checked'][timestep - dateVar['intSpin']] >= daymonthyear:
                    #if dateVar['checked'][timestep - 1] >= daymonthyear:
                        row = ""
                        row += " %8g" % timestep
                        for i in xrange(numbervalues):
                            value = expression[3][timestep-1][i]
                            if isinstance(value, Decimal):
                                row += "           1e31"
                            else:
                                row += " %14g" % (value)
                        row += "\n"
                        outputFile.write(row)

            outputFile.close()

        def writeFileHeader(outputFilename,expression):
            """
            writes header part of tss file
            """

            outputFile = open(outputFilename, "w")
            # header
            # outputFile.write("timeseries " + self._spatialDatatype.lower() + "\n")
            outputFile.write("timeseries " + " settingsfile: " + os.path.realpath(sys.argv[1]) + " date: " + xtime.ctime(xtime.time()) + "\n")
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
        # self.report(self.Precipitation,binding['TaMaps'])




        # ************************************************************
        # ***** WRITING RESULTS: MAPS   ******************************
        # ************************************************************

        # print '----------------#'
        varname = None
        varnameCollect =[]
        if option['reportMap'] and dateVar['curr'] >= dateVar['intSpin']  :
            for map in outMap.keys():
                for i in xrange(outMap[map].__len__()):
                    if outMap[map][i] != "None":

                        netfile = outMap[map][i][0]
                        flag = outMap[map][i][2]
                        # flag to create netcdf or to write
                        varname = outMap[map][i][1]
                        varnameCollect.append(varname)
                        inputmap = 'self.var.' + varname

                        if map[-5:] == "daily":
                            # writenetcdf(netfile, varname, varunits, inputmap, timeStamp, posCnt, flag, flagTime=True):
                            outMap[map][i][2] = writenetcdf(netfile, varname, "undefined", eval(inputmap),  dateVar['currDate'],dateVar['currwrite'], flag, True, dateVar['diffdays'])


                        if map[-8:] == "monthend":
                            if dateVar['checked'][dateVar['currwrite'] - 1]>0:
                                outMap[map][i][2] = writenetcdf(netfile, varname+ "_monthend", "undefined", eval(inputmap),  dateVar['currDate'], dateVar['currMonth'], flag,True,dateVar['diffMonth'])
                        if (map[-8:] == "monthtot"):
                            # sum up daily value to monthly values
                            vars(self.var)[varname + "_monthtot"] += vars(self.var)[varname]
                        if (map[-8:] == "monthavg"):
                            vars(self.var)[varname + "_monthavg"] += vars(self.var)[varname]

                        # if end of month is reached
                        if dateVar['checked'][dateVar['currwrite'] - 1]>0:
                            if (map[-8:] == "monthtot"):
                                outMap[map][i][2] = writenetcdf(netfile, varname+"monthtot", "undefined", eval(inputmap+ "_monthtot"), dateVar['currDate'], dateVar['currMonth'], flag, True,dateVar['diffMonth'])
                                #vars(self.var)[varname + "monthtot"] = 0
                            if (map[-8:] == "monthavg"):
                                days = calendar.monthrange(int(dateVar['currDate'].strftime('%Y')), int(dateVar['currDate'].strftime('%m')))[1]
                                avgmap = vars(self.var)[varname + "_monthavg"] / days
                                outMap[map][i][2] = writenetcdf(netfile, varname+"monthavg", "undefined", avgmap,dateVar['currDate'], dateVar['currMonth'], flag, True,dateVar['diffMonth'])
                                #vars(self.var)[varname+"monthavg"] = 0



                        if map[-9:] == "annualend":
                                if dateVar['checked'][dateVar['currwrite'] - 1]==2:
                                    outMap[map][i][2] = writenetcdf(netfile, varname+"_annualend", "undefined", eval(inputmap),  dateVar['currDate'], dateVar['currYear'], flag,True,dateVar['diffYear'])
                        if (map[-9:] == "annualtot") or (map[-9:] == "annualavg"):
                                vars(self.var)[varname + "_annualtot"] += vars(self.var)[varname]
                                if dateVar['checked'][dateVar['currwrite'] - 1]==2:
                                    if (map[-9:] == "annualtot"):
                                        outMap[map][i][2] = writenetcdf(netfile, varname+"annualtot", "undefined", eval(inputmap+ "_annualtot"), dateVar['currDate'], dateVar['currYear'], flag, True, dateVar['diffYear'])
                                    if (map[-9:] == "annualavg"):
                                        avgmap = vars(self.var)[varname + "_monthtot"] / 365
                                        outMap[map][i][2] = writenetcdf(netfile, varname+"annualavg", "undefined", avgmap, dateVar['currDate'], dateVar['currYear'], flag, True, dateVar['diffYear'])
                                    #vars(self.var)[varname+"annualtot"] = 0



        # ************************************************************
        # ***** WRITING RESULTS: TIME SERIES *************************
        # ************************************************************

        if Flags['loud'] and option['reportTss']:
            # print the discharge of the first output map loc
            # print " %10.2f"  %cellvalue(maptotal(decompress(eval('self.var.' + reportTimeSerieAct["DisTS"]['outputVar'][0]))),1,1)[0]
            # print " %10.2f" % self.var.Tss["DisTS"].firstout(decompress(self.var.ChanQAvg))
            #print " %10.2f" % outTss['routing_out_tss_daily'][0][0].firstout(decompress(self.var.discharge))
            print " %10.2f" % firstout(self.var.discharge)

        if option['reportTss']:
            for tss in outTss.keys():
                for i in xrange(outTss[tss].__len__()):
                    # loop for each variable in a section
                    if outTss[tss][i] != "None":
                        varname = outTss[tss][i][1]
                        varnameCollect.append(varname)
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
                            #outTss[tss][i][0].sample2(decompress(eval(what)), 0 )
                            outTss[tss][i] = sample3(outTss[tss][i],eval(what),0)

                        if tss[-8:] == "monthend":
                            # reporting at the end of the month:
                            #outTss[tss][i][0].sample2(decompress(eval(what)),1)
                            outTss[tss][i] = sample3(outTss[tss][i], eval(what), 1)

                        if (tss[-8:] == "monthtot"):
                            # if  monthtot is not calculated it is done here
                            if (varname + "_monthtotTss") in vars(self.var):
                                vars(self.var)[varname + "_monthtotTss"] += vars(self.var)[varname]
                            else:
                                vars(self.var)[varname + "_monthtotTss"] = vars(self.var)[varname]
                            #outTss[tss][i][0].sample2(decompress(eval(what + "_monthtotTss")), 1)
                            outTss[tss][i] = sample3(outTss[tss][i], eval(what + "_monthtotTss"), 1)

                        if (tss[-8:] == "monthavg"):
                            if (varname + "_monthavgTss") in vars(self.var):
                                vars(self.var)[varname + "_monthavgTss"] += vars(self.var)[varname]
                            else:
                                vars(self.var)[varname + "_monthavgTss"] = 0
                                vars(self.var)[varname + "_monthavgTss"] += vars(self.var)[varname]
                            avgmap = vars(self.var)[varname + "_monthavgTss"] /  dateVar['daysInMonth']
                            #outTss[tss][i][0].sample2(decompress(avgmap), 1)
                            outTss[tss][i] = sample3(outTss[tss][i], avgmap, 1)




                        if tss[-9:] == "annualend":
                            # reporting at the end of the month:
                            #outTss[tss][i][0].sample2(decompress(eval(what)), 2)
                            outTss[tss][i] = sample3(outTss[tss][i], eval(what), 2)

                        if (tss[-9:] == "annualtot"):
                            # if  monthtot is not calculated it is done here
                            if (varname + "_annualtotTss0") in vars(self.var):
                                for ii in xrange(self.var.noOutpoints):
                                    vars(self.var)[varname + "_annualtotTss"+str(ii)] += vars(self.var)[varname][ii]
                            else:
                                for ii in xrange(self.var.noOutpoints):
                                    vars(self.var)[varname + "_annualtotTss"+str(ii)] = 0
                                    vars(self.var)[varname + "_annualtotTss"+str(ii)] += vars(self.var)[varname][ii]
                            #outTss[tss][i][0].sample2(decompress(eval(what + "_annualtotTss")), 2)
                            outTss[tss][i] = sample4(outTss[tss][i], eval(what + "_annualtotTss"), 2)

                        if (tss[-9:] == "annualavg"):
                            if (varname + "_annualavgTss") in vars(self.var):
                                vars(self.var)[varname + "_annualavgTss"] += vars(self.var)[varname]
                            else:
                                vars(self.var)[varname + "_annualavgTss"] = vars(self.var)[varname]
                            avgmap = vars(self.var)[varname + "_annualavgTss"] /dateVar['daysInYear']
                            #outTss[tss][i][0].sample2(decompress(avgmap), 2)
                            outTss[tss][i] = sample3(outTss[tss][i], avgmap, 2)




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
                for ii in xrange(self.var.noOutpoints):
                    if (varname + "_annualtotTss"+str(ii)) in vars(self.var):
                        vars(self.var)[varname + "_annualtotTss"+str(ii)] = 0
                if (varname + "_annualavgTss") in vars(self.var):
                    vars(self.var)[varname + "_annualavgTss"] = 0

