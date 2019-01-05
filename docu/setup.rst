
#######################
Setup of the model
#######################

.. contents:: 
    :depth: 4

Setup
=====
	
Requirements
------------

Python version
**************

NEW from 2019 on:
Requirements are a 64 bit `Python 3.7.x version <https://www.python.org/downloads/release/python-372/>`_

Reason for this step:

* Python 2.7 support ends in 2019
* We will be able to provide a better error handling
* We are able to provide an executable of CWATM for Windows


.. warning:: a 32 bit version is not able to handle the data requirements!

.. warning:: From 2019 on we are changing to Python 3.7. We do not provide further support for Python 2.7

Libraries
*********

These external libraries are needed:

* `Numpy <http://www.numpy.org>`_
* `Scipy <https://www.scipy.org>`_
* `netCDF4 <https://pypi.python.org/pypi/netCDF4>`_
* `GDAL <http://www.gdal.org>`_

**Windows**

The four libraries can be installed with pip or
downloaded at `Unofficial Windows Binaries for Python Extension Packages <http://www.lfd.uci.edu/~gohlke/pythonlibs>`_


Windows executeable Python version
**********************************

| A CWATM executable cwatm.exe can be used instead of the Python version

* ADVANTAGE: You can run it without installing or knowledge of Python
* DISADVANTAGE 1: You cannot see the source code or change it 
* DISADVANTAGE 2: We do not update this version as often as the Python version

* It is done with cx_freeze library 
* It includes all Python libraries

.. note::
    | A cwatmexe.zip (around 300 MB with all Python libraries) is stored on:
    | `Source code on Github repository of CWATM <https://github.com/CWatM/CWatM>`_

.. note::
    We recommend using the Python 3.7.x version, but if you not experienced in Python or have problems installing CWATM, please use the executable version.     

PCRaster
******** 

| CWATM is not using anymore anything from PCRaster
| But the general idea of PCraster to split the modules in a initial part and a dynamic part 
| is still used

| Anyway PCRaster is still a great tool
| PCRASTER from Faculty of Geosciences, Utrecht University, The Netherlands
| `Webpage of PCRaster <http://pcraster.geo.uu.nl>`_

| Reference:
| Karssenberg, D., Schmitz, O., Salamon, P., de Jong, K., and Bierkens, M. F. P.: A software framework for construction of process-based stochastic spatio-temporal models and data assimilation, Environmental Modelling & Software 25(4), 489-502, 2010. doi: 10.1016/j.envsoft.2009.10.004



C++ libraries
-------------

For the computational time demanding parts e.g. routing,
CWATM comes with a C++ library

Compiled versions
*****************

| **Windows and CYGWIN_NT-6.1**
| a compiled version is provided and CWATM is detecting automatically which system is running and which compiled version is needed

| **Linux**
| For Cygwin linux a compiled version *t5cyg.so* is provided in *../source/hydrological_modules/routing_reservoirs/* for version CYGWIN_NT-6.1.
| If you use another cygwin version please compile it by yourself and name it *t5_linux.so*

For Linux Ubuntu a compiled version is provided as *t5_linux.so*. The file is in *../source/hydrological_modules/routing_reservoirs/* 

.. note::
    If you use another Linux version or the compiled version is not working or you have a compiler which produce faster executables please compile a version on your own.


Compiling a version
*******************

C++ sourcecode is in *../source/hydrological_modules/routing_reservoirs/t5.cpp*

.. note::
    A compiled version is already provided for Windows and Linux.

**Windows**

A compiled version is provided, but maybe you have a faster compiler than the "Minimalist GNU for Windows" or "Microsoft Visual Studio 14.0" we used.

To compile with g++::

    ..\g++ -c -fPIC -Ofast t5.cpp -o t5.o
    ..\g++ -shared -Ofast -Wl,-soname,t5.so -o t5.so  t5.o
	
To compile with Microsoft Visual Studio 14.0::
 
    call "C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\bin\amd64/vcvars64.bat"
    cl /LD /O2 t5.cpp

.. note::

    We used Visual Studio, because it seems to be computational faster
	| the libray used with Windows is named *t5.dll*, if you generate a libray *t5.so* the filename in **../source/management_modules/globals.py** has to be changed!

**Linux**

To compile with g++::

    ..\g++ -c -fPIC -Ofast t5.cpp -o t5_linux.o
    ..\g++ -shared -Ofast -Wl,-soname,t5_linux.so -o t5_linux.so  t5_linux.o
	
	or
	
	..\g++ -c -Ofast t5.cpp -o t5_linux.o
    ..\g++ -shared -Ofast -Wl,-soname,t5_linux.so -o t5_linux.so  t5_linux.o


.. warning:: Please rename your compiled version to t5_linux.so! At the moment the file t5_linux.so is compiled with Ubuntu Linux


Test the model
--------------

**Windows and Linux**

python <modelpath>/cwatm.py 


The output should be::

   Running under platform:  Windows  **(or Linux etc)** 
   CWatM - Community Water Model
   Authors: ...
   Version: ...
   Date: ...
   
	
.. warning:: If python is not set in the environment path, the full path of python has to be used

.. warning:: Please use the right version of CWATM with the right version of Python (either 2.7 or 3.7)



Running the model
=================

Start the model
---------------

.. warning:: The model needs a settings file as an argument. See: :ref:`rst_settingdoc` 

**Windows**

python <modelpath>/cwatm.py settingsfile flags

example::

   python cwatm.py settings1.ini
   or with more information and an overview of computational runtime
   python cwatm.py settings1.ini -l -t
	
.. warning:: If python is not set in the environment path, the full path of python has to be used


**Linux**

<modelpath>/cwatm.py settingsfile flags

example::

    cwatm.py settings1.ini -l -t
	
Flags
*****

Flags can be used to change the runtime output on the screen

example::

    -q --quiet       output progression given as .
    -v --veryquiet   no output progression is given
    -l --loud        output progression given as time step, date and discharge
    -c --check       input maps and stack maps are checked, output for each input map BUT no model run
    -h --noheader    .tss file have no header and start immediately with the time series
    -t --printtime   the computation time for hydrological modules are printed
	-w --warranty    copyright and warranty information

	

Settings file
*************
	
The setup of the setings file is shown in the next chapter.
	
	
NetCDF meta data 
****************

The format for spatial data for output data is netCDF.
In the meta data file information can be added  e.g. a description of the parameter

.. note:: It is not necessary to change this file! This is an option to put additional information into output maps











.. _rst_settingdoc:

Settings file
===============

The settings file is controlling the CWATM run

.. literalinclude:: _static/settings1.ini
    :linenos:
    :language: ini
    :lines: 3-11

Components of the settings file
-------------------------------

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
    :lines: 130-142	


Initial conditions
***************************

Initial conditions can be stored and be loaded in order to initialise a warm start of the model

.. note:: Initial conditions are store as one netCDF file with all necessary variables

.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 145-158

	
Initial conditions can be put directly into the settings file.
Either as numbers or references to maps (.tif, PCraster or netCDF)

.. warning:: The values here (if not set to NONE) will overwrite the initial conditions of the general initial condition netCDF file

.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 335-337



.. _rst_outputone:

Output
*******



Output can be spatial/time as netCDF4 map stacks
  | and/or time series at specified points

.. note:: For additional information see :ref:`rst_outputtwo`

Output can be as maps and time series:

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

   OUT_TSS_MonthTot = Precipitation, Tavg
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
    :lines: 279-318
	
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

.. literalinclude:: _static/settings1.ini









NetCDF meta data
================

.. _rst_metadata:
	
Output Meta NetCDF information
------------------------------

The metaNetcdf.xml includes information on the output netCDF files
e.g. description of the parameter, unit ..

Example of a metaNetcdf.xml file:

.. literalinclude:: _static/metaNetcdf.xml


Name and location of the NetCDF meta data file
----------------------------------------------

In the settings file the name and location of the metadata file is given.

::
   
   #-------------------------------------------------------
   [NETCDF_ATTRIBUTES]
   institution = IIASA
   title = Global Water Model - WATCH WDFEI
   metaNetcdfFile = $(FILE_PATHS:PathRoot)/CWATM/source/metaNetcdf.xml


.. _rst_meta:






Initialisation
==============



CWATM needs to have estimates of the initial state of the internal storage variables, e.g. the amount of water stored in snow, soil, groundwater etc.

There are two possibilities:

1. The initial state of the internal storage variables are unknown and a **first** guess has to be used e.g. all storage variables are half filled.

2. The initial state is known from a previous run, where the variables are stored at a certain time step. This is called **warm start**

The the **warm start** is usful for:

* using a long pre-run to find the steady-state storage of the groundwater storage and use it as initial value

* using the stored variables to shorten the warm-up period

* using the stored variables to restart every day with the values from the pre3vious day (forecasting mode)

Example of soil moisture
------------------------

The next figure shows the impact of different initial condition on the soil moisture of the lower soil.
In one of the simulations the soil is initially almost ompletely saturated. In another simulation the soil is completely dry and the third simulation starts with initial conditions in between the two extremes.

In the beginning the effect of different initial condition can be seen clearly. But after one year the three curves converge. The **memory** of the lower soil goes back for about one year.

For all the initial condition apart from groundwater the memory is about 12 month. That means practically a spin-up of one year is sufficient to habve enough warm-up time.



.. figure:: _static/init_soilmoisture.jpg
    :width: 600px

Figure: Simulation of soil moisture in the lower soil with different initial conditions

For the groundwater zone a longer warm-up period is needed, because of the slow response of groundwater. Here a rather fast reacting groundwater storage is shown with the three curves coverge after two years.

.. figure:: _static/init_groundwater.jpg
    :width: 600px

Figure: Simulation of groundwater storage with different initial conditions



Cold start
----------

For a **cold start** the values of the storage variables are unknown and set to a "first" guess.
A list of variables and their default value for a **cold start** is given below in: :ref:`rst_initialcondition`

Set up a cold start in the settingsfile
***************************************

In the settings file the option: **load_initial** has to be set on **False**

.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 145-152


.. note:: It is possible to exclude the warming up period of your model run for further analysis of results by setting the **SpinUp** option

::
 
    [TIME-RELATED_CONSTANTS]
    SpinUp =  01/01/1995 
	
Storing initial variables 
-------------------------

In the settings file the option **save_intitisal** has to be set to **True**

The name of the initial netCDF4 file has to be put in **initsave**

and one or more dates have to be specified in StepInit

.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 154-158


	
Warm start
----------

CWATM can write internal variables to a netCDF file for choosen timesteps. These netCDF files can be used as the initial conditions for a suceeding simulation.

This is useful for establishing a steady-state with a long-term run and then using this steady-state for succeding simulations or for an every day run (forecasting mode)

.. warning:: If the parameters are changes after a run(especially the groundwater parameters) the stored initial values do not represent the conditions of the storage variables. Stored initial conditions should **not** be used as initial values for a model run with another set of parameters. If you do this during calibration, you will not be able to reproduce the calibration results!




Set up a cold start in the settingsfile
***************************************

In the settings file the option: **load_initial** has to be set on **True**
And define the name of the netcdf4 file in **initLoad**

.. note:: Use the initial values of the previous day here. E.g. if you run the model from 01/01/2006 use the inital condition from 31/12/2005

.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 145-152



.. _rst_initialcondition:

Initial conditions
------------------



.. csv-table:: 
   :header: "No.","Variable","Description", "Default value","Number of maps"
   :widths: 20,50, 100, 50,30
   
   "1","SnowCover","Snow cover for up to 7 zones","0","7"
   "2","FrostIndex","Degree days frost threshold","0","1"
   "3","Forest state","Interception storage","0","1"
   "","","Top water layer","0","1"
   "","","Soil storage for 3 soil layers","0","3"
   "4","Grassland state","Interception storage","0","1"
   "","","Top water layer","0","1"
   "","","Soil storage for 3 soil layers","0","3"
   "5","Paddy irrigation state","Interception storage","0","1"
   "","","Top water layer","0","1"
   "","","Soil storage for 3 soil layers","0","3"
   "6","Irrigation state","Interception storage","0","1"
   "","","Top water layer","0","1"
   "","","Soil storage for 3 soil layers","0","3"
   "7","Sealed area state","Interception storage","0","1"
   "8","Groundwater","Groundwater storage","0","1"   
   "9","Runoff concentration","10 layers of runoff concentration","0","10"  
   "10","Routing","Channel storage","0.2 * total cross section","1"  
   "","Routing","Riverbed exchange","0","1" 
   "","Routing","Discharge","depending on ini channel stor.","1" 
   "11","Lakes and Reservoirs","Lake inflow","from HydroLakes database","1" 
   "","","Lake outflow","same as lake inflow","1" 
   "","","Lake&Res outflow to other lakes&res","same as lake inflow","1" 
   "","","Lake storage","based on inflow and lake area","1" 
   "","","Reservoir storage","0.5 * max. reservoir storage","1" 
   "","","Small lake storage","based on inflow and lake area","1" 
   "","","Small lake inflow","from HydroLakes database","1" 
   "","","Small lake outflow","same as small lake inflow","1" 

.. _rst_outputtwo:

   
Model Output
============

An advantage of **CWATM** is the full flexibility of the output variables.

- All parameters and variables can be used for output as maps or time series.
- Even if the model is run at daily timestep, output can be daily, monthly, annual, at the end of a run
- all variables maps are stored as netcdf and the meta data information can be added

Time depending and non depending output maps
--------------------------------------------
	
| Output maps will be produced as spatial maps, stack of spatial maps (over time) 
| Format: `netCDF4 <http://www.unidata.ucar.edu/software/netcdf/>`_

The netCDF maps can be read with:

**Windows**

- `Panoply <http://www.giss.nasa.gov/tools/panoply>`_

**Linux**

- `ncview <http://meteora.ucsd.edu/~pierce/ncview_home_page.html>`_
- `cdo <https://www.unidata.ucar.edu/software/netcdf/workshops/2012/third_party/CDO.html>`_


Or time series at specified points
----------------------------------

| Timeseries are procuded as ASCII files, which can be read with every text editor
| or with `PCRaster Aquila <http://pcraster.geo.uu.nl/projects/developments/aguila/>`_

| The specific point where timeseries are provided are defined in the settings file as *Gauges*:

::
   
   # Station data
   # either a map e.g. $(FILE_PATHS:PathRoot)/data/areamaps/area3.map
   # or a location coordinates (X,Y) e.g. 5.75 52.25 9.25 49.75 )
   # Lobith/Rhine
   Gauges = 6.25 51.75
   
   # if .tif file for gauges, this is a flag if the file is global or local
   # e.g. Gauges = $(FILE_PATHS:PathRoot)/data/areamaps/gaugesRhine.tif
   GaugesLocal = True


Output variables
----------------

Output can be every global defined variable in the model
Variable are e.g. Precipitation, runoff, baseflow

but also not so common variables as:

- reservoirStorage (amount of water in the reservoirs in [m3])
- nonIrrReturnFlowFraction (returnflow from domenstic and industrial water use [m3])
- actualET[1] (actual evapotranspiration from grassland [m/day])
- ...



Daily, monthly - at the end or average
--------------------------------------

* per day
* total month, average month, end of month
* total year, average year, end of year 
* total average, total at the end

for example
::
   
   [OUTPUT]
   # OUTPUT maps and timeseries
   OUT_Dir = $(FILE_PATHS:PathOut)
   OUT_MAP_Daily = discharge, runoff
   OUT_MAP_MonthAvg = Precipitation
   OUT_MAP_TotalEnd = lakeStorage
   OUT_MAP_TotalAvg = Tavg
   
   OUT_TSS_Daily = discharge
   OUT_TSS_AnnualAvg = Precipitation

  
   
.. note:: For each variable the meta data information can be defined in :ref:`rst_metadata`

.. note:: For information how to adjust the output in the settings file see :ref:`rst_outputone`


Most important output variables - a selection
---------------------------------------------

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



Output variables - starting a list
----------------------------------

| A list of variables can be produced by using:
| grep -d recurse 'self.var.' *.py 
| Every self.var.variable can be used as output variable
| For a description of the variable please take a look at the python module itself.
| 
| As output variable please use without self.var.

::
   
   #Python_modul            Variable_name
   capillarRise.py          self.var.capRiseFrac 
   evaporationPot.py        self.var.AlbedoCanopy
   evaporationPot.py        self.var.AlbedoSoil
   evaporationPot.py        self.var.AlbedoWater
   evaporationPot.py        self.var.ETRef
   evaporationPot.py        self.var.EWRef
   evaporation.py           self.var.potBareSoilEvap 
   evaporation.py           self.var.snowEvap
   evaporation.py           self.var.SnowMelt
   evaporation.py           self.var.potBareSoilEvap 
   evaporation.py           self.var.cropKC[No] 
   evaporation.py           self.var.totalPotET[No] 
   evaporation.py           self.var.potTranspiration[No]
   groundwater.py           self.var.recessionCoeff 
   groundwater.py           self.var.specificYield 
   groundwater.py           self.var.kSatAquifer 
   groundwater.py           self.var.storGroundwater 
   groundwater.py           self.var.baseflow 
   interception.py          self.var.interceptCap[No]  
   interception.py          self.var.interceptStor[No] 
   interception.py          self.var.availWaterInfiltration[No] 
   interception.py          self.var.potTranspiration[No] 
   interception.py          self.var.actualET[No] 
   lakes_reservoirs.py      self.var.waterBodyID 
   lakes_reservoirs.py      self.var.waterBodyOut
   lakes_reservoirs.py      self.var.lakeArea
   lakes_reservoirs.py      self.var.lakeDis0
   lakes_reservoirs.py      self.var.lakeAC
   lakes_reservoirs.py      self.var.lakeEvaFactor
   lakes_reservoirs.py      self.var.reslakeoutflow
   lakes_reservoirs.py      self.var.lakeVolume
   lakes_reservoirs.py      self.var.lakeStorage
   lakes_reservoirs.py      self.var.lakeInflow
   lakes_reservoirs.py      self.var.lakeOutflow
   lakes_reservoirs.py      self.var.reservoirStorage
   lakes_reservoirs.py      self.var.lakeResStorage
   lakes_reservoirs.py      self.var.sumlakeResInflow
   lakes_reservoirs.py      self.var.sumlakeResOutflow
   lakes_res_small.py       self.var.smalllakeArea
   lakes_res_small.py       self.var.smalllakeDis0
   lakes_res_small.py       self.var.smalllakeA
   lakes_res_small.py       self.var.smalllakeFactor
   lakes_res_small.py       self.var.smalllakeVolumeM3
   lakes_res_small.py       self.var.smallevapWaterBodyStorage 
   landcoverType.py         self.var.coverTypes
   landcoverType.py         self.var.totalET
   landcoverType.py         self.var.actSurfaceWaterAbstract
   landcoverType.py         self.var.minInterceptCap
   landcoverType.py         self.var.interceptStor[No]
   landcoverType.py         self.var.sum_interceptStor
   landcoverType.py         self.var.minCropKC
   landcoverType.py         self.var.maxGWCapRise
   ... (to be continued)





