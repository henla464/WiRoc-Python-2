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
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS, LoraRadioMessagePunchDoubleReDCoSRS, \
    LoraRadioMessagePunchReDCoSRS
from loraradio.RSCoderLora import RSCoderLora

# Run with python3 -m unittest loraradio/TestLoraRadioDataHandler.py
from settings.settings import SettingsClass
from utils.utils import Utils


class TestLoraRadioDataHandler(unittest.TestCase):

    # Message: 8b97bdf2be0a
                                        # stx         31                            37800=>10:30

    PunchMsg_Correct_1 =                          bytearray(bytes([0x87, 0x1F, 0x00, 0x00, 0x00, 0xFF, 0x00, 0X93, 0xA8, 0x13, 0x95, 0xfe, 0x24, 0xba, 0xb2]))
    PunchMsg_Corrupted_1 =                        bytearray(bytes([0x88, 0x10, 0x00, 0x00, 0x01, 0xFF, 0x01, 0X93, 0xA8, 0x13, 0x95, 0xfe, 0x24, 0xba, 0xb2]))

    PunchDoubleMsg_Correct_1 =                    bytearray(bytes([0x88, 0xff, 0x00, 0x00, 0x63, 0x67, 0x00, 0x03, 0x86, 0xff, 0x00, 0x00, 0x63, 0x67, 0x40, 0x00, 0x0c,   0xa6, 0x3a, 0x82, 0x3d, 0x4e, 0x6f, 0x19, 0x5a, 0xc5, 0x86]))
    PunchDoubleMsg_Corrupted_1 =                  bytearray(bytes([0x88, 0xff, 0x01, 0x01, 0x63, 0x67, 0x01, 0x03, 0x86, 0xff, 0x01, 0x01, 0x63, 0x67, 0x40, 0x01, 0x0c,   0xa6, 0x3a, 0x82, 0x3d, 0x4e, 0x6f, 0x19, 0x5a, 0xc5, 0x86]))
                                                                    #             2    3                  6                      10,   11                     15
    PunchReDCoSMsg_Correct_1_WithoutRS_CS =       bytearray(bytes([0x87, 0x1F, 0x00, 0x00, 0x00, 0xFF, 0x00, 0X93, 0xA8]))
    PunchReDCoSMsg_Correct_2_WithoutRS_CS =       bytearray(bytes([0x87, 0x1E, 0x01, 0x00, 0x00, 0xFF, 0x01, 0X93, 0xB8]))
    PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS = bytearray(bytes([0x88, 0xff, 0x00, 0x00, 0x63, 0x67, 0x00, 0x03, 0x86, 0xff, 0x00, 0x00, 0x63, 0x67, 0x00, 0x03, 0x9d]))
    PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS = bytearray(bytes([0x88, 0xfe, 0x00, 0x00, 0x63, 0x67, 0x00, 0x03, 0x86, 0xff, 0x0f, 0x00, 0x63, 0x67, 0x00, 0x03, 0x9d]))

    # ---
    Case1_PunchDoubleMsg_Previous_WithRS =        bytearray(bytes([0x88, 0xe7, 0x00, 0x0f, 0x42, 0x3f, 0x40, 0x8f, 0xe1, 0xe7, 0x00, 0x0f, 0x42, 0x3f, 0x40, 0x8f, 0xbe,   0x9c, 0xad, 0xe8, 0xdd, 0x4b, 0x8f, 0x17, 0x00, 0xed, 0xf2]))
    Case1_PunchDoubleMsg_Correct_WithRS =         bytearray(bytes([0x88, 0xe7, 0x00, 0x0f, 0x42, 0x3f, 0x40, 0x8f, 0xe2, 0xe7, 0x00, 0x0f, 0x42, 0x3f, 0x40, 0x8f, 0xe3,   0x94, 0x55, 0xbc, 0x52, 0x89, 0xf1, 0x0e, 0xd0, 0x6a, 0xca]))
    Case1_PunchDoubleMsg_Corrupted_WithRS =       bytearray(bytes([0x08, 0x6f, 0x08, 0x07, 0x42, 0x95, 0x6a, 0x8d, 0xa2, 0xe7, 0x00, 0x0b, 0x43, 0x3f, 0x40, 0x8f, 0xe3,   0x4a, 0xf8, 0xa9, 0x53, 0x89, 0xf1, 0x0e, 0xd0, 0x6a, 0xca]))
    # The correct message for the  (so wrong in positions: 0  1  2  3, 5, 6, 7, 8, 11, 12, 17, 18, 19, 20)
    # ---

    # ---
    Case2_PunchDoubleMsg_Previous_WithRS =        bytearray(bytes([0x88, 0x10, 0x00, 0x6a, 0xe3, 0xfc, 0x0c, 0xa2, 0xba, 0x10, 0x00, 0x15, 0x66, 0x05, 0x0c, 0xa2, 0xbf, 0xc9, 0x0e, 0x1c, 0xe6, 0x78, 0x52, 0x5a, 0xc3, 0x60, 0x6b]))
    Case2_PunchDoubleMsg_Correct_WithRS =         bytearray(bytes([0x88, 0x10, 0x00, 0x73, 0xfb, 0x1e, 0x0c, 0xa2, 0xca, 0x10, 0x00, 0x11, 0x1a, 0xf0, 0x0c, 0xa2, 0xd3, 0x0d, 0x50, 0xda, 0xe4, 0xdd, 0x5a, 0x8a, 0x92, 0x17, 0xb2]))
    Case2_PunchDoubleMsg_Corrupted_WithRS =       bytearray(bytes([0x88, 0xd8, 0x08, 0x3f, 0xfb, 0x1e, 0x1d, 0xa3, 0xdb, 0x10, 0x00, 0x11, 0x1a, 0xf0, 0x0c, 0xa2, 0xd3, 0x0d, 0x50, 0xda, 0xe4, 0xde, 0x5b, 0x8b, 0x93, 0x17, 0xb2]))
    # Wrong in positions: [1,  2,  3, 6, 7, 8, 21, 22, 23, 24]
    # ---

    # ---
    Case3_PunchDoubleMsg_Previous_WithRS =        bytearray(bytes([0x88, 0x10, 0x00, 0x97, 0xae, 0x8a, 0x0c, 0x02, 0x5a, 0x10, 0x00, 0x1d, 0xfa, 0xb5, 0x0c, 0x02, 0x5e, 0x60, 0x5d, 0xdd, 0x72, 0xed, 0x1a, 0x94, 0x9c, 0x06, 0x84]))
    Case3_PunchDoubleMsg_Correct_WithRS =         bytearray(bytes([0x88, 0x10, 0x00, 0x04, 0xca, 0x8e, 0x0d, 0x02, 0xe5, 0x10, 0x00, 0x10, 0xc9, 0x4a, 0x0d, 0x02, 0xe7, 0xbe, 0xa2, 0xf0, 0x47, 0x60, 0xfa, 0x6e, 0x06, 0xee, 0x7f]))
    Case3_PunchDoubleMsg_Corrupted_WithRS =       bytearray(bytes([0x88, 0x10, 0x00, 0x04, 0xca, 0x8e, 0x0d, 0x02, 0xe5, 0x50, 0x44, 0x50, 0xc9, 0x4e, 0x0d, 0x02, 0xe7, 0xbe, 0xa2, 0xf0, 0x47, 0x60, 0xfa, 0x6e, 0x06, 0xee, 0x7f]))
    # ---  wrong in positions [9, 8, 10, 11, 16]

    # ---
    Case4_PunchDoubleMsg_Previous_WithRS =        bytearray(bytes([0x87, 0x10, 0x00, 0x1c, 0x3e, 0x21, 0x0d, 0x05, 0xbe, 0xbf, 0x74, 0x29, 0xc0, 0x61, 0x20]))
    Case4_PunchDoubleMsg_Correct_WithRS =         bytearray(bytes([0x88, 0x10, 0x00, 0x1c, 0x3e, 0x21, 0x0d, 0x05, 0xbe, 0x10, 0x00, 0x0f, 0x1a, 0xca, 0x0d, 0x05, 0xc3, 0xdc, 0x06, 0xb0, 0x68, 0x0b, 0x2f, 0x72, 0x7d, 0xdb, 0x5c]))
    Case4_PunchDoubleMsg_Corrupted_WithRS =       bytearray(bytes([0x88, 0x10, 0x00, 0x1c, 0x3e, 0x21, 0x0d, 0x05, 0xbe, 0x10, 0x00, 0x0f, 0x1a, 0xca, 0x0d, 0x05, 0xc3, 0xdc, 0x06, 0xb0, 0x68, 0xf5, 0xee, 0xa1, 0x76, 0xdb, 0x5c]))
    # --- wrong in positions [21, 22, 23, 24]

    # ---
    Case5_PunchDoubleMsg_Previous_WithRS =        bytearray(bytes([0x87, 0x10, 0x00, 0x1b, 0xe7, 0xdc, 0x0d, 0x06, 0x1d, 0x8f, 0xdf, 0xe1, 0x10, 0xb2, 0x20]))
    Case5_PunchDoubleMsg_Correct_WithRS =         bytearray(bytes([0x88, 0x10, 0x00, 0x0e, 0x75, 0x77, 0x0d, 0x06, 0x29, 0x10, 0x00, 0x04, 0xca, 0xda, 0x0d, 0x06, 0x2c, 0x1a, 0xe4, 0x84, 0xc1, 0x9e, 0x5f, 0x13, 0xfc, 0xe5, 0xc1]))
    Case5_PunchDoubleMsg_Corrupted_WithRS =       bytearray(bytes([0x88, 0x10, 0x00, 0x0e, 0x75, 0x77, 0x0d, 0x06, 0x29, 0x90, 0x80, 0x84, 0x4a, 0xd2, 0x0d, 0x06, 0x1a, 0x1a, 0xe4, 0x84, 0xc1, 0x9e, 0x5f, 0x13, 0xfc, 0xe5, 0xc1]))
    # --- wrong in positions [9,10,11,12,13,16]

    # ---
    Case6_PunchDoubleMsg_Previous_WithRS =        bytearray(bytes([0x87, 0x10, 0x00, 0x0f, 0xbb, 0x63, 0x0d, 0x0c, 0x67, 0x76, 0x7a, 0x99, 0xb3, 0xf7, 0xbc]))
    Case6_PunchDoubleMsg_Correct_WithRS =         bytearray(bytes([0x88, 0x10, 0x00, 0x80, 0x86, 0x9e, 0x0d, 0x0c, 0xc3, 0x10, 0x00, 0x0f, 0xe0, 0xbf, 0x0d, 0x0c, 0xb0, 0x01, 0xff, 0xb2, 0x6f, 0x87, 0x81, 0xe3, 0xf5, 0x52, 0x27]))
    Case6_PunchDoubleMsg_Corrupted_WithRS =       bytearray(bytes([0x88, 0x10, 0x00, 0x80, 0x86, 0x9e, 0x0d, 0x0c, 0xc3, 0x10, 0x00, 0x0f, 0xe0, 0xbf, 0x0d, 0x0c, 0xb0, 0x01, 0xfe, 0xb3, 0x6e, 0x87, 0x81, 0xe3, 0xf5, 0x52, 0x27]))
    # ---wrong in positions [18,19,20]

    # ---
    Case7_PunchDoubleMsg_Previous_WithRS =        bytearray(bytes([0x87, 0x10, 0x00, 0x00, 0x77, 0x0e, 0x0d, 0x0e, 0x30, 0x61, 0x8c, 0xa7, 0x97, 0xf6, 0x8c]))
    Case7_PunchDoubleMsg_Correct_WithRS =         bytearray(bytes([0x88, 0x10, 0x00, 0x00, 0x6c, 0x42, 0x0d, 0x0e, 0xa3, 0x10, 0x00, 0x1f, 0x7d, 0x8d, 0x0d, 0x0e, 0xb1, 0xf2, 0xa6, 0xbc, 0xbf, 0x23, 0x79, 0x6f, 0x39, 0x5d, 0xdd]))
    Case7_PunchDoubleMsg_Corrupted_WithRS =       bytearray(bytes([0x88, 0x01, 0x01, 0x10, 0x7d, 0x43, 0x0d, 0x0e, 0xa3, 0x10, 0x00, 0x1f, 0x7d, 0x8d, 0x0d, 0x0e, 0xb1, 0xf2, 0xa6, 0xbc, 0xbf, 0x23, 0x79, 0x6f, 0x39, 0x5d, 0xdd]))
    # ---

    # ---
    Case8_PunchDoubleMsg_Previous_AirOrder_WithRS =        bytearray([0x87, 0xd1, 0x0f, 0x42, 0xff, 0x3f, 0x06, 0xba, 0x00, 0xf3, 0xfb, 0x41, 0xf7, 0x08, 0xe2])
    Case8_PunchDoubleMsg_Correct_AirOrder_WithRS =         bytearray(bytes([0x88, 0xb2, 0x0f, 0x42, 0x3f, 0xff, 0x06, 0xba, 0x0f, 0x42, 0x00, 0x3f, 0x06, 0xbb, 0x41, 0xf9, 0xe0, 0x29, 0xff, 0xf7, 0x6e, 0xe6, 0x00, 0x1c, 0xda, 0x41, 0xed]))
    Case8_PunchDoubleMsg_Corrupted_AirOrder_WithRS =       bytearray(bytes([0x88, 0xb2, 0x0f, 0x42, 0x3f, 0xff, 0x06, 0xba, 0x8f, 0xc2, 0x80, 0xbf, 0x0e, 0xbb, 0x41, 0xf9, 0xe0, 0x29, 0xff, 0xf7, 0x2e, 0x88, 0xcc, 0x30, 0xb8, 0x53, 0xc8]))
    # ---

    # ---
    Case9_PunchDoubleMsg_Previous_AirOrder_WithRS =        bytearray([0x88, 0xf9, 0x0f, 0x42, 0x3f, 0xff, 0x07, 0x01, 0x0f, 0x42, 0x00, 0x3f, 0x07, 0x02, 0x41, 0x9e, 0x6a, 0x77, 0xff, 0x58, 0x70, 0x7d, 0x00, 0x37, 0x6a, 0x41, 0xff])
    Case9_PunchDoubleMsg_Correct_AirOrder_WithRS =         bytearray([0x88, 0x1c, 0x0f, 0x42, 0x3f, 0xff, 0x07, 0x02, 0x0f, 0x42, 0x00, 0x3f, 0x07, 0x03, 0x41, 0x9c, 0xac, 0x48, 0xff, 0xe4, 0x11, 0x86, 0x00, 0x4b, 0xc9, 0x41, 0x56])
    Case9_PunchDoubleMsg_Corrupted_AirOrder_WithRS =       bytearray([0x88, 0x1c, 0x4d, 0x42, 0x39, 0xff, 0x07, 0x02, 0x4f, 0x42, 0x04, 0x3b, 0x03, 0x03, 0x41, 0x9c, 0xac, 0x48, 0xff, 0xe4, 0x11, 0x06, 0x88, 0xc3, 0xc1, 0x41, 0x57])
    # ---

    # ---
    Case10_PunchDoubleMsg_Previous_AirOrder_WithRS =       bytearray([0x87, 0x54, 0x0f, 0x42, 0xff, 0x3f, 0x07, 0x03, 0x00, 0x39, 0xfc, 0x41, 0x04, 0x8e, 0x5b])
    Case10_PunchDoubleMsg_Correct_AirOrder_WithRS =        bytearray([0x88, 0xcc, 0x0f, 0x42, 0x3f, 0xff, 0x07, 0x4d, 0x0f, 0x42, 0x00, 0x3f, 0x07, 0x4d, 0x41, 0x7f, 0xf1, 0x4d, 0xff, 0x84, 0x40, 0x49, 0x00, 0xe3, 0x25, 0x41, 0xfe])
    Case10_PunchDoubleMsg_Corrupted_AirOrder_WithRS =      bytearray([0x98, 0xdd, 0x1e, 0x52, 0x3e, 0xff, 0x07, 0x4d, 0x0f, 0x42, 0x00, 0x3f, 0x07, 0x4d, 0x41, 0x7f, 0xf1, 0x4d, 0xff, 0x84, 0x40, 0x49, 0x10, 0xf3, 0x25, 0x41, 0xfe])
    # --

    # ---
    Case11_PunchDoubleMsg_Previous_AirOrder_WithRS =       bytearray([0x87, 0x5a, 0x0f, 0x42, 0xff, 0x3f, 0x09, 0x0e, 0x00, 0x1a, 0xd2, 0x41, 0x6e, 0xea, 0x19])
    Case11_PunchDoubleMsg_Correct_AirOrder_WithRS =        bytearray([0x88, 0x78, 0x0f, 0x42, 0x3f, 0xff, 0x09, 0x1a, 0x0f, 0x42, 0x00, 0x3f, 0x09, 0x1b, 0x41, 0x0f, 0xfe, 0x1b, 0xff, 0xab, 0x88, 0x99, 0x00, 0xd9, 0x00, 0x41, 0x8e])
    Case11_PunchDoubleMsg_Corrupted_AirOrder_WithRS =      bytearray([0xb8, 0x2d, 0x6b, 0x20, 0x18, 0xdf, 0x1b, 0x2a, 0x0e, 0x42, 0x00, 0x3f, 0x09, 0x1b, 0x41, 0x0f, 0xfe, 0x1b, 0xff, 0xab, 0x88, 0x99, 0x00, 0xd9, 0x00, 0x41, 0x8e])
    # --

    # ---
    Case12_PunchDoubleMsg_Previous_AirOrder_WithRS =       bytearray([0x88, 0xc1, 0x0f, 0x42, 0x3f, 0xff, 0x09, 0x42, 0x0f, 0x42, 0x00, 0x3f, 0x09, 0x43, 0x41, 0x0a, 0xd1, 0x00, 0xff, 0x84, 0x5f, 0x04, 0x00, 0x70, 0xfd, 0x41, 0xff])
    Case12_PunchDoubleMsg_Correct_AirOrder_WithRS =        bytearray([0x88, 0x77, 0x0f, 0x42, 0x3f, 0xff, 0x09, 0x43, 0x0f, 0x42, 0x00, 0x3f, 0x09, 0x44, 0x41, 0x6d, 0x50, 0x7b, 0xff, 0x8b, 0x92, 0x52, 0x00, 0x5e, 0xdc, 0x41, 0x89])
    Case12_PunchDoubleMsg_Corrupted_AirOrder_WithRS =      bytearray([0x88, 0x77, 0x0f, 0x42, 0x3f, 0xff, 0x09, 0x43, 0x0f, 0x42, 0x00, 0x3f, 0x09, 0x44, 0x41, 0x6d, 0x50, 0x7b, 0xff, 0x8b, 0x92, 0xd2, 0x88, 0xd6, 0xa4, 0x03, 0xb9])
    # --

    # ---
    Case1_PunchMsg_Previous_WithRS =      bytearray(bytes([0x87, 0xe7, 0x00, 0x0f, 0x42, 0x3f, 0x40, 0x91, 0x9e, 0x0b, 0x47, 0x92, 0x83, 0xc0, 0x4e]))
    Case1_PunchMsg_Correct_WithRS =       bytearray(bytes([0x87, 0x10, 0x00, 0x1f, 0x15, 0x8e, 0x0c, 0x91, 0xdf, 0x6d, 0x70, 0x2e, 0x62, 0xc9, 0x68]))
    Case1_PunchMsg_Corrupted_WithRS =     bytearray(bytes([0x97, 0x11, 0x01, 0x1e, 0x14, 0x8e, 0x0c, 0x91, 0x1f, 0xa8, 0x55, 0xad, 0x1d, 0xc9, 0x68]))
    # -- wrong in positions 0, 1, 2, 3, 4, 8, 9, 10, 11, 12

    # ---
    Case2_PunchMsg_Previous_WithRS =      bytearray(bytes([0x87, 0x10, 0x00, 0x1f, 0x15, 0x8e, 0x0c, 0x9b, 0xe1, 0xc3, 0x8c, 0xcb, 0xe1, 0xa8, 0x4a]))
    Case2_PunchMsg_Correct_WithRS =       bytearray(bytes([0x87, 0x10, 0x00, 0x1f, 0x7d, 0x9e, 0x0c, 0x9e, 0xb1, 0xb5, 0x14, 0xfa, 0x13, 0x5c, 0xe0]))
    Case2_PunchMsg_Corrupted_WithRS =     bytearray(bytes([0x87, 0x36, 0x42, 0x1b, 0x37, 0x60, 0xc0, 0x01, 0x85, 0xfa, 0x44, 0xfa, 0x13, 0x5c, 0xe0]))
    # -- wrong in positions 1, 2, 3, 4, 5,6,7, 8, 9, 10

    # ---
    Case3_PunchMsg_Previous_WithRS =      bytearray(bytes([0x87, 0x10, 0x00, 0x04, 0xc8, 0x05, 0x0c, 0xa2, 0x71, 0xf8, 0x63, 0xee, 0xf4, 0x66, 0xe9]))
    Case3_PunchMsg_Correct_WithRS =       bytearray(bytes([0x87, 0x10, 0x00, 0x6a, 0xe3, 0xfc, 0x0c, 0xa2, 0xba, 0xa3, 0xa6, 0xc5, 0x36, 0xa0, 0x4e]))
    Case3_PunchMsg_Corrupted_WithRS =     bytearray(bytes([0x97, 0x00, 0x41, 0x3a, 0xf2, 0xfc, 0x2e, 0x80, 0x8b, 0xa3, 0xa6, 0xc5, 0x36, 0xa0, 0x4e]))
    # -- wrong in positions 1, 2, 3, 4, 6,7, 8

    # ---
    Case4_PunchMsg_Previous_WithRS =      bytearray(bytes([0x87, 0x10, 0x00, 0x1f, 0xb5, 0x6e, 0x0c, 0xa6, 0x65, 0xe0, 0xee, 0xb2, 0x20, 0x5d, 0xa4]))
    Case4_PunchMsg_Correct_WithRS =       bytearray(bytes([0x87, 0x10, 0x00, 0x00, 0xab, 0x13, 0x0c, 0xa6, 0x80, 0xc3, 0x9a, 0xbb, 0xe7, 0xe4, 0x20]))
    Case4_PunchMsg_Corrupted_WithRS =     bytearray(bytes([0x87, 0x10, 0x00, 0x00, 0xab, 0x13, 0x0c, 0xa6, 0x80, 0x69, 0xef, 0x5d, 0xe3, 0x00, 0x00]))
    # -- wrong in positions 9,10,11,12

    # ---
    Case5_PunchMsg_Previous_WithRS =      bytearray(bytes([0x87, 0x10, 0x00, 0x1f, 0x6b, 0xa4, 0x0d, 0x05, 0x6f, 0x5a, 0x70, 0xe5, 0xef, 0xb3, 0x14]))
    Case5_PunchMsg_Correct_WithRS =       bytearray(bytes([0x87, 0x10, 0x00, 0x03, 0xc7, 0x75, 0x0d, 0x05, 0x7c, 0x10, 0x1f, 0xab, 0xf6, 0xe7, 0xe3]))
    Case5_PunchMsg_Corrupted_WithRS =     bytearray(bytes([0x87, 0x30, 0x22, 0x01, 0xe7, 0x57, 0x07, 0xcf, 0x12, 0x21, 0x1f, 0x17, 0xc3, 0xe7, 0xe3]))
    Case5_PunchMsg_Corrupted_WithRS2 =    bytearray(bytes([0x87, 0x29, 0xe8, 0x7c, 0xa9, 0x71, 0x0d, 0x05, 0x7c, 0x10, 0x1f, 0xab, 0xf6, 0xe7, 0xe3]))
    # --

    # ---
    Case6_PunchMsg_Previous_WithRS =      bytearray(bytes([0x87, 0x10, 0x00, 0x20, 0x88, 0x97, 0x0d, 0x05, 0xa4, 0x27, 0x74, 0x3a, 0x6d, 0x8b, 0xf5]))
    Case6_PunchMsg_Correct_WithRS =       bytearray(bytes([0x87, 0x10, 0x00, 0x1c, 0x3e, 0x21, 0x0d, 0x05, 0xbe, 0xbf, 0x74, 0x29, 0xc0, 0x61, 0x20]))
    Case6_PunchMsg_Corrupted_WithRS =     bytearray(bytes([0x87, 0x10, 0x00, 0x1c, 0x3e, 0x31, 0x50, 0xa8, 0x22, 0xbf, 0x74, 0x29, 0xc0, 0x61, 0x20]))
    # -- wrong in positions 5,6,7,8

    # ---
    Case7_PunchMsg_Previous_WithRS =      bytearray(bytes([0x87, 0x10, 0x00, 0x1b, 0xe7, 0xdc, 0x0d, 0x06, 0x1d, 0x8f, 0xdf, 0xe1, 0x10, 0xb2, 0x20]))
    Case7_PunchMsg_Correct_WithRS =       bytearray(bytes([0x87, 0x10, 0x00, 0x0e, 0x75, 0x77, 0x0d, 0x06, 0x29, 0xe3, 0x1f, 0xe1, 0xa4, 0xa2, 0x4c]))
    Case7_PunchMsg_Corrupted_WithRS =     bytearray(bytes([0x87, 0x10, 0x00, 0x0e, 0x75, 0x77, 0x0d, 0x06, 0x29, 0x1f, 0x57, 0x17, 0x7e, 0xa2, 0x4c]))
    # -- wrong in positions 9, 10,11,12

    # ---
    Case8_PunchMsg_Previous_WithRS =                  bytearray(bytes([0x87, 0x10, 0x00, 0x19, 0xf2, 0xf9, 0x0d, 0x08, 0xba, 0xa5, 0x56, 0x7b, 0xb2, 0x5a, 0xc8]))
    Case8_PunchMsg_Correct_WithRS =                   bytearray(bytes([0x87, 0x10, 0x00, 0x00, 0x3c, 0xe9, 0x0d, 0x08, 0xf4, 0x3b, 0x22, 0xe3, 0x49, 0x9e, 0xfb]))
    Case8_PunchMsg_Corrupted_WithRS =                 bytearray(bytes([0x87, 0x10, 0x00, 0x00, 0x3c, 0xe9, 0x0d, 0x08, 0xf4, 0x3b, 0xf4, 0xc4, 0xd0, 0x9e, 0xfb]))
    # --

    # -- wrong in positions 10,11,12
    Case8_PunchMsg_Corrupted_WithRS2 =                bytearray(bytes([0x87, 0x10, 0x00, 0x00, 0x3c, 0x29, 0x09, 0x08, 0x38, 0xb4, 0x22, 0x18, 0x1d, 0x9e, 0xfb]))
    Case8_PunchMsg_Corrupted_WithRS_BestCombination = bytearray(bytes([0x87, 0x10, 0x00, 0x00, 0x3c, 0xe9, 0x0d, 0x08, 0xf4, 0x3b, 0x22, 0xc4, 0xd0, 0x9e, 0xfb]))
    # -- wrong in positions 9,11,12

    # ---
    Case9_PunchMsg_Previous_AirOrder_WithRS =               bytearray([0x88, 0xf9, 0x0f, 0x42, 0x3f, 0xff, 0x07, 0x01, 0x0f, 0x42, 0x00, 0x3f, 0x07, 0x02, 0x41, 0x9e, 0x6a, 0x77, 0xff, 0x58, 0x70, 0x7d, 0x00, 0x37, 0x6a, 0x41, 0xff])
    Case9_PunchMsg_Correct_AirOrder_WithRS =                bytearray([0x87, 0xc3, 0x0f, 0x42, 0xff, 0x3f, 0x07, 0x02, 0x00, 0x36, 0xca, 0x41, 0x7c, 0xce, 0x4e])
    Case9_PunchMsg_Corrupted_AirOrder_WithRS =              bytearray([0xc7, 0xc7, 0x0b, 0x02, 0xfb, 0x3f, 0x07, 0x02, 0x00, 0x36, 0xca, 0x41, 0x7c, 0xce, 0x4e])
    # --

    # ---
    Case10_PunchMsg_Previous_AirOrder_WithRS =               bytearray([0x87, 0x54, 0x0f, 0x42, 0xff, 0x3f, 0x07, 0x03, 0x00, 0x39, 0xfc, 0x41, 0x04, 0x8e, 0x5b])
    Case10_PunchMsg_Correct_AirOrder_WithRS =                bytearray([0x87, 0x12, 0x0f, 0x42, 0xff, 0x3f, 0x07, 0x4b, 0x00, 0xa6, 0x50, 0x41, 0x88, 0x79, 0x36])
    Case10_PunchMsg_Corrupted_AirOrder_WithRS =              bytearray([0xa7, 0x12, 0x2d, 0x42, 0xfd, 0xb7, 0x07, 0x4b, 0x08, 0xa6, 0x40, 0x40, 0x89, 0x7d, 0x36])
    # --

    # ---
    Case11_PunchMsg_Previous_AirOrder_WithRS =               bytearray([0x87, 0x5a, 0x0f, 0x42, 0xff, 0x3f, 0x09, 0x0e, 0x00, 0x1a, 0xd2, 0x41, 0x6e, 0xea, 0x19])
    Case11_PunchMsg_Correct_AirOrder_WithRS =                bytearray([0x87, 0xbe, 0x0f, 0x42, 0xff, 0x3f, 0x09, 0x1a, 0x00, 0xd6, 0x4d, 0x41, 0x40, 0x83, 0x97])
    Case11_PunchMsg_Corrupted_AirOrder_WithRS =              bytearray([0x87, 0xbf, 0x0f, 0x43, 0xde, 0x3d, 0x29, 0x3a, 0x10, 0xd7, 0x4c, 0x51, 0x40, 0x83, 0x97])
    # --

    # ---
    Case12_PunchMsg_Previous_AirOrder_WithRS =               bytearray([0x87, 0x49, 0x0f, 0x42, 0xff, 0x3f, 0x09, 0x98, 0x00, 0x1b, 0x23, 0x41, 0x66, 0x84, 0xeb])
    Case12_PunchMsg_Correct_AirOrder_WithRS =                bytearray([0x87, 0x39, 0x0f, 0x42, 0xff, 0x3f, 0x09, 0xab, 0x00, 0x07, 0xb0, 0x41, 0x86, 0xd8, 0x1d])
    Case12_PunchMsg_Corrupted_AirOrder_WithRS =              bytearray([0xa7, 0x1b, 0x2f, 0x62, 0xfd, 0x3f, 0x09, 0xab, 0x00, 0x07, 0xb0, 0x41, 0x86, 0xd8, 0x1d])
    # --

    # Prev:    87490f42ff3f0998001b23416684eb
    # Sent:    87390f42ff3f09ab0007b04186d81d
    # Rec:     a71b2f62fd3f09ab0007b04186d81d

    PunchMsg_Correct_HighestTHTL =                    bytearray(bytes([0x87, 0x1F, 0x00, 0x00, 0x00, 0xFF, 0x00, 0XA8, 0xC0, 0x69, 0xe7, 0x82, 0x03, 0xbf, 0x2b]))
    StatusMsg_Correct_WithRS =                        bytearray(bytes([0x04, 0x60, 0x10, 0x00, 0xd4, 0x12, 0x43, 0x24, 0x6a, 0x0c, 0x47, 0x32, 0x63, 0xa5]))

    dataHandler = LoraRadioDataHandler(False)

    def setUp(self):
        LoraRadioDataHandler.WiRocLogger.setLevel(logging.DEBUG)

    def tearDown(self):
        self.dataHandler.ReceivedPunchMessageDict = {}
        self.dataHandler.LastPunchMessageTime = None
        self.dataHandler.LastPunchMessage = None
        self.dataHandler.DataReceived = bytearray()

    def test_AddData(self):
        print("============================================================================================== START test_AddData ==============================================================================================")
        self.dataHandler.AddData(bytearray([0x02]))
        self.assertEqual(self.dataHandler.DataReceived, bytearray([0x02]), "Adding data failed 1")

        self.dataHandler.AddData(bytearray([0x03, 0x04]))
        self.assertEqual(self.dataHandler.DataReceived, bytearray([0x02, 0x03, 0x04]), "Adding data failed 2")
        print("=== END test_AddData ===")

    def test_IsLongEnoughToBeMessage(self):
        print("============================================================================================== START test_IsLongEnoughToBeMessage ==============================================================================================")
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
        print("============================================================================================== START test_CacheMessage ==============================================================================================")
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.PunchMsg_Correct_1)
        loraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(TestLoraRadioDataHandler.PunchMsg_Correct_1 + rsCodes)
        self.dataHandler._CacheMessage(loraMsg)
        msgAndMetaData = self.dataHandler.ReceivedPunchMessageDict[loraMsg.GetControlNumber()]
        self.assertEqual(loraMsg, msgAndMetaData.GetLoraRadioMessageRS())
        self.assertIsNotNone(self.dataHandler.LastPunchMessageTime)
        self.assertEqual(self.dataHandler.LastPunchMessage,loraMsg)
        print("=== END test_CacheMessage ===")

    def test_Case1_FindPunchErasuresDoubleMessage(self):
        print("============================================================================================== START test_Case1_FindPunchErasuresDoubleMessage ==============================================================================================")

        correctMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case1_PunchDoubleMsg_Previous_WithRS)
        loraPunchMsg1, loraPunchMsg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(correctMsg)
        # Cache individual messages but remove the whole double message from data received
        self.dataHandler._CacheMessage(loraPunchMsg1)
        self.dataHandler._CacheMessage(loraPunchMsg2)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case1_PunchDoubleMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindReDCoSPunchDoubleErasures(corruptedLoraMsg)
        print("test_Case1_FindPunchErasuresDoubleMessage: " + str(erasures))
        corruptPositions = [0,  1,  2,  3, 5, 6, 7, 8, 11, 12, 17, 18, 19, 20]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case2_FindPunchErasuresDoubleMessage(self):
        print("============================================================================================== START test_Case2_FindPunchErasuresDoubleMessage ==============================================================================================")
        msg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(self.StatusMsg_Correct_WithRS)
        msg.GenerateAndAddRSCode()
        print("Message: " + Utils.GetDataInHex(msg.GetByteArray()[-4:], logging.DEBUG))
        msg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(False, True,
                                                                  self.PunchDoubleMsg_Correct_1[0:10])
        print("Message: " + Utils.GetDataInHex(msg.GetByteArray()[-10:], logging.DEBUG))

        correctMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case2_PunchDoubleMsg_Previous_WithRS)
        loraPunchMsg1, loraPunchMsg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(correctMsg)
        # Cache individual messages but remove the whole double message from data received
        self.dataHandler._CacheMessage(loraPunchMsg1)
        self.dataHandler._CacheMessage(loraPunchMsg2)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case2_PunchDoubleMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindReDCoSPunchDoubleErasures(corruptedLoraMsg)
        corruptPositions = [1,  2,  3, 6, 7, 8, 21, 22, 23, 24]
        print("test_Case2_FindPunchErasuresDoubleMessage erasures: " + str(erasures))
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case3_FindPunchErasuresDoubleMessage(self):
        print("============================================================================================== START test_Case3_FindPunchErasuresDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case3_PunchDoubleMsg_Previous_WithRS)
        loraPunchMsg1, loraPunchMsg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(correctMsg)
        # Cache individual messages but remove the whole double message from data received
        self.dataHandler._CacheMessage(loraPunchMsg1)
        self.dataHandler._CacheMessage(loraPunchMsg2)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case3_PunchDoubleMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindReDCoSPunchDoubleErasures(corruptedLoraMsg)
        print("test_Case3_FindPunchErasuresDoubleMessage: " + str(erasures))
        corruptPositions = [8, 9, 10, 11, 16]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case4_FindPunchErasuresDoubleMessage(self):
        print("============================================================================================== START test_Case4_FindPunchErasuresDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case4_PunchDoubleMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(correctMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case4_PunchDoubleMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindReDCoSPunchDoubleErasures(corruptedLoraMsg)
        print("test_Case4_FindPunchErasuresDoubleMessage: " + str(erasures))
        corruptPositions = [21, 22, 23, 24]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case5_FindPunchErasuresDoubleMessage(self):
        print("============================================================================================== START test_Case5_FindPunchErasuresDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case5_PunchDoubleMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(correctMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case5_PunchDoubleMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindReDCoSPunchDoubleErasures(corruptedLoraMsg)
        print("test_Case5_FindPunchErasuresDoubleMessage: " + str(erasures))
        corruptPositions = [9, 10, 11, 12, 13, 16]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case5_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case5_GetPunchDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case5_PunchDoubleMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(correctMsg)

        corruptedInAirOrder = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(TestLoraRadioDataHandler.Case5_PunchDoubleMsg_Corrupted_WithRS)
        for i in range(0, len(corruptedInAirOrder)):
            self.dataHandler.AddData(corruptedInAirOrder[i:i + 1])

        # Can be decoded with ReDCos but has many combinations to try
        SettingsClass.SetReDCoSCombinationThreshold(500000)
        punchDoubleMsg = self.dataHandler._GetPunchDoubleReDCoSMessage()
        self.assertIsNotNone(punchDoubleMsg)

        print("=== END test_Case5_GetPunchDoubleMessage ===")

    def test_Case6_FindPunchErasuresDoubleMessage(self):
        print("============================================================================================== START test_Case6_FindPunchErasuresDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case6_PunchDoubleMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(correctMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case6_PunchDoubleMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindReDCoSPunchDoubleErasures(corruptedLoraMsg)
        print("test_Case6_FindPunchErasuresDoubleMessage: " + str(erasures))
        corruptPositions = [18, 19, 20]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case6_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case6_GetPunchDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case6_PunchDoubleMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(correctMsg)

        interleaved = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(TestLoraRadioDataHandler.Case6_PunchDoubleMsg_Corrupted_WithRS)
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])
        punchDoubleMsg = self.dataHandler._GetPunchDoubleReDCoSMessage()
        self.assertIsNotNone(punchDoubleMsg)
        print("=== END test_Case6_GetPunchDoubleMessage ===")

    def test_Case7_FindPunchErasuresDoubleMessage(self):
        print("============================================================================================== START test_Case7_FindPunchErasuresDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case7_PunchDoubleMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(correctMsg)
        self.dataHandler.LastPunchMessageTime = time.monotonic() - 9

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case7_PunchDoubleMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindReDCoSPunchDoubleErasures(corruptedLoraMsg)
        print("test_Case7_FindPunchErasuresDoubleMessage: " + str(erasures))
        corruptPositions = [1, 2, 3, 4, 5]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case7_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case7_GetPunchDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case7_PunchDoubleMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(correctMsg)

        interleaved = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(TestLoraRadioDataHandler.Case7_PunchDoubleMsg_Corrupted_WithRS)
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])
        punchDoubleMsg = self.dataHandler._GetPunchDoubleReDCoSMessage()
        self.assertIsNotNone(punchDoubleMsg)
        print("=== END test_Case7_GetPunchDoubleMessage ===")

    def test_Case8_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case8_GetPunchDoubleMessage ==============================================================================================")
        deinterleaved = LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case8_PunchDoubleMsg_Previous_AirOrder_WithRS[:])
        correctMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(deinterleaved)
        self.dataHandler._CacheMessage(correctMsg)
        seconds = 3.4
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case8_PunchDoubleMsg_Corrupted_AirOrder_WithRS[:]
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])
        punchDoubleMsg = self.dataHandler._GetPunchDoubleReDCoSMessage()
        self.assertIsNotNone(punchDoubleMsg)
        self.assertEqual(punchDoubleMsg.GetByteArray(), LoraRadioMessagePunchDoubleReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case8_PunchDoubleMsg_Correct_AirOrder_WithRS))
        print("=== END test_Case8_GetPunchDoubleMessage ===")

    def test_Case9_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case9_GetPunchDoubleMessage ==============================================================================================")
        deinterleaved = LoraRadioMessagePunchDoubleReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case9_PunchDoubleMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(deinterleaved)
        loraPunchMsg1, loraPunchMsg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(prevMsg)
        self.dataHandler._CacheMessage(loraPunchMsg1)
        self.dataHandler._CacheMessage(loraPunchMsg2)
        seconds = 2.8
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case9_PunchDoubleMsg_Corrupted_AirOrder_WithRS[:]
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])
        punchDoubleMsg = self.dataHandler._GetPunchDoubleReDCoSMessage()
        self.assertIsNotNone(punchDoubleMsg)
        print("Decoded msg: " + Utils.GetDataInHex(punchDoubleMsg.GetByteArray(), logging.DEBUG))
        print("Correct msg: " + Utils.GetDataInHex(LoraRadioMessagePunchDoubleReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case9_PunchDoubleMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        self.assertEqual(punchDoubleMsg.GetByteArray(), LoraRadioMessagePunchDoubleReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case9_PunchDoubleMsg_Correct_AirOrder_WithRS))
        print("=== END test_Case9_GetPunchDoubleMessage ===")

    def test_Case10_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case10_GetPunchDoubleMessage ==============================================================================================")
        deinterleaved = LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case10_PunchDoubleMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(deinterleaved)
        self.dataHandler._CacheMessage(prevMsg)
        seconds = 2.8
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case10_PunchDoubleMsg_Corrupted_AirOrder_WithRS[:]
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])
        punchDoubleMsg = self.dataHandler._GetPunchDoubleReDCoSMessage()
        self.assertIsNotNone(punchDoubleMsg)
        print("Decoded msg: " + Utils.GetDataInHex(punchDoubleMsg.GetByteArray(), logging.DEBUG))
        print("Correct msg: " + Utils.GetDataInHex(LoraRadioMessagePunchDoubleReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case10_PunchDoubleMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        # One of the CRC bytes is wrong so exclude it when comparing.
        self.assertEqual(punchDoubleMsg.GetByteArray()[:-2], LoraRadioMessagePunchDoubleReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case10_PunchDoubleMsg_Correct_AirOrder_WithRS)[:-2])
        print("=== END test_Case10_GetPunchDoubleMessage ===")

    def test_Case11_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case11_GetPunchDoubleMessage ==============================================================================================")
        deinterleaved = LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case11_PunchDoubleMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(deinterleaved)
        self.dataHandler._CacheMessage(prevMsg)
        seconds = 16
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case11_PunchDoubleMsg_Corrupted_AirOrder_WithRS[:]
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])
        punchDoubleMsg = self.dataHandler._GetPunchDoubleReDCoSMessage()
        self.assertIsNotNone(punchDoubleMsg)
        print("Decoded msg: " + Utils.GetDataInHex(punchDoubleMsg.GetByteArray(), logging.DEBUG))
        print("Correct msg: " + Utils.GetDataInHex(LoraRadioMessagePunchDoubleReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case11_PunchDoubleMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        self.assertEqual(punchDoubleMsg.GetByteArray(), LoraRadioMessagePunchDoubleReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case11_PunchDoubleMsg_Correct_AirOrder_WithRS))
        print("=== END test_Case11_GetPunchDoubleMessage ===")

    def test_Case12_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case12_GetPunchDoubleMessage ==============================================================================================")
        deinterleaved = LoraRadioMessagePunchDoubleReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case12_PunchDoubleMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(deinterleaved)
        loraPunchMsg1, loraPunchMsg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(prevMsg)
        self.dataHandler._CacheMessage(loraPunchMsg1)
        self.dataHandler._CacheMessage(loraPunchMsg2)
        seconds = 3.2
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case12_PunchDoubleMsg_Corrupted_AirOrder_WithRS[:]
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])
        punchDoubleMsg = self.dataHandler._GetPunchDoubleReDCoSMessage()
        self.assertIsNotNone(punchDoubleMsg)
        print("Decoded msg: " + Utils.GetDataInHex(punchDoubleMsg.GetByteArray(), logging.DEBUG))
        print("Correct msg: " + Utils.GetDataInHex(LoraRadioMessagePunchDoubleReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case12_PunchDoubleMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        # One of the CRC bytes is wrong so exclude it when comparing.
        self.assertEqual(punchDoubleMsg.GetByteArray()[:-2], LoraRadioMessagePunchDoubleReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case12_PunchDoubleMsg_Correct_AirOrder_WithRS)[:-2])
        print("=== END test_Case12_GetPunchDoubleMessage ===")

    def test_Case1_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case1_FindPunchErasuresMessage ==============================================================================================")
        prevMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case1_PunchMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(prevMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case1_PunchMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg)
        print("test_Case1_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [0, 1, 2, 3, 4, 8, 9, 10, 11, 12]
        corruptPositions.append(6)  # add 6 since we sent incorrect week information
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case2_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case2_FindPunchErasuresMessage ==============================================================================================")
        prevMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case2_PunchMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(prevMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case2_PunchMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg)
        print("test_Case2_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case3_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case3_FindPunchErasuresMessage ==============================================================================================")
        prevMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case3_PunchMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(prevMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case3_PunchMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg)
        print("test_Case3_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [1, 2, 3, 4, 6, 7, 8, 9]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case4_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case4_FindPunchErasuresMessage ==============================================================================================")
        prevMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case4_PunchMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(prevMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case4_PunchMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg)
        print("test_Case4_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [9,10,11,12]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case5_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case5_FindPunchErasuresMessage ==============================================================================================")
        prevMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case5_PunchMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(prevMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case5_PunchMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg)
        print("test_Case5_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [1,2,3,4,5,6,7,8,9,10,12]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

        #self.dataHandler._CacheMessage(prevMsg)

        corruptedLoraMsg2 = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case5_PunchMsg_Corrupted_WithRS2)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg2)
        print("test_Case5_FindPunchErasuresMessage 2: " + str(erasures))
        corruptPositions = [1, 2, 3, 4, 5]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case6_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case6_FindPunchErasuresMessage ==============================================================================================")
        prevMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case6_PunchMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(prevMsg)
        # Adjust the LastPunchMessageTime
        seconds = 7
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds
        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case6_PunchMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg)
        print("test_Case6_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [5,6,7,8]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case7_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case7_FindPunchErasuresMessage ==============================================================================================")
        prevMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case7_PunchMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(prevMsg)
        # Adjust the LastPunchMessageTime
        seconds = 7
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds
        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case7_PunchMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg)
        print("test_Case7_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [9,10,11,12]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case8_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case8_FindPunchErasuresMessage ==============================================================================================")
        prevMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case8_PunchMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(prevMsg)
        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case8_PunchMsg_Corrupted_WithRS)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg)
        print("test_Case8_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [10,11,12]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case8_FindPunchErasuresMessage2(self):
        print("============================================================================================== START test_Case8_FindPunchErasuresMessage2 ==============================================================================================")
        prevMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case8_PunchMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(prevMsg)
        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case8_PunchMsg_Corrupted_WithRS2)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg)
        print("test_Case8_FindPunchErasuresMessage2: " + str(erasures))
        corruptPositions = [5, 6, 8, 9, 11, 12]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    def test_Case8_GetPunchMessage_BestCombination(self):
        print("============================================================================================== START test_Case8_GetPunchMessage_BestCombination ==============================================================================================")
        prevMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.Case8_PunchMsg_Previous_WithRS)
        self.dataHandler._CacheMessage(prevMsg)

        interleaved = LoraRadioMessagePunchReDCoSRS.InterleaveToAirOrder(TestLoraRadioDataHandler.Case8_PunchMsg_Corrupted_WithRS_BestCombination)
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])

        loraMsg = self.dataHandler._GetPunchReDCoSMessage()
        self.assertIsNotNone(loraMsg)
        print(Utils.GetDataInHex(loraMsg.GetByteArray(), logging.DEBUG))
        print("=== END test_Case8_GetPunchMessage_BestCombination ===")

    def test_Case9_GetPunchMessage(self):
        print("============================================================================================== START test_Case9_GetPunchMessage ==============================================================================================")
        deinterleaved = LoraRadioMessagePunchDoubleReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case9_PunchMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(deinterleaved)
        loraPunchMsg1, loraPunchMsg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(prevMsg)
        self.dataHandler._CacheMessage(loraPunchMsg1)
        self.dataHandler._CacheMessage(loraPunchMsg2)
        seconds = 2.8
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case9_PunchMsg_Corrupted_AirOrder_WithRS[:]
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])
        punchMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case9_PunchMsg_Corrupted_AirOrder_WithRS[:]), logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case9_PunchMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        self.assertIsNotNone(punchMsg)
        self.assertEqual(punchMsg.GetByteArray(), LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case9_PunchMsg_Correct_AirOrder_WithRS))
        print("=== END test_Case9_GetPunchMessage ===")

    def test_Case10_GetPunchMessage(self):
        print("============================================================================================== START test_Case10_GetPunchMessage ==============================================================================================")
        deinterleaved = LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case10_PunchMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(deinterleaved)
        self.dataHandler._CacheMessage(prevMsg)
        seconds = 9
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case10_PunchMsg_Corrupted_AirOrder_WithRS[:]
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])
        punchMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case10_PunchMsg_Corrupted_AirOrder_WithRS[:]), logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case10_PunchMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        # 3 SINo bytes wrong and 3 ECC bytes wrong so cannot decode
        self.assertIsNone(punchMsg)
        print("=== END test_Case10_GetPunchMessage ===")

    def test_Case11_GetPunchMessage(self):
        print("============================================================================================== START test_Case11_GetPunchMessage ==============================================================================================")
        deinterleaved = LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case11_PunchMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(deinterleaved)
        self.dataHandler._CacheMessage(prevMsg)
        seconds = 5
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case11_PunchMsg_Corrupted_AirOrder_WithRS[:]
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])
        punchMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case11_PunchMsg_Corrupted_AirOrder_WithRS[:]), logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case11_PunchMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        # SN1, SN0, E1 and E2 cannot be guessed.
        # Could TL be guessed. Prev message has TL 0e (14 dec). It was 5 seconds earlier. But TL should be 1a (26 dec). With delays/resends it is difficult to predict a precise TL.
        self.assertIsNone(punchMsg)
        print("=== END test_Case11_GetPunchMessage ===")

    def test_Case12_GetPunchMessage(self):
        print("============================================================================================== START test_Case12_GetPunchMessage ==============================================================================================")
        deinterleaved = LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case12_PunchMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(deinterleaved)
        self.dataHandler._CacheMessage(prevMsg)
        seconds = 5
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case12_PunchMsg_Corrupted_AirOrder_WithRS[:]
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])
        punchMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case12_PunchMsg_Corrupted_AirOrder_WithRS[:]), logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case12_PunchMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        self.assertIsNotNone(punchMsg)
        self.assertEqual(punchMsg.GetByteArray(),LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case12_PunchMsg_Correct_AirOrder_WithRS))
        print("=== END test_Case12_GetPunchMessage ===")

    def test_FindPunchErasures(self):
        print("============================================================================================== START test_FindPunchErasures ==============================================================================================")
        loraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.PunchMsg_Correct_1)
        self.dataHandler._CacheMessage(loraMsg)

        # TH changed to more than 5 minutes more
        corruptedMessageTH = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageTH[7] = corruptedMessageTH[7] | 0x04
        corruptedLoraMsgTH = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            corruptedMessageTH)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsgTH)
        self.assertEqual(erasures, [7], "TH erasure not correct")

        # TH changed to higher than possible
        corruptedMessageTH2 = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageTH2[7] = 0xA9
        corruptedLoraMsgTH2 = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            corruptedMessageTH2)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsgTH2)
        self.assertEqual(erasures, [7], "TH erasure not correct")

        # TH changed to more than 5 minutes more and the combination TH TL too high
        corruptedMessageTL = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageTL[7] = 0xA8
        corruptedMessageTL[8] = 0xC1
        corruptedLoraMsgTL = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            corruptedMessageTL)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsgTL)
        self.assertEqual(erasures, [7], "TH, TL erasure not correct")

        # TL changed to higher than possible (TH already highest)
        loraMsg2 = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.PunchMsg_Correct_HighestTHTL)
        self.dataHandler._CacheMessage(loraMsg2)
        corruptedMessageTL2 = TestLoraRadioDataHandler.PunchMsg_Correct_HighestTHTL[:]
        corruptedMessageTL2[8] = 0xC1
        corruptedLoraMsgTL2 = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            corruptedMessageTL2)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsgTL2)
        self.assertEqual(erasures, [8], "TL erasure not correct")

        # Control number changed
        self.dataHandler._CacheMessage(loraMsg)
        corruptedMessageCN0 = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        corruptedMessageCN0[1] = 0x20
        corruptedLoraMsgCN0 = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            corruptedMessageCN0)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsgCN0)
        self.assertEqual(erasures, [1], "CN0 erasure not correct")
        print("=== END test_FindPunchErasures ===")

    def test_CheckAndRemoveLoraModuleRXError(self):
        print("============================================================================================== START test_CheckAndRemoveLoraModuleRXError ==============================================================================================")
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
        print("============================================================================================== START test_GetMessageTypeByLength ==============================================================================================")
        for i in range(0, len(TestLoraRadioDataHandler.PunchMsg_Correct_1)):
            self.dataHandler.AddData(TestLoraRadioDataHandler.PunchMsg_Correct_1[i:i+1])
        msgTypes = self.dataHandler._GetMessageTypesByLength()
        self.assertEqual(msgTypes, [LoraRadioMessageRS.MessageTypeSIPunchReDCoS], "Didn't get the expected message type")
        print("=== END test_GetMessageTypeByLength ===")

    def test_GetLikelyMessageTypes(self):
        print("============================================================================================== START test_GetLikelyMessageTypes ==============================================================================================")
        loraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.PunchMsg_Correct_1)
        self.dataHandler._CacheMessage(loraMsg)

        # controlnumber bit 8
        messageArr = TestLoraRadioDataHandler.PunchMsg_Correct_1[:]
        for i in range(0, len(messageArr)):
            self.dataHandler.AddData(messageArr[i:i+1])
        messageTypes = self.dataHandler._GetLikelyMessageTypes()
        self.assertEqual(messageTypes, [0x07], "Didn't get the expected message type short punch")

        self.dataHandler.DataReceived = bytearray()
        print("=== END test_GetLikelyMessageTypes ===")

    def test_GetPunchMessage(self):
        print("============================================================================================== START test_GetPunchMessage ==============================================================================================")
        interleaved = LoraRadioMessagePunchReDCoSRS.InterleaveToAirOrder(TestLoraRadioDataHandler.PunchMsg_Correct_1)
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])

        # wrong message type
        punchMsg = self.dataHandler._GetAckMessage()
        self.assertIsNone(punchMsg)
        # right message type
        punchMsg = self.dataHandler._GetPunchReDCoSMessage()
        self.assertIsNotNone(punchMsg)
        # Message is only removed from datareceived in TryGetMessage so it should fetch same again
        punchMsg2 = self.dataHandler._GetPunchReDCoSMessage()
        self.assertEqual(punchMsg.GetByteArray(), punchMsg2.GetByteArray())
        print("=== END test_GetPunchMessage ===")

    def test_GetTwoPunchMessages(self):
        print("============================================================================================== START test_GetTwoPunchMessages ==============================================================================================")
        # Add two messages at once before trying to fetch the messages
        interleaved = LoraRadioMessagePunchReDCoSRS.InterleaveToAirOrder(TestLoraRadioDataHandler.PunchMsg_Correct_1)
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])

        punchMsg = self.dataHandler._GetPunchReDCoSMessage()
        self.assertIsNotNone(punchMsg)
        messageLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchReDCoS]
        self.dataHandler._removeBytesFromDataReceived(messageLength + self.dataHandler.RSSIByteCount)
        punchMsg = self.dataHandler.GetMessage()  # Removes the message from data received
        self.assertIsNotNone(punchMsg, "second message not fetched")
        punchMsg = self.dataHandler._GetPunchReDCoSMessage()
        self.assertIsNone(punchMsg)
        print("=== END test_GetTwoPunchMessages ===")

    def test_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_GetPunchDoubleMessage ==============================================================================================")
        # messageTypeToTry, erasures = None):
        interleaved = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])

        print("added no of bytes: " + str(len(self.dataHandler.DataReceived)))

        # wrong message type
        punchMsg = self.dataHandler._GetPunchReDCoSMessage()
        self.assertIsNone(punchMsg)
        # right message type
        punchDoubleMsg = self.dataHandler._GetPunchDoubleReDCoSMessage()
        self.assertIsNotNone(punchDoubleMsg)
        # returned message so buffer should be empty
        punchDoubleMsg = self.dataHandler._GetPunchDoubleReDCoSMessage()
        self.assertIsNotNone(punchDoubleMsg)
        self.assertGreater(len(self.dataHandler.DataReceived), 0)

        punchDoubleMsg = self.dataHandler.GetMessage()
        self.assertIsNotNone(punchDoubleMsg)
        self.assertEqual(len(self.dataHandler.DataReceived), 0)

        print("=== END test_GetPunchDoubleMessage ===")

    def test_GetTwoPunchDoubleMessages(self):
        print("============================================================================================== START test_GetTwoPunchDoubleMessages ==============================================================================================")
        # Add two messages at once before trying to fetch the messages
        interleaved = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(
            TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])

        punchDoubleMsg = self.dataHandler._GetPunchDoubleReDCoSMessage()
        self.assertIsNotNone(punchDoubleMsg)
        # remove first message manually since it is only done in TryGetMessage
        messageLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS]
        self.dataHandler._removeBytesFromDataReceived(messageLength + self.dataHandler.RSSIByteCount)
        punchDoubleMsg = self.dataHandler._GetPunchDoubleReDCoSMessage()
        self.assertIsNotNone(punchDoubleMsg, "could not get second message")
        punchDoubleMsg = self.dataHandler._GetPunchDoubleReDCoSMessage()
        self.assertIsNotNone(punchDoubleMsg)
        print("=== END test_GetTwoPunchDoubleMessages ===")

    def test_GetMessage_PunchMessage_Correct(self):
        print("============================================================================================== START test_GetMessage_PunchMessage_Correct ==============================================================================================")
        self.dataHandler.AddData(bytearray([0, 0]))
        msg = self.dataHandler.GetMessage()

        interleaved = LoraRadioMessagePunchReDCoSRS.InterleaveToAirOrder(TestLoraRadioDataHandler.PunchMsg_Correct_1)
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])

        msg = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg, "expected to receive the message back")
        self.assertEqual(TestLoraRadioDataHandler.PunchMsg_Correct_1, msg.GetByteArray(),
                         "Didn't receive the same bytes back")
        self.assertEqual(len(self.dataHandler.DataReceived), 0,
                         "DataReceived not empty")
        print("=== END test_GetMessage_PunchMessage_Correct ===")

    def test_GetMessage_PunchMessage_WithPrefixGarbage(self):
        print("============================================================================================== START test_GetMessage_PunchMessage_WithPrefixGarbage ==============================================================================================")
        self.dataHandler.AddData(bytearray([0,0]))
        msg = self.dataHandler.GetMessage() # will clear datarecieve

        interleaved = LoraRadioMessagePunchReDCoSRS.InterleaveToAirOrder(TestLoraRadioDataHandler.PunchMsg_Correct_1)
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])

        msg = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg, "expected to receive the message back")
        self.assertEqual(TestLoraRadioDataHandler.PunchMsg_Correct_1, msg.GetByteArray(),
                         "Didn't receive the same bytes back")
        self.assertEqual(len(self.dataHandler.DataReceived), 0,
                         "DataReceived not empty")
        print("=== END test_GetMessage_PunchMessage_WithPrefixGarbage ===")

    def test_GetMessage_CorruptedPunchMessage(self):
        print("============================================================================================== START test_GetMessage_CorruptedPunchMessage ==============================================================================================")
        interleaved = LoraRadioMessagePunchReDCoSRS.InterleaveToAirOrder(TestLoraRadioDataHandler.PunchMsg_Corrupted_1)
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])

        # Not decodable because we have no lastmessage so we incorrecly will assume wrong
        # Controlnumber CN0 and CN1Plus
        msg2 = self.dataHandler.GetMessage()
        self.assertIsNone(msg2, "Received a message but it shouldn't be decodable")

        loraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(
            TestLoraRadioDataHandler.PunchMsg_Correct_1)
        self.dataHandler._CacheMessage(loraMsg)

        # correct one byte, then it should be decodable without RedCos
        corrupt = TestLoraRadioDataHandler.PunchMsg_Corrupted_1[:]
        corrupt[4] = 0x00
        interleaved2  = LoraRadioMessagePunchReDCoSRS.InterleaveToAirOrder(corrupt)
        for i in range(0, len(interleaved2)):
            self.dataHandler.AddData(interleaved2[i:i + 1])

        msg3 = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg3, "Didn't receive a message, it should be decodable")
        print("=== END test_GetMessage_CorruptedPunchMessage ===")

    def test_GetMessage_PunchDoubleMessage(self):
        # messageTypeToTry, erasures = None):
        print("============================================================================================== START test_GetMessage_PunchDoubleMessage ==============================================================================================")
        interleaved = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1)
        for i in range(0, len(interleaved)):
            self.dataHandler.AddData(interleaved[i:i + 1])

        msg = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg, "Expected to receive the message back")
        self.assertEqual(TestLoraRadioDataHandler.PunchDoubleMsg_Correct_1, msg.GetByteArray(), "Didn't receive the same bytes back")

        interleaved2 = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(TestLoraRadioDataHandler.PunchDoubleMsg_Corrupted_1[:])
        for i in range(0, len(interleaved2)):
            self.dataHandler.AddData(interleaved2[i:i + 1])

        msg2 = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg2, "Message should be decodable with alternatives")

        print("=== END test_GetMessage_PunchDoubleMessage ===")

    def test_GetMessage_Status(self):
        print("============================================================================================== START test_GetMessage_Status ==============================================================================================")
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

    def test_GetAlternatives(self):
        print("============================================================================================== START test_GetAlternatives ==============================================================================================")
        msg = LoraRadioMessageCreator.GetPunchReDCoSMessage(
            TestLoraRadioDataHandler.PunchReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
            TestLoraRadioDataHandler.PunchReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
            TestLoraRadioDataHandler.PunchReDCoSMsg_Correct_1_WithoutRS_CS[1:])

        self.dataHandler._CacheMessage(msg)

        msg2 = LoraRadioMessageCreator.GetPunchReDCoSMessage(
            TestLoraRadioDataHandler.PunchReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
            TestLoraRadioDataHandler.PunchReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
            TestLoraRadioDataHandler.PunchReDCoSMsg_Correct_2_WithoutRS_CS[1:])

        alts, fixedValues, fixedErasures = self.dataHandler._GetPunchMessageAlternatives(msg2)

        self.assertEqual(len(alts), 4)

    def test_GetAlternativesDouble(self):
        print("============================================================================================== START test_GetAlternativesDouble ==============================================================================================")
        msg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[1:])

        msg1, msg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(msg)
        self.dataHandler._CacheMessage(msg1)
        self.dataHandler._CacheMessage(msg2)

        msg3 = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[1:])

        alts, fixedValues, fixedErasures = self.dataHandler._GetPunchDoubleMessageAlternatives(msg3)

        for i in range(len(alts)):
            print(alts[i])

        self.assertEqual(len(alts), 8)

    def test_GetReDCoSErasures(self):
        print("============================================================================================== START test_GetReDCoSErasures ==============================================================================================")

        msg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[1:])

        msg1, msg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(msg)
        self.dataHandler._CacheMessage(msg1)
        self.dataHandler._CacheMessage(msg2)

        msg3 = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[1:])

        alts, fixedValues, fixedErasures = self.dataHandler._GetPunchDoubleMessageAlternatives(msg3)
        erasuresCombinations = self.dataHandler._GetReDCoSErasureCombinations(msg3, fixedValues, fixedErasures, 0)

        self.assertEqual(len(alts), 8, "No of alternatives wrong")
        self.assertEqual(fixedValues, [0, 1, 2, 6, 7, 9, 10, 14, 15], "fixedValues unexpected")
        self.assertEqual(fixedErasures, [], "fixedErasures unexpected")
        self.assertEqual(len(list(erasuresCombinations)), 12870, "No of erasure combinations unexpected")

    def test_SevenPlusOneCRCWrong_DecodeReDCos(self):
        print("============================================================================================== START test_SevenPlusOneCRCWrong_DecodeReDCos ==============================================================================================")

        msg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[1:])

        msg1, msg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(msg)
        # print("tw: "+  str(msg2.GetTwelveHourTimer()))
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
        #msg4Corrupted = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(corruptedMessageData)

        interleaved2 = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(corruptedMessageData[:])
        for i in range(0, len(interleaved2)):
            self.dataHandler.AddData(interleaved2[i:i + 1])

        SettingsClass.SetReDCoSCombinationThreshold(500000)
        msg = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg)

    def test_SevenPlusOneCRCWrong_FewerCombinations_DecodeReDCos(self):
        print("============================================================================================== START test_SevenPlusOneCRCWrong_FewerCombinations_DecodeReDCos ==============================================================================================")

        msg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[1:])

        msg1, msg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(msg)
        # print("tw: "+  str(msg2.GetTwelveHourTimer()))
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

        interleaved2 = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(corruptedMessageData[:])
        for i in range(0, len(interleaved2)):
            self.dataHandler.AddData(interleaved2[i:i + 1])

        # We don't expect it to work with this few combinations (this force it to reduce combinations to inlcude only for erasures)
        SettingsClass.SetReDCoSCombinationThreshold(5000)
        msg = self.dataHandler.GetMessage()
        self.assertIsNone(msg)

    def test_SevenPlusOneCRCWrong_MoreCombinations_DecodeReDCos(self):
        print("============================================================================================== START test_SevenPlusOneCRCWrong_MoreCombinations_DecodeReDCos ==============================================================================================")

        msg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[1:])


        msg1, msg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(msg)
        self.dataHandler._CacheMessage(msg1)
        self.dataHandler._CacheMessage(msg2)

        msg3 = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[1:])
        correct = msg3.GetByteArray()[:]

        corruptedMessageData = msg3.GetByteArray()[:]
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.TL] = 0x00
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.TL_2] = 0x00
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.SN0] = 0x01
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.SN1] = 0x01
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.SN2] = 0x01
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.SN0_2] = 0x01
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.SN1_2] = 0x01
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.CRC0] = 0x00
        # msg4Corrupted = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(corruptedMessageData)

        interleaved2 = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(corruptedMessageData[:])
        for i in range(0, len(interleaved2)):
            self.dataHandler.AddData(interleaved2[i:i + 1])

        # This should reduce the combinations to include 6 erasures. Plus the two extra ECC bytes can correct one error. So should work.
        SettingsClass.SetReDCoSCombinationThreshold(10000)
        msg4 = self.dataHandler.GetMessage()

        print("Correct message  : " + Utils.GetDataInHex(correct, logging.DEBUG))
        print("Decoded message  : " + Utils.GetDataInHex(msg4.GetByteArray(), logging.DEBUG))

        self.assertIsNotNone(msg4)
        self.assertEqual(correct, msg4.GetByteArray())

    def test_FivePlusOneCRCWrong_FewerCombinations_DecodeReDCos(self):
        print("============================================================================================== START test_FivePlusOneCRCWrong_FewerCombinations_DecodeReDCos ==============================================================================================")

        msg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_1_WithoutRS_CS[1:])


        msg1, msg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(msg)
        self.dataHandler._CacheMessage(msg1)
        self.dataHandler._CacheMessage(msg2)

        msg3 = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.BatLowBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[0] & LoraRadioMessageRS.AckBitMask,
            TestLoraRadioDataHandler.PunchDoubleReDCoSMsg_Correct_2_WithoutRS_CS[1:])
        correct = msg3.GetByteArray()[:]

        corruptedMessageData = msg3.GetByteArray()[:]
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.TL] = 0x00
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.TL_2] = 0x00
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.SN0] = 0x01
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.SN1] = 0x01
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.SN2] = 0x01
        #corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.SN0_2] = 0x01
        #corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.SN1_2] = 0x01
        corruptedMessageData[LoraRadioMessagePunchDoubleReDCoSRS.CRC0] = 0x00
        # msg4Corrupted = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(corruptedMessageData)

        interleaved2 = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(corruptedMessageData[:])
        for i in range(0, len(interleaved2)):
            self.dataHandler.AddData(interleaved2[i:i + 1])

        # We don't expect it to work with this few combinations
        SettingsClass.SetReDCoSCombinationThreshold(5000)
        msg4 = self.dataHandler.GetMessage()

        print("Correct message  : " + Utils.GetDataInHex(correct, logging.DEBUG))
        print("Decoded message  : " + Utils.GetDataInHex(msg4.GetByteArray(), logging.DEBUG))

        self.assertIsNotNone(msg4)
        self.assertEqual(correct, msg4.GetByteArray())
