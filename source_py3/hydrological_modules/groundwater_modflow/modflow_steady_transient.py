# -------------------------------------------------------------------------
# Name:        Modflow steady and transient module
# Purpose:
#
# Author:      Luca Guillaumot,PB
#
# Created:     18/04/2019
# Copyright:   (c) LG, PB 2019
# -------------------------------------------------------------------------


import numpy as np
from management_modules.data_handling import *

from hydrological_modules.groundwater_modflow.ModFlow_modelV5 import ModFlow_modelV5


def decompress(map):
    """
    Decompressing map from 1D to 2D with missing values

    :param map: compressed map
    :return: decompressed 2D map
    """

    dmap = maskinfo['maskall'].copy()
    dmap[~maskinfo['maskflat']] = map[:]

    return dmap.data


def modflow2CWATM(self,variable):

    #var_area = variable.copy()
    #var_area[np.isnan(var_area)] = 0
    #var_area[var_area>0]=1

    #zi = np.zeros(indexes['Weight2'].shape)
    catsums = np.zeros(indexes['Weight2'].shape)
    #catsums_area = np.zeros(indexes['Weight2'].shape)
    h = np.bincount(indexes['CWATMindex'], variable.ravel())
    #h_area = np.bincount(indexes['CWATMindex'], var_area)
    catsums[:h.shape[0]] = h
    #catsums_area[:h_area.shape[0]] = h_area

    zi = catsums * indexes['Weight2']
    #zi_area = np.where(indexes['taille'] > 0, 1 - catsums_area / indexes['taille'], 0)
    zi = zi.reshape(domain['nlat'], domain['nlon'])
    #zi_area = zi_area.reshape(domain['nlat'], domain['nlon'])

    #return zi, zi_area
    return zi


def modflow_steady(self,compteur):
    """
	Run CWATM-ModFlow model in Steady state")
	"""

    """Each step we run successively CWATM and ModFlow saving the output used as input by the other model,
		models simulates only one step.
		For CWATM it is always the same day with mean forcing (Precip and Temperatures)
		For ModFlow, each step is a steady simulation (or annual timestep)
		We also need to save variable states at the end (like storage in CWATM and ModFlow layers) to import them for the next step
	"""

    # numero is negative if in steady state and running to 0
    numero = (-1 * self.var.Ndays_steady * self.var.modflow_timestep) + (compteur - 1) * self.var.modflow_timestep

    # instead of steady state a long transient run of 2 years is used
    StepSize = 2 *365.25

    # gwrecharge from CWATM soil part, will be decompressed to 2D array
    # multiplied with timesteps (e.g. 7 days)
    gw1 = decompress(self.var.sum_gwRecharge) * StepSize

    # CWATM 2D array is converted to Modflow 2D array
    gwrecharge = indexes['Weight'] * gw1[indexes['CWATMindex']]
    gwrecharge[np.isnan(gwrecharge)] = 0
    gwrecharge[gwrecharge < 1e-20] = 0
    self.var.Volume_modflow = np.nansum(gwrecharge * self.var.res_ModFlow * self.var.res_ModFlow)
    gwrecharge = gwrecharge.reshape(domain['nrow'], domain['ncol'])

    #ProjMeanRecharge(res_ModFlow, res_CWATM, Inputs_file, InitRecharge, Outputs_file + 'GWrecharge_map.txt')
    # To Modflow subroutine
    cap,base, budget_terms = ModFlow_modelV5(self,self.var.PathModflow , compteur, numero, StepSize,domain['nrow'],domain['ncol'],gwrecharge,pumping_datas=[])

    # conversion from Modflow to CWATM 2D format
    self.var.capillar = compressArray(modflow2CWATM(self,cap.ravel()))
    self.var.baseflow = compressArray(modflow2CWATM(self, base.ravel()))


    if self.var.writeerror:
        groundwaterStor = (self.var.head[0] - self.var.actual_thick) / self.var.poro
        ModFlow_error = budget_terms[-1][1]
        # -1 because the last value correspond to the percent discrepancy of the simulated period
        print (compteur, "-",np.nansum(self.var.capillar),np.nansum(self.var.baseflow),ModFlow_error)
    else:
        print(compteur, "-", np.nansum(self.var.capillar), np.nansum(self.var.baseflow))

    return budget_terms


# --------------------------------------------------------------------------------


def modflow_transient(self,compteur):
    """
	Run CWATM-ModFlow model in transient state")
	"""

    # gwrecharge from CWATM soil part, will be decompressed to 2D array
    # using the sumed up (over e.g 7 days gwrecharge)
    gw1 = decompress(self.var.sumed_sum_gwRecharge)

    # CWATM 2D array is comverted to Modflow 2D array
    gwrecharge = indexes['Weight'] * gw1[indexes['CWATMindex']]
    gwrecharge[np.isnan(gwrecharge)] = 0
    #gwrecharge[gwrecharge < 1e-20] = 0
    self.var.Volume_modflow = np.nansum(gwrecharge * self.var.res_ModFlow * self.var.res_ModFlow)
    gwrecharge = gwrecharge.reshape(domain['nrow'], domain['ncol'])

    #ProjMeanRecharge(res_ModFlow, res_CWATM, Inputs_file, InitRecharge, Outputs_file + 'GWrecharge_map.txt')

    # To Modflow subroutine
    ### MODIF LUCA, add the pumping case
    if self.var.GW_pumping:
        pumping_data = cbinding('Pumping_input_file')
        pumping_data = np.load(pumping_data)
        cap,base, budget_terms = ModFlow_modelV5(self,self.var.PathModflow , compteur, 1, self.var.modflow_timestep, domain['nrow'],domain['ncol'], gwrecharge, pumping_datas=pumping_data)
    else:
        cap,base, budget_terms = ModFlow_modelV5(self,self.var.PathModflow , compteur, 1, self.var.modflow_timestep, domain['nrow'],domain['ncol'], gwrecharge, pumping_datas=[])


    ## WATERBALANCE Calculation
    ### MODIF LUCA, ModFlow cells storage is already computed in ModFlow_modelV5
    #self.var.modflowStorGW = self.var.modflowStorGW + gwrecharge
    #self.var.modflowStorGW = self.var.modflowStorGW - (cap + base)* self.var.modflow_timestep
    #self.var.modflowStorGW = (self.var.modflowWaterLevel-previoushead) * self.var.poro modflowGwStore
    # self.var.storGroundwater1 = self.var.storGroundwater1 - self.var.sumed_sum_gwRecharge
    #self.var.sumstorGW2 = (globals.inZero + 1.) * np.nansum(self.var.modflowStorGW)



    # conversion from Modflow to CWATM 2D format
    # already as m/d
    self.var.capillar = compressArray(modflow2CWATM(self,cap.ravel()))
    self.var.baseflow = compressArray(modflow2CWATM(self, base.ravel()))


    ##self.var.gwstore = compressArray(modflow2CWATM(self, self.var.modflowGwStore))


    return budget_terms