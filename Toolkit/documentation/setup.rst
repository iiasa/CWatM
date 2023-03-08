
#######################
Setup of the model
#######################

.. contents:: 
    :depth: 4

.. _rst_setupdoc:

Setup python version
====================
	
Python
---------------

Requirements are a 64-bit `Python 3.7.x or 3.8.x version <https://www.python.org/downloads/>`_

.. warning:: a 32-bit version is not able to handle the data requirements!

.. warning:: CWatM is tested for Python 3.7 and 3.8 and will for sure not work with Python versions lower than 3.6. We recommend using Python 3.7 or 3.8

External libraries
-------------------

These external libraries are needed:

* `NumPy <http://www.numpy.org>`_
* `SciPy <https://www.scipy.org>`_
* `netCDF4 <https://pypi.python.org/pypi/netCDF4>`_
* `GDAL <http://www.gdal.org>`_

The four libraries can be installed with conda, pip or downloaded at `Unofficial Windows Binaries for Python Extension Packages <http://www.lfd.uci.edu/~gohlke/pythonlibs>`_

Additional libraries for CWatM - MODFLOW

* `FloPy <https://www.usgs.gov/software/flopy-python-package-creating-running-and-post-processing-modflow-based-models>`_
* `xmipy <https://pypi.org/project/xmipy>`_

Additional libraries for CWatM - crop specific

* `Pandas <https://pandas.pydata.org>`_
* `xlrd <https://xlrd.readthedocs.io>`_
* `openpyxl <https://openpyxl.readthedocs.io/en/stable>`_


.. warning::
   | **Troublemaker GDAL**
   | Installing GDAL via pip causes sometimes problems. We recommend downloading the library from
   | `Unofficial Windows Binaries for Python Extension Packages <http://www.lfd.uci.edu/~gohlke/pythonlibs>`_ 
   | as GDAL-3.0.4-cp37-cp37m-win_amd64.whl (or a later version depending on your Python version) and installing them as: 
   | pip install C:/Users/XXXXX/Downloads/GDAL-3.0.4-cp37-cp37m-win_amd64.whl
   | 
   | Sometimes problems occure if you have installed GDAL separately (or a software did, like QGIS)
   

.. warning::
   | **Still troublemaker GDAL**  
   | for Python version 3.8 we changed import gdal to:
   | from osgeo import gdal
   | from osgeo import osr
   | from osgeo import gdalconst   
   | gdal can be installed for Python 3.8 from pip or conda

Installing
------------

Finally the model can be installed with pip.

.. code-block:: python

   pip install git+git://github.com/iiasa/CWatM

or directly downloaded via **'clone or download'** from: https://github.com/iiasa/CWatM

and installing them in a folder.

C++ libraries
----------------

For the computational time demanding parts e.g. routing, CWatM comes with a C++ library. A pre-compiled version is included for Windows and Linux. Normally, you don't have to do anything and the pre-compiled version should just work.

Pre-compiled C++ libraries
****************************

| **Windows and CYGWIN_NT-6.1**
| a compiled version is provided and CWatM is detecting automatically which system is running and which compiled version is needed

| **Linux**
| For Cygwin linux a compiled version *t5cyg.so* is provided in *../cwatm/hydrological_modules/routing_reservoirs/* for version CYGWIN_NT-6.1.
| If you use another cygwin version please compile it by yourself and name it *t5_linux.so*

For Linux Ubuntu a compiled version is provided as *t5_linux.so*. The file is in *../cwatm/hydrological_modules/routing_reservoirs/* 

.. note::
    If you use another Linux version or the compiled version is not working or you have a compiler which produce faster executables please compile a version on your own.


Compiling a version
*****************************

C++ sourcecode is in *../cwatm/hydrological_modules/routing_reservoirs/t5.cpp*

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
	| the libray used with Windows is named *t5.dll*, if you generate a libray *t5.so* the filename in **../cwatm/management_modules/globals.py** has to be changed!

**Linux**

To compile with g++::

    ..\g++ -c -fPIC -Ofast t5.cpp -o t5_linux.o
    ..\g++ -shared -Ofast -Wl,-soname,t5_linux.so -o t5_linux.so  t5_linux.o
	
	or
	
	..\g++ -c -Ofast t5.cpp -o t5_linux.o
    ..\g++ -shared -Ofast -Wl,-soname,t5_linux.so -o t5_linux.so  t5_linux.o


.. warning:: Please rename your compiled version to t5_linux.so! At the moment the file t5_linux.so is compiled with Ubuntu Linux


Error and exeption handling
---------------------------

We try to make our program behave properly when encountering unexpected conditions. Therefore we caption a number of possible wrong inputs.

If you get an output with an error number please look at :ref:`rst_error`


Test the Python version
-------------------------

Run from the command line::

    run_cwatm
    or
    python run_cwatm.py if you installed CWatM not with pip

The output should be::

   Running under platform:  Windows  **(or Linux etc)** 
   CWatM - Community Water Model
   Authors: ...
   Version: ...
   Date: ...
	
.. warning:: If python is not set in the environment path, the full path of python has to be used

.. warning:: Please use the right version of CWatM with the right version of Python (either 3.7 or 3.8)


Run the Python version
-----------------------------

Run from the command line::

    run_cwatm settingsfile flags
    or
    python run_cwatm settingsfile flags
    
    

example::

   python run_cwatm settings1.ini

or with more information and an overview of computational runtime::

   python run_cwatm settings1.ini -l -t
	
.. warning:: If python is not set in the environment path, the full path of python has to be used

.. warning:: The model needs a settings file as an argument. See: :ref:`rst_settingdoc` 


.. note:: it is also possible to use paths with white spaces or dots. An easy way to avoid this is using relative paths, but is is also possible with absolute paths.

::

    "C:/Python 37/python" "C:/CWatM Hydrologic.modeling/CWatM/run_cwatm.py" "C:/CWatM Hydrologic.modeling/settings .rhine30min.ini" -l
    
    But in the settingsfile do not use apostrophe "" or '':
    PathRoot = C:/CWatM Hydrologic.modeling
   
	
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


Windows executable Python version
===================================

| A CWatM executable cwatm.exe can be used instead of the Python version

* ADVANTAGE: You can run it without installing or knowledge of Python
* DISADVANTAGE 1: You cannot see the source code or change it 
* DISADVANTAGE 2: We do not update this version as often as the Python version

* It is done with cx_freeze library 
* It includes all Python libraries

.. note::
    | A cwatmexe.zip (around 300 MB with all Python libraries) is stored on:
    | `Source code on Github repository of CWatM <https://github.com/iiasa/CWatM>`_
    | `Executable cwatmexe.zip on Github repository of CWatM <https://github.com/iiasa/CWatM/tree/version1.05/tutorial/CWATM_model>`_

.. note::
    | We recommend using the Python 3.7.x version, 
    | but if you not experienced in Python or have problems installing CWatM, please use the executable version.     
    | Either start it in DOS box (command cmd), or use the batch file cwatmbat.bat to start it


.. todo::
    We will put a whole example of 30 deg Rhine basin with all necessary data in another zip file. Just for an easier start.


	
NetCDF meta data 
=================

The format for spatial data for output data is netCDF.
In the meta data file information can be added  e.g. a description of the parameter

.. note:: It is not necessary to change this file! This is an option to put additional information into output maps


Test the data
==================

| The model is only as good as the data!
| To give out a list of data and to check the data the model can run a check.

example::

   python run_cwatm settings1.ini -c
   or
   python run_cwatm settings1.ini -c > checkdata.txt 

A list is created with::

   Name:      Name of the variable
   Filename:  filename or if the value if it is a fixed value
   nonMV:     non missing value in 2D map
   MV:        missing value in 2D map
   lon-lat:   longitude x latitude of 2D map
   CompressV: 2D is compressed to 1D?
   MV-comp:   missing value in 1D
   Zero-comp: Number of 0 in 1D
   NonZero:   Number of non 0 in 1D
   min:       minimum in 1D (or 2D)
   mean:      mean in 1D (or 2D)
   max:       maximum in 1D (or 2D)
   
example::

   Name                          File/Value                                    nonMV         MV    lon-lat   Compress    MV-comp  Zero-comp    NonZero        min       mean        max
   MaskMap                       put5min_netcdf/areamaps/rhine5min.map          5236          0      68x77      False          0       2404       2832       0.00       0.54       1.00
   Ldd                           _5min/input5min_netcdf/routing/ldd.nc          5236          0      68x77      False          0          0       5236       1.00       5.34       9.00
   Mask+Ldd                                                                     2832          0      68x77       True          0       2832          0       0.00       0.00       0.00
   CellArea                      n_netcdf/landsurface/topo/cellarea.nc          2832          0      68x77       True          0          0       2832   5.31E+07   5.63E+07   5.94E+07
   precipitation_coversion       86.4                                              -          -          -          -          -                 86.40           
   evaporation_coversion         1.00                                              -          -          -          -          -                  1.00           
   crop_correct                  1.534                                             -          -          -          -          -                  1.53           
   NumberSnowLayers              7                                                 -          -          -          -          -                  7.00           
   GlacierTransportZone          3                                                 -          -          -          -          -                  3.00           
   ElevationStD                  min_netcdf/landsurface/topo/elvstd.nc          2832          0      68x77       True          0          0       2832       0.04      78.67     672.68
   ...
   ...


.. _rst_settingdoc:

Settings file
===============

The settings file is controlling the CWatM run

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


.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 108-128	

.. note:: 

    | If you start with a basin defined by the outlet of a basin e.g. 6.25 51.75
    | You can generate a new mask map for the following runs by:
    | **savebasinmap = True** in [OPTIONS]
    | a basin.tif is generated in the output folder, which you can copy and use next time as:
    | **MaskMap = your_directory/basin.tif**

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

	
StepInit indicate the date(s) when initial conditions are saved::

    StepInit = 31/12/1989 
    StepInit = 31/12/1989 31/12/2010
    StepInit = 31/12/1989 5y
    here: second value in StepInit is indicating a repetition of year(y), month(m) or day(d),
    e.g. 2y for every 2 years or 6m for every 6 month



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
    :linenos:



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
   metaNetcdfFile = $(FILE_PATHS:PathRoot)/cwatm/metaNetcdf.xml


.. _rst_meta:






Initialisation
==============



CWatM needs to have estimates of the initial state of the internal storage variables, e.g. the amount of water stored in snow, soil, groundwater etc.

There are two possibilities:

1. The initial state of the internal storage variables are unknown and a **first** guess has to be used e.g. all storage variables are half filled.

2. The initial state is known from a previous run, where the variables are stored at a certain time step. This is called **warm start**

The **warm start** is usful for:

* using a long pre-run to find the steady-state storage of the groundwater storage and use it as initial value

* using the stored variables to shorten the warm-up period

* using the stored variables to restart every day with the values from the previous day (forecasting mode)

Example of soil moisture
------------------------

The next figure shows the impact of different initial condition on the soil moisture of the lower soil.
In one of the simulations the soil is initially almost completely saturated. In another simulation the soil is completely dry and the third simulation starts with initial conditions in between the two extremes.

In the beginning the effect of different initial condition can be seen clearly. But after one year the three curves converge. The **memory** of the lower soil goes back for about one year.

For all the initial condition apart from groundwater, lakes and reservoirs the memory is about 12 month. 



.. figure:: _static/init_soilmoisture.jpg
    :width: 600px

Figure: Simulation of soil moisture in the lower soil with different initial conditions

For the groundwater zone a longer warm-up period is needed, because of the slow response of groundwater. Here a rather fast reacting groundwater storage is shown with the three curves coverge after two years.
We propose a warm-up of several decades. The longer the better.

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

In the settings file the option **save_initial** has to be set to **True**

The name of the initial netCDF4 file has to be put in **initsave**

and one or more dates have to be specified in StepInit

.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 154-158


	
Warm start
----------

CWatM can write internal variables to a netCDF file for choosen timesteps. These netCDF files can be used as the initial conditions for a suceeding simulation.

This is useful for establishing a steady-state after a long-term run and then using this steady-state for succeding simulations or for an every day run (forecasting mode)

.. warning:: If the parameters are changed after a run(especially the groundwater, lakes and reservoir parameters) the stored initial values do not represent the conditions of the storage variables. Stored initial conditions should **not** be used as initial values for a model run with another set of parameters. If you do this during calibration, you will not be able to reproduce the calibration results!




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

An advantage of **CWatM** is the full flexibility of the output variables.

- All parameters and variables can be used for output as maps or time series.
- Even if the model is run at daily timestep, output can be daily, monthly, annual, at the end of a run
- all variables maps are stored as netcdf and the meta data information can be added

Time depending and non depending output maps
--------------------------------------------
	
| Output maps will be produced as spatial maps, stack of spatial maps (over time) 
| Format: `netCDF <http://www.unidata.ucar.edu/software/netcdf/>`_

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

available prefixes are: 'daily', 'monthtot','monthavg', 'monthend','annualtot','annualavg','annualend','totaltot','totalavg'

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
   OUT_TSS_MonthTot = runoff
   OUT_TSS_AnnualAvg = Precipitation
   OUT_TSS_AnnualTot = runoff

  
   
.. note:: For each variable the meta data information can be defined in :ref:`rst_metadata`

.. note:: For information how to adjust the output in the settings file see :ref:`rst_outputone`

Time series as point infomation or catchment sum or average
-----------------------------------------------------------

As standard time series can include values of the specific cell as defined in the settings file as *Gauges*
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
| grep -d recurse 'self.var.' \*.py 
| Every self.var.variable can be used as output variable
| For a description of the variable please take a look at the python module itself.
| .
| As output variable please use without self.var.

We started a list of possible output variables. Please note that this list is under construction. We still need to fill in all descriptions and all units.
You find this list at :ref:`rst_variables`