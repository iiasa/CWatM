from cwatm.management_modules import globals
from cwatm.management_modules.data_handling import returnBool, binding, readnetcdf2

class waterdemand_environmental_flow:
    def __init__(self, model):
        self.var = model.var
        self.model = model

    def initial(self):
        if "use_environflow" in binding:
            self.var.use_environflow = returnBool('use_environflow')
        else:
            self.var.use_environflow = False
        if self.var.use_environflow:
            self.var.cut_ef_map = returnBool('cut_ef_map')
        else:
            self.var.cut_ef_map = False

    def dynamic(self):
        if self.var.use_environflow:
            if globals.dateVar['newStart'] or globals.dateVar['newMonth']:
                # envflow in [m3/s] -> [m]
                self.var.envFlowm3s = readnetcdf2('EnvironmentalFlowFile', globals.dateVar['currDate'], "month", cut=self.var.cut_ef_map) # in [m3/s]
                self.var.envFlow = self.var.M3toM  * self.var.channelAlpha * self.var.chanLength * self.var.envFlowm3s ** 0.6 # in [m]
        else:
            self.var.envFlow = 0.0