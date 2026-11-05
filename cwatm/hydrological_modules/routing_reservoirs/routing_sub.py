# -------------------------------------------------------------------------------
# Name:        Routing_sub
# Purpose:     subroutines for routing kinematic waves
#
# Author:      PB
# Created:     17/01/2017
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------------


import numpy as np
import math
from cwatm.management_modules.data_handling import *

"""
ROUTING subroutines
partly using C++ for speeding up
"""


def Compress(map, mask):
    """
    Compress 2D map to 1D array removing masked values.

    Converts a 2D spatial map to a 1D compressed array by removing
    cells that are masked (missing values or outside model domain).

    Parameters
    ----------
    map : array_like
        Input 2D spatial map to be compressed
    mask : array_like
        Boolean mask array indicating valid cells

    Returns
    -------
    numpy.ndarray
        1D compressed array without missing values
    """

    maskmap = np.ma.masked_array(map, mask)
    compmap = np.ma.compressed(maskmap)
    return compmap


def decompress1(map):
    """
    Decompress 1D array back to 2D spatial map.

    Converts a compressed 1D array back to its original 2D spatial
    representation using stored mask information.

    Parameters
    ----------
    map : array_like
        1D compressed array to be decompressed

    Returns
    -------
    numpy.ndarray
        2D spatial map with missing values restored
    """

    dmap = maskinfo['maskall'].copy()
    dmap[~maskinfo['maskflat']] = map[:]
    dmap = dmap.reshape(maskinfo['shape'])
    return dmap


def pointerJump(dirshort, value, keepDownstream):
    """
    For every cell: a marked cell on its way downstream to the pit (the cell itself included), found by pointer
    jumping (no recursion, no loop over the cells: about log2(longest flow path) NumPy passes).

    :param dirshort: index of the downstream cell, -1 at pits
    :param value: marked cells: their own index, other cells -1
    :param keepDownstream: True: the most downstream marked cell, False: the nearest marked cell
    :return: index of the marked cell for every cell, -1 if there is none
    """

    cells = np.arange(dirshort.size, dtype=np.int64)
    # ptr: a cell further downstream (pits point to themselves); value[c]: the result for the path from c to ptr[c]
    ptr = np.where(dirshort < 0, cells, dirshort).astype(np.int64)
    value = value.astype(np.int64)
    while True:
        down = value[ptr]
        if keepDownstream:
            # a marked cell further downstream wins
            new = np.where(down >= 0, down, value)
        else:
            # the nearest marked cell: keep it, only take the one further downstream if there is none yet
            new = np.where(value >= 0, value, down)
        nxt = ptr[ptr]
        if np.array_equal(nxt, ptr) and np.array_equal(new, value):
            break
        value, ptr = new, nxt
    return value


def dirUpstream(dirshort):
    """
    Upstream cells of every cell (CSR arrays), with NumPy.

    :param dirshort: index of the downstream cell, -1 at pits
    :return: dirupLen (start index of the upstream cells of each cell in dirupID, length cells + 1),
             dirupID (upstream cells, ascending index for each cell - same order as the former Python loop)
    """

    n = maskinfo['mapC'][0]
    up = dirshort >= 0
    # number of upstream cells of each cell
    cnt = np.bincount(dirshort[up], minlength=n)
    dirupLen = np.concatenate(([0], np.cumsum(cnt))).astype(np.int64)
    # upstream cells grouped by their downstream cell, ascending index inside a group (stable sort)
    dirupID = np.nonzero(up)[0][np.argsort(dirshort[up], kind='stable')].astype(np.int64)
    return dirupLen, dirupID


def dirDownstream(dirshort, lddcomp):
    """
    River network order downstream - every cell after all cells upstream of it - and the catchment of each pit.

    Without recursion and without a loop over the cells (NumPy, pointer jumping): for every cell the pit it drains
    to and the number of cells to it. Order = cells sorted by this distance (largest first), cells with the same
    distance by their index. The upstream cells of a cell are therefore in the same order as before (ascending index)
    -> upstreamArea adds them in the same order (bit-identical). (Before 2026-11-04: postorder from every pit, same
    catchment and upstream areas, other order of dirDown.)

    :param dirshort: index of the downstream cell, -1 at pits
    :param lddcomp: repaired ldd, 5 = pit
    :return: dirDown (cells in routing order), catchment (id of the pit catchment, pits numbered 1, 2, ... by index)
    """

    n = maskinfo['mapC'][0]
    cells = np.arange(n, dtype=np.int64)
    # pointer to the downstream cell, pits point to themselves
    ptr = np.where(dirshort < 0, cells, dirshort).astype(np.int64)
    # number of steps to the cell ptr points to (0 for pits)
    dist = np.where(dirshort < 0, 0, 1).astype(np.int64)
    # pointer jumping: after each pass ptr points twice as far downstream, until every ptr is a pit
    while True:
        nxt = ptr[ptr]
        if np.array_equal(nxt, ptr):
            break
        dist += dist[ptr]
        ptr = nxt

    # catchment: pits numbered 1, 2, ... in the order of their index, every cell gets the number of its pit
    pitid = np.zeros(n, dtype=np.int64)
    pits = np.nonzero(lddcomp == 5)[0]
    pitid[pits] = np.arange(1, pits.size + 1)
    catchment = pitid[ptr]

    # routing order: largest distance first, same distance by index
    dirDown = np.lexsort((cells, -dist)).astype(np.int64)
    return dirDown, catchment



def upstreamArea(dirDown, dirshort, area):
    """
    Calculate cumulative upstream area for each cell.

    Computes the total upstream contributing area for each grid cell
    by accumulating cell areas along flow paths.

    Parameters
    ----------
    dirDown : array_like
        Downstream direction array pointing to next downstream cell
    dirshort : array_like
        Short drainage direction array
    area : array_like
        Cell area in square meters for each grid cell

    Returns
    -------
    numpy.ndarray
        Cumulative upstream area for each cell
    """

    ups = area.copy().astype(np.float64)
    lib2.ups(dirDown, dirshort, ups, len(dirDown))
    return ups


def kinematicLevels(dirDown, dirupLen, dirupID):
    """
    Sorts the cells of a river network into levels for the parallel kinematic wave.
    Level 0 = source cells, level n = cells whose upstream cells all have a level < n.
    Cells of one level do not depend on each other -> computed in parallel (lib2.kinematicPar)

    :param dirDown: cells in routing order
    :param dirupLen: start index of the upstream cells of each cell
    :param dirupID: upstream cells
    :return: levelOrder (cells sorted by level), levelStart (start index of each level), number of levels
    """
    size = len(dirDown)
    levelOrder = np.zeros(size, dtype=np.int64)
    levelStart = np.zeros(size + 2, dtype=np.int64)
    nlevels = lib2.kinematicLevels(dirDown, dirupLen, dirupID, size, maskinfo['mapC'][0], levelOrder, levelStart)
    return levelOrder, np.ascontiguousarray(levelStart[:nlevels + 1]), nlevels


def upstream1(downstruct, weight):
    """
    Calculates 1 cell upstream

    :param downstruct:
    :param weight:
    :return: upstream 1cell
    """
    return np.bincount(downstruct, weights=weight)[:-1]


def catchment1(dirshort, points):
    """
    Catchments of points: every cell gets the id of the most downstream point on its way to the pit (the cell
    itself included), 0 if there is none. A point inside the catchment of another point does not get an own
    catchment (same result as the former postorder version, now with NumPy).

    :param dirshort: index of the downstream cell, -1 at pits
    :param points: point ids (> 0), other cells <= 0
    :return: catchment id of every cell
    """

    points = np.asarray(points)
    marked = np.where(points > 0, np.arange(points.size, dtype=np.int64), -1)
    far = pointerJump(dirshort, marked, keepDownstream=True)
    return np.where(far >= 0, points[np.maximum(far, 0)], 0).astype(np.int64)


def subcatchment1(dirshort, points, ups=None):
    """
    Subcatchments of points: every cell gets the id of the nearest point on its way to the pit (the cell itself
    included), 0 if there is none - nested points keep their own subcatchment.
    (Same result as the former postorder version, which did the points by decreasing upstream area ups; ups is
    not needed any more: a point downstream always has a larger upstream area.)

    One cell per point id: if an id is at several cells, only the last cell (highest index) is used (warning).

    :param dirshort: index of the downstream cell, -1 at pits
    :param points: point ids (> 0), other cells <= 0
    :param ups: not used (kept for the call)
    :return: subcatchment id of every cell
    """

    points = np.asarray(points)
    idx = np.nonzero(points > 0)[0]
    # last cell of each id
    vals = points[idx]
    _, lastrev = np.unique(vals[::-1], return_index=True)
    keep = idx[::-1][lastrev]
    if keep.size < idx.size:
        double = np.unique(vals[np.isin(idx, keep, invert=True)])
        msg = "Warning: subcatchments: " + str(double.size) + " point id(s) at more than one cell, only the last cell " \
              "is used (e.g. id " + str(int(double[0])) + ")\n"
        print(CWATMWarning(msg))
    marked = np.full(points.size, -1, dtype=np.int64)
    marked[keep] = keep
    near = pointerJump(dirshort, marked, keepDownstream=False)
    return np.where(near >= 0, points[np.maximum(near, 0)], 0).astype(np.int64)


# ----------------------------------------------------------------



def lddNetwork(ldd):
    """
    Repaired river network and upstream directions from a compressed ldd
    (used by defLdd2 and routing_kinematic.catchment)

    :param ldd: river network (compressed 1D, values 1-9)
    :return: lddCompress (repaired ldd), dirshort (index of the downstream cell, -1 at pits), dirupLen, dirupID
    """

    # decompressing ldd from 1D -> 2D
    dmap = maskinfo['maskall'].copy()
    dmap[~maskinfo['maskflat']] = ldd[:]
    ldd2D = dmap.reshape(maskinfo['shape']).astype(np.int64)
    ldd2D[ldd2D.mask] = 0
    # invalid ldd values inside the mask (not 1-9) become pits; otherwise the C code reads outside its direction
    # table (negative values) and the cell and all cells upstream of it are not routed
    # (only inside the mask: the line above also removes the mask of ldd2D, cells outside must stay 0)
    ldd2D[~maskinfo['mask'] & ((ldd2D < 1) | (ldd2D > 9))] = 5

    # every cell gets an order starting from 0 ...
    lddshortOrder = np.arange(maskinfo['mapC'][0])
    # decompress this map to 2D
    lddOrder = decompress1(lddshortOrder)
    lddOrder[maskinfo['mask']] = -1
    lddOrder = np.array(lddOrder.data, dtype=np.int64)

    lddCompress, dirshort = lddrepair(ldd2D, lddOrder)
    dirupLen, dirupID = dirUpstream(dirshort)
    return lddCompress, dirshort, dirupLen, dirupID


def defLdd2(ldd):
    """
    defines river network

    :param ldd: river network
    :return: ldd variables
    """

    lddCompress, dirshort, dirupLen, dirupID = lddNetwork(ldd)

    # for upstream calculation: each cell gets the id of the downstream cell
    downstruct = np.where(dirshort >= 0, dirshort, np.arange(maskinfo['mapC'][0])).astype(np.int64)
    # all pits gets a high number
    downstruct[lddCompress == 5] = maskinfo['mapC'][0]

    # self.var.dirDown: direction downstream - from each cell the pointer to a downstream cell (can only be 1)
    # self.var.catchment: each catchment with a pit gets a own ID
    dirDown, catchment = dirDownstream(dirshort, lddCompress)
    lendirDown = len(dirDown)

    return lddCompress, dirshort, dirupLen, dirupID, downstruct, catchment, dirDown, lendirDown

def lddrepair(lddnp, lddOrder):
    """
    repairs a river network

    * eliminate unsound parts
    * add pits at points with no connections

    :param lddnp: rivernetwork as 1D array
    :param lddOrder:
    :return: repaired ldd
    """

    yi = lddnp.shape[0]
    xi = lddnp.shape[1]
    # print "========= repair 1"

    # direction downstream naming the order of the cell
    dir = np.array(np.empty(maskinfo['shape']), dtype=np.int64)
    dir.fill(-1)

    lib2.repairLdd1(lddnp, yi, xi)

    lddcomp = compressArray(lddnp).astype(np.int64)
    lib2.dirID(lddOrder, lddnp, dir, yi, xi)
    dirshort = compressArray(dir).astype(np.int64)

    check = np.array(np.zeros(maskinfo['mapC'][0]), dtype=np.int64)
    lib2.repairLdd2(lddcomp, dirshort, check, maskinfo['mapC'][0])

    
    """
    for i in range(maskinfo['mapC'][0]):
       path=[]
       j=i
       while 1:
          if j in path:
            lddcomp[path[-1]] = 5
            dirshort[path[-1]] = -1
            break
          if (lddcomp[j]==5) or (check[j]==1): break
          path.append(j)
          j = dirshort[j]
       check[path]=1
    """

    return lddcomp, dirshort
