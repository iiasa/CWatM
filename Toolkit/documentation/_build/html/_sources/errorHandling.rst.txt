.. _rst_error:

#######################
Error handling
#######################

We try to make our program behave properly when encountering unexpected conditions. The problematic situations that a program can encounter fall into two categories.

- Programmer mistakes: If someone forgets to pass a required argument to a function 
- Genuine problems: If the program asks the user to enter a name and it gets back an empty string, that is something the programmer can not prevent.

This part deals with genuine problems. Please look for your error number



.. csv-table::
  :header: "Error No", "Description", "Settingsfile", "Measure", "Module", "Procedure"

    "`E101`_", "Gauges in settingsfile is not a coordinate e.g. Gauges = bad bad", "Gauges", "Put in pairs of coordinates or a map with coordinates", "datahandling", "valuecell"
    "`E102`_", "One of the gauges is outside the map extend of the mask map", "Gauges", "Make sure that all gauges are inside the mask map area", "datahandling", "valuecell"
    "`E103`_", "Maskmap is not a valid mask map nor valid coordinates nor valid point e.g. MaskMap = 1 2 3 4 5 6 ", "MaskMap", "Put in a pair of coordinates, a defined rectangle (5 numbers) or a filename", "datahandling", "loadsetclone"
    "`E104`_", "MaskMap point does not have a valid value in the river network (LDD)", "MaskMap", "You put in a coordinate as MaskMap\, but at this coordinate there is no valid river network value", "datahandling", "maskfrompoint"
    "`E105`_", "The map you are loading has a different shape (different cols\,rows) than the other maps", "Any map", "Make sure your map has the same resolution\, rows\, cols than the river network map", "datahandling", "compressArray"
    "`E106`_", "The map you are loading has missing cell values (NaNs) where the river network and the mask map has valid values", "Any map", "Check the map and include cell values where the river network map has valid (non NaNs) values", "datahandling", "compressArray"
    "`E107`_", "The netCDF map has different attributes (resolution\, rows\,cols) than your standard map", "Any netCDF map", "Make sure your map has the same resolution\, rows\, cols as the river network map", "datahandling", "mapattrNetCDF"
    "`E108`_", "The tif map has different attributes (resolution\, rows\,cols) than your standard map", "Any tif map", "Make sure your map has the same resolution\, rows\, cols as the river network map", "datahandling", "mapattrTiff"
    "`E109`_", "The meteo map (e.g. temperature\, precipitation\, evaporation..) has different attributes (resolution\, rows\,cols) than your standard map", "Meteo netCDF map", "Make sure your meteo input maps have the same resolution\, rows\, cols as the river network map. If it is the ET maps\, it might be from another run with different mask. Please look at the option: calc_evaporation", "datahandling", "readmeteodata"
    "`E110`_", "The netcdf map with a time variable (e.g. waterdemand\, land cover\, lakes..) has different attributes (resolution\, rows\,cols) than your standard map", "All time depending netCDF maps appart from meteo maps", "Make sure your netCDF input maps have the same resolution\, rows\, cols as the river network map", "datahandling", "readnetcdf2"
    "`E111`_", "The netcdf maps without time is turned upside dowm", "Any netCDF map without time", "Make sure your map is in right order e.g. latitude coordinate are turned", "datahandling", "readnetcdfWithoutTime"
    "`E112`_", "The initial map (load_initial) stack is turned upside down", "Initload", "Make sure your initial map (in initial_load) is in right order e.g. latitude coordinate are turned", "datahandling", "readnetcdfInitial"
    "`E113`_", "The initial map stack (initial_load) has different attributes (resolution\, rows\,cols) than your standard map", "Initload", "Make sure your initial maps (in initial_load)has the same attributes. Maybe your initial maps are from a different run with a different mask?", "datahandling", "readnetcdfInitial"
    "`E114`_", "Problem reading initial maps", "Initload", "Initial maps has maybe not the same shape as the mask map. Maybe put load_initial = False", "datahandling", "readnetcdfInitial"
    "`E115`_", "Variable with a  True or False value can not be read", "Any flag (True or False)", "Make sure the variable has either: varname = False or varname = True. Ttrue or faalse is not working!", "datahandling", "returnBool"
    "`E116`_", "One of the variable names in [Option] is written wrong", "Any variable in [Option]", "A keyword in option is maybe written wrong e.g. CaaapillarRise instead CapillarRise", "datahandling", "checkOption"
    "`E117`_", "One of the variable names is written wrong", "Any variable after [Option]", "A keyword in option is maybe written wrong e.g. MaaaskMap instead MaskMap. Pay attention: in Linux words are case sensitive!", "datahandling", "cbinding"
    "`E118`_", "Timing in the section TIME-RELATED_CONSTANTS is wrong", "StepStart\, SpinUp\, StepEnd", "Please check the variables StepStart\, SpinUp\, StartEnd", "timestep", "ctbinding"
    "`E119`_", "`Either date in StepStart is not a date or in SpinUp or StepEnd it is neither a number or a date", "StepStart\, SpinUp\, StepEnd", "Please check the variables StepStart\, SpinUp\, StartEnd - A date is missing", "timestep", "Calendar"
    "`E120`_", "First date in StepInit is neither a number or a date", "StepInit", "Check StepInit in INITITIAL CONDITIONS. It is not a date or a number", "timestep", "Calendar"
    "`E121`_", "Second value in StepInit is not a number or date nor indicating a repetition of year(y)\, month(m) or day(d) e.g. 2y for every 2 years or 6m for every 6 month", "StepInit", "Check StepInit. The second part is neither a date or d\,m\,y", "timestep", "datetosaveInit"
    "`E122`_", "Third value in StepInit is not an integer after 'y' or 'm' or 'd'", "StepInit", "Check StepInit. The third part after d\,m\,y is not an integer", "timestep", "datetosaveInit"
    "`E123`_", "StepStart has to be a valid date", "StepStart", "Check StepStart. It has to be a date e.g.  01/01/2009", "timestep", "checkifDate"
    "`E124`_", "StepEnd is earlier than StepStart", "StepStart\, StepEnd", "Check StepStart and StepEnd. StepEnd has to be later than StepStart", "timestep", "checkifDate"
    "`E125`_", "Spin Date is smaller/bigger than the first/last time step date", "StepStart\, SpinUp\, StepEnd", "Check that SpinDate is in between StepStart and StepEnd", "timestep", "checkifDate"
    "`E127`_", "Coordinates are not pairs", "InflowPoints", "Check that location in InflowPoints comes in pairs", "inflow", "initial"
    "`E128`_", "OUT_MAP_Daily = discharge may be not defined in [OUTPUT]", "calc_ef_afterRun\, Out_MAP_Daily", "Make sure that you define Out_MAP_Daily = discharge. Is seems daily discharge is not stored", "`Environflow", "initial"
    "`E129`_", "Output points in Gauges are not pairs e.g. Gauges = 17.5 55.6 18.5", "Gauges", "Check that output-points in Gauges are of coordinate e.g. Gauges = 6.25 51.75", "output", "initial"
    "`E130`_", "Out_TSS or Out_MAP is not one of these: daily\, monthend\, monthtot\, monthavg\, annualend\, annualtot\, annualavg", "Out_TSS\, Out_MAP", "Please check that the wording after Out_TSS or Out_MAP is correct. Only a few keywords are valid e.g. Out_MAP_Daily\, Out_TSS_monthavg", "output", "initial"
    "`E131`_", "Second keyword after TSS or MAP is wrong", "Out_TSS\, Out_MAP", "Use TSS for point value\, AreaSum for sum of area\, AreaAvg for average of area e.g. OUT_TSS_AreaSum_Daily", "output", "initial"
    "`E132`_", "Variable is not defined in list of variables", "Out_TSS\, Out_MAP", "Please correct the writing of the variable name\, check also case sensitive e.g. Precipitation instead precipitation", "output", "dynamic"
    "`E201`_", "Cannot load the maskmap as a file e.g. MaskMap = notexisting.tif", "MaskMap", "Make sure the file you put in MaskMap is existing and is a map e.g. *.nc\, *.map\, *.tif", "datahandling", "loadsetclone"
    "`E202`_", "Your map is upside down", "Any map", "Make sure your map is in right order e.g. latitude coordinate are turned", "datahandling", "loadmap"
    "`E203`_", "Cannot find the map\, filename does not exists at this location", "Any map", "the datafile cannot be found\, the location is wrong or the file is missing", "datahandling", "loadmap"
    "`E204`_", "Trying to read the precipitation map metadata", "Precipitation map", "Make sure the precipitation netcdf are existing and correct", "datahandling", "metaNetCDF"
    "`E205`_", "Read error  while reading netcdf map", "any netcdf map", "Make sure netcdf map is existing and correct", "datahandling", "readCoordNetCDF"
    "`E206`_", "read error while reading meteo maps", "any meteo maps", "Make sure the meteo input maps are in the right location and chave correct attributes", "datahandling", "checkMeteo_Wordclim"
    "`E207`_", "read error while reading the wordclim map for downscaling meteo maps", "Wordlclim maps", "Make sure the wordclim maps are in the right location and chave correct attributes", "datahandling", "checkMeteo_Wordclim"
    "`E208`_", "Cannot find meteomaps", "any meteomap", "Make sure the meteo input maps are at the right location", "datahandling", "multinetdf"
    "`E209`_", "`Error loading meteomaps", "any meteomap", "Check if the filenames of the meteomaps are ok. Does the filename exist at this location", "datahandling", "multinetdf"
    "`E210`_", "Meteomap does not have this date", "any meteomap", "The netCDF file does not contain this date. Check your start and end date", "datahandling", "readmeteodata"
    "`E211`_", "`Error loading meteomaps", "any meteomap", "Check if the filenames of the meteomaps are ok. Does the filename exist at this location", "datahandling", "readmeteodata"
    "`E212`_", "`Error loading any other time depending map but not meteomaps", "any time dependending netCDF map", "Check if the filenames of the map is ok. Does the filename exist at this location", "datahandling", "readnetcdf2"
    "`E213`_", "`Error loading netCDF maps without time", "any non time depending netCDF map", "Check if the filenames of the map is ok. Does the filename exist at this location", "datahandling", "readnetcdfWithoutTime"
    "`E214`_", "`Error loading the initial map", "initial netCDF map", "Check if the loaction of the initial  map is o. Please check filename in initLoad", "datahandling", "readnetcdfInitial"
    "`E215`_", "Trying to read the precipitation map metadata", "Precipitation map", "Make sure the precipitation netcdf are existing and correct", "timestep", "checkifDate"
    "`E216`_", "Outflow/Inflow point file cannot be loaded", "InflowPoints", "Check if filename of InflowPoints exists", "inflow", "initial"
    "`E217`_", "Mistake reading inflow file\, name of inflow points are used twice", "In_Dir ", "Check inflow file header", "inflow", "initial"
    "`E218`_", "Mistake reading inflow file", "In_Dir ", "Check if filename of inflow file exists", "inflow", "initial"
    "`E219`_", "Mistake in discharge daily netcdf file", "Out_MAP_Daily = discharge", "Something is wrong with the daily discharge file. Check location and content", "`Environment", "initial"
    "`E220`_", "Output file path is wrong", "OUT_Dir\, PathOut", "Check OUT_Dir and PathOut. OUT_Dir can be used several times in the settings file.", "output", "appendinfo"
    "`E221`_", "`Error using file in Gauges", "Gauges", "Please check if file in Gauges exists and is correct", "output", "initial"
    "`E301`_", "Python version is not 64 bit", "-", "Make sure that you use a 64 bit version of Python", "global", "main"
    "`E302`_", "Settingsfile not found", "-", "Make sure the settings file exists and is at the right location", "configuration", "parse_configuration"
    "`E303`_", "An error occured while reading metaNetcdf.xml", "metaNetcdfFile", "Please check that metaNetcdf is a valid .xml file", "configuration", "read_metanetcdf"
    "`E304`_", "Cannot find alternative option file metaNetcdf.xml not found ", "metaNetcdfFile", "Please check in metaNetcdfFile that the file exists", "configuration", "read_metanetcdf"
    "`E305`_", "An error occured while reading alternative metaNetcdf.xml", "metaNetcdfFile", "Please check that metaNetcdf is a valid .xml file", "configuration", "read_metanetcdf"




E101
---------------------------------------------------------------------------
  :Description:  Gauges in settingsfile is not a coordinate e.g. Gauges = bad bad
  :Where:        Gauges
  :What to do:   Put in pairs of coordinates or a map with coordinates
  :Module:       datahandling, valuecell




E102
---------------------------------------------------------------------------
  :Description:  One of the gauges is outside the map extend of the mask map
  :Where:        Gauges
  :What to do:   Make sure that all gauges are inside the mask map area
  :Module:       datahandling, valuecell




E103
---------------------------------------------------------------------------
  :Description:  Maskmap is not a valid mask map nor valid coordinates nor valid point e.g. MaskMap = 1 2 3 4 5 6 
  :Where:        MaskMap
  :What to do:   Put in a pair of coordinates, a defined rectangle (5 numbers) or a filename
  :Module:       datahandling, loadsetclone




E104
---------------------------------------------------------------------------
  :Description:  MaskMap point does not have a valid value in the river network (LDD)
  :Where:        MaskMap
  :What to do:   You put in a coordinate as MaskMap, but at this coordinate there is no valid river network value
  :Module:       datahandling, maskfrompoint




E105
---------------------------------------------------------------------------
  :Description:  The map you are loading has a different shape (different cols,rows) than the other maps
  :Where:        Any map
  :What to do:   Make sure your map has the same resolution, rows, cols than the river network map
  :Module:       datahandling, compressArray




E106
---------------------------------------------------------------------------
  :Description:  The map you are loading has missing cell values (NaNs) where the river network and the mask map has valid values
  :Where:        Any map
  :What to do:   Check the map and include cell values where the river network map has valid (non NaNs) values
  :Module:       datahandling, compressArray




E107
---------------------------------------------------------------------------
  :Description:  The netCDF map has different attributes (resolution, rows,cols) than your standard map
  :Where:        Any netCDF map
  :What to do:   Make sure your map has the same resolution, rows, cols as the river network map
  :Module:       datahandling, mapattrNetCDF




E108
---------------------------------------------------------------------------
  :Description:  The tif map has different attributes (resolution, rows,cols) than your standard map
  :Where:        Any tif map
  :What to do:   Make sure your map has the same resolution, rows, cols as the river network map
  :Module:       datahandling, mapattrTiff




E109
---------------------------------------------------------------------------
  :Description:  The meteo map (e.g. temperature, precipitation, evaporation..) has different attributes (resolution, rows,cols) than your standard map
  :Where:        Meteo netCDF map
  :What to do:   Make sure your meteo input maps have the same resolution, rows, cols as the river network map. If it is the ET maps, it might be from another run with different mask. Please look at the option: calc_evaporation
  :Module:       datahandling, readmeteodata




E110
---------------------------------------------------------------------------
  :Description:  The netcdf map with a time variable (e.g. waterdemand, land cover, lakes..) has different attributes (resolution, rows,cols) than your standard map
  :Where:        All time depending netCDF maps appart from meteo maps
  :What to do:   Make sure your netCDF input maps have the same resolution, rows, cols as the river network map
  :Module:       datahandling, readnetcdf2




E111
---------------------------------------------------------------------------
  :Description:  The netcdf maps without time is turned upside dowm
  :Where:        Any netCDF map without time
  :What to do:   Make sure your map is in right order e.g. latitude coordinate are turned
  :Module:       datahandling, readnetcdfWithoutTime




E112
---------------------------------------------------------------------------
  :Description:  The initial map (load_initial) stack is turned upside down
  :Where:        Initload
  :What to do:   Make sure your initial map (in initial_load) is in right order e.g. latitude coordinate are turned
  :Module:       datahandling, readnetcdfInitial




E113
---------------------------------------------------------------------------
  :Description:  The initial map stack (initial_load) has different attributes (resolution, rows,cols) than your standard map
  :Where:        Initload
  :What to do:   Make sure your initial maps (in initial_load)has the same attributes. Maybe your initial maps are from a different run with a different mask?
  :Module:       datahandling, readnetcdfInitial




E114
---------------------------------------------------------------------------
  :Description:  Problem reading initial maps
  :Where:        Initload
  :What to do:   Initial maps has maybe not the same shape as the mask map. Maybe put load_initial = False
  :Module:       datahandling, readnetcdfInitial




E115
---------------------------------------------------------------------------
  :Description:  Variable with a  True or False value can not be read
  :Where:        Any flag (True or False)
  :What to do:   Make sure the variable has either: varname = False or varname = True. Ttrue or faalse is not working!
  :Module:       datahandling, returnBool




E116
---------------------------------------------------------------------------
  :Description:  One of the variable names in [Option] is written wrong
  :Where:        Any variable in [Option]
  :What to do:   A keyword in option is maybe written wrong e.g. CaaapillarRise instead CapillarRise
  :Module:       datahandling, checkOption




E117
---------------------------------------------------------------------------
  :Description:  One of the variable names is written wrong
  :Where:        Any variable after [Option]
  :What to do:   A keyword in option is maybe written wrong e.g. MaaaskMap instead MaskMap. Pay attention: in Linux words are case sensitive!
  :Module:       datahandling, cbinding




E118
---------------------------------------------------------------------------
  :Description:  Timing in the section TIME-RELATED_CONSTANTS is wrong
  :Where:        StepStart, SpinUp, StepEnd
  :What to do:   Please check the variables StepStart, SpinUp, StartEnd
  :Module:       timestep, ctbinding




E119
---------------------------------------------------------------------------
  :Description:  Either date in StepStart is not a date or in SpinUp or StepEnd it is neither a number or a date
  :Where:        StepStart, SpinUp, StepEnd
  :What to do:   Please check the variables StepStart, SpinUp, StartEnd - A date is missing
  :Module:       timestep, Calendar




E120
---------------------------------------------------------------------------
  :Description:  First date in StepInit is neither a number or a date
  :Where:        StepInit
  :What to do:   Check StepInit in INITITIAL CONDITIONS. It is not a date or a number
  :Module:       timestep, Calendar




E121
---------------------------------------------------------------------------
  :Description:  Second value in StepInit is not a number or date nor indicating a repetition of year(y), month(m) or day(d) e.g. 2y for every 2 years or 6m for every 6 month
  :Where:        StepInit
  :What to do:   Check StepInit. The second part is neither a date or d,m,y
  :Module:       timestep, datetosaveInit




E122
---------------------------------------------------------------------------
  :Description:  Third value in StepInit is not an integer after 'y' or 'm' or 'd'
  :Where:        StepInit
  :What to do:   Check StepInit. The third part after d,m,y is not an integer
  :Module:       timestep, datetosaveInit




E123
---------------------------------------------------------------------------
  :Description:  StepStart has to be a valid date
  :Where:        StepStart
  :What to do:   Check StepStart. It has to be a date e.g.  01/01/2009
  :Module:       timestep, checkifDate




E124
---------------------------------------------------------------------------
  :Description:  StepEnd is earlier than StepStart
  :Where:        StepStart, StepEnd
  :What to do:   Check StepStart and StepEnd. StepEnd has to be later than StepStart
  :Module:       timestep, checkifDate




E125
---------------------------------------------------------------------------
  :Description:  Spin Date is smaller/bigger than the first/last time step date
  :Where:        StepStart, SpinUp, StepEnd
  :What to do:   Check that SpinDate is in between StepStart and StepEnd
  :Module:       timestep, checkifDate




E127
---------------------------------------------------------------------------
  :Description:  Coordinates are not pairs
  :Where:        InflowPoints
  :What to do:   Check that location in InflowPoints comes in pairs
  :Module:       inflow, initial




E128
---------------------------------------------------------------------------
  :Description:  OUT_MAP_Daily = discharge may be not defined in [OUTPUT]
  :Where:        calc_ef_afterRun, Out_MAP_Daily
  :What to do:   Make sure that you define Out_MAP_Daily = discharge. Is seems daily discharge is not stored
  :Module:       environflow, initial




E129
---------------------------------------------------------------------------
  :Description:  Output points in Gauges are not pairs e.g. Gauges = 17.5 55.6 18.5
  :Where:        Gauges
  :What to do:   Check that output-points in Gauges are of coordinate e.g. Gauges = 6.25 51.75
  :Module:       output, initial




E130
---------------------------------------------------------------------------
  :Description:  Out_TSS or Out_MAP is not one of these: daily, monthend, monthtot, monthavg, annualend, annualtot, annualavg
  :Where:        Out_TSS, Out_MAP
  :What to do:   Please check that the wording after Out_TSS or Out_MAP is correct. Only a few keywords are valid e.g. Out_MAP_Daily, Out_TSS_monthavg
  :Module:       output, initial




E131
---------------------------------------------------------------------------
  :Description:  Second keyword after TSS or MAP is wrong
  :Where:        Out_TSS, Out_MAP
  :What to do:   Use TSS for point value, AreaSum for sum of area, AreaAvg for average of area e.g. OUT_TSS_AreaSum_Daily
  :Module:       output, initial




E132
---------------------------------------------------------------------------
  :Description:  Variable is not defined in list of variables
  :Where:        Out_TSS, Out_MAP
  :What to do:   Please correct the writing of the variable name, check also case sensitive e.g. Precipitation instead precipitation
  :Module:       output, dynamic




E201
---------------------------------------------------------------------------
  :Description:  Cannot load the maskmap as a file e.g. MaskMap = notexisting.tif
  :Where:        MaskMap
  :What to do:   Make sure the file you put in MaskMap is existing and is a map e.g. .nc, .map, .tif
  :Module:       datahandling, loadsetclone




E202
---------------------------------------------------------------------------
  :Description:  Your map is upside down
  :Where:        Any map
  :What to do:   Make sure your map is in right order e.g. latitude coordinate are turned
  :Module:       datahandling, loadmap




E203
---------------------------------------------------------------------------
  :Description:  Cannot find the map, filename does not exists at this location
  :Where:        Any map
  :What to do:   the datafile cannot be found, the location is wrong or the file is missing
  :Module:       datahandling, loadmap




E204
---------------------------------------------------------------------------
  :Description:  Trying to read the precipitation map metadata
  :Where:        Precipitation map
  :What to do:   Make sure the precipitation netcdf are existing and correct
  :Module:       datahandling, metaNetCDF




E205
---------------------------------------------------------------------------
  :Description:  Read error  while reading netcdf map
  :Where:        any netcdf map
  :What to do:   Make sure netcdf map is existing and correct
  :Module:       datahandling, readCoordNetCDF




E206
---------------------------------------------------------------------------
  :Description:  read error while reading meteo maps
  :Where:        any meteo maps
  :What to do:   Make sure the meteo input maps are in the right location and chave correct attributes
  :Module:       datahandling, checkMeteo_Wordclim




E207
---------------------------------------------------------------------------
  :Description:  read error while reading the wordclim map for downscaling meteo maps
  :Where:        Wordlclim maps
  :What to do:   Make sure the wordclim maps are in the right location and chave correct attributes
  :Module:       datahandling, checkMeteo_Wordclim




E208
---------------------------------------------------------------------------
  :Description:  Cannot find meteomaps
  :Where:        any meteomap
  :What to do:   Make sure the meteo input maps are at the right location
  :Module:       datahandling, multinetdf




E209
---------------------------------------------------------------------------
  :Description:  Error loading meteomaps
  :Where:        any meteomap
  :What to do:   Check if the filenames of the meteomaps are ok. Does the filename exist at this location
  :Module:       datahandling, multinetdf




E210
---------------------------------------------------------------------------
  :Description:  Meteomap does not have this date
  :Where:        any meteomap
  :What to do:   The netCDF file does not contain this date. Check your start and end date
  :Module:       datahandling, readmeteodata




E211
---------------------------------------------------------------------------
  :Description:  Error loading meteomaps
  :Where:        any meteomap
  :What to do:   Check if the filenames of the meteomaps are ok. Does the filename exist at this location
  :Module:       datahandling, readmeteodata




E212
---------------------------------------------------------------------------
  :Description:  Error loading any other time depending map but not meteomaps
  :Where:        any time dependending netCDF map
  :What to do:   Check if the filenames of the map is ok. Does the filename exist at this location
  :Module:       datahandling, readnetcdf2




E213
---------------------------------------------------------------------------
  :Description:  Error loading netCDF maps without time
  :Where:        any non time depending netCDF map
  :What to do:   Check if the filenames of the map is ok. Does the filename exist at this location
  :Module:       datahandling, readnetcdfWithoutTime




E214
---------------------------------------------------------------------------
  :Description:  Error loading the initial map
  :Where:        initial netCDF map
  :What to do:   Check if the loaction of the initial  map is o. Please check filename in initLoad
  :Module:       datahandling, readnetcdfInitial




E215
---------------------------------------------------------------------------
  :Description:  Trying to read the precipitation map metadata
  :Where:        Precipitation map
  :What to do:   Make sure the precipitation netcdf are existing and correct
  :Module:       timestep, checkifDate




E216
---------------------------------------------------------------------------
  :Description:  Outflow/Inflow point file cannot be loaded
  :Where:        InflowPoints
  :What to do:   Check if filename of InflowPoints exists
  :Module:       inflow, initial




E217
---------------------------------------------------------------------------
  :Description:  Mistake reading inflow file, name of inflow points are used twice
  :Where:        In_Dir 
  :What to do:   Check inflow file header
  :Module:       inflow, initial




E218
---------------------------------------------------------------------------
  :Description:  Mistake reading inflow file
  :Where:        In_Dir 
  :What to do:   Check if filename of inflow file exists
  :Module:       inflow, initial




E219
---------------------------------------------------------------------------
  :Description:  Mistake in discharge daily netcdf file
  :Where:        Out_MAP_Daily = discharge
  :What to do:   Something is wrong with the daily discharge file. Check location and content
  :Module:       environment, initial




E220
---------------------------------------------------------------------------
  :Description:  Output file path is wrong
  :Where:        OUT_Dir, PathOut
  :What to do:   Check OUT_Dir and PathOut. OUT_Dir can be used several times in the settings file.
  :Module:       output, appendinfo




E221
---------------------------------------------------------------------------
  :Description:  Error using file in Gauges
  :Where:        Gauges
  :What to do:   Please check if file in Gauges exists and is correct
  :Module:       output, initial




E301
---------------------------------------------------------------------------
  :Description:  Python version is not 64 bit
  :Where:        -
  :What to do:   Make sure that you use a 64 bit version of Python
  :Module:       global, main




E302
---------------------------------------------------------------------------
  :Description:  Settingsfile not found
  :Where:        -
  :What to do:   Make sure the settings file exists and is at the right location
  :Module:       configuration, parse_configuration




E303
---------------------------------------------------------------------------
  :Description:  An error occured while reading metaNetcdf.xml
  :Where:        metaNetcdfFile
  :What to do:   Please check that metaNetcdf is a valid .xml file
  :Module:       configuration, read_metanetcdf




E304
---------------------------------------------------------------------------
  :Description:  Cannot find alternative option file metaNetcdf.xml not found 
  :Where:        metaNetcdfFile
  :What to do:   Please check in metaNetcdfFile that the file exists
  :Module:       configuration, read_metanetcdf




E305
---------------------------------------------------------------------------
  :Description:  An error occured while reading alternative metaNetcdf.xml
  :Where:        metaNetcdfFile
  :What to do:   Please check that metaNetcdf is a valid .xml file
  :Module:       configuration, read_metanetcdf


