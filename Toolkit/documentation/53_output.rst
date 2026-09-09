
##############
Output Options
##############

.. contents:: 
    :depth: 4
	

.. _rst_metadata:

Output meta information 
=======================

The format for spatial data for output data is netCDF.
The cwatm/metaNetcdf.xml includes information on the output netCDF files
e.g. description of the parameter, unit ..

In the meta data file information can be added  e.g. a description of the variable, unit

.. note:: It is not necessary to change this file! This is an option to put additional information into output maps

Example of a metaNetcdf.xml file:

.. literalinclude:: _static/metaNetcdf.xml


.. _rst_output:

Model Output
============

An advantage of **CWatM** is the full flexibility of the output variables.

- All parameters and variables can be used for output as maps or time series.
- Even if the model is run at daily timestep, output can be daily, monthly, annual, at the end of a run
- all variables maps are stored as netcdf and the meta data information can be added

Varity of outputs
-----------------

Time depending and non depending output maps
********************************************
	
| Output maps will be produced as spatial maps, stack of spatial maps (over time) 
| Format: `netCDF <http://www.unidata.ucar.edu/software/netcdf/>`_

The netCDF maps can be read with:

**Windows**

- `Panoply <http://www.giss.nasa.gov/tools/panoply>`_

**Linux**

- `ncview <http://meteora.ucsd.edu/~pierce/ncview_home_page.html>`_

- `cdo <https://www.unidata.ucar.edu/software/netcdf/workshops/2012/third_party/CDO.html>`_


Or time series at specified points
**********************************

| Timeseries are produced as ASCII .csv files, which can be read with every text editor or Excel
| If you need the old version .tss with you can read with `PCRaster Aquila <http://pcraster.geo.uu.nl/projects/developments/aguila/>`_
| you need to put reportOldTss = True in [Option]

| The specific point(s) where timeseries are provided are defined in the settings file as *Gauges*:
| Can be several points in the format lon lat lon lat ..

::
   
   # Station data
   # either a map e.g. $(FILE_PATHS:PathRoot)/data/areamaps/area3.map
   # or a location coordinates (X,Y) e.g. 5.75 52.25 9.25 49.75 )
   # Lobith/Rhine
   Gauges = 6.25 51.75 7.75 49.75
   
   # if .tif file for gauges, this is a flag if the file is global or local
   # e.g. Gauges = $(FILE_PATHS:PathRoot)/data/areamaps/gaugesRhine.tif
   GaugesLocal = True


Or time series as a catchment sum or average
********************************************

As standard, time series can include values of the specific cell as defined in the settings file as *Gauges*
But time series can also show the area sum or area average of the upstream catchment from the specific cell

for example
::
   
   [OUTPUT]
   # OUTPUT maps and timeseries
   # Standard values of a specific cell
   OUT_TSS_Daily = discharge
   OUT_TSS_AnnualAvg = Precipitation
   # Area sum of upstream catchment
   OUT_TSS_AreaSum_MonthTot = Precipitation, runoff
   # Area sum of upstream catchment
   OUT_TSS_AreaAvg_MonthTot = Precipitation




Format of output in the settings file
-------------------------------------

* per day [Daily]
* total month [MonthTot],  average month [MonthAvg], end of month [MonthEnd]
* total year  [AnnualTot], average year [AnnualAvg], end of year [AnnualEnd]
* total sum [TotalTot], total average [TotalAvg]

For each of the following sections output can be defined for different variables:

* Meteo
* Snow
* Soil for different land cover (forest, grassland, irrigated land, paddy irrigated)
* Water demand
* Groundwater
* River routing
* Lakes and reservoirs

**Or** output can be defined in the section *[output]*

An output directory can be defined and for each sort of output the variable(s) can be set:

| *OUT_* defines that this variable(s) are output
| *MAP_* or *TSS_* defines if it is a spatial map or a time series of point(s)
| *AreaSum_* or *AreaAvg_* after *TSS_* defines if the catchment sum of average upstream of the point is calculated
| *Daily* or *MonthAvg* or .. is specifying the time
| The variable is given after the equal sign e.g. * = discharge*
| If more than one variable should be used for output, split with **,**
| E.g. OUT_MAP_Daily = discharge -> daily spatial map of discharge

As example output for precipitation, temperature and discharge is shown here::

   # OUTPUT maps and timeseries
   OUT_Dir = $(FILE_PATHS:PathOut)
   OUT_MAP_Daily = 
   OUT_MAP_MonthEnd = 
   OUT_MAP_MonthTot = Precipitation, Tavg
   OUT_MAP_MonthAvg = 

   OUT_TSS_MonthTot = Precipitation, Tavg   # monthly total precipitation and average temperature
   OUT_TSS_Daily = discharge                # daily discharge
   OUT_TSS_MonthEnd = discharge
   OUT_TSS_AnnualEnd = discharge

   OUT_TSS_AreaSum_Daily = Precipitation    # daily sum of precipitation for the upstream catchment
   OUT_TSS_AreaAvg_MonthAvg = runoff        # monthly average sum of runoff for the upstream catchment

.. note:: For each variable the meta data information can be defined in :ref:`rst_metadata`


Output variables
----------------

Output can be every global defined variable in the model
Variable are e.g. Precipitation, runoff, baseflow

but also not so common variables as:

- reservoirStorage (amount of water in the reservoirs in [m3])
- nonIrrReturnFlowFraction (returnflow from domestic and industrial water use [m3])
- actualET[1] (actual evapotranspiration from grassland [m/day])
- ...


Most important output variables - a selection
*********************************************

::
   
   #Variable name    : Description
   discharge         : river discharge
   runoff            : runoff
   Precipitation     : rainfall + snow
   Tavg              : average temperature
   ETRef: potential  : evaporation from reference soil
   sum_gwRecharge    : total groundwater recharge
   totalET           : total actual evapotranspiration
   baseflow          : baseflow from groundwater
   ... (to be continued)



Output variables - a list
*************************

| A list of variables can be produced by using:
| grep -d recurse 'self.var.' \*.py 
| Every self.var.variable can be used as output variable
| For a description of the variable please take a look at the python module itself.
| .
| As output variable, use without self.var.

A list of possible output variables are in: **6 References** - List of variables.



Daily, monthly - at the end or average
--------------------------------------

* per day
* total month, average month, end of month
* total year, average year, end of year 
* total average, total at the end

available prefixes are: 'daily', 'monthtot','monthavg', 'monthend','annualtot','annualavg','annualend','totaltot','totalavg'

for example
::
   
   [OUTPUT]
   # OUTPUT maps and timeseries
   OUT_Dir = $(FILE_PATHS:PathOut)
   OUT_MAP_Daily = discharge, runoff, actualET[1]
   OUT_MAP_MonthAvg = Precipitation
   OUT_MAP_TotalEnd = lakeStorage
   OUT_MAP_TotalAvg = Tavg
   
   OUT_TSS_Daily = discharge
   OUT_TSS_MonthTot = runoff
   OUT_TSS_AnnualAvg = Precipitation
   OUT_TSS_AnnualTot = runoff

  
   
.. note:: For each variable the meta data information can be defined in :ref:`rst_metadata`

.. note:: We are not very precise when to use capital letter for some output variables. But we fear now, if we change the variable name, we will forget it somewhere.



