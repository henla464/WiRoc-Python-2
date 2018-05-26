from chipGPIO.chipGPIO import *
import logging
import socket

class HardwareAbstraction(object):
    def __init__(self, typeOfDisplay):
        logging.info("HardwareAbstraction::Init start")
        self.typeOfDisplay = typeOfDisplay
        self.runningOnChip = socket.gethostname() == 'chip'

    def SetupPins(self):
        if socket.gethostname() == 'chip':
            pinMode(0, OUTPUT)
            pinMode(1, OUTPUT)
            pinMode(2, OUTPUT)
            pinMode(3, OUTPUT)
            pinMode(4, OUTPUT)
            pinMode(5, OUTPUT)
            pinMode(6, OUTPUT)
            pinMode(7, OUTPUT)
            if self.typeOfDisplay == '7SIG':
                pinModeNonXIO(138, INPUT)
                pinModeNonXIO(139, OUTPUT)
                digitalWriteNonXIO(139, 1)
            else: #OLED
                pinModeNonXIO(134, INPUT)
                pinModeNonXIO(135, OUTPUT)
                digitalWriteNonXIO(135, 1)

    def EnableLora(self):
        # disable radio module 139; #with new oled design: 135
        if self.typeOfDisplay == '7SEG':
            digitalWriteNonXIO(139, 0)
        else:
            digitalWriteNonXIO(135, 0)


    def DisableLora(self):
        # disable radio module 139; #with new oled design: 135
        if self.typeOfDisplay == '7SEG':
            digitalWriteNonXIO(139, 1)
        else:
            digitalWriteNonXIO(135, 1)

    def GetIsTransmittingReceiving(self):
        # aux 138, with new oled design: 134
        if self.typeOfDisplay == '7SEG':
            return digitalReadNonXIO(138) == 0
        else:
            return digitalReadNonXIO(134) == 0
