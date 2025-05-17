import eventlet
eventlet.monkey_patch()

import math
from flask import Flask, render_template_string
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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Live Mission Planner</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css"/>
    <style>
        #map { height: 70vh; }
        .controls { padding: 20px; background: #f0f0f0; }
        .param-group { margin: 10px 0; }
    </style>
</head>
<body>
    <div class="controls">
        <h2>Mission Parameters</h2>
        <div class="param-group">
            <label>Shape: 
            <select id="shapeType">
                <option value="circle">Circle</option>
                <option value="square">Square</option>
                <option value="triangle">Triangle</option>
            </select></label>
            
            <label>Pattern: 
            <select id="patternType">
                <option value="zigzag">Zigzag</option>
                <option value="spiral_out">Spiral Out</option>
                <option value="spiral_in">Spiral In</option>
            </select></label>
            
            <label>Radius (m): <input type="number" id="radius" value="50"></label>
            <label>Stripe Separation (m): <input type="number" id="stripeSep" value="5"></label>
            <label>Rotation (°): <input type="number" id="rotation" value="0"></label>
            <label>Altitude (m): <input type="number" id="altitude" value="10"></label>
            <label><input type="checkbox" id="enableSpray"> Enable Spray</label>
        </div>
        <button onclick="generateMission()">Generate Mission</button>
        <button onclick="uploadMission()">Upload Mission</button>
    </div>
    <div id="map"></div>

    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        const socket = io();
        let map, missionLayer;

        socket.on('init_map', function(data) {
            map = L.map('map').setView([data.start_lat, data.start_lon], 17);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
            missionLayer = L.layerGroup().addTo(map);
            
            L.marker([data.start_lat, data.start_lon], {
                icon: L.icon({iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png'})
            }).bindPopup('Home Position').addTo(map);
        });

        socket.on('mission_update', function(data) {
            missionLayer.clearLayers();
            
            data.waypoints.forEach((wp, idx) => {
                L.circleMarker([wp.lat, wp.lon], {
                    color: wp.is_spray ? 'red' : 'blue',
                    radius: 5
                }).bindTooltip(`WP-${idx} (${wp.alt}m)`).addTo(missionLayer);
            });

            if(data.waypoints.length > 1) {
                const path = data.waypoints.map(wp => [wp.lat, wp.lon]);
                L.polyline(path, {color: '#1f77b4', weight: 2}).addTo(missionLayer);
            }
        });

        socket.on('status', function(data) {
            alert(data.message);
        });

        function generateMission() {
            const params = {
                shapeType: document.getElementById('shapeType').value,
                patternType: document.getElementById('patternType').value,
                radius: parseFloat(document.getElementById('radius').value),
                stripeSep: parseFloat(document.getElementById('stripeSep').value),
                rotation: parseFloat(document.getElementById('rotation').value),
                altitude: parseFloat(document.getElementById('altitude').value),
                enableSpray: document.getElementById('enableSpray').checked
            };
            socket.emit('generate_mission', params);
        }

        function uploadMission() {
            socket.emit('upload_mission');
        }
    </script>
</body>
</html>
"""

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
        
        mission_items = []
        current_seq = 0
        
        for wp in current_mission['items']:
            if wp['is_spray']:
                mission_items.append({
                    'seq': current_seq,
                    'frame': mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                    'command': mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
                    'param1': MissionParams().servo_channel,
                    'param2': MissionParams().servo_pwm,
                    'x': wp['lat'],
                    'y': wp['lon'],
                    'z': wp['alt']
                })
            else:
                mission_items.append({
                    'seq': current_seq,
                    'frame': mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                    'command': mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                    'x': wp['lat'],
                    'y': wp['lon'],
                    'z': wp['alt']
                })
            current_seq += 1
        
        mission_handler.upload_mission(mission_items)
        socketio.emit('status', {'message': 'Mission uploaded successfully'})
    except Exception as e:
        socketio.emit('error', {'message': f'Upload failed: {str(e)}'})

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    # Ensure we're in application context
    with app.app_context():
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)