"""
SnowModelVariables Class

This script defines the SnowModelVariables class, which initializes and holds the state variables
for a snow-climate model. These variables represent different physical quantities such as
snow depth, snow water equivalent, snow melt, sublimation, condensation, runoff, and energy
fluxes. Each variable is initialized as an array of zeros or NaN values with a given shape (outdim)
to be used in the simulation of snow and energy balance processes.

Units: the units below are the output units, i.e. after _prepare_outputs (snow depth in mm, water
fluxes and storages in mm water equivalent). During the time step the same variables are in m
(water equivalent); _prepare_outputs multiplies them by 1000 (const.WATERDENS).

SnowMelt (array-like): Snow melt (mm).
SnowWaterEq (array-like): Snow water equivalent (mm).
SnowfallWaterEq (array-like): Snowfall water equivalent (mm).
SnowDepth (array-like): Snow depth (mm).
SnowDensity (array-like): Snowpack density (kg/m³).
Sublimation (array-like): Snow sublimation (mm).
Condensation (array-like): Snow condensation (mm).
Evaporation (array-like): Snow evaporation at T=0 °C (mm).
Deposition (array-like): Snow depostiion (mm).
SnowTemp (array-like): Snow surface temperature (°C).
MeltEnergy (array-like): Energy used for melting snow (kJ/m²/timestep).
Energy (array-like): Net energy to the snowpack (kJ/m²/timestep).
Albedo (array-like): Snow surface albedo.
ExistSnow (array-like): Snow cover binary (1 for snow, 0 for no snow).
RaininSnow (array-like): Rain added to the snowpack (mm).
Runoff (array-like): Runoff from the snowpack (mm).
RefrozenWater (array-like): Liquid water refrozen in the snowpack (mm).
PackWater (array-like): Liquid water present in the snowpack (mm).
LW_down (array-like): Downward longwave radiation to the snow surface (kJ/m²/timestep).
LW_up (array-like): Upward longwave radiation from the snow surface (kJ/m²/timestep).
SW_down (array-like): Downward shortwave radiation to the snow surface (kJ/m²/timestep).
SW_up (array-like): Upward shortwave radiation from the snow surface (kJ/m²/timestep).
Q_latent (array-like): Latent heat flux (kJ/m²/timestep).
Q_sensible (array-like): Sensible heat flux (kJ/m²/timestep).
Q_precip (array-like): Precipitation heat flux (kJ/m²/timestep).
PackCC (array-like): Snowpack cold content (kJ/m²/timestep).
CCenergy (array-like): Cold content changes due to energy flux (kJ/m²/timestep).
CCsnowfall (array-like): Cold content added by snowfall (kJ/m²/timestep).
"""

import numpy as np

class SnowModelVariables:
    """
    SnowModelVariables initializes the key variables needed to run the snow model,
    pre-allocating arrays with NaN values for snowpack and energy flux calculations.
    """

    def __init__(self, outdim):
        self.SnowMelt = np.zeros(outdim, dtype=np.float32)
        self.SnowWaterEq = np.zeros(outdim, dtype=np.float32)
        self.SnowfallWaterEq = np.full(outdim, np.nan, dtype=np.float32)
        self.SnowDepth = np.zeros(outdim, dtype=np.float32)
        self.SnowDensity = np.full(outdim, np.nan, dtype=np.float32)
        self.Sublimation = np.zeros(outdim, dtype=np.float32)
        self.Condensation = np.zeros(outdim, dtype=np.float32)
        self.Evaporation = np.zeros(outdim, dtype=np.float32)
        self.Deposition = np.zeros(outdim, dtype=np.float32)
        self.SnowTemp = np.full(outdim, np.nan, dtype=np.float32)
        self.MeltEnergy = np.full(outdim, np.nan, dtype=np.float32)
        self.Energy = np.full(outdim, np.nan, dtype=np.float32)
        self.Albedo = np.full(outdim, np.nan, dtype=np.float32)
        self.ExistSnow = np.zeros(outdim, dtype=np.float32)
        self.RaininSnow = np.zeros(outdim, dtype=np.float32)
        self.Runoff = np.zeros(outdim, dtype=np.float32)
        self.RefrozenWater = np.zeros(outdim, dtype=np.float32)
        self.PackWater = np.zeros(outdim, dtype=np.float32)
        self.LW_down = np.full(outdim, np.nan, dtype=np.float32)
        self.LW_up = np.full(outdim, np.nan, dtype=np.float32)
        self.SW_down = np.full(outdim, np.nan, dtype=np.float32)
        self.SW_up = np.full(outdim, np.nan, dtype=np.float32)
        self.Q_latent = np.full(outdim, np.nan, dtype=np.float32)
        self.Q_sensible = np.full(outdim, np.nan, dtype=np.float32)
        self.Q_precip = np.full(outdim, np.nan, dtype=np.float32)
        self.PackCC = np.full(outdim, np.nan, dtype=np.float32)
        self.CCenergy = np.full(outdim, np.nan, dtype=np.float32)
        self.CCsnowfall = np.full(outdim, np.nan, dtype=np.float32)

