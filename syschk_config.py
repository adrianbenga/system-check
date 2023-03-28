import logging
import subprocess as sp
from datetime import datetime

"""
This is the configuration file of the syschk.py monitoring tool,
containing definition of the variables, classes and functions 
that will the used in the main tool
"""

# ----------------------------------------------------------------------------
# Define the scope of the monitoring
# ----------------------------------------------------------------------------
os_checks = True
db_checks = True
asm_checks = True
rac_checks = True

# ----------------------------------------------------------------------------
# Variables defined to be used by syschk.py tool
# ----------------------------------------------------------------------------

install_path = "/home/oracle/monitoring_scripts"
logs_path = "/home/oracle/monitoring_scripts"
exec_user = "oracle"
hostname = "dbi-prod-1"
timebase=datetime.now().strftime("%Y-%B-%d %H:%M")
today = datetime.today()
log_file = '{}/{}_{}_{}.log'.format(logs_path, "syschk", hostname, today.strftime('%Y%m%d'))
trace_file = '{}/{}_{}_{}.trace'.format(logs_path, "syschk", hostname, today.strftime('%Y%m%d'))
encoding = "utf-8"

# ----------------------------------------------------------------------------
# Oracle specific variables
# ----------------------------------------------------------------------------

# oracle_host = '192.168.0.38'
oracle_host = '192.168.86.28'
oracle_user = 'system'
oracle_user_psswd = 'system123'
oracle_service = 'orcldb'
connect_string = f'{oracle_user}/{oracle_user_psswd}@{oracle_host}/{oracle_service}'
scan_listeners = ['LISTENER_SCAN1', 'LISTENER_SCAN2', 'LISTENER_SCAN3']
# scan_name = 'rac-scan.isctr-mt.ro'
scan_name = 'localhost'
scan_vips = ['scan1', 'scan2', 'scan3']
scan_connect_string = f'{oracle_user}/{oracle_user_psswd}@{scan_name}/{oracle_service}'



# ----------------------------------------------------------------------------
# Defined thresholds
# ----------------------------------------------------------------------------

# OS thresholds
# CPU thresholds
cpu_idle_critical_threshold = 0
cpu_idle_warning_threshold = 15
# Mem thresholds
mem_critical_threshold_percent = 0.05
mem_warning_threshold_percent = 0.1
# File systems thresholds
fs_used_critical_threshold = 95
fs_used_warning_threshold = 90

# ASM thresholds
# asm diskgroups occupancy thresholds
asm_dg_used_critical_threshold = 95
asm_dg_used_warning_threshold = 90

# Database thresholds
# tablespace occupancy thresholds
tbs_used_critical_threshold = 95
tbs_used_warning_threshold = 90

# ----------------------------------------------------------------------------
# Classes and functions to be used by systemcheck.py tool
# ----------------------------------------------------------------------------

# Print function to print to log file or console
def print_to_log(*records):
    with open(log_file, 'a') as log:
        for record in records:
            log.write(record)
        
def print_to_trace(*records):
    with open(trace_file, 'a') as trace:
        for record in records:
            trace.write(record)
        
def print_cmd_to_trace(cmd):
    cmd_output = sp.Popen(cmd, shell=True, stdout=sp.PIPE)
    [print_to_trace(line.decode(encoding)) for line in cmd_output.stdout.readlines()]

def print_cmd_to_log(cmd):
    cmd_output = sp.Popen(cmd, shell=True, stdout=sp.PIPE)
    [print_to_log(line.decode(encoding)) for line in cmd_output.stdout.readlines()]
    
def print_cmd_to_console(cmd):
    cmd_output = sp.Popen(cmd, shell=True, stdout=sp.PIPE)
    [print(line.strip().decode(encoding)) for line in cmd_output.stdout.readlines()]
    
# Function that returns the header taht separates the output to the log or console based on the 
# section that is executed

def output_head(cmd, section):
    if section:
        # header of the specific section
        header= "\n" + "-"*5 + f'\tSection "{section}"\t' + "-"*5 + "\n"
    else:
        # header of the specific command for traces only
        header= "\n" + "-"*5 + f'\tOutput of the command "{cmd}"\t' + "-"*5 + "\n\n"
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