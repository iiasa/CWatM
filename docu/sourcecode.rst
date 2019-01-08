
###########
Source code
###########

.. contents:: 
    :depth: 4

Source code on Github
=====================

| The source code of CWATM is freely available under the GNU General Public License. 
| Please see its :ref:`rst_terms`

   `Source code on Github repository of CWATM <https://github.com/CWatM/CWatM>`_

| Please use the actual Python 3.7 version
| From 2019 we are not maintaining the Python 2.7 version
| In case of trouble, try the executable version cwatmexe.zip

.. warning:: The source code is free, but we can give only limited support, due to limited person power!


Source code
===========

    ::

        --------------------------------------------------
        ######## ##          ##  ####  ######  ##    ##
        ##       ##          ## ##  ##   ##   ####  ####
        ##        ##        ##  ##  ##   ##   ## #### ##
        ##        ##   ##   ## ########  ##  ##   ##   ##
        ##         ## #### ##  ##    ##  ##  ##        ##
        ##         ####  #### ##      ## ## ##          ##
        ##########  ##    ##  ##      ## ## ##          ##
        
        Community WATer Model
        --------------------------------------------------

Modules of CWATM
----------------

The source code of CWATM has a modular structure. Modules for data handling, output, reading as parsing the setting files
are in the **management_modules** folder.

Modules for hydrological processes e.g. snow, soil, groundwater etc. are located in the folder **hydrological_modules**. The kinematic routing
and the C++ routines (for speeding up the computational time) are in the folder **hydrological_modules/routing_reservoirs**.

Fig 1 show a profile with of the workflow of CWATM.

.. image:: _static/callgraph.png
    :width: 900px

Figure 1: Graphical profile of CWATM run for Rhine catchment from 1/1/190-31/12/2010

.. note::
   | Figure created with:
   | python -m cProfile -o  l1.pstats cwatm3.py settings1.ini -l   
   | gprof2dot -f pstats l1.pstats | dot -T png -o callgraph.png

Source code description
-----------------------

.. toctree::
   :maxdepth: 4

   cwatm3
   cwatm_dynamic
   cwatm_initial
   hydrological_modules
   management_modules

Download Manual as pdf
======================

:download:`CWATM_MANUAL.pdf<_static/CWATM.pdf>`


Global dataset
==============

| If you are interested in obtaining the gloabl data set,
| please send an email to wfas.info@iiasa.ac.at
| We will give you access to our ftp server


Contact CWATM
=============

| `www.iiasa.ac.at/cwatm <http://www.iiasa.ac.at/cwatm>`_ 
| wfas.info@iiasa.ac.at

Remarks
=======

We as developers belief that CWATM should be utilize to encourage ideas and to advance hydrological, environmental science and stimulate integration into other science disciplines.

CWATM is based on existing knowledge of hydrology realized with Python and C++. Especially ideas from HBV, PCR-GLOBE, LISFLOOD, H08, MatSiro, WaterGAP are used for inspiration.

**Your support is more then welcome and highly appreciated**
**Have fun!**

The developers of CWAT Model
