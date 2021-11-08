from ADC import MCP3208
import time

adc = MCP3208()
x = 0
while(x < 30):
    CH1 = adc.read(channel = 0)
    CH2 = adc.read(channel = 1)
    CH3 = adc.read(channel = 2)
    CH4 = adc.read(channel = 3)
    CH5 = adc.read(channel = 4)
    CH6 = adc.read(channel = 5)
    CH7 = adc.read(channel = 6)
    CH8 = adc.read(channel = 7)
    print("Anliegende Spannung Ch1: %.2f" % (CH1 / 4096.0  * 3.33) )
    print("Anliegende Spannung Ch2: %.2f" % (CH2 / 4096.0  * 3.33) )
    print("Anliegende Spannung Ch3: %.2f" % (CH3 / 4096.0  * 3.33) )
    print("Anliegende Spannung Ch4: %.2f" % (CH4 / 4096.0  * 3.33) )
    print("Anliegende Spannung Ch5: %.2f" % (CH5 / 4096.0  * 3.33) )
    print("Anliegende Spannung Ch6: %.2f" % (CH6 / 4096.0  * 3.33) )
    print("Anliegende Spannung Ch7: %.2f" % (CH7 / 4096.0  * 3.33) )
    print("Anliegende Spannung Ch8: %.2f" % (CH8 / 4096.0  * 3.33) )
    x += 1
    time.sleep(1)
