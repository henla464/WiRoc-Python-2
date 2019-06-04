from settings.settings import SettingsClass
from serialcomputer.serialcomputer import SerialComputer
from datamodel.db_helper import DatabaseHelper
import socket
import logging
import os

class SendSerialAdapter(object):
    Instances = []
    SendSerialAdapterActive = None

    @staticmethod
    def CreateInstances():
        serialPorts = []

        if socket.gethostname() == 'chip' or socket.gethostname() == 'nanopiair':
            if os.path.exists('/dev/ttyGS0'):
                serialPorts.append('/dev/ttyGS0')

        if len(serialPorts) > 0:
            if len(SendSerialAdapter.Instances) > 0:
                if SendSerialAdapter.Instances[0].GetSerialDevicePath() != serialPorts[0]:
                    SendSerialAdapter.Instances[0] = SendSerialAdapter(1, serialPorts[0])
                    return True
                else:
                    if SendSerialAdapter.SendSerialAdapterActive is None:
                        return True
                    if SendSerialAdapter.Instances[0].TestConnection():
                        if not SendSerialAdapter.SendSerialAdapterActive:
                            return True
                        else:
                            return False
                    else:
                        if SendSerialAdapter.SendSerialAdapterActive:
                            return True # change, so setup will call init
                        else:
                            return False
            else:
                SendSerialAdapter.Instances.append(SendSerialAdapter(1, serialPorts[0]))
                return True
        else:
            if len(SendSerialAdapter.Instances) > 0:
                SendSerialAdapter.Instances = []
                return True
        return False

    @staticmethod
    def EnableDisableSubscription():
        logging.debug("SendSerialAdapter::EnableDisableSubscription()")
        if len(SendSerialAdapter.Instances) > 0:
            if SendSerialAdapter.Instances[0].TestConnection():
                if SendSerialAdapter.SendSerialAdapterActive is None or not SendSerialAdapter.SendSerialAdapterActive:
                    logging.info("SendSerialAdapter::EnableDisableSubscription() update subscription enable")
                    SendSerialAdapter.SendSerialAdapterActive = True
                    SettingsClass.SetSendSerialAdapterActive(True)
                    DatabaseHelper.update_subscriptions(True, SendSerialAdapter.GetDeleteAfterSent(), SendSerialAdapter.GetTypeName())
                    SettingsClass.SetForceReconfigure(True)
            else:
                if SendSerialAdapter.SendSerialAdapterActive is None or SendSerialAdapter.SendSerialAdapterActive:
                    logging.info("SendSerialAdapter::EnableDisableSubscription() update subscription disable")
                    SendSerialAdapter.SendSerialAdapterActive = False
                    SettingsClass.SetSendSerialAdapterActive(False)
                    DatabaseHelper.update_subscriptions(False, SendSerialAdapter.GetDeleteAfterSent(), SendSerialAdapter.GetTypeName())
                    SettingsClass.SetForceReconfigure(True)
        else:
            logging.debug("SendSerialAdapter::EnableDisableSubscription() Setting SetSendSerialAdapterActive False 2")
            if SettingsClass.GetSendSerialAdapterActive():
                SendSerialAdapter.SendSerialAdapterActive = False
                SettingsClass.SetSendSerialAdapterActive(False)
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
        self.serialComputer = SerialComputer.GetInstance(portName)
        self.transforms = {}
        self.isDBInitialized = False

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
        return ["LoraSIMessageToSITransform", "SISIMessageToSITransform"]

    def SetTransform(self, transformClass):
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName):
        return self.transforms[transformName]

    def TestConnection(self):
        return self.serialComputer.TestConnection()

    def GetIsInitialized(self):
        return self.serialComputer.GetIsInitialized()

    def ShouldBeInitialized(self):
        return not self.serialComputer.GetIsInitialized() and SendSerialAdapter.SendSerialAdapterActive

    # has adapter, transforms, subscriptions etc been added to database?
    def GetIsDBInitialized(self):
        return self.isDBInitialized

    def SetIsDBInitialized(self, val = True):
        self.isDBInitialized = val

    def Init(self):
        return self.serialComputer.Init()

    def IsReadyToSend(self):
        return self.serialComputer.GetIsInitialized()

    @staticmethod
    def GetDelayAfterMessageSent():
        return 0

    def GetRetryDelay(self, tryNo):
        return 1

    # messageData is a bytearray
    def SendData(self, messageData, successCB, failureCB, notSentCB, callbackQueue, settingsDictionary):
        if self.serialComputer.SendData(messageData):
            callbackQueue.put((DatabaseHelper.add_message_stat, self.GetInstanceName(), None, "Sent", 1))
            callbackQueue.put((successCB,))
            dataInHex = ''.join(format(x, '02x') for x in messageData)
            logging.debug("SendSerialAdapter::SendData() Sent to computer, data: " + dataInHex)
            return True
        else:
            callbackQueue.put((DatabaseHelper.add_message_stat, self.GetInstanceName(), None, "NotSent", 0))
            callbackQueue.put((failureCB,))
            logging.warning("SendSerialAdapter::SendData() Could not send to computer")
            #SendSerialAdapter.EnableDisableSubscription()
            return False
