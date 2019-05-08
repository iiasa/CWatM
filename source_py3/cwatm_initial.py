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
from hydrological_modules.evaporationPot import *
from hydrological_modules.inflow import *
from hydrological_modules.snow_frost import *
from hydrological_modules.soil import *
from hydrological_modules.landcoverType import *
from hydrological_modules.sealed_water import *
from hydrological_modules.evaporation import *
from hydrological_modules.groundwater import *
from hydrological_modules.groundwater_modflow.groundwater_modflow import *

from hydrological_modules.waterdemand import *
from hydrological_modules.capillarRise import *
from hydrological_modules.interception import *
from hydrological_modules.runoff_concentration import *
from hydrological_modules.lakes_res_small import *

from hydrological_modules.waterbalance import *
from hydrological_modules.environflow import *

from hydrological_modules.routing_reservoirs.routing_kinematic import *
from hydrological_modules.lakes_reservoirs import *
from hydrological_modules.waterquality1 import *

# --------------------------------------------

#from management_modules.data_handling import *
from management_modules.output import *
import os, glob



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

        ## MakMap: the maskmap is flexible e.g. col,row,x1,y1  or x1,x2,y1,y2
        # set the maskmap
        self.MaskMap = loadsetclone('MaskMap')


        name = cbinding('PrecipitationMaps')
        #name1 = os.path.splitext(cbinding(('Ldd')))[0] + '.nc'
        nameall = glob.glob(os.path.normpath(name))
        if not nameall:
            raise CWATMFileError(name, sname='PrecipitationMaps')
        namemeteo = nameall[0]
        latmeteo, lonmeteo, cell, invcellmeteo = readCoordNetCDF(namemeteo)
        nameldd = cbinding('Ldd')
        #nameldd = os.path.splitext(nameldd)[0] + '.nc'
        #latldd, lonldd, cell, invcellldd = readCoordNetCDF(nameldd)
        latldd, lonldd, cell, invcellldd = readCoord(nameldd)
        maskmapAttr['reso_mask_meteo'] = round(invcellldd / invcellmeteo)


        # if meteo maps have the same extend as the other spatial static maps -> meteomapsscale = True
        self.meteomapsscale = True
        if invcellmeteo != invcellldd:
            if (not(Flags['quiet'])) and (not(Flags['veryquiet'])) and (not(Flags['check'])):
                msg = "Resolution of meteo forcing is " + str(maskmapAttr['reso_mask_meteo']) + " times higher than base maps."
                print(msg)
            self.meteomapsscale = False

        cutmap[0], cutmap[1], cutmap[2], cutmap[3] = mapattrNetCDF(nameldd)
        for i in range(4): cutmapFine[i] = cutmap[i]


        if not self.meteomapsscale:
            cutmapFine[0], cutmapFine[1],cutmapFine[2],cutmapFine[3],cutmapVfine[0], cutmapVfine[1],cutmapVfine[2],cutmapVfine[3]  = mapattrNetCDFMeteo(namemeteo)
            for i in range(4): cutmapGlobal[i] = cutmapFine[i]
            # for downscaling it is always cut from the global map
            if (latldd != latmeteo) or (lonldd != lonmeteo):
                cutmapGlobal[0] = int(cutmap[0] / maskmapAttr['reso_mask_meteo'])
                cutmapGlobal[2] = int(cutmap[2] / maskmapAttr['reso_mask_meteo'])
                cutmapGlobal[1] = int(cutmap[1] / maskmapAttr['reso_mask_meteo']+0.999)
                cutmapGlobal[3] = int(cutmap[3] / maskmapAttr['reso_mask_meteo']+0.999)

        if checkOption('writeNetcdfStack') or checkOption('writeNetcdf'):
            # if NetCDF is writen, the pr.nc is read to get the metadata
            # like projection
            metaNetCDF()


            if "coverresult" in binding:
                coverresult[0] = returnBool('coverresult')
                if coverresult[0]:
                    cover = loadmap('covermap', compress = False)
                    cover[cover > 1] = False
                    cover[cover == 1] = True
                    coverresult[1] = cover
                    #coverresult[1] = np.ma.array(cover, mask = covermask)


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
        self.snowfrost_module = snow(self)
        self.soil_module = soil(self)
        self.landcoverType_module = landcoverType(self)
        self.evaporation_module = evaporation(self)
        self.groundwater_module = groundwater(self)
        self.groundwater_modflow_module = groundwater_modflow(self)

        self.waterdemand_module = waterdemand(self)
        self.capillarRise_module = capillarRise(self)
        self.interception_module = interception(self)
        self.sealed_water_module = sealed_water(self)
        self.runoff_concentration_module = runoff_concentration(self)
        self.lakes_res_small_module = lakes_res_small(self)

        self.routing_kinematic_module = routing_kinematic(self)
        self.lakes_reservoirs_module = lakes_reservoirs(self)
        self.waterquality1 = waterquality1(self)

        # include output of tss and maps
        self.output_module = outputTssMap(self)
# ----------------------------------------------------------------


        # run intial misc to get all global variables
        self.misc_module.initial()
        self.init_module.initial()

        self.readmeteo_module.initial()
        self.inflow_module.initial()

        self.evaporationPot_module.initial()

        self.snowfrost_module.initial()
        self.soil_module.initial()

        self.groundwater_modflow_module.initial()
        # groundwater before meteo, bc it checks steady state


        self.landcoverType_module.initial()
        self.groundwater_module.initial()



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


