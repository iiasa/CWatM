
#######################
Settings file
#######################

.. contents:: 
    :depth: 3

.. _rst_settingdoc:

Settings file
===============

The settings file is controlling the CWATM run

.. literalinclude:: _static/settings1.ini
    :linenos:
    :language: ini
    :lines: 3-11


General flags
*************

General flags are set in the first paragraph
For example: If Temperature data are in unit ° Celsius ot Kelvin

.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 15-86

	
NetCDF meta data
****************

The format for spatial data for input and output data is netCDF.
For output data the basic information are given in the settingsfile  

.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 102-105		
	
For each output file the specific information about units, variable name, displayed variable name is given 
in the metaNetcdf.xml. See: :ref:`rst_metadata`
	
Path of data, output
********************

.. note:: Further on the pathes can be used as placeholders

.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 88-100	

	
Defining the modeling area
***************************

In general the input data are stored and used at global scale.
The modeling area can be defined by:

* a mask map
* coordinates 

.. note:: 

    The mask map can be a .tif, PCraster or a netCDF format
    | The coordinates have the format: Number of Cols, Number of rows, cellsize, upper left corner X, upper left corner Y 


.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 108-128	


Defining the time
*****************

The start and end time have to be defined.
Spin-up time is the time for warming up (results will be stored after the spin-up time)

.. note:: The time can be given as date: dd/mm/yyyy or as relative date: number (but then CalendarDayStart has to be defined)

.. note:: Spin-up time can be given as date or number 
	
	
.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 130-141	


Initial conditions
***************************

Initial conditions can be stored and be loaded in order to initialise a warm start of the model

.. note:: Initial conditions are store as one netCDF file with all necessary variables

.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 143-156

	
Initial conditions can be put directly into the settings file.
Either as numbers or references to maps (.tif, PCraster or netCDF)

.. warning:: The values here (if not set to NONE) will overwrite the initial conditions of the general initial condition netCDF file

.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 330-332


Output
***************************

Output can be spatial/time as netCDF4 map stacks
  | and/or time series at specified points

Output can be as maps and time series:

* per day
* total month, average month, end of month
* total year, average year, end of year 

For each of the following sections output can be defined for different variables:

* Meteo
* Snow
* Soil for different land cover (forest, grassland, irrigated land, paddy irrigated)
* Water demand
* Groundwater
* River routing
* Lakes and reservoirs

An output directory can be defined and for each sort of output the variable(s) can be set
As example output for precipitation, temperature and discharge is shown here::

   # OUTPUT maps and timeseries
   OUT_Dir = $(FILE_PATHS:PathOut)
   OUT_MAP_Daily = 
   OUT_MAP_MonthEnd = 
   OUT_MAP_MonthTot = Precipitation, Tavg
   OUT_MAP_MonthAvg = 

   OUT_TSS_MonthTot = Precipitation, Tavg


::
   
   # OUTPUT maps and timeseries
   OUT_Dir = $(FILE_PATHS:PathOut)
   OUT_MAP_Daily = discharge
   OUT_MAP_MonthEnd = 
   OUT_MAP_MonthTot =  

   OUT_TSS_Daily = discharge
   OUT_TSS_MonthEnd = discharge
   OUT_TSS_AnnualEnd = discharge

.. note:: For each variable the meta data information can be defined in :ref:`rst_metadata`


Reading information
***************************

Information will be read in from values in the settings file
Here the value definitions for [SNOW] is shown:	

.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 283-317
	
.. note:: TemperatureLapseRate = 0.0065
     | for the variable TemperatureLapseRate the value of 0.0065 is set	

Variables can also be defined by spatial maps or map stacks
	
::

   tanslope = $(PathTopo)\tanslope.map
   forest_coverFractionNC   = $(PathForest)\coverFractionInputForest366days.nc

.. note:: suffix can be .map, but if there is no PCraster map it will look automatically for netCDF .nc
	
.. warning:: in most cases values can be replaced by map

	
| ____________________________________________________________________________________________________________
| 

Sections of information
=======================

* Snow
* Frost
* General information on land cover types
* Soil
* Information for each of the six land cover types
	* Forest
	* Grassland
	* Paddy irrigated area
	* Irrigated area
	* Sealed area
	* Water covered area
* Interflow
* Groundwater
* Water demand
* Runoff concentration
* Routing
* Lakes and reservoirs
* Inflow

	
.. _rst_setting:	

Complete settings file
======================

Example of a settings file:

.. literalinclude:: _static/settings1.ini



