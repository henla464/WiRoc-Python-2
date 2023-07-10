from settings.settings import SettingsClass
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
import logging
import smbus


class ReceiveSRRAdapter(object):
    Instances = []

    @staticmethod
    def CreateInstances(hardwareAbstraction):
        if hardwareAbstraction.wirocHWVersion == "v6Rev1":
            if len(ReceiveSRRAdapter.Instances) == 0:
                bus = smbus.SMBus(0)  # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
                addr = 0x20

                try:
                    # firmware version
                    firmwareVersion = bus.read_byte_data(addr, 0x00)

                    # hardware features
                    hardwareFeatures = bus.read_byte_data(addr, 0x01)

                    RED_CHANNEL = 0x01
                    BLUE_CHANNEL = 0x02
                    if hardwareFeatures & RED_CHANNEL or hardwareFeatures & BLUE_CHANNEL:
                        # Listens for messages on at least one of the two SRR channels.
                        ReceiveSRRAdapter.Instances.append(ReceiveSRRAdapter("SRR1", bus, addr, firmwareVersion, hardwareFeatures, hardwareAbstraction))
                    return True
                except Exception as err:
                    logging.getLogger('WiRoc.Input').error(
                        "ReceiveSRRAdapter::CreateInstances() Exception: " + str(err))
        return False

    @staticmethod
    def GetTypeName():
        return "SRR"

    def __init__(self, instanceName, i2cBus, i2cAddress, firmwareVersion, hardwareFeatures, hardwareAbstraction):
        self.WiRocLogger = logging.getLogger('WiRoc.Input')
        self.instanceName = instanceName
        self.isInitialized = False
        self.i2cBus = i2cBus
        self.i2cAddress = i2cAddress
        self.firmwareVersion = firmwareVersion
        self.hardwareFeatures = hardwareFeatures
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
        return True

    def GetData(self):
        if self.hardwareAbstraction.GetSRRIRQValue():
            # punch length
            PUNCH_LENGTH_REGADDR = 0x20
            punchLength = self.i2cBus.read_byte_data(self.i2cAddress, PUNCH_LENGTH_REGADDR)

            if punchLength == 0:
                return None

            # read punch
            SET_DATA_INDEX_REGADDR = 0x05
            PUNCH_REGADDR = 0x40
            index = 0
            if punchLength > 0:  # and (status & 0x01) > 0:
                while index < punchLength:
                    self.i2cBus.write_byte_data(self.i2cAddress, SET_DATA_INDEX_REGADDR, index)
                    remaining = punchLength - index
                    noToRead = remaining
                    if remaining > 31:
                        noToRead = 31
                    data = self.i2cBus.read_i2c_block_data(self.i2cAddress, PUNCH_REGADDR, noToRead)
                    index += noToRead

                self.WiRocLogger.debug("ReceiveSRRAdapter::GetData() Data to fetch")
                return {"MessageType": "DATA", "MessageSubTypeName": "SRRMessage", "MessageSource": "SRR", "Data": data, "ChecksumOK": True}
        return None

    def AddedToMessageBox(self, mbid):
        return None
