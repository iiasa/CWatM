Calibration tool for hydrological models using a distributed evolutionary algorithm in Python

How does it work?
============

The calibration tool builds a single-objective optimization framework using the Python library DEAP.

DEAP library: https://github.com/DEAP/deap/blob/master/README.md
To install DEAP on Python 3.10+: 
https://github.com/DEAP/deap/issues/610#issuecomment-1082102147

For each run, it triggers a run of the hydrological model:
- using a template of the settings file
- replacing the output folder in this template file
- replace placeholder calibration parameters with values. The range of the parameter values is given in ParamRanges.csv.

After each run, the model run is compared to observed values (e.g., observed_data/lobith2006.csv)

What is needed?
==============

1) The template files in the folder [templates_CWatM] must be adjusted.
1.1) runpy.bat: the path to cwatm.py have to be set correctly (for Linux, a .sh file has to be created)
1.2) The actual version of a cwatm settings file has to be modified:
   - replacing the output folder with the placeholder: %run_rand_id
   - replacing calibration parameter values with a placeholder: e.g., %SnowMelt

2) The range of parameter space has to be defined in ParamRanges.csv.

3) The observed discharge has to be provided in a .cvs file, e.g., observed_data/lobith2006.csv
3.1) In the template settings, the date has to be set so that the period of observed discharge is between SpinUp and StepEnd

4) A few options in the settings_calibration.txt have to be adjusted (how many runs? a first run with standard parameters? etc.)

5) Run the calibration by double-clicking the batch file: 1. run_calibration
If the calibration stops in the middle, simply run the batch file again to start from where it left off.
Before starting a new calibration, delete all folders inside runs_calibration.

The following programs generate figures in the folder [figures]
6.1) For analysis of the calibration, double-click the batch file: 2. run_plot_calibration
6.2) For analysis of the calibration parameters, double-click the batch file: 3. run_violin_plots


Recommendations
===============

1. Run the model first to store the pot. evaporation results
   Afterwards, use the stored evaporation to run the calibration
   calc_evaporation = False
   
2. Run the model and store the last day to be used as the initial condition for the calibration runs
   The best is to use a long-term run for this.
   load_initial = False
   save_initial = True
   During calibration use:
   load_initial = True
   save_initial = False
   
3. Use a long SpinUp time (> 5 years to give groundwater enough time)


Reference: 
Félix-Antoine Fortin, François-Michel De Rainville, Marc-André Gardner, Marc Parizeau and Christian Gagné, "DEAP: Evolutionary Algorithms Made Easy", Journal of Machine Learning Research, vol. 13, pp. 2171-2175, Jul 2012

The calibration tool was created by Hylke Beck 2014 (JRC, Princeton) hylkeb@princeton.edu
Thanks, Hylke, for making it available for use and modification.
The IIASA Water Security research group has modified it.

The submodule Hydrostats was created in 2011 by:
Sat Kumar Tomer (modified by Hylke Beck): Book "Python in Hydrology", http://greenteapress.com/pythonhydro/pythonhydro.pdf.
