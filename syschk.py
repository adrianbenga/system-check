import sys
import logging
import syschk_config as scc
import subprocess as sp
import cx_Oracle as cx
from syschk_config import logger, output_head

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
        # create the stdout handler for logging to the console (logs all five levels)
        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.setFormatter(scc.CustomFormatter(scc.fmt))
        logger.addHandler(stdout_handler)
    elif arg1 == 'FILE':
        # create file handler for logging to a file (logs all five levels)
        logfile_handler = logging.FileHandler(scc.log_file, 'a')
        logfile_handler.setLevel(logging.DEBUG)
        logfile_handler.setFormatter(logging.Formatter(scc.fmt))
        logger.addHandler(logfile_handler)
        
    else:
        logger.error('The first argument is mandatory and must be "console" or "file"')
        exit(1)

# ----------------------------------------------------------------------------
# Function to perform operating system checks
# ----------------------------------------------------------------------------

def os_checks():
    check_section = "Operating system checks"
    section_header = output_head(section=check_section, cmd=None)
    
    # printing the section header
    scc.print_to_log(section_header) if arg1 == 'FILE' else print(section_header)
    for command in os_commands:
        cmd_output = sp.Popen(command, shell=True, stdout=sp.PIPE)
        # parse the "sar" output, retain the Average line and the average idle value as integer
        if command.split()[0] == 'sar':
            avg_line = cmd_output.stdout.readlines()[-1]
            avg_idle = int(float(avg_line.split()[-1].decode(encoding)))
            if avg_idle == scc.cpu_idle_critical_threshold:
                logger.critical(f"The system CPU idle is at {avg_idle} critical level!")
            elif avg_idle < scc.cpu_idle_warning_threshold:
                logger.warning(f"The system CPU idle is {avg_idle}, below warning level!")
            else:
                logger.info(f"The system CPU idle is {avg_idle}.")
            
        # parse the "free -m" output, check if available is bigger than the defined thresholds
        # mem_critical_threshold_percent < 5%
        # mem_warning_threshold_percent < 10%
        if command.split()[0] == 'free':
            mem_line = cmd_output.stdout.readlines()[1]
            total_mem = int(float(mem_line.split()[1].decode(encoding)))
            free_mem = int(float(mem_line.split()[3].decode(encoding)))
            mem_critical_threshold = int(total_mem * scc.mem_critical_threshold_percent)
            mem_warning_threshold = int(total_mem * scc.mem_warning_threshold_percent)
            if free_mem < mem_critical_threshold:
                logger.critical(f"The system Free Memory is {free_mem} Mb, less than 5% of the total {total_mem} Mb!")
            elif free_mem < mem_warning_threshold:
                logger.warning(f"The system Free Memory is {free_mem} Mb, less than 10% of the total {total_mem} Mb!")
            else:
                logger.info(f"The system Free Memory is {free_mem} Mb, more than 10% of the total {total_mem} Mb.")

        # parse the file systems usage "df -h", check if we have space in FS available more than the specified thresholds
        # fs_used_critical_threshold = 95
        # fs_used_warning_threshold = 90
        if command.split()[0] == 'df':
            for line in cmd_output.stdout.readlines()[1:]:
                fs = line.split()[-1].decode(encoding)
                fs_used_percent = int(line.split()[-2].decode(encoding)[:-1])
                if fs in fs_tocheck_list:
                    if fs_used_percent > scc.fs_used_critical_threshold:
                        logger.critical(f"File system {fs} usage is {fs_used_percent}%. Less than {(100 - scc.fs_used_critical_threshold)} space available!")
                    elif fs_used_percent > scc.fs_used_warning_threshold:
                        logger.warning(f"File system {fs} usage is {fs_used_percent}%. Less than {(100 - scc.fs_used_warning_threshold)} space available!")
                    else:
                        logger.info(f"File system {fs} usage is {fs_used_percent}%.")

# ----------------------------------------------------------------------------
# Function to perform listener checks
# ----------------------------------------------------------------------------

def listener_checks():
    # printing the section header
    check_section = "Local listener checks"
    section_header = output_head(section=check_section, cmd=None)
    scc.print_to_log(section_header) if arg1 == 'FILE' else print(section_header)
    
    for command in listener_commands:
        cmd_output = sp.Popen(command, shell=True, stdout=sp.PIPE)
        return_code = cmd_output.wait()
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

# ----------------------------------------------------------------------------
# Function to perform database checks
# ----------------------------------------------------------------------------

def db_checks():
    # print specific section header
    check_section = "Database checks"
    section_header = output_head(section=check_section, cmd=None)
    scc.print_to_log(section_header) if arg1 == 'FILE' else print(section_header)
    
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
            if sql == sql_tbs_usage:
                for row in cursor.fetchall():
                    tbs_name, tbs_type, tbs_size, tbs_used, tbs_free, tbs_used_percent = [*row]
                    # check if the tablespace has at list one autoextensible datafile
                    # if yes, the tablespace will autoextend so we need to check the free space in ASM disk group
                    if tbs_type == 'TEMPORARY':
                        sql_tbs_autoext = f'select count(*) from dba_temp_files where tablespace_name = \'{tbs_name}\' and autoextensible = \'YES\''
                    else:
                        sql_tbs_autoext = f'select count(*) from dba_data_files where tablespace_name = \'{tbs_name}\' and autoextensible = \'YES\''
                    cursor1 = con.cursor()
                    cursor1.execute(sql_tbs_autoext)
                    tbs_autoextensible = 'ON' if int(cursor1.fetchone()[0]) >=1 else 'OFF'
                    if float(tbs_used_percent) >= scc.tbs_used_critical_threshold and tbs_autoextensible == 'OFF':
                        logger.critical(f"Tablespace {tbs_name} usage is {tbs_used_percent}% and AUTOEXTEND is {tbs_autoextensible} for all datafiles!")
                    elif float(tbs_used_percent) >= scc.tbs_used_critical_threshold and tbs_autoextensible == 'ON':
                        logger.info(f"Tablespace {tbs_name} usage is {tbs_used_percent}% and AUTOEXTEND is {tbs_autoextensible} for at least one datafile.")
                    elif float(tbs_used_percent) >= scc.tbs_used_warning_threshold and tbs_autoextensible == 'OFF':
                        logger.warning(f"Tablespace {tbs_name} usage is {tbs_used_percent}% and AUTOEXTEND is {tbs_autoextensible} for all datafiles!")
                    elif float(tbs_used_percent) >= scc.tbs_used_warning_threshold and tbs_autoextensible == 'ON':
                        logger.info(f"Tablespace {tbs_name} usage is {tbs_used_percent}% and AUTOEXTEND is {tbs_autoextensible} for at least one datafile")
                    else:
                        logger.info(f"Tablespace {tbs_name} usage is {tbs_used_percent} and AUTOEXTEND is {tbs_autoextensible} for at least one datafile.")
            
            # checking the status of the last backup of the database and archivelog
            if sql == sql_db_bkp_check or sql_arch_bkp_check:
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

# ----------------------------------------------------------------------------
# Function to perform ASM checks
# ----------------------------------------------------------------------------

def asm_checks():
    # print specific section header
    check_section = "Automatic Storage Management checks"
    section_header = output_head(section=check_section, cmd=None)
    scc.print_to_log(section_header) if arg1 == 'FILE' else print(section_header)
    
    # check if oracle service is responding
    try: 
        con = cx.connect(scc.connect_string)
    except cx.DatabaseError:
        logger.critical(f"Connection on host {scc.oracle_host} using oracle service {scc.oracle_service} is NOT possible!")
        logger.critical(f"Database checks cannot be performed until the connection to tthe database is fixed!!")
    else:
        cursor = con.cursor()
        cursor.execute(sql_asm_diskgroup_check)
        for row in cursor.fetchall():
            dg_name, dg_state, dg_redundancy_type, dg_total_size_mb, dg_free_size_mb, dg_offline_disks = [*row]
            # dg_name, dg_state, dg_redundancy_type, dg_total_size_mb, dg_free_size_mb, dg_offline_disks = ['DATA', 'CONNECTED', 'EXTERN', 1023996, 50000, 0]
            if dg_state != 'CONNECTED':
                logger.critical(f"ASM disk group {dg_name} is not connected! Current disk group state is {dg_state}.")
            elif dg_offline_disks != 0:
                logger.warning(f"ASM disk group {dg_name} is {dg_state} but some disks are offline! Number of offline disks is {dg_offline_disks}.")
            else:
                logger.info(f"ASM disk group {dg_name} is {dg_state}, redundancy set to {dg_redundancy_type} and all disks are online.")
            
            asm_dg_free_percentage = (dg_free_size_mb * 100) / dg_total_size_mb  
            asm_dg_used_percentage = 100 - asm_dg_free_percentage

            if asm_dg_used_percentage >= scc.asm_dg_used_critical_threshold:
                logger.critical(f"Total size of ASM disk group {dg_name} is {round(dg_total_size_mb / 1024)} GB, used space is {round((dg_total_size_mb - dg_free_size_mb) / 1024)} GB. Less than {round(asm_dg_free_percentage)}% of space is available!")
            elif asm_dg_used_percentage >= scc.asm_dg_used_warning_threshold:
                logger.warning(f"Total size of ASM disk group {dg_name} is {round(dg_total_size_mb / 1024)} GB, used space is {round((dg_total_size_mb - dg_free_size_mb) / 1024)} GB. Less than {round(asm_dg_free_percentage)}% of space is available!")
            else:
                logger.info(f"Total size of ASM disk group {dg_name} is {round(dg_total_size_mb / 1024)} GB, used space is {round((dg_total_size_mb - dg_free_size_mb) / 1024)} GB. {round(asm_dg_free_percentage)}% of space is available.")
        
# ----------------------------------------------------------------------------
# Function to perform Oracle RAC checks
# ----------------------------------------------------------------------------

def rac_checks():
    # print specific section header
    check_section = "Oracle RAC checks"
    section_header = output_head(section=check_section, cmd=None)
    scc.print_to_log(section_header) if arg1 == 'FILE' else print(section_header)
    
    # check if scan listeners are started
    for command in rac_commands:
        cmd_output = sp.Popen(command, shell=True, stdout=sp.PIPE)
        for line in cmd_output.stdout.readlines():
            line = line.strip().decode(encoding)
            if 'is not running' in line:
                logger.critical(line)
            else:
                logger.info(line)
    # cmd_output = sp.Popen('ping -c 1 scc.scan_name', shell=True, stdout=sp.PIPE)
    cmd_output = sp.Popen('ping -c 4 localhost', shell=True, stdout=sp.PIPE)
    return_code = cmd_output.wait()
    if return_code != 0:
        logger.critical(f"Scan name {scc.scan_name} not answering to ping!")
    else:
        logger.info(f"Scan name {scc.scan_name} answering to ping.")
    
    # check if oracle service is responding on scan name
    try: 
        cx.connect(scc.scan_connect_string)
    except cx.DatabaseError:
        logger.critical(f"Connection on SCAN name {scc.scan_name} using oracle service {scc.oracle_service} is NOT possible!")
        logger.critical(f"Database checks cannot be performed until the connection to the database is fixed!!")
    else:
        logger.info(f"Connection on SCAN name {scc.scan_name} using oracle service {scc.oracle_service} is OK!")

# ----------------------------------------------------------------------------
# SQL statements for Oracle database and ASM check section
# ----------------------------------------------------------------------------

sql_tbs_usage = """
    SELECT
    dts.tablespace_name,
    dts.contents,
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
    AND NOT dts.contents like 'TEMPORARY'
    UNION ALL
    SELECT
    dts.tablespace_name,
    dts.contents,
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
    AND dts.contents like 'TEMPORARY'
    order by 1
"""

sql_tbs_autoextend = """
    select tablespace_name, autoextensible from dba_data_files
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

sql_asm_diskgroup_check = """
    select NAME, STATE, TYPE, TOTAL_MB, FREE_MB, OFFLINE_DISKS 
    from V$ASM_DISKGROUP_STAT
"""

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

# Setting local variables 
os_commands = ['sar 1 3', 'free -m', 'df -h']
fs_tocheck_list = ['/', '/mnt/webapp_1', '/run']
listener_commands = ['lsnrctl status',]
db_sqls = [sql_tbs_usage, sql_db_bkp_check, sql_arch_bkp_check]
rac_commands = ['cat scan_listener', 'cat scan_vip']

if __name__ == "__main__":
    if scc.os_checks:
        os_checks()
    if scc.db_checks:    
        listener_checks() 
        db_checks()
    if scc.rac_checks:
        asm_checks()
        rac_checks()