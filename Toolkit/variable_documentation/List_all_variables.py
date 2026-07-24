# -*- coding: utf-8 -*-
"""
CWatM Variable Documentation Generator

This program automatically scans CWatM (Community Water Model) Python modules to extract,
document, and maintain variable definitions used throughout the hydrological modeling system.

Main Functionality:
- Scans Python files in specified folders to find all 'self.var' variable references
- Tracks variable definitions vs. usage across different modules  
- Creates comprehensive Excel documentation with variable descriptions, units, and priorities
- Generates NetCDF metadata XML files for model output variables
- Automatically injects variable documentation tables into Python module docstrings

The program helps maintain consistent variable documentation across the entire CWatM codebase
by providing a centralized system for tracking and documenting model variables. It supports
interactive editing workflows where users can manually update variable descriptions and
metadata through Excel files.

Output Files:
- Excel workbooks with variable documentation (default: selfvar.xlsx)
- NetCDF metadata XML files (default: metaNetcdf.xml)
- Updated Python module files with embedded variable documentation tables

Created on Tue Apr  7 15:13:10 2020
@author: Luca G., Peter B.
"""

'''
Requires:
openpyxl
loguru

'''

import argparse
import os
import platform
import re
import time
# PB added to sort the Dict_AllVariables
from collections import OrderedDict, Counter
from operator import getitem
from xml.dom import minidom

import numpy as np
import pandas as pd
from loguru import logger


base_folders = [
    'hydrological_modules',
    'hydrological_modules/routing_reservoirs',
    'hydrological_modules/groundwater_modflow',
    'hydrological_modules/water_demand',
    'management_modules',
    '.'
]

xcols = [
    'Variable name',
    'Long name',
    'Unit',
    'Description',
    'Type',
    'Dimension',
    'Optional',
    'First module',
    'Priority',
    'Module 1', 'Module 2', 'Module 3', 'Module 4',
    'Module 5', 'Module 6', 'Module 7', 'Module 8',
    'Module 9', 'Module 10', 'Module 11', 'Module 12',
    'Module 13', 'Module 14', 'Module 15', 'Module 16'
]


netxml_head = (
    "<CWATM>\n" +
    "# METADATA for NETCDF OUTPUT DATA\n\n" +
    "# varname: name of the variable in the CWAT code\n" +
    "# unit: unit of the varibale\n" +
    "# long name# standard name\n\n" +
    '# Time information\n' +
    '<metanetcdf varname="_daily"     time=": daily"/>\n' +
    '<metanetcdf varname="_monthavg"  time=": monthly average"/>\n' +
    '<metanetcdf varname="_monthend"  time=": last value of the month"/>\n' +
    '<metanetcdf varname="_monthtot"  time=": monthly sum"/>\n' +
    '<metanetcdf varname="_annualavg" time=": annual average"/>\n' +
    '<metanetcdf varname="_annualend" time=": last value of the year"/>\n' +
    '<metanetcdf varname="_annualtot" time=": annual sum"/>\n' +
    '<metanetcdf varname="_totalavg"  time=": average over the whole time period"/>\n' +
    '<metanetcdf varname="_totaltot"  time=": sum the whole time period"/>\n' +
    '<metanetcdf varname="_totalend"  time=": last value of the whole time period"/>\n\n\n'
)


def open_workbook(wbook_file):
    """
    Open the workbook file using the system's default spreadsheet application.
    
    Opens the argument workbook file using Excel under Windows operating system
    or LibreOffice Calc under Linux. MacOS is not currently supported.
    
    Parameters
    ----------
    wbook_file : str
        Path to the workbook file to be opened.
    
    Returns
    -------
    int
        0 if the operation was successful, -1 if not supported or failed.
        
    Notes
    -----
    The function automatically detects the operating system and uses the 
    appropriate application. On Windows, it uses the default Excel application.
    On Linux, it uses LibreOffice Calc (soffice).
    """
    ret = 0
    plt = platform.system()
    logger.info(f'Detected {plt} operating system.')
    logger.info(
        f'Closing the file can take up to a minute, wait until the message of successfully edited appears '
        'before pressing any key.'
    )
    
    if plt.lower() == 'windows':
        # os.system(f'start EXCEL.EXE "{wbook_file}"')
        os.system(f'"{wbook_file}"')
    elif plt.lower() == 'linux':
        os.system(f'soffice "{wbook_file}"')
    elif plt.lower() == 'darwin':
        logger.warning('Sorry we do not support MacOS yet.')
    else:
        logger.warning('Unsupported operating system')
        ret = -1
    return ret


def collect_option_names(folders):
    """
    Collect the names of all settings-file [OPTIONS] used anywhere in the code.

    An option name is recognized when it appears as checkOption('name'), as
    'name' in option, or as returnBool('name'). The latter covers boolean
    settings flags that are not listed in the [OPTIONS] section (e.g. useHuss,
    albedo, snowmelt_radiation, includeOnlyGlaciersMelt). The resulting set is
    used to also recognize option flags that are stored in self.var
    (e.g. self.var.includeGlaciers, self.var.snowmelt_radiation).

    Parameters
    ----------
    folders : list of str
        List of folder paths to scan for Python modules.

    Returns
    -------
    set of str
        All option names found in the code.
    """
    pat_checkoption = re.compile(r'checkOption\(\s*[\'"](\w+)[\'"]')
    pat_in_option = re.compile(r'[\'"](\w+)[\'"]\s+in\s+option\b')
    pat_returnbool = re.compile(r'returnBool\(\s*[\'"](\w+)[\'"]')
    names = set()
    for path in folders:
        for fn in os.listdir(str(path)):
            if fn.endswith('py'):
                with open(os.path.join(str(path), fn), 'r', encoding='utf-8',
                          errors='surrogateescape') as f:
                    txt = f.read()
                names.update(pat_checkoption.findall(txt))
                names.update(pat_in_option.findall(txt))
                names.update(pat_returnbool.findall(txt))
    return names


def options_in_condition(condition, known_options):
    """
    Extract the option names an if/elif condition depends on.

    Recognizes checkOption('name'), returnBool('name') and self.var.name (if name
    is a known option). Negated checks ('not checkOption(...)', 'not self.var.x')
    are ignored, because the guarded block runs when the option is switched OFF.

    Parameters
    ----------
    condition : str
        The stripped source line of the if/elif statement.
    known_options : set of str
        All known option names (from collect_option_names).

    Returns
    -------
    set of str
        The option names the condition requires to be True.
    """
    opts = set()
    for m in re.finditer(r'checkOption\(\s*[\'"](\w+)[\'"]', condition):
        if condition[max(0, m.start() - 4):m.start()] != 'not ':
            opts.add(m.group(1))
    for m in re.finditer(r'returnBool\(\s*[\'"](\w+)[\'"]', condition):
        if condition[max(0, m.start() - 4):m.start()] != 'not ':
            opts.add(m.group(1))
    for m in re.finditer(r'self\.var\.(\w+)', condition):
        if m.group(1) in known_options and condition[max(0, m.start() - 4):m.start()] != 'not ':
            opts.add(m.group(1))
    return opts


def scan_variables(folders):
    """
    Scan Python modules in specified folders to extract self.var variables.
    
    Recursively searches through Python files in the given folders to identify and 
    catalog all self.var variables, tracking their definitions and usage across modules.
    
    Parameters
    ----------
    folders : list of str
        List of folder paths to scan for Python modules.
    
    Returns
    -------
    collections.OrderedDict
        Ordered dictionary mapping variable names to dictionaries containing:
        - Module names as keys with line information as values
        - 'defined' key mapping to the module where the variable is first defined
        Variables are sorted by their defining module.
        
    Notes
    -----
    The function scans all .py files (except List_all_variables.py) in the specified
    folders. For each variable found, it tracks:
    - Which modules define vs. use the variable
    - Line numbers where variables appear
    - The first module that defines each variable
    """

    Dict_AllVariables = {}
    var_def = {}
    # options needed by a variable: intersection over its definition sites -- a variable
    # that is also defined somewhere unconditionally does not need any option
    def_options = {}
    use_options = {}
    known_options = collect_option_names(folders)
    logger.info(f'Found {len(known_options)} settings options used in the code.')
    for folders_paths in folders:
        path = str(folders_paths)
        python_modules = os.listdir(path)
        for ll in range(len(python_modules)):
            # if the file is a Python module
            if python_modules[ll][-2:] == 'py' and python_modules[ll][-2:] != 'List_all_variables':
                [variable_names_list, associated_line, first_definition, associated_options] = extract_selfvar(
                    path + '/' + python_modules[ll], known_options)
                for ii in range(len(variable_names_list)):  # For each variable
                    vname = variable_names_list[ii]
                    if first_definition[ii] == 1:
                        txt_line = 'defined line ' + str(associated_line[ii])
                        var_def[vname] = python_modules[ll][:-3]
                        def_options[vname] = (associated_options[ii] if vname not in def_options
                                              else def_options[vname] & associated_options[ii])
                    else:
                        txt_line = 'used line ' + str(associated_line[ii])
                        use_options[vname] = (associated_options[ii] if vname not in use_options
                                              else use_options[vname] & associated_options[ii])
    
                    name_module_python = python_modules[ll][:-3]  # to go to the line when saving
                    # if the self.var is not already defined
                    if variable_names_list[ii] not in Dict_AllVariables:
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

    # options per variable: from the definition sites; if a variable is only used
    # (never defined at a line start), fall back to the options of its use sites
    var_options = {}
    for vname in Dict_AllVariables:
        var_options[vname] = def_options.get(vname, use_options.get(vname, frozenset()))

    return Dict_AllVariables, var_options


def extract_selfvar(module_name, known_options=None):
    """
    Extract all 'self.var.varname' variables defined in a Python module.

    Parses a Python module file to find all instances of self.var variables,
    tracking their line numbers and whether they represent definitions or usage.
    Handles comment blocks and special cases for the evaporation module.

    Parameters
    ----------
    module_name : str
        Full path to the Python module file to analyze.
    known_options : set of str, optional
        All known settings [OPTIONS] names. If given, the function also tracks
        which options guard each occurrence (via enclosing if checkOption('x') or
        if self.var.x blocks, detected by indentation).

    Returns
    -------
    tuple of (list, list, list, list)
        A tuple containing:
        - variable_names_list : list of str
            Names of all self.var variables found (e.g., 'self.var.temperature')
        - associated_line : list of int
            Line numbers where each variable appears (1-indexed)
        - first_definition : list of int
            1 if variable is defined/updated on this line, 0 if only used
        - associated_options : list of frozenset
            The settings options that guard each occurrence (empty if unguarded)

    Notes
    -----
    The function performs several parsing steps:
    - Removes comments and handles multi-line docstrings
    - Special handling for evaporation.py module
    - Identifies variable boundaries using delimiters
    - Distinguishes between variable definitions (line start) and usage

    Variable names are extracted by finding 'self.var' patterns and determining
    their boundaries using common Python delimiters like operators, parentheses,
    and method calls.
    """

    # Openning and closing the Python module
    logger.info("----> " + module_name)
    fichier = open(module_name, "r", encoding='utf-8', errors='surrogateescape')
    aa = fichier.readlines()
    fichier.close()
    logger.info('Exploring : ' + module_name)
    variable_names_list = []
    associated_line = []  # Line where the module appears
    first_definition = []  # 1 if defined or updated, zero if only used
    associated_options = []  # settings options guarding each occurrence
    option_stack = []  # stack of (indent, set of options) of enclosing if-blocks
    test_comment = 0
    for ii in range(len(aa)):  # for each line in the Python code
        bb = aa[ii]
        indent = len(bb) - len(bb.lstrip())  # indentation of the original line
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

        if os.path.basename(module_name) == 'evaporation.py':
            test_comment = 0
        # deleted the lines to detect #
        if test_comment == 0:
            # track which settings options guard the current line: an if/elif block with
            # checkOption('x') or self.var.x (x being a known option) puts x on the stack;
            # leaving the block (indentation) removes it again
            code_line = bb.strip()
            if code_line and known_options is not None:
                while option_stack and indent <= option_stack[-1][0]:
                    option_stack.pop()
                if code_line.startswith('if ') or code_line.startswith('elif '):
                    opts = options_in_condition(code_line, known_options)
                    if opts:
                        option_stack.append((indent, opts))

            indexselfvar = 0
            idselfvar = 0
            while indexselfvar != -1:
                bb_temp = bb[idselfvar:]
                indexselfvar = bb_temp.find("self.var")  # Find all self.var position in the line

                if indexselfvar != -1:  # there is at least one self.var in the line
                    # PB change to +1 and to ww=len(bb_temp) because some variable lost last letter
                    for ww in range(indexselfvar, len(bb_temp) + 1):
                        if (ww == len(bb_temp) or bb_temp[ww] in ':,() =*+-/[]"' or
                                bb_temp[ww:ww + 5] in ['.appe', '.copy', '.ravel'] or bb_temp[ww] in '<>' or
                                bb_temp[ww:ww + 7] == '.astype'):  # Find the end of the var name
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
                            # options of all enclosing if-blocks guard this occurrence
                            active = frozenset().union(*(s for _i, s in option_stack)) \
                                if option_stack else frozenset()
                            associated_options.append(active)
                            if indexselfvar == 0:  # if 'self.var' is at the beginning of the line
                                first_definition.append(1)
                            else:
                                first_definition.append(0)
                    idselfvar = idselfvar + indexselfvar + 1

    return variable_names_list, associated_line, first_definition, associated_options


# tokens in a size expression that stand for the number of active grid cells
_CELL_REFS = ('inzero', 'mapc', 'maskinfo', 'ncells', 'decompress', 'maskall')


def _balanced(s, open_pos):
    """Return the index of the bracket matching the opening bracket at s[open_pos], or -1."""
    depth = 0
    for i in range(open_pos, len(s)):
        if s[i] in '([{':
            depth += 1
        elif s[i] in ')]}':
            depth -= 1
            if depth == 0:
                return i
    return -1


def _split_top(s):
    """Split a string on top-level commas (ignoring commas inside brackets)."""
    parts, depth, cur = [], 0, ''
    for ch in s:
        if ch in '([{':
            depth += 1
            cur += ch
        elif ch in ')]}':
            depth -= 1
            cur += ch
        elif ch == ',' and depth == 0:
            parts.append(cur)
            cur = ''
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def _size_token(tok):
    """
    Map one element of a shape/reps tuple to a compact size string.

    A reference to the compressed grid (globals.inZero, maskinfo['mapC'], ...)
    becomes 'N'; an integer literal is kept; a plain symbol (e.g. a counter such
    as 'max') is kept; anything more complex becomes '?'.
    """
    tok = tok.strip()
    low = tok.lower()
    if any(r in low for r in _CELL_REFS):
        return 'N'
    if re.fullmatch(r'\d+', tok):
        return tok
    sym = tok.replace('self.var.', '').strip()
    if re.fullmatch(r'\w+', sym):
        return sym
    return '?'


def infer_dim_from_rhs(rhs):
    """
    Infer an array dimension string from the right-hand side of an assignment.

    Recognizes the common CWatM array-creation idioms so that a variable's
    dimension can be derived statically from the code, without running the model.
    Returns None when the RHS does not match a known array-creation pattern
    (e.g. a scalar or an arithmetic combination of other variables).

    Examples
    --------
    ``np.zeros((4, 13, len(globals.inZero)))`` -> ``'3D (4, 13, N)'``
    ``np.zeros((2, len(globals.inZero)))``     -> ``'2D (2, N)'``
    ``np.tile(1 + globals.inZero, (4, 1))``    -> ``'2D (4, N)'``
    ``globals.inZero.copy()`` / ``loadmap(...)`` / ``readnetcdf2(...)`` -> ``'1D (N)'``
    """
    rhs = rhs.strip()

    # numpy array constructors with an explicit shape as the first argument
    m = re.match(r'(?:np|numpy)\.(?:zeros|ones|empty|full)\s*\(', rhs)
    if m:
        close = _balanced(rhs, m.end() - 1)
        if close == -1:  # unbalanced (e.g. assignment continues on the next line): skip
            return None
        args = _split_top(rhs[m.end():close])
        if not args:
            return None
        shape = args[0]
        toks = _split_top(shape[1:-1]) if shape.startswith('(') else [shape]
        if not toks:
            return None
        mapped = [_size_token(t) for t in toks]
        return f"{len(mapped)}D ({', '.join(mapped)})"

    # np.tile(base, (reps..., 1)): the base is a 1D cell array, the last rep tiles it
    m = re.match(r'(?:np|numpy)\.tile\s*\(', rhs)
    if m:
        close = _balanced(rhs, m.end() - 1)
        if close == -1:
            return None
        args = _split_top(rhs[m.end():close])
        if len(args) >= 2 and args[1].startswith('('):
            reps = _split_top(args[1][1:-1])
            if reps:
                mapped = [_size_token(t) for t in reps]
                mapped[-1] = 'N'  # base's cell axis
                return f"{len(mapped)}D ({', '.join(mapped)})"
        return None

    # 1D-over-cells idioms: anything built from globals.inZero, a map read from disk,
    # or a restored initial state is a 1D array over the active grid cells
    if 'globals.inZero' in rhs:
        return '1D (N)'
    if re.match(r'(loadmap|readnetcdf\w*|self\.var\.load)\s*\(', rhs):
        return '1D (N)'
    return None


def infer_dimensions_from_code(folders):
    """
    Derive array dimensions statically from the source code.

    Scans every ``self.var.x = <expr>`` definition in the given folders and infers
    the dimension of ``x`` from the creation idiom on the right-hand side (see
    infer_dim_from_rhs). This is the fallback for variables that cannot be measured
    at runtime because their module is switched off in the settings file.

    Parameters
    ----------
    folders : list of str
        Folder paths to scan for Python modules.

    Returns
    -------
    dict
        Mapping variable name -> dimension string (e.g. '1D (N)', '2D (4, N)').
        A variable defined several times keeps the richest inference (the one with
        the most dimensions; ties are broken by the most frequent).
    """
    pat = re.compile(r'^\s*self\.var\.(\w+)\s*=\s*(.+?)\s*$')
    candidates = {}
    for path in folders:
        for fn in os.listdir(str(path)):
            if not fn.endswith('py'):
                continue
            with open(os.path.join(str(path), fn), 'r', encoding='utf-8',
                      errors='surrogateescape') as f:
                for line in f:
                    code = line.split('#', 1)[0]  # drop line comments (line-based, like the rest)
                    m = pat.match(code)
                    if not m:
                        continue
                    dim = infer_dim_from_rhs(m.group(2))
                    if dim:
                        candidates.setdefault(m.group(1), []).append(dim)

    def _ndim(d):
        mm = re.match(r'(\d+)D', d)
        return int(mm.group(1)) if mm else 1

    result = {}
    for name, dims in candidates.items():
        best = max(_ndim(d) for d in dims)
        rich = [d for d in dims if _ndim(d) == best]
        result[name] = Counter(rich).most_common(1)[0][0]
    logger.info(f'Inferred dimensions of {len(result)} variables statically from the code.')
    return result


def _xml_safe(text):
    """
    Remove characters that are invalid in an XML attribute value / unwanted in a
    description: '&' becomes 'and', and the quote and angle-bracket characters
    (" ' < >) are dropped. Whitespace runs left by the removals are collapsed.
    """
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ''
    s = str(text).replace('&', 'and')
    for ch in '"\'<>':
        s = s.replace(ch, '')
    return re.sub(r'\s{2,}', ' ', s).strip()


def _clean_comment(text):
    """
    Turn a raw source comment into a usable variable description, or None.

    Strips the leading '#', drops comments that are not descriptions -- separator
    banners, author/TODO tags, commented-out code (anything with a function call or
    a self. reference or a leading keyword), and bare unit notes such as 'in m/day'.
    Returns None when nothing description-like remains.
    """
    text = text.strip().lstrip('#').strip()
    if not text:
        return None
    # separator banners: ----, ====, ****, ####, ////
    if re.fullmatch(r'[-=*_#~/ ]+', text):
        return None
    # header / author / change tags
    if re.match(r'(TODO|FIXME|XXX|HACK|PB|NOTE|Author|Purpose|Name|Created|Modified|Copyright)\b',
                text, re.I):
        return None
    # commented-out code: a self. reference, a function call, or a leading keyword
    if 'self.' in text or re.search(r'\b\w+\(', text):
        return None
    if re.match(r'(def|class|import|from|for|while|if|elif|else|try|except|return|print|with|lambda)\b',
                text):
        return None
    # a bare unit note like 'in m/day' or 'in m2'
    if re.match(r'in\s+\[?[\w/.²°^*\-+ ]+\]?$', text) and len(text.split()) <= 4:
        return None
    # require a couple of words and letters to count as a description
    if len(re.findall(r'[A-Za-z]', text)) < 4 or len(text.split()) < 2:
        return None
    return text[:150].rsplit(' ', 1)[0] if len(text) > 150 else text


def _comment_block(lines, start, step):
    """Collect the contiguous run of descriptive comment lines from start, moving by step."""
    parts = []
    j = start
    while 0 <= j < len(lines) and lines[j].lstrip().startswith('#'):
        c = _clean_comment(lines[j])
        if c is None:  # stop at the first non-descriptive comment: keep the block tight
            break
        parts.append(c)
        j += step
    if step < 0:
        parts.reverse()
    return ' '.join(parts) if parts else None


def infer_descriptions_from_code(folders):
    """
    Extract a best-effort description for each variable from nearby source comments.

    For every ``self.var.x = ...`` definition the function looks at the comment block
    directly above, the inline comment on the same line, and the comment block directly
    below, and keeps the best candidate (block above preferred, then inline, then below).
    Commented-out code, separators, author/TODO tags and bare units are ignored.

    Parameters
    ----------
    folders : list of str
        Folder paths to scan for Python modules.

    Returns
    -------
    dict
        Mapping variable name -> extracted description text (without any marker).
        The caller appends a ' (AI)' marker when it uses one of these to fill an
        otherwise empty description.
    """
    def_pat = re.compile(r'^\s*self\.var\.(\w+)\s*(?:=|\+=|-=|\*=|/=)[^=]')
    candidates = {}  # name -> list of (priority, text); lower priority = better
    for path in folders:
        for fn in os.listdir(str(path)):
            if not fn.endswith('py'):
                continue
            with open(os.path.join(str(path), fn), 'r', encoding='utf-8',
                      errors='surrogateescape') as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                m = def_pat.match(line)
                if not m:
                    continue
                name = m.group(1)
                above = _comment_block(lines, i - 1, -1)
                below = _comment_block(lines, i + 1, 1)
                hash_pos = line.find('#')
                inline = _clean_comment(line[hash_pos:]) if hash_pos != -1 else None
                for pr, txt in ((0, above), (1, inline), (2, below)):
                    if txt:
                        candidates.setdefault(name, []).append((pr, txt))

    result = {}
    for name, cands in candidates.items():
        cands.sort(key=lambda pt: (pt[0], -len(pt[1])))  # best priority, then longest
        result[name] = cands[0][1]
    logger.info(f'Extracted candidate descriptions for {len(result)} variables from code comments.')
    return result


def measure_dimensions(settings_file, root_dir):
    """
    Run CWatM for a single time step and measure the dimension of every self.var variable.

    Imports the CWatM model from root_dir, initializes it with the given settings file,
    runs exactly one time step and then inspects every attribute of the variable
    container to determine its dimensionality and shape.

    Parameters
    ----------
    settings_file : str
        Path to a working CWatM settings (.ini) file. The paths inside it must be
        valid on this machine; the model is initialized with it.
    root_dir : str
        Root directory of the CWatM code (folder containing hydrological_modules);
        its parent is put on sys.path so the cwatm package can be imported.

    Returns
    -------
    dict
        Mapping variable name -> dimension string, e.g.
        '1D (N)' for a 1d array over the active grid cells,
        '2D (6, N)' for a 2d array (e.g. per land cover fraction),
        'list (12)' for a list/tuple with 12 entries,
        'scalar' for 0d numpy values.

    Notes
    -----
    The number of active grid cells depends on the basin of the settings file, but it
    is replaced by the placeholder 'N' in the output, so the resulting dimension
    strings are settings-independent: any working settings file gives the same result.
    Only variables of modules that are switched off in the settings (e.g. modflow)
    cannot be measured and keep their previous Dimension value.
    """
    import sys
    pkg_parent = os.path.dirname(os.path.abspath(root_dir))
    if pkg_parent not in sys.path:
        sys.path.insert(0, pkg_parent)

    from cwatm.management_modules.configuration import (parse_configuration, read_metanetcdf,
                                                        dateVar, settingsfile)
    from cwatm.management_modules.data_handling import Flags, cbinding
    from cwatm.management_modules.globals import outTss, outMap
    from cwatm.management_modules.timestep import checkifDate
    from cwatm.management_modules.dynamicModel import ModelFrame
    from cwatm.run_cwatm import headerinfo
    from cwatm.cwatm_model import CWATModel

    logger.info(f'Running CWatM for one time step with {settings_file} to measure variable dimensions ...')
    Flags['veryquiet'] = True
    settingsfile.append(settings_file)  # global used e.g. in output file headers and error messages
    headerinfo()  # initializes the versioning info used when loading input files
    parse_configuration(settings_file)
    # switch off all time series and map output: not needed for measuring dimensions,
    # avoids writing output files as a side effect and skips output-related errors
    outTss.clear()
    outMap.clear()
    read_metanetcdf('metaNetcdf.xml')
    checkifDate('StepStart', 'StepEnd', 'SpinUp', cbinding('PrecipitationMaps'))
    dateVar['intEnd'] = dateVar['intStart']  # one time step is enough

    model = CWATModel()
    ModelFrame(model, firstTimestep=dateVar['intStart'], lastTimeStep=dateVar['intEnd']).run()

    # determine the number of active grid cells (the size of the compressed 1D maps):
    # it is the by far most common array size. Writing the placeholder 'N' instead of
    # the number makes the dimension info settings-independent -- the structure of a
    # variable is the same in every basin, only the cell count changes.
    sizes = [v.shape[-1] for v in vars(model.var).values()
             if isinstance(v, np.ndarray) and v.ndim >= 1]
    ncells = Counter(sizes).most_common(1)[0][0] if sizes else -1

    dims = {}
    for name, val in vars(model.var).items():
        if isinstance(val, np.ndarray):
            if val.ndim == 0:
                dims[name] = 'scalar'
            else:
                shape = ['N' if s == ncells else str(s) for s in val.shape]
                dims[name] = f"{val.ndim}D ({', '.join(shape)})"
        elif isinstance(val, (list, tuple)):
            dims[name] = f'list ({len(val)})'
    logger.info(f'Measured dimensions of {len(dims)} variables (N = {ncells} cells).')
    return dims


def make_all_variables_df(Dict_AllVariables, df_cur, var_options=None):
    """
    Create a comprehensive DataFrame of all variables by merging discovered and existing data.
    
    Combines newly discovered variables from code analysis with existing variable
    documentation, handling priorities, descriptions, and module information.
    
    Parameters
    ----------
    Dict_AllVariables : dict
        Dictionary mapping variable names to their module usage information.
        Created by scan_variables().
    df_cur : pandas.DataFrame
        Current variable documentation DataFrame with existing descriptions,
        units, and other metadata.
        
    Returns
    -------
    pandas.DataFrame
        Comprehensive DataFrame containing all variables with columns:
        - Variable name, Long name, Unit, Description, Type, Priority
        - First module (where variable is first defined)  
        - Module 1-16 columns showing usage across modules
        New variables get default priority 'low' and empty descriptions.
        
    Notes
    -----
    The function performs several operations:
    - Merges new variables with existing documentation
    - Maintains backward compatibility with legacy Excel files
    - Type can be Array, List, Number or Flag (False/True)
    - Handles missing Priority and Long name columns
    - Sets default values for new variables (priority='low')
    - Preserves existing descriptions and units where available
    
    The resulting DataFrame is structured to match the Excel output format
    with separate columns for each module where variables are used.
    
    """
    df_all_vars = dict(zip(xcols, [[] for i in range(0, len(xcols))]))
    df_cur['Description'] = df_cur['Description'].astype("string")
    df_cur['Type'] = df_cur['Type'].astype("string")
    for k, v in Dict_AllVariables.items():
        if isinstance(v, dict):
            var_name = k.replace('self.var.', '')
            df_all_vars['Variable name'].append(var_name)
            df_all_vars['Unit'].append('')
            df_all_vars['Description'].append(np.nan)
            df_all_vars['Type'].append(np.nan)
            df_all_vars['Dimension'].append(np.nan)
            # Optional is always refreshed from the code scan, never taken from the excel
            opts = var_options.get(k, frozenset()) if var_options else frozenset()
            df_all_vars['Optional'].append(';'.join(sorted(opts)))
            df_all_vars['Priority'].append(np.nan)
            df_all_vars['Long name'].append(np.nan)
            cnt = 1
            for kv, vv in v.items():
                if kv == 'defined':
                    df_all_vars['First module'].append(vv)
                elif cnt <= 16:
                    col = f'Module {cnt}'
                    df_all_vars[col].append(f'{kv}: {vv}')
                    cnt += 1
                else:
                    logger.warning(f'{var_name}: used in more than 16 modules, '
                                   f'"{kv}" does not fit in the Module columns')
            for i in range(cnt, 17):  # fill up remaining Module n columns
                df_all_vars[f'Module {i}'].append('')

    df_all_vars = pd.DataFrame(df_all_vars)

    drop_cols = [c + '_r' for c in xcols[1:]]
    df = df_all_vars.join(df_cur.set_index('Variable name'), rsuffix='_r', on='Variable name')
    df.reset_index(drop=True, inplace=True)

    # use if to maintain retro-compatibility with legacy excel files that do not have priority
    if 'Priority' in list(df_cur.columns):
        df['Priority'] = df['Priority_r']
    else:
        drop_cols.remove('Priority_r')

    if 'Type' in list(df_cur.columns):
        df['Type'] = df['Type_r']
    else:
        drop_cols.remove('Type_r')

    if 'Dimension' in list(df_cur.columns):
        df['Dimension'] = df['Dimension_r']
    else:
        drop_cols.remove('Dimension_r')

    if 'Long name' in list(df_cur.columns):
        df['Long name'] = df['Long name_r']
    else:
        drop_cols.remove('Long name_r') 

    # a variable is "newly found" when it is discovered in the code but was not present
    # in the previous excel file at all (membership test, not "has no description" -- so a
    # variable that exists in the excel but was left blank keeps its place and its unit)
    existing_names = set(df_cur['Variable name']) if 'Variable name' in df_cur.columns else set()
    mask_new = ~df['Variable name'].isin(existing_names)

    # take over existing description and unit for variables already in the excel
    df['Description'] = np.where(mask_new, df['Description'], df['Description_r'])
    df['Unit'] = np.where(mask_new, df['Unit'], df['Unit_r'])

    # order: the newly found variables always on top, then the ones already documented --
    # done with a stable sort instead of pd.concat, whose handling of empty or all-NA
    # frames is deprecated (FutureWarning)
    order = np.argsort(~mask_new.to_numpy(), kind='stable')
    df_new_old = df.iloc[order].reset_index(drop=True)

    # print(drop_cols)
    # errors='ignore': suffixed columns are missing when the excel lacks the original column
    df_new_old.drop(columns=drop_cols, inplace=True, errors='ignore')
    mask = df_new_old['Priority'].isnull()
    df_new_old['Priority'] = np.where(mask, 'low', df_new_old['Priority'])

    mask = df_new_old['Long name'].isnull()
    df_new_old['Long name'] = np.where(mask, '', df_new_old['Long name'])

    mask = df_new_old['Type'].isnull()
    df_new_old['Type'] = np.where(mask, '', df_new_old['Type'])

    mask = df_new_old['Dimension'].isnull()
    df_new_old['Dimension'] = np.where(mask, '', df_new_old['Dimension'])
    # use the short placeholder N for the number of active grid cells
    df_new_old['Dimension'] = df_new_old['Dimension'].astype(str).str.replace('ncells', 'N', regex=False)

    return df_new_old

def write_new_excel(wbook_file, df_new_old):
    """
    Write variable data to Excel file and create separate sheets for each priority level.
    
    Creates an Excel workbook with variable documentation, opens it for user editing,
    and then reorganizes the data into separate worksheets based on priority levels.
    
    Parameters
    ----------
    wbook_file : str
        Path to the Excel file to be created/updated.
    df_new_old : pandas.DataFrame
        DataFrame containing all variable information with descriptions,
        units, priorities, and module usage data.
        
    Returns
    -------
    pandas.DataFrame
        The re-read DataFrame including the user's edits, so that the XML
        generation and docstring injection use the edited values.

    Notes
    -----
    The function performs several steps:
    1. Writes the complete variable DataFrame to the 'variables' sheet
    2. Opens the file for user editing using the system's default application
    3. After user edits, re-reads the file and creates separate sheets for each priority level
    4. Each priority level (e.g., 'high', 'medium', 'low') gets its own worksheet
    
    The function blocks execution waiting for user input after opening the Excel file,
    allowing manual editing of descriptions, units, and priorities before continuing.
    """
    with pd.ExcelWriter(wbook_file) as writer:
        df_new_old.to_excel(writer, sheet_name='variables', index=False)
        logger.info(f'{wbook_file} file with all variables saved.')

    print('Press enter to open and edit the excel file with the variable. Once edited, save it and close to '
          'continue the variables documentation process')
    wbook_edited = open_workbook(wbook_file=wbook_file)
    if wbook_edited == 0:
        logger.info(f'{wbook_file} successfully edited')
    else:
        logger.warning(f'{wbook_file} was not edited')

    # make one sheet for all priority levels
    df = pd.read_excel(wbook_file, 'variables')
    prio_levels = list(df['Priority'].unique())
    with pd.ExcelWriter(wbook_file) as writer:
        df.to_excel(writer, sheet_name='variables', index=False)

        for l in prio_levels:
            df_l = df[df['Priority'] == l]
            df_l.to_excel(writer, sheet_name=l, index=False)

    # return the edited data so XML generation and docstring injection use the user's edits
    return df

def write_to_metaNetCdf(df_new_old, netxml_file):
    """
    Generate NetCDF metadata XML file from variable documentation DataFrame.
    
    Creates or updates an XML file containing NetCDF metadata for CWATM variables,
    preserving existing standard names while adding new variable definitions.
    
    Parameters
    ----------
    df_new_old : pandas.DataFrame
        Complete variable documentation DataFrame with columns:
        Variable name, Long name, Unit, Description, etc.
    netxml_file : str
        Path to the output XML metadata file to be created/updated.
        
    Returns
    -------
    int
        Always returns 0 indicating successful completion.
        
    Notes
    -----
    The function performs several key operations:
    - Attempts to load existing metadata from the XML file if it exists
    - Preserves existing standard_name attributes for known variables
    - Handles special unit conversions (e.g., '°C' -> 'C' for NetCDF compatibility)
    - Creates CWATM-formatted XML metadata entries for each variable
    - Includes predefined time aggregation metadata in the header
    
    If the existing XML file cannot be parsed, the user is prompted to either
    create a new file ('c') or abort execution ('a').
    
    The output XML follows the CWATM metadata format with entries like:
    <metanetcdf varname="temperature" unit="C" standard_name="air_temperature" 
                long_name="Air temperature" description="..." title="CWATM" author="IIASA WAT" />
    """
    metaNetcdfVar = {}
    user_opt = 'c'
    # load existing info if file exists
    if os.path.isfile(netxml_file):
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
            if user_opt == 'a':
                exit()
    with open(netxml_file, 'w') as f:
        f.writelines(netxml_head)

        for _index, row in df_new_old.iterrows():
            var_name = row['Variable name']
            # strip characters that are invalid in XML attribute values (& " ' < >)
            long_name = _xml_safe(row['Long name'])
            unt = _xml_safe(row['Unit'])
            if unt == '°C':
                unt = 'C'
            des = _xml_safe(row['Description'])
            vtype = '' if pd.isna(row['Type']) else str(row['Type'])
            vdim = ''
            if 'Dimension' in row.index and not pd.isna(row['Dimension']):
                vdim = str(row['Dimension']).replace(' ', '')  # compact, e.g. 2D(16,N)
            vopt = ''
            if 'Optional' in row.index and not pd.isna(row['Optional']):
                vopt = str(row['Optional'])

            # brackets in the description: the dimension if there is one, e.g. [2D(16,N)];
            # nothing when there is no dimension entry (the type is no longer appended)
            if vdim:
                des = des + "[" + vdim + "]"

            standard_name = ''
            if var_name in metaNetcdfVar.keys():
                standard_name = _xml_safe(metaNetcdfVar[var_name].get('standard_name', ''))

            line = (f'<metanetcdf varname="{var_name}" unit="{unt}"  standard_name="{standard_name}" '
                    f'long_name="{long_name}" type="{vtype}" dim="{vdim}" option="{vopt}" '
                    f'description="{des}"  title="CWATM" author="IIASA WAT" />\n')
            f.write(line)

        f.write('</CWATM>')

    return 0


def get_vars_modules_descriptor(df_new_old):
    """
    Extract variable descriptions and units into a lookup dictionary.
    
    Creates a dictionary mapping variable names to their descriptions and units
    for easy lookup during module documentation generation.
    
    Parameters
    ----------
    df_new_old : pandas.DataFrame
        Complete variable documentation DataFrame containing columns:
        'Variable name', 'Description', 'Unit', and other metadata.
        
    Returns
    -------
    dict
        Dictionary with variable names as keys and dictionaries as values.
        Each value dictionary contains:
        - 'Description': Variable description text
        - 'Unit': Variable unit string
        
    Notes
    -----
    This function is used to create a convenient lookup table for variable
    metadata when generating documentation that gets injected into Python
    module docstrings. It extracts only the essential description and unit
    information needed for the module documentation tables.
    """
    # Sort df_new_old by Type (Flag, Number, List, Array) then by Variable name alphabetically
    type_order = {'Flag': 1, 'Number': 2, 'List': 3, 'Array': 4}
    df_sorted = df_new_old.sort_values(by=['Type', 'Variable name'],
                                               key=lambda x: x.map(type_order).fillna(5) if x.name == 'Type' else x)

    new_old = []
    for _index, row in df_sorted.iterrows():
        var_name = row['Variable name']
        uom = row['Unit']
        descr = row['Description']
        type = row['Type']
        new_old.append([var_name,type,descr,uom])


    dict_new_old = {}
    for _index, row in df_sorted.iterrows():
        var_name = row['Variable name']
        uom = row['Unit']
        descr = row['Description']
        type = row['Type']
        dict_new_old[var_name] = {'Type': type,'Description': descr, 'Unit': uom}

    return new_old, dict_new_old

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CWatM variable documentation generator')
    parser.add_argument('--dir', default='..', dest='root_dir', metavar='ROOT_DIR',
                        help='Root directory of the CWatM code, i.e. the folder containing '
                             'hydrological_modules (default: ..)')
    parser.add_argument('--excel', default=None, metavar='EXCEL_FILE',
                        help='Excel file where the variable names and attributes are stored '
                             '(skips the interactive prompt; default: selfvar.xlsx)')
    parser.add_argument('--xml', default=None, metavar='XML_FILE',
                        help='XML file where the variables NetCDF4 metadata will be stored '
                             '(skips the interactive prompt; default: metaNetcdf.xml)')
    parser.add_argument('--settings', default=None, metavar='SETTINGS_INI',
                        help='CWatM settings file; if given, CWatM is run for one time step to '
                             'measure the dimension of each array variable (fills the "Dimension" '
                             'column, e.g. "1D (N)" or "2D (6, N)" with N = number of grid cells -- '
                             'the result is settings-independent, any working settings file can be used)')
    args = parser.parse_args()

    root_dir = args.root_dir
    if not os.path.isdir(os.path.join(root_dir, 'hydrological_modules')):
        logger.error(f'"{root_dir}" does not contain a hydrological_modules folder. '
                     'Use --dir to point to the CWatM root directory.')
        exit(1)

    folders = [os.path.join(root_dir, f) for f in base_folders]

    # Keys are variable name : then 1rst module and associated line
    Dict_AllVariables, var_options = scan_variables(folders)
    kn = len(Dict_AllVariables.keys())
    logger.info(f'Found {kn} variables.')

    # get variables in previous xcel
    if args.excel:
        wbook_file = args.excel
    else:
        wbook_file = input(
            "Enter the excel file name where the variables names and attributes are stored or press any key to "
            "accept the default name (selfvar.xlsx).\nIf the file does not exist, it will be created else "
            "overwritten.\n"
        )

    if len(wbook_file) < 2:
        wbook_file = 'selfvar.xlsx'  # set default if any key pressed
    if 'xlsx' not in wbook_file:
        wbook_file += '.xlsx'

    # create file if not existing
    if not os.path.isfile(wbook_file):
        df = pd.DataFrame(columns=xcols)
        df = pd.DataFrame(df)
        with pd.ExcelWriter(wbook_file) as writer:
            df.to_excel(writer, sheet_name='variables', index=False)
            logger.info(f'{wbook_file} file created.')

    # find all the variables not included in the current documentation
    df_cur = pd.read_excel(wbook_file, sheet_name='variables')
    all_vars = list(Dict_AllVariables.keys())
    all_vars_names = [k.replace('self.var.', '') for k in all_vars]  # all variables names read from the code
    df_all_names = pd.DataFrame({'vars': all_vars, 'var_names': all_vars_names})
    df_new = df_all_names[~df_all_names['var_names'].isin(df_cur['Variable name'])]
    n_nw = len(df_new.index)
    logger.info(f'Found {n_nw} new variables.')

    # variables in the excel that are no longer found in the code get outsorted (dropped
    # from excel, xml and docstrings); append their old rows to a separate file so their
    # documentation is not lost without a trace
    df_removed = df_cur[~df_cur['Variable name'].isin(all_vars_names)]
    if len(df_removed.index) > 0:
        removed_file = 'removed_variables.csv'
        df_removed = df_removed.copy()
        df_removed.insert(0, 'Removed on', time.strftime('%Y-%m-%d %H:%M:%S'))
        df_removed.to_csv(removed_file, mode='a', header=not os.path.isfile(removed_file), index=False)
        logger.warning(f'{len(df_removed.index)} variables no longer found in the code will be removed '
                       f'from the excel; their rows were appended to {removed_file}: '
                       + ', '.join(df_removed['Variable name'].astype(str)))

    # print(df_new.head(100))
    # create a dataframe with all variables and save it to excel
    df_new_old = make_all_variables_df(Dict_AllVariables, df_cur, var_options)

    # fill in array dimensions derived statically from the code. This always runs and
    # only fills blanks, so it covers variables of modules that are switched off in the
    # settings file (which the runtime measurement below cannot reach).
    code_dims = infer_dimensions_from_code(folders)
    df_new_old['Dimension'] = [
        dim if (isinstance(dim, str) and dim.strip()) else code_dims.get(name, dim)
        for name, dim in zip(df_new_old['Variable name'], df_new_old['Dimension'])]

    # measure array dimensions by running CWatM for one time step (optional); the
    # measured (exact) dimensions take precedence over the statically inferred ones
    if args.settings:
        dims = measure_dimensions(args.settings, root_dir)
        df_new_old['Dimension'] = [dims.get(name, dim) for name, dim in
                                   zip(df_new_old['Variable name'], df_new_old['Dimension'])]

    # for variables that still have no description, try to extract one from the
    # surrounding source comments and mark it with '(AI)' so the user can review/refine
    # it when the excel is opened for editing below
    code_descr = infer_descriptions_from_code(folders)
    filled_descr = 0
    new_descr = []
    for name, desc in zip(df_new_old['Variable name'], df_new_old['Description']):
        if (pd.isna(desc) or str(desc).strip() == '') and code_descr.get(name):
            new_descr.append(_xml_safe(code_descr[name]) + ' (AI)')
            filled_descr += 1
        else:
            new_descr.append(desc)
    df_new_old['Description'] = new_descr
    logger.info(f'Filled {filled_descr} empty descriptions from code comments (marked "(AI)").')

    # write new excel with all variables and a worksheet for each priority level;
    # returns the re-read file including the user's edits
    df_new_old = write_new_excel(wbook_file, df_new_old)

    if args.xml:
        netxml_file = args.xml
    else:
        netxml_file = input(
            "Enter the xml file name where the variables NetCDF4 metadata will be stored or press any key to "
            "accept the default name (metaNetcdf.xml).\nIf the file does not exist, it will be created else "
            "overwritten.\n"
        )

    if len(netxml_file) < 2:
        netxml_file = 'metaNetcdf.xml'  # set default if any key pressed
    if 'xml' not in netxml_file:
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
                    file = open(filename_to_modify, 'r', encoding='utf-8', errors='surrogateescape')
                    lines = file.readlines()
                    file.close()

                    # PB change to make the output table variable
                    lead = " " * 4
                    between = " " * 2
                    col1 = 35
                    col11 = 10
                    col2 = 70
                    col3 = 5
                    # col4 = 30

                    added_description = "\n"+ lead + "**Global variables**\n"

                    added_description = (added_description + lead + '{:{x}.{x}}'.format('=' * col1, x=col1) +
                                         between + '{:{x}.{x}}'.format('=' * col11, x=col11) + between +
                                         between + '{:{x}.{x}}'.format('=' * col2, x=col2) + between +
                                         '{:{x}.{x}}'.format('=' * col3, x=col3) + "\n")
                    added_description = (added_description + lead + '{:{x}.{x}}'.format('Variable [self.var]', x=col1) +
                                         between + '{:{x}.{x}}'.format('Type', x=col11) + between +
                                         between + '{:{x}.{x}}'.format('Description', x=col2) + between +
                                         '{:{x}.{x}}'.format('Unit', x=col3) + "\n")
                    added_description = (added_description + lead + '{:{x}.{x}}'.format('=' * col1, x=col1) +
                                         between + '{:{x}.{x}}'.format('=' * col11, x=col11) + between +
                                         between + '{:{x}.{x}}'.format('=' * col2, x=col2) + between +
                                         '{:{x}.{x}}'.format('=' * col3, x=col3) + "\n")

                    # added_description = added_description + "    ==========================  ========================================================================================  =========  ==============================\n"
                    # added_description = added_description + "    Variable [self.var]         Description                                                                               Unit       Appears in\n"
                    # added_description = added_description + "    ==========================  ========================================================================================  =========  ==============================\n"
                    # put variable names: {description, units} in a dictionary
                    new_old,dict_new_old = get_vars_modules_descriptor(df_new_old)
                    for vv in var_name_in_module:
                        list_modules = ""
                        v_name = vv.replace('self.var.', '')
                        # defaults, so a variable missing from the excel does not inherit
                        # the values of the previous loop iteration
                        type = ''
                        descr = ''
                        uim = '--'
                        if v_name in dict_new_old.keys():
                            ds_um = dict_new_old[v_name]
                            type = ds_um['Type']
                            descr = ds_um['Description']
                            uim = ds_um['Unit']
                            
                            if isinstance(descr, str) == False:
                                descr = ''
                            if isinstance(uim, str) == False or uim == '-' or len(uim) == 0:
                                uim = '--'

                        added_description = (added_description + lead + '{:{x}.{x}}'.format(vv[9:], x=col1) +
                                             between + '{:{x}.{x}}'.format(type, x=col11) + between +
                                             between + '{:{x}.{x}}'.format(descr, x=col2) + between +
                                             '{:{x}.{x}}'.format(uim, x=col3) + "\n")

                    # added_description = added_description + "    ==========================  ========================================================================================  =========  ==============================\n\n"
                    # added_description = added_description + lead + '{:{x}.{x}}'.format('='*col1,x=col1) + between + '{:{x}.{x}}'.format('='*col2,x=col2) + between +\
                    #                    '{:{x}.{x}}'.format('='*col3,x=col3) + between + '{:{x}.{x}}'.format('='*col4,x=col4) + "\n\n"

                    added_description = (added_description + lead + '{:{x}.{x}}'.format('=' * col1, x=col1) +
                                         between + '{:{x}.{x}}'.format('=' * col11, x=col11) + between +
                                         between + '{:{x}.{x}}'.format('=' * col2, x=col2) + between +
                                         '{:{x}.{x}}'.format('=' * col3, x=col3) + "\n\n")
                    ###added_description = added_description + "    **Functions**\n"

                    # delete old table in module (if there is any).
                    # The table consists of a '**Global variables**' header and three '====' separator
                    # lines (top, below header row, bottom). Deletion MUST stop at the bottom separator --
                    # deleting to end of file would destroy the whole module (this happened once!).
                    linesnew = []
                    in_table = False
                    after_table = False
                    sep_count = 0
                    for line in lines:
                        if line.find('**Global variables**') > -1:
                            in_table = True
                            sep_count = 0
                            continue
                        if in_table:
                            if line.lstrip().startswith('='):
                                sep_count += 1
                                if sep_count == 3:  # bottom separator -> table ends here
                                    in_table = False
                                    after_table = True
                            continue
                        if after_table:
                            if line.strip() == '':  # swallow blank lines left behind by the old table
                                continue
                            after_table = False
                        linesnew.append(line)
                    if in_table:  # never saw the bottom separator: table was cut off, do not risk this file
                        logger.error(f'{filename_to_modify}: found "**Global variables**" but no complete '
                                     'table; file left unchanged.')
                        continue
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
                        if (lines[module_line].startswith('    """') and begin_outcommented_lines != -1 and
                                class_index != -1):
                            end_outcommented_lines = module_line

                    if end_outcommented_lines != -1:  # we found a class and definition just after, so we can add text
                        # lines[end_outcommented_lines-1] = lines[end_outcommented_lines-1] + '\n' + added_description
                        # PB removed the /n in between
                        lines[end_outcommented_lines - 1] = lines[end_outcommented_lines - 1] + added_description

                    # safety net: never write back a module that would no longer compile
                    new_content = ''.join(lines)
                    try:
                        compile(new_content, filename_to_modify, 'exec')
                    except SyntaxError as e:
                        logger.error(f'{filename_to_modify}: injecting the table would break the file '
                                     f'(SyntaxError line {e.lineno}); file left unchanged.')
                        continue

                    # PB to make it unix compatible (windows does not care but linux)
                    file = open(filename_to_modify, mode='w', newline='\n', encoding='utf8',
                                errors='surrogateescape')
                    file.writelines(lines)
                    file.close()
                    
    print('Process completed.')
