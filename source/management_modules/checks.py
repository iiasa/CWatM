# -------------------------------------------------------------------------
# Name:        checks if inputs are valid
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



def counted(fn):
    def wrapper(*args, **kwargs):
        wrapper.called+= 1
        return fn(*args, **kwargs)
    wrapper.called= 0
    wrapper.__name__= fn.__name__
    return wrapper

@counted
def checkmap(name, value, map, flagmap, find):
    """ check maps if the fit to the mask map
    """
    s = [name, value]
    if flagmap:
        amap = scalar(defined(MMaskMap))
        try:
            smap = scalar(defined(map))
        except:
            msg = "Map: " + name + " in " + value + " does not fit"
            if name == "LZAvInflowMap":
                msg +="\nMaybe run initial run first"
            raise LisfloodError(msg)

        mvmap = maptotal(smap)
        mv = cellvalue(mvmap, 1, 1)[0]
        s.append(mv)

        less = maptotal(ifthenelse(defined(MMaskMap), amap - smap, scalar(0)))
        s.append(cellvalue(less, 1, 1)[0])
        less = mapminimum(scalar(map))
        s.append(cellvalue(less, 1, 1)[0])
        less = maptotal(scalar(map))
        if mv > 0:
            s.append(cellvalue(less, 1, 1)[0] / mv)
        else:
            s.append('0')
        less = mapmaximum(scalar(map))
        s.append(cellvalue(less, 1, 1)[0])
        if find > 0:
            if find == 2:
                s.append('last_Map_used')
            else:
                s.append('')

    else:
        s.append(0)
        s.append(0)
        s.append(float(map))
        s.append(float(map))
        s.append(float(map))

    if checkmap.called == 1:
        print "%-25s%-40s%11s%11s%11s%11s%11s" %("Name","File/Value","nonMV","MV","min","mean","max")
    print "%-25s%-40s%11i%11i%11.2f%11.2f%11.2f" %(s[0],s[1][-39:],s[2],s[3],s[4],s[5],s[6])
    return


def timemeasure(name,loops=0, update = False, sample = 1):
    timeMes.append(xtime.clock())
    if loops == 0:
        s = name
    else:
        s = name+"_%i" %(loops)
    timeMesString.append(s)
    return


def Calendar(input):
    """
    get the date from CalendarDayStart in the settings xml
    """
    try:
        date = float(input)
    except ValueError:
        d = input.replace('.', '/')
        d = d.replace('-', '/')
        year = d.split('/')[-1:]
        if len(year[0]) == 4:
            formatstr = "%d/%m/%Y"
        else:
            formatstr = "%d/%m/%y"
        if len(year[0]) == 1:
            d = d.replace('/', '.', 1)
            d = d.replace('/', '/0')
            d = d.replace('.', '/')
            print d
        date = datetime.datetime.strptime(d, formatstr)
        # value=str(int(date.strftime("%j")))
    return date

def datetoInt(dateIn,both=False):
    date1 = Calendar(dateIn)
    begin = Calendar(binding['CalendarDayStart'])

    if type(date1) is datetime.datetime:
         str1 = date1.strftime("%d/%m/%Y")
         int1 = (date1 - begin).days + 1
    else:
        int1 = int(date1)
        str1 = str(date1)
    if both: return int1,str1
    else: return int1

def checkifDate(start,end):

    begin = Calendar(binding['CalendarDayStart'])

    intStart,strStart = datetoInt(binding[start],True)
    intEnd,strEnd = datetoInt(binding[end],True)

    # test if start and end > begin
    if (intStart<0) or (intEnd<0) or ((intEnd-intStart)<0):
        strBegin = begin.strftime("%d/%m/%Y")
        msg="Start Date: "+strStart+" and/or end date: "+ strEnd + " are wrong!\n or smaller than the first time step date: "+strBegin
        raise LisfloodError(msg)
    modelSteps.append(intStart)
    modelSteps.append(intEnd)
    return

