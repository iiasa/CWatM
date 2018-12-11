
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
   │-  README.txt
   │
   └--areamaps
   │   └- maskmap, stationmap
   │
   └--landcover
   │   └---forest
   │   │   │-  CropCoefficientForest_10days
   │   │   │-  interceptcapForest10days
   │   │   │-  maxRootdepth, minSoilDepthFrac
   │   │   └-  rootFraction1, rootFraction2
   │   │
   │   └---grassland (same var as forest)
   │   │
   │   └---irrNonPaddy (same var as forest)
   │   │
   │   └---irrPaddy (same var as forest)
   │
   └───landsurface   
   │   │- fractionlandcover, global_clone
   │   │ 
   │   └---albedo
   │   │   └- albedo
   │   │ 
   │   └---topo
   │   │   └- dz_Rel_hydro1k, elvstd , tanslope
   │   │ 
   │   └---waterDemand
   │       └- domesticWaterDemand, industryWaterDemand, irrigationArea, efficiency
   │
   └───soil
   │   └- alpha, forest_alpha, lamdba, forest_lambda, ksat, forest_ksat, thetas, forest_thetas, thetar, forest_thetar
   │   └-cropgrp
   │
   └---groundwater   
   │   └- kSatAquifer, recessionCoeff, specificYield
   │
   └---routing   
       │- ldd, catchment, cellarea
       │
       └---kinematic
       │   └- chanbnkf, chanbw, changrad, chanleng, chanman
       │
       └---lakereservoirs
           └- lakeResArea, lakeResDis,lakeResID, lakeResType, lakeResVolRes, lakeResYear, 
           └- smallLakesRes, smalllakesresArea, smalllakesresDis, smallwatershedarea



Static data
===============

Mask map
---------

* mask map or coordinates to model only regions or catchments
* maps or coordinates for station to print time series


Landsurface
-----------

Albedo
******

Global Albedo dataset from Muller et al., (2012) http://www.globalbedo.org

Digital elevation model and river channel network
*************************************************

The model uses a digital elevation model and its derivate (e.g. standards deviation, slope) as variables for the snow processes and for the routing of surface runoff. The Shuttle Radar Topography Mission - SRTM (Jarvis et al., 2008) is used for latitudes <= 60 deg North and DEM Hydro1k (US Geological Survey Center for Earth Resources Observation and Science)is used for latitudes > 60 deg North
CWATM uses a local drainage direction map which defines the dominant flow direction in one of the eight neighboring grid cells (D8 flow model). This forms a river network from the springs to the mouth of a basin. To be compliant with the ISIMIP framework  the  0.5 deg drainage direction map (DDM30)  of (Döll and Lehner, 2002) is used. For higher resolution e.g. 5’ different sources of river network maps are available e.g. HydroSheds (Lehner et al., 2008) – DRT (Wu et al., 2011) and CaMa-Flood (Yamazaki et al., 2009). These approaches uses the same hydrological sound digital elevation model but differ in the upscaling methods. Fang et al. (2017) shows the importance of routing schemes and river networks in peak discharge simulation.


Soil and soil hydraulic properties
----------------------------------

Soil textural data were derived from the ISRIC SoilGrids1km database http://www.isric.org/explore/soilgrids (Hengl et al. 2014). 
Pedotransfer functions applied on 1km soil texture data - originating from the HYPRES database (Wösten et al. 1999) were used to obtain the Mualem - VanGenuchten soil hydraulic parameters for soil water transport modeling in the soil module.

Water demand
------------

Groundwater
-----------

GLHYMPS—Global Hydrogeology Maps of permeability and porosity  http://crustalpermeability.weebly.com/data-sources.html (Gleeson et al., 2014)



Lakes and Reservoirs
********************

The HydroLakes database http://www.hydrosheds.org/page/hydrolakes (Bernhard Lehner et al., 2011; Messager, Lehner, Grill, Nedeva, & Schmitt, 2016) provides 1.4 million global lakes and reservoirs with a surface area of at least 10ha. CWATM differentiate between big lakes and reservoirs which are connected inside the river network and smaller lakes and reservoirs which are part of a single grid cell and part of the runoff concentration within a grid cell.  Therefore the HydroLakes database is separated into “big” lakes and reservoirs with an area ≥ 100 km2 or a upstream area ≥ 5000 km2 and “small” lakes which represents the non-big lakes. All lakes and reservoirs are combined at grid cell level but big lakes can have the expansion of several grid cells. Lakes bigger than 10000 km2 are shifted according to the ISIMIP protocol.



Temporal data for each year
===========================

Crop coefficient
----------------

Based on:
MIRCA2000—Global data set of monthly irrigated and rainfed crop areas around the year 2000. http://www.uni-frankfurt.de/45218023/MIRCA  (Portmann et al., 2010)

Land cover
----------

Land cover is used to calculate fraction of water, forest, irrigated area, rice irrigated area, sealed (impermeable area) and the remaining fraction for each cell. For each fraction the soil module runs separately. The total runoff of each cell is calculated by weighting the cell according to the different fractions.

Source: https://lta.cr.usgs.gov/GLCC (US Geological Survey Center for Earth Resources Observation and Science)


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

* WFDEI.GPCC  (Weedon et al. 2014) WFD—Watch forcing data set: 0.5 3/6 hourly meteorological forcing from ECMRWF reanalysis (ERA40) bias-corrected and extrapolated by CRU TS and GPCP (rainfall) and corrections for under catch
* PGMFD v.2 - Princeton (Sheffield et al. 2006),
* GSWP3 (Kim et al.)
* MSWEP (Beck et al. 2017) .

From Global Circulation models GCMs (see ISI-Mip 2b)

- HadGem2-ES (Met Office Hadley Centre, UK)
- IPSL-CM5A-LR (Institut Pierre-Simon Laplace, France)
- GFDL-ESM2M (NOAA, USA)
- MIROC-ESM-CHEM (JAMSTEC, AORI, University of Tokyo, NIES, Japan)
- NorESM1-M (Norwegian Climate Centre, Norway)




References
===========

- Beck, H. E., A. I. J. M. Van Dijk, V. Levizzani, J. Schellekens, D. G. Miralles, B. Martens and A. De Roo (2017). "MSWEP: 3-hourly 0.25° global gridded precipitation (1979-2015) by merging gauge, satellite, and reanalysis data." Hydrology and Earth System Sciences 21(1): 589-615.
- Döll, P. and B. Lehner (2002). "Validation of a new global 30-min drainage direction map." Journal of Hydrology 258(1): 214-231.
- Döll, P. and S. Siebert (2002). "Global modeling of irrigation water requirements." Water Resources Research 38(4): 81-811.
- Gleeson, T., N. Moosdorf, J. Hartmann and L. P. H. Van Beek (2014). "A glimpse beneath earth's surface: GLobal HYdrogeology MaPS (GLHYMPS) of permeability and porosity." Geophysical Research Letters 41(11): 3891-3898.
- Hengl, T., J. M. de Jesus, R. A. MacMillan, N. H. Batjes, G. B. M. Heuvelink, E. Ribeiro, A. Samuel-Rosa, B. Kempen, J. G. B. Leenaars, M. G. Walsh and M. R. Gonzalez (2014). "SoilGrids1km — Global Soil Information Based on Automated Mapping." PLOS ONE 9(8): e105992.
- Jarvis, A., H. I. Reuter, A. Nelson and E. Guevara (2008). Hole-filled SRTM for the globe Version 4, available from the CGIAR-CSI SRTM 90m Database (http://srtm.csi.cgiar.org).
- Kim, H., S. Watanabe, E.-C. Chang, K. Yoshimura, Y. Hirabayashi, J. Famiglietti and T. Oki "Century long observation constrained global dynamic downscaling and hydrologic implication [in preparation]."
- Lehner, B., C. R. Liermann, C. Revenga, C. Vörösmarty, B. Fekete, P. Crouzet, P. Döll, M. Endejan, K. Frenken, J. Magome, C. Nilsson, J. C. Robertson, R. Rödel, N. Sindorf and D. Wisser (2011). "High-resolution mapping of the world's reservoirs and dams for sustainable river-flow management." Frontiers in Ecology and the Environment 9(9): 494-502.
- Lehner, B., K. Verdin and A. Jarvis (2008). "New global hydrography derived from spaceborne elevation data." Eos 89(10): 93-94.
- Messager, M. L., B. Lehner, G. Grill, I. Nedeva and O. Schmitt (2016). "Estimating the volume and age of water stored in global lakes using a geo-statistical approach."  7: 13603.
- Muller, P. J., P. Lewis, J. Fischer, P. North and U. Framer (2012). The ESA GlobAlbedo Project for mapping the Earth's land surface albedo for 15 Years from European Sensors., paper presented at IEEE Geoscience and Remote Sensing Symposium (IGARSS)  IEEE Geoscience and Remote Sensing Symposium (IGARSS) 2012. Munich, Germany.
- Portmann, F. T., S. Siebert and P. Döll (2010). "MIRCA2000—Global monthly irrigated and rainfed crop areas around the year 2000: A new high-resolution data set for agricultural and hydrological modeling." Global Biogeochemical Cycles 24(1): n/a-n/a.
- Sheffield, J., G. Goteti and E. F. Wood (2006). "Development of a 50-year high-resolution global dataset of meteorological forcings for land surface modeling." Journal of Climate 19(13): 3088-3111.
- Siebert, S., P. Döll, J. Hoogeveen, J. M. Faures, K. Frenken and S. Feick (2005). "Development and validation of the global map of irrigation areas." Hydrology and Earth System Sciences 9(5): 535-547.
- US Geological Survey Center for Earth Resources Observation and Science Hydro1k. U. E. Land Processes Distributed Active Archive Center (LP DAAC), Sioux Falls, SD.
- Weedon, G. P., G. Balsamo, N. Bellouin, S. Gomes, M. J. Best and P. Viterbo (2014). "The WFDEI meteorological forcing data set: WATCH Forcing data methodology applied to ERA-Interim reanalysis data." Water Resources Research 50(9): 7505-7514.
- Wösten, J. H. M., A. Lilly, A. Nemes and C. Le Bas (1999). "Development and use of a database of hydraulic properties of European soils." Geoderma 90(3-4): 169-185.
- Wu, H., J. S. Kimball, N. Mantua and J. Stanford (2011). "Automated upscaling of river networks for macroscale hydrological modeling." Water Resources Research 47(3).
- Yamazaki, D., T. Oki and S. Kanae (2009). "Deriving a global river network map and its sub-grid topographic characteristics from a fine-resolution flow direction map." Hydrology and Earth System Sciences 13(11): 2241-2251.
- Zhao, F., Veldkamp, T. I. E., Frieler, K., Schewe, J., Ostberg, S., Willner, S., Schauberger, B., Gosling, S., N. , Müller Schmied, H., Portmann, F., T. , Leng, G., Huang, M., Liu, X., Tang, Q., Hanasaki, N., Biemans, H., Gerten, D., Satoh, Y., Pokhrel, Y., Stacke, T., Ciais, P., Chang, J., Ducharne, A., Guimberteau, M., Wada, Y., Kim, H., & Yamazaki, D. (2017). The critical role of the routing scheme in simulating peak river discharge in global hydrological models. Environmental Research Letters, 12(7), 075003




