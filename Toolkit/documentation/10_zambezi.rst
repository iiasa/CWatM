.. raw:: html

   <pre style="font-size: 0.7em;">
   Todo en la tierra se encrespó, la zarza
   clavó y el hilo verde
   mordía, el pétalo cayó cayendo
   hasta que única flor fue la caída
   Pablo Neruda Agua
   </pre>


#######################
**10. Example Zambezi**
#######################


Zambezi basin
-------------

The hydrological model CWatM is intended to be scalable and can be applied at finer spatial scales (e.g., basin scale). CWatM has been calibrated for the Zambezi, using six sub catchments and measured discharge.


Assessment of water stress
--------------------------

The CWatM-calibrated model is used to assess water scarcity through 2050 in the Zambezi basin. Water resources at each grid cell depend on climate, water management (e.g., reservoirs), and water use for irrigation, livestock, domestic, or industrial purposes.
For each cell (at 5 arcmin ~ 9x9 km2) and for aggregated regions water resources can be related to water demand from different sectors. Results from the distributed hydrological model CWatM are aggregated to 21 sub-basins. 


Water Stress Index for Zambezi
------------------------------
The WSI is defined in Falkenmark et al. (1989), Falkenmark (1997), and Wada et al. (2011) as the ratio of blue water availability to net total water demand. A ratio defines water scarcity as the ratio of total withdrawals across the sectors — domestic, industrial, and agriculture — to water resources. 

:math:`{WSI=  Water demand / Water availability}` 

| where:
| WSI: 		Water Stress Index
| Water demand:	Net total water demand as the sum of livestock, irrigation, industrial and domestic water demand
| Water avail:	Freshwater availability from rivers, lakes and renewable groundwater

A region is considered “severely water stressed” if WSI exceeds 40% (Alcamo et al., 2003). The yearly WSI shows no water stress for the whole basin in 2010, but this will change till 2050 for the BAU scenario (business-as-usual composed from SSP2 and RCP6.0 scenarios), mainly due to increasing agricultural and domestic water demand (increase by a factor of 5) as annual mean river discharge is only increasing by 6%. August is chosen for the monthly comparison as this is the month with the highest rate of water withdrawal (WW) and a mean monthly discharge (MMD) that is only slightly higher than in November:


.. raw:: html 

   <iframe width="745" height="680" frameborder="0" scrolling="no" src="https://chart-studio.plotly.com/~bupe/22.embed"></iframe>



Figure 1: Annual water stress 2010 - and 2050
