from chipGPIO.hardwareAbstraction import HardwareAbstraction
from datamodel.db_helper import DatabaseHelper
from inputadapters.receivesiadapter import ReceiveSIUSBSerialPort
from settings.settings import SettingsClass
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from battery import Battery
import logging
import time
from datetime import datetime, timedelta
from chipGPIO.hardwareAbstraction import HardwareAbstraction


class CreateStatusAdapter(object):
    Instances = []

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction):
        if SettingsClass.GetSendStatusMessages():
            if len(CreateStatusAdapter.Instances) == 0:
                CreateStatusAdapter.Instances.append(CreateStatusAdapter("status1", hardwareAbstraction))
                return True
        else:
            if len(CreateStatusAdapter.Instances) > 0:
                CreateStatusAdapter.Instances = []
                return True
        return False

    @staticmethod
    def GetTypeName():
        return "STATUS"

    def __init__(self, instanceName: str, hardwareAbstraction: HardwareAbstraction):
        self.WiRocLogger = logging.getLogger('WiRoc.Input')
        self.instanceName = instanceName
        self.isInitialized = False
        self.TimeToFetch = False
        self.LastTimeCreated = time.monotonic()
        self.hardwareAbstraction = hardwareAbstraction

    def GetInstanceName(self):
        return self.instanceName

    def GetIsInitialized(self):
        return self.isInitialized

    def ShouldBeInitialized(self):
        return not self.isInitialized

    def Init(self):
        if self.GetIsInitialized():
            return True
        self.isInitialized = True
        return True

    def UpdateInfrequently(self):
        currentTime = time.monotonic()
        self.TimeToFetch = (currentTime - self.LastTimeCreated > SettingsClass.GetStatusMessageInterval())
        return self.TimeToFetch

    def GetData(self):
        if self.TimeToFetch:
            self.LastTimeCreated = time.monotonic()
            self.TimeToFetch = False

            statusIntervalSeconds: int = SettingsClass.GetStatusMessageInterval()
            endTime: datetime = datetime.now()
            startTime: datetime = endTime - timedelta(seconds=statusIntervalSeconds)

            noOfLoraMsgSentNotAcked: int = DatabaseHelper.get_no_of_lora_messages_sent_not_acked(startTime, endTime)
            allLoraPunchesSucceded: bool = DatabaseHelper.get_if_all_lora_punches_succeeded(startTime, endTime)

            SRRDongleRedFound: bool = False
            SRRDongleRedAck: bool = False
            SRRDongleBlueFound: bool = False
            SRRDongleBlueAck: bool = False
            SIMasterConnectedOnUSB1: bool = False
            SIMasterConnectedOnUSB2: bool = False

            a = [inst.portName for inst in ReceiveSIUSBSerialPort.Instances]
            print(a)
            usbInstances: list[ReceiveSIUSBSerialPort] = ReceiveSIUSBSerialPort.Instances
            # first instance
            usb1Instance: ReceiveSIUSBSerialPort | None = next((inst for inst in usbInstances), None)
            if usb1Instance is not None:
                if usb1Instance.GetIsSRRDongle():
                    if usb1Instance.GetSRRChannel() == "RED":
                        SRRDongleRedFound = True
                        SRRDongleRedAck = usb1Instance.GetIsSRRAcking()
                    if usb1Instance.GetSRRChannel() == "BLUE":
                        SRRDongleBlueFound = True
                        SRRDongleBlueAck = usb1Instance.GetIsSRRAcking()
                else:
                    SIMasterConnectedOnUSB1 = True
            else:
                print("USB1 instance none")

            # skip first one, get second
            usb2Instance: ReceiveSIUSBSerialPort | None = next((inst for inst in usbInstances[1:]), None)
            if usb2Instance is not None:
                if usb2Instance.GetIsSRRDongle():
                    if usb2Instance.GetSRRChannel() == "RED":
                        SRRDongleRedFound = True
                        SRRDongleRedAck = usb2Instance.GetIsSRRAcking()
                    if usb2Instance.GetSRRChannel() == "BLUE":
                        SRRDongleBlueFound = True
                        SRRDongleBlueAck = usb2Instance.GetIsSRRAcking()
                else:
                    SIMasterConnectedOnUSB2 = True
            else:
                print("USB2 instance none")

            internalSRRRedEnabled = False
            internalSRRRedAck = True
            internalSRRBlueEnabled = False
            internalSRRBlueAck = True
            internalSRRBlueDirection = False
            internalSRRRedDirection = False
            if self.hardwareAbstraction.HasSRR():
                internalSRRRedEnabled = SettingsClass.GetSRREnabled() and SettingsClass.GetSRRRedChannelEnabled()
                internalSRRRedAck = not SettingsClass.GetSRRRedChannelListenOnly()
                internalSRRBlueEnabled = SettingsClass.GetSRREnabled() and SettingsClass.GetSRRBlueChannelEnabled()
                internalSRRBlueAck = not SettingsClass.GetSRRBlueChannelListenOnly()
                internalSRRBlueDirection = SettingsClass.GetSRRMode() != "RECEIVE"
                internalSRRRedDirection = SettingsClass.GetSRRMode() != "RECEIVE"

            tcpipSirapEnabled = SettingsClass.GetSendToSirapEnabled()
            serialPortBaudRate4800 = SettingsClass.GetForceBTSerial4800BaudRateFromSIStation()
            serialPortDirection = SettingsClass.GetSendSerialAdapterActive()

            msgStatus = LoraRadioMessageCreator.GetStatus2Message(Battery.GetIsBatteryLow(), noOfLoraMsgSentNotAcked,
                                                                  allLoraPunchesSucceded, SRRDongleRedFound, SRRDongleRedAck,
                                                                  SRRDongleBlueFound, SRRDongleBlueAck, SIMasterConnectedOnUSB1, SIMasterConnectedOnUSB2,
                                                                  internalSRRRedEnabled, internalSRRRedAck,
                                                                  internalSRRBlueEnabled, internalSRRBlueAck,
                                                                  internalSRRBlueDirection, internalSRRRedDirection,
                                                                  tcpipSirapEnabled, serialPortBaudRate4800, serialPortDirection)
            self.WiRocLogger.debug("CreateStatusAdapter::GetData() Data to fetch")
            return {"MessageType": "DATA", "MessageSubTypeName": "Status", "MessageSource": "Status", "Data": msgStatus.GetByteArray(), "ChecksumOK": True}
        return None

    def AddedToMessageBox(self, mbid):
        return None
