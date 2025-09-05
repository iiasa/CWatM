"""
Calculates sublimation and evaporation processes, updating snow water equivalent (SWE), 
snow depth, snow density, and cold content (cc) based on energy flux (E) and snowpack conditions.
"""
import numpy as np
import cwatm.hydrological_modules.pySnowClim.constants as const

def calc_sublimation(E, snowpack, snow_vars, SnowDensDefault):
    """
    Update snowpack properties by calculating sublimation and evaporation.

    Parameters:
    -----------
    E: Energy flux (kg/m²/s).
    snow_vars (object): Snow variables object to update (e.g., CCenergy, SnowMelt, etc.).
    snowpack (object): Snowpack variables class (e.g., lastsnowdepth, packsnowdensity, etc.).
    SnowDensDefault: Density of snow (kg/m³).

    Returns:
    --------
    - Updated sublimation, condensation
    """
    # Calculate sublimation and evaporation
    has_snow = snowpack.lastsnowdepth > 0 
    Sublimation = np.where(np.logical_and(snow_vars.SnowTemp < 0, has_snow),
                           -E/const.WATERDENS, 0) # Sublimation when snow temp < 0°C
    Evaporation = np.where(np.logical_and(np.isclose(snow_vars.SnowTemp, 0, atol=1e-8), 
                                          has_snow),
                            -E/ const.WATERDENS, 0)  # Evaporation at 0°C
    
    has_sublimation = np.logical_and(snowpack.lastswe  > Sublimation, has_snow)  # Sublimation occurs, update SWE, snow depth, cc
    no_snow_left = np.logical_and(snowpack.lastswe <= Sublimation, has_snow)  # Complete sublimation, no snow left

    snowpack.update_pack_sublimation(Sublimation, has_sublimation)

    # Complete sublimation
    Sublimation[no_snow_left] = snowpack.lastswe[no_snow_left]
    snowpack.complete_pack_sublimation(Evaporation, no_snow_left, SnowDensDefault)

    # Output sublimation and condensation
    sub_cond = Sublimation > 0
    sublimation = np.where(sub_cond, Sublimation, 0)
    condensation = np.where(~sub_cond, Sublimation, 0)

    return sublimation, condensation
