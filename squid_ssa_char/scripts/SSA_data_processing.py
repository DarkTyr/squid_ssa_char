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

#first calculate the needed values for demarkation in the plots
#this includes converting from ADC values
#TODO: do unit conversions in here too or nah?
def calculate_Ms():
    return

