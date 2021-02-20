#!/usr/bin/python3
"""Telegram Bot for Home automation tasks"""
import configparser
import re
import signal
import qrcode
import telepot
import telepot.api
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
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

    def on_chat_message(msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        debug_log(str(content_type)+ str(chat_type)+ str(chat_id))

        helptext = "Verfügbare Funktionen"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='WiFi Password', callback_data='wifipass')]
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

        bot.answerCallbackQuery(query_id, text="Fertig", show_alert=0)

    bot_chatId = config.get("BotSettings", "bot_chatId")
    bot_token = config.get("BotSettings", "bot_token")
    debug_log("bot_chatId: " + bot_chatId + " bot_token: " + bot_token)
    debug = config.get("BotSettings", "debug")
    debug_log("debug state:" + str(debug))
    psk_file = config.get("WifiSettings", "pskfile")
    ssid = config.get("WifiSettings", "ssid")

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
