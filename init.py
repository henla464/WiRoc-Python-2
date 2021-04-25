__author__ = 'henla464'

from flask import Flask
from flask_swagger_ui import get_swaggerui_blueprint
import subprocess

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


# if python < 3.5 then create the subprocess.run
try:
    from subprocess import CompletedProcess
except ImportError:
    class CompletedProcess:
        def __init__(self, args, returncode, stdout=None, stderr=None):
            self.args = args
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr
        def check_returncode(self):
            if self.returncode != 0:
                err = subprocess.CalledProcessError(self.returncode, self.args, output=self.stdout)
                raise err
            return self.returncode
    def sp_run(*popenargs, **kwargs):
        print(kwargs)
        input = kwargs.pop("input", None)
        print(kwargs)
        check = kwargs.pop("check", False)
        print(kwargs)
        if input is not None:
            if 'stdin' in kwargs:
                raise ValueError('stdin and input arguments may not both be used.')
            kwargs['stdin'] = subprocess.PIPE
        process = subprocess.Popen(*popenargs, **kwargs)
        try:
            outs, errs = process.communicate(input)
        except:
            process.kill()
            process.wait()
            raise
        returncode = process.poll()
        if check and returncode:
            raise subprocess.CalledProcessError(returncode, popenargs, output=outs)
        return CompletedProcess(popenargs, returncode, stdout=outs, stderr=errs)
    subprocess.run = sp_run
    # ^ This monkey patch allows it work on Python 2 or 3 the same way
