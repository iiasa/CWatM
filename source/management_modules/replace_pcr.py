# -------------------------------------------------------------------------
# Name:        replace_pcr
# Purpose:     Replace pcraster command with numpy array commands
#
# Author:      PB
#
# Created:     2/08/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

import numpy as np


  
# ------------------------ all this area commands
#              np.take(np.bincount(AreaID,weights=Values),AreaID)     #     areasum
#                (np.bincount(b, a) / np.bincount(b))[b]              # areaaverage
#              np.take(np.bincount(AreaID,weights=Values),AreaID)     # areaaverage
#                valueMax = np.zeros(AreaID.max() + 1)
#                np.maximum.at(valueMax, AreaID, Values)
#                max = np.take(valueMax, AreaID)             # areamax


def npareatotal(values, areaclass):
    return np.take(np.bincount(areaclass,weights=values),areaclass)


def npareaaverage(values, areaclass):
    return np.take(np.bincount(areaclass,weights=values)/ np.bincount(areaclass) ,areaclass)


def npareamaximum(values, areaclass):
    valueMax = np.zeros(areaclass.max() + 1)
    np.maximum.at(valueMax, areaclass, values)
    return np.take(valueMax ,areaclass)


def npareamajority(values, areaclass):
    uni,ind = np.unique(areaclass,return_inverse=True)
    return np.array([np.argmax(np.bincount(values[areaclass == group])) for group in uni])[ind]












"""
def wrapper(func, *args, **kwargs):
     def wrapped():
         return func(*args, **kwargs)
     return wrapped

def f1(id,v):
    uni,ind = np.unique(id,return_inverse=True)
    v5 = np.array([np.argmax(np.bincount(v[id == group])) for group in uni])
    return v5[ind]

def f2(id,v):
    v1 = v.copy()
    for group in uni:
        v1[id == group] = np.argmax(np.bincount(v[id == group]))
    return v1

def f3(areaclass, values):
    res = np.take(np.bincount(areaclass,weights=values)/ np.bincount(areaclass) ,areaclass)
    return res
id = np.array([1,1,1,2,1,3,2,2,3,3])
v =  np.array([5,5,6,4,3,2,6,6,1,2])
#
uni = np.unique(id)
sums = []

v1 = v.copy()
for group in uni:
    v1[id == group] = np.argmax(np.bincount(v[id == group]))
print id
print v
print v1
print "------"

uni,ind = np.unique(id,return_inverse=True)
v3 = np.array([np.argmax(np.bincount(v[id == group])) for group in uni])
print v3[ind]

print "++++++++++++++"
id = np.random.randint(100, size=10000)+1
v = np.random.randint(10000, size=10000)

print "loop"
wrapped = wrapper(f2, id,v)
print wrapped()
print timeit.timeit(wrapped, number = 100)

print "enum"
wrapped = wrapper(f1, id,v)

print wrapped()
print timeit.timeit(wrapped, number = 100)



print "avg"
wrapped = wrapper(f3, id,v)
print wrapped()
print timeit.timeit(wrapped, number = 100)


"""