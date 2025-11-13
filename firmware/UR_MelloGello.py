import sys
import M5
from M5 import *
from unit import KeyUnit
from unit import Roller485Unit
from unit import Joystick2Unit
import time
from hardware import I2C
from hardware import Pin
import struct


label_zerod = None
label_stream_state = None
circle0 = None
i2c0 = None
key_0 = None
joystick2_0 = None
roller485_0 = None
roller485_1 = None
roller485_2 = None
roller485_3 = None
roller485_4 = None
roller485_5 = None
now = None
packets_sent = 0
key_0_pressed = 0

joint_values_measured = None
stream_is_paused = None
joint_init_pos = None
joint_signs = [-1, -1, 1, -1, -1, -1, 1]
# Describe this function...
def read_sensors_write_data():
  global key_0_pressed, packets_sent, now, joint_values_measured, stream_is_paused, joystick2_0, roller485_0, roller485_1, roller485_2, roller485_3, roller485_4, roller485_5
  joint_values_measured = [joint_signs[0] * roller485_0.get_motor_position_readback(),
                           joint_signs[1] * roller485_1.get_motor_position_readback(), 
                           joint_signs[2] * roller485_2.get_motor_position_readback(), 
                           joint_signs[3] * roller485_3.get_motor_position_readback(), 
                           joint_signs[4] * roller485_4.get_motor_position_readback(), 
                           joint_signs[5] * roller485_5.get_motor_position_readback(), 
                           joystick2_0.get_y_position(),
                           joystick2_0.get_x_position()]
  joint_vel  = [joint_signs[0] * roller485_0.get_motor_speed_readback(),
                joint_signs[1] * roller485_1.get_motor_speed_readback(), 
                joint_signs[2] * roller485_2.get_motor_speed_readback(), 
                joint_signs[3] * roller485_3.get_motor_speed_readback(), 
                joint_signs[4] * roller485_4.get_motor_speed_readback(), 
                joint_signs[5] * roller485_5.get_motor_speed_readback()]
  dt = time.time_ns() - now
  now = time.time_ns()
  button_pressed = joystick2_0.get_button_status()
  if not stream_is_paused:
    header = b'\xAA\xBB'
    packets_sent += 1
    data = struct.pack('<14f4i', *(joint_values_measured + joint_vel + [dt, packets_sent, button_pressed, key_0_pressed]))
    sys.stdout.buffer.write(header + data)
  key_0_pressed = 0


# Describe this function...
def init_position():
  global joint_init_pos, roller485_0, roller485_1, roller485_2, roller485_3, roller485_4, roller485_5
  joint_init_pos = [roller485_0.get_motor_position_readback(), roller485_1.get_motor_position_readback(), roller485_2.get_motor_position_readback(), roller485_3.get_motor_position_readback(), roller485_4.get_motor_position_readback(), roller485_5.get_motor_position_readback(), 0]
  time.sleep_ms(100)



def key_0_wasDoubleclicked_event(state):
  global key_0_pressed, label_stream_state, key_0, joystick2_0, stream_is_paused
  stream_is_paused = not stream_is_paused
  if stream_is_paused:
    key_0.set_color(0xffcc00)
    joystick2_0.fill_color(0xffcc66)
    label_stream_state.setColor(0xffffff, 0xffcc00)
  else:
    key_0.set_color(0x33ff33)
    joystick2_0.fill_color(0x33ff33)
    label_stream_state.setColor(0xffffff, 0x33cc00)
  key_0_pressed = 2


def key_0_wasPressed_event(state):
  global key_0_pressed, label_zerod, key_0, joystick2_0
  key_0.set_color(0x33ff33)
  joystick2_0.fill_color(0x33ff33)
  label_zerod.setColor(0xffffff, 0x33cc00)
  init_position()
  key_0_pressed = 1


def setup():
  global now, label_zerod, label_stream_state, circle0, i2c0, key_0, joystick2_0, roller485_0, roller485_1, roller485_2, roller485_3, roller485_4, roller485_5, joint_values_measured, stream_is_paused, joint_init_pos
  
  M5.begin()
  Widgets.setRotation(1)
  Widgets.fillScreen(0xffffff)
  label_zerod = Widgets.Label("ZERO'D", 7, 216, 1.0, 0xffffff, 0xff0000, Widgets.FONTS.DejaVu12)
  label_stream_state = Widgets.Label("STREAMING", 223, 217, 1.0, 0xffffff, 0xff0000, Widgets.FONTS.DejaVu12)
  circle0 = Widgets.Circle(50, 155, 35, 0xfb0000, 0xff0000)

  i2c0 = I2C(0, scl=Pin(1), sda=Pin(2), freq=400000)
  roller485_0 = Roller485Unit(i2c0, address=0x64, mode=Roller485Unit.I2C_MODE)
  roller485_1 = Roller485Unit(i2c0, address=0x65, mode=Roller485Unit.I2C_MODE)
  roller485_2 = Roller485Unit(i2c0, address=0x66, mode=Roller485Unit.I2C_MODE)
  roller485_3 = Roller485Unit(i2c0, address=0x67, mode=Roller485Unit.I2C_MODE)
  roller485_4 = Roller485Unit(i2c0, address=0x69, mode=Roller485Unit.I2C_MODE)
  roller485_5 = Roller485Unit(i2c0, address=0x68, mode=Roller485Unit.I2C_MODE)
  key_0 = KeyUnit((8, 9))
  key_0.setCallback(type=key_0.CB_TYPE.WAS_DOUBLECLICKED, cb=key_0_wasDoubleclicked_event)
  key_0.setCallback(type=key_0.CB_TYPE.WAS_PRESSED, cb=key_0_wasPressed_event)
  roller485_0.set_motor_mode(2)
  roller485_1.set_motor_mode(2)
  roller485_2.set_motor_mode(2)
  roller485_3.set_motor_mode(2)
  roller485_4.set_motor_mode(2)
  roller485_5.set_motor_mode(2)
  roller485_5.set_motor_output_state(1)
  roller485_5.set_position_max_current(40000)
  joint_values_measured = [0] * 7
  joint_init_pos = [0] * 7

  key_0.set_color(0xff6600)
  joystick2_0 = Joystick2Unit(i2c0, 0x63)
  joystick2_0.fill_color(0xff0000)
  stream_is_paused = True
  init_position()
  circle0.setCursor(x=50, y=155)
  circle0.setRadius(r=35)
  circle0.setColor(color=0xff0000, fill_c=0xff0000)
  now = time.time_ns()


def loop():
  global key_0
  M5.update()
  key_0.tick(None)
  read_sensors_write_data()



if __name__ == '__main__':
  try:
    setup()
    last_time = time.time_ns()
    while True:
      loop()
      while time.time_ns() - last_time < 1e7:
        pass
      last_time = time.time_ns()
  except (Exception, KeyboardInterrupt) as e:
    try:
      from utility import print_error_msg
      print_error_msg(e)
    except ImportError:
      print("please update to latest firmware")
