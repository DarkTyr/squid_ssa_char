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
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import time
from squid_ssa_char.modules import ssa_data_class
from scipy import interpolate

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
    

    #TODO: add .load after SSA_Data_Class
    data = [ssa_data_class.SSA_Data_Class(fnames[0])]
    for i in range(len(fnames) - 1):
        data.append(ssa_data_class.SSA_Data_Class(fnames[i + 1]))


    for i in data:
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
        intermediate01 = interpolate.splrep(i.phase0_1_triangle[0:int(0.5*len(i.phase0_1_triangle))], dVdI_fb[0:int(0.5*len(i.phase0_1_triangle))], k=2, s=15)
        intermediate10 = interpolate.splrep(i.phase1_0_triangle[0:int(0.5*len(i.phase1_0_triangle))], dVdI_in[0:int(0.5*len(i.phase1_0_triangle))], k=2, s=9)
        dVdI_fb_smooth = interpolate.splev(i.phase0_1_triangle[0:int(0.5*len(i.phase0_1_triangle))], intermediate01, der=0)*1000
        dVdI_in_smooth = interpolate.splev(i.phase1_0_triangle[0:int(0.5*len(i.phase1_0_triangle))], intermediate10, der=0)*1000

        #these are smoothed then derived - for phase00 data this method reduced noise without eliminating features 
        intermediate00_max = interpolate.splrep(i.dac_sweep_array, i.phase0_0_vmod_max, k=2, s=9)
        intermediate00_min = interpolate.splrep(i.dac_sweep_array, i.phase0_0_vmod_min, k=2, s=9)
        intermediate00_sab = interpolate.splrep(i.dac_sweep_array, i.phase0_0_vmod_sab, k=2, s=9)
        phase0_0_max_smooth = interpolate.splev(i.dac_sweep_array, intermediate00_max, der=0) 
        phase0_0_min_smooth = interpolate.splev(i.dac_sweep_array, intermediate00_min, der=0)
        phase0_0_vphi_smooth = interpolate.splev(i.dac_sweep_array, intermediate00_sab, der=0)
        dVmodmax_dIsab = np.gradient(phase0_0_max_smooth*i.factor_adc_mV*1000, i.dac_sweep_array*i.sab_dac_factor)
        dVmodmin_dIsab = np.gradient(phase0_0_min_smooth*i.factor_adc_mV*1000, i.dac_sweep_array*i.sab_dac_factor)
        dVdI_sab = np.gradient(phase0_0_vphi_smooth*i.factor_adc_mV*1000, i.dac_sweep_array*i.sab_dac_factor)
        
        #TODO: actually name the file path this is a HUGE filler right now
        if args.pdf_report:
            report_name = fname_path + '/' + fname + '.pdf'
            pdf = PdfPages(report_name)
            print('Generating Report: ', report_name)

        #TODO: currently it just makes everything for either argument, make more sophisticated
        if args.full_report or args.external_report:
            #start of plotting
            fig1, (ax1, ax2) = plt.subplots(2,1)
            fig1.set_size_inches(7.5, 10, forward=True)
            fig1.subplots_adjust(hspace=0.35)
            fig1.suptitle('Figure 1: device ' + i.chip_id, fontsize=14, fontweight='bold')
            # plot 1: mod depth [mV] vs SA bias current [uA]
            ax1.plot((i.dac_sweep_array * i.sab_dac_factor), (i.phase0_0_vmod_sab * i.factor_adc_mV))
            ax1.set_title('Voltage Modulation Depth vs Sa Bias')
            ax1.set_xlabel('I$_{SAB}$ [$\mu$A]')
            ax1.set_ylabel('SA Modulation Depth [mV]')
            ax1.axvline(x = i.dac_ic_min * i.sab_dac_factor, ymin=0, ymax=1, color='b', lw=0.5)
            ax1.axvline(x = i.dac_ic_max * i.sab_dac_factor, ymin=0, ymax=1, color='b', lw=0.5)
            ax1.axhline(y = np.max(i.phase0_0_vmod_sab * i.factor_adc_mV), xmin=0, xmax=1, color='b', lw=0.5)
            ax1.text(i.dac_ic_min * i.sab_dac_factor, np.max(i.phase0_0_vmod_sab * i.factor_adc_mV)*0.7, '$I_{cmin}$ \n %.1f $\mu$A' %(i.dac_ic_min*i.sab_dac_factor), \
                    ha='center', va='center', color = 'blue', backgroundcolor='w',fontsize=10)
            ax1.text(i.dac_ic_max * i.sab_dac_factor, np.max(i.phase0_0_vmod_sab * i.factor_adc_mV)*0.4, '$I_{cmax}$ \n %.1f $\mu$A' %(i.dac_ic_max*i.sab_dac_factor), \
                    ha='center', va='center', color = 'blue', backgroundcolor='w',fontsize=10)
            ax1.text((i.dac_sweep_array[-1]*i.sab_dac_factor)*.95, np.max(i.phase0_0_vmod_sab*i.factor_adc_mV)*0.97, \
                    '$V_{mod}$\n %.1f mV' %np.max(i.phase0_0_vmod_sab*i.factor_adc_mV), ha='center', va='center', color='blue', backgroundcolor ='w', fontsize=10)

            # plot 2: V_ssa_min and V_ssa_max [mV] vs SA bias [uA]
            #TODO: make labels for legend more accurate
            ax2.plot((i.dac_sweep_array * i.sab_dac_factor), (i.phase0_0_vmod_min * i.factor_adc_mV), label = '$V_{min}$')
            ax2.plot((i.dac_sweep_array * i.sab_dac_factor), (i.phase0_0_vmod_max * i.factor_adc_mV), label = '$V_{max}$')
            ax2.set_title('')
            ax2.set_ylabel('SSA Voltage [mV]')
            ax2.set_xlabel('I$_{SAB}$ [$\mu$A]')
            ax2.legend()
            ax2.text(np.max(i.dac_sweep_array*i.sab_dac_factor)*.95, np.max(i.phase0_0_vmod_min*i.factor_adc_mV)*.65, '$V_{min}$', ha='center', va='center', color='black', backgroundcolor='w',fontsize=10)
            
            if args.pdf_report:
                pdf.savefig()


            fig2, (ax3, ax4) = plt.subplots(2,1)
            fig2.set_size_inches(7.5, 10, forward=True)
            fig2.subplots_adjust(hspace=0.35)
            fig2.suptitle('Figure 2: device ' + i.chip_id, fontsize=14, fontweight='bold')
            # plot 3: Vssa [mV] vs Iin [uA], Min marked on this plot
            ax3.plot((i.phase1_0_triangle * Min_scale_factor), (i.phase1_0_icmax_vphi * i.factor_adc_mV))
            ax3.set_title('Device Voltage vs Input Current at at I$_{cmax}$')
            ax3.set_ylabel('Device Voltage [mV]')
            ax3.set_xlabel('SAIN Current [$\mu$A]')
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
            ax4.plot((i.phase1_0_triangle[0:int(0.5*len(i.phase1_0_triangle))])*Min_scale_factor, dVdI_in_smooth)
            ax4.set_title('SA Input Gain vs SA Input Current at I$_{cmax}$')
            ax4.set_ylabel('dV$_{dev}$/dI$_{SAIN}$ [$\mu$V/$\mu$A]')
            ax4.set_xlabel('SAIN Current [$\mu$A]')
            ax4.set_xlim(0, sain_xlim)
            ax4.axhline(y=np.max(dVdI_in_smooth), xmin=0, xmax=1, lw=0.5)
            ax4.axhline(y=np.min(dVdI_in_smooth), xmin=0, xmax=1, lw=0.5)
            ax4.text(sain_xlim*0.95, np.min(dVdI_in_smooth), '%.1f' %np.min(dVdI_fb_smooth), \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)
            ax4.text(sain_xlim*0.95, np.max(dVdI_in_smooth), '%.1f' %np.max(dVdI_fb_smooth), \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)

            if args.pdf_report:
                pdf.savefig()          
            
            # plot 5: Vssa [mV] vs Ifab [uA], Mfb marked on this plot
            fig3, (ax5, ax6) = plt.subplots(2,1)
            fig3.set_size_inches(7.5, 10, forward=True)
            fig3.subplots_adjust(hspace=0.35)
            fig3.suptitle('Figure 3: device ' + i.chip_id, fontsize=14, fontweight='bold')
            ax5.plot((i.phase0_1_triangle * Mfb_scale_factor), (i.phase0_1_icmax_vphi * i.factor_adc_mV))
            ax5.set_title('Device Voltage vs Feedback Current at I$_{cmax}$')
            ax5.set_ylabel('Device Voltage [mV]')
            ax5.set_xlabel('SAFB Current [$\mu$A]')
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
            ax6.plot((i.phase0_1_triangle[0:int(0.5*len(i.phase0_1_triangle))])*Mfb_scale_factor, dVdI_fb_smooth)
            ax6.set_title('Feedback Gain vs Feedback Current at I$_{cmax}$')
            ax6.set_ylabel('dV$_{dev}$/dI$_{SAFB}$ [$\mu$V/$\mu$A]')
            ax6.set_xlabel('SAFB Current [$\mu$A]')
            ax6.set_xlim(0, safb_xlim)
            ax6.axhline(y=np.max(dVdI_fb_smooth), xmin=0, xmax=1, lw=0.5)
            ax6.axhline(y=np.min(dVdI_fb_smooth), xmin=0, xmax=1, lw=0.5)
            ax6.text(safb_xlim*0.95, np.min(dVdI_fb_smooth), '%.1f' %np.min(dVdI_fb_smooth), \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)
            ax6.text(safb_xlim*0.95, np.max(dVdI_fb_smooth), '%.1f' %np.max(dVdI_fb_smooth), \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)

            if args.pdf_report:
                pdf.savefig()        

            fig4, (ax7, ax8) = plt.subplots(2,1)
            fig4.set_size_inches(7.5, 10, forward=True)
            fig4.subplots_adjust(hspace=0.35)
            fig4.suptitle('Figure 4: device ' + i.chip_id, fontsize=14, fontweight='bold')
            # plot 7: dVssa/dIsab vs Isab
            #TODO: update title and axes labels
            ax7.plot(i.dac_sweep_array*i.sab_dac_factor, dVmodmax_dIsab, label = 'dV$_{max}$/dI$_{SAB}$')
            ax7.plot(i.dac_sweep_array*i.sab_dac_factor, dVmodmin_dIsab, label = 'dV$_{min}$/dI$_{SAB}$')
            ax7.set_title('Not sure What this is called just yet')
            ax7.set_ylabel('dV$_{SSA}$/dI$_{SAB}$ [$\mu$V/$\mu$A]')
            ax7.set_xlabel('I$_{SAB}$ [$\mu$A]')
            ax7.legend()
            asymptote_max = np.mean(dVmodmax_dIsab[-7:-1])
            asymptote_min = np.mean(dVmodmin_dIsab[-7:-1])
            baseline = np.mean([np.mean(dVmodmax_dIsab[0:10]), np.mean(dVmodmin_dIsab[0:10])])
            ax7.axhline(y=asymptote_max, xmin=0, xmax=1, lw=0.5, ls='--', color='k')
            ax7.axhline(y=asymptote_min, xmin=0, xmax=1, lw=0.5, ls = '--', color='k')
            ax7.axhline(y=baseline, xmin=0, xmax=1, lw=0.5, ls = '--', color='k')
            ax7.text(i.dac_sweep_array[-1]*i.sab_dac_factor, dVmodmax_dIsab[-1]*.8, '%.1f ohms' %asymptote_max, \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)
            ax7.text(i.dac_sweep_array[-1]*i.sab_dac_factor, dVmodmin_dIsab[-1]*1.2, '%.1f ohms' %asymptote_min, \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)
            ax7.text(i.dac_sweep_array[-1]*i.sab_dac_factor, baseline*1.2, '%.1f ohms' %baseline, \
                    ha='center', va='center',color='blue',backgroundcolor='w',fontsize=8)          
            # plot 8: dV/dIin vs Vssa
            #           transimpedance? - TODO: malcolm also wanted this bs Ifbx but I think thats already in ax4? derivative of Vssa vs Iin vs Iin?
            ax8.plot(i.phase1_0_icmax_vphi[0:int(0.5*len(i.phase1_0_triangle))]*i.factor_adc_mV, dVdI_in_smooth)
            ax8.set_title('Device Transimpedance vs Device Voltage')
            ax8.set_xlabel('V$_{SSA}$ input [mV]')
            ax8.set_ylabel('dV$_{SSA}$/dI$_{in}$ [$\mu$V/$\mu$A]')

            if args.pdf_report:
                pdf.savefig()
            #
            fig5, (ax9, ax10) = plt.subplots(2,1)
            fig5.set_size_inches(7.5, 10, forward=True)
            fig5.subplots_adjust(hspace=0.35)
            fig5.suptitle('*THIS IS WRONG* Figure 5: device ' + i.chip_id, fontsize=14, fontweight='bold')
            # plot 9: dV/dIsab vs Vssa
            #           dynamic resistance TODO: update title, check if data products are right (unlikely)
            ax9.plot(i.phase0_0_vmod_sab*i.factor_adc_mV, dVdI_sab)
            ax9.set_title('Not sure what this is or if its right YAY')
            ax9.set_xlabel('V$_{SSA}$ [mV]')
            ax9.set_ylabel('dV$_{SSA}$/dI$_{SAB}$')
            # plot 10: dV/dIsab vs Ifbx
            #           also dynamic resisance? TODO: update title, check if data products are right (unlikely)
            ax10.plot(i.phase0_1_triangle[0:len(dVdI_sab)]*Mfb_scale_factor, dVdI_sab)
            ax10.set_title('Same as above my dude')
            ax10.set_xlabel('I$_{FBX}$')
            ax10.set_ylabel('dV$_{SSA}$/dI$_{SAB}$')
            #
            if args.pdf_report:
                pdf.savefig()
        #
        if args.pdf_report:
            pdf.close()
        elif not args.pdf_report:
            plt.show()