# -*- coding: utf-8 -*-
"""
Created on Tue Apr  7 15:13:10 2020

@author: Luca G.
"""
from builtins import isinstance

'''
Requires:

openpyxl
loguru

'''

import os
# PB added to sort the Dict_AllVariables
from collections import OrderedDict
from operator import getitem


from loguru import logger
import platform
import pandas as pd
import numpy as np
from xml.dom import minidom


base_folders = ['hydrological_modules', 
                'hydrological_modules/routing_reservoirs',
                'hydrological_modules/groundwater_modflow', 
                'hydrological_modules/water_demand', 
                'management_modules',
                '.'
                ]

xcols = ['Variable name', 
         'Long name',
        'Unit', 
        'Description', 
        'First module', 
        'Priority',
        'Module 1', 'Module 2', 'Module 3', 'Module 4', 
        'Module 5', 'Module 6', 'Module 7', 'Module 8', 
        'Module 9', 'Module 10', 'Module 11', 'Module 12', 
        'Module 13', 'Module 14', 'Module 15', 'Module 16'
        ]


netxml_head= "<CWATM>\n" + "# METADATA for NETCDF OUTPUT DATA\n\n" + \
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

    
def open_workbook(wbook_file):
    '''
    Opens the argument workbook file using Excel under Windows operating system
    or LibreOffice Calc under Linux.
    
    @return:  0 if the operation was successfull, -1 if not.
    '''
    ret = 0    
    plt = platform.system()
    logger.info(f'Detected {plt} operating system.')
    logger.info(f'Closing the file can take up to a minute, wait until the message of successfully edited appears before pressing any key.')
    
    if(plt.lower() == 'windows'):
        #os.system(f'start EXCEL.EXE "{wbook_file}"')
        os.system(f'"{wbook_file}"')
    elif(plt.lower() == 'linux'):
        os.system(f'soffice "{wbook_file}"')
    elif(plt.lower() == 'darwin'):
        logger.warning('Sorry we do not support MacOS yet.')
    else:
        logger.warning('Unsupported operating system')
        ret = -1
    return ret


def scan_variables(folders):
    Dict_AllVariables = {}
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
    
    return Dict_AllVariables

         

### DEFINING TWO USEFULL FUNCTIONS ###

def extract_selfvar(module_name):
    """Extract all 'self.var.varname' defined in the module,
    module_name has to include the path.
    Return the list of this variables"""

    # Openning and closing the Python module
    logger.info("----> " + module_name)
    fichier = open(module_name, "r")
    aa = fichier.readlines()
    fichier.close()
    logger.info('Exploring : ' + module_name)
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

        # This needs to be repaired -- evaporation was not being searched properly
        # With this fix, captures evaporation variables

        if module_name == '../hydrological_modules/evaporation.py':
            test_comment = 0
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



def make_all_variables_df(Dict_AllVariables, df_cur):
    
    df_all_vars = dict(zip(xcols, [[] for i in range(0, len(xcols))]))
    df_cur['Description'] = df_cur['Description'].astype("string")
    for k, v in Dict_AllVariables.items():
        
        if(isinstance(v, dict)):
            var_name = k.replace('self.var.', '')
            df_all_vars['Variable name'].append(var_name)
            df_all_vars['Unit'].append('')
            df_all_vars['Description'].append(np.NaN)
            df_all_vars['Priority'].append(np.NaN)
            df_all_vars['Long name'].append(np.NaN)
            
            cnt = 1
            for kv, vv in v.items():
                if(kv == 'defined'):
                    df_all_vars['First module'].append(vv)
                else:
                    col = f'Module {cnt}'
                    df_all_vars[col].append(f'{kv}: {vv}')
                    
                    cnt+=1
                
            if(cnt < 16): #fill up Module n columns
                
                for i in range(cnt, 17):
                    col = f'Module {i}'
                    df_all_vars[col].append('')
                    
    
    df_all_vars = pd.DataFrame(df_all_vars) 


    drop_cols = [c + '_r' for c in xcols[1:]]
    df = df_all_vars.join(df_cur.set_index('Variable name'), rsuffix='_r', on = 'Variable name')
    df.reset_index(drop=True, inplace=True)

    #use if to maintain retro-compatibility with legacy excel files that do not have priority
    if('Priority' in list(df_cur.columns)):
        df['Priority'] = df['Priority_r']
    else:
        drop_cols.remove('Priority_r')    
        
    if('Long name' in list(df_cur.columns)):
        df['Long name'] = df['Long name_r']
    else:
        drop_cols.remove('Long name_r') 

    df_new = df[df['Description_r'].isnull()].copy(deep=True)
    df_old = df[~df['Description_r'].isnull()].copy(deep=True)
    df_old['Description'] = df_old['Description_r']
    df_old['Unit'] = df_old['Unit_r']

        
    df_new_old = pd.concat([df_new, df_old], ignore_index=True)
    #print(df_new_old.columns)
   
    #print(drop_cols)
    df_new_old.drop(columns=drop_cols, index = 1, inplace=True)
    mask = df_new_old['Priority'].isnull()
    df_new_old['Priority'] = np.where(mask, 'low', df_new_old['Priority'])    

    mask = df_new_old['Long name'].isnull()
    df_new_old['Long name'] = np.where(mask, '', df_new_old['Long name'])   
    
    return df_new_old

def write_new_excel(wbook_file, df_new_old):
    with pd.ExcelWriter(wbook_file) as writer:
        df_new_old.to_excel(writer, sheet_name='variables', index = False)
        logger.info(f'{wbook_file} file with all variables saved.')    
        
    print('Press enter to open and edit the excel file with the variable. Once edited, save it and close to continue the variables documentation process')
    
    wbook_edited = open_workbook(wbook_file = wbook_file)
    if(wbook_edited == 0):
        logger.info(f'{wbook_file} successfully edited')
    else:
        logger.warning(f'{wbook_file} was not edited')    
    
    
    #make one sheet for all priority levels
    df = pd.read_excel(wbook_file, 'variables')
    prio_levels = list(df['Priority'].unique())
    
    with pd.ExcelWriter(wbook_file) as writer:
        df.to_excel(writer, sheet_name='variables', index = False)   
        
        for l in prio_levels:
            df_l = df[df['Priority'] == l] 
            df_l.to_excel(writer, sheet_name=l, index = False)     
    
    
    return 0
    
def write_to_metaNetCdf(df_new_old, netxml_file):
        
    metaNetcdfVar = {}
    user_opt = 'c'
    #load existing info if file exists
    if(os.path.isfile(netxml_file) == True):
    
        # open the metanetcdf file
        try:
            metaparse = minidom.parse(netxml_file)
            meta = metaparse.getElementsByTagName("CWATM")[0]
            for metavar in meta.getElementsByTagName("metanetcdf"):
                d = {}
                for key in list(metavar.attributes.keys()):
                    if key != 'varname':
                        d[key] = metavar.attributes[key].value
                key = metavar.attributes['varname'].value
                metaNetcdfVar[key] = d   
        except Exception as e:
            logger.error(f'An error occured while trying to read the {netxml_file} file') 
            logger.error(e) 
            user_opt = input('Press "c" to create a new empty file or "a" to abort the execution.')
        
        finally:
            if(user_opt == 'a'):
                exit()
        
    
    with open(netxml_file, 'w') as f:
        f.writelines(netxml_head) 
        
        for _index, row in df_new_old.iterrows():
            var_name = row['Variable name']
            long_name = row['Long name']
            unt = row['Unit']
            if(unt=='°C'):
                unt= 'C'
            des = row['Description']
            if(isinstance(des, pd._libs.missing.NAType)):
                des = ''
            standard_name = ''
            
            if(var_name in metaNetcdfVar.keys()):
                standar_name = metaNetcdfVar[var_name]['standard_name']

                
                
            line = f'<metanetcdf varname="{var_name}" unit="{unt}"  standard_name="{standard_name}" long_name="{long_name}" description="{des}"  title="CWATM" author="IIASA WAT" />\n'
            f.write(line)
            
        f.write('</CWATM>')
            
    
    
    return 0



def get_vars_modules_descriptor(df_new_old):
    dict_new_old = {}
    
    for _index, row in df_new_old.iterrows():
        var_name = row['Variable name']
        uom = row['Unit']
        descr = row['Description']
        dict_new_old[var_name] = {'Description': descr, 'Unit': uom}
    return dict_new_old
    

if __name__ == '__main__':
          
    folders = ['../' + f for f in base_folders]
    Dict_AllVariables =  scan_variables(folders) # Keys are variable name : then 1rst module and associated line
    kn = len(Dict_AllVariables.keys())
    logger.info(f'Found {kn} variables.')
    
    #get variables in previous xcel
    wbook_file = input("Enter the excel file name where the variables names and attributes are stored or press any key to accept the default name (selfvar.xlsx).\nIf the file does not exist, it will be created else overwritten.\n")
    
    if(len(wbook_file) < 2):            
        wbook_file = 'selfvar.xlsx' #set default if any key pressed
    if('xlsx' not in wbook_file):
        wbook_file += '.xlsx'
        
    #create file if not existing
    if(os.path.isfile(wbook_file) == False):
        df = pd.DataFrame(columns=xcols)
        df = pd.DataFrame(df)
        with pd.ExcelWriter(wbook_file) as writer:
            df.to_excel(writer, sheet_name='variables', index = False)
            logger.info(f'{wbook_file} file created.')
            
            
    #find all the variables not included in the current documentation
    df_cur = pd.read_excel(wbook_file, sheet_name = 'variables')
    all_vars = list(Dict_AllVariables.keys())
    all_vars_names = [k.replace('self.var.', '') for k in all_vars] #all variables names read from the code
    df_all_names = pd.DataFrame({'vars': all_vars, 'var_names': all_vars_names})
    df_new = df_all_names[~df_all_names['var_names'].isin(df_cur['Variable name'])  ]
    n_nw = len(df_new.index)
    logger.info(f'Found {n_nw} new variables.')
    
    #print(df_new.head(100))
    #create a dataframe with all variables and save it to excel
    df_new_old = make_all_variables_df(Dict_AllVariables, df_cur)
    
    #write new excel with al variables and a worksheet for each priority level
    write_new_excel(wbook_file, df_new_old)



    netxml_file = input("Enter the xml file name where the variables NetCDF4 metadata will be stored or press any key to accept the default name (metaNetcdf.xml).\nIf the file does not exist, it will be created else overwritten.\n")
    
    if(len(netxml_file) < 2):            
        netxml_file = 'metaNetcdf.xml' #set default if any key pressed
    if('xml' not in netxml_file):
        netxml_file += '.xml'
        
    write_to_metaNetCdf(df_new_old, netxml_file)
    
    
    
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
                        if python_modules[ll][:-3] == keys:  # we search the module where we want to add information
                            var_name_in_module.append(
                                var_name)  # This list contains all var_name appearing in this module

                if len(var_name_in_module) > 0:

                    ## Now, we modify the Python module to add self.var description
                    logger.info("=== " + filename_to_modify)
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
                    #put variable names: {description, units} in a dictionary
                    dict_new_old = get_vars_modules_descriptor(df_new_old)
                    for vv in var_name_in_module:
                        list_modules = ""
                        v_name = vv.replace('self.var.','')
                        if(v_name in dict_new_old.keys()):
                            ds_um = dict_new_old[v_name]
                            descr = ds_um['Description']
                            uim = ds_um['Unit']
                            
                            if(isinstance(descr, str) == False):
                                descr = ''
                            if(isinstance(uim, str) == False or uim == '-' or len(uim)==0):
                                uim = '--'

                        added_description = added_description + lead + '{:{x}.{x}}'.format(vv[9:],
                                                                                           x=col1) + between + '{:{x}.{x}}'.format(
                            descr, x=col2) + between + \
                                            '{:{x}.{x}}'.format(uim, x=col3) + "\n"

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
                    
    print('Process completed.')
