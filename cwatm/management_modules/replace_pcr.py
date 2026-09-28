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
    total = np.bincount(areaclass, weights=values)
    count = np.bincount(areaclass)
    with np.errstate(invalid='ignore', divide='ignore'):
        if total.size > areaclass.size:
            # large, sparse class ids (more classes than cells): take to the cells first, then divide per cell
            # avoids dividing (0/0) over all empty classes; same result
            return np.take(total, areaclass) / np.take(count, areaclass)
        return np.take(total / count, areaclass)


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


class AreaIndex:
    """
    Index for a static area class map (e.g. waterBodyID, adminSegments).

    Built once: the class ids renumbered 0..n-1, so the area functions work with small bincount
    arrays. With onlypositive=True only cells with class > 0 are used and cells with class 0 get 0
    (e.g. lakes); with onlypositive=False class 0 is a normal class and all cells are used.
    For the used cells the results are the same as npareatotal, npareaaverage and npareamaximum
    (bit-identical). The class map must not change after the index is built.

    Parameters
    ----------
    areaclass : numpy.ndarray
        Array of area class identifiers (integer)
    onlypositive : bool
        True: only cells with class > 0; False: all cells, class 0 is a class
    """

    def __init__(self, areaclass, onlypositive=True):
        self.size = areaclass.size
        if onlypositive:
            self.cells = np.nonzero(areaclass > 0)[0]
            cls = areaclass[self.cells]
        else:
            self.cells = None
            cls = areaclass
        self.dense = np.unique(cls, return_inverse=True)[1].reshape(-1).astype(np.int64)
        self.count = np.bincount(self.dense)

    def _values(self, values):
        return values if self.cells is None else values[self.cells]

    def _out(self, result):
        if self.cells is None:
            return result
        out = np.zeros(self.size)
        out[self.cells] = result
        return out

    def total(self, values):
        """Total of values for each class, as npareatotal"""
        return self._out(np.take(np.bincount(self.dense, weights=self._values(values)), self.dense))

    def average(self, values):
        """Average of values for each class, as npareaaverage"""
        with np.errstate(invalid='ignore', divide='ignore'):
            return self._out(np.take(np.bincount(self.dense, weights=self._values(values)) / self.count, self.dense))

    def maximum(self, values):
        """Maximum of values for each class, as npareamaximum"""
        valueMax = np.zeros(self.count.size)
        np.maximum.at(valueMax, self.dense, self._values(values))
        return self._out(np.take(valueMax, self.dense))


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
