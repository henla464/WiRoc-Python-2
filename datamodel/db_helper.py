__author__ = 'henla464'

from datamodel.datamodel import *
from databaselib.db import DB
from databaselib.datamapping import DataMapping
from datetime import timedelta, datetime


class DatabaseHelper:
    db = DB("WiRoc.db", DataMapping())

    @classmethod
    def ensure_tables_created(cls):
        logging.debug("DatabaseHelper::ensure_tables_created()")
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

    @classmethod
    def drop_all_tables(cls):
        logging.debug("DatabaseHelper::drop_all_tables()")
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

    @classmethod
    def truncate_setup_tables(cls):
        logging.debug("DatabaseHelper::truncate_setup_tables()")
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
        db = cls.db
        db.execute_SQL("DELETE FROM BlenoPunchData")
        db.execute_SQL("DELETE FROM MessageSubscriptionArchiveData")
        db.execute_SQL("DELETE FROM MessageSubscriptionData")
        db.execute_SQL("DELETE FROM MessageBoxArchiveData")
        db.execute_SQL("DELETE FROM MessageBoxData")
        db.execute_SQL("DELETE FROM TestPunchData")

#Settings
    @classmethod
    def save_setting(cls, settingData):
        sd = cls.get_setting_by_key(settingData.Key)
        if sd is None:
            sd = cls.db.save_table_object(settingData, True)
        else:
            sd.Value = settingData.Value
            sd = cls.db.save_table_object(sd, True)
        return sd

    @classmethod
    def get_setting(cls, id):
        sd = cls.db.get_table_object(SettingData, str(id))
        return sd

    @classmethod
    def get_settings(cls):
        rows = cls.db.get_table_objects(SettingData)
        return rows

    @classmethod
    def get_setting_by_key(cls, key):
        row_list = cls.db.get_table_objects_by_SQL(SettingData, "SELECT * FROM SettingData WHERE Key = '" + key + "'")
        if len(row_list) == 0:
            return None
        return row_list[0]

#Subscriber
    @classmethod
    def save_subscriber(cls, subscriberData):
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
        rows = cls.db.get_table_objects_by_SQL(SubscriberView, "SELECT "
            "SubscriberData.id, SubscriberData.TypeName, SubscriberData.InstanceName, "
            "SubscriptionData.Enabled, MsgIn.Name MessageInName, MsgOut.Name MessageOutName, "
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
        rows = cls.db.get_table_objects_by_SQL(SubscriberView, "SELECT "
            "SubscriberData.id, SubscriberData.TypeName, SubscriberData.InstanceName, "
            "SubscriptionData.Enabled, MsgIn.Name MessageInName, MsgOut.Name MessageOutName, "
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
    def get_message_type(cls, messageTypeName):
        sql = "SELECT * FROM MessageTypeData WHERE Name = '" + messageTypeName + "'"
        rows = cls.db.get_table_objects_by_SQL(MessageTypeData, sql)
        if len(rows) >= 1:
            return rows[0]
        return None

    @classmethod
    def save_message_type(cls, messageTypeData):
        rows = cls.db.get_table_objects_by_SQL(MessageTypeData, "SELECT * FROM MessageTypeData WHERE Name = '" +
                                           messageTypeData.Name + "'")
        if len(rows) == 0:
            return cls.db.save_table_object(messageTypeData, False)
        else:
            # nothing to update
            return rows[0].id

#Transforms

    @classmethod
    def save_transform(cls, transformData):
        rows = cls.db.get_table_objects_by_SQL(TransformData, "SELECT * FROM TransformData WHERE Name = '" +
                                           transformData.Name + "'")
        if len(rows) > 0:
            transformData.id = rows[0].id
        return cls.db.save_table_object(transformData, False)

    @classmethod
    def set_transform_enabled(cls, enabled, transformName):
        dbValue = DataMapping.get_database_value(enabled)
        sql = ("UPDATE TransformData SET Enabled = " + str(dbValue) + " " +
               "WHERE TransformData.Name = '" + transformName + "'")
        logging.debug(sql)
        cls.db.execute_SQL(sql)

#Subscriptions
    @classmethod
    def save_subscription(cls, subscriptionData):
        rows = cls.db.get_table_objects_by_SQL(SubscriptionData, ("SELECT * FROM SubscriptionData WHERE "
                                           "SubscriberId = " + str(subscriptionData.SubscriberId) +
                                           " and TransformId = " + str(subscriptionData.TransformId)))
        if len(rows) > 0:
            subscriptionData.id = rows[0].id
        return cls.db.save_table_object(subscriptionData, False)

    @classmethod
    def get_subscriptions_by_input_message_type_id(cls, messageTypeId):
        sql = ("SELECT SubscriptionData.* FROM TransformData JOIN SubscriptionData "
               "ON TransformData.id = SubscriptionData.TransformId "
               "WHERE TransformData.Enabled = 1 AND SubscriptionData.Enabled = 1 AND "
               "InputMessageTypeID = " + str(messageTypeId))
        rows = cls.db.get_table_objects_by_SQL(SubscriptionData, sql)
        return rows

    @classmethod
    def update_subscriptions(cls, enabled, deleteAfterSent, subscriberTypeName):
        sql = ("UPDATE SubscriptionData SET Enabled = " + str(1 if enabled else 0) + ", "
               "DeleteAfterSent = " + str(1 if deleteAfterSent else 0) + " WHERE SubscriberId IN "
               "(SELECT id from SubscriberData WHERE SubscriberData.TypeName = '" + str(subscriberTypeName) + "')")
        cls.db.execute_SQL(sql)


#MessageSubscriptions
    @classmethod
    def get_no_of_message_subscriptions_by_message_box_id(cls, msgBoxId):
        sql = "SELECT count(*) FROM MessageSubscriptionData WHERE MessageBoxId = %s" %(msgBoxId)
        no = cls.db.get_scalar_by_SQL(sql)
        return no

    @classmethod
    def update_customdata(cls, subscriptionId, customData):
        sql = "UPDATE MessageSubscriptionData SET CustomData = '%s' WHERE id = %s" % (customData, subscriptionId)
        cls.db.execute_SQL(sql)

    @classmethod
    def save_message_subscription(cls, messageSubscription):
        cls.db.save_table_object(messageSubscription, False)

    @classmethod
    def archive_message_subscription_view_after_sent(cls, messageSubscriptionView):
        msa = MessageSubscriptionArchiveData()
        msa.OrigId = messageSubscriptionView.id
        msa.CustomData = messageSubscriptionView.CustomData
        msa.SentDate = datetime.now()
        msa.NoOfSendTries = messageSubscriptionView.NoOfSendTries + 1
        msa.FindAdapterTryDate = messageSubscriptionView.FindAdapterTryDate
        msa.FindAdapterTries = messageSubscriptionView.FindAdapterTries
        msa.SendFailedDate = messageSubscriptionView.SendFailedDate
        msa.AckReceivedDate = messageSubscriptionView.AckReceivedDate
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
        msa = MessageSubscriptionArchiveData()
        msa.OrigId = messageSubscriptionView.id
        msa.CustomData = messageSubscriptionView.CustomData
        msa.SentDate = messageSubscriptionView.SentDate
        msa.SendFailedDate = messageSubscriptionView.SendFailedDate
        msa.FindAdapterTryDate = messageSubscriptionView.FindAdapterTryDate
        msa.FindAdapterTries = messageSubscriptionView.FindAdapterTries
        msa.NoOfSendTries = messageSubscriptionView.NoOfSendTries
        msa.AckReceivedDate = messageSubscriptionView.AckReceivedDate
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
    def increment_send_tries_and_set_sent_date(cls, messageSubscriptionView):
        msa = cls.db.get_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        msa.SentDate = datetime.now()
        msa.NoOfSendTries = msa.NoOfSendTries + 1
        msa.FindAdapterTryDate = None
        msa.FindAdapterTries = 0
        cls.db.save_table_object(msa, False)

    @classmethod
    def increment_send_tries_and_set_send_failed_date(cls, messageSubscriptionView):
        msa = cls.db.get_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        msa.SendFailedDate = datetime.now()
        msa.NoOfSendTries = msa.NoOfSendTries + 1
        msa.FindAdapterTryDate = None
        msa.FindAdapterTries = 0
        cls.db.save_table_object(msa, False)

    @classmethod
    def increment_find_adapter_tries_and_set_find_adapter_try_date(cls, messageSubscriptionView):
        msa = cls.db.get_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        msa.FindAdapterTryDate = datetime.now()
        msa.FindAdapterTries = msa.FindAdapterTries + 1
        cls.db.save_table_object(msa, False)

    @classmethod
    def archive_message_subscription_after_ack(cls, messageNumber):
        sixtySecondsAgo = datetime.now() - timedelta(seconds=60)
        sql = ("SELECT MessageSubscriptionData.* FROM MessageSubscriptionData WHERE "
                                       "CustomData = '%s' AND SentDate > '%s' "
                                        "ORDER BY SentDate desc LIMIT 1") % (messageNumber, sixtySecondsAgo)
        rows = cls.db.get_table_objects_by_SQL(MessageSubscriptionData, sql)

        if len(rows) > 0:
            msd = rows[0]
            msa = MessageSubscriptionArchiveData()
            msa.OrigId = msd.id
            msa.CustomData = msd.CustomData
            msa.SentDate = msd.SentDate
            msa.SendFailedDate = msd.SendFailedDate
            msa.FindAdapterTryDate = msd.FindAdapterTryDate
            msa.FindAdapterTries = msd.FindAdapterTries
            msa.NoOfSendTries = msd.NoOfSendTries
            msa.AckReceivedDate = datetime.now()
            msa.MessageBoxId = msd.MessageBoxId
            msa.SubscriptionId = msd.SubscriptionId
            subscriberView = DatabaseHelper.get_subscriber_by_subscription_id(msd.SubscriptionId)
            if len(subscriberView) > 0:
                msa.SubscriberTypeName = subscriberView[0].TypeName
                msa.TransformName = subscriberView[0].TransformName
            cls.db.save_table_object(msa, False)
            cls.db.delete_table_object(MessageSubscriptionData, msd.id)
            remainingMsgSub = cls.get_no_of_message_subscriptions_by_message_box_id(msd.MessageBoxId)
            if remainingMsgSub == 0:
                cls.archive_message_box(msd.MessageBoxId)


#MessageSubscriptionView

    @classmethod
    def get_message_subscriptions_view(cls, limit = 100):
        sql = ("SELECT count(MessageSubscriptionData.id) FROM MessageSubscriptionData")
        cnt = cls.db.get_scalar_by_SQL(sql)
        if cnt > 0:
            sql = ("SELECT MessageSubscriptionData.id, "
                   "MessageSubscriptionData.CustomData, "
                   "MessageSubscriptionData.SentDate, "
                   "MessageSubscriptionData.SendFailedDate, "
                   "MessageSubscriptionData.FindAdapterTryDate, "
                   "MessageSubscriptionData.FindAdapterTries, "
                   "MessageSubscriptionData.NoOfSendTries, "
                   "MessageSubscriptionData.AckReceivedDate, "
                   "MessageSubscriptionData.MessageBoxId, "
                   "MessageSubscriptionData.SubscriptionId, "
                   "SubscriptionData.DeleteAfterSent, "
                   "SubscriptionData.Enabled, "
                   "SubscriptionData.SubscriberId, "
                   "SubscriberData.TypeName as SubscriberTypeName, "
                   "SubscriberData.InstanceName as SubscriberInstanceName, "
                   "TransformData.Name as TransformName, "
                   "MessageBoxData.MessageData,"
                   "MessageBoxData.id as MessageBoxId "
                   "FROM TransformData JOIN SubscriptionData "
                   "ON TransformData.id = SubscriptionData.TransformId "
                   "JOIN SubscriberData ON SubscriberData.id = SubscriptionData.SubscriberId "
                   "JOIN MessageSubscriptionData ON MessageSubscriptionData.SubscriptionId = SubscriptionData.id "
                   "JOIN MessageBoxData ON MessageBoxData.id = MessageSubscriptionData.MessageBoxId "
                   "WHERE SubscriptionData.Enabled IS NOT NULL AND SubscriptionData.Enabled = 1 AND "
                   "TransformData.Enabled IS NOT NULL AND TransformData.Enabled = 1 "
                   "ORDER BY MessageSubscriptionData.NoOfSendTries asc, "
                   "MessageSubscriptionData.SentDate asc LIMIT %s") % limit
            return cls.db.get_table_objects_by_SQL(MessageSubscriptionView, sql)
        return []

#MessageBox
    @classmethod
    def save_message_box(cls, messageBoxData):
        return cls.db.save_table_object(messageBoxData, False)

    @classmethod
    def get_message_box_messages(cls):
        return cls.db.get_table_objects(MessageBoxData)

    @classmethod
    def archive_message_box(cls, msgBoxId):
        sql = "INSERT INTO MessageBoxArchiveData (OrigId, MessageData, PowerCycleCreated," \
              "CreatedDate, ChecksumOK, InstanceName, MessageTypeName) SELECT id, MessageData," \
              "PowerCycleCreated, CreatedDate, ChecksumOK, InstanceName, MessageTypeName FROM " \
              "MessageBoxData WHERE Id = %s" % msgBoxId
        cls.db.execute_SQL(sql)
        cls.db.delete_table_object(MessageBoxData, msgBoxId)

#InputAdapterInstances
    @classmethod
    def update_input_adapter_instances(cls, inputAdapterObjects):
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
        inputAdapterInstances = cls.db.get_table_objects(InputAdapterInstances)
        return inputAdapterInstances

#BlenoPunchData
    @classmethod
    def save_bleno_punch_data(cls, blenoPunchData):
        cls.db.save_table_object(blenoPunchData, False)

    @classmethod
    def get_bleno_punches(cls):
        return cls.db.get_table_objects(BlenoPunchData)

    @classmethod
    def delete_bleno_punch_data(cls, rowId):
        cls.db.delete_table_object(BlenoPunchData, rowId)

#TestPunchData
    @classmethod
    def add_test_punch(cls, testBatchGuid, SINo, twelveHourTimer, twentyFourHour, ackReq):
        testPunch = TestPunchData()
        testPunch.BatchGuid = testBatchGuid
        testPunch.MessageBoxId = None
        testPunch.TwelveHourTimer = twelveHourTimer
        testPunch.TwentyFourHour = twentyFourHour
        testPunch.SICardNumber = SINo
        testPunch.AckReq = ackReq
        cls.db.save_table_object(testPunch, False)

    @classmethod
    def delete_other_test_punches(cls, testBatchGuid):
        cls.db.execute_SQL("DELETE FROM TestPunchData WHERE BatchGuid <> %s" % testBatchGuid)

    @classmethod
    def get_test_punch_to_add(cls):
        testPunches = cls.db.get_table_objects_by_SQL(TestPunchData, "SELECT * FROM TestPunchData WHERE AddedToMessageBox = 0 ORDER BY TwentyFourHour, TwelveHourTimer LIMIT 1")
        if len(testPunches) > 0:
            return testPunches[0]
        return None

    @classmethod
    def get_test_punch_ack_req(cls, msgId):
        testPunches = cls.db.get_table_objects_by_SQL(TestPunchData,
                                                      "SELECT * FROM TestPunchData WHERE MessageBoxId = %s" % msgId)
        if len(testPunches) > 0:
            return testPunches[0].AckReq
        return False

    @classmethod
    def set_test_punch_added_to_message_box(cls, messageBoxId, testPunchId):
        cls.db.execute_SQL("UPDATE TestPunchData SET AddedToMessageBox = 1, MessageBoxId = %s WHERE id = %s" % (messageBoxId, testPunchId))
        return None

    @classmethod
    def get_test_punches(cls, testBatchGuid):
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
         "END Status "
         "FROM TestPunchData LEFT JOIN MessageBoxData ON TestPunchData.MessageBoxId = MessageBoxData.id "
         "LEFT JOIN MessageSubscriptionData ON MessageBoxData.id = MessageSubscriptionData.MessageBoxId "
         "LEFT JOIN MessageBoxArchiveData ON TestPunchData.MessageBoxId = MessageBoxArchiveData.OrigId "
         "LEFT JOIN MessageSubscriptionArchiveData ON MessageBoxArchiveData.OrigId = MessageSubscriptionArchiveData.MessageBoxId "
         "WHERE BatchGuid = '%s'" % testBatchGuid)
        return testPunchesView

    @classmethod
    def get_test_punches_not_fetched(cls, testBatchGuid):
        allPunches = cls.get_test_punches(testBatchGuid)
        notFetchedPunches = list(filter(lambda p: not p.Fetched, allPunches))
        for punch in notFetchedPunches:
            if punch.Status == 'Not sent' or punch.Status == 'Acked' or punch.Status == 'Not acked':
                cls.db.execute_SQL("UPDATE TestPunchData SET Fetched = 1 WHERE id = %s" % punch.id)
        return notFetchedPunches

#Channels
    @classmethod
    def get_channel(cls, channel, dataRate):
        sql = ("SELECT * FROM ChannelData WHERE Channel = " + str(channel) +
               " and DataRate = " + str(dataRate))
        rows = cls.db.get_table_objects_by_SQL(ChannelData, sql)
        if len(rows) >= 1:
            return rows[0]
        return None

    @classmethod
    def save_channel(cls, channel):
        cls.db.save_table_object(channel, False)

    @classmethod
    def add_default_channels(cls):
        channels = []
        channels.append(ChannelData(1, 146, 439700000, 72333, 22, 12, 6))
        channels.append(ChannelData(2, 146, 439725000, 72333, 22, 12, 6))
        channels.append(ChannelData(3, 146, 439775000, 72333, 22, 12, 6))
        channels.append(ChannelData(4, 146, 439800000, 72333, 22, 12, 6))
        channels.append(ChannelData(5, 146, 439850000, 72333, 22, 12, 6))
        channels.append(ChannelData(6, 146, 439875000, 72333, 22, 12, 6))
        channels.append(ChannelData(7, 146, 439925000, 72333, 22, 12, 6))
        channels.append(ChannelData(8, 146, 439950000, 72333, 22, 12, 6))
        channels.append(ChannelData(9, 146, 439975000, 72333, 22, 12, 6))
        channels.append(ChannelData(1, 293, 439700000, 52590, 16, 12, 7))
        channels.append(ChannelData(2, 293, 439725000, 52590, 16, 12, 7))
        channels.append(ChannelData(3, 293, 439775000, 52590, 16, 12, 7))
        channels.append(ChannelData(4, 293, 439800000, 52590, 16, 12, 7))
        channels.append(ChannelData(5, 293, 439850000, 52590, 16, 12, 7))
        channels.append(ChannelData(6, 293, 439875000, 52590, 16, 12, 7))
        channels.append(ChannelData(7, 293, 439925000, 52590, 16, 12, 7))
        channels.append(ChannelData(8, 293, 439950000, 52590, 16, 12, 7))
        channels.append(ChannelData(9, 293, 439975000, 52590, 16, 12, 7))
        channels.append(ChannelData(1, 586, 439700000, 26332, 16, 12, 8))
        channels.append(ChannelData(2, 586, 439725000, 26332, 16, 12, 8))
        channels.append(ChannelData(3, 586, 439775000, 26332, 16, 12, 8))
        channels.append(ChannelData(4, 586, 439800000, 26332, 16, 12, 8))
        channels.append(ChannelData(5, 586, 439850000, 26332, 16, 12, 8))
        channels.append(ChannelData(6, 586, 439875000, 26332, 16, 12, 8))
        channels.append(ChannelData(7, 586, 439925000, 26332, 16, 12, 8))
        channels.append(ChannelData(8, 586, 439950000, 26332, 16, 12, 8))
        channels.append(ChannelData(9, 586, 439975000, 26332, 16, 12, 8))
        channels.append(ChannelData(1, 2148, 439700000, 7132, 15, 11, 9))
        channels.append(ChannelData(2, 2148, 439725000, 7132, 15, 11, 9))
        channels.append(ChannelData(3, 2148, 439775000, 7132, 15, 11, 9))
        channels.append(ChannelData(4, 2148, 439800000, 7132, 15, 11, 9))
        channels.append(ChannelData(5, 2148, 439850000, 7132, 15, 11, 9))
        channels.append(ChannelData(6, 2148, 439875000, 7132, 15, 11, 9))
        channels.append(ChannelData(7, 2148, 439925000, 7132, 15, 11, 9))
        channels.append(ChannelData(8, 2148, 439950000, 7132, 15, 11, 9))
        channels.append(ChannelData(9, 2148, 439975000, 7132, 15, 11, 9))
        channels.append(ChannelData(1, 7032, 439700000, 2500, 15, 10, 9))
        channels.append(ChannelData(2, 7032, 439725000, 2500, 15, 10, 9))
        channels.append(ChannelData(3, 7032, 439775000, 2500, 15, 10, 9))
        channels.append(ChannelData(4, 7032, 439800000, 2500, 15, 10, 9))
        channels.append(ChannelData(5, 7032, 439850000, 2500, 15, 10, 9))
        channels.append(ChannelData(6, 7032, 439875000, 2500, 15, 10, 9))
        channels.append(ChannelData(7, 7032, 439925000, 2500, 15, 10, 9))
        channels.append(ChannelData(8, 7032, 439950000, 2500, 15, 10, 9))
        channels.append(ChannelData(9, 7032, 439975000, 2500, 15, 10, 9))
        for channel in channels:
            cls.save_channel(channel)



