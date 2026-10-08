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

sys.setrecursionlimit(5000)
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


def postorder(dirUp, catchment, node, catch, dirDown):
    """
    Perform postorder tree traversal of drainage network.

    Traverses the drainage network tree structure in postorder to assign
    catchment identifiers and establish downstream flow directions.

    Parameters
    ----------
    dirUp : list
        Upstream direction lookup table
    catchment : array_like
        Catchment identifier array
    node : int
        Current node being processed
    catch : int
        Catchment identifier to assign
    dirDown : list
        Downstream direction list being built

    Returns
    -------
    tuple
        Updated dirDown and catchment arrays
    """

    if dirUp[node] != []:
        postorder(dirUp, catchment, dirUp[node][0], catch, dirDown)
        catchment[dirUp[node][0]] = catch
        dirDown.append(dirUp[node][0])
        if len(dirUp[node]) > 1:
            postorder(dirUp, catchment, dirUp[node][1], catch, dirDown)
            catchment[dirUp[node][1]] = catch
            dirDown.append(dirUp[node][1])
            if len(dirUp[node]) > 2:
                postorder(dirUp, catchment, dirUp[node][2], catch, dirDown)
                catchment[dirUp[node][2]] = catch
                dirDown.append(dirUp[node][2])
                if len(dirUp[node]) > 3:
                    postorder(dirUp, catchment, dirUp[node][3], catch, dirDown)
                    catchment[dirUp[node][3]] = catch
                    dirDown.append(dirUp[node][3])
                    if len(dirUp[node]) > 4:
                        postorder(dirUp, catchment, dirUp[node][4], catch, dirDown)
                        catchment[dirUp[node][4]] = catch
                        dirDown.append(dirUp[node][4])
                        if len(dirUp[node]) > 5:
                            postorder(dirUp, catchment, dirUp[node][5], catch, dirDown)
                            catchment[dirUp[node][5]] = catch
                            dirDown.append(dirUp[node][5])
                            if len(dirUp[node]) > 6:
                                postorder(dirUp, catchment, dirUp[node][6], catch, dirDown)
                                catchment[dirUp[node][6]] = catch
                                dirDown.append(dirUp[node][6])
                                if len(dirUp[node]) > 7:
                                    postorder(dirUp, catchment, dirUp[node][7], catch, dirDown)
                                    catchment[dirUp[node][7]] = catch
                                    dirDown.append(dirUp[node][7])


def dirUpstream(dirshort):
    """
    Build upstream direction network from drainage direction map.

    Creates upstream direction lookup tables from the compressed drainage
    direction array, enabling traversal from outlets to sources.

    Parameters
    ----------
    dirshort : array_like
        Compressed drainage direction array

    Returns
    -------
    tuple
        Upstream direction arrays (dirUp, dirupLen, dirupID)
    """

    # -- up direction
    dirUp = list([] for i in range(maskinfo['mapC'][0]))
    for i in range(dirshort.shape[0]):
        value = dirshort[i]
        if value > -1:
            dirUp[value].append(i)

    dirupLen = [0]
    dirupID = []
    j = 0
    for i in range(dirshort.shape[0]):
        j += len(dirUp[i])
        dirupLen.append(j)
        for k in range(len(dirUp[i])):
            dirupID.append(dirUp[i][k])

    return dirUp, np.array(dirupLen).astype(np.int64), np.array(dirupID).astype(np.int64)


def dirDownstream(dirUp, lddcomp, dirDown):
    """
    runs the river network tree downstream - from source to outlet

    :param dirUp:
    :param lddcomp:
    :param dirDown:
    :return: direction downstream
    """

    catchment = np.array(np.zeros(maskinfo['mapC'][0]), dtype=np.int64)
    j = 0
    for pit in range(maskinfo['mapC'][0]):
        if lddcomp[pit] == 5:
            j += 1
            postorder(dirUp, catchment, pit, j, dirDown)
            dirDown.append(pit)
            catchment[pit] = j
    return np.array(dirDown).astype(np.int64), np.array(catchment).astype(np.int64)



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

    ups = area.copy()
    lib2.ups(dirDown, dirshort, ups, len(dirDown))
    return ups

def upstream1(downstruct, weight):
    """
    Calculates 1 cell upstream

    :param downstruct:
    :param weight:
    :return: upstream 1cell
    """
    return np.bincount(downstruct, weights=weight)[:-1]


def downstream1(dirUp, weight):
    """
    calculated 1 cell downstream

    :param dirUp:
    :param weight:
    :return: dowmnstream 1 cell
    """

    downstream = weight.copy()
    k = 0
    for i in dirUp:
        for j in i:
            downstream[j] = weight[k]
        k += 1
    return downstream


def catchment1(dirUp, points):
    """
    calculates all cells which belongs to a catchment from point onward

    :param dirUp:
    :param points:
    :return: subcatchment
    """

    subcatch = np.array(np.zeros(maskinfo['mapC'][0]), dtype=np.int64)
    # if subcatchment = true -> calculation of subcatchment: every point is calculated
    # if false: calculation of catchment: only point calculated which are not inside a bigger catchment
    # from another point


    for cell in range(maskinfo['mapC'][0]):
        j = points[cell]
        if (j > 0) and (subcatch[cell] < 1):
            dirDown = []
            postorder(dirUp, subcatch, cell, j, dirDown)
            subcatch[cell] = j
    return subcatch



def subcatchment1(dirUp, points, ups):
    """
    calculates subcatchments of points

    :param dirUp:
    :param points:
    :param ups:
    :return: subcatchment
    """

    subcatch = np.array(np.zeros(maskinfo['mapC'][0]), dtype=np.int64)
    # if subcatchment = true -> calculation of subcatchment: every point is calculated
    # if false: calculation of catchment: only point calculated which are not inside a bigger catchment
    # from another point

    subs = {}
    # sort waterbodies of reverse upstream area
    for cell in range(maskinfo['mapC'][0]):
        if points[cell] > 0:
            subs[points[cell]] = [cell, ups[cell]]
    subsort = sorted(list(subs.items()), key=lambda x: x[1][1], reverse=True)


    # for cell in xrange(maskinfo['mapC'][0]):
    for sub in subsort:
        j = sub[0]
        cell = sub[1][0]
        dirDown = []
        postorder(dirUp, subcatch, cell, j, dirDown)
        subcatch[cell] = j

    return subcatch


# ----------------------------------------------------------------



def defLdd2(ldd):
    """
    defines river network

    :param ldd: river network
    :return: ldd variables
    """

    # decompressing ldd from 1D -> 2D
    dmap = maskinfo['maskall'].copy()
    dmap[~maskinfo['maskflat']] = ldd[:]
    ldd2D = dmap.reshape(maskinfo['shape']).astype(np.int64)
    ldd2D[ldd2D.mask] = 0

    # every cell gets an order starting from 0 ...
    lddshortOrder = np.arange(maskinfo['mapC'][0])
    # decompress this map to 2D
    lddOrder = decompress1(lddshortOrder)
    lddOrder[maskinfo['mask']] = -1
    lddOrder = np.array(lddOrder.data, dtype=np.int64)


    lddCompress, dirshort = lddrepair(ldd2D, lddOrder)
    dirUp, dirupLen, dirupID = dirUpstream(dirshort)

    # for upstream calculation
    inAr = np.arange(maskinfo['mapC'][0], dtype=np.int64)
    # each upstream pixel gets the id of the downstream pixel
    downstruct = downstream1(dirUp, inAr).astype(np.int64)
    # all pits gets a high number
    downstruct[lddCompress == 5] = maskinfo['mapC'][0]

    # self.var.dirDown: direction downstream - from each cell the pointer to a downstream cell (can only be 1)
    # self.var.catchment: each catchment with a pit gets a own ID
    dirDown = []
    dirDown, catchment = dirDownstream(dirUp, lddCompress, dirDown)
    lendirDown = len(dirDown)

    return lddCompress, dirshort, dirUp, dirupLen, dirupID, downstruct, catchment, dirDown, lendirDown

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
