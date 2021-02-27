import configparser

class myCommon:
    global debug
    configfile = "homebot.ini"
    config = configparser.ConfigParser()
    try:
        print("using config file: " + configfile, True)
        config.read(configfile)
    except:
        raise

    debug = config.get("BotSettings", "debug")
    debug = eval(debug)

    def debug_log(logmessage):
       if debug:
           print("DEBUG True: " + str(logmessage))
       else:
           print("DEBUG False: " + str(logmessage))
       return

