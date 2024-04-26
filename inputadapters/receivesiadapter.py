from __future__ import annotations

from multiprocessing import Queue, Process

from settings.settings import SettingsClass
import serial
import logging
from constants import *
from time import sleep
from utils.utils import Utils
from datamodel.datamodel import SIMessage, ErrorCodeData
from datamodel.db_helper import DatabaseHelper
from chipGPIO.hardwareAbstraction import HardwareAbstraction
import serial.tools.list_ports
import socket
import select


class ReceiveSIAdapter(object):
    WiRocLogger: logging.Logger = logging.getLogger('WiRoc.Input')
    AddressOfLastPunch: dict[int, int] = {}
    MSMode: bytes = bytes([0xFF, 0x02, 0xF0, 0x01, 0x4D, 0x6D, 0x0A, 0x03])

    @staticmethod
    def CreateInstances():
        return False

    @staticmethod
    def GetTypeName():
        return "SI"

    def __init__(self, instanceName: str, instanceNumber: int, portName: str):
        self.instanceName: str = instanceName
        self.instanceNumber: int = instanceNumber
        self.portName: str = portName
        self.isInitialized: bool = False
        self.oneWay: bool = False
        self.oneWayFallbackTryReInitWhenDataReceived: bool = False
        self.oneWayFallbackShouldNotTriggerReInit: bool = False
        self.shouldReinitialize: bool = False
        self.siStationNumber: int = 0
        self.hasTimeBeenSet: bool = False
        self.serialNumber: int | None = None
        self.noOfFailedReadsInRow: int = 0
        self.fetchFromBackup: bool = False
        self.fetchFromBackupAddress: int | None = None #exclusive
        self.fetchToBackupAddress: int | None = None #exclusive
        self.isSRRDongle: bool = False

    def GetInstanceName(self) -> str:
        return self.instanceName

    def GetInstanceNumber(self) -> int:
        return self.instanceNumber

    def GetSerialDevicePath(self) -> str:
        return self.portName

    # abstract/virtual method
    def GetIsInitialized(self) -> bool:
        return False

    # abstract/virtual method
    def writeData(self, dataToWrite: bytes) -> None:
        return None

    # abstract/virtual method
    def readData(self, waitMS: int, expectedLength: int) -> tuple[bytearray, bytearray, int]:
        return bytearray(), bytearray(), 0

    # abstract/virtual method
    def Init(self) -> bool:
        return False

    # abstract/virtual method
    def IsDataAvailable(self) -> bool:
        return False

    def ShouldBeInitialized(self) -> bool:
        return not self.GetIsInitialized()

    def IsChecksumOK(self, receivedData: bytearray) -> bool:
        calculatedCRC = Utils.CalculateCRC(receivedData[1:-3])
        crcInMessage = receivedData[-3:-1]
        return calculatedCRC == crcInMessage

    def isCorrectMSModeDirectResponse(self, data: bytearray) -> bool:
        return len(data) == 9 and data[0] == STX and data[5] == 0x4D

    def sendCommand(self, command: bytes, printLog:bool = True):
        if printLog:
            ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::sendCommand: {self.instanceName}: command: " + Utils.GetDataInHex(command, logging.DEBUG))
        writeOK = self.writeData(command)
        if printLog:
            ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::sendCommand: {self.instanceName}: after write. WriteOK: {writeOK}")
        if writeOK:
            response, allData, expectedLength = self.readData(300, 3)
            if printLog:
                ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::sendCommand: {self.instanceName}: response: " + Utils.GetDataInHex(response, logging.DEBUG))
            return response
        else:
            return None

    def GetTimeAsTenthOfSeconds(self, twelveHourTime: bytearray, subSecondsAsTensOfSeconds: int, twentyFourHour: int):
        time = ((twelveHourTime[0] << 8) + twelveHourTime[1]) * 10 + subSecondsAsTensOfSeconds
        if twentyFourHour == 1:
            time += 36000 * 12
        return time

    def getSIStationTimeAndStationNumber(self, printLog:bool = True) -> tuple[int, int, int, int, int, int ,int] | None:
        getTimeCmd = bytes([0xFF, 0x02, 0xF7, 0x00, 0xF7, 0x00, 0x03])
        timeResp = self.sendCommand(getTimeCmd, printLog=printLog)
        if timeResp is None:
            ReceiveSIAdapter.WiRocLogger.error(
                f"ReceiveSIAdapter::getSIStationTimeAndStationNumber: {self.instanceName}: sendCommand returned None")
            return None
        SIMsg = SIMessage()
        SIMsg.AddPayload(timeResp)
        if not SIMsg.GetIsChecksumOK():
            ReceiveSIAdapter.WiRocLogger.error(
                f"ReceiveSIAdapter::getSIStationTimeAndStationNumber: {self.instanceName}: getTimeCmd returned invalid checksum")
            return None
        twelveHourTime = timeResp[9:11]
        subSecondsAsTensOfSeconds = int(timeResp[11] // 25.6)
        twentyFourHour = timeResp[8] & 0x01
        timeAsTenthOfSeconds = self.GetTimeAsTenthOfSeconds(twelveHourTime, subSecondsAsTensOfSeconds, twentyFourHour)
        hour = int(timeAsTenthOfSeconds // 36000)
        numberOfMinutesInTenthOfSecs = (timeAsTenthOfSeconds - hour * 36000)
        minute = numberOfMinutesInTenthOfSecs // 600
        numberOfSecondsInTenthOfSecs = (timeAsTenthOfSeconds - hour * 36000 - minute * 600)
        second = numberOfSecondsInTenthOfSecs // 10
        year = timeResp[5]
        month = timeResp[6]
        day = timeResp[7]
        siStationCode = (timeResp[3] << 8) + timeResp[4]
        return year, month, day, hour, minute, second, siStationCode

    def getStationSettingSystemValue(self) -> tuple[bool | None, bool | None, bool | None, int | None, int | None]:
        getSystemValueCmd = bytes([0xFF, 0x02, 0x83, 0x02, 0x74, 0x01, 0x04, 0x14, 0x03])
        ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::getStationSettingSystemValue: {self.instanceName}:")
        sysValResp = self.sendCommand(getSystemValueCmd, printLog=False)
        if sysValResp is None:
            ReceiveSIAdapter.WiRocLogger.error(
                f"ReceiveSIAdapter::getStationSettingSystemValue: {self.instanceName}: sendCommand returned None")
            return None, None, None, None, None
        configByte = sysValResp[6]
        #   xxxxxxx1b extended protocol
        #   xxxxxx1xb auto send out
        #   xxxxx1xxb handshake (only valid for card readout)
        #   xxx1xxxxb access with password only
        #   1xxxxxxxb read out SI-card after punch (only for punch modes;
        #             depends on bit 2: auto send out or handshake)
        extendedProtocol = ((configByte & 0x01) > 0)
        autoSend = ((configByte & 0x02) > 0)
        readOut = ((configByte & 0x80) > 0)
        stationNumber = (sysValResp[3] << 8) | sysValResp[4]
        ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::getStationSettingSystemValue: {self.instanceName}: response extendedProtocol:{extendedProtocol}, autoSend:{autoSend}, readOut:{readOut}, stationNumber:{stationNumber}, configByte:{configByte}")
        return extendedProtocol, autoSend, readOut, stationNumber, configByte

    def getStationSettingModelValue(self) -> bytearray | None:
        getSystemValueCmd = bytes([0xFF, 0x02, 0x83, 0x02, 0x0B, 0x02, 0x06, 0x18, 0x03])
        ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::getStationSettingModelValue: {self.instanceName}:")
        sysValResp = self.sendCommand(getSystemValueCmd, printLog=False)
        if sysValResp is None:
            ReceiveSIAdapter.WiRocLogger.error(
                f"ReceiveSIAdapter::getStationSettingModelValue: {self.instanceName}: sendCommand returned None")
            return None
        model0 = sysValResp[6]
        model1 = sysValResp[7]
        modelNumber = bytearray([model0, model1])
        ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::getStationSettingModelValue: {self.instanceName}: modelNumber:" + Utils.GetDataInHex(modelNumber, logging.DEBUG))
        return modelNumber

    def getSerialNumberSystemValue(self) -> int | None:
        addr = 0x00
        cmdLength = 0x02
        noOfBytesToRead = 0x04
        getSerialNumberSystemValueCmd = bytes([0xFF, 0x02, 0x02, 0x83, cmdLength, addr, noOfBytesToRead, 0xbc, 0x0f, 0x03])
        ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::getSerialNumberSystemValue: {self.instanceName}:")
        serialNumberArray = self.sendCommand(getSerialNumberSystemValueCmd, printLog=False)
        if serialNumberArray is None:
            ReceiveSIAdapter.WiRocLogger.error(
                "ReceiveSIAdapter::getSerialNumberSystemValue sendCommand returned None")
            return None
        ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::getSerialNumberSystemValue: {self.instanceName}: data: " + Utils.GetDataInHex(serialNumberArray, logging.DEBUG))
        serialNumber = serialNumberArray[6] << 24 | serialNumberArray[7] << 16 | serialNumberArray[8] << 8 | serialNumberArray[9]
        ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::getSerialNumberSystemValue: {self.instanceName}: serialNumber: " + str(serialNumber))
        return serialNumber

    def getBackupPunchAsSIMessageArray(self, address: int) -> None | bytearray:
        if self.siStationNumber is None:
            self.siStationNumber = self.getStationSettingSystemValue()[3]
        addressArr = [((address >> 16) & 0xFF), ((address >> 8) & 0xFF), (address & 0xFF)]
        getBackupPunchCmdArr = [0xFF, 0x02, 0x02, 0x81, 0x04, addressArr[0], addressArr[1], addressArr[2], 0x08, 0x00, 0x00, 0x03]
        crc = Utils.CalculateCRC(bytearray(bytes(getBackupPunchCmdArr[3:-3])))
        getBackupPunchCmdArr[9] = crc[0]
        getBackupPunchCmdArr[10] = crc[1]
        ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::getBackupPunchAsSIMessageArray")
        backupPunchRecord = self.sendCommand(bytes(getBackupPunchCmdArr), printLog=False)
        if backupPunchRecord is None:
            ReceiveSIAdapter.WiRocLogger.error(
                "ReceiveSIAdapter::getBackupPunchAsSIMessageArray could not fetch backup punch record")
            return None
        SIMsg = SIMessage()
        SIMsg.AddPayload(backupPunchRecord)
        if not SIMsg.GetIsChecksumOK():
            ReceiveSIAdapter.WiRocLogger.error(
                "ReceiveSIAdapter::getBackupPunchAsSIMessageArray getBackupPunchCmd returned invalid checksum")
            return None

        twentyFourHour = backupPunchRecord[12] & 0x01

        siMsg = SIMessage()
        siMsg.AddHeader(SIMessage.SIPunch)
        siMsg.AddByte((self.siStationNumber >> 8) & 0xFF)
        siMsg.AddByte(self.siStationNumber & 0xFF)
        siMsg.AddByte(0)
        siMsg.AddByte(backupPunchRecord[8])
        siMsg.AddByte(backupPunchRecord[9])
        siMsg.AddByte(backupPunchRecord[10])
        siMsg.AddByte(twentyFourHour)
        siMsg.AddByte(backupPunchRecord[13])
        siMsg.AddByte(backupPunchRecord[14])
        siMsg.AddByte(backupPunchRecord[15])
        siMsg.AddFooter()
        siMsgByteArr = siMsg.GetByteArray()
        ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::getBackupPunchAsSIMessageArray SIMsg created from backup punch: " + Utils.GetDataInHex(siMsgByteArr, logging.DEBUG))
        return siMsgByteArr

    def setAutosendAndExtendedProtocol(self) -> None:
        extendedProtocol, autoSend, readOut, stationNumber, configByte = self.getStationSettingSystemValue()
        if autoSend is not None and extendedProtocol is not None and (not autoSend or not extendedProtocol):
            configByte = configByte | 0b00000001
            configByte = configByte | 0b00000010
            setSystemValueCmdData = bytes([0x82, 0x02, 0x74, configByte])
            calculatedCrc = Utils.CalculateCRC(bytearray(setSystemValueCmdData))
            setSystemValueCmd = bytes([0xFF, 0x02, 0x02]) + setSystemValueCmdData + bytes([calculatedCrc[0]]) + bytes([calculatedCrc[1]]) + bytes([0x03])
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::setAutosendAndExtendedProtocol()")
            response = self.sendCommand(setSystemValueCmd, printLog=False)
            if response is None:
                ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::setAutosendAndExtendedProtocol() sendCommand returned None")
                return
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::setAutosendAndExtendedProtocol(): response: " + Utils.GetDataInHex(response, logging.DEBUG))

    def updateComputerTime(self) -> None:
        theCurrentTimeInSiStation = self.getSIStationTimeAndStationNumber(printLog=False)
        ReceiveSIAdapter.WiRocLogger.debug(
            "ReceiveSIAdapter::updateComputerTime time to set: " + str(2000+theCurrentTimeInSiStation[0]) + "-" +
            str(theCurrentTimeInSiStation[1]) + "-" + str(theCurrentTimeInSiStation[2]) + "  " +
            str(theCurrentTimeInSiStation[3]) + ":" + str(theCurrentTimeInSiStation[4]) + ":" + str(theCurrentTimeInSiStation[5]))
        try:
            Utils.SetDateTime(2000+theCurrentTimeInSiStation[0], theCurrentTimeInSiStation[1], theCurrentTimeInSiStation[2], theCurrentTimeInSiStation[3], theCurrentTimeInSiStation[4], theCurrentTimeInSiStation[5])
        except Exception as ex:
            # If month = 0 then battery is probably dead. Can't set
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::updateComputerTime exception: " + str(ex))
        SettingsClass.SetTimeOfLastMessageSentToLora()
        DatabaseHelper.change_future_created_dates()
        DatabaseHelper.change_future_sent_dates()

    def updateSiStationNumber(self) -> None:
        ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::updateSiStationNumber: {self.instanceName}:")
        theCurrentTimeInSiStation = self.getSIStationTimeAndStationNumber(printLog=False)
        ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::updateSiStationNumber: {self.instanceName}: stationNumber: " + str(theCurrentTimeInSiStation[6]))
        self.siStationNumber = theCurrentTimeInSiStation[6]
        SettingsClass.SetSIStationNumber(self.siStationNumber)

    def UpdateInfrequently(self) -> bool:
        #SettingsClass.SetSIStationNumber(self.siStationNumber)
        return True

    def detectMissedPunchesDuringInit(self) -> None:
        lastAddr = ReceiveSIAdapter.AddressOfLastPunch.get(self.serialNumber, None)
        if lastAddr is None:
            return None
        getBackupPointerCmd = bytes([0xFF, 0x02, 0x02, 0x83, 0x02, 0x1C, 0x07, 0x74,0x06, 0x03])
        ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::detectMissedPunchesDuringInit: sendCommand")
        response = self.sendCommand(getBackupPointerCmd, printLog=False)
        if response is None:
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::detectMissedPunchesDuringInit sendCommand returned None")
            return None
        SIMsg = SIMessage()
        SIMsg.AddPayload(response)
        if not SIMsg.GetIsChecksumOK():
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::detectMissedPunchesDuringInit getBackupPointerCmd returned invalid checksum")
            return None
        curAddr = (response[7] << 16) | (response[11] << 8 ) | response[12] # next free memory address

        if curAddr > lastAddr:
            noOfMissedPunches = ((curAddr - lastAddr) / 8) -1
            if 0 < noOfMissedPunches <= 30:
                # We missed punches...
                ReceiveSIAdapter.WiRocLogger.info(
                    "ReceiveSIAdapter::detectMissedPunchesDuringInit Punches missed, lastAddr: " + str(lastAddr) + " curAddr: " + str(curAddr))
                self.fetchFromBackupAddress = lastAddr
                self.fetchToBackupAddress = curAddr
                self.fetchFromBackup = True

    def detectMissedPunches(self, siMsg : SIMessage) -> bool:
        ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::detectMissedPunches enter")
        if self.serialNumber is None:
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::detectMissedPunches serialNumber is None")
            return False
        lastAddr = ReceiveSIAdapter.AddressOfLastPunch.get(self.serialNumber, None)
        curAddr = siMsg.GetBackupMemoryAddressAsInt()
        ReceiveSIAdapter.AddressOfLastPunch[self.serialNumber] = curAddr
        if lastAddr is None:
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::detectMissedPunches lastAddr is None")
            return False
        if self.fetchFromBackup:
            # already in fetch from backup mode
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::detectMissedPunches alreaty in fetch from backup mode")
            return False

        if curAddr > lastAddr:
            noOfMissedPunches = ((curAddr - lastAddr) / 8) -1
            if 0 < noOfMissedPunches <= 30:
                # We missed punches...
                ReceiveSIAdapter.WiRocLogger.info(
                    "ReceiveSIAdapter::detectMissedPunches Punches missed, lastAddr: " + str(
                        lastAddr) + " curAddr: " + str(curAddr))
                self.fetchFromBackupAddress = lastAddr
                self.fetchToBackupAddress = curAddr
                self.fetchFromBackup = True
                ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::detectMissedPunches missed punches detected")
                return True
        ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::detectMissedPunches no missed punches detected")
        return False

    def getBackupPunch(self) -> None | dict[str, str|bool|bytearray]:
        if self.fetchFromBackup:
            addrToPunch = self.fetchFromBackupAddress + 8
            if addrToPunch < self.fetchToBackupAddress:
                SIMsgByteArray = self.getBackupPunchAsSIMessageArray(addrToPunch)
                if SIMsgByteArray is None:
                    return None
                self.fetchFromBackupAddress = addrToPunch
                if ReceiveSIAdapter.AddressOfLastPunch[self.serialNumber] < addrToPunch:
                    ReceiveSIAdapter.AddressOfLastPunch[self.serialNumber] = addrToPunch
                source = "SIStation"
                ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::getBackupPunch Fetched backup punch")
                return {"MessageType": "DATA", "MessageSource": source,
                        "MessageSubTypeName": "SIMessage", "Data": SIMsgByteArray,
                        "ChecksumOK": self.IsChecksumOK(SIMsgByteArray)}
            else:
                self.fetchFromBackup = False
        return None

    # messageData is a bytearray
    def GetData(self) -> None | dict[str, str|bool|bytearray|int]:
        if not self.IsDataAvailable():
            if self.oneWay:
                return None
            else:
                return self.getBackupPunch()
        ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::GetData() Data to fetch")

        expectedLength = 3
        receivedData, allReceivedData, expectedLength = self.readData(waitMS=0, expectedLength=expectedLength)

        if len(receivedData) != expectedLength:
            # throw away the data, isn't correct
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::GetData() data not of expected length (thrown away), expected: " + str(expectedLength) + " got: " + str(len(receivedData)) + " data: " + Utils.GetDataInHex(allReceivedData, logging.ERROR))
            return None

        SIMsg = SIMessage()
        SIMsg.AddPayload(receivedData)
        if SIMsg.GetMessageType() == SIMessage.SIPunch:
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::GetData() SI message received! data: " + Utils.GetDataInHex(receivedData, logging.DEBUG))
            if len(allReceivedData) != len(receivedData):
                logging.error("ReceiveSIAdapter::GetData() Received more data than expected, all data: " + Utils.GetDataInHex(allReceivedData, logging.ERROR))

            if not self.oneWay:
                self.detectMissedPunches(SIMsg)

            DatabaseHelper.add_message_stat(self.GetInstanceName(), "SIMessage", "Received", 1)
            source = "SIStation"
            return {"MessageType": "DATA", "MessageSource": source,
                    "MessageSubTypeName": "SIMessage", "Data": receivedData,
                    "SerialNumber": self.serialNumber,
                    "ChecksumOK": self.IsChecksumOK(receivedData)}
        elif SIMsg.GetMessageType() == SIMessage.Status: # Status message send from other WiRoc device
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::GetData() WiRoc to WiRoc status message!")
            return {"MessageType": "DATA", "MessageSource": "WiRoc",
                    "MessageSubTypeName": "Status", "SIStationSerialNumber": self.serialNumber,
                    "Data": receivedData, "ChecksumOK": self.IsChecksumOK(receivedData)}
        else:
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::GetData() Unknown SI message received! Data: " + Utils.GetDataInHex(allReceivedData, logging.ERROR))
            return None

    def AddedToMessageBox(self, mbid: int) -> None:
        return None


class ReceiveSISerialPort(ReceiveSIAdapter):
    def __init__(self, instanceName: str, instanceNumber: int, portName: str):
        super().__init__(instanceName, instanceNumber, portName)
        self.siSerial = serial.Serial()  # not for SIBTSP

    def writeData(self, dataToWrite: bytes) -> bool:
        self.siSerial.write(dataToWrite)
        self.siSerial.flush()
        return True

    def readData(self, waitMS: int, expectedLength: int) -> tuple[bytearray, bytearray, int]:
        if waitMS > 0:
            idx = 0
            while self.siSerial.in_waiting == 0 and idx < waitMS:
                sleep(0.001)
                idx = idx + 1

        #ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::readData(): after waiting for response")

        allBytesReceived = bytearray()
        startFound = False
        response = bytearray()

        while self.siSerial.in_waiting > 0:
            # print("looking for stx: ", end="")
            bytesRead = self.siSerial.read(1)
            allBytesReceived.append(bytesRead[0])
            if bytesRead[0] == STX:
                startFound = True
                if len(response) == 1:
                    # second STX found, discard
                    continue
            if startFound:
                response.append(bytesRead[0])
                if len(response) == 3:
                    expectedLength = response[2] + 6
                if len(response) == expectedLength:
                    break
                if len(response) < expectedLength and self.siSerial.in_waiting == 0:
                    logging.debug("ReceiveSIAdapter::readData() sleep and wait for more bytes")
                    sleep(0.05)
        return response, allBytesReceived, expectedLength

    def InitOneWay(self, baudrate: int) -> bool:
        try:
            if self.siSerial.is_open:
                self.siSerial.close()
            self.siSerial.baudrate = baudrate
            self.siSerial.open()
            self.siSerial.reset_input_buffer()
            ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::InitOneWay: {self.instanceName}: opened serial, baudRate: {self.siSerial.baudrate}")
        except Exception as ex:
            ReceiveSIAdapter.WiRocLogger.error(
                f"ReceiveSIAdapter::InitOneWay: {self.instanceName}: opening serial exception:")
            ReceiveSIAdapter.WiRocLogger.error(ex)
            try:
                self.siSerial.close()
            except Exception as ex2:
                ReceiveSIAdapter.WiRocLogger.error(f"ReceiveSIAdapter::InitOneWay: {self.instanceName}: close serial exception 1:")
                ReceiveSIAdapter.WiRocLogger.error(ex2)
            return False

        if self.siSerial.is_open:
            self.isInitialized = True
            self.oneWay = True
            return True
        return False

    def DetectBaudRate(self) -> bool:
        self.siSerial.baudrate = 38400
        try:
            if self.siSerial.baudrate != 38400:
                if self.siSerial.is_open:
                    self.siSerial.close()
                self.siSerial.baudrate = 38400
                self.siSerial.open()
                ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::DetectBaudRate: {self.instanceName}: serial opened, baudRate: 38400")
            else:
                if not self.siSerial.is_open:
                    self.siSerial.open()
                    ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::DetectBaudRate: {self.instanceName}: serial opened, baudRate: 38400")
                else:
                    ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::DetectBaudRate: {self.instanceName}: serial already open, baudRate: 38400")
            self.siSerial.reset_input_buffer()
            self.siSerial.reset_output_buffer()

        except Exception as ex:
            ReceiveSIAdapter.WiRocLogger.error(f"ReceiveSIAdapter::DetectBaudRate() opening serial exception:")
            ReceiveSIAdapter.WiRocLogger.error(ex)
            try:
                self.siSerial.close()
            except Exception as ex2:
                ReceiveSIAdapter.WiRocLogger.error(f"ReceiveSIAdapter::DetectBaudRate() close serial exception:")
                ReceiveSIAdapter.WiRocLogger.error(ex2)
            return False

        if self.siSerial.is_open:
            try:
                # set master - mode to direct
                ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::DetectBaudRate: {self.instanceName}: serial port open, set master - mode to direct")
                response = self.sendCommand(ReceiveSIAdapter.MSMode, printLog=False)
                if response is None:
                    ReceiveSIAdapter.WiRocLogger.info(f"ReceiveSIAdapter::DetectBaudRate: {self.instanceName}: msmodedirect command failed")
                    return False

                if not self.isCorrectMSModeDirectResponse(response):
                    ReceiveSIAdapter.WiRocLogger.info(f"ReceiveSIAdapter::DetectBaudRate: {self.instanceName}: not correct msmodedirectresponse: " + str(response))

                    # something wrong, try other baudrate
                    self.siSerial.close()
                    self.siSerial.port = self.portName
                    self.siSerial.baudrate = 4800
                    self.siSerial.open()
                    self.siSerial.reset_input_buffer()
                    self.siSerial.reset_output_buffer()

                    ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIAdapter::DetectBaudRate: {self.instanceName}: retry with 4800, serial port open, set master - mode to direct")
                    response = self.sendCommand(ReceiveSIAdapter.MSMode, printLog=False)
                    if response is None:
                        ReceiveSIAdapter.WiRocLogger.info(f"ReceiveSIAdapter::DetectBaudRate: {self.instanceName}: msmodedirect command failed")
                        return False

                    if not self.isCorrectMSModeDirectResponse(response):
                        ReceiveSIAdapter.WiRocLogger.info(f"ReceiveSIAdapter::DetectBaudRate: {self.instanceName}: not correct msmodedirectresponse: " + str(response))
                        ReceiveSIAdapter.WiRocLogger.error(f"ReceiveSIAdapter::DetectBaudRate: {self.instanceName}: could not communicate with master station")
                        try:
                            self.siSerial.close()
                        except Exception as ex2:
                            ReceiveSIAdapter.WiRocLogger.error(f"ReceiveSIAdapter::DetectBaudRate: {self.instanceName}: close serial exception (2):")
                            ReceiveSIAdapter.WiRocLogger.error(ex2)
                        return False

                    ReceiveSIAdapter.WiRocLogger.info(f"ReceiveSIAdapter::DetectBaudRate: {self.instanceName}: SI Station 4800 kbit/s works")
                else:
                    ReceiveSIAdapter.WiRocLogger.info(f"ReceiveSIAdapter::DetectBaudRate: {self.instanceName}: SI Station 38400 kbit/s works")

                return True
            except Exception as ex2:
                ReceiveSIAdapter.WiRocLogger.error(f"ReceiveSIAdapter::DetectBaudRate: {self.instanceName}: exception:")
                ReceiveSIAdapter.WiRocLogger.error(ex2)
                try:
                    self.siSerial.close()
                except Exception as ex3:
                    ReceiveSIAdapter.WiRocLogger.error(f"ReceiveSIAdapter::DetectBaudRate: {self.instanceName}: close serial exception:")
                    ReceiveSIAdapter.WiRocLogger.error(ex2)
                return False
        else:
            return False

    def InitTwoWay(self, skipDetectBaudRate) -> bool:
        if skipDetectBaudRate or self.DetectBaudRate():
            try:
                if not HardwareAbstraction.Instance.HasRTC():
                    self.updateComputerTime()
                self.updateSiStationNumber()
                self.setAutosendAndExtendedProtocol()
                self.serialNumber = self.getSerialNumberSystemValue()
                self.detectMissedPunchesDuringInit()

                self.isInitialized = True
                self.oneWay = False
                return True
            except Exception as ex2:
                ReceiveSIAdapter.WiRocLogger.error(f"ReceiveSIAdapter::InitTwoWay: {self.instanceName}: exception:")
                ReceiveSIAdapter.WiRocLogger.error(ex2)
                try:
                    self.siSerial.close()
                except Exception as ex3:
                    ReceiveSIAdapter.WiRocLogger.error(f"ReceiveSIAdapter::InitTwoWay: {self.instanceName}: close serial exception:")
                    ReceiveSIAdapter.WiRocLogger.error(ex2)
                return False
        else:
            return False

    def IsDataAvailable(self) -> bool:
        return self.siSerial.in_waiting > 0

    def GetData(self) -> None | dict[str, str|bool|bytearray|int]:
        data = super().GetData()
        if data is not None:
            if self.oneWayFallbackTryReInitWhenDataReceived:
                self.shouldReinitialize = True
        return data


class ReceiveSIHWSerialPort(ReceiveSISerialPort):
    Instances: list[ReceiveSIHWSerialPort] = []

    @staticmethod
    def CreateInstances() -> bool:
        serialPorts = []
        # Add any HW serial ports used for SportIdent units
        if SettingsClass.GetRS232Mode() == "RECEIVE":
            hwSISerialPorts = HardwareAbstraction.Instance.GetSISerialPorts()
            serialPorts.extend(hwSISerialPorts)

        # already existing
        previouslyCreated = [instance for instance in ReceiveSIHWSerialPort.Instances if instance.GetSerialDevicePath() in serialPorts]
        highestInstanceNumber = max([instance.GetInstanceNumber() for instance in previouslyCreated], default=0)

        # new serial paths that we should create ReceiveSIHWSerialPort for
        newSerialPaths = [serialPath for serialPath in serialPorts if serialPath not in [instance.GetSerialDevicePath() for instance in previouslyCreated]]

        newInstances = []
        for serialPath in newSerialPaths:
            highestInstanceNumber = highestInstanceNumber+1
            newInstances.append(ReceiveSIHWSerialPort('sihw' + str(highestInstanceNumber), highestInstanceNumber, serialPath))

        newIntancesFound = len(newInstances) > 0
        instancesRemoved = len(previouslyCreated) < len(ReceiveSIHWSerialPort.Instances)

        if newIntancesFound or instancesRemoved:
            ReceiveSIHWSerialPort.Instances = previouslyCreated + newInstances
            return True
        else:
            return False

    def GetIsInitialized(self) -> bool:
        oneWayConfig: bool = SettingsClass.GetRS232OneWayReceiveFromSIStation()
        baudRateConfig: int = 4800 if oneWayConfig and SettingsClass.GetForceRS2324800BaudRateFromSIStation() else 38400

        ReceiveSIAdapter.WiRocLogger.debug(
            "ReceiveSIHWSerialPort::GetIsInitialized() " + self.GetInstanceName()
            + " isInitialized: " + str(self.isInitialized)
            + " oneWayConfig: " + str(oneWayConfig)
            + " oneWay: " + str(self.oneWay)
            + " oneWayFallbackTryReInitWhenDataReceived: " + str(self.oneWayFallbackTryReInitWhenDataReceived)
            + " baudRateConfig: " + str(baudRateConfig) + " baudRate: " + str(self.siSerial.baudrate))
        return self.isInitialized and not self.shouldReinitialize \
            and (oneWayConfig == self.oneWay or (self.oneWay and (self.oneWayFallbackTryReInitWhenDataReceived or self.oneWayFallbackShouldNotTriggerReInit))) \
            and baudRateConfig == self.siSerial.baudrate

    def Init(self) -> bool:
        try:
            if self.GetIsInitialized() and self.siSerial.is_open:
                return True
            self.isInitialized = False
            self.shouldReinitialize = False
            self.oneWayFallbackTryReInitWhenDataReceived = False
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIHWSerialPort::Init() SI Station port name: " + self.portName)
            self.siSerial.close()
            self.siSerial.port = self.portName

            baudrate = 38400
            if SettingsClass.GetRS232OneWayReceiveFromSIStation():
                if SettingsClass.GetForceRS2324800BaudRateFromSIStation():
                    # can only be forced to 4800 when in one-way receive
                    baudrate = 4800
                success = self.InitOneWay(baudrate)
                return success
            else:
                if self.InitTwoWay(skipDetectBaudRate=False):
                    return True
                else:
                    # better with init one way if two-way is not working than aborting
                    success = self.InitOneWay(baudrate)
                    if success:
                        self.oneWayFallbackTryReInitWhenDataReceived = True    #todo: maybe this is not a good idea since we can loose messages every time we try to reinit as two-way. Or we should limit the number of retries, and/or how often.
                    return success

        except Exception as msg:
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIHWSerialPort::Init() Exception: " + str(msg))
            return False


class ReceiveSIUSBSerialPort(ReceiveSISerialPort):
    Instances: list[ReceiveSIUSBSerialPort] = []
    SRRDongleModel: bytearray = bytearray([0x6F, 0x21])

    @staticmethod
    def CreateInstances() -> bool:
        # Add USB serial ports
        portInfoList = serial.tools.list_ports.grep('10c4:800a|0525:a4aa|1a86:7523|067b:2303|0403:6001|0557:2008|10c4:ea60')
        serialPorts = [portInfo.device for portInfo in portInfoList]
        # SPORTident USB device                                                                 -- Works
        # Linux-USB CDC Composite Gadge (Ethernet and ACM)      {ie:Chip computer}              -- Works
        # 1a86:7523 QinHeng Electronics HL-340 USB-Serial adapter                               -- Doesn't work (possibly works one-way)
        # 067b:2303 Prolific Technology, Inc. PL2303 Serial Port                                -- Works
        # 0403:6001 Future Technology Devices International, Ltd FT232 USB-Serial (UART) IC     -- Works
        # 0557:2008 ATEN International Co., Ltd UC-232A Serial Port [pl2303]                    -- Works
        # 10c4:ea60 Silicon Labs CP210x UART Bridge  Punch Generator

        # already existing
        previouslyCreated = [instance for instance in ReceiveSIUSBSerialPort.Instances if
                             instance.GetSerialDevicePath() in serialPorts]
        highestInstanceNumber = max([instance.GetInstanceNumber() for instance in previouslyCreated], default=0)

        # new serial paths that we should create receivesiadapter for
        newSerialPaths = [serialPath for serialPath in serialPorts if
                          serialPath not in [instance.GetSerialDevicePath() for instance in previouslyCreated]]

        newInstances = []
        for serialPath in newSerialPaths:
            highestInstanceNumber = highestInstanceNumber + 1
            newInstances.append(ReceiveSIUSBSerialPort('si' + str(highestInstanceNumber), highestInstanceNumber, serialPath))

        newIntancesFound = len(newInstances) > 0
        instancesRemoved = len(previouslyCreated) < len(ReceiveSIUSBSerialPort.Instances)

        if instancesRemoved:
            ReceiveSIUSBSerialPort.SetErrorCode("")

        if newIntancesFound or instancesRemoved:
            ReceiveSIUSBSerialPort.Instances = previouslyCreated + newInstances

            if len(ReceiveSIUSBSerialPort.Instances) > 0:
                SettingsClass.SetReceiveSIAdapterActive(True)
            else:
                SettingsClass.SetReceiveSIAdapterActive(False)
            return True
        else:
            return False

    @staticmethod
    def SetErrorCode(message: str):
        errorCodeData = ErrorCodeData()
        errorCodeData.Code = ErrorCodeData.ERR_SI_USB_CONF
        errorCodeData.Message = message
        DatabaseHelper.save_error_code(errorCodeData)
        if len(message)>0:
            SettingsClass.SetNewErrorCode()

    def GetIsInitialized(self) -> bool:
        oneWayConfig: bool = SettingsClass.GetOneWayReceiveFromSIStation()
        baudRateConfig: int = 4800 if oneWayConfig and SettingsClass.GetForce4800BaudRateFromSIStation() else 38400

        ReceiveSIAdapter.WiRocLogger.debug(
            "ReceiveSIUSBSerialPort::GetIsInitialized() " + self.GetInstanceName() + " isInitialized: " + str(
                self.isInitialized) + " oneWayConfig: " + str(oneWayConfig) + " oneWay: " + str(self.oneWay)
                + " oneWayFallbackTryReInitWhenDataReceived: " + str(self.oneWayFallbackTryReInitWhenDataReceived)
                + " oneWayFallbackShouldNotTriggerReInit: " + str(self.oneWayFallbackShouldNotTriggerReInit)
                + " shouldReinitialize: " + str(self.shouldReinitialize)
                + " baudRateConfig: " + str(baudRateConfig) + " baudRate: " + str(self.siSerial.baudrate))

        if self.isInitialized and not oneWayConfig and self.oneWay and not self.isSRRDongle:
            # We are initialized as one way even though configuration says it shouldn't be one-way.
            # and is not a device that we know is one-way (SRR dongle)
            self.SetErrorCode(f"{self.instanceName} two-way init failed")
        else:
            # Clear error code
            self.SetErrorCode("")

        return self.isInitialized and not self.shouldReinitialize \
            and (oneWayConfig == self.oneWay
                 or (self.oneWay and (self.oneWayFallbackTryReInitWhenDataReceived or self.oneWayFallbackShouldNotTriggerReInit))) \
            and baudRateConfig == self.siSerial.baudrate

    def Init(self) -> bool:
        try:
            if self.GetIsInitialized() and self.siSerial.is_open:
                return True
            self.isInitialized = False
            self.shouldReinitialize = False
            self.oneWayFallbackTryReInitWhenDataReceived = False
            self.oneWayFallbackShouldNotTriggerReInit = False
            self.isSRRDongle = False
            ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIUSBSerialPort::Init: {self.instanceName}: SI Station port name: " + self.portName)
            self.siSerial.close()
            self.siSerial.port = self.portName

            baudrate = 38400

            if SettingsClass.GetOneWayReceiveFromSIStation():
                if SettingsClass.GetForce4800BaudRateFromSIStation():
                    # can only be forced to 4800 when in one-way receive
                    baudrate = 4800
                success = self.InitOneWay(baudrate)
                return success
            else:
                if self.DetectBaudRate():
                    if self.getStationSettingModelValue() == ReceiveSIUSBSerialPort.SRRDongleModel:
                        ReceiveSIAdapter.WiRocLogger.info(f"ReceiveSIUSBSerialPort::Init: {self.instanceName}: SRR-Dongle found!")
                        # Serial port is open, with correct baudrate, set it as one-way since we cant ask for backup punches etc.
                        self.isInitialized = True
                        self.oneWay = True
                        self.oneWayFallbackShouldNotTriggerReInit = True
                        self.isSRRDongle = True
                        return True
                    else:
                        successTwoWay = self.InitTwoWay(skipDetectBaudRate=True)
                        if successTwoWay:
                            return True
                        else: # better with init one way if two way is not working than aborting
                            successOneWay = self.InitOneWay(baudrate)
                            if successOneWay:
                                self.oneWayFallbackTryReInitWhenDataReceived = False  # reinitialization risks losing messages that arrive at the same time
                                self.oneWayFallbackShouldNotTriggerReInit = True # reinitialization risks losing messages that arrive at the same time
                                return True
                            else:
                                return False
                else:
                    successOneWay = self.InitOneWay(baudrate)
                    if successOneWay:
                        self.oneWayFallbackTryReInitWhenDataReceived = False  # reinitialization risks losing messages that arrive at the same time
                        self.oneWayFallbackShouldNotTriggerReInit = True  # reinitialization risks losing messages that arrive at the same time
                        return True
                    else:
                        return False

        except Exception as msg:
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIUSBSerialPort::Init() Exception: " + str(msg))
            return False


class ReceiveSIBluetoothSP(ReceiveSIAdapter):
    Instances: list[ReceiveSIBluetoothSP] = []

    def __init__(self, instanceName: str, instanceNumber: int, portName: str):
        super().__init__(instanceName, instanceNumber, portName)
        self.sock = None
        self.sockQueue: Queue = Queue()
        self.exitQueue: Queue = Queue()
        self.connectBackgroundProcess = None

    @staticmethod
    def CreateInstances() -> bool:
        # Get BT Serial ports from database
        btSerialPortData = DatabaseHelper.get_bluetooth_serial_ports()
        serialPorts = ["rfcomm" + btSerialPort.DeviceBTAddress for btSerialPort in btSerialPortData]

        # already existing
        previouslyCreated = [instance for instance in ReceiveSIBluetoothSP.Instances if
                             instance.GetSerialDevicePath() in serialPorts]
        highestInstanceNumber = max([instance.GetInstanceNumber() for instance in previouslyCreated], default=0)

        # new serial paths that we should create receivesiadapter for
        newSerialPaths = [serialPath for serialPath in serialPorts if
                          serialPath not in [instance.GetSerialDevicePath() for instance in previouslyCreated]]

        newInstances = []
        for serialPath in newSerialPaths:
            highestInstanceNumber = highestInstanceNumber + 1
            newInstances.append(ReceiveSIBluetoothSP('sibtsp' + str(highestInstanceNumber), highestInstanceNumber, serialPath))

        newIntancesFound = len(newInstances) > 0
        instancesRemoved = len(previouslyCreated) < len(ReceiveSIBluetoothSP.Instances)

        if newIntancesFound or instancesRemoved:
            ReceiveSIBluetoothSP.Instances = previouslyCreated + newInstances
            return True
        else:
            return False

    def GetIsInitialized(self) -> bool:
        oneWayConfig = SettingsClass.GetBTSerialOneWayReceiveFromSIStation()

        ReceiveSIAdapter.WiRocLogger.debug(
            "ReceiveSIBluetoothSP::GetIsInitialized() " + self.GetInstanceName() + " isInitialized: "
            + str(self.isInitialized) + " oneWayConfig: " + str(oneWayConfig) + " oneWay: "
            + str(self.oneWay) + " oneWayFallbackTryReInitWhenDataReceived: " + str(self.oneWayFallbackTryReInitWhenDataReceived))
        return self.isInitialized and not self.shouldReinitialize and (oneWayConfig == self.oneWay or (self.oneWay and self.oneWayFallbackTryReInitWhenDataReceived))

    # implements abstract/virtual method
    def writeData(self, dataToWrite: bytes) -> bool:
        try:
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIBluetoothSP::writeData enter")
            self.sock.send(dataToWrite)
        except OSError as oserror:
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIBluetoothSP::writeData() exception:" + str(oserror))
            if oserror.errno == 107:
                # BT device disconnected
                ReceiveSIAdapter.WiRocLogger.error("ReceiveSIBluetoothSP::writeData() BT Device not connected!")
                #self.sock = None
                self.isInitialized = False
                self.oneWay = False
            return False
        except Exception as ex:
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIBluetoothSP::writeData() exception:")
            ReceiveSIAdapter.WiRocLogger.error(ex)
            btSerialPortDatas = DatabaseHelper.get_bluetooth_serial_port(self.portName.replace('rfcomm', ''))
            if len(btSerialPortDatas)>0:
                btSerialPortDatas[0].Status = "WriteError"
                DatabaseHelper.save_bluetooth_serial_port(btSerialPortDatas[0])
            return False
        return True

    # abstract/virtual method
    def readData(self, waitMS: int, expectedLength: int) -> tuple[bytearray, bytearray, int]:
        try:
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIBluetoothSP::readData(): enter")
            ready = select.select([self.sock], [], [], waitMS/1000)
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIBluetoothSP::readData(): 1")
            if ready[0]:
                ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIBluetoothSP::readData(): 2")
                self.sock.settimeout(0.01)
                allBytes = bytearray(self.sock.recv(100))
                ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIBluetoothSP::readData(): 3")
                response = bytearray(allBytes)
                ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIBluetoothSP::readData(): after waiting for response")
                while len(response) > 0 and response[0] != STX:
                    response = response[1:]
                if len(response) > 1:
                    if response[0] == STX and response[1] == STX:
                        response = response[1:]

                if len(response) > 2:
                    expectedLength = response[2] + 6

                return response, allBytes, expectedLength
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIBluetoothSP::readData(): return nothing")
            return bytearray(), bytearray(), expectedLength
        except Exception as ex:
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIBluetoothSP::readData() exception:")
            ReceiveSIAdapter.WiRocLogger.error(ex)
            self.isInitialized = False
            btSerialPortDatas = DatabaseHelper.get_bluetooth_serial_port(self.portName.replace('rfcomm',''))
            if len(btSerialPortDatas)>0:
                btSerialPortDatas[0].Status = "ReadError"
                DatabaseHelper.save_bluetooth_serial_port(btSerialPortDatas[0])
            return bytearray(), bytearray(), expectedLength

    def InitOneWay(self, baudrate: int | None) -> bool:
        try:
            # Need to test if oneway is possible, if the bt device is connected at all
            self.sock.send(bytearray(bytes([0])))
            self.isInitialized = True
            self.oneWay = True
            ReceiveSIAdapter.WiRocLogger.info("ReceiveSIBluetoothSP::InitOneWay() Initialized!")
            return True
        except socket.timeout as socktimeout:
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIBluetoothSP::InitOneWay() exception:" + str(socktimeout))
            return False
        except OSError as oserror:
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIBluetoothSP::InitOneWay() exception:" + str(oserror))
            if oserror.errno == 107:
                # BT device disconnected
                ReceiveSIAdapter.WiRocLogger.error("ReceiveSIBluetoothSP::InitOneWay() BT Device not connected!")
                self.sock = None
                self.isInitialized = False
                self.oneWay = False

    def InitTwoWay(self) -> bool:
        try:
            # set master - mode to direct
            ReceiveSIAdapter.WiRocLogger.debug(f"ReceiveSIBluetoothSP::InitTwoWay: {self.instanceName}: set set master - mode to direct")
            response = self.sendCommand(ReceiveSIAdapter.MSMode, printLog=False)

            if response is None:
                ReceiveSIAdapter.WiRocLogger.info(f"ReceiveSIBluetoothSP::InitTwoWay: {self.instanceName}: msmodedirect command failed")
                return False

            if not self.isCorrectMSModeDirectResponse(response):
                ReceiveSIAdapter.WiRocLogger.info(f"ReceiveSIBluetoothSP::InitTwoWay: {self.instanceName}: not correct msmodedirectresponse: " + str(response))
                return False

            if not HardwareAbstraction.Instance.HasRTC():
                self.updateComputerTime()
            self.updateSiStationNumber()
            self.setAutosendAndExtendedProtocol()
            self.serialNumber = self.getSerialNumberSystemValue()
            self.detectMissedPunchesDuringInit()

            self.isInitialized = True
            self.oneWay = False
            return True
        except Exception as ex2:
            ReceiveSIAdapter.WiRocLogger.error(f"ReceiveSIBluetoothSP::InitTwoWay: {self.instanceName}: exception:")
            ReceiveSIAdapter.WiRocLogger.error(ex2)
            return False

    def processSockQueue(self):
        if self.sockQueue.empty():
            return True

        theReturnedSock = None
        while not self.sockQueue.empty():
            theReturnedSock = self.sockQueue.get(False)
            self.exitQueue.put("Exit!")

        if theReturnedSock is None:
            self.sock = None
            self.isInitialized = False
            self.oneWay = False
            return False
        else:
            self.sock = theReturnedSock
            if SettingsClass.GetBTSerialOneWayReceiveFromSIStation():
                self.oneWayFallbackTryReInitWhenDataReceived = False
                success = self.InitOneWay(None)
            else:
                success = self.InitTwoWay()
                if not success:
                    # better with init one way if two way is not working than aborting
                    success = self.InitOneWay(None)
                    if success:
                        self.oneWayFallbackTryReInitWhenDataReceived = True

            btSerialPortDatas = DatabaseHelper.get_bluetooth_serial_port(self.portName.replace('rfcomm', ''))
            if len(btSerialPortDatas) > 0:
                btSerialPortData = btSerialPortDatas[0]
                if success:
                    btSerialPortData.Status = "Connected"
                    DatabaseHelper.save_bluetooth_serial_port(btSerialPortData)
                else:
                    btSerialPortData.Status = "NotConnected"
                    DatabaseHelper.save_bluetooth_serial_port(btSerialPortData)
            else:
                raise Exception("Could not find the BluetoothSerialPortData row in database")
            return success

    @staticmethod
    def ConnectBackground(sockQueue: Queue, exitQueue: Queue, sock: socket, deviceBTAddress: str, port: int):
        try:
            sock.connect((deviceBTAddress, port))
            sock.setblocking(False)
            sockQueue.put(sock)
            exitQueue.get() # Will block until something is put in the queue
        except Exception as msg:
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIBluetoothSP::connectBackground() Exception: " + str(msg))
            sockQueue.put(None)

    def Init(self) -> bool:
        try:
            self.processSockQueue()
            if self.connectBackgroundProcess is not None:
                self.connectBackgroundProcess.join()
                self.connectBackgroundProcess = None
                while not self.exitQueue.empty():
                    self.exitQueue.get(False)
            if self.GetIsInitialized():
                return True
            self.isInitialized = False
            self.shouldReinitialize = False
            self.oneWayFallbackTryReInitWhenDataReceived = False
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIBluetoothSP::Init() SI Station port name: " + self.portName)

           # if self.sock is None:
            self.sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            deviceBTAddress = self.portName.replace('rfcomm', '')  # get only the BTAddress from the portName
            port = 1

            self.connectBackgroundProcess = Process(
                target=ReceiveSIBluetoothSP.ConnectBackground,
                args=(self.sockQueue, self.exitQueue, self.sock, deviceBTAddress, port))
            self.connectBackgroundProcess.start()

            return False
                #self.sock.connect((deviceBTAddress, port))
                #self.sock.setblocking(False)

            #if SettingsClass.GetBTSerialOneWayReceiveFromSIStation():
            #    self.oneWayFallbackTryReInitWhenDataReceived = False
            #    success = self.InitOneWay(None)
            #else:
            #    success = self.InitTwoWay()
            #    if not success:
            #        # better with init one way if two way is not working than aborting
            #        success = self.InitOneWay(None)
            #        if success:
            #            self.oneWayFallbackTryReInitWhenDataReceived = True

            #btSerialPortDatas = DatabaseHelper.get_bluetooth_serial_port(self.portName.replace('rfcomm', ''))
            #if len(btSerialPortDatas) > 0:
            #    btSerialPortData = btSerialPortDatas[0]
            #    if success:
            #        btSerialPortData.Status = "Connected"
            #        DatabaseHelper.save_bluetooth_serial_port(btSerialPortData)
            #    else:
            #        btSerialPortData.Status = "NotConnected"
            #        DatabaseHelper.save_bluetooth_serial_port(btSerialPortData)
            #else:
            #    raise Exception("Could not find the BluetoothSerialPortData row in database")
            #return success
        except Exception as msg:
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIBluetoothSP::Init() Exception: " + str(msg))
            self.sock = None
            self.isInitialized = False
            self.oneWay = False
            return False

    # abstract/virtual method
    def IsDataAvailable(self):
        readable, writable, exceptional = select.select([self.sock], [], [], 0)
        return len(readable) > 0

    def GetData(self) -> dict[str, str | bool | bytearray | int] | None:
        data = super().GetData()
        if data is not None:
            if self.oneWayFallbackTryReInitWhenDataReceived:
                self.shouldReinitialize = True
        return data
