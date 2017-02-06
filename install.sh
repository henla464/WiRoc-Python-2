#!/bin/bash



echo "update"
read line
# update app list
apt-get update

echo "sqlite3"
read line
#Install sqlite3
apt-get install libsqlite3-dev

echo "python/pip"
read line
#Install python/pip
apt-get install python3
apt-get install python3-pip

echo "flask"
read line
#Install flask
pip3 install flask

echo "pyserial"
read line
#Install serial
pip3 install pyserial

echo "jsonpickle"
read line
#Install jsonpickle
pip3 install jsonpickle

echo "pyudev"
read line
#Install pyudev
pip3 install pyudev

echo "newer nodejs"
read line
#Install newer nodejs
wget https://nodejs.org/dist/v6.9.1/node-v6.9.1-linux-armv7l.tar.xz
tar -C /usr/local --strip-components 1 -xJf node-v6.9.1-linux-armv7l.tar.xz
ln -s /usr/local/bin/node /usr/bin/nodejs
ln -s /usr/local/bin/npm /usr/bin/npm





read -n1 -r -p "Press space to continue..." key

if [ "$key" = '' ]; then
    # Space pressed, do something
    # echo [$key] is empty when SPACE is pressed # uncomment to trace
else
    # Anything else pressed, do whatever else.
    # echo [$key] not empty
fi
