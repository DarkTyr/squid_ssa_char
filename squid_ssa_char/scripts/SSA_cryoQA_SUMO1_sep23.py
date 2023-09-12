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

# Installedd Package Imports
import named_serial # Can be sourced from multiple repos at NIST
#from statsmodels.nonparametric.smoothers_lowess import lowess
from scipy.signal import butter, lfilter, freqz

# Local Imports
from squid_ssa_char.modules import ssa_data_class
from squid_ssa_char.modules import daq
from squid_ssa_char.modules import towerchannel


class SSA:
    #initializes class - WHAT STAY WHAT GO?
    def __init__(self):
        self.save_all_data_flag = False
        self.number_rows = 4
        
        self.ncol = 8 #placeholder for number of columns
        self.data = np.zeros(self.ncol)
        for i in range(self.ncol):
            self.data[i] = ssa_data_class.SSA_Data_Class()
        
        today = time.localtime()
        self.date = str(today.tm_year) + '_' + str(today.tm_mon) + '_' + str(today.tm_mday)
        
        self.serialport = named_serial.Serial(port='rack', shared=True)
        self.tower = towerchannel.TowerChannel(cardaddr=0, column=0, serialport="tower")

        #for now variables until happy with configs
        self.num_steps = 256
        self.icmin_pickoff = 4
        
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
    

    
    #TODO what the heck is this and can we disect it and put into calc_ics and ramp2voltage?
    def sq1_bias_sweeper(self):
        start_time = time.time()
        step_time= 0
        print('Sarting row sweep of :/t' + str(self.number_steps) + ' steps\n')
        print()
        return
    
    #takes bias sweep results, picks off Icmin when peaks occur, picks vmod and icmax when modulation amplitude is max
    def calculate_ics(self):
        for col in range(self.ncol):
            have_icmin = False
            for sweep_point in range(self.num_steps):
                if (have_icmin == False) and (sweep_point != 0):
                    #TODO update this situation - use sigma dependence
                    #TODO why cant it see dac_ic_min?
                    #TODO update to be our data - row_...mod is the abs of the diff btwn min(err) and max(err) at sweep_point
                    if self.row_sweep_average_mod[col] >= self.icmin_pickoff*self.baselines_range[col]:
                        self.data[col].dac_ic_min = self.row_sweep_tower_values[sweep_point]
                        
                        have_icmin = True
                
                #TODO why cant it see dac_ic_max
                #TODO get row_sweep_tower_values to align with our current setup
                if have_icmin == True:
                    self.data[col].dac_ic_max = self.row_sweep_tower_values[np.argmax(self.row_sweep_average_mod[col])]

                else:
                    self.data[col].dac_ic_min = int(2**16 -1)
                    self.data[col].dac_ic_max = 0

    
    # send triangle down fb to get baselines, sweep bias, pick off icmin, icmax and vmod, get mfb
    def phase1(self):
        self.zero_everything()
        self.get_baselines()
        #TODO here is where the ramp2voltage vs sq1biassweeper choice gottta be made
        self.calculate_ics()

    #send triangle down input to get min
    def phase2():
        return
       
    #saves data results - john currently has this as part of one of the modules 
    def save_npz():
        return

    



    
