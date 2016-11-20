__author__ = 'henla464'

from battery.battery import Battery
from constants import *
from datamodel.datamodel import MessageBoxData
from datamodel.datamodel import MessageSubscriptionData
from setup import Setup
import threading
import time
import logging, logging.handlers
from webroutes.radioconfiguration import *
from webroutes.meosconfiguration import *


battery = Battery()

class Main:
    settings = None
    timeSlotManager = None
    nextCallTimeSlotMessage = None
    inboundRadioMode = None
    radios = []
    sock = None
    lastTimeReconfigured = time.time()

    def __init__(self):
        #DatabaseHelper.drop_all_tables()
        DatabaseHelper.truncate_setup_tables()
        DatabaseHelper.ensure_tables_created()
        DatabaseHelper.add_default_channels()
        SettingsClass.IncrementPowerCycle()
        #DatabaseHelper.ensure_main_settings_exists()
        #self.settings = SettingsClass()

        self.subscriberAdapters = Setup.SetupSubscribers()
        self.inputAdapters = Setup.SetupInputAdapters(True)

        #self.timeSlotManager = TimeSlotManager(self.settings)
        #self.nextCallTimeSlotMessage = time.time()

        self.radios = []

        #detectedRadios = self.DetectRadios()
        #radioNumbers = [radio.GetRadioNumber() for radio in detectedRadios]
        #DatabaseHelper.ensure_radio_settings_exists(radioNumbers)

        #self.ConfigureRadios(detectedRadios)


    def timeToReconfigure(self):
        currentTime = time.time()
        if currentTime - self.lastTimeReconfigured > 30:
            self.lastTimeReconfigured = currentTime
            return True
        else:
            return False


    def Run(self):
        while True:

            if self.timeToReconfigure():
                self.subscriberAdapters = Setup.SetupSubscribers()
                self.inputAdapters = Setup.SetupInputAdapters(False)

            time.sleep(0.05)
            for inputAdapter in self.inputAdapters:
                inputData = inputAdapter.GetData()
                if inputData is not None:
                    if inputData["MessageType"] == "DATA":
                        logging.debug("Received data")
                        messageTypeName = inputAdapter.GetTypeName()
                        instanceName = inputAdapter.GetInstanceName()
                        messageTypeId = DatabaseHelper.get_message_type(messageTypeName).id
                        mbd = MessageBoxData()
                        mbd.MessageData = inputData["Data"]
                        mbd.MessageTypeId = messageTypeId
                        mbd.PowerCycleCreated = SettingsClass.GetPowerCycle()
                        mbd.ChecksumOK = inputData["ChecksumOK"]
                        mbd.InstanceName = instanceName
                        mbd = DatabaseHelper.save_message_box(mbd)

                        logging.debug("MessageTypeID: " + messageTypeId)
                        subscriptions = DatabaseHelper.get_subscriptions_by_input_message_type_id(messageTypeId)
                        for subscription in subscriptions:
                            msgSubscription = MessageSubscriptionData()
                            msgSubscription.MessageBoxId = mbd.id
                            msgSubscription.SubscriptionId = subscription.id
                            DatabaseHelper.save_message_subscription(msgSubscription)
                    elif inputData["MessageType"] == "ACK":
                        messageNumber = inputData["MessageNumber"]
                        logging.debug("Received ack, for message number: " + str(messageNumber))
                        DatabaseHelper.archive_message_subscription_after_ack(messageNumber)

            msgSubscriptions = DatabaseHelper.get_message_subscriptions_view()
            for msgSub in msgSubscriptions:
                #find the right adapter
                for subAdapter in self.subscriberAdapters:
                    if (msgSub.SubscriberInstanceName == subAdapter.GetInstanceName() and
                            msgSub.SubscriberTypeName == subAdapter.GetTypeName()):

                        # transform the data before sending
                        transformClass = subAdapter.GetTransform(msgSub.TransformName)
                        transformedData = transformClass.Transform(msgSub.MessageData)
                        if transformedData is not None:
                            success = subAdapter.SendData(transformedData)
                            if success:
                                logging.info("Message sent")
                                if msgSub.DeleteAfterSent: # move msgsub to archive
                                    DatabaseHelper.archive_message_subscription_view_after_sent(msgSub)
                                else: # set SentDate and increment NoOfSendTries
                                    DatabaseHelper.increment_send_tries_and_set_sent_date(msgSub)
                            else:
                                # failed to send
                                logging.warning("Failed to send message")
                        else:
                            # shouldn't be sent, so just archive the message subscription
                            DatabaseHelper.archive_message_subscription_view_not_sent(msgSub)


def startMain():
    logging.info("Start main")
    main = Main()
    main.Run()

@app.route('/')
def index():
    return app.send_static_file('index.htm')

@app.route('/commonsettings', methods=['GET', 'POST'])
def common_settings():
    personId = request.form['personId'] #request.form.get('personId', type=int)
    return personId

def startWebServer():
    logging.info("Start web server")
    app.run(debug=True, host='0.0.0.0', use_reloader=False)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        filename='WiRoc.log',
                        filemode='w')
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    rotFileHandler = logging.handlers.RotatingFileHandler('WiRoc.log', maxBytes=20000000, backupCount=5)
    rotFileHandler.setFormatter(formatter)

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(rotFileHandler)
    logging.getLogger('').addHandler(console)

    logging.info("Start")
    threading.Thread(target=startMain).start()
    startWebServer()







