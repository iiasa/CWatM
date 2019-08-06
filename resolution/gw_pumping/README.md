Groundwater pumping
===================================

If you would like to include groundwater pumping, you must provide a list of well locations and pumping rates. The script  gw_pumping_excel2npy.py converts groundwater pumping information held in excel format into one readble by cwatm. Specifically, converting data on location and pumping rate into an (.npy) file. This is only necessary if Groundwater_pumping = True in the settings file.

gw_pumping_excel2npy.py

Required files: 
- pumping_wells.xlsx
- catchment limits 

pumping_wells.xlsx
-------------------------------------

Provide a list of well locations (latitude and longitude) and pumping rates (m3/day).

The Latitude and Longitude can be given in any defined coordinate system, and is chosen here to be in WGS84 format (World Geodesic System).

wgs84=pyproj.Proj("+init=EPSG:4326")        # Associated coord system

This is the projection system for the Upper Bhima basin. You're associated projection system can be found here: https://epsg.io/32643

UTM=pyproj.Proj("+init=EPSG:32643")         # Projection system for the Upper Bhima basin, 
                                            # WGS 84 / UTM zone 43N

Depending on your region, you will need to change the UTM coding

catchment limits
-------------------------------------
The program also uses one of the CWATM input files with data on the dimensions on the simulation area, set to the variable catchment_limits.

The default script uses the file UB_limits.txt, and should be changed to your limits file accordingly. 

This creates the file Pumping_input_file.npy that CWatM reads in each Modflow timestep. 
