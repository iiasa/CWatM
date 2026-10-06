# Purpose: MODFLOW coupling module integrating external groundwater simulation with CWatM.
# Manages bidirectional data exchange between surface and groundwater models.
# Supports transient groundwater simulation with dynamic surface-groundwater interaction.
import numpy as np
import os

from cwatm.management_modules.data_handling import *
from cwatm.hydrological_modules.groundwater_modflow.grid import ModflowGrid
from cwatm.hydrological_modules.groundwater_modflow.modflow6 import ModFlowSimulation
from cwatm.hydrological_modules.groundwater_modflow.modflow6_process import ModFlowProcess
import functools


def setting_bool(name, default=False):
    """True/False key of the settings file, default if the key is missing"""
    return returnBool(name) if name in binding else default


def option_bool(name):
    """True/False key of the [OPTIONS] section, False if the key is missing"""
    return name in option and bool(checkOption(name))


class groundwater_modflow:
    """
    MODFLOW groundwater coupling module for CWatM.

    This class provides the interface between CWatM and MODFLOW 6 for
    coupled surface-groundwater modeling. It handles data conversion,
    model initialization, and dynamic groundwater calculations.

    Attributes
    ----------
    var : object
        Model variables container
    model : object
        CWatM model instance
    modflow : ModFlowSimulation
        MODFLOW 6 simulation instance
    grid : ModflowGrid
        ModFlow grid and the conversion of maps between CWatM and ModFlow (grid.py)










    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    modflow                              Flag          True if modflow_coupling = True in settings file                        bool 
    sum_gwRecharge                       Array         groundwater recharge                                                    m    
    gwdepth_observations                 Array         Input, gw_depth_observations, groundwater depth observations            m    
    gwdepth_adjuster                     Array         Groundwater depth adjuster                                              m    
    baseflow                             Array         simulated baseflow (= groundwater discharge to river)                   m    
    capillar                             Array         Flow from groundwater to the third CWATM soil layer. Used with MODFLOW  m    
    capriseindex                         Array         computing saturated fraction of each CWatM cells (where water table >=  --   
    soildepth12                          Array         Total thickness of layer 2 and 3                                        m    
    leakageriver_factor                  Array                                                                                 --   
    leakagelake_factor                   Array                                                                                 --   
    modflow_timestep                     Array         Chosen ModFlow model timestep (1day, 7days, 30days, etc.)               day  
    head                                 Array         Simulated ModFlow water level [masl]                                    m    
    gwdepth_adjusted                     Array         Adjusted depth to groundwater table                                     m    
    gwdepth                              Array         Depth to groundwater table                                              m    
    channel_ratio                        Array                                                                                 --   
    modflowtotalSoilThickness            Array         Array (nrows, ncol) used to compute water table depth in post-processi  m    
    load_init_water_table                Flag          defining the initial water table map (it can be a hydraulic head map p  --   
    GW_pumping                           Flag          Input, True if Groundwater_pumping=True                                 bool 
    use_complex_solver_for_modflow       Flag                                                                                  --   
    use_super_complex_solver_for_modflo  Flag                                                                                  --   
    availableGWStorageFraction           Array                                                                                 --   
    wells_index                          Array                                                                                 --   
    sumed_sum_gwRecharge                 Array         setting sumed up recharge again to 7 (or 14 or 30...), will be sumed u  --   
    modflow_compteur                     Number        Counts each day relatively to the chosen ModFlow timestep, allow to ru  day  
    modflow_watertable                   Array         water table will be also saved at modflow resolution (AI)               --   
    writeerror                           Flag                                                                                  --   
    modflowdiscrepancy                   Array         saving modflow discrepancy, it will be written a text file at the end   --   
    groundwater_storage_top_layer        Array         then, we got the initial groundwater storage map at ModFlow resolution  --   
    groundwater_storage_available        Array         Groundwater storage. Used with MODFLOW.                                 m    
    gwstorage_full                       Number        Groundwater storage at full capacity                                    m    
    permeability                         Array         permeability need to be translated into CWatM map to compute leakage f  --   
    modfPumpingM_actual                  Array         Actual groundwater pumping. Used with MODFLOW.                          m    
    gwdepth_difference_sim_obs           Array         Difference between simulated and observed groundwater table             m    
    modflow_head_adjusted                Array                                                                                 --   
    cellArea                             Array         Area of cell                                                            m2   
    modfPumpingM                         Array         modfPumpingM is initialized every modflow_timestep in groundwater_modf  --   
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize the groundwater-MODFLOW coupling module.

        Parameters
        ----------
        model : object
            CWatM model instance containing variables and configuration
        """
        self.var = model.var
        self.model = model


    def storage(self, head):
        """Groundwater storage in the aquifer (m water) at ModFlow resolution from the head"""
        top, bottom = self.layer_boundaries[0], self.layer_boundaries[1]
        return (np.where(head > top, top, head) - bottom) * self.porosity[0]

    def read_settings(self):
        """Settings of the MODFLOW coupling (defaults if a key is missing)"""
        self.verbose = setting_bool('verbose_GW')

        # MODFLOW in a child process: a MODFLOW error (Fortran STOP) does not end Python (Error 313)
        # modflow_subprocess = False: libmf6 in the CWatM process (e.g. for debugging)
        # modflow_timeout: longest time in seconds for one MODFLOW call (start or one time step), 0: no limit
        timeout = float(cbinding('modflow_timeout')) if 'modflow_timeout' in binding else 3600
        self.ModFlow = functools.partial(ModFlowProcess, timeout=timeout)
        if not setting_bool('modflow_subprocess', True):
            self.ModFlow = ModFlowSimulation
        # MODFLOW input files are reused if no input changed (hash), load_modflow_from_disk = False: always new
        self.load_from_disk = setting_bool('load_modflow_from_disk', True)
        # MODFLOW input files: binary (default) or text (modflow_text_input = True)
        self.binary = not setting_bool('modflow_text_input')

        # Define the size of the ModFlow time step - means that ModFlow is called each "modflow_timestep"
        self.var.modflow_timestep = int(loadmap('modflow_timestep'))
        if self.verbose:
            print('ModFlow is activated')
            print('ModFlow timestep is : ', self.var.modflow_timestep, ' days\n')

        self.directory_mf6dll = cbinding('path_mf6dll')
        if not os.path.isdir(self.directory_mf6dll):
            msg = "Error 222: Path to Modflow6 files does not exists "
            raise CWATMDirError(self.directory_mf6dll, msg, sname='path_mf6dll')
        self.nlay = int(loadmap('nlay'))
        # top, bottom, permeability, porosity and thickness are only set for one layer
        if self.nlay != 1:
            raise CWATMError("Error 146: nlay = " + str(self.nlay) + " - the MODFLOW coupling works only with one layer (nlay = 1)\n")

        # defining the initial water table map (it can be a hydraulic head map previously simulated)
        self.var.load_init_water_table = setting_bool('load_init_water_table')
        # test if ModFlow pumping is used as defined in settings file
        self.var.GW_pumping = setting_bool('Groundwater_pumping')
        if self.verbose:
            print('=> Groundwater pumping should be deactivated if includeWaterDemand is False')
        self.var.use_complex_solver_for_modflow = option_bool('use_complex_solver_for_modflow')
        self.var.use_super_complex_solver_for_modflow = option_bool('use_super_complex_solver_for_modflow')
        # water balance check of the CWatM - ModFlow exchange: written to ModFlow_DiscrepancyError.txt
        self.var.writeerror = setting_bool('writeModflowError')
        if self.verbose:
            print('=> ModFlow-CwatM water balance is ' + ('' if self.var.writeerror else 'not ') + 'checked')

    def aquifer_top(self, topography):
        """
        Top and bottom of the ModFlow layer (self.layer_boundaries): the top is the topography, minus the soil depth
        (use_soildepth_as_GWtop) and / or a depth under lakes (correct_soildepth_underlakes), under rivers 1 m lower
        """
        soildepth_as_GWtop = setting_bool('use_soildepth_as_GWtop')
        correct_depth_underlakes = setting_bool('correct_soildepth_underlakes')
        if self.verbose:
            print('=> Upper limit of groundwater: topography' + (' minus soil depth' if soildepth_as_GWtop else '')
                  + (', depth under lakes corrected' if correct_depth_underlakes else ''))

        waterBodyID = loadmap('waterBodyID').astype(np.int64)
        if soildepth_as_GWtop:  # topographic minus soil depth map is used as groundwater upper boundary
            soildepth = self.var.soildepth12
            if correct_depth_underlakes:
                # in some regions soil depth is around zeros under lakes, it should be similar to neighboring cells
                median = np.nanmedian(self.var.soildepth12)
                soildepth = np.where(waterBodyID != 0, median - loadmap('depth_underlakes'), soildepth)
                # some cells around lakes have small soil depths (before 2026-10 this line started again from
                # soildepth12, so the lake correction above had no effect)
                soildepth = np.where(self.var.soildepth12 < 0.4, median, soildepth)
            soildepth_modflow = self.grid.to_modflow(soildepth, all_cells=True) + 0.05
        elif correct_depth_underlakes:  # topography minus a depth under lakes
            soildepth_modflow = self.grid.to_modflow(np.where(waterBodyID != 0, loadmap('depth_underlakes'), 0),
                                                     all_cells=True)
        else:  # topographic map is used as groundwater upper boundary
            soildepth_modflow = np.zeros((self.grid.nrow, self.grid.ncol), dtype=np.float32)
        soildepth_modflow[np.isnan(soildepth_modflow)] = 0

        self.layer_boundaries = np.empty((self.nlay + 1, self.grid.nrow, self.grid.ncol), dtype=np.float32)
        self.layer_boundaries[0] = topography - soildepth_modflow
        self.layer_boundaries[1] = self.layer_boundaries[0] - self.thickness

        lake_modf = self.grid.to_modflow(np.where(waterBodyID != 0, 1, 0), all_cells=True)
        soildepth_modflow[np.isnan(lake_modf)] = 0
        # under rivers (channel_ratio > 0, no lake) the top of the aquifer is 1 m lower: groundwater drains
        # (DRN elevation = top) to the river from 1 m below the surface
        self.layer_boundaries[0] = np.where(lake_modf <= 0, np.where(self.var.channel_ratio > 0,
                                                                     self.layer_boundaries[0] - 1,
                                                                     self.layer_boundaries[0]),
                                            self.layer_boundaries[0])

        # saving soil thickness at modflow resolution to compute water table depth in postprocessing
        self.var.modflowtotalSoilThickness = soildepth_modflow

    def initial_head(self):
        """
        Initial head at ModFlow resolution: the MODFLOW head saved with the init file (restart), init_water_table
        or initial_water_table_depth below the top of the aquifer
        returns the head for CWatM (float32) and the head for MODFLOW (float64 for a restart)
        """
        # restart: MODFLOW head saved together with the init file (save_initial) - float64 for MODFLOW;
        # <init file>_modflowhead.nc, or .npy (written before 2026-10)
        restart_head = None
        if self.var.loadInit:
            for extension in ('.nc', '.npy'):
                filename = os.path.splitext(self.var.initLoadFile)[0] + '_modflowhead' + extension
                if os.path.isfile(filename):
                    restart_head = filename
                    break

        if restart_head is not None:
            if self.var.load_init_water_table:
                print(CWATMWarning("Warning: init_water_table is not used - the MODFLOW head saved with the "
                                   "init file is used: " + restart_head))
            head_modflow = self.grid.read_map(restart_head)
            # CWatM works with float32 heads (as after each MODFLOW step), MODFLOW gets the float64 head
            return head_modflow.astype(np.float32), head_modflow

        if self.var.load_init_water_table:
            # head map at ModFlow resolution: netCDF (variable with 2 dimensions row, col) or .npy
            watertable = cbinding('init_water_table')
            if self.verbose:
                print('=> Initial water table depth is uploaded from ', watertable)
            head = self.grid.read_map(watertable)
        else:
            start_watertabledepth = loadmap('initial_water_table_depth')
            if self.verbose:
                print('=> Water table depth is - ', start_watertabledepth, ' m at the begining')
            head = self.layer_boundaries[0] - start_watertabledepth
        return head, head

    def pumping_wells(self, modflow_basin):
        """Wells in each active ModFlow cell (None without pumping) and the storage limit for pumping"""
        self.var.availableGWStorageFraction = 0.85
        if not self.var.GW_pumping:
            return None
        # wells_index: flat index (row * ncol + col) of each well
        self.var.wells_index = np.flatnonzero(modflow_basin)
        if 'water_table_limit_for_pumping' in binding:
            # if available storage is too low, no pumping in this cell
            self.var.availableGWStorageFraction = np.maximum(
                np.minimum(0.98, loadmap('water_table_limit_for_pumping')),
                0)  # if 85% of the ModFlow cell is empty, we prevent pumping in this cell
        if self.verbose:
            print('=> Pumping in the ModFlow layer is prevented if water table is under',
                  int(100 * (1 - self.var.availableGWStorageFraction)), '% of the layer capacity')
        return np.copy(modflow_basin)

    def initial(self):
        """
        Initialize MODFLOW groundwater model setup.

        Sets up the MODFLOW 6 simulation including model domain, parameters,
        initial conditions, and establishes the coupling interface with CWatM.
        Configures aquifer properties, boundary conditions, and solver settings.
        """

        # no steady state run: the initial water table is given (initial_water_table_depth or init_water_table)
        self.var.modflow_timestep = 1
        if not self.var.modflow:
            return

        self.read_settings()
        # ModFlow grid, index pairs of CWatM / ModFlow cells and conversion of maps (grid.py)
        self.grid = ModflowGrid(self.var.cellArea)
        modflow_basin = self.grid.basin
        topography = np.where(modflow_basin, self.grid.read_tif('topo_modflow'), np.nan)
        # the percentage of river at ModFlow resolution, used to partition the upward flow from ModFlow into
        # capillary rise and baseflow; correction river_percent_factor of the settings file (only where there
        # is a river), between 0 and 1
        channel_ratio = self.grid.read_tif('chanRatio')
        factor_channelratio = float(binding['river_percent_factor']) if 'river_percent_factor' in binding else 0.
        self.var.channel_ratio = np.where(channel_ratio > 0, np.clip(channel_ratio + factor_channelratio, 0, 1), 0)

        # aquifer properties: one value or a map at CWatM resolution (permeability in m/s -> m/day)
        self.permeability = self.grid.from_cwatm_cells('permeability', 1e-6, factor=86400)
        self.porosity = self.grid.from_cwatm_cells('poro', 0.02)
        self.thickness = self.grid.from_cwatm_cells('thickness', 50)

        self.aquifer_top(topography)
        head, head_modflow = self.initial_head()

        # Defining potential leakage under rivers and lakes or reservoirs
        self.var.leakageriver_factor = 0
        if 'leakageriver_permea' in binding:
            self.var.leakageriver_factor = loadmap('leakageriver_permea')  # in m/day
            if self.verbose:
                print('=> Potential groundwater inflow from rivers is ', self.var.leakageriver_factor, ' m/day')
        self.var.leakagelake_factor = 0
        if 'leakagelake_permea' in binding:
            self.var.leakagelake_factor = loadmap('leakagelake_permea')  # in m/day
            if self.verbose:
                print('=> Groundwater inflow from lakes/reservoirs is ', self.var.leakagelake_factor, ' m/day')

        pumpingloc = self.pumping_wells(modflow_basin)

        # initializing the ModFlow6 model (specific yield: also the porosity map without pumping - before 2026-10
        # float(cbinding('poro')), which stopped with a porosity map)
        self.modflow = self.ModFlow(
            'transient',
            cbinding('PathGroundwaterModflowOutput'),
            self.directory_mf6dll,
            timestep=self.var.modflow_timestep,
            specific_storage=0,
            specific_yield=self.porosity,
            nlay=self.nlay,
            nrow=self.grid.domain['nrow'],
            ncol=self.grid.domain['ncol'],
            rowsize=self.grid.domain['rowsize'],
            colsize=self.grid.domain['colsize'],
            top=self.layer_boundaries[0],
            bottom=self.layer_boundaries[1],
            basin=modflow_basin,
            head=head_modflow,
            topography=self.layer_boundaries[0],
            permeability=self.permeability,
            load_from_disk=self.load_from_disk,
            setpumpings=self.var.GW_pumping,
            pumpingloc=pumpingloc,
            verbose=self.verbose,
            complex_solver=self.var.use_complex_solver_for_modflow,
            super_complex_solver=self.var.use_super_complex_solver_for_modflow,
            binary=self.binary)

        # top of the aquifer at CWatM resolution (constant) for the groundwater depth
        self.top_cwatm = self.grid.to_cwatm(self.layer_boundaries[0])

        # initializing arrays
        # capillary rise from MODFLOW - from the init file for a restart (used by the soil before MODFLOW runs)
        self.var.capillar = self.var.load_initial('capillar', default=globals.inZero.copy())
        self.var.baseflow = globals.inZero.copy()

        # sumed up groundwater recharge for the number of days
        self.var.sumed_sum_gwRecharge = globals.inZero.copy()
        self.var.modflow_compteur = 0  # number of the MODFLOW run (water balance check file)
        # percentage discrepancy error of each MODFLOW run: (number of the MODFLOW run, date, error in %)
        self.var.modflowdiscrepancy = []

        # water table at ModFlow resolution and converted into CWatM map
        self.var.modflow_watertable = np.copy(head)
        self.var.head = self.grid.to_cwatm(head)

        # initial groundwater storage at ModFlow resolution and as CWatM map (in meter, used in water demand)
        self.var.groundwater_storage_top_layer = self.storage(head)
        self.var.groundwater_storage_available = self.grid.to_cwatm(self.var.groundwater_storage_top_layer)
        # groundwater storage at full capacity: limits the pumping in water demand
        self.var.gwstorage_full = self.grid.to_cwatm(
            (self.layer_boundaries[0] - self.layer_boundaries[1]) * self.porosity[0])

        # permeability need to be translated into CWatM map to compute leakage from surface water bodies
        self.var.permeability = self.grid.to_cwatm(self.permeability[0])

    def water_balance(self, recharge, outflow, storage_change, pumping):
        """
        Water balance error of the aquifer in % of the mean flow (m3 per MODFLOW period): recharge = capillary rise
        + baseflow (outflow) + storage change - pumping (actual pumping < 0)
        """
        mid_gwflow = np.nansum(((recharge + outflow) * self.grid.cell_area - pumping) / 2)
        return np.round(100 * (np.nansum(
            (recharge - outflow - storage_change) * self.grid.cell_area + pumping) / mid_gwflow), 2)

    def write_discrepancy(self):
        """Writing the ModFlow discrepancies above 0.01 % to ModFlow_DiscrepancyError.txt"""
        threeshold_modflow_error = 0.01  # in percentage
        with open(cbinding('PathOut') + '/' + 'ModFlow_DiscrepancyError.txt', "w") as discrep_file:
            sum_modflow_errors = 0
            for nrun, date, error in self.var.modflowdiscrepancy:
                if abs(error) > threeshold_modflow_error:  # if error is higer than threeshold in %, we print it.
                    discrep_file.write("ModFlow stress period " + str(nrun) + " (" + date +
                                       ") : percentage error in ModFlow is " + str(error) + "\n")
                    sum_modflow_errors += 1
            if sum_modflow_errors == 0:
                discrep_file.write(
                    "ModFlow error was always below " + str(threeshold_modflow_error) + ' % during the simulation')

    def modflow_run(self):
        """
        One MODFLOW run: recharge and pumping of the last MODFLOW period to ModFlow, run, then head, storage,
        capillary rise, baseflow, actual pumping and saturated fraction back to CWatM
        """
        self.var.modflow_compteur += 1

        # converting the CWatM recharge into ModFlow recharge (in meter)
        # we avoid recharge on saturated ModFlow cells, thus CWatM recharge is concentrated  on unsaturated cells
        # (a fully saturated CWatM cell, capriseindex = 1, gets no recharge - checked 2026-10: CWatM recharge
        # is already 0 there, Bhima 40 days: 0.00 % of the recharge)
        corrected_recharge = np.where(self.var.capriseindex == 1, 0,
                                      self.var.sumed_sum_gwRecharge / (1 - self.var.capriseindex))
        groundwater_recharge_modflow = self.grid.to_modflow(corrected_recharge, nanvalue=0)
        groundwater_recharge_modflow = np.where(self.var.modflow_watertable - self.layer_boundaries[0] >= 0,
                                                0, groundwater_recharge_modflow)
        # give the information to ModFlow
        self.modflow.set_recharge(groundwater_recharge_modflow)

        # pumping: groundwater demand of the CWatM water demand module (wells in each Modflow cell),
        # given to ModFlow in m3 per MODFLOW period and < 0
        if self.var.GW_pumping:
            groundwater_abstraction = (- self.grid.to_modflow(self.var.modfPumpingM)
                                       * self.grid.domain['rowsize'] * self.grid.domain['colsize'])
            self.modflow.set_groundwater_abstraction(groundwater_abstraction)

        # running ModFlow
        self.modflow.step()

        # extracting the new simulated hydraulic head map
        head = self.modflow.decompress(self.modflow.head.astype(np.float32))

        # groundwater storage at ModFlow resolution (in meter) - the previous one for the water balance check
        groundwater_storage_top_layer0 = self.var.groundwater_storage_top_layer
        self.var.groundwater_storage_top_layer = self.storage(head)
        # converting the groundwater storage from ModFlow to CWatM map (in meter)
        self.var.groundwater_storage_available = self.grid.to_cwatm(self.var.groundwater_storage_top_layer)

        # groundwater outflow = drain flow of MODFLOW (DRN: conductance = permeability * cell area * timestep,
        # elevation = top), in m/day per ModFlow cell - before 2026-10 recomputed from the float32 head
        groundwater_outflow = self.modflow.decompress(
            -self.modflow.drainage / (self.grid.cell_area * self.var.modflow_timestep))
        groundwater_outflow[~self.modflow.basin] = 0
        # saturated ModFlow cells: for the next step, it will prevent recharge where ModFlow cells are saturated,
        # even if there is no capillary rise (where h==topo)
        groundwater_outflow2 = np.where(head - self.layer_boundaries[0] >= 0, 1.0, 0.0)

        # capillary rise and baseflow from groundwater are allocated in function of the river percentage of each
        # ModFlow cell (still in ModFlow coordinates)
        capillar = groundwater_outflow * (1 - self.var.channel_ratio)
        baseflow = groundwater_outflow * self.var.channel_ratio

        # actual ModFlow pumping in m3 (MODFLOW reduces the pumping if a cell is almost dry) - water cycle output
        # (modfPumpingM_actual) and water balance check; one well in each active ModFlow cell (wells_index)
        actual_pumping_modflow_array = 0
        if self.var.GW_pumping:
            actual_pumping = self.modflow.actualwell_rate.astype(np.float32)
            actual_pumping_modflow_array = np.bincount(
                self.var.wells_index, weights=actual_pumping,
                minlength=self.grid.nrow * self.grid.ncol).reshape((self.grid.nrow, self.grid.ncol))
            self.var.modfPumpingM_actual = - self.grid.to_cwatm(actual_pumping_modflow_array) / self.grid.cell_area

        if self.var.writeerror:
            #  saving modflow discrepancy, it will be written a text file at the end of the simulation
            error = self.water_balance(groundwater_recharge_modflow, (capillar + baseflow) * self.var.modflow_timestep,
                                       self.var.groundwater_storage_top_layer - groundwater_storage_top_layer0,
                                       actual_pumping_modflow_array)
            self.var.modflowdiscrepancy.append((self.var.modflow_compteur, dateVar['currDatestr'], error))

        # converting flows from ModFlow to CWatM domain
        self.var.capillar = self.grid.to_cwatm(capillar)
        baseflow = baseflow.astype('float64')  # required for runoff concentration (lib2.runoffConc)
        self.var.baseflow = self.grid.to_cwatm(baseflow)

        # fraction of saturated ModFlow cells in each CWatM cell (water table >= top of the aquifer)
        self.var.capriseindex = self.grid.fraction_to_cwatm(groundwater_outflow2)

        # updating water table maps both at CWatM and ModFlow resolution
        self.var.head = self.grid.to_cwatm(head)
        self.var.gwdepth = self.top_cwatm - self.var.head

        if 'gw_depth_observations' in binding:
            self.var.gwdepth_difference_sim_obs = self.var.gwdepth - self.var.gwdepth_observations
        if 'gw_depth_sim_obs' in binding:
            self.var.gwdepth_adjusted = np.maximum(self.var.gwdepth - self.var.gwdepth_adjuster, 0)
            self.var.modflow_head_adjusted = self.layer_boundaries[0] - self.grid.to_modflow(self.var.gwdepth_adjusted)

        self.var.modflow_watertable = np.copy(head)

        # Re-initializing the weekly (orbi-weekly, or monthly...) sum of groundwater pumping
        self.var.modfPumpingM = globals.inZero.copy()
        # Re-initializing the sum of recharge for the next MODFLOW run (as the pumping above)
        self.var.sumed_sum_gwRecharge = 0

    def dynamic(self):
        """
        Execute dynamic groundwater calculations for current time step.

        Handles groundwater recharge input, pumping rates, runs MODFLOW simulation,
        and processes results for feedback to CWatM. Manages temporal coupling
        and data exchange between surface and groundwater models.
        """

        # actual pumping of MODFLOW: only on MODFLOW days (water cycle output)
        self.var.modfPumpingM_actual = globals.inZero.copy()

        # Adding recharge of the day to the weekly (or bi-weekly, or monthly...) sum - the sum starts again after
        # each MODFLOW run (at the end of modflow_run), also after the first run on day 1
        self.var.sumed_sum_gwRecharge = self.var.sumed_sum_gwRecharge + self.var.sum_gwRecharge

        # Every modflow timestep (e.g. 7,14,30... days)
        if dateVar['curr'] == 1 or (dateVar['curr'] % self.var.modflow_timestep) == 0:
            self.modflow_run()

        # restart: MODFLOW head (float64, MODFLOW grid) saved together with the init file (save_initial / StepInit)
        # as netCDF <initSave>_<date>_modflowhead.nc - also usable as init_water_table
        if self.var.saveInit and dateVar['curr'] in dateVar['intInit']:
            headfile = self.var.saveInitFile + "_%02d%02d%02d_modflowhead.nc" % (
                dateVar['currDate'].year, dateVar['currDate'].month, dateVar['currDate'].day)
            self.grid.write_netcdf(headfile, 'head', self.modflow.decompress(
                np.asarray(self.modflow.head, dtype=np.float64)), 'm', 'MODFLOW head (water table) ' +
                dateVar['currDate'].strftime('%d/%m/%Y'))

        # Writing ModFlow discrepancies at the end of simulation (also if the last day is not a MODFLOW day)
        if dateVar['currDate'] == dateVar['dateEnd'] and self.var.writeerror:
            self.write_discrepancy()
