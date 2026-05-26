
################
Installing CWatM
################

.. contents:: 
    :depth: 4

.. _rst_setupdoc:

	
Installing Python
=================

CWatM requires having `Python <https://www.python.org/downloads/>`_.

.. note:: CWatM is tested for Python 3.7 - 3.12. We recommend using the most recent stable release.

.. warning:: a 64-bit version is necessary. This is generally the default download.


Martin Bednář from Brno University of Technology, Czech Republic wrote the following instructions to install Python and the virtual environment:


The following text describes instructions regarding the Windows 10 operating system
(OS). However, there might be some differences in the case of different OS.
The first step is to install Python on your machine. You can find the
latest version on the official Python Website. As of October 2024, the latest version of
Python is 3.13.0. However, it is a relatively new release, thus not all packages might be
up to date. So scroll a bit down and download the second latest version, which should
be 3.12.7.


Select the particular Python version and find a 64-bit version for Windows OS and click its name.
Open the file and follow the recommended instructions. Be careful during the installation
of the option to add Python to PATH environmental variable. Figure 2 shows what
to look for during the installation. It is not the end of the world if you did not check
this checkbox and it is possible to add Python to PATH variable later. However, try to
do it now, as it will make your life way simpler when using python. After successful
installation open the Command Prompt (use i.e. WIN + R shortcut to open Run window
and write cmd and hit ENTER.). If you write python -V and hit ENTER. It should return
the Python version number you just installed.

Virtual environment setup (optional)
------------------------------------

What is virtual environment
***************************

The virtual environment enables you to run a clean “separate copy” of Python. Then
you are able to install packages into this copied Python, which do not collide with the
“main” Python installed.
For example, you install Python on your machine and then install a package named
thebestpackage. Let's say it is a new package; thus, its version would be 1.0.0. Then you
write code using this package’s functions. After some time, you will need to update
this package because for example, in version 1.2.0 the creator added a new feature
you would like to use. So you update the package. However, the new version changed
how some existing functions operated and now your former code does not work properly.
However, if you installed the first version of package in the virtual environment, the
package would remain at version 1.0.0 even if you update the package on the main
Python because the virtual environment created a separate copy od Python.
Therefore, the virtual environment is very useful in controlling the versions of
packages used for your particular piece of code and if you will need and updated version
version for different code (on main Python version or in different virtual environments)
It will remain functional. Nevertheless, the virtual environment is not necessary and
is totally optional, so if you are not interested, you can simply skip this.


How to install a virtual environment
**********************************

There are many ways to set up a virtual environment. Two ways of setup the virtual
environment will be described (The second one was presented in the CwatM Level A1
Summer School). The first one is using the venv package that is built-in the Python
since version 3.3. The usage of this package is following:

1. Create a folder for your project.
2. Open the Command Prompt inside this folder.
3. Use command: python -m venv .venv

Now, you have created a virtual environment that is named “.venv” inside your folder.
So, how does that command work? Firstly, you tell it to use Python (python) then the
flag -m tells Python to execute a module as a script and the module would be venv, which
follows. The last part is simply the name of your virtual environment. The name of
virtual environment can be whatever you like, e. g. “my_project” or you can use a
path to any folder you like if you do not want to create a virtual environment in the
destination you are currently in.
To activate the virtual environment using the venv package you need to open a Command
Prompt inside your project folder (where the virtual environment was created)
and use the following command (“.venv” is the name of your virtual environment)::

    .venv/Scripts/Activate.bat


This will start the virtual environment and you will see its name in brackets before
the next command line (Figure 5). After you activate the virtual environment, all the
packages you install will be installed specifically in this activated environment and will
not be affected by any changes in the main Python environment. To deactivate the
virtual environment, simply put in Command Prompt the deactivate command.


External libraries
------------------

These seven Python packages are needed:

1. `NumPy <http://www.numpy.org>`_
2. `SciPy <https://www.scipy.org>`_
3. `netCDF4 <https://pypi.python.org/pypi/netCDF4>`_
4. `pandas <https://pypi.org/project/pandas>`_
5. `xmipy <https://pypi.org/project/xmipy>`_
6. `openpyxl <https://pypi.org/project/openpyxl>`_
7. `rasterio <https://pypi.org/project/rasterio>`_

These seven libraries can be installed with pip, conda

8. `GDAL <http://www.gdal.org>`_

.. note::
   | **Troublemaker GDAL**
   | Installing GDAL via pip can be troublesome. We recommend downloading the library from
   | `Christoph Gohkles github page - geospatial-wheels <https://github.com/cgohlke/geospatial-wheels/releases>`_
   | as GDAL-3.9.2-cp312-cp312m-win_amd64.whl (depending on your Python version)
   | (You have to click on show all 156 assets, to see GDAL, for older versions e.g. GDAL-3.8.4-cp311-cp311-win_amd64.whl use earlier releases e.g. v2024.2.18)
   | and installing as:
   | pip install C:/Users/XXXXX/Downloads/GDAL-3.9.2-cp312-cp312m-win_amd64.whl
   |
   | Sometimes problems occur if you have installed GDAL separately (or a software did, like QGIS)
   | We tested GDAL and Numpy on ~40 computers and we could not figure out a version combination (ython, numpy, gdal)  which works all the time
   | - on some computers: Python 3.12, Numpy 2.1 and GDAL 3.9
   | - on others only pip install numpy==1.26, GDAL 3.8
  

.. note::
   | **Numpy version 2.1, 2.2**
   | the branch: develop version work now with Numpy 2.1,2.2. BUT it seems Numpy and GDAL are not good friends. 
   | On some computer we could no work with numpy 2.x
   | and we had to downscale to: pip install numpy==1.26

These additional packages are used for the post-processing Notebooks (in CWatM/Toolkit)

* `Jupyter Notebook <https://pypi.org/project/notebook/>`_
* `plotly <https://pypi.org/project/plotly/>`_
* `XlsxWriter <https://pypi.org/project/XlsxWriter/>`_

These additional package are used for CWatM-MODFLOW

* `FloPy <https://www.usgs.gov/software/flopy-python-package-creating-running-and-post-processing-modflow-based-models>`_



Installing CWatM
================

CWatM can be cloned through our `CWatM GitHub repository <https://github.com/iiasa/CWatM>`_.

For those new to GitHub, we recommend using `GitHub desktop <https://desktop.github.com/>`_.

Getting CWatM with GitHub desktop is covered in our `YouTube tutorial <https://youtu.be/9JMBwo4eESk>`_.

Input data to run CWatM at 30 arcminutes (~50 km x 50km) are available through our
`CWatM-Earth-30min GitHub repository <https://github.com/iiasa/CWatM-Earth-30min>`_.

C++ libraries
-------------

For the computational time demanding parts e.g. routing, CWatM comes with a C++ library. A pre-compiled version is included for Windows and Linux. Normally, you don't have to do anything and the pre-compiled version should just work.

**Pre-compiled C++ libraries**

| **Windows and CYGWIN_NT-6.1**
| a compiled version is provided and CWatM is detecting automatically which system is running and which compiled version is needed

| **Linux**
| For Cygwin linux a compiled version *t5cyg.so* is provided in *../cwatm/hydrological_modules/routing_reservoirs/* for version CYGWIN_NT-6.1.
| If you use another cygwin version please compile it by yourself and name it *t5_linux.so*

For Linux Ubuntu a compiled version is provided as *t5_linux.so*. The file is in *../cwatm/hydrological_modules/routing_reservoirs/* 

.. note::
    If you use another Linux version or the compiled version is not working or you have a compiler which produce faster executables please compile a version on your own.

| **Mac**
| For the new Mac M4 processor we compiled a version t5_mac.so. The old Mac should run with t5_linux.so (we are not using Mac by ourself, therefore no guaranty!)



Compiling a version
*******************

C++ sourcecode is in *../cwatm/hydrological_modules/routing_reservoirs/t5.cpp*

.. note::
    A compiled version is already provided for Windows and Linux and Apple.

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
	| the libray used with Windows is named *t5.dll*, if you generate a libray *t5.so* the filename in **../cwatm/management_modules/globals.py** has to be changed!

**Linux**

To compile with g++::

    ..\g++ -c -fPIC -Ofast t5.cpp -o t5_linux.o
    ..\g++ -shared -Ofast -Wl,-soname,t5_linux.so -o t5_linux.so  t5_linux.o
	
	or
	
	..\g++ -c -Ofast t5.cpp -o t5_linux.o
    ..\g++ -shared -Ofast -Wl,-soname,t5_linux.so -o t5_linux.so  t5_linux.o


.. warning:: Please rename your compiled version to t5_linux.so! At the moment the file t5_linux.so is compiled with Ubuntu Linux


Installing CwatM on Mac
-----------------------

We do not run Mac by ourselves, therefore this information is from Vlad Amihaesei:

Install Miniconda to run the CWATM model on a Macbook. After that, open a terminal and type conda create—n "cwatm" python=3.12.7 (you have to specify which version of Python you need to use—it took me a while to notice that). Then, type conda activate cwatm. 

Install the required libraries::

    conda install numpy 
    conda install netcdf4 
    conda install scipy
    conda install pandas
    conda install gdal==3.9.2 
    conda install openpyxl 
    conda install xmimpy


| Go to the folder of the model, open it in the terminal, then type: conda activate cwatm 
| Type: python run_cwatm.py
| You might have the error of security showing that the t5_mac.so file  is not trusted. The location of that file is: ...hydrological_modules/routing_reservoirs/t5_mac_so
| You have to go to the System Settings on the Mac:
| System Settings -> Privacy & Security -> scroll down until you see Allow applications and choose Allow the t5_mac_so


Running the model for the first time
====================================

From a terminal inside the CWatM folder, Run from the command line::

    python run_cwatm.py

The output should be::

   Running under platform:  Windows  **(or Linux etc)** 
   CWatM - Community Water Model
   Authors: ...
   Version: ...
   Date: ...
   Arguments list:
   settings.ini     settings file
   -q --quiet       output progression given as .
   -v --veryquiet   no output progression is given
   -l --loud        output progression given as time st
   -c --check       input maps and stack maps are check
   -h --noheader    .tss file have no header and start
   -t --printtime   the computation time for hydrologic
   -w --warranty    copyright and warranty information   
	
.. warning:: If python is not set in the environment path, the full path of python has to be used

.. warning:: We are using run_cwatm.py inside the main repository (CWatM\\run_cwatm.py), not one folder deeper (CWatM\\cwatm\\run_cwatm.py).

.. note:: Possible errors are adressed in:  :ref:`rst_errors` 


Run with a settingsfile
-----------------------

Run from the command line::

    python run_cwatm.py settingsfile flags
    

example (from inside the CWatM folder)::

   python run_cwatm.py settings.ini

or with more information and an overview of computational runtime::

   python run_cwatm.py settings.ini -l -t
	
.. warning:: If python is not set in the environment path, the full path of python has to be used

.. warning:: The model needs a settings file as an argument. See: :ref:`rst_settingdoc` 


.. note:: it is also possible to use paths with white spaces or dots. An easy way to avoid this is using relative paths, but is is also possible with absolute paths.

::

    "C:/Python 37/python" "C:/CWatM Hydrologic.modeling/CWatM/run_cwatm.py" "C:/CWatM Hydrologic.modeling/settings .rhine30min.ini" -l
    
    But in the settingsfile do not use apostrophe "" or '':
    PathRoot = C:/CWatM Hydrologic.modeling
   


Using Flags
===========

Flags can be used to change the runtime output on the screen

example::

    -q --quiet       output progression given as .
    -v --veryquiet   no output progression is given
    -l --loud        output progression given as time step, date and discharge
    -c --check       input maps and stack maps are checked, output for each input map BUT no model run
    -h --noheader    .tss file have no header and start immediately with the time series
    -t --printtime   the computation time for hydrological modules are printed
	-w --warranty    copyright and warranty information
