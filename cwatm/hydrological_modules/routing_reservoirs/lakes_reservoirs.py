# -------------------------------------------------------------------------
# Name:        Lakes and reservoirs module
# Purpose:     Coordinator of the lakes and reservoirs: water bodies from maps and Excel, river network with
#              lakes/reservoirs as pits, yearly water body types, inflow, selection lake/reservoir, water balance,
#              outflow to the river network or to the next lake.
#              Processes in lakes.py, wetlands.py, reservoirs.py, reservoir_transfers.py, puls.py
#
# Author:      PB, MS, DF
# Created:     01/08/2016
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *
from cwatm.management_modules.replace_pcr import npareamaximum, AreaIndex
from cwatm.hydrological_modules.routing_reservoirs.routing_sub import *

from cwatm.management_modules.globals import *
from cwatm.hydrological_modules.routing_reservoirs.puls import lake_parameter_a
from cwatm.hydrological_modules.routing_reservoirs.reservoir_transfers import reservoir_transfers
from cwatm.hydrological_modules.routing_reservoirs.reservoirs import reservoirs, reservoir_info_rows
from cwatm.hydrological_modules.routing_reservoirs.wetlands import wetlands
from cwatm.hydrological_modules.routing_reservoirs.lakes import lakes


def buffer_waterbody(rec, waterBody):
    """
    Puts a buffer of a rectangular rec around the lakes and reservoirs
    (each cell gets the smallest water body ID within the rectangle; water body cells keep their own ID)
    parameter rec = size of rectangular
    output buffer = compressed buffer
    """
    # offsets of the rectangle: j = 1, 2, 3, 4, 5 ... -> 0, 1, -1, 2, -2 ... (even rec: one more cell on the + side)
    offsets = [-(j // 2) if j % 2 else j // 2 for j in range(1, rec + 1)]
    # only water bodies (id > 0) give a value; masked cells and -9999 count as no water body
    ids = np.ma.filled(waterBody, 0)
    buffer = np.where(ids > 0, ids, 1.0e15).astype(np.float64)
    # smallest id in the rectangle = smallest along the rows, then along the columns
    for axis in (0, 1):
        src = buffer
        buffer = np.full(src.shape, 1.0e15)
        n = src.shape[axis]
        for d in offsets:
            if abs(d) >= n:
                continue
            # cell k gets the id of cell k - d (water body at y gives its id to y + d)
            to = [slice(None), slice(None)]
            fr = [slice(None), slice(None)]
            to[axis] = slice(d, n) if d >= 0 else slice(0, n + d)
            fr[axis] = slice(0, n - d) if d >= 0 else slice(-d, n)
            np.minimum(buffer[tuple(to)], src[tuple(fr)], out=buffer[tuple(to)])
    buffer[buffer == 1.0e15] = 0.

    # In the case of overlapping buffers, we ensure that each waterbody
    # is at least inside its own command area, and not the CA of another waterbody
    buffer = np.where(waterBody > 0, waterBody, buffer)

    return compressArray(buffer).astype(np.int64)


class lakes_reservoirs(object):
    """
    Lakes and reservoirs - coordinator

    Water bodies (waterBodyID) are pits of the river network. Each water body has one outlet; the
    lake/reservoir arrays are compressed to the outlets (variable names ending with C).

    Water body types (waterBodyTyp map, Excel sheet Reservoirs):
    1 = lake, 2 = reservoir, 3 = lake before and reservoir after the construction year,
    4 = water distribution reservoir (input = output), 5 = fake reservoir for transfers, 6 = wetland.
    Before the construction year, types 2, 4, 5 are 0 (no retention), type 3 is 1 (waterBodyTypCTemp).

    Sub modules (objects of this class):
    - lakes (lakes.py): Modified Puls approach, warm start
    - wetlands (wetlands.py): type 6 - triangular shape, variable area, maximum level
    - reservoirs (reservoirs.py): reservoir routine of LISFLOOD, releases from netCDF or Excel
    - transfers (reservoir_transfers.py): transfers between reservoirs (rules 1-6)
    - puls.py: shared Modified Puls formulas (also used by lakes_res_small.py)

    The lake and the reservoir routine run in parallel for all water bodies; dynamic_inloop selects the
    outflow by the type of the year and puts it into the river network or into the next lake.

    References: LISFLOOD manual Annex 1 and 3 (Burek et al. 2013)

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    modflow                              Flag          True if modflow_coupling = True in settings file                        bool 
    load_initial                         Flag          Settings initLoad holds initial conditions for variables                bool 
    wastewater_to_reservoirs             Array                                                                                 --   
    reservoir_info                       List          Values per reservoir from Excel sheet Reservoirs                        --   
    waterBodyID_C                        Array         ID of the waterbody - compressed                                        --   
    compress_LR                          Array         boolean map as mask map for compressing lake/reservoir                  --   
    waterBodyOut                         Array         biggest outlet (biggest accumulation of ldd network) of a waterbody     --   
    dirshort                             Array         index of the downstream cell (-1 at pits)                               --   
    ldd_LR                               Array         change river network (put pits in where lakes are)                      --   
    lddCompress                          Array         compressed river network (without missing values)                       --   
    lddCompress_LR                       Array         compressed river network lakes/reservoirs (without missing values)      --   
    dirupLen_LR                          Array         number of bifurcation upstream lake/reservoir                           --   
    downstruct_LR                        Array         river network downstream lake/reservoir                                 --   
    catchment_LR                         Array         catchments lake/reservoir                                               --   
    dirDown_LR                           Array         river network direktion downstream lake/reservoir                       --   
    lendirDown_LR                        Array         number of river network connections lake/reservoir                      --   
    decompress_LR                        Array         boolean map as mask map for decompressing lake/reservoir                --   
    waterBodyOutC                        Array         compressed map biggest outlet of each lake/reservoir                    --   
    resYear                              Array         Settings waterBodyYear, with first operating year of reservoirs         map  
    resYearC                             Array         Compressed map of resYear                                               --   
    resVolumeC                           Array         compressed map of reservoir volume                                      Mm3  
    waterBodyTyp                         Array         Settings, waterBodyTyp, with waterbody type 1-4                         map  
    waterBodyTypC                        Array         water body types 3 reservoirs and lakes (used as reservoirs but before  --   
    lakeArea                             Array         area of each lake/reservoir                                             m2   
    lakeAreaC                            Array         compressed map of the area of each lake/reservoir                       m2   
    lakeDis0                             Array         compressed map average discharge at the outlet of a lake/reservoir      m3 s-
    lakeDis0C                            Array         average discharge at the outlet of a lake/reservoir                     m3 s-
    lakeAC                               Array         compressed map of parameter of channel width, gravity and weir coeffic  --   
    lakeEvaFactorC                       Array         compressed map of a factor which increases evaporation from lake becau  --   
    reslakeoutflow                       Array         outflow of lakes and reservoirs                                         m3   
    lakeVolume                           Array         volume of lakes                                                         m3   
    lakeLevel                            Array         Waterlevel of lakes                                                     m    
    outLake                              Array         outflow from lakes                                                      m    
    lakeInflow                           Array         Inflow into lakes                                                       m3   
    lakeOutflow                          Array         lake outflow - uncompressed  for all basin cells                        m3   
    reservoirStorage                     Array         Storage of reservoirs                                                   m3   
    MtoM3C                               Array         conversion factor from m to m3 (compressed map)                         --   
    EvapWaterBodyMOutlet                 Array         Evaporation from waterbodies - sum at the outlet                        m    
    lakeResInflowM                       Array         lake reservoir inflow in [m]                                            m    
    lakeResOutflowM                      Array         lake reservoiroutflow in [m]                                            m    
    returnFlowLakeM3                     Array         return flow of lake cells, goes into the lake (not into the channel)    m3   
    resVolume                            Array         Reservoir volume                                                        m3   
    includeType4                         Flag          True if there is a reservoir of waterbody type 4 in waterBodyTyp map    bool 
    resId_restricted                     Array         waterbody ID for waste water                                            --   
    waterBodyBuffer                      Array         Create a buffer around water bodies as command areas for lakes and res  m2   
    waterBodyBufferIndex                 Object        index of waterBodyBuffer for area total/maximum, all cells (AreaIndex)  --   
    waterBodyBuffer_wwt                  Array         Create a buffer around water bodies as command areas for lakes and res  m2   
    waterBodyBuffer_wwtIndex             Object        index of waterBodyBuffer_wwt for area total/maximum (AreaIndex)         --   
    reservoir_transfers_option           Flag          True if reservoir_transfers = True (Excel sheet Reservoir_transfers)    bool 
    inflow_option                        Flag          True if inflow = True: inflow from the inflow module into lakes/res.    bool 
    waterBodyTypTemp                     Array         waterbody temp e.g. lake, reservoir, wetlands                           --   
    sumEvapWaterBodyC                    Array         evaporation from waterbodies - compressed                               m    
    sumlakeResInflow                     Array         infow into waterbodies                                                  m3   
    sumlakeResOutflow                    Array         outflow of waterbodies                                                  m3   
    lakeIn                               Array         Inflow into lakes                                                       m3   
    lakeEvapWaterBodyC                   Array         Evaporation from lakes and reservoirs                                   m3   
    resEvapWaterBodyC                    Array         evaporation from reservoirs                                             m    
    EvapWaterBodyM                       Array         Evaporation from lakes and reservoirs                                   m    
    lakeResStorage_filled                Array          Puts the value of lakeResStorage into all cells covered by the waterb  m3   
    lakeResStorage_buffer                Array                                                                                 --   
    lakeStorage                          Array         Storage volume of lakes                                                 m3   
    lakeStorageBalance                   Array         water balance storage of lakes (in-out-evap), saved for warm start      m3   
    resStorage                           Array         Storage volume of reservoirs                                            m3   
    DtSec                                Array         number of seconds per timestep (default = 86400)                        s    
    MtoM3                                Array         Coefficient to change units                                             --   
    waterBodyID                          Array         lakes/reservoirs map with a single ID for each lake/reservoir           --   
    waterBodyIndex                       Object        index of lake/reservoir cells for area total/maximum (AreaIndex)        --   
    UpArea1                              Array         upstream area of a grid cell                                            m2   
    dirupID_LR                           Array         index river upstream lake/reservoir                                     --   
    lakeEvaFactor                        Array         a factor which increases evaporation from lake because of wind          --   
    dtRouting                            Array         number of seconds per routing timestep                                  s    
    noRoutingSteps                       Number        Number of routing step - how often the subroutine is run during a day   --   
    discharge                            Array         Channel discharge                                                       m3 s-
    inflowDt                             Number        flow from inlets per sub step (AI)                                      --   
    downstruct                           Array         structure of the river network in downstream direction                  --   
    runoff_m3                            Array         back to [m]  # with and without in m3 (AI)                              --   
    fracVegCover                         Array         Fraction of specific land covers (0=forest, 1=grasslands, etc.)         %    
    cellArea                             Array         Area of cell                                                            m2   
    includeWastewater                    Flag                                                                                  --   
    waterBodyTyp_unchanged               Array                                                                                 --   
    lakeStorageC                         Array                                                                                 --   
    reservoirStorageM3C                  Array         Initial reservoir fill (fraction of total storage, [-]) (AI)            --   
    lakeResStorageC                      Array         and from the combined onenpfor waterbalance issues (AI)                 --   
    lakeResStorage                       Array                                                                                 --   
    waterBodyTypCTemp                    Array         waterbody temp e.g. lake, reservoir, wetlands -> compressed             --   
    levelOrder_LR                        Array         cells of the network with lakes/reservoirs as pits, sorted by level     --   
    levelStart_LR                        Array         start index of each level in levelOrder_LR (parallel kinematic wave)    --   
    nlevels_LR                           Number        number of levels of the network with lakes/reservoirs as pits           --   
    inLakeSrc                            Array         cells flowing into a lake cell (network with lakes as pits)             --   
    inLakePos                            Array         position of that lake cell in waterBodyIndex.cells                      --   
    outletDense                          Array         lake (renumbered id) of each outlet, in the order of compress_LR        --   
    outBelow                             Array         cell below each lake/reservoir outlet                                   --   
    outToRiver                           Array         True if the cell below the outlet is a river cell                       bool 
    outToLake                            Array         True if the cell below the outlet is a cell of another lake             bool 
    ===================================  ==========    ======================================================================  =====

    """

    def __init__(self, model):
        """
        Initialize lakes and reservoirs module.
        
        Parameters
        ----------
        model : object
            CWatM model instance providing access to variables and configuration
        """
        self.var = model.var
        self.model = model
        # water transfers between reservoirs (reservoir_transfers.py)
        self.transfers = reservoir_transfers(model)
        # reservoirs (reservoirs.py), with the transfers
        self.reservoirs = reservoirs(model, self.transfers)
        # wetlands (wetlands.py, water body type 6)
        self.wetlands = wetlands(model)
        # lakes (lakes.py, Modified Puls), with the wetlands
        self.lakes = lakes(model, self.wetlands)

    def initWaterbodies(self):
        """
        Initialize water bodies
        Read parameters from maps e.g
        area, location, initial average discharge, type 9reservoir or lake) etc.

        Compress numpy array from mask map to the size of lakes+reservoirs
        (marked as capital C at the end of the variable name)
        """

        if checkOption('includeWaterBodies'):

            # load lakes/reservoirs map with a single ID for each lake/reservoir
            self.var.waterBodyID = loadmap('waterBodyID').astype(np.int64)

            # look into the Excel to find if there are new reservoirs
            if checkOption('reservoir_add_info_in_Excel',True):
                resnew = decompress(globals.inZero.copy())
                resnew1 = []
                remove = []

                for i in range(len(self.var.reservoir_info)):

                    if self.var.reservoir_info[i][1]:
                        # create new reservoir/lake
                        col = int((float(self.var.reservoir_info[i][3]) - maskmapAttr['x']) * maskmapAttr['invcell'])
                        row = int((maskmapAttr['y'] - float(self.var.reservoir_info[i][2])) * maskmapAttr['invcell'])
                        if (col<0) or (row<0) or (col> (resnew.shape[1]-1)) or  (row> (resnew.shape[0]-1)):

                            msg = "---- New lake/reservoir No: " + str(int(self.var.reservoir_info[i][0])) + " with coordinates:\n"
                            msg +=  "lat or y: "+ str(self.var.reservoir_info[i][2]) + "  lon or x: " + str(self.var.reservoir_info[i][3]) + "\n"
                            msg += "is not in Mask map (result in row/col " + str(row) + " " + str(col) + ")\n"
                            if Flags['loud']: print (msg)
                            remove.append(self.var.reservoir_info[i])

                        else:
                            resnew[row,col] = int(self.var.reservoir_info[i][0])
                            resnew1.append(int(self.var.reservoir_info[i][0]))

                if len(resnew1) > 0:
                    resnewC = compressArray(resnew).astype(np.int64)
                    # check if lakes/res is in map
                    for i in resnew1:
                        if not(i in resnewC):
                            msg = "--- New lake/reservoir No: "+ str(i) + " is not in the Mask Map\n"
                            if Flags['loud']: print (msg)

                    # check if lake/res already exists
                    index = np.where(resnewC>0)[0]
                    for i in index:
                        if self.var.waterBodyID[i] > 0:
                            msg = "New lake/reservoir No: "+ str(resnewC[i]) + \
                                  " is at the place of an existing one No: "+ str(self.var.waterBodyID[i]) + "\n"
                            raise CWATMError(msg)
                    self.var.waterBodyID = np.where(self.var.waterBodyID == 0, resnewC, self.var.waterBodyID)

                for i in remove:
                    self.var.reservoir_info.remove(i)


            # option includeWastewater (False if not in the settings file)
            self.var.includeWastewater = checkOption('includeWastewater',True)
            # inflow from the inflow module into a lake or reservoir cell (used in each routing substep)
            self.var.inflow_option = checkOption('inflow')
                
            # calculate biggest outlet = biggest accumulation of ldd network
            lakeResmax = npareamaximum(self.var.UpArea1, self.var.waterBodyID)
            self.var.waterBodyOut = np.where(self.var.UpArea1 == lakeResmax, self.var.waterBodyID, 0)

            # dismiss water bodies that are not a subcatchment of an outlet
            sub = subcatchment1(self.var.dirshort, self.var.waterBodyOut, self.var.UpArea1)
            self.var.waterBodyID = np.where(self.var.waterBodyID == sub, sub, 0)

            

            # and again calculate outlets, because ID might have changed due to the operation before
            lakeResmax = npareamaximum(self.var.UpArea1, self.var.waterBodyID)
            self.var.waterBodyOut = np.where(self.var.UpArea1 == lakeResmax, self.var.waterBodyID, 0)

            # change ldd: put pits in where lakes are:
            self.var.ldd_LR = np.where(self.var.waterBodyID > 0, 5, self.var.lddCompress)

            # create new ldd without lakes reservoirs
            self.var.lddCompress_LR, dirshort_LR, self.var.dirupLen_LR, self.var.dirupID_LR, \
            self.var.downstruct_LR, self.var.catchment_LR, self.var.dirDown_LR, self.var.lendirDown_LR = defLdd2(
                self.var.ldd_LR)

            # levels of the network with lakes/reservoirs as pits, for the parallel kinematic wave
            self.var.levelOrder_LR, self.var.levelStart_LR, self.var.nlevels_LR = kinematicLevels(
                self.var.dirDown_LR, self.var.dirupLen_LR, self.var.dirupID_LR)

            # boolean map as mask map for compressing and decompressing
            self.var.compress_LR = self.var.waterBodyOut > 0
            self.var.decompress_LR = np.nonzero(self.var.waterBodyOut)[0]
            self.var.waterBodyOutC = np.compress(self.var.compress_LR, self.var.waterBodyOut)
            self.var.waterBodyID_C = np.compress(self.var.compress_LR, self.var.waterBodyID)
            ids, counts = np.unique(self.var.waterBodyID_C, return_counts=True)
            if (counts > 1).any():
                msg = "Water bodies with more than one outlet (same largest upstream area), No: "
                msg += ", ".join(str(i) for i in ids[counts > 1]) + "\n"
                raise CWATMError(msg)

            # index of the lake/reservoir cells for the area totals in routing (waterBodyID is not changed after this)
            self.var.waterBodyIndex = AreaIndex(self.var.waterBodyID)

            # First year that the reservoir is operating
            self.var.resYear = loadmap('waterBodyYear')
            self.var.resYearC = np.compress(self.var.compress_LR, self.var.resYear)
            self.var.resVolumeC = np.compress(self.var.compress_LR, loadmap('waterBodyVolRes')) * 1000000
            self.var.waterBodyTyp = loadmap('waterBodyTyp').astype(np.int64)
            self.var.waterBodyTypC = np.compress(self.var.compress_LR, self.var.waterBodyTyp)

            # ================================
            # Lakes

            # Surface area of each lake [m2]
            self.var.lakeArea = loadmap('waterBodyArea') * 1000 * 1000  # mult with 1000000 to convert from km2 to m2
            self.var.lakeAreaC = np.compress(self.var.compress_LR, self.var.lakeArea)

            # lake discharge at outlet to calculate alpha: parameter of channel width, gravity and weir coefficient
            # Lake parameter A (suggested  value equal to outflow width in [m])
            # multiplied with the calibration parameter LakeMultiplier
            self.var.lakeDis0 = np.maximum(loadmap('waterBodyDis'), 0.1)
            self.var.lakeDis0C = np.compress(self.var.compress_LR, self.var.lakeDis0)
            lakeAFactor = globals.inZero + loadmap('lakeAFactor')
            lakeAFactorC = np.compress(self.var.compress_LR, lakeAFactor)
            # lakeAC is calculated after the Excel info (discharge and lakeAFactor can be changed there)


            # evaporation factor and start values of the full maps
            # a factor which increases evaporation from lake because of wind
            # (lakeEvaFactor is loaded in routing_kinematic.initial, which runs before)
            self.var.lakeEvaFactorC = np.compress(self.var.compress_LR, self.var.lakeEvaFactor)

            # initial only the big arrays are set to 0,
            # the  initial values are loaded inside the subroutines of lakes and reservoirs
            self.var.reslakeoutflow = globals.inZero.copy()
            self.var.lakeVolume = globals.inZero.copy()
            self.var.lakeLevel = globals.inZero.copy()
            # water balance storage of lakes for the init file (differs from the Puls volume lakeVolume)
            self.var.lakeStorageBalance = globals.inZero.copy()
            self.var.outLake = self.var.load_initial("outLake")

            self.var.lakeStorage = globals.inZero.copy()
            self.var.lakeInflow = globals.inZero.copy()
            self.var.lakeOutflow = globals.inZero.copy()
            self.var.reservoirStorage = globals.inZero.copy()

            self.var.MtoM3C = np.compress(self.var.compress_LR, self.var.MtoM3)

            # init water balance [m]
            self.var.EvapWaterBodyMOutlet = globals.inZero.copy()
            self.var.EvapWaterBodyM = globals.inZero.copy()
            self.var.lakeResInflowM = globals.inZero.copy()
            self.var.lakeResOutflowM = globals.inZero.copy()


            # Excel sheet Reservoirs: values > 0 replace the values of the maps (reservoir_add_info_in_Excel)
            for info, resindex in reservoir_info_rows(self.var):
                if not np.isnan(info[4]) and int(info[4]) >0: self.var.waterBodyTypC[resindex] = int(info[4])

                if float(info[6]) >0: self.var.lakeAreaC[resindex] = float(info[6]) * 1000 * 1000
                if float(info[7]) > 0: self.var.lakeDis0C[resindex] = float(info[7])
                if float(info[8]) > 0: self.var.resVolumeC[resindex] = float(info[8]) * 1000000
                if float(info[9]) > 0: lakeAFactorC[resindex] = float(info[9])
                if float(info[10]) >0: self.var.lakeEvaFactorC[resindex] = float(info[10])
                if float(info[11]) >0: self.var.resYearC[resindex] = int(info[11])

            # lake discharge at outlet to calculate alpha: parameter of channel width, gravity and weir coefficient
            # (after Excel: discharge and lakeAFactor may be changed)
            self.var.lakeAC = lake_parameter_a(self.var.lakeDis0C, lakeAFactorC)

            # wetlands: flags, Excel sheet Wetlands, wet area of the first day (wetlands.py)
            self.wetlands.initial()
            
            # volume from map and Excel, before lakes get a volume
            # (used below: reservoirs without a volume are changed to lakes)
            resVolumeInC = self.var.resVolumeC.copy()
            # correcting reservoir volume for lakes, just to run them all as reservoirs
            # (no division by 0 in reservoirFillC, the reservoir routine runs for all water bodies)
            self.var.resVolumeC = np.where(self.var.resVolumeC > 0, self.var.resVolumeC, self.var.lakeAreaC * 10)
            self.var.resVolume = globals.inZero.copy()
            np.put(self.var.resVolume, self.var.decompress_LR, self.var.resVolumeC)
            # Flag if res type-4 are used
            self.var.includeType4 = bool((self.var.waterBodyTypC == 4).any())
            # full map with the types from map and Excel, before reservoirs are changed to lakes (used by wastewater)
            np.put(self.var.waterBodyTyp, self.var.decompress_LR, self.var.waterBodyTypC)
            self.var.waterBodyTyp_unchanged = self.var.waterBodyTyp.copy()

            # changing reservoirs type 2 and 3 to lakes if volumes (map and Excel) are zero
            self.var.waterBodyTypC = np.where((resVolumeInC <= 0.) & ((self.var.waterBodyTypC == 2) | (self.var.waterBodyTypC == 3)),
                                              1, self.var.waterBodyTypC)
            np.put(self.var.waterBodyTyp, self.var.decompress_LR, self.var.waterBodyTypC)


            # write the construction year back to the full map (used by waterBodyTypTemp for leakage and by wastewater)
            resYearOut = globals.inZero.copy()
            np.put(resYearOut, self.var.decompress_LR, self.var.resYearC)
            self.var.resYear = np.where(self.var.waterBodyID > 0, self.var.waterBodyIndex.maximum(resYearOut), self.var.resYear)

            # needs to be changed - maybe update all reservoir to spreadsheet
            self.var.resId_restricted = globals.inZero.copy()
            if self.var.includeWastewater:
                # one list of reservoirs per WWTP, the lists can have different lengths
                resIdList = np.unique([res for reservoirs in self.var.wastewater_to_reservoirs.values() for res in reservoirs])
                for rid in resIdList:
                    self.var.resId_restricted += np.where(self.var.waterBodyID == rid, rid, 0)

            # Create a buffer around water bodies as command areas for lakes and reservoirs
            if checkOption('includeWaterDemand'):
                waterBody_UnRestricted = self.var.waterBodyID.copy()

                if self.var.includeWastewater:
                    waterBody_UnRestricted = np.where(np.isin(waterBody_UnRestricted, self.var.resId_restricted), 0, waterBody_UnRestricted)
                rectangular = 1
                if "buffer_waterbodies" in binding:
                    rectangular = int(loadmap('buffer_waterbodies'))

                self.var.waterBodyBuffer = buffer_waterbody(rectangular, decompress(waterBody_UnRestricted))
                if self.var.includeWastewater:
                    self.var.waterBodyBuffer_wwt = buffer_waterbody(rectangular, decompress(self.var.resId_restricted))
                    # index for the area functions with the buffer map (not changed after this)
                    self.var.waterBodyBuffer_wwtIndex = AreaIndex(self.var.waterBodyBuffer_wwt, onlypositive=False)
            else:
                self.var.waterBodyBuffer = self.var.waterBodyID.copy()
            # index for the area functions with the buffer map (not changed after this)
            # all cells are used (class 0 is a class), so the results are the same as npareatotal/npareamaximum
            self.var.waterBodyBufferIndex = AreaIndex(self.var.waterBodyBuffer, onlypositive=False)



    def initial(self):
        """
        Initial part of the lakes and reservoirs: water bodies, lakes (with wetlands), reservoirs (with transfers),
        storage of lakes and reservoirs together for the water balance
        """
        self.initWaterbodies()
        self.lakes.initial()
        self.reservoirs.initial()

        # water balance # put lakes and wetland together
        typLake = np.where((self.var.waterBodyTypC == 1)| (self.var.waterBodyTypC == 6), True, False)

        self.var.lakeResStorageC = np.where(self.var.waterBodyTypC == 0, 0.,
                                            np.where(typLake, self.var.lakeStorageC,
                                                     self.var.reservoirStorageM3C))
        lakeStorageC = np.where(typLake, self.var.lakeStorageC, 0.)
        resStorageC = np.where(typLake == False, self.var.reservoirStorageM3C, 0.)
        self.var.lakeResStorage = globals.inZero.copy()
        self.var.lakeStorage = globals.inZero.copy()
        self.var.resStorage = globals.inZero.copy()
        np.put(self.var.lakeResStorage, self.var.decompress_LR, self.var.lakeResStorageC)
        np.put(self.var.lakeStorage, self.var.decompress_LR, lakeStorageC)
        np.put(self.var.resStorage, self.var.decompress_LR, resStorageC)


    # ------------------ End init ------------------------------------------------------------------------------------
    # ----------------------------------------------------------------------------------------------------------------

    def dynamic(self):
        """
        Dynamic part set lakes and reservoirs for each year
        """
        if checkOption('includeWaterBodies'):

            # wetlands: wet area of the day and new Modified Puls factor (wetlands.py)
            self.wetlands.dynamic()

            # check years
            if dateVar['newStart'] or dateVar['newYear']:
                year = dateVar['currDate'].year

                # water body types:
                # - 5 = Fake reservoir: outflow = inflow, no evaporation -> used for water transfer
                # - 4 = water distribution reservoirs, input = output; only allows input from specified sources,
                #       e.g., inter-basin transfers, wastewater treatment, desalination, etc.
                # - 3 = reservoirs and lakes (used as reservoirs but before the year of construction as lakes)
                # - 2 = reservoirs (regulated discharge)
                # - 1 = lakes (weirFormula)
                # - 0 = non lakes or reservoirs (e.g. wetland)

                if returnBool('useResAndLakes'):
                    if returnBool('dynamicLakesRes'):
                        year = dateVar['currDate'].year
                    else:
                        year = loadmap('fixLakesResYear')

                    self.var.waterBodyTypCTemp = np.where((self.var.resYearC > year) & (self.var.waterBodyTypC == 2), 0,
                                                          self.var.waterBodyTypC)
                    self.var.waterBodyTypCTemp = np.where((self.var.resYearC > year) & (self.var.waterBodyTypC > 3) & (self.var.waterBodyTypC < 6), 0,
                                                          self.var.waterBodyTypCTemp)
                    self.var.waterBodyTypCTemp = np.where((self.var.resYearC > year) & (self.var.waterBodyTypC == 3), 1,
                                                          self.var.waterBodyTypCTemp)
                    # we also need the uncompressed version to compute leakage
                    if self.var.modflow or self.var.includeType4:
                        self.var.waterBodyTypTemp = np.where((self.var.resYear > year) & (self.var.waterBodyTyp == 2),
                                                             0, self.var.waterBodyTyp)
                        self.var.waterBodyTypTemp = np.where((self.var.resYear > year) & (self.var.waterBodyTyp > 3) & (self.var.waterBodyTyp < 6),0,
                                                             self.var.waterBodyTypTemp)
                        self.var.waterBodyTypTemp = np.where((self.var.resYear > year) & (self.var.waterBodyTyp == 3),
                                                             1, self.var.waterBodyTypTemp)
                else:
                    self.var.waterBodyTypCTemp = np.where(self.var.waterBodyTypC == 2, 0, self.var.waterBodyTypC)
                    self.var.waterBodyTypCTemp = np.where((self.var.waterBodyTypC > 3) & (self.var.waterBodyTypC < 6), 0, self.var.waterBodyTypCTemp)
                    self.var.waterBodyTypCTemp = np.where(self.var.waterBodyTypC == 3, 1, self.var.waterBodyTypCTemp)

                    if self.var.modflow or self.var.includeType4:
                        self.var.waterBodyTypTemp = np.where(self.var.waterBodyTyp == 2, 0, self.var.waterBodyTyp)
                        self.var.waterBodyTypTemp = np.where((self.var.waterBodyTyp > 3) & (self.var.waterBodyTyp < 6), 0, self.var.waterBodyTypTemp)
                        self.var.waterBodyTypTemp = np.where(self.var.waterBodyTyp == 3, 1, self.var.waterBodyTypTemp)

            self.var.sumEvapWaterBodyC = 0
            self.var.sumlakeResInflow = 0
            self.var.sumlakeResOutflow = 0

            # daily release ratio of the reservoirs (netCDF or Excel)
            self.reservoirs.dynamic()

    def initInloopIndex(self):
        """
        Index lists for dynamic_inloop, built once at the first routing substep
        (the river network downstruct is set up by the routing, after the lakes)

        * inLakeSrc, inLakePos: cells flowing into a lake cell (network with lakes as pits) and the
          position of that lake cell in waterBodyIndex.cells
        * outletDense: lake (renumbered id) of each outlet, in the order of compress_LR
        * outBelow, outToRiver, outToLake: cell below each outlet and if it is a river cell or a lake cell
        """
        ix = self.var.waterBodyIndex
        n = ix.size
        lake = self.var.waterBodyID > 0

        down = self.var.downstruct_LR
        src = np.nonzero(down < n)[0]
        src = src[lake[down[src]]]
        self.var.inLakeSrc = src
        self.var.inLakePos = np.searchsorted(ix.cells, down[src])

        self.var.outletDense = ix.dense[np.searchsorted(ix.cells, self.var.decompress_LR)]

        below = self.var.downstruct[self.var.decompress_LR]
        valid = below < n
        below = np.where(valid, below, 0)
        self.var.outBelow = below
        self.var.outToRiver = valid & ~lake[below]
        self.var.outToLake = valid & lake[below]

    def dynamic_inloop(self, NoRoutingExecuted):
        """
        Dynamic part to calculate outflow from lakes and reservoirs

        * lakes with modified Puls approach
        * reservoirs with special filling levels

        :param NoRoutingExecuted: actual number of routing substep
        :return: outLdd: outflow in m3 to the network

        Note:
            outflow to adjected lakes and reservoirs is calculated separately
        """
        if not hasattr(self.var, 'outletDense'):
            self.initInloopIndex()

        # -------------------------- Lakes and reservoirs -------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------

        # ----------
        # inflow lakes
        # 1.  dis = upstream1(self_.var.downstruct_LR, self_.var.discharge)   # from river upstream
        # 2.  runoff = npareatotal(self.var_.waterBodyID, self_.var.waterBodyID)  # from cell itself
        # 3.                  # outflow from upstream lakes

        # ----------
        # outflow lakes res -> inflow ldd_LR
        # 1. out = upstream1(self_.var.downstruct, self_.var.outflow)

        # only the lake cells, the cells flowing into them and the outlets are used (index lists from initInloopIndex);
        # the sums are made in the same order as with upstream1 and npareatotal
        ix = self.var.waterBodyIndex

        # collect discharge from above waterbodies (only for the lake cells) and unit convered to [m]
        dis_LR = np.bincount(self.var.inLakePos, weights=self.var.discharge[self.var.inLakeSrc],
                             minlength=ix.cells.size) * self.var.DtSec

        # sum up runoff and discharge on the lake
        # + return flow of lake cells (routing_kinematic.py, 0 without water demand)
        inflowLake = np.bincount(ix.dense, weights=dis_LR + (self.var.runoff_m3 + self.var.returnFlowLakeM3)[ix.cells])

        # only once at the outlet
        # calculate total inflow into lakes and compress it to waterbodie outflow point
        # inflow to lake is discharge from upstream network + runoff directly into lake + outflow from upstream lakes
        # outLake is a number (0) at the start if it is not loaded from an initial file, later a map
        outLakeC = self.var.outLake[self.var.decompress_LR] if np.ndim(self.var.outLake) else self.var.outLake
        inflowC = inflowLake[self.var.outletDense] / self.var.noRoutingSteps + outLakeC

        if self.var.inflow_option:
            # inflow (from module inflow) into a cell of a lake or reservoir goes into the lake or reservoir
            inflow2basin = np.bincount(ix.dense, weights=self.var.inflowDt[ix.cells])
            inflowC = inflowC + inflow2basin[self.var.outletDense]

        # ------------------------------------------------------------

        outflowLakesC = self.lakes.route(inflowC, NoRoutingExecuted)
        outflowResC = self.reservoirs.route(inflowC, NoRoutingExecuted)
        outflow0C = inflowC.copy()     # no retention

        typLake = np.where((self.var.waterBodyTypCTemp == 1) | (self.var.waterBodyTypCTemp == 6), True, False)
        outflowC = np.where(self.var.waterBodyTypCTemp == 0, outflow0C, np.where(typLake, outflowLakesC, outflowResC))

        # waterbalance
        inflowCorrC = np.where(typLake, self.var.lakeIn * self.var.dtRouting, inflowC)
        EvapWaterBodyC = np.where(self.var.waterBodyTypCTemp == 0, 0., np.where(typLake, self.var.lakeEvapWaterBodyC,self.var.resEvapWaterBodyC))

        self.var.lakeResStorageC = np.where(self.var.waterBodyTypCTemp == 0, 0., np.where(typLake, self.var.lakeStorageC,self.var.reservoirStorageM3C))
        lakeStorageC = np.where(typLake, self.var.lakeStorageC, 0.)
        resStorageC = np.where(typLake == False, self.var.reservoirStorageM3C, 0.)

        self.var.sumEvapWaterBodyC += EvapWaterBodyC  # in [m3]
        self.var.sumlakeResInflow += inflowCorrC
        self.var.sumlakeResOutflow += outflowC

        # decompress to normal maskarea size waterbalance
        if self.var.noRoutingSteps == (NoRoutingExecuted + 1):
            np.put(self.var.EvapWaterBodyMOutlet, self.var.decompress_LR, self.var.sumEvapWaterBodyC)
            self.var.EvapWaterBodyMOutlet = self.var.EvapWaterBodyMOutlet / self.var.cellArea
            np.put(self.var.lakeResInflowM, self.var.decompress_LR, self.var.sumlakeResInflow)
            self.var.lakeResInflowM = self.var.lakeResInflowM / self.var.cellArea
            np.put(self.var.lakeResOutflowM, self.var.decompress_LR, self.var.sumlakeResOutflow)
            self.var.lakeResOutflowM = self.var.lakeResOutflowM / self.var.cellArea

            # evaporation of each lake [m3] is distributed to the lake cells by their water area
            # a lake cell has at minimum 5% water
            fracwatermin = np.where(self.var.waterBodyID > 0, np.maximum(self.var.fracVegCover[5], 0.05), 0)
            # water area of each lake cell and of the whole lake [m2]
            wlakearea = fracwatermin * self.var.cellArea
            wlakeareasum = self.var.waterBodyIndex.total(wlakearea)
            # evaporation of the whole lake [m3] in all lake cells
            ebody = self.var.waterBodyIndex.total(self.var.EvapWaterBodyMOutlet * self.var.cellArea)
            # [m3] -> [m] per cell, so that sum(EvapWaterBodyM * cellArea) = ebody
            self.var.EvapWaterBodyM = divideValues(ebody * fracwatermin, wlakeareasum)

            np.put(self.var.lakeResStorage, self.var.decompress_LR, self.var.lakeResStorageC)
            np.put(self.var.lakeStorage, self.var.decompress_LR, lakeStorageC)
            np.put(self.var.resStorage, self.var.decompress_LR, resStorageC)

            # Puts the value of lakeResStorage into all cells covered by the waterbody
            # (only needed once per day: lakeResStorage changes only in this last routing substep)
            self.var.lakeResStorage_filled = self.var.waterBodyIndex.maximum(self.var.lakeResStorage)
            self.var.lakeResStorage_buffer = self.var.waterBodyBufferIndex.maximum(self.var.lakeResStorage)

            # water transfer: daily sums to the full maps, sums start again at 0
            if self.var.reservoir_transfers_option:
                self.transfers.daily_output()


        # ------------------------------------------------------------

        np.put(self.var.reslakeoutflow, self.var.decompress_LR, outflowC)
        lakeResOutflowDis = ix.total(self.var.reslakeoutflow) / (
                    self.var.DtSec / self.var.noRoutingSteps)
        # shift outflow 1 cell downstream: only the outlets have an outflow (same sums as upstream1)
        outflowOut = self.var.reslakeoutflow[self.var.decompress_LR]
        # everything with is not going to another lake is output to river network
        river = self.var.outToRiver
        outLdd = np.bincount(self.var.outBelow[river], weights=outflowOut[river], minlength=ix.size)

        # everything what is not going to the network is going to another lake
        tolake = self.var.outToLake
        outLake1 = np.bincount(self.var.outBelow[tolake], weights=outflowOut[tolake], minlength=ix.size)
        # sum up all inflow from other lakes
        outLakein = ix.total(outLake1)
        # use only the value of the outflow point
        self.var.outLake = np.zeros(ix.size)
        self.var.outLake[self.var.decompress_LR] = outLakein[self.var.decompress_LR]

        return outLdd, lakeResOutflowDis

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
