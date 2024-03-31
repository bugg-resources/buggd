#
# Regular cron jobs for the buggd package.
#
0 4	* * *	root	[ -x /usr/bin/buggd_maintenance ] && /usr/bin/buggd_maintenance
