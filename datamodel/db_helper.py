__author__ = 'henla464'

from datamodel.datamodel import *
from constants import *
from databaselib.db import DB
from databaselib.datamapping import DataMapping
from datetime import timedelta, datetime


class DatabaseHelper:
    database_name = "radiomessages.db"

    def __init__(self):
        self.db = DB(DatabaseHelper.database_name, DataMapping())

    def ensure_tables_created(self):
        table = SettingData()
        self.db.ensure_table_created(table)
        table = ChannelData()
        self.db.ensure_table_created(table)
        table = MessageBoxData()
        self.db.ensure_table_created(table)
        table = MessageBoxArchiveData()
        self.db.ensure_table_created(table)
        table = SubscriberData()
        self.db.ensure_table_created(table)
        table = MessageTypeData()
        self.db.ensure_table_created(table)
        table = TransformData()
        self.db.ensure_table_created(table)
        table = SubscriptionData()
        self.db.ensure_table_created(table)
        table = MessageSubscriptionData()
        self.db.ensure_table_created(table)
        table = MessageSubscriptionArchiveData()
        self.db.ensure_table_created(table)


    def drop_all_tables(self):
        table = SettingData()
        self.db.drop_table(table)
        table = ChannelData()
        self.db.drop_table(table)
        table = MessageBoxData()
        self.db.drop_table(table)
        table = MessageBoxArchiveData()
        self.db.drop_table(table)
        table = SubscriberData()
        self.db.drop_table(table)
        table = MessageTypeData()
        self.db.drop_table(table)
        table = TransformData()
        self.db.drop_table(table)
        table = SubscriptionData()
        self.db.drop_table(table)
        table = MessageSubscriptionData()
        self.db.drop_table(table)
        table = MessageSubscriptionArchiveData()
        self.db.drop_table(table)

    def truncate_setup_tables(self):
        self.db.execute_SQL("DELETE FROM SubscriberData")
        self.db.execute_SQL("DELETE FROM MessageTypeData")
        self.db.execute_SQL("DELETE FROM SubscriptionData")
        self.db.execute_SQL("DELETE FROM TransformData")
        self.db.execute_SQL("DELETE FROM ChannelData")


#Settings
    def save_setting(self, settingData):
        sd = self.get_setting_by_key(settingData.Key)
        if sd is None:
            sd = self.db.save_table_object(settingData)
        else:
            sd.Value = settingData.Value
            sd = self.db.save_table_object(sd)

        return self.get_setting(sd.id)

    def get_setting(self, id):
        sd = self.db.get_table_object(SettingData, str(id))
        return sd

    def get_setting_by_key(self, key):
        row_list = self.db.get_table_objects_by_SQL(SettingData, "SELECT * FROM SettingData WHERE Key = '" + key + "'")
        if len(row_list) == 0:
            return None
        return row_list[0]

#Subscriber
    def save_subscriber(self, subscriberData):
        rows = self.db.get_table_objects_by_SQL(SubscriberData, "SELECT * FROM SubscriberData WHERE TypeName = '" +
                                    subscriberData.TypeName + "' and InstanceName = '" +
                                    subscriberData.InstanceName + "'")
        if len(rows) == 0:
            return self.db.save_table_object(subscriberData)
        else:
            #nothing to update
            return rows[0]



#MessageTypes
    def get_message_type(self, messageTypeName):
        sql = "SELECT * FROM MessageTypeData WHERE Name = '" + messageTypeName + "'"
        rows = self.db.get_table_objects_by_SQL(MessageTypeData, sql)
        if len(rows) >= 1:
            return rows[0]
        return None


    def save_message_type(self, messageTypeData):
        rows = self.db.get_table_objects_by_SQL(MessageTypeData, "SELECT * FROM MessageTypeData WHERE Name = '" +
                                           messageTypeData.Name + "'")
        if len(rows) == 0:
            return self.db.save_table_object(messageTypeData)
        else:
            # nothing to update
            return rows[0]

#Transforms
    def save_transform(self, transformData):
        rows = self.db.get_table_objects_by_SQL(TransformData, "SELECT * FROM TransformData WHERE Name = '" +
                                           transformData.Name + "'")
        if len(rows) > 0:
            transformData.id = rows[0].id
        return self.db.save_table_object(transformData)

    def set_transform_enabled(self, enabled, transformName):
        dbValue = DataMapping.get_database_value(enabled)
        sql = ("UPDATE TransformData SET Enabled = " + str(dbValue) + " " +
               "WHERE TransformData.Name = '" + transformName + "'")
        logging.debug(sql)
        self.db.execute_SQL(sql)

#Subscriptions
    def save_subscription(self, subscriptionData):
        rows = self.db.get_table_objects_by_SQL(SubscriptionData, ("SELECT * FROM SubscriptionData WHERE "
                                           "SubscriberId = " + str(subscriptionData.SubscriberId) +
                                           " and TransformId = " + str(subscriptionData.TransformId)))
        if len(rows) > 0:
            subscriptionData.id = rows[0].id
        return self.db.save_table_object(subscriptionData)


    def get_subscriptions_by_input_message_type_id(self, messageTypeId):
        sql = ("SELECT SubscriptionData.* FROM TransformData JOIN SubscriptionData "
               "ON TransformData.id = SubscriptionData.TransformId "
               "WHERE TransformData.Enabled = 1 AND SubscriptionData.Enabled = 1 AND "
               "InputMessageTypeID = " + str(messageTypeId))
        rows = self.db.get_table_objects_by_SQL(SubscriptionData, sql)
        return rows

    def set_subscriptions_enabled(self, enabled, subscriberTypeName):
        sql = ("SELECT SubscriptionData.* FROM SubscriberData JOIN SubscriptionData "
               "ON SubscriberData.id = SubscriptionData.SubscriberId "
               "WHERE SubscriberData.TypeName = '" + str(subscriberTypeName) +"'")
        rows = self.db.get_table_objects_by_SQL(SubscriptionData, sql)
        for subscription in rows:
            subscription.Enabled = enabled
            self.db.save_table_object(subscription)

#MessageSubscriptions
    def get_no_of_message_subscriptions_by_message_box_id(self, msgBoxId):
        rows = self.db.get_table_objects_by_SQL(MessageSubscriptionData, ("SELECT * FROM "
                                                                     "MessageSubscriptionData WHERE "
                                                                     "MessageBoxId = " + str(msgBoxId)))
        return len(rows)

    def save_message_subscription(self, messageSubscription):
        return self.db.save_table_object(messageSubscription)

    def archive_message_subscription_view_after_sent(self, messageSubscriptionView):
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
        self.db.save_table_object(msa)
        self.db.delete_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        remainingMsgSub = self.get_no_of_message_subscriptions_by_message_box_id(messageSubscriptionView.MessageBoxId)
        if remainingMsgSub == 0:
            self.archive_message_box(messageSubscriptionView.MessageBoxId)


    def archive_message_subscription_view_not_sent(self, messageSubscriptionView):
        msa = MessageSubscriptionArchiveData()
        msa.OrigId = messageSubscriptionView.id
        msa.CustomData = messageSubscriptionView.CustomData
        msa.SentDate = None
        msa.SendFailedDate = messageSubscriptionView.SendFailedDate
        msa.FindAdapterTryDate = messageSubscriptionView.FindAdapterTryDate
        msa.FindAdapterTries = messageSubscriptionView.FindAdapterTries
        msa.NoOfSendTries = messageSubscriptionView.NoOfSendTries
        msa.AckReceivedDate = messageSubscriptionView.AckReceivedDate
        msa.MessageBoxId = messageSubscriptionView.MessageBoxId
        msa.SubscriptionId = messageSubscriptionView.SubscriptionId
        self.db.save_table_object(msa)
        self.db.delete_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        remainingMsgSub = self.get_no_of_message_subscriptions_by_message_box_id(messageSubscriptionView.MessageBoxId)
        if remainingMsgSub == 0:
            self.archive_message_box(messageSubscriptionView.MessageBoxId)

    def increment_send_tries_and_set_sent_date(self, messageSubscriptionView):
        msa = self.db.get_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        msa.SentDate = datetime.now()
        msa.NoOfSendTries = msa.NoOfSendTries + 1
        msa.FindAdapterTryDate = None
        msa.FindAdapterTries = 0
        self.db.save_table_object(msa)

    def increment_send_tries_and_set_send_failed_date(self, messageSubscriptionView):
        msa = self.db.get_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        msa.SendFailedDate = datetime.now()
        msa.NoOfSendTries = msa.NoOfSendTries + 1
        msa.FindAdapterTryDate = None
        msa.FindAdapterTries = 0
        self.db.save_table_object(msa)

    def increment_find_adapter_tries_and_set_find_adapter_try_date(self, messageSubscriptionView):
        msa = self.db.get_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        msa.FindAdapterTryDate = datetime.now()
        msa.FindAdapterTries = msa.FindAdapterTries + 1
        self.db.save_table_object(msa)

    def archive_message_subscription_after_ack(self, messageNumber):
        thirtySecondsAgo = datetime.now() - timedelta(seconds=30)
        rows = self.db.get_table_objects_by_SQL(MessageSubscriptionData,
                                                          ("SELECT MessageSubscriptionData.* FROM "
                                                           "MessageSubscriptionData WHERE "
                                                           "CustomData = " + str(messageNumber) + " AND "
                                                           "SendDate > " + str(thirtySecondsAgo) + " "
                                                           "ORDER BY SendDate desc LIMIT 1"))

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
            self.db.save_table_object(msa)
            self.db.delete_table_object(MessageSubscriptionData, msd.id)
            remainingMsgSub = self.get_no_of_message_subscriptions_by_message_box_id(msd.MessageBoxId)
            if remainingMsgSub == 0:
                self.archive_message_box(msd.MessageBoxId)


#MessageSubscriptionView
    def get_message_subscriptions_view(self):
        sql = ("SELECT count(MessageSubscriptionData.id) FROM MessageSubscriptionData")
        cnt = self.db.get_scalar_by_SQL(MessageSubscriptionView, sql)
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
                   "MessageBoxData.MessageData "
                   "FROM TransformData JOIN SubscriptionData "
                   "ON TransformData.id = SubscriptionData.TransformId "
                   "JOIN SubscriberData ON SubscriberData.id = SubscriptionData.SubscriberId "
                   "JOIN MessageSubscriptionData ON MessageSubscriptionData.SubscriptionId = SubscriptionData.id "
                   "JOIN MessageBoxData ON MessageBoxData.id = MessageSubscriptionData.MessageBoxId "
                   "WHERE SubscriptionData.Enabled IS NOT NULL AND SubscriptionData.Enabled = 1 AND "
                   "TransformData.Enabled IS NOT NULL AND TransformData.Enabled = 1 "
                   "ORDER BY MessageSubscriptionData.NoOfSendTries asc, "
                   "MessageSubscriptionData.SentDate asc")
            return self.db.get_table_objects_by_SQL(MessageSubscriptionView, sql)
        return []

#MessageBox
    def save_message_box(self, messageBoxData):
        return self.db.save_table_object(messageBoxData)

    def archive_message_box(self, msgBoxId):
        messageBoxData = self.db.get_table_object(MessageBoxData, msgBoxId)
        messageBoxArchive = MessageBoxArchiveData()
        messageBoxArchive.OrigId = messageBoxData.id
        messageBoxArchive.MessageData = messageBoxData.MessageData
        messageBoxArchive.PowerCycleCreated = messageBoxData.PowerCycleCreated
        messageBoxArchive.CreatedDate = messageBoxData.CreatedDate
        messageBoxArchive.ChecksumOK = messageBoxData.ChecksumOK
        messageBoxArchive.InstanceName = messageBoxData.InstanceName
        messageBoxArchive.MessageTypeId = messageBoxData.MessageTypeId
        self.db.save_table_object(messageBoxArchive)
        self.db.delete_table_object(MessageBoxData, msgBoxId)


#Channels
    def get_channel(self, channel, dataRate):
        sql = ("SELECT * FROM ChannelData WHERE Channel = " + str(channel) +
               " and DataRate = " + str(dataRate))
        rows = self.db.get_table_objects_by_SQL(ChannelData, sql)
        if len(rows) >= 1:
            return rows[0]
        return None

    def save_channel(self, channel):
        self.db.save_table_object(channel)

    def add_default_channels(self):
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
            self.save_channel(channel)


DatabaseHelper.mainDatabaseHelper = None