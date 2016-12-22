# -------------------------------------------------------------------------
# Name:        runoff concentration module
# Purpose:	   this is the part between runoff generation and routing
#              for each gridcell and for each land cover class the generated runoff is concentrated at a corner of a gridcell
#              this concentration needs some lag-time (and peak time) and leads to diffusion
#              lag-time/ peak time is calculated using slope, length and land cover class
#              diffusion is calculated using a triangular-weighting-function
# Author:      PB
#
# Created:     16/12/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *

class runoff_concentration(object):

    """@package
    # ************************************************************
    # ***** runoff concentration *****************************************
    # ************************************************************
    """

    def __init__(self, runoff_concentration_variable):
        self.var = runoff_concentration_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the  runoff concentration module
        """
        if option['includeRunoffConcentration']:

            # --- Topography -----------------------------------------------------
            tanslope = loadmap('tanslope')
            # self.var.slopeLength = loadmap('slopeLength')
            # setting slope >= 0.00001 to prevent 0 value
            tanslope = np.maximum(tanslope, 0.00001)

            # Natural   Resources   Conservation Service TR55 - upland method
            # T lag = 0.6 T conc = 0.6 * Flowlength / (60* Velocity); V = K * Slope^0.5
            # K paved = 6, k forest = 0.3, grass  = 0.6

            # time to peak in days
            tpeak = 0.5 + 0.6 * 50000.0 / (1440.0 * 60 * np.power(tanslope,0.5))



            self.var.coverTypes= map(str.strip, binding["coverTypes"].split(","))

            #     /\   peak time for concentrated runoff
            #   /   \
            #  ---*--
            #landcoverAll = ['runoff_peak']
            #for variable in landcoverAll:  vars(self.var)[variable] = np.tile(globals.inZero, (6, 1))

            # Load run off concentration coefficient

            # for calibartion a general runoff concentration factor is loaded
            runoffConc_factor = loadmap('runoffConc_factor')

            i = 0
            self.var.runoff_peak = []
            max = globals.inZero
            for coverType in self.var.coverTypes:
                tpeak_cover = runoffConc_factor * tpeak * loadmap(coverType + "_runoff_peaktime")
                tpeak_cover = np.minimum(np.maximum(tpeak_cover, 0.5,),10.0)
                if "coverType" == "water": tpeak_cover = 0.5
                #tpeak_cover = 0.5
                self.var.runoff_peak.append(tpeak_cover)


                max = np.where(self.var.runoff_peak[i] > max, self.var.runoff_peak[i], max)
                i += 1
            #     /\   maximal timestep for concentrated runoff
            #   /   \
            #  ------*

            self.var.tpeak_interflow = runoffConc_factor * tpeak * loadmap("interflow_runoff_peaktime")
            #self.var.tpeak_interflow = 0.5
            self.var.tpeak_interflow = np.minimum(np.maximum(self.var.tpeak_interflow, 0.5, ), 10.0)
            self.var.tpeak_baseflow = runoffConc_factor * tpeak * loadmap("baseflow_runoff_peaktime")
            #self.var.tpeak_baseflow = 0.5
            self.var.tpeak_baseflow = np.minimum(np.maximum(self.var.tpeak_baseflow, 0.5, ), 20.0)

            max = np.where(self.var.tpeak_baseflow > max, self.var.tpeak_baseflow, max)
            self.var.maxtime_runoff_conc = int(np.ceil(2 * np.amax(max)))

            # array with concentrated runoff
            #self.var.runoff_conc = np.tile(globals.inZero, (self.var.maxtime_runoff_conc, 1))
            self.var.runoff_conc = []
            #for i in xrange(self.var.maxtime_runoff_conc-1):
            #    self.var.runoff_conc.append(globals.inZero)
            self.var.runoff_conc = np.tile(globals.inZero, (self.var.maxtime_runoff_conc, 1))


# --------------------------------------------------------------------------		
		
    def dynamic(self):
        """ Dynamic part of the runoff concentration module
#              for each gridcell and for each land cover class the generated runoff is concentrated at a corner of a gridcell
#              this concentration needs some lag-time (and peak time) and leads to diffusion
#              lag-time/ peak time is calculated using slope, length and land cover class
#              diffusion is calculated using a triangular-weighting-function
        Args:
            coverType: coverType land cover type: forest, grassland ..
            No: Number of land cover type: forest = 0, grassland = 1 ...
        """

        self.var.sum_landSurfaceRunoff = globals.inZero.copy()

        if not(option['includeRunoffConcentration']):

            for No in xrange(6):
                self.var.landSurfaceRunoff[No] = self.var.directRunoff[No] + self.var.interflow[No]
                self.var.sum_landSurfaceRunoff += self.var.fracVegCover[No] * self.var.landSurfaceRunoff[No]

                self.var.runoff = self.var.sum_landSurfaceRunoff + self.var.baseflow



        # -------------------------------------------------------
        # runoff concentration: triangular-weighting method
        else:
            # shifting array
            self.var.runoff_conc = np.roll(self.var.runoff_conc, -1,axis=0)
            self.var.runoff_conc[self.var.maxtime_runoff_conc-1] = globals.inZero



            for No in xrange(6):
                div = 2 * np.power(self.var.runoff_peak[No], 2)
                areaFractionOld = 0.0
                for lag in xrange(self.var.maxtime_runoff_conc):

                    lag1 = np.float(lag+1)
                    lag1alt = 2 * self.var.runoff_peak[No] - lag1
                    area = np.power(lag1,2)  / div
                    areaAlt = 1- np.power(lag1alt,2) / div
                    areaFractionSum = np.where(lag1 <=  self.var.runoff_peak[No], area + globals.inZero, areaAlt + globals.inZero)
                    areaFractionSum = np.where(lag1alt > 0, areaFractionSum, 1.0 + globals.inZero)
                    areaFraction = areaFractionSum - areaFractionOld
                    areaFractionOld = areaFractionSum.copy()

                    self.var.runoff_conc[lag] += self.var.fracVegCover[No] * self.var.directRunoff[No] * areaFraction
                    #self.var.runoff_conc[lag] = self.var.runoff_conc[lag]  + 1.0 * areaFraction

            # interflow time of concentration
            areaFractionOld = 0.0
            for lag in xrange(self.var.maxtime_runoff_conc):
                lag1 = np.float(lag + 1)
                div = 2 * np.power(self.var.tpeak_interflow, 2)
                lag1alt = 2 * self.var.tpeak_interflow - lag1
                area = np.power(lag1, 2) / div
                areaAlt  = 1 - np.power(lag1alt, 2)  / div

                areaFractionSum = np.where(lag1 <= self.var.tpeak_interflow, area + globals.inZero, areaAlt + globals.inZero)
                areaFractionSum = np.where(lag1alt > 0, areaFractionSum, 1.0 + globals.inZero)
                areaFraction = areaFractionSum - areaFractionOld
                areaFractionOld = areaFractionSum.copy()
                self.var.runoff_conc[lag] +=  self.var.sum_interflow * areaFraction

            self.var.sum_landSurfaceRunoff = self.var.runoff_conc[0].copy()

            # baseflow time of concentration
            areaFractionOld = 0.0
            for lag in xrange(self.var.maxtime_runoff_conc):
                lag1 = np.float(lag + 1)
                div = 2 * np.power(self.var.tpeak_baseflow, 2)
                lag1alt = 2 * self.var.tpeak_baseflow - lag1
                area = np.power(lag1, 2) / div
                areaAlt  = 1 - np.power(lag1alt, 2)  / div

                areaFractionSum = np.where(lag1 <= self.var.tpeak_baseflow, area + globals.inZero, areaAlt + globals.inZero)
                areaFractionSum = np.where(lag1alt > 0, areaFractionSum, 1.0 + globals.inZero)
                areaFraction = areaFractionSum - areaFractionOld
                areaFractionOld = areaFractionSum.copy()

                self.var.runoff_conc[lag] +=  self.var.baseflow * areaFraction


            # -------------------------------------------------------------------------------
            #  --- from routing module -------
            #runoff from landSurface cells (unit: m)
            #self.var.runoff = self.var.sum_landSurfaceRunoff + self.var.baseflow
            self.var.runoff = self.var.runoff_conc[0].copy()







