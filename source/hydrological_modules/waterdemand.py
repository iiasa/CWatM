# -------------------------------------------------------------------------
# Name:        Waterdemand module
# Purpose:
#
# Author:      PB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class waterdemand(object):

    """
    # ************************************************************
    # ***** SOIL *****************************************
    # ************************************************************
    """

    def __init__(self, waterdemand_variable):
        self.var = waterdemand_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the groundwater module
        """
        if option['includeWaterDemandDomInd']:
           #self.var.recessionCoeff = loadmap('recessionCoeff')

           i = 1
           # TODO : add  zones at which water allocation (surface and groundwater allocation) is determined
           #  landSurface.py lines 317ff



# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the soil module
        """

        # get NON-Irrigation GROSS water demand and its return flow fraction
        # obtainNonIrrWaterDemand landsurface 487

        # domestic water demand
        self.var.domesticGrossDemand = readnetcdf2(binding['domesticWaterDemandFile'], self.var.CalendarDate, "monthly", value="domesticGrossDemand")
        self.var.domesticNettoDemand = readnetcdf2(binding['domesticWaterDemandFile'], self.var.CalendarDate, "monthly", value="domesticNettoDemand")
        # industry water demand
        self.var.industryGrossDemand = readnetcdf2(binding['industryWaterDemandFile'], self.var.CalendarDate, "yearly", value="industryGrossDemand")
        self.var.industryNettoDemand = readnetcdf2(binding['industryWaterDemandFile'], self.var.CalendarDate, "yearly", value="industryNettoDemand")

        # avoid small values (less than 1 m3):
        self.var.domesticGrossDemand = np.where(self.var.domesticGrossDemand > self.var.InvCellArea, self.var.domesticGrossDemand, 0.0)
        self.var.domesticNettoDemand = np.where(self.var.domesticNettoDemand > self.var.InvCellArea, self.var.domesticNettoDemand, 0.0)
        self.var.industryGrossDemand = np.where(self.var.industryGrossDemand > self.var.InvCellArea, self.var.industryGrossDemand, 0.0)
        self.var.industryNettoDemand = np.where(self.var.industryNettoDemand > self.var.InvCellArea, self.var.industryNettoDemand, 0.0)

        # total (potential) non irrigation water demand
        self.var.potentialNonIrrGrossWaterDemand = self.var.domesticGrossDemand + self.var.industryGrossDemand
        self.var.potentialNonIrrNettoWaterDemand = np.minimum(self.var.potentialNonIrrGrossWaterDemand, self.var.domesticNettoDemand + self.var.industryNettoDemand)

        # fraction of return flow from domestic and industrial water demand
        self.var.nonIrrReturnFlowFraction = getValDivZero((self.var.potentialNonIrrGrossWaterDemand - self.var.potentialNonIrrNettoWaterDemand),\
                                     (self.var.potentialNonIrrGrossWaterDemand), 1E-39)

        # ---------------------------------------------------------------------------------------
        # partitioningGroundSurfaceAbstraction  - landsurface 615
        # partitioning abstraction sources: groundwater and surface water
        # Inge's principle: partitioning based on local average baseflow (m3/s) and upstream average discharge (m3/s)

        # estimates of fractions of groundwater and surface water abstractions
        """
        averageBaseflowInput = routing.avgBaseflow
        averageUpstreamInput = pcr.upstream(routing.lddMap, routing.avgDischarge)

        if self.usingAllocSegments:
            averageBaseflowInput = pcr.max(0.0, pcr.ifthen(self.landmask, averageBaseflowInput))
            averageUpstreamInput = pcr.max(0.0, pcr.ifthen(self.landmask, averageUpstreamInput))
            averageBaseflowInput = pcr.cover(pcr.areaaverage(pcr.cover(averageBaseflowInput, 0.0), self.allocSegments), 0.0)
            averageUpstreamInput = pcr.cover(pcr.areamaximum(pcr.cover(averageUpstreamInput, 0.0), self.allocSegments), 0.0)

        else:
             print("WARNING! Water demand can only be satisfied by local source.")

        swAbstractionFraction = pcr.max(0.0, pcr.min(1.0,averageUpstreamInput / pcr.max(1e-20,averageUpstreamInput + averageBaseflowInput)))
        swAbstractionFraction = pcr.cover(swAbstractionFraction, 0.0)
        swAbstractionFraction = pcr.roundup(swAbstractionFraction * 100.) / 100.
        swAbstractionFraction = pcr.max(0.0, swAbstractionFraction)
        swAbstractionFraction = pcr.min(1.0, swAbstractionFraction)

        gwAbstractionFraction = 1.0 - swAbstractionFraction
        """
        self.var.gwAbstractionFraction = 0.5
