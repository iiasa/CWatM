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
    
    Notes
    -----

    Placeholder syntax:

    - Cross-section: $(SECTION:OPTION) - references option in different section
    - Same-section: $(OPTION) - references option in current section

    The parser respects MAX_INTERPOLATION_DEPTH from configparser (nesting depth
    of placeholders) to stop circular references with Error 141.
    A $( which is not a complete placeholder raises Error 143.

    """

    # implementing extended interpolation
    def get(self, section, option, raw=False, vars=None, _depth=0, _ref="", **kwargs):
        r"""
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
        _depth : int, optional
            Nesting depth of the placeholder replacement (internal, set by the
            recursive calls). Default is 0.
        _ref : str, optional
            Placeholder and key which refer to this option (internal, set by the
            recursive calls, added to Error 116). Default is "".
        **kwargs : dict
            Additional keyword arguments for ConfigParser compatibility.
        
        Returns
        -------
        str
            Configuration value with all placeholders replaced.
        
        Raises
        ------
        CWATMError
            If the requested section or option is not found (Error 116). Names
            the sections which have the option, or the closest section/option
            (difflib), and the key with the $(...) reference if there is one.
            If placeholders are nested deeper than MAX_INTERPOLATION_DEPTH,
            indicating a circular reference (Error 141).
            If a $( is not part of a complete placeholder (Error 143).

        Notes
        -----
        The method uses regular expressions to identify and replace placeholders:
        - r'\$\(([^:()$]*):([^:()$]*)\)' for cross-section references
        - r'\$\(([^:()$]*)\)' for same-section references
        Names may contain any character except : ( ) $ (e.g. Path-Root).

        The nesting depth is passed down with _depth, so it counts only the
        chain of references of this value.
        """

        try:
            r_opt = configparser.ConfigParser.get(self, section, option, raw=True, vars=vars)
        except configparser.NoSectionError:
            closest = difflib.get_close_matches(section, self.sections())
            if not closest:
                closest = ["- no match -"]
            msg = "Error 116: No section with the name: [" + section + "] (asked for key: \"" + option + "\")\n"
            msg += "Closest section to the required one is: [" + closest[0] + "]\n"
            raise CWATMError(msg + _ref)
        except configparser.NoOptionError:
            msg = "Error 116: No key with the name: \"" + option + "\" in section: [" + section + "]\n"
            insec = [sec for sec in self.sections() if self.has_option(sec, option)]
            if insec:
                msg += "The key is in section: [" + "], [".join(insec) + "]\n"
            else:
                keys = [key for sec in self.sections() for key in self.options(sec)]
                closest = difflib.get_close_matches(option, keys)
                if not closest:
                    closest = ["- no match -"]
                msg += "Closest key to the required one is: \"" + closest[0] + "\"\n"
            raise CWATMError(msg + _ref)

        if raw or "$(" not in r_opt:
            return r_opt
        if _depth >= configparser.MAX_INTERPOLATION_DEPTH:
            msg = "Error 141: Circular reference (or more than " + str(configparser.MAX_INTERPOLATION_DEPTH) + " nested $(...) levels)\n"
            msg += "in key: \"" + option + "\" in section: [" + section + "] = " + r_opt
            raise CWATMError(msg)

        ret = r_opt
        usedin = " is used in key: \"" + option + "\" in section: [" + section + "] = " + r_opt
        # other section $(SECTION:OPTION)
        for f_section, f_option in set(re.findall(r'\$\(([^:()$]*):([^:()$]*)\)', r_opt)):
            placeholder = "$(" + f_section + ":" + f_option + ")"
            sub = self.get(f_section, f_option, vars=vars, _depth=_depth + 1, _ref=placeholder + usedin)
            ret = ret.replace(placeholder, sub)
        # same section $(OPTION)
        for l_option in set(re.findall(r'\$\(([^:()$]*)\)', r_opt)):
            placeholder = "$(" + l_option + ")"
            sub = self.get(section, l_option, vars=vars, _depth=_depth + 1, _ref=placeholder + usedin)
            ret = ret.replace(placeholder, sub)
        # the replaced values have no $( left, so a $( here is from a broken placeholder e.g. $(A:B:C) or $(PathRoot
        if "$(" in ret:
            msg = "Error 143: Placeholder cannot be read - it has to be $(SECTION:KEY) or $(KEY)\n"
            msg += "in key: \"" + option + "\" in section: [" + section + "] = " + r_opt
            raise CWATMError(msg)
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
        If the settings file does not exist (Error 302), cannot be read or
        parsed (Error 307), has no PathOut (Error 308) or has [OPTIONS] not in
        capital letters (Error 144).
    CWATMError
        If a value in [OPTIONS] is neither True/False nor an integer (Error 142).
        If an output key is not OUT_Dir, OUT_TSS_... or OUT_MAP_ + a type of
        outputTypMap (Error 145).

    Notes
    -----
    Configuration file structure:
    - [OPTIONS] section contains boolean/integer flags (0/1 become False/True)
    - Output parameters follow naming convention: out_*, out_tss_*, *_dir
    - All other parameters become model bindings; a key in two sections with
      different values gives a warning and the later value is used
    - Inline comments after " #" are removed from the value
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
        - Empty entries are left out ("a,,b" -> a, b); no entry at all gives ["None"]
        - Whitespace is stripped from each variable name
        - Used primarily for parsing output variable lists in configuration
        """

        # empty entries are left out: "OUT_MAP_Daily = , discharge" or "a,,b" (else an empty variable name)
        out = [v for v in map(str.strip, varin.split(',')) if v]
        if not out:
            out = ["None"]
        if out[0] != "None":
            check = True
        return out, check

    if not (os.path.isfile(settingsFileName)):
        msg = "Error 302: Settingsfile not found!\n"
        raise CWATMFileError(settingsFileName, msg)
    # inline comments: "key = value  # comment" -> value (# needs a space before it, a#b stays a#b)
    config = ExtParser(inline_comment_prefixes=("#",))
    config.optionxform = str
    try:
        config.read(settingsFileName, encoding='utf8')
    except (configparser.Error, UnicodeDecodeError) as e:
        msg = "Error 307: Settingsfile cannot be read (no UTF-8 encoding, a key or section is twice in the file,\n"
        msg += "a line is outside a section or is not \"key = value\"):\n" + str(e) + "\n"
        raise CWATMFileError(settingsFileName, msg)
    bindsec = {}  # section of each binding key, to warn if a key is in two sections with different values
    referenced = set()  # keys used in $(...) placeholders: used by the settings file itself (see check_settings_keys)
    for sec in config.sections():
        # [OPTIONS] is the only section with a special meaning - [Options] would make all options normal keys
        if sec.upper() == "OPTIONS" and sec != "OPTIONS":
            msg = "Error 144: Section [" + sec + "] has to be written [OPTIONS] (capital letters)"
            raise CWATMFileError(settingsFileName, msg)
        options = config.options(sec)
        check_section = False
        for opt in options:
            referenced.update(re.findall(r'\$\((?:[^:()$]*:)?([^:()$]*)\)', config.get(sec, opt, raw=True)))
            if sec == "OPTIONS":
                # getboolean first: 0/1 (also yes/no, on/off) become False/True, other integers stay int
                # e.g. evaporation.py tests checkOption('use_GeneralCropIrr') is True with use_GeneralCropIrr = 1
                try:
                    option[opt] = config.getboolean(sec, opt)
                except ValueError:
                    try:
                        option[opt] = config.getint(sec, opt)
                    except ValueError:
                        msg = "Error 142: The option: \"" + opt + "\" in [OPTIONS] has to be True/False or an integer, not: \"" + config.get(sec, opt) + "\""
                        raise CWATMError(msg)
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
                            # map output: OUT_MAP_<type> - other names are not written by output.py
                            # (and gave a misleading Error 132 with a single letter as variable name)
                            if opt.lower()[4:8] != "map_" or opt.lower()[8:] not in outputTypMap:
                                msg = "Error 145: Output key: \"" + opt + "\" in section [" + sec + "] is not possible!\n"
                                msg += "Map output has to be OUT_MAP_ + one of these: " + ", ".join(outputTypMap) + "\n"
                                msg += "(time series: OUT_TSS_..., output folder: OUT_Dir)"
                                raise CWATMError(msg)
                            outMap[index], check_section = splitout(config.get(sec, opt), check_section)

                else:
                    # binding: all the parameters which are not output or option are collected
                    value = config.get(sec, opt)
                    # dict.get: the comparison is not a use of the key by the model (binding records used keys)
                    if opt in bindsec and value != dict.get(binding, opt):
                        msg = "Key: \"" + opt + "\" is in section [" + bindsec[opt] + "] and [" + sec + "] with different values\n"
                        msg += "[" + bindsec[opt] + "] " + opt + " = " + dict.get(binding, opt) + "\n"
                        msg += "[" + sec + "] " + opt + " = " + value + "   <- this value is used\n"
                        print(CWATMWarning(msg))
                    binding[opt] = value
                    bindsec[opt] = sec

        if check_section:
            outsection.append(sec)

    if "PathOut" not in binding:
        msg = "Error 308: No key with the name: \"PathOut\" (output directory) in the settingsfile\n"
        raise CWATMFileError(settingsFileName, msg)
    outputDir.append(binding["PathOut"])
    # Output directory is stored in a separate global array
    binding.used.update(referenced)


def check_settings_keys():
    """
    Warn about keys in the settings file which are probably misspelled or in the wrong section.

    Called once after the first time step. binding and option (KeyTrackDict in globals.py) record
    which keys the model asked for. A key the model asked for but did not find is compared with the
    keys of the settings file the model never used:

    - same name (ignoring capital letters) in [OPTIONS] instead of another section, or the other way round
      -> the value is not used, the key is in the wrong section
    - similar name (difflib, ignoring capital letters, cutoff 0.85) -> probably misspelled

    Returns
    -------
    list of str
        The warning messages (also printed as CWATMWarning).

    Notes
    -----
    Optional keys are checked in the code with e.g. "if 'stopaftersnow' in option" - a misspelled
    stopAfterSnoww = True would be ignored without this check and the default would be used.
    Keys used only in $(...) placeholders count as used. Keys asked for later than the first time step
    are not checked. Obsolete options (reportMap, reportTss, sumWaterBalance, writeNetcdfStack) are ignored.
    """

    # old options which are still in many settings files but not used by the code any more
    # (e.g. reportTss would else be taken as a misspelled reportOldTss)
    obsolete = {"reportMap", "reportTss", "sumWaterBalance", "writeNetcdfStack"}
    msgs = []
    unused = {"[OPTIONS]": [k for k in option.keys() if k not in option.used and k not in obsolete],
              "settings": [k for k in binding.keys() if k not in binding.used]}
    for where, d in (("[OPTIONS]", option), ("settings", binding)):
        other = "settings" if where == "[OPTIONS]" else "[OPTIONS]"
        for key in sorted(d.missing):
            found = False
            # same name in the other kind of section
            for k in unused[other]:
                if k.lower() == key.lower():
                    found = True
                    if where == "[OPTIONS]":
                        msgs.append("Key: \"" + k + "\" has to be in [OPTIONS] - in another section it is not used")
                    else:
                        msgs.append("Key: \"" + k + "\" in [OPTIONS] is not used - it has to be in another section (e.g. the section of its module)")
            if found:
                continue
            # similar name in the same kind of section
            lower = {k.lower(): k for k in unused[where]}
            close = difflib.get_close_matches(key.lower(), list(lower), 1, 0.85)
            if close:
                msgs.append("Key: \"" + lower[close[0]] + "\" in the settingsfile is not used - is it a misspelled \"" + key + "\"?")

    for msg in msgs:
        print(CWATMWarning(msg + "\n"))
    return msgs


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
        If XML file cannot be parsed due to syntax errors or encoding issues (Error 303).
        If metadata file cannot be found at the expected location (Error 304).
        If there is no <CWATM> element or an entry has no varname (Error 309).
    
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

    metaxml = os.path.join(pathlib.Path(__file__).resolve().parent.parent, name)
    if os.path.isfile(metaxml):
        try:
            metaparse = xml.dom.minidom.parse(metaxml)
        except Exception:
            msg = "Error 303: using option file: " + metaxml
            raise CWATMError(msg)

        # running through all output variable
        # if an output variable is not defined here the standard metadata is used
        # unit = "undefined", standard name = long name = variable name
        roots = metaparse.getElementsByTagName("CWATM")
        if not roots:
            msg = "Error 309: no <CWATM> element in the metadata file: " + metaxml
            raise CWATMError(msg)
        meta = roots[0]

        for i, metavar in enumerate(meta.getElementsByTagName("metanetcdf")):
            if not metavar.hasAttribute('varname'):
                msg = "Error 309: entry " + str(i + 1) + " <metanetcdf ...> has no varname in the metadata file: " + metaxml + "\n"
                msg += "attributes: " + ", ".join(k + "=\"" + v + "\"" for k, v in list(metavar.attributes.items())[:4])
                raise CWATMError(msg)
            d = {}
            for key in metavar.attributes.keys():
                if key != 'varname':
                    d[key] = metavar.attributes[key].value
            key = metavar.attributes['varname'].value
            metaNetcdfVar[key] = d

    else:
        msg = "Error 304: cannot find file: " + metaxml
        raise CWATMError(msg)