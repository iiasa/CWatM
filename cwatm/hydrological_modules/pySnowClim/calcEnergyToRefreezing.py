"""
This script distributes excess energy in the snowpack to allow refreezing of rain and meltwater, updates the snow water equivalent (SWE), snowpack cold content (CC), and snow density.
"""

import numpy as np
import cwatm.hydrological_modules.pySnowClim.constants as const

def calc_energy_to_refreezing(lastpackwater, lastswe, lastpackcc, lastsnowdepth, 
                              RefrozenWater, packsnowdensity):
    """
    Distributes excess energy to refreeze rain and meltwater in the snowpack, updates SWE, cold content, and snow density.

    Parameters:
    -----------
    - lastpackwater: Current water content in the snowpack (array).
    - lastswe: Snow water equivalent (array).
    - lastpackcc: Snowpack cold content (array).
    - lastsnowdepth: Current snow depth (array).
    - RefrozenWater: Amount of refrozen water (array).
    - packsnowdensity: Snowpack density (array).

    Returns:
    --------
    - lastpackwater: Updated water content in the snowpack (array).
    - lastswe: Updated snow water equivalent (array).
    - lastpackcc: Updated cold content (array).
    - packsnowdensity: Updated snow density (array).
    - RefrozenWater: Updated amount of refrozen water (array).
    """
    
    # Condition for refreezing: available water, snow, cold content, and density < 550 kg/m^3
    b = np.logical_and(np.logical_and(lastpackwater > 0, lastswe > 0), 
                       np.logical_and(lastpackcc < 0, packsnowdensity < 550)
                       )
    
    # Potential energy from refreezing
    Prf = np.zeros_like(lastpackwater)
    if np.any(b):
        Prf[b] = const.WATERDENS * const.LATHEATFREEZ * lastpackwater[b]

    # 1. If cold content exceeds refreezing potential energy, freeze all water and update cold content
    bb = np.logical_and(b, -lastpackcc >= Prf)
    if np.any(bb):
        lastswe[bb] += lastpackwater[bb]
        RefrozenWater[bb] = lastpackwater[bb]
        lastpackwater[bb] = 0
        lastpackcc[bb] += Prf[bb]
        Prf[bb] = 0

    # 2. If cold content is insufficient for full refreezing, freeze what is possible
    bb = np.logical_and(lastpackwater > 0, lastswe > 0) 
    bb = np.logical_and(bb, lastpackcc < 0) 
    bb = np.logical_and(bb, -lastpackcc < Prf) 
    bb = np.logical_and(bb, packsnowdensity < 550)
    if np.any(bb):
        RefrozenWater[bb] = -lastpackcc[bb] / (const.WATERDENS * const.LATHEATFREEZ)
        lastswe[bb] += RefrozenWater[bb]
        lastpackwater[bb] -= RefrozenWater[bb]
        lastpackcc[bb] = 0

    # Update snow density, assuming snow depth remains unchanged
    bb = lastsnowdepth > 0
    packsnowdensity[bb] = lastswe[bb] * const.WATERDENS / lastsnowdepth[bb]

    return lastpackwater, lastswe, lastpackcc, packsnowdensity, RefrozenWater
