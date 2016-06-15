__author__ = 'henla464'

from flask import Flask
app = Flask("__main__")

class MicroMock(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)