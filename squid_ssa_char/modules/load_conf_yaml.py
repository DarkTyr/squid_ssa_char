#################################################################################
#
# Written by: Johnathon Gard, Erin Maloney
# Purpose: Process the local testing YAML file and system YAML
#
# This module will check given file paths and load up the yaml configs for the
# system and ssa_testing. This module will also apply precedence for finding
# the system_config.yaml file. The testing config file is easy, either from 
# where the script was called or given explicitly.
#
# September 2023
#
#################################################################################
# TODO: CRITICAL Check functionality on Linux!

# System Level imports
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

# Local class defines that might be OS dependent
SSA_TEST_CONFIG_NAME = 'ssa_test_config.yaml'

if(sys.platform == 'win32'):
    SYSTEM_CONFIG_NAME = 'system_config.yaml'
    SYSTEM_CONFIG_YAML = '\\etc\\system_config.yaml'
    SSA_TEST_CONFIG_NAME = 'ssa_test_config.yaml'
    LOCAL_MODULE_CONFIG_PATH = '\\..\\conf_files\\'
else:
    SYSTEM_CONFIG_NAME = 'system_config.yaml'
    SSA_TEST_CONFIG_NAME = 'ssa_test_config.yaml'
    # Last place to look for the system_config.yaml
    SYSTEM_CONFIG_YAML = '/etc/system_config.yaml'
    LOCAL_MODULE_CONFIG_PATH = '/../conf_files/'

class Load_Conf_YAML:
    # Text before INIT
    def __init__(self, test_config_path_arg='', system_config_path_arg=None, verbosity=0):
        #Text After Init
        self.verbosity = verbosity
        self.cwd = os.getcwd()
        self.class_file_path = os.path.dirname(__file__)
        self.system_config_path_arg = system_config_path_arg
        self.test_config_path_arg = test_config_path_arg
        self.sys_file_path = []
        self.config_file_path = []

        # Check the file paths and apply precedence
        self.check_system_conf_path()
        self.check_test_conf_path()
        if(self.verbosity != 0):
            print('_______Arguments_______')
            print('Current Working Directory: ' + self.cwd)
            print('  System Config File path: ' + self.sys_file_path)
            print('SSA test Config File Path: ' + self.config_file_path )
            print('          Verbosity level: ' + str(self.verbosity))

    def check_system_conf_path(self):
        if(self.system_config_path_arg  == None):
        # Look in the directory where the script was called from
            self.sys_file_path = glob.glob(SYSTEM_CONFIG_NAME)
            if(self.sys_file_path == []):
                # if nothing in local directory, look in some system folder
                self.sys_file_path = glob.glob(SYSTEM_CONFIG_YAML)
                if(self.sys_file_path == []):
                    self.sys_file_path = glob.glob(self.class_file_path + LOCAL_MODULE_CONFIG_PATH + SYSTEM_CONFIG_NAME)
        else:
            self.sys_file_path = glob.glob(self.system_config_path_arg)

        # Check that the config file paths are valid. If not, there is no point
        # in continuing so raise an exception
        if(self.sys_file_path == None):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                    SYSTEM_CONFIG_NAME)
        if(self.sys_file_path == []):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                    SYSTEM_CONFIG_NAME)
    
        # Pull the paths out of the lists glob returned
        if(type(self.sys_file_path) == list and len(self.sys_file_path) > 0):
            self.sys_file_path = self.sys_file_path[0]

    def check_test_conf_path(self):
        # pass the config_file_path to the glob function and see if it is there, if None, load from CWD
        # 1. passed in with -s flag
        # 2. Local directory
        if((self.test_config_path_arg == '') or (self.test_config_path_arg == None)):
            # Look in the directory where the script was called from
            self.config_file_path = glob.glob(SSA_TEST_CONFIG_NAME)
        else:
            self.config_file_path = glob.glob(self.test_config_path_arg)

        if(self.config_file_path == None):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                    SSA_TEST_CONFIG_NAME)
        if(self.config_file_path == []):
            raise FileNotFoundError('SSA Test Config File path not given, no file found in Current Working Directory')
        
        # Pull the paths out of the lists glob returned
        if(type(self.config_file_path) == list and len(self.config_file_path) > 0):
            self.config_file_path = self.config_file_path[0]

    def read_system_config(self):
        with open(self.sys_file_path, 'r') as file:
            try:
                self.sys_config = yaml.safe_load(file)
                return self.sys_config
            except yaml.YAMLError as exc:
                print(exc)

    def read_test_config(self):
        with open(self.config_file_path, 'r') as file:
            try:
                self.test_config = yaml.safe_load(file)
                return self.test_config
            except yaml.YAMLError as exc:
                print(exc)
