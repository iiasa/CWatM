#####################
The Model Itself
#####################


.. contents:: 
    :depth: 3

Performance
===========

Computational run time (on a linux single node - 2400 MHz with Intel Xeon CPU E5- 2699A v4):

Daily timestep on 0.5 deg 

**Global:** 100 years in appr. 12h = 7.2min per year

.. csv-table:: 
   :header: "","Process", "sum % runtime"
   :widths: 5, 20, 10

   "1","Read Meteo Data","6.2"
   "2","Et pot","7.6"
   "3","Snow","8.8"
   "4","Soil","59.4"
   "5","Groundwater","59.5"
   "6","Runoff conc","70.1"
   "7","Lakes","70.4"
   "8","Routing","95.5"
   "9","Output","100"

For the global setting, soil processes with 50% computing time is the most time consuming part, followed by routing with 25% and runoff concentration with 10%.


**Rhine:**  640 years in appr. 4.5h = 0.4min per year 

.. csv-table:: 
   :header: "","Process", "sum % runtime"
   :widths: 5, 20, 10

   "1","Read Meteo Data","79.4"
   "2","Et pot","80.5"
   "3","Snow","80.9"
   "4","Soil","88.8"
   "5","Groundwater","88.9"
   "6","Runoff conc","89.6"
   "7","Lakes","89.8"
   "8","Routing","99.6"
   "9","Output","100"

For the Rhine basin reading input maps 79% is by far the most time consuming process, followed by routing (kinematic wave) 10% and the soil processes (8%)

Updates
=======

**Most recent updates on top**

4/01/2019

* Change to Python 3.7
* added a lot of changes in the mean time please see change track on github


25/09/2017

* bugfix on snow modul 
* added additional evaporation from open water (transition loss in channels)

20/08/2017
----------

* improved water demand modul
* added small lakes and reservoirs

24/06/2017
----------

* added netcdf read module - now the netcdf does not need to be merged before - abilitity to read in a stack of netcdf files
* added inflow to a catchment - inflow is given as text file


25/05/2017
----------

* added new soil scheme based on Arno scheme 

27/03/2017
----------

* included license term GNU V3 in cwatm.py and globals.py

26/03/2017
----------

* added documentation for autodocu for a lot of subroutines












Bug and bugfix report
=====================

This is the only and first source code without bugs
Really!

Hey really!!

Ok some exceptions:
-------------------





TODO
====

Structural improvements
-----------------------

.. note::
    This has to be done. Importance: 1 to be changed first .. 3 to be changed later 

.. csv-table:: 
   :header: "Topic","TODO", "Description","Importance","DONE"
   :widths: 30, 40, 50, 30, 20 
   
   "Documentation","Documentation","start writing a user manual","1","."
   "Documentation","Source code documentation","Improve comment-lines in the code and include them in the autodocu sphinx","1","."
   "Documentation","Include log file/change log","document the changes in the code/settings","2","."
   "Output","GAMS output","output/input in GAMS (gdx -files)","2","."
   "Output","Extent output possibilities","Output as e.g. yearly areatotal, catchment total as maps, as time series","1", "."
   "Handling","Improve error handling","more messages for users if something goes wrong","1","."
   "Handling","Checks maps","include a pre-run, where input data are checked for plausibility","2","."
   "Handling","Load multiple netcd files","read meteo input netcdf from split files","2","."

   
Model improvements
------------------


.. csv-table:: 
   :header: "TODO", "Description","Importance","DONE"
   :widths: 40, 50, 40, 20 
   
   "Frost","include frost routine (no soil movement during strong frost)","1","X"
   "Snow","include more than 3 vertical layers (make it flexible)","2","X"
   "Runoff concentration","include a 1st routing to the edge of a grid cell","1","X"
   "Include water & sealed land cover","include 2 more land cover types (water covered area, sealed area)","1","X"
   "Preferential flow","include preferential flow to soil layers","1", "X"
   "Calculate Evaporation on PM","include Penman Monteith ET routine","1","X"
   "Reduce reading of time series maps","e.g. interception maps only 1 per month","2","X"
   "Kinematic wave","Add C++ kinematic wave procedure","2","X"
   "soil depend on land cover","include hydropedo transfer function landcover -> soil","2","."
   "Improve lakes& reservoirs","Add another way of including lakes/reservoirs","2","X"
   "Inflow points","add points where water can be added/substracted","1","X"
   "Include Environmental flow","use environmental flow concept on the fly not only post-processing","2","X"
   "Water allocation","include water demand <-> water supply functionality","2-3","."
   "Include EPIC approach","to be in line with ESM include the EPIC approach","3","."