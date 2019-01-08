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
        wrapper.called+= 1
        return fn(*args, **kwargs)
    wrapper.called= 0
    wrapper.__name__= fn.__name__
    return wrapper

@counted
def checkmap(name, value, map, flagmap, find):
    """
    check maps if the fit to the mask map

    :param name: name of the variable in settingsfile
    :param value: filename of the variable
    :param map: data (either a number or a 1D array)
    :param flagmap: indicates a 1D array or a number
    :param find: at the moment a dummy
    :return: -

    Todo:
        still to improve, this is work in progress!
    """

    s = [name, value]
    if flagmap:
        numbernonmv = np.count_nonzero(~np.isnan(map))
        numbermv = np.count_nonzero(np.isnan(map))
        minmap = map[~np.isnan(map)].min()
        meanmap = map[~np.isnan(map)].mean()
        maxmap = map[~np.isnan(map)].max()


        s.append(numbernonmv)
        s.append(numbermv)
        s.append(minmap)
        s.append(meanmap)
        s.append(maxmap)
        s.append(find)
        s.append(np.count_nonzero(map))
    else:
        s.append(0)
        s.append(0)
        s.append(float(map))
        s.append(float(map))
        s.append(float(map))
        s.append(0)
        s.append(0)
        """
        amap = scalar(defined(MMaskMap))
        try:
            smap = scalar(defined(map))
        except:
            msg = "Map: " + name + " in " + value + " does not fit"
            if name == "LZAvInflowMap":
                msg +="\nMaybe run initial run first"
            raise CWATMError(msg)

        mvmap = maptotal(smap)
        mv = cellvalue(mvmap, 1, 1)[0]
        s.append(mv)

        less = maptotal(ifthenelse(defined(MMaskMap), amap - smap, scalar(0)))
        s.append(cellvalue(less, 1, 1)[0])
        less = mapminimum(scalar(map))
        s.append(cellvalue(less, 1, 1)[0])
        less = maptotal(scalar(map))
        if mv > 0:
            s.append(cellvalue(less, 1, 1)[0] / mv)
        else:
            s.append('0')
        less = mapmaximum(scalar(map))
        s.append(cellvalue(less, 1, 1)[0])
        if find > 0:
            if find == 2:
                s.append('last_Map_used')
            else:
                s.append('')
        """

    if checkmap.called == 1:
        print("%-30s%-40s%11s%11s%11s%11s%14s%14s%14s" %("Name","File/Value","nonMV","MV", "non0","Compress","min","mean","max"))
    print("%-30s%-40s%11i%11i%11i%11i%14.2f%14.2f%14.2f" %(s[0],s[1][-39:],s[2],s[3],s[8],s[7],s[4],s[5],s[6]))
    return



