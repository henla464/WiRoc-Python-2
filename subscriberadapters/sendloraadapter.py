import os
import threading

from chipGPIO.hardwareAbstraction import HardwareAbstraction
from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
from loraradio.LoraRadioDRF1268DS_RS import LoraRadioDRF1268DS_RS, ReturnStatus
from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
import serial
import logging
import socket
import collections
from datetime import datetime, timedelta


class SendLoraAdapter(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')
    Instances = []
    WiRocMode = None
    SubscriptionsEnabled = None
    AdapterInitialized = None

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction):
        # check the number of lora radios and return an instance for each
        serialPorts = ['/dev/ttyS1']

        if len(serialPorts) > 0:
            if len(SendLoraAdapter.Instances) > 0:
                if SendLoraAdapter.Instances[0].GetSerialDevicePath() != serialPorts[0]:
                    SendLoraAdapter.Instances[0] = SendLoraAdapter(1, serialPorts[0], hardwareAbstraction)
                    return True
                elif SendLoraAdapter.WiRocMode is None or SendLoraAdapter.WiRocMode != SettingsClass.GetLoraMode():
                    return True
            else:
                SendLoraAdapter.Instances.append(SendLoraAdapter(1, serialPorts[0], hardwareAbstraction))
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
            shouldSubscriptionBeEnabled = SendLoraAdapter.Instances[0].GetIsInitialized() and SendLoraAdapter.Instances[
                0].GetIsEnabled()
            for name, transf in SendLoraAdapter.Instances[0].transforms.items():
                if (SendLoraAdapter.SubscriptionsEnabled != shouldSubscriptionBeEnabled or
                        transf.GetDeleteAfterSentChanged()):
                    deleteAfterSent = transf.GetDeleteAfterSent()
                    SendLoraAdapter.WiRocLogger.info(
                        "SendLoraAdapter::EnableDisableSubscription() subscription set enabled: " + str(
                            shouldSubscriptionBeEnabled))
                    DatabaseHelper.update_subscription(shouldSubscriptionBeEnabled, deleteAfterSent,
                                                       SendLoraAdapter.GetTypeName(), name)
            SendLoraAdapter.SubscriptionsEnabled = shouldSubscriptionBeEnabled

    @staticmethod
    def EnableDisableTransforms():
        if len(SendLoraAdapter.Instances) > 0:
            if SendLoraAdapter.WiRocMode is None or SendLoraAdapter.WiRocMode != SettingsClass.GetLoraMode():
                SendLoraAdapter.WiRocMode = SettingsClass.GetLoraMode()
                enableSendTransforms = (
                            SendLoraAdapter.WiRocMode == "SENDER" or SendLoraAdapter.WiRocMode == "REPEATER")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "SISIMessageToLoraTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "SRRSRRMessageToLoraTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "SITestTestToLoraTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "StatusStatusToLoraTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "HAMCSHamcsToLoraTransform")
                # For receiver: Sends schedules an ack for message received from sender when sender requested repeater
                # (we don't send ack directly because repeater is expected to reply with ack directly)
                DatabaseHelper.set_transform_enabled(not enableSendTransforms, "LoraSIMessageToLoraAckTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "RepeaterSIMessageToLoraAckTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "RepeaterSIMessageToLoraTransform")
                DatabaseHelper.set_transform_enabled(enableSendTransforms, "RepeaterStatusToLoraTransform")

    def __init__(self, instanceNumber, portName, hardwareAbstraction):
        self.instanceNumber = instanceNumber
        self.portName = portName
        self.loraRadio = LoraRadioDRF1268DS_RS.GetInstance(portName, hardwareAbstraction)
        self.transforms = {}
        self.isDBInitialized = False
        self.lastMessageRepeaterBit = False
        self.blockSendingFromThisDate = None
        self.blockSendingForSeconds = None
        self.blockSendingReason: str = ""
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
    def GetTransformNames(self) -> list[str]:
        transforms = ["SISIMessageToLoraTransform", "SRRSRRMessageToLoraTransform", "SITestTestToLoraTransform",
                      "StatusStatusToLoraTransform", "RepeaterSIMessageToLoraAckTransform",
                      "RepeaterSIMessageDoubleToLoraAckTransform", "RepeaterSIMessageToLoraTransform",
                      "RepeaterSIMessageDoubleToLoraTransform", "RepeaterStatusToLoraTransform",
                      "LoraSIMessageToLoraAckTransform", "HAMCSHamcsToLoraTransform"]
        return transforms

    def SetTransform(self, transformClass):
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName):
        return self.transforms[transformName]

    def GetIsEnabled(self) -> bool:
        return self.loraRadio.GetIsEnabled()

    def GetIsInitialized(self):
        enabled: bool = SettingsClass.GetLoraEnabled()
        channel = SettingsClass.GetChannel()
        loraRange = SettingsClass.GetLoraRange()
        loraPower = SettingsClass.GetLoraPower()
        codeRate = SettingsClass.GetCodeRate()
        rxGain = SettingsClass.GetRxGainEnabled()
        return self.loraRadio.GetIsInitialized(channel, loraRange, loraPower, codeRate, rxGain, enabled)

    def ShouldBeInitialized(self):
        enabled: bool = SettingsClass.GetLoraEnabled()
        channel = SettingsClass.GetChannel()
        loraRange = SettingsClass.GetLoraRange()
        loraPower = SettingsClass.GetLoraPower()
        codeRate = SettingsClass.GetCodeRate()
        rxGain = SettingsClass.GetRxGainEnabled()
        loraRadioInitialized = self.loraRadio.GetIsInitialized(channel, loraRange, loraPower, codeRate, rxGain, enabled)
        SendLoraAdapter.WiRocLogger.debug(f"SendLoraAdapter::ShouldBeInitialized() loraRadioInitialized {loraRadioInitialized}")
        SendLoraAdapter.WiRocLogger.debug(
            f"SendLoraAdapter::ShouldBeInitialized() loraRadioInitialized SendLoraAdapter.Instances[0].AdapterInitialized {SendLoraAdapter.Instances[0].AdapterInitialized}")
        # initialize if loraRadio isn't initialized yet, or if the loraradio initialization status changed
        return not loraRadioInitialized or SendLoraAdapter.Instances[0].AdapterInitialized != loraRadioInitialized

    # has adapter, transforms, subscriptions etc been added to database?
    def GetIsDBInitialized(self):
        return self.isDBInitialized

    def SetIsDBInitialized(self, val=True):
        self.isDBInitialized = val

    def Init(self):
        enabled: bool = SettingsClass.GetLoraEnabled()
        channel = SettingsClass.GetChannel()
        loraRange = SettingsClass.GetLoraRange()
        loraPower = SettingsClass.GetLoraPower()
        codeRate = SettingsClass.GetCodeRate()
        rxGain = SettingsClass.GetRxGainEnabled()
        # set the AdapterInitialized to same value as loraRadios initialized
        # if loraRadio changes initialize value later we can detect this.
        if self.loraRadio.GetIsInitialized(channel, loraRange, loraPower, codeRate, rxGain, enabled):
            SendLoraAdapter.Instances[0].AdapterInitialized = True
            return True
        loraInitialized = self.loraRadio.Init(channel, loraRange, loraPower, codeRate, rxGain, enabled)
        SendLoraAdapter.Instances[0].AdapterInitialized = loraInitialized
        return loraInitialized

    def BlockAfterReceivingAck(self):
        if self.loraRadio.GetAckReceivedMatchingLastSentMessage():
            self.blockSendingForSeconds = SettingsClass.GetNoOfSecondsToWaitToGiveOtherWiRocChanceToSendAfterReceiveingAck()
            self.blockSendingFromThisDate = datetime.now()
            self.blockSendingReason = "givingotherwirocchancetosend"
            SendLoraAdapter.WiRocLogger.debug("SendLoraAdapter::BlockAfterReceivingAck give other chance")
        else:
            # Last ack received likely was an ack to another WiRoc device. If we are blocking
            # because lora module returned "busy" then now the air should be free so unblock early.
            self.RemoveBlockSendingDueToBusy()
            SendLoraAdapter.WiRocLogger.debug("SendLoraAdapter::BlockAfterReceivingAck lets go")

    def BlockSendingToLetRepeaterSendAndReceiveAck(self):
        timeS = LoraRadioMessageRS.GetLoraMessageTimeSendingTimeSByMessageType(
            LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS) + \
                LoraRadioMessageRS.GetLoraMessageTimeSendingTimeSByMessageType(
                    LoraRadioMessageRS.MessageTypeLoraAck) + 0.35
        self.blockSendingForSeconds = timeS
        self.blockSendingFromThisDate = datetime.now()
        self.blockSendingReason = "waitforrepeater"

    def BlockSendingUntilMessageSentAndAckReceived(self, delayInS):
        self.blockSendingForSeconds = delayInS
        self.blockSendingFromThisDate = datetime.now()
        self.blockSendingReason = "untilsentandack"

    def BlockSendingDueToBusy(self, delayInS: int | None):
        if delayInS is None:
            # wait time should be chosen so that there is high chance to squeeze in between two messages from
            # another WiRoc unit. But high enough that the risk to squeeze between another message and its ack is low
            # The time in BlockAfterReceivingAck is also important.
            self.blockSendingForSeconds = 0.2
        else:
            self.blockSendingForSeconds = delayInS
        self.blockSendingFromThisDate = datetime.now()
        self.blockSendingReason = "busy"

    def RemoveBlockSendingDueToBusy(self):
        if self.blockSendingReason == "busy":
            SendLoraAdapter.WiRocLogger.debug("SendLoraAdapter::RemoveBlockSendingDueToBusy() unblocking busy")
            self.blockSendingForSeconds = None
            self.blockSendingFromThisDate = None
            self.blockSendingReason = ""

    def IsReadyToSend(self):
        now = datetime.now()
        if self.blockSendingFromThisDate is None or self.blockSendingForSeconds is None or \
                (self.blockSendingFromThisDate + timedelta(seconds=self.blockSendingForSeconds)) < now:
            isReadyToSend = self.loraRadio.IsReadyToSend()
            if not isReadyToSend:
                # The radio is sending or receiveing. It could be another WiRoc sending its message.
                # If this WiRoc tries to send every few ms then there is a chance that we start sending
                # directly after the other WiRoc finished sending, but before the reciever had time to reply.
                # To lower the chance of this we should block sending for a bit.
                self.BlockSendingDueToBusy(None)
                SendLoraAdapter.WiRocLogger.debug(
                    "SendLoraAdapter::IsReadyToSend() blocking due to radio not ready to send, wait until: "
                    + ("None" if self.blockSendingFromThisDate is None
                       else str(self.blockSendingFromThisDate + timedelta(seconds=self.blockSendingForSeconds))))
                return False
            else:
                SendLoraAdapter.WiRocLogger.debug("SendLoraAdapter::IsReadyToSend() True")
                return True
        if self.blockSendingFromThisDate > now:
            # computer time must have changed, so reset blockSendingFromThisDate
            self.blockSendingFromThisDate = None

        SendLoraAdapter.WiRocLogger.debug("SendLoraAdapter::IsReadyToSend() blocked from sending until: "
                                          + ("None" if self.blockSendingFromThisDate is None
                                             else str(self.blockSendingFromThisDate + timedelta(
            seconds=self.blockSendingForSeconds)) + " " + self.blockSendingReason))
        return False

    @staticmethod
    def GetDelayAfterMessageSent():
        timeS = LoraRadioMessageRS.GetLoraMessageTimeSendingTimeSByMessageType(
            LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS) + 0.05  # message + one loop
        if SettingsClass.GetAcknowledgementRequested():
            timeS += LoraRadioMessageRS.GetLoraMessageTimeSendingTimeSByMessageType(
                LoraRadioMessageRS.MessageTypeLoraAck) + 0.15  # reply ack + 3 loop
        return timeS

    def GetRetryDelay(self, tryNo):
        return SettingsClass.GetRetryDelay(tryNo)

    def AddSuccessWithoutRepeaterBit(self):
        self.successWithoutRepeaterBitQueue.appendleft(datetime.now())
        if len(self.successWithoutRepeaterBitQueue) > 20:
            self.successWithoutRepeaterBitQueue.pop()
        SendLoraAdapter.WiRocLogger.debug(
            "SendLoraAdapter::AddSuccessWithoutRepeaterBit() Add success without repeater bit, queue length: " + str(
                len(self.successWithoutRepeaterBitQueue)))

    def AddSuccessWithRepeaterBit(self):
        # we received and ack from the repeater, only
        # count it as success if we requested it
        if self.lastMessageRepeaterBit:
            self.successWithRepeaterBitQueue.appendleft(datetime.now())
            if len(self.successWithRepeaterBitQueue) > 20:
                self.successWithRepeaterBitQueue.pop()
            SendLoraAdapter.WiRocLogger.debug(
                "SendLoraAdapter::AddSuccessWithRepeaterBit() Add success with repeater bit, queue length: " + str(
                    len(self.successWithRepeaterBitQueue)))

    def AddSentWithoutRepeaterBit(self):
        self.lastMessageRepeaterBit = False
        self.sentQueueWithoutRepeaterBit.appendleft(datetime.now())
        if len(self.sentQueueWithoutRepeaterBit) > 20:
            self.sentQueueWithoutRepeaterBit.pop()
        SendLoraAdapter.WiRocLogger.debug(
            "SendLoraAdapter::AddSentWithoutRepeaterBit() Add sent without repeater bit, queue length: " + str(
                len(self.sentQueueWithoutRepeaterBit)))

    def AddSentWithRepeaterBit(self):
        self.lastMessageRepeaterBit = True
        self.sentQueueWithRepeaterBit.appendleft(datetime.now())
        if len(self.sentQueueWithRepeaterBit) > 20:
            self.sentQueueWithRepeaterBit.pop()
        SendLoraAdapter.WiRocLogger.debug(
            "SendLoraAdapter::AddSentWithRepeaterBit() Add sent with repeater bit, queue length: " + str(
                len(self.sentQueueWithRepeaterBit)))

    def GetSuccessRateToDestination(self):
        #dateTimeToUse = max(min(self.successWithoutRepeaterBitQueue[-1], self.sentQueueWithoutRepeaterBit[-1]), datetime.now() - timedelta(minutes=30))
        dateTimeToUse = max(self.sentQueueWithoutRepeaterBit[-1], datetime.now() - timedelta(minutes=30))
        successCount = sum(1 for successDate in self.successWithoutRepeaterBitQueue if successDate >= dateTimeToUse)
        sentCount = sum(1 for sentDate in self.sentQueueWithoutRepeaterBit if sentDate >= dateTimeToUse)
        SendLoraAdapter.WiRocLogger.debug(
            "SendLoraAdapter::GetSuccessRateToDestination() successCount: " + str(successCount) + " sentCount: " + str(
                sentCount))
        if sentCount == 0:
            return 100
        return int((successCount / sentCount) * 100)

    def GetSuccessRateToRepeater(self):
        #dateTimeToUse = max(min(self.successWithRepeaterBitQueue[-1], self.sentQueueWithRepeaterBit[-1]),
        #                    datetime.now() - timedelta(minutes=30))
        dateTimeToUse = max(self.sentQueueWithRepeaterBit[-1], datetime.now() - timedelta(minutes=30))

        successCount = sum(1 for successDate in self.successWithRepeaterBitQueue if successDate >= dateTimeToUse)
        sentCount = sum(1 for sentDate in self.sentQueueWithRepeaterBit if sentDate >= dateTimeToUse)
        SendLoraAdapter.WiRocLogger.debug(
            "SendLoraAdapter::GetSuccessRateToRepeater() successCount: " + str(successCount) + " sentCount: " + str(
                sentCount))
        if sentCount == 0:
            return 100
        return int((successCount / sentCount) * 100)

    def GetShouldRequestRepeater(self):
        if SettingsClass.GetShouldAlwaysRequestRepeater():
            return True
        reqRepeater = False
        if SendLoraAdapter.WiRocMode == "SENDER":
            successDestination = self.GetSuccessRateToDestination()
            successRepeater = self.GetSuccessRateToRepeater()
            if SettingsClass.GetHasReceivedMessageFromRepeater() and \
                    successDestination < 85 \
                    and successRepeater > successDestination:
                reqRepeater = True
            SendLoraAdapter.WiRocLogger.debug("Request repeater: " + str(reqRepeater) + " success destination: " + str(
                successDestination) + " success repeater: " + str(successRepeater))
            return reqRepeater
        else:
            SendLoraAdapter.WiRocLogger.debug("Request repeater: " + str(reqRepeater))
            return reqRepeater

    # messageData is a tuple of bytearrays
    def SendData(self, messageData, successCB, failureCB, notSentCB, settingsDictionary):
        statMessageType = ""
        loraSendStatus = ReturnStatus.SENT
        for data in messageData:
            headerMessageType = LoraRadioDataHandler.GetHeaderMessageType(data)

            if headerMessageType != LoraRadioMessageRS.MessageTypeLoraAck:
                SettingsClass.SetTimeOfLastMessageSentToLora()

            if headerMessageType == LoraRadioMessageRS.MessageTypeLoraAck:
                statMessageType = "Ack"

            if headerMessageType == LoraRadioMessageRS.MessageTypeSIPunchReDCoS or \
                    headerMessageType == LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS:
                SettingsClass.SetTimeOfLastPunchMessageSentToLora()
                statMessageType = "Punch"
                SettingsClass.SetMessageIDOfLastLoraMessageSent(settingsDictionary["MessageID"])

            if headerMessageType == LoraRadioMessageRS.MessageTypeStatus:
                statMessageType = "Status"

            delayS = settingsDictionary["DelayAfterMessageSent"]
            self.BlockSendingUntilMessageSentAndAckReceived(delayS)
            status = self.loraRadio.SendData(data)
            if status == ReturnStatus.SENT:
                repeater = LoraRadioDataHandler.GetRepeater(data)
                if SendLoraAdapter.WiRocMode == "SENDER" and repeater:
                    self.AddSentWithRepeaterBit()
                else:
                    self.AddSentWithoutRepeaterBit()
            elif status == ReturnStatus.BUSY:
                # failed to send now, probably because 'busy' was returned, ie. something else was sending on same frequency. Delay a short bit.
                self.BlockSendingDueToBusy(None)
                if loraSendStatus == ReturnStatus.SENT:
                    loraSendStatus = ReturnStatus.BUSY
            elif status == ReturnStatus.NOREPLY:
                self.BlockSendingDueToBusy(None)
                if loraSendStatus == ReturnStatus.SENT:
                    loraSendStatus = ReturnStatus.NOREPLY
            elif status == ReturnStatus.OTHER:
                self.BlockSendingDueToBusy(None)
                if loraSendStatus == ReturnStatus.SENT:
                    loraSendStatus = ReturnStatus.OTHER

        if loraSendStatus == ReturnStatus.SENT:
            SendLoraAdapter.WiRocLogger.debug(
                f"SendLoraAdapter::SendData() before add message stat {os.getpid()} {threading.get_ident()}")
            DatabaseHelper.add_message_stat(self.GetInstanceName(), statMessageType, "Sent", 1)
            SendLoraAdapter.WiRocLogger.debug(
                f"SendLoraAdapter::SendData() after add message stat {os.getpid()} {threading.get_ident()}")
            successCB()
        elif loraSendStatus == ReturnStatus.BUSY:
            DatabaseHelper.add_message_stat(self.GetInstanceName(), statMessageType, "NotSent", 0)
            notSentCB()
        elif loraSendStatus == ReturnStatus.NOREPLY:
            DatabaseHelper.add_message_stat(self.GetInstanceName(), statMessageType, "NotSent", 0)
            failureCB()
        elif loraSendStatus == ReturnStatus.OTHER:
            DatabaseHelper.add_message_stat(self.GetInstanceName(), statMessageType, "NotSent", 0)
            notSentCB()
