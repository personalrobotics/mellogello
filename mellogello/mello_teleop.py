"""Module to control robot using Mello device through serial communication."""

import serial
import threading
import ast
import math
import time
import struct

class DummyMelloTeleopInterface:
    """A dummy version of MelloTeleopInterface that returns fixed joint positions for testing."""
    def __init__(self, port=None, baudrate=None):
        """
        Initialize with fixed joint positions.
        port and baudrate are ignored, they're just here for API compatibility.
        """
        # Initialize with a reasonable "home" position in radians
        self.fixed_joints = [0, -math.pi/2, math.pi/2, -math.pi/2, -math.pi/2, 0]
        # Concatenate joints with gripper value (1 for open, -1 for closed)
        self.latest_values = self.fixed_joints + [1]  # Gripper stays open
        print("Initialized DummyMelloTeleopInterface with fixed joint positions")
        print(f"Fixed joints (rad): {self.fixed_joints}")
        print(f"Fixed joints (deg): {[math.degrees(j) for j in self.fixed_joints]}")
        print(f"Latest values (joints + gripper): {self.latest_values}")

    def get_latest_values(self):
        """Get the fixed joint positions and gripper state as concatenated array."""
        return self.latest_values

    def cleanup(self):
        """Dummy cleanup method for API compatibility."""
        pass

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

class MelloTeleopInterface:
    def __init__(self, port='/dev/serial/by-id/usb-M5Stack_Technology_Co.__Ltd_M5Stack_UiFlow_2.0_4827e266dd480000-if00', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self._setup_serial()
        # Initialize previous values
        self.prev_joints = [0] * 6
        self.prev_gripper = 0
        # Concatenate joints with gripper value (1 for open, -1 for closed)
        self.latest_values = self.prev_joints + [1]  # Start with gripper open
        self.running = True
        self.packets_received = 0
        self.start_time = None
        self.last_packet_time = None
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
        FORMAT = '<8f6i'  # little-endian, 6 floats + 2 ints
        PACKET_SIZE = struct.calcsize(FORMAT)
        SYNC = b'\xAA\xBB'
        SYNC_SIZE = len(SYNC)
        while self.running:
            try:
                read_sync = self.serial.read(SYNC_SIZE)
                now = time.time()
                if SYNC == read_sync:
                    # if self.serial.read(1) == SYNC[1:2]:
                    try:
                        # Read exactly one packet
                        with self.read_thread.lock:
                            raw_data = self.serial.read(PACKET_SIZE)
                            # Unpack into Python values
                            unpacked = struct.unpack(FORMAT, raw_data)
                            
                            # Extract components
                            joint_positions = list(unpacked[:7])
                            self.joystick_x_position = unpacked[7]
                            self.dt = unpacked[8]
                            self.packets_sent = unpacked[9]
                            self.button_pressed = unpacked[10]
                            self.key_0_pressed = unpacked[11]
                            # internal mello time:
                            # self.sec = unpacked[12]
                            # self.nsec = unpacked[13]
                            # local time:
                            self.sec = int(now)
                            self.nsec = int((now - self.sec)*1e9)
                            # Apply your same logic as before
                            joints_deg = joint_positions[:6]
                            joints_deg[2] = -1 * joints_deg[2]  # negate joint 2
                            joints_rad = self._degrees_to_radians(joints_deg)
                            
                            # Update gripper value
                            gripper_value = self.prev_gripper
                            if len(joint_positions) > 6:
                                gripper_value = joint_positions[-1]
                            
                            if not all(j == 0 for j in joints_rad):
                                self.prev_joints = joints_rad
                            self.prev_gripper = gripper_value
                            
                            # Convert gripper to normalized 0–0.7 scale
                            gripper_value = abs(gripper_value) / 4096 * 0.7
                            
                            self.latest_values = self.prev_joints + [gripper_value]
                            self.packets_received += 1
                            if self.last_packet_time is not None:
                                self.packet_time = time.perf_counter() - self.last_packet_time
                            else:
                                self.packet_time = self.dt
                            self.last_packet_time = time.perf_counter()
                            if self.start_time is None:
                                self.start_time = self.packets_sent
                    except (ValueError, SyntaxError) as e:
                        print(f"Error parsing serial data: {e}")
                else:
                    print(SYNC, read_sync)
            except Exception as e:
                print(f"Error reading serial data: {e}")
            time.sleep(0.001)  # Small sleep to prevent busy waiting

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
        if self.packets_received == 0 or self.packets_sent == self.start_time or self.last_packet_time is None or self.start_time is None:
            return False, 0.0, 0, 0
        packets_expected = self.packets_sent - self.start_time
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