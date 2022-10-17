# -------------------------------------------------------------------------
# Name:       CWATM Initial
# Purpose:
#
# Author:      PB
#
# Created:     16/05/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------


from cwatm.hydrological_modules.miscInitial import miscInitial
from cwatm.hydrological_modules.initcondition import initcondition

from cwatm.hydrological_modules.readmeteo import readmeteo
from cwatm.hydrological_modules.evaporationPot import evaporationPot
from cwatm.hydrological_modules.inflow import inflow
from cwatm.hydrological_modules.snow_frost import snow_frost
from cwatm.hydrological_modules.soil import soil
from cwatm.hydrological_modules.landcoverType import landcoverType
from cwatm.hydrological_modules.sealed_water import sealed_water
from cwatm.hydrological_modules.evaporation import evaporation
from cwatm.hydrological_modules.groundwater import groundwater
from cwatm.hydrological_modules.groundwater_modflow.transient import groundwater_modflow
from cwatm.hydrological_modules.water_demand.water_demand import water_demand
from cwatm.hydrological_modules.water_demand.wastewater import waterdemand_wastewater as wastewater
from cwatm.hydrological_modules.capillarRise import capillarRise
from cwatm.hydrological_modules.interception import interception
from cwatm.hydrological_modules.runoff_concentration import runoff_concentration
from cwatm.hydrological_modules.lakes_res_small import lakes_res_small
from cwatm.hydrological_modules.waterbalance import waterbalance
from cwatm.hydrological_modules.environflow import environflow
from cwatm.hydrological_modules.routing_reservoirs.routing_kinematic import routing_kinematic
from cwatm.hydrological_modules.lakes_reservoirs import lakes_reservoirs
from cwatm.hydrological_modules.waterquality1 import waterquality1

from cwatm.management_modules.output import *
from cwatm.management_modules.data_handling import *
import os, glob


class Variables:
    def load_initial(self, name, default=0.0, number=None):
        """
        First it is checked if the initial value is given in the settings file

        * if it is <> None it is used directly
        * if None it is loaded from the init netcdf file

        :param name: Name of the init value
        :param default: default value -> default is 0.0
        :param number: in case of snow or runoff concentration several layers are included: number = no of the layer
        :return: spatial map or value of initial condition
        """

        if number is not None:
            name = name + str(number)

        if self.loadInit:
            map = readnetcdfInitial(self.initLoadFile, name)
            if Flags['calib']:
                self.initmap[name] = map
            return map
        else:
            return default

class Config:
    pass


class CWATModel_ini(DynamicModel):

    """
    CWATN initial part
    this part is to initialize the variables.
    It will call the initial part of the hydrological modules
    """

    def __init__(self):
        """
        Init part of the initial part
        defines the mask map and the outlet points
        initialization of the hydrological modules
        """

        DynamicModel.__init__(self)

        self.var = Variables()
        self.conf = Config()

        # ----------------------------------------
        # include output of tss and maps
        self.output_module = outputTssMap(self)

        # include all the hydrological modules
        self.misc_module = miscInitial(self)
        self.init_module = initcondition(self)
        self.waterbalance_module = waterbalance(self)
        self.readmeteo_module = readmeteo(self)
        self.environflow_module = environflow(self)
        self.evaporationPot_module = evaporationPot(self)
        self.inflow_module = inflow(self)
        self.snowfrost_module = snow_frost(self)
        self.soil_module = soil(self)
        self.landcoverType_module = landcoverType(self)
        self.evaporation_module = evaporation(self)
        self.groundwater_module = groundwater(self)
        self.groundwater_modflow_module = groundwater_modflow(self)
        self.waterdemand_module = water_demand(self)
        self.wastewater_module = wastewater(self)
        self.capillarRise_module = capillarRise(self)
        self.interception_module = interception(self)
        self.sealed_water_module = sealed_water(self)
        self.runoff_concentration_module = runoff_concentration(self)
        self.lakes_res_small_module = lakes_res_small(self)
        self.routing_kinematic_module = routing_kinematic(self)
        self.lakes_reservoirs_module = lakes_reservoirs(self)
        self.waterquality1 = waterquality1(self)
        self.waterbalance = waterbalance(self)

        # ----------------------------------------

        # reading of the metainformation of variables to put into output netcdfs
        metaNetCDF()

        # test if ModFlow coupling is used as defined in settings file
        self.var.modflow = False
        if "modflow_coupling" in option:
            self.var.modflow = checkOption('modflow_coupling')

        ## MakMap: the maskmap is flexible e.g. col,row,x1,y1  or x1,x2,y1,y2
        # set the maskmap
        self.MaskMap = loadsetclone(self, 'MaskMap')
        # run intial misc to get all global variables
        self.misc_module.initial()
        self.init_module.initial()

        self.readmeteo_module.initial()
        self.inflow_module.initial()

        self.evaporationPot_module.initial()

        self.snowfrost_module.initial()
        self.soil_module.initial()

        # groundwater before meteo, bc it checks steady state
        if self.var.modflow:
            self.groundwater_modflow_module.initial()
        else:
            self.groundwater_module.initial()

        self.landcoverType_module.initial()

        self.runoff_concentration_module.initial()
        self.lakes_res_small_module.initial()

        self.routing_kinematic_module.initial()
        if checkOption('includeWaterBodies'):
            self.lakes_reservoirs_module.initWaterbodies()
            self.lakes_reservoirs_module.initial_lakes()
            self.lakes_reservoirs_module.initial_reservoirs()

        self.waterdemand_module.initial()
        self.waterbalance_module.initial()
        # calculate initial amount of water in the catchment

        self.output_module.initial()
        self.environflow_module.initial()
        self.waterquality1.initial()


