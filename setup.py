from dynamicloader.loader import *
from datamodel.datamodel import SubscriberData
from datamodel.datamodel import MessageTypeData
from datamodel.datamodel import SubscriptionData
from datamodel.datamodel import TransformData
from datamodel.datamodel import MessageSubscriptionData
from datamodel.db_helper import DatabaseHelper
from chipGPIO.hardwareAbstraction import HardwareAbstraction
from inputadapters.createhamcallsignmessageadapter import CreateHAMCallSignMessageAdapter
from inputadapters.resubmitloraadapter import ResubmitLoraAdapter
from subscriberadapters.sendloraadapter import SendLoraAdapter
from subscriberadapters.sendmeshadapter import SendMeshAdapter
from subscriberadapters.sendserialadapter import SendSerialAdapter
from subscriberadapters.sendtoblenoadapter import SendToBlenoAdapter
from subscriberadapters.sendtosirapadapter import SendToSirapAdapter
from subscriberadapters.sendstatusadapter import SendStatusAdapter
from inputadapters.createstatusadapter import CreateStatusAdapter
from inputadapters.receiveloraadapter import ReceiveLoraAdapter
from inputadapters.receivesiadapter import ReceiveSIAdapter
from inputadapters.receivesiadapter import ReceiveSIUSBSerialPort
from inputadapters.receivesiadapter import ReceiveSIHWSerialPort
from inputadapters.receivesiadapter import ReceiveSIBluetoothSP
from inputadapters.receivesrradapter import ReceiveSRRAdapter
from inputadapters.receivetestpunchesadapter import ReceiveTestPunchesAdapter
from inputadapters.receiverepeatermessagesadapter import ReceiveRepeaterMessagesAdapter
#import requests.packages.urllib3.util.connection as urllib3_cn
import urllib3.util.connection as urllib3_cn
import logging
from settings.settings import SettingsClass


class Setup:
    SubscriberAdapters: list[SendLoraAdapter | SendSerialAdapter | SendToBlenoAdapter | SendToSirapAdapter | SendStatusAdapter] = None
    InputAdapters: list[CreateStatusAdapter | ReceiveLoraAdapter | ReceiveSIUSBSerialPort | ReceiveSIHWSerialPort | ReceiveSIBluetoothSP | ReceiveTestPunchesAdapter | ReceiveRepeaterMessagesAdapter | ReceiveSRRAdapter] = None
    WiRocLogger = logging.getLogger('WiRoc')

    @staticmethod
    def SetupAdapters() -> bool:
        subscriberObjects = []
        subscriberAdapterClasses = [SendLoraAdapter, SendSerialAdapter, SendToBlenoAdapter, SendToSirapAdapter, SendStatusAdapter, SendMeshAdapter]
        subscriberAdapterChanged = False
        for subAdpCls in subscriberAdapterClasses:
            if subAdpCls.CreateInstances(HardwareAbstraction.Instance):
                subscriberAdapterChanged = True
                Setup.WiRocLogger.debug(
                    f"Setup::SetupAdapters() Subscriber Adapter TypeName: {subAdpCls.GetTypeName()} changed")
            subscriberObjects.extend(subAdpCls.Instances)

        inputObjects = []
        inputAdapterClasses = [CreateStatusAdapter, ReceiveLoraAdapter, ReceiveSIUSBSerialPort, ReceiveSIHWSerialPort,
                                    ReceiveSIBluetoothSP, ReceiveTestPunchesAdapter, ReceiveRepeaterMessagesAdapter,
                               ReceiveSRRAdapter, ResubmitLoraAdapter, CreateHAMCallSignMessageAdapter]
        inputAdapterChanged = False
        for inputAdpCls in inputAdapterClasses:
            if inputAdpCls.CreateInstances(HardwareAbstraction.Instance):
                inputAdapterChanged = True
                Setup.WiRocLogger.debug(f"Setup::SetupAdapters() Input Adapter TypeName: {inputAdpCls.GetTypeName()} changed")
            inputObjects.extend(inputAdpCls.Instances)

        anyShouldBeInitialized = False
        for inst in subscriberObjects:
            if inst.ShouldBeInitialized():
                Setup.WiRocLogger.debug(f"Setup::SetupAdapters() Should be initialized: {inst.GetInstanceName()}")
                anyShouldBeInitialized = True

        for inst in inputObjects:
            if inst.ShouldBeInitialized():
                Setup.WiRocLogger.debug(f"Setup::SetupAdapters() Should be initialized: {inst.GetInstanceName()}")
                anyShouldBeInitialized = True

        if (not anyShouldBeInitialized and not SettingsClass.GetForceReconfigure()
                and not inputAdapterChanged and not subscriberAdapterChanged):
            # acknowledgementRequested might have changed so that the subscription must be updated.
            for adapterObj in subscriberObjects:
                adapterObj.EnableDisableSubscription()
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
                            batchSize = transformClass.GetBatchSize()
                            messageTypeData = MessageTypeData(messageTypeName, messageSubTypeName)
                            inputMessageDataId = DatabaseHelper.save_message_type(messageTypeData)
                            messageTypeName = transformClass.GetOutputMessageType()
                            messageSubTypeName = transformClass.GetOutputMessageSubType()
                            messageTypeData = MessageTypeData(messageTypeName, messageSubTypeName)
                            outputMessageDataId = DatabaseHelper.save_message_type(messageTypeData)

                            # add transform to database
                            transformData = TransformData(transformClass.GetName(), inputMessageDataId, outputMessageDataId)
                            transformDataId = DatabaseHelper.save_transform(transformData)
                            Setup.WiRocLogger.info("Setup::SetupAdapters() Add transform: %s" %(transformClass.GetName()))

                            # add subscription to database
                            deleteAfterSent = transformClass.GetDeleteAfterSent()
                            enabled = False
                            subscriptionData = SubscriptionData(deleteAfterSent, enabled, subscriberDataId, transformDataId, batchSize)
                            DatabaseHelper.save_subscription(subscriptionData)
                adapter.SetIsDBInitialized()

        for adapterObj in subscriberObjects:

            if not adapterObj.Init():
                Setup.WiRocLogger.error("Setup::SetupAdapters() Init adapter failed: " + adapterObj.GetInstanceName())
            else:
                Setup.WiRocLogger.debug("Setup::SetupAdapters() Initialized subscriber adapter: " + str(adapterObj.GetInstanceName()))
            adapterObj.EnableDisableSubscription()
            adapterObj.EnableDisableTransforms()

        for adapterObj in inputObjects:
            Setup.WiRocLogger.debug("Setup::SetupAdapters() Before Init() input adapter: " + str(adapterObj.GetInstanceName()))
            adapterObj.Init()
        DatabaseHelper.update_input_adapter_instances(inputObjects)

        Setup.InputAdapters = inputObjects
        Setup.SubscriberAdapters = subscriberObjects

        return True

    @staticmethod
    def AddMessageTypes() -> None:
        # add message types to database
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


