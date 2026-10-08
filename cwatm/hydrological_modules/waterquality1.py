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
    The module calculates:
    - Flow velocity based on discharge and cross-sectional area
    - Travel time and distance for water routing
    - Water depth in channels and floodplains
    - Water temperature using air temperature relationships
    
    Hydraulic calculations use empirical relationships from van Vliet et al. (2012)
    for channel width and cross-sectional area based on discharge.
    
    Water temperature estimation follows the logistic relationship from
    Morrill et al. (2005) and Mohseni et al. (1998).

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    DtSec                                Array         number of seconds per timestep (default = 86400)                        s    
    Tavg                                 Array         Input, average air Temperature                                          K    
    discharge                            Array         Channel discharge                                                       m3/s 
    chanLength                           Array         Input, Channel length                                                   m    
    totalCrossSectionArea                Array                                                                                 --   
    cellArea                             Array         Area of cell                                                            m2   
    waterquality                         Flag          Flag to use waterquality                                                bool 
    celllength                           Array         Cell length, defined as the square root of cell area                    m    
    downdist                             Array         flowdistance inside a cell. Diagonal = 1.414* celllength                m    
    travelDistance                       Array         travel distance of water: flow velocity per day                         m    
    travelTime                           List          time to travel a gridcell: chanLength / flowVelocity                    day  
    waterLevel                           Array         Water level                                                             m    
    waterTemperature                     Array         Temperature of water                                                    deg C
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
        Initialize water quality calculation parameters.
        
        Sets up geometric parameters for flow distance calculations including
        cell length and downstream distances accounting for diagonal flow
        directions in the local drainage direction network.
        
        Notes
        -----
        Initialization includes:
        - Cell length calculation from cell area
        - Downstream distance adjustment for diagonal flow directions
        - Geometric corrections for 8-direction flow (LDD values 1,3,7,9)
        
        Diagonal flow distances are multiplied by âˆš2 (â‰ˆ1.414214) to account
        for longer flow paths in diagonal directions.
        """

        self.var.waterquality = False
        if "waterquality" in option:
            self.var.waterquality = checkOption('waterquality')

        if self.var.waterquality:
            self.var.celllength = np.sqrt(self.var.cellArea)
            ldd = loadmap('Ldd')
            self.var.downdist = self.var.celllength
            self.var.downdist = np.where(ldd == 1, 1.414214 * self.var.downdist, self.var.downdist)
            self.var.downdist =np.where(ldd == 3, 1.414214 * self.var.downdist , self.var.downdist )
            self.var.downdist =np.where(ldd == 7, 1.414214 * self.var.downdist , self.var.downdist )
            self.var.downdist =np.where(ldd == 9, 1.414214 * self.var.downdist , self.var.downdist )

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------


    def dynamic(self):
        """
        Calculate water quality variables for current time step.
        
        Computes flow velocity, travel time, water depth, and water temperature
        based on current discharge and meteorological conditions. Uses empirical
        relationships to relate hydraulic properties to discharge.
        
        Notes
        -----
        Calculation sequence:
        1. Channel width and cross-sectional area from discharge relationships
        2. Flow velocity with constraints to avoid extremes
        3. Travel time and distance for water routing
        4. Water depth in channels and floodplains
        5. Water temperature from air temperature
        
        Empirical relationships used:
        - Width = 1.22 * Q^0.557 (van Vliet et al. 2012)
        - Cross-section = 0.4148 * Q^0.898
        - Velocity = min(Q/Area, 0.36 * Q^0.24) with minimum constraint
        - Water temperature = logistic function of air temperature
        
        References
        ----------
        van Vliet, M.T.H. et al. (2012) Coupled daily streamflow and water
        temperature modelling in large river basins. Hydrol. Earth Syst. Sci.
        
        Morrill et al. (2005), Mohseni et al. (1998) for water temperature
        """

        if self.var.waterquality:

          # crossArea = 0.34 * (self.var.discharge ** 0.341) * 1.22 * (self.var.discharge ** 0.557)
          dis = np.where(self.var.discharge < 0.0001, 0.0001, self.var.discharge)
          width = 1.22 * (dis ** 0.557)
          crossArea = 0.4148 * dis ** 0.898
          # van Vliet et al. 2012
          #van Vliet, M.T.H., Yearsley, J.R., Franssen, W.H.P., Ludwig, F., Haddeland, I., Lettenmaier, D.P., and Kabat, P.: Coupled daily streamflow and water
          #temperature modelling in large river  basins, Hydrol.Earth Syst.Sci., 16, 4303ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã¢â‚¬Å“4321, https: // doi.org / 10.5194 / hess - 16 - 4303 - 2012, 2012.

          #flowVelocity = np.minimum(self.var.discharge /self.var.totalCrossSectionArea, 0.36*self.var.discharge**0.24)
          flowVelocity = np.minimum(self.var.discharge / crossArea, 0.36 * dis ** 0.24)
          flowVelocity = np.maximum(flowVelocity, 10.*0.0011575)
             # Channel velocity (m/s); dividing Q (m3/s) by CrossSectionArea (m2)
             # avoid extreme velocities by using the Wollheim 2006 equation
             #  minimum velocity = 1000 m per day!
             #FlowVelocity = FlowVelocity * np.min(PixelLength/ChanLength,1)
             # reduction for sinuosity of channels


          self.var.travelDistance = flowVelocity * self.var.DtSec
             # if flow is fast, Traveltime=1, TravelDistance is high: Pixellength*DtSec
             # if flow is slow, Traveltime=DtSec then TravelDistance=PixelLength
             # maximum set to 30km/day for 5km cell, is at DtSec/Traveltime=6, is at Traveltime<DtSec/6

          #TravelTime = downstreamdist(Ldd) * (ChanLength/PixelLength) / FlowVelocity
          self.var.travelTime = self.var.chanLength / flowVelocity
          self.var.travelTime = np.where(self.var.travelTime > 200000, 200000, self.var.travelTime)
                # Traveltime through gridcell (sec)
                # further calculation with pc raster: l2.map = ldddist(ldd.map,p1.map,ttime1.map/cell.map)/86400
                # / cell.map (here 0.8333 deg is necessary because it is multiplied again in the ldddist command
                # p1.map is boolean map with mouth as 1, rest as 0


          # Water level
          chanCrossSectionArea = np.where(crossArea < self.var.totalCrossSectionArea, crossArea, self.var.totalCrossSectionArea)
          chanWaterDepth = chanCrossSectionArea / width
          # Water level in channel [m]

          floodPlainCrossSectionArea = np.where(crossArea < self.var.totalCrossSectionArea, 0, crossArea - self.var.totalCrossSectionArea)
          floodPlainWaterDepth = floodPlainCrossSectionArea / (2.0 * width)
          # Water level on floodplain [m]
          self.var.waterLevel = chanWaterDepth + floodPlainWaterDepth
          # Total water level [m]

          # Water-Air temperature relationship based on Morrill et al. (2005), Mohseni et al. (1998), van Vliet et al. (2012)
          # Water Temperature equation parameters

          WTalpha = 28.0
          # this is the max water temperature (degree Celsius)
          WTmu = 3.0
          # this is the min water temperature (degree Celsius)
          WTgamma = 0.18
          WTbeta = 14

          #WaterTemperature = 3.0 + (28-3)/(1+exp(0.18*(14-AirTemperature)));
          self.var.waterTemperature = WTmu + (WTalpha - WTmu)/(1 + np.exp(WTgamma * (WTbeta -  self.var.Tavg)))
             # Water-Air temperature relationship based on Morrill et al. (2005)
          i =1