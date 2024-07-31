import abc
import os

import fabric
import invoke


NextFixation = object  # TODO need to think about passing around (e.g. via ssh) fixation objects


# ABCs
## YL workflow: can write concrete one and only create ABC on 2nd concrete
class IImageReader(abc.ABC):
    @abc.abstractmethod
    def read(self, img_src):
        pass


class IFixationLoader(abc.ABC):
    @abc.abstractmethod
    def load(self, fixation_src):
        pass


class IEyeMover(abc.ABC):
    @abc.abstractmethod
    def saccade(self, next_fixation):
        pass


class AbstractStarFC(abc.ABC):
    img_reader: IImageReader
    fixation_loader: IFixationLoader
    eye_mover: IEyeMover

    def __init__(self, img_reader, fixation_loader, eye_mover) -> None:
        self.img_reader = img_reader
        self.fixation_loader = fixation_loader
        self.eye_mover = eye_mover

    @abc.abstractmethod
    def calc_fixation(self, image):
        pass

    def process_single(self, img_src=None):
        image = self.img_reader.read(img_src)
        fixation_src = self.calc_fixation(image)
        next_fixation = self.fixation_loader.load(fixation_src)
        self.eye_mover.saccade(next_fixation)


## Concrete Classes
GSV_CONN_STRING = "eason@gsv.eecs.yorku.ca"
MYPASS = os.getenv("GSV_PW")
LOCAL_IMG_FILENAME = 'bridge-cards-s.jpg'
REMOTE_IMG_FILENAME = 'curr_frame.jpg'


class GsvStarFC(AbstractStarFC):
    CONFIG_PATH = 'config_files/pantilt.ini'

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


class SshImageReader(IImageReader):
    """This acts as a POST."""
    LOCAL_IMG_DIRPATH = '/home/yiqian/repos/pySTAR-FC/images/'
    REMOTE_IMG_DIRPATH = '/home/eason/repos/pySTAR-FC/images/'

    def __init__(self, ssh_conn) -> None:
        self.conn = ssh_conn

    def read(self, img_src=None):
        local_img_filepath = self.LOCAL_IMG_DIRPATH + img_src
        remote_img_filepath = self.REMOTE_IMG_DIRPATH + REMOTE_IMG_FILENAME
        print("Putting to", remote_img_filepath)
        self.conn.put(local_img_filepath, remote=remote_img_filepath)


class SshFixationLoader(IFixationLoader):
    """This acts as a GET."""
    img_name = REMOTE_IMG_FILENAME.rsplit('.', maxsplit=1)[0]
    REMOTE_OUTPUT_PATH = f'/home/eason/repos/pySTAR-FC/output/{img_name}/fixations_{img_name}.mat'
    LOCAL_OUTPUT_PATH = f'/home/yiqian/repos/pySTAR-FC/output/from_wrapper/fixations_{img_name}.mat'

    def __init__(self, ssh_conn) -> None:
        self.conn = ssh_conn

    def load(self, fixation_src) -> NextFixation:  # TODO pass in remove output path
        print("Downloading to", self.LOCAL_OUTPUT_PATH)
        self.conn.get(self.REMOTE_OUTPUT_PATH, local=self.LOCAL_OUTPUT_PATH)
        # TODO return next_fixation


if __name__ == '__main__':
    # Example usage
    ssh_conn = fabric.Connection(GSV_CONN_STRING, connect_kwargs=dict(password=MYPASS))

    img_reader = SshImageReader(ssh_conn)
    fix_loader = SshFixationLoader(ssh_conn)
    gsv_star_fc = GsvStarFC(img_reader, fix_loader)

    gsv_star_fc.connect(ssh_conn)
    gsv_star_fc.process_single(LOCAL_IMG_FILENAME)
