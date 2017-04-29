__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass
from datamodel.datamodel import SettingData
from init import *
from flask import request
import jsonpickle
import json

@app.route('/misc/status/', methods=['GET'])
def getStatus():
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

@app.route('/misc/setting/<keyandvalue>/', methods=['GET'])
def setSetting(keyandvalue):
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
    deviceName = SettingsClass.GetWiRocDeviceName(False)
    return jsonpickle.encode(MicroMock(WiRocDeviceName=deviceName))

@app.route('/misc/database/<operation>/', methods=['GET'])
def deletePunches(operation):
    if operation.lower() == "deletepunches":
        DatabaseHelper.delete_punches()
        return jsonpickle.encode(MicroMock(Status="OK"))
    elif operation.lower() == "dropalltables":
        DatabaseHelper.drop_all_tables()
        return jsonpickle.encode(MicroMock(Status="OK"))
    else:
        return jsonpickle.encode(MicroMock(Status="Operation not found"))
