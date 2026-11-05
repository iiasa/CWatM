# -------------------------------------------------------------------------
# Name:        INITCONDITION
# Purpose:     Read/write initial conditions for warm start
#
# Author:      PB
# Created:     19/08/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
from cwatm.management_modules.caching import readexcel

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
    daily_crop_KC                        Flag          True if the growth stages in Excel are in days (longest season > 36)    bool 
    loadInit                             Flag          If true initial conditions are loaded                                   bool 
    includeDesal                         Flag                                                                                  --   
    unlimitedDesal                       Flag                                                                                  --   
    desalAnnualCap                       Number                                                                                --   
    wwt_def                              Flag                                                                                  --   
    wastewater_to_reservoirs             Array                                                                                 --   
    initLoadFile                         String        load file name of the initial condition data                            --   
    saveInit                             Flag          If true initial conditions are saved                                    bool 
    saveInitFile                         String        save file name of the initial condition data                            --   
    reservoir_info                       List          Values per reservoir from Excel sheet Reservoirs                        --   
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

    def excel_settings_file(self, use):
        """
        Path of the Excel settings file; Error 137 if it is not in the settings file.

        Parameters
        ----------
        use : str
            What the file is needed for - for the error message

        Returns
        -------
        str
            Path of the Excel settings file
        """
        if 'Excel_settings_file' in binding:
            return cbinding('Excel_settings_file')
        msg = "Error 137: The Excel settings file needs to be included into the settings file:\n" \
              "Excel_settings_file ="+r"*PATH*\cwatm_settings.xlsx"+"\n"
        msg += "It is needed for: " + use + "\n"
        raise CWATMError(msg)

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
        df = readexcel(xl_settings_file_path, 'Crops')

        # Growth stages are given in months or in days, for all crops in the same way
        # The longest season decides: more than 36 cannot be months (so far at most 17 months are used)
        stages = df[['GS1', 'GS2', 'GS3', 'GS4']]
        seasons = stages.sum(axis=1)
        self.var.daily_crop_KC = bool(len(df) > 0 and seasons.max() > 36)
        if self.var.daily_crop_KC:
            # with days: a season below 25 is most likely a crop given in months (mixed table)
            wrong = df['Crop'][(seasons < 25) | (stages % 1 != 0).any(axis=1)].tolist()
            if wrong:
                msg = "Error 157: Excel settings file: " + xl_settings_file_path + "\n"
                msg += "Sheet \"Crops\": the longest season is " + str(seasons.max()) + " -> growth stages are read as days\n"
                msg += "All crops need whole days for GS1 to GS4 and a season of at least 25 days. Not valid: " + str(wrong) + "\n"
                raise CWATMError(msg)

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

            if self.var.daily_crop_KC:
                # whole days (checked above), a column can be read as float
                gs1, gs2, gs3, gs4 = [int(df['GS' + str(gs)][i]) for gs in range(1, 5)]

                KC_crop_daily_stage_1 = [df['KC1'][i]] * gs1
                KC_crop_daily_stage_2 = [df['KC1'][i] * (1 - (d / gs2)) + df['KC2'][i] * (d / gs2) for d in range(gs2)]
                KC_crop_daily_stage_3 = [df['KC2'][i]] * gs3
                KC_crop_daily_stage_4 = [df['KC2'][i] * (1 - (d / gs4)) + df['KC3'][i] * (d / gs4) for d in range(gs4)]

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
        Read the sheet Reservoirs: new reservoirs and values replacing the maps for existing reservoirs.

        The first 19 rows of each column from the 6th column on: ID, new reservoir, lat, lon, type, name,
        area, outflow, volume, lake factors, year, storage limits and outflow limits.
        
        Parameters
        ----------
        xl_settings_file_path : str
            Path to Excel file containing reservoir configuration data

        Returns
        -------
        list
            One list of 19 values per reservoir
        """
        df = readexcel(xl_settings_file_path, 'Reservoirs', header=None)

        # reservoir_info = one list of the 19 values of a reservoir per column, from the 6th column on
        reservoir_info = []
        if len(df) < 19:
            msg = "Error 126: Excel settings file: " + xl_settings_file_path + "\n"
            msg += "Sheet \"Reservoirs\" needs at least 19 rows, it has " + str(len(df)) + "\n"
            raise CWATMError(msg)
        for col in list(df)[5:]:
            info = []
            # more complicated by sometimes excel mismatch dtypes
            for var in range(19):
                v = np.array(df[col][var]).tolist()
                info.append(v)

            # an empty cell is NaN: it would count as True for "New Reservoir" and cannot be converted to int
            blank = [isinstance(v, float) and np.isnan(v) for v in info]
            if blank[0] or blank[1] or (info[1] and (blank[2] or blank[3])):
                msg = "Error 126: Excel settings file: " + xl_settings_file_path + "\n"
                msg += "Sheet \"Reservoirs\", column " + str(col + 1) + ": needs an ID and New Reservoir (True or False)"
                msg += " and for a new reservoir also lat and lon\n"
                raise CWATMError(msg)
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
        df = readexcel(xl_settings_file_path, 'Reservoir_transfers', header=None)

        # reservoir_transfers = [ [Giving reservoir, Receiving reservoir, [366-day array of releases]] ]
        reservoir_transfers = []
        if len(df) < 370:
            msg = "Error 156: Excel settings file: " + xl_settings_file_path + "\n"
            msg += "Sheet \"Reservoir_transfers\" needs 370 rows (4 rows + 366 days), it has " + str(len(df)) + "\n"
            raise CWATMError(msg)

        for col in list(df)[5:]:
            releases = [df[col][4+day] for day in range(366)]
            # info for transfer: Ruleset, giving res, receiving res, Limits, release days
            # default rule = 1
            try:
                rule = int(df[col][0])
            except (ValueError, TypeError):
                # e.g. empty cell
                rule = 1
            try:
                giver, receiver = int(df[col][1]), int(df[col][2])
            except (ValueError, TypeError):
                msg = "Error 156: Excel settings file: " + xl_settings_file_path + "\n"
                msg += "Sheet \"Reservoir_transfers\", column " + str(col + 1)
                msg += ": giving and receiving reservoir have to be whole numbers (0 = from/to outside)\n"
                raise CWATMError(msg)
            transfer = [rule, giver, receiver, df[col][3], releases]
            reservoir_transfers.append(transfer)

        return reservoir_transfers
 
    # To initialize wastewater2reservoir; and wastewater attributes
    def wastewater_to_reservoirs(self, xl_settings_file_path):
        """
        Read the sheet Wastewater_to_reservoirs: which treatment plant sends water to which reservoirs.
        
        Parameters
        ----------
        xl_settings_file_path : str
            Path to Excel file containing wastewater discharge configurations

        Returns
        -------
        dict
            WWTP ID -> list of receiving reservoirs
        """
        # fix - build an object with wwtp_id as key and res as values.
        # get unique wwtp_id and iterate
        df = readexcel(xl_settings_file_path, 'Wastewater_to_reservoirs')
        
       
        wwtp_to_reservoir = {}

        for wwtpid in df['Sending WWTP'].unique():
            wwtp_to_reservoir[wwtpid] = df[df['Sending WWTP'] == wwtpid]['Receiving Reservoir'].tolist()
        return wwtp_to_reservoir
    
    def wastewater_def(self, xl_settings_file_path):
        """
        Read the sheet Wastewater_def: the definition of each treatment plant.

        Columns: from year, to year, volume, treatment days, treatment level, export share, domestic,
        industrial and minimum hydraulic retention time.
        
        Parameters
        ----------
        xl_settings_file_path : str
            Path to Excel file containing wastewater treatment definitions

        Returns
        -------
        dict
            WWTP ID -> array with one row per period
        """
        df = readexcel(xl_settings_file_path, 'Wastewater_def')
        
        cols = ['From year', 'To year', 'Volume (cubic m per day)', 'Treatment days', 'Treatment level', 'Export share', 'Domestic', 'Industrial', 'min_HRT']
        wwtp_definitions = {}
        for wwtpid in df['WWTP ID'].unique():
            wwtp_definitions[wwtpid] = df[df['WWTP ID'] == wwtpid][cols].to_numpy()
        return wwtp_definitions
    
    def desalinationCapacity(self, xl_settings_file_path):
        """
        Read the sheet Desalination: the capacity of each year of the run.

        A year which is not in the sheet takes the capacity of the last year before it (0 if there is none).
        
        Parameters
        ----------
        xl_settings_file_path : str
            Path to Excel file containing desalination capacity configurations

        Returns
        -------
        dict
            Year -> capacity
        """
        df = readexcel(xl_settings_file_path, 'Desalination')
        
        s_year = dateVar['dateBegin'].year
        e_year = dateVar['dateEnd'].year
        
        desalCap = {}
        # capacity of the last Excel year before the start of the run (0 if there is none)
        before = df[df['Year'] < s_year].sort_values('Year')['Capacity'].to_list()
        lastDesal = before[-1] if before else 0
        for year in range(s_year, e_year + 1):
            if np.isin(year, df['Year']):
                lastDesal = df[df['Year'] == year]['Capacity'].to_list()[0]
            desalCap[year] = lastDesal
        return desalCap
        
    
    def initial(self):
        """
        initial part of the initcondition module
        Puts all the variables which have to be stored in 2 lists:

        * initCondVar: the name of the variable in the init netcdf file
        * initCondVarValue: the variable name, optionally with integer index e.g. w1[2] (read with getoutvar)

        Reads the parameters *save_initial* and *load_initial* to know if to save or load initial values
        """

        # list all initial variables
        # Snow & Frost
        if not checkOption('usepySnowClim', True):
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
        self.var.coverTypes = list(map(str.strip, cbinding("coverTypes").split(",")))

        # soil paddy irrigation
        initCondVar.append("topwater")
        initCondVarValue.append("topwater")

        for i, coverType in enumerate(self.var.coverTypes):
            if coverType in ['forest', 'grassland', 'irrPaddy', 'irrNonPaddy']:
                for cond in ["interceptStor", "w1","w2","w3"]:
                    initCondVar.append(coverType+"_"+ cond)
                    initCondVarValue.append(cond+"["+str(i)+"]")
            if coverType in ['sealed']:
                for cond in ["interceptStor"]:
                    initCondVar.append(coverType+"_"+ cond)
                    initCondVarValue.append(cond+"["+str(i)+"]")

        # land cover fractions: the stores above belong to them (they change with moveIrrFallowToNonIrr and the yearly
        # land cover maps) - a warm start moves the loaded water to the fractions of its first day (landcoverType)
        for i, coverType in enumerate(self.var.coverTypes):
            initCondVar.append("fracVegCover_" + coverType)
            initCondVarValue.append("fracVegCover[" + str(i) + "]")

        self.var.includeCrops = False
        if "includeCrops" in option:
            self.var.includeCrops = checkOption('includeCrops')

        if self.var.includeCrops:

            xl_settings_file_path = self.excel_settings_file('includeCrops')
            self.var.Crops, self.var.Crops_names = self.crops_initialise(xl_settings_file_path)

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

                # crop coefficients: set only on the 1st of a month - without them a run starting later in the
                # month has Kc = 0 until the next month (no crop transpiration, no non-paddy irrigation)
                initCondVar.append('currentKC_' + str(c))
                initCondVarValue.append('currentKC[' + str(c) + ']')
                initCondVar.append('currentKY_' + str(c))
                initCondVarValue.append('currentKY[' + str(c) + ']')

        # water demand (unmetDemandPaddy / unmetDemandNonpaddy removed 2026-11: always 0)
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
                xl_settings_file_path = self.excel_settings_file('includeDesalination')
                self.var.desalAnnualCap = self.desalinationCapacity(xl_settings_file_path)
        
        # groundwater
        if not self.var.modflow:
            initCondVar.append("storGroundwater")
            initCondVarValue.append("storGroundwater")
        else:
            # MODFLOW: capillary rise and saturated fraction are used by soil and land cover before MODFLOW runs on
            # the first day of a restart (the MODFLOW head is saved as <initSave>_<date>_modflowhead.nc)
            initCondVar.append("capillar")
            initCondVarValue.append("capillar")
            initCondVar.append("capriseindex")
            initCondVarValue.append("capriseindex")
            # rejected recharge of the last MODFLOW run: goes to interflow on the next day (landcoverType.py)
            initCondVar.append("rejected_recharge_previous_day")
            initCondVarValue.append("rejected_recharge_previous_day")
            # seepage scheme (modflow_seepage, groundwater_modflow/transient.py): seepage pond of the land covers with soil
            if returnBool('modflow_seepage') if 'modflow_seepage' in binding else True:
                for No in range(4):
                    initCondVar.append(self.var.coverTypes[No] + "_seepagePond")
                    initCondVarValue.append("seepagePond[" + str(No) + "]")

        # routing
        # (riverbedExchange removed 2026-11-04: never computed, always 0; old init files still load - the variable is
        # not read any more)
        routing = ["channelStorage", "discharge"]
        initCondVar.extend(routing)
        initCondVarValue.extend(routing)
        # inflow of the previous day (inflow.py): the routing interpolates the inflow of the day from it
        if checkOption('inflow'):
            initCondVar.append("QInM3Old")
            initCondVarValue.append("QInM3Old")

        # lakes & reservoirs
        if checkOption('includeWaterBodies'):
            Var1 = ["lakeInflow", "lakeStorage","reservoirStorage","outLake","lakeOutflow","lakeStorageBalance"]
            Var2 = ["lakeInflow","lakeVolume","reservoirStorage","outLake","lakeOutflow","lakeStorageBalance"]

            initCondVar.extend(Var1)
            initCondVarValue.extend(Var2)

            if returnBool('useSmallLakes'):
                Var1 = ["smalllakeInflow","smalllakeStorage","smalllakeOutflow","smalllakeStorageBalance"]
                Var2 = ["smalllakeInflowOld","smalllakeVolumeM3","smalllakeOutflow","smalllakeStorage"]
                initCondVar.extend(Var1)
                initCondVarValue.extend(Var2)


        if 'reservoir_add_info_in_Excel' in option:
            if checkOption('reservoir_add_info_in_Excel'):
                xl_settings_file_path = self.excel_settings_file('reservoir_add_info_in_Excel')
                self.var.reservoir_info = self.reservoir_addinfo(xl_settings_file_path)


        if 'reservoir_transfers' in option:
            if checkOption('reservoir_transfers'):
                xl_settings_file_path = self.excel_settings_file('reservoir_transfers')
                self.var.reservoir_transfers = self.reservoir_transfers(xl_settings_file_path)
        
        if 'includeWastewater' in option:
            if checkOption('includeWastewater'):
                xl_settings_file_path = self.excel_settings_file('includeWastewater')
                self.var.wwt_def = self.wastewater_def(xl_settings_file_path)
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

        # Save init file
        # several initial conditions can be stored in different netcdf files
        # initSave has the path and the first part of the name
        # intInit has the dates - as a single date, as several dates
        # or in certain interval e.g. 2y = every 2 years, 3m = every 3 month, 15d = every 15 days

        self.var.saveInit = returnBool('save_initial')
        if self.var.saveInit:
            self.var.saveInitFile = cbinding('initSave')
            initdates = cbinding('StepInit').split()
            datetosaveInit(initdates,dateVar['dateBegin'],dateVar['dateEnd'])

    def dynamic(self):
        """
        Dynamic part of the initcondition module
        write initial conditions into a single netcdf file

        Note:
            Several dates can be stored in different netcdf files
        """

        if self.var.saveInit:
            if  dateVar['curr'] in dateVar['intInit']:
                saveFile = self.var.saveInitFile + "_" + "%02d%02d%02d.nc" % (dateVar['currDate'].year, dateVar['currDate'].month, dateVar['currDate'].day)
                initVar=[]
                for value in initCondVarValue:
                    base, index = parseoutvar(value)
                    initVar.append(getoutvar(self.var, base, index))
                writeIniNetcdf(saveFile, initCondVar,initVar)

