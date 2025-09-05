"""
Estimates precipitation phase (rain or snow) based on temperature and relative humidity using a bivariate logistic regression model from Jennings et al., 2018.
"""
import numpy as np

def calc_phase(temp_celsius, rh):
    """
    Calculate the precipitation phase (rain or snow) based on temperature, relative humidity, and precipitation data.
    
    Parameters:
    -----------
    - temp_celsius: Air temperature in C (scalar or array).
    - rh: Relative humidity as a percentage (scalar or array).
    
    Returns:
    --------
    - psnow: Portion of precipitation classified as snow. 
    """
    # TODO add the below coefficients to the constant file
    # Coefficients from Jennings et al., 2018 (Table 2)
    a = -10.04
    b = 1.41
    g = 0.09

    # Calculate probability of snow
    psnow = 1.0 / (1.0 + np.exp(a + b * temp_celsius + g * rh))
    
    return psnow
