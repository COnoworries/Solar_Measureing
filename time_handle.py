import threading
interval = 1
from datetime import datetime, timedelta
import time

# def myPeriodicFunction():
#     print(datetime.now())
#     print ("This loops on a timer every %d seconds" % interval)

# def startTimer():
#     threading.Timer(interval, startTimer).start()
#     myPeriodicFunction()

# startTimer()
# while(1):
#     start = datetime.now()
#     print(datetime.now())
#     end = datetime.now()

#     exec_time = end - start
#     print(exec_time)
#     time.sleep(1-exec_time.total_seconds())

start_time_global = datetime.now()
end_time_gloabl = datetime(2000,1,1)
x = 1
a = 0
while(1):
    while start_time_global + timedelta(seconds=x) > end_time_gloabl:
        start_time_local = datetime.now()
        end_time_local = datetime(2000,1,1)
        
        while start_time_local + timedelta(milliseconds=100) > end_time_local:
            #print("PEACE")
            end_time_local = datetime.now()
        end_time_gloabl = datetime.now()

        
        # if x != 10:
        #     print("Es ist passier!")

        #print("SEKUNDE VORBEI")
        a += 1
        print(a)

    if a != 10:
        print(a)
        print("Es ist passiert!")
    
    print(datetime.now())
    
    
    a = 0
    x += 1   
       

                        