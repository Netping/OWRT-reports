#!/usr/bin/python3
import enum
import ubus
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
    name = ""
    description = ""
    active = False
    callbacks = None
    method = method_type.empty
    period = period_type.empty
    report_format = ""
    settings = {}

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
default_report = report()
max_reports = 20

def poll():
    mutex.acquire()

    if not reports:
        mutex.release()
        return

    for r in reports:
        if r.active:
            #TODO handle report

    mutex.release()

def applyconfig():
    global pollThread
    global ubusConnected

    mutex.acquire()

    try:
        if not ubusConnected:
            ubus.connect()

        confvalues = ubus.call("uci", "get", {"config": confName})
        for confdict in list(confvalues[0]['values'].values()):
            if confdict['.type'] == 'report' and confdict['.name'] == 'prototype':
                default_report.name = confdict['name']
                default_report.active = bool(int(confdict['state']))

                #TODO fill another parameters

            if confdict['.type'] == 'report' and confdict['.name'] != 'prototype':
                exist = False
                r = report()
                r.name = confdict['name']

                for element in reports:
                    if element.name == e.name:
                        journal.WriteLog(module_name, "Normal", "error", "Report with name " + e.name + " is exists!")
                        exist = True
                        break

                if r.name == '':
                    journal.WriteLog(module_name, "Normal", "error", "Name can't be empty")
                    continue

                if exist:
                    continue

                try:
                    r.active = bool(int(confdict['state']))
                except:
                    r.active = default_report.active

                #TODO fill another parameters

                if reports.length() == max_reports:
                    journal.WriteLog(module_name, "Normal", "error", "Max reports exceeded")
                    continue

                reports.append(r)

        if not ubusConnected:
            ubus.disconnect()

        if not pollThread:
            pollThread = Thread(target=poll, args=())
            pollThread.start()

    except Exception as ex:
        journal.WriteLog(module_name, "Normal", "error", "Can't connect to ubus " + str(ex))

    mutex.release()

if __name__ == "__main__":
    applyconfig()
