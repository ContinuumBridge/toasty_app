#!/usr/bin/env python
#toasty_app.py
"""
Copyright (c) 2014 ContinuumBridge Limited

"""
ModuleName = "toasty_app" 

import sys
import os.path
import time
import logging
from cbcommslib import CbApp
from cbconfig import *
from twisted.internet import reactor

times = [
         {"on": ['23', '30', '00']},
         {"off" : ['01', '30', '00']}
        ]

def delay(n, tomorrow=False):
    now = time.time()
    if tomorrow:
        localtime = time.localtime(now + 24*60*60)
    else:
        localtime = time.localtime(now)
    t = time.strftime('%Y %m %d %H %M %S', localtime).split()
    t[3] = n[0]
    t[4] = n[1]
    t[5] = n[2]
    t1 = ' '.join(t)
    epoch = int(time.mktime(time.strptime(t1, '%Y %m %d %H %M %S')))
    return int(epoch - now)

class App(CbApp):
    def __init__(self, argv):
        logging.basicConfig(filename=CB_LOGFILE,level=CB_LOGGING_LEVEL,format='%(asctime)s %(message)s')
        self.appClass = "control"
        self.state = "stopped"
        self.gotSwitch = False
        self.step = "off" 
        self.sensorsID = [] 
        self.switchID = ""
        # Super-class init must be called
        CbApp.__init__(self, argv)

    def setState(self, action):
        self.state = action
        msg = {"id": self.id,
               "status": "state",
               "state": self.state}
        self.sendManagerMessage(msg)

    def startTiming(self):
        if self.step == "off":
            switchDel = delay(['23', '30', '00'])
        else:
            switchDel = delay(['01', '30', '00'], True)
        logging.debug("%s startTimiing, switchDel: %s, time: %s", ModuleName, str(switchDel), str(time.time()))
        reactor.callLater(switchDel, self.doTiming)

    def doTiming(self):
        command = {"id": self.id,
                   "request": "command"}
        if self.step == "off":
            command["data"] = "on"
            self.step = "on"
        else:
            command["data"] = "off"
            self.step = "off"
        self.sendMessage(command, self.switchID)
        logging.debug("%s doTimiing, command: %s, time: %s", ModuleName, command["data"], str(time.time()))
        self.startTiming()

    def onAdaptorService(self, message):
        logging.debug("%s onadaptorService, message: %s", ModuleName, message)
        sensor = False
        switch = False
        buttons = False
        number_buttons = False
        for p in message["service"]:
            if p["characteristic"] == "buttons":
                buttons = True
            elif p["characteristic"] == "number_buttons":
                number_buttons = True
            elif p["characteristic"] == "switch":
                switch = True
        if buttons:
            self.sensorsID.append(message["id"])
            req = {"id": self.id,
                  "request": "service",
                  "service": [
                                {"characteristic": "buttons",
                                 "interval": 0
                                }
                             ]
                  }
            self.sendMessage(req, message["id"])
            #logging.debug("%s onadaptorservice, req: %s", ModuleName, req)
        elif number_buttons:
            self.sensorsID.append(message["id"])
            req = {"id": self.id,
                  "request": "service",
                  "service": [
                                {"characteristic": "number_buttons",
                                 "interval": 0
                                }
                             ]
                  }
            self.sendMessage(req, message["id"])
        elif switch:
            self.switchID = message["id"]
            self.gotSwitch = True
            #logging.debug("%s switchID: %s", ModuleName, self.switchID)
        self.setState("running")

    def onAdaptorData(self, message):
        logging.debug("%s %s onAdaptorData. message: %s", ModuleName, self.id, str(message))
        if message["id"] in self.sensorsID:
            if self.gotSwitch:
                command = {"id": self.id,
                           "request": "command"}
                if message["characteristic"] == "buttons":
                    if message["data"]["rightButton"] == 1:
                        command["data"] = "on"
                        self.sendMessage(command, self.switchID)
                    elif message["data"]["leftButton"] == 1:
                        command["data"] = "off"
                        self.sendMessage(command, self.switchID)
                elif message["characteristic"] == "binary_sensor":
                    command["data"] = message["data"]
                    self.sendMessage(command, self.switchID)
                elif message["characteristic"] == "number_buttons":
                    if "on" in  message["data"].values():
                        command["data"] = "on"
                    else:
                        command["data"] = "off"
                    self.sendMessage(command, self.switchID)
            else:
                logging.debug("%s Trying to turn on/off before switch connected", ModuleName)
        elif message["id"] == self.switchID:
            self.switchState = message["body"]

    def onConfigureMessage(self, config):
        #logging.debug("%s onConfigureMessage, config: %s", ModuleName, config)
        self.startTiming()
        self.setState("starting")

if __name__ == '__main__':
    App(sys.argv)
