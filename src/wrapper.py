import abc


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

    @abc.abstractmethod
    def calc_fixation(self, image):
        pass

    def process_single(self, path):
        img = self.img_reader.read(path)
        next_fixation = self.calc_fixation(img)
        self.fixation_writer.write(next_fixation)
