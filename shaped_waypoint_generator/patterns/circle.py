from .pattern_utils import *

def generate_zigzag(radius_m, stripe_separation_m):
    waypoints = [(0, 0)]
    num_stripes = int((radius_m * 2) / stripe_separation_m)
    
    for i in range(num_stripes + 1):
        y = -radius_m + (i * stripe_separation_m)
        half_width = math.sqrt(max(0, radius_m**2 - y**2))
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
        
        circumference = 2 * math.pi * current_radius
        num_points = max(8, int(circumference / stripe_separation_m))
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = current_radius * math.cos(angle)
            y = current_radius * math.sin(angle)
            waypoints.append((x, y))
        
        if direction == "out":
            current_radius += stripe_separation_m
        else:
            current_radius -= stripe_separation_m
    
    waypoints.append((0, 0))
    return waypoints