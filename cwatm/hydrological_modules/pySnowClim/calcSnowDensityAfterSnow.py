"""
Calculates the new snowpack density after fresh snowfall based on the existing snowpack 
and the density of the new snow, using Essery et al. (2013), eqn 17.
"""
def calc_snow_density_after_snow(lastswe, newswe, packsnowdensity, newsnowdensity):
    """
    Calculate the new snowpack density after fresh snowfall.

    Parameters:
    -----------
    - lastswe: Snow water equivalent (SWE) of the existing snowpack in kg/m².
    - newswe: Snow water equivalent (SWE) of the new snow in kg/m².
    - packsnowdensity: Density of the existing snowpack in kg/m³.
    - newsnowdensity: Density of the new snow in kg/m³.

    Returns:
    --------
    - packsnowdensity: Updated snowpack density in kg/m³.
    """
    
    packsnowdensity = (lastswe + newswe) / ((lastswe / packsnowdensity) + (newswe / newsnowdensity))
    
    return packsnowdensity
