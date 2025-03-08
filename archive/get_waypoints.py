from pymavlink import mavutil
import json

# Connect to MAVProxy's udpout port
master = mavutil.mavlink_connection('udp:localhost:14603')

print("Waiting for heartbeat...")
master.wait_heartbeat()
print("Heartbeat received!")

# Target system ID and component ID (usually 1 and 1)
target_system = 1
target_component = 1

# Function to get navigation waypoints
def get_nav_waypoints():
    # Request mission count
    master.mav.mission_request_list_send(target_system, target_component)
    
    waypoints = []
    mission_count = None
    received_count = 0

    while mission_count is None or received_count < mission_count:
        try:
            msg = master.recv_match(type=['MISSION_COUNT', 'MISSION_ITEM', 'MISSION_ACK'], blocking=True, timeout=5)
            if msg is not None:
                if msg.get_type() == 'MISSION_COUNT':
                    mission_count = msg.count
                    print(f"Mission count: {mission_count}")
                    for seq in range(mission_count):
                        master.mav.mission_request_int_send(target_system, target_component, seq)
                elif msg.get_type() == 'MISSION_ITEM':
                    waypoint = {
                        'seq': msg.seq,
                        'frame': msg.frame,
                        'command': msg.command,
                        'param1': msg.param1,
                        'param2': msg.param2,
                        'param3': msg.param3,
                        'param4': msg.param4,
                        'x': msg.x,
                        'y': msg.y,
                        'z': msg.z,
                        'autocontinue': msg.autocontinue
                    }
                    waypoints.append(waypoint)
                    print(f"Received waypoint: {waypoint}")
                    received_count += 1
                elif msg.get_type() == 'MISSION_ACK':
                    print("Mission download complete")
                    break
        except Exception as e:
            print(f"Error: {e}")
            break

    # Save waypoints to JSON
    if waypoints:
        with open('waypoints.json', 'w') as f:
            json.dump(waypoints, f, indent=4)
        print("Waypoints saved to waypoints.json")
    else:
        print("No waypoints received.")

get_nav_waypoints()