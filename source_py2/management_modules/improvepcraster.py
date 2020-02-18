# -------------------------------------------------------------------------
# Name:        improve/correct some pcraster routines
# Purpose:
#
# Author:      burekpe
#
# Created:     16/05/2016
# Copyright:   (c) burekpe 2016
# -------------------------------------------------------------------------


import datetime
import time as xtime
import os

#from pcraster import*
#from pcraster.framework import *


from pcraster2.dynamicFramework import *


from globals import *
from cwatm.management_modules.timestep import *

# --------------------------------------------------

class DynamicFramework2(DynamicFramework):
    """
    Framework class for dynamic models.
    `userModel`
    Instance that models the Dynamic Model Concept <dynamicModelConcept>.
    `lastTimeStep`   Last timestep to run.
    `firstTimestep`  Sets the starting timestep of the model (optional, default is 1).
    Updated by improvepcraster.py
    """



    def run(self):
        """
        Run the dynamic user model.
        """
        self._atStartOfScript()
        if(hasattr(self._userModel(), "resume")):
            #if self._userModel().firstTimeStep() == 1:
            # replaced this because starting date is not always the 1
            if self._userModel().firstTimeStep() == datetoInt(binding['StepStart']):
               self._runInitial()
            else:
               self._runResume()
        else:
            self._runInitial()

        self._runDynamic()

        # Only execute this section while running filter frameworks.
        if hasattr(self._userModel(), "suspend") and \
        hasattr(self._userModel(), "filterPeriod"):
          self._runSuspend()

        return 0



    # Adjusting the def _atStartOfTimeStep defined in DynamicFramework for a real quiet output

    rquiet = False
    rtrace = False

    def _atStartOfTimeStep(self, step):
        """
        Adjusting the def _atStartOfTimeStep defined in DynamicFramework
        for a real quiet output

        :param step:
        :return:
        """
        self._userModel()._setInTimeStep(True)
        if not self.rquiet:
            if not self.rtrace:
                msg = u"#"

            else:
                msg = u"%s<time step=\"%s\">\n" % (self._indentLevel(), step)
            sys.stdout.write(msg)
            sys.stdout.flush()

