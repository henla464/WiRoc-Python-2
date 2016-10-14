__author__ = 'henla464'

from settings.settings import SettingsClass
from loraradio.radio import Radio
from datamodel.db_helper import DatabaseHelper
from datamodel.datamodel import RadioMessageData
from battery.battery import Battery
from constants import *
from loraradio.timeslotmanager import TimeSlotManager
#import RPi.GPIO as GPIO
from os import listdir
from os.path import isfile, join
import threading
import time
import socket
import sys
from webroutes.radioconfiguration import *
from webroutes.meosconfiguration import *

battery = Battery()

class Main:
    settings = None
    timeSlotManager = None
    nextCallTimeSlotMessage = None
    inboundRadioMode = None
    radios = []
    sock = None

    def __init__(self):
        DatabaseHelper.ensure_tables_created()
        #DatabaseHelper.ensure_main_settings_exists()
        self.settings = SettingsClass()
        self.timeSlotManager = TimeSlotManager(self.settings)
        self.nextCallTimeSlotMessage = time.time()

        self.radios = []

        print("init")
        #detectedRadios = self.DetectRadios()
        #radioNumbers = [radio.GetRadioNumber() for radio in detectedRadios]
        #DatabaseHelper.ensure_radio_settings_exists(radioNumbers)

        #self.ConfigureRadios(detectedRadios)

    def ConfigureRadio(self, radio):
        radioNumber = radio.GetRadioNumber()
        print("radioNumber: ", end="")
        print(radioNumber)
        radioChannel = self.settings.GetRadioChannel(radioNumber)
        enabled = self.settings.GetRadioEnabled(radioNumber)
        if enabled and radioChannel is not None:
            radio.Init(radioChannel)
        else:
            radio.Disable()
            print("Radio not enabled")


    def ConfigureRadios(self, detectedRadios):
        oldRadioNumbers = [radio.GetRadioNumber() for radio in self.radios]
        newRadioNumbers = [radio.GetRadioNumber() for radio in detectedRadios]
        newRadios = [radio for radio in detectedRadios if radio.GetRadioNumber() not in oldRadioNumbers]
        # add and configure the newly detected radios that doesn't exist in old
        for newRadio in newRadios:
            self.ConfigureRadio(newRadio)
        self.radios += newRadios
        # disable and remove the radios that doesn't exist anymore
        radiosToRemove = [r for r in self.radios if r.GetRadioNumber() not in newRadioNumbers]
        for radioToRemove in radiosToRemove:
            radioToRemove.Disable()
        self.radios = [r for r in self.radios if r.GetRadioNumber() in newRadioNumbers]
        # reconfigure existing radios
        existingRadios = [r for r in self.radios if r.GetRadioNumber() in oldRadioNumbers]
        for existingRadio in existingRadios:
            self.ConfigureRadio(existingRadio)


    def Run(self):
        while True:
            self.GetInboundRadioMessageToDB()
            self.SendAckMessage()
            self.SendToCompetitionDatabase()
            self.SendTestMessage()
            self.CheckForChangesToConfigurationAndReconfigure()

    def CheckForChangesToConfigurationAndReconfigure(self):
        if self.settings.GetIsConfigurationDirty():
            SettingsClass.SetConfigurationDirty(False)
            self.settings.UpdateFromDatabase()
            detectedRadios = self.DetectRadios()
            self.ConfigureRadios(detectedRadios)
            if self.IsAnyRadioInP2MRetryMode():
                self.SetupSendTimeSlotMessageTimer()


    def PrintRadioMessage(self, radioMessage):
        print("RadioMessage: messageNumber: ", end="")
        print(radioMessage.messageNumber)
        for punch in radioMessage.dataRecordArray:
            print(" siCardNumber: " + str(punch.siCardNumber))

    def GetInboundRadioMessageToDB(self):
        #time.sleep(0.1)
        for radio in self.radios:
            if radio.GetIsInitialized():
                #print("for each radio initialized")
                radioMessage = radio.GetRadioData()
                if radioMessage is not None:
                    print("Radio message received from node: ", end="")
                    print(radioMessage.fromNode)
                    if radioMessage.messageType == PUNCH or radioMessage.messageType == COMBINED_PUNCH:
                        self.PrintRadioMessage(radioMessage)
                        DatabaseHelper.save_radio_message(radioMessage)


    def SendAckMessage(self):
        for radio in self.radios:
            if radio.GetIsInitialized():
                radioNumber = radio.GetRadioNumber()
                radioMode = self.settings.GetRadioMode(radioNumber)

                if radioMode == P2P_RETRY:
                    #send simple ack
                    radioMessages = DatabaseHelper.get_last_x_radio_message_data_not_acked(radioNumber, 1)
                    if len(radioMessages) > 0 and radioMessages[0].messageNumber is not None:
                        print("send simple ack")
                        radio.SendSimpleAckMessage(radioMessages[0].messageNumber)
                        radioMessages[0].ackSent = True
                        DatabaseHelper.save_radio_message(radioMessages[0])


    def SendToCompetitionDatabase(self):
        punches = DatabaseHelper.get_punches_to_send_to_meos()
        if self.settings.GetSendToMeosEnabled():
            if len(punches) > 0:
                # Create a TCP/IP socket
                #time.sleep(1)
                print("time1")
                if self.sock is None:
                    try:
                        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        print("Address: " + self.settings.GetMeosDatabaseServer() + " Port: " + str(self.settings.GetMeosDatabaseServerPort()))
                        server_address = (self.settings.GetMeosDatabaseServer(), self.settings.GetMeosDatabaseServerPort())
                        self.sock.connect(server_address)
                        print("after connect")
                    except socket.gaierror as msg:
                        print("Address-related error connecting to server: " + str(msg))
                        print("close")
                        self.sock.close()
                        self.sock = None
                        time.sleep(1)
                        return
                    except socket.error as msg:
                        print("Connection error: " + str(msg))
                        print("close")
                        self.sock.close()
                        self.sock = None
                        time.sleep(1)
                        return

                try:
                    for punch in punches:
                        stationNumber = DatabaseHelper.get_control_number_by_node_number(punch.origFromNode)
                        if stationNumber is not None:
                            print("send punch to meos")
                            punchBytesToSend = punch.GetMeosByteArray(stationNumber)

                            # Send data
                            self.sock.sendall(punchBytesToSend)
                            DatabaseHelper.set_punch_sent_to_meos(punch.id)
                        else:
                            DatabaseHelper.set_no_station_number_found(punch.id)
                except socket.error as msg:
                    print(msg)
                    self.sock = None
                #finally:
                    #print("close")
                    #self.sock.close()

    def SendTestMessage(self):
        for radio in self.radios:
            if radio.GetIsInitialized():
                radioNumber = radio.GetRadioNumber()
                radioMode = self.settings.GetRadioMode(radioNumber)

                if radioMode == TESTING and time.time() > radio.GetTimeOfLastTestMessageSent() + 5:
                    print("send testing message")
                    nodeNumber = self.settings.GetNodeNumber()
                    radio.SendTestMessage(nodeNumber)


def startMain():
    print("start main")
    main = Main()
    main.Run()

@app.route('/')
def index():
    return app.send_static_file('index.htm')

@app.route('/commonsettings', methods=['GET', 'POST'])
def common_settings():
    personId = request.form['personId'] #request.form.get('personId', type=int)
    return personId

def startWebServer():
    app.run(debug=True, host='0.0.0.0', use_reloader=False)

if __name__ == '__main__':
    print("main")
    threading.Thread(target=startMain).start()
    startWebServer()







