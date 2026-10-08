# -------------------------------------------------------------------------
# Name:        Configuration
# Purpose: Configuration file parsing and settings management with advanced interpolation.
# Processes INI files with cross-section variable substitution capabilities.
# Populates global dictionaries controlling model behavior and output specifications.
#
# Author:      burekpe
# Created:     16/05/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

import configparser
import difflib  # to check the closest word in settingsfile, if an error occurs
import os
import pathlib
import re
import xml.dom.minidom

from cwatm.management_modules.globals import *
from cwatm.management_modules.messages import *


class ExtParser(configparser.ConfigParser):
    """
    Extended configuration parser with placeholder replacement functionality.
    
    This class extends the standard ConfigParser to support cross-section
    and same-section variable substitution using a custom placeholder syntax.
    Enables dynamic path construction and parameter referencing in configuration
    files, which is essential for maintaining flexible and maintainable CWatM
    model configurations.
    
    Attributes
    ----------
    cur_depth : int
        Current recursion depth for nested placeholder replacements.
        Used to prevent infinite recursion during variable substitution.
    
    Notes
    -----
    Placeholder syntax:
    - Cross-section: $(SECTION:OPTION) - references option in different section
    - Same-section: $(OPTION) - references option in current section
    
    The parser respects MAX_INTERPOLATION_DEPTH from configparser to prevent
    infinite recursion in circular references.
    """

    # implementing extended interpolation
    def __init__(self, *args, **kwargs):
        """
        Initialize the extended configuration parser.
        
        Parameters
        ----------
        *args : tuple
            Variable length argument list passed to parent ConfigParser.
        **kwargs : dict
            Arbitrary keyword arguments passed to parent ConfigParser.
        """
        self.cur_depth = 0
        configparser.ConfigParser.__init__(self, *args, **kwargs)

    def get(self, section, option, raw=False, vars=None, **kwargs):
        """
        Retrieve configuration value with placeholder replacement.
        
        This method extends the standard ConfigParser.get() to perform
        recursive placeholder substitution. It processes both cross-section
        $(SECTION:OPTION) and same-section $(OPTION) placeholders.
        
        Parameters
        ----------
        section : str
            Configuration file section name containing the option.
        option : str
            Configuration option name to retrieve.
        raw : bool, optional
            If True, return raw value without placeholder substitution.
            Default is False.
        vars : dict, optional
            Dictionary of additional variables for interpolation.
            Default is None.
        **kwargs : dict
            Additional keyword arguments for ConfigParser compatibility.
        
        Returns
        -------
        str
            Configuration value with all placeholders replaced.
        
        Raises
        ------
        CWATMError
            If the requested option is not found. Provides closest match
            suggestions using difflib for debugging assistance.
        InterpolationDepthError
            If placeholder replacement exceeds maximum recursion depth,
            indicating circular references.
        
        Notes
        -----
        The method uses regular expressions to identify and replace placeholders:
        - r'\$\((\w*):(\w*)\)' for cross-section references
        - r'\$\((\w*)\)' for same-section references
        
        Recursion depth tracking prevents infinite loops in circular references.
        """

        # h1 = sys.tracebacklimit
        # sys.tracebacklimit = 0  # no long error message
        try:
            r_opt = configparser.ConfigParser.get(self, section, option, raw=True, vars=vars)
        except:
            print(section, option)
            closest = difflib.get_close_matches(option, list(binding.keys()))
            if not closest:
                closest = ["- no match -"]
            msg = "Error 116: Closest key to the required one is: \"" + closest[0] + "\""
            raise CWATMError(msg)

        # sys.tracebacklimit = h1   # set error message back to default
        if raw:
            return r_opt

        ret = r_opt
        re_newintp1 = r'\$\((\w*):(\w*)\)'  # other section
        re_newintp2 = r'\$\((\w*)\)'  # same section

        re_old1 = re.findall(r'\$\(\w*:\w*\)', r_opt)
        re_old2 = re.findall(r'\$\(\w*\)', r_opt)

        m_new1 = re.findall(re_newintp1, r_opt)
        m_new2 = re.findall(re_newintp2, r_opt)

        if m_new1:
            i = 0
            for f_section, f_option in m_new1:
                self.cur_depth += 1
                if self.cur_depth < configparser.MAX_INTERPOLATION_DEPTH:
                    sub = self.get(f_section, f_option, vars=vars)
                    ret = ret.replace(re_old1[i], sub)
                    i += 1
                else:
                    raise configparser.InterpolationDepthError(option, section, r_opt)

        if m_new2:
            i = 0
            for l_option in m_new2:
                self.cur_depth += 1
                if self.cur_depth < configparser.MAX_INTERPOLATION_DEPTH:
                    sub = self.get(section, l_option, vars=vars)
                    ret = ret.replace(re_old2[i], sub)
                    i += 1
                else:
                    raise configparser.InterpolationDepthError(option, section, r_opt)

        self.cur_depth -= 1
        return ret



def parse_configuration(settingsFileName):
    """
    Parse CWatM configuration file and populate global parameter dictionaries.
    
    This function is the main entry point for configuration processing. It reads
    the INI-format settings file, processes all sections and options, and populates
    the global dictionaries that control model behavior. Separates parameters into
    model bindings, boolean/integer options, and output specifications.
    
    Parameters
    ----------
    settingsFileName : str
        Absolute or relative path to the CWatM configuration file (.ini format).
    
    Returns
    -------
    None
        Results are stored in global dictionaries:
        - binding: Model parameters and file paths
        - option: Boolean and integer configuration flags
        - outTss, outMap: Time series and map output specifications
        - outDir: Output directory mappings
        - outsection: List of sections with output definitions
        - outputDir: Global output directory list
    
    Raises
    ------
    CWATMFileError
        If the settings file does not exist or cannot be read.
    
    Notes
    -----
    Configuration file structure:
    - [OPTIONS] section contains boolean/integer flags
    - Output parameters follow naming convention: out_*, out_tss_*, *_dir
    - All other parameters become model bindings
    - Supports UTF-8 encoding for international file paths
    - Uses case-sensitive option names (optionxform = str)
    
    Global variables modified:
    - binding: Main parameter dictionary
    - option: Boolean/integer options dictionary  
    - outTss: Time series output specifications
    - outMap: Map output specifications
    - outDir: Output directory per section
    - outsection: Sections with output definitions
    - outputDir: Global output directory list
    """

    def splitout(varin, check):
        """
        Split comma-separated output variable string into list.
        
        Helper function to parse output variable specifications that may contain
        multiple variables separated by commas. Handles empty strings by
        converting to "None" and updates the check flag when valid variables
        are found.
        
        Parameters
        ----------
        varin : str
            Comma-separated string of variable names or file paths.
        check : bool
            Flag indicating whether valid output variables have been found.
        
        Returns
        -------
        list
            List of stripped variable names or paths.
        bool
            Updated check flag - True if valid variables found.
        
        Notes
        -----
        - Empty strings are converted to "None" for consistency
        - Whitespace is stripped from each variable name
        - Used primarily for parsing output variable lists in configuration
        """

        out = list(map(str.strip, varin.split(',')))
        if out[0] == "":
            out[0] = "None"
        if out[0] != "None":
            check = True
        return out, check

    if not (os.path.isfile(settingsFileName)):
        msg = "Error 302: Settingsfile not found!\n"
        raise CWATMFileError(settingsFileName, msg)
    config = ExtParser()
    config.optionxform = str
    config.sections()
    config.read(settingsFileName, encoding='utf8')
    for sec in config.sections():
        # print sec
        options = config.options(sec)
        check_section = False
        for opt in options:
            if sec == "OPTIONS":
                try:
                    option[opt] = config.getboolean(sec, opt)
                except:
                    option[opt] = config.getint(sec, opt)
            else:
                # Check if config line = output line
                if opt.lower()[0:4] == "out_":
                    index = sec.lower() + "_" + opt.lower()

                    if opt.lower()[-4:] == "_dir":
                        outDir[sec] = config.get(sec, opt)
                    else:
                        # split into timeseries and maps
                        if opt.lower()[4:8] == "tss_":
                            outTss[index], check_section = splitout(config.get(sec, opt), check_section)
                        else:
                            outMap[index], check_section = splitout(config.get(sec, opt), check_section)

                else:
                    # binding: all the parameters which are not output or option are collected
                    binding[opt] = config.get(sec, opt)

        if check_section:
            outsection.append(sec)

    outputDir.append(binding["PathOut"])
    # Output directory is stored in a separate global array


def read_metanetcdf(name):
    """
    Parse XML metadata file for NetCDF variable attributes.
    
    Reads an XML metadata file containing variable attributes for NetCDF output.
    The metadata includes units, long names, standard names, and other CF-compliant
    attributes required for proper scientific data documentation. This information
    is essential for creating self-describing NetCDF files that comply with
    climate and hydrological data standards.
    
    Parameters
    ----------
    name : str
        Filename of the XML metadata file, typically 'metaNetcdf.xml'.
        Path is resolved relative to the parent directory of this module.
    
    Returns
    -------
    None
        Results stored in global metaNetcdfVar dictionary.
    
    Raises
    ------
    CWATMError
        If XML file cannot be parsed due to syntax errors or encoding issues.
        If metadata file cannot be found at the expected location.
    
    Notes
    -----
    Expected XML structure:
    <CWATM>
        <metanetcdf varname="variable_name" unit="units" long_name="description" 
                    standard_name="cf_standard_name" .../>
    </CWATM>
    
    Global variables modified:
    - metaNetcdfVar: Dictionary mapping variable names to their metadata attributes
    
    The metadata is used during NetCDF file creation to ensure proper
    documentation and CF compliance for output variables.
    """

    metaxml = os.path.join(pathlib.Path(__file__).parent.resolve().parent.resolve(), name)
    if os.path.isfile(metaxml):
        try:
            metaparse = xml.dom.minidom.parse(metaxml)
        except:
            msg = "Error 303: using option file: " + metaxml
            raise CWATMError(msg)

        # running through all output variable
        # if an output variable is not defined here the standard metadata is used
        # unit = "undefined", standard name = long name = variable name
        meta = metaparse.getElementsByTagName("CWATM")[0]

        for metavar in meta.getElementsByTagName("metanetcdf"):
            d = {}
            for key in list(metavar.attributes.keys()):
                if key != 'varname':
                    d[key] = metavar.attributes[key].value
            key = metavar.attributes['varname'].value
            metaNetcdfVar[key] = d

    else:
        msg = "Error 304: cannot find file: " + metaxml
        raise CWATMError(msg)


    ii = 1