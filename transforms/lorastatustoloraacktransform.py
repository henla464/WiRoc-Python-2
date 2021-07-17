# from loraradio.LoraRadioMessageRS import LoraRadioMessageStatusRS
# from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
# from settings.settings import SettingsClass
#
# class LoraStatusToLoraAckTransform(object):
#
#     @staticmethod
#     def GetInputMessageType():
#         return "LORA"
#
#     @staticmethod
#     def GetInputMessageSubType():
#         return "Status"
#
#     @staticmethod
#     def GetOutputMessageType():
#         return "LORA"
#
#     @staticmethod
#     def GetName():
#         return "LoraStatusToLoraAckTransform"
#
#     @staticmethod
#     def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
#         if SettingsClass.GetLoraMode() == "RECEIVER":
#             payloadData = messageBoxData.MessageData
#             loraMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(payloadData, rssiByte=None)
#             if loraMsg.GetRepeaterBit() and loraMsg.GetAcknowledgementRequested():
#                 # ack (10), waiting for repeater to reply with ack
#                 # and send message (23) to receiver
#                 # + little delay 0.1 sec
#                 return SettingsClass.GetLoraMessageTimeSendingTimeSByMessageType(LoraRadioMessageStatusRS.MessageTypeLoraAck) + \
#                        SettingsClass.GetLoraMessageTimeSendingTimeS(len(payloadData))+0.1
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
#             loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(payloadData, rssiByte=None)
#
#             if loraStatusMsg.GetRepeaterBit() and loraStatusMsg.GetAcknowledgementRequested():
#                 md5Hash = loraStatusMsg.GetMD5Hash()
#                 loraStatusAckMsg = LoraRadioMessageCreator.GetAckMessage(md5Hash)
#                 loraStatusAckMsg.SetAckRequested(True) # indicate ack sent from receiver
#                 loraStatusAckMsg.SetRepeater(False)  # indicate this ack doesn't come from repeater
#                 loraStatusAckMsg.GenerateRSCode()
#                 return {"Data": loraStatusAckMsg.GetByteArray(), "MessageID": loraStatusAckMsg.GetMD5Hash()}
#         return None