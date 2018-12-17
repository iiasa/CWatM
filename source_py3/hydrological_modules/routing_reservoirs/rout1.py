#-------------------------------------------------------------------------------
# Name:        pc rasterreplace
# Purpose:
#
# Author:      burekpe
#
# Created:     05/01/2015
# Copyright:   (c) burekpe 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------

from .routing_sub import *
from globals import *
import time
import pickle
import pcraster



def loadObject(name):
  filehandler1 = open(name, 'r')
  var = pickle.load(filehandler1)
  filehandler1.close()
  return(np.array(var))

def dumpObject(var,name):
    file_object1 = open(name, 'w')
    pickle.dump(var.tolist(), file_object1)
    file_object1.close()



def main():


#    lddname="lddDiep.map"
#    lddname="l3.map"
    lddname="ldd2.map"

    pcraster.setclone(lddname)
    ldd=pcraster.readmap(lddname)
    # change to numpy array
    lddnp = pcraster.pcr2numpy(ldd, np.nan).astype(np.int64)


#    file_object1 = open("lddnp.pck", 'w')
#    pickle.dump(lddnp, file_object1)
#    file_object1.close()
     #lddnp=np.array(loadObject("lddnp.pck"), dtype=np.int64)


#----------------

    lddOrder,dir, catchment = defLdd(lddnp)
    print("define")
    lddcomp, lddOrder, dirshort = lddrepair(lddnp,lddOrder,dir)
    print("repair")

# -----------------

    dirUp,dirupLen,dirupID = dirUpstream(dirshort)
    dirDownstream(dirUp,lddcomp,catchment)
    print("catchment")

    ups = upstreamArea(dirDown,dirshort)
    print("upstreamarea")


    downstr1 = downstream(dirUp,ups)
    print("downstream")

# -----------------
# ----------------------------------  Kinematic
    alpha, deltaX, deltaT = 5.0, 5000.0, 86400.0

    Qnew = np.array(np.empty(maskattr["compshape"]),dtype=np.double)
    Qold = np.array(np.empty(maskattr["compshape"]),dtype=np.double)
    Qold.fill(2.0)
    Mold = Qold**0.6 * alpha * deltaX

    q = np.array(np.empty(maskattr["compshape"]),dtype=np.double)
    q.fill(0.0)

    Qnew = np.array(np.empty(maskattr["compshape"]),dtype=np.double)
    Qnew.fill(0.0)

    dd=np.array(dirDown).astype(np.int64)
    dl=np.array(dirupLen).astype(np.int64)
    di=np.array(dirupID).astype(np.int64)
    print("--",Qold[0])
    lib2.kinematic(Qold,q,dd,dl,di,Qnew,alpha,0.6,deltaT,deltaX,len(dirDown))

    print("kinematic")
    for i in range(5):
	   print(Qnew[i], end=' ')
# ----------------------------------------------------------------------
# ----------------Output -----------------------------------------------

    lddmap = Decompress(lddcomp,maskattr["mask"],maskattr["emptymap"])
    lddmap[maskattr["mask"]]=-9999
    map = pcraster.numpy2pcr(pcraster.Ldd, lddmap, -9999)
    pcraster.report(map,"z_ldd.map")
    #dumpObject(lddmap,"z_ldd.pck")


    map1 = Decompress(catchment,maskattr["mask"],maskattr["emptymap"])
    map1[maskattr["mask"]]=-9999
    map = pcraster.numpy2pcr(pcraster.Nominal, map1, -9999)
    pcraster.report(map,"catch.map")
    # dumpObject(map1,"catch.pck")

    upsmap = Decompress(ups,maskattr["mask"],maskattr["emptymap"])
    upsmap[upsmap.mask]=-9999
    map = pcraster.numpy2pcr(pcraster.Scalar, upsmap, -9999)
    pcraster.report(map,"z_ups.map")
   # dumpObject(upsmap,"z_ups.pck")


    QnewDe = Decompress(Qnew,maskattr["mask"],maskattr["emptymap"])
    QnewDe[QnewDe.mask]=-9999
    QnewR = pcraster.numpy2pcr(pcraster.Scalar, QnewDe, -9999)
    pcraster.report(QnewR, "Qnew3.map")
 #   dumpObject(QnewDe,"qnew3.pck")
# ----------------------------------------------------------------------
# ----------------Output End--------------------------------------------

if __name__ == '__main__':
    main()
