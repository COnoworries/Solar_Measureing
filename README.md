# Solar_Measureing
Experimental proof of the PV-yield from vehicle-integrated PV-cells

# Before use
Before starting the installed software be aware that you are useing a software which was updated the last time on Dec. 2021. 
There is no garantee that the system oder the program will work as expected if you update oder upgrade the software.

# Installation
For the Installation please follw the next steps:
  0. (Download and unzip the file on your Raspberry)
  1.  Navigate in the 'Installation' folder an execute the install.sh file with 'sudo chmod u+x install.sh && sudo ./install.sh' this can take up to 30min
  2.  Execute the 'USB_config.sh' file
  3.  Copy the 'Solar_Measureing-1632696549576.json' file to your grafana template folder
  4.  Copy the 'influx_datasource.yaml' file to your Influx-DB template folder

# Usecase and further informations
This work deals with the development of a measuring device for the detection of solar radiation on moving or stationary vehicles. The aim is to contribute to the (further) development of electric vehicles powered by integrated PV cells. With the help of the sensor, it should be possible to make a forecast of the yield of such cells as accurately as possible in retrospect. For this purpose, the specific requirements are first defined, the idea generation process is shown and finally the elaboration is presented. The final concept consists of six sensors, a central computing unit and a plug-on and adapter board with analog input for the computing unit deve-loped within the scope of this work. 
In addition, a multi-layer sustainable data backup concept was developed, 
implemented and tested. 
The measuring device is placed centrally on the roof. It records the irradiation acting on the different levels of the vehicle in all relevant orientations. In addition, vibration/impact informati-on and GPS information are recorded and stored. 

The Software should collect 10 measureings each second. Due to some processingtime and further technical limitations it is only collecting about 6-8 meassureings each sec.
The measureings are stored in a list where after each second the max. min. and mean value is collected. The time between the measurements can be shortened as needed, the raspberry is powerfull enough to handle more readings each second. The only slow component is the GPS module which take about 0.1-0.2 sec to fetch its data. A solution would may be a multiprocessing handleing of the seperate Softwareparts. 
The Data (min, max & mean) will be stored in an InfluxDB and will be displayed in Grafana

# Startup
After the successfull installation the System and the Software will boot as soon as they are connected to an powersupply. The data can be viewed live by connecting to the Hotspot which will also start whilest booting. The SSID and password is as follows:
SSID: RPiNetwork
Password: RP!Network
The data can be view by visiting '192.168.1.1:3000/' in any browser.
The default login and password for the grafana page is: Username 'Admin' and password 'admin'



# Contact
Please feel free to contakt the creator of Version 0:
    Name: Lukas Geschka
    Email: LGeschka@gmail.com
    
