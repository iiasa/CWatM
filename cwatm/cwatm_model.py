# -------------------------------------------------------------------------
# Name: CWATM Model
# Purpose: Primary CWatM model class integrating initialization and dynamic components.
# Combines CWATModel_ini and CWATModel_dyn through multiple inheritance.
# Provides unified interface for complete hydrological modeling framework.
#
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------



from cwatm.cwatm_initial import CWATModel_ini
from cwatm.cwatm_dynamic import CWATModel_dyn

class CWATModel(CWATModel_ini, CWATModel_dyn):
    """
    Main CWatM model class combining initialization and dynamics.

    This class serves as the primary interface for the Community Water Model (CWatM),
    inheriting from both the initialization (CWATModel_ini) and dynamic (CWATModel_dyn)
    components to provide a complete hydrological modeling framework.

    The model handles:
    - Initial setup and parameter configuration
    - Temporal simulation loops
    - Integration of all hydrological processes
    - Model state management

    Attributes
    ----------
    Inherits all attributes from CWATModel_ini and CWATModel_dyn including:
    - var : object
        Model variables container
    - model : object
        Model configuration and state

    Notes
    -----
    The initial part handles all non-temporal initialization procedures including
    reading input data, setting up model parameters, and initializing state variables.
    The dynamic part manages the temporal simulation loop, executing hydrological
    processes for each time step.
    """
