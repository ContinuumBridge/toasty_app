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

times = [
         {
             ""
def nicetime(timeStamp):
    localtime = time.localtime(timeStamp)
    milliseconds = '%03d' % int((timeStamp - int(timeStamp)) * 1000)
    now = time.strftime('%Y-%m-%d %H:%M:%S', localtime)
    return now

def epochtime(date_time):
    pattern = '%Y-%m-%d %H:%M:%S'
    epoch = int(time.mktime(time.strptime(date_time, pattern)))
    return epoch

def calcnext():


class App(CbApp):
    def __init__(self, argv):
        logging.basicConfig(filename=CB_LOGFILE,level=CB_LOGGING_LEVEL,format='%(asctime)s %(message)s')
        self.appClass = "control"
        self.state = "stopped"
        self.gotSwitch = False
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
        self.setState("starting")

if __name__ == '__main__':
    App(sys.argv)
