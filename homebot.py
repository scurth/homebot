#!/usr/bin/python3
"""Telegram Bot for Home automation tasks"""
import configparser
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
import paho.mqtt.client as mqtt
from myCommon import myCommon
import myRSS

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
    dhcpQueue = collections.deque(maxlen=10)

    def mqtt_on_log(client, userdata, level, buf):
        myCommon.debug_log("mqtt_log: ", buf)

    def mqtt_on_connect(client, userdata, flags, resultCode):
        myCommon.debug_log("MQTT connect resultCode: " + str(resultCode))
        if resultCode == 0:
            client.connected_flag = True
            myCommon.debug_log("MQTT connected OK Returned code:" + str(resultCode))
            for topic in mqttTopics:
                client.subscribe(topic + '/#')
        else:
            myCommon.debug_log("Bad connection Returned code= ", resultCode)

    def mqtt_on_disconnect(client, userdata, resultCode):
        myCommon.debug_log("disconnecting reason  "  +str(resultCode))
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
                if combinedValue not in dhcpQueue:
                    dhcpQueue.append(combinedValue)
                myCommon.debug_log(deviceName)
            except:
                raise
        elif msg.topic.startswith(gargentorCallback):
            toggleChannel = mqtt_msg_json_obj.get("channel")
            if int(toggleChannel) == int(gargentorChannel):
                mySendMessage("Gargentor geschaltet")
            myCommon.debug_log(mqtt_msg_json_obj)
        else:
            myCommon.debug_log("ignoring topic: ", msg.topic)

    def on_chat_message(msg):
        content_type, chat_type, chat_id, chat_date, chat_msg_id = telepot.glance(msg, long=True)
        myCommon.debug_log(str(content_type)+ str(chat_type)+ str(chat_id))

        helptext = "Verfügbare Funktionen"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='WiFi Password', callback_data='wifipass'),
             InlineKeyboardButton(text='DHCP History', callback_data='dhcphistory')],
            [InlineKeyboardButton(text='Garage', callback_data='garagedoor')],
            [InlineKeyboardButton(text='RSS Feeds', callback_data='rss')]
        ])

        if content_type == 'text' and msg['text'][0] == "/":
            command = msg['text'].lower()[1:].split(" ", 1)[0]
            myCommon.debug_log("found :" + command + ":")
            if content_type != 'text':
                bot.sendMessage(chat_id, helptext, reply_markup=keyboard)
                return
            elif command in ["help", "start"]:
                bot.sendMessage(chat_id, helptext, reply_markup=keyboard)
                return
            else:
                myCommon.debug_log("DEBUG: " + command + str(type(command)))
        elif msg['pinned_message']:
            myCommon.debug_log(chat_msg_id)
        else:
            myCommon.debug_log("Ignoriere Nachricht: " + msg['text'])

    configfile = "homebot.ini"
    config = configparser.ConfigParser()
    try:
        myCommon.debug_log("using config file: " + configfile)
        config.read(configfile)
    except:
        raise

    def on_callback_query(msg):
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
        if query_data.startswith("{"):
            query_data = json.loads(query_data)

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
            myCommon.debug_log("RSS FEEDS")
            markup = InlineKeyboardMarkup(inline_keyboard=[])
            feedkeyboard = []
            for feed in myRSS.rssFetch.getFeeds():
                feedkeyboard.append(InlineKeyboardButton(text=feed['FEED_NAME'], callback_data='{"feed": "' + str(feed['rssid']) + '"}'))
            markup = InlineKeyboardMarkup(inline_keyboard=[feedkeyboard])
            bot.sendMessage(bot_chatId, "Welchen Feed?", reply_markup=markup)

        elif query_data.get("feed"):
            feedid = query_data['feed']
            print(feedid)

            for feedentry in myRSS.rssFetch.getFeedEntry(feedid):
                feedlink = feedentry.get("FEED_LINK")
                feedtitle = feedentry.get("FEED_TITLE")
                itemid = str(feedentry.get("id"))

                markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='Nein', callback_data='{"feedid": "' + feedid + '","itemid": "' + itemid + '", "feeback": "n" }'),
                 InlineKeyboardButton(text='Ja', callback_data='{"feedid": "' + feedid + '","itemid": "' + itemid + '", "feeback": "y" }')],
                [InlineKeyboardButton(text='RSS Feed wechseln', callback_data='rss')]
                ])
                bot.sendMessage(bot_chatId, feedtitle + "\n" + feedlink, reply_markup=markup)

        elif query_data.get("feedid"):
            myRSS.rssFetch.setFeedEntryVote(query_data['itemid'], query_data['feeback'])
            print(query_data.get("feedid"))
            bot.answerCallbackQuery(query_id, text="Feedback gespeichert", show_alert=0)
            feedid = query_data['feedid']
            for feedentry in myRSS.rssFetch.getFeedEntry(feedid):
                feedlink = feedentry.get("FEED_LINK")
                feedtitle = feedentry.get("FEED_TITLE")
                itemid = str(feedentry.get("id"))

                markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='Nein', callback_data='{"feedid": "' + feedid + '","itemid": "' + itemid + '", "feeback": "n" }'),
                 InlineKeyboardButton(text='Ja', callback_data='{"feedid": "' + feedid + '","itemid": "' + itemid + '", "feeback": "y" }')],
                [InlineKeyboardButton(text='RSS Feed wechseln', callback_data='rss')]
                ])
                print(markup)
                bot.sendMessage(bot_chatId, feedtitle + "\n" + feedlink, reply_markup=markup)

        else:
            print("unklar")
            print(query_data.get("feed"))

        bot.answerCallbackQuery(query_id, text="Fertig", show_alert=0)

    def mySendMessage(msg, parse_mode="HTML", disable_web_page_preview=False):
        try:
            myCommon.debug_log("bot_chatId: " + str(bot_chatId) + " message: " + str(msg))
            editable = bot.sendMessage(bot_chatId, str(msg), parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
            time.sleep(0.01)
            editable = telepot.message_identifier(editable)
            return editable
        except telepot.exception as error:
            myCommon.debug_log(error)

    bot_chatId = config.get("BotSettings", "bot_chatId")
    bot_token = config.get("BotSettings", "bot_token")
    myCommon.debug_log("bot_chatId: " + bot_chatId + " bot_token: " + bot_token)
    psk_file = config.get("WifiSettings", "pskfile")
    ssid = config.get("WifiSettings", "ssid")

    mqttTopics = config.get("MqttSubscribe", "MqttTopics").replace(' ', '').split(',')

    gargentorTopic = config.get("Tinkerforge", "gargentorTopic")
    gargentorChannel = config.get("Tinkerforge", "gargentorChannel")
    garagenTorCallback = gargentorTopic.replace('request', 'callback')
    myCommon.debug_log(garagenTorCallback)

    global client
    client = mqtt.Client("homebot")
    client.connected_flag = False
    client.on_log = mqtt_on_log
    client.on_connect = mqtt_on_connect
    client.on_disconnect = mqtt_on_disconnect
    client.on_message = mqtt_on_message

    try:
        client.connect('localhost', 1883, keepalive=500)
        myCommon.debug_log("MQTT Connected: " + str(client.connected_flag))
    except:
        myCommon.debug_log("mqtt_connect error")
        raise

    try:
        client.loop_start()
        myCommon.debug_log("MQTT client.connected_flag:" + str(client.connected_flag))
        while not client.connected_flag:
            myCommon.debug_log("Wait Loop, MQTT Connected: " + str(client.connected_flag))
            time.sleep(1)
    except:
        myCommon.debug_log("MQTT client.connected_flag:" + str(client.connected_flag))
        myCommon.debug_log("MQTT Client Loop Error")
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
        myCommon.debug_log("telepot intilialisation error")
        raise

if __name__ == "__main__":
    main()
