"""
This script distributes excess energy in the snowpack to snowmelt, updates snow water equivalent (SWE), snow depth, and energy balance.
"""

import numpy as np
import cwatm.hydrological_modules.pySnowClim.constants as const

def calc_energy_to_melt(lastswe, lastsnowdepth, packsnowdensity, lastenergy, 
                        lastpackwater, SnowMelt, MeltEnergy):
    """
    Distributes excess energy to snowmelt, updates snow water equivalent (SWE), snow depth, and the energy balance.

    Parameters:
    -----------
    - lastswe: Current snow water equivalent in the snowpack (array).
    - lastsnowdepth: Current snow depth (array).
    - packsnowdensity: Snowpack density (array).
    - lastenergy: Available energy in the snowpack (array).
    - lastpackwater: Current water content in the snowpack (array).
    - SnowMelt: Amount of snowmelt generated during the time step (array).
    - MeltEnergy: Energy used for snowmelt (array).

    Returns:
    --------
    - SnowMelt: Updated snowmelt for the current time step (array).
    - MeltEnergy: Updated melt energy (array).
    - lastpackwater: Updated water content in the snowpack (array).
    - lastswe: Updated snow water equivalent (array).
    - lastsnowdepth: Updated snow depth (array).
    """
    
    # Case where SWE is positive and energy is available
    b = np.logical_and(lastswe > 0, lastenergy > 0)
    # Initialize melt array
    melt = np.zeros_like(lastpackwater)
    
    if np.any(b):
        # Calculate potential melt in meters of water equivalent
        potmelt = lastenergy[b] / (const.LATHEATFREEZ * const.WATERDENS)    
        
        # Actual melt is the minimum of available SWE or potential melt
        melt[b] = np.minimum(lastswe[b], potmelt)
        melt[melt < 0] = 0
        
        # Add melt to the monthly melt accumulation
        SnowMelt[b] = melt[b]
        
        # Calculate the energy used for melting
        meltenergy = melt[b] * const.LATHEATFREEZ * const.WATERDENS
        lastenergy[b] -= meltenergy
        MeltEnergy[b] = meltenergy
    
    # Update water content in the snowpack
    lastpackwater += melt    
    # Update SWE and snow depth
    lastswe -= melt
    
    b = lastswe > 0
    lastsnowdepth[b] = lastswe[b] * const.WATERDENS / packsnowdensity[b]
    lastsnowdepth[~b] = 0

    return SnowMelt, MeltEnergy, lastpackwater, lastswe, lastsnowdepth, lastenergy
