"""
MODFLOW 6 through its library libmf6 (BMI with xmipy) for the CWatM coupling (transient.py)

The input files are written with flopy (one layer, one stress period which is solved again in each step) and
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


def mf6_input_files(working_directory, namefile='mfsim.nam'):
    """
    Return the input files listed in a MODFLOW 6 name file and in the model name files listed there

    In each block except OPTIONS a line "FTYPE6  file  ..." has the file name as 2nd entry.
    Files referenced inside package files (OPEN/CLOSE) are found with mf6_external_files.
    """
    files = []
    block = None
    with open(os.path.join(working_directory, namefile)) as f:
        for line in f:
            words = line.split()
            if not words or words[0][0] in '#!':
                continue
            if words[0].upper() == 'BEGIN':
                block = words[1].upper()
            elif words[0].upper() == 'END':
                block = None
            elif block not in (None, 'OPTIONS') and len(words) > 1 and words[0].upper().endswith('6'):
                fname = words[1].strip('\'"')
                files.append(fname)
                if block == 'MODELS' and os.path.isfile(os.path.join(working_directory, fname)):
                    files += mf6_input_files(working_directory, fname)
    return files


def mf6_external_files(working_directory, files):
    """
    Return the files referenced with OPEN/CLOSE in the package files (e.g. the binary files top.bin, wells.bin)

    Only package files smaller than 1 MB are read: flopy writes the reference to an external file into a small
    package file; a large package file has the data inside (text input)
    """
    external = []
    for fname in files:
        path = os.path.join(working_directory, fname)
        if not os.path.isfile(path) or os.path.getsize(path) > 1000000:
            continue
        with open(path, errors='replace') as f:
            for line in f:
                words = line.split()
                for i, word in enumerate(words[:-1]):
                    if word.upper() == 'OPEN/CLOSE':
                        external.append(words[i + 1].strip('\'"'))
    return external


def mf6_error_text(working_directory, nlines=30):
    """
    Return the ERROR REPORT in mfsim.lst (MODFLOW listing file) and the lines after it,
    and the names of the files where the cause of the MODFLOW error can be found
    """
    wd = os.path.realpath(working_directory)
    fname = os.path.join(wd, 'mfsim.lst')
    text = ""
    if os.path.isfile(fname):
        with open(fname, errors='replace') as f:
            lines = f.readlines()
        start = [i for i, line in enumerate(lines) if 'ERROR REPORT' in line]
        if start:
            # the first one: an ERROR REPORT can be followed by a UNIT ERROR REPORT
            text = "MODFLOW error message:\n" + "".join(lines[start[0]:start[0] + nlines]).rstrip() + "\n\n"
        text += "The cause of the MODFLOW error is in the MODFLOW listing file:\n" + fname + "\n"
        text += "(more information: the model listing file *.lst and mfsim.stdout in the same folder)\n"
    else:
        text += "No MODFLOW listing file mfsim.lst (MODFLOW stopped before writing it) - look at mfsim.stdout\n"
        text += "(if it exists) in: " + wd + "\n"
    return text


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
    (layer 1) with layer, row, column and the values {name: one value or an array with a value for each cell}.
    Binary file <name>.bin for period 1, or a list of rows (flopy writes it as text). For binary the data go to
    flopy as pandas DataFrame: a list of tuples is converted very slowly by flopy (Bhima: 3.5 s per package
    instead of ~1 s)
    """
    row, column = np.nonzero(cells)
    data = {name_value: np.full(row.shape, value, dtype=np.float64) for name_value, value in values.items()}
    if not binary:
        return [[0, r, c, *v] for r, c, *v in zip(row.tolist(), column.tolist(), *(d.tolist() for d in data.values()))]
    data = pd.DataFrame(dict({'layer': np.zeros(row.shape, np.int64), 'row': row.astype(np.int64),
                              'column': column.astype(np.int64)}, **data))
    return {0: {'filename': name + '.bin', 'factor': 1.0, 'iprn': 1, 'binary': True, 'data': data}}


def mf6_input_hash(timestep, specific_storage, specific_yield, nlay, nrow, ncol, rowsize, colsize, top, bottom,
                   basin, topography, permeability, setpumpings=False, pumpingloc=None, complex_solver=False,
                   super_complex_solver=False, binary=True):
    """
    Hash over everything that goes into the MODFLOW input files, the flopy version and the source code of this
    file (a code change writes the files new). The initial head and the run length are not part of the files
    """
    flopy = importlib.import_module("flopy")
    h = hashlib.sha256()
    with open(__file__, 'rb') as f:
        h.update(f.read())
    h.update(flopy.__version__.encode())
    for value in (timestep, specific_storage, specific_yield, nlay, nrow, ncol, rowsize, colsize, top, bottom,
                  basin, topography, permeability, setpumpings, pumpingloc, complex_solver, super_complex_solver,
                  binary):
        if value is None:
            # not as array: an object array would give a memory address (different in each run)
            h.update(b'None')
            continue
        a = np.ascontiguousarray(value)
        h.update(str(a.dtype).encode() + str(a.shape).encode() + a.tobytes())
    return h.hexdigest()


class ModFlowSimulation:
    """
    One MODFLOW 6 model (one layer) run through libmf6

    Arrays at ModFlow resolution (nrow, ncol), with a layer dimension (nlay, nrow, ncol) for specific_yield,
    bottom and permeability (m/day). basin: active cells. head: initial head. Pumping wells (setpumpings) in the
    cells of pumpingloc. load_from_disk: reuse the input files in <folder>/wd if no input changed (hash),
    binary: binary input files (else text). Solver: SIMPLE, or complex_solver / super_complex_solver.

    Attributes used by transient.py: head (active cells), drainage (drain flow, m3 per period), actualwell_rate
    (actual pumping, m3 per period), basin, decompress, set_recharge, set_groundwater_abstraction, step, finalize
    """

    def __init__(self, name, folder, path_mf6dll, timestep, specific_storage, specific_yield, nlay, nrow, ncol,
                 rowsize, colsize, top, bottom, basin, head, topography, permeability, load_from_disk=False,
                 setpumpings=False, pumpingloc=None, verbose=False, complex_solver=False,
                 super_complex_solver=False, binary=True):

        self.name = name.upper()  # MODFLOW requires the name to be uppercase
        self.dir_mf6dll = path_mf6dll
        self.nrow, self.ncol = nrow, ncol
        self.rowsize, self.colsize = rowsize, colsize
        self.basin = basin
        self.wellsloc = pumpingloc if setpumpings else None
        self.working_directory = os.path.join(folder, 'wd')
        os.makedirs(self.working_directory, exist_ok=True)
        self.verbose = verbose
        # the initial head is not in the files (set through the BMI pointer in load_bmi)
        self.head0 = head

        # the MODFLOW input files are written new only if an input changed (hash in wd/input_hash);
        # load_from_disk = False: always write new
        hash_file = os.path.join(self.working_directory, 'input_hash')
        input_hash = mf6_input_hash(timestep, specific_storage, specific_yield, nlay, nrow, ncol, rowsize, colsize,
                                    top, bottom, basin, topography, permeability, setpumpings, pumpingloc,
                                    complex_solver, super_complex_solver, binary)
        reuse = False
        if load_from_disk and os.path.isfile(hash_file):
            with open(hash_file) as f:
                reuse = f.read().strip() == input_hash

        if reuse:
            if self.verbose:
                print("MODFLOW input files reused (inputs unchanged)")
        else:
            if os.path.isfile(hash_file):
                os.remove(hash_file)
            self.write_input(timestep, specific_storage, specific_yield, nlay, top, bottom, topography, permeability,
                             setpumpings, complex_solver, super_complex_solver, binary)
            with open(hash_file, 'w') as f:
                f.write(input_hash)

        self.load_bmi(setpumpings)

    def write_input(self, timestep, specific_storage, specific_yield, nlay, top, bottom, topography, permeability,
                    setpumpings, complex_solver, super_complex_solver, binary):
        """Write the MODFLOW input files with flopy (the packages are registered in the simulation)"""
        flopy = importlib.import_module("flopy")
        if self.verbose:
            print("Creating MODFLOW model")
        # MODFLOW runs through the library (libmf6), not mf6.exe; no memory tables in mfsim.lst
        sim = flopy.mf6.MFSimulation(sim_name=self.name, version='mf6', sim_ws=self.working_directory)

        # one stress period, solved again in each step (see step): the files do not depend on the run length
        flopy.mf6.ModflowTdis(sim, nper=1, perioddata=[(1.0, 1, 1)])

        # iterative model solution. If the model fails with xmipy.errors.XMIError: MODFLOW 6 BMI, exception in:
        # finalize_solve () - use a smaller modflow_timestep, or the complex solver
        if complex_solver:
            ims = dict(complexity='COMPLEX')
        elif super_complex_solver:
            ims = dict(complexity='COMPLEX', linear_acceleration='BICGSTAB', under_relaxation='SIMPLE',
                       under_relaxation_gamma=0.1, backtracking_number=5, backtracking_tolerance=10 ** 5,
                       backtracking_reduction_factor=0.3, backtracking_residual_limit=150)
        else:
            # rclose: MODFLOW default of complexity SIMPLE - the former L2NORM_RCLOSE 0.1*86400*timestep*cells
            # (Bhima 1.6e9) had no effect, the convergence is controlled by the head change (Bhima bit-identical)
            # ims = dict(complexity='SIMPLE', linear_acceleration='BICGSTAB',
            #            rcloserecord=[0.1 * 24 * 3600 * timestep * np.nansum(basin), 'L2NORM_RCLOSE'])
            ims = dict(complexity='SIMPLE', linear_acceleration='BICGSTAB')
        if self.verbose:
            print('MODFLOW solver complexity', ims['complexity'])
        flopy.mf6.ModflowIms(sim, print_option=None, **ims)

        # groundwater flow model (newtonoptions='under_relaxation' can help if there is no convergence)
        gwf = flopy.mf6.ModflowGwf(sim, modelname=self.name, newtonoptions='under_relaxation', print_input=False,
                                   print_flows=False)

        # input files: binary *.bin (binary = True: exact values, faster to write) or text
        # (storage STO stays text: flopy 3.10 cannot write sy as binary file - "modeltime" error)
        shape = (nlay, self.nrow, self.ncol)
        flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=self.nrow, ncol=self.ncol, delr=self.rowsize,
                                delc=self.colsize, top=mf6_array('top', top, binary, shape[1:]),
                                botm=mf6_array('botm', bottom, binary, shape),
                                idomain=mf6_array('idomain', self.basin, binary, shape, np.int32), nogrb=True)

        # strt = top of the aquifer, so the files do not depend on the initial head; the real initial head is
        # set through the BMI pointer in load_bmi (tested: bit-identical to strt = head)
        flopy.mf6.ModflowGwfic(gwf, strt=mf6_array('strt', top, binary, shape))
        flopy.mf6.ModflowGwfnpf(gwf, save_flows=True, icelltype=1,
                                k=mf6_array('k', mf6_constant(permeability * timestep), binary, shape))

        # output control only to stop MODFLOW printing all heads into TRANSIENT.lst (without OC, or with an empty
        # OC, MODFLOW prints the heads of the last time step of each period: Bhima 198 MB, +7 s). CWatM gets the
        # head through the BMI pointer. ('HEAD', 'FREQUENCY', 10) is every 10th time step of a stress period -
        # with 1 time step per period never, so TRANSIENT.hds stays empty
        flopy.mf6.ModflowGwfoc(gwf, head_filerecord=f'{self.name}.hds', saverecord=[('HEAD', 'FREQUENCY', 10)])

        flopy.mf6.ModflowGwfsto(gwf, save_flows=False, iconvert=1, ss=mf6_constant(specific_storage),
                                sy=mf6_constant(specific_yield), steady_state=False, transient=True)

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

        # drains in each active cell: elevation = top of the aquifer, conductance = permeability * cell area *
        # timestep (baseflow and capillary rise)
        conductance = permeability[0, self.basin] * self.rowsize * self.colsize * timestep
        flopy.mf6.ModflowGwfdrn(gwf, maxbound=self.basin.sum(), print_input=False, print_flows=False,
                                save_flows=False, stress_period_data=mf6_list(
                                    'drainage', self.basin, {'elev': topography[self.basin], 'cond': conductance},
                                    binary))

        sim.write_simulation()

    def pointer(self, *address):
        """BMI pointer of a MODFLOW variable (variable name, model / solution name, component)"""
        return self.mf6.get_value_ptr(self.mf6.get_var_address(*address))

    def load_bmi(self, setpump):
        """Load the MODFLOW library, initialize the model and get the pointers of the exchanged variables"""
        if platform.system() not in MF6_LIBRARY:
            raise ValueError(f'Platform {platform.system()} not recognized.')
        library_name = MF6_LIBRARY[platform.system()]

        # modflow requires the real path (no symlinks etc.)
        library_path = os.path.realpath(os.path.join(self.dir_mf6dll, library_name))
        if not os.path.isfile(library_path):
            msg = "Error 310: MODFLOW library " + library_name + " not found\n"
            raise CWATMFileError(library_path, msg=msg, sname="path_mf6dll")
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
            # modflow requires the real path (no symlinks etc.)
            config_file = os.path.realpath('mfsim.nam')
            if not os.path.exists(config_file):
                msg = "Error 226: MODFLOW simulation file not found - delete input_hash in this folder or set\n"
                msg += "load_modflow_from_disk = False, then the MODFLOW input files are written new\n"
                raise CWATMFileError(config_file, msg=msg, sname="load_modflow_from_disk")

            # a missing input file stops MODFLOW with a Fortran STOP, which also ends Python (exit code 2)
            input_files = mf6_input_files('.')
            missing = [f for f in input_files + mf6_external_files('.', input_files) if not os.path.isfile(f)]
            if missing:
                msg = "Error 227: MODFLOW input files listed in the name files are missing in:\n"
                msg += os.path.realpath('.') + "\n" + "\n".join(missing) + "\n"
                msg += "Delete input_hash in this folder or set load_modflow_from_disk = False to write them new\n"
                raise CWATMError(msg)

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
        self.head[:] = np.asarray(self.head0, dtype=np.float64)[self.basin]

        if setpump:
            if self.name + "/WEL_0/Q" in input_names:
                self.well_rate = self.pointer("Q", self.name, "WEL_0")
            else:
                self.well_rate = self.pointer("BOUND", self.name, "WEL_0")[:, 0]
            self.actualwell_rate = self.pointer("SIMVALS", self.name, "WEL_0")

        # drain flow of each active cell (m3 per MODFLOW period, < 0: out of the aquifer) - baseflow and capillary rise
        self.drainage = self.pointer("SIMVALS", self.name, "DRN_0")

        self.max_iter = self.pointer("MXITER", "SLN_1")[0]
        self.mf6.prepare_time_step(self.mf6.get_time_step())

    def decompress(self, a):
        """Values of the active cells -> map (nrow, ncol) with nan outside the basin"""
        o = np.full(self.basin.shape, np.nan, dtype=a.dtype)
        o[self.basin] = a
        return o

    def set_recharge(self, recharge):
        """Set recharge, value in m per MODFLOW period (RECHARGE: flux, BOUND of old libmf6: m3)"""
        self.recharge[:] = recharge[self.basin] * self.recharge_factor

    def set_groundwater_abstraction(self, groundwater_abstraction):
        """Set well rate, value in m3 per MODFLOW period (< 0 for pumping)"""
        self.well_rate[:] = groundwater_abstraction[self.wellsloc]

    def step(self):
        """
        Solve one MODFLOW time step. MODFLOW has only one stress period, which is solved again in each step
        (as in GEB): MODFLOW uses the last solution as old head of the storage term, its time is not advanced.
        Bit-identical to one stress period per step (tested Bhima, Burgenland). No finalize_time_step: MODFLOW
        writes no output per time step (CWatM gets everything through the BMI pointers)
        """
        t0 = time()
        for solution_id in range(1, self.mf6.get_subcomponent_count() + 1):
            self.mf6.prepare_solve(solution_id)
            # convergence loop
            for _ in range(self.max_iter):
                if self.mf6.solve(solution_id):
                    break
            self.mf6.finalize_solve(solution_id)

        self.nstep += 1
        if self.verbose:
            print(f'MODFLOW timestep {self.nstep} converged in {round(time() - t0, 2)} seconds')

    def finalize(self):
        self.mf6.finalize()
