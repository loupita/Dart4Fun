#!/usr/bin/python
# -*- coding: utf-8 -*-

# Second Year ENSTA Bretagne SPID Project
#    D : Brian Detourbet
#    A : Elouan Autret
#    A : Fahad Al Shaik
#    R : Corentin Rifflart
#    R : Clément Rodde
#    T : Rémi Terrien

# Code modified in May 2016, by BenBlop (small changes to conform with
#  new DART)

# Code modified in May 2017, by BenBlop (big changes to adapt to Irvin's
# drivers and to communicate with V-REP using sockets

# student starting code

import os
import time
import math
import struct
import sys


def high_low_int(high_byte, low_byte):
    '''
    Convert low and low and high byte to int
    '''
    return (high_byte << 8) + low_byte

def high_byte(integer):
    '''
    Get the high byte from a int
    '''
    return integer >> 8


def low_byte(integer):
    '''
    Get the low byte from a int
    '''
    return integer & 0xFF

class Dart():
    def __init__(self):

        
        # test if on real robot, if yes load the drivers
#        if os.access("/var/www/daarrt.conf", os.F_OK) :
        if os.access("/sys/class/gpio/gpio266", os.F_OK) :
            print ("Real DART is being created")

            # Import modules
            from drivers.trex import TrexIO
            from drivers.sonars import SonarsIO
            from drivers.razor import RazorIO
            from drivers.rear_odo import RearOdos

            self.__trex = TrexIO()
            self.__sonars = SonarsIO()
            self.__razor = RazorIO()
            self.__rear_odos = RearOdos()
            self.__trex.command["use_pid"] = 0 # 1

        # if not create virtual drivers for the robot running in V-REP
        else :
            print ("Virtual DART is being created")

            import threading

            import socket
            import sys
            import struct
            import time
 
            # socket connection to V-REP
            self.__HOST = 'localhost'  # IP of the sockect
            self.__PORT = 30100 # port (set similarly in v-rep)

            self.__s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print ('Socket created')

            # bind socket to local host and port
            try:
                # prevent to wait for  timeout for reusing the socket after crash
                # from :  http://stackoverflow.com/questions/29217502/socket-error-address-already-in-use
                self.__s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.__s.bind((self.__HOST, self.__PORT))
            except socket.error as msg:
                print (msg)
                sys.exit()
            print ('Socket bind completed')
             
            # start listening on socket
            self.__s.listen(10)
            print ('Socket now listening')

            # reset variables 
            self.__vMotorLeft =  0.0
            self.__vMotorRight = 0.0
            self.__vEncoderLeft = 0
            self.__vEncoderRight = 0
            self.__vSonarLeft = 0.0
            self.__vSonarRight = 0.0
            self.__vSonarFront = 0.0
            self.__vSonarRear = 0.0
            self.__vHeading =  0.0

            # initiate communication thread with V-Rep
            self.__simulation_alive = True
            a = self.__s
            vrep = threading.Thread(target=self.vrep_com_socket,args=(a,))
            vrep.start()

            # start virtual drivers 
            import vDaarrt.modules.vTrex as vTrex
            import vDaarrt.modules.vSonar as vSonar
            import vDaarrt.modules.vRazor as vRazor

            self.__trex = vTrex.vTrex()
            self.__razor = vRazor.vRazorIO()
            self.__sonars = vSonar.vSonar(self)



    @property
    def s(self):
        return self.__s

    @property
    def vMotorLeft(self):
        return self.__vMotorLeft

    @property
    def vMotorRight(self):
        return self.__vMotorRight

    @property
    def vSonarFront(self):
        return self.__vSonarFront

    @property
    def vSonarRear(self):
        return self.__vSonarRear

    @property
    def vSonarLeft(self):
        return self.__vSonarLeft

    @property
    def vSonarRight(self):
        return self.__vSonarRight

    @property
    def vEncoderLeft(self):
        return self.__vEncoderLeft

    @property
    def vEncoderRight(self):
        return self.__vEncoderRight

    @property
    def simulation_alive(self):
        return self.__simulation_alive

    @property
    def vHeading(self):
        return self.__vHeading

    @property
    def angles(self):
        return self.__razor.angles 
    
    def vrep_com_socket(vdart,s):
        print (s)
        RECV_BUFFER = 4096 # buffer size 
        while True:
            #wait to accept a connection - blocking call
            conn, addr =  s.accept()
            print ('Connected with ' + addr[0] + ':' + str(addr[1]))
            #print (conn)

            while True:
                #print ("socket read",conn)
                data = conn.recv(RECV_BUFFER)
                #print (len(data))
                hd0,hd1,sz,lft,vSonarFront, vSonarRear,vSonarLeft, vSonarRight, vEncoderLeft, vEncoderRight, vHeading, simulationTime = struct.unpack('<ccHHffffffff',data)
                #print (hd0,hd1,sz,lft,vSonarFront, vSonarRear,vSonarLeft, vSonarRight, vEncoderLeft, vEncoderRight, vHeading, simulationTime)

                #print (vEncoderLeft, vEncoderRight, vHeading)

                vdart.vrep_update_sim_param (vEncoderLeft,vEncoderRight,vSonarLeft,vSonarRight,vSonarFront,vSonarRear,vHeading)

                vMotorLeft = vdart.vMotorLeft
                vMotorRight = vdart.vMotorRight

                strSend = struct.pack('<BBHHff',data[0],data[1],8,0,vMotorLeft,vMotorRight)
                conn.send(strSend)
                if not vdart.simulation_alive:
                    break
                time.sleep(0.010)

            if not vdart.simulation_alive:
                break



    def vrep_update_sim_param (self,vEncoderLeft,vEncoderRight,vSonarLeft,vSonarRight,vSonarFront,vSonarRear,vHeading):
        self.__vEncoderLeft = vEncoderLeft
        self.__vEncoderRight = vEncoderRight
        self.__vSonarLeft = vSonarLeft
        self.__vSonarRight = vSonarRight
        self.__vSonarFront = vSonarFront
        self.__vSonarRear = vSonarRear
        self.__trex.status["left_encoder"] = vEncoderLeft
        self.__trex.status["right_encoder"] = vEncoderRight
        self.__vMotorLeft = self.__trex.command["left_motor_speed"]
        self.__vMotorRight = self.__trex.command["right_motor_speed"]
        self.__vHeading = vHeading

    # insert here your functions to control the robot using motors, sonars
    # encoders and heading

    def stop(self):
        print ("Game Over")
        # add a command to stop the motors
        self.set_speed(0,0)
        # stop the connection to the simulator	
        self.__simulation_alive = False
   
    def set_speed(self, speed_left, speed_right):
        self.__trex.command["left_motor_speed"] = speed_left
        self.__trex.command["right_motor_speed"] = speed_right 
    
    def get_odometers(self):
        vLeft = self.__trex.status ['left_encoder']
        vRight = self.__trex.status ['right_encoder']
        return vLeft, vRight  
        
    def get_distance(self, direction):
        return(self.__sonars.get_distance(direction))
	
    def get_angles(self):
        #return(self.__razor.angles()[0])
        return(self.__vHeading)

    def goCap(self, trigo):
        self.set_speed(50,-50)
        while(self.get_angles()-trigo > 2 or self.get_angles()-trigo < -2):
            continue
        self.stop()
 
    def center(self, a,b,s):
        
        if s<=-180:
            s = s + 360
        elif s > 180:
            s = s - 360
        #a entre -180 et 180
        #b entre -180 et 180
        return(s)


    def setHeading(self, head):
        #head entre 0 et 360
        headErrMax = 0.5
        headOK = False
        while not headOK :
            headMes = self.get_angles()
            headErr = head - headMes
            headErr = self.center(head, headMes, headErr)
            #headErr = headErr - 180
            #headErr centré en 0
            vit = abs(headErr)/4 + 30
            if headErr >=0 :
                self.set_speed(vit,-vit)
            else :
                self.set_speed(-vit,vit)

            if abs(headErr) < headErrMax:
                print("ca marche Michel")
                headOK = True
                self.set_speed(0,0)
            else:
                print(self.__vHeading)
                #print(abs(headErr) - headErrMax)
                time.sleep(0.01)

    def goLineHeading (self,head,speed, duration):
        self.setHeading(head, 1)
        capinitial=head
        t0=time.time()
        t1=time.time()
        capfinal=self.get_angles()
        while t1-t0 < duration:
            if capinitial-capfinal>0:
                self.set.speed(speed[0]+0.5,speed[1])
            else:
                self.set.speed(speed[0], speed[1]+0.5)

    def goLineOdo (self,speed, duration):
        self.setHeading(1,1)
        t0=time.time()
        t1=time.time()
        a=self.get_odometers()
        while t1-t0 < duration:
            time.sleep(0.1)
            b=self.get_odometers()
            if b-a==0 or b-a<0.001:
                self.goLineHeading(self.setHeading(1,1), speed,duration)
                a=b

    def obstcleAVoid(self):
        distanceMax=0.1
        d=self.get_distance(front)
        if d-distanceMax<0:
             self.goLineHeading (self.setHeading(1,1),(50,-50), 0.1)
        else:
            self.goLineHeading (self.setHeading(1,1),(50,50), 0.1)

    def goCurveOdo (self,speedTan, radius, sign, duration):

        t0=time.time()
        t1=time.time()
        while t1-t0 < duration:
            if sign==1:
                self.goLineHeading (self.setHeading(1,1),(50,-50), 0.1)
	    else:
                self.goLineHeading (self.setHeading(1,1),(-50,50), 0.1)
	
        
            
        
                


            
            
        

	
        

        
        

if __name__ == "__main__":
    myDart = Dart()

    #arrêt
    myDart.stop()


