import display.displaystatemachine
import display.displaystate
from display.oleddisplaystate import OledDisplayState
from PIL import Image
from PIL import ImageDraw
import logging
from pathlib import Path


class OledStartup(OledDisplayState):
    def __init__(self):
        self.wiRocLogger = logging.getLogger('WiRoc.Display')
        self.imageChanged = True
        self.deviceName = None
        self.pythonVersion = "err"
        self.bleVersion = "err"
        try:
            with open('../WiRocPythonVersion.txt', 'r') as versionFile:
                self.pythonVersion = versionFile.read()
        except:
            pass
        try:
            with open('../WiRocBLEVersion.txt', 'r') as versionFile:
                self.bleVersion = versionFile.read()
        except:
            pass
        self.OledImage = Image.new('1', (OledDisplayState.OledWidth, OledDisplayState.OledHeight))
        self.OledDraw = ImageDraw.Draw(self.OledImage)
        self.OledDraw.text((3, 1), self.pythonVersion, font=self.OledThinFont2, fill=255)
        self.OledDraw.text((60, 1), 'BLE: ' + self.bleVersion, font=self.OledThinFont2, fill=255)

    def Draw(self,channel, ackRequested, wiRocMode, loraRange, deviceName, sirapTCPEnabled, sendSerialActive, sirapIPAddress, sirapIPPort, wiRocIPAddress):
        if self.deviceName != deviceName:
            self.deviceName = deviceName
            self.imageChanged = True
            self.wiRocLogger.debug("OledStartup::Draw imagechanged")
            self.OledDraw.rectangle((1, 16, 128, 31), outline=0, fill=0)
            self.OledDraw.text((1, 16), deviceName, font=self.OledThinFont2, fill=255)

        if self.imageChanged:
            self.imageChanged = False
            OledDisplayState.OledDisp.image(self.OledImage)
            OledDisplayState.OledDisp.display()

    def Next(self):
        # set imageChanged to true because next time this state is entered we
        # should draw the image
        self.imageChanged = True
        return display.displaystatemachine.DisplayStateMachine.OledNormal
