#!/usr/bin/python3
"""Telegram Bot for Home automation tasks"""
import configparser
import feedparser
import re
import time
import signal
import json
import collections
import qrcode
import telepot
import telepot.api
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
from datetime import datetime, timedelta
from dateutil.parser import parse
import paho.mqtt.client as mqtt

signal.signal(signal.SIGINT, signal.SIG_DFL)


def generateQR(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save("img1.png", "PNG")

    return "img1.png"

def main(argv=None):
    global debug
    dhcpQueue = collections.deque(maxlen=10)

    def debug_log(logmessage):
        global debug
        try:
            debug
        except NameError:
            print("Debug not set")
            debug = True

        if bool(debug) == True:
            print("DEBUG: " + str(logmessage))
        else:
            print("shall not log" + debug)
        return

    def mqtt_on_log(client, userdata, level, buf):
        debug_log("mqtt_log: ", buf)

    def mqtt_on_connect(client, userdata, flags, resultCode):
        debug_log("MQTT connect resultCode: " + str(resultCode))
        if resultCode == 0:
            client.connected_flag = True
            debug_log("MQTT connected OK Returned code:" + str(resultCode))
            for topic in mqttTopics:
                client.subscribe(topic + '/#')
        else:
            debug_log("Bad connection Returned code= ", resultCode)

    def mqtt_on_disconnect(client, userdata, resultCode):
        debug_log("disconnecting reason  "  +str(resultCode))
        client.connected_flag = False
        client.disconnect_flag = True

    def mqtt_on_message(client, userdata, msg):
        mqtt_msg_json_obj = json.loads(msg.payload)
        if msg.topic.startswith("dhcpd"):
            deviceName = msg.topic.split('/')[1]
            try:
                ipAddress = mqtt_msg_json_obj.get("ip-address")
                deviceName = mqtt_msg_json_obj.get("device-name")
                macAdress = mqtt_msg_json_obj.get("mac-adress")
                combinedValue = macAdress + " " + ipAddress + " " + deviceName
                dhcpQueue.append(combinedValue)
                debug_log(deviceName)
            except:
                raise
        elif msg.topic.startswith(gargentorCallback):
            toggleChannel = mqtt_msg_json_obj.get("channel")
            if int(toggleChannel) == int(gargentorChannel):
                mySendMessage("Gargentor geschaltet")
            debug_log(mqtt_msg_json_obj)
        else:
            debug_log("ignoring topic: ", msg.topic)

    def on_chat_message(msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        debug_log(str(content_type)+ str(chat_type)+ str(chat_id))

        helptext = "Verfügbare Funktionen"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='WiFi Password', callback_data='wifipass'),
             InlineKeyboardButton(text='DHCP History', callback_data='dhcphistory')],
            [InlineKeyboardButton(text='Garage', callback_data='garagedoor')],
            [InlineKeyboardButton(text='RSS Feeds', callback_data='rss')]
        ])

        if msg['text'].lower()[0] == "/":
            command = msg['text'].lower()[1:].split(" ", 1)[0]
            debug_log("found :" + command + ":")
            if content_type != 'text':
                bot.sendMessage(chat_id, helptext, reply_markup=keyboard)
                return
            elif command in ["help", "start"]:
                bot.sendMessage(chat_id, helptext, reply_markup=keyboard)
                return
            else:
                debug_log("DEBUG: " + command + str(type(command)))
        else:
            debug_log("Ignoriere Nachricht: " + msg['text'])

    configfile = "homebot.ini"
    config = configparser.ConfigParser()
    try:
        debug_log("using config file: " + configfile)
        config.read(configfile)
    except:
        raise

    def on_callback_query(msg):
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')

        if query_data == 'wifipass':
            qrwifi = "WIFI:T:WPA;S:"
            qrwifi = qrwifi + ssid + ";P:"

            for line in open(psk_file, 'r'):
                if re.search("00:00:00:00:00:00", line):
                    passwd = line.split(" ")[1].replace('\n', '').replace('\r', '')
                    qrwifi = qrwifi + passwd.replace('$', '\$').replace(';', '\;') + ";;"
            imgpath = generateQR(qrwifi)
            bot.sendPhoto(bot_chatId, photo=open(imgpath, 'rb'))
            bot.sendMessage(bot_chatId, passwd)
        elif query_data == 'dhcphistory':
            for item in dhcpQueue:
                mySendMessage(item)
        elif query_data == 'garagedoor':
            ret = client.publish(gargentorTopic, '{"channel":' + gargentorChannel + ', "value": true, "time": 1000}')
        elif query_data == 'rss':
            for feed in rssfeeds:
                feedname = "*" + feed.replace('https://','').split('/')[0] + "*"
                debug_log(feedname)
                mySendMessage(feedname, parse_mode='Markdown')
                NewsFeed = feedparser.parse(feed)
                past = datetime.now() - timedelta(days=1)
                past = past.replace(tzinfo=None)
                count = 0
                for entry in NewsFeed.entries:
                     rawdate = entry.published
                     dt = parse(rawdate).replace(tzinfo=None)
                     if dt > past:
                         mySendMessage( "[" + entry.title + "](" + entry.link + ")",parse_mode = "Markdown", disable_web_page_preview = True  )
                         count = count + 1
                     if count == 10:
                         break

        bot.answerCallbackQuery(query_id, text="Fertig", show_alert=0)

    def mySendMessage(msg, parse_mode = "HTML", disable_web_page_preview = False ):
        try:
            debug_log("bot_chatId: " + str(bot_chatId) + " message: " + str(msg))
            editable = bot.sendMessage(bot_chatId, str(msg), parse_mode = parse_mode, disable_web_page_preview = disable_web_page_preview)
            time.sleep(0.01)
            editable = telepot.message_identifier(editable)
            return editable
        except telepot.exception as error:
            debug_log(error)

    bot_chatId = config.get("BotSettings", "bot_chatId")
    bot_token = config.get("BotSettings", "bot_token")
    debug_log("bot_chatId: " + bot_chatId + " bot_token: " + bot_token)
    debug = config.get("BotSettings", "debug")
    debug_log("debug state:" + str(debug))
    psk_file = config.get("WifiSettings", "pskfile")
    ssid = config.get("WifiSettings", "ssid")

    mqttTopics = config.get("MqttSubscribe", "MqttTopics").replace(' ', '').split(',')
    rssfeeds = config.get("RSS", "feeds").replace(' ', '').split(',')

    gargentorTopic = config.get("Tinkerforge", "gargentorTopic")
    gargentorChannel = config.get("Tinkerforge", "gargentorChannel")
    garagenTorCallback = gargentorTopic.replace('request', 'callback')
    debug_log(garagenTorCallback)

    global client
    client = mqtt.Client("homebot")
    client.connected_flag = False
    client.on_log = mqtt_on_log
    client.on_connect = mqtt_on_connect
    client.on_disconnect = mqtt_on_disconnect
    client.on_message = mqtt_on_message

    try:
        client.connect('localhost', 1883, keepalive=500)
        debug_log("MQTT Connected: " + str(client.connected_flag))
    except:
        debug_log("mqtt_connect error")
        raise

    try:
        client.loop_start()
        debug_log("MQTT client.connected_flag:" + str(client.connected_flag))
        while not client.connected_flag:
            debug_log("Wait Loop, MQTT Connected: " + str(client.connected_flag))
            time.sleep(1)
    except:
        debug_log("MQTT client.connected_flag:" + str(client.connected_flag))
        debug_log("MQTT Client Loop Error")
        raise

    def always_use_new(req, **user_kw):
        return None

    try:
        telepot.api._which_pool = always_use_new
        bot = telepot.Bot(bot_token)
        MessageLoop(bot, {'chat': on_chat_message,
                          'callback_query': on_callback_query}).run_forever()
    except KeyboardInterrupt:
        pass
    except:
        debug_log("telepot intilialisation error")
        raise

if __name__ == "__main__":
    main()
