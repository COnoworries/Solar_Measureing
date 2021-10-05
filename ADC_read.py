from ADC import MCP3208
import time

adc = MCP3208()
while(1):
    SZ = adc.read(channel = 6)
    print("Anliegende Spannung: %.2f" % (SZ / 4096.0  * 10.0) )
    time.sleep(1)
