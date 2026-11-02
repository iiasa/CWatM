# -------------------------------------------------------------------------
# Name:        Water quality 1 model
# Purpose:     Calculate velocity, travel time, water temperature
#
# Author:      PB
# Created:     29/03/2019
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


class waterquality1(object):
    """
    Water quality module for calculating hydraulic and thermal water properties.
    
    Computes water quality variables including flow velocity, travel time, water depth,
    and water temperature in river channels and floodplains. Provides essential
    parameters for water quality modeling and pollutant transport calculations.
    
    Attributes
    ----------
    var : object
        Reference to model variables object containing state variables
    model : object
        Reference to the main CWatM model instance
        
    Notes
    -----
    The module calculates in the river channels, with the channel of the routing:
    - Cross section from the discharge with Manning: channel of the routing (width, gradient, roughness) without its
      calibration factors, which are not physical (the depth at the biggest cell of the Rhine would be 18 m)
    - Flow velocity = discharge / cross section, so area x velocity is the discharge (down to a minimum velocity)
    - Travel time and distance
    - Water level: with chanWidth up to bankfull, above it on a floodplain wider than the channel
    - Water temperature using air temperature relationships (logistic, Morrill et al. 2005, Mohseni et al. 1998)

    Cells of lakes and reservoirs have no river: all results are NaN there.

    Parameters from the settings file (a number or a map), with their default:
    minFlowVelocity = 1000 [m/day], floodplainWidthFactor = 2, waterTempMax = 28 [deg C], waterTempMin = 3 [deg C],
    waterTempGamma = 0.18 [1/deg C], waterTempBeta = 14 [deg C]

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    DtSec                                Array         number of seconds per timestep (default = 86400)                        s    
    Tavg                                 Array         Input, average air Temperature                                          degC 
    discharge                            Array         Channel discharge                                                       m3 s-
    chanLength                           Array         Input, Channel length                                                   m    
    chanWidth                            Array         Input, Channel bottom width                                             m    
    channelAlpha                         Array         Alpha of the kinematic wave of the routing, with calibration            --   
    alphaManning                         Array         Alpha without calibration: cross section = alphaManning * Q ** beta     --   
    beta                                 Array         Beta of the kinematic wave                                              --   
    waterBodyID                          Array         ID of the lakes and reservoirs, 0: no water body                        --   
    totalCrossSectionAreaBankFull        Array         Area (sq m) of bank full discharge cross section [m2] (AI)              --   
    waterquality                         Flag          Flag to use waterquality                                                bool 
    minVelocity                          Array         Minimum flow velocity                                                   m s-1
    floodplainWidthFactor                Array         Width of the floodplain as a multiple of the channel width              --   
    waterTempMax                         Array         Maximum water temperature                                               degC 
    waterTempMin                         Array         Minimum water temperature                                               degC 
    waterTempGamma                       Array         Steepness of the water temperature curve                                1/deg
    waterTempBeta                        Array         Air temperature at the middle of the water temperature curve            degC 
    travelDistance                       Array         travel distance of water: flow velocity per day                         m    
    travelTime                           Array         time to travel a gridcell: chanLength / flowVelocity                    s    
    waterLevel                           Array         Water level                                                             m    
    waterTemperature                     Array         Temperature of water                                                    degC 
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize water quality module.
        
        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Read the option and the parameters of the settings file.
        """

        self.var.waterquality = False
        if "waterquality" in option:
            self.var.waterquality = checkOption('waterquality')

        if self.var.waterquality:
            # the results come from the discharge: without routing it would stay at the value of the first day
            if not checkOption('includeRouting'):
                msg = "Error 170: waterquality = True needs includeRouting = True, without routing the discharge does not change"
                raise CWATMError(msg)

            # channelAlpha of the routing without its factor 2.5 and the calibration factor manningsN: Manning's equation
            # with chanMan, chanGrad and the wetted perimeter of the routing
            self.var.alphaManning = self.var.channelAlpha / (2.5 * loadmap('manningsN') ** self.var.beta)

            # parameters: a number or a map in the settings file, else the default
            def parameter(key, default):
                return loadmap(key) if key in binding else default

            self.var.minVelocity = parameter('minFlowVelocity', 1000.) / 86400.
            self.var.floodplainWidthFactor = parameter('floodplainWidthFactor', 2.)
            self.var.waterTempMax = parameter('waterTempMax', 28.)
            self.var.waterTempMin = parameter('waterTempMin', 3.)
            self.var.waterTempGamma = parameter('waterTempGamma', 0.18)
            self.var.waterTempBeta = parameter('waterTempBeta', 14.)

    # --------------------------------------------------------------------------

    def dynamic(self):
        """
        Calculate water quality variables for current time step.
        
        Computes flow velocity, travel time, water level and water temperature from the discharge of the routing
        and the air temperature. Cells of lakes and reservoirs get NaN.

        Notes
        -----
        - Cross section = alphaManning * Q ** beta (Manning, without the calibration of the routing)
        - Velocity = Q / cross section, at least minVelocity
        - Level = cross section / chanWidth up to bankfull,
          above it chanDepth + water above bankfull / (floodplainWidthFactor * chanWidth)
        - Water temperature = logistic function of air temperature

        References
        ----------
        Morrill et al. (2005), Mohseni et al. (1998), van Vliet et al. (2012) for water temperature
        """

        if self.var.waterquality:

            # no division by 0
            dis = np.where(self.var.discharge < 1e-7, 1e-7, self.var.discharge)

            # cross section of the channel with Manning
            crossArea = self.var.alphaManning * dis ** self.var.beta

            # Channel velocity [m/s]: area x velocity = discharge, down to the minimum velocity
            flowVelocity = np.maximum(dis / crossArea, self.var.minVelocity)

            # distance per time step [m]
            travelDistance = flowVelocity * self.var.DtSec
            # time to travel through the cell [s]
            travelTime = self.var.chanLength / flowVelocity

            # Water level [m]: in the channel up to bankfull, the water above it on the floodplain
            bankFull = self.var.totalCrossSectionAreaBankFull
            chanWaterDepth = np.minimum(crossArea, bankFull) / self.var.chanWidth
            floodPlainWaterDepth = np.maximum(crossArea - bankFull, 0.) / (self.var.floodplainWidthFactor * self.var.chanWidth)
            waterLevel = chanWaterDepth + floodPlainWaterDepth

            # Water-Air temperature relationship based on Morrill et al. (2005), Mohseni et al. (1998), van Vliet et al. (2012)
            waterTemperature = self.var.waterTempMin + (self.var.waterTempMax - self.var.waterTempMin) / \
                               (1 + np.exp(self.var.waterTempGamma * (self.var.waterTempBeta - self.var.Tavg)))

            # lakes and reservoirs have no river: as in the routing, cells with a water body are not channels
            if checkOption('includeWaterBodies'):
                lake = self.var.waterBodyID > 0
                travelDistance = np.where(lake, np.nan, travelDistance)
                travelTime = np.where(lake, np.nan, travelTime)
                waterLevel = np.where(lake, np.nan, waterLevel)
                waterTemperature = np.where(lake, np.nan, waterTemperature)

            self.var.travelDistance = travelDistance
            self.var.travelTime = travelTime
            self.var.waterLevel = waterLevel
            self.var.waterTemperature = waterTemperature
