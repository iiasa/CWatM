"""
This script creates and saves a dictionary of parameters for a snow model to read.
Default values are based on the application of the snow model to the western United States.
The parameters include settings for albedo, stability, snow density, and other
model configurations.

"""
import numpy as np
from datetime import datetime, timedelta


def create_dict_parameters(cal=None, hours_in_ts=24, stability=None, windHt=None, tempHt=None,
                          snowoff_month=None, snowoff_day=None, albedo_option=None,
                          max_albedo=None, z_0=None, z_h=None, lw_max=None,
                          Tstart=None, Tadd=None, maxtax=None, E0_value=None, E0_app=None,
                          E0_stable=None, Ts_add=None, smooth_time_steps =None, ground_albedo=None,
                          snow_emis=None, snow_dens_default=None, G=None, max_swe_height=None,
                          downward_radiation_factor=None, downward_radiation_start_month=None,
                          downward_radiation_end_month=None):
    """
    Writes parameters to a dictionary.
    Default values are those used in application of the snow model to the
    western United States, some of which were determined through calibration
    at SNOTEL stations (Lute et al., 2022).

    :param cal: Time period for the model run (default: (2001-10-01 to 2002-09-30))
    :param hours_in_ts: Hours in time step (default: 4)
    :param stability: Stability setting (default: 1)
    :param windHt: Wind height (default: 10)
    :param tempHt: Temperature height (default: 2)
    :param snowoff_month: Month of snow-off (default: 9)
    :param snowoff_day: Day of snow-off (default: 1)
    :param albedo_option: Albedo option (default: 2)
    :param max_albedo: Maximum albedo (default: 0.85)
    :param z_0: Roughness length (default: 0.00001)
    :param z_h: Roughness length for heat (default: z_0/10)
    :param lw_max: Maximum factor water snowpack (default: 0.1)
    :param Tstart: Starting temperature (default: 0)
    :param Tadd: Temperature adjustment (default: -10000)
    :param maxtax: Maximum tax (default: 0.9)
    :param E0_value: Windless exchange coefficient (default: 1)
    :param E0_app: Windless exchange application option (default: 1)
    :param E0_stable: Windless exchange stability option (default: 2)
    :param Ts_add: Temperature add factor (default: 2)
    :param smooth_time_steps: Smoothing time steps (default: 12)
    :param ground_albedo: Ground albedo (default: 0.25)
    :param snow_emis: Snow emissivity (default: 0.98)
    :param snow_dens_default: Default snow density (default: 250)
    :param G: Ground conduction (default: 173/86400 kJ/m2/s)
    :param max_swe_height: Max height of SWE before downward radiation factor starts to work (default: 100 m)
    :param downward_radiation_factor: Factor to be multiplied by downward radiation when SWE > max_swe_height (default: 1.3)
    :param downward_radiation_start_month: Month where downward_radiation_factor start to be applied (default: 6)
    :param downward_radiation_end_month: Month where downward_radiation_factor ends (default: 10)
    """
    if cal is None :
        # Time period for the model run (2001-10-01 to 2002-09-30)
        cal = np.array([[d.year, d.month, d.day, d.hour, d.minute, d.second]
                        for d in (datetime(2001, 10, 1) + timedelta(hours=i * hours_in_ts)
                                  for i in range(int((datetime(2002, 10, 1) - datetime(2001, 10, 1)).total_seconds() / 3600 / hours_in_ts)))])

    # Create a dictionary to store parameters
    parameters = {
        'cal': cal,
        'hours_in_ts': hours_in_ts,
        'stability': 1 if stability is None else stability,
        'windHt': 10 if windHt is None else windHt,
        'tempHt': 2 if tempHt is None else tempHt,
        'snowoff_month': 9 if snowoff_month is None else snowoff_month,
        'snowoff_day': 1 if snowoff_day is None else snowoff_day,
        'albedo_option': 2 if albedo_option is None else albedo_option,
        'max_albedo': 0.85 if max_albedo is None else max_albedo,
        'z_0': 0.00001 if z_0 is None else z_0,
        'z_h': (0.00001 / 10) if z_h is None else z_h,
        'lw_max': 0.1 if lw_max is None else lw_max,
        'Tstart': 0 if Tstart is None else Tstart,
        'Tadd': -10000 if Tadd is None else Tadd,
        'maxtax': 0.9 if maxtax is None else maxtax,
        'E0_value': 1 if E0_value is None else E0_value,
        'E0_app': 1 if E0_app is None else E0_app,
        'E0_stable': 2 if E0_stable is None else E0_stable,
        'Ts_add': 2 if Ts_add is None else Ts_add,
        'smooth_time_steps': 24 // hours_in_ts if smooth_time_steps is None else smooth_time_steps,
        'ground_albedo': 0.25 if ground_albedo is None else ground_albedo,
        'snow_emis': 0.98 if snow_emis is None else snow_emis, #% snow emissivity (from Snow and Climate, Armstrong + Brun eds, pg 58)
        'snow_dens_default': 250 if snow_dens_default is None else snow_dens_default, # % default snow density (kg/m3) (from Essery et al., (2013), snow compaction option 2, based on Cox et al., (1999))
        'G': (173 / 86400) if G is None else G, #% ground conduction (kJ/m2/s), from Walter et al., (2005)
        'max_swe_height': 100 if max_swe_height is None else max_swe_height,
        'downward_radiation_factor': 1.3 if downward_radiation_factor is None else downward_radiation_factor,
        'downward_radiation_start_month': 6 if downward_radiation_start_month is None else downward_radiation_start_month,
        'downward_radiation_end_month': 10 if downward_radiation_end_month is None else downward_radiation_end_month,    
        }

    return parameters
