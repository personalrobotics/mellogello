#!/usr/bin/env python3
"""
Record joint states and perform frequency analysis (FFT) on each joint's position and velocity.
Waits for 1000 messages (~10 seconds at 100 Hz), then computes and plots frequency spectra.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import numpy as np
import matplotlib.pyplot as plt

class JointFreqAnalyzer(Node):
    def __init__(self):
        super().__init__('joint_freq_analyzer')
        
        # Parameters
        self.topic_name = '/right_manual_teleop/joint_states'
        self.num_samples = 1000  # number of messages to record
        self.data_positions = []
        self.data_velocities = []
        self.joint_names = []
        self.timestamps = []
        
        # Subscription
        self.subscription = self.create_subscription(
            JointState,
            self.topic_name,
            self.joint_callback,
            10
        )

        self.get_logger().info(f"Listening to {self.topic_name} for {self.num_samples} messages...")

    def joint_callback(self, msg: JointState):
        """Callback to record joint state data."""
        if not self.joint_names:
            self.joint_names = msg.name
        
        self.data_positions.append(msg.position)
        self.data_velocities.append(msg.velocity)
        self.timestamps.append(msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9)

        if len(self.data_positions) >= self.num_samples:
            self.get_logger().info("Collected enough samples. Performing frequency analysis...")
            self.subscription.destroy()  # stop listening
            self.analyze_frequency()

    def analyze_frequency(self):
        """Perform FFT analysis on joint data."""
        positions = np.array(self.data_positions)
        velocities = np.array(self.data_velocities)
        timestamps = np.array(self.timestamps)
        
        # Drop the first ("vention") and last ("gripper") joints
        positions = positions[:, 1:-1]
        velocities = velocities[:, 1:-1]
        joint_names = self.joint_names[1:-1]
        
        # Compute sampling rate from time deltas
        dt = np.mean(np.diff(timestamps))
        fs = 1.0 / dt
        self.get_logger().info(f"Estimated sampling rate: {fs:.2f} Hz")

        n_samples = positions.shape[0]
        freq = np.fft.rfftfreq(n_samples, d=dt)

        # Plot frequency response for each joint
        num_joints = positions.shape[1]
        fig, axes = plt.subplots(num_joints, 2, figsize=(8, 2 * num_joints))
        fig.suptitle("Mello Joint Frequency Analysis (Position & Velocity)", fontsize=13)
        
        if num_joints == 1:
            axes = np.array([axes])  # handle case with one joint

        for i in range(num_joints):
            pos_fft = np.fft.rfft(positions[:, i])
            vel_fft = np.fft.rfft(velocities[:, i])
            
            pos_gain = np.abs(pos_fft)
            vel_gain = np.abs(vel_fft)

            # Position spectrum
            axes[i, 0].plot(freq, pos_gain, linewidth=2, color='grey')
            axes[i, 0].set_title(f"{joint_names[i]} - Pos", fontsize=10)
            axes[i, 0].set_xlabel("Freq (Hz)")
            axes[i, 0].set_ylabel("Gain")
            
            # Velocity spectrum
            axes[i, 1].plot(freq, vel_gain, linewidth=2, color='grey')
            axes[i, 1].set_title(f"{joint_names[i]} - Vel", fontsize=10)
            axes[i, 1].set_xlabel("Freq (Hz)")
            axes[i, 1].set_ylabel("Gain")
            
            # Thicker border lines
            for ax in axes[i]:
                for spine in ax.spines.values():
                    spine.set_linewidth(2)
            axes[i, 0].set_xlim(0, 20)
            axes[i, 1].set_xlim(0, 20)
            axes[i, 0].set_ylim(0, 100)
            axes[i, 1].set_ylim(0, 100)
        # Save the figure

        plt.tight_layout()
        plt.savefig('../figures/mello_joint_frequency_analysis.pdf', bbox_inches='tight', pad_inches=0)
        plt.show()

        self.get_logger().info("FFT analysis complete. Closing node.")
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = JointFreqAnalyzer()
    rclpy.spin(node)


if __name__ == "__main__":
    main()