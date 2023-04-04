Prerequisites: the script must be run using the same virtual environment used to run CWatM. The files the script requires to operate must be stored in the same directory as the script; otherwise, new files will be created. The necessary files are an XML file structured as a netCDF4 metadata and an Excel file with the following columns:
Variable name, Long name, Unit, Description, First module, Priority, Module 1, Module 2, Module 3, Module 4, Module 5, Module 6, Module 7, Module 8, Module 9, Module 10, Module 11, Module 12, Module 13, Module 14, Module 15, Module 16

1. Run the following command to launch the script: python List_all_variables.py and follow the instructions prompted in the console
2. The script will browse all the modules of CWaTM and produce a variable list with the information on where each variable is declared and used
3. When prompted, enter a name for the excel file or accept the default (Note: if the file exists, it will be overwritten)
4. The list of variables will be compared with the list of variables in the excel file (if it existed before step 3); if the list contains new variables, they are added to the excel
5. The excel file is automatically opened: if needed, edit the information of the variables (e.g. description, level of priority, long name etc.)
6. Save and close the excel file, and press enter in the terminal
7. The script proceeds to read the file, create a worksheet for each of the variables' priority levels, and update the variable documentation in the CWatM scripts. 