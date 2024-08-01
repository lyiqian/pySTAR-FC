import abc
import os

import fabric
import invoke


NextFixation = object  # TODO need to think about passing around (e.g. via ssh) fixation objects


# ABCs
## YL workflow: can write concrete one and only create ABC on 2nd concrete
class IImageReader(abc.ABC):
    """An intermediate layer between eye and FC algorithm."""
    @abc.abstractmethod
    def read(self, img_src):
        pass


class IFixationLoader(abc.ABC):
    """An intermediate layer between FC algorithm and eye mover."""
    @abc.abstractmethod
    def load(self, fixation_src):
        pass


class IRetina(abc.ABC):
    @abc.abstractmethod
    def capture(self):
        pass

class IEyeMover(abc.ABC):
    @abc.abstractmethod
    def saccade(self, next_fixation):
        pass

class IEye(abc.ABC):
    retina: IRetina
    eye_mover: IEyeMover


class AbstractEmbodiedStarFC(abc.ABC):
    img_reader: IImageReader
    fixation_loader: IFixationLoader
    eye: IEye

    def __init__(self, img_reader, fixation_loader, eye) -> None:
        self.img_reader = img_reader
        self.fixation_loader = fixation_loader
        self.eye = eye

    @abc.abstractmethod
    def calc_fixation(self, image):
        pass

    def process_single(self):
        img_src = self.eye.retina.capture()

        image = self.img_reader.read(img_src)
        fixation_src = self.calc_fixation(image)

        next_fixation = self.fixation_loader.load(fixation_src)
        self.eye.eye_mover.saccade(next_fixation)


## Concrete Classes
GSV_CONN_STRING = "eason@gsv.eecs.yorku.ca"
MYPASS = os.getenv("GSV_PW")
LOCAL_ROOT = '/home/yiqian/repos/pySTAR-FC'
REMOTE_ROOT = '/home/eason/repos/pySTAR-FC'
LOCAL_IMG_FILENAME = 'bridge-cards-s.jpg'
REMOTE_IMG_FILENAME = 'curr_frame.jpg'


class GsvStarFC(AbstractEmbodiedStarFC):
    CONFIG_PATH = 'config_files/pantilt.ini'

    # output format depends on `dumpFixationsToMat`
    IMG_NAME = REMOTE_IMG_FILENAME.rsplit('.', maxsplit=1)[0]
    OUTPUT_PATH = f'{REMOTE_ROOT}/output/{IMG_NAME}/fixations_{IMG_NAME}.mat'

    def connect(self, ssh_conn):
        self.ssh_conn = ssh_conn

    def calc_fixation(self, image):
        # TODO dynamically change config file based on `image`
        print("Calc next fixation")
        cmd = (
            f'cd ~/repos/pySTAR-FC/docker '
            f'&& sudo docker exec starfc python3 src/STAR_FC.py -v -c {self.CONFIG_PATH}'
        )
        sudopass = invoke.Responder(pattern=r'\[sudo\] password for eason:', response=MYPASS+'\n')
        run_fc_result = self.ssh_conn.run(cmd, pty=True, watchers=[sudopass])

        if run_fc_result.stderr:
            print("ERROR")
            print(run_fc_result.stderr)

        return self.OUTPUT_PATH


class SshImageReader(IImageReader):
    """This acts as a POST."""
    REMOTE_IMG_PATH = f'{REMOTE_ROOT}/images/{REMOTE_IMG_FILENAME}'

    def __init__(self, ssh_conn) -> None:
        self.conn = ssh_conn

    def read(self, img_src=None):
        print("Putting to", self.REMOTE_IMG_PATH)
        self.conn.put(img_src, remote=self.REMOTE_IMG_PATH)
        return self.REMOTE_IMG_PATH


class SshFixationLoader(IFixationLoader):
    """This acts as a GET."""
    LOCAL_OUTPUT_PATH = f'{LOCAL_ROOT}/output/from_wrapper/next_fixation.mat'

    def __init__(self, ssh_conn) -> None:
        self.conn = ssh_conn

    def load(self, fixation_src) -> NextFixation:
        print("Downloading to", self.LOCAL_OUTPUT_PATH)
        self.conn.get(fixation_src, local=self.LOCAL_OUTPUT_PATH)
        # TODO load & return next_fixation


class StaticFileRetina(IRetina):
    def capture(self):
        local_img_src = f'{LOCAL_ROOT}/images/{LOCAL_IMG_FILENAME}'
        return local_img_src

class PtuEyeMover(IEyeMover):
    """Pan-tilt unit eye mover."""
    def saccade(self, next_fixation):
        pass  # TODO

class BasicEye(IEye):
    def __init__(self, retina: IRetina, eye_mover: IEyeMover) -> None:
        self.retina = retina
        self.eye_mover = eye_mover


if __name__ == '__main__':
    # Example usage
    ssh_conn = fabric.Connection(GSV_CONN_STRING, connect_kwargs=dict(password=MYPASS))

    img_reader = SshImageReader(ssh_conn)
    fix_loader = SshFixationLoader(ssh_conn)
    eye = BasicEye(StaticFileRetina(), PtuEyeMover())
    gsv_star_fc = GsvStarFC(img_reader, fix_loader, eye)

    gsv_star_fc.connect(ssh_conn)

    gsv_star_fc.process_single()
