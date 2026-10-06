"""
Run the MODFLOW 6 library (libmf6) in a separate (child) process

A fatal MODFLOW error (e.g. a wrong input file) ends the process with a Fortran STOP (exit code 2).
If libmf6 runs in the CWatM process, this also ends Python without any message. Here only the child
process ends: CWatM stops with Error 313 and the error report of MODFLOW (mfsim.lst).

ModFlowProcess has the arguments, methods and attributes of ModFlowSimulation (modflow6.py) which are
used in transient.py. The arrays are sent through a Pipe with their dtype, so the results are the same
as with ModFlowSimulation.
"""

import multiprocessing
import os

from cwatm.management_modules import globals
from cwatm.management_modules.messages import CWATMError
from cwatm.hydrological_modules.groundwater_modflow.modflow6 import ModFlowSimulation, mf6_error_text

# child processes not finalized yet (e.g. a former run in the same Python process stopped with an error)
_running = []


def stop_running():
    """End the child processes of former runs which were not finalized"""
    for p in _running[:]:
        p.close()


def _child(conn, working_directory, args, kwargs):
    """
    Child process: create ModFlowSimulation (loads libmf6) and run the commands sent by ModFlowProcess

    Answers ('ok', values), or ('error', header, message) for a Python error
    """
    try:
        sim = ModFlowSimulation(*args, **kwargs)
        conn.send(('ok', sim.head.copy()))
        while True:
            command, values = conn.recv()
            if command == 'step':
                recharge, abstraction = values
                if recharge is not None:
                    sim.set_recharge(recharge)
                if abstraction is not None:
                    sim.set_groundwater_abstraction(abstraction)
                sim.step()
                actualwell = sim.actualwell_rate.copy() if hasattr(sim, 'actualwell_rate') else None
                conn.send(('ok', (sim.head.copy(), actualwell, sim.drainage.copy())))
            elif command == 'finalize':
                sim.finalize()
                conn.send(('ok', None))
                return
    except EOFError:
        # CWatM closed the Pipe (stop_running)
        return
    except CWATMError as e:
        header = type(e).header
        answer = ('error', header, str(e)[len(header):])
    except Exception as e:
        msg = "Error 314: MODFLOW error\n" + type(e).__name__ + ": " + str(e) + "\n"
        if type(e).__name__ == 'XMIError':
            msg += "If the MODFLOW solver does not converge: use a smaller modflow_timestep or use_complex_solver_for_modflow\n"
        answer = ('error', CWATMError.header, msg + mf6_error_text(working_directory))
    try:
        conn.send(answer)
    except OSError:
        pass


class ModFlowProcess:
    """
    MODFLOW in a child process, used in transient.py instead of ModFlowSimulation

    Parameters are the same as for ModFlowSimulation. A MODFLOW error which ends the child process
    raises Error 313, a Python error in the child process is raised as CWatM error (Error 312, 314, ...).
    """

    decompress = ModFlowSimulation.decompress

    def __init__(self, name, folder, path_mf6dll, timeout=3600, **kwargs):
        stop_running()
        # longest time in seconds for one MODFLOW call (start or one time step), 0: no limit
        self.timeout = timeout if timeout > 0 else None
        self.basin = kwargs['basin']
        self.nrow = kwargs['nrow']
        self.ncol = kwargs['ncol']
        self.working_directory = os.path.join(folder, 'wd')
        self.actualwell_rate = None
        self.drainage = None
        self.nstep = 0
        self._recharge = None
        self._abstraction = None

        # mfsim.lst of a former run would give a wrong error report if MODFLOW stops before writing a new one
        try:
            os.remove(os.path.join(self.working_directory, 'mfsim.lst'))
        except OSError:
            pass

        # spawn: a new Python process on all systems, libmf6 is loaded only in the child process
        context = multiprocessing.get_context('spawn')
        self.conn, child_conn = context.Pipe()
        self.process = context.Process(target=_child, daemon=True,
                                       args=(child_conn, self.working_directory, (name, folder, path_mf6dll), kwargs))
        self.process.start()
        # the parent keeps only its own end, so recv() gets EOFError when the child process ends
        child_conn.close()
        _running.append(self)
        self.head = self._receive('initialize')

    def _send(self, command, values):
        try:
            self.conn.send((command, values))
        except OSError:
            # child process has ended: _receive reports it
            pass

    def _receive(self, task):
        """Wait for the answer of the child process, raise a CWatM error if MODFLOW failed or did not answer in time"""
        if 'currDatestr' in globals.dateVar:
            task += " (" + globals.dateVar['currDatestr'] + ")"
        # poll: True if there is an answer or the child process has ended, False after timeout seconds
        try:
            answered = self.conn.poll(self.timeout)
        except OSError:
            answered = True
        if not answered:
            self.process.terminate()
            self.close()
            msg = "Error 315: MODFLOW did not finish " + task + " within " + str(self.timeout) + " seconds - the MODFLOW process is stopped\n"
            msg += "If MODFLOW is only slow: use a larger modflow_timeout in [GROUNDWATER_MODFLOW] (0: no limit)\n"
            raise CWATMError(msg + mf6_error_text(self.working_directory))
        try:
            answer = self.conn.recv()
        except (EOFError, OSError):
            answer = None
        # raised outside of except, so EOFError is not printed as reason
        if answer is None:
            self.close()
            code = self.process.exitcode
            # a Windows crash code, e.g. 0xc0000005 (access violation)
            if code is not None and code > 255:
                code = hex(code)
            msg = "Error 313: MODFLOW stopped with exit code " + str(code) + " in " + task
            msg += "\n" + mf6_error_text(self.working_directory)
            raise CWATMError(msg)
        if answer[0] == 'error':
            self.close()
            e = CWATMError(answer[2])
            e.args = (answer[1] + answer[2],)
            raise e
        return answer[1]

    def set_recharge(self, recharge):
        """Set recharge, value in m/day (given to MODFLOW at the next step)"""
        self._recharge = recharge

    def set_groundwater_abstraction(self, groundwater_abstraction):
        """Set well rate, value in m3/day (given to MODFLOW at the next step)"""
        self._abstraction = groundwater_abstraction

    def step(self):
        self.nstep += 1
        self._send('step', (self._recharge, self._abstraction))
        self.head, self.actualwell_rate, self.drainage = self._receive('MODFLOW time step ' + str(self.nstep))
        self._recharge = None
        self._abstraction = None

    def finalize(self):
        """Finalize MODFLOW and end the child process"""
        if self.process.is_alive():
            self._send('finalize', None)
            self._receive('finalize')
        self.close()

    def close(self):
        """End the child process (without finalize, if it is still running)"""
        self.conn.close()
        self.process.join(10)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join()
        if self in _running:
            _running.remove(self)
