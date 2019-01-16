######################################
Increasing resolution (in development)
######################################

Data handling
=============

Artificially increasing resolution
----------------------------------

Currently, input data must all be of the same resolution. If the model is to be run at 1km resolution, then all the data must be available at 1km resolution.
One can artificially increase the resolution by appropriately dividing the cells to match the desired resolution, if data of a higher resolution is not available.
The value of these smaller cells depends on the context, for example, the value could match that of the parent cell, or be an appropriate fraction of the parent cell.

The program subset_shrink increases the resolution from 5 minutes to 1 kilometer, and extracts a subset of the map based on latitudinal and longitudinal limits.

The subset_shrink package contains:
1. the executable program,
2. the associated settings file to list the data files to be handled, and the extraction limits,
3. the python script for the program and
4. a README file.

**Download program folder**

:download:`subset_shrink<_downloads/subset_shrink.zip>`

