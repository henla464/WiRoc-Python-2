__author__ = 'henla464'

from datamodel.datamodel import MessageBoxData
from datamodel.datamodel import RepeaterMessageBoxData
from datamodel.datamodel import MessageSubscriptionData
from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage
from subscriberadapters.sendstatusadapter import SendStatusAdapter
from subscriberadapters.sendloraadapter import SendLoraAdapter
from inputadapters.receiveloraadapter import ReceiveLoraAdapter
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
from utils.utils import Utils
import requests, queue, threading
import sys

class Main:
    def __init__(self):
        if len(sys.argv) > 1 and sys.argv[1] == "testrepeater":
            logging.debug("Test repeater")
            ReceiveLoraAdapter.TestRepeater = True
            SendLoraAdapter.TestRepeater = True
        self.shouldReconfigure = False
        self.forceReconfigure = False
        #self.lastTimeReconfigured = datetime.now()
        self.nextTimeToReconfigure = time.monotonic() + 10
        self.messagesToSendExists = True
        self.previousChannel = None
        self.previousAckRequested = None
        self.wifiPowerSaving = None
        self.activeInputAdapters = None
        self.webServerUp = False
        self.callbackQueue = queue.Queue()
        self.threadQueue = queue.Queue()
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
                messageTypeId = DatabaseHelper.get_message_type(msg.MessageTypeName, msg.MessageSubTypeName).id
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

        #Add device to web server
        try:
            btAddress = SettingsClass.GetBTAddress()
            webServerUrl = SettingsClass.GetWebServerUrl()
            apiKey = SettingsClass.GetAPIKey()
            wiRocDeviceName = SettingsClass.GetWiRocDeviceName()
            host = webServerUrl.replace('http://', '').replace('https://', '')
            addrs = socket.getaddrinfo(host, 80)
            ipv4_addrs = [addr[4][0] for addr in addrs if addr[0] == socket.AF_INET]
            headers = {'Authorization': apiKey, 'host': host}

            if SendStatusAdapter.DeviceId == None:
                URL = webServerUrl.replace(host, ipv4_addrs[0]) + "/api/v1/Devices/LookupDeviceByBTAddress/" + btAddress
                resp = requests.get(url=URL, timeout=1, headers=headers)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    SendStatusAdapter.DeviceId = retDevice['id']
                if resp.status_code == 404:
                    device = {"BTAddress": btAddress, "name": wiRocDeviceName}  # "description": None
                    URL = webServerUrl.replace(host, ipv4_addrs[0]) + "/api/v1/Devices"
                    resp = requests.post(url=URL, json=device, timeout=1, headers=headers)
                    if resp.status_code == 200:
                        retDevice = resp.json()
                        SendStatusAdapter.DeviceId = retDevice['id']
        except Exception as ex:
            logging.warning("Start::Init error creating device on webserver")
            logging.warning(ex)

        self.runningOnChip = socket.gethostname() == 'chip'

    def displayChannel(self, channel, ackRequested):
        if self.runningOnChip:
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

    def archiveFailedMessages(self):
        #if self.messagesToSendExists:
        msgSubscriptions = DatabaseHelper.get_message_subscriptions_view_to_archive(SettingsClass.GetMaxRetries(), 100)
        for msgSub in msgSubscriptions:
            #if self.shouldArchiveMessage(msgSub):
            logging.info("Start::archiveFailedMessages() subscription reached max tries: " + msgSub.SubscriberInstanceName + " Transform: " + msgSub.TransformName + " msgSubId: " + str(msgSub.id))
            DatabaseHelper.archive_message_subscription_view_not_sent(msgSub)

    def updateWifiPowerSaving(self, sendToMeos):
        if self.runningOnChip:
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

    def reconfigureBackground(self,channel,ackRequested,sendToMeos, webServerUrl):
        self.displayChannel(channel,ackRequested)
        self.webServerUp = SendStatusAdapter.TestConnection(webServerUrl)
        self.updateWifiPowerSaving(sendToMeos)
        Battery.Tick()
        SettingsClass.Tick()

    def reconfigure(self):
        SettingsClass.IsDirty("StatusMessageBaseInterval", True, True)  # force check dirty in db
        self.archiveFailedMessages()
        DatabaseHelper.archive_old_repeater_message()
        if Setup.SetupAdapters():
            self.subscriberAdapters = Setup.SubscriberAdapters
            self.inputAdapters = Setup.InputAdapters

        channel = None
        ackRequested = None
        sendToMeos = None
        webServerUrl = SettingsClass.GetWebServerUrl()
        if self.runningOnChip:
            channel = SettingsClass.GetChannel()
            ackRequested = SettingsClass.GetAcknowledgementRequested()
            sendToMeos = SettingsClass.GetSendToMeosEnabled()

        t = threading.Thread(target=self.reconfigureBackground, args=(channel,ackRequested,sendToMeos, webServerUrl))
        t.start()



    def handleInput(self):
        for inputAdapter in self.activeInputAdapters:
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
                    messageID = inputData.get("MessageID", None)
                    messageTypeName = inputAdapter.GetTypeName()
                    instanceName = inputAdapter.GetInstanceName()
                    if messageTypeName == "LORA" and SettingsClass.GetWiRocMode() == "REPEATER":
                        # WiRoc is in repeater mode and received a LORA message
                        logging.info("Start::Run() In repeater mode")
                        loraMessage = inputData.get("LoraRadioMessage", None)
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
                        rmbd.MessageID = messageID
                        rmbd.AckRequested = loraMessage.GetAcknowledgementRequested()
                        rmbd.RepeaterRequested = loraMessage.GetRepeaterBit()
                        rmbd.NoOfTimesSeen = 1
                        rmbd.NoOfTimesAckSeen = 0
                        rmbdid = DatabaseHelper.save_repeater_message_box(rmbd)
                    else:
                        loraMessage = inputData.get("LoraRadioMessage", None)
                        if loraMessage != None:
                            logging.debug(
                                "MessageType: " + messageTypeName + ", WiRocMode: " + SettingsClass.GetWiRocMode() + " RepeaterBit: " + str(
                                    loraMessage.GetRepeaterBit()))
                        if messageTypeName == "LORA" and \
                                        SettingsClass.GetWiRocMode() == "RECEIVER":
                            if not loraMessage.GetRepeaterBit():
                                # Message received that might come from repeater. Archive any already scheduled ack message
                                # from previously received message (directly from sender)
                                # Message number ignored, remove acks for same SI-card-number and SI-Station-number
                                DatabaseHelper.archive_lora_ack_message_subscription(messageID)

                        messageSubTypeName = inputData["MessageSubTypeName"]
                        mbd = MessageBoxData()
                        mbd.MessageData = inputData["Data"]
                        mbd.MessageTypeName = messageTypeName
                        mbd.PowerCycleCreated = SettingsClass.GetPowerCycle()
                        mbd.ChecksumOK = inputData["ChecksumOK"]
                        mbd.InstanceName = instanceName
                        mbd.MessageSubTypeName = messageSubTypeName
                        mbd.MessageSource = inputData["MessageSource"]
                        mbdid = DatabaseHelper.save_message_box(mbd)
                        SettingsClass.SetTimeOfLastMessageAdded()
                        inputAdapter.AddedToMessageBox(mbdid)
                        anySubscription = False

                        messageTypeId = DatabaseHelper.get_message_type(messageTypeName, messageSubTypeName).id
                        subscriptions = DatabaseHelper.get_subscription_view_by_input_message_type_id(messageTypeId)
                        for subscription in subscriptions:
                            msgSubscription = MessageSubscriptionData()
                            now = datetime.now()

                            subAdapters = [subAdapter for subAdapter in self.subscriberAdapters if
                                           subAdapter.GetTypeName() == subscription.SubscriberTypeName]
                            if len(subAdapters) > 0:
                                subAdapter = subAdapters[0]
                                transform = subAdapter.GetTransform(subscription.TransformName)
                                noOfSecondsToWait = transform.GetWaitThisNumberOfSeconds(mbd, subscription, subAdapter)
                                if noOfSecondsToWait == None:
                                    continue  # skip this subscription
                                scheduledWaitTime = now + timedelta(seconds=noOfSecondsToWait)
                                scheduledTimeOfOthersToSameAdapter = DatabaseHelper.get_highest_scheduled_time_of_new_subscriptions(subAdapter.GetTypeName())
                                minimumScheduledTime = now
                                if scheduledTimeOfOthersToSameAdapter == None:
                                    logging.debug('scheduledTimeOfOthersToSameAdapter=None')
                                    minimumScheduledTime = SettingsClass.GetTimeOfLastMessageSentToLoraDateTime()+ timedelta(seconds=subAdapter.GetDelayAfterMessageSent())
                                else:
                                    minimumScheduledTime = scheduledTimeOfOthersToSameAdapter + timedelta(seconds=subAdapter.GetDelayAfterMessageSent())
                                    logging.debug('scheduledTimeOfOthersToSameAdapter!=None: ' + str(minimumScheduledTime))
                                msgSubscription.ScheduledTime = max(scheduledWaitTime, minimumScheduledTime)
                                logging.debug('ScheduledTime set to: ' + str(msgSubscription.ScheduledTime))
                            else:
                                logging.error("Start::Run() SubAdapter not found")

                            msgSubscription.MessageBoxId = mbdid
                            msgSubscription.SubscriptionId = subscription.id
                            if messageID != None:
                                dataInHex = ''.join(format(x, '02x') for x in messageID)
                                logging.debug("MessageID: " + dataInHex)
                            msgSubscription.MessageID = messageID  # used for messages from repeater table or test table (added always but only used when in repeater mode)
                            msgSubscription.MessageNumber = MessageSubscriptionData.GetNextMessageNumber()
                            DatabaseHelper.save_message_subscription(msgSubscription)
                            anySubscription = True
                            self.messagesToSendExists = True
                        if not anySubscription:
                            logging.info(
                                "Start::Run() Message has no subscribers, being archived, msgid: " + str(mbdid))
                            DatabaseHelper.archive_message_box(mbdid)
                elif inputData["MessageType"] == "ACK":
                    messageID = inputData["MessageID"]
                    loraMessage = inputData["LoraRadioMessage"]
                    destinationHasAcked = loraMessage.GetAcknowledgementRequested()
                    wirocMode = SettingsClass.GetWiRocMode()
                    if wirocMode == "REPEATER" and len(messageID) == 6:
                        logging.debug("Start::Run() Received ack, for repeater message number: " + str(
                            messageID[0]) + " sicardno: " + str(Utils.DecodeCardNr(messageID[2:6])))
                        DatabaseHelper.repeater_message_acked(messageID)
                        DatabaseHelper.archive_repeater_lora_message_subscription_after_ack(messageID)
                        if destinationHasAcked:
                            DatabaseHelper.set_ack_received_from_receiver_on_repeater_lora_ack_message_subscription(
                                messageID)
                    else:
                        if len(messageID) == 6:
                            logging.debug("Start::Run() Received ack, for message number: " + str(
                                messageID[0]) + " sicardno: " + str(Utils.DecodeCardNr(messageID[2:6])))
                        else:
                            logging.debug(
                                "Start::Run() Received ack, for status message number: " + str(messageID[0]))
                        DatabaseHelper.archive_message_subscription_after_ack(messageID)

                    receivedFromRepeater = loraMessage.GetRepeaterBit()
                    loraSubAdapters = [subAdapter for subAdapter in self.subscriberAdapters if
                                       subAdapter.GetTypeName() == "LORA"]
                    if len(loraSubAdapters) > 0:
                        loraSubAdapter = loraSubAdapters[0]
                        if receivedFromRepeater:
                            loraSubAdapter.AddSuccessWithRepeaterBit()
                        else:
                            loraSubAdapter.AddSuccessWithoutRepeaterBit()

                    if wirocMode == "SENDER" and receivedFromRepeater:
                        if not destinationHasAcked:
                            # delay an extra message + ack, same as a normal delay after a message is sent
                            # because the repeater should also send and receive ack
                            timeS = SettingsClass.GetLoraMessageTimeSendingTimeS(35)  # message 23 + ack 10 + 2 extra
                            DatabaseHelper.increase_scheduled_time_if_less_than(timeS)

    def handleOutput(self, settDict):
        if self.messagesToSendExists:
            noOfMsgSubWaiting, msgSub = DatabaseHelper.get_message_subscriptions_view_to_send(SettingsClass.GetMaxRetries())
            if noOfMsgSubWaiting == 0:
                self.messagesToSendExists = False
            if msgSub != None:
                #logging.info("msgSub count: " + str(len(msgSubscriptions)))
                # find the right adapter
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

                                logging.debug("In loop: subadapter: " + str(type(subAdapter)) + " delayaftermessagesent: " + str(
                                    subAdapter.GetDelayAfterMessageSent()))
                                def createSuccessCB(innerSubAdapter):
                                    def successCB():
                                        logging.info(
                                            "Start::Run() Message sent to " + msgSub.SubscriberInstanceName + " " + msgSub.SubscriberTypeName + " Trans:" + msgSub.TransformName)
                                        if msgSub.DeleteAfterSent:  # move msgsub to archive
                                            DatabaseHelper.archive_message_subscription_view_after_sent(msgSub)
                                        else:  # set SentDate and increment NoOfSendTries
                                            retryDelay = SettingsClass.GetRetryDelay(msgSub.NoOfSendTries + 1)
                                            DatabaseHelper.increment_send_tries_and_set_sent_date(msgSub, retryDelay)
                                            logging.debug("subadapter: " +str(type(innerSubAdapter)) + " delayaftermessagesent: " + str(innerSubAdapter.GetDelayAfterMessageSent()))
                                            DatabaseHelper.increase_scheduled_time_for_other_subscriptions(msgSub,innerSubAdapter.GetDelayAfterMessageSent())
                                    return successCB

                                def createFailureCB():
                                    def failureCB():
                                        # failed to send
                                        logging.warning(
                                            "Start::Run() Failed to send message: " + msgSub.SubscriberInstanceName + " " + msgSub.SubscriberTypeName + " Trans:" + msgSub.TransformName + " id:"+ str(msgSub.id))
                                        retryDelay = SettingsClass.GetRetryDelay(msgSub.NoOfSendTries + 1)
                                        DatabaseHelper.increment_send_tries_and_set_send_failed_date(msgSub, retryDelay)
                                    return failureCB

                                t = threading.Thread(target=subAdapter.SendData,
                                                     args=(transformedData["Data"], createSuccessCB(subAdapter), createFailureCB(), self.callbackQueue, settDict))
                                self.threadQueue.put(t)
                                t.start()
                            else:
                                # shouldn't be sent, so just archive the message subscription
                                # (Probably a Lora message that doesn't request ack
                                logging.debug("Start::Run() " + msgSub.TransformName + " return None so not sent")
                                DatabaseHelper.archive_message_subscription_view_not_sent(msgSub)
                if not adapterFound:
                    logging.warning(
                        "Start::Run() Send adapter not found for " + msgSub.SubscriberInstanceName + " " + msgSub.SubscriberTypeName)
                    retryDelay = SettingsClass.GetRetryDelay(msgSub.FindAdapterTries + 1)
                    DatabaseHelper.increment_find_adapter_tries_and_set_find_adapter_try_date(msgSub, retryDelay)

    def sendMessageStatsBackground(self, messageStat, webServerUrl, apiKey):
        if messageStat != None:
            btAddress = SettingsClass.GetBTAddress()
            host = webServerUrl.replace('http://', '').replace('https://', '')
            addrs = socket.getaddrinfo(host, 80)
            ipv4_addrs = [addr[4][0] for addr in addrs if addr[0] == socket.AF_INET]
            headers = {'Authorization': apiKey, 'host': host}

            if self.webServerUp:
                URL = webServerUrl.replace(host, ipv4_addrs[0]) + "/api/v1/MessageStats"
                messageStatToSend = {"adapterInstance": messageStat.AdapterInstanceName, "BTAddress": btAddress,
                                     "messageType": messageStat.MessageSubTypeName, "status": messageStat.Status,
                                     "noOfMessages": messageStat.NoOfMessages}

                try:
                    resp = requests.post(url=URL, timeout=1, json=messageStatToSend, allow_redirects=False, headers=headers)
                    if resp.status_code == 200 or resp.status_code == 303:
                        self.callbackQueue.put((DatabaseHelper.set_message_stat_uploaded, messageStat.id))
                    else:
                        self.webServerUp = False
                except Exception as ex:
                    logging.error("Start::sendMessageStatsBackground() Exception: " + str(ex))


    def sendMessageStats(self):
        if self.webServerUp:
            try:
                messageStat = DatabaseHelper.get_message_stat_to_upload()
                webServerUrl = SettingsClass.GetWebServerUrl()
                apiKey = SettingsClass.GetAPIKey(False)
                t = threading.Thread(target=self.sendMessageStatsBackground, args=(messageStat, webServerUrl, apiKey))
                t.start()
            except Exception as ex:
                logging.error("Start::sendMessageStats() Exception: " + str(ex))

    def handleCallbacks(self):
        try:
            cbt = self.callbackQueue.get(False)
            cb = cbt[0]
            cbargs = cbt[1:]
            logging.debug("arg: " + str(cbt[0]))
            cb(*cbargs)
        except queue.Empty:
            pass

    def Run(self):
        settDict = {}
        settDict["WebServerUrl"] = SettingsClass.GetWebServerUrl()
        settDict["WiRocDeviceName"] = SettingsClass.GetWiRocDeviceName() if SettingsClass.GetWiRocDeviceName() != None else "WiRoc Device"
        settDict["SendToMeosIP"] = SettingsClass.GetSendToMeosIP()
        settDict["SendToMeosIPPort"] = SettingsClass.GetSendToMeosIPPort()
        settDict["ApiKey"] = SettingsClass.GetAPIKey()

        while True:

            if self.timeToReconfigure():
                settDict["WebServerUrl"] = SettingsClass.GetWebServerUrl()
                settDict["WiRocDeviceName"] = SettingsClass.GetWiRocDeviceName() if SettingsClass.GetWiRocDeviceName() != None else "WiRoc Device"
                settDict["SendToMeosIP"] = SettingsClass.GetSendToMeosIP()
                settDict["SendToMeosIPPort"] = SettingsClass.GetSendToMeosIPPort()
                settDict["ApiKey"] = SettingsClass.GetAPIKey()
                self.reconfigure()

            self.activeInputAdapters = [inputAdapter for inputAdapter in self.inputAdapters
                                   if inputAdapter.UpdateInfreqently() and inputAdapter.GetIsInitialized()]

            for i in repeat(None, 20):
                time.sleep(0.05)
                self.handleInput()
                while not self.threadQueue.empty():
                    try:
                        bgThread = self.threadQueue.get(False)
                        bgThread.join()
                    except queue.Empty:
                        pass
                self.handleOutput(settDict)
                self.sendMessageStats()
                self.handleCallbacks()





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
