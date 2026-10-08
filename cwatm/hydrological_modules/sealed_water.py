# -------------------------------------------------------------------------
# Name:        Sealed_water module
# Purpose:     runoff calculation for open water and sealed areas

# Author:      PB
# Created:     12/12/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


class sealed_water(object):
    """
    Sealed surface and open water runoff and evaporation module.
    
    Handles runoff generation and evaporation processes for impermeable surfaces
    (sealed/urban areas) and open water land cover types. Accounts for water bodies
    not explicitly represented in the lakes/reservoirs/channels framework.
    
    Attributes
    ----------
    var : object
        Reference to model variables object containing state variables
    model : object
        Reference to the main CWatM model instance
        
    Notes
    -----
    The module addresses hydrological processes on:
    - Sealed surfaces: Impermeable urban/built-up areas with limited evaporation
    - Open water: Water land cover including small rivers, ponds, wetlands
    
    Open water evaporation accounts for water bodies not captured by explicit
    lakes, reservoirs, and channels. For instance, if explicit water bodies
    cover 10% of a cell but water land class covers 20%, this module handles
    evaporation from the additional 10% of unrepresented water surfaces.
    
    Evaporation rates differ by surface type:
    - Water surfaces: Full reference evapotranspiration rate
    - Sealed surfaces: Reduced rate (0.2 Ã— reference) for ponded water

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    modflow                              Flag          True if modflow_coupling = True in settings file                        bool 
    EWRef                                Array         potential evaporation rate from water surface                           m    
    availWaterInfiltration               Array         quantity of water reaching the soil after interception, more snowmelt   m    
    actualET                             Array         simulated evapotranspiration from soil, flooded area and vegetation     m    
    directRunoff                         Array         Simulated surface runoff                                                m    
    openWaterEvap                        Array         Simulated evaporation from open areas                                   m    
    capillar                             Array         Flow from groundwater to the third CWATM soil layer. Used with MODFLOW  m    
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize sealed water module.
        
        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.var = model.var
        self.model = model

    def dynamic(self, coverType, No):
        """
        Calculate runoff and evaporation for sealed surfaces and open water.
        
        Processes water balance for impermeable surfaces and open water land
        cover types, determining direct runoff and evaporation rates based on
        surface characteristics and available water.
        
        Parameters
        ----------
        coverType : str
            Land cover type identifier ('sealed' or 'water')
        No : int
            Index number of the land cover type in model arrays
            
        Notes
        -----
        Processing logic:
        - Sealed surfaces (No=4): Limited evaporation (0.2 Ã— EWRef), remainder to runoff
        - Open water (No=5): Full evaporation rate (1.0 Ã— EWRef), remainder to runoff
        - ModFlow integration: Includes capillary rise contributions to runoff
        - Updates actual evapotranspiration and direct runoff arrays
        
        The method only processes land cover types with No > 3 (sealed and water),
        as other land covers are handled by different modules.
        """

        if No > 3:  # 4 = sealed areas, 5 = water
            if coverType == "water":
                # bigger than 0.2 because of wind evaporation
                mult = 1.0
            else:
                # evaporation from open areas on sealed area estimated as 0.2 EWRef
                mult = 0.2

            # ModFlow capillary rise under sealed areas and water is sent to runoff
            if self.var.modflow:
                self.var.openWaterEvap[No] = np.minimum(mult * self.var.EWRef,
                                                        self.var.availWaterInfiltration[No])
                self.var.directRunoff[No] = (self.var.availWaterInfiltration[No] - self.var.openWaterEvap[No] + 
                                             self.var.capillar)
            else:
                self.var.openWaterEvap[No] = np.minimum(mult * self.var.EWRef, self.var.availWaterInfiltration[No])
                self.var.directRunoff[No] = (self.var.availWaterInfiltration[No] - 
                                              self.var.openWaterEvap[No])

            # Open water evaporation will be accounted for in river/lake water balance calculations
            self.var.actualET[No] = self.var.actualET[No] + self.var.openWaterEvap[No]



