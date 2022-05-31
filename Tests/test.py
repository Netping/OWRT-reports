#!/usr/bin/python3
import ubus
import os
import time
import json

# config info
config = "reportsconf"
config_path = "/etc/config/"

# ubus methods info
test_ubus_objects = [
    {
        'uobj': 'owrt_reports',
        'umethods': [
            {
                'umethod': 'get_reports',
                'inparams': {
                    "ubus_rpc_session":"0101"
                },
                'outparams': {
                    'retcode': ["__contains__", [x for x in range(-1,1)]],
                    'reports': ["__eqjson__", []]
                }
            },
        ]
    },
]

try:
    ubus.connect()
except:
    print("Can't connect to ubus")


def test_conf_existance():
    ret = False

    try:
        ret = os.path.isfile(f"{config_path}{config}")
    except:
        assert ret

    assert ret


def test_conf_valid():
    ret = False

    try:
        confvalues = ubus.call("uci", "get", {"config": config})
        for confdict in list(confvalues[0]['values'].values()):
            # check globals
            if confdict['.type'] == 'globals' and confdict['.name'] == 'globals':
                assert confdict['method'] == ['email.Почта', 'snmptrap.Отправить snmp сообщение']
            # check prototype
            if confdict['.type'] == 'report' and confdict['.name'] == 'prototype':
                assert confdict['name'] == 'Default report'
                assert confdict['description'] == 'Description text here'
                assert confdict['state'] == '0'
                assert confdict['callbacks'] == '[ { "module" : "owrt_module", "method" : "owrt_method", "input_parameters" : { "parameter" : "value" }, "output_parameters" : { "parameter" : "" } } ]'
                assert confdict['method'] == 'empty'
                assert confdict['schedule'] == 'none'
                assert confdict['text'] == 'Default text'
    except:
        assert ret


def test_ubus_methods_existance():
    ret = False

    try:
        test_uobj_list = [x['uobj'] for x in test_ubus_objects]
        test_uobj_list.sort()
        uobj_list = []
        for l in list(ubus.objects().keys()):
            if l in test_uobj_list:
                uobj_list.append(l)
        uobj_list.sort()
        assert test_uobj_list == uobj_list
    except:
        assert ret


def test_ubus_api():
    ret = False

    try:
        test_uobjs = [x for x in test_ubus_objects]
        for uobj in test_uobjs:
            test_uobj_methods = [x for x in uobj['umethods']]
            for method in test_uobj_methods:
                print(method['umethod'])
                res = ubus.call(uobj['uobj'], method['umethod'], method['inparams'])
                assert type(method['outparams']) == type(res[0])
                if isinstance(method['outparams'], dict):
                    for key in method['outparams']:
                        assert key in res[0]
                        if key in res[0]:
                            # if we need to check "contains"
                            if method['outparams'][key][0] == '__contains__':
                                assert getattr(method['outparams'][key][1], method['outparams'][key][0])(res[0][key])
                            # if we need to compare types of result
                            elif method['outparams'][key][0] == '__eq__':
                                eq = getattr(method['outparams'][key][1], method['outparams'][key][0])(res[0][key])
                                assert not isinstance(eq, type(NotImplemented))
                            # if we need to check result by json and compare types
                            elif method['outparams'][key][0] == '__eqjson__':
                                try:
                                    jeq = json.loads(res[0][key])
                                except:
                                    assert False
                                eq = getattr(method['outparams'][key][1], '__eq__')(jeq)
                                assert not isinstance(eq, type(NotImplemented))
    except:
        assert ret
