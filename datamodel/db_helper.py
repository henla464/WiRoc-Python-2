__author__ = 'henla464'

from datamodel.datamodel import RadioMessageData
from datamodel.datamodel import PunchData
from datamodel.datamodel import NodeSettingsData
from datamodel.datamodel import InboundRadioNodeData
from datamodel.datamodel import NodeToControlNumberData
from datamodel.datamodel import MainSettingsData
from datamodel.datamodel import RadioSettingsData
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
        radioMessageData = RadioMessageData()
        db.ensure_table_created(radioMessageData)
        punchData = PunchData()
        db.ensure_table_created(punchData)
        nodeSettingsData = NodeSettingsData()
        db.ensure_table_created(nodeSettingsData)
        inboundRadioNodeData = InboundRadioNodeData()
        db.ensure_table_created(inboundRadioNodeData)
        mainSettingsData = MainSettingsData()
        db.ensure_table_created(mainSettingsData)
        radioSettingsData = RadioSettingsData()
        db.ensure_table_created(radioSettingsData)
        channelData = ChannelData()
        db.ensure_table_created(channelData)
        nodeToControlNumberData = NodeToControlNumberData()
        db.ensure_table_created(nodeToControlNumberData)

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

 #   @staticmethod
 #   def get_node_settings_data():
 #       db = DB(DatabaseHelper.database_name, DataMapping())
 #       row_list = db.get_table_objects_by_SQL(NodeSettingsData, "SELECT * FROM NodeSettingsData ORDER BY id desc LIMIT 1")
 #       if len(row_list) == 0:
 #           return None
 #       node_settings = row_list[0]
 #       inbound_node_list = db.get_table_objects_by_SQL(InboundRadioNodeData, "SELECT * FROM InboundRadioNodeData ORDER BY id desc")
 #       node_settings.InboundRadioNodes = inbound_node_list
#        return node_settings

 #   @staticmethod
 #   def save_node_settings(node_settings_data):
 #       db = DB(DatabaseHelper.database_name, DataMapping())
 #       print("save nodes settings")
 #       print(node_settings_data.id)
 #       db.save_table_object(node_settings_data)
 #       for node in node_settings_data.InboundRadioNodes:
 #           db.save_table_object(node)
 #       return DatabaseHelper.get_node_settings_data()


    @staticmethod
    def get_main_settings_data():
        db = DB(DatabaseHelper.database_name, DataMapping())
        row_list = db.get_table_objects_by_SQL(MainSettingsData, "SELECT * FROM MainSettingsData ORDER BY id desc LIMIT 1")
        if len(row_list) == 0:
            return None
        main_settings = row_list[0]

        node_to_control_number_list = db.get_table_objects_by_SQL(NodeToControlNumberData, "SELECT * FROM NodeToControlNumberData ORDER BY id asc")
        main_settings.NodeToControlNumberMapping = node_to_control_number_list
        return main_settings

    @staticmethod
    def save_main_settings(main_settings_data):
        db = DB(DatabaseHelper.database_name, DataMapping())
        old_main_settings_data = DatabaseHelper.get_main_settings_data()
        if old_main_settings_data is not None:
            main_settings_data.id = old_main_settings_data.id
        db.save_table_object(main_settings_data)
        db.execute_SQL("DELETE FROM NodeToControlNumberData")
        for nodeToControl in main_settings_data.NodeToControlNumberMapping:
            db.save_table_object(nodeToControl)
        return DatabaseHelper.get_main_settings_data()

    @staticmethod
    def ensure_main_settings_exists():
        main_settings = DatabaseHelper.get_main_settings_data()
        if main_settings is None:
            main_setting = MainSettingsData()
            DatabaseHelper.save_main_settings(main_setting)

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
        mainSettingsData = MainSettingsData()
        db.drop_table(mainSettingsData)
        radioSettingsData = RadioSettingsData()
        db.drop_table(radioSettingsData)
        channelData = ChannelData()
        db.drop_table(channelData)

    @staticmethod
    def get_radio_settings_data(radioSettingsId=None):
        db = DB(DatabaseHelper.database_name, DataMapping())
        sql = ""
        if radioSettingsId is None:
            sql = "SELECT * FROM RadioSettingsData ORDER BY id"
        elif radioSettingsId is int:
            sql = "SELECT * FROM RadioSettingsData WHERE id = " + str(radioSettingsId)

        row_list = db.get_table_objects_by_SQL(RadioSettingsData, sql)
        for radioSetting in row_list:
            nodes = db.get_table_objects_by_SQL(InboundRadioNodeData, "SELECT * FROM InboundRadioNodeData WHERE RadioSettingsId = " + str(radioSetting.id))
            radioSetting.InboundRadioNodes = nodes

        return row_list

    @staticmethod
    def save_radio_settings(radio_settings_data):
        db = DB(DatabaseHelper.database_name, DataMapping())
        print("save radio settings")
        saved_radio_settings_data = db.save_table_object(radio_settings_data)
        print("save radio settings 2")
        db.execute_SQL("DELETE FROM InboundRadioNodeData WHERE RadioSettingsId = " + str(saved_radio_settings_data.id))
        for node in radio_settings_data.InboundRadioNodes:
            node.id = None
            node.RadioSettingsId = saved_radio_settings_data.id
            db.save_table_object(node)
        return DatabaseHelper.get_radio_settings_data(saved_radio_settings_data.id)

    @staticmethod
    def ensure_radio_settings_exists(all_radio_numbers):
        # create radiosettings for new radios
        radio_settings = DatabaseHelper.get_radio_settings_data()
        for radio_number in all_radio_numbers:
            radio_numbers_in_database = [radio_setting.RadioNumber for radio_setting in radio_settings]
            if not radio_number in radio_numbers_in_database:
                # create new radio setting
                radio_setting = RadioSettingsData()
                radio_setting.RadioNumber = radio_number
                DatabaseHelper.save_radio_settings(radio_setting)
            else:
                existing_radio_setting = next((radio_sett for radio_sett in radio_settings if radio_sett.RadioNumber == radio_number), None)
                if existing_radio_setting is not None:
                    existing_radio_setting.RadioExists = True
                    DatabaseHelper.save_radio_settings(existing_radio_setting)

        saved_radio_settings = DatabaseHelper.get_radio_settings_data()
        for saved_radio_setting in saved_radio_settings:
            if not saved_radio_setting.RadioNumber in all_radio_numbers:
                saved_radio_setting.RadioExists = False
                DatabaseHelper.save_radio_settings(saved_radio_setting)

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