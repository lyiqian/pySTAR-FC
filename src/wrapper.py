import abc


# ABCs
class IImageReader(abc.ABC):
    @abc.abstractmethod
    def read(self, path):
        pass


class IFixationWriter(abc.ABC):
    @abc.abstractmethod
    def write(self, fixations):
        pass


class AbstractStarFC(abc.ABC):
    img_reader: IImageReader
    fixation_writer: IFixationWriter

    def __init__(self, img_reader, fixation_writer) -> None:
        self.img_reader = img_reader
        self.fixation_writer = fixation_writer

    @abc.abstractmethod
    def calc_fixation(self, image):
        pass

    def process_single(self, path=None):
        image = self.img_reader.read(path)
        next_fixation = self.calc_fixation(image)
        self.fixation_writer.write(next_fixation)


## Concrete Classes
class GsvStarFC(AbstractStarFC):
    def calc_fixation(self, image):
        print("TODO Calc next fixation")


class SshImageReader(IImageReader):
    def read(self, path=None):
        print("TODO Reading path", path)


class SshFixationWriter(IFixationWriter):
    def write(self, fixations):
        print("TODO Writing fixations")


if __name__ == '__main__':
    # Example usage
    gsv_star_fc = GsvStarFC(
        img_reader=SshImageReader(),
        fixation_writer=SshFixationWriter())

    gsv_star_fc.process_single()
