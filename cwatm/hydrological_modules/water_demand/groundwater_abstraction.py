# -------------------------------------------------------------------------
# Name:        Waterdemand modules
# Purpose:     Groundwater abstraction: potential abstraction, non-fossil abstraction (with or without MODFLOW),
#              limitAbstraction True (demand may be unmet) or False (fossil groundwater, zonal abstraction),
#              MODFLOW pumping. Part of water_demand.py until 2026-11 (split).
#
# Author:      PB, MS
# Created:     05/11/2026
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import numpy as np
from cwatm.management_modules import globals
from cwatm.management_modules.globals import dateVar, option
from cwatm.management_modules.replace_pcr import AreaIndex
from cwatm.management_modules.data_handling import binding, loadmap, divideValues, checkOption, regularZones
from cwatm.hydrological_modules.water_demand.sector_demand import (split_sectors, SECTORS, ORDER_UNMET,
    ORDER_WITHDRAWAL_TOTAL, ORDER_WITHDRAWAL_SW, rest_of_demand, pot_source, sum_vars)


class waterdemand_groundwater(object):
    """
    Groundwater abstraction of the water demand.

    The demand left after the surface water sources is taken from groundwater: the potential abstraction
    (pot_GroundwaterAbstract, with sector fractions per sector) is limited by the groundwater available
    (readAvlStorGroundwater, or groundwater_storage_available with MODFLOW) -> nonFossilGroundwaterAbs.
    With limitAbstraction = True the rest stays unmet and the withdrawals are reduced; with limitAbstraction = False
    the rest is fossil groundwater (unmetDemand), optionally after a zonal allocation of channel water and
    groundwater (zonal_abstraction). With MODFLOW the pumping is passed to MODFLOW (modfPumpingM).

    **Global variables**

    =========================================  ==========    ================================================================  =====
    Variable [self.var]                        Type          Description                                                       Unit 
    =========================================  ==========    ================================================================  =====
    act_channelAbst                            Array         Channel abstraction                                               m    
    act_irrNonpaddyDemand                      Array         Non-paddy irrigation demand                                       m    
    act_irrNonpaddyWithdrawal                  Array         Non-paddy irrigation withdrawal                                   m    
    act_irrPaddyDemand                         Array         Paddy irrigation demand                                           m    
    act_irrPaddyWithdrawal                     Array         Paddy irrigation withdrawal                                       m    
    act_irrWithdrawal                          Array         Irrigation withdrawals                                            m    
    act_nonIrrWithdrawal                       Array         Non-irrigation withdrawals                                        m    
    act_SurfaceWaterAbstract                   Array         Surface water abstraction                                         m    
    allocation_zone                            Array         Zonal abstraction: zone of allocation_area x allocation_area      --   
    allocation_zoneIndex                       Object        Index of allocation_zone for area total, all cells (AreaIndex)    --   
    cellArea                                   Array         Cell area                                                         m2   
    Channel_Domestic                           Array         Channel water for domestic                                        m    
    Channel_Domestic_fromZone                  Array         Zonal abstraction: channel water for domestic                     m    
    Channel_Industry                           Array         Channel water for industry                                        m    
    Channel_Industry_fromZone                  Array         Zonal abstraction: channel water for industry                     m    
    Channel_Irrigation                         Array         Channel water for irrigation                                      m    
    Channel_Irrigation_fromZone                Array         Zonal abstraction: channel water for irrigation                   m    
    Channel_Livestock                          Array         Channel water for livestock                                       m    
    Channel_Livestock_fromZone                 Array         Zonal abstraction: channel water for livestock                    m    
    Channel_Other                              Array         Zonal channel water not attributed to a sector                    m    
    commandAreasRelaxGwAbstraction             Array         GW fraction for irrigation in command areas (agents)              frac 
    domesticDemand                             Array         Domestic water demand (withdrawal)                                m    
    fracVegCover                               Array         Land cover fractions (0 forest, 1 grassland, 2 paddy, ...)        frac 
    groundwater_storage_available              Array         MODFLOW: groundwater storage available for pumping                m    
    GW_Domestic                                Array         Groundwater for domestic (fossil incl. if limitAbstraction F)     m    
    GW_Domestic_fromZone                       Array         Zonal abstraction: groundwater for domestic                       m    
    GW_Industry                                Array         Groundwater for industry (fossil incl. if limitAbstraction F)     m    
    GW_Industry_fromZone                       Array         Zonal abstraction: groundwater for industry                       m    
    GW_Irrigation                              Array         Groundwater for irrigation (fossil incl. if limitAbstraction F)   m    
    GW_Irrigation_fromZone                     Array         Zonal abstraction: groundwater for irrigation                     m    
    GW_Livestock                               Array         Groundwater for livestock (fossil incl. if limitAbstraction F)    m    
    GW_Livestock_fromZone                      Array         Zonal abstraction: groundwater for livestock                      m    
    GW_Other                                   Array         Zonal groundwater not attributed to a sector                      m    
    GW_pumping                                 Flag          True if Groundwater_pumping = True (pumping sent to MODFLOW)      bool 
    gwAbstractionFraction_Domestic             Array         Input: share of the domestic demand from groundwater              frac 
    gwAbstractionFraction_Industry             Array         Input: share of the industry demand from groundwater              frac 
    gwAbstractionFraction_Irrigation           Array         Input: share of the irrigation demand from groundwater            frac 
    gwAbstractionFraction_Livestock            Array         Input: share of the livestock demand from groundwater             frac 
    includeIndusDomesDemand                    Flag          True if includeIndusDomesDemand = True                            bool 
    industryDemand                             Array         Industry water demand (withdrawal)                                m    
    irrDemand                                  Array         Irrigation demand per land cover                                  m    
    irrNonpaddyDemand                          Array         Non-paddy irrigation demand                                       m    
    irrPaddyDemand                             Array         Paddy irrigation demand                                           m    
    limitAbstraction                           Flag          True if limitAbstraction = True: no fossil groundwater            bool 
    livestockDemand                            Array         Livestock water demand (withdrawal)                               m    
    modflow                                    Flag          True if modflow_coupling = True                                   bool 
    modfPumpingM                               Array         MODFLOW: pumping since the last MODFLOW run                       m    
    nonFossilGroundwaterAbs                    Array         Non-fossil groundwater abstraction                                m    
    nonIrrDemand                               Array         Non-irrigation demand (domestic + industry + livestock)           m    
    pot_GroundwaterAbstract                    Array         Potential groundwater abstraction                                 m    
    Pumping_daily                              Array         MODFLOW: groundwater pumping of the day                           m    
    PumpingM3_daily                            Array         MODFLOW: groundwater pumping of the day                           m3   
    readAvlChannelStorageM                     Array         Channel water available for abstraction (minus env. flow)         m    
    readAvlStorGroundwater                     Array         storGroundwater available for abstraction (0 below a threshold)   m    
    reservoir_command_areas                    Array         Command areas of the reservoirs (no lakes / restricted res.)      --   
    sectorSourceAbstractionFractions           Flag          True if sector- and source-specific abstraction fractions         bool 
    swAbstractionFraction                      Array         Input swAbstractionFrac: surface water share of the demand        frac 
    totalIrrDemand                             Array         Irrigation demand                                                 m    
    unmetDemand                                Array         Unmet demand, taken from fossil groundwater (limitAbstraction F)  m    
    using_reservoir_command_areas              Flag          True if using_reservoir_command_areas = True                      bool 
    =========================================  ==========    ================================================================  =====

    """

    def __init__(self, model, agents):
        self.var = model.var
        self.model = model
        self.agents = agents   # irrigation agents: cap of the groundwater abstraction for irrigation

    def initial(self):
        """
        Groundwater abstraction fractions per sector, groundwater fraction for irrigation in command areas
        (commandAreasRelaxGwAbstraction) and the allocation zones of the zonal abstraction.
        Called after using_reservoir_command_areas is set.
        """

        # groundwater abstraction fraction per sector: 1 without limitAbstraction, maps otherwise
        if self.var.sectorSourceAbstractionFractions:

            if not self.var.limitAbstraction:
                self.var.gwAbstractionFraction_Domestic = 1 + globals.inZero.copy()
                self.var.gwAbstractionFraction_Livestock = 1 + globals.inZero.copy()
                self.var.gwAbstractionFraction_Industry = 1 + globals.inZero.copy()
                self.var.gwAbstractionFraction_Irrigation = 1 + globals.inZero.copy()
            else:
                self.var.gwAbstractionFraction_Domestic = loadmap('gwAbstractionFraction_Domestic')
                self.var.gwAbstractionFraction_Livestock = loadmap('gwAbstractionFraction_Livestock')
                self.var.gwAbstractionFraction_Industry = loadmap('gwAbstractionFraction_Industry')
                self.var.gwAbstractionFraction_Irrigation = loadmap('gwAbstractionFraction_Irrigation')

        # groundwater abstraction fraction for irrigation in reservoir command areas after the 15th of each month
        # (read once here, used every day in dynamic)
        if self.var.sectorSourceAbstractionFractions and 'commandAreasRelaxGwAbstraction' in binding and self.var.using_reservoir_command_areas:
            self.var.commandAreasRelaxGwAbstraction = loadmap('commandAreasRelaxGwAbstraction')

        # allocation zone: regular grid of allocation_area x allocation_area cells, only for the zonal
        # abstraction (before 2026-11 built in every run with water demand, file read here)
        if 'zonal_abstraction' in option and checkOption('zonal_abstraction'):
            inner = 1
            if "allocation_area" in binding:
                inner = int(loadmap('allocation_area'))
            self.var.allocation_zone = regularZones(inner)
            # index for the area functions per allocation zone (all cells, zone 0 is a zone)
            self.var.allocation_zoneIndex = AreaIndex(self.var.allocation_zone, onlypositive=False)

    def update_fractions(self):
        """
        Groundwater fraction for irrigation in the reservoir command areas: 0.01 at the start of a month,
        commandAreasRelaxGwAbstraction after the 15th (called after agents.update_fractions, which resets it).
        """

        if dateVar['newStart'] or dateVar['newMonth']:
            if 'commandAreasRelaxGwAbstraction' in binding and self.var.sectorSourceAbstractionFractions:
                self.var.gwAbstractionFraction_Irrigation = np.where(self.var.reservoir_command_areas > 0,
                                                                     0.01,
                                                                     self.var.gwAbstractionFraction_Irrigation)

        if self.var.sectorSourceAbstractionFractions and 'commandAreasRelaxGwAbstraction' in binding and \
                self.var.using_reservoir_command_areas:

            if dateVar['currDate'].day > 15:
                self.var.gwAbstractionFraction_Irrigation = np.where(self.var.reservoir_command_areas > 0,
                                                                     self.var.commandAreasRelaxGwAbstraction,
                                                                     self.var.gwAbstractionFraction_Irrigation)

    def dynamic(self, totalDemand, pot_Channel):
        """
        Groundwater abstraction of the day.

        Parameters
        ----------
        totalDemand : ndarray
            Total demand [m]
        pot_Channel : list of ndarray or None
            Potential channel abstraction per sector (SECTORS order, None without sector fractions), for the
            zonal abstraction [m]

        Returns
        -------
        tuple
            act_irrWithdrawalSW, act_irrWithdrawalGW: irrigation withdrawal from surface water / groundwater [m]
            for the irrigation agents (None with limitAbstraction = False)
        """

        # remaining is taken from groundwater if possible
        if self.var.sectorSourceAbstractionFractions:
            pot_GW_Domestic, pot_GW_Livestock, pot_GW_Industry, pot_GW_Irrigation = pot_source(
                self.var, 'GW', 'gwAbstractionFraction_%s')

            pot_GW_Irrigation = self.agents.cap_gw(pot_GW_Irrigation)


            self.var.pot_GroundwaterAbstract = pot_GW_Domestic + pot_GW_Livestock + pot_GW_Industry + pot_GW_Irrigation
        else:
            self.var.pot_GroundwaterAbstract = totalDemand - self.var.act_SurfaceWaterAbstract

        if self.var.modflow:
            # groundwater storage that can be pumped: above the minimum saturated fraction of each layer
            # (water_table_limit_for_pumping, groundwater_modflow/transient.py, Dor's version) - before 2026-10 no
            # pumping if the storage was below (1 - water_table_limit_for_pumping) * full storage. Minus the pumping
            # of the days since the last MODFLOW run (modfPumpingM, modflow_timestep > 1: the available storage is
            # updated only by MODFLOW runs) - before 2026-10-11 each day could take the full available storage
            self.var.nonFossilGroundwaterAbs = np.minimum(
                np.maximum(self.var.groundwater_storage_available - self.var.modfPumpingM, 0),
                self.var.pot_GroundwaterAbstract)
        else:
            self.var.nonFossilGroundwaterAbs = np.maximum(0., np.minimum(self.var.readAvlStorGroundwater,
                                                                         self.var.pot_GroundwaterAbstract))

        # if limitAbstraction from groundwater is True
        # fossil gwAbstraction and water demand may be reduced
        # variable to reduce/limit groundwater abstraction (> 0 if limitAbstraction = True)

        if self.var.sectorSourceAbstractionFractions:
            # A
            (self.var.GW_Domestic, self.var.GW_Livestock, self.var.GW_Industry,
             self.var.GW_Irrigation), _ = split_sectors(self.var.nonFossilGroundwaterAbs, (
                pot_GW_Domestic, pot_GW_Livestock, pot_GW_Industry, pot_GW_Irrigation))

            unmet_Domestic, unmet_Livestock, unmet_Industry, unmet_Irrigation = [
                rest_of_demand(self.var, sector, ORDER_UNMET) for sector in SECTORS]

        # lists in SECTORS order for limited / unlimited / zonal (None without sector fractions)
        pot_GW = unmet = None
        if self.var.sectorSourceAbstractionFractions:
            pot_GW = [pot_GW_Domestic, pot_GW_Livestock, pot_GW_Industry, pot_GW_Irrigation]
            unmet = [unmet_Domestic, unmet_Livestock, unmet_Industry, unmet_Irrigation]

        act_irrWithdrawalSW = act_irrWithdrawalGW = None
        if self.var.limitAbstraction:
            act_irrWithdrawalSW, act_irrWithdrawalGW, act_gw = self.limited(totalDemand)
        else:
            act_gw = self.unlimited(totalDemand, pot_Channel, pot_GW, unmet)

        if self.var.modflow:
            if self.var.GW_pumping:  # pumping demand is sent to ModFlow (used in transient module)
                # modfPumpingM is initialized every "modflow_timestep" in "groundwater_modflow/transient.py"
                self.var.modfPumpingM += act_gw
                self.var.Pumping_daily = np.copy(act_gw)
                self.var.PumpingM3_daily = act_gw * self.var.cellArea

        return act_irrWithdrawalSW, act_irrWithdrawalGW

    def limited(self, totalDemand):
        """
        limitAbstraction = True: no fossil groundwater, the withdrawals are what surface water and non-fossil
        groundwater give; the rest of the demand is unmet (unmetDemand).

        Returns
        -------
        tuple
            act_irrWithdrawalSW, act_irrWithdrawalGW [m], act_gw: groundwater abstraction (MODFLOW pumping) [m]
        """

        # real surface water abstraction can be lower, because not all demand can be done from surface water
        act_swAbstractionFraction = divideValues(self.var.act_SurfaceWaterAbstract, totalDemand)
        # Fossil groundwater abstraction is not allowed
        # allocation rule here: domestic& industry > irrigation > paddy

        if self.var.sectorSourceAbstractionFractions:

            self.var.act_nonIrrWithdrawal = sum_vars(self.var, [source + '_' + sector for source in
                                                                ORDER_WITHDRAWAL_TOTAL for sector in SECTORS[:3]])
            self.var.act_irrWithdrawal = sum_vars(self.var, [s + '_Irrigation' for s in ORDER_WITHDRAWAL_TOTAL])
            # Currently wastewater and desalination are accounted as surface water
            act_irrWithdrawalSW = sum_vars(self.var, [s + '_Irrigation' for s in ORDER_WITHDRAWAL_SW])
            act_irrWithdrawalGW = self.var.GW_Irrigation
            self.var.act_irrNonpaddyWithdrawal = np.minimum(self.var.act_irrWithdrawal,
                                                            self.var.fracVegCover[3] * self.var.irrDemand[3])
            self.var.act_irrPaddyWithdrawal = self.var.act_irrWithdrawal - self.var.act_irrNonpaddyWithdrawal

            act_gw = np.copy(self.var.nonFossilGroundwaterAbs)

        elif self.var.includeIndusDomesDemand:  # all demands are taken into account
            # non-irrgated water demand: adjusted (and maybe increased) by gwabstration factor if
            # non-irrgated water demand is higher than actual growndwater abstraction (what is needed and
            # what is stored in gw)
            act_nonIrrWithdrawalGW = self.var.nonIrrDemand * (1 - act_swAbstractionFraction)
            act_nonIrrWithdrawalGW = np.where(act_nonIrrWithdrawalGW > self.var.nonFossilGroundwaterAbs,
                                              self.var.nonFossilGroundwaterAbs, act_nonIrrWithdrawalGW)
            act_nonIrrWithdrawalSW = act_swAbstractionFraction * self.var.nonIrrDemand
            self.var.act_nonIrrWithdrawal = act_nonIrrWithdrawalSW + act_nonIrrWithdrawalGW

            # irrigated water demand:
            act_irrWithdrawalGW = self.var.totalIrrDemand * (1 - act_swAbstractionFraction)
            act_irrWithdrawalGW = np.minimum(self.var.nonFossilGroundwaterAbs - act_nonIrrWithdrawalGW,
                                             act_irrWithdrawalGW)
            act_irrWithdrawalSW = act_swAbstractionFraction * self.var.totalIrrDemand
            self.var.act_irrWithdrawal = act_irrWithdrawalSW + act_irrWithdrawalGW
            # (nonpaddy)
            act_irrnonpaddyGW = self.var.fracVegCover[3] * (1 - act_swAbstractionFraction) * \
                                self.var.irrDemand[3]
            act_irrnonpaddyGW = np.minimum(self.var.nonFossilGroundwaterAbs - act_nonIrrWithdrawalGW,
                                           act_irrnonpaddyGW)
            act_irrnonpaddySW = self.var.fracVegCover[3] * act_swAbstractionFraction * self.var.irrDemand[3]
            self.var.act_irrNonpaddyWithdrawal = act_irrnonpaddySW + act_irrnonpaddyGW
            # (paddy)
            act_irrpaddyGW = self.var.fracVegCover[2] * (1 - act_swAbstractionFraction) * self.var.irrDemand[2]
            act_irrpaddyGW = np.minimum(
                self.var.nonFossilGroundwaterAbs - act_nonIrrWithdrawalGW - act_irrnonpaddyGW, act_irrpaddyGW)
            act_irrpaddySW = self.var.fracVegCover[2] * act_swAbstractionFraction * self.var.irrDemand[2]
            self.var.act_irrPaddyWithdrawal = act_irrpaddySW + act_irrpaddyGW

            act_gw = act_nonIrrWithdrawalGW + act_irrWithdrawalGW
            # This should be equal to self.var.nonFossilGroundwaterAbs?


        else:  # only irrigation is considered

            self.var.act_nonIrrWithdrawal = globals.inZero.copy()

            # irrigated water demand:
            act_irrWithdrawalGW = self.var.totalIrrDemand * (1 - act_swAbstractionFraction)
            act_irrWithdrawalGW = np.minimum(self.var.nonFossilGroundwaterAbs, act_irrWithdrawalGW)
            act_irrWithdrawalSW = act_swAbstractionFraction * self.var.totalIrrDemand
            self.var.act_irrWithdrawal = act_irrWithdrawalSW + act_irrWithdrawalGW
            # (nonpaddy)
            act_irrnonpaddyGW = self.var.fracVegCover[3] * (1 - act_swAbstractionFraction) * \
                                self.var.irrDemand[3]
            act_irrnonpaddyGW = np.minimum(self.var.nonFossilGroundwaterAbs, act_irrnonpaddyGW)
            act_irrnonpaddySW = self.var.fracVegCover[3] * act_swAbstractionFraction * self.var.irrDemand[3]
            self.var.act_irrNonpaddyWithdrawal = act_irrnonpaddySW + act_irrnonpaddyGW
            # (paddy)
            act_irrpaddyGW = self.var.fracVegCover[2] * (1 - act_swAbstractionFraction) * self.var.irrDemand[2]
            act_irrpaddyGW = np.minimum(
                self.var.nonFossilGroundwaterAbs - act_irrnonpaddyGW, act_irrpaddyGW)
            act_irrpaddySW = self.var.fracVegCover[2] * act_swAbstractionFraction * self.var.irrDemand[2]
            self.var.act_irrPaddyWithdrawal = act_irrpaddySW + act_irrpaddyGW

            act_gw = np.copy(act_irrWithdrawalGW)

        # before 2026-11 minus unmetDemandPaddy / unmetDemandNonpaddy (carry-over of unmet demand), but these
        # were always 0: unmet = D - max(0, D - unmet_old) = min(D, unmet_old) stays 0 from a start of 0
        self.var.act_irrPaddyDemand = np.maximum(0, self.var.irrPaddyDemand)
        self.var.act_irrNonpaddyDemand = np.maximum(0, self.var.irrNonpaddyDemand)

        # unmet is either pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs or demand - withdrawal
        if self.var.includeIndusDomesDemand:  # all demands are taken into account
            self.var.unmetDemand = (self.var.totalIrrDemand - self.var.act_irrWithdrawal) + \
                                   (self.var.nonIrrDemand - self.var.act_nonIrrWithdrawal)
        else:  # only irrigation is considered
            self.var.unmetDemand = self.var.totalIrrDemand - self.var.act_irrWithdrawal

        return act_irrWithdrawalSW, act_irrWithdrawalGW, act_gw

    def unlimited(self, totalDemand, pot_Channel, pot_GW, unmet):
        """
        limitAbstraction = False: all demands are met, the rest is fossil groundwater (unmetDemand); with
        zonal_abstraction channel water and groundwater of the allocation zone are used first.

        Parameters
        ----------
        totalDemand : ndarray
            Total demand [m]
        pot_Channel, pot_GW, unmet : list of ndarray or None
            Potential channel and groundwater abstraction and unmet demand per sector (SECTORS order) [m]

        Returns
        -------
        ndarray
            act_gw: groundwater abstraction (MODFLOW pumping) [m]
        """

        if self.var.sectorSourceAbstractionFractions:
            pot_GW_Domestic, pot_GW_Livestock, pot_GW_Industry, pot_GW_Irrigation = pot_GW

        # limitAbstraction = False implies that all demands are satisfied.
        # zonal abstractions from channels will attempt to satisfy remaining surface water demands
        # Then, zonal groundwater will attempt to satisfy all groundwater demands
        # Then, unmetDemand = fossil water satisfies all remaining demands
        # limitAbstraction = False is not compatible with Modflow, however zonal channel abstraction should
        # be allowed. TODO: decouple limitAbstraction and channel zonal abstractions


        # This is the case when using ModFlow coupling (limitation imposed previously)
        # Modflow and limitAbstraction = False are not compatible.
        if self.var.modflow:
            # This is the case when using ModFlow coupling (limitation imposed previously)
            # part of the groundwater demand unsatisfied
            self.var.unmetDemand = self.var.pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs

            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.var.act_nonIrrWithdrawal = np.copy(self.var.nonIrrDemand)
            self.var.act_irrWithdrawal = np.copy(self.var.totalIrrDemand)

            act_gw = np.copy(self.var.nonFossilGroundwaterAbs)

        else:
            # Fossil groundwater abstractions are allowed (act = pot)
            if 'zonal_abstraction' in option and checkOption('zonal_abstraction'):
                # using allocation from abstraction zones (allocation_area x allocation_area cells)
                self.zonal(totalDemand, pot_Channel, pot_GW, unmet)
            else:  # no zonal abstraction (before 2026-11 the same block twice: option False or missing)
                self.var.unmetDemand = totalDemand - self.var.act_SurfaceWaterAbstract - self.var.nonFossilGroundwaterAbs
                if self.var.sectorSourceAbstractionFractions:
                    self.var.GW_Domestic = pot_GW_Domestic
                    self.var.GW_Industry = pot_GW_Industry
                    self.var.GW_Livestock = pot_GW_Livestock
                    self.var.GW_Irrigation = pot_GW_Irrigation

            if self.var.includeIndusDomesDemand:  # all demands are taken into account
                self.var.act_nonIrrWithdrawal = np.copy(self.var.nonIrrDemand)
            self.var.act_irrWithdrawal = np.copy(self.var.totalIrrDemand)

            act_gw = np.copy(self.var.pot_GroundwaterAbstract)

        self.var.act_irrNonpaddyWithdrawal = self.var.fracVegCover[3] * self.var.irrDemand[3]
        self.var.act_irrPaddyWithdrawal = self.var.fracVegCover[2] * self.var.irrDemand[2]

        self.var.act_irrNonpaddyDemand = self.var.act_irrNonpaddyWithdrawal.copy()
        self.var.act_irrPaddyDemand = self.var.act_irrPaddyWithdrawal.copy()

        # end of limit_abstraction = False

        return act_gw

    def zonal(self, totalDemand, pot_Channel, pot_GW, unmet):
        """
        Zonal abstraction (limitAbstraction = False, zonal_abstraction = True): the unmet demand of a cell is taken
        from the channel water and then the groundwater of its allocation zone (allocation_area x allocation_area
        cells); the rest is fossil groundwater. With sector fractions the zone water is split over the sectors.

        Parameters
        ----------
        totalDemand : ndarray
            Total demand [m]
        pot_Channel, pot_GW, unmet : list of ndarray or None
            Potential channel and groundwater abstraction and unmet demand per sector (SECTORS order) [m]
        """

        if self.var.sectorSourceAbstractionFractions:
            pot_Channel_Domestic, pot_Channel_Livestock, pot_Channel_Industry, pot_Channel_Irrigation = pot_Channel
            pot_GW_Domestic, pot_GW_Livestock, pot_GW_Industry, pot_GW_Irrigation = pot_GW
            unmet_Domestic, unmet_Livestock, unmet_Industry, unmet_Irrigation = unmet

        # using allocation from abstraction zone
        # this might be a regular grid e.g. 2x2 for 0.5 deg
        left_sf_avail = self.var.readAvlChannelStorageM  # already removed - self.var.act_channelAbst
        # sum demand, surface water - local used, groundwater - local use, not satisfied for allocation zone

        self.var.unmetDemand = totalDemand - self.var.act_SurfaceWaterAbstract - self.var.nonFossilGroundwaterAbs
        if self.var.sectorSourceAbstractionFractions:
            unmetChannel_Domestic = pot_Channel_Domestic - self.var.Channel_Domestic
            unmetChannel_Livestock = pot_Channel_Livestock - self.var.Channel_Livestock
            unmetChannel_Industry = pot_Channel_Industry - self.var.Channel_Industry
            unmetChannel_Irrigation = pot_Channel_Irrigation - self.var.Channel_Irrigation

            pot_Channel_Domestic = np.minimum(unmetChannel_Domestic, unmet_Domestic)
            pot_Channel_Livestock = np.minimum(unmetChannel_Livestock, unmet_Livestock)
            pot_Channel_Industry = np.minimum(unmetChannel_Industry, unmet_Industry)
            pot_Channel_Irrigation = np.minimum(unmetChannel_Irrigation, unmet_Irrigation)

            unmet_Channel = pot_Channel_Domestic + pot_Channel_Livestock \
                            + pot_Channel_Industry + pot_Channel_Irrigation
            unmetDemand_sw = unmet_Channel.copy()

            zoneDemand_sw = self.var.allocation_zoneIndex.total(unmet_Channel * self.var.cellArea) / self.var.cellArea


        else:
            # get the demand that still needs to be met

            #multiply with cellarea [m] -> [m3], otherwise bincount is not correct, divide again by cellarea to get [m] again
            unmetDemand_sw = np.minimum(self.var.unmetDemand,
                                        totalDemand * self.var.swAbstractionFraction- self.var.act_SurfaceWaterAbstract)
            zoneDemand_sw = self.var.allocation_zoneIndex.total(unmetDemand_sw * self.var.cellArea) / self.var.cellArea

        zone_sf_avail = self.var.allocation_zoneIndex.total(left_sf_avail * self.var.cellArea) / self.var.cellArea

        # zone abstraction is minimum of availability and demand [m3]
        zone_sf_abstraction = np.minimum(zoneDemand_sw, zone_sf_avail)
        # water taken from surface zone and allocated to cell demand

        # alternate formulation of following formula
        #cell_sf_abstraction = np.maximum(0., divideValues(left_sf_avail,
        #                                                  zone_sf_avail) * zone_sf_abstraction
        cell_sf_abstraction = np.maximum(0., np.where(zoneDemand_sw < zone_sf_avail,
                                                      divideValues(left_sf_avail, zone_sf_avail) * zoneDemand_sw, left_sf_avail))


        # the allocation doesn't need to be adapted because zone_sf_abstraction always <= zoneDemand
        # cell_sf_allocation shows for which cells demand is satisfied how much, whereas cell_sf_abstraction shows where water is abstracted
        cell_sf_allocation = np.maximum(0., divideValues(unmetDemand_sw,
                                                         zoneDemand_sw) * zone_sf_abstraction)

        # sum up with other abstraction
        self.var.act_SurfaceWaterAbstract = self.var.act_SurfaceWaterAbstract + cell_sf_abstraction
        self.var.act_channelAbst = self.var.act_channelAbst + cell_sf_abstraction

        if self.var.sectorSourceAbstractionFractions:
            # With zonal abstractions, cells can abstract more than their specific demands
            # In the case that abstractions are greater than demands, this is attributed
            # to Channel_Other
            (self.var.Channel_Domestic_fromZone, self.var.Channel_Livestock_fromZone,
             self.var.Channel_Industry_fromZone, self.var.Channel_Irrigation_fromZone), \
                self.var.Channel_Other = split_sectors(cell_sf_allocation, (
                    pot_Channel_Domestic, pot_Channel_Livestock, pot_Channel_Industry,
                    pot_Channel_Irrigation))
            self.var.Channel_Domestic += self.var.Channel_Domestic_fromZone
            self.var.Channel_Livestock += self.var.Channel_Livestock_fromZone
            self.var.Channel_Industry += self.var.Channel_Industry_fromZone
            self.var.Channel_Irrigation += self.var.Channel_Irrigation_fromZone

        # new potential groundwater abstraction
        self.var.pot_GroundwaterAbstract = \
            np.maximum(0., self.var.pot_GroundwaterAbstract - cell_sf_allocation)

        left_gw_demand = np.maximum(0., self.var.pot_GroundwaterAbstract - self.var.nonFossilGroundwaterAbs)
        left_gw_avail = np.maximum(0., self.var.readAvlStorGroundwater - self.var.nonFossilGroundwaterAbs)

        zone_gw_avail = self.var.allocation_zoneIndex.total(left_gw_avail * self.var.cellArea) / self.var.cellArea

        # for groundwater substract demand which is fulfilled by surface zone, calc abstraction and what
        # is left.
        zone_gw_demand = self.var.allocation_zoneIndex.total(left_gw_demand * self.var.cellArea) / self.var.cellArea
        #zone_gw_demand = zoneDemand - zone_sf_abstraction
        zone_gw_abstraction = np.minimum(zone_gw_demand, zone_gw_avail)
        # zone_unmetdemand = np.maximum(0., zone_gw_demand - zone_gw_abstraction)

        # water taken from groundwater zone and allocated to cell demand
        cell_gw_abstraction = np.maximum(0., np.where(zone_gw_demand < zone_gw_avail,
                                       divideValues(left_gw_avail, zone_gw_avail) * zone_gw_demand,
                                       left_gw_avail))
        #zone_gw_abstraction always <= zone_gw_demand
        cell_gw_allocation = \
            np.maximum(0., divideValues(left_gw_demand, zone_gw_demand) * zone_gw_abstraction)

        self.var.nonFossilGroundwaterAbs = self.var.nonFossilGroundwaterAbs + cell_gw_abstraction
        self.var.unmetDemand = np.maximum(0., left_gw_demand - cell_gw_allocation)

        # UNDER CONSTRUCTION
        if self.var.sectorSourceAbstractionFractions:

            # With zonal abstractions, cells can abstract more than their specific demands
            # In the case that abstractions are greater than demands, this is attributed
            # to GW_Other
            (self.var.GW_Domestic_fromZone, self.var.GW_Livestock_fromZone,
             self.var.GW_Industry_fromZone, self.var.GW_Irrigation_fromZone), \
                self.var.GW_Other = split_sectors(cell_gw_allocation, (
                    pot_GW_Domestic - self.var.GW_Domestic, pot_GW_Livestock - self.var.GW_Livestock,
                    pot_GW_Industry - self.var.GW_Industry, pot_GW_Irrigation - self.var.GW_Irrigation))
            self.var.GW_Domestic += self.var.GW_Domestic_fromZone
            self.var.GW_Livestock += self.var.GW_Livestock_fromZone
            self.var.GW_Industry += self.var.GW_Industry_fromZone
            self.var.GW_Irrigation += self.var.GW_Irrigation_fromZone

            # With zonal abstractions, cells can abstract more than their specific demands
            demand_satisfied = sum_vars(self.var, [source + '_' + sector for source in
                                                   ORDER_WITHDRAWAL_TOTAL for sector in SECTORS[:3]] +
                                        [s + '_Irrigation' for s in ORDER_WITHDRAWAL_SW + ('GW',)])

            self.var.unmetDemand = totalDemand - demand_satisfied

            # fossil groundwater: the rest up to pot_GW_* (at most the rest of the sector demand,
            # the channel water from the zone covers a part) is taken from fossil groundwater, as
            # without zonal abstraction (GW_* = pot_GW_* below). Before 2026-11 GW_* was only the
            # non-fossil part here, the consumption of the fossil water went to returnflowNonIrr
            # (= act_nonIrrWithdrawal (= nonIrrDemand) - act_nonIrrConsumption (from the GW_*))
            for sector, demand, pot_GW in (('Domestic', self.var.domesticDemand, pot_GW_Domestic),
                                           ('Livestock', self.var.livestockDemand, pot_GW_Livestock),
                                           ('Industry', self.var.industryDemand, pot_GW_Industry),
                                           ('Irrigation', self.var.totalIrrDemand, pot_GW_Irrigation)):
                GW = getattr(self.var, 'GW_' + sector)
                rest = demand - sum(getattr(self.var, source + '_' + sector) for source in
                                    ('Desal', 'Channel', 'wwt', 'Lift', 'Lake', 'Res')) - GW
                setattr(self.var, 'GW_' + sector, GW + np.maximum(0., np.minimum(pot_GW - GW, rest)))
