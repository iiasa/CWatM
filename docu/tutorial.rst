
#######################
Tutorial
#######################

.. contents:: 
    :depth: 4

	
Requirements
============

Python version
--------------


Requirements are a 64 bit `Python 2.7.x version <https://www.python.org/downloads/release/python-2712/>`_

.. warning:: a 32 bit version is not able to handle the data requirements!

Libraries
---------

These external libraries are needed:

* `Numpy <http://www.numpy.org>`_
* `netCDF4 <https://pypi.python.org/pypi/netCDF4>`_
* `GDAL <http://www.gdal.org>`_

**Windows**

Three libraries can be installed with pip or
downloaded at `Unofficial Windows Binaries for Python Extension Packages <http://www.lfd.uci.edu/~gohlke/pythonlibs>`_


Test the model
==============

**Windows and Linux**

python <modelpath>/cwatm.py 


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

   ======================== CWATM FILE ERROR ===========================
   Cannot find option file: d:/work/CWATM/source/metaNetcdf.xml In  "metaNetcdfFile"
   searching: "d:/work/CWATM/source/metaNetcdf.xml"
   path: d:/work/CWATM/source does not exists	


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
    metaNetcdfFile = $(FILE_PATHS:PathRoot)/CWATM/source/metaNetcdf.xml

.. note:: Please change the pathes according to your file system


Running the model 2
===================

If you type now::

   python cwatm.py settings_rhine.ini -l

You should see::

   E:\CWATM_rhine\source>python cwatm.py settings_rhine30min.ini -l
   CWATM - Community Water Model  Version: 0.991  Date:  16/09/2017
   International Institute of Applied Systems Analysis (IIASA)
   Running under platform:  Windows
   -----------------------------------------------------------
   CWATM Simulation Information and Setting
   The simulation output as specified in the settings file: settings_rhine30min.ini
   can be found in E:/CWATM_rhine/output
   Step         Date   Discharge
   1      01/01/1961        4.20
   2      02/01/1961        4.23
   ...


If you do't see this. Something went wrong and you mifght see this instead::

   E:\CWATM_rhine\source>python cwatm.py settings_rhine30min.ini -l
   CWATM - Community Water Model  Version: 0.991  Date:  16/09/2017
   International Institute of Applied Systems Analysis (IIASA)
   Running under platform:  Windows
   -----------------------------------------------------------
   ERROR 4: `E:/CWATM_rhine/cwatm_input/routing/ldd.map' does not exist in the file system,
   and is not recognised as a supported dataset name.
   management_modules.messages.CWATMFileError:
   ======================== CWATM FILE ERROR ===========================
   In  "Ldd"
   searching: "E:/CWATM_rhine/cwatm_input/routing/ldd.map"
   path: E:/CWATM_rhine/cwatm_input/routing does not exists

| The model tries to help you on finding the error.
| In this case it is looking for the river network map ldd.map or ldd.nc or ldd.tif
| but it cannot find the file and not even the path to the file.

Here you might change::

   [FILE_PATHS]
   PathRoot = E:/CWATM_rhine
   PathMaps = $(PathRoot)/cwatm_input

or::

   [TOPOP]
   # local drain direction map (1-9)
   Ldd = $(FILE_PATHS:PathMaps)/routing/ldd.map

But many other error can occure too! Have fun.



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



