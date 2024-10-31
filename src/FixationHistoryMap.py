import pickle
import scipy.io as sio
import numpy as np
import math

class FixationHistoryMap:
    def __init__(self, h, w, hPadded, wPadded, settings):
        self.height = h
        self.width = w
        self.hPadded = hPadded
        self.wPadded = wPadded
        self.iorSizePx = int(settings.iorSizeDeg*settings.pix2deg)
        self.settings = settings

        self.fixHistMap = np.zeros((self.height, self.width), dtype=np.float32)
        self.fixHistMapPadded = np.zeros((self.hPadded, self.wPadded), dtype=np.float32)

        self.lastFixation = None
        self.fixationList = np.empty((0, 2), dtype=np.int32)


    def saveFixationCoords(self, fixCoords):
        self.lastFixation = fixCoords
        fixCoordsPadded = fixCoords + np.array([self.height/2, self.width/2], dtype=np.int32)

        self.fixationList = np.append(self.fixationList, [fixCoords], axis=0)
        #add inhibition area around the new fixation with radius iorSizePx
        for i in range(fixCoordsPadded[0]-self.iorSizePx, fixCoordsPadded[0]+self.iorSizePx):
            for j in range(fixCoordsPadded[1]-self.iorSizePx, fixCoordsPadded[1]+self.iorSizePx):
                d = math.sqrt((fixCoordsPadded[0]-i)*(fixCoordsPadded[0]-i) + (fixCoordsPadded[1]-j)*(fixCoordsPadded[1]-j))
                if d <= self.iorSizePx:
                    self.fixHistMapPadded[i,j] = min(1, self.fixHistMapPadded[i,j] + 1 - d/self.iorSizePx)

    def decayFixations(self):
        self.fixHistMapPadded -= 1/self.settings.iorDecayRate
        self.fixHistMapPadded = np.fmax(self.fixHistMapPadded, np.zeros((self.hPadded, self.wPadded)))

    def getFixationHistoryMap(self):
        #when there is no history of fixations yet return map of 0s
        if self.lastFixation is None:
            return self.fixHistMap
        else:
            return self.fixHistMapPadded[self.lastFixation[0]:self.lastFixation[0]+self.height, self.lastFixation[1]:self.lastFixation[1]+self.width]

    def dumpFixationsToMat(self, savePath):
        fixationList = np.fliplr(self.fixationList).astype(np.float64) # flip array since save format is [horz_coord, vert_coord]
        sio.savemat(savePath, {'fixations': fixationList})


class FixationHistory:
    CALI_MAT = np.asarray(
        [[1.8/0.00112, 0, 4656/2],
         [0, 1.8/0.00112, 3496/2],
         [0, 0, 1]]
    )
    RESCALE_FACTOR = 5

    def __init__(self, path):
        with open(path, 'rb') as fi:
            self.motor_history = np.asarray(pickle.load(fi))

        # accumulate motor commands to get fixation history
        self.fixt_history = self.motor_history.cumsum(axis=0)

        # relative to current fixation
        self.fixt_history_rel = self.fixt_history - self.fixt_history[-1, :]

        # convert polar to cartesian
        self.fixt_history_sphere = []  # on unit sphere
        for p_deg, t_deg in self.fixt_history_rel:
            p_rad, t_rad = p_deg/180*np.pi, t_deg/180*np.pi
            x = np.cos(t_rad) * np.sin(p_rad)
            y = np.sin(t_rad)
            z = np.cos(t_rad) * np.cos(p_rad)
            self.fixt_history_sphere.append((x, y, z))

    def getFixationHistoryMap(self, h, w, settings):
        fixHistMap = np.zeros((h, w), dtype=np.float32)
        cali_mat_inv = np.linalg.inv(self.CALI_MAT)
        min_cos_sim = np.cos(settings.iorSizeDeg/2/180*np.pi)
        for x, y, z in self.fixt_history_sphere:
            # decay first
            fixHistMap -= 1/settings.iorDecayRate
            fixHistMap = np.fmax(fixHistMap, np.zeros((h, w)))

            # compute new IoR region
            for i in fixHistMap.shape[0]:
                for j in fixHistMap.shape[1]:
                    homo_coord = np.asarray([j*self.RESCALE_FACTOR, i*self.RESCALE_FACTOR, 1])
                    ray = np.matmul(cali_mat_inv, homo_coord)
                    normalized = ray/np.linalg.norm(ray)
                    cos_sim = np.dot(normalized, np.array([x, y, z]))
                    if cos_sim >= min_cos_sim:
                        # TODO based on distance
                        fixHistMap[i, j] = 1

        return fixHistMap
