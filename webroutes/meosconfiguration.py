__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass
from datamodel.datamodel import SettingData
from init import *
from flask import request
import jsonpickle


@app.route('/meosconfiguration/sendtomeosenabled/', methods=['GET'])
def GetSendToMeosEnabled():
    enabled = SettingsClass.GetSendToMeosEnabled(False)
    return jsonpickle.encode(MicroMock(SendToMeosEnabled=enabled))

@app.route('/meosconfiguration/sendtomeosenabled/<enabled>/', methods=['GET'])
def SetSendToMeosEnabled(enabled):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('SendToMeosEnabled')
    if sd is None:
        sd = SettingData()
        sd.Key = 'SendToMeosEnabled'
    sd.Value = '1' if enabled.lower() == 'true' else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetConfigurationDirty('SendToMeosEnabled', True)
    return jsonpickle.encode(MicroMock(SendToMeosEnabled=sd.Value.lower()=='true'))

@app.route('/meosconfiguration/sendtomeosip/', methods=['GET'])
def GetSendToMeosIP():
   ip = SettingsClass.GetSendToMeosIP(False)
   return jsonpickle.encode(MicroMock(SendToMeosIP=ip))

@app.route('/meosconfiguration/sendtomeosip/<ip>/', methods=['GET'])
def SetSendToMeosIP(ip):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('SendToMeosIP')
    if sd is None:
        sd = SettingData()
        sd.Key = 'SendToMeosIP'
    sd.Value = ip
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetConfigurationDirty('SendToMeosIP', True)
    return jsonpickle.encode(MicroMock(SendToMeosIP=sd.Value))


@app.route('/meosconfiguration/sendtomeosipport/', methods=['GET'])
def getSendToMeosIPPort():
   port = SettingsClass.GetSendToMeosIPPort(False)
   return jsonpickle.encode(MicroMock(SendToMeosIPPort=port))


@app.route('/meosconfiguration/sendtomeosipport/<port>/', methods=['GET'])
def setSendToMeosIPPort(port):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('SendToMeosIPPort')
    if sd is None:
        sd = SettingData()
        sd.Key = 'SendToMeosIPPort'
    sd.Value = port
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetConfigurationDirty('SendToMeosIPPort', True)
    return jsonpickle.encode(MicroMock(SendToMeosIPPort=sd.Value))

