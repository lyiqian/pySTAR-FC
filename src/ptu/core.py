import serial

DEFAULT_PORT_NAME = '/dev/ttyUSB0'


class PtuController:
    def __init__(self, port_name) -> None:
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
        self.ser.write(cmd.encode('ascii'))
