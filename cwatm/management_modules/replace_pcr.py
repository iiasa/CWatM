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
AreaIndex : precomputed index of a static class map (total, average, maximum)

Notes
-----
These functions use NumPy's bincount and advanced indexing operations for
efficient spatial aggregation. The class map must be integer and >= 0
(np.bincount; a float class map or a negative class gives Error 140).
Class 0 is a normal class. Missing values are not handled: a NaN in values
gives NaN for the whole class.
"""

import numpy as np

from cwatm.management_modules.messages import CWATMError

__all__ = ["npareatotal", "npareaaverage", "npareamaximum", "npareamajority", "AreaIndex"]


def _classerror(areaclass):
    """
    Error 140 if the class map cannot be used by np.bincount / as an index, otherwise None.

    Checked only after numpy failed (npareatotal, npareaaverage) or before np.maximum.at
    (npareamaximum: a negative class would silently index from the end of the array).
    """
    a = np.asarray(areaclass)
    if a.dtype.kind not in "biu":
        why = "it has the type " + str(a.dtype) + " but must be integer (e.g. .astype(np.int64))"
    elif a.size and a.min() < 0:
        why = "it has negative class ids (smallest: " + str(a.min()) + "), class ids must be >= 0"
    else:
        return None
    return CWATMError("Error 140: The class map of an area function (npareatotal, npareaaverage, "
                      "npareamaximum) cannot be used:\n" + why)


# ------------------------ the area commands in short (AreaID = class map, Values = values)
#   areatotal:    np.take(np.bincount(AreaID, weights=Values), AreaID)
#   areaaverage:  np.take(np.bincount(AreaID, weights=Values) / np.bincount(AreaID), AreaID)
#   areamaximum:  valueMax = np.zeros(AreaID.max() + 1); valueMax[AreaID] = -np.inf
#                 np.maximum.at(valueMax, AreaID, Values)
#                 np.take(valueMax, AreaID)


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
    try:
        total = np.bincount(areaclass, weights=values)
    except (TypeError, ValueError) as err:
        e = _classerror(areaclass)
        if e is None:
            raise
        raise e from err
    return np.take(total, areaclass)


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
    try:
        total = np.bincount(areaclass, weights=values)
    except (TypeError, ValueError) as err:
        e = _classerror(areaclass)
        if e is None:
            raise
        raise e from err
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
    Creates an array sized to hold all possible class IDs, starting at -inf
    (so a class with only negative values gets its real maximum, not 0), then
    uses np.maximum.at to find the maximum value for each class.
    The result is mapped back to original positions using np.take.
    The class map is checked first (Error 140): a negative class would not
    raise an error in np.maximum.at but index from the end of the array.
    """
    e = _classerror(areaclass)
    if e is not None:
        raise e
    # -inf only at the used class ids: np.zeros is cheap for large, sparse ids, np.full would fill all
    valueMax = np.zeros(areaclass.max() + 1)
    valueMax[areaclass] = -np.inf
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
    For maximum the cells are sorted by class once, so each call is one np.maximum.reduceat.

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
        # for maximum: cells sorted by class and the start of each class in the sorted cells
        # (every class has at least one cell, so the starts are strictly increasing)
        self.order = np.argsort(self.dense, kind='stable')
        self.starts = np.concatenate(([0], np.cumsum(self.count)[:-1])).astype(np.int64)

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
        """Average of values for each class, as npareaaverage (every class has a count >= 1, no division by 0)"""
        return self._out(np.take(np.bincount(self.dense, weights=self._values(values)) / self.count, self.dense))

    def maximum(self, values):
        """Maximum of values for each class, as npareamaximum"""
        if self.count.size == 0:
            return self._out(np.zeros(0))
        v = np.asarray(self._values(values), dtype=np.float64)
        valueMax = np.maximum.reduceat(v[self.order], self.starts)
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
    Without a loop over the classes: each (class, value) pair gets one number,
    np.unique counts the pairs, and per class the pair with the highest count
    is taken. With a tie the smallest value wins (as np.argmax of a bincount).
    Values can be any discrete numbers (also negative); areaclass can be any integers.
    """
    _, cls = np.unique(areaclass, return_inverse=True)
    vuni, val = np.unique(values, return_inverse=True)
    cls = cls.reshape(-1).astype(np.int64)
    val = val.reshape(-1).astype(np.int64)
    # pairs sorted by class, then by value
    pair, count = np.unique(cls * vuni.size + val, return_counts=True)
    pcls = pair // vuni.size
    # per class: highest count first, with a tie the smallest value first
    order = np.lexsort((pair, -count, pcls))
    first = order[np.concatenate(([True], pcls[order][1:] != pcls[order][:-1]))]
    return vuni[pair[first] % vuni.size][cls]
