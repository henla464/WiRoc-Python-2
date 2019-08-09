from serialcomputer.serialcomputer import SerialComputer
import os
import logging
from constants import *
from utils.utils import Utils
from battery import Battery
from settings.settings import SettingsClass
import random
from datetime import datetime, time, date

class ReceiveSerialComputerAdapter(object):

    Instances = []
    randomSerialNumber = None
    @staticmethod
    def CreateInstances(hardwareAbstraction):
        serialPort = None

        if hardwareAbstraction.runningOnChip or hardwareAbstraction.runningOnChip:
            if os.path.exists('/dev/ttyGS0'):
                serialPort = '/dev/ttyGS0'

        if serialPort is not None:
            if len(ReceiveSerialComputerAdapter.Instances) == 0:
                ReceiveSerialComputerAdapter.Instances.append(
                    ReceiveSerialComputerAdapter('rcvSer1', serialPort))
                return True
            else:
                return False

    @staticmethod
    def GetTypeName():
        return "SERIAL"

    def __init__(self, instanceName, portName):
        self.instanceName = instanceName
        self.portName = portName
        self.serialComputer = SerialComputer.GetInstance(portName)
        if ReceiveSerialComputerAdapter.randomSerialNumber == None:
            ReceiveSerialComputerAdapter.randomSerialNumber = 0xF0000000 + random.randint(0, 0xFFFFFF)

    def GetInstanceName(self):
        return self.instanceName

    def GetSerialDevicePath(self):
        return self.portName

    def GetIsInitialized(self):
        return self.serialComputer.GetIsInitialized()

    def ShouldBeInitialized(self):
        return not self.serialComputer.GetIsInitialized() and self.serialComputer.TestConnection()

    def IsChecksumOK(self, receivedData):
        calculatedCRC = Utils.CalculateCRC(receivedData[1:-3])
        crcInMessage = receivedData[-3:-1]
        return calculatedCRC == crcInMessage

    def Init(self):
        return self.serialComputer.Init()

    def UpdateInfreqently(self):
        return True

    def replyGetSerialNumberSystemValue(self, data):
        address = data["Data"][3]
        numberOfBytesRequested = data["Data"][4]

        replyMessage = bytearray()
        replyMessage.append(STX)  # STX
        replyMessage.append(0x83)
        replyMessage.append(numberOfBytesRequested + 3)  # length
        replyMessage.append(0x03)  # station number 3E7 == 999
        replyMessage.append(0xE7)
        replyMessage.append(address)  # index 5
        sn1 = (ReceiveSerialComputerAdapter.randomSerialNumber >> 24) & 0xFF
        sn2 = (ReceiveSerialComputerAdapter.randomSerialNumber >> 16) & 0xFF
        sn3 = (ReceiveSerialComputerAdapter.randomSerialNumber >> 8) & 0xFF
        sn4 = ReceiveSerialComputerAdapter.randomSerialNumber & 0xFF
        if numberOfBytesRequested >= 1:
            replyMessage.append(sn1)
        if numberOfBytesRequested >= 2:
            replyMessage.append(sn2)
        if numberOfBytesRequested >= 3:
            replyMessage.append(sn3)
        if numberOfBytesRequested >= 4:
            replyMessage.append(sn4)
        for i in range(4, numberOfBytesRequested):
            replyMessage.append(0x00)

        crc = Utils.CalculateCRC(replyMessage[1:])
        replyMessage.append(crc[0])  # crc1
        replyMessage.append(crc[1])  # crc0
        replyMessage.append(ETX)
        return replyMessage


    def replyGetStationSettingSystemValue(self, data):
        # Get system value
        replyMessage = bytearray()
        replyMessage.append(STX)  # STX
        replyMessage.append(0x83)
        address = data["Data"][3]
        numberOfBytesRequested = data["Data"][4]
        replyMessage.append(numberOfBytesRequested + 3)  # length
        replyMessage.append(0x03)  # station number 3E7 == 999
        replyMessage.append(0xE7)
        replyMessage.append(address)  # index 5
        for addr in range(address, address + numberOfBytesRequested):
            if addr == 0x71:  # index 7
                logging.debug("Addr: " + str(addr) + " val 0x02")
                replyMessage.append(0x02)  # control 0x02 (dec 2)
            elif addr == 0x74:  # index 10
                logging.debug("Addr: " + str(addr) + " val 0x03")
                replyMessage.append(0x03)  # 00000011, autosend and extended protocol
            else:  # index 6, 8, 9, 11
                logging.debug("Addr: " + str(addr) + " val 0x00")
                replyMessage.append(0x00)
        crc = Utils.CalculateCRC(replyMessage[1:])
        replyMessage.append(crc[0])  # crc1
        replyMessage.append(crc[1])  # crc0
        replyMessage.append(ETX)
        return replyMessage


    def replyGetBackupPointerSystemValue(self, data):
        address = data["Data"][3]
        numberOfBytesRequested = data["Data"][4]

        replyMessage = bytearray()
        replyMessage.append(STX)  # STX
        replyMessage.append(0x83)
        replyMessage.append(numberOfBytesRequested + 3)  # length
        replyMessage.append(0x03)  # station number 3E7 == 999
        replyMessage.append(0xE7)
        replyMessage.append(address)  # index 5

        curAddr1 = 0x00
        curAddr2 = 0x00
        curAddr3 = 0x00
        curAddr4 = 0x00
        if numberOfBytesRequested >= 1:
            replyMessage.append(curAddr1)
        if numberOfBytesRequested >= 2:
            replyMessage.append(curAddr2)
        if numberOfBytesRequested >= 3:
            replyMessage.append(0x00)
        if numberOfBytesRequested >= 4:
            replyMessage.append(0x00)
        if numberOfBytesRequested >= 5:
            replyMessage.append(0x00)
        if numberOfBytesRequested >= 6:
            replyMessage.append(curAddr3)
        if numberOfBytesRequested >= 7:
            replyMessage.append(curAddr4)
        for i in range(7, numberOfBytesRequested):
            replyMessage.append(0x00)

        crc = Utils.CalculateCRC(replyMessage[1:])
        replyMessage.append(crc[0])  # crc1
        replyMessage.append(crc[1])  # crc0
        replyMessage.append(ETX)
        return replyMessage

    def replyGetBackupPunch(self, data):
        address1 = data["Data"][3]
        address2 = data["Data"][4]
        address3 = data["Data"][5]
        backupMemoryAddress = (address1 << 16) | (address2 << 8) | address3
        numberOfBytesRequested = data["Data"][6]

        replyMessage = bytearray()
        replyMessage.append(STX)  # STX
        replyMessage.append(0x81)
        replyMessage.append(numberOfBytesRequested + 5)  # length
        replyMessage.append(0x03)  # station number 3E7 == 999
        replyMessage.append(0xE7)
        replyMessage.append(address1)
        replyMessage.append(address2)
        replyMessage.append(address3)
        for i in range(0, numberOfBytesRequested):
            replyMessage.append(0x00)

        #crc = Utils.CalculateCRC(replyMessage[1:])
        #replyMessage.append(crc[0])  # crc1
        #replyMessage.append(crc[1])  # crc0
        replyMessage.append(0x00) # add invalid crc, because this doesn't have a correct punch
        replyMessage.append(0x00) # add invalid crc
        replyMessage.append(ETX)
        return replyMessage

    #[0xFF, 0x02, 0x02, 0xF7, 0x00, 0xF7, 0x00, 0x03])
    def replyStationTimeAndStationNumber(self, data):
        replyMessage = bytearray()
        replyMessage.append(STX)  # STX
        replyMessage.append(0xF7)
        replyMessage.append(0x09)  # length
        replyMessage.append(0x03)  # station number 3E7 == 999
        replyMessage.append(0xE7)
        todaysDateTime = datetime.now()
        replyMessage.append(todaysDateTime.year - 2000)
        replyMessage.append(todaysDateTime.month)
        replyMessage.append(todaysDateTime.day)
        if todaysDateTime.time() >= time(hour=12):
            #not sure if it should be > or >= 12
            replyMessage.append(0x01)
        else:
            replyMessage.append(0x00)
        noOfSeconds = todaysDateTime.hour * 3600 + todaysDateTime.minute * 60 + todaysDateTime.second
        replyMessage.append((noOfSeconds & 0xFF00) >> 8)
        replyMessage.append(noOfSeconds & 0xFF)
        tenthOfSecond = int(todaysDateTime.microsecond / 100000)
        replyMessage.append(tenthOfSecond)
        crc = Utils.CalculateCRC(replyMessage[1:])
        replyMessage.append(crc[0])  # crc1
        replyMessage.append(crc[1])  # crc0
        replyMessage.append(ETX)
        return replyMessage

    def replySetTransferMode(self, data):
        # set transfer mode
        replyMessage = bytearray()
        replyMessage.append(STX)  # STX
        replyMessage.append(0xF0)
        replyMessage.append(0x03)  # length
        replyMessage.append(0x03)  # station number 3E7 == 999
        replyMessage.append(0xE7)
        replyMessage.append(0x4D)  # direct communication
        crc = Utils.CalculateCRC(replyMessage[1:])
        replyMessage.append(crc[0])  # crc1
        replyMessage.append(crc[1])  # crc0
        replyMessage.append(ETX)
        return replyMessage

    def handleWiRocToWiRoc(self, data):
        # other WiRoc replied to the I'm a WiRoc device message
        # disable charging to avoid draining the other WiRocs battery
        # or slow the charging. Battery class remember time when charging disabled
        # and restores it in reconfigure call to Tick
        if data["Data"][3] == 0x01:
            # Host WiRoc has power supplied so lets charge too, but slowly
            logging.debug("ReceiveSerialComputerAdapter::GetData() Change to slow charging...")
            Battery.DisableChargingIfBatteryOK()
            Battery.LimitCurrentDrawTo100IfBatteryOK()
        else:
            logging.debug("ReceiveSerialComputerAdapter::GetData() Disable charging...")
            Battery.DisableChargingIfBatteryOK()
            Battery.LimitCurrentDrawTo100IfBatteryOK()
        SettingsClass.SetConnectedComputerIsWiRocDevice()


    # messageData is a bytearray
    def GetData(self):
        data = self.serialComputer.GetData()
        if data is not None:
            if not data["ChecksumOK"]:
                logging.debug("ReceiveSerialComputerAdapter::GetData() Checksum not ok, message thrown away")
                return None

            replyMessage = bytearray()
            commandCode = data["Data"][1]
            replyMessage.append(STX)  # STX
            replyMessage.append(commandCode)
            if commandCode == 0x83:
                # Get system value
                address = data["Data"][3]
                if address == 0x00:
                    replyMessage = self.replyGetSerialNumberSystemValue(data)
                elif address == 0x74:
                    replyMessage = self.replyGetStationSettingSystemValue(data)
                elif address == 0x1C:
                    replyMessage = self.replyGetBackupPointerSystemValue(data)
            elif commandCode ==0x81:
                    replyMessage = self.replyGetBackupPunch(data)
            elif commandCode == 0xF7:
                replyMessage = self.replyStationTimeAndStationNumber(data)
            elif commandCode == 0xF0:
                replyMessage = self.replySetTransferMode(data)
            elif commandCode == 0x01:
                # other WiRoc replied to the I'm a WiRoc device message
                self.handleWiRocToWiRoc(data)
                return None
            else:
                logging.debug("ReceiveSerialComputerAdapter::GetData() Unknown command received")
                return None

            logging.debug("ReceiveSerialComputerAdapter::GetData() Received: " + Utils.GetDataInHex(data["Data"], logging.DEBUG) + " Sending reply message: " + Utils.GetDataInHex(replyMessage, logging.DEBUG))
            try:
                self.serialComputer.SendData(replyMessage)
            except:
                logging.error("ReceiveSerialComputerAdapter::GetData() Error sending reply message")
        return None

    def AddedToMessageBox(self, mbid):
        return None
