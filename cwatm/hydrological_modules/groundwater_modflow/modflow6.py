"""
MODFLOW 6 through its library libmf6 (BMI with xmipy) for the CWatM coupling (transient.py)

The input files are written with flopy (nlay layers, one stress period which is solved again in each step) and
reused if no input changed. Recharge, pumping, head and drain flow are exchanged through the BMI pointers.
Used in the CWatM process (modflow_subprocess = False) or in a child process (modflow6_process.py).
"""
from time import time
from contextlib import contextmanager
import os
import hashlib
import importlib
import platform

import numpy as np
import pandas as pd

from cwatm.management_modules.messages import CWATMError, CWATMFileError
from cwatm.management_modules.data_modflow import (make_directory, remove_file, read_binary, read_text,
                                                   write_text, mf6_library_path, mf6_simulation_file,
                                                   mf6_error_text)
# flopy and xmipy are imported when they are needed (only for MODFLOW runs)


@contextmanager
def cd(newdir):
    """Change the working directory in a with block"""
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


# functions of libmf6 used by CWatM through xmipy
MF6_FUNCTIONS = ['initialize', 'finalize', 'get_end_time', 'get_current_time', 'get_time_step',
                 'get_var_address', 'get_value_ptr', 'prepare_time_step', 'finalize_time_step',
                 'get_subcomponent_count', 'prepare_solve', 'solve', 'finalize_solve']

# name of the MODFLOW library
MF6_LIBRARY = {'Windows': 'libmf6.dll', 'Linux': 'libmf6.so', 'Darwin': 'libmf6.dylib'}

# settings of the MODFLOW solver IMS (modflow_solver in the settings file); cooley: Dor's version (modflow_layers_df)
MF6_SOLVERS = {
    # rclose: MODFLOW default of complexity SIMPLE - the former L2NORM_RCLOSE 0.1*86400*timestep*cells (Bhima 1.6e9)
    # had no effect, the convergence is controlled by the head change (Bhima bit-identical)
    'simple': dict(complexity='SIMPLE', linear_acceleration='BICGSTAB'),
    'complex': dict(complexity='COMPLEX'),
    'super_complex': dict(complexity='COMPLEX', linear_acceleration='BICGSTAB', under_relaxation='SIMPLE',
                          under_relaxation_gamma=0.1, backtracking_number=5, backtracking_tolerance=10 ** 5,
                          backtracking_reduction_factor=0.3, backtracking_residual_limit=150),
    # COOLEY under-relaxation can handle abrupt wetting and drying cycles. outer_dvclose: with the COMPLEX default
    # (0.1 m) MODFLOW reported convergence with budget errors up to -187 % (UNWMZ, drains with a large conductance)
    'cooley': dict(complexity='COMPLEX', linear_acceleration='BICGSTAB', under_relaxation='COOLEY',
                   under_relaxation_gamma=0.3, backtracking_number=10, backtracking_tolerance=1.5,
                   backtracking_reduction_factor=0.5, backtracking_residual_limit=100, outer_dvclose=0.01,
                   inner_dvclose=0.001),
    # steady state (Dor's version): delta-bar-delta under-relaxation for strong non-linear oscillations.
    # outer_dvclose / inner_dvclose: with the COMPLEX default (0.1 m) the steady state depended on the start head in
    # cells with a dry layer 1 (UNWMZ: 6 cells up to 3.8 m); with 0.001 m the same head from each start (150 s, before 110 s)
    'dbd': dict(complexity='COMPLEX', linear_acceleration='BICGSTAB', under_relaxation='DBD',
                under_relaxation_gamma=0.05, backtracking_number=5, backtracking_tolerance=10 ** 5,
                backtracking_reduction_factor=0.3, backtracking_residual_limit=150, outer_maximum=5000,
                inner_maximum=500, outer_dvclose=0.001, inner_dvclose=0.0001)}


def mf6_constant(a):
    """A uniform array as one value (written as CONSTANT by flopy: smaller file, same value), else the array"""
    a = np.asarray(a)
    if a.size > 0 and np.all(a == a.flat[0]):
        return a.flat[0].item()
    return a


def mf6_array(name, data, binary, shape, dtype=np.float64):
    """
    Array for a flopy package: binary file <name>.bin with the given shape (exact values, faster to write),
    or the data as it is (flopy writes it as text). A single value (CONSTANT, see mf6_constant) stays a value
    """
    if not binary or np.isscalar(data):
        return data
    return {'filename': name + '.bin', 'factor': 1.0, 'iprn': 1, 'binary': True,
            'data': np.asarray(data, dtype=dtype).reshape(shape)}


def mf6_list(name, cells, values, binary):
    """
    stress_period_data for a flopy list package (RCH, WEL, DRN): one row for each cell of the bool map cells
    (a 2D map: layer 1, a 3D map: each layer) with layer, row, column and the values {name: one value or an array
    with a value for each cell}.
    Binary file <name>.bin for period 1, or a list of rows (flopy writes it as text). For binary the data go to
    flopy as pandas DataFrame: a list of tuples is converted very slowly by flopy (Bhima: 3.5 s per package
    instead of ~1 s)
    """
    # cells (nrow, ncol): layer 1, cells (nlay, nrow, ncol): the cells of each layer
    if cells.ndim == 3:
        layer, row, column = np.nonzero(cells)
    else:
        row, column = np.nonzero(cells)
        layer = np.zeros(row.shape, np.int64)
    data = {name_value: np.full(row.shape, value, dtype=np.float64) for name_value, value in values.items()}
    if not binary:
        return [[l, r, c, *v] for l, r, c, *v in zip(layer.tolist(), row.tolist(), column.tolist(),
                                                     *(d.tolist() for d in data.values()))]
    data = pd.DataFrame(dict({'layer': layer.astype(np.int64), 'row': row.astype(np.int64),
                              'column': column.astype(np.int64)}, **data))
    return {0: {'filename': name + '.bin', 'factor': 1.0, 'iprn': 1, 'binary': True, 'data': data}}


def mf6_input_hash(timestep, specific_storage, specific_yield, nlay, nrow, ncol, rowsize, colsize, top, bottom,
                   basin, topography, permeability, setpumpings=False, pumpingloc=None, binary=True,
                   permeability_vertical=None, confined=None, drain_elevation=None, solver=None, steady=False,
                   perlen=1.0, constant_head=None):
    """
    Hash over everything that goes into the MODFLOW input files, the flopy version and the source code of this
    file (a code change writes the files new). The initial head and the run length are not part of the files
    """
    flopy = importlib.import_module("flopy")
    h = hashlib.sha256()
    h.update(read_binary(__file__))
    h.update(flopy.__version__.encode())
    for value in (timestep, specific_storage, specific_yield, nlay, nrow, ncol, rowsize, colsize, top, bottom,
                  basin, topography, permeability, setpumpings, pumpingloc, binary, permeability_vertical, confined,
                  drain_elevation, solver, steady, perlen, constant_head):
        if value is None:
            # not as array: an object array would give a memory address (different in each run)
            h.update(b'None')
            continue
        a = np.ascontiguousarray(value)
        h.update(str(a.dtype).encode() + str(a.shape).encode() + a.tobytes())
    return h.hexdigest()


class ModFlowSimulation:
    """
    One MODFLOW 6 model (nlay layers, the same active cells in each layer) run through libmf6

    Arrays at ModFlow resolution (nrow, ncol), with a layer dimension (nlay, nrow, ncol) for specific_yield,
    specific_storage, bottom, permeability and permeability_vertical (m/day, k33; None: = permeability) and confined
    (0: confined, > 0: convertible; None: all convertible). basin: active cells (nrow, ncol). head: initial head
    (nrow, ncol) or (nlay, nrow, ncol). Recharge into layer 1, drains in layer 1 at drain_elevation (None:
    topography). Pumping wells (setpumpings) in the cells of pumpingloc ((nrow, ncol): layer 1, or (nlay, nrow,
    ncol)). load_from_disk: reuse the input files in <folder>/wd if no input changed (hash), binary: binary input
    files (else text). Solver: solver = simple, complex, super_complex, cooley or dbd (MF6_SOLVERS); solver None:
    simple.

    Attributes used by transient.py: head (active cells), drainage (drain flow, m3 per period), actualwell_rate
    (actual pumping, m3 per period), basin, decompress, layer_flows, set_recharge, set_groundwater_abstraction, step,
    finalize
    """

    def __init__(self, name, folder, path_mf6dll, timestep, specific_storage, specific_yield, nlay, nrow, ncol,
                 rowsize, colsize, top, bottom, basin, head, topography, permeability, load_from_disk=False,
                 setpumpings=False, pumpingloc=None, verbose=False, binary=True, permeability_vertical=None,
                 confined=None, drain_elevation=None, solver=None, steady=False, perlen=1.0, constant_head=None):

        self.name = name.upper()  # MODFLOW requires the name to be uppercase
        self.dir_mf6dll = path_mf6dll
        self.nrow, self.ncol = nrow, ncol
        self.nlay = nlay
        self.rowsize, self.colsize = rowsize, colsize
        self.basin = basin
        self.wellsloc = pumpingloc if setpumpings else None
        # steady state (run_only_steady_state): own folder wd_steady, one steady stress period of perlen days
        self.working_directory = os.path.join(folder, 'wd_steady' if steady else 'wd')
        make_directory(self.working_directory)
        self.verbose = verbose
        # the initial head is not in the files (set through the BMI pointer in load_bmi)
        self.head0 = head

        # the MODFLOW input files are written new only if an input changed (hash in wd/input_hash);
        # load_from_disk = False: always write new
        hash_file = os.path.join(self.working_directory, 'input_hash')
        input_hash = mf6_input_hash(timestep, specific_storage, specific_yield, nlay, nrow, ncol, rowsize, colsize,
                                    top, bottom, basin, topography, permeability, setpumpings, pumpingloc, binary,
                                    permeability_vertical, confined, drain_elevation, solver, steady, perlen,
                                    constant_head)
        reuse = load_from_disk and read_text(hash_file) == input_hash

        if reuse:
            if self.verbose:
                print("MODFLOW input files reused (inputs unchanged)")
        else:
            remove_file(hash_file)
            self.write_input(timestep, specific_storage, specific_yield, nlay, top, bottom, topography, permeability,
                             setpumpings, binary, permeability_vertical, confined, drain_elevation, solver, steady,
                             perlen, constant_head)
            write_text(hash_file, input_hash)

        self.load_bmi(setpumpings)

    def write_input(self, timestep, specific_storage, specific_yield, nlay, top, bottom, topography, permeability,
                    setpumpings, binary, permeability_vertical=None, confined=None, drain_elevation=None,
                    solver=None, steady=False, perlen=1.0, constant_head=None):
        """Write the MODFLOW input files with flopy (the packages are registered in the simulation)"""
        flopy = importlib.import_module("flopy")
        if self.verbose:
            print("Creating MODFLOW model")
        # MODFLOW runs through the library (libmf6), not mf6.exe; no memory tables in mfsim.lst
        sim = flopy.mf6.MFSimulation(sim_name=self.name, version='mf6', sim_ws=self.working_directory)

        # one stress period, solved again in each step (see step): the files do not depend on the run length
        flopy.mf6.ModflowTdis(sim, nper=1, perioddata=[(float(perlen) if steady else 1.0, 1, 1)])

        # iterative model solution. If the model fails with xmipy.errors.XMIError: MODFLOW 6 BMI, exception in:
        # finalize_solve () - use a smaller modflow_timestep, or another solver (modflow_solver)
        # (the [OPTIONS] use_complex_solver_for_modflow / use_super_complex_solver_for_modflow: transient.py)
        if solver is None:
            solver = 'simple'
        ims = MF6_SOLVERS[solver]
        if self.verbose:
            print('MODFLOW solver', solver, '- complexity', ims['complexity'])
        flopy.mf6.ModflowIms(sim, print_option=None, **ims)

        # groundwater flow model (newtonoptions='under_relaxation' can help if there is no convergence)
        gwf = flopy.mf6.ModflowGwf(sim, modelname=self.name, newtonoptions='under_relaxation', print_input=False,
                                   print_flows=False)

        # input files: binary *.bin (binary = True: exact values, faster to write) or text
        # (storage STO stays text: flopy 3.10 cannot write sy as binary file - "modeltime" error)
        shape = (nlay, self.nrow, self.ncol)

        # maps of layer 1 (nrow, ncol) for all layers (one layer: unchanged, the files are the same as before)
        def all_layers(a):
            return a if nlay == 1 else np.broadcast_to(a, shape)

        # cell type of NPF / STO: 0 confined, 1 convertible (Dor: set_confinedAquifer); None: all convertible
        celltype = 1 if confined is None else mf6_array('icelltype', mf6_constant(
            (np.asarray(confined) > 0).astype(np.int32)), binary, shape, np.int32)

        flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=self.nrow, ncol=self.ncol, delr=self.rowsize,
                                delc=self.colsize, top=mf6_array('top', top, binary, shape[1:]),
                                botm=mf6_array('botm', bottom, binary, shape),
                                idomain=mf6_array('idomain', all_layers(self.basin), binary, shape, np.int32),
                                nogrb=True)

        # strt = top of the aquifer, so the files do not depend on the initial head; the real initial head is
        # set through the BMI pointer in load_bmi (tested: bit-identical to strt = head)
        flopy.mf6.ModflowGwfic(gwf, strt=mf6_array('strt', all_layers(top), binary, shape))
        # horizontal permeability k, vertical k33 (Dor: permeability_vertical; without k33 MODFLOW uses k)
        npf = dict(k=mf6_array('k', mf6_constant(permeability * timestep), binary, shape))
        if permeability_vertical is not None:
            npf['k33'] = mf6_array('k33', mf6_constant(permeability_vertical * timestep), binary, shape)
        flopy.mf6.ModflowGwfnpf(gwf, save_flows=True, icelltype=celltype, **npf)

        # output control only to stop MODFLOW printing all heads into TRANSIENT.lst (without OC, or with an empty
        # OC, MODFLOW prints the heads of the last time step of each period: Bhima 198 MB, +7 s). CWatM gets the
        # head through the BMI pointer. ('HEAD', 'FREQUENCY', 10) is every 10th time step of a stress period -
        # with 1 time step per period never, so TRANSIENT.hds stays empty
        flopy.mf6.ModflowGwfoc(gwf, head_filerecord=f'{self.name}.hds', saverecord=[('HEAD', 'FREQUENCY', 10)])

        flopy.mf6.ModflowGwfsto(gwf, save_flows=False, iconvert=celltype, ss=mf6_constant(specific_storage),
                                sy=mf6_constant(specific_yield), steady_state=steady, transient=not steady)

        # recharge in each active cell: > 0, in m per MODFLOW period (set in each step)
        flopy.mf6.ModflowGwfrch(gwf, fixed_cell=False, print_input=False, print_flows=False, save_flows=False,
                                boundnames=None, maxbound=self.basin.sum(),
                                stress_period_data=mf6_list('recharge', self.basin, {'recharge': 0}, binary))

        if setpumpings:
            # pumping wells: < 0 for abstraction, in m3 per MODFLOW period (set in each step)
            # no boundnames argument: flopy treats boundnames=False as names and then refuses a binary list
            # (the text file is the same without it)
            flopy.mf6.ModflowGwfwel(gwf, print_input=False, print_flows=False, save_flows=False,
                                    maxbound=self.wellsloc.sum(),
                                    stress_period_data=mf6_list('wells', self.wellsloc, {'q': 0}, binary),
                                    auto_flow_reduce=0.1)

        # drains in each active cell of layer 1: elevation = drain_elevation (None: top of the aquifer), conductance =
        # permeability of layer 1 * cell area * timestep (baseflow and capillary rise)
        elevation = topography if drain_elevation is None else drain_elevation
        conductance = permeability[0, self.basin] * self.rowsize * self.colsize * timestep
        flopy.mf6.ModflowGwfdrn(gwf, maxbound=self.basin.sum(), print_input=False, print_flows=False,
                                save_flows=False, stress_period_data=mf6_list(
                                    'drainage', self.basin, {'elev': elevation[self.basin], 'cond': conductance},
                                    binary))

        # constant head in layer 1 (steady state, Dor's version): cells with a value in constant_head (nan: none)
        if constant_head is not None:
            cells = self.basin & ~np.isnan(constant_head)
            flopy.mf6.ModflowGwfchd(gwf, maxbound=int(cells.sum()), print_input=False, print_flows=False,
                                    save_flows=False, stress_period_data=mf6_list(
                                        'constant_head', cells, {'head': constant_head[cells]}, binary))

        sim.write_simulation()

    def pointer(self, *address):
        """BMI pointer of a MODFLOW variable (variable name, model / solution name, component)"""
        return self.mf6.get_value_ptr(self.mf6.get_var_address(*address))

    def load_bmi(self, setpump):
        """Load the MODFLOW library, initialize the model and get the pointers of the exchanged variables"""
        if platform.system() not in MF6_LIBRARY:
            raise ValueError(f'Platform {platform.system()} not recognized.')
        library_name = MF6_LIBRARY[platform.system()]

        # modflow requires the real path (no symlinks etc.); Error 310 if missing (data_modflow.py)
        library_path = mf6_library_path(self.dir_mf6dll, library_name)
        try:
            xmipy = importlib.import_module("xmipy")
            # xmipy >= 1.1 changes to working_directory for every call (default: folder at creation time)
            self.mf6 = xmipy.XmiWrapper(library_path, working_directory=self.working_directory)
        except Exception as e:
            raise CWATMError("Error 310: MODFLOW library cannot be loaded: " + library_path + "\n" + str(e) + "\n")

        # an old libmf6 (e.g. MODFLOW 6.2.2) has no get_value_ptr, which newer xmipy versions call
        missing = [name for name in MF6_FUNCTIONS if not hasattr(self.mf6.lib, name)]
        if missing:
            msg = "Error 311: MODFLOW library is too old for the installed xmipy: " + library_path + "\n"
            msg += "Missing functions: " + ", ".join(missing) + "\n"
            msg += "Use a current libmf6 (e.g. MODFLOW 6.8.1) in path_mf6dll\n"
            raise CWATMError(msg)

        with cd(self.working_directory):
            # simulation file and input files: Error 226 / 227 if missing (data_modflow.py)
            config_file = mf6_simulation_file('.')

            try:
                self.mf6.initialize(config_file)
            except Exception as e:
                raise CWATMError("Error 312: MODFLOW initialize failed\n" + str(e) + "\n" + mf6_error_text('.'))
            if self.verbose:
                print("MODFLOW model initialized")

        self.nstep = 0

        # newer libmf6 (tested 6.8.1): recharge is read from RECHARGE (flux in m per period, MODFLOW multiplies it
        # by the cell area) and wells from Q (m3 per period). BOUND is filled from them in every time step, so a
        # value written to BOUND is lost. Old libmf6 (e.g. 6.2.2): BOUND (m3 per period)
        input_names = set(self.mf6.get_input_var_names())
        if self.name + "/RCH_0/RECHARGE" in input_names:
            self.recharge = self.pointer("RECHARGE", self.name, "RCH_0")
            self.recharge_factor = 1.0
        else:
            self.recharge = self.pointer("BOUND", self.name, "RCH_0")[:, 0]
            self.recharge_factor = self.rowsize * self.colsize

        self.head = self.pointer("X", self.name)
        # initial head through the pointer (the files have strt = top) - before prepare_time_step, which copies it
        # to the old head of the storage term
        # MODFLOW order: layer 1 (active cells row by row), layer 2, ...; a 2D head is the head of layer 1 (nlay = 1)
        self.head[:] = np.asarray(self.head0, dtype=np.float64).reshape(
            (self.nlay,) + self.basin.shape)[:, self.basin].ravel()

        if setpump:
            if self.name + "/WEL_0/Q" in input_names:
                self.well_rate = self.pointer("Q", self.name, "WEL_0")
            else:
                self.well_rate = self.pointer("BOUND", self.name, "WEL_0")[:, 0]
            self.actualwell_rate = self.pointer("SIMVALS", self.name, "WEL_0")

        # drain flow of each active cell (m3 per MODFLOW period, < 0: out of the aquifer) - baseflow and capillary rise
        self.drainage = self.pointer("SIMVALS", self.name, "DRN_0")
        # drain elevation of each drain (m), changed by set_drainage (adjust_drainage_by_river): ELEV (libmf6 > 6.2,
        # tested 6.8.1), 1st column of BOUND (old libmf6)
        if self.name + "/DRN_0/ELEV" in input_names:
            self.drain_elevation = self.pointer("ELEV", self.name, "DRN_0")
        else:
            self.drain_elevation = self.pointer("BOUND", self.name, "DRN_0")[:, 0]

        # cell-to-cell flows (FLOWJA, m3 per MODFLOW period, > 0: into the cell) of each connection of the reduced
        # nodes (CSR: IA, JA, 1-based; node = active cell, numbered layer by layer as the head) - per-layer budget
        # (layer_flows): for each connection of a node except the diagonal: same layer, layer above, layer below
        self.flowja = self.pointer("FLOWJA", self.name)
        ia = np.asarray(self.pointer("IA", self.name, "CON"), dtype=np.int64) - 1
        ja = np.asarray(self.pointer("JA", self.name, "CON"), dtype=np.int64) - 1
        self.nnode = ia.size - 1
        node = np.repeat(np.arange(self.nnode), np.diff(ia))
        ncell = self.nnode // self.nlay
        layer, layer_other = node // ncell, ja // ncell
        self.flow_connections = []
        for kind in (layer_other == layer, layer_other < layer, layer_other > layer):
            index = np.nonzero(kind & (ja != node))[0]
            self.flow_connections.append((index, node[index]))

        self.max_iter = self.pointer("MXITER", "SLN_1")[0]
        self.converged = True
        self.mf6.prepare_time_step(self.mf6.get_time_step())

    def decompress(self, a):
        """
        Values of the active cells -> map (nrow, ncol) with nan outside the basin; values of the active cells of
        all layers (e.g. head with nlay > 1) -> maps (nlay, nrow, ncol)
        """
        nlay = a.size // max(int(np.count_nonzero(self.basin)), 1)
        if nlay <= 1:
            o = np.full(self.basin.shape, np.nan, dtype=a.dtype)
            o[self.basin] = a
            return o
        o = np.full((nlay,) + self.basin.shape, np.nan, dtype=a.dtype)
        o[:, self.basin] = np.reshape(a, (nlay, -1))
        return o

    def layer_flows(self):
        """
        Flows into each active cell of all layers in the last time step (m3 per MODFLOW period, > 0: into the cell),
        array (3, nlay * active cells): from the other cells of the same layer (lateral), from the layer above,
        from the layer below
        """
        return np.stack([np.bincount(node, weights=self.flowja[index], minlength=self.nnode)
                         for index, node in self.flow_connections])

    def set_recharge(self, recharge):
        """Set recharge, value in m per MODFLOW period (RECHARGE: flux, BOUND of old libmf6: m3)"""
        self.recharge[:] = recharge[self.basin] * self.recharge_factor

    def set_groundwater_abstraction(self, groundwater_abstraction):
        """Set well rate, value in m3 per MODFLOW period (< 0 for pumping)"""
        self.well_rate[:] = groundwater_abstraction[self.wellsloc]

    def set_drainage(self, drain_elevation):
        """Set the elevation (m) of the drains (active cells of layer 1, map nrow x ncol) for the next step"""
        self.drain_elevation[:] = drain_elevation[self.basin]

    def step(self):
        """
        Solve one MODFLOW time step. MODFLOW has only one stress period, which is solved again in each step
        (as in GEB): MODFLOW uses the last solution as old head of the storage term, its time is not advanced.
        Bit-identical to one stress period per step (tested Bhima, Burgenland). No finalize_time_step: MODFLOW
        writes no output per time step (CWatM gets everything through the BMI pointers).
        self.converged: False if the outer iterations reached MXITER without convergence (transient.py warns)
        """
        t0 = time()
        self.converged = True
        for solution_id in range(1, self.mf6.get_subcomponent_count() + 1):
            self.mf6.prepare_solve(solution_id)
            # convergence loop
            for _ in range(self.max_iter):
                if self.mf6.solve(solution_id):
                    break
            else:
                self.converged = False
            self.mf6.finalize_solve(solution_id)

        self.nstep += 1
        if self.verbose:
            print(f'MODFLOW timestep {self.nstep} ' + ('converged' if self.converged else 'did NOT converge') +
                  f' in {round(time() - t0, 2)} seconds')

    def finalize(self):
        self.mf6.finalize()
