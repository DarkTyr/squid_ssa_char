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
import IPython
import glob
import os
from scipy.signal import butter, lfilter
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import time
from squid_ssa_char.modules import ssa_data_class

#for date/time stamps on reports, now goes out to minutes 
today = time.localtime()
now = '{0:04d}_'.format(today.tm_year) + '{0:02d}_'.format(today.tm_mon) + '{0:02d}_'.format(today.tm_mday) + \
    '{0:02d}'.format(today.tm_hour) + '{0:02d}'.format(today.tm_min)

#constants for calculations/unit conversions
phi0 = 2.06783383e-15   #magnetic flux quantum (H*A)
scale_L = 1.0e18        #1/(pH*uA)
scale_uA = 1.0e6        #scale to microamps
#TODO: remove constants and factors below this, for now there here as reminders
Pamp_gain = 96.0        #Tower preamp card gain 
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
#resistors
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
#this includes converting from ADC values, returns the M value and the two pickoff points for plot demarkation
def calculate_Ms(m_data, triangle_data, scale_factor):
    m_average = np.average(m_data)                                          #shift amount
    m_zeros = np.where(np.diff(np.signbit(m_data - m_average)))[0]          #stores indexes where the now shifted vphi crosses 0
    if len(m_zeros) >= 4:
        # We could do a calculation to find the peaks (average between the first two zeros, and the second pair of zeros)
        #currently this picks M off the shifted 0s so still accurate but will be visually different
        delta0 = triangle_data[m_zeros[2]] - triangle_data[m_zeros[0]]      # ADC value for M - the spacing between one full waveform of zeros
        delta1 = triangle_data[m_zeros[3]] - triangle_data[m_zeros[1]]
        m_start = triangle_data[m_zeros[0]]
        m_end = triangle_data[m_zeros[2]]

    #scale the values to current 
    M = phi0 / delta0 * scale_factor                #this combines all scaling - to be used if we put these values in the class
    m_start = m_start * scale_factor
    m_end = m_end * scale_factor  
    return M, m_start, m_end


#Thoughts:
    #create two outputs - one that has some plots for external use, one with all plots for internal use
    #include xl table in the output doc - all one thing?
        #con with this is xl is all 8 chips ususlly - could do just one table line? 
            #could also stick with the printout xl we put together for each module on top of this so its in 
            #multiple places
    #Do we want to always create both documents or make them both optional? Kinda like a flag thing

    #TODO: talk with John about file path for final report storage



#TODO: update help aspect to parser arguments
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Take data from QA_DAQ, scale it, plot it and generate a PDF report'
                                     'for each device specified in list of files')
    parser.add_argument('list_of_files',
                        type=str,
                        help='A list of paths to some files that will be parsed and plotted')
    parser.add_argument('-f',
                        dest='full_report',
                        action='store_true',
                        help='Makes plots summarizing the device measurements. Includes all plots our internal people requested to see')
    parser.add_argument('-r',
                        dest='pdf_report',
                        action='store_true',
                        help='Makes a pdf report for each chip including the selected plots generated in this script ')
    parser.add_argument('-e',
                        dest='external_reports',
                        action='store_true',
                        help='Creates only the plots we need to go with our deliverables')
    
    args = parser.parse_args()

    fnames = glob.glob(str(args.list_of_files))
    fnames.sort()

    #TODO: add .load after SSA_Data_Class
    data = [ssa_data_class.SSA_Data_Class(fnames[0])]
    for i in range(len(fnames) - 1):
        data.append(ssa_data_class.SSA_Data_Class(fnames[i + 1]))


    for i in data:
        Mfb_scale_factor = ((i.sys.daq_dac_vref * scale_uA) / ((2**(i.sys.daq_dac_nbits) - 1) * i.sys.fb_bias_r)) * i.sys.daq_dac_gain
        Min_scale_factor = ((i.sys.in_dac_vref * scale_uA) / ((2**(i.sys.daq_dac_nbits) - 1) * i.sys.in_bias_r)) * i.sys.daq_dac_gain
        i.M_in, i.Min_start, i.Min_end = calculate_Ms(i.phase1_0_icmax_vphi, i.phase1_0_triangle, Min_scale_factor)
        i.M_fb, i.Mfb_start, i.Mfb_end = calculate_Ms(i.phase0_1_icmax_vphi, i.phase0_1_triangle, Mfb_scale_factor)
        i.factor_adc_mV = ((i.sys.daq_adc_vrange) / (2**i.sys.daq_adc_nbits - 1) / (i.sys.daq_adc_gain) / (i.sys.amp_gain)) * 1000
        i.sab_dac_factor = ((i.sys.amp_dac_vref * scale_uA) / ((2**(i.sys.amp_dac_nbits) - 1) * i.sys.amp_bias_r)) * i.sys.amp_dac_gain

        #plot order:
        #        **note that most of this is off the white board drawing in Erins office - so names might be wierd
        #               TODO: figure out how these names relate to actual data variables LOL
        # 
        # plot 1: mod depth [mV] vs SA bias [uA]
        #     data product: phase0_0_vmod_sab vs dac_sweep_array
        fig1, (ax1, ax2) = plt.subplots(2,1)
        fig1.suptitle('Figure 1: device ' + i.chip_id, fontsize=14, fontweight='bold')
        ax1.plot((i.dac_sweep_array * i.sab_dac_factor), (i.phase0_0_vmod_sab * i.factor_adc_mV))
        ax1.set_title('Voltage Modulation Depth vs Sa Bias')
        ax1.set_xlabel('I$_{SAB}$ [$\mu$A]')
        ax1.set_ylabel('SA Modulation Depth [mV]')
        ax1.axvline(x = i.dac_ic_min * i.sab_dac_factor, ymin=0, ymax=1, color='b', lw=0.5)
        ax1.axvline(x = i.dac_ic_max * i.sab_dac_factor, ymin=0, ymax=1, color='b', lw=0.5)
        ax1.axhline(y = np.max(i.phase0_0_vmod_sab * i.factor_adc_mV), xmin=0, xmax=1, color='b', lw=0.5)
        #TODO: add text labels to plot1 next to vlines and hlines 

        # plot 2: V_ssa_min and V_ssa_max [mV] vs SA bias [uA]
        #           data product: phase0_0_vmod_min and phase0_0_vmod_max both vs dac_sweep_array
        #TODO: make labels for legend more accurate
        ax2.plot((i.dac_sweep_array * i.sab_dac_factor), (i.phase0_0_vmod_min * i.factor_adc_mV), label = 'Min')
        ax2.plot((i.dac_sweep_array * i.sab_dac_factor), (i.phase0_0_vmod_max * i.factor_adc_mV), label = 'Max')
        ax2.set_title('')
        ax2.set_ylabel('SSA Voltage [mV]')
        ax2.set_xlabel('I$_{SAB}$ [$\mu$A]')
        ax2.legend()

        # 
        # plot 3: dVssa/dIsab vs Isab [uA]
        #   also two curves at max and min?
        #           data product: this needs to be calculated bc derivative? (derivative of figure 2)
        #
        #          ** -- start of analysis at max mod depth -- **
        # plot 4: Vssa [mV] vs Iin [uA]
        #       data product: phase1_0_icmax_vphi vs phase1_0_triangle
        #       mark Min on this plot
        fig2, (ax3, ax4) = plt.subplots(2,1)
        fig2.suptitle('Figure 2: device ' + i.chip_id, fontsize=14, fontweight='bold')
        ax3.plot((i.phase1_0_triangle * Min_scale_factor), (i.phase1_0_icmax_vphi * i.factor_adc_mV))
        ax3.set_title('Device Voltage vs Input Current at at I$_{cmax}$')
        ax3.set_ylabel('Device Voltage [mV]')
        ax3.set_xlabel('SAIN Current [$\mu$A]')
        ax3.axvline(x=i.Min_end, ymin=0, ymax=1)
        ax3.axvline(x=i.Min_start, ymin=0, ymax=1)

        #TODO: derivative of ax3 plot 
        ax4.plot()
        ax4.set_title('')
        ax4.set_ylabel('')
        ax4.set_xlabel('')
        
        # plot 5: Vssa [mV] vs Ifab [uA]
        #       data product = phase0_1_icmax_vphi vs phase0_1_triangle
        #       mark Mfb on this plot
        fig3, (ax5, ax6) = plt.subplots(2,1)
        fig3.suptitle('Figure 3: device ' + i.chip_id, fontsize=14, fontweight='bold')
        ax5.plot((i.phase0_1_triangle * Mfb_scale_factor), (i.phase0_1_icmax_vphi * i.factor_adc_mV))
        ax5.set_title('Device Voltage vs Feedback Current at I$_{cmax}$')
        ax5.set_ylabel('Device Voltage [mV]')
        ax5.set_xlabel('SAFB Current [$\mu$A]')
        ax5.axvline(x=i.Mfb_end, ymin=0, ymax=1)
        ax5.axvline(x=i.Mfb_start, ymin=0, ymax=1)
        #TODO: make the horizontal line between the two verticals, axhline uses grid coordinates so is HARD

        #TODO: derivative of ax5 plot 
        ax6.plot()
        ax6.set_title('')
        ax6.set_ylabel('')
        ax6.set_xlabel('')
        #
        # plot 6: dV/dIin vs Vssa
        #           transimpedance
        #           data product: this needs to be calculated bc derivative?
        #
        # plot 7: dV/dIin vs Ifbx
        #           also transimpedance?
        #           data product: this needs to be calculated bc derivative?
        #
        # plot 8: dV/dIsab vs Vssa
        #           dynamic resistance
        #           data product: this needs to be calculated bc derivative?
        #
        # plot 9: dV/dIsab vs Ifbx
        #           also dynamic resisance?
        #           data product: this needs to be calculated bc derivative?
        #
        #
        #