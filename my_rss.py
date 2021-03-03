#!/usr/bin/python3
"""RSS Feed fetcher"""

import configparser
from dateutil.parser import parse
import pymysql
import feedparser
from myCommon import myCommon

CONFIG = configparser.ConfigParser()
CONFIGFILE = "homebot.ini"
try:
    myCommon.debug_log("using config file: " + CONFIGFILE)
    CONFIG.read(CONFIGFILE)
except:
    raise

CONNECTION = pymysql.connect(host=CONFIG.get("MYSQL", "host"),
                             user=CONFIG.get("MYSQL", "user"),
                             password=CONFIG.get("MYSQL", "password"),
                             database=CONFIG.get("MYSQL", "database"),
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

class RssFetch:
    def exec_sql(sql):
        global CONNECTION
        mycursor = CONNECTION.cursor()

        try:
            if CONNECTION.open is False:
                max_try = 15
                ntry = 0
                while CONNECTION.open is False:
                    if ntry < max_try:
                        CONNECTION.ping() # autoreconnect is true by default
                        ntry += 1
            if CONNECTION.open:
                mycursor.execute(sql)
            else:
                print("Upps...")
        except:
            print("CONNECTION error")
            RssFetch(sql)

        CONNECTION.commit()
        return mycursor

    def set_feed_entry_vote(feedid, feeback):
        sql = 'update feeds set liked = "%s" where id = %s' % (feeback, feedid)
        mycursor = RssFetch.exec_sql(sql)
        CONNECTION.commit()

        mycursor.close()

    def get_feeds():
        sql = 'select FEED_NAME, rssid from `rss`'
        mycursor = RssFetch.exec_sql(sql)
        result = mycursor.fetchall()
        mycursor.close()

        return result

    def get_feed_entry(feedid):
        sql = 'select FEED_TITLE, FEED_LINK, FEED_PUBLISHED, id from `feeds`'
        sql = sql + ' where rssid = "%s" and liked = "u" order by RAND() limit 1' % (feedid)
        mycursor = RssFetch.exec_sql(sql)
        result = mycursor.fetchall()
        mycursor.close()

        return result

    def __init__(self):
        rssfeeds = CONFIG.get("RSS", "feeds").replace(' ', '').split(',')

        for feed in rssfeeds:
            news_feed = feedparser.parse(feed)
            feedname = news_feed['feed']['title']
            sql = 'insert ignore into `rss` (`FEED_NAME`) VALUES ("%s") ' % (feedname)
            sql = sql + 'ON DUPLICATE KEY UPDATE rssid=LAST_INSERT_ID(`rssid`)'
            mycursor = RssFetch.exec_sql(sql)
            myCommon.debug_log(mycursor.lastrowid)
            feedid = mycursor.lastrowid

            for entry in news_feed.entries:
                rawdate = entry.published
                tzdt = parse(rawdate).replace(tzinfo=None)
                title = entry.title.replace('"', '')
                sql = 'insert ignore into feeds (`FEED_TITLE`,`FEED_LINK`,`FEED_PUBLISHED`,`rssid`,`description`)'
                sql = sql + ' VALUES ("%s", "%s", "%s", "%s", "%s")' % (title, entry.link, tzdt, feedid, entry.description.replace('"',''))
                mycursor = RssFetch.exec_sql(sql)

        mycursor.close()

if __name__ == "__main__":
    # execute only if run as a script
    RssFetch()