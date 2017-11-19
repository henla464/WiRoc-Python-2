import pyudev
import traceback
from loraradio.loraradio import LoraRadio
from datamodel.datamodel import LoraRadioMessage
from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
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

        if len(newInstances) != len(ReceiveLoraAdapter.Instances):
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

    def ShouldBeInitialized(self):
        channel = SettingsClass.GetChannel()
        loraDataRate = SettingsClass.GetDataRate()
        return not self.loraRadio.GetIsInitialized(channel, loraDataRate)

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
                ackRequested = loraMessage.GetAcknowledgementRequested()
                repeaterRequested = loraMessage.GetRepeaterBit()
                if repeaterRequested:
                    SettingsClass.SetHasReceivedMessageFromRepeater()
                messageType = loraMessage.GetMessageType()
                if messageType == LoraRadioMessage.MessageTypeLoraAck:
                    if ((SettingsClass.GetWiRocMode() == "SENDER") or (SettingsClass.GetWiRocMode() == "REPEATER")):
                        messageID =  loraMessage.GetMessageIDThatIsAcked()
                        return {"MessageType": "ACK", "MessageSource":"Lora", "MessageSubTypeName": "Ack", "MessageID": messageID, "ChecksumOK": True, "LoraRadioMessage": loraMessage}
                elif messageType == LoraRadioMessage.MessageTypeStatus:
                    if ackRequested and \
                            ((SettingsClass.GetWiRocMode() == "RECEIVER" and not repeaterRequested)
                            or (SettingsClass.GetWiRocMode() == "REPEATER" and repeaterRequested)):
                            logging.debug("Lora status message received, send ack. WiRocMode: " + SettingsClass.GetWiRocMode() + " Repeater requested: " + str(repeaterRequested))
                            messageType = LoraRadioMessage.MessageTypeLoraAck
                            loraMessage2 = LoraRadioMessage(0, messageType, False, False)
                            loraMessage2.SetMessageIDToAck(loraMessage.GetMessageID())
                            loraMessage2.UpdateChecksum()
                            self.loraRadio.SendData(loraMessage2.GetByteArray())
                    relayPathNo = loraMessage.GetLastRelayPathNoFromStatusMessage()
                    SettingsClass.UpdateRelayPathNumber(relayPathNo)
                    DatabaseHelper.add_message_stat(self.GetInstanceName(), "Status", "Received", 1)
                    return {"MessageType": "DATA", "MessageSource":"Lora", "MessageSubTypeName": "Status", "Data": receivedData, "MessageID": loraMessage.GetMessageID(), "LoraRadioMessage": loraMessage, "ChecksumOK": True}
                else:
                    messageID = loraMessage.GetMessageID()
                    if ackRequested and \
                            ((SettingsClass.GetWiRocMode() == "RECEIVER" and not repeaterRequested)
                             or (SettingsClass.GetWiRocMode() == "REPEATER" and repeaterRequested)):
                            logging.debug("Lora message received, send ack. WiRocMode: " + SettingsClass.GetWiRocMode() + " Repeater requested: " + str(repeaterRequested))
                            messageType = LoraRadioMessage.MessageTypeLoraAck
                            loraMessage2 = LoraRadioMessage(5, messageType, False, False)
                            loraMessage2.SetAcknowledgementRequested(True) # indicate this is receiver acking
                            loraMessage2.SetMessageIDToAck(messageID)
                            loraMessage2.UpdateChecksum()
                            self.loraRadio.SendData(loraMessage2.GetByteArray())
                    DatabaseHelper.add_message_stat(self.GetInstanceName(), "SIMessage", "Received", 1)
                    return {"MessageType": "DATA", "MessageSource":"Lora", "MessageSubTypeName": "SIMessage", "Data": receivedData, "MessageID": messageID, "LoraRadioMessage": loraMessage, "ChecksumOK": True}
            else:
                return {"MessageType": "DATA", "MessageSource":"Lora", "MessageSubTypeName":"Unknown", "Data": receivedData, "MessageID":None, "ChecksumOK": False}

        return None

    def AddedToMessageBox(self, mbid):
        return None