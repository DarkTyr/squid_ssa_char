#################################################################################
#
# Written by: Johnathon Gard, Erin Maloney
# Purpose: SSA data processing script. Takes the screening data, calculates needed 
# values, creates plots and puts them into external documents. One document to go
# out as a deliverable, one for internal use with more specific requested plots
#
# September 2023
#
#################################################################################

#all imports from original - lets see what we end up using!
import argparse
import Ipython
import glob
import os
from scipy.signal import butter, lfilter
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import time
from squid_ssa_char.modules import load_conf_yaml, ssa_data_class, daq, towerchannel

#for date/time stamps on reports, now goes out to minutes 
today = time.localtime()
now = '{0:04d}_'.format(today.tm_year) + '{0:02d}_'.format(today.tm_mon) + '{0:02d}_'.format(today.tm_mday) + \
    '{0:02d}'.format(today.tm_hour) + '{0:02d}'.format(today.tm_min)

#constants for calculations/unit conversions
#TODO: not sure how many of these are needed at all let alone wanted here vs in some config
phi0 = 2.06783383e-15   #magnetic flux quantum
scale_L = 1.0e18        #1/(pH*uA)
scale_uA = 1.0e6        #scale to microamps
Pamp_gain = 96.0        #Tower preamp card gain TODO: this is part of the sys config?
#tower bias DACs
Towerfs = 2.0**16 - 1   #DAC units
Towerref = 2.5          #Volts
#crate bias DACs
DACfs = 2.0**14 -1      #DAC units
DACref = 1.0            #Volts
#client ADCs
#TODO: likely wrong bc this assumes Matter not dastard
Clientfs = 2.0**12 -1   #DAC units
Clientref = 1.0         #Volts
Client_scale = 1.0e3
#TODO: 99% sure these are in the system config - adjust accordingly
R_sa_fb = 5100.0
R_sa_in = 2000.0
R_sa_bias = 10000.0
R_sa_DAC_out = 6250.0
R_sa_total = R_sa_bias + R_sa_DAC_out
#scaling factors - unit conversion
#TODO: dont think we wanna do it this way but now there here...? Big thoughts to come
factor_sa_fb = DACref * scale_uA / (DACfs * R_sa_fb)                #converts SAFB DAC to feedback current [uA]
factor_sa_in = DACref * scale_uA / (DACfs * R_sa_in)                #converts SQ1FB DAC to input current [uA]
factor_dev_I = Towerref * scale_uA / (Towerfs * R_sa_total)         #convert SAFB DAC to device current [uA]
#TODO: likely wrong because uses Matter values and were gonna do Dastard
factor_dev_V = Clientref * Client_scale / (Clientfs * Pamp_gain)    #convert Matter client ADC to device voltage [mV]




#first calculate the needed values for demarkation in the plots
#this includes converting from ADC values
#TODO: do unit conversions in here too or nah?
def calculate_Ms(m_data):
    #TODO: do I reference the columns the same way as in data capture?
    for col in columns:
        #TODO: the idea is you find the places where the derivative's sign changes, store those indexes, then find the
        #spacing between peaks 2 and 4 (two tops skips a bottom) then convert that range to proper units bc rn in ADC units
        #Do we need to shift this somehow? Or will this find the peaks as is?
        #TODO: this is a giant mess - need to reference the data properly, initialize storage variables, then actually convert units.
        m_zeros = np.where(np.diff(np.signbit(m_data)))[0]         #heres where we reference phase0_1_icmax_vphi
        if len(m_zeros) >= 4:
            mfb_data[col,0] = phase0_1_icmax_vphi[col]      #TODO: reference this correctly
            mfb_peak_centers_idx = int(np.average(mfb_zeros[2:4]))
            mfb_data[col,1] = phase0_1_icmax_vphi[col,mfb_peak_centers_idx]

        if len(min_zeros) >= 4:
            min_data[col,0] = phase1_0_icmax_vphi[col]      #TODO: reference this correctly
            min_peak_centers_idx = int(np.average(min_zeros[2:4]))
            min_data[col,1] = phase1_0_icmax_vphi[col,min_peak_centers_idx]      

    Mfb = phi0 / ((mfb_data[:,1]-mfb_data[:,0])*factor_sa_fb)*scale_L   
    Min = phi0 / ((min_data[:,1]-min_data[:,0])*factor_sa_in)*scale_L       
    return


#Thoughts:
    #create two outputs - one that has some plots for external use, one with all plots for internal use
    #include xl table in the output doc - all one thing?
        #con with this is xl is all 8 chips ususlly - could do just one table line? 
            #could also stick with the printout xl we put together for each module on top of this so its in 
            #multiple places
    #how do plots? could create a function that takes x,y then returns a line plot then add things to 
    # each plot made by the call?
        #not sure how that would work in practice - probably wont reduce code length the way I think
    #How do we want to order the plots?
    #Do we want to always create both documents or make them both optional? Kinda like a flag thing

    #TODO: talk with John about loading in the files, the file path, and properly referencing data
        #what do the argparse thingy do in original (first long thing), do we need it?


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Take data from QA_DAQ, scale it, plot it and generate a PDF report'
                                     'for each device specified in list of files')
    parser.add_argument('list_of_files',
                        type=str,
                        help='A list of paths to some files that will be parsed and plotted')
    
    args = parser.parse_args()

    fnames = glob.glob(str(args.list_of_files))
    fnames.sort()

    data = [ssa_data_class.SSA_Data_Class(fnames[0])]
    for i in range(len(fnames) - 1):
        data.append(ssa_data_class.SSA_Data_Class(fnames[i + 1]))


    for i in data:
        i.M_in = calculate_Ms(i.phase1_0_icmax_vphi)
        i.M_fb = calculate_Ms(i.phase0_1_icmax_vphi)        