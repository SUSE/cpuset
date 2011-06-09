#!/bin/sh
#
# Example system startup script for setting up presistent cpusets with the
# cset tool from package cpuset.  Copy this script to /etc/init.d/cset and
# uncomment out the commands in start() and stop() below, or add your own.
# Based on /etc/init.d/skeleton template.
#
#     Copyright (C) 2009 Novell, Inc.
#          
#     This library is free software; you can redistribute it and/or modify it
#     under the terms of the GNU Lesser General Public License as published by
#     the Free Software Foundation; either version 2.1 of the License, or (at
#     your option) any later version.
#			      
#     This library is distributed in the hope that it will be useful, but
#     WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#     Lesser General Public License for more details.
#      
#     You should have received a copy of the GNU Lesser General Public
#     License along with this library; if not, write to the Free Software
#     Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307,
#     USA.
#
#
# LSB compatible service control script; see http://www.linuxbase.org/spec/
# 
# Note: This template uses functions rc_XXX defined in /etc/rc.status on
# UnitedLinux/SUSE/Novell based Linux distributions. If you want to base your
# script on this template and ensure that it works on non UL based LSB 
# compliant Linux distributions, you either have to provide the rc.status
# functions from UL or change the script to work without them.
# See skeleton.compat for a template that works with other distros as well.
#
### BEGIN INIT INFO
# Provides:          cset
# Required-Start:    $local_fs $remote_fs
# Required-Stop:     $local_fs
# Default-Start:     2 3 5
# Default-Stop:      0 1 6
# Short-Description: Make cpuset setup persistent across boots
# Description:       Configure desired cpuset setup with the
#	cset tool for persistent cpusets across boots.
### END INIT INFO
# 

# Check for missing binaries (stale symlinks should not happen)
# Note: Special treatment of stop for LSB conformance
CSET_BIN=/usr/bin/cset
test -x $CSET_BIN || { echo "$CSET_BIN not installed"; 
	if [ "$1" = "stop" ]; then exit 0;
	else exit 5; fi; }

# cset variables (EDIT apropriately for your situation)
CSET_SYSTEM=0
CSET_USER=1-7

# Check for existence of cset config file and read it
# This is not used in this example, but you can create one for
# your setup if you wish.
#CSET_CONFIG=/etc/sysconfig/cset
#test -r $CSET_CONFIG || { echo "$CSET_CONFIG not existing";
#	if [ "$1" = "stop" ]; then exit 0;
#	else exit 6; fi; }

# Read config	
#. $CSET_CONFIG

# Source LSB init functions
. /etc/rc.status

# Reset status of this service
rc_reset

case "$1" in
    start)
	echo -n "Starting cpuset "

	# For a simple shield, we can use the shield subcommand as follows;
	# however, for any setup more comples it is not recommended to use
	# shield, but instead to use the set and proc subcommands.  The reason
	# is that the shield command has certain side effects which may complicate
	# the setup.  For example, shield marks the cpusets as exclusive.

	##
	#### Example 1: using the shield subcommand
	##
	
	#$CSET_BIN shield --cpu=1-3

	# Note that this creates CPU 0 as the general processor that runs
	# everything and all other CPUs (assuming this is a 4-CPU system) are assigned
	# to the shield.  This is a typical simple shielding setup.  Adjust if your
	# needs are different.

	# For shielding kernel threads as well, use the -k switch below instead
	# of the shield command above.
	#$CSET_BIN shield --cpu=1-3 -k

	##
	#### Example 2: using the set and proc subcommands
	##
	
	# To set up the exact same with the set and proc commands, use the
	# following commands.

	# Note that the CPUs are defined in the CSET_SYSTEM and
	# CSET_USER variables defined at the begining of this file.
	# Also you are not limited to call these cpusets "system" and
	# "user", you can call them anything, just be sure to be
	# consistent with the names in this script.

	#$CSET_BIN set --set=system --cpu=$CSET_SYSTEM
	#$CSET_BIN set --set=user --cpu=$CSET_USER

	# And to shield kernel threads, add the following command.
	
	#$CSET_BIN proc --move --kthread --fromset=root --toset=system

	# Remember status and be verbose
	rc_status -v
	;;
    stop)
	echo -n "Shutting down cpuset "

	##
	#### Example 1: using the shield command
	##
	
	# To turn the shield off, we use the reset switch to shield.  This
	# will move all tasks to the root cpuset and then remove both user
	# and system cpusets.

	#CSET_BIN shield --reset

	##
	#### Example 2: using the set and proc subcommands
	##

	# Note that we can simply remove the cpusets which will automatically
	# move the tasks in those cpusets to their parents; however, manually
	# moving tasks first gives more flexibility to more complex cpuset
	# configurations.

	#$CSET_BIN proc --move --kthread --force --fromset=system --toset=root
	#$CSET_BIN proc --move --kthread --force --fromset=user --toset=root

	# And now, destroy the cpusets
	
	#$CSET_BIN set --set=system --destroy
	#$CSET_BIN set --set=user --destroy

	# Remember status and be verbose
	rc_status -v
	;;
    status)
	echo -n "Checking for service cpuset "
	# This command simply shows which cpusets are set up and how many
	# tasks are running in them.
	$CSET_BIN set --recurse
	rc_status -v
	;;
    *)
	echo "Usage: $0 {start|stop|status}"
	exit 1
	;;
esac
rc_exit
