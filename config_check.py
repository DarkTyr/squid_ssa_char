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

# System wide imports
import os
import errno
import glob
import sys
import argparse
import textwrap
import IPython

# Installed package imports
import yaml

# Local imports


# In the future I envision the ability to have a prescedance level
# for the system_config file. If not in the CWD, then some user location
# and then a system level file (think, /etc/ in Linux)
# Because this is current be developed on Windows, things get weird
SSA_TEST_CONFIG_NAME = 'ssa_test_config.yaml'

if(sys.platform == 'win32'):
    SYSTEM_CONFIG_NAME = 'system_config.yaml'
    SYSTEM_CONFIG_YAML = '/etc/system_config.yaml'
    SSA_TEST_CONFIG_NAME = 'ssa_test_config.yaml'
    LOCAL_MODULE_CONFIG_PATH = '/conf_files/'
else:
    SYSTEM_CONFIG_NAME = 'system_config.yaml'
    SSA_TEST_CONFIG_NAME = 'ssa_test_config.yaml'
    # Last place to look for the system_config.yaml
    SYSTEM_CONFIG_YAML = '/etc/system_config.yaml'

HELP_TEXT = '''\
This script is to check the locations of the config files and
verify functionality of the configs. 

Currently a work in progress
'''
if (__name__ == '__main__'):
    cwd = os.getcwd()
    script_path = os.path.dirname(__file__)
    # Setup the flag and argument parser for the script
    parser = argparse.ArgumentParser(
        prog='config_check',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(HELP_TEXT))
    
    parser.add_argument('-s', '--sys_file_path', 
                        help='path to the system_config file')
    parser.add_argument('-c', '--config_file_path', 
                        help='path to config file')
    parser.add_argument('-v', '--verbosity', 
                        help='Set terminal debugging verbositiy',
                        action='count',
                        default=0)
    parser.add_argument('-i', '--interactive', 
                        help='Drop into Interactive mode',
                        action='store_true')
    args = parser.parse_args()

    sys_file_path = args.sys_file_path  
    if(sys_file_path == None):
        # Look in the directory where the script was called from
        sys_file_path = glob.glob(SYSTEM_CONFIG_NAME)
    if(sys_file_path == []):
        # if nothing in local directory, look in some system folder
        sys_file_path = glob.glob(SYSTEM_CONFIG_YAML)
    if(sys_file_path == []):
        sys_file_path = glob.glob(script_path + LOCAL_MODULE_CONFIG_PATH + SYSTEM_CONFIG_NAME)
    if(type(sys_file_path) == list):
        sys_file_path = sys_file_path[0]

    config_file_path = args.config_file_path
    if(args.config_file_path == None):
        # Look in the directory where the script was called from
        config_file_path = glob.glob(SSA_TEST_CONFIG_NAME)[0]


    print('_____Arguments_____')
    print('System Config File path: ' + sys_file_path[0]) #glob returns a list
    print('SSA test Config File Path: ' + str(args.config_file_path))
    print('Verbosity level: ' + str(args.verbosity))
    print('Interactive Flag: '+str(args.interactive))
    print('script location: ' + str(os.getcwd()))

    # Check that the config file paths are valid. If not, there is no point
    # in continuing
    if(sys_file_path == None):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                SYSTEM_CONFIG_NAME)
    if(sys_file_path == []):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                SYSTEM_CONFIG_NAME)
    if(config_file_path == None):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                SSA_TEST_CONFIG_NAME)
    if(config_file_path == []):
        raise FileNotFoundError('SSA Test Config File path not given')

    #####################################
    # Here we go, let us load up the yaml
    with open(sys_file_path, 'r') as file:
        try:
            sys_config = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            print(exc)
        
    with open(config_file_path, 'r') as file:
        try:
            test_config = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            print(exc)

        
    # If the argument for interactive was passed, drop into embeded IPython
    if(args.interactive):
        IPython.embed()

    # first check the number of columns list and verify it is valid
    num_columns = len(test_config['test_globals']['column'])