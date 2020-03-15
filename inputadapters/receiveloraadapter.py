import pyudev
import traceback
from loraradio.loraradio import LoraRadio
from loraradio.loraradiodrf1268ds import LoraRadioDRF1268DS
from datamodel.datamodel import LoraRadioMessage
from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
import serial
import time
import logging
import socket

class ReceiveLoraAdapter(object):
    Instances = []
    TestRepeater = False
    WiRocLogger = logging.getLogger('WiRoc.Input')

    @staticmethod
    def CreateInstances(hardwareAbstraction):
        # check the number of lora radios and return an instance for each
        serialPorts = []
        if hardwareAbstraction.runningOnChip:
            serialPorts.append('/dev/ttyS2')
        elif hardwareAbstraction.runningOnNanoPi:
            serialPorts.append('/dev/ttyS1')
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
                    ReceiveLoraAdapter(highestInstanceNumber, serialDev, hardwareAbstraction))

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

    def __init__(self, instanceNumber, portName, hardwareAbstraction):
        self.instanceNumber = instanceNumber
        self.portName = portName
        if hardwareAbstraction.runningOnNanoPi:
            self.loraRadio = LoraRadioDRF1268DS.GetInstance(portName, hardwareAbstraction)
        else:
            self.loraRadio = LoraRadio.GetInstance(portName, hardwareAbstraction)
        self.hardwareAbstraction = hardwareAbstraction

    def GetInstanceNumber(self):
        return self.instanceNumber

    def GetInstanceName(self):
        return "reclora" + str(self.instanceNumber)

    def GetSerialDevicePath(self):
        return self.portName

    def GetIsInitialized(self):
        channel = SettingsClass.GetChannel()
        loraRange = SettingsClass.GetLoraRange()
        loraPower = SettingsClass.GetLoraPower()
        return self.loraRadio.GetIsInitialized(channel, loraRange, loraPower)

    def ShouldBeInitialized(self):
        channel = SettingsClass.GetChannel()
        loraRange= SettingsClass.GetLoraRange()
        loraPower = SettingsClass.GetLoraPower()
        return not self.loraRadio.GetIsInitialized(channel, loraRange, loraPower)

    def Init(self):
        channel = SettingsClass.GetChannel()
        loraRange = SettingsClass.GetLoraRange()
        loraPower = SettingsClass.GetLoraPower()
        if self.loraRadio.GetIsInitialized(channel, loraRange, loraPower):
            return True
        self.loraRadio.Init(channel, loraRange, loraPower)

    def UpdateInfreqently(self):
        return True

    def TrySendData(self, messageData):
        startTrySendTime = time.monotonic()
        dataSentOK = self.loraRadio.SendData(messageData)
        while not dataSentOK:
            time.sleep(0.01)
            dataSentOK = self.loraRadio.SendData(messageData)
            if time.monotonic() - startTrySendTime > (SettingsClass.GetRetryDelay(1) / 2000):
                # Wait half of a first retrydelay (GetRetryDelay returns in microseconds)
                ReceiveLoraAdapter.WiRocLogger.error("ReceiveLoraAdapter::TrySendData() Wasn't able to send ack (busy response)")
                break

    # messageData is a bytearray
    def GetData(self):
        loraMessage = None
        try:
            loraMessage = self.loraRadio.GetRadioData()
        except Exception as ex:
            ReceiveLoraAdapter.WiRocLogger.error("ReceiveLoraAdapter::GetData() Error reading from lora " + traceback.format_exc())
            time.sleep(0.5)

        if loraMessage is not None:
            receivedData = loraMessage.GetByteArray()
            isChecksumOK = loraMessage.GetIsChecksumOK()
            if isChecksumOK:
                ackRequested = loraMessage.GetAcknowledgementRequested()
                repeaterRequested = loraMessage.GetRepeaterBit()
                messageType = loraMessage.GetMessageType()
                if messageType == LoraRadioMessage.MessageTypeLoraAck:
                    if repeaterRequested:
                        SettingsClass.SetHasReceivedMessageFromRepeater()
                    if ((SettingsClass.GetWiRocMode() == "SENDER") or (SettingsClass.GetWiRocMode() == "REPEATER")):
                        messageID =  loraMessage.GetMessageIDThatIsAcked()
                        return {"MessageType": "ACK", "MessageSource":"Lora", "MessageSubTypeName": "Ack", "MessageID": messageID, "ChecksumOK": True, "LoraRadioMessage": loraMessage}
                elif messageType == LoraRadioMessage.MessageTypeStatus:
                    if ReceiveLoraAdapter.TestRepeater and \
                            SettingsClass.GetWiRocMode() == "RECEIVER" and \
                            repeaterRequested:
                        return None

                    if loraMessage.GetBatteryLowBit():
                        SettingsClass.SetBatteryIsLowReceived(True)

                    if ackRequested and \
                            ((SettingsClass.GetWiRocMode() == "RECEIVER" and not repeaterRequested)
                            or (SettingsClass.GetWiRocMode() == "REPEATER" and repeaterRequested)):
                            ReceiveLoraAdapter.WiRocLogger.debug("Lora status message received, send ack. WiRocMode: " + SettingsClass.GetWiRocMode() + " Repeater requested: " + str(repeaterRequested))
                            messageType = LoraRadioMessage.MessageTypeLoraAck
                            loraMessage2 = LoraRadioMessage(0, messageType, False, False)
                            if SettingsClass.GetWiRocMode() == "RECEIVER":
                                loraMessage2.SetAcknowledgementRequested(True) # indicate this is receiver acking
                            if SettingsClass.GetWiRocMode() == "REPEATER":
                                loraMessage2.SetRepeaterBit(True)  # indicate this is repeater acking
                            loraMessage2.SetMessageIDToAck(loraMessage.GetMessageID())
                            loraMessage2.UpdateChecksum()
                            self.TrySendData(loraMessage2.GetByteArray())
                    relayPathNo = loraMessage.GetLastRelayPathNoFromStatusMessage()
                    SettingsClass.UpdateRelayPathNumber(relayPathNo)
                    DatabaseHelper.add_message_stat(self.GetInstanceName(), "Status", "Received", 1)
                    return {"MessageType": "DATA", "MessageSource":"Lora", "MessageSubTypeName": "Status", "Data": receivedData, "MessageID": loraMessage.GetMessageID(), "LoraRadioMessage": loraMessage, "ChecksumOK": True}
                else:
                    if ReceiveLoraAdapter.TestRepeater and \
                            SettingsClass.GetWiRocMode() == "RECEIVER" and \
                            repeaterRequested:
                        return None

                    if loraMessage.GetBatteryLowBit():
                        SettingsClass.SetBatteryIsLowReceived(True)

                    messageID = loraMessage.GetMessageID()
                    if ackRequested and \
                            ((SettingsClass.GetWiRocMode() == "RECEIVER" and not repeaterRequested)
                             or (SettingsClass.GetWiRocMode() == "REPEATER" and repeaterRequested)):
                            ReceiveLoraAdapter.WiRocLogger.debug("Lora message received, send ack. WiRocMode: " + SettingsClass.GetWiRocMode() + " Repeater requested: " + str(repeaterRequested))
                            messageType = LoraRadioMessage.MessageTypeLoraAck
                            loraMessage2 = LoraRadioMessage(5, messageType, False, False)
                            if SettingsClass.GetWiRocMode() == "RECEIVER":
                                loraMessage2.SetAcknowledgementRequested(True) # indicate this is receiver acking
                            if SettingsClass.GetWiRocMode() == "REPEATER":
                                loraMessage2.SetRepeaterBit(True)  # indicate this is repeater acking
                            loraMessage2.SetMessageIDToAck(messageID)
                            loraMessage2.UpdateChecksum()
                            try:
                                self.TrySendData(loraMessage2.GetByteArray())
                            except Exception as ex2:
                                ReceiveLoraAdapter.WiRocLogger.error("ReceiveLoraAdapter::GetData() Error sending ack: " + str(ex2))
                    try:
                        DatabaseHelper.add_message_stat(self.GetInstanceName(), "SIMessage", "Received", 1)
                    except Exception as ex:
                        ReceiveLoraAdapter.WiRocLogger.error("ReceiveLoraAdapter::GetData() Error saving statistics: " + str(ex))
                    return {"MessageType": "DATA", "MessageSource":"Lora", "MessageSubTypeName": "SIMessage", "Data": receivedData, "MessageID": messageID, "LoraRadioMessage": loraMessage, "ChecksumOK": True}
            else:
                messageType = loraMessage.GetMessageType()
                if messageType == LoraRadioMessage.MessageTypeLoraAck:
                    messageID = loraMessage.GetMessageIDThatIsAcked()
                    return {"MessageType": "ACK", "MessageSource": "Lora", "MessageSubTypeName":"Ack", "Data": receivedData, "MessageID":messageID, "ChecksumOK": False, "LoraRadioMessage": loraMessage}
                else:
                    return {"MessageType": "DATA", "MessageSource":"Lora", "MessageSubTypeName":"Unknown", "Data": receivedData, "MessageID":None, "ChecksumOK": False}

        return None

    def AddedToMessageBox(self, mbid):
        return None