
#######################
Data
#######################

.. contents:: 
    :depth: 3

Data requirements
=================

Data format
=================
In general data format is netCDF (version3 or version4)

For the mask map (to define the area of calculation) or the stations (to define the time series outputs) in can be either
netCDF, Geotiff or PCRaster maps

Data storage structure
======================

.. code-block:: rest
   
   project
   ├── README.txt
   │
   ├── areamaps
   │   └── maskmap, stationmap
   │
   ├── landcover
   │   ├──forest
   │   │   ├── cropCoefficientForest_10days
   │   │   ├── interceptcapForest10days
   │   │   ├── maxRootdepth, minSoilDepthFrac
   │   │   └── rootFraction1, rootFraction2
   │   │
   │   ├── grassland (same var as forest)
   │   │
   │   ├── irrNonPaddy (same var as forest)
   │   │
   │   └── irrPaddy (same var as forest)
   │
   ├───landsurface   
   │   ├── fractionlandcover, global_clone
   │   │ 
   │   ├── albedo
   │   │   └── albedo
   │   │ 
   │   ├── topo
   │   │   └── dz_Rel_hydro1k, elvstd , tanslope
   │   │ 
   │   └── waterDemand
   │       └── domesticWaterDemand, industryWaterDemand, irrigationArea, efficiency
   │
   ├── soil
   │   ├── alpha, forest_alpha, lamdba, forest_lambda, ksat, forest_ksat, thetas, forest_thetas, thetar, forest_thetar
   │   └── cropgrp
   │
   ├── groundwater   
   │   └── kSatAquifer, recessionCoeff, specificYield
   │
   └── routing   
       ├── ldd, catchment, cellarea
       │
       ├── kinematic
       │   └── chanbnkf, chanbw, changrad, chanleng, chanman
       │
       └── lakereservoirs
           ├── lakeResArea, lakeResDis,lakeResID, lakeResType, lakeResVolRes, lakeResYear, 
           └── smallLakesRes, smalllakesresArea, smalllakesresDis, smallwatershedarea



Static data
===============

Mask map
---------

* mask map or coordinates to model only regions or catchments (value in mask = 1)
* maps or coordinates for station to print time series

.. image:: _static/mask_rhine.jpg
    :width: 300px

Figure 1: Mask map for the Rhine basin at 5' showing in addition 6 stations

.. warning::

    Make sure any cell defined in the mask map has a value (not NaN!) in the following map. A missing value in a cell will lead to a missing value in the result maps from the process this map is linked to. 
    
    The routing process will carry this missing value downstream!


Landsurface
-----------


Digital elevation model and river channel network
*************************************************

The model uses a digital elevation model and its derivate (e.g. standards deviation, slope) as variables for the snow processes and for the routing of surface runoff. The Shuttle Radar Topography Mission - SRTM (Jarvis et al., 2008) [#]_ is used for latitudes <= 60 deg North and DEM Hydro1k (US Geological Survey Center for Earth Resources Observation and Science) [#]_ is used for latitudes > 60 deg North

.. image:: _static/dem.jpg
    :width: 600px

Figure 1: Digital elevation based on SRTM for 30' and 5'

.. image:: _static/Standard_deviation_elevation_5min.jpg
    :width: 300px

Figure 2: Standard deviation of elevation based on SRTM and 5'

River drainage maps
-------------------

The river drainage map or local drain direction (LDD) is the essential component to connect the grid cells in order to express the flow direction from one cell to another and forming a river network from the springs to the mouth.

The approach to find the flow direction is in theory quite simple:
There are eight valid output directions relating to the eight adjacent cells into which flow could travel. This approach is commonly referred to as an eight-direction (D8) flow model. The direction from each cell to its steepest downslope neighbour is chosen as flow direction. If the flow direction for each cell is given, a raster of accumulated flow into each cell can be calculated. Figure 4 shows the steps from DEM to flow direction to flow accumulation. Flow direction is shown in PC-Raster coding of the direction (ArcGIS uses another coding).

CWatM uses a local drainage direction map which defines the dominant flow direction in one of the eight neighboring grid cells (D8 flow model). This forms a river network from the springs to the mouth of a basin. To be compliant with the ISIMIP framework  the  0.5° drainage direction map (DDM30)  of (Döll and Lehner, 2002) [#]_ is used. For higher resolution e.g. 5’ different sources of river network maps are available e.g. HydroSheds (Lehner et al., 2008) [#]_ – DRT (Wu et al., 2011) [#]_ and CaMa-Flood (Yamazaki et al., 2009) [#]_. These approaches uses the same hydrological sound digital elevation model but differ in the upscaling methods. Zhao et al. (2017) [#]_ shows the importance of routing schemes and river networks in peak discharge simulation.
For CWatM the DDM30 is used for 0.5° and DRT is used for 5'.


.. image:: _static/elevation_flowaccu.jpg
    :width: 600px

Figure 3: From elevation to flow accumulation

.. image:: _static/ldd.jpg
    :width: 600px

Figure 4: River network for the Rhine basin

River channel maps
------------------

Channel maps are describing the geometry like the length, slope, width and depth of the main channel inside a grid cell.
Data used to get the geometry are mainly taken from elevation model and channel network. 

Methodology
***********

Flow through the channel is simulated using the kinematic wave equations. The basic equations used are the equations of continuity and momentum. 
The continuity equation is:

:math:`{\frac{\delta Q}{\delta x}} + {\frac{\delta A }{\delta t}} = q` 

| where:
| Q: channel discharge [m3 s-1], 
| A: cross-sectional area of the flow [m2]
| q: amount of lateral inflow per unit flow length [m2 s-1]. 

The momentum equation can also be expressed as (Chow et al., 1988):

:math:`{A = \alpha Q^\beta}` 

The coefficients α and β are calculated by putting in Manning's equation

:math:`Q = A v = \frac{AR^{2/3} \sqrt{So}}{n} = \frac{A^{5/3} \sqrt{So}}{n P^{2/3}}` 

| where:
| v: velocity [m/s]
| n: Manning's roughness coefficient
| P: wetted perimeter of a cross-section of the surface flow [m]
| R: hydraulic Radius R=A/P

Solving this for α and β gives:

:math:`\alpha = (\frac{nP^{2/3}}{\sqrt{So}})^\beta` and  :math:`\beta = 0.6` 

| To calculate α CWatM uses static maps of:
| P: wetted perimeter approximated in CWatM: P = channel width + 2 * channel bankful depth
| n: Manning’s coefficient
| S0: gradient (slope) of the water surface: S0 = Δelevation/channel length

Channel length
**************
The network upscaling method of Wu et al. (2011) [5]_ is tracing the finer river network inside the coarser resolution.
Channel length of 5' is traced from original SRTM channel length with the diagonal path taken to be √2 ∙ straight path.

Channel gradient
****************

Channel gradient (or channel slope) is the average gradient of the main river inside a cell.

The approach taken here is to take the elevation from where the fine resolution channel enters the coarser grid cell and the elevation where it leaves the grid cell. Channel gradient is then calculated as:
 
Channel gradient = (elevation[in] –elevation[out]) / channel length.

.. image:: _static/Channel_gradient.png
    :width: 600px

Figure x: Channel gradient at 5 in % or tan(α)'

Manning’s roughness
*******************

Manning’s roughness coefficient (n) is one of the calibration parameter in CWatM. But on subbasin level an estimation of the spatial distribution of n is needed. n normally range between 0.025 (low land rivers) and 0.075 (mountainous rivers with a lot of vegetation, gravels). A low n = smooth surface results in a faster travel time and higher peaks. A high n = rough surface results in slower travel time and lower peaks. Inspection of the riverbed will reveal characteristics related to roughness. A treatment of the use of Manning's coefficients is in McCuen (1998) [#]_. Below is a first-approximation of Manning's coefficients for some widely observed beds::

	n = 0.04 - 0.05		Mountain streams
	n = 0.035 		    Winding, weedy streams
	n = 0.028 - 0.035 	Major streams with widths > 30m at flood stage
	n = 0.015 		    Clean, earthen channels

For the base map of Manning a regression function is used with 0.025 as the minimum value for flatland rivers with large upstream areas. A maximum of 0.015 is added for flatland rivers and small upstream areas (upstream area dependent) and another maximum of 0.030 is added if in mountainous areas (elevation dependent)::
   
   Manning =0.025 + 0.015 * min(50/upstream,1) + 0.030*min(DEM/2000,1)
   Where:
   upstream: upstream catchment area [km]
   DEM:		 elevation from Digital elevation model [m]

.. image:: _static/Mannings_roughness_5min.png
    :width: 600px

Figure x: Manning’s roughness coefficient for 5'


Channel Bottom Width
********************

The channel bottom width is calculated in two steps with the first step using a simply regression between channel width and upstream area and the second uses a better correlated one between average discharge and channel width. 
First the channel bottom width is calculated by a simply regression between upstream catchment area and width::

   Channel width=upstreamArea ×0.0032

This first map is used to run CWatM to get an estimate on average discharge. 

In the second step a regression formula from Pistocchi et al. 2006 [#]_ is used to calculate the channel bottom width with average discharge as regressor, because discharge seems to be better correlated to width than upstream area. This is quite obvious if you look at small alpine catchment with high precipitation and therefore high discharge and on the other side at big, almost semiarid catchments on the Iberian peninsula with low average discharge::

   Channel width=average Q ^ 0.539

.. image:: _static/Channel_width_5min.png
    :width: 600px

Figure 6: Channel width at 5'


Channel bankful depth 
*********************

Instead of deriving channel hydraulic properties from a non linear correlation with the upstream area we are using the Manning’s equation to get a better estimate. But for the first estimate (same as for channel bottom width) we use a correlation with upstream area::

   Channel bankful depth = 0.27 upstreamArea^0.33

In the second step we use the Manning’s equation. We adopt a rectangular cross section and we assume depth is small compared to width. So the perimeter is assumed to be::

   P = 1.01 * channel bottom width 

Discharge for bankful discharge is assumed to be two times the average discharge (Qavg)
  
:math:`Q = 2 * Qavg` 

:math:`Q = \frac{A^{5/3} \sqrt{So}}{n P^{2/3}} \approx \frac{Wh^{5/3} \sqrt{So}}{n (1.01W)^{2/3}}` 

| Where:
| W: Channel width
| h: bankful depth
| Q: bankful discharge ~ 2 * average discharge

As we now know all the other variables we can solve this equation for bankful depth with some assumption:

This leads to the equation:

:math:`Channel bankful depth (h)= 1.004 N^{3/5} Q^{3/5} W^{-3/5} So^{-3/10}` 

| Where:
| W: Channel width
| Q: bankful discharge ~ 2 * average discharge


Soil and soil hydraulic properties
----------------------------------

Modeling of unsaturated flow and transport processes can be done with the 1D Richard equation, which requires a high spatial and temporal distribution of the soil hydraulic properties

:math:`\frac{\delta \Theta}{\delta t} = \frac{\delta}{\delta z}[K(\Theta(\frac{\delta h(\Theta)}{\delta z}-1)]-S(\Theta)`  (1D Richard equation)

| Where:
| θ: soil volumetric moisture content [L3/L3]  
| t:   time [T]
| h:  soil water pressure head [L]
| K(θ): unsaturated hydraulic conductivity [L/T]
| z: vertical coordinate
| S: source sink term [T-1] 

With the simplification the 1D Richard equation e.g.  flow of soil moisture is entirely gravitu-driven and matrix potential gradient is zero this implies a flow tha tis always in downward direction at a rate that equals the conductivity of the soil. The relationship can now be described with the model of Mualem (1976) [#]_ and with the van Genuchten model (1980) [#]_ equation. Please find a full description of the modeled soil processes in `Burek et al. 2020 <https://gmd.copernicus.org/articles/13/3267/2020>`_

:math:`K(\Theta) = K_s(\frac{\Theta - \Theta_r}{\Theta_s - \Theta_r})^{0.5} \lbrace 1-[1-(\frac{\Theta - \Theta_r}{\Theta_s - \Theta_r})^{1/m}]^{m} \rbrace^{2}`  (Van Genuchten equation)

| Where:
| Ks: saturated conductivity of the soil [cm/d-1]
| K(θ): unsaturated conductivity
| :math:`\Theta` :math:`\Theta_s` :math:`\Theta_r` : actual, maximum and residual amounts of moisture in the soil [mm]
| m: is calculated from the pore-size index :math:`\lambda` : :math:`m = \frac{\lambda}{\lambda + 1}` 

The soil hydraulic parameter :math:`\Theta_s` :math:`\Theta_r` :math:`\lambda` and :math:`K_s` are needed to simulated soil water transport for the van Genuchten model.

| The infiltration capacity of the soil is using the Xinanjiang (also known as VIC/ARNO) model (Todini, 1996) [#]_
| The soil hydraulic parameter :math:`\alpha` (inverse of air entry suction) is needed for calculating infiltration capacity


Harmonized World Soil Database
******************************

The Harmonized World Soil Database 1.2 (HWSD) FAO et al. (2012) [#]_ - Version 1.2 7 March, 2012 was developed by the Land Use Change and Agriculture Program of IIASA (LUC) and the Food and Agriculture Organization of the United Nations (FAO). The HWSD is a 30 arc-second raster database with over 16000 different soil mapping units that combines existing regional and national updates of soil information worldwide – the European Soil Database (ESDB), the 1:1 million soil map of China, various regional SOTER databases (SOTWIS Database), and the Soil Map of the World – with the information contained within the 1:5000000 scale FAO-UNESCO Soil Map of the World. The resulting raster database is linked to harmonized soil property data.

.. image:: _static/HWSD_index.jpg
    :width: 600px

Figure x: Harmonized World Soil Database Index, FAO et al. (2012)

From the HWSD the standard soil properties like texture, porosity, soil minerals (% of sand, clay), organic mater and bulk density are used.
For example Bulk density second soil layer 5-30 cm depth:

.. image:: _static/Bulk_Density1.png
    :width: 600px

Figure x: Bulk density second soil layer 5-30 cm  at 5'



Pedotransfer function Rosetta3
******************************

Soil parameters required by CWatM are obtained from soil properties by using a pedotransfer function.

A pedotransfer is used from Zhang and Schaap 2016 [#]_ to transfer the standard soil properties (soil texture, porosity, organic mater and bulk density) to the van Genuchten model parameters: :math:`\Theta_s` (maximal amount of moisture) :math:`\Theta_r` (residual amount of moisture) :math:`\lambda` (pore-size index) :math:`K_s` (saturated conductivity of the soil) and :math:`\alpha` (inverse of air entry suction)

Rosetta3 code is available at: http://www.cals.arizona.edu/research/rosettav3.html

For example θs and Ks:

.. image:: _static/soil_theta.jpg
    :width: 600px

Figure x: Soil volumetric moisture content (θs) [%]  second soil layer 5-30 cm  at 5'


.. image:: _static/soil_ks.jpg
    :width: 600px

Figure x: Saturated hydraulic conductivity (Ks) [cm/day] second soil layer 5-30 cm  at 5'

Groundwater
-----------

For groundwater modeling maps of the recession constant of the hydraulic conductivity and the storage coefficient are needed.
Gleeson et al., (2011) [#]_ and Gleeson et al. (2014) [#]_ can provide data for this.

| Global RecessionConstant GLIM: [1/day] based on drainage theory (linear reservoir) 
| Global SatHydraulicConductivity: Mean permeability of consolidated and unconsolidated geologic units below the soil [log10 m2]
| Global StorageCoefficient [m/m]: specific yields or storage coefficients

| Data:
| GLHYMPS—Global Hydrogeology Maps of permeability and porosity  (Gleeson et al., 2014)
| http://crustalpermeability.weebly.com/data-sources.html 
| http://spatial.cuahsi.org/gleesont01/

.. image:: _static/Recession_Constant.png
    :width: 600px

Figure x: Recession constant GLIM: [1/day] at 5'


Lakes and Reservoirs
********************

The HydroLakes database http://www.hydrosheds.org/page/hydrolakes (Lehner et al. (2011) [#]_; Messager et al. (2016) [#]_, provides 1.4 million global lakes and reservoirs with a surface area of at least 10ha. CWatM differentiate between big lakes and reservoirs which are connected inside the river network and smaller lakes and reservoirs which are part of a single grid cell and part of the runoff concentration within a grid cell.  Therefore the HydroLakes database is separated into “big” lakes and reservoirs with an area ≥ 100 km2 or a upstream area ≥ 5000 km2 and “small” lakes which represents the non-big lakes. All lakes and reservoirs are combined at grid cell level but big lakes can have the expansion of several grid cells. Lakes bigger than 10000 km2 are shifted according to the ISIMIP protocol.
Lake and reservoir (LR) data are specified by an id for each LR, type of LR (1 for lake, 2 for reservoir), area of LR, year of constraction of reservoir and average discharge at the outlet of LR.




Temporal data for each year
===========================

Crop coefficient
----------------

Based on:
MIRCA2000—Global data set of monthly irrigated and rainfed crop areas around the year 2000. http://www.uni-frankfurt.de/45218023/MIRCA  (Portmann et al., 2010) [#]_

Land cover
----------

Land cover is used to calculate fraction of water, forest, irrigated area, rice irrigated area, sealed (impermeable area) and the remaining fraction for each cell. For each fraction the soil module runs separately. The total runoff of each cell is calculated by weighting the cell according to the different fractions.

Source: https://lta.cr.usgs.gov/GLCC (US Geological Survey Center for Earth Resources Observation and Science)

Forest 
******

Forest land cover is used from from Hansen et al. (2013) [#]_

.. image:: _static/Tree_cover_5min.jpg
    :width: 600px

Figure x: Tree cover in 2010 at 5'

Sealed
******

Urban area or impervious surface area (ISA) based on.

| Based on 1km version of Elvidge et al. (2007) [#]_
| https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3841857/
| ftp://ftp.ngdc.noaa.gov/DMSP/

Future projection based on:

Transient, future land use pattern generated by the LU model MAgPIE (Popp et al. 2014 [#]_; Stevanovic et al. 2016 [#]_), assuming population growth and economic as in SSP2 and climate change scenario RCP6.0

.. image:: _static/Sealed_5min.png
    :width: 600px

Figure x: Sealed area in 2010 at 5'

Albedo
******

Global Albedo dataset from Muller et al., (2012) [#]_ 


Continous temporal data
=======================

Meteorological data 
--------------------

* max, min, avg temperature [K]
* humidity (relative[%] or specific[%])
* surface pressure [Pa]
* radiation (short wave and long wave downwards) [W m-2]
* windspeed [m/s]

If potential evaporation is already calculated in a prerun or from external source

* Precipitation [Kg m-2 s-1] or [m] or [mm] (can be adjusted by a conversion factor in the settings file)
* Temperature (avg) [K]
* Potential evaporation [Kg m-2 s-1] or [m] or [mm] (can be adjusted by a conversion factor in the settings file)


From observation: (see ISI-MIP 2a)

* WFDEI.GPCC  (Weedon et al. 2014) [#]_ WFD—Watch forcing data set: 0.5 3/6 hourly meteorological forcing from ECMRWF reanalysis (ERA40) bias-corrected and extrapolated by CRU TS and GPCP (rainfall) and corrections for under catch
* PGMFD v.2 - Princeton (Sheffield et al. 2006) [#]_
* GSWP3 (Kim et al.) [#]_
* MSWEP (Beck et al. 2017) [#]_

From Global Circulation models GCMs (see ISI-Mip 2b)

- HadGem2-ES (Met Office Hadley Centre, UK)
- IPSL-CM5A-LR (Institut Pierre-Simon Laplace, France)
- GFDL-ESM2M (NOAA, USA)
- MIROC-ESM-CHEM (JAMSTEC, AORI, University of Tokyo, NIES, Japan)
- NorESM1-M (Norwegian Climate Centre, Norway)




References
===========

.. [#] Jarvis, A., H. I. Reuter, A. Nelson and E. Guevara (2008). Hole-filled SRTM for the globe Version 4, available from the CGIAR-CSI SRTM 90m Database (http://srtm.csi.cgiar.org).
.. [#] US Geological Survey Center for Earth Resources Observation and Science Hydro1k. U. E. Land Processes Distributed Active Archive Center (LP DAAC), Sioux Falls, SD.
.. [#] Döll, P. and B. Lehner (2002). "Validation of a new global 30-min drainage direction map." Journal of Hydrology 258(1): 214-231.
.. [#] Lehner, B., K. Verdin and A. Jarvis (2008). "New global hydrography derived from spaceborne elevation data." Eos 89(10): 93-94.
.. [#] Wu, H., J. S. Kimball, N. Mantua and J. Stanford (2011). "Automated upscaling of river networks for macroscale hydrological modeling." Water Resources Research 47(3).
.. [#] Yamazaki, D., T. Oki and S. Kanae (2009). "Deriving a global river network map and its sub-grid topographic characteristics from a fine-resolution flow direction map." Hydrology and Earth System Sciences 13(11): 2241-2251.
.. [#] Zhao, F., Veldkamp, T. I. E., Frieler, K., Schewe, J., Ostberg, S., Willner, S., Schauberger, B., Gosling, S., N. , Müller Schmied, H., Portmann, F., T. , Leng, G., Huang, M., Liu, X., Tang, Q., Hanasaki, N., Biemans, H., Gerten, D., Satoh, Y., Pokhrel, Y., Stacke, T., Ciais, P., Chang, J., Ducharne, A., Guimberteau, M., Wada, Y., Kim, H., & Yamazaki, D. (2017). The critical role of the routing scheme in simulating peak river discharge in global hydrological models. Environmental Research Letters, 12(7), 075003
.. [#] McCuen, R. H. (1998). Hydrologic Analysis and Design. Upper Saddle River, NJ, USA: Prentice Hall.
.. [#] Pistocchi, A., & Pennington, D. (2006). European hydraulic geometries for continental SCALE environmental modelling. Journal of Hydrology, 329(3-4), 553-567
.. [#] Mualem, Y. (1976). A  New  Model  for Predicting  the  Hydraulic  Conductivity  of Unsaturated Porous Medial. Water Resources Research, Vol. 12, 513-522
.. [#] Van  Genuchten, M. T. (1980). A Closed Form Equation for Predicting the Hydraulic Conductivity of Unsaturated Soils. Soil Science Society of America Journal
.. [#] Todini, E. (1996). The ARNO rainfall—runoff model. Journal of Hydrology, 175(1), 339-382
.. [#] FAO, IIASA, ISRIC, ISSCAS, & JRC. (2012). Harmonized World Soil Database (version 1.2). http://www.fao.org/soils-portal/soil-survey/soil-maps-and-databases/harmonized-world-soil-database-v12/en/
.. [#] Zhang, Y., Schaap, M.,(2017): Weighted recalibration of the Rosetta pedotransfer model with improved estimates of hydraulic parameter distributions and summary statistics (Rosetta3),Journal of Hydrology,Volume 547,Pages 39-53,ISSN 0022-1694,https://doi.org/10.1016/j.jhydrol.2017.01.004. (http://www.sciencedirect.com/science/article/pii/S0022169417300057)
.. [#] Gleeson, T., L. Smith, N. Moosdorf, J. Hartmann, H. H. Dürr, A. H. Manning, L. P. H. van Beek, and A. M. Jellinek (2011), Mapping permeability over the surface of the Earth, Geophys. Res. Lett., 38, L02401, doi:10.1029/2010GL045565. 
.. [#] Gleeson, T., N. Moosdorf, J. Hartmann and L. P. H. Van Beek (2014). "A glimpse beneath earth's surface: GLobal HYdrogeology MaPS (GLHYMPS) of permeability and porosity." Geophysical Research Letters 41(11): 3891-3898.
.. [#] Lehner, B., C. R. Liermann, C. Revenga, C. Vörösmarty, B. Fekete, P. Crouzet, P. Döll, M. Endejan, K. Frenken, J. Magome, C. Nilsson, J. C. Robertson, R. Rödel, N. Sindorf and D. Wisser (2011). "High-resolution mapping of the world's reservoirs and dams for sustainable river-flow management." Frontiers in Ecology and the Environment 9(9): 494-502.
.. [#] Messager, M. L., B. Lehner, G. Grill, I. Nedeva and O. Schmitt (2016). "Estimating the volume and age of water stored in global lakes using a geo-statistical approach."  7: 13603.
.. [#] Portmann, F. T., S. Siebert and P. Döll (2010). "MIRCA2000—Global monthly irrigated and rainfed crop areas around the year 2000: A new high-resolution data set for agricultural and hydrological modeling." Global Biogeochemical Cycles 24(1): n/a-n/a.
.. [#] Hansen, M. C., P. V. Potapov, R. Moore, M. Hancher, S. A. Turubanova, A. Tyukavina, D. Thau, S. V. Stehman, S. J. Goetz, T. R. Loveland, A. Kommareddy, A. Egorov, L. Chini, C. O. Justice, and J. R. G. Townshend. 2013. “High-Resolution Global Maps of 21st-Century Forest Cover Change.” Science 342 (15 November): 850–53. Data available on-line from: http://earthenginepartners.appspot.com/science-2013-global-forest.
.. [#] Elvidge, C. D., Tuttle, B. T., Sutton, P. C., Baugh, K. E., Howard, A. T., Milesi, C., Bhaduri, B., Nemani, R. (2007). Global Distribution and Density of Constructed Impervious Surfaces. Sensors (Basel, Switzerland), 7(9), 1962-1979. doi:10.3390/s7091962
.. [#] Popp, A., Humpenöder, F., Weindl, I., Bodirsky, B. L., Bonsch, M., Lotze-Campen, H., Müller, C., Biewald, A., Rolinski, S., Stevanovic, M., & Dietrich, J. P. (2014). Land-use protection for climate change mitigation. Nature Climate Change, 4, 1095
.. [#] Stevanović, M., Popp, A., Lotze-Campen, H., Dietrich, J. P., Müller, C., Bonsch, M., Schmitz, C., Bodirsky, B. L., Humpenöder, F., and Weindl, I.(2016): The impact of high-end climate change on agricultural welfare, Science Advances, 2, 2016. http://advances.sciencemag.org/content/2/8/e1501452
.. [#] Muller, P. J., P. Lewis, J. Fischer, P. North and U. Framer (2012). The ESA GlobAlbedo Project for mapping the Earth's land surface albedo for 15 Years from European Sensors., paper presented at IEEE Geoscience and Remote Sensing Symposium (IGARSS)  IEEE Geoscience and Remote Sensing Symposium (IGARSS) 2012. Munich, Germany. http://www.globalbedo.org
.. [#] Weedon, G. P., G. Balsamo, N. Bellouin, S. Gomes, M. J. Best and P. Viterbo (2014). "The WFDEI meteorological forcing data set: WATCH Forcing data methodology applied to ERA-Interim reanalysis data." Water Resources Research 50(9): 7505-7514.
.. [#] Sheffield, J., G. Goteti and E. F. Wood (2006). "Development of a 50-year high-resolution global dataset of meteorological forcings for land surface modeling." Journal of Climate 19(13): 3088-3111.
.. [#] Kim, H., S. Watanabe, E.-C. Chang, K. Yoshimura, Y. Hirabayashi, J. Famiglietti and T. Oki "Century long observation constrained global dynamic downscaling and hydrologic implication [in preparation]."
.. [#] Beck, H. E., A. I. J. M. Van Dijk, V. Levizzani, J. Schellekens, D. G. Miralles, B. Martens and A. De Roo (2017). "MSWEP: 3-hourly 0.25° global gridded precipitation (1979-2015) by merging gauge, satellite, and reanalysis data." Hydrology and Earth System Sciences 21(1): 589-615.

- Döll, P. and S. Siebert (2002). "Global modeling of irrigation water requirements." Water Resources Research 38(4): 81-811.
- Siebert, S., P. Döll, J. Hoogeveen, J. M. Faures, K. Frenken and S. Feick (2005). "Development and validation of the global map of irrigation areas." Hydrology and Earth System Sciences 9(5): 535-547.





