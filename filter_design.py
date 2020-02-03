#!/usr/bin/env python3
"""A low pass filter based on scipy optimized on filtering the temperature values from sensors
mounted to an oil based rocket burner."""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, lfilter, lfilter_zi
from scipy.ndimage.interpolation import shift

class therm_sens_filter:
    def __init__(self, fcut, fsamp, order, gradient_factor):
        fnyq = 0.5 * fsamp
        self.b, self.a = butter(order, fcut / fnyq, btype='low')
        self.fcut = fcut
        self.fsamp = fsamp
        self.x = np.full(len(self.b), 0.)
        self.y = np.full(len(self.a), 0.)
        self.gradient_factor = gradient_factor
        self.init = False

    def filter_data(self, data):
        # Low pass filter as defined in __init__, recognizing initial value
        zi = lfilter_zi(self.b, self.a)
        filtered, zo = lfilter(self.b, self.a, data, zi=zi*data[0])
        # Determine gradient for each point
        grad = (filtered[1:] - filtered[:-1]) * self.fsamp
        grad = np.insert(grad, 0, grad[0])
        # Apply gradient to values to compensate from sensor inertness
        return filtered + self.gradient_factor * grad

    def step(self, x):
        #a[0]*y[n] = b[0]*x[n] + b[1]*x[n-1] + ... + b[nb]*x[n-nb]
        #                      - a[1]*y[n-1] - ... - a[na]*y[n-na]
        if not self.init:
            self.x = np.full(len(self.b), float(x))
            self.y = np.full(len(self.a), float(x))
            self.init = True

        # Execute low pass filter
        self.x = shift(self.x, 1, cval=x)
        self.y = shift(self.y, 1, cval=0.)
        self.y[0] = (np.sum(self.b * self.x) - np.sum(self.a * self.y)) / self.a[0]
        # apply gradient
        return self.y[0] + self.gradient_factor * (self.y[0] - self.y[1]) * self.fsamp

    def filter_step(self, data):
        out = np.full(len(data), 0.)
        for num, val in enumerate(data):
            out[num] = self.step(val)
        return out

    def plot(self, data):
        time = np.linspace(0, len(data) / self.fsamp, len(data), endpoint=True)
        filtered = self.filter_data(data)
        plt.figure(1)
        plt.clf()
        plt.plot(time, data, label='Noisy signal')
        plt.plot(time, filtered, label='Filtered signal')
        plt.xlabel('time (seconds)')
        plt.grid(True)
        plt.axis('tight')
        plt.legend(loc='upper left')
        plt.show()

if __name__ == "__main__":
    # Sample rate and desired cutoff frequencies (in Hz).
    fs = 1.0
    cut = 0.1

    # Filter a temperature signal.
    in_stream = open("heating.log", "r")
    line_list = in_stream.readlines(100000)
    time_list = []
    therm_list = []
    line_cnt = 0
    while line_list:
        for line in line_list:
            val_list = line.split()
            time_list.append(float(val_list[0]))
            therm_list.append(float(val_list[1]))
            line_cnt += 1
        print("Read {} lines".format(line_cnt))
        line_list = in_stream.readlines(100000)
    t = np.array(time_list) - time_list[0]
    x = np.array(therm_list)

    fs = (len(t)-1) / (t[-1] - t[0]) # 0.937
    cut = 0.02
    filt = therm_sens_filter(cut, fs, 3, 37)
    filt.plot(x)
