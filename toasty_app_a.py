#!/usr/bin/env python
#toasty_app_a.py
"""
Copyright (c) 2014 ContinuumBridge Limited

"""
ModuleName = "toasty_app" 

import sys
import os.path
import time
import logging
import json
from cbcommslib import CbApp
from cbconfig import *
from twisted.internet import reactor

CHECK_DELAY = 60   # How often to check the times and switch
ontimes = []
offtimes = []

class App(CbApp):
    def __init__(self, argv):
        logging.basicConfig(filename=CB_LOGFILE,level=CB_LOGGING_LEVEL,format='%(asctime)s %(message)s')
        self.appClass = "control"
        self.state = "stopped"
        self.gotSwitch = False
        self.switchState = "off" 
        self.sensorsID = [] 
        self.switchID = ""
        configFile = CB_CONFIG_DIR + "toasty.json"
        global ontimes, offtimes
        try:
            with open(configFile, 'r') as configFile:
                config = json.load(configFile)
                ontimes = config["ontimes"]
                logging.debug("%s ontimes: %s", ModuleName, ontimes)
                offtimes = config["offtimes"]
                logging.debug("%s offtimes: %s", ModuleName, offtimes)
                logging.info('%s Read toasty.json', ModuleName)
        except Exception as ex:
            logging.warning('%s toasty.json does not exist or file is corrupt', ModuleName)
            logging.warning("%s Exception: %s %s", ModuleName, type(ex), str(ex.args))
        # Super-class init must be called
        CbApp.__init__(self, argv)

    def setState(self, action):
        self.state = action
        msg = {"id": self.id,
               "status": "state",
               "state": self.state}
        self.sendManagerMessage(msg)

    def doTiming(self):
        if self.gotSwitch:
            now = time.strftime('%a %H:%M', time.localtime())
            if self.switchState == "off":
                for t in ontimes:
                    if t == now:
                        command = {"id": self.id,
                                   "request": "command",
                                   "data": "on"}
                        self.sendMessage(command, self.switchID)
                        logging.debug("%s doTimiing, command: %s, time: %s", ModuleName, command["data"], now)
                        self.switchState = "on"
            elif self.switchState == "on":
                for t in offtimes:
                    if t == now:
                        command = {"id": self.id,
                                   "request": "command",
                                   "data": "off"}
                        self.sendMessage(command, self.switchID)
                        logging.debug("%s doTimiing, command: %s, time: %s", ModuleName, command["data"], now)
                        self.switchState = "off"
        reactor.callLater(CHECK_DELAY, self.doTiming)

    def onAdaptorService(self, message):
        logging.debug("%s onadaptorService, message: %s", ModuleName, message)
        sensor = False
        switch = False
        buttons = False
        binary_sensor = False
        number_buttons = False
        for p in message["service"]:
            if p["characteristic"] == "buttons":
                buttons = True
            if p["characteristic"] == "number_buttons":
                number_buttons = True
            if p["characteristic"] == "switch":
                switch = True
            if p["characteristic"] == "binary_sensor":
                binary_sensor = True
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
        if number_buttons:
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
        if switch:
            self.switchID = message["id"]
            self.gotSwitch = True
            if binary_sensor:
                req = {"id": self.id,
                       "request": "service",
                       "service": [
                                     {"characteristic": "binary_sensor",
                                      "interval": 0
                                     }
                                  ]
                      }
                self.sendMessage(req, message["id"])
            #logging.debug("%s onadaptorservice, req: %s", ModuleName, req)
        self.setState("running")

    def onAdaptorData(self, message):
        #logging.debug("%s %s onAdaptorData. message: %s", ModuleName, self.id, str(message))
        if message["id"] in self.sensorsID:
            if self.gotSwitch:
                command = {"id": self.id,
                           "request": "command",
                           "data": ""
                          }
                if message["characteristic"] == "buttons":
                    if message["data"]["rightButton"] == 1:
                        command["data"] = "on"
                        self.sendMessage(command, self.switchID)
                    elif message["data"]["leftButton"] == 1:
                        command["data"] = "off"
                        self.sendMessage(command, self.switchID)
                elif message["characteristic"] == "number_buttons":
                    for m in message["data"].keys():
                        if m == "1":
                            command["data"] = "on"
                        self.sendMessage(command, self.switchID)
                    for m in message["data"].keys():
                        if m == "3":
                            command["data"] = "off"
                        self.sendMessage(command, self.switchID)
            else:
                logging.debug("%s Trying to turn on/off before switch connected", ModuleName)
        elif message["id"] == self.switchID:
            self.switchState = message["data"]

    def onConfigureMessage(self, config):
        #logging.debug("%s onConfigureMessage, config: %s", ModuleName, config)
        self.doTiming()
        self.setState("starting")

if __name__ == '__main__':
    App(sys.argv)
