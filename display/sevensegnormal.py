import display.displaystatemachine
import display.displaystate
from chipGPIO.chipGPIO import *

class SevenSegNormal(display.displaystate.DisplayState):
    def Draw(self,channel, ackRequested, wiRocMode, dataRate, deviceName):
        # def displayChannel(self, channel, ackRequested):
        if channel != display.displaystate.DisplayState.channel or ackRequested != display.displaystate.DisplayState.ackRequested:
            self.channel = channel
            self.ackRequested = ackRequested
            lightSegA = channel in [2, 3, 5, 6, 7, 8, 9]
            lightSegB = channel in [1, 2, 3, 4, 7, 8, 9]
            lightSegC = channel in [1, 3, 4, 5, 6, 7, 8, 9]
            lightSegD = channel in [2, 3, 5, 6, 8]
            lightSegE = channel in [2, 6, 8]
            lightSegF = channel in [4, 5, 6, 8, 9]
            lightSegG = channel in [2, 3, 4, 5, 6, 8, 9]

            if True:
                lightSegA = not lightSegA
                lightSegB = not lightSegB
                lightSegC = not lightSegC
                lightSegD = not lightSegD
                lightSegE = not lightSegE
                lightSegF = not lightSegF
                lightSegG = not lightSegG
                ackRequested = not ackRequested

            digitalWrite(0, int(lightSegA))
            digitalWrite(1, int(lightSegB))
            digitalWrite(2, int(lightSegC))
            digitalWrite(3, int(lightSegD))
            digitalWrite(4, int(lightSegE))
            digitalWrite(5, int(lightSegF))
            digitalWrite(6, int(lightSegG))

            digitalWrite(7, int(ackRequested))
        return None

    def Next(self):
        return display.displaystatemachine.DisplayStateMachine.SevenSegNormal
