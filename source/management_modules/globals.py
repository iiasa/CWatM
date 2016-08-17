# -------------------------------------------------------------------------
# Name:        globals
# Purpose:
#
# Author:      burekpe
#
# Created:     16/05/2016
# Copyright:   (c) burekpe 2016
# -------------------------------------------------------------------------

import getopt

global maskinfo,zeromap,modelSteps,xmlstring
maskinfo = {}
modelSteps=[]
xmlstring=[]

global binding, option, FlagName, Flags, ReportSteps, FilterSteps, EnsMembers, outputDir
global MMaskMap, maskmapAttr, bigmapAttr, cutmap, metadataNCDF
global timestepInit
global metaNetcdfVar

timestepInit =[]
binding = {}
option = {}
metaNetcdfVar = {}

#date variable
global dateVar
dateVar = {}

# Output variables
global outDir, outsection, outputTyp
global outMap, outTss
outDir = {}
outMap = {}
outTss = {}
outsection = []
outputTypMap = ['daily', 'monthtot','monthavg', 'monthend','annualtot','annualavg','annualend']
outputTypTss = ['daily', 'monthtot','monthavg', 'monthend','annualtot','annualavg','annualend']

reportTimeSerieAct = {}
reportMapsAll = {}
reportMapsSteps = {}
reportMapsEnd = {}

MMaskMap = 0
ReportSteps = {}
FilterSteps = []
EnsMembers = []
nrCores = []
outputDir = []

maskmapAttr = {}
bigmapAttr = {}
cutmap = [0, 1, 0, 1]
cdfFlag = [0, 0, 0,0,0,0,0]  # flag for netcdf output for all, steps and end, monthly (steps), yearly(steps), monthly , yearly
metadataNCDF = {}

global timeMes,TimeMesString, timeMesSum
timeMes=[]
timeMesString = []  # name of the time measure - filled in dynamic
timeMesSum = []    # time measure of hydrological modules

# ----------------------------------
FlagName = ['quiet', 'veryquiet', 'loud',
            'checkfiles', 'noheader', 'printtime']
Flags = {'quiet': False, 'veryquiet': False, 'loud': False,
         'check': False, 'noheader': False, 'printtime': False}


def globalFlags(arg):
    """ read flags - according to the flags the output is adjusted
        quiet,veryquiet, loud, checkfiles, noheader,printtime
    """
    try:
        opts, args = getopt.getopt(arg, 'qvlcht', FlagName)
    except getopt.GetoptError:
        usage()

    for o, a in opts:
        if o in ('-q', '--quiet'):
            Flags['quiet'] = True          # Flag[0]=1
        if o in ('-v', '--veryquiet'):
            Flags['veryquiet'] = True      # Flag[1]=1
        if o in ('-l', '--loud'):
            Flags['loud'] = True  # Loud=True
        if o in ('-c', '--checkfiles'):
            Flags['check'] = True  # Check=True
        if o in ('-h', '--noheader'):
            Flags['noheader'] = True  # NoHeader=True
        if o in ('-t', '--printtime'):
            Flags['printtime'] = True      # Flag[2]=1
