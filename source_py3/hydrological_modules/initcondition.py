# -------------------------------------------------------------------------
# Name:        INITCONDITION
# Purpose:	   Read/write initial condtions for warm start
#
# Author:      PB
#
# Created:     19/08/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *

class initcondition(object):

    """
    READ/WRITE INITIAL CONDITIONS
    all initial condition can be stored at the end of a run to be used as a **warm** start for a following up run
    """

    def __init__(self, initcondition_variable):
        self.var = initcondition_variable


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """
        initial part of the initcondition module
		Puts all the variables which has to be stored in 2 lists:

		* initCondVar: the name of the variable in the init netcdf file
		* initCondVarValue: the variable as it can be read with the 'eval' command

		Reads the parameter *save_initial* and *save_initial* to know if to save or load initial values
        """

        # list all initiatial variables
        # Snow & Frost
        number = int(loadmap('NumberSnowLayers'))
        for i in range(number):
            initCondVar.append("SnowCover"+str(i+1))
            initCondVarValue.append("SnowCoverS["+str(i)+"]")
        initCondVar.append("FrostIndex")
        initCondVarValue.append("FrostIndex")

        if checkOption('includeRunoffConcentration'):
            for i in range(10):
                initCondVar.append("runoff_conc" + str(i + 1))
                initCondVarValue.append("runoff_conc[" + str(i) + "]")


        # soil / landcover
        i = 0
        self.var.coverTypes = list(map(str.strip, cbinding("coverTypes").split(",")))

        # soil paddy irrigation
        initCondVar.append("topwater")
        initCondVarValue.append("topwater")

        for coverType in self.var.coverTypes:
            if coverType in ['forest', 'grassland', 'irrPaddy', 'irrNonPaddy']:
                for cond in ["interceptStor", "w1","w2","w3"]:
                    initCondVar.append(coverType+"_"+ cond)
                    initCondVarValue.append(cond+"["+str(i)+"]")
            if coverType in ['sealed']:
                for cond in ["interceptStor"]:
                    initCondVar.append(coverType+"_"+ cond)
                    initCondVarValue.append(cond+"["+str(i)+"]")
            i += 1

        # water demand
        initCondVar.append("unmetDemandPaddy")
        initCondVarValue.append("unmetDemandPaddy")
        initCondVar.append("unmetDemandNonpaddy")
        initCondVarValue.append("unmetDemandNonpaddy")

        # groundwater
        initCondVar.append("storGroundwater")
        initCondVarValue.append("storGroundwater")

        # routing
        Var1 = ["channelStorage", "discharge", "riverbedExchange"]
        Var2 = ["channelStorage", "discharge", "riverbedExchange"]

        initCondVar.extend(Var1)
        initCondVarValue.extend(Var2)

        # lakes & reservoirs
        if checkOption('includeWaterBodies'):
            Var1 = ["lakeInflow", "lakeStorage","reservoirStorage","outLake","lakeOutflow"]
            Var2 = ["lakeInflow","lakeVolume","reservoirStorage","outLake","lakeOutflow"]
            initCondVar.extend(Var1)
            initCondVarValue.extend(Var2)

        # lakes & reservoirs

        if checkOption('includeWaterBodies'):
            if returnBool('useSmallLakes'):
                Var1 = ["smalllakeInflow","smalllakeStorage","smalllakeOutflow"]
                Var2 = ["smalllakeInflowOld","smalllakeVolumeM3","smalllakeOutflow"]
                initCondVar.extend(Var1)
                initCondVarValue.extend(Var2)



        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # Load init file - a single file can be loaded - needs path and file name
        self.var.loadInit = returnBool('load_initial')
        if self.var.loadInit:
            self.var.initLoadFile = cbinding('initLoad')

        # Safe init file
        # several initial conditions can be stored in different netcdf files
        # initSave has the path and the first part of the name
        # intInit has the dates - as a single date, as several dates
        # or in certain interval e.g. 2y = every 2 years, 3m = every 3 month, 15d = every 15 days

        self.var.saveInit = returnBool('save_initial')

        if self.var.saveInit:
            self.var.saveInitFile = cbinding('initSave')
            initdates = cbinding('StepInit').split()
            datetosaveInit(initdates,dateVar['dateBegin'],dateVar['dateEnd'])

            #for d in initdates:
            #    dd = datetoInt(d, dateVar['dateBegin'])
            #    dateVar['intInit'].append(datetoInt(d, dateVar['dateBegin']))




# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def load_initial(self,name,default = 0.0,number = None):
        """
        First it is checked if the initial value is given in the settings file

        * if it is <> None it is used directly
        * if None it is loaded from the init netcdf file

        :param name: Name of the init value
        :param default: default value -> default is 0.0
        :param number: in case of snow or runoff concentration several layers are included: number = no of the layer
        :return: spatial map or value of initial condition
        """

        if number is not None:
            name = name + str(number)

        if self.var.loadInit:
            return readnetcdfInitial(self.var.initLoadFile, name)
        else:
            return default

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Dynamic part of the initcondition module
        write initital conditions into a single netcdf file

        Note:
            Several dates can be stored in different netcdf files
        """

        if self.var.saveInit:

            if  dateVar['curr'] in dateVar['intInit']:


                #self.var.avgDischarge = self.var.discharge
                #self.var.waterBodyStorage = globals.inZero.copy()

                #saveFile = self.var.saveInitFile + "_" + dateVar['currDate'].strftime("%Y%m%d") +".nc"
                saveFile = self.var.saveInitFile + "_" + "%02d%02d%02d.nc" % (dateVar['currDate'].year, dateVar['currDate'].month, dateVar['currDate'].day)
                initVar=[]
                i = 0
                for var in initCondVar:
                    variabel = "self.var."+initCondVarValue[i]
                    #print variabel
                    initVar.append(eval(variabel))
                    i += 1
                writeIniNetcdf(saveFile, initCondVar,initVar)

