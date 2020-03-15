__author__ = 'henla464'

from datamodel.datamodel import *
from databaselib.db import DB
from databaselib.datamapping import DataMapping
from datetime import timedelta, datetime
#from settings.settings import SettingsClass
import time


class DatabaseHelper:
    db = None

    @classmethod
    def init(cls):
        if cls.db == None:
            cls.db = DB("WiRoc.db", DataMapping())

    @classmethod
    def reInit(cls):
        cls.db = DB("WiRoc.db", DataMapping())

    @classmethod
    def ensure_tables_created(cls):
        logging.debug("DatabaseHelper::ensure_tables_created()")
        cls.init()
        db = cls.db
        table = SettingData()
        db.ensure_table_created(table)
        table = ChannelData()
        db.ensure_table_created(table)
        table = MessageBoxData()
        db.ensure_table_created(table)
        table = MessageBoxArchiveData()
        db.ensure_table_created(table)
        table = SubscriberData()
        db.ensure_table_created(table)
        table = MessageTypeData()
        db.ensure_table_created(table)
        table = TransformData()
        db.ensure_table_created(table)
        table = SubscriptionData()
        db.ensure_table_created(table)
        table = MessageSubscriptionData()
        db.ensure_table_created(table)
        table = MessageSubscriptionArchiveData()
        db.ensure_table_created(table)
        table = InputAdapterInstances()
        db.ensure_table_created(table)
        table = BlenoPunchData()
        db.ensure_table_created(table)
        table = TestPunchData()
        db.ensure_table_created(table)
        table = RepeaterMessageBoxData()
        db.ensure_table_created(table)
        table = RepeaterMessageBoxArchiveData()
        db.ensure_table_created(table)
        table = MessageStatsData()
        db.ensure_table_created(table)

    @classmethod
    def drop_all_tables(cls):
        logging.debug("DatabaseHelper::drop_all_tables()")
        cls.init()
        db = cls.db
        table = SettingData()
        db.drop_table(table)
        table = ChannelData()
        db.drop_table(table)
        table = MessageBoxData()
        db.drop_table(table)
        table = MessageBoxArchiveData()
        db.drop_table(table)
        table = SubscriberData()
        db.drop_table(table)
        table = MessageTypeData()
        db.drop_table(table)
        table = TransformData()
        db.drop_table(table)
        table = SubscriptionData()
        db.drop_table(table)
        table = MessageSubscriptionData()
        db.drop_table(table)
        table = MessageSubscriptionArchiveData()
        db.drop_table(table)
        table = InputAdapterInstances()
        db.drop_table(table)
        table = BlenoPunchData()
        db.drop_table(table)
        table = TestPunchData()
        db.drop_table(table)
        table = RepeaterMessageBoxData()
        db.drop_table(table)
        table = RepeaterMessageBoxArchiveData()
        db.drop_table(table)

    @classmethod
    def truncate_setup_tables(cls):
        logging.debug("DatabaseHelper::truncate_setup_tables()")
        cls.init()
        db = cls.db
        db.execute_SQL("DELETE FROM SubscriptionData")
        db.execute_SQL("DELETE FROM TransformData")
        db.execute_SQL("DELETE FROM InputAdapterInstances")
        db.execute_SQL("DELETE FROM SubscriberData")
        db.execute_SQL("DELETE FROM MessageTypeData")
        db.execute_SQL("DELETE FROM MessageSubscriptionData")

    @classmethod
    def delete_punches(cls):
        logging.debug("DatabaseHelper::delete_punches()")
        cls.init()
        db = cls.db
        db.execute_SQL("DELETE FROM BlenoPunchData")
        db.execute_SQL("DELETE FROM MessageSubscriptionArchiveData")
        db.execute_SQL("DELETE FROM MessageSubscriptionData")
        db.execute_SQL("DELETE FROM MessageBoxArchiveData")
        db.execute_SQL("DELETE FROM MessageBoxData")
        db.execute_SQL("DELETE FROM TestPunchData")
        db.execute_SQL("DELETE FROM RepeaterMessageBoxData")
        db.execute_SQL("DELETE FROM RepeaterMessageBoxArchiveData")

#Settings
    @classmethod
    def save_setting(cls, settingData):
        cls.init()
        sd = cls.get_setting_by_key(settingData.Key)
        if sd is None:
            sd = cls.db.save_table_object(settingData, True)
        else:
            sd.Value = settingData.Value
            sd = cls.db.save_table_object(sd, True)
        return sd

    @classmethod
    def get_setting(cls, id):
        cls.init()
        sd = cls.db.get_table_object(SettingData, str(id))
        return sd

    @classmethod
    def get_settings(cls):
        cls.init()
        rows = cls.db.get_table_objects(SettingData)
        return rows

    @classmethod
    def get_setting_by_key(cls, key):
        cls.init()
        row_list = cls.db.get_table_objects_by_SQL(SettingData, "SELECT * FROM SettingData WHERE Key = '" + key + "'")
        if len(row_list) == 0:
            return None
        return row_list[0]

#Subscriber
    @classmethod
    def save_subscriber(cls, subscriberData):
        cls.init()
        rows = cls.db.get_table_objects_by_SQL(SubscriberData, "SELECT * FROM SubscriberData WHERE TypeName = '" +
                                    subscriberData.TypeName + "' and InstanceName = '" +
                                    subscriberData.InstanceName + "'")
        if len(rows) == 0:
            return cls.db.save_table_object(subscriberData, False)
        else:
            #nothing to update
            return rows[0].id

    @classmethod
    def get_subscribers(cls):
        cls.init()
        rows = cls.db.get_table_objects_by_SQL(SubscriberView, "SELECT "
            "SubscriberData.id, SubscriberData.TypeName, SubscriberData.InstanceName, "
            "SubscriptionData.Enabled, MsgIn.Name MessageInName, MsgIn.MessageSubTypeName MessageInSubTypeName, "
            "MsgOut.Name MessageOutName, MsgOut.MessageSubTypeName MessageOutSubTypeName, "
            "TransformData.Enabled as TransformEnabled, "
            "TransformData.Name as TransformName "
            "from SubscriptionData JOIN SubscriberData "
            "ON SubscriptionData.SubscriberId = SubscriberData.Id "
            "JOIN TransformData ON TransformData.Id = SubscriptionData.TransformId "
            "JOIN MessageTypeData MsgIn on MsgIn.Id = TransformData.InputMessageTypeId "
            "JOIN MessageTypeData MsgOut on MsgOut.Id = TransformData.OutputMessageTypeId")
        return rows

    @classmethod
    def get_subscriber_by_subscription_id(cls, subscriptionId):
        cls.init()
        rows = cls.db.get_table_objects_by_SQL(SubscriberView, "SELECT "
            "SubscriberData.id, SubscriberData.TypeName, SubscriberData.InstanceName, "
            "SubscriptionData.Enabled, MsgIn.Name MessageInName, MsgIn.MessageSubTypeName MessageInSubTypeName, "
            "MsgOut.Name MessageOutName, MsgOut.MessageSubTypeName MessageOutSubTypeName, "
            "TransformData.Enabled as TransformEnabled, "
            "TransformData.Name as TransformName "
            "from SubscriptionData JOIN SubscriberData "
            "ON SubscriptionData.SubscriberId = SubscriberData.Id "
            "JOIN TransformData ON TransformData.Id = SubscriptionData.TransformId "
            "JOIN MessageTypeData MsgIn on MsgIn.Id = TransformData.InputMessageTypeId "
            "JOIN MessageTypeData MsgOut on MsgOut.Id = TransformData.OutputMessageTypeId "
            "WHERE SubscriptionData.id = %s" % subscriptionId)
        return rows

#MessageTypes
    @classmethod
    def get_message_type(cls, messageTypeName, messageSubTypeName):
        cls.init()
        sql = "SELECT * FROM MessageTypeData WHERE Name = ? AND MessageSubTypeName = ?"
        rows = cls.db.get_table_objects_by_SQL(MessageTypeData, sql, (messageTypeName, messageSubTypeName))
        if len(rows) >= 1:
            return rows[0]
        return None

    @classmethod
    def save_message_type(cls, messageTypeData):
        cls.init()
        sql = "SELECT * FROM MessageTypeData WHERE Name = ? AND MessageSubTypeName = ?"
        rows = cls.db.get_table_objects_by_SQL(MessageTypeData, sql, (messageTypeData.Name, messageTypeData.MessageSubTypeName))
        if len(rows) == 0:
            return cls.db.save_table_object(messageTypeData, False)
        else:
            # nothing to update
            return rows[0].id

#Transforms

    @classmethod
    def save_transform(cls, transformData):
        cls.init()
        rows = cls.db.get_table_objects_by_SQL(TransformData, "SELECT * FROM TransformData WHERE Name = '" +
                                           transformData.Name + "'")
        if len(rows) > 0:
            transformData.id = rows[0].id
        return cls.db.save_table_object(transformData, False)

    @classmethod
    def set_transform_enabled(cls, enabled, transformName):
        cls.init()
        dbValue = DataMapping.get_database_value(enabled)
        sql = ("UPDATE TransformData SET Enabled = " + str(dbValue) + " " +
               "WHERE TransformData.Name = '" + transformName + "'")
        logging.debug(sql)
        cls.db.execute_SQL(sql)

#Subscriptions
    @classmethod
    def save_subscription(cls, subscriptionData):
        cls.init()
        rows = cls.db.get_table_objects_by_SQL(SubscriptionData, ("SELECT * FROM SubscriptionData WHERE "
                                           "SubscriberId = " + str(subscriptionData.SubscriberId) +
                                           " and TransformId = " + str(subscriptionData.TransformId)))
        if len(rows) > 0:
            subscriptionData.id = rows[0].id
        return cls.db.save_table_object(subscriptionData, False)

    @classmethod
    def get_subscriptions_by_input_message_type_id(cls, messageTypeId):
        cls.init()
        sql = ("SELECT SubscriptionData.* FROM TransformData JOIN SubscriptionData "
               "ON TransformData.id = SubscriptionData.TransformId "
               "WHERE TransformData.Enabled = 1 AND SubscriptionData.Enabled = 1 AND "
               "InputMessageTypeID = " + str(messageTypeId))
        rows = cls.db.get_table_objects_by_SQL(SubscriptionData, sql)
        return rows

    @classmethod
    def get_subscription_view_by_input_message_type_id(cls, messageTypeId):
        cls.init()
        sql = ("SELECT SubscriptionData.*, TransformData.Name as TransformName, SubscriberData.TypeName as SubscriberTypeName "
               "FROM TransformData JOIN SubscriptionData ON TransformData.id = SubscriptionData.TransformId "
               "JOIN SubscriberData ON SubscriberData.id = SubscriptionData.SubscriberId "
               "WHERE TransformData.Enabled = 1 AND SubscriptionData.Enabled = 1 AND "
               "InputMessageTypeID = " + str(messageTypeId))
        rows = cls.db.get_table_objects_by_SQL(SubscriptionViewData, sql)
        return rows

    @classmethod
    def update_subscriptions(cls, enabled, deleteAfterSent, subscriberTypeName):
        cls.init()
        sql = ("UPDATE SubscriptionData SET Enabled = " + str(1 if enabled else 0) + ", "
               "DeleteAfterSent = " + str(1 if deleteAfterSent else 0) + " WHERE SubscriberId IN "
               "(SELECT id from SubscriberData WHERE SubscriberData.TypeName = '" + str(subscriberTypeName) + "')")
        cls.db.execute_SQL(sql)

    @classmethod
    def update_subscription(cls, enabled, deleteAfterSent, subscriberTypeName, transformName):
        cls.init()
        sql = ("UPDATE SubscriptionData SET Enabled = " + str(1 if enabled else 0) + ", "
               "DeleteAfterSent = " + str(1 if deleteAfterSent else 0) + " WHERE SubscriberId IN "
               "(SELECT id from SubscriberData WHERE SubscriberData.TypeName = '" + str(subscriberTypeName) + "') "
               "AND TransformId IN "
                "(SELECT id from TransformData WHERE TransformData.Name = '" + str(transformName) + "') ")
        cls.db.execute_SQL(sql)

#MessageSubscriptions
    @classmethod
    def get_no_of_message_subscriptions_by_message_box_id(cls, msgBoxId):
        cls.init()
        sql = "SELECT count(*) FROM MessageSubscriptionData WHERE MessageBoxId = %s" %(msgBoxId)
        no = cls.db.get_scalar_by_SQL(sql)
        return no

    @classmethod
    def update_messageid(cls, subscriptionId, messageID):
        cls.init()
        sql = "UPDATE MessageSubscriptionData SET MessageID = ? WHERE id = ?"
        cls.db.execute_SQL(sql,(messageID, subscriptionId))

    @classmethod
    def save_message_subscription(cls, messageSubscription):
        cls.init()
        cls.db.save_table_object(messageSubscription, False)

    @classmethod
    def archive_message_subscription_view_after_sent(cls, messageSubscriptionView):
        cls.init()
        msa = MessageSubscriptionArchiveData()
        msa.OrigId = messageSubscriptionView.id
        msa.MessageID = messageSubscriptionView.MessageID
        msa.SentDate = datetime.now()
        msa.NoOfSendTries = messageSubscriptionView.NoOfSendTries + 1
        msa.FindAdapterTryDate = messageSubscriptionView.FindAdapterTryDate
        msa.FindAdapterTries = messageSubscriptionView.FindAdapterTries
        msa.SendFailedDate = messageSubscriptionView.SendFailedDate
        msa.AckReceivedDate = messageSubscriptionView.AckReceivedDate
        msa.Delay = messageSubscriptionView.Delay
        msa.RetryDelay = messageSubscriptionView.RetryDelay
        msa.FindAdapterRetryDelay = messageSubscriptionView.FindAdapterRetryDelay
        msa.MessageBoxId = messageSubscriptionView.MessageBoxId
        msa.SubscriptionId = messageSubscriptionView.SubscriptionId
        msa.SubscriberTypeName = messageSubscriptionView.SubscriberTypeName
        msa.TransformName = messageSubscriptionView.TransformName
        cls.db.save_table_object(msa, False)
        cls.db.delete_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        remainingMsgSub = cls.get_no_of_message_subscriptions_by_message_box_id(messageSubscriptionView.MessageBoxId)
        if remainingMsgSub == 0:
            cls.archive_message_box(messageSubscriptionView.MessageBoxId)

    @classmethod
    def archive_message_subscription_view_not_sent(cls, messageSubscriptionView):
        cls.init()
        msa = MessageSubscriptionArchiveData()
        msa.OrigId = messageSubscriptionView.id
        msa.MessageID = messageSubscriptionView.MessageID
        msa.SentDate = messageSubscriptionView.SentDate
        msa.SendFailedDate = messageSubscriptionView.SendFailedDate
        msa.FindAdapterTryDate = messageSubscriptionView.FindAdapterTryDate
        msa.FindAdapterTries = messageSubscriptionView.FindAdapterTries
        msa.NoOfSendTries = messageSubscriptionView.NoOfSendTries
        msa.AckReceivedDate = messageSubscriptionView.AckReceivedDate
        msa.Delay = messageSubscriptionView.Delay
        msa.RetryDelay = messageSubscriptionView.RetryDelay
        msa.FindAdapterRetryDelay = messageSubscriptionView.FindAdapterRetryDelay
        msa.MessageBoxId = messageSubscriptionView.MessageBoxId
        msa.SubscriptionId = messageSubscriptionView.SubscriptionId
        msa.SubscriberTypeName = messageSubscriptionView.SubscriberTypeName
        msa.TransformName = messageSubscriptionView.TransformName
        cls.db.save_table_object(msa, False)
        cls.db.delete_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        remainingMsgSub = cls.get_no_of_message_subscriptions_by_message_box_id(messageSubscriptionView.MessageBoxId)
        if remainingMsgSub == 0:
            cls.archive_message_box(messageSubscriptionView.MessageBoxId)

    @classmethod
    def increment_send_tries_and_set_sent_date(cls, messageSubscriptionView, retryDelay):
        cls.init()
        msa = cls.db.get_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        if msa is None:
            return None
        msa.SentDate = datetime.now()
        msa.NoOfSendTries = msa.NoOfSendTries + 1
        msa.FindAdapterTryDate = None
        msa.FindAdapterTries = 0
        # this method is called for messages that wait for an ack before being archived
        # we set a RetryDelay below to block it from being sent again until it timed out so no need to keep
        # the FetchedForSending block anymore.
        msa.FetchedForSending = None
        msa.RetryDelay = retryDelay
        msa.FindAdapterRetryDelay = 0
        cls.db.save_table_object(msa, False)

    @classmethod
    def clear_fetched_for_sending(cls, messageSubscriptionView):
        cls.init()
        msa = cls.db.get_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        msa.FetchedForSending = None
        cls.db.save_table_object(msa, False)

    @classmethod
    def increment_send_tries_and_set_send_failed_date(cls, messageSubscriptionView, retryDelay):
        cls.init()
        msa = cls.db.get_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        msa.SendFailedDate = datetime.now()
        msa.NoOfSendTries = msa.NoOfSendTries + 1
        msa.FindAdapterTryDate = None
        msa.FindAdapterTries = 0
        msa.FetchedForSending = None
        msa.RetryDelay = retryDelay
        msa.FindAdapterRetryDelay = 0
        cls.db.save_table_object(msa, False)

    @classmethod
    def increment_find_adapter_tries_and_set_find_adapter_try_date(cls, messageSubscriptionView, retryDelay):
        cls.init()
        msa = cls.db.get_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        msa.FindAdapterTryDate = datetime.now()
        msa.FindAdapterTries = msa.FindAdapterTries + 1
        msa.FindAdpterRetryDelay = retryDelay
        cls.db.save_table_object(msa, False)



    @classmethod
    def set_ack_received_from_receiver_on_repeater_lora_ack_message_subscription(cls, messageID):
        cls.init()
        sql = ("SELECT MessageSubscriptionData.* FROM MessageSubscriptionData JOIN SubscriptionData "
               "ON SubscriptionData.id = MessageSubscriptionData.SubscriptionId "
               "JOIN TransformData ON SubscriptionData.TransformId = TransformData.id "
               "WHERE TransformData.Name = 'RepeaterToLoraAckTransform' AND "
               "MessageSubscriptionData.MessageID = ? ORDER BY SentDate desc LIMIT 1")
        rows = cls.db.get_table_objects_by_SQL(MessageSubscriptionData, sql, (messageID,))

        if len(rows) > 0:
            msd = rows[0]
            msd.AckReceivedFromReceiver = True
            logging.debug("DatabaseHelper::set_ack_received_from_receiver_on_repeater_lora_ack_message_subscription(): The ack sent from repeater to sender should indicate the message has been received by receiver")
            cls.db.save_table_object(msd, False)

    @classmethod
    def archive_lora_ack_message_subscription(cls, messageID):
        cls.init()
        sql = ("SELECT MessageSubscriptionData.* FROM MessageSubscriptionData JOIN SubscriptionData "
                "ON SubscriptionData.id = MessageSubscriptionData.SubscriptionId "
                "JOIN TransformData ON SubscriptionData.TransformId = TransformData.id "
                "WHERE TransformData.Name = 'LoraSIMessageToLoraAckTransform' AND "
                "hex(MessageSubscriptionData.MessageID) like '__' || hex(?)")
        rows = cls.db.get_table_objects_by_SQL(MessageSubscriptionData, sql, (messageID[1:], ))

        if len(rows) > 0:
            now = datetime.now()
            msd = rows[0]
            msa = MessageSubscriptionArchiveData()
            msa.OrigId = msd.id
            msa.MessageID = msd.MessageID
            msa.SentDate = msd.SentDate
            msa.SendFailedDate = msd.SendFailedDate
            msa.FindAdapterTryDate = msd.FindAdapterTryDate
            msa.FindAdapterTries = msd.FindAdapterTries
            msa.NoOfSendTries = msd.NoOfSendTries
            msa.Delay = msd.Delay
            msa.RetryDelay = msd.RetryDelay
            msa.FindAdapterRetryDelay = msd.FindAdapterRetryDelay
            msa.AckReceivedDate = now
            msa.MessageBoxId = msd.MessageBoxId
            msa.SubscriptionId = msd.SubscriptionId
            subscriberView = DatabaseHelper.get_subscriber_by_subscription_id(msd.SubscriptionId)
            if len(subscriberView) > 0:
                msa.SubscriberTypeName = subscriberView[0].TypeName
                msa.TransformName = subscriberView[0].TransformName
            logging.debug("DatabaseHelper::archive_lora_ack_message_subscription(): Archive ack message because it was already sent when SIMessage was received")
            cls.db.save_table_object(msa, False)
            cls.db.delete_table_object(MessageSubscriptionData, msd.id)
            remainingMsgSub = cls.get_no_of_message_subscriptions_by_message_box_id(msd.MessageBoxId)
            if remainingMsgSub == 0:
                cls.archive_message_box(msd.MessageBoxId)


    @classmethod
    def archive_repeater_lora_message_subscription_after_ack(cls, messageID, rssiValue):
        cls.init()
        sql = ("SELECT MessageSubscriptionData.* FROM MessageSubscriptionData JOIN SubscriptionData "
                "ON SubscriptionData.id = MessageSubscriptionData.SubscriptionId "
                "JOIN TransformData ON SubscriptionData.TransformId = TransformData.id "
                "WHERE (TransformData.Name = 'RepeaterSIMessageToLoraTransform' OR "
                "TransformData.Name = 'SITestTestToLoraTransform') AND "
                "MessageSubscriptionData.MessageID = ? ORDER BY SentDate desc LIMIT 1")
        rows = cls.db.get_table_objects_by_SQL(MessageSubscriptionData, sql, (messageID, ))

        if len(rows) > 0:
            now = datetime.now()
            msd = rows[0]
            msa = MessageSubscriptionArchiveData()
            msa.OrigId = msd.id
            msa.MessageID = msd.MessageID
            msa.SentDate = msd.SentDate
            msa.SendFailedDate = msd.SendFailedDate
            msa.FindAdapterTryDate = msd.FindAdapterTryDate
            msa.FindAdapterTries = msd.FindAdapterTries
            msa.NoOfSendTries = msd.NoOfSendTries
            msa.Delay = msd.Delay
            msa.RetryDelay = msd.RetryDelay
            msa.FindAdapterRetryDelay = msd.FindAdapterRetryDelay
            msa.AckReceivedDate = now
            msa.AckRSSIValue = rssiValue
            msa.MessageBoxId = msd.MessageBoxId
            msa.SubscriptionId = msd.SubscriptionId
            subscriberView = DatabaseHelper.get_subscriber_by_subscription_id(msd.SubscriptionId)
            if len(subscriberView) > 0:
                msa.SubscriberTypeName = subscriberView[0].TypeName
                msa.TransformName = subscriberView[0].TransformName
            logging.debug("DatabaseHelper::archive_repeater_lora_message_subscription_after_ack(): Archive message because it was already received by receiver")
            cls.db.save_table_object(msa, False)
            cls.db.delete_table_object(MessageSubscriptionData, msd.id)
            remainingMsgSub = cls.get_no_of_message_subscriptions_by_message_box_id(msd.MessageBoxId)
            if remainingMsgSub == 0:
                cls.archive_message_box(msd.MessageBoxId)

    @classmethod
    def archive_message_subscription_after_ack(cls, messageID, ackRSSIValue):
        cls.init()
        sixtySecondsAgo = datetime.now() - timedelta(seconds=60)
        sql = ("SELECT MessageSubscriptionData.* FROM MessageSubscriptionData WHERE "
                                       "MessageID = ? AND SentDate > ? "
                                        "ORDER BY SentDate desc LIMIT 1")
        rows = cls.db.get_table_objects_by_SQL(MessageSubscriptionData, sql, (messageID, sixtySecondsAgo))

        if len(rows) > 0:
            now = datetime.now()
            msd = rows[0]
            msa = MessageSubscriptionArchiveData()
            msa.OrigId = msd.id
            msa.MessageID = msd.MessageID
            msa.SentDate = msd.SentDate
            msa.SendFailedDate = msd.SendFailedDate
            msa.FindAdapterTryDate = msd.FindAdapterTryDate
            msa.FindAdapterTries = msd.FindAdapterTries
            msa.NoOfSendTries = msd.NoOfSendTries
            msa.AckReceivedDate = now
            msa.Delay = msd.Delay
            msa.RetryDelay = msd.RetryDelay
            msa.FindAdapterRetryDelay = msd.FindAdapterRetryDelay
            msa.MessageBoxId = msd.MessageBoxId
            msa.AckRSSIValue = ackRSSIValue
            msa.SubscriptionId = msd.SubscriptionId
            subscriberView = DatabaseHelper.get_subscriber_by_subscription_id(msd.SubscriptionId)
            if len(subscriberView) > 0:
                msa.SubscriberTypeName = subscriberView[0].TypeName
                msa.TransformName = subscriberView[0].TransformName
            logging.debug("DatabaseHelper::archive_message_subscription_after_ack(): Archive message")
            cls.db.save_table_object(msa, False)
            cls.db.delete_table_object(MessageSubscriptionData, msd.id)
            remainingMsgSub = cls.get_no_of_message_subscriptions_by_message_box_id(msd.MessageBoxId)
            if remainingMsgSub == 0:
                cls.archive_message_box(msd.MessageBoxId)

    @classmethod
    def repeater_message_acked(cls, messageID, ackRSSIValue):
        cls.init()
        sql = ("SELECT RepeaterMessageBoxData.* FROM RepeaterMessageBoxData WHERE "
               "MessageID = ?")
        rows = cls.db.get_table_objects_by_SQL(RepeaterMessageBoxData, sql, (messageID, ))
        if len(rows) > 0:
            msgToUpdate = rows[0]
            msgToUpdate.Acked = True
            msgToUpdate.NoOfTimesAckSeen = msgToUpdate.NoOfTimesAckSeen + 1
            msgToUpdate.AckRSSIValue = ackRSSIValue
            if msgToUpdate.AckedTime is None:
                msgToUpdate.AckedTime = datetime.now()
            logging.debug("DatabaseHelper::repeater_message_acked(): Marking RepeaterMessageBoxData message as acked")
            return cls.db.save_table_object(msgToUpdate, False)

    @classmethod
    def archive_repeater_message_after_added_to_message_box(cls, repeaterMessageBoxId, messageBoxId):
        cls.init()
        repeaterMessageBox = cls.db.get_table_object(RepeaterMessageBoxData, repeaterMessageBoxId)
        msa = RepeaterMessageBoxArchiveData()
        msa.OrigId = repeaterMessageBox.id
        msa.MessageData = repeaterMessageBox.MessageData
        msa.MessageTypeName = repeaterMessageBox.MessageTypeName
        msa.PowerCycleCreated = repeaterMessageBox.PowerCycleCreated
        msa.InstanceName = repeaterMessageBox.InstanceName
        msa.MessageSubTypeName = repeaterMessageBox.MessageSubTypeName
        msa.ChecksumOK = repeaterMessageBox.ChecksumOK
        msa.MessageSource = repeaterMessageBox.MessageSource
        msa.SICardNumber = repeaterMessageBox.SICardNumber
        msa.SportIdentHour = repeaterMessageBox.SportIdentHour
        msa.SportIdentMinute = repeaterMessageBox.SportIdentMinute
        msa.SportIdentSecond = repeaterMessageBox.SportIdentSecond
        msa.MessageID = repeaterMessageBox.MessageID
        msa.AckRequested = repeaterMessageBox.AckRequested
        msa.RepeaterRequested = repeaterMessageBox.RepeaterRequested
        msa.NoOfTimesSeen = repeaterMessageBox.NoOfTimesSeen
        msa.NoOfTimesAckSeen = repeaterMessageBox.NoOfTimesAckSeen
        msa.Acked = repeaterMessageBox.Acked
        msa.AckedTime = repeaterMessageBox.AckedTime
        msa.MessageBoxId = repeaterMessageBox.MessageBoxId  #todo: set messageBoxId ?
        msa.AddedToMessageBoxTime = datetime.now()
        msa.RSSIValue = repeaterMessageBox.RSSIValue
        msa.AckRSSIValue = repeaterMessageBox.AckRSSIValue
        msa.LastSeenTime = repeaterMessageBox.LastSeenTime
        msa.OrigCreatedDate = repeaterMessageBox.CreatedDate
        cls.db.save_table_object(msa, False)
        cls.db.delete_table_object(RepeaterMessageBoxData, repeaterMessageBox.id)

#MessageSubscriptionView
    @classmethod
    def get_last_message_subscription_view_that_was_sent_to_lora(cls):
        sql = ("SELECT MessageSubscriptionData.id, "
               "MessageSubscriptionData.MessageID, "
               "MessageSubscriptionData.AckReceivedFromReceiver, "
               "MessageSubscriptionData.MessageNumber, "
               "MessageSubscriptionData.SentDate, "
               "MessageSubscriptionData.SendFailedDate, "
               "MessageSubscriptionData.FindAdapterTryDate, "
               "MessageSubscriptionData.FindAdapterTries, "
               "MessageSubscriptionData.NoOfSendTries, "
               "MessageSubscriptionData.AckReceivedDate, "
               "MessageSubscriptionData.Delay, "
               "MessageSubscriptionData.RetryDelay, "
               "MessageSubscriptionData.FindAdapterRetryDelay, "
               "MessageSubscriptionData.MessageBoxId, "
               "MessageSubscriptionData.SubscriptionId, "
               "MessageSubscriptionData.FetchedForSending, "
               "SubscriptionData.DeleteAfterSent, "
               "SubscriptionData.Enabled, "
               "SubscriptionData.SubscriberId, "
               "SubscriberData.TypeName as SubscriberTypeName, "
               "SubscriberData.InstanceName as SubscriberInstanceName, "
               "TransformData.Name as TransformName, "
               "MessageBoxData.MessageData,"
               "MessageBoxData.CreatedDate as CreatedDate "
               "FROM TransformData JOIN SubscriptionData "
               "ON TransformData.id = SubscriptionData.TransformId "
               "JOIN SubscriberData ON SubscriberData.id = SubscriptionData.SubscriberId "
               "JOIN MessageSubscriptionData ON MessageSubscriptionData.SubscriptionId = SubscriptionData.id "
               "JOIN MessageBoxData ON MessageBoxData.id = MessageSubscriptionData.MessageBoxId "
               "WHERE SubscriptionData.Enabled IS NOT NULL AND SubscriptionData.Enabled = 1 AND "
               "TransformData.Enabled IS NOT NULL AND TransformData.Enabled = 1 AND "
               "SubscriberData.TypeName = 'LORA' AND "
               "MessageSubscriptionData.SentDate IS NOT NULL "
               "ORDER BY MessageBoxData.CreatedDate asc, "
               "MessageSubscriptionData.SentDate asc")
        messageSubscriptions = cls.db.get_table_objects_by_SQL(MessageSubscriptionView, sql)
        now = datetime.now()
        for messageSubscription in messageSubscriptions:
            if messageSubscription.SentDate != None and messageSubscription.SentDate < now < messageSubscription.SentDate + timedelta(
                    microseconds=messageSubscription.RetryDelay):
                    # has been sent, not yet passed the retry delay (may still be waiting for ack)
                return messageSubscription

    @classmethod
    def get_message_subscriptions_view_to_send(cls, maxRetries):
        sql = ("SELECT count(MessageSubscriptionData.id) FROM MessageSubscriptionData")
        cls.init()
        cnt = cls.db.get_scalar_by_SQL(sql)
        if cnt > 0:

            sql = ("SELECT MessageSubscriptionData.id, "
                   "MessageSubscriptionData.MessageID, "
                   "MessageSubscriptionData.AckReceivedFromReceiver, "
                   "MessageSubscriptionData.MessageNumber, "
                   "MessageSubscriptionData.SentDate, "
                   "MessageSubscriptionData.SendFailedDate, "
                   "MessageSubscriptionData.FindAdapterTryDate, "
                   "MessageSubscriptionData.FindAdapterTries, "
                   "MessageSubscriptionData.NoOfSendTries, "
                   "MessageSubscriptionData.AckReceivedDate, "
                   "MessageSubscriptionData.Delay, "
                   "MessageSubscriptionData.RetryDelay, "
                   "MessageSubscriptionData.FindAdapterRetryDelay, "
                   "MessageSubscriptionData.MessageBoxId, "
                   "MessageSubscriptionData.SubscriptionId, "
                   "MessageSubscriptionData.FetchedForSending, "
                   "SubscriptionData.DeleteAfterSent, "
                   "SubscriptionData.Enabled, "
                   "SubscriptionData.SubscriberId, "
                   "SubscriberData.TypeName as SubscriberTypeName, "
                   "SubscriberData.InstanceName as SubscriberInstanceName, "
                   "TransformData.Name as TransformName, "
                   "MessageBoxData.MessageData,"
                   "MessageBoxData.CreatedDate as CreatedDate "
                   "FROM TransformData JOIN SubscriptionData "
                   "ON TransformData.id = SubscriptionData.TransformId "
                   "JOIN SubscriberData ON SubscriberData.id = SubscriptionData.SubscriberId "
                   "JOIN MessageSubscriptionData ON MessageSubscriptionData.SubscriptionId = SubscriptionData.id "
                   "JOIN MessageBoxData ON MessageBoxData.id = MessageSubscriptionData.MessageBoxId "
                   "WHERE SubscriptionData.Enabled IS NOT NULL AND SubscriptionData.Enabled = 1 AND "
                   "TransformData.Enabled IS NOT NULL AND TransformData.Enabled = 1 "
                   "ORDER BY MessageBoxData.CreatedDate asc, "
                   "MessageSubscriptionData.SentDate asc")
            messageSubscriptions = cls.db.get_table_objects_by_SQL(MessageSubscriptionView, sql)

            messageSubscriptionToSend = None
            adapterTypesAlreadyHandlingMessages = set()
            for messageSubscription in messageSubscriptions:
                if messageSubscription.SubscriberTypeName in adapterTypesAlreadyHandlingMessages:
                    # a message has already been sent to this adapter or is waiting to be sent (been delayed)
                    # skip any following messages to the same adapter
                    continue

                now = datetime.now()
                if messageSubscription.FetchedForSending is not None and messageSubscription.FetchedForSending < now < messageSubscription.FetchedForSending + timedelta(
                        seconds=12):
                    # recently fetched and is being sent by another thread
                    adapterTypesAlreadyHandlingMessages.add(messageSubscription.SubscriberTypeName)
                    continue

                if  messageSubscription.CreatedDate < now < messageSubscription.CreatedDate + timedelta(microseconds=messageSubscription.Delay):
                    # Should have an initial delay that has not passed yet
                    adapterTypesAlreadyHandlingMessages.add(messageSubscription.SubscriberTypeName)
                    continue

                if messageSubscription.SentDate != None and messageSubscription.SentDate < now < messageSubscription.SentDate + timedelta(microseconds=messageSubscription.RetryDelay):
                    # has been sent, not yet passed the retry delay (may still be waiting for ack)
                    adapterTypesAlreadyHandlingMessages.add(messageSubscription.SubscriberTypeName)
                    continue

                if messageSubscription.FindAdapterTryDate != None and messageSubscription.FindAdapterTryDate < now < messageSubscription.FindAdapterTryDate + timedelta(microseconds=messageSubscription.FindAdapterRetryDelay):
                    # should wait longer before trying to find adapter again
                    adapterTypesAlreadyHandlingMessages.add(messageSubscription.SubscriberTypeName)
                    continue

                if messageSubscription.NoOfSendTries >= maxRetries:
                    # Message may have been sent, noOfSendTries icremented, passed the retry time
                    # BUT has not yet been archived. Just skip/should be ignored
                    continue

                if messageSubscription.FindAdapterTries >= maxRetries:
                    # Ignore messages exceeding find adapter tries. Has not yet been archived.
                    continue

                messageSubscriptionToSend = messageSubscription
                break

            if messageSubscriptionToSend != None:
                sql = "UPDATE MessageSubscriptionData SET FetchedForSending = ? WHERE Id = ?"
                cls.db.execute_SQL(sql, (datetime.now(), messageSubscriptionToSend.id))
                return cnt, messageSubscriptionToSend
        return cnt, None

    @classmethod
    def get_message_subscriptions_view_to_archive(cls, maxRetries, limit=100):
        sql = ("SELECT count(MessageSubscriptionData.id) FROM MessageSubscriptionData ")
        cls.init()
        cnt = cls.db.get_scalar_by_SQL(sql)
        if cnt > 0:

            sql = ("SELECT MessageSubscriptionData.id, "
                   "MessageSubscriptionData.MessageID, "
                   "MessageSubscriptionData.AckReceivedFromReceiver, "
                   "MessageSubscriptionData.MessageNumber, "
                   "MessageSubscriptionData.SentDate, "
                   "MessageSubscriptionData.SendFailedDate, "
                   "MessageSubscriptionData.FindAdapterTryDate, "
                   "MessageSubscriptionData.FindAdapterTries, "
                   "MessageSubscriptionData.NoOfSendTries, "
                   "MessageSubscriptionData.Delay, "
                   "MessageSubscriptionData.RetryDelay, "
                   "MessageSubscriptionData.FindAdapterRetryDelay, "
                   "MessageSubscriptionData.AckReceivedDate, "
                   "MessageSubscriptionData.MessageBoxId, "
                   "MessageSubscriptionData.SubscriptionId, "
                   "MessageSubscriptionData.FetchedForSending, "
                   "SubscriptionData.DeleteAfterSent, "
                   "SubscriptionData.Enabled, "
                   "SubscriptionData.SubscriberId, "
                   "SubscriberData.TypeName as SubscriberTypeName, "
                   "SubscriberData.InstanceName as SubscriberInstanceName, "
                   "TransformData.Name as TransformName, "
                   "MessageBoxData.MessageData, "
                   "MessageBoxData.CreatedDate "
                   "FROM TransformData JOIN SubscriptionData "
                   "ON TransformData.id = SubscriptionData.TransformId "
                   "JOIN SubscriberData ON SubscriberData.id = SubscriptionData.SubscriberId "
                   "JOIN MessageSubscriptionData ON MessageSubscriptionData.SubscriptionId = SubscriptionData.id "
                   "JOIN MessageBoxData ON MessageBoxData.id = MessageSubscriptionData.MessageBoxId "
                   "WHERE SubscriptionData.Enabled IS NOT NULL AND SubscriptionData.Enabled = 1 AND "
                   "TransformData.Enabled IS NOT NULL AND TransformData.Enabled = 1 AND "
                   "(MessageSubscriptionData.NoOfSendTries >= %s or MessageSubscriptionData.FindAdapterTries >= %s) "
                   "ORDER BY MessageBoxData.CreatedDate desc "
                   "LIMIT %s") % (maxRetries, maxRetries, limit)
            return cls.db.get_table_objects_by_SQL(MessageSubscriptionView, sql)
        return []

    @classmethod
    def change_future_sent_dates(cls):
        cls.init()
        sql = ("SELECT * FROM MessageSubscriptionData ORDER BY SentDate desc")
        subs = cls.db.get_table_objects_by_SQL(MessageSubscriptionData, sql)
        now = datetime.now()
        for sub in subs:
            if sub.SentDate > now:
                sub.SentDate = now
                cls.db.save_table_object(sub, False)
                logging.debug('Set future SentDate: ' + str(sub.SentDate) + " to: " + str(now))
            else:
                return

    @classmethod
    def change_future_created_dates(cls):
        cls.init()
        sql = ("SELECT * FROM MessageBoxData ORDER BY CreatedDate desc")
        messageBoxDatas = cls.db.get_table_objects_by_SQL(MessageBoxData, sql)
        now = datetime.now()
        for msg in messageBoxDatas:
            if msg.CreatedDate > now:
                msg.CreatedDate = now
                cls.db.save_table_object(msg, False)
                logging.debug('Set future CreatedDate: ' + str(msg.CreatedDate) + " to: " + str(now))
            else:
                return
#MessageBox
    @classmethod
    def create_message_box_data(cls, messageSource, messageTypeName, messageSubTypeName, instanceName, checksumOK, powerCycle, serialNumber, data, rssiValue):
        mbd = MessageBoxData()
        mbd.MessageData = data
        mbd.MessageTypeName = messageTypeName
        mbd.PowerCycleCreated = powerCycle
        mbd.ChecksumOK = checksumOK
        mbd.InstanceName = instanceName
        mbd.MessageSubTypeName = messageSubTypeName
        mbd.MessageSource = messageSource
        mbd.SIStationSerialNumber = serialNumber
        mbd.RSSIValue = rssiValue

        mbd.SIStationNumber = None
        mbd.SIStationSerialNumber = None
        mbd.LowBattery = None

        siPayloadData = None
        if messageTypeName == "LORA" and messageSubTypeName == "SIMessage":
            loraHeaderSize = LoraRadioMessage.GetHeaderSize()
            siPayloadData = data[loraHeaderSize:]
            loraMessage = LoraRadioMessage()
            loraMessage.AddPayload(data)
            mbd.LowBattery = loraMessage.GetBatteryLowBit()
        elif messageSubTypeName == "SIMessage":
            #source WiRoc, SIStation
            siPayloadData = data

        if siPayloadData != None:
            siMsg = SIMessage()
            siMsg.AddPayload(siPayloadData)
            mbd.SICardNumber = siMsg.GetSICardNumber()
            mbd.SportIdentHour = siMsg.GetHour()
            mbd.SportIdentMinute = siMsg.GetMinute()
            mbd.SportIdentSecond = siMsg.GetSeconds()
            mbd.MemoryAddress = siMsg.GetBackupMemoryAddressAsInt()
            mbd.SIStationNumber = siMsg.GetStationNumber()
        return mbd


    @classmethod
    def save_message_box(cls, messageBoxData):
        # todo: test performance with using fixed sql to insert instead
        cls.init()
        return cls.db.save_table_object(messageBoxData, False)

    @classmethod
    def get_message_box_messages(cls):
        cls.init()
        return cls.db.get_table_objects(MessageBoxData)

    @classmethod
    def archive_message_box(cls, msgBoxId):
        cls.init()
        sql = "INSERT INTO MessageBoxArchiveData (OrigId, MessageData," \
              "PowerCycleCreated, MessageTypeName, InstanceName, MessageSubTypeName, MemoryAddress," \
              "SICardNumber, SIStationSerialNumber, SportIdentHour, SportIdentMinute," \
              "SportIdentSecond, SIStationNumber, LowBattery, ChecksumOK, CreatedDate) SELECT id, MessageData," \
              "PowerCycleCreated, MessageTypeName, InstanceName, MessageSubTypeName, MemoryAddress," \
              "SICardNumber, SIStationSerialNumber, SportIdentHour, SportIdentMinute," \
              "SportIdentSecond, SIStationNumber, LowBattery, ChecksumOK, CreatedDate FROM " \
              "MessageBoxData WHERE Id = %s" % msgBoxId

        cls.db.execute_SQL(sql)
        cls.db.delete_table_object(MessageBoxData, msgBoxId)

    @classmethod
    def archive_message_box_without_subscriptions(cls):
        cls.init()
        sql = "INSERT INTO MessageBoxArchiveData (OrigId, MessageData," \
              "PowerCycleCreated, MessageTypeName, InstanceName, MessageSubTypeName, MemoryAddress," \
              "SICardNumber, SIStationSerialNumber, SportIdentHour, SportIdentMinute," \
              "SportIdentSecond, SIStationNumber, LowBattery, ChecksumOK, CreatedDate) SELECT MessageBoxData.id, MessageData," \
              "PowerCycleCreated, MessageTypeName, InstanceName, MessageSubTypeName, MemoryAddress," \
              "SICardNumber, SIStationSerialNumber, SportIdentHour, SportIdentMinute," \
              "SportIdentSecond, SIStationNumber, LowBattery, ChecksumOK, CreatedDate FROM " \
              "MessageBoxData LEFT JOIN MessageSubscriptionData ON MessageBoxData.id = " \
              "MessageSubscriptionData.MessageboxId WHERE MessageSubscriptionData.id is null"
        cls.db.execute_SQL(sql)
        sql = "DELETE FROM MessageBoxData WHERE id in (SELECT MessageBoxData.id FROM " \
              "MessageBoxData LEFT JOIN MessageSubscriptionData ON MessageBoxData.id = " \
              "MessageSubscriptionData.MessageboxId WHERE MessageSubscriptionData.id IS NULL)"
        cls.db.execute_SQL(sql)

#RepeaterMessageBox
    @classmethod
    def create_repeater_message_box_data(cls, messageSource, messageTypeName, messageSubTypeName, instanceName, checksumOK,
                                powerCycle, serialNumber, messageID, data, rssiValue):
        rmbd = RepeaterMessageBoxData()
        rmbd.MessageData = data
        rmbd.MessageTypeName = messageTypeName
        rmbd.PowerCycleCreated = powerCycle
        rmbd.ChecksumOK = checksumOK
        rmbd.InstanceName = instanceName
        rmbd.MessageSubTypeName = messageSubTypeName
        rmbd.MessageSource = messageSource
        rmbd.SIStationSerialNumber = serialNumber
        rmbd.RSSIValue = rssiValue
        rmbd.NoOfTimesSeen = 1
        rmbd.NoOfTimesAckSeen = 0

        rmbd.SIStationNumber = None
        rmbd.SIStationSerialNumber = None
        rmbd.LowBattery = None

        siPayloadData = None
        if messageTypeName == "LORA" and messageSubTypeName == "SIMessage":
            loraHeaderSize = LoraRadioMessage.GetHeaderSize()
            siPayloadData = data[loraHeaderSize:]
            loraMessage = LoraRadioMessage()
            loraMessage.AddPayload(data)
            rmbd.LowBattery = loraMessage.GetBatteryLowBit()
            rmbd.MessageID = messageID
            rmbd.AckRequested = loraMessage.GetAcknowledgementRequested()
            rmbd.RepeaterRequested = loraMessage.GetRepeaterBit()

        if siPayloadData != None:
            siMsg = SIMessage()
            siMsg.AddPayload(siPayloadData)
            rmbd.SICardNumber = siMsg.GetSICardNumber()
            rmbd.SportIdentHour = siMsg.GetHour()
            rmbd.SportIdentMinute = siMsg.GetMinute()
            rmbd.SportIdentSecond = siMsg.GetSeconds()
            rmbd.MemoryAddress = siMsg.GetBackupMemoryAddressAsInt()
            rmbd.SIStationNumber = siMsg.GetStationNumber()

        return rmbd

    @classmethod
    def save_repeater_message_box(cls, repeaterMessageBoxData):
        cls.init()
        msgID = repeaterMessageBoxData.MessageID
        sql = ("SELECT RepeaterMessageBoxData.* FROM RepeaterMessageBoxData WHERE MessageID = ?")
        rows = cls.db.get_table_objects_by_SQL(RepeaterMessageBoxData, sql, (msgID,))
        if len(rows) > 0:
            msgToUpdate = rows[0]
            msgToUpdate.NoOfTimesSeen = msgToUpdate.NoOfTimesSeen + 1
            msgToUpdate.LastSeenTime = datetime.now()
            msgToUpdate.RSSIValue = repeaterMessageBoxData.RSSIValue
            return cls.db.save_table_object(msgToUpdate, False)
        else:
            repeaterMessageBoxData.LastSeenTime = datetime.now()
            return cls.db.save_table_object(repeaterMessageBoxData, False)

    @classmethod
    def archive_old_repeater_message(cls):
        cls.init()
        fiveMinutesAgo = datetime.now() - timedelta(seconds=300)
        sql = ("INSERT INTO RepeaterMessageBoxArchiveData (id, "
               "OrigId, MessageData, MessageTypeName, PowerCycleCreated, "
               "InstanceName, MessageSubTypeName, ChecksumOK, MessageSource, "
               "SICardNumber, SportIdentHour, SportIdentMinute, SportIdentSecond, "
               "MessageID, AckRequested, RepeaterRequested, NoOfTimesSeen, "
               "NoOfTimesAckSeen, Acked, AckedTime, MessageBoxId, RSSIValue, "
               "AckRSSIValue, AddedToMessageBoxTime, LastSeenTime, OrigCreatedDate, "
               "CreatedDate) SELECT NULL, "
               "id as OrigId, MessageData, MessageTypeName, PowerCycleCreated, "
               "InstanceName, MessageSubTypeName, ChecksumOK, MessageSource, "
               "SICardNumber, SportIdentHour, SportIdentMinute, SportIdentSecond, "
               "MessageID, AckRequested, RepeaterRequested, NoOfTimesSeen, "
               "NoOfTimesAckSeen, Acked, AckedTime, MessageBoxId, RSSIValue, "
               "AckRSSIValue, ? as AddedToMessageBoxTime, LastSeenTime, CreatedDate as OrigCreatedDate, "
               "? as CreatedDate "
               "FROM RepeaterMessageBoxData WHERE LastSeenTime < ?")
        cls.db.execute_SQL(sql, (datetime.now(), datetime.now(), fiveMinutesAgo))
        sql = ("DELETE FROM RepeaterMessageBoxData WHERE LastSeenTime < ? ")
        cls.db.execute_SQL(sql, (fiveMinutesAgo,))

    @classmethod
    def get_repeater_message_to_add(cls):
        cls.init()
        repeaterMessages = cls.db.get_table_objects_by_SQL(RepeaterMessageBoxData,
                                                      "SELECT * FROM RepeaterMessageBoxData WHERE "
                                                      "(RepeaterRequested = 1 or NoOfTimesSeen > 1) ORDER BY "
                                                      "SportIdentHour, SportIdentMinute, SportIdentSecond LIMIT 1")
        if len(repeaterMessages) > 0:
            return repeaterMessages[0]
        return None

#InputAdapterInstances
    @classmethod
    def update_input_adapter_instances(cls, inputAdapterObjects):
        cls.init()
        sql = ("UPDATE InputAdapterInstances SET ToBeDeleted = 1")
        cls.db.execute_SQL_no_commit(sql)
        for inputAdapter in inputAdapterObjects:
            sql = ("WITH new (TypeName, InstanceName, ToBeDeleted) AS "
                   "( VALUES('%s', '%s', 0) ) "
                    "INSERT OR REPLACE INTO InputAdapterInstances "
                    "(id, TypeName, InstanceName, ToBeDeleted) "
                    "SELECT old.id, new.TypeName, new.InstanceName, new.ToBeDeleted "
                    "FROM new LEFT JOIN InputAdapterInstances AS old "
                    "ON new.InstanceName = old.InstanceName") % (inputAdapter.GetTypeName(), inputAdapter.GetInstanceName())
            cls.db.execute_SQL_no_commit(sql)
        sql = ("DELETE FROM InputAdapterInstances WHERE ToBeDeleted = 1")
        cls.db.execute_SQL(sql)

    @classmethod
    def get_input_adapter_instances(cls):
        cls.init()
        inputAdapterInstances = cls.db.get_table_objects(InputAdapterInstances)
        return inputAdapterInstances

#BlenoPunchData
    @classmethod
    def save_bleno_punch_data(cls, blenoPunchData):
        cls.init()
        cls.db.save_table_object(blenoPunchData, False)

    @classmethod
    def get_bleno_punches(cls):
        cls.init()
        return cls.db.get_table_objects(BlenoPunchData)

    @classmethod
    def delete_bleno_punch_data(cls, rowId):
        cls.init()
        cls.db.delete_table_object(BlenoPunchData, rowId)

#TestPunchData
    @classmethod
    def add_test_punch(cls, testBatchGuid, SINo, twelveHourTimer, twentyFourHour):
        cls.init()
        testPunch = TestPunchData()
        testPunch.BatchGuid = testBatchGuid
        testPunch.MessageBoxId = None
        testPunch.TwelveHourTimer = twelveHourTimer
        testPunch.TwentyFourHour = twentyFourHour
        testPunch.SICardNumber = SINo
        cls.db.save_table_object(testPunch, False)

    @classmethod
    def delete_other_test_punches(cls, testBatchGuid):
        cls.init()
        cls.db.execute_SQL("DELETE FROM TestPunchData WHERE BatchGuid <> '%s'" % testBatchGuid)
        return None

    @classmethod
    def get_test_punch_to_add(cls):
        cls.init()
        testPunches = cls.db.get_table_objects_by_SQL(TestPunchData, "SELECT * FROM TestPunchData WHERE AddedToMessageBox = 0 ORDER BY TwentyFourHour, TwelveHourTimer, id LIMIT 1")
        if len(testPunches) > 0:
            return testPunches[0]
        return None

    @classmethod
    def set_test_punch_added_to_message_box(cls, messageBoxId, testPunchId):
        cls.init()
        cls.db.execute_SQL("UPDATE TestPunchData SET AddedToMessageBox = 1, MessageBoxId = %s WHERE id = %s" % (messageBoxId, testPunchId))
        return None

    @classmethod
    def get_test_punches(cls, testBatchGuid):
        cls.init()
        testPunchesView = cls.db.get_table_objects_by_SQL(TestPunchView,
         "SELECT TestPunchData.id, TestPunchData.SICardNumber, TestPunchData.TwentyFourHour, "
         "TestPunchData.TwelveHourTimer, TestPunchData.Fetched, TestPunchData.MessageBoxId, CASE "
           "WHEN MessageSubscriptionData.id is not null THEN MessageSubscriptionData.SubscriptionId "
           "WHEN MessageSubscriptionArchiveData.id is not null THEN MessageSubscriptionArchiveData.SubscriptionId "
           "ELSE -1 "
         "END SubscriptionId, CASE "
           "WHEN MessageSubscriptionData.id is not null THEN MessageSubscriptionData.NoOfSendTries "
           "WHEN MessageSubscriptionArchiveData.id is not null THEN MessageSubscriptionArchiveData.NoOfSendTries "
           "ELSE 0 "
         "END NoOfSendTries, CASE "
           "WHEN MessageBoxData.id is null and MessageBoxArchiveData.id is null THEN 'Not added' "
           "WHEN MessageSubscriptionData.id is not null "
             "and MessageSubscriptionData.SentDate is null THEN 'Added' "
           "WHEN MessageSubscriptionData.id is not null "
             "and MessageSubscriptionData.SentDate is not null and MessageSubscriptionData.AckReceivedDate is null THEN 'Sent' "
           "WHEN MessageSubscriptionArchiveData.id is not null "
             "and MessageSubscriptionArchiveData.SentDate is null THEN 'Not sent' "
           "WHEN MessageSubscriptionArchiveData.id is not null "
             "and MessageSubscriptionArchiveData.SentDate is not null and MessageSubscriptionArchiveData.AckReceivedDate is null THEN 'Not acked' "
           "WHEN MessageSubscriptionArchiveData.id is not null "
             "and MessageSubscriptionArchiveData.SentDate is not null and MessageSubscriptionArchiveData.AckReceivedDate is not null THEN 'Acked' "
           "ELSE 'No subscr.' "
         "END Status, CASE "
           "WHEN MessageSubscriptionArchiveData.id is not null THEN MessageSubscriptionArchiveData.AckRSSIValue "
           "ELSE 0 "
         "END AckRSSIValue "
         "FROM TestPunchData LEFT JOIN MessageBoxData ON TestPunchData.MessageBoxId = MessageBoxData.id "
         "LEFT JOIN MessageSubscriptionData ON MessageBoxData.id = MessageSubscriptionData.MessageBoxId "
         "LEFT JOIN MessageBoxArchiveData ON TestPunchData.MessageBoxId = MessageBoxArchiveData.OrigId "
         "LEFT JOIN MessageSubscriptionArchiveData ON MessageBoxArchiveData.OrigId = MessageSubscriptionArchiveData.MessageBoxId "
         "WHERE BatchGuid = '%s'" % testBatchGuid)
        return testPunchesView

    @classmethod
    def get_test_punches_not_fetched(cls, testBatchGuid):
        cls.init()
        allPunches = cls.get_test_punches(testBatchGuid)
        notFetchedPunches = list(filter(lambda p: not p.Fetched, allPunches))
        for punch in notFetchedPunches:
            if punch.Status == 'Not sent' or punch.Status == 'Acked' or punch.Status == 'Not acked':
                cls.db.execute_SQL("UPDATE TestPunchData SET Fetched = 1 WHERE id = %s" % punch.id)
        return notFetchedPunches

# MessageStatsData
    @classmethod
    def add_message_stat(cls, adapterInstanceName, messageSubTypeName, status, noOfMessages):
        cls.init()
        stat = MessageStatsData()
        stat.AdapterInstanceName = adapterInstanceName
        stat.MessageSubTypeName = messageSubTypeName
        stat.Status = status
        stat.NoOfMessages = noOfMessages
        stat.CreatedDate = datetime.now()
        cls.db.save_table_object(stat, False)

    @classmethod
    def get_message_stat_to_upload(cls):
        cls.init()
        fiveSecondsAgo = datetime.now() - timedelta(seconds=5)
        sql = ("SELECT * FROM MessageStatsData WHERE Uploaded = 0 AND "
               "(FetchedForUpload is null OR FetchedForUpload < ?) LIMIT 1")
        messageStats = cls.db.get_table_objects_by_SQL(MessageStatsData, sql, (fiveSecondsAgo,))
        if len(messageStats) > 0:
            sql = "UPDATE MessageStatsData SET FetchedForUpload = ? WHERE Id = ?"
            cls.db.execute_SQL(sql, (datetime.now(), messageStats[0].id))
            return messageStats[0]

    @classmethod
    def set_message_stat_uploaded(cls, messageStatId):
        cls.init()
        sql = "UPDATE MessageStatsData SET Uploaded = 1 WHERE Id = " + str(messageStatId)
        cls.db.execute_SQL(sql)

#Channels
    @classmethod
    def get_channelold(cls, channel, dataRate, loraModem):
        cls.init()
        sql = ("SELECT * FROM ChannelData WHERE Channel = " + str(channel) +
               " and DataRate = " + str(dataRate) + " and LoraModem = '" + loraModem + "'")
        rows = cls.db.get_table_objects_by_SQL(ChannelData, sql)
        if len(rows) >= 1:
            return rows[0]
        return None

    @classmethod
    def get_channel(cls, channel, loraRange, loraModem):
        cls.init()
        sql = ("SELECT * FROM ChannelData WHERE Channel = " + str(channel) +
               " and LoraRange = '" + loraRange + "' and LoraModem = '" + loraModem + "'")
        rows = cls.db.get_table_objects_by_SQL(ChannelData, sql)
        if len(rows) >= 1:
            return rows[0]
        return None

    @classmethod
    def save_channel(cls, channel):
        cls.init()
        cls.db.save_table_object(channel, False)

    @classmethod
    def add_default_channels(cls):
        cls.init()
        channels = []
        # =========================      RF1276T      ==============================
        channels.append(ChannelData(1, 293, 'L', 439750000, 52590, 16, 12, 7, "RF1276T"))
        channels.append(ChannelData(2, 293, 'L', 439775000, 52590, 16, 12, 7, "RF1276T"))
        channels.append(ChannelData(3, 293, 'L', 439800000, 52590, 16, 12, 7, "RF1276T"))
        channels.append(ChannelData(4, 293, 'L', 439825000, 52590, 16, 12, 7, "RF1276T"))
        channels.append(ChannelData(5, 293, 'L', 439850000, 52590, 16, 12, 7, "RF1276T"))
        channels.append(ChannelData(6, 293, 'L', 439875000, 52590, 16, 12, 7, "RF1276T"))
        channels.append(ChannelData(7, 293, 'L', 439900000, 52590, 16, 12, 7, "RF1276T"))
        channels.append(ChannelData(8, 293, 'L', 439925000, 52590, 16, 12, 7, "RF1276T"))

        channels.append(ChannelData(1, 537, 'ML', 439750000, 24130, 16, 11, 7, "RF1276T"))
        channels.append(ChannelData(2, 537, 'ML', 439775000, 24130, 16, 11, 7, "RF1276T"))
        channels.append(ChannelData(3, 537, 'ML', 439800000, 24130, 16, 11, 7, "RF1276T"))
        channels.append(ChannelData(4, 537, 'ML', 439825000, 24130, 16, 11, 7, "RF1276T"))
        channels.append(ChannelData(5, 537, 'ML', 439850000, 24130, 16, 11, 7, "RF1276T"))
        channels.append(ChannelData(6, 537, 'ML', 439875000, 24130, 16, 11, 7, "RF1276T"))
        channels.append(ChannelData(7, 537, 'ML', 439900000, 24130, 16, 11, 7, "RF1276T"))
        channels.append(ChannelData(8, 537, 'ML', 439925000, 24130, 16, 11, 7, "RF1276T"))

        channels.append(ChannelData(1, 977, 'MS', 439750000, 15680, 16, 10, 7, "RF1276T"))
        channels.append(ChannelData(2, 977, 'MS', 439775000, 15680, 16, 10, 7, "RF1276T"))
        channels.append(ChannelData(3, 977, 'MS', 439800000, 15680, 16, 10, 7, "RF1276T"))
        channels.append(ChannelData(4, 977, 'MS', 439825000, 15680, 16, 10, 7, "RF1276T"))
        channels.append(ChannelData(5, 977, 'MS', 439850000, 15680, 16, 10, 7, "RF1276T"))
        channels.append(ChannelData(6, 977, 'MS', 439875000, 15680, 16, 10, 7, "RF1276T"))
        channels.append(ChannelData(7, 977, 'MS', 439900000, 15680, 16, 10, 7, "RF1276T"))
        channels.append(ChannelData(8, 977, 'MS', 439925000, 15680, 16, 10, 7, "RF1276T"))

        channels.append(ChannelData(1, 1758, 'S', 439750000, 8714, 15, 9, 7, "RF1276T"))
        channels.append(ChannelData(2, 1758, 'S', 439775000, 8714, 15, 9, 7, "RF1276T"))
        channels.append(ChannelData(3, 1758, 'S', 439800000, 8714, 15, 9, 7, "RF1276T"))
        channels.append(ChannelData(4, 1758, 'S', 439825000, 8714, 15, 9, 7, "RF1276T"))
        channels.append(ChannelData(5, 1758, 'S', 439850000, 8714, 15, 9, 7, "RF1276T"))
        channels.append(ChannelData(6, 1758, 'S', 439875000, 8714, 15, 9, 7, "RF1276T"))
        channels.append(ChannelData(7, 1758, 'S', 439900000, 8714, 15, 9, 7, "RF1276T"))
        channels.append(ChannelData(8, 1758, 'S', 439925000, 8714, 15, 9, 7, "RF1276T"))

        channels.append(ChannelData(1, 3125, 'XS', 439750000, 4793, 15, 8, 7, "RF1276T"))
        channels.append(ChannelData(2, 3125, 'XS', 439775000, 4793, 15, 8, 7, "RF1276T"))
        channels.append(ChannelData(3, 3125, 'XS', 439800000, 4793, 15, 8, 7, "RF1276T"))
        channels.append(ChannelData(4, 3125, 'XS', 439825000, 4793, 15, 8, 7, "RF1276T"))
        channels.append(ChannelData(5, 3125, 'XS', 439850000, 4793, 15, 8, 7, "RF1276T"))
        channels.append(ChannelData(6, 3125, 'XS', 439875000, 4793, 15, 8, 7, "RF1276T"))
        channels.append(ChannelData(7, 3125, 'XS', 439900000, 4793, 15, 8, 7, "RF1276T"))
        channels.append(ChannelData(8, 3125, 'XS', 439925000, 4793, 15, 8, 7, "RF1276T"))

        channels.append(ChannelData(1, 5470, 'US', 439750000, 2736, 15, 7, 7, "RF1276T"))
        channels.append(ChannelData(2, 5470, 'US', 439775000, 2736, 15, 7, 7, "RF1276T"))
        channels.append(ChannelData(3, 5470, 'US', 439800000, 2736, 15, 7, 7, "RF1276T"))
        channels.append(ChannelData(4, 5470, 'US', 439825000, 2736, 15, 7, 7, "RF1276T"))
        channels.append(ChannelData(5, 5470, 'US', 439850000, 2736, 15, 7, 7, "RF1276T"))
        channels.append(ChannelData(6, 5470, 'US', 439875000, 2736, 15, 7, 7, "RF1276T"))
        channels.append(ChannelData(7, 5470, 'US', 439900000, 2736, 15, 7, 7, "RF1276T"))
        channels.append(ChannelData(8, 5470, 'US', 439925000, 2736, 15, 7, 7, "RF1276T"))

        #======================
        #                     channel, datarate, freq, slopek, M, rffactor, rfBw, loramodem
        channels.append(ChannelData(1, 73, 'UL', 439712500, 210410, 16, 12, 5, "DRF1268DS"))
        channels.append(ChannelData(2, 73, 'UL', 439762500, 210410, 16, 12, 5, "DRF1268DS"))
        channels.append(ChannelData(3, 73, 'UL', 439812500, 210410, 16, 12, 5, "DRF1268DS"))
        channels.append(ChannelData(4, 73, 'UL', 439862500, 210410, 16, 12, 5, "DRF1268DS"))
        channels.append(ChannelData(5, 73, 'UL', 439912500, 210410, 16, 12, 5, "DRF1268DS"))
        channels.append(ChannelData(6, 73, 'UL', 439962500, 210410, 16, 12, 5, "DRF1268DS"))

        channels.append(ChannelData(1, 134, 'XL', 439712500, 114626, 16, 11, 5, "DRF1268DS"))
        channels.append(ChannelData(2, 134, 'XL', 439762500, 114626, 16, 11, 5, "DRF1268DS"))
        channels.append(ChannelData(3, 134, 'XL', 439812500, 114626, 16, 11, 5, "DRF1268DS"))
        channels.append(ChannelData(4, 134, 'XL', 439862500, 114626, 16, 11, 5, "DRF1268DS"))
        channels.append(ChannelData(5, 134, 'XL', 439912500, 114626, 16, 11, 5, "DRF1268DS"))
        channels.append(ChannelData(6, 134, 'XL', 439962500, 114626, 16, 11, 5, "DRF1268DS"))

        channels.append(ChannelData(1, 244, 'L', 439712500, 62950, 16, 10, 5, "DRF1268DS"))
        channels.append(ChannelData(2, 244, 'L', 439762500, 62950, 16, 10, 5, "DRF1268DS"))
        channels.append(ChannelData(3, 244, 'L', 439812500, 62950, 16, 10, 5, "DRF1268DS"))
        channels.append(ChannelData(4, 244, 'L', 439862500, 62950, 16, 10, 5, "DRF1268DS"))
        channels.append(ChannelData(5, 244, 'L', 439912500, 62950, 16, 10, 5, "DRF1268DS"))
        channels.append(ChannelData(6, 244, 'L', 439962500, 62950, 16, 10, 5, "DRF1268DS"))

        channels.append(ChannelData(1, 439, 'ML', 439712500, 34988, 16, 9, 5, "DRF1268DS"))
        channels.append(ChannelData(2, 439, 'ML', 439762500, 34988, 16, 9, 5, "DRF1268DS"))
        channels.append(ChannelData(3, 439, 'ML', 439812500, 34988, 16, 9, 5, "DRF1268DS"))
        channels.append(ChannelData(4, 439, 'ML', 439862500, 34988, 16, 9, 5, "DRF1268DS"))
        channels.append(ChannelData(5, 439, 'ML', 439912500, 34988, 16, 9, 5, "DRF1268DS"))
        channels.append(ChannelData(6, 439, 'ML', 439962500, 34988, 16, 9, 5, "DRF1268DS"))

        channels.append(ChannelData(1, 781, 'MS', 439712500, 19667, 16, 8, 5, "DRF1268DS"))
        channels.append(ChannelData(2, 781, 'MS', 439762500, 19667, 16, 8, 5, "DRF1268DS"))
        channels.append(ChannelData(3, 781, 'MS', 439812500, 19667, 16, 8, 5, "DRF1268DS"))
        channels.append(ChannelData(4, 781, 'MS', 439862500, 19667, 16, 8, 5, "DRF1268DS"))
        channels.append(ChannelData(5, 781, 'MS', 439912500, 19667, 16, 8, 5, "DRF1268DS"))
        channels.append(ChannelData(6, 781, 'MS', 439962500, 19667, 16, 8, 5, "DRF1268DS"))

        channels.append(ChannelData(1, 1367, 'S', 439712500, 11236, 16, 7, 5, "DRF1268DS"))
        channels.append(ChannelData(2, 1367, 'S', 439762500, 11236, 16, 7, 5, "DRF1268DS"))
        channels.append(ChannelData(3, 1367, 'S', 439812500, 11236, 16, 7, 5, "DRF1268DS"))
        channels.append(ChannelData(4, 1367, 'S', 439862500, 11236, 16, 7, 5, "DRF1268DS"))
        channels.append(ChannelData(5, 1367, 'S', 439912500, 11236, 16, 7, 5, "DRF1268DS"))
        channels.append(ChannelData(6, 1367, 'S', 439962500, 11236, 16, 7, 5, "DRF1268DS"))

        for channel in channels:
            cls.save_channel(channel)



