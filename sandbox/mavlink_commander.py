# mav_commander.py
from pymavlink import mavutil
import sys

# Connect to MAVProxy's udpout port
master = mavutil.mavlink_connection('udp:localhost:14601')
# master = mavutil.mavlink_connection('udpout:localhost:14601')
# master = mavutil.mavlink_connection('udpout:localhost:14603')
# master = mavutil.mavlink_connection('tcp:localhost:5887')

print("Waiting for heartbeat...")
master.wait_heartbeat()
print("Heartbeat received!")

# Target system ID and component ID (usually 1 and 1)
target_system = 1
target_component = 1

# Arm the vehicle
master.mav.command_long_send(
    target_system,
    target_component,
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
    0,
    1, 0, 0, 0, 0, 0, 0
)
print("Arming vehicle...")

# Set mode
# mode = 'QSTABILIZE'
# mode = 'AUTO'
mode = 'TAKEOFF'

# Check if mode is available
if mode not in master.mode_mapping():
    print('Unknown mode : {}'.format(mode))
    print('Try:', list(master.mode_mapping().keys()))
    sys.exit(1)

# Get mode ID
mode_id = master.mode_mapping()[mode]
master.mav.set_mode_send(
    target_system,
    mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
    mode_id
)
print("Setting mode to " + mode)

# Disarm after a short delay (for demonstration)
import time
time.sleep(10)

mode = 'QLAND'

# Check if mode is available
if mode not in master.mode_mapping():
    print('Unknown mode : {}'.format(mode))
    print('Try:', list(master.mode_mapping().keys()))
    sys.exit(1)

# Get mode ID
mode_id = master.mode_mapping()[mode]
master.mav.set_mode_send(
    target_system,
    mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
    mode_id
)
print("Setting mode to " + mode)

# Disarm after a short delay (for demonstration)
import time
time.sleep(5)

master.mav.command_long_send(
    target_system,
    target_component,
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
    0,
    0, 0, 0, 0, 0, 0, 0
)
print("Disarming vehicle...")

mode = 'QSTABILIZE'

# Check if mode is available
if mode not in master.mode_mapping():
    print('Unknown mode : {}'.format(mode))
    print('Try:', list(master.mode_mapping().keys()))
    sys.exit(1)

mode_id = master.mode_mapping()[mode]
master.mav.set_mode_send(
    target_system,
    mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
    mode_id
)
print("Setting mode to " + mode)