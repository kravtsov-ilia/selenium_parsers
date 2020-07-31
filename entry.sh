#!/bin/sh
/usr/sbin/crond -f -l 8
python worker/run.py
