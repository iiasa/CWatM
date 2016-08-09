# -------------------------------------------------------------------------
# Name:        Handling of timesteps and dates
# Purpose:
#
# Author:      P. Burek
#
# Created:     09/08/2016
# Copyright:   (c) burekpe 2016
# -------------------------------------------------------------------------


import os
import calendar
import datetime
import time as xtime
import numpy as np
from management_modules.globals import *
from management_modules.messages import *





def timemeasure(name,loops=0, update = False, sample = 1):
    timeMes.append(xtime.clock())
    if loops == 0:
        s = name
    else:
        s = name+"_%i" %(loops)
    timeMesString.append(s)
    return

# -----------------------------------------------------------------------
# Calendar routines
# -----------------------------------------------------------------------

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

    if type(date1) is datetime.datetime:
         str1 = date1.strftime("%d/%m/%Y")
         int1 = 1
    else:
        int1 = int(date1)
        str1 = str(date1)
    if both: return int1,str1
    else: return int1




def checkifDate(start,end):

    begin = Calendar(binding['CalendarDayStart'])
    startdate = Calendar(binding['StepStart'])
    if type(startdate) is datetime.datetime:
        begin = startdate
    else:
        begin = begin + datetime.timedelta(days=startdate-1)

    dateVar['intStart'],strStart = datetoInt(binding[start],True)
    dateVar['intEnd'],strEnd = datetoInt(binding[end],True)

    # test if start and end > begin
    if (dateVar['intStart']<0) or (dateVar['intEnd']<0) or ((dateVar['intEnd']-dateVar['intStart'])<0):
        strBegin = begin.strftime("%d/%m/%Y")
        msg="Start Date: "+strStart+" and/or end date: "+ strEnd + " are wrong!\n or smaller than the first time step date: "+strBegin
        raise CWATMError(msg)

    dateVar['dateStart'] = begin
    dateVar['diffdays'] = dateVar['intEnd'] - dateVar['intStart'] + 1
    dateVar['dateEnd'] = begin + datetime.timedelta(days=dateVar['diffdays']-1)
    dateVar['curr'] = 0

    dateVar['datelastmonth'] = datetime.datetime(year=dateVar['dateEnd'].year, month= dateVar['dateEnd'].month, day=1) - datetime.timedelta(days=1)
    dateVar['datelastyear'] = datetime.datetime(year=dateVar['dateEnd'].year, month= 1, day=1) - datetime.timedelta(days=1)

    dateVar['checkend'] = []
    dates = np.arange(dateVar['dateStart'], dateVar['dateEnd'], datetime.timedelta(days = 1)).astype(datetime.datetime)
    for d in dates:
        if d.day == calendar.monthrange(d.year, d.month)[1]:
            if d.month == 12:
                dateVar['checkend'].append(2)
            else:
                dateVar['checkend'].append(1)
        else:
            dateVar['checkend'].append(0)






    return













def datecheck( date, step):
    print date
    yearend = False
    if date.day == calendar.monthrange(date.year, date.month)[1]:
        monthend = True
        if date.month == 12:
            yearend = True
    else:
        monthend = False
    doy = date.strftime('%j')

    laststep = False
    if step == dateVar['intEnd']:
      laststep=True

    datelastmonth = datetime.datetime(year=dateVar['dateEnd'].year, month= dateVar['dateEnd'].month, day=1) - datetime.timedelta(days=1)
    datelastyear = datetime.datetime(year=dateVar['dateEnd'].year, month= 1, day=1) - datetime.timedelta(days=1)

    laststepmonthend = False
    laststepyearend = False
    if date == datelastmonth:
        laststepmonthend = True
    if date == datelastyear:
        laststepyearend = True

    #start = self._userModel.firstTimeStep()
    #end = self._userModel.nrTimeSteps()

    dateVar['doy'] = date.strftime('%j')


    return monthend, yearend, laststepmonthend, laststepyearend, laststep





