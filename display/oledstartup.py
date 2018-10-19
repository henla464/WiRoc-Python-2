import display.displaystatemachine
import display.displaystate
from PIL import Image
from PIL import ImageDraw
import logging
from pathlib import Path

class OledStartup(display.displaystate.OledDisplayState):
    def __init__(self):
        self.imageChanged = True
        self.deviceName = None
        self.pythonVersion = Path('WiRocPythonVersion.txt').read_text()
        self.bleVersion = Path('WiRocBLEVersion.txt').read_text()
        self.OledImage = Image.new('1', (display.displaystate.OledDisplayState.OledWidth, display.displaystate.OledDisplayState.OledHeight))
        self.OledDraw = ImageDraw.Draw(self.OledImage)
        self.OledDraw.text((1, 1), 'WiRoc:' + self.pythonVersion, font=self.OledThinFont2, fill=255)
        self.OledDraw.text((41, 1), 'BLE:' + self.bleVersion, font=self.OledThinFont2, fill=255)


    def Draw(self,channel, ackRequested, wiRocMode, dataRate, deviceName):
        if self.deviceName != deviceName:
            self.deviceName = deviceName
            self.imageChanged = True
            logging.debug("OledStartup::Draw wirocMode imagechanged")
            self.OledDraw.rectangle((41, 16, 102, 31), outline=0, fill=0)
            self.OledDraw.text((41, 16), deviceName, font=self.OledThinFont2, fill=255)

        if self.imageChanged:
            display.displaystate.OledDisplayState.OledDisp.image(self.OledImage)
            self.OledDisp.display()

    def Next(self):
        # set imageChanged to true because next time this state is entered we
        # should draw the image
        self.imageChanged = True
        return display.displaystatemachine.DisplayStateMachine.OledNormal
