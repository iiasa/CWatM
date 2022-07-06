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
from . import globals

import sys
import os
import string
import math
import difflib  # to check the closest word in settingsfile, if an error occurs

from cwatm.hydrological_modules.routing_reservoirs.routing_sub import *


from cwatm.management_modules.checks import *
from cwatm.management_modules.replace_pcr import *
from cwatm.management_modules.data_handling import *
from .messages import *
from netCDF4 import Dataset,num2date,date2num,date2index

from decimal import Decimal

class outputTssMap(object):

    """
    Output of time series and map


    **Global variables**

    =====================================  ======================================================================  =====
    Variable [self.var]                    Description                                                             Unit 
    =====================================  ======================================================================  =====
    dirUp                                  river network in upstream direction                                     --   
    cellArea                               Area of cell                                                            m2   
    sampleAdresses                                                                                                      
    noOutpoints                                                                                                         
    evalCatch                                                                                                           
    catcharea                                                                                                           
    firstout                                                                                                            
    discharge                              discharge                                                               m3/s 
    =====================================  ======================================================================  =====

    **Functions**
    """

    def __init__(self, model):
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initial part of the output module
        """

        def getlocOutpoints(out):
            """
            Get the location of output points

            :param out: get out
            :return: sampleAdresses - number and locs of the output
            """

            sampleAdresses = {}
            for i in range(maskinfo['mapC'][0]):
                if out[i]>0:
                    sampleAdresses[out[i]] = i
            return sampleAdresses


        def appendinfo(out,sec, name, type, ismap):
            """
            Append all information on outputpoints and maps - what output, where, when

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
                                #vars(self.var)[var+"_"+type] = 0
                                # creates a var to sum/ average the results e.g. self.var.Precipitation_monthtot
                            else:
                                # TimeoutputTimeseries(binding[tss], self.var, outpoints, noHeader=Flags['noheader'])
                                #info.append(os.path.join(outDir[sec], str(var) + "_daily.tss"))
                                name = os.path.join(outDir[sec], str(var) + "_"+ type + ".tss")
                                #info.append(TimeoutputTimeseries2(name, self.var, outpoints, noHeader=False))
                                info.append(name)
                        else:
                            msg = "Error 220: Checking output file path \n"
                            raise CWATMFileError(outDir[sec], msg)
                        info.append(var)
                        if ismap: info.append(False)  # flag set False for initial writing if it is a map
                        else: info.append(not(Flags['noheader']))  # flag set True for writing time series header

                        placeholder =[]
                        info.append(placeholder)
                        if ismap: info.append(type)  # set type to create variable later on first timestep
                        out[key][i] = info
                        i +=1


        # ------------------------------------------------------------------------------
        # if a geotif is used it can be a local map or a global
        localGauges = returnBool('GaugesLocal')
        where = "Gauges"
        outpoints = cbinding(where)

        #globals.inZero = np.zeros(maskinfo['mapC'])

        coord = cbinding(where).split()  # could be gauges, sites, lakeSites etc.
        if len(coord) % 2 == 0:
            compress_arange = np.arange(maskinfo['mapC'][0])
            arange = decompress(compress_arange).astype(int)

            #outpoints = valuecell( coord, outpoints)
            col,row = valuecell(coord, outpoints, returnmap = False)
            self.var.sampleAdresses = {}
            for i in range(len(col)):
                self.var.sampleAdresses[i+1] = arange[row[i],col[i]]

        else:
            if os.path.exists(outpoints):
                outpoints = loadmap(where, local = localGauges).astype(np.int64)
            else:
                if len(coord) == 1:
                    msg = "Error 221: Checking output-points file\n"
                else:
                    msg = "Error 129: Coordinates are not pairs\n"
                raise CWATMFileError(outpoints, msg, sname="Gauges")

            # self.var.Tss[tss] = TimeoutputTimeseries(cbinding(tss), self.var, outpoints, noHeader=Flags['noheader'])
            outpoints[outpoints < 0] = 0
            self.var.sampleAdresses = getlocOutpoints(outpoints)  # for key in sorted(mydict):

        self.var.noOutpoints = len(self.var.sampleAdresses)
        #catch = subcatchment1(self.var.dirUp,outpoints,self.var.UpArea1)

        # check if catchment area calculation is necessary
        calcCatch = False
        for s in filter(lambda x: "areaavg" in x, outTss.keys()): calcCatch = True
        for s in filter(lambda x: "areasum" in x, outTss.keys()): calcCatch = True

        if calcCatch:
           self.var.evalCatch ={}
           self.var.catcharea = {}


           for key in sorted(self.var.sampleAdresses):
              outp  = globals.inZero.copy()
              outp[self.var.sampleAdresses[key]] = key



              self.var.evalCatch[key] = catchment1(self.var.dirUp, outp)
              self.var.catcharea[key] =np.bincount(self.var.evalCatch[key], weights=self.var.cellArea)[key]

        # ------------------------------------------------------------------------------
        if checkOption('reportTss'):
            # loop through all the section with output variables
            for sec in outsection:
                for type2 in outputTypTss2:
                    for type in outputTypTss:
                        if type2 == "tss":
                            type = type
                        else:
                            type = type2 + "_" + type
                        appendinfo(outTss, sec, "_out_tss_",type, False)


        if checkOption('reportMap'):
            # load netcdf metadata from precipitation
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




    def dynamic(self, ef = False):
        """
        Dynamic part of the output module
        Output of maps and timeseries

        :param ef: done with environmental flow
        """

        def firstout(map):
            """
            returns the first cell as output value

            :param map: 1D array of data
            :return: value of the first output point
            """

            first = sorted(list(self.var.sampleAdresses))[0]
            value = map[self.var.sampleAdresses[first]]
            return value

        def checkifvariableexists(name, vari, space):
            """
            Test if variable exists

            :param name: variable name
            :param vari: variable to check if it exists in the variable space
            :param space: variable space of self.var
            """
            if not (vari in space):
                closest = difflib.get_close_matches(vari, space)
                if not closest: closest = ["- no match -"]
                msg = "Error 132: Variable \"" + vari + "\" is not defined in \""+ name+"\"\n"
                msg += "Closest variable to this name is: \"" + closest[0] + "\""
                raise CWATMError(msg)



        def sample3(expression, map, daymonthyear):
            """
            Collects outputpoint value to write it into a time series file
            calls function :meth:`management_modules.writeTssFile`

            :param expression: array of outputpoint information
            :param map: 1D array of data
            :param daymonthyear: day =0 , month =1 , year =2
            :return: expression
            """

            #if dateVar['checked'][dateVar['currwrite'] - 1] >= daymonthyear:
            # using a list with is 1 for monthend and 2 for year end to check for execution
            value = []
            #tss.split('_')[-2]

            # if inputmap is not an array give out error message
            if not (hasattr(map, '__len__')):
                msg = "No values in: " + expression[1] + "\nCould not write: " + expression[0]
                print(CWATMWarning(msg))
                return expression

            for key in sorted(self.var.sampleAdresses):
                if expression[0].split('_')[-2] in ['areaavg','areasum']:
                    # value from catchment
                    v = np.bincount(self.var.evalCatch[key], weights = map * self.var.cellArea)[key]

                    if expression[0].split('_')[-2] == 'areaavg':
                        if self.var.catcharea[key] == 0:
                            v = 0.
                        else:
                            v = v / self.var.catcharea[key]
                else: # from single cell
                   v = map[self.var.sampleAdresses[key]]
                value.append(v)
            expression[3].append(value)

            if dateVar['laststep']:
                writeTssFile(expression, daymonthyear)

            return expression


        def writeTssFile(expression, daymonthyear):
            """
            writing timeseries
            calls function :meth:`management_modules.writeFileHeader`

            :param expression:  array of outputpoint information
            :param daymonthyear: day =0 , month =1 , year =2
            :return: -
            """

            outputFilename = expression[0]

            if expression[2]:
                writeFileHeader(outputFilename,expression)
                outputFile = open(outputFilename, "a")
            else:
                outputFile = open(outputFilename, "w")

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

        def writeFileHeader(outputFilename,expression):
            """
            writes header part of tss file

            :param outputfilename: name of the outputfile
            :param expression:  array of outputpoint information
            :return: -
            """

            outputFile = open(outputFilename, "w")
            # header
            # outputFile.write("timeseries " + self._spatialDatatype.lower() + "\n")
            header = "timeseries " + " settingsfile: " + os.path.realpath(settingsfile[0]) + " date: " + xtime.ctime(xtime.time())
            header += " CWATM: " + versioning['exe']  + ", " +versioning['lastdate'] + "\n"
            if 'save_git' in option:
                if checkOption("save_git"):
                    import git
                    header += "git commit " + git.Repo(search_parent_directories=True).head.object.hexsha
           
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
            Write map information to textfile

            :param expression:
            :param map:
            :return:
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
        varnameCollect =[]
        if checkOption('reportMap') and dateVar['curr'] >= dateVar['intSpin'] or ef:
            for map in list(outMap.keys()):
                for i in range(outMap[map].__len__()):
                    if outMap[map][i] != "None":

                        netfile = outMap[map][i][0]
                        flag = outMap[map][i][2]
                        # flag to create netcdf or to write
                        varname = outMap[map][i][1]
                        type = outMap[map][i][4]

                        # to use also variables with index from soil e.g. actualET[2]
                        if '[' in varname:
                            checkname = varname[0:varname.index("[")]
                        else:
                            checkname = varname
                        checkifvariableexists(map,checkname, list(vars(self.var).keys()))

                        varnameCollect.append(varname)
                        inputmap = 'self.var.' + varname

                        # create variable after it is checked on the first timestep
                        # creates a var to sum/ average the results e.g. self.var.Precipitation_monthtot
                        if dateVar['curr'] == dateVar['intSpin']:
                            vars(self.var)[varname+"_"+type] = 0

                        if map[-5:] == "daily":
                            outMap[map][i][2] = writenetcdf(netfile, varname,"", "undefined", eval(inputmap),  dateVar['currDate'],dateVar['currwrite'], flag, True, dateVar['diffdays'])
                        if map[-8:] == "monthend":
                            if dateVar['checked'][dateVar['currwrite'] - 1]>0:
                                outMap[map][i][2] = writenetcdf(netfile, varname, "_monthend", "undefined", eval(inputmap),  dateVar['currDate'], dateVar['currMonth'], flag,True,dateVar['diffMonth'])
                        if map[-8:] == "monthtot":
                            # sum up daily value to monthly values
                            vars(self.var)[varname + "_monthtot"] = vars(self.var)[varname + "_monthtot"] + vars(self.var)[varname]
                        if map[-8:] == "monthavg":
                            vars(self.var)[varname + "_monthavg"] = vars(self.var)[varname + "_monthavg"] + vars(self.var)[varname]

                        if map[-4:] == "once":
                            if (returnBool('calc_ef_afterRun') == False) or (dateVar['currDate'] == dateVar['dateEnd']):
                                # either load already calculated discharge or at the end of the simulation
                                outMap[map][i][2] = writenetcdf(netfile, varname,"", "undefined", eval(inputmap),
                                                            dateVar['currDate'], dateVar['currwrite'], flag, False)
                        if map[-7:] == "12month":
                            if (returnBool('calc_ef_afterRun') == False) or (dateVar['currDate'] == dateVar['dateEnd']):
                                # either load already calculated discharge or at the end of the simulation
                                flag1 = False # create new netcdf file
                                for j in range(12):
                                    in1 = inputmap  + '[' +str(j) + ']'
                                    date1 = datetime.datetime(dateVar['dateEnd'].year, j+1, 1, 0, 0)
                                    outMap[map][i][2] = writenetcdf(netfile, varname,"", "undefined", eval(in1), date1, j+1, flag1, True,12)
                                    flag1 = True # now append to netcdf file


                        # if end of month is reached
                        if dateVar['checked'][dateVar['currwrite'] - 1]>0:
                            #if (map[-8:] == "monthend"):
                            #    outMap[map][i][2] = writenetcdf(netfile, varname,"_monthend", "undefined", eval(inputmap+ "_monthend"), #dateVar['currDate'], dateVar['currMonth'], flag, True,
                            #                                    dateVar['diffMonth'],dateunit="months")
                            if map[-8:] == "monthtot":
                                outMap[map][i][2] = writenetcdf(netfile, varname,"_monthtot", "undefined", eval(inputmap+ "_monthtot"), dateVar['currDate'], dateVar['currMonth'], flag, True,
                                                                dateVar['diffMonth'],dateunit="months")
                                #vars(self.var)[varname + "monthtot"] = 0
                            if map[-8:] == "monthavg":
                                #days = calendar.monthrange(dateVar['currDate'].year, dateVar['currDate'].month)[1]
                                avgmap = vars(self.var)[varname + "_monthavg"] / dateVar['daysInMonth']
                                outMap[map][i][2] = writenetcdf(netfile, varname,"_monthavg", "undefined", avgmap,dateVar['currDate'], dateVar['currMonth'], flag, True,dateVar['diffMonth'],dateunit="months")
                                #vars(self.var)[varname+"monthavg"] = 0



                        if map[-9:] == "annualend":
                            if dateVar['checked'][dateVar['currwrite'] - 1]==2:
                                outMap[map][i][2] = writenetcdf(netfile, varname,"_annualend", "undefined", eval(inputmap),  dateVar['currDate'], dateVar['currYear'], flag,True,dateVar['diffYear'],
                                                                dateunit="years")
                        if map[-9:] == "annualtot":
                            vars(self.var)[varname + "_annualtot"] = vars(self.var)[varname + "_annualtot"] + vars(self.var)[varname]
                        if map[-9:] == "annualavg":
                            vars(self.var)[varname + "_annualavg"] = vars(self.var)[varname + "_annualavg"] + vars(self.var)[varname]

                        if dateVar['checked'][dateVar['currwrite'] - 1]==2:
                            if map[-9:] == "annualtot":
                                    outMap[map][i][2] = writenetcdf(netfile, varname,"_annualtot", "undefined", eval(inputmap+ "_annualtot"), dateVar['currDate'], dateVar['currYear'], flag, True,
                                                                    dateVar['diffYear'], dateunit="years")
                            if map[-9:] == "annualavg":
                                        days = 366 if calendar.isleap(dateVar['currDate'].year) else 365
                                        avgmap = vars(self.var)[varname + "_annualavg"] / days
                                        outMap[map][i][2] = writenetcdf(netfile, varname,"_annualavg", "undefined", avgmap, dateVar['currDate'], dateVar['currYear'], flag, True,
                                                                        dateVar['diffYear'],dateunit="years")
                                    #vars(self.var)[varname+"annualtot"] = 0


                        if map[-8:] == "totaltot":
                            if dateVar['curr'] >= dateVar['intSpin']:
                                vars(self.var)[varname + "_totaltot"] = vars(self.var)[varname + "_totaltot"] + vars(self.var)[varname]
                                if dateVar['currDate'] == dateVar['dateEnd']:
                                    # at the end of simulation write this map
                                    outMap[map][i][2] = writenetcdf(netfile, varname,"_totaltot", "undefined", eval(inputmap +  "_totaltot"),
                                                                dateVar['currDate'], dateVar['currwrite'], flag, False)

                        if map[-8:] == "totalavg":
                            if dateVar['curr'] >= dateVar['intSpin']:
                                vars(self.var)[varname + "_totalavg"] = vars(self.var)[varname + "_totalavg"] + vars(self.var)[varname]/ float(dateVar['diffdays'])
                                if dateVar['currDate'] == dateVar['dateEnd']:
                                    # at the end of simulation write this map
                                    outMap[map][i][2] = writenetcdf(netfile, varname,"_totalavg", "undefined",
                                                                    eval(inputmap + "_totalavg"),
                                                                    dateVar['currDate'], dateVar['currwrite'],
                                                                    flag, False)

                        if map[-8:] == "totalend":
                            if dateVar['currDate'] == dateVar['dateEnd']:
                                # at the end of simulation write this map
                                vars(self.var)[varname + "_totalend"] = vars(self.var)[varname]
                                outMap[map][i][2] = writenetcdf(netfile, varname,"_totalend","undefined", vars(self.var)[varname],
                                                                dateVar['currDate'],
                                                                dateVar['currwrite'],
                                                                flag, False)


                                # ************************************************************
        # ***** WRITING RESULTS: TIME SERIES *************************
        # ************************************************************
        self.var.firstout = firstout(self.var.discharge)

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

        #if Flags['loud'] and checkOption('reportTss'):
            #print(" %10.2f" % self.var.firstout)

        if checkOption('reportTss'):
            for tss in list(outTss.keys()):
                for i in range(outTss[tss].__len__()):
                    # loop for each variable in a section
                    if outTss[tss][i] != "None":
                        varname = outTss[tss][i][1]
                        varnameCollect.append(varname)
                        what = 'self.var.' + outTss[tss][i][1]

                        # to use also variables with index from soil e.g. actualET[2]
                        if '[' in varname:
                            checkname = varname[0:varname.index("[")]
                        else:
                            checkname = varname
                        checkifvariableexists(tss, checkname, list(vars(self.var).keys()))

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
                            outTss[tss][i] = sample3(outTss[tss][i], eval(what), 1)

                        if tss[-8:] == "monthtot":
                            # if  monthtot is not calculated it is done here
                            if (varname + "_monthtotTss") in vars(self.var):
                                vars(self.var)[varname + "_monthtotTss"] = vars(self.var)[varname + "_monthtotTss"] + vars(self.var)[varname]
                            else:
                                vars(self.var)[varname + "_monthtotTss"] = vars(self.var)[varname]
                            outTss[tss][i] = sample3(outTss[tss][i], eval(what + "_monthtotTss"), 1)

                        if tss[-8:] == "monthavg":
                            if (varname + "_monthavgTss") in vars(self.var):
                                vars(self.var)[varname + "_monthavgTss"] =  vars(self.var)[varname + "_monthavgTss"] + vars(self.var)[varname]
                            else:
                                vars(self.var)[varname + "_monthavgTss"] = 0
                                vars(self.var)[varname + "_monthavgTss"] = vars(self.var)[varname + "_monthavgTss"] + vars(self.var)[varname]
                            avgmap = vars(self.var)[varname + "_monthavgTss"] /  dateVar['daysInMonth']
                            outTss[tss][i] = sample3(outTss[tss][i], avgmap, 1)




                        if tss[-9:] == "annualend":
                            # reporting at the end of the month:
                            #outTss[tss][i][0].sample2(decompress(eval(what)), 2)
                            outTss[tss][i] = sample3(outTss[tss][i], eval(what), 2)

                        if tss[-9:] == "annualtot":

                            if (varname + "_annualtotTss") in vars(self.var):
                                vars(self.var)[varname + "_annualtotTss"] = vars(self.var)[varname + "_annualtotTss"] + vars(self.var)[varname]
                            else:
                                vars(self.var)[varname + "_annualtotTss"] = vars(self.var)[varname]
                            outTss[tss][i] = sample3(outTss[tss][i], eval(what + "_annualtotTss"), 2)

                        if tss[-9:] == "annualavg":
                            if (varname + "_annualavgTss") in vars(self.var):
                                vars(self.var)[varname + "_annualavgTss"] = vars(self.var)[varname + "_annualavgTss"] + vars(self.var)[varname]
                            else:
                                vars(self.var)[varname + "_annualavgTss"] = vars(self.var)[varname]
                            avgmap = vars(self.var)[varname + "_annualavgTss"] /dateVar['daysInYear']
                            #outTss[tss][i][0].sample2(decompress(avgmap), 2)
                            outTss[tss][i] = sample3(outTss[tss][i], avgmap, 2)

                        if tss[-8:] == "totaltot":
                            if dateVar['curr'] >= dateVar['intSpin']:
                                if (varname + "_totaltotTss") in vars(self.var):
                                    vars(self.var)[varname + "_totaltotTss"] =  vars(self.var)[varname + "_totaltotTss"] + vars(self.var)[varname]
                                else:
                                    vars(self.var)[varname + "_totaltotTss"] = vars(self.var)[varname]
                                if dateVar['currDate'] == dateVar['dateEnd']:
                                    #outTss[tss][i] = sample_maptotxt(outTss[tss][i],  eval(what + "_totaltotTss"))
                                    sample_maptotxt(outTss[tss][i], eval(what + "_totaltotTss"))

                        if tss[-8:] == "totalavg":
                            if dateVar['curr'] >= dateVar['intSpin']:
                                if (varname + "_totalavgTss") in vars(self.var):
                                    vars(self.var)[varname + "_totalavgTss"] = vars(self.var)[varname + "_totalavgTss"] + vars(self.var)[varname] / float(dateVar['diffdays'])
                                else:
                                    vars(self.var)[varname + "_totalavgTss"] = vars(self.var)[varname] / float(dateVar['diffdays'])
                                if dateVar['currDate'] == dateVar['dateEnd']:
                                    #outTss[tss][i] = sample_maptotxt(outTss[tss][i], eval(what + "_totalavgTss"))
                                    sample_maptotxt(outTss[tss][i], eval(what + "_totalavgTss"))

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
                for ii in range(self.var.noOutpoints):
                    if (varname + "_annualtotTss"+str(ii)) in vars(self.var):
                        vars(self.var)[varname + "_annualtotTss"+str(ii)] = 0
                if (varname + "_annualavgTss") in vars(self.var):
                    vars(self.var)[varname + "_annualavgTss"] = 0

