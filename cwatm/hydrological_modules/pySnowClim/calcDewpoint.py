"""
This script calculates the dew point temperature at a given altitude based on specific humidity 
and elevation using the CIMIS pressure formula.
"""

import numpy as np

def calc_dewpoint(shv, Z):
    """
    Calculates the dew point temperature (in Kelvin) from specific humidity and elevation.

    Parameters:
    -----------
    - shv: Specific humidity in g/kg.
    - Z: Elevation in meters.

    Returns:
    --------
    - Td: Dew point temperature in Kelvin.
    """
    # CIMIS formula to calculate atmospheric pressure based on elevation
    pres = 1013.25 * ((293 - 0.0065 * Z) / 293) ** 5.26
    
    # Adjust specific humidity based on pressure
    shv = shv * pres / 0.622
    
    # Calculate logarithm of vapor pressure ratio
    e1 = np.log(shv / 6.112)
    
    # Calculate dew point temperature in Celsius
    Td = 243.5 * e1 / (17.67 - e1)
    
    # Convert Celsius to Kelvin
    Td = Td + 273.15
    
    return Td
