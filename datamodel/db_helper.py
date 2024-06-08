__author__ = 'henla464'

from datamodel.datamodel import *
from databaselib.db import DB
from databaselib.datamapping import DataMapping
from datetime import timedelta, datetime


class DatabaseHelper:
    db = DB("WiRoc.db", DataMapping())
    WiRocLogger = logging.getLogger('WiRoc')

    @classmethod
    def init(cls) -> None:
        pass
        #if cls.db is None:
        #    cls.db = DB("WiRoc.db", DataMapping())

    #@classmethod
    #def reInit(cls) -> None:
    #    cls.db = DB("WiRoc.db", DataMapping())

    @classmethod
    def ensure_tables_created(cls) -> None:
        DatabaseHelper.WiRocLogger.debug("DatabaseHelper::ensure_tables_created()")
        cls.init()
        db = cls.db
        table = SettingData()
        db.ensure_table_created(table)
        table = ErrorCodeData()
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
        table = BluetoothSerialPortData()
        db.ensure_table_created(table)

    @classmethod
    def drop_all_tables(cls) -> None:
        DatabaseHelper.WiRocLogger.debug("DatabaseHelper::drop_all_tables()")
        cls.init()
        db = cls.db
        table = SettingData()
        db.drop_table(table)
        table = ErrorCodeData()
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
        table = BluetoothSerialPortData()
        db.drop_table(table)

    @classmethod
    def truncate_setup_tables(cls) -> None:
        DatabaseHelper.WiRocLogger.debug("DatabaseHelper::truncate_setup_tables()")
        cls.init()
        db = cls.db
        db.execute_SQL("DELETE FROM SubscriptionData")
        db.execute_SQL("DELETE FROM TransformData")
        db.execute_SQL("DELETE FROM InputAdapterInstances")
        db.execute_SQL("DELETE FROM SubscriberData")
        db.execute_SQL("DELETE FROM MessageTypeData")
        db.execute_SQL("DELETE FROM MessageSubscriptionData")

    @classmethod
    def delete_punches(cls) -> None:
        DatabaseHelper.WiRocLogger.debug("DatabaseHelper::delete_punches()")
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

    # Settings
    @classmethod
    def save_setting(cls, settingData: SettingData) -> SettingData:
        cls.init()
        sd = cls.get_setting_by_key(settingData.Key)
        if sd is None:
            sd = cls.db.save_table_object(settingData, True)
        else:
            sd.Value = settingData.Value
            sd = cls.db.save_table_object(sd, True)
        return sd

    @classmethod
    def get_setting(cls, id: int) -> SettingData | None:
        cls.init()
        sd = cls.db.get_table_object(SettingData, str(id))
        return sd

    @classmethod
    def get_settings(cls) -> list[SettingData]:
        cls.init()
        rows = cls.db.get_table_objects(SettingData)
        return rows

    @classmethod
    def get_setting_by_key(cls, key: str) -> SettingData | None:
        cls.init()
        row_list = cls.db.get_table_objects_by_SQL(SettingData, "SELECT * FROM SettingData WHERE Key = '" + key + "'")
        if len(row_list) == 0:
            return None
        return row_list[0]

    @classmethod
    def get_error_codes(cls) -> list[ErrorCodeData]:
        cls.init()
        rows = cls.db.get_table_objects(ErrorCodeData)
        return [row for row in rows if len(row.Message) > 0]

    @classmethod
    def save_error_code(cls, errorCodeData: ErrorCodeData) -> int:
        cls.init()
        rows = cls.db.get_table_objects_by_SQL(SubscriberData, "SELECT * FROM ErrorCodeData WHERE Code = '" +
                                               errorCodeData.Code + "'")
        if len(rows) > 0:
            errorCodeData.id = rows[0].id

        return cls.db.save_table_object(errorCodeData, False)

    # Subscriber
    @classmethod
    def save_subscriber(cls, subscriberData: SubscriberData) -> int:
        cls.init()
        rows = cls.db.get_table_objects_by_SQL(SubscriberData, "SELECT * FROM SubscriberData WHERE TypeName = '" +
                                               subscriberData.TypeName + "' and InstanceName = '" +
                                               subscriberData.InstanceName + "'")
        if len(rows) == 0:
            return cls.db.save_table_object(subscriberData, False)
        else:
            # nothing to update
            return rows[0].id

    @classmethod
    def get_subscribers(cls) -> list[SubscriberView]:
        cls.init()
        rows = cls.db.get_table_objects_by_SQL(
                SubscriberView, "SELECT "
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
    def get_subscriber_by_subscription_id(cls, subscriptionId: int) -> list[SubscriberView]:
        cls.init()
        rows = cls.db.get_table_objects_by_SQL(
            SubscriberView,
            "SELECT "
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

    @classmethod
    def save_message_type(cls, messageTypeData: MessageTypeData) -> MessageTypeData | int:
        cls.init()
        sql = "SELECT * FROM MessageTypeData WHERE Name = ? AND MessageSubTypeName = ?"
        rows = cls.db.get_table_objects_by_SQL(MessageTypeData, sql, (messageTypeData.Name, messageTypeData.MessageSubTypeName))
        if len(rows) == 0:
            return cls.db.save_table_object(messageTypeData, False)
        else:
            # nothing to update
            return rows[0].id

    # Transforms
    @classmethod
    def save_transform(cls, transformData: TransformData) -> int:
        cls.init()
        rows = cls.db.get_table_objects_by_SQL(TransformData, "SELECT * FROM TransformData WHERE Name = '" +
                                                              transformData.Name + "'")
        if len(rows) > 0:
            transformData.id = rows[0].id
        return cls.db.save_table_object(transformData, False)

    @classmethod
    def set_transform_enabled(cls, enabled: bool, transformName: str) -> None:
        cls.init()
        dbValue = DataMapping.get_database_value(enabled)
        sql = ("UPDATE TransformData SET Enabled = " + str(dbValue) + " " +
               "WHERE TransformData.Name = '" + transformName + "'")
        DatabaseHelper.WiRocLogger.debug(sql)
        cls.db.execute_SQL(sql)

    # Subscriptions
    @classmethod
    def save_subscription(cls, subscriptionData: SubscriptionData) -> int:
        cls.init()
        rows = cls.db.get_table_objects_by_SQL(SubscriptionData,
                                               "SELECT * FROM SubscriptionData WHERE "
                                               "SubscriberId = " + str(subscriptionData.SubscriberId) +
                                               " and TransformId = " + str(subscriptionData.TransformId))
        if len(rows) > 0:
            subscriptionData.id = rows[0].id
        return cls.db.save_table_object(subscriptionData, False)

    @classmethod
    def get_subscriptions_by_input_message_type_id(cls, messageTypeId: int) -> list[SubscriptionData]:
        cls.init()
        sql = ("SELECT SubscriptionData.* FROM TransformData JOIN SubscriptionData "
               "ON TransformData.id = SubscriptionData.TransformId "
               "WHERE TransformData.Enabled = 1 AND SubscriptionData.Enabled = 1 AND "
               "InputMessageTypeID = " + str(messageTypeId))
        rows = cls.db.get_table_objects_by_SQL(SubscriptionData, sql)
        return rows

    @classmethod
    def get_subscription_view_by_input_message_type(cls, messageTypeName: str, messageSubTypeName: str) -> list[SubscriptionViewData]:
        cls.init()
        sql = ("SELECT SubscriptionData.*, TransformData.Name as TransformName, SubscriberData.TypeName as SubscriberTypeName "
               "FROM TransformData JOIN SubscriptionData ON TransformData.id = SubscriptionData.TransformId "
               "JOIN SubscriberData ON SubscriberData.id = SubscriptionData.SubscriberId "
               "JOIN MessageTypeData ON MessageTypeData.id = TransformData.InputMessageTypeID "
               "WHERE TransformData.Enabled = 1 AND SubscriptionData.Enabled = 1 AND "
               "MessageTypeData.Name = '" + str(messageTypeName) + "' AND MessageSubTypeName = '" + str(messageSubTypeName) + "'")
        rows = cls.db.get_table_objects_by_SQL(SubscriptionViewData, sql)
        return rows

    @classmethod
    def update_subscriptions(cls, enabled: bool, deleteAfterSent: bool, subscriberTypeName: str) -> None:
        cls.init()
        sql = ("UPDATE SubscriptionData SET Enabled = " + str(1 if enabled else 0) + ", "
               "DeleteAfterSent = " + str(1 if deleteAfterSent else 0) + " WHERE SubscriberId IN "
               "(SELECT id from SubscriberData WHERE SubscriberData.TypeName = '" + str(subscriberTypeName) + "')")
        cls.db.execute_SQL(sql)

    @classmethod
    def update_subscription(cls, enabled: bool, deleteAfterSent: bool, subscriberTypeName: str, transformName: str) -> None:
        cls.init()
        sql = ("UPDATE SubscriptionData SET Enabled = " + str(1 if enabled else 0) + ", "
               "DeleteAfterSent = " + str(1 if deleteAfterSent else 0) + " WHERE SubscriberId IN "
               "(SELECT id from SubscriberData WHERE SubscriberData.TypeName = '" + str(subscriberTypeName) + "') "
               "AND TransformId IN "
               "(SELECT id from TransformData WHERE TransformData.Name = '" + str(transformName) + "') ")
        cls.db.execute_SQL(sql)

    # MessageSubscriptions
    @classmethod
    def get_no_of_message_subscriptions_by_message_box_id(cls, msgBoxId: int) -> int:
        cls.init()
        sql = "SELECT count(*) FROM MessageSubscriptionData WHERE MessageBoxId = %s" % msgBoxId
        no = cls.db.get_scalar_by_SQL(sql)
        return no

    @classmethod
    def update_messageid(cls, subscriptionId: int, messageID: bytearray) -> None:
        cls.init()
        sql = "UPDATE MessageSubscriptionData SET MessageID = ? WHERE id = ?"
        cls.db.execute_SQL(sql, (messageID, subscriptionId))

    @classmethod
    def save_message_subscription(cls, messageSubscription: MessageSubscriptionData) -> None:
        cls.init()
        cls.db.save_table_object(messageSubscription, False)

    @classmethod
    def archive_message_subscription_view_after_sent(cls, messageSubscriptionId: int) -> None:
        cls.init()
        messageSubscriptionView = DatabaseHelper.get_message_subscriptions_view_by_id(messageSubscriptionId)
        msa = MessageSubscriptionArchiveData()
        msa.OrigId = messageSubscriptionView.id
        msa.MessageID = messageSubscriptionView.MessageID
        msa.AckReceivedFromReceiver = messageSubscriptionView.AckReceivedFromReceiver
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
    def archive_message_subscription_view_not_sent(cls, messageSubscriptionId: int) -> None:
        cls.init()
        messageSubscriptionView = DatabaseHelper.get_message_subscriptions_view_by_id(messageSubscriptionId)
        msa = MessageSubscriptionArchiveData()
        msa.OrigId = messageSubscriptionView.id
        msa.MessageID = messageSubscriptionView.MessageID
        msa.AckReceivedFromReceiver = messageSubscriptionView.AckReceivedFromReceiver
        msa.SentDate = messageSubscriptionView.SentDate
        if messageSubscriptionView.SendFailedDate is None:
            msa.SendFailedDate = datetime.now()
        else:
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
    def increment_send_tries_and_set_sent_date(cls, messageSubscriptionId: int, retryDelay: float, sentDate: datetime) -> None:
        cls.init()
        msa = cls.db.get_table_object(MessageSubscriptionData, messageSubscriptionId)
        if msa is None:
            return None
        msa.SentDate = sentDate
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
    def clear_fetched_for_sending(cls, messageSubscriptionId: int) -> None:
        cls.init()
        msa = cls.db.get_table_object(MessageSubscriptionData, messageSubscriptionId)
        msa.FetchedForSending = None
        cls.db.save_table_object(msa, False)

    @classmethod
    def increment_send_tries_and_set_send_failed_date(cls, messageSubscriptionId: int, retryDelay: float, sendFailureDate: datetime) -> None:
        cls.init()
        msa = cls.db.get_table_object(MessageSubscriptionData, messageSubscriptionId)
        msa.SendFailedDate = sendFailureDate
        msa.NoOfSendTries = msa.NoOfSendTries + 1
        msa.FindAdapterTryDate = None
        msa.FindAdapterTries = 0
        msa.FetchedForSending = None
        msa.RetryDelay = retryDelay
        msa.FindAdapterRetryDelay = 0
        cls.db.save_table_object(msa, False)

    @classmethod
    def increment_find_adapter_tries_and_set_find_adapter_try_date(cls, messageSubscriptionId: int, retryDelay: float) -> None:
        cls.init()
        msa = cls.db.get_table_object(MessageSubscriptionData, messageSubscriptionId)
        msa.FindAdapterTryDate = datetime.now()
        msa.FindAdapterTries = msa.FindAdapterTries + 1
        msa.FindAdpterRetryDelay = retryDelay
        cls.db.save_table_object(msa, False)

    @classmethod
    def set_ack_received_from_receiver_on_repeater_lora_ack_message_subscription(cls, messageID: bytearray) -> None:
        cls.init()
        sql = ("SELECT MessageSubscriptionData.* FROM MessageSubscriptionData JOIN SubscriptionData "
               "ON SubscriptionData.id = MessageSubscriptionData.SubscriptionId "
               "JOIN TransformData ON SubscriptionData.TransformId = TransformData.id "
               "WHERE TransformData.Name = 'RepeaterToLoraAckTransform' AND "
               "MessageSubscriptionData.MessageID = ? ORDER BY SentDate desc LIMIT 2")
        rows = cls.db.get_table_objects_by_SQL(MessageSubscriptionData, sql, (messageID,))

        for msd in rows:
            msd.AckReceivedFromReceiver = True
            DatabaseHelper.WiRocLogger.debug("DatabaseHelper::set_ack_received_from_receiver_on_repeater_lora_ack_message_subscription(): The ack sent from repeater to sender should indicate the message has been received by receiver")
            cls.db.save_table_object(msd, False)

    @classmethod
    def archive_lora_ack_message_subscription(cls, messageID: bytearray):
        cls.init()
        sql = ("SELECT MessageSubscriptionData.* FROM MessageSubscriptionData JOIN SubscriptionData "
               "ON SubscriptionData.id = MessageSubscriptionData.SubscriptionId "
               "JOIN TransformData ON SubscriptionData.TransformId = TransformData.id "
               "WHERE TransformData.Name = 'LoraSIMessageToLoraAckTransform' AND "
               "MessageSubscriptionData.MessageID = ?")
        rows = cls.db.get_table_objects_by_SQL(MessageSubscriptionData, sql, (messageID, ))

        if len(rows) > 0:
            now = datetime.now()
            msd = rows[0]
            msa = MessageSubscriptionArchiveData()
            msa.OrigId = msd.id
            msa.MessageID = msd.MessageID
            msa.AckReceivedFromReceiver = msd.AckReceivedFromReceiver
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
            DatabaseHelper.WiRocLogger.debug("DatabaseHelper::archive_lora_ack_message_subscription(): Archive ack message because it was already sent when SIMessage was received")
            cls.db.save_table_object(msa, False)
            cls.db.delete_table_object(MessageSubscriptionData, msd.id)
            remainingMsgSub = cls.get_no_of_message_subscriptions_by_message_box_id(msd.MessageBoxId)
            if remainingMsgSub == 0:
                cls.archive_message_box(msd.MessageBoxId)

    @classmethod
    def archive_repeater_lora_message_subscriptions_after_ack(cls, messageID: bytearray, rssiValue: int):
        cls.init()
        sql = ("SELECT MessageSubscriptionData.* FROM MessageSubscriptionData JOIN SubscriptionData "
               "ON SubscriptionData.id = MessageSubscriptionData.SubscriptionId "
               "JOIN TransformData ON SubscriptionData.TransformId = TransformData.id "
               "WHERE (TransformData.Name = 'RepeaterSIMessageToLoraTransform' OR "
               "TransformData.Name = 'SITestTestToLoraTransform') AND "
               "MessageSubscriptionData.MessageID = ? ORDER BY SentDate desc LIMIT 2")
        rows = cls.db.get_table_objects_by_SQL(MessageSubscriptionData, sql, (messageID, ))

        for msd in rows:
            now = datetime.now()
            msa = MessageSubscriptionArchiveData()
            msa.OrigId = msd.id
            msa.MessageID = msd.MessageID
            msa.AckReceivedFromReceiver = msd.AckReceivedFromReceiver
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
            DatabaseHelper.WiRocLogger.debug("DatabaseHelper::archive_repeater_lora_message_subscription_after_ack(): Archive message because it was already received by receiver")
            cls.db.save_table_object(msa, False)
            cls.db.delete_table_object(MessageSubscriptionData, msd.id)
            remainingMsgSub = cls.get_no_of_message_subscriptions_by_message_box_id(msd.MessageBoxId)
            if remainingMsgSub == 0:
                cls.archive_message_box(msd.MessageBoxId)

    @classmethod
    def archive_message_subscriptions_after_ack(cls, messageID: bytearray, ackRSSIValue: int):
        cls.init()
        sixtySecondsAgo = datetime.now() - timedelta(seconds=60)
        sql = ("SELECT MessageSubscriptionData.* FROM MessageSubscriptionData WHERE "
               "MessageID = ? AND SentDate > ? ORDER BY SentDate desc LIMIT 2")
        rows = cls.db.get_table_objects_by_SQL(MessageSubscriptionData, sql, (messageID, sixtySecondsAgo))

        for msd in rows:
            now = datetime.now()
            msa = MessageSubscriptionArchiveData()
            msa.OrigId = msd.id
            msa.MessageID = msd.MessageID
            msa.AckReceivedFromReceiver = msd.AckReceivedFromReceiver
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
            DatabaseHelper.WiRocLogger.debug("DatabaseHelper::archive_message_subscriptions_after_ack(): Archive message, messageID " + Utils.GetDataInHex(messageID, logging.DEBUG))
            cls.db.save_table_object(msa, False)
            cls.db.delete_table_object(MessageSubscriptionData, msd.id)
            remainingMsgSub = cls.get_no_of_message_subscriptions_by_message_box_id(msd.MessageBoxId)
            if remainingMsgSub == 0:
                cls.archive_message_box(msd.MessageBoxId)

    @classmethod
    def get_no_of_lora_messages_sent_not_acked(cls, startTime: datetime, endTime: datetime) -> int:
        selectSQL = ("select sum(NoOfSendTries) from "
                     "(select sum(NoOfSendTries) as NoOfSendTries from MessageSubscriptionArchiveData "
                     "join MessageBoxArchiveData on MessageSubscriptionArchiveData.MessageBoxId = MessageBoxArchiveData.OrigId "
                     "where MessageSubscriptionArchiveData.SentDate >= ? and MessageSubscriptionArchiveData.SentDate < ?"
                     "union "
                     "select sum(NoOfSendTries) as NoOfSendTries from MessageSubscriptionData "
                     "join MessageBoxData on MessageSubscriptionData.MessageBoxId = MessageBoxData.Id "
                     "where MessageSubscriptionData.SentDate >= ? and MessageSubscriptionData.SentDate < ?);")

        noOfMessages = cls.db.get_scalar_by_SQL(selectSQL, (startTime,endTime, startTime, endTime))
        if noOfMessages is None:
            return 0
        return noOfMessages

    @classmethod
    def get_if_all_lora_punches_succeeded(cls, startTime: datetime, endTime: datetime) -> bool:
        # is there any messages that failed all retries?
        selectSQL = ("select count(*) from MessageSubscriptionArchiveData "
                     "join MessageBoxArchiveData on MessageSubscriptionArchiveData.MessageBoxId = MessageBoxArchiveData.OrigId "
                     "where MessageSubscriptionArchiveData.SendFailedDate >= ? and MessageSubscriptionArchiveData.SendFailedDate < ?;")
        noOfMessages = cls.db.get_scalar_by_SQL(selectSQL, (startTime,endTime))
        return noOfMessages == 0

    @classmethod
    def get_failed_lora_messages(cls, startTime: datetime, endTime: datetime) -> list[MessageBoxArchiveData]:
        selectSQL = ("select MessageBoxArchiveData.* from MessageSubscriptionArchiveData "
                     "join MessageBoxArchiveData on MessageSubscriptionArchiveData.MessageBoxId = MessageBoxArchiveData.OrigId "
                     "where MessageSubscriptionArchiveData.SendFailedDate >= ? and MessageSubscriptionArchiveData.SendFailedDate < ? "
                     "and MessageSubscriptionArchiveData.AckReceivedDate IS NULL and MessageSubscriptionArchiveData.SubscriberTypeName = 'LORA' "
                     "and (MessageBoxArchiveData.Resubmitted = 0 or MessageBoxArchiveData.Resubmitted IS NULL)"
                     "order by MessageSubscriptionArchiveData.SendFailedDate desc LIMIT 1;")
        messageBoxDatas = cls.db.get_table_objects_by_SQL(MessageBoxArchiveData, selectSQL, (startTime,endTime))
        return messageBoxDatas

    @classmethod
    def get_no_of_times_message_data_submitted_since_last_acked_message(cls, messageData: bytearray) -> int:
        selectLastAckReceivedDateSQL = ("select MessageSubscriptionArchiveData.AckReceivedDate from MessageSubscriptionArchiveData "
                                        "where MessageSubscriptionArchiveData.SubscriberTypeName = 'LORA' "
                                        "order by MessageSubscriptionArchiveData.AckReceivedDate desc LIMIT 1;")
        lastAckReceivedDate = cls.db.get_scalar_by_SQL(selectLastAckReceivedDateSQL)
        selectCountSQL = ("select count(MessageBoxArchiveData.OrigId) from MessageSubscriptionArchiveData "
                          "join MessageBoxArchiveData on MessageSubscriptionArchiveData.MessageBoxId = MessageBoxArchiveData.OrigId "
                          "where MessageSubscriptionArchiveData.SubscriberTypeName = 'LORA' "
                          "and MessageBoxArchiveData.MessageData = ? "
                          "and SendFailedDate > ?;")

        noOfSubmits = cls.db.get_scalar_by_SQL(selectCountSQL, (messageData,lastAckReceivedDate))
        return noOfSubmits


    @classmethod
    def set_message_resubmitted(cls, messageBoxArchiveId: int):
        updateSQL = "update MessageBoxArchiveData set Resubmitted = 1 where MessageBoxArchiveData.id = ?"
        cls.db.execute_SQL(updateSQL, (messageBoxArchiveId,))

    @classmethod
    def repeater_messages_acked(cls, messageID: bytearray, ackRSSIValue: int):
        cls.init()
        sql = ("SELECT RepeaterMessageBoxData.* FROM RepeaterMessageBoxData WHERE "
               "MessageID = ?")
        rows = cls.db.get_table_objects_by_SQL(RepeaterMessageBoxData, sql, (messageID, ))
        for msgToUpdate in rows:
            msgToUpdate.Acked = True
            msgToUpdate.NoOfTimesAckSeen = msgToUpdate.NoOfTimesAckSeen + 1
            msgToUpdate.AckRSSIValue = ackRSSIValue
            if msgToUpdate.AckedTime is None:
                msgToUpdate.AckedTime = datetime.now()
            DatabaseHelper.WiRocLogger.debug("DatabaseHelper::repeater_messages_acked(): Marking RepeaterMessageBoxData message as acked")
            cls.db.save_table_object(msgToUpdate, False)

    @classmethod
    def archive_repeater_message_after_added_to_message_box(cls, repeaterMessageBoxId: int):
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
        msa.MessageBoxId = repeaterMessageBox.MessageBoxId
        msa.AddedToMessageBoxTime = datetime.now()
        msa.RSSIValue = repeaterMessageBox.RSSIValue
        msa.AckRSSIValue = repeaterMessageBox.AckRSSIValue
        msa.LastSeenTime = repeaterMessageBox.LastSeenTime
        msa.OrigCreatedDate = repeaterMessageBox.CreatedDate
        cls.db.save_table_object(msa, False)
        cls.db.delete_table_object(RepeaterMessageBoxData, repeaterMessageBoxId)

    # MessageSubscriptionView

    @classmethod
    def does_message_id_exist(cls, messageID: bytearray) -> bool:
        sql = ("SELECT MessageSubscriptionData.id "
               "FROM MessageSubscriptionData "
               "WHERE MessageSubscriptionData.MessageID = ?")
        messageSubscriptions = cls.db.get_table_objects_by_SQL(MessageSubscriptionView, sql, (messageID,))
        if len(messageSubscriptions) > 0:
            return True
        return False

    @classmethod
    def get_message_subscriptions_view_by_id(cls, messageSubscriptionId: int) -> MessageSubscriptionView | None:
        cls.init()
        sql = ("SELECT MessageSubscriptionData.id, "
               "MessageSubscriptionData.MessageID, "
               "MessageSubscriptionData.AckReceivedFromReceiver, "
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
               "WHERE MessageSubscriptionData.id = ?")
        messageSubscriptions = cls.db.get_table_objects_by_SQL(MessageSubscriptionView, sql, (messageSubscriptionId,))
        if len(messageSubscriptions) > 0:
            return messageSubscriptions[0]
        return None

    @classmethod
    def get_message_subscriptions_view_to_send(cls, maxRetries: int) -> tuple[int, MessageSubscriptionBatch | None]:
        sql = "SELECT count(MessageSubscriptionData.id) FROM MessageSubscriptionData"
        cls.init()
        cnt = cls.db.get_scalar_by_SQL(sql)
        if cnt > 0:

            sql = ("SELECT MessageSubscriptionData.id, "
                   "MessageSubscriptionData.MessageID, "
                   "MessageSubscriptionData.AckReceivedFromReceiver, "
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
                   "SubscriptionData.BatchSize, "
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

            now = datetime.now()
            messageSubscriptionBatch = None
            adapterTypesAlreadyHandlingMessages = set()
            for messageSubscription in messageSubscriptions:
                if messageSubscription.SubscriberTypeName in adapterTypesAlreadyHandlingMessages:
                    # a message has already been sent to this adapter or is waiting to be sent (been delayed)
                    # skip any following messages to the same adapter
                    #DatabaseHelper.WiRocLogger.debug('a message has already been sent to this adapter or is waiting to be sent (been delayed): ' + str(messageSubscription.SubscriberTypeName))
                    continue

                if messageSubscription.FetchedForSending is not None and messageSubscription.FetchedForSending < now < messageSubscription.FetchedForSending + timedelta(
                        seconds=12):
                    # recently fetched and is being sent by another thread
                    #DatabaseHelper.WiRocLogger.debug("Recently fetched and is being sent by another thread. Time fetched: " + str(messageSubscription.FetchedForSending))
                    adapterTypesAlreadyHandlingMessages.add(messageSubscription.SubscriberTypeName)
                    continue

                if messageSubscription.CreatedDate < now < messageSubscription.CreatedDate + timedelta(microseconds=messageSubscription.Delay):
                    # Should have an initial delay that has not passed yet
                    #DatabaseHelper.WiRocLogger.debug(f"Should have an initial delay that has not passed yet: Created: {messageSubscription.CreatedDate} Delay: {messageSubscription.Delay}")
                    adapterTypesAlreadyHandlingMessages.add(messageSubscription.SubscriberTypeName)
                    continue

                if messageSubscription.SentDate is not None and messageSubscription.SentDate < now < messageSubscription.SentDate + timedelta(microseconds=messageSubscription.RetryDelay):
                    # has been sent, not yet passed the retry delay (may still be waiting for ack)
                    #DatabaseHelper.WiRocLogger.debug(f"has been sent, not yet passed the retry delay (may still be waiting for ack). RetryDelay: {messageSubscription.RetryDelay} Delayed until: {messageSubscription.SentDate + timedelta(microseconds=messageSubscription.RetryDelay)}")
                    adapterTypesAlreadyHandlingMessages.add(messageSubscription.SubscriberTypeName)
                    continue

                if messageSubscription.FindAdapterTryDate is not None and messageSubscription.FindAdapterTryDate < now < messageSubscription.FindAdapterTryDate + timedelta(microseconds=messageSubscription.FindAdapterRetryDelay):
                    # should wait longer before trying to find adapter again
                    #DatabaseHelper.WiRocLogger.debug(f"Should wait longer before trying to find adapter again. FindAdapterRetryDelay {messageSubscription.FindAdapterRetryDelay}")
                    adapterTypesAlreadyHandlingMessages.add(messageSubscription.SubscriberTypeName)
                    continue

                if messageSubscription.NoOfSendTries >= maxRetries:
                    # Message may have been sent, noOfSendTries incremented, passed the retry time
                    # BUT has not yet been archived. Just skip/should be ignored
                    #DatabaseHelper.WiRocLogger.debug("Message may have been sent, noOfSendTries incremented, passed the retry time BUT has not yet been archived. Just skip/should be ignored")
                    continue

                if messageSubscription.FindAdapterTries >= maxRetries:
                    #DatabaseHelper.WiRocLogger.debug("Ignore messages exceeding find adapter tries. Has not yet been archived.")
                    # Ignore messages exceeding find adapter tries. Has not yet been archived.
                    continue

                if messageSubscriptionBatch is None:
                    messageSubscriptionBatch = MessageSubscriptionBatch()
                    messageSubscriptionBatch.AckReceivedFromReceiver = messageSubscription.AckReceivedFromReceiver
                    messageSubscriptionBatch.DeleteAfterSent = messageSubscription.DeleteAfterSent
                    messageSubscriptionBatch.SubscriberTypeName = messageSubscription.SubscriberTypeName
                    messageSubscriptionBatch.SubscriberInstanceName = messageSubscription.SubscriberInstanceName
                    messageSubscriptionBatch.TransformName = messageSubscription.TransformName
                    messageSubscriptionBatch.FindAdapterTries = messageSubscription.FindAdapterTries
                    item = MessageSubscriptionBatchItem()
                    item.id = messageSubscription.id
                    item.MessageData = messageSubscription.MessageData
                    item.NoOfSendTries = messageSubscription.NoOfSendTries
                    messageSubscriptionBatch.MessageSubscriptionBatchItems.append(item)
                else:
                    if (messageSubscriptionBatch.AckReceivedFromReceiver == messageSubscription.AckReceivedFromReceiver and
                            messageSubscriptionBatch.DeleteAfterSent == messageSubscription.DeleteAfterSent and
                            messageSubscriptionBatch.SubscriberTypeName == messageSubscription.SubscriberTypeName and
                            messageSubscriptionBatch.SubscriberInstanceName == messageSubscription.SubscriberInstanceName and
                            messageSubscriptionBatch.TransformName == messageSubscription.TransformName):
                        item = MessageSubscriptionBatchItem()
                        item.id = messageSubscription.id
                        item.MessageData = messageSubscription.MessageData
                        item.NoOfSendTries = messageSubscription.NoOfSendTries

                        messageSubscriptionBatch.MessageSubscriptionBatchItems.append(item)

                if messageSubscriptionBatch is not None and \
                        len(messageSubscriptionBatch.MessageSubscriptionBatchItems) >= messageSubscription.BatchSize:
                    # Batch is full
                    break

            if messageSubscriptionBatch is not None:
                for item in messageSubscriptionBatch.MessageSubscriptionBatchItems:
                    sql = "UPDATE MessageSubscriptionData SET FetchedForSending = ? WHERE Id = ?"
                    cls.db.execute_SQL(sql, (datetime.now(), item.id))
                return cnt, messageSubscriptionBatch
        return cnt, None

    @classmethod
    def get_message_subscriptions_view_to_archive(cls, maxRetries: int, limit: int = 100):
        sql = "SELECT count(MessageSubscriptionData.id) FROM MessageSubscriptionData "
        cls.init()
        cnt = cls.db.get_scalar_by_SQL(sql)
        if cnt > 0:

            sql = ("SELECT MessageSubscriptionData.id, "
                   "MessageSubscriptionData.MessageID, "
                   "MessageSubscriptionData.AckReceivedFromReceiver, "
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
    def change_future_sent_dates(cls) -> None:
        cls.init()
        sql = "SELECT * FROM MessageSubscriptionData ORDER BY SentDate desc"
        subs = cls.db.get_table_objects_by_SQL(MessageSubscriptionData, sql)
        now = datetime.now()
        for sub in subs:
            if sub.SentDate is not None and sub.SentDate > now:
                sub.SentDate = now
                cls.db.save_table_object(sub, False)
                DatabaseHelper.WiRocLogger.debug('Set future SentDate: ' + str(sub.SentDate) + " to: " + str(now))
            else:
                return

    @classmethod
    def change_future_created_dates(cls) -> None:
        cls.init()
        sql = "SELECT * FROM MessageBoxData ORDER BY CreatedDate desc"
        messageBoxDatas = cls.db.get_table_objects_by_SQL(MessageBoxData, sql)
        now = datetime.now()
        for msg in messageBoxDatas:
            if msg.CreatedDate > now:
                msg.CreatedDate = now
                cls.db.save_table_object(msg, False)
                DatabaseHelper.WiRocLogger.debug('Set future CreatedDate: ' + str(msg.CreatedDate) + " to: " + str(now))
            else:
                return

    @classmethod
    def save_message_box(cls, messageBoxData: MessageBoxData) -> int:
        # todo: test performance with using fixed sql to insert instead
        cls.init()
        return cls.db.save_table_object(messageBoxData, False)

    @classmethod
    def get_message_box_messages(cls) -> list[MessageBoxData]:
        cls.init()
        return cls.db.get_table_objects(MessageBoxData)

    @classmethod
    def archive_message_box(cls, msgBoxId: int):
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

    # RepeaterMessageBox
    @classmethod
    def create_repeater_message_box_data(cls, messageSource, messageTypeName, messageSubTypeName, instanceName, checksumOK,
                                         powerCycle, serialNumber, lowBattery, ackRequested, repeater, siPayloadData,
                                         messageID, data, rssiValue):
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
        rmbd.MessageID = messageID
        rmbd.LowBattery = lowBattery
        rmbd.AckRequested = ackRequested
        rmbd.RepeaterRequested = repeater

        if siPayloadData is not None:
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
        sql = "SELECT RepeaterMessageBoxData.* FROM RepeaterMessageBoxData WHERE MessageID = ?"
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
        sql = "DELETE FROM RepeaterMessageBoxData WHERE LastSeenTime < ? "
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

    # InputAdapterInstances
    @classmethod
    def update_input_adapter_instances(cls, inputAdapterObjects):
        cls.init()
        sql = "UPDATE InputAdapterInstances SET ToBeDeleted = 1"
        cls.db.execute_SQL(sql)
        for inputAdapter in inputAdapterObjects:
            sql = ("WITH new (TypeName, InstanceName, ToBeDeleted) AS "
                   "( VALUES('%s', '%s', 0) ) "
                   "INSERT OR REPLACE INTO InputAdapterInstances "
                   "(id, TypeName, InstanceName, ToBeDeleted) "
                   "SELECT old.id, new.TypeName, new.InstanceName, new.ToBeDeleted "
                   "FROM new LEFT JOIN InputAdapterInstances AS old "
                   "ON new.InstanceName = old.InstanceName") % (inputAdapter.GetTypeName(), inputAdapter.GetInstanceName())
            cls.db.execute_SQL(sql)
        sql = "DELETE FROM InputAdapterInstances WHERE ToBeDeleted = 1"
        cls.db.execute_SQL(sql)

    @classmethod
    def get_input_adapter_instances(cls):
        cls.init()
        inputAdapterInstances = cls.db.get_table_objects(InputAdapterInstances)
        return inputAdapterInstances

    # BlenoPunchData
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


    @classmethod
    def get_lowest_messageboxdata_id(cls):
        cls.init()
        msgBoxId = cls.db.get_scalar_by_SQL("SELECT min(id) FROM MessageBoxData")
        return msgBoxId

    # TestPunchData
    @classmethod
    def add_test_punch(cls, testBatchGuid, SINo, twelveHourTimer, twentyFourHour, subSecond):
        cls.init()
        testPunch = TestPunchData()
        testPunch.BatchGuid = testBatchGuid
        testPunch.MessageBoxId = None
        testPunch.TwelveHourTimer = twelveHourTimer
        testPunch.TwentyFourHour = twentyFourHour
        testPunch.SubSecond = subSecond
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
        testPunches = cls.db.get_table_objects_by_SQL(TestPunchData, "SELECT * FROM TestPunchData WHERE AddedToMessageBox = 0 ORDER BY TwentyFourHour, TwelveHourTimer, SubSecond, id LIMIT 1")
        if len(testPunches) > 0:
            return testPunches[0]
        return None

    @classmethod
    def set_test_punch_added_to_message_box(cls, messageBoxId: int, testPunchId: int) -> None:
        cls.init()
        cls.db.execute_SQL("UPDATE TestPunchData SET AddedToMessageBox = 1, MessageBoxId = %s WHERE id = %s" % (messageBoxId, testPunchId))
        return None

    @classmethod
    def get_test_punches(cls, testBatchGuid: str, msgBoxId: int | None) -> list[TestPunchView]:
        cls.init()
        sql = (f"SELECT * FROM ( \
         SELECT TestPunchData.id, \
         TestPunchData.SICardNumber, \
         TestPunchData.TwentyFourHour, \
         TestPunchData.TwelveHourTimer, \
         TestPunchData.Fetched, \
         TestPunchData.MessageBoxId, \
         CASE \
           WHEN MessageSubscriptionData.id is not null THEN MessageSubscriptionData.NoOfSendTries \
           WHEN MessageSubscriptionArchiveData.id is not null THEN MessageSubscriptionArchiveData.NoOfSendTries \
           ELSE 0 \
         END NoOfSendTries, \
         CASE \
           WHEN MessageBoxData.id is null and MessageBoxArchiveData.id is null THEN 'Not added' \
           WHEN MessageSubscriptionData.id is not null \
             and MessageSubscriptionData.SentDate is null THEN 'Added' \
           WHEN MessageSubscriptionData.id is not null \
             and MessageSubscriptionData.SentDate is not null and MessageSubscriptionData.AckReceivedDate is null THEN 'Sent' \
           WHEN MessageSubscriptionArchiveData.id is not null \
             and MessageSubscriptionArchiveData.SentDate is null THEN 'Not sent' \
           WHEN MessageSubscriptionArchiveData.id is not null \
             and MessageSubscriptionArchiveData.SentDate is not null and MessageSubscriptionArchiveData.AckReceivedDate is null THEN 'Not acked' \
           WHEN MessageSubscriptionArchiveData.id is not null \
             and MessageSubscriptionArchiveData.SentDate is not null and MessageSubscriptionArchiveData.AckReceivedDate is not null THEN 'Acked' \
           ELSE 'No subscr.' \
         END Status, \
         'TestPunch' as Type, \
         CASE \
           WHEN MessageSubscriptionArchiveData.id is not null THEN MessageSubscriptionArchiveData.AckRSSIValue \
           ELSE 0 \
         END AckRSSIValue, \
         SubscriberData.TypeName \
         FROM TestPunchData LEFT JOIN MessageBoxData ON TestPunchData.MessageBoxId = MessageBoxData.id \
         LEFT JOIN MessageSubscriptionData ON MessageBoxData.id = MessageSubscriptionData.MessageBoxId \
         LEFT JOIN MessageBoxArchiveData ON TestPunchData.MessageBoxId = MessageBoxArchiveData.OrigId \
         LEFT JOIN MessageSubscriptionArchiveData ON MessageBoxArchiveData.OrigId = MessageSubscriptionArchiveData.MessageBoxId \
         LEFT JOIN SubscriptionData ON (SubscriptionData.Id = MessageSubscriptionArchiveData.SubscriptionId or SubscriptionData.Id = MessageSubscriptionData.SubscriptionId) \
         LEFT JOIN SubscriberData ON SubscriberData.Id = SubscriptionData.SubscriberId \
        WHERE BatchGuid = '{testBatchGuid}' \
         UNION ALL \
         SELECT \
         'MSDID' || MessageSubscriptionData.id as id, \
         MessageBoxData.SICardNumber, \
         CASE \
           WHEN cast(MessageBoxData.SportIdentHour as integer) >= 12 THEN 1 \
           ELSE 0 \
         END TwentyFourHour, \
         CASE \
           WHEN cast(MessageBoxData.SportIdentHour as integer) >= 12 THEN (cast(MessageBoxData.SportIdentHour as integer)-12) * 3600 + cast(MessageBoxData.SportIdentMinute as integer) * 60 + cast(MessageBoxData.SportIdentSecond as integer) \
           ELSE cast(MessageBoxData.SportIdentHour as integer) * 3600 + cast(MessageBoxData.SportIdentMinute as integer) * 60 + cast(MessageBoxData.SportIdentSecond as integer) \
         END TwelveHourTimer, \
         False as Fetched, \
         MessageBoxData.id as MessageBoxId, \
         MessageSubscriptionData.NoOfSendTries, \
        CASE \
           WHEN MessageSubscriptionData.id is not null \
             and MessageSubscriptionData.SentDate is null THEN 'Added' \
           WHEN MessageSubscriptionData.id is not null \
             and MessageSubscriptionData.SentDate is not null and MessageSubscriptionData.AckReceivedDate is null THEN 'Sent' \
         ELSE 'No subscr.' \
         END Status, \
         'Punch' as Type, \
         0 as AckRSSIValue, \
         SubscriberData.TypeName \
         FROM MessageBoxData LEFT JOIN (SELECT * FROM TestPunchData WHERE BatchGuid = '{testBatchGuid}') as tp ON tp.MessageBoxId = MessageBoxData.id \
         JOIN MessageSubscriptionData ON MessageBoxData.id = MessageSubscriptionData.MessageBoxId \
         JOIN SubscriptionData ON SubscriptionData.Id = MessageSubscriptionData.SubscriptionId \
         JOIN SubscriberData ON SubscriberData.Id = SubscriptionData.SubscriberId \
         WHERE tp.id is null and MessageBoxData.MessageTypeName != 'STATUS' and (SubscriberData.TypeName = 'LORA' or SubscriberData.TypeName = 'SIRAP') \
        UNION ALL \
         SELECT \
         'MSDID' || MessageSubscriptionArchiveData.OrigId as id, \
         MessageBoxArchiveData.SICardNumber, \
         CASE \
           WHEN cast(MessageBoxArchiveData.SportIdentHour as integer) >= 12 THEN 1 \
           ELSE 0 \
         END TwentyFourHour, \
         CASE \
           WHEN cast(MessageBoxArchiveData.SportIdentHour as integer)>= 12 THEN (cast(MessageBoxArchiveData.SportIdentHour as integer)-12) * 3600 + cast(MessageBoxArchiveData.SportIdentMinute as integer) * 60 + cast(MessageBoxArchiveData.SportIdentSecond as integer) \
           ELSE cast(MessageBoxArchiveData.SportIdentHour as integer) * 3600 + cast(MessageBoxArchiveData.SportIdentMinute as integer) * 60 + cast(MessageBoxArchiveData.SportIdentSecond as integer) \
         END TwelveHourTimer, \
         False as Fetched, \
         MessageBoxArchiveData.OrigId as MessageBoxId, \
         MessageSubscriptionArchiveData.NoOfSendTries, \
         CASE \
           WHEN MessageSubscriptionArchiveData.id is not null \
             and MessageSubscriptionArchiveData.SentDate is null THEN 'Not sent' \
           WHEN MessageSubscriptionArchiveData.id is not null \
             and MessageSubscriptionArchiveData.SentDate is not null and MessageSubscriptionArchiveData.AckReceivedDate is null THEN 'Not acked' \
           WHEN MessageSubscriptionArchiveData.id is not null \
             and MessageSubscriptionArchiveData.SentDate is not null and MessageSubscriptionArchiveData.AckReceivedDate is not null THEN 'Acked' \
           ELSE 'No subscr.' \
         END Status, \
         'Punch' as Type, \
         0 as AckRSSIValue, \
         SubscriberData.TypeName \
         FROM MessageBoxArchiveData LEFT JOIN (SELECT * FROM TestPunchData WHERE BatchGuid = '{testBatchGuid}') as tp ON tp.MessageBoxId = MessageBoxArchiveData.OrigId \
         JOIN MessageSubscriptionArchiveData ON MessageBoxArchiveData.OrigId = MessageSubscriptionArchiveData.MessageBoxId \
         JOIN SubscriptionData ON SubscriptionData.Id = MessageSubscriptionArchiveData.SubscriptionId \
         JOIN SubscriberData ON SubscriberData.Id = SubscriptionData.SubscriberId \
         WHERE tp.id is null and MessageBoxArchiveData.MessageTypeName != 'STATUS' and (SubscriberData.TypeName = 'LORA' or SubscriberData.TypeName = 'SIRAP') {f'and MessageBoxArchiveData.OrigId >= {msgBoxId}' if msgBoxId is not None else ''}) \
         ORDER BY MessageBoxId;")

        testPunchesView = cls.db.get_table_objects_by_SQL(TestPunchView, sql)
        # "SELECT TestPunchData.id, TestPunchData.SICardNumber, TestPunchData.TwentyFourHour, "
        # "TestPunchData.TwelveHourTimer, TestPunchData.Fetched, TestPunchData.MessageBoxId, CASE "
        #   "WHEN MessageSubscriptionData.id is not null THEN MessageSubscriptionData.SubscriptionId "
        #   "WHEN MessageSubscriptionArchiveData.id is not null THEN MessageSubscriptionArchiveData.SubscriptionId "
        #   "ELSE -1 "
        # "END SubscriptionId, CASE "
        #   "WHEN MessageSubscriptionData.id is not null THEN MessageSubscriptionData.NoOfSendTries "
        #   "WHEN MessageSubscriptionArchiveData.id is not null THEN MessageSubscriptionArchiveData.NoOfSendTries "
        #   "ELSE 0 "
        # "END NoOfSendTries, CASE "
        #   "WHEN MessageBoxData.id is null and MessageBoxArchiveData.id is null THEN 'Not added' "
        #   "WHEN MessageSubscriptionData.id is not null "
        #     "and MessageSubscriptionData.SentDate is null THEN 'Added' "
        #   "WHEN MessageSubscriptionData.id is not null "
        #     "and MessageSubscriptionData.SentDate is not null and MessageSubscriptionData.AckReceivedDate is null THEN 'Sent' "
        #   "WHEN MessageSubscriptionArchiveData.id is not null "
        #     "and MessageSubscriptionArchiveData.SentDate is null THEN 'Not sent' "
        #   "WHEN MessageSubscriptionArchiveData.id is not null "
        #     "and MessageSubscriptionArchiveData.SentDate is not null and MessageSubscriptionArchiveData.AckReceivedDate is null THEN 'Not acked' "
        #   "WHEN MessageSubscriptionArchiveData.id is not null "
        #     "and MessageSubscriptionArchiveData.SentDate is not null and MessageSubscriptionArchiveData.AckReceivedDate is not null THEN 'Acked' "
        #   "ELSE 'No subscr.' "
        # "END Status, CASE "
        #   "WHEN MessageSubscriptionArchiveData.id is not null THEN MessageSubscriptionArchiveData.AckRSSIValue "
        #   "ELSE 0 "
        # "END AckRSSIValue "
        # "FROM TestPunchData LEFT JOIN MessageBoxData ON TestPunchData.MessageBoxId = MessageBoxData.id "
        # "LEFT JOIN MessageSubscriptionData ON MessageBoxData.id = MessageSubscriptionData.MessageBoxId "
        # "LEFT JOIN MessageBoxArchiveData ON TestPunchData.MessageBoxId = MessageBoxArchiveData.OrigId "
        # "LEFT JOIN MessageSubscriptionArchiveData ON MessageBoxArchiveData.OrigId = MessageSubscriptionArchiveData.MessageBoxId "
        # "WHERE BatchGuid = '%s'" % testBatchGuid)
        return testPunchesView

    @classmethod
    def get_test_punches_not_fetched(cls, testBatchGuid: str, msgBoxId: int | None) -> list[TestPunchView]:
        cls.init()
        allPunches = cls.get_test_punches(testBatchGuid, msgBoxId)
        notFetchedPunches: list[TestPunchView] = list(filter(lambda p: not p.Fetched, allPunches))
        for punch in notFetchedPunches:
            if punch.Type == 'TestPunch' and (punch.Status == 'Not sent' or punch.Status == 'Acked' or punch.Status == 'Not acked'):
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
        DatabaseHelper.WiRocLogger.debug("DatabaseHelper::set_message_stat_uploaded() 1")
        cls.db.execute_SQL(sql)
        DatabaseHelper.WiRocLogger.debug("DatabaseHelper::set_message_stat_uploaded() 2")

    # Channels
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
        channels = [ChannelData(1, 293, 'L', 439750000, 52590, 16, 12, 7, "RF1276T"),
                    ChannelData(2, 293, 'L', 439775000, 52590, 16, 12, 7, "RF1276T"),
                    ChannelData(3, 293, 'L', 439800000, 52590, 16, 12, 7, "RF1276T"),
                    ChannelData(4, 293, 'L', 439825000, 52590, 16, 12, 7, "RF1276T"),
                    ChannelData(5, 293, 'L', 439850000, 52590, 16, 12, 7, "RF1276T"),
                    ChannelData(6, 293, 'L', 439875000, 52590, 16, 12, 7, "RF1276T"),
                    ChannelData(7, 293, 'L', 439900000, 52590, 16, 12, 7, "RF1276T"),
                    ChannelData(8, 293, 'L', 439925000, 52590, 16, 12, 7, "RF1276T"),
                    ChannelData(1, 537, 'ML', 439750000, 24130, 16, 11, 7, "RF1276T"),
                    ChannelData(2, 537, 'ML', 439775000, 24130, 16, 11, 7, "RF1276T"),
                    ChannelData(3, 537, 'ML', 439800000, 24130, 16, 11, 7, "RF1276T"),
                    ChannelData(4, 537, 'ML', 439825000, 24130, 16, 11, 7, "RF1276T"),
                    ChannelData(5, 537, 'ML', 439850000, 24130, 16, 11, 7, "RF1276T"),
                    ChannelData(6, 537, 'ML', 439875000, 24130, 16, 11, 7, "RF1276T"),
                    ChannelData(7, 537, 'ML', 439900000, 24130, 16, 11, 7, "RF1276T"),
                    ChannelData(8, 537, 'ML', 439925000, 24130, 16, 11, 7, "RF1276T"),
                    ChannelData(1, 977, 'MS', 439750000, 15680, 16, 10, 7, "RF1276T"),
                    ChannelData(2, 977, 'MS', 439775000, 15680, 16, 10, 7, "RF1276T"),
                    ChannelData(3, 977, 'MS', 439800000, 15680, 16, 10, 7, "RF1276T"),
                    ChannelData(4, 977, 'MS', 439825000, 15680, 16, 10, 7, "RF1276T"),
                    ChannelData(5, 977, 'MS', 439850000, 15680, 16, 10, 7, "RF1276T"),
                    ChannelData(6, 977, 'MS', 439875000, 15680, 16, 10, 7, "RF1276T"),
                    ChannelData(7, 977, 'MS', 439900000, 15680, 16, 10, 7, "RF1276T"),
                    ChannelData(8, 977, 'MS', 439925000, 15680, 16, 10, 7, "RF1276T"),
                    ChannelData(1, 1758, 'S', 439750000, 8714, 15, 9, 7, "RF1276T"),
                    ChannelData(2, 1758, 'S', 439775000, 8714, 15, 9, 7, "RF1276T"),
                    ChannelData(3, 1758, 'S', 439800000, 8714, 15, 9, 7, "RF1276T"),
                    ChannelData(4, 1758, 'S', 439825000, 8714, 15, 9, 7, "RF1276T"),
                    ChannelData(5, 1758, 'S', 439850000, 8714, 15, 9, 7, "RF1276T"),
                    ChannelData(6, 1758, 'S', 439875000, 8714, 15, 9, 7, "RF1276T"),
                    ChannelData(7, 1758, 'S', 439900000, 8714, 15, 9, 7, "RF1276T"),
                    ChannelData(8, 1758, 'S', 439925000, 8714, 15, 9, 7, "RF1276T"),
                    ChannelData(1, 3125, 'XS', 439750000, 4793, 15, 8, 7, "RF1276T"),
                    ChannelData(2, 3125, 'XS', 439775000, 4793, 15, 8, 7, "RF1276T"),
                    ChannelData(3, 3125, 'XS', 439800000, 4793, 15, 8, 7, "RF1276T"),
                    ChannelData(4, 3125, 'XS', 439825000, 4793, 15, 8, 7, "RF1276T"),
                    ChannelData(5, 3125, 'XS', 439850000, 4793, 15, 8, 7, "RF1276T"),
                    ChannelData(6, 3125, 'XS', 439875000, 4793, 15, 8, 7, "RF1276T"),
                    ChannelData(7, 3125, 'XS', 439900000, 4793, 15, 8, 7, "RF1276T"),
                    ChannelData(8, 3125, 'XS', 439925000, 4793, 15, 8, 7, "RF1276T"),
                    ChannelData(1, 5470, 'US', 439750000, 2736, 15, 7, 7, "RF1276T"),
                    ChannelData(2, 5470, 'US', 439775000, 2736, 15, 7, 7, "RF1276T"),
                    ChannelData(3, 5470, 'US', 439800000, 2736, 15, 7, 7, "RF1276T"),
                    ChannelData(4, 5470, 'US', 439825000, 2736, 15, 7, 7, "RF1276T"),
                    ChannelData(5, 5470, 'US', 439850000, 2736, 15, 7, 7, "RF1276T"),
                    ChannelData(6, 5470, 'US', 439875000, 2736, 15, 7, 7, "RF1276T"),
                    ChannelData(7, 5470, 'US', 439900000, 2736, 15, 7, 7, "RF1276T"),
                    ChannelData(8, 5470, 'US', 439925000, 2736, 15, 7, 7, "RF1276T"),
                    ChannelData(1, 73, 'UL', 439712500, 210410, 16, 12, 5, "DRF1268DS"),
                    ChannelData(2, 73, 'UL', 439762500, 210410, 16, 12, 5, "DRF1268DS"),
                    ChannelData(3, 73, 'UL', 439812500, 210410, 16, 12, 5, "DRF1268DS"),
                    ChannelData(4, 73, 'UL', 439862500, 210410, 16, 12, 5, "DRF1268DS"),
                    ChannelData(5, 73, 'UL', 439912500, 210410, 16, 12, 5, "DRF1268DS"),
                    ChannelData(6, 73, 'UL', 439962500, 210410, 16, 12, 5, "DRF1268DS"),
                    ChannelData(1, 134, 'XL', 439712500, 114626, 16, 11, 5, "DRF1268DS"),
                    ChannelData(2, 134, 'XL', 439762500, 114626, 16, 11, 5, "DRF1268DS"),
                    ChannelData(3, 134, 'XL', 439812500, 114626, 16, 11, 5, "DRF1268DS"),
                    ChannelData(4, 134, 'XL', 439862500, 114626, 16, 11, 5, "DRF1268DS"),
                    ChannelData(5, 134, 'XL', 439912500, 114626, 16, 11, 5, "DRF1268DS"),
                    ChannelData(6, 134, 'XL', 439962500, 114626, 16, 11, 5, "DRF1268DS"),
                    ChannelData(1, 244, 'L', 439712500, 62950, 16, 10, 5, "DRF1268DS"),
                    ChannelData(2, 244, 'L', 439762500, 62950, 16, 10, 5, "DRF1268DS"),
                    ChannelData(3, 244, 'L', 439812500, 62950, 16, 10, 5, "DRF1268DS"),
                    ChannelData(4, 244, 'L', 439862500, 62950, 16, 10, 5, "DRF1268DS"),
                    ChannelData(5, 244, 'L', 439912500, 62950, 16, 10, 5, "DRF1268DS"),
                    ChannelData(6, 244, 'L', 439962500, 62950, 16, 10, 5, "DRF1268DS"),
                    ChannelData(1, 439, 'ML', 439712500, 34988, 16, 9, 5, "DRF1268DS"),
                    ChannelData(2, 439, 'ML', 439762500, 34988, 16, 9, 5, "DRF1268DS"),
                    ChannelData(3, 439, 'ML', 439812500, 34988, 16, 9, 5, "DRF1268DS"),
                    ChannelData(4, 439, 'ML', 439862500, 34988, 16, 9, 5, "DRF1268DS"),
                    ChannelData(5, 439, 'ML', 439912500, 34988, 16, 9, 5, "DRF1268DS"),
                    ChannelData(6, 439, 'ML', 439962500, 34988, 16, 9, 5, "DRF1268DS"),
                    ChannelData(1, 781, 'MS', 439712500, 19667, 16, 8, 5, "DRF1268DS"),
                    ChannelData(2, 781, 'MS', 439762500, 19667, 16, 8, 5, "DRF1268DS"),
                    ChannelData(3, 781, 'MS', 439812500, 19667, 16, 8, 5, "DRF1268DS"),
                    ChannelData(4, 781, 'MS', 439862500, 19667, 16, 8, 5, "DRF1268DS"),
                    ChannelData(5, 781, 'MS', 439912500, 19667, 16, 8, 5, "DRF1268DS"),
                    ChannelData(6, 781, 'MS', 439962500, 19667, 16, 8, 5, "DRF1268DS"),
                    ChannelData(1, 1367, 'S', 439712500, 11236, 16, 7, 5, "DRF1268DS"),
                    ChannelData(2, 1367, 'S', 439762500, 11236, 16, 7, 5, "DRF1268DS"),
                    ChannelData(3, 1367, 'S', 439812500, 11236, 16, 7, 5, "DRF1268DS"),
                    ChannelData(4, 1367, 'S', 439862500, 11236, 16, 7, 5, "DRF1268DS"),
                    ChannelData(5, 1367, 'S', 439912500, 11236, 16, 7, 5, "DRF1268DS"),
                    ChannelData(6, 1367, 'S', 439962500, 11236, 16, 7, 5, "DRF1268DS")]
        # =========================      RF1276T      ==============================

        #  ======================
        #                     channel, datarate, freq, slopek, M, rffactor, rfBw, loramodem

        for channel in channels:
            cls.save_channel(channel)

    # BluetoothSerialPortData
    @classmethod
    def get_bluetooth_serial_ports(cls):
        cls.init()
        rows = cls.db.get_table_objects(BluetoothSerialPortData)
        return rows

    @classmethod
    def get_bluetooth_serial_port(cls, deviceBluetoothAddress):
        cls.init()
        sql = ("SELECT * FROM BluetoothSerialPortData WHERE DeviceBTAddress = '" + deviceBluetoothAddress + "'")
        rows = cls.db.get_table_objects_by_SQL(BluetoothSerialPortData, sql)
        return rows

    @classmethod
    def save_bluetooth_serial_port(cls, bluetoothSerialPortData):
        cls.init()
        rowid = cls.db.save_table_object(bluetoothSerialPortData)
        return rowid

    @classmethod
    def delete_bluetooth_serial_port(cls, deviceBluetoothAddress):
        cls.init()
        db = cls.db
        db.execute_SQL("DELETE FROM BluetoothSerialPortData WHERE DeviceBTAddress = '" + deviceBluetoothAddress + "'")
        return None
