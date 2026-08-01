from __future__ import annotations

from typing import Any
from urllib.parse import quote

from chipGPIO.hardwareAbstraction import HardwareAbstraction
from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
import requests
import logging
from datetime import datetime, timedelta

from utils.utils import Utils


class SendToRocAdapter(object):
    WiRocLogger: logging.Logger = logging.getLogger('WiRoc.Output')
    Instances: list[SendToRocAdapter] = []
    SubscriptionsEnabled: bool = False

    ROC_VERSION = "ver7.3"
    MAX_PUNCHES_PER_CALL = 10

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
        if len(SendToRocAdapter.Instances) == 0:
            SendToRocAdapter.Instances.append(SendToRocAdapter('roc1'))
            return True
        # check if enabled changed => let init/enabledisablesubscription run
        isInitialized = SendToRocAdapter.Instances[0].GetIsInitialized()
        enabled = SettingsClass.GetRocEnabled()
        subscriptionShouldBeEnabled = (isInitialized and enabled)
        if SendToRocAdapter.SubscriptionsEnabled != subscriptionShouldBeEnabled:
            return True
        return False

    @staticmethod
    def GetTypeName() -> str:
        return "ROC"

    ROC_TRANSFORM_NAMES = ["LoraSIMessageToRocTransform", "SISIMessageToRocTransform",
                           "SITestTestToRocTransform", "LoraSIMessageDoubleToRocTransform",
                           "SRRSRRMessageToRocTransform"]

    @staticmethod
    def EnableDisableSubscription():
        enabled = SettingsClass.GetRocEnabled()
        subscriptionShouldBeEnabled = enabled
        if SendToRocAdapter.SubscriptionsEnabled != subscriptionShouldBeEnabled:
            SendToRocAdapter.SubscriptionsEnabled = subscriptionShouldBeEnabled
            deleteAfterSent = SendToRocAdapter.GetDeleteAfterSent()
            for name, transf in SendToRocAdapter.Instances[0].transforms.items():
                maxTries = transf.GetMaxTries()
                SendToRocAdapter.WiRocLogger.info(
                    "SendToRocAdapter::EnableDisableSubscription() subscription set enabled: " + str(
                        subscriptionShouldBeEnabled) + " name: " + name + " deleteAfterSent: " + str(deleteAfterSent) +
                        " maxTries: " + str(maxTries))
                DatabaseHelper.update_subscription(subscriptionShouldBeEnabled, deleteAfterSent,
                                                   SendToRocAdapter.GetTypeName(), name, maxTries)

    @staticmethod
    def EnableDisableTransforms() -> None:
        enableTransforms = SettingsClass.GetRocEnabled()
        for name in SendToRocAdapter.ROC_TRANSFORM_NAMES:
            DatabaseHelper.set_transform_enabled(enableTransforms, name)

    def __init__(self, instanceName):
        self.instanceName: str = instanceName
        self.transforms: dict[str, any] = {}
        self.isInitialized: bool = False
        self.isDBInitialized: bool = False

    def GetInstanceName(self) -> str:
        return self.instanceName

    @staticmethod
    def GetDeleteAfterSent() -> bool:
        return True

    @staticmethod
    def GetWaitUntilAckSent() -> bool:
        return False

    def GetIsInitialized(self) -> bool:
        return self.isInitialized

    def ShouldBeInitialized(self) -> bool:
        return not self.isInitialized

    def GetIsDBInitialized(self) -> bool:
        return self.isDBInitialized

    def SetIsDBInitialized(self, val: bool = True) -> None:
        self.isDBInitialized = val

    def GetTransformNames(self) -> list[str]:
        return ["LoraSIMessageToRocTransform", "SISIMessageToRocTransform",
                "SITestTestToRocTransform", "LoraSIMessageDoubleToRocTransform",
                "SRRSRRMessageToRocTransform"]

    def SetTransform(self, transformClass):
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName: str) -> Any:
        return self.transforms[transformName]

    def Init(self) -> bool:
        if self.GetIsInitialized():
            return True
        self.isInitialized = True
        return True

    def IsReadyToSend(self) -> bool:
        return SettingsClass.GetRocEnabled()

    @staticmethod
    def GetDelayAfterMessageSent() -> float:
        return 0

    def GetRetryDelay(self, tryNo: int) -> float:
        return 1000000  # 1 second in microseconds

    @staticmethod
    def _computePunchDate(twentyFourHour: int, hour: int, minute: int, second: int) -> str:
        """Compute punch date from SI 12-hour time + 24h flag.
        Uses the 70-minute rule: if punch time is within 70 minutes ahead of now,
        assume today; otherwise assume yesterday."""
        now = datetime.now()
        # SportIdent time is in 12-hour format. 24h flag means PM if hour < 12.
        punchHour = hour
        if twentyFourHour == 1 and hour < 12:
            punchHour = hour + 12
        elif twentyFourHour == 0 and hour == 12:
            punchHour = 0

        punchTime = now.replace(hour=punchHour, minute=minute, second=second, microsecond=0)
        # If punch time is more than 70 minutes in the future, it must be from yesterday
        if punchTime > now + timedelta(minutes=70):
            punchTime = punchTime - timedelta(days=1)

        return punchTime.strftime("%Y-%m-%d")

    @staticmethod
    def _computePunchTimeStr(hour: int, minute: int, second: int) -> str:
        """Format punch time as HH:MM:SS in 24-hour format."""
        return f"{hour:02d}:{minute:02d}:{second:02d}"

    def SendData(self, messageData: tuple, successCB, failureCB, notSentCB, settingsDictionary: dict[str, any]) -> bool:
        """messageData is a tuple of punch dicts from the transform."""
        try:
            unitId = SettingsClass.GetBTAddress().replace(':', '').lower()
            rocServerUrl = SettingsClass.GetRocServerUrl()
            rocVersion = SendToRocAdapter.ROC_VERSION

            if not unitId or unitId == "NoBTAddress":
                SendToRocAdapter.WiRocLogger.error("SendToRocAdapter::SendData() No BTAddress (unitId)")
                failureCB()
                return False

            punches = messageData
            noOfPunches = len(punches)

            if noOfPunches == 0:
                SendToRocAdapter.WiRocLogger.error("SendToRocAdapter::SendData() No punches to send!")
                failureCB()
                return False

            # Build per-punch params first to compute totalLength
            punchParams = []
            totalLength = 0
            for i, punch in enumerate(punches, start=1):
                twentyFourHour = punch.get("twentyFourHour", 0)
                hour = punch.get("hour", 0)
                minute = punch.get("minute", 0)
                second = punch.get("second", 0)
                subSecondMs = punch.get("subSecondMs", 0)
                stationNumber = punch.get("stationNumber", 0)
                cardNumber = punch.get("cardNumber", 0)

                date = SendToRocAdapter._computePunchDate(twentyFourHour, hour, minute, second)
                timeStr = SendToRocAdapter._computePunchTimeStr(hour, minute, second)
                ms = f"{int(subSecondMs):03d}"
                rawPunchData = punch.get("rawPunchData", "")

                fileValue = f"punch{i}.txt"
                punchParams.append((str(i), fileValue))
                punchParams.append((f"punchdata{i}", rawPunchData))
                punchParams.append((f"control{i}", stationNumber))
                punchParams.append((f"sinumber{i}", cardNumber))
                punchParams.append((f"date{i}", date))
                punchParams.append((f"sitime{i}", timeStr))
                punchParams.append((f"ms{i}", ms))

                totalLength += len(
                    f"&{i}={quote(fileValue)}&punchdata{i}={quote(rawPunchData)}&control{i}={quote(str(stationNumber))}"
                    f"&sinumber{i}={quote(str(cardNumber))}&date{i}={quote(date)}&sitime{i}={quote(timeStr)}&ms{i}={quote(ms)}"
                )

            # Build ordered params: macaddr, length, then per-punch params
            params = [("macaddr", unitId)]
            params.append(("length", str(totalLength)))
            for pp in punchParams:
                params.append(pp)

            URL = f"{rocServerUrl}/{rocVersion}/sendpunches_v2.php"
            fullURL = requests.Request('GET', URL, params=params).prepare().url
            SendToRocAdapter.WiRocLogger.debug(f"SendToRocAdapter::SendData() Full URL: {fullURL}")

            resp = requests.get(url=URL, params=params, timeout=10, verify=False)

            if resp.status_code == 200:
                SendToRocAdapter.WiRocLogger.info(
                    f"SendToRocAdapter::SendData() Sent {noOfPunches} punch(es) to ROC server successfully")
                DatabaseHelper.add_message_stat(self.GetInstanceName(), "Punch", "Sent", noOfPunches)
                successCB()
                return True
            else:
                SendToRocAdapter.WiRocLogger.warning(
                    f"SendToRocAdapter::SendData() ROC server returned status {resp.status_code}: {resp.text}")
                failureCB()
                return False

        except requests.exceptions.Timeout:
            SendToRocAdapter.WiRocLogger.warning("SendToRocAdapter::SendData() Timeout sending to ROC server")
            failureCB()
            return False
        except Exception as ex:
            SendToRocAdapter.WiRocLogger.error(f"SendToRocAdapter::SendData() Exception: {ex}")
            failureCB()
            return False
