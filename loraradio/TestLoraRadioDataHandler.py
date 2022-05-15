__author__ = 'henla464'

from multiprocessing import Pool, Queue, Process, current_process
import queue
import hashlib
import logging
import time
import unittest
import reedsolo

from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS, LoraRadioMessagePunchDoubleReDCoSRS
from loraradio.RSCoderLora import RSCoderLora

# Run with python3 -m unittest loraradio/TestLoraRadioDataHandler.py
from utils.utils import Utils


class TestLoraRadioDataHandler(unittest.TestCase):
                                        # stx         31                            37800=>10:30
    PunchMsg_Correct_1 =   bytearray(bytes([0x83, 0x1F, 0x00, 0x00, 0x00, 0xFF, 0x00, 0X93, 0xA8, 0x00]))
    PunchMsg_Corrupted_1 = bytearray(bytes([0x84, 0x10, 0x00, 0x00, 0x01, 0xFF, 0x01, 0X93, 0xA8, 0x00]))
    PunchDoubleMsg_Correct_1 = bytearray(bytes([0x86, 0xff, 0x00, 0x00, 0x63, 0x67, 0x00, 0x03, 0x86, 0x12, 0xff, 0x00, 0x00, 0x63, 0x67, 0x00, 0x0c, 0x9d, 0x6e]))
    PunchDoubleMsg_Corrupted_1 = bytearray(bytes([0x86, 0xff, 0x01, 0x01, 0x63, 0x67, 0x01, 0x03, 0x86, 0x12, 0xff, 0x01, 0x01, 0x63, 0x67, 0x01, 0x0c, 0x9d, 0x6e]))

    PunchReDCoSMsg_Correct_1_WithoutRS_CS = bytearray(bytes([0x83, 0x1F, 0x00, 0x00, 0x00, 0xFF, 0x00, 0X93, 0xA8]))
    PunchReDCoSMsg_Correct_2_WithoutRS_CS = bytearray(bytes([0x83, 0x1E, 0x01, 0x00, 0x00, 0xFF, 0x01, 0X93, 0xB8]))
    PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS = bytearray(bytes([0x88, 0xff, 0x00, 0x00, 0x63, 0x67, 0x00, 0x03, 0x86, 0xff, 0x00, 0x00, 0x63, 0x67, 0x00, 0x03, 0x9d]))
    PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS = bytearray(bytes([0x88, 0xfe, 0x00, 0x00, 0x63, 0x67, 0x00, 0x03, 0x86, 0xff, 0x0f, 0x00, 0x63, 0x67, 0x00, 0x03, 0x9d]))


# ---
    Case1_PunchDoubleMsg_Previous_WithRS = bytearray(bytes([0x86, 0xe7, 0x00, 0x0f, 0x42, 0x3f, 0x40, 0x8f, 0xe1, 0x9a, 0xe7, 0x00, 0x0f, 0x42, 0x3f, 0x40, 0x8f, 0xe2, 0x1b, 0x32, 0xaa, 0x8b, 0x50, 0x3e, 0xaa, 0x4a, 0x99]))
    Case1_PunchDoubleMsg_Corrupted_WithRS = bytearray(bytes([0x06, 0x6f, 0x08, 0x07, 0x42, 0x95, 0x6a, 0x8d, 0xa2, 0x9b, 0xe7, 0x44, 0x0b, 0x42, 0x3f, 0x40, 0x8f, 0xf2, 0x1c, 0x4a, 0xf8, 0xa9, 0x52, 0x81, 0xf1, 0xd8, 0xe0]))
    # The correct message for the PunchDoubleMsg_Corrupted_2_WithRS is: 06 6f 08 07 42 95 6a 8d a2 9b e7 44 0b 42 3f 40 8f f2 1c 4a f8 a9 52 81 f1 d8 e0  (so wrong in positions: 0  1  2  3, 5, 6, 7, 8, 11, 12, 17, 18, 19, 20)
    # ---

    # ---
    Case2_PunchDoubleMsg_Previous_WithRS = bytearray(bytes([0x86, 0x10, 0x00, 0x6a, 0xe3, 0xfc, 0x0c, 0xa2, 0xba, 0xa6, 0x10, 0x00, 0x15, 0x66, 0x05, 0x0c, 0xa2, 0xbf, 0x1d, 0xef, 0x54, 0xd8, 0x10, 0x82, 0xe3, 0x3f, 0x16]))
    Case2_PunchDoubleMsg_Correct_WithRS = bytearray(bytes([0x86, 0x10, 0x00, 0x73, 0xfb, 0x1e, 0x0c, 0xa2, 0xca, 0x6d, 0x10, 0x00, 0x11, 0x1a, 0xf0, 0x0c, 0xa2, 0xd3, 0x66, 0xa6, 0x77, 0x5c, 0xa7, 0xc9, 0xa1, 0xad, 0x16]))
    Case2_PunchDoubleMsg_Corrupted_WithRS = bytearray(bytes([0x86, 0xd8, 0x08, 0x3f, 0xfb, 0x1e, 0x1d, 0xa3, 0xdb, 0x7c, 0x10, 0x00, 0x11, 0x1a, 0xf0, 0x0c, 0xa2, 0xd3, 0x66, 0xa6, 0x77, 0x5c, 0xa7, 0x39, 0x33, 0x49, 0x37]))
    # ---

    # ---
    Case3_PunchDoubleMsg_Previous_WithRS = bytearray(bytes([0x86, 0x10, 0x00, 0x97, 0xae, 0x8a, 0x0c, 0xa8, 0x5a, 0xdc, 0x10, 0x00, 0x1d, 0xfa, 0xb5, 0x0c, 0xa8, 0x5e, 0xd0, 0x5b, 0x73, 0x05, 0x67, 0xea, 0x3a, 0xb4, 0x41]))
    Case3_PunchDoubleMsg_Correct_WithRS = bytearray(bytes([0x86, 0x10, 0x00, 0x04, 0xca, 0x8e, 0x0d, 0x02, 0xe5, 0xe0, 0x10, 0x00, 0x10, 0xc9, 0x4a, 0x0d, 0x02, 0xe7, 0x1a, 0xb2, 0xd0, 0x90, 0xdb, 0xb1, 0x73, 0xb7, 0xf1]))
    Case3_PunchDoubleMsg_Corrupted_WithRS = bytearray(bytes([0x86, 0x10, 0x00, 0x04, 0xca, 0x8e, 0x0d, 0x02, 0xe5, 0xe0, 0x50, 0x44, 0x50, 0xc9, 0x4e, 0x0d, 0x02, 0xe7, 0x1a, 0xb2, 0xd0, 0x90, 0xdb, 0xb1, 0x73, 0xb7, 0xf1]))
    # ---

    # ---
    Case4_PunchDoubleMsg_Previous_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x1c, 0x3e, 0x21, 0x0d, 0x05, 0xbe, 0xcd, 0x7f, 0xd8, 0x15, 0x59]))
    Case4_PunchDoubleMsg_Correct_WithRS = bytearray(bytes([0x86, 0x10, 0x00, 0x1c, 0x3e, 0x21, 0x0d, 0x05, 0xbe, 0xcd, 0x10, 0x00, 0x0f, 0x1a, 0xca, 0x0d, 0x05, 0xc3, 0x23, 0xb3, 0xf4, 0xd5, 0x99, 0xa5, 0x3b, 0x39, 0x65]))
    Case4_PunchDoubleMsg_Corrupted_WithRS = bytearray(bytes([0x86, 0x10, 0x00, 0x1c, 0x3e, 0x21, 0x0d, 0x05, 0xbe, 0xcd, 0x10, 0x00, 0x0f, 0x1a, 0xca, 0x0d, 0x05, 0xc3, 0x23, 0xb3, 0xf4, 0xd5, 0x99, 0xf5, 0xee, 0xa1, 0x76]))
    # ---

    # ---
    Case5_PunchDoubleMsg_Previous_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x1b, 0xe7, 0xdc, 0x0d, 0x06, 0x1d, 0xb4, 0x44, 0x8a, 0x31, 0xee]))
    Case5_PunchDoubleMsg_Correct_WithRS = bytearray(bytes([0x86, 0x10, 0x00, 0x0e, 0x75, 0x77, 0x0d, 0x06, 0x29, 0x9c, 0x10, 0x00, 0x04, 0xca, 0xda, 0x0d, 0x06, 0x2c, 0xaa, 0x17, 0x68, 0xca, 0x31, 0xd9, 0x34, 0x10, 0xd4]))
    Case5_PunchDoubleMsg_Corrupted_WithRS = bytearray(bytes([0x86, 0x10, 0x00, 0x0e, 0x75, 0x77, 0x0d, 0x06, 0x29, 0x9c, 0x90, 0x80, 0x84, 0x4a, 0xd2, 0x0d, 0x06, 0x2c, 0xaa, 0x17, 0x68, 0xca, 0x31, 0xd9, 0x34, 0x10, 0xd4]))
    # ---

    # ---
    Case6_PunchDoubleMsg_Previous_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x0f, 0xbb, 0x63, 0x0d, 0x0c, 0x67, 0x8c, 0xda, 0xc7, 0x57, 0xe4]))
    Case6_PunchDoubleMsg_Correct_WithRS = bytearray(bytes([0x86, 0x10, 0x00, 0x80, 0x86, 0x9e, 0x0d, 0x0c, 0xc3, 0xe0, 0x10, 0x00, 0x0f, 0xe0, 0xbf, 0x0d, 0x0c, 0xd1, 0xb0, 0x06, 0x00, 0x83, 0x44, 0x62, 0x52, 0x12, 0xef]))
    Case6_PunchDoubleMsg_Corrupted_WithRS = bytearray(bytes([0x86, 0x10, 0x00, 0x80, 0x86, 0x9e, 0x0d, 0x0c, 0xc3, 0xe0, 0x10, 0x00, 0x0f, 0xe0, 0xbf, 0x0d, 0x0c, 0xd1, 0xb0, 0x06, 0xa0, 0x81, 0x64, 0x62, 0x52, 0x12, 0xef]))
    # ---

    # ---
    Case7_PunchDoubleMsg_Previous_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x00, 0x77, 0x0e, 0x0d, 0x0e, 0x30, 0xef, 0xfa, 0xe9, 0x8d, 0xa8]))
    Case7_PunchDoubleMsg_Correct_WithRS = bytearray(bytes([0x86, 0x10, 0x00, 0x00, 0x6c, 0x42, 0x0d, 0x0e, 0xa3, 0xe7, 0x10, 0x00, 0x1f, 0x7d, 0x8d, 0x0d, 0x0e, 0xb1, 0xc8, 0x45, 0x9f, 0x0d, 0xde, 0x99, 0x02, 0x65, 0x8d]))
    Case7_PunchDoubleMsg_Corrupted_WithRS = bytearray(bytes([0x86, 0x01, 0x01, 0x10, 0x7d, 0x43, 0x0d, 0x0e, 0xa3, 0xe7, 0x10, 0x00, 0x1f, 0x7d, 0x8d, 0x0d, 0x0e, 0xb1, 0xc8, 0x45, 0x9f, 0x0d, 0xde, 0x99, 0x02, 0x65, 0x8d]))
    # ---

    # ---
    Case1_PunchMsg_Previous_WithRS = bytearray(bytes([0x83, 0xe7, 0x00, 0x0f, 0x42, 0x3f, 0x40, 0x91, 0x9e, 0x89, 0x75, 0xa9, 0x83, 0x8f]))
    Case1_PunchMsg_Correct_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x1f, 0x15, 0x8e, 0x0c, 0x91, 0xdf, 0x4f, 0x6c, 0x99, 0x0f, 0xe0]))
    Case1_PunchMsg_Corrupted_WithRS = bytearray(bytes([0x93, 0x11, 0x01, 0x1e, 0x14, 0x8e, 0x0c, 0x91, 0x1f, 0x6f, 0xa8, 0x55, 0xad, 0x1d]))
    # -- wrong in positions 0, 1, 2, 3, 4, 8, 9, 10, 11, 12, 13

    # ---
    Case2_PunchMsg_Previous_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x1f, 0x15, 0x8e, 0x0c, 0x9b, 0xe1, 0x58, 0x39, 0x2c, 0xad, 0x81]))
    Case2_PunchMsg_Correct_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x1f, 0x7d, 0x9e, 0x0c, 0x9e, 0xb1, 0x6a, 0x7a, 0xc4, 0xc9, 0x51]))
    Case2_PunchMsg_Corrupted_WithRS = bytearray(bytes([0x83, 0x36, 0x42, 0x1b, 0x37, 0x60, 0xc0, 0x01, 0x85, 0x9d, 0xfa, 0x44, 0xc9, 0x51]))
    # -- wrong in positions 1, 2, 3, 4, 5,6,7, 8, 9, 10, 11

    # ---
    Case3_PunchMsg_Previous_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x04, 0xc8, 0x05, 0x0c, 0xa2, 0x71, 0xe1, 0x1b, 0x67, 0x9e, 0x86]))
    Case3_PunchMsg_Correct_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x6a, 0xe3, 0xfc, 0x0c, 0xa2, 0xba, 0xa6, 0x6a, 0x7e, 0x95, 0xd5]))
    Case3_PunchMsg_Corrupted_WithRS = bytearray(bytes([0x93, 0x00, 0x41, 0x3a, 0xf2, 0xfc, 0x2e, 0x80, 0x8b, 0xb5, 0x6a, 0x7e, 0x95, 0xd5]))
    # -- wrong in positions 1, 2, 3, 4, 6,7, 8, 9

    # ---
    Case4_PunchMsg_Previous_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x1f, 0xb5, 0x6e, 0x0c, 0xa6, 0x65, 0xbf, 0x53, 0x8e, 0x2c, 0xd6]))
    Case4_PunchMsg_Correct_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x00, 0xab, 0x13, 0x0c, 0xa6, 0x80, 0xb9, 0xe9, 0xe7, 0xd5, 0x63]))
    Case4_PunchMsg_Corrupted_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x00, 0xab, 0x13, 0x0c, 0xa6, 0x80, 0xb9, 0x69, 0xef, 0x5d, 0xe3]))
    # -- wrong in positions 10,11,12,13

    # ---
    Case5_PunchMsg_Previous_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x1f, 0x6b, 0xa4, 0x0d, 0x05, 0x6f, 0xf1, 0xc8, 0xcb, 0xcb, 0x1d]))
    Case5_PunchMsg_Correct_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x03, 0xc7, 0x75, 0x0d, 0x05, 0x7c, 0xa1, 0x31, 0x03, 0x16, 0xd3]))
    Case5_PunchMsg_Corrupted_WithRS = bytearray(bytes([0x83, 0x30, 0x22, 0x01, 0xe7, 0x57, 0x07, 0xcf, 0x12, 0x23, 0x21, 0x03, 0x17, 0xc3]))
    Case5_PunchMsg_Corrupted_WithRS2 = bytearray(bytes([0x83, 0x29, 0xe8, 0x7c, 0xa9, 0x71, 0x0d, 0x05, 0x7c, 0xa1, 0x31, 0x03, 0x16, 0xd3]))
    # -- wrong in positions 10,11,12,13

    # ---
    Case6_PunchMsg_Previous_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x20, 0x88, 0x97, 0x0d, 0x05, 0xa4, 0xb8, 0xfd, 0x05, 0xdc, 0x9c]))
    Case6_PunchMsg_Correct_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x1c, 0x3e, 0x21, 0x0d, 0x05, 0xbe, 0xcd, 0x7f, 0xd8, 0x15, 0x59]))
    Case6_PunchMsg_Corrupted_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x1c, 0x3e, 0x31, 0x50, 0xa8, 0x22, 0x56, 0x7f, 0xd8, 0x15, 0x59]))
    # -- wrong in positions 5,6,7,8,9

    # ---
    Case7_PunchMsg_Previous_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x1b, 0xe7, 0xdc, 0x0d, 0x06, 0x1d, 0xb4, 0x44, 0x8a, 0x31, 0xee]))
    Case7_PunchMsg_Correct_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x0e, 0x75, 0x77, 0x0d, 0x06, 0x29, 0x9c, 0x5f, 0x53, 0x13, 0x3e]))
    Case7_PunchMsg_Corrupted_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x0e, 0x75, 0x77, 0x0d, 0x06, 0x29, 0x9c, 0x1f, 0x57, 0x17, 0x7e]))
    # -- wrong in positions 10,11,12,13


    # ---
    Case8_PunchMsg_Previous_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x19, 0xf2, 0xf9, 0x0d, 0x08, 0xba, 0x27, 0x64, 0x40, 0xb2, 0x8f]))
    Case8_PunchMsg_Correct_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x00, 0x3c, 0xe9, 0x0d, 0x08, 0xf4, 0xa6, 0xb5, 0xb0, 0x08, 0x1c]))
    Case8_PunchMsg_Corrupted_WithRS = bytearray(bytes([0x83, 0x10, 0x00, 0x00, 0x3c, 0xe9, 0x0d, 0x08, 0xf4, 0xa6, 0xb5, 0xf4, 0xc4, 0xd0]))
    # -- wrong in positions 11,12,13
    Case8_PunchMsg_Corrupted_WithRS2 = bytearray(bytes([0x83, 0x10, 0x00, 0x00, 0x3c, 0x29, 0x09, 0x08, 0x38, 0xa6, 0xb4, 0xb0, 0x18, 0x1d]))
    Case8_PunchMsg_Corrupted_WithRS_BestCombination = bytearray(bytes([0x83, 0x10, 0x00, 0x00, 0x3c, 0xe9, 0x0d, 0x08, 0xf4, 0xa6, 0xb5, 0xb0, 0xc4, 0xd0]))
    # -- wrong in positions 10,12,13



    PunchMsg_Correct_HighestTHTL = bytearray(bytes([0x83, 0x1F, 0x00, 0x00, 0x00, 0xFF, 0x00, 0XA8, 0xC0, 0x00]))
    StatusMsg_Correct_WithRS = bytearray(bytes([0x04, 0x60, 0x10, 0x00, 0xd4, 0x12, 0x43, 0x24, 0x6a, 0x01, 0x0c, 0x71, 0x01, 0xc2]))

    dataHandler = LoraRadioDataHandler(False)

    def setUp(self):
        LoraRadioDataHandler.WiRocLogger.setLevel(logging.DEBUG)

    def tearDown(self):
        self.dataHandler.ReceivedPunchMessageDict = {}
        self.dataHandler.LastPunchMessageTime = None
        self.dataHandler.LastPunchMessage = None
        self.dataHandler.DataReceived = bytearray()

    # def test_AddData(self):
    #     print("=== START test_AddData ===")
    #     self.dataHandler.AddData(bytearray([0x02]))
    #     self.assertEqual(self.dataHandler.DataReceived, bytearray([0x02]), "Adding data failed 1")
    #
    #     self.dataHandler.AddData(bytearray([0x03, 0x04]))
    #     self.assertEqual(self.dataHandler.DataReceived, bytearray([0x02, 0x03, 0x04]), "Adding data failed 2")
    #     print("=== END test_AddData ===")
    #
    # def test_IsLongEnoughToBeMessage(self):
    #     print("=== START test_IsLongEnoughToBeMessage ===")
    #     self.dataHandler.AddData(bytearray([0x02,0x03,0x4]))
    #     couldBeMsg = self.dataHandler._IsLongEnoughToBeMessage()
    #     self.assertFalse(couldBeMsg, "3 bytes should not be a message")
    #     self.dataHandler.AddData(bytearray([0x02, 0x03, 0x4]))
    #     couldBeMsg = self.dataHandler._IsLongEnoughToBeMessage()
    #     self.assertFalse(couldBeMsg, "6 bytes should not be a message")
    #     self.dataHandler.AddData(bytearray([0x02, 0x03, 0x4]))
    #     couldBeMsg = self.dataHandler._IsLongEnoughToBeMessage()
    #     self.assertTrue(couldBeMsg, "9 bytes should be a message")
    #     print("=== END test_IsLongEnoughToBeMessage ===")
    #
    # def test_CacheMessage(self):
    #     print("=== START test_CacheMessage ===")
    #     rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
    #     loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes)
    #     self.dataHandler._CacheMessage(loraMsg)
    #     msgAndMetaData = self.dataHandler.ReceivedPunchMessageDict[loraMsg.GetControlNumber()]
    #     self.assertEqual(loraMsg, msgAndMetaData.GetLoraRadioMessageRS())
    #     self.assertIsNotNone(self.dataHandler.LastPunchMessageTime)
    #     self.assertEqual(self.dataHandler.LastPunchMessage,loraMsg)
    #     print("=== END test_CacheMessage ===")
    #
    # def test_Case1_FindPunchErasuresDoubleMessage(self):
    #     print("=== START test_Case1_FindPunchErasuresDoubleMessage ===")
    #     correctMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case1_PunchDoubleMsg_Previous_WithRS)
    #     loraPunchMsg1, loraPunchMsg2 = self.dataHandler._GetPunchTupleFromPunchDouble(correctMsg)
    #     # Cache individual messages but remove the whole double message from data received
    #     self.dataHandler._CacheMessage(loraPunchMsg1)
    #     self.dataHandler._CacheMessage(loraPunchMsg2)
    #
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case1_PunchDoubleMsg_Corrupted_WithRS)
    #     erasures = self.dataHandler._FindPunchDoubleErasures(corruptedLoraMsg)
    #     print("test_Case1_FindPunchErasuresDoubleMessage: " + str(erasures))
    #     corruptPositions = [0,  1,  2,  3, 5, 6, 7, 8, 11, 12, 17, 18, 19, 20]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case2_FindPunchErasuresDoubleMessage(self):
    #     print("=== START test_Case2_FindPunchErasuresDoubleMessage ===")
    #     correctMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case2_PunchDoubleMsg_Previous_WithRS)
    #     loraPunchMsg1, loraPunchMsg2 = self.dataHandler._GetPunchTupleFromPunchDouble(correctMsg)
    #     # Cache individual messages but remove the whole double message from data received
    #     self.dataHandler._CacheMessage(loraPunchMsg1)
    #     self.dataHandler._CacheMessage(loraPunchMsg2)
    #
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case2_PunchDoubleMsg_Corrupted_WithRS)
    #     erasures = self.dataHandler._FindPunchDoubleErasures(corruptedLoraMsg)
    #     print("test_Case2_FindPunchErasuresDoubleMessage: " + str(erasures))
    #     corruptPositions = [1,  2,  3, 6, 7, 8, 9, 23, 24, 25, 26]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case3_FindPunchErasuresDoubleMessage(self):
    #     print("=== START test_Case3_FindPunchErasuresDoubleMessage ===")
    #     correctMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case3_PunchDoubleMsg_Previous_WithRS)
    #     loraPunchMsg1, loraPunchMsg2 = self.dataHandler._GetPunchTupleFromPunchDouble(correctMsg)
    #     # Cache individual messages but remove the whole double message from data received
    #     self.dataHandler._CacheMessage(loraPunchMsg1)
    #     self.dataHandler._CacheMessage(loraPunchMsg2)
    #
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case3_PunchDoubleMsg_Corrupted_WithRS)
    #     erasures = self.dataHandler._FindPunchDoubleErasures(corruptedLoraMsg)
    #     print("test_Case3_FindPunchErasuresDoubleMessage: " + str(erasures))
    #     corruptPositions = [10, 11, 12]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case4_FindPunchErasuresDoubleMessage(self):
    #     print("=== START test_Case4_FindPunchErasuresDoubleMessage ===")
    #     correctMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case4_PunchDoubleMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(correctMsg)
    #
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case4_PunchDoubleMsg_Corrupted_WithRS)
    #     erasures = self.dataHandler._FindPunchDoubleErasures(corruptedLoraMsg)
    #     print("test_Case4_FindPunchErasuresDoubleMessage: " + str(erasures))
    #     corruptPositions = [23, 24, 25, 26]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case5_FindPunchErasuresDoubleMessage(self):
    #     print("=== START test_Case5_FindPunchErasuresDoubleMessage ===")
    #     correctMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case5_PunchDoubleMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(correctMsg)
    #
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case5_PunchDoubleMsg_Corrupted_WithRS)
    #     erasures = self.dataHandler._FindPunchDoubleErasures(corruptedLoraMsg)
    #     print("test_Case5_FindPunchErasuresDoubleMessage: " + str(erasures))
    #     corruptPositions = [10, 11, 12, 13, 14]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case5_GetPunchDoubleMessage(self):
    #     print("=== START test_Case5_GetPunchDoubleMessage ===")
    #     correctMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case5_PunchDoubleMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(correctMsg)
    #
    #     for i in range(0, len(TestLoraRadioDataHandler.Case5_PunchDoubleMsg_Corrupted_WithRS)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.Case5_PunchDoubleMsg_Corrupted_WithRS[i:i + 1])
    #     punchDoubleMsg = self.dataHandler._GetPunchDoubleMessage()
    #     self.assertIsNotNone(punchDoubleMsg)
    #     print("=== END test_Case5_GetPunchDoubleMessage ===")
    #
    # def test_Case6_FindPunchErasuresDoubleMessage(self):
    #     print("=== START test_Case6_FindPunchErasuresDoubleMessage ===")
    #     correctMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case6_PunchDoubleMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(correctMsg)
    #
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case6_PunchDoubleMsg_Corrupted_WithRS)
    #     erasures = self.dataHandler._FindPunchDoubleErasures(corruptedLoraMsg)
    #     print("test_Case6_FindPunchErasuresDoubleMessage: " + str(erasures))
    #     corruptPositions = [20, 21, 22]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case6_GetPunchDoubleMessage(self):
    #     print("=== START test_Case6_GetPunchDoubleMessage ===")
    #     correctMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case6_PunchDoubleMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(correctMsg)
    #
    #     for i in range(0, len(TestLoraRadioDataHandler.Case6_PunchDoubleMsg_Corrupted_WithRS)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.Case6_PunchDoubleMsg_Corrupted_WithRS[i:i + 1])
    #     punchDoubleMsg = self.dataHandler._GetPunchDoubleMessage()
    #     self.assertIsNotNone(punchDoubleMsg)
    #     print("=== END test_Case6_GetPunchDoubleMessage ===")
    #
    # def test_Case7_FindPunchErasuresDoubleMessage(self):
    #     print("=== START test_Case7_FindPunchErasuresDoubleMessage ===")
    #     correctMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case7_PunchDoubleMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(correctMsg)
    #
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case7_PunchDoubleMsg_Corrupted_WithRS)
    #     erasures = self.dataHandler._FindPunchDoubleErasures(corruptedLoraMsg)
    #     print("test_Case7_FindPunchErasuresDoubleMessage: " + str(erasures))
    #     corruptPositions = [1, 2, 3, 4, 5]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case7_GetPunchDoubleMessage(self):
    #     print("=== START test_Case7_GetPunchDoubleMessage ===")
    #     correctMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case7_PunchDoubleMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(correctMsg)
    #
    #     for i in range(0, len(TestLoraRadioDataHandler.Case7_PunchDoubleMsg_Corrupted_WithRS)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.Case7_PunchDoubleMsg_Corrupted_WithRS[i:i + 1])
    #     punchDoubleMsg = self.dataHandler._GetPunchDoubleMessage()
    #     self.assertIsNotNone(punchDoubleMsg)
    #     print("=== END test_Case7_GetPunchDoubleMessage ===")
    #
    # def test_Case1_FindPunchErasuresMessage(self):
    #     print("=== START test_Case1_FindPunchErasuresMessage ===")
    #     prevMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case1_PunchMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(prevMsg)
    #
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case1_PunchMsg_Corrupted_WithRS)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsg)
    #     print("test_Case1_FindPunchErasuresMessage: " + str(erasures))
    #     corruptPositions = [0, 1, 2, 3, 4, 8, 9, 10, 11, 12, 13]
    #     corruptPositions.append(6)  # add 6 since we sent incorrect week information
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case2_FindPunchErasuresMessage(self):
    #     print("=== START test_Case2_FindPunchErasuresMessage ===")
    #     prevMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case2_PunchMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(prevMsg)
    #
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case2_PunchMsg_Corrupted_WithRS)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsg)
    #     print("test_Case2_FindPunchErasuresMessage: " + str(erasures))
    #     corruptPositions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case3_FindPunchErasuresMessage(self):
    #     print("=== START test_Case3_FindPunchErasuresMessage ===")
    #     prevMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case3_PunchMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(prevMsg)
    #
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case3_PunchMsg_Corrupted_WithRS)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsg)
    #     print("test_Case3_FindPunchErasuresMessage: " + str(erasures))
    #     corruptPositions = [1, 2, 3, 4, 6, 7, 8, 9]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case4_FindPunchErasuresMessage(self):
    #     print("=== START test_Case4_FindPunchErasuresMessage ===")
    #     prevMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case4_PunchMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(prevMsg)
    #
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case4_PunchMsg_Corrupted_WithRS)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsg)
    #     print("test_Case4_FindPunchErasuresMessage: " + str(erasures))
    #     corruptPositions = [10,11,12,13]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case5_FindPunchErasuresMessage(self):
    #     print("=== START test_Case5_FindPunchErasuresMessage ===")
    #     prevMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case5_PunchMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(prevMsg)
    #
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case5_PunchMsg_Corrupted_WithRS)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsg)
    #     print("test_Case5_FindPunchErasuresMessage: " + str(erasures))
    #     corruptPositions = [1,2,3,4,5,6,7,8,9,10,12,13]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    #     #self.dataHandler._CacheMessage(prevMsg)
    #
    #     corruptedLoraMsg2 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case5_PunchMsg_Corrupted_WithRS2)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsg2)
    #     print("test_Case5_FindPunchErasuresMessage 2: " + str(erasures))
    #     corruptPositions = [1, 2, 3, 4, 5]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case6_FindPunchErasuresMessage(self):
    #     print("=== START test_Case6_FindPunchErasuresMessage ===")
    #     prevMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case6_PunchMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(prevMsg)
    #     # Adjust the LastPunchMessageTime
    #     seconds = 7
    #     self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case6_PunchMsg_Corrupted_WithRS)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsg)
    #     print("test_Case6_FindPunchErasuresMessage: " + str(erasures))
    #     corruptPositions = [5,6,7,8,9]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case7_FindPunchErasuresMessage(self):
    #     print("=== START test_Case7_FindPunchErasuresMessage ===")
    #     prevMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case7_PunchMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(prevMsg)
    #     # Adjust the LastPunchMessageTime
    #     seconds = 7
    #     self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case7_PunchMsg_Corrupted_WithRS)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsg)
    #     print("test_Case7_FindPunchErasuresMessage: " + str(erasures))
    #     corruptPositions = [10,11,12,13]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case8_FindPunchErasuresMessage(self):
    #     print("=== START test_Case8_FindPunchErasuresMessage ===")
    #     prevMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case8_PunchMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(prevMsg)
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case8_PunchMsg_Corrupted_WithRS)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsg)
    #     print("test_Case8_FindPunchErasuresMessage: " + str(erasures))
    #     corruptPositions = [11,12,13]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case8_FindPunchErasuresMessage2(self):
    #     print("=== START test_Case8_FindPunchErasuresMessage2 ===")
    #     prevMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case8_PunchMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(prevMsg)
    #     corruptedLoraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case8_PunchMsg_Corrupted_WithRS2)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsg)
    #     print("test_Case8_FindPunchErasuresMessage2: " + str(erasures))
    #     corruptPositions = [5, 6, 8, 10, 12, 13]
    #     for pos in erasures:
    #         self.assertIn(pos, corruptPositions)
    #
    # def test_Case8_GetPunchMessage_BestCombination(self):
    #     print("=== START test_Case8_GetPunchMessage_BestCombination ===")
    #     prevMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.Case8_PunchMsg_Previous_WithRS)
    #     self.dataHandler._CacheMessage(prevMsg)
    #
    #     for i in range(0, len(TestLoraRadioDataHandler.Case8_PunchMsg_Corrupted_WithRS_BestCombination)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.Case8_PunchMsg_Corrupted_WithRS_BestCombination[i:i + 1])
    #
    #     loraMsg = self.dataHandler._GetPunchMessage()
    #     self.assertIsNotNone(loraMsg)
    #     print(Utils.GetDataInHex(loraMsg.GetByteArray(), logging.DEBUG))
    #     print("=== END test_Case8_GetPunchMessage_BestCombination ===")
    #
    # def test_FindPunchErasures(self):
    #     print("=== START test_FindPunchErasures ===")
    #     rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
    #     loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes)
    #     self.dataHandler._CacheMessage(loraMsg)
    #
    #     # controlnumber bit 8
    #     corruptedMessageCNBit8 = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
    #     corruptedMessageCNBit8[6] = 0x40
    #     corruptedLoraMsgCNBit8 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(corruptedMessageCNBit8 + rsCodes)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgCNBit8)
    #     self.assertEqual(erasures, [6], "controlnumber bit 8 erasure not correct")
    #
    #     # ack requested
    #     corruptedMessageAckReq = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
    #     corruptedMessageAckReq[0] = corruptedMessageAckReq[0] & 0x7F
    #     corruptedLoraMsgAckReq = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(corruptedMessageAckReq + rsCodes)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgAckReq)
    #     self.assertEqual(erasures, [0], "ackreq erasure not correct")
    #
    #     # TH changed to more than 5 minutes more
    #     corruptedMessageTH = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
    #     corruptedMessageTH[7] = corruptedMessageTH[7] | 0x04
    #     corruptedLoraMsgTH = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         corruptedMessageTH + rsCodes)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgTH)
    #     self.assertEqual(erasures, [7], "TH erasure not correct")
    #
    #     # TH changed to higher than possible
    #     corruptedMessageTH2 = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
    #     corruptedMessageTH2[7] = 0xA9
    #     corruptedLoraMsgTH2 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         corruptedMessageTH2 + rsCodes)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgTH2)
    #     self.assertEqual(erasures, [7], "TH erasure not correct")
    #
    #     # TH changed to more than 5 minutes more and the combination TH TL too high
    #     corruptedMessageTL = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
    #     corruptedMessageTL[7] = 0xA8
    #     corruptedMessageTL[8] = 0xC1
    #     corruptedLoraMsgTL = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         corruptedMessageTL + rsCodes)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgTL)
    #     self.assertEqual(erasures, [7], "TH, TL erasure not correct")
    #
    #     # TL changed to higher than possible (TH already highest)
    #     rsCodes2 = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_HighestTHTL[1:])
    #     loraMsg2 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.PunchMsg_Correct_HighestTHTL + rsCodes2)
    #     self.dataHandler._CacheMessage(loraMsg2)
    #     corruptedMessageTL2 = TestLoraRadioDataHandler.PunchMsg_Correct_HighestTHTL[:]
    #     corruptedMessageTL2[8] = 0xC1
    #     corruptedLoraMsgTL2 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         corruptedMessageTL2 + rsCodes2)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgTL2)
    #     self.assertEqual(erasures, [8], "TL erasure not correct")
    #
    #     # Control number changed
    #     self.dataHandler._CacheMessage(loraMsg)
    #     corruptedMessageCN0 = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
    #     corruptedMessageCN0[1] = 0x20
    #     corruptedLoraMsgCN0 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         corruptedMessageCN0 + rsCodes)
    #     erasures = self.dataHandler._FindPunchErasures(corruptedLoraMsgCN0)
    #     self.assertEqual(erasures, [1], "CN0 erasure not correct")
    #     print("=== END test_FindPunchErasures ===")
    #
    # def test_CheckAndRemoveLoraModuleRXError(self):
    #     print("=== START test_CheckAndRemoveLoraModuleRXError ===")
    #     rxerrorMessage = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
    #     rxerrorMessage = "rx error\r\n".encode('latin-1') + rxerrorMessage
    #     for i in range(0, len(rxerrorMessage)):
    #         self.dataHandler.AddData(rxerrorMessage[i:i+1])
    #     self.assertFalse(self.dataHandler.RxError)
    #     self.assertEqual(rxerrorMessage, self.dataHandler.DataReceived)
    #     self.dataHandler._CheckAndRemoveLoraModuleRXError()
    #     self.assertTrue(self.dataHandler.RxError)
    #     self.assertEqual(TestLoraRadioDataHandler.PunchMsg_Correct_1, self.dataHandler.DataReceived)
    #     print("=== END test_CheckAndRemoveLoraModuleRXError ===")
    #
    # def test_GetMessageTypeByLength(self):
    #     print("=== START test_GetMessageTypeByLength ===")
    #     rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
    #     for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i+1])
    #     #print(rsCodes)
    #     for i in range(0, len(rsCodes)):
    #         self.dataHandler.AddData(rsCodes[i:i+1])
    #     msgTypes = self.dataHandler._GetMessageTypesByLength()
    #     self.assertEqual(msgTypes, [0x03, 0x04], "Didn't get the expected message type")
    #     print("=== END test_GetMessageTypeByLength ===")
    #
    # def test_GetLikelyMessageTypes(self):
    #     print("=== START test_GetLikelyMessageTypes ===")
    #     rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
    #     loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
    #         TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes)
    #     self.dataHandler._CacheMessage(loraMsg)
    #
    #     # controlnumber bit 8
    #     messageArr = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
    #     for i in range(0, len(messageArr)):
    #         self.dataHandler.AddData(messageArr[i:i+1])
    #     for i in range(0, len(rsCodes)):
    #         self.dataHandler.AddData(rsCodes[i:i+1])
    #     messageTypes = self.dataHandler._GetLikelyMessageTypes()
    #     self.assertEqual(messageTypes, [0x03, 0x04], "Didn't get the expected message type short punch")
    #
    #     self.dataHandler.DataReceived = bytearray()
    #     print("=== END test_GetLikelyMessageTypes ===")
    #
    # def test_GetPunchMessage(self):
    #     print("=== START test_GetPunchMessage ===")
    #     rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
    #     for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i + 1])
    #     for i in range(0, len(rsCodes)):
    #         self.dataHandler.AddData(rsCodes[i:i + 1])
    #
    #     # wrong message type
    #     punchMsg = self.dataHandler._GetAckMessage()
    #     self.assertIsNone(punchMsg)
    #     # right message type
    #     punchMsg = self.dataHandler._GetPunchMessage()
    #     self.assertIsNotNone(punchMsg)
    #     # returned message so buffer should be empty
    #     punchMsg = self.dataHandler._GetPunchMessage()
    #     self.assertIsNone(punchMsg)
    #     print("=== END test_GetPunchMessage ===")
    #
    # def test_GetTwoPunchMessages(self):
    #     print("=== START test_GetTwoPunchMessages ===")
    #     # Add two messages at once before trying to fetch the messages
    #     rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
    #     for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i + 1])
    #     for i in range(0, len(rsCodes)):
    #         self.dataHandler.AddData(rsCodes[i:i + 1])
    #     for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i + 1])
    #     for i in range(0, len(rsCodes)):
    #         self.dataHandler.AddData(rsCodes[i:i + 1])
    #
    #     punchMsg = self.dataHandler._GetPunchMessage()
    #     self.assertIsNotNone(punchMsg)
    #     punchMsg = self.dataHandler._GetPunchMessage()
    #     self.assertIsNotNone(punchMsg, "second message not fetched")
    #     punchMsg = self.dataHandler._GetPunchMessage()
    #     self.assertIsNone(punchMsg)
    #     print("=== END test_GetTwoPunchMessages ===")
    #
    # def test_GetPunchDoubleMessage(self):
    #     print("=== START test_GetPunchDoubleMessage ===")
    #     # messageTypeToTry, erasures = None):
    #     rsCodes = RSCoderLora.encodeLong(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)
    #     for i in range(0, len(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1[i:i + 1])
    #     for i in range(0, len(rsCodes)):
    #         self.dataHandler.AddData(rsCodes[i:i + 1])
    #
    #     print("added no of bytes: " + str(len(self.dataHandler.DataReceived)))
    #
    #     # wrong message type
    #     punchMsg = self.dataHandler._GetPunchMessage()
    #     self.assertIsNone(punchMsg)
    #     # right message type
    #     punchDoubleMsg = self.dataHandler._GetPunchDoubleMessage()
    #     self.assertIsNotNone(punchDoubleMsg)
    #     # returned message so buffer should be empty
    #     punchDoubleMsg = self.dataHandler._GetPunchDoubleMessage()
    #     self.assertIsNone(punchDoubleMsg)
    #     self.assertEqual(len(self.dataHandler.DataReceived), 0)
    #
    #     print("=== END test_GetPunchDoubleMessage ===")
    #
    # def test_GetTwoPunchDoubleMessages(self):
    #     print("=== START test_GetTwoPunchDoubleMessages ===")
    #     # Add two messages at once before trying to fetch the messages
    #     rsCodes = RSCoderLora.encodeLong(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)
    #     for i in range(0, len(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1[i:i + 1])
    #     for i in range(0, len(rsCodes)):
    #         self.dataHandler.AddData(rsCodes[i:i + 1])
    #     for i in range(0, len(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1[i:i + 1])
    #     for i in range(0, len(rsCodes)):
    #         self.dataHandler.AddData(rsCodes[i:i + 1])
    #
    #     punchDoubleMsg = self.dataHandler._GetPunchDoubleMessage()
    #     self.assertIsNotNone(punchDoubleMsg)
    #     punchDoubleMsg = self.dataHandler._GetPunchDoubleMessage()
    #     self.assertIsNotNone(punchDoubleMsg, "could not get second message")
    #     punchDoubleMsg = self.dataHandler._GetPunchDoubleMessage()
    #     self.assertIsNone(punchDoubleMsg)
    #     print("=== END test_GetTwoPunchDoubleMessages ===")
    #
    # def test_GetMessage_PunchMessage_Correct(self):
    #     print("=== START test_GetMessage_PunchMessage_Correct ===")
    #     self.dataHandler.AddData(bytearray([0, 0]))
    #     msg = self.dataHandler.GetMessage()
    #
    #     rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
    #     for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i + 1])
    #     for i in range(0, len(rsCodes)):
    #         self.dataHandler.AddData(rsCodes[i:i + 1])
    #
    #     msg = self.dataHandler.GetMessage()
    #     self.assertIsNotNone(msg, "expected to receive the message back")
    #     self.assertEqual(TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes, msg.GetByteArray(),
    #                      "Didn't receive the same bytes back")
    #     self.assertEqual(len(self.dataHandler.DataReceived), 0,
    #                      "DataReceived not empty")
    #     print("=== END test_GetMessage_PunchMessage_Correct ===")
    #
    # def test_GetMessage_PunchMessage_WithPrefixGarbage(self):
    #     print("=== START test_GetMessage_PunchMessage_WithPrefixGarbage ===")
    #     self.dataHandler.AddData(bytearray([0,0]))
    #     msg = self.dataHandler.GetMessage() # will clear datarecieve
    #
    #     rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
    #     for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i + 1])
    #     for i in range(0, len(rsCodes)):
    #         self.dataHandler.AddData(rsCodes[i:i + 1])
    #
    #     msg = self.dataHandler.GetMessage()
    #     self.assertIsNotNone(msg, "expected to receive the message back")
    #     self.assertEqual(TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes, msg.GetByteArray(),
    #                      "Didn't receive the same bytes back")
    #     self.assertEqual(len(self.dataHandler.DataReceived), 0,
    #                      "DataReceived not empty")
    #     print("=== END test_GetMessage_PunchMessage_WithPrefixGarbage ===")
    #
    # def test_GetMessage_CorruptedPunchMessage(self):
    #     print("=== START test_GetMessage_CorruptedPunchMessage ===")
    #     rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
    #     for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Corrupted_1)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Corrupted_1[i:i + 1])
    #     for i in range(0, len(rsCodes)):
    #         self.dataHandler.AddData(rsCodes[i:i + 1])
    #
    #     msg2 = self.dataHandler.GetMessage()
    #     self.assertIsNone(msg2, "Received a message but it shouldn't be decodable")
    #
    #     # correct one byte, then it should be decodable
    #     corrupt = TestLoraRadioDataHandler.PunchMsg_Corrupted_1[:]
    #     corrupt[4] = 0x00
    #     for i in range(0, len(corrupt)):
    #         self.dataHandler.AddData(corrupt[i:i + 1])
    #     for i in range(0, len(rsCodes)):
    #         self.dataHandler.AddData(rsCodes[i:i + 1])
    #
    #     msg3 = self.dataHandler.GetMessage()
    #     self.assertIsNotNone(msg3, "Didn't receive a message, it should be decodable")
    #     print("=== END test_GetMessage_CorruptedPunchMessage ===")
    #
    # def test_GetMessage_PunchDoubleMessage(self):
    #     # messageTypeToTry, erasures = None):
    #     print("=== START test_GetMessage_PunchDoubleMessage ===")
    #     rsCodes = RSCoderLora.encodeLong(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)
    #     for i in range(0, len(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1[i:i + 1])
    #     for i in range(0, len(rsCodes)):
    #         self.dataHandler.AddData(rsCodes[i:i + 1])
    #
    #     msg = self.dataHandler.GetMessage()
    #     self.assertIsNotNone(msg, "Expected to receive the message back")
    #     self.assertEqual(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1 + rsCodes, msg.GetByteArray(), "Didn't receive the same bytes back")
    #
    #     for i in range(0, len(TestLoraRadioDataHandler.PunchDoubleMsg_Corrupted_1)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.PunchDoubleMsg_Corrupted_1[i:i + 1])
    #     for i in range(0, len(rsCodes)):
    #         self.dataHandler.AddData(rsCodes[i:i + 1])
    #     msg2 = self.dataHandler.GetMessage()
    #     self.assertIsNone(msg2, "Didn't expec to get a message back, shouldn't be decodable")
    #
    #     # correct one byte, then it should be decodable
    #     for i in range(0, len(TestLoraRadioDataHandler.PunchDoubleMsg_Corrupted_1)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.PunchDoubleMsg_Corrupted_1[i:i + 1])
    #     for i in range(0, len(rsCodes)):
    #         self.dataHandler.AddData(rsCodes[i:i + 1])
    #     self.dataHandler.DataReceived[3] = 0x00
    #     print("the correct: " + str(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1) + " len: " + str(len(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)))
    #     print("the corrupted: " + str(self.dataHandler.DataReceived) + " len: " + str(len(self.dataHandler.DataReceived)))
    #     msg3 = self.dataHandler.GetMessage()
    #     self.assertIsNotNone(msg3, "Didn't receive a message, it should be decodable")
    #     print("=== END test_GetMessage_PunchDoubleMessage ===")
    #     #self.assertEqual(TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes, msg2.GetByteArray(), "Didn't receive a corrected message")
    #
    # def test_GetMessage_Status(self):
    #     print("=== START test_GetMessage_Status ===")
    #     for i in range(0, len(TestLoraRadioDataHandler.StatusMsg_Correct_WithRS)):
    #         self.dataHandler.AddData(TestLoraRadioDataHandler.StatusMsg_Correct_WithRS[i:i + 1])
    #
    #     msg = self.dataHandler.GetMessage()
    #     self.assertIsNotNone(msg, "Expected to receive the message back")
    #     self.assertEqual(TestLoraRadioDataHandler.StatusMsg_Correct_WithRS, msg.GetByteArray(),
    #                      "Didn't receive the same bytes back")
    #     self.assertEqual(msg.GetMessageCategory(), "DATA")
    #     self.assertTrue(isinstance(msg, LoraRadioMessageRS))
    #     print("=== END test_GetMessage_Status ===")
    #     # self.assertEqual(TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes, msg2.GetByteArray(), "Didn't receive a corrected message")
    #
    # def test_GetAlternatives(self):
    #     print("=== START test_GetAlternatives ===")
    #     msg = LoraRadioMessageCreator.GetPunchReDCoSMessage(
    #         TestLoraRadioDataHandler.PunchReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
    #         TestLoraRadioDataHandler.PunchReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
    #         TestLoraRadioDataHandler.PunchReDCoSMsg_Correct_1_WithoutRS_CS[1:])
    #
    #     self.dataHandler._CacheMessage(msg)
    #
    #     msg2 = LoraRadioMessageCreator.GetPunchReDCoSMessage(
    #         TestLoraRadioDataHandler.PunchReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
    #         TestLoraRadioDataHandler.PunchReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
    #         TestLoraRadioDataHandler.PunchReDCoSMsg_Correct_2_WithoutRS_CS[1:])
    #
    #     alts, fixedValues, fixedErasures = self.dataHandler._GetPunchMessageAlternatives(msg2)
    #
    #     for i in range(len(alts)):
    #         print(alts[i])
    #
    #     self.assertEqual(len(alts), 4)
    #
    # def test_GetAlternativesDouble(self):
    #     print("=== START test_GetAlternativesDouble ===")
    #     msg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
    #         TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
    #         TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
    #         TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[1:])
    #
    #     msg1, msg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(msg)
    #     self.dataHandler._CacheMessage(msg1)
    #     self.dataHandler._CacheMessage(msg2)
    #
    #     msg3 = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
    #         TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
    #         TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
    #         TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[1:])
    #
    #     alts, fixedValues, fixedErasures = self.dataHandler._GetPunchDoubleMessageAlternatives(msg3)
    #
    #     for i in range(len(alts)):
    #         print(alts[i])
    #
    #     self.assertEqual(len(alts), 4)
    #
    # def test_GetReDCoSErasures(self):
    #     print("=== START test_GetReDCoSErasures ===")
    #
    #     msg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
    #         TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
    #         TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
    #         TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[1:])
    #
    #     msg1, msg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(msg)
    #     self.dataHandler._CacheMessage(msg1)
    #     self.dataHandler._CacheMessage(msg2)
    #
    #     msg3 = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
    #         TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
    #         TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
    #         TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[1:])
    #
    #     alts, fixedValues, fixedErasures = self.dataHandler._GetPunchDoubleMessageAlternatives(msg3)
    #     erasuresCombinations = self.dataHandler._GetReDCoSErasures(msg3, fixedValues)
    #
    #     print("alternatives:")
    #     print(alts)
    #     print("fixedValues:")
    #     print(fixedValues)
    #     print("fixedErasures:")
    #     print(fixedErasures)
    #
    #     print("erasure combinations length: " + str(len(list(erasuresCombinations))))
    #     print("erasure combinations: ")
    #     print(erasuresCombinations)

    def test_DecodeReDCos(self):
        print("=== START test_DecodeReDCos ===")

        msg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[1:])

        msg1, msg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(msg)
        print("tw: "+  str(msg2.GetTwelveHourTimer()))
        self.dataHandler._CacheMessage(msg1)
        self.dataHandler._CacheMessage(msg2)

        msg3 = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[1:])

        corruptedMessageData = msg3.GetByteArray()[:]
        print("Correct message  : " + Utils.GetDataInHex(corruptedMessageData, logging.DEBUG))
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.TL] = 0x00
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.TL_2] = 0x00
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.SN0] = 0x01
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.SN1] = 0x01
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.SN2] = 0x01
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.SN0_2] = 0x01
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.SN1_2] = 0x01
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.CRC0] = 0x00
        msg4Corrupted = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(corruptedMessageData)
        print("Corrupted message: " + Utils.GetDataInHex(msg4Corrupted.GetByteArray(), logging.DEBUG))


        #erasures = [(3, 4, 5, 8, 11, 12, 13, 16)]
        #print("innerCorruptedMessageData: " + Utils.GetDataInHex(msg4Corrupted.GetByteArray()[:-2], logging.DEBUG))
        #print("innerErasuresCombination:  " + str(erasures[0]))
        #res = RSCoderLora.decodeLong(msg4Corrupted.GetByteArray()[:-2], erasures[0])
        #print("Dedocoded: " + Utils.GetDataInHex(res, logging.DEBUG))
        # shake = hashlib.shake_128()
        # shake.update(res[1:])
        # theCRCHash = shake.digest(2)
        # print("theCRCHash: " + Utils.GetDataInHex(theCRCHash, logging.DEBUG))
        # shake = hashlib.shake_128()
        # shake.update(res[1:])
        # theCRCHash = shake.digest(2)
        # print("theCRCHash: " + Utils.GetDataInHex(theCRCHash, logging.DEBUG))

        alts, fixedValues, fixedErasures = self.dataHandler._GetPunchDoubleMessageAlternatives(msg4Corrupted)
        lengthOfDataThatRSCalculatedOverWithoutRSCode = len(
            msg4Corrupted.GetPayloadByteArray() + msg4Corrupted.GetHeaderData()) - len(fixedValues) - len(fixedErasures)
        print("length of data..." + str(lengthOfDataThatRSCalculatedOverWithoutRSCode))

        erasuresCombinationIterator = self.dataHandler._GetReDCoSErasureCombinations(msg4Corrupted, fixedValues, fixedErasures)
        erasuresCombinationList = list(erasuresCombinationIterator)
        global createDecode

        def createDecode(innerCorruptedMessageData):
            global decode

            def decode(innerErasuresCombination):
                #print("innerCorruptedMessageData: " + Utils.GetDataInHex(innerCorruptedMessageData, logging.DEBUG))
                #print("innerErasuresCombination:  " + str(innerErasuresCombination))
                res = RSCoderLora.decodeLong(innerCorruptedMessageData, innerErasuresCombination)
                #print("Decoded:  " + Utils.GetDataInHex(res, logging.DEBUG))
                return res

            return decode

        print("length of erasurecombinationlist: " + str(len(erasuresCombinationList)))

        for startMessageDataComboToTry in alts:
            theDecodeFunction = createDecode(startMessageDataComboToTry[0:-2])
            print("The alternative tested:    " + Utils.GetDataInHex(startMessageDataComboToTry[0:-2], logging.DEBUG))
            crcDictionary = {}
            with Pool(5) as p:
                res = p.map(theDecodeFunction, erasuresCombinationList)

                #print("alternatives:")
                #print(alts)
                #print("fixedValues:")
                #print(fixedValues)
                #print("fixedErasures:")
                #print(fixedErasures)
                for decoded in res:
                    if decoded[:-8] == bytearray(bytes([0x88, 0xfe, 0x00, 0x00, 0x63, 0x67, 0x00, 0x03, 0x86, 0xff, 0x0f, 0x00, 0x63, 0x67, 0x00, 0x03, 0x9d])):
                        print("Decoded: " + Utils.GetDataInHex(decoded, loggingLevel=logging.DEBUG))
                    shake = hashlib.shake_128()
                    shake.update(decoded[1:])
                    theCRCHash = shake.digest(2)
                    if theCRCHash in crcDictionary:
                        crcDictionary[theCRCHash] += 1
                    else:
                        crcDictionary[theCRCHash] = 1
                    if theCRCHash == msg4Corrupted.GetByteArray()[-2:]:
                        print("CRC Match")
                        return
                    else:
                        if crcDictionary[theCRCHash] == lengthOfDataThatRSCalculatedOverWithoutRSCode+1:
                            # We found many messages that after decoding has same CRC. If one of the two
                            # CRC bytes matches then we assume we found a correctly decoded message.
                            if theCRCHash[0] == alts[3][LoraRadioMessagePunchDoubleReDCoSRS.CRC0] or \
                                    theCRCHash[1] == alts[3][LoraRadioMessagePunchDoubleReDCoSRS.CRC1]:
                                print("woohoo found a half match to the CRC")
                                return
                print(crcDictionary)


        self.assertTrue(False, msg="No match found!")