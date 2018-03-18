__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass
from datamodel.datamodel import SettingData
from init import *
from flask import request
import jsonpickle


@app.route('/radioconfiguration/channel/', methods=['GET'])
def getChannel():
    channel = SettingsClass.GetChannel(False)
    return jsonpickle.encode(MicroMock(Channel=channel))

@app.route('/radioconfiguration/channel/<int:channel>/', methods=['GET'])
def setChannel(channel):
    sd = DatabaseHelper.get_setting_by_key('Channel')
    if sd is None:
        sd = SettingData()
        sd.Key = 'Channel'
    sd.Value = channel
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetConfigurationDirty('Channel', True)
    return jsonpickle.encode(MicroMock(Channel=int(sd.Value)))

@app.route('/radioconfiguration/datarate/', methods=['GET'])
def getDataRate():
   dataRate = SettingsClass.GetDataRate(False)
   return jsonpickle.encode(MicroMock(DataRate=dataRate))

@app.route('/radioconfiguration/datarate/<int:dataRate>/', methods=['GET'])
def setDataRate(dataRate):
    sd = DatabaseHelper.get_setting_by_key('DataRate')
    if sd is None:
        sd = SettingData()
        sd.Key = 'DataRate'
    sd.Value = dataRate
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetConfigurationDirty('DataRate', True)
    return jsonpickle.encode(MicroMock(DataRate=int(sd.Value)))


@app.route('/radioconfiguration/acknowledgementrequested/', methods=['GET'])
def getAcknowledgementRequested():
   acksRequested = SettingsClass.GetAcknowledgementRequested(False)
   return jsonpickle.encode(MicroMock(AcknowledgementRequested=acksRequested))


@app.route('/radioconfiguration/acknowledgementrequested/<ack>/', methods=['GET'])
def setAcknowledgement(ack):
    sd = DatabaseHelper.get_setting_by_key('AcknowledgementRequested')
    if sd is None:
        sd = SettingData()
        sd.Key = 'AcknowledgementRequested'
    sd.Value = '1' if ack.lower() == 'true' else '0'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetConfigurationDirty('AcknowledgementRequested', True)
    return jsonpickle.encode(MicroMock(AcknowledgementRequested=sd.Value == '1'))

@app.route('/radioconfiguration/power/', methods=['GET'])
def getPower():
    power = SettingsClass.GetLoraPower(False)
    return jsonpickle.encode(MicroMock(Power=power))

@app.route('/radioconfiguration/power/<int:power>/', methods=['GET'])
def setPower(power):
    sd = DatabaseHelper.get_setting_by_key('LoraPower')
    if sd is None:
        sd = SettingData()
        sd.Key = 'LoraPower'
    sd.Value = power
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetConfigurationDirty('LoraPower', True)
    return jsonpickle.encode(MicroMock(Power=int(sd.Value)))

