# -------------------------------------------------------------------------
# Name:        replace_pcr
# Purpose:     Replace pc raster command with numpy array commands
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
    """
    numpy area total procedure

    :param values:
    :param areaclass:
    :return: calculates the total area of a class
    """
    return np.take(np.bincount(areaclass,weights=values),areaclass)


def npareaaverage(values, areaclass):
    """
    numpy area average procedure

    :param values:
    :param areaclass:
    :return: calculates the average area of a class
    """
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.take(np.bincount(areaclass,weights=values)/ np.bincount(areaclass) ,areaclass)


def npareamaximum(values, areaclass):
    """
    numpy area maximum procedure

    :param values:
    :param areaclass:
    :return: calculates the maximum of an area of a class
    """
    valueMax = np.zeros(areaclass.max() + 1)
    np.maximum.at(valueMax, areaclass, values)
    return np.take(valueMax ,areaclass)


def npareamajority(values, areaclass):
    """
    numpy area majority procedure

    :param values:
    :param areaclass:
    :return: calculates the majority of an area of a class
    """

    uni,ind = np.unique(areaclass,return_inverse=True)
    return np.array([np.argmax(np.bincount(values[areaclass == group])) for group in uni])[ind]








