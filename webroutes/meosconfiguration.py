__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass
from datamodel.datamodel import SettingData
from init import *
from flask import request
import jsonpickle


@app.route('/meosconfiguration/sendtomeosenabled/', methods=['GET'])
def GetSendToMeosEnabled():
    enabled = SettingsClass.GetSendToMeosEnabled(True)
    return jsonpickle.encode(MicroMock(SendToMeosEnabled=enabled))

@app.route('/meosconfiguration/sendtomeosenabled/<enabled>/', methods=['GET'])
def SetSendToMeosEnabled(enabled):
    sd = DatabaseHelper.webDatabaseHelper.get_setting_by_key('SendToMeosEnabled')
    if sd is None:
        sd = SettingData()
        sd.Key = 'SendToMeosEnabled'
    sd.Value = 'True' if enabled.lower() == 'true' else 'False'
    sd = DatabaseHelper.webDatabaseHelper.save_setting(sd)
    SettingsClass.SetConfigurationDirty('SendToMeosEnabled')
    return jsonpickle.encode(MicroMock(SendToMeosEnabled=sd.Value.lower()=='true'))

@app.route('/meosconfiguration/sendtomeosip/', methods=['GET'])
def GetSendToMeosIP():
   ip = SettingsClass.GetSendToMeosIP(True)
   return jsonpickle.encode(MicroMock(SendToMeosIP=ip))

@app.route('/meosconfiguration/sendtomeosip/<ip>/', methods=['GET'])
def SetSendToMeosIP(ip):
    sd = DatabaseHelper.webDatabaseHelper.get_setting_by_key('SendToMeosIP')
    if sd is None:
        sd = SettingData()
        sd.Key = 'SendToMeosIP'
    sd.Value = ip
    sd = DatabaseHelper.webDatabaseHelper.save_setting(sd)
    SettingsClass.SetConfigurationDirty('SendToMeosIP')
    return jsonpickle.encode(MicroMock(SendToMeosIP=sd.Value))


@app.route('/meosconfiguration/sendtomeosipport/', methods=['GET'])
def getSendToMeosIPPort():
   port = SettingsClass.GetSendToMeosIPPort(True)
   return jsonpickle.encode(MicroMock(SendToMeosIPPort=port))


@app.route('/meosconfiguration/sendtomeosipport/<port>/', methods=['GET'])
def setSendToMeosIPPort(port):
    sd = DatabaseHelper.webDatabaseHelper.get_setting_by_key('SendToMeosIPPort')
    if sd is None:
        sd = SettingData()
        sd.Key = 'SendToMeosIPPort'
    sd.Value = port
    sd = DatabaseHelper.webDatabaseHelper.save_setting(sd)
    SettingsClass.SetConfigurationDirty('SendToMeosIPPort')
    return jsonpickle.encode(MicroMock(SendToMeosIPPort=sd.Value))

