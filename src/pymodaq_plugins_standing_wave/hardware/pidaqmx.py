from typing import List


from pymodaq_plugins_daqmx.hardware.national_instruments.daqmx import (DAQmx, AIChannel,
                                                                       ClockSettings)

from pymodaq_plugins_physik_instrumente.daq_move_plugins.daq_move_PI import DAQ_Move_PI


class PIDAQMx:
    """Custom wrapper holding references for both the PI stages and the daqmx acquisition"""
    def __init__(self, pi_params: dict = None):
        self._pi = DAQ_Move_PI(None, pi_params)
        self._daqmx = DAQmx()
        self.channels_ai: List[AIChannel] = None

    @property
    def pi(self) -> DAQ_Move_PI:
        return self._pi

    @property
    def daqmx(self) -> DAQmx:
        return self._daqmx