from time import time
from contextlib import contextmanager
import os

import numpy as np

import importlib
# dynamically installed:
#from xmipy import XmiWrapper
#import flopy
import platform

@contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


class ModFlowSimulation:
    def __init__(
        self,
        name,
        folder,
        path_mf6dll,
        ndays,
        timestep,
        specific_storage,
        specific_yield,
        nlay,
        nrow,
        ncol,
        rowsize,
        colsize,
        top,
        bottom,
        basin,
        head,
        topography,
        permeability,
        load_from_disk=False,
        setpumpings=False,
        pumpingloc=None,
        verbose=False,
        complex_solver = False
    ):

        flopy = importlib.import_module("flopy", package=None)

        self.name = name.upper()  # MODFLOW requires the name to be uppercase
        self.folder = folder
        self.dir_mf6dll = path_mf6dll
        self.nrow = nrow
        self.ncol = ncol
        self.rowsize = rowsize
        self.colsize = colsize
        self.basin = basin
        if setpumpings == True:
            self.wellsloc = pumpingloc
        self.n_active_cells = self.basin.sum()
        self.working_directory = os.path.join(folder, 'wd')
        if not os.path.exists(self.working_directory):
            os.makedirs(self.working_directory)
        self.verbose = verbose

        if not load_from_disk:
            if self.verbose:
                print("Creating MODFLOW model")
            sim = flopy.mf6.MFSimulation(
                sim_name=self.name,
                version='mf6',
                exe_name=os.path.join(folder, 'mf6'),
                sim_ws=self.working_directory,
                memory_print_option='all'
            )
            
            # create tdis package
            tdis = flopy.mf6.ModflowTdis(sim, nper=ndays, perioddata=[(1.0, 1, 1)] * ndays)

            # create iterative model solution and register the gwf model with it If the model fails with the
            # following error: xmipy.errors.XMIError: MODFLOW 6 BMI, exception in: finalize_solve () Then one can
            # reduce the modflow timestep, or use the following ims lines with complexity = 'COMPLEX'

            if complex_solver:
                if self.verbose:
                    print('using compex modflow solver')
                ims = flopy.mf6.ModflowIms(sim, print_option=None, complexity='COMPLEX')
            else:
                ims = flopy.mf6.ModflowIms(sim, print_option=None, complexity='SIMPLE', linear_acceleration='BICGSTAB',
                                           rcloserecord=[0.1 * 24 * 3600 * timestep * np.nansum(basin),
                                                         'L2NORM_RCLOSE'])


            # create gwf model
            # MODIF LUCA
            gwf = flopy.mf6.ModflowGwf(sim, modelname=self.name, newtonoptions='under_relaxation', print_input=False, print_flows=False)  # newtonoptions='under_relaxation' can be tried if there is no convergence

            discretization = flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=self.nrow, ncol=self.ncol,
                delr=self.rowsize, delc=self.colsize, top=top,
                botm=bottom, idomain=self.basin, nogrb=True)

            initial_conditions = flopy.mf6.ModflowGwfic(gwf, strt=head)
            node_property_flow = flopy.mf6.ModflowGwfnpf(gwf, save_flows=True, icelltype=1, k=permeability*timestep)

            # MODIF LUCA
            output_control = flopy.mf6.ModflowGwfoc(gwf, head_filerecord=f'{self.name}.hds',
                                                    saverecord=[('HEAD', 'FREQUENCY', 10)])
            #output_control = flopy.mf6.ModflowGwfoc(
            #    gwf,
            #    head_filerecord=f'{self.name}.hds',
            #    headprintrecord=[
            #        ('COLUMNS', 10, 'WIDTH', 15,
            #            'DIGITS', 6, 'GENERAL')],
            #    saverecord=[('HEAD', 'ALL')],
            #    printrecord=[('HEAD', 'ALL'),
            #                    ('BUDGET', 'ALL')]
            #)

            storage = flopy.mf6.ModflowGwfsto(gwf,
                save_flows=False,
                iconvert=1,
                ss=specific_storage,  # specific storage
                sy=specific_yield,  # specific yield
                steady_state=False,
                transient=True,
            )

            recharge = np.zeros((self.basin.sum(), 4), dtype=np.int32)
            recharge_locations = np.where(self.basin == True)  # only set wells where basin is True
            # 0: layer, 1: y-idx, 2: x-idx, 3: rate
            recharge[:,0] = 0
            recharge[:, 1] = recharge_locations[0]
            recharge[:, 2] = recharge_locations[1]
            #recharge = np.zeros((self.basin.sum(), 2), dtype=np.int32)
            #recharge[0, 0] =
            recharge = recharge.tolist()

            # Recharge is > 0, and already given in m/timestep per ModFlow cell
            recharge = flopy.mf6.ModflowGwfrch(gwf, fixed_cell=False,
                              print_input=False, print_flows=False,
                              save_flows=False, boundnames=None,
                              maxbound=self.basin.sum(), stress_period_data=recharge)

            if setpumpings == True:
                wells = np.zeros((self.wellsloc.sum(), 4), dtype=np.int32)
                well_locations = np.where(self.wellsloc == True)  # only set wells where basin is True
                # 0: layer, 1: y-idx, 2: x-idx, 3: rate
                wells[:, 1] = well_locations[0]
                wells[:, 2] = well_locations[1]
                wells = wells.tolist()

                # Pumping is < 0 for abstraction, and is already given here in m3/timestep per ModFlow cell
                wells = flopy.mf6.ModflowGwfwel(gwf, print_input=False, print_flows=False, save_flows=False,
                                            maxbound=self.basin.sum(), stress_period_data=wells,
                                            boundnames=False, auto_flow_reduce=0.1)

            # MODIF LUCA
            drainage = np.zeros((self.basin.sum(), 5))  # Only i,j,k indices should be integer
            drainage_locations = np.where(self.basin == True)  # only set wells where basin is True
            # 0: layer, 1: y-idx, 2: x-idx, 3: drainage altitude, 4: permeability
            drainage[:, 1] = drainage_locations[0]
            drainage[:, 2] = drainage_locations[1]
            drainage[:, 3] = topography[drainage_locations]  # This one should not be an integer
            drainage[:, 4] = permeability[0, self.basin == True] * self.rowsize * self.colsize * timestep
            drainage = drainage.tolist()
            drainage = [[int(i), int(j), int(k) ,l, m] for i, j, k, l, m in drainage]  # MODIF LUCA

            drainage = flopy.mf6.ModflowGwfdrn(gwf, maxbound=self.basin.sum(), stress_period_data=drainage,
                                        print_input=False, print_flows=False, save_flows=False)
            
            sim.write_simulation()
            # sim.run_simulation()
        elif self.verbose:
            print("Loading MODFLOW model from disk")
        
        self.load_bmi(setpumpings)

    def bmi_return(self, success, model_ws):
        """
        parse libmf6.so and libmf6.dll stdout file
        """
        fpth = os.path.join(model_ws, 'mfsim.stdout')
        return success, open(fpth).readlines()

    def load_bmi(self, setpump):
        """Load the Basic Model Interface"""
        success = False
                
        if platform.system() == 'Windows':
            library_name = 'libmf6.dll'
        elif platform.system() == 'Linux':
            library_name = 'libmf6.so'
        else:
            raise ValueError(f'Platform {platform.system()} not recognized.')

        # modflow requires the real path (no symlinks etc.)
        library_path = os.path.realpath(os.path.join(self.dir_mf6dll, library_name))
        try:
            xmipy = importlib.import_module("xmipy")
            self.mf6 = xmipy.XmiWrapper(library_path)

        except Exception as e:
            print("Failed to load " + library_path)
            print("with message: " + str(e))
            return self.bmi_return(success, self.working_directory)

        with cd(self.working_directory):

            # modflow requires the real path (no symlinks etc.)
            config_file = os.path.realpath('mfsim.nam')
            if not os.path.exists(config_file):
                raise FileNotFoundError(f"Config file {config_file} not found on disk. Did you create the model first (load_from_disk = False)?")

            # initialize the model
            try:
                self.mf6.initialize(config_file)
            except:
                return self.bmi_return(success, self.working_directory)

            if self.verbose:
                print("MODFLOW model initialized")
        
        self.end_time = self.mf6.get_end_time()

        recharge_tag = self.mf6.get_var_address("BOUND", self.name, "RCH_0")
        # there seems to be a bug in xmipy where the size of the pointer to RCHA is
        # is the size of the entire modflow area, including basined cells. Only the first
        # part of the array is actually used, when a part of the area is basined. Since
        # numpy returns a view of the array when the array[]-syntax is used, we can simply
        # use the view of the first part of the array up to the number of active
        # (non-basined) cells
        self.recharge = self.mf6.get_value_ptr(recharge_tag)[:, 0]

        # print(self.mf6.get_output_var_names())
        
        head_tag = self.mf6.get_var_address("X", self.name)
        self.head = self.mf6.get_value_ptr(head_tag)

        if setpump == True:
            well_tag = self.mf6.get_var_address("BOUND", self.name, "WEL_0")
            self.well_rate = self.mf6.get_value_ptr(well_tag)[:, 0]
            actualwell_tag = self.mf6.get_var_address("SIMVALS", self.name, "WEL_0")
            self.actualwell_rate = self.mf6.get_value_ptr(actualwell_tag)

        drainage_tag = self.mf6.get_var_address("BOUND", self.name, "DRN_0")
        self.drainage = self.mf6.get_value_ptr(drainage_tag)[:, 0]

        mxit_tag = self.mf6.get_var_address("MXITER", "SLN_1")
        self.max_iter = self.mf6.get_value_ptr(mxit_tag)[0]

        self.prepare_time_step()

    def compress(self, a):
        return np.compress(self.basin, a)

    def decompress(self, a):
        o = np.full(self.basin.shape, np.nan, dtype=a.dtype)
        o[self.basin] = a
        return o

    def prepare_time_step(self):
        dt = self.mf6.get_time_step()
        self.mf6.prepare_time_step(dt)

    def set_recharge(self, recharge):
        """Set recharge, value in m/day"""
        recharge = recharge[self.basin == True]
        self.recharge[:] = recharge * (self.rowsize * self.colsize)
    
    def set_groundwater_abstraction(self, groundwater_abstraction):
        """Set well rate, value in m3/day"""
        well_rate = groundwater_abstraction[self.wellsloc == True]
        self.well_rate[:] = well_rate

    def get_drainage(self):
        return self.decompress(self.drainage / (self.rowsize * self.colsize))

    def step(self, plot=False):
        if self.mf6.get_current_time() > self.end_time:
            raise StopIteration("MODFLOW used all iteration steps. Consider increasing `ndays`")

        t0 = time()
        # loop over subcomponents
        n_solutions = self.mf6.get_subcomponent_count()
        for solution_id in range(1, n_solutions + 1):

            # convergence loop
            kiter = 0
            self.mf6.prepare_solve(solution_id)
            while kiter < self.max_iter:
                has_converged = self.mf6.solve(solution_id)
                kiter += 1

                if has_converged:
                    break

            self.mf6.finalize_solve(solution_id)

        self.mf6.finalize_time_step()

        if self.verbose:
            print(f'MODFLOW timestep {int(self.mf6.get_current_time())} converged in {round(time() - t0, 2)} seconds')
        
        # If next step exists, prepare timestep. Otherwise the data set through the bmi
        # will be overwritten when preparing the next timestep.
        if self.mf6.get_current_time() < self.end_time:
            self.prepare_time_step()

    def finalize(self):
        self.mf6.finalize()