from cwatm.cwatm_initial import CWATModel_ini
from cwatm.cwatm_dynamic import CWATModel_dyn

class CWATModel(CWATModel_ini, CWATModel_dyn):
    """
    Initial and dynamic part of the CWATM model
    * initial part takes care of all the non temporal initialiation procedures
    * dynamic part loops over time
    """
