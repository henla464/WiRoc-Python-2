__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass
from datamodel.datamodel import SettingData
from init import *
from flask import request
import jsonpickle


@app.route('/radioconfiguration/channel/', methods=['GET'])
def getChannel():
    DatabaseHelper.reInit()
    setting = DatabaseHelper.get_setting_by_key('Channel')
    channel = 1
    if setting != None:
        channel = int(setting.Value)
    return jsonpickle.encode(MicroMock(Channel=channel))

@app.route('/radioconfiguration/channel/<int:channel>/', methods=['GET'])
def setChannel(channel):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('Channel')
    if sd is None:
        sd = SettingData()
        sd.Key = 'Channel'
    sd.Value = channel
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(Channel=int(sd.Value)))

@app.route('/radioconfiguration/datarate/', methods=['GET'])
def getDataRate():
    DatabaseHelper.reInit()
    setting = DatabaseHelper.get_setting_by_key('DataRate')
    dataRate = 293
    if setting != None:
        dataRate = int(setting.Value)
    return jsonpickle.encode(MicroMock(DataRate=dataRate))

@app.route('/radioconfiguration/datarate/<int:dataRate>/', methods=['GET'])
def setDataRate(dataRate):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('DataRate')
    if sd is None:
        sd = SettingData()
        sd.Key = 'DataRate'
    sd.Value = dataRate
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(DataRate=int(sd.Value)))


@app.route('/radioconfiguration/acknowledgementrequested/', methods=['GET'])
def getAcknowledgementRequested():
    DatabaseHelper.reInit()
    setting = DatabaseHelper.get_setting_by_key('AcknowledgementRequested')
    acksRequested = True
    if setting != None:
        acksRequested = (setting.Value == "1")
    return jsonpickle.encode(MicroMock(AcknowledgementRequested=acksRequested))

@app.route('/radioconfiguration/acknowledgementrequested/<ack>/', methods=['GET'])
def setAcknowledgement(ack):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('AcknowledgementRequested')
    if sd is None:
        sd = SettingData()
        sd.Key = 'AcknowledgementRequested'
    sd.Value = '1' if ack.lower() == 'true' else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(AcknowledgementRequested=sd.Value == '1'))

@app.route('/radioconfiguration/power/', methods=['GET'])
def getPower():
    DatabaseHelper.reInit()
    setting = DatabaseHelper.get_setting_by_key('LoraPower')
    power = 0x07
    if setting != None:
        power = int(setting.Value)
    return jsonpickle.encode(MicroMock(Power=power))

@app.route('/radioconfiguration/power/<int:power>/', methods=['GET'])
def setPower(power):
    DatabaseHelper.reInit()
    sd = DatabaseHelper.get_setting_by_key('LoraPower')
    if sd is None:
        sd = SettingData()
        sd.Key = 'LoraPower'
    sd.Value = power
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetSettingUpdatedByWebService()
    return jsonpickle.encode(MicroMock(Power=int(sd.Value)))

