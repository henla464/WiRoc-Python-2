from PIL import ImageFont
from display.displaystate import DisplayState


class OledDisplayState(DisplayState):
    OledDisp = None
    #OledAddress = 0x3c
    OledWidth = 0
    OledHeight = 0
    OledThinFont = ImageFont.truetype('display/GeosansLight.ttf', 10)
    OledThinFont2 = ImageFont.truetype('display/GeosansLight.ttf', 14)
    OledBoldFont = ImageFont.truetype('display/theboldfont.ttf', 44)

    def Draw(self, channel, ackRequested, wiRocMode, loraRange, deviceName, sirapTCPEnabled, sendSerialActive, sirapIPAddress, sirapIPPort, wiRocIPAddress):
        assert(0,"Draw not implemented")

    def Next(self):
        assert(0,"Next not implemented")