__author__ = 'henla464'

import unittest

from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.RSCoderLora import RSCoderLora


class TestLoraRadioDataHandler(unittest.TestCase):
                                        # stx         31                            37800=>10:30
    PunchMsg_Correct_1 = bytearray(bytes([0x02, 0x83, 0x1F, 0x00, 0x00, 0xFF, 0x00, 0X93, 0xA8, 0x00]))
    PunchMsg_Corrupted_1 = bytearray(bytes([0x02, 0x84, 0x10, 0x00, 0x01, 0xFF, 0x01, 0X93, 0xA8, 0x00]))

    PunchMsg_4bytes_Correct_1 = bytearray(bytes([0x02, 0x83, 0x1F, 0x00, 0x00, 0x00, 0xFF, 0x00, 0X93, 0xA8, 0x00]))
    PunchMsg_Correct_HighestTHTL = bytearray(bytes([0x02, 0x83, 0x1F, 0x00, 0x00, 0xFF, 0x00, 0XA8, 0xC0, 0x00]))

    dataHandler = LoraRadioDataHandler()

    def test_AddData(self):

        self.dataHandler.DataReceived = bytearray()
        self.dataHandler.AddData(bytearray([0x02]))
        self.assertEqual(self.dataHandler.DataReceived, bytearray([0x02]), "Adding data failed 1")

        self.dataHandler.AddData(bytearray([0x03, 0x04]))
        self.assertEqual(self.dataHandler.DataReceived, bytearray([0x02, 0x03, 0x04]), "Adding data failed 2")

    def test_IsLongEnoughToBeMessage(self):
        self.dataHandler.DataReceived = bytearray()
        self.dataHandler.AddData(bytearray([0x02,0x03,0x4]))
        couldBeMsg = self.dataHandler._IsLongEnoughToBeMessage()
        self.assertFalse(couldBeMsg, "3 bytes should not be a message")
        self.dataHandler.AddData(bytearray([0x02, 0x03, 0x4]))
        couldBeMsg = self.dataHandler._IsLongEnoughToBeMessage()
        self.assertFalse(couldBeMsg, "6 bytes should not be a message")
        self.dataHandler.AddData(bytearray([0x02, 0x03, 0x4]))
        couldBeMsg = self.dataHandler._IsLongEnoughToBeMessage()
        self.assertTrue(couldBeMsg, "9 bytes should be a message")


    def test_CacheMessage(self):
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1[1:])
        loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes)
        self.dataHandler.ReceivedPunchMessageDict = {}
        self.dataHandler.LastPunchMessageTime = None
        self.dataHandler.LastPunchMessage = None
        self.dataHandler._CacheMessage(loraMsg)
        msgAndMetaData = self.dataHandler.ReceivedPunchMessageDict[loraMsg.GetControlNumber()]
        self.assertEqual(loraMsg, msgAndMetaData.GetLoraRadioMessageRS())
        self.assertIsNotNone(self.dataHandler.LastPunchMessageTime)
        self.assertEqual(self.dataHandler.LastPunchMessage,loraMsg)

    def test_FindPunchErasures(self):
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1[1:])
        loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes)
        self.dataHandler.ReceivedPunchMessageDict = {}
        self.dataHandler.LastPunchMessageTime = None
        self.dataHandler.LastPunchMessage = None
        self.dataHandler._CacheMessage(loraMsg)

        # controlnumber bit 8
        corruptedMessageCNBit8 = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageCNBit8[6] = 0x40
        corruptedLoraMsgCNBit8 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(corruptedMessageCNBit8 + rsCodes)
        erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgCNBit8)
        self.assertEqual(erasures, [6], "controlnumber bit 8 erasure not correct")

        # ack requested
        corruptedMessageAckReq = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageAckReq[1] = corruptedMessageAckReq[1] & 0x7F
        corruptedLoraMsgAckReq = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(corruptedMessageAckReq + rsCodes)
        erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgAckReq)
        self.assertEqual(erasures, [1], "ackreq erasure not correct")

        #TH changed to more than 5 minutes more
        corruptedMessageTH = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageTH[7] = corruptedMessageTH[7] | 0x04
        corruptedLoraMsgTH = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            corruptedMessageTH + rsCodes)
        erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgTH)
        self.assertEqual(erasures, [7], "TH erasure not correct")

        #TH changed to higher than possible
        corruptedMessageTH2 = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageTH2[7] = 0xA9
        corruptedLoraMsgTH2 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            corruptedMessageTH2 + rsCodes)
        erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgTH2)
        self.assertEqual(erasures, [7], "TH erasure not correct")

        #TH changed to more than 5 minutes more and the combination TH TL too high
        corruptedMessageTL = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageTL[7] = 0xA8
        corruptedMessageTL[8] = 0xC1
        corruptedLoraMsgTL = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            corruptedMessageTL + rsCodes)
        erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgTL)
        self.assertEqual(erasures, [7], "TH, TL erasure not correct")

        #TL changed to higher than possible (TH already highest)
        rsCodes2 = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_HighestTHTL[1:])
        loraMsg2 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            TestLoraRadioDataHandler.PunchMsg_Correct_HighestTHTL + rsCodes2)
        self.dataHandler._CacheMessage(loraMsg2)
        corruptedMessageTL2 = TestLoraRadioDataHandler.PunchMsg_Correct_HighestTHTL[:]
        corruptedMessageTL2[8] = 0xC1
        corruptedLoraMsgTL2 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            corruptedMessageTL2 + rsCodes2)
        erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgTL2)
        self.assertEqual(erasures, [8], "TL erasure not correct")

        #TH changed to more than 5 minutes more and the combination TH TL too high
        corruptedMessageCN0 = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageCN0[2] = 0x20
        corruptedLoraMsgCN0 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            corruptedMessageCN0 + rsCodes)
        erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgCN0)
        self.assertEqual(erasures, [2], "TH, TL erasure not correct")

    def test_CheckAndRemoveLoraModuleRXError(self):
        rxerrorMessage = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        rxerrorMessage = "rx error\r\n".encode('latin-1') + rxerrorMessage
        for i in range(0, len(rxerrorMessage)):
            self.dataHandler.AddData(rxerrorMessage[i:i+1])
        self.assertFalse(self.dataHandler.RxError)
        self.assertEqual(rxerrorMessage, self.dataHandler.DataReceived)
        self.dataHandler._CheckAndRemoveLoraModuleRXError()
        self.assertTrue(self.dataHandler.RxError)
        self.assertEqual(TestLoraRadioDataHandler.PunchMsg_Correct_1, self.dataHandler.DataReceived)

    def test_GetMessageTypeByLength(self):
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1[1:])
        self.dataHandler.ReceivedPunchMessageDict = {}
        self.dataHandler.LastPunchMessageTime = None
        self.dataHandler.LastPunchMessage = None
        self.dataHandler.DataReceived = bytearray()
        for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i+1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i+1])
        msgType = self.dataHandler._GetMessageTypeByLength()
        self.assertEqual(msgType, 0x03, "Didn't get the expected message type")

        self.dataHandler.DataReceived = bytearray()
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_4bytes_Correct_1)
        for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_4bytes_Correct_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_4bytes_Correct_1[i:i+1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i+1])
        msgType = self.dataHandler._GetMessageTypeByLength()
        self.assertEqual(msgType, 0x04, "Didn't get the expected message type")


    def test_GetLikelyMessageTypes(self):
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1[1:])
        loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes)
        self.dataHandler.ReceivedPunchMessageDict = {}
        self.dataHandler.LastPunchMessageTime = None
        self.dataHandler.LastPunchMessage = None
        self.dataHandler._CacheMessage(loraMsg)
        self.dataHandler.DataReceived = bytearray()

        # controlnumber bit 8
        messageArr = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        for i in range(0, len(messageArr)):
            self.dataHandler.AddData(messageArr[i:i+1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i+1])
        messageTypes = self.dataHandler._GetLikelyMessageTypes()
        self.assertEqual(messageTypes, [0x03], "Didn't get the expected message type short punch")

        self.dataHandler.DataReceived = bytearray()

        # controlnumber bit 8
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_4bytes_Correct_1[1:])
        corruptedMsgType = TestLoraRadioDataHandler.PunchMsg_4bytes_Correct_1[:]
        corruptedMsgType[1] = 0x83
        for i in range(0, len(corruptedMsgType)):
            self.dataHandler.AddData(corruptedMsgType[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])

        messageTypes = self.dataHandler._GetLikelyMessageTypes()
        self.assertEqual(messageTypes, list({0x03, 0x04}), "Didn't get the expected message type, long punch with message type as short punch")

    def test_GetPunchMessage(self):
        #messageTypeToTry, erasures = None):
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1[1:])
        self.dataHandler.ReceivedPunchMessageDict = {}
        self.dataHandler.LastPunchMessageTime = None
        self.dataHandler.LastPunchMessage = None
        self.dataHandler.DataReceived = bytearray()
        for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])

        # wrong message type
        punchMsg = self.dataHandler._GetPunchMessage(0x04)
        self.assertIsNone(punchMsg)
        # right message type
        punchMsg = self.dataHandler._GetPunchMessage(0x03)
        self.assertIsNotNone(punchMsg)
        # returned message so buffer should be empty
        punchMsg = self.dataHandler._GetPunchMessage(0x03)
        self.assertIsNone(punchMsg)

        # Add two messages at once before trying to fetch the messages
        for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])
        for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])

        punchMsg = self.dataHandler._GetPunchMessage(0x03)
        self.assertIsNotNone(punchMsg)
        punchMsg = self.dataHandler._GetPunchMessage(0x03)
        self.assertIsNotNone(punchMsg)
        punchMsg = self.dataHandler._GetPunchMessage(0x03)
        self.assertIsNone(punchMsg)

    def test_GetMessage(self):
        # messageTypeToTry, erasures = None):
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1[1:])
        self.dataHandler.ReceivedPunchMessageDict = {}
        self.dataHandler.LastPunchMessageTime = None
        self.dataHandler.LastPunchMessage = None
        self.dataHandler.DataReceived = bytearray()
        for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])

        msg = self.dataHandler.GetMessage()
        self.assertEqual(TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes, msg.GetByteArray(), "Didn't receive the same bytes back")


        for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Corrupted_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Corrupted_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])
        print("before")
        msg2 = self.dataHandler.GetMessage()
        print("after")
        self.assertIsNone(msg2, "Received a message but it shouldn't be decodable")

        # correct one byte, then it should be decodable
        self.dataHandler.DataReceived[4] = 0x00
        msg3 = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg3, "Didn't receive a message, it should be decodable")
        #self.assertEqual(TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes, msg2.GetByteArray(), "Didn't receive a corrected message")
