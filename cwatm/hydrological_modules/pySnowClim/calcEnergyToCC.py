"""
This script distributes excess energy into snowpack cold content, updating cold content and energy in the snowpack.
"""

import numpy as np

def calc_energy_to_cc(lastpackcc, lastenergy, CCenergy):
    """
    Distributes excess energy to snowpack cold content and adjusts energy for refreezing or melting processes.

    Parameters:
    -----------
    - lastpackcc: Current cold content of the snowpack (array).
    - lastenergy: Available energy in the snowpack (array).
    - CCenergy: Cold content energy (array) to track the energy used for refreezing.

    Returns:
    --------
    - lastpackcc: Updated cold content of the snowpack (array).
    - lastenergy: Updated available energy in the snowpack (array).
    - CCenergy: Updated cold content energy used for refreezing (array).
    """
    # Case 1: if cold content = 0 and lastenergy > 0, then nothing changes

    # Case 2: Cold content can be fully balanced by the available energy
    b = np.logical_and(-lastpackcc > 0, -lastpackcc <= lastenergy)
    if np.any(b):
        lastenergy[b] += lastpackcc[b]
        lastpackcc[b] = 0
        CCenergy[b] = np.minimum(0, lastenergy[b])

    # Case 3: Energy is insufficient to eliminate cold content, so some cold content remains
    b = (-lastpackcc > lastenergy)
    if np.any(b):
        lastpackcc[b] += lastenergy[b]
        CCenergy[b] = np.minimum(0, lastenergy[b])
        lastenergy[b] = 0

    return lastpackcc, lastenergy, CCenergy
