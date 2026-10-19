# Purpose: MODFLOW coupling module integrating external groundwater simulation with CWatM.
# Manages bidirectional data exchange between surface and groundwater models.
# Supports transient groundwater simulation with dynamic surface-groundwater interaction.
import numpy as np
import os

from cwatm.management_modules.data_handling import *
from cwatm.hydrological_modules.groundwater_modflow.grid import ModflowGrid
from cwatm.hydrological_modules.groundwater_modflow.modflow6 import ModFlowSimulation, MF6_SOLVERS
from cwatm.hydrological_modules.groundwater_modflow.modflow6_process import ModFlowProcess
from cwatm.management_modules.data_modflow import find_restart_head, write_discrepancy_file, check_mf6_directory
import functools


def setting_bool(name, default=False):
    """True/False key of the settings file, default if the key is missing"""
    return returnBool(name) if name in binding else default


def option_bool(name):
    """True/False key of the [OPTIONS] section, False if the key is missing"""
    return name in option and bool(checkOption(name))


def renamed_key(name, old_name):
    """Settings key name, or its former name old_name (with a warning); None if both are missing"""
    if name in binding:
        return name
    if old_name in binding:
        print(CWATMWarning("Warning: " + old_name + " is a former name - please use " + name))
        return old_name
    return None


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
    capriseindex_start                   Array         saturated fraction of each CWatM cell of the initial MODFLOW head       --   
    soildepth12                          Array         Total thickness of layer 2 and 3                                        m    
    leakageriver_factor                  Array                                                                                 --   
    leakagelake_factor                   Array                                                                                 --   
    modflow_timestep                     Array         Chosen ModFlow model timestep (1day, 7days, 30days, etc.)               day  
    head                                 Array         Simulated ModFlow water level of layer 1 [masl]                         m    
    gwdepth_adjusted                     Array         Adjusted depth to groundwater table                                     m    
    gwdepth                              Array         Depth to groundwater table (top of the aquifer - head of layer 1)       m    
    channel_ratio                        Array                                                                                 --   
    modflowtotalSoilThickness            Array         Array (nrows, ncol) used to compute water table depth in post-processi  m    
    load_init_water_table                Flag          defining the initial water table map (it can be a hydraulic head map p  --   
    GW_pumping                           Flag          Input, True if Groundwater_pumping=True                                 bool 
    availableGWStorageFraction           Array         Minimum saturated fraction kept in each layer (pumping limit)           --   
    wells_index                          Array                                                                                 --   
    sumed_sum_gwRecharge                 Array         setting sumed up recharge again to 7 (or 14 or 30...), will be sumed u  --   
    modflow_compteur                     Number        Counts each day relatively to the chosen ModFlow timestep, allow to ru  day  
    modflow_watertable                   Array         water table will be also saved at modflow resolution (AI)               --   
    writeerror                           Flag                                                                                  --   
    modflowdiscrepancy                   Array         saving modflow discrepancy, it will be written a text file at the end   --   
    groundwater_storage_top_layer        Array         Groundwater storage of layer 1 at ModFlow resolution                    m    
    groundwater_storage_available        Array         Groundwater storage of all layers above the minimum, cells with wells   m    
    gwstorage_full                       Array         Groundwater storage of layer 1 at full capacity (output only)           m    
    permeability                         Array         permeability need to be translated into CWatM map to compute leakage f  --   
    modfPumpingM_actual                  Array         Actual groundwater pumping. Used with MODFLOW.                          m    
    gwdepth_difference_sim_obs           Array         Difference between simulated and observed groundwater table             m    
    modflow_head_adjusted                Array                                                                                 --   
    cellArea                             Array         Area of cell                                                            m2   
    modfPumpingM                         Array         modfPumpingM is initialized every modflow_timestep in groundwater_modf  --   
    head<n>                              Array         Simulated ModFlow water level of layer n (n = 1 ... nlay)               m    
    gwdepth<n>                           Array         Depth of the head below the top of layer n (n = 1 ... nlay)             m    
    permeability_vertical                Array         Vertical permeability of layer 1 at CWatM resolution                    m/day
    recharge_limit                       Array         Recharge limit min(permeability_vertical, lowPermabilityCover) or None  m/day
    sum_gwRecharge_actualM               Array         Recharge given to MODFLOW, mean per day of the MODFLOW period           m    
    rejected_recharge_previous_day       Array         CWatM recharge not given to MODFLOW (saturated, dry cells), interflow   m    
    sum_gwRechargeExported               Array         Recharge collected to other groundwater basins (collect_recharge)       m    
    modflow_buffer                       Array         coupling buffer CWatM-MODFLOW: water between the models (WaterCycle)    m    
    capillarUsed                         Array         capillary rise of the last MODFLOW run used today by the land           m    
    gwRechargeExported_day               Array         recharge exported to other groundwater basins on MODFLOW days           m    
    balance_gw                           Array         Recharge - capillar - baseflow + pumping - storage change per period    m3   
    groundwater_storage_total            Array         Groundwater storage of all MODFLOW layers                               m    
    modflow_nlay                         Number        Number of ModFlow layers (WaterBalance output columns)                  --   
    gwlayer<n>_storage                   Array         Groundwater storage of layer n (WaterBalance)                           m    
    gwlayer<n>_<flow>                    Array         Flow into layer n per MODFLOW run: lateral, fromAbove, fromBelow        m    
    gwlayer<n>_pumping                   Array         Actual pumping from layer n per MODFLOW run (WaterBalance)              m    
    gwlayer1_recharge                    Array         Recharge into layer 1 per MODFLOW run (WaterBalance)                    m    
    gwlayer1_drain                       Array         Drain flow (baseflow + capillary rise) of layer 1 per MODFLOW run       m    
    gw_lateral                           Array         Lateral flow of all layers per MODFLOW run (WaterBalance)               m    
    gw_rechargeMoved                     Array         Recharge moved between CWatM cells by the ModFlow grid per MODFLOW run  m    
    depth_to_water                       Array         Topography (topo_modflow) minus the head of layer 1                     m    
    firstout                             Number        Discharge of the first gauge (0 for the steady state run)               m3/s 
    modflow_seepage                      Flag          Seepage scheme with MODFLOW: modflow_seepage in settings, default True  bool 
    modflow_cover                        Array         Share of the CWatM cell covered by active ModFlow cells                 --   
    seepage                              Array         MODFLOW outflow not taken up by the soil, goes to the seepage pond      m    
    capRiseFromAquifer                   Array         Capillary rise from the aquifer (seepage scheme), negative recharge     m    
    seepagePond                          Array         Seepage pond per land cover (max. 0.1 m x saturated share)              m    
    seepageEvap                          Array         Evaporation from the seepage pond, up to EWRef x saturated share        m    
    capRiseAquiferLimit                  Array         Max. capillary rise from the aquifer: 10 % of layer-1 storage per day   m    
    sum_capRiseFromAquifer               Array         Capillary rise from the aquifer, cell mean                              m    
    sumed_capRiseFromAquifer             Array         Capillary rise from the aquifer summed over the MODFLOW period          m    
    coverTypes                           Array         land cover types - forest - grassland - irrPaddy - irrNonPaddy - water  --   
    load_initial                         Flag          Settings initLoad holds initial conditions for variables                bool 
    pondOverflow                         Array         Seepage pond overflow to direct runoff (rest after the soil) per cover  m    
    over2river                           Array         Seepage pond overflow to direct runoff (rest after soil), cell mean     m    
    pondarea                             Array         Pond area: max(capriseindex, saturatedFrac), share of soil covers       --   
    pondToSoil                           Array         Seepage pond overflow into the soil (layer 3, 2 up to field cap.)       m    
    pond2soil                            Array         Seepage pond overflow into the soil, cell mean (output)                 m    
    pondDepth                            Number        Depth of the seepage pond over the pond area (seepage_pond_depth)       m    
    pondToSoil3                          Array         Part of pondToSoil into soil layer 3 (the rest into layer 2)            m    
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


    def saturated_fraction(self, head):
        """
        Saturated fraction of each layer (0 - 1, nlay x nrow x ncol) from the heads, with the quadratic smoothing of
        MODFLOW 6 (Documentation for the MODFLOW 6 Groundwater Flow Model, TM 6-A55, eq. 4-4 to 4-6, omega = 1e-6),
        from Dor's multi-layer version
        """
        omega = 1e-6
        a_omega = 1 / (1 - omega)
        top, bottom = self.layer_boundaries[:-1], self.layer_boundaries[1:]
        thickness = top - bottom
        saturated = np.maximum(np.minimum(head, top) - bottom, 0.)
        sf = np.divide(saturated, thickness, out=np.zeros_like(saturated), where=thickness > 0)
        return np.where(sf < omega, a_omega / (2 * omega) * sf ** 2,
                        np.where(sf < 1 - omega, a_omega * sf + 0.5 * (1 - a_omega),
                                 np.where(sf < 1, 1 - a_omega / (2 * omega) * (1 - sf) ** 2, 1.)))

    def storage(self, head):
        """
        Groundwater storage of each layer (m water, nlay x nrow x ncol) at ModFlow resolution from the heads (nlay,
        nrow, ncol), as MODFLOW 6 (TM 6-A55 ch. 5): saturated thickness * specific yield of convertible layers +
        specific storage * saturated thickness * (head - middle of the saturated thickness). Before 2026-10-10 the
        specific storage term used the head in m a.s.l. (Dor, E8): UNWMZ with Ss = 1e-5 balance check -53 to -125 %
        per day, now -0.44 to 0.26 %. No effect with specific storage 0 (default)
        """
        bottom = self.layer_boundaries[1:]
        saturated = (self.layer_boundaries[:-1] - bottom) * self.saturated_fraction(head)
        specific_storage = 0. if self.specific_storage is None else self.specific_storage
        convertible = 1. if self.confined is None else (self.confined > 0)
        return specific_storage * saturated * (head - bottom - saturated / 2) + saturated * self.specific_yield * convertible

    def available_storage(self, head):
        """
        Groundwater storage of each layer that can be pumped (m water, nlay x nrow x ncol), as in Dor's version: the
        storage above the minimum saturated fraction availableGWStorageFraction (water_table_limit_for_pumping) of the
        layer, in the cells with wells (self.wells); specific storage term as in storage()
        """
        top, bottom = self.layer_boundaries[:-1], self.layer_boundaries[1:]
        thickness = top - bottom
        fraction = self.saturated_fraction(head)
        fraction_min = self.var.availableGWStorageFraction
        saturated = thickness * fraction
        specific_storage = 0. if self.specific_storage is None else self.specific_storage
        convertible = 1. if self.confined is None else (self.confined > 0)
        volume_ss = specific_storage * saturated * (head - bottom - saturated / 2)
        volume_ss_min = specific_storage * (fraction_min * thickness) ** 2 / 2
        available = np.maximum(volume_ss - volume_ss_min, 0) + thickness * (
            self.specific_yield * np.maximum(fraction - fraction_min, 0) * convertible)
        return np.where(self.wells, np.maximum(available, 0), 0)

    def optional_layers(self, name, default, fill=None, factor=1):
        """
        Property of each layer from the keys <name><n> (see grid.layer_property), None if no layer has a key;
        default (a value or an array nlay x nrow x ncol, in the model unit) for the layers without key
        """
        if all(self.grid.layer_key(name, n) is None for n in range(1, self.nlay + 1)):
            return None
        shape = (self.nlay, self.grid.nrow, self.grid.ncol)
        return self.grid.layer_property(name, self.nlay, fill, factor, default=np.broadcast_to(default, shape))

    def layer_outputs(self, head):
        """
        Head and groundwater depth below the top of each layer n at CWatM resolution: head<n>, gwdepth<n>, and the
        groundwater depth of layer 1 (gwdepth, compared to observations) - at the start and after each MODFLOW run
        """
        for n in range(1, self.nlay + 1):
            head_n = self.var.head if n == 1 else self.grid.to_cwatm(head[n - 1], mean=True)
            setattr(self.var, 'head' + str(n), head_n)
            setattr(self.var, 'gwdepth' + str(n), self.layer_top_cwatm[n - 1] - head_n)
        self.var.gwdepth = self.top_cwatm - self.var.head

        if 'gw_depth_observations' in binding:
            self.var.gwdepth_difference_sim_obs = self.var.gwdepth - self.var.gwdepth_observations
        if 'gw_depth_sim_obs' in binding:
            self.var.gwdepth_adjusted = np.maximum(self.var.gwdepth - self.var.gwdepth_adjuster, 0)
            self.var.modflow_head_adjusted = self.layer_boundaries[0] - self.grid.to_modflow(self.var.gwdepth_adjusted)

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
        check_mf6_directory(self.directory_mf6dll)  # Error 222 if missing (data_modflow.py)
        self.nlay = int(loadmap('nlay'))
        # number of ModFlow layers (the same active cells in each layer); layer properties: keys <name><n>
        if self.nlay < 1:
            raise CWATMError("Error 146: nlay = " + str(self.nlay) + " - the number of ModFlow layers has to be 1 or more\n")

        # defining the initial water table map (it can be a hydraulic head map previously simulated)
        self.var.load_init_water_table = setting_bool('load_init_water_table')
        # test if ModFlow pumping is used as defined in settings file
        self.var.GW_pumping = setting_bool('Groundwater_pumping')
        if self.verbose:
            print('=> Groundwater pumping should be deactivated if includeWaterDemand is False')
        # MODFLOW solver: modflow_solver = simple (default), complex, super_complex, cooley (Dor's version) or dbd
        self.solver = 'simple'
        if 'modflow_solver' in binding:
            self.solver = cbinding('modflow_solver').strip().lower()
            if self.solver not in MF6_SOLVERS:
                msg = "Error 151: modflow_solver = " + cbinding('modflow_solver') + " is not known - use one of: "
                msg += ", ".join(MF6_SOLVERS) + "\n"
                raise CWATMError(msg)
        # the former [OPTIONS] use_complex_solver_for_modflow / use_super_complex_solver_for_modflow are not used any
        # more (2026-10-16): a warning; with True and without modflow_solver they still choose their solver (as before)
        for old, solver in [('use_super_complex_solver_for_modflow', 'super_complex'),
                            ('use_complex_solver_for_modflow', 'complex')]:
            if old in option:
                msg = ("Warning: " + old + " in [OPTIONS] is not used any more - use modflow_solver = " + solver +
                       " in [GROUNDWATER_MODFLOW]")
                if option_bool(old) and 'modflow_solver' not in binding:
                    self.solver = solver
                    msg += " (" + solver + " is used for this run)"
                print(CWATMWarning(msg))
        # water balance check of the CWatM - ModFlow exchange: written to ModFlow_DiscrepancyError.txt
        self.var.writeerror = setting_bool('writeModflowError')
        if self.verbose:
            print('=> ModFlow-CwatM water balance is ' + ('' if self.var.writeerror else 'not ') + 'checked')
        # seepage scheme (modflow_seepage, default True; False: the old scheme with saturated ModFlow cells): the
        # MODFLOW outflow on the land is seepage (pond, evaporation, runoff) instead of soil water; capillary rise into
        # the soil and percolation with the sub-grid saturated share from relativeElevation (capillarRise.py) instead
        # of the saturated ModFlow cells (flip-flop)
        self.var.modflow_seepage = setting_bool('modflow_seepage', True)

    def aquifer_top(self, topography):
        """
        Top of the aquifer and bottom of each ModFlow layer (self.layer_boundaries, nlay + 1): the top is the
        topography, minus the soil depth (use_soildepth_as_GWtop) and / or a depth under lakes
        (correct_soildepth_underlakes), under rivers 1 m lower; bottom of layer n = bottom of layer n - 1 - thickness<n>
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
                # in some regions soil depth is around zeros under lakes, it should be similar to neighboring cells:
                # cells with small soil depths (also around lakes) get the median soil depth, lakes / reservoirs the
                # median plus depth_underlakes (top of the aquifer depth_underlakes below the normal top, as without
                # use_soildepth_as_GWtop). Before 2026-10-11: lakes median - depth_underlakes (top higher), then
                # overwritten by the median where the soil depth < 0.4 m (before 2026-10-05 the lake correction had no
                # effect at all: the second line started again from soildepth12)
                median = np.nanmedian(self.var.soildepth12)
                soildepth = np.where(self.var.soildepth12 < 0.4, median, soildepth)
                soildepth = np.where(waterBodyID != 0, median + loadmap('depth_underlakes'), soildepth)
            soildepth_modflow = self.grid.to_modflow(soildepth, all_cells=True) + 0.05
        elif correct_depth_underlakes:  # topography minus a depth under lakes
            soildepth_modflow = self.grid.to_modflow(np.where(waterBodyID != 0, loadmap('depth_underlakes'), 0),
                                                     all_cells=True)
        else:  # topographic map is used as groundwater upper boundary
            soildepth_modflow = np.zeros((self.grid.nrow, self.grid.ncol), dtype=np.float32)
        soildepth_modflow[np.isnan(soildepth_modflow)] = 0

        self.layer_boundaries = np.empty((self.nlay + 1, self.grid.nrow, self.grid.ncol), dtype=np.float32)
        self.layer_boundaries[0] = topography - soildepth_modflow

        lake_modf = self.grid.to_modflow(np.where(waterBodyID != 0, 1, 0), all_cells=True)
        # share of lakes / reservoirs in each ModFlow cell (no lowering of the drains under lakes)
        self.lake_modflow = np.nan_to_num(lake_modf)
        # under rivers (channel_ratio > 0, no lake) the top of the aquifer is 1 m lower: groundwater drains
        # (DRN elevation = top) to the river from 1 m below the surface
        self.layer_boundaries[0] = np.where(lake_modf <= 0, np.where(self.var.channel_ratio > 0,
                                                                     self.layer_boundaries[0] - 1,
                                                                     self.layer_boundaries[0]),
                                            self.layer_boundaries[0])
        # bottoms below the (lowered) top: the whole column is 1 m lower under rivers, layer 1 keeps thickness1 -
        # before 2026-10-11 the bottoms were computed before the lowering: layer 1 was 1 m thinner under rivers
        # (UNWMZ 2 layers: 9.9 -> 8.9 m), with thickness1 <= 1 m the top was at or below the bottom
        for n in range(self.nlay):
            self.layer_boundaries[n + 1] = self.layer_boundaries[n] - self.thickness[n]

        # saving soil thickness at modflow resolution to compute water table depth in postprocessing
        self.var.modflowtotalSoilThickness = soildepth_modflow

    def initial_head(self):
        """
        Initial head of each layer at ModFlow resolution (nlay, nrow, ncol): the MODFLOW head saved with the init file
        (restart), init_water_table (one file with all layers) or initial_water_table_depth<n> below the top of the
        aquifer; returns the head for CWatM (float32) and the head for MODFLOW (float64 for a restart)
        """
        # restart: MODFLOW head saved together with the init file (save_initial) - float64 for MODFLOW;
        # <init file>_modflowhead.nc (before 2026-10-13 also .npy, written before 2026-10)
        restart_head = find_restart_head(self.var.initLoadFile) if self.var.loadInit else None

        if restart_head is not None:
            if self.var.load_init_water_table:
                print(CWATMWarning("Warning: init_water_table is not used - the MODFLOW head saved with the "
                                   "init file is used: " + restart_head))
            head_modflow = self.grid.read_map(restart_head, self.nlay)
            # CWatM works with float32 heads (as after each MODFLOW step), MODFLOW gets the float64 head
            return head_modflow.astype(np.float32), head_modflow

        if self.var.load_init_water_table:
            # head of all layers at ModFlow resolution: netCDF (variable layer, row, col or row, col for one layer)
            # or .npy
            watertable = cbinding('init_water_table')
            if self.verbose:
                print('=> Initial water table depth is uploaded from ', watertable)
            head = self.grid.read_map(watertable, self.nlay)
        else:
            # depth below the top of the aquifer for each layer n: initial_water_table_depth<n> (layer 1 also without
            # number); a layer without key gets the depth of layer 1
            depth1 = self.grid.layer_property('initial_water_table_depth', 1)
            depth = self.grid.layer_property('initial_water_table_depth', self.nlay,
                                             default=np.repeat(depth1, self.nlay, axis=0))
            if self.verbose:
                print('=> Water table depth is - ', np.nanmean(depth, axis=(1, 2)), ' m at the begining')
            head = self.layer_boundaries[0] - depth
        return head, head

    def pumping_wells(self, modflow_basin):
        """
        Wells of each layer (nlay, nrow, ncol): pump_location<n> > 0 (default: all active cells), the minimum saturated
        fraction of each layer which is not pumped (water_table_limit_for_pumping);
        returns the wells for MODFLOW (None without pumping)
        """
        # minimum saturated fraction kept in each layer (Dor's version, default 0.7): a value or a map at CWatM or
        # ModFlow resolution. Before 2026-10: the usable fraction of the full storage (default 0.85)
        self.var.availableGWStorageFraction = 0.7
        if 'water_table_limit_for_pumping' in binding:
            self.var.availableGWStorageFraction = np.clip(
                self.grid.property_map('water_table_limit_for_pumping'), 0, 0.98)
        # wells: also without pumping for the available storage (water demand)
        shape = (self.nlay, self.grid.nrow, self.grid.ncol)
        location = self.optional_layers('pump_location', 1.)
        self.wells = np.broadcast_to(modflow_basin, shape).copy() if location is None else (location > 0) & modflow_basin
        # correctPumpingDiscrepancy (Dor's version) removed 2026-10-10: the pumping split gives ModFlow exactly the
        # CWatM abstraction (difference < 1e-8), there is nothing left to scale
        if 'correctPumpingDiscrepancy' in binding:
            print(CWATMWarning("Warning: correctPumpingDiscrepancy is not used any more - MODFLOW gets the CWatM "
                               "pumping without scaling"))
        if not self.var.GW_pumping:
            return None
        # wells_index: flat index (row * ncol + col) of each well (in the order of the MODFLOW wells: layer by layer)
        layer, row, column = np.nonzero(self.wells)
        self.var.wells_index = row * self.grid.ncol + column
        # layer of each well (pumping per layer, layer_budget)
        self.wells_layer = layer
        if self.verbose:
            print('=> Pumping keeps', np.round(np.mean(self.var.availableGWStorageFraction) * 100),
                  '% of the saturated thickness of each layer;', len(row), 'wells')
        return self.wells

    def channel_ratio_rules(self):
        """
        Channel ratio (share of capillary rise / baseflow going to the river) - Dor's version, only with the keys:
        channel_ratio_lakes = True: 1 under lakes / reservoirs; wetland_fraction (a value or a map) * wetland_bf_coeff
        (default 1): minimum channel ratio outside lakes / reservoirs (more baseflow from wetlands)
        """
        lakes = self.lake_modflow > 0
        if setting_bool('channel_ratio_lakes'):
            self.var.channel_ratio = np.where(lakes, 1., self.var.channel_ratio)
        if 'wetland_fraction' in binding:
            coefficient = float(cbinding('wetland_bf_coeff')) if 'wetland_bf_coeff' in binding else 1.
            wetland = np.clip(self.grid.property_map('wetland_fraction') * coefficient, 0, 1)
            self.var.channel_ratio = np.where(lakes, self.var.channel_ratio,
                                              np.maximum(self.var.channel_ratio, np.nan_to_num(wetland)))

    def drains(self):
        """
        Elevation of the drains in layer 1 (nrow, ncol), Dor's version; None (drain = top of the aquifer) if no key:
        - topo_percentile_modflow: netCDF of sub-grid elevation percentiles at ModFlow resolution, variable
          topo_percentile_prm (default z_p10): drain = min(percentile, top)
        - adjust_drainage_by_river = True: in cells of main rivers (chanWidth >= chanWidthThreshold, default 25 m)
          the drain is lowered by the bankfull depth chanDepth (not under lakes / reservoirs); before each MODFLOW
          run the water depth of the river is added again (river_drains)
        drains stay at least 1 m above the bottom of layer 1
        """
        self.adjust_drainage = setting_bool('adjust_drainage_by_river')
        percentile = renamed_key('topo_percentile_modflow', 'topo_percetile_modflow')
        if percentile is None and not self.adjust_drainage:
            return None
        drain = self.layer_boundaries[0].copy()
        if percentile is not None:
            variable = renamed_key('topo_percentile_prm', 'topo_percetile_prm')
            variable = cbinding(variable).strip() if variable is not None else 'z_p10'
            drain = np.fmin(self.grid.read_map(cbinding(percentile), variable=variable)[0], drain)
        if self.adjust_drainage:
            # main rivers; chanWidth / chanDepth read here: routing_kinematic.initial runs after this module
            min_width = loadmap('chanWidthThreshold') if 'chanWidthThreshold' in binding else 25.
            self.river_main = loadmap('chanWidth') >= min_width
            depth = self.grid.to_modflow(np.where(self.river_main, loadmap('chanDepth'), 0.), nanvalue=0,
                                         all_cells=True)
            drain = drain - np.where(self.lake_modflow > 0, 0., depth)
        return np.maximum(drain, self.layer_boundaries[1] + 1.)

    def river_drains(self):
        """
        Drain elevation with the water depth of the main rivers (Dor's version, formula as in waterquality1.py):
        drains + water depth from the discharge (no flood plain), at most the top of the aquifer
        """
        discharge = np.maximum(self.var.discharge, 0.0001)
        width = 1.22 * discharge ** 0.557
        cross_section = np.minimum(0.4148 * discharge ** 0.898, self.var.totalCrossSectionArea)
        depth = self.grid.to_modflow(np.where(self.river_main, cross_section / width, 0.), nanvalue=0)
        depth = np.where(self.lake_modflow > 0, 0., depth)
        return np.minimum(self.drain_elevation + depth, self.layer_boundaries[0])

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

        # aquifer properties of each layer n: keys thickness<n>, poro<n>, permeability<n> (layer 1 also without
        # number), a value, a map at CWatM resolution or a raster at ModFlow resolution (permeability m/s -> m/day)
        self.permeability = self.grid.layer_property('permeability', self.nlay, 1e-6, factor=86400)
        self.porosity = self.grid.layer_property('poro', self.nlay, 0.02)
        self.thickness = self.grid.layer_property('thickness', self.nlay, 50)
        # further properties of each layer (multi-layer version), used only if a key is given (missing layers:
        # default): vertical permeability permeability_vertical<n> (m/s, default horizontal), specific storage
        # specific_storage<n> (1/m, default 0), confined<n> (0: confined, 1: convertible, default 1) and
        # specific_yield_coeff<n> (specific yield = poro * coefficient, default 1)
        self.permeability_vertical = self.optional_layers('permeability_vertical', self.permeability, 1e-6, 86400)
        self.specific_storage = self.optional_layers('specific_storage', 0.)
        self.confined = self.optional_layers('confined', 1.)
        coefficient = self.optional_layers('specific_yield_coeff', 1.)
        self.specific_yield = self.porosity if coefficient is None else self.porosity * coefficient

        self.aquifer_top(topography)
        head, head_modflow = self.initial_head()
        # head of each layer of the last MODFLOW step (no recharge into cells which are dry in all layers)
        self.head_layers = head
        # fraction of saturated ModFlow cells of the initial head (as in modflow_run): capriseindex before the first
        # MODFLOW run (modflow_timestep > 1) if there is no init file (landcoverType.py) - before 2026-10-11: 0
        self.var.capriseindex_start = self.grid.fraction_to_cwatm(
            np.where(head[0] - self.layer_boundaries[0] >= 0, 1.0, 0.0))
        # topography at ModFlow resolution (depth_to_water)
        self.topography = topography
        self.channel_ratio_rules()
        # share of the recharge collected to other groundwater basins (collect_recharge, 0 - 1, Dor's version)
        self.collect_recharge = None
        if 'collect_recharge' in binding:
            self.collect_recharge = np.clip(self.grid.property_map('collect_recharge'), 0, 1)

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
        # drains (Dor's version): sub-grid elevation percentile and / or main rivers; None: top of the aquifer
        self.drain_elevation = self.drains()

        # number of layers (output.initial: per-layer budget of the WaterBalance output, also for the steady state)
        self.var.modflow_nlay = self.nlay
        # steady state (Dor's version, run 1 of 2, steady.py): MODFLOW head of all layers -> steady_state_heads.nc,
        # no time step
        if setting_bool('run_only_steady_state'):
            # no time step: the seepage scheme is not used (its arrays are only set for the transient run below;
            # capillarRise.py and landcoverType.py follow modflow_seepage)
            self.var.modflow_seepage = False
            # imported here: steady.py imports setting_bool / renamed_key from this module
            from cwatm.hydrological_modules.groundwater_modflow.steady import steady_state
            steady_state(self, modflow_basin, head_modflow)
            return

        # initializing the ModFlow6 model (specific yield: also the porosity map without pumping - before 2026-10
        # float(cbinding('poro')), which stopped with a porosity map)
        self.modflow = self.ModFlow(
            'transient',
            cbinding('PathGroundwaterModflowOutput'),
            self.directory_mf6dll,
            timestep=self.var.modflow_timestep,
            specific_storage=0 if self.specific_storage is None else self.specific_storage,
            specific_yield=self.specific_yield,
            nlay=self.nlay,
            nrow=self.grid.domain['nrow'],
            ncol=self.grid.domain['ncol'],
            rowsize=self.grid.domain['rowsize'],
            colsize=self.grid.domain['colsize'],
            top=self.layer_boundaries[0],
            bottom=self.layer_boundaries[1] if self.nlay == 1 else self.layer_boundaries[1:],
            basin=modflow_basin,
            head=head_modflow,
            topography=self.layer_boundaries[0],
            drain_elevation=self.drain_elevation,
            permeability=self.permeability,
            permeability_vertical=self.permeability_vertical,
            confined=self.confined,
            load_from_disk=self.load_from_disk,
            setpumpings=self.var.GW_pumping,
            pumpingloc=pumpingloc,
            verbose=self.verbose,
            solver=self.solver,
            binary=self.binary)

        # top of the aquifer at CWatM resolution (constant) for the groundwater depth, top of each layer for gwdepth<n>
        self.top_cwatm = self.grid.to_cwatm(self.layer_boundaries[0], mean=True)
        self.layer_top_cwatm = [self.top_cwatm] + [self.grid.to_cwatm(self.layer_boundaries[n], mean=True)
                                                   for n in range(1, self.nlay)]

        # initializing arrays
        # capillary rise from MODFLOW - from the init file for a restart (used by the soil before MODFLOW runs)
        self.var.capillar = self.var.load_initial('capillar', default=globals.inZero.copy())
        self.var.baseflow = globals.inZero.copy()

        # sumed up groundwater recharge for the number of days
        self.var.sumed_sum_gwRecharge = globals.inZero.copy()
        # seepage scheme: capillary rise from the aquifer of the MODFLOW period (soil.py), extracted in modflow_run
        self.var.sumed_capRiseFromAquifer = globals.inZero.copy()
        self.var.modflow_compteur = 0  # number of the MODFLOW run (water balance check file)
        # percentage discrepancy error of each MODFLOW run: (number of the MODFLOW run, date, error in %)
        self.var.modflowdiscrepancy = []

        # water table (layer 1) at ModFlow resolution and converted into CWatM map; head<n>, gwdepth<n> of each layer
        self.var.modflow_watertable = np.copy(head[0])
        self.var.head = self.grid.to_cwatm(head[0], mean=True)
        self.layer_outputs(head)

        # initial groundwater storage at ModFlow resolution (all layers: water balance check), storage that can be
        # pumped of each layer and as CWatM map (in meter, used in water demand)
        storage = self.storage(head)
        self.storage_total = np.sum(storage, axis=0)
        self.var.groundwater_storage_top_layer = storage[0]
        self.available = self.available_storage(head)
        self.var.groundwater_storage_available = self.grid.to_cwatm(np.sum(self.available, axis=0))
        # per-layer budget (WaterBalance output): storage of each layer at the start, no flows yet
        self.layer_budget(storage)
        # groundwater storage of layer 1 at full capacity (output; before 2026-10 the pumping limit in water demand)
        self.var.gwstorage_full = self.grid.to_cwatm(
            (self.layer_boundaries[0] - self.layer_boundaries[1]) * self.specific_yield[0])

        # permeability need to be translated into CWatM map to compute leakage from surface water bodies
        self.var.permeability = self.grid.to_cwatm(self.permeability[0], mean=True)
        # recharge limit in the soil (Dor's version, soil.py), m/day: vertical permeability of layer 1
        # (permeability_vertical<n>) and a low permeability cover (lowPermabilityCover, m/day, e.g. laterite);
        # the recharge above the limit goes to interflow. None: no limit (as before 2026-10)
        self.var.recharge_limit = None
        if self.permeability_vertical is not None:
            self.var.permeability_vertical = self.grid.to_cwatm(self.permeability_vertical[0], mean=True)
            self.var.recharge_limit = self.var.permeability_vertical
        if 'lowPermabilityCover' in binding:
            cover = loadmap('lowPermabilityCover')
            self.var.recharge_limit = cover if self.var.recharge_limit is None else \
                np.minimum(self.var.recharge_limit, cover)

        # outputs of each MODFLOW run (Dor's version): actual / rejected / exported recharge (m per day), storage of
        # all layers and depth to water (m), groundwater balance per CWatM cell (m3 per MODFLOW period)
        self.var.sum_gwRecharge_actualM = globals.inZero.copy()
        self.var.rejected_recharge_previous_day = self.var.load_initial('rejected_recharge_previous_day',
                                                                        default=globals.inZero.copy())
        self.var.sum_gwRechargeExported = globals.inZero.copy()
        self.var.balance_gw = globals.inZero.copy()
        self.var.groundwater_storage_total = self.grid.to_cwatm(self.storage_total)
        self.var.depth_to_water = self.grid.to_cwatm(self.topography - head[0], mean=True)
        # share of each CWatM cell covered by active ModFlow cells (seepage scheme: saturated share, capillarRise.py)
        self.var.modflow_cover = self.grid.covered_area / self.grid.cwatm_cell_area
        if self.var.modflow_seepage:
            # seepage scheme (soil.py): seepage and capillary rise from the aquifer per land cover with soil (m per day)
            self.var.seepage = [globals.inZero.copy() for _ in range(4)]
            self.var.capRiseFromAquifer = [globals.inZero.copy() for _ in range(4)]
            # seepage pond (m over the land cover; from the init file for a restart, else 0) and its evaporation (m/day)
            self.var.seepagePond = [self.var.load_initial(self.var.coverTypes[No] + '_seepagePond',
                                                          default=globals.inZero.copy(), warn=False) for No in range(4)]
            self.var.seepageEvap = [globals.inZero.copy() for _ in range(4)]
            # pond overflow into the soil and to direct runoff per land cover (cell means: pond2soil, over2river,
            # landcoverType.py) and pond area (share of the soil land covers), soil.py
            self.var.pondToSoil = [globals.inZero.copy() for _ in range(4)]
            # part of pondToSoil into layer 3 (the rest into layer 2), for the water balance of the soil layers
            self.var.pondToSoil3 = [globals.inZero.copy() for _ in range(4)]
            self.var.pondOverflow = [globals.inZero.copy() for _ in range(4)]
            self.var.pond2soil = globals.inZero.copy()
            self.var.over2river = globals.inZero.copy()
            self.var.pondarea = globals.inZero.copy()
            # depth of the seepage pond over the pond area (m, seepage_pond_depth, default 0.1): above it overflow
            # (Tisa 6 years: 0.1 m 24 mm/yr to the rivers, 0.3 m 20, 1 m 16 - the pond then keeps growing)
            self.var.pondDepth = float(cbinding('seepage_pond_depth')) if 'seepage_pond_depth' in binding else 0.1
            self.caprise_limit()

    def caprise_limit(self):
        """
        Seepage scheme: capillary rise from the aquifer into the soil (soil.py) per day at most 10 % of the storage
        of layer 1 per MODFLOW period (m over the CWatM cell) - nearly dry cells give almost nothing (C4 test without
        a limit: MODFLOW diverged, UNWMZ)
        """
        self.var.capRiseAquiferLimit = 0.1 * self.grid.to_cwatm(
            np.nan_to_num(self.var.groundwater_storage_top_layer)) / self.var.modflow_timestep

    def layer_budget(self, storage=None, flows=None, recharge=None, drain=None, pumping=None):
        """
        Per-layer budget for the WaterBalance output, m over the CWatM cell: gwlayer<n>_storage (storage = None: kept),
        and the flows of a MODFLOW run in m per MODFLOW period (flows = None: 0, days without MODFLOW run):
        gwlayer<n>_lateral (from the other cells of the same layer; inside a catchment it cancels, the sum is the
        flow across the border of the catchment), gwlayer<n>_fromAbove / _fromBelow (from the layer above / below),
        gwlayer<n>_pumping (actual pumping, > 0), gwlayer1_recharge (recharge into layer 1, < 0: capillary rise from
        the aquifer), gwlayer1_drain (baseflow + capillary rise); gw_lateral = lateral flow of all layers.
        ModFlow maps (nlay, nrow, ncol) in m over the ModFlow cell -> to_cwatm as the storage, so the balance of
        each layer closes for each CWatM cell
        """
        zero = globals.inZero.copy()
        self.var.gw_lateral = zero.copy()
        for n in range(self.nlay):
            name = 'gwlayer' + str(n + 1) + '_'
            if storage is not None:
                setattr(self.var, name + 'storage', self.grid.to_cwatm(storage[n]))
            for i, term in enumerate(['lateral', 'fromAbove', 'fromBelow']):
                setattr(self.var, name + term, zero.copy() if flows is None else self.grid.to_cwatm(flows[i][n]))
            setattr(self.var, name + 'pumping', zero.copy() if pumping is None else self.grid.to_cwatm(pumping[n]))
            self.var.gw_lateral += getattr(self.var, name + 'lateral')
        self.var.gwlayer1_recharge = zero.copy() if recharge is None else self.grid.to_cwatm(recharge)
        self.var.gwlayer1_drain = zero.copy() if drain is None else self.grid.to_cwatm(drain)

    def water_balance(self, recharge, outflow, storage_change, pumping):
        """
        Water balance error of the aquifer in % of the mean flow (m3 per MODFLOW period): recharge = capillary rise
        + baseflow (outflow) + storage change - pumping (actual pumping < 0)
        """
        # recharge as magnitude: with the seepage scheme the net recharge can be negative (capillary rise from the
        # aquifer) - the mean flow would be near 0 and the error in % too large (Tisa 1990-01-01: -1.46 %)
        mid_gwflow = np.nansum(((np.abs(recharge) + outflow) * self.grid.cell_area - pumping) / 2)
        return np.round(100 * (np.nansum(
            (recharge - outflow - storage_change) * self.grid.cell_area + pumping) / mid_gwflow), 2)

    def write_discrepancy(self):
        """Writing the ModFlow discrepancies above 0.01 % to ModFlow_DiscrepancyError.txt (data_modflow.py)"""
        write_discrepancy_file(cbinding('PathOut') + '/' + 'ModFlow_DiscrepancyError.txt',
                               self.var.modflowdiscrepancy, 0.01)

    def modflow_run(self):
        """
        One MODFLOW run: recharge and pumping of the last MODFLOW period to ModFlow, run, then head, storage,
        capillary rise, baseflow, actual pumping and saturated fraction back to CWatM
        """
        self.var.modflow_compteur += 1

        # converting the CWatM recharge into ModFlow recharge (in meter)
        # we avoid recharge on saturated ModFlow cells, thus CWatM recharge is concentrated  on unsaturated cells
        # (a fully saturated CWatM cell, capriseindex = 1, gets no recharge). Recharge not given to MODFLOW (saturated
        # or dry cells, uncovered part of a CWatM cell) goes the next day to interflow: rejected_recharge_previous_day
        recharge = self.var.sumed_sum_gwRecharge
        if self.var.modflow_seepage:
            # seepage scheme: gross recharge (soil.py subtracts the capillary rise from the aquifer: added again here,
            # extracted below), no concentration and no rejection on saturated ModFlow cells - the percolation is
            # already reduced by the sub-grid saturated share (soil.py); the 0/1 switch caused the 2-day flip-flop
            recharge = self.var.sumed_sum_gwRecharge + self.var.sumed_capRiseFromAquifer
            corrected_recharge = recharge
            groundwater_recharge_modflow = self.grid.to_modflow(corrected_recharge, nanvalue=0)
        else:
            corrected_recharge = np.where(self.var.capriseindex == 1, 0,
                                          self.var.sumed_sum_gwRecharge / (1 - self.var.capriseindex))
            groundwater_recharge_modflow = self.grid.to_modflow(corrected_recharge, nanvalue=0)
            groundwater_recharge_modflow = np.where(self.var.modflow_watertable - self.layer_boundaries[0] >= 0,
                                                    0, groundwater_recharge_modflow)
        # no recharge into cells which are dry in all layers (head at or below the bottom of each layer, Dor's
        # version) - before 2026-10-10 "<": it never applied, the float32 head of a dry cell equals the bottom (UNWMZ
        # 2 layers: 30 dry columns got recharge, MODFLOW diverged with cooley and super_complex)
        groundwater_recharge_modflow = np.where(np.all(self.head_layers <= self.layer_boundaries[1:], axis=0), 0,
                                                groundwater_recharge_modflow)
        # ModFlow cells which get recharge (rejected recharge below: before the export)
        recharged = groundwater_recharge_modflow > 0
        # recharge collected to other groundwater basins (collect_recharge, Dor's version)
        if self.collect_recharge is not None:
            exported = groundwater_recharge_modflow * self.collect_recharge
            groundwater_recharge_modflow = groundwater_recharge_modflow - exported
            self.var.sum_gwRechargeExported = self.grid.to_cwatm(exported) / self.var.modflow_timestep
        if self.var.modflow_seepage:
            # capillary rise from the aquifer (seepage scheme, soil.py) as negative recharge: each CWatM cell takes the
            # share (capillary rise / layer-1 storage) of the layer-1 storage of its ModFlow cells (as the pumping
            # below), so MODFLOW gets exactly the CWatM total; soil.py limits it to 10 % of the storage
            storage1 = np.nan_to_num(np.where(self.modflow.basin, self.var.groundwater_storage_top_layer, 0.))
            available1 = self.grid.to_cwatm(storage1)
            ratio = np.divide(self.var.sumed_capRiseFromAquifer, available1, out=np.zeros_like(available1),
                              where=available1 > 0)
            groundwater_recharge_modflow = groundwater_recharge_modflow - storage1 * self.grid.to_modflow(
                ratio) * self.grid.modflow_covered.reshape(storage1.shape) / self.grid.cell_area
        # actual recharge (m per day) - and the CWatM recharge not given to MODFLOW (saturated or dry ModFlow cells, part
        # of the CWatM cell without active ModFlow cells; not the exported recharge), m per day: CWatM recharge minus
        # what its overlap pairs give to ModFlow cells with recharge. It goes to interflow on the next days
        # (landcoverType.py, runoff_concentration.py). Before 2026-10-11 it was lost (UNWMZ 2 layers 1981: 5.8 % of the
        # recharge) and computed as CWatM recharge - actual recharge (also > 0 where to_modflow only moved recharge)
        self.var.sum_gwRecharge_actualM = self.grid.to_cwatm(groundwater_recharge_modflow) / self.var.modflow_timestep
        given = self.grid.kept_to_cwatm(corrected_recharge, recharged)
        self.var.rejected_recharge_previous_day = np.maximum(
            recharge - given, 0) / self.var.modflow_timestep
        # WaterBalance output: recharge moved between CWatM cells by the grid (m per MODFLOW period, only on MODFLOW
        # days): what MODFLOW gets in the ModFlow cells of a CWatM cell minus what the CWatM cell hands over (recharge -
        # rejected - exported). A ModFlow cell gets the mean recharge of the CWatM cells it overlaps (to_modflow), so a
        # CWatM cell gets more or less back than it gave - 0 over the whole mask (Uganda 1980: 0.002 of 123 mm)
        if self.var.waterbalanceOut:
            ts = self.var.modflow_timestep
            self.var.gw_rechargeMoved = ((self.var.sum_gwRecharge_actualM + self.var.rejected_recharge_previous_day
                                          + self.var.sum_gwRechargeExported) * ts - self.var.sumed_sum_gwRecharge)
        # give the information to ModFlow
        self.modflow.set_recharge(groundwater_recharge_modflow)

        # pumping: groundwater abstraction of the CWatM water demand module, given to ModFlow in m3 per MODFLOW period
        # and < 0: each CWatM cell takes the share ratio (abstraction / available storage, <= 1) of the available
        # storage of its ModFlow cells (overlap area of the pairs, as in to_cwatm), so ModFlow gets exactly the CWatM
        # abstraction; split over the layers in proportion to their available storage. Before 2026-10-10 (Dor's
        # weights min(available of the ModFlow cell / available of the CWatM cell, 1)) ModFlow got only 78 % (UNWMZ)
        # - 81 % (Bhima) of the CWatM abstraction - the rest was used in CWatM but not taken from the aquifer
        if self.var.GW_pumping:
            ratio = np.divide(self.var.modfPumpingM, self.var.groundwater_storage_available,
                              out=np.zeros_like(self.var.modfPumpingM, dtype=np.float64),
                              where=self.var.groundwater_storage_available > 0)
            available = np.sum(self.available, axis=0)
            abstraction = - available * self.grid.to_modflow(ratio) * self.grid.modflow_covered.reshape(available.shape)
            share = np.divide(self.available, available, out=np.zeros_like(self.available), where=available > 0)
            self.modflow.set_groundwater_abstraction(abstraction * share)

        # drains of the main rivers with the water depth of the river (adjust_drainage_by_river)
        if self.drain_elevation is not None and self.adjust_drainage:
            self.modflow.set_drainage(self.river_drains())

        # running ModFlow
        self.modflow.step()
        # outer iterations at MXITER without convergence (before 2026-10-11 only noticed if the head was nan, Error 152)
        if not self.modflow.converged:
            print(CWATMWarning("Warning: MODFLOW did not converge on " + dateVar['currDatestr'] + " (MODFLOW run " +
                               str(self.var.modflow_compteur) + ") - results of this step are not reliable; use "
                               "another modflow_solver (cooley, complex, super_complex) or a smaller modflow_timestep"))

        # extracting the new simulated hydraulic head of each layer (nlay, nrow, ncol)
        head = self.modflow.decompress(self.modflow.head.astype(np.float32)).reshape(
            (self.nlay, self.grid.nrow, self.grid.ncol))
        # MODFLOW did not converge: head not a number or unrealistic (e.g. 2e66 m) in an active cell
        wrong = ~np.isfinite(head[:, self.modflow.basin]) | (np.abs(head[:, self.modflow.basin]) > 1e6)
        if wrong.any():
            msg = "Error 152: MODFLOW gives a wrong head (not a number or > 1e6 m) in " + str(int(wrong.sum()))
            msg += " ModFlow cells (layer " + ", ".join(str(n + 1) for n in np.unique(np.nonzero(wrong)[0]))
            msg += ") on " + dateVar['currDatestr'] + " - the MODFLOW solver did not converge\n"
            msg += "Use another solver (modflow_solver = cooley, complex or super_complex), a smaller modflow_timestep "
            msg += "or check the aquifer properties (thickness<n>, permeability<n>, pumping)\n"
            raise CWATMError(msg)

        # groundwater storage of all layers at ModFlow resolution (in meter) - the previous one for the water balance
        storage_total0 = self.storage_total
        storage = self.storage(head)
        self.storage_total = np.sum(storage, axis=0)
        self.var.groundwater_storage_total = self.grid.to_cwatm(self.storage_total)
        self.head_layers = head
        # storage of layer 1 (output), storage that can be pumped (all layers, wells) as CWatM map (in meter)
        self.var.groundwater_storage_top_layer = storage[0]
        if self.var.modflow_seepage:
            self.caprise_limit()
        self.available = self.available_storage(head)
        self.var.groundwater_storage_available = self.grid.to_cwatm(np.sum(self.available, axis=0))

        # groundwater outflow = drain flow of MODFLOW (DRN: conductance = permeability * cell area * timestep,
        # elevation = top), in m/day per ModFlow cell - before 2026-10 recomputed from the float32 head
        groundwater_outflow = self.modflow.decompress(
            -self.modflow.drainage / (self.grid.cell_area * self.var.modflow_timestep))
        groundwater_outflow[~self.modflow.basin] = 0
        # saturated ModFlow cells: for the next step, it will prevent recharge where ModFlow cells are saturated,
        # even if there is no capillary rise (where h==topo)
        groundwater_outflow2 = np.where(head[0] - self.layer_boundaries[0] >= 0, 1.0, 0.0)

        # capillary rise and baseflow from groundwater are allocated in function of the river percentage of each
        # ModFlow cell (still in ModFlow coordinates)
        capillar = groundwater_outflow * (1 - self.var.channel_ratio)
        baseflow = groundwater_outflow * self.var.channel_ratio

        # actual ModFlow pumping in m3 (MODFLOW reduces the pumping if a cell is almost dry) - water cycle output
        # (modfPumpingM_actual) and water balance check; wells of all layers summed per ModFlow cell (wells_index)
        actual_pumping_modflow_array = 0
        if self.var.GW_pumping:
            actual_pumping = self.modflow.actualwell_rate.astype(np.float32)
            actual_pumping_modflow_array = np.bincount(
                self.var.wells_index, weights=actual_pumping,
                minlength=self.grid.nrow * self.grid.ncol).reshape((self.grid.nrow, self.grid.ncol))
            # m3 per ModFlow cell -> m over its part inside the mask (the pumping was set for this part), so the CWatM
            # total is MODFLOW's actual pumping (before 2026-10-12 / cell_area: border cells lost, Tisa -0.7 %)
            covered = self.grid.modflow_covered.reshape(actual_pumping_modflow_array.shape)
            self.var.modfPumpingM_actual = - self.grid.to_cwatm(np.divide(
                actual_pumping_modflow_array, covered, out=np.zeros_like(covered), where=covered > 0))

        # MODFLOW budget error in % - the solver can report convergence with a large budget error (UNWMZ with the
        # COMPLEX default outer_dvclose 0.1 m: up to -187 %); saved for ModFlow_DiscrepancyError.txt (writeModflowError)
        error = self.water_balance(groundwater_recharge_modflow, (capillar + baseflow) * self.var.modflow_timestep,
                                   self.storage_total - storage_total0, actual_pumping_modflow_array)
        if abs(error) > 1:
            print(CWATMWarning("Warning: MODFLOW budget error of " + str(error) + " % on " + dateVar['currDatestr'] +
                               " (MODFLOW run " + str(self.var.modflow_compteur) + ") - results of this step are not "
                               "reliable; use a smaller modflow_timestep or another modflow_solver"))
        if self.var.writeerror:
            self.var.modflowdiscrepancy.append((self.var.modflow_compteur, dateVar['currDatestr'], error))

        # converting flows from ModFlow to CWatM domain
        self.var.capillar = self.grid.to_cwatm(capillar)
        baseflow = baseflow.astype('float64')  # required for runoff concentration (lib2.runoffConc)
        self.var.baseflow = self.grid.to_cwatm(baseflow)

        # per-layer budget of this MODFLOW run (only if the WaterBalance output is written), m per ModFlow cell:
        # cell-to-cell flows of MODFLOW, actual pumping of the wells of each layer, recharge and drain flow
        if self.var.waterbalanceOut:
            shape = (self.nlay, self.grid.nrow, self.grid.ncol)
            flows = [self.modflow.decompress(f).reshape(shape) / self.grid.cell_area
                     for f in self.modflow.layer_flows()]
            pumping = None
            if self.var.GW_pumping:
                pumping = np.bincount(self.wells_layer * self.grid.nrow * self.grid.ncol + self.var.wells_index,
                                      weights=-actual_pumping, minlength=int(np.prod(shape))).reshape(shape)
                pumping = pumping / self.grid.cell_area
            self.layer_budget(storage, flows, groundwater_recharge_modflow,
                              groundwater_outflow * self.var.modflow_timestep, pumping)

        # groundwater balance per CWatM cell (m3 per MODFLOW period, Dor's version): recharge - capillary rise -
        # baseflow + actual pumping (< 0) - storage change of all layers
        balance = (groundwater_recharge_modflow - (capillar + baseflow) * self.var.modflow_timestep
                   - (self.storage_total - storage_total0) + actual_pumping_modflow_array / self.grid.cell_area)
        self.var.balance_gw = self.grid.to_cwatm(balance) * self.var.cellArea
        self.var.depth_to_water = self.grid.to_cwatm(self.topography - head[0], mean=True)

        # fraction of saturated ModFlow cells in each CWatM cell (water table >= top of the aquifer)
        self.var.capriseindex = self.grid.fraction_to_cwatm(groundwater_outflow2)

        # updating water table maps both at CWatM and ModFlow resolution
        self.var.head = self.grid.to_cwatm(head[0], mean=True)
        self.layer_outputs(head)

        self.var.modflow_watertable = np.copy(head[0])

        # Re-initializing the weekly (orbi-weekly, or monthly...) sum of groundwater pumping
        self.var.modfPumpingM = globals.inZero.copy()
        # Re-initializing the sum of recharge for the next MODFLOW run (as the pumping above)
        self.var.sumed_sum_gwRecharge = 0
        self.var.sumed_capRiseFromAquifer = 0

    def dynamic(self):
        """
        Execute dynamic groundwater calculations for current time step.

        Handles groundwater recharge input, pumping rates, runs MODFLOW simulation,
        and processes results for feedback to CWatM. Manages temporal coupling
        and data exchange between surface and groundwater models.
        """

        # actual pumping of MODFLOW: only on MODFLOW days (water cycle output)
        self.var.modfPumpingM_actual = globals.inZero.copy()
        # per-layer flows and recharge moved by the grid (WaterBalance output): only on MODFLOW days (modflow_run), else 0
        if self.var.waterbalanceOut:
            self.layer_budget()
            self.var.gw_rechargeMoved = globals.inZero.copy()
        # capillary rise from MODFLOW used today by the land (soil, seepage pond, sealed and water -> runoff): the
        # value of the last MODFLOW run, before today's run (WaterCycle output)
        self.var.capillarUsed = self.var.capillar

        # Adding recharge of the day to the weekly (or bi-weekly, or monthly...) sum - the sum starts again after
        # each MODFLOW run (at the end of modflow_run)
        self.var.sumed_sum_gwRecharge = self.var.sumed_sum_gwRecharge + self.var.sum_gwRecharge
        if self.var.modflow_seepage:
            self.var.sumed_capRiseFromAquifer = self.var.sumed_capRiseFromAquifer + self.var.sum_capRiseFromAquifer

        # Every modflow timestep (e.g. 7,14,30... days): each MODFLOW run gets the recharge and pumping of all days
        # of its period; before the first run (days 1 to modflow_timestep - 1): head and storage of the start,
        # capillary rise from the init file (or 0), baseflow 0. Before 2026-10-11 also on day 1: the first run had
        # one day of recharge and pumping for a step of modflow_timestep days, the second modflow_timestep - 1 days
        if (dateVar['curr'] % self.var.modflow_timestep) == 0:
            self.modflow_run()

        # WaterCycle output (water balance check): coupling buffer between CWatM and MODFLOW in m over the CWatM cell -
        # water which left one model and is not yet in the other: recharge and pumping of the days since the last
        # MODFLOW run (not yet given to MODFLOW), capillary rise and rejected recharge of the last run for the
        # remaining days until the next run (soil and interflow use them each day before MODFLOW), baseflow of the
        # last run for the remaining days (runoff concentration uses it each day after MODFLOW)
        remain = self.var.modflow_timestep - dateVar['curr'] % self.var.modflow_timestep
        self.var.modflow_buffer = (self.var.sumed_sum_gwRecharge - self.var.modfPumpingM
                                   + remain * (self.var.capillar + self.var.rejected_recharge_previous_day)
                                   + (remain - 1) * self.var.baseflow)
        # recharge collected to other groundwater basins (collect_recharge): leaves on MODFLOW days only (m per day)
        if dateVar['curr'] % self.var.modflow_timestep == 0:
            self.var.gwRechargeExported_day = self.var.sum_gwRechargeExported * self.var.modflow_timestep
        else:
            self.var.gwRechargeExported_day = globals.inZero.copy()

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
