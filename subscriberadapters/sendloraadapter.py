from loraradio.loraradio import LoraRadio
from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
import pyudev
import serial
import logging
import socket

class SendLoraAdapter(object):
    Instances = []
    WiRocMode = None
    SubscriptionsEnabled = None
    AdapterInitialized = None

    @staticmethod
    def CreateInstances():
        # check the number of lora radios and return an instance for each
        serialPorts = []

        if socket.gethostname() == 'chip':
            serialPorts.append('/dev/ttyS2')
        else:
            portInfoList = serial.tools.list_ports.grep('10c4:ea60')
            for portInfo in portInfoList:
                serialPorts.append(portInfo.device)

        if len(serialPorts) > 0:
            if len(SendLoraAdapter.Instances) > 0:
                if SendLoraAdapter.Instances[0].GetSerialDevicePath() != serialPorts[0]:
                    SendLoraAdapter.Instances[0] = SendLoraAdapter(1, serialPorts[0])
                    return True
                elif SendLoraAdapter.WiRocMode is None or SendLoraAdapter.WiRocMode != SettingsClass.GetWiRocMode():
                    return True
            else:
                SendLoraAdapter.Instances.append(SendLoraAdapter(1, serialPorts[0]))
                return True
        else:
            if len(SendLoraAdapter.Instances) > 0:
                SendLoraAdapter.Instances = []
                return True
        return False

    @staticmethod
    def GetTypeName():
        return "LORA"

    @staticmethod
    def EnableDisableSubscription():
        if len(SendLoraAdapter.Instances) > 0:
            isInitialized = SendLoraAdapter.Instances[0].GetIsInitialized()
            deleteAfterSent = SendLoraAdapter.GetDeleteAfterSent()
            shouldSubscriptionBeEnabled = isInitialized
            if (SendLoraAdapter.SubscriptionsEnabled != shouldSubscriptionBeEnabled or
                SendLoraAdapter.DeleteAfterSent != deleteAfterSent):
                SendLoraAdapter.SubscriptionsEnabled = shouldSubscriptionBeEnabled
                SendLoraAdapter.DeleteAfterSent = deleteAfterSent
                logging.info("SendLoraAdapter::EnableDisableSubscription() subscription set enabled: " + str(shouldSubscriptionBeEnabled))
                DatabaseHelper.update_subscriptions(shouldSubscriptionBeEnabled, deleteAfterSent, SendLoraAdapter.GetTypeName())

    @staticmethod
    def EnableDisableTransforms():
        if len(SendLoraAdapter.Instances) > 0:
            if SendLoraAdapter.WiRocMode is None or SendLoraAdapter.WiRocMode != SettingsClass.GetWiRocMode():
                SendLoraAdapter.WiRocMode = SettingsClass.GetWiRocMode()
                enableSendTransforms = (SendLoraAdapter.WiRocMode == "SEND" or SendLoraAdapter.WiRocMode == "REPEATER")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "SIToLoraTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "SITestToLoraTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "StatusToLoraTransform")
                #DatabaseHelper.set_transform_enabled(not enableSendTransforms, "LoraToLoraAckTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "RepeaterToLoraAckTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "RepeaterToLoraTransform")

    def __init__(self, instanceNumber, portName):
        self.instanceNumber = instanceNumber
        self.portName = portName
        self.loraRadio = LoraRadio.GetInstance(portName)
        self.transforms = {}
        self.isDBInitialized = False

    def GetInstanceNumber(self):
        return self.instanceNumber

    def GetInstanceName(self):
        return "sndlora" + str(self.instanceNumber)

    def GetSerialDevicePath(self):
        return self.portName

    @staticmethod
    def GetDeleteAfterSent():
        # check setting for ack
        return not SettingsClass.GetAcknowledgementRequested()

    # when receiving from other WiRoc device, should we wait until the other
    # WiRoc device sent an ack to aviod sending at same time
    @staticmethod
    def GetWaitUntilAckSent():
        return True

    # return both receive and send transforms, they will be enabled/disabled automatically depending
    # on lora mode
    def GetTransformNames(self):
        transforms = []
        transforms.append("SIToLoraTransform")
        transforms.append("SITestToLoraTransform")
        transforms.append("StatusToLoraTransform")
        transforms.append("RepeaterToLoraAckTransform")
        transforms.append("RepeaterToLoraTransform")
        return transforms

    def SetTransform(self, transformClass):
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName):
        return self.transforms[transformName]

    def GetIsInitialized(self):
        channel = SettingsClass.GetChannel()
        loraDataRate = SettingsClass.GetDataRate()
        return self.loraRadio.GetIsInitialized(channel, loraDataRate)

    def ShouldBeInitialized(self):
        channel = SettingsClass.GetChannel()
        loraDataRate = SettingsClass.GetDataRate()
        loraRadioInitialized = self.loraRadio.GetIsInitialized(channel, loraDataRate)
        # initialize if loraRadio isn't initialized yet, or if the loraradio initialization status changed
        return not loraRadioInitialized or SendLoraAdapter.Instances[0].AdapterInitialized != loraRadioInitialized

    # has adapter, transforms, subscriptions etc been added to database?
    def GetIsDBInitialized(self):
        return self.isDBInitialized

    def SetIsDBInitialized(self, val = True):
        self.isDBInitialized = val

    def Init(self):
        channel = SettingsClass.GetChannel()
        loraDataRate = SettingsClass.GetDataRate()
        # set the AdapterInitialized to same value as loraRadios initialized
        # if loraRadio changes initialize value later we can detect this.
        if self.loraRadio.GetIsInitialized(channel, loraDataRate):
            SendLoraAdapter.Instances[0].AdapterInitialized = True
            return True
        loraInitialized = self.loraRadio.Init(channel, loraDataRate)
        SendLoraAdapter.Instances[0].AdapterInitialized = loraInitialized
        return loraInitialized

    def IsReadyToSend(self):
        return self.loraRadio.IsReadyToSend()

    # messageData is a bytearray
    def SendData(self, messageData):
        return self.loraRadio.SendData(messageData)
