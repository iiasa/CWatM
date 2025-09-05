# CWatM+pySnowClim

Integration of the Community Water Model (CWatM) with pySnowClim model to enhance the simulation of hydrological processes. A more accurate representation of water resources, accounting for the critical role of snow in the hydrological cycle.

## Getting started

### Clone the repository to your local machine
```
git clone <repository-url>

# Navigate to the project directory
cd <repository-name>
```


## Usage
There are 2 components of this project. The CWatM model and the pySnowClim model.
To run CWatM one needs to specify the `.ini` file. For instance:
```
python run_cwatm.py settings_myrun.ini
```
The file `example_settings_Thompson_5min_ERA5-land.ini`
has an example of how to use the coupled models. More information anout how to run CWatM can be found inside the [CWatM repo](https://github.com/iiasa/CWatM) and in the original CWatM readme.md which can be found bellow.

pySnowclim forcings are:
* lrad - downward longwave radiation (kJ/m2/hr *time step) (time x space)
* tavg - average air temperature (C) (time x space)
* ppt - precipitation (m) (time x space)
* solar - downward shortwave radiation (kJ/m2/hr *time step) (time x space)
* tdmean  - dewpoint temperature (C) (time x space)
* vs - windspeed (m/s) (time x space)
* relhum - relative humidity (%) (time x space)
* psfc - air pressure (hPa or mb) (time x space)
* huss - specific humidity (kg/kg) (time x space)

CWatM forcings are similar to the ones used by pySnowClim.
However the units are different and an internal conversion is made before the model is called.
The only missing forcing is `tdmean` which is used only by pySnowClim and must be added in `TdewMaps` in `K`.

To run CWatM using pySnowClim snow model one only needs to add the necessary parameters inside the `.ini` file. For example:

```
#-------------------------------------------------------
[__pySNOWCLIM]
#-------------------------------------------------------
usepySnowClim = True

TdewMaps = $(FILE_PATHS:PathMeteo)/tdps_day_1950-2021_remapped_K*

stability = 1
windHt = 10
tempHt = 2
snowoff_month = 9
snowoff_day = 1
albedo_option = 3
max_albedo = 0.85
z_0 = 0.00001
z_h = 0.000001
lw_max = 0.1
Tstart = 0
Tadd = -10000
maxtax = 0.9
E0_value = 1
E0_app = 1
E0_stable = 2
Ts_add = 2
smooth_time_steps = 1
ground_albedo = 0.25
snow_emis = 0.98
snow_dens_default = 250
G = 0.0020023148148148147
max_swe_height = 10
downward_radiation_factor =1.3
downward_radiation_start_month = 1
downward_radiation_end_month = 12
```
The `usepySnowClim` option is the one which defines if CWatM will run with pySnowClim or not. If `usepySnowClim = False` then the code will **IGNORE** pySnowClim and run the original CWatM snow component with the correction of albedo (originally albedo was missing from the snow component).

The `TdewMaps` variable defines where the dew point temperature dataset is located. Please note that `TdewMaps` is only needed when `usepySnowClim = True` as pySnowClim needs dewpoint temperature to run.

Finally the other parameters `[stability, windHt, ... ,  snow_dens_default, G]` are the parameters needed by the original snowclim model. More information
about the parameters can be found in [Lute et al. (2022)](https://doi.org/10.5194/gmd-15-5045-2022).


Some new parameters defined inside the ini file (`max_swe_height`, `downward_radiation_factor`, `downward_radiation_start_month`, `downward_radiation_end_month`) were implemented to avoid the snow tower problem.

- `max_swe_height`: Max height of SWE before downward radiation factor starts to work (default: 100 m)
- `downward_radiation_factor`: Factor to be multiplied by downward radiation when SWE > max_swe_height (default: 1.3)
- `downward_radiation_start_month`: Month where downward_radiation_factor start to be applied (default: 6)
- `downward_radiation_end_month`: Month where downward_radiation_factor ends (default: 10)


***

# README of Community Water Model (CWatM)

[![latest](https://img.shields.io/github/last-commit/iiasa/CWatM)](https://github.com/iiasa/CWatM)
[![license](https://img.shields.io/github/license/iiasa/CWatM?color=1)](https://github.com/iiasa/CWatM/blob/version1.05/LICENSE)
[![python](https://img.shields.io/badge/python-3.7_|_3.8_|_3.9_|_3.10|_3.11-blue?logo=python&logoColor=white)](https://github.com/iiasa/CWatM)
[![pytest](https://github.com/IAMconsortium/pyam/actions/workflows/pytest.yml/badge.svg)](https://github.com/iiasa/CWatM)
[![codecov](https://codecov.io/gh/iiasa/CWATM_priv/branch/develop/graph/badge.svg?token=6HENTZM7SC)](https://codecov.io/gh/iiasa/CWATM_priv)
[![size](https://img.shields.io/github/repo-size/iiasa/CWatM)](https://github.com/iiasa/CWatM)
[![ReadTheDocs](https://readthedocs.org/projects/pyam-iamc/badge/?version=latest)](https://cwatm.iiasa.ac.at/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3528097.svg)](https://doi.org/10.5281/zenodo.3528097)


User manual and model documentation at [https://cwatm.iiasa.ac.at](https://cwatm.iiasa.ac.at).

Questions? Start a discussion on our [GitHub forum](https://github.com/iiasa/CWatM/discussions) and
check out our [CWatM tutorials on YouTube](https://www.youtube.com/playlist?list=PLyT8dd_rWLaymQIewMyzVcjMYvPR8Rqtw).

Our repository [CWatM-Earth-30min](https://github.com/iiasa/CWatM-Earth-30min) contains input data for CWatM at 30 arcminutes and further links to climate and higher resolution input data.


## Overview and scope

Community Water Model (CWatM) is a hydrological model simulating the water cycle daily at global and local levels, historically and into the future, maintained by IIASA’s Water Security group. CWatM assesses water supply, demand, and environmental needs, including water management and human influence within the water cycle. CWatM includes an accounting of how future water demands will evolve in response to socioeconomic change and how water availability will change in response to climate and management.

CWatM is open source, and its modular structure facilitates integration with other models. CWatM will be a basis to develop next-generation global hydro-economic modelling coupled with existing IIASA models like MESSAGE and GLOBIOM.

<p align="center">
  <img src="Toolkit/documentation/_static/CWatM_logo.png" width="200" title="CWatM">
</p>


## Model design and processes included

Modules for hydrological processes, e.g. snow, soil, groundwater, lakes & reservoirs, evaporation, etc., are in the folder hydrological_modules. The kinematic routing and the C++ routines (for speeding up the computational time) are in the folder hydrological_modules/routing_reservoirs.


<p align="center">
  <img src="Toolkit/documentation/_static/Hydrological-model2.jpg" width="450" title="Schematic view of processes">
</p>
Figure 1: Schematic view of CWatM processes

## Next-generation global hydro-economic modelling framework

CWatM will help to develop a next-generation hydro-economic modelling tool that represents the economic trade-offs among water supply technologies and demands.  The tool will track water use from all sectors and identify the least-cost solutions for meeting future water demands under policy constraints.  In addition, the tool will track the energy requirements associated with the water supply system (e.g., desalination and water conveyance) to facilitate linking with the energy-economic tool. The tool will also incorporate environmental flow requirements to ensure sufficient water for environmental needs.

## The Nexus framework of IIASA

In the nexus framework of water, energy, food, and ecosystem, CWatM will be coupled to the existing IIASA models, including the Integrated Assessment Model MESSAGE and the global land and ecosystem model GLOBIOM to realize improved assessments of water-energy-food-ecosystem nexus and associated feedback.

<p align="center">
  <img src="Toolkit/documentation/_static/nexus.jpg" width="350" title="IIASA nexus">
</p>
Figure 2: IIASA model nexus


## Short to medium-term vision

Our vision for short to medium-term work is to refine the human influence within the water cycle, integrate biodiversity, introduce water quality (e.g., salinization in deltas and eutrophication associated with megacities), and consider qualitative and quantitative measures of transboundary river and groundwater governance into an integrated modelling framework.
