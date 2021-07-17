#!/bin/bash
systemctl stop WiRocBLE
systemctl disable WiRocBLE
rm /etc/systemd/system/WiRocBLE.service
systemctl stop blink
systemclt disable blink
rm /etc/systemd/system/blink.service
rm /usr/local/bin/blink.sh
systemctl enable bluetooth
systemctl start bluetooth
systemctl stop WiRocPython
systemctl stop WiRocPythonWS

wget -O /home/chip/WiRoc-StartupScripts/Startup.sh https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/Startup.sh
chmod +x /home/chip/WiRoc-StartupScripts/Startup.sh

wget -O /etc/systemd/system/WiRocBLEAPI.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocBLEAPI.service
wget -O /etc/systemd/system/WiRocPython.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocPython.service
wget -O /etc/systemd/system/WiRocPythonWS.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocPythonWS.service
wget -O /etc/systemd/system/WiRocStartup.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/WiRocStartup.service
#wget -O /etc/systemd/system/ifup-wait-all-auto.service https://raw.githubusercontent.com/henla464/WiRoc-StartupScripts/master/ifup-wait-all-auto.service
#systemctl enable /etc/systemd/system/ifup-wait-all-auto.service
systemctl enable /etc/systemd/system/WiRocStartup.service
systemctl enable /etc/systemd/system/WiRocPython.service
systemctl enable /etc/systemd/system/WiRocPythonWS.service
systemctl enable /etc/systemd/system/WiRocBLEAPI.service

mkdir WiRoc-WatchDog
wget -O /home/chip/WiRoc-WatchDog/gpio.sh https://raw.githubusercontent.com/henla464/WiRoc-WatchDog/master/gpio.sh
wget -O /home/chip/WiRoc-WatchDog/WiRoc-WatchDog.sh https://raw.githubusercontent.com/henla464/WiRoc-WatchDog/master/WiRoc-WatchDog.sh
chmod +x /home/chip/WiRoc-WatchDog/WiRoc-WatchDog.sh
wget -O /etc/systemd/system/WiRocWatchDog.service https://raw.githubusercontent.com/henla464/WiRoc-WatchDog/master/WiRocWatchDog.service
if [[ $(hostname -s) = nanopiair ]]; then
    echo "nanopiair"
    wget -O /home/chip/WiRoc-WatchDog/WiRoc-WatchDog.cfg https://raw.githubusercontent.com/henla464/WiRoc-WatchDog/master/WiRoc-WatchDog.cfg
else
    echo "chip"
    wget -O /home/chip/WiRoc-WatchDog/WiRoc-WatchDog.cfg https://raw.githubusercontent.com/henla464/WiRoc-WatchDog/master/WiRoc-WatchDog.chip.cfg
fi
systemctl enable /etc/systemd/system/WiRocWatchDog.service
systemctl start WiRocWatchDog

# then run ./installWiRocPython 0.173 ./installWiRocBLEAPI.sh 0.5
