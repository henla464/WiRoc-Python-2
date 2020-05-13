__author__ = 'henla464'

from flask import Flask
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask("__main__")


### swagger specific ###
SWAGGER_URL = '/api/swagger'
API_URL = '/api/openapicontent'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "WiRoc API"
    }
)
app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)
### end swagger specific ###


class MicroMock(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)