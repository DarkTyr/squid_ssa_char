#################################################################################
#
# Written by: Johnathon Gard, Erin Maloney
# Purpose: Process the local testing YAML file and system YAML
#
# This will be a test script that will readin the two YAML files and ensure that
# it will process correctly. Ex. When we call set_tower_voltage, we know
# the correct tower voltage on the corrct address and channel numbers.
# This file will also be used to verify the commanding of the TDM crate with
# the relevant parameters. It will also be used to check the presense of the
# configuration files.
#
# September 2023
#
#################################################################################

# System Level imports
import os
import errno
import glob
import sys
import argparse

# Installed package imports
import yaml

# Local imports

SSA_TEST_CONFIG_NAME = 'ssa_test_config.yaml'

if(sys.platform == 'win32'):
    SYSTEM_CONFIG_NAME = 'system_config.yaml'
    SYSTEM_CONFIG_YAML = '/etc/system_config.yaml'
    SSA_TEST_CONFIG_NAME = 'ssa_test_config.yaml'
else:
    SYSTEM_CONFIG_NAME = 'system_config.yaml'
    SSA_TEST_CONFIG_NAME = 'ssa_test_config.yaml'
    # Last place to look for the system_config.yaml
    SYSTEM_CONFIG_YAML = '/etc/system_config.yaml'


# determine current working directoy from where the script was called
cwd = os.getcwd()

# get a list of files using glob
file_name = glob.glob(cwd + SYSTEM_CONFIG_NAME)

# If glob returned an empty array, print that we didn't find anything, else print file names
if(file_name == []):
    print('No system_config.yaml Files Found!!')

for i in file_name:
    print(i)


if (__name__ == '__main__'):
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--sys_file', help='path to the system_config file')
    parser.add_argument('-c', '--config_file', help='path to config file')
    parser.add_argument('-v', '--verbosity', help='Set terminal debugging verbositiy', action='count', defaul=0)
    parser.add_argument('-i', '--interactive', help='Drop into Interactive mode')
    args = parser.parse_args()

    sys_file = args.sys_file
    if(args.sys_file == None):
        # Look in the directory where the script was called from
        sys_file = glob.glob(SYSTEM_CONFIG_NAME)
        if(sys_file == []):
            # if nothing in local directory, look in some system folder
            sys_file = glob.glob(SYSTEM_CONFIG_YAML)

    config_file = args.config_file
    if(args.config_file == None):
        # Look in the directory where the script was called from
        config_file = glob.glob(SSA_TEST_CONFIG_NAME)


    print('_____Arguments_____')
    print('System Config File path: ' + args.sys_file)
    print('SSA test Config File Path: ' + args.config_file)

    if(sys_file == None):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                SYSTEM_CONFIG_NAME)
    if(config_file == None):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                SSA_TEST_CONFIG_NAME)
    


