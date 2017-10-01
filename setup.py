from dynamicloader.loader import *
from datamodel.datamodel import SubscriberData
from datamodel.datamodel import MessageTypeData
from datamodel.datamodel import SubscriptionData
from datamodel.datamodel import TransformData
from datamodel.datamodel import MessageSubscriptionData
from datamodel.db_helper import DatabaseHelper
from subscriberadapters.sendloraadapter import SendLoraAdapter
from subscriberadapters.sendserialadapter import SendSerialAdapter
from subscriberadapters.sendtoblenoadapter import SendToBlenoAdapter
from subscriberadapters.sendtomeosadapter import SendToMeosAdapter
from inputadapters.createstatusadapter import CreateStatusAdapter
from inputadapters.receiveloraadapter import ReceiveLoraAdapter
from inputadapters.receiveserialcomputeradapter import ReceiveSerialComputerAdapter
from inputadapters.receivesiadapter import ReceiveSIAdapter
from inputadapters.receivetestpunchesadapter import ReceiveTestPunchesAdapter
from inputadapters.receiverepeatermessagesadapter import ReceiveRepeaterMessagesAdapter
import logging
from chipGPIO.chipGPIO import *
import socket
from settings.settings import SettingsClass

class Setup:
    SubscriberAdapters = None
    InputAdapters = None
    @staticmethod
    def SetupAdapters(): #createMessageTypeIfNotExist = False):
        subscriberObjects = []
        change1 = SendLoraAdapter.CreateInstances()
        change2 = SendSerialAdapter.CreateInstances()
        change3 = SendToBlenoAdapter.CreateInstances()
        change4 = SendToMeosAdapter.CreateInstances()
        subscriberObjects.extend(SendLoraAdapter.Instances)
        subscriberObjects.extend(SendSerialAdapter.Instances)
        subscriberObjects.extend(SendToBlenoAdapter.Instances)
        subscriberObjects.extend(SendToMeosAdapter.Instances)

        inputObjects = []
        inChange1 = CreateStatusAdapter.CreateInstances()
        inChange2 = ReceiveLoraAdapter.CreateInstances()
        inChange3 = ReceiveSerialComputerAdapter.CreateInstances()
        inChange4 = ReceiveSIAdapter.CreateInstances()
        inChange5 = ReceiveTestPunchesAdapter.CreateInstances()
        inChange6 = ReceiveRepeaterMessagesAdapter.CreateInstances()
        inputObjects.extend(CreateStatusAdapter.Instances)
        inputObjects.extend(ReceiveLoraAdapter.Instances)
        inputObjects.extend(ReceiveSerialComputerAdapter.Instances)
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
            and not change1 and not change2 and not change3 and not change4 and
            not inChange1 and not inChange2 and not inChange3 and not inChange4
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
                            messageTypeData = MessageTypeData(messageTypeName)
                            inputMessageDataId = DatabaseHelper.save_message_type(messageTypeData)
                            messageTypeName = transformClass.GetOutputMessageType()
                            messageTypeData = MessageTypeData(messageTypeName)
                            outputMessageDataId = DatabaseHelper.save_message_type(messageTypeData)

                            # add transform to database
                            transformData = TransformData(transformClass.GetName(), inputMessageDataId, outputMessageDataId)
                            transformDataId = DatabaseHelper.save_transform(transformData)

                            # add subscription to database
                            deleteAfterSent = adapter.GetDeleteAfterSent()
                            waitUntilAckSent = adapter.GetWaitUntilAckSent()
                            waitThisNumberOfBytes = transformClass.GetWaitThisNumberOfBytes()
                            enabled = False
                            subscriptionData = SubscriptionData(deleteAfterSent, enabled, subscriberDataId, transformDataId, waitUntilAckSent, waitThisNumberOfBytes)
                            DatabaseHelper.save_subscription(subscriptionData)
                adapter.SetIsDBInitialized()

        for adapterObj in subscriberObjects:
            logging.debug("Setup::SetupSubscribers() Before Init() subscriber adapter: " + str(adapterObj.GetInstanceName()))
            if not adapterObj.Init():
                logging.error("Setup::SetupSubscribers() Init adapter failed: " + adapterObj.GetInstanceName())
            adapterObj.EnableDisableSubscription()
            adapterObj.EnableDisableTransforms()

        for adapterObj in inputObjects:
            logging.debug("Setup::SetupInputAdapters() Before Init() input adapter: " + str(adapterObj.GetInstanceName()))
            adapterObj.Init()
        DatabaseHelper.update_input_adapter_instances(inputObjects)

        Setup.InputAdapters = inputObjects
        Setup.SubscriberAdapters = subscriberObjects

        return True

    @staticmethod
    def AddMessageTypes():
        #add message types to database
        messageTypeName = CreateStatusAdapter.GetTypeName()
        messageTypeData = MessageTypeData(messageTypeName)
        DatabaseHelper.save_message_type(messageTypeData)

        messageTypeName = ReceiveLoraAdapter.GetTypeName()
        messageTypeData = MessageTypeData(messageTypeName)
        DatabaseHelper.save_message_type(messageTypeData)

        messageTypeName = ReceiveSerialComputerAdapter.GetTypeName()
        messageTypeData = MessageTypeData(messageTypeName)
        DatabaseHelper.save_message_type(messageTypeData)

        messageTypeName = ReceiveSIAdapter.GetTypeName()
        messageTypeData = MessageTypeData(messageTypeName)
        DatabaseHelper.save_message_type(messageTypeData)

        messageTypeName = ReceiveTestPunchesAdapter.GetTypeName()
        messageTypeData = MessageTypeData(messageTypeName)
        DatabaseHelper.save_message_type(messageTypeData)

        messageTypeName = ReceiveRepeaterMessagesAdapter.GetTypeName()
        messageTypeData = MessageTypeData(messageTypeName)
        DatabaseHelper.save_message_type(messageTypeData)

    @staticmethod
    def SetupPins():
        if socket.gethostname() == 'chip':
            pinMode(0, OUTPUT)
            pinMode(1, OUTPUT)
            pinMode(2, OUTPUT)
            pinMode(3, OUTPUT)
            pinMode(4, OUTPUT)
            pinMode(5, OUTPUT)
            pinMode(6, OUTPUT)
            pinMode(7, OUTPUT)
            pinModeNonXIO(138, INPUT)
            pinModeNonXIO(139, OUTPUT)
            digitalWriteNonXIO(139, 1)
