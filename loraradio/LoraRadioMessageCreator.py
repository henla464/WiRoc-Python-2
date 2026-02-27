__author__ = 'henla464'

import logging
from utils.utils import Utils
from loraradio.LoraRadioMessageRS import LoraRadioMessageAckRS, \
    LoraRadioMessageStatusRS, LoraRadioMessageStatus2RS, LoraRadioMessagePunchReDCoSRS, \
    LoraRadioMessagePunchDoubleReDCoSRS, LoraRadioMessageRS, LoraRadioMessageHAMCallSignRS


class LoraRadioMessageCreator(object):
    @staticmethod
    def GetAckMessage(theHash: bytearray) -> LoraRadioMessageAckRS:
        loraAckMessage = LoraRadioMessageAckRS()
        loraAckMessage.SetAckRequested(False)
        loraAckMessage.SetBatteryLow(False)
        loraAckMessage.SetRepeater(False)
        loraAckMessage.AddPayload(theHash)
        loraAckMessage.AddPayload(theHash)
        loraAckMessage.AddPayload(theHash)
        return loraAckMessage

    @staticmethod
    def GetAckMessageByFullMessageData(fullMessageData: bytearray, rssiValue: int = None,
                                       snrValue: int = None,
                                       statusValue: int = None) -> LoraRadioMessageAckRS:
        loraAckMessage = LoraRadioMessageAckRS()
        loraAckMessage.SetHeader(fullMessageData[0:1])
        loraAckMessage.AddPayload(fullMessageData[1:])
        loraAckMessage.SetRSSIValue(rssiValue)
        loraAckMessage.SetSNRValue(snrValue)
        loraAckMessage.SetStatusValue(statusValue)
        return loraAckMessage

    @staticmethod
    def GetPunchReDCoSMessage(batteryLow: bool, ackReq: bool,
                              payload: bytearray = None) -> LoraRadioMessagePunchReDCoSRS:
        loraPunchMessage = LoraRadioMessagePunchReDCoSRS()
        loraPunchMessage.SetBatteryLow(batteryLow)
        loraPunchMessage.SetAckRequested(ackReq)
        if payload is not None:
            loraPunchMessage.AddPayload(payload)
            loraPunchMessage.GenerateAndAddRSCode()
            loraPunchMessage.GenerateAndAddCRC()
        return loraPunchMessage

    @staticmethod
    def GetPunchReDCoSMessageByFullMessageData(fullMessageDataDeinterleaved: bytearray,
                                               rssiValue: int = None,
                                               snrValue: int = None,
                                               statusValue: int = None) -> LoraRadioMessagePunchReDCoSRS:
        if len(fullMessageDataDeinterleaved) < LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchReDCoS]:
            raise Exception('Message data too short for a LoraRadioMessagePunchRedCoSRS message')
        loraPunchMessage = LoraRadioMessagePunchReDCoSRS()
        loraPunchMessage.SetHeader(fullMessageDataDeinterleaved[0:1])
        loraPunchMessage.AddPayload(fullMessageDataDeinterleaved[
                                        1:-LoraRadioMessagePunchReDCoSRS.NoOfECCBytes - LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes])
        # print("punchmessage payload: " + Utils.GetDataInHex(fullMessageDataDeinterleaved[1:-LoraRadioMessagePunchReDCoSRS.NoOfECCBytes-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes],
        #                                                    logging.DEBUG))
        loraPunchMessage.AddRSCode(fullMessageDataDeinterleaved[
                                       -LoraRadioMessagePunchReDCoSRS.NoOfECCBytes - LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes:-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes])
        loraPunchMessage.AddCRC(fullMessageDataDeinterleaved[-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes:])
        loraPunchMessage.SetRSSIValue(rssiValue)
        loraPunchMessage.SetSNRValue(snrValue)
        loraPunchMessage.SetStatusValue(statusValue)
        return loraPunchMessage

    @staticmethod
    def GetPunchDoubleReDCoSMessage(batteryLow: bool, ackReq: bool,
                                    payload: bytearray = None,
                                    snrValue: int = None,
                                    statusValue: int = None) -> LoraRadioMessagePunchDoubleReDCoSRS:
        loraPunchDoubleMessage = LoraRadioMessagePunchDoubleReDCoSRS()
        loraPunchDoubleMessage.SetBatteryLow(batteryLow)
        loraPunchDoubleMessage.SetAckRequested(ackReq)
        if payload is not None:
            loraPunchDoubleMessage.AddPayload(payload)
            loraPunchDoubleMessage.GenerateAndAddRSCode()
            loraPunchDoubleMessage.GenerateAndAddCRC()

        return loraPunchDoubleMessage

    @staticmethod
    def GetPunchDoubleReDCoSMessageByFullMessageData(fullMessageDataDeinterleaved: bytearray,
                                                     rssiValue: int = None,
                                                     snrValue: int = None,
                                                     statusValue: int = None) -> LoraRadioMessagePunchDoubleReDCoSRS:
        loraPunchDoubleMessage = LoraRadioMessagePunchDoubleReDCoSRS()
        loraPunchDoubleMessage.SetHeader(fullMessageDataDeinterleaved[0:1])
        loraPunchDoubleMessage.AddPayload(fullMessageDataDeinterleaved[
                                              1:-LoraRadioMessagePunchDoubleReDCoSRS.NoOfECCBytes - LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes])
        loraPunchDoubleMessage.AddRSCode(fullMessageDataDeinterleaved[
                                             -LoraRadioMessagePunchDoubleReDCoSRS.NoOfECCBytes - LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes:-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes])
        loraPunchDoubleMessage.AddCRC(fullMessageDataDeinterleaved[-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes:])
        loraPunchDoubleMessage.SetRSSIValue(rssiValue)
        loraPunchDoubleMessage.SetSNRValue(snrValue)
        loraPunchDoubleMessage.SetStatusValue(statusValue)
        return loraPunchDoubleMessage

    @staticmethod
    def GetStatusMessage(batteryLow: bool, noOfLoraMsgSentNotAcked: int,
                         allLoraPunchesSucceded: bool) -> LoraRadioMessageStatusRS:
        loraStatusMessage = LoraRadioMessageStatusRS(noOfLoraMsgSentNotAcked, allLoraPunchesSucceded)
        loraStatusMessage.SetBatteryLow(batteryLow)
        loraStatusMessage.SetAckRequested(False)
        loraStatusMessage.SetRepeater(False)
        loraStatusMessage.GenerateAndAddRSCode()
        return loraStatusMessage

    @staticmethod
    def GetStatus2Message(batteryLow: bool, noOfLoraMsgSentNotAcked: int, allLoraPunchesSucceded: bool,
                          SRRDongleRedFound: bool, SRRDongleRedAck: bool,
                          SRRDongleBlueFound: bool, SRRDongleBlueAck: bool,
                          SIMasterConnectedOnUSB1: bool, SIMasterConnectedOnUSB2: bool,
                          internalSRRRedEnabled: bool, internalSRRRedAck: bool,
                          internalSRRBlueEnabled: bool, internalSRRBlueAck: bool,
                          internalSRRBlueDirection: bool, internalSRRRedDirection: bool,
                          tcpipSirapEnabled: bool, serialPortBaudRate4800: bool, serialPortDirection: bool
                          ) -> LoraRadioMessageStatus2RS:
        loraStatus2Message = LoraRadioMessageStatus2RS(noOfLoraMsgSentNotAcked, allLoraPunchesSucceded,
                                                       SRRDongleRedFound,
                                                       SRRDongleRedAck, SRRDongleBlueFound, SRRDongleBlueAck,
                                                       SIMasterConnectedOnUSB1, SIMasterConnectedOnUSB2,
                                                       internalSRRRedEnabled, internalSRRRedAck,
                                                       internalSRRBlueEnabled, internalSRRBlueAck,
                                                       internalSRRBlueDirection, internalSRRRedDirection,
                                                       tcpipSirapEnabled, serialPortBaudRate4800, serialPortDirection)
        loraStatus2Message.SetBatteryLow(batteryLow)
        loraStatus2Message.SetAckRequested(False)
        loraStatus2Message.SetRepeater(False)
        loraStatus2Message.GenerateAndAddRSCode()
        return loraStatus2Message

    @staticmethod
    def GetStatusMessageByFullMessageData(fullMessageData: bytearray, rssiValue: int = None,
                                           snrValue: int = None,
                                           statusValue: int = None) -> LoraRadioMessageStatusRS:
        loraStatusMessage = LoraRadioMessageStatusRS()
        loraStatusMessage.SetHeader(fullMessageData[0:1])
        loraStatusMessage.SetPayload(fullMessageData[1:-LoraRadioMessageStatusRS.NoOfECCBytes])
        loraStatusMessage.AddRSCode(fullMessageData[-LoraRadioMessageStatusRS.NoOfECCBytes:])
        loraStatusMessage.SetRSSIValue(rssiValue)
        loraStatusMessage.SetSNRValue(snrValue)
        loraStatusMessage.SetStatusValue(statusValue)
        return loraStatusMessage

    @staticmethod
    def GetStatus2MessageByFullMessageData(fullMessageData: bytearray,
                                           rssiValue: int = None,
                                           snrValue: int = None,
                                           statusValue: int = None) -> LoraRadioMessageStatus2RS:
        loraStatusMessage = LoraRadioMessageStatus2RS()
        loraStatusMessage.SetHeader(fullMessageData[0:1])
        loraStatusMessage.SetPayload(fullMessageData[1:-LoraRadioMessageStatus2RS.NoOfECCBytes])
        loraStatusMessage.AddRSCode(fullMessageData[-LoraRadioMessageStatus2RS.NoOfECCBytes:])
        loraStatusMessage.SetRSSIValue(rssiValue)
        loraStatusMessage.SetSNRValue(snrValue)
        loraStatusMessage.SetStatusValue(statusValue)
        return loraStatusMessage

    @staticmethod
    def GetHAMCallSignMessage(HAMCallSign: str) -> LoraRadioMessageHAMCallSignRS:
        loraHamMessage = LoraRadioMessageHAMCallSignRS(HAMCallSign)
        return loraHamMessage
