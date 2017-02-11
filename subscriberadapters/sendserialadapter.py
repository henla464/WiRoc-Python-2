from settings.settings import SettingsClass
from serialcomputer.serialcomputer import SerialComputer
from datamodel.db_helper import DatabaseHelper
import socket
import logging
import os

class SendSerialAdapter(object):
    Instances = []

    @staticmethod
    def CreateInstances():
        serialPorts = []

        if socket.gethostname() == 'chip':
            if os.path.exists('/dev/ttyGS0'):
                serialPorts.append('/dev/ttyGS0')

        newInstances = []
        for serialDev in serialPorts:
            alreadyCreated = False
            for instance in SendSerialAdapter.Instances:
                if instance.GetSerialDevicePath() == serialDev:
                    alreadyCreated = True
                    newInstances.append(instance)

            if not alreadyCreated:
                newInstances.append(
                    SendSerialAdapter(1 + len(newInstances), serialDev))

        SendSerialAdapter.Instances = newInstances
        SendSerialAdapter.EnableDisableSubscription()
        return SendSerialAdapter.Instances

    @staticmethod
    def EnableDisableSubscription():
        if len(SendSerialAdapter.Instances) > 0:
            if SendSerialAdapter.Instances[0].TestConnection():
                logging.info("Setting SetSendSerialAdapterActive True")
                if not SettingsClass.GetSendSerialAdapterActive():
                    SettingsClass.SetSendSerialAdapterActive(True)
                    DatabaseHelper.mainDatabaseHelper.set_subscriptions_enabled(True, SendSerialAdapter.GetTypeName())
            else:
                logging.info("Setting SetSendSerialAdapterActive False")
                if SettingsClass.GetSendSerialAdapterActive():
                    SettingsClass.SetSendSerialAdapterActive(False)
                    DatabaseHelper.mainDatabaseHelper.set_subscriptions_enabled(False, SendSerialAdapter.GetTypeName())
        else:
            logging.info("Setting SetSendSerialAdapterActive False 2")
            if SettingsClass.GetSendSerialAdapterActive():
                SettingsClass.SetSendSerialAdapterActive(False)

    @staticmethod
    def GetTypeName():
        return "SERIAL"

    def __init__(self, instanceNumber, portName):
        self.instanceNumber = instanceNumber
        self.portName = portName
        self.serialComputer = SerialComputer.GetInstance(portName)
        self.transforms = {}
        self.isDBInitialized = False

    def GetInstanceNumber(self):
        return self.instanceNumber

    def GetInstanceName(self):
        return "sndserial" + str(self.instanceNumber)

    def GetSerialDevicePath(self):
        return self.portName

    def GetDeleteAfterSent(self):
        # check setting for ack
        return True

    def GetTransformNames(self):
        #"BLEToSITransform", SIToSITransform
        return ["LoraToSITransform"]

    def SetTransform(self, transformClass):
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName):
        return self.transforms[transformName]

    def TestConnection(self):
        return self.serialComputer.TestConnection()

    def GetIsInitialized(self):
        return self.serialComputer.GetIsInitialized()

    def GetIsDBInitialized(self):
        return self.isDBInitialized

    def SetIsDBInitialized(self, val = True):
        self.isDBInitialized = val

    def Init(self):
        return self.serialComputer.Init()

    # messageData is a bytearray
    def SendData(self, messageData):
        if self.TestConnection():
            self.serialComputer.SendData(messageData)
            logging.info("Sent to SI computer")
            return True
        else:
            logging.info("Could not send to SI computer, test connection failed")
            SendSerialAdapter.EnableDisableSubscription()
            return False
