#!/bin/bash
#systemctl disable apt-daily.service # disable run when system boot
#systemctl disable apt-daily.timer   # disable timer run

# This parses yaml files and outputs rows on the format
# variable="value"
# group_varname="value2"
#
# use it with "eval $(parse_yaml sample.yml)"
function parse_yaml {
   local prefix=$2
   local s='[[:space:]]*' w='[a-zA-Z0-9_]*' fs=$(echo @|tr @ '\034')
   sed -ne "s|^\($s\):|\1|" \
        -e "s|^\($s\)\($w\)$s:$s[\"']\(.*\)[\"']$s\$|\1$fs\2$fs\3|p" \
        -e "s|^\($s\)\($w\)$s:$s\(.*\)$s\$|\1$fs\2$fs\3|p"  $1 |
   awk -F$fs '{
      indent = length($1)/2;
      vname[indent] = $2;
      for (i in vname) {if (i > indent) {delete vname[i]}}
      if (length($3) > 0) {
         vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])("_")}
         printf("%s%s%s=\"%s\"\n", "'$prefix'",vn, $2, $3);
      }
   }'
}


echo "This script is tested on OS release:"
echo "Armbian Linux 6.6.72-current-sunxi"
echo "Description:	Armbian_community 25.2.0-trunk.377 noble"
echo "Release:	24.04"
echo "Codename:	noble"

# Current OS
echo ""
echo "Current release:"
lsb_release --all

# Get the variables from the root settings yaml if it exists
SETTINGSFILE=/root/settings.yaml
if test -f "$SETTINGSFILE"; then
  echo "using /root/settings.yaml"
  eval $(parse_yaml "$SETTINGSFILE")
  echo "WiRoc Python 2 version: $WiRocPythonVersion"
  echo "WiRoc BLE API version: $WiRocBLEAPIVersion"
  echo "WiRoc HW Version: $WiRocHWVersion"
else
  WiRocPythonVersion="0.281"
  echo "Which WiRocPython2Version? [$WiRocPythonVersion]"
  read wPOption
  if ! [[ -z "$wPOption" ]];
  then
    WiRocPythonVersion=$wPOption
  fi

  WiRocBLEAPIVersion="0.14"
  echo "Which WiRocBLEAPIVersion? [$WiRocBLEAPIVersion]"
  read wBLEOption
  if ! [[ -z "$wBLEOption" ]];
  then
    WiRocBLEAPIVersion=$wBLEOption
  fi

  echo "Which hardware is this runnig on:"
  echo "3: NanoPi"
  echo "4: NanoPi+SerialPort"
  echo "5: NanoPi+SerialPort+SRR"
  echo "6: NanoPi+SerialPort+SRR with pin headers"
  echo "7: NanoPi+SerialPort+SRR with pin headers (programming pins for SRR)"

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
fi

# if apikey is available in root folder then use it
APIKEYFILE=/root/apikey.txt
if test -f "$APIKEYFILE"; then
  echo "$APIKEYFILE exists."
  cp /root/apikey.txt .
else
  echo "Type the apikey, followed by [ENTER]:"
  read apikey
cat << EOF > apikey.txt
${apikey}
EOF
fi




echo "Settings.yaml"
cat << EOF > settings.yaml
WiRocDeviceName: WiRoc Device
WiRocPythonVersion: ${WiRocPythonVersion}
WiRocBLEAPIVersion: ${WiRocBLEAPIVersion}
WiRocHWVersion: ${WiRocHWVersion}
EOF

apt-get -y install net-tools
apt-get -y install git
apt-get -y install i2c-tools


echo "zip"
apt-get -y install zip
cd /home/chip/
mkdir LogArchive

echo "sqlite3"
apt-get -y install libsqlite3-dev

echo "python/pip"
# needed for install scripts
apt-get -y install python3-pip
## venv ## apt-get -y install python3-setuptools
## venv ## apt-get -y install python3-dev
## venv ## apt-get -y install gpiod

# This allows pip to do system wide installs. Probably should change to use virtual environments though
python3 -m pip config set global.break-system-packages true

# WiRoc-Python
## venv ## pip3 install gpiod
## venv ## pip3 install --ignore-installed flask
## venv ## pip3 install --ignore-installed flask-swagger-ui
## venv ## pip3 install pyserial
## venv ## pip3 install jsonpickle
## venv ## pip3 install pyyaml
## venv ## pip3 install pyudev
## venv ## pip3 install daemonize
## venv ## pip3 install smbus2
## venv ## pip3 install Adafruit-Blinka
## venv ## pip3 install adafruit-circuitpython-ssd1306

#not actually used but it is loaded by gpio because it thinks chip is bb
#sudo apt-get install build-essential python3-dev python3-pip -y
#git clone https://github.com/adafruit/adafruit-beaglebone-io-python.git
#cd adafruit-beaglebone-io-python
#python3 setup.py install
#cd ..

apt-get -y install libgirepository1.0-dev
apt-get -y install libcairo2-dev 
apt-get -y install pkg-config
apt-get -y install python3.12-venv
pip3 install pycairo
python3 -m pip install --ignore-installed PyGObject

apt-get -y install libtiff5-dev libjpeg-dev zlib1g-dev
apt-get -y install python3-dev build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev
apt-get -y install libfreetype6-dev
apt-get -y install python3-numpy
## venv ## pip3 install pillow

## venv ## pip3 install -U setuptools
## venv ## pip3 install wheel

## venv ## pip3 install cachetools

# used in install scripts
pip3 install requests


# reedsolomon
pip3 install cython
pip3 install build
git clone https://github.com/tomerfiliba-org/reedsolomon.git
cd reedsolomon
pip3 install virtualenv
python3 -sBm build --config-setting="--build-option=--cythonize"
export DEB_PYTHON_INSTALL_LAYOUT=deb_system
# below filename changes with python version
pip3 install dist/reedsolo-2.1.2b1-cp312-cp312-linux_armv7l.whl
cd /home/chip

#pip install reedsolo --pre
#pip3 install --upgrade reedsolo --no-binary "reedsolo" --no-cache --config-setting="--build-option=--cythonize" --use-pep517 --isolated --verbose
#pip3 install git+https://github.com/henla464/reedsolomon.git


# WiRoc-BLE-API
## venv ## pip3 install dbus-python
ln -s /usr/lib/python3/dist-packages/_dbus_bindings.cpython-312-arm-linux-gnueabihf.so /usr/lib/python3/dist-packages/_dbus_bindings.so
ln -s /usr/lib/python3/dist-packages/_dbus_glib_bindings.cpython-312-arm-linux-gnueabihf.so /usr/lib/python3/dist-packages/_dbus_glib_bindings.so



echo "Install bluetooth stuff"

# There is a problem with 5.50-1.2~deb10u3 that makes BLE writes and reads give errors. "u2" works. And it seems it is enough to downgrade bluez.
# Newer version seem to work too: https://www.makeuseof.com/install-bluez-latest-version-on-ubuntu/ (no need for --experimental) (5.66)
# bluez=5.50-1.2~deb10u2
apt-get -y install bluetooth bluez libbluetooth-dev libudev-dev

##################################
echo "WiRoc-BLE"
###################################

wget -O WiRoc-BLE-API.tar.gz https://github.com/henla464/WiRoc-BLE-API/archive/v$WiRocBLEAPIVersion.tar.gz
rm -rf WiRoc-BLE-API
tar xvfz WiRoc-BLE-API.tar.gz WiRoc-BLE-API-$WiRocBLEAPIVersion
mv WiRoc-BLE-API-$WiRocBLEAPIVersion WiRoc-BLE-API
mv WiRoc-BLE-API/installWiRocBLEAPI.sh .
chmod ugo+x installWiRocBLEAPI.sh
echo "Update WiRocBLEAPI version"

apt-get -y install libdbus-1-dev
cd WiRoc-BLE-API
python3 -m venv env
source env/bin/activate
wget -O requirements.txt https://raw.githubusercontent.com/henla464/WiRoc-BLE-API/master/requirements.txt
env/bin/pip install -r requirements.txt
deactivate
cd /home/chip

wget -O /etc/systemd/system/WiRocBLEAPI.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocBLEAPI.service
systemctl enable /etc/systemd/system/WiRocBLEAPI.service


##################################
echo "WiRoc-Python-2"
###################################

wget -O installWiRocPython.py https://raw.githubusercontent.com/henla464/WiRoc-Python-2/master/installWiRocPython.py
chmod ugo+x installWiRocPython.py
./installWiRocPython.py $WiRocPythonVersion

cd WiRoc-Python-2
python3 -m venv env
source env/bin/activate
env/bin/pip install -r requirements.txt
sudo env/bin/pip install ../reedsolomon/dist/reedsolo-2.1.2b1-cp312-cp312-linux_armv7l.whl
deactivate
cd /home/chip

wget -O /etc/systemd/system/WiRocPython.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocPython.service
wget -O /etc/systemd/system/WiRocPythonWS.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocPythonWS.service
systemctl enable /etc/systemd/system/WiRocPython.service
systemctl enable /etc/systemd/system/WiRocPythonWS.service

###################################
echo "install startup scripts"
###################################

mkdir WiRoc-StartupScripts
wget -O /home/chip/WiRoc-StartupScripts/Startup.py https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/Startup.py
wget -O /home/chip/WiRoc-StartupScripts/requirements.txt https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/requirements.txt
chmod +x /home/chip/WiRoc-StartupScripts/Startup.py

cd WiRoc-StartupScripts
python3 -m venv env
source env/bin/activate
env/bin/pip install -r requirements.txt
deactivate
cd /home/chip

echo "nanopiair"
wget -O /usr/bin/devmem2 https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/devmem2
chmod ugo+x /usr/bin/devmem2

wget -O /etc/systemd/system/WiRocStartup.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocStartup.service
systemctl enable /etc/systemd/system/WiRocStartup.service

###################################
echo "install wiroc-watchdog"
###################################

mkdir WiRoc-WatchDog
wget -O /home/chip/WiRoc-WatchDog/WiRoc-WatchDog.py https://raw.githubusercontent.com/henla464/WiRoc-WatchDog/master/WiRoc-WatchDog.py
wget -O /home/chip/WiRoc-WatchDog/requirements.txt https://raw.githubusercontent.com/henla464/WiRoc-WatchDog/master/requirements.txt
chmod +x /home/chip/WiRoc-WatchDog/WiRoc-WatchDog.py

cd WiRoc-WatchDog
python3 -m venv env
source env/bin/activate
env/bin/pip install -r requirements.txt
deactivate
cd /home/chip

wget -O /etc/systemd/system/WiRocWatchDog.service https://raw.githubusercontent.com/henla464/WiRoc-WatchDog/master/WiRocWatchDog.service
systemctl enable /etc/systemd/system/WiRocWatchDog.service

###################################

echo "add user to dialout"
sudo usermod -a -G dialout $USER





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

if [ "$hwVersion" = "v1Rev1" ] || [ "$hwVersion" = "v2Rev1" ] || [ "$hwVersion" = "v3Rev1" ] || [ "$hwVersion" = "v3Rev2" ] || [ "$hwVersion" = "v4Rev1" ] || [ "$hwVersion" = "v5Rev1" ] || [ "$hwVersion" = "v6Rev1" ]
then
   :
else
  # Install hwclock
  apt-get install util-linux-extra
  # Add the RTC module
  if ! grep -Fxq "rtc_pcf8563" /etc/modules
  then
    echo "add rtc_pcf8563 to /etc/modules"
    echo "rtc_pcf8563" >> /etc/modules
  fi

  if [ ! -f /usr/lib/udev/rules.d/51-udev-rtc.rules ]; then
    echo "Make symlink to rtc1 which probably is the pcf8563"
    echo 'SUBSYSTEM=="rtc", KERNEL=="rtc1", SYMLINK+="rtc", OPTIONS+="link_priority=-100"' >> /usr/lib/udev/rules.d/51-udev-rtc.rules
  fi
  systemctl disable chrony
fi

if ! grep -Fq 'compat' /lib/systemd/system/bluetooth.service
then
    echo "change to compat mode"
    # previous exec path: /usr/lib/bluetooth/bluetoothd
    sed -i -E "s@(ExecStart=).*@ExecStart=/usr/libexec/bluetooth/bluetoothd --compat --noplugin=sap@" /lib/systemd/system/bluetooth.service
    systemctl daemon-reload
else
    echo "compat"
fi

# changed to new location for bluetooth.service
if ! grep -Fxq 'ExecStartPost=/usr/bin/sdptool add SP' /usr/lib/systemd/system/bluetooth.service
then
    echo "add SP profile"
    sed -i '/ExecStart=.*/a ExecStartPost=/usr/bin/sdptool add SP' /usr/lib/systemd/system/bluetooth.service
    systemctl daemon-reload
else
    echo "SP profile already exist"
fi



