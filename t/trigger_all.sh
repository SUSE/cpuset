#!/bin/bash

PROG_PATH=$(dirname $0)/..
PYTHON_INTERPRETER=${PYTHON_INTERPRETER:-"python3"}

cd $PROG_PATH
ln -s . bin
$PYTHON_INTERPRETER bin/cset help # bin/ preix to trigget more code paths
$PYTHON_INTERPRETER cset version
$PYTHON_INTERPRETER cset -l /dev/shm/cset.log copyright
$PYTHON_INTERPRETER cset shield -c 2-3 -e /bin/true
$PYTHON_INTERPRETER cset shield /bin/true # and another way to exec a command behind the shield
$PYTHON_INTERPRETER cset shield -r
$PYTHON_INTERPRETER cset -m shield -s -c 3 -k off # -m for "machine readable output"
$PYTHON_INTERPRETER cset shield -s # surprisingly this is a way to print out user shield stats
$PYTHON_INTERPRETER cset shield -u # and system shield stats
$PYTHON_INTERPRETER cset shield -s -c 2-3 -k on # trigger shield modify operation
$PYTHON_INTERPRETER cset shield -s -p $$
$PYTHON_INTERPRETER cset shield -s -p $$ --force # just to trigger one more code path
$PYTHON_INTERPRETER cset shield -s $$
$PYTHON_INTERPRETER cset shield $$ # same as "-s -p <PID>
$PYTHON_INTERPRETER cset shield -v # trigger shield stats routines, -v for verbose
$PYTHON_INTERPRETER cset shield -v -v # -v -v for more verbosity
$PYTHON_INTERPRETER cset shield -u -p $$
$PYTHON_INTERPRETER cset shield -k on
$PYTHON_INTERPRETER cset shield -k off

#----------------- command set ---------------------
$PYTHON_INTERPRETER cset set
$PYTHON_INTERPRETER cset set -l -v
$PYTHON_INTERPRETER cset set -l -x root
$PYTHON_INTERPRETER cset -m set -l -r -s root
$PYTHON_INTERPRETER cset set -s user -n intermediate
$PYTHON_INTERPRETER cset set -n test intermediate
$PYTHON_INTERPRETER cset set -s test/one -c 2
$PYTHON_INTERPRETER cset set -s test/two -c 3
$PYTHON_INTERPRETER cset proc -m -s test/one -p $$ # move this process to test/two to trigger more code paths
$PYTHON_INTERPRETER cset set -s test/one -n root/to_delete # intentionally fail
$PYTHON_INTERPRETER cset set -s test/one -n to_delete
$PYTHON_INTERPRETER cset set -d test/to_delete
$PYTHON_INTERPRETER cset set -s test -d -r --force
$PYTHON_INTERPRETER cset set -s user -c 2-3
$PYTHON_INTERPRETER cset set -s user --mem_exclusive --cpu_exclusive

#----------------- command proc ---------------------
$PYTHON_INTERPRETER cset proc -l system
$PYTHON_INTERPRETER cset -m proc -l -s system
$PYTHON_INTERPRETER cset proc -e -s user -u lpechacek -g nobody -- /bin/true
$PYTHON_INTERPRETER cset proc -e -s user -u lpechacek -- /bin/true
# fifty shades of move operation
$PYTHON_INTERPRETER cset proc -m -s system -t user -p 1000-3000 --threads
$PYTHON_INTERPRETER cset proc -m -s user -p 1000-2000 --threads
$PYTHON_INTERPRETER cset proc -m -s user -t system --threads
$PYTHON_INTERPRETER cset proc -m -k -f 2-2000 user # -k for kernel threads, -f force
$PYTHON_INTERPRETER cset proc -m 1000-2000 user system
$PYTHON_INTERPRETER cset proc -m -p 1000-2000 system user
$PYTHON_INTERPRETER cset -m proc -v -m -p 1000-2000 system # -m for machine readable output, -v for verbose
$PYTHON_INTERPRETER cset proc -v -m -p $$ user # -v for verbose output
$PYTHON_INTERPRETER cset proc -m user system
$PYTHON_INTERPRETER cset proc -k -s root -t system

# the below tests assume empty user set
PYTHONPATH=. $PYTHON_INTERPRETER t/test_cset.py
PYTHONPATH=. $PYTHON_INTERPRETER t/test_util.py

# clean up
PYTHONPATH=. $PYTHON_INTERPRETER cset set -d -r --force user
PYTHONPATH=. $PYTHON_INTERPRETER cset set -d system
