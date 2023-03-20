import sys
import os
import re
import logging
import subprocess as sp
from datetime import datetime

"""
This is the configuration file of the syschk.py monitoring tool,
containing definition of the variables, classes and functions 
that will the used in the main tool
"""

# Variables defined to be used by syschk.py tool

install_path = "/home/oracle/monitoring_scripts"
logs_path = "/var/log/systemcheck_logs"
exec_user = "oracle"
hostname = "dbi-prod-1"
timebase=datetime.now().strftime("%Y-%B-%d %H:%M")
today = datetime.today()
log_file = '{}_{}_{}.log'.format("syschk", hostname, today.strftime('%Y%m%d'))
trace_file = '{}_{}_{}.trace'.format("syschk", hostname, today.strftime('%Y%m%d'))
encoding = "utf-8"

# Classes and functions to be used by systemcheck.py tool

# Print function to print to log file, trace file or console
def print_to_log(record):
    with open(log_file, 'a') as log:
        log.write(record)
        
def print_to_trace(record):
    with open(trace_file, 'a') as trace:
        trace.write(record)
        
def print_cmd_to_trace(cmd):
    cmd_output = sp.Popen(cmd, shell=True, stdout=sp.PIPE)
    [print_to_trace(line.decode(encoding)) for line in cmd_output.stdout.readlines()]
    
def print_cmd_to_console(cmd):
    cmd_output = sp.Popen(cmd, shell=True, stdout=sp.PIPE)
    [print(line.strip().decode(encoding)) for line in cmd_output.stdout.readlines()]
    
# Function that returns the header taht separates the output to the log, trace or console based on the 
# section that i sexecuted

def output_head(cmd, section):
    if section:
        header="-"*100  + "\n" + "-"*100 + f'\n\tSection "{section}"\t\tDatetime: {timebase}\n' + "-"*100 + "\n" + "-"*100 + "\n"
    else:
        # header="-"*100 + f'\n\tOutput of the command "{cmd}"\t\tDatetime: {timebase}\n' + "-"*100 + "\n"
        header="\n" + "-"*10 + f'\tOutput of the command "{cmd}"\t' + "-"*10 + "\n\n"
    return header

# Class and function that will print messages to the console and logfile
class CustomFormatter(logging.Formatter):
    """Logging colored formatter, adapted from https://stackoverflow.com/a/56944256/3638629"""

    grey = '\x1b[38;21m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# create custom logger logging all five levels
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# define the format of the logs
fmt = '%(asctime)s | %(levelname)8s | %(message)s'

# create the stdout handler for logging to the console (logs all five levels)
stdout_handler = logging.StreamHandler()
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(CustomFormatter(fmt))

# create file handler for logging to a file (logs all five levels)
logfile_handler = logging.FileHandler(log_file)
logfile_handler.setLevel(logging.DEBUG)
logfile_handler.setFormatter(logging.Formatter(fmt))

# create file handler for the trace file (logs all five levels)
tracefile_handler = logging.FileHandler(trace_file)
tracefile_handler.setLevel(logging.DEBUG)
tracefile_handler.setFormatter(logging.Formatter(fmt))

# Examples of usage
# add both handlers to the logger
# logger.addHandler(stdout_handler)
# logger.addHandler(logfile_handler)
# logger.addHandler(tracefile_handler)

# logger.debug('This is a debug-level message')
# logger.info('This is an info-level message')
# logger.warning('This is a warning-level message')
# logger.error('This is an error-level message')
# logger.critical('This is a critical-level message')




