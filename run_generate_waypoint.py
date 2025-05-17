import math
import folium
import webbrowser
from pymavlink import mavutil
from config import MissionParams
from mavlink import MissionHandler
from patterns import *

def create_mission_map(start_lat, start_lon, waypoints, spray_points):
    """Create interactive Folium map with mission visualization"""
    spray_indices = {seq for seq, _ in spray_points}
    
    m = folium.Map(location=[start_lat, start_lon], zoom_start=17)
    
    # Add start position
    folium.Marker(
        [start_lat, start_lon],
        icon=folium.Icon(color='green', icon='flag'),
        tooltip='Start Position'
    ).add_to(m)
    
    # Add waypoints with different colors for spray points
    for idx, (lat, lon, alt) in enumerate(waypoints):
        color = 'red' if idx in spray_indices else 'blue'
        folium.CircleMarker(
            location=[lat, lon],
            radius=3,
            color=color,
            fill=True,
            fill_color=color,
            tooltip=f"WP-{idx} ({alt}m)"
        ).add_to(m)
    
    # Connect waypoints with lines
    points = [[wp[0], wp[1]] for wp in waypoints]
    folium.PolyLine(points, color='#1f77b4', weight=2.5).add_to(m)
    
    # Save map
    map_path = 'mission_preview.html'
    m.save(map_path)
    return map_path

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
    
    # Generate and display mission map
    map_path = create_mission_map(start_lat, start_lon, waypoints_with_sprays, spray_points)
    print(f"\nGenerated mission preview: {map_path}")
    webbrowser.open(map_path)
    
    # Wait for user confirmation
    input("\nReview the mission map in your browser.\nPress Enter to upload mission or Ctrl+C to cancel...")
    
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
    print(f"\nMission uploaded: {params.shape_type} pattern with {len(waypoints_with_sprays)} waypoints")
    print(f"Spray system {'ACTIVE' if params.enable_spray else 'DISABLED'}")

if __name__ == "__main__":
    main()