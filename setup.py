from dynamicloader.loader import *
from datamodel.datamodel import SubscriberData
from datamodel.datamodel import MessageTypeData
from datamodel.datamodel import SubscriptionData
from datamodel.datamodel import TransformData
from datamodel.db_helper import DatabaseHelper
from subscriberadapters.sendloraadapter import SendLoraAdapter
from subscriberadapters.sendserialadapter import SendSerialAdapter
from subscriberadapters.sendtoblenoadapter import SendToBlenoAdapter
from subscriberadapters.sendtomeosadapter import SendToMeosAdapter
from inputadapters.createstatusadapter import CreateStatusAdapter
from inputadapters.receiveloraadapter import ReceiveLoraAdapter
from inputadapters.receiveserialcomputeradapter import ReceiveSerialComputerAdapter
from inputadapters.receivesiadapter import ReceiveSIAdapter
import logging
from chipGPIO.chipGPIO import *
import socket

class Setup:
    SubscriberAdapters = None
    InputAdapters = None
    @staticmethod
    def SetupSubscribers():
        adapterObjects = []
        change1 = SendLoraAdapter.CreateInstances()
        change2 = SendSerialAdapter.CreateInstances()
        change3 = SendToBlenoAdapter.CreateInstances()
        change4 = SendToMeosAdapter.CreateInstances()
        if change1 or change2 or change3 or change4:
            adapterObjects.extend(SendLoraAdapter.Instances)
            adapterObjects.extend(SendSerialAdapter.Instances)
            adapterObjects.extend(SendToBlenoAdapter.Instances)
            adapterObjects.extend(SendToMeosAdapter.Instances)
        else:
            allInitialized = True
            for inst in adapterObjects:
                if not inst.GetIsInitialized():
                    allInitialized = False
            if allInitialized:
                return False

        for adapter in adapterObjects:
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
                            enabled = False
                            subscriptionData = SubscriptionData(deleteAfterSent, enabled, subscriberDataId, transformDataId)
                            DatabaseHelper.save_subscription(subscriptionData)
                adapter.SetIsDBInitialized()

        for adapterObj in adapterObjects:
            logging.debug("Setup::SetupSubscribers() Before Init() subscriber adapter: " + str(adapterObj.GetInstanceName()))
            if not adapterObj.Init():
                logging.error("Setup::SetupSubscribers() Init adapter failed: " + adapterObj.GetInstanceName())
            adapterObj.EnableDisableSubscription()
            adapterObj.EnableDisableTransforms()



        Setup.SubscriberAdapters = adapterObjects
        return True

    @staticmethod
    def SetupInputAdapters(createMessageTypeIfNotExist):
        #if Setup.inputAdapterClasses is None:
        #    Setup.inputAdapterClasses = []
        #    modules = Loader.ImportDirectory("inputadapters", False)
        #    for mod in modules:
        #        adapterClass = Loader.GetFirstClassFromModule(mod, "Adapter")
        #        Setup.inputAdapterClasses.append(adapterClass)


        adapterObjects = []
        change1 = CreateStatusAdapter.CreateInstances()
        change2 = ReceiveLoraAdapter.CreateInstances()
        change3 = ReceiveSerialComputerAdapter.CreateInstances()
        change4 = ReceiveSIAdapter.CreateInstances()
        if change1 or change2 or change3 or change4:
            adapterObjects.extend(CreateStatusAdapter.Instances)
            adapterObjects.extend(ReceiveLoraAdapter.Instances)
            adapterObjects.extend(ReceiveSerialComputerAdapter.Instances)
            adapterObjects.extend(ReceiveSIAdapter.Instances)
        else:
            return False

        if createMessageTypeIfNotExist:
            # add message types to database
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

        for adapterObj in adapterObjects:
            logging.debug("Setup::SetupInputAdapters() Before Init() input adapter: " + str(adapterObj.GetInstanceName()))
            adapterObj.Init()
        DatabaseHelper.update_input_adapter_instances(adapterObjects)
        Setup.InputAdapters = adapterObjects
        return True


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
            pinModeNonXIO(139, OUTPUT)
            digitalWriteNonXIO(139, 1)
