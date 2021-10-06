import traceback
from loraradio.loraradio import LoraRadio
from loraradio.LoraRadioDRF1268DS_RS import LoraRadioDRF1268DS_RS
from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
import serial
import time
import logging
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from utils.utils import Utils


class ReceiveLoraAdapter(object):
    Instances = []
    WiRocLogger = logging.getLogger('WiRoc.Input')

    @staticmethod
    def CreateInstances(hardwareAbstraction):
        # check the number of lora radios and return an instance for each
        serialPorts = []
        if hardwareAbstraction.runningOnChip:
            serialPorts.append('/dev/ttyS2')
        elif hardwareAbstraction.runningOnNanoPi:
            serialPorts.append('/dev/ttyS1')
        else: #TODO: figure out why this else is here...
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
            self.loraRadio = LoraRadioDRF1268DS_RS.GetInstance(portName, hardwareAbstraction)
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
        codeRate = SettingsClass.GetCodeRate()
        rxGain = SettingsClass.GetRxGainEnabled()
        return self.loraRadio.GetIsInitialized(channel, loraRange, loraPower, codeRate, rxGain)

    def ShouldBeInitialized(self):
        channel = SettingsClass.GetChannel()
        loraRange= SettingsClass.GetLoraRange()
        loraPower = SettingsClass.GetLoraPower()
        codeRate = SettingsClass.GetCodeRate()
        rxGain = SettingsClass.GetRxGainEnabled()
        return not self.loraRadio.GetIsInitialized(channel, loraRange, loraPower, codeRate, rxGain)

    def Init(self):
        channel = SettingsClass.GetChannel()
        loraRange = SettingsClass.GetLoraRange()
        loraPower = SettingsClass.GetLoraPower()
        codeRate = SettingsClass.GetCodeRate()
        rxGain = SettingsClass.GetRxGainEnabled()
        if self.loraRadio.GetIsInitialized(channel, loraRange, loraPower, codeRate, rxGain):
            return True
        self.loraRadio.Init(channel, loraRange, loraPower, codeRate, rxGain)

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
                return False
        return True

    # messageData is a bytearray
    def GetData(self):
        loraMessage = None
        try:
            loraMessage = self.loraRadio.GetRadioData()
        except Exception as ex:
            ReceiveLoraAdapter.WiRocLogger.error(
                "ReceiveLoraAdapter::GetData() Error reading from lora " + traceback.format_exc())
            time.sleep(0.5)

        if loraMessage is not None:
            receivedData = loraMessage.GetByteArray()
            ackRequested = loraMessage.GetAckRequested()
            repeaterRequested = loraMessage.GetRepeater()
            # For testing purposes we can set SimulatedMessageDropPercentageRepeaterNotRequested and/or
            # SimulatedMessageDropPercentageRepeaterRequested to randomly drop a percentage of messages
            if repeaterRequested:
                simulatedMessageDropPercentageRepReq = SettingsClass.GetSimulatedMessageDropPercentageRepeaterRequested()
                if simulatedMessageDropPercentageRepReq > 0 and Utils.GetShouldDropMessage(simulatedMessageDropPercentageRepReq):
                    return None
            else:
                simulatedMessageDropPercentageRepNotReq = SettingsClass.GetSimulatedMessageDropPercentageRepeaterNotRequested()
                if simulatedMessageDropPercentageRepNotReq > 0 and Utils.GetShouldDropMessage(simulatedMessageDropPercentageRepNotReq):
                    return None
            messageType = loraMessage.GetMessageType()
            messageID = loraMessage.GetHash()
            messageIDToReturn = messageID
            if messageType == LoraRadioMessageRS.MessageTypeLoraAck:
                if repeaterRequested:
                    SettingsClass.SetHasReceivedMessageFromRepeater()
                if ((SettingsClass.GetLoraMode() == "SENDER") or (SettingsClass.GetLoraMode() == "REPEATER")):
                    messageIDToReturn = loraMessage.GetMessageIDThatIsAcked()
            elif messageType == LoraRadioMessageRS.MessageTypeStatus:
                if loraMessage.GetBatteryLow():
                    SettingsClass.SetBatteryIsLowReceived(True)

                relayPathNo = loraMessage.GetLastRelayPathNoFromStatusMessage()
                SettingsClass.UpdateRelayPathNumber(relayPathNo)
                DatabaseHelper.add_message_stat(self.GetInstanceName(), "Status", "Received", 1)
            elif messageType == LoraRadioMessageRS.MessageTypeSIPunch or messageType == LoraRadioMessageRS.MessageTypeSIPunchDouble:
                if loraMessage.GetBatteryLow():
                    SettingsClass.SetBatteryIsLowReceived(True)

                if ackRequested and \
                        ((SettingsClass.GetLoraMode() == "RECEIVER" and not repeaterRequested)
                         or (SettingsClass.GetLoraMode() == "REPEATER" and repeaterRequested)):
                    ReceiveLoraAdapter.WiRocLogger.debug(
                        "Lora message received, send ack. WiRocMode: " + SettingsClass.GetLoraMode() + " Repeater requested: " + str(
                            repeaterRequested))
                    ackMsg = LoraRadioMessageCreator.GetAckMessage(messageID)
                    if SettingsClass.GetLoraMode() == "RECEIVER":
                        ackMsg.SetAckRequested(True)  # indicate this is receiver acking
                    if SettingsClass.GetLoraMode() == "REPEATER":
                        ackMsg.SetRepeater(True)  # indicate this is repeater acking
                    try:
                        self.TrySendData(ackMsg.GetByteArray())
                    except Exception as ex2:
                        ReceiveLoraAdapter.WiRocLogger.error(
                            "ReceiveLoraAdapter::GetData() Error sending ack: " + str(ex2))
                try:
                    DatabaseHelper.add_message_stat(self.GetInstanceName(), "SIMessage", "Received", 1)
                except Exception as ex:
                    ReceiveLoraAdapter.WiRocLogger.error("ReceiveLoraAdapter::GetData() Error saving statistics: " + str(ex))
            return {"MessageType": loraMessage.GetMessageCategory(), "MessageSource": "Lora", "MessageSubTypeName": loraMessage.GetMessageSubType(),
                    "Data": receivedData, "MessageID": messageIDToReturn, "LoraRadioMessage": loraMessage, "ChecksumOK": True}
        return None

    def AddedToMessageBox(self, mbid):
        return None