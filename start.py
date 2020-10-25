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
from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass
import cProfile
from chipGPIO.hardwareAbstraction import HardwareAbstraction
import socket
from itertools import repeat
from battery import Battery
from utils.utils import Utils
from display.displaystatemachine import DisplayStateMachine
import requests, queue, threading
import sys
from logging.handlers import HTTPHandler

class Main:
    def __init__(self):
        self.wirocLogger = logging.getLogger("WiRoc")
        if len(sys.argv) > 1 and sys.argv[1] == "testrepeater":
            self.wirocLogger.debug("Test repeater")
            ReceiveLoraAdapter.TestRepeater = True
            SendLoraAdapter.TestRepeater = True
        self.shouldReconfigure = False
        self.forceReconfigure = False
        self.nextTimeToReconfigure = time.monotonic() + 10
        self.messagesToSendExists = True
        self.previousChannel = None
        self.previousAckRequested = None
        self.wifiPowerSaving = None
        self.activeInputAdapters = None
        self.webServerUp = False
        self.lastBatteryIsLowReceived = False
        self.callbackQueue = queue.Queue()
        self.threadQueue = queue.Queue()
        self.displayStateMachine = DisplayStateMachine()
        Battery.Setup()
        HardwareAbstraction.Instance.SetupPins()

        #DatabaseHelper.drop_all_tables()
        DatabaseHelper.ensure_tables_created()
        DatabaseHelper.truncate_setup_tables()
        DatabaseHelper.add_default_channels()
        DatabaseHelper.change_future_created_dates()
        DatabaseHelper.change_future_sent_dates()
        SettingsClass.IncrementPowerCycle()
        SettingsClass.SetReceiveSIAdapterActive(False)
        Setup.AddMessageTypes()

        if Setup.SetupAdapters():
            self.subscriberAdapters = Setup.SubscriberAdapters
            self.inputAdapters = Setup.InputAdapters

            # recreate message subscriptions after reboot for messages in the messagebox
            messages = DatabaseHelper.get_message_box_messages()
            for msg in messages:
                subscriptions = DatabaseHelper.get_subscription_view_by_input_message_type(msg.MessageTypeName, msg.MessageSubTypeName)
                for subscription in subscriptions:
                    msgSubscription = MessageSubscriptionData()
                    msgSubscription.MessageBoxId = msg.id
                    msgSubscription.SubscriptionId = subscription.id
                    #msgSubscription.ScheduledTime = datetime.now()
                    msgSubscription.MessageNumber = MessageSubscriptionData.GetNextMessageNumber()
                    DatabaseHelper.save_message_subscription(msgSubscription)

            # archive the messages that does not have subscriptions
            DatabaseHelper.archive_message_box_without_subscriptions()

        # Disable logToServer, must activate manually
        SettingsClass.SetSetting("LogToServer", "0")

        #Add device to web server
        webServerHost = SettingsClass.GetWebServerHost()
        webServerUrl = SettingsClass.GetWebServerUrl()
        btAddress = SettingsClass.GetBTAddress()
        apiKey = SettingsClass.GetAPIKey()
        wiRocDeviceName = SettingsClass.GetWiRocDeviceName() if SettingsClass.GetWiRocDeviceName() != None else "WiRoc Device"
        t = threading.Thread(target=self.addDeviceBackground, args=(webServerHost, webServerUrl, btAddress, apiKey, wiRocDeviceName))
        t.daemon = True
        t.start()

    def updateWebserverIPBackground(self, webServerHost):
        try:
            self.wirocLogger.debug("Start::updateWebserverIPBackground " + str(datetime.now()))
            addrs = socket.getaddrinfo(webServerHost, 80)
            ipv4_addrs = [addr[4][0] for addr in addrs if addr[0] == socket.AF_INET]
            SettingsClass.SetWebServerIP(ipv4_addrs[0])
        except Exception as ex:
            self.wirocLogger.debug("Start::updateWebserverIPBackground Exception " + str(ex) + " " + str(datetime.now()))

    def addDeviceBackground(self, webServerHost, webServerUrl, btAddress, apiKey, wiRocDeviceName):
        try:
            self.updateWebserverIPBackground(webServerHost)
            headers = {'Authorization': apiKey, 'host': webServerHost}

            if SettingsClass.GetDeviceId() == None:
                URL = SettingsClass.GetWebServerIPUrlBackground(webServerUrl) + "/api/v1/Devices/LookupDeviceByBTAddress/" + btAddress
                resp = requests.get(url=URL, timeout=1, headers=headers)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    SettingsClass.SetDeviceId(retDevice['id'])
                if resp.status_code == 404:
                    device = {"BTAddress": btAddress, "name": wiRocDeviceName}  # "description": None
                    URL = SettingsClass.GetWebServerIPUrlBackground(webServerUrl) + "/api/v1/Devices"
                    resp = requests.post(url=URL, json=device, timeout=1, headers=headers)
                    if resp.status_code == 200:
                        retDevice = resp.json()
                        SettingsClass.SetDeviceId(retDevice['id'])
        except Exception as ex:
            self.wirocLogger.warning("Start::Init error creating device on webserver")
            self.wirocLogger.warning("Start::Init " + str(ex))

    def archiveFailedMessages(self):
        #if self.messagesToSendExists:
        msgSubscriptions = DatabaseHelper.get_message_subscriptions_view_to_archive(SettingsClass.GetMaxRetries(), 100)
        for msgSub in msgSubscriptions:
            self.wirocLogger.info("Start::archiveFailedMessages() subscription reached max tries: " + msgSub.SubscriberInstanceName + " Transform: " + msgSub.TransformName + " msgSubId: " + str(msgSub.id))
            DatabaseHelper.archive_message_subscription_view_not_sent(msgSub)

    def reconfigureBackground(self, sendToSirap, webServerIPUrl, webServerHost, loggingServerHost, loggingServerPort, logToServer):
        if any(isinstance(h, logging.handlers.HTTPHandler) for h in logging.getLogger('').handlers):
            if not logToServer:
                logging.getLogger('').handlers = [h for h in logging.getLogger('').handlers if
                                                  not isinstance(h, logging.handlers.HTTPHandler)]
        else:
            if logToServer:
                server = loggingServerHost + ':' + loggingServerPort
                httpHandler = logging.handlers.HTTPHandler(server, '/', method='POST')
                self.wirocLogger.getLogger('').addHandler(httpHandler)

        self.updateWebserverIPBackground(webServerHost)
        self.webServerUp = SendStatusAdapter.TestConnection(webServerIPUrl, webServerHost)
        Battery.UpdateWifiPowerSaving(sendToSirap)
        Battery.Tick()

    def updateDisplayBackground(self,channel,ackRequested, wirocMode, loraRange, wirocDeviceName, sirapTCPEnabled,
                              sendSerialActive, sirapIPAddress, sirapIPPort, wiRocIPAddress):
        self.displayStateMachine.Draw(channel, ackRequested, wirocMode, loraRange, wirocDeviceName, sirapTCPEnabled,
                                      sendSerialActive, sirapIPAddress, sirapIPPort, wiRocIPAddress)

    def doFrequentMaintenanceTasks(self):
        SettingsClass.Tick()
        if HardwareAbstraction.Instance.runningOnChip or HardwareAbstraction.Instance.runningOnNanoPi:
            wiRocDeviceName = SettingsClass.GetWiRocDeviceName() if SettingsClass.GetWiRocDeviceName() != None else "WiRoc Device"
            channel = SettingsClass.GetChannel()
            ackRequested = SettingsClass.GetAcknowledgementRequested()
            wirocMode = SettingsClass.GetWiRocMode()
            loraRange = SettingsClass.GetLoraRange()
            sirapTCPEnabled = SettingsClass.GetSendToSirapEnabled()
            sendSerialActive = SettingsClass.GetSendSerialAdapterActive()
            sirapIPAddress = SettingsClass.GetSendToSirapIP()
            sirapIPPort = SettingsClass.GetSendToSirapIPPort()
            wiRocIPAddress = HardwareAbstraction.Instance.GetWiRocIPAddresses()

            t = threading.Thread(target=self.updateDisplayBackground, args=(
            channel, ackRequested, wirocMode, loraRange, wiRocDeviceName, sirapTCPEnabled, sendSerialActive, sirapIPAddress, sirapIPPort, wiRocIPAddress))
            t.daemon = True
            t.start()


    def doInfrequentMaintenanceTasks(self):
        self.archiveFailedMessages()
        DatabaseHelper.archive_old_repeater_message()
        self.updateBatteryIsLow()

    def reconfigure(self):
        if Setup.SetupAdapters():
            self.subscriberAdapters = Setup.SubscriberAdapters
            self.inputAdapters = Setup.InputAdapters

        webServerIPUrl = SettingsClass.GetWebServerIPUrl()
        webServerHost = SettingsClass.GetWebServerHost()
        loggingServerHost = SettingsClass.GetLoggingServerHost()
        loggingServerPort = SettingsClass.GetLoggingServerPort()
        logToServer = SettingsClass.GetLogToServer()
        sendToSirap = SettingsClass.GetSendToSirapEnabled()

        t = threading.Thread(target=self.reconfigureBackground, args=(sendToSirap, webServerIPUrl, webServerHost, loggingServerHost, loggingServerPort, logToServer))
        t.daemon = True
        t.start()



    def handleInput(self):
        for inputAdapter in self.activeInputAdapters:
            inputData = None
            try:
                inputData = inputAdapter.GetData()
            except Exception as ex:
                self.shouldReconfigure = True
                self.wirocLogger.error("InputAdapter error in GetData: " + str(inputAdapter.GetInstanceName()))
                self.wirocLogger.error(ex)

            if inputData is not None:
                if inputData["MessageType"] == "DATA":
                    self.wirocLogger.info("Start::handleInput() Received data from " + inputAdapter.GetInstanceName())
                    messageID = inputData.get("MessageID", None)
                    messageTypeName = inputAdapter.GetTypeName()
                    messageSource = inputData["MessageSource"]
                    checksumOK = inputData["ChecksumOK"]
                    instanceName = inputAdapter.GetInstanceName()
                    powerCycle = SettingsClass.GetPowerCycle()
                    messageData = inputData["Data"]
                    messageSubTypeName = inputData["MessageSubTypeName"]
                    SIStationSerialNumber = inputData.get("SIStationSerialNumber", None)
                    if messageTypeName == "LORA" and SettingsClass.GetWiRocMode() == "REPEATER":
                        # WiRoc is in repeater mode and received a LORA message
                        self.wirocLogger.info("Start::handleInput() In repeater mode")

                        if not checksumOK:
                            self.wirocLogger.error(
                                "Start::handleInput() MessageType: " + messageTypeName + " MessageSubtypeName: " + messageSubTypeName + " Checksum WRONG")
                            continue
                        loraMessage = inputData.get("LoraRadioMessage", None)
                        if loraMessage == None:
                            self.wirocLogger.error(
                                "Start::handleInput() MessageType: " + messageTypeName + " MessageSubtypeName: " + messageSubTypeName + " No LoraRadioMessage property found")
                            continue
                        rssiValue = loraMessage.GetRSSIValue()
                        rmbd = DatabaseHelper.create_repeater_message_box_data(messageSource, messageTypeName, messageSubTypeName,
                                                                     instanceName, checksumOK, powerCycle,
                                                                     SIStationSerialNumber, messageID, messageData, rssiValue)
                        rmbdid = DatabaseHelper.save_repeater_message_box(rmbd)
                    else:
                        rssiValue = 0
                        if messageTypeName == "LORA":
                            if not checksumOK:
                                self.wirocLogger.error(
                                    "Start::handleInput() MessageType: " + messageTypeName + " MessageSubtypeName: " + messageSubTypeName + " Checksum WRONG")
                                continue
                            loraMessage = inputData.get("LoraRadioMessage", None)
                            if loraMessage == None:
                                self.wirocLogger.error(
                                    "Start::handleInput() MessageType: " + messageTypeName + " MessageSubtypeName: " + messageSubTypeName + " No LoraRadioMessage property found")
                                continue

                            self.wirocLogger.debug(
                                "Start::handleInput() MessageType: " + messageTypeName + ", WiRocMode: " + SettingsClass.GetWiRocMode() + " RepeaterBit: " + str(
                                    loraMessage.GetRepeaterBit()))
                            rssiValue = loraMessage.GetRSSIValue()
                            if SettingsClass.GetWiRocMode() == "RECEIVER":
                                if not loraMessage.GetRepeaterBit():
                                    # Message received that might come from repeater. Archive any already scheduled ack message
                                    # from previously received message (directly from sender)
                                    # Message number ignored, remove acks for same SI-card-number and SI-Station-number
                                    DatabaseHelper.archive_lora_ack_message_subscription(messageID)

                        mbd = DatabaseHelper.create_message_box_data(messageSource, messageTypeName, messageSubTypeName, instanceName, checksumOK, powerCycle, SIStationSerialNumber, messageData, rssiValue)
                        mbdid = DatabaseHelper.save_message_box(mbd)
                        SettingsClass.SetTimeOfLastMessageAdded()
                        inputAdapter.AddedToMessageBox(mbdid)
                        anySubscription = False

                        subscriptions = DatabaseHelper.get_subscription_view_by_input_message_type(messageTypeName, messageSubTypeName)
                        for subscription in subscriptions:
                            self.wirocLogger.debug("Start::handleInput() Subscription: " + subscription.SubscriberTypeName + " " + subscription.TransformName)
                            msgSubscription = MessageSubscriptionData()

                            subAdapters = [subAdapter for subAdapter in self.subscriberAdapters if
                                           subAdapter.GetTypeName() == subscription.SubscriberTypeName]
                            if len(subAdapters) > 0:
                                subAdapter = subAdapters[0]
                                transform = subAdapter.GetTransform(subscription.TransformName)
                                noOfSecondsToWait = transform.GetWaitThisNumberOfSeconds(mbd, subscription, subAdapter)
                                if noOfSecondsToWait == None:
                                    continue  # skip this subscription
                                msgSubscription.Delay = noOfSecondsToWait * 1000000
                                self.wirocLogger.debug('Start::handleInput() Delay: ' + str(noOfSecondsToWait * 1000000))
                                # used for wiroc to wiroc to wait for receiver to send ack first...
                            else:
                                self.wirocLogger.error("Start::handleInput()  SubAdapter not found")

                            msgSubscription.MessageBoxId = mbdid
                            msgSubscription.SubscriptionId = subscription.id
                            if messageID != None:
                                self.wirocLogger.debug("MessageID: " + Utils.GetDataInHex(messageID, logging.DEBUG))
                            # messageid is used for messages from repeater table or test table. Is updated after transform when sent
                            msgSubscription.MessageID = messageID
                            msgSubscription.MessageNumber = MessageSubscriptionData.GetNextMessageNumber()
                            DatabaseHelper.save_message_subscription(msgSubscription)
                            anySubscription = True
                            self.messagesToSendExists = True
                        if not anySubscription:
                            self.wirocLogger.info(
                                "Start::handleInput() Message has no subscribers, being archived, msgid: " + str(mbdid))
                            DatabaseHelper.archive_message_box(mbdid)
                elif inputData["MessageType"] == "ACK":
                    loraSubAdapters = [subAdapter for subAdapter in self.subscriberAdapters if
                                       subAdapter.GetTypeName() == "LORA"]
                    if len(loraSubAdapters) > 0:
                        loraSubAdapter = loraSubAdapters[0]
                        messageID = inputData["MessageID"]
                        loraMessage = inputData["LoraRadioMessage"]
                        destinationHasAcked = loraMessage.GetAcknowledgementRequested()
                        receivedFromRepeater = loraMessage.GetRepeaterBit()
                        rssiValue = loraMessage.GetRSSIValue()
                        wirocMode = SettingsClass.GetWiRocMode()

                        # block/unblock should be done regardless if this is an ack for message sent from this checkpoint or another
                        if wirocMode == "SENDER" and receivedFromRepeater:
                            if not destinationHasAcked:
                                # delay an extra message + ack, same as a normal delay after a message is sent
                                # because the repeater should also send and receive ack
                                loraSubAdapter.BlockSendingToLetRepeaterSendAndReceiveAck()
                            else:
                                loraSubAdapter.RemoveBlock()
                        else:
                            loraSubAdapter.RemoveBlock()

                        subscriptionView = DatabaseHelper.get_last_message_subscription_view_that_was_sent_to_lora()
                        if not inputData["ChecksumOK"]:
                            if Utils.IsEnoughAlike(messageID, subscriptionView.MessageID):
                                messageID = subscriptionView.MessageID
                            else:
                                self.wirocLogger.debug(
                                    "Start::handleInput() Received ack but checksum is wrong and acked message id is not found")
                                continue
                        else:
                            if messageID != subscriptionView.MessageID:
                                # ack is probably an ack of a message sent from another checkpoint
                                self.wirocLogger.debug("Start::handleInput() Received ack but last sent message doesn't match the message id")
                                continue

                        # Only add success when matching message found
                        if messageID == subscriptionView.MessageID:
                            if receivedFromRepeater:
                                loraSubAdapter.AddSuccessWithRepeaterBit()
                            else:
                                loraSubAdapter.AddSuccessWithoutRepeaterBit()

                            if wirocMode == "REPEATER" and len(messageID) == 6:
                                self.wirocLogger.debug("Start::handleInput() Received ack, for repeater message number: " + str(
                                    messageID[0]) + " sicardno: " + str(Utils.DecodeCardNr(messageID[2:6])))
                                DatabaseHelper.repeater_message_acked(messageID, rssiValue)
                                DatabaseHelper.archive_repeater_lora_message_subscription_after_ack(messageID, rssiValue)
                                if destinationHasAcked:
                                    DatabaseHelper.set_ack_received_from_receiver_on_repeater_lora_ack_message_subscription(
                                        messageID)
                            else:
                                if len(messageID) == 6:
                                    self.wirocLogger.debug("Start::handleInput() Received ack, for message number: " + str(
                                        messageID[0]) + " sicardno: " + str(Utils.DecodeCardNr(messageID[2:6]))
                                                  + " receivedFromRepeater: " + str(receivedFromRepeater)
                                                  + " destinationHasAcked: " + str(destinationHasAcked))
                                else:
                                    self.wirocLogger.debug(
                                        "Start::handleInput() Received ack, for status message number: " + str(messageID[0]))
                                DatabaseHelper.archive_message_subscription_after_ack(messageID, rssiValue)



    def handleOutput(self, settDict):
        #self.wirocLogger.debug("IsReadyToSend: " + str(SendLoraAdapter.Instances[0].IsReadyToSend()) + " DateTime: " + str(datetime.now()))
        if self.messagesToSendExists:
            noOfMsgSubWaiting, msgSub = DatabaseHelper.get_message_subscriptions_view_to_send(SettingsClass.GetMaxRetries())
            if noOfMsgSubWaiting == 0:
                self.messagesToSendExists = False
            if msgSub != None:
                #self.wirocLogger.info("msgSub count: " + str(len(msgSubscriptions)))
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

                                if msgSub.DeleteAfterSent:
                                    # shouldn't wait for ack. (ie. repeater message ack)
                                    self.wirocLogger.debug("In loop: subadapter: " + str(type(subAdapter)) + " DeleteAfterSent")
                                    settDict["DelayAfterMessageSent"] = 0
                                else:
                                    self.wirocLogger.debug("In loop: subadapter: " + str(type(subAdapter)) + " DelayAfterMessageSent: " + str(subAdapter.GetDelayAfterMessageSent()))
                                    settDict["DelayAfterMessageSent"] = subAdapter.GetDelayAfterMessageSent()

                                def createSuccessCB(innerSubAdapter):
                                    def successCB():
                                        self.wirocLogger.info(
                                            "Start::Run() successCB() Message sent to " + msgSub.SubscriberInstanceName + " " + msgSub.SubscriberTypeName + " Trans:" + msgSub.TransformName)
                                        if msgSub.DeleteAfterSent:  # move msgsub to archive
                                            DatabaseHelper.archive_message_subscription_view_after_sent(msgSub)
                                        else:  # set SentDate and increment NoOfSendTries
                                            retryDelay = innerSubAdapter.GetRetryDelay(msgSub.NoOfSendTries + 1)
                                            DatabaseHelper.increment_send_tries_and_set_sent_date(msgSub, retryDelay)
                                            self.wirocLogger.debug("Start::Run() successCB() Subadapter: " +str(type(innerSubAdapter)) +
                                                          " Increment send tries, NoOfSendTries: " + str(msgSub.NoOfSendTries) +
                                                          " retryDelay: " + str(retryDelay))
                                    return successCB

                                def createFailureCB(innerSubAdapter):
                                    def failureCB():
                                        # failed to send
                                        self.wirocLogger.warning(
                                            "Start::Run() Failed to send message: " + msgSub.SubscriberInstanceName + " " + msgSub.SubscriberTypeName + " Trans:" + msgSub.TransformName + " id:"+ str(msgSub.id))
                                        retryDelay = innerSubAdapter.GetRetryDelay(msgSub.NoOfSendTries + 1)
                                        DatabaseHelper.increment_send_tries_and_set_send_failed_date(msgSub, retryDelay)
                                        self.wirocLogger.debug(
                                            "Start::Run() failureCB() Subadapter: " + str(type(innerSubAdapter)) +
                                            " Increment send tries, NoOfSendTries: " + str(msgSub.NoOfSendTries) +
                                            " retryDelay: " + str(retryDelay))
                                    return failureCB

                                def createNotSentCB():
                                    def notSentCB():
                                        # msg not sent
                                        self.wirocLogger.warning(
                                            "Start::Run() Message was not sent: " + msgSub.SubscriberInstanceName + " " + msgSub.SubscriberTypeName + " Trans:" + msgSub.TransformName + " id:"+ str(msgSub.id))
                                        DatabaseHelper.clear_fetched_for_sending(msgSub)
                                    return notSentCB

                                t = threading.Thread(target=subAdapter.SendData,
                                                     args=(transformedData["Data"], createSuccessCB(subAdapter), createFailureCB(subAdapter), createNotSentCB(), self.callbackQueue, settDict))
                                self.threadQueue.put(t)
                                t.start()
                            else:
                                # shouldn't be sent, so just archive the message subscription
                                # (Probably a Lora message that doesn't request ack
                                self.wirocLogger.debug("Start::Run() " + msgSub.TransformName + " return None so not sent")
                                DatabaseHelper.archive_message_subscription_view_not_sent(msgSub)
                        else:
                            DatabaseHelper.clear_fetched_for_sending(msgSub)
                            return

                        return

                if not adapterFound:
                    self.wirocLogger.warning(
                        "Start::Run() Send adapter not found for " + msgSub.SubscriberInstanceName + " " + msgSub.SubscriberTypeName)
                    retryDelay = SettingsClass.GetRetryDelay(msgSub.FindAdapterTries + 1)
                    DatabaseHelper.increment_find_adapter_tries_and_set_find_adapter_try_date(msgSub, retryDelay)

    def updateBatteryIsLow(self):
        if self.webServerUp:
            try:
                webServerIPUrl = SettingsClass.GetWebServerIPUrl()
                webServerHost = SettingsClass.GetWebServerHost()
                apiKey = SettingsClass.GetAPIKey()
                batteryIsLowReceived = SettingsClass.GetBatteryIsLowReceived()
                deviceId = SettingsClass.GetDeviceId()
                t = threading.Thread(target=self.updateBatteryIsLowBackground, args=(batteryIsLowReceived, webServerIPUrl, webServerHost, apiKey, deviceId))
                t.daemon = True
                t.start()
            except Exception as ex:
                self.wirocLogger.error("Start::updateBatteryIsLow() Exception: " + str(ex))

    def updateBatteryIsLowBackground(self, batteryIsLowReceived, webServerIPUrl, webServerHost, apiKey, deviceId):
        if deviceId != None:
            try:
                headers = {'Authorization': apiKey, 'host': webServerHost}

                if batteryIsLowReceived and not self.lastBatteryIsLowReceived:
                    URL = webServerIPUrl + "/api/v1/Devices/" + str(deviceId) + "/SetBatteryIsLow"
                    resp = requests.get(url=URL, timeout=1, headers=headers)
                    if resp.status_code == 200:
                        retDevice = resp.json()
                        self.lastBatteryIsLowReceived = retDevice['batteryIsLow']
            except Exception as ex:
                self.wirocLogger.error("Start::updateBatteryIsLowBackground() Exception: " + str(ex))

    def sendMessageStatsBackground(self, messageStat, webServerIPUrl, webServerHost, apiKey):
        if messageStat != None:
            btAddress = SettingsClass.GetBTAddress()
            headers = {'Authorization': apiKey, 'host': webServerHost}

            if self.webServerUp:
                URL = webServerIPUrl + "/api/v1/MessageStats"
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
                    self.wirocLogger.error("Start::sendMessageStatsBackground() Exception: " + str(ex))


    def sendMessageStats(self):
        if self.webServerUp:
            try:
                messageStat = DatabaseHelper.get_message_stat_to_upload()
                webServerIPUrl = SettingsClass.GetWebServerIPUrl()
                webServerHost = SettingsClass.GetWebServerHost()
                apiKey = SettingsClass.GetAPIKey()
                t = threading.Thread(target=self.sendMessageStatsBackground, args=(messageStat, webServerIPUrl, webServerHost, apiKey))
                t.daemon = True
                t.start()
            except Exception as ex:
                self.wirocLogger.error("Start::sendMessageStats() Exception: " + str(ex))

    def handleCallbacks(self):
        try:
            cbt = self.callbackQueue.get(False)
            cb = cbt[0]
            cbargs = cbt[1:]
            self.wirocLogger.debug("arg: " + str(cbt[0]))
            cb(*cbargs)
        except queue.Empty:
            pass
        except Exception as ex:
            self.wirocLogger.error("Start::handleCallbacks() Exception: " + str(ex))

    def Run(self):
        settDict = {}
        settDict["WebServerIPUrl"] = SettingsClass.GetWebServerIPUrl()
        settDict["WebServerHost"] = SettingsClass.GetWebServerHost()
        settDict["WiRocDeviceName"] = SettingsClass.GetWiRocDeviceName() if SettingsClass.GetWiRocDeviceName() != None else "WiRoc Device"
        settDict["SendToSirapIP"] = SettingsClass.GetSendToSirapIP()
        settDict["SendToSirapIPPort"] = SettingsClass.GetSendToSirapIPPort()
        settDict["ApiKey"] = SettingsClass.GetAPIKey()

        while True:
            for i in range(1,1004):
                didTasks = False
                if i % 149 == 0: #use prime numbers to avoid the tasks happening on the same interation
                    print("frequent maintenance time: " + str(datetime.now()))
                    didTasks = True
                    self.doFrequentMaintenanceTasks()

                if i % 251 == 0:
                    print("reconfigure time: " + str(datetime.now()))
                    didTasks = True
                    self.shouldReconfigure = False
                    settDict["WebServerIPUrl"] = SettingsClass.GetWebServerIPUrl()
                    settDict["WebServerHost"] = SettingsClass.GetWebServerHost()
                    settDict[
                        "WiRocDeviceName"] = SettingsClass.GetWiRocDeviceName() if SettingsClass.GetWiRocDeviceName() != None else "WiRoc Device"
                    settDict["SendToSirapIP"] = SettingsClass.GetSendToSirapIP()
                    settDict["SendToSirapIPPort"] = SettingsClass.GetSendToSirapIPPort()
                    settDict["ApiKey"] = SettingsClass.GetAPIKey()
                    self.reconfigure()

                if i % 499 == 0:
                    print("infrequent maintenance time: " + str(datetime.now()))
                    didTasks = True
                    self.doInfrequentMaintenanceTasks()

                #todo: call UpdateInfrequently in i%499
                self.activeInputAdapters = [inputAdapter for inputAdapter in self.inputAdapters
                                            if inputAdapter.UpdateInfreqently() and inputAdapter.GetIsInitialized()]

                if not didTasks:
                    time.sleep(0.04)
                #print("time: " + str(datetime.now()))
                self.handleInput()
                self.handleOutput(settDict)
                self.sendMessageStats()
                while not self.threadQueue.empty():  #ensure that messages are sent before handleCallbacks. Maybe separate send threads from others in future
                    try:
                        bgThread = self.threadQueue.get(False)
                        bgThread.join()
                    except queue.Empty:
                        pass
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
    logging.basicConfig(level=logging.ERROR,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        filename='WiRoc.log',
                        filemode='a')
    logging.raiseExceptions = False
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    rotFileHandler = logging.handlers.RotatingFileHandler('WiRoc.log', maxBytes=20000000, backupCount=3)
    rotFileHandler.doRollover()
    rotFileHandler.setFormatter(formatter)

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)

    # add the handler to the myLogger
    myLogger = logging.getLogger('WiRoc')
    myLogger.setLevel(logging.DEBUG)
    myLogger.propagate = False
    myLogger.addHandler(rotFileHandler)
    myLogger.addHandler(console)

    WiRocDisplayLogger = logging.getLogger('WiRoc.Display')
    WiRocDisplayLogger.setLevel(logging.DEBUG)
    WiRocDisplayLogger.propagate = False
    WiRocDisplayLogger.addHandler(rotFileHandler)
    WiRocDisplayLogger.addHandler(console)
    WiRocInputLogger = logging.getLogger('WiRoc.Input')
    WiRocInputLogger.setLevel(logging.DEBUG)
    WiRocInputLogger.propagate = False
    WiRocInputLogger.addHandler(rotFileHandler)
    WiRocInputLogger.addHandler(console)
    WiRocOutputLogger = logging.getLogger('WiRoc.Output')
    WiRocOutputLogger.setLevel(logging.DEBUG)
    WiRocOutputLogger.propagate = False
    WiRocOutputLogger.addHandler(rotFileHandler)
    WiRocOutputLogger.addHandler(console)

    myLogger.info("Start")
    startMain()
