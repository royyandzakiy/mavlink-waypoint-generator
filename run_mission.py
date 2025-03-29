import math
from pymavlink import mavutil
from config import MissionParams
from mavlink import MissionHandler
from patterns import *

def main():
    params = MissionParams()
    handler = MissionHandler(params.connection_string)
    
    # Get current position
    msg = handler.master.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
    start_lat = msg.lat / 1e7
    start_lon = msg.lon / 1e7
    
    # Generate waypoints
    generators = {
        'circle': {
            'zigzag': circle_zigzag,
            'spiral_out': lambda r, s: circle_spiral(r, s, 'out'),
            'spiral_in': lambda r, s: circle_spiral(r, s, 'in')
        },
        'square': {
            'zigzag': square_zigzag,
            'spiral_out': lambda r, s: square_spiral(r, s, 'out'),
            'spiral_in': lambda r, s: square_spiral(r, s, 'in')
        },
        'triangle': {
            'zigzag': triangle_zigzag,
            'spiral_out': lambda r, s: triangle_spiral(r, s, 'out'),
            'spiral_in': lambda r, s: triangle_spiral(r, s, 'in')
        }
    }
    
    generator = generators[params.shape_type][params.pattern_type]
    waypoints_local = generator(params.radius_m, params.stripe_separation_m)
    
    # Rotate and convert to global coordinates
    rotation_rad = math.radians(params.rotation_deg)
    waypoints_global = []
    for x, y in waypoints_local:
        x_rot, y_rot = rotate_point(x, y, rotation_rad)
        lat = start_lat + meters_to_degrees(y_rot, start_lat)
        lon = start_lon + meters_to_degrees(x_rot, start_lat)
        waypoints_global.append((lat, lon, params.altitude))
    
    # Conditionally add spray points
    waypoints_with_sprays, spray_points = add_spray_points(
        waypoints_global,
        params.spray_interval_m,
        start_lat,
        params.enable_spray
    )
    
    # Prepare mission items
    mission_items = []
    current_seq = 0
    
    for i, wp in enumerate(waypoints_with_sprays):
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
        
        # Only add spray commands if enabled
        if params.enable_spray:
            for spray_seq, spray_pos in spray_points:
                if spray_seq == i:
                    mission_items.append({
                        'seq': current_seq,
                        'frame': mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                        'command': mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
                        'current': 0,
                        'autocontinue': 1,
                        'param1': params.servo_channel,
                        'param2': params.servo_pwm,
                        'param3': 0,
                        'param4': 0,
                        'x': spray_pos[0],
                        'y': spray_pos[1],
                        'z': spray_pos[2],
                        'is_spray': True
                    })
                    current_seq += 1
    
    # Upload mission
    handler.upload_mission(mission_items)
    print(f"Mission completed: {params.shape_type} pattern with {'spray' if params.enable_spray else 'no spray'}")

if __name__ == "__main__":
    main()