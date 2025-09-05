"""
Update snowpack liquid water content and calculate runoff.

This function updates the liquid water content in the snowpack based on thresholds for irreducible water
and maximum water content. It calculates gravity drainage when water content is between these thresholds
and drains excess water when content exceeds the maximum, adding the resulting water to runoff.

References:
- Marsh (1991), Kinar and Pomeroy (2015) for irreducible and maximum water content rates.
- Snow principles suggest that maximum water content could be set higher in some cases.

"""

import numpy as np

def update_pack_water(exist_snow, lastpackwater, lastsnowdepth, lw_max, runoff, sec_in_ts):
    """
    Update snowpack liquid water content based on thresholds for irreducible and maximum water.
    
    Parameters:
    exist_snow (numpy.ndarray): Active snowpack mask.
    lastpackwater (numpy.ndarray): Previous timestep snowpack liquid water.
    lastsnowdepth (numpy.ndarray): Previous timestep snow depth.
    lw_max (float): Maximum liquid water content as fraction of snow depth.
    runoff (numpy.ndarray): Array to accumulate runoff values.
    sec_in_ts (int): Seconds in each timestep.

    Returns:
    tuple: Updated runoff and lastpackwater.
    """
    # Irreducible water (1% of snow depth)
    min_water = 0.01 * lastsnowdepth
    # Maximum water content (fraction of snow depth)
    max_water = lw_max * lastsnowdepth

    # Gravity drainage if water content is between min and max water
    b = np.logical_and(exist_snow, np.logical_and(lastpackwater > min_water, 
                                                  lastpackwater <= max_water))
    
    if np.any(b):
        waterrate = np.full_like(lastpackwater[b], 2.7778e-05)  # Drainage rate (10 cm/hr converted to m/s)
        waterdrainage = waterrate * (sec_in_ts / 2)  # Volume of water drained during the timestep
    
        # Don't let drainage drop packwater below the minimum threshold
        waterdrainage = np.minimum(waterdrainage, lastpackwater[b] - min_water[b])
        runoff[b] += waterdrainage
        lastpackwater[b] -= waterdrainage
    
    # Drain all excess water if packwater exceeds max_water
    b = np.logical_and(exist_snow, lastpackwater > max_water)
    if np.any(b):
        runoff[b] += (lastpackwater[b] - max_water[b])
        lastpackwater[b] = max_water[b]

    return runoff, lastpackwater
