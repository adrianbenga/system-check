# system-check
# install cx_Oracle python module
<!-- user@webapp01$ python3 -m pip install cx_Oracle --upgrade
Defaulting to user installation because normal site-packages is not writeable
Collecting cx_Oracle
  Downloading cx_Oracle-8.3.0-cp310-cp310-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_12_x86_64.manylinux2010_x86_64.whl (892 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 892.6/892.6 KB 6.2 MB/s eta 0:00:00
Installing collected packages: cx_Oracle
Successfully installed cx_Oracle-8.3.0
user@webapp01$  -->
# install oracle client if needed
# source: https://help.ubuntu.com/community/Oracle%20Instant%20Client
<!-- alien -i oracle-instantclient12.1-basic-12.1.0.2.0-1.x86_64.rpm
alien -i oracle-instantclient12.1-sqlplus-12.1.0.2.0-1.x86_64.rpm
alien -i oracle-instantclient12.1-devel-12.1.0.2.0-1.x86_64.rpm -->

<!-- user@webapp01$ export ORACLE_HOME=/usr/lib/oracle/12.1/client64/
user@webapp01$ export LD_LIBRARY_PATH=/usr/lib/oracle/12.1/client64/lib/${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
user@webapp01$ export PATH=$PATH:$ORACLE_HOME/bin -->

