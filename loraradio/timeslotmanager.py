__author__ = 'henla464'

from datamodel.datamodel import TimeSlotData
from datamodel.db_helper import DatabaseHelper
from constants import *

class TimeSlotManager:
    settings = None

    def __init__(self, settings):
        self.settings = settings

    def GetTimeSlotData(self, radioNumber):
        nodes = self.settings.GetInboundRadioNodes(radioNumber)
        timeSlotRecords = []
        for node in nodes:
            timeSlot = TimeSlotData(1, node.NodeNumber, 0)
            timeSlotRecords.append(timeSlot)

        # !!! get message only for the radioNumber
        radioMessages = DatabaseHelper.get_last_x_radio_message_data(MAX_NO_OF_TIMESLOTS_PER_ROUND)
        for radioMessage in radioMessages:
            if not radioMessage.ackSent:
                messageNumberAddedToTimeSlot = False
                for timeSlotRecord in timeSlotRecords:
                    if timeSlotRecord.nodeNumber == radioMessage.fromNode \
                            and timeSlotRecord.messageNumber == 0:
                        timeSlotRecord.messageNumber = radioMessage.messageNumber
                        messageNumberAddedToTimeSlot = True

                if not messageNumberAddedToTimeSlot:
                    timeSlot = TimeSlotData(0, radioMessage.fromNode, radioMessage.messageNumber)
                    timeSlotRecords.append(timeSlot)
                radioMessage.ackSent = True
                DatabaseHelper.save_radio_message(radioMessage)
        return timeSlotRecords