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
from utils.utils import Utils

class Main:
    def __init__(self):
        self.shouldReconfigure = False
        self.forceReconfigure = False
        #self.lastTimeReconfigured = datetime.now()
        self.nextTimeToReconfigure = time.monotonic() + 10
        self.messagesToSendExists = True
        self.previousChannel = None

        Setup.SetupPins()

        #DatabaseHelper.drop_all_tables()
        DatabaseHelper.ensure_tables_created()
        DatabaseHelper.truncate_setup_tables()
        DatabaseHelper.add_default_channels()
        SettingsClass.IncrementPowerCycle()

        if Setup.SetupAdapters(True):
            self.subscriberAdapters = Setup.SubscriberAdapters
            self.inputAdapters = Setup.InputAdapters

        self.runningOnChip = socket.gethostname() == 'chip'

    def displayChannel(self):
        if self.runningOnChip:
            channel = SettingsClass.GetChannel()
            if channel != self.previousChannel:
                self.previousChannel = channel
                lightSegA = channel in [2,3,5,6,7,8,9]
                lightSegB = channel in [1, 2, 3, 4, 7, 8, 9]
                lightSegC = channel in [1, 3, 4, 5, 6, 7, 8, 9]
                lightSegD = channel in [2, 3, 5, 6, 8]
                lightSegE = channel in [2, 6, 8]
                lightSegF = channel in [4, 5, 6, 8, 9]
                lightSegG = channel in [2, 3, 4, 5, 6, 8, 9]
                ackRequested = SettingsClass.GetAcknowledgementRequested()

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
            #self.lastTimeReconfigured = currentTime
            self.nextTimeToReconfigure = currentTime + 10
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
                (msgSub.NoOfSendTries == 1 and datetime.now() - lastSendTryDate > timedelta(seconds=SettingsClass.GetFirstRetryDelay())) or
                (msgSub.NoOfSendTries == 2 and datetime.now() - lastSendTryDate > timedelta(seconds=SettingsClass.GetSecondRetryDelay())))
            )
            or (lastSendTryDate < lastFindAdapterTryDate and
                ((msgSub.FindAdapterTries == 0 or
                 (msgSub.FindAdapterTries == 1 and datetime.now() - msgSub.FindAdapterTryDate > timedelta(seconds=SettingsClass.GetFirstRetryDelay())) or
                 (msgSub.FindAdapterTries == 2 and datetime.now() - msgSub.FindAdapterTryDate > timedelta(seconds=SettingsClass.GetSecondRetryDelay())))
                ))):
            return True
        return False

    def shouldArchiveMessage(self, msgSub):
        lastSendTryDate = max(msgSub.SentDate if msgSub.SentDate is not None else datetime.min,
                              msgSub.SendFailedDate if msgSub.SendFailedDate is not None else datetime.min)
        if (
            (msgSub.NoOfSendTries >= 3 and datetime.now() - lastSendTryDate >  timedelta(seconds=SettingsClass.GetSecondRetryDelay()))
            or
            (msgSub.FindAdapterTries >= 3 and datetime.now() - msgSub.FindAdapterTryDate > timedelta(seconds=SettingsClass.GetSecondRetryDelay()))):
            return True
        return False

    def getMessageSubscriptionsToSend(self):
        msgSubsToSend = []
        if self.messagesToSendExists:
            msgSubscriptions = DatabaseHelper.get_message_subscriptions_view()
            if len(msgSubscriptions) == 0:
                self.messagesToSendExists = False
            else:
                msgSubsToSend = [msgSub for msgSub in msgSubscriptions if self.timeToSendMessage(msgSub)]
                #for msgSub in msgSubscriptions:
                #    if self.timeToSendMessage(msgSub):
                #        msgSubsToSend.append(msgSub)
        return msgSubsToSend

    def archiveFailedMessages(self):
        if self.messagesToSendExists:
            msgSubscriptions = DatabaseHelper.get_message_subscriptions_view()
            for msgSub in msgSubscriptions:
                if self.shouldArchiveMessage(msgSub):
                    DatabaseHelper.archive_message_subscription_view_not_sent(msgSub)


    def Run(self):
        while True:

            if self.timeToReconfigure():
                SettingsClass.IsDirty("StatusMessageInterval", True, True) #force check dirty in db
                #SettingsClass.SetMessagesToSendExists(True)
                self.archiveFailedMessages()
                self.displayChannel()
                if Setup.SetupAdapters(False):
                    self.subscriberAdapters = Setup.SubscriberAdapters
                    self.inputAdapters = Setup.InputAdapters
                #return

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
                            messageTypeId = DatabaseHelper.get_message_type(messageTypeName).id
                            mbd = MessageBoxData()
                            mbd.MessageData = inputData["Data"]
                            mbd.MessageTypeId = messageTypeId
                            mbd.PowerCycleCreated = SettingsClass.GetPowerCycle()
                            mbd.ChecksumOK = inputData["ChecksumOK"]
                            mbd.InstanceName = instanceName
                            mbdid = DatabaseHelper.save_message_box(mbd)
                            SettingsClass.SetTimeOfLastMessageAdded()
                            anySubscription = False
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

                                # transform the data before sending
                                transformClass = subAdapter.GetTransform(msgSub.TransformName)
                                transformedData = transformClass.Transform(msgSub.MessageData)
                                if transformedData is not None:
                                    success = subAdapter.SendData(transformedData)
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
