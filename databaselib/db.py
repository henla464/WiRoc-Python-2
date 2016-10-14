__author__ = 'henla464'

import sqlite3 as lite
import datetime
from datamodel.datamodel import SettingData

class DB:

    def __init__(self, database_file_path, data_mapping):
        self.connection = lite.connect(database_file_path, timeout=100)
        self.data_mapping = data_mapping

    @staticmethod
    def _get_python_type(table_object, column_name):
        for column in table_object.columns:
            if column[0] == column_name:
                return column[1]

    def _get_table_object(self, table_class, row):
        table_object = table_class()

        for column_name in row.keys():
            print(column_name)
            python_type = DB._get_python_type(table_object, column_name)
            python_value = self.data_mapping.get_python_value(python_type, row[column_name])
            setattr(table_object, column_name, python_value)
        return table_object

    def drop_table(self, table_object):
        with self.connection:
            table_name = table_object.__class__.__name__
            drop_table_SQL_statement = "DROP TABLE " + table_name
            self.connection.execute(drop_table_SQL_statement)

    def ensure_table_created(self, table_object):
        with self.connection:
            table_name = table_object.__class__.__name__
            create_table_SQL_statement = "CREATE TABLE IF NOT EXISTS " + table_name \
                                         + "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
            create_table_SQL_statement += ", ".join(column_name + " "
                                                    + self.data_mapping.get_database_type(python_type)
                                                    for column_name, python_type in table_object.__class__.columns)
            create_table_SQL_statement += ")"
            print(create_table_SQL_statement)
            self.connection.execute(create_table_SQL_statement)


    def save_table_object(self, table_object):
        with self.connection:
            table_name = table_object.__class__.__name__
            rowid = table_object.id

            if table_object.id is None:
                table_object.createdDate = datetime.datetime.now()
                SQL_statement = "INSERT INTO " + table_name + "("
                column_list = ", ".join(column_name for column_name, column_type in table_object.__class__.columns)
                SQL_statement += column_list + ") VALUES ("
                SQL_statement += ", ".join(self.data_mapping.get_database_value(getattr(table_object, column_name))
                                           for column_name, column_type in table_object.__class__.columns)
                SQL_statement += ")"
            else:
                SQL_statement = "UPDATE " + table_name + " SET "
                SQL_statement += ", ".join(column_name + " = " +
                                           self.data_mapping.get_database_value(getattr(table_object, column_name))
                                           for column_name, column_type in table_object.__class__.columns)
                SQL_statement += " WHERE id = " + str(table_object.id)

            db_cursor = self.connection.cursor()
            print(SQL_statement)
            db_cursor.execute(SQL_statement)
            if rowid is None:
                rowid = db_cursor.lastrowid
            return self.get_table_object(table_object.__class__, rowid)

    def get_table_object(self, table_class, rowid):
        with self.connection:
            self.connection.row_factory = lite.Row
            db_cursor = self.connection.cursor()
            table_name = table_class.__name__
            select_SQL_statement = "SELECT * FROM " + table_name + " WHERE id = " + str(rowid)
            print(select_SQL_statement)
            db_cursor.execute(select_SQL_statement)
            row = db_cursor.fetchone()
            table_object = self._get_table_object(table_class, row)
            return table_object

    def get_table_objects_by_SQL(self, table_class, select_SQL_statement):
        with self.connection:
            self.connection.row_factory = lite.Row
            db_cursor = self.connection.cursor()
#            if table_class is SettingData:
#                print(select_SQL_statement)
            db_cursor.execute(select_SQL_statement)
            rows = db_cursor.fetchall()
            table_objects = []
            for row in rows:
                table_object = self._get_table_object(table_class, row)
                table_objects.append(table_object)
            return table_objects

    def execute_SQL(self, SQL_statement):
        with self.connection:
            self.connection.execute(SQL_statement)

    def get_table_objects(self, table_class):
        table_name = table_class.__name__
        select_SQL_statement = "SELECT * FROM " + table_name
        return self.get_table_objects_by_SQL(table_class, select_SQL_statement)


# db = DB("test.db");
# acc = AccelerationData()
# db.ensure_table_created(acc)
# acc.id = None
# acc.xAcc = 0
# acc.yAcc = 2
# acc.zAcc = 3
# acc.comment = "hej hoppsan 2"
# #db.save_table_object(acc)
# theObject = db.get_table_object(AccelerationData, 1)
# print(vars(theObject))
# theObject = db.get_table_object(AccelerationData, 2)
# print(vars(theObject))
#
# theObjects = db.get_table_objects(AccelerationData)
# print(vars(theObjects[4]))
