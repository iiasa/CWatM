"""
Calculates sublimation and evaporation processes, updating snow water equivalent (SWE),
snow depth, snow density, and cold content (cc) based on energy flux (E) and snowpack conditions.
Changes from Aranildo 12/03/26
"""
import numpy as np
#import constants as const
import cwatm.hydrological_modules.pySnowClim.constants as const
from cwatm.hydrological_modules.pySnowClim.calcLatHeatVap import calculate_lat_heat_vap
from cwatm.hydrological_modules.pySnowClim.calcLatHeatSub import calculate_lat_heat_sub


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
    # Latent heat of vaporization and sublimation
    LatHeatVap = calculate_lat_heat_vap(snow_vars.SnowTemp.copy())  # kJ/kg
    LatHeatSub = calculate_lat_heat_sub(snow_vars.SnowTemp.copy())  # kJ/kg

    Ei = E * LatHeatSub
    Ew = E * LatHeatVap
    
    negative_temp = np.logical_and(snow_vars.SnowTemp < 0, has_snow)
    zero_temp = np.logical_and(snow_vars.SnowTemp == 0, has_snow)

    mask_sublimation = np.logical_and(negative_temp, Ei < 0)
    mask_evaporation = np.logical_and(zero_temp, Ew < 0)
    mask_deposition = np.logical_and(negative_temp, Ei > 0)
    mask_condensation = np.logical_and(zero_temp, Ew > 0)

    Sublimation = np.where(mask_sublimation, -Ei / (LatHeatSub * const.WATERDENS), 0.0)
    Evaporation = np.where(mask_evaporation, -Ew / (LatHeatVap * const.WATERDENS), 0.0)
    Deposition = np.where(mask_deposition, -Ei / (LatHeatSub * const.WATERDENS), 0.0)
    Condensation = np.where(mask_condensation, -Ew / (LatHeatVap * const.WATERDENS), 0.0)

    has_sublimation = np.logical_and(snowpack.lastswe  > Sublimation, has_snow)  # Sublimation occurs, update SWE, snow depth, cc
    no_snow_left = np.logical_and(snowpack.lastswe <= Sublimation, has_snow)  # Complete sublimation, no snow left

    Sublimation,Deposition = snowpack.update_pack_sublimation(Sublimation, has_sublimation,Deposition )

    # Complete sublimation
    Sublimation[no_snow_left] = snowpack.lastswe[no_snow_left]
    # Output sublimation and condensation
    sub_cond = Sublimation > 0
    sublimation = np.where(sub_cond, Sublimation, 0)
    #condensation = np.where(~sub_cond, Sublimation, 0)

    Evaporation = snowpack.complete_pack_sublimation(Evaporation, Condensation,no_snow_left, SnowDensDefault)

    return sublimation, Condensation, Evaporation, Deposition
