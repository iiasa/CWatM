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

    """
    Runoff concentration

    this is the part between runoff generation and routing
    for each gridcell and for each land cover class the generated runoff is concentrated at a corner of a gridcell
    this concentration needs some lag-time (and peak time) and leads to diffusion
    lag-time/ peak time is calculated using slope, length and land cover class
    diffusion is calculated using a triangular-weighting-function

    :math:`Q(t) = \sum_{i=0}^{max} c(i) * Q_{\mathrm{GW}} (t - i + 1)`

    where :math:`c(i) = \int_{i-1}^{i} {2 \over{max}} - | u - {max \over {2}} | * {4 \over{max^2}} du`

    see also:

    http://stackoverflow.com/questions/24040984/transformation-using-triangular-weighting-function-in-python


    """

    def __init__(self, runoff_concentration_variable):
        self.var = runoff_concentration_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """
        Initial part of the  runoff concentration module

        Setting the peak time for:

        * surface runoff = 3
        * interflow = 4
        * baseflow = 5

        based on the slope the concentration time for each land cover type is calculated

        Note:
            only if option **includeRunoffConcentration** is TRUE
        """

        if checkOption('includeRunoffConcentration'):

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



            self.var.coverTypes= list(map(str.strip, cbinding("coverTypes").split(",")))

            #     /\   peak time for concentrated runoff
            #   /   \
            #  ---*--
            #landcoverAll = ['runoff_peak']
            #for variable in landcoverAll:  vars(self.var)[variable] = np.tile(globals.inZero, (6, 1))

            # Load run off concentration coefficient

            # for calibration a general runoff concentration factor is loaded
            runoffConc_factor = loadmap('runoffConc_factor')

            i = 0
            self.var.runoff_peak = []
            max = globals.inZero
            for coverType in self.var.coverTypes:
                tpeak_cover = runoffConc_factor * tpeak * loadmap(coverType + "_runoff_peaktime")
                tpeak_cover = np.minimum(np.maximum(tpeak_cover, 0.5,),3.0)
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
            self.var.tpeak_interflow = np.minimum(np.maximum(self.var.tpeak_interflow, 0.5, ), 4.0)
            self.var.tpeak_baseflow = runoffConc_factor * tpeak * loadmap("baseflow_runoff_peaktime")
            #self.var.tpeak_baseflow = 0.5
            self.var.tpeak_baseflow = np.minimum(np.maximum(self.var.tpeak_baseflow, 0.5, ), 5.0)

            max = np.where(self.var.tpeak_baseflow > max, self.var.tpeak_baseflow, max)
            self.var.maxtime_runoff_conc = int(np.ceil(2 * np.amax(max)))
            max = 10
            if self.var.maxtime_runoff_conc > 10: max = self.var.maxtime_runoff_conc

            # array with concentrated runoff
            #self.var.runoff_conc = np.tile(globals.inZero, (self.var.maxtime_runoff_conc, 1))
            self.var.runoff_conc = []
            #self.var.runoff_conc = np.tile(globals.inZero, (self.var.maxtime_runoff_conc, 1))
            self.var.runoff_conc = np.tile(globals.inZero,(max,1))
            for i in range(self.var.maxtime_runoff_conc):
                self.var.runoff_conc[i] = self.var.init_module.load_initial("runoff_conc", number = i+1)




# --------------------------------------------------------------------------		
		
    def dynamic(self):
        """
        Dynamic part of the runoff concentration module

        For surface runoff for each land cover class  and for interflow and for baseflow the
        runoff concentration time is calculated

        Note:
            the time demanding part is calculated in a c++ library

        """

        def runoff_concentration(lagtime, peak, fraction,flow, flow_conc):
            """
            Part which is transferred to C++ for computational speed

            :param lagtime:
            :param peak:
            :param fraction:
            :param flow:
            :param flow_conc:
            :return:
            """

            areaFractionOld = 0.0
            div = 2 * np.power(peak, 2)

            for lag in range(lagtime):
                lag1 = np.float(lag + 1)
                lag1alt = 2 * peak - lag1
                area = np.power(lag1, 2) / div
                areaAlt = 1 - np.power(lag1alt, 2) / div

                areaFractionSum = np.where(lag1 <= peak, area + globals.inZero, areaAlt + globals.inZero)
                areaFractionSum = np.where(lag1alt > 0, areaFractionSum, 1.0 + globals.inZero)
                areaFraction = areaFractionSum - areaFractionOld
                areaFractionOld = areaFractionSum.copy()

                flow_conc[lag] += fraction * flow * areaFraction
            return flow_conc

        self.var.sum_landSurfaceRunoff = globals.inZero.copy()
        #self.var.sum_directRunoff = globals.inZero.copy()

        if not(checkOption('includeRunoffConcentration')):


            for No in range(6):
                #self.var.sum_directRunoff += self.var.fracVegCover[No] * self.var.directRunoff[No]
                self.var.landSurfaceRunoff[No] = self.var.directRunoff[No] + self.var.interflow[No]
                self.var.sum_landSurfaceRunoff += self.var.fracVegCover[No] * self.var.landSurfaceRunoff[No]

            self.var.runoff = self.var.sum_landSurfaceRunoff + self.var.baseflow


        # -------------------------------------------------------
        # runoff concentration: triangular-weighting method
        else:
            # shifting array
            self.var.runoff_conc = np.roll(self.var.runoff_conc, -1,axis=0)
            self.var.runoff_conc[self.var.maxtime_runoff_conc-1] = globals.inZero



            for No in range(6):
               #self.var.runoff_conc = runoff_concentration(self.var.maxtime_runoff_conc,self.var.runoff_peak[No],self.var.fracVegCover[No] ,self.var.directRunoff[No], self.var.runoff_conc)
               lib2.runoffConc(self.var.runoff_conc, self.var.runoff_peak[No],self.var.fracVegCover[No] ,self.var.directRunoff[No],self.var.maxtime_runoff_conc,maskinfo['mapC'][0])


            # interflow time of concentration
            #self.var.runoff_conc = runoff_concentration(self.var.maxtime_runoff_conc, self.var.tpeak_interflow, 1.0, self.var.sum_interflow, self.var.runoff_conc)
            lib2.runoffConc(self.var.runoff_conc, self.var.tpeak_interflow,globals.inZero +1 ,self.var.sum_interflow,self.var.maxtime_runoff_conc,maskinfo['mapC'][0])

            self.var.sum_landSurfaceRunoff = self.var.runoff_conc[0].copy()

            # baseflow time of concentration

            #self.var.runoff_conc = runoff_concentration(self.var.maxtime_runoff_conc, self.var.tpeak_baseflow, 1.0, self.var.baseflow, self.var.runoff_conc)
            lib2.runoffConc(self.var.runoff_conc, self.var.tpeak_baseflow,globals.inZero +1 ,self.var.baseflow,self.var.maxtime_runoff_conc,maskinfo['mapC'][0])


            # -------------------------------------------------------------------------------
            #  --- from routing module -------
            #runoff from landSurface cells (unit: m)
            #self.var.runoff = self.var.sum_landSurfaceRunoff + self.var.baseflow
            self.var.runoff = self.var.runoff_conc[0].copy()








