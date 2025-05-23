"""
Calculates the latent heat of sublimation as a function of snow temperature.
"""

import numpy as np

def calculate_lat_heat_sub(lastsnowtemp):
    """
    Calculate the latent heat of sublimation (in kJ/kg) based on snow temperature.
    
    Parameters:
    -----------
    - lastsnowtemp: Snow temperature in degrees Celsius (array or scalar).
    
    Returns:
    --------
    - LatHeatSub: Latent heat of sublimation in kJ/kg.
    """
    
    LatHeatSub = 2834.1 - 0.29 * lastsnowtemp - 0.004 * np.power(lastsnowtemp, 2)
    
    return LatHeatSub
