# -------------------------------------------------------------------------
# Name:        Snow module
# Purpose:
#
# Author:      PB
#
# Created:     13/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
import numpy as np

# TODO remove this portion of the code using sys and make simular to what CWatM uses
# Get the absolute path of /station_gap_fill and to sys.path
# common_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../station_gap_fill"))
# sys.path.append(common_path)
from cwatm.hydrological_modules.pySnowClim.snowclim_model import _process_forcings_and_energy, _run_snowclim_step, _prepare_outputs
from cwatm.hydrological_modules.pySnowClim.createParameterFile import create_dict_parameters
from cwatm.hydrological_modules.pySnowClim.SnowpackVariables import Snowpack
from cwatm.hydrological_modules.pySnowClim.SnowModelVariables import SnowModelVariables
import cwatm.hydrological_modules.pySnowClim.constants as const
import metpy.calc as mpcalc
from metpy.units import units

class snow_frost(object):

    """
    RAIN AND SNOW

    Domain: snow calculations evaluated for center points of up to 7 sub-pixel
    snow zones 1 -7 which each occupy a part of the pixel surface

    Variables *snow* and *rain* at end of this module are the pixel-average snowfall and rain


    **Global variables**

    =====================================  ======================================================================  =====
    Variable [self.var]                    Description                                                             Unit
    =====================================  ======================================================================  =====
    load_initial                           Settings initLoad holds initial conditions for variables                input
    fracGlacierCover                                                                                               --
    DtDay                                  seconds in a timestep (default=86400)                                   s
    dzRel                                  relative elevation above flood plains (max elevation above plain)       m
    Precipitation                          Precipitation (input for the model)                                     m
    Tavg                                   Input, average air Temperature                                          K
    SnowMelt                               total snow melt from all layers                                         m
    Rain                                   Precipitation less snow                                                 m
    prevSnowCover                          snow cover of previous day (only for water balance)                     m
    SnowCover                              snow cover (sum over all layers)                                        m
    numberSnowLayersFloat                                                                                          --
    numberSnowLayers                       Number of snow layers (up to 10)                                        --
    glaciertransportZone                   Number of layers which can be mimiced as glacier transport zone         --
    frac_snow_redistribution                                                                                       --
    DeltaTSnow                             Temperature lapse rate x std. deviation of elevation                    °C
    SnowDayDegrees                         day of the year to degrees: 360/365.25 = 0.9856                         --
    SeasonalSnowMeltSin                                                                                            --
    excludeGlacierArea                                                                                             --
    summerSeasonStart                      day when summer season starts = 165                                     --
    IceDayDegrees                          days of summer (15th June-15th Sept.) to degree: 180/(259-165)          --
    SnowSeason                             seasonal melt factor                                                    m (Ce
    TempSnowLow                            Temperature below which all precipitation is snow                       °C
    TempSnowHigh                           Temperature above which all precipitation is rain                       °C
    TempSnow                               Average temperature at which snow melts                                 °C
    SnowFactor                             Multiplier applied to precipitation that falls as snow                  --
    SnowMeltCoef                           Snow melt coefficient - default: 0.004                                  --
    IceMeltCoef                            Ice melt coefficnet - default  0.007                                    --
    TempMelt                               Average temperature at which snow melts                                 °C
    SnowCoverS                             snow cover for each layer                                               m
    Kfrost                                 Snow depth reduction coefficient, (HH, p. 7.28)                         m-1
    Afrost                                 Daily decay coefficient, (Handbook of Hydrology, p. 7.28)               --
    FrostIndexThreshold                    Degree Days Frost Threshold (stops infiltration, percolation and capil  --
    SnowWaterEquivalent                    Snow water equivalent, (based on snow density of 450 kg/m3) (e.g. Tarb  --
    FrostIndex                             FrostIndex - Molnau and Bissel (1983), A Continuous Frozen Ground Inde  --
    extfrostindex                          Flag for second frostindex                                              --
    FrostIndexThreshold2                   FrostIndex2 - Molnau and Bissel (1983), A Continuous Frozen Ground Ind  --
    frostInd1                              forstindex 1                                                            --
    frostInd2                              frostindex 2                                                            --
    frostindexS                            array for frostindex                                                    --
    Snow                                   Snow (equal to a part of Precipitation)                                 m
    snow_redistributed_previous                                                                                    --
    SnowM1                                                                                                         --
    IceM1                                                                                                          --
    fracVegCover                           Fraction of specific land covers (0=forest, 1=grasslands, etc.)         %
    =====================================  ======================================================================  =====


    **Functions**
    """


    def __init__(self, model):
        self.var = model.var
        self.model = model


    def initial(self):
        """
        Initial part of the snow and frost module

        * loads all the parameters for the day-degree approach for rain, snow and snowmelt
        * loads the parameter for frost
        """

        self.var.numberSnowLayersFloat = loadmap('NumberSnowLayers')

        # now using dz_relative -> fix to 1 or several
        #if self.var.numberSnowLayersFloat > 1.0:
        #    self.var.numberSnowLayersFloat = 5.0
        self.var.numberSnowLayers = int(self.var.numberSnowLayersFloat)
        self.var.glaciertransportZone = int(loadmap('GlacierTransportZone'))  # default 1 -> highest zone is transported to middle zone

        self.var.usepySnowClim = returnBool('usepySnowClim')
        if self.var.usepySnowClim:
            self.var.numberSnowLayers = 1
            self.var.includeGlaciers= False
        # Difference between (average) air temperature at average elevation of
        # pixel and centers of upper- and lower elevation zones [deg C]
        # ElevationStD:   Standard Deviation of the DEM
        # 0.9674:    Quantile of the normal distribution: u(0,833)=0.9674 to split the pixel in 3 equal parts.

        # --- Topography -----------------------------------------------------
        # maps of relative elevation above flood plains

        dzRel = ['dzRel0001','dzRel0005',
                 'dzRel0010','dzRel0020','dzRel0030','dzRel0040','dzRel0050',
                 'dzRel0060','dzRel0070','dzRel0080','dzRel0090','dzRel0100']

        self.var.dzRel = []
        for i in dzRel:
            self.var.dzRel.append(readnetcdfWithoutTime(cbinding('relativeElevation'),i))

        # from relative elevation take 5 levels: 80-100% -> 90% -> id11, 60-80% -> 70% -> id9  ...
        dzSnow = \
            [[7],
            [9, 5],
            [9, 7, 5],
            [11, 8, 5, 3],
            [11, 9, 7, 5, 3],
            [11, 9, 7, 5, 3, 1],
            [11, 9, 8, 7, 5, 3, 1],
            [11, 9, 8, 7, 6, 5, 3, 1],
            [11, 10, 9, 8, 7, 6, 5, 3, 1],
            [11, 10, 9, 8, 7, 6, 5, 4, 3, 1]]

        self.var.dzSnow = dzSnow[self.var.numberSnowLayers - 1]

        self.var.lapseratevar = False
        if 'LapseRateVariable' in binding:
            self.var.lapseratevar = returnBool('LapseRateVariable')

        if self.var.lapseratevar:
            self.var.lapseR = []
            for i in range(12):
                self.var.lapseR.append(readnetcdf12month(cbinding('LapseRate'), i))
                # read lapse rate from Dutra et al. 2022 global 0.25 deg
                # values are negative
                # https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2019ea000984

        else:
            self.var.lapseRate = loadmap('TemperatureLapseRate')

        #divNo = 1./float(self.var.numberSnowLayers)
        #deltaNorm = np.linspace(divNo/2, 1-divNo/2, self.var.numberSnowLayers)
        #self.var.deltaInvNorm = norm.ppf(deltaNorm)
        #self.var.deltaInvNorm = dn[self.var.numberSnowLayers]
        #self.var.ElevationMin = loadmap('Elevation')
        #self.var.ElevationMean = loadmap('Elevation_avg')

        # max_frac_snow_redistriution = 0.5
        # max_ELevationStD = 1500
        #min_ElevationStD_snow_redistr = 100
        # 0.46 is the maximum fraction that can be redistributed if snow density is assumed to be 350kg/m3 according to eq. 13 in Frey & Holzmann (2015)
        # this fraction has to be multiplied with the slope, highest slope is 90 degrees
        # the mean slope of each grid cell is the mean of all slopes of the 3'' SRTM DEM
        # the maximum fraction that can be redistributed if snow density is assumed to be 200kg/m3 according to eq. 13 in Frey & Holzmann (2015) is 0.35
        slope_degrees = np.degrees(np.arctan(loadmap('tanslope')))
        self.var.frac_snow_redistribution = np.maximum(0.35 * slope_degrees / 90, globals.inZero)


        self.var.SnowDayDegrees = 0.9856
        #to get the seasonal cycle in snow melt coefficient, value is 81 (263) for northern (southern) hemisphere
        if 'SeasonalSnowMeltSin' in binding:
            self.var.SeasonalSnowMeltSin = loadmap('SeasonalSnowMeltSin')

        self.var.excludeGlacierArea = False
        if self.var.includeGlaciers:
            self.var.excludeGlacierArea = returnBool('excludeGlacierArea')

        # day of the year to degrees: 360/365.25 = 0.9856
        self.var.summerSeasonStart = 165
        #self.var.IceDayDegrees = 1.915
        self.var.IceDayDegrees = 180./(259- self.var.summerSeasonStart)
        # days of summer (15th June-15th Sept.) to degree: 180/(259-165)
        self.var.SnowSeason = loadmap('SnowSeasonAdj') * 0.5
        # default value of range  of seasonal melt factor is set to 0.001 m C-1 day-1
        # 0.5 x range of sinus function [-1,1]
        if 'TempSnowLow' in binding:
            self.var.TempSnowLow = loadmap('TempSnowLow')
            self.var.TempSnowHigh = loadmap('TempSnowHigh')
        else:
            self.var.TempSnow = loadmap('TempSnow')
        self.var.SnowFactor = loadmap('SnowFactor')
        self.var.SnowMeltCoef = loadmap('SnowMeltCoef')
        self.var.IceMeltCoef = loadmap('IceMeltCoef')

        self.var.TempMelt = loadmap('TempMelt')

        # New snowmelt includes radiation and a calibration factor for radiation
        if 'SnowMeltRad' in binding:
            self.var.SnowMeltRad = loadmap('SnowMeltRad')        # initialize as many snow covers as snow layers -> read them as SnowCover1 , SnowCover2 ...
        else:
            self.var.SnowMeltRad = 1 + globals.inZero

        # SnowCover1 is the highest zone
        self.var.SnowCoverS = []
        for i in range(self.var.numberSnowLayers):
            self.var.SnowCoverS.append(self.var.load_initial("SnowCover",number = i+1))

        # initial snow depth in elevation zones A, B, and C, respectively  [mm]
        self.var.SnowCover = np.sum(self.var.SnowCoverS,axis=0) / self.var.numberSnowLayersFloat + globals.inZero

        # SnowAge
        self.var.SnowAge = []
        for i in range(self.var.numberSnowLayers):
            self.var.SnowAge.append(globals.inZero)

        # if the EMO dataset for meteo data is used, only rd is given, so we need additional data like elevation and latitude
        # it is loaded in evapopot, but not always evapopot is calculated
        if self.var.only_radiation:
            self.var.dem = loadmap('dem')
            self.var.lat = loadmap('latitude')

        # Pixel-average initial snow cover: average of values in 3 elevation
        # zones

        # ---------------------------------------------------------------------------------
        # Initial part of frost index

        self.var.Kfrost = loadmap('Kfrost')
        self.var.Afrost = loadmap('Afrost')
        self.var.FrostIndexThreshold = loadmap('FrostIndexThreshold')
        self.var.SnowWaterEquivalent = loadmap('SnowWaterEquivalent')

        self.var.FrostIndex = self.var.load_initial('FrostIndex')

        if self.var.usepySnowClim:
            # self.var.lat = loadmap('latitude')

            self.var.stability = loadmap('stability')
            self.var.windHt = loadmap('windHt')
            self.var.tempHt = loadmap('tempHt')
            self.var.snowoff_month = loadmap('snowoff_month')
            self.var.snowoff_day = loadmap('snowoff_day')
            self.var.albedo_option = loadmap('albedo_option')
            self.var.max_albedo = loadmap('max_albedo')
            self.var.z_0 = loadmap('z_0')
            self.var.z_h = loadmap('z_h')
            self.var.lw_max = loadmap('lw_max')
            self.var.Tstart = loadmap('Tstart')
            self.var.Tadd = loadmap('Tadd')
            self.var.maxtax = loadmap('maxtax')
            self.var.E0_value = loadmap('E0_value')
            self.var.E0_app = loadmap('E0_app')
            self.var.E0_stable = loadmap('E0_stable')
            self.var.Ts_add = loadmap('Ts_add')
            self.var.smooth_time_steps = loadmap('smooth_time_steps')
            self.var.ground_albedo = loadmap('ground_albedo')
            self.var.snow_emis = loadmap('snow_emis')
            self.var.snow_dens_default = loadmap('snow_dens_default')
            self.var.G = loadmap('G')
            self.var.max_swe_height = loadmap('max_swe_height')
            self.var.downward_radiation_factor = loadmap('downward_radiation_factor')
            self.var.downward_radiation_start_month = loadmap('downward_radiation_start_month')
            self.var.downward_radiation_end_month = loadmap('downward_radiation_end_month')

            # The lines below can be replace by for example
            # stability = loadmap('stability'). The reason is neing loaded before
            # then passed is to give clarify using the xml file variables.
            self.var.snowclimParameters = create_dict_parameters(
                stability = self.var.stability,
                windHt = self.var.windHt,
                tempHt = self.var.tempHt,
                snowoff_month = self.var.snowoff_month,
                snowoff_day = self.var.snowoff_day,
                albedo_option = self.var.albedo_option,
                max_albedo = self.var.max_albedo,
                z_0 = self.var.z_0,
                z_h = self.var.z_h,
                lw_max = self.var.lw_max,
                Tstart = self.var.Tstart,
                Tadd = self.var.Tadd,
                maxtax = self.var.maxtax,
                E0_value = self.var.E0_value,
                E0_app = self.var.E0_app,
                E0_stable = self.var.E0_stable,
                Ts_add = self.var.Ts_add,
                smooth_time_steps = self.var.smooth_time_steps,
                ground_albedo = self.var.ground_albedo,
                snow_emis = self.var.snow_emis,
                snow_dens_default = self.var.snow_dens_default,
                G = self.var.G,
                max_swe_height = self.var.max_swe_height,
                downward_radiation_factor = self.var.downward_radiation_factor,
                downward_radiation_start_month = self.var.downward_radiation_start_month,
                downward_radiation_end_month = self.var.downward_radiation_end_month,
                )

            self.var.snowpack = Snowpack(globals.inZero.shape[0],
                                         self.var.snowclimParameters)
            self.var.snowModelvars = SnowModelVariables(globals.inZero.shape[0])

    # --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Dynamic part of the snow module

        Distinguish between rain/snow and calculates snow melt and glacier melt
        The equation is a modification of:

        References:
            Speers, D.D., Versteeg, J.D. (1979) Runoff forecasting for reservoir operations - the pastand the future. In: Proceedings 52nd Western Snow Conference, 149-156

        Frost index in soil [degree days] based on:

        References:
            Molnau and Bissel (1983, A Continuous Frozen Ground Index for Flood Forecasting. In: Maidment, Handbook of Hydrology, p. 7.28, 7.55)
        """
        if checkOption('calcWaterBalance'):
            self.var.prevSnowCover = self.var.SnowCover.copy()

        if self.var.usepySnowClim:
            # TODO remove the hard coded unit transformations
            # ###############################################
            #               ATTENTION !!!!!                 #
            # ###############################################
            # All the transformations in the forcings data were added to adjust
            # the forcings to the correct units used by pySnowClim, which are:
            # lrad - downward longwave radiation (kJ/m2/hr) (time x space)
            # tavg - average air temperature (C) (time x space)
            # ppt - precipitation (m) (time x space)
            # solar - downward shortwave radiation (kJ/m2/hr) (time x space)
            # tdmean  - dewpoint temperature (C) (time x space)
            # vs - windspeed (m/s) (time x space)
            # relhum - relative humidity (%) (time x space)
            # psfc - air pressure (hPa or mb) (time x space)
            # huss - specific humidity (kg/kg) (time x space)

            # TODO the specific humidity calculation should probably be inside
            # readmeto.py

            # kPa to hPA
            Psurf = self.var.Psurf.copy() * 10
            pressure_with_units = (Psurf) * units('hPa')
            dewpoint_with_units = (self.var.Tdew) * units('degC')

            # Calculate specific humidity
            specific_humidity = mpcalc.specific_humidity_from_dewpoint(
                pressure_with_units, dewpoint_with_units)

            forcings = {"tavg": self.var.Tavg,
                        "psfc": Psurf,
                        # For wind speed there is an adjustment for measurement height made on readmeteo.
                        # Correction from wind speed measured at 10 m to 2 m height
                        "vs": self.var.Wind/0.749, # correction back from the internal correction made by CwatM
                        "ppt": self.var.Precipitation,
                        # from W/m2 to kJ/m2/hr *time step
                        "solar": (self.var.Rsds/self.var.WtoMJ)*3.6*self.var.snowclimParameters['hours_in_ts'],
                        "lrad": (self.var.Rsdl/self.var.WtoMJ)*3.6*self.var.snowclimParameters['hours_in_ts'],
                        "huss": specific_humidity.magnitude,
                        # TODO create a variable for RH.
                        # Qair is in fact RH when using the option useHuss
                        "relhum": self.var.Qair,
                        "tdmean": self.var.Tdew
                }
            # TODO Lat is only used in snowcilm to calculate albedo and define the
            # sizes of the classes. The variable to get lat should be added here after.
            # There is only 1 albedo scheme which uses lat. Tavg is passed here
            # only to have the size of the classes correctly.
            coords = {"lat": self.var.Tavg}
            forcings_data = {"forcings": forcings, "coords": coords}

            # Because CWatM handles data differenty and it is daily these
            # values snow_model_instances and index_snowclim are basically
            # unused by pySnowClim.
            snow_model_instances = [None]
            index_snowclim = 0

            # loading necessary data to run the model
            input_forcings, snow_vars, previous_energy, precip = _process_forcings_and_energy(
                index_snowclim, forcings_data, self.var.snowclimParameters, snow_model_instances)
            # partition between snow and rain made by snowclim
            SnowS = precip.sfe.copy()
            RainS = precip.rain.copy()

            time_value = [dateVar['currDate'].year, dateVar['currDate'].month, dateVar['currDate'].day]
            # Reset to 0 snow at the specified time of year,
            if self.var.snowoff_month > 0:
                if time_value[1] == self.var.snowoff_month and time_value[2] == self.var.snowoff_day:
                    self.var.snowpack = Snowpack(globals.inZero.shape[0],
                                                self.var.snowclimParameters)

            self.var.snowpack, snow_vars = _run_snowclim_step(
                snow_vars,
                self.var.snowpack,
                precip,
                forcings,
                self.var.snowclimParameters,
                coords,
                time_value,
                previous_energy)
            snow_vars.CCsnowfall = precip.snowfallcc.copy()
            self.var.snowModelvars =  _prepare_outputs(snow_vars, precip)

            self.var.ExistSnow = self.var.snowModelvars.ExistSnow.copy()
            self.var.SnowMelt = self.var.snowModelvars.Runoff.copy()/const.WATERDENS
            self.var.Rain_on_snow = np.where(self.var.ExistSnow, precip.rain.copy(), 0)
            self.var.Rain = np.where(self.var.ExistSnow, 0, precip.rain.copy())
            self.var.Snow = precip.sfe.copy()

            self.var.IceMelt = globals.inZero.copy()
            self.var.SnowCover = self.var.snowModelvars.SnowWaterEq.copy()/const.WATERDENS
            self.var.snow_redistributed_previous = globals.inZero.copy()
            self.var.SnowFraction = globals.inZero.copy()
        else:
            # sinus shaped function between the
            # annual minimum (December 21st) and annual maximum (June 21st) for the northern hemisphere
            # annual maximum (December 21st) and annual minimum (June 21st) for the northern hemisphere
            if 'SeasonalSnowMeltSin' in binding:
                SnowMeltCycle = np.sin(np.radians((dateVar['doy'] - self.var.SeasonalSnowMeltSin)
                                        * self.var.SnowDayDegrees))
                SeasSnowMeltCoef = self.var.SnowSeason * SnowMeltCycle + self.var.SnowMeltCoef

                # IceMelt is adjusted to account for southern hemisphere
                # for northern hemisphere Icemelt can occur between doy 166 and doy 256
                # for southern hemisphere Icemelt can occur between doy 348 and doy 73
                # amplitude and curve shape are the same

                SummerSeason = np.sin(
                    math.radians((dateVar['doy'] - self.var.summerSeasonStart) * self.var.SnowDayDegrees * 2))

                SummerSeason = np.where(SummerSeason < 0 or SnowMeltCycle < 0, globals.inZero, SummerSeason)

            else:
                SeasSnowMeltCoef = self.var.SnowSeason * np.sin(math.radians((dateVar['doy'] - 81)
                                                                                * self.var.SnowDayDegrees)) + self.var.SnowMeltCoef
                if (dateVar['doy'] > self.var.summerSeasonStart) and (dateVar['doy'] < 260):
                    SummerSeason = np.sin(math.radians((dateVar['doy'] - self.var.summerSeasonStart) * self.var.IceDayDegrees))
                else:
                    SummerSeason = 0.0

            self.var.Snow = globals.inZero.copy()
            self.var.Rain = globals.inZero.copy()
            self.var.SnowMelt = globals.inZero.copy()
            self.var.IceMelt = globals.inZero.copy()
            self.var.SnowCover = globals.inZero.copy()
            self.var.snow_redistributed_previous = globals.inZero.copy()

            # snow melt potential is collected from up the mountain towards valley
            snowIceM_surplus = globals.inZero.copy()
            # snow cover fraction of a gridcell
            self.var.SnowFraction = globals.inZero.copy()

            #get number of elevation zones with forest
            #assume forest is most present at lowest location
            nr_frac_forest = self.var.numberSnowLayers - np.round(self.var.fracVegCover[0] / (1 / self.var.numberSnowLayers)) - 1

            if self.var.includeGlaciers:
                if self.var.excludeGlacierArea:
                    current_fracGlacierCover = self.var.fracGlacierCover.copy() #percentage area of each layer
                # elev_red = 5
                # current_fracGlacierCover = self.var.fracGlacierCover / elev_red
            #substract glacier area from highest areas
            #loops through snow layers from highest to lowest
            #the capacity depends on the fraction of forest or grassland
            #self.var.SnowCoverSCapacity[i]

            # if only radiation is given like in the EMO meteo dataset:
            # then rsdl has to be calculted in this way
            if self.var.snowmelt_radiation:
                if self.var.only_radiation:
                    radian = np.pi / 180 * self.var.lat
                    distanceSun = 1 + 0.033 * np.cos(2 * np.pi * dateVar['doy'] / 365)
                    # Chapter 3: equation 24
                    declin = 0.409 * np.sin(2 * np.pi * dateVar['doy'] / 365 - 1.39)
                    ws = np.arccos(-np.tan(radian * np.tan(declin)))
                    Ra = 24 * 60 / np.pi * 0.082 * distanceSun * (
                            ws * np.sin(radian) * np.sin(declin) + np.cos(radian) * np.cos(declin) * np.sin(ws))
                    # Equation 21 Chapter 3
                    Rso = Ra * (0.75 + (2 * 10 ** -5 * self.var.dem))  # in MJ/m2/day
                    # Equation 37 Chapter 3
                    RsRso = 1.35 * self.var.Rsds / Rso - 0.35
                    RsRso = np.minimum(np.maximum(RsRso, 0.05), 1)
                    RSNet = (0.34 - 0.14 * np.sqrt(self.var.EAct)) * RsRso
                    # Eact in hPa but needed in kPa : kpa = 0.1 * hPa - conversion done in readmeteo

            month = dateVar['currDate'].month - 1
            # run through all snow layers
            for i in range(self.var.numberSnowLayers):
                if self.var.lapseratevar:
                    # lapse rate from Dutra et al. 2022 is negative
                    TavgS = self.var.Tavg + self.var.lapseR[month] * (self.var.dzRel[self.var.dzSnow[i]] - self.var.dzRel[7])
                else:
                    TavgS = self.var.Tavg - self.var.lapseRate * (self.var.dzRel[self.var.dzSnow[i]] - self.var.dzRel[7])

                # Temperature at center of each zone (temperature at zone B equals Tavg)
                # i=0 -> highest zone
                # i=2 -> lower zone
                if 'TempSnowLow' in binding:
                    #fraction of solid precipitation maximum 1, minimum 0
                    frac_solid = np.clip(1 - (TavgS - self.var.TempSnowLow) / (self.var.TempSnowHigh - self.var.TempSnowLow), 0, 1)
                    SnowS = frac_solid * self.var.SnowFactor * self.var.Precipitation
                    RainS = (1 - frac_solid) * self.var.Precipitation
                else:
                    SnowS = np.where(TavgS < self.var.TempSnow, self.var.SnowFactor * self.var.Precipitation,
                                        globals.inZero)
                    # Precipitation is assumed to be snow if daily average temperature is below TempSnow
                    # Snow is multiplied by correction factor to account for undercatch of
                    # snow precipitation (which is common)
                    RainS = np.where(TavgS >= self.var.TempSnow, self.var.Precipitation, globals.inZero)

                # Snow melt with with radiation
                # radiation part from evaporationPot -> snowmelt has now a temperature part and a radiation part
                # from Erlandsen et al. Hydrology Research 52.2 2021
                if self.var.snowmelt_radiation:
                    # R Shrestha and A. Lima: added albedo decay as a function of snow age based on VIC model (Liang et al., 1994)
                    nosnowtoday = (SnowS<0.01).astype(int)
                    # if snowday -> snowage = 0 otherwise it is added up
                    self.var.SnowAge[i] = self.var.SnowAge[i] * nosnowtoday + nosnowtoday

                    # if it melts snow is decaying faster - snow decay from
                    # Livneh et al 2010 https://doi.org/10.1175/2009JHM1174.1
                    SnowAlb = np.where(TavgS >= self.var.TempSnow,
                                        np.maximum((0.85 * 0.82 ** (self.var.SnowAge[i] ** 0.46)),
                                                    0.4),
                                        np.maximum((0.85 * 0.94 ** (self.var.SnowAge[i] ** 0.58)),
                                                    0.4))

                    SnowAlb = np.minimum(SnowAlb, 0.85)
                    # For radiation (RNup, Rsdl, Rsds) there is a conversion from W/m2 to MJ/m2/d
                    RNup = 4.903E-9 * (TavgS + 273.16) ** 4
                    # if only radiation is given like in the EMO meteo dataset:
                    if self.var.only_radiation:
                        RLN = RNup * RSNet
                    else:
                        RLN = RNup - self.var.Rsdl

                    RN = (self.var.Rsds* (1 - SnowAlb) - RLN) / 334.0
                    # latent heat of fusion = 0.334 mJKg-1 * desity of water = 1000 khm-3

                    SnowMeltS = (TavgS - self.var.TempMelt) * SeasSnowMeltCoef + self.var.SnowMeltRad * RN
                    SnowMeltS = SnowMeltS * (1 + 0.01 * RainS) * self.var.DtDay
                else:
                    # without radiation
                    SnowMeltS = (TavgS - self.var.TempMelt) * SeasSnowMeltCoef * (1 + 0.01 * RainS) * self.var.DtDay

                SnowMeltS = np.maximum(SnowMeltS, globals.inZero)

                # for which layer the ice melt is calculated with the middle temp.
                # for the others it is calculated with the corrected temp
                # this is to mimic glacier transport to lower zones
                if i <= self.var.glaciertransportZone:
                    IceMeltS = self.var.Tavg * self.var.IceMeltCoef * self.var.DtDay * SummerSeason
                    # if i = 0 and 1 -> higher and middle zone
                    # Ice melt coeff in m/C/deg
                else:
                    IceMeltS = TavgS * self.var.IceMeltCoef * self.var.DtDay * SummerSeason

                # Check snowcover and snowmelt
                IceMeltS = np.maximum(IceMeltS, globals.inZero)

                SnowIceMeltS = np.maximum(np.minimum(SnowMeltS + IceMeltS + snowIceM_surplus,
                                                        self.var.SnowCoverS[i]),
                                            globals.inZero)

                # snowIceM_surplus: each elevation band snow melt potential is collected -> one way to melt additianl snow which might
                # be colleted in the valley because of snow retribution
                snowIceM_surplus = np.abs(np.minimum(self.var.SnowCoverS[i] - (SnowMeltS + IceMeltS + snowIceM_surplus),0))

                IceMeltS = np.maximum(SnowIceMeltS - SnowMeltS, globals.inZero)
                SnowMeltS = np.maximum(SnowIceMeltS - IceMeltS, globals.inZero)
                # check if snow+ice not bigger than snowcover
                self.var.SnowCoverS[i] = self.var.SnowCoverS[i] + SnowS - SnowIceMeltS

                # snow redistribution inspired by Frey and Holzmann (2015) doi:10.5194/hess-19-4517-2015
                # if snow cover higher than snow holding capacity redistribution
                # get the thresholds for the snow based on the snow density and snow depth values in Frey and Holzmann (2015)
                # capacity of forest 2.5m snow cover, assumed snow density 250kg/m3: 0.25 * 1000 * 2.5 / 1000
                # capacity of other land cover 0.25m snow cover, assumed snow density 250kg/m3: 0.25 * 1000 * 0.25 / 1000
                # but only for cells with std above 100m
                swe_forest = 0.625
                swe_other = 0.2
                # snow capacity depends on whether there is frost cover in the elevation zone
                snowcapacity = np.where(i <= nr_frac_forest, swe_other, swe_forest)
                # where snow cover is higher than capacity, a fraction of snow will be redistributed

                # reduction factor at lowest level no snow_retri, increasing to factor 0.9 at highest level
                reduction_factor = 1.0 * (1 - (i + 1) / self.var.numberSnowLayers)
                snow_redistributed = np.where(self.var.SnowCoverS[i] > snowcapacity,
                        self.var.frac_snow_redistribution * self.var.SnowCoverS[i] * reduction_factor, 0)
                # the lowest elevation zone cannot redistribute snow -> this is replaced by reduction_factor = 0 in the lowest elevation band
                #if i == self.var.numberSnowLayers - 1:
                #    snow_redistributed = globals.inZero.copy()

                snow_redistributed = np.maximum(snow_redistributed, globals.inZero)
                # if self.var.usepySnowClim:
                #     snow_redistributed = globals.inZero.copy()
                # the current snow cover will be reduced by the amount of snow that is redistributed
                # the redistributed snow from higher elevation zone will be added
                self.var.SnowCoverS[i] = self.var.SnowCoverS[i] - snow_redistributed + self.var.snow_redistributed_previous
                # redistributed snow will be added to next elevation zone in next loop
                self.var.snow_redistributed_previous = snow_redistributed.copy()

                # calculation of snow fraction in each elevation band
                # =< 0.02 SnowCoverS -> no snow
                sfrac = np.where(self.var.SnowCoverS[i] > 0.02,0.25,0)
                sfrac = np.where(self.var.SnowCoverS[i] > 0.05, 0.5,sfrac)
                sfrac = np.where(self.var.SnowCoverS[i] > 0.10, 1.0, sfrac)

                self.var.SnowFraction += sfrac / self.var.numberSnowLayers

                # here outputs are just summed up because equal distribution across elevation zones
                # when glaciers areevations should play less of a role
                if self.var.excludeGlacierArea:
                    # the weight is the fraction of current elevation zone that is not covered by glacier
                    # the glacier is subtracted from the highest elevation zone first
                    weight = 1 / self.var.numberSnowLayers - current_fracGlacierCover
                    # the fraction of glacier cover is decreased by fraction that is covered by glacier in current elevation zone
                    current_fracGlacierCover = np.where(weight > 0, 0, abs(weight))
                    #weight below zero is set to zero
                    weight[weight < 0] = 0
                    assert (weight >= 0).all()
                    self.var.Snow += SnowS * weight
                    self.var.Rain += RainS * weight
                    self.var.SnowMelt += SnowMeltS * weight
                    self.var.IceMelt += IceMeltS * weight
                    self.var.SnowCover += self.var.SnowCoverS[i] * weight
                else:
                    self.var.Snow += SnowS
                    self.var.Rain += RainS
                    self.var.SnowMelt += SnowMeltS
                    self.var.IceMelt += IceMeltS
                    self.var.SnowCover += self.var.SnowCoverS[i]

            if not self.var.excludeGlacierArea:
                self.var.Snow /= self.var.numberSnowLayersFloat
                self.var.Rain /= self.var.numberSnowLayersFloat
                self.var.SnowMelt /= self.var.numberSnowLayersFloat
                self.var.IceMelt /= self.var.numberSnowLayersFloat
                self.var.SnowCover /= self.var.numberSnowLayersFloat

        # DEBUG Snow
        if checkOption('calcWaterBalance'):
            self.model.waterbalance_module.waterBalanceCheck(
                [self.var.Snow],  # In
                [self.var.SnowMelt, self.var.IceMelt],  # Out
                [self.var.prevSnowCover],   # prev storage
                [self.var.SnowCover],
                "Snow1", False)

        # --------------------- included the higher el------------------------------------------------------------
        # Dynamic part of frost index
        self.var.Kfrost = np.where(self.var.Tavg < 0, 0.08, 0.5)
        FrostIndexChangeRate = -(1 - self.var.Afrost) * self.var.FrostIndex - self.var.Tavg * \
            np.exp(-0.4 * 100 * self.var.Kfrost * np.minimum(1.0,self.var.SnowCover / self.var.SnowWaterEquivalent))
        # Rate of change of frost index (expressed as rate, [degree days/day])
        self.var.FrostIndex = np.maximum(self.var.FrostIndex + FrostIndexChangeRate * self.var.DtDay, 0)
        # frost index in soil [degree days] based on Molnau and Bissel (1983, A Continuous Frozen Ground Index for Flood
        # Forecasting. In: Maidment, Handbook of Hydrology, p. 7.28, 7.55)
        # if Tavg is above zero, FrostIndex will stay 0
        # if Tavg is negative, FrostIndex will increase with 1 per degree C per day
        # Exponent of 0.04 (instead of 0.4 in HoH): conversion [cm] to [mm]!  -> from cm to m HERE -> 100 * 0.4
        # maximum snowlayer = 1.0 m
        # Division by SnowDensity because SnowDepth is expressed as equivalent water depth(always less than depth of snow pack)
        # SnowWaterEquivalent taken as 0.45
        # Afrost, (daily decay coefficient) is taken as 0.97 (Handbook of Hydrology, p. 7.28)
        # Kfrost, (snow depth reduction coefficient) is taken as 0.57 [1/cm], (HH, p. 7.28) -> from Molnau taken as 0.5 for t> 0 and 0.08 for T<0
