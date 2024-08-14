import serial

DEBUG = True
DEFAULT_PORT_NAME = '/dev/ttyUSB0'


class PtuController:
    """As a convention, using whitespace as the delimiter."""
    def __init__(self, port_name=DEFAULT_PORT_NAME) -> None:
        self.ser = serial.Serial(port_name, 9600, timeout=1)
        self.ser.xonxoff = True
        self.ser.isOpen()

        self.run_cmd('pxu1500 ')
        self.run_cmd('pnu-1000 ')
        self.run_cmd('tn-900 ')
        self.run_cmd('tx900 ')
        self.run_cmd('pp0 ')
        self.run_cmd('tp0 ')

    def run_cmd(self, cmd):
        """Run a command, using syntax specified in the manual."""
        assert cmd.count(' ') == 1, "Only accept one command at a time!"
        self.ser.write(cmd.encode('ascii'))

        ret = self.ser.read_until()
        if DEBUG:
            print(ret)
        return ret

    def shutdown(self):
        """Release serial port."""
        self.ser.close()
