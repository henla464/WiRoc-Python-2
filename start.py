__author__ = 'henla464'

from datamodel.datamodel import MessageSubscriptionData
from inputadapters.createstatusadapter import CreateStatusAdapter
from inputadapters.receiveloraadapter import ReceiveLoraAdapter
from inputadapters.receiverepeatermessagesadapter import ReceiveRepeaterMessagesAdapter
from inputadapters.receivesiadapter import ReceiveSIUSBSerialPort, ReceiveSIHWSerialPort, ReceiveSIBluetoothSP
from inputadapters.receivesrradapter import ReceiveSRRAdapter
from inputadapters.receivetestpunchesadapter import ReceiveTestPunchesAdapter
from subscriberadapters.sendloraadapter import SendLoraAdapter
from subscriberadapters.sendserialadapter import SendSerialAdapter
from subscriberadapters.sendstatusadapter import SendStatusAdapter
from setup import Setup
import time
import logging, logging.handlers
from datetime import datetime, timedelta
from datamodel.db_helper import DatabaseHelper
from datamodel.MessageHelper import MessageHelper
from settings.settings import SettingsClass
import cProfile
from chipGPIO.hardwareAbstraction import HardwareAbstraction
from battery import Battery
from subscriberadapters.sendtoblenoadapter import SendToBlenoAdapter
from subscriberadapters.sendtosirapadapter import SendToSirapAdapter
from utils.utils import Utils
from display.displaystatemachine import DisplayStateMachine
from display.displaydata import DisplayData
import requests, queue, threading
import urllib3
import yaml


class Main:
    def __init__(self):
        urllib3.disable_warnings()

        self.wirocLogger: logging.Logger = logging.getLogger("WiRoc")
        self.shouldReconfigure: bool = False
        self.forceReconfigure: bool = False
        self.nextTimeToReconfigure: float = time.monotonic() + 10
        self.messagesToSendExists: bool = True
        self.previousChannel = None
        self.previousAckRequested = None
        #self.wifiPowerSaving = None
        self.activeInputAdapters: None | list[CreateStatusAdapter | ReceiveLoraAdapter | ReceiveSIUSBSerialPort | ReceiveSIHWSerialPort | ReceiveSIBluetoothSP | ReceiveTestPunchesAdapter | ReceiveRepeaterMessagesAdapter | ReceiveSRRAdapter] = None
        self.subscriberAdapters: None | list[SendLoraAdapter | SendSerialAdapter | SendToBlenoAdapter | SendToSirapAdapter | SendStatusAdapter] = None

        self.webServerUp: bool = False
        self.lastBatteryIsLowReceived = None
        self.lastBatteryIsLow = None
        self.callbackQueue = queue.Queue()
        self.threadQueue = queue.Queue()
        self.displayStateMachine = DisplayStateMachine()
        self.lastWiRocDeviceNameSentToServer = None
        Battery.Setup()
        HardwareAbstraction.Instance.SetupPins()

        HardwareAbstraction.Instance.DisablePMUIRQ1()
        HardwareAbstraction.Instance.DisablePMUIRQ2()
        HardwareAbstraction.Instance.DisablePMUIRQ4()

        #DatabaseHelper.drop_all_tables()
        DatabaseHelper.ensure_tables_created()
        DatabaseHelper.truncate_setup_tables()
        DatabaseHelper.add_default_channels()
        DatabaseHelper.change_future_created_dates()
        DatabaseHelper.change_future_sent_dates()
        SettingsClass.IncrementPowerCycle()
        SettingsClass.SetReceiveSIAdapterActive(False)
        Setup.AddMessageTypes()
        self.doFrequentMaintenanceTasks()

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
                    DatabaseHelper.save_message_subscription(msgSubscription)

            # archive the messages that does not have subscriptions
            DatabaseHelper.archive_message_box_without_subscriptions()

        # Disable logToServer, must activate manually
        SettingsClass.SetSetting("LogToServer", "0")

        if SettingsClass.GetSendStatusMessages():
            webServerUrl = SettingsClass.GetWebServerUrl()
            self.webServerUp = SendStatusAdapter.TestConnection(webServerUrl)
        else:
            self.webServerUp = False

        self.addDevice()

    def addDevice(self):
        deviceName = SettingsClass.GetWiRocDeviceName() if SettingsClass.GetWiRocDeviceName() is not None else "WiRoc Device"
        if self.webServerUp and (self.lastWiRocDeviceNameSentToServer != deviceName):
            # Add device to web server
            btAddress = SettingsClass.GetBTAddress()

            if btAddress == "NoBTAddress":
                return
                #time.sleep(2)
                #btAddress = SettingsClass.GetBTAddress()
                #self.wirocLogger.info("start::addDevice() retry get btAddress: " + btAddress)

            self.wirocLogger.info("start::addDevice() btAddress: " + btAddress)
            apiKey = SettingsClass.GetAPIKey()
            webServerUrl = SettingsClass.GetWebServerUrl()
            self.lastWiRocDeviceNameSentToServer = deviceName
            with open("../settings.yaml", "r") as f:
                settings = yaml.load(f, Loader=yaml.BaseLoader)
            wirocPythonVersion = settings['WiRocPythonVersion']
            wirocBLEAPIVersion = settings['WiRocBLEAPIVersion']
            hardwareVersion = settings["WiRocHWVersion"]

            t = threading.Thread(target=self.addDeviceBackground, args=(webServerUrl, btAddress, apiKey, deviceName, wirocPythonVersion, wirocBLEAPIVersion, hardwareVersion))
            t.daemon = True
            t.start()

    def addDeviceBackground(self, webServerUrl, btAddress, apiKey, wiRocDeviceName, wirocPythonVersion, wirocBLEAPIVersion, hardwareVersion):
        try:
            headers = {'X-Authorization': apiKey}
            device = {"BTAddress": btAddress, "headBTAddress": btAddress, "name": wiRocDeviceName,
                      "wirocPythonVersion":wirocPythonVersion, "wirocBLEAPIVersion": wirocBLEAPIVersion,
                      "hardwareVersion": hardwareVersion}
            URL = webServerUrl + "/api/v1/Devices"
            resp = requests.post(url=URL, json=device, timeout=1, headers=headers, verify=False)
            self.wirocLogger.warning("Start::Init resp statuscode btaddress " + btAddress + "  " + str(resp.status_code) + " " + resp.text)
            if resp.status_code == 200:
                retDevice = resp.json()
        except Exception as ex:
            self.wirocLogger.warning("Start::Init error creating device on webserver")
            self.wirocLogger.warning("Start::Init " + str(ex))

    def archiveFailedMessages(self):
        msgSubscriptions = DatabaseHelper.get_message_subscriptions_view_to_archive(SettingsClass.GetMaxRetries(), 100)
        for msgSub in msgSubscriptions:
            self.wirocLogger.info("Start::archiveFailedMessages() subscription reached max tries: " + msgSub.SubscriberInstanceName + " Transform: " + msgSub.TransformName + " msgSubId: " + str(msgSub.id))
            DatabaseHelper.archive_message_subscription_view_not_sent(msgSub.id)

    def reconfigureBackground(self, sendToSirap, webServerUrl, loggingServerHost, loggingServerPort, logToServer):
        if any(isinstance(h, logging.handlers.HTTPHandler) for h in logging.getLogger('').handlers):
            if not logToServer:
                logging.getLogger('').handlers = [h for h in logging.getLogger('').handlers if
                                                  not isinstance(h, logging.handlers.HTTPHandler)]
        else:
            if logToServer:
                server = loggingServerHost + ':' + loggingServerPort
                httpHandler = logging.handlers.HTTPHandler(server, '/', method='POST')
                self.wirocLogger.getLogger('').addHandler(httpHandler)

        if SettingsClass.GetSendStatusMessages():
            self.webServerUp = SendStatusAdapter.TestConnection(webServerUrl)
        else:
            self.webServerUp = False
        Battery.Tick()

    def updateDisplayBackground(self, displayData : DisplayData):
        self.displayStateMachine.Draw(displayData)

    def doFrequentMaintenanceTasks(self):
        displayData = DisplayData()
        displayData.wiRocDeviceName = SettingsClass.GetWiRocDeviceName() if SettingsClass.GetWiRocDeviceName() is not None else "WiRoc Device"
        displayData.channel = SettingsClass.GetChannel()
        displayData.ackRequested = SettingsClass.GetAcknowledgementRequested()
        displayData.wiRocMode = SettingsClass.GetLoraMode()
        displayData.loraRange = SettingsClass.GetLoraRange()
        displayData.sirapTCPEnabled = SettingsClass.GetSendToSirapEnabled()
        displayData.sendSerialActive = SettingsClass.GetSendSerialAdapterActive()
        displayData.sirapIPAddress = SettingsClass.GetSendToSirapIP()
        displayData.sirapIPPort = SettingsClass.GetSendToSirapIPPort()
        displayData.wiRocIPAddresses = HardwareAbstraction.Instance.GetWiRocIPAddresses()
        displayData.errorCodes = DatabaseHelper.get_error_codes()

        t = threading.Thread(target=self.updateDisplayBackground, args=(displayData,))
        t.daemon = True
        t.start()

    def doInfrequentMaintenanceTasks(self):
        self.archiveFailedMessages()
        DatabaseHelper.archive_old_repeater_message()
        self.updateBatteryIsLowReceived()
        self.updateBatteryIsLow()
        self.sendSetConnectedToInternet()
        self.addDevice()

    def reconfigure(self):
        if Setup.SetupAdapters():
            self.subscriberAdapters = Setup.SubscriberAdapters
            self.inputAdapters = Setup.InputAdapters

        webServerUrl = SettingsClass.GetWebServerUrl()
        loggingServerHost = SettingsClass.GetLoggingServerHost()
        loggingServerPort = SettingsClass.GetLoggingServerPort()
        logToServer = SettingsClass.GetLogToServer()
        sendToSirap = SettingsClass.GetSendToSirapEnabled()

        t = threading.Thread(target=self.reconfigureBackground, args=(sendToSirap, webServerUrl, loggingServerHost, loggingServerPort, logToServer))
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
                    messageID: bytearray | None = inputData.get("MessageID", None)
                    messageTypeName = inputAdapter.GetTypeName()
                    messageSource = inputData["MessageSource"]
                    #checksumOK = inputData["ChecksumOK"]
                    instanceName = inputAdapter.GetInstanceName()
                    powerCycle = SettingsClass.GetPowerCycle()
                    messageData = inputData["Data"]
                    messageSubTypeName = inputData["MessageSubTypeName"]
                    SIStationSerialNumber = inputData.get("SIStationSerialNumber", None)
                    if messageTypeName == "LORA" and SettingsClass.GetLoraMode() == "REPEATER":
                        # WiRoc is in repeater mode and received a LORA message
                        self.wirocLogger.info("Start::handleInput() In repeater mode")

                        #if not checksumOK:
                        #    self.wirocLogger.error(
                        #        "Start::handleInput() MessageType: " + messageTypeName + " MessageSubtypeName: " + messageSubTypeName + " Checksum WRONG")
                        #    continue
                        loraMessage = inputData.get("LoraRadioMessage", None)
                        if loraMessage is None:
                            self.wirocLogger.error(
                                "Start::handleInput() MessageType: " + messageTypeName + " MessageSubtypeName: " + messageSubTypeName + " No LoraRadioMessage property found")
                            continue
                        rssiValue = loraMessage.GetRSSIValue()

                        lowBattery, ackRequested, repeater, siPayloadData = MessageHelper.GetLowBatterySIPayload(messageTypeName, messageSubTypeName, messageData)
                        rmbd = DatabaseHelper.create_repeater_message_box_data(messageSource, messageTypeName, messageSubTypeName,
                                                                               instanceName, True, powerCycle, SIStationSerialNumber,
                                                                               lowBattery, ackRequested, repeater, siPayloadData,
                                                                               messageID, messageData, rssiValue)
                        rmbdid = DatabaseHelper.save_repeater_message_box(rmbd)
                    else:
                        if messageTypeName == "LORA":
                            #if not checksumOK:
                            #    self.wirocLogger.error(
                            #        "Start::handleInput() MessageType: " + messageTypeName + " MessageSubtypeName: " + messageSubTypeName + " Checksum WRONG")
                            #    continue
                            loraMessage = inputData.get("LoraRadioMessage", None)
                            if loraMessage is None:
                                self.wirocLogger.error(
                                    "Start::handleInput() MessageType: " + messageTypeName + " MessageSubtypeName: " + messageSubTypeName + " No LoraRadioMessage property found")
                                continue

                            self.wirocLogger.debug(
                                "Start::handleInput() MessageType: " + messageTypeName + " MessageSubtypeName: " + messageSubTypeName + " WiRocMode: " + SettingsClass.GetLoraMode() + " RepeaterBit: " + str(
                                    loraMessage.GetRepeater()))
                            if SettingsClass.GetLoraMode() == "RECEIVER":
                                if not loraMessage.GetRepeater():
                                    # Message received that might come from repeater (repeater (request repeater) is set to false when sent from repeater).
                                    # Archive any already scheduled ack message from previously received message (directly from sender)
                                    DatabaseHelper.archive_lora_ack_message_subscription(messageID)
                        else:
                            loraMessage = None

                        try:
                            mbd = MessageHelper.GetMessageBoxData(messageSource, messageTypeName, messageSubTypeName, instanceName, powerCycle, SIStationSerialNumber, loraMessage, messageData)
                        except Exception as ex:
                            self.shouldReconfigure = True
                            self.wirocLogger.error("Start::handleInput() Error creating message box data")
                            self.wirocLogger.error(ex)
                            continue

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
                                if noOfSecondsToWait is None:
                                    continue  # skip this subscription
                                msgSubscription.Delay = noOfSecondsToWait * 1000000
                                self.wirocLogger.debug('Start::handleInput() Delay: ' + str(noOfSecondsToWait * 1000000))
                                # used for wiroc to wiroc to wait for receiver to send ack first...
                            else:
                                self.wirocLogger.error("Start::handleInput()  SubAdapter not found")

                            msgSubscription.MessageBoxId = mbdid
                            msgSubscription.SubscriptionId = subscription.id
                            if messageID is not None:
                                self.wirocLogger.debug("Start::handleInput() MessageID: " + Utils.GetDataInHex(messageID, logging.DEBUG))
                            # messageid is used for messages from repeater table or test table. Is updated after transform when sent
                            msgSubscription.MessageID = messageID
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
                        destinationHasAcked = loraMessage.GetAckRequested()
                        receivedFromRepeater = loraMessage.GetRepeater()
                        rssiValue = loraMessage.GetRSSIValue()
                        wiRocMode = SettingsClass.GetLoraMode()

                        # block/unblock should be done regardless if this is an ack for message sent from this checkpoint or another
                        if wiRocMode == "SENDER" and receivedFromRepeater:
                            if not destinationHasAcked:
                                # delay an extra message + ack, same as a normal delay after a message is sent
                                # because the repeater should also send and receive ack
                                loraSubAdapter.BlockSendingToLetRepeaterSendAndReceiveAck()
                            else:
                                loraSubAdapter.BlockAfterReceivingAck()
                        else:
                            loraSubAdapter.BlockAfterReceivingAck()

                        if not DatabaseHelper.does_message_id_exist(messageID):
                            # ack is probably an ack of a message sent from another checkpoint or repeater
                            self.wirocLogger.debug("Start::handleInput() Received ack but could not find a message with the id. The ack message id: " + Utils.GetDataInHex(messageID, logging.INFO))
                            # we return instead of continue to get to handleOutput earlier so that we will cut in to send before other wiroc sends its next message.
                            return

                        # Only add success when matching message found
                        if receivedFromRepeater:
                            loraSubAdapter.AddSuccessWithRepeaterBit()
                        else:
                            loraSubAdapter.AddSuccessWithoutRepeaterBit()

                        if wiRocMode == "REPEATER":
                            self.wirocLogger.debug("Start::handleInput() Received ack, for repeater message id: " + Utils.GetDataInHex(messageID, logging.DEBUG))
                            DatabaseHelper.repeater_messages_acked(messageID, rssiValue)  #todo: does this work, is messageID same?
                            DatabaseHelper.archive_repeater_lora_message_subscriptions_after_ack(messageID, rssiValue)
                            if destinationHasAcked:
                                DatabaseHelper.set_ack_received_from_receiver_on_repeater_lora_ack_message_subscription(
                                    messageID)
                        else:
                            self.wirocLogger.debug("Start::handleInput() Received ack, for message id: " + Utils.GetDataInHex(messageID, logging.DEBUG) + " "
                                          + " receivedFromRepeater: " + str(receivedFromRepeater)
                                          + " destinationHasAcked: " + str(destinationHasAcked))
                        DatabaseHelper.archive_message_subscriptions_after_ack(messageID, rssiValue)

    def handleOutput(self, settDict):
        self.wirocLogger.debug("Handle output")
        if self.messagesToSendExists:
            noOfMsgSubWaiting, msgSubBatch = DatabaseHelper.get_message_subscriptions_view_to_send(SettingsClass.GetMaxRetries())
            if noOfMsgSubWaiting == 0:
                self.messagesToSendExists = False
            self.wirocLogger.debug("Handle output no of noOfMsgSubWaiting: " + str(noOfMsgSubWaiting))
            if msgSubBatch is not None:
                self.wirocLogger.debug("Handle output msgSubBatch is not None")
                # self.wirocLogger.info("msgSub count: " + str(len(msgSubscriptions)))
                # find the right adapter
                adapterFound = False
                for subAdapter in self.subscriberAdapters:
                    if (msgSubBatch.SubscriberInstanceName == subAdapter.GetInstanceName() and
                            msgSubBatch.SubscriberTypeName == subAdapter.GetTypeName()):
                        adapterFound = True

                        if subAdapter.IsReadyToSend():
                            # transform the data before sending
                            transformClass = subAdapter.GetTransform(msgSubBatch.TransformName)
                            transformedData = transformClass.Transform(msgSubBatch, subAdapter)
                            if transformedData is not None:
                                if transformedData["MessageID"] is not None:
                                    settDict["MessageID"] = transformedData["MessageID"]
                                    for item in msgSubBatch.MessageSubscriptionBatchItems:
                                        self.wirocLogger.debug("Start::handleOutput() Update MessageID: " + Utils.GetDataInHex(transformedData["MessageID"], logging.DEBUG))
                                        DatabaseHelper.update_messageid(item.id, transformedData["MessageID"])
                                else:
                                    settDict["MessageID"] = None

                                if msgSubBatch.DeleteAfterSent:
                                    # shouldn't wait for ack. (ie. repeater message ack)
                                    self.wirocLogger.debug("In loop: sub adapter: " + str(type(subAdapter)) + " DeleteAfterSent")
                                    settDict["DelayAfterMessageSent"] = 0
                                    settDict["DelayAfterMessageSentWhenAck"] = subAdapter.GetDelayAfterMessageSent()
                                else:
                                    self.wirocLogger.debug("In loop: sub adapter: " + str(type(subAdapter)) + " DelayAfterMessageSent: " + str(subAdapter.GetDelayAfterMessageSent()))
                                    settDict["DelayAfterMessageSent"] = subAdapter.GetDelayAfterMessageSent()
                                    settDict["DelayAfterMessageSentWhenAck"] = settDict["DelayAfterMessageSent"]
                                def createSuccessCB(innerSubAdapter, innerMsgSubBatch):
                                    sentDate = datetime.now()

                                    def successCB():
                                        self.wirocLogger.info(
                                            "Start::Run() successCB() Message sent to " + innerMsgSubBatch.SubscriberInstanceName + " " + innerMsgSubBatch.SubscriberTypeName + " Trans:" + innerMsgSubBatch.TransformName)
                                        if innerMsgSubBatch.DeleteAfterSent:  # move msg subsription to archive
                                            for batchItem in innerMsgSubBatch.MessageSubscriptionBatchItems:
                                                DatabaseHelper.archive_message_subscription_view_after_sent(batchItem.id)
                                        else:  # set SentDate and increment NoOfSendTries
                                            for batchItem in innerMsgSubBatch.MessageSubscriptionBatchItems:
                                                innerRetryDelay = innerSubAdapter.GetRetryDelay(batchItem.NoOfSendTries + 1)
                                                DatabaseHelper.increment_send_tries_and_set_sent_date(batchItem.id, innerRetryDelay, sentDate)
                                                self.wirocLogger.debug("Start::Run() successCB() Sub adapter: " +str(type(innerSubAdapter)) +
                                                                       " Increment send tries, NoOfSendTries: " + str(batchItem.NoOfSendTries) +
                                                                       " retryDelay: " + str(innerRetryDelay))
                                    return successCB

                                def createFailureCB(innerSubAdapter, innerMsgSubBatch):
                                    sendFailureDate = datetime.now()

                                    def failureCB():
                                        # failed to send
                                        for batchItem in innerMsgSubBatch.MessageSubscriptionBatchItems:
                                            self.wirocLogger.warning(
                                                "Start::Run() Failed to send message: " + innerMsgSubBatch.SubscriberInstanceName + " " + innerMsgSubBatch.SubscriberTypeName + " Trans:" + innerMsgSubBatch.TransformName + " batchItem.id:"+ str(batchItem.id))
                                            innerRetryDelay = innerSubAdapter.GetRetryDelay(batchItem.NoOfSendTries + 1)
                                            DatabaseHelper.increment_send_tries_and_set_send_failed_date(batchItem.id, innerRetryDelay, sendFailureDate)
                                            self.wirocLogger.debug(
                                                "Start::Run() failureCB() Subadapter: " + str(type(innerSubAdapter)) +
                                                " Increment send tries, NoOfSendTries: " + str(batchItem.NoOfSendTries) +
                                                " retryDelay: " + str(innerRetryDelay))
                                    return failureCB

                                def createNotSentCB(innerMsgSubBatch):
                                    def notSentCB():
                                        for batchItem in innerMsgSubBatch.MessageSubscriptionBatchItems:
                                            # msg not sent
                                            self.wirocLogger.warning(
                                                "Start::Run() Message was not sent: " + innerMsgSubBatch.SubscriberInstanceName + " " + innerMsgSubBatch.SubscriberTypeName + " Trans:" + innerMsgSubBatch.TransformName + " batchItem.id:"+ str(batchItem.id))
                                            DatabaseHelper.clear_fetched_for_sending(batchItem.id)
                                    return notSentCB

                                t = threading.Thread(target=subAdapter.SendData,
                                                     args=(transformedData["Data"], createSuccessCB(subAdapter, msgSubBatch), createFailureCB(subAdapter, msgSubBatch), createNotSentCB(msgSubBatch), self.callbackQueue, settDict))
                                self.threadQueue.put(t)
                                t.start()
                            else:
                                # shouldn't be sent, so just archive the message subscription
                                # (Probably a Lora message that doesn't request ack
                                for item in msgSubBatch.MessageSubscriptionBatchItems:
                                    self.wirocLogger.debug("Start::Run() " + msgSubBatch.TransformName + " return None so not sent")
                                    DatabaseHelper.archive_message_subscription_view_not_sent(item.id)
                        else:
                            for item in msgSubBatch.MessageSubscriptionBatchItems:
                                DatabaseHelper.clear_fetched_for_sending(item.id)
                            return

                        return

                if not adapterFound:
                    if msgSubBatch.SubscriberInstanceName is None:
                        self.wirocLogger.debug("SubscriberInstanceName none")
                        self.wirocLogger.debug(msgSubBatch.SubscriberTypeName)
                    if msgSubBatch.SubscriberTypeName is None:
                        self.wirocLogger.debug("SubscriberTypeName none")
                    self.wirocLogger.warning(
                        "Start::Run() Send adapter not found for " + msgSubBatch.SubscriberInstanceName + " " + msgSubBatch.SubscriberTypeName)
                    retryDelay = SettingsClass.GetRetryDelay(msgSubBatch.FindAdapterTries + 1)
                    for item in msgSubBatch.MessageSubscriptionBatchItems:
                        DatabaseHelper.increment_find_adapter_tries_and_set_find_adapter_try_date(item.id, retryDelay)

    def updateBatteryIsLow(self):
        if self.webServerUp:
            try:
                apiKey = SettingsClass.GetAPIKey()
                batteryIsLow = Battery.GetIsBatteryLow()
                btAddress = SettingsClass.GetBTAddress()
                webServerURL = SettingsClass.GetWebServerUrl()
                t = threading.Thread(target=self.updateBatteryIsLowBackground, args=(batteryIsLow, webServerURL, apiKey, btAddress))
                t.daemon = True
                t.start()
            except Exception as ex:
                self.wirocLogger.error("Start::updateBatteryIsLow() Exception: " + str(ex))

    def updateBatteryIsLowBackground(self, batteryIsLow, webServerUrl, apiKey, btAddress):
        try:
            headers = {'X-Authorization': apiKey}

            if batteryIsLow and (self.lastBatteryIsLow is None or not (self.lastBatteryIsLow == '1')):
                URL = webServerUrl + "/api/v1/Devices/" + btAddress + "/SetBatteryIsLow"
                resp = requests.get(url=URL, timeout=1, headers=headers,  verify=False)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    self.lastBatteryIsLow = retDevice['batteryIsLow']
            elif not batteryIsLow and (self.lastBatteryIsLow is None or (self.lastBatteryIsLow == '1')):
                URL = webServerUrl + "/api/v1/Devices/" + btAddress + "/SetBatteryIsNormal"
                resp = requests.get(url=URL, timeout=1, headers=headers,  verify=False)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    self.lastBatteryIsLow = retDevice['batteryIsLow']
        except Exception as ex:
            self.wirocLogger.error("Start::updateBatteryIsLowBackground() Exception: " + str(ex))

    def updateBatteryIsLowReceived(self):
        if self.webServerUp:
            try:
                webServerUrl = SettingsClass.GetWebServerUrl()
                apiKey = SettingsClass.GetAPIKey()
                batteryIsLowReceived = SettingsClass.GetBatteryIsLowReceived()
                btAddress = SettingsClass.GetBTAddress()
                t = threading.Thread(target=self.updateBatteryIsLowReceivedBackground, args=(batteryIsLowReceived, webServerUrl, apiKey, btAddress))
                t.daemon = True
                t.start()
            except Exception as ex:
                self.wirocLogger.error("Start::updateBatteryIsLow() Exception: " + str(ex))

    def updateBatteryIsLowReceivedBackground(self, batteryIsLowReceived, webServerUrl, apiKey, btAddress):
        try:
            headers = {'X-Authorization': apiKey}

            if batteryIsLowReceived and (self.lastBatteryIsLowReceived is None or not (self.lastBatteryIsLowReceived=='1')):
                URL = webServerUrl + "/api/v1/Devices/" + btAddress + "/SetBatteryIsLowReceived"
                resp = requests.get(url=URL, timeout=1, headers=headers, verify=False)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    self.lastBatteryIsLowReceived = retDevice['batteryIsLowReceived']
            elif not batteryIsLowReceived and (self.lastBatteryIsLowReceived is None or (self.lastBatteryIsLowReceived=='1')):
                URL = webServerUrl + "/api/v1/Devices/" + btAddress + "/SetBatteryIsNormalReceived"
                resp = requests.get(url=URL, timeout=1, headers=headers, verify=False)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    self.lastBatteryIsLowReceived = retDevice['batteryIsLowReceived']
        except Exception as ex:
            self.wirocLogger.error("Start::updateBatteryIsLowReceivedBackground() Exception: " + str(ex))

    def sendMessageStatsBackground(self, messageStat, webServerUrl, apiKey):
        if messageStat is not None:
            btAddress = SettingsClass.GetBTAddress()
            headers = {'X-Authorization': apiKey}

            if self.webServerUp:
                URL = webServerUrl + "/api/v1/MessageStats"
                messageStatToSend = {"adapterInstance": messageStat.AdapterInstanceName, "BTAddress": btAddress,
                                     "messageType": messageStat.MessageSubTypeName, "status": messageStat.Status,
                                     "noOfMessages": messageStat.NoOfMessages}

                try:
                    resp = requests.post(url=URL, json=messageStatToSend, timeout=1, allow_redirects=False, headers=headers, verify=False)
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
                webServerUrl = SettingsClass.GetWebServerUrl()
                apiKey = SettingsClass.GetAPIKey()
                t = threading.Thread(target=self.sendMessageStatsBackground, args=(messageStat, webServerUrl, apiKey))
                t.daemon = True
                t.start()
            except Exception as ex:
                self.wirocLogger.error("Start::sendMessageStats() Exception: " + str(ex))

    def sendSetConnectedToInternetBackground(self, webServerUrl, apiKey):
        btAddress = SettingsClass.GetBTAddress()
        headers = {'X-Authorization': apiKey}
        URL = webServerUrl + "/api/v1/Devices/" + btAddress + "/SetConnectedToInternetTime"
        try:
            resp = requests.post(url=URL, timeout=1, headers=headers, verify=False)
            if resp.status_code != 200 and resp.status_code != 303:
                self.webServerUp = False
        except Exception as ex:
            self.wirocLogger.error("Start::sendSetConnectedToInternetBackground() Exception: " + str(ex))

    def sendSetConnectedToInternet(self):
        if self.webServerUp:
            try:
                webServerUrl = SettingsClass.GetWebServerUrl()
                apiKey = SettingsClass.GetAPIKey()
                t = threading.Thread(target=self.sendSetConnectedToInternetBackground,
                                     args=(webServerUrl, apiKey))
                t.daemon = True
                t.start()
            except Exception as ex:
                self.wirocLogger.error("Start::sendSetConnectedToInternet() Exception: " + str(ex))

    def handleCallbacks(self):
        try:
            cbt = self.callbackQueue.get(False)
            cb = cbt[0]
            cbargs = cbt[1:]
            #self.wirocLogger.debug("arg: " + str(cbt[0]))
            cb(*cbargs)
        except queue.Empty:
            pass
        except Exception as ex:
            self.wirocLogger.error("Start::handleCallbacks() Exception: " + str(ex))

    def Run(self):
        settDict: dict[str, str | int | None] = {
            "WiRocDeviceName": SettingsClass.GetWiRocDeviceName() if SettingsClass.GetWiRocDeviceName() is not None else "WiRoc Device",
            "SendToSirapIP": SettingsClass.GetSendToSirapIP(),
            "SendToSirapIPPort": SettingsClass.GetSendToSirapIPPort(), "WebServerUrl": SettingsClass.GetWebServerUrl(),
            "ApiKey": SettingsClass.GetAPIKey()}

        self.activeInputAdapters = [inputAdapter for inputAdapter in self.inputAdapters
                                    if inputAdapter.UpdateInfrequently() and inputAdapter.GetIsInitialized()]
        while True:
            for i in range(1,1004):
                didTasks = False
                if i % 11 == 0: # use prime numbers to avoid the tasks happening on the same iteration
                    # Check if button was pressed, if so run doFrequentMaintenanceTasks to update OLED
                    if HardwareAbstraction.Instance.GetIsPMUIRQ():
                        didTasks = True
                        self.doFrequentMaintenanceTasks()

                if i % 149 == 0:
                    # We need to call SettingsClass.Tick() to clear settings cache so new configurations take effect
                    didTasks = True
                    SettingsClass.Tick()
                    self.doFrequentMaintenanceTasks()

                if i % 251 == 0:
                    # print("reconfigure time: " + str(datetime.now()))
                    didTasks = True
                    self.shouldReconfigure = False
                    settDict[
                        "WiRocDeviceName"] = SettingsClass.GetWiRocDeviceName() if SettingsClass.GetWiRocDeviceName() is not None else "WiRoc Device"
                    settDict["SendToSirapIP"] = SettingsClass.GetSendToSirapIP()
                    settDict["SendToSirapIPPort"] = SettingsClass.GetSendToSirapIPPort()
                    settDict["WebServerUrl"] = SettingsClass.GetWebServerUrl()
                    settDict["ApiKey"] = SettingsClass.GetAPIKey()
                    self.reconfigure()
                    self.activeInputAdapters = [inputAdapter for inputAdapter in self.inputAdapters
                                                if inputAdapter.UpdateInfrequently() and inputAdapter.GetIsInitialized()]

                if i % 997 == 0:
                    # print("infrequent maintenance time: " + str(datetime.now()))
                    didTasks = True
                    self.doInfrequentMaintenanceTasks()

                if not didTasks:
                    time.sleep(0.04)
                # print("time: " + str(datetime.now()))
                self.handleInput()
                self.handleOutput(settDict)
                self.sendMessageStats()
                while not self.threadQueue.empty():  # ensure that messages are sent before handleCallbacks. Maybe separate send threads from others in future
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
    # cProfile.run('run()')


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
