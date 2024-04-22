import numpy as np
from typing import List

from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins, Axis, DataToExport, DataActuator
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter
from pymodaq.utils.parameter.utils import iter_children
from pymodaq.utils.math_utils import linspace_step_N
from pymodaq_plugins_standing_wave.hardware.pidaqmx import PIDAQMx, DAQ_Move_PI
from pymodaq_plugins_daqmx.hardware.national_instruments.daqmx import (DAQmx, AIChannel,
                                                                       ClockSettings,
                                                                       TriggerSettings)

from pymodaq_plugins_standing_wave import config

device_ai = config('daqmx', 'device_ai')
channel_ai = config('daqmx', 'channel_ai')
clock_ai_terminal = config('daqmx', 'clock_ai_terminal')
trigger_ai_terminal = config('daqmx', 'trigger_ai_terminal')


class DAQ_1DViewer_GrabMove(DAQ_Viewer_base):
    """ Instrument plugin class for a 1D viewer.
    
    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Viewer module through inheritance via
    DAQ_Viewer_base. It makes a bridge between the DAQ_Viewer module and the Python wrapper of a particular instrument.

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.
         
    """
    params = comon_parameters+[
        {'title': 'Npoints:', 'name': 'npoints', 'type': 'int', 'value': config('npts')},
        {'title': 'Axis offset position:', 'name': 'axis_offset', 'type': 'float', 'value': 0.},
        {'title': 'Move to offset:', 'name': 'move_offset', 'type': 'bool_push', 'value': False,
         'label': 'Move to'},

        {'title': 'PI waveform', 'name': 'wf', 'type': 'group', 'children': [
            {'title': 'Use Waveform:', 'name': 'wf_use', 'type': 'bool', 'value': False},
            {'title': 'Waveform start:', 'name': 'wf_start', 'type': 'float', 'value': config('waveform', 'start')},
            {'title': 'Waveform stop:', 'name': 'wf_stop', 'type': 'float', 'value': config('waveform', 'stop')},
            ]},

        {'title': 'DAQmx', 'name': 'daqmx_params', 'type': 'group', 'children': [
            {'title': 'AI Channel:', 'name': 'ai_channel', 'type': 'list',
             'values': DAQmx.get_NIDAQ_channels(source_type='Analog_Input'),
             'value': f'{device_ai}/{channel_ai}'},
            {'title': 'Clock Channel:', 'name': 'clock_channel', 'type': 'list',
             'values': DAQmx.get_NIDAQ_channels(source_type='Terminals'),
             'value': f'/{device_ai}/{clock_ai_terminal}'},
            {'title': 'Clock rate:', 'name': 'clock_rate', 'type': 'int',
             'value': config('daqmx', 'clock_rate')},
            {'title': 'Trigger Channel:', 'name': 'trigger_channel', 'type': 'list',
             'values': DAQmx.get_NIDAQ_channels(source_type='Terminals'),
             'value': f'/{device_ai}/{trigger_ai_terminal}'},
            {'title': 'Enable Trigger:', 'name': 'trigger_enabled', 'type': 'bool',
             'value': config('daqmx', 'trigger_enabled')},
            {'title': 'Trigger level:', 'name': 'trigger_level', 'type': 'float',
             'value': config('daqmx', 'trigger_level')},
        ]},
        {'title': 'PI', 'name': 'pi_params', 'type': 'group', 'children': DAQ_Move_PI.params}
        ]

    def ini_attributes(self):
        self.controller: PIDAQMx = None
        self.x_axis = None

        self.channel_ai: AIChannel = None
        self.clock_settings: ClockSettings = None
        self.trigger_settings: TriggerSettings = None

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """

        if (param.name() == 'npoints' or param.name() in
                iter_children(self.settings.child('daqmx_params'), [])):
            self.update_tasks()
            self.update_axis()
        if param.name() in iter_children(self.settings.child('pi_params'), []):
            self.controller.pi.commit_settings(param)
        elif param.name() == 'move_offset':
            if param.value():
                self.controller.pi.move_abs(DataActuator(data=self.settings['axis_offset']))
                param.setValue(False)
        if ((param.name() in iter_children(self.settings.child('wf'), []) or param.name() == 'npoints') and
                self.settings['wf', 'wf_use']):
            self.prepare_waveform()

    def prepare_waveform(self):
        amplitude = self.settings['wf', 'wf_stop'] - self.settings['wf', 'wf_start']
        offset = self.settings['wf', 'wf_start']
        self.controller.pi.controller.set_1D_waveform(amplitude, offset, npts=self.settings['npoints'],
                                                      axis=int(self.controller.pi.axis_name))
        self.controller.pi.controller.set_trigger_waveform([1], do=1)
        self.settings.child('daqmx_params', 'trigger_enabled').setValue(True)

    def update_tasks(self):

        self.channel_ai = AIChannel(name=self.settings['daqmx_params', 'ai_channel'],
                                      source='Analog_Input', analog_type='Voltage',
                                      value_min=-10., value_max=10., termination='Diff', ),

        self.clock_settings = ClockSettings(source=self.settings['daqmx_params', 'clock_channel'],
                                            frequency=self.settings['daqmx_params', 'clock_rate'],
                                            Nsamples=self.settings['npoints'],)

        self.trigger_settings = TriggerSettings(
            trig_source=self.settings['daqmx_params', 'trigger_channel'],
            enable=self.settings['daqmx_params', 'trigger_enabled'],
            level=self.settings['daqmx_params', 'trigger_level'])

        self.controller.daqmx.update_task(self.channel_ai,
                                          clock_settings=self.clock_settings,
                                          trigger_settings=self.trigger_settings)

    def update_axis_position(self, position: DataActuator):
        self.settings.child('axis_offset').setValue(position.value())

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator/detector by controller
            (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """

        self.ini_detector_init(old_controller=controller,
                               new_controller=PIDAQMx(self.settings.child('pi_params').saveState()))

        if self.settings['controller_status'] == "Master":
            self.controller.pi.ini_stage()

            self.settings.child('pi_params', 'multiaxes', 'axis').setLimits(self.controller.pi.axis_names)

        self.update_axis()
        self.update_tasks()

        info = "GrabMove detector is initialized"
        initialized = True
        return info, initialized

    def update_axis(self):
        self.x_axis = Axis('time', 's',
                           data=linspace_step_N(0, 1 / self.settings['daqmx_params', 'clock_rate'],
                                                self.settings['npoints']))

    def close(self):
        """Terminate the communication protocol"""
        self.controller.pi.close()
        self.controller.daqmx.close()

    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging (if hardware averaging is possible, self.hardware_averaging should be set to
            True in class preamble and you should code this implementation)
        kwargs: dict
            others optionals arguments
        """
        self.controller.daqmx.start()

        if self.settings['wf', 'wf_use']:
            self.controller.pi.controller.start_waveform(int(self.controller.pi.axis_name), cycles=1)

        data_array = self.controller.daqmx.readAnalog(1, self.clock_settings)

        self.dte_signal.emit(DataToExport('myplugin',
                                          data=[DataFromPlugins(name='GrabMove', data=[data_array],
                                                                dim='Data1D', labels=['Signal'],
                                                                axes=[self.x_axis])]))
        self.controller.daqmx.stop()

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        self.controller.daqmx.stop()
        return ''


if __name__ == '__main__':
    main(__file__, init=False)
