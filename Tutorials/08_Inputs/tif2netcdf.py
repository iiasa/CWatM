#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      burekpe
#
# Created:     16/01/2015
# Copyright:   (c) burekpe 2015
#-------------------------------------------------------------------------------

import numpy as np
from netCDF4 import Dataset
from netCDF4 import num2date, date2num
import time as timex
import datetime as date

from osgeo import gdal
from osgeo import osr
import os, sys


class ConvertMapsToNetCDF4():
    def __init__(self, attribute=None):

        # latitudes and longitudes
        reso = 0.5
        reso2 = reso/2.0
        lat1 = 90.0 - reso2
        lon1 = -180 + reso2

        self.latitudes = np.arange(lat1, -90.0, -reso)
        self.longitudes = np.arange(lon1, 180.0, reso)


        # netCDF format and attributes:
        self.format = 'NETCDF4_CLASSIC'
        self.attributeDictionary = {}
        if attribute == None:
            self.attributeDictionary['institution'] = "IIASA"
            self.attributeDictionary['title'] = "Soil ksat2"
            self.attributeDictionary['description'] = 'saturated soil conductivity'
        else:
            self.attributeDictionary = attribute


    def writeToNetCDF(self, ncFileName, varShortNames, varLongNames, varUnits,  timeAttribute=False):
        rootgrp = Dataset(ncFileName, 'w', format=self.format)

        # general Attributes
        rootgrp.history = 'Created ' + timex.ctime(timex.time())
        rootgrp.Conventions = 'CF-1.6'
        rootgrp.Source_Software = 'Python netCDF4_Classic'
        rootgrp.esri_pe_string = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]]'
        rootgrp.keywords = 'soil, hydraulic properties, Global'

        # -create dimensions - time is unlimited, others are fixed
        rootgrp.createDimension('lat', len(self.latitudes))
        rootgrp.createDimension('lon', len(self.longitudes))

        lat = rootgrp.createVariable('lat', 'f8', ('lat',))
        lat.long_name = 'latitude'
        lat.units = 'degrees_north'
        lat.standard_name = 'latitude'

        lon = rootgrp.createVariable('lon', 'f8', ('lon',))
        lon.standard_name = 'longitude'
        lon.long_name = 'longitude'
        lon.units = 'degrees_east'

        lat[:] = self.latitudes
        lon[:] = self.longitudes

        if timeAttribute:
            # rootgrp.createDimension('time',None)
            no = 2010-1900
            rootgrp.createDimension('time', no)
            # every 10 days

            date_time = rootgrp.createVariable('time', 'f4', ('time',))
            date_time.standard_name = 'time'
            date_time.long_name = 'Days since 1901-01-01'
            date_time.units = 'Days since 1901-01-01'
            date_time.calendar = 'standard'
        else:
            pass

        for i in range(0, len(varShortNames)):
            shortVarName = varShortNames[i]
            if varLongNames != None:
                longVarName = varLongNames[i]
            else:
                longVarName = shortVarName
            if varUnits != None:
                # unitVar = varUnits[i]
                unitVar = varUnits
            else:
                unitVar = 'undefined'
            if timeAttribute:
                var = rootgrp.createVariable(shortVarName, 'f4', ('time', 'lat', 'lon',), fill_value=1e20, zlib=True)
            else:
                var = rootgrp.createVariable(shortVarName, 'f4', ('lat', 'lon',), fill_value=1e20, zlib=True)
            var.standard_name = shortVarName
            var.long_name = longVarName
            var.units = unitVar

        attributeDictionary = self.attributeDictionary
        for k, v in attributeDictionary.items():
            setattr(rootgrp, k, v)

        rootgrp.sync()
        rootgrp.close()





# ------------------------------------
# ------------------------------------
# ------------------------------------

inDir = "./"
inName1 = inDir+"ksat2_2.tif"
outDir = "./"
netcdfOut = outDir + "ksat2_2.nc"
timeattr = False

varShortNames = ['ksat2']
varLongNames = ['saturated soil conditivity layer2']
# We have to standardize units based on  the CF convention.
varUnits = '[cm]'

newMap = ConvertMapsToNetCDF4(attribute=None)
newMap.writeToNetCDF(netcdfOut, varShortNames, varLongNames,  varUnits, timeAttribute=timeattr)

startingDate = '1901-01-01'
date_units = 'Days since 1901-01-01'
date_calendar = 'standard'



# ------------------------------------
# ------------------------------------
# ------------------------------------

timedelta1 =[]
shortVarName = varShortNames[0]

# read from tif
nf2 = Dataset(netcdfOut, 'a')

if timeattr:
    i = 0
    for year in xrange(1901,2011):
        inName = inName1 + str(year)+".tif"
        print (year, inName)

        timeStamp = date.datetime(year, 1, 1)
        t = date2num(timeStamp, date_units, date_calendar)

        ds = gdal.Open(inName)
        cols = ds.RasterXSize
        rows = ds.RasterYSize
        value = np.array(ds.GetRasterBand(1).ReadAsArray())

        nf2.variables['time'][i] = date2num(timeStamp, date_units, date_calendar)
        nf2.variables[shortVarName][i, :, :] = (value)
        # close dataset
        ds = None
        i += 1

else:
    ds = gdal.Open(inName1)
    cols = ds.RasterXSize
    rows = ds.RasterYSize
    value = np.array(ds.GetRasterBand(1).ReadAsArray())
    
    value[value<0] = np.nan
    nf2.variables[shortVarName][:, :] = (value)

nf2.close()
print ("Done")


