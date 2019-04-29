#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on 14/06/2017
Ver: 1.1
@author: lucas.balthazar
"""

#Importa bibliotecas
import socket
import threading
import numpy as np

class TCP_protocol(threading.Thread):
    def __init__(self, TCP_IP='10.128.44.7', port=10001, buffer=1024):
        threading.Thread.__init__(self)
        self.buffer_size = buffer
        self.port = int(port)       #port default = 10001
        self.tcpip = str(TCP_IP)
        self.error_list()
        self.start()
            
    def callback(self):
        self._stop()

    def run(self):
        self.commands()
        
    def commands(self):
        self.UP_NORM =  'UPMODE:NORMAL\r'           #In this mode of operation the power works in the standard update mode.
        self.ON =       'MON\r'                     #Turn the Module ON
        self.OFF =      'MOFF\r'                    #Turn the Module OFF
        self.VER =      'VER\r'                     #Return regarding the model and the current installed firmware version
        self.MST =      'MST\r'                     #Return value of power supply internal status register. \
                                                    #Example:#MST: 08000002\r\n, where, 08000002 is hex representation 
        self.MRESET =   'MRESET\r'                  #Reset module register
        self.MRI =      'MRI\r'                     #Returns readback value output current
        self.MRV =      'MRV\r'                     #Returns readback value output voltage
        self.loopi =    'LOOP:I\r'                  #Returns Constant Current (c.c.) mode
        self.loopv =    'LOOP:V\r'                  #Returns Constant Voltage (c.v.) mode
        self.MWI =      'MWI:'                      #Set the output current value when the module is in the constant current mode
        self.MWV =      'MWV:'                      #Set the output voltage value when the module is in the constant voltage mode
        self.MWIR =     'MWIR:'                     #Perform a ramp to the given current setpoint
        self.MSRI =     'MSRI:'                     #Change the value of the current ramp slew-rate

        #special features - firmware 1.5.17
        self.UP_WF =        'UPMODE:WAVEFORM\r'     #Command used to set the power module in analog control.
        self.KEEP_ST =      'WAVE:KEEP_START\r'     #Command used to start the waveform generation when the module is in TRIGGER mode.
        self.N_PERIODS =    'WAVE:N_PERIODS:'       #Command is used to set the number of periods the waveform needs to be reproduced.\
                                                    #By setting "0", the waveform is reproduced with an infinite number of periods.
        self.WF_POINTS =    'WAVE:POINTS:'          #Command is used to store the waveform points into the module. Min 100, Max 500000.\
                                                    #Resolution, point by point, 10 us.
        self.WF_START =     'WAVE:START\r'          #Command is used to start the waveform generation when the module is NOT in trigger mode.
        self.WF_STOP =      'WAVE:STOP\r'           #Command is used to stop the wafeform generation.

    def connect(self):
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.connect((self.tcpip, self.port))
            return True
        except:
            return False

    def send(self,msg):
        self.s.send(msg.encode('utf-8'))
                      
    def data_recv(self):
        data = self.s.recv(self.buffer_size)
        real = data.decode('utf-8')
        return real

    def on_output(self):
        self.send(self.ON)
        return self.check_reply()

    def disconnect(self):
        try:
            self.s.close()
            return True
        except:
            return False

    def off_output(self):
        self.send(self.OFF)
        return self.check_reply()

    def set_curr(self,current):   
        curr = str(current)
        curr_ref = self.MWI+curr+'\r'
        self.send(curr_ref)
        return self.check_reply()

    def set_volt(self,voltage):
        volt = str(voltage)
        volt_ref = self.MWV+volt+'\r'
        self.send(volt_ref)
        return self.check_reply()

    def read_curr(self):
        leitura = self.send(self.MRI)
        reply = self.data_recv()
        corrente = reply[5:14]
        try:
            corrente = float(corrente)   
            return corrente
        
        except AttributeError:
            return 'Reading failure'
        
    def read_volt(self):
        leitura = self.send(self.MRV)
        reply = self.data_recv()
        volts = reply[5:14]
        try:
            volts = float(volts)
            return volts
        
        except AttributeError:
            return 'Reading failure'

    def ramp_setpoint(self, end):
        final = str(end)
        final_ref = self.MWIR+final+'\r'
        self.send(final_ref)
        return self.check_reply()

    def cc_mode(self):          #Remember: Before change operation mode, turn the module OFF
        self.send(self.loopi)
        self.const_curr = True
        return self.check_reply()

    def cv_mode(self):          #Remember: Before change operation mode, turn the module OFF
        self.send(self.loopv)
        self.const_volt = True
        return self.check_reply()

    def damped_sinusoidal(self, amp, offset, freq, ncycle, theta, tau):
        
        sen = lambda t: (amp*np.sin(2*np.pi*freq*t + theta/360*2*np.pi) *
                                 np.exp(-t/tau) + offset)
        self.x = np.linspace(0, ncycle/freq, 10000)
        self.y = sen(self.x)

        pts = np.array2string(self.y, precision=2, separator=':').strip("[]").replace(" ", "")
        pts = pts.replace("\n", "")
        self.waveform_gen(pts)
        
    def waveform_gen(self, pts):
        self.send(self.WF_POINTS+str(pts)+'\r')
        return self.check_reply()
    
    def check_reply(self):
        value = self.data_recv()
        if value[1] == 'A':
            pass
        elif value[1] == 'N':
            errorbit = int(value[5]+value[6])
            if errorbit in self._errors:
                return self._errors[errorbit]
            else:
                return 'Unknown error'

    def error_list(self):
        self._errors = {1: 'Unknown command',2: 'Unknown Parameter',
                       3: 'Index out of range',4: 'Not Enough Arguments',
                       5: 'Privilege Level Requirement not met',
                       6: 'Saving Error on device',7: 'Invalid password',
                       8: 'Power supply in fault',9: 'Power supply already ON',
                       10:'Setpoint is out of model limits',
                       11:'Setpoint is oiut of software limits',
                       12:'Setpoint is not a number',13:'Module is OFF',
                       14:'Slew Rate out of limits', 15:'Device is set in local mode',
                       16:'Module is not in waveform mode',
                       17:'Module is in waveform mode', 18:'Device is set in remote mode',
                       19:'Module is already in the selected loop mode',
                       20:'Module is not in the selected loop mode',
                       99:'Setpoint is out of software limits'}
