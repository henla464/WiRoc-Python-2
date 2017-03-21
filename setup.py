from dynamicloader.loader import *
from datamodel.datamodel import SubscriberData
from datamodel.datamodel import MessageTypeData
from datamodel.datamodel import SubscriptionData
from datamodel.datamodel import TransformData
from datamodel.db_helper import DatabaseHelper
import logging
from chipGPIO.chipGPIO import *
import socket

class Setup:
    subscriberAdapterClasses = None
    inputAdapterClasses = None
    @staticmethod
    def SetupSubscribers():
        if Setup.subscriberAdapterClasses is None:
            Setup.subscriberAdapterClasses = []
            subscriberModules = Loader.ImportDirectory("subscriberadapters", False)

            for mod in subscriberModules:
                adapterClass = Loader.GetFirstClassFromModule(mod, "Adapter")
                Setup.subscriberAdapterClasses.append(adapterClass)

        adapterObjects = []
        for adapterClass in Setup.subscriberAdapterClasses:
            if adapterClass is None:
                logging.debug("Setup::SetupSubscribers() couldn't load subscriber class")
            else:
                instances = adapterClass.CreateInstances()
                adapterObjects.extend(instances)

        for adapter in adapterObjects:
            if not adapter.GetIsDBInitialized():
                # add subscriber to the database
                typeName = adapter.GetTypeName()
                instanceName = adapter.GetInstanceName()
                subscriberData = SubscriberData(typeName, instanceName)
                subscriberDataId = DatabaseHelper.mainDatabaseHelper.save_subscriber(subscriberData)

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
                            inputMessageDataId = DatabaseHelper.mainDatabaseHelper.save_message_type(messageTypeData)
                            messageTypeName = transformClass.GetOutputMessageType()
                            messageTypeData = MessageTypeData(messageTypeName)
                            outputMessageDataId = DatabaseHelper.mainDatabaseHelper.save_message_type(messageTypeData)

                            # add transform to database
                            transformData = TransformData(transformClass.GetName(), inputMessageDataId, outputMessageDataId)
                            transformDataId = DatabaseHelper.mainDatabaseHelper.save_transform(transformData)

                            # add subscription to database
                            deleteAfterSent = adapter.GetDeleteAfterSent()
                            enabled = False
                            subscriptionData = SubscriptionData(deleteAfterSent, enabled, subscriberDataId, transformDataId)
                            DatabaseHelper.mainDatabaseHelper.save_subscription(subscriptionData)

        for adapterObj in adapterObjects:
            adapterObj.SetIsDBInitialized()
            adapterObj.EnableDisableSubscription()
            adapterObj.EnableDisableTransforms()
            logging.debug("Setup::SetupSubscribers() Before Init() subscriber adapter: " + str(adapterObj.GetInstanceName()))
            if not adapterObj.Init():
                logging.error("Setup::SetupSubscribers() Init adapter failed: " + adapterObj.GetInstanceName())

        return adapterObjects

    @staticmethod
    def SetupInputAdapters(createMessageTypeIfNotExist):
        if Setup.inputAdapterClasses is None:
            Setup.inputAdapterClasses = []
            modules = Loader.ImportDirectory("inputadapters", False)
            for mod in modules:
                adapterClass = Loader.GetFirstClassFromModule(mod, "Adapter")
                Setup.inputAdapterClasses.append(adapterClass)

        adapterObjects = []
        for adapterClass in Setup.inputAdapterClasses:
            instances = adapterClass.CreateInstances()

            if createMessageTypeIfNotExist:
                # add message types to database
                messageTypeName = adapterClass.GetTypeName()
                messageTypeData = MessageTypeData(messageTypeName)
                DatabaseHelper.mainDatabaseHelper.save_message_type(messageTypeData)

            adapterObjects.extend(instances)

        for adapterObj in adapterObjects:
            logging.debug("Setup::SetupInputAdapters() Before Init() input adapter: " + str(adapterObj.GetInstanceName()))
            adapterObj.Init()
        DatabaseHelper.mainDatabaseHelper.update_input_adapter_instances(adapterObjects)
        return adapterObjects


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
