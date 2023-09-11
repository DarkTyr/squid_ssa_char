import numpy as np
from nasa_client import easyClient


class Daq:

    def __init__(self, tri_period=512, averages=10):
        self.c = easyClient.EasyClient(clockmhz=125)
        self.c.setupAndChooseChannels()
        self.pointsPerSlice = tri_period
        self.averages = averages

    def take_average_data(self):
        #
        # Gathers data from easyClient and averages one period of it over as many periods as possible in the data.
        # Returns two arrays: fb, err
        #
        data = self.c.getNewData(minimumNumPoints=self.pointsPerSlice * self.averages, exactNumPoints=True)

        slices = np.int_(data.shape[2] / self.pointsPerSlice)
        start = 0
        end = start + self.pointsPerSlice

        i = 0
        fb = np.zeros((self.c.ncol, self.c.nrow, self.pointsPerSlice))
        err = np.zeros((self.c.ncol, self.c.nrow, self.pointsPerSlice))

        while i != slices:
            for col in range(self.c.ncol):
                fb[col] += data[col, :, start:end, 1]
                err[col] += data[col, :, start:end, 0]
            start += self.pointsPerSlice
            end += self.pointsPerSlice
            i += 1

        return fb / slices, err / slices

    def take_data(self):
        #
        #
        data = self.c.getNewData(minimumNumPoints=self.pointsPerSlice, exactNumPoints=True)

        fb = np.zeros((self.c.ncol, self.c.nrow, self.pointsPerSlice))
        err = np.zeros((self.c.ncol, self.c.nrow, self.pointsPerSlice))

        fb = data[:, :, :, 1]
        err = data[:, :, :, 0]

        return fb, err

    def take_average_data(self):
        # 
        # The assumption of for this method is that there is a triangle on the FB data channel
        # this method will then roll the error data to the next zero value in the FB.
        # it will pu tthe roll value from the first column and use that for the rest of the
        # columns  
        data = self.c.getNewData(minimumNumPoints=self.pointsPerSlice, exactNumPoints=True)
        fb = np.array(data[:, :, :, 1])
        err = np.array(data[:, :, :, 0])
        nsamp_roll = -fb[0, :].argmin()
        fb = np.roll(fb, nsamp_roll)
        err = np.roll(err, nsamp_roll)

        return fb, err

