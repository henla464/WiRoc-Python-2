__author__ = 'henla464'

from datamodel.datamodel import *
from constants import *
from databaselib.db import DB
from databaselib.datamapping import DataMapping
from datetime import timedelta, datetime


class DatabaseHelper:
    database_name = "radiomessages.db"

    @staticmethod
    def ensure_tables_created():
        db = DB(DatabaseHelper.database_name, DataMapping())
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

    @staticmethod
    def drop_all_tables():
        db = DB(DatabaseHelper.database_name, DataMapping())
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

    @staticmethod
    def truncate_setup_tables():
        db = DB(DatabaseHelper.database_name, DataMapping())
        db.execute_SQL("DELETE FROM SubscriberData")
        db.execute_SQL("DELETE FROM MessageTypeData")
        db.execute_SQL("DELETE FROM SubscriptionData")
        db.execute_SQL("DELETE FROM TransformData")
        db.execute_SQL("DELETE FROM ChannelData")


#Settings
    @staticmethod
    def save_setting(settingData):
        db = DB(DatabaseHelper.database_name, DataMapping())
        sd = DatabaseHelper.get_setting_by_key(settingData.Key)
        if sd is None:
            sd = db.save_table_object(settingData)
        else:
            sd.Value = settingData.Value
            sd = db.save_table_object(sd)

        return DatabaseHelper.get_setting(sd.id)

    @staticmethod
    def get_setting(id):
        db = DB(DatabaseHelper.database_name, DataMapping())
        sd = db.get_table_object(SettingData, str(id))
        return sd

    @staticmethod
    def get_setting_by_key(key):
        db = DB(DatabaseHelper.database_name, DataMapping())
        row_list = db.get_table_objects_by_SQL(SettingData, "SELECT * FROM SettingData WHERE Key = '" + key + "'")
        if len(row_list) == 0:
            return None
        return row_list[0]

#Subscriber
    @staticmethod
    def save_subscriber(subscriberData):
        db = DB(DatabaseHelper.database_name, DataMapping())
        rows = db.get_table_objects_by_SQL(SubscriberData, "SELECT * FROM SubscriberData WHERE TypeName = '" +
                                    subscriberData.TypeName + "' and InstanceName = '" +
                                    subscriberData.InstanceName + "'")
        if len(rows) == 0:
            return db.save_table_object(subscriberData)
        else:
            #nothing to update
            return rows[0]



#MessageTypes
    @staticmethod
    def get_message_type(messageTypeName):
        db = DB(DatabaseHelper.database_name, DataMapping())
        sql = "SELECT * FROM MessageTypeData WHERE Name = '" + messageTypeName + "'"
        rows = db.get_table_objects_by_SQL(MessageTypeData, sql)
        if len(rows) >= 1:
            return rows[0]
        return None


    @staticmethod
    def save_message_type(messageTypeData):
        db = DB(DatabaseHelper.database_name, DataMapping())
        rows = db.get_table_objects_by_SQL(MessageTypeData, "SELECT * FROM MessageTypeData WHERE Name = '" +
                                           messageTypeData.Name + "'")
        if len(rows) == 0:
            return db.save_table_object(messageTypeData)
        else:
            # nothing to update
            return rows[0]

#Transforms
    @staticmethod
    def save_transform(transformData):
        db = DB(DatabaseHelper.database_name, DataMapping())
        rows = db.get_table_objects_by_SQL(TransformData, "SELECT * FROM TransformData WHERE Name = '" +
                                           transformData.Name + "'")
        if len(rows) > 0:
            transformData.id = rows[0].id
        return db.save_table_object(transformData)

#Subscriptions
    @staticmethod
    def save_subscription(subscriptionData):
        db = DB(DatabaseHelper.database_name, DataMapping())
        rows = db.get_table_objects_by_SQL(SubscriptionData, ("SELECT * FROM SubscriptionData WHERE "
                                           "SubscriberId = " + str(subscriptionData.SubscriberId) +
                                           " and TransformId = " + str(subscriptionData.TransformId)))
        if len(rows) > 0:
            subscriptionData.id = rows[0].id
        return db.save_table_object(subscriptionData)


    @staticmethod
    def get_subscriptions_by_input_message_type_id(messageTypeId):
        db = DB(DatabaseHelper.database_name, DataMapping())
        sql = ("SELECT SubscriptionData.* FROM TransformData JOIN SubscriptionData "
               "ON TransformData.id = SubscriptionData.TransformId "
               "WHERE InputMessageTypeID = " + str(messageTypeId))
        rows = db.get_table_objects_by_SQL(SubscriptionData, sql)
        return rows

#MessageSubscriptions
    @staticmethod
    def get_no_of_message_subscriptions_by_message_box_id(msgBoxId):
        db = DB(DatabaseHelper.database_name, DataMapping())
        rows = db.get_table_objects_by_SQL(MessageSubscriptionData, ("SELECT * FROM "
                                                                     "MessageSubscriptionData WHERE "
                                                                     "MessageBoxId = " + str(msgBoxId)))
        return len(rows)

    @staticmethod
    def save_message_subscription(messageSubscription):
        db = DB(DatabaseHelper.database_name, DataMapping())
        return db.save_table_object(messageSubscription)

    @staticmethod
    def archive_message_subscription_view_after_sent(messageSubscriptionView):
        db = DB(DatabaseHelper.database_name, DataMapping())
        msa = MessageSubscriptionArchiveData()
        msa.OrigId = messageSubscriptionView.id
        msa.CustomData = messageSubscriptionView.CustomData
        msa.SentDate = datetime.now()
        msa.NoOfSendTries = messageSubscriptionView.NoOfSendTries + 1
        msa.AckReceivedDate = messageSubscriptionView.AckReceivedDate
        msa.MessageBoxId = messageSubscriptionView.MessageBoxId
        msa.SubscriptionId = messageSubscriptionView.SubscriptionId
        db.save_table_object(msa)
        db.delete_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        remainingMsgSub = DatabaseHelper.get_no_of_message_subscriptions_by_message_box_id(messageSubscriptionView.MessageBoxId)
        if remainingMsgSub == 0:
            DatabaseHelper.archive_message_box(messageSubscriptionView.MessageBoxId)


    @staticmethod
    def archive_message_subscription_view_not_sent(messageSubscriptionView):
        db = DB(DatabaseHelper.database_name, DataMapping())
        msa = MessageSubscriptionArchiveData()
        msa.OrigId = messageSubscriptionView.id
        msa.CustomData = messageSubscriptionView.CustomData
        msa.SentDate = None
        msa.NoOfSendTries = messageSubscriptionView.NoOfSendTries
        msa.AckReceivedDate = messageSubscriptionView.AckReceivedDate
        msa.MessageBoxId = messageSubscriptionView.MessageBoxId
        msa.SubscriptionId = messageSubscriptionView.SubscriptionId
        db.save_table_object(msa)
        db.delete_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        remainingMsgSub = DatabaseHelper.get_no_of_message_subscriptions_by_message_box_id(messageSubscriptionView.MessageBoxId)
        if remainingMsgSub == 0:
            DatabaseHelper.archive_message_box(messageSubscriptionView.MessageBoxId)

    @staticmethod
    def increment_send_tries_and_set_sent_date(messageSubscriptionView):
        db = DB(DatabaseHelper.database_name, DataMapping())
        msa = db.get_table_object(MessageSubscriptionData, messageSubscriptionView.id)
        msa.SentDate = datetime.now()
        msa.NoOfSendTries = msa.NoOfSendTries + 1
        db.save_table_object(msa)

    @staticmethod
    def archive_message_subscription_after_ack(messageNumber):
        db = DB(DatabaseHelper.database_name, DataMapping())
        thirtySecondsAgo = datetime.now() - timedelta(seconds=30)
        rows = db.get_table_objects_by_SQL(MessageSubscriptionData, ("SELECT id, CustomData, SentDate, "
                                     "NoOfSendTries, AckReceivedDate, "
                                     "MessageBoxId, SubscriptionId FROM "
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
            msa.NoOfSendTries = msd.NoOfSendTries
            msa.AckReceivedDate = datetime.now()
            msa.MessageBoxId = msd.MessageBoxId
            db.save_table_object(msa)
            db.delete_table_object(MessageSubscriptionData, msd.id)


#MessageSubscriptionView
    @staticmethod
    def get_message_subscriptions_view():
        db = DB(DatabaseHelper.database_name, DataMapping())
        sql = ("SELECT MessageSubscriptionData.id, "
               "MessageSubscriptionData.CustomData, MessageSubscriptionData.SentDate, "
               "MessageSubscriptionData.NoOfSendTries, MessageSubscriptionData.AckReceivedDate, "
               "MessageSubscriptionData.MessageBoxId, "
               "MessageSubscriptionData.SubscriptionId, SubscriptionData.DeleteAfterSent, "
               "SubscriptionData.Enabled, SubscriptionData.SubscriberId, "
               "SubscriberData.TypeName as SubscriberTypeName, SubscriberData.InstanceName as SubscriberInstanceName, "
               "TransformData.Name as TransformName, MessageBoxData.MessageData "
               "FROM TransformData JOIN SubscriptionData "
               "ON TransformData.id = SubscriptionData.TransformId "
               "JOIN SubscriberData ON SubscriberData.id = SubscriptionData.SubscriberId "
               "JOIN MessageSubscriptionData ON MessageSubscriptionData.SubscriptionId = SubscriptionData.id "
               "JOIN MessageBoxData ON MessageBoxData.id = MessageSubscriptionData.MessageBoxId "
               "WHERE SubscriptionData.Enabled IS NOT NULL "
               "ORDER BY MessageSubscriptionData.NoOfSendTries asc, "
               "MessageSubscriptionData.SentDate asc")
        return db.get_table_objects_by_SQL(MessageSubscriptionView, sql)

#MessageBox
    @staticmethod
    def save_message_box(messageBoxData):
        db = DB(DatabaseHelper.database_name, DataMapping())
        return db.save_table_object(messageBoxData)

    @staticmethod
    def archive_message_box(msgBoxId):
        db = DB(DatabaseHelper.database_name, DataMapping())
        messageBoxData = db.get_table_object(MessageBoxData, msgBoxId)
        messageBoxArchive = MessageBoxArchiveData()
        messageBoxArchive.OrigId = messageBoxData.id
        messageBoxArchive.MessageData = messageBoxData.MessageData
        messageBoxArchive.PowerCycleCreated = messageBoxData.PowerCycleCreated
        messageBoxArchive.CreatedDate = messageBoxData.CreatedDate
        messageBoxArchive.ChecksumOK = messageBoxData.ChecksumOK
        messageBoxArchive.InstanceName = messageBoxData.InstanceName
        messageBoxArchive.MessageTypeId = messageBoxData.MessageTypeId
        db.save_table_object(messageBoxArchive)
        db.delete_table_object(MessageBoxData, msgBoxId)


#Channels
    @staticmethod
    def get_channel(channel, dataRate):
        db = DB(DatabaseHelper.database_name, DataMapping())
        sql = ("SELECT * FROM ChannelData WHERE Channel = " + str(channel) +
               " and DataRate = " + str(dataRate))
        rows = db.get_table_objects_by_SQL(ChannelData, sql)
        if len(rows) >= 1:
            return rows[0]
        return None

    @staticmethod
    def save_channel(channel):
        db = DB(DatabaseHelper.database_name, DataMapping())
        db.save_table_object(channel)

    @staticmethod
    def add_default_channels():
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
            DatabaseHelper.save_channel(channel)

    #---


    @staticmethod
    def get_punches_to_send_to_meos():
        db = DB(DatabaseHelper.database_name, DataMapping())
        row_list = db.get_table_objects_by_SQL(PunchData, "SELECT * FROM PunchData " +
                                                                 "WHERE sentToMeos = 0 AND " +
                                                                 "stationNumberNotFound = 0 ORDER BY id asc")
        return row_list

    @staticmethod
    def set_punch_sent_to_meos(punchDataId):
        db = DB(DatabaseHelper.database_name, DataMapping())
        db.execute_SQL("UPDATE PunchData SET sentToMeos = 1 WHERE id=" + str(punchDataId))

    @staticmethod
    def set_no_station_number_found(punchDataId):
        db = DB(DatabaseHelper.database_name, DataMapping())
        db.execute_SQL("UPDATE PunchData SET stationNumberNotFound = 1 WHERE id=" + str(punchDataId))

    @staticmethod
    def get_control_number_by_node_number(node_number):
        db = DB(DatabaseHelper.database_name, DataMapping())
        rows = db.get_table_objects_by_SQL(NodeToControlNumberData, "SELECT * FROM NodeToControlNumberData " +
                                                             "WHERE NodeNumber = " + str(node_number))
        if len(rows) >= 1:
            return rows[0].ControlNumber
        return None

    @staticmethod
    def remove_all_punches():
        db = DB(DatabaseHelper.database_name, DataMapping())
        db.execute_SQL("DELETE FROM PunchData")
        db.execute_SQL("DELETE FROM RadioMessageData")

    @staticmethod
    def get_channels():
        db = DB(DatabaseHelper.database_name, DataMapping())
        sql = "SELECT * FROM ChannelData ORDER BY id"
        row_list = db.get_table_objects_by_SQL(ChannelData, sql)
        return row_list


