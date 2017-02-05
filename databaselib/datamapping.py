__author__ = 'henla464'

import datetime

class DataMapping:
    @staticmethod
    def get_database_type(python_type):
        if python_type.__name__ == "str":
            return "TEXT"
        if python_type.__name__ == "datetime":
            return "TIMESTAMP"
        if python_type.__name__ == "bool":
            return "INT"
        if python_type.__name__ == "float":
            return "REAL"
        if python_type.__name__ == "bytearray":
            return "BLOB"

        return "INT"

    @staticmethod
    def get_database_value(column_value):
        if column_value is None:
            return None
        if type(column_value) is str or type(column_value) is datetime.datetime:
            return str(column_value)
        if type(column_value) is bool:
            if column_value:
                return 1
            else:
                return 0
        #return str(column_value)
        return column_value

    @staticmethod
    def get_python_value(python_type, column_value):
        if column_value is None:
            return None
        if python_type is datetime.datetime:
            return datetime.datetime.strptime(column_value, '%Y-%m-%d %H:%M:%S.%f')
        if python_type is bool:
            return column_value != 0
        return column_value