
####################################
Calibration tool
####################################


| Calibration tool for hydrological models
| in ../CWatM/calibration


| using a distributed evolutionary algorithms in python: DEAP library
| http://deap.readthedocs.io/en/master/
| https://github.com/DEAP/deap/blob/master/README.md

Félix-Antoine Fortin, François-Michel De Rainville, Marc-André Gardner, Marc Parizeau and Christian Gagné, "DEAP: Evolutionary Algorithms Made Easy", Journal of Machine Learning Research, vol. 13, pp. 2171-2175

| The calibration tool was created by Hylke Beck 2014 (JRC, Princeton) hylkeb@princeton.edu
| Thanks Hylke for making it available for use and modification
| Modified by Peter Burek

| The submodule Hydrostats was created 2011 by:
| Sat Kumar Tomer (modified by Hylke Beck)
| Please see his book `Python in Hydrology <http://greenteapress.com/pythonhydro/pythonhydro.pdf>`_ 

Calibration method
==================

Calibration is using an evolutionary computation framework in Python called DEAP (Fortin et al., 2012). We used the implemented evolutionary algorithm NSGA-II (Deb et al., 2002) for single objective optimization.
As objective function we used the modified version of the Kling-Gupta Efficiency (Kling et al., 2012), 2012), with r as the correlation coefficient between simulated and observed discharge (dimensionless), β as the bias ratio (dimensionless) and γ as the variability ratio. 

| :math:`KGE' = 1-\sqrt{(r-1)^2) + (\beta -1)^2 + (\gamma-1)^2 }`
| where: :math:`\beta = \frac{\mu_s}{\mu_o}`   and    :math:`\gamma = \frac{CV_s}{CV_o} =  \frac{\sigma_s/\mu_s}{\sigma_o/\mu_o}`
   
Where CV is the coefficient of variation, μ is the mean streamflow [m3 s−1] and σ is the standard deviation of the streamflow [m3 s−1]. KGE’, r, β and γ have their optimum at unity. The KGE’ measures the Euclidean distance from the ideal point (unity) of the Pareto front and is therefore able to provide an optimal solution which is simultaneously good for bias, flow variability, and correlation. For a discussion of the KGE objective function and its advantages over the often used Nash–Sutcliffe Efficiency (NSE) or the related mean squared error see (Gupta et al., 2009).
The calibration uses general a population size (µ) of 256, a recombination pool size (λ) of 32.The number of generations was set to 30, which we found was sufficient to achieve convergence for stations


Further ideas for calibration
-----------------------------

- Regionalization see (Samaniego et al. 2017) and (Beck et al. 2016)
- Using Budyko see (Greve et al. 2016)


Suggested Calibration parameters
================================

| **Snow**
| 1.	Snowmelt coefficient in [m/C deg/day]  as a degree-day factor
| **Evapotranspiration**
| 2.	Crop factor as an adjustment to crop evapotranspiration
| **Soil**
| 3.	Soil depth factor: a factor for the overall soil depth of soil layer 1 and 2
| 4.	Preferential bypass flow: empirical shape parameter of the preferential flow relation
| 5.	Infiltration capacity parameter: empirical shape parameter b of the ARNO model
| **Groundwater**
| 6.	Interflow factor: factor to  adjust the amount which percolates from interflow to groundwater
| 7.	Recession coefficient factor: factor to adjust the base flow recession constant (the contribution from groundwater to baseflow)
| **Routing**
| 8.	Runoff concentration factor: a factor for the concentration time of run-off in each grid-cell
| 9.	Channel Manning's n factor: a factor roughness in channel routing 
| 10.	Channel, lake and river evaporation factor: factor to adjust open water evaporation
| **Reservoir & lakes**
| 11.	Normal storage limit: the fraction of storage capacity used as normal storage limit
| 12.	Lake A factor : factor to channel width and weir coefficient as a part of the Poleni weir equation


Calibration tool structure
==========================

.. code-block:: rest

   calibration
   │-  readme.txt
   │-  readme.txt
   │
   └--observed_data
   │   └- lobith2006.cvs, ...
   │
   └--templates
   │   └-- runpy.bat, runpy.sh
   │   └-- settings.ini
   

How it works
============

The calibration tool builds up a single-objective obtimization framework using the Python libray DEAP
For each run it triggers the run of the hydrological model:

- using a template of the settings file
- replacing the output folder in this template file
- replace placeholders with the values of calibration parameters, the limit of the parameter range is given in the file: ParamRanges.csv

After each run the model run is compared to observed values (e.g. observed_data/lobith2006.csv)

After the calibration, statistics and the best run is printed output


What is needed
==============

| **1.** The template files in ../templates have to be adjusted

- runpy.bat: the path to cwatm.py have to be set correctly (for linux a .sh file has to be created)
- The actual version of a cwatm settings file has to modified:
- replacing the output folder with the placeholder: %run_rand_id

.. literalinclude:: _static/settingsCalTemplate.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 28-37

- putting the output variables in e.g. OUT_TSS_Daily = discharge or monthly average discharge OUT_TSS_MonthAvg = discharge

.. literalinclude:: _static/settingsCalTemplate.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 38-39

- delete all the output variables in the template (mostly at the end of the file)

- replacing calibration parameter values with a placeholder: e.g. %SnowMelt

.. literalinclude:: _static/settingsCalTemplate.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 42-64


| **2.** the range of parameter space has to be defined in ParamRanges.csv

.. literalinclude:: _static/ParamRanges.csv



| **3.** The observed discharge has to be provided in an .cvs file e.g. observed_data/lobith2006.csv

| In the template settings the date has to be set, so that the period of observed discharge is between SpinUp and StepEnd

.. literalinclude:: _static/settingsCalTemplate.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 1-12


| **4.** And empty ../catchments directory needs to be created

| **5.** A few option in the settings.txt have to be adjusted (how many runs?, a first run with standard parameters? etc)

.. literalinclude:: _static/settings.txt
   

| **6.** run python calibration_single.py settings.txt


Recommendations
===============

| **1.** Run the model first to store the pot. evaporation results

| Afterwards use the stored evaporation to run the calibration
| calc_evaporation = False
   
| **2.** Run the model and store the last day to be used as initial condition for the calibration runs

| Best is to use a long term run for this.


.. literalinclude:: _static/settings1.ini
    :linenos:
    :lineno-match:
    :language: ini
    :lines: 146-158

| load_initial = False
| save_initial = True
   
|  During calibration use:
|  load_initial = True
|  save_initial = False
   
| **3.** Use a long SpinUp time (> 5 years to give groundwater enough time)


References
==========

- Beck, H. E., A. I. J. M. van Dijk, A. de Roo, D. G. Miralles, T. R. McVicar, J. Schellekens and L. A. Bruijnzeel (2016). "Global-scale regionalization of hydrologic model parameters." Water Resources Research 52(5): 3599-3622.
- Deb, K., A. Pratap, S. Agarwal and T. Meyarivan (2002). "A fast and elitist multiobjective genetic algorithm: NSGA-II." IEEE Transactions on Evolutionary Computation 6(2): 182-197.
- Fortin, F. A., F. M. De Rainville, M. A. Gardner, M. Parizeau and C. Gagńe (2012). "DEAP: Evolutionary algorithms made easy." Journal of Machine Learning Research 13: 2171-2175.
- Greve, P., L. Gudmundsson, B. Orlowsky and S. I. Seneviratne (2016). "A two-parameter Budyko function to represent conditions under which evapotranspiration exceeds precipitation." Hydrology and Earth System Sciences 20(6): 2195-2205.
- Gupta, H. V., H. Kling, K. K. Yilmaz and G. F. Martinez (2009). "Decomposition of the mean squared error and NSE performance criteria: Implications for improving hydrological modelling." Journal of Hydrology 377(1-2): 80-91.
- Kling, H., M. Fuchs and M. Paulin (2012). "Runoff conditions in the upper Danube basin under an ensemble of climate change scenarios." Journal of Hydrology 424-425: 264-277.
- Samaniego, L., R. Kumar, S. Thober, O. Rakovec, M. Zink, N. Wanders, S. Eisner, H. Müller Schmied, E. Sutanudjaja, K. Warrach-Sagi and S. Attinger (2017). "Toward seamless hydrologic predictions across spatial scales." Hydrology and Earth System Sciences 21(9): 4323-4346.


