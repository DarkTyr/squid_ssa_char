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


import matplotlib.pyplot as plt
import numpy as np
import time


#for date/time stamps on reports 
today = time.localtime()

#constants for calculations/unit conversions
#TODO: not sure how many of these are needed at all let alone wanted here vs in some config
phi0 = 2.06783383e-15   #magnetic flux quantum
scale_L = 1.0e18        #1/(pH*uA)
scale_uA = 1.0e6        #scale to microamps
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
#TODO: 99% sure these are in the daq config - adjust accordingly
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
def calculate_Ms():
    return

