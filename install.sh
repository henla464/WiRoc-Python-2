#!/bin/bash
#systemctl disable apt-daily.service # disable run when system boot
#systemctl disable apt-daily.timer   # disable timer run



echo "This script is tested on OS release:"
echo "Armbian Linux 6.6.72-current-sunxi"
echo "Description:	Armbian_community 25.2.0-trunk.377 noble"
echo "Release:	24.04"
echo "Codename:	noble"

# Current OS
echo ""
echo "Current release:"
lsb_release --all

WiRocPython2Version="0.279"
echo "Which WiRocPython2Version? [$WiRocPython2Version]"
read wPOption
if ! [[ -z "$wPOption" ]];
then
    WiRocPython2Version=$wPOption
fi

WiRocBLEVersion="0.14"
echo "Which WiRocBLEVersion? [$WiRocBLEVersion]"
read wBLEOption
if ! [[ -z "$wBLEOption" ]];
then
    WiRocBLEVersion=$wBLEOption
fi

echo "Which hardware is this runnig on: 3: NanoPi, 4: NanoPi+SerialPort, 5: NanoPi+SerialPort+SRR, 6: NanoPi+SerialPort+SRR with pin headers, 7: NanoPi+SerialPort+SRR with pin headers (programming pins for SRR)"

read hwOption
WiRocHWVersion="v3Rev2"
if [[ $hwOption = 1 ]]; then
    WiRocHWVersion="v2Rev1"
fi
if [[ $hwOption = 2 ]]; then
    WiRocHWVersion="v2Rev2"
fi
if [[ $hwOption = 3 ]]; then
    WiRocHWVersion="v3Rev2"
fi
if [[ $hwOption = 4 ]]; then
    WiRocHWVersion="v4Rev1"
fi
if [[ $hwOption = 5 ]]; then
    WiRocHWVersion="v6Rev1"
fi
if [[ $hwOption = 6 ]]; then
    WiRocHWVersion="v7Rev1"
fi
if [[ $hwOption = 7 ]]; then
    WiRocHWVersion="v7Rev2"
fi



echo "Type the apikey, followed by [ENTER]:"
read apikey
cat << EOF > apikey.txt
${apikey}
EOF


echo "Settings.yaml"
cat << EOF > settings.yaml
WiRocDeviceName: WiRoc Device
WiRocPythonVersion: ${WiRocPython2Version}
WiRocBLEAPIVersion: ${WiRocBLEVersion}
WiRocHWVersion: ${WiRocHWVersion}
EOF


echo "update"
#read line
# update app list
#add-apt-repository ppa:deadsnakes/ppa
#apt-get update

apt-get -y intall net-tools
apt-get -y install git
apt-get -y install i2c-tools
apt-get -y install python3.11
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

echo "zip"
apt-get -y install zip
cd /home/chip/
mkdir LogArchive

echo "sqlite3"
#read line
#Install sqlite3
apt-get -y install libsqlite3-dev

echo "python/pip"
#read line
#Install python/pip


#apt-get -y install python3
apt-get -y install python3-pip
apt-get -y install python3-setuptools
apt-get -y install python3-dev
apt-get -y install python3.11-distutils
apt-get -y install gpiod
pip3 install -U setuptools
pip3 install wheel
pip3 install requests
pip3 install cachetools
#pip3 install reedsolo
pip3 install cython


apt-get -y install python3.11-dev
pip3 install build
git clone https://github.com/tomerfiliba-org/reedsolomon.git
cd reedsolomon
pip3 install virtualenv
python3 -sBm build --config-setting="--build-option=--cythonize"
#export SETUPTOOLS_USE_DISTUTILS=stdlib 
export DEB_PYTHON_INSTALL_LAYOUT=deb_system
pip3 install dist/reedsolo-2.1.2b1-cp311-cp311-linux_armv7l.whl
cd /home/chip


#pip install reedsolo --pre
#pip3 install --upgrade reedsolo --no-binary "reedsolo" --no-cache --config-setting="--build-option=--cythonize" --use-pep517 --isolated --verbose
#pip3 install git+https://github.com/henla464/reedsolomon.git

# Dbus stuff required for BLE
#apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-4.0
#pip3 install pycairo
#pip3 install pgi
#pip3 install dasbus
#pip3 install pydbus
#


apt-get -y install libgirepository1.0-dev
apt-get -y install libcairo2-dev 
apt-get -y install pkg-config
export SETUPTOOLS_USE_DISTUTILS=stdlib 
pip3 install pycairo
python3 -m pip install --ignore-installed PyGObject
pip3 install dbus-python

#apt-get -y install python-dbus
#cp /usr/lib/python3/dist-packages/_dbus_bindings.cpython-310-arm-linux-gnueabihf.so /usr/lib/python3/dist-packages/_dbus_bindings.cpython-311-arm-linux-gnueabihf.so
#cp /usr/lib/python3/dist-packages/_dbus_glib_bindings.cpython-310-arm-linux-gnueabihf.so /usr/lib/python3/dist-packages/_dbus_glib_bindings.cpython-311-arm-linux-gnueabihf.so
ln -s /usr/lib/python3/dist-packages/_dbus_bindings.cpython-312-arm-linux-gnueabihf.so _dbus_bindings.so
ln -s _dbus_glib_bindings.cpython-312-arm-linux-gnueabihf.so _dbus_glib_bindings.so


pip3 install gpiod

echo "flask"
#read line
#Install flask
pip3 install --ignore-installed flask
pip3 install --ignore-installed flask-swagger-ui

echo "pyserial"
#read line
#Install serial
pip3 install pyserial

echo "jsonpickle"
#read line
#Install jsonpickle
pip3 install jsonpickle

pip3 install pyyaml

echo "pyudev"
#read line
#Install pyudev
pip3 install pyudev
pip3 install daemonize
pip3 install smbus2

pip3 install Adafruit-Blinka
pip3 install adafruit-circuitpython-ssd1306
#not actually used but it is loaded by gpio because it thinks chip is bb
#sudo apt-get install build-essential python3-dev python3-pip -y
#git clone https://github.com/adafruit/adafruit-beaglebone-io-python.git
#cd adafruit-beaglebone-io-python
#python3 setup.py install
#cd ..

#pip3 install Adafruit_SSD1306
apt-get -y install libtiff5-dev libjpeg-dev zlib1g-dev
apt-get -y install python3 python3-dev build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev
apt-get -y install libfreetype6-dev
#libjpeg62-turbo-dev
export SETUPTOOLS_USE_DISTUTILS=stdlib
pip3 install pillow
#apt-get install python3-pil
apt-get -y install python3-numpy


echo "Install bluetooth stuff"

# this old version no longer available on newer armbian
#cat << EOF > /etc/apt/preferences.d/bluez
#Package: bluez
#Pin: version 5.50-1.2~deb10u2
#Pin-Priority: 999
#EOF

# There is a problem with 5.50-1.2~deb10u3 that makes BLE writes and reads give errors. "u2" works. And it seems it is enough to downgrade bluez.
# Newer version seem to work too: https://www.makeuseof.com/install-bluez-latest-version-on-ubuntu/ (no need for --experimental) (5.66)
# bluez=5.50-1.2~deb10u2
apt-get -y install bluetooth bluez libbluetooth-dev libudev-dev




#wget -O WiRoc-Python-2.tar.gz https://github.com/henla464/WiRoc-Python-2/archive/v$WiRocPython2Version.tar.gz
#rm -rf WiRoc-Python-2
#tar xvfz WiRoc-Python-2.tar.gz WiRoc-Python-2-$WiRocPython2Version
#mv WiRoc-Python-2-$WiRocPython2Version WiRoc-Python-2
#mv WiRoc-Python-2/installWiRocPython.sh .
#chmod ugo+x installWiRocPython.sh


#echo "Update WiRocPython version"
#cat << EOF > WiRocPythonVersion.txt
#${WiRocPython2Version}
#EOF

echo "WiRoc-BLE"

#install WiRoc-BLE
wget -O WiRoc-BLE-API.tar.gz https://github.com/henla464/WiRoc-BLE-API/archive/v$WiRocBLEVersion.tar.gz
rm -rf WiRoc-BLE-API
tar xvfz WiRoc-BLE-API.tar.gz WiRoc-BLE-API-$WiRocBLEVersion
mv WiRoc-BLE-API-$WiRocBLEVersion WiRoc-BLE-API
mv WiRoc-BLE-API/installWiRocBLEAPI.sh .
chmod ugo+x installWiRocBLEAPI.sh
echo "Update WiRocBLEAPI version"

echo "WiRoc-Python-2"
wget https://raw.githubusercontent.com/henla464/WiRoc-Python-2/master/installWiRocPython.py
chmod ugo+x installWiRocPython.py
./installWiRocPython.py $WiRocPython2Version

echo "install startup scripts"
#read line
#Startup scripts:
mkdir WiRoc-StartupScripts
wget -O /home/chip/WiRoc-StartupScripts/Startup.sh https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/Startup.sh
chmod +x /home/chip/WiRoc-StartupScripts/Startup.sh
if [[ $(hostname -s) = nanopiair ]]; then
    echo "nanopiair"
    wget -O /usr/bin/devmem2 https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/devmem2
    chmod ugo+x /usr/bin/devmem2
    wget -O /etc/systemd/system/WiRocBLEAPI.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocBLEAPI.service
    systemctl enable /etc/systemd/system/WiRocBLEAPI.service
else
    wget -O /home/chip/WiRoc-StartupScripts/setGPIOuart2 https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/setGPIOuart2
    chmod +x /home/chip/WiRoc-StartupScripts/setGPIOuart2
    wget -O /etc/systemd/system/WiRocBLE.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocBLE.service
    systemctl enable /etc/systemd/system/WiRocBLE.service
fi

wget -O /etc/systemd/system/WiRocPython.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocPython.service
wget -O /etc/systemd/system/WiRocPythonWS.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocPythonWS.service
wget -O /etc/systemd/system/WiRocStartup.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocStartup.service
systemctl enable /etc/systemd/system/WiRocStartup.service
systemctl enable /etc/systemd/system/WiRocPython.service
systemctl enable /etc/systemd/system/WiRocPythonWS.service


echo "install wiroc-watchdog"
mkdir WiRoc-WatchDog
wget -O /home/chip/WiRoc-WatchDog/WiRoc-WatchDog.py https://raw.githubusercontent.com/henla464/WiRoc-WatchDog/master/WiRoc-WatchDog.py
chmod +x /home/chip/WiRoc-WatchDog/WiRoc-WatchDog.py
wget -O /etc/systemd/system/WiRocWatchDog.service https://raw.githubusercontent.com/henla464/WiRoc-WatchDog/master/WiRocWatchDog.service
systemctl enable /etc/systemd/system/WiRocWatchDog.service

echo "add user to dialout"
sudo usermod -a -G dialout $USER




echo "nanopiair"
if ! grep -Fxq "setenv video-mode sunxi:1920x1080,monitor=none,hpd=0,edid=1" /boot/boot.cmd
then
    sed -i '$a setenv video-mode sunxi:1920x1080,monitor=none,hpd=0,edid=1' /boot/boot.cmd
    sed -i '$a saveenv' /boot/boot.cmd
    mkimage -C none -A arm -T script -d /boot/boot.cmd /boot/boot.scr
    echo "Changed boot.cmd and recompiled it"
fi

if [ "$hwVersion" = "v1Rev1" ] || [ "$hwVersion" = "v2Rev1" ] || [ "$hwVersion" = "v3Rev1" ] || [ "$hwVersion" = "v3Rev2" ]
then
   if ! grep -Fxq "overlays=uart1 uart3 usbhost1 usbhost2 usbhost3 i2c0" /boot/armbianEnv.txt
   then
       echo "Change overlays"
       sed -i -E "s/(overlays=).*/overlays=uart1 uart3 usbhost1 usbhost2 usbhost3 i2c0/" /boot/armbianEnv.txt
   fi
else
   if ! grep -Fxq "overlays=uart1 uart2 uart3 usbhost1 usbhost2 usbhost3 i2c0" /boot/armbianEnv.txt
   then
       echo "Change overlays"
       sed -i -E "s/(overlays=).*/overlays=uart1 uart2 uart3 usbhost1 usbhost2 usbhost3 i2c0/" /boot/armbianEnv.txt
   fi
fi

# Might not be needed anymore... test without?
if ! grep -Fxq "param_uart3_rtscts=1" /boot/armbianEnv.txt
then
    echo "Change overlays, add uart3 rtscts"
    sed -i '$a param_uart3_rtscts=1' /boot/armbianEnv.txt
fi

# Add the RTC module
if [ "$hwVersion" = "v7Rev1" ] || [ "$hwVersion" = "v7Rev2" ]
then
  if ! grep -Fxq "rtc_pcf8563" /etc/modules
  then
    echo "add rtc_pcf8563 to /etc/modules"
    echo "rtc_pcf8563" >> /etc/modules
  fi

  if [ ! -f /usr/lib/udev/rules.d/51-udev-rtc.rules ]; then
    echo "Make symlink to rtc1 which probably is the pcf8563"
    echo 'SUBSYSTEM=="rtc", KERNEL=="rtc1", SYMLINK+="rtc", OPTIONS+="link_priority=-100"' >> /usr/lib/udev/rules.d/51-udev-rtc.rules
  fi
fi

# really not sure what is required anymore for it to work
# with x command echo 205 will never be found since that means it matches the whole line, not sure what we try to look for...
#if ! grep -Fxq "echo 205" /etc/init.d/ap6212-bluetooth
#then
#    echo "Replace ap6212-bluetooth"
#    cp /etc/init.d/ap6212-bluetooth ~/ap6212-bluetooth.backup
#    wget -O /etc/init.d/ap6212-bluetooth https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/ap6212-bluetooth
#    chmod ugo+x /etc/init.d/ap6212-bluetooth
#fi
#
#
#
#

if [ "$hwVersion" = "v1Rev1" ] || [ "$hwVersion" = "v2Rev1" ] || [ "$hwVersion" = "v3Rev1" ] || [ "$hwVersion" = "v3Rev2" ] || [ "$hwVersion" = "v4Rev1" ] || [ "$hwVersion" = "v5Rev1" ] || [ "$hwVersion" = "v6Rev1" ]
then
   :
else
   systemctl disable chrony
fi

# 
#if ! grep -Fq 'compat' /lib/systemd/system/bluetooth.service
#then
#    echo "change to compat mode"
#    sed -i -E "s@(ExecStart=).*@ExecStart=/usr/lib/bluetooth/bluetoothd --compat --noplugin=sap@" /lib/systemd/system/bluetooth.service
#    systemctl daemon-reload
#else
#    echo "compat"
#fi

# changed to new location for bluetooth.service
if ! grep -Fxq 'ExecStartPost=/usr/bin/sdptool add SP' /usr/lib/systemd/system/bluetooth.service
then
    echo "add SP profile"
    sed -i '/ExecStart=.*/a ExecStartPost=/usr/bin/sdptool add SP' /usr/lib/systemd/system/bluetooth.service
    systemctl daemon-reload
else
    echo "SP profile already exist"
fi



