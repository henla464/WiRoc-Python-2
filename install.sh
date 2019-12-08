#!/bin/bash
#systemctl disable apt-daily.service # disable run when system boot
#systemctl disable apt-daily.timer   # disable timer run

WiRocPython2Version="0.137"
WiRocBLEVersion="0.38"


echo "update"
#read line
# update app list
if [[ $(hostname -s) = nanopiair ]]; then
   apt-get update
else
   apt-key update
   apt-get -o Acquire::Check-Valid-Until=false update
fi

apt-get -y install git
apt-get -y install i2c-tools

echo "zip"
apt-get install zip
cd /home/chip/
mkdir LogArchive

echo "sqlite3"
#read line
#Install sqlite3
apt-get -y install libsqlite3-dev

echo "python/pip"
#read line
#Install python/pip
apt-get -y install python3
apt-get -y install python3-pip
apt-get -y install python3-setuptools
apt-get -y install python3-dev
pip3 install -U setuptools
pip3 install wheel
pip3 install requests
pip3 install cachetools


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
pip3 install smbus2

pip3 install Adafruit_BBIO==1.0.0 #not actually used but it is loaded by gpio because it thinks chip is bb
pip3 install Adafruit_SSD1306
apt-get -y install libtiff5-dev libjpeg62-turbo-dev zlib1g-dev
apt-get -y install libfreetype6-dev
# liblcms2-dev libwebp-dev libharfbuzz-dev 
#apt-get install libfribidi-dev 
#apt-get install tcl8.6-dev tk8.6-dev
pip3 install pillow
# nanopi: apt-get install python3-pillow

echo "newer nodejs"
#read line
#Install newer nodejs
wget https://nodejs.org/dist/v6.9.1/node-v6.9.1-linux-armv7l.tar.xz
#wget https://nodejs.org/dist/v8.11.3/node-v8.11.3-linux-armv7l.tar.xz
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
wget -O WiRoc-Python-2.tar.gz https://github.com/henla464/WiRoc-Python-2/archive/v$WiRocPython2Version.tar.gz
rm -rf WiRoc-Python-2
tar xvfz WiRoc-Python-2.tar.gz WiRoc-Python-2-$WiRocPython2Version
mv WiRoc-Python-2-$WiRocPython2Version WiRoc-Python-2
mv WiRoc-Python-2/installWiRocPython.sh .
chmod ugo+x installWiRocPython.sh


echo "Update WiRocPython version"
cat << EOF > WiRocPythonVersion.txt
${WiRocPython2Version}
EOF


echo "WiRoc-BLE"
#read line
#install WiRoc-BLE
wget -O WiRoc-BLE-Device.tar.gz https://github.com/henla464/WiRoc-BLE-Device/archive/v$WiRocBLEVersion.tar.gz
rm -rf WiRoc-BLE-Device
tar xvfz WiRoc-BLE-Device.tar.gz WiRoc-BLE-Device-$WiRocBLEVersion
mv WiRoc-BLE-Device-$WiRocBLEVersion WiRoc-BLE-Device
mv WiRoc-BLE-Device/installWiRocBLE.sh .
chmod ugo+x installWiRocBLE.sh


echo "Update WiRocBLE version"
cat << EOF > WiRocBLEVersion.txt
${WiRocBLEVersion}
EOF

#npm install -g node-gyp
echo "install bluetooth-hci-socket"
cd /home/chip/
npm --unsafe-perm install bluetooth-hci-socket

echo "install bleno"
#read line
#install bleno
#if [[ $(hostname -s) = nanopiair ]]; then
    npm install henla464/bleno
#else
#    npm install bleno
#    wget -O /home/chip/node_modules/bleno/lib/bleno.js https://raw.githubusercontent.com/sandeepmistry/bleno/2548cc375646717ae76259d8a780159f9834b361/lib/bleno.js
#    wget -O /home/chip/node_modules/bleno/lib/hci-socket/acl-stream.js https://raw.githubusercontent.com/sandeepmistry/bleno/2548cc375646717ae76259d8a780159f9834b361/lib/hci-socket/acl-stream.js
#    wget -O /home/chip/node_modules/bleno/lib/hci-socket/bindings.js https://raw.githubusercontent.com/sandeepmistry/bleno/2548cc375646717ae76259d8a780159f9834b361/lib/hci-socket/bindings.js
#    wget -O /home/chip/node_modules/bleno/lib/hci-socket/hci.js https://raw.githubusercontent.com/sandeepmistry/bleno/2548cc375646717ae76259d8a780159f9834b361/lib/hci-socket/hci.js
#fi

echo "install startup scripts"
#read line
#Startup scripts:
mkdir WiRoc-StartupScripts
wget -O /home/chip/WiRoc-StartupScripts/Startup.sh https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/Startup.sh
chmod +x /home/chip/WiRoc-StartupScripts/Startup.sh
if ! [[ $(hostname -s) = nanopiair ]]; then
    wget -O /home/chip/WiRoc-StartupScripts/setGPIOuart2 https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/setGPIOuart2
    chmod +x /home/chip/WiRoc-StartupScripts/setGPIOuart2
else
    wget -O /usr/bin/devmem2 https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/devmem2
    chmod ugo+x /usr/bin/devmem2
fi
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


echo "install wiroc-monitor"
#read line
#Install WiRoc-Monitor
wget -O /home/chip/WiRoc-WatchDog/gpio.sh https://raw.githubusercontent.com/henla464/WiRoc-WatchDog/master/gpio.sh
wget -O /home/chip/WiRoc-WatchDog/WiRoc-WatchDog.sh https://raw.githubusercontent.com/henla464/WiRoc-WatchDog/master/WiRoc-WatchDog.sh
chmod +x /home/chip/WiRoc-WatchDog/WiRoc-WatchDog.sh
wget -O /etc/systemd/system/WiRoc-WatchDog.service https://raw.githubusercontent.com/henla464/WiRoc-WatchDog/master/WiRoc-WatchDog.service
if [[ $(hostname -s) = nanopiair ]]; then
    echo "nanopiair"
    wget -O /home/chip/WiRoc-WatchDog/WiRoc-WatchDog.cfg https://raw.githubusercontent.com/henla464/WiRoc-WatchDog/master/WiRoc-WatchDog.cfg
else
    echo "chip"
    wget -O /home/chip/WiRoc-WatchDog/WiRoc-WatchDog.cfg https://raw.githubusercontent.com/henla464/WiRoc-WatchDog/master/WiRoc-WatchDog.chip.cfg
fi
systemctl enable /etc/systemd/system/WiRoc-WatchDog.service

echo "add user to dialout"
#read line
sudo usermod -a -G dialout $USER

echo "Type the apikey, followed by [ENTER]:"
read apikey
cat << EOF > apikey.txt
${apikey}
EOF





if [[ $(hostname -s) = nanopiair ]]; then
    echo "nanopiair"
    if ! grep -Fxq "setenv video-mode sunxi:1920x1080,monitor=none,hpd=0,edid=1" /boot/boot.cmd
    then
        sed -i '$a setenv video-mode sunxi:1920x1080,monitor=none,hpd=0,edid=1' /boot/boot.cmd
        sed -i '$a saveenv' /boot/boot.cmd
        mkimage -C none -A arm -T script -d /boot/boot.cmd /boot/boot.scr
        echo "Changed boot.cmd and recompiled it"
    fi

    if ! grep -Fxq "overlays=uart1 uart3 usbhost1 usbhost2 usbhost3 i2c0" /boot/armbianEnv.txt
    then
        echo "Change overlays"
        sed -i -E "s/(overlays=).*/overlays=uart1 uart3 usbhost1 usbhost2 i2c0/" /boot/armbianEnv.txt
    fi

    if ! grep -Fxq "param_uart3_rtscts=1" /boot/armbianEnv.txt
    then
        echo "Change overlays, add uart3 rtscts"
        sed -i '$a param_uart3_rtscts=1' /boot/armbianEnv.txt
    fi

    if ! grep -Fxq "PORT=ttyS3" /etc/default/ap6212
    then
        echo "Change to use ttyS3 for bluetooth"
        sed -i 's/PORT=ttyS1/PORT=ttyS3/' /etc/default/ap6212
    fi

    if ! grep -Fxq "echo 205" /etc/init.d/ap6212-bluetooth
    then
        echo "Replace ap6212-bluetooth"
        cp /etc/init.d/ap6212-bluetooth ~/ap6212-bluetooth.backup
        wget -O /etc/init.d/ap6212-bluetooth https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/ap6212-bluetooth
        chmod ugo+x /etc/init.d/ap6212-bluetooth
    fi

    wget -O /home/chip/bluez_5.43-2%2Bdeb9u1_armhf-fix.deb https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/bluez_5.43-2%2Bdeb9u1_armhf-fix.deb
    dpkg -i /home/chip/bluez_5.43-2%2Bdeb9u1_armhf-fix.deb

else
    mkdir /lib/modules/4.4.13-ntc-mlc/kernel/drivers/usb/class
    wget -O /lib/modules/4.4.13-ntc-mlc/kernel/drivers/usb/class/cdc-acm.ko https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/cdc-acm.ko
    depmod
    modprobe cdc-acm

    wget -O /etc/udev/rules.d/99-ttyexcludemm.rules https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/99-ttyexcludemm.rules
    udevadm control --reload-rules

    echo "install new dtb"
    #read line
    #Install the new dtb on chip
    rm /boot/sun5i-r8-chip.dtb
    wget -O /boot/sun5i-r8-chip.dtb https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/sun5i-r8-chip.dtb


fi
