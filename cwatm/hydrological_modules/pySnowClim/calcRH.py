"""
Calculates relative humidity (%) from specific humidity, temperature, and surface pressure.
"""
import numpy as np

def calc_rh(huss, temp, pres):
    """
    Convert specific humidity to relative humidity based on the formula from 
    https://earthscience.stackexchange.com/questions/2360/how-do-i-convert-specific-humidity-to-relative-humidity.

    Parameters:
    -----------
    - huss: Specific humidity in kg/kg (scalar or array).
    - temp: Air temperature in degrees Celsius (scalar or array).
    - pres: Surface pressure in millibars (mb) (scalar or array).

    Returns:
    --------
    - relhum: Relative humidity as a percentage (bounded between 0 and 100%).
    """
    
    # Calculate saturation vapor pressure (es) using the Magnus formula
    es = 6.112 * np.exp((17.67 * temp) / (temp + 243.5))

    # Calculate vapor pressure (e)
    e = huss * pres / (0.378 * huss + 0.622)

    # Calculate relative humidity
    relhum = 100 * e / es

    # Bound relative humidity between 0 and 100%
    relhum = np.clip(relhum, 0, 100)
    
    return relhum
