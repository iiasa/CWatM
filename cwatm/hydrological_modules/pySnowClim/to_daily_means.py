"""
Module for data conversion functions.

This module contains functions to convert data from specific time steps to daily means
and other time-related transformations. The main function provided here is `to_daily_means`,
which takes input data measured at regular intervals and computes the daily mean values.

"""

import numpy as np

def to_daily_means(data_on_timestep, hours_in_ts):
    """
    Convert data from the specified time step to daily means.

    Parameters:
    data_on_timestep (numpy.ndarray): Input data with a shape (n_time_steps, n_samples).
    hours_in_ts (int): Number of hours in the time step.

    Returns:
    numpy.ndarray: Daily mean values of the input data.
    """
    # Reshape the data to (number of hours in a day / hours_in_ts, number of days, number of samples)
    data_reshape = data_on_timestep.reshape((24 // hours_in_ts, 
                                              data_on_timestep.shape[0] // (24 // hours_in_ts), 
                                              data_on_timestep.shape[1]))
    
    # Calculate the mean across the first axis (time steps)
    data_daily_mean = np.nanmean(data_reshape, axis=0)
    
    return data_daily_mean
