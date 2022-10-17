# -------------------------------------------------------------------------
# Name:        READ METEO input maps
# Purpose:
#
# Author:      PB
#
# Created:     13/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
from datetime import datetime, timedelta


class environflow(object):

    """
    ENVIRONMENTAL FLOW

    calculates environmental flow


    **Global variables**

    =====================================  ======================================================================  =====
    Variable [self.var]                    Description                                                             Unit 
    =====================================  ======================================================================  =====
    MAF                                    Mean of discharge for all days                                          m3/s 
    Q90                                    10% of the lowest discharge for all days                                m3/s 
    MMF                                    Mean of discharge for each month separately                             m3/s 
    MQ90                                   10% of lowest discharge for each month separately                       m3/s 
    EF_VMF                                 EF requirement with Variable Monthly Flow: Pastor et al.(2014): Accoun  m3/s 
    cut_ef_map                             if TRUE calculated maps of environmental flow are clipped to the area   bool 
    =====================================  ======================================================================  =====

    **Functions**
    """

    def __init__(self, model):
        self.var = model.var
        self.model = model
        
    def initial(self):
        """
        Initial part of environmental flow

        """
        self.var.cut_ef_map = False
        if checkOption('calc_environflow'):
            self.var.cut_ef_map = returnBool('cut_ef_map')
            if returnBool('calc_ef_afterRun'):
                meteofiles['EFDis'] = ''
                try:
                    t = outMap['output_out_map_daily']
                except:
                    msg = "Error 128: OUT_MAP_Daily = discharge may be not defined in [OUTPUT] \n in the settings file: \"" + settingsfile[0] + "\"\n"
                    raise CWATMError(msg)

                for map in outMap['output_out_map_daily']:
                    if map[1] == 'discharge':
                        meteolist = {}
                        indstart = (dateVar['dateStart'] - dateVar['dateBegin']).days
                        indend = (dateVar['dateEnd'] - dateVar['dateBegin']).days
                        meteolist[0] = [map[0], indstart, indend, dateVar['dateStart'], dateVar['dateEnd']]
                        meteofiles['EFDis'] = meteolist

                if meteofiles['EFDis'] == '':
                    print("No discharge map defined")

            else:
                dismap = ["EFDis"]
                multinetdf(dismap, startcheck = 'dateStart')



        self.var.MAF = 1
        self.var.Q90 = 1
        self.var.MMF = 1
        self.var.MQ90 = 1
        self.var.EF_VMF = 1




    # --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    # noinspection PyTypeChecker
    def dynamic(self):
        """
        Dynamic part of the environmental flow module
        Read meteo input maps from netcdf files
        """

        if checkOption('calc_environflow'):
          if (returnBool('calc_ef_afterRun')  == False) or (dateVar['currDate'] == dateVar['dateEnd']):
            # either load already calculated discharge or at the end of the simulation

            # calculate date array
            #datearray = np.arange(dateVar['dateStart'], dateVar['dateEnd'], datetime.timedelta(days=1)).astype(datetime.datetime)
            datearray = np.arange(dateVar['dateStart1'], dateVar['dateEnd1'], timedelta(days=1)).astype(datetime)

            montharray = np.array([d.month for d in datearray])
            monthshape = montharray.shape[0]

            # create empy array for all discharge data
            disall = np.empty(shape=[monthshape, maskinfo['mapC'][0]])

            # run through discharge netcdfs

            name = 'EFDis'
            #idx = inputcounter[name]

            for key in meteofiles[name]:

                filename = os.path.normpath(meteofiles[name][key][0])

                try:
                    nf1 = Dataset(filename, 'r')
                except:
                    msg = "Error 219: Netcdf map stacks: \n"
                    raise CWATMFileError(filename, msg, sname=name)

                value = list(nf1.variables.items())[-1][0]  # get the last variable name

                for i in range(monthshape):
                    if returnBool('cut_ef_map'):
                        mapnp = nf1.variables[value][i, cutmap[2]:cutmap[3], cutmap[0]:cutmap[1]]
                    else:
                        mapnp = nf1.variables[value][i]

                    disall[i, :] = compressArray(mapnp)

                nf1.close()

            self.var.MAF = np.average(disall, axis=0)
            self.var.Q90 = np.percentile(disall, 10, axis=0)

            self.var.MMF = np.empty(shape=[12, maskinfo['mapC'][0]])
            self.var.MQ90 = np.empty(shape=[12, maskinfo['mapC'][0]])
            for i in range(12):
                dispermonth = disall[montharray == (i + 1), :]
                self.var.MMF[i] = np.average(dispermonth, axis=0)
                self.var.MQ90[i] = np.percentile(dispermonth, 10, axis=0)

            ## calculating EF requirement with Variable Monthly Flow p. 5049
            ## A.V.Pastor et al.(2014): Accounting for environmental flow requirements in global water assessments, Hydrol Earth Syst Sci, 18, p5041-5059

            self.var.EF_VMF = np.empty(shape=[12, maskinfo['mapC'][0]])
            for i in range(12):
                self.var.EF_VMF[i] = np.where(self.var.MMF[i] <= (0.4 * self.var.MAF), 0.6 * self.var.MMF[i] ,np.where(self.var.MMF[i] > (0.8 * self.var.MAF), 0.3 * self.var.MMF[i] ,0.45 * self.var.MMF[i]))
            ii = 1







