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

    def take_data_roll(self, avg_all_rows=False):
        # 
        # The assumption of for this method is that there is a triangle on the FB data channel
        # this method will then roll the error data to the next zero value in the FB.
        # it will put the roll value from the first column and use that for the rest of the
        # columns  
        data = self.c.getNewData(minimumNumPoints=self.pointsPerSlice, exactNumPoints=True)
        fb = np.array(data[:, :, :, 1])
        err = np.array(data[:, :, :, 0])
        #Determine how far to roll for each element in the 2D array of time streams
        for i in range(fb.shape[0]):
            for j in range(fb.shape[1]):
                # Check if there is a feedback value to roll too. Just print to console about the issue. 
                if(np.all(fb[i,j,:] == fb[i,j,0])):
                    raise self.FeedBackException("FB value is constant, this will cause erratic behavior in take_data_roll(). C={}, R={}".format(i, j))
                nsamp_roll = -fb[i, j, :].argmin()
                fb[i, j, :] = np.roll(fb[i, j, :], nsamp_roll)
                err[i, j, :] = np.roll(err[i, j, :], nsamp_roll)

        # If the average all rows has been passed in, return the average over all of the rows
        if(avg_all_rows):
            return np.average(fb, axis=1), np.average(err, axis=1)
        else:
            return fb, err
        
    #
    #
    #
    def take_average_data_roll(self, avg_all_rows=False):

        if(self.averages <= 1):
            data = self.take_data_roll(avg_all_rows=avg_all_rows)
            return data
        else:
            avg_cnt = self.averages - 1
            data = self.take_data_roll(avg_all_rows=avg_all_rows)
            for i in range(avg_cnt):
                data = np.add(self.take_data_roll(avg_all_rows=avg_all_rows), (data))

            return data[0]/self.averages, data[1]/self.averages


    class FeedBackException(Exception):
        pass
