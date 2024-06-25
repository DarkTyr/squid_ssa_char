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

#TODO: remove butter and lfiter if not used - check later
#TODO: checked whats holding up the program when script called - its hanging on argparse and glob
import argparse
import glob
#from scipy.signal import butter, lfilter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import time
from squid_ssa_char.modules import ssa_data_class
import scipy.signal as sig
import IPython

#for date/time stamps on reports, now goes out to minutes 
today = time.localtime()
now = '{0:04d}_'.format(today.tm_year) + '{0:02d}_'.format(today.tm_mon) + '{0:02d}_'.format(today.tm_mday) + \
    '{0:02d}'.format(today.tm_hour) + '{0:02d}'.format(today.tm_min)

#constants for calculations/unit conversions
phi0 = 2.06783383e-15   #magnetic flux quantum (H*A)
scale_L = 1.0e18        #1/(pH*uA)
scale_uA = 1.0e6        #scale to microamps

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
    M = (phi0 / (delta0 * scale_factor)) * scale_L                #this combines all scaling - to be used if we put these values in the class
    m_start = m_start * scale_factor
    m_end = m_end * scale_factor  
    return M, m_start, m_end

#smooths the data using functions within interpolate. Takes the x axis of the plot and the y axis of the plot [prescaled to be the same length
#with no overlapping values (triangle is cut at just the up-slope)]. Also takes smoothing paramater s for splrep higher->more smoothed
def smooth(y_arr, sm_lev):
   #first_pass = interpolate.splrep(x_arr, y_arr, k=2, s=sm_lev)
   #second_pass = interpolate.splev(x_arr, first_pass, der=0)

   filtercoeffs = sig.firwin(sm_lev,0.1,window=('hamming'))    # amt of taps passed in by call, low-pass at 0.1*fsamp/2
   ysmooth = sig.filtfilt(filtercoeffs,1.0,y_arr)              # Applies filter forward and backward
   return ysmooth

#TODO: talk with John about file path for final report storage                                  

#TODO: update help aspect to parser arguments
def main():
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
                        dest='external_report',
                        action='store_true',
                        help='Creates only the plots we need to go with our deliverables')
    parser.add_argument('-i',
                        dest='interactive',
                        action='store_true',
                        help='Enter interactive mode at end of script')
    
    args = parser.parse_args()
    
    #breaks up the list of files into individual things
    print(str(args.list_of_files))
    fnames = glob.glob(str(args.list_of_files))
    fnames.sort()

    if len(fnames) == 0:
        print('glob did not parse the given string and fnames has length zero')

    #this is for navigating directories - to be used with wafer plots
    fname_arr = []

    for element in fnames:
        print(element)
        fname_arr.append(element.rsplit('/', 1)[-1][:11])

    fname_arr = np.array(fname_arr)
    #data load and format into string if file names
    
    #TODO: check fnames for length greater than one, if not, report that there were no files found and print out what was passed in
    data = [ssa_data_class.SSA_Data_Class.load(fnames[0])]
    for i in range(len(fnames) - 1):
        data.append(ssa_data_class.SSA_Data_Class.load(fnames[i + 1]))

    #counter for numerical indexing during data file loop
    cnt = -1

    for i in data:
        cnt += 1
        #plotting scaling factors and call of M value calculations
        Mfb_scale_factor = ((i.sys.daq_dac_vref * scale_uA) / ((2**(i.sys.daq_dac_nbits) - 1) * i.sys.fb_bias_r)) * i.sys.daq_dac_gain
        Min_scale_factor = ((i.sys.in_dac_vref * scale_uA) / ((2**(i.sys.daq_dac_nbits) - 1) * i.sys.in_bias_r)) * i.sys.daq_dac_gain
        i.M_in, i.Min_start, i.Min_end = calculate_Ms(i.phase1_0_icmax_vphi, i.phase1_0_triangle, Min_scale_factor)
        i.M_fb, i.Mfb_start, i.Mfb_end = calculate_Ms(i.phase0_1_icmax_vphi, i.phase0_1_triangle, Mfb_scale_factor)
        i.factor_adc_mV = ((i.sys.daq_adc_vrange) / (2**i.sys.daq_adc_nbits - 1) / (i.sys.daq_adc_gain) / (i.sys.amp_gain)) * 1000
        i.sab_dac_factor = ((i.sys.amp_dac_vref * scale_uA) / ((2**(i.sys.amp_dac_nbits) - 1) * i.sys.amp_bias_r)) / i.sys.amp_dac_gain

        #data smoothing and derivatives. Smoothing done using interpolate splrep and splev derivative with gradient
        #These are derived then smoothed - we found for phase01 and phase10 data this method reduced noise without eliminating features
        dVdI_fb = np.gradient(i.phase0_1_icmax_vphi*i.factor_adc_mV, i.phase0_1_triangle*Mfb_scale_factor)
        dVdI_in = np.gradient(i.phase1_0_icmax_vphi*i.factor_adc_mV, i.phase1_0_triangle*Min_scale_factor)
        dVdI_fb_smooth = (smooth(dVdI_fb[0:int(0.5*len(i.phase0_1_triangle))], 51))*1000
        dVdI_in_smooth = (smooth(dVdI_in[0:int(0.5*len(i.phase1_0_triangle))], 31))*1000

        #these are smoothed then derived - for phase00 data this method reduced noise without eliminating features 
        dVmodmax_dIsafb = np.gradient(i.phase0_0_vmod_max*i.factor_adc_mV*1000, i.dac_sweep_array*i.sab_dac_factor)
        dVmodmin_dIsafb = np.gradient(i.phase0_0_vmod_min*i.factor_adc_mV*1000, i.dac_sweep_array*i.sab_dac_factor)
        dVmodmax_dIsafb_smooth = smooth(dVmodmax_dIsafb, 11)
        dVmodmin_dIsafb_smooth = smooth(dVmodmin_dIsafb, 11)

        #setup for data table of calculated values, creates lables and the list of data for the cells (rounded to 2 decimal places)
        tdata = [round((i.dac_ic_min*i.sab_dac_factor),2), round((i.dac_ic_max*i.sab_dac_factor),2), round((np.max(i.phase0_0_vmod_sab*i.factor_adc_mV)),2), \
                 round((i.M_fb),2), round((i.M_in),2), round((i.M_in)/(i.M_fb),2)]
        column_labels = ['Icmin [$\mu$A]', 'Icmax [$\mu$A]', 'Mod Depth [mV]', 'Mfb [pH]', 'Min [pH]', 'Min/Mfb']

        #Rdyn calculation 
            #find the vphi for icmax, store the indexes where thats true, take first instance then some step of vphis up or down (we chose 3 steps up)
            #difference the instance from the vphi some step away, then convert from dac units to volts and amps, divide the voltage change by the current changes
        find_max = np.where(i.phase0_0_vphis == i.phase0_1_icmax_vphi)
        max_idx = int(np.mean(find_max[0]))
        phi_step = 3
        volt_diff = (i.phase0_0_vphis[max_idx+phi_step] - i.phase0_0_vphis[max_idx])*i.factor_adc_mV*(1e-3)
        curr_diff = (i.dac_sweep_array[max_idx+phi_step] - i.dac_sweep_array[max_idx])*i.sab_dac_factor*(1e-6)
        rdyn = volt_diff/curr_diff
        rdyn_smooth = smooth(rdyn, 31)


        #TODO: actually name the file path this is a HUGE filler right now
        if args.pdf_report:
            report_name = fname_arr[cnt] + '_' + str(now) + '.pdf'
            pdf = PdfPages(report_name)
            print('Generating Report: ', report_name)

        #TODO: currently it just makes everything for either argument, make more sophisticated
        if args.full_report or args.external_report or args.pdf_report:
            #start of plotting
            fig1, (ax0, ax1, ax2) = plt.subplots(3,1, gridspec_kw={'height_ratios': [1, 10, 10]})
            fig1.set_size_inches(7.5, 10, forward=True)
            fig1.subplots_adjust(hspace=0.45)
            fig1.suptitle('Figure 1: device ' + i.chip_id, fontsize=14, fontweight='bold')
            #table of values for the chip - turn off axes and frame then make the table
            ax0.set_frame_on(False)
            ax0.set_xticks([])
            ax0.set_yticks([])
            table = ax0.table(cellText=[tdata], colLabels=column_labels, loc='upper left', cellLoc='center', colColours=['lightgray']*7, fontsize=20)
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            ax0.set_title(i.chip_id + ': Table of Calculated Values', fontsize=16)
            # plot 1: mod depth [mV] vs SA bias current [uA]
            ax1.plot((i.dac_sweep_array * i.sab_dac_factor), (i.phase0_0_vmod_sab * i.factor_adc_mV))
            ax1.set_title('Voltage Modulation Depth vs SA Bias', fontsize=16)
            ax1.set_xlabel('I$_{SAFB}$ [$\mu$A]', fontsize=14)
            ax1.set_ylabel('SA Modulation Depth [mV]', fontsize=14)
            ax1.axvline(x = i.dac_ic_min * i.sab_dac_factor, ymin=0, ymax=1, color='b', lw=0.5)
            ax1.axvline(x = i.dac_ic_max * i.sab_dac_factor, ymin=0, ymax=1, color='b', lw=0.5)
            ax1.axhline(y = np.max(i.phase0_0_vmod_sab * i.factor_adc_mV), xmin=0, xmax=1, color='b', lw=0.5)
            ax1.text(i.dac_ic_min * i.sab_dac_factor, np.max(i.phase0_0_vmod_sab * i.factor_adc_mV)*0.7, '$I_{cmin}$ \n %.1f $\mu$A' %(i.dac_ic_min*i.sab_dac_factor), \
                    ha='center', va='center', color = 'blue', backgroundcolor='w',fontsize=10)
            ax1.text(i.dac_ic_max * i.sab_dac_factor, np.max(i.phase0_0_vmod_sab * i.factor_adc_mV)*0.4, '$I_{cmax}$ \n %.1f $\mu$A' %(i.dac_ic_max*i.sab_dac_factor), \
                    ha='center', va='center', color = 'blue', backgroundcolor='w',fontsize=10)
            ax1.text((i.dac_sweep_array[-1]*i.sab_dac_factor)*.95, np.max(i.phase0_0_vmod_sab*i.factor_adc_mV)*0.93, \
                    '$V_{mod}$\n %.1f mV' %np.max(i.phase0_0_vmod_sab*i.factor_adc_mV), ha='center', va='center', color='blue', backgroundcolor ='w', fontsize=10)

            # plot 2: V_ssa_min and V_ssa_max [mV] vs SA bias [uA]
            ax2.plot((i.dac_sweep_array * i.sab_dac_factor), (i.phase0_0_vmod_min * i.factor_adc_mV), label = '$V_{min}$')
            ax2.plot((i.dac_sweep_array * i.sab_dac_factor), (i.phase0_0_vmod_max * i.factor_adc_mV), label = '$V_{max}$')
            ax2.set_title('Device Voltage vs Bias Current', fontsize=16)
            ax2.set_ylabel('SSA Voltage [mV]', fontsize=14)
            ax2.set_xlabel('I$_{SAFB}$ [$\mu$A]', fontsize=14)
            ax2.legend()
            ax2.text(np.max(i.dac_sweep_array*i.sab_dac_factor)*.95, np.max(i.phase0_0_vmod_min*i.factor_adc_mV)*.65, '$V_{min}$', ha='center', va='center', color='black', backgroundcolor='w',fontsize=10)
            ax2.text(np.max(i.dac_sweep_array*i.sab_dac_factor)*.7, np.max(i.phase0_0_vmod_max*i.factor_adc_mV)*.85, '$V_{max}$', ha='center', va='center', color='black', backgroundcolor='w',fontsize=10)

            if args.pdf_report:
                pdf.savefig()


            fig2, (ax3, ax4) = plt.subplots(2,1)
            fig2.set_size_inches(7.5, 10, forward=True)
            fig2.subplots_adjust(hspace=0.35)
            fig2.suptitle('Figure 2: device ' + i.chip_id, fontsize=14, fontweight='bold')
            # plot 3: Vssa [mV] vs Iin [uA], Min marked on this plot
            ax3.plot((i.phase1_0_triangle * Min_scale_factor), (i.phase1_0_icmax_vphi * i.factor_adc_mV))
            ax3.set_title('Device Voltage vs Input Current at at I$_{cmax}$', fontsize=16)
            ax3.set_ylabel('Device Voltage [mV]', fontsize=14)
            ax3.set_xlabel('SAIN Current [$\mu$A]', fontsize=14)
            sain_xlim = int(np.max(i.phase1_0_triangle * Min_scale_factor)) + 1
            ax3.set_xlim(0, sain_xlim)
            ax3.set_ylim((np.min(i.phase1_0_icmax_vphi*i.factor_adc_mV))-1, np.max(i.phase1_0_icmax_vphi*i.factor_adc_mV)+1)
            ax3.axvline(x=i.Min_end, ymin=0, ymax=1, lw=0.5)
            ax3.axvline(x=i.Min_start, ymin=0, ymax=1, lw=0.5)
            ax3.axhline(y=np.max(i.phase1_0_icmax_vphi * i.factor_adc_mV)*.75, xmin=(1.0/sain_xlim)*i.Min_start, xmax=(1.0/sain_xlim)*i.Min_end, lw=0.5)
            ax3.axhline(y=np.min(i.phase1_0_icmax_vphi * i.factor_adc_mV), xmin=0, xmax=1, lw=0.5)
            ax3.axhline(y=np.max(i.phase1_0_icmax_vphi * i.factor_adc_mV), xmin=0, xmax=1, lw=0.5)
            ax3.text((i.Min_start+i.Min_end)/2, np.max(i.phase1_0_icmax_vphi * i.factor_adc_mV)*0.75, '$M_{in}$ = %.1f pH' %i.M_in,\
                    ha='center', va='center', color='black', backgroundcolor='w', fontsize=10)
            ax3.text(i.Min_end, np.max(i.phase1_0_icmax_vphi * i.factor_adc_mV)*0.15, '%.1f' %i.Min_end, \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)
            ax3.text(i.Min_start, np.max(i.phase1_0_icmax_vphi * i.factor_adc_mV)*0.15, '%.1f' %i.Min_start, \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)
            ax3.text(sain_xlim*0.95, np.max(i.phase1_0_icmax_vphi * i.factor_adc_mV), '%.1f' %np.max(i.phase1_0_icmax_vphi * i.factor_adc_mV), \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)
            ax3.text(sain_xlim*0.95, np.min(i.phase1_0_icmax_vphi * i.factor_adc_mV), '%.1f' %np.min(i.phase1_0_icmax_vphi * i.factor_adc_mV), \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)

            # derivative of Vssa vs Isain 
            ax4.plot((i.phase1_0_triangle[5:int(0.5*len(i.phase1_0_triangle)-5)])*Min_scale_factor, dVdI_in_smooth[5:-5])
            ax4.set_title('SA Input Gain vs SA Input Current at I$_{cmax}$', fontsize=16)
            ax4.set_ylabel('dV$_{dev}$/dI$_{SAIN}$ [$\mu$V/$\mu$A]', fontsize=14)
            ax4.set_xlabel('SAIN Current [$\mu$A]', fontsize=14)
            ax4.set_xlim(0, sain_xlim)
            ax4.axhline(y=np.max(dVdI_in_smooth[5:-5]), xmin=0, xmax=1, lw=0.5)
            ax4.axhline(y=np.min(dVdI_in_smooth[5:-5]), xmin=0, xmax=1, lw=0.5)
            ax4.text(sain_xlim*0.95, np.min(dVdI_in_smooth[5:-5]), '%.1f' %np.min(dVdI_in_smooth[5:-5]), \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)
            ax4.text(sain_xlim*0.95, np.max(dVdI_in_smooth[5:-5]), '%.1f' %np.max(dVdI_in_smooth[5:-5]), \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)

            if args.pdf_report:
                pdf.savefig()          
            
            # plot 5: Vssa [mV] vs Ifab [uA], Mfb marked on this plot
            fig3, (ax5, ax6) = plt.subplots(2,1)
            fig3.set_size_inches(7.5, 10, forward=True)
            fig3.subplots_adjust(hspace=0.35)
            fig3.suptitle('Figure 3: device ' + i.chip_id, fontsize=14, fontweight='bold')
            ax5.plot((i.phase0_1_triangle * Mfb_scale_factor), (i.phase0_1_icmax_vphi * i.factor_adc_mV))
            ax5.set_title('Device Voltage vs Feedback Current at I$_{cmax}$', fontsize=16)
            ax5.set_ylabel('Device Voltage [mV]', fontsize=14)
            ax5.set_xlabel('SAFB Current [$\mu$A]', fontsize=14)
            safb_xlim = int(np.max(i.phase0_1_triangle * Mfb_scale_factor)) + 1
            ax5.set_xlim(0, safb_xlim)
            ax5.set_ylim((np.min(i.phase0_1_icmax_vphi*i.factor_adc_mV))-1, np.max(i.phase0_1_icmax_vphi*i.factor_adc_mV)+1)
            ax5.axvline(x=i.Mfb_end, ymin=0, ymax=1, lw=0.5)
            ax5.axvline(x=i.Mfb_start, ymin=0, ymax=1, lw=0.5)
            ax5.axhline(y=np.max(i.phase0_1_icmax_vphi * i.factor_adc_mV)*.75, xmin=(1.0/safb_xlim)*i.Mfb_start, xmax=(1.0/safb_xlim)*i.Mfb_end, lw=0.5)
            ax5.axhline(y=np.min(i.phase0_1_icmax_vphi * i.factor_adc_mV), xmin=0, xmax=1, lw=0.5)
            ax5.axhline(y=np.max(i.phase0_1_icmax_vphi * i.factor_adc_mV), xmin=0, xmax=1, lw=0.5)
            ax5.text((i.Mfb_start+i.Mfb_end)/2, np.max(i.phase0_1_icmax_vphi * i.factor_adc_mV)*0.75, '$M_{fb}$ = %.1f pH' %i.M_fb, \
                    ha='center', va='center', color='black', backgroundcolor='w', fontsize=10)
            ax5.text(i.Mfb_end, np.max(i.phase0_1_icmax_vphi * i.factor_adc_mV)*0.15, '%.1f' %i.Mfb_end, \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)
            ax5.text(i.Mfb_start, np.max(i.phase0_1_icmax_vphi * i.factor_adc_mV)*0.15, '%.1f' %i.Mfb_start, \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)
            ax5.text(safb_xlim*0.95, np.min(i.phase0_1_icmax_vphi * i.factor_adc_mV), '%.1f' %np.min(i.phase0_1_icmax_vphi * i.factor_adc_mV), \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)
            ax5.text(safb_xlim*0.95, np.max(i.phase0_1_icmax_vphi * i.factor_adc_mV), '%.1f' %np.max(i.phase0_1_icmax_vphi * i.factor_adc_mV), \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)

            #derivative of Vssa vs Isafb plot
            ax6.plot((i.phase0_1_triangle[5:int(0.5*len(i.phase0_1_triangle))-5])*Mfb_scale_factor, dVdI_fb_smooth[5:-5])
            ax6.set_title('Feedback Gain vs Feedback Current at I$_{cmax}$', fontsize=16)
            ax6.set_ylabel('dV$_{dev}$/dI$_{SAFB}$ [$\mu$V/$\mu$A]', fontsize=14)
            ax6.set_xlabel('SAFB Current [$\mu$A]', fontsize=14)
            ax6.set_xlim(0, safb_xlim)
            ax6.axhline(y=np.max(dVdI_fb_smooth[5:-5]), xmin=0, xmax=1, lw=0.5)
            ax6.axhline(y=np.min(dVdI_fb_smooth[5:-5]), xmin=0, xmax=1, lw=0.5)
            ax6.text(safb_xlim*0.95, np.min(dVdI_fb_smooth[5:-5]), '%.1f' %np.min(dVdI_fb_smooth[5:-5]), \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)
            ax6.text(safb_xlim*0.95, np.max(dVdI_fb_smooth[5:-5]), '%.1f' %np.max(dVdI_fb_smooth[5:-5]), \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)

            if args.pdf_report:
                pdf.savefig()        

            fig4, (ax7, ax8) = plt.subplots(2,1)
            fig4.set_size_inches(7.5, 10, forward=True)
            fig4.subplots_adjust(hspace=0.35)
            fig4.suptitle('Figure 4: device ' + i.chip_id, fontsize=14, fontweight='bold')
            # plot 7: dVssa/dIsab vs Isab
            #TODO: Ask carl about this title - not sure we should call this dynamic resistance when we have that later? Im confused.
            ax7.plot(i.dac_sweep_array[5:-7]*i.sab_dac_factor, dVmodmax_dIsafb[5:-7], label = 'dV$_{max}$/dI$_{SAB}$')
            ax7.plot(i.dac_sweep_array[5:-7]*i.sab_dac_factor, dVmodmin_dIsafb[5:-7], label = 'dV$_{min}$/dI$_{SAB}$')
            ax7.set_title('Dynamic Resistance vs Bias Current', fontsize=16)
            ax7.set_ylabel('dV$_{SSA}$/dI$_{SAB}$ [$\mu$V/$\mu$A]', fontsize=14)
            ax7.set_xlabel('I$_{SAFB}$ [$\mu$A]', fontsize=14)
            ax7.legend()
            asymptote_max = np.mean(dVmodmax_dIsafb[-20:-5])
            asymptote_min = np.mean(dVmodmin_dIsafb[-12:-5])
            baseline = np.mean([np.mean(dVmodmax_dIsafb[20:60]), np.mean(dVmodmin_dIsafb[20:60])])
            ax7.axhline(y=asymptote_max, xmin=0, xmax=1, lw=0.5, ls='--', color='k')
            ax7.axhline(y=asymptote_min, xmin=0, xmax=1, lw=0.5, ls = '--', color='k')
            ax7.axhline(y=baseline, xmin=0, xmax=1, lw=0.5, ls = '--', color='k')
            ax7.text(i.dac_sweep_array[-1]*i.sab_dac_factor, asymptote_max*.8, '%.1f Ohms' %asymptote_max, \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)
            ax7.text(i.dac_sweep_array[-1]*i.sab_dac_factor, asymptote_min*1.1, '%.1f Ohms' %asymptote_min, \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)
            ax7.text(i.dac_sweep_array[10]*i.sab_dac_factor, baseline*10, '%.1f Ohms' %baseline, \
                    ha='center', va='center',color='blue',fontsize=8)          
            # plot 8: Device Transimpedance vs Device Volgtage
            ax8.plot(i.phase1_0_icmax_vphi[0:int(0.5*len(i.phase1_0_triangle))]*i.factor_adc_mV, dVdI_in_smooth)
            ax8.set_title('Device Transimpedance vs Device Voltage', fontsize=16)
            ax8.set_xlabel('V$_{SSA}$ input [mV]', fontsize=14)
            ax8.set_ylabel('dV$_{SSA}$/dI$_{in}$ [$\mu$V/$\mu$A]', fontsize=14)

            if args.pdf_report:
                pdf.savefig()
            #
            fig5, (ax9, ax10) = plt.subplots(2,1)
            fig5.set_size_inches(7.5, 10, forward=True)
            fig5.subplots_adjust(hspace=0.35)
            fig5.suptitle('Figure 5: device ' + i.chip_id, fontsize=14, fontweight='bold')
            # plot 9: Dynamic Resistance vs Current
            #rdyn is repeating twice, plot half to get cleaner data
            ax9.plot(i.phase0_1_triangle[0:int(0.5*len(rdyn))]*Mfb_scale_factor, rdyn_smooth[0:int(0.5*len(rdyn))])
            ax9.set_title('Dynamic Resistence vs Current', fontsize=16)
            ax9.set_xlabel('I$_{SAFB}$ [$\mu$A]', fontsize=14)
            ax9.set_ylabel('Resistance [$\Omega$]', fontsize=14)
            # plot 10: Dynamic Resistance vs Voltage
            #circles over itself 4 times within the range, plot only 1/4 to get cleaner plot
            ax10.plot(i.phase0_1_icmax_vphi[0:int(0.25*len(rdyn))]*i.factor_adc_mV, rdyn_smooth[0:int(0.25*len(rdyn))])
            ax10.set_title('Dynamic Resistance vs Voltage', fontsize=16)
            ax10.set_xlabel('V$_{SSA}$ feedback [mV]', fontsize=14)
            ax10.set_ylabel('Resistance [$\Omega$]', fontsize=14)
            #
            if args.pdf_report:
                pdf.savefig()
        #
        if args.pdf_report:
            pdf.close()

    if not args.pdf_report:
        plt.show()
    if args.interactive:
        IPython.start_ipython(argv=[], user_ns=locals())

if __name__ == '__main__':
    main()