import RoPi_SerialCom as ropi
#this program will show you how you
#how to use the motors and set the speed.
import time
#you can let speed be set any whole number from 0 - 100

print("speed 30%")
ropi.speed(30.1)
ropi.forward()
time.sleep(2)

print("speed 50%")
ropi.speed(50)
ropi.backward()
time.sleep(1)

print("speed 60%")
ropi.speed(60)
ropi.forward()
time.sleep(1)

ropi.stop()
