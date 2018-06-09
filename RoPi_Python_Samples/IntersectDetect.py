import RoPi as rp
import cv2
import time
import math

#frame_width = 640
#frame_height = 480

#frame_width = 320
#frame_height = 240

frame_width = 160
frame_height = 128

#frame_width = 80
#frame_height = 64

#initiate the RoPi at speed 20% and set the width and height
ropi = rp.RoPi(speed= 20, width= frame_width, height= frame_height)


#the minimum
minPixArea = frame_width*frame_height*0.001
print("min pix area: ", minPixArea)

#threshold will make a region in the center
#that the object will be considered centered
threshold = 0.22

#hold the position the robot last saw the object
lastseenX = 0
lastseenY = 0

#this method is used as an empty callback function for the trackbars
def nothing(x):
    pass

# Creating a window for later use
cv2.namedWindow('Control Panel')

orangeMarker = [6,226,241,4,73,63]
blueMarker = [114,105,120,4,60,50]

selectedColor = blueMarker

# Creating trackbars

#cv.CreateTrackbar(trackbarName, windowName, value, count, onChange)  None
cv2.createTrackbar('hue', 'Control Panel',selectedColor[0],180,nothing)
cv2.createTrackbar('sat', 'Control Panel',selectedColor[1],255,nothing)
cv2.createTrackbar('val', 'Control Panel',selectedColor[2],255,nothing)
cv2.createTrackbar('hueRange', 'Control Panel',selectedColor[3],127,nothing)
cv2.createTrackbar('satRange', 'Control Panel',selectedColor[4],127,nothing)
cv2.createTrackbar('valRange', 'Control Panel',selectedColor[5],127,nothing)

#--------------------------------------------------------------
#this method will take in the original video frame
# and return a filtered binary frame
def filterColor(frame):

    #collect all the trackbar positions
    h = cv2.getTrackbarPos('hue','Control Panel')
    s = cv2.getTrackbarPos('sat','Control Panel')
    v = cv2.getTrackbarPos('val','Control Panel')
    hr = cv2.getTrackbarPos('hueRange', 'Control Panel')
    sr = cv2.getTrackbarPos('satRange', 'Control Panel')
    vr = cv2.getTrackbarPos('valRange', 'Control Panel')

    #use the trackbar positions to set
    #a boundary for the color filter
    hsvLower = (h-hr, s-sr, v-vr)
    hsvUpper = (h+hr, s+sr, v+vr)
    
    #turn into HSV color space
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    #mask will be a frame that has filtered the color we are looking for
    #that color will be within the hsvLower and hsvUpper constraints.
    mask = cv2.inRange(hsv, hsvLower, hsvUpper)

    return mask

#--------------------------------------------------------------

#this is tuned for my car, it will move the car forward and turn "90 degrees"
#suppose to occur when intersection is faced
def interLeftTurn():
    ropi.speed(40)
    ropi.moveForward()
    time.sleep(0.6)
    ropi.moveStop()
    time.sleep(0.1)
    ropi.moveLeft()
    time.sleep(0.3)
    ropi.moveStop()

#this will draw all the contours (4) and find if it detects the intersection
def drawAllContours(sortedCont):
    
    yAxisList = []
    xAxisList = []
    areaList = []
    areaSum = 0

    # loop through the sorted contours
    for i in range(0,len(sortedCont)):
        contour = sortedCont[i]
        # find the x value, y value, width, and height of the rectangle
        # that bounds the contour
        x, y, w, h = cv2.boundingRect(contour)
        
        if(w*h>minPixArea):
            areaList.append(w*h)
            areaSum = areaSum + w*h 
            # establish a color for the rectangle
            rectangleColor = (255, i*85, 255-i*85) #(Blue,Green,Red) they go from 0-255

            # create a rectangle in the frame using the values from the contour
            cv2.rectangle(frame, (x, y), (x + w, y + h), rectangleColor, 2)

            ((x, y), radius) = cv2.minEnclosingCircle(contour)
            yAxisList.append(int(y))
            xAxisList.append(int(x))
            cv2.putText(frame, format(i), (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, rectangleColor, 1, cv2.LINE_AA)
            if i > 0:#draw the lines between center points
                cv2.line(frame,(xAxisList[i],yAxisList[i]),(xAxisList[i-1],yAxisList[i-1]),(0,255-i*50,0),2)
                #draw from the center of the first contour to the next
                a = (yAxisList[i]-yAxisList[i-1])
                b = (xAxisList[i]-xAxisList[i-1])
                if ( abs(b)>0 ):
                    #make sure not to divide by zero
                    #find angle of line created from point to point
                    angle = math.atan(a/b)*180/(3.14159)
                    cv2.putText(frame, format(angle),int(x+20), int(y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 1, cv2.LINE_AA)
            if (i is 3) and (areaSum > 1800) and (abs(yAxisList[2]-yAxisList[1]) < frame_height*0.2) :
                #ropi.moveStop()
                print("intersection")
                #time.sleep(0.02)
                #check the distance between the 2 y axis objects
                #ropi.moveForward()
                #time.sleep(0.5)
                #if(yAxisList[2]-yAxisList[1]):
                #    interLeftTurn()
    

    


while (1):
    
    #grab intial time to measure how long
    #it takes to process the image
    #ticks1 = cv2.getTickCount()

    # grab the raw NumPy array representing the image - this array
    # will be 3D, representing the width, height, and # of channels
    #convert the image into a numpy array
    frame = ropi.getFrame()

    #flips the frame if necessary change 0 to 1 or 2..
    frame = cv2.flip(frame,-1)
    
    #///////////////////////////
    mask = filterColor(frame)
    mask = cv2.dilate(mask, None)
    mask = cv2.blur(mask, (7,7))
    mask = cv2.dilate(mask, None)
    #///////////////////////////
    
    #this "res" frame pieces together 2 the mask frame and the original frame
    res = cv2.bitwise_and(frame,frame, mask= mask)

    #Find contours
    cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) [-2]
    #sort the contours by size, biggest to smallest, max 5 contours
    sortedContours = sorted(cnts, key=cv2.contourArea, reverse=True)[:4]


    #-----------------------------------------------------------------------
    #Only proceed if at least one contour was found
    if len(cnts) > 0:
        # find the largest contour in the mask, then use
        # it to compute the minimum enclosing circle and
        # centroid
        drawAllContours(sortedContours)
        #maxCountour = max(cnts, key=cv2.contourArea)
        maxCountour = sortedContours[0]
        
        ((x, y), radius) = cv2.minEnclosingCircle(maxCountour)
        lastseenX = x
        lastseenY = y
        
        cv2.circle(res, (int(x), int(y)), int(radius),(0, 255, 255), 2)
        cv2.putText(res, format(int(y)), (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (211,211,211), 1, cv2.LINE_AA)
        #if the radius of that object is big enough

        #if(radius**2 > minPixArea and (y > frame_height*0.5)):
        if(radius**2 > minPixArea):
            
            
            #if x pixel is below 38% of the frame width ex. x<(320*0.38=121.6)
            if(x < (frame_width*(0.5-threshold))):
                ropi.speed(15)
                ropi.moveLeft()
                #time.sleep(0.02)
                #ropi.moveStop()
                #print("Right")
                
                
            elif (x > (frame_width*(0.5+threshold))):
                ropi.speed(15)
                ropi.moveRight()
                #time.sleep(0.02)
                #ropi.moveStop()
                #print("Left")

            #object is centered go forward   
            elif (x > (frame_width*(0.5-threshold)) and x < (frame_width*(0.5+threshold))):
                #ropi.moveStop()
                ropi.speed(30)
                ropi.moveForward()
                #print("Stopping")
            else:
                pass
        else:
            #scanning to the left
            ropi.speed(10)
            ropi.moveLeft()
            time.sleep(0.02)
            ropi.moveStop()
               
    else:#nothing is detected stop
            #scanning to the left
                  
        ropi.speed(10)
        ropi.moveLeft()
        time.sleep(0.02)
        ropi.moveStop()
        
        '''
        if(lastseenX < (frame_width*(0.5-threshold))):
            print("searching")
            ropi.speed(20)
            ropi.moveLeft()   
            time.sleep(0.1)
            ropi.moveStop()
            
        elif(lastseenX > (frame_width*(0.5+threshold))):
            print("searching")
            ropi.speed(20)
            ropi.moveRight()   
            time.sleep(0.1)
            ropi.moveStop()
        else:
            pass
       '''
    

        
    #-----------------------------------------------------------------------                

    #the key that is clicked save it as variable key
    key = cv2.waitKey(1) & 0xFF
 
    # if the `q` key was pressed, break from the loop
    if key == ord("q"):
        break

    
    #cv2.imshow("frame", frame)
    cv2.imshow('Control Panel',frame)
    cv2.imshow("res", res)

    #store the time elapsed
    #ticks2 = cv2.getTickCount()
    #(e2 - e1) gives you the number of ticks
    #this line converts the number of ticks into time elapsed per loop
    #timeElapsed = int((ticks2 - ticks1)/cv2.getTickFrequency()*1000)
    #print(timeElapsed,"ms")
    
#just in case the robot is still moving make it stop
ropi.moveStop()
#if click exit before clicking q, robot will still move
print("End of program")
cv2.destroyAllWindows()
