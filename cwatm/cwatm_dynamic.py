# -------------------------------------------------------------------------
# Name:       CWAT Model Dynamic
# Purpose:
#
# Author:      burekpe
#
# Created:     16/05/2016
# Copyright:   (c) burekpe 2016
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
from cwatm.management_modules.messages import *

import time



class CWATModel_dyn(DynamicModel):

    # =========== DYNAMIC ====================================================

    def dynamic(self):
        """
        Dynamic part of CWATM
        calls the dynamic part of the hydrological modules
        Looping through time and space

        Note:
            if flags set the output on the screen can be changed e.g.

            * v: no output at all
            * l: time and first gauge discharge
            * t: timing of different processes at the end
        """

        #self.CalendarDate = dateVar['dateStart'] + datetime.timedelta(days=dateVar['curr'])
        #self.CalendarDay = int(self.CalendarDate.strftime("%j"))
        timestep_dynamic(self)


        del timeMes[:]
        timemeasure("Start dynamic")



        if Flags['loud']:
            print("%-6i %10s" %(dateVar['currStart'],dateVar['currDatestr']), end=' ')
        else:
            if not(Flags['check']):
                if (Flags['quiet']) and (not(Flags['veryquiet'])):
                    sys.stdout.write(".")
                if (not(Flags['quiet'])) and (not(Flags['veryquiet'])):
                    sys.stdout.write("\r%d" % dateVar['currStart'])
                    sys.stdout.flush()
                if not (Flags['veryquiet']): print()

        # ************************************************************
        """ up to here it was fun, now the real stuff starts
        """

        if not(self.var.modflow and self.var.modflowsteady):

            if checkOption('calc_environflow') and (returnBool('calc_ef_afterRun')  == False):
                # if only the dis is used for calculation of EF
                self.environflow_module.dynamic()
                self.output_module.dynamic(ef = True)
                header = "\n\n ======================== CWATM ONLY EF calculation===========\n"
                print(header + "done with Environmental Flow\n")
                sys.exit(400)


            self.readmeteo_module.dynamic()
            timemeasure("Read meteo") # 1. timing after read input maps

            self.evaporationPot_module.dynamic()
            timemeasure("ET pot") # 2. timing after read input maps

            #if Flags['check']: return  # if check than finish here

            """ Here it starts with hydrological modules:
            """

            # ***** INFLOW HYDROGRAPHS (OPTIONAL)****************
            self.inflow_module.dynamic()
            self.lakes_reservoirs_module.dynamic()

            # ***** RAIN AND SNOW *****************************************
            self.snowfrost_module.dynamic()
            timemeasure("Snow")  # 3. timing

            # ***** READ land use fraction maps***************************

            self.landcoverType_module.dynamic_fracIrrigation(init = dateVar['newYear'], dynamic = self.var.dynamicLandcover)
            self.capillarRise_module.dynamic()
            timemeasure("Soil 1.Part")  # 4. timing

            # *********  Soil splitted in different land cover fractions *************
            self.landcoverType_module.dynamic()
            timemeasure("Soil main")  # 5. timing

            if self.var.modflow:
                self.groundwater_modflow_module.dynamic_transient()
            self.groundwater_module.dynamic()
            timemeasure("Groundwater")  # 7. timing

            self.runoff_concentration_module.dynamic()
            timemeasure("Runoff conc.")  # 8. timing

            self.lakes_res_small_module.dynamic()
            timemeasure("Small lakes")  # 9. timing


            self.routing_kinematic_module.dynamic()
            timemeasure("Routing_Kin")  # 10. timing

            self.waterquality1.dynamic()

            # calculate Total water storage (tws) [m] as a sum of
            # Groundwater [m] + soil [m] + lake and reservoir storage [m3] + channel storage [m3]
            # [m3] >> [m] --> * InvCellArea
            if (checkOption('includeRouting')):
                self.var.totalET_WB = self.var.EvapoChannel
                if checkOption('includeWaterBodies'):
                    if returnBool('useSmallLakes'):
                        # Sum off lake and reservoirs and small lakes
                       self.var.lakeReservoirStorage = self.var.lakeResStorage + self.var.smalllakeStorage
                    else:
                        # Sum off lake and reservoirs - here without small lakes
                        self.var.lakeReservoirStorage = self.var.lakeResStorage

                    self.var.tws = self.var.storGroundwater + self.var.totalSto + self.var.lakeReservoirStorage * self.var.InvCellArea + self.var.channelStorage * self.var.InvCellArea
                    self.var.totalET_WB = self.var.totalET_WB + self.var.totalET + self.var.EvapWaterBodyM
                    if returnBool('useSmallLakes'):
                        self.var.totalET_WB = self.var.totalET_WB + self.var.smallevapWaterBody
                else:
                    self.var.tws = self.var.storGroundwater + self.var.totalSto + self.var.channelStorage * self.var.InvCellArea
            else:
                self.var.tws = self.var.storGroundwater + self.var.totalSto

            if checkOption('includeRunoffConcentration'):
                self.var.tws = self.var.tws + self.var.gridcell_storage

            # *******  Calculate CUMULATIVE MASS BALANCE ERROR  **********
            # self.waterbalance_module.dynamic()

            # ------------------------------------------------------
            # End of calculation -----------------------------------
            # ------------------------------------------------------

            self.waterbalance_module.checkWaterSoilGround()
            timemeasure("Waterbalance")  # 11. timing

            self.environflow_module.dynamic()
            # in case environmental flow is calculated last
            # overFlo error from Flo Roemer

            self.output_module.dynamic()
            timemeasure("Output")  # 12. timing

            self.init_module.dynamic()

            for i in range(len(timeMes)):
                #if self.currentTimeStep() == self.firstTimeStep():
                if self.currentStep == self.firstStep:
                    timeMesSum.append(timeMes[i] - timeMes[0])
                else: timeMesSum[i] += timeMes[i] - timeMes[0]


            #self.var.sumsum_directRunoff += self.var.sum_directRunoff
            #self.var.sumsum_Runoff += self.var.sum_directRunoff
            #self.var.sumsum_Precipitation += self.var.Precipitation
            #self.var.sumsum_gwRecharge += self.var.sum_gwRecharge
            #runoff = self.var.baseflow + self.var.sum_landSurfaceRunoff
            #self.var.sumsum_Runoff += runoff

            #print self.sum_directRunoff,  self.sum_interflowTotal, self.sum_landSurfaceRunoff, self.baseflow, runoff
            #print self.sumsum_Precipitation, self.sumsum_Runoff

              #report(decompress(self.var.sum_potTranspiration), "c:\work\output/trans.map")
              #r eport(decompress(self.var.directRunoff[3 ]), "c:\work\output\dir.map")
            #report(decompress(runoff), "c:\work\output\dirsum.map")
            #report(decompress(self.sumsum_Precipitation), "c:\work\output\prsum.map")
               #report(decompress(runoff), "c:\work\output/runoff.map")


        else:
            # Modflow and steady state calculation

            #Each step we run successively CWATM and ModFlow saving the output used as input by the other model,
            #models simulates only one step.
            #For CWATM it is always the same day with mean forcing (Precip and Temperatures)
            #For ModFlown, each step is a steady simulation (or annual timestep)
            #We also need to save variable states at the end (like storage in CWATM and ModFlow layers) to import them for the next step"""

            start1 = time.time()

            for compteur in range(1,self.var.Ndays_steady+1):
            #for compteur in range(1, 1 + 1):

                if compteur == 1:
                    self.readmeteo_module.dynamic()
                    self.evaporationPot_module.dynamic()
                    #self.snowfrost_module.dynamic()
                    # for steady state no snow, because once there is snow -> no melt -> no recharge
                    self.var.Rain = self.var.Precipitation
                    self.var.SnowCover = self.var.Precipitation * 0
                    self.var.SnowMelt = self.var.Precipitation * 0
                    self.var.Snow = self.var.Precipitation * 0
                    self.var.FrostIndex = self.var.Precipitation * 0
                    self.landcoverType_module.dynamic_fracIrrigation(init=dateVar['newYear'], dynamic=self.var.dynamicLandcover)

                    # initial run of soil to get recharge in steady state
                    try:
                        no_days = self.var.init_days_of_soil
                    except:
                        no_days = 365

                    for days in range(no_days):
                        self.landcoverType_module.dynamic()
                        print (days)

                start2 = time.time()
                self.landcoverType_module.dynamic()
                print("   cwatm -", time.time() - start2)

                start2 = time.time()
                self.groundwater_modflow_module.dynamic_steady(compteur)
                print("   modflow -", time.time() - start2)

            print("runtime -", time.time() - start1)

            # for pytest set this to 0 to get a positive test
            self.var.firstout = 0.



		
