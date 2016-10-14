__author__ = 'henla464'

from datamodel.datamodel import SettingData

from datamodel.datamodel import RadioMessageData
from datamodel.datamodel import PunchData
from datamodel.datamodel import ChannelData
from constants import *
from databaselib.db import DB
from databaselib.datamapping import DataMapping


class DatabaseHelper:
    database_name = "radiomessages.db"
    @staticmethod
    def drop_tables():
        db = DB(DatabaseHelper.database_name, DataMapping())

    @staticmethod
    def ensure_tables_created():
        db = DB(DatabaseHelper.database_name, DataMapping())
        settingsData = SettingData()
        db.ensure_table_created(settingsData)

        radioMessageData = RadioMessageData()
        db.ensure_table_created(radioMessageData)
        punchData = PunchData()
        db.ensure_table_created(punchData)
        channelData = ChannelData()
        db.ensure_table_created(channelData)

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
        print("SELECT * FROM SettingData WHERE Key = '" + key + "'")
        row_list = db.get_table_objects_by_SQL(SettingData, "SELECT * FROM SettingData WHERE Key = '" + key + "'")
        print(len(row_list))
        if len(row_list) == 0:
            return None
        return row_list[0]

#---


    @staticmethod
    def save_radio_message(radioMessageData):
        db = DB(DatabaseHelper.database_name, DataMapping())
        rm = db.save_table_object(radioMessageData)
        print(radioMessageData.dataRecordArray)
        if radioMessageData.dataRecordArray is not None:
            for rec in radioMessageData.dataRecordArray:
                rec.radioMessageId = rm.id
                if rm.messageType == PUNCH:
                    rec.origFromNode = rm.fromNode
                db.save_table_object(rec)
        return DatabaseHelper.get_radio_message(rm.id)


    @staticmethod
    def get_radio_message(id):
        db = DB(DatabaseHelper.database_name, DataMapping())
        row_list = db.get_table_objects_by_SQL(RadioMessageData, "SELECT * FROM RadioMessageData WHERE id = " + str(id) + " ORDER BY id")
        if row_list[0].messageType == PUNCH or row_list[0].messageType == COMBINED_PUNCH:
            dataRecords = db.get_table_objects_by_SQL(PunchData, "SELECT * FROM PunchData WHERE radioMessageId = " + str(id))
            row_list[0].dataRecordArray = dataRecords
        return row_list[0]


    @staticmethod
    def get_last_radio_message_data():
        db = DB(DatabaseHelper.database_name, DataMapping())
        row_list = db.get_table_objects_by_SQL(RadioMessageData, "SELECT * FROM RadioMessageData ORDER BY id desc LIMIT 1")
        return row_list[0]

    @staticmethod
    def get_last_x_radio_message_data(noOfMessages):
        db = DB(DatabaseHelper.database_name, DataMapping())
        row_list = db.get_table_objects_by_SQL(RadioMessageData, "SELECT * FROM RadioMessageData ORDER BY id desc LIMIT " + str(noOfMessages))
        return row_list

    @staticmethod
    def get_last_x_radio_message_data_not_acked(radioNumber, noOfMessages=1):
        db = DB(DatabaseHelper.database_name, DataMapping())
        row_list = db.get_table_objects_by_SQL(RadioMessageData, "SELECT * FROM RadioMessageData " +
                                                                 "WHERE ackSent = 0 "
                                                                 "and radioNumber = " + str(radioNumber) +
                                                                 " ORDER BY id desc LIMIT " +
                                               str(noOfMessages))
        return row_list

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
    def drop_all_tables():
        db = DB(DatabaseHelper.database_name, DataMapping())
        radioMessageData = RadioMessageData()
        db.drop_table(radioMessageData)
        punchData = PunchData()
        db.drop_table(punchData)
        nodeSettingsData = NodeSettingsData()
        db.drop_table(nodeSettingsData)
        inboundRadioNodeData = InboundRadioNodeData()
        db.drop_table(inboundRadioNodeData)
        radioSettingsData = RadioSettingsData()
        db.drop_table(radioSettingsData)
        channelData = ChannelData()
        db.drop_table(channelData)

    @staticmethod
    def get_channels():
        db = DB(DatabaseHelper.database_name, DataMapping())
        sql = "SELECT * FROM ChannelData ORDER BY id"
        row_list = db.get_table_objects_by_SQL(RadioSettingsData, sql)
        return row_list

    @staticmethod
    def get_channel(channel_id):
        if channel_id is None:
            return None
        db = DB(DatabaseHelper.database_name, DataMapping())
        sql = "SELECT * FROM ChannelData WHERE Id = " + str(channel_id)
        rows = db.get_table_objects_by_SQL(RadioSettingsData, sql)
        if len(rows) >= 1:
            return rows[0].FrequencyName + rows[0].SpeedName
        return None

    @staticmethod
    def save_channel(channel):
        db = DB(DatabaseHelper.database_name, DataMapping())
        db.save_table_object(channel)

    @staticmethod
    def add_default_channels():
        channel = ChannelData('A', '1', 7204063, 77332.743718593, 22, 12, 6)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('B', '1', 7205292, 77332.743718593, 22, 12, 6)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('C', '1', 7206521, 77332.743718593, 22, 12, 6)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('D', '1', 7207750, 77332.743718593, 22, 12, 6)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('E', '2', 7204473, 52590.391959799, 16, 12, 7)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('F', '2', 7205702, 52590.391959799, 16, 12, 7)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('G', '2', 7206930, 52590.391959799, 16, 12, 7)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('H', '2', 7208159, 52590.391959799, 16, 12, 7)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('I', '3', 7204882, 26331.9798994975, 16, 12, 8)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('J', '3', 7206111, 26331.9798994975, 16, 12, 8)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('K', '3', 7207340, 26331.9798994975, 16, 12, 8)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('L', '3', 7208569, 26331.9798994975, 16, 12, 8)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('A', '4', 7204063, 7132.2211055276, 15, 11, 9)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('B', '4', 7205292, 7132.2211055276, 15, 11, 9)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('C', '4', 7206521, 7132.2211055276, 15, 11, 9)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('D', '4', 7207750, 7132.2211055276, 15, 11, 9)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('E', '5', 7204473, 2301.4874371859, 15, 9, 9)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('F', '5', 7205702, 2301.4874371859, 15, 9, 9)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('G', '5', 7206930, 2301.4874371859, 15, 9, 9)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('H', '5', 7208159, 2301.4874371859, 15, 9, 9)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('I', '6', 7204882, 964.7236180905, 26, 7, 9)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('J', '6', 7206111, 964.7236180905, 26, 7, 9)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('K', '6', 7207340, 964.7236180905, 26, 7, 9)
        DatabaseHelper.save_channel(channel)
        channel = ChannelData('L', '6', 7208569, 964.7236180905, 26, 7, 9)
        DatabaseHelper.save_channel(channel)
