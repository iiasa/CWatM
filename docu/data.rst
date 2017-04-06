
#######################
Data
#######################

.. contents:: 
    :depth: 3

Data requirements
=================

Data format
=================

* netCDF
* Geotiff
* PCRaster maps

Data storage structure
======================


.. code-block:: rest
   
   project
   │-  README.txt
   │
   └───areamaps
   │   │-  globalarea,lobith, ...
   │
   └───landcover
   │   └───forest
   │   │   │-  CropCoefficientForest_10days
   │   │   │-  interceptcapForest10days
   │   │   │-  maxRootdepth, maxSoilDepthFrac, minSoilDepthFrac
   │   │   │-  rootFraction1, rootFraction2
   │   │
   │   └───grassland (same var as forest)
   │   │
   │   └───irrNonPaddy (same var as forest)
   │   │
   │   └───irrPaddy (same var as forest)
   │
   └───landsurface   
   │   │- fractionlandcover, global_clone
   │   │ 
   │   └───albedo
   │   │   │- albedo
   │   │ 
   │   └───topo
   │   │   │- dz_Rel_hydro1k, orographyBeta, tanslope
   │   │
   │   └───soil
   │   │   │- airEntry1,airEntry2,KSat1,KSat2,poreSizeBeta1, poreSizeBeta2
   │   │   │- resVolWC1, resVolWC2, satVolWC1, satVolWC2
   │   │   │- StorageDepth1, StorageDepth2, soilWaterStorageCap1, soilWaterStorageCap2
   │   │   │- percolationImp 
   │   │ 
   │   └───waterDemand
   │   │   │- domesticWaterDemand, industryWaterDemand3, irrigationArea, efficiency.nc
   │
   └───groundwater   
   │   │- kSatAquifer, recessionCoeff, specificYield
   │
   └───routing   
       │- ldd, catchment, cellarea
	   │
       └───kinematic
       │   │- chanbnkf, chanbw, changrad, chanleng, chanman
       │
	   └───lakereservoirs
           │- lakeResArea, lakeResDis,lakeResID, lakeResType, lakeResVolRes, lakeResYear



Static data
===============

Area maps
---------

* mask map or coordinates to model only regions or catchments
* maps or coordinates for station to print time series

Landcover
---------

Landsurface
-----------

Albedo
******

Topographie data
****************

Soil and soil hydraulic properties
**********************************

Water demand
************

Groundwater
-----------

Routing
-------

Kinematic wave
**************

Lakes and Reservoirs
********************


Temporal data for each year
===========================

Crop coefficient
----------------

Continous temporal data
=======================

Meteorological data
-------------------

* Precipitation
* Temperature
* Potential evaporation

Meteorological data for calculation pot. evaporation
----------------------------------------------------

* max, min temperature
* humidity
* radiation
