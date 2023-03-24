import sys
import os
import re
import logging
import syschk_config as scc
import subprocess as sp
import cx_Oracle as cx
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

os_commands = ['sar 1 3', 'free -m', 'df -h']
# CPU thresholds
cpu_idle_critical_threshold = 0
cpu_idle_warning_threshold = 15
# Mem thresholds
mem_critical_threshold_percent = 0.05
mem_warning_threshold_percent = 0.1
# File systems thresholds
fs_used_critical_threshold = 95
fs_used_warning_threshold = 90
fs_tocheck_list = ['/', '/mnt/webapp_1', '/run']




def os_checks():
    check_section = "Operating system checks"
    section_header = output_head(section=check_section, cmd=None)
    
    # printing the section header
    (scc.print_to_log(section_header), scc.print_to_trace(section_header)) if arg1 == 'FILE' else print(section_header)
    for command in os_commands:
        cmd_output = sp.Popen(command, shell=True, stdout=sp.PIPE)
        cmd_header = output_head(section=None, cmd=command)
        (scc.print_to_trace(cmd_header), scc.print_cmd_to_trace(command), scc.print_to_trace('\n')) if arg1 == 'FILE' else None
        
        # parse the "sar" output, retain the Average line and the average idle value as integer
        if command.split()[0] == 'sar':
            avg_line = cmd_output.stdout.readlines()[-1]
            avg_idle = int(float(avg_line.split()[-1].decode(encoding)))
            if avg_idle == cpu_idle_critical_threshold:
                logger.critical(f"The system CPU idle is at {avg_idle} critical level!")
            elif avg_idle < cpu_idle_warning_threshold:
                logger.warning(f"The system CPU idle is {avg_idle}, below warning level!")
            else:
                logger.info(f"The system CPU idle is {avg_idle}.")
            
        # parse the "free -m" output, check if available is bigger than the defined thresholds
        # mem_critical_threshold < 5%
        # mem_warning_threshold < 10%
        if command.split()[0] == 'free':
            mem_line = cmd_output.stdout.readlines()[1]
            total_mem = int(float(mem_line.split()[1].decode(encoding)))
            free_mem = int(float(mem_line.split()[3].decode(encoding)))
            mem_critical_threshold = int(total_mem * mem_critical_threshold_percent)
            mem_warning_threshold = int(total_mem * mem_warning_threshold_percent)
            if free_mem < mem_critical_threshold:
                logger.critical(f"The system Free Memory is {free_mem} Mb, less than 5% of the total {total_mem} Mb!")
            elif free_mem < mem_warning_threshold:
                logger.warning(f"The system Free Memory is {free_mem} Mb, less than 10% of the total {total_mem} Mb!")
            else:
                logger.info(f"The system Free Memory is {free_mem} Mb, more than 10% of the total {total_mem} Mb.")

        # parse the file systems usage
        if command.split()[0] == 'df':
            for line in cmd_output.stdout.readlines()[1:]:
                fs = line.split()[-1].decode(encoding)
                fs_used_percent = int(line.split()[-2].decode(encoding)[:-1])
                if fs in fs_tocheck_list:
                    if fs_used_percent > fs_used_critical_threshold:
                        logger.critical(f"File system {fs} usage is {fs_used_percent}%!")
                    elif fs_used_percent > fs_used_warning_threshold:
                        logger.warning(f"File system {fs} usage is {fs_used_percent}%!")
                    else:
                        logger.info(f"File system {fs} usage is {fs_used_percent}%.")

# Function to perform database checks

db_sqls = [scc.sql_tbs_usage, scc.sql_db_bkp_check, scc.sql_arch_bkp_check]
# tablespace occupancy thresholds
tbs_used_critical_threshold = 95
tbs_used_warning_threshold = 90

def db_checks():
    # print specific section header
    check_section = "Database checks"
    section_header = output_head(section=check_section, cmd=None)
    (scc.print_to_log(section_header), scc.print_to_trace(section_header)) if arg1 == 'FILE' else print(section_header)
    
    # check if oracle service is responding
    try: 
        con = cx.connect(scc.connect_string)
    except cx.DatabaseError:
        logger.critical(f"Connection on host {scc.oracle_host} using oracle service {scc.oracle_service} is NOT possible!")
        logger.critical(f"Database checks cannot be performed until the connection to tthe database is fixed!!")
    else:
        logger.info(f"Connection on host {scc.oracle_host} using oracle service {scc.oracle_service} is OK!")

        # check size of the tablesapaces and free space as percentage (tbs_usage)
        for sql in db_sqls:
            cursor = con.cursor()
            cursor.execute(sql)
            if sql == scc.sql_tbs_usage:
                for row in cursor.fetchall():
                    tbs_name, tbs_type, tbs_size, tbs_used, tbs_free, tbs_used_percent = [*row]
                    # check if the tablespace has at list one autoextensible datafile
                    # if yes, the tablespace will autoextend
                    if tbs_type == 'TEMPORARY':
                        sql_tbs_autoext = f'select count(*) from dba_temp_files where tablespace_name = \'{tbs_name}\' and autoextensible = \'YES\''
                    else:
                        sql_tbs_autoext = f'select count(*) from dba_data_files where tablespace_name = \'{tbs_name}\' and autoextensible = \'YES\''
                    cursor1 = con.cursor()
                    cursor1.execute(sql_tbs_autoext)
                    tbs_autoextensible = 'ON' if int(cursor1.fetchone()[0]) >=1 else 'OFF'
                    if float(tbs_used_percent) >= tbs_used_critical_threshold and tbs_autoextensible == 'OFF':
                        logger.critical(f"Tablespace {tbs_name} usage is {tbs_used_percent}% and AUTOEXTEND is {tbs_autoextensible} for all datafiles!")
                    elif float(tbs_used_percent) >= tbs_used_critical_threshold and tbs_autoextensible == 'ON':
                        logger.info(f"Tablespace {tbs_name} usage is {tbs_used_percent}% and AUTOEXTEND is {tbs_autoextensible} for at least one datafile")
                    elif float(tbs_used_percent) >= tbs_used_warning_threshold and tbs_autoextensible == 'OFF':
                        logger.warning(f"Tablespace {tbs_name} usage is {tbs_used_percent}% and AUTOEXTEND is {tbs_autoextensible} for all datafiles!")
                    elif float(tbs_used_percent) >= tbs_used_warning_threshold and tbs_autoextensible == 'ON':
                        logger.info(f"Tablespace {tbs_name} usage is {tbs_used_percent}% and AUTOEXTEND is {tbs_autoextensible} for at least one datafile")
                    else:
                        logger.info(f"Tablespace {tbs_name} usage is {tbs_used_percent} and AUTOEXTEND is {tbs_autoextensible} for at least one datafile.")
            
            # checking the status of the last backup of the database and archivelog
            if sql == scc.sql_db_bkp_check or scc.sql_arch_bkp_check:
                for row in cursor.fetchall():
                    bkp_session_key, bkp_type, bkp_status, bkp_start_time, bkp_end_time, bkp_time_minutes = [*row]
                    bkp_scope = 'Database' if 'DB' in bkp_type else 'Archivelog' if 'ARCHIVELOG' in bkp_type else 'Unkown'
                    if bkp_status == 'COMPLETED':
                        logger.info(f"{bkp_scope} backup {bkp_type} is {bkp_status} on {bkp_end_time} and took {bkp_time_minutes} minutes.")
                    elif bkp_status == 'FAILED':
                        logger.critical(f"{bkp_scope}  backup {bkp_type} {bkp_status} on {bkp_end_time}!")
                    elif 'RUNNING' in bkp_status:
                        logger.info(f"{bkp_scope}  backup {bkp_type} is {bkp_status}, started on {bkp_start_time} and not yet completed.")
                    else:
                        logger.warning(f"{bkp_scope}  backup {bkp_type} {bkp_status} on {bkp_end_time}!")


# Function to perform listener checks

listener_commands = ['lsnrctl status',]

def listener_checks():
    # printing the section header
    check_section = "Listener checks"
    section_header = output_head(section=check_section, cmd=None)
    
    # printing the section header
    (scc.print_to_log(section_header), scc.print_to_trace(section_header)) if arg1 == 'FILE' else print(section_header)
    for command in listener_commands:
        cmd_output = sp.Popen(command, shell=True, stdout=sp.PIPE)
        return_code = cmd_output.wait()
        cmd_header = output_head(section=None, cmd=command)
        (scc.print_to_trace(cmd_header), scc.print_cmd_to_trace(command), scc.print_to_trace('\n')) if arg1 == 'FILE' else None
        
        # parse the "lsnrctl status" output, make sure listenr is started and the service is registered
        if command == 'lsnrctl status':
            if return_code != 0:
                logger.critical(f"Listener NOT started!")
            else:
                logger.info(f"Listener is started!")
                service_registered = False
                for line in cmd_output.stdout.readlines():
                    if f'Service "{scc.oracle_service}" has 1 instance' in line.strip().decode(encoding):
                        service_registered = True
                if service_registered:
                    logger.info(f"Service {scc.oracle_service} is registered with listener")
                else:
                    logger.critical(f"Service {scc.oracle_service} is NOT registered with listener")



# os_checks()
db_checks()
# listener_checks()