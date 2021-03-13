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
import my_rss

signal.signal(signal.SIGINT, signal.SIG_DFL)

def generate_qr(data):
    qr_obj = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr_obj.add_data(data)
    qr_obj.make(fit=True)

    img = qr_obj.make_image(fill_color="black", back_color="white")
    img.save("img1.png", "PNG")

    return "img1.png"

def main(argv=None):
    dhcp_queue = collections.deque(maxlen=10)
    global markise_position

    def mqtt_on_log(client, userdata, level, buf):
        myCommon.debug_log("mqtt_log: ", buf)

    def mqtt_on_connect(client, userdata, flags, resultCode):
        myCommon.debug_log("MQTT connect resultCode: " + str(resultCode))
        if resultCode == 0:
            client.connected_flag = True
            myCommon.debug_log("MQTT connected OK Returned code:" + str(resultCode))
            for topic in mqtt_topics:
                myCommon.debug_log("subscribe to topic:" + topic)
                client.subscribe(topic + '/#')
        else:
            myCommon.debug_log("Bad connection Returned code= ", resultCode)

        for topic in init_mqtt_topics:
            ret = client.publish(topic, "0")
            myCommon.debug_log(ret)

        client.publish("cmnd/tasmota-5FCFB2/Status", "1")

    def mqtt_on_disconnect(client, userdata, resultCode):
        myCommon.debug_log("disconnecting reason  "  +str(resultCode))
        client.connected_flag = False
        client.disconnect_flag = True

    def mqtt_on_message(client, userdata, msg):
        global markise_position
        mqtt_msg_json_obj = json.loads(msg.payload)
        myCommon.debug_log("new message for topic: " + msg.topic)
        myCommon.debug_log(mqtt_msg_json_obj)

        if msg.topic.startswith("stat/tasmota-5FCFB2/RESULT"):
            global lastMarkiseMsg
            markise_position = str(mqtt_msg_json_obj['Shutter1']['Position'])
            myCommon.debug_log("Pos: " + str(markise_position))
            try:
                lastMarkiseMsg
            except NameError:
                lastMarkiseMsg = (0, 0)
            else:
                myCommon.debug_log("lastMarkiseMsg is defined.")

            lastMarkiseMsg = my_send_message("Markise auf Position:" + str(markise_position), "HTML", False, lastMarkiseMsg)
            myCommon.debug_log(lastMarkiseMsg)
            # Stop button
            # am ende das keyboard mit den auswahl
            if mqtt_msg_json_obj['Shutter1']['Position'] == mqtt_msg_json_obj['Shutter1']['Target']:
                lastMarkiseMsg = (0, 0)
                print("Fertig")

        # SENSOR comes in every 10 secs or so
        elif msg.topic.startswith("tele/tasmota-5FCFB2/SENSOR"):
            markise_position = str(mqtt_msg_json_obj['Shutter1']['Position'])

        # this is actively triggers by cmd/+/status
        elif msg.topic.startswith("stat/tasmota-5FCFB2/STATUS10"):
            markise_position = str(mqtt_msg_json_obj['StatusSNS']['Shutter1']['Position'])

        elif msg.topic.startswith("dhcpd"):
            device_name = msg.topic.split('/')[1]
            try:
                ip_adress = mqtt_msg_json_obj.get("ip-address")
                device_name = mqtt_msg_json_obj.get("device-name")
                mac_adress = mqtt_msg_json_obj.get("mac-adress")
                combined_value = mac_adress + " " + ip_adress + " " + device_name
                if combined_value not in dhcp_queue:
                    dhcp_queue.append(combined_value)
                myCommon.debug_log(device_name)
            except:
                myCommon.debug_log("Error")
                raise
        elif msg.topic.startswith(gargentor_callback):
            toggle_channel = mqtt_msg_json_obj.get("channel")
            if int(toggle_channel) == int(gargentor_channel):
                my_send_message("Gargentor geschaltet")
            myCommon.debug_log(mqtt_msg_json_obj)
        else:
            myCommon.debug_log("ignoring topic: ", msg.topic)
        myCommon.debug_log("MQTT Message done")

    def is_json(myjson):
        try:
            json_object = json.loads(myjson)
        except ValueError as e:
            return False
        return True

    def build_inline_keyboard(keyboard, text, callback_data):
        if not isinstance(keyboard, list):
            myCommon.debug_log("keyboard is not a list, but " + str(type(keyboard)) + ". Resetting it to be an empty list")
            inline_keyboard = []
        else:
            inline_keyboard = keyboard

        if not is_json(callback_data):
            myCommon.debug_log("callback_data needs to be json")
            return inline_keyboard

        if not isinstance(text, str):
            myCommon.debug_log("button text need to be from type string")
            return inline_keyboard

        inline_keyboard.append(InlineKeyboardButton(text=text, callback_data=callback_data))

        return inline_keyboard

    def on_chat_message(msg):
        global markise_position
        content_type, chat_type, chat_id, chat_date, chat_msg_id = telepot.glance(msg, long=True)
        myCommon.debug_log(str(content_type)+ str(chat_type)+ str(chat_id))

        helptext = "Verfügbare Funktionen"
        try:
            markise_position
        except NameError:
            markise_position = -1

        markise_text = 'Markise (' + str(markise_position) + ')'

        new_keyboard_line1 = []
        new_keyboard_line1 = build_inline_keyboard(new_keyboard_line1, 'WiFi Password', '{"cb": "wifipass"}')
        new_keyboard_line1 = build_inline_keyboard(new_keyboard_line1, 'DHCP History', '{"cb": "dhcphistory"}')

        new_keyboard_line2 = []
        new_keyboard_line2 = build_inline_keyboard(new_keyboard_line2, 'Garage', '{"cb": "garagedoor"}')
        new_keyboard_line2 = build_inline_keyboard(new_keyboard_line2, markise_text, '{"cb": "markise"}')

        new_keyboard_line3 = []
        new_keyboard_line3 = build_inline_keyboard(new_keyboard_line3, 'RSS Feeds', '{"cb": "rss"}')

        keyboard = InlineKeyboardMarkup(inline_keyboard=[new_keyboard_line1, new_keyboard_line2, new_keyboard_line3])


        if content_type == 'text' and msg['text'][0] == "/":
            command = msg['text'].lower()[1:].split(" ", 1)[0]
            myCommon.debug_log("found :" + command + ":")
            if command in ["help", "start"]:
                entity = bot.getChat(chat_id)
                helptext = "Hallo %s, diese Funktionen sind verfügbar" % (entity['first_name'])
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
        if not is_json(query_data):
            myCommon.debug_log("query_data must be json")
            return
        else:
            query_data = json.loads(query_data)
            if  not query_data.get("cb"):
                myCommon.debug_log("query_data must be json and contain cb")
        global lastMarkiseMsg
        lastMarkiseMsg = (0, 0)
        if query_data.get("cb") == "wifipass":
            qrwifi = "WIFI:T:WPA;S:"
            qrwifi = qrwifi + ssid + ";P:"

            for line in open(psk_file, 'r'):
                if re.search("00:00:00:00:00:00", line):
                    passwd = line.split(" ")[1].replace('\n', '').replace('\r', '')
                    qrwifi = qrwifi + passwd.replace('$', '\$').replace(';', '\;') + ";;"
            imgpath = generate_qr(qrwifi)
            bot.sendPhoto(bot_chatId, photo=open(imgpath, 'rb'))
            bot.sendMessage(bot_chatId, passwd)

        elif query_data.get("cb") == "dhcphistory":
            for item in dhcp_queue:
                my_send_message(item)
        elif query_data.get("cb") == "garagedoor":
            ret = client.publish(gargentor_topic, '{"channel":' + gargentor_channel + ', "value": true, "time": 1000}')
        elif query_data.get("cb") == "markise":
            possible_positions = []
            for fixed_position in 0, 40, 80, 100:
                possible_positions.append(fixed_position)

            new_keyboard_line2 = []
            for adjustment in -10, 10:
                new_value = int(markise_position) + adjustment
                allowed_range = range(0, 100)
                if new_value in allowed_range:
                    new_keyboard_line2 = build_inline_keyboard(new_keyboard_line2, str(new_value), '{"cb":"shutterposition", "target": "' + str(new_value) + '"}')
                    if new_value in possible_positions:
                        possible_positions.remove(new_value)

            new_keyboard_line1 = []
            for possibleshutterposition in possible_positions:
                if possibleshutterposition != markise_position:
                    new_keyboard_line1 = build_inline_keyboard(new_keyboard_line1, str(possibleshutterposition), '{"cb":"shutterposition", "target": "' + str(possibleshutterposition) + '"}')

            markup = InlineKeyboardMarkup(inline_keyboard=[new_keyboard_line1, new_keyboard_line2])
            bot.sendMessage(bot_chatId, "Wie weit soll die Markise raus??", reply_markup=markup)

        elif query_data.get("cb") == "shutterposition":
            ret = client.publish(markise_topic, query_data.get("target"))
            bot.answerCallbackQuery(query_id, text="Markise ist unterwegs", show_alert=0)
        elif query_data.get("cb") == "rss":
            myCommon.debug_log("RSS FEEDS")
            markup = InlineKeyboardMarkup(inline_keyboard=[])
            feedkeyboard = []
            feednames = my_rss.RssFetch.get_feeds()
            if feednames:
                for feed in feednames:
                    buttontext = feed['FEED_NAME'] + " (" + str(feed['COUNT']) + ")"
                    feedkeyboard.append(InlineKeyboardButton(text=buttontext, callback_data='{"cb": "feedid", "fid": "' + str(feed['rssid']) + '"}'))
                markup = InlineKeyboardMarkup(inline_keyboard=[feedkeyboard])
                bot.sendMessage(bot_chatId, "Welchen Feed?", reply_markup=markup)
            else:
                bot.sendMessage(bot_chatId, "Keine neuen Nachrichten")

        elif query_data.get("cb") == "feedid":
            feedid = query_data['fid']
            if query_data.get('fb') and query_data.get('itemid'):
                my_rss.RssFetch.set_feed_entry_vote(query_data['itemid'], query_data['fb'])
                myCommon.debug_log(feedid)
                bot.answerCallbackQuery(query_id, text="Feedback gespeichert", show_alert=0)

            myCommon.debug_log("Requesting feeds from feedid: " + feedid)
            for feedentry in my_rss.RssFetch.get_feed_entry(feedid):
                feedlink = feedentry.get("FEED_LINK")
                feedtitle = feedentry.get("FEED_TITLE")
                itemid = str(feedentry.get("id"))

                callback_no = '{"cb": "feedid", "fid": "' + feedid + '", "itemid": "' + itemid + '", "fb": "n" }'
                callback_yes = '{"cb": "feedid", "fid": "' + feedid + '", "itemid": "' + itemid + '", "fb": "y" }'

                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='Nein', callback_data=callback_no),
                     InlineKeyboardButton(text='Ja', callback_data=callback_yes)],
                    [InlineKeyboardButton(text='RSS Feed wechseln', callback_data='{"cb": "rss"}')]
                    ])
                bot.sendMessage(bot_chatId, feedtitle + "\n" + feedlink, reply_markup=markup)
        else:
            print("unklar")
            print(query_data)

        bot.answerCallbackQuery(query_id, text="Fertig", show_alert=0)

    def my_send_message(msg, parse_mode="HTML", disable_web_page_preview=False, edit=(0, 0)):
        global editable
        try:
            myCommon.debug_log("bot_chatId: " + str(bot_chatId) + " message: " + str(msg))
            myCommon.debug_log("parse_mode: " + str(parse_mode) + " disable_web_page_preview: " + str(disable_web_page_preview))
            if edit != (0, 0):
                editable = bot.editMessageText(editable, str(msg))
            else:
                try:
                    editable = bot.sendMessage(bot_chatId, str(msg), parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
                except:
                    myCommon.debug_log("bot sendMessage error")

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

    mqtt_topics = config.get("MqttSubscribe", "MqttTopics").replace(' ', '').split(',')
    init_mqtt_topics = config.get("MqttSubscribe", "InitMqttSubscribe").replace(' ', '').split(',')

    gargentor_topic = config.get("Tinkerforge", "gargentorTopic")
    gargentor_channel = config.get("Tinkerforge", "gargentorChannel")
    gargentor_callback = gargentor_topic.replace('request', 'callback')

    markise_topic = config.get("Tinkerforge", "markiseTopic")

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
