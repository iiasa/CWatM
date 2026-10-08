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
        drain_elevation,
        basin,
        confined_only,
        head,
        topography,
        permeability,
        permeability_vertical,
        load_from_disk=False,
        setpumpings=False,
        pumpingloc=None,
        verbose=False,
        complex_solver=False
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
            """
            if complex_solver:
                if self.verbose:
                    print('using compex modflow solver')
                ims = flopy.mf6.ModflowIms(sim, print_option=None, complexity='COMPLEX')
            else:
                ims = flopy.mf6.ModflowIms(sim, print_option=None, complexity='SIMPLE', linear_acceleration='BICGSTAB',
                                           rcloserecord=[0.1 * 24 * 3600 * timestep * np.nansum(basin),
                                                         'L2NORM_RCLOSE'])
            """
            # create iterative model solution and register the gwf model with it
            #ims = flopy.mf6.ModflowIms(sim, print_option=None, complexity='SIMPLE', linear_acceleration='BICGSTAB')
            #ims = flopy.mf6.ModflowIms(sim, print_option=None, complexity='COMPLEX', linear_acceleration='BICGSTAB')
            
            # For Debuggin set print_option to 'ALL' or 'SUMMARY'; otherwise None
            '''
            ims = flopy.mf6.ModflowIms(sim, print_option='SUMMARY', complexity='COMPLEX', linear_acceleration='BICGSTAB',
                                       under_relaxation='SIMPLE', under_relaxation_gamma=0.1,
                                       backtracking_number=5, backtracking_tolerance=10 ** 5,
                                       backtracking_reduction_factor=0.3, backtracking_residual_limit=150)
            '''                        
            # change under_relaxation from SIMPLE to COOLEY - so it can handle abrupt wetting and drying cycles
            ims = flopy.mf6.ModflowIms(sim, print_option='SUMMARY', complexity='COMPLEX', linear_acceleration='BICGSTAB',
                                       under_relaxation='COOLEY', under_relaxation_gamma=0.3, 
                                       backtracking_number=10, backtracking_tolerance=1.5,
                                       backtracking_reduction_factor=0.5, backtracking_residual_limit=100)


            #ims = flopy.mf6.ModflowIms(sim, print_option=None, complexity='COMPLEX', linear_acceleration='BICGSTAB',
            #                           under_relaxation='SIMPLE', under_relaxation_gamma=0.2,
            #                           backtracking_number=10, backtracking_tolerance=10**4,
            #                           backtracking_reduction_factor=0.2, backtracking_residual_limit=100)
            # create gwf model
            # MODIF LUCA
            #gwf = flopy.mf6.ModflowGwf(sim, modelname=self.name, print_input=False, print_flows=False)
            #gwf = flopy.mf6.ModflowGwf(sim, modelname=self.name, newtonoptions='newton under_relaxation', print_input=False, print_flows=False)
            gwf = flopy.mf6.ModflowGwf(sim, modelname=self.name, newtonoptions='UNDER_RELAXATION', print_input=False, print_flows=False)
            # NEWTON is implied in newton options

            discretization = flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=self.nrow, ncol=self.ncol,
                delr=self.rowsize, delc=self.colsize, top=top,
                botm=bottom, idomain=self.basin, nogrb=True)

            initial_conditions = flopy.mf6.ModflowGwfic(gwf, strt=head)
            
            # if vertical is assigned -> use K33 
            #node_property_flow = flopy.mf6.ModflowGwfnpf(gwf, save_flows=True, icelltype=confined_only, k=permeability*timestep, k33=permeability_vertical*timestep)
            node_property_flow = flopy.mf6.ModflowGwfnpf(gwf, save_flows=True, icelltype=confined_only,
                                                         k=permeability * timestep, k33=permeability_vertical*timestep) #,
                                                         #wetdry=0)
            # MODIF LUCA
            output_control = flopy.mf6.ModflowGwfoc(gwf, head_filerecord=f'{self.name}.hds',
            #budget_filerecord = f'{self.name}.bud',
            saverecord=[('HEAD', 'FREQUENCY', 10)])#, ('BUDGET', 'ALL')])
     
            storage = flopy.mf6.ModflowGwfsto(gwf,
                save_flows=False,
                iconvert=confined_only,
                ss=specific_storage,  # specific storage
                sy=specific_yield,  # specific yield
                steady_state=False,
                transient=True,
            )

            # MODIFIED DOR FRIDMAN - Currently only allowed to have one mask for all layers
            #basin_map = np.where(self.basin[0], self.basin[0], False)
            basin_map = self.basin.copy()
            #basin_map = np.where(self.basin[0], self.basin[0], np.where(self.basin[1], self.basin[1], False))
            #print(basin_map.shape)
            recharge = np.zeros((basin_map.sum(), 4), dtype=np.int32)
            recharge_locations = np.where(basin_map == True)  # only set wells where basin is True
            
            # 0: layer, 1: y-idx, 2: x-idx, 3: rate
            recharge[:, 0] = recharge_locations[0]
            recharge[:, 1] = recharge_locations[1]
            recharge[:, 2] = recharge_locations[2]

            recharge = recharge.tolist()

            recharge = flopy.mf6.ModflowGwfrch(gwf, fixed_cell=False,
                              print_input=False, print_flows=False,
                              save_flows=False, boundnames=None,
                              #maxbound=self.basin[0].sum(), stress_period_data=recharge)
                              maxbound = self.basin.sum(), stress_period_data = recharge)
        
            if setpumpings == True:
                # MODIFIED DOR FRIDMAN
                wells = np.zeros((self.wellsloc.sum(), 4), dtype=np.int32)
                well_locations = np.where(self.wellsloc == True)  # only set wells where basin is True
                # 0: layer, 1: y-idx, 2: x-idx, 3: rate
                wells[:, 0] = well_locations[0]
                wells[:, 1] = well_locations[1]                
                wells[:, 2] = well_locations[2]
                wells = wells.tolist()

                wells = flopy.mf6.ModflowGwfwel(gwf, print_input=False, print_flows=False, save_flows=False,
                                            maxbound=self.basin.sum(), stress_period_data=wells,
                                            boundnames=False, auto_flow_reduce=0.1)
            
            # MODIFIED DOR FRIDMAN
            #topography2 = np.array([topography] * nlay)
            topography2 = drain_elevation.copy()
            permeability2 = permeability.copy()

            drainage = np.zeros((self.basin[0].sum(), 5))  # Only i,j,k indices should be integer
            #print(drainage)
            drainage_locations = np.where(self.basin[0] == True)  # only set wells where basin is True
            # 0: layer, 1: y-idx, 2: x-idx, 3: drainage altitude, 4: permeability
            drainage[:, 0] = 0
            drainage[:, 1] = drainage_locations[0]
            drainage[:, 2] = drainage_locations[1]
            #print(drainage)
            #print(topography2[0][drainage_locations])
            #drainage[:, 3] = topography2[0][drainage_locations]  # This one should not be an integer
            drainage[:, 3] = topography2[drainage_locations]  # This one should not be an integer
            drainage[:, 4] = permeability2[0][
                                 self.basin[0] == True] * self.rowsize * self.colsize # removed ref to layer 0; permeability[0, self.basin == True]...
            drainage = drainage.tolist()
            drainage = [[int(i), int(j), int(k), l, m] for i, j, k, l, m in drainage]  # MODIF LUCA

            #print(len(drainage))

            self.drn = flopy.mf6.ModflowGwfdrn(gwf, maxbound=self.basin[0].sum(), stress_period_data=drainage,
                                        print_input=False, print_flows=False, save_flows=False)
            
            sim.write_simulation()
            ii = 1
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
        head_tag = self.mf6.get_var_address("X", self.name)
        self.head = self.mf6.get_value_ptr(head_tag)
        if setpump == True:
            well_tag = self.mf6.get_var_address("BOUND", self.name, "WEL_0")
            self.well_rate = self.mf6.get_value_ptr(well_tag)[:, 0]
            actualwell_tag = self.mf6.get_var_address("SIMVALS", self.name, "WEL_0")
            self.actualwell_rate = self.mf6.get_value_ptr(actualwell_tag)


        #drainage_tag = self.mf6.get_var_address("BOUND", self.name, "DRN_0")
        #self.drainage = self.mf6.get_value_ptr(drainage_tag)[:, 0]
        #drainage_simvals_tag = self.mf6.get_var_address("SIMVALS", self.name, "DRN_0")
        #self.live_drainage = -self.mf6.get_value_ptr(drainage_simvals_tag)
     

        mxit_tag = self.mf6.get_var_address("MXITER", "SLN_1")
        self.max_iter = self.mf6.get_value_ptr(mxit_tag)[0]

        self.prepare_time_step()

    def compress(self, a):
        return np.compress(self.basin, a)

    def decompress(self, a, top_layer = False):

        bas_ = self.basin.copy()
        if top_layer:
            bas_ = self.basin[0].copy()
        
        o = np.full(bas_.shape, np.nan, dtype=a.dtype)
        o[bas_ ] = a
        return o

    def prepare_time_step(self):
        dt = self.mf6.get_time_step()
        self.mf6.prepare_time_step(dt)

    def set_recharge(self, recharge):
        """Set recharge, value in m3/day - associated with list input to the recharge package"""
        # MODIFIED DOR FRIDMAN - ASSUMES ALL LAYER MASKS ARE THE SAME
        basin_map =  self.basin.copy()#[0]
        recharge = recharge[basin_map == True]
        self.recharge[:] = recharge * (self.rowsize * self.colsize)
    
    def set_groundwater_abstraction(self, groundwater_abstraction):
        """Set well rate, value in m3/day"""
        well_rate = groundwater_abstraction[self.wellsloc == True]
        self.well_rate[:] = well_rate

    def set_drainage(self, dynamicDrainElevation):
        """Update  the drain elevation (topography)"""
        # 1. Extract values at active basin locations
        drainage_locations = np.where(self.basin[0] == True)
        new_elevs = dynamicDrainElevation[drainage_locations]
    
        # 2. Get existing records for stress period 0: [(lay, row, col, stage, cond), ...]
        current_data = self.drn.stress_period_data.get_data()[0]
        # 3. Modify only the elevation element (index 3) in each record
        updated_data = [
            (rec[0], float(new_e), rec[2])
            for rec, new_e in zip(current_data, new_elevs)
        ]
        
        # 4. Push updated data back to the FloPy package
        self.drn.stress_period_data.set_data(updated_data, key=0)
        
    '''
    def get_drainage(self):
        #return self.decompress(self.drainage / (self.rowsize * self.colsize), top_layer = True)
        return self.decompress(self.live_drainage / (self.rowsize * self.colsize), top_layer = True)
    
    # fetching drainage from memory is not stable.
    '''
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
        
        # READ FLOWS
        #self.groundwater_outflow  = self.get_drainage().copy()
        
        if self.verbose:
            print(f'MODFLOW timestep {int(self.mf6.get_current_time())} converged in {round(time() - t0, 2)} seconds')

        # If next step exists, prepare timestep. Otherwise the data set through the bmi
        # will be overwritten when preparing the next timestep.
        if self.mf6.get_current_time() < self.end_time:
            self.prepare_time_step()

    def finalize(self):
        self.mf6.finalize()