
######
Errors
######

.. contents:: 
    :depth: 2

.. _rst_errors:

	
Potential Errors
================

We try to make our program behave properly when encountering unexpected conditions. Therefore we caption a number of possible wrong inputs.

If you get an output with an error number please look at :ref:`rst_errorhandling`


Error because you did not run with Python
--------------------------------------------

if the model is causing an error with look like this::

   File "run_cwatm.py", line 116
   print("%-6s %10s %11s\n" %("Step","Date","Discharge"), end=' ')
   SyntaxError: invalid syntax

You run the model without the python command in front. Please use: python cwatm.py
(You may have to adjust the path to your python version and to cwatm.py).


Error because python is not added to the PATH
---------------------------------------------

If executing python return an error like this

   ‘python’ is not recognized as an internal or external command

You need either need to add Python to the PATH Environmental Variable or you need to start Python with full path.

   c:/path_to_python/python


Error because the path has white spaces included
------------------------------------------------

It is also possible to use paths with white spaces or dots. An easy way to avoid this is using relative paths, but is is also possible with absolute paths::

    "C:/Python 37/python" "C:/CWatM Hydrologic.modeling/CWatM/run_cwatm.py" "C:/CWatM Hydrologic.modeling/settings .rhine30min.ini" -l
    
    But in the settingsfile do not use apostrophe:
    PathRoot = C:/CWatM Hydrologic.modeling
   

Error because the python libraries are installed incorrectly
------------------------------------------------------------

If the model is causing an error at this stage, please check the python libraries::

    python
    import numpy
    import scipy.ndimage
    import gdal
    import netCDF4
	
	
Error because the settings file is not stored as utf-8 file
-----------------------------------------------------------

If the model causing an error which look like this::

    UnicodeDecodeError: 'utf-8' codec can't decode byte 0x83 in position 1504: invalid start byte


It is because the file was not stored as utf-8 (Unicode Transformation Format - 8-bit) file. This can happen if you use the Windows texteditor Wordpad or Notepad. We suggest you use Notepad++ and store the file as utf-8. Might happen too, if your language use strange characters like German Umlaut.


Error because the references are used wrong
-------------------------------------------

In the settingsfile we use references::

    [FILE_PATHS]
    PathRoot = C:\basin
    PathMaps = $(PathRoot)/input
	
	
If you use the reference in the next section, you have to put in the section where you defined the reference. Here: FILE_PATHS::

    [NETCDF_ATTRIBUTES]
    metaNetcdfFile = $(FILE_PATHS:PathRoot)/metaNetcdf.xml


Errors Errors Err Er E
----------------------

If you type::

   python cwatm.py settings.ini -l


You should see something like this::

   E:\CWatM_rhine\source>python cwatm.py settings_rhine30min.ini -l
   CWatM - Community Water Model  Version: 0.991  Date:  16/09/2017
   International Institute of Applied Systems Analysis (IIASA)
   Running under platform:  Windows
   -----------------------------------------------------------
   CWatM Simulation Information and Setting
   The simulation output as specified in the settings file: settings_rhine30min.ini
   can be found in E:/CWatM_rhine/output
   Step         Date   Discharge
   1      01/01/1961        4.20
   2      02/01/1961        4.23
   ...


If you don't see this. Something went wrong and you might see this instead::

   E:\CWatM_rhine\source>python cwatm.py settings_rhine30min.ini -l
   CWatM - Community Water Model  Version: 0.991  Date:  16/09/2017
   International Institute of Applied Systems Analysis (IIASA)
   Running under platform:  Windows
   -----------------------------------------------------------
   ERROR 4: `E:/CWatM_rhine/cwatm_input/routing/ldd.map' does not exist in the file system,
   and is not recognised as a supported dataset name.
   management_modules.messages.CWatMFileError:
   ======================== CWatM FILE ERROR ===========================
   In  "Ldd"
   searching: "E:/CWatM_rhine/cwatm_input/routing/ldd.map"
   path: E:/CWatM_rhine/cwatm_input/routing does not exists

| The model tries to help you on finding the error.
| In this case it is looking for the river network map ldd.map or ldd.nc or ldd.tif
| but it cannot find the file and not even the path to the file.

Here you might change::

   [FILE_PATHS]
   PathRoot = E:/CWatM_rhine
   PathMaps = $(PathRoot)/cwatm_input

or::

   [TOPOP]
   # local drain direction map (1-9)
   Ldd = $(FILE_PATHS:PathMaps)/routing/ldd.map

But many other error can occure too! Have fun.


.. _rst_errorhandling:

Error handling of CWatM – list of error codes
=============================================

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
    "`E119`_", "Either date in StepStart is not a date or in SpinUp or StepEnd it is neither a number or a date", "StepStart\, SpinUp\, StepEnd", "Please check the variables StepStart\, SpinUp\, StartEnd - A date is missing", "timestep", "Calendar"
    "`E120`_", "First date in StepInit is neither a number or a date", "StepInit", "Check StepInit in INITITIAL CONDITIONS. It is not a date or a number", "timestep", "Calendar"
    "`E121`_", "Second value in StepInit is not a number or date nor indicating a repetition of year(y)\, month(m) or day(d) e.g. 2y for every 2 years or 6m for every 6 month", "StepInit", "Check StepInit. The second part is neither a date or d\,m\,y", "timestep", "datetosaveInit"
    "`E122`_", "Third value in StepInit is not an integer after 'y' or 'm' or 'd'", "StepInit", "Check StepInit. The third part after d\,m\,y is not an integer", "timestep", "datetosaveInit"
    "`E123`_", "StepStart has to be a valid date", "StepStart", "Check StepStart. It has to be a date e.g.  01/01/2009", "timestep", "checkifDate"
    "`E124`_", "StepEnd is earlier than StepStart", "StepStart\, StepEnd", "Check StepStart and StepEnd. StepEnd has to be later than StepStart", "timestep", "checkifDate"
    "`E125`_", "Spin Date is smaller/bigger than the first/last time step date", "StepStart\, SpinUp\, StepEnd", "Check that SpinDate is in between StepStart and StepEnd", "timestep", "checkifDate"
    "`E126`_", "Time step not stored in the netCDF map stack", "Any netCDF map stack", "The file has fewer time steps than the run needs - check the file and StepStart / StepEnd", "datahandling", "loadmap"
    "`E127`_", "Coordinates are not pairs", "InflowPoints", "Check that location in InflowPoints comes in pairs", "inflow", "initial"
    "`E128`_", "OUT_MAP_Daily = discharge may be not defined in [OUTPUT]", "calc_ef_afterRun\, Out_MAP_Daily", "Make sure that you define Out_MAP_Daily = discharge. Is seems daily discharge is not stored", "Environflow", "initial"
    "`E129`_", "Output points in Gauges are not pairs e.g. Gauges = 17.5 55.6 18.5", "Gauges", "Check that output-points in Gauges are of coordinate e.g. Gauges = 6.25 51.75", "output", "initial"
    "`E130`_", "Out_TSS or Out_MAP is not one of these: daily\, monthend\, monthtot\, monthavg\, annualend\, annualtot\, annualavg", "Out_TSS\, Out_MAP", "Please check that the wording after Out_TSS or Out_MAP is correct. Only a few keywords are valid e.g. Out_MAP_Daily\, Out_TSS_monthavg", "output", "initial"
    "`E131`_", "Second keyword after TSS or MAP is wrong", "Out_TSS\, Out_MAP", "Use TSS for point value\, AreaSum for sum of area\, AreaAvg for average of area e.g. OUT_TSS_AreaSum_Daily", "output", "initial"
    "`E132`_", "Variable is not defined in list of variables", "Out_TSS\, Out_MAP", "Please correct the writing of the variable name\, check also case sensitive e.g. Precipitation instead precipitation", "output", "dynamic"
    "`E133`_", "The maps seem to be in lat/lon (cell size and corner in degree) - the cell area cannot be derived from the cell size", "MaskMap\, gridSizeUserDefined\, CellArea", "Set gridSizeUserDefined = True in [OPTIONS] and give a map of the cell area in m2 with CellArea", "miscInitial", "initial"
    "`E134`_", "Coordinates of a gauge are inside the box of the mask map but on a cell outside the mask", "Gauges\, MaskMap", "Move the gauge to a cell inside the mask (or change MaskMap)", "output", "appendinfo"
    "`E135`_", "Output variable name is not valid", "output keys e.g. OUT_MAP_Daily\, OUT_TSS_MonthAvg", "Use a variable name\, optionally with integer indices e.g. discharge or actualET[1]", "datahandling", "parseoutvar"
    "`E136`_", "No key with this name in the settings file (the closest key is shown)", "Any key", "Check the writing of the key (also upper and lower case) or add it to the settings file", "datahandling", "checkOption"
    "`E137`_", "The Excel settings file is not given in the settings file", "Excel_settings_file", "Add Excel_settings_file = <path>/cwatm_settings.xlsx (needed e.g. for includeCrops)", "initcondition", "initial"
    "`E138`_", "A date does not exist in the calendar of the precipitation maps (e.g. 29 February in a 365 day calendar)", "StepStart\, StepEnd\, SpinUp\, StepInit", "Use a date that exists in the calendar of the meteo maps", "timestep", "datenum"
    "`E139`_", "WaterCycle output needs a standard calendar in the precipitation maps", "OUT_TSS_WaterCycle ...", "Use meteo maps with a standard calendar or no WaterCycle output", "output", "writeTssFileNew"
    "`E140`_", "The class map of an area function (npareatotal\, npareaaverage\, npareamaximum) cannot be used: float values or a negative class id", "Maps used as classes (e.g. waterBodyID\, adminSegments)", "Use a map with integer classes >= 0", "replace_pcr", "_classerror"
    "`E141`_", "Circular reference in placeholders $(...) or more than 10 nested levels", "Any key with $(...)", "Check the placeholders - a key must not refer to itself", "configuration", "get"
    "`E142`_", "An option in [OPTIONS] is neither True/False nor an integer", "[OPTIONS]", "Write True or False (or an integer) e.g. includeWaterDemand = True", "configuration", "splitout"
    "`E143`_", "Placeholder cannot be read - it has to be $(SECTION:KEY) or $(KEY)", "Any key with $(...)", "Check the brackets and the colon of the placeholder", "configuration", "get"
    "`E144`_", "Section [OPTIONS] is not written in capital letters", "[OPTIONS]", "Write [OPTIONS]", "configuration", "splitout"
    "`E145`_", "Output key is not possible - it has to be OUT_MAP\, OUT_TSS or OUT_RES with a valid type (e.g. OUT_MAP_Daily\, OUT_TSS_MonthAvg)", "output keys e.g. OUT_MAP_Daily\, OUT_TSS_MonthAvg","Check the writing of the output key", "configuration", "splitout"
    "`E146`_", "nlay is smaller than 1", "nlay", "Set nlay = 1 or more (number of ModFlow layers)", "groundwater_modflow transient", "initial"
    "`E147`_", "The CRS of the CWatM grid (MaskMap) is not known - needed for the overlap of CWatM and ModFlow cells", "MaskMap\, cwatm_crs", "Set cwatm_crs = EPSG:... in [GROUNDWATER_MODFLOW] or use a MaskMap with CRS", "groundwater_modflow grid", "cwatm_crs"
    "`E148`_", "More than half of the active ModFlow cells are not inside the CWatM mask", "modflow_basin\, MaskMap", "Check modflow_basin\, MaskMap and the CRS of both (cwatm_crs)", "groundwater_modflow grid", "ModflowGrid"
    "`E149`_", "A map at ModFlow resolution (MODFLOW head of a restart or init_water_table) has another size than the ModFlow grid or another number of layers than nlay", "init_water_table\, <init file>_modflowhead.nc", "Use a map of the same ModFlow grid (modflow_basin)", "groundwater_modflow grid", "read_map"
    "`E150`_", "A layer property of the ModFlow layers (e.g. thickness3) is missing in the settings file", "thickness<n>\, poro<n>\, permeability<n>\, nlay", "Give a value or map for each layer n = 1 ... nlay (layer 1 also without number)", "groundwater_modflow grid", "layer_property"
    "`E151`_", "The MODFLOW solver in modflow_solver is not known", "modflow_solver", "Use one of: simple\, complex\, super_complex\, cooley", "groundwater_modflow transient", "read_settings"
    "`E152`_", "MODFLOW gives a wrong head (not a number or > 1e6 m) - the MODFLOW solver did not converge", "modflow_solver\, modflow_timestep\, thickness<n>\, permeability<n>\, pumping", "Use another solver (modflow_solver = cooley\, complex or super_complex)\, a smaller modflow_timestep or check the aquifer properties", "groundwater_modflow transient", "modflow_run"
    "`E153`_", "The netCDF variable (e.g. topo_percentile_prm = z_p10) is not in the file at ModFlow resolution", "topo_percentile_modflow\, topo_percentile_prm", "Use one of the variables listed in the message", "groundwater_modflow grid", "read_map"
    "`E154`_", "A map does not cover the whole mask map", "Any map", "Use a map which covers the mask map (the message gives the missing cells west and north)", "datahandling", "checkmapcover"
    "`E155`_", "A map is not on the same grid as the mask map (shifted by a part of a cell)", "Any map", "Use a map with the same cell size and cell borders as the mask map", "datahandling", "checkmapcover"
    "`E156`_", "Excel sheet Reservoir_transfers has less than 370 rows or a giving / receiving reservoir is not a whole number", "Excel_settings_file\, sheet Reservoir_transfers", "Use 4 rows + 366 days and whole numbers for the reservoirs (0 = from/to outside)", "initcondition", "reservoir_transfers"
    "`E157`_", "Excel sheet Crops: growth stages are read as days but are not whole days or a season is shorter than 25 days", "Excel_settings_file\, sheet Crops", "Give whole days for GS1 to GS4 and a season of at least 25 days", "initcondition", "crops_initialise"
    "`E158`_", "Inflow points are outside the mask map or in the same cell as another point\, or no inflow point is inside the mask map", "InflowPoints\, MaskMap", "Check the coordinates or the map of the inflow points", "inflow", "initial"
    "`E159`_", "An inflow file has missing or negative values in this run", "In_Dir\, QInTS", "Give a value >= 0 for each day of the run", "inflow", "initial"
    "`E160`_", "An inflow point has no column in the inflow files", "InflowPoints\, QInTS", "Add a column for each inflow point (the message lists the columns of the files)", "inflow", "initial"
    "`E161`_", "An inflow file has no value for some days of this run", "In_Dir\, QInTS", "Give daily values from StepStart to StepEnd", "inflow", "initial"
    "`E162`_", "The inflow files have a different number of rows", "QInTS", "Use inflow files with the same days", "inflow", "initial"
    "`E163`_", "An inflow point number is in more than one cell of the inflow point map", "InflowPoints", "Use each number only once in the map", "inflow", "getlocOutpoints"
    "`E164`_", "inflow = True needs includeRouting = True", "inflow\, includeRouting", "Set includeRouting = True or inflow = False", "inflow", "initial"
    "`E165`_", "Environmental flow needs all 12 months from SpinUp to StepEnd", "calc_environflow\, SpinUp\, StepEnd", "Run at least one day in each month", "environflow", "initial"
    "`E166`_", "The discharge file for the environmental flow starts too late or has not enough days", "OUT_MAP_Daily = discharge\, SpinUp\, StepStart\, StepEnd", "Use a discharge file which covers the whole period", "datahandling", "readDischargeFiles"
    "`E167`_", "The discharge for the environmental flow has missing values on some days", "OUT_MAP_Daily = discharge", "Use a discharge file without missing values in the mask", "environflow", "dynamic"
    "`E168`_", "An output key in a section without OUT_Dir", "OUT_Dir", "Add OUT_Dir = ... to the section with the output", "output", "appendinfo"
    "`E169`_", "The discharge map for the environmental flow has another size than the mask map", "OUT_MAP_Daily = discharge\, MaskMap", "Use the discharge of a run with the same mask map", "datahandling", "readDischargeFiles"
    "`E170`_", "waterquality = True needs includeRouting = True", "waterquality\, includeRouting", "Set includeRouting = True or waterquality = False", "waterquality1", "initial"
    "`E171`_", "use_GeneralCropIrr = True needs the map GeneralCrop_Irr", "use_GeneralCropIrr\, GeneralCrop_Irr", "Add GeneralCrop_Irr to the settings file or set use_GeneralCropIrr = False", "evaporation", "dynamic"
    "`E172`_", "use_GeneralCropnonIrr = True needs the map GeneralCrop_nonIrr", "use_GeneralCropnonIrr\, GeneralCrop_nonIrr", "Add GeneralCrop_nonIrr to the settings file or set use_GeneralCropnonIrr = False", "evaporation", "dynamic"
    "`E173`_", "PET_modus is not a valid method for the potential evaporation", "PET_modus", "Use 1 (Penman-Monteith)\, 2 (Milly-Dunne)\, 3 (Penman-Monteith with CO2 correction)\, 4 (Priestley-Taylor) or 5 (modified Thornthwaite)", "readmeteo", "initial"
    "`E174`_", "The CO2 file must have one CO2 value per year (not a map)", "co2conc", "Use a file with the variable CO2 with only the dimension time", "evaporationPot", "dynamic_1"
    "`E175`_", "chanBeta has to be a single number\, not a map", "chanBeta", "Use one value e.g. chanBeta = 0.6", "routing_kinematic", "initial"
    "`E176`_", "snowmelt_radiation = True needs SnowMeltRad", "snowmelt_radiation\, SnowMeltRad", "Add SnowMeltRad (calibration factor of the radiation snow melt\, about 1.0) to the settings file", "snow", "initial"
    "`E177`_", "The variable is not in the netCDF file of a yearly map", "irrNonPaddy_efficiency (yearly netCDF stack)", "Use the name of the variable in the netCDF file", "datahandling", "loadmapYearly"
    "`E178`_", "Irrigation efficiency is not > 0 and <= 1\, or fraction_IncreaseIrrigation_Nonpaddy < 1 (in cells with irrigated area)", "irrPaddy_efficiency\, irrNonPaddy_efficiency\, fraction_IncreaseIrrigation_Nonpaddy", "Use efficiencies > 0 and <= 1 and a factor >= 1", "irrigation", "checkEfficiency"
    "`E179`_", "A reservoir outlet cell is in a command area but not on a canal of this command area - the canal leakage would be lost", "reservoir_command_areas\, canals", "Put the outlet cell of the reservoir on a canal cell of its command area\, or the command area number on the outlet cell", "surface_water_abstraction", "initial"
    "`E180`_", "activate_irrigation_agents = True with monthly requests but no adminSegments map", "activate_irrigation_agents\, adminSegments", "Add adminSegments (the agent areas) or set activate_irrigation_agents = False", "irrigation_agents", "initial"
    "`E181`_", "Water body output key is not possible - it has to be OUT_RES_ or OUT_RES0_ ... OUT_RES6_ with a time type (not TotalTot\, TotalAvg)", "output keys e.g. OUT_RES2_Daily", "Use n = 0 (all) ... 6 and Daily\, MonthTot\, MonthAvg\, MonthEnd\, AnnualTot\, AnnualAvg or AnnualEnd", "configuration", "splitout"
    "`E182`_", "WaterCycle or WaterBalance as water body output (OUT_RES...)", "OUT_RES<n>_... = WaterCycle", "Use WaterCycle / WaterBalance with OUT_TSS_... (catchment of the gauges)", "output", "initial_res"
    "`E201`_", "Cannot load the maskmap as a file e.g. MaskMap = notexisting.tif", "MaskMap", "Make sure the file you put in MaskMap is existing and is a map e.g. \*.nc\, \*.map\, \*.tif", "datahandling", "loadsetclone"
    "`E202`_", "Your map is upside down", "Any map", "Make sure your map is in right order e.g. latitude coordinate are turned", "datahandling", "loadmap"
    "`E203`_", "Cannot find the map\, filename does not exists at this location", "Any map", "the datafile cannot be found\, the location is wrong or the file is missing", "datahandling", "loadmap"
    "`E204`_", "Trying to read the precipitation map metadata", "Precipitation map", "Make sure the precipitation netcdf are existing and correct", "datahandling", "metaNetCDF"
    "`E205`_", "Read error  while reading netcdf map", "any netcdf map", "Make sure netcdf map is existing and correct", "datahandling", "readCoordNetCDF"
    "`E206`_", "read error while reading meteo maps", "any meteo maps", "Make sure the meteo input maps are in the right location and chave correct attributes", "datahandling", "checkMeteo_Wordclim"
    "`E207`_", "read error while reading the wordclim map for downscaling meteo maps", "Wordlclim maps", "Make sure the wordclim maps are in the right location and chave correct attributes", "datahandling", "checkMeteo_Wordclim"
    "`E208`_", "Cannot find meteomaps", "any meteomap", "Make sure the meteo input maps are at the right location", "datahandling", "multinetdf"
    "`E209`_", "Error loading meteomaps", "any meteomap", "Check if the filenames of the meteomaps are ok. Does the filename exist at this location", "datahandling", "multinetdf"
    "`E210`_", "Meteomap does not have this date", "any meteomap", "The netCDF file does not contain this date. Check your start and end date", "datahandling", "readmeteodata"
    "`E211`_", "Error loading meteomaps", "any meteomap", "Check if the filenames of the meteomaps are ok. Does the filename exist at this location", "datahandling", "readmeteodata"
    "`E212`_", "Error loading any other time depending map but not meteomaps", "any time dependending netCDF map", "Check if the filenames of the map is ok. Does the filename exist at this location", "datahandling", "readnetcdf2"
    "`E213`_", "Error loading netCDF maps without time", "any non time depending netCDF map", "Check if the filenames of the map is ok. Does the filename exist at this location", "datahandling", "readnetcdfWithoutTime"
    "`E214`_", "Error loading the initial map", "initial netCDF map", "Check if the loaction of the initial  map is o. Please check filename in initLoad", "datahandling", "readnetcdfInitial"
    "`E215`_", "Trying to read the precipitation map metadata", "Precipitation map", "Make sure the precipitation netcdf are existing and correct", "timestep", "checkifDate"
    "`E216`_", "Outflow/Inflow point file cannot be loaded", "InflowPoints", "Check if filename of InflowPoints exists", "inflow", "initial"
    "`E217`_", "Mistake reading inflow file\, name of inflow points are used twice", "In_Dir ", "Check inflow file header", "inflow", "initial"
    "`E218`_", "Mistake reading inflow file", "In_Dir ", "Check if filename of inflow file exists", "inflow", "initial"
    "`E219`_", "Mistake in discharge daily netcdf file", "Out_MAP_Daily = discharge", "Something is wrong with the daily discharge file. Check location and content", "Environment", "initial"
    "`E220`_", "Output file path is wrong", "OUT_Dir\, PathOut", "Check OUT_Dir and PathOut. OUT_Dir can be used several times in the settings file.", "output", "appendinfo"
    "`E221`_", "Error using file in Gauges", "Gauges", "Please check if file in Gauges exists and is correct", "output", "initial"
    "`E222`_", "Path to the MODFLOW 6 library does not exist", "path_mf6dll", "Check path_mf6dll (folder with libmf6.dll / libmf6.so)", "groundwater_modflow transient", "initial"
    "`E223`_", "A meteo netCDF map stack cannot be opened", "Meteo maps (e.g. PrecipitationMaps\, TavgMaps)", "Check that the file exists and is a valid netCDF file", "datahandling", "readmeteodata"
    "`E224`_", "A netCDF map stack with 12 monthly maps cannot be read", "Monthly maps (e.g. lapse rate)", "Check that the file exists and has 12 maps", "datahandling", "readnetcdf12month"
    "`E225`_", "Precipitation maps not found", "PrecipitationMaps", "Check PrecipitationMaps and PathMeteo", "readmeteo", "initial"
    "`E226`_", "MODFLOW simulation file mfsim.nam not found in the MODFLOW working folder", "PathGroundwaterModflowOutput\, load_modflow_from_disk", "Delete input_hash in <PathGroundwaterModflowOutput>/wd or set load_modflow_from_disk = False - then the MODFLOW input files are written new", "groundwater_modflow modflow6", "load_bmi"
    "`E227`_", "MODFLOW input files listed in the name files (or binary files named with OPEN/CLOSE in a package file) are missing - MODFLOW itself would end Python", "PathGroundwaterModflowOutput\, load_modflow_from_disk", "Delete input_hash in <PathGroundwaterModflowOutput>/wd or set load_modflow_from_disk = False - then the MODFLOW input files are written new", "groundwater_modflow modflow6", "load_bmi"
    "`E301`_", "Python version is not 64 bit", "-", "Make sure that you use a 64 bit version of Python", "global", "main"
    "`E302`_", "Settingsfile not found", "-", "Make sure the settings file exists and is at the right location", "configuration", "parse_configuration"
    "`E303`_", "An error occured while reading metaNetcdf.xml", "metaNetcdfFile", "Please check that metaNetcdf is a valid .xml file", "configuration", "read_metanetcdf"
    "`E304`_", "Cannot find alternative option file metaNetcdf.xml not found ", "metaNetcdfFile", "Please check in metaNetcdfFile that the file exists", "configuration", "read_metanetcdf"
    "`E305`_", "The routing library is an old version without parallel routing (kinematicPar)", "-", "Use the current routing library t6 (compile it again)", "globals", "clear"
    "`E306`_", "The routing library (t6) cannot be loaded", "-", "Check that the routing library for your system (t6.dll\, t6_linux.so\, ...) is in the cwatm folder (compile it if needed)", "globals", "clear"
    "`E307`_", "Settings file cannot be read: no UTF-8 encoding\, a key or section is twice in the file\, a line is outside a section or is not key = value", "Settings file", "Correct the line given in the message", "configuration", "splitout"
    "`E308`_", "No key PathOut (output directory) in the settings file", "PathOut", "Add PathOut = <output folder> in [FILE_PATHS]", "configuration", "splitout"
    "`E309`_", "metaNetcdf.xml has no <CWATM> element or an entry without varname", "metaNetcdfFile", "Check the metadata file", "configuration", "read_metanetcdf"
    "`E310`_", "The MODFLOW library libmf6.dll (Windows) / libmf6.so (Linux) is not found or cannot be loaded", "path_mf6dll", "Check path_mf6dll: the folder needs libmf6.dll / libmf6.so of a MODFLOW 6 release", "groundwater_modflow modflow6", "load_bmi"
    "`E311`_", "The MODFLOW library is too old for the installed xmipy (e.g. libmf6 6.2.2 has no get_value_ptr)", "path_mf6dll", "Use a current libmf6 (e.g. MODFLOW 6.8.1) in path_mf6dll", "groundwater_modflow modflow6", "load_bmi"
    "`E312`_", "MODFLOW initialize failed (error from xmipy)", "MODFLOW input files", "Read the MODFLOW error message and the listing file mfsim.lst named in the message", "groundwater_modflow modflow6", "load_bmi"
    "`E313`_", "MODFLOW stopped (e.g. a Fortran STOP for a wrong input file\, exit code 2) - only the MODFLOW process ends\, not Python", "MODFLOW input files\, modflow_subprocess", "Read the MODFLOW error message and the listing file mfsim.lst named in the message", "groundwater_modflow modflow6_process", "_receive"
    "`E314`_", "Python error in the MODFLOW process during a time step (e.g. the solver does not converge)", "modflow_timestep\, use_complex_solver_for_modflow", "If the solver does not converge: use a smaller modflow_timestep or use_complex_solver_for_modflow. Read the MODFLOW error message and the listing file mfsim.lst named in the message", "groundwater_modflow modflow6_process", "_child"
    "`E315`_", "MODFLOW did not finish a call (the start or one time step) within modflow_timeout seconds - the MODFLOW process is stopped", "modflow_timeout", "If MODFLOW is only slow: use a larger modflow_timeout (0: no limit). Else check the MODFLOW input", "groundwater_modflow modflow6_process", "_receive"
    "`E400`_", "Not an error: only the environmental flow is calculated from an existing discharge file - the run ends with exit code 400", "calc_environflow = True\, calc_ef_afterRun = False\, EFDis", "Nothing to do", "environflow / cwatm_dynamic", "dynamic"
    "`E601`_", "The temperature maps might be in Kelvin instead of Celsius or vice versa", "TavgMaps\, TminMaps\, TmaxMaps\, [OPTIONS]", "Check the temperature flag in [OPTIONS] (temperature in Kelvin or Celsius)", "readmeteo", "check_celsius"




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




E126
---------------------------------------------------------------------------
  :Description:  Time step not stored in the netCDF map stack
  :Where:        Any netCDF map stack
  :What to do:   The file has fewer time steps than the run needs - check the file and StepStart / StepEnd
  :Module:       datahandling, loadmap




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




E133
---------------------------------------------------------------------------
  :Description:  The maps seem to be in lat/lon (cell size and corner in degree) - the cell area cannot be derived from the cell size
  :Where:        MaskMap, gridSizeUserDefined, CellArea
  :What to do:   Set gridSizeUserDefined = True in [OPTIONS] and give a map of the cell area in m2 with CellArea
  :Module:       miscInitial, initial




E134
---------------------------------------------------------------------------
  :Description:  Coordinates of a gauge are inside the box of the mask map but on a cell outside the mask
  :Where:        Gauges, MaskMap
  :What to do:   Move the gauge to a cell inside the mask (or change MaskMap)
  :Module:       output, appendinfo




E135
---------------------------------------------------------------------------
  :Description:  Output variable name is not valid
  :Where:        output keys e.g. OUT_MAP_Daily, OUT_TSS_MonthAvg
  :What to do:   Use a variable name, optionally with integer indices e.g. discharge or actualET[1]
  :Module:       datahandling, parseoutvar




E136
---------------------------------------------------------------------------
  :Description:  No key with this name in the settings file (the closest key is shown)
  :Where:        Any key
  :What to do:   Check the writing of the key (also upper and lower case) or add it to the settings file
  :Module:       datahandling, checkOption




E137
---------------------------------------------------------------------------
  :Description:  The Excel settings file is not given in the settings file
  :Where:        Excel_settings_file
  :What to do:   Add Excel_settings_file = <path>/cwatm_settings.xlsx (needed e.g. for includeCrops)
  :Module:       initcondition, initial




E138
---------------------------------------------------------------------------
  :Description:  A date does not exist in the calendar of the precipitation maps (e.g. 29 February in a 365 day calendar)
  :Where:        StepStart, StepEnd, SpinUp, StepInit
  :What to do:   Use a date that exists in the calendar of the meteo maps
  :Module:       timestep, datenum




E139
---------------------------------------------------------------------------
  :Description:  WaterCycle output needs a standard calendar in the precipitation maps
  :Where:        OUT_TSS_WaterCycle ...
  :What to do:   Use meteo maps with a standard calendar or no WaterCycle output
  :Module:       output, writeTssFileNew




E140
---------------------------------------------------------------------------
  :Description:  The class map of an area function (npareatotal, npareaaverage, npareamaximum) cannot be used: float values or a negative class id
  :Where:        Maps used as classes (e.g. waterBodyID, adminSegments)
  :What to do:   Use a map with integer classes >= 0
  :Module:       replace_pcr, _classerror




E141
---------------------------------------------------------------------------
  :Description:  Circular reference in placeholders $(...) or more than 10 nested levels
  :Where:        Any key with $(...)
  :What to do:   Check the placeholders - a key must not refer to itself
  :Module:       configuration, get




E142
---------------------------------------------------------------------------
  :Description:  An option in [OPTIONS] is neither True/False nor an integer
  :Where:        [OPTIONS]
  :What to do:   Write True or False (or an integer) e.g. includeWaterDemand = True
  :Module:       configuration, splitout




E143
---------------------------------------------------------------------------
  :Description:  Placeholder cannot be read - it has to be $(SECTION:KEY) or $(KEY)
  :Where:        Any key with $(...)
  :What to do:   Check the brackets and the colon of the placeholder
  :Module:       configuration, get




E144
---------------------------------------------------------------------------
  :Description:  Section [OPTIONS] is not written in capital letters
  :Where:        [OPTIONS]
  :What to do:   Write [OPTIONS]
  :Module:       configuration, splitout




E145
---------------------------------------------------------------------------
  :Description:  Output key is not possible - it has to be OUT_MAP, OUT_TSS or OUT_RES with a valid type (e.g. OUT_MAP_Daily, OUT_TSS_MonthAvg)
  :Where:        output keys e.g. OUT_MAP_Daily, OUT_TSS_MonthAvg
  :What to do:   Check the writing of the output key
  :Module:       configuration, splitout




E146
---------------------------------------------------------------------------
  :Description:  nlay is smaller than 1
  :Where:        nlay
  :What to do:   Set nlay = 1 or more (number of ModFlow layers)
  :Module:       groundwater_modflow transient, initial



E147
---------------------------------------------------------------------------
  :Description:  The CRS of the CWatM grid (MaskMap) is not known - needed for the overlap of CWatM and ModFlow cells
  :Where:        MaskMap, cwatm_crs
  :What to do:   Set cwatm_crs = EPSG:... in [GROUNDWATER_MODFLOW] or use a MaskMap with CRS
  :Module:       groundwater_modflow grid, cwatm_crs



E148
---------------------------------------------------------------------------
  :Description:  More than half of the active ModFlow cells are not inside the CWatM mask
  :Where:        modflow_basin, MaskMap
  :What to do:   Check modflow_basin, MaskMap and the CRS of both (cwatm_crs)
  :Module:       groundwater_modflow grid, ModflowGrid



E149
---------------------------------------------------------------------------
  :Description:  A map at ModFlow resolution (MODFLOW head of a restart or init_water_table) has another size than the ModFlow grid or another number of layers than nlay
  :Where:        init_water_table, <init file>_modflowhead.nc
  :What to do:   Use a map of the same ModFlow grid (modflow_basin)
  :Module:       groundwater_modflow grid, read_map



E150
---------------------------------------------------------------------------
  :Description:  A layer property of the ModFlow layers (e.g. thickness3) is missing in the settings file
  :Where:        thickness<n>, poro<n>, permeability<n>, nlay
  :What to do:   Give a value or map for each layer n = 1 ... nlay (layer 1 can also be given without number, e.g. thickness)
  :Module:       groundwater_modflow grid, layer_property



E151
---------------------------------------------------------------------------
  :Description:  The MODFLOW solver in modflow_solver is not known
  :Where:        modflow_solver
  :What to do:   Use one of: simple, complex, super_complex, cooley
  :Module:       groundwater_modflow transient, read_settings



E152
---------------------------------------------------------------------------
  :Description:  MODFLOW gives a wrong head (not a number or > 1e6 m) - the MODFLOW solver did not converge
  :Where:        modflow_solver, modflow_timestep, thickness<n>, permeability<n>, pumping
  :What to do:   Use another solver (modflow_solver = cooley, complex or super_complex), a smaller modflow_timestep or check the aquifer properties
  :Module:       groundwater_modflow transient, modflow_run



E153
---------------------------------------------------------------------------
  :Description:  The netCDF variable (e.g. topo_percentile_prm = z_p10) is not in the file at ModFlow resolution
  :Where:        topo_percentile_modflow, topo_percentile_prm
  :What to do:   Use one of the variables listed in the message
  :Module:       groundwater_modflow grid, read_map




E154
---------------------------------------------------------------------------
  :Description:  A map does not cover the whole mask map
  :Where:        Any map
  :What to do:   Use a map which covers the mask map (the message gives the missing cells west and north)
  :Module:       datahandling, checkmapcover




E155
---------------------------------------------------------------------------
  :Description:  A map is not on the same grid as the mask map (shifted by a part of a cell)
  :Where:        Any map
  :What to do:   Use a map with the same cell size and cell borders as the mask map
  :Module:       datahandling, checkmapcover




E156
---------------------------------------------------------------------------
  :Description:  Excel sheet Reservoir_transfers has less than 370 rows or a giving / receiving reservoir is not a whole number
  :Where:        Excel_settings_file, sheet Reservoir_transfers
  :What to do:   Use 4 rows + 366 days and whole numbers for the reservoirs (0 = from/to outside)
  :Module:       initcondition, reservoir_transfers




E157
---------------------------------------------------------------------------
  :Description:  Excel sheet Crops: growth stages are read as days but are not whole days or a season is shorter than 25 days
  :Where:        Excel_settings_file, sheet Crops
  :What to do:   Give whole days for GS1 to GS4 and a season of at least 25 days
  :Module:       initcondition, crops_initialise




E158
---------------------------------------------------------------------------
  :Description:  Inflow points are outside the mask map or in the same cell as another point, or no inflow point is inside the mask map
  :Where:        InflowPoints, MaskMap
  :What to do:   Check the coordinates or the map of the inflow points
  :Module:       inflow, initial




E159
---------------------------------------------------------------------------
  :Description:  An inflow file has missing or negative values in this run
  :Where:        In_Dir, QInTS
  :What to do:   Give a value >= 0 for each day of the run
  :Module:       inflow, initial




E160
---------------------------------------------------------------------------
  :Description:  An inflow point has no column in the inflow files
  :Where:        InflowPoints, QInTS
  :What to do:   Add a column for each inflow point (the message lists the columns of the files)
  :Module:       inflow, initial




E161
---------------------------------------------------------------------------
  :Description:  An inflow file has no value for some days of this run
  :Where:        In_Dir, QInTS
  :What to do:   Give daily values from StepStart to StepEnd
  :Module:       inflow, initial




E162
---------------------------------------------------------------------------
  :Description:  The inflow files have a different number of rows
  :Where:        QInTS
  :What to do:   Use inflow files with the same days
  :Module:       inflow, initial




E163
---------------------------------------------------------------------------
  :Description:  An inflow point number is in more than one cell of the inflow point map
  :Where:        InflowPoints
  :What to do:   Use each number only once in the map
  :Module:       inflow, getlocOutpoints




E164
---------------------------------------------------------------------------
  :Description:  inflow = True needs includeRouting = True
  :Where:        inflow, includeRouting
  :What to do:   Set includeRouting = True or inflow = False
  :Module:       inflow, initial




E165
---------------------------------------------------------------------------
  :Description:  Environmental flow needs all 12 months from SpinUp to StepEnd
  :Where:        calc_environflow, SpinUp, StepEnd
  :What to do:   Run at least one day in each month
  :Module:       environflow, initial




E166
---------------------------------------------------------------------------
  :Description:  The discharge file for the environmental flow starts too late or has not enough days
  :Where:        OUT_MAP_Daily = discharge, SpinUp, StepStart, StepEnd
  :What to do:   Use a discharge file which covers the whole period
  :Module:       datahandling, readDischargeFiles




E167
---------------------------------------------------------------------------
  :Description:  The discharge for the environmental flow has missing values on some days
  :Where:        OUT_MAP_Daily = discharge
  :What to do:   Use a discharge file without missing values in the mask
  :Module:       environflow, dynamic




E168
---------------------------------------------------------------------------
  :Description:  An output key in a section without OUT_Dir
  :Where:        OUT_Dir
  :What to do:   Add OUT_Dir = ... to the section with the output
  :Module:       output, appendinfo




E169
---------------------------------------------------------------------------
  :Description:  The discharge map for the environmental flow has another size than the mask map
  :Where:        OUT_MAP_Daily = discharge, MaskMap
  :What to do:   Use the discharge of a run with the same mask map
  :Module:       datahandling, readDischargeFiles




E170
---------------------------------------------------------------------------
  :Description:  waterquality = True needs includeRouting = True
  :Where:        waterquality, includeRouting
  :What to do:   Set includeRouting = True or waterquality = False
  :Module:       waterquality1, initial




E171
---------------------------------------------------------------------------
  :Description:  use_GeneralCropIrr = True needs the map GeneralCrop_Irr
  :Where:        use_GeneralCropIrr, GeneralCrop_Irr
  :What to do:   Add GeneralCrop_Irr to the settings file or set use_GeneralCropIrr = False
  :Module:       evaporation, dynamic




E172
---------------------------------------------------------------------------
  :Description:  use_GeneralCropnonIrr = True needs the map GeneralCrop_nonIrr
  :Where:        use_GeneralCropnonIrr, GeneralCrop_nonIrr
  :What to do:   Add GeneralCrop_nonIrr to the settings file or set use_GeneralCropnonIrr = False
  :Module:       evaporation, dynamic




E173
---------------------------------------------------------------------------
  :Description:  PET_modus is not a valid method for the potential evaporation
  :Where:        PET_modus
  :What to do:   Use 1 (Penman-Monteith), 2 (Milly-Dunne), 3 (Penman-Monteith with CO2 correction), 4 (Priestley-Taylor) or 5 (modified Thornthwaite)
  :Module:       readmeteo, initial




E174
---------------------------------------------------------------------------
  :Description:  The CO2 file must have one CO2 value per year (not a map)
  :Where:        co2conc
  :What to do:   Use a file with the variable CO2 with only the dimension time
  :Module:       evaporationPot, dynamic_1




E175
---------------------------------------------------------------------------
  :Description:  chanBeta has to be a single number, not a map
  :Where:        chanBeta
  :What to do:   Use one value e.g. chanBeta = 0.6
  :Module:       routing_kinematic, initial




E176
---------------------------------------------------------------------------
  :Description:  snowmelt_radiation = True needs SnowMeltRad
  :Where:        snowmelt_radiation, SnowMeltRad
  :What to do:   Add SnowMeltRad (calibration factor of the radiation snow melt, about 1.0) to the settings file
  :Module:       snow, initial




E177
---------------------------------------------------------------------------
  :Description:  The variable is not in the netCDF file of a yearly map
  :Where:        irrNonPaddy_efficiency (yearly netCDF stack)
  :What to do:   Use the name of the variable in the netCDF file
  :Module:       datahandling, loadmapYearly




E178
---------------------------------------------------------------------------
  :Description:  Irrigation efficiency is not > 0 and <= 1, or fraction_IncreaseIrrigation_Nonpaddy < 1 (in cells with irrigated area)
  :Where:        irrPaddy_efficiency, irrNonPaddy_efficiency, fraction_IncreaseIrrigation_Nonpaddy
  :What to do:   Use efficiencies > 0 and <= 1 and a factor >= 1
  :Module:       irrigation, checkEfficiency




E179
---------------------------------------------------------------------------
  :Description:  A reservoir outlet cell is in a command area but not on a canal of this command area - the canal leakage would be lost
  :Where:        reservoir_command_areas, canals
  :What to do:   Put the outlet cell of the reservoir on a canal cell of its command area, or the command area number on the outlet cell
  :Module:       surface_water_abstraction, initial




E180
---------------------------------------------------------------------------
  :Description:  activate_irrigation_agents = True with monthly requests but no adminSegments map
  :Where:        activate_irrigation_agents, adminSegments
  :What to do:   Add adminSegments (the agent areas) or set activate_irrigation_agents = False
  :Module:       irrigation_agents, initial




E181
---------------------------------------------------------------------------
  :Description:  Water body output key is not possible - it has to be OUT_RES_ or OUT_RES0_ ... OUT_RES6_ with a time type (not TotalTot, TotalAvg)
  :Where:        output keys e.g. OUT_RES2_Daily
  :What to do:   Use n = 0 (all) ... 6 and Daily, MonthTot, MonthAvg, MonthEnd, AnnualTot, AnnualAvg or AnnualEnd
  :Module:       configuration, splitout




E182
---------------------------------------------------------------------------
  :Description:  WaterCycle or WaterBalance as water body output (OUT_RES...)
  :Where:        OUT_RES<n>_... = WaterCycle
  :What to do:   Use WaterCycle / WaterBalance with OUT_TSS_... (catchment of the gauges)
  :Module:       output, initial_res




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




E222
---------------------------------------------------------------------------
  :Description:  Path to the MODFLOW 6 library does not exist
  :Where:        path_mf6dll
  :What to do:   Check path_mf6dll (folder with libmf6.dll / libmf6.so)
  :Module:       groundwater_modflow transient, initial




E223
---------------------------------------------------------------------------
  :Description:  A meteo netCDF map stack cannot be opened
  :Where:        Meteo maps (e.g. PrecipitationMaps, TavgMaps)
  :What to do:   Check that the file exists and is a valid netCDF file
  :Module:       datahandling, readmeteodata




E224
---------------------------------------------------------------------------
  :Description:  A netCDF map stack with 12 monthly maps cannot be read
  :Where:        Monthly maps (e.g. lapse rate)
  :What to do:   Check that the file exists and has 12 maps
  :Module:       datahandling, readnetcdf12month




E225
---------------------------------------------------------------------------
  :Description:  Precipitation maps not found
  :Where:        PrecipitationMaps
  :What to do:   Check PrecipitationMaps and PathMeteo
  :Module:       readmeteo, initial




E226
---------------------------------------------------------------------------
  :Description:  MODFLOW simulation file mfsim.nam not found in the MODFLOW working folder
  :Where:        PathGroundwaterModflowOutput, load_modflow_from_disk
  :What to do:   Delete input_hash in <PathGroundwaterModflowOutput>/wd or set load_modflow_from_disk = False - then the MODFLOW input files are written new
  :Module:       groundwater_modflow modflow6, load_bmi




E227
---------------------------------------------------------------------------
  :Description:  MODFLOW input files listed in the name files (or binary files named with OPEN/CLOSE in a package file) are missing - MODFLOW itself would end Python
  :Where:        PathGroundwaterModflowOutput, load_modflow_from_disk
  :What to do:   Delete input_hash in <PathGroundwaterModflowOutput>/wd or set load_modflow_from_disk = False - then the MODFLOW input files are written new
  :Module:       groundwater_modflow modflow6, load_bmi




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
  :Description:  The routing library is an old version without parallel routing (kinematicPar)
  :Where:        -
  :What to do:   Use the current routing library t6 (compile it again)
  :Module:       globals, clear



E306
---------------------------------------------------------------------------
  :Description:  The routing library (t6) cannot be loaded
  :Where:        -
  :What to do:   Check that the routing library for your system (t6.dll, t6_linux.so, ...) is in the cwatm folder (compile it if needed)
  :Module:       globals, clear




E307
---------------------------------------------------------------------------
  :Description:  Settings file cannot be read: no UTF-8 encoding, a key or section is twice in the file, a line is outside a section or is not key = value
  :Where:        Settings file
  :What to do:   Correct the line given in the message
  :Module:       configuration, splitout




E308
---------------------------------------------------------------------------
  :Description:  No key PathOut (output directory) in the settings file
  :Where:        PathOut
  :What to do:   Add PathOut = <output folder> in [FILE_PATHS]
  :Module:       configuration, splitout




E309
---------------------------------------------------------------------------
  :Description:  metaNetcdf.xml has no <CWATM> element or an entry without varname
  :Where:        metaNetcdfFile
  :What to do:   Check the metadata file
  :Module:       configuration, read_metanetcdf




E310
---------------------------------------------------------------------------
  :Description:  The MODFLOW library libmf6.dll (Windows) / libmf6.so (Linux) is not found or cannot be loaded
  :Where:        path_mf6dll
  :What to do:   Check path_mf6dll: the folder needs libmf6.dll / libmf6.so of a MODFLOW 6 release
  :Module:       groundwater_modflow modflow6, load_bmi




E311
---------------------------------------------------------------------------
  :Description:  The MODFLOW library is too old for the installed xmipy (e.g. libmf6 6.2.2 has no get_value_ptr)
  :Where:        path_mf6dll
  :What to do:   Use a current libmf6 (e.g. MODFLOW 6.8.1) in path_mf6dll
  :Module:       groundwater_modflow modflow6, load_bmi




E312
---------------------------------------------------------------------------
  :Description:  MODFLOW initialize failed (error from xmipy)
  :Where:        MODFLOW input files
  :What to do:   Read the MODFLOW error message and the listing file mfsim.lst named in the message
  :Module:       groundwater_modflow modflow6, load_bmi




E313
---------------------------------------------------------------------------
  :Description:  MODFLOW stopped (e.g. a Fortran STOP for a wrong input file, exit code 2) - only the MODFLOW process ends, not Python
  :Where:        MODFLOW input files, modflow_subprocess
  :What to do:   Read the MODFLOW error message and the listing file mfsim.lst named in the message
  :Module:       groundwater_modflow modflow6_process, _receive




E314
---------------------------------------------------------------------------
  :Description:  Python error in the MODFLOW process during a time step (e.g. the solver does not converge)
  :Where:        modflow_timestep, use_complex_solver_for_modflow
  :What to do:   If the solver does not converge: use a smaller modflow_timestep or use_complex_solver_for_modflow. Read the MODFLOW error message and the listing file mfsim.lst named in the message
  :Module:       groundwater_modflow modflow6_process, _child




E315
---------------------------------------------------------------------------
  :Description:  MODFLOW did not finish a call (the start or one time step) within modflow_timeout seconds - the MODFLOW process is stopped
  :Where:        modflow_timeout
  :What to do:   If MODFLOW is only slow: use a larger modflow_timeout (0: no limit). Else check the MODFLOW input
  :Module:       groundwater_modflow modflow6_process, _receive



E400
---------------------------------------------------------------------------
  :Description:  Not an error: only the environmental flow is calculated from an existing discharge file - the run ends with exit code 400
  :Where:        calc_environflow = True, calc_ef_afterRun = False, EFDis
  :What to do:   Nothing to do
  :Module:       environflow / cwatm_dynamic, dynamic




E601
---------------------------------------------------------------------------
  :Description:  The temperature maps might be in Kelvin instead of Celsius or vice versa
  :Where:        TavgMaps, TminMaps, TmaxMaps, [OPTIONS]
  :What to do:   Check the temperature flag in [OPTIONS] (temperature in Kelvin or Celsius)
  :Module:       readmeteo, check_celsius



