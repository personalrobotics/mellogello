import struct
import sys
import time

import M5
from M5 import Widgets
from hardware import I2C
from hardware import Pin
from unit import Joystick2Unit
from unit import KeyUnit
from unit import Roller485Unit

try:
	import mello_settings as SETTINGS
except ImportError:
	class _DefaultSettings:
		ALLOW_PARTIAL_RIG = True
		MISSING_MOTOR_VALUE = 0.0
		LOOP_PERIOD_NS = 10000000
		WIFI_AUTOCONNECT = False
		WIFI_CONNECT_TIMEOUT_MS = 10000

	SETTINGS = _DefaultSettings()


I2C_FREQUENCY = 400000
ROLLER_ADDRESSES = [0x64, 0x65, 0x66, 0x67, 0x69, 0x68]
JOYSTICK_ADDRESS = 0x63
JOINT_SIGNS = [-1, -1, 1, -1, -1, -1, 1]
PACKET_HEADER = b"\xAA\xBB"
PACKET_FORMAT = "<14f4i"
MAX_INT32 = 2147483647
MIN_INT32 = -2147483648


label_mode = None
label_health = None
label_hint_primary = None
label_hint_secondary = None
label_hint_tertiary = None
label_hint_quaternary = None
label_warning = None
label_event = None
label_stats = None
status_led = None
i2c0 = None
key_0 = None
joystick2_0 = None
roller_units = [None, None, None, None, None, None]
available_motor_count = 0

now = 0
packets_sent = 0
key_0_pressed = 0
joint_values_measured = [0.0] * 7
joint_init_pos = [0.0] * 7
stream_is_paused = True
ui_last_refresh_ms = 0
ui_event_text = ""
ui_event_expire_ms = 0
ui_state_cache = {}

UI_REFRESH_MS = 250
UI_EVENT_MS = 1200

COLOR_BG = 0xFFFFFF
COLOR_TEXT = 0x111111
COLOR_READY = 0xFFCC00
COLOR_STREAM = 0x33CC33
COLOR_DEGRADED = 0xFF9900
COLOR_ERROR = 0xFF3333
COLOR_EVENT = 0x0066CC


def _clamp_i32(value):
	if value > MAX_INT32:
		return MAX_INT32
	if value < MIN_INT32:
		return MIN_INT32
	return int(value)


def _safe_read_motor_position(index):
	unit = roller_units[index]
	if unit is None:
		return SETTINGS.MISSING_MOTOR_VALUE
	try:
		return JOINT_SIGNS[index] * unit.get_motor_position_readback()
	except Exception:
		return SETTINGS.MISSING_MOTOR_VALUE


def _safe_read_motor_velocity(index):
	unit = roller_units[index]
	if unit is None:
		return SETTINGS.MISSING_MOTOR_VALUE
	try:
		return JOINT_SIGNS[index] * unit.get_motor_speed_readback()
	except Exception:
		return SETTINGS.MISSING_MOTOR_VALUE


def _safe_joystick_positions():
	if joystick2_0 is None:
		return 0.0, 0.0
	try:
		return joystick2_0.get_y_position(), joystick2_0.get_x_position()
	except Exception:
		return 0.0, 0.0


def _safe_joystick_button():
	if joystick2_0 is None:
		return 0
	try:
		return int(joystick2_0.get_button_status())
	except Exception:
		return 0


def _show_event(message):
	global ui_event_text, ui_event_expire_ms
	ui_event_text = message
	ui_event_expire_ms = time.ticks_add(time.ticks_ms(), UI_EVENT_MS)


def _ui_mode_and_color():
	if available_motor_count < len(ROLLER_ADDRESSES):
		if stream_is_paused:
			return "DEGRADED", COLOR_DEGRADED
		return "STREAMING*", COLOR_DEGRADED
	if stream_is_paused:
		return "READY", COLOR_READY
	return "STREAMING", COLOR_STREAM


def _policy_text():
	if SETTINGS.ALLOW_PARTIAL_RIG:
		return "PERMISSIVE"
	return "STRICT"


def _update_hardware_button_colors(mode_color):
	if key_0 is not None:
		key_0.set_color(mode_color)
	if joystick2_0 is not None:
		joystick2_0.fill_color(mode_color)


def _set_label_state(key, label, text, text_color, bg_color):
	if label is None:
		return
	state = (text, text_color, bg_color)
	if ui_state_cache.get(key) == state:
		return
	label.setText(text)
	label.setColor(text_color, bg_color)
	ui_state_cache[key] = state


def _refresh_ui(force=False):
	global ui_last_refresh_ms
	now_ms = time.ticks_ms()
	if (not force) and time.ticks_diff(now_ms, ui_last_refresh_ms) < UI_REFRESH_MS:
		return
	ui_last_refresh_ms = now_ms

	mode_text, mode_color = _ui_mode_and_color()
	health_text = "MOTORS %d/%d | JOY %s" % (
		available_motor_count,
		len(ROLLER_ADDRESSES),
		"OK" if joystick2_0 is not None else "MISS",
	)
	policy = _policy_text()
	stats_text = "PKT: %d | LOOP: %d ms" % (
		packets_sent,
		int(SETTINGS.LOOP_PERIOD_NS // 1000000),
	)

	_set_label_state("mode", label_mode, "MODE: %s" % mode_text, 0xFFFFFF, mode_color)
	_set_label_state("health", label_health, "%s | %s" % (health_text, policy), COLOR_TEXT, COLOR_BG)

	warning_text = "RIG: FULL"
	warning_color = COLOR_TEXT
	if available_motor_count < len(ROLLER_ADDRESSES):
		if SETTINGS.ALLOW_PARTIAL_RIG:
			warning_text = "WARNING: PARTIAL RIG (PERMISSIVE MODE)"
			warning_color = COLOR_DEGRADED
		else:
			warning_text = "WARNING: PARTIAL RIG (STRICT MODE)"
			warning_color = COLOR_ERROR
	_set_label_state("warning", label_warning, warning_text, warning_color, COLOR_BG)
	_set_label_state("stats", label_stats, stats_text, COLOR_TEXT, COLOR_BG)

	event_active = time.ticks_diff(ui_event_expire_ms, now_ms) > 0
	if event_active and ui_event_text:
		_set_label_state("event", label_event, "EVENT: %s" % ui_event_text, 0xFFFFFF, COLOR_EVENT)
	else:
		_set_label_state("event", label_event, "EVENT: -", COLOR_TEXT, COLOR_BG)

	if status_led is not None:
		status_led.setColor(color=mode_color, fill_c=mode_color)

	_update_hardware_button_colors(mode_color)


def _connect_wifi_if_enabled():
	if not SETTINGS.WIFI_AUTOCONNECT:
		return

	try:
		import network
		import wifi_secrets
	except ImportError:
		return

	sta = network.WLAN(network.STA_IF)
	if sta.isconnected():
		return

	sta.active(True)
	sta.connect(wifi_secrets.SSID, wifi_secrets.PASSWORD)

	deadline = time.ticks_add(time.ticks_ms(), int(SETTINGS.WIFI_CONNECT_TIMEOUT_MS))
	while not sta.isconnected() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
		time.sleep_ms(100)


def _setup_rollers():
	global available_motor_count, roller_units

	detected = []
	try:
		detected = i2c0.scan()
	except Exception:
		detected = []

	roller_units = [None, None, None, None, None, None]
	available_motor_count = 0

	for index, address in enumerate(ROLLER_ADDRESSES):
		if address not in detected:
			if not SETTINGS.ALLOW_PARTIAL_RIG:
				raise RuntimeError("Missing Roller485 at address: 0x%02X" % address)
			continue

		try:
			unit = Roller485Unit(i2c0, address=address, mode=Roller485Unit.I2C_MODE)
			unit.set_motor_mode(2)
			roller_units[index] = unit
			available_motor_count += 1
		except Exception:
			if not SETTINGS.ALLOW_PARTIAL_RIG:
				raise

	if roller_units[5] is not None:
		try:
			roller_units[5].set_motor_output_state(1)
			roller_units[5].set_position_max_current(40000)
		except Exception:
			if not SETTINGS.ALLOW_PARTIAL_RIG:
				raise


def read_sensors_write_data():
	global key_0_pressed, packets_sent, now, joint_values_measured

	joystick_y, joystick_x = _safe_joystick_positions()
	button_pressed = _safe_joystick_button()

	joint_values_measured = [
		_safe_read_motor_position(0),
		_safe_read_motor_position(1),
		_safe_read_motor_position(2),
		_safe_read_motor_position(3),
		_safe_read_motor_position(4),
		_safe_read_motor_position(5),
		joystick_y,
		joystick_x,
	]

	joint_vel = [
		_safe_read_motor_velocity(0),
		_safe_read_motor_velocity(1),
		_safe_read_motor_velocity(2),
		_safe_read_motor_velocity(3),
		_safe_read_motor_velocity(4),
		_safe_read_motor_velocity(5),
	]

	timestamp = time.time_ns()
	dt = timestamp - now
	now = timestamp

	if not stream_is_paused:
		packets_sent += 1
		data = struct.pack(
			PACKET_FORMAT,
			*(joint_values_measured + joint_vel + [
				_clamp_i32(dt),
				_clamp_i32(packets_sent),
				_clamp_i32(button_pressed),
				_clamp_i32(key_0_pressed),
			])
		)
		sys.stdout.buffer.write(PACKET_HEADER + data)

	key_0_pressed = 0


def init_position():
	global joint_init_pos
	joint_init_pos = [
		_safe_read_motor_position(0),
		_safe_read_motor_position(1),
		_safe_read_motor_position(2),
		_safe_read_motor_position(3),
		_safe_read_motor_position(4),
		_safe_read_motor_position(5),
		0,
	]
	time.sleep_ms(100)


def key_0_wasDoubleclicked_event(state):
	global key_0_pressed, stream_is_paused
	stream_is_paused = not stream_is_paused
	if stream_is_paused:
		_show_event("STREAM OFF")
	else:
		_show_event("STREAM ON")
	key_0_pressed = 2
	_refresh_ui(force=True)


def key_0_wasPressed_event(state):
	global key_0_pressed
	init_position()
	_show_event("ZERO CAPTURED")
	key_0_pressed = 1
	_refresh_ui(force=True)


def setup():
	global now, label_mode, label_health, label_hint_primary, label_hint_secondary
	global label_hint_tertiary, label_hint_quaternary
	global label_warning, label_event, label_stats, status_led
	global i2c0, key_0, joystick2_0, stream_is_paused

	M5.begin()
	Widgets.setRotation(1)
	Widgets.fillScreen(COLOR_BG)

	label_mode = Widgets.Label(
		"MODE: BOOTING", 8, 8, 1.0, 0xFFFFFF, COLOR_READY, Widgets.FONTS.DejaVu18
	)
	label_health = Widgets.Label(
		"MOTORS 0/6 | JOY -", 8, 42, 1.0, COLOR_TEXT, COLOR_BG, Widgets.FONTS.DejaVu12
	)
	label_hint_primary = Widgets.Label(
		"Button Functionality:", 8, 90, 1.0, COLOR_TEXT, COLOR_BG, Widgets.FONTS.DejaVu18
	)
	label_hint_secondary = Widgets.Label(
		"--------------------------------", 8, 114, 1.0, COLOR_TEXT, COLOR_BG, Widgets.FONTS.DejaVu12
	)
	label_hint_tertiary = Widgets.Label(
		"Press and hold to ZERO", 8, 132, 1.0, COLOR_TEXT, COLOR_BG, Widgets.FONTS.DejaVu12
	)
	label_hint_quaternary = Widgets.Label(
		"Double click: Start/Stop Stream",
		8,
		148,
		1.0,
		COLOR_TEXT,
		COLOR_BG,
		Widgets.FONTS.DejaVu12,
	)
	label_warning = Widgets.Label(
		"RIG: CHECKING...", 8, 170, 1.0, COLOR_TEXT, COLOR_BG, Widgets.FONTS.DejaVu12
	)
	label_event = Widgets.Label(
		"EVENT: -", 8, 192, 1.0, COLOR_TEXT, COLOR_BG, Widgets.FONTS.DejaVu12
	)
	label_stats = Widgets.Label(
		"PKT: 0 | LOOP: 10 ms", 8, 214, 1.0, COLOR_TEXT, COLOR_BG, Widgets.FONTS.DejaVu12
	)
	status_led = Widgets.Circle(292, 22, 14, COLOR_READY, COLOR_READY)

	i2c0 = I2C(0, scl=Pin(1), sda=Pin(2), freq=I2C_FREQUENCY)
	_setup_rollers()

	key_0 = KeyUnit((8, 9))
	key_0.setCallback(type=key_0.CB_TYPE.WAS_DOUBLECLICKED, cb=key_0_wasDoubleclicked_event)
	key_0.setCallback(type=key_0.CB_TYPE.WAS_PRESSED, cb=key_0_wasPressed_event)

	try:
		joystick2_0 = Joystick2Unit(i2c0, JOYSTICK_ADDRESS)
		joystick2_0.fill_color(0xFF0000)
	except Exception:
		joystick2_0 = None

	stream_is_paused = True
	init_position()
	_show_event("READY")

	_connect_wifi_if_enabled()
	now = time.time_ns()
	_refresh_ui(force=True)


def loop():
	M5.update()
	key_0.tick(None)
	read_sensors_write_data()
	_refresh_ui(force=False)


if __name__ == "__main__":
	try:
		setup()
		last_time = time.time_ns()
		loop_period_ns = int(SETTINGS.LOOP_PERIOD_NS)

		while True:
			loop()
			elapsed_ns = time.time_ns() - last_time
			if elapsed_ns < loop_period_ns:
				remaining_ns = loop_period_ns - elapsed_ns
				sleep_ms = remaining_ns // 1000000
				if sleep_ms > 0:
					time.sleep_ms(sleep_ms)
				while time.time_ns() - last_time < loop_period_ns:
					pass
			last_time = time.time_ns()
	except (Exception, KeyboardInterrupt) as e:
		try:
			from utility import print_error_msg

			print_error_msg(e)
		except ImportError:
			print("please update to latest firmware")