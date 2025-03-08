# mav_telemetry.py
from pymavlink import mavutil

# Connect to MAVProxy's udpin port
master = mavutil.mavlink_connection('udpin:localhost:14601')
# master = mavutil.mavlink_connection('udpin:localhost:14602')
# master = mavutil.mavlink_connection('udpbcast:localhost:14700')

print("Waiting for heartbeat...")
master.wait_heartbeat()
print("Heartbeat received!")

while True:
    try:
        msg = master.recv_match(blocking=True)
        if msg:
            print(msg)  # Print all incoming messages
    except Exception as e:
        print(f"Error: {e}")