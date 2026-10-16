# Purpose: MODFLOW steady state (Dor's version, run 1 of 2): head of all layers with the long-term recharge, written to
# <PathGroundwaterModflowOutput>/steady_state_heads.nc - init_water_table of the transient run (transient.py).
# Called from groundwater_modflow.initial (transient.py) with run_only_steady_state = True; CWatM makes no time step.
import os

import numpy as np

from cwatm.management_modules.data_handling import *
from cwatm.hydrological_modules.groundwater_modflow.transient import setting_bool, renamed_key


def steady_multiplier(nlay, name):
    """
    Permeability multiplier of each layer for the steady state (nlay, nrow, ncol): keys <name><n> (e.g. cal_prm1),
    former name <name>_<n> (with a warning); default 1
    """
    values = []
    for n in range(1, nlay + 1):
        key = renamed_key(name + str(n), name + '_' + str(n))
        values.append(float(cbinding(key)) if key is not None else 1.)
    return np.array(values)[:, np.newaxis, np.newaxis]


def steady_state(gw, basin, head):
    """
    Steady state of MODFLOW (Dor's version, run 1 of 2) with the long-term recharge (longterm_recharge, m/day,
    default 0.0001), drains (drain elevation), optional constant head (include_constant_head_steady_state,
    chd_boundary_map: 1 or -9999 (none), chd_absolute: the map is the head in m, else the top; at least the top),
    permeability multipliers cal_prm<n> / cal_prm_v<n>, period Ndays_steady (default 1 day).
    gw: the groundwater_modflow object (transient.py) after its initial part up to the drains (grid, layers,
    permeability, specific yield / storage, drain elevation); basin: active ModFlow cells; head: initial head
    (nlay, nrow, ncol). Writes the head of all layers to <PathGroundwaterModflowOutput>/steady_state_heads.nc (usable
    as init_water_table in run 2) and stops CWatM without a time step
    """
    print('\n=> MODFLOW steady state (run_only_steady_state = True): no time step of CWatM')
    if 'include_rch_drn_steady_state' in binding and not setting_bool('include_rch_drn_steady_state'):
        print(CWATMWarning("Warning: include_rch_drn_steady_state is not used - the steady state always has "
                           "recharge and drains"))
    top = gw.layer_boundaries[0]
    permeability = gw.permeability * steady_multiplier(gw.nlay, 'cal_prm')
    multiplier_v = steady_multiplier(gw.nlay, 'cal_prm_v')
    permeability_vertical = None
    if gw.permeability_vertical is not None or np.any(multiplier_v != 1):
        vertical = gw.permeability if gw.permeability_vertical is None else gw.permeability_vertical
        permeability_vertical = vertical * multiplier_v

    # long-term recharge (m/day) into layer 1
    if 'longterm_recharge' in binding:
        # a value or a map at CWatM resolution (a value as map: inZero + value)
        # negative values (mean net recharge of the seepage scheme: capillary rise from the aquifer > percolation)
        # set to 0 - with them the steady state did not converge (UNWMZ: 1.8 % of the cells, 5000 outer iterations
        # with dbd / cooley / super_complex; set to 0: converged in 1.3 s)
        longterm = globals.inZero + loadmap('longterm_recharge')
        if np.any(longterm < 0):
            print(CWATMWarning("Warning: longterm_recharge < 0 in " + str(int(np.sum(longterm < 0))) +
                               " cells - set to 0 for the steady state"))
        recharge = gw.grid.to_modflow(np.maximum(longterm, 0), nanvalue=0, all_cells=True)
    else:
        print(CWATMWarning("Warning: longterm_recharge is missing - steady state with 0.0001 m/day recharge"))
        recharge = np.full((gw.grid.nrow, gw.grid.ncol), 0.0001)

    # constant head in layer 1: chd_boundary_map 1 (or the head with chd_absolute = True), -9999: no constant head
    constant_head = None
    chd = renamed_key('include_constant_head_steady_state', 'include_cosntant_head_steady_state')
    if chd is not None and returnBool(chd):
        values = globals.inZero + loadmap('chd_boundary_map')
        values = np.where(values == -9999, np.nan, values)
        constant_head = gw.grid.to_modflow(values, all_cells=True)
        if not setting_bool('chd_absolute'):
            constant_head = constant_head * top
        constant_head = np.where(np.isnan(constant_head), np.nan, np.maximum(constant_head, top))

    solver = cbinding('modflow_solver_steady').strip().lower() if 'modflow_solver_steady' in binding else 'dbd'
    model = gw.ModFlow(
        'steady', cbinding('PathGroundwaterModflowOutput'), gw.directory_mf6dll,
        timestep=1, specific_storage=0 if gw.specific_storage is None else gw.specific_storage,
        specific_yield=gw.specific_yield, nlay=gw.nlay, nrow=gw.grid.nrow, ncol=gw.grid.ncol,
        rowsize=gw.grid.domain['rowsize'], colsize=gw.grid.domain['colsize'], top=top,
        bottom=gw.layer_boundaries[1] if gw.nlay == 1 else gw.layer_boundaries[1:], basin=basin, head=head,
        topography=top, permeability=permeability, permeability_vertical=permeability_vertical,
        confined=gw.confined, drain_elevation=gw.drain_elevation, load_from_disk=False, setpumpings=False,
        verbose=gw.verbose, solver=solver, binary=gw.binary, steady=True,
        perlen=float(cbinding('Ndays_steady')) if 'Ndays_steady' in binding else 1.0, constant_head=constant_head)
    model.set_recharge(recharge)
    model.step()
    if not model.converged:
        print(CWATMWarning("Warning: the MODFLOW steady state did not converge - the head in steady_state_heads.nc "
                           "is not reliable; use another modflow_solver_steady or change Ndays_steady"))
    heads = model.decompress(np.asarray(model.head, dtype=np.float64)).reshape(
        (gw.nlay, gw.grid.nrow, gw.grid.ncol))
    model.finalize()

    filename = os.path.join(cbinding('PathGroundwaterModflowOutput'), 'steady_state_heads.nc')
    gw.grid.write_netcdf(filename, 'head', heads, 'm', 'MODFLOW steady state head')
    print('=> MODFLOW steady state head of ' + str(gw.nlay) + ' layer(s) written to: ' + filename)
    print('   use it in the next run: load_init_water_table = True, init_water_table = ' + filename)
    # no time step of CWatM (ModelFrame.run: while currentStep <= lastStep); discharge of the first gauge (returned
    # by run_cwatm.CWATMexe, set by output.py in each time step): 0
    dateVar['intEnd'] = dateVar['intStart'] - 1
    gw.var.firstout = 0.
