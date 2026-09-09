#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 20 15:36:37 2011
@ author:                  Sat Kumar Tomer (modified by Hylke Beck)
@ author's webpage:        http://civil.iisc.ernet.in/~satkumar/
@ author's email id:       satkumartomer@gmail.com
@ author's website:        www.ambhas.com

A library with Python functions for calculating several objective functions commonly used in hydrological sciences.
Inputs consist of two equal sized arrays representing modeled and observed time series, and an integer specifying the
number of days to ignore in the beginning of the time series.

Example usage:
correlation = HydroStats.correlation(s=Qsim,o=Qobs,365)

Functions:
    RSR :     RMSE-observations standard deviation ratio
    br :      bias ratio
    pc_bias : percentage bias
    pc_bias2: percentage bias 2
    apb :     absolute percent bias
    apb2 :    absolute percent bias 2
    rmse :    root mean square error
    mae :     mean absolute error
    bias :    bias
    NS :      Nash Sutcliffe Coefficient
    NSlog :   Nash Sutcliffe Coefficient from log-transformed data
    correlation: correlation
    KGE:      Kling Gupta Efficiency
    vr :      variability ratio
    
"""

# import required modules
import numpy as np
from random import randrange
#import matplotlib.pyplot as plt
from scipy.optimize import fsolve
from scipy.stats import gamma,kstest
import numpy.ma as ma
import warnings


def filter_nan(s,o):
    """
    this functions removed the data  from simulated and observed data
    whereever the observed data contains nan
    
    this is used by all other functions, otherwise they will produce nan as 
    output
    """
    data = np.array([s.flatten(),o.flatten()])
    data = np.transpose(data)
    data = data[~np.isnan(data).any(1)]

    #mask = ~np.isnan(s) & ~np.isnan(o)
    #o_nonan = o[mask]
    #s_nonan = s[mask]

    #return o_nonan,s_nonan
    return data[:,0],data[:,1]



def RSR(s,o,warmup):
    """
    RMSE-observations standard deviation ratio
    input:
        s: simulated
        o: observed
    output:
        RSR: RMSE-observations standard deviation ratio
    """
    #s = s[warmup+1:]
    #o = o[warmup+1:]
    #s,o = filter_nan(s,o)
    RMSE = np.sqrt(np.sum((s-o) ** 2))
    STDEV_obs = np.sqrt(np.sum((o-np.mean(o)) ** 2))
    return RMSE/STDEV_obs

def br(s,o,warmup):
    """
    Bias ratio
    input:
        s: simulated
        o: observed
    output:
        br: bias ratio
    """
    s = s[warmup+1:]
    o = o[warmup+1:]
    s,o = filter_nan(s,o)
    return 1 - abs(np.mean(s)/np.mean(o) - 1)

def pc_bias(s,o,warmup):
    """
    Percent Bias
    input:
        s: simulated
        o: observed
    output:
        pc_bias: percent bias
    """
    s = s[warmup+1:]
    o = o[warmup+1:]
    s,o = filter_nan(s,o)
    return 100.0*sum(s-o)/sum(o)

def pc_bias2(s,o,warmup):
    """
    Percent Bias 2
    input:
        s: simulated
        o: observed
    output:
        apb2: absolute percent bias 2
    """
    #s = s[warmup+1:]
    #o = o[warmup+1:]
    #s,o = filter_nan(s,o)
    return 100*(np.mean(s)-np.mean(o))/np.mean(o)

def apb(s,o,warmup):
    """
    Absolute Percent Bias
    input:
        s: simulated
        o: observed
    output:
        apb: absolute percent bias
    """
    s = s[warmup+1:]
    o = o[warmup+1:]
    s,o = filter_nan(s,o)
    return 100.0*sum(abs(s-o))/sum(o)

def apb2(s,o,warmup):
    """
    Absolute Percent Bias 2
    input:
        s: simulated
        o: observed
    output:
        apb2: absolute percent bias 2
    """
    s = s[warmup+1:]
    o = o[warmup+1:]
    s,o = filter_nan(s,o)
    return 100*abs(np.mean(s)-np.mean(o))/np.mean(o)

def rmse(s,o,warmup):
    """
    Root Mean Squared Error
    input:
        s: simulated
        o: observed
    output:
        rmses: root mean squared error
    """
    #s = s[warmup+1:]
    #o = o[warmup+1:]
    #s,o = filter_nan(s,o)
    return np.sqrt(np.mean((s-o)**2))

def mae(s,o,warmup):
    """
    Mean Absolute Error
    input:
        s: simulated
        o: observed
    output:
        maes: mean absolute error
    """
    #s = s[warmup+1:]
    #o = o[warmup+1:]
    #s,o = filter_nan(s,o)
    return np.mean(abs(s-o))

def bias(s,o,warmup):
    """
    Bias
    input:
        s: simulated
        o: observed
    output:
        bias: bias
    """
    s = s[warmup+1:]
    o = o[warmup+1:]
    s,o = filter_nan(s,o)
    return np.mean(s-o)

def NS(s,o,warmup):
    """
    Nash-Sutcliffe efficiency coefficient
    input:
        s: simulated
        o: observed
    output:
        NS: Nash-Sutcliffe efficient coefficient
    """
    #s = s[warmup+1:]
    #o = o[warmup+1:]
    #s,o = filter_nan(s,o)

    return 1 - sum((s-o)**2)/sum((o-np.mean(o))**2)

def NSlog(s,o,warmup):
    """
    Nash-Sutcliffe efficiency coefficient from log-transformed data
    input:
        s: simulated
        o: observed
    output:
        NSlog: Nash-Sutcliffe efficient coefficient from log-transformed data
    """
    #s = s[warmup+1:]
    #o = o[warmup+1:]
    #s,o = filter_nan(s,o)
    s = np.log(s)
    o = np.log(o)
    return 1 - sum((s-o)**2)/sum((o-np.mean(o))**2)

def correlation(s,o,warmup):
    """
    correlation coefficient
    input:
        s: simulated
        o: observed
    output:
        correlation: correlation coefficient
    """
    #s = s[warmup+1:]
    #o = o[warmup+1:]
    #s,o = filter_nan(s,o)
    if s.size == 0:
        corr = np.NaN
    else:
        corr = np.corrcoef(o, s)[0,1]
        
    return corr


def index_agreement(s,o,warmup):
    """
    index of agreement
    input:
        s: simulated
        o: observed
    output:http://dx.doi.org/10.1016/j.jhydrol.2012.01.011
        ia: index of agreement
    """
    #s = s[warmup+1:]
    #o = o[warmup+1:]
    #s,o = filter_nan(s,o)
    ia = 1 -(np.sum((o-s)**2))/(np.sum(
    			(np.abs(s-np.mean(o))+np.abs(o-np.mean(o)))**2))
    return ia

def  rmseglobal(s,o):
    rmse = np.nanmean((s-o)**2,axis=0)
    return rmse

def KGEglobal(s,o):
    warnings.filterwarnings("ignore", message="divide by zero encountered")
    warnings.filterwarnings("ignore", message="invalid value encountered")
    warnings.filterwarnings("ignore", message="Mean of empty slice")
    warnings.filterwarnings("ignore", message="Degrees of freedom")

    B = np.nanmean(s,axis=0) / np.nanmean(o,axis=0)
    pbias = np.nansum((s-o),axis=0) / np.nansum(o,axis=0)
    y = (np.nanstd(s,axis=0) / np.nanmean(s,axis=0)) / (np.nanstd(o,axis=0) / np.nanmean(o,axis=0))
    NS =  1 - np.nansum((s-o)**2,axis=0)/ np.nansum((o-np.nanmean(o,axis=0))**2,axis=0)

    r = np.empty(s.shape[1])
    for i in range(s.shape[1]):
        s1 = ma.masked_invalid(s[:,i])
        o1 = ma.masked_invalid(o[:,i])
        msk = (~o1.mask & ~s1.mask)
        r[i] =ma.corrcoef(o1[msk], s1[msk]).data[0,1]

    KGE = 1 - np.sqrt((r - 1) ** 2 + (B - 1) ** 2 + (y - 1) ** 2)

    return KGE, NS, r, pbias


def rankObj(obj,ranking,w, station_w):
    anz = len(w)
    rank = np.empty(anz)
    weights = np.array(w)
    for i in range(len(ranking)-1):
        y1 = obj >= ranking[i]
        y2 = obj >= ranking[i+1]
        if not(station_w): 
            rank[i] = y1.sum() - y2.sum()        
        else:
            # insert a weigning of stations here
            sumy1 = 0
            sumy2 = 0  
            for j in range(len(obj)):
                sumy1= sumy1 + y1[j] * station_w[j]
                sumy2= sumy2 + y2[j] * station_w[j]
            rank[i] = sumy1 - sumy2
            
    ranksum = (rank*weights).sum()
    return ranksum,rank

def rankB(obj,ranking,w, station_w):
    anz = len(w)
    rank = np.empty(anz)
    weights = np.array(w)
    obj1 = abs(obj) * 100
    for i in range(len(ranking)-1):
        y1 = obj1 <= ranking[i]
        y2 = obj1 <= ranking[i+1]
        if not(station_w):
            rank[i] = y1.sum() - y2.sum()        
        else:
            # insert a weigning of stations here
            sumy1 = 0
            sumy2 = 0  
            for j in range(len(obj)):
                sumy1= sumy1 + y1[j] * station_w[j]
                sumy2= sumy2 + y2[j] * station_w[j]
            rank[i] = sumy1 - sumy2

    ranksum = (rank*weights).sum()
    return ranksum,rank



def KGE(s,o,warmup):
    """
    Kling Gupta Efficiency (Kling et al., 2012, http://dx.doi.org/10.1016/j.jhydrol.2012.01.011)
    input:
        s: simulated
        o: observed
    output:
        KGE: Kling Gupta Efficiency
    """
    #s = s[warmup+1:]
    #o = o[warmup+1:]
    #s,o = filter_nan(s,o)
    B = np.mean(s) / np.mean(o)
    y = (np.std(s) / np.mean(s)) / (np.std(o) / np.mean(o))
    r = np.corrcoef(o, s)[0,1]

    KGE = 1 - np.sqrt((r - 1) ** 2 + (B - 1) ** 2 + (y - 1) ** 2)

    return KGE

def vr(s,o,warmup):
    """
    Variability ratio
    input:
        s: simulated
        o: observed
    output:
        vr: variability ratio
    """
    s = s[warmup+1:]
    o = o[warmup+1:]
    s,o = filter_nan(s,o)
    return 1 - abs((np.std(s) / np.mean(s)) / (np.std(o) / np.mean(o)) - 1)

def budykoFunc(x, const = 2.6):
    return 1 + x - (1 + x**const)**(1/const)

def budykoDist(xp,yp,x):
    return (xp-x)**2 + (yp-budykoFunc(x))**2


def iter1(xp,yp,xmin,step):
    dist0 = 9999999999999999.
    for i in range(20):
        x = xmin + i * step
        dist = budykoDist(xp,yp,x)
        if dist > dist0:
            return x-2*step
        dist0 = dist
    return -9999

def Budyko(x,y):
    xx = x.as_matrix()
    yy = y.as_matrix()
    nr = xx.shape[1]
    budyko = 0

    for k in range(nr):  # through all the gauges
        
        for i in range(len(x)):  # all the yearly values
            xmin = np.minimum(0., xx[i][k])
            for j in range(6):
                step = 10**-j
                xmin = iter1(xx[i][k],yy[i][k],xmin,step)
            xmin = xmin + step
            budyko += budykoDist(xx[i][k],yy[i][k],xmin)

    return budyko

def budw(x,y):
    """
    estimate w-value
    x: ETP/Precipitation
    y: ETA/Precipitation
     
    """
    xx = x.as_matrix()
    yy = y.as_matrix()
    nr = xx.shape[1]
    ads_sum = 0

    for k in range(nr):  # through all the gauges

        for i in range(len(x)):
            func = lambda omega: (1 + xx[i][k] - (1 + xx[i][k] ** omega) ** (1 / omega)) - yy[i][k]
            sol[i] = fsolve(func, 2.6)

    ads =  kstest(sol-1,'gamma',args=(4.54,0,0.37))
    ads_sum += ads[0]
    return ads_sum

def budw1d(x,y):
    """
    estimate w-value (1D)
    x: ETP/Precipitation
    y: ETA/Precipitation
    """
    sol = np.zeros(shape=(len(x)))
    func = lambda omega: (1 + x[i] - (1 + x[i] ** omega) ** (1 / omega)) - y[i]
    for i in range(len(x)):
        #func = lambda omega: (1 + x[i] - (1 + x[i] ** omega) ** (1 / omega)) - y[i]
        sol[i] = fsolve(func, 2.6)

    ads = kstest(sol - 1, 'gamma', args=(4.54, 0, 0.37))
    return ads[0]
