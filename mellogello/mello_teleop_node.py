#!/usr/bin/env python3
"""
Script to teleoperate the robot arm using Mello device.

This script reads joint positions from the Mello device at 20 Hz and forwards
them directly to the position controller via position commands.
"""

import time
import sys
import math
import rclpy
from rclpy.node import Node
import numpy as np
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray
from typing import Optional
from mello_teleop import MelloTeleopInterface

class MelloTeleopNode(Node):
    """ROS2 node to teleoperate robot arm using Mello device."""

    def __init__(self, arm_name: str):
        super().__init__('mello_teleop_node')
        
        self.arm_name = arm_name
        self.curr_state: Optional[JointState] = None
        self.mello: Optional[MelloTeleopInterface] = None
        # Parameters
        self.read_frequency = 100.0
        self.read_period = 1.0 / self.read_frequency
        self.joint_values = None
        self.last_joint_values = None
        self.gripper_value = None
        self.max_packet_loss_percentage = 0.0
        self.packet_time = []
        self.dt = []
        # this corresponds to the order in which the joints are read from the Mello device
        self.arm_joint_names = [
            f'{self.arm_name}_shoulder_pan_joint',
            f'{self.arm_name}_shoulder_lift_joint',
            f'{self.arm_name}_elbow_joint',
            f'{self.arm_name}_wrist_1_joint',
            f'{self.arm_name}_wrist_2_joint',
            f'{self.arm_name}_wrist_3_joint',
        ]
        self.full_joint_names = [
            f'vention_{self.arm_name}',
            *self.arm_joint_names,
            f'{self.arm_name}_hand_finger_joint'
            ]
        # Subscribe to joint states
        self.subscription = self.create_subscription(
            JointState,
            f'/{arm_name}/joint_states',
            self._get_current_cb,
            10
        )
        
        self.get_logger().info(f'Mello ROS node initialized for {arm_name} arm')
        self.get_logger().info(f'Reading frequency: {self.read_frequency} Hz')
        # create a timer event:
        self.read_timer = self.create_timer(self.read_period, self.read_callback)
        self.offset = None
        # publisher for joint states and gripper value
        self.joint_publisher = self.create_publisher(
            JointState,
            f'/{arm_name}_manual_teleop/joint_states',
            10
        )


    def _get_current_cb(self, msg: JointState) -> None:
        """Callback for current joint state updates."""                
        self.curr_state = msg
    
    def get_joints_aligned_to_names(self):
        """Get joints aligned to the joint names."""
        if self.curr_state is None:
            return None, None
        q0 = []
        v0 = []
        for joint_name in self.arm_joint_names:
            if joint_name in self.curr_state.name:
                idx = self.curr_state.name.index(joint_name)
                q0.append(self.curr_state.position[idx])
                v0.append(self.curr_state.velocity[idx])
        return np.array(q0), np.array(v0)

    def initialize_mello(self) -> bool:
        """Initialize the Mello interface."""
        try:
            self.get_logger().info('Initializing Mello device...')
            time.sleep(2)  # Give device time to initialize
            self.mello = MelloTeleopInterface()
            self.get_logger().info(f"Mello {self.arm_name} device initialized")
            return True
        except Exception as e:
            self.get_logger().error(f'Failed to initialize Mello interface: {e}')
            return False

    def read_callback(self) -> None:
        """Main teleoperation loop."""
        if self.mello is None:
            self.get_logger().error('Mello interface not initialized')
            return
        
        values = self.mello.get_latest_values()
        joints = np.array(values[:-1])  # First 6 values are joints
        sec = self.mello.sec
        nsec = self.mello.nsec
        if len(joints) != 6:
            self.get_logger().error(f'Mello returned {len(joints)} joints, expected 6')
            return
        if joints.all() == 0:
            return
        if self.curr_state is None:
            self.get_logger().error('Current state is not available')
            return
        if self.offset is None:
            self.offset = joints - self.get_joints_aligned_to_names()[0]
        self.joint_values = joints - self.offset
        self.gripper_value = values[-1]  # Last value is gripper
        # publish joint
        joint_msg = JointState()
        joint_msg.header.stamp.sec = sec
        joint_msg.header.stamp.nanosec = nsec
        joint_msg.name = self.full_joint_names
        # vention is 0 so set it to 0
        joint_msg.position = [0.0] + self.joint_values.tolist() + [self.gripper_value]
        self.joint_publisher.publish(joint_msg)

def main(args=None):
    """Main function."""
    # Initialize ROS2
    rclpy.init(args=args)
    
    # Create node
    node = MelloTeleopNode(arm_name='right')
    node.initialize_mello()
    rclpy.spin_once(node)
    while rclpy.ok():
        rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main() 