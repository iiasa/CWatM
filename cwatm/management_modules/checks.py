# -------------------------------------------------------------------------
# Name:        checks if inputs are valid
# Purpose:
#
# Author:      burekpe
#
# Created:     16/05/2016
# Copyright:   (c) burekpe 2016
# -------------------------------------------------------------------------


from .globals import *

def counted(fn):
    """
    count number of times a subroutine is called

    :param fn:
    :return: number of times the subroutine is called
    """
    def wrapper(*args, **kwargs):
        wrapper.called += 1
        return fn(*args, **kwargs)
    wrapper.called = 0
    wrapper.__name__ = fn.__name__
    return wrapper


@counted
def checkmap(name, value, map, flagmap, flagcompress, mapC):
    """
    check maps if the fit to the mask map

    :param name: name of the variable in settingsfile
    :param value: filename of the variable
    :param map: data (either a number or a 1D array)
    :param flagmap: indicates a 1D array or a number
    :param flagcompress: is there a compressed map available
    :param mapC: compressed map
    :return: -

    Todo:
        still to improve, this is work in progress!
    """

    def input2str(inp):
        if isinstance(inp, str):
            return(inp)
        elif isinstance(inp, int):
            return f'{inp}'
        else:
            if inp < 100000:
                return f'{inp:.2f}'
            else:
                return f'{inp:.2E}'

    # ----------------------------------
    s = [name]
    s.append(value[-37:])

    if flagmap:

        try:
            mapshape = input2str(map.shape[0]) + "x" + input2str(map.shape[1])
        except:
            mapshape = input2str(map.shape[0])

        if not(flagcompress):
            mapshape = input2str(map.shape[0]) + "x" + input2str(map.shape[1])
            numbernonmv = np.count_nonzero(~np.isnan(map))  # count nonmissing values
            numbermv = np.count_nonzero(np.isnan(map))  # count missing value (np.nan)
            #numbernan = "-"
            #numberzero = "-"
            numbernan = input2str(np.count_nonzero(np.isnan(map)))
            numberzero = input2str( map.shape[0] * map.shape[1] -  np.count_nonzero(map))
            numbernonzero = input2str(np.count_nonzero(map))

            compressF = "False"
            minmap = map[~np.isnan(map)].min()
            meanmap = map[~np.isnan(map)].mean()
            maxmap = map[~np.isnan(map)].max()

        else:
            numbernonmv = np.count_nonzero(~np.isnan(mapC))  # count nonmissing values
            numbermv = np.count_nonzero(np.isnan(mapC))  # count missing value (np.nan)

            compressF ="True"
            numbernan = input2str(np.count_nonzero(np.isnan(mapC)))
            numberzero = input2str(mapC.shape[0] - np.count_nonzero(mapC))
            numbernonzero = input2str(np.count_nonzero(mapC))

            minmap = mapC[~np.isnan(mapC)].min()
            meanmap = mapC[~np.isnan(mapC)].mean()
            maxmap = mapC[~np.isnan(mapC)].max()

        s.append(input2str(numbernonmv))
        s.append(input2str(numbermv))
        s.append(input2str(mapshape))
        s.append(compressF)
        s.append(numbernan)
        s.append(numberzero)
        s.append(numbernonzero)
        s.append(input2str(minmap))
        s.append(input2str(meanmap))
        s.append(input2str(maxmap))

    else:
        s.append("-")
        s.append("-")
        s.append("-")
        s.append("-")
        s.append("-")  # CompressF
        s.append("")
        s.append(input2str(float(map)))
        s.append("")


    t = ["<30","<40",">11",">11",">11",">11",">11",">11",">11",">11",">11", ">11",">11"]
    h = ["Name","File/Value","nonMV","MV", "lon-lat","Compress","MV-comp","Zero-comp","NonZero","min","mean","max","x1","x2","x3"]
    if checkmap.called == 1:
        print("---------------------------------------------")
        print("nonMV:     non missing value in 2D map")
        print("MV:        missing value in 2D map")
        print("lon-lat:   longitude x latitude of 2D map")
        print("CompressV: 2D is compressed to 1D?")
        print("MV-comp:   missing value in 1D")
        print("Zero-comp: Number of 0 in 1D")
        print("NonZero:   Number of non 0 in 1D")
        print("min:       minimum in 1D (or 2D)")
        print("mean:      mean in 1D (or 2D)")
        print("max:       maximum in 1D (or 2D)")
        print("---------------------------------------------")

        for i in range(len(s)):
            if i<(len(s)-1):
               print(f'{h[i]:{t[i]}}',end = '')
            else:
               print(f'{h[i]:{t[i]}}')

    for i in range(len(s)):
        if i < (len(s) - 1):
            print(f'{s[i]:{t[i]}}',end = '')
        else:
            print(f'{s[i]:{t[i]}}')



    #print("%-30s%-40s%11i%11i%11i%11i%14.2f%14.2f%14.2f" %(s[0],s[1][-39:],s[2],s[3],s[8],s[7],s[4],s[5],s[6]))
    #print("%-30s%-40s%11s%11s%11s%11s%14s%14s%14s" % (s[0], s[1][-39:], s[2], s[3], s[8], s[7], s[4], s[5], s[6]))

    return



