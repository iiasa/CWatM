The program subset_shrink increases the resolution of a set of netCDF files from any resolution to 1 kilometer, 
and extracts a subset of these maps based on latitudinal and longitudinal limits.

The program will create a directory of the same name of your Basin code (see below), and move all of the created data inside.

You can either run subset_shrink.py (all versions of Python should work) or double-click the batch file.

The settings file is of the form:
L1 Basin code = xxx 			#name of whatever length without spaces 
L2					#blank line
L3 lateral bounds 	= ##.# ##.#	#minimum and maxiumum lateral bounds
L4 longitudinal bounds 	= ##.# ##.#	#minimum and maximum longitudinal bounds
L5 					#blankline
L6 filename1 				#full or appropriate pathname
...
LN filenameN 				#full or appropriate path	
