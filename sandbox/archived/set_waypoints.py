from pymavlink import mavutil
import time

# Connect to MAVProxy's udpout port
master = mavutil.mavlink_connection('udp:localhost:14603')

print("Waiting for heartbeat...")
master.wait_heartbeat()
print("Heartbeat received!")

# Target system ID and component ID (usually 1 and 1)
target_system = 1
target_component = 1

# Get current location
msg = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
lat = msg.lat / 1e7
lon = msg.lon / 1e7
alt = 30  # Desired altitude in meters

# Define square waypoints (40m sides)
distance = 0.001  # Approx 40m in degrees of latitude/longitude

waypoints = [
    (lat, lon, alt),
    (lat, lon + distance, alt),
    (lat + distance, lon + distance, alt),
    (lat + distance, lon, alt),
    (lat, lon, alt)  # Back to start
]

# Clear existing mission
master.waypoint_clear_all_send()
print("Cleared existing mission.")

# Send the number of waypoints
master.waypoint_count_send(len(waypoints))
print(f"Sent waypoint count: {len(waypoints)}")

# Wait for the drone to request waypoints
while True:
    msg = master.recv_match(type=['MISSION_REQUEST', 'WAYPOINT_REQUEST'], blocking=True)
    if msg:
        seq = msg.seq
        if seq >= len(waypoints):
            break  # All waypoints have been sent
        print(f"Sending waypoint {seq}...")

        # Send the waypoint
        lat, lon, alt = waypoints[seq]
        master.mav.mission_item_send(
            target_system,
            target_component,
            seq,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
            0,  # Current waypoint
            1,  # Autocontinue
            0, 0, 0, 0,  # Parameters 1-4 (unused)
            lat,
            lon,
            alt
        )

# Set the first waypoint as current
master.waypoint_set_current_send(0)
print("Set first waypoint as current.")

# End mission
master.mav.mission_ack_send(target_system, target_component, mavutil.mavlink.MAV_MISSION_ACCEPTED)
print("Square mission uploaded!")