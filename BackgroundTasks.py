import time
import traceback

from battery import Battery
from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass
import requests
import threading
import yaml
import logging
from multiprocessing import Process, Queue
from queue import Full, Empty

from subscriberadapters.sendstatusadapter import SendStatusAdapter


class BackgroundTasks(object):
    WiRocLogger: logging.Logger = logging.getLogger('WiRoc')

    def __init__(self):
        self.lastWiRocDeviceNameSentToServer: str | None = None
        self.lastBatteryIsLow: bool | None = None
        self.lastBatteryIsLowReceived: bool | None = None
        self.webServerUpQueue = Queue()
        self.webServerUpQueueCommands = Queue()
        self.messageStatQueueCommands = Queue()
        self.doInfrequentDatabaseTasksQueueCommands = Queue()
        #self.infrequentHTTPTaskWebServerUpQueue = Queue()
        #self.infrequentHTTPTaskBatteryIsLowQueue = Queue()
        #self.infrequentHTTPTaskBatteryIsLowReceivedQueue = Queue()
        self.doInfrequentHTTPTasksQueueCommands = Queue()
        #self.exitHTTPQueue = Queue()

        self.messageStatProcess: Process | None = None
        self.updateWebServerUpProcess: Process | None = None

        self.doInfrequentHTTPTasksBackgroundProcess: Process | None = None
        self.doInfrequentDatabaseTasksBackgroundProcess: Process | None = None

    #def processInfrequentHTTPTaskQueues(self):
    #    try:
    #        while not self.infrequentHTTPTaskWebServerUpQueue.empty():
    #            webServerUp = self.infrequentHTTPTaskWebServerUpQueue.get(False)
    #            SettingsClass.SetWebServerUp(webServerUp)

    #        while not self.infrequentHTTPTaskBatteryIsLowQueue.empty():
    #            self.lastBatteryIsLow = self.infrequentHTTPTaskBatteryIsLowQueue.get(False)

    #        while not self.infrequentHTTPTaskBatteryIsLowReceivedQueue.empty():
    #            self.lastBatteryIsLowReceived = self.infrequentHTTPTaskBatteryIsLowReceivedQueue.get(False)

    #        self.exitHTTPQueue.put("Exit!")
    #    except Exception as ex:
    #        BackgroundTasks.WiRocLogger.error(f"BackgroundTasks::processInfrequentHTTPTaskQueues() exception: {ex}")

    def SendDataToInfrequentHTTPTaskProcess(self):
        batteryIsLow = Battery.GetIsBatteryLow()
        try:
            if batteryIsLow:
                self.doInfrequentHTTPTasksQueueCommands.put("BATTERYISLOW", False)
            else:
                self.doInfrequentHTTPTasksQueueCommands.put("BATTERYISNOTLOW", False)
        except Full as fex:
            BackgroundTasks.WiRocLogger.error(f"BackgroundTasks::SendDataToInfrequentHTTPTaskProcess() doInfrequentHTTPTasksQueueCommands full")

        batteryIsLowReceived = SettingsClass.GetBatteryIsLowReceived()
        try:
            if batteryIsLowReceived:
                self.doInfrequentHTTPTasksQueueCommands.put("BATTERYISLOWRECEIVED", False)
            else:
                self.doInfrequentHTTPTasksQueueCommands.put("BATTERYISLOWNOTRECEIVED", False)
        except Full as fex:
            BackgroundTasks.WiRocLogger.error(f"BackgroundTasks::SendDataToInfrequentHTTPTaskProcess() doInfrequentHTTPTasksQueueCommands full 2")

    def GetDataFromSubProcesses(self):
        try:
            while not self.webServerUpQueue.empty():
                webServerUp = self.webServerUpQueue.get(False)
                BackgroundTasks.WiRocLogger.debug(
                    f"BackgroundTasks::GetDataFromSubProcesses() webServerUp {webServerUp}")
                SettingsClass.SetWebServerUp(webServerUp)
                try:
                    if webServerUp:
                        self.messageStatQueueCommands.put("WEBSERVERUP", False)
                    else:
                        self.messageStatQueueCommands.put("WEBSERVERDOWN", False)
                except Full as fex:
                    BackgroundTasks.WiRocLogger.error(
                        f"BackgroundTasks::GetDataFromSubProcesses() : messageStatQueueCommands FULL")
                    pass
        except Exception as ex:
            BackgroundTasks.WiRocLogger.debug(f"BackgroundTasks::GetDataFromSubProcesses() exception: {ex}")

    def StartInfrequentHTTPTasks(self):
        #self.processInfrequentHTTPTaskQueues()

        # join any old doInfrequentTasksBackgroundProcess
        #if self.doInfrequentHTTPTasksBackgroundProcess is not None:
        #    self.doInfrequentHTTPTasksBackgroundProcess.join()
        #    self.doInfrequentHTTPTasksBackgroundProcess = None

        try:
            if self.doInfrequentHTTPTasksBackgroundProcess is None:
                batteryIsLow = Battery.GetIsBatteryLow()
                batteryIsLowReceived = SettingsClass.GetBatteryIsLowReceived()
                self.doInfrequentHTTPTasksBackgroundProcess = Process(
                    target=BackgroundTasks.DoInfrequentHTTPTasksBackground,
                    args=(self.doInfrequentHTTPTasksQueueCommands,
                          # self.exitHTTPQueue,
                          # self.infrequentHTTPTaskBatteryIsLowQueue,
                          # self.infrequentHTTPTaskBatteryIsLowReceivedQueue,
                          # self.infrequentHTTPTaskWebServerUpQueue,
                          # btAddress,
                          # webServerUrl,
                          # apiKey,
                          batteryIsLow,
                          # self.lastBatteryIsLow,
                          batteryIsLowReceived,
                          # self.lastBatteryIsLowReceived,
                          # wiRocDeviceName,
                          # updateWiRocDevice
                          ),
                    daemon=True)
                self.doInfrequentHTTPTasksBackgroundProcess.start()
            try:
                self.doInfrequentDatabaseTasksQueueCommands.put("START", False)
            except Full as fex:
                BackgroundTasks.WiRocLogger.error(
                    f"BackgroundTasks::StartInfrequentHTTPTasks() doInfrequentDatabaseTasksQueueCommands FULL Exception: {fex}")
        except Exception as ex:
            tb = traceback.format_exc()
            BackgroundTasks.WiRocLogger.error(f"BackgroundTasks::StartInfrequentHTTPTasks() Exception: {ex} StackTrace: {tb}")



        #if SettingsClass.GetWebServerUp():
            #btAddress = SettingsClass.GetBTAddress()
            #webServerUrl = SettingsClass.GetWebServerUrl()
            #apiKey = SettingsClass.GetAPIKey()
        #    batteryIsLow = Battery.GetIsBatteryLow()
        #    batteryIsLowReceived = SettingsClass.GetBatteryIsLowReceived()
            #wiRocDeviceName = SettingsClass.GetWiRocDeviceName() if SettingsClass.GetWiRocDeviceName() is not None else "WiRoc Device"
            #updateWiRocDevice = SettingsClass.GetWebServerUp() and btAddress != "NoBTAddress" and (self.lastWiRocDeviceNameSentToServer != wiRocDeviceName)
            #if updateWiRocDevice:
            #    self.lastWiRocDeviceNameSentToServer = wiRocDeviceName

        #    self.doInfrequentHTTPTasksBackgroundProcess = Process(target=BackgroundTasks.DoInfrequentHTTPTasksBackground,
        #                                                          args=(self.exitHTTPQueue,
        #                                                                self.infrequentHTTPTaskBatteryIsLowQueue,
        #                                                                self.infrequentHTTPTaskBatteryIsLowReceivedQueue,
        #                                                                self.infrequentHTTPTaskWebServerUpQueue,
        #                                                                #btAddress,
        #                                                                #webServerUrl,
        #                                                                #apiKey,
        #                                                                batteryIsLow,
        #                                                                self.lastBatteryIsLow,
        #                                                                batteryIsLowReceived,
        #                                                                self.lastBatteryIsLowReceived,
                                                                        #wiRocDeviceName,
                                                                        #updateWiRocDevice
        #                                                                ),
        #                                                          daemon=True)
        #    self.doInfrequentHTTPTasksBackgroundProcess.start()


    @staticmethod
    def DoInfrequentHTTPTasksBackground(doInfrequentHTTPTasksQueueCommands: Queue,
                                        #batteryIsLowQueue: Queue,
                                        #batteryIsLowReceivedQueue: Queue,
                                        #infrequentWebServerUpQueue: Queue,
                                        #btAddress: str,
                                        #webServerUrl: str,
                                        #apiKey: str,
                                        batteryIsLow: bool,
                                        #lastBatteryIsLow: bool,
                                        batteryIsLowReceived: bool,
                                        #lastBatteryIsLowReceived: bool,
                                        #wiRocDeviceName: str,
                                        #updateWiRocDevice: bool
                                        ):
        BackgroundTasks.WiRocLogger.debug("BackgroundTasks::DoInfrequentDatabaseTasksBackground()")
        lastWiRocDeviceNameSentToServer: str | None = None
        lastBatteryIsLow: bool = not batteryIsLow  # so it saves the new value
        lastBatteryIsLowReceived: bool = not batteryIsLowReceived  # so it saves the new value
        webServerUp = True
        while True:
            try:
                cmd = "START"
                if not doInfrequentHTTPTasksQueueCommands.empty():
                    try:
                        cmd = doInfrequentHTTPTasksQueueCommands.get(False)
                    except Empty:
                        BackgroundTasks.WiRocLogger.debug("BackgroundTasks::DoInfrequentDatabaseTasksBackground() doInfrequentDatabaseTasksQueueCommands is empty")
                        time.sleep(1)
                        continue

                if cmd == "START":
                    if webServerUp:
                        BackgroundTasks.WiRocLogger.debug("BackgroundTasks::doInfrequentHTTPTasksBackground()")
                        btAddress = SettingsClass.GetBTAddress()
                        webServerUrl = SettingsClass.GetWebServerUrl()
                        apiKey = SettingsClass.GetAPIKey()
                        wiRocDeviceName = SettingsClass.GetWiRocDeviceName() if SettingsClass.GetWiRocDeviceName() is not None else "WiRoc Device"
                        updateWiRocDevice = (SettingsClass.GetWebServerUp() and btAddress != "NoBTAddress"
                                             and (lastWiRocDeviceNameSentToServer != wiRocDeviceName))

                        lastBatteryIsLowReceived = BackgroundTasks.UpdateBatteryIsLowReceivedBackground(webServerUrl,
                                                                                                        apiKey,
                                                                                                        batteryIsLowReceived,
                                                                                                        btAddress,
                                                                                                        lastBatteryIsLowReceived)
                        lastBatteryIsLow = BackgroundTasks.UpdateBatteryIsLowBackground(batteryIsLow, webServerUrl, apiKey,
                                                                                        btAddress, lastBatteryIsLow)
                        BackgroundTasks.SendSetConnectedToInternetBackground(webServerUrl, apiKey, btAddress)

                        if updateWiRocDevice:
                            lastWiRocDeviceNameSentToServer = wiRocDeviceName
                            BackgroundTasks.AddDeviceBackground(wiRocDeviceName, btAddress, apiKey, webServerUrl)
                        time.sleep(40)
                elif cmd == "EXIT":
                    return
                elif cmd == "WEBSERVERUP":
                    webServerUp = True
                elif cmd == "WEBSERVERDOWN":
                    webServerUp = False
                elif cmd == "BATTERYISLOW":
                    batteryIsLow = True
                elif cmd == "BATTERYISNOTLOW":
                    batteryIsLow = False
                elif cmd == "BATTERYISLOWRECEIVED":
                    batteryIsLowReceived = True
                elif cmd == "BATTERYISLOWNOTRECEIVED":
                    batteryIsLowReceived = False
            except Exception as ex:
                BackgroundTasks.WiRocLogger.debug(f"BackgroundTasks::DoInfrequentDatabaseTasksBackground() exception: {ex}")
                time.sleep(40)

        #BackgroundTasks.WiRocLogger.debug("BackgroundTasks::doInfrequentHTTPTasksBackground()")
        #BackgroundTasks.UpdateBatteryIsLowReceivedBackground(batteryIsLowReceivedQueue, webServerUrl, apiKey, batteryIsLowReceived, btAddress, lastBatteryIsLowReceived)
        #BackgroundTasks.UpdateBatteryIsLowBackground(batteryIsLowQueue, batteryIsLow, webServerUrl, apiKey, btAddress, lastBatteryIsLow)
        #BackgroundTasks.SendSetConnectedToInternetBackground(infrequentWebServerUpQueue, webServerUrl, apiKey, btAddress)

        #if updateWiRocDevice:
        #    BackgroundTasks.AddDeviceBackground(wiRocDeviceName, btAddress, apiKey, webServerUrl)

        #BackgroundTasks.WiRocLogger.debug("BackgroundTasks::doInfrequentHTTPTasksBackground() wait for exit")
        #exitHTTPQueue.get()
        #BackgroundTasks.WiRocLogger.debug("BackgroundTasks::doInfrequentHTTPTasksBackground() exit")

    @staticmethod
    def UpdateBatteryIsLowBackground(batteryIsLow, webServerURL, apiKey, btAddress, lastBatteryIsLow):
        try:
            headers = {'X-Authorization': apiKey}

            if batteryIsLow and (lastBatteryIsLow is None or not (lastBatteryIsLow == '1')):
                URL = webServerURL + "/api/v1/Devices/" + btAddress + "/SetBatteryIsLow"
                resp = requests.get(url=URL, timeout=1, headers=headers, verify=False)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    batteryIsLow = retDevice['batteryIsLow']
            elif not batteryIsLow and (lastBatteryIsLow is None or (lastBatteryIsLow == '1')):
                URL = webServerURL + "/api/v1/Devices/" + btAddress + "/SetBatteryIsNormal"
                resp = requests.get(url=URL, timeout=1, headers=headers, verify=False)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    batteryIsLow = retDevice['batteryIsLow']
            return batteryIsLow
        except Exception as ex:
            BackgroundTasks.WiRocLogger.error("BackgroundTasks::UpdateBatteryIsLowBackground() Exception: " + str(ex))
            return lastBatteryIsLow

    @staticmethod
    def UpdateBatteryIsLowReceivedBackground(webServerUrl, apiKey, batteryIsLowReceived, btAddress, lastBatteryIsLowReceived) -> bool:
        try:
            headers = {'X-Authorization': apiKey}

            if batteryIsLowReceived and (lastBatteryIsLowReceived is None or not (lastBatteryIsLowReceived == '1')):
                URL = webServerUrl + "/api/v1/Devices/" + btAddress + "/SetBatteryIsLowReceived"
                resp = requests.get(url=URL, timeout=1, headers=headers, verify=False)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    batteryIsLowReceived = retDevice['batteryIsLowReceived']
            elif not batteryIsLowReceived and (lastBatteryIsLowReceived is None or (lastBatteryIsLowReceived == '1')):
                URL = webServerUrl + "/api/v1/Devices/" + btAddress + "/SetBatteryIsNormalReceived"
                resp = requests.get(url=URL, timeout=1, headers=headers, verify=False)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    batteryIsLowReceived = retDevice['batteryIsLowReceived']
            return batteryIsLowReceived
        except Exception as ex:
            BackgroundTasks.WiRocLogger.error(
                "BackgroundTasks::updateBatteryIsLowReceivedBackground() Exception: " + str(ex))
            return lastBatteryIsLowReceived

    @staticmethod
    def SendSetConnectedToInternetBackground(webServerUrl, apiKey, btAddress):
        headers = {'X-Authorization': apiKey}
        URL = webServerUrl + "/api/v1/Devices/" + btAddress + "/SetConnectedToInternetTime"
        try:
            resp = requests.post(url=URL, timeout=2, headers=headers, verify=False)
            if resp.status_code != 200 and resp.status_code != 303:
                BackgroundTasks.WiRocLogger.error(
                    f"BackgroundTasks::SendSetConnectedToInternetBackground() resp.status_code {resp.status_code}")
        except Exception as ex:
            BackgroundTasks.WiRocLogger.error("BackgroundTasks::SendSetConnectedToInternetBackground() Exception: " + str(ex))

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
                      "wirocPythonVersion": wirocPythonVersion, "wirocBLEAPIVersion": wirocBLEAPIVersion,
                      "hardwareVersion": hardwareVersion}
            URL = webServerUrl + "/api/v1/Devices"
            resp = requests.post(url=URL, json=device, timeout=1, headers=headers, verify=False)
            BackgroundTasks.WiRocLogger.warning(
                "BackgroundTasks::AddDeviceBackground resp statuscode btaddress " + btAddress + "  " + str(
                    resp.status_code) + " " + resp.text)
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
            BackgroundTasks.WiRocLogger.warning(
                "BackgroundTasks::AddDeviceBackground error creating device on webserver")
            BackgroundTasks.WiRocLogger.warning("BackgroundTasks::AddDeviceBackground " + str(ex))

    # ################## Database tasks ##############
    def StartInfrequentDatabaseTasks(self):
        try:
            if self.doInfrequentDatabaseTasksBackgroundProcess is None:
                self.doInfrequentDatabaseTasksBackgroundProcess = Process(
                    target=BackgroundTasks.DoInfrequentDatabaseTasksBackground,
                    args=(self.doInfrequentDatabaseTasksQueueCommands,),
                    daemon=True)
                self.doInfrequentDatabaseTasksBackgroundProcess.start()
            try:
                self.doInfrequentDatabaseTasksQueueCommands.put("START", False)
            except Full as fex:
                BackgroundTasks.WiRocLogger.error(
                    f"BackgroundTasks::StartInfrequentDatabaseTasks() doInfrequentDatabaseTasksQueueCommands FULL Exception: {fex}")
        except Exception as ex:
            tb = traceback.format_exc()
            BackgroundTasks.WiRocLogger.error(f"BackgroundTasks::StartInfrequentDatabaseTasks() Exception: {ex} StackTrace: {tb}")

    @staticmethod
    def DoInfrequentDatabaseTasksBackground(doInfrequentDatabaseTasksQueueCommands: Queue):
        BackgroundTasks.WiRocLogger.debug("BackgroundTasks::DoInfrequentDatabaseTasksBackground()")
        while True:
            try:
                cmd = "START"
                if not doInfrequentDatabaseTasksQueueCommands.empty():
                    try:
                        cmd = doInfrequentDatabaseTasksQueueCommands.get(False)
                    except Empty:
                        BackgroundTasks.WiRocLogger.debug("BackgroundTasks::DoInfrequentDatabaseTasksBackground() doInfrequentDatabaseTasksQueueCommands is empty")
                        time.sleep(1)
                        continue

                if cmd == "START":
                    BackgroundTasks.ArchiveFailedMessagesBackground()
                    BackgroundTasks.ArchiveOldRepeaterMessagesBackground()
                elif cmd == "EXIT":
                    return
                time.sleep(40)
            except Exception as ex:
                BackgroundTasks.WiRocLogger.debug(f"BackgroundTasks::DoInfrequentDatabaseTasksBackground() exception: {ex}")
                time.sleep(40)

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

    # ############### message stats #############
    def StartMessageStats(self):
        try:
            if self.messageStatProcess is None:
                self.messageStatProcess = Process(target=BackgroundTasks.SendMessageStatsBackground, args=(self.messageStatQueueCommands, SettingsClass.GetWebServerUp()), daemon=True)
                self.messageStatProcess.start()
            try:
                self.messageStatQueueCommands.put("START",False)
            except Full as fex:
                BackgroundTasks.WiRocLogger.error(
                    f"BackgroundTasks::sendMessageStats() messageStatQueueCommands FULL Exception: {fex}")
        except Exception as ex:
            tb = traceback.format_exc()
            BackgroundTasks.WiRocLogger.error(f"BackgroundTasks::sendMessageStats() Exception: {ex} StackTrace: {tb}")

    @staticmethod
    def SendMessageStatsBackground(messageStatQueueCommands: Queue, webServerUp: bool):
        BackgroundTasks.WiRocLogger.debug("BackgroundTasks::SendMessageStatsBackground() begin")
        while True:
            try:
                cmd = None
                while not messageStatQueueCommands.empty():
                    try:
                        cmd = messageStatQueueCommands.get(False)
                    except Empty:
                        BackgroundTasks.WiRocLogger.debug("BackgroundTasks::SendMessageStatsBackground() messageStatQueueCommands is empty")
                        time.sleep(1)
                        continue

                if cmd == "START":
                    if webServerUp:
                        messageStat = DatabaseHelper.get_message_stat_to_upload()
                        if messageStat is not None:
                            btAddress = SettingsClass.GetBTAddress()
                            webServerUrl = SettingsClass.GetWebServerUrl()
                            apiKey = SettingsClass.GetAPIKey()

                            headers = {'X-Authorization': apiKey}
                            URL = webServerUrl + "/api/v1/MessageStats"
                            messageStatToSend = {"adapterInstance": messageStat.AdapterInstanceName,
                                                 "BTAddress": btAddress,
                                                 "messageType": messageStat.MessageSubTypeName,
                                                 "status": messageStat.Status,
                                                 "noOfMessages": messageStat.NoOfMessages}

                            try:
                                resp = requests.post(url=URL, json=messageStatToSend, timeout=2, allow_redirects=False,
                                                     headers=headers,
                                                     verify=False)
                                if resp.status_code == 200 or resp.status_code == 303:
                                    DatabaseHelper.set_message_stat_uploaded(messageStat.id)
                            except Exception as ex:
                                tb = traceback.format_exc()
                                BackgroundTasks.WiRocLogger.error(
                                    f"BackgroundTasks::SendMessageStatsBackground() Exception: {ex} StackTrace: {tb}")
                elif cmd == "WEBSERVERUP":
                    webServerUp = True
                elif cmd == "WEBSERVERDOWN":
                    webServerUp = False
                elif cmd == "EXIT":
                    return
                time.sleep(1)
            except Exception as ex:
                BackgroundTasks.WiRocLogger.debug(f"BackgroundTasks::SendMessageStatsBackground() exception: {ex}")
                time.sleep(1)

    # ############ WEB SERVER UP ##############
    def StartUpdateWebServerUp(self):
        if SettingsClass.GetSendStatusMessages():
            if self.updateWebServerUpProcess is None:
                webServerUrl = SettingsClass.GetWebServerUrl()
                self.updateWebServerUpProcess = Process(target=self.UpdateWebServerUpBackground, args=(self.webServerUpQueueCommands, self.webServerUpQueue, webServerUrl), daemon=True)
                self.updateWebServerUpProcess.start()

            self.webServerUpQueueCommands.put("CHECK", False)
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
    def UpdateWebServerUpBackground(webServerUpQueueCommands, webServerUpQueue, webServerUrl):
        while True:
            try:
                cmd = "CHECK"
                if not webServerUpQueueCommands.empty():
                    cmd = webServerUpQueueCommands.get(False)
                if cmd == "CHECK":
                    webServerUp: bool = BackgroundTasks.TestConnection(webServerUrl)
                    webServerUpQueue.put(webServerUp)
                elif cmd == "EXIT":
                    return
                time.sleep(15)
            except Exception as ex:
                BackgroundTasks.WiRocLogger.debug(f"BackgroundTasks::UpdateWebServerUpBackground() exception: {ex}")
                webServerUpQueue.put(False)
                time.sleep(1)
