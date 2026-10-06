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

This module provides the error handling framework for the Community Water
Model: error classes for different types of failures and classes for user
communication. Errors are shown as formatted messages with diagnostic
information, without a Python traceback.

Classes
-------
CWATMError : Base error class for general CWatM errors
CWATMFileError : Specialized error class for file-related issues
CWATMDirError : Specialized error class for directory-related issues
CWATMWarning : Warning class for non-fatal issues
CWATMRunInfo : Information class for simulation status messages

Functions
---------
print_cwatm_error : Print a CWatM error and the CWatM errors it replaced

Notes
-----
All error classes extract the error number from the message string
("Error XXX: ...") and store it as attribute errornumber. The formatted message
is the text of the exception (str(e)); nothing is printed when an error is
created. run_cwatm.main prints caught errors with print_cwatm_error, and an
uncaught CWatM error is printed the same way by the exception hook installed
here - in both cases without a Python traceback. Other exceptions keep their
full traceback.
"""


import linecache
import os
import sys
import traceback

# folder of the cwatm package and its parent folder - for the line numbers of an error
_cwatmdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_rootdir = os.path.dirname(_cwatmdir)


def _cwatmframes(e):
    """Frames of the traceback of e inside the cwatm package, innermost first."""
    frames = [f for f in traceback.extract_tb(e.__traceback__) if os.path.abspath(f.filename).startswith(_cwatmdir)]
    return frames[::-1]


def _where(f):
    """File (relative to the CWatM folder), line number and function of a frame."""
    return os.path.relpath(f.filename, _rootdir) + " line " + str(f.lineno) + " (" + f.name + ")"


def _code(f, n=5):
    """The last n lines of code up to the line of frame f, with line numbers."""
    first = max(1, f.lineno - n + 1)
    lines = [linecache.getline(f.filename, i).rstrip() for i in range(first, f.lineno + 1)]
    indent = min((len(l) - len(l.lstrip()) for l in lines if l.strip()), default=0)
    return "".join("    {:>5} | {}\n".format(first + k, l[indent:]) for k, l in enumerate(lines))


def _errornumber(msg):
    """Return XXX from a message starting with "Error XXX", otherwise 100."""
    if msg.startswith("Error "):
        try:
            return int(msg[6:9])
        except ValueError:
            pass
    return 100


def _pathtext(filename, what, sname):
    """Diagnostic text for a missing or unreadable file or directory."""
    text = ""
    if sname:
        text = "In setting: \"" + sname + "\"\n"
    path, name = os.path.split(filename)
    if os.path.exists(filename):
        text += what + ": " + filename + " exists, but an error was raised\n"
    elif os.path.exists(path or "."):
        text += "path: " + (path or ".") + " exists\nbut " + what + ": " + name + " does not exist\n"
        if what == "file" and os.path.splitext(name)[1] in (".nc", ".nc4"):
            text += "file name extension can be .nc4 or .nc\n"
    else:
        text += "searching: \"" + filename + "\"\npath: " + path + " does not exist\n"
    return text


class CWATMError(Exception):
    """
    Base error handling class for CWatM errors.

    Parameters
    ----------
    msg : str
        Error message string, optionally containing error number in format
        "Error XXX: message" where XXX is a 3-digit error code

    Attributes
    ----------
    errornumber : int
        Error number XXX from the message, 100 if the message has none

    Notes
    -----
    The text of the exception (str(e)) is the formatted message with header.
    Print it with print_cwatm_error.
    """

    header = "\n\n ========================== CWATM ERROR =============================\n"

    def __init__(self, msg):
        if not msg.endswith("\n"):
            msg += "\n"
        self.errornumber = _errornumber(msg)
        super().__init__(self.header + msg)


class CWATMFileError(CWATMError):
    """
    Specialized error handling class for file-related errors.

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
    Adds diagnostics to the message: whether the file exists, or only its
    directory, or neither. For netCDF files the hint that the extension can be
    .nc4 or .nc is added.
    """

    header = "\n\n ======================== CWATM FILE ERROR ===========================\n"

    def __init__(self, filename, msg="", sname=""):
        if msg and not msg.endswith("\n"):
            msg += "\n"
        CWATMError.__init__(self, msg + _pathtext(filename, "file", sname))


class CWATMDirError(CWATMError):
    """
    Specialized error handling class for directory-related errors.

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
    Adds diagnostics to the message: whether the directory exists, or only its
    parent directory, or neither.
    """

    header = "\n\n ====================== CWATM DIRECTORY ERROR =========================\n"

    def __init__(self, filename, msg="", sname=""):
        if msg and not msg.endswith("\n"):
            msg += "\n"
        CWATMError.__init__(self, msg + _pathtext(filename, "directory", sname))


def print_cwatm_error(e, details=False):
    """
    Print a CWatM error and all CWatM errors it replaced, without traceback.

    Parameters
    ----------
    e : CWATMError
        The error to print
    details : bool, optional
        If True (flag -e) the code lines of the error are printed, by default False

    Notes
    -----
    Some CWatM errors are raised inside a try block and replaced by a more
    general one in the except block (e.g. Error 202 by Error 203). All CWatM
    errors of the chain are printed, the oldest first. A Python exception that
    led to a CWatM error is printed as one line below it. With details, each
    error gets the line where it was raised and up to 2 calling lines in CWatM.
    """
    chain = []
    while e is not None:
        chain.append(e)
        e = e.__cause__ or e.__context__
    for i in range(len(chain) - 1, -1, -1):
        if isinstance(chain[i], CWATMError):
            print(chain[i])
            if details:
                for j, f in enumerate(_cwatmframes(chain[i])[:5]):
                    print(("Raised in:   " if j == 0 else "called from: ") + _where(f))
                    if j == 0:
                        print(_code(f), end="")
            if i + 1 < len(chain) and not isinstance(chain[i + 1], CWATMError):
                text = "Python: " + type(chain[i + 1]).__name__ + ": " + str(chain[i + 1])
                frames = _cwatmframes(chain[i + 1])
                if details and frames:
                    text += "  (" + _where(frames[0]) + ")"
                print(text)


def _excepthook(etype, value, tb):
    """Print uncaught CWatM errors without traceback, all others as usual."""
    if isinstance(value, CWATMError):
        # an error while globals.py is imported (e.g. Error 301, 305, 306): Flags does not exist yet
        try:
            from cwatm.management_modules.globals import Flags
            details = Flags['error']
        except Exception:
            details = False
        print_cwatm_error(value, details)
    else:
        _default_excepthook(etype, value, tb)


_default_excepthook = sys.excepthook
sys.excepthook = _excepthook


class CWATMWarning(Warning):
    """
    Warning handling class for non-fatal CWatM issues.

    This class provides standardized warning messages for situations that
    don't stop model execution but should be brought to the user's attention.
    It is printed, not raised: print(CWATMWarning(msg)).

    Parameters
    ----------
    msg : str
        Warning message to be displayed to the user

    Notes
    -----
    Use this class for:
    - Parameter values outside recommended ranges
    - Missing optional input data
    - Deprecated feature usage
    - Performance-related advisories
    """

    def __init__(self, msg):
        super().__init__("\n========================== CWATM Warning =============================\n" + msg)


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
