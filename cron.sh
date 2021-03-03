#!/bin/bash
. $HOME/.profile
cd $HOME/sandbox/homebot
python3 my_rss.py 
python3 blog_rss_feed.py
