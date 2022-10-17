# -*- coding: utf-8 -*-
"""
Created on Tue Apr  7 15:13:10 2020

@author: Luca G.
"""

import os
# PB added to sort the Dict_AllVariables
from collections import OrderedDict
from operator import getitem

import argparse

parser = argparse.ArgumentParser(description='Determine if the Excel file has been updated.')
parser.add_argument('integers', metavar='N', type=int, nargs=1,
                    help='add 1 after .py if the Excel has been updated')
args = parser.parse_args()
if args.integers[0]:
    print('The Excel has already been updated -- including descriptions into CWatM')
else:
    print('The Excel has not yet been updated -- creating new Excel')

### DEFINING TWO USEFULL FUNCTIONS ###

def extract_selfvar(module_name):
    """Extract all 'self.var.varname' defined in the module,
    module_name has to include the path.
    Return the list of this variables"""

    # Openning and closing the Python module
    print("----> ", module_name)
    fichier = open(module_name, "r")
    aa = fichier.readlines()
    fichier.close()
    print('Exploring : ', module_name)
    variable_names_list = []
    associated_line = []  # Line where the module appears
    first_definition = []  # 1 if defined or updated, zero if only used
    test_comment = 0
    for ii in range(len(aa)):  # for each line in the Python code

        bb = aa[ii]
        bb = bb.lstrip()  # Removing space at the beginning

        # test if we are in """ out commented lines:
        # index_out_commented = bb_temp.find('"""')
        # if index_out_commented

        # PB test if the line is a comment line
        bb = bb[:bb.find("#")]

        if bb.find('"""') > -1:
            if test_comment == 1:
                test_comment = 0
            else:
                test_comment = 1
        # sometime start and end """ are in the same line (should not be!): to detect end """ and resume validating
        if bb[3:].find('"""') > -1:
            test_comment = 1

        # deleted the lines to detect #

        if test_comment == 0:
            indexselfvar = 0
            idselfvar = 0
            while indexselfvar != -1:
                bb_temp = bb[idselfvar:]
                indexselfvar = bb_temp.find("self.var")  # Find all self.var position in the line

                if indexselfvar != -1:  # there is at least one self.var in the line
                    # PB change to +1 and to ww=len(bb_temp) because some variable lost last letter
                    for ww in range(indexselfvar, len(bb_temp) + 1):
                        if ww == len(bb_temp) or bb_temp[ww] == ':' or bb_temp[ww] == ',' or bb_temp[ww] == '(' or \
                                bb_temp[ww] == ')' \
                                or bb_temp[ww] == ' ' or bb_temp[ww] == '=' or bb_temp[ww] == '*' or bb_temp[
                            ww] == '+' or bb_temp[ww] == '-' \
                                or bb_temp[ww] == '/' or bb_temp[ww] == '[' or bb_temp[ww] == ']' or bb_temp[
                            ww] == '"' or bb_temp[ww:ww + 5] == '.appe' \
                                or bb_temp[ww:ww + 5] == '.copy' or bb_temp[ww:ww + 5] == '.ravel' or bb_temp[
                                                                                                      ww:ww + 5] == '<' or bb_temp[
                                                                                                                           ww:ww + 5] == '>' \
                                or bb_temp[ww:ww + 7] == '.astype':  # Find the end of the var name
                            break
                        # PB changed to ww-indexselfvar because ww is absolut in the line
                        www = ww - indexselfvar
                        if www > 8:
                            if bb_temp[ww] == '.' or bb_temp[ww] == "'":
                                break

                    # Normally, we have defined a 'self.var.xxxxxxx' string
                    if bb_temp[indexselfvar:ww] != 'self.var':
                        # PB tested again because it is not sorted out
                        if bb_temp[indexselfvar:ww] != 'self.var.':
                            variable_names_list.append(bb_temp[indexselfvar:ww])  # Append this variable to the list
                            associated_line.append(ii + 1)  # Append the associated line to the list
                            if indexselfvar == 0:  # if 'self.var' is at the beginning of the line
                                first_definition.append(1)
                            else:
                                first_definition.append(0)
                    idselfvar = idselfvar + indexselfvar + 1

    return variable_names_list, associated_line, first_definition


def extract_localvar(module_name, str_name):
    """Extract all 'local variable name' defined in the module.
    Return the list of this variables"""

    sub_fun = [v for v in dir(module_name) if not v.startswith('__')]  # Find all functions in the Python module

    variable_names_list = []
    for ii in range(len(sub_fun)):
        name = str_name + '.' + str(sub_fun[ii]) + '.__code__.co_varnames'
        temp_list = eval(name)
        variable_names_list.append(temp_list)

    return variable_names_list

### EXTRACT LOCAL AND SELF.VAR VARIABLES FROM EACH MODULE

Dict_AllVariables = {}  # Keys are variable name : then 1rst module and associated line

# For each CWAT module:

# local_variable_names_list = extract_localvar(soil , 'soil')

folders = ['hydrological_modules', 'hydrological_modules/routing_reservoirs',
           'hydrological_modules/groundwater_modflow', 'hydrological_modules/water_demand', 'management_modules']

temp_folders = ['../' + f for f in folders]
folders = temp_folders

var_def = {}
for folders_paths in folders:
    path = str(folders_paths)
    python_modules = os.listdir(path)
    for ll in range(len(python_modules)):
        # if the file is a Python module
        if python_modules[ll][-2:] == 'py' and python_modules[ll][-2:] != 'List_all_variables':
            [variable_names_list, associated_line, first_definition] = extract_selfvar(path + '/' + python_modules[ll])
            for ii in range(len(variable_names_list)):  # For each variable
                if first_definition[ii] == 1:
                    txt_line = 'defined line ' + str(associated_line[ii])
                    var_def[variable_names_list[ii]] = python_modules[ll][:-3]
                else:
                    txt_line = 'used line ' + str(associated_line[ii])

                name_module_python = python_modules[ll][:-3]  # to go to the line when saving
                if variable_names_list[ii] not in Dict_AllVariables:  # if the self.var is not already defined
                    Dict_AllVariables[variable_names_list[ii]] = {name_module_python: txt_line}
                    if variable_names_list[ii] not in var_def:
                        var_def[variable_names_list[ii]] = name_module_python

                else:  # We add the new module to the list of the variable
                    # if the variable is already defined in this module
                    if name_module_python in Dict_AllVariables[variable_names_list[ii]]:
                        if first_definition[ii] == 1:
                            txt_line = 'updated line ' + str(associated_line[ii])
                        else:
                            txt_line = 'used line ' + str(associated_line[ii])
                        aa = Dict_AllVariables[variable_names_list[ii]][name_module_python]
                        Dict_AllVariables[variable_names_list[ii]][name_module_python] = aa + ', ' + txt_line
                    else:
                        Dict_AllVariables[variable_names_list[ii]][name_module_python] = txt_line

# PB put in where the variable is defined

for ii in Dict_AllVariables:
    Dict_AllVariables[ii]['defined'] = var_def[ii]

# PB sorting by where the variable is defined
Dict_AllVariables = OrderedDict(sorted(Dict_AllVariables.items(), key=lambda x: getitem(x[1], 'defined')))

if not args.integers[0]:

    import pandas as pd

    df = pd.read_excel(
        io='selfvar.xlsx',
        sheet_name='variables')
    dict = {}

    for var in range(len(df['Variable name'])):
        dict[df['Variable name'][var]] = [df['Unit'][var], df['Description'][var]]

    import xlsxwriter
    import numpy as np

    workbook = xlsxwriter.Workbook('selfvar_new.xlsx')
    worksheet = workbook.add_worksheet('variables')
    bold = workbook.add_format({'bold': True})

    #f = open('List_CWatM_variables.txt', 'w')
    row = 1
    max_number_of_modules = 1

    for ii in Dict_AllVariables:

        #f.write(str(ii) + ';')
        var_name = str(ii)[9:]

        worksheet.write(row, 0, var_name, bold)
        if var_name in dict.keys():
            unit = dict[var_name][0]
            description = dict[var_name][1]

            if unit not in [np.nan]:
                worksheet.write(row, 1, unit)
            if description not in [np.nan]:
                worksheet.write(row, 2, description)

        #f.write(Dict_AllVariables[ii]['defined'] + ';')
        worksheet.write(row, 3, Dict_AllVariables[ii]['defined'])

        col = 4
        for keys in Dict_AllVariables[ii]:
            if keys != 'defined':
                #f.write(str(keys) + ':' + Dict_AllVariables[ii][keys] + ';')
                worksheet.write(row, col, str(keys) + ':' + Dict_AllVariables[ii][keys] + ';')
                col += 1

        max_number_of_modules = np.maximum(col - 1, max_number_of_modules)
        #f.write('\n')  # Go to the line after each variable

        row += 1

    #f.close()

    worksheet.write(0, 0, 'Variable name', bold)
    worksheet.write(0, 1, 'Unit', bold)
    worksheet.write(0, 2, 'Description', bold)
    worksheet.write(0, 3, 'First module', bold)
    for module in range(max_number_of_modules):
        worksheet.write(0, module + 4, 'Module ' + str(module + 1), bold)
    workbook.close()



    print('Now it is time to update the Excel selfvar_new.xlsx with descriptions and units.')
    print('When you are finished, save this as selfvar.xlsx.')
    print('Then, run this script again, with a 1 after the .py')
    a = bb


# Open the Excel file with variables description and save varname and description in python list
# Reading an Excel file using Python

import xlrd

xlrd.xlsx.ensure_elementtree_imported(False, None)
xlrd.xlsx.Element_has_iter = True
# Give the location of the file
loc = ("selfvar.xlsx")

# To open Workbook
wb = xlrd.open_workbook(loc)
sheet = wb.sheet_by_index(0)
rows = sheet.nrows
var_name_in_excel = []
var_description_in_excel = []
var_unit_in_excel = []
for ir in range(1, rows):
    name_complete = 'self.var.' + sheet.cell_value(ir, 0)
    var_name_in_excel.append(name_complete)
    var_description_in_excel.append(sheet.cell_value(ir, 2))
    var_unit_in_excel.append(sheet.cell_value(ir, 1))

# Now we have:
#   - a list of variables name used in CWATM with the modules and lines where they are used
#   - a list of variables name in an excel file (warning it is not the same variables name because coming
#     from an older version)
#   - a list of variables description


### ADDING DESCRIPTION TO THE MAIN DICTIONARY ###

print('Adding description and unit to the dictionary')
for name_var in Dict_AllVariables:  # for each self.var variable name
    cnt_xl = 0
    for excel_name in var_name_in_excel:  # for each self.var variable name described in excel sheet
        if excel_name.startswith(name_var):  # the excel variable is probably the same as namevar
            aa = 0
            # check if excel_name is not another variable
            for name_var2 in Dict_AllVariables:
                if name_var2 != name_var:
                    if excel_name.startswith(name_var2):
                        if len(name_var2) > len(name_var):  # another variable fit better
                            aa = 1  # do nothing as another variable will fit better

            if aa == 0:  # we have the best match, we can add the corresponding description
                if 'description' in Dict_AllVariables[name_var]:  # we already fill the description
                    if Dict_AllVariables[name_var]['description'] == '':
                        Dict_AllVariables[name_var]['description'] = var_description_in_excel[cnt_xl]
                        Dict_AllVariables[name_var]['unit'] = var_unit_in_excel[cnt_xl]
                else:
                    Dict_AllVariables[name_var]['description'] = var_description_in_excel[cnt_xl]
                    Dict_AllVariables[name_var]['unit'] = var_unit_in_excel[cnt_xl]

        cnt_xl += 1

### SAVE THE FINAL LIST IN A TEXT FILE ###

#f = open('CompleteList_CWatMvars.txt', 'w')
#for ii in Dict_AllVariables:
#    if 'description' in Dict_AllVariables[ii]:
#        f.write(str(ii) + '    //    Descri : ' + str(Dict_AllVariables[ii]['description']) + '    //    Unit : ' +
#                str(Dict_AllVariables[ii]['unit']) + '    //    Appears in : ' + str(Dict_AllVariables[ii]))
#    else:
#        f.write(str(ii) + '    //    Descri : ' + '   ' + '    //    Unit : ' + '   ' + '    //    Appears in : ' +
#                str(Dict_AllVariables[ii]))
#
#    f.write('\n')  # Go to the line after each variable
#f.close()

### ADDING THE SELF.VAR DESCRIPTIONS AND OCCURENCE LINES IN PYTHON CWATM MODULES

print('Modifying CWATM modules to add self.var information')

for folders_paths in folders:
    path = str(folders_paths)
    python_modules = os.listdir(path)
    for ll in range(len(python_modules)):
        if python_modules[ll][-2:] == 'py':
            filename_to_modify = path + '/' + python_modules[ll]

            # We know the Python file, now we need to find all variables inside
            var_name_in_module = []
            for var_name in Dict_AllVariables:  # FOR EACH SELF.VARIABLE NAME
                for keys in Dict_AllVariables[var_name]:
                    if python_modules[ll][:-3] == keys:  # we are searching the module where we want add information
                        var_name_in_module.append(var_name)  # This list contains all var_name appering in this module

            if len(var_name_in_module) > 0:

                ## Now, we modify the Python module to add self.var description
                print("=== " + filename_to_modify)
                file = open(filename_to_modify, 'r')
                lines = file.readlines()
                file.close()

                # PB change to make the output table variable
                lead = " " * 4
                between = " " * 2
                col1 = 37
                col2 = 70
                col3 = 5
                # col4 = 30

                added_description = lead + "**Global variables**\n\n"

                added_description = added_description + lead + '{:{x}.{x}}'.format('=' * col1,
                                                                                   x=col1) + between + '{:{x}.{x}}'.format(
                    '=' * col2, x=col2) + between + \
                                    '{:{x}.{x}}'.format('=' * col3, x=col3) + "\n"
                added_description = added_description + lead + '{:{x}.{x}}'.format('Variable [self.var]',
                                                                                   x=col1) + between + '{:{x}.{x}}'.format(
                    'Description', x=col2) + between + \
                                    '{:{x}.{x}}'.format('Unit', x=col3) + "\n"
                added_description = added_description + lead + '{:{x}.{x}}'.format('=' * col1,
                                                                                   x=col1) + between + '{:{x}.{x}}'.format(
                    '=' * col2, x=col2) + between + \
                                    '{:{x}.{x}}'.format('=' * col3, x=col3) + "\n"

                # added_description = added_description + "    ==========================  ========================================================================================  =========  ==============================\n"
                # added_description = added_description + "    Variable [self.var]         Description                                                                               Unit       Appears in\n"
                # added_description = added_description + "    ==========================  ========================================================================================  =========  ==============================\n"

                for vv in var_name_in_module:
                    list_modules = ""
                    for jj in Dict_AllVariables[vv]:
                        if jj != 'description' and jj != 'unit' and jj != 'defined':
                            list_modules = list_modules + str(jj) + ","
                    if 'description' in Dict_AllVariables[vv].keys():
                        desc = Dict_AllVariables[vv]['description']
                    else:
                        desc = ""
                    if 'unit' in Dict_AllVariables[vv].keys():
                        unit = Dict_AllVariables[vv]['unit']
                        if unit == "-":
                            unit = "--"  # PB just to have a nicer representation on the web side
                    else:
                        unit = ""

                    # added_description = added_description + lead + '{:{x}.{x}}'.format(vv[9:],x=col1) + between + '{:{x}.{x}}'.format(desc, x=col2) + between +\
                    #                    '{:{x}.{x}}'.format(unit, x=col3) + between + '{:{x}.{x}}'.format(list_modules, x=col4) + "\n"
                    added_description = added_description + lead + '{:{x}.{x}}'.format(vv[9:],
                                                                                       x=col1) + between + '{:{x}.{x}}'.format(
                        desc, x=col2) + between + \
                                        '{:{x}.{x}}'.format(unit, x=col3) + "\n"

                # added_description = added_description + "    ==========================  ========================================================================================  =========  ==============================\n\n"
                # added_description = added_description + lead + '{:{x}.{x}}'.format('='*col1,x=col1) + between + '{:{x}.{x}}'.format('='*col2,x=col2) + between +\
                #                    '{:{x}.{x}}'.format('='*col3,x=col3) + between + '{:{x}.{x}}'.format('='*col4,x=col4) + "\n\n"

                added_description = added_description + lead + '{:{x}.{x}}'.format('=' * col1,
                                                                                   x=col1) + between + '{:{x}.{x}}'.format(
                    '=' * col2, x=col2) + between + \
                                    '{:{x}.{x}}'.format('=' * col3, x=col3) + "\n\n"
                added_description = added_description + "    **Functions**\n"

                # PB delete old list in module (if there is any)
                linesnew = []
                add = True
                for line in lines:
                    if line.find('**Global variables**') > -1:
                        add = False
                    if add:
                        linesnew.append(line)
                    if line.find('**Functions**') > -1:
                        add = True
                lines = linesnew

                # Find where to add this description
                class_index = -1
                begin_outcommented_lines = -1
                end_outcommented_lines = -1
                for module_line in range(len(lines)):
                    if lines[module_line].startswith('class'):  # the class is defined here
                        class_index = module_line
                    if lines[module_line].startswith('    """') and class_index != -1:
                        begin_outcommented_lines = module_line
                    if lines[module_line].startswith(
                            '    """') and begin_outcommented_lines != -1 and class_index != -1:
                        end_outcommented_lines = module_line

                if end_outcommented_lines != -1:  # we found a class and definition just after, so we can add our text
                    # lines[end_outcommented_lines-1] = lines[end_outcommented_lines-1] + '\n' + added_description
                    # PB removed the /n in between
                    lines[end_outcommented_lines - 1] = lines[end_outcommented_lines - 1] + added_description

                # PB to make it unix compatible (windows does not care but linux)
                file = open(filename_to_modify, mode='w', newline='\n', encoding='utf8')
                file.writelines(lines)
                file.close()

### MODIFY THE XML FILE ###


###################### RUN A SECOND TIME THE CODE TO ACTUALIZE LINES ##################################################################################
### EXTRACT LOCAL AND SELF.VAR VARIABLES FROM EACH MODULE

Dict_AllVariables = {}  # Keys are variable name : then 1rst module and associated line

# For each CWAT module:

# local_variable_names_list = extract_localvar(soil , 'soil')

for folders_paths in folders:
    path = str(folders_paths)
    python_modules = os.listdir(path)
    for ll in range(len(python_modules)):
        if python_modules[ll][-2:] == 'py' and python_modules[ll][
                                               -2:] != 'List_all_variables':  # if the file is a Python module
            [variable_names_list, associated_line, first_definition] = extract_selfvar(path + '/' + python_modules[ll])
            for ii in range(len(variable_names_list)):  # For each variable
                if first_definition[ii] == 1:
                    txt_line = 'defined line ' + str(associated_line[ii])
                else:
                    txt_line = 'used line ' + str(associated_line[ii])

                name_module_python = python_modules[ll][:-3]  # to go to the line when saving
                if variable_names_list[ii] not in Dict_AllVariables:  # if the self.var is not already defined
                    Dict_AllVariables[variable_names_list[ii]] = {name_module_python: txt_line}

                else:  # We add the new module to the list of the variable
                    if name_module_python in Dict_AllVariables[
                        variable_names_list[ii]]:  # if the variable is already defined in this module
                        if first_definition[ii] == 1:
                            txt_line = 'updated line ' + str(associated_line[ii])
                        else:
                            txt_line = 'used line ' + str(associated_line[ii])
                        aa = Dict_AllVariables[variable_names_list[ii]][name_module_python]
                        Dict_AllVariables[variable_names_list[ii]][name_module_python] = aa + ', ' + txt_line
                    else:
                        Dict_AllVariables[variable_names_list[ii]][name_module_python] = txt_line

### SAVE THE FINAL LIST IN A TEXT FILE ###
#f = open('List_CWatM_variables.txt', 'w')
#for ii in Dict_AllVariables:
#    f.write(str(ii) + ' ; ')
#    for keys in Dict_AllVariables[ii]:
#        f.write(str(keys) + ' : ' + Dict_AllVariables[ii][keys] + ' ; ')
#    f.write('\n')  # Go to the line after each variable
#f.close()

### OPEN THE EXCEL FILE WITH VARIABLES DESCRIPTION AND SAVE VARNAME AND DESCRIPTION IN PYTHON LIST
# Reading an excel file using Python
import xlrd

# Give the location of the file
loc = ("selfvar.xlsx")
# To open Workbook
wb = xlrd.open_workbook(loc)
sheet = wb.sheet_by_index(0)
rows = sheet.nrows
var_name_in_excel = []
var_description_in_excel = []
var_unit_in_excel = []
var_standardname_in_excel = []
for ir in range(1, rows):
    name_complete = 'self.var.' + sheet.cell_value(ir, 0)
    var_name_in_excel.append(name_complete)
    var_description_in_excel.append(sheet.cell_value(ir, 2))
    var_unit_in_excel.append(sheet.cell_value(ir, 1))
    var_standardname_in_excel.append(sheet.cell_value(ir, 0))

# No we have:
#   - a list of variables name used in CWATM with the modules and lines where they are used
#   - a list of variables name in an excel file (warning it is not the same variables name because coming from an older version)
#   - a list of variables description


### ADDING DESCRIPTION TO THE MAIN DICTIONNARY ###

print('Adding description and unit to the dictionary')
for name_var in Dict_AllVariables:  # for each self.var variable name
    cnt_xl = 0
    for excel_name in var_name_in_excel:  # for each self.var variable name described in excel sheet
        if excel_name.startswith(name_var):  # the excel variable is probably the same as namevar
            aa = 0
            # check if excel_name is not another variable
            for name_var2 in Dict_AllVariables:
                if name_var2 != name_var:
                    if excel_name.startswith(name_var2):
                        if len(name_var2) > len(name_var):  # another variable fit better
                            aa = 1  # do nothing as another variable will fit better

            if aa == 0:  # we have the best match, we can add the corresponding description
                if 'description' in Dict_AllVariables[name_var]:  # we already fill the description
                    if Dict_AllVariables[name_var][
                        'description'] == '':  # we replace by a better description than empty text
                        Dict_AllVariables[name_var]['description'] = var_description_in_excel[cnt_xl]
                        Dict_AllVariables[name_var]['unit'] = var_unit_in_excel[cnt_xl]
                else:
                    Dict_AllVariables[name_var]['description'] = var_description_in_excel[cnt_xl]
                    Dict_AllVariables[name_var]['unit'] = var_unit_in_excel[cnt_xl]

        cnt_xl += 1

### SAVE THE FINAL LIST IN A TEXT FILE ###

#f = open('CompleteList_CWatMvars.txt', 'w')
#for ii in Dict_AllVariables:
#    if 'description' in Dict_AllVariables[ii]:
#        f.write(str(ii) + '    //    Descri : ' + str(Dict_AllVariables[ii]['description']) + '    //    Unit : ' + str(
#            Dict_AllVariables[ii]['unit']) + '    //    Appears in : ' + str(Dict_AllVariables[ii]))
#    else:
#        f.write(str(ii) + '    //    Descri : ' + '   ' + '    //    Unit : ' + '   ' + '    //    Appears in : ' + str(
#            Dict_AllVariables[ii]))
#
#    f.write('\n')  # Go to the line after each variable
#f.close()

### WRITE AN XML FILE AS TEXT FILE

# Import module to open and write metanetdfc xml file
from xml.dom import minidom

metaNetcdfVar = {}
# open the metanetcdf file
metaparse = minidom.parse('metaNetcdf.xml')
meta = metaparse.getElementsByTagName("CWATM")[0]
for metavar in meta.getElementsByTagName("metanetcdf"):
    d = {}
    for key in list(metavar.attributes.keys()):
        if key != 'varname':
            d[key] = metavar.attributes[key].value
    key = metavar.attributes['varname'].value
    metaNetcdfVar[key] = d

# the format used by Peter is:
# <metanetcdf varname="ETRef" unit="m"  standard_name="Pot_reference_ET" long_name="Potential reference evapotranspiration rate"  title="CWATM" author="IIASA WAT" />

# each variable from the self.var.xlsx file is added to this xml file

# First lines:
first_lines = "<CWATM>\n" + "# METADATA for NETCDF OUTPUT DATA\n\n" + \
              "# varname: name of the variable in the CWAT code\n" + \
              "# unit: unit of the varibale\n" + \
              "# long name# standard name\n\n" + \
              '# Time information\n' + '<metanetcdf varname="_daily"     time=": daily"/>\n' + \
              '<metanetcdf varname="_monthavg"  time=": monthly average"/>\n' + \
              '<metanetcdf varname="_monthend"  time=": last value of the month"/>\n' + \
              '<metanetcdf varname="_monthtot"  time=": monthly sum"/>\n' + \
              '<metanetcdf varname="_annualavg" time=": annual average"/>\n' + \
              '<metanetcdf varname="_annualend" time=": last value of the year"/>\n' + \
              '<metanetcdf varname="_annualtot" time=": annual sum"/>\n' + \
              '<metanetcdf varname="_totalavg"  time=": average over the whole time period"/>\n' + \
              '<metanetcdf varname="_totaltot"  time=": sum the whole time period"/>\n' + \
              '<metanetcdf varname="_totalend"  time=": last value of the whole time period"/>\n\n\n'

f = open('metaNetcdf_new.xml', 'w')
f.write(first_lines)
cnt = 0
for excel_name in var_name_in_excel:

    if var_name_in_excel[cnt][9:] in metaNetcdfVar:  # if the var is already in the previous xml file
        # using long_name already used
        txt_var = '<metanetcdf varname="' + var_name_in_excel[cnt][9:] + \
                  '" unit="' + var_unit_in_excel[cnt] + \
                  '"  standard_name="' + metaNetcdfVar[var_name_in_excel[cnt][9:]]['standard_name'] + \
                  '" long_name="' + metaNetcdfVar[var_name_in_excel[cnt][9:]]['long_name'] + \
                  '" description="' + var_description_in_excel[cnt] + \
                  '"  title="CWATM" author="IIASA WAT" />'

    else:
        txt_var = '<metanetcdf varname="' + var_name_in_excel[cnt][9:] + \
                  '" unit="' + var_unit_in_excel[cnt] + \
                  '"  standard_name="' + var_standardname_in_excel[cnt] + \
                  '" long_name="' + '' + \
                  '" description="' + var_description_in_excel[cnt] + \
                  '"  title="CWATM" author="IIASA WAT" />'

    f.write(txt_var)
    f.write('\n')  # Go to the line after each variable
    cnt += 1
f.write('</CWATM>')
f.close()
