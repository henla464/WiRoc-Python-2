from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
import socket
import logging

class SendToMeosAdapter(object):
    Instances = []
    SubscriptionsEnabled = False

    @staticmethod
    def CreateInstances():
        if len(SendToMeosAdapter.Instances) == 0:
            SendToMeosAdapter.Instances.append(SendToMeosAdapter('meos1'))
            return True
        return False

    @staticmethod
    def GetTypeName():
        return "MEOS"

    @staticmethod
    def EnableDisableSubscription():
        if len(SendToMeosAdapter.Instances) > 0:
            isInitialized = SendToMeosAdapter.Instances[0].GetIsInitialized()
            enabled = SettingsClass.GetSendToMeosEnabled()
            subscriptionShouldBeEnabled = (isInitialized and enabled)
            if SendToMeosAdapter.SubscriptionsEnabled != subscriptionShouldBeEnabled:
                logging.info("SendToMeosAdapter::EnableDisableSubscription() subscription set enabled: " + str(subscriptionShouldBeEnabled))
                SendToMeosAdapter.SubscriptionsEnabled = subscriptionShouldBeEnabled
                DatabaseHelper.update_subscriptions(subscriptionShouldBeEnabled, SendToMeosAdapter.GetDeleteAfterSent(), SendToMeosAdapter.GetTypeName())


    @staticmethod
    def EnableDisableTransforms():
        return None

    def __init__(self, instanceName):
        self.instanceName = instanceName
        self.transforms = {}
        self.sock = None
        self.isInitialized = False
        self.isDBInitialized = False

    def GetInstanceName(self):
        return self.instanceName

    @staticmethod
    def GetDeleteAfterSent():
        return True

    def GetIsInitialized(self):
        return self.isInitialized

    # has adapter, transforms, subscriptions etc been added to database?
    def GetIsDBInitialized(self):
        return self.isDBInitialized

    def SetIsDBInitialized(self, val = True):
        self.isDBInitialized = val

    def GetTransformNames(self):
        return ["LoraToMeosTransform", "SIToMeosTransform" ]

    def SetTransform(self, transformClass):
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName):
        return self.transforms[transformName]

    def Init(self):
        if self.GetIsInitialized():
            return True
        self.isInitialized = True
        return True

    # messageData is a bytearray
    def SendData(self, messageData):
        if self.sock is None:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                logging.debug("SendToMeosAdapter::SendData() Address: " + SettingsClass.GetSendToMeosIP() + " Port: " + str(
                    SettingsClass.GetSendToMeosIPPort()))
                server_address = (SettingsClass.GetSendToMeosIP(), SettingsClass.GetSendToMeosIPPort())
                self.sock.settimeout(0.5)
                self.sock.connect(server_address)
                logging.debug("SendToMeosAdapter::SendData() After connect")
            except socket.gaierror as msg:
                logging.error("SendToMeosAdapter::SendData() Address-related error connecting to server: " + str(msg))
                self.sock.close()
                self.sock = None
                #time.sleep(0.1)
                return False
            except socket.error as msg:
                logging.error("SendToMeosAdapter::SendData() Connection error: " + str(msg))
                self.sock.close()
                self.sock = None
                #time.sleep(0.1)
                return False

        try:
            # Send data
            self.sock.sendall(messageData)
            self.sock.close()
            self.sock = None
            logging.debug("SendToMeosAdapter::SendData() Sent to MEOS")
            return True
        except socket.error as msg:
            logging.error(msg)
            self.sock.close()
            self.sock = None
            return False
        except:
            logging.error("SendToMeosAdapter::SendData() Exception")
            return False
