readme.txt 

The script gw_pumping_excel2npy.py converts groundwater pumping information held in excel format into one readble by cwatm. Specifically, converting data on location (latitude and longitude) and pumping rate (m3/day) into an (.npy) file. This is only necessary if Groundwater_pumping = True in the settings file.

gw_pumping_excel2npy.py
Required files: 
- Excel file: pumping_wells.xlsx
- catchment limits 

Excel file: pumping_wells.xlsx
-------------------------------------
Provide a list of well locations and pumping rates.

Latitude	Longitude	Pumping rate [m3/day]
18.7	    73.6	    600
18.65	    73.65	    600

The Latitude and Longitude can be given in any defined coordinate system, and is chosen here to be in WGS84 format (World Geodesic System).

wgs84=pyproj.Proj("+init=EPSG:4326")        # Associated coord system

This is the projection system for the Upper Bhima basin. You're associated projection system can be found here: https://epsg.io/32643

UTM=pyproj.Proj("+init=EPSG:32643")         # Projection system for the Upper Bhima basin, 
                                            # WGS 84 / UTM zone 43N

Depending on your region, you will need to change the UTM coding

catchment limits
-------------------------------------
The program also uses one of the CWATM input files with data on the dimensions on the simulation area, set to the variable catchment_limits.
Here is an example of this file:

324388.8217428711
625888.8217428711
2146608.857620636
1864108.8576206362
566
604
320
370

The default script uses the file UB_limits.txt, and should be changed to your limits file accordingly. 

This creates the file Pumping_input_file.npy that CWATM reads in each Modflow timestep. 
