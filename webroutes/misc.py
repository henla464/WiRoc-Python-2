__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass
from datamodel.datamodel import SettingData
from battery import Battery
from init import *
from flask import request
import jsonpickle
import json
import time
import socket
import yaml

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

    SettingsClass.SetSettingUpdatedByWebService()
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
    f = open("../settings.yaml", "r")
    settings = yaml.load(f, Loader=yaml.BaseLoader)
    f.close()
    return jsonpickle.encode(MicroMock(WiRocDeviceName=settings['WiRocDeviceName']))

@app.route('/misc/wirocdevicename/<deviceName>', methods=['GET'])
def setWiRocDeviceName(deviceName):
    f = open("../settings.yaml", "r")
    settings = yaml.load(f, Loader=yaml.BaseLoader)
    f.close()
    settings['WiRocDeviceName'] = deviceName
    f2 = open('../settings.yaml', 'w')
    yaml.dump(settings, f2)  # Write a YAML representation of data to 'settings.yaml'.
    SettingsClass.SetSettingUpdatedByWebService()
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
        punch['RSSI'] = testPunch.AckRSSIValue
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
    apiKey = SettingsClass.GetAPIKey()
    return jsonpickle.encode(MicroMock(ApiKey=apiKey))

@app.route('/misc/webserverurl/', methods=['GET'])
def getWebServerUrl():
    DatabaseHelper.reInit()
    webServerUrl = SettingsClass.GetWebServerUrl()
    host = webServerUrl.replace('http://', '').replace('https://', '')
    addrs = socket.getaddrinfo(host, 80)
    ipv4_addrs = [addr[4][0] for addr in addrs if addr[0] == socket.AF_INET]
    webServerUrl = webServerUrl.replace(host, ipv4_addrs[0])
    return jsonpickle.encode(MicroMock(WebServerUrl=webServerUrl))

@app.route('/misc/webserverhost/', methods=['GET'])
def getWebServerHost():
    DatabaseHelper.reInit()
    webServerUrl = SettingsClass.GetWebServerUrl()
    webServerHost = webServerUrl.replace('http://', '').replace('https://', '')
    return jsonpickle.encode(MicroMock(WebServerHost=webServerHost))


@app.route('/misc/force4800baudrate/', methods=['GET'])
def getForce4800BaudRate():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('Force4800BaudRate')
    force4800BaudRate = False
    if sett is not None:
        force4800BaudRate = (sett.Value == "1")
    return jsonpickle.encode(MicroMock(Force4800BaudRate=force4800BaudRate))

@app.route('/misc/force4800baudrate/<enabled>/', methods=['GET'])
def SetForce4800BaudRateEnabled(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('Force4800BaudRate')
    if sd is None:
        sd = SettingData()
        sd.Key = 'Force4800BaudRate'
    sd.Value = '1' if enabled.lower() == 'true' else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(Force4800BaudRate=sd.Value.lower()=='true'))


@app.route('/misc/onewayreceive/', methods=['GET'])
def getOneWayReceive():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('OneWayReceive')
    oneWayReceive = False
    if sett is not None:
        oneWayReceive = (sett.Value == "1")
    return jsonpickle.encode(MicroMock(OneWayReceive=oneWayReceive))

@app.route('/misc/onewayreceive/<enabled>/', methods=['GET'])
def SetOneWayReceiveEnabled(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('OneWayReceive')
    if sd is None:
        sd = SettingData()
        sd.Key = 'OneWayReceive'
    sd.Value = '1' if enabled.lower() == 'true' else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(OneWayReceive=sd.Value.lower()=='true'))

@app.route('/misc/logtoserver/', methods=['GET'])
def getLogToServer():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('LogToServer')
    logToServer = False
    if sett is not None:
        logToServer = (sett.Value == "1")
    return jsonpickle.encode(MicroMock(LogToServer=logToServer))

@app.route('/misc/logtoserver/<enabled>/', methods=['GET'])
def SetLogToServerEnabled(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('LogToServer')
    if sd is None:
        sd = SettingData()
        sd.Key = 'LogToServer'
    sd.Value = '1' if enabled.lower() == 'true' else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(LogToServer=sd.Value.lower()=='true'))


@app.route('/misc/loggingserverhost/', methods=['GET'])
def getLoggingServerHost():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('LoggingServerHost')
    loggingServerHost = ""
    if sett is not None:
        loggingServerHost = sett.Value
    return jsonpickle.encode(MicroMock(LoggingServerHost=loggingServerHost))

@app.route('/misc/loggingserverhost/<host>/', methods=['GET'])
def SetLoggingServerHost(host):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('LoggingServerHost')
    if sd is None:
        sd = SettingData()
        sd.Key = 'LoggingServerHost'
    sd.Value = host
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(LoggingServerHost=sd.Value))

@app.route('/misc/loggingserverport/', methods=['GET'])
def getLoggingServerPort():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('LoggingServerPort')
    loggingServerPort = ""
    if sett is not None:
        loggingServerPort = sett.Value
    return jsonpickle.encode(MicroMock(LoggingServerPort=loggingServerPort))

@app.route('/misc/loggingserverport/<port>/', methods=['GET'])
def SetLoggingServerPort(port):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('LoggingServerPort')
    if sd is None:
        sd = SettingData()
        sd.Key = 'LoggingServerPort'
    sd.Value = port
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(LoggingServerPort=sd.Value))

@app.route('/misc/wirocpythonversion/', methods=['GET'])
def GetWiRocPythonVersion():
    f = open("../../WiRocPythonVersion.txt", "r")
    wirocPythonVersion = f.read()
    f.close()
    return jsonpickle.encode(MicroMock(WiRocPythonVersion=wirocPythonVersion))

@app.route('/misc/wirocbleversion/', methods=['GET'])
def GetWiRocBLEVersion():
    f = open("../../wirocBLEVersion.txt", "r")
    wirocBLEVersion = f.read()
    f.close()
    return jsonpickle.encode(MicroMock(WirocBLEVersion=wirocBLEVersion))

@app.route('/misc/wirochwversion/', methods=['GET'])
def GetWiRocHWVersion():
    f = open("../../WirocHWVersion.txt", "r")
    wirocHWVersion = f.read()
    f.close()
    return jsonpickle.encode(MicroMock(WirocHWVersion=wirocHWVersion))

@app.route('/misc/allmainsettings/', methods=['GET'])
def getAllMainSettings():
    DatabaseHelper.reInit()
    isCharging = Battery.IsCharging()

    f = open("../settings.yaml", "r")
    settings = yaml.load(f, Loader=yaml.BaseLoader)
    f.close()
    deviceName = settings['WiRocDeviceName']


    setting = DatabaseHelper.get_setting_by_key('SendToMeosIPPort')
    sirapPort = ""
    if setting != None:
        sirapPort = setting.Value

    setting = DatabaseHelper.get_setting_by_key('SendToMeosIP')
    sirapIP = ""
    if setting != None:
        sirapIP = setting.Value

    setting = DatabaseHelper.get_setting_by_key('SendToMeosEnabled')
    sirapEnabled = '0'
    if setting != None:
        sirapEnabled = setting.Value

    setting = DatabaseHelper.get_setting_by_key('AcknowledgementRequested')
    acksRequested = '1'
    if setting != None:
        acksRequested = setting.Value

    setting = DatabaseHelper.get_setting_by_key('LoraRange')
    loraRange = 'L'
    if setting != None:
        loraRange = setting.Value

    loraModule = SettingsClass.GetLoraModule()

    dataRate = SettingsClass.GetDataRate(loraRange)

    setting = DatabaseHelper.get_setting_by_key('Channel')
    channel = 1
    if setting != None:
        channel = int(setting.Value)

    setting = DatabaseHelper.get_setting_by_key('LoraPower')
    loraPower = '7'
    if setting != None:
        loraPower = setting.Value

    f = open("../WiRocPythonVersion.txt", "r")
    wirocPythonVersion = f.read()
    wirocPythonVersion = wirocPythonVersion.replace("\n","")
    f.close()

    f = open("../WiRocBLEVersion.txt", "r")
    wirocBLEVersion = f.read()
    wirocBLEVersion = wirocBLEVersion.replace("\n", "")
    f.close()

    f = open("../WiRocHWVersion.txt", "r")
    wirocHWVersion = f.read()
    wirocHWVersion = wirocHWVersion.replace("\n", "")
    f.close()

    all = ('1' if isCharging else '0') + '¤' + deviceName + '¤' +  sirapPort + '¤' + sirapIP + '¤' + sirapEnabled + '¤' + \
          acksRequested + '¤' + str(dataRate) + '¤' + str(channel) + '¤' + '%batteryPercent%' + '¤' + \
          '%ipAddress%'+ '¤' + str(loraPower) + '¤' + loraModule + '¤' + loraRange + '¤' + wirocPythonVersion + '¤' + \
          wirocBLEVersion + '¤' + wirocHWVersion

    return jsonpickle.encode(MicroMock(All=all))
