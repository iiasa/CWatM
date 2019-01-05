#!/usr/bin/python

#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

"""
## -------------------------------------------------
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

__authors__ = "Peter Burek IIASA"
__version__ = "Version: 1.02"
__date__ = "04/01/2019"
__copyright__ = "Copyright 2016, IIASA"
__maintainer__ = "Peter Burek"
__status__ = "Development"


#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# to work with some versions of Linux  - a workaround with pyexpat is needed
from pyexpat import *
#import xml.dom.minidom
#import netCDF4
#from netCDF4 import Dataset

from management_modules.configuration import *
#from management_modules.messages import *



# ---------------------------

from cwatm_initial import *
from cwatm_dynamic import *


class CWATModel(CWATModel_ini, CWATModel_dyn):
	"""
	Initial and dynamic part of the CWATM model

	* initial part takes care of all the non temporal initialiation procedures

	* dynamic part loops over time
	
	
	"""

# ==================================================

def CWATMexe():
	"""
	Base subroutine of the CWATM model

	* parses the settings file
	* read the information for the netcdf files
	* check if dates are alright
	* check flags for screen output
	* runs the model


	"""


	parse_configuration(settings)
	#print option
	#print binding
	# read all the possible option for modelling and for generating output
	# read the settings file with all information about the catchments(s)
	# read the meta data information for netcdf outputfiles
	read_metanetcdf(cbinding('metaNetcdfFile'), 'metaNetcdfFile')

	#os.chdir(outputDir[0])
	# this prevent from using relative path in settings!

	checkifDate('StepStart','StepEnd','SpinUp')
	# checks if end date is later than start date and puts both in modelSteps


	CWATM = CWATModel()
	stCWATM = ModelFrame(CWATM, firstTimestep=dateVar["intStart"], lastTimeStep=dateVar["intEnd"])


	"""
	----------------------------------------------
	Deterministic run
	----------------------------------------------
	"""
	print(CWATMRunInfo(outputDir = outputDir[0]))
	start_time = datetime.datetime.now().time()
	if Flags['loud']:
		print("%-6s %10s %11s\n" %("Step","Date","Discharge"), end=' ')

	stCWATM.run()


	# cProfile.run('stLisflood.run()')
	# python -m cProfile -o  l1.pstats cwatm.py settings1.ini
	# gprof2dot -f pstats l1.pstats | dot -T png -o callgraph.png
	# pyreverse -AS -f ALL -o png cwatm.py -p Main

	if Flags['printtime']:
		print("\n\nTime profiling")
		print("%2s %-17s %10s %8s" %("No","Name","time[s]","%"))

		timeSum = np.array(timeMesSum)
		timePrint = timeSum
		for i in range(len(timePrint)):
			print("%2i %-17s %10.2f %8.1f"  %(i,timeMesString[i],timePrint[i],100 * timePrint[i] / timePrint[-1]))
	current_time = datetime.datetime.now().time()
	print(start_time.isoformat())
	print(current_time.isoformat())

# ==================================================
# ============== USAGE ==============================
# ==================================================


def usage():
	"""
	Prints some lines describing how to use this program which arguments and parameters it accepts, etc

	* -q --quiet       output progression given as .
	* -v --veryquiet   no output progression is given
	* -l --loud        output progression given as time step, date and discharge
	* -c --check       input maps and stack maps are checked, output for each input map BUT no model run
	* -h --noheader    .tss file have no header and start immediately with the time series
	* -t --printtime   the computation time for hydrological modules are printed

	"""
	print('CWatM - Community Water model')
	print('Authors: ', __authors__)
	print('Version: ', __version__)
	print('Date: ', __date__)
	print('Status: ', __status__)
	print("""
	Arguments list:
	settings.ini     settings file

	-q --quiet       output progression given as .
	-v --veryquiet   no output progression is given
	-l --loud        output progression given as time step, date and discharge
	-c --check       input maps and stack maps are checked, output for each input map BUT no model run
	-h --noheader    .tss file have no header and start immediately with the time series
	-t --printtime   the computation time for hydrological modules are printed
	-w --warranty    copyright and warranty information
	""")
	sys.exit(1)

def GNU():
	"""
	prints GNU General Public License information

	"""


	print('CWatM - Community Water model')
	print('Authors: ', __authors__)
	print('Version: ', __version__)
	print('Date: ', __date__)
	print()
	print("""
	CWATM is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details
	<http://www.gnu.org/licenses/>.
	""")
	sys.exit(1)

def headerinfo():
	"""
	Print the information on top of each run
	"""

	print("CWATM - Community Water Model ",__version__," Date: ",__date__," ")
	print("International Institute of Applied Systems Analysis (IIASA)")
	print("Running under platform: ", platform1)
	print("-----------------------------------------------------------")
current_time = datetime.datetime.now().time()
#print current_time.isoformat()

# ==================================================
# ============== MAIN ==============================
# ==================================================

if __name__ == "__main__":

	if len(sys.argv) < 2:
		usage()

	CWatM_Path = os.path.dirname(sys.argv[0])
	CWatM_Path = os.path.abspath(CWatM_Path)

	settings = sys.argv[1]    # setting.ini file

	args = sys.argv[2:]
	globalFlags(args)
	if Flags['use']: usage()
	if Flags['warranty']: GNU()
	# setting of global flag e.g checking input maps, producing more output information
	if not(Flags['veryquiet']) and not(Flags['quiet']) : headerinfo()
	CWATMexe()
