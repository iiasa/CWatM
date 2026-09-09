######################
**13. CWatM Glossary**
######################



.. glossary::
   :sorted:

A
=

**Actual Evapotranspiration**
   The real amount of water transferred from land to atmosphere through evaporation from soil and water surfaces plus transpiration from plants. Distinguished from potential evapotranspiration by accounting for water availability limitations.

**ARNO Model**
   A rainfall-runoff model used in CWatM for calculating infiltration capacity. The saturated fraction of a grid cell that contributes to surface runoff is related to the overall soil moisture through a nonlinear distribution function.

**ARNO Beta Parameter**
   Empirical shape parameter of the ARNO model for infiltration capacity. Calibration range: 0.01-1.0.

**Aquifer**
   Underground layer of water-bearing permeable rock or sediment from which groundwater can be extracted. In CWatM, represented in the groundwater storage component.

B
=

**Bankfull Discharge**
   The flow rate at which water begins to overflow the channel banks onto the floodplain. Used in channel geometry calculations.

**Base Flow**
   The portion of streamflow that comes from groundwater discharge rather than direct surface runoff. Calculated using: Qbase = Storage / (Tbase × Rcoeff), where Tbase is groundwater reservoir constant.

**Baseflow Recession Coefficient**
   Factor controlling the rate at which groundwater discharges to streams during dry periods. Calibration range: 0.1-10.0.

**Budyko Framework**
   A conceptual framework used for calibrating hydrological models, relating the long-term water and energy balance.

**Bulk Density**
   Mass of dry soil per unit volume (kg/m³). Used in pedotransfer functions to derive soil hydraulic parameters.

C
=

**Calibration**
   Process of adjusting model parameters to improve agreement between simulated and observed data. CWatM uses DEAP (Distributed Evolutionary Algorithms in Python) for automated calibration.

**Capillary Rise**
   Upward movement of water from groundwater to soil layers through capillary action. In CWatM, occurs when groundwater level is within 0-5m of the surface.

**Carrying Capacity (K)**
   In population models coupled with water resources, the maximum population that can be sustained by available water resources.

**CF 1.6 Convention**
   Climate and Forecast metadata convention for NetCDF files, ensuring standardized variable names, units, and metadata structure.

**Channel Geometry**
   Physical dimensions of river channels including width, depth, slope, and length. Derived using regression functions with discharge or upstream area.

**Channel Storage**
   Volume of water temporarily stored in river channels during routing processes.

**Climate Forcing**
   Meteorological input data driving the hydrological model, including precipitation, temperature, radiation, humidity, and wind speed.

**CMIP6**
   Coupled Model Intercomparison Project Phase 6 - Provides standardized climate model outputs for historical and future scenarios.

**Condensation**
   Process where water vapor changes to liquid water, forming clouds, dew, or fog. Occurs when air reaches its dew point temperature.

**Crop Factor (Kc)**
   Coefficient relating crop evapotranspiration to reference evapotranspiration. Calibration range: 0.8-3.0.

**CWatM**
   Community Water Model - Open-source hydrological model simulating the water cycle daily at global and local scales, developed by IIASA.

D
=

**D8 Flow Model**
   Eight-direction flow routing algorithm where each grid cell drains to one of its eight neighboring cells based on steepest descent.

**DDM30**
   0.5° drainage direction map used for ISIMIP compliance in global hydrological modeling.

**DEAP**
   Distributed Evolutionary Algorithms in Python - Optimization framework used for automatic calibration of CWatM parameters.

**Degree-Day Factor**
   Snowmelt coefficient (m °C⁻¹d⁻¹) relating temperature above freezing to snowmelt rate. Used in temperature-index snowmelt modeling.

**Depression Storage**
   Water accumulated in surface depressions that must be filled before runoff occurs.

**Dew Point**
   Temperature at which water vapor condenses into liquid water at constant pressure and water content.

**Discharge**
   Volume of water flowing through a river cross-section per unit time (m³/s). Primary output variable for model validation.

**Drainage Basin**
   Geographic area draining to a common outlet point. Also called watershed or catchment.

E
=

**ECHO Model**
   Hydro-economic model developed by IIASA for water infrastructure investment analysis, designed to couple with CWatM.

**Environmental Flow Requirements**
   Minimum water flows needed to maintain aquatic ecosystems and their services. Incorporated as constraints in water allocation.

**EPIC Model**
   Environmental Policy Integrated Climate model for crop yield simulation, can be coupled with CWatM.

**Evaporation**
   Process of water changing from liquid to vapor state. Energy-driven process primarily powered by solar radiation.

**Evapotranspiration (ET)**
   Combined water loss from evaporation from soil and water surfaces plus transpiration from plants. Can be calculated using Penman-Monteith or Hargreaves methods.

**EWEMBI**
   EartH2Observe, WFDEI and ERA-Interim data Merged and Bias-corrected for ISIMIP - Climate forcing dataset.

F
=

**FAIR Principles**
   Findable, Accessible, Interoperable, Reusable - Data management standards implemented in CWatM for tracking data sources and model versions.

**Field Capacity**
   Soil moisture content after excess gravitational water has drained (typically 2-3 days after saturation).

**FloPy**
   Python package for creating, running, and post-processing MODFLOW-based groundwater models. Used for CWatM-MODFLOW coupling.

**Forcing Data**
   External meteorological inputs driving the hydrological model, including precipitation, temperature, radiation, humidity.

**Fossil Water**
   Groundwater that has been stored in aquifers for more than 10,000 years with minimal recharge.

G
=

**GCM (General Circulation Model)**
   Global climate models providing projections of future climate conditions under different emission scenarios.

**GDAL**
   Geospatial Data Abstraction Library - Software library for reading and writing raster and vector geospatial data formats.

**Git Hash**
   Unique identifier for specific version of model code in version control system, stored in output files for reproducibility.

**GLOBIOM**
   Global Biosphere Management Model - IIASA's land use and agriculture model that can be coupled with CWatM.

**GNU GPL**
   GNU General Public License - Open source license under which CWatM is released.

**Groundwater Recession Constant**
   Time constant (days) controlling the rate of baseflow from groundwater storage. Key calibration parameter.

**Groundwater Recharge**
   Process of water moving from surface through soil to replenish groundwater aquifers.

**Groundwater Storage**
   Volume of water stored in aquifers below the water table. Modeled using linear reservoir approach or MODFLOW coupling.

**GSWP3**
   Global Soil Wetness Project Phase 3 - Provides meteorological forcing data for land surface modeling.

H
=

**Hargreaves Method**
   Temperature-based method for estimating potential evapotranspiration when radiation data is unavailable.

**HydroLakes Database**
   Global database providing information on 1.4 million lakes and reservoirs with surface area ≥10 hectares.

**HydroSheds**
   High-resolution hydrological data providing river networks, watershed boundaries, drainage directions, and flow accumulations.

**Hydrograph**
   Graph showing discharge variation over time at a specific location in a river.

**Hydrological Cycle**
   Continuous movement of water through Earth's systems: atmosphere, land surface, soil, groundwater, and oceans.

**Hydrological Processes**
   Physical mechanisms of water movement including precipitation, evaporation, infiltration, percolation, runoff, and groundwater flow.

**HWSD**
   Harmonized World Soil Database version 1.2 - Global soil property database at 30 arc-second resolution.

I
=

**IIASA**
   International Institute for Applied Systems Analysis - Research institute based in Austria that developed and maintains CWatM.

**Infiltration**
   Process of water entering soil from the surface. Rate depends on soil properties, moisture content, and surface conditions.

**Infiltration Capacity Parameter**
   Empirical shape parameter controlling maximum infiltration rate in the ARNO model.

**Initial Conditions**
   Starting values for state variables (soil moisture, groundwater, snow, etc.) at simulation beginning.

**Interception**
   Capture and temporary storage of precipitation on vegetation surfaces before reaching the ground.

**Interception Storage**
   Water held on leaf and stem surfaces that eventually evaporates without reaching the soil.

**Interflow**
   Lateral subsurface flow occurring above the water table in unsaturated soil zones.

**Interflow Factor**
   Calibration parameter controlling water percolation from interflow to groundwater. Range: 0.33-3.0.

**ISIMIP**
   Inter-Sectoral Impact Model Intercomparison Project - Framework for comparing global impact model outputs.

K
=

**Kinematic Wave Routing**
   Simplified solution of Saint-Venant equations for channel flow routing, assuming momentum equation can be approximated by uniform flow formula.

**KGE (Kling-Gupta Efficiency)**
   Model performance metric addressing limitations of Nash-Sutcliffe Efficiency by considering correlation, bias, and variability.

L
=

**Lake A Factor**
   Calibration parameter for lake area calculations. Range: 0.333-3.0.

**Lake Eva Factor**
   Calibration parameter for lake evaporation rates. Range: 0.5-3.0.

**Lake/Reservoir Storage**
   Water volume stored in lakes and reservoirs, differentiated between "big" (≥100 km² or upstream area ≥5000 km²) and "small".

**Lambert W-Function**
   Mathematical function used to solve transcendental equations like the Colebrook-White equation for flow friction.

**Land Cover**
   Physical material at Earth's surface (forest, grassland, urban, water, etc.) affecting hydrological processes.

**Lateral Flow**
   Horizontal movement of water through soil, particularly important in sloped terrain. Included in MODFLOW coupling.

**Linear Reservoir**
   Conceptual model where outflow is proportional to storage, used for groundwater and routing calculations.

**LISFLOOD**
   European flood forecasting model that shares some methodological approaches with CWatM.

M
=

**Manning's Coefficient (n)**
   Roughness coefficient for open channel flow. Ranges from 0.025 (smooth lowland rivers) to 0.075 (rough mountain streams).

**MARINA Model**
   Model for water quality assessment, particularly for nutrients and eutrophication, can be coupled with CWatM.

**Mask Map**
   Binary grid defining the spatial domain for model calculations and output.

**MESSAGE Model**
   IIASA's energy system optimization model for energy planning, designed to couple with CWatM.

**MODFLOW**
   Modular finite-difference groundwater flow model that can be coupled with CWatM for detailed groundwater simulation.

**Modified Puls Method**
   Reservoir routing method used in CWatM for simulating lake and reservoir operations.

**Modular Structure**
   Software architecture where functionality is divided into independent, interchangeable modules.

**MSWEP**
   Multi-Source Weighted-Ensemble Precipitation - Global precipitation dataset combining gauge, satellite, and reanalysis data.

N
=

**Nash-Sutcliffe Efficiency (NSE)**
   Statistical measure of model performance comparing simulated to observed values. Range: -∞ to 1 (perfect fit).

**NetCDF4**
   Network Common Data Form version 4 - Self-describing, portable data format for array-oriented scientific data.

**Normal Storage Limit**
   Threshold parameter for reservoir operations defining normal operating levels. Calibration range: 0.15-0.85.

O
=

**Open Source**
   Software with source code freely available for use, modification, and distribution. CWatM uses GNU GPL license.

**Outflow**
   Water leaving a system boundary, such as discharge from a watershed or release from a reservoir.

P
=

**PC-Raster Framework**
   Environmental modeling framework that influenced CWatM's modular structure with initialization and dynamic classes.

**Pedotransfer Function**
   Mathematical relationship deriving soil hydraulic parameters from easily measured soil properties like texture and organic matter.

**Penman-Monteith Equation**
   Physically-based method for calculating potential evapotranspiration using energy balance and aerodynamic principles.

**Percolation**
   Downward movement of water through soil and rock layers under gravity.

**PGMFD**
   Princeton Global Meteorological Forcing Dataset - Historical climate forcing data for land surface modeling.

**Porosity**
   Fraction of soil or rock volume occupied by pore spaces that can hold water or air.

**Potential Evapotranspiration (PET)**
   Maximum water loss possible from a surface with unlimited water supply under given atmospheric conditions.

**Precipitation**
   Any form of water falling from atmosphere to Earth's surface: rain, snow, sleet, hail.

**Preferential Flow**
   Rapid water movement through macropores bypassing the soil matrix. Controlled by empirical shape parameter.

**Python**
   High-level programming language in which CWatM is written, allowing platform independence and easy modification.

Q
=

**Qbase**
   Baseflow or outflow from groundwater zone in CWatM's linear reservoir groundwater model.

R
=

**RCP (Representative Concentration Pathway)**
   Greenhouse gas concentration trajectories adopted by IPCC for climate modeling (e.g., RCP2.6, RCP4.5, RCP6.0, RCP8.5).

**Recharge**
   Process of water addition to groundwater from precipitation or surface water infiltration.

**Recession Coefficient**
   Parameter controlling the rate of decrease in baseflow during dry periods. Key calibration parameter.

**Reservoir Operation**
   Rules governing water storage and release from reservoirs for flood control, water supply, and other purposes.

**Residence Time**
   Average time a water molecule spends in a particular reservoir (atmosphere ~10 days, oceans ~3000 years).

**Residual Water Content (θr)**
   Minimum volumetric water content remaining in soil at high suction pressures.

**Return Flow**
   Water returning to rivers or groundwater after use in irrigation, industry, or domestic sectors.

**River Network**
   System of connected stream channels draining a landscape, represented as grid cell connections in CWatM.

**River Routing**
   Process of moving water through channel networks using hydraulic equations.

**Root Zone**
   Soil depth from which plants extract water. Variable by vegetation type and soil properties.

**Rosetta**
   Pedotransfer function model deriving Van Genuchten parameters from basic soil properties.

**Runoff**
   Water flowing over land surface toward streams after exceeding infiltration capacity or saturation.

**Runoff Concentration**
   Process of collecting surface runoff within a grid cell before routing. Uses triangular weighting function in CWatM.

**Runoff Concentration Factor**
   Calibration parameter for time of concentration within grid cells. Range: 0.1-5.0.

S
=

**Saint-Venant Equations**
   Partial differential equations describing unsteady open channel flow. CWatM uses kinematic wave approximation.

**Saturated Hydraulic Conductivity (Ks)**
   Rate of water movement through fully saturated soil (m/day).

**Saturated Water Content (θs)**
   Maximum volumetric water content when all pore spaces are water-filled.

**Settings File**
   Configuration file (.ini format) containing all model parameters, paths, and options for a CWatM simulation.

**Snow Water Equivalent (SWE)**
   Depth of water that would result if snowpack melted completely.

**Snowmelt Coefficient**
   Degree-day factor relating temperature to snowmelt rate. Calibration range: 0.001-0.007 m °C⁻¹d⁻¹.

**Soil Depth Factor**
   Multiplier for adjusting modeled soil depth. Calibration range: 0.8-1.8.

**Soil Moisture**
   Water content in unsaturated soil zones, typically expressed as volumetric fraction.

**Spatial Resolution**
   Grid cell size for model calculations. CWatM supports 30 arcsec to 0.5 degrees.

**Spin-up Period**
   Initial simulation period allowing model states to equilibrate before analysis period.

**SSP (Shared Socioeconomic Pathway)**
   Scenarios of socioeconomic global changes used in climate impact assessments (SSP1-SSP5).

**Stomata**
   Microscopic pores on leaf surfaces controlling gas exchange and transpiration.

**Storage**
   Volume of water held in various reservoirs: soil, groundwater, lakes, snow, channels.

**Stream Flow**
   Water discharge through river channels, synonymous with discharge.

**Subdaily Time Step**
   Computational time intervals smaller than one day, used for soil moisture and routing calculations (10 steps/day).

**Surface Runoff**
   Water flowing over ground surface when rainfall rate exceeds infiltration capacity.

T
=

**Temporal Resolution**
   Time step for model calculations. CWatM uses daily steps with subdaily steps for certain processes.

**Total Water Storage (TWS)**
   Sum of all water stored in a system: surface water, soil moisture, groundwater, snow, ice.

**Transpiration**
   Water vapor release from plants through stomata. Major component of evapotranspiration.

**Triangular Weighting Function**
   Mathematical function used to distribute runoff concentration over time within grid cells.

U
=

**Unsaturated Hydraulic Conductivity**
   Rate of water movement through partially saturated soil, varies with water content.

**Unsaturated Zone**
   Soil region above water table where pore spaces contain both air and water.

**Upstream Area**
   Total land area draining to a specific point in the river network.

**Urban Water Cycle**
   Modified hydrological cycle in cities including water supply, wastewater, stormwater management.

V
=

**Van Genuchten Model**
   Mathematical model describing soil water retention curve and unsaturated hydraulic conductivity relationships.

**Vapor Pressure Deficit**
   Difference between saturation vapor pressure and actual vapor pressure, driving evapotranspiration.

**Variable Infiltration Capacity (VIC)**
   Hydrological model using variable infiltration curve. Compared with CWatM in model intercomparisons.

**Vegetation Dynamics**
   Temporal changes in plant communities affecting water cycle through changed evapotranspiration and interception.

**Version Control**
   System for tracking changes to model code. CWatM uses Git with version hashes stored in outputs.

W
=

**Warm Start**
   Initializing model simulation with saved state variables from previous run rather than default values.

**Water Balance**
   Accounting equation ensuring conservation of mass: Inputs = Outputs + Change in Storage.

**Water Demand**
   Human water requirements from irrigation, domestic, industrial, and energy sectors.

**Water Stress**
   Condition where water demand exceeds available supply, affecting plant growth or human activities.

**Water Table**
   Upper boundary of saturated groundwater zone where pore water pressure equals atmospheric pressure.

**Water Use**
   Actual water consumption by various sectors, may be less than demand due to availability constraints.

**Water Year**
   12-month period for hydrological accounting, often October-September in Northern Hemisphere.

**Watershed**
   Land area draining to common outlet, synonymous with drainage basin or catchment.

**WFDEI**
   WATCH Forcing Data methodology applied to ERA-Interim reanalysis - Climate forcing dataset.

**Wilting Point**
   Soil moisture content below which plants cannot extract water, leading to permanent wilting.

X
=

**xarray**
   Python library for working with labeled multi-dimensional arrays, particularly NetCDF data.

**XML Metadata**
   Extensible Markup Language files containing structured metadata about model configuration and data.

**xmipy**
   Python package for coupling models using the eXtended Model Interface, used in CWatM-MODFLOW coupling.

Z
=

**Zenodo**
   Research data repository where CWatM datasets and model versions are archived with DOIs.

**Zero Flow**
   Condition of no discharge in ephemeral or intermittent streams during dry periods.

**Zone of Aeration**
   Unsaturated zone above water table where pore spaces contain both air and water.

Mathematical Equations and Formulas
====================================

**Water Balance Equation**
   Basic conservation equation::

      P = ET + R + ΔS

   Where:
   - P = Precipitation
   - ET = Evapotranspiration  
   - R = Runoff
   - ΔS = Change in Storage

**Baseflow Equation**
   Linear reservoir outflow::

      Qbase = Storage / (Tbase × Rcoeff)

   Where:
   - Qbase = Baseflow
   - Storage = Groundwater storage
   - Tbase = Groundwater reservoir constant (days)
   - Rcoeff = Recession coefficient

**Van Genuchten Equation**
   Soil water retention curve::

      θ(h) = θr + (θs - θr) / [1 + (α|h|)^n]^m

   Where:
   - θ = Volumetric water content
   - h = Pressure head
   - θr = Residual water content
   - θs = Saturated water content
   - α, n, m = Empirical parameters

**Manning's Equation**
   Open channel flow velocity::

      V = (1/n) × R^(2/3) × S^(1/2)

   Where:
   - V = Velocity
   - n = Manning's roughness coefficient
   - R = Hydraulic radius
   - S = Channel slope

**Penman-Monteith Equation**
   Reference evapotranspiration::

      ET₀ = [Δ(Rn-G) + ρₐcₚ(eₛ-eₐ)/rₐ] / [Δ + γ(1 + rₛ/rₐ)]

   Where:
   - ET₀ = Reference evapotranspiration
   - Δ = Slope of saturation vapor pressure curve
   - Rn = Net radiation
   - G = Soil heat flux
   - ρₐ = Air density
   - cₚ = Specific heat of air
   - eₛ-eₐ = Vapor pressure deficit
   - rₐ = Aerodynamic resistance
   - rₛ = Surface resistance
   - γ = Psychrometric constant

.. note::
   This glossary covers CWatM version 1.10 (October 2025). Terms and definitions may evolve with model updates. For current information, consult https://cwatm.iiasa.ac.at/

.. seealso::
   - CWatM Documentation: https://cwatm.iiasa.ac.at/
   - GitHub Repository: https://github.com/iiasa/CWatM
   - IIASA Water Security: https://iiasa.ac.at/models-tools-data/cwatm
   - Model Manual: Burek et al. (2020) IIASA Report

.. rubric:: References

Burek P., et al. (2020). Development of the Community Water Model (CWatM v1.104) – a high-resolution hydrological model for global and regional assessment of integrated water resources management. Geoscientific Model Development 13(7): 3267-3298.

.. footer::
   Community Water Model Glossary | Version 1.06 | October 2024