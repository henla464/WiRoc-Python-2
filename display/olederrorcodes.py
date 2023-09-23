import display.displaystatemachine
import display.displaystate
from display.oleddisplaystate import OledDisplayState
from PIL import Image
from PIL import ImageDraw
from battery import Battery
import logging
from chipGPIO.hardwareAbstraction import HardwareAbstraction
from display.displaydata import DisplayData


class OledErrorCodes(OledDisplayState):
    def __init__(self):
        self.wiRocLogger = logging.getLogger('WiRoc.Display')
        self.imageChanged = True
        self.errorCodeMessage = None
        self.OledImage = Image.new('1', (OledDisplayState.OledWidth, OledDisplayState.OledHeight))
        self.OledDraw = ImageDraw.Draw(self.OledImage)
        self.OledDraw.text((3, 1), "Error:", font=self.OledThinFont2, fill=255)

    def Draw(self, displayData: DisplayData):

        if len(displayData.errorCodes) > 0 and self.errorCodeMessage != displayData.errorCodes[0].Message:
            self.errorCodeMessage = displayData.errorCodes[0].Message
            self.imageChanged = True
            self.wiRocLogger.debug("OledErrorCodes::Draw error message changed")
            self.OledDraw.rectangle((1, 16, 128, 31), outline=0, fill=0)
            if len(self.errorCodeMessage) > 0:
                self.OledDraw.text((2, 16), self.errorCodeMessage, font=self.OledThinFont2, fill=255)

        if self.imageChanged:
            self.imageChanged = False
            OledDisplayState.OledDisp.image(self.OledImage)
            self.OledDisp.show()

    def Next(self):
        # set imageChanged to true because next time this state is entered we
        # should draw the image
        self.imageChanged = True
        return display.displaystatemachine.DisplayStateMachine.OledStartup
