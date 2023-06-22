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
(Reading the full global maps takes only 1/3 longer than reading a part of the global maps)

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

For the Rhine basin reading input maps 79% is by far the most time consuming process, followed by routing (kinematic wave) 10% and the soil processes (8%).


Updates
=======

.. note::
    | Update history taken from github log
    | git log ---pretty=format:"%ad - %an : %s" ---date=short ---graph > github.log 

**Most recent updates on top**

.. literalinclude:: _static/gitlog.txt

