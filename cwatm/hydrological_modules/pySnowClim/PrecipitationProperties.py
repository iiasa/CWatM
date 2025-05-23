"""
PrecipitationProperties encapsulates properties related to snowfall, including rain,
snow water equivalent (SWE), snow density, and calculated snow depth.
""" 
import numpy as np
import cwatm.hydrological_modules.pySnowClim.constants as const

class PrecipitationProperties:
    """
    This class takes the precipitation properties as inputs and computes the snow
    depth based on SWE and snow density.

    Attributes:
        rain (np.ndarray): Rainfall in mm for the given timestep.
        sfe (np.ndarray): Snowfall water equivalent in mm.
        snowdens (np.ndarray): Density of the freshly fallen snow in kg/m^3.
        snowdepth (np.ndarray): Calculated depth of snow based on SWE and snow density.

    Methods:
        calculate_snowdepth(water_density): Computes the snow depth using SWE and
                                            snow density with a water density constant.
    """

    def __init__(self, rain, sfe, snowdens, snowfallcc):
        """
        Initializes the PrecipitationProperties class with rainfall, SWE, and snow density
        values, and computes the snow depth.

        Args:
            rain (np.ndarray): Rainfall amount (mm).
            sfe (np.ndarray): snowfall water equivalent (mm).
            snowdens (np.ndarray): Density of the fresh snow (kg/m^3).
            water_density (float): Constant representing water density (kg/m^3),
                                   typically 1000 for fresh water.
        """
        self.rain = np.copy(rain)
        self.sfe = np.copy(sfe)
        self.snowdens = np.copy(snowdens)
        self.snowfallcc = np.copy(snowfallcc)
        self.snowdepth = self._calculate_snowdepth()

    
    def _calculate_snowdepth(self):
        """
        Calculates snow depth based on SFE and snow density.

        Returns:
            np.ndarray: Calculated snow depth in meters.
        """
        return self.sfe * const.WATERDENS / self.snowdens
