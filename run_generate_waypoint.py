import eventlet
eventlet.monkey_patch()

import math
from flask import Flask, render_template
from flask_socketio import SocketIO
from pymavlink import mavutil
from config import MissionParams
from mavlink import MissionHandler
from patterns import *

# Initialize Flask first
app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# Then other global variables
mission_handler = None
current_mission = None

def connect_to_vehicle(connection_string):
    global mission_handler
    try:
        # Create handler inside application context
        with app.app_context():
            mission_handler = MissionHandler(connection_string)
            mission_handler.master.wait_heartbeat()
            return True
    except Exception as e:
        socketio.emit('error', {'message': f'Connection failed: {str(e)}'})
        return False

@socketio.on('connect')
def handle_connect():
    with app.app_context():
        if connect_to_vehicle(MissionParams().connection_string):
            msg = mission_handler.master.recv_match(
                type='GLOBAL_POSITION_INT', 
                blocking=True
            )
            start_lat = msg.lat / 1e7
            start_lon = msg.lon / 1e7
            socketio.emit('init_map', {
                'start_lat': start_lat, 
                'start_lon': start_lon
            })

def generate_waypoints(params):
    rotation_rad = math.radians(params['rotation'])
    waypoints_global = []

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

    generator = generators[params['shapeType']][params['patternType']]
    waypoints_local = generator(params['radius'], params['stripeSep'])

    msg = mission_handler.master.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
    start_lat = msg.lat / 1e7
    start_lon = msg.lon / 1e7

    for x, y in waypoints_local:
        x_rot, y_rot = rotate_point(x, y, rotation_rad)
        lat = start_lat + meters_to_degrees(y_rot, start_lat)
        lon = start_lon + meters_to_degrees(x_rot, start_lat)
        waypoints_global.append((lat, lon, params['altitude']))

    waypoints_with_sprays, spray_points = add_spray_points(
        waypoints_global,
        MissionParams().spray_interval_m,
        start_lat,
        params['enableSpray']
    )

    return waypoints_with_sprays, spray_points

@socketio.on('generate_mission')
def handle_generate_mission(params):
    try:
        global current_mission
        waypoints, spray_points = generate_waypoints(params)
        
        mission_items = []
        for i, wp in enumerate(waypoints):
            mission_items.append({
                'lat': wp[0],
                'lon': wp[1],
                'alt': wp[2],
                'is_spray': False
            })
            
            if params['enableSpray']:
                for spray_seq, spray_pos in spray_points:
                    if spray_seq == i:
                        mission_items.append({
                            'lat': spray_pos[0],
                            'lon': spray_pos[1],
                            'alt': spray_pos[2],
                            'is_spray': True
                        })

        current_mission = {
            'params': params,
            'items': mission_items
        }
        
        socketio.emit('mission_update', {'waypoints': mission_items})
    except Exception as e:
        socketio.emit('error', {'message': f'Generation failed: {str(e)}'})

@socketio.on('upload_mission')
def handle_upload_mission():
    try:
        if not current_mission:
            raise ValueError("No mission generated")
        
        # Get fresh params to ensure latest values
        params = MissionParams()
        
        # Convert to pymavlink format
        mission_items = []
        current_seq = 0
        
        for wp in current_mission['items']:
            if wp['is_spray']:
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
                    'x': wp['lat'],
                    'y': wp['lon'],
                    'z': wp['alt']
                })
            else:
                mission_items.append({
                    'seq': current_seq,
                    'frame': mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                    'command': mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                    'current': 0,
                    'autocontinue': 1,
                    'param1': 0,  # Hold time
                    'param2': 0,  # Acceptance radius
                    'param3': 0,  # Pass through
                    'param4': 0,  # Yaw angle
                    'x': wp['lat'],
                    'y': wp['lon'],
                    'z': wp['alt']
                })
            current_seq += 1

        # Use the original upload logic from MissionHandler
        mission_handler.master.waypoint_clear_all_send()
        mission_handler.master.waypoint_count_send(len(mission_items))
        
        last_seq = -1
        while True:
            msg = mission_handler.master.recv_match(
                type=['MISSION_REQUEST', 'WAYPOINT_REQUEST'],
                blocking=True,
                timeout=3
            )
            if msg is None:
                break
                
            seq = msg.seq
            if seq >= len(mission_items):
                break
                
            item = mission_items[seq]
            print(f"Sending {'spray' if item.get('is_spray', False) else 'navigation'} waypoint {seq}...")
            
            mission_handler.master.mav.mission_item_send(
                mission_handler.target_system,
                mission_handler.target_component,
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
            last_seq = seq

        mission_handler.master.waypoint_set_current_send(0)
        mission_handler.master.mav.mission_ack_send(
            mission_handler.target_system,
            mission_handler.target_component,
            mavutil.mavlink.MAV_MISSION_ACCEPTED
        )
        
        socketio.emit('status', {'message': 'Mission uploaded successfully'})
    except Exception as e:
        socketio.emit('error', {'message': f'Upload failed: {str(e)}'})

@app.route('/')
def index():
    return render_template("index.html")

if __name__ == '__main__':
    # Ensure we're in application context
    with app.app_context():
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)