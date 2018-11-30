from __future__ import print_function
from cpuset import util,config
import time

print("invocation with max set - progress bar should appear")
p = util.ProgressBar(15)
for n in range(18):
    time.sleep(0.07)
    p(n)

print("invocation without max set - nothing should appear")
p = util.ProgressBar(0)
for n in range(18):
    time.sleep(0.07)
    p(n)

print("invocation with max set and machine readable output set - nothing should appear")
config.mread=True
p = util.ProgressBar(15)
for n in range(18):
    time.sleep(0.07)
    p(n)

