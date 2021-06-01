The Main code should result in two folders containing input maps required to run CWatM-ModFlow.

The first folder will contain the river network at a finer resolution than the final resolution.
The second folder will contain several maps at the final resolution:
  1) ModFlow mask at the final resolution (tif)
  2) ModFlow DEM at the final resolution (tif)
  3) ModFlow map of the percentage of river in each cell (tif)
  4) A folder called indices containing CWatM cells indexes corresponding to each ModFlow cells and the area in common.
  5) They allow to convert exactly flows from CWatM to ModFlow and from ModFlow to CWatM even if resolution and coordinates system are different

User needs a topographic map at fine resolution in tif format, and the of the area simulated with CWatM.

QGis is required for of the steps.

Authors: L. Guillaumot, J. de Bruijn, M. Smilovic (IIASA, Water Security Group)

Updated on March 19th 2021
