# -------------------------------------------------------------------------
# Name:        ENVIRONMENTAL FLOW module
# Purpose: Environmental flow calculation module for ecosystem water requirements.
# Computes minimum water flows needed to maintain river ecosystem health.
# Supports water allocation decisions balancing human and environmental needs.
#
# Author:      PB
# Created:     13/07/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


def freeMemory():
    """
    Free physical memory of the computer in bytes, None if it cannot be found out.
    A limit of a job on a cluster (e.g. Slurm) is not seen.
    """
    if os.name == "nt":
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                        ("available", ctypes.c_ulonglong), ("totalPage", ctypes.c_ulonglong), ("availPage", ctypes.c_ulonglong),
                        ("totalVirtual", ctypes.c_ulonglong), ("availVirtual", ctypes.c_ulonglong), ("extended", ctypes.c_ulonglong)]

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        return status.available if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)) else None
    try:
        return os.sysconf('SC_AVPHYS_PAGES') * os.sysconf('SC_PAGE_SIZE')
    except (AttributeError, ValueError, OSError):
        return None


class environflow(object):
    """
    Environmental flow calculation module.

    Calculates the mean and low flows of the daily discharge of the whole period and of each month, and from these
    the environmental flow requirement. The discharge comes either from an existing file (EFDis, then the run ends
    after the calculation) or from the discharge output of this run (calc_ef_afterRun, calculated on the last day).

    Attributes
    ----------
    var : object
        Model variables container
    model : object
        CWatM model instance

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit
    ===================================  ==========    ======================================================================  =====
    MAF                                  Array         Mean of discharge for all days                                          m3 s-
    Q90                                  Array         10% of the lowest discharge for all days                                m3 s-
    MMF                                  Array         Mean of discharge for each month separately                             m3 s-
    MQ90                                 Array         10% of lowest discharge for each month separately                       m3 s-
    EF_VMF                               Array         EF requirement with Variable Monthly Flow: Pastor et al.(2014): Accoun  m3 s-
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize the environmental flow module.

        Parameters
        ----------
        model : object
            CWatM model instance containing variables and configuration
        """
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Check the settings of the environmental flow calculation and find the discharge files.

        Stops with an error if no discharge is available or the period does not cover all 12 months, so that a long
        run does not fail at its end. The results are zero maps until the calculation.
        """

        if checkOption('calc_environflow'):
            if returnBool('calc_ef_afterRun'):
                # OUT_MAP_Daily can be in any section with an OUT_Dir
                discharge = [m for key in outMap if key.endswith('_out_map_daily') for m in outMap[key]
                             if m != "None" and m[1] == 'discharge']
                if not discharge:
                    msg = ("Error 128: OUT_MAP_Daily = discharge is not defined in any section \n "
                           "of the settings file: \"" + settingsfile[0] + "\"\n")
                    raise CWATMError(msg)
                # the output of this run: starts at the spin up date, not cut, north up. Used places as in multinetdf:
                # 0: file, 1: index of the first day, 5: cut the map, 7: turn the latitude
                meteofiles['EFDis'] = {0: [discharge[0][0], 0, None, None, None, False, None, False]}

            # all 12 months are needed for the monthly values (-c runs only one day and calculates nothing)
            if not Flags['check']:
                months = set(d.month for d in dateVar['dates'][dateVar['intSpin'] - 1:dateVar['intEnd']])
                missing = [str(m) for m in range(1, 13) if m not in months]
                if missing:
                    msg = "Error 165: Environmental flow needs all 12 months from SpinUp to StepEnd\n"
                    msg += "Months without a day: " + " ".join(missing)
                    raise CWATMError(msg)

                # all days of all cells are held in memory: 4 bytes per value, 2 bytes for the check of missing values.
                # A warning only: the free memory now is not the free memory at the time of the calculation
                needed = 6. * maskinfo['mapC'][0] * (dateVar['intEnd'] - dateVar['intSpin'] + 1)
                free = freeMemory()
                if free is not None and needed > free:
                    msg = "Environmental flow needs about %.1f GB of memory for its calculation, " % (needed / 1e9)
                    msg += "but only %.1f GB are free" % (free / 1e9)
                    print(CWATMWarning(msg))

            if not returnBool('calc_ef_afterRun'):
                multinetdf(["EFDis"], startcheck='dateStart')

            self.var.MAF = globals.inZero.copy()
            self.var.Q90 = globals.inZero.copy()
            self.var.MMF = np.zeros(shape=[12, maskinfo['mapC'][0]])
            self.var.MQ90 = self.var.MMF.copy()
            self.var.EF_VMF = self.var.MMF.copy()

    # --------------------------------------------------------------------------

    def dynamic(self):
        """
        Calculate the environmental flow from the daily discharge of the whole period.

        Runs once: if the discharge comes from a file on the first day, after a run on the last day.
        With -c nothing is calculated, only one day runs: the results stay zero maps.
        """

        if not checkOption('calc_environflow') or Flags['check']:
            return
        afterRun = returnBool('calc_ef_afterRun')
        if afterRun and dateVar['currDate'] != dateVar['dateEnd']:
            return

        # month of each day from the spin up date to the last day, in the calendar of the netcdf files
        datearray = dateVar['dates'][dateVar['intSpin'] - 1:dateVar['intEnd']]
        montharray = np.array([d.month for d in datearray])

        # create empty array for all discharge data (float32: half the memory, the output files are float32 too)
        disall = np.empty(shape=[montharray.shape[0], maskinfo['mapC'][0]], dtype=np.float32)

        # after the run the last day is not in the file yet (the output comes behind this module)
        daysFromFile = montharray.shape[0] - 1 if afterRun else montharray.shape[0]
        if afterRun:
            disall[-1, :] = self.var.discharge

        name = 'EFDis'
        filename = readDischargeFiles(name, disall, daysFromFile)

        # missing values: on some days the statistics would be wrong -> error. A cell missing on all days has
        # no discharge in the file (e.g. a cell at the coast with another mask): flow 0, with a warning
        missing = np.isnan(disall[:daysFromFile])
        if missing.any():
            always = missing.all(axis=0)
            someDays = np.flatnonzero((missing & ~always).any(axis=1))
            if someDays.size > 0:
                day = datearray[someDays[0]]
                msg = "Error 167: Discharge has missing values on " + str(someDays.size) + " days, first: "
                msg += "%02d/%02d/%d\n" % (day.day, day.month, day.year)
                raise CWATMFileError(filename, msg, sname=name)
            msg = "Discharge files have no value at " + str(np.count_nonzero(always)) + " cells of the mask map: "
            msg += "their discharge is taken as 0 for the environmental flow"
            print(CWATMWarning(msg))
            disall[:, always] = 0.
        del missing

        # the means are summed up in float64, float32 loses accuracy over long series
        self.var.MAF = np.mean(disall, axis=0, dtype=np.float64)

        self.var.MMF = np.empty(shape=[12, maskinfo['mapC'][0]])
        self.var.MQ90 = np.empty(shape=[12, maskinfo['mapC'][0]])
        for i in range(12):
            dispermonth = disall[montharray == (i + 1), :]
            self.var.MMF[i] = np.mean(dispermonth, axis=0, dtype=np.float64)
            self.var.MQ90[i] = np.percentile(dispermonth, 10, axis=0, overwrite_input=True)
        del dispermonth

        # has to be the last one: overwrite_input (no copy of the array) mixes up the order of the days in disall
        self.var.Q90 = np.percentile(disall, 10, axis=0, overwrite_input=True).astype(np.float64)

        # calculating EF requirement with Variable Monthly Flow p. 5049
        # A.V.Pastor et al.(2014): Accounting for environmental flow requirements in global water assessments,
        # Hydrol Earth Syst Sci, 18, p5041-5059

        self.var.EF_VMF = np.empty(shape=[12, maskinfo['mapC'][0]])
        for i in range(12):
            self.var.EF_VMF[i] = np.where(self.var.MMF[i] <= (0.4 * self.var.MAF), 0.6 * self.var.MMF[i],
                                          np.where(self.var.MMF[i] > (0.8 * self.var.MAF),
                                                   0.3 * self.var.MMF[i], 0.45 * self.var.MMF[i]))
