# Community Water Model (CWatM)

[![latest](https://img.shields.io/github/last-commit/iiasa/CWatM)](https://github.com/iiasa/CWatM)
[![license](https://img.shields.io/github/license/iiasa/CWatM?color=1)](https://github.com/iiasa/CWatM/blob/version1.05/LICENSE)
[![pytest-37](https://github.com/IAMconsortium/pyam/workflows/pytest%20(3.7)/badge.svg?branch=master)](https://github.com/iiasa/CWatM)
[![pytest-38](https://github.com/IAMconsortium/pyam/workflows/pytest%20(3.8)/badge.svg?branch=master)](https://github.com/iiasa/CWatM)
[![codecov](https://codecov.io/gh/iiasa/CWATM_priv/branch/develop/graph/badge.svg?token=6HENTZM7SC)](https://codecov.io/gh/iiasa/CWATM_priv)
[![size](https://img.shields.io/github/repo-size/iiasa/CWatM)](https://github.com/iiasa/CWatM)
[![ReadTheDocs](https://readthedocs.org/projects/pyam-iamc/badge/?version=latest)](https://cwatm.iiasa.ac.at/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3528097.svg)](https://doi.org/10.5281/zenodo.3528097)


**Documentation on [https://cwatm.iiasa.ac.at](https://cwatm.iiasa.ac.at)**

**Questions? Start a discussion on our [forum](https://github.com/iiasa/CWatM/discussions)**


## Overview and scope

CWatM represents one of the new key elements of IIASA's Water program to assess water supply, water demand and environmental needs at global and regional level. The hydrologic model is open source and flexible to link in different aspects of the water energy food nexus. CWATM will be a basis to develop a next-generation global hydro-economic modeling and will be coupled to the existing IIASA models like MESSAGE and GLOBIOM

http://www.iiasa.ac.at/cwatm


<p align="center">
  <img src="docu/_static/CWatM_logo.png" width="200" title="CWatM">
</p>


## Model design and processes included

The Community Water Model (CWatM) will be designed for the purpose to assess water availability, water demand and environmental needs. It includes an accounting of how future water demands will evolve in response to socioeconomic change and how water availability will change in response to climate.

<p align="center">
  <img src="docu/_static/Hydrological-model2.jpg" width="450" title="Schematic view of processes">
</p>
Figure 1: Schematic view of CWatM processes

Modules for hydrological processes e.g. snow, soil, groundwater etc. are located in the folder hydrological_modules.
The kinematic routing and the C++ routines (for speeding up the computational time) are in the folder hydrological_modules/routing_reservoirs.

<p align="center">
  <img src="docu/_static/schematic_modules.jpg" width="650" title="Schematic modules">
</p>
Figure 2: Schematic graph of CWatM modules

## Next-generation global hydro-economic modeling framework

The Community Water Model will help to develop a next-generation hydro-economic modeling tool that represents the economic trade-offs among water supply technologies and demands.  The tool will track water use from all sectors and will identify the least-cost solutions for meeting future water demands under policy constraints.  In addition, the tool will track the energy requirements associated with the water supply system (e.g., desalination and water conveyance) to facilitate the linkage with the energy-economic tool. The tool will also incorporate environmental flow requirements to ensure sufficient water for environmental needs.

## The Nexus framework of IIASA

In the nexus framework â€“ water, energy, food, ecosystem - CWatM will be coupled to the existing IIASA models including the Integrated Assessment Model MESSAGE and the global land and ecosystem model GLOBIOM in order to realize an improved assessments of water-energy-food-ecosystem nexus and associated feedback.

<p align="center">
  <img src="docu/_static/nexus.jpg" width="350" title="IIASA nexus">
</p>
Figure 3: IIASA model nexus


## Short to medium vision

Our vision for the short to medium term work is to introduce water quality (e.g., salinization in deltas and eutrophication associated with mega cities) into CWatM and to consider qualitative and quantitative measures of transboundary river and groundwater governance into an integrated modelling framework.

## Contact CWatM

http://www.iiasa.ac.at/cwatm 

wfas.info@iiasa.ac.at

Our vision for the short to medium term work is to introduce water quality (e.g., salinization in deltas and eutrophication associated with mega cities) into CWatM and to consider qualitative and quantitative measures of transboundary river and groundwater governance into an integrated modelling framework.


## Link to full model documentation

https://cwatm.github.io/

