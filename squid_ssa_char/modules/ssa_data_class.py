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

class SSA_Data_Class:
    def __init__(self):
        # Testing Information storage
        self.chip_id = ''       # CHIP  ID
        self.qa_name = ''       #Name of the Person performing the test
        self.system_name = ''   # Name fo the system the test was performed on
        self.file_name = ''     # Name of the file if/when saved
        self.dac_n_bits = 14    # Number of of bits for the DAC : TODO: Needed?
        self.dac_vref = 2.5     # TODO: needed?
        
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
        
        # Phase1_0 Bias to Ic_Max while sweeping Input and save V_Phi
        self.phase1_0_icmax_vphi = np.array([])
        


    def save_npz(self, save_all=False):
        '''
        Method to save the data to NPZ
        '''
        return
    
    def load_npz(self):
        '''
        Method to load the data from an NPZ for use by other programs
        '''
        return
