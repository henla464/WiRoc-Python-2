__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass
from datamodel.datamodel import SettingData, BluetoothSerialPortData
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
from chipGPIO.hardwareAbstraction import HardwareAbstraction


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
    if setting is not None:
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
    if setting is not None:
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
    if setting is not None:
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
    if setting is not None:
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
    if setting is not None:
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
    if setting is not None:
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
    if setting is not None:
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
    if setting is not None:
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
    if setting is not None:
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
        subscriberAdapter = {'TypeName': sub.TypeName, 'InstanceName': sub.InstanceName,
                             'MessageInSubTypeName': sub.MessageInSubTypeName,
                             'Enabled': sub.Enabled and sub.TransformEnabled, 'MessageInName': sub.MessageInName,
                             'MessageOutName': sub.MessageOutName, 'MessageOutSubTypeName': sub.MessageOutSubTypeName}
        subAdpts.append(subscriberAdapter)

    inputAdaptersInstances = DatabaseHelper.get_input_adapter_instances()
    inputAdapters = []
    for sub in inputAdaptersInstances:
        inputAdapter = {'TypeName': sub.TypeName, 'InstanceName': sub.InstanceName}
        inputAdapters.append(inputAdapter)

    data = {'inputAdapters': inputAdapters, 'subscriberAdapters': subAdpts}
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
        sett = {'Key': setting.Key, 'Value': setting.Value}
        setts.append(sett)

    data = {'settings': setts}
    json_data = json.dumps(data)
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=json_data))

@app.route('/api/setting/<key>/<value>/', methods=['GET'])
def setSetting(key, value):
    DatabaseHelper.reInit()
    settingData = None
    settingData = SettingData()
    settingData.Key = key
    settingData.Value = value
    settingData = DatabaseHelper.save_setting(settingData)

    if settingData is None:
        return ''

    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=settingData.Key + '\t' + settingData.Value))

@app.route('/api/errorcodes/', methods=['GET'])
def getErrorCodes():
    DatabaseHelper.reInit()
    errorCodes = DatabaseHelper.get_error_codes()
    errCodes = []
    for errorCode in errorCodes:
        if errorCode.Message != "":
            errCode = {'Code': errorCode.Code, 'Message': errorCode.Message}
            errCodes.append(errCode)

    data = {'errorCodes': errCodes}
    json_data = json.dumps(data)
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=json_data))

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


@app.route('/api/loramode/', methods=['GET'])
def getLoraMode():
    loramode = "RECEIVER"
    setting = DatabaseHelper.get_setting_by_key('LoraMode')
    if setting is not None:
        loramode = setting.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=loramode))


@app.route('/api/loramode/<loramode>/', methods=['GET'])
def setLoraMode(loramode):
    if loramode == "RECEIVER" or loramode == "REPEATER" or loramode == "SENDER":
        DatabaseHelper.reInit()
        sd = DatabaseHelper.get_setting_by_key('LoraMode')
        if sd is None:
            sd = SettingData()
            sd.Key = 'LoraMode'
        sd.Value = loramode
        sd = DatabaseHelper.save_setting(sd)
        SettingsClass.SetSettingUpdatedByWebService()
        jsonpickle.set_preferred_backend('json')
        jsonpickle.set_encoder_options('json', ensure_ascii=False)
        return jsonpickle.encode(MicroMock(Value=sd.Value))
    else:
        raise Exception("Error: not a valid Lora/Radio Mode")


@app.route('/api/punches/', methods=['GET'])
def getPunches():
    DatabaseHelper.reInit()
    blenoPunches = DatabaseHelper.get_bleno_punches()
    punches = []
    for blenoPunch in blenoPunches:
        punch = {'StationNumber': blenoPunch.StationNumber, 'SICardNumber': blenoPunch.SICardNumber}
        timeInSeconds = blenoPunch.TwelveHourTimer
        if blenoPunch.TwentyFourHour == 1:
            timeInSeconds += 3600 * 12
        hours = timeInSeconds // 3600
        remainingSeconds = timeInSeconds % 3600
        minutes = remainingSeconds // 60
        seconds = remainingSeconds % 60
        punch['Time'] = str(hours) + ':' + str(minutes).zfill(2) + ':' + str(seconds).zfill(2)
        punches.append(punch)

    data = {'punches': punches}
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
        punch = {'Id': testPunch.id, 'MsgId': testPunch.MessageBoxId, 'Status': testPunch.Status,
                 'SINo': testPunch.SICardNumber, 'NoOfSendTries': testPunch.NoOfSendTries,
                 'SubscrId': testPunch.SubscriptionId, 'RSSI': testPunch.AckRSSIValue}
        timeInSeconds = testPunch.TwelveHourTimer
        if testPunch.TwentyFourHour == 1:
            timeInSeconds += 3600 * 12
        hours = timeInSeconds // 3600
        remainingSeconds = timeInSeconds % 3600
        minutes = remainingSeconds // 60
        seconds = remainingSeconds % 60
        punch['Time'] = str(hours) + ':' + str(minutes).zfill(2) + ':' + str(seconds).zfill(2)
        punches.append(punch)

    data = {'punches': punches}
    json_data = json.dumps(data)
    return json_data


@app.route('/api/testpunches/addtestpunch/<testBatchGuid>/<SINo>/', methods=['GET'])
def addTestPunch(testBatchGuid, SINo):
    DatabaseHelper.reInit()
    theTimeInSecondsFloat = time.time()
    localtime = time.localtime(theTimeInSecondsFloat)
    twelveHourTimer = 0
    twentyFourHour = 0
    subSecond = round((theTimeInSecondsFloat - int(theTimeInSecondsFloat)) * 255)
    if localtime.tm_hour >= 12:
        twelveHourTimer = (localtime.tm_hour-12) * 3600 + localtime.tm_min * 60 + localtime.tm_sec
        twentyFourHour = 1
    else:
        twelveHourTimer = localtime.tm_hour * 3600 + localtime.tm_min * 60 + localtime.tm_sec
    DatabaseHelper.delete_other_test_punches(testBatchGuid)
    DatabaseHelper.add_test_punch(testBatchGuid, SINo, twelveHourTimer, twentyFourHour, subSecond)

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


def getBatteryLevel():
    hostname = socket.gethostname()
    if hostname == "chip" or hostname == "nanopiair":
        #print("chip or nanopi")
        result = subprocess.run(['/usr/sbin/i2cget', '-f', '-y', '0', '0x34', '0xb9'], stdout=subprocess.PIPE)
        if result.returncode != 0:
            errStr = result.stderr.decode('utf-8')
            return 'Error: ' + errStr

        intPercent = int(result.stdout.decode('utf-8').splitlines()[0], 0)
        return str(intPercent)
    else:
        return '1'


@app.route('/api/batterylevel/', methods=['GET'])
def getBatteryLevel2():
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    batteryPercent = getBatteryLevel()
    return jsonpickle.encode(MicroMock(Value=batteryPercent))


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
def setOneWayReceive(enabled):
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


@app.route('/api/rs232mode/', methods=['GET'])
def getRS232Mode():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('RS232Mode')
    rs232Mode = "RECEIVE"
    if sett is not None:
        rs232Mode = sett.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=rs232Mode))


@app.route('/api/rs232mode/<mode>/', methods=['GET'])
def setRS232Mode(mode):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('RS232Mode')
    if sd is None:
        sd = SettingData()
        sd.Key = 'RS232Mode'
    sd.Value = 'SEND' if mode.lower() == 'send' else 'RECEIVE'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))


@app.route('/api/rs232onewayreceive/', methods=['GET'])
def getRS232OneWayReceive():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('RS232OneWayReceive')
    oneWayReceive = '0'
    if sett is not None:
        oneWayReceive = sett.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=oneWayReceive))


@app.route('/api/rs232onewayreceive/<enabled>/', methods=['GET'])
def setRS232OneWayReceive(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('RS232OneWayReceive')
    if sd is None:
        sd = SettingData()
        sd.Key = 'RS232OneWayReceive'
    sd.Value = '1' if (enabled.lower() == 'true' or enabled.lower() == '1') else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))


@app.route('/api/forcers2324800baudrate/', methods=['GET'])
def getForceRS2324800BaudRate():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('ForceRS2324800BaudRate')
    force4800BaudRate = '0'
    if sett is not None:
        force4800BaudRate = sett.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=force4800BaudRate))


@app.route('/api/forcers2324800baudrate/<enabled>/', methods=['GET'])
def setForceRS2324800BaudRateEnabled(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('ForceRS2324800BaudRate')
    if sd is None:
        sd = SettingData()
        sd.Key = 'ForceRS2324800BaudRate'
    sd.Value = '1' if (enabled.lower() == 'true' or enabled.lower() == '1') else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))


@app.route('/api/btserialonewayreceive/', methods=['GET'])
def getBTSerialOneWayReceive():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('BTSerialOneWayReceive')
    oneWayReceive = '0'
    if sett is not None:
        oneWayReceive = sett.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=oneWayReceive))


@app.route('/api/btserialonewayreceive/<enabled>/', methods=['GET'])
def setBTSerialOneWayReceive(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('BTSerialOneWayReceive')
    if sd is None:
        sd = SettingData()
        sd.Key = 'BTSerialOneWayReceive'
    sd.Value = '1' if (enabled.lower() == 'true' or enabled.lower() == '1') else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=sd.Value))


@app.route('/api/forcebtserial4800baudrate/', methods=['GET'])
def getForceBTSerial4800BaudRate():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('ForceBTSerial4800BaudRate')
    force4800BaudRate = '0'
    if sett is not None:
        force4800BaudRate = sett.Value
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=force4800BaudRate))


@app.route('/api/forcebtserial4800baudrate/<enabled>/', methods=['GET'])
def setForceBTSerial4800BaudRateEnabled(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('ForceBTSerial4800BaudRate')
    if sd is None:
        sd = SettingData()
        sd.Key = 'ForceBTSerial4800BaudRate'
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
def setLogToServerEnabled(enabled):
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
    with open("../settings.yaml", "r") as f:
        settings = yaml.load(f, Loader=yaml.BaseLoader)
    wirocPythonVersion = settings['WiRocPythonVersion']
    wirocPythonVersion = wirocPythonVersion.strip()

    #f = open("../WiRocPythonVersion.txt", "r")
    #wirocPythonVersion = f.read()
    #wirocPythonVersion = wirocPythonVersion.strip()
    f.close()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=wirocPythonVersion))


@app.route('/api/wirocbleversion/', methods=['GET'])
def getWiRocBLEVersion():
    with open("../settings.yaml", "r") as f:
        settings = yaml.load(f, Loader=yaml.BaseLoader)
    wirocBLEVersion = settings['WiRocBLEAPIVersion']
    wirocBLEVersion = wirocBLEVersion.strip()

    #f = open("../WiRocBLEVersion.txt", "r")
    #wirocBLEVersion = f.read()
    #wirocBLEVersion = wirocBLEVersion.strip()
    #f.close()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=wirocBLEVersion))


@app.route('/api/wirocbleapiversion/', methods=['GET'])
def getWiRocBLEAPIVersion():
    with open("../settings.yaml", "r") as f:
        settings = yaml.load(f, Loader=yaml.BaseLoader)
    wirocBLEAPIVersion = settings['WiRocBLEAPIVersion']
    wirocBLEAPIVersion = wirocBLEAPIVersion.strip()

    #f = open("../WiRocBLEAPIVersion.txt", "r")
    #wirocBLEVersion = f.read()
    #wirocBLEVersion = wirocBLEVersion.strip()
    #f.close()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=wirocBLEVersion))


@app.route('/api/wirochwversion/', methods=['GET'])
def getWiRocHWVersion():
    f = open("../settings.yaml", "r")
    settings = yaml.load(f, Loader=yaml.BaseLoader)
    f.close()
    wirocHWVersion = settings['WiRocHWVersion']

    #f = open("../WiRocHWVersion.txt", "r")
    #wirocHWVersion = f.read()
    #f.close()
    wirocHWVersion = wirocHWVersion.strip()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=wirocHWVersion))

@app.route('/api/scanbtaddresses/', methods=['GET'])
def getBTAddresses():
    result = subprocess.run(['hcitool', 'scan'], stdout=subprocess.PIPE, check=True)
    btaddresses = result.stdout.decode('utf-8').strip()
    btAddressAndNameArray = btaddresses.split('\n')
    btAddressAndNameArray = btAddressAndNameArray[1:]
    btAddressAndNameArray = [btAddrAndName.strip('\t') for btAddrAndName in btAddressAndNameArray]
    btAddressesAndNameObjArray = [MicroMock(BTAddress=btAddrAndName.split('\t')[0],
                                            Name=btAddrAndName.split('\t')[1],
                                            Found='True',
                                            Status='NotConnected')
                                  for btAddrAndName in btAddressAndNameArray]
    DatabaseHelper.reInit()
    btSerialPortDatas = DatabaseHelper.get_bluetooth_serial_ports()
    for btSerialPortData in btSerialPortDatas:
        found = False
        for btAddressAndName in btAddressesAndNameObjArray:
            if btAddressAndName.BTAddress == btSerialPortData.DeviceBTAddress:
                btAddressAndName.Status = btSerialPortData.Status
                found = True
        if not found:
            btAddressesAndNameObjArray.append(MicroMock(BTAddress=btSerialPortData.DeviceBTAddress,
                                                        Name=btSerialPortData.Name,
                                                        Found='False',
                                                        Status=btSerialPortData.Status))

    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=btAddressesAndNameObjArray))


@app.route('/api/bindrfcomm/<btAddress>/<btName>/', methods=['GET'])
def bindRFComm(btAddress, btName):
    btSerialPortDatas = DatabaseHelper.get_bluetooth_serial_port(btAddress)
    if len(btSerialPortDatas) == 0:
        btSerialPortData = BluetoothSerialPortData()
        btSerialPortData.DeviceBTAddress = btAddress
        btSerialPortData.Name = btName
        btSerialPortData.Status = 'NotConnected'
        DatabaseHelper.save_bluetooth_serial_port(btSerialPortData)
    btAddresses = getBTAddresses()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=btAddresses))


@app.route('/api/releaserfcomm/<btAddress>/', methods=['GET'])
def releaseRFComm(btAddress):
    DatabaseHelper.delete_bluetooth_serial_port(btAddress)
    btAddresses = getBTAddresses()
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=btAddresses))


def getIP():
    result = subprocess.run(['hostname', '-I'], stdout=subprocess.PIPE, check=True)
    ip = result.stdout.decode('utf-8').strip()
    return ip


def zipLogArchive(zipFilePath):
    result = subprocess.run(['zip', zipFilePath, '/home/chip/WiRoc-Python-2/WiRoc.db', '/home/chip/WiRoc-Python-2/WiRoc.db-shm', '/home/chip/WiRoc-Python-2/WiRoc.db-wal', '/home/chip/WiRoc-Python-2/WiRoc.log', '/home/chip/WiRoc-Python-2/WiRoc.log.1', '/home/chip/WiRoc-Python-2/WiRoc.log.2', '/home/chip/WiRoc-Python-2/WiRoc.log.3'], stdout=subprocess.PIPE)
    if result.returncode != 0:
        errStr = result.stderr.decode('utf-8')
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
    devices = result.stdout.decode('utf-8').splitlines()[0, -1]  # remove last empty element
    devices = [dev[40:] for dev in devices]
    ifaces = devices[::2]
    ifaceNetworkTypes = devices[1::2]
    for iface, ifaceNetworkType in zip(ifaces, ifaceNetworkTypes):
        if ifaceNetType == ifaceNetworkType:
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
    result = subprocess.run(['systemctl', 'is-active', 'WiRocWatchDog.service'], stdout=subprocess.PIPE)
    statusServices.append({'Name': 'WiRocWatchDog', 'Status': result.stdout.decode('utf-8').strip('\n')})
    jsonStr = json.dumps({'services': statusServices})
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


def uploadLogArchiveToServer(apiKey, filePath, serverProtocol, serverIP, serverHost):
    parameters = ['curl', '--insecure', '-X', 'POST', '-H', 'host:' + serverHost, '-H',
                  'accept:application/json', '-H', 'X-Authorization:' + apiKey, '-F', 'newfile=@' + filePath, serverProtocol + serverIP + '/api/v1/LogArchives']
    result = subprocess.run(parameters, capture_output=True)
    if result.returncode != 0:
        errStr = result.stderr.decode('utf-8')
        print('Helper.uploadLogArchive2: error: ' + errStr)
        raise Exception("Error: " + errStr)
    stdout = result.stdout.decode('utf-8')
    #if len(stdout) > 0:
    #    print(stdout)
    return 'OK'


def getZipFilePath(btAddress, date):
    filePath = "/home/chip/LogArchive/LogArchive_" + btAddress + "_" + date.now().strftime("%Y-%m-%d-%H:%M:%S") + ".zip"
    return filePath


@app.route('/api/listwifi/', methods=['GET'])
def getListWifi():
    # Get new wifi list
    result = subprocess.run(['nmcli', '-m', 'multiline', '-f', 'ssid,active,signal', 'device', 'wifi', 'list'], stdout=subprocess.PIPE)
    if result.returncode != 0:
        errStr = result.stderr.decode('utf-8')
        raise Exception("Error: " + errStr)

    wifiNetworks = result.stdout.decode('utf-8').splitlines()[0:-1]  # remove last empty element
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

def getWebServerProtocol():
    DatabaseHelper.reInit()
    proto = SettingsClass.GetWebServerProtocol()
    return proto

def getWebServerIP():
    DatabaseHelper.reInit()
    ip = SettingsClass.GetWebServerIP()
    return ip

@app.route('/api/uploadlogarchive/', methods=['GET'])
def uploadLogArchive():
    btAddress = getBTAddress()
    dateNow = datetime.datetime.now()
    zipFilePath = getZipFilePath(btAddress, dateNow)

    zipLogArchive(zipFilePath)

    apiKey = SettingsClass.GetAPIKey()
    serverProtocol = getWebServerProtocol()
    serverIP = getWebServerIP()
    serverHost = getWebServerHost()

    uploadLogArchiveToServer(apiKey, zipFilePath, serverProtocol, serverIP, serverHost)
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value='OK'))


@app.route('/api/startpatchap6212/', methods=['GET'])
def startPatchAP6212():
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    hostname = socket.gethostname()
    if hostname != "nanopiair":
        return jsonpickle.encode(MicroMock(Value='OK'))  # only nanopiair needs patching

    result = subprocess.run(
        ['systemctl', 'start', 'ap6212-bluetooth'], stdout=subprocess.PIPE)
    if result.returncode != 0:
        errStr = result.stderr.decode('utf-8')
        #print('Helper.startPatchAP6212: error: ' + errStr)

        result = subprocess.run(
            ['systemctl', 'start', 'ap6212-bluetooth'], stdout=subprocess.PIPE)
        if result.returncode != 0:
            errStr = result.stderr.decode('utf-8')
            #print('Helper.startPatchAP6212: second try error: ' + errStr)
            return jsonpickle.encode(MicroMock(Value='Error: ' + errStr))

    stdout = result.stdout.decode('utf-8')
    #if len(stdout) > 0:
    #    print(stdout)

    return jsonpickle.encode(MicroMock(Value='OK'))


@app.route('/api/upgradewirocble/<version>/', methods=['GET'])
def upgradeWiRocBLE(version):
    if HardwareAbstraction.Instance.runningOnChip:
        #print("upgradeWiRocBLEDevice")
        logfile = '../installWiRocBLE.log'
        with open(os.devnull, 'r+b') as DEVNULL:
            with open(logfile, 'a') as out:
                Popen(['./installWiRocBLE.sh %s' % version], shell=True, stdin=DEVNULL, stdout=out, stderr=out, close_fds=True, cwd='..')

        return jsonpickle.encode(MicroMock(Value='OK'))
    else:
        #print("upgradeWiRocBLE")
        logfile = '../installWiRocBLE.log'
        with open(os.devnull, 'r+b') as DEVNULL:
            with open(logfile, 'a') as out:
                Popen(['./installWiRocBLEAPI.sh %s' % version], shell=True, stdin=DEVNULL, stdout=out, stderr=out,
                      close_fds=True, cwd='..')

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
    if setting is not None:
        sirapPort = setting.Value

    setting = DatabaseHelper.get_setting_by_key('SendToSirapIP')
    sirapIP = ""
    if setting is not None:
        sirapIP = setting.Value

    setting = DatabaseHelper.get_setting_by_key('SendToSirapEnabled')
    sirapEnabled = '0'
    if setting is not None:
        sirapEnabled = setting.Value

    setting = DatabaseHelper.get_setting_by_key('AcknowledgementRequested')
    acksRequested = '1'
    if setting is not None:
        acksRequested = setting.Value

    setting = DatabaseHelper.get_setting_by_key('LoraRange')
    loraRange = 'L'
    if setting is not None:
        loraRange = setting.Value

    loraModule = SettingsClass.GetLoraModule()

    dataRate = SettingsClass.GetDataRate(loraRange)

    setting = DatabaseHelper.get_setting_by_key('Channel')
    channel = 1
    if setting is not None:
        channel = int(setting.Value)

    setting = DatabaseHelper.get_setting_by_key('LoraPower')
    loraPower = '7'
    if setting is not None:
        loraPower = setting.Value
    if loraModule == 'RF1276T' and int(loraPower) > 7:
        loraPower = '7'

    wiRocPythonVersion = settings['WiRocPythonVersion']
    #f = open("../WiRocPythonVersion.txt", "r")
    #wirocPythonVersion = f.read()
    #wirocPythonVersion = wirocPythonVersion.replace("\n", "")
    #f.close()

    wirocBLEVersion = settings['WiRocBLEAPIVersion']
    #f = open("../WiRocBLEVersion.txt", "r")
    #wirocBLEVersion = f.read()
    #wirocBLEVersion = wirocBLEVersion.replace("\n", "")
    #f.close()

    wirocHWVersion = settings['WiRocHWVersion']
    #f = open("../WiRocHWVersion.txt", "r")
    #wirocHWVersion = f.read()
    #wirocHWVersion = wirocHWVersion.replace("\n", "")
    #f.close()

    sett = DatabaseHelper.get_setting_by_key('OneWayReceive')
    oneWayReceive = '0'
    if sett is not None:
        oneWayReceive = sett.Value

    sett = DatabaseHelper.get_setting_by_key('Force4800BaudRate')
    force4800BaudRate = '0'
    if sett is not None:
        force4800BaudRate = sett.Value

    loramode = "RECEIVER"
    sett = DatabaseHelper.get_setting_by_key('LoraMode')
    if sett is not None:
        loramode = sett.Value

    sett = DatabaseHelper.get_setting_by_key('RxGainEnabled')
    rxGain = '1'
    if sett is not None:
        rxGain = sett.Value

    sett = DatabaseHelper.get_setting_by_key('CodeRate')
    codeRate = '0'
    if sett is not None:
        codeRate = sett.Value

    ipAddress = getIP()
    batteryPercent = getBatteryLevel()

    sett = DatabaseHelper.get_setting_by_key('RS232Mode')
    rs232Mode = 'RECEIVE'
    if sett is not None:
        rs232Mode = sett.Value

    sett = DatabaseHelper.get_setting_by_key('RS232OneWayReceive')
    RS232OneWayReceive = '0'
    if sett is not None:
        RS232OneWayReceive = sett.Value

    sett = DatabaseHelper.get_setting_by_key('ForceRS2324800BaudRate')
    forceRS2324800BaudRate = '0'
    if sett is not None:
        forceRS2324800BaudRate = sett.Value

    sett = DatabaseHelper.get_setting_by_key('BTSerialOneWayReceive')
    BTSerialOneWayReceive = '0'
    if sett is not None:
        BTSerialOneWayReceive = sett.Value

    sett = DatabaseHelper.get_setting_by_key('ForceBTSerial4800BaudRate')
    forceBTSerial4800BaudRate = '0'
    if sett is not None:
        forceBTSerial4800BaudRate = sett.Value

    allStr = ('1' if isCharging else '0') + '¤' + deviceName + '¤' + sirapPort + '¤' + sirapIP + '¤' + sirapEnabled + '¤' + \
        acksRequested + '¤' + str(dataRate) + '¤' + str(channel) + '¤' + batteryPercent + '¤' + \
        ipAddress + '¤' + str(loraPower) + '¤' + loraModule + '¤' + loraRange + '¤' + wirocPythonVersion + '¤' + \
        wirocBLEVersion + '¤' + wirocHWVersion + '¤' + oneWayReceive + '¤' + force4800BaudRate + '¤' + loramode + '¤' + \
        rxGain + '¤' + codeRate + '¤' + rs232Mode + '¤' + RS232OneWayReceive + '¤' + forceRS2324800BaudRate + '¤' + \
        BTSerialOneWayReceive + '¤' + forceBTSerial4800BaudRate

    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    return jsonpickle.encode(MicroMock(Value=allStr))
