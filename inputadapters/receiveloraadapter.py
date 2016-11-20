import pyudev
import traceback
from loraradio.loraradio import LoraRadio
from settings.settings import SettingsClass
import subscriberadapters
import time
import logging

class ReceiveLoraAdapter(object):

    Instances = []
    @staticmethod
    def CreateInstances():
        # check the number of lora radios and return an instance for each
        serialPorts = []
        # https://github.com/dhylands/usb-ser-mon/blob/master/find_port.py
        uDevContext = pyudev.Context()
        for device in uDevContext.list_devices(subsystem='tty'):
            if 'ID_VENDOR_ID' in device:
                if device['ID_VENDOR_ID'].lower() == '10c4' and \
                                device['ID_MODEL_ID'].lower() == 'ea60':
                    serialPorts.append(device.device_node)

        highestInstanceNumber = 0
        newInstances = []
        for serialDev in serialPorts:
            # only set up one receive adapter
            if len(ReceiveLoraAdapter.Instances) > 0:
                break

            alreadyCreated = False
            for instance in ReceiveLoraAdapter.Instances:
                if instance.GetSerialDevicePath() == serialDev:
                    alreadyCreated = True
                    newInstances.append(instance)
                    if instance.GetInstanceNumber() > highestInstanceNumber:
                        highestInstanceNumber = instance.GetInstanceNumber()

            # don't create both receive and send adapter for same serial port
            for instance in subscriberadapters.sendloraadapter.SendLoraAdapter.Instances:
                if instance.GetSerialDevicePath() == serialDev:
                    alreadyCreated = True

            if not alreadyCreated:
                highestInstanceNumber = highestInstanceNumber + 1
                newInstances.append(
                    ReceiveLoraAdapter(highestInstanceNumber, serialDev))

        ReceiveLoraAdapter.Instances = newInstances
        return ReceiveLoraAdapter.Instances


    @staticmethod
    def GetTypeName():
        return "LORA"

    def __init__(self, instanceNumber, portName):
        self.instanceNumber = instanceNumber
        self.portName = portName
        self.loraRadio = LoraRadio.GetInstance(portName)

    def GetInstanceNumber(self):
        return self.instanceNumber

    def GetInstanceName(self):
        return "reclora" + str(self.instanceNumber)

    def GetSerialDevicePath(self):
        return self.portName

    def GetIsInitialized(self):
        channel = SettingsClass.GetChannel()
        loraDataRate = SettingsClass.GetDataRate()
        return self.loraRadio.GetIsInitialized(channel, loraDataRate)

    def Init(self):
        channel = SettingsClass.GetChannel()
        loraDataRate = SettingsClass.GetDataRate()
        if self.loraRadio.GetIsInitialized(channel, loraDataRate):
            return True
        self.loraRadio.Init(channel, loraDataRate)


    # messageData is a bytearray
    def GetData(self):
        loraMessage = None
        try:
            loraMessage = self.loraRadio.GetRadioData()
        except Exception as ex:
            logging.error("Error reading from lora " + traceback.format_exc())
            time.sleep(2)

        if loraMessage is not None:
            receivedData = loraMessage.GetByteArray()
            isChecksumOK = loraMessage.GetIsChecksumOK()
            if isChecksumOK:
                messageType = loraMessage.GetMessageType()
                if messageType == 1: #ack
                    messageNumber = loraMessage.GetMessageNumber()
                    return {"MessageType": "ACK", "MessageNumber": messageNumber, "ChecksumOK": True}
                else:
                    return {"MessageType": "DATA", "Data": receivedData, "ChecksumOK": True}
            else:
                return {"MessageType": "DATA", "Data": receivedData, "ChecksumOK": False}

        return None