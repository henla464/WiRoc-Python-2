__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass
from datamodel.datamodel import SettingData
from battery import Battery
from init import *
from flask import request
import jsonpickle
import json
import yaml
import time
import socket
import subprocess
import re
import datetime
import os
from subprocess import Popen


@app.route('/api/openapicontent/', methods=['GET'])
def getOpenApiContent():
    f = open("webroutes/api.yaml", "r")
    swaggercontent = f.read()
    f.close()
    return swaggercontent


@app.route('/api/channel/', methods=['GET'])
def getChannel():
    DatabaseHelper.reInit()
    setting = DatabaseHelper.get_setting_by_key('Channel')
    channel = 1
    if setting != None:
        channel = int(setting.Value)
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=channel))

@app.route('/api/channel/<int:channel>/', methods=['GET'])
def setChannel(channel):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('Channel')
    if sd is None:
        sd = SettingData()
        sd.Key = 'Channel'
    sd.Value = channel
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=int(sd.Value)))

@app.route('/api/lorarange/', methods=['GET'])
def getLoraRange():
    DatabaseHelper.reInit()
    setting = DatabaseHelper.get_setting_by_key('LoraRange')
    loraRange = 'L'
    if setting != None:
        loraRange = setting.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=loraRange))

@app.route('/api/lorarange/<lorarange>/', methods=['GET'])
def setLoraRange(lorarange):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('LoraRange')
    if sd is None:
        sd = SettingData()
        sd.Key = 'LoraRange'
    sd.Value = lorarange
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))

@app.route('/api/acknowledgementrequested/', methods=['GET'])
def getAcknowledgementRequested():
    DatabaseHelper.reInit()
    setting = DatabaseHelper.get_setting_by_key('AcknowledgementRequested')
    acksRequested = '0'
    if setting != None:
        acksRequested = setting.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=acksRequested))

@app.route('/api/acknowledgementrequested/<ack>/', methods=['GET'])
def setAcknowledgementRequested(ack):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('AcknowledgementRequested')
    if sd is None:
        sd = SettingData()
        sd.Key = 'AcknowledgementRequested'
    sd.Value = '1' if (ack.lower() == 'true' or ack.lower() == '1') else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))

@app.route('/api/power/', methods=['GET'])
def getPower():
    DatabaseHelper.reInit()
    setting = DatabaseHelper.get_setting_by_key('LoraPower')
    power = 0x07
    if setting != None:
        power = int(setting.Value)
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=power))

@app.route('/api/power/<int:power>/', methods=['GET'])
def setPower(power):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('LoraPower')
    if sd is None:
        sd = SettingData()
        sd.Key = 'LoraPower'
    sd.Value = power
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=int(sd.Value)))

@app.route('/api/coderate/', methods=['GET'])
def getCodeRate():
    DatabaseHelper.reInit()
    setting = DatabaseHelper.get_setting_by_key('CodeRate')
    # 0x00->4/5, 0x01->4/6, 0x02->4/7, 0x03->4/8
    codeRate = 0x00
    if setting != None:
        codeRate = int(setting.Value)
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=codeRate))

@app.route('/api/coderate/<int:coderate>/', methods=['GET'])
def setCodeRate(coderate):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('CodeRate')
    if sd is None:
        sd = SettingData()
        sd.Key = 'CodeRate'
    sd.Value = coderate
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=int(sd.Value)))

@app.route('/api/rxgainenabled/', methods=['GET'])
def getRxGainEnabled():
    setting = DatabaseHelper.get_setting_by_key('RxGainEnabled')
    enabled = '0'
    if setting != None:
        enabled = setting.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=enabled))

@app.route('/api/rxgainenabled/<enabled>/', methods=['GET'])
def setRxGainEnabled(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('RxGainEnabled')
    if sd is None:
        sd = SettingData()
        sd.Key = 'RxGainEnabled'
    sd.Value = '1' if (enabled.lower() == 'true' or enabled.lower() == '1') else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))

@app.route('/api/sendtosirapenabled/', methods=['GET'])
def getSendToSirapEnabled():
    setting = DatabaseHelper.get_setting_by_key('SendToSirapEnabled')
    enabled = '0'
    if setting != None:
        enabled = setting.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=enabled))

@app.route('/api/sendtosirapenabled/<enabled>/', methods=['GET'])
def setSendToSirapEnabled(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('SendToSirapEnabled')
    if sd is None:
        sd = SettingData()
        sd.Key = 'SendToSirapEnabled'
    sd.Value = '1' if (enabled.lower() == 'true' or enabled.lower() == '1') else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))

@app.route('/api/sendtosirapip/', methods=['GET'])
def getSendToSirapIP():
    setting = DatabaseHelper.get_setting_by_key('SendToSirapIP')
    ip = ""
    if setting != None:
        ip = setting.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=ip))

@app.route('/api/sendtosirapip/<ip>/', methods=['GET'])
def setSendToSirapIP(ip):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('SendToSirapIP')
    if sd is None:
        sd = SettingData()
        sd.Key = 'SendToSirapIP'
    sd.Value = ip
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))

@app.route('/api/sendtosirapipport/', methods=['GET'])
def getSendToSirapIPPort():
    setting = DatabaseHelper.get_setting_by_key('SendToSirapIPPort')
    port = ""
    if setting != None:
        port = setting.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=port))

@app.route('/api/sendtosirapipport/<port>/', methods=['GET'])
def setSendToSirapIPPort(port):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('SendToSirapIPPort')
    if sd is None:
        sd = SettingData()
        sd.Key = 'SendToSirapIPPort'
    sd.Value = port
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))

@app.route('/api/status/', methods=['GET'])
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
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=json_data))

@app.route('/api/settings/', methods=['GET'])
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
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=json_data))

@app.route('/api/setting/<path:keyandvalue>/', methods=['GET'])
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
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=settingData.Key + ';' + settingData.Value))

@app.route('/api/wirocdevicename/', methods=['GET'])
def getWiRocDeviceName():
    f = open("../settings.yaml", "r")
    settings = yaml.load(f, Loader=yaml.BaseLoader)
    f.close()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=settings['WiRocDeviceName']))

@app.route('/api/wirocdevicename/<deviceName>/', methods=['GET'])
def setWiRocDeviceName(deviceName):
    f = open("../settings.yaml", "r")
    settings = yaml.load(f, Loader=yaml.BaseLoader)
    f.close()
    settings['WiRocDeviceName'] = deviceName
    f2 = open('../settings.yaml', 'w')
    yaml.dump(settings, f2)  # Write a YAML representation of data to 'settings.yaml'.
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=deviceName))


def getWiRocMode():
    DatabaseHelper.reInit()

    sett = DatabaseHelper.get_setting_by_key('SendSerialAdapterActive')
    sendSerialAdapterActive = (sett is not None and sett.Value == "1")

    sett = DatabaseHelper.get_setting_by_key('SendToSirapEnabled')
    sendToSirapEnabled = (sett is not None and sett.Value == "1")

    sett = DatabaseHelper.get_setting_by_key('ReceiveSIAdapterActive')
    receiveSIAdapterActive = (sett is not None and sett.Value == "1")

    if sendSerialAdapterActive:  # and output = SERIAL
        # connected to computer or other WiRoc
        wirocMode = "RECEIVER"
    elif sendToSirapEnabled:  # and output = SIRAP
        # configured to send to Sirap over network/wifi
        wirocMode = "RECEIVER"
    elif receiveSIAdapterActive:
        wirocMode = "SENDER"
    else:
        wirocMode = "REPEATER"
    return wirocMode

@app.route('/api/wirocmode/', methods=['GET'])
def getWiRocModeJson():
    wirocMode = getWiRocMode()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=wirocMode))

@app.route('/api/punches/', methods=['GET'])
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

    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=json_data))

@app.route('/api/deletepunches/', methods=['GET'])
def deletePunches():
    DatabaseHelper.reInit()
    DatabaseHelper.delete_punches()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value="OK"))

@app.route('/api/dropalltables/', methods=['GET'])
def dropAllTables():
    DatabaseHelper.reInit()
    DatabaseHelper.drop_all_tables()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value="OK"))

@app.route('/api/testpunches/gettestpunches/<testBatchGuid>/<includeAll>/', methods=['GET'])
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

@app.route('/api/testpunches/addtestpunch/<testBatchGuid>/<SINo>/', methods=['GET'])
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

    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    json_data = jsonpickle.encode(MicroMock(Value="OK"))
    return json_data

@app.route('/api/ischarging/', methods=['GET'])
def getIsCharging():
    isCharging = Battery.IsCharging()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=('1' if isCharging else '0')))

@app.route('/api/apikey/', methods=['GET'])
def getApiKey():
    DatabaseHelper.reInit()
    apiKey = SettingsClass.GetAPIKey()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=apiKey))

def getWebServerUrl():
    DatabaseHelper.reInit()
    webServerUrl = SettingsClass.GetWebServerUrl()
    host = webServerUrl.replace('http://', '').replace('https://', '')
    addrs = socket.getaddrinfo(host, 80)
    ipv4_addrs = [addr[4][0] for addr in addrs if addr[0] == socket.AF_INET]
    webServerUrl = webServerUrl.replace(host, ipv4_addrs[0])
    return webServerUrl

@app.route('/api/webserverurl/', methods=['GET'])
def getWebServerUrl2():
    webServerUrl = getWebServerUrl()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=webServerUrl))

def getWebServerHost():
    DatabaseHelper.reInit()
    webServerUrl = SettingsClass.GetWebServerUrl()
    webServerHost = webServerUrl.replace('http://', '').replace('https://', '')
    return webServerHost

@app.route('/api/webserverhost/', methods=['GET'])
def getWebServerHost2():
    webServerHost = getWebServerHost()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=webServerHost))

@app.route('/api/onewayreceive/', methods=['GET'])
def getOneWayReceive():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('OneWayReceive')
    oneWayReceive = '0'
    if sett is not None:
        oneWayReceive = sett.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=oneWayReceive))

@app.route('/api/onewayreceive/<enabled>/', methods=['GET'])
def SetOneWayReceive(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('OneWayReceive')
    if sd is None:
        sd = SettingData()
        sd.Key = 'OneWayReceive'
    sd.Value = '1' if (enabled.lower() == 'true' or enabled.lower() == '1') else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))

@app.route('/api/force4800baudrate/', methods=['GET'])
def getForce4800BaudRate():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('Force4800BaudRate')
    force4800BaudRate = '0'
    if sett is not None:
        force4800BaudRate = sett.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=force4800BaudRate))

@app.route('/api/force4800baudrate/<enabled>/', methods=['GET'])
def SetForce4800BaudRateEnabled(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('Force4800BaudRate')
    if sd is None:
        sd = SettingData()
        sd.Key = 'Force4800BaudRate'
    sd.Value = '1' if (enabled.lower() == 'true' or enabled.lower() == '1') else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))

@app.route('/api/sendtoblenoenabled/', methods=['GET'])
def getSendToBlenoEnabled():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('SendToBlenoEnabled')
    sendToBlenoEnabled = '0'
    if sett is not None:
        sendToBlenoEnabled = sett.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sendToBlenoEnabled))

@app.route('/api/sendtoblenoenabled/<enabled>/', methods=['GET'])
def setSendToBlenoEnabled(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('SendToBlenoEnabled')
    if sd is None:
        sd = SettingData()
        sd.Key = 'SendToBlenoEnabled'
    sd.Value = '1' if (enabled.lower() == 'true' or enabled.lower() == '1') else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))

@app.route('/api/logtoserver/', methods=['GET'])
def getLogToServer():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('LogToServer')
    logToServer = '0'
    if sett is not None:
        logToServer = sett.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=logToServer))

@app.route('/api/logtoserver/<enabled>/', methods=['GET'])
def SetLogToServerEnabled(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('LogToServer')
    if sd is None:
        sd = SettingData()
        sd.Key = 'LogToServer'
    sd.Value = '1' if (enabled.lower() == 'true' or enabled.lower() == '1') else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))


@app.route('/api/loggingserverhost/', methods=['GET'])
def getLoggingServerHost():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('LoggingServerHost')
    loggingServerHost = ""
    if sett is not None:
        loggingServerHost = sett.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=loggingServerHost))

@app.route('/api/loggingserverhost/<host>/', methods=['GET'])
def SetLoggingServerHost(host):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('LoggingServerHost')
    if sd is None:
        sd = SettingData()
        sd.Key = 'LoggingServerHost'
    sd.Value = host
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))

@app.route('/api/loggingserverport/', methods=['GET'])
def getLoggingServerPort():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('LoggingServerPort')
    loggingServerPort = ""
    if sett is not None:
        loggingServerPort = sett.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=loggingServerPort))

@app.route('/api/loggingserverport/<port>/', methods=['GET'])
def setLoggingServerPort(port):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('LoggingServerPort')
    if sd is None:
        sd = SettingData()
        sd.Key = 'LoggingServerPort'
    sd.Value = port
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))

@app.route('/api/wirocpythonversion/', methods=['GET'])
def getWiRocPythonVersion():
    f = open("../WiRocPythonVersion.txt", "r")
    wirocPythonVersion = f.read()
    wirocPythonVersion = wirocPythonVersion.strip()
    f.close()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=wirocPythonVersion))

@app.route('/api/wirocbleversion/', methods=['GET'])
def getWiRocBLEVersion():
    f = open("../WiRocBLEVersion.txt", "r")
    wirocBLEVersion = f.read()
    wirocBLEVersion = wirocBLEVersion.strip()
    f.close()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=wirocBLEVersion))

@app.route('/api/wirocbleapiversion/', methods=['GET'])
def getWiRocBLEAPIVersion():
    f = open("../WiRocBLEAPIVersion.txt", "r")
    wirocBLEVersion = f.read()
    wirocBLEVersion = wirocBLEVersion.strip()
    f.close()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=wirocBLEVersion))

@app.route('/api/wirochwversion/', methods=['GET'])
def getWiRocHWVersion():
    f = open("../WiRocHWVersion.txt", "r")
    wirocHWVersion = f.read()
    wirocHWVersion = wirocHWVersion.strip()
    f.close()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=wirocHWVersion))

def getRFComms():
    boundResult = subprocess.run(['rfcomm'], stdout=subprocess.PIPE, check=True)
    rfComms = boundResult.stdout.decode('utf-8').strip()
    if len(rfComms) == 0:
        return []
    rfCommsArray = rfComms.split('\n')
    rfCommsObjArray = [MicroMock(SerialPortName=rfComm.split(' ')[0][:-1],
                                 BTAddress=rfComm.split(' ')[1],
                                 Channel=rfComm.split(' ')[3],
                                 Status=rfComm.split(' ')[4]) for rfComm in rfCommsArray]
    return rfCommsObjArray

@app.route('/api/scanbtaddresses/', methods=['GET'])
def getBTAddresses():
    result = subprocess.run(['hcitool', 'scan'], stdout=subprocess.PIPE, check=True)
    btaddresses = result.stdout.decode('utf-8').strip()
    btAddressAndNameArray = btaddresses.split('\n')
    btAddressAndNameArray = btAddressAndNameArray[1:]
    btAddressAndNameArray = [btAddrAndName.strip('\t') for btAddrAndName in btAddressAndNameArray]
    btAddressesAndNameObjArray = [MicroMock(BTAddress=btAddrAndName.split('\t')[0],
                                            Name=btAddrAndName.split('\t')[1]) for btAddrAndName in btAddressAndNameArray]

    rfCommsObjArray = getRFComms()

    combinedList = []
    for btAddrObj in btAddressesAndNameObjArray:
        combinedObj = MicroMock(SerialPortName=None,
                                PortNumber=None,
                                BTAddress=btAddrObj.BTAddress,
                                Channel=None,
                                Status=None,
                                Name=btAddrObj.Name)
        combinedList.append(combinedObj)

    for rfCommObj in rfCommsObjArray:
        combinedObj = MicroMock(SerialPortName=rfCommObj.SerialPortName,
                                PortNumber=rfCommObj.SerialPortName.replace("rfcomm", ""),
                                BTAddress=rfCommObj.BTAddress,
                                Channel=rfCommObj.Channel,
                                Status=rfCommObj.Status,
                                Name="")
        combinedList.append(combinedObj)

    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=combinedList))

@app.route('/api/bindrfcomm/<btAddress>/', methods=['GET'])
def bindRFComm(btAddress):
    result = subprocess.run(['sdptool','browse', 'local'], stdout=subprocess.PIPE, check=True)
    sdpToolResult = result.stdout.decode('utf-8').strip()
    pattern = re.compile('.*Channel: (.*?)$.*', re.MULTILINE | re.DOTALL)
    match = pattern.match(sdpToolResult)
    if match != None:
        channel = match.group(1)
        rfCommsObjArray = getRFComms()
        matchingPortsByBTAddress = [rfCommObj for rfCommObj in rfCommsObjArray if rfCommObj.BTAddress == btAddress]
        if len(matchingPortsByBTAddress) == 0:
            # Not bound already
            portNumberToUse = None
            for portNumber in range(10):
                portName = 'rfcomm'+str(portNumber)
                matchingPorts = [rfCommObj for rfCommObj in rfCommsObjArray if rfCommObj.SerialPortName == portName]
                if len(matchingPorts)==0:
                    portNumberToUse = portNumber
                    break
            if portNumberToUse != None:
                # Bind the device to a serial port
                res = subprocess.run(['rfcomm', 'bind', str(portNumberToUse), btAddress, channel], stdout=subprocess.PIPE, check=True)

    rfCommsArray = getRFComms()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=rfCommsArray))

@app.route('/api/releaserfcomm/<portNumberUsed>/', methods=['GET'])
def releaseRFComm(portNumberUsed):
    # Bind the device to a serial port
    res = subprocess.run(['rfcomm', 'release', portNumberUsed], stdout=subprocess.PIPE, check=True)
    releaseStr = res.stdout.decode('utf-8').strip()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    rfCommsArray = getRFComms()
    return jsonpickle.encode(MicroMock(Value=rfCommsArray))

def getIP():
    result = subprocess.run(['hostname', '-I'], stdout=subprocess.PIPE, check=True)
    ip = result.stdout.decode('utf-8').strip()
    return ip

def zipLogArchive(zipFilePath):
    result = subprocess.run(['zip', zipFilePath, '/home/chip/WiRoc-Python-2/WiRoc.db', '/home/chip/WiRoc-Python-2/WiRoc.log*'], stdout=subprocess.PIPE)
    if result.returncode != 0:
        errStr = result.stderr.decode('utf-8')
        print('Helper.zipLogArchive: error: ' + errStr)
        raise Exception("Error: " + errStr)

    return 'OK'

@app.route('/api/ip/', methods=['GET'])
def getIP2():
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=getIP()))

@app.route('/api/renewip/<ifaceNetType>/', methods=['GET'])
def renewIP(ifaceNetType):
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    result = subprocess.run(['nmcli', '-m', 'multiline', '-f', 'device,type', 'device', 'status'], stdout=subprocess.PIPE, check=True)
    if result.returncode != 0:
        errStr = result.stderr.decode('utf-8')
        raise Exception("Error: " + errStr)
    devices = result.stdout.decode('utf-8').splitlines()[0, -1] # remove last empty element
    devices = [dev[40:] for dev in devices]
    ifaces = devices[::2]
    ifaceNetworkTypes = devices[1::2]
    for iface, ifaceNetworkType in zip(ifaces, ifaceNetworkTypes):
        if (ifaceNetType == ifaceNetworkType):
            result2 = subprocess.run(['dhclient', '-v', '-1', iface], stdout=subprocess.PIPE, check=True)
            if result2.returncode != 0:
                errStr = result2.stderr.decode('utf-8')
                raise Exception("Error: " + errStr)
            resultStr = result2.stdout.decode('utf-8')
            return jsonpickle.encode(MicroMock(Value='OK'))
    return jsonpickle.encode(MicroMock(Value='Error: No matching iface'))


@app.route('/api/services/', methods=['GET'])
def getServices():
    statusServices = []
    result = subprocess.run(['systemctl', 'is-active', 'WiRocPython.service'], stdout=subprocess.PIPE)
    statusServices.append({'Name': 'WiRocPython', 'Status': result.stdout.decode('utf-8').strip('\n')})
    result = subprocess.run(['systemctl', 'is-active', 'WiRocPythonWS.service'], stdout=subprocess.PIPE)
    statusServices.append({'Name': 'WiRocPythonWS', 'Status': result.stdout.decode('utf-8').strip('\n')})
    result = subprocess.run(['systemctl', 'is-active', 'blink.service'], stdout=subprocess.PIPE)
    statusServices.append({'Name': 'WiRocMonitor', 'Status': result.stdout.decode('utf-8').strip('\n')})
    jsonStr = json.dumps({'services': statusServices })
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=jsonStr))


def getBTAddress():
    result = subprocess.run(['hcitool', 'dev'], capture_output=True)
    if result.returncode != 0:
        errStr = result.stderr.decode('utf-8')
        raise Exception("Error: " + errStr)

    stdout = result.stdout.decode('utf-8').replace("Devices:", "")
    stdout = stdout.strip()
    btAddress = "NoBTAddress"
    stdoutWords = stdout.split("\t")
    if len(stdoutWords) > 1 and len(stdoutWords[1]) == 17:
        btAddress = stdoutWords[1]
    return btAddress

def uploadLogArchiveToServer(apiKey, filePath, serverUrl, serverHost):
    parameters = ['curl', '-X', 'POST', '-H', 'host:' + serverHost, '-H',
         'accept:application/json', '-H', 'Authorization:' + apiKey, '-F', 'newfile=@' + filePath, serverUrl + '/api/v1/LogArchives']
    print(parameters)
    result = subprocess.run(parameters, capture_output=True)
    if result.returncode != 0:
        errStr = result.stderr.decode('utf-8')
        print('Helper.uploadLogArchive2: error: ' + errStr)
        raise Exception("Error: " + errStr)
    stdout = result.stdout.decode('utf-8')
    if len(stdout) > 0:
        print(stdout)
    return 'OK'

def getZipFilePath(btAddress, date):
    filePath = "/home/chip/LogArchive/LogArchive_" + btAddress + "_" + date.now().strftime("%Y-%m-%d-%H:%M:%S") + ".zip"
    return filePath

@app.route('/api/listwifi/', methods=['GET'])
def getListWifi():
    #Get new wifi list
    result = subprocess.run(['nmcli', '-m', 'multiline', '-f', 'ssid,active,signal', 'device', 'wifi', 'list'], stdout=subprocess.PIPE)
    if result.returncode != 0:
        errStr = result.stderr.decode('utf-8')
        raise Exception("Error: " + errStr)

    wifiNetworks = result.stdout.decode('utf-8').splitlines()[0:-1] # remove last empty element
    wifiNetworks2 = [netName[40:].strip() for netName in wifiNetworks]
    wifiDataList = '\n'.join(wifiNetworks2)
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=wifiDataList))

@app.route('/api/connectwifi/<wifiName>/<wifiPassword>/', methods=['GET'])
def connectWifi(wifiName, wifiPassword):
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    wlanIFace = 'wlan0'

    result = subprocess.run(['nmcli', 'device', 'wifi', 'connect', wifiName, 'password', wifiPassword, 'ifname', wlanIFace], stdout=subprocess.PIPE)
    if result.returncode != 0:
        errStr = result.stderr.decode('utf-8')
        return jsonpickle.encode(MicroMock(Value='Error: ' + errStr))

    return jsonpickle.encode(MicroMock(Value='OK'))

@app.route('/api/disconnectwifi/', methods=['GET'])
def disconnectWifi():
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    wlanIFace = 'wlan0'

    result = subprocess.run(['nmcli', 'device', 'disconnect', wlanIFace], stdout=subprocess.PIPE)
    if result.returncode != 0:
        errStr = result.stderr.decode('utf-8')
        return jsonpickle.encode(MicroMock(Value='Error: ' + errStr))

    return jsonpickle.encode(MicroMock(Value='OK'))

def getBatteryLevel():
    hostname = socket.gethostname()
    if hostname == "chip" or hostname == "nanopiair":
        print("chip or nanopi")
        result = subprocess.run(['/usr/sbin/i2cget', '-f', '-y', '0', '0x34', '0xb9'], stdout=subprocess.PIPE)
        if result.returncode != 0:
            print('return code not 0')
            errStr = result.stderr.decode('utf-8')
            return 'Error: ' + errStr

        intPercent = int(result.stdout.decode('utf-8').splitlines()[0], 0)
        print('Battery level - onReadRequest: value (dec)=' + str(intPercent))
        return str(intPercent)
    else:
        return '1'

@app.route('/api/batterylevel/', methods=['GET'])
def getBatteryLevel2():
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    batteryPercent = getBatteryLevel()
    return jsonpickle.encode(MicroMock(Value=batteryPercent))

@app.route('/api/uploadlogarchive/', methods=['GET'])
def uploadLogArchive():
    print('Helper.uploadLogArchive')
    btAddress = getBTAddress()
    dateNow = datetime.datetime.now()
    zipFilePath = getZipFilePath(btAddress, dateNow)

    zipLogArchive(zipFilePath)

    apiKey = SettingsClass.GetAPIKey()
    serverUrl = getWebServerUrl()
    serverHost = getWebServerHost()

    uploadLogArchiveToServer(apiKey, zipFilePath, serverUrl, serverHost)
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value='OK'))

@app.route('/api/startpatchap6212/', methods=['GET'])
def startPatchAP6212():
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    hostname = socket.gethostname()
    if hostname != "nanopiair":
        return jsonpickle.encode(MicroMock(Value='OK')) # only nanopiair needs patching

    result = subprocess.run(
        ['systemctl', 'start', 'ap6212-bluetooth'], stdout=subprocess.PIPE)
    if result.returncode != 0:
        errStr = result.stderr.decode('utf-8')
        print('Helper.startPatchAP6212: error: ' + errStr)

        result = subprocess.run(
            ['systemctl', 'start', 'ap6212-bluetooth'], stdout=subprocess.PIPE)
        if result.returncode != 0:
            errStr = result.stderr.decode('utf-8')
            print('Helper.startPatchAP6212: second try error: ' + errStr)
            return jsonpickle.encode(MicroMock(Value='Error: ' + errStr))

    stdout = result.stdout.decode('utf-8')
    if len(stdout) > 0:
        print(stdout)

    return jsonpickle.encode(MicroMock(Value='OK'))

@app.route('/api/upgradewirocble/<version>/', methods=['GET'])
def upgradeWiRocBLE(version):
    print("upgradeWiRocBLE")
    logfile = '../installWiRocBLE.log'
    with open(os.devnull, 'r+b') as DEVNULL:
        with open(logfile, 'a') as out:
            p = Popen(['./installWiRocBLEAPI.sh %s' % version], shell=True, stdin=DEVNULL, stdout=out, stderr=out, close_fds=True, cwd='..')

    return jsonpickle.encode(MicroMock(Value='OK'))

@app.route('/api/all/', methods=['GET'])
def getAllMainSettings():
    DatabaseHelper.reInit()
    isCharging = Battery.IsCharging()

    f = open("../settings.yaml", "r")
    settings = yaml.load(f, Loader=yaml.BaseLoader)
    f.close()
    deviceName = settings['WiRocDeviceName']


    setting = DatabaseHelper.get_setting_by_key('SendToSirapIPPort')
    sirapPort = ""
    if setting != None:
        sirapPort = setting.Value

    setting = DatabaseHelper.get_setting_by_key('SendToSirapIP')
    sirapIP = ""
    if setting != None:
        sirapIP = setting.Value

    setting = DatabaseHelper.get_setting_by_key('SendToSirapEnabled')
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
    if loraModule == 'RF1276T' and int(loraPower) > 7:
        loraPower = '7'

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

    sett = DatabaseHelper.get_setting_by_key('OneWayReceive')
    oneWayReceive = '0'
    if sett is not None:
        oneWayReceive = sett.Value

    sett = DatabaseHelper.get_setting_by_key('Force4800BaudRate')
    force4800BaudRate = '0'
    if sett is not None:
        force4800BaudRate = sett.Value

    wirocMode = getWiRocMode()

    sett = DatabaseHelper.get_setting_by_key('RxGainEnabled')
    rxGain ='1'
    if sett is not None:
        rxGain = sett.Value

    sett = DatabaseHelper.get_setting_by_key('CodeRate')
    codeRate = '0'
    if sett is not None:
        codeRate = sett.Value

    ipAddress = getIP()
    batteryPercent = getBatteryLevel()

    all = ('1' if isCharging else '0') + '¤' + deviceName + '¤' +  sirapPort + '¤' + sirapIP + '¤' + sirapEnabled + '¤' + \
        acksRequested + '¤' + str(dataRate) + '¤' + str(channel) + '¤' + batteryPercent + '¤' + \
        ipAddress + '¤' + str(loraPower) + '¤' + loraModule + '¤' + loraRange + '¤' + wirocPythonVersion + '¤' + \
        wirocBLEVersion + '¤' + wirocHWVersion + '¤' + oneWayReceive + '¤' + force4800BaudRate + '¤' + wirocMode + '¤' + \
        rxGain + '¤' + codeRate

    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=all))
