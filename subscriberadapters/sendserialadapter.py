from settings.settings import SettingsClass
from serialcomputer.serialcomputer import SerialComputer
from datamodel.db_helper import DatabaseHelper
import socket
import logging
import os

class SendSerialAdapter(object):
    Instances = []
    SendSerialAdapterActive = None

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
        return SendSerialAdapter.Instances

    @staticmethod
    def EnableDisableSubscription():
        logging.debug("SendSerialAdapter::EnableDisableSubscription()")
        if len(SendSerialAdapter.Instances) > 0:
            if SendSerialAdapter.Instances[0].TestConnection():
                if SendSerialAdapter.SendSerialAdapterActive is None or not SendSerialAdapter.SendSerialAdapterActive:
                    logging.info("SendSerialAdapter::EnableDisableSubscription() update subscription enable")
                    SendSerialAdapter.SendSerialAdapterActive = True
                    SettingsClass.SetSendSerialAdapterActive(True)
                    DatabaseHelper.mainDatabaseHelper.update_subscriptions(True, SendSerialAdapter.GetDeleteAfterSent(), SendSerialAdapter.GetTypeName())
            else:
                if SendSerialAdapter.SendSerialAdapterActive is None or SendSerialAdapter.SendSerialAdapterActive:
                    logging.info("SendSerialAdapter::EnableDisableSubscription() update subscription disable")
                    SendSerialAdapter.SendSerialAdapterActive = False
                    SettingsClass.SetSendSerialAdapterActive(False)
                    DatabaseHelper.mainDatabaseHelper.update_subscriptions(False, SendSerialAdapter.GetDeleteAfterSent(), SendSerialAdapter.GetTypeName())
        else:
            logging.debug("SendSerialAdapter::EnableDisableSubscription() Setting SetSendSerialAdapterActive False 2")
            if SettingsClass.GetSendSerialAdapterActive():
                SendSerialAdapter.SendSerialAdapterActive = False
                SettingsClass.SetSendSerialAdapterActive(False)

    @staticmethod
    def GetTypeName():
        return "SERIAL"

    @staticmethod
    def EnableDisableTransforms():
        return None

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

    @staticmethod
    def GetDeleteAfterSent():
        # check setting for ack
        return True

    def GetTransformNames(self):
        return ["LoraToSITransform", "SIToSITransform"]

    def SetTransform(self, transformClass):
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName):
        return self.transforms[transformName]

    def TestConnection(self):
        return self.serialComputer.TestConnection()

    def GetIsInitialized(self):
        return self.serialComputer.GetIsInitialized()

    # has adapter, transforms, subscriptions etc been added to database?
    def GetIsDBInitialized(self):
        return self.isDBInitialized

    def SetIsDBInitialized(self, val = True):
        self.isDBInitialized = val

    def Init(self):
        return self.serialComputer.Init()

    # messageData is a bytearray
    def SendData(self, messageData):
        if self.serialComputer.SendData(messageData):
            logging.debug("SendSerialAdapter::SendData() Sent to computer")
            return True
        else:
            logging.warning("SendSerialAdapter::SendData() Could not send to computer, call EnableDisableSubscription")
            SendSerialAdapter.EnableDisableSubscription()
            return False
