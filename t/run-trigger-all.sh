#!/bin/bash

PYTHONIOENCODING=utf-8 PYTHON_INTERPRETER=python2 bash -x t/trigger_all.sh 2>&1 | sed '/^[^+]/s/[[:digit:]]\+/NUMBER/g;/^+/{s/python[23]/PYTHON_INTERPRETER/;s/\(shield\|-p\|-s\) [[:digit:]]\+/\1 NUMBER/g}' > t/trigger_all-python2
PYTHONIOENCODING=utf-8 PYTHON_INTERPRETER=python3 bash -x t/trigger_all.sh 2>&1 | sed '/^[^+]/s/[[:digit:]]\+/NUMBER/g;/^+/{s/python[23]/PYTHON_INTERPRETER/;s/\(shield\|-p\|-s\) [[:digit:]]\+/\1 NUMBER/g}' > t/trigger_all-python3
