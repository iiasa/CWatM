# -------------------------------------------------------------------------
# Name:       CWATM Initial
# Purpose:
#
# Author:      PB
#
# Created:     16/05/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------


from hydrological_modules.miscInitial import *
from hydrological_modules.initcondition import *

from hydrological_modules.readmeteo import *
from hydrological_modules.inflow import *
from hydrological_modules.snow_frost import *
from hydrological_modules.soil import *
from hydrological_modules.landcoverType import *
from hydrological_modules.evaporation import *
from hydrological_modules.groundwater import *
from hydrological_modules.waterdemand import *
from hydrological_modules.capillarRise import *
from hydrological_modules.interception import *
from hydrological_modules.routing import *
from hydrological_modules.lakes_reservoirs import *

"""
from hydrological_modules.leafarea import *

from hydrological_modules.landusechange import *

from hydrological_modules.frost import *

from hydrological_modules.routing import *

from hydrological_modules.surface_routing import *
from hydrological_modules.reservoir import *
from hydrological_modules.lakes import *
from hydrological_modules.polder import *
from hydrological_modules.waterabstraction import *
from hydrological_modules.indicatorcalc import *

from hydrological_modules.riceirrigation import *

from hydrological_modules.evapowater import *
from hydrological_modules.transmission import *

from hydrological_modules.soilloop import *
from hydrological_modules.opensealed import *
from hydrological_modules.waterbalance import *
from hydrological_modules.waterlevel import *
from hydrological_modules.structures import *
"""


# --------------------------------------------
from pcraster import*
from pcraster.framework import *
from management_modules.data_handling import *
from management_modules.output import *



class CWATModel_ini(DynamicModel):

    """ CWATN initial part
        this part is to initialize the variables
        it will call the initial part of the hydrological modules
    """

    def __init__(self):
        """ init part of the initial part
            defines the mask map and the outlet points
            initialization of the hydrological modules
        """
        DynamicModel.__init__(self)

        ## MaskMap: the maskmap is flexible e.g. col,row,x1,y1  or x1,x2,y1,y2
        self.MaskMap = loadsetclone('MaskMap')


        # get the extent of the maps from the precipitation input maps
        # and the modelling extent from the MaskMap
        # cutmap[] defines the MaskMap inside the precipitation map
        cutmap[0], cutmap[1], cutmap[2], cutmap[
            3] = mapattrNetCDF(binding['E0Maps'])
        if option['writeNetcdfStack'] or option['writeNetcdf']:
            # if NetCDF is writen, the pr.nc is read to get the metadata
            # like projection
            metaNetCDF()

        # ----------------------------------------
        # include output of tss and maps
        self.output_module = outputTssMap(self)

        # include all the hydrological modules

        self.misc_module = miscInitial(self)
        self.init_module = initcondition(self)

        self.readmeteo_module = readmeteo(self)
        self.inflow_module = inflow(self)
        self.snowfrost_module = snow(self)
        self.soil_module = soil(self)
        self.landcoverType_module = landcoverType(self)
        self.evaporation_module = evaporation(self)
        self.groundwater_module = groundwater(self)
        self.waterdemand_module = waterdemand(self)
        self.capillarRise_module = capillarRise(self)
        self.interception_module = interception(self)
        self.routing_module = routing(self)
        self.lakes_reservoirs_module = lakes_reservoirs(self)

        # include output of tss and maps
        self.output_module = outputTssMap(self)

        """
        self.landusechange_module = landusechange(self)
        self.leafarea_module = leafarea(self)



        self.routing_module = routing(self)
        self.surface_routing_module = surface_routing(self)
        self.reservoir_module = reservoir(self)
        self.lakes_module = lakes(self)
        self.polder_module = polder(self)
#
        self.waterabstraction_module = waterabstraction(self)
        self.indicatorcalc_module = indicatorcalc(self)

        self.riceirrigation_module = riceirrigation(self)
        self.evapowater_module = evapowater(self)
        self.transmission_module = transmission(self)

        self.soilloop_module = soilloop(self)
        self.opensealed_module = opensealed(self)
        self.waterbalance_module = waterbalance(self)
        self.waterlevel_module = waterlevel(self)
        self.structures_module = structures(self)

        # --------------------------------------

        """


        # run intial misc to get all global variables
        self.misc_module.initial()
        self.init_module.initial()

        self.inflow_module.initial()
        self.snowfrost_module.initial()
        self.soil_module.initial()
        self.landcoverType_module.initial()
        self.groundwater_module.initial()
        self.waterdemand_module.initial()

        self.routing_module.initial()
        self.lakes_reservoirs_module.initial()

        self.output_module.initial()

        """
        # include output of tss and maps
        self.output_module = outputTssMap(self)

        MMaskMap = self.MaskMap
        # for checking maps

        self.ReportSteps = ReportSteps['rep']

        self.landusechange_module.initial()

        self.leafarea_module.initial()

        self.soil_module.initial()
        self.routing_module.initial()


        self.waterlevel_module.initial()

        self.surface_routing_module.initial()

        self.reservoir_module.initial()
        self.lakes_module.initial()
        self.polder_module.initial()

        self.transmission_module.initial()
        self.output_module.initial()

        self.structures_module.initial()
        # Structures such as reservoirs and lakes are modelled by interrupting the channel flow paths

        # ----------------------------------------------------------------------
        # ----------------------------------------------------------------------

        self.routing_module.initialSecond()
        # CHANNEL INITIAL SPLIT UP IN SECOND CHANNEL

        self.evapowater_module.initial()
        self.riceirrigation_module.initial()
        self.waterabstraction_module.initial()
        self.indicatorcalc_module.initial()

        self.waterbalance_module.initial()
        # calculate initial amount of water in the catchment
        """
# ====== INITIAL ================================
    def initial(self):
        """ Initial part of LISFLOOD
            calls the initial part of the hydrological modules
        """
