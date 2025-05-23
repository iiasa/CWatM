import xarray as xr
import metpy.calc as mpcalc
from metpy.units import units

def calculate_specific_humidity(dewpoint_file, pressure_file, output_file):
    """
    Calculate specific humidity from dewpoint and pressure and save the result to a NetCDF file.

    Args:
        dewpoint_file (str): Path to the NetCDF file containing dewpoint temperature.
        pressure_file (str): Path to the NetCDF file containing pressure.
        output_file (str): Path to save the resulting specific humidity NetCDF file.

    Returns:
        None: Saves the specific humidity to the specified output file.
    """
    # Load the NetCDF files
    dewpoint_ds = xr.open_dataset(dewpoint_file)
    pressure_ds = xr.open_dataset(pressure_file)

    # Extract dewpoint and pressure
    dewpoint = dewpoint_ds['tdps']  # Replace 'dewpoint' with the actual variable name
    dewpoint.attrs['units'] = 'degC'
    pressure = pressure_ds['ps']  # Replace 'pressure' with the actual variable name
    pressure.attrs['units'] = 'hPa'

    # Align dimensions if needed
    dewpoint, pressure = xr.align(dewpoint, pressure)

    # Attach units using MetPy
    dewpoint = dewpoint.metpy.quantify()
    pressure = pressure.metpy.quantify()

    # Calculate specific humidity
    specific_humidity = mpcalc.specific_humidity_from_dewpoint(pressure, dewpoint)

    # Convert the result back to xarray DataArray
    specific_humidity = xr.DataArray(
        specific_humidity,  # Get numerical values
        coords=dewpoint.coords,      # Use the same coordinates as dewpoint
        dims=dewpoint.dims,          # Use the same dimensions as dewpoint
        name="specific_humidity",    # Name of the variable
        attrs={"units": "kg/kg", "long_name": "Specific Humidity"}  # Metadata
    )

    # Save the result to a NetCDF file
    specific_humidity.to_netcdf(output_file)
    print(f"Specific humidity saved to {output_file}")


# Example usage
calculate_specific_humidity(
    dewpoint_file="/home/ral003/hall5/datasets/basins/thompson/snowclim_era_land/tdps_day_1950-2021_Thompson_C.nc",
    pressure_file="/home/ral003/hall5/datasets/basins/thompson/snowclim_era_land/ps_day_1950-2021_Thompson_hPa.nc",
    output_file="/home/ral003/hall5/datasets/basins/thompson/snowclim_era_land/huss_day_1950-2021_Thompson_kgkg.nc"
)
