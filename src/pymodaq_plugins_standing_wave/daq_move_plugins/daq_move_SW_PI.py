from typing import Union

from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun, main, DataActuatorType,\
    DataActuator  # common set of parameters for all actuators
from pymodaq.utils.daq_utils import ThreadCommand # object used to send info back to the main thread
from pymodaq.utils.parameter import Parameter

from pymodaq_plugins_standing_wave.hardware.pidaqmx import PIDAQMx, DAQ_Move_PI
from pymodaq_plugins_physik_instrumente.hardware.pi_wrapper import PIWrapper


class DAQ_Move_SW_PI(DAQ_Move_PI):
    """ Instrument plugin class for an actuator.
    
    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Move module through inheritance via
    DAQ_Move_base. It makes a bridge between the DAQ_Move module and the Python wrapper of a particular instrument.


    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.

    """

    def ini_stage(self, controller: Union[PIDAQMx, PIWrapper] = None):
        """Actuator communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator by controller (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        if controller is not None:
            if isinstance(controller, PIDAQMx):
                controller = controller.pi.controller

        info, initialized = super().ini_stage(controller)

        self.axis_units = ['µm', 'µm', 'µm']
        self.epsilons = [self.epsilon for _ in range(len(self.axis_units))]
        self.axis_unit = self.axis_units[self.axis_index_key]

        return info, initialized


if __name__ == '__main__':
    main(__file__, init=False)
