# -------------------------------------------------------------------------
# Name:        Waterdemand modules
# Purpose: Agricultural irrigation water demand module for crop water requirements.
# Calculates irrigation needs based on crop water stress and soil moisture deficits.
# Supports multiple irrigation systems and crop-specific water application methods.
#
# Author:      PB, YS, MS, JdB, DF
# Created:     15/07/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules import globals
from cwatm.management_modules.data_handling import *
from cwatm.hydrological_modules.soil import rootZoneStress, arnoInfiltrationCapacity
import numpy as np


class waterdemand_irrigation:
    """
    Agricultural irrigation water demand module for crop water requirements.
    
    This class calculates irrigation needs based on crop water stress and soil moisture
    deficits. It supports multiple irrigation systems (paddy and non-paddy) and
    crop-specific water application methods. The module computes potential irrigation
    consumption based on soil water availability, crop coefficients, and infiltration
    capacity, considering irrigation efficiency and return flow fractions.
    
    Attributes
    ----------
    var : object
        Model variables container from parent model
    model : object
        Parent CWatM model instance

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    cropKC                               Array         crop coefficient for each of the 4 different land cover types (forest,  --   
    efficiencyPaddy                      Array         Input, irrPaddy_efficiency, paddy irrigation efficiency, the amount of  frac 
    efficiencyNonpaddy                   Array         Input, irrNonPaddy_efficiency, non-paddy irrigation efficiency, the am  frac 
    efficiencyNonpaddyStack              Flag          True: irrNonPaddy_efficiency is a yearly netCDF stack, read every new   bool 
    efficiencyNonpaddyWithdrawal         Array         efficiencyNonpaddy / fraction_IncreaseIrrigation_Nonpaddy: consumption  frac 
    returnfractionIrr                    Array         Input, irrigation_returnfraction, the fraction of non-efficient water   frac 
    alphaDepletion                       Array         Input, alphaDepletion, irrigation aims to alphaDepletion of field capa  frac 
    minimum_irrigation                   Array         Cover-specific irrigation in metres is 0 if less than this, currently   m    
    pot_irrConsumption                   Array         Cover-specific potential irrigation consumption                         m    
    fraction_IncreaseIrrigation_Nonpadd  Array         Input, extra non-paddy withdrawal for application losses (not to soil)  frac 
    irrPaddyDemand                       Array         Paddy irrigation demand                                                 m    
    ws1                                  Array         Maximum storage capacity in layer 1                                     m    
    ws2                                  Array         Maximum storage capacity in layer 2                                     m    
    wwp1                                 Array         Soil moisture at wilting point in layer 1                               m    
    wwp2                                 Array         Soil moisture at wilting point in layer 2                               m    
    arnoBeta                             Array         arnoBeta defines the shape of soil water capacity distribution curve a  --   
    maxtopwater                          Array         maximum heigth of topwater                                              m    
    paddyFloodKC                         Array         Input, irrPaddy_floodKC (0.75), paddy flooded + irrigated if cropKC >   --   
    nonpaddyIrrKC                        Array         Input, irrNonPaddy_minKC (0.20), non-paddy irrigated if cropKC > this   --   
    totAvlWater                          Array         Field capacity minus wilting point in soil layers 1 and 2               m    
    InvCellArea                          Array         Inverse of cell area of each simulated mesh                             1 m-2
    availWaterInfiltration               Array         quantity of water reaching the soil after interception, more snowmelt   m    
    w1                                   Array         Simulated water storage in the layer 1                                  m    
    w2                                   Array         Simulated water storage in the layer 2                                  m    
    topwater                             Array         quantity of water above the soil (flooding)                             m    
    FrostDay                             Array         frost index in soil [degree days] based on Molnau and Bissel (1983, A   --   
    fracVegCover                         Array         Fraction of specific land covers (0=forest, 1=grasslands, etc.)         frac 
    irrDemand                            Array         Cover-specific Irrigation demand                                        m    
    irrNonpaddyDemand                    Array         Sum up irrigation water demand with area fraction (AI)                  m    
    totalIrrDemand                       Array         Irrigation demand                                                       m    
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize the irrigation water demand module.
        
        Parameters
        ----------
        model : object
            The CWatM model instance containing variables and methods
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initialize irrigation water demand parameters and efficiency maps.
        
        Sets up unmet water demand tracking for paddy and non-paddy irrigation,
        loads irrigation efficiency maps, return flow fractions, and depletion
        coefficients. Initializes minimum irrigation thresholds and prepares
        variables for irrigation demand calculations.
        """

        # unmetDemand, unmetDemand_runningSum: set in water_demand.initial
        # before this is called
        # irrigation efficiency: paddy a single map, non-paddy a single map or a yearly stack
        self.var.efficiencyPaddy = loadmap("irrPaddy_efficiency")

        # Modified by Silvia Artuso: single map or yearly netcdf stack (a stack is read again every new year in
        # dynamic; before 2026-11 only the first year was used, the variable had to be named irrNonPaddy_efficiency)
        self.var.efficiencyNonpaddy, self.var.efficiencyNonpaddyStack = loadmapYearly(
            "irrNonPaddy_efficiency", dateVar['currDate'])

        self.var.returnfractionIrr = loadmap("irrigation_returnfraction")

        # for Xiaogang's agent model
        if "alphaDepletion" in binding:
            self.var.alphaDepletion = loadmap('alphaDepletion')
        else:
            self.var.alphaDepletion = 0.7

        # extra non-paddy withdrawal for application losses (loaded once, before 2026-11 every time step)
        self.var.fraction_IncreaseIrrigation_Nonpaddy = None
        if "fraction_IncreaseIrrigation_Nonpaddy" in binding:
            self.var.fraction_IncreaseIrrigation_Nonpaddy = (
                loadmap('fraction_IncreaseIrrigation_Nonpaddy') + globals.inZero.copy())

        # ignore demand (paddy and non-paddy) if less than self.var.minimum_irrigation [m]: 1 m3 per cell
        self.var.minimum_irrigation = self.var.InvCellArea

        self.checkEfficiency()

    def checkEfficiency(self):
        """
        Error 178 if the irrigation efficiency is not > 0 and <= 1, or fraction_IncreaseIrrigation_Nonpaddy < 1.

        Only cells with paddy or non-paddy area are checked (a map may have missing values = 0 elsewhere).
        Efficiency 0 gives an infinite demand; an efficiency > 1 (also efficiency / factor with a factor < 1)
        gives negative losses, i.e. water is created. Checked in initial and every new year (land cover and
        yearly efficiency stack change).
        """
        checks = [('irrPaddy_efficiency', self.var.efficiencyPaddy, 2, 'paddy'),
                  ('irrNonPaddy_efficiency', self.var.efficiencyNonpaddy, 3, 'non-paddy')]
        msg = ""
        for name, eff, No, cover in checks:
            eff = eff + globals.inZero
            # NaN is wrong too
            bad = (self.var.fracVegCover[No] > 0) & ~((eff > 0) & (eff <= 1))
            if np.any(bad):
                msg += "%s has to be > 0 and <= 1 in cells with %s area: %d cells, values %g to %g\n" % (
                    name, cover, np.sum(bad), np.nanmin(eff[bad]), np.nanmax(eff[bad]))
        if self.var.fraction_IncreaseIrrigation_Nonpaddy is not None:
            fac = self.var.fraction_IncreaseIrrigation_Nonpaddy
            bad = (self.var.fracVegCover[3] > 0) & ~(fac >= 1)
            if np.any(bad):
                msg += ("fraction_IncreaseIrrigation_Nonpaddy has to be >= 1 (extra water for losses) in cells with "
                        "non-paddy area: %d cells, values %g to %g\n" % (np.sum(bad), np.nanmin(fac[bad]),
                                                                         np.nanmax(fac[bad])))
        if msg:
            raise CWATMError("Error 178: irrigation efficiency\n" + msg)

    def dynamic(self):
        """
        Calculate dynamic irrigation water demand for current time step.
        
        Computes irrigation water requirements for paddy (No=2) and non-paddy (No=3)
        systems based on crop coefficients, soil moisture conditions, and available
        water. Considers soil water stress, infiltration capacity, and crop-specific
        water depletion factors. Calculates potential consumption and total demand
        considering irrigation efficiency.
        """

        # Paddy irrigation -> No = 2
        # Non paddy irrigation -> No = 3

        # non-paddy irrigation efficiency as yearly stack: the map of the new year (the start year is read in initial)
        if dateVar['newYear'] and not dateVar['newStart']:
            if self.var.efficiencyNonpaddyStack:
                self.var.efficiencyNonpaddy = readnetcdf2("irrNonPaddy_efficiency", dateVar['currDate'], 'yearly')
            # new efficiency map and/or new land cover fractions
            self.checkEfficiency()

        # irrigation water demand for paddy
        No = 2
        if np.any(self.var.fracVegCover[No] > 0):
            # a function of cropKC (evaporation and transpiration) and available water see Wada et al. 2014 p. 19
            # flooded if cropKC > paddyFloodKC (landcoverType, default 0.75) up to maxtopwater (as soil.py; before
            # 2026-11 up to alphaDepletion x maxtopwater: alphaDepletion is the soil depletion of non-paddy)
            self.var.pot_irrConsumption[No] = np.where(
                self.var.cropKC[No] > self.var.paddyFloodKC,
                np.maximum(0., (self.var.maxtopwater -
                               (self.var.topwater + self.var.availWaterInfiltration[No]))), 0.)
            # ignore demand if less than self.var.minimum_irrigation
            self.var.pot_irrConsumption[No] = np.where(self.var.pot_irrConsumption[No] > self.var.minimum_irrigation,
                                                       self.var.pot_irrConsumption[No], 0)
            self.var.irrDemand[No] = self.var.pot_irrConsumption[No] / self.var.efficiencyPaddy
        else:
            # no paddy in the domain today (before 2026-11 a demand was calculated, but weighted with fraction 0)
            self.var.pot_irrConsumption[No] = 0.
            self.var.irrDemand[No] = 0.

        # -----------------
        # irrNonPaddy
        No = 3

        # Infiltration capacity (Arno scheme, same function as soil.py), soil water before bare soil evaporation
        potInf, _ = arnoInfiltrationCapacity(self.var.w1[No], self.var.w2[No], self.var.ws1[No],
                                             self.var.ws2[No], self.var.arnoBeta[No])
        # rain + snow melt reaching the soil today fill the infiltration capacity first (soil.py: infiltration =
        # min(potInf, availWaterInfiltration + irrigation - prefFlow)), irrigation gets only the rest
        rainInf = np.minimum(self.var.availWaterInfiltration[No], potInf)
        # ----------------------------------------------------------
        # water above wilting point in layers 1 and 2
        availWaterPlant1 = np.maximum(0., self.var.w1[No] - self.var.wwp1[No])
        availWaterPlant2 = np.maximum(0., self.var.w2[No] - self.var.wwp2[No])
        readAvlWater = availWaterPlant1 + availWaterPlant2

        # calculate   ****** SOIL WATER STRESS ************************************
        # water stress of the whole root zone as for the transpiration (soil.py rootZoneStress, crop group 1):
        # irrigation starts if the stress factor is below alphaDepletion (before 2026-11: own stress of the layers
        # 1 + 2, not weighted with the root fraction, irrigation if readAvlWater < alphaDepletion x critical water)
        rws, _, _ = rootZoneStress(self.var, No, True)

        # with alpha from Xiaogang He, to adjust irrigation to farmer's need
        # amount: layers 1 and 2 (reached by the irrigation water) up to alphaDepletion x (field capacity - wilting point)
        # minus the infiltrating rain + snow melt of today (as for paddy; before 2026-11 rain was not taken into account)
        # no irrigation on frozen soil: soil.py lets nothing infiltrate on FrostDay (and no transpiration), the water
        # would go directly to runoff (before 2026-11 it was withdrawn and sent back as runoff)
        self.var.pot_irrConsumption[No] = np.where(
            (self.var.cropKC[No] > self.var.nonpaddyIrrKC) & (rws < self.var.alphaDepletion) & ~self.var.FrostDay,
            np.maximum(0.0, self.var.alphaDepletion * self.var.totAvlWater - readAvlWater - rainInf), 0.)

        # should not be bigger than the infiltration capacity left after today's rain + snow melt
        # (before 2026-11 the whole capacity: on rainy days the irrigation water went to runoff)
        self.var.pot_irrConsumption[No] = np.minimum(self.var.pot_irrConsumption[No], potInf - rainInf)

        # ignore demand if less than self.var.minimum_irrigation
        self.var.pot_irrConsumption[No] = np.where(
            self.var.pot_irrConsumption[No] > self.var.minimum_irrigation,
            self.var.pot_irrConsumption[No], 0)
        # fraction_IncreaseIrrigation_Nonpaddy: extra water withdrawn to offset application inefficiencies, it does
        # not reach the soil (losses: return flow + evaporation); used by water_demand for act_irrConsumption too
        # (before 2026-11 it scaled pot_irrConsumption before the infiltration limit, which clipped it nearly always)
        if self.var.fraction_IncreaseIrrigation_Nonpaddy is None:
            self.var.efficiencyNonpaddyWithdrawal = self.var.efficiencyNonpaddy
        else:
            self.var.efficiencyNonpaddyWithdrawal = (self.var.efficiencyNonpaddy /
                                                     self.var.fraction_IncreaseIrrigation_Nonpaddy)
        self.var.irrDemand[No] = self.var.pot_irrConsumption[No] / self.var.efficiencyNonpaddyWithdrawal

        # Sum up irrigation water demand with area fraction
        self.var.irrNonpaddyDemand = self.var.fracVegCover[3] * self.var.irrDemand[3]
        self.var.irrPaddyDemand = self.var.fracVegCover[2] * self.var.irrDemand[2]
        self.var.totalIrrDemand = self.var.irrPaddyDemand + self.var.irrNonpaddyDemand
