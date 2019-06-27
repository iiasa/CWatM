# -------------------------------------------------------------------------
# Name:        Groundwater Modflow module
# Purpose:
#
# Author:      Luca Guillaumot, PB
#
# Created:     18/04/2019
# Copyright:   (c) LG,PB 2019
# -------------------------------------------------------------------------

from management_modules.data_handling import *

class groundwater_modflow(object):
    """
    GROUNDWATER MODFLOW 
    """

    def __init__(self, groundwater_modflow_variable):
        self.var = groundwater_modflow_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """
        Initial part of the groundwater modflow module


        """

        # test if ModFlow is in the settingsfile
        # if not, use default without Modflow
        self.var.modflow = False
        if "modflow_coupling" in option:
            self.var.modflow = checkOption('modflow_coupling')

        if not(self.var.modflow):
            # ModFlow version is not used
            ii =1
        else:

            # if ModFlow is used then use this libraries
            from datetime import datetime
            from hydrological_modules.groundwater_modflow.modflow_steady_transient import modflow_steady, modflow_transient
            flopypth = os.path.join('..', '..', 'flopy')
            if flopypth not in sys.path:
                sys.path.append(flopypth)
            import flopy
            import flopy.utils.binaryfile as bf

            # ----------------------------
            ## Model properties ##
            self.var.modflowsteady = returnBool('modflow_steadystate')

            # using the Modflow version: MODFLOW-NWT_64.exe from 16/01/2019
            self.var.modflowexe = cbinding('modflow_exe')

            self.var.PathModflow = cbinding('PathGroundwaterModflow')
            self.var.PathModflowOutput = cbinding('PathGroundwaterModflowOutput')


            # Load initial map and values

            self.var.res_ModFlow = loadmap('res_ModFlow')
            self.var.modflow_timestep = int(loadmap('modflow_timestep'))
            self.var.Ndays_steady = int(loadmap('Ndays_steady'))

            #CWATMs resolution [degree]
            res_CWATM = maskmapAttr['cell']
            gridcellarea = self.var.cellArea

            ## We need to stop here and run the Matlab code "Create_RiverNetwork.matlab" to compute stream network from the new created topographic map
            ## And then we need to run Python code "Stream_Loading.py" to compute the river network
            # Inputs_file + 'Lobith_limits200m.txt'

            ## ModFlow domain and grid definition ##
            # "Lobith_limits.txt" is created by the ExtractBasinLimits function
            self.var.nlay = int(loadmap('nlay'))
            Size = np.loadtxt(cbinding('catchment_limits'))

            domain['cellsize'] = self.var.res_ModFlow
            domain['west'] = int(Size[0])
            domain['east'] = int(Size[1])
            domain['north'] = int(Size[2])
            domain['south'] = int(Size[3])
            domain['nrow'] = int(Size[4])
            domain['ncol'] = int(Size[5])
            domain['nlat'] = int(Size[6])
            domain['nlon'] = int(Size[7])

            ## Processing thickness map for ModFlow-Flopy format ##
            # We assume a confined aquifer, the unique parameters are transmissivity, porosity and thickness
            #self.var.Gleesonindex = returnBool('Gleesonindex')  # 'True, with hetero thick'  # Write True or False
            #self.var.actual_thick = loadmap('actual_thick')  #400

            thick = cbinding('thickness')  # default = 400
            try:
                thick1 = float(thick)
                self.var.actual_thick = np.full((self.var.nlay, domain['nrow'], domain['ncol']), thick1)
            except:
                thick1 = np.loadtxt(thick)
                self.var.actual_thick = thick1.reshape(domain['nrow'], domain['ncol'])

            # Coef to multiply transmissivity and storage coefficient (because ModFlow convergence is better if aquifer's thicknes is big and permeability is small)
            self.var.coef = 1

            delv = self.var.actual_thick * self.var.coef
            self.var.delv2 = np.full((self.var.nlay, domain['nrow'], domain['ncol']), delv)

            ## Processing top and bottom map of the ModFlow model with the topographic information for ModFlow-Flopy format ##
            top = np.loadtxt(cbinding('topo_modflow'))
            # "Topo.txt" is created by the ProjMapToModFlow function
            topography = top.reshape(domain['nrow'], domain['ncol'])
            self.var.botm = np.full((self.var.nlay + 1, domain['nrow'], domain['ncol']), topography)
            for il in range(1, self.var.nlay + 1):
                self.var.botm[il] = self.var.botm[il - 1] - self.var.delv2[0]

            ## Uploading river percentage of each ModFlow cell computed by Matlab Topotoolbox on a finner topography map ##
            #  print("Calculate River percentage")
            # RiverPercentage=ComputeRiverPercent(res_ModFlow, basin, Inputs_file+"Lobith_limits.txt", stream_file, limit_stream_file)
            # np.save(Inputs_file+'RiverPercentage.npy',RiverPercentage)

            gwRiverMult = 1.
            if "gwRiverMult" in binding:
                gwRiverMult = loadmap('gwRiverMult')


            self.var.riverPercentage = np.load(cbinding('riverPercentage')) * gwRiverMult

            self.var.riverPercentage = np.minimum(np.maximum(self.var.riverPercentage,0.),1.)

            ## Processing permeability map for ModFlow-Flopy format ##
            # Permea = np.loadtxt(Inputs_file+"Permea.txt")  # Heterogeneous version, Unit:[m/d]
            # hk0 = [[[(3600*24*1e7*10**(Permea[ic+ir*ncol]))/coef for ic in range(ncol)] for ir in range(nrow)] for il in range(nlay)]  # Heterogeneous version, Unit:[m/d]
            # hk0 = [[[(3600*24*1e7*10**(-12))/coef for ic in range(ncol)] for ir in range(nrow)] for il in range(nlay)]  # Homogeneous version, Unit:[m/d]

            permea = cbinding('permeability')  # default = - 12
            try:
                permea1 = float(permea)
                self.var.hk0 = np.full((self.var.nlay, domain['nrow'], domain['ncol']), (86400 * permea1) / self.var.coef)
            except:
                permea1 = np.loadtxt(permea)
                permea2 = permea1.reshape(self.var.nlay,domain['nrow'], domain['ncol'])
                self.var.hk0 = (86400 * permea2) / self.var.coef


            ## Processing porosity map for ModFlow-Flopy format ##
            # Poro = np.loadtxt(Inputs_file+"Poro.txt")  # Heterogeneous version, Unit: []
            poro = cbinding('poro')   # default = 0.1
            try:
                poro1 = float(poro)
                self.var.poro = np.full((self.var.nlay, domain['nrow'], domain['ncol']), poro1)
            except:
                self.var.poro = np.loadtxt(poro)
                self.var.poro = self.var.poro.reshape(self.var.nlay, domain['nrow'], domain['ncol'])




            indexes['CWATMindex'] = np.loadtxt(cbinding('index_cwatm')).astype(int)
            # Contains CWATM index corresponding to each ModFlow cell
            indexes['Weight'] = np.loadtxt(cbinding('weight_cwatm'))  # Importing weight for projection
            indexes['Weight2'] = np.loadtxt(cbinding('weight_modflow'))  # Importing the weight of ModFlow cells in the CWATM matrix

            ## Total basin area of ModFlow, (probably not exactly the same than the CWATM basin because of projection) ##
            #basin = np.loadtxt(cbinding('basin_limits'))
            #basin_area = self.var.res_ModFlow * np.sum(basin)  # [m2]
            basin = np.where(indexes['CWATMindex'] > 0, 1.0, 0.0)
            self.var.basin = basin.reshape(self.var.nlay, domain['nrow'], domain['ncol'])


            # Using total soildepth from CWATM - soillayer 0, 1 and 2
            #depthLayer3 = np.loadtxt(cbinding('depthLayer3'))  # [m]
            #D3 = depthLayer3.reshape(domain['nrow'], domain['ncol'])
            #self.var.waterTable3 = topography - D3
            # replace by
            soildepth12 = maskinfo['maskall'].copy()
            soildepth12[~maskinfo['maskflat']] = self.var.soildepth12[:]
            # CWATM 2D array is comverted to Modflow 2D array
            soildepth_modflow = indexes['Weight'] * soildepth12[indexes['CWATMindex']]
            soildepth_modflow[np.isnan(soildepth_modflow)] = 1.0
            soildepth_modflow[soildepth_modflow < 1e-20] = 1.0
            soildepth_modflow = soildepth_modflow.reshape(domain['nrow'], domain['ncol'])
            self.var.waterTable3 = topography - soildepth_modflow


            taille = np.zeros(indexes['Weight2'].shape)
            h = np.bincount(indexes['CWATMindex'], np.ones(indexes['CWATMindex'].shape)).astype(int)
            taille[:h.shape[0]] = h
            indexes['taille'] = taille

            self.var.nameModflowModel = cbinding('nameModflowModel')
            if self.var.modflowsteady:
                self.var.nameModflowModel = self.var.nameModflowModel + "_steady"
            else:
                self.var.nameModflowModel = self.var.nameModflowModel + "_transient"

            self.var.nameModflowModel = cbinding('nameModflowModel')

            ## Importing initial water levels from the previous step or from steady state
            # Steady state
            # even for steady state a previous steady state is better than a new run, this enables the loading ofd a steady state
            self.var.steady_previous = False
            if "load_steady_previous" in binding:
                self.var.steady_previous = returnBool('load_steady_previous')


            if self.var.modflowsteady and not(self.var.steady_previous):
                self.var.nameModflowModel = self.var.nameModflowModel + "_steady"

                # The initial water level is the topography minus Xm
                head1 = np.ones((self.var.nlay, domain['nrow'], domain['ncol']), dtype=np.float32)
                self.var.head= self.var.botm[0]- head1 * 2
            # Transient
            else:
                self.var.nameModflowModel = self.var.nameModflowModel + "_transient"
                # if run in transient state, water table is read in:
                #headobj = bf.HeadFile(pathname + '_1.hds')
                headobj = bf.HeadFile(cbinding('modflow_steadyInit'))
                periode = headobj.get_times()
                # Matrix of the simulated water levels
                self.var.head = headobj.get_data(totim=periode[0])
                headobj.close()


            # standard file defined before run:
            pn = self.var.PathModflowOutput + '/' + self.var.nameModflowModel

            self.var.GW_pumping = False
            if "Groundwater_pumping" in binding:
                 self.var.GW_pumping = returnBool('Groundwater_pumping')
            if self.var.GW_pumping:
                # add the pumping case
                self.var.modflow_text_to_write = '# Name file for MODFLOW-NWT, generated by Flopy version 3.2.6.\n#xul:0; yul:636000; rotation:0; proj4_str:+init=EPSG:4326; units:meters; lenuni:2; length_multiplier:1.0 ;start_datetime:1-1-1970\nLIST               2  '\
                                + pn +'.list\nDIS               11  ' + pn +'.dis \nBAS6              13  ' + pn +'.bas \nUPW               31  ' + pn +'.upw \nNWT               32  '\
                                + pn +'.nwt \nDRN               21  ' + pn +'.drn \nWEL               20  ' + pn +'.wel \nRCH               19  ' + pn +'.rch \nOC                14  '\
                                + pn +'.oc \nDATA(BINARY)      51  ' + pn + '.hds REPLACE\n'
            else:
                self.var.modflow_text_to_write = '# Name file for MODFLOW-NWT, generated by Flopy version 3.2.6.\n#xul:0; yul:636000; rotation:0; proj4_str:+init=EPSG:4326; units:meters; lenuni:2; length_multiplier:1.0 ;start_datetime:1-1-1970\nLIST               2  '\
                    + pn +'.list\nDIS               11  ' + pn +'.dis \nBAS6              13  ' + pn +'.bas \nUPW               31  ' + pn +'.upw \nNWT               32  '\
                    + pn +'.nwt \nDRN               21  ' + pn +'.drn \nRCH               19  ' + pn +'.rch \nOC                14  '\
                    + pn +'.oc \nDATA(BINARY)      51  ' + pn + '.hds REPLACE\n'

            #Initial values:
            # sumed up groundwater recharge for the number of days
            self.var.sumed_sum_gwRecharge = globals.inZero

            self.var.capillar = globals.inZero
            self.var.baseflow = globals.inZero
            self.var.gwstore = globals.inZero
            self.var.modflow_compteur = 0



            # write modflow error
            self.var.writeerror = returnBool('writeModflowError')
            if self.var.writeerror:
                self.var.nameerrorfile = pn + "_error.txt"
                modflowfile = open(self.var.nameerrorfile, "w")
                modflowfile.write("Error of Modflow file\n")
                modflowfile.write("No,date,STORAGE_IN,CONSTANT_HEAD_IN,DRAINS_IN,RECHARGE_IN,TOTAL_IN,STORAGE_OUT,CONSTANT_HEAD_OUT,DRAINS_OUT,RECHARGE_OUT,TOTAL_OUT,IN-OUT,PERCENT_DISCREPANCY\n")
                modflowfile.close()


            # Only for calculating waterbalance
            self.var.storGroundwater1 = globals.inZero
            self.var.modflowStorGW = self.var.poro[0] * 0.
            self.var.modflowWaterLevel = self.var.poro[0] * 0.
            self.var.sumstorGW = globals.inZero
            self.var.sumstorGW2 = globals.inZero



    # --------------------------------------------------------------------------
    def error_output(self,Budget_terms):

        if self.var.writeerror:
            modflowfile = open(self.var.nameerrorfile, "a")
            modflowfile.write("%5s,%11s" % (dateVar['curr'], dateVar['currDatestr']))
            for b in Budget_terms:
                modflowfile.write(",%20.5f" % (b[1]))
            modflowfile.write("\n")
            modflowfile.close()


    def dynamic_steady(self,compteur):
        """
        Dynamic part of the groundwater modflow module -= steady state
        """

        from hydrological_modules.groundwater_modflow.modflow_steady_transient import modflow_steady, modflow_transient

        #from  hydrological_modules.groundwater_modflow.modflow_steady import modflow_steady
        budget_terms = modflow_steady(self,compteur)
        if self.var.writeerror:
            self.error_output(budget_terms)

    # --------------------------------------------------------------------------
    def dynamic_transient(self):
        """
        Dynamic part of the groundwater modflow module - transinet
        """

        from hydrological_modules.groundwater_modflow.modflow_steady_transient import modflow_steady, modflow_transient

        if checkOption('calcWaterBalance'):
            self.var.pregwstore = self.var.gwstore.copy()
            self.var.prestorGroundwater1 = self.var.storGroundwater1.copy()

        # Sumed recharge is re-initialized here for water budget computing purpose
        if (dateVar['curr']-int(dateVar['curr']/self.var.modflow_timestep)*self.var.modflow_timestep) == 1:  # if it is the first step of the week
            # setting sumed up recharge again to 7, will be sumed up for the following 7 days
            self.var.sumed_sum_gwRecharge = 0
        self.var.sumed_sum_gwRecharge = self.var.sumed_sum_gwRecharge + self.var.sum_gwRecharge

        # every modflow timestep e.g. 7 days

        if (dateVar['curr']  % self.var.modflow_timestep) == 0:

            self.var.modflow_compteur += 1
            # Saving the previous GW level
            previoushead=self.var.modflowWaterLevel

            ## ---- go to Modflow ------------------------------------------
            budget_terms = modflow_transient(self,self.var.modflow_compteur)
            ## --------------------------------------------------------

            #self.var.storGroundwater1 = self.var.storGroundwater1 + self.var.sumed_sum_gwRecharge
            #self.var.storGroundwater1 = self.var.storGroundwater1 + self.var.rgw

            if self.var.writeerror:
                #ModFlow_error = Budget_terms[-1][1]
                # -1 because the last value correspond to the percent discrepancy of the simulated period
                self.error_output(budget_terms)

            ### Computing water volume variation to check water balance, and saving water levels
            #print (ModFlow_error,np.nansum(self.var.modflowStorGW)), np.nansum(self.var.storGroundwater1))
            #gwstorage = self.var.sumed_sum_gwRecharge - (self.var.baseflow + self.var.capillar)*self.var.modflow_timestep
            #print('ModFlow storage variations from Modflow [mm]:     ', np.round(np.nansum(self.var.modflowStorGW * self.var.res_ModFlow * self.var.res_ModFlow)/46000000000*1000))
            #print('ModFlow storage variations from CWATM [mm]:       ', np.round(np.nansum(gwstorage * self.var.cellArea)/46000000000*1000))
            self.var.modflowWaterLevel = self.var.head[0].copy()
            self.var.modflowWaterLevel[self.var.modflowWaterLevel < 0] = np.nan
            # print('ModFlow storage variations from Water levels [mm]:', np.round(np.nansum(((self.var.modflowWaterLevel-previoushead) * self.var.res_ModFlow * self.var.res_ModFlow * self.var.poro))/46000000000*1000))
            self.var.GWVolumeVariation = np.nansum((self.var.modflowWaterLevel - previoushead) * self.var.poro) * self.var.res_ModFlow * self.var.res_ModFlow


        if checkOption('calcWaterBalance'):
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.sumed_sum_gwRecharge],  # In
                [self.var.baseflow, self.var.capillar ],  # Out
                [self.var.prestorGroundwater1],  # prev storage
                [self.var.storGroundwater1],
                "Ground1", True)

        if checkOption('calcWaterBalance'):
            self.var.waterbalance_module.waterBalanceCheck(
                [self.var.sumed_sum_gwRecharge],            # In
                [self.var.baseflow,self.var.capillar],      # Out
                [self.var.pregwstore],                      # prev storage
                [self.var.gwstore],
                "ModFlow1", False)




 #hydrological_modules.groundwater_modflow.
        ii = 1