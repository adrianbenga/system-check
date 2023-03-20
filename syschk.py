import sys
import os
import re
import logging
import syschk_config as scc
import subprocess as sp
from datetime import datetime
from syschk_config import logger, output_head

# Setting logger output, default to the console
logger.addHandler(scc.stdout_handler)

# ----------------------------------------------------------------------------
# Managing script arguments
# ----------------------------------------------------------------------------
nb_arguments = 1
arg_list = sys.argv
arg1 = arg_list[1].upper()
encoding = "utf-8"
if len(arg_list) < nb_arguments + 1:
    logger.error('Output argument is mandatory and must be set to "console" or "logfile"')
    exit(1)
else:
    if arg1 == 'CONSOLE':
        logger.addHandler(scc.stdout_handler)
    elif arg1 == 'FILE':
        logger.addHandler(scc.logfile_handler)
        logger.addHandler(scc.tracefile_handler)
    else:
        logger.error('The first argument is mandatory and must be "console" or "file"')
        exit(1)

# Function to perform operating system checks


command = 'dir'
# command = 'sar 1 3'
def os_checks():
    check_section = "Operating system checks"
    header = output_head(section=check_section, cmd=None)
    if arg1 == 'FILE':
        scc.print_to_log(header)
        scc.print_to_trace(header)
    else:
        print(header)
    header = output_head(section=None, cmd=command)
    scc.print_to_trace(header)
    scc.print_cmd_to_trace(command)
    scc.print_cmd_to_console(command)
    
os_checks()
    
