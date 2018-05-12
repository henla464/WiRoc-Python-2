__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from databaselib.db import DB
from databaselib.datamapping import DataMapping
from settings.settings import SettingsClass
from datamodel.datamodel import SettingData
from battery import Battery
from init import *
from flask import request
import jsonpickle
import json
import time
import socket

@app.route('/misc/status/', methods=['GET'])
def getStatus():
    DatabaseHelper.reInit()
    subscribersView = DatabaseHelper.get_subscribers()
    subAdpts = []
    for sub in subscribersView:
        subscriberAdapter = {}
        subscriberAdapter['TypeName'] = sub.TypeName
        subscriberAdapter['InstanceName'] = sub.InstanceName
        subscriberAdapter['Enabled'] = sub.Enabled and sub.TransformEnabled
        subscriberAdapter['MessageInName'] = sub.MessageInName
        subscriberAdapter['MessageOutName'] = sub.MessageOutName
        subAdpts.append(subscriberAdapter)

    inputAdaptersInstances = DatabaseHelper.get_input_adapter_instances()
    inputAdapters = []
    for sub in inputAdaptersInstances:
        inputAdapter = {}
        inputAdapter['TypeName'] = sub.TypeName
        inputAdapter['InstanceName'] = sub.InstanceName
        inputAdapters.append(inputAdapter)

    data = {}
    data['inputAdapters'] = inputAdapters
    data['subscriberAdapters'] = subAdpts
    json_data = json.dumps(data)
    return json_data

@app.route('/misc/settings/', methods=['GET'])
def getSettings():
    DatabaseHelper.reInit()
    settings = DatabaseHelper.get_settings()
    setts = []
    for setting in settings:
        sett = {}
        sett['Key'] = setting.Key
        sett['Value'] = setting.Value
        setts.append(sett)

    data = {}
    data['settings'] = setts
    json_data = json.dumps(data)
    return json_data

@app.route('/misc/setting/<path:keyandvalue>/', methods=['GET'])
def setSetting(keyandvalue):
    DatabaseHelper.reInit()
    settingData = None
    keyandvaluelist = keyandvalue.split(';')
    if len(keyandvaluelist) > 1:
        settingData = SettingData()
        settingData.Key = keyandvaluelist[0]
        settingData.Value = keyandvaluelist[1]
        settingData = DatabaseHelper.save_setting(settingData)

    if settingData is None:
        return ''

    settingData2 = SettingData()
    settingData2.Key = 'ConfigDirty'
    settingData2.Value = '1'
    settingData2 = DatabaseHelper.save_setting(settingData2)
    if settingData2 is None:
        return ''

    return settingData.Key + ';' + settingData.Value

@app.route('/misc/punches/', methods=['GET'])
def getPunches():
    DatabaseHelper.reInit()
    blenoPunches = DatabaseHelper.get_bleno_punches()
    punches = []
    for blenoPunch in blenoPunches:
        punch = {}
        punch['StationNumber'] = blenoPunch.StationNumber
        punch['SICardNumber'] = blenoPunch.SICardNumber
        timeInSeconds = blenoPunch.TwelveHourTimer
        if blenoPunch.TwentyFourHour == 1:
            timeInSeconds += 3600 * 12
        hours = timeInSeconds // 3600
        remainingSeconds = timeInSeconds % 3600
        minutes = remainingSeconds // 60
        seconds = remainingSeconds % 60
        punch['Time'] = str(hours) + ':' + str(minutes).zfill(2) +':' + str(seconds).zfill(2)
        punches.append(punch)

    data = {}
    data['punches'] = punches
    json_data = json.dumps(data)

    for blenoPunch in blenoPunches:
        DatabaseHelper.delete_bleno_punch_data(blenoPunch.id)

    return json_data


@app.route('/misc/wirocdevicename/', methods=['GET'])
def getWiRocDeviceName():
    DatabaseHelper.reInit()
    setting = DatabaseHelper.get_setting_by_key('WiRocDeviceName')
    deviceName = "WiRoc Device"
    if setting != None:
        deviceName = setting.Value
    return jsonpickle.encode(MicroMock(WiRocDeviceName=deviceName))

@app.route('/misc/database/<operation>/', methods=['GET'])
def deletePunches(operation):
    DatabaseHelper.reInit()
    if operation.lower() == "deletepunches":
        DatabaseHelper.delete_punches()
        return jsonpickle.encode(MicroMock(Status="OK"))
    elif operation.lower() == "dropalltables":
        DatabaseHelper.drop_all_tables()
        return jsonpickle.encode(MicroMock(Status="OK"))
    else:
        return jsonpickle.encode(MicroMock(Status="Operation not found"))

@app.route('/misc/testpunches/gettestpunches/<testBatchGuid>/<includeAll>/', methods=['GET'])
def getTestPunches(testBatchGuid, includeAll):
    DatabaseHelper.reInit()
    testPunches = None
    if includeAll == "true":
        testPunches = DatabaseHelper.get_test_punches(testBatchGuid)
    else:
        testPunches = DatabaseHelper.get_test_punches_not_fetched(testBatchGuid)
    punches = []
    for testPunch in testPunches:
        punch = {}
        punch['Id'] = testPunch.id
        punch['MsgId'] = testPunch.MessageBoxId
        punch['Status'] = testPunch.Status
        punch['SINo'] = testPunch.SICardNumber
        punch['NoOfSendTries'] = testPunch.NoOfSendTries
        punch['SubscrId'] = testPunch.SubscriptionId
        timeInSeconds = testPunch.TwelveHourTimer
        if testPunch.TwentyFourHour == 1:
            timeInSeconds += 3600 * 12
        hours = timeInSeconds // 3600
        remainingSeconds = timeInSeconds % 3600
        minutes = remainingSeconds // 60
        seconds = remainingSeconds % 60
        punch['Time'] = str(hours) + ':' + str(minutes).zfill(2) +':' + str(seconds).zfill(2)
        punches.append(punch)

    data = {}
    data['punches'] = punches
    json_data = json.dumps(data)
    return json_data

@app.route('/misc/testpunches/addtestpunch/<testBatchGuid>/<SINo>/', methods=['GET'])
def addTestPunch(testBatchGuid, SINo):
    DatabaseHelper.reInit()
    localtime = time.localtime(time.time())
    twelveHourTimer = 0
    twentyFourHour = 0
    if localtime.tm_hour >= 12:
        twelveHourTimer = (localtime.tm_hour-12) * 3600 + localtime.tm_min * 60 + localtime.tm_sec
        twentyFourHour = 1
    else:
        twelveHourTimer = localtime.tm_hour * 3600 + localtime.tm_min * 60 + localtime.tm_sec
    DatabaseHelper.delete_other_test_punches(testBatchGuid)
    DatabaseHelper.add_test_punch(testBatchGuid, SINo, twelveHourTimer, twentyFourHour)

    json_data = jsonpickle.encode(MicroMock(Status="OK"))
    return json_data

@app.route('/misc/ischarging/', methods=['GET'])
def getIsCharging():
    isCharging = Battery.IsCharging()
    return jsonpickle.encode(MicroMock(IsCharging=isCharging))

@app.route('/misc/apikey/', methods=['GET'])
def getApiKey():
    DatabaseHelper.reInit()
    apiKey = SettingsClass.GetAPIKey(False)
    return jsonpickle.encode(MicroMock(ApiKey=apiKey))

@app.route('/misc/webserverurl/', methods=['GET'])
def getWebServerUrl():
    DatabaseHelper.reInit()
    webServerUrl = SettingsClass.GetWebServerUrl(False)
    host = webServerUrl.replace('http://', '').replace('https://', '')
    addrs = socket.getaddrinfo(host, 80)
    ipv4_addrs = [addr[4][0] for addr in addrs if addr[0] == socket.AF_INET]
    webServerUrl = webServerUrl.replace(host, ipv4_addrs[0])
    return jsonpickle.encode(MicroMock(WebServerUrl=webServerUrl))

@app.route('/misc/webserverhost/', methods=['GET'])
def getWebServerHost():
    DatabaseHelper.reInit()
    webServerUrl = SettingsClass.GetWebServerUrl(False)
    webServerHost = webServerUrl.replace('http://', '').replace('https://', '')
    return jsonpickle.encode(MicroMock(WebServerHost=webServerHost))
