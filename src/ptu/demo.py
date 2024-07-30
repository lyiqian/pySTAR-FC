import serial
import time

PORT_NAME = '/dev/ttyUSB0'

def ser_write(ser, s):
    ser.write(s.encode('ascii'))

global ser
ser = serial.Serial(PORT_NAME, 9600, timeout=1)
ser.xonxoff = True
ser.isOpen()

ser_write(ser, 'pp0 ')
ser_write(ser, 'tp0 ')
ser_write(ser, 'pxu1500 ')
ser_write(ser, 'pnu-1000 ')
ser_write(ser, 'tn-900 ')
ser_write(ser, 'tx900 ')
# ser_write(ser, 'pp1000 ')
# ser_write(ser, 'tp500 ')
ser_write(ser, 'pp1000 ')
ser_write(ser, 'tp-500 ')



ser.isOpen()

# print 'Enter your commands below.\r\n'

# input=1
# while 1 :
#     input = raw_input("")
#     if input == 'exit':
#         ser.close()
#         exit()
#     else:
#         ser.write(input + '\r\n')
#         out = ''
#         time.sleep(1)
#         while ser.inWaiting() > 0:
#             out += ser.read(1)

#         if out != '':
#             print (">>" + out)


ser.close()