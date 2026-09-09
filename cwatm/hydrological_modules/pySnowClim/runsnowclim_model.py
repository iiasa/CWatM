"""
This script runs the SnowClim Model. It:
 - Sets default parameter values
 - Imports example forcing data
 - Runs the SnowClim model

The script can be adapted for different parameters, time periods, or datasets.
"""
import os
import scipy.io
import numpy as np
import xarray as xr
import json

from createParameterFile import create_dict_parameters
from snowclim_model import run_snowclim_model

import metpy.calc as mpcalc
from metpy.units import units


FORCINGS = {'lrad', 'solar', 'tavg', 'ppt', 'vs', 'psfc', 'huss', 'relhum','tdmean'}

def _load_forcing_data(file_path, parameters):#,
                                  #first_valid_year, last_valid_year):#, station):
    """
    Load data from a file based on its extension.

    Parameters:
        file_path (str): Path to the input file.

    Returns:
        dict: Dataset in dictionary form with variable names as keys and data arrays as values.
    """
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".nc":
        return _load_ncdf_file(file_path, parameters)#,
                                          #first_valid_year, last_valid_year)#, station)
    else:
        #raise ValueError(f"Unsupported file extension: {ext}")
        return _load_mat_data(file_path)


def _load_ncdf_file(file_path, parameters):#,
                                  #first_valid_year, last_valid_year):#, station):
    """
    Loads a NetCDF file and extracts meteorological forcing data, time, and coordinates.

    Args:
        file_path (str): Path to the NetCDF file.
        parameters (dict): Dictionary containing model parameters.

    Returns:
        dict: Extracted data including latitude, longitude, time, and forcings.
    """
    ds = xr.open_dataset(file_path)#.sel(space=station)
    #start_date = f"{first_valid_year}-01-01"
    #end_date = f"{last_valid_year}-12-31"

    # Select the time range in another xarray dataset (ds2)
    #ds = ds.sel(time=slice(start_date, end_date))

    if np.ndim(ds['lat'].values) > 0:
        lat = np.broadcast_to(ds['lat'].values[:, np.newaxis],
                              (len(ds['lat'].values), len(ds['lon'].values)))
    else:
        lat = np.array(ds['lat'].values).reshape(1,1)

    lon = ds['lon'].values
    time = ds['time'].values
    time_sliced = [str(np.datetime64(t,'s')) for t in time]
    time_sliced = [[int(d[:4]), int(d[5:7]), int(d[8:10]), int(d[11:13]), int(d[14:16]), int(d[17:19])] for d in time_sliced]

    rename_list = [{"tas": "tavg"}, {"rlds": "lrad"}, {"ps": "psfc"},
                {"hr": "relhum"}, {"rsds": "solar"}, {"tdps": "tdmean"},
                {"wind": "vs"}, {"pr": "ppt"}]

    for n in rename_list:
        ds = ds.rename(n)


    pressure_with_units = (ds.psfc.values*0.01) * units('hPa')
    dewpoint_with_units = (ds.tdmean.values-273.15) * units('degC')

    # Calculate specific humidity
    specific_humidity = mpcalc.specific_humidity_from_dewpoint(pressure_with_units,
                                                                dewpoint_with_units)
    # Convert the result back to xarray DataArray
    specific_humidity = xr.DataArray(
        specific_humidity.magnitude,  # Get numerical values
        coords=ds.tdmean.coords,  # Use the same coordinates as dewpoint
        dims=ds.tdmean.dims,      # Use the same dimensions as dewpoint
        name="huss",    # Name of the variable
        attrs={"units": "kg/kg", "long_name": "Specific Humidity"}  # Metadata
    )
    ds = xr.merge([ds,specific_humidity], compat='override')


    # Load meteorological data (forcing inputs)
    forcings = {}
    for f in FORCINGS:
        if ds[f].values.ndim == 1:
            forcings[f] = ds[f].values.reshape(-1, 1, 1)
        else:
            forcings[f] = ds[f].values

        # if f == 'ppt':
        #     forcings[f] /= 1000

        # converting from kJ m-2 hr-1 to kJ m-2 timestep-1
        if f == 'lrad' or f == 'solar':
            forcings[f] *= (parameters['hours_in_ts'] * 3.6)

        if f == 'tavg' or f == 'tdmean':
            forcings[f] -= 273.15

        if f == 'psfc':
            forcings[f] *= 0.01

    final_dict= {'coords':
            {
            'lat': lat,
            'lon': lon,
            'time': time,
            'time_sliced': time_sliced,
            },
        'forcings': forcings
        }
    ds.close()

    return final_dict


def _load_mat_data(data_dir):
    """
    Load meteorological forcing data and geospatial information from the specified directory.

    Args:
        data_dir (str): Path to the directory containing the forcing data files.

    Returns:
        dict: Dictionary containing the loaded variables (lat, lon, lrad, solar, tavg, ppt, vs, psfc, huss, relhum, tdmean).
    """

    # Load latitude, longitude, and elevation data
    latlonelev = scipy.io.loadmat(f'{data_dir}lat_lon_elev.mat')
    lat = latlonelev['lat']
    lon = latlonelev['lon']

    # Load meteorological data (forcing inputs)
    lrad = scipy.io.loadmat(f'{data_dir}lrad.mat')['lrad']
    solar = scipy.io.loadmat(f'{data_dir}solar.mat')['solar']
    tavg = scipy.io.loadmat(f'{data_dir}tavg.mat')['tavg']
    ppt = scipy.io.loadmat(f'{data_dir}ppt.mat')['ppt']
    vs = scipy.io.loadmat(f'{data_dir}vs.mat')['vs']
    psfc = scipy.io.loadmat(f'{data_dir}psfc.mat')['psfc']
    huss = scipy.io.loadmat(f'{data_dir}huss.mat')['huss']
    relhum = scipy.io.loadmat(f'{data_dir}relhum.mat')['relhum']
    tdmean = scipy.io.loadmat(f'{data_dir}tdmean.mat')['tdmean']

    # Return the data as a dictionary
    return {'coords':
            {
            'lat': lat,
            'lon': lon,
            'time': None,
            'time_sliced': None,
            },
        'forcings':
            {
            'lrad': lrad,
            'solar': solar,
            'tavg': tavg,
            'ppt': ppt,
            'vs': vs,
            'psfc': psfc,
            'huss': huss,
            'relhum': relhum,
            'tdmean': tdmean
        }
    }


def _load_parameter_file(parameterfilename):
    """
    Load the parameters from a json file if exists.

    Args:
        parameterfilename (str): Name of the file to load parameters from.

    Returns:
        dict or None: Dictionary of parameters if file exists, otherwise None.
    """
    if parameterfilename is None:
        print("Parameter file undefined, using default parameters")
        parameters = create_dict_parameters()
    else:
        if os.path.exists(parameterfilename):
            print(f"Loading parameters from {parameterfilename}")
            with open(parameterfilename, "r") as f:
                parameters = json.load(f)
        else:
            print(f"Parameter file {parameterfilename} not found, using default parameters")
            parameters = create_dict_parameters()

    return parameters


def _save_outputs_npy(model_output, outputs_path=None):
    """
    Save model outputs to file.

    Args:
        model_output (class): class containing snow model outputs
        outputs_path (str): name of directory to save outputs to.

    Returns:
        nothing
    """
    n_locations = model_output[0].SnowWaterEq.shape[1]
    variables_to_save = [x for x in dir(model_output[0]) if not x.startswith('__')]
    for v in variables_to_save:
        var_data = np.empty((len(model_output),n_locations))
        for t in range(len(model_output)):
            var_data[t,:] = getattr(model_output[t],v).ravel()
        np.save(outputs_path + v + '.npy', var_data)


def _save_variables_as_ncdf(snow_model_list, lat, lon, time, output_dir):
    """
    Save the variables of SnowModelVariables as individual NetCDF files.

    Args:
        snow_model_list (list): A list of SnowModelVariables instances, each representing a time step.
        lat (np.ndarray): Latitude values (1D array).
        lon (np.ndarray): Longitude values (1D array).
        time (np.ndarray): Time values (1D array, e.g., datetime objects or strings).
        output_dir (str): Directory to save the NetCDF files.
    """
    # guarantee to work on size 1 or size > 1
    # lat = np.atleast_1d(lat)
    lon = np.atleast_1d(lon)

    # Calculate the expected shape of combined_data
    expected_shape = (len(time), len(lat[:,0]), len(lon))

    # Get the first instance to determine variable names
    first_instance = snow_model_list[0]
    variable_names = [var for var in dir(first_instance) if not var.startswith("_")]

    for variable_name in variable_names:
        # Combine data for this variable across all time steps
        combined_data = np.stack([getattr(model, variable_name) for model in snow_model_list], axis=0)
        # Reshape combined_data to match the expected shape
        combined_data = combined_data.reshape(expected_shape)

        # Create an xarray DataArray
        da = xr.DataArray(
            combined_data,
            dims=("time", "lat", "lon"),
            coords={"time": time, "lat": lat[:,0], "lon": lon},
            name=variable_name,
            attrs={"description": f"{variable_name} from SnowModelVariables"}
        )

        # Define the output file path
        file_path = os.path.join(output_dir, f"{variable_name}.nc")

        if variable_name == 'SnowWaterEq':
            # Save as NetCDF
            # return da
            da.to_netcdf(file_path)
            print(f"Saved {variable_name} to {file_path}")


def run_model(forcings_path, parameters_path, outputs_path=None, save_format=None):
    #,station=None):

    print('Loading necessary files...')
    parameters = _load_parameter_file(parameters_path)
    forcings_data = _load_forcing_data(forcings_path, parameters)#, station)

    ext = os.path.splitext(forcings_path)[-1].lower()
    if ext != ".nc":
        forcings_data['coords']['time_sliced'] = parameters['cal']

    print('Files loaded, running the model...')
    model_output = run_snowclim_model(forcings_data, parameters)
    if outputs_path is not None:
        if os.path.exists(outputs_path):
            if save_format == '.nc':
                _save_variables_as_ncdf(model_output,
                                        forcings_data['coords']['lat'],
                                        forcings_data['coords']['lon'],
                                        forcings_data['coords']['time'],
                                        outputs_path)
            else:
                _save_outputs_npy(model_output, outputs_path)
        else:
            print('Output to save files does not exist!')

    return model_output
