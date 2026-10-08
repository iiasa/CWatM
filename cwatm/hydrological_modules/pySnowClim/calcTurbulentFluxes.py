"""
Calculate Turbulent Heat and Mass Fluxes Using Richardson Number Parameterization.
"""
import numpy as np

from cwatm.hydrological_modules.pySnowClim.calcSpecificHumidity import calculate_specific_humidity
from cwatm.hydrological_modules.pySnowClim.calcLatHeatVap import calculate_lat_heat_vap
from cwatm.hydrological_modules.pySnowClim.calcLatHeatSub import calculate_lat_heat_sub
import cwatm.hydrological_modules.pySnowClim.constants as const


def calc_turbulent_fluxes(parameters, wind_speed, lastsnowtemp, tavg,
                          psfc, huss, sec_in_ts):
    """
    Calculate turbulent fluxes of heat and mass (evaporation/sublimation) using
    Richardson number parameterization based on Essery et al. (2013).

    Parameters:
    parameters: dictionary with the parameters to be used.
    wind_speed: Wind speed (m/s)
    lastsnowtemp: Snow surface temperature (C)
    tavg: Air temperature (C)
    psfc: Surface pressure (hPa)
    huss: Specific humidity (kg/kg)
    sec_in_ts: Seconds in the current timestep

    Returns:
    H: Sensible heat flux (kJ/m2/timestep)
    E: Latent heat flux (kg/m2/timestep)
    EV: Energy flux due to evaporation or sublimation (kJ/m2/timestep)
    """
    # Constants
    R = 287  # gas constant for dry air (J K-1 kg-1)
    g = 9.80616  # gravitational acceleration (m/s^2)
    c = 5  # stability constant from Essery et al., (2013), table 6
    E0 = parameters['E0_value'] / 1000  # Convert E0 to kJ/m2/K/s

    # Convert air pressure from hPa to Pa
    psfcpa = psfc * 100

    # Calculate air density (kg/m^3)
    pa = psfcpa / (R * (tavg + const.K_2_C))

    # Calculate vapor densities (kg/m^3)
    rhoa = huss.copy()
    rhos = calculate_specific_humidity(lastsnowtemp.copy(), psfc)

    # Exchange coefficient for neutral conditions if not 'stability' then (CHN)
    CH = const.K**2 * np.power(np.log(parameters['windHt'] / parameters['z_0']), -1) \
        * np.power(np.log(parameters['tempHt'] / parameters['z_h']), -1)

    if parameters['stability']:
        # Calculate the bulk Richardson number
        Rib = (g * parameters['windHt'] * (tavg - lastsnowtemp)) / \
            ((tavg + const.K_2_C) * wind_speed**2)

        # Calculate FH as a function of Rib
        FH = np.full_like(tavg, np.nan)
        # For unstable case
        FH[Rib < 0] = 1 - ((3 * c * Rib[Rib < 0]) / (1 + 3 * c**2 * CH *
                           (-Rib[Rib < 0] * parameters['windHt'] / parameters['z_0'])**0.5))
        # For neutral case
        FH[np.isclose(Rib, 0, atol=1e-8)] = 1
        # For stable case
        FH[Rib > 0] = (1 + ((2 * c * Rib[Rib > 0]) /
                       (1 + Rib[Rib > 0])**0.5))**-1

        # Calculate exchange coefficient CH
        CH *= FH

    # Latent heat of vaporization and sublimation
    LatHeatVap = calculate_lat_heat_vap(lastsnowtemp.copy())  # kJ/kg
    LatHeatSub = calculate_lat_heat_sub(lastsnowtemp.copy())  # kJ/kg

    # Windless exchange coefficient
    Ex = np.zeros_like(wind_speed)
    if parameters['E0_stable'] == 1:
        Ex = E0
    elif parameters['E0_stable'] == 2:
        Ex[Rib > 0] = E0

    # Sensible heat flux (H)
    H = -(pa * const.CA * CH * wind_speed + Ex) * (lastsnowtemp - tavg)

    # Latent heat flux (E)
    if parameters['E0_app'] == 1:
        E = -(pa * CH * wind_speed) * (rhos - rhoa)  # Mass flux kg/m2/s
    elif ['E0_app'] == 2:
        E = -(pa * CH * wind_speed + Ex) * (rhos - rhoa)  # Mass flux kg/m2/s

    # Evaporation and sublimation energy flux (EV)
    Evap = E * LatHeatVap
    Esub = E * LatHeatSub
    EV = np.where(lastsnowtemp >= 0, Evap, Esub)

    # Convert from per second to per timestep
    H *= sec_in_ts  # kJ/m2/s
    E *= sec_in_ts  # kg/m2/s
    EV *= sec_in_ts  # kJ/m2/s

    # Avoid NaNs for zero wind speed
    has_zero_speed = np.isclose(wind_speed, 0, atol=1e-8)
    H[has_zero_speed] = 0
    E[has_zero_speed] = 0
    EV[has_zero_speed] = 0

    return H, E, EV
