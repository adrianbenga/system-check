import sys
import os
import re
import logging
import subprocess as sp
from datetime import datetime
import cx_Oracle as cx


"""
This is the configuration file of the syschk.py monitoring tool,
containing definition of the variables, classes and functions 
that will the used in the main tool
"""

# Variables defined to be used by syschk.py tool

install_path = "/home/oracle/monitoring_scripts"
logs_path = "/home/user/Desktop/Projects/ISCTR/Monitoring tools/system-check"
exec_user = "oracle"
hostname = "dbi-prod-1"
timebase=datetime.now().strftime("%Y-%B-%d %H:%M")
today = datetime.today()
log_file = '{}/{}_{}_{}.log'.format(logs_path, "syschk", hostname, today.strftime('%Y%m%d'))
trace_file = '{}/{}_{}_{}.trace'.format(logs_path, "syschk", hostname, today.strftime('%Y%m%d'))
encoding = "utf-8"

# Oracle specific variables

oracle_host = '192.168.0.38'
oracle_user = 'system'
oracle_user_psswd = 'system123'
oracle_service = 'orcldb'
connect_string = f'{oracle_user}/{oracle_user_psswd}@{oracle_host}/{oracle_service}'

# Classes and functions to be used by systemcheck.py tool

# Print function to print to log file, trace file or console
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
    
# Function that returns the header taht separates the output to the log, trace or console based on the 
# section that i sexecuted

def output_head(cmd, section):
    if section:
        header="-"*100  + "\n" + "-"*100 + f'\n\tSection "{section}"\t\tDatetime: {timebase}\n' + "-"*100 + "\n" + "-"*100 + "\n"
    else:
        # header="-"*100 + f'\n\tOutput of the command "{cmd}"\t\tDatetime: {timebase}\n' + "-"*100 + "\n"
        header="\n" + "-"*20 + f'\tOutput of the command "{cmd}"\t' + "-"*20 + "\n\n"
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
logfile_handler = logging.FileHandler(log_file, 'a')
logfile_handler.setLevel(logging.DEBUG)
logfile_handler.setFormatter(logging.Formatter(fmt))

# create file handler for the trace file (logs all five levels)
tracefile_handler = logging.FileHandler(trace_file, 'a')
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

# SQL statements for Oracle database check section

sql_tbs_usage = """
    SELECT
    dts.tablespace_name,
    NVL(ddf.bytes / 1024 / 1024, 0) avail,
    NVL(ddf.bytes - NVL(dfs.bytes, 0), 0)/1024/1024 used,
    NVL(dfs.bytes / 1024 / 1024, 0) free,
    TO_CHAR(NVL((ddf.bytes - NVL(dfs.bytes, 0)) / ddf.bytes * 100, 0), '990.0') pctused
    FROM
    sys.dba_tablespaces dts,
    (select tablespace_name, sum(bytes) bytes
    from dba_data_files group by tablespace_name) ddf,
    (select tablespace_name, sum(bytes) bytes
    from dba_free_space group by tablespace_name) dfs
    WHERE
    dts.tablespace_name = ddf.tablespace_name(+)
    AND dts.tablespace_name = dfs.tablespace_name(+)
    AND NOT (dts.extent_management like 'LOCAL'
    AND dts.contents like 'TEMPORARY')
    UNION ALL
    SELECT
    dts.tablespace_name,
    NVL(dtf.bytes / 1024 / 1024, 0) avail,
    NVL(t.bytes, 0)/1024/1024 used,
    NVL(dtf.bytes - NVL(t.bytes, 0), 0)/1024/1024 free,
    TO_CHAR(NVL(t.bytes / dtf.bytes * 100, 0), '990.0') as pctused
    FROM
    sys.dba_tablespaces dts,
    (select tablespace_name, sum(bytes) bytes
    from dba_temp_files group by tablespace_name) dtf,
    (select tablespace_name, sum(bytes_used) bytes
    from v$temp_space_header group by tablespace_name) t
    WHERE
    dts.tablespace_name = dtf.tablespace_name(+)
    AND dts.tablespace_name = t.tablespace_name(+)
    AND dts.extent_management like 'LOCAL'
    AND dts.contents like 'TEMPORARY'
    order by 1
"""

sql_db_bkp_check = """
    SELECT SESSION_KEY, INPUT_TYPE, STATUS,
    TO_CHAR(START_TIME,'mm/dd/yy hh24:mi') start_time,
    TO_CHAR(END_TIME,'mm/dd/yy hh24:mi') end_time,
    ELAPSED_SECONDS/60 min
    FROM V$RMAN_BACKUP_JOB_DETAILS
    WHERE INPUT_TYPE LIKE 'DB %'
    ORDER BY SESSION_KEY DESC FETCH FIRST 1 ROWS ONLY
"""

sql_arch_bkp_check = """
    SELECT SESSION_KEY, INPUT_TYPE, STATUS,
    TO_CHAR(START_TIME,'mm/dd/yy hh24:mi') start_time,
    TO_CHAR(END_TIME,'mm/dd/yy hh24:mi') end_time,
    ELAPSED_SECONDS/60 min
    FROM V$RMAN_BACKUP_JOB_DETAILS
    WHERE INPUT_TYPE LIKE 'ARCHIVELOG'
    ORDER BY SESSION_KEY DESC FETCH FIRST 1 ROWS ONLY
"""




