
###################
Recover former runs
###################

.. contents:: 
    :depth: 3

.. _rst_recover:

recover or reproduce former runs
================================


Model results can be reproduced given the same input data, the same model version, and the same environment settings.

Information about the run
-------------------------


We put information about the run in every output.csv file.

For example:

.. note:: 
    settingsfile: c:\\Morava\settings\settings_morava.ini,Runnning date: Fri Oct  3 12:33:41 2025,CWATM: C:\cwatm\run_cwatm.py Git-Branch:develop Hash:5e5c4557926a84c21f93bbfcf9304dee37f83651

and in each output netcdf as global attributes:

- Path and name of the settingsfile
- Date of creation
- Path to the CWatM programm
- git commit hash

More information
----------------

In discharge and potential evaporation netCDF output we put additional information to recover and reproduce a run:

- The complete settingsfile in: version_settingsfile
- The Python version and all libraries with version number: version_modules
- The data used (location of the data is store in the settingsfile). But this gives information about the creation date

.. note:: 
    | for example: 
    | morava.map 17/02/2025 08:47
    | ldd.nc 13/02/2025 17:34
    | cellarea.nc 23/02/2024 14:26
    | pr_EMO-1_1990_2022.nc 08/03/2024 10:51
	
How to recover
--------------

| we put a Python script in:
| Toolkit\git_commits_versioning\Toolkit\git_commits_versioning

to rebuild the settingsfile and list the information of the Python and data version  
