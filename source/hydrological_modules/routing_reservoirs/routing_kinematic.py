# -------------------------------------------------------------------------
# Name:        Routing module - Kinematic wave
# Purpose:
#
# Author:      PB
#
# Created:     17/01/2017
# Copyright:   (c) PB 2017
# -------------------------------------------------------------------------

from management_modules.data_handling import *
from hydrological_modules.routing_reservoirs.routing_sub import *
from hydrological_modules.lakes_reservoirs import *

class routing_kinematic(object):

    """
    # ************************************************************
    # ***** ROUTING      *****************************************
    # ************************************************************
    """

    def __init__(self, routing_kinematic_variable):
        self.var = routing_kinematic_variable
        self.lakes_reservoirs_module = lakes_reservoirs(self.var)


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the routing module
        """

        ldd = loadmap('Ldd')
        self.var.lddCompress, dirshort, self.var.dirUp, self.var.dirupLen, self.var.dirupID, self.var.downstruct, self.var.catchment, self.var.dirDown, self.var.lendirDown = defLdd2(ldd)

        #self.var.ups = upstreamArea(dirDown, dirshort, self.var.cellArea)
        self.var.UpArea1 = upstreamArea(self.var.dirDown, dirshort, globals.inZero + 1.0)
        self.var.UpArea = upstreamArea(self.var.dirDown, dirshort, self.var.cellArea)
        d1 =downstream1(self.var.dirUp, self.var.UpArea1)
        up1 = upstream1( self.var.downstruct,self.var.UpArea1)

        ii =1

        #lib2.kinematic(Qold, q, dd, dl, di, Qnew, alpha, 0.6, deltaT, deltaX, len(dirDown))
        #lib2.kinematic(Qold, q, self.var.dirDown, self.var.dirupLen, self.var.dirupID, Qnew, alpha, 0.6, deltaT, deltaX, self.var.lendirDown)

        #---------------------------------------------------------------
        #Calibration
        # mannings roughness factor 0.1 - 10.0
        manningsFactor = loadmap('manningsN')


        # number of substep per day
        self.var.noRoutingSteps = int(loadmap('NoRoutingSteps'))
        # kinematic wave parameter: 0.6 is for broad sheet flow
        self.var.beta = loadmap('chanBeta')
        # Channel Manning's n
        self.var.chanMan = loadmap('chanMan') * manningsFactor
        # Channel gradient (fraction, dy/dx)
        self.var.chanGrad = np.maximum(loadmap('chanGrad'), loadmap('chanGradMin'))
        # Channel length [meters]
        self.var.chanLength = loadmap('chanLength')
        # Channel bottom width [meters]
        self.var.chanWidth = loadmap('chanWidth')
        # Bankfull channel depth [meters]
        self.var.chanDepth = loadmap('chanDepth')



        #-----------------------------------------------
        # Inverse of beta for kinematic wave
        self.var.invbeta = 1 / self.var.beta
        # Inverse of channel length [1/m]
        self.var.invchanLength = 1 / self.var.chanLength

        # Corresponding sub-timestep (seconds)
        self.var.dtRouting = self.var.DtSec / self.var.noRoutingSteps
        self.var.invdtRouting = 1 / self.var.dtRouting

        # -----------------------------------------------
        # ***** CHANNEL GEOMETRY  ************************************

        # Area (sq m) of bank full discharge cross section [m2]
        self.var.totalCrossSectionAreaBankFull = self.var.chanDepth * self.var.chanWidth
        # Cross-sectional area at half bankfull [m2]
        # This can be used to initialise channel flow (see below)
        #TotalCrossSectionAreaHalfBankFull = 0.5 * self.var.TotalCrossSectionAreaBankFull
        # TotalCrossSectionAreaInitValue = loadmap('TotalCrossSectionAreaInitValue')
        self.var.totalCrossSectionArea =  0.5 * self.var.totalCrossSectionAreaBankFull
        # Total cross-sectional area [m2]: if initial value in binding equals -9999 the value at half bankfull is used,

        # -----------------------------------------------
        # ***** CHANNEL ALPHA (KIN. WAVE)*****************************
        # ************************************************************
        # Following calculations are needed to calculate Alpha parameter in kinematic
        # wave. Alpha currently fixed at half of bankful depth

        # Reference water depth for calculation of Alpha: half of bankfull
        #chanDepthAlpha = 0.5 * self.var.chanDepth
        # Channel wetted perimeter [m]
        self.var.chanWettedPerimeterAlpha = self.var.chanWidth + 2 * 0.5 * self.var.chanDepth

        # ChannelAlpha for kinematic wave
        alpTermChan = (self.var.chanMan / (np.sqrt(self.var.chanGrad))) ** self.var.beta
        self.var.alpPower = self.var.beta / 1.5
        self.var.channelAlpha = alpTermChan * (self.var.chanWettedPerimeterAlpha ** self.var.alpPower) *2.5
        self.var.invchannelAlpha = 1. / self.var.channelAlpha

        # -----------------------------------------------
        # ***** CHANNEL INITIAL DISCHARGE ****************************

        # channel water volume [m3]
        # Initialise water volume in kinematic wave channels [m3]
        self.var.channelStorage = self.var.totalCrossSectionArea * self.var.chanLength * 0.5

        # Initialise discharge at kinematic wave pixels (note that InvBeta is
        # simply 1/beta, computational efficiency!)
        #self.var.chanQKin = np.where(self.var.channelAlpha > 0, (self.var.totalCrossSectionArea / self.var.channelAlpha) ** self.var.invbeta, 0.)
        self.var.chanQKin = (self.var.channelStorage * self.var.invchanLength * self.var.invchannelAlpha) ** (self.var.invbeta)

        self.var.riverbedExchange = globals.inZero.copy()
        self.var.discharge = self.var.chanQKin.copy()

        ii =1

        #self.var.channelAlphaPcr = decompress(self.var.channelAlpha)
        #self.var.chanLengthPcr = decompress(self.var.chanLength)

        self.var.timestepsToAvgDischarge = globals.inZero.copy()







# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the routing module
        """
        #   if option['PCRaster']: from pcraster.framework import *

# ---------------------------------------------------------------------------------



        # if routing is not needed return
        if not(option['includeRouting']):
            return

        if option['calcWaterBalance']:
            self.var.prechannelStorage = self.var.channelStorage.copy()


        Qnew = globals.inZero.copy()

        # ------------------------------------------------------
        # ***** SIDEFLOW **************************************

        runoffM3 = self.var.runoff * self.var.cellArea / self.var.noRoutingSteps


    #    sideflowChanM3 -= self.var.sum_actSurfaceWaterAbstract * self.var.cellArea
        # return flow from (m) non irrigation water demand
    #    self.var.nonIrrReturnFlow = self.var.nonIrrReturnFlowFraction * self.var.nonIrrGrossDemand
    #    sideflowChanM3 +=  self.var.nonIrrReturnFlow * self.var.cellArea
        #sideflowChan = sideflowChanM3 * self.var.invchanLength * self.var.invdtRouting

        # ************************************************************
        # ***** KINEMATIC WAVE                        ****************
        # ************************************************************

        #sideflowChan = sideflowChan / self.var.noRoutingSteps
        for subrouting in xrange(self.var.noRoutingSteps):

            sideflowChanM3 = runoffM3.copy()
            if option['includeWaterBodies']:
                sideflowChanM3 += self.lakes_reservoirs_module.dynamic_inloop(subrouting)

            #sideflowChan = sideflowChanM3 * self.var.invchanLength * self.var.InvDtSec
            sideflowChan = sideflowChanM3 * self.var.invchanLength * 1/ self.var.dtRouting

            if option['includeWaterBodies']:
               lib2.kinematic(self.var.discharge, sideflowChan, self.var.dirDown_LR, self.var.dirupLen_LR, self.var.dirupID_LR, Qnew, self.var.channelAlpha, 0.6, self.var.dtRouting, self.var.chanLength, self.var.lendirDown_LR)
            else:
               lib2.kinematic(self.var.discharge, sideflowChan, self.var.dirDown, self.var.dirupLen, self.var.dirupID, Qnew, self.var.channelAlpha, 0.6, self.var.dtRouting, self.var.chanLength, self.var.lendirDown)
            self.var.discharge = Qnew.copy()



        # -- end substeping ---------------------

        self.var.channelStorage = self.var.channelAlpha * self.var.chanLength * Qnew ** 0.6
        ii =11

        #if option['PCRaster']: report(decompress(self.var.discharge), "C:\work\output2/q1.map")



        """
        chanM3KinPcr = decompress(self.var.channelStorage)
        for subrouting in xrange(self.var.noRoutingSteps):
            chanM3KinPcr = kinwavestate(self.var.Ldd1, chanM3KinPcr, decompress(sideflowChan), self.var.channelAlphaPcr, self.var.beta, 1, self.var.dtRouting, self.var.chanLengthPcr)

        self.var.channelStorage = compressArray(chanM3KinPcr)

        # side flow consists of runoff (incl. groundwater), inflow from reservoirs (optional)
        # and external inflow hydrographs (optional)
        # ChanQKin in [cu m / s]
        self.var.chanQKin = (self.var.channelStorage * self.var.invchanLength * self.var.invchannelAlpha) ** (self.var.invbeta)
        self.var.discharge = np.maximum(self.var.chanQKin, 0)
        """


        """
         # update channelStorage (unit: m3) after runoff
         self.var.channelStorage += self.var.runoff * self.var.cellArea

         # update channelStorage (unit: m3) after actSurfaceWaterAbstraction
         self.var.channelStorage -= self.var.sum_actSurfaceWaterAbstract * self.var.cellArea

         # return flow from (m) non irrigation water demand
         self.var.nonIrrReturnFlow = self.var.nonIrrReturnFlowFraction * self.var.nonIrrGrossDemand
         self.var.channelStorage  =  self.var.channelStorage + self.var.nonIrrReturnFlow * self.var.cellArea


         # Runoff (surface runoff + flow out of Upper and Lower Zone), outflow from
         # reservoirs and lakes and inflow from external hydrographs are added to the channel
         # system (here in [cu m])
         sideflowChanM3 = self.var.ToChanM3RunoffDt.copy()


         if option['openwaterevapo']:
             sideflowChanM3 -= self.var.EvaAddM3Dt
         if option['wateruse']:
             sideflowChanM3 -= self.var.WUseAddM3Dt
         if option['inflow']:
             sideflowChanM3 += self.var.QInDt
         if option['TransLoss']:
             sideflowChanM3 -= self.var.TransLossM3Dt

         # SideflowChan=if(IsChannelKinematic, SideflowChanM3*InvChanLength*InvDtRouting);
         # Sideflow expressed in [cu m /s / m channel length]
         sideflowChan = sideflowChanM3 * self.var.invChanLength * self.var.invDtRouting
         """


        """
        chanM3KinPcr = decompress(self.var.channelStorage)
        chanM3KinPcr = kinwavestate(self.var.Ldd1, chanM3KinPcr, decompress(sideflowChan), self.var.channelAlphaPcr, self.var.beta, 1, self.var.dtRouting, self.var.chanLengthPcr)
        #ChanM3KinPcr = kinwavestate(self.var.LddKinematic, ChanM3KinPcr, decompress(SideflowChan), self.var.ChannelAlpha, self.var.Beta, 1, self.var.DtRouting, self.var.ChanLength)
        self.var.channelStorage = compressArray(chanM3KinPcr)


        # side flow consists of runoff (incl. groundwater), inflow from reservoirs (optional)
        # and external inflow hydrographs (optional)
        # ChanQKin in [cu m / s]
        self.var.chanQKin = (self.var.channelStorage * self.var.invchanLength * self.var.invchannelAlpha) ** (self.var.invbeta)

        # self.var.ChanQKin=pc raster.max(self.var.ChanQKin,0)
        self.var.discharge = np.maximum(self.var.chanQKin, 0)
        # at single kin. ChanQ is the same
        #self.var.sumDisDay += self.var.ChanQ
        # Total channel storage [cu m], equal to ChanM3Kin
        #  self.var.ChanQ = maxpcr(self.var.ChanQKin, null)
        """


        """
        a = readmap("C:\work\output/q_pcr")
        b = nominal(a*100)
        c = ifthenelse(b == 105779, scalar(9999), scalar(0))
        report(c,"C:\work\output/t3.map")
        d = compressArray(c)
        np.where(d == 9999)   #23765
        e = pcr2numpy(c, 0).astype(np.float64)
        np.where(e > 9000)   # 75, 371  -> 76, 372
        """



