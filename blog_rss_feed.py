import datetime
import configparser
from feedgen.feed import FeedGenerator
from dateutil.parser import parse
import pytz
import boto3

import pymysql
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

    def get_feeds():
        sql = 'select id,FEED_TITLE, FEED_LINK, FEED_PUBLISHED, last_updated, description from feeds where liked = "y" and last_updated >= DATE_ADD(CURDATE(), INTERVAL -3 DAY)'
        mycursor = RssFetch.exec_sql(sql)
        result = mycursor.fetchall()
        return result

    def __init__(self):
        feeds = RssFetch.get_feeds()

        fg = FeedGenerator()
        fg.title("Sascha's Reader's Digest")
        fg.link( href='https://www.sascha-curth.de', rel='alternate' )
        fg.description('These news catched my attention.')
        for item in feeds:
            fe = fg.add_entry()
            fe.id(item['FEED_LINK'])
            fe.title(item['FEED_TITLE'])
            fe.link(href=item['FEED_LINK'], rel="alternate")
            fe.pubDate(pytz.utc.localize(item['FEED_PUBLISHED']))
            fe.description(str(item['description']))
 
#        result = fg.rss_str()
        fg.rss_file('static/readers_digest_rss.xml') 

        s3 = boto3.resource('s3')
#        s3.meta.client.upload_file('static/readers_digest_rss.xml', 'sascha-curth.de', 'verification/readers_digest_rss.xml')
        s3.meta.client.upload_file(CONFIG.get("AWS", "sourcefile"), CONFIG.get("AWS", "bucket"), CONFIG.get("AWS", "targetfile"))

if __name__ == "__main__":
    # execute only if run as a script
    RssFetch()
