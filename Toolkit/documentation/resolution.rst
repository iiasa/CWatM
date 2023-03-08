#####################
Increasing resolution
#####################

.. note:: In development

Data handling
=============


River dimensions
================

This section details how to derive the necessary river dimensions, including:
1. Manning coefficient, 2. Width, 3. Length, 4. Gradient, and 5. Depth/Height.

**Necessary inputs:**

* Ldd: Local drainage directions: This was derived from the drainage direction map (as_dir_30s) available from hydrosheds.com. The map from hydrosheds.com uses the ESRI direction conventions (for example, the direction top-right is 32) while we require the keypad convention (top-right is 9) for pcraster. The included *reclass_arc_ldd* file can be used for this "reclassification" in ArcGIS.

* cell area: The file *cellarea_30sec_global.tif* is included

* dem: Digital elevation model: downloaded from hydrosheds.com

We demonstrate this at 30 seconds resolution for the Upper Bhima basin in India. The input data is all of 30s resolution and type .map unless otherwise indicated.

**Manning coefficient and Width**

- Input: ldd_UB, cellarea_UB, dem_UB
- Output: chanmann_UB, chanwidth_UB

Run >pcrcalc -f mann_width.mod

**Length**

- Input: ldd_UB
- Output: chanleng_UB

The chanleng file denotes the length of the river in the cell, in metres. Simply, each cell with a river is attributed either a value of 1000 or 1414.

Reclassify the ldd file in the following way:
1,3,7,9 becomes 1414;
2,4,6,8 becomes 1000.


**Gradient**

- Pre-processing inputs: dem15s
- Pre-processing outputs: dem_agg_min/med_UB

Aggregate the 15s dem to 30s in two ways, with both the minimum and the median values.

- Input: ldd_UB, chanleng_UB, dem_agg_min/med_UB
- Output: changrad_UB

Run >pcrcalc -f grad.mod

**Depth/Height**

- Input: ldd_UB, chanleng_UB, changrad_UB
- Output: chanleng_UB

Run >pcrcalc -f height.mod



Artificially increasing resolution
==================================

Currently, input data must all be of the same resolution. If the model is to be run at 1km resolution, then all the data must be available at 1km resolution.
One can artificially increase the resolution by appropriately dividing the cells to match the desired resolution, if data of a higher resolution is not available.
The value of these smaller cells depends on the context, for example, the value could match that of the parent cell, or be an appropriate fraction of the parent cell.

The program subset_shrink increases the resolution from 5 minutes to 1 kilometer, and extracts a subset of the map based on latitudinal and longitudinal limits.

The subset_shrink package contains:
1. the executable program,
2. the associated settings file to list the data files to be handled, and the extraction limits,
3. the python script for the program and
4. a README file.


