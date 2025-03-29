from .pattern_utils import *

def generate_zigzag(radius_m, stripe_separation_m):
    waypoints = [(0, 0)]
    half_size = radius_m
    stripe_count = int((half_size * 2) / stripe_separation_m)
    
    for i in range(stripe_count + 1):
        x = -half_size + (i * stripe_separation_m)
        if i % 2 == 0:
            waypoints.append((x, half_size))
            waypoints.append((x, -half_size))
        else:
            waypoints.append((x, -half_size))
            waypoints.append((x, half_size))
    
    waypoints.append((0, 0))
    return waypoints

def generate_spiral(radius_m, stripe_separation_m, direction="out"):
    waypoints = [(0, 0)]
    max_radius = radius_m
    current_radius = stripe_separation_m if direction == "out" else max_radius
    
    while (direction == "out" and current_radius <= max_radius) or \
          (direction == "in" and current_radius > 0):
        
        half_size = current_radius
        waypoints.append((-half_size, -half_size))
        waypoints.append((-half_size, half_size))
        waypoints.append((half_size, half_size))
        waypoints.append((half_size, -half_size))
        waypoints.append((-half_size, -half_size))
        
        if direction == "out":
            current_radius += stripe_separation_m
        else:
            current_radius -= stripe_separation_m
    
    waypoints.append((0, 0))
    return waypoints