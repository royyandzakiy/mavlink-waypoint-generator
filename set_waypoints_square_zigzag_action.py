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
stripe_separation_m = 50  # Distance between zigzag lines in meters
rotation_deg = 0  # Rotation angle in degrees (0 = east, 90 = north)
spray_interval_m = 50  # Distance between spray triggers in meters
servo_channel = 6  # PWM output channel to use (typically 6-9 for ArduPilot)
servo_pwm = 1900  # PWM value for spray ON (1100-1900)


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

# Calculate distance between two points in meters
def calculate_distance_meters(p1, p2, latitude):
    lat1, lon1 = p1
    lat2, lon2 = p2
    dlat = degrees_to_meters(lat2 - lat1, latitude)
    dlon = degrees_to_meters(lon2 - lon1, latitude)
    return math.sqrt(dlat**2 + dlon**2)

# Interpolate points between waypoints for spray triggers
def add_spray_points(waypoints, interval_m, start_lat):
    if len(waypoints) < 2:
        return waypoints, []
    
    new_waypoints = []
    spray_commands = []
    
    for i in range(len(waypoints) - 1):
        wp1 = waypoints[i]
        wp2 = waypoints[i+1]
        new_waypoints.append(wp1)
        
        # Calculate distance between waypoints
        distance = calculate_distance_meters(
            (wp1[0], wp1[1]), 
            (wp2[0], wp2[1]), 
            start_lat
        )
        
        # Calculate number of spray points needed
        num_sprays = int(distance / interval_m)
        if num_sprays > 0:
            # Calculate interpolation factors
            steps = np.linspace(0, 1, num_sprays + 2)[1:-1]
            
            for t in steps:
                # Interpolate position
                lat = wp1[0] + t * (wp2[0] - wp1[0])
                lon = wp1[1] + t * (wp2[1] - wp1[1])
                
                # Add spray command waypoint
                spray_commands.append((len(new_waypoints), (lat, lon, wp1[2])))
                
                # Add regular waypoint (MAV_CMD_NAV_WAYPOINT)
                new_waypoints.append((lat, lon, wp1[2]))
    
    new_waypoints.append(waypoints[-1])
    return new_waypoints, spray_commands

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

# Add spray trigger points between waypoints
waypoints_with_sprays, spray_points = add_spray_points(waypoints_global, spray_interval_m, start_lat)

# Clear existing mission
master.waypoint_clear_all_send()
print("Cleared existing mission.")

# Create combined mission list
mission_items = []
current_seq = 0

# Add all waypoints and spray commands
for i, wp in enumerate(waypoints_with_sprays):
    # Add navigation waypoint
    mission_items.append({
        'seq': current_seq,
        'frame': mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        'command': mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        'current': 0,
        'autocontinue': 1,
        'param1': 0,
        'param2': 0,
        'param3': 0,
        'param4': 0,
        'x': wp[0],
        'y': wp[1],
        'z': wp[2],
        'is_spray': False
    })
    current_seq += 1
    
    # Check if we need to add a spray command after this waypoint
    for spray_seq, spray_pos in spray_points:
        if spray_seq == i:
            mission_items.append({
                'seq': current_seq,
                'frame': mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                'command': mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
                'current': 0,
                'autocontinue': 1,
                'param1': servo_channel,
                'param2': servo_pwm,
                'param3': 0,
                'param4': 0,
                'x': spray_pos[0],
                'y': spray_pos[1],
                'z': spray_pos[2],
                'is_spray': True
            })
            current_seq += 1

# Send the number of waypoints
master.waypoint_count_send(len(mission_items))
print(f"Sent waypoint count: {len(mission_items)}")

# Wait for the drone to request waypoints
while True:
    msg = master.recv_match(type=['MISSION_REQUEST', 'WAYPOINT_REQUEST'], blocking=True)
    if msg:
        seq = msg.seq
        if seq >= len(mission_items):
            break  # All waypoints have been sent
        
        item = mission_items[seq]
        print(f"Sending {'spray' if item['is_spray'] else 'navigation'} waypoint {seq}...")
        
        master.mav.mission_item_send(
            target_system,
            target_component,
            seq,
            item['frame'],
            item['command'],
            item['current'],
            item['autocontinue'],
            item['param1'],
            item['param2'],
            item['param3'],
            item['param4'],
            item['x'],
            item['y'],
            item['z']
        )

# Set the first waypoint as current
master.waypoint_set_current_send(0)
print("Set first waypoint as current.")

# End mission
master.mav.mission_ack_send(target_system, target_component, mavutil.mavlink.MAV_MISSION_ACCEPTED)
print(f"Agricultural spray mission uploaded with {rotation_deg}° rotation and {spray_interval_m}m spray intervals!")
print(f"Spray control configured on servo channel {servo_channel} with PWM {servo_pwm}")