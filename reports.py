#!/usr/bin/python3
import enum
import ubus
import json
import time
import schedule
from datetime import datetime
from threading import Thread
from threading import Lock
from journal import journal




class method_type(enum.Enum):
    empty = 0
    email = 1
    snmptrap = 2

class period_type(enum.Enum):
    empty = 0
    hourly = 1
    daily = 2
    weekly = 3
    monthly = 4

class report:
    #def __run(self):
    #    journal.WriteLog(module_name, "Normal", "notice", "Report callbacks: " + str(self.__callbacks))

        
    def __init__(self, name, description, active, callbacks, method, period, report_format, settings):
        self.__name = name
        self.__description = description
        self.__active = active
        self.__callbacks = callbacks
        self.__method = method
        self.__period = period
        self.__report_format = report_format
        self.__settings = settings

        def run():
            journal.WriteLog(module_name, "Normal", "notice", "Report callbacks: " + str(self.__callbacks))
            #TODO ubus call for getting parameters
            #TODO generate text from report_format
            text = report_format

            if self.__method == method_type.email:
            for addr in self.__settings['toaddr']:
                ubus.call("owrt_email", "send_mail", { "fromaddr":self.__settings['fromaddr'], "toaddr":addr, "text": text, "subject":self.__settings['subject'] ,"signature":self.__settings['signature'], "ubus_rpc_session":"1" })


        if self.__active:
            expr = "schedule.every()." + period + ".do(run)"
            journal.WriteLog(module_name, "Normal", "notice", expr)
            expr_res = eval(expr)

            if not expr_res:
                journal.WriteLog(module_name, "Normal", "error", "Wrong schedule expression")


module_name = "Reports"

reports = []
confName = 'reportsconf'

method_type_map = { 
                    'empty' : method_type.empty,
                    'email' : method_type.email,
                    'snmptrap' : method_type.snmptrap
                }

period_type_map = { 
                    'hourly' : period_type.hourly,
                    'daily' : period_type.daily,
                    'weekly' : period_type.weekly,
                    'monthly' : period_type.monthly 
                }

mutex = Lock()
pollThread = None
ubusConnected = False
poll_flag = True
default_report = None
max_reports = 20

def reconfigure(event, data):
    if data['config'] == confName:
        mutex.acquire()

        del reports[:]

        mutex.release()

        journal.WriteLog(module_name, "Normal", "notice", "Config changed!")

        applyconfig()

def poll():
    global poll_flag

    while poll_flag:
        journal.WriteLog(module_name, "Normal", "notice", "run_pending")
        schedule.run_pending()
        time.sleep(1)

def applyconfig():
    global pollThread
    global ubusConnected

    try:
        if not ubusConnected:
            ubus.connect()

        confvalues = ubus.call("uci", "get", {"config": confName})
        for confdict in list(confvalues[0]['values'].values()):
            if confdict['.type'] == 'report' and confdict['.name'] == 'prototype':
                name = confdict['name']
                active = bool(int(confdict['state']))
                description = confdict['description']
                callbacks = json.loads(confdict['callbacks'])
                method = method_type_map[confdict['method']]
                period = confdict['schedule']
                report_format = confdict['text']
                settings = {}

                #settings parse
                if method == method_type.empty:
                    pass
                elif method == method_type.email:
                    try:
                        settings['fromaddr'] = confdict['from']
                    except:
                        settings['fromaddr'] = ''

                    try:
                        settings['subject'] = confdict['subject']
                    except:
                        settings['subject'] = ''

                    try:
                        settings['signature'] = confdict['signature']
                    except:
                        settings['signature'] = ''

                    try:
                        settings['toaddr'] = [ a for a in confdict['sendto'].split(',')]
                    except:
                        settings['toaddr'] = []
                elif method == method_type.snmptrap:
                    try:
                        settings['url'] = confdict['url']
                    except:
                        settings['url'] = ''

                    try:
                        settings['oid'] = confdict['oid']
                    except:
                        settings['oid'] = ''

                    try:
                        settings['port'] = confdict['port']
                    except:
                        settings['port'] = ''
                else:
                    journal.WriteLog(module_name, "Normal", "error", "Wrong method type. Settings is empty")

                default_report = report(name, description, active, callbacks, method, period, report_format, settings)

            if confdict['.type'] == 'report' and confdict['.name'] != 'prototype':
                exist = False

                name = confdict['name']
                active = bool(int(confdict['state']))
                description = confdict['description']
                callbacks = json.loads(confdict['callbacks'])
                method = method_type_map[confdict['method']]
                period = confdict['schedule']
                report_format = confdict['text']
                settings = {}

                #settings parse
                if method == method_type.email:
                    try:
                        settings['fromaddr'] = confdict['from']
                    except:
                        settings['fromaddr'] = ''

                    try:
                        settings['subject'] = confdict['subject']
                    except:
                        settings['subject'] = ''

                    try:
                        settings['signature'] = confdict['signature']
                    except:
                        settings['signature'] = ''

                    try:
                        settings['toaddr'] = [ a for a in confdict['sendto'].split(',')]
                    except:
                        settings['toaddr'] = []
                elif method == method_type.snmptrap:
                    try:
                        settings['url'] = confdict['url']
                    except:
                        settings['url'] = ''

                    try:
                        settings['oid'] = confdict['oid']
                    except:
                        settings['oid'] = ''

                    try:
                        settings['port'] = confdict['port']
                    except:
                        settings['port'] = ''
                else:
                    journal.WriteLog(module_name, "Normal", "error", "Wrong method type. Settings is empty")

                r = report(name, description, active, callbacks, method, period, report_format, settings)
                
                mutex.acquire()

                if len(reports) == max_reports:
                    journal.WriteLog(module_name, "Normal", "error", "Max reports exceeded")
                    continue

                reports.append(r)

                mutex.release()

        if not ubusConnected:
            ubus.disconnect()

    except Exception as ex:
        journal.WriteLog(module_name, "Normal", "error", "Can't connect to ubus " + str(ex))

if __name__ == "__main__":
    try:
        applyconfig()

        if not pollThread:
            pollThread = Thread(target=poll, args=())
            pollThread.start()

        ubus.connect()

        ubus.listen(("commit", reconfigure))
        ubus.loop()

    except KeyboardInterrupt:
        del reports[:]
        poll_flag = False

    ubus.disconnect()
