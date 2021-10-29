#!/usr/bin/python3
# -*- coding:utf-8 -*-
from influxdb import InfluxDBClient
from datetime import datetime, timedelta
from ADC import MCP3208
import numpy as np
import time
import yaml
import RPi.GPIO as GPIO
from os import path
import pyudev
import serial
import sys, traceback
import pytz
import subprocess
import math
import os



### ---CONFIG_Data--- ###
fname = '/home/pi/Solar_Measureing/config.yaml'
yaml_file = open(fname)
yaml_file = yaml.load(yaml_file, Loader=yaml.FullLoader)
INTERVALL = yaml_file["Save_Intervall"]["INTERVALL"]
TIMEZONE = pytz.timezone(yaml_file["Time"]["LOCATION"])
USB_FLAG = False
delta_time = timedelta(seconds=INTERVALL)
Attempt_GPS_on = 0
Attempt_GPS_stat = 0
GPS_READY = False
SETTIME = False


### ---LED-SETUP--- ###
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)

### ---Daten_Lesen--- ###
class Vibrationssensor:

    def __init__(self):
        self.calibrated = False
        self.count = 0
        self.adc = MCP3208()

        self.ZERO_X = 1.28 #accleration of X-AXIS is 0g, the voltage of X-AXIS is 1.22v
        self.ZERO_Y = 1.28
        self.ZERO_Z = 1.28 #
        self.SENSITIVITY = 0.25 #sensitivity of X/Y/Z axis is 0.25v/g
        self.X_AXIS_PIN = 0
        self.Y_AXIS_PIN = 1
        self.Z_AXIS_PIN = 2
        self.ADC_AMPLITUDE = 4096 #amplitude of the 12bit-ADC of Arduino is 4096LSB
        self.ADC_REF = 3.33   #ADC reference is 3.33v

    def getXYZ(self):
        #Get all Data from ADC
        x = self.adc.read(channel = self.X_AXIS_PIN)
        y = self.adc.read(channel = self.Y_AXIS_PIN)
        z = self.adc.read(channel = self.Z_AXIS_PIN)
        #print("X: {0}; Y: {1}; Z: {2}".format(x,y,z))
        return [x, y, z]

    def getAcceleration(self):
        #get real g-force value
        x = y = z = 0
        xvoltage = yvoltage = zvoltage = 0.0
        erg = self.getXYZ()
        x = erg[0]
        y = erg[1]
        z = erg[2]

        xvoltage = float(x*self.ADC_REF/self.ADC_AMPLITUDE)
        yvoltage = float(y*self.ADC_REF/self.ADC_AMPLITUDE)
        zvoltage = float(z*self.ADC_REF/self.ADC_AMPLITUDE)
        #print("xv: {0}; yv: {1}; zv: {2}".format(xvoltage, zvoltage, zvoltage))


        ax = (xvoltage - self.ZERO_X)/self.SENSITIVITY
        ay = (yvoltage - self.ZERO_Y)/self.SENSITIVITY
        az = (zvoltage - self.ZERO_Z)/self.SENSITIVITY
        #print("X_Zero {0}; Sensitivity {1}".format(self.ZERO_X,self.SENSITIVITY))
        #print("ax: {0}; ay: {1}; az: {2}".format(ax, ay, az))

        return [ax, ay, az]


    def Calibrate(self):
        self.calibrated = True
        x = y = z = sum_x = sum_y = sum_z = 0

        #Lege 'Ruhewerte' fest
        #Get X und Y in Normallage
        get_erg = self.getXYZ()
        self.ZERO_X = get_erg[0] * (3.3/4096)
        self.ZERO_Y = get_erg[1] * (3.3/4096)
        input("Turn x-axis straight up and press Enter")
        #Get Z in Normallage
        get_erg = self.getXYZ()
        self.ZERO_Z = get_erg[2] * (3.3/4096)

        #Messe aktuelle g-Zahl
        ax = ay = az = 0.0
        acc_erg = self.getAcceleration()
        ax = acc_erg[0]
        ay = acc_erg[1]
        az = acc_erg[2]
        #print("ax: {0}; ay: {1}; az: {2}".format(ax, ay, az))

        if((abs(ax) < 0.1) and (abs(ay) < 0.1)):
            print("calibration successfull")
            return [x, y, z]

        elif((abs(ax) < 0.1) and (abs(az) < 0.1)):
            print("calibration successfull")
            return [x, y, z]

        elif((abs(az) < 0.1) and (abs(ay) < 0.1)):
            print("calibration successfull")
            return [x, y, z]

        else:
            self.calibrated = False
            raise SystemError("calibration failed")



    def Read_Data(self):
        _x = self.adc.read(channel = 0) * 3.3 / 4096.0
        _y = self.adc.read(channel = 1) * 3.3 / 4096.0
        _z = self.adc.read(channel = 2) * 3.3 / 4096.0

        x_val = (_x - self.ZERO_X)/self.SENSITIVITY
        y_val = (_y - self.ZERO_Y)/self.SENSITIVITY
        z_val = (_z - self.ZERO_Z)/self.SENSITIVITY

        return [x_val, y_val, z_val]

### ---Solarzellen---###
class Solarzellen:
    def __init__(self):
        self.adc = MCP3208()
        self.SZ1 = self.SZ2 = self.SZ3 = self.SZ4 = self.SZ5 = 0

    def Read_Data(self):
        self.SZ1 = self.adc.read(channel = 3)/4096.0 * 10.0
        self.SZ2 = self.adc.read(channel = 4)/4096.0 * 10.0
        self.SZ3 = self.adc.read(channel = 5)/4096.0 * 10.0
        self.SZ4 = self.adc.read(channel = 6)/4096.0 * 10.0
        self.SZ5 = self.adc.read(channel = 7)/4096.0 * 10.0

        return [self.SZ1, self.SZ2, self.SZ3, self.SZ4, self.SZ5]

### ---GPS_Modul---###
class GPS_Data:

    def __init__(self):
        global GPS_READY
        GPS_READY= False
        self.ser = serial.Serial('/dev/ttyS0',115200)
        self.ser.flushInput()
        self.power_key = 6
        self.rec_buff = ''
        self.time_count = 0

    def send_at(self,command,back,timeout):
        self.ser.write((command+'\r\n').encode())
        time.sleep(timeout)
        if self.ser.in_waiting:
            time.sleep(0.01 )
            self.rec_buff = self.ser.read(self.ser.in_waiting)
        print(self.rec_buff)
        if self.rec_buff != '':
            if back not in self.rec_buff.decode():
                print(command + ' ERROR')
                #print(command + ' back:\t' + rec_buff.decode())
                return 0
            else:
                return self.rec_buff.decode()
        else:
            return 0

    def get_gps_position(self):
        self.answer = 0
        self.liste = []
        self.answer = self.send_at('AT+CGPSINFO','+CGPSINFO: ',0.2)
        if self.answer != 0:
            if ',,,,,,' in self.answer:
                print('GPS is not ready')
                return [0.0,0.0,0.0,0.0,0.0]

            #+CGPSINFO: [lat],[N/S],[log],[E/W],[date],[UTC time],[alt],[speed],[course]
            for i in self.answer.split('\n'):
                if "+CGPSINFO: " in i:
                    self.liste = i.split(':')[1].split(',')
                    break

            for i in range(len(self.liste)):
                self.liste[i] = self.liste[i].strip()
            self.answer = 0
            #Lat Long Alt, Date, Time, speed
            return [float(self.liste[0]),float(self.liste[2]),float(self.liste[6]),float(self.liste[4]),float(self.liste[5]),float(self.liste[7])]


        else:
            print('error %d'%self.answer)
            self.rec_buff = ''
            #self.send_at('AT+CGPS=0','OK',1)
            return [0.0,0.0,0.0,0.0,0.0]




    def power_on(self,power_key):
        print('SIM7600X is starting:')
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(power_key,GPIO.OUT)
        time.sleep(0.1)
        GPIO.output(power_key,GPIO.HIGH)
        time.sleep(2)
        GPIO.output(power_key,GPIO.LOW)
        time.sleep(20)
        self.ser.flushInput()
        print('SIM7600X is ready')
        #Start GPS session in standalone mode
        print("Start GPS session...")
        self.send_at('AT+CGPS=1,1','OK',0.2)
        time.sleep(2)

    def power_down(self,power_key):
        self.send_at('AT+CGPS=0','OK',1)
        print('SIM7600X is loging off:')
        GPIO.output(power_key,GPIO.HIGH)
        time.sleep(3)
        GPIO.output(power_key,GPIO.LOW)
        time.sleep(18)
        print('Good bye')

### ---Backup_local---###
class Backup_Influx_loc:

    json_body = []

    def __init__(self):
        self.SERVER_IP = yaml_file["Backup_Local"]["SERVER_IP"]
        self.SERVER_PORT = yaml_file["Backup_Local"]["SERVER_PORT"]
        self.DATABASE_NAME = yaml_file["Backup_Local"]["DATABASE_NAME"]
        self.MEASUREMENT_NAME = yaml_file["Backup_Local"]["MEASUREMEMT_NAME"]
        self.client = InfluxDBClient(host = self.SERVER_IP, port = self.SERVER_PORT, database = self.DATABASE_NAME)

    def start_data(self):
        self.insert_data()

    def insert_data(self, data = [0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ], status = False):

        measurements = [
            {
                "measurement": self.MEASUREMENT_NAME,
                "tags":{},
                "time": data[0], #datetime.now(TIMEZONE),
                "fields": {
                    "Solarzelle 1 (Mean)": data[1],
                    "Solarzelle 1 (Max) ": data[2],
                    "Solarzelle 1 (Min) ": data[3],
                    "Solarzelle 2 (Mean)": data[4],
                    "Solarzelle 2 (Max) ": data[5],
                    "Solarzelle 2 (Min) ": data[6],
                    "Solarzelle 3 (Mean)": data[7],
                    "Solarzelle 3 (Max) ": data[8],
                    "Solarzelle 3 (Min) ": data[9],
                    "Solarzelle 4 (Mean)": data[10],
                    "Solarzelle 4 (Max) ": data[11],
                    "Solarzelle 4 (Min) ": data[12],
                    "Solarzelle 5 (Mean)": data[13],
                    "Solarzelle 5 (Max) ": data[14],
                    "Solarzelle 5 (Min) ": data[15],
                    "Location (long)": data[16],
                    "Location (Lati)": data[17],
                    "Location (Alti)": data[18],
                    "Accelerometer (Max) ": data[19],
                    "Accelerometer (Mean)": data[20],


                    "Noti./Status": status,

                    }

            }
        ]

        # print(measurements)
        self.client.write_points(measurements)
        print("data successfull inserted!@ {}".format(data[0]))

### ---Backup_extern---###
class Backup_Influx_ext:

    def __init__(self):
        self.SERVER_IP = yaml_file["Backup_Extern"]["SERVER_IP"]
        self.SERVER_PORT = yaml_file["Backup_Extern"]["SERVER_PORT"]
        self.DATABASE_NAME = yaml_file["Backup_Extern"]["DATABASE_NAME"]
        self.MEASUREMENT_NAME = yaml_file["Backup_Extern"]["MEASUREMEMT_NAME"]
        self.client = InfluxDBClient(host = self.SERVER_IP, port = self.SERVER_PORT, database = self.DATABASE_NAME)


    def insert_data(self, data = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], status = False):

        measurements = [
            {
                "measurement": self.MEASUREMENT_NAME,
                "tags":{},
                "time": datetime.now(TIMEZONE),
                "fields": {
                    "Solarzelle 1 (Mean)": data[1],
                    "Solarzelle 1 (Max) ": data[2],
                    "Solarzelle 1 (Min) ": data[3],
                    "Solarzelle 2 (Mean)": data[4],
                    "Solarzelle 2 (Max) ": data[5],
                    "Solarzelle 2 (Min) ": data[6],
                    "Solarzelle 3 (Mean)": data[7],
                    "Solarzelle 3 (Max) ": data[8],
                    "Solarzelle 3 (Min) ": data[9],
                    "Solarzelle 4 (Mean)": data[10],
                    "Solarzelle 4 (Max) ": data[11],
                    "Solarzelle 4 (Min) ": data[12],
                    "Solarzelle 5 (Mean)": data[13],
                    "Solarzelle 5 (Max) ": data[14],
                    "Solarzelle 5 (Min) ": data[15],
                    "Location (long)": data[16],
                    "Location (Lati)": data[17],
                    "Location (Alti)": data[18],
                    "Accelerometer (Max) ": data[19],
                    "accelerometer (Mean)": data[20],


                    "Noti./Status": status,

                    }

            }
        ]
        #self.json_body = []
        # print(measurements)
        self.client.write_points(measurements)
        print("data successfull sended!@ {}".format(data[0]))

### ---USB_Backup---###
class Safe_To_USB():

    def __init__(self):
        self.status = False
        self.context = pyudev.Context()
        self.device_list = (device.device_node for device in self.context.list_devices(subsystem='block', DEVTYPE='partition'))

    def check_USB(self):
        # global USB_FLAG

        for i in self.device_list:
            if i == "/dev/sda1":
                try:
                    if yaml_file["USB_FOLDER"]["STATUS"] == False:
                        subprocess.call(['sh', 'Installation/USB_config.sh'])
                        yaml_file["USB_FOLDER"]["STATUS"] = True
                        with open(fname, 'w') as yaml_write:
                            yaml_write.write(yaml.dump(yaml_file, sort_keys=False))

                except Exception as e:
                    print('\033[91m' + "ERROR: {}".format(e) )
                    print("Couldn't create Folder")
                # USB_FLAG = True
                self.status = True
                break

        return self.status


    def write_Backup(self, data):
    #Prueft ob die Datei existiert
        if (self.check_USB()):
            with open("/mnt/Backup_Data/Backup.csv", 'a') as bu_file: #ANPASSUNG AN USB SPEICHERORT
                for i in range(len(data)):
                    bu_file.write("{}; ". format(data[i]))
                bu_file.write('\n')
                print("Successful! Values to Backup appended!")
            bu_file.close()
        else:
            return self.check_USB()

### ---Convert Time---###
def time_convert(date_val, time_val):
    date = float(date_val)
    y = int(math.modf(date/100)[0]*100)+2000
    m = int(math.modf(math.modf(date/100)[1]/100)[0]*100)
    d = int(math.modf(math.modf(date/100)[1]/100)[1])
    date_string = "{0:04}/{1:02}/{2:02}".format(y,m,d)
    t = float(time_val)
    S = int(math.modf(t/100)[0]*100)
    M = int(math.modf(math.modf(t/100)[1]/100)[0]*100)
    H = int(math.modf(math.modf(t/100)[1]/100)[1]) + 2
    time_string = "{0:02}/{1:02}/{2:02}".format(H,M,S)
    end_string = date_string + '/' + time_string
    element = datetime.strptime(end_string,"%Y/%m/%d/%H/%M/%S")
    return element

### ---Waiting function--- ###
def waiting():
    animation = "|/-\\"
    idx = 0
    a = 0
    n = 300
    while a<n:
        a += 1
        print("connection to satellite... " + animation[idx % len(animation)] + " progress: " + "{}".format(a/10) + "/" + "{}".format(n/10) + " " + '{:.2f}'.format(a/n*100)+'%', end="\r")
        idx += 1
        time.sleep(0.1)

    print("connection to satellite...   finished  \n")

### ---main()--- ###
def main():
    #Kalibrieren der Software
    print("Software booting...")
    global Attempt_GPS_on
    global Attempt_GPS_stat
    global GPS_READY
    global SETTIME
    GPIO.output(17, GPIO.HIGH)
    SZ = Solarzellen()
    GPS = GPS_Data()
    time.sleep(1)

    #Anschalten des GPS
    while Attempt_GPS_on < 5:
        try:
            GPS.power_on(GPS.power_key)
            break
        except Exception as e:
            GPS.power_down(GPS.power_key)
            print(e)
            Attempt_GPS_on += 1
            time.sleep(10)
    Attempt_GPS_on = 0

    #Vibrationssensor
    VS = Vibrationssensor()

    #InfluxDB Starten
    BIL = Backup_Influx_loc()
    try:
        BIL.start_data()
        print("Influx-connection successfull")
    except Exception as e:
        print('\033[91m' + "ERROR: {}".format(e) )
        traceback.print_exc(file=sys.stdout)
        sys.exit("ERROR: Influx-connection failed\033[00m")
        #raise ConnectionError("Influx-connection refused")


    #USB Stick initialisieren
    USB_BU = Safe_To_USB()
    USB_BU.check_USB()
    if USB_BU.check_USB():
        print("USB recognized")
    else:
        print('\033[93m' + "WARNING: No USB available\033[00m")


    #VS.Calibrate()

    #Variablen initialisieren
    gps_val = [0.0, 0.0, 0.0]
    # SZ_max_val = [0.0, 0.0, 0.0, 0.0, 0.0]
    x_data = np.array([])
    y_data = np.array([])
    z_data = np.array([])
    SZ1 = np.array([])
    SZ2 = np.array([])
    SZ3 = np.array([])
    SZ4 = np.array([])
    SZ5 = np.array([])
    #Zeitinformation, den Mittel-/, Maximal-/ und Minimalwerten jeder Solarzelle, den Positionsdaten des Sensors (Längengrad, Breitengrad, Höhe) und den Maximalwert sowie Mittelwert des Vibrationssensors.
    datensatz = [0.0, 1.0, 1.1, 1.2, 2.0, 2.1, 2.2, 3.0, 3.1, 3.2, 4.0, 4.1, 4.2, 5.0, 5.1, 5.2, 111, 222, 333, 444, 555]

    gps_val = GPS.get_gps_position()

    while not gps_val[0]:
        waiting()
        gps_val = GPS.get_gps_position()
        if not gps_val[0]:
            print("connection failed... restart")
            Attempt_GPS_stat += 1
        if Attempt_GPS_stat == 5:
            GPS.send_at('AT+CGPS=0','OK',1)
        if Attempt_GPS_stat == 6:
            GPS.send_at('AT+CGPS=1,1','OK',0.2)
        if Attempt_GPS_stat == 10:
            raise TimeoutError("GPS failed to start")


    if not SETTIME:
        print('\033[93m' + "OS time set\033[00m")
        os.system('date -s "{}"'.format(time_convert(gps_val[3],gps_val[4])))
        SETTIME = True
        

    #startwerte festlegen
    x = 1
    count = 0.0
    start_time_global = datetime.now()
    end_time_gloabl = datetime(2000,1,1)

    #Hauptschleife
    while(1):
        t0 = time.perf_counter()
        #Check ob USB-Stick vorhanden
        USB_BU.check_USB()
        print(start_time_global + timedelta(seconds=x))
        print(end_time_gloabl)

        #Time in 1s Abschnitten
        while start_time_global + timedelta(seconds=x) > end_time_gloabl:
            # end_time_local = datetime.now()
            # start_time_local = datetime.now()

            # while start_time_local + timedelta(milliseconds=100) > end_time_local:
            #         end_time_local = datetime.now()
            time.sleep(0.1)
            count +=1.0
            VS_val = VS.getAcceleration()
            SZ_val_new = SZ.Read_Data()
            x_data = np.append(x_data, VS_val[0])
            y_data = np.append(y_data, VS_val[1])
            z_data = np.append(z_data, VS_val[2])
            SZ1 = np.append(SZ1, SZ_val_new[0])
            SZ2 = np.append(SZ2, SZ_val_new[1])
            SZ3 = np.append(SZ3, SZ_val_new[2])
            SZ4 = np.append(SZ4, SZ_val_new[3])
            SZ5 = np.append(SZ5, SZ_val_new[4])
            end_time_gloabl = datetime.now()
            t1 = time.perf_counter()

        print(count)
        try:
            gps_val = GPS.get_gps_position()
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            print('\033[91m' + '{}' + '\033[00m'.format(e))
            gps_val = [0.0,0.0,0.0,0.0,0.0]



        if count != 0:
            datensatz[0] = datetime.now(TIMEZONE)
            datensatz[1] = np.mean(SZ1)
            datensatz[2] = np.max(SZ1)
            datensatz[3] = np.min(SZ1)
            datensatz[4] = np.mean(SZ2)
            datensatz[5] = np.max(SZ2)
            datensatz[6] = np.min(SZ2)
            datensatz[7] = np.mean(SZ3)
            datensatz[8] = np.max(SZ3)
            datensatz[9] = np.min(SZ3)
            datensatz[10] = np.mean(SZ4)
            datensatz[11] = np.max(SZ4)
            datensatz[12] = np.min(SZ4)
            datensatz[13] = np.mean(SZ5)
            datensatz[14] = np.max(SZ5)
            datensatz[15] = np.min(SZ5)
            datensatz[16] = gps_val[0]
            datensatz[17] = gps_val[1]
            datensatz[18] = gps_val[2]
            datensatz[-2] = np.max(z_data)
            datensatz[-1] = np.mean(z_data)
        # print(datensatz)

        #Zurücksetzten der Listen und Arrays
        x_data = np.array([])
        y_data = np.array([])
        z_data = np.array([])
        SZ1 = np.array([])
        SZ2 = np.array([])
        SZ3 = np.array([])
        SZ4 = np.array([])
        SZ5 = np.array([])
        t2 = time.perf_counter()


        #schreiben auf USB-CSV
        if USB_BU.check_USB():
            USB_BU.write_Backup(datensatz)

        #schreiben in InfluxDB
        BIL.insert_data(datensatz, True)

        t3 = time.perf_counter()

        # print("Abschnitt 1 {}".format(t1-t0))
        # print("Abschnitt 2 {}".format(t2-t1))
        # print("Abschnitt 3 {}".format(t3-t2))

        count = 0.0
        x += 1

### --- Tests --- ###
def Test_Solarzellen():
    try:
        SZ_class = Solarzellen()
        print(SZ_class.Read_Data())
    except:
        print("Couldn't execute the funtion")
        raise

def Test_VS_Read():
    #[x_val, y_val, z_val]
    #print(Vibrationssensor().Read_Data())
    print('-----------------')
    VS = Vibrationssensor()
    values = VS.getAcceleration()
    print("X: {0}; Y: {1}; Z: {2}".format(values[0], values[1], values[2]))
    print('-----------------')
    #Vibrationssensor().Read()

def Test_DB_loc_Insert():
    instanz = Backup_Influx_loc()
    data = [398, 473, 558, 618, 720, -459, 751, 640, 630, 716, 1627318641.5335495]
    instanz.insert_data(data, True) #Datensatz
    instanz.insert_data() #Fehlerhafter Datensatz

def Test_DB_ext_Insert():
    instanz = Backup_Influx_ext()
    data = [398, 473, 558, 618, 720, -459, 751, 640, 630, 716, 1627318641.5335495]
    #instanz.insert_data(data, True) #Datensatz
    instanz.insert_data() #Fehlerhafter Datensatz

def Test_USB_BU():
    data = [1627318641.5335495, 1.0, 1.1, 1.2, 2.0, 2.1, 2.2, 3.0, 3.1, 3.2, 4.0, 4.1, 4.2, 5.0, 5.1, 5.2, 111, 222, 333, 444, 555]
    USB_BU = Safe_To_USB()
    if (USB_BU.check_USB()):
        USB_BU.write_Backup(data)
        print("USB recognized and Data successfully written")
    else:
        print('\033[93m' + "WARNING: No USB available")

def Test_GPS():
    GPS = GPS_Data()
    i = 0
    try:
        GPS.power_on(GPS.power_key)
        while i < 50:
            print(GPS.get_gps_position())
            i+=1
            time.sleep(1)
        GPS.power_down(GPS.power_key)
    except:
        if GPS.ser != None:
            GPS.ser.close()
        GPS.power_down(GPS.power_key)
        GPIO.cleanup()
    if GPS.ser != None:
            GPS.ser.close()
            GPIO.cleanup()

def Test_main():
    # Test_DB_loc_Insert()
    # Vibrationssensor().Calibrate()
    # for i in range (1000):
    #    #Test_VS_Read()
    #    Test_Solarzellen()
    #    time.sleep(1)
    # get_time()
    # print(datetime.now())
    # Test_USB_BU()
    # Test_Solarzellen()
    Test_GPS()

if __name__ == "__main__":

    try:
        # Test_main()
        # print(datetime.now(TIMEZONE))
        main()

    except KeyboardInterrupt:
        print("'\033[93m' Shutdown requested...exiting\033[00m")
        GPS = GPS_Data()
        GPS.power_down(GPS.power_key)
        if GPS.ser != None:
            GPS.ser.close()
        GPIO.cleanup()
    except Exception:
        GPS = GPS_Data()
        traceback.print_exc(file=sys.stdout)
        GPS.power_down(GPS.power_key)
        if GPS.ser != None:
            GPS.ser.close()
        GPIO.cleanup()
    if GPS_Data().ser != None:
        GPS_Data().ser.close()
        GPIO.cleanup()

    sys.exit(0)
