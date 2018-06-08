import os
import sys
sys.path.append('/usr/local/lib/python2.7/site-packages')

from picamera.array import PiRGBArray
from picamera import PiCamera
import time
import cv2
import numpy as np
import RoPi_SerialCom as ropi

#width in pixels of camera resolution
#resolution_w = 320
resolution_w = 160
threshold = 0.125*resolution_w

#height in pixels of camera resolution
#resolution_h = 240
resolution_h = 128

#the minimum pixel area, if an objects area is to small we will ignore it
minPixArea = resolution_w*resolution_h*0.001


#the color thresholds these are looking for blue
lower = np.array([100,83-117,33-68])
upper = np.array([130,83+117,33+68])



#Initialize camera
camera = PiCamera()
camera.resolution = (resolution_w,resolution_h)
camera.hflip = True
camera.vflip = True
rawCapture = PiRGBArray(camera)
time.sleep(0.1)


def drawAndFind(contour, frame, color):

    #find the min bounding rectangle of the contour
    rect = cv2.minAreaRect(contour)
            
    #center = rect[0]#(x,y)
    x = int(rect[0][0])
    y = int(rect[0][1])
    #size = rect[1]#(width, height)
    #angle = rect[2]#of most top length of bounding box
            
    #Draw a circle at the center of the rectangle
    cv2.circle(frame, (x, y), 2, (255,255,255), -1)

    box = np.int0(cv2.cv.BoxPoints( rect ))
            
    #draw the bounding box onto "frame"
    cv2.drawContours(frame, [box], 0, color, 2)
    return x, y

#to use this function you must give it the center of the object
def ropiCenterTo(x,y):
    amICentered = False
    #the threshold for centering to an object
    #threshold = 0.125*resolution_w
    
    if x < (resolution_w/2-threshold):
        ropi.left()
        print("left", x)
    elif x > (resolution_w/2+threshold):
        ropi.right()
        print("right", x)
    else:
        amICentered = True
        print("centered", x)

    return amICentered
    
                    
def filterFrame(frame, lowerThreshold, upperThreshold):
    #Filter out all colors except those within the threshold
    hsvFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    filteredFrame = cv2.inRange(hsvFrame, lowerThreshold, upperThreshold)
    
    filteredFrame = cv2.dilate(filteredFrame,np.ones((3,3),np.uint8),iterations = 1)
    filteredFrame = cv2.morphologyEx(filteredFrame, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT,(5,5)) )
    #https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_imgproc/py_morphological_ops/py_morphological_ops.html

    filteredFrame = cv2.blur(filteredFrame,(5,5))
    ret,filteredFrame = cv2.threshold(filteredFrame,20,255,cv2.THRESH_BINARY)
    
    colorCutoutFrame = cv2.bitwise_and(frame,frame, mask= filteredFrame)
    return filteredFrame , colorCutoutFrame

def simplefilterFrame(frame, lowerThreshold, upperThreshold):
    #Filter out all colors except those within the threshold
    hsvFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    filteredFrame = cv2.inRange(hsvFrame, lowerThreshold, upperThreshold)
    
    colorCutoutFrame = cv2.bitwise_and(frame,frame, mask= filteredFrame)
    #return 2 frames
    return filteredFrame , colorCutoutFrame


def ropiAvoidWalls():
    #read the top IR sensors
    leftIR, middleIR, rightIR = ropi.readTopIRsensors()

    #detect something on the left move right
    if leftIR < 400:
        ropi.right()
        print("right")
        time.sleep(0.2)
    #detect something on the right move left    
    elif rightIR < 400:
        ropi.left()
        print("left")
        time.sleep(0.2)
    #detect something ahead, move backward    
    elif middleIR < 400:
        print("Backward")
        ropi.backward()
        time.sleep(1)
        ropi.left()
        time.sleep(0.2)

    #nothing ahead move straight ahead
    else:
        print("Forward")
        ropi.forward()

def ropiAvoidBlackLines():
    
    leftBottomIR, middleBottomIR, rightBottomIR = ropi.readBottomIRSensors()
    

    #detect something on the left move right
    if leftBottomIR<1:
        ropi.right()
        print("black line move right")
        time.sleep(0.2)
        
    #detect something on the right move left    
    elif rightBottomIR<1:
        ropi.left()
        print("black line move left")
        time.sleep(0.2)
        
        
    #detect something ahead, move backward    
    elif middleBottomIR<1:
        print("Backward")
        ropi.backward()
        time.sleep(0.2)

    #nothing ahead move straight ahead
    else:
        #print("Forward")
        #ropi.forward()
        pass
        
ropi.speed(50)

for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):

    #ropiAvoidWalls()
    #ropiAvoidBlackLines()
    
    #Get camera feed and turn into numpy array
    frame = np.array(frame.array)

    #filter the frame
    mask, bluemask = filterFrame(frame,lower,upper)
    #mask, bluemask = simplefilterFrame(frame,lower,upper)

    #display only the color you want
    cv2.imshow("bluemask", bluemask)

    #Find contours
    cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) [-2]
    #sort the contours by size, biggest to smallest, max 5 contours
    sortedContours = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]

    
    #If no contours could be found, do nothing        
    #If the largest contour is less than 0.1 max pixel area, do nothing
    if len(cnts) > 0 and cv2.contourArea(sortedContours[0]) > minPixArea:
        x, y = drawAndFind(sortedContours[0], frame, (0,255,255))
        isLaneCentered = ropiCenterTo(x,y)
        if (isLaneCentered is True):
            ropi.forward()
            print("forward")
    else:
        ropi.stop()
    #if you want to draw the second largest contour uncomment below 
    if len(cnts) > 1 and cv2.contourArea(sortedContours[1]) > minPixArea:
        x, y = drawAndFind(sortedContours[1], frame, (255,255,0))


    #Update windows
    cv2.imshow("Mask", mask)

    #these two lines show you the thresholds that are used when trying to center
    cv2.line(frame,(int(resolution_w/2-threshold),0),(int(resolution_w/2-threshold),resolution_h),(0,0,255),1)
    cv2.line(frame,(int(resolution_w/2+threshold),0),(int(resolution_w/2+threshold),resolution_h),(0,0,255),1)

    cv2.imshow("Result", frame)

    #Free up capture stream
    rawCapture.truncate(0)

    #Press 'q' to quit
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        ropi.stop()
        break


#Stop drone and destroy windows
ropi.stop()
cv2.destroyAllWindows()
