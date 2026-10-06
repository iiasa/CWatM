#!/usr/bin/env python3

"""
::

 -------------------------------------------------
 ######## ##          ##  ####  ######  ##    ##
 ##       ##          ## ##  ##   ##   ####  ####
 ##        ##        ##  ##  ##   ##   ## #### ##
 ##        ##   ##   ## ########  ##  ##   ##   ##
 ##         ## #### ##  ##    ##  ##  ##        ##
 ##         ####  #### ##      ## ## ##          ##
 ##########  ##    ##  ##      ## ## ##          ##

 Community WATer Model


CWATM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

CWATM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details
<http://www.gnu.org/licenses/>.

# --------------------------------------------------
"""
import os
os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")   # must precede any netCDF4/HDF5 import
import sys

from cwatm import __author__, __version__, __date__, __copyright__, __maintainer__, __status__
from cwatm.run_cwatm import main, mainwarm, parse_args, usage, GNU, run_from_command_line

# mainwarm for calibration
# exit code 0 if the run was successful, 1 if it stopped with an error
if __name__ == "__main__":
    run_from_command_line()



