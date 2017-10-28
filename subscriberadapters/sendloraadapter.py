from loraradio.loraradio import LoraRadio
from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
#import pyudev
import serial
import logging
import socket
import collections
from datetime import datetime, timedelta
from datamodel.datamodel import LoraRadioMessage

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
            shouldSubscriptionBeEnabled = SendLoraAdapter.Instances[0].GetIsInitialized()
            for name, transf in SendLoraAdapter.Instances[0].transforms.items():
                if (SendLoraAdapter.SubscriptionsEnabled != shouldSubscriptionBeEnabled or
                            transf.GetDeleteAfterSentChanged()):
                    deleteAfterSent = transf.GetDeleteAfterSent()
                    logging.info("SendLoraAdapter::EnableDisableSubscription() subscription set enabled: " + str(
                        shouldSubscriptionBeEnabled))
                    DatabaseHelper.update_subscription(shouldSubscriptionBeEnabled, deleteAfterSent,
                                                        SendLoraAdapter.GetTypeName(), name)
            SendLoraAdapter.SubscriptionsEnabled = shouldSubscriptionBeEnabled

    @staticmethod
    def EnableDisableTransforms():
        if len(SendLoraAdapter.Instances) > 0:
            if SendLoraAdapter.WiRocMode is None or SendLoraAdapter.WiRocMode != SettingsClass.GetWiRocMode():
                SendLoraAdapter.WiRocMode = SettingsClass.GetWiRocMode()
                enableSendTransforms = (SendLoraAdapter.WiRocMode == "SENDER" or SendLoraAdapter.WiRocMode == "REPEATER")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "SISIMessageToLoraTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "SITestTestToLoraTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "StatusStatusToLoraTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "SILoraRadioMessageToLoraTransform")
                DatabaseHelper.set_transform_enabled(not enableSendTransforms, "LoraSIMessageToLoraAckTransform")
                DatabaseHelper.set_transform_enabled(not enableSendTransforms, "LoraStatusToLoraAckTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "RepeaterSIMessageToLoraAckTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "RepeaterSIMessageToLoraTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "RepeaterStatusToLoraAckTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "RepeaterStatusToLoraTransform")

    def __init__(self, instanceNumber, portName):
        self.instanceNumber = instanceNumber
        self.portName = portName
        self.loraRadio = LoraRadio.GetInstance(portName)
        self.transforms = {}
        self.isDBInitialized = False
        self.lastMessageRepeaterBit = False
        self.sentQueueWithoutRepeaterBit = collections.deque()
        self.sentQueueWithRepeaterBit = collections.deque()
        self.successWithoutRepeaterBitQueue = collections.deque()
        self.successWithRepeaterBitQueue = collections.deque()
        # add one entry to each statistics queue so that we have initial values
        self.AddSentWithoutRepeaterBit()
        self.AddSentWithRepeaterBit()
        self.AddSuccessWithoutRepeaterBit()
        self.AddSuccessWithRepeaterBit()

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
        transforms.append("SISIMessageToLoraTransform")
        transforms.append("SITestTestToLoraTransform")
        transforms.append("StatusStatusToLoraTransform")
        transforms.append("SILoraRadioMessageToLoraTransform") # status message received through serial wiroc-wiroc
        transforms.append("RepeaterSIMessageToLoraAckTransform")
        transforms.append("RepeaterSIMessageToLoraTransform")
        transforms.append("RepeaterStatusToLoraAckTransform")
        transforms.append("RepeaterStatusToLoraTransform")
        transforms.append("LoraSIMessageToLoraAckTransform")
        transforms.append("LoraStatusToLoraAckTransform")
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

    def GetDelayAfterMessageSent(self):
        wMode = SettingsClass.GetWiRocMode()
        noOfBytesToDelay = 25
        if SettingsClass.GetAcknowledgementRequested():
            noOfBytesToDelay += 10  # one message 23 + one ack 10 + 2 bytes extra
        #if wMode == "SENDER":
        #    if self.GetShouldRequestRepeater() and \
        #        SettingsClass.GetHasReceivedMessageFromRepeater():
        #        noOfBytesToDelay += 10 # wait also for repeaters ack
                # (if repeater ack is received then the time will extended again)
        timeS = SettingsClass.GetLoraMessageTimeSendingTimeS(noOfBytesToDelay)
        return timeS

    def AddSuccessWithoutRepeaterBit(self):
        self.successWithoutRepeaterBitQueue.appendleft(datetime.now())
        if len(self.successWithoutRepeaterBitQueue) > 20:
            self.successWithoutRepeaterBitQueue.pop()

    def AddSuccessWithRepeaterBit(self):
        # we received and ack from the repeater, only
        # count it as success if we requested it
        if self.lastMessageRepeaterBit:
            self.successWithRepeaterBitQueue.appendleft(datetime.now())
            if len(self.successWithRepeaterBitQueue) > 20:
                self.successWithRepeaterBitQueue.pop()

    def AddSentWithoutRepeaterBit(self):
        self.lastMessageRepeaterBit = False
        self.sentQueueWithoutRepeaterBit.appendleft(datetime.now())
        if len(self.sentQueueWithoutRepeaterBit) > 20:
            self.sentQueueWithoutRepeaterBit.pop()

    def AddSentWithRepeaterBit(self):
        self.lastMessageRepeaterBit = True
        self.sentQueueWithRepeaterBit.appendleft(datetime.now())
        if len(self.sentQueueWithRepeaterBit) > 20:
            self.sentQueueWithRepeaterBit.pop()

    def GetSuccessRateToDestination(self):
        dateTimeToUse = max(min(self.successWithoutRepeaterBitQueue[-1], self.sentQueueWithoutRepeaterBit[-1]), datetime.now() - timedelta(minutes=30))
        successCount = sum(1 for successDate in self.successWithoutRepeaterBitQueue if successDate >= dateTimeToUse)
        sentCount = sum(1 for sentDate in self.sentQueueWithoutRepeaterBit if sentDate >= dateTimeToUse)
        if sentCount == 0:
            return 100
        return int((successCount / sentCount)*100)

    def GetSuccessRateToRepeater(self):
        dateTimeToUse = max(min(self.successWithRepeaterBitQueue[-1], self.sentQueueWithRepeaterBit[-1]),
                            datetime.now() - timedelta(minutes=30))
        successCount = sum(1 for successDate in self.successWithRepeaterBitQueue if successDate >= dateTimeToUse)
        sentCount = sum(1 for sentDate in self.sentQueueWithRepeaterBit if sentDate >= dateTimeToUse)
        if sentCount == 0:
            return 100
        return int((successCount / sentCount) * 100)

    def GetShouldRequestRepeater(self):
        reqRepeater = False
        successDestination = self.GetSuccessRateToDestination()
        successRepeater = self.GetSuccessRateToRepeater()
        if SettingsClass.GetHasReceivedMessageFromRepeater() and \
                        successDestination < 85 \
                and successRepeater > successDestination:
            reqRepeater = True
        logging.debug("Request repeater: " + str(reqRepeater) + " success destination: " + str(successDestination) + " success repeater: " + str(successRepeater))
        return reqRepeater

    # messageData is a bytearray
    def SendData(self, messageData):
        msg = LoraRadioMessage()
        msg.AddPayload(messageData)
        SettingsClass.SetTimeOfLastMessageSentToLora()
        if SendLoraAdapter.WiRocMode == "SENDER" and msg.GetRepeaterBit():
            self.AddSentWithRepeaterBit()
        else:
            self.AddSentWithoutRepeaterBit()
        return self.loraRadio.SendData(messageData)
