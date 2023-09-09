#################################################################################
#
# Written by: Johnathon Gard, Erin Maloney
# Purpose: Process the local testing YAML file and system YAML
#
# This will be a test script that will readin the two YAML files and ensure that
# it will process correctly. Ex. When we call set_tower_voltage, we know
# the correct tower voltage on the corrct address and channel numbers.
# This file will also be used to verify the commanding of the TDM crate with
# the relevant parameters. 
#
# September 2023
#
#################################################################################

# System wide imports
import os
import glob
import sys

# Installed package imports
import yaml

# Local imports

if(sys.platform == 'win32'):
    SYSTEM_CONFIG_NAME = '\\system_config.yaml'
    SYSTEM_CONFIG_YAML = '/etc/system_config.yaml'
else:
    SYSTEM_CONFIG_NAME = 'system_config.yaml'
    # Last place to look for the system_config.yaml
    SYSTEM_CONFIG_YAML = '/etc/system_config.yaml'

# determine current working directoy from where the script was called
cwd = os.getcwd()

# get a list of files using glob
file_name = glob.glob(cwd + SYSTEM_CONFIG_NAME)

# If glob returned an empty array, print that we didn't find anything, else print file names
if(file_name == []):
    print("No Files Found!!")

for i in file_name:
    print(i)




