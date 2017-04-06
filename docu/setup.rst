
#######################
Setup of the model
#######################

.. contents:: 
    :depth: 3

Requirements
============

Python version
**************

Requirements are a 64 bit `Python 2.7.x version <https://www.python.org/downloads/release/python-2712/>`_

.. warning:: a 32 bit version is not able to handle the data requirements!

Libraries
*********

Two external libraries are needed:

* `Numpy <http://www.numpy.org>`_
* `netCDF4 <https://pypi.python.org/pypi/netCDF4>`_

**Windows**

Both libraries can be installed with pip or
downloaded at `Unofficial Windows Binaries for Python Extension Packages <http://www.lfd.uci.edu/~gohlke/pythonlibs>`_


PCRaster
******** 

And the PCRASTER library from Faculty of Geosciences, Utrecht University, The Netherlands - `Webpage of PCRaster <http://pcraster.geo.uu.nl>`_

| Reference:
| Karssenberg, D., Schmitz, O., Salamon, P., de Jong, K., and Bierkens, M. F. P.: A software framework for construction of process-based stochastic spatio-temporal models and data assimilation, Environmental Modelling & Software 25(4), 489-502, 2010. doi: 10.1016/j.envsoft.2009.10.004


PCRaster installation
=====================

| CWATM is using the PCRaster Python framwork of PCRaster but not the GIS commands.
| But nevertheless it is quite usefull to install a full PCRaster version:

| **Windows**
| `Windows installation guide of PCRaster <http://pcraster.geo.uu.nl/quick-start-guide/>`_

| **Linux**
| `Linux installation guide of PCRaster <http://pcraster.geo.uu.nl/getting-started/pcraster-on-linux/>`_

.. note:: If it is not possible to install a full version of PCRaster! 
    Copy following files

::

    From: PCRasterFolder\python\pcraster\framework
    
    dynamicBase.py
    dynamicFramework.py
    dynamicPCRasterBase.py
    frameworkBase.py
    shellscript.py
    
    To: CWATM/source/pcraster2	


C++ libraries
===============

For the computational time demanding parts e.g. routing,
CWATM comes with a C++ library

Compiled versions
*****************

| **Windows and CYGWIN_NT-6.1**
| a compiled version is provided and CWATM is detecting automatically which system is running and which compiled version is needed

| **Linux**
| For Cygwin linux a compiled version *t5cyg.so* is provided in *../source/hydrological_modules/routing_reservoirs/* for version CYGWIN_NT-6.1.
| If you use another cygwin version please compile it by yourself and name it *t5_linux.so*

For Linux Ubuntu a compiled version is provided as *t5_linux.so*. The file is in *../source/hydrological_modules/routing_reservoirs/* 

.. note::
    If you use another Linux version or the compiled version is not working or you have a compiler which produce faster executables please compile a version on your own.


Compiling a version
*******************

C++ sourcecode is in *../source/hydrological_modules/routing_reservoirs/t5.cpp*

**Windows**

A compiled version is provided, but maybe you have a faster compiler than the "Minimalist GNU for Windows" or "Microsoft Visual Studio 14.0" we used.

To compile with g++::

    ..\g++ -c -fPIC -Ofast t5.cpp -o t5.o
    ..\g++ -shared -Ofast -Wl,-soname,t5.so -o t5.so  t5.o
	
To compile with Microsoft Visual Studio 14.0::
 
    call "C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\bin\amd64/vcvars64.bat"
    cl /LD /O2 t5.cpp

.. note::

    We used Visual Studio, because it seems to be computational faster
	| the libray used with Windows is named *t5.dll*, if you generate a libray *t5.so* the filename in **../source/management_modules/globals.py** has to be changed!

**Linux**

To compile with g++::

    ..\g++ -c -fPIC -Ofast t5.cpp -o t5_linux.o
    ..\g++ -shared -Ofast -Wl,-soname,t5_linux.so -o t5_linux.so  t5_linux.o
	
	or
	
	..\g++ -c -Ofast t5.cpp -o t5_linux.o
    ..\g++ -shared -Ofast -Wl,-soname,t5_linux.so -o t5_linux.so  t5_linux.o


.. warning:: Please rename your compiled version to t5_linux.so! At the moment the file t5_linux.so is compiled with Ubuntu Linux


Test the model
===============

**Windows and Linux**

python <modelpath>/cwatm.py 


The output should be::

   Running under platform:  Windows  **(or Linux etc)** 
   CWatM - Community Water Model
   Authors: ...
   Version: ...
   Date: ...
   
	
.. warning:: If python is not set in the environment path, the full path of python has to be used
	
