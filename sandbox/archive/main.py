from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
import threading
import time
from pymavlink import mavutil
from tabulate import tabulate

app = FastAPI()

# Global connection object
# connect_str = 'tcp:127.0.0.1:5887'
# connect_str = 'udpin:127.0.0.1:14550'
# connect_str = 'udpout:127.0.0.1:14552'
# connect_str = 'udpbcast:127.0.0.1:14553'
connect_str = 'udp:localhost:14603'

# connect_str = 'udp:127.0.0.1:14552'
connection = mavutil.mavlink_connection(connect_str)
# Wait for the first heartbeat to set the system and component ID of remote system for the link
connection.wait_heartbeat()
print("Heartbeat from system (system %u component %u)" % (connection.target_system, connection.target_component))

# Global variable to store logs
mavlink_logs = []

# Global variable to store telemetry data
telemetry_data = {
    "accelero": {"x": 0, "y": 0, "z": 0},
    "gyro": {"x": 0, "y": 0, "z": 0},
    "speed": 0,
    "altitude": 0,
    "heading": 0,
}

# Function to handle MAVLink messages
def mavlink_listener():
    print("Connected to " + connect_str)

    while True:
        # Wait for a MAVLink message
        msg = connection.recv_msg()

        if msg:
            # Append the log to the global list
            log_entry = f"Received MAVLink message: {msg}"
            mavlink_logs.append(log_entry)

            # Keep only the last 100 logs
            if len(mavlink_logs) > 100:
                mavlink_logs.pop(0)

            # Update telemetry data based on MAVLink message type
            if msg.get_type() == "ATTITUDE":
                telemetry_data["gyro"]["x"] = msg.rollspeed
                telemetry_data["gyro"]["y"] = msg.pitchspeed
                telemetry_data["gyro"]["z"] = msg.yawspeed
            elif msg.get_type() == "GLOBAL_POSITION_INT":
                telemetry_data["altitude"] = msg.alt / 1000  # Convert to meters
                telemetry_data["heading"] = msg.hdg / 100  # Convert to degrees
            elif msg.get_type() == "VFR_HUD":
                telemetry_data["speed"] = msg.groundspeed

        time.sleep(0.01)  # Small delay to avoid busy-waiting

# Start the MAVLink listener in a separate thread
mavlink_thread = threading.Thread(target=mavlink_listener, daemon=True)
mavlink_thread.start()

def vtol_takeoff():
    try:
        message = connection.mav.command_long_encode(
            connection.target_system,  # Target system ID
            connection.target_component,  # Target component ID
            mavutil.mavlink.MAV_CMD_NAV_VTOL_TAKEOFF,  # Command
            0,
            0,
            0, 0, 0, 0, 50, 0
        )
        connection.mav.send(message)
        response = connection.recv_match(type='COMMAND_ACK', blocking=True)
        if response and response.command == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM and response.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            print("Command accepted")
        else:
            print("Command failed")
    except Exception as e:
        print(f"Error: {e}")

def vtol_land():
    try:
        message = connection.mav.command_long_encode(
            connection.target_system,  # Target system ID
            connection.target_component,  # Target component ID
            mavutil.mavlink.MAV_CMD_NAV_VTOL_LAND,  # Command
            0,
            0,
            0, 0, 0, 0, 0, 0
        )
        connection.mav.send(message)
        response = connection.recv_match(type='COMMAND_ACK', blocking=True)
        if response and response.command == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM and response.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            print("Command accepted")
        else:
            print("Command failed")
    except Exception as e:
        print(f"Error: {e}")

# Function to read waypoints
def read_waypoints():
    # Request list of waypoints
    connection.waypoint_request_list_send()
    waypoints = []

    # Wait for waypoints to be received
    while True:
        msg = connection.recv_match(type=['MISSION_ITEM'], blocking=True, timeout=5)
        if msg is None:
            break

        waypoints.append({
            "Seq": msg.seq,
            "Lat": msg.x,
            "Lon": msg.y,
            "Alt": msg.z,
            "Command": msg.command
        })

        if msg.seq + 1 >= connection.waypoint_count():
            break

    return waypoints

# FastAPI endpoints
@app.get("/")
def read_root():
    return {"message": "MAVLink listener is running. Check /logs-page for MAVLink messages."}

@app.post("/stabilize")
def takeoff():
    try:
        # Construct the MAVLink message
        # QSTABILIZE mode in ArduPilot is custom mode 1
        custom_mode = 1
        base_mode = mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED

        # Send the command
        connection.mav.set_mode_send(
            connection.target_system,
            base_mode,
            custom_mode,
        )

        print("QSTABILIZE mode command sent.")
    except Exception as e:
        print(f"Error: {e}")
    return {"message": "takeoff command sent."}

@app.post("/takeoff")
def takeoff():
    vtol_takeoff()
    return {"message": "takeoff command sent."}

@app.post("/land")
def land():
    vtol_land()
    return {"message": "land command sent."}

@app.get("/waypoints")
def waypoints_read():
    waypoints = read_waypoints()
    return {"waypoints": waypoints}

@app.get("/logs")
def logs():
    # Stream logs dynamically
    def generate_logs():
        while True:
            if mavlink_logs:
                yield f"data: {mavlink_logs[-1]}\n\n"
            time.sleep(0.1)

    return StreamingResponse(generate_logs(), media_type="text/event-stream")

@app.get("/logs-page")
def logs_page():
    # Serve an HTML page to display logs
    html_content = """
    <html>
        <head>
            <title>MAVLink Logs</title>
            <style>
                #logs {
                    font-family: monospace;
                    white-space: pre;
                    background-color: #f4f4f4;
                    padding: 10px;
                    border: 1px solid #ccc;
                    max-height: 400px;
                    overflow-y: auto;
                }
            </style>
        </head>
        <body>
            <h1>MAVLink Logs</h1>
            <div id="logs"></div>
            <script>
                const logElement = document.getElementById("logs");
                const maxRows = 100;

                const eventSource = new EventSource("/logs");
                eventSource.onmessage = function(event) {
                    // Add new log entry
                    const logEntry = document.createElement("div");
                    logEntry.textContent = event.data;
                    logElement.appendChild(logEntry);

                    // Remove old rows if exceeding maxRows
                    while (logElement.children.length > maxRows) {
                        logElement.removeChild(logElement.firstChild);
                    }

                    // Auto-scroll to the bottom
                    logElement.scrollTop = logElement.scrollHeight;
                };
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/telemetry")
def telemetry_page():
    # Serve an HTML page to display telemetry data
    html_content = """
    <html>
        <head>
            <title>Telemetry Data</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                th, td {
                    padding: 10px;
                    border: 1px solid #ddd;
                    text-align: left;
                }
                th {
                    background-color: #f4f4f4;
                }
            </style>
        </head>
        <body>
            <h1>Telemetry Data</h1>
            <table>
                <thead>
                    <tr>
                        <th>Parameter</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody id="telemetry-data">
                    <tr><td>Accelerometer (X)</td><td id="accel-x">0</td></tr>
                    <tr><td>Accelerometer (Y)</td><td id="accel-y">0</td></tr>
                    <tr><td>Accelerometer (Z)</td><td id="accel-z">0</td></tr>
                    <tr><td>Gyroscope (X)</td><td id="gyro-x">0</td></tr>
                    <tr><td>Gyroscope (Y)</td><td id="gyro-y">0</td></tr>
                    <tr><td>Gyroscope (Z)</td><td id="gyro-z">0</td></tr>
                    <tr><td>Speed (m/s)</td><td id="speed">0</td></tr>
                    <tr><td>Altitude (m)</td><td id="altitude">0</td></tr>
                    <tr><td>Heading (°)</td><td id="heading">0</td></tr>
                </tbody>
            </table>
            <script>
                const eventSource = new EventSource("/telemetry-stream");
                eventSource.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        console.log("Received telemetry data:", data); // Debugging line
                        document.getElementById("accel-x").textContent = data.accelero.x.toFixed(2);
                        document.getElementById("accel-y").textContent = data.accelero.y.toFixed(2);
                        document.getElementById("accel-z").textContent = data.accelero.z.toFixed(2);
                        document.getElementById("gyro-x").textContent = data.gyro.x.toFixed(2);
                        document.getElementById("gyro-y").textContent = data.gyro.y.toFixed(2);
                        document.getElementById("gyro-z").textContent = data.gyro.z.toFixed(2);
                        document.getElementById("speed").textContent = data.speed.toFixed(2);
                        document.getElementById("altitude").textContent = data.altitude.toFixed(2);
                        document.getElementById("heading").textContent = data.heading.toFixed(2);
                    } catch (error) {
                        console.error("Error parsing telemetry data:", error); // Debugging line
                    }
                };
                eventSource.onerror = function(error) {
                    console.error("EventSource failed:", error); // Debugging line
                };
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/telemetry-stream")
def telemetry_stream():
    # Stream telemetry data dynamically
    def generate_telemetry():
        while True:
            yield f"data: {telemetry_data}\n\n"
            time.sleep(0.1)

    return StreamingResponse(generate_telemetry(), media_type="text/event-stream")

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)