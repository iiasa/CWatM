# -------------------------------------------------------------------------
# Name:        Modified Puls formulas
# Purpose:     Shared formulas of the Modified Puls approach for lakes (lakes_reservoirs.py)
#              and small lakes (lakes_res_small.py): lake parameter A, Puls factor, outflow, start volume
#
# Author:      PB
# Created:     06/11/2026
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import numpy as np


def lake_parameter_a(dis0, afactor):
    """
    Lake parameter A of the weir formula Q = A * H**2

    channel width from the average discharge (7.1 * Q**0.539), weir coefficient 0.612 * 2/3, gravity

    :param dis0: average discharge at the lake outlet [m3/s]
    :param afactor: calibration factor lakeAFactor [-]
    :return: lake parameter A
    """
    chanwidth = 7.1 * np.power(dis0, 0.539)
    return afactor * 0.612 * 2 / 3 * chanwidth * (2 * 9.81) ** 0.5


def puls_factor(area, dt, a):
    """
    Modified Puls factor area / (dt * sqrt(A)) and its square (for faster calculation in the routing step)

    :param area: lake area [m2]
    :param dt: time step [s]
    :param a: lake parameter A
    :return: factor, factor**2
    """
    factor = area / (dt * np.sqrt(a))
    return factor, np.square(factor)


def puls_outflow(si, factor, factorsqr):
    """
    Lake outflow of a rectangular lake: solution of the quadratic equation
    (storage proportional to the level, Q = A * H**2)

    :param si: storage indicator S/dt + Q/2 [m3/s]
    :param factor: Puls factor
    :param factorsqr: Puls factor**2
    :return: outflow [m3/s]
    """
    return np.square(-factor + np.sqrt(factorsqr + 2 * si))


def puls_outflow_triangular(si, factor, factorsqr):
    """
    Lake outflow of a triangular lake (wetlands, water body type 6)

    :param si: storage indicator S/dt + Q/2 [m3/s]
    :param factor: Puls factor
    :param factorsqr: Puls factor**2
    :return: outflow [m3/s]
    """
    return np.square(-0.5 * factor + np.sqrt(0.25 * factorsqr + 2 * si))


def start_volume(area, q, a):
    """
    Lake volume at the start from the inflow: level H = sqrt(Q / A)

    :param area: lake area [m2]
    :param q: inflow [m3/s]
    :param a: lake parameter A
    :return: lake volume [m3]
    """
    return area * np.sqrt(q / a)
