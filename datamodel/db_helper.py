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
                     "(select sum(CASE WHEN MessageSubscriptionArchiveData.SendFailedDate is not null THEN NoOfSendTries ELSE NoOfSendTries-1 END) as NoOfSendTries from MessageSubscriptionArchiveData "
                     "join MessageBoxArchiveData on MessageSubscriptionArchiveData.MessageBoxId = MessageBoxArchiveData.OrigId "
                     "where MessageSubscriptionArchiveData.SentDate >= ? and MessageSubscriptionArchiveData.SentDate < ? and "
                     "MessageSubscriptionArchiveData.SubscriberTypeName = 'LORA' and MessageBoxArchiveData.MessageTypeName <> 'STATUS' "
                     "and (MessageSubscriptionArchiveData.AckReceivedDate is not null or MessageSubscriptionArchiveData.SendFailedDate is not null) "
                     "union "
                     "select sum(CASE WHEN MessageSubscriptionData.SendFailedDate is not null THEN NoOfSendTries ELSE NoOfSendTries-1 END) as NoOfSendTries from MessageSubscriptionData "
                     "join SubscriptionData ON MessageSubscriptionData.SubscriptionId = SubscriptionData.id "
                     "join SubscriberData ON SubscriberData.id = SubscriptionData.SubscriberId "
                     "join MessageBoxData on MessageSubscriptionData.MessageBoxId = MessageBoxData.Id "
                     "where MessageSubscriptionData.SentDate >= ? and MessageSubscriptionData.SentDate < ? and "
                     "SubscriberData.TypeName = 'LORA' and MessageBoxData.MessageTypeName <> 'STATUS' "
                     "and (MessageSubscriptionData.AckReceivedDate is not null or MessageSubscriptionData.SendFailedDate is not null));")

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
            # only archive messages that it is longer than 15 seconds ago they were sent
            # assume 15 seconds is long enough for all datarate settings
            fifteenSecondsAgo: datetime = datetime.now() - timedelta(seconds=15)
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
                   "((MessageSubscriptionData.NoOfSendTries >= %s AND MessageSubscriptionData.SentDate < ?) or MessageSubscriptionData.FindAdapterTries >= %s) "
                   "ORDER BY MessageBoxData.CreatedDate desc "
                   "LIMIT %s") % (maxRetries, maxRetries, limit)
            return cls.db.get_table_objects_by_SQL(MessageSubscriptionView, sql, (fifteenSecondsAgo,))
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
              "SportIdentSecond, SIStationNumber," \
              "SICardNumber2, SportIdentHour2, SportIdentMinute2, SportIdentSecond2, SIStationNumber2," \
              "LowBattery, ChecksumOK, CreatedDate) SELECT id, MessageData," \
              "PowerCycleCreated, MessageTypeName, InstanceName, MessageSubTypeName, MemoryAddress," \
              "SICardNumber, SIStationSerialNumber, SportIdentHour, SportIdentMinute," \
              "SportIdentSecond, SIStationNumber, " \
              "SICardNumber2, SportIdentHour2, SportIdentMinute2, SportIdentSecond2, SIStationNumber2," \
              "LowBattery, ChecksumOK, CreatedDate FROM " \
              "MessageBoxData WHERE Id = %s" % msgBoxId

        cls.db.execute_SQL(sql)
        cls.db.delete_table_object(MessageBoxData, msgBoxId)

    @classmethod
    def archive_message_box_without_subscriptions(cls):
        cls.init()
        sql = "INSERT INTO MessageBoxArchiveData (OrigId, MessageData," \
              "PowerCycleCreated, MessageTypeName, InstanceName, MessageSubTypeName, MemoryAddress," \
              "SICardNumber, SIStationSerialNumber, SportIdentHour, SportIdentMinute," \
              "SportIdentSecond, SIStationNumber, " \
              "SICardNumber2, SportIdentHour2, SportIdentMinute2, SportIdentSecond2, SIStationNumber2," \
              "LowBattery, ChecksumOK, CreatedDate) SELECT MessageBoxData.id, MessageData," \
              "PowerCycleCreated, MessageTypeName, InstanceName, MessageSubTypeName, MemoryAddress," \
              "SICardNumber, SIStationSerialNumber, SportIdentHour, SportIdentMinute," \
              "SportIdentSecond, SIStationNumber, " \
              "SICardNumber2, SportIdentHour2, SportIdentMinute2, SportIdentSecond2, SIStationNumber2," \
              "LowBattery, ChecksumOK, CreatedDate FROM " \
              "MessageBoxData LEFT JOIN MessageSubscriptionData ON MessageBoxData.id = " \
              "MessageSubscriptionData.MessageboxId WHERE MessageSubscriptionData.id is null"
        cls.db.execute_SQL(sql)
        sql = "DELETE FROM MessageBoxData WHERE id in (SELECT MessageBoxData.id FROM " \
              "MessageBoxData LEFT JOIN MessageSubscriptionData ON MessageBoxData.id = " \
              "MessageSubscriptionData.MessageboxId WHERE MessageSubscriptionData.id IS NULL)"
        cls.db.execute_SQL(sql)

    # RepeaterMessageBox
    #@classmethod
    #def create_repeater_message_box_data(cls, messageSource, messageTypeName, messageSubTypeName, instanceName, checksumOK,
    #                                     powerCycle, serialNumber, lowBattery, ackRequested, repeater, siPayloadData,
    #                                     messageID, data, rssiValue):
    #    rmbd = RepeaterMessageBoxData()
    #    rmbd.MessageData = data
    #    rmbd.MessageTypeName = messageTypeName
    #    rmbd.PowerCycleCreated = powerCycle
    #    rmbd.ChecksumOK = checksumOK
    #    rmbd.InstanceName = instanceName
    #    rmbd.MessageSubTypeName = messageSubTypeName
    #    rmbd.MessageSource = messageSource
    #    rmbd.SIStationSerialNumber = serialNumber
    #    rmbd.RSSIValue = rssiValue
    #    rmbd.NoOfTimesSeen = 1
    #    rmbd.NoOfTimesAckSeen = 0
    #    rmbd.SIStationNumber = None
    #    rmbd.SIStationSerialNumber = None
    #    rmbd.MessageID = messageID
    #    rmbd.LowBattery = lowBattery
    #    rmbd.AckRequested = ackRequested
    #    rmbd.RepeaterRequested = repeater

    #    if siPayloadData is not None:
    #        siMsg = SIMessage()
    #        siMsg.AddPayload(siPayloadData)
    #        rmbd.SICardNumber = siMsg.GetSICardNumber()
    #        rmbd.SportIdentHour = siMsg.GetHour()
    #        rmbd.SportIdentMinute = siMsg.GetMinute()
    #        rmbd.SportIdentSecond = siMsg.GetSeconds()
    #        rmbd.MemoryAddress = siMsg.GetBackupMemoryAddressAsInt()
    #        rmbd.SIStationNumber = siMsg.GetStationNumber()

    #    return rmbd

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
               "SICardNumber, SportIdentHour, SportIdentMinute, SportIdentSecond, SIStationNumber, "
               "SICardNumber2,SportIdentHour2, SportIdentMinute2, SportIdentSecond2, SIStationNumber2, "
               "MessageID, AckRequested, RepeaterRequested, NoOfTimesSeen, "
               "NoOfTimesAckSeen, Acked, AckedTime, MessageBoxId, RSSIValue, "
               "AckRSSIValue, AddedToMessageBoxTime, LastSeenTime, OrigCreatedDate, "
               "CreatedDate) SELECT NULL, "
               "id as OrigId, MessageData, MessageTypeName, PowerCycleCreated, "
               "InstanceName, MessageSubTypeName, ChecksumOK, MessageSource, "
               "SICardNumber, SportIdentHour, SportIdentMinute, SportIdentSecond, SIStationNumber, "
               "SICardNumber2,SportIdentHour2, SportIdentMinute2, SportIdentSecond2, SIStationNumber2, "
               "MessageID, AckRequested, RepeaterRequested, NoOfTimesSeen, "
               "NoOfTimesAckSeen, Acked, AckedTime, MessageBoxId, RSSIValue, "
               "AckRSSIValue, ? as AddedToMessageBoxTime, LastSeenTime, CreatedDate as OrigCreatedDate, "
               "? as CreatedDate "
               "FROM RepeaterMessageBoxData WHERE LastSeenTime < ?")
        cls.db.execute_SQL(sql, (datetime.now(), datetime.now(), fiveMinutesAgo))
        sql = "DELETE FROM RepeaterMessageBoxData WHERE LastSeenTime < ? "
        cls.db.execute_SQL(sql, (fiveMinutesAgo,))

    @classmethod
    def get_repeater_message_to_add(cls) -> RepeaterMessageBoxData | None:
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
    def get_lowest_messageboxdata_id(cls) -> int:
        cls.init()
        msgBoxId = cls.db.get_scalar_by_SQL("SELECT min(id) FROM MessageBoxData")
        if msgBoxId is None:
            return 18446744073709551615 # sqlite max
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
         ORDER BY (cast(TwelveHourTimer as integer) * 3600 + cast(TwentyFourHour as integer) * 43200), MessageBoxId;")

        testPunchesView = cls.db.get_table_objects_by_SQL(TestPunchView, sql)
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
        return None

    @classmethod
    def set_message_stat_uploaded(cls, messageStatId):
        cls.init()
        sql = "UPDATE MessageStatsData SET Uploaded = 1 WHERE Id = " + str(messageStatId)
        DatabaseHelper.WiRocLogger.debug("DatabaseHelper::set_message_stat_uploaded() 1")
        cls.db.execute_SQL(sql)
        DatabaseHelper.WiRocLogger.debug("DatabaseHelper::set_message_stat_uploaded() 2")

    # Channels
    @classmethod
    def get_channel(cls, channel: str, loraRange: str, loraModem: str) -> ChannelData:
        cls.init()
        sql = ("SELECT * FROM ChannelData WHERE Channel = '" + str(channel) +
               "' and LoraRange = '" + loraRange + "' and LoraModem = '" + loraModem + "'")
        rows = cls.db.get_table_objects_by_SQL(ChannelData, sql)
        if len(rows) >= 1:
            return rows[0]
        return None

    @classmethod
    def save_channel(cls, channel) -> None:
        cls.init()
        cls.db.save_table_object(channel, False)

    @classmethod
    def delete_channels(cls) -> None:
        cls.init()
        cls.db.execute_SQL("DELETE FROM ChannelData")

    @classmethod
    def get_channels_exists(cls) -> bool:
        cls.init()
        cnt = cls.db.get_scalar_by_SQL("SELECT count(*) FROM ChannelData")
        return cnt > 0

    @classmethod
    def add_default_channels(cls):
        cls.init()
        if not cls.get_channels_exists():
            channels = [ChannelData('1', 73, 'UL', 439712500, 12, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('2', 73, 'UL', 439762500,  12, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('3', 73, 'UL', 439812500, 12, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('4', 73, 'UL', 439862500,  12, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('5', 73, 'UL', 439912500,  12, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('6', 73, 'UL', 439962500,  12, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('1', 134, 'XL', 439712500,  11, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('2', 134, 'XL', 439762500,  11, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('3', 134, 'XL', 439812500,  11, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('4', 134, 'XL', 439862500, 11, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('5', 134, 'XL', 439912500, 11, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('6', 134, 'XL', 439962500, 11, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('1', 244, 'L', 439712500, 10, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('2', 244, 'L', 439762500, 10, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('3', 244, 'L', 439812500, 10, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('4', 244, 'L', 439862500, 10, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('5', 244, 'L', 439912500, 10, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('6', 244, 'L', 439962500, 10, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('1', 439, 'ML', 439712500, 9, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('2', 439, 'ML', 439762500, 9, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('3', 439, 'ML', 439812500,  9, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('4', 439, 'ML', 439862500,  9, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('5', 439, 'ML', 439912500, 9, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('6', 439, 'ML', 439962500, 9, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('1', 781, 'MS', 439712500, 8, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('2', 781, 'MS', 439762500, 8, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('3', 781, 'MS', 439812500, 8, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('4', 781, 'MS', 439862500, 8, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('5', 781, 'MS', 439912500, 8, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('6', 781, 'MS', 439962500, 8, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('1', 1367, 'S', 439712500, 7, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('2', 1367, 'S', 439762500, 7, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('3', 1367, 'S', 439812500, 7, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('4', 1367, 'S', 439862500, 7, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('5', 1367, 'S', 439912500, 7, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('6', 1367, 'S', 439962500, 7, 5, True, True, 8, "DRF1268DS"),

                        ChannelData('HAM1', 73, 'UL', 439712500, 12, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM2', 73, 'UL', 433787500, 12, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM3', 73, 'UL', 433837500, 12, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM4', 73, 'UL', 433887500, 12, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM5', 73, 'UL', 433937500, 12, 5, True, True, 8, "DRF1268DS"),

                        ChannelData('HAM1', 134, 'XL', 433737500, 11, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM2', 134, 'XL', 433787500, 11, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM3', 134, 'XL', 433837500, 11, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM4', 134, 'XL', 433887500, 11, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM5', 134, 'XL', 433937500, 11, 5, True, True, 8, "DRF1268DS"),

                        ChannelData('HAM1', 244, 'L', 433737500, 10, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM2', 244, 'L', 433787500, 10, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM3', 244, 'L', 433837500, 10, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM4', 244, 'L', 433887500, 10, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM5', 244, 'L', 433937500, 10, 5, True, True, 8, "DRF1268DS"),

                        ChannelData('HAM1', 439, 'ML', 433737500, 9, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM2', 439, 'ML', 433787500, 9, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM3', 439, 'ML', 433837500, 9, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM4', 439, 'ML', 433887500, 9, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM5', 439, 'ML', 433937500, 9, 5, True, True, 8, "DRF1268DS"),

                        ChannelData('HAM1', 781, 'MS', 433737500, 8, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM2', 781, 'MS', 433787500, 8, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM3', 781, 'MS', 433837500, 8, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM4', 781, 'MS', 433887500, 8, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM5', 781, 'MS', 433937500, 8, 5, True, True, 8, "DRF1268DS"),

                        ChannelData('HAM1', 1367, 'S', 433737500, 7, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM2', 1367, 'S', 433787500, 7, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM3', 1367, 'S', 433837500, 7, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM4', 1367, 'S', 433887500, 7, 5, True, True, 8, "DRF1268DS"),
                        ChannelData('HAM5', 1367, 'S', 433937500, 7, 5, True, True, 8, "DRF1268DS"),
                        # DRF1268DS Compatible 31khz bw modes
                        ChannelData('1', 73, 'UL', 439712500, 12, 7, False, True, 8,"RAK3172"),
                        ChannelData('2', 73, 'UL', 439762500, 12, 7, False, True, 8,"RAK3172"),
                        ChannelData('3', 73, 'UL', 439812500, 12, 7, False, True, 8,"RAK3172"),
                        ChannelData('4', 73, 'UL', 439862500, 12, 7, False, True, 8,"RAK3172"),
                        ChannelData('5', 73, 'UL', 439912500, 12, 7, False, True, 8,"RAK3172"),
                        ChannelData('6', 73, 'UL', 439962500, 12, 7, False, True, 8,"RAK3172"),
                        ChannelData('1', 134, 'XL', 439712500, 11, 7, False, True, 8,"RAK3172"),
                        ChannelData('2', 134, 'XL', 439762500, 11, 7, False, True, 8,"RAK3172"),
                        ChannelData('3', 134, 'XL', 439812500, 11, 7, False, True, 8,"RAK3172"),
                        ChannelData('4', 134, 'XL', 439862500, 11, 7, False, True, 8,"RAK3172"),
                        ChannelData('5', 134, 'XL', 439912500, 11, 7, False, True, 8,"RAK3172"),
                        ChannelData('6', 134, 'XL', 439962500, 11, 7, False, True, 8,"RAK3172"),
                        ChannelData('1', 244, 'L', 439712500, 10, 7, False, True, 8,"RAK3172"),
                        ChannelData('2', 244, 'L', 439762500, 10, 7, False, True, 8,"RAK3172"),
                        ChannelData('3', 244, 'L', 439812500, 10, 7, False, True, 8,"RAK3172"),
                        ChannelData('4', 244, 'L', 439862500, 10, 7, False, True, 8,"RAK3172"),
                        ChannelData('5', 244, 'L', 439912500, 10, 7, False, True, 8,"RAK3172"),
                        ChannelData('6', 244, 'L', 439962500, 10, 7, False, True, 8,"RAK3172"),
                        ChannelData('1', 439, 'ML', 439712500, 9, 7, False, True, 8,"RAK3172"),
                        ChannelData('2', 439, 'ML', 439762500, 9, 7, False, True, 8,"RAK3172"),
                        ChannelData('3', 439, 'ML', 439812500, 9, 7, False, True, 8,"RAK3172"),
                        ChannelData('4', 439, 'ML', 439862500, 9, 7, False, True, 8,"RAK3172"),
                        ChannelData('5', 439, 'ML', 439912500, 9, 7, False, True, 8,"RAK3172"),
                        ChannelData('6', 439, 'ML', 439962500, 9, 7, False, True, 8,"RAK3172"),
                        ChannelData('1', 781, 'MS', 439712500, 8, 7, False, True, 8,"RAK3172"),
                        ChannelData('2', 781, 'MS', 439762500, 8, 7, False, True, 8,"RAK3172"),
                        ChannelData('3', 781, 'MS', 439812500, 8, 7, False, True, 8,"RAK3172"),
                        ChannelData('4', 781, 'MS', 439862500, 8, 7, False, True, 8,"RAK3172"),
                        ChannelData('5', 781, 'MS', 439912500, 8, 7, False, True, 8,"RAK3172"),
                        ChannelData('6', 781, 'MS', 439962500, 8, 7, False, True, 8,"RAK3172"),
                        ChannelData('1', 1367, 'S', 439712500, 7, 7, False, True, 8,"RAK3172"),
                        ChannelData('2', 1367, 'S', 439762500, 7, 7, False, True, 8,"RAK3172"),
                        ChannelData('3', 1367, 'S', 439812500, 7, 7, False, True, 8,"RAK3172"),
                        ChannelData('4', 1367, 'S', 439862500, 7, 7, False, True, 8,"RAK3172"),
                        ChannelData('5', 1367, 'S', 439912500, 7, 7, False, True, 8,"RAK3172"),
                        ChannelData('6', 1367, 'S', 439962500, 7, 7, False, True, 8,"RAK3172"),

                        ChannelData('HAM1', 73, 'UL', 439712500, 12, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM2', 73, 'UL', 433787500, 12, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM3', 73, 'UL', 433837500, 12, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM4', 73, 'UL', 433887500, 12, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM5', 73, 'UL', 433937500, 12, 7, False, True, 8,"RAK3172"),

                        ChannelData('HAM1', 134, 'XL', 433737500, 11, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM2', 134, 'XL', 433787500, 11, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM3', 134, 'XL', 433837500, 11, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM4', 134, 'XL', 433887500, 11, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM5', 134, 'XL', 433937500, 11, 7, False, True, 8,"RAK3172"),

                        ChannelData('HAM1', 244, 'L', 433737500, 10, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM2', 244, 'L', 433787500, 10, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM3', 244, 'L', 433837500, 10, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM4', 244, 'L', 433887500, 10, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM5', 244, 'L', 433937500, 10, 7, False, True, 8,"RAK3172"),

                        ChannelData('HAM1', 439, 'ML', 433737500, 9, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM2', 439, 'ML', 433787500, 9, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM3', 439, 'ML', 433837500, 9, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM4', 439, 'ML', 433887500, 9, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM5', 439, 'ML', 433937500, 9, 7, False, True, 8,"RAK3172"),

                        ChannelData('HAM1', 781, 'MS', 433737500, 8, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM2', 781, 'MS', 433787500, 8, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM3', 781, 'MS', 433837500, 8, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM4', 781, 'MS', 433887500, 8, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM5', 781, 'MS', 433937500, 8, 7, False, True, 8,"RAK3172"),

                        ChannelData('HAM1', 1367, 'S', 433737500, 7, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM2', 1367, 'S', 433787500, 7, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM3', 1367, 'S', 433837500, 7, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM4', 1367, 'S', 433887500, 7, 7, False, True, 8,"RAK3172"),
                        ChannelData('HAM5', 1367, 'S', 433937500, 7, 7, False, True, 8,"RAK3172"),

                        # RfBW = 4 => 10.4 kHz
                        ChannelData('1', 73, 'UL', 439700000, 10, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('2', 73, 'UL', 439725000, 10, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('3', 73, 'UL', 439750000, 10, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('4', 73, 'UL', 439775000, 10, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('5', 73, 'UL', 439800000, 10, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('6', 73, 'UL', 439825000, 10, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('7', 73, 'UL', 439850000, 10, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('8', 73, 'UL', 439875000, 10, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('9', 73, 'UL', 439900000, 10, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('10', 73, 'UL', 439925000, 10, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('11', 73, 'UL', 439950000, 10, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('12', 73, 'UL', 439975000, 10, 4, False, True, 8,"RAK3172-2"),

                        ChannelData('1', 134, 'XL', 439700000, 9, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('2', 134, 'XL', 439725000, 9, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('3', 134, 'XL', 439750000, 9, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('4', 134, 'XL', 439775000, 9, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('5', 134, 'XL', 439800000, 9, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('6', 134, 'XL', 439825000, 9, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('7', 134, 'XL', 439850000, 9, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('8', 134, 'XL', 439875000, 9, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('9', 134, 'XL', 439900000, 9, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('10', 134, 'XL', 439925000, 9, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('11', 134, 'XL', 439950000, 9, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('12', 134, 'XL', 439975000, 9, 4, False, True, 8,"RAK3172-2"),

                        ChannelData('1', 244, 'L', 439700000, 8, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('2', 244, 'L', 439725000, 8, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('3', 244, 'L', 439750000, 8, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('4', 244, 'L', 439775000, 8, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('5', 244, 'L', 439800000, 8, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('6', 244, 'L', 439825000, 8, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('7', 244, 'L', 439850000, 8, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('8', 244, 'L', 439875000, 8, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('9', 244, 'L', 439900000, 8, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('10', 244, 'L', 439925000, 8, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('11', 244, 'L', 439950000, 8, 4, False, True, 8,"RAK3172-2"),
                        ChannelData('12', 244, 'L', 439975000, 8, 4, False, True, 8,"RAK3172-2"),

                        ChannelData('1', 439, 'ML', 439700000, 7, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('2', 439, 'ML', 439725000, 7, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('3', 439, 'ML', 439750000, 7, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('4', 439, 'ML', 439775000, 7, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('5', 439, 'ML', 439800000, 7, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('6', 439, 'ML', 439825000, 7, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('7', 439, 'ML', 439850000, 7, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('8', 439, 'ML', 439875000, 7, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('9', 439, 'ML', 439900000, 7, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('10', 439, 'ML', 439925000, 7, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('11', 439, 'ML', 439950000, 7, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('12', 439, 'ML', 439975000, 7, 4, False, False, 8,"RAK3172-2"),

                        ChannelData('1', 781, 'MS', 439700000, 6, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('2', 781, 'MS', 439725000, 6, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('3', 781, 'MS', 439750000, 6, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('4', 781, 'MS', 439775000, 6, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('5', 781, 'MS', 439800000, 6, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('6', 781, 'MS', 439825000, 6, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('7', 781, 'MS', 439850000, 6, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('8', 781, 'MS', 439875000, 6, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('9', 781, 'MS', 439900000, 6, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('10', 781, 'MS', 439925000, 6, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('11', 781, 'MS', 439950000, 6, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('12', 781, 'MS', 439975000, 6, 4, False, False, 8,"RAK3172-2"),

                        ChannelData('1', 1367, 'S', 439700000, 5, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('2', 1367, 'S', 439725000, 5, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('3', 1367, 'S', 439750000, 5, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('4', 1367, 'S', 439775000, 5, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('5', 1367, 'S', 439800000, 5, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('6', 1367, 'S', 439825000, 5, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('7', 1367, 'S', 439850000, 5, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('8', 1367, 'S', 439725000, 5, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('9', 1367, 'S', 439900000, 5, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('10', 1367, 'S', 439925000, 5, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('11', 1367, 'S', 439950000, 5, 4, False, False, 8,"RAK3172-2"),
                        ChannelData('12', 1367, 'S', 439975000, 5, 4, False, False, 8,"RAK3172-2"),

                        ChannelData('HAM1', 73, 'UL', 439712500, 10, 4, False, True, 8,"RAK3172"),
                        ChannelData('HAM2', 73, 'UL', 433787500, 10, 4, False, True, 8,"RAK3172"),
                        ChannelData('HAM3', 73, 'UL', 433837500, 10, 4, False, True, 8,"RAK3172"),
                        ChannelData('HAM4', 73, 'UL', 433887500, 10, 4, False, True, 8,"RAK3172"),
                        ChannelData('HAM5', 73, 'UL', 433937500, 10, 4, False, True, 8,"RAK3172"),

                        ChannelData('HAM1', 134, 'XL', 433737500, 9, 4, False, True, 8,"RAK3172"),
                        ChannelData('HAM2', 134, 'XL', 433787500, 9, 4, False, True, 8,"RAK3172"),
                        ChannelData('HAM3', 134, 'XL', 433837500, 9, 4, False, True, 8,"RAK3172"),
                        ChannelData('HAM4', 134, 'XL', 433887500, 9, 4, False, True, 8,"RAK3172"),
                        ChannelData('HAM5', 134, 'XL', 433937500, 9, 4, False, True, 8,"RAK3172"),

                        ChannelData('HAM1', 244, 'L', 433737500, 8, 4, False, True, 8,"RAK3172"),
                        ChannelData('HAM2', 244, 'L', 433787500, 8, 4, False, True, 8,"RAK3172"),
                        ChannelData('HAM3', 244, 'L', 433837500, 8, 4, False, True, 8,"RAK3172"),
                        ChannelData('HAM4', 244, 'L', 433887500, 8, 4, False, True, 8,"RAK3172"),
                        ChannelData('HAM5', 244, 'L', 433937500, 8, 4, False, True, 8,"RAK3172"),

                        ChannelData('HAM1', 439, 'ML', 433737500, 7, 4, False, False, 8,"RAK3172"),
                        ChannelData('HAM2', 439, 'ML', 433787500, 7, 4, False, False, 8,"RAK3172"),
                        ChannelData('HAM3', 439, 'ML', 433837500, 7, 4, False, False, 8,"RAK3172"),
                        ChannelData('HAM4', 439, 'ML', 433887500, 7, 4, False, False, 8,"RAK3172"),
                        ChannelData('HAM5', 439, 'ML', 433937500, 7, 4, False, False, 8,"RAK3172"),

                        ChannelData('HAM1', 781, 'MS', 433737500, 6, 4, False, False, 8,"RAK3172"),
                        ChannelData('HAM2', 781, 'MS', 433787500, 6, 4, False, False, 8,"RAK3172"),
                        ChannelData('HAM3', 781, 'MS', 433837500, 6, 4, False, False, 8,"RAK3172"),
                        ChannelData('HAM4', 781, 'MS', 433887500, 6, 4, False, False, 8,"RAK3172"),
                        ChannelData('HAM5', 781, 'MS', 433937500, 6, 4, False, False, 8,"RAK3172"),

                        ChannelData('HAM1', 1367, 'S', 433737500, 5, 4, False, False, 8,"RAK3172"),
                        ChannelData('HAM2', 1367, 'S', 433787500, 5, 4, False, False, 8,"RAK3172"),
                        ChannelData('HAM3', 1367, 'S', 433837500, 5, 4, False, False, 8,"RAK3172"),
                        ChannelData('HAM4', 1367, 'S', 433887500, 5, 4, False, False, 8,"RAK3172"),
                        ChannelData('HAM5', 1367, 'S', 433937500, 5, 4, False, False, 8,"RAK3172"),

                        ]

            for channel in channels:
                cls.save_channel(channel)
            DatabaseHelper.WiRocLogger.debug("DatabaseHelper::add_default_channels() Channels added")
        else:
            DatabaseHelper.WiRocLogger.debug("DatabaseHelper::add_default_channels() Channels already exists")

    @classmethod
    def get_timeonair(cls, spreadingFactor: int, rfBw: int, codeRate: int, lowDatarateOptimize: bool, header: bool, CRCOn: bool, DRF1268DSCompatMode: bool, preambleLength: int, loraModule: str) -> TimeOnAirData | None:
        cls.init()
        sql = (f"SELECT * FROM TimeOnAirData WHERE SpreadingFactor = {spreadingFactor} and RfBw = {rfBw} and CodeRate = {codeRate} and LowDatarateOptimize = {lowDatarateOptimize} "
               f"and header = {header} and CRCOn = {CRCOn} and DRF1268DSCompatMode = {DRF1268DSCompatMode} and PreambleLength = {preambleLength} and LoraModem = '" + loraModule + "'")
        rows = cls.db.get_table_objects_by_SQL(ChannelData, sql)
        if len(rows) >= 1:
            return rows[0]
        return None

    @classmethod
    def save_timeonair(cls, timeonair) -> None:
        cls.init()
        cls.db.save_table_object(timeonair, False)

    @classmethod
    def get_timeonair_exists(cls) -> bool:
        cls.init()
        cnt = cls.db.get_scalar_by_SQL("SELECT count(*) FROM TimeOnAirData")
        return cnt > 0

    @classmethod
    def add_timeonair(cls):
        cls.init()
        if not cls.get_timeonair_exists():
            # RfBW = 5 => 31,25 kHz on DRF1268DS, CodingRate 1 = 4/5
            timeOnAirDatas = [
                        # DRF
                        TimeOnAirData(12, 5, 1, True, True, True, 8, True, "DRF1268DS", 5280, 6590, 3960,5280, 4620),
                        TimeOnAirData(11, 5, 1, True, True, True, 8, True, "DRF1268DS", 2640, 3620, 1980, 2640, 2310),
                        TimeOnAirData(10, 5, 1, True, True, True, 8, True, "DRF1268DS", 1480, 1970, 1160, 1480, 1320),
                        TimeOnAirData(9, 5, 1, True, True, True, 8, True, "DRF1268DS", 742, 1070, 578, 824, 660),
                        TimeOnAirData(8, 5, 1, True, True, True, 8, True, "DRF1268DS", 412, 576, 330, 453, 371),
                        TimeOnAirData(7, 5, 1, True, True, True, 8, True, "DRF1268DS", 247, 329, 165,247, 206),
                        # CodingRate 2 = 4/6
                        TimeOnAirData(12, 5, 2, True, True, True, 8, True, "DRF1268DS", 5800, 7370, 4230, 5800, 5010),
                        TimeOnAirData(11, 5, 2, True, True, True, 8, True, "DRF1268DS", 2900, 4080, 2110, 2900, 2510),
                        TimeOnAirData(10, 5, 2, True, True, True, 8, True, "DRF1268DS", 1650, 2240, 1250, 1650, 1450),
                        TimeOnAirData(9, 5, 2, True, True, True, 8, True, "DRF1268DS", 824, 1220, 627, 922, 725),
                        TimeOnAirData(8, 5, 2, True, True, True, 8, True, "DRF1268DS", 461, 658, 363, 510, 412),
                        TimeOnAirData(7, 5, 2, True, True, True, 8, True, "DRF1268DS", 280, 378, 182, 280, 231),
                        # CodingRate 3 = 4/7
                        TimeOnAirData(12, 5, 3, True, True, True, 8, True, "DRF1268DS", 6320, 8160, 4490, 6320, 5410),
                        TimeOnAirData(11, 5, 3, True, True, True, 8, True, "DRF1268DS", 3160, 4540, 2240, 3160, 2700),
                        TimeOnAirData(10, 5, 3, True, True, True, 8, True, "DRF1268DS", 1810, 2500, 1350, 1810, 1580),
                        TimeOnAirData(9, 5, 3, True, True, True, 8, True, "DRF1268DS", 906, 1360, 676, 1020, 791),
                        TimeOnAirData(8, 5, 3, True, True, True, 8, True, "DRF1268DS", 510, 740, 396, 568, 453),
                        TimeOnAirData(7, 5, 3, True, True, True, 8, True, "DRF1268DS", 313, 427, 198, 313, 255),
                        # CodingRate 4 = 4/8
                        TimeOnAirData(12, 5, 4, True, True, True, 8, True, "DRF1268DS", 6850, 8950, 4750, 6850, 5800),
                        TimeOnAirData(11, 5, 4, True, True, True, 8, True, "DRF1268DS", 3420, 5000, 2380, 3420, 2900),
                        TimeOnAirData(10, 5, 4, True, True, True, 8, True, "DRF1268DS", 1970, 2760, 1450, 1970, 1710),
                        TimeOnAirData(9, 5, 4, True, True, True, 8, True, "DRF1268DS", 988, 1510, 725, 1120, 857),
                        TimeOnAirData(8, 5, 4, True, True, True, 8, True, "DRF1268DS", 560, 822, 428, 625, 494),
                        TimeOnAirData(7, 5, 4, True, True, True, 8, True, "DRF1268DS", 346, 477, 214, 346, 280),

                        # RAK3172 Compat mode
                        # RfBW = 7 => 31,25 kHz on RAK3172, CodingRate 0 = 4/4
                        TimeOnAirData(12, 7, 0, True, True, False, 8, True, "RAK3172", 4620, 6590, 3310, 4620, 3960),
                        TimeOnAirData(11, 7, 0, True, True, False, 8, True, "RAK3172", 2310, 3290, 1980, 2310, 1980),
                        TimeOnAirData(10, 7, 0, True, True, False, 8, True, "RAK3172", 1160, 1810, 992, 1320, 1160),
                        TimeOnAirData(9, 7, 0, True, True, False, 8, True, "RAK3172", 660, 988, 496, 660, 578),
                        TimeOnAirData(8, 7, 0, True, True, False, 8, True, "RAK3172", 371, 576, 289, 371, 330),
                        TimeOnAirData(7, 7, 0, True, True, False, 8, True, "RAK3172", 206, 288, 145, 206, 165),

                        # RfBW = 7 => 31,25 kHz on RAK3172, CodingRate 1 = 4/5
                        TimeOnAirData(12, 7, 1, True, True, False, 8,True, "RAK3172", 4620, 6590, 3960, 4620, 3960),
                        TimeOnAirData(11, 7, 1, True, True, False, 8,True, "RAK3172", 2640, 3290, 1980, 2640, 2310),
                        TimeOnAirData(10, 7, 1, True, True, False, 8,True, "RAK3172", 1320, 1810, 992, 1320, 1160),
                        TimeOnAirData(9, 7, 1, True, True, False, 8,True, "RAK3172", 742, 988, 496, 742, 660),
                        TimeOnAirData(8, 7, 1, True, True, False, 8,True, "RAK3172", 412, 576, 289, 412, 330),
                        TimeOnAirData(7, 7, 1, True, True, False, 8,True, "RAK3172", 227, 329, 165, 227, 186),
                        # RfBW = 7 => 31,25 kHz on RAK3172, CodingRate 2 = 4/6
                        TimeOnAirData(12, 7, 2, True, True, False, 8, True, "RAK3172", 5010, 7370, 4230, 5010, 4230),
                        TimeOnAirData(11, 7, 2, True, True, False, 8, True, "RAK3172", 2900, 3690, 2110, 2900, 2510),
                        TimeOnAirData(10, 7, 2, True, True, False, 8, True, "RAK3172", 1450, 2040, 1060, 1450, 1250),
                        TimeOnAirData(9, 7, 2, True, True, False, 8, True, "RAK3172", 824, 1120, 529, 824, 725),
                        TimeOnAirData(8, 7, 2, True, True, False, 8, True, "RAK3172", 461, 658, 314, 461, 363),
                        TimeOnAirData(7, 7, 2, True, True, False, 8, True, "RAK3172", 255, 378, 182, 255, 206),
                        # RfBW = 7 => 31,25 kHz on RAK3172, CodingRate 3 = 4/7
                        TimeOnAirData(12, 7, 3, True, True, False, 8, True, "RAK3172", 5410, 8160, 4490, 5410, 4490),
                        TimeOnAirData(11, 7, 3, True, True, False, 8, True, "RAK3172", 3160, 4080, 2240, 3160, 2700),
                        TimeOnAirData(10, 7, 3, True, True, False, 8, True, "RAK3172", 1580, 2270, 1120, 1580, 1350),
                        TimeOnAirData(9, 7, 3, True, True, False, 8, True, "RAK3172", 906, 1250, 562, 906, 791),
                        TimeOnAirData(8, 7, 3, True, True, False, 8, True, "RAK3172", 510, 740, 338, 510, 396),
                        TimeOnAirData(7, 7, 3, True, True, False, 8, True, "RAK3172", 284, 427, 198, 284, 227),
                        # RfBW = 7 => 31,25 kHz on RAK3172, CodingRate 4 = 4/8
                        TimeOnAirData(12, 7, 4, True, True, False, 8, True, "RAK3172", 5800, 8950, 4750, 5800, 4750),
                        TimeOnAirData(11, 7, 4, True, True, False, 8, True, "RAK3172", 3420, 4470, 2380, 3420, 2900),
                        TimeOnAirData(10, 7, 4, True, True, False, 8, True, "RAK3172", 1710, 2500, 1190, 1710, 1450),
                        TimeOnAirData(9, 7, 4, True, True, False, 8, True, "RAK3172", 988, 1380, 594, 988, 857),
                        TimeOnAirData(8, 7, 4, True, True, False, 8, True, "RAK3172", 560, 822, 363, 560, 428),
                        TimeOnAirData(7, 7, 4, True, True, False, 8, True, "RAK3172", 313, 477, 214, 313, 247),

                        # Non compat mode
                        # RfBW = 4 => 10.4 kHz on RAK3172, CodingRate 0=4/4
                        # recommended to no use LDO for spreadingfactor 5,6,7 so maybe change that...
                        TimeOnAirData(10, 4, 0, True, True, False, 8, False, "RAK3172", 3470, 4940, 2970, 3470, 2970),
                        TimeOnAirData(9, 4, 0, True, True, False, 8, False, "RAK3172", 1980, 2470, 1490, 1980, 1730),
                        TimeOnAirData(8, 4, 0, True, True, False, 8, False, "RAK3172", 990, 1480, 744, 1110, 867),
                        #TimeOnAirData(7, 4, 0, True, True, False, 8, False, "RAK3172", 556, 802, 434, 618, 495),
                        #TimeOnAirData(6, 4, 0, True, True, False, 8, False, "RAK3172", 321, 475, 229, 352, 291),
                        #TimeOnAirData(5, 4, 0, True, True, False, 8, False, "RAK3172", 192, 299, 130, 207, 161),
                        TimeOnAirData(7, 4, 0, False, True, False, 8, False, "RAK3172", 495, 679, 434, 495, 434),
                        TimeOnAirData(6, 4, 0, False, True, False, 8, False, "RAK3172", 260, 383, 229, 291, 229),
                        TimeOnAirData(5, 4, 0, False, True, False, 8, False, "RAK3172", 145, 207, 115, 161, 130),

                        # CodingRate 1=4/5
                        TimeOnAirData(10, 4, 1, True, True, False, 8, False, "RAK3172", 3960, 5430, 2970, 3960, 3470),
                        TimeOnAirData(9, 4, 1, True, True, False, 8, False, "RAK3172", 1980, 2960, 1490, 2220, 1730),
                        TimeOnAirData(8, 4, 1, True, True, False, 8, False, "RAK3172", 1110, 1600, 867, 1230, 990),
                        TimeOnAirData(7, 4, 1, False, True, False, 8, False, "RAK3172", 556, 741, 372, 556, 495),
                        TimeOnAirData(6, 4, 1, False, True, False, 8, False, "RAK3172", 291, 414, 229, 321, 260),
                        TimeOnAirData(5, 4, 1, False, True, False, 8, False, "RAK3172", 161, 238, 115, 176, 146),

                        # CodingRate 2=4/6
                        TimeOnAirData(10, 4, 2, True, True, False, 8, False, "RAK3172", 4350, 6120, 3170, 4350, 3760),
                        TimeOnAirData(9, 4, 2, True, True, False, 8, False, "RAK3172", 2170, 3350, 1590, 2470, 1880),
                        TimeOnAirData(8, 4, 2, True, True, False, 8, False, "RAK3172", 1230, 1820, 940, 1380, 1090),
                        TimeOnAirData(7, 4, 2, False, True, False, 8, False, "RAK3172", 618, 839, 397, 618, 544),
                        TimeOnAirData(6, 4, 2, False, True, False, 8, False, "RAK3172", 321, 469, 248, 358, 285),
                        TimeOnAirData(5, 4, 2, False, True, False, 8, False, "RAK3172", 179, 271, 124, 198, 161),

                        # CodingRate 3=4/7
                        TimeOnAirData(10, 4, 3, True, True, False, 8, False, "RAK3172", 4740, 6810, 3370, 4740, 4050),
                        TimeOnAirData(9, 4, 3, True, True, False, 8, False, "RAK3172", 2370, 3750, 1680, 2720, 2030),
                        TimeOnAirData(8, 4, 3, True, True, False, 8, False, "RAK3172", 1360, 2050, 1010, 1530, 1190),
                        #TimeOnAirData(7, 4, 3, True, True, False, 8, False, "RAK3172", 765, 1190, 507, 851, 679),
                        #TimeOnAirData(6, 4, 3, True, True, False, 8, False, "RAK3172", 481, 739, 309, 481, 395),
                        #TimeOnAirData(5, 4, 3, True, True, False, 8, False, "RAK3172", 284, 456, 176, 305, 241),
                        TimeOnAirData(7, 4, 3, False, True, False, 8, False, "RAK3172", 679, 937, 421, 679, 593),
                        TimeOnAirData(6, 4, 3, False, True, False, 8, False, "RAK3172", 352, 524, 266, 395, 309),
                        TimeOnAirData(5, 4, 3, False, True, False, 8, False, "RAK3172", 198, 305, 133, 219, 176),

                        # CodingRate 4=4/8
                        TimeOnAirData(10, 4, 4, True, True, False, 8, False, "RAK3172", 5140, 7500, 3560, 5140, 4350),
                        TimeOnAirData(9, 4, 4, True, True, False, 8, False, "RAK3172", 2570, 4140, 1780, 2960, 2170),
                        TimeOnAirData(8, 4, 4, True, True, False, 8, False, "RAK3172", 1480, 2270, 1090, 1680, 1280),
                        #TimeOnAirData(7, 4, 4, True, True, False, 8, False, "RAK3172", 839, 1330, 544, 937, 741),
                        #TimeOnAirData(6, 4, 4, True, True, False, 8, False, "RAK3172", 530, 825, 334, 530, 432),
                        #TimeOnAirData(5, 4, 4, True, True, False, 8, False, "RAK3172", 315, 511, 176, 339, 265),
                        TimeOnAirData(7, 4, 4, False, True, False, 8, False, "RAK3172", 740, 1040, 446, 741, 642),
                        TimeOnAirData(6, 4, 4, False, True, False, 8, False, "RAK3172", 383, 579, 284, 432, 334),
                        TimeOnAirData(5, 4, 4, False, True, False, 8, False, "RAK3172", 216, 339, 142, 241, 192),

                        # Fixed length, no header mode, CodingRate 0
                        TimeOnAirData(11, 4, 0, True, False, False, 8, False, "RAK3172", 5950, None, 4960, None, 4960),
                        TimeOnAirData(10, 4, 0, True, False, False, 8, False, "RAK3172", 2970, None, 2480, None, 2970),
                        TimeOnAirData(9, 4, 0, True, False, False, 8, False, "RAK3172", 1730, None, 1240, None, 1730),
                        TimeOnAirData(8, 4, 0, True, False, False, 8, False, "RAK3172", 867, None, 621, None, 867),
                        #TimeOnAirData(7, 4, 0, True, False, False, 8, False, "RAK3172", 495, None, 372, None, 495),
                        #TimeOnAirData(6, 4, 0, True, False, False, 8, False, "RAK3172", 291, None, 199, None, 291),
                        #TimeOnAirData(5, 4, 0, True, False, False, 8, False, "RAK3172", 176, None, 115, None, 161),
                        TimeOnAirData(7, 4, 0, False, False, False, 8, False, "RAK3172", 434, None, 311, None, 434),
                        TimeOnAirData(6, 4, 0, False, False, False, 8, False, "RAK3172", 229, None, 168, None, 229),
                        TimeOnAirData(5, 4, 0, False, False, False, 8, False, "RAK3172", 130, None, 99, None, 130),

                # BW 10kHz: (fixed lenght... 44.76bps 166.8dB) 81 bps 164.3dB, 146.48 bps 161.8 dB, 260.42 bps 159.3dB, 455.74bps 156.8dB, 781.27bps 154.3dB, 1302.1bps 151.8dB
                        # BW 31kHz:                                    73 bps 164.6dB, 134.27 bps 162.1 dB, 244.14 bps 159.6dB, 439.45bps 157.1dB, 781.25bps 154.6dB, 1367.1bps 152.1dB
                    ]

            for timeOnAirData in timeOnAirDatas:
                cls.save_timeonair(timeOnAirData)
            DatabaseHelper.WiRocLogger.debug("DatabaseHelper::add_timeonair() TimeOnAirData added")
        else:
            DatabaseHelper.WiRocLogger.debug("DatabaseHelper::add_timeonair() TimeOnAirData already exists")

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
