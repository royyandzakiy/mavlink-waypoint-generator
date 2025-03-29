from pymavlink import mavutil
import time

class MissionHandler:
    def __init__(self, connection_string):
        self.master = mavutil.mavlink_connection(connection_string)
        print("Waiting for heartbeat...")
        self.master.wait_heartbeat()
        print("Heartbeat received!")
        self.target_system = 1
        self.target_component = 1

    def upload_mission(self, mission_items):
        self.master.waypoint_clear_all_send()
        print("Cleared existing mission.")
        
        self.master.waypoint_count_send(len(mission_items))
        print(f"Sent waypoint count: {len(mission_items)}")
        
        last_seq = -1
        retries = 0
        max_retries = 3  # Maximum retries for same waypoint request
        
        while True:
            # Use a short timeout for recv_match to prevent hanging
            msg = self.master.recv_match(type=['MISSION_REQUEST', 'WAYPOINT_REQUEST'], 
                                       blocking=True,
                                       timeout=0.5)  # Short timeout
            
            if msg is None:
                if last_seq == len(mission_items) - 1:
                    break  # All waypoints sent and no more requests
                continue
                
            seq = msg.seq
            
            # Check if we're getting repeated requests for the same waypoint
            if seq == last_seq:
                retries += 1
                if retries > max_retries:
                    print(f"Warning: Too many retries for waypoint {seq}, continuing...")
                    retries = 0
            else:
                retries = 0
                last_seq = seq
            
            if seq >= len(mission_items):
                break  # Shouldn't happen but just in case
            
            item = mission_items[seq]
            print(f"Sending {'spray' if item['is_spray'] else 'navigation'} waypoint {seq}...")
            
            self.master.mav.mission_item_send(
                self.target_system,
                self.target_component,
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
            
            # Short delay to prevent flooding
            time.sleep(0.02)
        
        self.master.waypoint_set_current_send(0)
        print("Set first waypoint as current.")
        
        self.master.mav.mission_ack_send(
            self.target_system, 
            self.target_component, 
            mavutil.mavlink.MAV_MISSION_ACCEPTED
        )
        print("Mission uploaded successfully!")