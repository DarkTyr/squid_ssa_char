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
import tqdm
#from statsmodels.nonparametric.smoothers_lowess import lowess
# from scipy.signal import butter, lfilter, freqz

# Local Imports
from squid_ssa_char.modules import load_conf_yaml, ssa_data_class, daq, towerchannel

class SSA:
    '''
    #initializes class - WHAT STAY WHAT GO?
    '''
    def __init__(self, sys_conf, test_conf):
        # Configuration Dictionaries loaded from External Config Files
        self.sys_conf = sys_conf
        self.test_conf = test_conf
        self.verbosity = 0
        self.save_all_data_flag = False  # TODO: Should this be in the config? - Erin says yes, this is a leftover from day1
        
        self.number_rows = test_conf['test_globals']['n_rows']
        self.sel_col = test_conf['test_globals']['columns'] # Array of the selected columns
        self.ncol = len(test_conf['test_globals']['columns'])   # length of the selectred columns
        
        self.data = [ssa_data_class.SSA_Data_Class()]
        for i in range(self.ncol - 1):
            self.data.append(ssa_data_class.SSA_Data_Class())
        
        today = time.localtime()
        self.date = str(today.tm_year) + '_' + str(today.tm_mon) + '_' + str(today.tm_mday)
        
        self.serialport = named_serial.Serial(port='rack', shared=True)
        self.tower = towerchannel.TowerChannel(cardaddr=0, column=0, serialport="tower")
        self.daq = daq.Daq() # Defaults are fine, will reassign later
        # TODO: should we perform book keeping here automatically or have a method to call?

    #connects to the tower and sets the dac voltage bias for each channel  
    def set_sa_bias_voltage(self, channel, dac_value):
        # reach in and assign the proper channel to the class
        tower_map = self.sys_conf['col_map']['col'+str(channel)]['SA_Bias']
        tower_card_ref = self.sys_conf['tower'][tower_map['tower_card']]
        self.tower.bluebox.address = tower_card_ref['addr']
        self.tower.bluebox.channel = tower_map['tower_col_n']
        if(self.verbosity > 2):
            print('    set_sa_bias_voltage(channel={}, dac_value={})'.format(channel, dac_value))
            print('        self.tower.bluebox.address = {}'.format(self.tower.bluebox.address))
            print('        self.tower.bluebox.channel = {}'.format(self.tower.bluebox.channel))
        # Now use the class to send the data to the tower
        self.tower.set_value(dac_value)
    
    # runs dac voltage from set start value, often 0, to set end value
    # TODO: This ramps a single col to a set point, better to loop all col for each change in value?
    def ramp_to_voltage(self, channel, to_dac_value, from_dac_value=0, slew_rate=8):
        if self.verbosity > 0:
            print('ramp_to_voltage: Channel={}, from={}, to={}'.format(channel, from_dac_value, to_dac_value))

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
                self.set_sa_bias_voltage(channel, bias)
            
        if down:
            while (bias + dac_step) > to_dac_value:
                bias = bias + dac_step
                self.set_sa_bias_voltage(channel, bias)
        
        bias = to_dac_value
        self.set_sa_bias_voltage(channel, bias)
    
    #resets all values to zero or default
    def zero_everything(self):
        for i in self.sel_col:
            self.set_sa_bias_voltage(i, 0)
    
    #name of user
    def set_qa_name(self, qa_name):
        self.qa_name = qa_name    
   
    # determines background noise level, assumes no rows active to start
    def get_baselines(self, bias=0):
        for i in self.sel_col:
            self.ramp_to_voltage(i, bias)
        
        time.sleep(self.test_conf['test_globals']['bias_change_wait_ms'] / 1000.0)

        fb, err = self.daq.take_average_data()
        
        for col in range(self.ncol):
            self.data[col].baselines_std = np.std(err[self.sel_col[col]])
            self.data[col].baselines_range = np.max(err[self.sel_col[col]]) - np.min(err[self.sel_col[col]])
            self.data[col].baselines_average = np.average(err[self.sel_col[col]])
            self.data[col].baselines_SNR = self.data[col].baselines_average/self.data[col].baselines_std
            self.data[col].baselines_trace = err[self.sel_col[col]]
        

        # TODO: print out for outliers - CHECK value for baseline and decide if we want it at all
        # for col in range(len(self.baselines_std)):
        #     if self.baselines_std[col] > 20:
        #         print('The standard deviation for col: ' + str(col) + ' is high: ' + str(self.baselines_std[col]))
    
    def calculate_ics(self):
        '''takes bias sweep results, picks off Icmin when peaks occur, picks vmod and icmax when modulation amplitude is max'''
        for col in self.data:
            # For finding Ic_min take the std of the traces at each bias point
            vphi_std = np.std(col.phase0_0_vphis, axis=1)

            # find all of the indexs less than n times the std, and take the greatest index
            icmin_idx = np.where(vphi_std < col.baselines_std * self.test_conf['phase0_0']['icmin_pickoff'])[-1][-1]
            
            # If the found index is the last point in the sweep array, we really didn't find the Ic_min
            # so set it to the max DAC value the system can have
            if (icmin_idx == (len(col.dac_sweep_array) - 1)):
                col.dac_ic_min = 2**16 - 1
            else:
                col.dac_ic_min = col.dac_sweep_array[icmin_idx]

            
            # Determine Ic_max based on Vmod depths
            icmax_idx = col.phase0_0_vmod_sab.argmax()
            
            if (icmax_idx == (len(col.dac_sweep_array) - 1)):
                col.dac_ic_max = 0
            else:
                col.dac_ic_max = col.dac_sweep_array[icmax_idx]

    def bookkeeping(self):
        '''This will copy values from the config files to the SSA data structures'''
        for idx in range(self.ncol):
            self.data[idx].qa_name = self.test_conf['info']['user']
            self.data[idx].chip_id = self.test_conf['info']['chip_ids'][idx]

    # send triangle down fb to get baselines, sweep bias, pick off icmin, icmax and vmod, get mfb
    #TODO Thoughts:
        #Sq1BiasSweeper in orig setsup the time remaining/status printout, takes in data from take_avg_data, rolls it, calculates row_sweep_avg
            #_max, _min and _mod (range) these are used in calc_ics. Do that here instead or do in own version of biasSweeper?
        #Also, do we want the print out at all?
        #Do we want to do Mfb here (orig 2_0) then only habe one phase for triangle on FB and one for triangle on IN or do two phases for FB?
    def phase0_0(self):
        '''
        Sweep SQUID SSA Bias and extract ADC_min, ADC_max, and ADC_modulation depth
        The units will be left in ADC units reported by DASTARD
        '''
        # gather variables from configs
        phase_conf = self.test_conf['phase0_0']
        sa_bias_sweep_val = np.linspace(phase_conf['bias_sweep_start'], 
                                        phase_conf['bias_sweep_end'], 
                                        phase_conf['bias_sweep_npoints'],
                                        dtype=np.int32) # start, stop, num
        
        #used to set up proper data structure size, calculate the number of points in the full triangle response
        npts_data = (2**phase_conf['crate']['tri_steps'])*(phase_conf['crate']['tri_step_size'])*(2**phase_conf['crate']['tri_dwell'])

        # Set the DAQ to appropriate values 
        self.daq.pointsPerSlice = npts_data
        self.daq.averages = phase_conf['n_avg']

        #initiates data storage arrays through data classes
        for i in self.data:
            i.dac_sweep_array = sa_bias_sweep_val
            i.sa_bias_start = phase_conf['bias_sweep_start']
            i.sa_bias_stop = phase_conf['bias_sweep_end']
            i.phase0_0_vphis = np.zeros((phase_conf['bias_sweep_npoints'], npts_data))
            i.phase0_0_vmod_max = np.zeros(phase_conf['bias_sweep_npoints'])
            i.phase0_0_vmod_min = np.zeros(phase_conf['bias_sweep_npoints'])
            i.phase0_0_vmod_sab = np.zeros(phase_conf['bias_sweep_npoints'])

        # Zero all of the columns and then grab the baseline data
        self.zero_everything()
        self.get_baselines()

        # Assign the starting point for the bias sweep (same from config and sa_bias_sweep_val)
        # This will then be used as the previous value for the ramp_to_voltage call
        previous_bias = phase_conf['bias_sweep_start']

        # Main outter for loop wrapped with tqdm class to display a progress bar and estimated time
        for sweep_point in tqdm.tqdm(range(phase_conf['bias_sweep_npoints'])):
            
            # Go thru the columns and ramp the voltage to the desired value form the previous value
            for col in self.sel_col:
                self.ramp_to_voltage(col, sa_bias_sweep_val[sweep_point], previous_bias)         

            # Sleep to let system transient settle out before taking data
            time.sleep(phase_conf['bias_change_wait_ms'] / 1000.0)

            # Take data that has been rolled and then averaged accross all of the rows
            _, err = self.daq.take_average_data_roll(avg_all_rows=True)
            
            # Move the gathered data to appropriate arrays and calculate min, max, values
            for col in self.sel_col:
                self.data[col].phase0_0_vphis[sweep_point] = err[self.sel_col[col]]
                self.data[col].phase0_0_vmod_max[sweep_point] = np.max(err[self.sel_col[col]])
                self.data[col].phase0_0_vmod_min[sweep_point] = np.min(err[self.sel_col[col]])
                self.data[col].phase0_0_vmod_sab[sweep_point] = np.abs(self.data[col].phase0_0_vmod_max[sweep_point] - self.data[col].phase0_0_vmod_min[sweep_point])
            
            # the current sweep bias value now becomes the previous value
            previous_bias = sa_bias_sweep_val[sweep_point]

        # Calc ics will eventually be called here when ready.
        # self.calculate_ics()

    def phase0_1(self):
        return
    #send triangle down input to get min
    def phase1_0():
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

