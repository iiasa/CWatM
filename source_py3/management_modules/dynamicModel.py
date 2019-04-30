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

  def run(self):
    """  Run the dynamic part of the model

    :return: -
    """

    step = self._model.firstStep

    # if using the steady state model modflow the dynmaic part should run only 1 time
    # inside cwatm_dynamic it will interate
    if (self._model.modflow and self._model.modflowsteady):
        step = self._model.lastStep

    while step <= self._model.lastStep:
      self._model.currentStep = step
      self._model.dynamic()
      step += 1




