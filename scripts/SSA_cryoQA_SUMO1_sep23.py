#################################################################################
#
# Written by: Johnathon Gard, Erin Maloney
# Purpose: SSA screening script,
#
# September 2023
#
#################################################################################


# System Level Imports
import sys
import numpy as np
import pandas as pd
import time

# Installed Package Imports
import named_serial # Can be sourced from multiple repos at NIST
#from statsmodels.nonparametric.smoothers_lowess import lowess
from scipy.signal import butter, lfilter, freqz

# Local Imports

# TODO: local imports (to come)


class SSA:
    #initializes class - WHAT STAY WHAT GO?
    def __init__(self, which_columns = [0]):
        self.save_all_data_flag = False
        self.number_columns = len(which_columns)
        self.number_rows = 4
        self.blines = np.zeros(self.number_columns)
        self.baselines_std = np.zeros(self.number_columns)
        self.baselines_range = np.zeros(self.number_columns)
        self.baselines_average = np.zeros(self.number_columns)
        self.baselines_SNR = np.zeros(self.number_columns)

        self.icmin = np.zeros(self.number_columns)
        self.icmax = np.zeros(self.number_columns)
        self.icmod_max = np.zeros(self.number_columns)

        self.icmin_xy = np.zeros((self.number_columns, 2))
        self.icmax_xy = np.zeros((self.number_columns, 2))
        self.icmod_max_xy = np.zeros((self.number_columns, 2))

        self.safb_bias_phase2 = np.zeros(self.number_columns)
        self.sq1_row_bias_phase2 = np.zeros(self.number_rows)
        self.sabias_phase2 = np.zeros(self.number_columns)
        self.safb_m = np.zeros((self.number_columns, 2))
        self.sain_m = np.zeros((self.number_columns, 2))
        self.sq1_row_fb_m = np.zeros((self.number_columns, 2))

        self.chip_id = np.zeros(self.number_columns, dtype=object)
        self.chip_id.fill('')
        self.icmax.fill(None)
        self.qa_name = None
        
        today = time.localtime()
        self.date = str(today.tm_year) + '_' + str(today.tm_mon) + '_' + str(today.tm_mday)
        return
    
    def tower_set_dacVoltage():
        return
    
    # runs dac voltage from set start value, often 0, to set end value
    def ramp_to_voltage(self, channel, to_dac_value, from_dac_value=0, slew_rate=8, report=True):
        if report:
            print(('Ramp chanel ', channel, ' from ', from_dac_value, +  ' to ', to_dac_value))

        bias = from_dac_value

        if to_dac_value == from_dac_value:
            up = False
            down = False
            dac_step = 0
        elif (to_dac_value - from_dac_value) > 0:
            dac_step = 2**slew_rate
            up = True
            down = False
        else:
            dac_step = -(2**slew_rate)
            up = False
            down = True
        
        if up:
            while (bias + dac_step) < to_dac_value:
                bias = bias + dac_step
                self.tower_set_dacVoltage(channel, bias)
            
        if down:
            while (bias + dac_step) > to_dac_value:
                bias = bias + dac_step
                self.tower_set_dacVoltage(channel, bias)
        
        bias = to_dac_value
        self.tower_set_dacVoltage(channel, bias)
    
    #resets all values to zero or default
    def zero_everything(self):
        for i in range(8):
            self.tower_set_dacVoltage(i, 0)
    
    #name of user
    def set_qa_name(self, qa_name):
        self.qa_name = qa_name    
   
    # determines background noise level, assumes no rows active to start
    def get_baselines(self, bias=0, averages=10):
        for i in range(8):
            self.ramp_to_voltage(i, bias, report=False)
        
        fb,err = self.daq.take_average_data()
        fb = np.mean(fb, 1)
        err = np.mean(err, 1)
        self.baselines_std = np.std(err, 1)
        self.baselines_range = np.max(err, 1) - np.min(err, 1)
        self.baselines_average = np.average(err, 1)
        self.baselines_SNR = self.baselines_average / self.baselines_std

        # TODO: print out for outlires - CHECK value for baseline and decide if we want it at all
        for col in range(len(self.baselines_std)):
            if self.baselines_std[col] > 20:
                print('The standard deviation for col: ' + str(col) + ' is high: ' + str(self.baselines_std[col]))
    

    
    #
    def sq1_bias_sweeper(self):
        start_time = time.time()
        step_time= 0
        print('Sarting row sweep of :/t' + str(self.number_steps) + ' steps\n')
        print()
        return
    
    #takes bias sweep results, picks off Icmin when peaks occur, picks vmod and icmax when modulation amplitude is max
    def calculate_ics():
        return
    
    # send triangle down fb to get baselines, sweep bias, pick off icmin, icmax and vmod, get mfb
    def phase1():
        return

    #send triangle down input to get min
    def phase2():
        return
       
    #saves data results
    def save_npz():
        return

    #TODO: what to do about chip IDs?

    



    
