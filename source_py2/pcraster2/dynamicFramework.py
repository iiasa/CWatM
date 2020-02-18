# -*- coding: utf-8 -*-
import sys


import atexit
import os
import re
import weakref
import time
import traceback


## cwat_dynamic 14 #from pcraster2.dynamicFramework import *
#cwat.py stCWATM = DynamicFramework(CWATM, firstTimestep=dateVar["intStart"], lastTimeStep=dateVar["intEnd"]

class WeakCallback (object):
    """A Weak Callback object that will keep a reference to
    the connecting object with weakref semantics.

    This allows object A to pass a callback method to object S,
    without object S keeping A alive.
    """
    def __init__(self, mcallback):
        """Create a new Weak Callback calling the method @mcallback"""
        obj = mcallback.im_self
        attr = mcallback.im_func.__name__
        self.wref = weakref.ref(obj, self.object_deleted)
        self.callback_attr = attr

    def __call__(self, *args, **kwargs):
        obj = self.wref()
        if obj:
            attr = getattr(obj, self.callback_attr)
            result = attr(*args, **kwargs)
        else:
            result = self.default_callback(*args, **kwargs)
        return result

    def default_callback(self, *args, **kwargs):
        """Called instead of callback when expired"""
        assert False
        # pass

    def object_deleted(self, wref):
        """Called when callback expires"""
        pass


@atexit.register
def _atExit():
  print




# --------------------------------------------------------------------

class DynamicFramework(object):
  """
  Framework class for dynamic models.

  `userModel`
    Instance that models the Dynamic Model Concept <dynamicModelConcept>

  `lastTimeStep`
    Last timestep to run.

  `firstTimestep`
    Sets the starting timestep of the model (optional, default is 1).
  """
  # output relevant attributes
  _d_quiet = False
  _d_trace = False
  _d_debug = False
  _d_indentLevel = 0
  _d_inScript = False
  _d_mapExtension = ".map"
  
  
  def __init__(self,
    userModel,
    lastTimeStep=0,
    firstTimestep=1):
#    frameworkBase.FrameworkBase.__init__(self, ["frameworkBase.py"])

    self._startTime = time.time()

    self._d_silentModelOutput = False
    self._d_silentFrameworkOutput = True
    self._d_quietProgressDots = False
    self._d_quietProgressSampleNr = False

    self._d_model = userModel
    self._testRequirements()

    # fttb
    self._addMethodToClass(self._readmapNew)
    self._addMethodToClass(self._reportNew)

    try:
      self._userModel()._setNrTimeSteps(lastTimeStep)
      self._d_firstTimestep = firstTimestep
      self._userModel()._setFirstTimeStep(self._d_firstTimestep)
    except Exception, msg:
      sys.stderr.write('Error: %s\n' % str(msg))
      sys.exit(1)

  def _userModel(self):
    """
    Return the model instance provided by the user.
    """
    return self._d_model


  def run(self):
	"""
	Run the dynamic user model.
	"""
	self._atStartOfScript()
	if(hasattr(self._userModel(), "resume")):
		#if self._userModel().firstTimeStep() == 1:
		# replaced this because starting date is not always the 1
		if self._userModel().firstTimeStep() == datetoInt(binding['StepStart']):
		   self._runInitial()
		else:
		   self._runResume()
	else:
		self._runInitial()

	self._runDynamic()

	# Only execute this section while running filter frameworks.
	if hasattr(self._userModel(), "suspend") and \
	hasattr(self._userModel(), "filterPeriod"):
	  self._runSuspend()

	return 0



  # Adjusting the def _atStartOfTimeStep defined in DynamicFramework for a real quiet output
  rquiet = False
  rtrace = False	
	

  def _testRequirements(self):
    """
    Test whether the user model models the
    Dynamic Model Concept <dynamicModelConcept>
    """
    if hasattr(self._userModel(), "_userModel"):
      msg = "The _userModel method is deprecated and obsolete"
      self.showWarning(msg)

    if( not hasattr(self._userModel(), "dynamic") and not hasattr(self._userModel(), "run")):
      msg = "Cannot run dynamic framework: Implement dynamic method"
      raise frameworkBase.FrameworkError(msg)


    if not hasattr(self._userModel(), "initial"):
      if self._debug():
        self.showWarning("No initial section defined.")

  def setQuiet(self, quiet=True):
    """
    Disables the progress display of timesteps.
    """
    self._d_quietProgressDots = quiet
# ------------------------------------------------------


	
  def _getName(self):
    return self._name

  def _getArguments(self):
    return self._arguments

  def _getOptions(self):
    return self._options

  ## Name property, read-only.
  name = property(_getName)

  ## Arguments property, read-only.
  #  Note: usualy equals sys.argv[1:], so 1 less than sys.argv
  arguments = property(_getArguments)

  ## Options property, read-only.
  options = property(_getOptions)

  def _formatMessage(self,
         message,
         prefix=""):
    messages = message.split("\n")
    for i in range(0, len(messages)):
      if prefix:
        messages[i] = "%s: %s" % (prefix, messages[i])
    return "%s\n" % ("\n".join(messages)).encode("utf-8")

  ## Prints a message on stdout.
  #
  # \param     message Message to print.
  #
  # - Message is stripped.
  # - A newline is appended.
  def showMessage(self, message):
    sys.stdout.write(self._formatMessage(message))

  ## Prints a warning message on stdout.
  #
  # \param     message Message to print.
  #
  # - Message is prepended by "Warning: ".
  # - Message is stripped.
  # - A newline is appended.
  def showWarning(self, message):
    sys.stdout.write(self._formatMessage(message, "Warning"))

  ## Prints an error message on stderr.
  #
  # \param     message Message to print.
  #
  # - Message is prepended by "Error: ".
  # - Message is stripped.
  # - A newline is appended.
  def showError(self, message):
    sys.stderr.write(self._formatMessage(message, "Error"))

  ## Prints a message on stdout.
  #
  # \param     message Message to print.
  #
  # The stream is flushed, so the output is imediately visible.
  def write(self, message):
    sys.stdout.write(message.strip())
    sys.stdout.flush()

  ## Wraps the call to _parseOptions() and _run() by exception handling code.
  #
  # Returns the result of _run() if it is not None, otherwise 0 is returned.

# ------------------------------------------------------
  def _parseOptions(self):
    pass

  def _run(self):
    return 0




  ##
  # \deprecated Use arguments().
  def argv(self):
    print "deprecated, update your script"
    return [self.name] + self.arguments

  ##
  # \deprecated Use len(arguments()).
  def nrArguments(self):
    print "deprecated, update your script"
    return len(self.argv())

  ##
  # \deprecated Use name().
  def appName(self):
    print "deprecated, update your script"
    return self.name

  ##
  # \deprecated Not crucial for a basic shellscript class.
  def duration(self):
    print "deprecated, update your script"
    self._endTime = time.time()
    return "%s" % (utils.duration(self._startTime, self._endTime))

  ##
  # \deprecated Not crucial for a basic shellscript class.
  def printDuration(self):
    print "deprecated, update your script"
    self._endTime = time.time()
    self.showMessage("duration %s: %s" % (self.name,
         utils.duration(self._startTime, self._endTime)))

  ##
  # \deprecated Not crucial for a basic shellscript class.
  def preRun(self):
    print "deprecated, update your script"

  ##
  # \deprecated Not crucial for a basic shellscript class.
  def postRun(self):
    print "deprecated, update your script"

  ##
  # \deprecated Use showMessage().
  def message(self, msg):
    print "deprecated, update your script"
    self.showMessage(msg)

  ##
  # \deprecated Use showWarning().
  def warning(self, msg):
    print "deprecated, update your script"
    self.showWarning(msg)

  ##
  # \deprecated Use showError().
  def error(self, msg):
    print "deprecated, update your script"
    self.showError(msg)



# --------------------------------------	
	
  def _inUpdateWeight(self):
    if not hasattr(self._userModel(), "_d_inUpdateWeight"):
      return False
    return self._userModel()._d_inUpdateWeight

  def _inResume(self):
    if not hasattr(self._userModel(), "_d_inResume"):
      return False
    return self._userModel()._d_inResume

  def __del__(self):
    self._atEndOfScript()

  def _silentModelOutput(self):
    return self._d_silentModelOutput

  def _addMethodToClass(self, func):
    # NO! This will create a circular reference between the user model and the
    # framework class. Both will never be deleted because the reference counts
    # will never drop to zero.
    # setattr(self._userModel(), func.__name__, func)

    # Use a weak reference to the framework class. This assumes that the
    # framework class will be alive for as long as the user model is used.
    call_back = WeakCallback(func)
    setattr(self._userModel(), func.__name__, call_back)

  def _addAttributeToClass(self, attr, value):
    setattr(self._userModel(), attr, value)


  def _atStartOfTimeStep(self, step):
	"""
	Adjusting the def _atStartOfTimeStep defined in DynamicFramework
	for a real quiet output

	:param step:
	:return:
	"""
	self._userModel()._setInTimeStep(True)
	if not self.rquiet:
		if not self.rtrace:
			msg = u"#"

		else:
			msg = u"%s<time step=\"%s\">\n" % (self._indentLevel(), step)
		sys.stdout.write(msg)
		sys.stdout.flush()	
	
	

  def _timeStepFinished(self):
    self._userModel()._setInTimeStep(False)

    if not self._quiet():
      if self._trace():
        self.showMessage("%s</time>" % (self._indentLevel()))

  def _atStartOfScript(self):
    if not self._d_inScript:
      self._userModel()._d_inScript = True
      if not self._quiet():
        if self._trace():
          self.showMessage("<script>")

  def _atEndOfScript(self):
    if self._d_inScript:
      self._d_inScript = False
      if not self._quiet():
        if not self._trace():
          msg = u"\n"
        else:
          msg = u"</script>\n"
        # showMessage does not work due to encode throw
        sys.stdout.write(msg)
        sys.stdout.flush()

  def _incrementIndentLevel(self):
    self._d_indentLevel += 1

  def _decrementIndentLevel(self):
    assert self._d_indentLevel > 0
    self._d_indentLevel -= 1

  def _scriptFinished(self):
    self._atEndOfScript()


  def _trace(self):
    return self._d_trace

  ## \brief debug
  #
  # \return true or false
  def _debug(self):
    return self._d_debug

  def _indentLevel(self):
    return self._d_indentLevel * "  "

  def _traceIn(self, functionName):
    if not self._quiet():
      if self._trace():
        self.showMessage("%s<%s>" % (self._indentLevel(), functionName))

  def _traceOut(self, functionName):
    if not self._quiet():
      if self._trace():
        self.showMessage("%s</%s>" % (self._indentLevel(), functionName))

  def _quiet(self):
    """
    Return the quiet state.
    """
    return self._d_quietProgressDots

  def _quietProgressSampleNr(self):
    """
    Return state of sample number display.

    .. todo::

      This method assumes a Monte Carlo style framework specialization.
      We should think of a more general verbosity level member to which
      frameworks can respond.
    """
    return self._d_quietProgressSampleNr


  def setTrace(self,
    trace):
    """
    Trace framework output to stdout.

    `trace`
      True/False. Default is set to False.

    If tracing is enabled the user will get a detailed framework output
    in an XML style.
    """
    self._d_trace = trace	
	
	
	
# ------------------------------------------------------
  def setDebug(self,
    debug):
    self._d_debug = debug

  def _atStartOfSample(self,
    nr):
    self._userModel()._d_inSample = True

    if not self._quietProgressSampleNr():
      if not self._trace():
        msg = u"%d " % (nr)
      else:
        msg = u"%s<sample nr=\"%s\">\n" % (self._indentLevel(), nr)
      # no showMessage here, \n not desired in non-trace "..." timestep output
      sys.stdout.write(msg)
      sys.stdout.flush()

  def _sampleFinished(self):
    self._userModel()._d_inSample = False

    if not self._quiet():
      #if not self._trace():
        #msg = "]"
      #else:
      if self._trace():
        msg = "%s</sample>" % (self._indentLevel())
        self.showMessage(msg)

  def _atStartOfFilterPeriod(self,
    nr):
    self._userModel()._d_inFilterPeriod = True
    if not self._d_model._quiet():
      if not self._d_model._trace():
        msg = "\nPeriod %d" % (nr + 1)
      else:
        msg = "%s<period nr=\"%s\">" % (self._indentLevel(), nr + 1)

      self.showMessage(msg)

  def _atEndOfFilterPeriod(self):
    self._userModel()._d_inFilterPeriod = False
    if not self._d_model._quiet():
      if self._d_model._trace():
        msg = "%s</period>" % (self._indentLevel())
        self.showMessage(msg)



  def _runInitial(self):
    self._userModel()._setInInitial(True)
    if(hasattr(self._userModel(), 'initial')):
      self._incrementIndentLevel()
      self._traceIn("initial")
      self._userModel().initial()
      self._traceOut("initial")
      self._decrementIndentLevel()

    self._userModel()._setInInitial(False)

  def _runDynamic(self):
    self._userModel()._setInDynamic(True)
    step = self._userModel().firstTimeStep()
    while step <= self._userModel().nrTimeSteps():

      self._incrementIndentLevel()
      self._atStartOfTimeStep(step)
      self._userModel()._setCurrentTimeStep(step)
      if hasattr(self._userModel(), 'dynamic'):
        self._incrementIndentLevel()
        self._traceIn("dynamic")
        self._userModel().dynamic()
        self._traceOut("dynamic")
        self._decrementIndentLevel()

      self._timeStepFinished()
      self._decrementIndentLevel()
      step += 1

    self._userModel()._setInDynamic(False)


  def _runSuspend(self):
    if(hasattr(self._userModel(), 'suspend')):
      self._incrementIndentLevel()
      self._traceIn("suspend")
      self._userModel().suspend()
      self._traceOut("suspend")
      self._decrementIndentLevel()

  def _runResume(self):
    self._userModel()._d_inResume = True
    if(hasattr(self._userModel(), 'resume')):
      self._incrementIndentLevel()
      self._traceIn("resume")
      self._userModel().resume()
      self._traceOut("resume")
      self._decrementIndentLevel()
    self._userModel()._d_inResume = False

  def _runPremcloop(self):
    self._userModel()._d_inPremc = True
    if hasattr(self._userModel(), 'premcloop') :
      self._incrementIndentLevel()
      self._traceIn("premcloop")
      self._userModel().premcloop()
      self._traceOut("premcloop")
      self._decrementIndentLevel()

    self._userModel()._d_inPremc = False

  def _runPostmcloop(self):
    self._userModel()._d_inPostmc = True
    if hasattr(self._userModel(), 'postmcloop'):
      self._incrementIndentLevel()
      self._traceIn("postmcloop")
      self._userModel().postmcloop()
      self._traceOut("postmcloop")
      self._decrementIndentLevel()

    self._userModel()._d_inPostmc = False
# ------------------------------------------------------
  def _report(self, variable, name):
    """
    Report map data to disk.

    .. todo::

      Uses PCRaster package which isn't imported.
    """
    pcraster.report(variable, name)

  def _generateName(self, name):
    """
    Return a filename based on the name and the current sample number
    and time step.

    The filename created will depend on whether this function is called
    from within a sample and/or a time step. Pseudo code:

    if sample and time step:
      sample/name.timestep
    else if sample:
      sample/name
    else if time step:
      name.timestep
    else:
      name

    If this function is not called from within a time step and name does not
    have an extension, the default extension '.map' is added to the name.

    See also: generateNameS(), generateNameT(), generateNameST()
    """
    if self._inSample() and self._inTimeStep():
      name = self._generateNameST(name, self.currentSampleNumber(),
        self.currentTimeStep())
    elif self.inSample():
      name = self._generateNameS(name, self.currentSampleNumber())
    elif self.inTimeStep():
      name = self._generateNameT(name, self.currentTimeStep())

    if not self.inTimeStep() and len(os.path.splitext(name)[1]) == 0:
      name = name + ".map"

    return name

  def _generateNameT(self, name, time):
    return generateNameT(name, time)

  def _generateNameS(self, name, sample):
    return generateNameS(name, sample)

  def _generateNameST(self, name, sample, time):
    """
    Return a filename based on the name, sample number and time step.

    See also: generateNameT(), generateNameS()
    """
    return self._generateNameS(self._generateNameT(name, time), sample)

  def generateNameS(self, name, sample):
    return generateNameS(name, sample)

  def _reportNew(self,
    variable,
    name,
    style=1):
    """

    .. todo::

      `style` argument is not used.
    """
    head, tail = os.path.split(name)

    if re.search("\.", tail):
      msg = "File extension given in '" + name + "' not allowed, provide filename without extension"
      raise FrameworkError(msg)

    directoryPrefix = ""
    nameSuffix = ".map"
    newName = ""

    if hasattr(self._userModel(), "_inStochastic"):
      if self._userModel()._inStochastic():
        if self._userModel()._inPremc():
          newName = name + nameSuffix
        elif self._userModel()._inPostmc():
          newName = name + nameSuffix
        else:
          directoryPrefix = str(self._userModel().currentSampleNumber())

    if self._userModel()._inInitial():
      newName = name + nameSuffix

    if hasattr(self._userModel(), "_inDynamic"):
      if self._userModel()._inDynamic() or self._inUpdateWeight():
        newName = generateNameT(name, self._userModel().currentTimeStep())

    path = os.path.join(directoryPrefix, newName)
    import pcraster
    pcraster.report(variable, path)

  def _readmapNew(self, name,
    style=1):
    """

    .. todo::

      `style` argument is not used.
    """
    directoryPrefix = ""
    nameSuffix = ".map"
    newName = ""

    if hasattr(self._userModel(), "_inStochastic"):
      if self._userModel()._inStochastic():
        if self._userModel()._inPremc() or self._userModel()._inPostmc():
          newName = name + nameSuffix
        else:
          directoryPrefix = str(self._userModel().currentSampleNumber())

    if hasattr(self._userModel(), "_inInitial"):
      if self._userModel()._inInitial():
        newName = name + nameSuffix

    if self._inResume():
      timestep = self._userModel().firstTimeStep()
      newName = generateNameT(name, timestep - 1)

    if hasattr(self._userModel(), "_inDynamic"):
      if self._userModel()._inDynamic() or self._inUpdateWeight():
        timestep = self._userModel().currentTimeStep()
        newName = generateNameT(name, timestep)

    path = os.path.join(directoryPrefix, newName)
    assert path is not ""
    import pcraster
    return pcraster.readmap(path)

  def _assertAndThrow(self,
    expression,
    message):
    assert expression, message



# ------------------------------------------------------
class FrameworkError(Exception):
  def __init__(self,
    msg):
    self._msg = msg

  def __str__(self):
    return self._msg

