
###############
Tips and Tricks
###############

.. contents:: 
    :depth: 4

Here we collect some tricks which may mentioned on other pages of the documentation, but are overseen and might be helpful.

Settings file
=============

Notepad++ for settingsfile
---------------------------

Notepad++ https://notepad-plus-plus.org is a very good editor for changing the settingsfile.

With **Alt-0** and **Alt-Shift-0** you can fold/unfold a settingsfile 


Generate a basin and an upstream map
------------------------------------

The modeling area can be defined by:

* a mask map e.g.: $(FILE_PATHS:PathRoot)/source/rhine30min.tif
* coordinates e.g.: 14 12 0.5 5.0 52.0
* lowest point of a catchment e.g.: 6.25 51.75

If you use the *lowest point of a catchment* (aka outlet), you can generate .tif
of the basin and the upstream area

.. note:: 

    | If you start with a basin defined by the outlet of a basin e.g. 6.25 51.75
    | You can generate a new mask map for the following runs by adding in:
    | [OPTIONS]
    | **savebasinmap = True** 

    | a basin.tif and an upstream area map are generated in the output folder, which you can copy and use next time as:

    | **MaskMap = your_directory/basin.tif**
	
Placeholder in settingsfile
---------------------------

You can use placeholder in the settingsfile. For example to put in the filepath only once:

.. note::
   
    | [FILE_PATHS]
    | PathRoot = C:/cwatm/basin
	| **and somewhere else**
	| [TOPOP]
    | Ldd = $(FILE_PATHS:PathRoot)/input/routing/ldd.nc
	
You can also define a placeholder:

.. note::

    | [SIM]
    |  gcm = CanESM5
	| You can use this here to replace the scenario placeholder
	| PathOut = $(PathRoot)/out/$(SIM:gcm)
	

	



Output
======

Output as timeseries of area averages or sums
---------------------------------------------

For some variables it is more useful to get the sum (or the average) of the upstream area than the value for the cell.

| With *AreaSum* or *AreaAvg* you can produce such .csv files.

   OUT_TSS_AreaSum_Daily = Precipitation    # daily sum of precipitation for the upstream catchment
   OUT_TSS_AreaAvg_MonthAvg = runoff        # monthly average sum of runoff for the upstream catchment
   
.. warning:: This is only working for timeseries output not for netcdfs


Output of indexed variables
---------------------------

CWatM uses 6 land cover classes:

0: Forest
1: Grassland (or Others)
2: Irrigated area
3: Paddy irrigated (Rice)
4: Water
5: Sealed area

| You can output a variable for a specific land cover class by adding the the number e.g [0] for forest
| It works for timeseries (TSS) and for netcdfs (MAP)

Examples:

- actualET[1] - actual evapotranspiration from grassland [m/day]
- directRunoff[4] - surface runoff from sealed area [m/day]

.. note:: 
      The output of directRunoff[4] gives you the value as if there is 100% sealed area in this cell
	  
	  To get the real amount, you have to multiply it with the fraction of land cover which can change every year
	  
	  You can output this with *OUT_MAP_AnnualEnd = fracVegCover[No]*   (with No = [0-5])