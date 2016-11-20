from dynamicloader.loader import *
from datamodel.datamodel import SubscriberData
from datamodel.datamodel import MessageTypeData
from datamodel.datamodel import SubscriptionData
from datamodel.datamodel import TransformData
from datamodel.db_helper import DatabaseHelper
import logging

class Setup:
    @staticmethod
    def SetupSubscribers():
        modules = Loader.ImportDirectory("subscriberadapters", False)
        adapterObjects = []
        for mod in modules:
            adapterClass = Loader.GetFirstClassFromModule(mod, "Adapter")
            instances = adapterClass.CreateInstances()
            adapterObjects.extend(instances)

        for adapter in adapterObjects:
            if not adapter.GetIsInitialized():
                # add subscriber to the database
                typeName = adapter.GetTypeName()
                instanceName = adapter.GetInstanceName()
                subscriberData = SubscriberData(typeName, instanceName)
                subscriberData = DatabaseHelper.save_subscriber(subscriberData)

                # add message types, transforms and subscriptions to the database
                transformNames = adapter.GetTransformNames()
                for transformName in transformNames:
                    transModule = Loader.ImportModule("transforms." + transformName.lower())
                    if transModule is not None:
                        transformClass = Loader.GetFirstClassFromModule(transModule, "Transform")
                        if transformClass is not None:
                            logging.debug(transformClass)
                            adapter.SetTransform(transformClass)
                            # add message types to database
                            messageTypeName = transformClass.GetInputMessageType()
                            messageTypeData = MessageTypeData(messageTypeName)
                            inputMessageData = DatabaseHelper.save_message_type(messageTypeData)
                            messageTypeName = transformClass.GetOutputMessageType()
                            messageTypeData = MessageTypeData(messageTypeName)
                            outputMessageData = DatabaseHelper.save_message_type(messageTypeData)

                            # add transform to database
                            transformData = TransformData(transformClass.GetName(), inputMessageData.id, outputMessageData.id)
                            transformData = DatabaseHelper.save_transform(transformData)

                            # add subscription to database
                            deleteAfterSent = adapter.GetDeleteAfterSent()
                            enabled = True
                            subscriptionData = SubscriptionData(deleteAfterSent, enabled, subscriberData.id, transformData.id)
                            subscriptionData = DatabaseHelper.save_subscription(subscriptionData)

        for adapterObj in adapterObjects:
            if not adapterObj.Init():
                logging.error("Init adapter failed: " + adapterObj.GetInstanceName())

        return adapterObjects

    @staticmethod
    def SetupInputAdapters(createMessageTypeIfNotExist):
        modules = Loader.ImportDirectory("inputadapters", False)
        adapterObjects = []
        for mod in modules:
            adapterClass = Loader.GetFirstClassFromModule(mod, "Adapter")
            instances = adapterClass.CreateInstances()

            if createMessageTypeIfNotExist:
                # add message types to database
                messageTypeName = adapterClass.GetTypeName()
                messageTypeData = MessageTypeData(messageTypeName)
                DatabaseHelper.save_message_type(messageTypeData)

            adapterObjects.extend(instances)

        for adapterObj in adapterObjects:
            adapterObj.Init()

        return adapterObjects

