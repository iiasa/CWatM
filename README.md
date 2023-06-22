# Community Water Model (CWatM)

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
