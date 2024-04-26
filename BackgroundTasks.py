from battery import Battery
from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass
import requests
import threading
import yaml
import logging
from multiprocessing import Process, Queue

from subscriberadapters.sendstatusadapter import SendStatusAdapter


class BackgroundTasks(object):
    WiRocLogger: logging.Logger = logging.getLogger('WiRoc')

    def __init__(self):
        self.lastWiRocDeviceNameSentToServer: str | None = None
        self.lastBatteryIsLow: bool | None = None
        self.lastBatteryIsLowReceived: bool | None = None
        self.webServerUpQueue = Queue()
        self.batteryIsLowQueue = Queue()
        self.batteryIsLowReceivedQueue = Queue()
        self.exitHTTPQueue = Queue()

        self.messageStatProcess: Process | None = None
        self.updateWebServerUpProcess: Process | None = None

        self.doInfrequentHTTPTasksBackgroundProcess: Process | None = None
        self.doInfrequentDatabaseTasksBackgroundProcess: Process | None = None

    def processQueues(self):
        try:
            while not self.webServerUpQueue.empty():
                webServerUp = self.webServerUpQueue.get(False)
                SettingsClass.SetWebServerUp(webServerUp)

            while not self.batteryIsLowQueue.empty():
                self.lastBatteryIsLow = self.batteryIsLowQueue.get(False)

            while not self.batteryIsLowReceivedQueue.empty():
                self.lastBatteryIsLowReceived = self.batteryIsLowReceivedQueue.get(False)

            self.exitHTTPQueue.put("Exit!")
        except Exception as ex:
            BackgroundTasks.WiRocLogger.debug(f"BackgroundTasks::processQueues() exception: {ex}")

    def doInfrequentHTTPTasks(self):
        self.processQueues()

        # join any old doInfrequentTasksBackgroundProcess
        if self.doInfrequentHTTPTasksBackgroundProcess is not None:
            self.doInfrequentHTTPTasksBackgroundProcess.join()
            self.doInfrequentHTTPTasksBackgroundProcess = None

        if SettingsClass.GetWebServerUp():
            btAddress = SettingsClass.GetBTAddress()
            webServerUrl = SettingsClass.GetWebServerUrl()
            apiKey = SettingsClass.GetAPIKey()
            batteryIsLow = Battery.GetIsBatteryLow()
            batteryIsLowReceived = SettingsClass.GetBatteryIsLowReceived()
            wiRocDeviceName = SettingsClass.GetWiRocDeviceName() if SettingsClass.GetWiRocDeviceName() is not None else "WiRoc Device"
            updateWiRocDevice = SettingsClass.GetWebServerUp() and btAddress != "NoBTAddress" and (self.lastWiRocDeviceNameSentToServer != wiRocDeviceName)
            if updateWiRocDevice:
                self.lastWiRocDeviceNameSentToServer = wiRocDeviceName

            self.doInfrequentHTTPTasksBackgroundProcess = Process(target=BackgroundTasks.DoInfrequentHTTPTasksBackground,
                                                                  args=(self.exitHTTPQueue, self.batteryIsLowQueue,
                                                                        self.batteryIsLowReceivedQueue,
                                                                        self.webServerUpQueue, btAddress, webServerUrl, apiKey,
                                                                        batteryIsLow, self.lastBatteryIsLow, batteryIsLowReceived,
                                                                        self.lastBatteryIsLowReceived, wiRocDeviceName, updateWiRocDevice))
            self.doInfrequentHTTPTasksBackgroundProcess.start()

    def doInfrequentDatabaseTasks(self):
        if self.doInfrequentDatabaseTasksBackgroundProcess is not None:
            self.doInfrequentDatabaseTasksBackgroundProcess.join()
            self.doInfrequentDatabaseTasksBackgroundProcess = None

        self.doInfrequentHTTPTasksBackgroundProcess = Process(target=BackgroundTasks.DoInfrequentDatabaseTasksBackground,
                                                              args=())
        self.doInfrequentHTTPTasksBackgroundProcess.start()



    @staticmethod
    def DoInfrequentHTTPTasksBackground(exitHTTPQueue: Queue, batteryIsLowQueue: Queue, batteryIsLowReceivedQueue: Queue,
                                    webServerUpQueue: Queue, btAddress: str,
                                    webServerUrl: str, apiKey: str, batteryIsLow: bool,
                                    lastBatteryIsLow: bool, batteryIsLowReceived: bool,
                                    lastBatteryIsLowReceived: bool, wiRocDeviceName: str,
                                    updateWiRocDevice: bool):
        BackgroundTasks.WiRocLogger.debug("BackgroundTasks::doInfrequentHTTPTasksBackground()")
        BackgroundTasks.UpdateBatteryIsLowReceivedBackground(batteryIsLowReceivedQueue, webServerUrl, apiKey, batteryIsLowReceived, btAddress, lastBatteryIsLowReceived)
        BackgroundTasks.UpdateBatteryIsLowBackground(batteryIsLowQueue, batteryIsLow, webServerUrl, apiKey, btAddress, lastBatteryIsLow)
        BackgroundTasks.SendSetConnectedToInternetBackground(webServerUpQueue, webServerUrl, apiKey, btAddress)

        if updateWiRocDevice:
            BackgroundTasks.AddDeviceBackground(wiRocDeviceName, btAddress, apiKey, webServerUrl)

        exitHTTPQueue.get()

    @staticmethod
    def DoInfrequentDatabaseTasksBackground():
        BackgroundTasks.WiRocLogger.debug("BackgroundTasks::doInfrequentDatabaseTasksBackground()")
        BackgroundTasks.ArchiveFailedMessagesBackground()
        BackgroundTasks.ArchiveOldRepeaterMessagesBackground()

    @staticmethod
    def SendMessageStatsBackground(webServerUpQueue, messageStat, btAddress, webServerUrl, apiKey):

            headers = {'X-Authorization': apiKey}

            URL = webServerUrl + "/api/v1/MessageStats"
            messageStatToSend = {"adapterInstance": messageStat.AdapterInstanceName, "BTAddress": btAddress,
                                 "messageType": messageStat.MessageSubTypeName, "status": messageStat.Status,
                                 "noOfMessages": messageStat.NoOfMessages}

            try:
                resp = requests.post(url=URL, json=messageStatToSend, timeout=1, allow_redirects=False, headers=headers, verify=False)
                if resp.status_code == 200 or resp.status_code == 303:
                    DatabaseHelper.set_message_stat_uploaded(messageStat.id)
                else:
                    webServerUpQueue.put(False)
            except Exception as ex:
                BackgroundTasks.WiRocLogger.error("BackgroundTasks::sendMessageStatsBackground() Exception: " + str(ex))

    def sendMessageStats(self):
        self.processQueues()
        if self.messageStatProcess is not None:
            self.messageStatProcess.join()
            self.messageStatProcess = None

        if SettingsClass.GetWebServerUp():
            try:
                messageStat = DatabaseHelper.get_message_stat_to_upload()
                if messageStat is not None:
                    btAddress = SettingsClass.GetBTAddress()
                    webServerUrl = SettingsClass.GetWebServerUrl()
                    apiKey = SettingsClass.GetAPIKey()

                    self.messageStatProcess = Process(target=BackgroundTasks.SendMessageStatsBackground, args=(self.webServerUpQueue, messageStat, btAddress, webServerUrl, apiKey))
                    self.messageStatProcess.start()
            except Exception as ex:
                BackgroundTasks.WiRocLogger.error("BackgroundTasks::sendMessageStats() Exception: " + str(ex))


    @staticmethod
    def AddDeviceBackground(wiRocDeviceName, btAddress, apiKey, webServerUrl):
        try:
            with open("../settings.yaml", "r") as f:
                settings = yaml.load(f, Loader=yaml.BaseLoader)
            wirocPythonVersion = settings['WiRocPythonVersion']
            wirocBLEAPIVersion = settings['WiRocBLEAPIVersion']
            hardwareVersion = settings["WiRocHWVersion"]

            headers = {'X-Authorization': apiKey}
            device = {"BTAddress": btAddress, "headBTAddress": btAddress, "name": wiRocDeviceName,
                      "wirocPythonVersion":wirocPythonVersion, "wirocBLEAPIVersion": wirocBLEAPIVersion,
                      "hardwareVersion": hardwareVersion}
            URL = webServerUrl + "/api/v1/Devices"
            resp = requests.post(url=URL, json=device, timeout=1, headers=headers, verify=False)
            BackgroundTasks.WiRocLogger.warning("BackgroundTasks::AddDeviceBackground resp statuscode btaddress " + btAddress + "  " + str(resp.status_code) + " " + resp.text)
            if resp.status_code == 200:
                BackgroundTasks.WiRocLogger.info(
                    f"BackgroundTasks::AddDeviceBackground resp statuscode: {resp.status_code} btaddress: {btAddress} {resp.text}")
                retDevice = resp.json()
                BackgroundTasks.WiRocLogger.info(
                    f"BackgroundTasks::AddDeviceBackground returned json: {retDevice}")
            else:
                BackgroundTasks.WiRocLogger.warning(
                    f"BackgroundTasks::AddDeviceBackground resp statuscode: {resp.status_code} btaddress: {btAddress} {resp.text}")

        except Exception as ex:
            BackgroundTasks.WiRocLogger.warning("BackgroundTasks::AddDeviceBackground error creating device on webserver")
            BackgroundTasks.WiRocLogger.warning("BackgroundTasks::AddDeviceBackground " + str(ex))

    def updateWebServerUp(self):
        self.processQueues()
        if self.updateWebServerUpProcess is not None:
            self.updateWebServerUpProcess.join()
            self.updateWebServerUpProcess = None

        if SettingsClass.GetSendStatusMessages():
            webServerUrl = SettingsClass.GetWebServerUrl()
            self.updateWebServerUpProcess = Process(target=self.UpdateWebServerUpBackground, args=(self.webServerUpQueue, webServerUrl))
            self.updateWebServerUpProcess.start()
        else:
            SettingsClass.SetWebServerUp(False)

    @staticmethod
    def TestConnection(webServerUrl):
        try:

            URL = webServerUrl + "/api/v1/ping"
            BackgroundTasks.WiRocLogger.debug("BackgroundTasks::TestConnection() " + URL)
            r = requests.get(url=URL, timeout=2, headers={}, verify=False)
            data = r.json()
            BackgroundTasks.WiRocLogger.debug(data)
            return data['code'] == 0
        except Exception as ex:
            SendStatusAdapter.WiRocLogger.error("BackgroundTasks::TestConnection() " + webServerUrl + " Exception: " + str(ex))
            return False

    @staticmethod
    def UpdateWebServerUpBackground(webServerUpQueue, webServerUrl):
        webServerUp: bool = BackgroundTasks.TestConnection(webServerUrl)
        webServerUpQueue.put(webServerUp)

    @staticmethod
    def UpdateBatteryIsLowBackground(batteryIsLowQueue, batteryIsLow, webServerURL, apiKey, btAddress, lastBatteryIsLow):
        try:
            headers = {'X-Authorization': apiKey}

            if batteryIsLow and (lastBatteryIsLow is None or not (lastBatteryIsLow == '1')):
                URL = webServerURL + "/api/v1/Devices/" + btAddress + "/SetBatteryIsLow"
                resp = requests.get(url=URL, timeout=1, headers=headers,  verify=False)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    batteryIsLow = retDevice['batteryIsLow']
                    batteryIsLowQueue.put(batteryIsLow)
            elif not batteryIsLow and (lastBatteryIsLow is None or (lastBatteryIsLow == '1')):
                URL = webServerURL + "/api/v1/Devices/" + btAddress + "/SetBatteryIsNormal"
                resp = requests.get(url=URL, timeout=1, headers=headers,  verify=False)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    batteryIsLow = retDevice['batteryIsLow']
                    batteryIsLowQueue.put(batteryIsLow)
        except Exception as ex:
            BackgroundTasks.WiRocLogger.error("BackgroundTasks::updateBatteryIsLowBackground() Exception: " + str(ex))


    @staticmethod
    def UpdateBatteryIsLowReceivedBackground(batteryIsLowReceivedQueue, webServerUrl, apiKey, batteryIsLowReceived, btAddress, lastBatteryIsLowReceived):
        try:
            headers = {'X-Authorization': apiKey}

            if batteryIsLowReceived and (lastBatteryIsLowReceived is None or not (lastBatteryIsLowReceived == '1')):
                URL = webServerUrl + "/api/v1/Devices/" + btAddress + "/SetBatteryIsLowReceived"
                resp = requests.get(url=URL, timeout=1, headers=headers, verify=False)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    batteryIsLowReceived = retDevice['batteryIsLowReceived']
                    batteryIsLowReceivedQueue.put(batteryIsLowReceived)
            elif not batteryIsLowReceived and (lastBatteryIsLowReceived is None or (lastBatteryIsLowReceived=='1')):
                URL = webServerUrl + "/api/v1/Devices/" + btAddress + "/SetBatteryIsNormalReceived"
                resp = requests.get(url=URL, timeout=1, headers=headers, verify=False)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    batteryIsLowReceived = retDevice['batteryIsLowReceived']
                    batteryIsLowReceivedQueue.put(batteryIsLowReceived)

        except Exception as ex:
            BackgroundTasks.WiRocLogger.error("BackgroundTasks::updateBatteryIsLowReceivedBackground() Exception: " + str(ex))


    @staticmethod
    def SendSetConnectedToInternetBackground(webServerUpQueue, webServerUrl, apiKey, btAddress):
        headers = {'X-Authorization': apiKey}
        URL = webServerUrl + "/api/v1/Devices/" + btAddress + "/SetConnectedToInternetTime"
        try:
            resp = requests.post(url=URL, timeout=1, headers=headers, verify=False)
            if resp.status_code != 200 and resp.status_code != 303:
                webServerUpQueue.put(False)
        except Exception as ex:
            BackgroundTasks.WiRocLogger.error("BackgroundTasks::sendSetConnectedToInternetBackground() Exception: " + str(ex))

    @staticmethod
    def ArchiveOldRepeaterMessagesBackground():
        DatabaseHelper.archive_old_repeater_message()

    @staticmethod
    def ArchiveFailedMessagesBackground():
        msgSubscriptions = DatabaseHelper.get_message_subscriptions_view_to_archive(SettingsClass.GetMaxRetries(),100)
        for msgSub in msgSubscriptions:
            BackgroundTasks.WiRocLogger.info(
                "BackgroundTasks::archiveFailedMessages() subscription reached max tries: " + msgSub.SubscriberInstanceName + " Transform: " + msgSub.TransformName + " msgSubId: " + str(
                    msgSub.id))
            DatabaseHelper.archive_message_subscription_view_not_sent(msgSub.id)