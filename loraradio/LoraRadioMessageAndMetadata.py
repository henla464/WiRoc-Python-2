__author__ = 'henla464'

import time

class LoraRadioMessageAndMetadata(object):
    def __init__(self, loraRadioMessage):
        self.loraRadioMessage = loraRadioMessage
        self.timeCreated = time.monotonic()

    def GetLoraRadioMessageRS(self):
        return self.loraRadioMessage

    def GetTimeCreated(self):
        return self.timeCreated
