class DisplayState(object):
    ackRequested = None
    channel = None

    def Draw(self, channel, ackRequested, wiRocMode, dataRate, deviceName, sirapTCPEnabled, sendSerialActive, sirapIPAddress, sirapIPPort, wiRocIPAddress):
        assert(0,"Draw not implemented")

    def Next(self):
        assert(0,"Next not implemented")
