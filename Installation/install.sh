#!/usr/bin/env bash

#---it is nessesary to use an raspberry-os-lite image!!---

#---the following steps are necessary BEVOR executeing the script---!!!
#installing GitHub and downloading data
#sudo apt install -y git
#git clone https://github.com/Gesakul/Solar_Measureing.git
#username: Gesakul
#password: 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
#---Make Shell-script executeable and execute it---
#sudo chmod u+x install.sh && ./install.sh



#------------------------------------

#Path to config-file
CONFIG="/boot/config.txt"
LOCATION="/etc/wpa_supplicant/wpa_supplicant.conf"
HOTSPOT_CONF="/etc/hostapd/hostapd.conf"


#-------------------------------------


#Update Raspberry
echo "###-----update raspberry-----###"
apt update
apt upgrade -y

#change password
echo "###-----change pwd-----###" 
passwd pi


#install influxdb 1.8.9
echo "###------influx------###"
echo "add influx to repository"
wget -qO- https://repos.influxdata.com/influxdb.key | sudo apt-key add -
source /etc/os-release
echo "deb https://repos.influxdata.com/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/influxdb.list

echo "----- installing influxdb -----"
apt update && apt install -y influxdb

echo "----- start influxdb-service -----"
systemctl unmask influxdb.service
systemctl start influxdb
systemctl enable influxdb.service

#------------------------------------
#Influx Configuration
echo "----- setting-up influxdb -----"
apt-get install curl

sed -i '/ # Determines whether HTTP endpoint is enabled./!b;n;c  \ \ \ \ enabled = true' /etc/influxdb/influxdb.conf
sed -i '/ # The bind address used by the HTTP service./!b;n;c  \ \ \ \ bind-address = ":8086"' /etc/influxdb/influxdb.conf
systemctl restart influxdb
curl -XPOST 'http://localhost:8086/query' --data-urlencode 'q=CREATE DATABASE "Backup_Data"'


#------------------------------------

echo "###----- setting up required modules -----###"
#install python pip
echo "-----install pip-----"
apt install -y python3-pip

#install timedelta modul
echo "-----install timedelta-----"
pip3 install pytz

#install python-influx
echo "-----install python-influx-----"
pip3 install influxdb

#install numpy
echo "-----install numpy-----"
pip3 install numpy
apt-get install -y libatlas-base-dev

#install yaml-load
echo "-----install pyyaml-----"
pip3 install pyyaml

#install RPi.GPIO
echo "-----install RPi.GPIO-----"
pip3 install RPi.GPIO

#install pyudev
echo "----- install pyudev-----"
pip3 install pyudev

#install serial
echo "-----install pyserial-----"
pip3 install pyserial

#------------------------------------

#install on-off-switch
echo "###-----setting up requirements for on- off- switch-----###"

if grep -Fq "dtoverlay=gpio-shutdown,gpio_pin=3, active_low=1,gpio_pull=up" $CONFIG
then 
	echo "line already exists"
else 
	echo "added line to config-file"
	echo "#Configuration for on- off- switch" >> $CONFIG
	echo "dtoverlay=gpio-shutdown,gpio_pin=3, active_low=1,gpio_pull=up" >> $CONFIG
	echo " " >> $CONFIG
fi

#------------------------------------

#installing spi-bib
echo "###-----installing and setting up spi-requirements-----###"

apt-get install -y python-dev
wget https://github.com/doceme/py-spidev/archive/master.zip 
unzip master.zip
cd py-spidev-master
python setup.py install

if grep -Fq "dtparam=spi=on" $CONFIG
then
        echo "spi-bus enabled set"
        sed -i "s/#dtparam=spi=on/dtparam=spi=on/" $CONFIG
else
        echo " " >> $CONFIG
        echo "spi-bus enabled create"
        echo "#Enable spi" >> $CONFIG
        echo "dtparam=spi=on" >> $CONFIG
        echo " " >> $CONFIG
fi

#------------------------------------

#installing grafana
echo "###-----grafana-----###"
echo "add grafana to repoitory"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list

echo "-----installing grafana-----"
apt update && apt install -y grafana

echo "-----initialize grafana-----"
cp -a /home/pi/Solar_Measureing/Installation/influx_datasource.yaml /etc/grafana/provisioning/datasources
cp -a /home/pi/Solar_Measureing/Installation/Solar_Measureing-1632696549576.json /etc/grafana/provisioning/dashboards

echo "-----enable & start grafana-server-----"
systemctl unmask grafana-server.service
systemctl start grafana-server
systemctl enable grafana-server.service



#-------------------------------------

#installing LTE-HAT
echo "###-----install SIM7600X 4G HAT-----###"
if grep -Fq "enable_uart" $CONFIG
then
        echo "enable_uart exists and set to 1 "
        sed -i "s/enable_uart=0/enable_uart=1/" $CONFIG
else
        echo " " >> $CONFIG
        echo "enable_uart create"
        echo "#Enable uart" >> $CONFIG
        echo "enable_uart=1" >> $CONFIG
        echo " " >> $CONFIG
fi

apt-get install -y minicom


#--------------------------------------

echo "###-----Configurate RPi-hotspot-----###"
echo "-----install hostapd-----"
apt-get install -y hostapd
echo "-----install dnsmasq-----"
apt-get install -y dnsmasq
systemctl unmask hostapd

sudo systemctl stop hostapd
sudo systemctl stop dnsmasq

echo "-----Configurate hotspot-----"
HS_FILE="/etc/dhcpcd.conf"
echo "interface wlan0" >> $HS_FILE
echo "static ip_address=192.168.0.10/24" >> $HS_FILE
echo "denyinterfaces eth0" >> $HS_FILE
echo "denyinterfaces wlan0" >> $HS_FILE

sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig

DNS_FILE="/etc/dnsmasq.conf"
echo "interface=wlan0" >> $DNS_FILE
echo "  dhcp-range=192.168.0.11,192.168.0.30,255.255.255.0,24h" >> $DNS_FILE

if test -f "$HOTSPOT_CONF"; then
    echo "$HOTSPOT_CONF exists."
else
    touch /etc/hostapd/hostapd.conf
fi

echo "Copy lines to $HOTSPOT_CONF"
echo "#2.4GHz setup wifi 80211 b,g,n" > $HOTSPOT_CONF
echo "interface=wlan0" >> $HOTSPOT_CONF
echo "bridge=br0" >> $HOTSPOT_CONF
echo "hw_mode=g" >> $HOTSPOT_CONF
echo "channel=7" >> $HOTSPOT_CONF
echo "wmm_enabled=0" >> $HOTSPOT_CONF
echo "macaddr_acl=0" >> $HOTSPOT_CONF
echo "auth_algs=1" >> $HOTSPOT_CONF
echo "ignore_broadcast_ssid=0" >> $HOTSPOT_CONF
echo "wpa=2" >> $HOTSPOT_CONF
echo "wpa_key_mgmt=WPA-PSK" >> $HOTSPOT_CONF
echo "wpa_pairwise=TKIP" >> $HOTSPOT_CONF
echo "rsn_pairwise=CCMP" >> $HOTSPOT_CONF
echo "ssid=RPiNetwork" >> $HOTSPOT_CONF

HADP2_FILE="/etc/default/hostapd"

if grep -Fq "#DAEMON_CONF=" $HADP2_FILE
then
        echo "DAEMON_CONF-Path set"
        # sed -i 's#DAEMON_CONF=#root /var/www#' somefile
        sed -i 's?#DAEMON_CONF=.*?DAEMON_CONF="/etc/hostapd/hostapd.conf"?g' $HADP2_FILE
fi

#Set country-location
if grep -Fq "country=" $LOCATION
then 
	echo "Set country-code to DE"
	sed -i "s/country.*/country=DE/g" $LOCATION
else 
	echo "added configurations to file"
	echo "country=DE" >> $LOCATION
	echo " " >> $LOCATION
fi

echo "-----set timezone-----"
timedatectl set-timezone Europe/Berlin
echo "-----unblock wifi-----"
rfkill unblock 0


#Check if all requirements are up to date
echo "-----check if everything is up to date-----"
apt update
apt upgrade -y

#-------------------------------------

echo "WARNING: Rebooting system..."
reboot