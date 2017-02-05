from loraradio.loraradio import LoraRadio
from settings.settings import SettingsClass
import inputadapters.receiveloraadapter
import pyudev
import logging
import socket

class SendLoraAdapter(object):
    Instances = []

    @staticmethod
    def CreateInstances():
        # check the number of lora radios and return an instance for each
        serialPorts = []

        if socket.gethostname() == 'chip':
            serialPorts.append('/dev/ttyS2')
        else:
            # https://github.com/dhylands/usb-ser-mon/blob/master/find_port.py
            uDevContext = pyudev.Context()
            for device in uDevContext.list_devices(subsystem='tty'):
                if 'ID_VENDOR_ID' in device:
                    if device['ID_VENDOR_ID'].lower() == '10c4' and \
                                    device['ID_MODEL_ID'].lower() == 'ea60':
                        #serialPorts.append(device.device_node)
                        "asdf"

        highestInstanceNumber = 0
        newInstances = []
        for serialDev in serialPorts:
            # only set up one send adapter
            if len(SendLoraAdapter.Instances) > 0:
                break

            alreadyCreated = False
            for instance in SendLoraAdapter.Instances:
                logging.info("SendLoraAdapter instance: " + instance.GetSerialDevicePath())
                if instance.GetSerialDevicePath() == serialDev:
                    alreadyCreated = True
                    newInstances.append(instance)
                    if instance.GetInstanceNumber() > highestInstanceNumber:
                        highestInstanceNumber = instance.GetInstanceNumber()

            #don't create both receive and send adapter for same serial port
            #for instance in inputadapters.receiveloraadapter.ReceiveLoraAdapter.Instances:
            #    if instance.GetSerialDevicePath() == serialDev:
            #        alreadyCreated = True

            if not alreadyCreated:
                highestInstanceNumber = highestInstanceNumber + 1
                logging.info("SendLoraAdapter created: " + serialDev + " instanceNo: " + str(highestInstanceNumber))
                newInstances.append(
                    SendLoraAdapter(highestInstanceNumber, serialDev))

        if len(newInstances) > 0:
            SendLoraAdapter.Instances = newInstances
        return SendLoraAdapter.Instances

    @staticmethod
    def GetTypeName():
        return "LORA"

    def __init__(self, instanceNumber, portName):
        self.instanceNumber = instanceNumber
        self.portName = portName
        self.loraRadio = LoraRadio.GetInstance(portName)
        self.transforms = {}

    def GetInstanceNumber(self):
        return self.instanceNumber

    def GetInstanceName(self):
        return "sndlora" + str(self.instanceNumber)

    def GetSerialDevicePath(self):
        return self.portName

    def GetDeleteAfterSent(self):
        # check setting for ack
        return not SettingsClass.GetAcknowledgementRequested()

    def GetTransformNames(self):
        #"BLEToLoraTransform",
        transforms = []
        if SettingsClass.GetLoraMode() == "SEND":
            transforms.append("SIToLoraTransform")
        else:
            transforms.append("LoraToLoraAckTransform")
        return transforms

    def SetTransform(self, transformClass):
        logging.info("Add transform: " + transformClass.GetName())
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName):
        return self.transforms[transformName]

    def GetIsInitialized(self):
        channel = SettingsClass.GetChannel()
        loraDataRate = SettingsClass.GetDataRate()
        return self.loraRadio.GetIsInitialized(channel, loraDataRate)

    def Init(self):
        channel = SettingsClass.GetChannel()
        loraDataRate = SettingsClass.GetDataRate()
        if self.loraRadio.GetIsInitialized(channel, loraDataRate):
            return True
        return self.loraRadio.Init(channel, loraDataRate)

    # messageData is a bytearray
    def SendData(self, messageData):
        self.loraRadio.SendData(messageData)
        logging.info("Sent to LORA")
        return True
