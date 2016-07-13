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
# --------------------------------------------------
"""

__authors__ = "Peter Burek IIASA"
__version__ = "Version: 0.99"
__date__ = "16/05/2016"
__copyright__ = "Copyright 2016, IIASA"
__maintainer__ = "Peter Burek"
__status__ = "Development"


#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# to work with the new grid engine  - a workaround with pyexpat is needed
import xml.dom.minidom
from netCDF4 import Dataset
from pcraster import *
from pcraster.framework import *

from management_modules.configuration import *
from management_modules.messages import *

# ---------------------------

from cwatm_initial import *
from cwatm_dynamic import *


class CWATModel(CWATModel_ini, CWATModel_dyn):
    """ Initial and dynamic part of the CWat model
	    initial part takes care of all the non temporal initialiation procedures
		dynamic part loops over time
    """

# ==================================================

def CWATMexe():

    parse_configuration(settings)
    print option
    print binding
    # read all the possible option for modelling and for generating output
    # read the settings file with all information about the catchments(s)

    ### bindkey = sorted(binding.keys())

    #os.chdir(outputDir[0])
    # this prevent from using relative path in settings!

    checkifDate('StepStart','StepEnd')
    # checks if end date is later than start date and puts both in modelSteps

    #if option['InitCWATM']: print "INITIALISATION RUN"
    #print "Start - End: ",modelSteps[0]," - ", modelSteps[1]
    if Flags['loud']:
        print"%-6s %10s %11s\n" %("Step","Date","Discharge"),

    CWATM = CWATModel()
    stCWATM = DynamicFramework(CWATM, firstTimestep=modelSteps[0], lastTimeStep=modelSteps[1])
    stCWATM.rquiet = True
    stCWATM.rtrace = False


    """
    ----------------------------------------------
    Deterministic run
    ----------------------------------------------
    """
    print CWATMRunInfo(outputDir = outputDir[0])
    stCWATM.run()

		# cProfile.run('stLisflood.run()')
    # python -m cProfile -o  l1.pstats lisf1.py settingsNew3.xml
    # gprof2dot -f pstats l1.pstats | dot -Tpng -o callgraph.png

    if Flags['printtime']:
        print "\n\nTime profiling"
        print "%2s %-17s %10s %8s" %("No","Name","time[s]","%")
        div = 1
        timeSum = np.array(timeMesSum)
        timePrint = timeSum
        for i in xrange(len(timePrint)):
            print "%2i %-17s %10.2f %8.1f"  %(i,timeMesString[i],timePrint[i],100 * timePrint[i] / timePrint[-1])


# ==================================================
# ============== USAGE ==============================
# ==================================================


def usage():
    """ prints some lines describing how to use this program
        which arguments and parameters it accepts, etc
    """
    print 'CWatM - Community Water model'
    print 'Authors: ', __authors__
    print 'Version: ', __version__
    print 'Date: ', __date__
    print 'Status: ', __status__
    print """
    Arguments list:
    settings.ini     settings file

    -q --quiet       output progression given as .
    -v --veryquiet   no output progression is given
    -l --loud        output progression given as time step, date and discharge
    -c --check       input maps and stack maps are checked, output for each input map BUT no model run
    -h --noheader    .tss file have no header and start immediately with the time series
    -t --printtime   the computation time for hydrological modules are printed
    """
    sys.exit(1)

def headerinfo():

   print "CWATM - Community Water Model ",__version__," ",__date__,
   print """
Community Water Model
International Institute of Applied Systems Analysis (IIASA)
----------------------------------------------------------"""


# ==================================================
# ============== MAIN ==============================
# ==================================================

if __name__ == "__main__":

    if len(sys.argv) < 2:
        usage()

    CWatM_Path = os.path.dirname(sys.argv[0])
    CWatM_Path = os.path.abspath(CWatM_Path)
    optionxml = os.path.normpath(CWatM_Path + "/OptionTserieMaps.xml")

    settings = sys.argv[1]    # setting.ini file

    args = sys.argv[2:]
    globalFlags(args)
    # setting of global flag e.g checking input maps, producing more output information
    if not(Flags['veryquiet']) and not(Flags['quiet']) : headerinfo()
    CWATMexe()
