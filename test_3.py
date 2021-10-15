#!/usr/bin/python
# -*- coding:utf-8 -*-
import RPi.GPIO as GPIO

import serial
import time

ser = serial.Serial('/dev/ttyS0',115200)
ser.reset_input_buffer()

power_key = 6
rec_buff = ''
rec_buff2 = ''
time_count = 0

def send_at(command,timeout):
    rec_buff = ''
    ser.write((command+('\n')).encode('utf-8'))
    time.sleep(timeout)
    if ser.in_waiting:
        time.sleep(0.01)
        rec_buff = ser.read(ser.in_waiting)
        print(rec_buff)


def power_on(power_key):
    print('SIM7600X is starting:')
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(power_key,GPIO.OUT)
    time.sleep(0.1)
    GPIO.output(power_key,GPIO.HIGH)
    time.sleep(2)
    GPIO.output(power_key,GPIO.LOW)
    time.sleep(10)
    ser.reset_input_buffer()
    print('SIM7600X is ready')

def power_down(power_key):
    print('SIM7600X is loging off:')
    GPIO.output(power_key,GPIO.HIGH)
    time.sleep(3)
    GPIO.output(power_key,GPIO.LOW)
    time.sleep(8)
    print('Good bye')
i=0
power_on(power_key)

print('AT+CGPSPWR=1')
print('---------------------------------------------')
send_at('AT+CGPSPWR=1', 1)
#ser.flush()
ser.reset_input_buffer()
ser.reset_output_buffer()
print('AT+CREG?')
print('---------------------------------------------')
time.sleep(2)
send_at('AT+CREG?', 1)
#ser.flush()
ser.reset_input_buffer()
ser.reset_output_buffer()
print('AT+CGPS=1,1')
print('---------------------------------------------')
time.sleep(2)
send_at('AT+CGPS=1,1', 1)
#ser.flush()
ser.reset_input_buffer()
ser.reset_output_buffer()
while i <20:
        if ser.writable():
            print('AT+CGPSINFO')
            print('---------------------------------------------')
            time.sleep(2)
            send_at('AT+CGPSINFO', 1)
            #ser.flush()
            ser.reset_input_buffer()
            ser.reset_output_buffer()

print('---------------------------------------------')
power_down(power_key)
