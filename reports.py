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
    #name = ""
    #description = ""
    #active = False
    #callbacks = None
    #method = method_type.empty
    #period = period_type.empty
    #report_format = ""
    #settings = {}

    def __run(self):
        journal.WriteLog(module_name, "Normal", "notice", "Report callbacks: " + str(self.__callbacks))

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

        if self.__active:
            expr = "schedule.every()." + period + ".do(run)"
            journal.WriteLog(module_name, "Normal", "notice", expr)
            expr_res = eval(expr)

            if not expr_res:
                journal.WriteLog(module_name, "Normal", "error", "Wrong schedule expression")
            #schedule.every().minute.do(self.__func)


module_name = "Reports"

reports = []
confName = 'reportsconf'

method_type_map = { 'email' : method_type.email,
                    'snmptrap' : method_type.snmptrap }

period_type_map = { 'hourly' : period_type.hourly,
                    'daily' : period_type.daily,
                    'weekly' : period_type.weekly,
                    'monthly' : period_type.monthly }

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
                #default_report.name = confdict['name']
                #default_report.active = bool(int(confdict['state']))
                #default_report.description = confdict['description']
                #default_report.callbacks = json.loads(confdict['callbacks'])
                #default_report.method = method_type_map[confdict['method']]
                #default_report.period = period_type_map[confdict['schedule']]
                #default_report.period = confdict['schedule']
                #default_report.report_format = confdict['text']

                name = confdict['name']
                active = bool(int(confdict['state']))
                description = confdict['description']
                callbacks = json.loads(confdict['callbacks'])
                method = method_type_map[confdict['method']]
                period = confdict['schedule']
                report_format = confdict['text']
                settings = {}

                #TODO settings parse

                #default_report = report(name, description, active, callbacks, method, period, report_format, settings)

            if confdict['.type'] == 'report' and confdict['.name'] != 'prototype':
                exist = False
                #r.name = confdict['name']

                #for element in reports:
                #    if element.name == e.name:
                #        journal.WriteLog(module_name, "Normal", "error", "Report with name " + e.name + " is exists!")
                #        exist = True
                #        break

                #if r.name == '':
                #    journal.WriteLog(module_name, "Normal", "error", "Name can't be empty")
                #    continue

                #if exist:
                #    continue
                name = confdict['name']
                active = bool(int(confdict['state']))
                description = confdict['description']
                callbacks = json.loads(confdict['callbacks'])
                method = method_type_map[confdict['method']]
                period = confdict['schedule']
                report_format = confdict['text']
                settings = {}

                #TODO settings parse

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
