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
    global config

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

    def setFeedEntryVote(feedid,feeback):
        sql = 'update feeds set liked = "%s" where id = %s' % (feeback, feedid)
        updatecursor = connection.cursor()
        try:
            result = updatecursor.execute(sql)
            connection.commit()
        except Exception as e:
            print(str(e))
        updatecursor.close()

    def getFeeds():
        feedcursor = connection.cursor()
        sql = 'select FEED_NAME, rssid from `rss`'
        try:
            result = feedcursor.execute(sql)
        except Exception as e:
            print(str(e))
       
        result = feedcursor.fetchall() 
        feedcursor.close()
        return result

    def getFeedEntry(feedid):
        feedcursor = connection.cursor()
        sql = 'select FEED_TITLE, FEED_LINK, FEED_PUBLISHED, id  from `feeds` where rssid = "%s" and liked = "u" order by RAND() limit 1' % (feedid)
        try:
            result = feedcursor.execute(sql)
        except Exception as e:
            print(str(e))

        result = feedcursor.fetchall()
        feedcursor.close()
        return result
    
    def __init__():
        global connection
        global config

        rssfeeds = config.get("RSS", "feeds").replace(' ', '').split(',')

        for feed in rssfeeds:
            NewsFeed = feedparser.parse(feed)
            feedname = NewsFeed['feed']['title']
            sql = 'insert ignore into `rss` (`FEED_NAME`) VALUES ("%s") ON DUPLICATE KEY UPDATE rssid=LAST_INSERT_ID(`rssid`)' % (feedname)
            cursor = connection.cursor()
            try:
                res = cursor.execute(sql)
                myCommon.debug_log(cursor.lastrowid)
            except Exception as e:
                print(str(e))
            feedid = cursor.lastrowid
            connection.commit()


            for entry in NewsFeed.entries:
                rawdate = entry.published
                dt = parse(rawdate).replace(tzinfo=None)
                cursor = connection.cursor()
                title = entry.title.replace('"','')
                sql = 'insert ignore into `feeds` (`FEED_TITLE`,`FEED_LINK`,`FEED_PUBLISHED`,`rssid`) VALUES ("%s", "%s", "%s", "%s")' % (title,entry.link ,dt, feedid)
                try:
                    cursor.execute(sql)
                except Exception as e:
                    print(sql)
                    print(str(e))
                connection.commit()

if __name__ == "__main__":
    # execute only if run as a script
    rssFetch.__init__()
