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


  
# ------------------------ all this area commands
#              np.take(np.bincount(AreaID,weights=Values),AreaID)     #     areasum
#                (np.bincount(b, a) / np.bincount(b))[b]              # areaaverage
#              np.take(np.bincount(AreaID,weights=Values),AreaID)     # areaaverage
#                valueMax = np.zeros(AreaID.max() + 1)
#                np.maximum.at(valueMax, AreaID, Values)
#                max = np.take(valueMax, AreaID)             # areamax


def npareatotal(values, areaclass):
    return np.take(np.bincount(areaclass,weights=values),areaclass)


def npareaaverage(values, areaclass):
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.take(np.bincount(areaclass,weights=values)/ np.bincount(areaclass) ,areaclass)


def npareamaximum(values, areaclass):
    valueMax = np.zeros(areaclass.max() + 1)
    np.maximum.at(valueMax, areaclass, values)
    return np.take(valueMax ,areaclass)


def npareamajority(values, areaclass):
    uni,ind = np.unique(areaclass,return_inverse=True)
    return np.array([np.argmax(np.bincount(values[areaclass == group])) for group in uni])[ind]








