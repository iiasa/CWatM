
#######################
Running the model
#######################

.. contents:: 
    :depth: 3

Start the model
===============

.. warning:: The model needs a settings file as an argument. See: :ref:`rst_settingdoc` 

**Windows**

python <modelpath>/cwatm.py settingsfile flags

example::

   python cwatm.py settings1.ini
   or with more information and an overview of computational runtime
   python cwatm.py settings1.ini -l -t
	
.. warning:: If python is not set in the environment path, the full path of python has to be used


**Linux**

<modelpath>/cwatm.py settingsfile flags

example::

    cwatm.py settings1.ini -l -t
	
Flags
*****

Flags can be used to change the runtime output on the screen

example::

    -q --quiet       output progression given as .
    -v --veryquiet   no output progression is given
    -l --loud        output progression given as time step, date and discharge
    -c --check       input maps and stack maps are checked, output for each input map BUT no model run
    -h --noheader    .tss file have no header and start immediately with the time series
    -t --printtime   the computation time for hydrological modules are printed
	-w --warranty    copyright and warranty information

	

Settings file
*************
	
The setup of the setings file is shown in the next chapter.
	
See: :ref:`rst_settingdoc` 

	
NetCDF meta data 
****************

The format for spatial data for output data is netCDF.
In the meta data file information can be added  e.g. a description of the parameter

See: :ref:`rst_metadata`

.. note:: It is not necessary to change this file! This is an option to put additional information into output maps



