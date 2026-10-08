"""
Snowpack Model Script

This script defines a `Snowpack` class used to manage the initialization and tracking of
snowpack-related variables for climate or environmental models.

Attributes:
-----------
- lastalbedo (np.ndarray): Albedo values initialized based on the ground albedo parameter.
- lastswe (np.ndarray): Last snow water equivalent initialized to zeros.
- lastsnowdepth (np.ndarray): Last snow depth initialized to zeros.
- packsnowdensity (np.ndarray): Snow density initialized based on the default parameter.
- lastpackcc (np.ndarray): Last pack cold content initialized to zeros.
- lastpackwater (np.ndarray): Last pack water content initialized to zeros.
- lastpacktemp (np.ndarray): Last pack temperature initialized to zeros (only with full initialization).
- snowage (np.ndarray): Snow age initialized to zeros (only with full initialization).
- runoff (np.ndarray): Runoff values initialized to zeros to track water movement from the snowpack.

Usage:
------
For initializing the snowpack variables:
    1. `initialize_full_snowpack()`: Initializes all variables, including `lastpacktemp` and `snowage`.
    >>> snowpack = Snowpack(n_lat, parameters)
    >>> snowpack.initialize_full_snowpack(forcings_data)
    2. `initialize_snowpack_base()`: Initializes all variables except `lastpacktemp` and `snowage`.
    >>> snowpack.initialize_snowpack_base(forcings_data)
"""

import numpy as np
import cwatm.hydrological_modules.pySnowClim.constants as const

from cwatm.hydrological_modules.pySnowClim.calcSnowDensityAfterSnow import calc_snow_density_after_snow
from cwatm.hydrological_modules.pySnowClim.calcSnowDensity import calc_snow_density
from cwatm.hydrological_modules.pySnowClim.updatePackWater import update_pack_water
from cwatm.hydrological_modules.pySnowClim.calcAlbedo import calc_albedo


class Snowpack:
    def __init__(self, n_lat, parameters):
        """
        Class to handle initialization and management of snowpack-related variables.

        Args:
        -----
            n_lat (int): Number of latitude points.
            parameters (dict): Dictionary of model parameters, including 'ground_albedo' and 'snow_dens_default'.
        """
        self.n_lat = n_lat
        self.ground_albedo = parameters['ground_albedo']
        self.snow_dens_default = parameters['snow_dens_default']
        self.sec_in_ts = parameters['hours_in_ts'] * const.HR_2_SECS
        self.initialize_full_snowpack()

    def initialize_snowpack_base(self):
        """Initialize all core snowpack-related variables except 'lastpacktemp' and 'snowage'."""
        self.lastalbedo = np.ones(
            self.n_lat, dtype=np.float32) * self.ground_albedo
        # Snow Water Equivalent
        self.lastswe = np.zeros(self.n_lat, dtype=np.float32)
        self.lastsnowdepth = np.zeros(self.n_lat, dtype=np.float32)
        self.packsnowdensity = np.ones(
            self.n_lat, dtype=np.float32) * self.snow_dens_default
        self.lastpackcc = np.zeros(
            self.n_lat, dtype=np.float32)  # Cold content
        self.lastpackwater = np.zeros(
            self.n_lat, dtype=np.float32)  # Pack water content
        self.rain_in_snow = np.zeros(self.n_lat, dtype=np.float32) #np.full(self.n_lat, np.nan, dtype=np.float32)
        self.runoff = np.zeros(self.n_lat, dtype=np.float32) #np.full(self.n_lat, np.nan, dtype=np.float32)

    def initialize_snowpack_runoff(self):
        """Initialize runoff related variables except 'lastpacktemp' and 'snowage'."""
        self.runoff = np.zeros(self.n_lat, dtype=np.float32) #np.full(self.n_lat, np.nan, dtype=np.float32)


    def initialize_full_snowpack(self):
        """Initialize all snowpack variables, including 'lastpacktemp' and 'snowage'."""
        # Initialize base variables
        self.initialize_snowpack_base()
        # Initialize lastpacktemp and snowage
        self.lastpacktemp = np.zeros(self.n_lat, dtype=np.float32)
        self.snowage = np.zeros(self.n_lat, dtype=np.float32)

    def apply_temperature_instability_correction(self, input_forcings):
        """
        Apply a temperature instability correction to adjust lastpacktemp and lastpackcc
        for snow with small SWE values.

        Args:
            input_forcings (dict): Input meteorological forcings, including 'tavg'.
            sec_in_ts (float): Number of seconds in the timestep.
        """
        # Define threshold based on time step
        thres = self.sec_in_ts / const.HR_2_SECS * \
            0.015  # 15mm for each hour in the time step

        # Identify indices where the instability correction should apply
        instability_indices = np.logical_and(
            self.lastswe < thres, self.lastswe > 0)
        instability_indices = np.logical_and(instability_indices,
                                             self.lastpacktemp < input_forcings['tavg'])

        # Apply corrections
        self.lastpacktemp[instability_indices] = np.minimum(
            0, input_forcings['tavg'][instability_indices])
        self.lastpackcc[instability_indices] = const.WATERDENS * const.CI * \
            self.lastswe[instability_indices] * \
            self.lastpacktemp[instability_indices]

    def calculate_new_snow_temperature_and_cold_content(self, precip, input_forcings):
        """
        Calculate snow temperature and cold content and updates pack conditions.

        Parameters:
            precip (object): Precipitation data with snowfall and rainfall properties.
            input_forcings: dict, containing current timestep forcings such as temperature.
        """
        self.lastpackcc += precip.snowfallcc.copy()

        has_new_snow = precip.sfe > 0
        # Update last pack temperature where there is snowfall
        if np.any(has_new_snow):
            self.lastpacktemp[has_new_snow] = self.lastpackcc[has_new_snow] / \
                (const.WATERDENS * const.CI *
                 (self.lastswe[has_new_snow] + precip.sfe[has_new_snow]))

    def _calc_snowdensity_after_snow(self, has_snow, precip):
        """
        Calculate the new snowpack density after fresh snowfall.

        Parameters:
        -----------
            has_snow (numpy.ndarray): Active snowpack mask.
            precip (object): Precipitation data with snowfall and rainfall properties.
        """
        value = self.packsnowdensity.copy()
        value[has_snow] = calc_snow_density_after_snow(
            self.lastswe[has_snow].copy(), precip.sfe[has_snow].copy(),
            self.packsnowdensity[has_snow].copy(), precip.snowdens[has_snow].copy())
        self.packsnowdensity = value

    def _calc_new_snow_density(self, has_snow):
        """
        Calculate new snow density following compaction as a function of SWE and snow temperature.
        Based on Essery et al. (2013), Anderson (1976), and Boone (2002).

        Parameters:
        -----------
            - lastswe: Snow water equivalent (SWE) in kg/m².
            - sec_in_ts: Number of seconds in the current timestep.
        """
        value = self.packsnowdensity.copy()
        value[has_snow] = calc_snow_density(
            self.lastswe[has_snow].copy(), self.lastpacktemp[has_snow].copy(),
            self.packsnowdensity[has_snow].copy(), self.sec_in_ts)
        self.packsnowdensity = value
        self.lastsnowdepth[has_snow] = self.lastswe[has_snow] * \
            const.WATERDENS / self.packsnowdensity[has_snow]

    def update_snowpack_water(self, has_snow, lw_max):
        """
        Update snowpack liquid water content based on thresholds for irreducible and maximum water.

        Parameters:
            has_snow (numpy.ndarray): Active snowpack mask.
            sec_in_ts (int): Seconds in each timestep.
            lw_max (float): Maximum liquid water content as fraction of snow depth.
        """
        updated_runoff, lastpackwater = update_pack_water(
            has_snow, self.lastpackwater.copy(), self.lastsnowdepth.copy(),
            lw_max, self.runoff.copy(), self.sec_in_ts
        )
        self.runoff = updated_runoff.copy()
        self.lastpackwater = lastpackwater.copy()

    def _calc_rain_in_snow(self, has_snow, previouspackwater):
        """
        Calculate the amount of rain in the snow.

        Parameters:
            has_snow (numpy.ndarray): Active snowpack mask.
            previouspackwater (numpy.ndarray): Previous snowpack water.
        """
        self.rain_in_snow = np.where(has_snow,
                                     np.maximum(self.lastpackwater -
                                                previouspackwater, 0),
                                     np.nan)

    def _calculate_albedo(self, parameters, precip,
                          snow_vars, lat, month, day):
        """
        Calculate the snow albedo based on the selected model option and various snow and environmental parameters.

        Parameters:
        -----------
            parameters (dict): Model parameters containing albedo coefficients and thresholds.
            precip (object): Precipitation data with snowfall and rainfall properties.
            snow_vars (SnowModelVariables): Current state of the snowpack variables.
            lat (float): Latitude of the location, in degrees.
            month (int): Current month (1–12) for seasonal adjustments.
            day (int): Day of the month (1–31) for daily solar angle effects.
        """
        lastalbedo, snowage = calc_albedo(
            parameters, self.lastalbedo.copy(), precip.snowdepth.copy(),
            self.lastsnowdepth.copy(), precip.sfe, self.lastswe.copy(),
            snow_vars.SnowTemp.copy(), lat, month, day,
            self.snowage.copy(), self.lastpackcc.copy(), self.sec_in_ts
        )
        self.snowage = snowage.copy()
        self.lastalbedo = lastalbedo.copy()

    def update_snowpack_state(self, input_forcings, parameters, snow_vars,
                              precip, coords, time_value):
        """
        Updates the snowpack state variables based on surface temperature, snowfall,
        pack density, water content, and albedo.

        Args:
            input_forcings (dict): Dictionary with temperature and other input forcings.
            parameters (dict): Model parameters for snowpack calculations.
            snow_vars (object): Snow model variables object for storing outputs.
            precip (class): Precipitation properties.
            sec_in_ts (float): Number of seconds in a timestep.
            coords (dict): Coordinates information.
            time_value (tuple): Current time step and other time-related info.
        """
        self._calc_snowdensity_after_snow(snow_vars.ExistSnow, precip)

        self.lastswe += precip.sfe.copy()
        self.lastsnowdepth += precip.snowdepth.copy()

        self._calc_new_snow_density(snow_vars.ExistSnow)

        # Update snowpack liquid water content
        previouspackwater = self.lastpackwater.copy()
        self.lastpackwater[snow_vars.ExistSnow] += precip.rain[snow_vars.ExistSnow]

        self.update_snowpack_water(snow_vars.ExistSnow, parameters['lw_max'])
        self._calc_rain_in_snow(snow_vars.ExistSnow, previouspackwater)
        self._calculate_albedo(parameters, precip, snow_vars, coords['lat'],
                               time_value[1], time_value[2])

    def adjust_temp_snow(self):
        """Temperature adjustment for snow with positive SWE."""
        b = self.lastswe > 0
        if np.any(b):
            self.lastpacktemp[b] = self.lastpackcc[b] / \
                (const.WATERDENS * const.CI * self.lastswe[b])

    def update_class_no_snow(self, parameters):
        """Temperature adjustment for snow with positive SWE."""
        b = self.lastswe > 0
        if np.any(~b):
            self.lastpackwater[~b] = 0
            self.lastalbedo[~b] = parameters['ground_albedo']
            self.snowage[~b] = 0
            self.lastpacktemp[~b] = 0
            self.lastpackcc[~b] = 0
            self.lastsnowdepth[~b] = 0
            self.packsnowdensity[~b] = parameters['snow_dens_default']

    def update_pack_sublimation(self, Sublimation, has_sublimation):
        """
        Update snowpack properties by calculating sublimation.

        Parameters:
        -----------
        - sublimation: Current sublimation value (kg/m²).
        - has_sublimation: Where sublimatino occurs.
        """
        initialSWE = self.lastswe.copy()

        # For non-complete sublimation
        self.lastswe[has_sublimation] -= Sublimation[has_sublimation]
        self.lastsnowdepth[has_sublimation] = self.lastswe[has_sublimation] / \
            self.packsnowdensity[has_sublimation] * const.WATERDENS

        # only update cc for sublimation, not condensation
        cc_sublimation = np.logical_and(has_sublimation,  Sublimation > 0)
        self.lastpackcc[cc_sublimation] *= self.lastswe[cc_sublimation] / \
            initialSWE[cc_sublimation]

    def complete_pack_sublimation(self, Evaporation, no_snow_left, SnowDensDefault):
        """
        Finishes the sublimation process in the snowpack.

        Parameters:
        -----------
        - Evaporation: Current Evaporation value (kg/m²).
        - no_snow_left: Where snows is gone.
        - SnowDensDefault: default values for the packsnowdensity.
        """
        # Complete sublimation
        self.lastswe[no_snow_left] = 0
        self.lastsnowdepth[no_snow_left] = 0
        self.lastpackcc[no_snow_left] = 0
        self.packsnowdensity[no_snow_left] = SnowDensDefault

        # Update packwater by subtracting evaporation
        self.lastpackwater = np.maximum(0, self.lastpackwater - Evaporation)
