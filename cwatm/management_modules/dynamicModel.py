# initial and dynamic model-> idea taken from PC_Raster

class DynamicModel:
    i = 1

# ----------------------------------------

class ModelFrame:
    """
    Frame of the dynamic hydrological model

    lastTimeStep:  Last time step to run
    firstTimestep: Starting time step of the model
    """

    def __init__(self, model, lastTimeStep=1, firstTimestep=1):
        """
        sets first and last time step into the model

        :param lastTimeStep: last timestep
        :param firstTimeStep: first timestep
        :return: -
        """

        self._model = model
        self._model.lastStep = lastTimeStep
        self._model.firstStep = firstTimestep

    def step(self):
        self._model.currentStep = self.currentStep
        self._model.dynamic()
        self.currentStep += 1    

    def initialize_run(self):
        # inside cwatm_dynamic it will interate
        self.currentStep = self._model.firstStep

    def run(self):
        """  Run the dynamic part of the model

        :return: -
        """
        self.initialize_run()
        while self.currentStep <= self._model.lastStep:
            self.step()




