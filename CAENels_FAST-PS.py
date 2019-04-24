#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on 14/06/2017
Versão 1.0
@author: lucas.balthazar
"""

#Importa bibliotecas
import sys
import socket
import traceback
import threading
import numpy as np

class TCP_protocol(threading.Thread):
    def __init__(self, TCP_IP='10.128.44.7', port=10001, buffer=1024):
        threading.Thread.__init__(self)
        self.buffer_size = buffer
        self.port = int(port)       #port default = 10001
        self.tcpip = str(TCP_IP)
        self.start()
            
    def callback(self):
        self._stop()

    def run(self):
        self.Comandos()
        
    def Comandos(self):
        self.ON =       'MON\r'     #Turn the Module ON
        self.OFF =      'MOFF\r'    #Turn the Module OFF
        self.VER =      'VER\r'     #Return regarding the model and the current installed firmware version
        self.MST =      'MST\r'     #Return value of power supply internal status register. Example:#MST: 08000002\r\n, where, 08000002 is hex representation 
        self.MRESET =   'MRESET\r'  #Reset module register
        self.MRI =      'MRI\r'     #Returns readback value output current
        self.MRV =      'MRV\r'     #Returns readback value output voltage
        self.loopi =    'LOOP:I\r'  #Returns Constant Current (c.c.) mode
        self.loopv =    'LOOP:V\r'  #Returns Constant Voltage (c.v.) mode
        self.MWI =      'MWI:'      #Set the output current value when the module is in the constant current mode
        self.MWV =      'MWV:'      #Set the output voltage value when the module is in the constant voltage mode
        self.MWIR =     'MWIR:'     #Perform a ramp to the given current setpoint
        self.MSRI =     'MSRI:'     #Change the value of the current ramp slew-rate

        #special features - firmware 1.5.17
        self.UP_WF =        'UPMODE:WAVEFORM\r'     #Command used to set the power module in analog control.
        self.KEEP_ST =      'WAVE:KEEP_START\r'     #Command used to start the waveform generation when the module is in TRIGGER mode.
        self.N_PERIODS =    'WAVE:N_PERIODS:'       #Command is used to set the number of periods the waveform needs to be reproduced. By setting "0", the waveform is reproduced with an infinite number of periods.
        self.WF_POINTS =    'WAVE:POINTS:'          #Command is used to store the waveform points into the module. Min 100, Max 500000. Resolution, point by point, 10 us.
        self.WF_START =     'WAVE:START\r'          #Command is used to start the waveform generation when the module is NOT in trigger mode.
        self.WF_STOP =      'WAVE:STOP\r'           #Command is used to stop the wafeform generation.

    def Conectar(self):
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.connect((self.tcpip, self.port))
            return True
        except Exception:
                traceback.print_exc(file=sys.stdout)

    def Enviar(self,msg):            
        self.s.send(msg.encode('utf-8'))
                      
    def data_recv(self):
        data = self.s.recv(self.buffer_size)
        real = data.decode('utf-8')
        return real

    def ON_output(self):
        self.Enviar(self.ON)
        return self.check_reply()

    def Desconectar(self):
        self.s.close()        

    def OFF_output(self):
        self.Enviar(self.OFF)
        return self.check_reply()

    def set_curr(self,current):     
        curr = str(current)
        curr_ref = self.MWI+curr+'\r'
        self.Enviar(curr_ref)       ## Send constant current reference
        return self.check_reply()

    def set_volt(self,voltage):
        volt = str(voltage)
        volt_ref = self.MWV+volt+'\r'
        self.Enviar(volt_ref)
        return self.check_reply()

    def read_curr(self):
        leitura = self.Enviar(self.MRI)
        reply = self.data_recv()
        corrente = reply[5:14]
        try:
            corrente = float(corrente)    
            return corrente
        
        except AttributeError:
            return 'Falha na leitura'
        
    def read_volt(self):
        leitura = self.Enviar(self.MRV)
        reply = self.data_recv()
        volts = reply[5:14]
        try:
            volts = float(volts)    
            return volts
        
        except AttributeError:
            return 'Falha na leitura'

    def ramp_setpoint(self, end):
        final = str(end)
        final_ref = self.MWIR+final+'\r'
        self.Enviar(final_ref)
        return self.check_reply()

    def cc_mode(self):          ## Remember: Before change operation mode, turn the module OFF
        self.Enviar(self.loopi)
        self.const_curr = True
        return self.check_reply()

    def cv_mode(self):          ## Remember: Before change operation mode, turn the module OFF
        self.Enviar(self.loopv)
        self.const_volt = True
        return self.check_reply()

    def damped_sinusoidal(self, amp, offset=0, freq, ncycle, theta=0, tau):
        
        sen = lambda t: (amp*np.sin(2*np.pi*freq*t + theta/360*2*np.pi) *
                                 np.exp(-t/tau) + offset)
        self.x = np.linspace(0, ncycle/freq, 100000)
        self.y = sen(self.x)

        pontos = np.array2string(self.y, precision=2, separator=',')
        pontos = pontos.strip("[]")
        self.waveform_gen(pontos)
        
    def waveform_gen(self, pts):
        self.Enviar(self.WF_POINTS+str(pts)+'\r')
        return self.check_reply()
    
    def check_reply(self):
        value = self.data_recv()    
        if value[1] == 'A':
            pass        
        elif value[1] == 'N':
            errorbit = int(value[5]+value[6])
            return self.error_list(errorbit)
              
    #Errors checklist
    def error_list(self,val):
        if val == 1:
            return 'Unknown command'
        elif val == 2:
            return 'Unknown Parameter'
        elif val == 3:
            return 'Index out of range'
        elif val == 4:
            return 'Not Enough Arguments'
        elif val == 5:
            return 'Privilege Level Requirement not met'
        elif val == 6:
            return 'Saving Error on device'
        elif val == 7:
            return 'Invalid password'
        elif val == 8:
            return 'Power supply in fault'
        elif val == 9:
            return 'Power supply already ON'
        elif val == 10:
            return 'Setpoint is out of model limits'
        elif val == 11:
            return 'Setpoint is out of software limits'
        elif val == 12:
            return 'Setpoint is not a number'
        elif val == 13:
            return 'Module is OFF'
        elif val == 14:
            return 'Slew Rate out of limits'
        elif val == 15:
            return 'Device is set in local mode '
        elif val == 16:
            return 'Module is not in waveform mode'
        elif val == 17:
            return 'Module is in waveform mode'
        elif val == 18:
            return 'Device is set in remote mode'
        elif val == 19:
            return 'Module is already in the selected loop mode'
        elif val == 20:
            return 'Module is not in the selected loop mode'
        elif val == 99:
            return 'Setpoint is out of software limits'        
        else:
            return 'Unknown error'
