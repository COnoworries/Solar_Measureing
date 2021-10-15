import serial
import RPi.GPIO as GPIO
import time
from datetime import datetime, timedelta
import traceback
import sys

class GPS_Data:
    
    
    
    def __init__(self):
        
        self.ser = serial.Serial('/dev/ttyS0',115200)
        self.ser.reset_input_buffer() 
        self.power_key = 6
        self.rec_buff = ''
        self.rec_buff2 = ''
        self.time_count = 0

    def send_at(self,command,back,timeout):
        self.ser.write((command+'\n').encode('utf-8'))
        time.sleep(timeout)
        if self.ser.inWaiting():
            time.sleep(0.01)
            #print(self.ser.inWaiting().decode('utf-8'))
            print(self.ser.read(self.ser.inWaiting()))
            self.rec_buff = self.ser.read(self.ser.inWaiting())
        if self.rec_buff != '':
            if back not in self.rec_buff.decode('utf-8'):
                print(command + ' ERROR')
                #print(command + ' back:\t' + rec_buff.decode())
                self.ser.flush()
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                return 0
            else:
                #print(rec_buff.decode())
                ret = self.rec_buff.decode()
                self.ser.flush()
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                return ret 
        else:
            print('GPS is not ready')
            self.ser.flush()
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
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
                #print(self.liste)
                return [float(self.liste[0]),float(self.liste[2]),float(self.liste[6])]
            except Exception:
                return [0.0,0.0,0.0]
        
        else:
            print('error %d' %self.answer)
            self.rec_buff = ''
            self.send_at('AT+CGPS=0','OK',0.1)
            
            return [0.0,0.0,0.0]
        #time.sleep(1.5)


    def power_on(self,power_key):
        print('SIM7600X is starting:')
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(True)
        GPIO.setup(power_key,GPIO.OUT)
        time.sleep(0.1)
        GPIO.output(power_key,GPIO.HIGH)
        time.sleep(2)
        GPIO.output(power_key,GPIO.LOW)
        time.sleep(20)
        self.ser.reset_input_buffer()
        print('SIM7600X is ready')
        #Start GPS session in standalone mode
        self.send_at('AT+CGPS=1,1','OK',1)
        time.sleep(2)

    def power_down(self,power_key):
        GPIO.setmode(GPIO.BCM)
        self.send_at('AT+CGPS=0','OK',1)
        print('SIM7600X is loging off:')
        GPIO.output(power_key,GPIO.HIGH)
        time.sleep(3)
        GPIO.output(power_key,GPIO.LOW)
        GPIO.cleanup()
        time.sleep(18)
        print('Good bye')
Attempt_GPS = 0 

while Attempt_GPS < 5:
    try:
        GPS = GPS_Data()
        Attempt_GPS += 1
        GPS.power_on(GPS.power_key)
    except Exception as e:
        GPS.power_down(GPS.power_key)
        print(e)
        continue
    break

start_time_global = datetime.now()
end_time_gloabl = datetime(2000,1,1)
x=1
restart = 0
while(1):
    print(x)
    x += 1
    while restart < 5:
        try:
            restart += 1
            gps_val = GPS.get_gps_position()
        except Exception as e:
            #print('\033[91m' + "{}".format(e))
            print(traceback.format_exc())
            time.sleep(1)
            gps_val = "fail"
            continue
        restart = 1 
        break

    if restart == 5:
        print("----------------------------------------------------------------")
        print("I'm here")
        print("----------------------------------------------------------------")
        serial.Serial('/dev/ttyS0',115200).flush()
        serial.Serial('/dev/ttyS0',115200).reset_input_buffer()
        serial.Serial('/dev/ttyS0',115200).reset_output_buffer()
        GPS.power_down(GPS.power_key)
        break
    print(gps_val)
    time.sleep(1)