# -------------------------------------------------------------------------
# Name:        Messages  
# Purpose:     Error handling and message system for CWatM
#
# Author:      burekpe
# Created:     16/05/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

"""
Error handling and user communication system for CWatM.

This module provides a comprehensive error handling framework for the Community
Water Model, including specialized error classes for different types of failures
and user communication. The system provides clear, formatted error messages
with diagnostic information to help users identify and resolve issues.

Classes
-------
CWATMError : Base error class for general CWatM errors
CWATMFileError : Specialized error class for file-related issues
CWATMDirError : Specialized error class for directory-related issues  
CWATMWarning : Warning class for non-fatal issues
CWATMRunInfo : Information class for simulation status messages

Notes
-----
All error classes automatically extract error numbers from message strings
and provide formatted output with consistent headers. The system suppresses
Python traceback information to provide cleaner error messages for end users.
"""


import os
import sys


class CWATMError(Warning):
    """
    Base error handling class for CWatM errors.
    
    This class provides standardized error reporting with formatted output
    and automatic error number extraction. It suppresses Python tracebacks
    to provide cleaner error messages for end users.
    
    Parameters
    ----------
    msg : str
        Error message string, optionally containing error number in format
        "Error XXX: message" where XXX is a 3-digit error code
        
    Notes
    -----
    Error numbers are automatically extracted from message strings that follow
    the pattern "Error XXX:" where XXX is a 3-digit number. If no valid error
    number is found, defaults to error code 100.
    
    The class prints formatted error messages with a distinctive header and
    suppresses Python traceback information by setting sys.tracebacklimit = 0.
    """

    def __init__(self, msg):

        # don't show the error code, lines etc.
        sys.tracebacklimit = 0
        header = "\n\n ========================== CWATM ERROR =============================\n"

        print(header + msg + "\n")

        try:
            errornumber = int(msg[6:9])
        except:
            errornumber = 100
        # sys.exit(errornumber)
        print("CWatM errornumber: " + str(errornumber))



class CWATMFileError(CWATMError):
    """
    Specialized error handling class for file-related errors.
    
    This class extends CWATMError to provide detailed diagnostics for file
    access issues, including path validation and suggestions for common
    file problems in CWatM.
    
    Parameters
    ----------
    filename : str
        Full path to the problematic file
    msg : str, optional
        Error message string, by default ""
    sname : str, optional
        Setting name or context where the error occurred, by default ""
        
    Notes
    -----
    Provides enhanced diagnostics by:
    - Checking if the file exists but has other issues
    - Verifying if the directory path exists but filename is wrong
    - Suggesting common file extension alternatives (.nc4, .nc)
    - Providing context about which settings section caused the error
    
    The diagnostic information helps users quickly identify whether the issue
    is a missing directory, incorrect filename, or file permission problem.
    """
    def __init__(self, filename, msg="", sname=""):
        # don't show the error code, lines etc.
        sys.tracebacklimit = 0
        path, name = os.path.split(filename)
        if os.path.exists(filename):
            text1 = "In  \"" + sname + "\"\n"
            text1 += "filename: "+ filename + " exists, but an error was raised"
        elif os.path.exists(path):
            text1 = "In  \"" + sname + "\"\n"
            text1 += "path: "+ path + " exists\nbut filename: "+name+ " does not\n"
            text1 +="file name extension can be .nc4 or .nc\n"
        else:
            text1 = " In  \""+ sname +"\"\n"
            text1 += "searching: \""+filename+"\""
            text1 += "\npath: "+ path + " does not exists\n"

        header = "\n\n ======================== CWATM FILE ERROR ===========================\n"
        print (header + msg + text1 +"\n")

        try:
            errornumber = int(msg[6:9])
        except:
            errornumber = 100
        print ("CWatM errornumber: " + str(errornumber))
        #sys.exit(errornumber)

class CWATMDirError(CWATMError):
    """
    Specialized error handling class for directory-related errors.
    
    This class extends CWATMError to provide detailed diagnostics for directory
    access issues, helping users identify problems with output directories,
    input data directories, and path configuration in settings files.
    
    Parameters
    ----------
    filename : str
        Full path to the problematic directory
    msg : str, optional
        Error message string, by default ""
    sname : str, optional
        Setting name or context where the error occurred, by default ""
        
    Notes
    -----
    Provides enhanced diagnostics by:
    - Checking if the directory exists but has permission or other issues
    - Verifying if the parent directory exists but the target subdirectory doesn't
    - Identifying which settings section contains the problematic directory path
    - Suggesting potential solutions for common directory problems
    
    This is particularly useful for output directory configuration where users
    may specify non-existent paths or lack write permissions.
    """
    def __init__(self, filename, msg="", sname=""):
        # don't show the error code, lines etc.
        sys.tracebacklimit = 0
        path, name = os.path.split(filename)
        if os.path.exists(filename):
            text1 = "in setting name  \"" + sname + "\"\n"
            text1 += "directory name: "+ filename + " exists, but an error was raised"
        elif os.path.exists(path):
            text1 = "in setting name: \"" + sname + "\"\n"
            text1 += "directory path: "+ path + " exists\nbut: "+name+ " does not\n"

        else:
            text1 = " in settings name: \""+ sname +"\"\n"
            text1 += "searching: \""+filename+"\""
            text1 += "\npath: "+ path + " does not exists\n"

        header = "\n\n ======================== CWATM FILE ERROR ===========================\n"
        print (header + msg + text1 +"\n")

        try:
            errornumber = int(msg[6:9])
        except:
            errornumber = 100
        #sys.exit(errornumber)
        print("CWatM errornumber: " + str(errornumber))


class CWATMWarning(Warning):
    """
    Warning handling class for non-fatal CWatM issues.
    
    This class provides standardized warning messages for situations that
    don't stop model execution but should be brought to the user's attention.
    Unlike error classes, warnings don't terminate the program.
    
    Parameters
    ----------
    msg : str
        Warning message to be displayed to the user
        
    Notes
    -----
    Warnings are formatted with a distinctive header and temporarily suppress
    traceback information during initialization. The traceback limit is restored
    after initialization to maintain normal Python error handling for other issues.
    
    Use this class for:
    - Parameter values outside recommended ranges
    - Missing optional input data
    - Deprecated feature usage
    - Performance-related advisories
    """

    def __init__(self, msg):
        sys.tracebacklimit = 0
        header = "\n========================== CWATM Warning =============================\n"
        self._msg = header + msg
        sys.tracebacklimit = 1
    def __str__(self):
        return self._msg

class CWATMRunInfo(Warning):
    """
    Information display class for CWatM simulation status and settings.
    
    This class provides formatted information messages about simulation
    progress, output locations, and configuration details. Used to communicate
    important information to users without indicating errors or warnings.
    
    Parameters
    ----------
    outputS : list
        List containing output information, typically [settings_file, output_directory]
        
    Returns
    -------
    str
        Formatted information message with header and simulation details
        
    Notes
    -----
    This class is used to provide users with:
    - Confirmation of simulation settings and output locations
    - Progress updates during long model runs
    - Summary information about completed simulations
    - Configuration validation results
    
    The message format is designed to be informative and easy to locate
    in model output logs.
    """

    def __init__(self, outputS):
        header = "CWATM Simulation Information and Setting\n"
        msg = "The simulation output as specified in the settings file: " + str(outputS[0]) + " can be found in "+str(outputS[1])+"\n"
        self._msg = header + msg
    def __str__(self):
        return self._msg

