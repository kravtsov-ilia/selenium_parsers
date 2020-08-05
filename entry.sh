#!/bin/sh
python worker/run.py &
/usr/sbin/crond -f -l 8
