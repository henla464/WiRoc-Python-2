__author__ = 'henla464'

from datamodel.datamodel import MessageBoxData
from datamodel.datamodel import RepeaterMessageBoxData
from datamodel.datamodel import MessageSubscriptionData
from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage
from setup import Setup
import time
import logging, logging.handlers
from datetime import datetime, timedelta
from webroutes.meosconfiguration import *
import cProfile
from chipGPIO.chipGPIO import *
import socket
from itertools import repeat
from battery import Battery

class Main:
    def __init__(self):
        self.shouldReconfigure = False
        self.forceReconfigure = False
        #self.lastTimeReconfigured = datetime.now()
        self.nextTimeToReconfigure = time.monotonic() + 10
        self.messagesToSendExists = True
        self.previousChannel = None
        self.previousAckRequested = None
        self.wifiPowerSaving = None

        Battery.Setup()
        Setup.SetupPins()

        #DatabaseHelper.drop_all_tables()
        DatabaseHelper.ensure_tables_created()
        DatabaseHelper.truncate_setup_tables()
        DatabaseHelper.add_default_channels()
        SettingsClass.IncrementPowerCycle()
        Setup.AddMessageTypes()

        if Setup.SetupAdapters():
            self.subscriberAdapters = Setup.SubscriberAdapters
            self.inputAdapters = Setup.InputAdapters

            # recreate message subscriptions after reboot for messages in the messagebox
            messages = DatabaseHelper.get_message_box_messages()
            for msg in messages:
                messageTypeId = DatabaseHelper.get_message_type(msg.MessageTypeName).id
                subscriptions = DatabaseHelper.get_subscriptions_by_input_message_type_id(messageTypeId)
                for subscription in subscriptions:
                    msgSubscription = MessageSubscriptionData()
                    msgSubscription.MessageBoxId = msg.id
                    msgSubscription.SubscriptionId = subscription.id
                    msgSubscription.ScheduledTime = datetime.now()
                    msgSubscription.MessageNumber = MessageSubscriptionData.GetNextMessageNumber()
                    DatabaseHelper.save_message_subscription(msgSubscription)

            # archive the messages that does not have subscriptions
            DatabaseHelper.archive_message_box_without_subscriptions()

        self.runningOnChip = socket.gethostname() == 'chip'

    def displayChannel(self):
        if self.runningOnChip:
            channel = SettingsClass.GetChannel()
            ackRequested = SettingsClass.GetAcknowledgementRequested()
            if channel != self.previousChannel or ackRequested != self.previousAckRequested:
                self.previousChannel = channel
                self.previousAckRequested = ackRequested
                lightSegA = channel in [2,3,5,6,7,8,9]
                lightSegB = channel in [1, 2, 3, 4, 7, 8, 9]
                lightSegC = channel in [1, 3, 4, 5, 6, 7, 8, 9]
                lightSegD = channel in [2, 3, 5, 6, 8]
                lightSegE = channel in [2, 6, 8]
                lightSegF = channel in [4, 5, 6, 8, 9]
                lightSegG = channel in [2, 3, 4, 5, 6, 8, 9]

                if True:
                    lightSegA = not lightSegA
                    lightSegB = not lightSegB
                    lightSegC = not lightSegC
                    lightSegD = not lightSegD
                    lightSegE = not lightSegE
                    lightSegF = not lightSegF
                    lightSegG = not lightSegG
                    ackRequested = not ackRequested

                digitalWrite(0, int(lightSegA))
                digitalWrite(1, int(lightSegB))
                digitalWrite(2, int(lightSegC))
                digitalWrite(3, int(lightSegD))
                digitalWrite(4, int(lightSegE))
                digitalWrite(5, int(lightSegF))
                digitalWrite(6, int(lightSegG))

                digitalWrite(7, int(ackRequested))

    def timeToReconfigure(self):
        currentTime = time.monotonic()
        if currentTime > self.nextTimeToReconfigure or self.shouldReconfigure:
            self.nextTimeToReconfigure = currentTime + SettingsClass.GetReconfigureInterval()
            self.shouldReconfigure = False
            return True
        else:
            return False

    def getMessageSubscriptionsToSend(self):
        cnt, msgSubsToSend = DatabaseHelper.get_message_subscriptions_view_to_send(SettingsClass.GetMaxRetries(), 1)
        if cnt == 0:
           self.messagesToSendExists = False
        return msgSubsToSend

    def archiveFailedMessages(self):
        #if self.messagesToSendExists:
        msgSubscriptions = DatabaseHelper.get_message_subscriptions_view_to_archive(SettingsClass.GetMaxRetries(), 100)
        for msgSub in msgSubscriptions:
            #if self.shouldArchiveMessage(msgSub):
            logging.info("Start::archiveFailedMessages() subscription reached max tries: " + msgSub.SubscriberInstanceName + " Transform: " + msgSub.TransformName + " msgSubId: " + str(msgSub.id))
            DatabaseHelper.archive_message_subscription_view_not_sent(msgSub)

    def updateWifiPowerSaving(self):
        if self.runningOnChip:
            sendToMeos = SettingsClass.GetSendToMeosEnabled()
            if sendToMeos and (self.wifiPowerSaving or self.wifiPowerSaving is None):
                # disable power saving
                logging.info("Start::updateWifiPowerSaving() Disable WiFi power saving")
                os.system("sudo iw wlan0 set power_save off")
                self.wifiPowerSaving = False
            elif not sendToMeos and (not self.wifiPowerSaving or self.wifiPowerSaving is None):
                # enable power saving
                logging.info("Start::updateWifiPowerSaving() Enable WiFi power saving")
                os.system("sudo iw wlan0 set power_save on")
                self.wifiPowerSaving = True


    def Run(self):
        while True:

            if self.timeToReconfigure():
                SettingsClass.IsDirty("StatusMessageBaseInterval", True, True) #force check dirty in db
                #SettingsClass.SetMessagesToSendExists(True)
                self.archiveFailedMessages()
                DatabaseHelper.archive_old_repeater_message()
                self.displayChannel()
                self.updateWifiPowerSaving()
                Battery.Tick()
                SettingsClass.Tick()
                if Setup.SetupAdapters():
                    self.subscriberAdapters = Setup.SubscriberAdapters
                    self.inputAdapters = Setup.InputAdapters


            activeInputAdapters = [inputAdapter for inputAdapter in self.inputAdapters
                                   if inputAdapter.UpdateInfreqently() and inputAdapter.GetIsInitialized()]

            for i in repeat(None, 20):
                time.sleep(0.05)
                for inputAdapter in activeInputAdapters:
                    inputData = None
                    try:
                        inputData = inputAdapter.GetData()
                    except Exception as ex:
                        self.shouldReconfigure = True
                        logging.error("InputAdapter error in GetData: " + str(inputAdapter.GetInstanceName()))
                        logging.error(ex)

                    if inputData is not None:
                        if inputData["MessageType"] == "DATA":
                            logging.info("Start::Run() Received data from " + inputAdapter.GetInstanceName())
                            messageTypeName = inputAdapter.GetTypeName()
                            instanceName = inputAdapter.GetInstanceName()
                            if messageTypeName == "LORA" and SettingsClass.GetWiRocMode() == "REPEATER":
                                # WiRoc is in repeater mode and received a LORA message
                                logging.info("Start::Run() In repeater mode")
                                loraMessage = inputData["LoraRadioMessage"]
                                rmbd = RepeaterMessageBoxData()
                                rmbd.MessageData = inputData["Data"]
                                rmbd.MessageTypeName = messageTypeName
                                rmbd.PowerCycleCreated = SettingsClass.GetPowerCycle()
                                rmbd.InstanceName = instanceName
                                rmbd.MessageSubTypeName = inputData["MessageSubTypeName"]
                                rmbd.ChecksumOK = inputData["ChecksumOK"]
                                rmbd.MessageSource = inputData["MessageSource"]
                                if loraMessage.GetMessageType() == LoraRadioMessage.MessageTypeSIPunch:
                                    loraHeaderSize = LoraRadioMessage.GetHeaderSize()
                                    siPayloadData = loraMessage.GetByteArray()[loraHeaderSize:]
                                    siMsg = SIMessage()
                                    siMsg.AddPayload(siPayloadData)
                                    rmbd.SICardNumber = siMsg.GetSICardNumber()
                                    rmbd.SportIdentHour = siMsg.GetHour()
                                    rmbd.SportIdentMinute = siMsg.GetMinute()
                                    rmbd.SportIdentSecond = siMsg.GetSeconds()
                                rmbd.MessageID = inputData["MessageID"]
                                rmbd.AckRequested = loraMessage.GetAcknowledgementRequested()
                                rmbd.RelayRequested = loraMessage.GetRepeaterBit()
                                rmbd.NoOfTimesSeen = 1
                                rmbd.NoOfTimesAckSeen = 0
                                rmbdid = DatabaseHelper.save_repeater_message_box(rmbd)
                            else:
                                #if messageTypeName == "LORA" and SettingsClass.GetWiRocMode() == "RECEIVE":
                                #    DatabaseHelper.archive_repeater_lora_message_subscription_after_ack(messageID)

                                mbd = MessageBoxData()
                                mbd.MessageData = inputData["Data"]
                                mbd.MessageTypeName = messageTypeName
                                mbd.PowerCycleCreated = SettingsClass.GetPowerCycle()
                                mbd.ChecksumOK = inputData["ChecksumOK"]
                                mbd.InstanceName = instanceName
                                mbd.MessageSubTypeName = inputData["MessageSubTypeName"]
                                mbd.MessageSource = inputData["MessageSource"]
                                mbdid = DatabaseHelper.save_message_box(mbd)
                                SettingsClass.SetTimeOfLastMessageAdded()
                                inputAdapter.AddedToMessageBox(mbdid)
                                anySubscription = False
                                messageTypeId = DatabaseHelper.get_message_type(messageTypeName).id
                                subscriptions = DatabaseHelper.get_subscriptions_by_input_message_type_id(messageTypeId)
                                for subscription in subscriptions:
                                    msgSubscription = MessageSubscriptionData()
                                    now = datetime.now()
                                    if subscription.WaitUntilAckSent and mbd.MessageSource == "WiRoc":
                                        msgSubscription.ScheduledTime = now + timedelta(seconds=SettingsClass.GetLoraAckMessageSendingTimeS())
                                    elif subscription.WaitThisNumberOfBytes > 0:
                                        msgSubscription.ScheduledTime = now + timedelta(
                                            seconds=SettingsClass.GetLoraMessageTimeSendingTimeS(subscription.WaitThisNumberOfBytes))
                                    else:
                                        msgSubscription.ScheduledTime = now
                                    msgSubscription.MessageBoxId = mbdid
                                    msgSubscription.SubscriptionId = subscription.id
                                    msgSubscription.MessageID = inputData.get("MessageID", None) # used for messages from repeater table
                                    msgSubscription.MessageNumber = MessageSubscriptionData.GetNextMessageNumber()
                                    DatabaseHelper.save_message_subscription(msgSubscription)
                                    anySubscription = True
                                    self.messagesToSendExists = True
                                if not anySubscription:
                                    logging.info("Start::Run() Message has no subscribers, being archived, msgid: " + str(mbdid))
                                    DatabaseHelper.archive_message_box(mbdid)
                        elif inputData["MessageType"] == "ACK":
                            messageID = inputData["MessageID"]
                            logging.debug("Start::Run() Received ack, for message number: " + str(messageID[0]))
                            loraMessage = inputData["LoraRadioMessage"]
                            destinationHasAcked = loraMessage.GetAcknowledgementRequested()
                            wirocMode = SettingsClass.GetWiRocMode()
                            if wirocMode == "REPEATER":
                                logging.info("Start::Run() In repeater mode")
                                DatabaseHelper.repeater_message_acked(messageID)
                                DatabaseHelper.archive_repeater_lora_message_subscription_after_ack(messageID)
                                if destinationHasAcked:
                                    DatabaseHelper.set_ack_received_from_receiver_on_repeater_lora_ack_message_subscription(messageID)
                            else:
                                DatabaseHelper.archive_message_subscription_after_ack(messageID)

                            receivedFromRepeater = loraMessage.GetRepeaterBit()
                            loraSubAdapters = [subAdapter for subAdapter in self.subscriberAdapters if subAdapter.GetTypeName == "LORA"]
                            if len(loraSubAdapters) > 0:
                                loraSubAdapter = loraSubAdapters[0]
                                if receivedFromRepeater:
                                    loraSubAdapter.AddSuccessWithRepeaterBit()
                                else:
                                    loraSubAdapter.AddSuccessWithoutRepeaterBit()

                            if wirocMode == "SEND" and receivedFromRepeater:
                                if not destinationHasAcked:
                                    # delay an extra message + ack, same as a normal delay after a message is sent
                                    # because the repeater should also send and receive ack
                                    timeS = SettingsClass.GetLoraMessageTimeSendingTimeS(35) # message 23 + ack 10 + 2 extra
                                    DatabaseHelper.increase_scheduled_time(timeS)


                if self.messagesToSendExists:
                    msgSubscriptions = self.getMessageSubscriptionsToSend()
                    for msgSub in msgSubscriptions:
                        #find the right adapter
                        adapterFound = False
                        for subAdapter in self.subscriberAdapters:
                            if (msgSub.SubscriberInstanceName == subAdapter.GetInstanceName() and
                                    msgSub.SubscriberTypeName == subAdapter.GetTypeName()):
                                adapterFound = True

                                if subAdapter.IsReadyToSend():
                                    # transform the data before sending
                                    transformClass = subAdapter.GetTransform(msgSub.TransformName)
                                    transformedData = transformClass.Transform(msgSub, subAdapter)
                                    if transformedData is not None:
                                        if transformedData["MessageID"] is not None:
                                            DatabaseHelper.update_messageid(msgSub.id, transformedData["MessageID"])

                                        success = subAdapter.SendData(transformedData["Data"])
                                        if success:
                                            logging.info("Start::Run() Message sent to " + msgSub.SubscriberInstanceName + " " + msgSub.SubscriberTypeName + " Trans:" + msgSub.TransformName)
                                            if msgSub.DeleteAfterSent: # move msgsub to archive
                                                DatabaseHelper.archive_message_subscription_view_after_sent(msgSub)
                                            else: # set SentDate and increment NoOfSendTries
                                                retryDelay = SettingsClass.GetRetryDelay(msgSub.NoOfSendTries+1)
                                                DatabaseHelper.increment_send_tries_and_set_sent_date(msgSub, retryDelay)
                                                DatabaseHelper.increase_scheduled_time_for_other_subscriptions(msgSub, subAdapter.GetDelayAfterMessageSent())
                                        else:
                                            # failed to send
                                            logging.warning("Start::Run() Failed to send message: " + msgSub.SubscriberInstanceName + " " + msgSub.SubscriberTypeName + " Trans:" + msgSub.TransformName)
                                            retryDelay = SettingsClass.GetRetryDelay(msgSub.NoOfSendTries+1)
                                            DatabaseHelper.increment_send_tries_and_set_send_failed_date(msgSub, retryDelay)
                                    else:
                                        # shouldn't be sent, so just archive the message subscription
                                        # (Probably a Lora message that doesn't request ack
                                        logging.debug("Start::Run() " + msgSub.TransformName + " return None so not sent")
                                        DatabaseHelper.archive_message_subscription_view_not_sent(msgSub)
                        if not adapterFound:
                            logging.warning("Start::Run() Send adapter not found for " + msgSub.SubscriberInstanceName + " " + msgSub.SubscriberTypeName)
                            retryDelay = SettingsClass.GetRetryDelay(msgSub.FindAdapterTries+1)
                            DatabaseHelper.increment_find_adapter_tries_and_set_find_adapter_try_date(msgSub, retryDelay)




main = None
def main():
    logging.info("Start::main() Start main")
    global main
    main = Main()


def run():
    global main
    main.Run()

def startMain():
    main()
    run()
    #cProfile.run('run()')

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        filename='WiRoc.log',
                        filemode='a')
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    rotFileHandler = logging.handlers.RotatingFileHandler('WiRoc.log', maxBytes=20000000, backupCount=3)
    rotFileHandler.doRollover()
    rotFileHandler.setFormatter(formatter)

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(rotFileHandler)
    logging.getLogger('').addHandler(console)

    logging.info("Start")
    startMain()
