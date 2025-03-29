from pymavlink import mavutil
import time
import math
import numpy as np

# Connect to MAVProxy's udpout port
master = mavutil.mavlink_connection('udp:localhost:14603')

print("Waiting for heartbeat...")
master.wait_heartbeat()
print("Heartbeat received!")

# Target system ID and component ID (usually 1 and 1)
target_system = 1
target_component = 1

# Get current location (this will be our starting point)
msg = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
start_lat = msg.lat / 1e7
start_lon = msg.lon / 1e7
alt = 30  # Desired altitude in meters

# Configuration parameters
square_size_m = 500  # Size of the square area in meters
stripe_separation_m = 100  # Distance between zigzag lines in meters
# rotation_deg = 45  # Rotation angle in degrees (0 = east, 90 = north)
rotation_deg = 0  # Rotation angle in degrees (0 = east, 90 = north)

# Convert meters to degrees (approximate)
def meters_to_degrees(meters, latitude):
    # At equator, 1 degree ≈ 111,320 meters
    return meters / (111320 * math.cos(math.radians(latitude)))

# Convert degrees to meters (approximate)
def degrees_to_meters(degrees, latitude):
    return degrees * (111320 * math.cos(math.radians(latitude)))

# Rotate a point (x,y) around origin (0,0) by angle_rad radians
def rotate_point(x, y, angle_rad):
    x_rot = x * math.cos(angle_rad) - y * math.sin(angle_rad)
    y_rot = x * math.sin(angle_rad) + y * math.cos(angle_rad)
    return x_rot, y_rot

# Calculate the square boundaries in meters
half_size = square_size_m / 2

# Generate zigzag waypoints in local coordinates (meters)
waypoints_local = []
stripe_count = int(square_size_m / stripe_separation_m)

# Add starting point (current position) first - will be (0,0) in local coords
waypoints_local.append((0, 0))

# Generate zigzag pattern in local coordinates
for i in range(stripe_count + 1):
    x = -half_size + (i * stripe_separation_m)
    
    if i % 2 == 0:
        # Even pass: go to top
        waypoints_local.append((x, half_size))
    else:
        # Odd pass: go to bottom
        waypoints_local.append((x, -half_size))
    
    # Add the turn point (except for the last pass)
    if i < stripe_count:
        next_x = -half_size + ((i + 1) * stripe_separation_m)
        if i % 2 == 0:
            # Coming from top, turn right
            waypoints_local.append((next_x, half_size))
        else:
            # Coming from bottom, turn right
            waypoints_local.append((next_x, -half_size))

# Return to start (optional)
waypoints_local.append((0, 0))

# Convert rotation angle to radians
rotation_rad = math.radians(rotation_deg)

# Rotate all waypoints and convert to global coordinates
waypoints_global = []
for x, y in waypoints_local:
    # Rotate the point
    x_rot, y_rot = rotate_point(x, y, rotation_rad)
    
    # Convert meters to degrees
    lat_offset = meters_to_degrees(y_rot, start_lat)
    lon_offset = meters_to_degrees(x_rot, start_lat)
    
    # Calculate global coordinates
    lat = start_lat + lat_offset
    lon = start_lon + lon_offset
    waypoints_global.append((lat, lon, alt))

# Clear existing mission
master.waypoint_clear_all_send()
print("Cleared existing mission.")

# Send the number of waypoints
master.waypoint_count_send(len(waypoints_global))
print(f"Sent waypoint count: {len(waypoints_global)}")

# Wait for the drone to request waypoints
while True:
    msg = master.recv_match(type=['MISSION_REQUEST', 'WAYPOINT_REQUEST'], blocking=True)
    if msg:
        seq = msg.seq
        if seq >= len(waypoints_global):
            break  # All waypoints have been sent
        print(f"Sending waypoint {seq}...")

        # Send the waypoint
        lat, lon, alt = waypoints_global[seq]
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
print(f"Zigzag mission uploaded with {rotation_deg} degree rotation!")