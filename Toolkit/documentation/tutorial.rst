
#######################
Tutorial
#######################

.. contents:: 
    :depth: 4

	
Requirements
============

Requirements
------------

Python version
**************

NEW from 2019 on:
Requirements are a 64 bit `Python 3.7.x version <https://www.python.org/downloads/release/python-372/>`_

.. warning:: a 32 bit version is not able to handle the data requirements!

.. warning:: From 2019 on we are changing to Python37. We do not provide further support for Python 2.7

.. warning:: CWatM is tested for Python 3.7, 3.8 and will for sure not work with Python versions lower than 3.6. We recommend using Python 3.7, 3.8

Libraries
*********

These external libraries are needed:

* `Numpy <http://www.numpy.org>`_
* `Scipy <https://www.scipy.org>`_
* `netCDF4 <https://pypi.python.org/pypi/netCDF4>`_
* `GDAL <http://www.gdal.org>`_
* `Flopy <https://www.usgs.gov/software/flopy-python-package-creating-running-and-post-processing-modflow-based-models>`_

.. warning::

    Installing GDAL via pip causes sometimes problems. We recommend downloading the library from `Unofficial Windows Binaries for Python Extension Packages <http://www.lfd.uci.edu/~gohlke/pythonlibs>`_ as GDAL-3.0.4-cp37-cp37m-win_amd64.whl (or a later version depending on your Python version) and installing them as: 
	
	pip install C:/Users/XXXXX/Downloads/GDAL-3.0.4-cp37-cp37m-win_amd64.whl


**Windows**

The five libraries can be installed with pip or
downloaded at `Unofficial Windows Binaries for Python Extension Packages <http://www.lfd.uci.edu/~gohlke/pythonlibs>`_


Windows executeable Python version
**********************************

| The A cwatmexe.zip with all Python libraries and a test case (River Rhine)) is stored on:
| `Source code on Github repository of CWatM <https://github.com/iiasa/CWatM>`_
| `Executable cwatmexe.zip on Github repository of CWatM <https://github.com/iiasa/CWatM/tree/version1.05/tutorial/CWATM_model>`_


Test the executable model version
=================================

**only Windows**

If you familiar with Python just go to the next chapter.

.. code-block:: rest
   
   cwatm
   │-- README.md
   │
   └-- cwatmexe
   │   └- lib
   │   └---cwatm.exe
   │   └---metaNetcdf.xml
   │   └--- libraries etc.
   │
   └--rhine_basin
   │   └---climate_rhine
   │   └---cwatm_input_rhine
   │   └---init
   │   └---output
   │   └---run_python_rhine30.bat
   │   └---settings_rhine30.ini
   │   
   └-- run_test1.bat
   └-- run_test2_rhine30min.bat
   └-- settings_rhine_test.ini
   └-- tutorial.html


| Either start cwatm.exe in a DOS box (cmd windows command), or use a batch file e.g. run_test1.bat

Test 1
------

In the root directory cwatm

Please try::

  run run_test1.bat or type .\cwatmexe\cwatm.exe

The output should be like See: :ref:`rst_output1` 


Test 2
------

Please try::

  run run_test2_rhine30min.bat or type .\cwatmexe\cwatm.exe settings_rhine30_test.ini -l

The output should be like See: :ref:`rst_output2` 

.. _rst_output1:

Test the Python model version
=============================

**Windows and Linux** (and maybe Mac, but not tested)

Please try::


   python <modelpath>/run_cwatm.py  (for the Python3.7 version)
   or:
   <modelpath>/cwatm  (for the .exe version)

The output should be::

   Running under platform:  Windows  **(or Linux etc)** 
   CWatM - Community Water Model
   Authors: ...
   Version: ...
   Date: ...
   Arguments list:
   settings.ini     settings file
   -q --quiet       output progression given as .
   -v --veryquiet   no output progression is given
   -l --loud        output progression given as time st
   -c --check       input maps and stack maps are check
   -h --noheader    .tss file have no header and start
   -t --printtime   the computation time for hydrologic
   -w --warranty    copyright and warranty information   
	
.. warning:: If python is not set in the environment path, the full path of python has to be used

Error because you did not run it with Python
--------------------------------------------

if the model is causing an error with look like this::

   File "run_cwatm.py", line 116
   print("%-6s %10s %11s\n" %("Step","Date","Discharge"), end=' ')
   SyntaxError: invalid syntax

You run the model without the python command in front. Please use: python cwatm.py
(You may have to adjust the path to your python version and to cwatm.py).


Error because python is not added to the PATH
---------------------------------------------

If executing python return an error like this

   ‘python’ is not recognized as an internal or external command

You need either need to add Python to the PATH Environmental Variable or you need to start Python with full path.

   c:/path_to_python/python


Error because the path has white spaces included
------------------------------------------------

It is also possible to use paths with white spaces or dots. An easy way to avoid this is using relative paths, but is is also possible with absolute paths::

    "C:/Python 37/python" "C:/CWatM Hydrologic.modeling/CWatM/run_cwatm.py" "C:/CWatM Hydrologic.modeling/settings .rhine30min.ini" -l
    
    But in the settingsfile do not use apostrophe:
    PathRoot = C:/CWatM Hydrologic.modeling
   


Error because the python libraries are installed incorrectly
------------------------------------------------------------

If the model is causing an error at this stage, please check the python libraries::

    python
    import numpy
    import scipy.ndimage
    import gdal
    import netCDF4

Running the model 1
===================


.. warning:: The model needs a settings file as an argument. See: :ref:`rst_settingdoc` 

python <modelpath>/cwatm.py settingsfile flags

example::

   python cwatm.py settings_rhine.ini -l
	
The flag -l show the output on screen as date and discharge 

At this point you should receive this eror message::

   ======================== CWatM FILE ERROR ===========================
   Cannot find option file: d:/work/CWatM/source/metaNetcdf.xml In  "metaNetcdfFile"
   searching: "d:/work/CWatM/source/metaNetcdf.xml"
   path: d:/work/CWatM/source does not exists	


Downloading and installing the spatial dataset 
==============================================

The spatial dataset contains:

* static data ie. data that does not change over time (a model assumption) e.g. soil data
* time dependend (inter annual) data that change periodical during a year e.g. crop coefficient of vegetation
* time dependend (intra annual) data that change by month or year e.g. fraction of landcover

These data are stored as global dataset:

* cwat_input.zip  for the 30' global version
* cwat_input5min.zip  for the 5' global version


As climate data different forcings can be used e.g:

* PGMFD v.2 (Princeton), GSWP3, etc.
* precipitation from e.g. MSWEP http://www.gloh2o.org/
* WATCH+WFDEI  https://www.isimip.org/gettingstarted/details/5/

and as projection e.g.:

* ISI-MIP dataset https://www.isimip.org/gettingstarted/#input-data-bias-correction


| For the tutorial we cut out Rhine basin and included the WATCH+WFDEI precipitation, average temperature and the calculated potential evaporation .
| A 30' and a 5' version can be found on FTP in rhine/climate

| Reference:
| Weedon, G.P., S.S. Gomes, P.P. Viterbo, W.J. Shuttleworth, E.E. Blyth, H.H. Österle, J.C. Adam, N.N. Bellouin, O.O. Boucher, and M.M. Best, 2011: Creation of the WATCH Forcing Data and Its Use to Assess Global and Regional Reference Crop Evaporation over Land during the Twentieth Century. J. Hydrometeor., 12, 823–848, doi: 10.1175/2011JHM1369.1
| Weedon, G. P., G. Balsamo, N. Bellouin, S. Gomes, M. J. Best, and P. Viterbo (2014), The WFDEI meteorological forcing data set: WATCH Forcing Data methodology applied to ERA-Interim reanalysis data, Water Resour. Res., 50, 7505–7514, doi:10.1002/2014WR015638.


.. note:: 
   
    | Please copy and unpack the spatial dataset (either 30' or 5')in a folder
    | Please copy the the climate dataset 30min_meteo_rhine.zip or 5min_meteo_rhine.zip in a seperate folder
    | Please create a folder called output

.. note:: 
   
    | For testing purpose there is a file rhine_basin.zip on GitHub
    | it has all the necessary data to run the River Rhine on 30 arcmin from 1990-2010


Changing the Settings file
==========================
	
to run the model the pathes to data have to be set correctly:
The information of pathes are stored in the settings file around line 80-100

[FILE_PATHS]::

    PathRoot = E:/      
    PathOut = $(PathRoot)/output
    PathMaps = E:/cwatm_input
    PathMeteo = E:/climate
    #--------------------------------------
    [NETCDF_ATTRIBUTES]
    institution = IIASA
    title = Global Water Model - WATCH WDFEI
    metaNetcdfFile = $(FILE_PATHS:PathRoot)/CWatM/source/metaNetcdf.xml

.. note:: Please change the pathes according to your file system

.. _rst_output2:


Error and exception handling
============================

We try to make our program behave properly when encountering unexpected conditions. Therefore we caption a number of possible wrong inputs.

If you get an output with an error number please look at :ref:`rst_error`


Running the model 2
===================

If you type now::

   python cwatm.py settings_rhine.ini -l



You should see::

   E:\CWatM_rhine\source>python cwatm.py settings_rhine30min.ini -l
   CWatM - Community Water Model  Version: 0.991  Date:  16/09/2017
   International Institute of Applied Systems Analysis (IIASA)
   Running under platform:  Windows
   -----------------------------------------------------------
   CWatM Simulation Information and Setting
   The simulation output as specified in the settings file: settings_rhine30min.ini
   can be found in E:/CWatM_rhine/output
   Step         Date   Discharge
   1      01/01/1961        4.20
   2      02/01/1961        4.23
   ...


If you don't see this. Something went wrong and you might see this instead::

   E:\CWatM_rhine\source>python cwatm.py settings_rhine30min.ini -l
   CWatM - Community Water Model  Version: 0.991  Date:  16/09/2017
   International Institute of Applied Systems Analysis (IIASA)
   Running under platform:  Windows
   -----------------------------------------------------------
   ERROR 4: `E:/CWatM_rhine/cwatm_input/routing/ldd.map' does not exist in the file system,
   and is not recognised as a supported dataset name.
   management_modules.messages.CWatMFileError:
   ======================== CWatM FILE ERROR ===========================
   In  "Ldd"
   searching: "E:/CWatM_rhine/cwatm_input/routing/ldd.map"
   path: E:/CWatM_rhine/cwatm_input/routing does not exists

| The model tries to help you on finding the error.
| In this case it is looking for the river network map ldd.map or ldd.nc or ldd.tif
| but it cannot find the file and not even the path to the file.

Here you might change::

   [FILE_PATHS]
   PathRoot = E:/CWatM_rhine
   PathMaps = $(PathRoot)/cwatm_input

or::

   [TOPOP]
   # local drain direction map (1-9)
   Ldd = $(FILE_PATHS:PathMaps)/routing/ldd.map

But many other error can occure too! Have fun.

P.s. some error we captured and we give a hint. Please look at :ref:`rst_error`


Changing parameters of the model
================================

.. note:: An overview of possibilities is given in  see :ref:`rst_settingdoc`


Changing the Output
===================

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
   OUT_TSS_AnnualAvg = Precipitation

  
   
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


A list of all variables
-----------------------

We started a list of possible output variables. Please note that this list is under construction. We still need to fill in all descriptions and all units.
You find this list at :ref:`rst_variables`


