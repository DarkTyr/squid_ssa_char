#################################################################################
#
# Written by: Johnathon Gard, Erin Maloney
# Purpose: SSA screening script. Data is stored for later processing. Only 
# Icmax and Icmin are picked off all other values will be found in processing.
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
import IPython
import named_serial # Can be sourced from multiple repos at NIST
import tqdm

# Local Imports
from squid_ssa_char.modules import load_conf_yaml, ssa_data_class, daq, towerchannel

class SSA:
    '''
    #initializes class
    '''
    def __init__(self, system_config_path, test_config_path, verbosity):
        '''
        Initializes the SSA class
        '''
        # Configuration Dictionaries loaded from External Config Files
        self._system_config_path = system_config_path
        self._test_config_path = test_config_path
        self._conf_parser = load_conf_yaml.Load_Conf_YAML(test_config_path, system_config_path, verbosity)
        self.sys_conf = self._conf_parser.read_system_config()
        self.test_conf = self._conf_parser.read_test_config()
        self.verbosity = verbosity        
        self.number_rows = self.test_conf['test_globals']['n_rows']
        self.sel_col = self.test_conf['test_globals']['columns'] # Array of the selected columns
        self.ncol = len(self.test_conf['test_globals']['columns'])   # length of the selectred columns
        
        self.data = [ssa_data_class.SSA_Data_Class()]
        for i in range(self.ncol - 1):
            self.data.append(ssa_data_class.SSA_Data_Class())
        
        today = time.localtime()
        self.date = '{0:04d}_'.format(today.tm_year) + \
                    '{0:02d}_'.format(today.tm_mon) + \
                    '{0:02d}_'.format(today.tm_mday) + \
                    '{0:02d}'.format(today.tm_hour) + \
                    '{0:02d}'.format(today.tm_min)
        
        self.bookkeeping()

        self.serialport = named_serial.Serial(port='rack', shared=True)
        self.tower = towerchannel.TowerChannel(cardaddr=0, column=0, serialport="tower")
        self.daq = daq.Daq() # Defaults are fine, will reassign later
        

    #connects to the tower and sets the dac voltage bias for each channel  
    def set_sa_bias_voltage(self, channel, dac_value):
        '''
        Connects to the tower then sets the DAC voltage bias. Needs the desired channel and DAC value passed to it.
        '''
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
    def ramp_to_voltage(self, channel, to_dac_value, from_dac_value=0, slew_rate=8):
        '''
        Ramps the DAC voltage from some start value, which has a defult of 0, to some end value. Needs the desired channel
        and the ending DAC value passed in. The starting DAC value and the slew rate can also be passed but have defaults 
        set (DAC start value = 0 and slew rate = 8)
        '''
        
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
        '''
        Sets the DAC bias voltage to 0 for all columns
        '''
        for i in self.sel_col:
            self.set_sa_bias_voltage(i, 0)
    
    #name of user
    def set_qa_name(self, qa_name):
        '''
        Pass in the initials of the person running the QA system
        '''
        self.qa_name = qa_name    
   
    # determines background noise level, assumes no rows active to start
    def get_baselines(self, bias=0):
        '''
        Ramps the voltage to 0, unless some other value is passed, then stores the data at the desired DAC bias.
        The std, range, average, and signal-to-noise ratio are all calculated and stored for each column at the set DAC bias.
        This is done at bias = 0 to get the background/baseline levels for better accuracy later.
        '''
        
        for i in self.sel_col:
            self.ramp_to_voltage(i, bias)
        
        time.sleep(self.test_conf['test_globals']['bias_change_wait_ms'] / 1000.0)

        fb, err = self.daq.take_average_data()

        print("Baseline Noise Data\n"
            + "Column | "
            + "\tStd Deivation | "
            + "\tRange | "
            + "\tAverage | "
            + "\tStd/Avg SNR |")
        
        for col in range(self.ncol):
            print("{:6d} | ".format(self.data[col].sys.channel_num), end="", flush=True)
            self.data[col].baselines_std = np.std(err[self.sel_col[col]])
            print("\t{:13.3f} | ".format(self.data[col].baselines_std), end="", flush=True)
            self.data[col].baselines_range = np.max(err[self.sel_col[col]]) - np.min(err[self.sel_col[col]])
            print("\t{:5.2f} | ".format(self.data[col].baselines_range), end="", flush=True)
            self.data[col].baselines_average = np.average(err[self.sel_col[col]])
            print("\t{:7.3f} | ".format(self.data[col].baselines_average), end="", flush=True)
            self.data[col].baselines_SNR = self.data[col].baselines_average/self.data[col].baselines_std
            print("\t{:11.3f} | ".format(self.data[col].baselines_SNR), flush=True)
            self.data[col].baselines_trace = err[self.sel_col[col]]
    
    def calculate_ics(self):
        '''takes bias sweep results, picks off Icmin when peaks occur, picks vmod and icmax when modulation amplitude is max'''
        # Print header for usefull stuff to the console
        print("Calculating IC Parameters\n"
            + "Column | "
            + "\tICMax_IDX | "
            + "\tICMin_IDX | "
            + "\tICMax_DAC | "
            + "\tICMin_DAC |")
        for col in self.data:
            print("{:6d} | ".format(col.sys.channel_num), end="", flush=True)

            # Determine Ic_max based on Vmod depths
            icmax_idx = col.phase0_0_vmod_sab.argmax()
            print("\t{:9d} | ".format(icmax_idx), end="", flush=True)

            # For finding Ic_min take the std of the traces at each bias point
            vphi_std = np.std(col.phase0_0_vphis, axis=1)

            # find all of the indices less than n times the std, and take the greatest index. limit to below icmax to avoid rail issues
            if(icmax_idx != 0):
                icmin_idx = np.where(vphi_std[:icmax_idx] < col.baselines_std * self.test_conf['phase0_0']['icmin_pickoff'])[-1][-1]
            else:
                icmin_idx = len(col.dac_sweep_array) - 1
            print("\t{:9d} | ".format(icmin_idx), end="", flush=True)

            # If the found index is the last point in the sweep array, we really didn't find the Ic_min
            # so set it to the max DAC value the system can have
            if (icmin_idx == (len(col.dac_sweep_array) - 1)):
                col.dac_ic_min = 2**16 - 1
            else:
                col.dac_ic_min = col.dac_sweep_array[icmin_idx]
            
            if (icmax_idx == (len(col.dac_sweep_array) - 1)):
                col.dac_ic_max = 0
            else:
                col.dac_ic_max = col.dac_sweep_array[icmax_idx]
            print("\t{:9d} | ".format(col.dac_ic_max), end="", flush=True)
            print("\t{:9d} |".format(col.dac_ic_min), flush=True)

    def bookkeeping(self):
        '''This will copy values from the config files to the SSA data structures. These values will be used to either 
        identify the devices, convert units to base units (uA and mV) and so forth.
        '''
        for idx in range(self.ncol):
            chan_num = int(self.test_conf['test_globals']['columns'][idx])
            self.data[idx].qa_name = self.test_conf['info']['user']
            self.data[idx].chip_id = self.test_conf['info']['chip_ids'][idx]
            self.data[idx].system_name = self.test_conf['info']['system']
            self.data[idx].chip_flavor = self.test_conf['info']['chip_flavor'][idx]
            self.data[idx].SSA_type = self.test_conf['info']['SSA_type'][idx]
            self.data[idx].timestamp = self.date
            self.data[idx].file_name = self.test_conf['info']['chip_ids'][idx] + '_' + \
                self.date + '_chan{0:02}'.format(self.test_conf['test_globals']['columns'][idx])
            self.data[idx].sys.channel_num = self.test_conf['test_globals']['columns'][idx]
            self.data[idx].test_conf_path = self._test_config_path
            self.data[idx].system_conf_path = self._system_config_path
            # Make temp vars to hold info about the card mapping
            sa_bias_card = self.sys_conf['col_map']['col' + str(chan_num)]['SA_Bias']
            input_card = self.sys_conf['col_map']['col' + str(chan_num)]['SA_Input']
            feedback_card = self.sys_conf['col_map']['col' + str(chan_num)]['SA_FB']
            crate_info = self.sys_conf['col_map']['col' + str(chan_num)]['DAQ']
            # Now that we have the map, let us copy things into the data class
            #   Pre-Amp with SA Bias DACs
            self.data[idx].sys.amp_bias_r = self.sys_conf['tower'][sa_bias_card['tower_card']]['bias_R'][int(sa_bias_card['tower_col_n'])]
            self.data[idx].sys.amp_gain = self.sys_conf['tower'][sa_bias_card['tower_card']]['gain_effective'][int(sa_bias_card['tower_col_n'])]
            self.data[idx].sys.amp_dac_vref = self.sys_conf['tower'][sa_bias_card['tower_card']]['dac_ref_v']
            self.data[idx].sys.amp_dac_nbits = self.sys_conf['tower'][sa_bias_card['tower_card']]['dac_nbits']
            self.data[idx].sys.amp_dac_gain = self.sys_conf['tower'][sa_bias_card['tower_card']]['dac_gain']
            #   Feedback Tower Bias Card though the DACs are not user here
            self.data[idx].sys.fb_bias_r = self.sys_conf['tower'][feedback_card['tower_card']]['bias_R'][int(feedback_card['tower_col_n'])]
            self.data[idx].sys.fb_dac_vref = self.sys_conf['tower'][feedback_card['tower_card']]['dac_ref_v']
            self.data[idx].sys.fb_dac_nbits = self.sys_conf['tower'][feedback_card['tower_card']]['dac_nbits']
            self.data[idx].sys.fb_dac_nbits = self.sys_conf['tower'][feedback_card['tower_card']]['dac_gain']
             #   Feedback Tower Bias Card though the DACs are not user here
            self.data[idx].sys.in_bias_r = self.sys_conf['tower'][input_card['tower_card']]['bias_R'][int(input_card['tower_col_n'])]
            self.data[idx].sys.in_dac_vref = self.sys_conf['tower'][input_card['tower_card']]['dac_ref_v']
            self.data[idx].sys.in_dac_nbits = self.sys_conf['tower'][input_card['tower_card']]['dac_nbits']
            self.data[idx].sys.in_dac_nbits = self.sys_conf['tower'][input_card['tower_card']]['dac_gain']    
            #   Crate DAQ Channel ADC
            self.data[idx].sys.daq_adc_nbits = self.sys_conf['crate'][crate_info['card']]['adc_n_bits']
            self.data[idx].sys.daq_adc_vrange = self.sys_conf['crate'][crate_info['card']]['adc_vin_range']
            self.data[idx].sys.daq_adc_gain = self.sys_conf['crate'][crate_info['card']]['input_gain']
            #   Crate DAQ Channel DAC
            self.data[idx].sys.daq_dac_nbits = self.sys_conf['crate'][crate_info['card']]['dac_n_bits']
            self.data[idx].sys.in_dac_vref = self.sys_conf['crate'][crate_info['card']]['dac_vout_range']
            self.data[idx].sys.daq_dac_gain = self.sys_conf['crate'][crate_info['card']]['dac_gain']

    # send triangle down fb to get baselines, sweep bias, pick off icmin, icmax and vmod
    def phase0_0(self):
        '''
        Sweep SQUID SSA Bias and extract ADC_min, ADC_max, and ADC_modulation depth
        The units will be left in ADC units reported by DASTARD
        The sweep end point is in the test config file and is determined by the SSA design
        '''
        # gather variables from configs
        phase_conf = self.test_conf['phase0_0']
        sa_bias_sweep_val = np.linspace(phase_conf['bias_sweep_start'], 
                                        phase_conf['bias_sweep_end'], 
                                        phase_conf['bias_sweep_npoints'],
                                        dtype=np.int32) # start, stop, num
        
        #used to set up proper data structure size, calculate the number of points in the full triangle response
        npts_data = (2**phase_conf['crate']['tri_steps'])*(2**phase_conf['crate']['tri_dwell']) * 2 # mult by two because of triangle no sawtooth

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

        print("Phase0_0 Bias Sweep")
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
            for col in range(self.ncol):
                self.data[col].phase0_0_vphis[sweep_point] = err[self.sel_col[col]]
                self.data[col].phase0_0_vmod_max[sweep_point] = np.max(err[self.sel_col[col]])
                self.data[col].phase0_0_vmod_min[sweep_point] = np.min(err[self.sel_col[col]])
                self.data[col].phase0_0_vmod_sab[sweep_point] = np.abs(self.data[col].phase0_0_vmod_max[sweep_point] - self.data[col].phase0_0_vmod_min[sweep_point])
            
            # the current sweep bias value now becomes the previous value
            previous_bias = sa_bias_sweep_val[sweep_point]

        # Calc ics for the next two phases to use
        self.calculate_ics()

    #work to get Mfb. ramp to icmax dac voltage then store the vphis
    def phase0_1(self):
        '''
        Biases squids to ADC_max value then stores the vphis and the triangle
        The units will be left in ADC units reported by DASTARD
        '''
       #gather variables from config
        phase_conf = self.test_conf['phase0_1']

        #used to set up proper data structure size, calculate the number of points in the full triangle response
        npts_data = (2**phase_conf['crate']['tri_steps'])*(2**phase_conf['crate']['tri_dwell']) * 2 # mult by two because of triangle no sawtooth

        # Set the DAQ to appropriate values 
        self.daq.pointsPerSlice = npts_data
        self.daq.averages = phase_conf['n_avg']

        # Zero all the columns
        self.zero_everything()

        print("Phase0_1 Bias to IC_Max and Save VPhi with Triagnle on SSA_FB")
        try:
            # Loop through the columns and ramp up to the icmax dac voltages        
            for col in range(self.ncol):
                self.ramp_to_voltage(self.sel_col[col], self.data[col].dac_ic_max)
        except Exception as e:
            print(e)
            print('Likely Icmax is 0 - try again')
        else:
            # Sleep to let system transient settle out before taking data
            time.sleep(phase_conf['bias_change_wait_ms'] / 1000.0)
            
            #Take data that has been rolled then averaged across all rows
            fb, err = self.daq.take_average_data_roll(avg_all_rows=True)
            
            #store gathered data for processing
            for col in range(self.ncol):
                self.data[col].phase0_1_icmax_vphi = err[self.sel_col[col]]
                self.data[col].phase0_1_triangle = fb[self.sel_col[col]]

    #send triangle down input to get min then store the vphis
    def phase1_0(self):
        '''
        Sends signal to the inputs, biases the squids to ADC_max, then stores the vphis and the triangle
        The units will be left in ADC units reported by DASTARD
        '''
        #gather variables from config
        phase_conf = self.test_conf['phase1_0']

        #used to set up proper data structure size, calculate the number of points in the full triangle response
        npts_data = (2**phase_conf['crate']['tri_steps'])*(2**phase_conf['crate']['tri_dwell']) * 2 # mult by two because of triangle no sawtooth

        # Set the DAQ to appropriate values 
        self.daq.pointsPerSlice = npts_data
        self.daq.averages = phase_conf['n_avg']

        #zero all the columns
        self.zero_everything()

        print("Phase1_0 Bias to IC_Max and Save VPhi with Triagnle on SSA_INPUT")
        try:
            #loop throught the columns and ramp up to the icmax dac voltage
            for col in range(self.ncol):
                self.ramp_to_voltage(self.sel_col[col], self.data[col].dac_ic_max)
        except Exception as e:
            print(e)
            print('Likely Icmax is 0 - try again')
        else:
            #sleep to let system transient settle out before taking data
            time.sleep(phase_conf['bias_change_wait_ms'] / 1000.0)

            #take data that has been rolled then averaged across all rows
            fb, err = self.daq.take_average_data_roll(avg_all_rows=True)

            #store gathered data for processing
            for col in range(self.ncol):
                self.data[col].phase1_0_icmax_vphi = err[self.sel_col[col]]
                self.data[col].phase1_0_triangle = fb[self.sel_col[col]]
       
    #saves data results - john currently has this as part of the dataclass module  
    def save_data(self):
        '''
        Save the data classes which contain the data with the assigned names from bookkeeping()
        '''
        for i in self.data:
            # Removed save_all_data flag from the script and will always pass in True to the save call
            i.save(True)

HELP_TEXT = '''\
This is the main SQUID Series Array Testing and Quality Assurance Data Collection Script
'''

def main():
    # Setup the flag and argument parser for the script
    parser = argparse.ArgumentParser(
        prog='SSA_data_collection',
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

    test = SSA(args.sys_file_path, args.config_file_path, args.verbosity)

    banner = "________   SSA_data_collection   ________\n" \
        + "Squid Series Array Data Collection Script\n" \
        + "_______Arguments_______\n" \
        + "\tCurrent Working Directory: " + test._conf_parser.cwd + "\n" \
        + "\t  System Config File path: " + test._conf_parser.sys_file_path + "\n" \
        + "\tSSA test Config File Path: " + test._conf_parser.config_file_path + "\n" \
        + "\t          Verbosity level: " + str(args.verbosity) + "\n" \
        + "\n" \
        + "Defined Classed:\n" \
        + "  test = SSA() : Test System level class containing the phases of testing.\n" \
        + "  test.data[n] : SSA_Data class which will contain the data that has been calculated or taken.\n" \
        + "\n" \
        + "_______Example Usage_______\n" \
        + "Once the system has been configured using Cringe and DATARD is running you can\n" \
        + "run the phases of testing.\n" \
        + "    test.phase0_0()   :  This runs the bias sweep to determine IC_Mod_Max and IC_Min.\n" \
        + "    test.phase0_1()   :  This biases each SSA at IC_Mod_Max and saves the SQUID VPhi.\n" \
        + "                         expecting the Feed Back to be swept by a triangle\n" \
        + "    test.phase1_0()   :  This biases each SSA at IC_Mod_Max and saves the SQUID VPhi\n" \
        + "                         expecting the Input to be swept by a triangle\n" \
        + "    test.save_data()  :  Will save all of the data to disk as pickles, each containing\n" \
        + "                         a pickle file for a single SSA and all related data.\n"
    if(args.interactive):
        print(banner)
        IPython.start_ipython(argv=[], user_ns=locals())

if (__name__ == '__main__'):
    main()
