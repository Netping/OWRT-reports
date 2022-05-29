#!/usr/bin/python3
import enum
import ubus
import json
import time
import schedule
import re
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

mutex = Lock()
ubusConnected = False
default_report = None
max_reports = 20

class report:
    unusable_id_list = list(range(1, max_reports + 1))

    def __init__(self, name, description, active, callbacks, method, period, report_format, settings):
        self.__id = report.unusable_id_list.pop(0)
        self.__name = name
        self.__description = description
        self.__active = active
        self.__callbacks = callbacks
        self.__method = method
        self.__period = period
        self.__report_format = report_format
        self.__settings = settings

        def run():
            #ubus call for getting parameters
            callbacks = self.__callbacks
            messages = []
            for c in callbacks:
                result = ubus.call(c['module'], c['method'], c['input_parameters'])

                if not result:
                    journal.WriteLog(module_name, "Normal", "error", "Can't get ubus call for " + c['module'] + " with method " + c['method'])
                    continue

                m = { 
                        "name" : c['module'],
                        "method" : c['method'],
                        "result" : result
                    }
                messages.append(m)

            #generate text from report_format
            text = report_format
            result = re.findall(r'%_(\S+)_%', text)
            result = set(result)

            for r in result:
                splited = r.split('|')
                r_module = splited[0]
                r_method = splited[1]
                r_result = splited[2]

                for m in messages:
                    if m['name'] == r_module and m['method'] == r_method:
                        res = m['result'][0]
                        text = text.replace("%_" + r + "_%", res[r_result])
                        break

            if self.__method == method_type.email:
                for addr in self.__settings['toaddr']:
                    ubus.call("owrt_email", "send_mail", { "fromaddr":self.__settings['fromaddr'], "toaddr":addr, "text": text, "subject":self.__settings['subject'] ,"signature":self.__settings['signature'], "ubus_rpc_session":"" })

            elif self.__method == method_type.snmptrap:
                for addr in self.__settings['toaddr']:
                    os.system('snmptrap -c public -v 2c ' + addr + ':' + self.__settings['port'] + ' "" ' + self.__settings['oid'] + ' 1 s "' + text + '"')

        if self.__active:
            expr = "schedule.every()." + period + ".do(run)"
            journal.WriteLog(module_name, "Normal", "notice", expr)
            expr_res = eval(expr)

            if not expr_res:
                journal.WriteLog(module_name, "Normal", "error", "Wrong schedule expression")

    def get_id(self):
        return self.__id

    def get_name(self):
        return self.__name

    def __del__(self):
        if not report.unusable_id_list:
            report.unusable_id_list.append(self.__id)
            return

        for i in range(0, len(report.unusable_id_list)):
            if self.__id <= report.unusable_id_list[i]:
                report.unusable_id_list.insert(i, self.__id)
                break

module_name = "Reports"

reports = []
confName = 'reportsconf'

method_type_map = { 
                    'empty' : method_type.empty,
                    'email' : method_type.email,
                    'snmptrap' : method_type.snmptrap
                }

def ubus_init_callbacks():
    def get_reports_callback(event, data):
        ret_val = { 'retcode' : '-1' }

        mutex.acquire()

        ret_val['reports'] = []

        for r in reports:
            obj = { 'name' : r.get_name(),
                    'id' : r.get_id() }

            ret_val['reports'].append(obj)

        mutex.release()

        ret_val['reports'] = str(ret_val['reports'])
        ret_val['retcode'] = 0

        event.reply(ret_val)

    ubus.add(
            'owrt_reports', {
                'get_reports': {
                    'method': get_reports_callback,
                    'signature': {
                        'ubus_rpc_session': ubus.BLOBMSG_TYPE_STRING
                    }
                }
            }
        )

def reconfigure(event, data):
    if data['config'] == confName:
        journal.WriteLog(module_name, "Normal", "notice", "Config changed!")

        #applyconfig()
        current_reports = applyconfig()
        delete_ids = []

        for r in reports:
            found = False

            for c_r in current_reports:
                if r.get_name() == c_r.get_name():
                    found = True
                    break

            if not found:
                delete_ids.append(r.get_id())

        for r in reports:
            for d in delete_ids:
                if r.get_id() == d.get_id():
                    reports.remove(r)
                    break

def applyconfig():
    result = []
    global ubusConnected

    try:
        if not ubusConnected:
            ubus.connect()

        default_name = None
        default_active = None
        default_description = None
        default_callbacks = None
        default_method = None
        default_period = None
        default_report_format = None
        default_settings = None

        confvalues = ubus.call("uci", "get", {"config": confName})
        for confdict in list(confvalues[0]['values'].values()):
            if confdict['.type'] == 'report' and confdict['.name'] == 'prototype':
                default_name = confdict['name']
                default_active = bool(int(confdict['state']))
                default_description = confdict['description']
                default_callbacks = json.loads(confdict['callbacks'])
                default_method = method_type_map[confdict['method']]
                default_period = confdict['schedule']
                default_report_format = confdict['text']
                default_settings = {}

                #settings parse
                if default_method == method_type.empty:
                    pass

                elif default_method == method_type.email:
                    try:
                        default_settings['fromaddr'] = confdict['from']
                    except:
                        default_settings['fromaddr'] = ''

                    try:
                        default_settings['subject'] = confdict['subject']
                    except:
                        default_settings['subject'] = ''

                    try:
                        default_settings['signature'] = confdict['signature']
                    except:
                        default_settings['signature'] = ''

                    try:
                        default_settings['toaddr'] = [ a for a in confdict['sendto'].split(',')]
                    except:
                        default_settings['toaddr'] = []

                elif default_method == method_type.snmptrap:
                    try:
                        default_settings['toaddr'] = confdict['toaddr']
                    except:
                        default_settings['toaddr'] = ''

                    try:
                        default_settings['oid'] = confdict['oid']
                    except:
                        default_settings['oid'] = ''

                    try:
                        default_settings['port'] = confdict['port']
                    except:
                        default_settings['port'] = ''

                else:
                    journal.WriteLog(module_name, "Normal", "error", "Wrong method type. Settings is empty")

                #default_report = report(name, description, active, callbacks, method, period, report_format, settings)

            if confdict['.type'] == 'report' and confdict['.name'] != 'prototype':
                exist = False

                try:
                    name = confdict['name']
                except:
                    name = default_name

                try:
                    active = bool(int(confdict['state']))
                except:
                    active = default_active

                try:
                    description = confdict['description']
                except:
                    description = default_description

                try:
                    callbacks = json.loads(confdict['callbacks'])
                except:
                    callbacks = default_callbacks

                try:
                    method = method_type_map[confdict['method']]
                except:
                    method = default_method

                try:
                    period = confdict['schedule']
                except:
                    period = default_period

                try:
                    report_format = confdict['text']
                except:
                    report_format = default_report

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
                        settings['toaddr'] = confdict['toaddr']
                    except:
                        settings['toaddr'] = ''

                    try:
                        settings['oid'] = confdict['oid']
                    except:
                        settings['oid'] = ''

                    try:
                        settings['port'] = confdict['port']
                    except:
                        settings['port'] = ''
                else:
                    settings = default_settings
                    journal.WriteLog(module_name, "Normal", "error", "Wrong method type. Settings is default")

                r = report(name, description, active, callbacks, method, period, report_format, settings)

                if len(result) == max_reports:
                    journal.WriteLog(module_name, "Normal", "error", "Max reports exceeded")
                    continue

                result.append(r)

        if not ubusConnected:
            ubus.disconnect()

    except Exception as ex:
        journal.WriteLog(module_name, "Normal", "error", "Can't connect to ubus " + str(ex))

    return result

if __name__ == "__main__":
    journal.WriteLog(module_name, "Normal", "notice", "Module " + module_name + " started!")

    try:
        reports = applyconfig()

        ubus.connect()

        ubus_init_callbacks()

        while True:
            schedule.run_pending()
            ubus.listen(("commit", reconfigure))
            ubus.loop(1)

    except KeyboardInterrupt:
        del reports[:]

    ubus.disconnect()

    journal.WriteLog(module_name, "Normal", "notice", "Module " + module_name + " finished!")
