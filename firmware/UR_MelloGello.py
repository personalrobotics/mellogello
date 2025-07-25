import os, sys, io
import M5
from M5 import *
from unit import KeyUnit
from unit import Joystick2Unit
import time
import network
from unit import Roller485Unit
from hardware import I2C
from hardware import Pin



image0 = None
label_pwr_status = None
label0 = None
label1 = None
label3 = None
title_bar = None
label_zerod = None
label2 = None
label4 = None
label_position_linked = None
label6 = None
label_wifi_status = None
label5 = None
label_stream_state = None
wlan = None
i2c0 = None
key_0 = None
joystick2_0 = None
roller485_0 = None
roller485_1 = None
roller485_2 = None
roller485_3 = None
roller485_4 = None
roller485_5 = None


stream_is_paused = None
k = None
joint_init_pos = None
joint_reported_position = None
joint_values_measured = None
joint_signs = None

# Describe this function...
def calc_position():
  global stream_is_paused, k, joint_init_pos, joint_reported_position, joint_values_measured, joint_signs, image0, label_pwr_status, label0, label1, label3, title_bar, label_zerod, label2, label4, label_position_linked, label6, label_wifi_status, label5, label_stream_state, wlan, i2c0, key_0, joystick2_0, roller485_0, roller485_1, roller485_2, roller485_3, roller485_4, roller485_5
  for k in range(7):
    joint_reported_position[int(k - 1)] = joint_init_pos[int(k - 1)] + joint_signs[int(k - 1)] * joint_values_measured[int(k - 1)]


# Describe this function...
def init_position():
  global stream_is_paused, k, joint_init_pos, joint_reported_position, joint_values_measured, joint_signs, image0, label_pwr_status, label0, label1, label3, title_bar, label_zerod, label2, label4, label_position_linked, label6, label_wifi_status, label5, label_stream_state, wlan, i2c0, key_0, joystick2_0, roller485_0, roller485_1, roller485_2, roller485_3, roller485_4, roller485_5
  joint_init_pos = [roller485_0.get_motor_position_readback(), roller485_1.get_motor_position_readback(), roller485_2.get_motor_position_readback(), roller485_3.get_motor_position_readback(), roller485_4.get_motor_position_readback(), roller485_5.get_motor_position_readback(), 0]
  time.sleep_ms(100)


def key_0_wasPressed_event(state):
  global image0, label_pwr_status, label0, label1, label3, title_bar, label_zerod, label2, label4, label_position_linked, label6, label_wifi_status, label5, label_stream_state, wlan, i2c0, key_0, joystick2_0, roller485_0, roller485_1, roller485_2, roller485_3, roller485_4, roller485_5, stream_is_paused, joint_init_pos, joint_reported_position, k, joint_values_measured, joint_signs
  key_0.set_color(0x33ff33)
  joystick2_0.fill_color(0x33ff33)
  label_zerod.setColor(0xffffff, 0x33cc00)
  init_position()


def key_0_wasDoubleclicked_event(state):
  global image0, label_pwr_status, label0, label1, label3, title_bar, label_zerod, label2, label4, label_position_linked, label6, label_wifi_status, label5, label_stream_state, wlan, i2c0, key_0, joystick2_0, roller485_0, roller485_1, roller485_2, roller485_3, roller485_4, roller485_5, stream_is_paused, joint_init_pos, joint_reported_position, k, joint_values_measured, joint_signs
  stream_is_paused = not stream_is_paused
  if stream_is_paused:
    key_0.set_color(0xffcc00)
    joystick2_0.fill_color(0xffcc66)
    label_stream_state.setColor(0xffffff, 0xffcc00)
  else:
    key_0.set_color(0x33ff33)
    joystick2_0.fill_color(0x33ff33)
    label_stream_state.setColor(0xffffff, 0x33cc00)


def setup():
  global image0, label_pwr_status, label0, label1, label3, title_bar, label_zerod, label2, label4, label_position_linked, label6, label_wifi_status, label5, label_stream_state, wlan, i2c0, key_0, joystick2_0, roller485_0, roller485_1, roller485_2, roller485_3, roller485_4, roller485_5, stream_is_paused, joint_init_pos, joint_reported_position, k, joint_values_measured, joint_signs

  M5.begin()
  Widgets.setRotation(1)
  Widgets.fillScreen(0xffffff)
  image0 = Widgets.Image("/flash/res/img/UR.png", 121, 73, scale_x=.5, scale_y=.5)
  label_pwr_status = Widgets.Label("pwr", 1, 41, 1.0, 0x008616, 0xffffff, Widgets.FONTS.DejaVu12)
  label0 = Widgets.Label("0", 251, 141, 1.0, 0x008616, 0xffffff, Widgets.FONTS.DejaVu12)
  label1 = Widgets.Label("1", 224, 123, 1.0, 0x008616, 0xffffff, Widgets.FONTS.DejaVu12)
  label3 = Widgets.Label("3", 185, 49, 1.0, 0x008616, 0xffffff, Widgets.FONTS.DejaVu12)
  title_bar = Widgets.Title("MELLO GELLO - UR1", 3, 0xffffff, 0x8e8e92, Widgets.FONTS.DejaVu18)
  label_zerod = Widgets.Label("ZERO'D", 7, 216, 1.0, 0xffffff, 0xff0000, Widgets.FONTS.DejaVu12)
  label2 = Widgets.Label("2", 226, 60, 1.0, 0x008616, 0xffffff, Widgets.FONTS.DejaVu12)
  label4 = Widgets.Label("4", 148, 59, 1.0, 0x008616, 0xffffff, Widgets.FONTS.DejaVu12)
  label_position_linked = Widgets.Label("POSITION LINKED", 83, 217, 1.0, 0xffffff, 0xff0000, Widgets.FONTS.DejaVu12)
  label6 = Widgets.Label("6", 143, 122, 1.0, 0x008616, 0xffffff, Widgets.FONTS.DejaVu18)
  label_wifi_status = Widgets.Label("Wifi_status", 2, 25, 1.0, 0x008616, 0xffffff, Widgets.FONTS.DejaVu12)
  label5 = Widgets.Label("5", 106, 110, 1.0, 0x008616, 0xffffff, Widgets.FONTS.DejaVu12)
  label_stream_state = Widgets.Label("STREAMING", 223, 217, 1.0, 0xffffff, 0xff0000, Widgets.FONTS.DejaVu12)

  wlan = network.WLAN(network.STA_IF)
  i2c0 = I2C(0, scl=Pin(1), sda=Pin(2), freq=100000)
  joystick2_0 = Joystick2Unit(i2c0, 0x63)
  roller485_0 = Roller485Unit(i2c0, address=0x64, mode=Roller485Unit.I2C_MODE)
  roller485_1 = Roller485Unit(i2c0, address=0x65, mode=Roller485Unit.I2C_MODE)
  roller485_2 = Roller485Unit(i2c0, address=0x66, mode=Roller485Unit.I2C_MODE)
  roller485_3 = Roller485Unit(i2c0, address=0x67, mode=Roller485Unit.I2C_MODE)
  roller485_4 = Roller485Unit(i2c0, address=0x69, mode=Roller485Unit.I2C_MODE)
  roller485_5 = Roller485Unit(i2c0, address=0x68, mode=Roller485Unit.I2C_MODE)
  key_0 = KeyUnit((8, 9))
  key_0.setCallback(type=key_0.CB_TYPE.WAS_PRESSED, cb=key_0_wasPressed_event)
  key_0.setCallback(type=key_0.CB_TYPE.WAS_DOUBLECLICKED, cb=key_0_wasDoubleclicked_event)
  roller485_0.set_motor_mode(4)
  roller485_1.set_motor_mode(4)
  roller485_2.set_motor_mode(4)
  roller485_3.set_motor_mode(4)
  roller485_4.set_motor_mode(4)
  roller485_5.set_motor_mode(4)
  joint_values_measured = [0] * 7
  joint_init_pos = [0] * 7
  joint_reported_position = [0] * 7
  joint_signs = [-1, -1, -1, -1, -1, -1, 1]
  try:
    wlan.connect('UW MPSK', 'acH4wUe?x&')
    label_wifi_status.setText(str((str('IP: ') + str((wlan.ifconfig()[0])))))
  except:
    label_wifi_status.setText(str((str('IP: ') + str('Not Connected'))))

  key_0.set_color(0xff6600)
  joystick2_0.fill_color(0xff0000)
  stream_is_paused = True
  init_position()


def loop():
  global image0, label_pwr_status, label0, label1, label3, title_bar, label_zerod, label2, label4, label_position_linked, label6, label_wifi_status, label5, label_stream_state, wlan, i2c0, key_0, joystick2_0, roller485_0, roller485_1, roller485_2, roller485_3, roller485_4, roller485_5, stream_is_paused, joint_init_pos, joint_reported_position, k, joint_values_measured, joint_signs
  key_0.tick(None)
  M5.update()
  joint_values_measured = [roller485_0.get_motor_position_readback(), roller485_1.get_motor_position_readback(), roller485_2.get_motor_position_readback(), roller485_3.get_motor_position_readback(), roller485_4.get_motor_position_readback(), roller485_5.get_motor_position_readback(), joystick2_0.get_y_position()]
  if not stream_is_paused:
    calc_position()
    print({'iniital_positions':joint_init_pos,'measured_positions':joint_values_measured,'joint_positions:':joint_reported_position})
    time.sleep_ms(1)
  label0.setText(str(joint_reported_position[0]))
  label1.setText(str(joint_reported_position[1]))
  label2.setText(str(joint_reported_position[2]))
  label3.setText(str(joint_reported_position[3]))
  label4.setText(str(joint_reported_position[4]))
  label5.setText(str(joint_reported_position[5]))
  label6.setText(str(joint_reported_position[6]))
  label_pwr_status.setText(str((str('BAT % : ') + str((Power.getBatteryLevel())))))


if __name__ == '__main__':
  try:
    setup()
    while True:
      loop()
  except (Exception, KeyboardInterrupt) as e:
    try:
      from utility import print_error_msg
      print_error_msg(e)
    except ImportError:
      print("please update to latest firmware")
