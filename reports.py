#!/usr/bin/python3
import enum
import ubus
from datetime import datetime
from threading import Thread
from threading import Lock
from journal import journal




    list method 'email.Почта'
    list method 'snmptrap.Отправить snmp сообщение'
    list period 'hourly.Каждый час'
    list period 'daily.Каждый день'
    list period 'weekly.Каждую неделю'
    list period 'monthly.Каждый месяц'

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

def applyconfig():
    #TODO
    pass

if __name__ == "__main__":
    applyconfig()
