gw_pumpinh_excel2npy.py

This script converts the Excel file with data on location (latitude and longitude) and pumping rate (m3/day) into UTM and then the associated indices and writes an npy file. 

1. Pumping wells
Excel file: pumping_wells.xlsx
You may have as many pumping wells as you wish (until someone discovers otherwise). I haven't gone about 66 wells.

2. Coordinates
The originail script uses the following conversions:
wgs84=pyproj.Proj("+init=EPSG:4326")        # Associated coord system
UTM=pyproj.Proj("+init=EPSG:32643")         # Projection system for the Upper Bhima basin

Depending on your region, you will need to change the UTM coding
For example, Beijing in UTM zone 50s is EPSG:32750

3. Basin limits
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

The default script has this file as UB_limits.txt, and should be changed to your limits file accordingly. 

This creates the file Pumping_input_file.npy that CWATM reads in each 7 days (or Modflow timestep). 
In my setup of the model, this should be put in the folder:
E:\Modflow\Last_CWatM_ModFlow_Bhima\ModFlow_input\ModFlow_inputs500m_Bhima