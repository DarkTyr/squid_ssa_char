#################################################################################
#
# Written by: Johnathon Gard, Erin Maloney
# Purpose: SSA screening script,
#
# Class to hold the recoreded data values for the SQUID Series Array Screening.
#
# September 2023
#
#################################################################################


import numpy as np
import pickle

class SSA_Data_Class:
    def __init__(self):
        # Testing Information storage
        self.chip_id = ''       # CHIP  ID
        self.qa_name = ''       #Name of the Person performing the test
        self.system_name = ''   # Name fo the system the test was performed on
        self.file_name = ''     # Name of the file if/when saved
        self.dac_n_bits = 14    # Number of of bits for the DAC : TODO: Needed?
        self.dac_vref = 2.5     # TODO: needed?
        self.channel_num = 0
        self.test_conf_name = ''
        
        # Phase0 SA Bias Sweep Data While Sweeping Feedback
        self.dac_sweep_array = np.array([]) # Store the SA Bias DAC values we will sweep
        self.dac_ic_min = 0.000 # Place to store the dac value IC min occured at
        self.dac_ic_max = 0.000 # Place to store the dac value IC Max occured at
        self.sa_bias_start = 0  # start value of series array bias sweep
        self.sa_bias_stop = 20000   # Stop value for SA bias sweep
        self.baselines_std = np.array([])
        self.baselines_range = np.array([])
        self.baselines_average = np.array([])
        self.baselines_SNR = np.array([])
        self.baselines_trace = np.array([])   # Place to store the trace that std, range, average, SNR was calced from
        self.phase0_0_vmod_sab = np.array([]) # SSA V Modulation depth vs bias
        self.phase0_0_vmod_min = np.array([]) # Store min value of the modulation in adc units
        self.phase0_0_vmod_max = np.array([]) # Store max value of the modulation in adc units
        self.phase0_0_vphis = np.array([])  # Place to store the VPhi for every bias value for testing 
        
        # Phase0_1 Bias to Ic_Max while sweeping Feed Back and save V_Phi
        self.phase0_1_icmax_vphi = np.array([])
        self.phase0_1_triangle = np.array([])
        
        # Phase1_0 Bias to Ic_Max while sweeping Input and save V_Phi
        self.phase1_0_icmax_vphi = np.array([])
        self.phase1_0_triangle = np.array([])
        
    def save(self, save_all=False):
        '''
        Method to save the data class to a pickle, if save_all is false, the bias sweep vphis
        will be cleared out and then the data class saved using pickle
        '''
        with open(self.file_name + '.pickle', 'wb') as f:
            # If save all is false, clear out the stored sweep of vphis form the data class
            if(save_all == False):
                self.phase0_0_vphis = np.array([])
            # Dump the class to the pickle file type
            pickle.dump(self, f, -1)  # -1 means use the latest encoding version of pickle
    
    @classmethod
    def load(cls, filename):
        '''
        Method to load the data from an NPZ for use by other programs
        '''
        with open(filename, 'rb') as f:
            return pickle.load(f)
