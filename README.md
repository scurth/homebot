# homebot
Home Automation Bot

# Install Requirements

```shell
pip3 install -r requirements.txt 
```

# Install Systemd Service

Make sure to adjust the path to the binary and the working directory as the homebot.ini is expected to be there.

```shell
cp homebot.service /etc/systemd/system/homebot.service
systemctl daemon-reload
systemctl enable homebot.service
systemctl start homebot.service
systemctl status homebot.service

● homebot.service - Homebot Telegram Service
   Loaded: loaded (/etc/systemd/system/homebot.service; enabled; vendor preset: enabled)
   Active: active (running) since Wed 2021-02-24 17:24:19 CET; 23h ago
 Main PID: 7547 (python3)
    Tasks: 4 (limit: 4915)
   CGroup: /system.slice/homebot.service
           └─7547 /usr/bin/python3 /home/pi/sandbox/homebot/homebot.py
```

