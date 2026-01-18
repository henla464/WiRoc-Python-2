__author__ = 'henla464'

import os
import time
import logging
from smbus2 import SMBus
import bisect

from chipGPIO.hardwareAbstraction import HardwareAbstraction


class Battery(object):
    WiRocLogger = logging.getLogger('WiRoc')
    timeChargingOrMaxCurrentDrawChangedFromNormal = None
    timeLastChargingConfigure = None
    currentMode = None
    limitCurrentMode = None
    wifiPowerSaving = None
    i2cAddress = 0x34
    i2cBus = None

    BatteryVoltagePercentageLookupList = [3.0008, 3.0492, 3.0855, 3.1295, 3.1669, 3.2065, 3.2450, 3.2725, 3.3000, 3.3275,
                                          3.3495, 3.3693, 3.3957, 3.4111, 3.4144, 3.4265, 3.4342, 3.4430, 3.4562, 3.4683,
                                          3.4793, 3.4892, 3.5002, 3.5189, 3.5299, 3.5409, 3.5497, 3.5563, 3.5651, 3.5739,
                                          3.5838, 3.5959, 3.6047, 3.6135, 3.6201, 3.6245, 3.6311, 3.6388, 3.6487, 3.6597,
                                          3.6718, 3.6784, 3.6905, 3.6960, 3.7037, 3.7147, 3.7224, 3.7378, 3.7477, 3.7543,
                                          3.7642, 3.7675, 3.7763, 3.7851, 3.7939, 3.8060, 3.8148, 3.8214, 3.8313, 3.8357,
                                          3.8423, 3.8533, 3.8621, 3.8742, 3.8819, 3.8874, 3.8962, 3.9050, 3.9094, 3.9193,
                                          3.9292, 3.9402, 3.9534, 3.9644, 3.9754, 3.9820, 3.9941, 4.0040, 4.0172, 4.0271,
                                          4.0348, 4.0403, 4.0458, 4.0469, 4.0480, 4.0513, 4.0524, 4.0546, 4.0567, 4.0601,
                                          4.0634, 4.0667, 4.0722, 4.0766, 4.0865, 4.0920, 4.1008, 4.1140, 4.1250, 4.1437]

    @classmethod
    def Setup(cls):
        if HardwareAbstraction.Instance is None:
            HardwareAbstraction.Instance = HardwareAbstraction()
        cls.i2cBus = SMBus(0)  # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)

    @classmethod
    def LimitCurrentDrawTo100IfBatteryOK(cls):
        if cls.limitCurrentMode != "100":
            if cls.GetBatteryPercent() > 20:
                Battery.WiRocLogger.info("Battery::LimitCurrentDrawTo100 Set to draw max 100mA from USB")
                os.system("sudo sh -c '/usr/sbin/i2cset -f -y 0 0x34 0x30 0x62'")
                cls.limitCurrentMode = "100"
            else:
                Battery.WiRocLogger.debug("Battery::LimitCurrentDrawTo100 Low battery so don't change max draw from USB")
        else:
            if cls.GetBatteryPercent() <= 18:
                Battery.WiRocLogger.info("Battery::LimitCurrentDrawTo100 Already 100 mA, but battery is low so set to 900")
                cls.LimitCurrentDrawTo900()
        cls.timeChargingOrMaxCurrentDrawChangedFromNormal = time.monotonic()

    @classmethod
    def LimitCurrentDrawTo900(cls):
        if cls.limitCurrentMode != "900":
            Battery.WiRocLogger.info("Battery::LimitCurrentDrawTo100 Set to draw max 900mA from USB")
            os.system("sudo sh -c '/usr/sbin/i2cset -f -y 0 0x34 0x30 0x60'")
            cls.limitCurrentMode = "900"
        cls.timeChargingOrMaxCurrentDrawChangedFromNormal = time.monotonic()

    @classmethod
    def DisableChargingIfBatteryOK(cls):
        if cls.currentMode != "DISABLED":
            if cls.GetBatteryPercent() > 15:
                Battery.WiRocLogger.info("Battery::DisableCharging Disable charging")
                os.system("sudo sh -c '/usr/sbin/i2cset -f -y 0 0x34 0x33 0x49'")
                cls.currentMode = "DISABLED"
            else:
                Battery.WiRocLogger.debug("Battery::DisableCharging Low battery so don't disable charging")
        else:
            if cls.GetBatteryPercent() <= 13:
                Battery.WiRocLogger.info("Battery::DisableCharging Already disabled, but battery is low so enable charging")
                cls.SetNormalCharging()
        cls.timeChargingOrMaxCurrentDrawChangedFromNormal = time.monotonic()

    @classmethod
    def SetSlowCharging(cls):
        if cls.currentMode != "SLOW":
            Battery.WiRocLogger.info("Battery::SetSlowCharging Charging set to slow")
            os.system("sudo sh -c '/usr/sbin/i2cset -f -y 0 0x34 0x33 0xC1'")
            cls.currentMode = "SLOW"
        cls.timeChargingOrMaxCurrentDrawChangedFromNormal = time.monotonic()

    @classmethod
    def SetNormalCharging(cls):
        if cls.currentMode != "NORMAL":
            Battery.WiRocLogger.info("Battery::SetNormalCharging Charging set to normal")
            os.system("sudo sh -c '/usr/sbin/i2cset -f -y 0 0x34 0x33 0xC9'")
            cls.currentMode = "NORMAL"
        cls.timeChargingOrMaxCurrentDrawChangedFromNormal = None

    @classmethod
    def GetPMUTemperature(cls):
        TEMPERATURE_MSB_REGADDR = 0x5e
        TEMPERATURE_LSB_REGADDR = 0x5f
        temperatureHighByte = cls.i2cBus.read_byte_data(cls.i2cAddress, TEMPERATURE_MSB_REGADDR)
        temperatureLowByte = cls.i2cBus.read_byte_data(cls.i2cAddress, TEMPERATURE_LSB_REGADDR)
        # PMU Internal temperature 000 is -144.7C steps of 0.1C, FFF is 264.8C
        temperatureCelsius = ((temperatureHighByte << 4 | (temperatureLowByte & 0xF)) - 1447) / 10
        return temperatureCelsius

    @classmethod
    def Tick(cls):
        if cls.timeLastChargingConfigure is None or \
                time.monotonic() > cls.timeLastChargingConfigure + 120:
            cls.timeLastChargingConfigure = time.monotonic()
            temperature = cls.GetPMUTemperature()
            if temperature > cls.GetPMUTemperature() > 85:
                if cls.currentMode != "SLOW":
                    cls.SetSlowCharging()
            elif temperature > 90:
                if cls.currentMode != "DISABLED":
                    cls.DisableChargingIfBatteryOK()
            else:
                if cls.currentMode != "NORMAL":
                    cls.SetNormalCharging()

    @classmethod
    def IsCharging(cls):
        logging.debug("Battery::IsCharging")
        # strValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0x01").read()
        POWERMODE_CHARGING_REGADDR = 0x01
        intValue = cls.i2cBus.read_byte_data(cls.i2cAddress, POWERMODE_CHARGING_REGADDR)
        # intValue = int(strValue, 16)
        isCharging = (intValue & 0x40) > 0
        return isCharging

    @classmethod
    def IsPowerSupplied(cls):
        Battery.WiRocLogger.debug("Battery::IsPowerSupplied")
        # strValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0x00").read()
        POWER_STATUS_REGADDR = 0x00
        intValue = cls.i2cBus.read_byte_data(cls.i2cAddress, POWER_STATUS_REGADDR)
        # intValue = int(strValue, 16)
        isPowerSupplied = (intValue & 0x10) > 0
        return isPowerSupplied

    @classmethod
    def GetIsBatteryLow(cls):
        #Battery.WiRocLogger.debug("Battery::GetIsBatteryLow")
        intPercentValue = cls.GetBatteryPercent()
        isBatteryLow = (intPercentValue < 30)
        return isBatteryLow

    @classmethod
    def GetBatteryVoltage(cls) -> float:
        # Battery.WiRocLogger.debug("Battery::GetBatteryVoltage")
        BATTERY_VOLTAGE_HIGH_REGADDR: int = 0x78
        BATTERY_VOLTAGE_LOW_REGADDR: int = 0x79
        intHighValue = cls.i2cBus.read_byte_data(cls.i2cAddress, BATTERY_VOLTAGE_HIGH_REGADDR)
        intLowValue = cls.i2cBus.read_byte_data(cls.i2cAddress, BATTERY_VOLTAGE_LOW_REGADDR)
        voltageRaw = (intHighValue << 4) | (intLowValue & 0x0F)
        voltage_mV = voltageRaw * 1.1  # each bit = 1.1 mV
        voltage_V = voltage_mV / 1000.0  # convert to volts
        return voltage_V

    @classmethod
    def GetBatteryPercent(cls) -> int:
        # Battery.WiRocLogger.debug("Battery::GetBatteryPercent")
        batVolt = cls.GetBatteryVoltage()
        batPerc = bisect.bisect_left(cls.BatteryVoltagePercentageLookupList, batVolt)
        Battery.WiRocLogger.debug("Battery::GetBatteryPercent: " + str(batPerc) + "%")
        return batPerc

    @classmethod
    def GetBatteryPercent4Bits(cls):
        Battery.WiRocLogger.debug("Battery::GetBatteryPercent4Bits")
        # strPercentValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0xb9").read()
        intPercentValue = cls.GetBatteryPercent()
        intPercentValue = min(intPercentValue, 100)
        batteryPercent4Bit = int(intPercentValue * 15 / 100)
        return batteryPercent4Bit

    @classmethod
    def UpdateWifiPowerSaving(cls, sendToSirap):
        if sendToSirap and (cls.wifiPowerSaving or cls.wifiPowerSaving is None):
            # disable power saving
            Battery.WiRocLogger.info("Start::updateWifiPowerSaving() Disable WiFi power saving")
            wlanIFace = HardwareAbstraction.Instance.GetBuiltinWifiInterfaceName()
            os.system(f"sudo iw {wlanIFace} set power_save off")
            cls.wifiPowerSaving = False
        elif not sendToSirap and (not cls.wifiPowerSaving or cls.wifiPowerSaving is None):
            # enable power saving
            Battery.WiRocLogger.info("Start::updateWifiPowerSaving() Enable WiFi power saving")
            wlanIFace = HardwareAbstraction.Instance.GetBuiltinWifiInterfaceName()
            os.system("sudo iw {wlanIFace} set power_save on")
            cls.wifiPowerSaving = True
