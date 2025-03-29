import math
import numpy as np

def meters_to_degrees(meters, latitude):
    return meters / (111320 * math.cos(math.radians(latitude)))

def rotate_point(x, y, angle_rad):
    x_rot = x * math.cos(angle_rad) - y * math.sin(angle_rad)
    y_rot = x * math.sin(angle_rad) + y * math.cos(angle_rad)
    return x_rot, y_rot

def calculate_distance_meters(p1, p2, latitude):
    lat1, lon1 = p1
    lat2, lon2 = p2
    dlat = (lat2 - lat1) * 111320
    dlon = (lon2 - lon1) * (111320 * math.cos(math.radians(latitude)))
    return math.sqrt(dlat**2 + dlon**2)

def add_spray_points(waypoints, interval_m, start_lat):
    if len(waypoints) < 2:
        return waypoints, []
    
    new_waypoints = []
    spray_commands = []
    
    for i in range(len(waypoints) - 1):
        wp1 = waypoints[i]
        wp2 = waypoints[i+1]
        new_waypoints.append(wp1)
        
        distance = calculate_distance_meters((wp1[0], wp1[1]), (wp2[0], wp2[1]), start_lat)
        num_sprays = int(distance / interval_m)
        
        if num_sprays > 0:
            steps = np.linspace(0, 1, num_sprays + 2)[1:-1]
            for t in steps:
                lat = wp1[0] + t * (wp2[0] - wp1[0])
                lon = wp1[1] + t * (wp2[1] - wp1[1])
                spray_commands.append((len(new_waypoints), (lat, lon, wp1[2])))
                new_waypoints.append((lat, lon, wp1[2]))
    
    new_waypoints.append(waypoints[-1])
    return new_waypoints, spray_commands