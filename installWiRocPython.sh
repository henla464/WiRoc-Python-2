#!/bin/bash
echo "start update wiroc python"
WiRocPython2Version=${1/v/}
systemctl stop WiRocPython
systemctl stop WiRocPythonWS
echo "after stop WiRocPython and WiRocPythonWS"
wget -O WiRoc-Python-2.tar.gz https://github.com/henla464/WiRoc-Python-2/archive/v$WiRocPython2Version.tar.gz
echo "after wget"
rm -rf WiRoc-Python-2
echo "after rf"
tar xvfz WiRoc-Python-2.tar.gz WiRoc-Python-2-$WiRocPython2Version
echo "after tar"
mv WiRoc-Python-2-$WiRocPython2Version WiRoc-Python-2
echo "after mv"
systemctl start WiRocPython
systemctl start WiRocPythonWS
echo "after start WirocPython and WiRocPythonWS"

