import numpy as np

import cwatm.hydrological_modules.pySnowClim.constants as const

from cwatm.hydrological_modules.pySnowClim.calcPhase import calc_phase
from cwatm.hydrological_modules.pySnowClim.calcFreshSnowDensity import calc_fresh_snow_density
from cwatm.hydrological_modules.pySnowClim.calcTurbulentFluxes import calc_turbulent_fluxes
from cwatm.hydrological_modules.pySnowClim.calcLongwave import calc_longwave
from cwatm.hydrological_modules.pySnowClim.calcEnergyToCC import calc_energy_to_cc
from cwatm.hydrological_modules.pySnowClim.calcEnergyToRefreezing import calc_energy_to_refreezing
from cwatm.hydrological_modules.pySnowClim.calcEnergyToMelt import calc_energy_to_melt
from cwatm.hydrological_modules.pySnowClim.calcSublimation import calc_sublimation

from cwatm.hydrological_modules.pySnowClim.SnowModelVariables import SnowModelVariables
from cwatm.hydrological_modules.pySnowClim.PrecipitationProperties import PrecipitationProperties
from cwatm.hydrological_modules.pySnowClim.SnowpackVariables import Snowpack

from tqdm import tqdm
import time

def _prepare_outputs(model_vars, precip):
    """
    Prepare outputs by scaling model variables with appropriate constants.

    Args:
    -----
    - model_vars: object
        An object containing model variables such as SnowWaterEq, SnowDepth, etc.
    - precip: Class
        Propreties of precipitation, including swe.

    Returns:
    --------
    Updated model_vars with scaled values for output.
    """
    # Scale model variables by WATERDENS or other units where applicable
    model_vars.SnowWaterEq *= const.WATERDENS
    model_vars.SnowfallWaterEq = precip.sfe * const.WATERDENS
    model_vars.SnowMelt *= const.WATERDENS
    model_vars.Sublimation *= const.WATERDENS
    model_vars.Condensation *= const.WATERDENS
    model_vars.SnowDepth *= 1000  # Convert to mm
    model_vars.Runoff *= const.WATERDENS
    model_vars.RaininSnow *= const.WATERDENS
    model_vars.RefrozenWater *= const.WATERDENS
    model_vars.PackWater *= const.WATERDENS

    return model_vars


def _perform_precipitation_operations(forcings_data, parameters):
    """
    Perform precipitation phase calculations and adjust snow and rain values.

    Args:
    -----
    - forcings_data: dict
        A dictionary containing forcing data, including 'tavg' (temperature) and 'relhum' (relative humidity).
    - parameters: dict
        Model parameters, including 'hours_in_ts' (hours per time step).

    Returns:
    --------
    - rainfall: np.ndarray
        Rainfall amount after phase calculation.
    - SnowfallWaterEq: np.ndarray
        Snowfall equivalent after phase calculation.
    - newsnowdensity: np.ndarray
        Fresh snow density based on the average temperature.
    """
    # Calculate phase (snow or rain fraction)
    passnow = calc_phase(forcings_data['tavg'], forcings_data['relhum'])

    # Separate rain and snow components of precipitation
    rainfall = forcings_data['ppt'] * (1 - passnow)
    SnowfallWaterEq = forcings_data['ppt'] * passnow

    # Threshold for snowfall equivalent and adjust rain accordingly
    threshold = 0.0001 * parameters['hours_in_ts']
    SnowfallWaterEq[SnowfallWaterEq < threshold] = 0
    rainfall[SnowfallWaterEq <
             threshold] = forcings_data['ppt'][SnowfallWaterEq < threshold]

    # Calculate fresh snow density based on temperature
    newsnowdensity = calc_fresh_snow_density(forcings_data['tavg'])

    # Update new snow temperature where there is new snow
    newsnowtemp = np.where(SnowfallWaterEq > 0, np.minimum(
        0, forcings_data['tdmean']), 0)

    # Calculate the cold content of the snowfall
    snowfallcc = const.WATERDENS * const.CI * SnowfallWaterEq * newsnowtemp
    precip = PrecipitationProperties(rainfall, SnowfallWaterEq, newsnowdensity,
                                     snowfallcc)
    return precip


def _process_forcings_and_energy(index, forcings_data, parameters,
                                 snow_model_instances):
    """
    Processes input forcings and smooths energy calculations.

    Parameters:
    - index: int, index of the current timestep.
    - forcings_data: dict, containing forcings data for the model.
    - parameters: dict, containing model parameters.
    - snow_model_instances: list, previous instances of SnowModelVariables containing energy data.

    Returns:
    - input_forcings: dict, forcings data for the current timestep.
    - snow_vars: SnowModelVariables, initialized snow model variables for current timestep.
    - smoothed_energy: ndarray, energy values smoothed over specified hours.
    """
    # Extract current timestep forcings
    if forcings_data['forcings']['huss'].ndim > 2:
        input_forcings = {key: value[index, :]
                          for key, value in forcings_data['forcings'].items()}
    else:
        input_forcings = {key: value for key, value in forcings_data['forcings'].items()}
        #input_forcings = {key: value[index, np.newaxis]
        #                   for key, value in forcings_data['forcings'].items()}

    # Initialize snow model variables for this timestep
    domain_size = _define_size(forcings_data)
    snow_vars = SnowModelVariables(domain_size)

    smoothed_energy = None
    if parameters['smooth_time_steps'] > 0:
        if index > parameters['smooth_time_steps']:
            smoothed_energy = np.full(
                (parameters['smooth_time_steps'], *domain_size), np.nan)
            for l in range(parameters['smooth_time_steps']):
                smoothed_energy[l, :,:] = snow_model_instances[index - l - 1].Energy
        else:
            if index > 0:
                smoothed_energy = np.full((index+1, *domain_size), np.nan)
                for l in range(index):
                    smoothed_energy[l, :,:] = snow_model_instances[l].Energy

    # Calculate new precipitation components
    precip = _perform_precipitation_operations(input_forcings, parameters)

    return input_forcings, snow_vars, smoothed_energy, precip


def _calculate_energy_fluxes(snow_vars, parameters, input_forcings, newrain,
                             lastalbedo):
    """
    Calculate energy fluxes at each timestep, including turbulent, rain, solar, longwave, and ground heat fluxes.

    Parameters:
    - exist_snow: Boolean array, indicating locations with existing snow.
    - parameters: dict, contains model parameters like 'G' and 'snow_emis'.
    - input_forcings: dict, contains the forcing data for this timestep.
    - lastsnowtemp: ndarray, surface temperature of the last snowpack.
    - newrain: ndarray, rainfall over snowpack.
    - lastalbedo: ndarray, albedo values from the previous timestep.

    Returns:
    - lastenergy: ndarray, net downward energy flux into the snow surface.
    """
    var_list = ['Q_sensible', 'E', 'Q_latent', 'Q_precip', 'SW_up', 'SW_down', 'LW_down',
                'LW_up']
    energy_var = {name: np.zeros_like(snow_vars.ExistSnow, dtype=np.float32) for name in var_list}
    sec_in_ts = parameters['hours_in_ts'] * const.HR_2_SECS

    # --- Calculate turbulent heat fluxes (kJ/m2/timestep) ---
    has_snow_and_wind = np.logical_and(
        snow_vars.ExistSnow, input_forcings['vs'] > 0)
    H, E, EV = calc_turbulent_fluxes(
        parameters, input_forcings['vs'][has_snow_and_wind], snow_vars.SnowTemp[has_snow_and_wind],
        input_forcings['tavg'][has_snow_and_wind], input_forcings['psfc'][has_snow_and_wind],
        input_forcings['huss'][has_snow_and_wind], sec_in_ts
    )
    energy_var['Q_sensible'][has_snow_and_wind] = H
    energy_var['E'][has_snow_and_wind] = E
    energy_var['Q_latent'][has_snow_and_wind] = EV

    # --- Rain heat flux into snowpack (kJ/m2/timestep) ---
    energy_var['Q_precip'][snow_vars.ExistSnow] = const.CW * const.WATERDENS * \
        np.maximum(
            0, input_forcings['tdmean'][snow_vars.ExistSnow]) * newrain[snow_vars.ExistSnow]

    # --- Net downward solar flux at surface (kJ/m2/timestep) ---
    energy_var['SW_up'][snow_vars.ExistSnow] = input_forcings['solar'][snow_vars.ExistSnow] * \
        lastalbedo[snow_vars.ExistSnow]
    energy_var['SW_down'][snow_vars.ExistSnow] = input_forcings['solar'][snow_vars.ExistSnow]

    # --- Longwave flux up from snow surface (kJ/m2/timestep) ---
    energy_var['LW_down'][snow_vars.ExistSnow] = input_forcings['lrad'][snow_vars.ExistSnow]
    energy_var['LW_up'][snow_vars.ExistSnow] = calc_longwave(
        parameters['snow_emis'], snow_vars.SnowTemp[snow_vars.ExistSnow],
        input_forcings['lrad'][snow_vars.ExistSnow], sec_in_ts)

    # --- Ground heat flux (kJ/m2/timestep) ---
    energy_var['Gf'] = np.where(
        snow_vars.ExistSnow, parameters['G'] * sec_in_ts, 0)

    return energy_var


def _apply_cold_content_tax(lastpackcc, parameters, previous_energy, lastenergy):
    """
    Apply cold content tax to the energy flux based on temperature parameters.

    Parameters:
    - lastpackcc (np.ndarray): The current cold content in the snowpack.
    - parameters (dict): Dictionary containing temperature and tax parameters,
                         including 'Tstart', 'Tadd', and 'maxtax'.
    - previous_energy (np.ndarray): The smoothed energy values.

    Returns:
    - np.ndarray: Updated energy values with the cold content tax applied.
    """
    # Calculate the tax based on the cold content
    tax = (lastpackcc - parameters['Tstart']) / \
        parameters['Tadd'] * parameters['maxtax']
    # Limit tax to be within 0 and maxtax
    tax = np.clip(tax, 0, parameters['maxtax'])

    if parameters['smooth_time_steps'] > 1 and previous_energy is not None:
        previous_energy[-1, :] = lastenergy
        smoothed_energy = np.nanmean(previous_energy, axis=0)
    else:
        smoothed_energy = lastenergy

    # Apply tax where energy is negative
    negative_energy = smoothed_energy < 0
    if np.any(negative_energy):
        smoothed_energy[negative_energy] *= (1 - tax[negative_energy])

    return smoothed_energy


def _distribute_energy_to_snowpack(taxed_last_energy, snow_vars,  snowpack,
                                   input_forcings, parameters):
    """
    Distributes the available energy to the snowpack components: cold content, refreezing, and melting.

    Args:
        taxed_last_energy (np.ndarray): Taxed energy available for distribution.
        snow_vars (object): Snow variables object to update (e.g., CCenergy, SnowMelt, etc.).
        snowpack (object): Snowpack variables class (e.g., lastsnowdepth, packsnowdensity, etc.).
        input_forcings (dict): Input meteorological forcings (e.g., temperature, tavg).
        parameters (dict): Parameters for snowpack calculations (e.g., snow density, melt coefficients).

    Returns:
        Updated snow_vars object, and modified lastpackcc, taxed_last_energy, lastpacktemp, lastpackwater, and lastswe.
    """
    # TODO: snow_vars should not be updated here. Ideally several variables should be returned
    # to the run_snowclim_model function and updated there.

    # 1. Energy goes to cold content
    snowpack.lastpackcc, taxed_last_energy, snow_vars.CCenergy = calc_energy_to_cc(
        snowpack.lastpackcc.copy(), taxed_last_energy.copy(), snow_vars.CCenergy.copy())

    # # Temperature adjustment for snow with positive SWE
    snowpack.adjust_temp_snow()
    snowpack.apply_temperature_instability_correction(input_forcings)

    # 2. Energy goes to refreezing
    lastpackwater, lastswe, lastpackcc, packsnowdensity, snow_vars.RefrozenWater = calc_energy_to_refreezing(
        snowpack.lastpackwater.copy(), snowpack.lastswe.copy(), snowpack.lastpackcc.copy(),
        snowpack.lastsnowdepth.copy(), snow_vars.RefrozenWater.copy(), snowpack.packsnowdensity.copy())
    snowpack.lastpackcc = lastpackcc.copy()

    # 3. Energy goes to melting
    snow_vars.SnowMelt, snow_vars.MeltEnergy, lastpackwater, lastswe, lastsnowdepth, lastenergy = calc_energy_to_melt(
        lastswe, snowpack.lastsnowdepth.copy(), packsnowdensity, taxed_last_energy,
        lastpackwater, snow_vars.SnowMelt.copy(), snow_vars.MeltEnergy.copy())

    snowpack.lastswe = lastswe.copy()
    snowpack.lastsnowdepth = lastsnowdepth.copy()
    snowpack.packsnowdensity = packsnowdensity.copy()
    snowpack.lastpackwater = lastpackwater.copy()

    snowpack.update_snowpack_water(snow_vars.ExistSnow, parameters['lw_max'])


def _process_snowpack(input_forcings, parameters, snow_vars, precip, snowpack, coords,
                      time_value, previous_energy):
    """
    Processes snowpack state, energy fluxes, and updates sublimation, condensation,
    and snow variables after precipitation and energy adjustments.
    """
    snowpack.update_snowpack_state(input_forcings, parameters, snow_vars, precip, coords,
                                   time_value)

    energy_var = _calculate_energy_fluxes(snow_vars, parameters, input_forcings,
                                          precip.rain, snowpack.lastalbedo)

    # --- Downward net energy flux into snow surface (kJ/m2/timestep) ---
    lastenergy = energy_var['SW_down'] - energy_var['SW_up']
    lastenergy += energy_var['LW_down'] - energy_var['LW_up']
    lastenergy += energy_var['Q_sensible'] + energy_var['Q_latent']
    lastenergy += energy_var['Gf'] + energy_var['Q_precip']

    # copying values from the dict to the object
    for key, value in energy_var.items():
        if hasattr(snow_vars, key):
            setattr(snow_vars, key, value)

    snow_vars.Energy = lastenergy.copy()

    taxed_last_energy = _apply_cold_content_tax(
        snowpack.lastpackcc, parameters, previous_energy, lastenergy)

    _distribute_energy_to_snowpack(
        taxed_last_energy, snow_vars, snowpack, input_forcings, parameters)

    # --- Sublimation ---
    a = snowpack.lastsnowdepth > 0
    if np.any(a):
        sublimation, condensation = calc_sublimation(energy_var['E'], snowpack, snow_vars,
                                                     parameters['snow_dens_default'])
        snow_vars.Sublimation = sublimation.copy()
        snow_vars.Condensation = condensation.copy()

    snowpack.update_class_no_snow(parameters)
    snowpack.adjust_temp_snow()
    snowpack.apply_temperature_instability_correction(input_forcings)

    return lastenergy


def _snowpack_to_snowmodel(model_vars, snowpack):
    """
    Copy outputs of the snowpack class to snowmodel class.

    Args:
    -----
    model_vars(object): An object containing model variables such as SnowWaterEq, SnowDepth, etc.
    snowpack (object): An object snowpack variables.

    Returns:
    --------
    Updated model_vars with scaled values for output.
    """
    # Update outputs
    model_vars.PackWater = snowpack.lastpackwater.copy()
    model_vars.Runoff = snowpack.runoff.copy()
    model_vars.RaininSnow = snowpack.rain_in_snow.copy()
    model_vars.Albedo[model_vars.ExistSnow] = snowpack.lastalbedo[model_vars.ExistSnow].copy()
    model_vars.PackCC = snowpack.lastpackcc.copy()
    model_vars.SnowDepth = snowpack.lastsnowdepth.copy()
    model_vars.SnowWaterEq = snowpack.lastswe.copy()
    b = snowpack.lastswe > 0
    if np.any(b):
        model_vars.SnowDensity[b] = snowpack.packsnowdensity[b].copy()

    return model_vars


def _run_snowclim_step(snow_vars, snowpack, precip, input_forcings, parameters, coords,
                       time_value, previous_energy):

    snowpack.calculate_new_snow_temperature_and_cold_content(
        precip, input_forcings)

    # If there is snow on the ground, run the model
    exist_snow = (precip.sfe + snowpack.lastswe) > 0
    if np.sum(exist_snow) > 0:
        snow_vars.ExistSnow = exist_snow.copy()
        # Set snow surface temperature
        snow_vars.SnowTemp[exist_snow] = np.minimum(input_forcings['tdmean'] + parameters['Ts_add'],
                                                    0)[exist_snow]

        # summer boost melt for snow towers
        if time_value[1] >= parameters['downward_radiation_start_month'] and time_value[1] <= parameters['downward_radiation_end_month']:
            is_snow_tower = (precip.sfe + snowpack.lastswe) > parameters['max_swe_height']
            if np.any(is_snow_tower):
                input_forcings['lrad'][is_snow_tower] = input_forcings['lrad'][is_snow_tower]*parameters['downward_radiation_factor']

        lastenergy = _process_snowpack(
            input_forcings, parameters, snow_vars, precip, snowpack, coords,
            time_value, previous_energy)

        snow_vars = _snowpack_to_snowmodel(snow_vars, snowpack)
        snowpack.initialize_snowpack_runoff()
    else:
        snowpack.initialize_snowpack_base()

    return snowpack, snow_vars


def _define_size(forcings_data):

    if forcings_data['forcings']['huss'].ndim > 2:
        domain_size = (forcings_data['coords']['lat'].shape[0],
                       forcings_data['coords']['lon'].size)
    else:
        #domain_size = (1,forcings_data['coords']['lat'].size)
        domain_size = (forcings_data['coords']['lat'].size)

    return domain_size


def run_snowclim_model(forcings_data, parameters):
    """
    Simulates snow accumulation, melting, sublimation, condensation, and energy balance
    over a given time period based on meteorological inputs.

    Parameters:
        forcings_data (dict): meteorological inputs.
        parameters (dict): Parameters required by the model.

    Returns:
        snow_model_instances (list): list with the results based on time.
    """
    # number of seconds in each time step
    coords = forcings_data['coords']

    domain_size = _define_size(forcings_data)
    snow_model_instances = [None] * len(forcings_data['coords']['time_sliced'])
    snowpack = Snowpack(domain_size, parameters)

    for i, time_value in enumerate(forcings_data['coords']['time_sliced']):#tqdm(forcings_data['coords']['time_sliced'])):
        # loading necessary data to run the model
        input_forcings, snow_vars, previous_energy, precip = _process_forcings_and_energy(
            i, forcings_data, parameters, snow_model_instances)

        # Reset to 0 snow at the specified time of year
        if time_value[1] == parameters['snowoff_month'] and time_value[2] == parameters['snowoff_day']:
            snowpack = Snowpack(domain_size, parameters)

        snowpack, snow_vars = _run_snowclim_step(
            snow_vars, snowpack, precip, input_forcings, parameters, coords, time_value, previous_energy)
        snow_vars.CCsnowfall = precip.snowfallcc.copy()
        snow_model_instances[i] = _prepare_outputs(snow_vars, precip)

    return snow_model_instances
