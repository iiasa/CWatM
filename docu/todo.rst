#####################
TODO
#####################

Structural improvements
=======================

.. todo:: This has to be done. Importance: 1 to be changed first .. 3 to be changed later 

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
==================


.. csv-table:: 
   :header: "TODO", "Description","Importance","DONE"
   :widths: 40, 50, 40, 20 
   
   "Frost","include frost routine (no soil movement during strong frost)","1","."
   "Snow","include more than 3 vertical layers (make it flexible)","2","X"
   "Runoff concentration","include a 1st routing to the edge of a grid cell","1","."
   "Include water & sealed land cover","include 2 more land cover types (water covered area, sealed area)","1","."
   "Preferential flow","include preferential flow to soil layers","1", "X"
   "soil depend on land cover","include hydropedo transfer function landcover -> soil","2","."
   "Calculate Evaporation on PM","include Penman Monteith ET routine","1","X"
   "Reduce reading of time series maps","e.g. interception maps only 1 per month","2","X"
   "Kinematic wave","Add another way of routing","2","."
   "Improve lakes& reservoirs","Add another way of including lakes/reservoirs","2","."
   "Inflow points","add points where water can be added/substracted","1","."
   "Include Environmental flow","use environmental flow concept on the fly not only post-processing","2","."
   "Water allocation","include water demand <-> water supply functionality","2-3","."
   "Include EPIC approach","to be in line with ESM include the EPIC approach","3","."