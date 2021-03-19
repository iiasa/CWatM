# -*- coding: utf-8 -*-
"""
Created on Wed Jan 16 13:41:25 2019

@author: Guillaumot Luca
"""

import numpy as np
import matplotlib.pyplot as plt
import rasterio
from rasterio.warp import reproject, Resampling

def ComputeRiverPercent(res_ModFlow, affine_modflow, ncol_ModFlow, nrow_ModFlow, init_rivermap_reso, StreamNetworkFile,
                        affine_modflow_200m, ncol_ModFlow_200m, nrow_ModFlow_200m, crs_modflow, create_tif=False):
    """Computing the percentage of river in each ModFlow cell based on the topographic map at 200 m
    (not necessarily 200 m but has to be finer than res_ModFlow)
    arg1: res_ModFlow : choosen ModFlow resolution
    arg2: affine_modflow : ModFlow grid information
    arg3: ncol_ModFlow : number of columns in ModFlow
    arg4: nrow_ModFlow : number of rows in ModFlow
    arg5: init_rivermap_reso : resolution of the initial map defining the river network. In [m]
    arg6: StreamNetworkFile: npy 2D array defining the river network at the finner resolution, 1 if there is a river, 0 if not
    arg7: affine_modflow_200m : ModFlow grid information of the initial map defining the river network
    arg8: ncol_ModFlow_200m : number of columns in ModFlow of the initial map defining the river network
    arg9: nrow_ModFlow_200m : number of rows in ModFlow of the initial map defining the river network
    arg10: crs_modflow : crs of the ModFlow grid (like {'init': 'EPSG:32643'} )
    arg11:create_tif=False : the new map is directly returned as numpy array
    """

    StreamNetwork200 = np.load(StreamNetworkFile)

    ## Defining ModFlow grid
    xi = np.arange(affine_modflow[2], affine_modflow[2] + ncol_ModFlow*affine_modflow[0], res_ModFlow) + res_ModFlow/2
    yi = np.arange(affine_modflow[5], affine_modflow[5] + nrow_ModFlow*affine_modflow[4], -res_ModFlow) - res_ModFlow/2

    ## Defining ModFlow grid at init_rivermap_reso (finer resolution)
    xi200 = np.arange(affine_modflow_200m[2], affine_modflow_200m[2] + ncol_ModFlow_200m*affine_modflow_200m[0],
                      init_rivermap_reso) + init_rivermap_reso/2
    yi200 = np.arange(affine_modflow_200m[5], affine_modflow_200m[5] + nrow_ModFlow_200m*affine_modflow_200m[4],
                      -init_rivermap_reso) - init_rivermap_reso/2

    Ratio = int(res_ModFlow/init_rivermap_reso)
    #xi200, yi200 = np.meshgrid(xi200,yi200) 
    #xi200 = xi200.reshape(np.product(xi200.shape))
    #yi200 = yi200.reshape(np.product(yi200.shape))
    #StreamNetwork200 = StreamNetwork200.reshape(np.product(StreamNetwork200.shape))
   
    RiverPercentage = np.zeros((nrow_ModFlow, ncol_ModFlow))
    # For each ModFlow cell
    for ir in range(0, nrow_ModFlow):
        if int(ir/20.00)-ir/20.00 == 0:
            print('Computing River Stream Percentage [%]: ', round(100.00*ir/nrow_ModFlow*100)/100)
        for ic in range(0, ncol_ModFlow):
            #som=0
            #compt=0
            # Could be improved !
            #if Ratio == 2:  # Simple case
            #    RiverPercentage[ir][ic] = np.nanmean(StreamNetwork200[int(ir*Ratio-Ratio/2.0)+1:int(ir*Ratio+Ratio/2.0)+1,
                #                                     int(ic*Ratio-Ratio/2.0)+1:int(ic*Ratio+Ratio/2.0)+1])
            #else:
            #    RiverPercentage[ir][ic] = np.nanmean(StreamNetwork200[int(round(ir*Ratio-Ratio/2.0))+1:int(round(ir*Ratio+Ratio/2.0))+2,
             #                                        int(round(ic*Ratio-Ratio/2.0))+1:int(round(ic*Ratio+Ratio/2.0))+2])

            RiverPercentage[ir][ic] = np.nanmean(StreamNetwork200[ir*Ratio:(ir+1)*Ratio, ic*Ratio:(ic+1)*Ratio])

            #RiverPercentage[ir][ic]=np.mean(StreamNetwork200[(np.sqrt((yi[ir]-yi200)**2+(xi[ic]-xi200)**2)) <= res_ModFlow/2.0])
            #for ir200 in range(ir*Ratio,ir*Ratio+Ratio):
                #for ic200 in range(ic*Ratio,ic*Ratio+Ratio):
                    #print("irRatio ", ic*Ratio)
                    #print("irRatio+Ratio ", ic*Ratio+Ratio)
                    #if np.abs(yi[ir]-yi200[ir200]) <= res_ModFlow/2.0 and np.abs(xi[ic]-xi200[ic200]) <= res_ModFlow/2.0:
                        #compt+=1
                        #som=som+StreamNetwork200[ir200][ic200] ## Values are equal to 1 if this is a river, 0 else
            #print("compt ", compt)
            #print("sum ", som)
            #if compt==0:
                #RiverPercentage[ir][ic]=0
           # else:
                #RiverPercentage[ir][ic]=som/compt # It is not in percent
     
    RiverPercentage[np.isnan(RiverPercentage)] = np.nanmean(RiverPercentage)

    if create_tif:  # We create a new tif fil for Matlab processing, in the aim to compute the stream network
        with rasterio.open(create_tif, 'w', driver='GTiff', width=ncol_ModFlow,
                            height=nrow_ModFlow, count=1, dtype=np.float64, nodata=-500, transform=affine_modflow,
                            crs=crs_modflow) as dst:
            dst.write(RiverPercentage, indexes=1)
        dst.close()
    print('\nThe precentage of river in each ModFlow cell has been computed and saved in\n', create_tif)


    plt.figure()
    plt.subplot(1, 1, 1, aspect='equal')

    limitXwest = affine_modflow[2]
    limitYnorth = affine_modflow[5]
    limitXeast = affine_modflow[2] + ncol_ModFlow*affine_modflow[0]
    limitYsouth = affine_modflow[5] + nrow_ModFlow*affine_modflow[4]
    extent = (limitXwest, limitXeast, limitYsouth, limitYnorth)
    plt.imshow(RiverPercentage, extent=extent, interpolation='none')
    plt.title('River percentage in each ModFlow cell')
    plt.colorbar()
    plt.show()



