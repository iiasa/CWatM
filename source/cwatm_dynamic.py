# -------------------------------------------------------------------------
# Name:       CWAT Model Dynamic
# Purpose:
#
# Author:      burekpe
#
# Created:     16/05/2016
# Copyright:   (c) burekpe 2016
# -------------------------------------------------------------------------


#from global_modules.add1 import *
from pcraster import*
from pcraster.framework import *


from management_modules.checks import *
from management_modules.improvepcraster import *
from management_modules.messages import *




class CWATModel_dyn(DynamicModel):

    # =========== DYNAMIC ====================================================

    def dynamic(self):
        """ Dynamic part of LISFLOOD
            calls the dynamic part of the hydrological modules
        """
        del timeMes[:]
        timemeasure("Start dynamic")
        self.CalendarDate = self.CalendarDayStart + datetime.timedelta(days=(self.currentTimeStep()-1) * self.DtDay)
        self.CalendarDay = int(self.CalendarDate.strftime("%j"))
        #correct method to calculate the day of the year

        i = self.currentTimeStep()
#        if i==1:    globals.cdfFlag = [0, 0, 0, 0 ,0 ,0,0]
          # flag for netcdf output for all, steps and end
          # set back to 0,0,0,0,0,0 if new Monte Carlo run

        self.TimeSinceStart = self.currentTimeStep() - self.firstTimeStep() + 1

        if Flags['loud']:
            print "%-6i %10s" %(self.currentTimeStep(),self.CalendarDate.strftime("%d/%m/%Y")) ,
        else:
            if not(Flags['check']):
                if (Flags['quiet']) and (not(Flags['veryquiet'])):
                    sys.stdout.write(".")
                if (not(Flags['quiet'])) and (not(Flags['veryquiet'])):
                    sys.stdout.write("\r%d" % i)
                    sys.stdout.flush()

        # ************************************************************
        """ up to here it was fun, now the real stuff starts
        """
        self.readmeteo_module.dynamic()
        timemeasure("Read meteo") # 1. timing after read input maps

        #if Flags['check']: return  # if check than finish here

        """ Here it starts with hydrological modules:
        """
        # ***** RAIN AND SNOW *****************************************
        self.snowfrost_module.dynamic()
        timemeasure("Snow")  # 2. timing

        # ***** READ land use fraction maps***************************
        """
        self.landusechange_module.dynamic()

        # ***** READ LEAF AREA INDEX DATA ****************************
        self.leafarea_module.dynamic()

        # ***** READ variable water fraction ****************************
        self.evapowater_module.dynamic_init()

        # ***** READ INFLOW HYDROGRAPHS (OPTIONAL)****************
        self.inflow_module.dynamic()
        timemeasure("Read LAI") # 2. timing after LAI and inflow

        # ***** RAIN AND SNOW *****************************************
        self.snow_module.dynamic()
        timemeasure("Snow")  # 3. timing after LAI and inflow

        # ***** FROST INDEX IN SOIL **********************************
        self.frost_module.dynamic()
        timemeasure("Frost")  # 4. timing after frost index

        # ************************************************************
        # ****Looping soil 2 times - second time for forest fraction *
        # ************************************************************

        for soilLoop in xrange(3):
            self.soilloop_module.dynamic(soilLoop)
            # soil module is repeated 2 times:
            # 1. for remaining areas: no forest, no impervious, no water
            # 2. for forested areas
            timemeasure("Soil",loops = soilLoop + 1) # 5/6 timing after soil

        # -------------------------------------------------------------------
        # -------------------------------------------------------------------

        # ***** ACTUAL EVAPORATION FROM OPEN WATER AND SEALED SOIL ***
        self.opensealed_module.dynamic()

        # *********  WATER USE   *************************
        self.riceirrigation_module.dynamic()
        self.waterabstraction_module.dynamic()
        timemeasure("Water abstraction")

        # ***** Calculation per Pixel ********************************
        self.soil_module.dynamic_perpixel()
        timemeasure("Soil done")

        self.groundwater_module.dynamic()
        timemeasure("Groundwater")

        # ************************************************************
        # ***** STOP if no routing is required    ********************
        # ************************************************************
        if option['InitLisfloodwithoutSplit']:
            # InitLisfloodwithoutSplit
            # Very fast InitLisflood
            # it is only to compute Lzavin.map and skip completely the routing component
            self.output_module.dynamic() # only lzavin

            timemeasure("After fast init")
            for i in xrange(len(timeMes)):
                if self.currentTimeStep() == self.firstTimeStep():
                   timeMesSum.append(timeMes[i] - timeMes[0])
                else: timeMesSum[i] += timeMes[i] - timeMes[0]

            return


        # *********  EVAPORATION FROM OPEN WATER *************
        self.evapowater_module.dynamic()
        timemeasure("open water eva.")

        # ***** ROUTING SURFACE RUNOFF TO CHANNEL ********************
        self.surface_routing_module.dynamic()
        timemeasure("Surface routing")  # 7 timing after surface routing

        # ***** POLDER INIT **********************************
        self.polder_module.dynamic_init()

        # ***** INLETS INIT **********************************
        self.inflow_module.dynamic_init()
        timemeasure("Before routing")  # 8 timing before channel routing

        # ************************************************************
        # ***** LOOP ROUTING SUB TIME STEP   *************************
        # ************************************************************
        self.sumDisDay = globals.inZero.copy()
        # sums up discharge of the sub steps
        for NoRoutingExecuted in xrange(self.NoRoutSteps):
            self.routing_module.dynamic(NoRoutingExecuted)
            #   routing sub steps
        timemeasure("Routing",loops = NoRoutingExecuted + 1)  # 9 timing after routing

        # ----------------------------------------------------------------------

        if option['inflow']:
            self.QInM3Old = self.QInM3
            # to calculate the parts of inflow for every routing timestep
            # for the next timestep the old inflow is preserved
            self.sumIn += self.QInDt*self.NoRoutSteps

        # if option['simulatePolders']:
        # ChannelToPolderM3=ChannelToPolderM3Old;

        if option['InitLisflood'] or (not(option['SplitRouting'])):
            self.ChanM3 = self.ChanM3Kin.copy()
                # Total channel storage [cu m], equal to ChanM3Kin
        else:
            self.ChanM3 = self.ChanM3Kin + self.Chan2M3Kin - self.Chan2M3Start
            #self.ChanM3 = self.ChanM3Kin + self.Chan2M3Kin - self.Chan2M3Start
                # Total channel storage [cu m], equal to ChanM3Kin
                # sum of both lines
            #CrossSection2Area = pcraster.max(scalar(0.0), (self.Chan2M3Kin - self.Chan2M3Start) / self.ChanLength)

        self.sumDis += self.sumDisDay
        self.ChanQAvg = self.sumDisDay/self.NoRoutSteps
        TotalCrossSectionAreaKin = self.ChanM3 * self.InvChanLength
            # New cross section area (kinematic wave)
            # This is the value after the kinematic wave, so we use ChanM3Kin here
            # (NOT ChanQKin, which is average discharge over whole step, we need state at the end of all iterations!)

        timemeasure("After routing")  # 10 timing after channel routing

        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        if not(option['dynamicWave']):
            # Dummy code if dynamic wave is not used, in which case the total cross-section
            # area equals TotalCrossSectionAreaKin, ChanM3 equals ChanM3Kin and
            # ChanQ equals ChanQKin
            self.TotalCrossSectionArea = TotalCrossSectionAreaKin
            # Total cross section area [cu m / s]
            WaterLevelDyn = -9999
            # Set water level dynamic wave to dummy value (needed

        if option['InitLisflood'] or option['repAverageDis']:
            self.CumQ += self.ChanQ
            self.avgdis = self.CumQ/self.TimeSinceStart
            # to calculate average discharge

        self.DischargeM3Out += np.where(self.AtLastPointC ,self.ChanQ * self.DtSec,0)
           # Cumulative outflow out of map

        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        # Calculate water level
        self.waterlevel_module.dynamic()

        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

        # ************************************************************
        # *******  Calculate CUMULATIVE MASS BALANCE ERROR  **********
        # ************************************************************
        self.waterbalance_module.dynamic()



        self.indicatorcalc_module.dynamic()



        # ************************************************************
        # ***** WRITING RESULTS: TIME SERIES AND MAPS ****************
        # ************************************************************

        self.output_module.dynamic()
        timemeasure("Water balance")



        ### Report states if EnKF is used and filter moment
        self.stateVar_module.dynamic()
        timemeasure("State report")

        timemeasure("All dynamic")


        for i in xrange(len(timeMes)):
            if self.currentTimeStep() == self.firstTimeStep():
                timeMesSum.append(timeMes[i] - timeMes[0])
            else: timeMesSum[i] += timeMes[i] - timeMes[0]



        self.indicatorcalc_module.dynamic_setzero()
           # setting monthly and yearly dindicator to zero at the end of the month (year)





        """
		
