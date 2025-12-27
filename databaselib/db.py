__author__ = 'henla464'

import os
import sqlite3 as lite
import datetime
import logging
import threading
import time
import traceback
from sqlite3 import Connection, OperationalError, Cursor
from typing import Any

from databaselib.datamapping import DataMapping


class DB:
    WiRocLogger = logging.getLogger('WiRoc')
    #opened: int = 0
    #closed: int = 0

    def __init__(self, database_file_path: str, data_mapping: DataMapping):
        if lite.threadsafety == 3:
            self.check_same_thread = False
        else:
            self.WiRocLogger.error("DB::__init__() SQLite3 database is not threadsafe")
            self.check_same_thread = True
        self.dbFilePath = database_file_path
        self.data_mapping = data_mapping

    def openConnection(self) -> Connection | None:
        #self.WiRocLogger.debug(f"DB::openConnection() PID: {os.getpid()} {threading.get_ident()}")
        connection = lite.connect(self.dbFilePath, timeout=10, check_same_thread=self.check_same_thread, isolation_level=None)
        try:
            #DB.opened = DB.opened + 1
            connection.row_factory = lite.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.commit()
            return connection
        except Exception as ex:
            self.WiRocLogger.exception(f"DB::openConnection() exception: {ex} {threading.get_ident()}")
            connection.close()
            #DB.closed = DB.closed + 1
            return None

    def closeConnection(self, connection: Connection):
        if connection is not None:
            connection.commit()
            connection.close()
            # we could open multiple connections so number of open and close is not always same, only most of the time.
            # So opened != closed temporarily now and then is ok.
            #DB.closed = DB.closed + 1
            #if DB.closed != DB.opened:
            #    stackTraceString: str = ''.join(traceback.format_stack())
            #    self.WiRocLogger.error(f"DB::closeConnection() DB opned {DB.opened} and DB closed {DB.closed} !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! {stackTraceString}")
        else:
            self.WiRocLogger.error(f"DB::closeConnection() connection null PID: {os.getpid()}")

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
        conn = self.openConnection()
        try:
            table_name = table_object.__class__.__name__
            drop_table_SQL_statement = "DROP TABLE " + table_name
            self._execute_SQL_retry(conn, drop_table_SQL_statement)
        finally:
            self.closeConnection(conn)

    def ensure_table_created(self, table_object) -> None:
        conn = self.openConnection()
        try:
            table_name = table_object.__class__.__name__
            create_table_SQL_statement = "CREATE TABLE IF NOT EXISTS " + table_name \
                                         + "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
            create_table_SQL_statement += ", ".join(column_name + " "
                                                    + self.data_mapping.get_database_type(python_type)
                                                    for column_name, python_type in table_object.__class__.columns)
            create_table_SQL_statement += ")"
            DB.WiRocLogger.debug(create_table_SQL_statement)
            self._execute_SQL_retry(conn, create_table_SQL_statement)
        finally:
            self.closeConnection(conn)

    def save_table_object(self, table_object, returnObj: bool = True):
        conn = self.openConnection()
        table_name = table_object.__class__.__name__
        rowid = table_object.id
        try:
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
            db_cursor = conn.cursor()
            try:
                newRowid = self._execute_cursor_SQL_lastrowid_retry(db_cursor, SQL_statement, valuesTuple)
                conn.commit()
                if rowid is None:
                    rowid = newRowid
            finally:
                db_cursor.close()
        finally:
            self.closeConnection(conn)
            if returnObj:
                return self.get_table_object(table_object.__class__, rowid)
            return rowid



    def get_table_object(self, table_class, rowid: int):
        conn = self.openConnection()
        try:
            db_cursor = conn.cursor()
            try:
                select_SQL_statement = "SELECT * FROM %s WHERE id = %s" % (table_class.__name__, rowid)
                row = self._execute_cursor_SQL_fetchone_retry(db_cursor, select_SQL_statement)
                if row is None:
                    return None
                table_object = self._get_table_object(table_class, row)
                return table_object
            finally:
                db_cursor.close()
        finally:
            self.closeConnection(conn)

    def get_scalar_by_SQL(self, select_SQL_statement: str, parameters: tuple[any, ...] = None) -> Any:
        conn = self.openConnection()
        try:
            db_cursor = conn.cursor()
            try:
                first = self._execute_cursor_SQL_fetchone_retry(db_cursor, select_SQL_statement, parameters)
                if first is None:
                    return None
                else:
                    return first[0]
            finally:
                db_cursor.close()
        finally:
            self.closeConnection(conn)

    def get_table_objects_by_SQL(self, table_class, select_SQL_statement, parameters=None):
        conn = self.openConnection()
        try:
            db_cursor = conn.cursor()
            try:
                rows = self._execute_cursor_SQL_fetchall_retry(db_cursor, select_SQL_statement, parameters)
                get_table_object_func = self._get_table_object
                table_objects = [get_table_object_func(table_class, row) for row in rows]
                return table_objects
            finally:
                db_cursor.close()
        finally:
            self.closeConnection(conn)

    def delete_table_object(self, table_class, rowId: int):
        conn = self.openConnection()
        try:
            delete_SQL_statement = "DELETE FROM %s WHERE id = %s" % (table_class.__name__, rowId)
            self._execute_SQL_retry(conn, delete_SQL_statement)
        finally:
            self.closeConnection(conn)

    def _execute_cursor_SQL_fetchone_retry(self, cursor: Cursor, SQL_statement: str, parameters=None) -> Any:
        timeout = 10
        for x in range(0, timeout):
            try:
                #DB.WiRocLogger.debug(
                #    f"DB::_execute_cursor_SQL_fetchone_retry() 1 {SQL_statement} PID: {os.getpid()} {threading.get_ident()}")
                if parameters is None:
                    cursor.execute(SQL_statement)
                    result = cursor.fetchone()
                else:
                    cursor.execute(SQL_statement, parameters)
                    result = cursor.fetchone()
                return result
            except OperationalError as ex:
                DB.WiRocLogger.debug(f"DB::_execute_cursor_SQL_fetchone_retry() Exception {ex} {SQL_statement}")
                time.sleep(0.01)
                continue
        DB.WiRocLogger.error(f"DB::_execute_cursor_SQL_fetchone_retry() ALL RETRIES FAILED {SQL_statement}")

    def _execute_cursor_SQL_fetchall_retry(self, cursor: Cursor, SQL_statement: str, parameters=None) -> Any:
        timeout = 10
        result = None
        for x in range(0, timeout):
            try:
                #DB.WiRocLogger.debug(
                #    f"DB::_execute_cursor_SQL_fetchall_retry() 1 {SQL_statement} PID: {os.getpid()} {threading.get_ident()}")
                if parameters is None:
                    cursor.execute(SQL_statement)
                    result = cursor.fetchall()
                else:
                    cursor.execute(SQL_statement, parameters)
                    result = cursor.fetchall()
                return result
            except OperationalError as ex:
                DB.WiRocLogger.debug(f"DB::_execute_cursor_SQL_fetchall_retry() Exception {ex} {SQL_statement}")
                time.sleep(0.01)
                continue
        DB.WiRocLogger.error(f"DB::_execute_cursor_SQL_fetchall_retry() ALL RETRIES FAILED {SQL_statement}")

    def _execute_cursor_SQL_lastrowid_retry(self, cursor: Cursor, SQL_statement: str, parameters=None) -> int | None:
        timeout = 10
        result = None
        for x in range(0, timeout):
            try:
                #DB.WiRocLogger.debug(
                #    f"DB::_execute_cursor_SQL_lastrowid_retry() 1 {SQL_statement} PID: {os.getpid()} {threading.get_ident()}")
                if parameters is None:
                    cursor.execute(SQL_statement)
                    result = cursor.lastrowid
                else:
                    cursor.execute(SQL_statement, parameters)
                    result = cursor.lastrowid
                return result
            except OperationalError as ex:
                DB.WiRocLogger.debug(f"DB::_execute_cursor_SQL_fetchall_retry() Exception {ex} {SQL_statement}")
                time.sleep(0.01)
                continue
        DB.WiRocLogger.error(
            f"DB::_execute_cursor_SQL_lastrowid_retry() ALL RETRIES FAILED {SQL_statement} PID: {os.getpid()} {threading.get_ident()}")

    def _execute_SQL_retry(self, conn: Connection, SQL_statement: str, parameters=None):
        timeout = 10
        for x in range(0, timeout):
            try:
                #DB.WiRocLogger.debug(f"DB::_execute_SQL_retry() 1 {SQL_statement} PID: {os.getpid()} {threading.get_ident()}")
                if parameters is None:
                    conn.execute(SQL_statement)
                else:
                    conn.execute(SQL_statement, parameters)
                return
            except OperationalError as ex:
                #DB.WiRocLogger.debug(f"DB::_execute_SQL_retry() Exception {ex} {SQL_statement} PID: {os.getpid()} {threading.get_ident()}")
                time.sleep(0.01)
                continue
        DB.WiRocLogger.error(
            f"DB::_execute_SQL_retry() ALL RETRIES FAILED {SQL_statement} PID: {os.getpid()} {threading.get_ident()}")

    def execute_SQL(self, SQL_statement: str, parameters=None):
        #DB.WiRocLogger.debug(f"DB::execute_SQL() 1 {SQL_statement}")
        conn = self.openConnection()
        #DB.WiRocLogger.debug(f"DB::execute_SQL() 1.1")
        try:
            self._execute_SQL_retry(conn, SQL_statement, parameters)
        finally:
            #DB.WiRocLogger.debug("DB::execute_SQL() 2")
            self.closeConnection(conn)
        #DB.WiRocLogger.debug("DB::execute_SQL() 3")

    def get_table_objects(self, table_class):
        table_name = table_class.__name__
        select_SQL_statement = "SELECT * FROM " + table_name
        tableObjects = self.get_table_objects_by_SQL(table_class, select_SQL_statement)
        return tableObjects


