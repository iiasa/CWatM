"""
Calculates the new snow density based on SWE (snow water equivalent) and snow temperature, 
considering compaction, using the equations from Essery et al. (2013).
"""
import numpy as np
import cwatm.hydrological_modules.pySnowClim.constants as const

def calc_snow_density(lastswe, lastsnowtemp, packsnowdensity, sec_in_ts):
    """
    Calculate new snow density following compaction as a function of SWE and snow temperature.
    Based on Essery et al. (2013), Anderson (1976), and Boone (2002).

    Parameters:
    -----------
    - lastswe: Snow water equivalent (SWE) in kg/m².
    - lastsnowtemp: Snow temperature in degrees Celsius.
    - packsnowdensity: Initial snowpack density in kg/m³.
    - sec_in_ts: Number of seconds in the current timestep.

    Returns:
    --------
    - packsnowdensity: Updated snow density in kg/m³.
    """
    # TODO move these constants to the constants file
    # Define constants
    c1 = 2.8E-6  # 1/s
    c2 = 0.042   # 1/K
    c3 = 0.046   # m³/kg
    c4 = 0.081   # 1/K
    c5 = 0.018   # m³/kg
    p0 = 150     # kg/m³
    n0 = 3.7E7   # kg/m/s
    g = 9.81     # m/s²

    # Average snow mass between the ground surface and snow surface
    mass = (lastswe / 2) * const.WATERDENS

    # Calculate snow viscosity (nu)
    nu = n0 * np.exp(c4 * -lastsnowtemp + c5 * packsnowdensity)

    # Calculate change in snow density
    delta_density = packsnowdensity * ((mass * g) / nu + c1 * np.exp(-c2 * -lastsnowtemp - c3 * np.maximum(0, packsnowdensity - p0)))

    # Convert delta_density from kg/m³/s to appropriate timestep
    delta_density = delta_density * sec_in_ts

    # Calculate new snow density
    packsnowdensity = packsnowdensity + delta_density

    return packsnowdensity
