import math
from datetime import datetime

def time_convert(date_val, time_val):
    "converts date and time strings to 'datetime' elements (format: date = 'DDMMYY', time= 'HHMMSS')"
    date = float(date_val)
    y = int(math.modf(date/100)[0]*100)+2000
    m = int(math.modf(math.modf(date/100)[1]/100)[0]*100)
    d = int(math.modf(math.modf(date/100)[1]/100)[1])
    print(m)
    date_string = "{0:04}/{1:02}/{2:02}".format(y,m,d)
    t = float(time_val)
    S = int(math.modf(t/100)[0]*100)
    M = int(math.modf(math.modf(t/100)[1]/100)[0]*100)
    H = int(math.modf(math.modf(t/100)[1]/100)[1]) + 1
    time_string = "{0:02}/{1:02}/{2:02}".format(H,M,S)
    end_string = date_string + '/' + time_string
    element = datetime.strptime(end_string,"%Y/%m/%d/%H/%M/%S")
    return element

date = '081121'
time = '070138'

print(time_convert(date, time))