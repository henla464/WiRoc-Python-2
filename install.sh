#!/bin/bash



echo "update"
#read line
# update app list
apt-get update

echo "sqlite3"
#read line
#Install sqlite3
apt-get -y install libsqlite3-dev

echo "python/pip"
#read line
#Install python/pip
apt-get -y install python3
apt-get -y install python3-pip

echo "flask"
#read line
#Install flask
pip3 install flask

echo "pyserial"
#read line
#Install serial
pip3 install pyserial

echo "jsonpickle"
#read line
#Install jsonpickle
pip3 install jsonpickle

echo "pyudev"
#read line
#Install pyudev
pip3 install pyudev

pip3 install daemonize

echo "newer nodejs"
#read line
#Install newer nodejs
wget https://nodejs.org/dist/v6.9.1/node-v6.9.1-linux-armv7l.tar.xz
tar -C /usr/local --strip-components 1 -xJf node-v6.9.1-linux-armv7l.tar.xz
ln -s /usr/local/bin/node /usr/bin/nodejs
ln -s /usr/local/bin/npm /usr/bin/npm

echo "Install python 2"
#read line
#Install python 2
apt-get -y install python

echo "Install bluetooth stuff"
#read line
#Install bluetooth stuff
apt-get -y install bluetooth bluez libbluetooth-dev libudev-dev

echo "WiRoc-Python-2"
#read line
#install Python-2
wget -O WiRoc-Python-2.tar.gz https://github.com/henla464/WiRoc-Python-2/archive/v0.74.tar.gz
rm -rf WiRoc-Python-2
tar xvfz WiRoc-Python-2.tar.gz WiRoc-Python-2-0.74
mv WiRoc-Python-2-0.74 WiRoc-Python-2

echo "WiRoc-BLE"
#read line
#install WiRoc-BLE
wget -O WiRoc-BLE-Device.tar.gz https://github.com/henla464/WiRoc-BLE-Device/archive/v0.15.tar.gz
rm -rf WiRoc-BLE-Device
tar xvfz WiRoc-BLE-Device.tar.gz WiRoc-BLE-Device-0.15
mv WiRoc-BLE-Device-0.15 WiRoc-BLE-Device

#npm install -g node-gyp
echo "install bluetooth-hci-socket"
cd /home/chip/
npm install bluetooth-hci-socket

echo "install bleno"
#read line
#install bleno
npm install bleno
wget -O /home/chip/node_modules/bleno/lib/bleno.js https://raw.githubusercontent.com/sandeepmistry/bleno/2548cc375646717ae76259d8a780159f9834b361/lib/bleno.js
wget -O /home/chip/node_modules/bleno/lib/hci-socket/acl-stream.js https://raw.githubusercontent.com/sandeepmistry/bleno/2548cc375646717ae76259d8a780159f9834b361/lib/hci-socket/acl-stream.js
wget -O /home/chip/node_modules/bleno/lib/hci-socket/bindings.js https://raw.githubusercontent.com/sandeepmistry/bleno/2548cc375646717ae76259d8a780159f9834b361/lib/hci-socket/bindings.js
wget -O /home/chip/node_modules/bleno/lib/hci-socket/hci.js https://raw.githubusercontent.com/sandeepmistry/bleno/2548cc375646717ae76259d8a780159f9834b361/lib/hci-socket/hci.js


echo "install startup scripts"
#read line
#Startup scripts:
mkdir WiRoc-StartupScripts
wget -O /home/chip/WiRoc-StartupScripts/Startup.sh https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/Startup.sh
chmod +x /home/chip/WiRoc-StartupScripts/Startup.sh
wget -O /home/chip/WiRoc-StartupScripts/setGPIOuart2 https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/setGPIOuart2
chmod +x /home/chip/WiRoc-StartupScripts/setGPIOuart2
wget -O /etc/systemd/system/WiRocPython.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocPython.service
wget -O /etc/systemd/system/WiRocPythonWS.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocPythonWS.service
wget -O /etc/systemd/system/WiRocBLE.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocBLE.service
wget -O /etc/systemd/system/WiRocStartup.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocStartup.service
#wget -O /etc/systemd/system/ifup-wait-all-auto.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/ifup-wait-all-auto.service
#systemctl enable /etc/systemd/system/ifup-wait-all-auto.service
systemctl enable /etc/systemd/system/WiRocStartup.service
systemctl enable /etc/systemd/system/WiRocBLE.service
systemctl enable /etc/systemd/system/WiRocPython.service
systemctl enable /etc/systemd/system/WiRocPythonWS.service

wget -O /etc/udev/rules.d/99-ttyexcludemm.rules https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/99-ttyexcludemm.rules
udevadm control --reload-rules


mkdir /lib/modules/4.4.13-ntc-mlc/kernel/drivers/usb/class
wget -O /lib/modules/4.4.13-ntc-mlc/kernel/drivers/usb/class/cdc-acm.ko https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/cdc-acm.ko
depmod
modprobe cdc-acm

echo "install new dtb"
#read line
#Install the new dtb on chip
rm /boot/sun5i-r8-chip.dtb
wget -O /boot/sun5i-r8-chip.dtb https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/sun5i-r8-chip.dtb


echo "install wiroc-monitor"
#read line
#Install WiRoc-Monitor
wget -O /usr/local/bin/gpio.sh https://raw.githubusercontent.com/henla464/WiRoc-Monitor/master/gpio.sh
wget -O /usr/local/bin/blink.sh https://raw.githubusercontent.com/henla464/WiRoc-Monitor/master/blink.sh
chmod +x /usr/local/bin/blink.sh
wget -O /etc/systemd/system/blink.service https://raw.githubusercontent.com/henla464/WiRoc-Monitor/master/blink.service
wget -O /usr/local/etc/blink.cfg https://raw.githubusercontent.com/henla464/WiRoc-Monitor/master/blink.cfg
systemctl enable /etc/systemd/system/blink.service

echo "add user to dialout"
#read line
sudo usermod -a -G dialout $USER


