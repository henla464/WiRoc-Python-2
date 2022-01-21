from settings.settings import SettingsClass
import serial
import logging
from constants import *
from time import sleep
from utils.utils import Utils
from battery import Battery
from datamodel.datamodel import SIMessage
from datamodel.db_helper import DatabaseHelper
from chipGPIO.hardwareAbstraction import HardwareAbstraction
import serial.tools.list_ports

class ReceiveSIAdapter(object):
    WiRocLogger = logging.getLogger('WiRoc.Input')
    Instances = []
    AddressOfLastPunch = {}

    @staticmethod
    def CreateInstances():
        # Add USB serial ports
        portInfoList = serial.tools.list_ports.grep('10c4:800a|0525:a4aa|1a86:7523|067b:2303|0403:6001|0557:2008')
        serialPorts = [portInfo.device for portInfo in portInfoList]
        # SPORTident USB device                                                                 -- Works
        # Linux-USB CDC Composite Gadge (Ethernet and ACM)      {ie:Chip computer}              -- Works
        # 1a86:7523 QinHeng Electronics HL-340 USB-Serial adapter                               -- Doesn't work (possibly works one-way)
        # 067b:2303 Prolific Technology, Inc. PL2303 Serial Port                                -- Works
        # 0403:6001 Future Technology Devices International, Ltd FT232 USB-Serial (UART) IC     -- Works
        # 0557:2008 ATEN International Co., Ltd UC-232A Serial Port [pl2303]                    -- Works

        # Add any HW serial ports used for SportIdent units
        if SettingsClass.GetRS232Mode() == "RECEIVE":
            hwSISerialPorts = HardwareAbstraction.Instance.GetSISerialPorts()
            serialPorts.extend(hwSISerialPorts)

        # Add BT Serial ports
        btSISerialPorts = HardwareAbstraction.Instance.GetRFCommsSerialPorts()
        serialPorts.extend(btSISerialPorts)

        # already existing
        previouslyCreated = [instance for instance in ReceiveSIAdapter.Instances if instance.GetSerialDevicePath() in serialPorts]
        highestInstanceNumber = max([instance.GetInstanceNumber() for instance in previouslyCreated], default=0)

        # new serial paths that we should create receivesiadapter for
        newSerialPaths = [serialPath for serialPath in serialPorts if serialPath not in [instance.GetSerialDevicePath() for instance in previouslyCreated]]

        newInstances = []
        for serialPath in newSerialPaths:
            highestInstanceNumber = highestInstanceNumber+1
            newInstances.append(ReceiveSIAdapter('si' + str(highestInstanceNumber), highestInstanceNumber, serialPath))

        newIntancesFound = len(newInstances) > 0
        instancesRemoved = len(previouslyCreated) < len(ReceiveSIAdapter.Instances)

        if newIntancesFound or instancesRemoved:
            ReceiveSIAdapter.Instances = previouslyCreated + newInstances

            if len(ReceiveSIAdapter.Instances) > 0:
                SettingsClass.SetReceiveSIAdapterActive(True)
            else:
                SettingsClass.SetReceiveSIAdapterActive(False)
            return True
        else:
            return False

    @staticmethod
    def GetTypeName():
        return "SI"

    def __init__(self, instanceName, instanceNumber, portName):
        self.instanceName = instanceName
        self.instanceNumber = instanceNumber
        self.portName = portName
        self.siSerial = serial.Serial()
        self.write_timeout = 0.02
        self.isInitialized = False
        self.oneWay = False
        self.siStationNumber = 0
        self.hasTimeBeenSet = False
        self.serialNumber = None
        self.noOfFailedInitializations = 0
        self.noOfFailedReadsInRow = 0
        self.fetchFromBackup = False
        self.fetchFromBackupAddress = None #exclusive
        self.fetchToBackupAddress = None #exclusive

    def GetInstanceName(self):
        return self.instanceName

    def GetInstanceNumber(self):
        return self.instanceNumber

    def GetSerialDevicePath(self):
        return self.portName

    def GetIsInitialized(self):
        hwSISerialPorts = HardwareAbstraction.Instance.GetSISerialPorts()
        btSISerialPorts = HardwareAbstraction.Instance.GetRFCommsSerialPorts()
        rfCommStatus = None
        if self.portName in hwSISerialPorts:
            oneWayConfig = SettingsClass.GetRS232OneWayReceiveFromSIStation()
            baudRateConfig = 4800 if oneWayConfig and SettingsClass.GetForceRS2324800BaudRateFromSIStation() else 38400
        elif self.portName in btSISerialPorts:
            oneWayConfig = False
            baudRateConfig = 38400
            rfCommStatus = HardwareAbstraction.Instance.GetRFCommStatus(self.portName)
        else:
            oneWayConfig = SettingsClass.GetOneWayReceiveFromSIStation()
            baudRateConfig = 4800 if oneWayConfig and SettingsClass.GetForce4800BaudRateFromSIStation() else 38400

        ReceiveSIAdapter.WiRocLogger.debug(
            "ReceiveSIAdapter::GetIsInitialized() " + self.GetInstanceName() + " isInitialized: " + str(self.isInitialized) + " oneWayConfig: " + str(oneWayConfig) + " oneWay: " + str(self.oneWay)
            + " baudRateConfig: " + str(baudRateConfig) + " baudRate: " + str(self.siSerial.baudrate) + " rfCommStatus: " + str(rfCommStatus))
        return self.isInitialized and oneWayConfig == self.oneWay and baudRateConfig == self.siSerial.baudrate and (rfCommStatus is None or rfCommStatus == "connected")

    def ShouldBeInitialized(self):
        return not self.GetIsInitialized()

    def IsChecksumOK(self, receivedData):
        calculatedCRC = Utils.CalculateCRC(receivedData[1:-3])
        crcInMessage = receivedData[-3:-1]
        return calculatedCRC == crcInMessage

    def isCorrectMSModeDirectResponse(self, data):
        return len(data) == 9 and data[0] == STX and data[5] == 0x4D

    def sendCommand(self, command):
        ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::sendCommand() command: " + Utils.GetDataInHex(command, logging.DEBUG))
        self.siSerial.write(command)
        ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::sendCommand(): after write")
        self.siSerial.flush()
        expectedLength = 3
        response = bytearray()
        allBytesReceived = bytearray()
        startFound = False
        idx = 0
        ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::sendCommand(): before waiting response")
        while self.siSerial.in_waiting == 0 and idx < 30:
            sleep(0.01)
            idx = idx + 1
        ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::sendCommand(): after waiting for response")

        while self.siSerial.in_waiting > 0:
            # print("looking for stx: ", end="")
            bytesRead = self.siSerial.read(1)
            allBytesReceived.append(bytesRead[0])
            # print(bytesRead)
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
                    logging.debug("ReceiveSIAdapter::sendCommand() sleep and wait for more bytes")
                    sleep(0.05)
        ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::sendCommand() response: " + Utils.GetDataInHex(response, logging.DEBUG))
        return response

    def InitOneWay(self, baudrate):
        self.siSerial.baudrate = baudrate

        try:
            self.siSerial.open()
            self.siSerial.reset_input_buffer()
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::InitOneWay() " + self.instanceName + " opened serial")
        except Exception as ex:
            ReceiveSIAdapter.WiRocLogger.error(
                "ReceiveSIAdapter::InitOneWay() " + self.instanceName + " opening serial exception:")
            ReceiveSIAdapter.WiRocLogger.error(ex)
            try:
                self.siSerial.close()
            except Exception as ex2:
                ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::InitOneWay() close serial exception 1:")
                ReceiveSIAdapter.WiRocLogger.error(ex2)
            return False

        if self.siSerial.is_open:
            self.isInitialized = True
            self.oneWay = True
            return True
        return False

    def InitBTSerialOneWay(self, baudrate):
        self.siSerial.baudrate = baudrate

        try:
            self.siSerial.open()
            self.siSerial.reset_input_buffer()
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::InitBTSerialOneWay() " + self.instanceName + " opened serial")
        except Exception as ex:
            ReceiveSIAdapter.WiRocLogger.error(
                "ReceiveSIAdapter::InitBTSerialOneWay() " + self.instanceName + " opening serial exception:")
            ReceiveSIAdapter.WiRocLogger.error(ex)
            try:
                self.siSerial.close()
            except Exception as ex2:
                ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::InitBTSerialOneWay() close serial exception 1:")
                ReceiveSIAdapter.WiRocLogger.error(ex2)
            return False

        try:
            # Check that we can get in_waiting. This seem to always work with the hardware serial ports regardless whether
            # SI Station/other device is connected or not. But for a BT-To-Serial device it fails after a few tries
            # (after ~0.05 seconds) if there is no SI Station connected to the BT-To-Serial device. We want it to fail
            # during init so that we don't get loads of errors in GetData method, and so that it will be reconfigured again
            # with InitTwoWay when InitOneWay was called as fallback (ie when one-way is not requested in the configuration).
            for i in range(10):
                noOfWaiting = self.siSerial.in_waiting
                ReceiveSIAdapter.WiRocLogger.error(
                    "ReceiveSIAdapter::InitBTSerialOneWay() " + self.instanceName + " in_waiting: " + str(noOfWaiting))
                sleep(0.02)
        except Exception as ex2:
            ReceiveSIAdapter.WiRocLogger.error(
                "ReceiveSIAdapter::InitBTSerialOneWay() " + self.instanceName + " Could not get in_waiting (not possible to read serial):")
            ReceiveSIAdapter.WiRocLogger.error(ex2)
            try:
                self.siSerial.close()
            except Exception as ex2:
                ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::InitBTSerialOneWay() close serial exception 2:")
                ReceiveSIAdapter.WiRocLogger.error(ex2)
            return False

        rfCommStatus = HardwareAbstraction.Instance.GetRFCommStatus(self.portName)
        if rfCommStatus != "connected":
            ReceiveSIAdapter.WiRocLogger.error(
                "ReceiveSIAdapter::InitBTSerialOneWay() " + self.instanceName + " rfCommStatus: " + rfCommStatus)
            try:
                self.siSerial.close()
            except Exception as ex3:
                ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::InitBTSerialOneWay() close serial exception 3:")
                ReceiveSIAdapter.WiRocLogger.error(ex3)
            return False

        if self.siSerial.is_open:
            self.isInitialized = True
            self.oneWay = True
            return True
        return False

    def InitTwoWay(self):
        self.siSerial.baudrate = 38400
        try:
            self.siSerial.open()
            self.siSerial.reset_input_buffer()
            self.siSerial.reset_output_buffer()
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::InitTwoWay() opened serial")
        except Exception as ex:
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::InitTwoWay() opening serial exception:")
            ReceiveSIAdapter.WiRocLogger.error(ex)
            try:
                self.siSerial.close()
            except Exception as ex2:
                ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::InitTwoWay() close serial exception:")
                ReceiveSIAdapter.WiRocLogger.error(ex2)
            return False

        if self.siSerial.is_open:
            try:
                # set master - mode to direct
                ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::InitTwoWay() serial port open")
                msdMode = bytes([0xFF, 0xFF, 0x02, 0x02, 0xF0, 0x01, 0x4D, 0x6D, 0x0A, 0x03])
                response = self.sendCommand(msdMode)

                if not self.isCorrectMSModeDirectResponse(response):
                    ReceiveSIAdapter.WiRocLogger.info("ReceiveSIAdapter::InitTwoWay() not correct msmodedirectresponse: " + str(response))

                    # something wrong, try other baudrate
                    self.siSerial.close()
                    self.siSerial.port = self.portName
                    self.siSerial.baudrate = 4800
                    self.siSerial.open()
                    self.siSerial.reset_input_buffer()
                    self.siSerial.reset_output_buffer()

                    response = self.sendCommand(msdMode)

                    if not self.isCorrectMSModeDirectResponse(response):
                        ReceiveSIAdapter.WiRocLogger.info("ReceiveSIAdapter::InitTwoWay() not correct msmodedirectresponse: " + str(response))
                        ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::InitTwoWay() could not communicate with master station")
                        try:
                            self.siSerial.close()
                        except Exception as ex2:
                            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::InitTwoWay() close serial exception (2):")
                            ReceiveSIAdapter.WiRocLogger.error(ex2)
                        return False

                    ReceiveSIAdapter.WiRocLogger.info("ReceiveSIAdapter::InitTwoWay() SI Station 4800 kbit/s works")
                else:
                    ReceiveSIAdapter.WiRocLogger.info("ReceiveSIAdapter::InitTwoWay() SI Station 38400 kbit/s works")

                # If this is the first instance then update the computer time
                if ReceiveSIAdapter.Instances[0].GetSerialDevicePath() == self.GetSerialDevicePath():
                    self.updateComputerTimeAndSiStationNumber()
                self.serialNumber = self.getSerialNumberSystemValue()
                self.detectMissedPunchesDuringInit()

                self.isInitialized = True
                self.oneWay = False
                return True
            except Exception as ex2:
                ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::InitTwoWay() exception:")
                ReceiveSIAdapter.WiRocLogger.error(ex2)
                try:
                    self.siSerial.close()
                except Exception as ex3:
                    ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::InitTwoWay() close serial exception:")
                    ReceiveSIAdapter.WiRocLogger.error(ex2)
                return False
        else:
            return False

    def Init(self):
        try:
            if self.GetIsInitialized() and self.siSerial.is_open:
                return True
            self.isInitialized = False
            ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::Init() SI Station port name: " + self.portName)
            self.siSerial.close()
            self.siSerial.port = self.portName

            hwSISerialPorts = HardwareAbstraction.Instance.GetSISerialPorts()
            btSISerialPorts = HardwareAbstraction.Instance.GetRFCommsSerialPorts()

            baudrate = 38400
            if self.portName in hwSISerialPorts:
                if SettingsClass.GetRS232OneWayReceiveFromSIStation():
                    if SettingsClass.GetForceRS2324800BaudRateFromSIStation():
                        # can only be forced to 4800 when in one-way receive
                        baudrate = 4800
                    success = self.InitOneWay(baudrate)
                    if success:
                        self.noOfFailedInitializations = 0
                    else:
                        self.noOfFailedInitializations +=1
                    return success
                else:
                    if self.InitTwoWay():
                        self.noOfFailedInitializations = 0
                        return True
                    else:
                        # better with init one way if two way is not working than aborting
                        # Since configuration for one-way and the initialization doesn't match
                        # configuration for InitTwoWay will be retried each adapter configure interval.
                        success = self.InitOneWay(baudrate)
                        if success:
                            self.noOfFailedInitializations = 0
                        else:
                            self.noOfFailedInitializations += 1
                        return success
            elif self.portName in btSISerialPorts:
                if self.noOfFailedInitializations == 2:
                    # Try to release and rebind, maybe that fixes the problem
                    HardwareAbstraction.Instance.ReleaseClosedRFCommsAndRebind()
                if self.noOfFailedInitializations == 4:
                    HardwareAbstraction.Instance.ReleaseRFCommByPortName(self.portName)
                    self.noOfFailedInitializations = 0
                    return False
                if SettingsClass.GetBTSerialOneWayReceiveFromSIStation():
                    if SettingsClass.GetForceBTSerial4800BaudRateFromSIStation():
                        # can only be forced to 4800 when in one-way receive
                        baudrate = 4800
                    success = self.InitBTSerialOneWay(baudrate)
                    if success:
                        self.noOfFailedInitializations = 0
                    else:
                        self.noOfFailedInitializations += 1
                    return success
                else:
                    if self.InitTwoWay():
                        self.noOfFailedInitializations = 0
                        return True
                    else:  # better with init one way if two way is not working than aborting
                        success = self.InitBTSerialOneWay(baudrate)
                        if success:
                            self.noOfFailedInitializations = 0
                        else:
                            self.noOfFailedInitializations += 1
                        return success
            else:
                if SettingsClass.GetOneWayReceiveFromSIStation():
                    baudrate = 38400
                    if SettingsClass.GetForce4800BaudRateFromSIStation():
                        # can only be forced to 4800 when in one-way receive
                        baudrate = 4800
                    success = self.InitOneWay(baudrate)
                    if success:
                        self.noOfFailedInitializations = 0
                    else:
                        self.noOfFailedInitializations += 1
                    return success
                else:
                    if self.InitTwoWay():
                        self.noOfFailedInitializations = 0
                        return True
                    else:  # better with init one way if two way is not working than aborting
                        success = self.InitOneWay(baudrate)
                        if success:
                            self.noOfFailedInitializations = 0
                        else:
                            self.noOfFailedInitializations += 1
                        return success
        except (Exception) as msg:
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::Init() Exception: " + str(msg))
            return False

    def GetTimeAsTenthOfSeconds(self, twelveHourTime, subSecondsAsTensOfSeconds, twentyFourHour):
        time = ((twelveHourTime[0] << 8) + twelveHourTime[1]) * 10 + subSecondsAsTensOfSeconds
        if twentyFourHour == 1:
            time += 36000 * 12
        return time

    def getSIStationTimeAndStationNumber(self):
        getTimeCmd = bytes([0xFF, 0x02, 0x02, 0xF7, 0x00, 0xF7, 0x00, 0x03])
        timeResp = self.sendCommand(getTimeCmd)
        SIMsg = SIMessage()
        SIMsg.AddPayload(timeResp)
        if not SIMsg.GetIsChecksumOK():
            ReceiveSIAdapter.WiRocLogger.error(
                "ReceiveSIAdapter::getSIStationTimeAndStationNumber getTimeCmd returned invalid checksum")
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

    def getStationSettingSystemValue(self):
        getSystemValueCmd = bytes([0xFF, 0x02, 0x02, 0x83, 0x02, 0x74, 0x01, 0x04, 0x14, 0x03])
        sysValResp = self.sendCommand(getSystemValueCmd)
        extendedProtocol = sysValResp[6] & 0x01
        autoSend = sysValResp[6] & 0x02
        readOut = sysValResp[6] & 0x80
        stationNumber = (sysValResp[3] << 8) | sysValResp[4]
        return extendedProtocol, autoSend, readOut, stationNumber

    def getSerialNumberSystemValue(self):
        addr = 0x00
        cmdLength = 0x02
        noOfBytesToRead = 0x04
        getSerialNumberSystemValueCmd = bytes([0xFF, 0x02, 0x02, 0x83, cmdLength, addr, noOfBytesToRead, 0xbc, 0x0f, 0x03])
        serialNumberArray = self.sendCommand(getSerialNumberSystemValueCmd)
        ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::getSerialNumberSystemValue() data: " + Utils.GetDataInHex(serialNumberArray, logging.DEBUG))
        serialNumber = serialNumberArray[6] << 24 | serialNumberArray[7] << 16 | serialNumberArray[8] << 8 | serialNumberArray[9]
        ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::getSerialNumberSystemValue() serialNumber: " + str(serialNumber))
        return serialNumber

    def getBackupPunchAsSIMessageArray(self, address):
        if self.siStationNumber is None:
            self.siStationNumber = self.getStationSettingSystemValue()[3]
        addressArr = [((address >> 16) & 0xFF), ((address >> 8) & 0xFF), (address & 0xFF)]
        getBackupPunchCmdArr = [0xFF, 0x02, 0x02, 0x81, 0x04, addressArr[0], addressArr[1], addressArr[2], 0x08, 0x00, 0x00, 0x03]
        crc = Utils.CalculateCRC(bytearray(bytes(getBackupPunchCmdArr[3:-3])))
        getBackupPunchCmdArr[9] = crc[0]
        getBackupPunchCmdArr[10] = crc[1]
        backupPunchRecord = self.sendCommand(bytes(getBackupPunchCmdArr))
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

    def updateComputerTimeAndSiStationNumber(self):
        theCurrentTimeInSiStation = self.getSIStationTimeAndStationNumber()
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
        self.siStationNumber = theCurrentTimeInSiStation[6]
        SettingsClass.SetSIStationNumber(self.siStationNumber)
        DatabaseHelper.change_future_created_dates()
        DatabaseHelper.change_future_sent_dates()


    def UpdateInfrequently(self):
        #SettingsClass.SetSIStationNumber(self.siStationNumber)
        return True

    def detectMissedPunchesDuringInit(self):
        lastAddr = ReceiveSIAdapter.AddressOfLastPunch.get(self.serialNumber, None)
        if lastAddr == None:
            return False
        getBackupPointerCmd = bytes([0xFF, 0x02, 0x02, 0x83, 0x02, 0x1C, 0x07, 0x74,0x06, 0x03])
        response = self.sendCommand(getBackupPointerCmd)
        SIMsg = SIMessage()
        SIMsg.AddPayload(response)
        if not SIMsg.GetIsChecksumOK():
            ReceiveSIAdapter.WiRocLogger.error("ReceiveSIAdapter::detectMissedPunchesDuringInit getBackupPointerCmd returned invalid checksum")
            return None
        curAddr = (response[7] << 16) | (response[11] << 8 ) | response[12] #next free memory address

        if curAddr > lastAddr:
            noOfMissedPunches = ((curAddr - lastAddr) / 8) -1
            if noOfMissedPunches > 0 and noOfMissedPunches <= 30:
                #We missed punches...
                ReceiveSIAdapter.WiRocLogger.info(
                    "ReceiveSIAdapter::detectMissedPunchesDuringInit Punches missed, lastAddr: " + str(lastAddr) + " curAddr: " + str(curAddr))
                self.fetchFromBackupAddress = lastAddr
                self.fetchToBackupAddress = curAddr
                self.fetchFromBackup = True

    def detectMissedPunches(self, siMsg):
        lastAddr = ReceiveSIAdapter.AddressOfLastPunch.get(self.serialNumber, None)
        curAddr = siMsg.GetBackupMemoryAddressAsInt()
        ReceiveSIAdapter.AddressOfLastPunch[self.serialNumber] = curAddr
        if lastAddr is None:
            return False
        if self.fetchFromBackup:
            #already in fetch from backup mode
            return False

        if curAddr > lastAddr:
            noOfMissedPunches = ((curAddr - lastAddr) / 8) -1
            if 0 < noOfMissedPunches <= 30:
                #We missed punches...
                ReceiveSIAdapter.WiRocLogger.info(
                    "ReceiveSIAdapter::detectMissedPunches Punches missed, lastAddr: " + str(
                        lastAddr) + " curAddr: " + str(curAddr))
                self.fetchFromBackupAddress = lastAddr
                self.fetchToBackupAddress = curAddr
                self.fetchFromBackup = True

    def getBackupPunch(self):
        if self.fetchFromBackup:
            addrToPunch = self.fetchFromBackupAddress + 8
            if addrToPunch < self.fetchToBackupAddress:
                SIMsgByteArray = self.getBackupPunchAsSIMessageArray(addrToPunch)
                if SIMsgByteArray is None:
                    return None
                self.fetchFromBackupAddress = addrToPunch
                source = "SIStation"
                ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::getBackupPunch Fetched backup punch")
                return {"MessageType": "DATA", "MessageSource": source,
                    "MessageSubTypeName": "SIMessage", "Data": SIMsgByteArray,
                    "ChecksumOK": self.IsChecksumOK(SIMsgByteArray)}
            else:
                self.fetchFromBackup = False
        return None

    # messageData is a bytearray
    def GetData(self):
        if self.siSerial.in_waiting == 0:
            if self.oneWay:
                return None
            else:
                return self.getBackupPunch()
        ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::GetData() Data to fetch")
        expectedLength = 3
        receivedData = bytearray()
        allReceivedData = bytearray()
        startFound = False
        while self.siSerial.in_waiting > 0:
            bytesRead = self.siSerial.read(1)
            allReceivedData.append(bytesRead[0])
            if bytesRead[0] == STX:
                startFound = True
                if len(receivedData) == 1:
                    # second STX found, discard
                    continue
            if startFound:
                receivedData.append(bytesRead[0])
                if len(receivedData) == 3:
                    expectedLength = receivedData[2]+6
                if len(receivedData) == expectedLength:
                    break
                if len(receivedData) < expectedLength and self.siSerial.in_waiting == 0:
                    ReceiveSIAdapter.WiRocLogger.debug("ReceiveSIAdapter::GetData() sleep and wait for more bytes")
                    sleep(0.05)

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

    def AddedToMessageBox(self, mbid):
        return None