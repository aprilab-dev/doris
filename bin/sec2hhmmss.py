#!/usr/bin/env python

import os
venv_path = os.getenv('DORIS_PYTHON2_VENV', None)
if venv_path:
    activate_venv_path = os.path.join(venv_path, 'bin/activate_this.py')
    with open(activate_venv_path) as f:
        exec(f.read(), {'__file__': activate_venv_path})

import os,sys,time

def usage():
    print '\nUsage: python sec2hhmmss.py time'
    print '  where time is the time of day in seconds.'
    print ' '
    print ' Example '
    print ' sec2hhmmss.py 59800.445398'
    print ' 16:36:40.393'

try:
    timeOfDay  = sys.argv[1] 
except:
    print 'Unrecognized input'
    usage()
    sys.exit(1)

timeOfDay  = float(sys.argv[1])

hh = timeOfDay//3600
timeOfDay = timeOfDay%3600
mm = timeOfDay//60
ss = timeOfDay%60
print "%d:%d:%f" %(hh,mm,ss)
