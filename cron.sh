#!/bin/bash
cd /home/pi/sandbox/homebot
source .
env
date
python3 my_rss.py 
python3 blog_rss_feed.py
