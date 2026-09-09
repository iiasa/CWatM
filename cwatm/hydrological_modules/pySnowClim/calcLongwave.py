"""
Calculates the terrestrial upward longwave radiation based on emissivity, temperature, and downward longwave radiation.
"""

import numpy as np
import cwatm.hydrological_modules.pySnowClim.constants as const

def calc_longwave(emissivity, temp, lwdown, sec_in_ts):
    """
    Calculate terrestrial upward longwave radiation.
    
    Parameters:
    -----------
    - emissivity: Emissivity of the surface (scalar or array).
    - temp: Surface temperature in degrees Celsius (scalar or array).
    - lwdown: Downward longwave radiation (in kJ/m²).
    - sec_in_ts: Seconds in the time step.
    
    Returns:
    --------
    - lw: Upward longwave radiation (in kJ/m² for the time step).
    """
    # TODO add constat t constanst file
    SBconstant = 5.67E-11  # Stefan-Boltzmann constant [kJ m-2 K-4 s-1]
    tempK = temp + const.K_2_C   # Convert temperature to Kelvin [K]
    
    lw = (emissivity * SBconstant * np.power(tempK, 4)) + ((1 - emissivity) * (lwdown / sec_in_ts))
    lw = lw * sec_in_ts     # Convert to longwave radiation for the time step
    
    return lw
