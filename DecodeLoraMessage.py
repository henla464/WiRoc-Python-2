# from datamodel.datamodel import LoraRadioMessage
# from datamodel.datamodel import SIMessage
# from utils.utils import Utils
# import logging
#
# def GetDataInHex(data):
#     dataInHex = ''.join(format(x, '02x') for x in data)
#     return dataInHex
#
# hexString = input("Enter your the LoraRadioMessage hex string: ")
# rssiExpected = len(hexString) >= 50 or (int(hexString[5],16)&0x07)==0x01
# print('rssiExpected: ' + str(rssiExpected))
# loraMessage = LoraRadioMessage()
# loraMessage.SetRSSIByteExpected(rssiExpected)
#
# cnt = 0
#
# while len(hexString) >= 2:
#     aByte = hexString[0:2]
#     if cnt == 0:
#         print(str(aByte) + ' STX')
#     elif cnt == 1:
#         print(str(aByte) + ' LENGTH')
#     elif cnt == 2:
#         print(str(aByte) + ' ACK(1) + BAT(1) + REPEATER(1) + LORA MESSAGE TYPE(6)')
#     elif cnt == 3:
#         print(str(aByte) + ' MESSAGE NUMBER')
#     elif cnt == 4:
#         print(str(aByte) + ' CRC')
#     elif cnt == 5:
#         print(str(aByte) + ' STX SIPUNCH')
#     elif cnt == 6:
#         print(str(aByte) + ' SI MESSAGE TYPE')
#     elif cnt == 7:
#         print(str(aByte) + ' LENGTH')
#     elif cnt == 8:
#         print(str(aByte) + ' CN1')
#     elif cnt == 9:
#         print(str(aByte) + ' CN0')
#     elif cnt == 10:
#         print(str(aByte) + ' SN3')
#     elif cnt == 11:
#         print(str(aByte) + ' SN2')
#     elif cnt == 12:
#         print(str(aByte) + ' SN1')
#     elif cnt == 13:
#         print(str(aByte) + ' SN0')
#     elif cnt == 14:
#         print(str(aByte) + ' reserved(2) + 4-week counter (2) + day of week (3) + AM=0/PM=1')
#     elif cnt == 15:
#         print(str(aByte) + ' TH twelve hour high')
#     elif cnt == 16:
#         print(str(aByte) + ' TL twelve hour low')
#     elif cnt == 17:
#         print(str(aByte) + ' TSS sub second')
#     elif cnt == 18:
#         print(str(aByte) + ' MEM2')
#     elif cnt == 19:
#         print(str(aByte) + ' MEM1')
#     elif cnt == 20:
#         print(str(aByte) + ' MEM0')
#     elif cnt == 21:
#         print(str(aByte) + ' CRC1')
#     elif cnt == 22:
#         print(str(aByte) + ' CRC0')
#     elif cnt == 23:
#         print(str(aByte) + ' ETX')
#     elif cnt == 24:
#         print(str(aByte) + ' RSSI')
#     cnt += 1
#     hexString = hexString[2:]
#     decValue = int(aByte, 16)
#     loraMessage.AddByte(decValue)
#
# print("")
# print("LORA MESSAGE")
# ackRequested = loraMessage.GetAcknowledgementRequested()
# print("Ack requested: " + str(ackRequested))
# batteryLow = loraMessage.GetBatteryLowBit()
# print("Battery low: " + str(batteryLow))
# checksumOK = loraMessage.GetIsChecksumOK()
# print("Checksum ok?: " + str(checksumOK))
# messageCRC = loraMessage.GetByteArray()[4]
# print("Checksum in message: " + format(messageCRC, '02x'))
# theMessageByteArray = loraMessage.GetByteArray()
# theMessageByteArray[4] = 0 # clear CRC
# calculatedCrc = 0
# calculatedCrc = Utils.CalculateCRC(theMessageByteArray)
# oneByteCalculatedCrc = calculatedCrc[0] ^ calculatedCrc[1]
# print("Calculated CRC: " + format(oneByteCalculatedCrc, '02x'))
# try:
#     messageID = loraMessage.GetMessageID()
#     messageIDStr = GetDataInHex(messageID)
#     print("MessageID: " + str(messageIDStr))
# except:
#     print("MessageID could not be retrieved")
# messageNumber = loraMessage.GetMessageNumber()
# print("MessageNumber: " + str(messageNumber))
# messageType = loraMessage.GetMessageType()
# print("MessageType: " + str(messageType))
# repeater = loraMessage.GetRepeaterBit()
# print("Repeater bit: " + str(repeater))
# rssiValue = loraMessage.GetRSSIValue()
# print("RSSI: " + str(rssiValue))
#
# print("")
# print("SI MESSAGE")
# loraHeaderSize = LoraRadioMessage.GetHeaderSize()
# siPayloadData = loraMessage.GetSIMessageByteArray()
# siMsg = SIMessage()
# siMsg.AddPayload(siPayloadData)
# messageType = siMsg.GetMessageType()
# print("messageType: " + format(messageType, '02x'))
# hour = siMsg.GetHour()
# print("Hour: " + str(hour))
# minute = siMsg.GetMinute()
# print("Minute: " + str(minute))
# second = siMsg.GetSeconds()
# print("Second: " + str(second))
# subSecond = siMsg.GetSubSecondAsTenthOfSeconds()
# print("subsecond: " + str(subSecond))
# backupMemoryAddress = siMsg.GetBackupMemoryAddressAsInt()
# print("backupMemoryAddress: " + str(backupMemoryAddress))
# checksumOK = siMsg.GetIsChecksumOK()
# print("checksum ok?: " + str(checksumOK))
# siCRC = siMsg.GetByteArray()[-3:-1]
# print("si message crc: " + GetDataInHex(siCRC))
# partToCalculateCRSOn = siMsg.GetByteArray()[1:-3]
# print("part si message crc is calculated on: " + GetDataInHex(partToCalculateCRSOn))
# crc = Utils.CalculateCRC(partToCalculateCRSOn)
# print("calculated si crc: " + GetDataInHex(crc))
#
# siCardNo = siMsg.GetSICardNumber()
# print("siCardNo: " + str(siCardNo))
# stationNo = siMsg.GetStationNumber()
# print("stationNo: " + str(stationNo))
