#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on 14/06/2017
Ver: 1.1
@author: Lucas Balthazar   (lucas.balthazar@lnls.br)
contribution: Paolo Fabris (p.fabris@caenels.com)
"""

#Library
import socket
import threading
import time
import numpy as np

class TCP_protocol(threading.Thread):
    def __init__(self, TCP_IP='10.128.44.7', port=10001, buffer=1024):
        threading.Thread.__init__(self)
        self.buffer_size = buffer
        self.port = int(port)                       #port default = 10001
        self.tcpip = str(TCP_IP)
        self.error_list()
        self.start()

    def callback(self):
        self._stop()

    def run(self):
        self.commands()
        #self._testWaveform()

    def commands(self):
        self.UP_NORM =  'UPMODE:NORMAL\n\r'         #In this mode of operation the power works in the standard update mode.
        self.ON =       'MON\r\n'                   #Turn the Module ON
        self.OFF =      'MOFF\r\n'                  #Turn the Module OFF
        self.VER =      'VER\r\n'                   #Return regarding the model and the current installed firmware version
        self.MST =      'MST\r\n'                   #Return value of power supply internal status register. \
                                                    #Example:#MST: 08000002\r\n, where, 08000002 is hex representation 
        self.MRESET =   'MRESET\r\n'                #Reset module register
        self.MRI =      'MRI\r\n'                   #Returns readback value output current
        self.MRV =      'MRV\r\n'                   #Returns readback value output voltage
        self.loopi =    'LOOP:I\r\n'                #Returns Constant Current (c.c.) mode
        self.loopv =    'LOOP:V\r\n'                #Returns Constant Voltage (c.v.) mode
        self.MWI =      'MWI:'                      #Set the output current value when the module is in the constant current mode
        self.MWV =      'MWV:'                      #Set the output voltage value when the module is in the constant voltage mode
        self.MWIR =     'MWIR:'                     #Perform a ramp to the given current setpoint
        self.MSRI =     'MSRI:'                     #Change the value of the current ramp slew-rate

        #special features - firmware 1.5.17
        self.UP_WF =        'UPMODE:WAVEFORM\r\n'   #Command used to set the power module in analog control.
        self.KEEP_ST =      'WAVE:KEEP_START\r\n'   #Command used to start the waveform generation when the module is in TRIGGER mode.
        self.N_PERIODS =    'WAVE:N_PERIODS:'       #Command is used to set the number of periods the waveform needs to be reproduced.\
                                                    #By setting "0", the waveform is reproduced with an infinite number of periods.
        self.WF_POINTS =    'WAVE:POINTS:'          #Command is used to store the waveform points into the module. Min 100, Max 500000.\
                                                    #Resolution, point by point, 10 us.
        self.WF_START =     'WAVE:START\r\n'        #Command is used to start the waveform generation when the module is NOT in trigger mode.
        self.WF_STOP =      'WAVE:STOP\r\n'         #Command is used to stop the wafeform generation.

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

    def reset(self):
        self.send(self.MRESET)
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
        curr_ref = self.MWI+curr+'\r\n'
        self.send(curr_ref)
        return self.check_reply()

    def set_volt(self,voltage):
        volt = str(voltage)
        volt_ref = self.MWV+volt+'\r\n'
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
        final_ref = self.MWIR+final+'\r\n'
        self.send(final_ref)
        return self.check_reply()

    def cc_mode(self):                              #Remember: Before change operation mode, turn the module OFF
        self.send(self.loopi)
        self.const_curr = True
        return self.check_reply()

    def cv_mode(self):                              #Remember: Before change operation mode, turn the module OFF
        self.send(self.loopv)
        self.const_volt = True
        return self.check_reply()

    def damped_sinusoidal(self, amp, offset, freq, ncycle, theta, tau):
        sen = lambda t: (amp*np.sin(2*np.pi*freq*t + theta/360*2*np.pi) *
                                 np.exp(-t/tau) + offset)
        totalPoints = int(ncycle * 100000 / freq)
        self.x = np.linspace(0, ncycle/freq, totalPoints)
        self.y = sen(self.x)

        if ((self.y.size > 500000) or (self.y.size < 100)):
            print("ERROR: invalid number of points")

        pts = ''
        for i in range(self.y.size):
            pts += '{:.5f}'.format(self.y[i]) + ":"
        pts = pts[:-1]
        self.waveform_gen(pts)

    def waveform_gen(self, pts):
        self.send(self.WF_POINTS+str(pts)+'\r\n')
        time.sleep(0.1)
        return self.check_reply()

    def waveform_mode(self):
        self.send(self.UP_WF)
        time.sleep(0.1)
        return self.check_reply()

    def waveform_start(self):
        self.send(self.WF_START)
        time.sleep(0.1)
        return self.check_reply()

    def waveform_stop(self):
        self.send(self.WF_STOP)
        time.sleep(0.1)
        return self.check_reply()

    def waveform_keep_start(self):
        self.send(self.KEEP_ST)
        time.sleep(0.1)
        return self.check_reply()

    def waveform_nPeriods(self, nPeriods = 0):
        self.send(self.N_PERIODS + str(nPeriods) + "\r\n")
        time.sleep(0.1)
        return self.check_reply()


    def check_reply(self):
        value = self.data_recv()
        if value[1] == 'A':
            pass
        elif value[1] == 'N':
            print(value)
            errorbit = int(value[5]+value[6])
            if errorbit in self._errors:
                return self._errors[errorbit]
            else:
                return 'Unknown error'

    def _testWaveform(self):
        self.connect()

        self.off_output()
        time.sleep(1)
        self.reset()
        self.cc_mode()
        self.waveform_mode()

        self.on_output()
        self.waveform_stop()
        self.waveform_nPeriods(0)
        self.damped_sinusoidal(2.1, 0.0, 2, 10, 0, 2.0)

        self.waveform_start()

        self.disconnect()

    def error_list(self):
        self._errors = {
            '01': 'Unknown Command',
            '02': 'Unknown Parameter',
            '03': 'Index Out Of Range',
            '04': 'Not Enough Arguments',
            '05': 'Privilege Level Requirement not met',
            '06': 'Save Error on device',
            '07': 'Invalid Password',
            '08': 'Module in fault',
            '09': 'Module already on',
            '10': 'Set-point is out of hardware bounds',
            '11': 'Set-point is out of software limits',
            '12': 'Set-point is not a number',
            '13': 'Module is off',
            '14': 'Slew rate out of limits',
            '15': 'Device is set in local mode, cannot modify values from remote interface while in this state',
            '16': 'Module is not currently generating a waveform',
            '17': 'Module is currently generating a waveform',
            '18': 'Device is not set in local mode, cannot modify values from local interface while in this state',
            '19': 'Loop mode already set to desired value',
            '20': 'Loop mode is not the same that uses the variable required to change',
            '21': 'Module is not in normal update mode',
            '22': 'Float mode already set to desired value',
            '23': 'Unknown sub-command for SFP command',
            '24': 'Unknown feature or feature not available for actual module (AIN,TRIG)',
            '25': 'Parallel fault',
            '26': 'Waveform error',
            '27': 'Cannot open the required file',
            '28': 'Cannot change set point because the module is inverting polarity',
            '29': 'Cannot write waveform data',
            '30': 'Polarity switch not allowed',
            '31': 'Cannot set options for socket used by oscilloscope',
            '32': 'Cannot change settings because in parallel slave mode',
            '33': 'MASTER and SLAVES have different firmware versions',
            '34': 'MASTER and SLAVES are different models',
            '35': 'MASTER and SLAVES have different ratings',
            '36': 'The required feature is not available',
            '37': 'UDP buffer overflow',
            '38': 'Cannot apply the setting because the module is in WAIT FOR OFF',
            '99': 'Unknown Error'
}

##if __name__ == "__main__":
##    tcp = TCP_protocol("192.168.1.91")

