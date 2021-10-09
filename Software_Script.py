#!/usr/bin/python
# -*- coding:utf-8 -*-
from influxdb import InfluxDBClient
from datetime import datetime, timedelta
from ADC import MCP3208
import numpy as np
import time
import yaml
import RPi.GPIO as GPIO
#import ntplib
#import pandas as pd
import csv
import os
from os import path
import pyudev
import serial
import sys
import pytz
import subprocess


### ---CONFIG_Data--- ###
fname = 'config.yaml'
yaml_file = open(fname)
yaml_file = yaml.load(yaml_file, Loader=yaml.FullLoader)
INTERVALL = yaml_file["Save_Intervall"]["INTERVALL"]
TIMEZONE = pytz.timezone(yaml_file["Time"]["LOCATION"])
USB_FLAG = False
delta_time = timedelta(seconds=INTERVALL)
Attempt_GPS = 0




### ---get_networktime--- ###
def get_time():
    ntp_client = ntplib.NTPClient()
    response = ntp_client.request('pool.ntp.org')
    #print(ctime(response.tx_time))
    return response

### ---LED-SETUP--- ###
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.OUT)

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
        self.ADC_REF = 3.3   #ADC reference is 5v
        
    def getXYZ(self, x, y, z):
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
        erg = self.getXYZ(x,y,z)
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
        get_erg = self.getXYZ(x,y,z)
        self.ZERO_X = get_erg[0] * (3.3/4096)
        self.ZERO_Y = get_erg[1] * (3.3/4096)
        input("Turn x-axis straight up and press Enter")
        #Get Z in Normallage
        get_erg = self.getXYZ(x,y,z)
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
        
        self.ser = serial.Serial('/dev/ttyS0',115200)
        self.ser.flushInput()   
        self.power_key = 6
        self.rec_buff = ''
        self.rec_buff2 = ''
        self.time_count = 0

    def send_at(self,command,back,timeout):
        self.ser.write((command+'\r\n').encode())
        time.sleep(timeout)
        if self.ser.inWaiting():
            time.sleep(0.01 )
            self.rec_buff = self.ser.read(self.ser.inWaiting())
        if self.rec_buff != '':
            if back not in self.rec_buff.decode():
                print(command + ' ERROR')
                #print(command + ' back:\t' + rec_buff.decode())
                return 0
            else:
                #print(rec_buff.decode())
                return self.rec_buff.decode()
        else:
            print('GPS is not ready')
            return 0

    def get_gps_position(self):
        self.rec_null = True
        self.answer = 0
        self.liste = []
        self.answer = self.send_at('AT+CGPSINFO','+CGPSINFO: ',0.2)
        if self.answer != 0:
            #+CGPSINFO: [lat],[N/S],[log],[E/W],[date],[UTC time],[alt],[speed],[course]
            for i in self.answer.split('\n'):
                if "+CGPSINFO: " in i:
                    #print(i)
                    self.liste = i.split(':')[1].split(',')
                    break

            for i in range(len(self.liste)):
                self.liste[i] = self.liste[i].strip()
            self.answer = 0
            try:
                return [float(self.liste[0]),float(self.liste[2]),float(self.liste[6])]
            except Exception:
                return [0.0,0.0,0.0]
        
        else:
            print('error %d'%self.answer)
            self.rec_buff = ''
            self.send_at('AT+CGPS=0','OK',0.1)
            return [0.0,0.0,0.0]
        #time.sleep(1.5)


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
        self.send_at('AT+CGPS=1,1','OK',1)
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
    
    def insert_data(self, data = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ], status = False):
        
        measurements = {
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
                    "Accelerometer (Mean)": data[20],
                    
                    
                    "Noti./Status": status,
                    
                    }
            
        }
        #self.json_body = []
        self.json_body.append(measurements)
        self.client.write_points(self.json_body)
        print("data successfull inserted!@ {}".format(data[0]))

### ---Backup_extern---###
class Backup_Influx_ext:
    
    json_body = []
    
    def __init__(self):
        self.SERVER_IP = yaml_file["Backup_Extern"]["SERVER_IP"]
        self.SERVER_PORT = yaml_file["Backup_Extern"]["SERVER_PORT"]
        self.DATABASE_NAME = yaml_file["Backup_Extern"]["DATABASE_NAME"]
        self.MEASUREMENT_NAME = yaml_file["Backup_Extern"]["MEASUREMEMT_NAME"]
        self.client = InfluxDBClient(host = self.SERVER_IP, port = self.SERVER_PORT, database = self.DATABASE_NAME)
    
    
    def insert_data(self, data = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], status = False):
        
        measurements = {
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
        #self.json_body = []
        self.json_body.append(measurements)
        self.client.write_points(self.json_body)
        print("data successfull sended!@ {}".format(data[0]))
    
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
        while i < 5:
            print(GPS.get_gps_position())
            i+=1
        GPS.power_down(GPS.power_key)
    except:
        if GPS.ser != None:
            GPS.ser.close()
        GPS.power_down(GPS.power_key)
        GPIO.cleanup()
    if GPS.ser != None:
            GPS.ser.close()
            GPIO.cleanup()

        

if __name__ == "__main__":
    # GPIO.output(4, GPIO.HIGH)
    
    # Test_DB_loc_Insert()
    # Test_VS_Read()
    # Vibrationssensor().Calibrate()
    # for i in range (1000):
    #    #Test_VS_Read()
    #    Test_Solarzellen()
    #    time.sleep(1)
    # get_time()
    # print(datetime.now())
    # Test_USB_BU()
    # Test_Solarzellen()
    # Test_GPS()
    
    try:
        print("Software booting...")
        USB_BU = Safe_To_USB()
        GPS = GPS_Data()
        time.sleep(1)
        while Attempt_GPS < 5:
            try:
                GPS.power_on(GPS.power_key)
                break
            except Exception as e:
                GPS.power_down(GPS.power_key)
                Attempt_GPS += 1
                print(e)

        Attempt_GPS = 0
        VS = Vibrationssensor()
        BIL = Backup_Influx_loc()
        
        try:
            BIL.start_data()
            print("Influx-connection successfull")
        except Exception as e:
            print('\033[91m' + "ERROR: {}".format(e) )
            sys.exit("ERROR: Influx-connection refused")
            #raise ConnectionError("Influx-connection refused")
        
        SZ = Solarzellen()
        
        USB_BU.check_USB()

        if USB_BU.check_USB():
            print("USB recognized")
        else:
            print('\033[93m' + "WARNING: No USB available")
        

        #VS.Calibrate()
        
        VS_max_val = [0.0, 0.0, 0.0]
        gps_val = [0.0, 0.0, 0.0]
        SZ_max_val = [0.0, 0.0, 0.0, 0.0, 0.0]
        x_data = np.array([])
        y_data = np.array([])
        z_data = np.array([])
        SZ1 = np.array([])
        SZ2 = np.array([])
        SZ3 = np.array([])
        SZ4 = np.array([])
        SZ5 = np.array([])
        #Zeitinformation, den Mittel-/, Maximal-/ und Minimalwerten jeder Solarzelle, den Positionsdaten des Sensors (Längengrad, Breitengrad, Höhe) und den Maximalwert sowie Mittelwert des Vibrationssensors.
        nullsatz = [0.0, 1.0, 1.1, 1.2, 2.0, 2.1, 2.2, 3.0, 3.1, 3.2, 4.0, 4.1, 4.2, 5.0, 5.1, 5.2, 111, 222, 333, 444, 555]
        
        x = 1
        start_time_global = datetime.now()
        end_time_gloabl = datetime(2000,1,1)
        
        while(1):
            t1_start = time.process_time()
            USB_BU.check_USB()
            
            while start_time_global + timedelta(seconds=x) > end_time_gloabl:
                start_time_local = datetime.now()
                end_time_local = datetime(2000,1,1)

                while start_time_local + timedelta(milliseconds=100) > end_time_local:
                    VS_val_new = VS.getAcceleration()
                    SZ_val_new = SZ.Read_Data()
                    end_time_local = datetime.now()
                end_time_gloabl = datetime.now()    
                #MAXIMUM VIB-SENS-VAL
            if VS_val_new[0] > VS_max_val[0]:
                VS_max_val[0] = VS_val_new[0]
                
            if VS_val_new[1] > VS_max_val[1]:
                VS_max_val[1] = VS_val_new[1]
                
            if VS_val_new[2] > VS_max_val[2]:
                VS_max_val[2] = VS_val_new[2]
                
            if SZ_val_new[0] > SZ_max_val[0]:
                SZ_max_val[0] = SZ_val_new[0]
                
            if SZ_val_new[1] > SZ_max_val[1]:
                SZ_max_val[1] = SZ_val_new[1]
                
            if SZ_val_new[2] > SZ_max_val[2]:
                SZ_max_val[2] = SZ_val_new[2]
                
            if SZ_val_new[3] > SZ_max_val[3]:
                SZ_max_val[3] = SZ_val_new[3]
                
            if SZ_val_new[4] > SZ_max_val[4]:
                SZ_max_val[4] = SZ_val_new[4]
            
                
            
            #MEAN VIB_SENS_VAL
            x_data = np.append(x_data, VS_val_new[0])
            y_data = np.append(y_data, VS_val_new[1])
            z_data = np.append(z_data, VS_val_new[2])
            SZ1 = np.append(SZ1, SZ_val_new[0])
            SZ2 = np.append(SZ2, SZ_val_new[1])
            SZ3 = np.append(SZ3, SZ_val_new[2])
            SZ4 = np.append(SZ4, SZ_val_new[3])
            SZ5 = np.append(SZ5, SZ_val_new[4])
                
            
            
        
            try:
                gps_val = GPS.get_gps_position()
            except Exception as e:
                print('\033[91m' + "{}".format(e))
                gps_val = [0.0, 0.0, 0.0]
                
            
            #print(nullsatz)
            nullsatz[0] = datetime.now(TIMEZONE)
            nullsatz[1] = np.mean(SZ1)
            nullsatz[2] = np.max(SZ1)
            nullsatz[3] = np.min(SZ1)
            nullsatz[4] = np.mean(SZ2)
            nullsatz[5] = np.max(SZ2)
            nullsatz[6] = np.min(SZ2)
            nullsatz[7] = np.mean(SZ3)
            nullsatz[8] = np.max(SZ3)
            nullsatz[9] = np.min(SZ3)
            nullsatz[10] = np.mean(SZ4)
            nullsatz[11] = np.max(SZ4)
            nullsatz[12] = np.min(SZ4)
            nullsatz[13] = np.mean(SZ5)
            nullsatz[14] = np.max(SZ5)
            nullsatz[15] = np.min(SZ5)
            nullsatz[16] = gps_val[0]
            nullsatz[17] = gps_val[1]
            nullsatz[18] = gps_val[2]
            nullsatz[-2] = VS_max_val[2]
            nullsatz[-1] = np.mean(z_data)
            #print(nullsatz)
            
            
            VS_max_val = [0.0, 0.0, 0.0]
            SZ_max_val = [0.0, 0.0, 0.0, 0.0, 0.0]
            x_data = np.array([])
            y_data = np.array([])
            z_data = np.array([])
            SZ1 = np.array([])
            SZ2 = np.array([])
            SZ3 = np.array([])
            SZ4 = np.array([])
            SZ5 = np.array([])

            if USB_BU.check_USB():
                USB_BU.write_Backup(nullsatz) 

            BIL.insert_data(nullsatz, True)

            x += 1
        t1_stop = time.process_time()
        print("Elapsed time during the whole program in seconds:",t1_stop-t1_start)  
        #BIL.insert_data() #Fehlerhafter Datensatz
    except Exception as e:
        print('\033[91m' + "FAIL: Softwareboot" )
        print(e)
        sys.exit("ERROR: Bad Timeout. Failed to start Software")
    