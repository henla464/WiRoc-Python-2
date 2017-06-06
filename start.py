__author__ = 'henla464'

from datamodel.datamodel import MessageBoxData
from datamodel.datamodel import MessageSubscriptionData
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
        self.wifiPowerSaving = False

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
                    DatabaseHelper.save_message_subscription(msgSubscription)

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

    def timeToSendMessage(self, msgSub):
        lastSendTryDate = max(msgSub.SentDate if msgSub.SentDate is not None else datetime.min,
                       msgSub.SendFailedDate if msgSub.SendFailedDate is not None else datetime.min)
        lastFindAdapterTryDate = msgSub.FindAdapterTryDate if msgSub.FindAdapterTryDate is not None else datetime.min
        if (
            (lastSendTryDate >= lastFindAdapterTryDate and
                (msgSub.NoOfSendTries == 0 or
                (msgSub.NoOfSendTries < SettingsClass.GetMaxRetries() and datetime.now() - lastSendTryDate > timedelta(microseconds=SettingsClass.GetRetryDelay(msgSub.NoOfSendTries))))
            )
            or (lastSendTryDate < lastFindAdapterTryDate and
                (msgSub.FindAdapterTries == 0 or
                 (msgSub.FindAdapterTries < SettingsClass.GetMaxRetries() and datetime.now() - msgSub.FindAdapterTryDate > timedelta(microseconds=SettingsClass.GetRetryDelay(msgSub.FindAdapterTries))))
                )):
            return True
        return False

    def shouldArchiveMessage(self, msgSub):
        return msgSub.NoOfSendTries >= SettingsClass.GetMaxRetries() or msgSub.FindAdapterTries >= SettingsClass.GetMaxRetries()

    def getMessageSubscriptionsToSend(self):
        msgSubsToSend = []
        if self.messagesToSendExists:
            msgSubscriptions = DatabaseHelper.get_message_subscriptions_view(1)
            if len(msgSubscriptions) == 0:
                self.messagesToSendExists = False
            else:
                msgSubsToSend = [msgSub for msgSub in msgSubscriptions if self.timeToSendMessage(msgSub)]
        return msgSubsToSend

    def archiveFailedMessages(self):
        if self.messagesToSendExists:
            msgSubscriptions = DatabaseHelper.get_message_subscriptions_view(100)
            for msgSub in msgSubscriptions:
                if self.shouldArchiveMessage(msgSub):
                    DatabaseHelper.archive_message_subscription_view_not_sent(msgSub)

    def updateWifiPowerSaving(self):
        if self.runningOnChip:
            sendToMeos = SettingsClass.GetSendToMeosEnabled()
            if sendToMeos and self.wifiPowerSaving:
                # disable power saving
                os.system("sudo iw wlan0 set power_save off")
            elif not sendToMeos and not self.wifiPowerSaving:
                # enable power saving
                os.system("sudo iw wlan0 set power_save on")


    def Run(self):
        while True:

            if self.timeToReconfigure():
                SettingsClass.IsDirty("StatusMessageBaseInterval", True, True) #force check dirty in db
                #SettingsClass.SetMessagesToSendExists(True)
                self.archiveFailedMessages()
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
                            mbd = MessageBoxData()
                            mbd.MessageData = inputData["Data"]
                            mbd.MessageTypeName = messageTypeName
                            mbd.PowerCycleCreated = SettingsClass.GetPowerCycle()
                            mbd.ChecksumOK = inputData["ChecksumOK"]
                            mbd.InstanceName = instanceName
                            mbdid = DatabaseHelper.save_message_box(mbd)
                            SettingsClass.SetTimeOfLastMessageAdded()
                            inputAdapter.AddedToMessageBox(mbdid)
                            anySubscription = False
                            messageTypeId = DatabaseHelper.get_message_type(messageTypeName).id
                            subscriptions = DatabaseHelper.get_subscriptions_by_input_message_type_id(messageTypeId)
                            for subscription in subscriptions:
                                msgSubscription = MessageSubscriptionData()
                                msgSubscription.MessageBoxId = mbdid
                                msgSubscription.SubscriptionId = subscription.id
                                DatabaseHelper.save_message_subscription(msgSubscription)
                                anySubscription = True
                                self.messagesToSendExists = True
                            if not anySubscription:
                                DatabaseHelper.archive_message_box(mbdid)
                        elif inputData["MessageType"] == "ACK":
                            messageNumber = inputData["MessageNumber"]
                            logging.debug("Start::Run() Received ack, for message number: " + str(messageNumber))
                            DatabaseHelper.archive_message_subscription_after_ack(messageNumber)

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
                                    transformedData = transformClass.Transform(msgSub)
                                    if transformedData is not None:
                                        if transformedData["CustomData"] is not None:
                                            DatabaseHelper.update_customdata(msgSub.id, transformedData["CustomData"])

                                        success = subAdapter.SendData(transformedData["Data"])
                                        if success:
                                            logging.info("Start::Run() Message sent to " + msgSub.SubscriberInstanceName + " " + msgSub.SubscriberTypeName + " Trans:" + msgSub.TransformName)
                                            if msgSub.DeleteAfterSent: # move msgsub to archive
                                                DatabaseHelper.archive_message_subscription_view_after_sent(msgSub)
                                            else: # set SentDate and increment NoOfSendTries
                                                DatabaseHelper.increment_send_tries_and_set_sent_date(msgSub)
                                        else:
                                            # failed to send
                                            logging.warning("Start::Run() Failed to send message: " + msgSub.SubscriberInstanceName + " " + msgSub.SubscriberTypeName + " Trans:" + msgSub.TransformName)
                                            DatabaseHelper.increment_send_tries_and_set_send_failed_date(msgSub)
                                    else:
                                        # shouldn't be sent, so just archive the message subscription
                                        # (Probably a Lora message that doesn't request ack
                                        logging.debug("Start::Run() " + msgSub.TransformName + " return None so not sent")
                                        DatabaseHelper.archive_message_subscription_view_not_sent(msgSub)
                        if not adapterFound:
                            logging.warning("Start::Run() Send adapter not found for " + msgSub.SubscriberInstanceName + " " + msgSub.SubscriberTypeName)
                            DatabaseHelper.increment_find_adapter_tries_and_set_find_adapter_try_date(msgSub)




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
                        filemode='w')
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    rotFileHandler = logging.handlers.RotatingFileHandler('WiRoc.log', maxBytes=20000000, backupCount=3)
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
