import serial

DEBUG = True
DEFAULT_PORT_NAME = '/dev/ttyUSB0'


class PtuController:
    """As a convention, using whitespace as the delimiter."""
    ARCSEC_PER_POS = 185.1429  # run_cmd('pr ') or run_cmd('tr ')

    def __init__(self, port_name=DEFAULT_PORT_NAME) -> None:
        self.ser = serial.Serial(port_name, 9600, timeout=1)
        self.ser.xonxoff = True
        self.ser.isOpen()

        # user defined limits; although not enforced anywhere
        self.run_cmd('pxu1500 ')
        self.run_cmd('pnu-1000 ')

        self.pan(0)
        self.tilt(0)

    def run_cmd(self, cmd):
        """Run a command, using syntax specified in the manual."""
        assert cmd.count(' ') == 1, "Only accept one command at a time!"
        self.ser.write(cmd.encode('ascii'))

        ret = self.ser.read_until()
        if DEBUG:
            print(ret)
        return ret.decode()

    def pan(self, degrees: float):
        pos = round(degrees * 3600 / self.ARCSEC_PER_POS)
        res = self.run_cmd(f'pp{pos} ')
        if '!' in res:
            raise RuntimeError(f"Failed to pan: {res}")

    def tilt(self, degrees: float):
        pos = round(degrees * 3600 / self.ARCSEC_PER_POS)
        res = self.run_cmd(f'tp{pos} ')
        if '!' in res:
            raise RuntimeError(f"Failed to tilt: {res}")

    def reset(self):
        """Reset, and self-calibrate."""
        self.run_cmd('r ')

    def shutdown(self):
        """Release serial port."""
        self.ser.close()
