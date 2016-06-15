__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from datamodel.datamodel import RadioSettingsData
from datamodel.datamodel import InboundRadioNodeData
from settings.settings import SettingsClass
from flask import request
from init import *
import jsonpickle


@app.route('/radiosettings/getchannels', methods=['GET'])
def getChannels():
    channels = DatabaseHelper.get_channels()
    return jsonpickle.encode(MicroMock(Channels=channels))

@app.route('/radiosettings', methods=['POST'])
def saveRadioSettings():
    postedRadioSettings = request.get_json(force=True)
    #print(postedRadioSettings)
    radioSettings = RadioSettingsData()
    #print(radioSettings)
    radioSettings.id = postedRadioSettings['id']
    radioSettings.RadioNumber = postedRadioSettings['RadioNumber']
    radioSettings.Description = postedRadioSettings['Description']
    radioSettings.ChannelId = postedRadioSettings['ChannelId']
    radioSettings.RadioMode = postedRadioSettings['RadioMode']
    radioSettings.Enabled = postedRadioSettings['Enabled']
    radioSettings.RadioExists = postedRadioSettings['RadioExists']
    radioSettings.InboundRadioNodes = []
    postedInboundRadioNodes = postedRadioSettings['InboundRadioNodes']
    print(postedInboundRadioNodes)
    for postedNode in postedInboundRadioNodes:
        node = InboundRadioNodeData()
        node.id = None
        node.NodeNumber = postedNode['NodeNumber']
        node.RadioSettingsId = None  #set later
        radioSettings.InboundRadioNodes.append(node)
    savedRadioSettings = DatabaseHelper.save_radio_settings(radioSettings)
    SettingsClass.SetConfigurationDirty(True)
    return jsonpickle.encode(MicroMock(RadioSettings=savedRadioSettings))


#@app.route('/getpersonbyid', methods = ['POST'])
#def getPersonById():
 #   personId = int(request.form['personId'])
 #   return str(personId)  # back to a string to produce a proper response


#personId = request.form.get('personId', type=int)