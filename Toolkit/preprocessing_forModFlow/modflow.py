from time import time
from contextlib import contextmanager
import matplotlib.pyplot as plt
import os
import rasterio
import numpy as np
from xmipy import XmiWrapper
import flopy
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
        ndays,
        specific_storage,
        specific_yield,
        nlay,
        nrow,
        ncol,
        rowsize,
        colsize,
        top,
        bottom,
        modflow_basin,
        head,
        topography,
        hk,
        permeability,
        load_from_disk=False,
        verbose=False
    ):
        self.name = name.upper()  # MODFLOW requires the name to be uppercase
        self.folder = folder
        self.nrow = nrow
        self.ncol = ncol
        self.rowsize = rowsize
        self.colsize = colsize
        self.modflow_basin = modflow_basin
        self.n_active_cells = self.modflow_basin.sum()
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
            tdis = flopy.mf6.ModflowTdis(sim, time_units='DAYS', nper=ndays, perioddata=[(1.0, 1, 1)] * ndays)

            # create iterative model solution and register the gwf model with it
            ims = flopy.mf6.ModflowIms(sim, print_option=None, complexity='SIMPLE', linear_acceleration='BICGSTAB')

            # create gwf model
            gwf = flopy.mf6.ModflowGwf(sim, modelname=self.name, newtonoptions='under_relaxation')

            discretization = flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=self.nrow, ncol=self.ncol,
                delr=self.rowsize, delc=self.colsize, top=top,
                botm=bottom, idomain=self.modflow_basin, nogrb=True)

            initial_conditions = flopy.mf6.ModflowGwfic(gwf, strt=head)
            node_property_flow = flopy.mf6.ModflowGwfnpf(gwf, save_flows=True, icelltype=1, k=hk)

            output_control = flopy.mf6.ModflowGwfoc(
                gwf, 
                head_filerecord=f'{self.name}.hds',
                headprintrecord=[
                    ('COLUMNS', 10, 'WIDTH', 15,
                        'DIGITS', 6, 'GENERAL')],
                saverecord=[('HEAD', 'ALL')],
                printrecord=[('HEAD', 'ALL'),
                                ('BUDGET', 'ALL')]
            )

            storage = flopy.mf6.ModflowGwfsto(gwf,
                save_flows=False,
                iconvert=1,
                ss=specific_storage,  # specific storage
                sy=specific_yield,  # specific yield
                steady_state=False,
                transient=True,
            )

            recharge = np.zeros((self.modflow_basin.sum(), 4), dtype=np.int32)
            recharge_locations = np.where(self.modflow_basin == True)  # only set wells where modflow_basin is True
            # 0: layer, 1: y-idx, 2: x-idx, 3: rate
            recharge[:, 1] = recharge_locations[0]
            recharge[:, 2] = recharge_locations[1]
            recharge = recharge.tolist()

            recharge = flopy.mf6.ModflowGwfrch(gwf, fixed_cell=False,
                              print_input=False, print_flows=False,
                              save_flows=False, boundnames=None,
                              maxbound=self.modflow_basin.sum(), stress_period_data=recharge)

            wells = np.zeros((self.modflow_basin.sum(), 4), dtype=np.int32)
            well_locations = np.where(self.modflow_basin == True)  # only set wells where modflow_basin is True
            # 0: layer, 1: y-idx, 2: x-idx, 3: rate
            wells[:, 1] = well_locations[0]
            wells[:, 2] = well_locations[1]
            wells = wells.tolist()

            wells = flopy.mf6.ModflowGwfwel(gwf, print_input=False, print_flows=False, save_flows=False,
                                        maxbound=self.modflow_basin.sum(), stress_period_data=wells,
                                        boundnames=False, auto_flow_reduce=0.1)

            drainage = np.zeros((self.modflow_basin.sum(), 5), dtype=np.int32)
            drainage_locations = np.where(self.modflow_basin == True)  # only set wells where modflow_basin is True
            # 0: layer, 1: y-idx, 2: x-idx, 3: drainage altitude, 4: permeability
            drainage[:, 1] = drainage_locations[0]
            drainage[:, 2] = drainage_locations[1]
            drainage[:, 3] = topography[drainage_locations]
            drainage[:, 4] = permeability * self.rowsize * self.colsize
            drainage = drainage.tolist()

            drainage = flopy.mf6.ModflowGwfdrn(gwf, maxbound=self.modflow_basin.sum(), stress_period_data=drainage,
                                        print_input=False, print_flows=False, save_flows=False)
            
            sim.write_simulation()
            # sim.run_simulation()
        elif self.verbose:
            print("Loading MODFLOW model from disk")
        
        self.load_bmi()

    def bmi_return(self, success, model_ws):
        """
        parse libmf6.so and libmf6.dll stdout file
        """
        fpth = os.path.join(model_ws, 'mfsim.stdout')
        return success, open(fpth).readlines()

    def load_bmi(self):
        """Load the Basic Model Interface"""
        success = False
        
        
        if platform.system() == 'Windows':
            libary_name = 'libmf6.dll'
        elif platform.system() == 'Linux':
            libary_name = 'libmf6.so'
        else:
            raise ValueError(f'Platform {platform.system()} not recognized.')

        # modflow requires the real path (no symlinks etc.)
        library_path = os.path.realpath(os.path.join(self.folder, libary_name))
        try:
            self.mf6 = XmiWrapper(library_path)
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
        # is the size of the entire modflow area, including modflow_basined cells. Only the first
        # part of the array is actually used, when a part of the area is modflow_basined. Since
        # numpy returns a view of the array when the array[]-syntax is used, we can simply
        # use the view of the first part of the array up to the number of active
        # (non-modflow_basined) cells
        self.recharge = self.mf6.get_value_ptr(recharge_tag)[:, 0]
        
        head_tag = self.mf6.get_var_address("X", self.name)
        self.head = self.mf6.get_value_ptr(head_tag)
        
        well_tag = self.mf6.get_var_address("BOUND", self.name, "WEL_0")
        self.well_rate = self.mf6.get_value_ptr(well_tag)[:, 0]

        mxit_tag = self.mf6.get_var_address("MXITER", "SLN_1")
        self.max_iter = self.mf6.get_value_ptr(mxit_tag)[0]

        self.prepare_time_step()

    def compress(self, a):
        return np.compress(self.modflow_basin, a)

    def decompress(self, a):
        o = np.empty(self.modflow_basin.shape, dtype=a.dtype)
        o[self.modflow_basin] = a
        return o

    def prepare_time_step(self):
        dt = self.mf6.get_time_step()
        self.mf6.prepare_time_step(dt)

    def set_recharge(self, recharge):
        """Set recharge, value in m/day"""
        if not np.isnan(recharge[self.modflow_basin == False]).all():
            raise ValueError("Values outside basin are non-nan values. This could lead to water 'disappearing'")            
        recharge = recharge[self.modflow_basin == True]
        self.recharge[:] = recharge * (self.rowsize * self.colsize)
    
    def set_well_rate(self, well_rate):
        """Set well rate, value in m/day"""
        if not np.isnan(well_rate[self.modflow_basin == False]).all():
            raise ValueError("Values outside basin are non-nan values. This could lead to water 'disappearing'")      
        well_rate = well_rate[self.modflow_basin == True]
        self.well_rate[:] = well_rate * (self.rowsize * self.colsize)

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

        if plot:
            _, (ax0, ax1, ax2) = plt.subplots(1, 3)
            
            # Recharge
            recharge = self.recharge / (self.rowsize * self.colsize)
            self.plot_compressed(recharge, ax=ax0)
            ax0.set_title('Recharge')

            # Head
            self.plot_compressed(self.head, ax=ax1)
            ax1.set_title('Head')

            # Pumping
            self.plot_compressed(self.well_rate / (self.rowsize * self.colsize), ax=ax2)
            ax2.set_title('Well rate')

            plt.show()
        
        # If next step exists, prepare timestep. Otherwise the data set through the bmi
        # will be overwritten when preparing the next timestep.
        if self.mf6.get_current_time() < self.end_time:
            self.prepare_time_step()

    def plot(self, a, ax=None):
        show = True if ax is None else False
        a = a.reshape(self.nrow, self.ncol)
        if a.dtype in ('float64', 'float32'):
            a[~self.modflow_basin] = np.nan
        
        if ax:
            ax.imshow(a)
        else:
            plt.imshow(a)
        if show:
            plt.show()

    def plot_compressed(self, a, ax=None):
        a = self.decompress(a)
        self.plot(a, ax=ax)

    def finalize(self):
        self.mf6.finalize()


def main():
    modflow_directory = 'DataDrive/CWatM/krishna/input/groundwater/modflow'
    input_directory = os.path.join(modflow_directory, '500m')
    
    NDAYS = 10
    NAME = 'transient'
    NLAY = 1
    SOILDEPTH = 2
    ACQUIFER_THICKNESS = 100
    PERMEABILITY = 1e-05
    # Coef to multiply transmissivity and storage coefficient
    # (because ModFlow convergence is better if aquifer's thicknes is big and permeability is small)
    COEFFICIENT = 1

    with rasterio.open(os.path.join(input_directory, 'modflow_basin.tif'), 'r') as src:
        modflow_basin = src.read(1).astype(np.bool)  # read in as 3-dimensional array (nlay, nrows, ncols).
        domain = {
            'rowsize': abs(src.profile['transform'].e),
            'colsize': abs(src.profile['transform'].a),
            # 'west': src.profile['transform'].c + src.profile['transform'].a * 0.5,
            # 'east': src.profile['transform'].c + (src.profile['width'] + 0.5) * src.profile['transform'].a,
            # 'north': src.profile['transform'].f + src.profile['transform'].e * 0.5,
            # 'south': src.profile['transform'].f + (src.profile['height'] + 0.5) * src.profile['transform'].e,
            'nrow': src.profile['height'],
            'ncol': src.profile['width'],
        }

    with rasterio.open(os.path.join(input_directory, 'elevation_modflow.tif'), 'r') as src:
        topography = src.read(1)

    layer_boundaries = np.empty((NLAY + 1, domain['nrow'], domain['ncol']))
    layer_boundaries[0] = topography - SOILDEPTH - 0.05
    layer_boundaries[1] = layer_boundaries[0] - ACQUIFER_THICKNESS

    mf = ModFlowSimulation(
        NAME,
        modflow_directory,
        ndays=NDAYS,
        specific_storage=0.1,
        specific_yield=0.,
        nlay=NLAY,
        nrow=domain['nrow'],
        ncol=domain['ncol'],
        rowsize=domain['rowsize'],
        colsize=domain['colsize'],
        top=layer_boundaries[0],
        bottom=layer_boundaries[1],
        modflow_basin=modflow_basin,
        head=layer_boundaries[0] - 2,
        topography=topography,
        hk=np.full((NLAY, domain['nrow'], domain['ncol']), 86400 * PERMEABILITY / COEFFICIENT),
        permeability=PERMEABILITY,
        load_from_disk=True,
        verbose=True
    )
    for _ in range(NDAYS):
        recharge = np.full((domain['nrow'], domain['ncol']), .01)
        recharge[~modflow_basin] = np.nan
        mf.set_recharge(recharge)
        well_rate = np.full((domain['nrow'], domain['ncol']), -.02)
        well_rate[~modflow_basin] = np.nan
        mf.set_well_rate(well_rate)
        mf.step(plot=False)
    
    mf.finalize()


if __name__ == "__main__":
    main()
