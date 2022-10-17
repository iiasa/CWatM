# -------------------------------------------------------------------------
# Name:        Water quality 1 model
# Purpose:     Calculate velocity, travel time, water temperature
#
# Author:      PB
#
# Created:     29/03/2019
# Copyright:   (c) PB 2019
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


class waterquality1(object):

    """
    WATER QUALITY 1

    calculates water quality variables e.g. travel time, velocity, water temperature


    **Global variables**

    =====================================  ======================================================================  =====
    Variable [self.var]                    Description                                                             Unit 
    =====================================  ======================================================================  =====
    DtSec                                  number of seconds per timestep (default = 86400)                        s    
    cellArea                               Area of cell                                                            m2   
    Tavg                                   Input, average air Temperature                                          K    
    discharge                              discharge                                                               m3/s 
    chanLength                             Input, Channel length                                                   m    
    totalCrossSectionArea                                                                                               
    waterquality                                                                                                        
    celllength                             Cell length, defined as the square root of cell area                    m    
    downdist                                                                                                            
    travelDistance                                                                                                      
    travelTime                                                                                                          
    waterLevel                                                                                                          
    waterTemperature                                                                                                    
    =====================================  ======================================================================  =====

    **Functions**
    """

    def __init__(self, model):
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initial part of waterquality1 flow

        """

        self.var.waterquality = False
        if "waterquality" in option:
           self.var.waterquality = checkOption('waterquality')

        if self.var.waterquality:
            self.var.celllength = np.sqrt(self.var.cellArea)
            ldd = loadmap('Ldd')
            self.var.downdist = self.var.celllength
            self.var.downdist =np.where(ldd == 1, 1.414214 * self.var.downdist , self.var.downdist )
            self.var.downdist =np.where(ldd == 3, 1.414214 * self.var.downdist , self.var.downdist )
            self.var.downdist =np.where(ldd == 7, 1.414214 * self.var.downdist , self.var.downdist )
            self.var.downdist =np.where(ldd == 9, 1.414214 * self.var.downdist , self.var.downdist )





            i =1





    # --------------------------------------------------------------------------
# --------------------------------------------------------------------------


    def dynamic(self):
        """
        Dynamic part of the waterquality1 module
        Read meteo input maps from netcdf files
        """

        if self.var.waterquality :

          #crossArea = 0.34 * (self.var.discharge ** 0.341) * 1.22 * (self.var.discharge ** 0.557)
          dis = np.where (self.var.discharge < 0.0001, 0.0001, self.var.discharge)
          width = 1.22 * (dis ** 0.557)
          crossArea = 0.4148 * dis ** 0.898
          # van Vliet et al. 2012




          #flowVelocity = np.minimum(self.var.discharge /self.var.totalCrossSectionArea, 0.36*self.var.discharge**0.24)
          flowVelocity = np.minimum(self.var.discharge / crossArea,0.36 * dis ** 0.24)
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