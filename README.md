# Teleop Setup Guide

## Overview
This guide covers the setup and usage of teleoperation for the robot arm using the Mello controller.

For hardware setup, refer to the [Mello Hardware Setup Guide](https://github.com/emmarUW/mello_gello).
For firmware setup, refer to the [Mello Firmware Setup Guide](/firmware/README.md).

## First-Time Device Flash (Required)

For a factory-fresh CoreS3, you must flash compatible firmware once before using the VS Code deploy tasks.

Use one of these official M5Stack tools:

1. UiFlow2 Web Burner: [https://uiflow2.m5stack.com/](https://uiflow2.m5stack.com/)
2. M5Burner (desktop): [https://docs.m5stack.com/en/uiflow/m5burner/intro](https://docs.m5stack.com/en/uiflow/m5burner/intro)

Recommended sequence:

1. Connect CoreS3 over USB.
2. Put CoreS3 in flashing mode: hold the reset button (not power) until the adjacent green LED flashes.
3. In UiFlow2, flash an empty CoreS3 project as the initial runtime/bootstrap image.
4. Reboot the board and confirm it appears as a serial port.
5. Return to this repository and continue with the VS Code workflow below.

Important:

- The burner step is one-time bootstrap.
- Day-to-day code updates should use the VS Code tasks in this repository.

## VS Code Workflow (Recommended)

This repository now includes a VS Code-based deploy workflow so users can update firmware without relying on the UiFlow project upload flow for day-to-day changes.

### One-time host setup

1. Select a Python interpreter in VS Code (prefer a workspace virtual environment).
2. Run task: `Mello: Install Host Dependencies`.

### Daily workflow

1. Run task: `Mello: Deploy Firmware`.
2. Run task: `Mello: Serial Monitor`.
3. On device, button behavior is:
   - Press and hold to ZERO.
   - Double click to start/stop stream output.

Optional tasks:

- `Mello: Deploy Firmware (With Secrets)` uploads local Wi-Fi secrets.
- `Mello: List Serial Ports` prints detected COM/TTY devices.
- `Mello: Reboot Device` sends a soft reset via mpremote.

### Partial Rig Mode (Missing Motors)

Firmware supports two behaviors when one or more Roller485 motors are missing.

- `ALLOW_PARTIAL_RIG = True` (permissive mode):
   - Firmware still boots and streams.
   - Missing motors are replaced with fallback values (`MISSING_MOTOR_VALUE`, default `0.0`).
   - UI shows a warning that the rig is partial.
- `ALLOW_PARTIAL_RIG = False` (strict mode):
   - Firmware treats missing motors as an error during setup.
   - This is useful when you want to enforce a complete 6-motor rig.

These settings are defined in `reference/mello_settings.py` and uploaded during deploy.

### VS Code Task Note

VS Code tasks run whatever command is currently saved in `.vscode/tasks.json`.
If a task run shows old arguments after edits, reload the VS Code window once so the task runner picks up the latest task definition.

## Important: Serial Output Is Binary During Streaming

When streaming is enabled on the controller, firmware sends binary packets to stdout for the host decoder. In a plain serial terminal this appears as garbled/random characters. This is expected and does not indicate broken firmware. THIS IS A CHANGE FROM EARLY MELLOGELLO IMPLEMENTATIONS.

Use the host decoder (`mellogello/mello_teleop.py`) to parse the stream.

## Mello Controller Setup

### 1. Calibrate Mello

1. Place Mello in the calibration position as shown in the images below
2. While holding it in this position, press and hold the red button for a few seconds

![Mello Calibration Position 1](readme_imgs/mello_calib_1.jpg)
![Mello Calibration Position 2](readme_imgs/mello_calib_2.jpg)

**Calibration Complete**: The ZERO indicator on the screen will turn green when calibration is successful.

![Mello Zero Indicator](readme_imgs/mello_zero.jpg)

### 2. Stream Joint Positions from Mello

1. **Unlock USB permissions**:
   ```bash
   sudo chmod 777 /dev/serial/by-id/usb-M5Stack_Technology_Co.__Ltd_M5Stack_UiFlow_2.0_24587ce945900000-if00
   ```

2. **Start streaming**: Double-tap the red button to begin streaming joint positions. The streaming indicator on the screen will turn green.

![Mello Streaming Indicator](readme_imgs/mello_streaming.jpg)

3. **Test the connection**:
   ```bash
   python tests/test_mello.py
   ```
   You should see joint positions being streamed in real-time.
