"""Module to control robot using Mello device through serial communication."""

import serial
import threading
import ast
import math
import time
import struct

class MelloTeleopInterface:
    def __init__(self, port='/dev/serial/by-id/usb-M5Stack_Technology_Co.__Ltd_M5Stack_UiFlow_2.0_4827e266dd480000-if00', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self._setup_serial()
        # Concatenate joints with gripper value (1 for open, -1 for closed)
        self.latest_values = []  # Start with gripper open
        self.running = True
        self.packets_received = 0
        self.start_packets_sent = None
        self.last_packet_time = time.perf_counter()
        self.packets_sent = 0
        self.dt = 0
        self._start_read_thread()

    def _setup_serial(self):
        """Set up serial connection to Mello device."""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,# baud rate is actually ignored over USB CDC: https://github.com/hathach/tinyusb/discussions/1659
                timeout=1  # 1 second timeout
            )
            print(f"Successfully connected to {self.port}")
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            raise

    def _degrees_to_radians(self, degrees):
        """Convert a list of angles from degrees to radians."""
        return [math.radians(deg) for deg in degrees]

    def _read_thread(self):
        """Background thread to continuously read from serial port."""
        FORMAT = '<14f4i'  # little-endian, 6 floats + 2 ints
        PACKET_SIZE = struct.calcsize(FORMAT)
        SYNC = b'\xAA\xBB'
        SYNC_SIZE = len(SYNC)
        while self.running:
            now = time.perf_counter() # time right before the read is as close as we can get to the actual time of the packet
            if self.serial.in_waiting>=SYNC_SIZE:
                read_sync = self.serial.read(SYNC_SIZE)
                if SYNC == read_sync:
                    with self.read_thread.lock:
                        raw_data = self.serial.read(PACKET_SIZE)
                        # Unpack into Python values
                        unpacked = struct.unpack(FORMAT, raw_data)
                        
                        # Extract components
                        joints_deg = list(unpacked[:6])
                        joystick_y_position = unpacked[6]
                        joystick_x_position = unpacked[7]
                        joint_velocities = list(unpacked[8:14])
                        self.dt = unpacked[14] * 1e-6 # dt is in milliseconds
                        self.packets_sent = unpacked[15]
                        button_pressed = unpacked[16]
                        key_0_pressed = unpacked[17]
                        sec = int(now)
                        nsec = int((now - sec)*1e9)
                        # Apply your same logic as before
                        joints_rad = self._degrees_to_radians(joints_deg)
                        joint_velocities_rad = self._degrees_to_radians(joint_velocities)
                        valid, packet_loss_percentage, packet_time, dt = self.get_packet_loss()
                        self.packets_received += 1
                        self.packet_time = time.perf_counter() - self.last_packet_time
                        self.last_packet_time = time.perf_counter()
                        if self.start_packets_sent is None:
                            self.start_packets_sent = self.packets_sent
                        if not valid:
                            continue
                        self.latest_values = joints_rad + joint_velocities_rad + [joystick_y_position, 
                        joystick_x_position, button_pressed, key_0_pressed, self.dt, sec, nsec, packet_loss_percentage, packet_time]

    def _start_read_thread(self):
        """Start the background reading thread."""
        self.read_thread = threading.Thread(target=self._read_thread)
        self.read_thread.daemon = True
        self.read_thread.lock = threading.Lock()
        self.read_thread.start()

    def get_latest_values(self):
        """Get the most recent joint and gripper values as concatenated array."""
        return self.latest_values
    
    def get_packet_loss(self):
        """Get the packet loss as a percentage."""
        if self.packets_received == 0 or self.packets_sent == self.start_packets_sent or self.start_packets_sent is None:
            return False, 0.0, 0, 0
        packets_expected = self.packets_sent - self.start_packets_sent
        packet_loss_percentage = 100 *(packets_expected - self.packets_received) / packets_expected
        return True, packet_loss_percentage, self.packet_time*1e3, self.dt

    def cleanup(self):
        """Clean up resources."""
        self.running = False
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("Serial port closed")

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup() 