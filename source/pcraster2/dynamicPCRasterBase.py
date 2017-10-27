# -*- coding: utf-8 -*-




class DynamicModel(object):

  def __init__(self):

    self.silentModelOutput = False
    self._d_nrTimeSteps = 0
    self.currentStep = 0
    self._d_firstTimeStep = 1
    self.inTimeStep = False
    self.inInitial = False
    self.inDynamic = False

	
	
	
	
	
  def initial(self):
    #print "Implement 'initial' method"
    ii =1
	
  def dynamic(self):
    print  "Implement 'dynamic' method"


  def timeSteps(self):
    """
    Return a list of time steps
    """
    return range(self.firstTimeStep(), self.nrTimeSteps() + 1)

  def nrTimeSteps(self):
    """
    Return the number of time steps
    """
    assert self._d_nrTimeSteps
    return self._d_nrTimeSteps

  def currentTimeStep(self):
    """
    Return the current time step in the range from firstTimeStep to nrTimeSteps.
    """
    assert self.currentStep >= 0
    return self.currentStep

  def firstTimeStep(self):
    """
    Return first timestep of a model.
    """
    assert self._d_firstTimeStep
    return self._d_firstTimeStep

  def setQuiet(self,
    quiet=True):
    """
    Disables the progress display of timesteps.
    """
    self.silentModelOutput = quiet	
	
# -------------------------------------------

	
  def _silentModelOutput(self):
    return self.silentModelOutput
	

  def _inDynamic(self):
    return self.inDynamic

  def _inInitial(self):
    return self.inInitial


  def _setInInitial(self, value):
    assert isinstance(value, bool)
    self.inInitial = value

  def _setInDynamic(self, value):
    assert isinstance(value, bool)
    self.inDynamic = value

  def _inTimeStep(self):
    """
    Returns whether a time step is currently executing.
    """
    #if hasattr(self._userModel(), "_d_inTimeStep"):
    #  return self._userModel()._d_inTimeStep
    #else:
    #  return False
    return self.inTimeStep

  def _setInTimeStep(self, value):
    assert isinstance(value, bool)
    self.inTimeStep = value	
  
  def _setFirstTimeStep(self, firstTimeStep):

    if not isinstance(firstTimeStep, int):
      msg = "first timestep argument (%s) of DynamicFramework must be of type int" % (type(firstTimeStep))
      raise AttributeError(msg)

    if firstTimeStep <= 0:
      msg = "first timestep argument (%s) of DynamicFramework must be > 0" % (firstTimeStep)
      raise AttributeError(msg)

    if firstTimeStep > self.nrTimeSteps():
      msg = "first timestep argument (%s) of DynamicFramework must be smaller than given last timestep (%s)" % (firstTimeStep, self.nrTimeSteps())
      raise AttributeError(msg)

    self._d_firstTimeStep = firstTimeStep
	
	
	
  def _setNrTimeSteps(self, TimeStep):
    """
    Set the number of time steps to run.
    """
    if not isinstance(TimeStep, int):
      msg = "last timestep argument (%s) of DynamicFramework must be of type int" % (type(TimeStep))
      raise AttributeError(msg)

    if TimeStep <= 0:
      msg = "last timestep argument (%s) of DynamicFramework must be > 0" % (TimeStep)
      raise AttributeError(msg)

    self._d_nrTimeSteps = TimeStep
	

  def _setCurrentTimeStep(self,
    step):
    """
    Set the current time step.
    """
    if step <= 0:
      msg = "Current timestep must be > 0"
      raise AttributeError(msg)

    if step > self.nrTimeSteps():
      msg = "Current timestep must be <= %d (nrTimeSteps)"
      raise AttributeError(msg)

    self.currentStep = step


# ----------------------------------------	
	
	

