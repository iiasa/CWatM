Prerequisites: the script must be run using the same virtual environment used to run CWatM. The files required by the script to operate
must be stored in the same directory of the script, otherwise new files will be created. The required files are an excel file with the 
following columns:
Variable name, Long name, Unit, Description, First module, Priority, Module 1, Module 2, Module 3, Module 4, Module 5, Module 6, Module 7, Module 8, Module 9, Module 10, Module 11, Module 12, Module 13, Module 14, Module 15, Module 16

and an xml file structured as netCDF4 metadata.

1. Run the following command to launch the script: python List_all_variables.py and follow the instructions prompted in the console
2. The script will browse all the modules of CWaTM e produce a list of variable with the information on where each variable is declared and used
3. When prompted, enter a name for the excel file or accept the default (Note: if the file exists, it will be overwritten)
4. The list of variables will be compared with the list of variables in the excel file (if it existed before step 3), if the list contains new variables, they are added to the excel
5. The excel file is authomatically open: if needed, edit the information of the variables (e.g. description, level of priority, long name etc.)
6. Save and close the excel file, press enter
7. The script proceeds to read the file and create a worksheet for each of the priority levels of the variables.
8. When prompted provide a name for the netCDF4 metadata xml file or accept the default