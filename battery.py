__author__ = 'henla464'

import os
import time
from settings.settings import SettingsClass
import logging
import socket

class Battery(object):
    timeChargingChangedFromNormal = None
    currentMode = None
    isRunningOnChip = False

    @classmethod
    def Setup(cls):
        cls.isRunningOnChip = (socket.gethostname() == 'chip')

    @classmethod
    def DisableCharging(cls):
        if cls.isRunningOnChip and cls.currentMode != "DISABLED":
            logging.info("Battery::DisableCharging Disable charging")
            os.system("sudo sh -c '/usr/sbin/i2cset -f -y 0 0x34 0x33 0x49'")
            cls.currentMode = "DISABLED"
        cls.timeChargingChangedFromNormal = time.monotonic()

    @classmethod
    def SetSlowCharging(cls):
        if cls.isRunningOnChip and cls.currentMode != "SLOW":
            logging.info("Battery::SetSlowCharging Charging set to slow")
            os.system("sudo sh -c '/usr/sbin/i2cset -f -y 0 0x34 0x33 0xC1'")
            cls.currentMode = "SLOW"
        cls.timeChargingChangedFromNormal = time.monotonic()

    @classmethod
    def SetNormalCharging(cls):
        if cls.isRunningOnChip and cls.currentMode != "NORMAL":
            logging.info("Battery::SetNormalCharging Charging set to normal")
            os.system("sudo sh -c '/usr/sbin/i2cset -f -y 0 0x34 0x33 0xC9'")
            cls.currentMode = "NORMAL"
        cls.timeChargingChangedFromNormal = None

    @classmethod
    def Tick(cls):
        if cls.timeChargingChangedFromNormal is not None and \
                        time.monotonic() > cls.timeChargingChangedFromNormal + 6 * SettingsClass.GetReconfigureInterval():
            cls.SetNormalCharging()

    @classmethod
    def IsCharging(cls):
        if cls.isRunningOnChip:
            logging.debug("Battery::IsCharging")
            strValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0x01").read()
            intValue = int(strValue, 16)
            isCharging = (intValue & 0x40) > 0
            return isCharging
        return False

    @classmethod
    def IsPowerSupplied(cls):
        if cls.isRunningOnChip:
            logging.debug("Battery::IsPowerSupplied")
            strValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0x00").read()
            intValue = int(strValue, 16)
            isPowerSupplied = (intValue & 0x10) > 0
            return isPowerSupplied
        return False

    @classmethod
    def GetIsBatteryLow(cls):
        if cls.isRunningOnChip:
            logging.debug("Battery::GetIsBatteryLow")
            strPercentValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0xb9").read()
            intPercentValue = int(strPercentValue, 16)
            isBatteryLow = (intPercentValue < 30)
            return isBatteryLow
        return False

    @classmethod
    def GetBatteryPercent(cls):
        if cls.isRunningOnChip:
            logging.debug("Battery::GetBatteryPercent")
            strPercentValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0xb9").read()
            intPercentValue = int(strPercentValue, 16)
            return intPercentValue
        return 100


    @classmethod
    def GetBatteryPercent4Bits(cls):
        if cls.isRunningOnChip:
            logging.debug("Battery::GetBatteryPercent4Bits")
            strPercentValue = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0xb9").read()
            intPercentValue = min(int(strPercentValue, 16), 100)
            batteryPercent4Bit = int(intPercentValue * 15 / 100)
            return batteryPercent4Bit
        return 15