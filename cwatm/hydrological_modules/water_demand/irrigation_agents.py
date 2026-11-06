# -------------------------------------------------------------------------
# Name:        Waterdemand modules
# Purpose:     Irrigation agents: monthly withdrawal requests per agent area (adminSegments), irrigation
#              fractions switched off when a request is met, relaxation of the fractions.
#              Part of water_demand.py until 2026-11 (split).
#
# Author:      PB, MS
# Created:     05/11/2026
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import numpy as np
from cwatm.management_modules import globals
from cwatm.management_modules.globals import dateVar, option
from cwatm.management_modules.replace_pcr import npareaaverage, AreaIndex
from cwatm.management_modules.messages import CWATMError
from cwatm.management_modules.data_handling import binding, loadmap, divideValues, checkOption
from cwatm.hydrological_modules.water_demand.sector_demand import set_zero


class waterdemand_irrigation_agents(object):
    """
    Irrigation agents of the water demand.

    An agent is an area of adminSegments with a monthly request of surface water and/or groundwater for
    irrigation (irrigation_agent_SW/GW_request_month_m3). The withdrawal of each month is summed per agent; when it
    is above the request, the irrigation abstraction fractions of the agent are set to 0 until the next month. With
    relax_irrigation_agents the fractions are reduced (relax_abstraction_fraction_initial / counter) for agents which
    used more than 95 % of their request on day 10, and the counter goes back on day 28 if they used less than 98 %.

    **Global variables**

    =========================================  ==========    ================================================================  =====
    Variable [self.var]                        Type          Description                                                       Unit 
    =========================================  ==========    ================================================================  =====
    act_irrWithdrawalGW_month                  Array         Agents: groundwater withdrawal of the month (segment)             m3   
    act_irrWithdrawalSW_month                  Array         Agents: surface water withdrawal of the month (segment)           m3   
    activate_domestic_agents                   Flag          True if activate_domestic_agents = True                           bool 
    activate_irrigation_agents                 Flag          True if activate_irrigation_agents = True                         bool 
    adminSegments                              Array         Agent areas (administrative segments) of the irrigation agents    --   
    adminSegmentsIndex                         Object        Index of adminSegments for area total/average (AreaIndex)         --   
    cellArea                                   Array         Cell area                                                         m2   
    gwAbstractionFraction_Irrigation           Array         Input: share of the irrigation demand from groundwater            frac 
    InvCellArea                                Array         Inverse of the cell area                                          1 m-2
    irrWithdrawalGW_max                        Array         Agents: groundwater request per month (segment average)           m3   
    irrWithdrawalSW_max                        Array         Agents: surface water request per month (segment average)         m3   
    limitAbstraction                           Flag          True if limitAbstraction = True: no fossil groundwater            bool 
    load_initial                               Function      Function: loads a variable from the initial conditions            --   
    loadInit                                   Flag          True if initial conditions are loaded (initLoad)                  bool 
    ratio_irrWithdrawalGW_month                Array         Agents: groundwater withdrawal of the month / request             frac 
    ratio_irrWithdrawalSW_month                Array         Agents: surface water withdrawal of the month / request           frac 
    relax_abstraction_fraction_initial         Array         Agents: initial fraction after relaxation (default 0.5)           frac 
    relax_irrigation_agents                    Flag          True if relax_irrigation_agents = True                            bool 
    relaxGWagent                               Array         Agents: relax counter of the groundwater fraction                 --   
    relaxSWagent                               Array         Agents: relax counter of the surface water fraction               --   
    sectorSourceAbstractionFractions           Flag          True if sector- and source-specific abstraction fractions         bool 
    swAbstractionFraction_Channel_Irrigation   Array         Input: share of the irrigation demand from channels               frac 
    swAbstractionFraction_Lake_Irrigation      Array         Input: share of the irrigation demand from lakes                  frac 
    swAbstractionFraction_Lift_Irrigation      Array         Input: share of the irrigation demand from lift areas             frac 
    swAbstractionFraction_Res_Irrigation       Array         Input: share of the irrigation demand from reservoirs             frac 
    using_lift_areas                           Flag          True if using_lift_areas = True                                   bool 
    =========================================  ==========    ================================================================  =====

    """

    def __init__(self, model):
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Agent flags, agent areas (adminSegments, also used without agents by water_demand.dynamic_output),
        monthly requests, relax counters (from the initial conditions) and Error 180 (agents without adminSegments).
        """

        # Variables related to agents =========================
        self.var.activate_domestic_agents = False
        if 'activate_domestic_agents' in option:
            if checkOption('activate_domestic_agents'):
                self.var.activate_domestic_agents = True

        self.var.activate_irrigation_agents = False
        if 'activate_irrigation_agents' in option:
            if checkOption('activate_irrigation_agents'):
                self.var.activate_irrigation_agents = True

        set_zero(self.var, ['relaxGWagent', 'relaxSWagent', 'irrWithdrawalSW_max', 'irrWithdrawalGW_max'])

        # irrigation agents need adminSegments: without them the request maps (irrWithdrawal*_max) stay 0, the
        # irrigation abstraction is capped to 0 and relax_abstraction_fraction_initial does not exist
        if self.var.activate_irrigation_agents and 'adminSegments' not in binding and \
                ('irrigation_agent_SW_request_month_m3' in binding or 'irrigation_agent_GW_request_month_m3' in binding):
            raise CWATMError("Error 180: activate_irrigation_agents = True with irrigation_agent_*_request_month_m3 "
                             "but no adminSegments map in the settings file\n"
                             "Add adminSegments (the agent areas) or set activate_irrigation_agents = False\n")

        self.var.relax_irrigation_agents = False
        if 'relax_irrigation_agents' in option:
            if checkOption('relax_irrigation_agents'):
                self.var.relax_irrigation_agents = True

        if 'adminSegments' in binding:
            # adminSegments (administrative segment) are collections of cells that are associated together, ie Agents
            # Cells within the same administrative segment have the same positive integer value.
            # Cells with non-positive integer values are all associated together.
            # Irrigation agents use adminSegments

            self.var.adminSegments = loadmap('adminSegments').astype(int)
            self.var.adminSegments = np.where(self.var.adminSegments > 0, self.var.adminSegments, 0)
            # index for the area totals and averages per segment (adminSegments is not changed after this)
            self.var.adminSegmentsIndex = AreaIndex(self.var.adminSegments, onlypositive=False)

            if 'irrigation_agent_SW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                self.var.irrWithdrawalSW_max = npareaaverage(
                    loadmap('irrigation_agent_SW_request_month_m3') + globals.inZero.copy(),
                    self.var.adminSegments)

                # saved with relax_irrigation_agents (initcondition.py), also without relax_sw_agent
                if self.var.loadInit and ('relax_sw_agent' in binding or self.var.relax_irrigation_agents):
                    self.var.relaxSWagent = self.var.load_initial('relaxSWagent', default=globals.inZero.copy())
                elif 'relax_sw_agent' in binding:
                    self.var.relaxSWagent = loadmap('relax_sw_agent')

            if 'irrigation_agent_GW_request_month_m3' in binding and self.var.activate_irrigation_agents:
                self.var.irrWithdrawalGW_max = npareaaverage(
                    loadmap('irrigation_agent_GW_request_month_m3') + globals.inZero.copy(),
                    self.var.adminSegments)

                # saved with relax_irrigation_agents (initcondition.py), also without relax_gw_agent
                if self.var.loadInit and ('relax_gw_agent' in binding or self.var.relax_irrigation_agents):
                    self.var.relaxGWagent = self.var.load_initial('relaxGWagent', default=globals.inZero.copy())
                elif 'relax_gw_agent' in binding:
                    self.var.relaxGWagent = loadmap('relax_gw_agent')

            if 'relax_abstraction_fraction_initial' in binding:
                self.var.relax_abstraction_fraction_initial = loadmap('relax_abstraction_fraction_initial') + globals.inZero.copy()
            else:
                self.var.relax_abstraction_fraction_initial = 0.5 + globals.inZero.copy()

        # agents with a surface water / groundwater request (instead of the binding check every day)
        self.sw = self.var.activate_irrigation_agents and 'irrigation_agent_SW_request_month_m3' in binding
        self.gw = self.var.activate_irrigation_agents and 'irrigation_agent_GW_request_month_m3' in binding

    def update_fractions(self):
        """
        Start of a month: reset the monthly withdrawals, read the irrigation abstraction fractions again (they are
        set to 0 when a request is met) and reduce them by the relax counters.
        """

        self.var.act_irrWithdrawalSW_month = globals.inZero.copy()
        self.var.act_irrWithdrawalGW_month = globals.inZero.copy()

        if self.sw:

            # These are read at the beginning of each month as they are updated by several relax functions
            # and turned off once satisfying request
            if self.var.sectorSourceAbstractionFractions:
                self.var.swAbstractionFraction_Channel_Irrigation = loadmap('swAbstractionFraction_Channel_Irrigation')
                if self.var.using_lift_areas:
                    self.var.swAbstractionFraction_Lift_Irrigation = loadmap('swAbstractionFraction_Lift_Irrigation')
                self.var.swAbstractionFraction_Lake_Irrigation = loadmap('swAbstractionFraction_Lake_Irrigation')
                self.var.swAbstractionFraction_Res_Irrigation = loadmap('swAbstractionFraction_Res_Irrigation')
            else:
                self.var.swAbstractionFraction_Channel_Irrigation = 1 + globals.inZero.copy()
                if self.var.using_lift_areas:
                    self.var.swAbstractionFraction_Lift_Irrigation = 1 + globals.inZero.copy()
                self.var.swAbstractionFraction_Lake_Irrigation = 1 + globals.inZero.copy()
                self.var.swAbstractionFraction_Res_Irrigation = 1 + globals.inZero.copy()

            if self.var.relax_irrigation_agents:
                self.var.swAbstractionFraction_Channel_Irrigation = np.where(
                    self.var.relaxSWagent > 0,
                    self.var.relax_abstraction_fraction_initial / self.var.relaxSWagent,
                    self.var.swAbstractionFraction_Channel_Irrigation)
                if self.var.using_lift_areas:
                    self.var.swAbstractionFraction_Lift_Irrigation = np.where(
                        self.var.relaxSWagent > 0,
                        self.var.relax_abstraction_fraction_initial / self.var.relaxSWagent,
                        self.var.swAbstractionFraction_Lift_Irrigation)
                self.var.swAbstractionFraction_Lake_Irrigation = np.where(
                    self.var.relaxSWagent > 0,
                    self.var.relax_abstraction_fraction_initial / self.var.relaxSWagent,
                    self.var.swAbstractionFraction_Lake_Irrigation)
                self.var.swAbstractionFraction_Res_Irrigation = np.where(
                    self.var.relaxSWagent > 0,
                    self.var.relax_abstraction_fraction_initial / self.var.relaxSWagent,
                    self.var.swAbstractionFraction_Res_Irrigation)

        if self.gw:

            if self.var.sectorSourceAbstractionFractions and self.var.limitAbstraction:
                self.var.gwAbstractionFraction_Irrigation = loadmap('gwAbstractionFraction_Irrigation')
            else:
                self.var.gwAbstractionFraction_Irrigation = 1 + globals.inZero.copy()

            if self.var.relax_irrigation_agents:
                self.var.gwAbstractionFraction_Irrigation = np.where(
                    self.var.relaxGWagent > 0,
                    self.var.relax_abstraction_fraction_initial / self.var.relaxGWagent,
                    self.var.gwAbstractionFraction_Irrigation)

    def cap_sw(self, pot):
        """
        Limit a potential surface water abstraction for irrigation [m] by the monthly request of the agent.
        (Channel, Lift and Reservoirs - not Lakes and wastewater, as before the split)
        """
        if self.sw:
            return np.minimum(pot, self.var.irrWithdrawalSW_max * self.var.InvCellArea)
        return pot

    def cap_gw(self, pot):
        """
        Limit a potential groundwater abstraction for irrigation [m] by the monthly request of the agent.
        """
        if self.gw:
            return np.minimum(pot, self.var.irrWithdrawalGW_max * self.var.InvCellArea)
        return pot

    def end_of_day(self, act_irrWithdrawalSW, act_irrWithdrawalGW):
        """
        End of a day: add the irrigation withdrawal to the monthly total per agent, switch off the irrigation
        fractions of agents above their request, relax counters on day 10 and day 28.

        Parameters
        ----------
        act_irrWithdrawalSW, act_irrWithdrawalGW : ndarray or None
            Irrigation withdrawal from surface water / groundwater of the day [m] (None with limitAbstraction False,
            then only the relax counters are updated)
        """

        if 'adminSegments' in binding and self.var.limitAbstraction:

            self.var.act_irrWithdrawalSW_month += self.var.adminSegmentsIndex.total(
                act_irrWithdrawalSW * self.var.cellArea)

            if self.sw:
                self.var.swAbstractionFraction_Channel_Irrigation = np.where(
                    self.var.act_irrWithdrawalSW_month > self.var.irrWithdrawalSW_max, 0,
                    self.var.swAbstractionFraction_Channel_Irrigation)

                self.var.swAbstractionFraction_Lift_Irrigation = np.where(
                    self.var.act_irrWithdrawalSW_month > self.var.irrWithdrawalSW_max, 0,
                    self.var.swAbstractionFraction_Lift_Irrigation)

                self.var.swAbstractionFraction_Lake_Irrigation = np.where(
                    self.var.act_irrWithdrawalSW_month > self.var.irrWithdrawalSW_max, 0,
                    self.var.swAbstractionFraction_Lake_Irrigation)

                self.var.swAbstractionFraction_Res_Irrigation = np.where(
                    self.var.act_irrWithdrawalSW_month > self.var.irrWithdrawalSW_max, 0,
                    self.var.swAbstractionFraction_Res_Irrigation)

                # no division by 0 where the request is 0; such a segment that withdraws water is over its
                # request (inf as before 2026-11), 0/0 (was NaN) -> 0: same result in the > 0.95 / 0.98 tests
                self.var.ratio_irrWithdrawalSW_month = np.where(
                    (self.var.irrWithdrawalSW_max <= 0) & (self.var.act_irrWithdrawalSW_month > 0), np.inf,
                    divideValues(self.var.act_irrWithdrawalSW_month, self.var.irrWithdrawalSW_max))

        if 'adminSegments' in binding and self.var.limitAbstraction:
            self.var.act_irrWithdrawalGW_month += self.var.adminSegmentsIndex.total(
                act_irrWithdrawalGW * self.var.cellArea)
            if self.gw:
                self.var.gwAbstractionFraction_Irrigation = np.where(
                    self.var.act_irrWithdrawalGW_month > self.var.irrWithdrawalGW_max, 0,
                    self.var.gwAbstractionFraction_Irrigation)

                self.var.ratio_irrWithdrawalGW_month = np.where(
                    (self.var.irrWithdrawalGW_max <= 0) & (self.var.act_irrWithdrawalGW_month > 0), np.inf,
                    divideValues(self.var.act_irrWithdrawalGW_month, self.var.irrWithdrawalGW_max))

        if self.var.relax_irrigation_agents:
            if dateVar['currDate'].day == 10:
                if self.sw:
                    self.var.relaxSWagent += np.where(self.var.ratio_irrWithdrawalSW_month > 0.95, 1, 0)
                if self.gw:
                    self.var.relaxGWagent += np.where(self.var.ratio_irrWithdrawalGW_month > 0.95, 1, 0)

            # This will decrease values that have increased, but not on agents that were never too large
            if dateVar['currDate'].day == 28:
                if self.sw:
                    self.var.relaxSWagent -= np.where(self.var.relaxSWagent > 0,
                                                      np.where(self.var.ratio_irrWithdrawalSW_month > 0.98, 0, 1),
                                                      0)
                if self.gw:
                    self.var.relaxGWagent -= np.where(self.var.relaxGWagent > 0,
                                                      np.where(self.var.ratio_irrWithdrawalGW_month > 0.98, 0, 1),
                                                      0)
