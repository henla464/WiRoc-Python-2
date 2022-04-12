__author__ = 'henla464'

import logging
import unittest

from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
from loraradio.RSCoderLora import RSCoderLora

# Run with python3 -m unittest loraradio/TestLoraRadioDataHandler.py
class TestLoraRadioDataHandler(unittest.TestCase):
                                        # stx         31                            37800=>10:30
    PunchMsg_Correct_1 =   bytearray(bytes([0x83, 0x1F, 0x00, 0x00, 0x00, 0xFF, 0x00, 0X93, 0xA8, 0x00]))
    PunchDoubleMsg_Correct_1 = bytearray(bytes([0x86, 0xff, 0x00, 0x00, 0x63, 0x67, 0x00, 0x03, 0x86, 0x12, 0xff, 0x00, 0x00, 0x63, 0x67, 0x00, 0x0c, 0x9d, 0x6e]))
    PunchMsg_Corrupted_1 = bytearray(bytes([0x84, 0x10, 0x00, 0x00, 0x01, 0xFF, 0x01, 0X93, 0xA8, 0x00]))
    PunchDoubleMsg_Corrupted_1 = bytearray(bytes([0x86, 0xff, 0x01, 0x01, 0x63, 0x67, 0x01, 0x03, 0x86, 0x12, 0xff, 0x01, 0x01, 0x63, 0x67, 0x01, 0x0c, 0x9d, 0x6e]))

    # ---
    Case1_PunchDoubleMsg_Previous_WithRS = bytearray(bytes([0x86, 0xe7, 0x00, 0x0f, 0x42, 0x3f, 0x40, 0x8f, 0xe1, 0x9a, 0xe7, 0x00, 0x0f, 0x42, 0x3f, 0x40, 0x8f, 0xe2, 0x1b, 0x32, 0xaa, 0x8b, 0x50, 0x3e, 0xaa, 0x4a, 0x99]))
    Case1_PunchDoubleMsg_Corrupted_WithRS = bytearray(bytes([0x06, 0x6f, 0x08, 0x07, 0x42, 0x95, 0x6a, 0x8d, 0xa2, 0x9b, 0xe7, 0x44, 0x0b, 0x42, 0x3f, 0x40, 0x8f, 0xf2, 0x1c, 0x4a, 0xf8, 0xa9, 0x52, 0x81, 0xf1, 0xd8, 0xe0]))
    # The correct message for the PunchDoubleMsg_Corrupted_2_WithRS is: 06 6f 08 07 42 95 6a 8d a2 9b e7 44 0b 42 3f 40 8f f2 1c 4a f8 a9 52 81 f1 d8 e0  (so wrong in positions: 0  1  2  3, 5, 6, 7, 8, 11, 12, 17, 18, 19, 20)
    # ---

    # ---
    Case1_PunchMsg_Previous_WithRS = bytearray(bytes([0x83, 0xe7, 0x00, 0x0f, 0x42, 0x3f, 0x40, 0x91, 0x9e, 0x89, 0x75, 0xa9, 0x83, 0x8f]))
    Case1_PunchMsg_Correct_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x1f, 0x15, 0x8e, 0x0c, 0x91, 0xdf, 0x4f, 0x6c, 0x99, 0x0f, 0xe0]))
    Case1_PunchMsg_Corrupted_WithRS = bytearray(bytes([0x93, 0x11, 0x01, 0x1e, 0x14, 0x8e, 0x0c, 0x91, 0x1f, 0x6f, 0xa8, 0x55, 0xad, 0x1d]))
    # -- wrong in positions 0, 1, 2, 3, 4, 8, 9, 10, 11, 12, 13

    PunchMsg_Correct_HighestTHTL = bytearray(bytes([0x83, 0x1F, 0x00, 0x00, 0x00, 0xFF, 0x00, 0XA8, 0xC0, 0x00]))
    StatusMsg_Correct_WithRS = bytearray(bytes([0xa4, 0xe0, 0x58, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef, 0xa0, 0xe5, 0xb6]))

    dataHandler = LoraRadioDataHandler(False)

    def setUp(self):
        LoraRadioDataHandler.WiRocLogger.setLevel(logging.DEBUG)

    def tearDown(self):
        self.dataHandler.ReceivedPunchMessageDict = {}
        self.dataHandler.LastPunchMessageTime = None
        self.dataHandler.LastPunchMessage = None
        self.dataHandler.DataReceived = bytearray()

    def test_AddData(self):
        print("=== START test_AddData ===")
        self.dataHandler.AddData(bytearray([0x02]))
        self.assertEqual(self.dataHandler.DataReceived, bytearray([0x02]), "Adding data failed 1")

        self.dataHandler.AddData(bytearray([0x03, 0x04]))
        self.assertEqual(self.dataHandler.DataReceived, bytearray([0x02, 0x03, 0x04]), "Adding data failed 2")
        print("=== END test_AddData ===")

    def test_IsLongEnoughToBeMessage(self):
        print("=== START test_IsLongEnoughToBeMessage ===")
        self.dataHandler.AddData(bytearray([0x02,0x03,0x4]))
        couldBeMsg = self.dataHandler._IsLongEnoughToBeMessage()
        self.assertFalse(couldBeMsg, "3 bytes should not be a message")
        self.dataHandler.AddData(bytearray([0x02, 0x03, 0x4]))
        couldBeMsg = self.dataHandler._IsLongEnoughToBeMessage()
        self.assertFalse(couldBeMsg, "6 bytes should not be a message")
        self.dataHandler.AddData(bytearray([0x02, 0x03, 0x4]))
        couldBeMsg = self.dataHandler._IsLongEnoughToBeMessage()
        self.assertTrue(couldBeMsg, "9 bytes should be a message")
        print("=== END test_IsLongEnoughToBeMessage ===")

    def test_CacheMessage(self):
        print("=== START test_CacheMessage ===")
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
        loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes)
        self.dataHandler._CacheMessage(loraMsg)
        msgAndMetaData = self.dataHandler.ReceivedPunchMessageDict[loraMsg.GetControlNumber()]
        self.assertEqual(loraMsg, msgAndMetaData.GetLoraRadioMessageRS())
        self.assertIsNotNone(self.dataHandler.LastPunchMessageTime)
        self.assertEqual(self.dataHandler.LastPunchMessage,loraMsg)
        print("=== END test_CacheMessage ===")

    def test_Case1_FindPunchErasuresDoubleMessage(self):
        print("=== START test_FindPunchErasuresDoubleMessage ===")
        correctMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(
            TestLoraRadioDataHandler.Case1_PunchDoubleMsg_Previous_WithRS)
        loraPunchMsg1, loraPunchMsg2 = self.dataHandler._GetPunchTupleFromPunchDouble(correctMsg)
        # Cache individual messages but remove the whole double message from data received
        self.dataHandler._CacheMessage(loraPunchMsg1)
        self.dataHandler._CacheMessage(loraPunchMsg2)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(
            TestLoraRadioDataHandler.Case1_PunchDoubleMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindPunchDoubleErasures(corruptedLoraMsg)
        print("test_Case1_FindPunchErasuresDoubleMessage: " + str(erasures))
        corruptPositions = [0,  1,  2,  3, 5, 6, 7, 8, 11, 12, 17, 18, 19, 20]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case1_FindPunchErasuresMessage(self):
        print("=== START test_Case1_FindPunchErasuresMessage ===")
        prevMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            TestLoraRadioDataHandler.Case1_PunchMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(prevMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            TestLoraRadioDataHandler.Case1_PunchMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsg)
        print("test_Case1_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [0, 1, 2, 3, 4, 8, 9, 10, 11, 12, 13]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_FindPunchErasures(self):
        print("=== START test_FindPunchErasures ===")
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
        loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes)
        self.dataHandler._CacheMessage(loraMsg)

        # controlnumber bit 8
        corruptedMessageCNBit8 = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageCNBit8[6] = 0x40
        corruptedLoraMsgCNBit8 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(corruptedMessageCNBit8 + rsCodes)
        erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgCNBit8)
        self.assertEqual(erasures, [6], "controlnumber bit 8 erasure not correct")

        # ack requested
        corruptedMessageAckReq = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageAckReq[0] = corruptedMessageAckReq[0] & 0x7F
        corruptedLoraMsgAckReq = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(corruptedMessageAckReq + rsCodes)
        erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgAckReq)
        self.assertEqual(erasures, [0], "ackreq erasure not correct")

        # TH changed to more than 5 minutes more
        corruptedMessageTH = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageTH[7] = corruptedMessageTH[7] | 0x04
        corruptedLoraMsgTH = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            corruptedMessageTH + rsCodes)
        erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgTH)
        self.assertEqual(erasures, [7], "TH erasure not correct")

        # TH changed to higher than possible
        corruptedMessageTH2 = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageTH2[7] = 0xA9
        corruptedLoraMsgTH2 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            corruptedMessageTH2 + rsCodes)
        erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgTH2)
        self.assertEqual(erasures, [7], "TH erasure not correct")

        # TH changed to more than 5 minutes more and the combination TH TL too high
        corruptedMessageTL = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageTL[7] = 0xA8
        corruptedMessageTL[8] = 0xC1
        corruptedLoraMsgTL = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            corruptedMessageTL + rsCodes)
        erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgTL)
        self.assertEqual(erasures, [7], "TH, TL erasure not correct")

        # TL changed to higher than possible (TH already highest)
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

        # Control number changed
        self.dataHandler._CacheMessage(loraMsg)
        corruptedMessageCN0 = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageCN0[1] = 0x20
        corruptedLoraMsgCN0 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            corruptedMessageCN0 + rsCodes)
        erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgCN0)
        self.assertEqual(erasures, [1], "CN0 erasure not correct")
        print("=== END test_FindPunchErasures ===")

    def test_CheckAndRemoveLoraModuleRXError(self):
        print("=== START test_CheckAndRemoveLoraModuleRXError ===")
        rxerrorMessage = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        rxerrorMessage = "rx error\r\n".encode('latin-1') + rxerrorMessage
        for i in range(0, len(rxerrorMessage)):
            self.dataHandler.AddData(rxerrorMessage[i:i+1])
        self.assertFalse(self.dataHandler.RxError)
        self.assertEqual(rxerrorMessage, self.dataHandler.DataReceived)
        self.dataHandler._CheckAndRemoveLoraModuleRXError()
        self.assertTrue(self.dataHandler.RxError)
        self.assertEqual(TestLoraRadioDataHandler.PunchMsg_Correct_1, self.dataHandler.DataReceived)
        print("=== END test_CheckAndRemoveLoraModuleRXError ===")

    def test_GetMessageTypeByLength(self):
        print("=== START test_GetMessageTypeByLength ===")
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
        for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i+1])
        #print(rsCodes)
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i+1])
        msgType = self.dataHandler._GetMessageTypeByLength()
        self.assertEqual(msgType, 0x03, "Didn't get the expected message type")
        print("=== END test_GetMessageTypeByLength ===")

    def test_GetLikelyMessageTypes(self):
        print("=== START test_GetLikelyMessageTypes ===")
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
        loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
            TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes)
        self.dataHandler._CacheMessage(loraMsg)

        # controlnumber bit 8
        messageArr = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        for i in range(0, len(messageArr)):
            self.dataHandler.AddData(messageArr[i:i+1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i+1])
        messageTypes = self.dataHandler._GetLikelyMessageTypes()
        self.assertEqual(messageTypes, [0x03], "Didn't get the expected message type short punch")

        self.dataHandler.DataReceived = bytearray()
        print("=== END test_GetLikelyMessageTypes ===")

    def test_GetPunchMessage(self):
        print("=== START test_GetPunchMessage ===")
        #messageTypeToTry, erasures = None):
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
        for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])

        # wrong message type
        punchMsg = self.dataHandler._GetAckMessage(0)
        self.assertIsNone(punchMsg)
        # right message type
        punchMsg = self.dataHandler._GetPunchMessage(0)
        self.assertIsNotNone(punchMsg)
        # returned message so buffer should be empty
        punchMsg = self.dataHandler._GetPunchMessage(0)
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

        punchMsg = self.dataHandler._GetPunchMessage()
        self.assertIsNotNone(punchMsg)
        punchMsg = self.dataHandler._GetPunchMessage()
        self.assertIsNotNone(punchMsg)
        punchMsg = self.dataHandler._GetPunchMessage()
        self.assertIsNone(punchMsg)
        print("=== END test_GetPunchMessage ===")

    def test_GetPunchDoubleMessage(self):
        print("=== START test_GetPunchDoubleMessage ===")
        # messageTypeToTry, erasures = None):
        rsCodes = RSCoderLora.encodeLong(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)
        for i in range(0, len(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])

        print("added no of bytes: " + str(len(self.dataHandler.DataReceived)))

        # wrong message type
        punchMsg = self.dataHandler._GetPunchMessage()
        self.assertIsNone(punchMsg)
        # right message type
        punchDoubleMsg = self.dataHandler._GetPunchDoubleMessage()
        self.assertIsNotNone(punchDoubleMsg)
        # returned message so buffer should be empty
        punchDoubleMsg = self.dataHandler._GetPunchDoubleMessage()
        self.assertIsNone(punchDoubleMsg)
        self.assertEqual(len(self.dataHandler.DataReceived), 0)

        # Add two messages at once before trying to fetch the messages
        for i in range(0, len(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])
        for i in range(0, len(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])

        punchDoubleMsg = self.dataHandler._GetPunchDoubleMessage()
        self.assertIsNotNone(punchDoubleMsg)
        punchDoubleMsg = self.dataHandler._GetPunchDoubleMessage()
        self.assertIsNotNone(punchDoubleMsg)
        punchDoubleMsg = self.dataHandler._GetPunchDoubleMessage()
        self.assertIsNone(punchDoubleMsg)
        print("=== END test_GetPunchDoubleMessage ===")

    def test_GetMessage_PunchMessage(self):
        print("=== START test_GetMessage_PunchMessage ===")
        # messageTypeToTry, erasures = None):
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
        for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])

        msg = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg, "expected to receive the message back")
        self.assertEqual(TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes, msg.GetByteArray(), "Didn't receive the same bytes back")


        for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Corrupted_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Corrupted_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])
        #print("before")
        msg2 = self.dataHandler.GetMessage()
        #print("after")
        self.assertIsNone(msg2, "Received a message but it shouldn't be decodable")

        # correct one byte, then it should be decodable
        self.dataHandler.DataReceived[4] = 0x00
        print("the correct: " + str(TestLoraRadioDataHandler.PunchMsg_Correct_1) + " len: " + str(len(TestLoraRadioDataHandler.PunchMsg_Correct_1)))
        print("the corrupted: " + str(self.dataHandler.DataReceived) + " len: " + str(len(self.dataHandler.DataReceived)))
        msg3 = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg3, "Didn't receive a message, it should be decodable")
        print("=== END test_GetMessage_PunchMessage ===")

    def test_GetMessage_PunchMessage_WithPrefixGarbage(self):
        print("=== START test_GetMessage_PunchMessage_WithPrefixGarbage ===")
        self.dataHandler.AddData(bytearray([0,0]))
        msg = self.dataHandler.GetMessage()

        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
        for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])

        msg = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg, "expected to receive the message back")
        self.assertEqual(TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes, msg.GetByteArray(),
                         "Didn't receive the same bytes back")
        self.assertEqual(len(self.dataHandler.DataReceived), 0,
                         "DataReceived not empty")
        for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Corrupted_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Corrupted_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])
        # print("before")
        msg2 = self.dataHandler.GetMessage()
        # print("after")
        self.assertIsNone(msg2, "Received a message but it shouldn't be decodable")

        # correct one byte, then it should be decodable
        self.dataHandler.DataReceived[4] = 0x00
        print("the correct: " + str(TestLoraRadioDataHandler.PunchMsg_Correct_1) + " len: " + str(
            len(TestLoraRadioDataHandler.PunchMsg_Correct_1)))
        print("the corrupted: " + str(self.dataHandler.DataReceived) + " len: " + str(
            len(self.dataHandler.DataReceived)))
        msg3 = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg3, "Didn't receive a message, it should be decodable")
        print("=== END test_GetMessage_PunchMessage_WithPrefixGarbage ===")

    def test_GetMessage_PunchDoubleMessage(self):
        # messageTypeToTry, erasures = None):
        print("=== START test_GetMessage_PunchDoubleMessage ===")
        rsCodes = RSCoderLora.encodeLong(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)
        for i in range(0, len(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])

        msg = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg, "Expected to receive the message back")
        self.assertEqual(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1 + rsCodes, msg.GetByteArray(), "Didn't receive the same bytes back")

        for i in range(0, len(TestLoraRadioDataHandler.PunchDoubleMsg_Corrupted_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchDoubleMsg_Corrupted_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])
        msg2 = self.dataHandler.GetMessage()
        self.assertIsNone(msg2, "Didn't expec to get a message back, shouldn't be decodable")

        # correct one byte, then it should be decodable
        for i in range(0, len(TestLoraRadioDataHandler.PunchDoubleMsg_Corrupted_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchDoubleMsg_Corrupted_1[i:i + 1])
        for i in range(0, len(rsCodes)):
            self.dataHandler.AddData(rsCodes[i:i + 1])
        self.dataHandler.DataReceived[3] = 0x00
        print("the correct: " + str(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1) + " len: " + str(len(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)))
        print("the corrupted: " + str(self.dataHandler.DataReceived) + " len: " + str(len(self.dataHandler.DataReceived)))
        msg3 = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg3, "Didn't receive a message, it should be decodable")
        print("=== END test_GetMessage_PunchDoubleMessage ===")
        #self.assertEqual(TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes, msg2.GetByteArray(), "Didn't receive a corrected message")

    def test_GetMessage_Status(self):

        # messageTypeToTry, erasures = None):
        print("=== START test_GetMessage_Status ===")
        for i in range(0, len(TestLoraRadioDataHandler.StatusMsg_Correct_WithRS)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.StatusMsg_Correct_WithRS[i:i + 1])

        msg = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg, "Expected to receive the message back")
        self.assertEqual(TestLoraRadioDataHandler.StatusMsg_Correct_WithRS, msg.GetByteArray(),
                         "Didn't receive the same bytes back")
        self.assertEqual(msg.GetMessageCategory(), "DATA")
        self.assertTrue(isinstance(msg, LoraRadioMessageRS))
        print("=== END test_GetMessage_Status ===")
        # self.assertEqual(TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes, msg2.GetByteArray(), "Didn't receive a corrected message")

#rint(loraPunchMsg1.GetByteArray())