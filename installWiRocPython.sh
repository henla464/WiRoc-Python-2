#!/bin/bash

WiRocPython2Version=${1/v/}
systemctl stop WiRocPython
systemctl stop WiRocPythonWS
wget -O WiRoc-Python-2.tar.gz https://github.com/henla464/WiRoc-Python-2/archive/v$WiRocPython2Version.tar.gz
rm -rf WiRoc-Python-2
tar xvfz WiRoc-Python-2.tar.gz WiRoc-Python-2-$WiRocPython2Version
mv WiRoc-Python-2-$WiRocPython2Version WiRoc-Python-2
systemctl start WiRocPython
systemctl start WiRocPythonWS

