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


@app.route('/api/channel/', methods=['GET'])
def getChannel():
    DatabaseHelper.reInit()
    setting = DatabaseHelper.get_setting_by_key('Channel')
    channel = 1
    if setting != None:
        channel = int(setting.Value)
    return jsonpickle.encode(MicroMock(Channel=channel, Value=channel))

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
    return jsonpickle.encode(MicroMock(Channel=int(sd.Value), Value=int(sd.Value)))

@app.route('/api/datarate/', methods=['GET'])
def getDataRate():
    DatabaseHelper.reInit()
    setting = DatabaseHelper.get_setting_by_key('LoraRange')
    dataRate = 293
    if setting != None:
        dataRate = SettingsClass.GetDataRate(setting.Value)
    return jsonpickle.encode(MicroMock(DataRate=dataRate, Value=dataRate))

@app.route('/api/datarate/<int:dataRate>/', methods=['GET'])
def setDataRate(dataRate):
    DatabaseHelper.reInit()

    # for compatibility with newer code set LoraRange
    sd = DatabaseHelper.get_setting_by_key('LoraRange')
    if sd is None:
        sd = SettingData()
        sd.Key = 'LoraRange'

    loraRange = 'L'
    if dataRate == 73:
        loraRange = 'UL'
    elif dataRate == 134:
        loraRange = 'XL'
    elif dataRate == 244 or dataRate == 293:
        loraRange = 'L'
    elif dataRate == 439 or dataRate == 537:
        loraRange = 'ML'
    elif dataRate == 781 or dataRate == 977:
        loraRange = 'MS'
    elif dataRate == 1367 or dataRate == 1758:
        loraRange = 'S'

    sd.Value = loraRange
    sd = DatabaseHelper.save_setting(sd)

    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(DataRate=int(dataRate), Value=int(dataRate)))

@app.route('/api/lorarange/', methods=['GET'])
def getLoraRange():
    DatabaseHelper.reInit()
    setting = DatabaseHelper.get_setting_by_key('LoraRange')
    loraRange = 'L'
    if setting != None:
        loraRange = setting.Value
    return jsonpickle.encode(MicroMock(LoraRange=loraRange, Value=loraRange))

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
    return jsonpickle.encode(MicroMock(LoraRange=sd.Value, Value=sd.Value))

@app.route('/api/acknowledgementrequested/', methods=['GET'])
def getAcknowledgementRequested():
    DatabaseHelper.reInit()
    setting = DatabaseHelper.get_setting_by_key('AcknowledgementRequested')
    acksRequested = True
    if setting != None:
        acksRequested = (setting.Value == "1")
    return jsonpickle.encode(MicroMock(AcknowledgementRequested=acksRequested, Value=acksRequested))

@app.route('/api/acknowledgementrequested/<ack>/', methods=['GET'])
def setAcknowledgement(ack):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('AcknowledgementRequested')
    if sd is None:
        sd = SettingData()
        sd.Key = 'AcknowledgementRequested'
    sd.Value = '1' if ack.lower() == 'true' else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(AcknowledgementRequested=sd.Value == '1', Value=sd.Value == '1'))

@app.route('/api/power/', methods=['GET'])
def getPower():
    DatabaseHelper.reInit()
    setting = DatabaseHelper.get_setting_by_key('LoraPower')
    power = 0x07
    if setting != None:
        power = int(setting.Value)
    return jsonpickle.encode(MicroMock(Power=power, Value=power))

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
    return jsonpickle.encode(MicroMock(Power=int(sd.Value), Value=int(sd.Value)))

@app.route('/api/sendtosirapenabled/', methods=['GET'])
def GetSendToSirapEnabled():
    setting = DatabaseHelper.get_setting_by_key('SendToSirapEnabled')
    enabled = False
    if setting != None:
        enabled = (setting.Value == "1")
    return jsonpickle.encode(MicroMock(SendToSirapEnabled=enabled, Value=enabled))

@app.route('/api/sendtosirapenabled/<enabled>/', methods=['GET'])
def SetSendToSirapEnabled(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('SendToSirapEnabled')
    if sd is None:
        sd = SettingData()
        sd.Key = 'SendToSirapEnabled'
    sd.Value = '1' if enabled.lower() == 'true' else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(SendToSirapEnabled=sd.Value=='1', Value=sd.Value=='1'))

@app.route('/api/sendtosirapip/', methods=['GET'])
def GetSendToSirapIP():
    setting = DatabaseHelper.get_setting_by_key('SendToSirapIP')
    ip = ""
    if setting != None:
        ip = setting.Value
    return jsonpickle.encode(MicroMock(SendToSirapIP=ip, Value=ip))

@app.route('/api/sendtosirapip/<ip>/', methods=['GET'])
def SetSendToSirapIP(ip):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('SendToSirapIP')
    if sd is None:
        sd = SettingData()
        sd.Key = 'SendToSirapIP'
    sd.Value = ip
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(SendToSirapIP=sd.Value, Value=sd.Value))

@app.route('/api/sendtosirapipport/', methods=['GET'])
def getSendToSirapIPPort():
    setting = DatabaseHelper.get_setting_by_key('SendToSirapIPPort')
    port = ""
    if setting != None:
        port = setting.Value
    return jsonpickle.encode(MicroMock(SendToSirapIPPort=port, Value=port))

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
    return jsonpickle.encode(MicroMock(SendToSirapIPPort=sd.Value, Value=sd.Value))

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
    return json_data

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
    return json_data

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
    return settingData.Key + ';' + settingData.Value

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

    return json_data

@app.route('/api/wirocdevicename/', methods=['GET'])
def getWiRocDeviceName():
    f = open("../settings.yaml", "r")
    settings = yaml.load(f, Loader=yaml.BaseLoader)
    f.close()
    return jsonpickle.encode(MicroMock(WiRocDeviceName=settings['WiRocDeviceName'], Value=settings['WiRocDeviceName']))

@app.route('/api/wirocdevicename/<deviceName>', methods=['GET'])
def setWiRocDeviceName(deviceName):
    f = open("../settings.yaml", "r")
    settings = yaml.load(f, Loader=yaml.BaseLoader)
    f.close()
    settings['WiRocDeviceName'] = deviceName
    f2 = open('../settings.yaml', 'w')
    yaml.dump(settings, f2)  # Write a YAML representation of data to 'settings.yaml'.
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(WiRocDeviceName=deviceName, Value=deviceName))

@app.route('/api/database/<operation>/', methods=['GET'])
def deletePunches(operation):
    DatabaseHelper.reInit()
    if operation.lower() == "deletepunches":
        DatabaseHelper.delete_punches()
        return jsonpickle.encode(MicroMock(Status="OK"))
    elif operation.lower() == "dropalltables":
        DatabaseHelper.drop_all_tables()
        return jsonpickle.encode(MicroMock(Status="OK", Value="OK"))
    else:
        return jsonpickle.encode(MicroMock(Status="Operation not found", Value="Operation not found"))

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

    json_data = jsonpickle.encode(MicroMock(Status="OK", Value="OK"))
    return json_data

@app.route('/api/ischarging/', methods=['GET'])
def getIsCharging():
    isCharging = Battery.IsCharging()
    return jsonpickle.encode(MicroMock(IsCharging=isCharging, Value=isCharging))

@app.route('/api/apikey/', methods=['GET'])
def getApiKey():
    DatabaseHelper.reInit()
    apiKey = SettingsClass.GetAPIKey()
    return jsonpickle.encode(MicroMock(ApiKey=apiKey, Value=apiKey))

@app.route('/api/webserverurl/', methods=['GET'])
def getWebServerUrl():
    DatabaseHelper.reInit()
    webServerUrl = SettingsClass.GetWebServerUrl()
    host = webServerUrl.replace('http://', '').replace('https://', '')
    addrs = socket.getaddrinfo(host, 80)
    ipv4_addrs = [addr[4][0] for addr in addrs if addr[0] == socket.AF_INET]
    webServerUrl = webServerUrl.replace(host, ipv4_addrs[0])
    return jsonpickle.encode(MicroMock(WebServerUrl=webServerUrl, Value=webServerUrl))

@app.route('/api/webserverhost/', methods=['GET'])
def getWebServerHost():
    DatabaseHelper.reInit()
    webServerUrl = SettingsClass.GetWebServerUrl()
    webServerHost = webServerUrl.replace('http://', '').replace('https://', '')
    return jsonpickle.encode(MicroMock(WebServerHost=webServerHost, Value=webServerHost))


@app.route('/api/force4800baudrate/', methods=['GET'])
def getForce4800BaudRate():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('Force4800BaudRate')
    force4800BaudRate = False
    if sett is not None:
        force4800BaudRate = (sett.Value == "1")
    return jsonpickle.encode(MicroMock(Force4800BaudRate=force4800BaudRate, Value=force4800BaudRate))

@app.route('/api/force4800baudrate/<enabled>/', methods=['GET'])
def SetForce4800BaudRateEnabled(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('Force4800BaudRate')
    if sd is None:
        sd = SettingData()
        sd.Key = 'Force4800BaudRate'
    sd.Value = '1' if enabled.lower() == 'true' else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(Force4800BaudRate=sd.Value=='1', Value=sd.Value=='1'))


@app.route('/api/onewayreceive/', methods=['GET'])
def getOneWayReceive():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('OneWayReceive')
    oneWayReceive = False
    if sett is not None:
        oneWayReceive = (sett.Value == "1")
    return jsonpickle.encode(MicroMock(OneWayReceive=oneWayReceive, Value=oneWayReceive))

@app.route('/api/onewayreceive/<enabled>/', methods=['GET'])
def SetOneWayReceiveEnabled(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('OneWayReceive')
    if sd is None:
        sd = SettingData()
        sd.Key = 'OneWayReceive'
    sd.Value = '1' if enabled.lower() == 'true' else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(OneWayReceive=sd.Value=='1', Value=sd.Value=='1'))

@app.route('/api/logtoserver/', methods=['GET'])
def getLogToServer():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('LogToServer')
    logToServer = False
    if sett is not None:
        logToServer = (sett.Value == "1")
    return jsonpickle.encode(MicroMock(LogToServer=logToServer, Value=logToServer))

@app.route('/api/logtoserver/<enabled>/', methods=['GET'])
def SetLogToServerEnabled(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('LogToServer')
    if sd is None:
        sd = SettingData()
        sd.Key = 'LogToServer'
    sd.Value = '1' if enabled.lower() == 'true' else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(LogToServer=sd.Value=='1', Value=sd.Value=='1'))


@app.route('/api/loggingserverhost/', methods=['GET'])
def getLoggingServerHost():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('LoggingServerHost')
    loggingServerHost = ""
    if sett is not None:
        loggingServerHost = sett.Value
    return jsonpickle.encode(MicroMock(LoggingServerHost=loggingServerHost, Value=loggingServerHost))

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
    return jsonpickle.encode(MicroMock(LoggingServerHost=sd.Value, Value=sd.Value))

@app.route('/api/loggingserverport/', methods=['GET'])
def getLoggingServerPort():
    DatabaseHelper.reInit()
    sett = DatabaseHelper.get_setting_by_key('LoggingServerPort')
    loggingServerPort = ""
    if sett is not None:
        loggingServerPort = sett.Value
    return jsonpickle.encode(MicroMock(LoggingServerPort=loggingServerPort, Value=loggingServerPort))

@app.route('/api/loggingserverport/<port>/', methods=['GET'])
def SetLoggingServerPort(port):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('LoggingServerPort')
    if sd is None:
        sd = SettingData()
        sd.Key = 'LoggingServerPort'
    sd.Value = port
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(LoggingServerPort=sd.Value, Value=sd.Value))

@app.route('/api/wirocpythonversion/', methods=['GET'])
def GetWiRocPythonVersion():
    f = open("../../WiRocPythonVersion.txt", "r")
    wirocPythonVersion = f.read()
    f.close()
    return jsonpickle.encode(MicroMock(WiRocPythonVersion=wirocPythonVersion, Value=wirocPythonVersion))

@app.route('/api/wirocbleversion/', methods=['GET'])
def GetWiRocBLEVersion():
    f = open("../../wirocBLEVersion.txt", "r")
    wirocBLEVersion = f.read()
    f.close()
    return jsonpickle.encode(MicroMock(WirocBLEVersion=wirocBLEVersion, Value=wirocBLEVersion))

@app.route('/api/wirochwversion/', methods=['GET'])
def GetWiRocHWVersion():
    f = open("../../WirocHWVersion.txt", "r")
    wirocHWVersion = f.read()
    f.close()
    return jsonpickle.encode(MicroMock(WirocHWVersion=wirocHWVersion, Value=wirocHWVersion))

@app.route('/api/allmainsettings/', methods=['GET'])
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
    oneWayReceive = False
    if sett is not None:
        oneWayReceive = (sett.Value == "1")

    all = ('1' if isCharging else '0') + '¤' + deviceName + '¤' +  sirapPort + '¤' + sirapIP + '¤' + sirapEnabled + '¤' + \
          acksRequested + '¤' + str(dataRate) + '¤' + str(channel) + '¤' + '%batteryPercent%' + '¤' + \
          '%ipAddress%'+ '¤' + str(loraPower) + '¤' + loraModule + '¤' + loraRange + '¤' + wirocPythonVersion + '¤' + \
          wirocBLEVersion + '¤' + wirocHWVersion + '¤' + ('1' if oneWayReceive else '0')

    return jsonpickle.encode(MicroMock(All=all, Value=all))
