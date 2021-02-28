#!/usr/bin/python3
"""RSS Feed fetcher"""

import configparser
import feedparser
import pymysql
from myCommon import myCommon
from datetime import datetime, timedelta
from dateutil.parser import parse

class rssFetch:
    global connection
    configfile = "homebot.ini"
    config = configparser.ConfigParser()
    try:
        myCommon.debug_log("using config file: " + configfile)
        config.read(configfile)
    except:
        raise

    connection = pymysql.connect(host=config.get("MYSQL","host"),
                         user=config.get("MYSQL","user"),
                         password=config.get("MYSQL","password"),
                         database=config.get("MYSQL","database"),
                         charset='utf8mb4',
                         cursorclass=pymysql.cursors.DictCursor)

    def getFeeds():
        feedcursor = connection.cursor()
        sql = 'select distinct(FEED_NAME) from `feeds`'
        try:
            result = feedcursor.execute(sql)
        except Exception as e:
            print(str(e))
       
        result = feedcursor.fetchall() 
        feedcursor.close()
        return result

    def getFeedEntry(feedname):
        feedcursor = connection.cursor()
        sql = 'select FEED_TITLE, FEED_LINK, FEED_PUBLISHED, id  from `feeds` where FEED_NAME = "%s" and showed=0 order by RAND() limit 1' % (feedname)
        print(sql)
        try:
            result = feedcursor.execute(sql)
        except Exception as e:
            print(str(e))

        result = feedcursor.fetchall()
        feedcursor.close()
        return result
    
    def __init__():
        print("los gehts")
        global connection

        rssfeeds = config.get("RSS", "feeds").replace(' ', '').split(',')

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
    # execute only if run as a script
    rssFetch.__init__()
