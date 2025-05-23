"""
Calculates the density of fresh snowfall as a function of air temperature based on Essery et al. (2013), derived from Anderson (1976). Constants are adopted from Oleson et al. (2004).
"""

import numpy as np

def calc_fresh_snow_density(airtemp):
    """
    Calculate the density of fresh snow based on air temperature.
    
    Parameters:
    -----------
    - airtemp: Air temperature in degrees Celsius (array or scalar).
    
    Returns:
    --------
    - newsnowdensity: Density of fresh snow (array or scalar).
    """
    # TODO move these constants to the constant file.
    # Define constants
    df = 1.7     # 1/K
    ef = 15      # K
    pmin = 50    # kg/m^3, minimum snow density
    
    # Ensure air temperatures do not fall below -ef to avoid imaginary numbers
    airtemp_cap = np.maximum(airtemp, -ef)
    
    # Calculate fresh snow density
    newsnowdensity = pmin + np.maximum(df * (airtemp_cap + ef) ** (3/2), 0)
    
    return newsnowdensity
