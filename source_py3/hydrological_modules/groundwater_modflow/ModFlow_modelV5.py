# -*- coding: utf-8 -*-
"""
Created on Wed Jan 16 13:55:27 2019

@author: Guillaumot Luca, PB
"""

import os
import sys
import numpy as np
flopypth = os.path.join('..', '..', 'flopy')
if flopypth not in sys.path:
    sys.path.append(flopypth)
import flopy
import flopy.utils.binaryfile as bf
import time


def ModFlow_modelV5(self, path_data, numero, namemodel, StepSize, nrow,ncol, recharge, pumping_datas=[]):
        """This function runs ModFlow in transient state and save automatically hydraulic heads in the model (with the namemodel)
        and the drain's flow ie the capillary rise for CWATM
        Input arguments:
        namemodel: Rhine+No
        input_name: file containg recharge value projected from CWATM to ModFlow grid
        properties: topography, porosity, permeability maps and the grid definition
        WaterTable3: water level in the third CWATM layer, used to compute the flow from ModFlow to CWATM
        output_name: name of the drained flow values, to be imported next in CWATM
        return also the volume that exit from ModFLow on the total area"""

        def check_if_close(files):
            # sometime modflow does not start because the writing has not finished
            for file in files:
                #print (file)
                try:
                    os.rename(file, file + "_")
                    os.rename(file + "_", file)
                except OSError as e:
                    print ("Access-error on file \"" + str(file) + "\"!!! \n" + str(e))
                    time.sleep(3)




        # output and name prefix
        pathname = self.var.PathModflowOutput + '/' + self.var.nameModflowModel

        ## Time discretization parameters
        # Number of days simulated
        nper = 1
        # Modflow Flopy library conform
        perlen = np.ones(nper)
        nstp = np.ones(nper)

        # MODFLOW FUNCTION
        ss = np.divide(self.var.poro,self.var.delv2)    # Specific storage [1/m]
        hk2 = self.var.hk0 * StepSize          # Permeability [1/m]
        laytyp = 0                             # 0 if confined, else laytyp=1
        layvka = 1                               # If layvka=0 vka=vertical hydraulic conductivity, if not vka=ratio horizontal to vertical conductivity
        vka = 1
        sy = 0.1                               # Specific yield: not used if the layer is confined

        ## FLOPY OBJECTS
        if numero == 1:
            mf = flopy.modflow.Modflow(self.var.nameModflowModel, model_ws = self.var.PathModflowOutput , exe_name=self.var.modflowexe , version='mfnwt') # Call the .exe ModFlow
            dis = flopy.modflow.ModflowDis(mf, self.var.nlay, nrow, ncol, delr=self.var.res_ModFlow, delc=self.var.res_ModFlow, top=self.var.botm[0], botm=self.var.botm[1:],
                                       nper=nper, perlen=perlen, nstp=nstp, steady = False) # Grid characteristics (itmuni=4 if days, 5 if years)
            bas = flopy.modflow.ModflowBas(mf, ibound=self.var.basin, strt=self.var.head)     # ibound = Grid containing 0 and 1 (if 1 the cell belows to the basin and it will be an active cell)
            upw = flopy.modflow.ModflowUpw(mf, hk=hk2, vka=vka, sy=sy, ss=ss,laytyp=laytyp,layvka=layvka) # Hydrodynamic properties
            nwt = flopy.modflow.ModflowNwt(mf, fluxtol=500* StepSize, Continue=True)        # If Continue=True the model continue even if percent discrepancy > criteria

            ## DRAIN PACKAGE
            ir = np.repeat(np.arange(nrow),ncol)
            ic = np.tile(np.arange(ncol),nrow)
            wt = self.var.waterTable3.ravel()
            cf = self.var.coef*hk2[0]* self.var.res_ModFlow * self.var.res_ModFlow
            cf = cf.ravel()
            dd = np.stack([np.zeros(ir.shape[0]),ir, ic,wt,cf])
            drain = np.swapaxes(dd,0,1)

            lrcec={0:drain}
            drn = flopy.modflow.ModflowDrn(mf, stress_period_data=lrcec,options=['NOPRINT'])
            ## RECHARGE PACKAGE
            rch = flopy.modflow.ModflowRch(mf, nrchop=3, rech=recharge)

            ### Add the pumping case - PUMPING WELL PACKAGE
            ## first we will consider constant pumping rates along the simulation, so pumping_data is only a 2D array
            if self.var.GW_pumping:
                wel_sp = []
                print('number of pumping wells :', len(pumping_datas))
                for kk in range(len(pumping_datas)):  # adding each pumping well to the package
                    wel_sp.append([0, pumping_datas[kk][0], pumping_datas[kk][1], pumping_datas[kk][2] * StepSize])
                    # Pumping [m3/timestep] in the first layer
                wel = flopy.modflow.ModflowWel(mf, stress_period_data=wel_sp)
                # the well path has to be defined in the .nam file

            ## OUTPUT CONTROL
            oc = flopy.modflow.ModflowOc(mf, stress_period_data=None)
            mf.write_input()                                                # Write the model input files
            
        else:
            mf = flopy.modflow.Modflow(self.var.nameModflowModel, model_ws = self.var.PathModflowOutput, exe_name=self.var.modflowexe , version='mfnwt') # Call the .exe ModFlow
            dis = flopy.modflow.ModflowDis(mf, self.var.nlay, nrow,ncol, delr=self.var.res_ModFlow, delc=self.var.res_ModFlow, top=self.var.botm[0], botm=self.var.botm[1:],
                                       nper=nper, perlen=perlen, nstp=nstp, steady=False) # Grid characteristics
            bas = flopy.modflow.ModflowBas(mf, ibound=self.var.basin, strt=self.var.head)     # ibound = Grid containing 0 and 1 (if 1 the cell belows to the basin and it will be an active cell)

            ## PUMPING WELL PACKAGE
            ## first we will consider constant pumping rates along the simulation, so pumping_data is only a 2D array
            if self.var.GW_pumping:
                wel_sp = []
                for kk in range(len(pumping_datas)):  # adding each pumping well to the package
                    wel_sp.append([0, pumping_datas[kk][0], pumping_datas[kk][1], pumping_datas[kk][2] * StepSize])  # Pumping [m3/timestep] in the first layer, warning pumping rate has to be  < 0 !!!
                wel = flopy.modflow.ModflowWel(mf, stress_period_data=wel_sp)  # the well path has to be defined in the .nam file

            rch = flopy.modflow.ModflowRch(mf, nrchop=3, rech=recharge)

            rch.write_file(check=True)
            bas.write_file(check=True)
            if self.var.GW_pumping: wel.write_file()
            #mf.write_input()

            # modify the nam file:
            #if numero == 2:
            nam_file=open(pathname+'.nam', "w")
            nam_file.write(self.var.modflow_text_to_write)
            nam_file.close()

            files = [rch.fn_path,bas.fn_path,pathname+'.nam']
            if self.var.GW_pumping: files.append(wel.fn_path)
            check_if_close(files)


        ### -------- Running MODFLOW -----------------------------
        success, mfoutput = mf.run_model(silent=True, pause=False)  # Run the model
        ### ------------------------------------------------------


        # TODO: some error routine needed
        #if not success:
         #   raise Exception('MODFLOW did not terminate normally.')


        ## COMPUTING AND SAVING OUTPUT FLOW BY DRAINS
        # Create the headfile object
        headobj = bf.HeadFile(pathname + '.hds')
        periode=headobj.get_times()
        # Matrix of the simulated water levels
        self.var.head = headobj.get_data(totim=periode[0])
        headobj.close()

        # outflow from groundwater # from m per timestep to m/d
        gwoutflow =  np.where(((self.var.head[0] - self.var.waterTable3)>=0) & (self.var.basin[0] == 1),
                      (self.var.head[0]-self.var.waterTable3)*self.var.coef*hk2[0] / StepSize,0)
        # CapillaryRise and baseflow
        cap_rise  = gwoutflow *(1 - self.var.riverPercentage)
        base_flow = gwoutflow * self.var.riverPercentage

        # Groundwater storage in [m]
        head = np.where(self.var.head[0] == -999, self.var.botm[0]-self.var.actual_thick[0], self.var.head[0])
        self.var.modflowStorGW = (head - (self.var.botm[0]-self.var.actual_thick[0])) * self.var.poro[0]

        budget_terms = 0
        if self.var.writeerror:
            mf_list = flopy.utils.MfListBudget(pathname + '.list')
            budget_terms = mf_list.get_data()  # (totim=periode[0], incremental=True)
            #Error_Percentage = Budget_terms[-1][1]
            # -1 because the last value correspond to the percent discrepancy of the simulated period


        #return Q1,Q2,Cap_rise, Base_flow, Budget_terms
        return cap_rise, base_flow, budget_terms


