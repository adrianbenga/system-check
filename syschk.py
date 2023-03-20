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

commands = ['sar 1 3', 'vmstat 1 3']
def os_checks():
    check_section = "Operating system checks"
    section_header = output_head(section=check_section, cmd=None)
    (scc.print_to_log(section_header), scc.print_to_trace(section_header)) if arg1 == 'FILE' else print(section_header)
    for command in commands:
        if arg1 == 'FILE':
            cmd_header = output_head(section=None, cmd=command)
            scc.print_to_log(cmd_header)
            scc.print_to_trace(cmd_header)
            scc.print_cmd_to_log(command)
            scc.print_cmd_to_trace(command)
        elif arg1 == 'CONSOLE':
            cmd_header = output_head(section=None, cmd=command)
            print(cmd_header)
            scc.print_cmd_to_console(command)
        
os_checks()
    
