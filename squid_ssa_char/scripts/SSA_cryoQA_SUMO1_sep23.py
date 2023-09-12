#################################################################################
#
# Written by: Johnathon Gard, Erin Maloney
# Purpose: SSA screening script,
#
# September 2023
#
#################################################################################


# System Level Imports
# import sys
import argparse
import textwrap
import numpy as np
# import pandas as pd
import time

# Installed Package Imports
import named_serial # Can be sourced from multiple repos at NIST
#from statsmodels.nonparametric.smoothers_lowess import lowess
# from scipy.signal import butter, lfilter, freqz

# Local Imports
from squid_ssa_char.modules import load_conf_yaml, ssa_data_class, daq, towerchannel

class SSA:
    #initializes class - WHAT STAY WHAT GO?
    def __init__(self, sys_conf, test_conf):
        # Configuration Dictionaries loaded from External Config Files
        self.sys_conf = sys_conf
        self.test_conf = test_conf
        self.verbosity = 0
        self.save_all_data_flag = False  # TODO: Should this be in the config? - Erin says yes, this is a leftover from day1
        
        self.number_rows = test_conf['test_globals']['n_rows']
        self.sel_col = test_conf['test_globals']['columns'] # Array of the selected columns
        self.ncol = len(test_conf['test_globals']['columns'])   # length of the selectred columns
        
        self.data = self.ncol*[ssa_data_class.SSA_Data_Class()] #TODO why is this called here then again in the loop? Doesnt this make ncol of the same class reference
        for i in range(self.ncol):                                  #then re-assigns them to different class calls in the loop?
            self.data[i] = ssa_data_class.SSA_Data_Class()
        
        today = time.localtime()
        self.date = str(today.tm_year) + '_' + str(today.tm_mon) + '_' + str(today.tm_mday)
        
        self.serialport = named_serial.Serial(port='rack', shared=True)
        self.tower = towerchannel.TowerChannel(cardaddr=0, column=0, serialport="tower")
        self.daq = daq.Daq() # Defaults are fine, will reassign later

        #for now variables until happy with configs
        # TODO: Should pull these from the config when the test phase is called now
        self.num_steps = self.test_conf['phase0_0']['bias_sweep_npoints']
        self.icmin_pickoff = 4

        return

    #connects to the tower and sets the dac voltage bias for each channel  
    def tower_set_dacVoltage(self, channel, dac_value):
        # reach in and assign the proper channel to the class
        tower_map = self.sys_conf['col_map']['col'+str(channel)]['SA_Bias']
        tower_card_ref = self.sys_conf['tower'][tower_map['tower_card']]
        self.tower.bluebox.address = tower_card_ref['addr']
        self.tower.bluebox.channel = tower_map['tower_col_n']
        if(self.verbosity > 2):
            print('    tower_set_dacVoltage(channel={}, dac_value={})'.format(channel, dac_value))
            print('        self.tower.bluebox.address = {}'.format(self.tower.bluebox.address))
            print('        self.tower.bluebox.channel = {}'.format(self.tower.bluebox.channel))
        # Now use the class to send the data to the tower
        self.tower.set_value(dac_value)
    
    # runs dac voltage from set start value, often 0, to set end value
    #TODO account for channel? currently part of towerSetVoltage call but TowerSetVoltage and TowerChannel not set up to include channel?
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
    #TODO also need to align this with TowerSetVolgtage - how to handle channel assignment
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
        self.baselines_std = np.std(err, 1)
        self.baselines_range = np.max(err, 1) - np.min(err, 1)
        self.baselines_average = np.average(err, 1)
        self.baselines_SNR = self.baselines_average / self.baselines_std

        # TODO: print out for outliers - CHECK value for baseline and decide if we want it at all
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
                    #TODO update this situation - use sigma dependence? or rms?
                    #TODO update to be our data - row_...mod is the abs of the diff btwn min(err) and max(err) at sweep_point
                    if self.row_sweep_average_mod[col] >= self.icmin_pickoff*self.baselines_range[col]:
                        self.data[col].dac_ic_min = self.row_sweep_tower_values[sweep_point]
                        
                        have_icmin = True
                
                #TODO get row_sweep_tower_values to align with our current setup
                if have_icmin == True:
                    self.data[col].dac_ic_max = self.row_sweep_tower_values[np.argmax(self.row_sweep_average_mod[col])]

                else:
                    self.data[col].dac_ic_min = int(2**16 -1)
                    self.data[col].dac_ic_max = 0

    
    # send triangle down fb to get baselines, sweep bias, pick off icmin, icmax and vmod, get mfb
    #TODO Thoughts:
        #Sq1BiasSweeper in orig setsup the time remaining/status printout, takes in data from take_avg_data, rolls it, calculates row_sweep_avg
            #_max, _min and _mod (range) these are used in calc_ics. Do that here instead or do in own version of biasSweeper?
        #Also, do we want the print out at all?
        #Do we want to do Mfb here (orig 2_0) then only habe one phase for triangle on FB and one for triangle on IN or do two phases for FB?
    def phase1(self):
        self.zero_everything()
        self.get_baselines()

        fb,err = self.daq.take_average_data_roll()
        
        #TODO here is where the ramp2voltage vs sq1biassweeper choice gottta be made
        self.calculate_ics()

    #send triangle down input to get min
    def phase2():
        return
       
    #saves data results - john currently has this as part of the dataclass module  
    def save_npz():
        return

    

HELP_TEXT = '''\
This is the main SQUID Series Array Testing and Quality Assurance Data Script


Currently a work in progress
'''
if (__name__ == '__main__'):
    # Setup the flag and argument parser for the script
    parser = argparse.ArgumentParser(
        prog='config_check',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(HELP_TEXT))
    
    parser.add_argument('-s', '--sys_file_path', 
                        help='path to the system_config file')
    parser.add_argument('-c', '--config_file_path', 
                        help='path to config file')
    parser.add_argument('-v', '--verbosity', 
                        help='Set terminal debugging verbositiy',
                        action='count',
                        default=0)
    parser.add_argument('-i', '--interactive', 
                        help='Drop into Interactive mode after setting up classes',
                        action='store_true')
    args = parser.parse_args()

    conf_parse = load_conf_yaml.Load_Conf_YAML(args.config_file_path, args.sys_file_path, args.verbosity)
    sys_conf = conf_parse.read_system_config()
    test_conf = conf_parse.read_test_config()

    test = SSA(sys_conf, test_conf)
    test.verbosity = args.verbosity

