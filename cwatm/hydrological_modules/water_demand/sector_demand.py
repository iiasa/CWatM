# -------------------------------------------------------------------------
# Name:        Waterdemand modules
# Purpose: Shared reading of the domestic, industry and livestock water demand maps.
# One definition of time setting, reading, scaling, unit conversion, small-value threshold
# and efficiency, used by domestic.py, industry.py and livestock.py.
#
# Author:      PB
# Created:     04/11/2026
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import numpy as np
from cwatm.management_modules import globals
from cwatm.management_modules.data_handling import returnBool, binding, loadmap, readnetcdf2, divideValues


def sector_time(key):
    """
    Time resolution of a sector demand file.

    Parameters
    ----------
    key : str
        Settings key, e.g. 'domesticTimeMonthly'

    Returns
    -------
    str
        'yearly' if the key is given and False, otherwise 'monthly'
    """
    if key in binding and not returnBool(key):
        return 'yearly'
    return 'monthly'


def new_sector_time(time):
    """
    True if the demand maps have to be read in this time step: at the start and with each new month (or year)
    """
    return globals.dateVar['newStart'] or globals.dateVar['newMonth' if time == 'monthly' else 'newYear']


def read_sector_demand(var, filebinding, wd_date, time, withdrawalvar, consumptionvar=None, scalebinding=None):
    """
    Read withdrawal and consumption of one sector for the month (or year) of wd_date.

    1. read withdrawal (and consumption) from the netCDF file
    2. multiply with the scaling map if scalebinding is in the settings
    3. transform from million m3 per month (or year) to m/day if demand_unit = False
    4. set values below 1 m3/day per cell to 0 (since 2026-11 after the transformation - before it was applied
       to the million m3 values, so there was no real threshold with demand_unit = False)
    5. efficiency = consumption / withdrawal, at most 1

    Parameters
    ----------
    var : object
        Model variables (demand_unit, M3toM, InvCellArea)
    filebinding : str
        Settings key of the netCDF file
    wd_date : datetime
        Date of the water demand (can be a fixed year)
    time : str
        'monthly' or 'yearly'
    withdrawalvar : str
        Variable name of the withdrawal in the file
    consumptionvar : str, optional
        Variable name of the consumption. None: consumption = withdrawal (efficiency 1)
    scalebinding : str, optional
        Settings key of a scaling factor (map or number)

    Returns
    -------
    tuple
        withdrawal [m/day], consumption [m/day], efficiency [-]
    """
    withdrawal = readnetcdf2(filebinding, wd_date, time, value=withdrawalvar)
    if consumptionvar is not None:
        consumption = readnetcdf2(filebinding, wd_date, time, value=consumptionvar)

    # user scaling of withdrawal and consumption through the settings file
    if scalebinding is not None and scalebinding in binding:
        scale = loadmap(scalebinding) + globals.inZero
        withdrawal = withdrawal * scale
        if consumptionvar is not None:
            consumption = consumption * scale

    # transform from mio m3 per year (or month) to m/day if necessary
    if not var.demand_unit:
        if time == 'monthly':
            timediv = globals.dateVar['daysInMonth']
        else:
            timediv = globals.dateVar['daysInYear']
        withdrawal = withdrawal * 1000000 * var.M3toM / timediv
        if consumptionvar is not None:
            consumption = consumption * 1000000 * var.M3toM / timediv

    # avoid small values (less than 1 m3/day per cell): m/day > 1/cellArea
    withdrawal = np.where(withdrawal > var.InvCellArea, withdrawal, 0.0)
    if consumptionvar is None:
        return withdrawal, withdrawal.copy(), 1.
    consumption = np.where(consumption > var.InvCellArea, consumption, 0.0)

    # consumption cannot be more than withdrawal
    efficiency = np.minimum(1., divideValues(consumption, withdrawal))
    return withdrawal, consumption, efficiency

# -------------------------------------------------------------------------
# shared functions of the water allocation (water_demand.py and its parts)
# -------------------------------------------------------------------------

def set_zero(var, names):
    """
    Set each variable in names to its own map of zeros (globals.inZero.copy()).

    Parameters
    ----------
    var : object
        Model variable container (self.var)
    names : list of str
        Names of the variables
    """
    for name in names:
        setattr(var, name, globals.inZero.copy())


# withdrawal of each sector from each source [m]: Desal_Domestic ... GW_Irrigation
SECTOR_SOURCE = [source + '_' + sector
                 for source in ('Desal', 'Channel', 'Lift', 'wwt', 'Lake', 'Res', 'GW')
                 for sector in ('Domestic', 'Industry', 'Livestock', 'Irrigation')]

def split_sectors(total, pots):
    """
    Split the water of one source over the sectors, one after the other.

    Each sector gets at most its potential: part_k = min(rest, pots[k]), rest = total - part_1 - ... - part_k
    (subtracted one by one in this order, as in the code before 2026-11, so the results are bit-identical).

    Parameters
    ----------
    total : ndarray
        Water of the source [m].
    pots : sequence of ndarray
        Potential abstraction of each sector in the order of the allocation (Domestic, Livestock, Industry,
        Irrigation) [m].

    Returns
    -------
    tuple of (parts, rest)
        parts : list of ndarray, the water of each sector [m]; rest : ndarray, total minus all parts [m]
    """
    parts = []
    rest = total
    for pot in pots:
        part = np.minimum(rest, pot)
        parts.append(part)
        rest = rest - part
    return parts, rest


SECTORS = ('Domestic', 'Livestock', 'Industry', 'Irrigation')     # order of split_sectors and of the cascade
SOURCES = ('Desal', 'Channel', 'Lift', 'wwt', 'Lake', 'Res', 'GW')  # order in which the sources are used
DEMAND = {'Domestic': 'domesticDemand', 'Livestock': 'livestockDemand', 'Industry': 'industryDemand',
          'Irrigation': 'totalIrrDemand'}

# orders of the sums as in the code before the split of water_demand.py (2026-11) - kept for bit-identity
# (float addition is not associative, a common order would change the last bit)
ORDER_UNMET = ('Desal', 'Channel', 'wwt', 'Lift', 'Lake', 'Res', 'GW')                # unmet_<sector>
ORDER_WITHDRAWAL_TOTAL = ('Desal', 'Channel', 'wwt', 'Lift', 'Lake', 'Res', 'GW')     # act_nonIrr/act_irrWithdrawal
ORDER_WITHDRAWAL_SW = ('Desal', 'Channel', 'Lift', 'wwt', 'Lake', 'Res')              # act_irrWithdrawalSW
ORDER_WITHDRAWAL_SECTOR = ('Channel', 'Lift', 'Desal', 'wwt', 'Lake', 'Res', 'GW')    # act_dom/liv/indWithdrawal


def rest_of_demand(var, sector, sources):
    """
    Demand of a sector minus the water it got from the sources, subtracted one by one in this order [m].

    Parameters
    ----------
    var : object
        Model variables (domesticDemand ..., <source>_<sector>)
    sector : str
        'Domestic', 'Livestock', 'Industry' or 'Irrigation'
    sources : sequence of str
        Sources in the order of the subtraction, e.g. ('Desal', 'Channel')
    """
    rest = getattr(var, DEMAND[sector])
    for source in sources:
        rest = rest - getattr(var, source + '_' + sector)
    return rest


def pot_source(var, source, fraction):
    """
    Potential abstraction of each sector from one source [m], in SECTORS order.

    min(fraction x demand, rest of the demand after the sources before it in SOURCES)

    Parameters
    ----------
    var : object
        Model variables
    source : str
        Source in SOURCES, e.g. 'GW'
    fraction : str
        Name pattern of the abstraction fractions with %s for the sector, e.g. 'gwAbstractionFraction_%s'
    """
    before = SOURCES[:SOURCES.index(source)]
    return [np.minimum(getattr(var, fraction % sector) * getattr(var, DEMAND[sector]),
                       rest_of_demand(var, sector, before)) for sector in SECTORS]


def sum_vars(var, names):
    """
    Sum of var.<name>, added one by one from left to right in the given order [m].
    """
    total = getattr(var, names[0])
    for name in names[1:]:
        total = total + getattr(var, name)
    return total
