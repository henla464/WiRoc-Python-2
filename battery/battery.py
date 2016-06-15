__author__ = 'henla464'

import datetime, threading, time



class Battery:
    ReferenceFullBatteryValue = 9040
    DifferenceFromFullBatteryValue = [16, 24, 33, 41, 49, 59, 63, 69, 74, 81,
                                      84, 86, 87, 88, 90, 97, 106, 124, 140, 154]
    nextCallBatteryUpdate = time.time()

    def __init__(self, fullBatteryValue = 9040):
        self.FullBatteryValue = fullBatteryValue
        self.ScalingFactor = self.FullBatteryValue / self.ReferenceFullBatteryValue
        self.CurrentBatteryValue = self.FullBatteryValue

    def GetBatteryPercentage(self):
        for i in range(19, 0, -1):
            if (self.CurrentBatteryValue < self.FullBatteryValue - self.ScalingFactor*10*self.DifferenceFromFullBatteryValue[i]):
                return 100-5*(i+1)
        return 100

    def GetBatteryVoltage(self):
        return (self.CurrentBatteryValue*5.0/10240)

    def UpdateBattery(self):
        sensorValue = 0 #analogRead(A15) * 10
        self.CurrentBatteryValue = 0.995*self.CurrentBatteryValue + 0.005*sensorValue

    def SetupBatteryMonitorTimer(self):
        self.UpdateBattery()
        self.nextCallBatteryUpdate += 1
        threading.Timer(self.nextCallBatteryUpdate - time.time(), self.SetupBatteryMonitorTimer).start()
