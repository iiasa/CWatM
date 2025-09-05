"""
Calculate the latent heat of vaporization as a function of snow temperature.
"""

import numpy as np

def calculate_lat_heat_vap(lastsnowtemp):
    """
    Calculate the latent heat of vaporization (in kJ/kg) based on snow temperature.
    
    Parameters:
    -----------
    - lastsnowtemp: Snow temperature in degrees Celsius (array or scalar).
    
    Returns:
    --------
    - LatHeatVap: Latent heat of vaporization in kJ/kg.
    """    
    LatHeatVap = (2500.8 - 2.36 * lastsnowtemp 
                  + 0.016 * np.power(lastsnowtemp, 2) 
                  + 0.00006 * np.power(lastsnowtemp, 3))
    
    return LatHeatVap
