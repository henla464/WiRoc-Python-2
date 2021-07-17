# from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
# from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
# from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
# from settings.settings import SettingsClass
#
# class LoraSIMessageToLoraAckTransform(object):
#
#     @staticmethod
#     def GetInputMessageType():
#         return "LORA"
#
#     @staticmethod
#     def GetInputMessageSubType():
#         return "SIMessage"
#
#     @staticmethod
#     def GetOutputMessageType():
#         return "LORA"
#
#     @staticmethod
#     def GetName():
#         return "LoraSIMessageToLoraAckTransform"
#
#     @staticmethod
#     def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
#         repeater = LoraRadioDataHandler.GetRepeater(messageBoxData.MessageData)
#         ackRequested = LoraRadioDataHandler.GetAckRequested(messageBoxData.MessageData)
#         if repeater and ackRequested and SettingsClass.GetLoraMode() == "RECEIVER":
#             # ack (10), waiting for repeater to reply with ack
#             # and send message (23) to receiver
#             # + little delay 0.15 sec
#             return SettingsClass.GetLoraMessageTimeSendingTimeSByMessageType(LoraRadioMessageRS.MessageTypeLoraAck) + \
#                         SettingsClass.GetLoraMessageTimeSendingTimeSByMessageType(LoraRadioMessageRS.MessageTypeSIPunch) + 0.15
#         return None
#
#     @staticmethod
#     def GetDeleteAfterSent():
#         return True
#
#     @staticmethod
#     def GetDeleteAfterSentChanged():
#         return False
#
#     #payloadData is a bytearray
#     @staticmethod
#     def Transform(msgSub, subscriberAdapter):
#         # This transform is only used to send ack message from the receiver
#         # when repeater is requested (because then we should delay sending ack)
#         if SettingsClass.GetLoraMode() == "RECEIVER":
#             payloadData = msgSub.MessageData
#             incomingMsgType = LoraRadioDataHandler.GetHeaderMessageType(payloadData)
#             repeater = LoraRadioDataHandler.GetRepeater(payloadData)
#             ackReq = LoraRadioDataHandler.GetAckRequested(payloadData)
#             if repeater and ackReq:
#                 recMsg = None
#                 if incomingMsgType == LoraRadioMessageRS.MessageTypeSIPunch:
#                     recMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(payloadData, rssiValue=None)
#                 if incomingMsgType == LoraRadioMessageRS.MessageTypeSIPunchExt:
#                     recMsg = LoraRadioMessageCreator.GetPunchExtMessageByFullMessageData(payloadData, rssiValue=None)
#                 if recMsg is not None:
#                     md5Hash = recMsg.GetMD5Hash()
#                     ackMsg = LoraRadioMessageCreator.GetAckMessage(md5Hash)
#                     ackMsg.SetAckRequested(True) # indicate ack sent from receiver
#                     ackMsg.SetRepeater(False) # indicate this ack doesn't come from repeater
#                     ackMsg.GenerateRSCode()
#                     return {"Data": ackMsg.GetByteArray(), "MessageID": ackMsg.GetMD5Hash()}
#         return None