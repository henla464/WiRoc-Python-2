__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass
from datamodel.datamodel import SettingData
from init import *
from flask import request
import jsonpickle


@app.route('/radioconfiguration/channel/', methods=['GET'])
def getChannel():
    channel = SettingsClass.GetChannel()
    return jsonpickle.encode(MicroMock(Channel=channel))

@app.route('/radioconfiguration/channel/<int:channel>/', methods=['GET'])
def setChannel(channel):
    sd = DatabaseHelper.get_setting_by_key('Channel')
    if sd is None:
        sd = SettingData()
        sd.Key = 'Channel'
    sd.Value = channel
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetConfigurationDirty('Channel')
    return jsonpickle.encode(MicroMock(Channel=int(sd.Value)))

@app.route('/radioconfiguration/datarate/', methods=['GET'])
def getDataRate():
   dataRate = SettingsClass.GetDataRate()
   return jsonpickle.encode(MicroMock(DataRate=dataRate))

@app.route('/radioconfiguration/datarate/<int:dataRate>/', methods=['GET'])
def setDataRate(dataRate):
    sd = DatabaseHelper.get_setting_by_key('DataRate')
    if sd is None:
        sd = SettingData()
        sd.Key = 'DataRate'
    if dataRate <= 219:
        sd.Value = 146
    elif dataRate <= 439:
        sd.Value = 293
    elif dataRate <= 1367:
        sd.Value = 586
    elif dataRate <= 4590:
        sd.Value = 2148
    else:
        sd.Value = 7032
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetConfigurationDirty('DataRate')
    return jsonpickle.encode(MicroMock(DataRate=int(sd.Value)))


@app.route('/radioconfiguration/acknowledgementrequested/', methods=['GET'])
def getAcknowledgementRequested():
   acksRequested = SettingsClass.GetAcknowledgementRequested()
   return jsonpickle.encode(MicroMock(AcknowledgementRequested=acksRequested))


@app.route('/radioconfiguration/acknowledgementrequested/<ack>/', methods=['GET'])
def setAcknowledgement(ack):
    sd = DatabaseHelper.get_setting_by_key('AcknowledgementRequested')
    if sd is None:
        sd = SettingData()
        sd.Key = 'AcknowledgementRequested'
    sd.Value = 'True' if ack.lower() == 'true' else 'False'
    sd = DatabaseHelper.save_setting(sd)
    SettingsClass.SetConfigurationDirty('AcknowledgementRequested')
    return jsonpickle.encode(MicroMock(AcknowledgementRequested=sd.Value.lower()=='true'))


