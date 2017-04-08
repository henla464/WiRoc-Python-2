__author__ = 'henla464'

import logging, logging.handlers
from datamodel.db_helper import DatabaseHelper
from init import *
from webroutes import radioconfiguration
from webroutes import meosconfiguration
from webroutes import misc

def startWebServer():
    logging.info("startWebServer() Start web server")
    app.run(debug=True, host='0.0.0.0', use_reloader=False)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        filename='WiRocWS.log',
                        filemode='w')
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    rotFileHandler = logging.handlers.RotatingFileHandler('WiRocWS.log', maxBytes=20000000, backupCount=3)
    rotFileHandler.setFormatter(formatter)

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)

    # add the handler to the root logger
    logging.getLogger('').addHandler(rotFileHandler)
    logging.getLogger('').addHandler(console)

    startWebServer()







