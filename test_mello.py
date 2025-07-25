import time
import sys
import math
from mellogello.mello_teleop import MelloTeleopInterface, DummyMelloTeleopInterface

"""
This file has been moved to mellogello/test_mello.py as part of the package structure.
Run `python -m mellogello.test_mello` or use the CLI entry point after installation.
"""
def test_mello_interface(use_dummy=False):
    """
    Test the MelloTeleopInterface by continuously reading and displaying data.
    
    Args:
        use_dummy: If True, use DummyMelloTeleopInterface for testing without hardware
    """
    try:
        if use_dummy:
            print("Using DummyMelloTeleopInterface for testing...")
            with DummyMelloTeleopInterface() as mello:
                print("Starting to read dummy data. Press Ctrl+C to stop.")
                while True:
                    values = mello.get_latest_values()
                    joints = values[:-1]
                    gripper = values[-1]
                    
                    print(f"Joints (rad): {[f'{j:.4f}' for j in joints]}")
                    print(f"Joints (deg): {[f'{math.degrees(j):.2f}' for j in joints]}")
                    print(f"Gripper: {'Closed' if gripper < 0 else 'Open'}")
                    print("-" * 50)
                    
                    time.sleep(0.1)  # Update every 100ms
        else:
            print("Using MelloTeleopInterface with real hardware...")
            with MelloTeleopInterface() as mello:
                print("Starting to read Mello data. Press Ctrl+C to stop.")
                while True:
                    values = mello.get_latest_values()
                    joints = values[:-1]
                    gripper = values[-1]
                    
                    print(f"Joints (rad): {[f'{j:.4f}' for j in joints]}")
                    print(f"Joints (deg): {[f'{math.degrees(j):.2f}' for j in joints]}")
                    print(f"Gripper: {'Closed' if gripper < 0 else 'Open'}")
                    print("-" * 50)
                    
                    time.sleep(0.1)  # Update every 100ms
                    
    except KeyboardInterrupt:
        print("\nStopping Mello interface...")
    except Exception as e:
        print(f"Error reading Mello data: {e}")

def main():
    """
    Entry point for running the Mello teleop test from the command line.
    """
    use_dummy = False
    if len(sys.argv) > 1 and sys.argv[1] == '--dummy':
        use_dummy = True
        print("Running in dummy mode (no hardware required)")

    try:
        # Give the device time to initialize
        if not use_dummy:
            print("Initializing Mello device...")
            time.sleep(2)

        # Start reading data
        test_mello_interface(use_dummy=use_dummy)

    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Unexpected error: {e}")

# Allow running as a module: python -m mellogello.test_mello
if __name__ == "__main__":
    main()