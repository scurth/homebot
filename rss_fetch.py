#!/usr/bin/python3
"""RSS Feed fetcher"""

import configparser
import feedparser
import pymysql
from myCommon import myCommon
from datetime import datetime, timedelta
from dateutil.parser import parse

def main():
    configfile = "homebot.ini"
    config = configparser.ConfigParser()
    try:
        myCommon.debug_log("using config file: " + configfile)
        config.read(configfile)
    except:
        raise

    rssfeeds = config.get("RSS", "feeds").replace(' ', '').split(',')

    connection = pymysql.connect(host=config.get("MYSQL","host"),
                             user=config.get("MYSQL","user"),
                             password=config.get("MYSQL","password"),
                             database=config.get("MYSQL","database"),
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)
    for feed in rssfeeds:
        NewsFeed = feedparser.parse(feed)
        feedname = NewsFeed['feed']['title']
        for entry in NewsFeed.entries:
            rawdate = entry.published
            dt = parse(rawdate).replace(tzinfo=None)

            cursor = connection.cursor()
            sql = 'insert ignore into `feeds` (`FEED_NAME`,`FEED_TITLE`,`FEED_LINK`,`FEED_PUBLISHED`) VALUES ("%s", "%s", "%s", "%s")' % (feedname, entry.title,entry.link ,dt)
            try:
                cursor.execute(sql)
                myCommon.debug_log(sql)
            except Exception as e:
                print(str(e))
            connection.commit()

if __name__ == "__main__":
    main()
