"""Device runtime settings for local Mello firmware."""

# If True, firmware runs even when some Roller485 motors are missing.
# If False, startup fails fast when any expected Roller485 motor is absent.
ALLOW_PARTIAL_RIG = True

# Placeholder value used for missing or unreadable motor values.
MISSING_MOTOR_VALUE = 0.0

# Main loop target period in ns (10 ms = 100 Hz).
LOOP_PERIOD_NS = 10_000_000

# Optional Wi-Fi behavior. Keep disabled unless wifi_secrets.py is uploaded.
WIFI_AUTOCONNECT = False
WIFI_CONNECT_TIMEOUT_MS = 10000
