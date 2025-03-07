from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
import threading
import time
from pymavlink import mavutil
from tabulate import tabulate

app = FastAPI()

# Global connection object
connection = mavutil.mavlink_connection('udp:127.0.0.1:14553')

# Global variable to store logs
mavlink_logs = []

# Function to handle MAVLink messages
def mavlink_listener():
    print("Connected to UDP port 127.0.0.1:14553")

    while True:
        # Wait for a MAVLink message
        msg = connection.recv_msg()

        if msg:
            # Append the log to the global list
            log_entry = f"Received MAVLink message: {msg}"
            mavlink_logs.append(log_entry)

            # Keep only the last 20 logs
            if len(mavlink_logs) > 100:
                mavlink_logs.pop(0)

        time.sleep(0.01)  # Small delay to avoid busy-waiting

# Start the MAVLink listener in a separate thread
mavlink_thread = threading.Thread(target=mavlink_listener, daemon=True)
mavlink_thread.start()

# Function to arm the drone
def arm_drone():
    connection.mav.command_long_send(
        connection.target_system,  # Target system ID
        connection.target_component,  # Target component ID
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,  # Command
        0,  # Confirmation
        1,  # Arm (1 = arm, 0 = disarm)
        0, 0, 0, 0, 0, 0  # Unused parameters
    )

# Function to disarm the drone
def disarm_drone():
    connection.mav.command_long_send(
        connection.target_system,  # Target system ID
        connection.target_component,  # Target component ID
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,  # Command
        0,  # Confirmation
        0,  # Disarm (1 = arm, 0 = disarm)
        0, 0, 0, 0, 0, 0  # Unused parameters
    )

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

@app.post("/arm")
def arm():
    arm_drone()
    return {"message": "Arm command sent."}

@app.post("/disarm")
def disarm():
    disarm_drone()
    return {"message": "Disarm command sent."}

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

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)