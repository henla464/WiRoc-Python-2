from dynamicloader.loader import *
from datamodel.datamodel import SubscriberData
from datamodel.datamodel import MessageTypeData
from datamodel.datamodel import SubscriptionData
from datamodel.datamodel import TransformData
from datamodel.datamodel import MessageSubscriptionData
from datamodel.db_helper import DatabaseHelper
from chipGPIO.hardwareAbstraction import HardwareAbstraction
from subscriberadapters.sendloraadapter import SendLoraAdapter
from subscriberadapters.sendserialadapter import SendSerialAdapter
from subscriberadapters.sendtoblenoadapter import SendToBlenoAdapter
from subscriberadapters.sendtomeosadapter import SendToMeosAdapter
from subscriberadapters.sendstatusadapter import SendStatusAdapter
from inputadapters.createstatusadapter import CreateStatusAdapter
from inputadapters.receiveloraadapter import ReceiveLoraAdapter
from inputadapters.receiveserialcomputeradapter import ReceiveSerialComputerAdapter
from inputadapters.receivesiadapter import ReceiveSIAdapter
from inputadapters.receivetestpunchesadapter import ReceiveTestPunchesAdapter
from inputadapters.receiverepeatermessagesadapter import ReceiveRepeaterMessagesAdapter
#import requests.packages.urllib3.util.connection as urllib3_cn
import urllib3.util.connection as urllib3_cn
import logging
from settings.settings import SettingsClass

class Setup:
    SubscriberAdapters = None
    InputAdapters = None
    WiRocLogger = logging.getLogger('WiRoc')

    @staticmethod
    def SetupInputAdapters():  # createMessageTypeIfNotExist = False):
        inputObjects = []
        inChange1 = CreateStatusAdapter.CreateInstances()  #uses db
        inChange2 = ReceiveLoraAdapter.CreateInstances(HardwareAbstraction.Instance) #doesn't use db, init uses
        inChange3 = ReceiveSerialComputerAdapter.CreateInstances(HardwareAbstraction.Instance) #doesn't use db,
        inChange4 = ReceiveSIAdapter.CreateInstances() #uses db, writes to it
        inChange5 = ReceiveTestPunchesAdapter.CreateInstances() #no doesnt use db
        inChange6 = ReceiveRepeaterMessagesAdapter.CreateInstances() #no doesnt use db
        inputObjects.extend(CreateStatusAdapter.Instances)
        inputObjects.extend(ReceiveLoraAdapter.Instances)
        inputObjects.extend(ReceiveSerialComputerAdapter.Instances)
        inputObjects.extend(ReceiveSIAdapter.Instances)
        inputObjects.extend(ReceiveTestPunchesAdapter.Instances)
        inputObjects.extend(ReceiveRepeaterMessagesAdapter.Instances)

        anyShouldBeInitialized = False
        for inst in inputObjects:
            if inst.ShouldBeInitialized():
                anyShouldBeInitialized = True

        if (not anyShouldBeInitialized and not SettingsClass.GetForceReconfigure()
            and not inChange1 and not inChange2 and not inChange3 and not inChange4
            and not inChange5 and not inChange6):
            return False

        SettingsClass.SetForceReconfigure(False)

        for adapterObj in inputObjects:
            Setup.WiRocLogger.debug(
                "Setup::SetupInputAdapters() Before Init() input adapter: " + str(adapterObj.GetInstanceName()))
            adapterObj.Init()
        DatabaseHelper.update_input_adapter_instances(inputObjects)

        Setup.InputAdapters = inputObjects
        return True

    @staticmethod
    def SetupAdapters(): #createMessageTypeIfNotExist = False):
        subscriberObjects = []
        change1 = SendLoraAdapter.CreateInstances(HardwareAbstraction.Instance)
        #change2 = SendSerialAdapter.CreateInstances()
        change3 = SendToBlenoAdapter.CreateInstances()
        change4 = SendToMeosAdapter.CreateInstances()
        change5 = SendStatusAdapter.CreateInstances()
        subscriberObjects.extend(SendLoraAdapter.Instances)
        #subscriberObjects.extend(SendSerialAdapter.Instances)
        subscriberObjects.extend(SendToBlenoAdapter.Instances)
        subscriberObjects.extend(SendToMeosAdapter.Instances)
        subscriberObjects.extend(SendStatusAdapter.Instances)

        inputObjects = []
        inChange1 = CreateStatusAdapter.CreateInstances()
        inChange2 = ReceiveLoraAdapter.CreateInstances(HardwareAbstraction.Instance)
        #inChange3 = ReceiveSerialComputerAdapter.CreateInstances(HardwareAbstraction.Instance)
        inChange4 = ReceiveSIAdapter.CreateInstances()
        inChange5 = ReceiveTestPunchesAdapter.CreateInstances()
        inChange6 = ReceiveRepeaterMessagesAdapter.CreateInstances()
        inputObjects.extend(CreateStatusAdapter.Instances)
        inputObjects.extend(ReceiveLoraAdapter.Instances)
        #inputObjects.extend(ReceiveSerialComputerAdapter.Instances)
        inputObjects.extend(ReceiveSIAdapter.Instances)
        inputObjects.extend(ReceiveTestPunchesAdapter.Instances)
        inputObjects.extend(ReceiveRepeaterMessagesAdapter.Instances)


        anyShouldBeInitialized = False
        for inst in subscriberObjects:
            if inst.ShouldBeInitialized():
                anyShouldBeInitialized = True

        for inst in inputObjects:
            if inst.ShouldBeInitialized():
                anyShouldBeInitialized = True

        if (not anyShouldBeInitialized and not SettingsClass.GetForceReconfigure()
            and not change1 and not change3 and not change4 and not change5 #and not change2
            and not inChange1 and not inChange2 and not inChange4 #and not inChange3
            and not inChange5 and not inChange6):
            return False

        SettingsClass.SetForceReconfigure(False)

        for adapter in subscriberObjects:
            if not adapter.GetIsDBInitialized():
                # add subscriber to the database
                typeName = adapter.GetTypeName()
                instanceName = adapter.GetInstanceName()
                subscriberData = SubscriberData(typeName, instanceName)
                subscriberDataId = DatabaseHelper.save_subscriber(subscriberData)

                # add message types, transforms and subscriptions to the database
                transformNames = adapter.GetTransformNames()
                for transformName in transformNames:
                    transModule = Loader.ImportModule("transforms." + transformName.lower())
                    if transModule is not None:
                        transformClass = Loader.GetFirstClassFromModule(transModule, "Transform")
                        if transformClass is not None:
                            adapter.SetTransform(transformClass)
                            # add message types to database
                            messageTypeName = transformClass.GetInputMessageType()
                            messageSubTypeName = transformClass.GetInputMessageSubType()
                            messageTypeData = MessageTypeData(messageTypeName, messageSubTypeName)
                            inputMessageDataId = DatabaseHelper.save_message_type(messageTypeData)
                            messageTypeName = transformClass.GetOutputMessageType()
                            messageTypeData = MessageTypeData(messageTypeName, "OUT")
                            outputMessageDataId = DatabaseHelper.save_message_type(messageTypeData)

                            # add transform to database
                            transformData = TransformData(transformClass.GetName(), inputMessageDataId, outputMessageDataId)
                            transformDataId = DatabaseHelper.save_transform(transformData)

                            # add subscription to database
                            deleteAfterSent = transformClass.GetDeleteAfterSent()
                            enabled = False
                            subscriptionData = SubscriptionData(deleteAfterSent, enabled, subscriberDataId, transformDataId)
                            DatabaseHelper.save_subscription(subscriptionData)
                adapter.SetIsDBInitialized()

        for adapterObj in subscriberObjects:
            Setup.WiRocLogger.debug("Setup::SetupSubscribers() Before Init() subscriber adapter: " + str(adapterObj.GetInstanceName()))
            if not adapterObj.Init():
                Setup.WiRocLogger.error("Setup::SetupSubscribers() Init adapter failed: " + adapterObj.GetInstanceName())
            adapterObj.EnableDisableSubscription()
            adapterObj.EnableDisableTransforms()

        for adapterObj in inputObjects:
            Setup.WiRocLogger.debug("Setup::SetupInputAdapters() Before Init() input adapter: " + str(adapterObj.GetInstanceName()))
            adapterObj.Init()
        DatabaseHelper.update_input_adapter_instances(inputObjects)

        Setup.InputAdapters = inputObjects
        Setup.SubscriberAdapters = subscriberObjects

        return True

    @staticmethod
    def AddMessageTypes():
        #add message types to database
        messageTypeName = CreateStatusAdapter.GetTypeName()
        messageSubTypeName = "Status"
        messageTypeData = MessageTypeData(messageTypeName, messageSubTypeName)
        DatabaseHelper.save_message_type(messageTypeData)

        messageTypeName = ReceiveLoraAdapter.GetTypeName()
        messageSubTypeName = "SIMessage"
        messageTypeData = MessageTypeData(messageTypeName, messageSubTypeName)
        DatabaseHelper.save_message_type(messageTypeData)
        messageSubTypeName = "Status"
        messageTypeData = MessageTypeData(messageTypeName, messageSubTypeName)
        DatabaseHelper.save_message_type(messageTypeData)
        messageSubTypeName = "Ack"
        messageTypeData = MessageTypeData(messageTypeName, messageSubTypeName)
        DatabaseHelper.save_message_type(messageTypeData)

        messageTypeName = ReceiveSIAdapter.GetTypeName()
        messageSubTypeName = "LoraRadioMessage"
        messageTypeData = MessageTypeData(messageTypeName, messageSubTypeName)
        DatabaseHelper.save_message_type(messageTypeData)
        messageSubTypeName = "SIMessage"
        messageTypeData = MessageTypeData(messageTypeName, messageSubTypeName)
        DatabaseHelper.save_message_type(messageTypeData)

        messageTypeName = ReceiveTestPunchesAdapter.GetTypeName()
        messageSubTypeName = "Test"
        messageTypeData = MessageTypeData(messageTypeName, messageSubTypeName)
        DatabaseHelper.save_message_type(messageTypeData)

        messageTypeName = ReceiveRepeaterMessagesAdapter.GetTypeName()
        messageSubTypeName = "SIMessage"
        messageTypeData = MessageTypeData(messageTypeName, messageSubTypeName)
        DatabaseHelper.save_message_type(messageTypeData)


