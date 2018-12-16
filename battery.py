__author__ = 'henla464'

import os
import time
from settings.settings import SettingsClass
import logging
import socket

class Battery(object):
    timeChargingOrMaxCurrentDrawChangedFromNormal = None
    currentMode = None
    limitCurrentMode = None
    isRunningOnChip = False
    isRunningOnNanoPi = False
    wifiPowerSaving = None

    @classmethod
    def Setup(cls):
        cls.isRunningOnChip = (socket.gethostname() == 'chip')
        cls.isRunningOnNanoPi = (socket.gethostname() == 'nanopiair')

    @classmethod
    def LimitCurrentDrawTo100IfBatteryOK(cls):
        if cls.isRunningOnChip or cls.isRunningOnNanoPi:
            if cls.limitCurrentMode != "100":
                if cls.GetBatteryPercent() > 20:
                    logging.info("Battery::LimitCurrentDrawTo100 Set to draw max 100mA from USB")
                    os.system("sudo sh -c '/usr/sbin/i2cset -f -y 0 0x34 0x30 0x62'")
                    cls.limitCurrentMode = "100"
                else:
                    logging.debug("Battery::LimitCurrentDrawTo100 Low battery so don't change max draw from USB")
            else:
                if cls.GetBatteryPercent() <= 18:
                    logging.info("Battery::LimitCurrentDrawTo100 Already 100 mA, but battery is low so set to 900")
                    cls.LimitCurrentDrawTo900()
        cls.timeChargingOrMaxCurrentDrawChangedFromNormal = time.monotonic()

    @classmethod
    def LimitCurrentDrawTo900(cls):
        if (cls.isRunningOnChip or cls.isRunningOnNanoPi) and cls.limitCurrentMode != "900":
            logging.info("Battery::LimitCurrentDrawTo100 Set to draw max 900mA from USB")
            os.system("sudo sh -c '/usr/sbin/i2cset -f -y 0 0x34 0x30 0x60'")
            cls.limitCurrentMode = "900"
        cls.timeChargingOrMaxCurrentDrawChangedFromNormal = time.monotonic()

    @classmethod
    def DisableChargingIfBatteryOK(cls):
        if cls.isRunningOnChip or cls.isRunningOnNanoPi:
            if cls.currentMode != "DISABLED":
                if cls.GetBatteryPercent() > 15:
                    logging.info("Battery::DisableCharging Disable charging")
                    os.system("sudo sh -c '/usr/sbin/i2cset -f -y 0 0x34 0x33 0x49'")
                    cls.currentMode = "DISABLED"
                else:
                    logging.debug("Battery::DisableCharging Low battery so don't disable charging")
            else:
                if cls.GetBatteryPercent() <= 13:
                    logging.info("Battery::DisableCharging Already disabled, but battery is low so enable charging")
                    cls.SetNormalCharging()
        cls.timeChargingOrMaxCurrentDrawChangedFromNormal = time.monotonic()

    @classmethod
    def SetSlowCharging(cls):
        if (cls.isRunningOnChip  or cls.isRunningOnNanoPi) and cls.currentMode != "SLOW":
            logging.info("Battery::SetSlowCharging Charging set to slow")
            os.system("sudo sh -c '/usr/sbin/i2cset -f -y 0 0x34 0x33 0xC1'")
            cls.currentMode = "SLOW"
        cls.timeChargingOrMaxCurrentDrawChangedFromNormal = time.monotonic()

    @classmethod
    def SetNormalCharging(cls):
        if (cls.isRunningOnChip  or cls.isRunningOnNanoPi) and cls.currentMode != "NORMAL":
            logging.info("Battery::SetNormalCharging Charging set to normal")
            os.system("sudo sh -c '/usr/sbin/i2cset -f -y 0 0x34 0x33 0xC9'")
            cls.currentMode = "NORMAL"
        cls.timeChargingOrMaxCurrentDrawChangedFromNormal = None

    @classmethod
    def Tick(cls):
        if cls.timeChargingOrMaxCurrentDrawChangedFromNormal is not None and \
                        time.monotonic() > cls.timeChargingOrMaxCurrentDrawChangedFromNormal + 6 * SettingsClass.GetReconfigureInterval():
            cls.SetNormalCharging()
            cls.LimitCurrentDrawTo900()

    @classmethod
    def IsCharging(cls):
        if cls.isRunningOnChip or cls.isRunningOnNanoPi:
            logging.debug("Battery::IsCharging")
            strValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0x01").read()
            intValue = int(strValue, 16)
            isCharging = (intValue & 0x40) > 0
            return isCharging
        return True

    @classmethod
    def IsPowerSupplied(cls):
        if cls.isRunningOnChip or cls.isRunningOnNanoPi:
            logging.debug("Battery::IsPowerSupplied")
            strValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0x00").read()
            intValue = int(strValue, 16)
            isPowerSupplied = (intValue & 0x10) > 0
            return isPowerSupplied
        return False

    @classmethod
    def GetIsBatteryLow(cls):
        if cls.isRunningOnChip or cls.isRunningOnNanoPi:
            logging.debug("Battery::GetIsBatteryLow")
            strPercentValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0xb9").read()
            intPercentValue = int(strPercentValue, 16)
            isBatteryLow = (intPercentValue < 30)
            return isBatteryLow
        return False

    @classmethod
    def GetBatteryPercent(cls):
        if cls.isRunningOnChip or cls.isRunningOnNanoPi:
            logging.debug("Battery::GetBatteryPercent")
            strPercentValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0xb9").read()
            intPercentValue = int(strPercentValue, 16)
            return intPercentValue
        return 100


    @classmethod
    def GetBatteryPercent4Bits(cls):
        if cls.isRunningOnChip or cls.isRunningOnNanoPi:
            logging.debug("Battery::GetBatteryPercent4Bits")
            strPercentValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0xb9").read()
            intPercentValue = min(int(strPercentValue, 16), 100)
            batteryPercent4Bit = int(intPercentValue * 15 / 100)
            return batteryPercent4Bit
        return 15

    @classmethod
    def UpdateWifiPowerSaving(cls, sendToMeos):
        if cls.isRunningOnChip or cls.isRunningOnNanoPi:
            if sendToMeos and (cls.wifiPowerSaving or cls.wifiPowerSaving is None):
                # disable power saving
                logging.info("Start::updateWifiPowerSaving() Disable WiFi power saving")
                os.system("sudo iw wlan0 set power_save off")
                cls.wifiPowerSaving = False
            elif not sendToMeos and (not cls.wifiPowerSaving or cls.wifiPowerSaving is None):
                # enable power saving
                logging.info("Start::updateWifiPowerSaving() Enable WiFi power saving")
                os.system("sudo iw wlan0 set power_save on")
                cls.wifiPowerSaving = True