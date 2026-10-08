# -------------------------------------------------------------------------
# Name:        INITCONDITION
# Purpose:     Read/write initial condtions for warm start
#
# Author:      PB
# Created:     19/08/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
import importlib
# importlib to import pandas as pd in has crop sentitive version is used

class initcondition(object):
    """
    Initial conditions management module for model state persistence.
    
    Handles reading and writing of initial conditions for warm start capabilities,
    crop parameterization from Excel files, reservoir configuration, and other
    initialization data required for model setup and restart functionality.
    
    Attributes
    ----------
    var : object
        Reference to model variables object containing state variables
    model : object
        Reference to the main CWatM model instance
        
    Notes
    -----
    The module provides functionality for:
    - Saving and loading model state variables for warm starts
    - Crop parameter initialization from Excel configurations
    - Reservoir operational parameter setup
    - Water transfer and wastewater configuration
    - Desalination capacity initialization
    
    All initial conditions can be stored at the end of a model run
    to be used as a warm start for subsequent model executions.

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    modflow                              Flag          True if modflow_coupling = True in settings file                        bool 
    Crops_names                          Array         Internal: List of specific crops                                        --   
    includeCrops                         Flag          1 when includeCrops=True in Settings, 0 otherwise                       bool 
    Crops                                Array         Internal: List of specific crops and Kc/Ky parameters                   --   
    daily_crop_KC                        Array                                                                                 --   
    loadInit                             Flag          If true initial conditions are loaded                                   bool 
    includeDesal                         Flag                                                                                  --   
    unlimitedDesal                       Flag                                                                                  --   
    desalAnnualCap                       Number                                                                                --   
    wwt_def                              Flag                                                                                  --   
    wastewater_to_reservoirs             Array                                                                                 --   
    initLoadFile                         Number        load file name of the initial condition data                            Strin
    saveInit                             Flag          If true initial conditions are saved                                    bool 
    saveInitFile                         Flag          save file name of the initial condition data                            bool 
    reservoir_info                       List          Number of lakes and reservoirs in Excel                                 --   
    reservoir_transfers                  Array         [['Giving reservoir'][i], ['Receiving reservoir'][i], ['Fraction of li  array
    coverTypes                           Array         land cover types - forest - grassland - irrPaddy - irrNonPaddy - water  --   
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize initial conditions module.
        
        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.var = model.var
        self.model = model

    def crops_initialise(self, xl_settings_file_path):
        """
        Initialize crop parameters from Excel configuration file.
        
        Reads crop-specific parameters including planting dates, growth stages,
        crop coefficients (KC), and yield response factors (KY) from Excel
        spreadsheet for crop-specific water use modeling.
        
        Parameters
        ----------
        xl_settings_file_path : str
            Path to Excel file containing crop parameter configurations
            
        Notes
        -----
        Processes crop data including:
        - Planting month/date for each crop
        - Four growth stage lengths (GS1-GS4)
        - Crop coefficients for each stage (KC1-KC4)
        - Yield response factors for each stage (KY1-KY4)
        
        Supports both monthly and daily time step configurations
        with automatic detection based on growth stage lengths.
        """
        pd = importlib.import_module("pandas", package=None)
        df = pd.read_excel(xl_settings_file_path, sheet_name='Crops')

        # Crops = [ [planting date, [length of growth stage i from planting, kc_i, ky_i]_i]_crop]
        Crops = []
        Crops_names = []
        for i in df.index:
            crop = [df['Planting month'][i]]
            growth_stage_end_month = 0

            # crop = [planting date, [GS1, KC1, KY1], [GS1+GS2, KC2, KY2], ..., [GS1+GS2+GS3+GS4, KC4, KY4]]
            for gs in range(1, 5):
                growth_stage_end_month += df['GS' + str(gs)][i]
                gs_parameters = [growth_stage_end_month, df['KC' + str(gs)][i], df['KY' + str(gs)][i]]
                crop.append(gs_parameters)

            # If the crop inputs are given in days, we pre-calculate the annual cycle of crop coefficients
            # using the first three crop coefficients and four growth stages, following the
            # flat - linear increase - flat - linear decrease standard FAO/AEZ crop coefficient timeseries

            # We detect if the crop inputs are given in days if the total growing season is less than 36:
            # This assumes crops have growing to harvest lengths of less than 60 months and a minimum of 60 days
            self.var.daily_crop_KC = False
            if growth_stage_end_month > 60:
                self.var.daily_crop_KC = True

                KC_crop_daily_stage_1 = [df['KC1'][i]] * df['GS1'][i]
                KC_crop_daily_stage_2 = [df['KC1'][i] * (1 - (d / df['GS2'][i])) + df['KC2'][i] * (d / df['GS2'][i]) for
                                         d in range(df['GS2'][i])]
                KC_crop_daily_stage_3 = [df['KC2'][i]] * df['GS3'][i]
                KC_crop_daily_stage_4 = [df['KC2'][i] * (1 - (d / df['GS4'][i])) + df['KC3'][i] * (d / df['GS4'][i]) for
                                         d in range(df['GS4'][i])]

                # crop = [planting date,
                #        [length of growth stage i from planting, kc_i, ky_i]_i,
                #        [growing cycle of daily KCs]]

                crop.append(
                    KC_crop_daily_stage_1 + KC_crop_daily_stage_2 + KC_crop_daily_stage_3 + KC_crop_daily_stage_4)

            Crops.append(crop)
            Crops_names.append(df['Crop'][i])

        return Crops, Crops_names

    def reservoir_addinfo(self, xl_settings_file_path):
        """
        Load additional reservoir information from Excel configuration.
        
        Reads supplementary reservoir parameters including new reservoir
        locations, operational characteristics, and configuration flags
        from Excel spreadsheet for enhanced reservoir modeling.
        
        Parameters
        ----------
        xl_settings_file_path : str
            Path to Excel file containing reservoir configuration data
        """
        pd = importlib.import_module("pandas", package=None)
        df = pd.read_excel(xl_settings_file_path, header=None, sheet_name='Reservoirs')

        # reservoir_transfers = [ [Giving reservoir, Receiving reservoir, [366-day array of releases]] ]
        reservoir_info = []
        #         0      1      2
        dtypes = ['int', 'bool', 'float', 'float', 'int', 'str', 'float', 'float', 'float', 'float', 'float', 
                  'float', 'float', 'float', 'float', 'float', 'float', 'float']
        for col in list(df)[5:]:
            info = []
            # more complicated by sometimes excel mismatch dtypes
            for var in range(19):
                v = np.array(df[col][var]).tolist()
                info.append(v)
            # info = np.array([df[col][values] for values in range(19)])
            reservoir_info.append(info)

        return reservoir_info


    def reservoir_transfers(self, xl_settings_file_path):
        """
        Configure inter-reservoir water transfer parameters.
        
        Sets up water transfer relationships between reservoirs including
        transfer rates, operational rules, and connectivity information
        from Excel configuration files.
        
        Parameters
        ----------
        xl_settings_file_path : str
            Path to Excel file containing reservoir transfer configurations
        """
        pd = importlib.import_module("pandas", package=None)
        df = pd.read_excel(xl_settings_file_path, header=None, sheet_name='Reservoir_transfers')

        # reservoir_transfers = [ [Giving reservoir, Receiving reservoir, [366-day array of releases]] ]
        reservoir_transfers = []

        for col in list(df)[5:]:
            releases = [df[col][4+day] for day in range(366)]
            # info for transfer: Ruleset, giving res, receiving res, Limits, release days
            # default rule = 1
            try:
                rule = int(df[col][0])
            except:
                rule = 1
            transfer = [rule, int(df[col][1]), int(df[col][2]), df[col][3], releases]
            reservoir_transfers.append(transfer)

        return reservoir_transfers
 
    # To initialize wastewater2reservoir; and wastewater attributes
    def wastewater_to_reservoirs(self, xl_settings_file_path):
        """
        Configure wastewater discharge to reservoirs.
        
        Sets up wastewater treatment and discharge parameters including
        treatment efficiencies, discharge locations, and operational
        characteristics from Excel configuration data.
        
        Parameters
        ----------
        xl_settings_file_path : str
            Path to Excel file containing wastewater discharge configurations
        """
        # fix - build an object with wwtp_id as key and res as values.
        # get unique wwtp_id and iterate
        pd = importlib.import_module("pandas", package=None)
        df = pd.read_excel(xl_settings_file_path, sheet_name='Wastewater_to_reservoirs')
        
       
        wwtp_to_reservoir = {}

        for wwtpid in df['Sending WWTP'].unique():
            wwtp_to_reservoir[wwtpid] = df[df['Sending WWTP'] == wwtpid]['Receiving Reservoir'].tolist()
            #transfer = [df['Sending WWTP'][i], df['Receiving Reservoir'][i]]
            #wwtp_to_reservoir.append(transfer)
        #print(wwtp_to_reservoir)
        return wwtp_to_reservoir
    
    def wasterwater_def(self, xl_settings_file_path):
        """
        Define wastewater treatment parameters and characteristics.
        
        Configures wastewater treatment system parameters including
        treatment capacities, removal efficiencies, and operational
        parameters from Excel configuration files.
        
        Parameters
        ----------
        xl_settings_file_path : str
            Path to Excel file containing wastewater treatment definitions
        """
        pd = importlib.import_module("pandas", package=None)
        df = pd.read_excel(xl_settings_file_path, sheet_name='Wastewater_def')
        
        cols = ['From year', 'To year', 'Volume (cubic m per day)', 'Treatment days', 'Treatment level', 'Export share', 'Domestic', 'Industrial', 'min_HRT']
        wwtp_definitions = {}
        for wwtpid in df['WWTP ID'].unique():
            wwtp_definitions[wwtpid] = df[df['WWTP ID'] == wwtpid][cols].to_numpy()
        return wwtp_definitions
    
    def desalinationCapacity(self, xl_settings_file_path):
        """
        Initialize desalination plant capacity and operational parameters.
        
        Configures desalination facility characteristics including production
        capacities, energy requirements, and operational constraints from
        Excel configuration data.
        
        Parameters
        ----------
        xl_settings_file_path : str
            Path to Excel file containing desalination capacity configurations
        """
        pd = importlib.import_module("pandas", package=None)
        df = pd.read_excel(xl_settings_file_path, sheet_name='Desalination')
        
        s_year = globals.dateVar['dateBegin'].year
        e_year = globals.dateVar['dateEnd'].year
        
        desalCap = {}
        lastDesal = 0
        for year in range(s_year, e_year + 1):
            if np.in1d(year, df['Year']):
                lastDesal = df[df['Year'] == year]['Capacity'].to_list()[0]
            desalCap[year] = lastDesal
        return desalCap
        
    
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

        self.var.includeCrops = False
        if "includeCrops" in option:
            self.var.includeCrops = checkOption('includeCrops')

        if self.var.includeCrops:

            if 'Excel_settings_file' in binding:
                xl_settings_file_path = cbinding('Excel_settings_file')
                self.var.Crops, self.var.Crops_names = self.crops_initialise(xl_settings_file_path)
            else:
                msg = "The Excel settings file needs to be included into the settings file:\n" \
                      "Excel_settings_file ="+r"*PATH*\cwatm_settings.xlsx"+"\n"
                raise CWATMError(msg)

            initCondVar.append('frac_totalIrr_max')
            initCondVarValue.append('frac_totalIrr_max')

            initCondVar.append('frac_totalnonIrr_max')
            initCondVarValue.append('frac_totalnonIrr_max')

            for c in range(len(self.var.Crops)):

                initCondVar.append('monthCounter_'+ str(c))
                initCondVarValue.append('monthCounter['+str(c)+']')

                initCondVar.append('fracCrops_Irr_'+ str(c))
                initCondVarValue.append('fracCrops_Irr['+str(c)+']')

                initCondVar.append('fracCrops_nonIrr_'+ str(c))
                initCondVarValue.append('fracCrops_nonIrr['+str(c)+']')

                initCondVar.append('activatedCrops_'+ str(c))
                initCondVarValue.append('activatedCrops['+str(c)+']')

        # water demand
        initCondVar.append("unmetDemandPaddy")
        initCondVarValue.append("unmetDemandPaddy")
        initCondVar.append("unmetDemandNonpaddy")
        initCondVarValue.append("unmetDemandNonpaddy")

        initCondVar.append('unmetDemand_runningSum')
        initCondVarValue.append('unmetDemand_runningSum')
        
        # Desalination
        self.var.includeDesal = False
        self.var.unlimitedDesal = False
        if 'includeDesalination' in option:
            self.var.includeDesal = checkOption('includeDesalination')
        
        if self.var.includeDesal:
            self.var.unlimitedDesal = returnBool('unlimitedDesalinationCapacity')
            if not self.var.unlimitedDesal:
                xl_settings_file_path = cbinding('Excel_settings_file')
                self.var.desalAnnualCap = self.desalinationCapacity(xl_settings_file_path)
        
        # groundwater
        if not self.var.modflow:
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


        if 'reservoir_add_info_in_Excel' in option:
            if checkOption('reservoir_add_info_in_Excel'):
                if 'Excel_settings_file' in binding:
                    xl_settings_file_path = cbinding('Excel_settings_file')
                    self.var.reservoir_info = self.reservoir_addinfo(xl_settings_file_path)


        if 'reservoir_transfers' in option:
            if checkOption('reservoir_transfers'):
                if 'Excel_settings_file' in binding:
                    xl_settings_file_path = cbinding('Excel_settings_file')
                    self.var.reservoir_transfers = self.reservoir_transfers(xl_settings_file_path)
        
        if 'includeWastewater' in option:
            if checkOption('includeWastewater'):
                if 'Excel_settings_file' in binding:
                    xl_settings_file_path = cbinding('Excel_settings_file')
                    self.var.wwt_def = self.wasterwater_def(xl_settings_file_path)
                    self.var.wastewater_to_reservoirs = self.wastewater_to_reservoirs(xl_settings_file_path)
                    
        
        if 'relax_irrigation_agents' in option:
            if checkOption('relax_irrigation_agents'):
                if 'irrigation_agent_SW_request_month_m3' in binding:
                    initCondVar.append("relaxSWagent")
                    initCondVarValue.append("relaxSWagent")
                if 'irrigation_agent_GW_request_month_m3' in binding:
                    initCondVar.append("relaxGWagent")
                    initCondVarValue.append("relaxGWagent")

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

    def dynamic(self):
        """
        Dynamic part of the initcondition module
        write initital conditions into a single netcdf file

        Note:
            Several dates can be stored in different netcdf files
        """

        if self.var.saveInit:
            if  dateVar['curr'] in dateVar['intInit']:
                saveFile = self.var.saveInitFile + "_" + "%02d%02d%02d.nc" % (dateVar['currDate'].year, dateVar['currDate'].month, dateVar['currDate'].day)
                initVar=[]
                i = 0
                for var in initCondVar:
                    variabel = "self.var."+initCondVarValue[i]
                    #print variabel
                    initVar.append(eval(variabel))
                    i += 1
                writeIniNetcdf(saveFile, initCondVar,initVar)

