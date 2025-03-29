from .pattern_utils import *

def generate_zigzag(radius_m, stripe_separation_m):
    waypoints = [(0, 0)]
    height = radius_m * 2
    stripe_count = int(height / stripe_separation_m)
    
    for i in range(stripe_count + 1):
        y = -radius_m + (i * stripe_separation_m)
        half_width = (height/2 - abs(y)) * math.tan(math.radians(30))
        if i % 2 == 0:
            waypoints.append((-half_width, y))
            waypoints.append((half_width, y))
        else:
            waypoints.append((half_width, y))
            waypoints.append((-half_width, y))
    
    waypoints.append((0, 0))
    return waypoints

def generate_spiral(radius_m, stripe_separation_m, direction="out"):
    waypoints = [(0, 0)]
    max_radius = radius_m
    current_radius = stripe_separation_m if direction == "out" else max_radius
    
    while (direction == "out" and current_radius <= max_radius) or \
          (direction == "in" and current_radius > 0):
        
        height = current_radius * 2
        half_width = height * math.tan(math.radians(30))
        waypoints.append((0, -current_radius))
        waypoints.append((-half_width, current_radius))
        waypoints.append((half_width, current_radius))
        waypoints.append((0, -current_radius))
        
        if direction == "out":
            current_radius += stripe_separation_m
        else:
            current_radius -= stripe_separation_m
    
    waypoints.append((0, 0))
    return waypoints