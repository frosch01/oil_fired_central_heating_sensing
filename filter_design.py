#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, lfilter, freqz
from scipy.ndimage.interpolation import shift

class butter_lowpass:
    def __init__(self, fcut, fsamp, order=5):
        fnyq = 0.5 * fsamp
        self.b, self.a = butter(order, fcut / fnyq, btype='low')
        self.fcut = fcut
        self.fsamp = fsamp
        self.x = np.full(len(self.b), 0.)
        self.y = np.full(len(self.a), 0.)
        
    def filter_data(self, data):
        # Low pass filter as defined in __init__
        filtered = lfilter(self.b, self.a, data)
        # Determine gradient for each point
        grad = (filtered[1:] - filtered[:-1]) * self.fsamp
        grad = np.insert(grad, 0, grad[0])
        # Apply gradient to values to compensate from sensor inertness
        return filtered + 37 * grad
    
    def step(self, x):
        #a[0]*y[n] = b[0]*x[n] + b[1]*x[n-1] + ... + b[nb]*x[n-nb]
        #                      - a[1]*y[n-1] - ... - a[na]*y[n-na]
        # Execure low pass filter
        self.x = shift(self.x, 1, cval = x)
        self.y = shift(self.y, 1, cval = 0.)
        self.y[0] = (np.sum(self.b * self.x) - np.sum(self.a * self.y)) / self.a[0]
        # apply gradient
        return self.y[0] + 37 * (self.y[0] - self.y[1]) * self.fsamp
        
    def filter_step(self, data):
        out = np.full(len(data), 0.)
        for num, val in enumerate(data):
            out[num] = self.step(val)
        return out

xy_last = (None, None)
def gradient(x, y):
    if xy_last[0]:
        return (y - xy_last[1]) / (x - xy_last[0])
        xy_last = (x, y)
    else:
        return 0

def run():
    # Sample rate and desired cutoff frequencies (in Hz).
    fs = 1.0
    cut = 0.1

    # Filter a temperature signal.
    in_stream = open("heating.log", "r")
    line_list = in_stream.readlines(100)
    time_list  = []
    therm_list = []
    while line_list:
        for line in line_list:
            val_list = line.split()
            time_list.append(float(val_list[0]))
            therm_list.append(float(val_list[1]))
        line_list = in_stream.readlines(100)
    t = np.array(time_list) - time_list[0]
    x = np.array(therm_list)
    
    plt.figure(1)
    plt.clf()
    plt.plot(t, x, label='Noisy signal')

    fs = (len(t)-1) / (t[-1] - t[0]) # 0.937
    cut = 0.02
    filt = butter_lowpass(cut, fs, 3)
    y1 = filt.filter_data(x)
    y2 = filt.filter_step(x)
    
    plt.plot(t[100:], y1[100:], label='Filtered signal using lfilter')
    plt.plot(t[100:], y2[100:], label='Filtered signal using step')
    plt.xlabel('time (seconds)')
    plt.grid(True)
    plt.axis('tight')
    plt.legend(loc='upper left')

    plt.show()
run()
