"""
SnowModelVariables Class

This script defines the SnowModelVariables class, which initializes and holds the state variables
for a snow-climate model. These variables represent different physical quantities such as
snow depth, snow water equivalent, snow melt, sublimation, condensation, runoff, and energy
fluxes. Each variable is initialized as an array of NaN values with a given shape (outdim)
to be used in the simulation of snow and energy balance processes.

SnowMelt (array-like): Snow melt (m).
SnowWaterEq (array-like): Snow water equivalent (m).
SnowfallWaterEq (array-like): Snowfall water equivalent (m).
SnowDepth (array-like): Snow depth (m).
SnowDensity (array-like): Snowpack density (kg/m³).
Sublimation (array-like): Snow sublimation (m).
Condensation (array-like): Snow condensation (m).
SnowTemp (array-like): Snow surface temperature (°C).
MeltEnergy (array-like): Energy used for melting snow (kJ/m²/timestep).
Energy (array-like): Net energy to the snowpack (kJ/m²/timestep).
Albedo (array-like): Snow surface albedo.
ExistSnow (array-like): Snow cover binary (1 for snow, 0 for no snow).
RaininSnow (array-like): Rain added to the snowpack (m).
Runoff (array-like): Runoff from the snowpack (m).
RefrozenWater (array-like): Liquid water refrozen in the snowpack (m).
PackWater (array-like): Liquid water present in the snowpack (m).
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
        self.SnowWaterEq = np.zeros(outdim, dtype=np.float32) #np.full(outdim, np.nan, dtype=np.float32)
        self.SnowfallWaterEq = np.full(outdim, np.nan, dtype=np.float32)
        self.SnowDepth = np.zeros(outdim, dtype=np.float32)
        self.SnowDensity = np.full(outdim, np.nan, dtype=np.float32)
        self.Sublimation = np.full(outdim, np.nan, dtype=np.float32)
        self.Condensation = np.full(outdim, np.nan, dtype=np.float32)
        self.SnowTemp = np.full(outdim, np.nan, dtype=np.float32)
        self.MeltEnergy = np.full(outdim, np.nan, dtype=np.float32)
        self.Energy = np.full(outdim, np.nan, dtype=np.float32)
        self.Albedo = np.full(outdim, np.nan, dtype=np.float32)
        self.ExistSnow = np.zeros(outdim, dtype=np.float32)
        self.RaininSnow = np.zeros(outdim, dtype=np.float32)
        self.Runoff = np.zeros(outdim, dtype=np.float32)
        self.RefrozenWater = np.full(outdim, np.nan, dtype=np.float32)
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
