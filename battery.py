__author__ = 'henla464'

import os
import time
import logging
import socket
from smbus2 import SMBus


class Battery(object):
    WiRocLogger = logging.getLogger('WiRoc')
    timeChargingOrMaxCurrentDrawChangedFromNormal = None
    timeLastChargingConfigure = None
    currentMode = None
    limitCurrentMode = None
    wifiPowerSaving = None
    i2cAddress = 0x34
    i2cBus = None

    @classmethod
    def Setup(cls):
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
        #strValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0x01").read()
        POWERMODE_CHARGING_REGADDR = 0x01
        intValue = cls.i2cBus.read_byte_data(cls.i2cAddress, POWERMODE_CHARGING_REGADDR)
        #intValue = int(strValue, 16)
        isCharging = (intValue & 0x40) > 0
        return isCharging

    @classmethod
    def IsPowerSupplied(cls):
        Battery.WiRocLogger.debug("Battery::IsPowerSupplied")
        #strValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0x00").read()
        POWER_STATUS_REGADDR = 0x00
        intValue = cls.i2cBus.read_byte_data(cls.i2cAddress, POWER_STATUS_REGADDR)
        #intValue = int(strValue, 16)
        isPowerSupplied = (intValue & 0x10) > 0
        return isPowerSupplied

    @classmethod
    def GetIsBatteryLow(cls):
        Battery.WiRocLogger.debug("Battery::GetIsBatteryLow")
        intPercentValue = cls.GetBatteryPercent()
        isBatteryLow = (intPercentValue < 30)
        return isBatteryLow

    @classmethod
    def GetBatteryPercent(cls):
        Battery.WiRocLogger.debug("Battery::GetBatteryPercent")
        #strPercentValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0xb9").read()
        POWER_MEASUREMENT_RESULT_REGADDR = 0xb9
        intPercentValue = cls.i2cBus.read_byte_data(cls.i2cAddress, POWER_MEASUREMENT_RESULT_REGADDR)
        #intPercentValue = int(strPercentValue, 16)
        return intPercentValue

    @classmethod
    def GetBatteryPercent4Bits(cls):
        Battery.WiRocLogger.debug("Battery::GetBatteryPercent4Bits")
        #strPercentValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0xb9").read()
        intPercentValue = cls.GetBatteryPercent()
        intPercentValue = min(intPercentValue, 100)
        batteryPercent4Bit = int(intPercentValue * 15 / 100)
        return batteryPercent4Bit

    @classmethod
    def UpdateWifiPowerSaving(cls, sendToSirap):
        if sendToSirap and (cls.wifiPowerSaving or cls.wifiPowerSaving is None):
            # disable power saving
            Battery.WiRocLogger.info("Start::updateWifiPowerSaving() Disable WiFi power saving")
            os.system("sudo iw wlan0 set power_save off")
            cls.wifiPowerSaving = False
        elif not sendToSirap and (not cls.wifiPowerSaving or cls.wifiPowerSaving is None):
            # enable power saving
            Battery.WiRocLogger.info("Start::updateWifiPowerSaving() Enable WiFi power saving")
            os.system("sudo iw wlan0 set power_save on")
            cls.wifiPowerSaving = True