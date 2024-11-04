import serial

DEBUG = True
DEFAULT_PORT_NAME = '/dev/ttyUSB0'


class PtuController:
    """As a convention, using whitespace as the delimiter."""
    ARCSEC_PER_POS = 185.1429  # run_cmd('pr ') or run_cmd('tr ')

    def __init__(self, port_name=DEFAULT_PORT_NAME) -> None:
        self.ser = serial.Serial(port_name, 9600, timeout=10)
        self.ser.xonxoff = True
        self.ser.isOpen()

        # user defined limits; although not enforced anywhere
        self.run_cmd('pxu1500 ')
        self.run_cmd('pnu-1000 ')

        self.pan(0)
        self.tilt(0)
        self.pan_pos = 0
        self.tilt_pos = 0

    def run_cmd(self, cmd):
        """Run a command, using syntax specified in the manual."""
        assert cmd.count(' ') == 1, "Only accept one command at a time!"
        self.ser.write(cmd.encode('ascii'))

        ret = self.ser.read_until()
        if DEBUG:
            print(ret)
        return ret.decode()

    def pan(self, degrees: float, relative=False):
        flag = 'o' if relative else 'p'
        pos = self.to_position(degrees)
        res = self.run_cmd(f'p{flag}{pos} ')
        if '!' in res:
            raise RuntimeError(f"Failed to pan: {res}")

    def tilt(self, degrees: float, relative=False):
        flag = 'o' if relative else 'p'
        pos = self.to_position(degrees)
        res = self.run_cmd(f't{flag}{pos} ')
        if '!' in res:
            raise RuntimeError(f"Failed to tilt: {res}")

    def wait(self):
        self.run_cmd('a ')

    def update_pan_tilt_pos(self):
        res = self.run_cmd('pp ')
        # 'pp * Current Pan position is 389\r\n'
        try:
            self.pan_pos = int(res.split()[-1])
        except Exception as e:
            print("res was: ", res)
            raise

        res = self.run_cmd('tp ')
        # 'tp * Current Tilt position is -292\r\n'
        try:
            self.tilt_pos = int(res.split()[-1])
        except Exception as e:
            print("res was: ", res)
            raise

    def calc_last_pan_tilt_degrees(self, prev_pan_pos, prev_tilt_pos):
        rel_pan_pos = self.pan_pos - prev_pan_pos
        rel_tilt_pos = self.tilt_pos - prev_tilt_pos
        pan_deg = self.to_degrees(rel_pan_pos)
        tilt_deg = self.to_degrees(rel_tilt_pos)
        return pan_deg, tilt_deg

    def to_degrees(self, pos):
        return pos * self.ARCSEC_PER_POS / 3600

    def to_position(self, degrees):
        return round(degrees * 3600 / self.ARCSEC_PER_POS)

    def reset(self):
        """Reset, and self-calibrate."""
        self.run_cmd('r ')

    def shutdown(self):
        """Release serial port."""
        self.ser.close()
