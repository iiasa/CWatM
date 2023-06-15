
.. _rst_demo:

#####################
Demo of the model
#####################

Resolution
==========
| CWatM can be run globally at 0.5° or separately for any basin or any clipping of a global map. 
| Depending on the data provided the model can also run for any other resolutions (e.g. 5 arcmin). 
| Timestep is daily, output of maps, time series can be daily, monthly, yearly 


Here some outputs of the global run on 0.5° are shown:

   
Demo 1 - NetCDF videos   
======================

Global discharge 
******************

One year run example: 1/1/1991- 31/12/1992

.. raw:: html 

   <video loop controls src="_static/CWAT_global_1year.mp4" width="700"></video>


Global potential evaporation [mm/day] 
*************************************

One year run example

.. raw:: html 

   <video autoplay loop controls src="_static/etr_glob_smaller.mp4" width="700"> </video>
   
   
Global soil moisture [mm/mm]
****************************

One year run example

.. raw:: html 

   <video loop controls src="_static/sm_glob_smaller.mp4" width="700"></video>


Demo 2 - NcView output   
======================   

| Global discharge as world map
| Output from NcView

.. figure:: _static/demo1_ncview.jpg
    :width: 700px

Demo 3 - NcView timeserie   
=========================	

| Discharge as timeseries
| Output from NcView

.. figure:: _static/demo2_ncview.jpg
    :width: 500px


Demo 4 - Monthly timeserie   
==========================	

Discharge as monthly timeseries

.. figure:: _static/demo3_timeserie.jpg
    :width: 500px

Demo 5 - PCRaster Aguila output   
===============================	

Discharge as timeseries
Output from `PCRaster Aquila <http://pcraster.geo.uu.nl/projects/developments/aguila/>`_

.. figure:: _static/demo4_ts_aguila.jpg
    :width: 500px
