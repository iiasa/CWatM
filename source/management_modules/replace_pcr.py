# -------------------------------------------------------------------------
# Name:        replace_pcr
# Purpose:     Replace pcraster command with numpy array commands
#
# Author:      PB
#
# Created:     2/08/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

import numpy as np


# -----------------------------------------
def getValDivZero2(x,y,y_lim,z_def= 0.0):
  #-returns the result of a division that possibly involves a zero
  # denominator; in which case, a default value is substituted:
  # x/y= z in case y > y_lim,
  # x/y= z_def in case y <= y_lim, where y_lim -> 0.
  # z_def is set to zero if not otherwise specified
  return np.where(y > y_lim,x / np.maximum(y_lim,y),z_def)
  
# ------------------------ all this area commands
#              np.take(np.bincount(AreaID,weights=Values),AreaID)     #     areasum
#                (np.bincount(b, a) / np.bincount(b))[b]              # areaaverage
#              np.take(np.bincount(AreaID,weights=Values),AreaID)     # areaaverage
#                valueMax = np.zeros(AreaID.max() + 1)
#                np.maximum.at(valueMax, AreaID, Values)
#                max = np.take(valueMax, AreaID)             # areamax


def npareatotal(values, areaclass):
    i = 1
    return np.take(np.bincount(areaclass,weights=values),areaclass)
	

def npareaaverage(values, areaclass):
    i = 1
    return np.take(np.bincount(areaclass,weights=values)/ np.bincount(areaclass) ,areaclass)

def npareamaximum(values, areaclass):
    i = 1
    valueMax = np.zeros(areaclass.max() + 1)
    np.maximum.at(valueMax, areaclass, values)
    return np.take(valueMax ,areaclass)
	
  
