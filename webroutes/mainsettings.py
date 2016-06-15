__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from datamodel.datamodel import MainSettingsData
from datamodel.datamodel import NodeToControlNumberData
from settings.settings import SettingsClass
from init import *
from flask import request
import jsonpickle


@app.route('/mainsettings/getradios', methods=['GET'])
def getRadios():
    radios = DatabaseHelper.get_radio_settings_data()
    #for radio in radios:
    #    radio.Title = "Radio " + str(radio.RadioNumber)

    return jsonpickle.encode(MicroMock(Radios=radios))

@app.route('/mainsettings', methods=['GET'])
def getMainSettings():
    main = DatabaseHelper.get_main_settings_data()
    print(main.MeosDatabaseServer)
    return jsonpickle.encode(MicroMock(mainSettings=main))

@app.route('/mainsettings/save', methods=['POST'])
def saveMainSettings():
    postedMainSettings = request.get_json(force=True)
    #print(postedRadioSettings)
    mainSettings = MainSettingsData()
    #print(radioSettings)
    mainSettings.id = None #save_main_settings will always update existing
    mainSettings.NodeNumber = postedMainSettings['NodeNumber']
    mainSettings.SendToMeosDatabase = postedMainSettings['SendToMeosDatabase']
    mainSettings.MeosDatabaseServer = postedMainSettings['MeosDatabaseServer']
    mainSettings.MeosDatabaseServerPort = postedMainSettings['MeosDatabaseServerPort']
    mainSettings.NodeToControlNumberMapping = []
    postedNodeToControlNumberMapping = postedMainSettings['NodeToControlNumberMapping']
    print(postedNodeToControlNumberMapping)
    for postedNodeToControl in postedNodeToControlNumberMapping:
        nodeToCtrl = NodeToControlNumberData()
        nodeToCtrl.id = None
        nodeToCtrl.NodeNumber = postedNodeToControl['NodeNumber']
        nodeToCtrl.ControlNumber = postedNodeToControl['ControlNumber']
        mainSettings.NodeToControlNumberMapping.append(nodeToCtrl)

    savedMainSettings = DatabaseHelper.save_main_settings(mainSettings)
    SettingsClass.SetConfigurationDirty(True)
    return jsonpickle.encode(MicroMock(MainSettings=savedMainSettings))

@app.route('/mainsettings/removeAllPunches', methods=['GET'])
def removeAllPunches():
    DatabaseHelper.remove_all_punches()
    return jsonpickle.encode(MicroMock(message="Punches deleted"))


@app.route('/mainsettings/recreateDatabase', methods=['GET'])
def recreateDatabase():
    DatabaseHelper.drop_all_tables()
    DatabaseHelper.ensure_tables_created()
    DatabaseHelper.add_default_channels()
    SettingsClass.SetConfigurationDirty(True)
    return jsonpickle.encode(MicroMock(message="Database emptied"))

@app.route('/mainsettings/scanForNewRadios', methods=['GET'])
def scanForNewRadios():
    SettingsClass.SetScanForNewRadiosRequest()
    return jsonpickle.encode(MicroMock(message="Scanning for new radios"))



