# initial and dynamic model-> idea taken from PC_Raster

class DynamicModel:
  i = 1

# ----------------------------------------

class ModelFrame:
  """
  Frame of the dynamic hydrological model

  :param userModel: Mask map
  :param lastTimeStep:  Last time step to run
  :param firstTimestep: Starting time step of the model
  :return:
  """

  def __init__(self, model, lastTimeStep=1, firstTimestep=1):
    self._model = model
    self._model.lastStep = lastTimeStep
    self._model.firstStep = firstTimestep

  def run(self):
    """  Run the dynamic part of the model """
    step = self._model.firstStep
    while step <= self._model.lastStep:
      self._model.currentStep = step
      self._model.dynamic()
      step += 1




