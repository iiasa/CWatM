"""
This module contains functions to calculate snow albedo using different snow models:
Essery et al. (2013), the Utah Snow Model (Tarboton), and the VIC model. These models
compute the albedo based on snow properties such as snow depth, snow water equivalent
(SWE), snow temperature, and snow age, along with environmental conditions like latitude,
ground albedo, and time of year.

Main Function:
--------------
- calc_albedo: The central function to compute snow albedo based on the selected model option.

Albedo Calculation Models:
---------------------------
1. Essery et al. (2013) Option 1:
   - Calculates snow albedo based on fresh snow, cold snow, and melting snow conditions
     using equations from Essery et al. (2013), with parameter values from Douville et al. (1995).

2. Utah Snow Model (Tarboton):
   - Albedo is calculated using equations adapted from the Utah Energy Balance (UEB) model.
   - Albedo is a function of snow age, temperature, and new snow depth, taking into account
     latitude, month, and day.

3. VIC Model:
   - The VIC (Variable Infiltration Capacity) model calculates albedo for new snow, cold-aged snow,
     and melting snow conditions, using snow depth and snow age. The model was adapted from the
     VIC snow utility.
"""
import numpy as np
import cwatm.hydrological_modules.pySnowClim.constants as const
from cwatm.hydrological_modules.pySnowClim.calcInclinationAngle import calc_inclination_angle

def calc_albedo(parameters, last_albedo, new_snow_depth,
                last_snow_depth, new_swe, last_swe, last_snow_temp, lat,
                month, day, snow_age, last_pack_cc, sec_in_ts):
    """
    Calculate the snow albedo based on the selected model option and various snow and environmental parameters.

    Parameters:
    -----------
    parameters: dict
        A dictionary of model parameters, including 'ground_albedo' and 'albedo_option'.
    last_albedo : ndarray
        Previous timestep snow albedo values.
    new_snow_depth : ndarray
        Depth of newly fallen snow.
    last_snow_depth : ndarray
        Depth of snow from the previous timestep.
    new_swe : ndarray
        Snow Water Equivalent (SWE) of new snow.
    last_swe : ndarray
        SWE from the previous timestep.
    last_snow_temp : ndarray
        Snow temperature from the previous timestep.
    lat: np.ndarray
        Array of latitudes.
    month : int
        Month of the current timestep (1-12).
    day : int
        Day of the current timestep (1-31).
    snow_age : ndarray
        Age of the snowpack.
    last_pack_cc : ndarray
        Cold content of the snowpack from the previous timestep.
    sec_in_ts : int
        Number of seconds in the current timestep.

    Returns:
    --------
    albedo : ndarray
        Calculated snow albedo for each grid point.
    snow_age : ndarray
        Updated snow age for each grid point.
    """
    if parameters['albedo_option'] == 1:
        albedo = _calc_albedo_essery_opt1(last_albedo, last_snow_temp, new_swe, last_swe,
                                          parameters, sec_in_ts)
    elif parameters['albedo_option'] == 2:
        albedo, snow_age = _calc_albedo_tarboton(last_snow_temp + const.K_2_C, snow_age,
                                                 new_snow_depth, lat, month, day, last_swe,
                                                 parameters, sec_in_ts)
    elif parameters['albedo_option'] == 3:
        albedo, snow_age = _calc_albedo_vic(new_snow_depth, snow_age, parameters,
                                            last_snow_depth, last_albedo, sec_in_ts,
                                            last_pack_cc)

    # Adjust albedo if total snow depth is low (< 0.1 m)
    z = last_snow_depth
    f = z < 0.1
    r = (1 - z[f] / 0.1) * np.exp(-z[f] / 0.2)
    r = np.minimum(r, 1)
    albedo[f] = r * parameters['ground_albedo'] + (1 - r) * albedo[f]

    # Ensure albedo is real and within range
    albedo = np.real(albedo)
    albedo = np.clip(albedo, 0, parameters['max_albedo'])

    return albedo, snow_age


def _calc_albedo_essery_opt1(last_albedo, last_snow_temp, new_swe, last_swe, parameters,
                             sec_in_ts):
    """
    Calculate snow albedo based on Essery et al. (2013) option 1.

    Parameters are similar to those in `calc_albedo`.

    Returns:
    --------
    albedo : ndarray
        Calculated snow albedo.
    """
    min_albedo = 0.5  # minimum snow albedo
    So = 10  # kg/m² ('critical SWE')
    Ta = 1e7  # s
    Tm = 3.6e5  # s

    dt = sec_in_ts
    Sf = new_swe * const.WATERDENS / dt  # snow fall rate (kg m-2 s-1)

    albedo = np.zeros_like(last_albedo)

    # No snow on the ground
    b = np.isclose(last_swe, 0, atol=1e-8)
    albedo[b] = parameters['ground_albedo']

    # Fresh snow
    b = new_swe > 0
    albedo[b] = last_albedo[b] + (parameters['max_albedo'] -
                                  last_albedo[b]) * ((Sf[b] * dt) / So)

    # Cold snow
    only_last_swe = np.logical_and(last_swe > 0,
                                    np.isclose(new_swe, 0, atol=1e-8))
    b = np.logical_and(only_last_swe, last_snow_temp < -0.5)
    albedo[b] = last_albedo[b] - dt / Ta

    # Melting snow
    b = np.logical_and(only_last_swe, last_snow_temp >= -0.5)
    albedo[b] = (last_albedo[b] - min_albedo) * np.exp(-dt / Tm) + min_albedo

    albedo = np.clip(albedo, min_albedo, parameters['max_albedo'])

    return albedo


def _calc_albedo_vic(new_snow_depth, snow_age, parameters, last_snow_depth,
                     last_albedo, sec_in_ts, last_pack_cc):
    """
    Calculate snow albedo based on the VIC model.

    Parameters are similar to those in `calc_albedo`.

    Returns:
    --------
    albedo : ndarray
        Calculated snow albedo.
    snow_age : ndarray
        Updated snow age.
    """
    SNOW_NEW_SNOW_ALB = parameters['max_albedo']
    SNOW_ALB_ACCUM_A = 0.94
    SNOW_ALB_ACCUM_B = 0.58
    SNOW_ALB_THAW_A = 0.82
    SNOW_ALB_THAW_B = 0.46
    sec_per_day = 24 * 60 * 60

    albedo = np.copy(last_albedo)

    # New snow case
    b = (new_snow_depth > 0.01) & (last_pack_cc < 0)
    snow_age[b] = 0
    albedo[b] = SNOW_NEW_SNOW_ALB

    # Aged snow case
    b = ~b & (last_snow_depth > 0)
    snow_age[b] += sec_in_ts

    # Cold snow
    c = b & (last_pack_cc < 0)
    albedo[c] = SNOW_NEW_SNOW_ALB * \
        SNOW_ALB_ACCUM_A ** ((snow_age[c] / sec_per_day) ** SNOW_ALB_ACCUM_B)

    # Melting snow
    c = np.logical_and(b, np.isclose(last_pack_cc, 0, atol=1e-8))
    albedo[c] = SNOW_NEW_SNOW_ALB * \
        SNOW_ALB_THAW_A ** ((snow_age[c] / sec_per_day) ** SNOW_ALB_THAW_B)

    # No snow case
    b = np.isclose(last_snow_depth, 0, atol=1e-8)
    snow_age[b] = 0
    albedo[b] = parameters['ground_albedo']

    return albedo, snow_age


def _calc_albedo_tarboton(lastsnowtemp, snowage, newsnowdepth, lat, month, day, lastswe,
                          parameters, sec_in_ts):
    """
    Calculate albedo and snowage based on Tarboton model parameters.

    Parameters:
    -----------
    - lastsnowtemp: np.ndarray
        Array of last snow temperature.
    - snowage: np.ndarray
        Array of snow age values to be updated.
    - newsnowdepth: np.ndarray
        Array of new snow depths.
    - lat: np.ndarray
        Array of latitudes.
    - month: int
        Current month (for inclination angle calculation).
    - day: int
        Current day (for inclination angle calculation).
    - lastswe: np.ndarray
        Array of last snow water equivalent.
    - parameters: dict
        A dictionary of model parameters.
    - sec_in_ts: float
        Seconds in the time step.

    Returns:
    --------
    - albedo: np.ndarray
        Calculated albedo values.
    - snowage: np.ndarray
        Updated snow age values.
    """
    # Constants
    Cv = 0.2
    Cir = 0.5
    albedo_iro = 0.65
    albedo_vo = 2 * parameters['max_albedo'] - albedo_iro

    if albedo_vo > 1:
        d = albedo_vo - 1
        albedo_iro += d
        albedo_vo = 1

    # Initialize albedo array
    albedo = np.zeros_like(lastsnowtemp)

    # For new snow depths > 0.01 m
    b = newsnowdepth > 0.01
    if lat.shape != b.shape:
        lat_b = np.broadcast_to(lat, b.shape)
    else:
        lat_b = lat

    if np.any(b):
        albedo[b] = albedo_vo / 2 + albedo_iro / 2
        snowage[b] = 0

        # lat_b = np.broadcast_to(lat[:, np.newaxis], b.shape)

        inc = calc_inclination_angle(lat_b[b], month, day) * np.pi / 180
        c = np.cos(inc) < 0.5
        fpsi = 0.5 * (3. / (1 + 4 * np.cos(inc[c])) - 1)
        extra = np.zeros_like(inc)
        extra[c] = 0.2 * fpsi * (1 - albedo_vo) + 0.2 * fpsi * (1 - albedo_iro)
        albedo[b] += extra

    # For new snow depths <= 0.01 m (albedo is a function of snow age)
    b = ~b
    if np.any(b):
        r1 = np.exp(5000 * (1 / 273.16 - 1. / lastsnowtemp[b]))
        r2 = np.minimum(r1**10, 1)
        r3 = 0.03

        inc_age = (r1 + r2 + r3) / 1e6 * sec_in_ts
        snowage[b] += inc_age
        Fage = snowage[b] / (1 + snowage[b])

        albedo_1 = (1 - Cv * Fage) * albedo_vo
        albedo_2 = (1 - Cir * Fage) * albedo_iro
        albedo[b] = albedo_1 / 2 + albedo_2 / 2

        # lat_b = np.broadcast_to(lat, b.shape)
        # lat_b = np.broadcast_to(lat[:, np.newaxis], b.shape)

        inc = calc_inclination_angle(lat_b[b], month, day) * np.pi / 180
        c = np.cos(inc) < 0.5
        fpsi = 0.5 * (3. / (1 + 4 * np.cos(inc[c])) - 1)
        extra = np.zeros_like(inc)
        extra[c] = 0.2 * fpsi * (1 - albedo_1[c]) + 0.2 * fpsi * (1 - albedo_2[c])
        albedo[b] += extra

    # For no snow case
    b = np.isclose(lastswe, 0, atol=1e-8)
    if np.any(b):
        albedo[b] = parameters['ground_albedo']
        snowage[b] = 0

    return albedo, snowage
