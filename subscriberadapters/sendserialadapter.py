from chipGPIO.hardwareAbstraction import HardwareAbstraction
from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
from utils.utils import Utils
import serial
import logging
import threading


class SendSerialAdapter(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')
    Instances = []
    SubscriptionsEnabled = None

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
        serialPorts = HardwareAbstraction.Instance.GetSISerialPorts()

        if len(serialPorts) == 0:
            if len(SendSerialAdapter.Instances) > 0:
                tempInstance = SendSerialAdapter.Instances[0]
                SendSerialAdapter.Instances = []
                try:
                    tempInstance.rs232Serial.close()
                except Exception as ex:
                    SendSerialAdapter.WiRocLogger.debug("SendSerialAdapter:CreateInstances() Close serial failed ex: %s" % ex)
                return True
            return False

        if len(SendSerialAdapter.Instances) > 0:
            if SendSerialAdapter.Instances[0].GetSerialDevicePath() != serialPorts[0]:
                SendSerialAdapter.Instances[0] = SendSerialAdapter(1, serialPorts[0])
                return True
        else:
            SendSerialAdapter.Instances.append(SendSerialAdapter(1, serialPorts[0]))
            return True

        # check if enabled changed => let init/enabledisablesubscription run
        enabled = SettingsClass.GetRS232Mode() == "SEND"
        isInitialized = SendSerialAdapter.Instances[0].GetIsInitialized()
        subscriptionShouldBeEnabled = (isInitialized and enabled)
        if SendSerialAdapter.SubscriptionsEnabled != subscriptionShouldBeEnabled:
            return True
        return False

    @staticmethod
    def GetTypeName():
        return "SERIAL"

    @staticmethod
    def EnableDisableSubscription():
        enabled = SettingsClass.GetRS232Mode() == "SEND"
        shouldSubscriptionBeEnabled = False
        if enabled and len(SendSerialAdapter.Instances) > 0:
            shouldSubscriptionBeEnabled = SendSerialAdapter.Instances[0].GetIsInitialized()
        if SendSerialAdapter.SubscriptionsEnabled != shouldSubscriptionBeEnabled:
            SendSerialAdapter.SubscriptionsEnabled = shouldSubscriptionBeEnabled
            deleteAfterSent = SendSerialAdapter.GetDeleteAfterSent()
            if len(SendSerialAdapter.Instances) > 0:
                for name, transf in SendSerialAdapter.Instances[0].transforms.items():
                    maxTries = transf.GetMaxTries()
                    SendSerialAdapter.WiRocLogger.info("SendSerialAdapter::EnableDisableSubscription() update subscription enabled: " + str(shouldSubscriptionBeEnabled) + " name: " + name + " deleteAfterSent: " + str(deleteAfterSent) + " maxTries: " + str(maxTries))
                    DatabaseHelper.update_subscription(shouldSubscriptionBeEnabled, deleteAfterSent, SendSerialAdapter.GetTypeName(), name, maxTries)
            SettingsClass.SetSendSerialAdapterActive(shouldSubscriptionBeEnabled)

    @staticmethod
    def EnableDisableTransforms():
        enabled = SettingsClass.GetRS232Mode() == "SEND"
        if len(SendSerialAdapter.Instances) > 0:
            for name in SendSerialAdapter.Instances[0].transforms:
                DatabaseHelper.set_transform_enabled(enabled, name)

    def __init__(self, instanceNumber, portName):
        self.instanceNumber = instanceNumber
        self.portName = portName
        self.transforms = {}
        self.isDBInitialized = False
        self.isInitialized = False
        self.rs232Serial = serial.Serial()
        self.serialLock: threading.Lock = threading.Lock()

    def GetInstanceNumber(self):
        return self.instanceNumber

    def GetInstanceName(self):
        return "sndserial" + str(self.instanceNumber)

    def GetSerialDevicePath(self):
        return self.portName

    @staticmethod
    def GetDeleteAfterSent():
        # check setting for ack
        return True

    # when receiving from other WiRoc device, should we wait until the other
    # WiRoc device sent an ack to aviod sending at same time
    @staticmethod
    def GetWaitUntilAckSent():
        return False

    def GetTransformNames(self):
        return ["LoraSIMessageToSITransform", "SISIMessageToSITransform",
                "LoraSIMessageDoubleToSITransform", "SRRSRRMessageToSITransform",
                "SITestTestToSITransform"]

    def SetTransform(self, transformClass):
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName):
        return self.transforms[transformName]

    def GetIsInitialized(self):
        return self.isInitialized

    # TOOD. should return true when baudrate changed
    def ShouldBeInitialized(self):
        return not self.isInitialized and SettingsClass.GetRS232Mode == "SEND"

    # has adapter, transforms, subscriptions etc been added to database?
    def GetIsDBInitialized(self):
        return self.isDBInitialized

    def SetIsDBInitialized(self, val = True):
        self.isDBInitialized = val

    def Init(self):
        if SettingsClass.GetForceRS2324800BaudRateFromSIStation():
            self.rs232Serial.baudrate = 4800
        else:
            self.rs232Serial.baudrate = 38400
        self.rs232Serial.port = self.portName
        if not self.rs232Serial.is_open:
            self.rs232Serial.open()
        if not self.rs232Serial.is_open:
            SendSerialAdapter.WiRocLogger.error("SendSerialAdapter::Init() Serial port not open")
            return False

        self.isInitialized = True
        return True

    def IsReadyToSend(self):
        return self.GetIsInitialized()

    @staticmethod
    def GetDelayAfterMessageSent():
        return 0

    def GetRetryDelay(self, tryNo):
        return 1000000  # 1 second in microseconds

    # messageData is a tuple of bytearrays
    def SendData(self, messageData, successCB, failureCB, notSentCB, settingsDictionary):
        self.serialLock.acquire()
        try:
            returnSuccess = True

            for data in messageData:
                try:
                    self.rs232Serial.write(data)
                    self.rs232Serial.flush()
                    DatabaseHelper.add_message_stat(self.GetInstanceName(), None, "Sent", 1)
                    SendSerialAdapter.WiRocLogger.error(
                        "SendSerialAdapter::SendData() Sent to RS232 Serial, data: " + Utils.GetDataInHex(data, logging.DEBUG))
                except IOError as ioe:
                    returnSuccess = False
                    DatabaseHelper.add_message_stat(self.GetInstanceName(), None, "NotSent", 0)
                    SendSerialAdapter.WiRocLogger.error("SendSerialAdapter::SendData() Could not send to RS232 serial: " + str(ioe))

            if returnSuccess:
                successCB()
                return True
            else:
                failureCB()
                return False
        finally:
            self.serialLock.release()
