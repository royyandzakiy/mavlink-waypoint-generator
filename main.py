from fastapi import FastAPI
import threading
import time
from pymavlink import mavutil

app = FastAPI()

# Function to handle MAVLink messages
def mavlink_listener():
    # connection_str = 'tcp:127.0.0.1:5887'
    connection_str = 'udp:127.0.0.1:14552'
    connection = mavutil.mavlink_connection(connection_str)
    print("Connected to " + connection_str)

    while True:
        # Wait for a MAVLink message
        msg = connection.recv_msg()

        if msg:
            # Print the MAVLink message
            print(f"Received MAVLink message: {msg}")

        time.sleep(0.01)  # Small delay to avoid busy-waiting

# Start the MAVLink listener in a separate thread
mavlink_thread = threading.Thread(target=mavlink_listener, daemon=True)
mavlink_thread.start()

# FastAPI root endpoint
@app.get("/")
def read_root():
    return {"message": "MAVLink listener is running. Check the console for MAVLink messages."}

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)