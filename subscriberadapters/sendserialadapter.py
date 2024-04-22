from chipGPIO.hardwareAbstraction import HardwareAbstraction
from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
from utils.utils import Utils
import serial
import logging


class SendSerialAdapter(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')
    Instances = []
    SendSerialAdapterActive = None

    @staticmethod
    def CreateInstances():
        serialPorts = []

        if SettingsClass.GetRS232Mode() == "SEND":
            hwSISerialPorts = HardwareAbstraction.Instance.GetSISerialPorts()
            serialPorts.extend(hwSISerialPorts)

        if len(serialPorts) > 0:
            if len(SendSerialAdapter.Instances) > 0:
                return not SendSerialAdapter.Instances[0].GetIsInitialized()
            else:
                SendSerialAdapter.Instances.append(SendSerialAdapter(1, serialPorts[0]))
                return True
        else:
            if len(SendSerialAdapter.Instances) > 0:
                tempInstance = SendSerialAdapter.Instances[0]
                SendSerialAdapter.Instances = []
                SendSerialAdapter.EnableDisableSubscription()
                try:
                    tempInstance.rs232Serial.close()
                except Exception as ex:
                    SendSerialAdapter.WiRocLogger.debug("SendSerialAdapter:CreateInstances() Close serial failed ex: %s" % ex)

                return True
        return False

    @staticmethod
    def EnableDisableSubscription():
        # called before init
        SendSerialAdapter.WiRocLogger.debug("SendSerialAdapter::EnableDisableSubscription()")
        if len(SendSerialAdapter.Instances) > 0:
            if SendSerialAdapter.Instances[0].GetIsInitialized():
                if SendSerialAdapter.SendSerialAdapterActive is None or not SendSerialAdapter.SendSerialAdapterActive:
                    SendSerialAdapter.WiRocLogger.info("SendSerialAdapter::EnableDisableSubscription() update subscription enable")
                    SendSerialAdapter.SendSerialAdapterActive = True
                    DatabaseHelper.update_subscriptions(True, SendSerialAdapter.GetDeleteAfterSent(), SendSerialAdapter.GetTypeName())
                    SettingsClass.SetForceReconfigure(True)
            else:
                if SendSerialAdapter.SendSerialAdapterActive is None or SendSerialAdapter.SendSerialAdapterActive:
                    SendSerialAdapter.WiRocLogger.info("SendSerialAdapter::EnableDisableSubscription() update subscription disable")
                    SendSerialAdapter.SendSerialAdapterActive = False
                    DatabaseHelper.update_subscriptions(False, SendSerialAdapter.GetDeleteAfterSent(), SendSerialAdapter.GetTypeName())
                    SettingsClass.SetForceReconfigure(True)
        else:
            SendSerialAdapter.WiRocLogger.debug("SendSerialAdapter::EnableDisableSubscription() Setting SetSendSerialAdapterActive False 2")
            SendSerialAdapter.SendSerialAdapterActive = False
            SettingsClass.SetForceReconfigure(True)

    @staticmethod
    def GetTypeName():
        return "SERIAL"

    @staticmethod
    def EnableDisableTransforms():
        return None

    def __init__(self, instanceNumber, portName):
        self.instanceNumber = instanceNumber
        self.portName = portName
        self.transforms = {}
        self.isDBInitialized = False
        self.isInitialized = False
        self.rs232Serial = serial.Serial()

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
        return 1

    # messageData is a tuple of bytearrays
    def SendData(self, messageData, successCB, failureCB, notSentCB, callbackQueue, settingsDictionary):
        returnSuccess = True

        for data in messageData:
            try:
                self.rs232Serial.write(data)
                self.rs232Serial.flush()
                DatabaseHelper.add_message_stat(self.GetInstanceName(), None, "Sent", 1)
                #callbackQueue.put((DatabaseHelper.add_message_stat, self.GetInstanceName(), None, "Sent", 1))
                SendSerialAdapter.WiRocLogger.error(
                    "SendSerialAdapter::SendData() Sent to RS232 Serial, data: " + Utils.GetDataInHex(data, logging.DEBUG))
            except IOError as ioe:
                returnSuccess = False
                DatabaseHelper.add_message_stat(self.GetInstanceName(), None, "NotSent", 0)
                #callbackQueue.put((DatabaseHelper.add_message_stat, self.GetInstanceName(), None, "NotSent", 0))
                SendSerialAdapter.WiRocLogger.error("SendSerialAdapter::SendData() Could not send to RS232 serial: " + str(ioe))

        if returnSuccess:
            successCB()
            #callbackQueue.put((successCB,))
            return True
        else:
            failureCB()
            #callbackQueue.put((failureCB,))
            return False
