"""
Calculates specific humidity given the dewpoint temperature and surface pressure,
using the equation cited from Bolton (1980).
"""
import numpy as np

def calculate_specific_humidity(Td, P):
    """
    Calculate specific humidity.

    Parameters:
    -----------
    - Td: Dewpoint temperature in degrees Celsius.
    - P: Surface pressure in millibars (mb).

    Returns:
    --------
    - sh: Specific humidity (dimensionless ratio, kg water vapor/kg air).
    """

    e = 6.112 * np.exp((17.67 * Td) / (Td + 243.5))  # Saturation vapor pressure (mb)
    sh = (0.622 * e) / (P - (0.378 * e))  # Specific humidity formula
    
    return sh
