# -------------------------------------------------------------------------
# Name:        replace_pcr
# Purpose:     Replace PCRaster commands with NumPy array operations
#
# Author:      PB
# Created:     2/08/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

"""
PCRaster replacement functions using NumPy operations.

This module provides NumPy-based implementations of common PCRaster spatial
analysis operations, particularly area-based statistics functions. These functions
are used throughout CWatM to perform spatial aggregations and statistics on
raster data using efficient NumPy operations instead of PCRaster library calls.

The module focuses on area-based operations where values are aggregated or
analyzed within discrete spatial units defined by area class identifiers.

Key Functions
-------------
npareatotal : numpy area total calculation
npareaaverage : numpy area average calculation  
npareamaximum : numpy area maximum calculation
npareamajority : numpy area majority calculation

Notes
-----
These functions use NumPy's bincount and advanced indexing operations for
efficient spatial aggregation. They handle missing values and edge cases
appropriately for hydrological modeling applications.
"""

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
    Calculate total values for each area class using NumPy operations.
    
    This function computes the sum of all values within each area class,
    providing a NumPy equivalent to PCRaster's areatotal operation.
    
    Parameters
    ----------
    values : numpy.ndarray
        Array of values to be summed within each area class
    areaclass : numpy.ndarray
        Array of area class identifiers, same shape as values
        
    Returns
    -------
    numpy.ndarray
        Array with same shape as input, where each cell contains the
        total sum of all values within its area class
        
    Notes
    -----
    Uses np.bincount with weights to efficiently compute class totals,
    then maps results back to original array positions using np.take.
    This approach is much faster than iterative summation methods.
    """
    return np.take(np.bincount(areaclass, weights=values), areaclass)


def npareaaverage(values, areaclass):
    """
    Calculate average values for each area class using NumPy operations.
    
    This function computes the mean of all values within each area class,
    providing a NumPy equivalent to PCRaster's areaaverage operation.
    
    Parameters
    ----------
    values : numpy.ndarray
        Array of values to be averaged within each area class
    areaclass : numpy.ndarray  
        Array of area class identifiers, same shape as values
        
    Returns
    -------
    numpy.ndarray
        Array with same shape as input, where each cell contains the
        average of all values within its area class
        
    Notes
    -----
    Uses np.bincount to compute both weighted sums and counts for each class,
    then divides to get averages. Error state management prevents warnings
    from division by zero or invalid operations in empty classes.
    """
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.take(np.bincount(areaclass, weights=values) / np.bincount(areaclass), areaclass)


def npareamaximum(values, areaclass):
    """
    Calculate maximum values for each area class using NumPy operations.
    
    This function finds the maximum value within each area class,
    providing a NumPy equivalent to PCRaster's areamaximum operation.
    
    Parameters
    ----------
    values : numpy.ndarray
        Array of values to find maximum within each area class
    areaclass : numpy.ndarray
        Array of area class identifiers, same shape as values
        
    Returns
    -------
    numpy.ndarray
        Array with same shape as input, where each cell contains the
        maximum value found within its area class
        
    Notes
    -----
    Creates an array sized to hold all possible class IDs, then uses
    np.maximum.at to efficiently find the maximum value for each class.
    The result is mapped back to original positions using np.take.
    """
    valueMax = np.zeros(areaclass.max() + 1)
    np.maximum.at(valueMax, areaclass, values)
    return np.take(valueMax, areaclass)


def npareamajority(values, areaclass):
    """
    Calculate majority values for each area class using NumPy operations.
    
    This function finds the most frequently occurring value within each area
    class, providing a NumPy equivalent to PCRaster's areamajority operation.
    
    Parameters
    ----------
    values : numpy.ndarray
        Array of discrete values to find majority within each area class
    areaclass : numpy.ndarray
        Array of area class identifiers, same shape as values
        
    Returns
    -------
    numpy.ndarray
        Array with same shape as input, where each cell contains the
        most frequently occurring value within its area class
        
    Notes
    -----
    Uses np.unique to identify distinct area classes, then applies bincount
    to count occurrences of each value within each class. The most frequent
    value (argmax of bincount) becomes the majority value for that class.
    Results are mapped back using the inverse indices from unique operation.
    """

    uni, ind = np.unique(areaclass, return_inverse=True)
    return np.array([np.argmax(np.bincount(values[areaclass == group])) for group in uni])[ind]
