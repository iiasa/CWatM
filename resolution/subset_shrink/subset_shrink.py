import shutil
from netCDF4 import Dataset
import numpy as np
import os
import time as timex
import gc

##
##  This program can be used to both 1. cut out a square subset from the global map, and 2. increase the resolution from 5min/0.25 degree to 1km


#input/Eingabe netCDF
files_doc = open('settings.txt', 'r')
FILES_ = [file.replace('\\', '/') for file in files_doc]
FILES = [file.split() for file in FILES_]

basin_name = FILES[0][-1]

latbounds = [float(FILES[2][3]), float(FILES[2][4])]
lonbounds = [float(FILES[3][3]), float(FILES[3][4])]


# Create target Directory if don't exist
if not os.path.exists(basin_name):
    os.mkdir(basin_name)
    print("Directory " + basin_name + " created. \n")
else:
    print("Directory " + basin_name + " already exists. \n")

#-------------------#

## !! make these file inputs
reso = 1/120.   #1/120.=0.008333... degree = 0.5 min = ~1km
                #1/12. = 0.08333... degree = 5 min = ~10km
                #1/4 = 0.25 degree = 15 min
                #1/2 degree = 30min = ~50km

## Functions/Funktionen

def loadnetcdfSubset():

    lats = f.variables['lat'][:]
    lons = f.variables['lon'][:]

    # latitude lower and upper index
    latli = np.argmin(np.abs(lats - latbounds[0]))
    latui = np.argmin(np.abs(lats - latbounds[1]))

    # longitude lower and upper index
    lonli = np.argmin(np.abs(lons - lonbounds[0]))
    lonui = np.argmin(np.abs(lons - lonbounds[1]))

    latl = lats[latli]
    latu = lats[latui]
    lonl = lons[lonli]
    lonu = lons[lonui]

    # time, latitude, longitude
    Subsets = []

    if time_dependent:

        for name in names:
            print('Loading/Lade ' + name + '.')
            if lats[0]<lats[1]:
                if lons[0]<lons[1]:
                    Subsets.append(f.variables[name][:, latli:latui, lonli:lonui])
                else:
                    Subsets.append(f.variables[name][:, latli:latui, lonui:lonli])
            elif lons[0]<lons[1]:
                Subsets.append(f.variables[name][:, latui:latli, lonli:lonui])
            else:
                Subsets.append(f.variables[name][:, latui:latli, lonui:lonli])
    else:
        for name in names:
            print('Loading/Lade ' + name + '.')
            if lats[0]<lats[1]:
                if lons[0]<lons[1]:
                    Subsets.append(f.variables[name][latli:latui, lonli:lonui])
                else:
                    Subsets.append(f.variables[name][latli:latui, lonui:lonli])
            elif lons[0]<lons[1]:
                Subsets.append(f.variables[name][latui:latli, lonli:lonui])
            else:
                Subsets.append(f.variables[name][latui:latli, lonui:lonli])

    return Subsets, latli, latui, lonli, lonui, latl, latu, lonl, lonu



def outputnetcdf(netfile, srclist):

    latitudes = np.arange(latl + reso/2, latu, reso)
    longitudes = np.arange(lonl + reso/2, lonu, reso)

    nf1 = Dataset(netfile, 'w', format='NETCDF4')

    nf1.date_created = timex.ctime(timex.time())
    #nf1.institution = f.institution
    nf1.title = f.title
    #nf1.source = f.source
    #nf1.description = f.description
    #nf1.Conventions = f.Conventions
    #nf1.esri_pe_string = f.esri_pe_string
    #nf1.keywords = f.keywords

    # -create dimensions - time is unlimited, others are fixed
    nf1.createDimension('lat', len(latitudes))
    nf1.createDimension('lon', len(longitudes))

    lat = nf1.createVariable('lat', 'f8', ('lat',))
    lat.long_name = 'latitude'
    lat.units = 'degrees_north'
    lat.standard_name = 'latitude'
    lon = nf1.createVariable('lon', 'f8', ('lon',))
    lon.standard_name = 'longitude'
    lon.long_name = 'longitude'
    lon.units = 'degrees_east'

    lat[:] = latitudes
    lon[:] = longitudes

    if time_dependent:
        nf1.createDimension('time', nsteps)
        time = nf1.createVariable('time', 'f8', ('time'))
        time.standard_name = 'time'
        time.units = 'Days since 1901-01-01'
        time.calendar = 'standard'

        time[:] = f.variables['time'][:]

    for src, varname, longname, unit in srclist:
        if time_dependent:
            value = nf1.createVariable(varname, 'f4', ('time', 'lat', 'lon'), fill_value=1.e+20, zlib=True)
        else:
            value = nf1.createVariable(varname, 'f4', ('lat', 'lon'), fill_value=1.e+20, zlib=True)
        value.standard_name = varname
        value.long_name = longname  # longName
        value.units = unit  # unitName
        value[:] = src

    nf1.close()


## The beginning / Der Anfang

# output/Ausgabe netCDF
for file_ in FILES[5:]:

    file = file_[0]
    f = Dataset(file)

    original_reso = abs(f.variables['lat'][1]-f.variables['lat'][2])
    kron_coeff = int(round(original_reso / reso))

    names = list(f.variables.keys())

    time_dependent = False
    if 'time' in names:
        time_dependent = True
        nsteps = len(f.variables['time'])

    for std in ['lat', 'lon', 'time']:
        if std in names:
            names.remove(std)

    name = (file.split('/')[-1]).split('.')[-2]
    file_type = file.split('.')[-1]

    resultlandcoverfile = name + '_' + basin_name + '_1km.' + file_type

    Subsets, latli, latui, lonli, lonui, latl, latu, lonl, lonu = loadnetcdfSubset()

    Subsets1km = []
    for type in Subsets:
        Subsets1km.append(np.kron(type, np.ones((kron_coeff, kron_coeff))))

    print('Resampling complete/abgeschlossen.')

    landcoverfracs = [[Subsets1km[i], names[i], names[i], '[-]'] for i in range(len(Subsets))]

    outputnetcdf(resultlandcoverfile, landcoverfracs)

    print('Subset extraction complete/abgeschlossen.\n')

    shutil.move(resultlandcoverfile, basin_name)

print('Complete/Abgeschlossen.')
