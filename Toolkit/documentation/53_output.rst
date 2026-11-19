
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

   # optional: names of the stations, separated by space or comma (a name cannot include a space or comma)
   GaugesNames = Lobith Kaub

| With *GaugesNames* the column headers of the .csv files (row 4) change from G1, G2 .. to G1_Lobith, G2_Kaub ..
| The n-th name belongs to the n-th station (order of the coordinates in *Gauges*, or increasing gauge ID of a map).
| Stations without a name keep G<n>, names without a station are ignored.
| The columns R<ID> of OUT_RES<n>_ and the WaterCycle/WaterBalance headers are not changed.

| All netCDF output maps get the global attribute *Gauges*: for each gauge name, lat, lon (or y, x for a
| projected grid) and upstream area [km2], separated by blanks; the gauges are separated by ";", e.g.
| Gauges: G1_Lobith 51.8500 6.1400 161975.5; G2_Kaub 50.2500 7.7500 140664.4


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


Or time series at lakes and reservoirs
**************************************

| Time series can also be written at the outlet cell of each lake, reservoir or wetland (water body) instead of the *Gauges*.
| The key is *OUT_RES<n>_* + the time (Daily, MonthTot, MonthAvg, MonthEnd, AnnualTot, AnnualAvg, AnnualEnd).
| *n* is the type of the water body (type from the map waterBodyTyp or from the Excel sheet *Reservoirs*):

* 0 = all water bodies (type 1 to 6), *OUT_RES_* without a number is the same as *OUT_RES0_*
* 1 = lakes
* 2 = reservoirs
* 3 = lake and reservoir
* 4 = reservoir type 4 (pass-through of the inflow)
* 5 = reservoir type 5 (water transfer point, no retention, no evaporation)
* 6 = wetlands

| The water bodies are the ones in *waterBodyID* (e.g. lakeresID.nc) and the new ones of the Excel sheet *Reservoirs* inside the mask map.
| A reservoir without volume (run as a lake) keeps its type 2 or 3.
| The file is named <variable>_res<n>_<time>.csv e.g. reservoir_transfers_out_M3_res5_daily.csv.
| The columns are the water body IDs e.g. R4000006, sorted by ID, with the x, y of the outlet cell.
| If there is no water body of type n in the model, a warning is given and no file is written.
| TotalTot, TotalAvg (Error 181) and WaterCycle, WaterBalance (Error 182) are not possible.

for example
::

   [OUTPUT]
   OUT_Dir = $(FILE_PATHS:PathOut)
   # storage of all lakes and reservoirs
   OUT_RES0_Daily = lakeResStorage
   # monthly average storage of the reservoirs
   OUT_RES2_MonthAvg = resStorage
   # water given by the transfer points
   OUT_RES5_Daily = reservoir_transfers_out_M3


Suffix for the output file names
--------------------------------

| With the optional key OUT_suffix all output files (OUT_TSS_..., OUT_MAP_..., OUT_RES...) get a suffix at the end of the name,
| e.g. discharge_daily_<suffix>.csv or tws_monthend_<suffix>.nc. Without OUT_suffix (or with an empty value) the names are as before.
| One OUT_suffix is used for the output of all sections. Characters which are not possible in a file name (< > : " / \\ | ? *) give Error 184.

for example
::

   [FILE_PATHS]
   ScenarioName = TestScenario

   [OUTPUT]
   OUT_Dir = $(FILE_PATHS:PathOut)
   OUT_suffix = $(FILE_PATHS:ScenarioName)
   # -> discharge_daily_TestScenario.csv
   OUT_TSS_Daily = discharge




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
| *RES<n>_* instead of *TSS_* gives a time series at the outlets of the lakes / reservoirs of type n (see above)
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



