

############
Settingsfile
############

.. contents:: 
    :depth: 4

.. _rst_settingdoc:

Settings file
===============

The settings file is controlling the CWatM run

.. literalinclude:: _static/settings.ini
    :linenos:
    :language: ini
    :lines: 3-12

Components of the settings file
-------------------------------

General options
****************

General flags are set in the first paragraph
For example:

- if Temperature data are in unit ° Celsius ot Kelvin
- if OGGM glaciers is used
- if potential evaporation is calculated or precalculated is used
- if waterdemand is included
- if waterbodies are included
- AND many more

.. literalinclude:: _static/settings.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 15-116

	
NetCDF meta data
****************

The format for spatial data for input and output data is netCDF.
For output data the basic information are given in the settingsfile  

.. note::  From V1.10 the metadata.xml is always stored in the Python programm folder cwatm. 

.. literalinclude:: _static/settings.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 134-137		
	
For each output file the specific information about units, variable name, displayed variable name is given 
in the metaNetcdf.xml. See: :ref:`rst_metadata`
	
Path of data, output
********************

| Here the paths/folders/directories are defined
| It is a good pratice to use placeholder here, because then you have to change the paths only once

We include an Excel file, that holds information on crops and reservoirs. But it is only used if in [OPTIONS] *reservoir_add_info_in_Excel = True*

.. note:: 

   | Further on the pathes can be used as placeholders.
   | If you use them in the same section as defined: *$(PathRoot)*
   | if you use them in other sections: *$(FILE_PATHS:PathRoot)*   

.. literalinclude:: _static/settings.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 123-132


.. _rst_modelarea:
	
Defining the modeling area
***************************

In general the input data are stored and used at global scale.
The modeling area can be defined by:

* a mask map e.g.: $(FILE_PATHS:PathRoot)/source/rhine30min.tif
* coordinates e.g.: 14 12 0.5 5.0 52.0
* lowest point of a catchment e.g.: 6.25 51.75

.. note:: 

    | The mask map can be a .tif, PCraster or a netCDF format
    | The coordinates have the format: Number of Cols, Number of rows, cellsize, upper left corner X, upper left corner Y 
    | The point location (lon lat) will be used to create the catchment upstream of this point

.. warning:: If you use a mask map, make sure you do not use blanks in the file path or name! 


.. literalinclude:: _static/settings.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 139-160	

.. note:: 

    | If you start with a basin defined by the outlet of a basin e.g. 6.25 51.75
    | You can generate a new mask map for the following runs by:
    | **savebasinmap = True** in [OPTIONS]
	| 
    | a basin.tif is generated in the output folder, which you can copy and use next time as:
    | **MaskMap = your_directory/basin.tif**

Defining the time
*****************

The start and end time have to be defined.
Spin-up time is the time for warming up (results will be stored after the spin-up time)

.. note:: 

   | The time can be given as date: dd/mm/yyyy or as relative date: number (but then CalendarDayStart has to be defined)
   | Spin-up time can be given as date or number 
		
.. literalinclude:: _static/settings.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 160-172	


Initial conditions
***************************

Initial conditions can be stored and be loaded in order to initialise a warm start of the model

.. note:: Initial conditions are store as one netCDF file with all necessary variables

.. literalinclude:: _static/settings.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 174-187
	
StepInit indicate the date(s) when initial conditions are saved::

    StepInit = 31/12/1989 
    StepInit = 31/12/1989 31/12/2010
    StepInit = 31/12/1989 5y
    here: second value in StepInit is indicating a repetition of year(y), month(m) or day(d),
    e.g. 2y for every 2 years or 6m for every 6 month


Calibration
************

Any parameter can be used for calibration, but we used those which are most effective. See the :ref:`Calibration <rst_calibration>` for more information.

Calibration value can be a number (because it is not calibrated yet).

SnowFactor = 0.0045

Or a map:

SnowFactor = $(FILE_PATHS:PathParameter)/params_snowfactor.nc

.. literalinclude:: _static/settings.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 188-244


Information on processes
************************

| Information will be read in from values in the settings file
| As an example the value definitions for [SNOW] is shown:	

.. literalinclude:: _static/settings.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 328-355
	
.. note:: 

     | TemperatureLapseRate = 0.0065
     | for the variable TemperatureLapseRate the value of 0.0065 is set	

Variables can also be defined by spatial maps or map stacks
	
::

   tanslope = $(PathTopo)\tanslope.map
   forest_coverFractionNC   = $(PathForest)\coverFractionInputForest366days.nc

.. note:: 

   | suffix can be .map, but if there is no PCraster map it will look automatically for netCDF .nc
   | In most cases values can be replaced by map


Reading meteorological information
**********************************

| Meteorological information get be at coarser resolution (e.g. 5 arcmin) than the model is set up (e.g. 1 arcmin).
| CWatM is downscaling the coarser resolution on the fly, with monthly average values for precipitation and temperature.

.. note::

     | Precipitation data sometimes hve the unit [kg m-2s-1] and sometimes [kg m-2] or [mm]
	 | CWatM converts almost everything to [m]
	 | Therefore the *precipitation_coversion* converts e.g. from  [kg m-2s-1] to [m] with the factor: 86.4

.. literalinclude:: _static/settings.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 240-280

Using inflow
************

Inflow is using a timeseries of discharge for single grid cell(s) to put the value a the timeseries into the river(s) at these location as additiona; discharge

|If you defined in [Option] inflow = True. 
| You have to define the folder with inflow information, the inflow point(s) and the .csv file with the timeserie(s)

.. literalinclude:: _static/settings.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 916-932


Information on output
*********************

| We put OUTPUT as last section (easier to find)
| But in principle you can sort the [SECTIONS] in your preferable way

| Output should point to a folder, where the output should be stored.
| And the variables you want to store. For the format of output variables see: :ref:`rst_output` 

.. literalinclude:: _static/settings.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 954-964


Sections of information
-----------------------

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
----------------------

Example of a settings file:

.. literalinclude:: _static/settings.ini
    :linenos: