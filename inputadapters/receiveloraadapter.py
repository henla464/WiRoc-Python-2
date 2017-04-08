import pyudev
import traceback
from loraradio.loraradio import LoraRadio
from settings.settings import SettingsClass
import serial
import time
import logging
import socket

class ReceiveLoraAdapter(object):
    Instances = []

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
            # https://github.com/dhylands/usb-ser-mon/blob/master/find_port.py
            #uDevContext = pyudev.Context()
            #for device in uDevContext.list_devices(subsystem='tty'):
            #    if 'ID_VENDOR_ID' in device:
            #        logging.debug('ReceiveLoraAdapter vendor: ' + device['ID_VENDOR_ID'].lower() + " model: " + device['ID_MODEL_ID'].lower())
            #        if device['ID_VENDOR_ID'].lower() == '10c4' and \
            #                    device['ID_MODEL_ID'].lower() == 'ea60':
            #            serialPorts.append(device.device_node)

        newInstancesFoundOrRemoved = False
        highestInstanceNumber = 0
        newInstances = []
        for serialDev in serialPorts:
            alreadyCreated = False
            for instance in ReceiveLoraAdapter.Instances:
                if instance.GetSerialDevicePath() == serialDev:
                    alreadyCreated = True
                    newInstances.append(instance)
                    if instance.GetInstanceNumber() > highestInstanceNumber:
                        highestInstanceNumber = instance.GetInstanceNumber()

            if not alreadyCreated:
                newInstancesFoundOrRemoved = True
                highestInstanceNumber = highestInstanceNumber + 1
                newInstances.append(
                    ReceiveLoraAdapter(highestInstanceNumber, serialDev))

        if len(newInstances) != ReceiveLoraAdapter.Instances:
            newInstancesFoundOrRemoved = True

        if newInstancesFoundOrRemoved:
            ReceiveLoraAdapter.Instances = newInstances
            return True
        else:
            return False


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

    def UpdateInfreqently(self):
        return True

    # messageData is a bytearray
    def GetData(self):
        loraMessage = None
        try:
            loraMessage = self.loraRadio.GetRadioData()
        except Exception as ex:
            logging.error("ReceiveLoraAdapter::GetData() Error reading from lora " + traceback.format_exc())
            time.sleep(0.5)

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