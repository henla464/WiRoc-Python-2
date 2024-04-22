__author__ = 'henla464'

import sqlite3 as lite
import datetime
import logging

from databaselib.datamapping import DataMapping


class DB:
    WiRocLogger = logging.getLogger('WiRoc')

    def __init__(self, database_file_path: str, data_mapping: DataMapping):
        if lite.threadsafety == 3:
            check_same_thread = False
        else:
            self.WiRocLogger.error("DB::__init__() SQLite3 database is not threadsafe")
            check_same_thread = True

        self.connection = lite.connect(database_file_path, timeout=100, check_same_thread=check_same_thread)
        self.connection.row_factory = lite.Row
        self.data_mapping = data_mapping
        self.execute_SQL("PRAGMA journal_mode=WAL")

    @staticmethod
    def _get_python_type(table_object, column_name: str):
        for column in table_object.columns:
            if column[0] == column_name:
                return column[1]

    def _get_table_object(self, table_class, row):
        table_object = table_class()
        for column_name in row.keys():
            python_type = DB._get_python_type(table_object, column_name)
            python_value = self.data_mapping.get_python_value(python_type, row[column_name])
            setattr(table_object, column_name, python_value)
        return table_object

    def drop_table(self, table_object) -> None:
        with self.connection:
            table_name = table_object.__class__.__name__
            drop_table_SQL_statement = "DROP TABLE " + table_name
            self.connection.execute(drop_table_SQL_statement)

    def ensure_table_created(self, table_object) -> None:
        with self.connection:
            table_name = table_object.__class__.__name__
            create_table_SQL_statement = "CREATE TABLE IF NOT EXISTS " + table_name \
                                         + "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
            create_table_SQL_statement += ", ".join(column_name + " "
                                                    + self.data_mapping.get_database_type(python_type)
                                                    for column_name, python_type in table_object.__class__.columns)
            create_table_SQL_statement += ")"
            DB.WiRocLogger.debug(create_table_SQL_statement)
            self.connection.execute(create_table_SQL_statement)

    def save_table_object(self, table_object, returnObj: bool = True):
        #with self.connection:
        table_name = table_object.__class__.__name__
        rowid = table_object.id
        if table_object.id is None:
            table_object.CreatedDate = datetime.datetime.now()

            column_list = ", ".join(column_name for column_name, column_type in table_object.__class__.columns)
            value_list = ", ".join('?' for i in range(len(table_object.__class__.columns)))
            SQL_statement = "INSERT INTO %s(%s) VALUES (%s)" % (table_name, column_list, value_list)
        else:
            set_list = ", ".join(column_name + " = ?"
                                 for column_name, column_type in table_object.__class__.columns)
            SQL_statement = "UPDATE %s SET %s WHERE id = %s" % (table_name, set_list, str(rowid))

        valuesTuple = tuple(self.data_mapping.get_database_value(getattr(table_object, column_name))
                                for column_name, column_type in table_object.__class__.columns)
        db_cursor = self.connection.cursor()
        db_cursor.execute(SQL_statement, valuesTuple)
        self.connection.commit()
        if rowid is None:
            rowid = db_cursor.lastrowid
        if returnObj:
            return self.get_table_object(table_object.__class__, rowid)
        return rowid

    def get_table_object(self, table_class, rowid: int):
        #self.connection.row_factory = lite.Row
        db_cursor = self.connection.cursor()
        select_SQL_statement = "SELECT * FROM %s WHERE id = %s" % (table_class.__name__, rowid)
        db_cursor.execute(select_SQL_statement)
        row = db_cursor.fetchone()
        if row is None:
            return None
        table_object = self._get_table_object(table_class, row)
        return table_object

    def get_scalar_by_SQL(self, select_SQL_statement: str, parameters: tuple[any, ...] = None) -> any:
        #with self.connection:
        #    self.connection.row_factory = lite.Row
        db_cursor = self.connection.cursor()
        if parameters is not None:
            db_cursor.execute(select_SQL_statement, parameters)
        else:
            db_cursor.execute(select_SQL_statement)
        first = db_cursor.fetchone()
        if first is None:
            return None
        else:
            return first[0]

    def get_table_objects_by_SQL(self, table_class, select_SQL_statement, parameters=None):
        db_cursor = self.connection.cursor()
        if parameters is None:
            db_cursor.execute(select_SQL_statement)
        else:
            db_cursor.execute(select_SQL_statement, parameters)
        rows = db_cursor.fetchall()
        get_table_object_func = self._get_table_object
        table_objects = [get_table_object_func(table_class, row) for row in rows]
        return table_objects

    def delete_table_object(self, table_class, rowId: int):
        #with self.connection:
        #    self.connection.row_factory = lite.Row
        #    db_cursor = self.connection.cursor()
        delete_SQL_statement = "DELETE FROM %s WHERE id = %s" % (table_class.__name__, rowId)
        #db_cursor.execute(delete_SQL_statement)
        self.connection.execute(delete_SQL_statement)
        self.connection.commit()

    def execute_SQL(self, SQL_statement: str, parameters = None):
        if parameters is None:
            self.connection.execute(SQL_statement)
        else:
            self.connection.execute(SQL_statement, parameters)
        self.connection.commit()

    def execute_SQL_no_commit(self, SQL_statement: str):
        self.connection.execute(SQL_statement)

    def execute_many_SQL(self, SQL_statement: str, listOfValues):
        self.connection.executemany(SQL_statement, listOfValues)
        self.connection.commit()

    def get_table_objects(self, table_class):
        table_name = table_class.__name__
        select_SQL_statement = "SELECT * FROM " + table_name
        return self.get_table_objects_by_SQL(table_class, select_SQL_statement)


