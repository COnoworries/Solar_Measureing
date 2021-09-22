from ADC import MCP3208
import time

adc = MCP3208()
while(1):
    SZ1 = adc.read(channel = 6)
    print("Anliegende Spannung: %.2f" % (value / 1024.0  * 3.3) )
    time.sleep(1)
