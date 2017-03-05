__author__ = 'henla464'

from datamodel.datamodel import MessageBoxData
from datamodel.datamodel import MessageSubscriptionData
from setup import Setup
#import threading
import time
import logging, logging.handlers
from datetime import datetime, timedelta
from webroutes.meosconfiguration import *
import cProfile
from chipGPIO.chipGPIO import *
import socket


class Main:
    def __init__(self):
        self.shouldReconfigure = False
        self.lastTimeReconfigured = datetime.now()
        Setup.SetupPins()

        #DatabaseHelper.mainDatabaseHelper.drop_all_tables()
        #DatabaseHelper.mainDatabaseHelper.truncate_setup_tables()
        DatabaseHelper.mainDatabaseHelper = DatabaseHelper()
        DatabaseHelper.mainDatabaseHelper.ensure_tables_created()
        DatabaseHelper.mainDatabaseHelper.add_default_channels()
        SettingsClass.IncrementPowerCycle()

        self.subscriberAdapters = Setup.SetupSubscribers()
        self.inputAdapters = Setup.SetupInputAdapters(True)

        self.runningOnChip = socket.gethostname() == 'chip'

    def displayChannel(self):
        if self.runningOnChip:
            channel = SettingsClass.GetChannel()
            lightSegA = channel in [2,3,5,6,7,8,9]
            lightSegB = channel in [1, 2, 3, 4, 7, 8, 9]
            lightSegC = channel in [1, 3, 4, 5, 6, 7, 8, 9]
            lightSegD = channel in [2, 3, 5, 6, 8]
            lightSegE = channel in [2, 6, 8]
            lightSegF = channel in [4, 5, 6, 8, 9]
            lightSegG = channel in [2, 3, 4, 5, 6, 8, 9]

            digitalWrite(0, int(lightSegA))
            digitalWrite(1, int(lightSegB))
            digitalWrite(2, int(lightSegC))
            digitalWrite(3, int(lightSegD))
            digitalWrite(4, int(lightSegE))
            digitalWrite(5, int(lightSegF))
            digitalWrite(6, int(lightSegG))

            digitalWrite(7, int(SettingsClass.GetAcknowledgementRequested()))

    def timeToReconfigure(self):
        currentTime = datetime.now()
        if currentTime - self.lastTimeReconfigured > timedelta(seconds=10) or self.shouldReconfigure:
            self.lastTimeReconfigured = currentTime
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
        if SettingsClass.GetMessagesToSendExists():
            msgSubscriptions = DatabaseHelper.mainDatabaseHelper.get_message_subscriptions_view()
            if len(msgSubscriptions) == 0:
                SettingsClass.SetMessagesToSendExists(False)
            else:
                for msgSub in msgSubscriptions:
                    if self.timeToSendMessage(msgSub):
                        msgSubsToSend.append(msgSub)
        return msgSubsToSend

    def archiveFailedMessages(self):
        if SettingsClass.GetMessagesToSendExists():
            msgSubscriptions = DatabaseHelper.mainDatabaseHelper.get_message_subscriptions_view()
            for msgSub in msgSubscriptions:
                if self.shouldArchiveMessage(msgSub):
                    DatabaseHelper.mainDatabaseHelper.archive_message_subscription_view_not_sent(msgSub)


    def Run(self):
        while True:

            if self.timeToReconfigure():
                SettingsClass.SetMessagesToSendExists(True)
                self.archiveFailedMessages()
                self.displayChannel()
                #return
                self.subscriberAdapters = Setup.SetupSubscribers()
                self.inputAdapters = Setup.SetupInputAdapters(False)

            time.sleep(0.05)
            for inputAdapter in self.inputAdapters:
                inputData = None
                try:
                    inputData = inputAdapter.GetData()
                except Exception as ex:
                    self.shouldReconfigure = True
                    logging.error("InputAdapter error in GetData: " + str(inputAdapter.GetInstanceName()))
                    logging.error(ex)

                if inputData is not None:
                    logging.info("input data")
                    if inputData["MessageType"] == "DATA":
                        logging.info("Received data from " + inputAdapter.GetInstanceName())
                        messageTypeName = inputAdapter.GetTypeName()
                        instanceName = inputAdapter.GetInstanceName()
                        messageTypeId = DatabaseHelper.mainDatabaseHelper.get_message_type(messageTypeName).id
                        mbd = MessageBoxData()
                        mbd.MessageData = inputData["Data"]
                        mbd.MessageTypeId = messageTypeId
                        mbd.PowerCycleCreated = SettingsClass.GetPowerCycle()
                        mbd.ChecksumOK = inputData["ChecksumOK"]
                        mbd.InstanceName = instanceName
                        mbd = DatabaseHelper.mainDatabaseHelper.save_message_box(mbd)
                        SettingsClass.SetTimeOfLastMessageAdded()
                        anySubscription = False
                        logging.debug("MessageTypeID: " + str(messageTypeId))
                        subscriptions = DatabaseHelper.mainDatabaseHelper.get_subscriptions_by_input_message_type_id(messageTypeId)
                        for subscription in subscriptions:
                            msgSubscription = MessageSubscriptionData()
                            msgSubscription.MessageBoxId = mbd.id
                            msgSubscription.SubscriptionId = subscription.id
                            DatabaseHelper.mainDatabaseHelper.save_message_subscription(msgSubscription)
                            anySubscription = True
                            SettingsClass.SetMessagesToSendExists(True)
                        if not anySubscription:
                            DatabaseHelper.mainDatabaseHelper.archive_message_box(mbd.id)
                    elif inputData["MessageType"] == "ACK":
                        messageNumber = inputData["MessageNumber"]
                        logging.debug("Received ack, for message number: " + str(messageNumber))
                        DatabaseHelper.mainDatabaseHelper.archive_message_subscription_after_ack(messageNumber)

            if SettingsClass.GetMessagesToSendExists():
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
                                    logging.info("Message sent")
                                    if msgSub.DeleteAfterSent: # move msgsub to archive
                                        DatabaseHelper.mainDatabaseHelper.archive_message_subscription_view_after_sent(msgSub)
                                    else: # set SentDate and increment NoOfSendTries
                                        DatabaseHelper.mainDatabaseHelper.increment_send_tries_and_set_sent_date(msgSub)
                                else:
                                    # failed to send
                                    logging.warning("Failed to send message: " + msgSub.SubscriberTypeName)
                                    DatabaseHelper.mainDatabaseHelper.increment_send_tries_and_set_send_failed_date(msgSub)
                            else:
                                # shouldn't be sent, so just archive the message subscription
                                DatabaseHelper.mainDatabaseHelper.archive_message_subscription_view_not_sent(msgSub)
                    logging.info("sub adapter if not found")
                    if not adapterFound:
                        logging.info("Send adapter not found for " + msgSub.SubscriberInstanceName + " " + msgSub.SubscriberTypeName)
                        DatabaseHelper.mainDatabaseHelper.increment_find_adapter_tries_and_set_find_adapter_try_date(msgSub)




main = None
def main():
    logging.info("Start main")
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
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(rotFileHandler)
    logging.getLogger('').addHandler(console)

    #Create pid file for systemd service
    #pid = str(os.getpid())
    #f = open('/run/WiRocPython.pid', 'w')
    #f.write(pid)
    #f.close()

    logging.info("Start")
    startMain()
    #threading.Thread(target=startMain).start()
    #startWebServer()







